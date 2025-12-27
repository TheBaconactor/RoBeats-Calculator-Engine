from __future__ import annotations

import configparser
import logging
import os
import traceback

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
    try:
        init_db()
    except Exception:
        pass

    reporter = _setup_discord_reporter()

    completed = 0
    failed = 0
    total = int(total_tasks or 0)

    while True:
        try:
            item = result_queue.get()
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
            res = item
            if isinstance(item, dict) and item.get("_deferred_post"):
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

                persist_entries = build_persistence_entries(
                    db_payload,
                    item.get("ga_candidates") or [],
                    item.get("loadout_entries"),
                    build_details,
                )

                # Print results (including optional FG debug) in post process so GPU can move on.
                def _emit(_msg: str) -> None:
                    return

                try:
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
                        e
                        for e in persisted
                        if e.get("score", 0) > 0 and (e.get("gear") or e.get("minis"))
                    ]
                    if valid_entries:
                        save_loadouts_batch(db_key, valid_entries)
                    else:
                        print(f"[DB] Skipped save for {song_name}: no valid entries")

            # Discord stats/log
            if total > 0:
                try:
                    reporter.send_stats(build_stats_summary(res, completed, total))
                except Exception:
                    pass
            log_content = (res.get("log") or "").strip()
            if log_content:
                tail = log_content[-3000:] if len(log_content) > 3000 else log_content
                try:
                    reporter.send_log(f"Log for {song_name}:\n{tail}")
                except Exception:
                    pass

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
        if failed > 0:
            print(f"[POST][SUMMARY] {failed}/{max(1, total)} songs failed.")
    except Exception:
        pass

    try:
        reporter.shutdown(timeout=10.0)
    except Exception:
        pass
