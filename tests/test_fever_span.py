"""fever_span's sweep against the nested-loop reference it replaced: same (fewest, highest) on random
monotone event times and on a real chart's windows."""

from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.reverse.fever_reach import fever_span


def _reference_fever_span(times, fills, duration):
    """The implementation fever_span replaced, verbatim."""
    earliest, latest = times
    fill_lo, fill_hi = fills
    n = earliest.shape[0]
    most = np.full(n, -1, dtype=np.int64)
    least = np.full(n, n + 1, dtype=np.int64)
    fewest, highest = n, -1
    if fill_hi > n:
        fewest, highest = 0, 0
    for a in range(fill_lo - 1, min(fill_hi, n)):
        most[a], least[a] = 0, 0
    for a in range(n):
        if most[a] < 0:
            continue
        first = min(max(int(np.searchsorted(latest, earliest[a] + duration, side="left")), a + 1), n)
        last = max(min(int(np.searchsorted(earliest, latest[a] + duration, side="left")), n), first)
        for end in range(first, last + 1):
            if end + fill_hi >= n:
                fewest, highest = min(fewest, least[a] + end - a), max(highest, most[a] + end - a)
            for activation in range(end + fill_lo, min(end + fill_hi + 1, n)):
                most[activation] = max(most[activation], most[a] + end - a)
                least[activation] = min(least[activation], least[a] + end - a)
    return fewest, highest


def _case(rng, n, spread_lo, spread_hi):
    # event_times' contract: the k-th smallest earliest and latest play times, each sorted; the widths
    # keep latest >= earliest elementwise, as the order statistics do.
    starts = np.sort(rng.integers(0, 10_000, n)).astype(np.float64)
    widths = rng.integers(spread_lo, spread_hi, n).astype(np.float64)
    return np.ascontiguousarray(starts), np.ascontiguousarray(np.sort(starts + widths))


@pytest.mark.parametrize("seed", range(40))
def test_fever_span_matches_reference(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(1, 400))
    times = _case(rng, n, 0, 500)
    threshold = float(rng.uniform(1.0, 40.0))
    fill_lo = int(np.ceil(threshold))
    fill_hi = int(np.ceil(threshold + rng.uniform(0.0, 30.0)))
    duration = float(rng.uniform(0.0, 8000.0))
    assert fever_span(times, (fill_lo, fill_hi), duration) == _reference_fever_span(
        times, (fill_lo, fill_hi), duration
    )


@pytest.mark.parametrize("fill_lo,fill_hi,duration", [(1, 1, 0.0), (3, 90, 100.0), (40, 400, 10.0), (2, 2, 1e9)])
def test_fever_span_edges(fill_lo, fill_hi, duration):
    rng = np.random.default_rng(7)
    times = _case(rng, 64, 0, 300)
    assert fever_span(times, (fill_lo, fill_hi), duration) == _reference_fever_span(
        times, (fill_lo, fill_hi), duration
    )


def test_fever_span_zero_width_events():
    # Identical earliest/latest (no timing slack): every position's window is one end.
    times = np.arange(50, dtype=np.float64) * 100.0, np.arange(50, dtype=np.float64) * 100.0
    assert fever_span(times, (3, 5), 250.0) == _reference_fever_span(times, (3, 5), 250.0)


def test_fever_span_real_chart():
    pytest.importorskip("gear_optimizer.chart")
    from gear_optimizer.chart import load_chart
    from gear_optimizer.settings import paths

    charts = sorted(paths().data_dir.glob("Hard/*.txt")) or sorted(paths().data_dir.glob("*/*.txt"))
    if not charts:
        pytest.skip("no chart data")
    chart = load_chart(charts[0])
    from gear_optimizer.reverse.fever_reach import event_times

    for perfect_time in (0, 13):
        times = event_times(chart, perfect_time)
        for threshold, quarters, duration in ((20.0, 24, 1500.0), (5.0, 8, 400.0), (80.0, 120, 6000.0)):
            fills = (int(np.ceil(threshold)), int(np.ceil(threshold + quarters / 2.0)))
            assert fever_span(times, fills, duration) == _reference_fever_span(times, fills, duration)


