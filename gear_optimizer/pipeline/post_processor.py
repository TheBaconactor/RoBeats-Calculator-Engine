from __future__ import annotations

import queue
import logging
import traceback
import time
import sys
from typing import Any, cast

from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.parsing import env_flag
from gear_optimizer.core.output import suppress_stdout, suppress_stderr
from gear_optimizer.data.database import init_db
from gear_optimizer.app_async_db import AsyncDbSaver
from gear_optimizer.helpers.song_helpers.results_printer import print_results
from gear_optimizer.pipeline.post_processor_persist import (
    build_post_persist_context,
    build_post_persist_db_payload,
    build_post_persist_entries,
    build_post_persist_result_payload,
)
from gear_optimizer.persistence.entries import filter_valid_persistence_entries

from gear_optimizer.core.parsing import env_get
logger = logging.getLogger(__name__)

def run_post_processor(result_queue, total_tasks: int | None = None) -> None:
    """
    Background post-processor for native in-flight optimizer results.

    Consumes per-run compute payloads (songs may be repeated) and performs CPU-heavy work:
    - Build DB payload + persistence entries
    - Print results / debug output
    - Persist to SQLite
    """
    # Ensure timely console output from the post-process worker. On Windows,
    # `multiprocessing.Process` stdout can become block-buffered, making the
    # "final configuration" prints appear only at process exit.
    try:
        if hasattr(sys.stdout, "reconfigure"):
            cast(Any, sys.stdout).reconfigure(line_buffering=True)
        if hasattr(sys.stderr, "reconfigure"):
            cast(Any, sys.stderr).reconfigure(line_buffering=True)
    except Exception as e:
        logger.warning(f"post_processor:run_post_processor: {e}")
    output_enabled = bool(getattr(ENV, "output_enabled", False))
    if not output_enabled:
        suppress_stdout(True)
        suppress_stderr(True)

    # This runs in a spawned multiprocessing child whose root logger has no handlers, and
    # (in quiet mode) stderr is suppressed process-wide. Without configuring logging here,
    # per-song failure payloads (`[POST] FAILED: ...`) reach neither the console nor
    # bin/error.log, concealing fail-loud errors (see the 2026-07-02 "stuck at 33/2237"
    # incident). Configure AFTER the stderr swap so the console handler binds to the already
    # -suppressed stderr in quiet mode (no new console output), while the durable file handler
    # records error payloads regardless. Uses the same canonical target as the main process.
    from gear_optimizer.core.logging_config import configure_default_logging

    configure_default_logging()

    try:
        init_db()
    except Exception as e:
        logger.warning(f"post_processor:run_post_processor: {e}")

    async_db = AsyncDbSaver()

    completed = 0
    failed = 0
    total = int(total_tasks or 0)
    timing = env_flag("POST_TIMING")
    timing_threshold_ms = 50.0
    try:
        timing_threshold_ms = float(env_get("POST_TIMING_THRESHOLD_MS", str(timing_threshold_ms)))
    except Exception as e:
        logger.warning(f"post_processor:run_post_processor: {e}")
        timing_threshold_ms = 50.0

    def _log_timing(label: str, dt_sec: float, *, song: str | None = None) -> None:
        if not timing:
            return
        ms = float(dt_sec) * 1000.0
        if ms < timing_threshold_ms:
            return
        prefix = f"[POST][TIMING] {song} " if song else "[POST][TIMING] "
        print(f"{prefix}{label}={ms:.1f}ms")

    while True:
        try:
            item = result_queue.get(timeout=0.2)
        except queue.Empty:
            # Ensure async DB failures don't silently degrade the run while we wait
            # for compute results (or the shutdown sentinel).
            async_db.raise_if_failed()
            continue
        except KeyboardInterrupt:
            # Ctrl+C can land on this process while blocked in `Queue.get()` on Windows.
            # Ignore it so the parent can drive shutdown via the sentinel `None` and
            # we don't leave the producer blocked on a full queue.
            continue
        except (EOFError, BrokenPipeError, OSError):
            break

        if item is None:
            break

        # Propagate compute failures
        if isinstance(item, dict) and "_error" in item:
            failed += 1
            song_name = item.get("_song_name") or item.get("song") or "Unknown"
            err_type = item.get("_error_type") or type(item.get("_error")).__name__
            msg = f"[POST] FAILED: {song_name} - {err_type}: {item.get('_error')}"
            print(msg, file=sys.stderr)
            try:
                logging.error(msg)
                if item.get("_trace"):
                    logging.error(item.get("_trace"))
            except Exception as e:
                logger.warning(f"post_processor:_print_pending_final: {e}")
            continue

        completed += 1

        try:
            _t_item0 = time.perf_counter()
            res = item
            if isinstance(item, dict) and item.get("_deferred_post"):
                _t_build0 = time.perf_counter()
                post_context = build_post_persist_context(item)
                _log_timing("deferred_payload_unpack", time.perf_counter() - _t_build0, song=item.get("song"))

                _t_dbpayload0 = time.perf_counter()
                db_payload = build_post_persist_db_payload(post_context)
                _log_timing("build_db_payload", time.perf_counter() - _t_dbpayload0, song=item.get("song"))

                _t_persist0 = time.perf_counter()
                persist_entries = build_post_persist_entries(
                    item,
                    db_payload=db_payload,
                    context=post_context,
                )
                _log_timing("build_persistence_entries", time.perf_counter() - _t_persist0, song=item.get("song"))

                # Print results (including optional FG debug) in post process so GPU can move on.
                def _emit(_msg: str) -> None:
                    return

                try:
                    _t_print0 = time.perf_counter()
                    print_results(
                        item.get("song", "Unknown"),
                        post_context.best_data,
                        post_context.best_gear,
                        post_context.best_minis,
                        item.get("current_gear") or [],
                        item.get("current_minis") or [],
                        post_context.fg_variants,
                        _emit,
                        fg_debug=bool(item.get("fg_debug")),
                        ref_arrays=item.get("ref_arrays"),
                        calc_song=item.get("calc_song"),
                        cfg=post_context.cfg,
                        db_best_fg_score=post_context.db_best_fg_score,
                        prev_record=post_context.prev_record,
                    )
                    _log_timing("print_results", time.perf_counter() - _t_print0, song=item.get("song"))
                except Exception as e:
                    logger.warning(f"post_processor:_emit: {e}")

                res = build_post_persist_result_payload(
                    item,
                    db_payload=db_payload,
                    persist_entries=persist_entries,
                )

            song_name = res.get("song", "Unknown")
            db_key = res.get("db_key") or song_name

            # DB save
            if res.get("db_payload"):
                persisted = res.get("persist_entries")
                if persisted:
                    valid_entries = filter_valid_persistence_entries(persisted, require_base_score=True)
                    if valid_entries:
                        _t_db0 = time.perf_counter()
                        # Offload SQLite work + counter updates so this post-process loop
                        # keeps draining `result_queue` (prevents GPU starvation via backpressure).
                        async_db.submit(
                            song_name,
                            valid_entries,
                            meta={
                                "db_key": db_key,
                                "_processed_run": True,
                                "cfg_dict": item.get("cfg_dict") or {},
                            },
                        )
                        _log_timing("save_loadouts_batch_enqueue", time.perf_counter() - _t_db0, song=song_name)
                    else:
                        print(f"[DB] Skipped save for {song_name}: no valid entries")
                        # Still count this as a processed run for per-song attempt counters.
                        try:
                            async_db.submit(
                                song_name,
                                [],
                                meta={
                                    "db_key": db_key,
                                    "_processed_run": True,
                                    "cfg_dict": item.get("cfg_dict") or {},
                                },
                            )
                        except Exception as e:
                            logger.warning(f"post_processor:_emit: {e}")

            _log_timing("post_item_total", time.perf_counter() - _t_item0, song=song_name)

        except Exception as exc:
            failed += 1
            msg = f"[POST] Error: {type(exc).__name__}: {exc}"
            print(msg, file=sys.stderr)
            try:
                logging.error(msg + "\n" + traceback.format_exc())
            except Exception as e:
                logger.warning(f"post_processor:_emit: {e}")
        async_db.raise_if_failed()

    # Flush pending DB work before exiting so we don't leave the main pipeline
    # waiting on in-flight DB tasks.
    async_db.shutdown(timeout=30.0)

    try:
        if failed > 0:
            print(f"[POST][SUMMARY] {failed}/{max(1, total)} task(s) failed.")
    except Exception as e:
        logger.warning(f"post_processor:_emit: {e}")
