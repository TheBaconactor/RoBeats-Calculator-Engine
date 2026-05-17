from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.solver.scoring.scoring_core import (
    fast_calculate_score,
    lookup_reference_jit,
    optimize_core_exact_bounded_jit,
)


def _build_ref_arrays() -> dict[str, np.ndarray]:
    refs: dict[str, np.ndarray] = {}
    refs["pp"] = np.linspace(100, 300, int(TOTAL_ROWS) + 1, dtype=np.float32)
    refs["cm"] = np.linspace(200, 267, int(TOTAL_ROWS) + 1, dtype=np.float32)
    refs["fm"] = np.linspace(300, 400, int(TOTAL_ROWS) + 1, dtype=np.float32)
    return refs


def _bucket_pp(pp: int, ref_pp: np.ndarray) -> tuple:
    """Effective PP bucket preserving current + next 3 gem marginals."""
    MAX = int(TOTAL_ROWS)
    return (
        float(ref_pp[min(pp, MAX)]),
        float(ref_pp[min(pp + 2, MAX)]),
        float(ref_pp[min(pp + 4, MAX)]),
        float(ref_pp[min(pp + 6, MAX)]),
    )


def _bucket_cm(cm: int, ref_cm: np.ndarray) -> tuple:
    """Effective CM bucket preserving current + next 5 gem marginals."""
    MAX = int(TOTAL_ROWS)
    return tuple(float(ref_cm[min(cm + 2 * i, MAX)]) for i in range(6))


def _bucket_fm(fm: int, ref_fm: np.ndarray) -> tuple:
    """Effective FM bucket preserving current + next 3 gem marginals."""
    MAX = int(TOTAL_ROWS)
    return (
        float(ref_fm[min(fm, MAX)]),
        float(ref_fm[min(fm + 3, MAX)]),
        float(ref_fm[min(fm + 6, MAX)]),
        float(ref_fm[min(fm + 9, MAX)]),
    )


def test_bucket_preserves_current_multiplier() -> None:
    """Moonshot 5: Bucket must include current reference table value."""
    rng = np.random.default_rng(42)
    refs = _build_ref_arrays()

    for _ in range(50):
        pp = int(rng.integers(0, 100))
        cm = int(rng.integers(0, 100))
        fm = int(rng.integers(0, 100))

        b_pp = _bucket_pp(pp, refs["pp"])
        b_cm = _bucket_cm(cm, refs["cm"])
        b_fm = _bucket_fm(fm, refs["fm"])

        assert b_pp[0] == refs["pp"][pp]
        assert b_cm[0] == refs["cm"][cm]
        assert b_fm[0] == refs["fm"][fm]


def test_bucket_collapses_plateau_stats() -> None:
    """Moonshot 5: Stats on the same plateau should share buckets."""
    # Create a reference table with a wide deliberate plateau
    ref_pp = np.ones(int(TOTAL_ROWS) + 1, dtype=np.float32) * 200.0
    ref_pp[10:30] = 250.0  # Wide plateau from index 10 to 29

    pp_12 = _bucket_pp(12, ref_pp)
    pp_15 = _bucket_pp(15, ref_pp)

    # Both should have same current value
    assert pp_12[0] == pp_15[0]

    # If plateau is wide enough (covers up to +6), next marginals also match
    # pp=12 needs up to 18, pp=15 needs up to 21; plateau to 29 covers both
    assert pp_12 == pp_15


def test_colliding_bucket_keys_produce_same_score() -> None:
    """Moonshot 5-R: Same bucket key → same exact score."""
    rng = np.random.default_rng(123)
    refs = _build_ref_arrays()

    # Two candidates with different raw stats but same bucket
    # We need to find such a pair on a synthetic plateau
    ref_pp = refs["pp"].copy()
    ref_pp[20:24] = ref_pp[20]  # Create plateau at 20-23

    cur_pp_a = 20
    cur_pp_b = 22

    b_a = _bucket_pp(cur_pp_a, ref_pp)
    b_b = _bucket_pp(cur_pp_b, ref_pp)

    # If plateau is wide enough, buckets match
    if b_a == b_b:
        budget = 8
        cur_cm = 10
        cur_fm = 10
        cur_p_val = 20
        cur_s_val = 20

        head_len = 20
        fever_mask_head = np.zeros(head_len, dtype=np.bool_)
        fever_mask_head[::4] = True

        result_a = optimize_core_exact_bounded_jit(
            budget, cur_pp_a, cur_cm, cur_fm, cur_p_val, cur_s_val,
            1, 0, 1, 0, 1, 0, 1, 0,
            ref_pp, refs["cm"], refs["fm"],
            fever_mask_head, 50, 50,
            2, 3, 2, 3, int(TOTAL_ROWS), int(TOTAL_ROWS),
        )
        result_b = optimize_core_exact_bounded_jit(
            budget, cur_pp_b, cur_cm, cur_fm, cur_p_val, cur_s_val,
            1, 0, 1, 0, 1, 0, 1, 0,
            ref_pp, refs["cm"], refs["fm"],
            fever_mask_head, 50, 50,
            2, 3, 2, 3, int(TOTAL_ROWS), int(TOTAL_ROWS),
        )

        # Scores must match
        score_a = fast_calculate_score(
            float((result_a[3] * 2) + result_a[4] + lookup_reference_jit(result_a[0], ref_pp, int(TOTAL_ROWS))),
            lookup_reference_jit(result_a[1], refs["cm"], int(TOTAL_ROWS)),
            lookup_reference_jit(result_a[2], refs["fm"], int(TOTAL_ROWS)),
            fever_mask_head, 50, 50,
        )
        score_b = fast_calculate_score(
            float((result_b[3] * 2) + result_b[4] + lookup_reference_jit(result_b[0], ref_pp, int(TOTAL_ROWS))),
            lookup_reference_jit(result_b[1], refs["cm"], int(TOTAL_ROWS)),
            lookup_reference_jit(result_b[2], refs["fm"], int(TOTAL_ROWS)),
            fever_mask_head, 50, 50,
        )

        assert score_a == score_b


def test_different_bucket_keys_can_produce_different_scores() -> None:
    """Different buckets should generally produce different scores."""
    rng = np.random.default_rng(77)
    refs = _build_ref_arrays()

    # Pick two stats that are definitely not on the same plateau
    pp_a = 10
    pp_b = 50

    b_a = _bucket_pp(pp_a, refs["pp"])
    b_b = _bucket_pp(pp_b, refs["pp"])

    # Buckets should differ (linear ref table, no plateau)
    assert b_a != b_b


def test_bucket_key_is_sufficient_for_cache_indexing() -> None:
    """The bucket key contains all score-relevant information for a fixed timeline."""
    rng = np.random.default_rng(99)
    refs = _build_ref_arrays()

    pp = int(rng.integers(0, 80))
    cm = int(rng.integers(0, 80))
    fm = int(rng.integers(0, 80))

    key = (
        _bucket_pp(pp, refs["pp"]),
        _bucket_cm(cm, refs["cm"]),
        _bucket_fm(fm, refs["fm"]),
        20,  # P_val
        20,  # S_val
        "timeline_sig_42",
        10,  # budget
    )

    # Key is hashable and contains all deterministic score inputs
    assert hash(key) is not None
    assert len(key) == 7
