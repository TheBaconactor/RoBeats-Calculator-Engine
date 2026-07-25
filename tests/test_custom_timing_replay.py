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

import numpy as np
import pytest

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.utils import timing_envelope_full_context, timing_envelope_timing_context
from gear_optimizer.solver.scoring.exact_rescore import (
    score_stats_fixed_timing_exact_batch,
    score_stats_timing_exact_batch,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope


def _ref_arrays() -> dict[str, np.ndarray]:
    rows = TOTAL_ROWS + 1
    return {
        "Perfect Points": np.linspace(0.0, 10.0, rows, dtype=np.float64),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows, dtype=np.float64),
        "Fever Multiplier": np.linspace(1.0, 4.0, rows, dtype=np.float64),
        "Fever Fill Rate": np.linspace(0.3, 1.0, rows, dtype=np.float64),
        "Fever Time": np.linspace(0.3, 1.0, rows, dtype=np.float64),
    }


def _calc_song() -> dict:
    timestamps = np.round(np.arange(250, dtype=np.float32) * np.float32(0.1), 3).astype(np.float32)
    return {
        "metadata": {
            "Primary Color": "Rush",
            "Secondary Color": "Flow",
            "Long Notes": 0,
            "Last Note Time": float(timestamps[-1]),
        },
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
        },
    }


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


def _chart(cs: dict) -> np.ndarray:
    return np.asarray(cs["song_data"]["chart_timestamps"], dtype=np.float32)


def test_timing_at_zero_offset_matches_fixed_timing_bit_exact():
    """Parity gate: T == 0 (hit_timestamps == chart) == the zero_ms fixed-0ms scorer."""
    rows = [_stats(), {**_stats(), "Fever Time": 5, "Fever Fill Rate": 5}]
    cs = _calc_song()
    ref = _ref_arrays()

    fixed = score_stats_fixed_timing_exact_batch(rows, cs, ref)
    general = score_stats_timing_exact_batch(rows, cs, ref, _chart(cs))
    assert general == fixed
    assert general[0] > 0


def test_uniform_offset_is_score_invariant():
    """A uniform shift of every hit preserves the relative timeline -> identical fever -> same score."""
    rows = [_stats()]
    cs = _calc_song()
    ref = _ref_arrays()

    base = score_stats_timing_exact_batch(rows, cs, ref, _chart(cs))
    for shift in (np.float32(0.5), np.float32(-0.25)):
        shifted = (_chart(cs) + shift).astype(np.float32)
        assert score_stats_timing_exact_batch(rows, cs, ref, shifted) == base


def test_non_uniform_offset_changes_score():
    """A per-note offset that moves a fever boundary changes the exact score."""
    rows = [_stats()]
    cs = _calc_song()
    ref = _ref_arrays()

    base = score_stats_timing_exact_batch(rows, cs, ref, _chart(cs))
    # A monotone stretch pushes each note progressively later, widening inter-note spacing so the
    # fixed-duration fever windows cover fewer notes -> a different exact score. Stays sorted
    # (per-note increment 4ms << 100ms base spacing).
    ramp = (np.arange(250, dtype=np.float32) * np.float32(0.004)).astype(np.float32)
    hits = (_chart(cs) + ramp).astype(np.float32)
    assert score_stats_timing_exact_batch(rows, cs, ref, hits) != base


def test_reordering_offset_fails_loud():
    """hit_timestamps that reorder notes (non-monotonic) is invalid external input."""
    cs = _calc_song()
    ref = _ref_arrays()
    hits = _chart(cs).copy()
    hits[10] = hits[10] + np.float32(0.5)  # jumps past several later notes
    with pytest.raises(ValueError, match="non-decreasing"):
        score_stats_timing_exact_batch([_stats()], cs, ref, hits)


def test_wrong_length_offset_fails_loud():
    cs = _calc_song()
    ref = _ref_arrays()
    with pytest.raises(ValueError, match="length"):
        score_stats_timing_exact_batch([_stats()], cs, ref, _chart(cs)[:-1])


# --- apply_timing_envelope(baseline_offset=T): the prep-time T lever (zero_ms = T==0 preset) ---


def test_zero_ms_preset_leaves_chart_and_empty_hash():
    cs = _calc_song()
    info = apply_timing_envelope(cs, mode="zero_ms")  # no baseline_offset -> T == 0
    assert info["timing_mode"] == "zero_ms"
    assert info["baseline_hash"] == ""
    assert cs["metadata"]["TimingEnvelopeBaselineHash"] == ""
    np.testing.assert_array_equal(np.asarray(cs["song_data"]["fg_timestamps"]), _chart(cs))


