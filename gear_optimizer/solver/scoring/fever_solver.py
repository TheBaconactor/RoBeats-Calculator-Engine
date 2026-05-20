"""
Fever Solver - Fever Timeline and Gem Combination Optimization.
This module provides the main gem solver pipeline:
- solve_best_fever_combination: Main gem solver - optimizes gem allocation for maximum score
    Coordinates between:
    - Rules Layer (fever_timeline.py): Timeline calculation, SongTimelineGrid
    - Compute Layer (scoring_core.py): Score calculation, gem optimization
    - GPU Layer (taichi_gem.api): GPU-accelerated batch optimization
"""
import numpy as np
import logging
from ...core.constants import (
    TOTAL_GEM_BUDGET,
    GEM_SCALE_FEVER,
)
from ...core.color_flags import build_color_flag_values
from ...core.gem_defs import UserGemsSettings, build_gem_counts
from ..base_stats import build_base_fixed_stats_dict, build_stats_array
from ..registry_solve_request import RegistrySolveRequest, dispatch_registry_solve
from .stats_scoring import evaluate_stats_score
from .stats_ops import apply_gems_to_base_stats

logger = logging.getLogger(__name__)


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
    Main gem solver - dispatches the GPU registry solve for the configured base stats.
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
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    base_stats = initial_stats.copy()
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
    if skip_optimizer:
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
    if not silent:
        print("Iterating permutations...")
    color_flags = build_color_flag_values(p_color, s_color, selected_color)
    try:
        song_slot = int((calc_song or {}).get("_gpu_song_slot", 0) or 0)
    except Exception as e:
        logger.debug(f"fever_solver:solve_best_fever_combination:song_slot: {e}")
        song_slot = 0
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
        flags=color_flags.as_dict(),
        total_budget=int(TOTAL_GEM_BUDGET),
        gem_scale_fever=int(GEM_SCALE_FEVER),
        song_slot=int(song_slot),
    )
    gpu_results = dispatch_registry_solve(request)
    if not gpu_results:
        raise RuntimeError("GPU solver returned no results.")
    score, ft, ff, g_pp, g_cm, g_fm, g_ov = gpu_results[0]
    final_stats = apply_gems_to_base_stats(
        base_stats,
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
    return {
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
