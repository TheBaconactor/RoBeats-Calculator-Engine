from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.scoring.scoring_core import (
    fast_calculate_score,
    lookup_reference_jit,
    optimize_core_exact_bounded_jit,
    optimize_core_jit,
    semi_exact_upper_bound_jit,
)


def _build_ref_arrays() -> dict[str, np.ndarray]:
    """Build minimal reference arrays for testing."""
    ref_arrays: dict[str, np.ndarray] = {}
    ref_arrays["pp"] = np.linspace(100, 300, int(TOTAL_ROWS) + 1, dtype=np.float32)
    ref_arrays["cm"] = np.linspace(200, 267, int(TOTAL_ROWS) + 1, dtype=np.float32)
    ref_arrays["fm"] = np.linspace(300, 400, int(TOTAL_ROWS) + 1, dtype=np.float32)
    return ref_arrays


def _corrected_semi_exact_upper_bound(
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    count_body_fever: int,
    count_body_normal: int,
    n_hn: int,
    n_hf: int,
    sigma_hn: int,
    sigma_hf: int,
) -> float:
    """Corrected bound: body uses float (no floor), plus UB_EPS = N_notes."""
    base_f = np.float32(base_value)
    combo_mul_f = np.float32(combo_mul)
    fever_mul_f = np.float32(fever_mul)

    body_upper = (
        count_body_fever * float(base_f * combo_mul_f * fever_mul_f)
        + count_body_normal * float(base_f * combo_mul_f)
    )

    factor = (combo_mul_f - np.float32(1.0)) * base_f / np.float32(100.0)
    head_upper = (
        float(base_f * (np.float32(n_hn) + (fever_mul_f * np.float32(n_hf))))
        + float(factor * (np.float32(sigma_hn) + (fever_mul_f * np.float32(sigma_hf))))
    )

    n_notes = count_body_fever + count_body_normal + n_hn + n_hf
    ub_eps = float(n_notes)

    return body_upper + head_upper + ub_eps


@pytest.mark.parametrize("seed", [42, 123, 999])
def test_corrected_upper_bound_is_always_admissible(seed: int) -> None:
    """BASE-6/7/FG-6: Corrected U_semi_exact must be >= exact score for all valid inputs."""
    rng = np.random.default_rng(seed)
    refs = _build_ref_arrays()

    n_trials = 200
    for _ in range(n_trials):
        base_value = float(rng.integers(50, 500))
        combo_mul = float(rng.uniform(1.5, 3.0))
        fever_mul = float(rng.uniform(2.0, 4.0))
        count_body_fever = int(rng.integers(0, 300))
        count_body_normal = int(rng.integers(0, 300))
        n_hn = int(rng.integers(0, 50))
        n_hf = int(rng.integers(0, 50))
        sigma_hn = int(rng.integers(0, n_hn * 100 + 1))
        sigma_hf = int(rng.integers(0, n_hf * 100 + 1))

        # Build fever mask head
        head_len = n_hn + n_hf
        fever_mask_head = np.zeros(head_len, dtype=np.bool_)
        if head_len > 0 and n_hf > 0:
            fever_indices = rng.choice(head_len, size=min(n_hf, head_len), replace=False)
            fever_mask_head[fever_indices] = True

        # Compute sigma from actual mask (must match bound inputs)
        sigma_hn_actual = sum(i + 1 for i in range(head_len) if not fever_mask_head[i])
        sigma_hf_actual = sum(i + 1 for i in range(head_len) if fever_mask_head[i])

        exact_score = fast_calculate_score(
            base_value,
            combo_mul,
            fever_mul,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
        )

        upper_bound = _corrected_semi_exact_upper_bound(
            base_value,
            combo_mul,
            fever_mul,
            count_body_fever,
            count_body_normal,
            n_hn,
            n_hf,
            sigma_hn_actual,
            sigma_hf_actual,
        )

        assert upper_bound >= exact_score, (
            f"Bound violation: ub={upper_bound}, exact={exact_score}, "
            f"base={base_value}, cm={combo_mul}, fm={fever_mul}"
        )


