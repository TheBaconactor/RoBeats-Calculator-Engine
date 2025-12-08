#!/usr/bin/env python3
"""
Gear Optimizer - Main Entry Point

This is the refactored main module that orchestrates the complete optimization workflow.
Previously contained in a 5,196-line monolith, now cleanly organized into focused modules.
"""

import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import configparser
import gc
import json
import logging
import multiprocessing
import os
import re
import sys
import threading
import time

import numpy as np

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(_path=None):
        return False

try:
    import requests
except ImportError:
    requests = None

# Import from refactored modules
from gear_optimizer.constants import PATHS, SCRIPT_DIR, BIN_DIR, TOTAL_ROWS
from gear_optimizer.config import (
    write_metafinder_status,
    compute_memory_guard_limit,
    load_paths_cache,
)
from gear_optimizer.database import (
    init_db,
    save_loadouts_batch,
    get_db_connection,
    get_evolution_db_path,
)
from gear_optimizer.memory import (
    set_memory_watchdog_limit,
    memory_release_requested,
    get_memory_release_message,
    build_memory_guard_resume_context,
    load_memory_guard_resume_queue,
    MemoryGuardResumeTracker,
    restart_process_for_memory_guard,
    MEMORY_GUARD_RESUME_FILE,
)
from gear_optimizer.discord_reporter import DiscordReporter, build_stats_summary
from gear_optimizer.song_processor import safe_process_song_task, scan_song_header
from gear_optimizer.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from gear_optimizer.utils import safe_int, cfg_to_dict
from gear_optimizer.scoring import FEVER_TIMELINE_CACHE, FG_CACHE
from gear_optimizer.genetic import GEM_SOLVER_CACHE


