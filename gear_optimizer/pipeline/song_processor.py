"""
Song processing orchestration.

This module handles song file reading, optimization execution, and result persistence.
Contains the main process_song_task function that coordinates:
- Song data loading
- Fixed stats calculation
- GA optimization
- Force greats evaluation
- Database persistence

REFACTORED: Helper functions extracted to .helpers.song_helpers for maintainability.
"""
import concurrent.futures
import contextlib
import gc
import json
import logging
import multiprocessing
import os
import re
import sys
import time
import traceback
from io import StringIO

import numpy as np

from ..data.models import Tee, GASettings, WarnOnce
from ..data.database import (
    LOADOUTS_PER_SONG_LIMIT,
)
from ..data.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
)
from ..solver.genetic import solve_coevolution_genetic
from ..solver.scoring import (
    GEM_SOLVER_CACHE,
    FEVER_TIMELINE_CACHE,
    FG_CACHE,
    solve_best_fever_combination,
)
from ..core.memory import log_memory_usage
from ..core.utils import cfg_from_dict
from ..helpers.song_helpers import (
    load_database_context,
    setup_song_config,
    build_loadout_entries,
    process_force_greats,
    build_db_payload,
    build_persistence_entries,
    print_results,
)

# Global warn-once instance
WARN_ONCE = WarnOnce()

# Global counter for deterministic garbage collection
_SONG_GC_COUNTER = 0

# Performance timing flag (set via env var or config)
PERF_TIMING_ENABLED = os.environ.get("PERF_TIMING", "0") == "1"

def scan_song_header(fp):
    """
    Scan first 20 lines of song file for metadata (fast check).

    Args:
        fp: File path to song file

    Returns:
        dict: Metadata dictionary or None if parse fails
    """
    meta = {"Song Name": "", "Primary Color": "", "Secondary Color": "", "Difficulty": ""}
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            for _ in range(20):
                line = f.readline()
                if not line:
                    break
                line = line.strip()
                if line == "Song Data":
                    break
                # Handle both TAB and COLON separators
                if "\t" in line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
                elif ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        if key in meta:
                            meta[key] = parts[1].strip()
        return meta if meta["Song Name"] else None
    except Exception:
        return None


def read_song_file(fp):
    """
    Read complete song file including metadata and note timestamps.

    Args:
        fp: File path to song file

    Returns:
        dict: Song data with song_details and timestamps
    """
    data = {
        "song_details": {
            "Song Name": "",
            "Difficulty": "",
            "Primary Color": "",
            "Secondary Color": "",
            "Last Note Time": "",
            "Total Notes": "",
            "Fever Fill": "",
            "Fever Time": "",
            "Long Notes": "",
        },
        "timestamps": [],
    }
    if not fp:
        return data
    try:
        with open(fp, "r", encoding="utf-8-sig") as f:
            lines = f.read().splitlines()
        marker = next(
            (i for i, line in enumerate(lines) if line.strip() == "Song Data"), -1
        )
        if marker == -1:
            return data
        for line in lines[:marker]:
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                key = parts[0].strip()
                if key in data["song_details"]:
                    data["song_details"][key] = parts[1].strip() or "0"

        note_lines = []
        for line in lines[marker + 1:]:
            s = line.strip()
            if not s:
                continue
            c = s[0]
            if ("0" <= c <= "9") or c == ".":
                note_lines.append(line)

        if note_lines:
            nd = np.loadtxt(StringIO("\n".join(note_lines)), delimiter=None)
            if nd.size:
                nd = nd.reshape(1, -1) if nd.ndim == 1 else nd
                if nd.shape[1] >= 4:
                    data["timestamps"] = nd[:, 0].tolist()
        return data
    except Exception as exc:
        WARN_ONCE.warn("song-file", f"Failed to read song file {fp}: {exc}")
        return data


