"""Custom per-note timing base replay (generalizes zero_ms).

``score_stats_timing_exact_batch`` scores the base leaderboard under an EXPLICIT per-note
hit-time timeline (chart + T). These CPU tests pin:

- the parity gate: ``T == 0`` (hit_timestamps == chart) reproduces the fixed-0ms/``zero_ms``
  scorer bit-for-bit -- the property that lets the general path replace the bespoke one;
- uniform-shift invariance (a constant offset cannot change the relative timeline);
- that a non-uniform offset genuinely moves the exact score; and
- the fail-loud guards (reordering / wrong-length timing vectors are invalid input).

"""

from __future__ import annotations

from tests.curves_support import synthetic_curves
import numpy as np
import pytest

from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.scoring.exact_rescore import (
    score_stats_fixed_timing_exact_batch,
    score_stats_timing_exact_batch,
)
from gear_optimizer.solver.timing_envelope import time_song
from tests.songs_support import make_chart


def _curves() -> dict[str, np.ndarray]:
    rows = MAX_STAT + 1
    return synthetic_curves({
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 4.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.3, 1.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(0.3, 1.0, rows, dtype=np.float64),
    })


def _song(baseline_offset=None, mode: str = "zero_ms"):
    timestamps = np.round(np.arange(250, dtype=np.float32) * np.float32(0.1), 3).astype(np.float32)
    return time_song(make_chart(timestamps, primary="Rush", secondary="Flow"), mode, baseline_offset)


def _stats() -> dict[str, int]:
    return {
        "Perfect Points": 40,
        "Combo Multiplier": 55,
        "Fever Multiplier": 30,
        "Fever Time": 70,
        "Fever Fill Rate": 90,
        "Rush": 20,
        "Flow": 10,
        "Chill": 0,
        "Beat": 0,
        "Vibe": 0,
    }


def _chart(song) -> np.ndarray:
    return song.chart.timestamps


def test_timing_at_zero_offset_matches_fixed_timing_bit_exact():
    """Parity gate: T == 0 (hit_timestamps == chart) == the zero_ms fixed-0ms scorer."""
    rows = [_stats(), {**_stats(), "Fever Time": 5, "Fever Fill Rate": 5}]
    song = _song()
    ref = _curves()

    fixed = score_stats_fixed_timing_exact_batch(rows, song, ref)
    general = score_stats_timing_exact_batch(rows, song, ref, _chart(song))
    assert general == fixed
    assert general[0] > 0


def test_uniform_offset_is_score_invariant():
    """A uniform shift of every hit preserves the relative timeline -> identical fever -> same score."""
    rows = [_stats()]
    song = _song()
    ref = _curves()

    base = score_stats_timing_exact_batch(rows, song, ref, _chart(song))
    for shift in (np.float32(0.5), np.float32(-0.25)):
        shifted = (_chart(song) + shift).astype(np.float32)
        assert score_stats_timing_exact_batch(rows, song, ref, shifted) == base


def test_non_uniform_offset_changes_score():
    """A per-note offset that moves a fever boundary changes the exact score."""
    rows = [_stats()]
    song = _song()
    ref = _curves()

    base = score_stats_timing_exact_batch(rows, song, ref, _chart(song))
    # A monotone stretch pushes each note progressively later, widening inter-note spacing so the
    # fixed-duration fever windows cover fewer notes -> a different exact score. Stays sorted
    # (per-note increment 4ms << 100ms base spacing).
    ramp = (np.arange(250, dtype=np.float32) * np.float32(0.004)).astype(np.float32)
    hits = (_chart(song) + ramp).astype(np.float32)
    assert score_stats_timing_exact_batch(rows, song, ref, hits) != base


def test_reordering_offset_fails_loud():
    """hit_timestamps that reorder notes (non-monotonic) is invalid external input."""
    song = _song()
    ref = _curves()
    hits = _chart(song).copy()
    hits[10] = hits[10] + np.float32(0.5)  # jumps past several later notes
    with pytest.raises(ValueError, match="non-decreasing"):
        score_stats_timing_exact_batch([_stats()], song, ref, hits)


def test_wrong_length_offset_fails_loud():
    song = _song()
    ref = _curves()
    with pytest.raises(ValueError, match="length"):
        score_stats_timing_exact_batch([_stats()], song, ref, _chart(song)[:-1])


# --- time_song(baseline_offset=T): the prep-time T lever (zero_ms = T==0 preset) ---


def test_zero_ms_preset_leaves_chart_and_empty_hash():
    song = _song()  # no baseline_offset -> T == 0
    assert song.mode == "zero_ms"
    assert song.baseline_hash == ""
    np.testing.assert_array_equal(song.hit_timestamps, _chart(song))


def test_all_zero_offset_equals_zero_ms_preset():
    song = _song(np.zeros(250, dtype=np.float32))
    assert song.baseline_hash == ""
    np.testing.assert_array_equal(song.hit_timestamps, _chart(song))


def test_baseline_offset_shifts_hit_timestamps_and_hashes():
    offset = np.full(250, 0.03, dtype=np.float32)
    song = _song(offset)
    assert song.baseline_hash != ""
    np.testing.assert_allclose(song.hit_timestamps, _chart(song) + offset, atol=1e-6)


def test_distinct_offsets_give_disjoint_cache_context():
    ctx0 = _song().timeline_key[-4:]  # T == 0
    ctxa = _song(np.full(250, 0.02, dtype=np.float32)).timeline_key[-4:]
    ctxb = _song(np.full(250, 0.05, dtype=np.float32)).timeline_key[-4:]
    assert ctx0 != ctxa
    assert ctx0 != ctxb
    assert ctxa != ctxb
    # T == 0 context is unchanged from the historical zero_ms (empty baseline slot).
    assert ctx0[2] == ""


def test_prepared_baseline_offset_score_matches_direct_and_differs_from_zero():
    ref = _curves()
    rows = [_stats()]
    ramp = (np.arange(250, dtype=np.float32) * np.float32(0.004)).astype(np.float32)
    song0 = _song()
    song_t = _song(ramp)

    base0 = score_stats_fixed_timing_exact_batch(rows, song0, ref)
    base_t = score_stats_fixed_timing_exact_batch(rows, song_t, ref)
    # The prepared scorer reads the hit timeline (= chart + T); equals scoring chart+T directly.
    direct = score_stats_timing_exact_batch(rows, song_t, ref, (_chart(song_t) + ramp).astype(np.float32))
    assert base_t == direct
    assert base_t != base0


def test_baseline_offset_reordering_fails_loud_in_prep():
    bad = np.zeros(250, dtype=np.float32)
    bad[10] = np.float32(0.5)
    with pytest.raises(ValueError, match="reorder"):
        _song(bad)


def test_baseline_offset_rejected_for_perfect_window():
    with pytest.raises(ValueError, match="only valid for fixed"):
        _song(np.full(250, 0.02, dtype=np.float32), mode="perfect_window")


def test_cache_context_is_inert_at_zero_t_lossless():
    """LOSSLESS GUARD: the per-note ``T`` hash lives in the timing-context reserved slots, so at
    ``T == 0`` the timing cache keys are byte-identical to their pre-feature values. These frozen
    tuples lock that existing zero_ms cache keys (and therefore cached scores) are unchanged and that
    perfect_window carries only its cache revision -- if a future edit leaks a non-empty hash at
    ``T == 0``, this fails."""
    assert _song().timeline_key[-4:] == ("TIMING_ENVELOPE", "zero_ms", "", 0)
    assert _song(mode="perfect_window").timeline_key[-4:] == ("TIMING_ENVELOPE", "perfect_window@2", "", 0)
