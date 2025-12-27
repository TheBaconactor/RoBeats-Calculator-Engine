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
import logging
import multiprocessing
import os
import sys
import time
import traceback
from io import StringIO

import numpy as np

from ..data.models import Tee, WarnOnce
from ..core.constants import (
    LOADOUTS_PER_SONG_LIMIT,
    FG_CANDIDATE_LIMIT,
)

from ..solver.genetic import solve_coevolution_genetic
from ..solver.scoring import (
    GEM_SOLVER_CACHE,
    FEVER_TIMELINE_CACHE,
    FG_CACHE,
    solve_best_fever_combination,
)
from ..solver.gpu_profiler import get_gpu_profiler
from ..core.memory import log_memory_usage
from ..core.utils import cfg_from_dict, safe_int
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

# GPU profiler for songs/hour tracking
_gpu_profiler = get_gpu_profiler()

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
        "note_types": [],
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
                    # Column 4 is the note type: 1=normal, 2=held head, 3=held tail.
                    # Keep as int so we can apply held-tail timing rules when needed.
                    data["note_types"] = nd[:, 3].astype(int).tolist()
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

    args_list = list(args) if isinstance(args, (list, tuple)) else [args]
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
        fg_debug,
    ) = args_list[:16]

    # Optional extras (sequential pipeline mode):
    # - preloaded calc_song dict to avoid repeated disk I/O + parsing
    # - defer_post: if True, skip persistence/reporting and return raw compute payload
    preloaded_calc_song = None
    defer_post = False
    extras = args_list[16:] if len(args_list) > 16 else []
    if extras:
        if isinstance(extras[0], dict) and extras[0].get("song_data") is not None:
            preloaded_calc_song = extras[0]
            extras = extras[1:]
        if extras:
            defer_post = bool(extras[0])

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

    # GPU profiler: track song processing time
    _gpu_profiler.start_song(found_song_name)

    result_payload = None
    stage_timing: dict[str, float] = {}
    _song_wall_t0 = time.perf_counter()
    _cpu_prep_t0 = _song_wall_t0
    ga_time_sec = 0.0
    fg_time_sec = 0.0
    db_payload_time_sec = 0.0
    persist_build_time_sec = 0.0
    report_time_sec = 0.0

    try:
        best_data = None
        best_gear = []
        best_minis = []
        db_payload = None

        cfg = cfg_from_dict(cfg_dict)
        gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)

        if isinstance(preloaded_calc_song, dict) and preloaded_calc_song.get("song_data"):
            calc_song = preloaded_calc_song
            stage_timing["cpu_read_sec"] = 0.0
        else:
            _t_read0 = time.perf_counter()
            song_data = read_song_file(fp)

            # OPTIMIZATION: store timestamps as NumPy array once per song
            song_timestamps_np = np.array(song_data["timestamps"], dtype=np.float64)
            song_note_types_np = np.array(song_data.get("note_types") or [], dtype=np.int16)
            if song_note_types_np.shape[0] != song_timestamps_np.shape[0]:
                # Older song dumps may not include note types; default to "normal note".
                song_note_types_np = np.ones(song_timestamps_np.shape[0], dtype=np.int16)

            calc_song = {
                "metadata": song_data["song_details"],
                "song_data": {"timestamps": song_timestamps_np, "note_types": song_note_types_np},
            }
            stage_timing["cpu_read_sec"] = time.perf_counter() - _t_read0

        # ------------------------------------------------------------------
        # Optional: Synthetic human hit-time simulation (Perfect-only).
        # Stores an alternative timestamp sequence for ForceGreats modeling.
        # ------------------------------------------------------------------
        try:
            sim_enabled = cfg.getboolean("HumanHitSim", "Enabled", fallback=False)
        except Exception:
            sim_enabled = False

        sim_already_applied = bool(calc_song.get("metadata", {}).get("HumanHitSimApplied"))
        if sim_enabled and (not sim_already_applied) and calc_song.get("song_data", {}).get("timestamps") is not None:
            from ..solver.hit_simulation import (
                simulate_perfect_hit_timestamps_with_great_candidates,
                stable_seed_from_text,
            )

            apply_to = cfg.get("HumanHitSim", "ApplyTo", fallback="FG").strip().upper()
            if apply_to not in {"FG", "ALL"}:
                apply_to = "FG"

            try:
                seed_in = int(cfg.get("HumanHitSim", "Seed", fallback="0") or "0")
            except Exception:
                seed_in = 0

            dist = cfg.get("HumanHitSim", "Distribution", fallback="uniform").strip().lower()
            great_mode = cfg.get("HumanHitSim", "GreatMode", fallback="late").strip().lower()

            # Default per-song deterministic seed when unset.
            if seed_in == 0:
                song_key = str(calc_song.get("metadata", {}).get("Song Name", "")) or str(found_song_name)
                seed_in = stable_seed_from_text(song_key)

            base_ts = np.asarray(calc_song["song_data"].get("timestamps", ()), dtype=np.float64)
            base_types = np.asarray(calc_song["song_data"].get("note_types", ()), dtype=np.int16)
            if base_types.shape[0] != base_ts.shape[0]:
                base_types = np.ones(base_ts.shape[0], dtype=np.int16)

            _t_sim0 = time.perf_counter()
            sim_ts, sim_great_candidates, sim_dbg = simulate_perfect_hit_timestamps_with_great_candidates(
                base_ts,
                base_types,
                seed=seed_in,
                distribution=dist,
                great_mode=great_mode,
            )
            stage_timing["cpu_human_hit_sim_sec"] = time.perf_counter() - _t_sim0

            # Store for downstream FG scorers; only override full timestamps when requested.
            calc_song["song_data"]["fg_timestamps"] = np.asarray(sim_ts, dtype=np.float64)
            calc_song["song_data"]["fg_great_candidate_timestamps"] = np.asarray(
                sim_great_candidates, dtype=np.float64
            )
            calc_song["metadata"]["HumanHitSimSeed"] = int(seed_in)
            calc_song["metadata"]["HumanHitSimApplyTo"] = apply_to
            calc_song["metadata"]["HumanHitSimDistribution"] = dist
            calc_song["metadata"]["HumanHitSimGreatMode"] = great_mode
            calc_song["metadata"]["HumanHitSimDebug"] = sim_dbg
            calc_song["metadata"]["HumanHitSimApplied"] = True
            try:
                print(
                    f"[HumanHitSim] Enabled (ApplyTo={apply_to}, dist={dist}, seed={seed_in}, "
                    f"groups={sim_dbg.get('groups')}, forced_monotonic={sim_dbg.get('forced_monotonic')})"
                )
            except Exception:
                pass
            if apply_to == "ALL":
                calc_song["song_data"]["timestamps"] = np.asarray(sim_ts, dtype=np.float64)
        meta_primary_color = calc_song["metadata"].get("Primary Color", "")
        meta_secondary_color = calc_song["metadata"].get("Secondary Color", "")

        # Setup configuration and load current stats
        _t_setup0 = time.perf_counter()
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
        stage_timing["cpu_setup_sec"] = time.perf_counter() - _t_setup0

        # --- DB KEY MODIFICATION ---
        # The song name from the file header already includes difficulty suffix like "(Hard)" or "(Easy)"
        # Normal difficulty songs have no suffix. Use song name directly as DB key.
        db_key = found_song_name

        # Load database context (prev_record, known_loadouts)
        _t_db0 = time.perf_counter()
        prev_record, known_loadouts = load_database_context(
            found_song_name, use_evo_db, gears_by_name, minis_by_name
        )
        stage_timing["cpu_db_load_sec"] = time.perf_counter() - _t_db0

        db_seed = prev_record if prev_record else None

        # Calculate best FG score from DB before known_loadouts is cleared
        # known_loadouts structure: {hash: (score, fg_score, force_data, details_data)}
        db_best_fg_score = 0
        if known_loadouts:
            try:
                db_best_fg_score = max(v[1] for v in known_loadouts.values() if v[1])
            except (ValueError, IndexError, TypeError):
                db_best_fg_score = 0

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

        stage_timing["cpu_prep_sec"] = time.perf_counter() - _cpu_prep_t0

        # --- LOGIC BRANCHING BASED ON FINDERS ---
        # Performance timing variables (opt-in; enable via PERF_TIMING=1)

        if enable_gear or enable_mini:
            # Get GPU slot for timeline prefetch (prefetched or on-demand)
            _gpu_song_slot = 0
            if gpu_mode:
                try:
                    from gear_optimizer.solver.taichi_gem.api.gpu_prefetch import get_gpu_prefetch_manager
                    _prefetch_mgr = get_gpu_prefetch_manager()
                    _t_timeline0 = time.perf_counter()
                    _gpu_song_slot = _prefetch_mgr.get_slot(calc_song, ref_arrays)
                    stage_timing["gpu_timeline_precompute_sec"] = time.perf_counter() - _t_timeline0
                except Exception as _pfx_err:
                    pass  # Fallback to slot 0

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
                song_slot=_gpu_song_slot,  # Use prefetched GPU slot
            )
            ga_time_sec = time.perf_counter() - ga_start

            # Release GPU slot for reuse
            if gpu_mode and _gpu_song_slot > 0:
                try:
                    _prefetch_mgr.release(_gpu_song_slot)
                except Exception:
                    pass

            if PERF_TIMING_ENABLED:
                print(f"[PERF] GA: {ga_time_sec:.2f}s")

            # Memory leak fix: Clear known_loadouts after GA completes
            # This dict now caps at the per-song loadout limit (small footprint)
            if known_loadouts:
                known_loadouts.clear()


        else:
            # Run Gem Solver only (enable_fever) or Calculate-Only Mode (nothing enabled)
            # No GA population; include the current fixed loadout as a single
            # "evaluated candidate" so downstream ForceGreatsFinder can still
            # evaluate the active configuration even when MetaFinder is disabled.
            all_evaluated = []
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
            if best_data:
                base_score = best_data.get("BaseScore") or best_data.get("Score", 0) or 0
                all_evaluated = [
                    {
                        "Score": base_score,
                        "BaseScore": base_score,
                        "Gear": best_gear,
                        "Minis": best_minis,
                        "Data": best_data,
                    }
                ]

        # Cap GA candidates for downstream processing.
        # Ranked by Score (base score) for DB seeding. We keep a wider funnel so
        # ForceGreatsFinder can evaluate more unique loadouts even on a cold start
        # (empty DB). The final DB save still truncates to LOADOUTS_PER_SONG_LIMIT (51).
        ga_candidates = list(all_evaluated or [])
        if best_data and best_gear and best_minis:
            base_score = best_data.get("BaseScore") or best_data.get("Score", 0) or 0
            ga_candidates.append(
                {
                    "Score": base_score,
                    "BaseScore": base_score,
                    "Gear": best_gear,
                    "Minis": best_minis,
                    "Data": best_data,
                }
            )
        # Configurable FG funnel size (default FG_CANDIDATE_LIMIT).
        fg_candidate_limit = safe_int(
            cfg.get("IterationEngine", "FG_CandidateLimit", fallback=FG_CANDIDATE_LIMIT),
            FG_CANDIDATE_LIMIT,
        )
        # Clamp to avoid extreme values causing huge DB reads or GPU batches.
        fg_candidate_limit = max(LOADOUTS_PER_SONG_LIMIT, min(5000, fg_candidate_limit))

        fg_search_radius = None
        try:
            raw_fg_radius = str(cfg.get("IterationEngine", "FG_SearchRadius", fallback="") or "").strip()
        except Exception:
            raw_fg_radius = ""
        if raw_fg_radius:
            fg_search_radius = safe_int(raw_fg_radius, -1)
        # `FG_SearchRadius` semantics:
        # - unset/empty => use default radius (FG_SEARCH_RADIUS / env default 5)
        # - -1 => full window over all FT/FF gem allocations within TOTAL_GEM_BUDGET
        # - >=0 => radius in gem-space around each loadout's (FT, FF) center

        def _cand_key(cand: dict) -> tuple:
            gear_names = tuple((it or {}).get("Name", "") for it in (cand.get("Gear") or []))
            mini_names = tuple(sorted(((it or {}).get("Name", "") for it in (cand.get("Minis") or []))))
            return gear_names + mini_names

        def _truncate_candidates_with_fg_priority(candidates: list[dict], limit: int) -> list[dict]:
            if not candidates or limit <= 0:
                return []

            # De-dupe by (gear, minis) key; keep the best base-score copy.
            best_by_key: dict[tuple, dict] = {}
            for c in candidates:
                if not c:
                    continue
                k = _cand_key(c)
                prev = best_by_key.get(k)
                if prev is None or (c.get("Score", 0) or 0) > (prev.get("Score", 0) or 0):
                    best_by_key[k] = c
            uniq = list(best_by_key.values())
            if len(uniq) <= limit:
                return sorted(uniq, key=lambda r: r.get("Score", 0), reverse=True)

            primary = str(meta_primary_color or "")
            secondary = str(meta_secondary_color or "")

            def _mini_key(c: dict) -> tuple:
                minis = c.get("Minis") or []
                return tuple(sorted(((it or {}).get("Name", "") for it in minis)))

            def _fg_proxy(c: dict) -> int:
                # Proxy for FG potential: emphasize fever stats and element alignment.
                items = list(c.get("Gear") or []) + list(c.get("Minis") or [])
                total = 0
                for it in items:
                    if not it:
                        continue
                    total += int(it.get("Fever Multiplier", 0) or 0) * 4
                    total += int(it.get("Fever Fill Rate", 0) or 0) * 4
                    total += int(it.get("Fever Time", 0) or 0) * 3
                    total += int(it.get("Combo Multiplier", 0) or 0) * 2
                    total += int(it.get("Perfect Points", 0) or 0)
                    if primary:
                        total += int(it.get(primary, 0) or 0) * 2
                    if secondary and secondary != primary:
                        total += int(it.get(secondary, 0) or 0)
                return int(total)

            selected: list[dict] = []
            seen_keys: set[tuple] = set()
            seen_minis: set[tuple] = set()

            def _add(c: dict) -> bool:
                k = _cand_key(c)
                if k in seen_keys:
                    return False
                seen_keys.add(k)
                selected.append(c)
                seen_minis.add(_mini_key(c))
                return True

            # Budgets: keep a mix of exploitation (base score), exploration (FG proxy),
            # and diversity (unique mini teams), while still honoring `_fg_priority`.
            priority_min = min(limit, max(10, limit // 10))
            base_budget = min(limit, max(0, int(limit * 0.55)))
            fg_budget = min(limit, max(0, int(limit * 0.30)))

            # 0) Ensure some priority candidates are always present (use FG proxy ordering).
            priority = [c for c in uniq if c.get("_fg_priority")]
            priority.sort(key=_fg_proxy, reverse=True)
            for c in priority:
                if len(selected) >= priority_min:
                    break
                _add(c)

            # 1) Top by base score (stable "exploitation").
            uniq.sort(key=lambda r: r.get("Score", 0), reverse=True)
            for c in uniq:
                if len(selected) >= base_budget:
                    break
                _add(c)

            # 2) Top by FG proxy (captures low-base / high-FG candidates).
            for c in sorted(uniq, key=_fg_proxy, reverse=True):
                if len(selected) >= (base_budget + fg_budget):
                    break
                _add(c)

            # 3) Mini-team diversity fill.
            for c in uniq:
                if len(selected) >= limit:
                    break
                mk = _mini_key(c)
                if mk in seen_minis:
                    continue
                _add(c)

            # 4) Final fill by base score.
            for c in uniq:
                if len(selected) >= limit:
                    break
                _add(c)

            return selected[:limit]

        if ga_candidates and len(ga_candidates) > fg_candidate_limit:
            ga_candidates = _truncate_candidates_with_fg_priority(ga_candidates, fg_candidate_limit)

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
                fg_candidate_limit,  # Pass the larger budget to build_loadout_entries
                gears_by_name,
                minis_by_name,
                build_details,
            )

            # Process force greats
            db_loadouts_full_count = 0
            if use_evo_db:
                try:
                    from ..data.database import get_best_loadouts
                    db_loadouts_full = get_best_loadouts(
                        found_song_name,
                        limit=fg_candidate_limit,
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
                fg_search_radius=fg_search_radius,
                perf_timing=PERF_TIMING_ENABLED,
            )
            fg_time_sec = time.perf_counter() - fg_start

            if PERF_TIMING_ENABLED:
                n_loadouts = len(loadout_entries) if loadout_entries else 0
                print(f"[PERF] ForceGreats: {fg_time_sec:.2f}s ({n_loadouts} loadouts, finder={force_greats_finder})")


        # --- REPORTING & DB UPDATE (payload only; saved by coordinator) ---
        if defer_post and best_data:
            def _item_name(item):
                if isinstance(item, dict):
                    return item.get("Name", "")
                return str(item) if item else ""

            def _compact_items(items):
                return [_item_name(it) for it in (items or [])]

            def _compact_fg_variants(variants):
                out = []
                for v in variants or []:
                    if not isinstance(v, dict):
                        continue
                    out.append(
                        {
                            "score": v.get("score", 0),
                            "fg_score": v.get("fg_score", 0),
                            "gear": _compact_items(v.get("gear")),
                            "minis": _compact_items(v.get("minis")),
                            "data": v.get("data") or {},
                        }
                    )
                return out

            def _compact_ga_candidates(candidates):
                out = []
                for c in candidates or []:
                    if not isinstance(c, dict):
                        continue
                    out.append(
                        {
                            "Score": c.get("Score", 0),
                            "BaseScore": c.get("BaseScore", c.get("Score", 0)),
                            "Gear": _compact_items(c.get("Gear")),
                            "Minis": _compact_items(c.get("Minis")),
                            "Data": c.get("Data") or {},
                            "_fg_priority": c.get("_fg_priority", 0),
                        }
                    )
                return out

            def _compact_loadout_entries(entries):
                if entries is None:
                    return None
                out = {}
                for k, v in entries.items():
                    if not isinstance(v, dict):
                        continue
                    out[str(k)] = {
                        "score": v.get("score", 0),
                        "base_score": v.get("base_score", v.get("score", 0)),
                        "fg_score": v.get("fg_score", 0),
                        "gear": _compact_items(v.get("gear")),
                        "minis": _compact_items(v.get("minis")),
                        "details": v.get("details") or {},
                        "force": v.get("force"),
                    }
                return out

            def _compact_prev_record(record):
                if not isinstance(record, dict):
                    return None
                out = dict(record)
                out["gear"] = _compact_items(record.get("gear"))
                out["minis"] = _compact_items(record.get("minis"))
                if isinstance(out.get("loadout"), (list, tuple)):
                    out["loadout"] = [str(x) if x is not None else "" for x in out.get("loadout")]
                force_obj = out.get("force")
                if isinstance(force_obj, dict):
                    force_copy = dict(force_obj)
                    if isinstance(force_copy.get("gear"), (list, tuple)):
                        force_copy["gear"] = [str(x) if x is not None else "" for x in force_copy.get("gear")]
                    if isinstance(force_copy.get("minis"), (list, tuple)):
                        force_copy["minis"] = [str(x) if x is not None else "" for x in force_copy.get("minis")]
                    out["force"] = force_copy
                return out

            # BUG FIX: Capture buffer content BEFORE finally block closes it
            buf_content = buf.getvalue() if buf else ""

            result_payload = {
                "_deferred_post": True,
                "song": found_song_name,
                "db_key": db_key,
                "file_path": fp,
                "difficulty": effective_difficulty,
                "use_evo_db": bool(use_evo_db),
                "cfg_dict": cfg_dict,
                "ref_arrays": ref_arrays,
                "calc_song": calc_song,
                "best_data": best_data,
                "best_gear": _compact_items(best_gear),
                "best_minis": _compact_items(best_minis),
                "current_gear": _compact_items(current_gear_list),
                "current_minis": _compact_items(current_mini_list),
                "enable_gear": bool(enable_gear),
                "enable_mini": bool(enable_mini),
                "fg_variants": _compact_fg_variants(fg_variants),
                "ga_candidates": _compact_ga_candidates(ga_candidates),
                "loadout_entries": _compact_loadout_entries(loadout_entries),
                "prev_record": _compact_prev_record(prev_record),
                "attempt_lifetime": attempt_lifetime,
                "prev_attempts_first": prev_attempts_first,
                "db_best_fg_score": db_best_fg_score,
                "meta_primary_color": meta_primary_color,
                "meta_secondary_color": meta_secondary_color,
                "fg_debug": bool(fg_debug),
                "log": buf_content,
            }
            return result_payload

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
                db_best_fg_score=db_best_fg_score,
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
                fg_debug=fg_debug,
                ref_arrays=ref_arrays,
                calc_song=calc_song,
                cfg=cfg,
            )
            report_time_sec = time.perf_counter() - _t_report0

            if PERF_TIMING_ENABLED:
                print(
                    f"[PERF] DB/Persist/Report: payload={db_payload_time_sec:.3f}s "
                    f"persist={persist_build_time_sec:.3f}s report={report_time_sec:.3f}s"
                )

        else:
            # OPTIMIZATION FAILED: Provide fallback payload to diagnose "N/A" score issues
            print(f"[ERROR] Optimization failed for {found_song_name} - best_data is None")
            # Try to capture log tail from buffer
            log_tail = buf.getvalue()[-500:] if buf else "No log buffer"
            db_payload = {
                "score": 0,
                "fg_score": 0,
                "gear": [],
                "minis": [],
                "details": {
                    "Error": "Optimization failed - no valid loadout found",
                    "LogTail": log_tail
                },
                "force": None
            }

        # BUG FIX: Capture buffer content BEFORE finally block closes it
        buf_content = buf.getvalue() if buf else ""

        result_payload = {
            "song": found_song_name,
            "db_key": db_key,
            "db_payload": db_payload,
            "best_data": best_data,
            "best_gear": best_gear,
            "best_minis": best_minis,
            "persist_entries": persist_entries if best_data else [],
            "log": buf_content,
        }
        return result_payload
    finally:
        # Memory leak tracking: Log before cleanup
        log_memory_usage(f"Before cleanup: {found_song_name}")

        # GPU profiler: end song tracking
        _song_gpu_timing = _gpu_profiler.end_song()
        stage_timing["song_wall_sec"] = time.perf_counter() - _song_wall_t0
        stage_timing["cpu_post_sec"] = float(db_payload_time_sec) + float(persist_build_time_sec) + float(report_time_sec)
        stage_timing["cpu_ga_wall_sec"] = float(ga_time_sec)
        stage_timing["cpu_fg_wall_sec"] = float(fg_time_sec)

        if isinstance(result_payload, dict):
            result_payload.setdefault("_stage_timing", {}).update(stage_timing)
            if _song_gpu_timing is not None:
                result_payload.setdefault("_gpu_timing", {}).update(
                    {
                        "kernel_sec": float(getattr(_song_gpu_timing, "kernel_sec", 0.0) or 0.0),
                        "upload_sec": float(getattr(_song_gpu_timing, "upload_sec", 0.0) or 0.0),
                        "download_sec": float(getattr(_song_gpu_timing, "download_sec", 0.0) or 0.0),
                        "kernel_calls": int(getattr(_song_gpu_timing, "kernel_calls", 0) or 0),
                        "genome_evaluations": int(getattr(_song_gpu_timing, "genome_evaluations", 0) or 0),
                        "total_sec": float(getattr(_song_gpu_timing, "total_sec", 0.0) or 0.0),
                    }
                )

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
            "_song_name": song_name,
            "_error": str(exc),
            "_error_type": type(exc).__name__,
            "_trace": tb,
        }
