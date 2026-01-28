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
import hashlib
import json
import logging
import multiprocessing
import os
import sys
import threading
import time
import traceback
from io import StringIO

import numpy as np
from cachetools import LRUCache

from ..data.models import Tee, WarnOnce
from ..core.env_config import ENV
from ..core.result_payloads import build_error_payload
from ..core.types import SongResultPayload
from ..core.constants import (
    LOADOUTS_PER_SONG_LIMIT,
    FG_CANDIDATE_LIMIT,
)

from ..core.config import read_fg_candidate_limit, read_fg_search_radius
from ..solver.genetic import GA_POPULATION_SIZE, solve_coevolution_genetic
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
    # Candidate selection for FG funnel (keeps low-base/high-FG candidates)
    # without increasing FG_CandidateLimit.
    process_force_greats,
    build_db_payload,
    build_persistence_entries,
    print_results,
)
from ..helpers.song_helpers.persistence import make_build_details_fn, evaluate_record_update
from ..helpers.song_helpers.fg_candidate_selector import select_fg_candidates
from ..helpers.song_helpers.item_utils import names_list

# Global warn-once instance
WARN_ONCE = WarnOnce()

# Global counter for deterministic garbage collection
_SONG_GC_COUNTER = 0

# Performance timing flag (set via env var)
PERF_TIMING_ENABLED = bool(getattr(ENV, "perf_timing_unconditional", False))

# GPU profiler for songs/hour tracking
_gpu_profiler = get_gpu_profiler()


