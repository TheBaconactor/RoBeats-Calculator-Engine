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
from ...core.config import GPUExecutionSettings
from ...core.gem_defs import UserGemsSettings, build_gem_counts

from ..fever_timeline import (
    get_song_timeline_grid,
)

from ..scoring_core import (
    fast_calculate_score,
    lookup_reference_py,
    optimize_core_jit,
)
from ..base_stats import build_base_fixed_stats_dict, build_stats_array
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


def _refine_gem_allocation_hint_fixed_ftff_cpu(
    *,
    budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_pp: np.ndarray,
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
    pp_gems: int,
    cm_gems: int,
    fm_gems: int,
    ov_gems: int,
) -> tuple[int, int, int, int, int]:
    """
    Refine a greedy gem allocation hint for a fixed (FT, FF) combination.

    Matches the GPU-side refinement used in Taichi kernels:
    - Keep PP fixed to the hint
    - Sweep FM in a bounded window
    - Coarse+fine scan CM (OV is the remainder)
    """
    budget = int(budget)
    if budget <= 0:
        return (0, int(pp_gems), int(cm_gems), int(fm_gems), int(ov_gems))

    allow_cm = (int(cur_cm) <= 50) or (int(is_p_cm) != 0) or (int(is_s_cm) != 0)
    if not allow_cm:
        # Baseline score for the provided hint (no refinement).
        pp_stat = min(MAX_STAT_INDEX, int(cur_pp) + int(pp_gems) * GEM_SCALE_NORMAL)
        cm_stat = min(MAX_STAT_INDEX, int(cur_cm) + int(cm_gems) * GEM_SCALE_NORMAL)
        fm_stat = min(MAX_STAT_INDEX, int(cur_fm) + int(fm_gems) * GEM_SCALE_FEVER)

        p_val = (
            int(cur_p_val)
            + int(pp_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_pp)
            + int(cm_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_cm)
            + int(fm_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_fm)
            + int(ov_gems) * ELEMENTAL_GEM_SCALE * int(is_p_ov)
        )
        s_val = (
            int(cur_s_val)
            + int(pp_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_pp)
            + int(cm_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_cm)
            + int(fm_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_fm)
            + int(ov_gems) * ELEMENTAL_GEM_SCALE * int(is_s_ov)
        )
        base = (p_val * 2) + s_val + lookup_reference_py(pp_stat, ref_pp, TOTAL_ROWS)
        c_mul = lookup_reference_py(cm_stat, ref_cm, TOTAL_ROWS)
        f_mul = lookup_reference_py(fm_stat, ref_fm, TOTAL_ROWS)
        score = int(
            fast_calculate_score(
                base,
                c_mul,
                f_mul,
                fever_mask_head,
                int(count_body_fever),
                int(count_body_normal),
            )
        )
        return (score, int(pp_gems), int(cm_gems), int(fm_gems), int(ov_gems))

    # Clamp caps.
    max_cm_gems = (MAX_STAT_INDEX - int(cur_cm)) // GEM_SCALE_NORMAL
    max_fm_gems = (MAX_STAT_INDEX - int(cur_fm)) // GEM_SCALE_FEVER
    if max_cm_gems < 0:
        max_cm_gems = 0
    if max_fm_gems < 0:
        max_fm_gems = 0

    pp_gems = int(pp_gems)
    if pp_gems < 0:
        pp_gems = 0

    # Sweep knobs (keep in sync with GPU refinement).
    FM_SWEEP = 12
    CM_STEP = 4

    # Baseline score at the hint.
    pp_stat = min(MAX_STAT_INDEX, int(cur_pp) + pp_gems * GEM_SCALE_NORMAL)
    pp_factor = lookup_reference_py(pp_stat, ref_pp, TOTAL_ROWS)

    cm_stat = min(MAX_STAT_INDEX, int(cur_cm) + int(cm_gems) * GEM_SCALE_NORMAL)
    fm_stat = min(MAX_STAT_INDEX, int(cur_fm) + int(fm_gems) * GEM_SCALE_FEVER)
    p_val0 = (
        int(cur_p_val)
        + pp_gems * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_pp)
        + int(cm_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_cm)
        + int(fm_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_fm)
        + int(ov_gems) * ELEMENTAL_GEM_SCALE * int(is_p_ov)
    )
    s_val0 = (
        int(cur_s_val)
        + pp_gems * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_pp)
        + int(cm_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_cm)
        + int(fm_gems) * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_fm)
        + int(ov_gems) * ELEMENTAL_GEM_SCALE * int(is_s_ov)
    )
    base0 = (p_val0 * 2) + s_val0 + pp_factor
    c_mul0 = lookup_reference_py(cm_stat, ref_cm, TOTAL_ROWS)
    f_mul0 = lookup_reference_py(fm_stat, ref_fm, TOTAL_ROWS)
    best_score = int(
        fast_calculate_score(
            base0,
            c_mul0,
            f_mul0,
            fever_mask_head,
            int(count_body_fever),
            int(count_body_normal),
        )
    )
    best_cm = int(cm_gems)
    best_fm = int(fm_gems)
    best_ov = int(ov_gems)

    # Local refinement when CM is already invested (avoid full CM scan cost; fix CM-nonzero top-1 misses).
    if int(cm_gems) != 0:
        fm_lo = max(0, int(fm_gems) - FM_SWEEP)
        fm_hi = min(int(max_fm_gems), int(fm_gems) + FM_SWEEP)
        cm0 = int(cm_gems)
        cm_window = CM_STEP - 1
        for fm_g in range(fm_lo, fm_hi + 1):
            rem0 = budget - pp_gems - fm_g
            if rem0 < 0:
                continue
            cm_max_here = min(int(max_cm_gems), int(rem0))
            if cm_max_here < 0:
                continue
            cm_lo = max(0, cm0 - cm_window)
            cm_hi = min(cm_max_here, cm0 + cm_window)

            fm_stat = min(MAX_STAT_INDEX, int(cur_fm) + fm_g * GEM_SCALE_FEVER)
            f_mul = lookup_reference_py(fm_stat, ref_fm, TOTAL_ROWS)
            for cm_g in range(cm_lo, cm_hi + 1):
                ov_g = rem0 - cm_g
                cm_stat = min(MAX_STAT_INDEX, int(cur_cm) + cm_g * GEM_SCALE_NORMAL)
                c_mul = lookup_reference_py(cm_stat, ref_cm, TOTAL_ROWS)
                p_val = (
                    int(cur_p_val)
                    + pp_gems * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_pp)
                    + cm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_cm)
                    + fm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_fm)
                    + ov_g * ELEMENTAL_GEM_SCALE * int(is_p_ov)
                )
                s_val = (
                    int(cur_s_val)
                    + pp_gems * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_pp)
                    + cm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_cm)
                    + fm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_fm)
                    + ov_g * ELEMENTAL_GEM_SCALE * int(is_s_ov)
                )
                base = (p_val * 2) + s_val + pp_factor
                score = int(
                    fast_calculate_score(
                        base,
                        c_mul,
                        f_mul,
                        fever_mask_head,
                        int(count_body_fever),
                        int(count_body_normal),
                    )
                )
                if score > best_score:
                    best_score = score
                    best_cm = cm_g
                    best_fm = fm_g
                    best_ov = ov_g

        return (int(best_score), int(pp_gems), int(best_cm), int(best_fm), int(best_ov))

    fm_lo = max(0, int(fm_gems) - FM_SWEEP)
    fm_hi = min(int(max_fm_gems), int(fm_gems) + FM_SWEEP)
    for fm_g in range(fm_lo, fm_hi + 1):
        rem0 = budget - pp_gems - fm_g
        if rem0 < 0:
            continue

        fm_stat = min(MAX_STAT_INDEX, int(cur_fm) + fm_g * GEM_SCALE_FEVER)
        f_mul = lookup_reference_py(fm_stat, ref_fm, TOTAL_ROWS)

        cm_max_here = min(int(max_cm_gems), int(rem0))
        if cm_max_here < 0:
            continue

        best_cm_local = 0
        best_score_local = -(2**31) + 1
        for cm_g in range(0, cm_max_here + 1, CM_STEP):
            ov_g = rem0 - cm_g
            cm_stat = min(MAX_STAT_INDEX, int(cur_cm) + cm_g * GEM_SCALE_NORMAL)
            c_mul = lookup_reference_py(cm_stat, ref_cm, TOTAL_ROWS)

            p_val = (
                int(cur_p_val)
                + pp_gems * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_pp)
                + cm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_cm)
                + fm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_fm)
                + ov_g * ELEMENTAL_GEM_SCALE * int(is_p_ov)
            )
            s_val = (
                int(cur_s_val)
                + pp_gems * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_pp)
                + cm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_cm)
                + fm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_fm)
                + ov_g * ELEMENTAL_GEM_SCALE * int(is_s_ov)
            )
            base = (p_val * 2) + s_val + pp_factor
            score = int(
                fast_calculate_score(
                    base,
                    c_mul,
                    f_mul,
                    fever_mask_head,
                    int(count_body_fever),
                    int(count_body_normal),
                )
            )
            if score > best_score_local:
                best_score_local = score
                best_cm_local = cm_g
            if score > best_score:
                best_score = score
                best_cm = cm_g
                best_fm = fm_g
                best_ov = ov_g

        cm_lo = max(0, best_cm_local - (CM_STEP - 1))
        cm_hi = min(cm_max_here, best_cm_local + (CM_STEP - 1))
        for cm_g in range(cm_lo, cm_hi + 1):
            ov_g = rem0 - cm_g
            cm_stat = min(MAX_STAT_INDEX, int(cur_cm) + cm_g * GEM_SCALE_NORMAL)
            c_mul = lookup_reference_py(cm_stat, ref_cm, TOTAL_ROWS)
            p_val = (
                int(cur_p_val)
                + pp_gems * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_pp)
                + cm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_cm)
                + fm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_p_fm)
                + ov_g * ELEMENTAL_GEM_SCALE * int(is_p_ov)
            )
            s_val = (
                int(cur_s_val)
                + pp_gems * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_pp)
                + cm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_cm)
                + fm_g * GEM_STAT_TO_ELEMENT_SCALE * int(is_s_fm)
                + ov_g * ELEMENTAL_GEM_SCALE * int(is_s_ov)
            )
            base = (p_val * 2) + s_val + pp_factor
            score = int(
                fast_calculate_score(
                    base,
                    c_mul,
                    f_mul,
                    fever_mask_head,
                    int(count_body_fever),
                    int(count_body_normal),
                )
            )
            if score > best_score:
                best_score = score
                best_cm = cm_g
                best_fm = fm_g
                best_ov = ov_g

    return (int(best_score), int(pp_gems), int(best_cm), int(best_fm), int(best_ov))


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
        selected_color = calc_song["metadata"].get("Primary Color", "Rush")
        user_gems = UserGemsSettings.from_config(cfg, selected_color=selected_color)
        user_ft = int(user_gems.fever_time)
        user_ff = int(user_gems.fever_fill)
        user_pp = int(user_gems.perfect_points)
        user_cm = int(user_gems.combo_multiplier)
        user_fm = int(user_gems.fever_multiplier)
        static_elem_input = int(user_gems.static_element)
        use_gpu = bool(GPUExecutionSettings.from_config(cfg).gpu_mode)

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
            "GemCounts": build_gem_counts(user_pp, user_cm, user_fm, static_elem_input),
            "Stats": base_stats,
            "Selected Element": selected_color,
        }

    base_stats, _selected_color = build_base_fixed_stats_dict(
        base_stats,
        {
            "user_ft": user_ft,
            "user_ff": user_ff,
            "user_pp": user_pp,
            "user_cm": user_cm,
            "user_fm": user_fm,
            "static_elem_input": static_elem_input,
            "selected_color": selected_color,
        },
        fallback_selected_color=selected_color,
    )

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
        best_timeline = None
        best_budget = None
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
                best_timeline = (fever_mask_head, count_body_fever, count_body_normal)
                best_budget = int(current_budget)

    if best_tuple:
        (score, ft, ff, g_pp, g_cm, g_fm, g_ov) = best_tuple
        if (not use_gpu) and best_timeline is not None:
            budget0 = int(best_budget) if best_budget is not None else int(g_pp + g_cm + g_fm + g_ov)
            cur_beat = base_beat + (ft * GEM_STAT_TO_ELEMENT_SCALE)
            cur_vibe = base_vibe + (ff * GEM_STAT_TO_ELEMENT_SCALE)
            cur_p_val = get_val_inline(p_color, cur_beat, cur_vibe)
            cur_s_val = get_val_inline(s_color, cur_beat, cur_vibe)
            (score, g_pp, g_cm, g_fm, g_ov) = _refine_gem_allocation_hint_fixed_ftff_cpu(
                budget=budget0,
                cur_pp=cur_pp,
                cur_cm=cur_cm,
                cur_fm=cur_fm,
                cur_p_val=cur_p_val,
                cur_s_val=cur_s_val,
                is_p_pp=is_p_pp,
                is_s_pp=is_s_pp,
                is_p_cm=is_p_cm,
                is_s_cm=is_s_cm,
                is_p_fm=is_p_fm,
                is_s_fm=is_s_fm,
                is_p_ov=is_p_ov,
                is_s_ov=is_s_ov,
                ref_pp=ref_pp,
                ref_cm=ref_cm,
                ref_fm=ref_fm,
                fever_mask_head=best_timeline[0],
                count_body_fever=int(best_timeline[1]),
                count_body_normal=int(best_timeline[2]),
                pp_gems=g_pp,
                cm_gems=g_cm,
                fm_gems=g_fm,
                ov_gems=g_ov,
            )
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

        gem_counts = build_gem_counts(g_pp, g_cm, g_fm, g_ov)
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
