from __future__ import annotations

from pathlib import Path

import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_ROWS,
)
from gear_optimizer.solver.scoring_core import (
    fast_calculate_score,
    lookup_reference_py,
    optimize_core_exact_bounded_jit,
    optimize_core_jit,
    semi_exact_upper_bound_jit,
)


def _score_allocation(
    *,
    result: tuple,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    flags: tuple[int, int, int, int, int, int, int, int],
    ref_pp: np.ndarray,
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    g_pp = int(result[5])
    g_cm = int(result[6])
    g_fm = int(result[7])
    g_ov = int(result[8])
    pp_stat = int(cur_pp) + g_pp * int(GEM_SCALE_NORMAL)
    cm_stat = int(cur_cm) + g_cm * int(GEM_SCALE_NORMAL)
    fm_stat = int(cur_fm) + g_fm * int(GEM_SCALE_FEVER)
    p_val = (
        int(cur_p_val)
        + g_pp * int(GEM_STAT_TO_ELEMENT_SCALE) * int(flags[0])
        + g_cm * int(GEM_STAT_TO_ELEMENT_SCALE) * int(flags[2])
        + g_fm * int(GEM_STAT_TO_ELEMENT_SCALE) * int(flags[4])
        + g_ov * int(ELEMENTAL_GEM_SCALE) * int(flags[6])
    )
    s_val = (
        int(cur_s_val)
        + g_pp * int(GEM_STAT_TO_ELEMENT_SCALE) * int(flags[1])
        + g_cm * int(GEM_STAT_TO_ELEMENT_SCALE) * int(flags[3])
        + g_fm * int(GEM_STAT_TO_ELEMENT_SCALE) * int(flags[5])
        + g_ov * int(ELEMENTAL_GEM_SCALE) * int(flags[7])
    )
    base_value = np.float32((p_val * 2) + s_val) + np.float32(lookup_reference_py(pp_stat, ref_pp, TOTAL_ROWS))
    return int(
        fast_calculate_score(
            base_value,
            np.float32(lookup_reference_py(cm_stat, ref_cm, TOTAL_ROWS)),
            np.float32(lookup_reference_py(fm_stat, ref_fm, TOTAL_ROWS)),
            fever_mask_head,
            int(count_body_fever),
            int(count_body_normal),
        )
    )


def test_base1_same_surface_inner_dominance_has_executable_exact_solver_gate() -> None:
    ref_pp = np.linspace(1.0, 2.2, TOTAL_ROWS + 1, dtype=np.float32)
    ref_cm = np.linspace(1.0, 3.1, TOTAL_ROWS + 1, dtype=np.float32)
    ref_fm = np.linspace(1.0, 4.6, TOTAL_ROWS + 1, dtype=np.float32)
    fever_mask_head = np.asarray([0, 1, 1, 0, 1, 0, 0, 1] * 4, dtype=np.bool_)
    flags = (1, 0, 0, 1, 1, 0, 1, 0)
    budget = 12

    dominated = (54, 68, 73, 80, 31)
    dominating = (56, 68, 76, 83, 31)

    dominated_result = optimize_core_exact_bounded_jit(
        budget,
        *dominated,
        *flags,
        ref_pp,
        ref_cm,
        ref_fm,
        fever_mask_head,
        17,
        29,
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS,
        MAX_STAT_INDEX,
    )
    dominating_result = optimize_core_exact_bounded_jit(
        budget,
        *dominating,
        *flags,
        ref_pp,
        ref_cm,
        ref_fm,
        fever_mask_head,
        17,
        29,
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS,
        MAX_STAT_INDEX,
    )

    dominated_score = _score_allocation(
        result=dominated_result,
        cur_pp=dominated[0],
        cur_cm=dominated[1],
        cur_fm=dominated[2],
        cur_p_val=dominated[3],
        cur_s_val=dominated[4],
        flags=flags,
        ref_pp=ref_pp,
        ref_cm=ref_cm,
        ref_fm=ref_fm,
        fever_mask_head=fever_mask_head,
        count_body_fever=17,
        count_body_normal=29,
    )
    dominating_score = _score_allocation(
        result=dominating_result,
        cur_pp=dominating[0],
        cur_cm=dominating[1],
        cur_fm=dominating[2],
        cur_p_val=dominating[3],
        cur_s_val=dominating[4],
        flags=flags,
        ref_pp=ref_pp,
        ref_cm=ref_cm,
        ref_fm=ref_fm,
        fever_mask_head=fever_mask_head,
        count_body_fever=17,
        count_body_normal=29,
    )

    assert dominating_score >= dominated_score


def test_moonshot4_greedy_exact_inner_replacement_has_counterexample() -> None:
    ref_pp = np.linspace(1.0, 2.3, TOTAL_ROWS + 1, dtype=np.float32)
    ref_cm = np.linspace(1.0, 3.5, TOTAL_ROWS + 1, dtype=np.float32)
    ref_fm = np.linspace(1.0, 4.9, TOTAL_ROWS + 1, dtype=np.float32)
    fever_mask_head = np.asarray(
        [
            1,
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            1,
            0,
            0,
            1,
            1,
            0,
            1,
            1,
            0,
            1,
            1,
            1,
            0,
            1,
            1,
            0,
            0,
            1,
            1,
            0,
            0,
            0,
            1,
            0,
            1,
            1,
            0,
            1,
            0,
            0,
            0,
            1,
            1,
            0,
            0,
            1,
            0,
            1,
            1,
            0,
            0,
            0,
            0,
            1,
            1,
            1,
            1,
            0,
            1,
            1,
            0,
            0,
            0,
            1,
            0,
            1,
            0,
            0,
        ],
        dtype=np.bool_,
    )
    flags = (1, 1, 0, 0, 1, 0, 0, 0)
    cur = (95, 102, 58, 57, 53)
    common_args = (
        14,
        *cur,
        *flags,
        ref_pp,
        ref_cm,
        ref_fm,
        fever_mask_head,
        40,
        125,
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS,
        MAX_STAT_INDEX,
    )

    greedy = optimize_core_jit(*common_args)
    exact = optimize_core_exact_bounded_jit(*common_args)
    greedy_score = _score_allocation(
        result=greedy,
        cur_pp=cur[0],
        cur_cm=cur[1],
        cur_fm=cur[2],
        cur_p_val=cur[3],
        cur_s_val=cur[4],
        flags=flags,
        ref_pp=ref_pp,
        ref_cm=ref_cm,
        ref_fm=ref_fm,
        fever_mask_head=fever_mask_head,
        count_body_fever=40,
        count_body_normal=125,
    )
    exact_score = _score_allocation(
        result=exact,
        cur_pp=cur[0],
        cur_cm=cur[1],
        cur_fm=cur[2],
        cur_p_val=cur[3],
        cur_s_val=cur[4],
        flags=flags,
        ref_pp=ref_pp,
        ref_cm=ref_cm,
        ref_fm=ref_fm,
        fever_mask_head=fever_mask_head,
        count_body_fever=40,
        count_body_normal=125,
    )

    assert tuple(int(x) for x in greedy[5:9]) == (3, 0, 11, 0)
    assert tuple(int(x) for x in exact[5:9]) == (0, 0, 14, 0)
    assert exact_score > greedy_score


def test_base8_upper_bound_is_admissible_but_not_an_exact_score() -> None:
    fever_mask_head = np.asarray([0, 1, 0, 1, 1, 0, 0, 1] * 5, dtype=np.bool_)
    ref_cm = np.linspace(1.0, 2.9, TOTAL_ROWS + 1, dtype=np.float32)
    ref_fm = np.linspace(1.0, 4.8, TOTAL_ROWS + 1, dtype=np.float32)
    base_value = np.float32(812.5)
    combo_mul = np.float32(ref_cm[73])
    fever_mul = np.float32(ref_fm[64])
    n_hn = int((~fever_mask_head).sum())
    n_hf = int(fever_mask_head.sum())
    sigma_hn = int(sum(i + 1 for i, v in enumerate(fever_mask_head) if not v))
    sigma_hf = int(sum(i + 1 for i, v in enumerate(fever_mask_head) if v))

    exact = int(fast_calculate_score(base_value, combo_mul, fever_mul, fever_mask_head, 31, 47))
    upper = float(
        semi_exact_upper_bound_jit(
            base_value,
            combo_mul,
            fever_mul,
            31,
            47,
            n_hn,
            n_hf,
            sigma_hn,
            sigma_hf,
        )
    )

    assert upper >= exact
    assert upper > exact


def test_activation_count_skip_theorems_have_one_activation_shift_counterexample() -> None:
    note_values = [10, 50, 250, 260]
    fever_multiplier = 2
    baseline_mask = [False, True, True, False]
    shifted_mask = [False, False, True, True]
    forced_penalty = 15

    baseline = sum(v * fever_multiplier if f else v for v, f in zip(note_values, baseline_mask, strict=True))
    shifted = sum(v * fever_multiplier if f else v for v, f in zip(note_values, shifted_mask, strict=True))

    assert shifted - forced_penalty > baseline


def test_raw_stat_skyline_without_timing_context_has_counterexample() -> None:
    mask_no_fever = np.zeros((8,), dtype=np.bool_)
    mask_all_fever = np.ones((8,), dtype=np.bool_)

    higher_raw_lower_timing = int(
        fast_calculate_score(np.float32(120.0), np.float32(1.0), np.float32(3.0), mask_no_fever, 0, 20)
    )
    lower_raw_better_timing = int(
        fast_calculate_score(np.float32(100.0), np.float32(1.0), np.float32(3.0), mask_all_fever, 20, 0)
    )

    assert lower_raw_better_timing > higher_raw_lower_timing


def test_theorem_checklist_rows_all_have_closed_gates() -> None:
    checklist = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "Implementation Records"
        / "theorem-reduction"
        / "THEOREM_IMPLEMENTATION_CHECKLIST.md"
    )
    text = checklist.read_text(encoding="utf-8")
    allowed = {
        "`IMPLEMENTED_EXISTING`",
        "`IMPLEMENTED_NOW`",
        "`BLOCKED_FALSE`",
        "`BLOCKED_CONDITIONAL`",
        "`DOC_ONLY`",
    }
    rows = [line for line in text.splitlines() if line.startswith("| ") and not line.startswith("| Theorem")]
    theorem_rows = []
    for line in rows:
        if line.startswith("|---"):
            continue
        if any(status in line for status in allowed):
            theorem_rows.append(line)

    assert len(theorem_rows) >= 34
    for row in theorem_rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert len(cells) == 4
        assert cells[1] in allowed or any(status in cells[1] for status in allowed)
        assert cells[2] and cells[2] != "-"
        assert cells[3] and cells[3] != "-"
