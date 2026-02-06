from __future__ import annotations

import json
import logging
import os
import traceback
import time
import sys

from gear_optimizer.core.fallback_monitor import FallbackAwareConfigParser
from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.output import suppress_stdout, suppress_stderr
from gear_optimizer.data.database import init_db
from gear_optimizer.app_async_db import AsyncDbSaver
from gear_optimizer.helpers.song_helpers.persistence import (
    build_db_payload,
    build_persistence_entries,
    make_build_details_fn,
)
from gear_optimizer.helpers.song_helpers.results_printer import print_results


class _PostCpuProfiler:
    def __init__(self, *, enabled: bool, out_path: str | None) -> None:
        self.enabled = bool(enabled)
        out_path = str(out_path or "").strip()
        self.out_path = out_path or None
        self._t0_wall = time.perf_counter()
        self._t0_cpu = time.process_time()
        self._stages: dict[str, dict[str, float | int]] = {}

    def record(self, stage: str, cpu_s: float) -> None:
        if not self.enabled:
            return
        try:
            cpu_s = float(cpu_s)
        except Exception:
            return
        if cpu_s <= 0.0:
            return
        entry = self._stages.get(stage)
        if entry is None:
            entry = {"count": 0, "cpu_total_s": 0.0, "cpu_max_s": 0.0}
            self._stages[stage] = entry
        entry["count"] = int(entry.get("count", 0) or 0) + 1
        entry["cpu_total_s"] = float(entry.get("cpu_total_s", 0.0) or 0.0) + cpu_s
        entry["cpu_max_s"] = max(float(entry.get("cpu_max_s", 0.0) or 0.0), cpu_s)

    def emit(self) -> None:
        if not self.enabled:
            return
        total_cpu = max(0.0, time.process_time() - float(self._t0_cpu))
        total_wall = max(0.0, time.perf_counter() - float(self._t0_wall))
        ranked = sorted(self._stages.items(), key=lambda kv: float(kv[1].get("cpu_total_s", 0.0) or 0.0), reverse=True)
        print(f"[POST][CpuProfile] total_cpu_s={total_cpu:.3f} total_wall_s={total_wall:.3f}")
        for name, info in ranked[:10]:
            print(
                "[POST][CpuProfile] {:<22} cpu_total={:>8.3f}s max={:>6.3f}s n={}".format(
                    name,
                    float(info.get("cpu_total_s", 0.0) or 0.0),
                    float(info.get("cpu_max_s", 0.0) or 0.0),
                    int(info.get("count", 0) or 0),
                )
            )
        if self.out_path:
            try:
                os.makedirs(os.path.dirname(self.out_path), exist_ok=True)
            except Exception:
                pass
            try:
                payload = {"total_cpu_s": total_cpu, "total_wall_s": total_wall, "stages": self._stages}
                with open(self.out_path, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=2, sort_keys=True)
            except Exception:
                pass