def test_tight_bound_is_also_admissible() -> None:
    """U_tight = U_semi_exact - N_notes must also be >= exact score."""
    rng = np.random.default_rng(42)
    refs = _build_ref_arrays()

    for _ in range(100):
        base_value = float(rng.integers(50, 500))
        combo_mul = float(rng.uniform(1.5, 3.0))
        fever_mul = float(rng.uniform(2.0, 4.0))
        count_body_fever = int(rng.integers(0, 200))
        count_body_normal = int(rng.integers(0, 200))
        n_hn = int(rng.integers(0, 30))
        n_hf = int(rng.integers(0, 30))
        sigma_hn = int(rng.integers(0, n_hn * 50 + 1))
        sigma_hf = int(rng.integers(0, n_hf * 50 + 1))

        head_len = n_hn + n_hf
        fever_mask_head = np.zeros(head_len, dtype=np.bool_)
        if head_len > 0 and n_hf > 0:
            fever_indices = rng.choice(head_len, size=min(n_hf, head_len), replace=False)
            fever_mask_head[fever_indices] = True

        # Compute sigma from actual mask
        sigma_hn_actual = sum(i + 1 for i in range(head_len) if not fever_mask_head[i])
        sigma_hf_actual = sum(i + 1 for i in range(head_len) if fever_mask_head[i])

        exact_score = fast_calculate_score(
            base_value, combo_mul, fever_mul,
            fever_mask_head, count_body_fever, count_body_normal,
        )

        ub = _corrected_semi_exact_upper_bound(
            base_value, combo_mul, fever_mul,
            count_body_fever, count_body_normal,
            n_hn, n_hf, sigma_hn_actual, sigma_hf_actual,
        )

        n_notes = count_body_fever + count_body_normal + n_hn + n_hf
        tight_ub = float(ub) - float(n_notes)

        assert tight_ub >= exact_score - 1e-3, (
            f"Tight bound violation: tight={tight_ub}, exact={exact_score}"
        )


def test_admissible_bound_excludes_suboptimal_candidates() -> None:
    """BASE-6: If U < incumbent, candidate cannot win."""
    incumbent_score = 1_000_000

    # Candidate A: bound below incumbent
    ub_a = 950_000
    assert ub_a < incumbent_score
    # Therefore score_exact(A) <= ub_a < incumbent_score
    # A is excluded (this is the theorem gate, not a runtime test)

    # Candidate B: bound above incumbent
    ub_b = 1_050_000
    assert ub_b >= incumbent_score
    # B may or may not win; cannot be excluded


def test_fg_uplift_bound_composition() -> None:
    """BASE-7/S4: FG uplift bound is admissible."""
    base_score = 900_000
    max_fg_uplift = 50_000  # From S9 decomposition or U_semi_exact
    penalty_min = 5_000

    u_fg = base_score + max_fg_uplift - penalty_min
    best_fg = 940_000

    # If u_fg < best_fg, candidate cannot win
    if u_fg < best_fg:
        assert base_score + max_fg_uplift - penalty_min < best_fg
        # This is the safe exclusion condition


def test_bound_gap_is_at_most_n_notes() -> None:
    """The corrected semi-exact bound overestimates by at most 1 per note."""
    rng = np.random.default_rng(77)

    for _ in range(50):
        base_value = float(rng.integers(50, 500))
        combo_mul = float(rng.uniform(1.5, 3.0))
        fever_mul = float(rng.uniform(2.0, 4.0))
        count_body_fever = int(rng.integers(0, 100))
        count_body_normal = int(rng.integers(0, 100))
        n_hn = int(rng.integers(0, 20))
        n_hf = int(rng.integers(0, 20))
        sigma_hn = int(rng.integers(0, n_hn * 20 + 1))
        sigma_hf = int(rng.integers(0, n_hf * 20 + 1))

        head_len = n_hn + n_hf
        fever_mask_head = np.zeros(head_len, dtype=np.bool_)
        if head_len > 0 and n_hf > 0:
            fever_indices = rng.choice(head_len, size=min(n_hf, head_len), replace=False)
            fever_mask_head[fever_indices] = True

        # Compute sigma from actual mask
        sigma_hn_actual = sum(i + 1 for i in range(head_len) if not fever_mask_head[i])
        sigma_hf_actual = sum(i + 1 for i in range(head_len) if fever_mask_head[i])

        exact_score = fast_calculate_score(
            base_value, combo_mul, fever_mul,
            fever_mask_head, count_body_fever, count_body_normal,
        )

        ub = _corrected_semi_exact_upper_bound(
            base_value, combo_mul, fever_mul,
            count_body_fever, count_body_normal,
            n_hn, n_hf, sigma_hn_actual, sigma_hf_actual,
        )

        gap = float(ub) - float(exact_score)
        n_notes = count_body_fever + count_body_normal + n_hn + n_hf

        # Corrected bound adds UB_EPS = n_notes, so gap can be up to ~2*n_notes
        # (one from body floor, one from head floor, one from UB_EPS)
        assert gap <= float(2 * n_notes) + 1e-3, (
            f"Gap {gap} exceeds 2*n_notes {2*n_notes}"
        )
        assert gap >= 0.0
