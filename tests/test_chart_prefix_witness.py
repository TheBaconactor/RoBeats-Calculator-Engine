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


def test_section_prefix_witness_matches_chart_prefix_witness_across_modes_and_boundaries():
    """Differential test of section_prefix_witness against exact_label_hit_intervals + chart_prefix_witness across
    held tails, dense chords, HEAD_NOTES boundary, late_great, run_end == n, precise/non-precise, and exact clock edges."""
    from gear_optimizer.chart import Chart
    from gear_optimizer.frontier.producer_batch import song_arrays
    from gear_optimizer.solver.timing_envelope import HELD_TAIL_TYPE, time_song
    from gear_optimizer.trace.activation_witness import (
        exact_label_hit_intervals,
        section_prefix_witness,
        song_witness_template,
    )

    rng = np.random.default_rng(77)
    found = 0
    for trial in range(1200):
        n = int(rng.integers(2, 145))
        ts = (np.cumsum(rng.choice([0, 0, 5, 15, 45, 120], size=n)) * 0.001 + 1.0).astype(np.float32)
        lanes = rng.integers(1, 5, size=n, dtype=np.int32)
        ntypes = np.where(rng.random(n) < 0.28, HELD_TAIL_TYPE, 1).astype(np.int16)
        mode = "non-precise" if trial % 4 == 0 else "precise"
        chart = Chart(
            {"Song Name": "WitnessDiff", "Primary Color": "Rush", "Secondary Color": "Flow"},
            ts,
            ntypes,
            lanes,
            float(ts[-1]),
            int((ntypes != 1).sum()),
        )
        fg_in = time_song(chart, mode).fg_inputs
        ts_0, perfect_0, great_0, floor_0, great_floor_0, _, _, lane_0 = song_arrays(
            fg_in.timestamps,
            fg_in.perfect_candidates,
            fg_in.great_candidates,
            fg_in.perfect_floor,
            fg_in.great_floor,
            fg_in.late_great_floor,
            fg_in.exit_ceiling,
            fg_in.lanes,
        )
        m = int(ts_0.shape[0])
        if m < 2:
            continue
        tpl = song_witness_template(
            timestamps=ts_0,
            perfect_floor_timestamps=floor_0,
            perfect_candidate_timestamps=perfect_0,
            great_floor_timestamps=great_floor_0,
            great_candidate_timestamps=great_0,
            lanes=lane_0,
        )
        start = int(rng.integers(0, m))
        a = int(rng.integers(start, m))
        run_start = int(rng.integers(0, m + 1))
        run_end = m if trial % 7 == 0 else int(rng.integers(run_start, m + 1))
        late_great = bool(rng.random() < 0.3)
        is_great = np.zeros(m, dtype=np.bool_)
        is_great[run_start:run_end] = True
        if late_great:
            is_great[a] = True
        pre_events = a - start
        pre_greats = max(0, min(a, run_end) - max(start, run_start))
        pre_fill = 2 * pre_events - pre_greats
        denom = 0.5 * pre_fill + float(rng.choice([0.0, 0.25, 0.5, 1.0, 1.5]))
        hit = (
            float(floor_0[start - 1])
            if trial % 9 == 0 and start > 0
            else float(np.float32(float(ts_0[a]) + float(rng.uniform(-0.08, 0.08))))
        )
        pred = None if start == 0 else float(floor_0[start - 1])
        labels = exact_label_hit_intervals(
            is_great=is_great,
            timestamps=ts_0,
            perfect_floor_timestamps=floor_0,
            perfect_candidate_timestamps=perfect_0,
            great_floor_timestamps=great_floor_0,
            great_candidate_timestamps=great_0,
        )
        w_ref = chart_prefix_witness(
            labels=labels,
            lanes=lane_0,
            activation_index=a,
            activation_hit_timestamp=hit,
            fever_fill_denom=denom,
            preactivation_fill=pre_fill,
            section_start=start,
            predecessor_hit_timestamp=pred,
        )
        w_new = section_prefix_witness(
            tpl,
            run_start=run_start,
            run_end=run_end,
            late_great=late_great,
            activation_index=a,
            activation_hit_timestamp=hit,
            fever_fill_denom=denom,
            preactivation_fill=pre_fill,
            section_start=start,
            predecessor_hit_timestamp=pred,
        )
        if w_new is not None:
            found += 1
        assert w_new == w_ref
    assert found >= 150