def test_casual_classes_handles_unbounded_and_extreme_windows() -> None:
    from gear_optimizer.reverse.greats import HEAD_LISTED, casual_classes

    losses = np.array([60, 80, 100, 120, 140], dtype=np.int64)
    timelines = [(10_000, losses), (10_300, losses)]
    for greats in (1, 2, 5):
        unbounded = casual_classes((9_600.0, np.inf), timelines, greats=greats, listed_up_to=HEAD_LISTED)
        bounded = casual_classes((9_600.0, 10_300.0), timelines, greats=greats, listed_up_to=HEAD_LISTED)
        assert np.array_equal(unbounded, bounded)
        huge = casual_classes((9_600.0, 1.0e100), timelines, greats=greats, listed_up_to=HEAD_LISTED)
        assert np.array_equal(huge, bounded)
    assert casual_classes((20_000.0, np.inf), timelines, greats=2, listed_up_to=HEAD_LISTED).shape == (0, 9)


def test_fever_surfaces_matches_single_threaded_reference_with_greats() -> None:
    from gear_optimizer.chart import Chart
    from gear_optimizer.gamedata import stat_curves
    from gear_optimizer.reverse.fever_reach import (
        CELLS,
        _distinct,
        _walk_grid,
        event_times,
        fever_surfaces,
        great_times,
        pattern_words,
    )
    from gear_optimizer.score import HEAD_NOTES
    from gear_optimizer.solver.timing_envelope import HELD_TAIL_TYPE, fever_axes

    rng = np.random.default_rng(123)
    n = 135
    ts = (np.cumsum(rng.choice([0, 10, 35, 90, 180], size=n)) * 0.001 + 0.5).astype(np.float32)
    ntypes = np.where(rng.random(n) < 0.25, HELD_TAIL_TYPE, 1).astype(np.int16)
    lanes = rng.integers(1, 5, size=n, dtype=np.int32)
    chart = Chart(
        {"Song Name": "SynthReach", "Primary Color": "Rush", "Secondary Color": "Flow"},
        ts,
        ntypes,
        lanes,
        float(ts[-1]),
        int((ntypes != 1).sum()),
    )
    curves = stat_curves()
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, curves)

    for perfect_time in (0, 13):
        for greats in (0, 2, 4):
            got = fever_surfaces(chart, curves, perfect_time, greats=greats)
            ref_rows = _walk_grid(
                event_times(chart, perfect_time),
                great_times(chart, perfect_time),
                thresholds.astype(np.float64),
                durations * 1000.0,
                greats,
                (0, durations.shape[0]),
            )
            first, ids, order = _distinct((ref_rows[:, 0], ref_rows[:, 1], ref_rows[:, 2]))
            patterns, pattern_ids, _ = _distinct((ref_rows[first, 0], ref_rows[first, 1]))
            ref_words = pattern_words(ref_rows[first[patterns], 0], ref_rows[first[patterns], 1])
            pairs = ids[order].astype(np.int64) * CELLS + ref_rows[order, 3]
            pairs = pairs[np.concatenate(([True], pairs[1:] != pairs[:-1]))]
            assert np.array_equal(got.words, ref_words)
            assert np.array_equal(got.pattern, pattern_ids)
            assert np.array_equal(got.body_fever, ref_rows[first, 2].astype(np.int32))
            assert np.array_equal(got.cell_start, np.searchsorted(pairs // CELLS, np.arange(first.shape[0] + 1)))
            assert np.array_equal(got.cells, (pairs % CELLS).astype(np.int32))
            assert got.coeffs.shape == (ref_words.shape[0], 4)
            assert min(chart.total_notes, HEAD_NOTES) == 100