def run_post_processor(result_queue, total_tasks: int | None = None) -> None:
    """
    Background post-processor for sequential pipeline mode.

    Consumes per-song compute payloads and performs CPU-heavy work:
    - Build DB payload + persistence entries
    - Print results / debug output
    - Persist to SQLite
    """
    # Ensure timely console output from the post-process worker. On Windows,
    # `multiprocessing.Process` stdout can become block-buffered, making the
    # "final configuration" prints appear only at process exit.
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(line_buffering=True)
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    output_enabled = bool(getattr(ENV, "output_enabled", False))
    if not output_enabled:
        suppress_stdout(True)
        suppress_stderr(True)

    try:
        init_db()
    except Exception:
        pass

    async_db = AsyncDbSaver()

    completed = 0
    failed = 0
    total = int(total_tasks or 0)
    timing = str(os.environ.get("POST_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    sync_output = str(os.environ.get("POST_SYNC_OUTPUT", "1") or "").strip().lower() in {"1", "true", "yes", "on"}
    timing_threshold_ms = 50.0
    try:
        timing_threshold_ms = float(os.environ.get("POST_TIMING_THRESHOLD_MS", str(timing_threshold_ms)))
    except Exception:
        timing_threshold_ms = 50.0

    cpu_profile = str(os.environ.get("POST_CPU_PROFILE", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    cpu_profile_path = str(os.environ.get("POST_CPU_PROFILE_PATH", "") or "").strip() or None
    profiler = _PostCpuProfiler(enabled=cpu_profile, out_path=cpu_profile_path)

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

    def _best_fg_improving_score_from_variants(variants: list[dict]) -> int:
        best = 0
        for v in variants or []:
            if not isinstance(v, dict):
                continue
            data = v.get("data") or {}
            if not isinstance(data, dict):
                data = {}
            fg_meta = data.get("ForceGreats") or {}
            if not isinstance(fg_meta, dict):
                fg_meta = {}
            cfg = fg_meta.get("config") or {}
            if (
                not isinstance(cfg, dict)
                or sum([(int(x) if isinstance(x, (int, float)) else 0) for x in cfg.values()]) <= 0
            ):
                continue
            try:
                fg_score = int(v.get("fg_score", 0) or 0)
            except Exception:
                fg_score = 0
            base_score = v.get("base_score")
            if base_score is None:
                base_score = v.get("score", 0)
            try:
                base_score_i = int(base_score or 0)
            except Exception:
                base_score_i = 0
            if fg_score <= base_score_i:
                continue
            if fg_score > best:
                best = fg_score
        return int(best)

    def _fg_variants_from_persist_entries(entries: list[dict]) -> list[dict]:
        variants: list[dict] = []
        for e in entries or []:
            if not isinstance(e, dict):
                continue
            details = e.get("details") or {}
            if not isinstance(details, dict):
                details = {}
            try:
                fg_score = int(e.get("fg_score", 0) or 0)
            except Exception:
                fg_score = 0
            try:
                base_score = int(e.get("score", 0) or 0)
            except Exception:
                base_score = 0
            data = dict(details)
            data["Score"] = fg_score or base_score
            variants.append(
                {
                    "data": data,
                    "gear": e.get("gear") or [],
                    "minis": e.get("minis") or [],
                    "score": base_score,
                    "fg_score": fg_score,
                    "_is_ga": bool(e.get("_is_ga")),
                }
            )
        return variants

    def _print_pending_final(song: str) -> None:
        payload = pending_final_print.get(song)
        if not payload:
            return

        fg_state = pending_fg_summary.get(song) or {}
        fg_variants = fg_state.get("fg_variants") or []
        saw_fg_update = bool(fg_state.get("saw_fg_update"))
        try:
            saved = int(fg_state.get("saved_count") or 0)
        except Exception:
            saved = 0
        try:
            best_fg = int(fg_state.get("best_fg") or 0)
        except Exception:
            best_fg = 0

        # If FG work was deferred and no update arrived, `best_fg` will be 0.
        # Still show a meaningful FG number if the DB already has a best FG record.
        db_best_fg_floor = 0
        try:
            db_best_fg_floor = int(payload.get("db_best_fg_score") or 0)
        except Exception:
            db_best_fg_floor = 0
        if db_best_fg_floor <= 0:
            try:
                if payload.get("use_evo_db", True):
                    from gear_optimizer.data.database import get_db_connection_cached

                    conn = get_db_connection_cached()
                    row = conn.execute(
                        "SELECT best_fg_score FROM songs WHERE name = ?",
                        (str(payload.get("song", song) or "").strip(),),
                    ).fetchone()
                    if row is not None:
                        db_best_fg_floor = int(row[0] or 0)
            except Exception:
                db_best_fg_floor = 0

        if best_fg > db_best_fg_floor:
            db_best_fg_floor = best_fg

        try:
            cpu_t0 = time.process_time()
            _t_print0 = time.perf_counter()
            print_results(
                payload.get("song", song),
                payload.get("best_data") or {},
                payload.get("best_gear") or [],
                payload.get("best_minis") or [],
                payload.get("current_gear") or [],
                payload.get("current_minis") or [],
                bool(payload.get("enable_gear")),
                bool(payload.get("enable_mini")),
                fg_variants,
                payload.get("_emit") or (lambda _msg: None),
                fg_debug=bool(payload.get("fg_debug")),
                ref_arrays=payload.get("ref_arrays"),
                calc_song=payload.get("calc_song"),
                cfg=payload.get("cfg"),
                db_best_fg_score=db_best_fg_floor,
            )
            _log_timing("print_results", time.perf_counter() - _t_print0, song=song)
            profiler.record("print_results_pending_final", time.process_time() - cpu_t0)
        except Exception:
            pass

        if saw_fg_update and saved > 0:
            print(f"[POST][FG] Saved {saved} FG variant(s) for {song} (best_fg={best_fg})")

        pending_final_print.pop(song, None)
        pending_fg_summary.pop(song, None)

    while True:
        try:
            item = result_queue.get()
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
                fg_state = pending_fg_summary.get(song_name) or {}
                fg_state["saw_fg_update"] = True
                valid_entries: list[dict] = []

                if item.get("use_evo_db", True):
                    persisted = item.get("persist_entries") or []
                    valid_entries = [
                        e for e in (persisted or []) if e.get("score", 0) > 0 and (e.get("gear") or e.get("minis"))
                    ]
                    if valid_entries:
                        if timing:
                            print(f"[POST][FG] Saving {len(valid_entries)} FG variant(s) for {song_name}...")
                        cpu_t0 = time.process_time()
                        _t_db0 = time.perf_counter()

                        # Offload SQLite work + counter updates so the post-process loop
                        # keeps draining `result_queue` (prevents GPU starvation via backpressure).
                        async_db.submit(
                            song_name,
                            valid_entries,
                            meta={
                                "db_key": db_key,
                                "_processed_run": False,  # FG-only update: do NOT increment attempts
                                "file_path": item.get("file_path"),
                                "cfg_dict": item.get("cfg_dict") or {},
                                "ref_arrays": item.get("ref_arrays"),
                            },
                        )
                        _log_timing("fg_save_loadouts_batch_enqueue", time.perf_counter() - _t_db0, song=song_name)
                        profiler.record("fg_save_loadouts_batch_enqueue", time.process_time() - cpu_t0)
                    else:
                        if persisted:
                            print(f"[DB] Skipped FG update for {song_name}: no valid entries")

                    try:
                        _t_del0 = time.perf_counter()
                        cpu_t0 = time.process_time()
                        async_db.delete_pending_fg_job(db_key)
                        _log_timing("fg_delete_pending_job_enqueue", time.perf_counter() - _t_del0, song=song_name)
                        profiler.record("fg_delete_pending_job_enqueue", time.process_time() - cpu_t0)
                    except Exception:
                        pass

                fg_state["saved_count"] = len(valid_entries)
                # `fg_score` can equal `score` when the optimal FG config is "no forced greats"
                # (config all zeros). For reporting, treat "best FG" as the best *improving* FG
                # result that has a valid force payload, matching DB `best_fg_score` semantics.
                best_fg_improving = 0
                for e in valid_entries:
                    if not isinstance(e, dict):
                        continue
                    try:
                        score = int(e.get("score", 0) or 0)
                    except Exception:
                        score = 0
                    try:
                        fg_score = int(e.get("fg_score", 0) or 0)
                    except Exception:
                        fg_score = 0
                    if fg_score <= score:
                        continue
                    if not e.get("force"):
                        continue
                    if fg_score > best_fg_improving:
                        best_fg_improving = fg_score
                fg_state["best_fg"] = int(best_fg_improving)
                fg_state["fg_variants"] = _fg_variants_from_persist_entries(valid_entries)
                pending_fg_summary[song_name] = fg_state

                if sync_output and song_name in pending_final_print:
                    _print_pending_final(song_name)
                elif not sync_output:
                    try:
                        saved = int(fg_state.get("saved_count") or 0)
                    except Exception:
                        saved = 0
                    try:
                        best_fg = int(fg_state.get("best_fg") or 0)
                    except Exception:
                        best_fg = 0
                    if saved > 0:
                        print(f"[POST][FG] Saved {saved} FG variant(s) for {song_name} (best_fg={best_fg})")
                else:
                    # If there's no pending final output, keep a small status line so users still
                    # see that FG persistence happened.
                    try:
                        saved = int(fg_state.get("saved_count") or 0)
                    except Exception:
                        saved = 0
                    try:
                        best_fg = int(fg_state.get("best_fg") or 0)
                    except Exception:
                        best_fg = 0
                    if saved > 0:
                        print(f"[POST][FG] Saved {saved} FG variant(s) for {song_name} (best_fg={best_fg})")
            except Exception as exc:
                msg = f"[POST][FG] Error: {type(exc).__name__}: {exc}"
                print(msg, file=sys.stderr)
                try:
                    logging.error(msg + "\n" + traceback.format_exc())
                except Exception:
                    pass
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
            except Exception:
                pass
            continue

        completed += 1

        try:
            _t_item0 = time.perf_counter()
            cpu_item_t0 = time.process_time()
            res = item
            if isinstance(item, dict) and item.get("_deferred_post"):
                _t_build0 = time.perf_counter()
                cfg_dict = item.get("cfg_dict") or {}
                cfg = cfg_from_dict(cfg_dict) if cfg_dict else FallbackAwareConfigParser()

                primary = str(item.get("meta_primary_color") or "")
                secondary = str(item.get("meta_secondary_color") or "")
                difficulty = str(item.get("difficulty") or "Unknown")
                build_details = make_build_details_fn(primary, secondary, difficulty)

                best_data = item.get("best_data") or {}
                best_gear = item.get("best_gear") or []
                best_minis = item.get("best_minis") or []
                prev_record = item.get("prev_record")
                fg_variants = item.get("fg_variants") or []

                try:
                    run_score = int(best_data.get("BaseScore") or best_data.get("Score", 0) or 0)
                except Exception:
                    run_score = 0
                run_best_fg = _best_fg_improving_score_from_variants(fg_variants)

                prev_best_score = 0
                try:
                    prev_best_score = int((prev_record or {}).get("score", 0) or 0)
                except Exception:
                    prev_best_score = 0

                prev_best_fg = 0
                # Prefer authoritative best FG score from DB (`songs.best_fg_score`).
                # Payloads can omit/miscompute this (e.g., loadout-limited caches), which would
                # make the console show FG=0 even when the DB has valid FG records.
                try:
                    if item.get("use_evo_db", True):
                        db_key_for_query = str(item.get("db_key") or item.get("song") or "").strip()
                        from gear_optimizer.data.database import get_db_connection_cached

                        conn = get_db_connection_cached()
                        row = conn.execute(
                            "SELECT best_fg_score FROM songs WHERE name = ?",
                            (db_key_for_query,),
                        ).fetchone()
                        if row is not None:
                            prev_best_fg = int(row[0] or 0)
                except Exception:
                    prev_best_fg = 0

                if prev_best_fg <= 0:
                    try:
                        prev_best_fg = int(item.get("db_best_fg_score", 0) or 0)
                    except Exception:
                        prev_best_fg = 0

                record_improved = (run_score > prev_best_score) or (run_best_fg > prev_best_fg)

                attempt_lifetime = 0
                try:
                    attempt_lifetime = int(item.get("attempt_lifetime", 0) or 0)
                except Exception:
                    attempt_lifetime = 0
                if attempt_lifetime <= 0 and isinstance(prev_record, dict):
                    try:
                        attempt_lifetime = int((prev_record.get("details") or {}).get("attempt_lifetime", 0) or 0) + 1
                    except Exception:
                        attempt_lifetime = 0
                if attempt_lifetime <= 0:
                    attempt_lifetime = 1

                prev_attempts_first = 0
                try:
                    prev_attempts_first = int(item.get("prev_attempts_first", 0) or 0)
                except Exception:
                    prev_attempts_first = 0
                if prev_attempts_first <= 0 and isinstance(prev_record, dict):
                    try:
                        prev_attempts_first = int((prev_record.get("details") or {}).get("attempts_first", 0) or 0)
                    except Exception:
                        prev_attempts_first = 0

                attempts_first = (
                    1 if record_improved else (int(prev_attempts_first or 0) + 1 if prev_attempts_first else 1)
                )
                db_best_fg_score = prev_best_fg

                _log_timing("deferred_payload_unpack", time.perf_counter() - _t_build0, song=item.get("song"))

                _t_dbpayload0 = time.perf_counter()
                cpu_t0 = time.process_time()
                db_payload = build_db_payload(
                    best_data,
                    best_gear,
                    best_minis,
                    prev_record,
                    attempt_lifetime,
                    attempts_first,
                    fg_variants,
                    build_details,
                    db_best_fg_score=db_best_fg_score,
                )
                _log_timing("build_db_payload", time.perf_counter() - _t_dbpayload0, song=item.get("song"))
                profiler.record("build_db_payload", time.process_time() - cpu_t0)

                _t_persist0 = time.perf_counter()
                cpu_t0 = time.process_time()
                persist_entries = build_persistence_entries(
                    db_payload,
                    item.get("ga_candidates") or [],
                    item.get("loadout_entries"),
                    build_details,
                )
                _log_timing("build_persistence_entries", time.perf_counter() - _t_persist0, song=item.get("song"))
                profiler.record("build_persistence_entries", time.process_time() - cpu_t0)

                # Crash-safe deferred FG: store GA candidates so FG can run later without rerunning GA.
                if item.get("_pending_fg_job") and item.get("use_evo_db", True):
                    try:
                        _t_upsert0 = time.perf_counter()
                        cpu_t0 = time.process_time()
                        async_db.submit_pending_fg_job(
                            item.get("db_key", item.get("song", "Unknown")),
                            item.get("ga_candidates") or [],
                        )
                        _log_timing(
                            "upsert_pending_fg_job_enqueue",
                            time.perf_counter() - _t_upsert0,
                            song=item.get("song"),
                        )
                        profiler.record("upsert_pending_fg_job_enqueue", time.process_time() - cpu_t0)
                    except Exception:
                        pass

                # Print results (including optional FG debug) in post process so GPU can move on.
                def _emit(_msg: str) -> None:
                    return

                if sync_output and item.get("_pending_fg_job"):
                    song_name_for_print = item.get("song", "Unknown")
                    pending_final_print[song_name_for_print] = {
                        "song": song_name_for_print,
                        "best_data": best_data,
                        "best_gear": best_gear,
                        "best_minis": best_minis,
                        "current_gear": item.get("current_gear") or [],
                        "current_minis": item.get("current_minis") or [],
                        "enable_gear": bool(item.get("enable_gear")),
                        "enable_mini": bool(item.get("enable_mini")),
                        "fg_debug": bool(item.get("fg_debug")),
                        "ref_arrays": item.get("ref_arrays"),
                        "calc_song": item.get("calc_song"),
                        "cfg": cfg,
                        "use_evo_db": bool(item.get("use_evo_db", True)),
                        "db_best_fg_score": int(item.get("db_best_fg_score", 0) or 0),
                        "_emit": _emit,
                    }
                    # If the FG update arrived first (unlikely but possible), print immediately.
                    if pending_fg_summary.get(song_name_for_print, {}).get("saw_fg_update"):
                        _print_pending_final(song_name_for_print)
                else:
                    try:
                        cpu_t0 = time.process_time()
                        _t_print0 = time.perf_counter()
                        print_results(
                            item.get("song", "Unknown"),
                            best_data,
                            best_gear,
                            best_minis,
                            item.get("current_gear") or [],
                            item.get("current_minis") or [],
                            bool(item.get("enable_gear")),
                            bool(item.get("enable_mini")),
                            fg_variants,
                            _emit,
                            fg_debug=bool(item.get("fg_debug")),
                            ref_arrays=item.get("ref_arrays"),
                            calc_song=item.get("calc_song"),
                            cfg=cfg,
                            db_best_fg_score=db_best_fg_score,
                        )
                        _log_timing("print_results", time.perf_counter() - _t_print0, song=item.get("song"))
                        profiler.record("print_results", time.process_time() - cpu_t0)
                    except Exception:
                        pass

                res = {
                    "song": item.get("song", "Unknown"),
                    "db_key": item.get("db_key", item.get("song", "Unknown")),
                    "db_payload": db_payload,
                    "persist_entries": persist_entries,
                    "log": item.get("log") or "",
                }

            song_name = res.get("song", "Unknown")
            db_key = res.get("db_key") or song_name

            # DB save
            if res.get("db_payload") and item.get("use_evo_db", True):
                persisted = res.get("persist_entries")
                if persisted:
                    valid_entries = [
                        e for e in persisted if e.get("score", 0) > 0 and (e.get("gear") or e.get("minis"))
                    ]
                    if valid_entries:
                        cpu_t0 = time.process_time()
                        _t_db0 = time.perf_counter()
                        # Offload SQLite work + counter updates so this post-process loop
                        # keeps draining `result_queue` (prevents GPU starvation via backpressure).
                        async_db.submit(
                            song_name,
                            valid_entries,
                            meta={
                                "db_key": db_key,
                                "_processed_run": True,
                                "file_path": item.get("file_path"),
                                "cfg_dict": item.get("cfg_dict") or {},
                                "ref_arrays": item.get("ref_arrays"),
                            },
                        )
                        _log_timing("save_loadouts_batch_enqueue", time.perf_counter() - _t_db0, song=song_name)
                        profiler.record("save_loadouts_batch_enqueue", time.process_time() - cpu_t0)
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
                                    "file_path": item.get("file_path"),
                                    "cfg_dict": item.get("cfg_dict") or {},
                                    "ref_arrays": item.get("ref_arrays"),
                                },
                            )
                        except Exception:
                            pass

            _log_timing("post_item_total", time.perf_counter() - _t_item0, song=song_name)
            profiler.record("post_item_total", time.process_time() - cpu_item_t0)

        except Exception as exc:
            failed += 1
            msg = f"[POST] Error: {type(exc).__name__}: {exc}"
            print(msg, file=sys.stderr)
            try:
                logging.error(msg + "\n" + traceback.format_exc())
            except Exception:
                pass

    # Flush pending DB work (best-effort) before the process exits so we don't leave
    # the main pipeline waiting on in-flight DB tasks.
    try:
        async_db.shutdown(timeout=30.0)
    except Exception:
        pass

    try:
        if pending_final_print:
            for song_name in list(pending_final_print.keys()):
                _print_pending_final(song_name)

        if failed > 0:
            print(f"[POST][SUMMARY] {failed}/{max(1, total)} songs failed.")
    except Exception:
        pass

    try:
        profiler.emit()
    except Exception:
        pass
