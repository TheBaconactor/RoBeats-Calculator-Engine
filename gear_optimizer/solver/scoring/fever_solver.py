"""
Fever Solver - Fever Timeline and Gem Combination Optimization.

This module provides the main gem solver pipeline:
- precompute_fever_timelines: Precompute valid fever timelines for all FT/FF gem combinations
- solve_best_fever_combination: Main gem solver - optimizes gem allocation for maximum score

    Coordinates between:
    - Rules Layer (fever_timeline.py): Timeline calculation, SongTimelineGrid
    - Compute Layer (scoring_core.py): Score calculation, gem optimization
    - GPU Layer (taichi_gem.api): GPU-accelerated batch optimization
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
from ...core.color_flags import build_color_flags
from ...core.utils import safe_int

from ..fever_timeline import (
    get_song_timeline_grid,
)

from ..scoring_core import (
    fast_calculate_score,
    lookup_reference_py,
    optimize_core_jit,
)
from ..base_stats import build_stats_array
from ..registry_solve_request import RegistrySolveRequest, dispatch_registry_solve

from .stats_scoring import evaluate_stats_score
from .stats_ops import apply_gems_to_base_stats


def precompute_fever_timelines(
    base_stats,
    calc_song,
    ref_arrays,
    budget,
    max_ft_gems,
    max_ff_gems,
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

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    base_stats = initial_stats.copy()

    # GPU-only policy: production behavior must rely on GPU/Taichi/Vulkan.
    # Keep the CPU reference path available only when override_cfg explicitly disables GPU.
    if not override_cfg and not use_gpu:
        print("[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); forcing GPU_Mode=true.")
        use_gpu = True

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
        # CPU reference evaluation (no gem optimization).
        song_timestamps = calc_song["song_data"]["timestamps"]
        long_notes = int(calc_song["metadata"].get("Long Notes", 0))
        last_note = float(calc_song["metadata"].get("Last Note Time", 0))
        total_notes = len(song_timestamps)

        fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)
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

    flags = build_color_flags(p_color, s_color, selected_color)
    is_p_pp = flags["is_p_pp"]
    is_s_pp = flags["is_s_pp"]
    is_p_cm = flags["is_p_cm"]
    is_s_cm = flags["is_s_cm"]
    is_p_fm = flags["is_p_fm"]
    is_s_fm = flags["is_s_fm"]
    is_p_ov = flags["is_p_ov"]
    is_s_ov = flags["is_s_ov"]

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

    # GPU path: use the grid-based FT/FF solver (default), eliminating CPU timeline enumeration
    # and per-work-item fever mask transfers.
    if use_gpu:
        # Compute color contribution flags for FT/FF gems (FT gems add Beat, FF gems add Vibe).
        is_p_ft = flags["is_p_ft"]
        is_s_ft = flags["is_s_ft"]
        is_p_ff = flags["is_p_ff"]
        is_s_ff = flags["is_s_ff"]

        try:
            song_slot = int((calc_song or {}).get("_gpu_song_slot", 0) or 0)
        except Exception:
            song_slot = 0

        # Single-genome registry payload:
        # - Keep this path on the same registry/native dispatch used by batch evaluators.
        # - Use empty per-slot item pools and encode all fixed stats in base_fixed_stats.
        population_indices = np.zeros((1, 9), dtype=np.int32)
        item_stats = np.zeros((1, 10), dtype=np.int32)
        slot_start = np.zeros((9,), dtype=np.int32)
        slot_count = np.zeros((9,), dtype=np.int32)
        base_fixed_stats = build_stats_array(base_stats)

        request = RegistrySolveRequest(
            population_indices=population_indices,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats=base_fixed_stats,
            timeline_grid=calc_song,
            ref_arrays=ref_arrays,
            flags={
                "is_p_ft": int(is_p_ft),
                "is_s_ft": int(is_s_ft),
                "is_p_ff": int(is_p_ff),
                "is_s_ff": int(is_s_ff),
                "is_p_pp": int(is_p_pp),
                "is_s_pp": int(is_s_pp),
                "is_p_cm": int(is_p_cm),
                "is_s_cm": int(is_s_cm),
                "is_p_fm": int(is_p_fm),
                "is_s_fm": int(is_s_fm),
                "is_p_ov": int(is_p_ov),
                "is_s_ov": int(is_s_ov),
            },
            total_budget=int(TOTAL_GEM_BUDGET),
            gem_scale_fever=int(GEM_SCALE_FEVER),
            song_slot=int(song_slot),
        )
        gpu_results = dispatch_registry_solve(request)

        if not gpu_results:
            raise RuntimeError("GPU solver returned no results.")

        score, ft, ff, g_pp, g_cm, g_fm, g_ov = gpu_results[0]
        best_score = int(score)
        best_tuple = (best_score, int(ft), int(ff), int(g_pp), int(g_cm), int(g_fm), int(g_ov))

    if not use_gpu:
        # CPU reference path: enumerate all fever timelines, then optimize PP/CM/FM/OV per timeline.
        song_timestamps = calc_song["song_data"]["timestamps"]
        total_notes = len(song_timestamps)

        # 1. Precompute Timelines (Rules Layer)
        # This generates all valid fever scenarios without doing gem optimization yet.
        timelines = precompute_fever_timelines(
            base_stats,
            calc_song,
            ref_arrays,
            TOTAL_GEM_BUDGET,
            max_ft_gems,
            max_ff_gems,
        )

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
        final_stats = apply_gems_to_base_stats(
            base_stats,
            selected_color,
            ft,
            ff,
            g_pp,
            g_cm,
            g_fm,
            g_ov,
            add_missing_element_key=False,
        )

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
