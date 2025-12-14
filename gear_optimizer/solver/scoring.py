"""
Score calculation engine - orchestration layer.

This module orchestrates the scoring process by combining:
- Rules Layer (fever_timeline.py): Timeline calculation, SongTimelineGrid
- Compute Layer (scoring_core.py): Score calculation, gem optimization

Uses LRU caching to avoid redundant calculations.
"""
import numpy as np
from math import floor, ceil
from cachetools import LRUCache
import threading # Added threading import

from ..core.constants import (
    TOTAL_ROWS,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
)
from ..core.utils import safe_int, safe_float, stats_signature, SKIP_ITEM_KEYS

# Import from Rules Layer
from .fever_timeline import (
    SongTimelineGrid,
    get_song_timeline_grid,
    calculate_fever_timeline_indices,
    calculate_force_greats_timeline_indices,
    calculate_non_fever_sections,
    lookup_reference_py,
    SONG_TIMELINE_GRIDS,
)

# Import from Compute Layer
from .scoring_core import (
    lookup_reference_jit,
    fast_calculate_score,
    optimize_core_jit,
)

# GPU Gem Solver (lazy import to avoid init overhead if not used)
_gpu_solver_loaded = False
_optimize_gems_gpu = None
_optimize_gems_batch_gpu = None
_GPU_LOCK = threading.Lock()  # Serialize GPU kernel calls

def _get_gpu_solver():
    """Lazy-load the GPU gem solver to avoid Taichi init on import."""
    global _gpu_solver_loaded, _optimize_gems_gpu, _optimize_gems_batch_gpu
    if not _gpu_solver_loaded:
        try:
            from .taichi_gem_solver import (
                optimize_gems_gpu,
                optimize_gems_batch_gpu,
                load_ref_arrays,
            )
            _optimize_gems_gpu = optimize_gems_gpu
            _optimize_gems_batch_gpu = optimize_gems_batch_gpu
            _gpu_solver_loaded = True
        except ImportError as e:
            print(f"[GPU] Failed to load Taichi gem solver: {e}")
            _optimize_gems_gpu = None
            _optimize_gems_batch_gpu = None
            _gpu_solver_loaded = True  # Mark as attempted
    return _optimize_gems_gpu, _optimize_gems_batch_gpu

# Global caches for performance optimization
GEM_SOLVER_CACHE = LRUCache(maxsize=5000)
FEVER_TIMELINE_CACHE = LRUCache(maxsize=10000)
FG_CACHE = LRUCache(maxsize=2000)

# Bump this whenever ForceGreats evaluation semantics change, so we can invalidate
# stale DB-cached FG payloads (they can otherwise look like "score inflation").
FORCE_GREATS_ALGO_VERSION = 3

# Max FT/FF gems to iterate - derived from total budget (can't exceed it)
MAX_FT_FF_GEMS = TOTAL_GEM_BUDGET


def worker_coevolution_evaluate(args):
    """
    Evaluates a Co-Evolution Individual (genome = gear + minis).

    Uses a stat-signature cache: if multiple gear+mini combinations produce
    the same effective stats for the song's Primary/Secondary/Selected paths,
    we reuse the gem solver result instead of recomputing.

    This is called in parallel by the genetic algorithm.

    Args:
        args: Tuple of (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)

    Returns:
        dict: Evaluation result with score, genome, gear, minis, and data
    """
    (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays) = args

    current_stats = base_stats_fixed.copy()
    cs = current_stats
    cs_get = cs.get

    # Aggregate stats from all items in genome
    for item in genome:
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                cs[k] = cs_get(k, 0) + v

    # Check stat-signature cache before calling the expensive gem solver
    sel_color = cfg_data["selected_color"]
    sig = stats_signature(current_stats, calc_song, sel_color)
    cached = GEM_SOLVER_CACHE.get(sig)

    if cached is None:
        res = solve_best_fever_combination(
            None,
            current_stats,
            calc_song,
            ref_arrays,
            silent=True,
            override_cfg=cfg_data,
        )
        GEM_SOLVER_CACHE[sig] = res
    else:
        res = cached

    gear_part = genome[:6]
    mini_part = genome[6:]
    mini_names = [m["Name"] for m in mini_part]

    base_score = res["Score"]

    # CRITICAL: Inject BaseScore into res so it propagates through all caching layers
    # and reaches build_db_payload for correct DB storage. Without this, the heuristic
    # score would be stored instead of the true base score.
    res["BaseScore"] = base_score

    return {
        "Score": base_score,  # Used for GA selection
        "BaseScore": base_score,  # True base score (all perfects)
        "Genome": genome,
        "Gear": gear_part,
        "Minis": mini_part,
        "MiniNames": mini_names,
        "Data": res,
    }


