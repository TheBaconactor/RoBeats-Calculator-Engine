from __future__ import annotations

import configparser
import logging
import os
import traceback
import time
import sys

from gear_optimizer.core.utils import cfg_from_dict, safe_int
from gear_optimizer.data.database import init_db, save_loadouts_batch
from gear_optimizer.data.discord_reporter import DiscordReporter, build_stats_summary
from gear_optimizer.helpers.song_helpers.persistence import (
    build_db_payload,
    build_persistence_entries,
)
from gear_optimizer.helpers.song_helpers.results_printer import print_results


def _setup_discord_reporter() -> DiscordReporter:
    try:
        from dotenv import load_dotenv
    except Exception:
        load_dotenv = None

    # Mirror GearOptimizerApp.setup_discord()
    try:
        from gear_optimizer.core.constants import PATHS

        env_path = PATHS.discord_env
        if load_dotenv is not None:
            if os.path.exists(env_path):
                load_dotenv(env_path)
            else:
                load_dotenv()
    except Exception:
        pass

    token = os.getenv("DISCORD_TOKEN")
    logging_channel_id = safe_int(os.getenv("LOGGINGCHANNEL"), 0) or None
    stats_channel_id = safe_int(os.getenv("STATSCHANNEL"), 0) or None
    return DiscordReporter(
        token,
        log_channel_id=logging_channel_id,
        stats_channel_id=stats_channel_id,
        stats_batch_size=500,
    )


def _build_details_fn(primary_color: str, secondary_color: str, effective_difficulty: str):
    def build_details(data_dict: dict) -> dict:
        if not data_dict:
            return {}
        return {
            "FT": data_dict.get("FT", 0),
            "FF": data_dict.get("FF", 0),
            "GemCounts": data_dict.get("GemCounts", {}),
            "Stats": data_dict.get("Stats", {}),
            "SelectedElement": data_dict.get("Selected Element", ""),
            "PrimaryColor": primary_color,
            "SecondaryColor": secondary_color,
            "Difficulty": effective_difficulty,
            "ForceGreats": data_dict.get("ForceGreats", {}),
        }

    return build_details


