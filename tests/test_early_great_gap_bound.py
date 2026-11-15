"""early_great_gap_bound's merge against the searchsorted reference it replaced: same bound on random
sorted floors, ties, edges and a real chart's floors."""

from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.frontier.producer_reducer import early_great_gap_bound


def _reference_gap_bound(perfect_floor, great_floor):
    """The implementation early_great_gap_bound replaced, verbatim."""
    cutoffs = np.concatenate((perfect_floor, great_floor))
    gaps = np.searchsorted(great_floor, cutoffs, side="right") - np.searchsorted(
        perfect_floor, cutoffs, side="right"
    )
    return int(gaps.max(initial=0))


def _floor(rng, n, integer):
    # event floors are sorted timestamps (float32 on a real chart, small negatives included); integer
    # values stress ties, float ones the general case.
    if integer:
        return np.sort(rng.integers(-2, 60, n)).astype(np.float32)
    return np.sort(rng.random(n).astype(np.float32) * 180.0 - 0.01)


@pytest.mark.parametrize("seed", range(40))
@pytest.mark.parametrize("integer", [True, False])
def test_gap_bound_matches_reference(seed, integer):
    rng = np.random.default_rng(seed)
    pf = _floor(rng, int(rng.integers(1, 400)), integer)
    gf = _floor(rng, int(rng.integers(1, 400)), integer)
    assert early_great_gap_bound(pf, gf) == _reference_gap_bound(pf, gf)


@pytest.mark.parametrize(
    "pf,gf",
    [
        (np.array([], np.float32), np.array([], np.float32)),
        (np.array([1.0], np.float32), np.array([1.0], np.float32)),
        (np.array([0.0], np.float32), np.array([], np.float32)),
        (np.array([], np.float32), np.array([0.0], np.float32)),
        (np.full(9, 3.5, np.float32), np.full(9, 3.5, np.float32)),
        (np.arange(8, dtype=np.float32), np.arange(8, dtype=np.float32) + 100.0),
        (np.array([0.5, 0.5, 0.5], np.float32), np.array([0.5], np.float32)),
    ],
)
def test_gap_bound_edges(pf, gf):
    assert early_great_gap_bound(pf, gf) == _reference_gap_bound(pf, gf)


def test_gap_bound_identical_floors_is_zero():
    # Great floor == Perfect floor: no cutoff ever reaches further on the Great floor.
    floors = np.sort(np.random.default_rng(3).random(50).astype(np.float32))
    assert early_great_gap_bound(floors, floors.copy()) == 0


def test_gap_bound_real_chart():
    pytest.importorskip("gear_optimizer.chart")
    from gear_optimizer.chart import load_chart
    from gear_optimizer.frontier.fg_cache_keys import response_axes
    from gear_optimizer.gamedata import stat_curves
    from gear_optimizer.settings import paths
    from gear_optimizer.solver.timing_envelope import time_song

    charts = sorted(paths().data_dir.glob("Hard/*.txt")) or sorted(paths().data_dir.glob("*/*.txt"))
    if not charts:
        pytest.skip("no chart data")
    song, *_ = response_axes(time_song(load_chart(charts[0]), "precise"), stat_curves())
    assert early_great_gap_bound(song.perfect_floor, song.great_floor) == _reference_gap_bound(
        song.perfect_floor, song.great_floor
    )
