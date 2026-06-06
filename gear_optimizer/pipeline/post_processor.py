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
from gear_optimizer.pipeline.post_processor_deferred import (
    build_deferred_post_context,
    build_deferred_post_db_payload,
    build_deferred_post_persist_entries,
    build_deferred_post_print_payload,
    build_deferred_post_result_payload,
    should_persist_pending_fg_job,
)
from gear_optimizer.pipeline.post_processor_fg_updates import (
    build_fg_update_state,
    canonicalize_fg_update_entries as _canonicalize_fg_update_entries,
)
from gear_optimizer.persistence.entries import filter_valid_persistence_entries
from gear_optimizer.solver.frontier_cache_errors import MissingFrontierCacheError

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

    try:
        init_db()
    except Exception as e:
        logger.warning(f"post_processor:run_post_processor: {e}")

    async_db = AsyncDbSaver()

    completed = 0
    failed = 0
    total = int(total_tasks or 0)
    timing = env_flag("POST_TIMING")
    sync_output = env_flag("POST_SYNC_OUTPUT", "1")
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

    # In the native in-flight pipeline, the GA result is posted immediately while ForceGreats (FG)
    # runs later in the main process; printing the final block immediately can make subsequent FG
    # logs appear "after" the final output. To keep output coherent, we can delay printing per-song
    # final output until we see the corresponding FG update message.
    pending_final_print: dict[str, dict] = {}
    pending_fg_summary: dict[str, dict] = {}

    def _print_pending_final(song: str) -> None:
        payload = pending_final_print.get(song)
        if not payload:
            return

        fg_state = pending_fg_summary.get(song) or {}
        fg_variants = fg_state.get("fg_variants") or []
        saw_fg_update = bool(fg_state.get("saw_fg_update"))
        try:
            saved = int(fg_state.get("saved_count") or 0)
        except Exception as e:
            logger.warning(f"post_processor:_print_pending_final: {e}")
            saved = 0
        try:
            best_fg = int(fg_state.get("best_fg") or 0)
        except Exception as e:
            logger.warning(f"post_processor:_print_pending_final: {e}")
            best_fg = 0

        # If FG work was deferred and no update arrived, `best_fg` will be 0.
        # Still show a meaningful FG number if the DB already has a best FG record.
        db_best_fg_floor = 0
        try:
            db_best_fg_floor = int(payload.get("db_best_fg_score") or 0)
        except Exception as e:
            logger.warning(f"post_processor:_print_pending_final: {e}")
            db_best_fg_floor = 0

        if best_fg > db_best_fg_floor:
            db_best_fg_floor = best_fg

        try:
            _t_print0 = time.perf_counter()
            print_results(
                payload.get("song", song),
                payload.get("best_data") or {},
                payload.get("best_gear") or [],
                payload.get("best_minis") or [],
                payload.get("current_gear") or [],
                payload.get("current_minis") or [],
                fg_variants,
                payload.get("_emit") or (lambda _msg: None),
                fg_debug=bool(payload.get("fg_debug")),
                ref_arrays=payload.get("ref_arrays"),
                calc_song=payload.get("calc_song"),
                cfg=payload.get("cfg"),
                db_best_fg_score=db_best_fg_floor,
                prev_record=payload.get("prev_record"),
            )
            _log_timing("print_results", time.perf_counter() - _t_print0, song=song)
        except Exception as e:
            logger.warning(f"post_processor:_print_pending_final: {e}")

        if saw_fg_update and saved > 0:
            logger.debug("[POST][FG] Saved %s FG variant(s) for %s (best_fg=%s)", saved, song, best_fg)

        pending_final_print.pop(song, None)
        pending_fg_summary.pop(song, None)

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

        # Deferred ForceGreats updates (do not affect completed/total counts).
        if isinstance(item, dict) and item.get("_fg_update"):
            try:
                song_name = item.get("song", "Unknown")
                db_key = item.get("db_key") or song_name
                valid_entries: list[dict] = []

                persisted = item.get("persist_entries") or []
                persisted = _canonicalize_fg_update_entries(
                    persisted,
                    file_path=str(item.get("file_path") or ""),
                    cfg_dict=item.get("cfg_dict") or {},
                    ref_arrays=item.get("ref_arrays"),
                    song_name=str(song_name),
                )
                valid_entries = filter_valid_persistence_entries(persisted, require_base_score=True)
                if valid_entries:
                    if timing:
                        logger.debug(
                            "[POST][FG] Saving %s FG variant(s) for %s...",
                            len(valid_entries),
                            song_name,
                        )
                    _t_db0 = time.perf_counter()

                    # Offload SQLite work + counter updates so the post-process loop
                    # keeps draining `result_queue` (prevents GPU starvation via backpressure).
                    async_db.submit(
                        song_name,
                        valid_entries,
                        meta={
                            "db_key": db_key,
                            "_processed_run": False,  # FG-only update: do NOT increment attempts
                            "cfg_dict": item.get("cfg_dict") or {},
                        },
                    )
                    _log_timing("fg_save_loadouts_batch_enqueue", time.perf_counter() - _t_db0, song=song_name)
                else:
                    if persisted:
                        logger.debug("[DB] Skipped FG update for %s: no valid entries", song_name)

                try:
                    _t_del0 = time.perf_counter()
                    async_db.delete_pending_fg_job(db_key)
                    _log_timing("fg_delete_pending_job_enqueue", time.perf_counter() - _t_del0, song=song_name)
                except Exception as e:
                    logger.warning(f"post_processor:_print_pending_final: {e}")

                fg_state = build_fg_update_state(pending_fg_summary.get(song_name), valid_entries)
                pending_fg_summary[song_name] = fg_state

                if sync_output and song_name in pending_final_print:
                    _print_pending_final(song_name)
                elif not sync_output:
                    try:
                        saved = int(fg_state.get("saved_count") or 0)
                    except Exception as e:
                        logger.warning(f"post_processor:_print_pending_final: {e}")
                        saved = 0
                    try:
                        best_fg = int(fg_state.get("best_fg") or 0)
                    except Exception as e:
                        logger.warning(f"post_processor:_print_pending_final: {e}")
                        best_fg = 0
                    if saved > 0:
                        logger.debug("[POST][FG] Saved %s FG variant(s) for %s (best_fg=%s)", saved, song_name, best_fg)
                else:
                    # If there's no pending final output, keep a small status line so users still
                    # see that FG persistence happened.
                    try:
                        saved = int(fg_state.get("saved_count") or 0)
                    except Exception as e:
                        logger.warning(f"post_processor:_print_pending_final: {e}")
                        saved = 0
                    try:
                        best_fg = int(fg_state.get("best_fg") or 0)
                    except Exception as e:
                        logger.warning(f"post_processor:_print_pending_final: {e}")
                        best_fg = 0
                    if saved > 0:
                        logger.debug("[POST][FG] Saved %s FG variant(s) for %s (best_fg=%s)", saved, song_name, best_fg)
            except MissingFrontierCacheError as exc:
                # Fail loudly: a required prebuilt frontier cache was missing, so the FG
                # score could not be canonicalized. Count it and surface it rather than
                # silently completing the song with only its base score.
                failed += 1
                msg = (
                    f"[POST][FG] FAILED: {item.get('song', 'Unknown')} - required frontier "
                    f"cache missing; FG score not saved: {exc}"
                )
                print(msg, file=sys.stderr)
                try:
                    logging.error(msg + "\n" + traceback.format_exc())
                except Exception as e:
                    logger.warning(f"post_processor:_print_pending_final: {e}")
            except Exception as exc:
                msg = f"[POST][FG] Error: {type(exc).__name__}: {exc}"
                print(msg, file=sys.stderr)
                try:
                    logging.error(msg + "\n" + traceback.format_exc())
                except Exception as e:
                    logger.warning(f"post_processor:_print_pending_final: {e}")
            continue

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
                post_context = build_deferred_post_context(item)
                _log_timing("deferred_payload_unpack", time.perf_counter() - _t_build0, song=item.get("song"))

                _t_dbpayload0 = time.perf_counter()
                db_payload = build_deferred_post_db_payload(post_context)
                _log_timing("build_db_payload", time.perf_counter() - _t_dbpayload0, song=item.get("song"))

                _t_persist0 = time.perf_counter()
                persist_entries = build_deferred_post_persist_entries(
                    item,
                    db_payload=db_payload,
                    context=post_context,
                )
                _log_timing("build_persistence_entries", time.perf_counter() - _t_persist0, song=item.get("song"))

                # Durable deferred FG is opt-in. The normal in-flight queue is already
                # drained by FG workers; persisting it here bloats the main DB with
                # transient JSON pages and is not part of retained frontier coverage.
                if should_persist_pending_fg_job(item):
                    try:
                        _t_upsert0 = time.perf_counter()
                        async_db.submit_pending_fg_job(
                            item.get("db_key", item.get("song", "Unknown")),
                            item.get("ga_candidates") or [],
                        )
                        _log_timing(
                            "upsert_pending_fg_job_enqueue",
                            time.perf_counter() - _t_upsert0,
                            song=item.get("song"),
                        )
                    except Exception as e:
                        logger.warning(f"post_processor:_print_pending_final: {e}")

                # Print results (including optional FG debug) in post process so GPU can move on.
                def _emit(_msg: str) -> None:
                    return

                if sync_output and item.get("_pending_fg_job"):
                    song_name_for_print = item.get("song", "Unknown")
                    pending_final_print[song_name_for_print] = build_deferred_post_print_payload(
                        item,
                        context=post_context,
                        emit=_emit,
                    )
                    # If the FG update arrived first (unlikely but possible), print immediately.
                    if pending_fg_summary.get(song_name_for_print, {}).get("saw_fg_update"):
                        _print_pending_final(song_name_for_print)
                else:
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

                res = build_deferred_post_result_payload(
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
        if pending_final_print:
            for song_name in list(pending_final_print.keys()):
                _print_pending_final(song_name)

        if failed > 0:
            print(f"[POST][SUMMARY] {failed}/{max(1, total)} task(s) failed.")
    except Exception as e:
        logger.warning(f"post_processor:_emit: {e}")
