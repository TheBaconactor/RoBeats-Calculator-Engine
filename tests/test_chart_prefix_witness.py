"""chart_prefix_witness reads what the general witness search reads when the chart-order prefix plays."""
from __future__ import annotations

import numpy as np

from gear_optimizer.trace.activation_witness import LabelHitIntervals, chart_prefix_witness
from tests.activation_witness_oracle import activation_schedule_witnesses


def _labels(rng, n):
    times = np.cumsum(rng.integers(0, 60, n)) * 0.001 + 1.0
    is_great = rng.random(n) < 0.3
    empty_low, empty_high = np.float32(np.inf), np.float32(-np.inf)
    return LabelHitIntervals(
        is_great,
        np.where(is_great, times - 0.08, times - 0.04).astype(np.float32),
        np.where(is_great, times - 0.04, times + 0.04).astype(np.float32),
        np.where(is_great, times + 0.04, empty_low).astype(np.float32),
        np.where(is_great, times + 0.08, empty_high).astype(np.float32),
    ), times


def test_the_chart_order_witness_is_the_search_s():
    rng = np.random.default_rng(0)
    found = 0
    for _ in range(3000):
        n = int(rng.integers(2, 140))
        labels, times = _labels(rng, n)
        lanes = rng.integers(1, 5, n).astype(np.int32)
        start = int(rng.integers(0, n))
        a = int(rng.integers(start, n))
        fill = int(np.where(labels.is_great[start:a], 1, 2).sum())
        denom = 0.5 * fill + 0.25
        hit = float(np.float32(times[a] + rng.uniform(-0.03, 0.03)))
        predecessor = None if start == 0 else float(labels.primary_low[start - 1])
        witness = chart_prefix_witness(
            labels=labels, lanes=lanes, activation_index=a, activation_hit_timestamp=hit, fever_fill_denom=denom,
            preactivation_fill=fill, section_start=start, predecessor_hit_timestamp=predecessor,
        )
        rows = activation_schedule_witnesses(
            labels=labels, lanes=lanes, activation_index=a, activation_hit_timestamp=hit, fever_fill_denom=denom,
            section_start=start, predecessor_hit_timestamp=predecessor, required_signature=(fill, a - start),
        )
        chart_rows = [row for row in rows if sorted(row.preactivation_order) == list(range(start, a))]
        if witness is None:
            assert not chart_rows
        else:
            found += 1
            assert [row.preactivation_order for row in chart_rows] == [witness.order]
            assert [(row.lane, len(row.note_indices)) for row in chart_rows[0].lane_prefixes] == list(witness.lane_counts)
    assert found > 300