# --- Setup Directories and Logging ---
os.makedirs(BIN_DIR, exist_ok=True)
log_file_path = os.path.join(BIN_DIR, "error.log")
logging.basicConfig(
    filename=log_file_path,
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# --- Environment (Discord + external paths) ---
STATUS_FILE = PATHS.status_file
ENV_PATH = PATHS.discord_env
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LOGGING_CHANNEL_ID = safe_int(os.getenv("LOGGINGCHANNEL"), 0) or None
STATS_CHANNEL_ID = safe_int(os.getenv("STATSCHANNEL"), 0) or None
EVOLUTION_DB_PATH = os.getenv("EVOLUTION_DB_PATH") or PATHS.evolution_db_default

# Initialize Discord reporter
discord_reporter = DiscordReporter(
    DISCORD_TOKEN,
    log_channel_id=LOGGING_CHANNEL_ID,
    stats_channel_id=STATS_CHANNEL_ID,
)


# --- Main Execution ---
if __name__ == "__main__":
    multiprocessing.freeze_support()

    # BUG FIX: Validate status file path and show where it's writing
    print(f"[MetaFinder] Status file path: {STATUS_FILE}")
    try:
        # Test write to verify the path is accessible
        status_dir = os.path.dirname(STATUS_FILE)
        if not os.path.exists(status_dir):
            print(f"[MetaFinder] Creating status directory: {status_dir}")
        os.makedirs(status_dir, exist_ok=True)

        # Test write
        test_payload = {"test": True, "timestamp": time.time()}
        with open(STATUS_FILE + ".test", "w") as f:
            json.dump(test_payload, f)
        os.remove(STATUS_FILE + ".test")
        print(f"[MetaFinder] Status file path verified successfully")
    except Exception as e:
        print(f"[MetaFinder] WARNING: Cannot write to status file: {e}")
        print(f"[MetaFinder] Status updates will fail. Check path or set METAFINDER_STATUS_FILE env variable.")

    # Mark MetaFinder as online as soon as the main loop starts.
    write_metafinder_status("online", "MetaFinder process started")

    # Background heartbeat so the website can treat stale timestamps as offline
    _heartbeat_stop = threading.Event()

    def _heartbeat_loop():
        while not _heartbeat_stop.is_set():
            try:
                write_metafinder_status("online", "MetaFinder heartbeat")
            except Exception:
                pass
            # Sleep with interrupt support
            _heartbeat_stop.wait(60.0)

    try:
        threading.Thread(target=_heartbeat_loop, daemon=True).start()
    except Exception:
        # If heartbeat thread fails to start, we still continue the main loop.
        pass
    while True:
        loop_forever = False
        memory_guard_restart = False
        memory_resume_tracker = None
        start_time = time.time()

        # --- MEMORY LEAK FIX: Clear main process caches at start of each loop iteration ---
        # In LoopForever mode, these global caches can accumulate data across iterations.
        # Worker processes clear their own caches, but the main process must also clear them.
        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()
        FG_CACHE.clear()

        # Track manager/queue for cleanup in finally block
        manager = None
        status_queue = None
        status_thread = None

        try:
            cfg = configparser.ConfigParser()
            # Explicit UTF-8-SIG to avoid Windows default 'charmap' decoding issues
            cfg.read("config.ini", encoding="utf-8-sig")
            paths = load_paths_cache()
            set_memory_watchdog_limit(compute_memory_guard_limit(cfg))
            db_display_name = os.path.basename(get_evolution_db_path())
            discord_reporter.send_log(
                f"Gear Optimizer run started. DB file: {db_display_name}"
            )

            # --- DB LOAD (always, independent of UseEvolutionDB) ---
            init_db()

            # --- AUTO-MERGE SECONDARY DATABASES ---
            # Automatically find and merge any secondary .db files in the same directory
            try:
                from gear_optimizer.db_merge import auto_merge_secondary_databases
                merge_success, merge_message = auto_merge_secondary_databases(
                    delete_after_merge=True,  # Delete after successful merge
                    backup_before_merge=True  # Create backup before first merge
                )
                if merge_success and "No secondary databases" not in merge_message:
                    print(f"[DB Merge] {merge_message}")
                    discord_reporter.send_log(f"Database merge: {merge_message}")
                elif not merge_success:
                    print(f"[DB Merge] Warning: {merge_message}")
                    logging.warning(f"[DB Merge] {merge_message}")
            except Exception as e:
                logging.error(f"[DB Merge] Unexpected error: {e}")
                print(f"[DB Merge] Error: {e}")

            # --- Configuration Granularity ---
            meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
            enable_fever = enable_mini = enable_gear = bool(meta_finder)
            force_greats_mode = cfg.getboolean("IterationEngine", "ForceGreatsMode", fallback=False)
            force_greats_finder = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
            auto_buff = cfg.getboolean(
                "IterationEngine", "AutoSelectBuffAndColor", fallback=False
            )

            # Log ForceGreats configuration status
            if force_greats_mode:
                fg_status = "ForceGreatsFinder" if force_greats_finder else "Manual Config"
                print(f" >> [ForceGreats] Mode enabled ({fg_status})")
            ga_depth = safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=50))
            use_evo_db = cfg.getboolean(
                "IterationEngine", "UseEvolutionDB", fallback=True
            )
            loop_forever = cfg.getboolean(
                "IterationEngine", "LoopForever", fallback=False
            )
            eval_cpu_limit = safe_int(
                cfg.get("IterationEngine", "EvalCPUCores", fallback=0)
            )

            stats_path = paths.get("Stats", "")
            if not stats_path:
                stats_path = PATHS.stats_csv
            stats_table = read_table(stats_path)

            # --- CRITICAL FIX: PREVENT DB TAINTING ---
            # If any automation is active, FORCE manual gem inputs to 0 in memory.
            # This ensures the solver runs on a clean slate and the DB saves the "Pure" result.
            if enable_fever or enable_mini or enable_gear:
                print(" >> [Auto-Mode] Finders active: Ignoring manual [UserInputStatsGems] & [ElementalGems] to prevent database tainting.")

                if not cfg.has_section("UserInputStatsGems"):
                    cfg.add_section("UserInputStatsGems")
                cfg.set("UserInputStatsGems", "perfect_points", "0")
                cfg.set("UserInputStatsGems", "combo_multiplier", "0")
                cfg.set("UserInputStatsGems", "fever_multiplier", "0")
                cfg.set("UserInputStatsGems", "fever_fill", "0")
                cfg.set("UserInputStatsGems", "fever_time", "0")

                if not cfg.has_section("ElementalGems"):
                    cfg.add_section("ElementalGems")
                cfg.set("ElementalGems", "Chill", "0")
                cfg.set("ElementalGems", "Flow", "0")
                cfg.set("ElementalGems", "Rush", "0")
                cfg.set("ElementalGems", "Beat", "0")
                cfg.set("ElementalGems", "Vibe", "0")

            # Initialize variables at function scope to prevent NameError in cleanup paths
            # (CRITICAL FIX: Variables must be accessible in all code paths for cleanup)
            # BUG FIX: Explicitly initialize all variables that might persist across loop iterations
            future_map = None
            remaining_tasks = None
            completed_songs = None
            tasks = None

            # OPTIMIZATION: Pre-load References as NumPy arrays ONCE
            stat_names = [
                "Perfect Points",
                "Combo Multiplier",
                "Fever Multiplier",
                "Fever Fill Rate",
                "Fever Time",
            ]
            ref_arrays = {}
            for i, name in enumerate(stat_names):
                temp_list = []
                for v in range(TOTAL_ROWS + 1):
                    lookup_index = TOTAL_ROWS - v
                    try:
                        val = stats_table[lookup_index][i] if stats_table else 0
                    except Exception:
                        val = 0
                    temp_list.append(val)
                ref_arrays[name] = np.array(temp_list, dtype=np.float64)

            # OPTIMIZATION: Pre-load Gears and Minis ONCE
            all_gears = load_all_gears_list(paths)
            all_minis = load_all_minis_list(paths)
            gears_by_name = {g["Name"]: g for g in all_gears}
            minis_by_name = {m["Name"]: m for m in all_minis}

            diff = cfg.get("CalculateSong", "Difficulty", fallback="Hard")
            search_dir = paths.get(diff, SCRIPT_DIR)
            diff_lower = diff.strip().lower()
            filter_search = cfg.get("CalculateSong", "Song_Name", fallback="").strip().lower()

            def _parse_color_targets(raw_val):
                tokens = [
                    c.strip().lower()
                    for c in re.split(r"[,\|/]", raw_val or "")
                    if c and c.strip()
                ]
                is_all = not tokens or any(c in ("all", "any", "*") for c in tokens)
                return is_all, set() if is_all else set(tokens)

            target_primary_raw = cfg.get("CalculateSong", "TargetPrimary", fallback="")
            target_secondary_raw = cfg.get("CalculateSong", "TargetSecondary", fallback="")
            legacy_target_raw = cfg.get("CalculateSong", "TargetColor", fallback="")
            if not target_primary_raw and legacy_target_raw:
                target_primary_raw = legacy_target_raw
            if not target_secondary_raw:
                target_secondary_raw = "all"

            target_primary_all, target_primary_colors = _parse_color_targets(
                target_primary_raw
            )
            target_secondary_all, target_secondary_colors = _parse_color_targets(
                target_secondary_raw
            )
            resume_context = build_memory_guard_resume_context(
                diff_lower,
                filter_search,
                target_primary_all,
                target_primary_colors,
                target_secondary_all,
                target_secondary_colors,
            )

            diff_dirs = {}
            for key in ("Easy", "Normal", "Hard"):
                base_path = paths.get(key)
                if base_path:
                    norm = os.path.abspath(base_path).lower().rstrip("\\/") + os.sep
                    diff_dirs[key.lower()] = norm

            song_queue = []
            seen_paths = set()

            # If "All" is selected, search the entire Data folder.
            # Otherwise, search the specific difficulty folder from paths.
            if diff_lower not in ("easy", "normal", "hard"):
                # Search everything in Data/ if possible, or just SCRIPT_DIR
                data_root = PATHS.data_dir
                dirs_to_search = [data_root] if os.path.exists(data_root) else [SCRIPT_DIR]
            else:
                dirs_to_search = [search_dir]

            for d in dirs_to_search:
                if not os.path.exists(d):
                    continue
                for root, _, files in os.walk(d):
                    for f in files:
                        if f.lower().endswith(".txt"):
                            fp = os.path.join(root, f)
                            abs_fp = os.path.abspath(fp)
                            if abs_fp in seen_paths:
                                continue

                            meta = scan_song_header(fp)
                            if not meta:
                                continue

                            # --- ROBUST METADATA PARSING ---
                            # Trust the file content. The Song Name usually contains the difficulty
                            # (e.g. "Song (Hard) by Artist").
                            name = meta["Song Name"]
                            name_lower = name.lower()

                            # Extract difficulty from the song name if possible, or use the Difficulty field
                            # The Difficulty field is often a number (e.g. "10"), so checking for "Hard" text is better.
                            detected_diff = "Unknown"
                            if "(hard)" in name_lower:
                                detected_diff = "Hard"
                            elif "(normal)" in name_lower:
                                detected_diff = "Normal"
                            elif "(easy)" in name_lower:
                                detected_diff = "Easy"
                            else:
                                # Fallback to the Difficulty header if it's a word
                                meta_diff_val = (meta.get("Difficulty") or "").strip().capitalize()
                                if meta_diff_val in ("Hard", "Normal", "Easy"):
                                    detected_diff = meta_diff_val

                            # --- FILTERING ---
                            # 1. Difficulty Filter
                            if diff_lower in ("easy", "normal", "hard"):
                                # If user requested specific difficulty, ensure this song matches
                                if detected_diff.lower() != diff_lower:
                                    continue

                            # 2. Color Filter
                            primary_color = (meta.get("Primary Color") or "").strip().lower()
                            secondary_color = (meta.get("Secondary Color") or "").strip().lower()

                            if (
                                not target_primary_all
                                and (
                                    not primary_color
                                    or primary_color not in target_primary_colors
                                )
                            ):
                                continue
                            if (
                                not target_secondary_all
                                and (
                                    not secondary_color
                                    or secondary_color not in target_secondary_colors
                                )
                            ):
                                continue

                            # 3. Name Search Filter
                            if filter_search and filter_search not in name_lower:
                                continue

                            # Store full metadata to avoid re-scanning later
                            song_queue.append((fp, name, detected_diff))
                            seen_paths.add(abs_fp)

            resume_seed_queue = load_memory_guard_resume_queue(resume_context)
            if resume_seed_queue:
                print(
                    f"[MemoryGuard] Resuming {len(resume_seed_queue)} song(s) from previous interrupted run."
                )
                song_queue = resume_seed_queue

            if not song_queue:
                print("Error: No matching songs found.")
            else:
                if not filter_search:
                    # Fetch existing songs from DB
                    existing_songs = set()
                    if use_evo_db:
                        try:
                            conn = get_db_connection()
                            cursor = conn.execute("SELECT name FROM songs")
                            existing_songs = {row[0] for row in cursor}
                            # Memory leak fix #2: Checkpoint WAL before closing connection
                            try:
                                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                                conn.execute("PRAGMA optimize")
                            except Exception as e:
                                # CRITICAL FIX: Log checkpoint failures (was silently suppressed)
                                logging.warning(f"[DB] WAL checkpoint/optimize failed: {e}")
                            conn.close()
                        except Exception as e:
                            print(f"[DB] Error fetching existing songs: {e}")

                    missing = []
                    completed = []
                    for fp, meta_name, song_diff in song_queue:
                        # Song name already contains difficulty like "(Hard)" or "(Easy)"
                        # Use song name directly as lookup key
                        lookup_key = meta_name

                        # Skip _meta key when checking for completion
                        if lookup_key in existing_songs:
                            completed.append((fp, meta_name, song_diff))
                        else:
                            missing.append((fp, meta_name, song_diff))
                    if missing:
                        print(f"Auto-selection: {len(missing)} song(s) without DB records found; prioritizing those.")
                        song_queue = missing
                    else:
                        print("All songs have DB records; processing full list.")

                print(f"Found {len(song_queue)} songs to process.")

                discord_reporter.send_log(f"Queued {len(song_queue)} song(s) for processing.")

                memory_resume_tracker = MemoryGuardResumeTracker(MEMORY_GUARD_RESUME_FILE)
                memory_resume_tracker.prime(song_queue, resume_context)

                status_queue = None
                status_thread = None
                manager = multiprocessing.Manager()
                status_queue = manager.Queue()

                def _safe_sequential_gen(task_list):
                    for t in task_list:
                        try:
                            yield safe_process_song_task(t)
                        except Exception as seq_err:
                            yield {"_error": seq_err, "_song_name": t[1]}

                def _status_listener(q):
                    while True:
                        try:
                            msg = q.get()
                        except (EOFError, BrokenPipeError, OSError):
                            break
                        if msg is None:
                            break
                        print(msg, flush=True)
                        discord_reporter.send_log(str(msg))

                status_thread = threading.Thread(
                    target=_status_listener, args=(status_queue,), daemon=True
                )
                status_thread.start()

                cfg_dict = cfg_to_dict(cfg)

                tasks = []
                logical_cpus = os.cpu_count() or 1
                available_cpus = logical_cpus
                if eval_cpu_limit and eval_cpu_limit > 0:
                    available_cpus = max(1, min(logical_cpus, eval_cpu_limit))
                else:
                    available_cpus = max(1, available_cpus)
                if available_cpus != logical_cpus:
                    print(
                        f"EvalCPUCores cap applied: using {available_cpus} of {logical_cpus} cores."
                    )
                parallel_workers = 1  # Single-threaded per song to avoid nested pools on Windows

                for fp, found_song_name, task_diff in song_queue:
                    print(f"[QUEUE] {found_song_name}")
                    # Song name already includes difficulty like "(Hard)" or "(Easy)", use directly as key
                    tasks.append(
                        (
                            fp,
                            found_song_name,
                            task_diff,  # Pass the determined difficulty
                            cfg_dict,
                            paths,
                            ref_arrays,
                            all_gears,
                            all_minis,
                            gears_by_name,
                            minis_by_name,
                            use_evo_db,
                            auto_buff,
                            ga_depth,
                            status_queue,
                            parallel_workers,
                        )
                    )

                def _consume_results(
                    results_iter,
                    future_map=None,
                    propagate_broken_pool=False,
                    completed_songs=None,
                    completed_offset=0,
                ):
                    total = len(tasks)
                    completed = completed_offset
                    failed = 0
                    for item in results_iter:
                        completed += 1
                        # Handle Future objects (from ProcessPoolExecutor) with exception safety
                        if future_map is not None:
                            future = item
                            song_name = future_map.get(future, "Unknown")
                            try:
                                res = future.result()
                            except Exception as task_err:
                                failed += 1
                                err_msg = f"[{completed}/{total}] FAILED: {song_name} - {type(task_err).__name__}: {task_err}"
                                print(err_msg)
                                logging.error(err_msg)
                                discord_reporter.send_log(err_msg)
                                if propagate_broken_pool and isinstance(task_err, BrokenProcessPool):
                                    # Bubble up to trigger auto-recovery fallback
                                    raise
                                continue  # Skip this song and continue with the queue
                        else:
                            # Sequential processing - item is already the result (or error dict)
                            res = item
                            # Check if this is an error placeholder from _safe_sequential_gen
                            if isinstance(res, dict) and "_error" in res:
                                failed += 1
                                task_err = res["_error"]
                                song_name = res.get("_song_name", "Unknown")
                                err_msg = f"[{completed}/{total}] FAILED: {song_name} - {type(task_err).__name__}: {task_err}"
                                print(err_msg)
                                logging.error(err_msg)
                                discord_reporter.send_log(err_msg)
                                continue
                            # Normal sequential result; derive song name from payload
                            song_name = res.get("song", "Unknown")

                        # Track completed songs so we can avoid re-processing them in fallback
                        if completed_songs is not None and song_name:
                            completed_songs.add(song_name)
                        if memory_resume_tracker:
                            memory_resume_tracker.mark_completed(song_name)

                        # After finishing this song, bail out if MemoryGuard fired
                        if memory_release_requested():
                            print("[MemoryGuard] Early stop in _consume_results; "
                                  "leaving remaining songs for resume.")
                            break

                        print(f"[{completed}/{total}] Completed: {res['song']}")
                        print("=" * 60)
                        print(f"PROCESSING SONG: {res['song']}")
                        print("=" * 60)
                        discord_reporter.send_stats(build_stats_summary(res, completed, total))
                        # Logs already streamed live via Tee; buffer retained for completeness
                        if use_evo_db:
                            persisted = res.get("persist_entries")
                            if persisted:
                                save_loadouts_batch(res["song"], persisted)
                            else:
                                db_payload = res.get("db_payload")
                                if db_payload:
                                    save_loadouts_batch(res["song"], [{
                                        "score": db_payload.get("score", 0),
                                        "fg_score": db_payload.get("fg_score", 0),
                                        "gear": db_payload.get("gear", []),
                                        "minis": db_payload.get("minis", []),
                                        "details": db_payload.get("details", {}),
                                        "force": db_payload.get("force"),
                                    }])
                        log_content = (res.get("log") or "").strip()
                        if log_content:
                            discord_reporter.send_log(f"Log for {res.get('song', 'Unknown Song')} ({completed}/{total}):")
                            # Avoid Discord spam: keep only the tail of very long logs.
                            tail = log_content[-3000:] if len(log_content) > 3000 else log_content
                            discord_reporter.send_log(tail)

                        # Memory leak fix: Clear large result fields immediately after use
                        # These can accumulate 10-100MB per song (log buffers, persist data)
                        res["log"] = None
                        if "persist_entries" in res:
                            res["persist_entries"] = None
                        if "db_payload" in res:
                            res["db_payload"] = None
                    if failed > 0:
                        print(f"[SUMMARY] {failed}/{total} songs failed during processing.")

                # Plan parallelism across songs, capped by EvalCPUCores and per-song worker usage.
                song_worker_limit = max(1, available_cpus // max(1, parallel_workers))
                max_workers = max(1, min(len(tasks), song_worker_limit))
                print(
                    f"Parallel plan -> songs: {len(tasks)}, concurrent workers: {max_workers}, cores per song: {parallel_workers}"
                )
                print(f"Using {available_cpus} logical CPU cores")
                if len(tasks) > 1 and max_workers > 1:
                    # Track which songs completed successfully in the pool, so we can
                    # avoid re-processing them if we need to fall back to sequential.
                    completed_songs = set()

                    max_pool_retries = 3
                    broken_pool_failures = 0
                    remaining_tasks = list(tasks)
                    current_worker_cap = max_workers

                    def _run_sequential(pending_tasks, completed_offset=0):
                        if not pending_tasks:
                            return
                        _consume_results(
                            _safe_sequential_gen(pending_tasks),
                            future_map=None,
                            completed_songs=completed_songs,
                            completed_offset=completed_offset,
                        )

                    while remaining_tasks:
                        completed_offset = len(completed_songs)
                        effective_workers = max(
                            1, min(len(remaining_tasks), current_worker_cap)
                        )

                        # Use spawn everywhere to avoid fork-related state bleed across platforms.
                        try:
                            mp_ctx = multiprocessing.get_context("spawn")
                        except ValueError:
                            mp_ctx = multiprocessing.get_context()

                        if effective_workers == 1:
                            _run_sequential(remaining_tasks, completed_offset)
                            break

                        try:
                            with concurrent.futures.ProcessPoolExecutor(
                                max_workers=effective_workers,
                                mp_context=mp_ctx,
                            ) as executor:
                                future_map = {
                                    executor.submit(safe_process_song_task, t): t[1]
                                    for t in remaining_tasks
                                }
                                _consume_results(
                                    concurrent.futures.as_completed(future_map),
                                    future_map=future_map,
                                    propagate_broken_pool=True,
                                    completed_songs=completed_songs,
                                    completed_offset=completed_offset,
                                )

                                if memory_release_requested():
                                    print("[MemoryGuard] Stopping parallel loop after soft limit; "
                                          "not scheduling more songs in this run.")
                                    break
                        except BrokenProcessPool as bpp:
                            broken_pool_failures += 1
                            warn_msg = (
                                f"[Auto-Recover] Process pool broke while processing songs; "
                                f"attempt {broken_pool_failures}/{max_pool_retries}. "
                                f"Retrying remaining {len(remaining_tasks)} song(s) with up to "
                                f"{max(1, effective_workers - 1)} workers. Reason: {bpp}"
                            )
                            print(warn_msg)
                            logging.error(warn_msg)
                            discord_reporter.send_log(warn_msg)

                            # BUG FIX: Restart status_thread and manager after pool crash
                            # The old manager/queue may be in a broken state
                            print("[Auto-Recover] Restarting status_thread and manager...")
                            try:
                                # Stop old status_thread
                                if status_queue is not None:
                                    try:
                                        status_queue.put(None)
                                    except Exception:
                                        pass
                                if status_thread is not None:
                                    try:
                                        status_thread.join(timeout=2)
                                    except Exception:
                                        pass
                                # Shutdown old manager
                                if manager is not None:
                                    try:
                                        manager.shutdown()
                                    except Exception:
                                        pass

                                # Memory leak fix #4: Explicitly destroy old manager before creating new one
                                # Prevents 6-15 MB accumulation per pool crash
                                old_manager = manager
                                manager = None
                                status_queue = None
                                try:
                                    del old_manager
                                except (NameError, AttributeError):
                                    pass
                                gc.collect(generation=0)

                                # Create new manager and status_queue
                                manager = multiprocessing.Manager()
                                status_queue = manager.Queue()

                                # Restart status_thread
                                status_thread = threading.Thread(
                                    target=_status_listener, args=(status_queue,), daemon=True
                                )
                                status_thread.start()

                                print("[Auto-Recover] Status thread and manager restarted successfully.")
                            except Exception as restart_err:
                                print(f"[Auto-Recover] Warning: Failed to restart status infrastructure: {restart_err}")
                                # Continue anyway - status reporting is non-critical

                            # Rebuild remaining_tasks with new status_queue
                            remaining_songs = [t for t in tasks if t[1] not in completed_songs]
                            remaining_tasks = []
                            for fp, found_song_name, task_diff, *rest in remaining_songs:
                                # Rebuild task tuple with new status_queue
                                remaining_tasks.append((
                                    fp,
                                    found_song_name,
                                    task_diff,
                                    cfg_dict,
                                    paths,
                                    ref_arrays,
                                    all_gears,
                                    all_minis,
                                    gears_by_name,
                                    minis_by_name,
                                    use_evo_db,
                                    auto_buff,
                                    ga_depth,
                                    status_queue,  # New status_queue
                                    parallel_workers,
                                ))

                            current_worker_cap = max(1, effective_workers - 1)

                            if broken_pool_failures >= max_pool_retries:
                                fallback_msg = (
                                    "[Auto-Recover] Max pool retries hit; running remaining songs sequentially."
                                )
                                print(fallback_msg)
                                logging.error(fallback_msg)
                                discord_reporter.send_log(fallback_msg)
                                _run_sequential(
                                    remaining_tasks,
                                    completed_offset=len(completed_songs),
                                )
                                break

                            continue

                        break

                # Memory leak fix: Clear task lists after parallel processing completes
                # These accumulate 2MB per song in task tuples (ref_arrays, all_gears, all_minis)
                try:
                    if future_map is not None:
                        future_map.clear()
                except (NameError, AttributeError):
                    pass
                try:
                    if remaining_tasks is not None:
                        remaining_tasks.clear()
                except (NameError, AttributeError):
                    pass

                else:
                    # Sequential processing with per-song exception handling
                    _consume_results(_safe_sequential_gen(tasks), future_map=None)

                # Memory leak fix: Clear tasks list after consumption
                try:
                    if tasks is not None:
                        tasks.clear()
                except (NameError, AttributeError):
                    pass

                # Memory leak fix #1: Clear large reference data after task processing
                # These structures persist 5-51 MB per batch and are not reused
                try:
                    del ref_arrays, all_gears, all_minis, gears_by_name, minis_by_name
                    gc.collect(generation=0)
                except (NameError, AttributeError):
                    pass

                if status_queue:
                    status_queue.put(None)
                    if status_thread:
                        status_thread.join(timeout=2)
                    if manager:
                        manager.shutdown()
                discord_reporter.send_log("All queued songs processed.")
                if memory_resume_tracker:
                    memory_resume_tracker.finalize(memory_release_requested())
                if memory_release_requested():
                    print("[MemoryGuard] Soft limit reached; pending songs saved for resume.")
                    if loop_forever:
                        memory_guard_restart = True
                        print("[MemoryGuard] LoopForever enabled; scheduling automatic restart.")
                        discord_reporter.send_log(
                            "Memory soft limit reached; restarting MetaFinder to release RAM."
                        )

        except Exception as e:
            logging.error(f"Error: {e}")
            print(f"Error: {e}")
            discord_reporter.send_log(f"Error encountered: {e}")
        finally:
            # --- MEMORY LEAK FIX: Ensure manager/queue cleanup runs even on exceptions ---
            try:
                if status_queue is not None:
                    try:
                        status_queue.put(None)
                    except Exception:
                        pass
                if status_thread is not None:
                    try:
                        status_thread.join(timeout=2)
                    except Exception:
                        pass
                if manager is not None:
                    try:
                        manager.shutdown()
                    except Exception:
                        pass
            except Exception:
                pass

            elapsed = time.time() - start_time
            done_msg = f"Run completed in {elapsed:.2f}s"
            print(done_msg)
            discord_reporter.send_log(done_msg)
            # Update status timestamp so the website sees a fresh heartbeat.
            try:
                write_metafinder_status("online", done_msg)
            except Exception:
                pass

            # --- MEMORY LEAK FIX: Force garbage collection after each iteration ---
            # This helps reclaim memory from objects that may have circular references
            # or are otherwise not immediately collected.
            gc.collect()

        if memory_guard_restart:
            restart_process_for_memory_guard()
        elif loop_forever:
            wait_time = 3
            print(f"Restarting song scan in {wait_time} seconds...")

            # BUG FIX: Delete resume file when restarting after successful completion
            # This ensures the next iteration starts from scratch instead of resuming
            try:
                if os.path.exists(MEMORY_GUARD_RESUME_FILE):
                    os.remove(MEMORY_GUARD_RESUME_FILE)
                    print("[LoopForever] Cleared resume file for fresh start")
            except Exception as e:
                logging.warning(f"[LoopForever] Failed to delete resume file: {e}")

            time.sleep(wait_time)
            # Memory leak fix #3: Clear completed_songs set before next iteration
            # Prevents 50 KB per 1000 songs accumulation in loop_forever mode
            # BUG FIX: Properly clear/delete variables that could persist across iterations
            try:
                if completed_songs is not None:
                    completed_songs.clear()
                    del completed_songs
            except (NameError, AttributeError):
                pass
            try:
                if tasks is not None:
                    tasks.clear()
                    del tasks
            except (NameError, AttributeError):
                pass
            try:
                if future_map is not None:
                    future_map.clear()
                    del future_map
            except (NameError, AttributeError):
                pass
            try:
                if remaining_tasks is not None:
                    remaining_tasks.clear()
                    del remaining_tasks
            except (NameError, AttributeError):
                pass
        else:
            print("LoopForever=FALSE; exiting after completing queue.")
            discord_reporter.send_log("LoopForever disabled; exiting.")
            break

    # If we exit the main loop, mark MetaFinder as offline.
    try:
        write_metafinder_status("offline", "MetaFinder run stopped")
    except Exception:
        pass
