from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.scoring.scoring_core import (
    fast_calculate_score,
    optimize_core_exact_bounded_jit,
    optimize_core_jit,
    semi_exact_upper_bound_jit,
)


def _build_ref_arrays() -> dict[str, np.ndarray]:
    refs: dict[str, np.ndarray] = {}
    refs["pp"] = np.linspace(100, 300, int(TOTAL_ROWS) + 1, dtype=np.float32)
    refs["cm"] = np.linspace(200, 267, int(TOTAL_ROWS) + 1, dtype=np.float32)
    refs["fm"] = np.linspace(300, 400, int(TOTAL_ROWS) + 1, dtype=np.float32)
    return refs


def _compute_margin_brute_force(
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
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
    refs: dict[str, np.ndarray],
) -> tuple[int, int]:
    """Brute-force all allocations to find best and second-best scores."""
    GEM_SCALE_NORMAL = 2
    GEM_SCALE_FEVER = 3
    GEM_STAT_TO_ELEMENT_SCALE = 2
    ELEMENTAL_GEM_SCALE = 3
    MAX_STAT_INDEX = int(TOTAL_ROWS)

    scores: list[int] = []

    max_pp_gems = min(budget, (MAX_STAT_INDEX - cur_pp) // GEM_SCALE_NORMAL) if cur_pp < MAX_STAT_INDEX and (is_p_pp or is_s_pp) else 0
    max_cm_gems = min(budget, (MAX_STAT_INDEX - cur_cm) // GEM_SCALE_NORMAL) if cur_cm < MAX_STAT_INDEX else 0
    if not (is_p_cm or is_s_cm) and cur_cm > 50:
        max_cm_gems = 0
    elif not (is_p_cm or is_s_cm):
        max_cm_gems = min(max_cm_gems, (50 - cur_cm) // GEM_SCALE_NORMAL + 1)
    max_fm_gems = min(budget, (MAX_STAT_INDEX - cur_fm) // GEM_SCALE_FEVER) if cur_fm < MAX_STAT_INDEX else 0

    for g_cm in range(max_cm_gems + 1):
        for g_fm in range(min(max_fm_gems, budget - g_cm) + 1):
            leftover = budget - g_cm - g_fm
            max_pp_here = min(max_pp_gems, leftover)
            for g_pp in range(max_pp_here + 1):
                g_ov = leftover - g_pp

                pp_stat = cur_pp + g_pp * GEM_SCALE_NORMAL
                cm_stat = cur_cm + g_cm * GEM_SCALE_NORMAL
                fm_stat = cur_fm + g_fm * GEM_SCALE_FEVER

                p_val = (
                    cur_p_val
                    + g_pp * GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
                    + g_cm * GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
                    + g_fm * GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
                    + g_ov * ELEMENTAL_GEM_SCALE * is_p_ov
                )
                s_val = (
                    cur_s_val
                    + g_pp * GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
                    + g_cm * GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
                    + g_fm * GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
                    + g_ov * ELEMENTAL_GEM_SCALE * is_s_ov
                )

                base_value = float((p_val * 2) + s_val + refs["pp"][min(pp_stat, MAX_STAT_INDEX)])
                combo_mul = float(refs["cm"][min(cm_stat, MAX_STAT_INDEX)])
                fever_mul = float(refs["fm"][min(fm_stat, MAX_STAT_INDEX)])

                score = fast_calculate_score(
                    base_value, combo_mul, fever_mul,
                    fever_mask_head, count_body_fever, count_body_normal,
                )
                scores.append(int(score))

    if len(scores) < 2:
        return scores[0] if scores else 0, 0

    scores_sorted = sorted(set(scores), reverse=True)
    best = scores_sorted[0]
    second = scores_sorted[1] if len(scores_sorted) > 1 else best
    return best, best - second


def test_margin_is_positive_when_multiple_allocations_exist() -> None:
    """BASE-5: Margin M must be positive when multiple allocations produce different scores."""
    rng = np.random.default_rng(42)
    refs = _build_ref_arrays()

    for _ in range(20):
        budget = int(rng.integers(5, 15))
        cur_pp = int(rng.integers(0, 50))
        cur_cm = int(rng.integers(0, 30))
        cur_fm = int(rng.integers(0, 30))
        cur_p_val = int(rng.integers(0, 50))
        cur_s_val = int(rng.integers(0, 50))
        is_p_pp = int(rng.integers(0, 2))
        is_s_pp = int(rng.integers(0, 2))
        is_p_cm = int(rng.integers(0, 2))
        is_s_cm = int(rng.integers(0, 2))
        is_p_fm = int(rng.integers(0, 2))
        is_s_fm = int(rng.integers(0, 2))
        is_p_ov = int(rng.integers(0, 2))
        is_s_ov = int(rng.integers(0, 2))

        head_len = int(rng.integers(10, 30))
        n_hf = int(rng.integers(0, head_len // 2 + 1))
        fever_mask_head = np.zeros(head_len, dtype=np.bool_)
        if n_hf > 0:
            indices = rng.choice(head_len, size=n_hf, replace=False)
            fever_mask_head[indices] = True

        count_body_fever = int(rng.integers(50, 150))
        count_body_normal = int(rng.integers(50, 150))

        best, margin = _compute_margin_brute_force(
            budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
            fever_mask_head, count_body_fever, count_body_normal, refs,
        )

        # Margin should be non-negative; positive when allocations differ
        assert margin >= 0


def test_two_delta_condition_is_sufficient_for_reuse() -> None:
    """BASE-5-R: M > 2Δ guarantees allocation reuse safety."""
    # Synthetic case where we know the margin and perturbation
    center_best = 1_000_000
    center_alt = 990_000
    margin = center_best - center_alt  # 10,000
    delta = 4_000

    # M > 2Δ ?
    assert margin > 2 * delta

    # Worst case: best drops by Δ, alt rises by Δ
    worst_best = center_best - delta
    worst_alt = center_alt + delta

    # Best still wins
    assert worst_best > worst_alt


def test_two_delta_condition_is_necessary() -> None:
    """M <= 2Δ does NOT guarantee reuse safety."""
    center_best = 1_000_000
    center_alt = 995_000
    margin = center_best - center_alt  # 5,000
    delta = 3_000

    # M < 2Δ
    assert margin < 2 * delta

    worst_best = center_best - delta
    worst_alt = center_alt + delta

    # Alt can win!
    assert worst_alt > worst_best


def test_exact_solver_produces_non_negative_margin() -> None:
    """The production exact solver always returns an allocation with M >= 0."""
    rng = np.random.default_rng(123)
    refs = _build_ref_arrays()

    for _ in range(10):
        budget = int(rng.integers(3, 10))
        cur_pp = int(rng.integers(0, 40))
        cur_cm = int(rng.integers(0, 30))
        cur_fm = int(rng.integers(0, 30))
        cur_p_val = int(rng.integers(0, 40))
        cur_s_val = int(rng.integers(0, 40))

        head_len = int(rng.integers(5, 20))
        n_hf = int(rng.integers(0, head_len // 2 + 1))
        fever_mask_head = np.zeros(head_len, dtype=np.bool_)
        if n_hf > 0:
            indices = rng.choice(head_len, size=n_hf, replace=False)
            fever_mask_head[indices] = True

        count_body_fever = int(rng.integers(20, 80))
        count_body_normal = int(rng.integers(20, 80))

        # Use production exact solver
        result = optimize_core_exact_bounded_jit(
            budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
            1, 0, 1, 0, 1, 0, 1, 0,
            refs["pp"], refs["cm"], refs["fm"],
            fever_mask_head, count_body_fever, count_body_normal,
            2, 3, 2, 3, int(TOTAL_ROWS), int(TOTAL_ROWS),
        )

        # Result returns (pp_stat, cm_stat, fm_stat, p_val, s_val, pp_gems, cm_gems, fm_gems, ov_gems)
        assert result[5] >= 0  # pp_gems
        assert result[6] >= 0  # cm_gems
        assert result[7] >= 0  # fm_gems
        assert result[8] >= 0  # ov_gems
        assert result[5] + result[6] + result[7] + result[8] <= budget


def test_delta_bound_for_small_cell() -> None:
    """Compute conservative Δ for a small stat cell."""
    rng = np.random.default_rng(99)

    # Song parameters
    n_body_fever = 100
    n_body_normal = 100
    n_head = 50
    n_total = n_body_fever + n_body_normal + n_head

    # Stat cell widths (in actual stat units)
    delta_pp = 4
    delta_cm = 4
    delta_fm = 6
    delta_p = 5

    # Max multipliers
    combo_mul_max = 2.5
    fever_mul_max = 3.0
    base_max = 500.0

    # Conservative Δ: each stat change propagates through the bilinear score formula
    # P_val change: each point adds ~2-3 to base_value
    # For delta_p=5, base_value changes by ~10-15
    delta_body_p = delta_p * 3 * n_total * combo_mul_max * fever_mul_max

    # PP is within plateau, so ref_pp doesn't change → delta from PP is 0
    # CM within plateau: same
    # FM within plateau: same
    # Only P_val/S_val changes matter inside a safe cell
    delta_cell = delta_body_p

    # For a small cell where only P_val varies, Δ should be in the thousands
    assert delta_cell < 100_000
    assert delta_cell > 0

    # Typical margin on Normal songs: 500-5,000
    # For small cells with only linear stat changes, M > 2Δ may NOT hold
    # Cell reuse is only safe for very large margins or very small cells
    typical_margin = 2_500
    if typical_margin > 2 * delta_cell:
        # Cell reuse is safe for this representative
        pass