# ---------------------------------------------------------------------------
# Base calc_song cache (pre-HumanHitSim), keyed by file path + config hash.
#
# Motivation:
# - When the same song is processed multiple times (SongRepeats / repeated queue),
#   we were fully parsing the file + building arrays on every run.
# - HumanHitSim.Seed=0 requires re-applying the sim each repeat (unique seed),
#   so we cache the *base* calc_song and clone it per run before applying HitSim.
# ---------------------------------------------------------------------------
def _stable_cfg_hash(cfg_dict: dict | None) -> str:
    if not isinstance(cfg_dict, dict) or not cfg_dict:
        return "cfg0"
    try:
        payload = json.dumps(cfg_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    except Exception:
        payload = repr(sorted(cfg_dict.items(), key=lambda kv: str(kv[0])))
    h = hashlib.sha1(payload.encode("utf-8", errors="replace")).hexdigest()
    return h[:16]


_BASE_CALC_SONG_CACHE_MAX = max(1, int(os.environ.get("BASE_CALC_SONG_CACHE_MAX", "64") or "64"))
_BASE_CALC_SONG_CACHE: LRUCache = LRUCache(maxsize=_BASE_CALC_SONG_CACHE_MAX)
_BASE_CALC_SONG_CACHE_LOCK = threading.Lock()


def clone_calc_song(calc_song: dict) -> dict:
    """
    Clone a calc_song dict for per-run mutation.

    Arrays are shared by reference (read-only); dicts are copied.
    """
    if not isinstance(calc_song, dict):
        return {}
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    return {"metadata": dict(meta), "song_data": dict(song_data)}


def _build_base_calc_song_from_file(fp: str) -> dict:
    song_data = read_song_file(fp)

    song_timestamps_np = np.asarray(song_data.get("timestamps") or [], dtype=np.float64)
    song_note_types_np = np.asarray(song_data.get("note_types") or [], dtype=np.int16)
    if song_note_types_np.shape[0] != song_timestamps_np.shape[0]:
        song_note_types_np = np.ones(song_timestamps_np.shape[0], dtype=np.int16)

    return {
        "metadata": song_data.get("song_details", {}) or {},
        "song_data": {
            "timestamps": song_timestamps_np,
            "chart_timestamps": song_timestamps_np,
            "note_types": song_note_types_np,
        },
    }


def get_base_calc_song(fp: str, cfg_dict: dict | None = None) -> dict:
    """
    Get cached base calc_song for this file/config pair.

    The returned object is shared; callers must clone via clone_calc_song()
    before applying HumanHitSim or any other per-run mutation.
    """
    if not fp:
        return {}

    abs_fp = os.path.abspath(fp)
    cfg_h = _stable_cfg_hash(cfg_dict)
    key = (abs_fp, cfg_h)

    try:
        st = os.stat(abs_fp)
        mtime_ns = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
    except Exception:
        mtime_ns = -1

    with _BASE_CALC_SONG_CACHE_LOCK:
        entry = _BASE_CALC_SONG_CACHE.get(key)
        if entry is not None:
            cached_mtime_ns, cached_calc_song = entry
            if int(cached_mtime_ns) == int(mtime_ns) and isinstance(cached_calc_song, dict):
                return cached_calc_song

    base = _build_base_calc_song_from_file(abs_fp)
    with _BASE_CALC_SONG_CACHE_LOCK:
        _BASE_CALC_SONG_CACHE[key] = (int(mtime_ns), base)
    return base


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
        marker = next((i for i, line in enumerate(lines) if line.strip() == "Song Data"), -1)
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
        for line in lines[marker + 1 :]:
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


def process_song_task(args) -> SongResultPayload:
    """
    Run a single song end-to-end optimization.

    REFACTORED: Extracted helper functions where practical; this entrypoint remains
    orchestration-heavy because it owns per-song setup, solver routing, and persistence.

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
    repeat_ctx = None
    defer_post = False
    extras = args_list[16:] if len(args_list) > 16 else []
    if extras:
        for extra in extras:
            if isinstance(extra, dict):
                if extra.get("song_data") is not None:
                    preloaded_calc_song = extra
                    continue
                if "repeat_index" in extra and "repeat_total" in extra and "ga_seed" in extra:
                    repeat_ctx = extra
                    continue
            if isinstance(extra, bool) and not defer_post:
                defer_post = bool(extra)

    queue_label = found_song_name
    ga_seed = None
    if isinstance(repeat_ctx, dict):
        try:
            idx = int(repeat_ctx.get("repeat_index") or 0)
            total = int(repeat_ctx.get("repeat_total") or 0)
        except Exception:
            idx = 0
            total = 0
        try:
            ga_seed = int(repeat_ctx.get("ga_seed")) if repeat_ctx.get("ga_seed") is not None else None
        except Exception:
            ga_seed = None
        if idx > 0 and total > 1:
            queue_label = f"{found_song_name} (Run {idx}/{total})"

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
    output_enabled = bool(getattr(ENV, "output_enabled", False))
    tee = Tee(sys.stdout, buf) if output_enabled else Tee(buf)
    redirect_ctx = contextlib.redirect_stdout(tee)
    redirect_err_ctx = contextlib.redirect_stderr(tee)
    redirect_ctx.__enter__()
    redirect_err_ctx.__enter__()

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
    # GPU timeline slot reuse (GA -> FG). Keep these in outer scope for cleanup.
    _gpu_song_slot = 0
    _prefetch_mgr = None
    gpu_mode = False

    try:
        best_data = None
        best_gear = []
        best_minis = []
        db_payload = None

        cfg = cfg_from_dict(cfg_dict)
        gpu_mode_requested = True
        try:
            gpu_mode_requested = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=True)
        except Exception:
            gpu_mode_requested = True
        if not gpu_mode_requested:
            print("[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); forcing GPU_Mode=true.")
        gpu_mode = True

        if isinstance(preloaded_calc_song, dict) and preloaded_calc_song.get("song_data"):
            calc_song = clone_calc_song(preloaded_calc_song)
            stage_timing["cpu_read_sec"] = 0.0
        else:
            _t_read0 = time.perf_counter()
            base_calc_song = get_base_calc_song(fp, cfg_dict)
            calc_song = clone_calc_song(base_calc_song)
            stage_timing["cpu_read_sec"] = time.perf_counter() - _t_read0
        try:
            # Ensure chart_timestamps is always available for "HumanHitSim OFF" comparisons.
            song_data = calc_song.get("song_data", {}) or {}
            if "chart_timestamps" not in song_data and song_data.get("timestamps") is not None:
                song_data["chart_timestamps"] = np.asarray(song_data.get("timestamps"), dtype=np.float64)
        except Exception:
            pass

        # ------------------------------------------------------------------
        # Optional: Synthetic human hit-time simulation (Perfect-only).
        # Stores an alternative timestamp sequence for ForceGreats modeling.
        # ------------------------------------------------------------------
        try:
            from ..solver.hit_simulation import apply_human_hit_sim

            _t_sim0 = time.perf_counter()
            sim_info = apply_human_hit_sim(calc_song, cfg_dict=cfg_dict)
            if sim_info is not None:
                stage_timing["cpu_human_hit_sim_sec"] = time.perf_counter() - _t_sim0
                try:
                    sim_dbg = sim_info.get("debug") or {}
                    print(
                        f"[HumanHitSim] Enabled (ApplyTo={sim_info.get('apply_to')}, dist={sim_info.get('distribution')}, "
                        f"seed={sim_info.get('seed')}, groups={sim_dbg.get('groups')}, "
                        f"forced_monotonic={sim_dbg.get('forced_monotonic')})"
                    )
                except Exception:
                    pass
        except Exception:
            pass
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

        # --- DB KEY ---
        # HumanHitSim MUST NOT affect DB keying: HitSim is intended to explore/visualize
        # alternate timelines while accumulating results under the same song key.
        from gear_optimizer.helpers.song_helpers.database_context import build_db_key

        db_key = build_db_key(found_song_name, calc_song)

        # Load database context (prev_record, known_loadouts)
        _t_db0 = time.perf_counter()
        prev_record, known_loadouts = load_database_context(db_key, use_evo_db, gears_by_name, minis_by_name)
        stage_timing["cpu_db_load_sec"] = time.perf_counter() - _t_db0

        db_seed = prev_record if prev_record else None

        # Calculate best FG score from DB.
        # IMPORTANT: Do NOT derive this from `known_loadouts` alone because that list is
        # ordered/limited by base score and can omit the true best FG-improving loadout.
        db_best_fg_score = 0
        if use_evo_db:
            try:
                from gear_optimizer.data.database import get_db_connection_cached

                conn = get_db_connection_cached()
                row = conn.execute(
                    "SELECT best_fg_score FROM songs WHERE name = ?",
                    (str(db_key or "").strip(),),
                ).fetchone()
                if row is not None:
                    try:
                        db_best_fg_score = int(row[0] or 0)
                    except Exception:
                        db_best_fg_score = 0
            except Exception:
                db_best_fg_score = 0

        # Fallback: if songs row doesn't exist yet, approximate from known_loadouts.
        if (not db_best_fg_score) and known_loadouts:
            try:
                db_best_fg_score = max(v[1] for v in known_loadouts.values() if v[1])
            except (ValueError, IndexError, TypeError):
                db_best_fg_score = 0

        attempt_lifetime_prev = 0
        prev_attempts_first = 0
        if prev_record and "details" in prev_record:
            try:
                attempt_lifetime_prev = int(prev_record["details"].get("attempt_lifetime", 0) or 0)
            except Exception:
                attempt_lifetime_prev = 0
            try:
                prev_attempts_first = int(prev_record["details"].get("attempts_first", 0) or 0)
            except Exception:
                prev_attempts_first = 0

        attempt_lifetime = attempt_lifetime_prev + 1
        # Note: per-song attempt counters are now tracked in `songs` and updated in the DB-writer
        # (post-processor / async saver). This local value is best-effort metadata only.
        attempts_first = (prev_attempts_first + 1) if prev_attempts_first else 1

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
            if gpu_mode:
                try:
                    # Configure GPU-native GA run buffers BEFORE any Taichi field allocation
                    # (prefetch triggers `precompute_timeline_gpu()` -> `ensure_ready()`).
                    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

                    gpu_fields.configure_ga_run_buffers(
                        max_runs=ga_settings.multi_start,
                        max_genomes=GA_POPULATION_SIZE,
                    )
                except Exception:
                    pass  # Prefetch should still run even if sizing fails.

                try:
                    from gear_optimizer.solver.taichi_gem.api.gpu_prefetch import get_gpu_prefetch_manager

                    _prefetch_mgr = get_gpu_prefetch_manager()
                    _t_timeline0 = time.perf_counter()
                    _gpu_song_slot = _prefetch_mgr.get_slot(calc_song, ref_arrays)
                    stage_timing["gpu_timeline_precompute_sec"] = time.perf_counter() - _t_timeline0
                except Exception as _pfx_err:
                    pass  # Fallback to slot 0
                # Propagate song_slot into calc_song so downstream FG can reuse the same GPU timeline slot.
                try:
                    calc_song["_gpu_song_slot"] = int(_gpu_song_slot)
                except Exception:
                    pass

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
                ga_seed=ga_seed,
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
        fg_candidate_limit = read_fg_candidate_limit(
            cfg,
            default=FG_CANDIDATE_LIMIT,
            min_limit=LOADOUTS_PER_SONG_LIMIT,
        )

        fg_search_radius = read_fg_search_radius(cfg)
        # `FG_SearchRadius` semantics:
        # - unset/empty => use default radius (FG_SEARCH_RADIUS / env default 5)
        # - -1 => full window over all FT/FF gem allocations within TOTAL_GEM_BUDGET
        # - >=0 => radius in gem-space around each loadout's (FT, FF) center
        if manual_force_greats or force_greats_finder:
            ga_candidates = select_fg_candidates(
                ga_candidates,
                limit=fg_candidate_limit,
                primary_color=str(meta_primary_color or ""),
                secondary_color=str(meta_secondary_color or ""),
            )

        build_details = make_build_details_fn(meta_primary_color, meta_secondary_color, effective_difficulty)

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
            # ForceGreatsFinder no longer uses the historical "DB loadout count budget" heuristic;
            # avoid an extra SQLite read on the critical path.
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

        # ------------------------------------------------------------------
        # HumanHitSim timing summary (FG best-improving candidate, GA-origin).
        # Attach to the FG payload so it can be logged/persisted without per-note spam.
        # ------------------------------------------------------------------
        try:
            if fg_variants:
                from ..solver.scoring.force_greats import summarize_hitsim_offset_delta_ms_for_fg_variant

                best_fg_variant = None
                best_fg_score = -1
                for v in fg_variants or []:
                    if not isinstance(v, dict):
                        continue
                    if not bool(v.get("_is_ga", True)):
                        continue
                    try:
                        fg_score_v = int(v.get("fg_score", 0) or 0)
                    except Exception:
                        fg_score_v = 0
                    try:
                        base_score_v = int(v.get("score", 0) or 0)
                    except Exception:
                        base_score_v = 0
                    if fg_score_v <= base_score_v:
                        continue
                    if fg_score_v > best_fg_score:
                        best_fg_score = fg_score_v
                        best_fg_variant = v

                if best_fg_variant is not None:
                    fg_data = best_fg_variant.get("data") or {}
                    if isinstance(fg_data, dict):
                        fg_meta = fg_data.get("ForceGreats") or {}
                        already = isinstance(fg_meta, dict) and ("hitsim_offset_delta_ms" in fg_meta)
                        if not already:
                            delta_ms = summarize_hitsim_offset_delta_ms_for_fg_variant(calc_song, fg_data, ref_arrays)
                            if delta_ms is not None:
                                try:
                                    fg_meta_out = fg_data.get("ForceGreats") or {}
                                    if isinstance(fg_meta_out, dict):
                                        fg_meta_out["hitsim_offset_delta_ms"] = int(delta_ms)
                                        fg_data["ForceGreats"] = fg_meta_out
                                except Exception:
                                    pass
        except Exception:
            pass

        # --- REPORTING & DB UPDATE (payload only; saved by coordinator) ---
        if defer_post and best_data:

            def _compact_items(items):
                return names_list(items)

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

            try:
                record_info = evaluate_record_update(
                    best_data,
                    prev_record,
                    fg_variants,
                    db_best_fg_score=db_best_fg_score,
                )
            except Exception:
                record_info = None

            result_payload = {
                "_deferred_post": True,
                "song": found_song_name,
                "_queue_key": queue_label,
                "_queue_label": queue_label,
                "_repeat_index": int(repeat_ctx.get("repeat_index") or 0) if isinstance(repeat_ctx, dict) else 0,
                "_repeat_total": int(repeat_ctx.get("repeat_total") or 0) if isinstance(repeat_ctx, dict) else 0,
                "_ga_seed": int(ga_seed) if ga_seed is not None else None,
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
                "_record": record_info,
                "log": buf_content,
            }
            return result_payload

        if best_data:
            # Optional: HumanHitSim timing summary for base fever activation (ApplyTo=ALL only).
            try:
                from ..solver.scoring.force_greats import summarize_hitsim_offset_delta_ms_for_base

                if "hitsim_offset_delta_ms" not in best_data:
                    delta_ms = summarize_hitsim_offset_delta_ms_for_base(calc_song, best_data, ref_arrays)
                    if delta_ms is not None:
                        best_data["hitsim_offset_delta_ms"] = int(delta_ms)
            except Exception:
                pass

            # Build database payload
            _t_db0 = time.perf_counter()
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
                db_best_fg_score=db_best_fg_score,
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
                "details": {"Error": "Optimization failed - no valid loadout found", "LogTail": log_tail},
                "force": None,
            }

        # BUG FIX: Capture buffer content BEFORE finally block closes it
        buf_content = buf.getvalue() if buf else ""

        result_payload = {
            "song": found_song_name,
            "_queue_key": queue_label,
            "_queue_label": queue_label,
            "_repeat_index": int(repeat_ctx.get("repeat_index") or 0) if isinstance(repeat_ctx, dict) else 0,
            "_repeat_total": int(repeat_ctx.get("repeat_total") or 0) if isinstance(repeat_ctx, dict) else 0,
            "_ga_seed": int(ga_seed) if ga_seed is not None else None,
            "db_key": db_key,
            "file_path": fp,
            "difficulty": effective_difficulty,
            "cfg_dict": cfg_dict,
            "db_payload": db_payload,
            "_record": db_payload.get("_record") if isinstance(db_payload, dict) else None,
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
        stage_timing["cpu_post_sec"] = (
            float(db_payload_time_sec) + float(persist_build_time_sec) + float(report_time_sec)
        )
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
        redirect_err_ctx.__exit__(None, None, None)

        # Release GPU timeline slot after GA + FG (and any deferred-post early returns).
        if gpu_mode and int(_gpu_song_slot) > 0 and _prefetch_mgr is not None:
            try:
                _prefetch_mgr.release(int(_gpu_song_slot))
            except Exception:
                pass


def safe_process_song_task(args) -> SongResultPayload:
    """
    Wrapper around process_song_task that never raises across process boundaries.
    Returns an error payload with traceback if anything escapes, to avoid crashing pools.

    Args:
        args: Arguments tuple for process_song_task

    Returns:
        dict: Result dict or error dict with _error and _trace keys
    """
    song_name = "Unknown"
    queue_label = None
    try:
        if isinstance(args, (list, tuple)) and len(args) > 1:
            song_name = args[1]
            queue_label = str(song_name)
            try:
                if len(args) > 16:
                    for extra in args[16:]:
                        if not isinstance(extra, dict):
                            continue
                        if "repeat_index" in extra and "repeat_total" in extra:
                            idx = int(extra.get("repeat_index") or 0)
                            total = int(extra.get("repeat_total") or 0)
                            if idx > 0 and total > 1:
                                queue_label = f"{song_name} (Run {idx}/{total})"
                            break
            except Exception:
                queue_label = str(song_name)
        return process_song_task(args)
    except Exception as exc:
        tb = traceback.format_exc()
        msg = f"[safe_process_song_task] {song_name} failed: {type(exc).__name__}: {exc}"
        try:
            logging.error(msg + "\n" + tb)
            print(msg, file=sys.stderr)
        except Exception:
            pass
        return build_error_payload(
            song_name=str(song_name),
            queue_key=str(queue_label or song_name),
            queue_label=str(queue_label or song_name),
            exc=exc,
            trace=tb,
        )
