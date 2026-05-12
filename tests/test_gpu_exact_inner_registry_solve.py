import os
import sys

import numpy as np
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = pytest.mark.gpu


def _score_from_alloc(
    *,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    g_pp: int,
    g_cm: int,
    g_fm: int,
    g_ov: int,
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
) -> int:
    from gear_optimizer.core.constants import (
        ELEMENTAL_GEM_SCALE,
        GEM_SCALE_FEVER,
        GEM_SCALE_NORMAL,
        GEM_STAT_TO_ELEMENT_SCALE,
        TOTAL_ROWS,
    )
    from gear_optimizer.solver.scoring_core import fast_calculate_score, lookup_reference_py

    pp_stat = int(cur_pp) + int(g_pp) * int(GEM_SCALE_NORMAL)
    cm_stat = int(cur_cm) + int(g_cm) * int(GEM_SCALE_NORMAL)
    fm_stat = int(cur_fm) + int(g_fm) * int(GEM_SCALE_FEVER)
    p_val = (
        int(cur_p_val)
        + int(g_pp) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_p_pp)
        + int(g_cm) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_p_cm)
        + int(g_fm) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_p_fm)
        + int(g_ov) * int(ELEMENTAL_GEM_SCALE) * int(is_p_ov)
    )
    s_val = (
        int(cur_s_val)
        + int(g_pp) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_s_pp)
        + int(g_cm) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_s_cm)
        + int(g_fm) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_s_fm)
        + int(g_ov) * int(ELEMENTAL_GEM_SCALE) * int(is_s_ov)
    )
    base = np.float32((p_val * 2) + s_val) + np.float32(lookup_reference_py(pp_stat, ref_pp, TOTAL_ROWS))
    c_mul = np.float32(lookup_reference_py(cm_stat, ref_cm, TOTAL_ROWS))
    f_mul = np.float32(lookup_reference_py(fm_stat, ref_fm, TOTAL_ROWS))
    return int(
        fast_calculate_score(
            base,
            c_mul,
            f_mul,
            fever_mask_head,
            int(count_body_fever),
            int(count_body_normal),
        )
    )


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_registry_solve_inner_selector_matches_cpu_exact_for_both_branches():
    from gear_optimizer.core.color_flags import build_color_flags
    from gear_optimizer.core.constants import (
        ELEMENTAL_GEM_SCALE,
        GEM_SCALE_FEVER,
        GEM_SCALE_NORMAL,
        GEM_STAT_TO_ELEMENT_SCALE,
        MAX_STAT_INDEX,
        TOTAL_GEM_BUDGET,
        TOTAL_ROWS,
    )
    from gear_optimizer.solver.base_stats import build_stats_array
    from gear_optimizer.solver.registry_solve_request import RegistrySolveRequest, dispatch_registry_solve
    from gear_optimizer.solver.scoring.fever_solver import precompute_fever_timelines
    from gear_optimizer.solver.scoring_core import optimize_core_exact_bounded_jit

    timestamps = np.linspace(0.0, 120.0, 120, dtype=np.float32)
    calc_song = {
        "metadata": {
            "Song Name": "Exact Inner GPU Test",
            "Difficulty": "Hard",
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
            "Total Notes": int(timestamps.shape[0]),
        },
        "song_data": {"timestamps": timestamps},
    }

    rows = TOTAL_ROWS + 1
    ref_arrays = {
        "Perfect Points": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float32),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows, dtype=np.float32),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows, dtype=np.float32),
        "Fever Time": np.linspace(1.0, 2.5, rows, dtype=np.float32),
    }
    base_stats = {
        "Perfect Points": 100,
        "Combo Multiplier": 95,
        "Fever Multiplier": 90,
        "Fever Time": 80,
        "Fever Fill Rate": 85,
        "Rush": 140,
        "Flow": 120,
        "Beat": 60,
        "Vibe": 60,
        "Chill": 60,
    }
    flags = build_color_flags("Rush", "Flow", "Rush")

    cur_pp = int(base_stats["Perfect Points"])
    cur_cm = int(base_stats["Combo Multiplier"])
    cur_fm = int(base_stats["Fever Multiplier"])
    base_beat = int(base_stats["Beat"])
    base_vibe = int(base_stats["Vibe"])
    base_rush = int(base_stats["Rush"])
    base_flow = int(base_stats["Flow"])

    cpu_best = None
    timelines = precompute_fever_timelines(
        base_stats,
        calc_song,
        ref_arrays,
        int(TOTAL_GEM_BUDGET),
        int(TOTAL_GEM_BUDGET),
        int(TOTAL_GEM_BUDGET),
    )
    for t_data in timelines:
        ft = int(t_data["ft_gems"])
        ff = int(t_data["ff_gems"])
        current_budget = int(t_data["remaining_budget"])
        fever_mask_head = np.asarray(t_data["timeline"][0], dtype=np.bool_)
        count_body_fever = int(t_data["timeline"][1])
        count_body_normal = int(t_data["timeline"][2])

        cur_beat = base_beat + (ft * int(GEM_STAT_TO_ELEMENT_SCALE))
        cur_vibe = base_vibe + (ff * int(GEM_STAT_TO_ELEMENT_SCALE))
        cur_p_val = cur_beat if calc_song["metadata"]["Primary Color"] == "Beat" else (
            cur_vibe if calc_song["metadata"]["Primary Color"] == "Vibe" else base_rush
        )
        cur_s_val = cur_beat if calc_song["metadata"]["Secondary Color"] == "Beat" else (
            cur_vibe if calc_song["metadata"]["Secondary Color"] == "Vibe" else base_flow
        )

        exact = optimize_core_exact_bounded_jit(
            current_budget,
            cur_pp,
            cur_cm,
            cur_fm,
            int(cur_p_val),
            int(cur_s_val),
            int(flags["is_p_pp"]),
            int(flags["is_s_pp"]),
            int(flags["is_p_cm"]),
            int(flags["is_s_cm"]),
            int(flags["is_p_fm"]),
            int(flags["is_s_fm"]),
            int(flags["is_p_ov"]),
            int(flags["is_s_ov"]),
            np.asarray(ref_arrays["Perfect Points"], dtype=np.float32),
            np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32),
            np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32),
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
        score = _score_from_alloc(
            cur_pp=cur_pp,
            cur_cm=cur_cm,
            cur_fm=cur_fm,
            cur_p_val=int(cur_p_val),
            cur_s_val=int(cur_s_val),
            g_pp=int(exact[5]),
            g_cm=int(exact[6]),
            g_fm=int(exact[7]),
            g_ov=int(exact[8]),
            is_p_pp=int(flags["is_p_pp"]),
            is_s_pp=int(flags["is_s_pp"]),
            is_p_cm=int(flags["is_p_cm"]),
            is_s_cm=int(flags["is_s_cm"]),
            is_p_fm=int(flags["is_p_fm"]),
            is_s_fm=int(flags["is_s_fm"]),
            is_p_ov=int(flags["is_p_ov"]),
            is_s_ov=int(flags["is_s_ov"]),
            ref_pp=np.asarray(ref_arrays["Perfect Points"], dtype=np.float32),
            ref_cm=np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32),
            ref_fm=np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32),
            fever_mask_head=fever_mask_head,
            count_body_fever=count_body_fever,
            count_body_normal=count_body_normal,
        )
        result = (score, ft, ff, int(exact[5]), int(exact[6]), int(exact[7]), int(exact[8]))
        if cpu_best is None or int(result[0]) > int(cpu_best[0]):
            cpu_best = result

    assert cpu_best is not None

    item_stats = np.zeros((10, 10), dtype=np.int32)
    slot_start = np.arange(1, 10, dtype=np.int32)
    slot_count = np.ones(9, dtype=np.int32)
    population_indices = np.asarray([[1, 2, 3, 4, 5, 6, 7, 8, 9]], dtype=np.int32)
    gpu_bests = []
    for use_exact_inner_solver, score_cull_threshold in (
        (True, None),
        (False, None),
        (True, int(cpu_best[0])),
    ):
        req = RegistrySolveRequest(
            population_indices=population_indices,
            item_stats=item_stats,
            slot_start=slot_start,
            slot_count=slot_count,
            base_fixed_stats=build_stats_array(base_stats),
            timeline_grid=calc_song,
            ref_arrays=ref_arrays,
            flags={k: int(v) for k, v in flags.items()},
            total_budget=int(TOTAL_GEM_BUDGET),
            gem_scale_fever=int(GEM_SCALE_FEVER),
            song_slot=0,
            use_exact_inner_solver=use_exact_inner_solver,
            score_cull_threshold=score_cull_threshold,
        )
        gpu_results = dispatch_registry_solve(req)
        assert len(gpu_results) == 1
        gpu_best = tuple(int(v) for v in gpu_results[0])
        assert gpu_best[0] == int(cpu_best[0])
        gpu_bests.append(gpu_best)

    assert gpu_bests[0] == gpu_bests[1]
