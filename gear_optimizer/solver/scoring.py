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

    return {
        "Score": res["Score"],
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
    Evaluate entire population in a single GPU batch call.
    
    This is the GPU-optimized version that:
    1. Aggregates all genome stats in a batch (CPU vectorized)
    2. Calls GPU solver ONCE for all uncached genomes
    3. Returns results in same order as input population
    
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
    base_get = base_stats_fixed.get
    
    # Aggregate stats for each genome
    all_stats = []
    for genome in uncached_genomes:
        current_stats = base_stats_fixed.copy()
        for item in genome:
            for k, v in item.items():
                if k not in SKIP_ITEM_KEYS:
                    current_stats[k] = current_stats.get(k, 0) + v
        all_stats.append(current_stats)
    
    # Check stat-signature cache for deduplication
    sig_to_result = {}
    unique_stats = []
    unique_indices = []  # Maps unique_stats index -> list of uncached_indices
    
    for i, stats in enumerate(all_stats):
        sig = stats_signature(stats, calc_song, sel_color)
        cached = GEM_SOLVER_CACHE.get(sig)
        if cached is not None:
            sig_to_result[i] = cached
        else:
            # Check if same sig already in unique_stats
            found = False
            for j, (prev_sig, prev_stats) in enumerate(unique_stats):
                if prev_sig == sig:
                    unique_indices[j].append(i)
                    found = True
                    break
            if not found:
                unique_stats.append((sig, stats))
                unique_indices.append([i])
    
    # Call GPU solver for unique uncached stats
    if unique_stats:
        for j, (sig, stats) in enumerate(unique_stats):
            res = solve_best_fever_combination(
                None, stats, calc_song, ref_arrays,
                silent=True, override_cfg=cfg_data,
            )
            GEM_SOLVER_CACHE[sig] = res
            # Apply to all genomes with this signature
            for idx in unique_indices[j]:
                sig_to_result[idx] = res
    
    # Build results for uncached genomes
    uncached_results = {}
    for i, (genome, stats) in enumerate(zip(uncached_genomes, all_stats)):
        res = sig_to_result[i]
        gear_part = genome[:6]
        mini_part = genome[6:]
        mini_names = [m["Name"] for m in mini_part]
        
        result = {
            "Score": res["Score"],
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

    non_fever_cas = max(0.0, (total_notes - long_notes) * 0.333)
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    non_fever_great_to_fill = ceil(max(1.0, (non_fever_cas * fever_fill_rate) * 2.0))
    fever_time_cas = last_note_time * 0.15 + 0.15
    real_fever_time = fever_time_cas * fever_time_stat

    force_counts = list(forced_counts or [])
    fever_mask = np.zeros(total_notes, dtype=np.bool_)
    current_idx = 0
    non_fever_section = 0
    section_details = []

    while current_idx < total_notes:
        non_fever_section += 1
        base_notes = non_fever_base - 1 if non_fever_section == 1 else non_fever_base
        base_notes = max(0, base_notes)
        forced_val = 0
        if non_fever_section - 1 < len(force_counts):
            forced_val = max(0, int(force_counts[non_fever_section - 1]))
        forced_val = min(forced_val, non_fever_base)
        fill_penalty_notes = ceil(
            max(0.0, (non_fever_base * forced_val) / non_fever_great_to_fill)
        )
        notes_to_fill = base_notes + fill_penalty_notes
        section_start = current_idx
        end_normal = min(section_start + notes_to_fill, total_notes)
        actual_notes = max(0, end_normal - section_start)
        forced_applied = min(forced_val, actual_notes)

        section_details.append(
            {
                "start_idx": section_start,
                "notes": actual_notes,
                "forced": forced_applied,
                "fill_penalty_notes": fill_penalty_notes,
                "skip_wasted": (non_fever_section == 1),
            }
        )
        current_idx = end_normal
        if current_idx >= total_notes:
            break

        start_time = timestamps[current_idx]
        end_time = start_time + real_fever_time
        fever_end_idx = int(np.searchsorted(timestamps, end_time, side="left"))
        if fever_end_idx <= current_idx:
            fever_end_idx = min(total_notes, current_idx + 1)
        fever_mask[current_idx:fever_end_idx] = True
        current_idx = fever_end_idx

    head_limit = min(total_notes, 100)
    fever_mask_head = fever_mask[:head_limit]
    if total_notes > 100:
        body_slice = fever_mask[100:]
        count_body_fever = int(np.count_nonzero(body_slice))
        count_body_normal = max(len(body_slice) - count_body_fever, 0)
    else:
        count_body_fever = 0
        count_body_normal = 0

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


def run_force_greats_hill_climb(stats, calc_song, ref_arrays):
    """
    Simple hill-climb optimizer that increments forced greats per section
    while the total score improves.
    """
    baseline = evaluate_force_greats(stats, calc_song, ref_arrays, [])
    if not baseline:
        return None

    best_counts = [0] * baseline["num_non_fever_sections"]
    best_result = evaluate_force_greats(stats, calc_song, ref_arrays, best_counts)
    if not best_result or best_result["num_non_fever_sections"] == 0:
        return best_result

    improved = True
    while improved:
        improved = False
        for idx in range(best_result["num_non_fever_sections"]):
            candidate_counts = best_counts[:]
            if idx >= len(candidate_counts):
                candidate_counts.extend([0] * (idx + 1 - len(candidate_counts)))
            candidate_counts[idx] += 1
            candidate = evaluate_force_greats(stats, calc_song, ref_arrays, candidate_counts)
            if candidate and candidate["final_score"] > best_result["final_score"]:
                best_counts = candidate_counts
                best_result = candidate
                improved = True
                break
    return best_result


def apply_force_greats_to_result(
    data_dict,
    calc_song,
    ref_arrays,
    manual_counts=None,
    use_finder=False,
):
    """
    Evaluate forced-great penalties (manual config or hill-climb finder) for a result dict.
    Returns a cloned variant with the adjusted score while leaving the original untouched.
    Uses FG_CACHE to avoid redundant calculations for identical stats.
    """
    if not data_dict or "Stats" not in data_dict:
        return None

    stats = data_dict.get("Stats") or {}
    if not stats:
        return None

    # Build cache key from stats signature + FG parameters
    selected_color = data_dict.get("Selected Element", calc_song["metadata"].get("Primary Color", ""))
    base_sig = stats_signature(stats, calc_song, selected_color)
    manual_tuple = tuple(manual_counts) if manual_counts else ()
    fg_cache_key = (base_sig, use_finder, manual_tuple)

    # Check cache first
    cached_fg = FG_CACHE.get(fg_cache_key)
    if cached_fg is not None:
        fg_result = cached_fg
    else:
        if use_finder:
            fg_result = run_force_greats_hill_climb(stats, calc_song, ref_arrays)
        else:
            fg_result = evaluate_force_greats(stats, calc_song, ref_arrays, manual_counts)
        # Cache the result (even if None)
        FG_CACHE[fg_cache_key] = fg_result

    if not fg_result:
        return None

    fg_info = {
        "enabled": True,
        "config": fg_result["config_dict"],
        "base_score": fg_result["base_score"],
        "final_score": fg_result["final_score"],
        "score_penalty": fg_result["score_penalty"],
        "fill_penalty": fg_result["fill_penalty"],
        "total_penalty": fg_result["total_penalty"],
        "num_non_fever_sections": fg_result["num_non_fever_sections"],
        "penalty_analysis": fg_result["penalty_analysis"],
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
        use_gpu = cfg.getboolean("IterationEngine", "GPU_GemSolver", fallback=False) if hasattr(cfg, 'getboolean') else False

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

        final_stats["Perfect Points"] += g_pp * GEM_SCALE_NORMAL
        final_stats["Combo Multiplier"] += g_cm * GEM_SCALE_NORMAL
        final_stats["Fever Multiplier"] += g_fm * GEM_SCALE_FEVER

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
            "GemCounts": gem_counts,
            "Stats": final_stats,
            "Selected Element": selected_color,
        }

    return {}