def batch_evaluate_genomes(
    population: list,
    base_stats_fixed: dict,
    cfg_data: dict,
    calc_song: dict,
    ref_arrays: dict,
    genome_key_fn=None,
    evaluation_cache: dict = None,
) -> list:
    """
    Evaluate entire population in a SINGLE GPU kernel launch.
    
    MEGA-BATCH VERSION:
    1. Aggregate stats for all genomes
    2. Precompute all timelines (using cached SongTimelineGrid)
    3. Flatten ALL timelines from ALL genomes into one work list
    4. Launch ONE GPU kernel for all work items
    5. Reduce results per genome
    
    Args:
        population: List of genomes (each genome is list of item dicts)
        base_stats_fixed: Fixed base stats dictionary
        cfg_data: Configuration data
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        genome_key_fn: Optional function to generate genome keys for caching
        evaluation_cache: Optional cache dict to use
        
    Returns:
        list: Evaluation results in same order as population
    """
    if not population:
        return []
    
    # Check if GPU is enabled
    use_gpu = cfg_data.get("use_gpu", False)
    
    # Use cache if provided
    use_cache = genome_key_fn is not None and evaluation_cache is not None
    
    # Split into cached and uncached
    cached_results = {}
    uncached_genomes = []
    uncached_indices = []
    
    for i, genome in enumerate(population):
        if use_cache:
            key = genome_key_fn(genome)
            if key in evaluation_cache:
                cached_results[i] = evaluation_cache[key]
            else:
                uncached_genomes.append(genome)
                uncached_indices.append(i)
        else:
            uncached_genomes.append(genome)
            uncached_indices.append(i)
    
    # If all cached, return immediately
    if not uncached_genomes:
        return [cached_results[i] for i in range(len(population))]
    
    # Batch aggregate stats for all uncached genomes
    sel_color = cfg_data["selected_color"]
    
    # Aggregate stats for each genome (simple dict accumulation)
    all_stats = []
    for genome in uncached_genomes:
        current_stats = base_stats_fixed.copy()
        for item in genome:
            for k, v in item.items():
                if k not in SKIP_ITEM_KEYS:
                    current_stats[k] = current_stats.get(k, 0) + v
        all_stats.append(current_stats)
    
    # Check stat-signature cache for deduplication (O(n))
    sig_to_result = {}
    unique_stats = []  # [(sig, representative_stats)]
    sig_to_unique_idx = {}  # sig -> unique_idx
    unique_members = []  # unique_idx -> [genome_idx]

    # Fix regression: cache key must include user gem config.
    # (sig is a tuple, so we append via tuple concatenation)
    config_sig = (
        cfg_data["user_ft"],
        cfg_data["user_ff"],
        cfg_data["user_pp"],
        cfg_data["user_cm"],
        cfg_data["user_fm"],
        cfg_data["static_elem_input"],
    )

    for i, stats in enumerate(all_stats):
        base_sig = stats_signature(stats, calc_song, sel_color)
        sig = base_sig + config_sig

        cached = GEM_SOLVER_CACHE.get(sig)
        if cached is not None:
            sig_to_result[i] = cached
            continue

        unique_idx = sig_to_unique_idx.get(sig)
        if unique_idx is None:
            unique_idx = len(unique_stats)
            sig_to_unique_idx[sig] = unique_idx
            unique_stats.append((sig, stats))
            unique_members.append([i])
        else:
            unique_members[unique_idx].append(i)
    
    # GPU V2 FAST PATH - Full parallelization across (genome, ft, ff) combinations
    # This launches ~400k threads instead of 500, giving full GPU utilization!
    gpu_results = None
    if unique_stats and use_gpu:
        from .taichi_gem_solver import solve_genomes_parallel
        from .fever_timeline import get_song_timeline_grid
        
        # Get precomputed timeline grid for this song
        grid = get_song_timeline_grid(calc_song, ref_arrays)
        grid.precompute_all()  # Eagerly cache all 161x161 timelines (one-time ~0.5s cost)
        
        p_color = calc_song["metadata"].get("Primary Color", "")
        s_color = calc_song["metadata"].get("Secondary Color", "")
        
        user_ft = cfg_data["user_ft"]
        user_ff = cfg_data["user_ff"]
        user_pp = cfg_data["user_pp"]
        user_cm = cfg_data["user_cm"]
        user_fm = cfg_data["user_fm"]
        static_elem_input = cfg_data["static_elem_input"]
        
        # Build genome stats list for GPU kernel
        genome_stats_list = []
        
        for unique_idx, (sig, stats) in enumerate(unique_stats):
            # Compute base stat values (before gems) - kernel handles gem allocation
            base_pp = stats.get("Perfect Points", 0) - user_pp * GEM_SCALE_NORMAL
            base_cm = stats.get("Combo Multiplier", 0) - user_cm * GEM_SCALE_NORMAL
            base_fm = stats.get("Fever Multiplier", 0) - user_fm * GEM_SCALE_FEVER
            base_ft_stat = stats.get("Fever Time", 0) - user_ft * GEM_SCALE_FEVER
            base_ff_stat = stats.get("Fever Fill Rate", 0) - user_ff * GEM_SCALE_FEVER
            
            # Primary/Secondary elemental values
            # CAUTION: We must DEDUCT user-forced gems because the kernel adds them back!
            base_beat = stats.get("Beat", 0) - user_ft * GEM_STAT_TO_ELEMENT_SCALE
            base_vibe = stats.get("Vibe", 0) - user_ff * GEM_STAT_TO_ELEMENT_SCALE
            base_rush = stats.get("Rush", 0) - user_fm * GEM_STAT_TO_ELEMENT_SCALE
            base_flow = stats.get("Flow", 0) - user_cm * GEM_STAT_TO_ELEMENT_SCALE
            base_chill = stats.get("Chill", 0) - user_pp * GEM_STAT_TO_ELEMENT_SCALE
            
            # Deduct static overflow gems (if any)
            if sel_color == "Beat":
                base_beat -= static_elem_input * ELEMENTAL_GEM_SCALE
            elif sel_color == "Vibe":
                base_vibe -= static_elem_input * ELEMENTAL_GEM_SCALE
            elif sel_color == "Rush":
                base_rush -= static_elem_input * ELEMENTAL_GEM_SCALE
            elif sel_color == "Flow":
                base_flow -= static_elem_input * ELEMENTAL_GEM_SCALE
            elif sel_color == "Chill":
                base_chill -= static_elem_input * ELEMENTAL_GEM_SCALE

            # Select P/S values from deducted stats
            color_vals = {"Beat": base_beat, "Vibe": base_vibe, "Rush": base_rush, "Flow": base_flow, "Chill": base_chill}
            base_p_val = color_vals.get(p_color, 0)
            base_s_val = color_vals.get(s_color, 0)
            
            genome_stats_list.append({
                "base_pp": int(base_pp),
                "base_cm": int(base_cm),
                "base_fm": int(base_fm),
                "base_p_val": int(base_p_val),
                "base_s_val": int(base_s_val),
                "base_ft_stat": int(base_ft_stat),
                "base_ff_stat": int(base_ff_stat),
            })
        
        # Color flags (shared across all genomes for the same song)
        is_p_pp = 1 if "Chill" == p_color else 0
        is_s_pp = 1 if "Chill" == s_color else 0
        is_p_cm = 1 if "Flow" == p_color else 0
        is_s_cm = 1 if "Flow" == s_color else 0
        is_p_fm = 1 if "Rush" == p_color else 0
        is_s_fm = 1 if "Rush" == s_color else 0
        is_p_ov = 1 if sel_color == p_color else 0
        is_s_ov = 1 if sel_color == s_color else 0
        is_p_ft = 1 if "Beat" == p_color else 0
        is_s_ft = 1 if "Beat" == s_color else 0
        is_p_ff = 1 if "Vibe" == p_color else 0
        is_s_ff = 1 if "Vibe" == s_color else 0
        
        # V2 KERNEL: Parallelizes across (genome, ft, ff) = ~400k threads!
        # Route through GPU executor IPC in worker process mode
        from .gpu_executor import is_gpu_worker_mode, submit_gpu_solve_genomes
        
        try:
            if is_gpu_worker_mode():
                # IPC route to GPU executor (parallel song processing).
                # Pass lightweight `calc_song` dict to avoid pickling a full
                # SongTimelineGrid across IPC (can trigger WinError 1450).
                gpu_results = submit_gpu_solve_genomes(
                    genome_stats_list,
                    calc_song,
                    is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                    is_p_pp, is_s_pp, is_p_cm, is_s_cm,
                    is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                    ref_arrays,
                    total_budget=TOTAL_GEM_BUDGET,
                    gem_scale_fever=GEM_SCALE_FEVER,
                )
            else:
                # Direct GPU call (sequential mode or main process)
                with _GPU_LOCK:
                    gpu_results = solve_genomes_parallel(
                        genome_stats_list,
                        grid,  # Timeline grid - uploaded once
                        is_p_ft, is_s_ft, is_p_ff, is_s_ff,
                        is_p_pp, is_s_pp, is_p_cm, is_s_cm,
                        is_p_fm, is_s_fm, is_p_ov, is_s_ov,
                        ref_arrays,
                        total_budget=TOTAL_GEM_BUDGET,
                        gem_scale_fever=GEM_SCALE_FEVER,
                    )
        except Exception as e:
            # Fail-safe: never allow GPU/IPC issues to crash multi-song processing.
            print(f"[batch_evaluate_genomes] GPU path failed, falling back to CPU: {type(e).__name__}: {e}")
            gpu_results = None
        
    if unique_stats:
        if gpu_results is not None and len(gpu_results) < len(unique_stats):
            print(
                f"[batch_evaluate_genomes] GPU returned {len(gpu_results)}/{len(unique_stats)} results; "
                "filling missing via CPU"
            )

        # Populate sig_to_result for every uncached signature.
        for unique_idx, (sig, rep_stats) in enumerate(unique_stats):
            if gpu_results is None or unique_idx >= len(gpu_results):
                # CPU fallback for this signature (or entire GPU path failed).
                res = solve_best_fever_combination(
                    None, rep_stats, calc_song, ref_arrays,
                    silent=True, override_cfg=cfg_data,
                )
                GEM_SOLVER_CACHE[sig] = res
                members = unique_members[unique_idx] if unique_idx < len(unique_members) else []
                for i in members:
                    sig_to_result[i] = res
                continue

            score, g_ft, g_ff, g_pp, g_cm, g_fm, g_ov = gpu_results[unique_idx]
            score = int(score)
            g_ft = int(g_ft)
            g_ff = int(g_ff)
            g_pp = int(g_pp)
            g_cm = int(g_cm)
            g_fm = int(g_fm)
            g_ov = int(g_ov)

            members = unique_members[unique_idx] if unique_idx < len(unique_members) else []
            cache_written = False

            for i in members:
                if i in sig_to_result:
                    continue

                stats = all_stats[i]

                # Build final_stats with gem values (match CPU path for ForceGreats compatibility)
                final_stats = stats.copy()
                final_stats["Fever Time"] = final_stats.get("Fever Time", 0) + g_ft * GEM_SCALE_FEVER
                final_stats["Fever Fill Rate"] = final_stats.get("Fever Fill Rate", 0) + g_ff * GEM_SCALE_FEVER
                final_stats["Perfect Points"] = final_stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
                final_stats["Combo Multiplier"] = final_stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
                final_stats["Fever Multiplier"] = final_stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
                final_stats["Chill"] = final_stats.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
                final_stats["Flow"] = final_stats.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
                final_stats["Rush"] = final_stats.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
                final_stats["Beat"] = final_stats.get("Beat", 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
                final_stats["Vibe"] = final_stats.get("Vibe", 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE
                if sel_color in final_stats:
                    final_stats[sel_color] = final_stats.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE

                res = {
                    "Score": score,
                    "FT": g_ft,
                    "FF": g_ff,
                    "GemCounts": {
                        "Perfect Points": g_pp,
                        "Combo Multiplier": g_cm,
                        "Fever Multiplier": g_fm,
                        "Element Overflow": g_ov,
                    },
                    "Stats": final_stats,
                    "Selected Element": sel_color,
                }
                sig_to_result[i] = res
                if not cache_written:
                    # Cache one representative result for this signature
                    GEM_SOLVER_CACHE[sig] = res
                    cache_written = True
    
    # Build results for uncached genomes
    uncached_results = {}
    for i, (genome, stats) in enumerate(zip(uncached_genomes, all_stats)):
        res = sig_to_result.get(i)
        if res is None:
            # Safety net: if the GPU/CPU signature mapping missed this index, evaluate it now.
            base_sig = stats_signature(stats, calc_song, sel_color)
            sig = base_sig + config_sig
            res = GEM_SOLVER_CACHE.get(sig)
            if res is None:
                res = solve_best_fever_combination(
                    None, stats, calc_song, ref_arrays,
                    silent=True, override_cfg=cfg_data,
                )
                GEM_SOLVER_CACHE[sig] = res
            sig_to_result[i] = res
        gear_part = genome[:6]
        mini_part = genome[6:]
        mini_names = [m["Name"] for m in mini_part]
        
        base_score = res["Score"]
        
        # CRITICAL: Inject BaseScore into res so it propagates through all caching layers
        # and reaches build_db_payload for correct DB storage.
        res["BaseScore"] = base_score
        
        result = {
            "Score": base_score,  # Used for GA selection
            "BaseScore": base_score,  # True base score (all perfects)
            "Genome": genome,
            "Gear": gear_part,
            "Minis": mini_part,
            "MiniNames": mini_names,
            "Data": res,
        }
        
        uncached_results[uncached_indices[i]] = result
        
        # Update cache if provided
        if use_cache:
            key = genome_key_fn(genome)
            evaluation_cache[key] = result
    
    # Combine cached and uncached results
    all_results = []
    for i in range(len(population)):
        if i in cached_results:
            all_results.append(cached_results[i])
        else:
            all_results.append(uncached_results[i])
    
    return all_results


def evaluate_stats_score(
    stats,
    calc_song,
    ref_arrays,
    song_timestamps=None,
    long_notes=None,
    last_note=None,
    fever_mask_buffer=None,
):
    """
    Return total score for a fixed stats snapshot without gem reallocations.

    This is used when you just want to evaluate a loadout without optimizing gems.

    Args:
        stats: Stats dictionary
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        song_timestamps: Optional precomputed timestamps
        long_notes: Optional long notes count
        last_note: Optional last note time
        fever_mask_buffer: Optional preallocated fever mask buffer

    Returns:
        int: Total score
    """
    timestamps = (
        song_timestamps if song_timestamps is not None else calc_song["song_data"]["timestamps"]
    )
    total_notes = len(timestamps)
    long_count = (
        long_notes
        if long_notes is not None
        else safe_int(calc_song["metadata"].get("Long Notes"), 0)
    )
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_time = (
        last_note
        if last_note is not None
        else safe_float(calc_song["metadata"].get("Last Note Time"), default_last_note)
    )
    mask_buffer = fever_mask_buffer
    if mask_buffer is None or mask_buffer.shape[0] != total_notes:
        mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    ft_factor = lookup_reference_py(stats["Fever Time"], ref_arrays["Fever Time"], TOTAL_ROWS)
    ff_factor = lookup_reference_py(stats["Fever Fill Rate"], ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_mask_head, count_body_fever, count_body_normal, _ = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        ff_factor,
        ft_factor,
        long_count,
        last_time,
        mask_buffer,
    )

    base_pp = lookup_reference_py(stats["Perfect Points"], ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats["Combo Multiplier"], ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats["Fever Multiplier"], ref_arrays["Fever Multiplier"], TOTAL_ROWS)

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    primary_val = stats.get(p_color, 0)
    secondary_val = stats.get(s_color, 0)
    total_base = (primary_val * 2) + secondary_val + base_pp

    return fast_calculate_score(
        total_base,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )


def _force_greats_counts_to_dict(counts, sections):
    """Convert force counts to config dict."""
    config = {}
    for idx in range(sections):
        val = counts[idx] if idx < len(counts) else 0
        config[f"NonFever{idx + 1}"] = max(0, int(val))
    return config


def build_great_penalty_table(base_value, combo_mul, great_penalty_base, head_limit=100):
    """
    Precompute ramp penalties for the first `head_limit` notes.
    Avoids recalculating scaling when evaluating force-great permutations.
    """
    penalties = [0] * head_limit
    combo_span = combo_mul - 1.0
    for idx in range(head_limit):
        scaling = 1.0 + combo_span * (idx + 1) / 100.0
        perfect_val = floor(base_value * scaling)
        great_val = floor(great_penalty_base * scaling)
        penalties[idx] = max(0, perfect_val - great_val)
    return penalties


def fg_baseline_params(stats, calc_song, ref_arrays):
    """
    Lightweight baseline computation for ForceGreatsFinder batching.

    Returns:
        (num_non_fever_sections, non_fever_base)
    """
    if not stats or not calc_song:
        return 0, 0

    timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(timestamps)
    if total_notes <= 0:
        return 0, 0

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    ref_ff = ref_arrays["Fever Fill Rate"]
    ref_ft = ref_arrays["Fever Time"]

    fever_fill_rate = lookup_reference_py(stats.get("Fever Fill Rate", 0), ref_ff, TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats.get("Fever Time", 0), ref_ft, TOTAL_ROWS)
    non_fever_section, non_fever_base = calculate_non_fever_sections(
        timestamps,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
    )

    return int(non_fever_section), int(non_fever_base)


def _song_cache_key(calc_song):
    meta = calc_song.get("metadata", {}) or {}
    timestamps = calc_song.get("song_data", {}).get("timestamps", ())
    return (
        str(meta.get("Song Name", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
    )


def _compute_force_greats_timeline(
    timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes,
    last_note_time,
    force_counts,
    *,
    clamp_base_notes_nonnegative,
    clamp_forced_to_section_notes,
):
    fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    forced_arr = (
        np.asarray(force_counts, dtype=np.int32)
        if force_counts
        else np.zeros(0, dtype=np.int32)
    )

    # Worst-case: section count is bounded by note count (+1 for safety).
    section_cap = int(total_notes) + 1
    section_start = np.zeros(section_cap, dtype=np.int32)
    section_forced = np.zeros(section_cap, dtype=np.int32)
    section_fill_penalty = np.zeros(section_cap, dtype=np.int32)
    section_skip_wasted = np.zeros(section_cap, dtype=np.bool_)

    (
        fever_mask_head_view,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_count,
    ) = calculate_force_greats_timeline_indices(
        timestamps,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
        forced_arr,
        int(forced_arr.shape[0]),
        bool(clamp_base_notes_nonnegative),
        bool(clamp_forced_to_section_notes),
        fever_mask_buffer,
        section_start,
        section_forced,
        section_fill_penalty,
        section_skip_wasted,
    )

    section_details = []
    for i in range(int(section_count)):
        base_notes = non_fever_base - 1 if (i == 0) else non_fever_base
        if clamp_base_notes_nonnegative:
            base_notes = max(0, int(base_notes))
        notes_to_fill = int(base_notes) + int(section_fill_penalty[i])

        section_details.append(
            {
                "start_idx": int(section_start[i]),
                "forced": int(section_forced[i]),
                "fill_penalty_notes": int(section_fill_penalty[i]),
                "skip_wasted": bool(section_skip_wasted[i]),
                "notes": notes_to_fill,
            }
        )

    return (
        fever_mask_head_view.copy(),
        int(count_body_fever),
        int(count_body_normal),
        int(non_fever_base),
        section_details,
    )


def evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=None):
    """
    Recompute fever timeline and penalties when greats are forced in non-fever sections.
    Returns None when prerequisites are missing.
    """
    if not stats or not calc_song:
        return None

    timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(timestamps)
    if total_notes <= 0:
        return None

    metadata = calc_song["metadata"]
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    primary_color = metadata.get("Primary Color", "")
    secondary_color = metadata.get("Secondary Color", "")
    primary_val = stats.get(primary_color, 0)
    secondary_val = stats.get(secondary_color, 0)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ff = ref_arrays["Fever Fill Rate"]
    ref_ft = ref_arrays["Fever Time"]

    pp_factor = lookup_reference_py(stats["Perfect Points"], ref_pp, TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats["Combo Multiplier"], ref_cm, TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats["Fever Multiplier"], ref_fm, TOTAL_ROWS)
    fever_fill_rate = lookup_reference_py(stats["Fever Fill Rate"], ref_ff, TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats["Fever Time"], ref_ft, TOTAL_ROWS)

    base_value = (primary_val * 2) + secondary_val + pp_factor
    combo_value = floor(base_value * combo_mul)
    great_penalty_base = floor(((primary_val * 2) + secondary_val) * (2.0 / 3.0) + 150.0)
    great_combo_value = floor(great_penalty_base * combo_mul)
    penalty_table = build_great_penalty_table(base_value, combo_mul, great_penalty_base)
    body_penalty = max(0, combo_value - great_combo_value)

    force_counts = list(forced_counts or [])
    (
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_details,
    ) = _compute_force_greats_timeline(
        timestamps,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
        force_counts,
        clamp_base_notes_nonnegative=True,
        clamp_forced_to_section_notes=True,
    )

    base_score = fast_calculate_score(
        base_value,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )

    total_score_penalty = 0
    total_fill_penalty = 0
    penalty_analysis = {}
    for idx, detail in enumerate(section_details):
        section_key = f"NonFever{idx + 1}"
        fill_penalty_score = detail["fill_penalty_notes"] * combo_value
        total_fill_penalty += fill_penalty_score
        forced = detail["forced"]
        if forced > 0:
            start_idx = detail["start_idx"]
            if detail.get("skip_wasted"):
                start_idx = min(total_notes, start_idx + 1)
            score_penalty = 0
            note_idx = start_idx
            remaining = forced
            while remaining > 0:
                if note_idx < len(penalty_table):
                    score_penalty += penalty_table[note_idx]
                else:
                    score_penalty += body_penalty
                note_idx += 1
                remaining -= 1
        else:
            score_penalty = 0
        total_score_penalty += score_penalty
        penalty_analysis[section_key] = {
            "forced_greats": forced,
            "score_penalty": score_penalty,
            "fill_penalty": fill_penalty_score,
            "total_penalty": score_penalty + fill_penalty_score,
        }

    used_counts = force_counts[:]
    if len(used_counts) < len(section_details):
        used_counts.extend([0] * (len(section_details) - len(used_counts)))

    return {
        "base_score": base_score,
        "final_score": max(0, base_score - total_score_penalty),
        "score_penalty": total_score_penalty,
        "fill_penalty": total_fill_penalty,
        "total_penalty": total_score_penalty + total_fill_penalty,
        "num_non_fever_sections": len(section_details),
        "config_counts": used_counts[: len(section_details)],
        "config_dict": _force_greats_counts_to_dict(used_counts, len(section_details)),
        "penalty_analysis": penalty_analysis,
        "non_fever_base": non_fever_base,
    }


# Cache for FG timeline calculations (keyed by FG config tuple)
FG_TIMELINE_CACHE = LRUCache(maxsize=1000)


def evaluate_fg_with_gem_iteration(
    base_stats,
    calc_song,
    ref_arrays,
    selected_color,
    forced_counts,
    search_ranges=None,
    use_gpu: bool = False,
):
    """
    ForceGreats evaluation WITH full gem solver (FT/FF iteration).
    
    This function:
    1. Calculates the FG timeline for the given forced_counts
    2. Iterates ALL (FT, FF) combinations (like the main gem solver)
    3. For each (FT, FF), optimizes PP/CM/FM/OV gems
    4. Returns the best result with optimal gems for this FG config
    
    Args:
        base_stats: Stats BEFORE gem optimization (gear+mini only)
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        selected_color: Selected elemental color for overflow gems
        forced_counts: List of forced great counts per non-fever section
        
    Returns:
        dict: Result with final_score and optimal gem allocation
    """
    if not base_stats or not calc_song:
        return None

    timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(timestamps)
    if total_notes <= 0:
        return None

    metadata = calc_song["metadata"]
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    p_color = metadata.get("Primary Color", "")
    s_color = metadata.get("Secondary Color", "")

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ff = ref_arrays["Fever Fill Rate"]
    ref_ft = ref_arrays["Fever Time"]

    # Color contribution flags
    is_p_pp = 1 if "Chill" == p_color else 0
    is_s_pp = 1 if "Chill" == s_color else 0
    is_p_cm = 1 if "Flow" == p_color else 0
    is_s_cm = 1 if "Flow" == s_color else 0
    is_p_fm = 1 if "Rush" == p_color else 0
    is_s_fm = 1 if "Rush" == s_color else 0
    is_p_ft = 1 if "Beat" == p_color else 0
    is_s_ft = 1 if "Beat" == s_color else 0
    is_p_ff = 1 if "Vibe" == p_color else 0
    is_s_ff = 1 if "Vibe" == s_color else 0
    is_p_ov = 1 if selected_color == p_color else 0
    is_s_ov = 1 if selected_color == s_color else 0

    # Base stats (pre-gem)
    base_pp = base_stats.get("Perfect Points", 0)
    base_cm = base_stats.get("Combo Multiplier", 0)
    base_fm = base_stats.get("Fever Multiplier", 0)
    base_ff_stat = base_stats.get("Fever Fill Rate", 0)
    base_ft_stat = base_stats.get("Fever Time", 0)
    base_beat = base_stats.get("Beat", 0)
    base_vibe = base_stats.get("Vibe", 0)

    # Base elemental values for GPU solver (kernel adds FT/FF elemental contributions)
    base_p_val_for_gpu = base_stats.get(p_color, 0)
    base_s_val_for_gpu = base_stats.get(s_color, 0)

    non_fever_cas = max(0.0, (total_notes - long_notes) * 0.333)
    force_counts = list(forced_counts or [])
    song_key = _song_cache_key(calc_song)

    # Determine iteration ranges
    if search_ranges:
        start_ft, end_ft, start_ff, end_ff = search_ranges
        start_ft = max(0, int(start_ft))
        end_ft = min(MAX_FT_FF_GEMS, int(end_ft))
        start_ff = max(0, int(start_ff))
        end_ff = min(MAX_FT_FF_GEMS, int(end_ff))
    else:
        start_ft, end_ft = 0, MAX_FT_FF_GEMS
        start_ff, end_ff = 0, MAX_FT_FF_GEMS

    # Collect candidates first (so we can do a single GPU batch call when enabled)
    candidates = []  # preserves (ft, ff) iteration order
    batch_input = []

    for ft_gems in range(start_ft, end_ft + 1):
        remaining_after_ft = TOTAL_GEM_BUDGET - ft_gems
        if remaining_after_ft < 0:
            break

        ff_end = min(end_ff, remaining_after_ft)
        for ff_gems in range(start_ff, ff_end + 1):
            current_budget = remaining_after_ft - ff_gems
            if current_budget < 0:
                break

            # Look up fever parameters with FT/FF gems applied
            cur_ft_stat = base_ft_stat + ft_gems * GEM_SCALE_FEVER
            cur_ff_stat = base_ff_stat + ff_gems * GEM_SCALE_FEVER
            fever_fill_rate = lookup_reference_py(cur_ff_stat, ref_ff, TOTAL_ROWS)
            fever_time_stat = lookup_reference_py(cur_ft_stat, ref_ft, TOTAL_ROWS)
            non_fever_base = ceil(non_fever_cas * fever_fill_rate)

            # Timeline cache includes FT, FF, forced_counts, and song identity.
            # We also cache section_details because FG penalties need start indices.
            fg_cache_key = (ft_gems, ff_gems, tuple(force_counts), song_key)
            cached = FG_TIMELINE_CACHE.get(fg_cache_key)

            if cached is None:
                (
                    fever_mask_head,
                    count_body_fever,
                    count_body_normal,
                    _nf_base_from_jit,
                    section_details,
                ) = _compute_force_greats_timeline(
                    timestamps,
                    total_notes,
                    fever_fill_rate,
                    fever_time_stat,
                    long_notes,
                    last_note_time,
                    force_counts,
                    clamp_base_notes_nonnegative=False,
                    clamp_forced_to_section_notes=False,
                )

                cached = (fever_mask_head, count_body_fever, count_body_normal, section_details)
                FG_TIMELINE_CACHE[fg_cache_key] = cached

            fever_mask_head, count_body_fever, count_body_normal, section_details = (
                cached
            )

            # CPU optimizer expects p/s values with FT/FF elemental contributions already applied.
            cur_beat = base_beat + ft_gems * GEM_STAT_TO_ELEMENT_SCALE
            cur_vibe = base_vibe + ff_gems * GEM_STAT_TO_ELEMENT_SCALE
            cur_p_val = (
                cur_beat
                if p_color == "Beat"
                else (
                    cur_vibe
                    if p_color == "Vibe"
                    else base_stats.get(p_color, 0)
                )
            )
            cur_s_val = (
                cur_beat
                if s_color == "Beat"
                else (
                    cur_vibe
                    if s_color == "Vibe"
                    else base_stats.get(s_color, 0)
                )
            )

            candidates.append(
                (
                    ft_gems,
                    ff_gems,
                    current_budget,
                    non_fever_base,
                    fever_mask_head,
                    count_body_fever,
                    count_body_normal,
                    section_details,
                    cur_p_val,
                    cur_s_val,
                )
            )

            if use_gpu:
                batch_input.append(
                    {
                        "budget": current_budget,
                        "fever_mask_head": fever_mask_head,
                        "count_body_fever": count_body_fever,
                        "count_body_normal": count_body_normal,
                        "ft_gems": ft_gems,
                        "ff_gems": ff_gems,
                    }
                )

    # Optional GPU batch optimization (falls back to CPU if Taichi/GPU isn't available)
    gpu_results = None
    if use_gpu and batch_input:
        _, batch_solver = _get_gpu_solver()
        if batch_solver is not None:
            try:
                with _GPU_LOCK:
                    gpu_results = batch_solver(
                        batch_input,
                        base_pp,
                        base_cm,
                        base_fm,
                        base_p_val=base_p_val_for_gpu,
                        base_s_val=base_s_val_for_gpu,
                        is_p_ft=is_p_ft,
                        is_s_ft=is_s_ft,
                        is_p_ff=is_p_ff,
                        is_s_ff=is_s_ff,
                        is_p_pp=is_p_pp,
                        is_s_pp=is_s_pp,
                        is_p_cm=is_p_cm,
                        is_s_cm=is_s_cm,
                        is_p_fm=is_p_fm,
                        is_s_fm=is_s_fm,
                        is_p_ov=is_p_ov,
                        is_s_ov=is_s_ov,
                        ref_arrays=ref_arrays,
                    )
            except Exception as e:
                print(f"[GPU] FG batch solver failed; falling back to CPU: {e}")
                gpu_results = None

    best_result = None
    best_score = -1

    # Evaluate each candidate (CPU or GPU) in deterministic order.
    for idx, cand in enumerate(candidates):
        (
            ft_gems,
            ff_gems,
            current_budget,
            non_fever_base,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
            section_details,
            cur_p_val,
            cur_s_val,
        ) = cand

        if gpu_results is not None:
            res = gpu_results[idx]
            gems_pp = int(res[6])
            gems_cm = int(res[7])
            gems_fm = int(res[8])
            gems_ov = int(res[9])
            final_p_val = int(res[4])
            final_s_val = int(res[5])
            final_pp = base_pp + gems_pp * GEM_SCALE_NORMAL
            final_cm = base_cm + gems_cm * GEM_SCALE_NORMAL
            final_fm = base_fm + gems_fm * GEM_SCALE_FEVER
        else:
            (
                final_pp,
                final_cm,
                final_fm,
                final_p_val,
                final_s_val,
                gems_pp,
                gems_cm,
                gems_fm,
                gems_ov,
            ) = optimize_core_jit(
                current_budget,
                base_pp,
                base_cm,
                base_fm,
                cur_p_val,
                cur_s_val,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                ref_pp,
                ref_cm,
                ref_fm,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
                GEM_SCALE_NORMAL,
                GEM_SCALE_FEVER,
                GEM_STAT_TO_ELEMENT_SCALE,
                ELEMENTAL_GEM_SCALE,
                TOTAL_ROWS,
                MAX_STAT_INDEX,
            )

        pp_factor = lookup_reference_py(final_pp, ref_pp, TOTAL_ROWS)
        combo_mul = lookup_reference_py(final_cm, ref_cm, TOTAL_ROWS)
        fever_mul = lookup_reference_py(final_fm, ref_fm, TOTAL_ROWS)

        base_value = (final_p_val * 2) + final_s_val + pp_factor
        base_score = fast_calculate_score(
            base_value,
            combo_mul,
            fever_mul,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
        )

        # FG penalties (score penalty for greats + fill penalty)
        combo_value = floor(base_value * combo_mul)
        great_penalty_base = floor(
            ((final_p_val * 2) + final_s_val) * (2.0 / 3.0) + 150.0
        )
        penalty_table = build_great_penalty_table(
            base_value, combo_mul, great_penalty_base
        )
        body_penalty = max(0, combo_value - floor(great_penalty_base * combo_mul))

        total_score_penalty = 0
        total_fill_penalty = 0
        penalty_analysis = {}

        for s_idx, detail in enumerate(section_details):
            section_key = f"NonFever{s_idx + 1}"
            fill_p_score = detail["fill_penalty_notes"] * combo_value
            total_fill_penalty += fill_p_score

            forced = detail["forced"]
            score_p = 0
            if forced > 0:
                start_idx = detail["start_idx"]
                if detail.get("skip_wasted"):
                    start_idx = min(total_notes, start_idx + 1)

                note_idx = start_idx
                remaining = forced
                while remaining > 0:
                    if note_idx < len(penalty_table):
                        score_p += penalty_table[note_idx]
                    else:
                        score_p += body_penalty
                    note_idx += 1
                    remaining -= 1

            total_score_penalty += score_p
            penalty_analysis[section_key] = {
                "forced_greats": forced,
                "score_penalty": score_p,
                "fill_penalty": fill_p_score,
                "total_penalty": score_p + fill_p_score,
            }

        final_score = max(0, base_score - total_score_penalty)

        if final_score > (best_score if best_result else -1):
            best_score = final_score
            best_result = {
                "base_score": base_score,
                "final_score": final_score,
                "score_penalty": total_score_penalty,
                "fill_penalty": total_fill_penalty,
                "total_penalty": total_score_penalty + total_fill_penalty,
                "num_non_fever_sections": len(section_details),
                "penalty_analysis": penalty_analysis,
                "config_counts": force_counts[:],
                "config_dict": _force_greats_counts_to_dict(
                    force_counts, max(2, len(force_counts))
                ),
                "non_fever_base": non_fever_base,
                "gem_counts": {
                    "Perfect Points": gems_pp,
                    "Combo Multiplier": gems_cm,
                    "Fever Multiplier": gems_fm,
                    "Element Overflow": gems_ov,
                },
                "FT": ft_gems,
                "FF": ff_gems,
            }

    return best_result


def run_force_greats_hill_climb(
    stats,
    calc_song,
    ref_arrays,
    selected_color=None,
    center_ft=None,
    center_ff=None,
    search_radius=5,
    use_gpu: bool = False,
):
    """
    Brute-force enumeration of all ForceGreats configurations WITH gem re-optimization.
    
    For each FG config, re-runs the full gem solver (FT/FF iteration) to find
    optimal gems for that specific FG timeline. This guarantees finding the
    global optimum instead of getting stuck with gems optimized for normal timeline.
    
    NOTE: This function now expects stats to be the gem-optimized Stats dict from
    the main solver. It extracts base stats and uses the new gem iteration function.
    """
    # Get baseline info from existing stats
    baseline = evaluate_force_greats(stats, calc_song, ref_arrays, [])
    if not baseline:
        return None

    num_sections = baseline["num_non_fever_sections"]
    if num_sections == 0:
        return baseline
    
    # Selected element is a loadout/config property (overflow target), not always the song primary.
    # Default to song primary only if missing.
    selected_color = selected_color or calc_song["metadata"].get("Primary Color", "Rush")
    
    # Extract base stats (before gems) - use stats directly since we want gear+mini stats
    # The GPU path now returns gem-adjusted stats, so we need to reverse
    # For simplicity, we can use the stats as-is since evaluate_fg_with_gem_iteration
    # handles the gem allocation internally
    base_stats = {}
    for key in ["Perfect Points", "Combo Multiplier", "Fever Multiplier", 
                "Fever Time", "Fever Fill Rate", "Chill", "Flow", "Rush", "Beat", "Vibe"]:
        base_stats[key] = stats.get(key, 0)

    # Get the max forced greats per section (notes-to-fill limit)
    non_fever_base = baseline.get("non_fever_base", 20)
    max_per_section = min(non_fever_base, 15)  # Cap at 15 due to FT/FF iteration cost
    
    # Calculate FT/FF search window (kept tight; full FT/FF × all FG configs explodes combinatorially)
    search_ranges = None
    if center_ft is not None and center_ff is not None:
        search_ranges = (
            center_ft - search_radius,
            center_ft + search_radius,
            center_ff - search_radius,
            center_ff + search_radius,
        )

    # Build FG config list in deterministic order (matches the legacy nested loops)
    counts_list = []
    if num_sections == 1:
        for s0 in range(max_per_section + 1):
            counts_list.append((s0,))
    elif num_sections == 2:
        for s0 in range(max_per_section + 1):
            for s1 in range(max_per_section + 1):
                counts_list.append((s0, s1))
    elif num_sections == 3:
        cap = min(max_per_section, 10)
        for s0 in range(cap + 1):
            for s1 in range(cap + 1):
                for s2 in range(cap + 1):
                    counts_list.append((s0, s1, s2))
    else:
        from itertools import product

        cap = min(max_per_section, 5)
        for counts in product(range(cap + 1), repeat=num_sections):
            counts_list.append(tuple(counts))

    # --------------------------------------------------------------------
    # FULL GPU FINDER PATH (when enabled):
    #   Runs FG timeline + gem optimization + penalties entirely on GPU and
    #   reduces to the best FG config per loadout.
    # --------------------------------------------------------------------
    if use_gpu:
        try:
            from .taichi_gem_solver import solve_force_greats_finder_gpu

            timestamps = calc_song["song_data"]["timestamps"]
            total_notes = len(timestamps)
            if total_notes <= 0:
                return None

            meta = calc_song.get("metadata", {}) or {}
            long_notes = safe_int(meta.get("Long Notes"), 0)
            default_last_note = timestamps[-1] if total_notes else 0.0
            last_note_time = safe_float(meta.get("Last Note Time"), default_last_note)
            p_color = meta.get("Primary Color", "")
            s_color = meta.get("Secondary Color", "")

            # Color contribution flags
            is_p_pp = 1 if "Chill" == p_color else 0
            is_s_pp = 1 if "Chill" == s_color else 0
            is_p_cm = 1 if "Flow" == p_color else 0
            is_s_cm = 1 if "Flow" == s_color else 0
            is_p_fm = 1 if "Rush" == p_color else 0
            is_s_fm = 1 if "Rush" == s_color else 0
            is_p_ft = 1 if "Beat" == p_color else 0
            is_s_ft = 1 if "Beat" == s_color else 0
            is_p_ff = 1 if "Vibe" == p_color else 0
            is_s_ff = 1 if "Vibe" == s_color else 0
            is_p_ov = 1 if selected_color == p_color else 0
            is_s_ov = 1 if selected_color == s_color else 0

            # FT/FF window list (no budgets here; GPU computes budget=total_budget-ft-ff)
            if search_ranges:
                start_ft, end_ft, start_ff, end_ff = search_ranges
                start_ft = max(0, int(start_ft))
                end_ft = min(MAX_FT_FF_GEMS, int(end_ft))
                start_ff = max(0, int(start_ff))
                end_ff = min(MAX_FT_FF_GEMS, int(end_ff))
            else:
                start_ft, end_ft = 0, MAX_FT_FF_GEMS
                start_ff, end_ff = 0, MAX_FT_FF_GEMS

            ftff_pairs = []
            for ft in range(start_ft, end_ft + 1):
                remaining_after_ft = TOTAL_GEM_BUDGET - ft
                if remaining_after_ft < 0:
                    break
                ff_end = min(end_ff, remaining_after_ft)
                for ff in range(start_ff, ff_end + 1):
                    if ft + ff <= TOTAL_GEM_BUDGET:
                        ftff_pairs.append((ft, ff))

            # Single-genome input (base stats; GPU allocates gems)
            genome_stats_list = [{
                "base_pp": int(base_stats.get("Perfect Points", 0)),
                "base_cm": int(base_stats.get("Combo Multiplier", 0)),
                "base_fm": int(base_stats.get("Fever Multiplier", 0)),
                "base_ft_stat": int(base_stats.get("Fever Time", 0)),
                "base_ff_stat": int(base_stats.get("Fever Fill Rate", 0)),
                "base_p_val": int(base_stats.get(p_color, 0)),
                "base_s_val": int(base_stats.get(s_color, 0)),
            }]

            out = solve_force_greats_finder_gpu(
                genome_stats_list,
                timestamps,
                long_notes,
                last_note_time,
                counts_list,
                ftff_pairs,
                n_sections=len(counts_list[0]) if counts_list else 1,
                is_p_ft=is_p_ft, is_s_ft=is_s_ft,
                is_p_ff=is_p_ff, is_s_ff=is_s_ff,
                is_p_pp=is_p_pp, is_s_pp=is_s_pp,
                is_p_cm=is_p_cm, is_s_cm=is_s_cm,
                is_p_fm=is_p_fm, is_s_fm=is_s_fm,
                is_p_ov=is_p_ov, is_s_ov=is_s_ov,
                ref_arrays=ref_arrays,
                total_budget=TOTAL_GEM_BUDGET,
                gem_scale_fever=GEM_SCALE_FEVER,
            )
            best = out[0] if out else None
            if not best:
                return None

            cfg_idx = best.get("cfg_idx", -1)
            cfg_counts = list(counts_list[cfg_idx]) if (cfg_idx is not None and 0 <= int(cfg_idx) < len(counts_list)) else []

            result = {
                "base_score": best.get("base_score", 0),
                "final_score": best.get("final_score", 0),
                "score_penalty": best.get("score_penalty", 0),
                "fill_penalty": best.get("fill_penalty", 0),
                "total_penalty": (best.get("score_penalty", 0) or 0) + (best.get("fill_penalty", 0) or 0),
                "num_non_fever_sections": num_sections,
                "penalty_analysis": {},  # optional; GPU path currently omits per-section breakdown
                "config_counts": cfg_counts,
                "config_dict": _force_greats_counts_to_dict(cfg_counts, max(2, len(cfg_counts))),
                "non_fever_base": non_fever_base,
                "gem_counts": best.get("gem_counts", {}) or {},
                "FT": best.get("FT", 0),
                "FF": best.get("FF", 0),
            }
            result["ForceGreats"] = {
                "config": result.get("config_dict", {}),
                "base_score": result.get("base_score", 0),
            }
            return result
        except Exception as e:
            print(f"[GPU] FG full finder failed; falling back to CPU: {e}")

    # --------------------------------------------------------------------
    # CPU fallback: evaluate each FG config individually (CPU-only)
    # --------------------------------------------------------------------
    best_result = None
    best_score = -1

    for counts in counts_list:
        candidate = evaluate_fg_with_gem_iteration(
            base_stats,
            calc_song,
            ref_arrays,
            selected_color,
            list(counts),
            search_ranges,
            use_gpu=False,
        )
        if candidate and candidate.get("final_score", -1) > (best_score if best_score >= 0 else -1):
            best_result = candidate
            best_score = candidate["final_score"]

    if best_result:
        best_result["ForceGreats"] = {
            "config": best_result.get("config_dict", {}),
            "base_score": best_result.get("base_score", 0),
        }

    return best_result
def _extract_base_stats(stats, gem_counts, selected_color, ft_gems=0, ff_gems=0):
    """
    Extract base stats (before gem optimization) by reversing gem contributions.
    
    NOTE: The GPU batch path returns pre-gem stats, while CPU path returns post-gem stats.
    This function detects which case we're in and acts accordingly.
    
    Args:
        stats: Stats dict (may or may not have gem contributions)
        gem_counts: GemCounts dict from result
        selected_color: Selected elemental color for overflow
        ft_gems: Number of Fever Time gems allocated
        ff_gems: Number of Fever Fill gems allocated
        
    Returns:
        dict: Base stats before gem optimization
    """
    if not gem_counts:
        return stats.copy()
    
    # Quick check: would reversal make a key value negative?
    # If so, stats is already pre-gem (GPU batch path returns "Stats": stats)
    g_ov = gem_counts.get("Element Overflow", 0)
    expected_reduction = g_ov * ELEMENTAL_GEM_SCALE  # ~469 for 67 gems
    current_val = stats.get(selected_color, 0) if selected_color else 0
    
    # If subtracting overflow gems would make it negative, stats is already base stats
    if current_val - expected_reduction < -50:  # Small tolerance for rounding
        # Stats is already pre-gem, just return a copy
        return stats.copy()
    
    # Stats has gem contributions baked in - need to reverse them
    base = stats.copy()
    
    # Reverse gem contributions
    g_pp = gem_counts.get("Perfect Points", 0)
    g_cm = gem_counts.get("Combo Multiplier", 0)
    g_fm = gem_counts.get("Fever Multiplier", 0)
    
    # Subtract stat gem contributions
    base["Perfect Points"] = base.get("Perfect Points", 0) - g_pp * GEM_SCALE_NORMAL
    base["Chill"] = base.get("Chill", 0) - g_pp * GEM_STAT_TO_ELEMENT_SCALE
    
    base["Combo Multiplier"] = base.get("Combo Multiplier", 0) - g_cm * GEM_SCALE_NORMAL
    base["Flow"] = base.get("Flow", 0) - g_cm * GEM_STAT_TO_ELEMENT_SCALE
    
    base["Fever Multiplier"] = base.get("Fever Multiplier", 0) - g_fm * GEM_SCALE_FEVER
    base["Rush"] = base.get("Rush", 0) - g_fm * GEM_STAT_TO_ELEMENT_SCALE
    
    # Subtract FT gem contributions (Fever Time + Beat color)
    base["Fever Time"] = base.get("Fever Time", 0) - ft_gems * GEM_SCALE_FEVER
    base["Beat"] = base.get("Beat", 0) - ft_gems * GEM_STAT_TO_ELEMENT_SCALE
    
    # Subtract FF gem contributions (Fever Fill Rate + Vibe color)
    base["Fever Fill Rate"] = base.get("Fever Fill Rate", 0) - ff_gems * GEM_SCALE_FEVER
    base["Vibe"] = base.get("Vibe", 0) - ff_gems * GEM_STAT_TO_ELEMENT_SCALE
    
    # Subtract overflow gem contributions
    if selected_color:
        base[selected_color] = base.get(selected_color, 0) - g_ov * ELEMENTAL_GEM_SCALE
    
    return base


def apply_force_greats_to_result(
    data_dict,
    calc_song,
    ref_arrays,
    manual_counts=None,
    use_finder=False,
    use_gpu: bool = False,
):
    """
    Evaluate forced-great penalties (manual config or hill-climb finder) for a result dict.
    Returns a cloned variant with the adjusted score while leaving the original untouched.
    Uses FG_CACHE to avoid redundant calculations for identical stats.
    
    FIXED: Now properly re-runs gem optimization for the FG timeline instead of
    using stats optimized for the normal timeline.
    """
    if not data_dict or "Stats" not in data_dict:
        return None

    stats = data_dict.get("Stats") or {}
    if not stats:
        return None
    
    gem_counts = data_dict.get("GemCounts") or {}
    selected_color = data_dict.get(
        "Selected Element", calc_song["metadata"].get("Primary Color", "")
    )
    ft_gems = data_dict.get("FT", 0)
    ff_gems = data_dict.get("FF", 0)
    
    # Use stats directly - the original evaluate_force_greats correctly uses
    # the FT/FF values already in stats (from the main gem solver)
    # Our "optimized" version was broken because optimize_core_jit doesn't allocate FT/FF

    # Build cache key from stats signature + FG parameters
    sig = stats_signature(stats, calc_song, selected_color)
    manual_tuple = tuple(manual_counts) if manual_counts else ()
    if use_finder:
        # Finder depends on the FT/FF search window center and (optionally) GPU mode.
        fg_cache_key = (sig, "finder", int(ft_gems), int(ff_gems), int(5), bool(use_gpu))
    else:
        fg_cache_key = (sig, "manual", manual_tuple)

    # Check cache first
    cached_fg = FG_CACHE.get(fg_cache_key)
    if cached_fg is not None:
        fg_result = cached_fg
    else:
        # Extract base stats (remove gems) to avoid double counting during re-optimization
        # The optimizer adds gems back in, so we must start clean.
        base_stats = _extract_base_stats(stats, gem_counts, selected_color, ft_gems, ff_gems)
        
        if use_finder:
            fg_result = run_force_greats_hill_climb(
                base_stats, 
                calc_song, 
                ref_arrays,
                selected_color=selected_color,
                center_ft=ft_gems,
                center_ff=ff_gems,
                use_gpu=use_gpu,
            )
        else:
            # Legacy/Manual path - does NOT re-optimize gems, so uses original stats (with gems)
            # Evaluate penalty on existing configuration
            fg_result = evaluate_force_greats(stats, calc_song, ref_arrays, manual_counts)
            
        # Cache the result (even if None)
        FG_CACHE[fg_cache_key] = fg_result

    if not fg_result:
        return None

    fg_info = {
        "enabled": True,
        "algo_version": FORCE_GREATS_ALGO_VERSION,
        "config": fg_result["config_dict"],
        "base_score": fg_result["base_score"],
        "final_score": fg_result["final_score"],
        "score_penalty": fg_result["score_penalty"],
        "fill_penalty": fg_result["fill_penalty"],
        "total_penalty": fg_result["total_penalty"],
        "num_non_fever_sections": fg_result["num_non_fever_sections"],
        "penalty_analysis": fg_result["penalty_analysis"],
        "finder": bool(use_finder),
        "gpu": bool(use_gpu) if use_finder else False,
        "center_ft": int(ft_gems) if use_finder else None,
        "center_ff": int(ff_gems) if use_finder else None,
        "search_radius": 5 if use_finder else None,
    }

    data_dict["ForceGreats"] = fg_info

    # Memory leak fix: Shallow copy is sufficient (only modifying top-level keys)
    # Eliminates 28K deepcopy operations per song
    fg_variant = data_dict.copy()
    fg_variant["Score"] = fg_result["final_score"]
    fg_variant["ForceGreats"] = {**fg_info, "variant_applied": True}
    return fg_variant


def precompute_fever_timelines(
    base_stats,
    calc_song,
    ref_arrays,
    budget,
    max_ft_gems,
    max_ff_gems,
    fever_mask_buffer,
):
    """
    Precompute valid fever timelines for all reachable FT/FF gem combinations.
    
    Uses SongTimelineGrid for O(1) lookups based on stat indices.
    Decouples the complex fever rules (timeline logic) from the optimization loop.
    
    Args:
        base_stats: Base stats dictionary (before gems)
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        budget: Total gem budget
        max_ft_gems: Max allowed Fever Time gems
        max_ff_gems: Max allowed Fever Fill Rate gems
        fever_mask_buffer: Unused (kept for API compatibility)
        
    Returns:
        list: List of dicts, each containing:
            - ft_gems: Number of FT gems
            - ff_gems: Number of FF gems
            - ft_stat_val: Resulting FT stat value
            - ff_stat_val: Resulting FF stat value
            - ft_factor: FT multiplier factor
            - ff_factor: FF multiplier factor
            - timeline: Tuple (fever_mask_head, count_body_fever, count_body_normal, activations)
            - remaining_budget: Budget left for other gems
    """
    results = []
    
    # Get or create the song's timeline grid
    grid = get_song_timeline_grid(calc_song, ref_arrays)
    
    # Extract base stats for computing final stat values
    base_ft_stat = base_stats["Fever Time"]
    base_ff_stat = base_stats["Fever Fill Rate"]
    
    range_ft = min(budget, max_ft_gems)
    
    for ft in range(range_ft + 1):
        remaining_for_ff = budget - ft
        range_ff = min(remaining_for_ff, max_ff_gems)
        
        # Calculate final stat value after applying gems
        stat_ft_val = base_ft_stat + (ft * GEM_SCALE_FEVER)
        # Clamp to grid index
        ft_idx = max(0, min(TOTAL_ROWS, int(stat_ft_val)))
        ft_factor = grid.ft_factors[ft_idx]
        
        for ff in range(range_ff + 1):
            stat_ff_val = base_ff_stat + (ff * GEM_SCALE_FEVER)
            ff_idx = max(0, min(TOTAL_ROWS, int(stat_ff_val)))
            ff_factor = grid.ff_factors[ff_idx]
            
            # O(1) lookup from grid (lazy-computed if first access)
            timeline = grid.get_timeline(ft_idx, ff_idx)
            
            results.append({
                "ft_gems": ft,
                "ff_gems": ff,
                "ft_stat_val": stat_ft_val,
                "ff_stat_val": stat_ff_val,
                "ft_factor": ft_factor,
                "ff_factor": ff_factor,
                "timeline": timeline,
                "remaining_budget": budget - ft - ff
            })
            
    return results


def solve_best_fever_combination(
    cfg,
    initial_stats,
    calc_song,
    ref_arrays,
    silent=False,
    override_cfg=None,
    skip_optimizer=False,
):
    """
    Main gem solver - optimizes gem allocation for maximum score.

    Iterates through FT/FF combinations and uses greedy JIT optimizer for PP/CM/FM/Overflow.
    Uses extensive caching to avoid redundant timeline and gem solver calculations.

    Args:
        cfg: Configuration object or None
        initial_stats: Initial stats dictionary
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        silent: Suppress console output if True
        override_cfg: Override config dictionary (for parallel evaluation)
        skip_optimizer: Skip optimization and just calculate score

    Returns:
        dict: Result with Score, FT, FF, GemCounts, Stats, Selected Element
    """
    if override_cfg:
        user_ft = override_cfg["user_ft"]
        user_ff = override_cfg["user_ff"]
        user_pp = override_cfg["user_pp"]
        user_cm = override_cfg["user_cm"]
        user_fm = override_cfg["user_fm"]
        selected_color = override_cfg["selected_color"]
        static_elem_input = override_cfg["static_elem_input"]
        use_gpu = override_cfg.get("use_gpu", False)
    else:
        if not silent:
            print("\n=== STARTING FEVER ITERATION ENGINE (GEM SOLVER) ===")
        user_ft = safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0))
        user_ff = safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0))
        user_pp = safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0))
        user_cm = safe_int(
            cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)
        )
        user_fm = safe_int(
            cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)
        )
        selected_color = calc_song["metadata"].get("Primary Color", "Rush")
        static_elem_input = safe_int(
            cfg.get("ElementalGems", selected_color, fallback=0)
        )
        use_gpu = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False) if hasattr(cfg, 'getboolean') else False

    base_stats = initial_stats.copy()

    # OPTIMIZATION: timestamps are already a NumPy array (set in __main__)
    song_timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(song_timestamps)
    long_notes = int(calc_song["metadata"].get("Long Notes", 0))
    last_note = float(calc_song["metadata"].get("Last Note Time", 0))
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")

    # Reuse mask buffer across FT/FF permutations to avoid repeated allocations.
    fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]
    ref_ft = ref_arrays["Fever Time"]
    ref_ff = ref_arrays["Fever Fill Rate"]

    if skip_optimizer:
        score = evaluate_stats_score(
            base_stats,
            calc_song,
            ref_arrays,
            song_timestamps=song_timestamps,
            long_notes=long_notes,
            last_note=last_note,
            fever_mask_buffer=fever_mask_buffer,
        )
        return {
            "Score": score,
            "FT": user_ft,
            "FF": user_ff,
            "GemCounts": {
                "Perfect Points": user_pp,
                "Combo Multiplier": user_cm,
                "Fever Multiplier": user_fm,
                "Element Overflow": static_elem_input,
            },
            "Stats": base_stats,
            "Selected Element": selected_color,
        }

    base_stats["Fever Time"] -= user_ft * GEM_SCALE_FEVER
    base_stats["Beat"] -= user_ft * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Fever Fill Rate"] -= user_ff * GEM_SCALE_FEVER
    base_stats["Vibe"] -= user_ff * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Fever Multiplier"] -= user_fm * GEM_SCALE_FEVER
    base_stats["Rush"] -= user_fm * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Combo Multiplier"] -= user_cm * GEM_SCALE_NORMAL
    base_stats["Flow"] -= user_cm * GEM_STAT_TO_ELEMENT_SCALE
    base_stats["Perfect Points"] -= user_pp * GEM_SCALE_NORMAL
    base_stats["Chill"] -= user_pp * GEM_STAT_TO_ELEMENT_SCALE
    base_stats[selected_color] -= static_elem_input * ELEMENTAL_GEM_SCALE

    remaining_ft_stat = MAX_STAT_INDEX - base_stats["Fever Time"]
    remaining_ff_stat = MAX_STAT_INDEX - base_stats["Fever Fill Rate"]
    max_ft_gems = floor(remaining_ft_stat / GEM_SCALE_FEVER) if remaining_ft_stat > 0 else 0
    max_ff_gems = floor(remaining_ff_stat / GEM_SCALE_FEVER) if remaining_ff_stat > 0 else 0

    if not silent:
        print(f"Max allocatable Gems: FT<={max_ft_gems}, Fill<={max_ff_gems}")
        print("Iterating permutations...")

    best_score = -1
    best_tuple = None

    is_p_pp = 1 if "Chill" == p_color else 0
    is_s_pp = 1 if "Chill" == s_color else 0
    is_p_cm = 1 if "Flow" == p_color else 0
    is_s_cm = 1 if "Flow" == s_color else 0
    is_p_fm = 1 if "Rush" == p_color else 0
    is_s_fm = 1 if "Rush" == s_color else 0
    is_p_ov = 1 if selected_color == p_color else 0
    is_s_ov = 1 if selected_color == s_color else 0

    base_beat = base_stats.get("Beat", 0)
    base_vibe = base_stats.get("Vibe", 0)

    bs_get = base_stats.get

    def get_val_inline(k, b, v):
        if k == "Beat":
            return b
        if k == "Vibe":
            return v
        return bs_get(k, 0)

    cur_pp = base_stats["Perfect Points"]
    cur_cm = base_stats["Combo Multiplier"]
    cur_fm = base_stats["Fever Multiplier"]

    # 1. Precompute Timelines (Rules Layer)
    # This generates all valid fever scenarios without doing gem optimization yet.
    timelines = precompute_fever_timelines(
        base_stats,
        calc_song,
        ref_arrays,
        TOTAL_GEM_BUDGET,
        max_ft_gems,
        max_ff_gems,
        fever_mask_buffer,
    )

    # 2. Optimize Gems for each Timeline
    if use_gpu:
        # GPU BATCH PATH: Process all timelines in parallel on GPU
        _, batch_solver = _get_gpu_solver()
        if batch_solver is not None:
            # Compute color contribution flags for FT/FF gems
            # FT gems add Beat, FF gems add Vibe
            is_p_ft = 1 if "Beat" == p_color else 0
            is_s_ft = 1 if "Beat" == s_color else 0
            is_p_ff = 1 if "Vibe" == p_color else 0
            is_s_ff = 1 if "Vibe" == s_color else 0
            
            # Base color values (before FT/FF gems)
            base_p_val = base_stats.get(p_color, 0)
            base_s_val = base_stats.get(s_color, 0)
            
            # Prepare batch input - each timeline becomes one batch element
            batch_input = []
            for t_data in timelines:
                ft = t_data["ft_gems"]
                ff = t_data["ff_gems"]
                timeline = t_data["timeline"]
                current_budget = t_data["remaining_budget"]
                fever_mask_head, count_body_fever, count_body_normal, _ = timeline
                
                batch_input.append({
                    "budget": current_budget,
                    "fever_mask_head": fever_mask_head,
                    "count_body_fever": count_body_fever,
                    "count_body_normal": count_body_normal,
                    "ft_gems": ft,
                    "ff_gems": ff,
                })
            
            # SINGLE GPU kernel launch for ALL timelines - GPU-resident!
            # Direct call with lock for minimal overhead (scheduler queue was too slow)
            with _GPU_LOCK:
                batch_results = batch_solver(
                    batch_input,
                    cur_pp, cur_cm, cur_fm,
                    base_p_val=base_p_val,
                    base_s_val=base_s_val,
                    is_p_ft=is_p_ft,
                    is_s_ft=is_s_ft,
                    is_p_ff=is_p_ff,
                    is_s_ff=is_s_ff,
                    is_p_pp=is_p_pp,
                    is_s_pp=is_s_pp,
                    is_p_cm=is_p_cm,
                    is_s_cm=is_s_cm,
                    is_p_fm=is_p_fm,
                    is_s_fm=is_s_fm,
                    is_p_ov=is_p_ov,
                    is_s_ov=is_s_ov,
                    ref_arrays=ref_arrays,
                )
            
            # Find best result (only CPU work: simple max)
            for i, (t_data, result) in enumerate(zip(timelines, batch_results)):
                ft = t_data["ft_gems"]
                ff = t_data["ff_gems"]
                # Result: (score, pp, cm, fm, p_val, s_val, gems_pp, gems_cm, gems_fm, gems_ov)
                total_score = result[0]
                g_pp = result[6]
                g_cm = result[7]
                g_fm = result[8]
                g_ov = result[9]
                
                if total_score > best_score:
                    best_score = total_score
                    best_tuple = (total_score, ft, ff, g_pp, g_cm, g_fm, g_ov)
        else:
            # Fallback to CPU if GPU failed
            use_gpu = False
    
    if not use_gpu:
        # CPU PATH: Sequential processing
        for t_data in timelines:
            ft = t_data["ft_gems"]
            ff = t_data["ff_gems"]
            timeline = t_data["timeline"]
            current_budget = t_data["remaining_budget"]
            
            fever_mask_head, count_body_fever, count_body_normal, _ = timeline
            
            # Calculate stats affected by FT/FF gems
            cur_beat = base_beat + (ft * GEM_STAT_TO_ELEMENT_SCALE)
            cur_vibe = base_vibe + (ff * GEM_STAT_TO_ELEMENT_SCALE)

            cur_p_val = get_val_inline(p_color, cur_beat, cur_vibe)
            cur_s_val = get_val_inline(s_color, cur_beat, cur_vibe)

            (
                final_pp,
                final_cm,
                final_fm,
                final_p_val,
                final_s_val,
                g_pp,
                g_cm,
                g_fm,
                g_ov,
            ) = optimize_core_jit(
                current_budget,
                cur_pp,
                cur_cm,
                cur_fm,
                cur_p_val,
                cur_s_val,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                ref_pp,
                ref_cm,
                ref_fm,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
                GEM_SCALE_NORMAL,
                GEM_SCALE_FEVER,
                GEM_STAT_TO_ELEMENT_SCALE,
                ELEMENTAL_GEM_SCALE,
                TOTAL_ROWS,
                MAX_STAT_INDEX,
            )

            base = (final_p_val * 2) + final_s_val + lookup_reference_py(
                final_pp, ref_pp, TOTAL_ROWS
            )
            c_mul = lookup_reference_py(final_cm, ref_cm, TOTAL_ROWS)
            f_mul = lookup_reference_py(final_fm, ref_fm, TOTAL_ROWS)
            total_score = fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                count_body_fever,
                count_body_normal,
            )

            if total_score > best_score:
                best_score = total_score
                best_tuple = (total_score, ft, ff, g_pp, g_cm, g_fm, g_ov)

    if best_tuple:
        (score, ft, ff, g_pp, g_cm, g_fm, g_ov) = best_tuple
        final_stats = base_stats.copy()
        final_stats["Fever Time"] += ft * GEM_SCALE_FEVER
        final_stats["Fever Fill Rate"] += ff * GEM_SCALE_FEVER

        final_stats["Chill"] += g_pp * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Flow"] += g_cm * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Rush"] += g_fm * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Beat"] = base_stats.get("Beat", 0) + (
            ft * GEM_STAT_TO_ELEMENT_SCALE
        )
        final_stats["Vibe"] = base_stats.get("Vibe", 0) + (
            ff * GEM_STAT_TO_ELEMENT_SCALE
        )

        if selected_color in final_stats:
            final_stats[selected_color] += g_ov * ELEMENTAL_GEM_SCALE

        gem_counts = {
            "Perfect Points": g_pp,
            "Combo Multiplier": g_cm,
            "Fever Multiplier": g_fm,
            "Element Overflow": g_ov,
        }
        return {
            "Score": score,
            "FT": ft,
            "FF": ff,
            "config": {
                "FT Gems": ft,
                "FF Gems": ff,
                "PP Gems": g_pp,
                "CM Gems": g_cm,
                "FM Gems": g_fm,
                "Overflow Gems": g_ov,
            },
            "FT_gems": ft,
            "FF_gems": ff,
            "gem_counts": gem_counts,
            "GemCounts": gem_counts,
            "Stats": final_stats,
            "Selected Element": selected_color,
        }

    return {}
