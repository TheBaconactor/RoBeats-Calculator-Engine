"""
Fever Solver - Fever Timeline and Gem Combination Optimization.

This module provides the main gem solver pipeline:
- solve_best_fever_combination: Main gem solver - optimizes gem allocation for maximum score

    Coordinates between:
    - Compute Layer (score_math.py): Score calculation, gem optimization
    - GPU Layer (taichi_gem.api): GPU-accelerated batch optimization
"""

import numpy as np
import logging

from ...core.constants import (
    TOTAL_GEM_BUDGET,
    GEM_SCALE_FEVER,
)
from ...core.color_flags import build_color_flags
from ...core.config import GPUExecutionSettings
from ...core.gem_defs import UserGemsSettings, build_gem_counts

from ..base_stats import build_base_fixed_stats_dict, build_stats_array
from ..registry_solve_request import RegistrySolveRequest, dispatch_registry_solve

from .stats_ops import apply_gems_to_base_stats


logger = logging.getLogger(__name__)


def solve_best_fever_combination(
    cfg,
    initial_stats,
    calc_song,
    ref_arrays,
    silent=False,
    override_cfg=None,
):
    """
    Main gem solver - optimizes gem allocation for maximum score.

    GPU-only: dispatches the canonical registry solve which optimizes the full
    FT/FF/PP/CM/FM/Overflow gem allocation for maximum score.

    Args:
        cfg: Configuration object or None
        initial_stats: Initial stats dictionary
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        silent: Suppress console output if True
        override_cfg: Override config dictionary (for parallel evaluation)

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
    if not override_cfg and not use_gpu:
        print("[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); forcing GPU_Mode=true.")
        use_gpu = True
    if not use_gpu:
        raise RuntimeError(
            "solve_best_fever_combination is GPU-only; the nominal CPU reference path was removed"
        )

    # Normalize ref arrays to float32 so the GPU path uses consistent numeric behavior
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
        except Exception as e:
            logger.debug(f"fever_solver:solve_best_fever_combination: {e}")
            need_ref_cast = True
            break

    if need_ref_cast:
        ref_arrays = dict(ref_arrays)
        ref_arrays["Perfect Points"] = np.asarray(ref_pp_raw, dtype=np.float32)
        ref_arrays["Combo Multiplier"] = np.asarray(ref_cm_raw, dtype=np.float32)
        ref_arrays["Fever Multiplier"] = np.asarray(ref_fm_raw, dtype=np.float32)
        ref_arrays["Fever Time"] = np.asarray(ref_ft_raw, dtype=np.float32)
        ref_arrays["Fever Fill Rate"] = np.asarray(ref_ff_raw, dtype=np.float32)

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

    if not silent:
        print("Iterating permutations...")

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

    # GPU path: use the grid-based FT/FF solver, eliminating CPU timeline enumeration
    # and per-work-item fever mask transfers.
    # Compute color contribution flags for FT/FF gems (FT gems add Beat, FF gems add Vibe).
    is_p_ft = flags["is_p_ft"]
    is_s_ft = flags["is_s_ft"]
    is_p_ff = flags["is_p_ff"]
    is_s_ff = flags["is_s_ff"]

    try:
        song_slot = int((calc_song or {}).get("_gpu_song_slot", 0) or 0)
    except Exception as e:
        logger.debug(f"fever_solver:solve_best_fever_combination: {e}")
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
    best_tuple = (int(score), int(ft), int(ff), int(g_pp), int(g_cm), int(g_fm), int(g_ov))

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

        gem_counts = build_gem_counts(g_pp, g_cm, g_fm, g_ov)
        result = {
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
        return result

    return {}


def solve_best_fever_combination_batch(cfg, stats_list, calc_song, ref_arrays, override_cfg):
    """Batched GPU base gem re-solve: N loadouts in ONE skyline dispatch (n_genomes=N).

    The whole base solve (timeline reuse + skyline + scoring) then runs once for all loadouts, and
    the batch warmstart keeps each loadout's combo sweep independent. ``stats_list`` is N pre-gem
    stat rows (song fixed stats + tier delta + gear/mini item stats). Returns one result dict
    per input, in order: ``{Score, FT, FF, GemCounts, Stats, Selected Element, config}``. Each
    loadout's gem search is independent, so the per-loadout result is identical to the single-loadout
    ``solve_best_fever_combination`` GPU path -- served-batched == native-per-loadout (delta=0).
    GPU-only (override_cfg.use_gpu must be True; the on-demand re-solve always sets it)."""
    rows = [dict(s) for s in (stats_list or [])]
    if not rows:
        return []
    if not override_cfg:
        raise ValueError("solve_best_fever_combination_batch requires the parallel-eval override_cfg.")
    if not bool(override_cfg.get("use_gpu", False)):
        raise ValueError("solve_best_fever_combination_batch is GPU-only.")

    user_ft = int(override_cfg["user_ft"])
    user_ff = int(override_cfg["user_ff"])
    user_pp = int(override_cfg["user_pp"])
    user_cm = int(override_cfg["user_cm"])
    user_fm = int(override_cfg["user_fm"])
    selected_color = override_cfg["selected_color"]
    static_elem_input = int(override_cfg["static_elem_input"])

    # Match the single-loadout path's numeric behavior: ref arrays in float32.
    ref_arrays = dict(ref_arrays)
    for _k in ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate"):
        ref_arrays[_k] = np.asarray(ref_arrays[_k], dtype=np.float32)

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    flags = build_color_flags(p_color, s_color, selected_color)
    gem_settings = {
        "user_ft": user_ft,
        "user_ff": user_ff,
        "user_pp": user_pp,
        "user_cm": user_cm,
        "user_fm": user_fm,
        "static_elem_input": static_elem_input,
        "selected_color": selected_color,
    }

    n = len(rows)
    # Encode each loadout's pre-gem stats as ONE item in the skyline item pool. The
    # aggregator skips item_id == 0 (empty sentinel), so put loadout g at item g+1 and have
    # population_indices select only that item (slots 1-8 stay 0/empty). base_fixed_stats is 0, so
    # the aggregator yields exactly each loadout's pre-gem stats.
    item_stats = np.zeros((n + 1, 10), dtype=np.int32)
    population_indices = np.zeros((n, 9), dtype=np.int32)
    normalized: list[dict] = []
    for g, s in enumerate(rows):
        nb, _sel = build_base_fixed_stats_dict(s, gem_settings, fallback_selected_color=selected_color)
        normalized.append(nb)
        item_stats[g + 1, :] = np.asarray(build_stats_array(nb), dtype=np.int32)[:10]
        population_indices[g, 0] = g + 1

    try:
        song_slot = int((calc_song or {}).get("_gpu_song_slot", 0) or 0)
    except Exception as e:
        logger.debug(f"fever_solver:solve_best_fever_combination_batch: {e}")
        song_slot = 0

    request = RegistrySolveRequest(
        population_indices=population_indices,
        item_stats=item_stats,
        slot_start=np.zeros((9,), dtype=np.int32),
        slot_count=np.zeros((9,), dtype=np.int32),
        base_fixed_stats=np.zeros((10,), dtype=np.int32),
        timeline_grid=calc_song,
        ref_arrays=ref_arrays,
        flags={
            "is_p_ft": int(flags["is_p_ft"]),
            "is_s_ft": int(flags["is_s_ft"]),
            "is_p_ff": int(flags["is_p_ff"]),
            "is_s_ff": int(flags["is_s_ff"]),
            "is_p_pp": int(flags["is_p_pp"]),
            "is_s_pp": int(flags["is_s_pp"]),
            "is_p_cm": int(flags["is_p_cm"]),
            "is_s_cm": int(flags["is_s_cm"]),
            "is_p_fm": int(flags["is_p_fm"]),
            "is_s_fm": int(flags["is_s_fm"]),
            "is_p_ov": int(flags["is_p_ov"]),
            "is_s_ov": int(flags["is_s_ov"]),
        },
        total_budget=int(TOTAL_GEM_BUDGET),
        gem_scale_fever=int(GEM_SCALE_FEVER),
        song_slot=int(song_slot),
    )
    gpu_results = dispatch_registry_solve(request)
    if not gpu_results or len(gpu_results) != n:
        raise RuntimeError(
            f"batched base re-solve returned {len(gpu_results) if gpu_results else 0} results for {n} genomes"
        )

    out: list[dict] = []
    for g in range(n):
        score, ft, ff, g_pp, g_cm, g_fm, g_ov = gpu_results[g]
        final_stats = apply_gems_to_base_stats(
            normalized[g],
            selected_color,
            int(ft),
            int(ff),
            int(g_pp),
            int(g_cm),
            int(g_fm),
            int(g_ov),
            add_missing_element_key=False,
        )
        gem_counts = build_gem_counts(int(g_pp), int(g_cm), int(g_fm), int(g_ov))
        out.append(
            {
                "Score": int(score),
                "FT": int(ft),
                "FF": int(ff),
                "config": {
                    "FT Gems": int(ft),
                    "FF Gems": int(ff),
                    "PP Gems": int(g_pp),
                    "CM Gems": int(g_cm),
                    "FM Gems": int(g_fm),
                    "Overflow Gems": int(g_ov),
                },
                "FT_gems": int(ft),
                "FF_gems": int(ff),
                "gem_counts": gem_counts,
                "GemCounts": gem_counts,
                "Stats": final_stats,
                "Selected Element": selected_color,
            }
        )
    return out