def run_post_processor(result_queue, total_tasks: int | None = None) -> None:
    """
    Background post-processor for sequential pipeline mode.

    Consumes per-song compute payloads and performs CPU-heavy work:
    - Build DB payload + persistence entries
    - Print results / debug output
    - Persist to SQLite
    - Send Discord stats/logs
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

    try:
        init_db()
    except Exception:
        pass

    reporter = _setup_discord_reporter()

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

        try:
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
            )
            _log_timing("print_results", time.perf_counter() - _t_print0, song=song)
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
            _t_item0 = time.perf_counter()
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
                        _t_db0 = time.perf_counter()
                        save_loadouts_batch(db_key, valid_entries)
                        _log_timing("fg_save_loadouts_batch", time.perf_counter() - _t_db0, song=song_name)
                    else:
                        if persisted:
                            print(f"[DB] Skipped FG update for {song_name}: no valid entries")

                    try:
                        from gear_optimizer.data.database import delete_pending_fg_job

                        _t_del0 = time.perf_counter()
                        delete_pending_fg_job(db_key)
                        _log_timing("fg_delete_pending_job", time.perf_counter() - _t_del0, song=song_name)
                    except Exception:
                        pass

                fg_state["saved_count"] = len(valid_entries)
                try:
                    fg_state["best_fg"] = max(int(e.get("fg_score", 0) or 0) for e in valid_entries)
                except Exception:
                    fg_state["best_fg"] = 0
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
                print(msg)
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
            print(msg)
            try:
                logging.error(msg)
                if item.get("_trace"):
                    logging.error(item.get("_trace"))
            except Exception:
                pass
            try:
                reporter.send_log(msg)
            except Exception:
                pass
            continue

        completed += 1

        try:
            _t_item0 = time.perf_counter()
            res = item
            if isinstance(item, dict) and item.get("_deferred_post"):
                _t_build0 = time.perf_counter()
                cfg_dict = item.get("cfg_dict") or {}
                cfg = cfg_from_dict(cfg_dict) if cfg_dict else configparser.ConfigParser()

                primary = str(item.get("meta_primary_color") or "")
                secondary = str(item.get("meta_secondary_color") or "")
                difficulty = str(item.get("difficulty") or "Unknown")
                build_details = _build_details_fn(primary, secondary, difficulty)

                best_data = item.get("best_data") or {}
                best_gear = item.get("best_gear") or []
                best_minis = item.get("best_minis") or []
                prev_record = item.get("prev_record")
                attempt_lifetime = int(item.get("attempt_lifetime") or 0)
                prev_attempts_first = int(item.get("prev_attempts_first") or 0)
                fg_variants = item.get("fg_variants") or []
                db_best_fg_score = item.get("db_best_fg_score")

                _log_timing("deferred_payload_unpack", time.perf_counter() - _t_build0, song=item.get("song"))

                _t_dbpayload0 = time.perf_counter()
                db_payload = build_db_payload(
                    best_data,
                    best_gear,
                    best_minis,
                    prev_record,
                    attempt_lifetime,
                    prev_attempts_first,
                    fg_variants,
                    build_details,
                    db_best_fg_score=db_best_fg_score,
                )
                _log_timing("build_db_payload", time.perf_counter() - _t_dbpayload0, song=item.get("song"))

                _t_persist0 = time.perf_counter()
                persist_entries = build_persistence_entries(
                    db_payload,
                    item.get("ga_candidates") or [],
                    item.get("loadout_entries"),
                    build_details,
                )
                _log_timing("build_persistence_entries", time.perf_counter() - _t_persist0, song=item.get("song"))

                # Crash-safe deferred FG: store GA candidates so FG can run later without rerunning GA.
                if item.get("_pending_fg_job") and item.get("use_evo_db", True):
                    try:
                        from gear_optimizer.data.database import upsert_pending_fg_job

                        _t_upsert0 = time.perf_counter()
                        upsert_pending_fg_job(
                            item.get("db_key", item.get("song", "Unknown")),
                            item.get("ga_candidates") or [],
                        )
                        _log_timing("upsert_pending_fg_job", time.perf_counter() - _t_upsert0, song=item.get("song"))
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
                        "_emit": _emit,
                    }
                    # If the FG update arrived first (unlikely but possible), print immediately.
                    if pending_fg_summary.get(song_name_for_print, {}).get("saw_fg_update"):
                        _print_pending_final(song_name_for_print)
                else:
                    try:
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
                        )
                        _log_timing("print_results", time.perf_counter() - _t_print0, song=item.get("song"))
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
                        _t_db0 = time.perf_counter()
                        save_loadouts_batch(db_key, valid_entries)
                        _log_timing("save_loadouts_batch", time.perf_counter() - _t_db0, song=song_name)
                    else:
                        print(f"[DB] Skipped save for {song_name}: no valid entries")

            # Discord stats/log
            if total > 0:
                try:
                    _t_stats0 = time.perf_counter()
                    reporter.send_stats(build_stats_summary(res, completed, total))
                    _log_timing("discord_send_stats", time.perf_counter() - _t_stats0, song=song_name)
                except Exception:
                    pass
            log_content = (res.get("log") or "").strip()
            if log_content:
                tail = log_content[-3000:] if len(log_content) > 3000 else log_content
                try:
                    _t_log0 = time.perf_counter()
                    reporter.send_log(f"Log for {song_name}:\n{tail}")
                    _log_timing("discord_send_log", time.perf_counter() - _t_log0, song=song_name)
                except Exception:
                    pass
            _log_timing("post_item_total", time.perf_counter() - _t_item0, song=song_name)

        except Exception as exc:
            failed += 1
            msg = f"[POST] Error: {type(exc).__name__}: {exc}"
            print(msg)
            try:
                logging.error(msg + "\n" + traceback.format_exc())
            except Exception:
                pass
            try:
                reporter.send_log(msg)
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
        reporter.shutdown(timeout=10.0)
    except Exception:
        pass