def test_all_zero_offset_equals_zero_ms_preset():
    cs = _calc_song()
    info = apply_timing_envelope(cs, mode="zero_ms", baseline_offset=np.zeros(250, dtype=np.float32))
    assert info["baseline_hash"] == ""
    np.testing.assert_array_equal(np.asarray(cs["song_data"]["fg_timestamps"]), _chart(cs))


def test_baseline_offset_shifts_fg_timestamps_and_hashes():
    cs = _calc_song()
    chart = _chart(cs)
    offset = np.full(250, 0.03, dtype=np.float32)
    info = apply_timing_envelope(cs, mode="zero_ms", baseline_offset=offset)
    assert info["baseline_hash"] != ""
    np.testing.assert_allclose(np.asarray(cs["song_data"]["fg_timestamps"]), chart + offset, atol=1e-6)


def test_distinct_offsets_give_disjoint_cache_context():
    cs0 = _calc_song()
    apply_timing_envelope(cs0, mode="zero_ms")  # T == 0
    csa = _calc_song()
    apply_timing_envelope(csa, mode="zero_ms", baseline_offset=np.full(250, 0.02, dtype=np.float32))
    csb = _calc_song()
    apply_timing_envelope(csb, mode="zero_ms", baseline_offset=np.full(250, 0.05, dtype=np.float32))

    ctx0 = timing_envelope_timing_context(cs0)
    ctxa = timing_envelope_timing_context(csa)
    ctxb = timing_envelope_timing_context(csb)
    assert ctx0 != ctxa
    assert ctx0 != ctxb
    assert ctxa != ctxb
    # T == 0 context is unchanged from the historical zero_ms (empty baseline slot).
    assert ctx0[2] == ""


def test_prepared_baseline_offset_score_matches_direct_and_differs_from_zero():
    ref = _ref_arrays()
    rows = [_stats()]
    cs0 = _calc_song()
    apply_timing_envelope(cs0, mode="zero_ms")
    csT = _calc_song()
    ramp = (np.arange(250, dtype=np.float32) * np.float32(0.004)).astype(np.float32)
    apply_timing_envelope(csT, mode="zero_ms", baseline_offset=ramp)

    base0 = score_stats_fixed_timing_exact_batch(rows, cs0, ref)
    base_t = score_stats_fixed_timing_exact_batch(rows, csT, ref)
    # The prepared scorer reads fg_timestamps (= chart + T); equals scoring chart+T directly.
    direct = score_stats_timing_exact_batch(rows, csT, ref, (_chart(csT) + ramp).astype(np.float32))
    assert base_t == direct
    assert base_t != base0


def test_baseline_offset_reordering_fails_loud_in_prep():
    cs = _calc_song()
    bad = np.zeros(250, dtype=np.float32)
    bad[10] = np.float32(0.5)
    with pytest.raises(ValueError, match="reorder"):
        apply_timing_envelope(cs, mode="zero_ms", baseline_offset=bad)


def test_baseline_offset_rejected_for_perfect_window():
    cs = _calc_song()
    with pytest.raises(ValueError, match="only valid for fixed"):
        apply_timing_envelope(cs, mode="perfect_window", baseline_offset=np.full(250, 0.02, dtype=np.float32))


def test_cache_context_is_inert_at_zero_t_lossless():
    """LOSSLESS GUARD: the per-note ``T`` hash lives in the timing-context reserved slots, so at
    ``T == 0`` the timing cache keys are byte-identical to their pre-feature values. These frozen
    tuples lock that existing zero_ms / perfect_window cache keys (and therefore cached scores) are
    unchanged -- if a future edit leaks a non-empty hash at ``T == 0``, this fails."""
    cs_zero = _calc_song()
    apply_timing_envelope(cs_zero, mode="zero_ms")
    assert timing_envelope_timing_context(cs_zero) == ("TIMING_ENVELOPE", "zero_ms", "", 0)
    assert timing_envelope_full_context(cs_zero) == ("TIMING_ENVELOPE", "zero_ms", "none", 0)

    cs_pw = _calc_song()
    apply_timing_envelope(cs_pw, mode="perfect_window")
    assert timing_envelope_timing_context(cs_pw) == ("TIMING_ENVELOPE", "perfect_window", "", 0)
    assert timing_envelope_full_context(cs_pw) == ("TIMING_ENVELOPE", "perfect_window", "late_upper", 0)
