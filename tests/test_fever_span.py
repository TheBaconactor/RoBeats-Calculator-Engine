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
