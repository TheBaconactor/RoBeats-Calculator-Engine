"""
Fever Solver - Fever Timeline and Gem Combination Optimization.

This module provides the main gem solver pipeline:
- precompute_fever_timelines: Precompute valid fever timelines for all FT/FF gem combinations
- solve_best_fever_combination: Main gem solver - optimizes gem allocation for maximum score

Coordinates between:
- Rules Layer (fever_timeline.py): Timeline calculation, SongTimelineGrid
- Compute Layer (scoring_core.py): Score calculation, gem optimization
- GPU Layer (taichi_gem_solver): GPU-accelerated batch optimization
"""

import numpy as np
from math import floor

from ...core.constants import (
    TOTAL_ROWS,
    MAX_STAT_INDEX,
    TOTAL_GEM_BUDGET,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
)
from ...core.utils import safe_int

from ..fever_timeline import (
    get_song_timeline_grid,
    lookup_reference_py,
)

from ..scoring_core import (
    fast_calculate_score,
    optimize_core_jit,
)

from .gpu_solver import _get_gpu_solver, _GPU_LOCK
from .stats_scoring import evaluate_stats_score


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
            - timeline: Tuple where the first 3 elements are:
              (fever_mask_head, count_body_fever, count_body_normal). Additional
              trailing fields may exist depending on timeline implementation.
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

            results.append(
                {
                    "ft_gems": ft,
                    "ff_gems": ff,
                    "ft_stat_val": stat_ft_val,
                    "ff_stat_val": stat_ff_val,
                    "ft_factor": ft_factor,
                    "ff_factor": ff_factor,
                    "timeline": timeline,
                    "remaining_budget": budget - ft - ff,
                }
            )

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
        user_cm = safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0))
        user_fm = safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0))
        selected_color = calc_song["metadata"].get("Primary Color", "Rush")
        static_elem_input = safe_int(cfg.get("ElementalGems", selected_color, fallback=0))
        use_gpu = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False) if hasattr(cfg, "getboolean") else False

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

    # Normalize ref arrays to float32 so CPU and GPU paths use identical numeric behavior
    # regardless of input dtype (tests may pass float64 arrays).
    #
    # Performance: avoid rebuilding a new dict when inputs are already float32.
    ref_pp_raw = ref_arrays["Perfect Points"]
    ref_cm_raw = ref_arrays["Combo Multiplier"]
    ref_fm_raw = ref_arrays["Fever Multiplier"]
    ref_ft_raw = ref_arrays["Fever Time"]
    ref_ff_raw = ref_arrays["Fever Fill Rate"]

    need_ref_cast = False
    for _arr in (ref_pp_raw, ref_cm_raw, ref_fm_raw, ref_ft_raw, ref_ff_raw):
        try:
            if np.asarray(_arr).dtype != np.float32:
                need_ref_cast = True
                break
        except Exception:
            need_ref_cast = True
            break

    if need_ref_cast:
        ref_arrays = dict(ref_arrays)
        ref_arrays["Perfect Points"] = np.asarray(ref_pp_raw, dtype=np.float32)
        ref_arrays["Combo Multiplier"] = np.asarray(ref_cm_raw, dtype=np.float32)
        ref_arrays["Fever Multiplier"] = np.asarray(ref_fm_raw, dtype=np.float32)
        ref_arrays["Fever Time"] = np.asarray(ref_ft_raw, dtype=np.float32)
        ref_arrays["Fever Fill Rate"] = np.asarray(ref_ff_raw, dtype=np.float32)

    ref_pp = ref_arrays["Perfect Points"]
    ref_cm = ref_arrays["Combo Multiplier"]
    ref_fm = ref_arrays["Fever Multiplier"]

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
                "Element": static_elem_input,
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
                fever_mask_head = timeline[0]
                count_body_fever = timeline[1]
                count_body_normal = timeline[2]

                batch_input.append(
                    {
                        "budget": current_budget,
                        "fever_mask_head": fever_mask_head,
                        "count_body_fever": count_body_fever,
                        "count_body_normal": count_body_normal,
                        "ft_gems": ft,
                        "ff_gems": ff,
                    }
                )

            # SINGLE GPU kernel launch for ALL timelines - GPU-resident!
            # Direct call with lock for minimal overhead (scheduler queue was too slow)
            with _GPU_LOCK:
                batch_results = batch_solver(
                    batch_input,
                    cur_pp,
                    cur_cm,
                    cur_fm,
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

            fever_mask_head = timeline[0]
            count_body_fever = timeline[1]
            count_body_normal = timeline[2]

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

            base = (final_p_val * 2) + final_s_val + lookup_reference_py(final_pp, ref_pp, TOTAL_ROWS)
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
        # Apply gem contributions to the *primary stats* as well as their elemental
        # mappings. These are required for correct persistence/UI rendering and for
        # downstream logic that reverses gem effects (e.g. ForceGreats base extraction).
        final_stats["Perfect Points"] += g_pp * GEM_SCALE_NORMAL
        final_stats["Combo Multiplier"] += g_cm * GEM_SCALE_NORMAL
        final_stats["Fever Multiplier"] += g_fm * GEM_SCALE_FEVER
        final_stats["Fever Time"] += ft * GEM_SCALE_FEVER
        final_stats["Fever Fill Rate"] += ff * GEM_SCALE_FEVER

        final_stats["Chill"] += g_pp * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Flow"] += g_cm * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Rush"] += g_fm * GEM_STAT_TO_ELEMENT_SCALE
        final_stats["Beat"] = base_stats.get("Beat", 0) + (ft * GEM_STAT_TO_ELEMENT_SCALE)
        final_stats["Vibe"] = base_stats.get("Vibe", 0) + (ff * GEM_STAT_TO_ELEMENT_SCALE)

        if selected_color in final_stats:
            final_stats[selected_color] += g_ov * ELEMENTAL_GEM_SCALE

        gem_counts = {
            "Perfect Points": g_pp,
            "Combo Multiplier": g_cm,
            "Fever Multiplier": g_fm,
            "Element": g_ov,
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