def process_song_task(args):
    """
    Run a single song end-to-end optimization.

    REFACTORED: Reduced from 767 lines to ~130 lines using helper functions.

    Main steps:
    1. Parse arguments and setup
    2. Read song file
    3. Load previous best from database (if using DB)
    4. Run GA or gem solver only
    5. Apply force greats if enabled
    6. Build persistence payload
    7. Cleanup and return results

    Args:
        args: Tuple of (fp, song_name, difficulty, cfg_dict, paths, ref_arrays,
                        all_gears, all_minis, gears_by_name, minis_by_name,
                        use_evo_db, auto_buff, ga_depth, status_queue, parallel_workers)

    Returns:
        dict: Result with song, db_key, db_payload, best_data, persist_entries, log
    """
    # --- CRITICAL: Clear caches at start of task to prevent OOM in worker process ---
    # These globals persist in the worker process if not cleared, leading to memory leaks
    # especially when GA is skipped (Calculate-Only mode) but caches are still populated.
    GEM_SOLVER_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()
    FG_CACHE.clear()

    (
        fp,
        found_song_name,
        effective_difficulty,  # Difficulty determined from file header or folder path
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
    ) = args

    # Initialize variables at function start to avoid 'in locals()' pattern issues
    local_executor = None
    loadout_entries = None
    known_loadouts = None
    persist_entries = None
    buf_content = ""  # Capture buffer content before closing

    # Optional local pool for single-song runs to saturate available cores.
    if parallel_workers:
        worker_count = min(parallel_workers, os.cpu_count() or 1)
        if worker_count > 1:
            local_executor = concurrent.futures.ProcessPoolExecutor(
                max_workers=worker_count,
                mp_context=multiprocessing.get_context("spawn"),
            )

    buf = StringIO()
    tee = Tee(sys.stdout, buf)
    redirect_ctx = contextlib.redirect_stdout(tee)
    redirect_ctx.__enter__()

    # Memory leak tracking: Log memory at start of song
    log_memory_usage(f"Start: {found_song_name}")

    try:
        best_data = None
        best_gear = []
        best_minis = []
        db_payload = None

        cfg = cfg_from_dict(cfg_dict)
        gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)

        song_data = read_song_file(fp)

        # OPTIMIZATION: store timestamps as NumPy array once per song
        song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)

        calc_song = {
            "metadata": song_data["song_details"],
            "song_data": {"timestamps": song_timestamps_np},
        }
        meta_primary_color = calc_song["metadata"].get("Primary Color", "")
        meta_secondary_color = calc_song["metadata"].get("Secondary Color", "")

        # Setup configuration and load current stats
        (
            ga_settings,
            fixed_stats,
            current_gear_stats,
            current_gear_list,
            current_mini_stats,
            current_mini_list,
            meta_finder,
            enable_fever,
            enable_mini,
            enable_gear,
            force_greats_mode,
            force_greats_finder,
            force_greats_config,
            manual_force_greats,
        ) = setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name)

        # --- DB KEY MODIFICATION ---
        # The song name from the file header already includes difficulty suffix like "(Hard)" or "(Easy)"
        # Normal difficulty songs have no suffix. Use song name directly as DB key.
        db_key = found_song_name

        # Load database context (prev_record, known_loadouts)
        prev_record, known_loadouts = load_database_context(
            found_song_name, use_evo_db, gears_by_name, minis_by_name
        )

        db_seed = prev_record if prev_record else None

        attempt_lifetime_prev = 0
        prev_attempts_first = 0
        if prev_record and "details" in prev_record:
            attempt_lifetime_prev = prev_record["details"].get("attempt_lifetime", 0)
            prev_attempts_first = prev_record["details"].get("attempts_first", 0)

        attempt_lifetime = attempt_lifetime_prev + 1

        def emit(msg):
            if status_queue:
                try:
                    status_queue.put(f"[{found_song_name}] {msg}")
                except Exception:
                    pass

        emit("START")

        # --- LOGIC BRANCHING BASED ON FINDERS ---
        # Performance timing variables (opt-in; enable via PERF_TIMING=1)
        ga_time_sec = 0.0
        fg_time_sec = 0.0
        db_payload_time_sec = 0.0
        persist_build_time_sec = 0.0
        report_time_sec = 0.0
        
        if enable_gear or enable_mini:
            # Run Genetic Algorithm (now memetic-enhanced)
            ga_start = time.perf_counter()
            (
                best_data,
                best_gear,
                best_minis,
                _,
                _,
                _,
                all_evaluated,  # All unique loadouts from GA
            ) = solve_coevolution_genetic(
                cfg,
                fixed_stats,
                paths,
                calc_song,
                ref_arrays,
                all_gears,
                all_minis,
                gears_by_name,
                minis_by_name,
                optimize_gear=enable_gear,
                optimize_minis=enable_mini,
                fixed_gear=current_gear_list,
                fixed_minis=current_mini_list,
                ga_depth=ga_depth,
                db_seed=db_seed,
                ga_settings=ga_settings,
                status_cb=lambda m: emit(m),
                executor=local_executor,
                known_loadouts=known_loadouts,
            )
            ga_time_sec = time.perf_counter() - ga_start
            
            if PERF_TIMING_ENABLED:
                print(f"[PERF] GA: {ga_time_sec:.2f}s")

            # Memory leak fix: Clear known_loadouts after GA completes
            # This dict now caps at the per-song loadout limit (small footprint)
            if known_loadouts:
                known_loadouts.clear()


        else:
            # Run Gem Solver only (enable_fever) or Calculate-Only Mode (nothing enabled)
            all_evaluated = []  # No GA, so no evaluated loadouts
            if not enable_fever:
                print("[Calculate-Only Mode] MetaFinder disabled - calculating score with current config...")

            # Common logic: combine fixed_stats + gear_stats + mini_stats
            combined_stats = fixed_stats.copy()
            for k, v in current_gear_stats.items():
                combined_stats[k] = combined_stats.get(k, 0) + v
            for k, v in current_mini_stats.items():
                combined_stats[k] = combined_stats.get(k, 0) + v

            best_data = solve_best_fever_combination(
                cfg,
                combined_stats,
                calc_song,
                ref_arrays,
                silent=enable_fever,  # Silent if enable_fever, verbose otherwise
                skip_optimizer=not enable_fever,  # Skip optimizer if no finders enabled
            )
            best_gear = current_gear_list
            best_minis = current_mini_list

        # Cap GA candidates for downstream processing to the DB loadout limit
        ga_candidates = all_evaluated or []
        if ga_candidates and len(ga_candidates) > LOADOUTS_PER_SONG_LIMIT:
            ga_candidates = sorted(
                ga_candidates,
                key=lambda r: r.get("Score", 0),
                reverse=True,
            )[:LOADOUTS_PER_SONG_LIMIT]

        def build_details(data_dict):
            if not data_dict:
                return {}
            return {
                "FT": data_dict.get("FT", 0),
                "FF": data_dict.get("FF", 0),
                "GemCounts": data_dict.get("GemCounts", {}),
                "Stats": data_dict.get("Stats", {}),
                "SelectedElement": data_dict.get("Selected Element", ""),
                "PrimaryColor": meta_primary_color,
                "SecondaryColor": meta_secondary_color,
                "Difficulty": effective_difficulty,  # Use the effective difficulty
                "ForceGreats": data_dict.get("ForceGreats", {}),
            }

        # --- APPLY FORCE GREATS TO ALL EVALUATED LOADOUTS ---
        fg_variants = []
        loadout_entries = None
        if manual_force_greats or force_greats_finder:
            # Build union of DB + GA loadouts
            loadout_entries = build_loadout_entries(
                found_song_name,
                use_evo_db,
                ga_candidates,
                LOADOUTS_PER_SONG_LIMIT,
                gears_by_name,
                minis_by_name,
                build_details,
            )

            # Process force greats
            db_loadouts_full_count = 0
            if use_evo_db:
                try:
                    from .database import get_best_loadouts
                    db_loadouts_full = get_best_loadouts(
                        found_song_name, limit=LOADOUTS_PER_SONG_LIMIT,
                        gears_by_name=gears_by_name, minis_by_name=minis_by_name
                    )
                    db_loadouts_full_count = len(db_loadouts_full)
                except Exception:
                    db_loadouts_full_count = 0

            fg_start = time.perf_counter()
            fg_variants = process_force_greats(
                loadout_entries,
                manual_force_greats,
                force_greats_finder,
                force_greats_config,
                calc_song,
                ref_arrays,
                meta_primary_color,
                build_details,
                db_loadouts_full_count,
                use_gpu=gpu_mode,
                perf_timing=PERF_TIMING_ENABLED,
            )
            fg_time_sec = time.perf_counter() - fg_start
            
            if PERF_TIMING_ENABLED:
                n_loadouts = len(loadout_entries) if loadout_entries else 0
                print(f"[PERF] ForceGreats: {fg_time_sec:.2f}s ({n_loadouts} loadouts, finder={force_greats_finder})")


        # --- REPORTING & DB UPDATE (payload only; saved by coordinator) ---
        if best_data:
            # Build database payload
            _t_db0 = time.perf_counter()
            db_payload = build_db_payload(
                best_data,
                best_gear,
                best_minis,
                prev_record,
                attempt_lifetime,
                prev_attempts_first,
                fg_variants,
                build_details,
            )
            db_payload_time_sec = time.perf_counter() - _t_db0

            # Build persistence entries
            _t_persist0 = time.perf_counter()
            persist_entries = build_persistence_entries(
                db_payload,
                ga_candidates,
                loadout_entries,
                build_details,
            )
            persist_build_time_sec = time.perf_counter() - _t_persist0

            # Print results
            _t_report0 = time.perf_counter()
            print_results(
                found_song_name,
                best_data,
                best_gear,
                best_minis,
                current_gear_list,
                current_mini_list,
                enable_gear,
                enable_mini,
                fg_variants,
                emit,
            )
            report_time_sec = time.perf_counter() - _t_report0

            if PERF_TIMING_ENABLED:
                print(
                    f"[PERF] DB/Persist/Report: payload={db_payload_time_sec:.3f}s "
                    f"persist={persist_build_time_sec:.3f}s report={report_time_sec:.3f}s"
                )

        # BUG FIX: Capture buffer content BEFORE finally block closes it
        buf_content = buf.getvalue() if buf else ""

        return {
            "song": found_song_name,
            "db_key": db_key,
            "db_payload": db_payload,
            "best_data": best_data,
            "best_gear": best_gear,
            "best_minis": best_minis,
            "persist_entries": persist_entries if best_data else [],
            "log": buf_content,
        }
    finally:
        # Memory leak tracking: Log before cleanup
        log_memory_usage(f"Before cleanup: {found_song_name}")

        if local_executor:
            local_executor.shutdown()
            local_executor = None  # Break reference

        # Prevent memory leak from unbounded cache growth across thousands of songs
        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()
        FG_CACHE.clear()

        # Memory leak fix: Clear local data structures explicitly
        # Using direct checks instead of 'in locals()' pattern (more reliable)
        if loadout_entries is not None:
            loadout_entries.clear()
        if known_loadouts is not None:
            known_loadouts.clear()

        # Memory leak fix: Close StringIO buffer explicitly
        # This buffer can hold 10-100MB of captured output per song
        if buf is not None:
            try:
                buf.close()
            except Exception as e:
                # Log buffer close failures (was silently suppressed)
                logging.debug(f"[StringIO] Failed to close buffer: {e}")

        # Force garbage collection (deterministic: every 5 songs for gen-2)
        # CRITICAL FIX: Use deterministic counter instead of random (was non-deterministic)
        global _SONG_GC_COUNTER
        _SONG_GC_COUNTER += 1
        if _SONG_GC_COUNTER % 5 == 0:  # Every 5 songs: full collection
            gc.collect(generation=2)
        else:  # Other songs: quick collection
            gc.collect(generation=0)

        # Memory leak tracking: Log after cleanup
        log_memory_usage(f"After cleanup: {found_song_name}")

        redirect_ctx.__exit__(None, None, None)

    # Should never reach here; fallback to avoid crashes
    return {
        "song": found_song_name,
        "db_key": found_song_name,
        "db_payload": None,
        "best_data": None,
        "best_gear": [],
        "best_minis": [],
        "log": buf_content,  # Use captured content instead of buf.getvalue()
    }


def safe_process_song_task(args):
    """
    Wrapper around process_song_task that never raises across process boundaries.
    Returns an error payload with traceback if anything escapes, to avoid crashing pools.

    Args:
        args: Arguments tuple for process_song_task

    Returns:
        dict: Result dict or error dict with _error and _trace keys
    """
    song_name = "Unknown"
    try:
        if isinstance(args, (list, tuple)) and len(args) > 1:
            song_name = args[1]
        return process_song_task(args)
    except Exception as exc:
        tb = traceback.format_exc()
        msg = f"[safe_process_song_task] {song_name} failed: {type(exc).__name__}: {exc}"
        try:
            logging.error(msg + "\n" + tb)
            print(msg)
        except Exception:
            pass
        return {
            "song": song_name,
            "_error": exc,
            "_trace": tb,
        }
