from __future__ import annotations

import numpy as np

from gear_optimizer.solver.exact_base_search import _refill_effective_candidate_rows


def test_effective_refill_continues_past_duplicate_high_bound_rows() -> None:
    evaluated = np.asarray([True, False, False, False, False], dtype=np.bool_)
    bounds = np.asarray([100, 90, 80, 70, 60], dtype=np.int32)
    effective_keys = {"a"}
    key_by_row = np.asarray(["a", "a", "b", "b", "c"], dtype=object)
    calls: list[list[int]] = []

    def evaluate_rows(selected: np.ndarray) -> None:
        calls.append([int(row) for row in selected])
        evaluated[selected] = True
        effective_keys.update(str(key_by_row[int(row)]) for row in selected)

    count = _refill_effective_candidate_rows(
        evaluated=evaluated,
        bounds=bounds,
        batch_limit=8,
        required=3,
        effective_count=lambda: len(effective_keys),
        evaluate_rows=evaluate_rows,
    )

    assert count == 3
    assert calls == [[1, 2], [3], [4]]


def test_effective_refill_stops_at_frontier_exhaustion() -> None:
    evaluated = np.asarray([True, False, False], dtype=np.bool_)
    bounds = np.asarray([100, 90, 80], dtype=np.int32)
    effective_keys = {"same"}

    def evaluate_rows(selected: np.ndarray) -> None:
        evaluated[selected] = True

    count = _refill_effective_candidate_rows(
        evaluated=evaluated,
        bounds=bounds,
        batch_limit=2,
        required=3,
        effective_count=lambda: len(effective_keys),
        evaluate_rows=evaluate_rows,
    )

    assert count == 1
    assert evaluated.tolist() == [True, True, True]
