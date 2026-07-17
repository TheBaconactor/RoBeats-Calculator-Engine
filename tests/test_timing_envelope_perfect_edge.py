from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.solver.timing_envelope import build_perfect_candidate_envelope_sec


@pytest.mark.parametrize(("note_type", "upper_ms"), ((1, 40.0), (3, 80.0)))
def test_perfect_candidate_is_latest_float32_inside_hard_judgment_edge(
    note_type: int,
    upper_ms: float,
) -> None:
    """Issue #161: integer-ms envelope encoding must not cross the hard delta edge."""
    chart = np.asarray([50.82], dtype=np.float32)
    candidate = build_perfect_candidate_envelope_sec(
        chart,
        np.asarray([note_type], dtype=np.int32),
    )[0]
    hard_upper = float(chart[0]) + float(upper_ms) / 1000.0

    assert float(candidate) <= hard_upper
    assert float(np.nextafter(candidate, np.float32(np.inf))) > hard_upper
    assert (float(candidate) - float(chart[0])) * 1000.0 <= upper_ms
