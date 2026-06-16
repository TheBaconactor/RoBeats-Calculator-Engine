"""The Monte Carlo Perfect-timing sampler must only ever emit in-window hit offsets.

Regression for the same-timestamp chord-tied held-tail case: after the grouping split that
gives a held tail its own [-40,+80] group, the old fixed-order monotone carry could force a
co-timed narrower note's offset past its legal upper bound (reviewer repro: seed 0 -> [62, 62],
the [-20,+40] note illegally at +62). The decompiled server registers each lane's hit in its
OWN window with no forced-monotone coupling (ServerPlayerNoteSequenceInfo:push_note_sequence),
so the sampler now draws each group independently within its own window.
"""

import numpy as np

from gear_optimizer.solver.timing_envelope import (
    compute_fever_timeline_signature,
    generate_perfect_timing_events_ms,
    prepare_perfect_timing_envelope,
)

_PERFECT_LOWER_MS = -20
_PERFECT_UPPER_MS = 40
_HELD_TAIL_TYPE = 3
_HELD_TAIL_MULT = 2


def _prepare(timestamps_sec, note_types):
    return prepare_perfect_timing_envelope(
        np.asarray(timestamps_sec, dtype=np.float32),
        np.asarray(note_types, dtype=np.int16),
        perfect_lower_ms=_PERFECT_LOWER_MS,
        perfect_upper_ms=_PERFECT_UPPER_MS,
        held_tail_type=_HELD_TAIL_TYPE,
        held_tail_time_multiplier=_HELD_TAIL_MULT,
        quantize_ms=True,
    )


def _per_group_offsets(prepared, event_ms):
    starts = np.asarray(prepared["group_starts"], dtype=np.int64)
    base_t = np.asarray(prepared["group_base_t"], dtype=np.int64)
    return np.asarray(event_ms, dtype=np.int64)[starts] - base_t


def test_sampler_never_emits_out_of_window_offset_for_chord_tied_held_tail():
    prepared = _prepare([1.0, 1.0], [_HELD_TAIL_TYPE, 1])
    g_low = np.asarray(prepared["group_low"], dtype=np.int64)
    g_high = np.asarray(prepared["group_high"], dtype=np.int64)
    # held tail first ([-40,+80]), normal second ([-20,+40]) -- each its own split group
    assert list(g_low) == [-40, -20]
    assert list(g_high) == [80, 40]

    for seed in range(500):
        offs = _per_group_offsets(prepared, generate_perfect_timing_events_ms(prepared, seed=seed))
        assert np.all(offs >= g_low) and np.all(offs <= g_high), ("out-of-window", seed, offs.tolist())

    # The exact pre-fix failure seed (0) emitted [62, 62]; the [-20,+40] note must now be legal.
    off0 = _per_group_offsets(prepared, generate_perfect_timing_events_ms(prepared, seed=0))
    assert off0[1] <= 40


def test_sampler_legal_across_mixed_held_tail_chords():
    # A spread of co-timed chords, some with a held tail, some without, plus solo notes.
    timestamps = [0.0, 0.0, 0.5, 1.0, 1.0, 1.0, 2.0]
    note_types = [_HELD_TAIL_TYPE, 1, 1, _HELD_TAIL_TYPE, 1, 1, 1]
    prepared = _prepare(timestamps, note_types)
    g_low = np.asarray(prepared["group_low"], dtype=np.int64)
    g_high = np.asarray(prepared["group_high"], dtype=np.int64)
    for seed in range(300):
        offs = _per_group_offsets(prepared, generate_perfect_timing_events_ms(prepared, seed=seed))
        assert np.all(offs >= g_low) and np.all(offs <= g_high), ("out-of-window", seed, offs.tolist())


def test_fever_signature_uses_contiguous_first_exit_on_nonmonotone():
    # Independent lanes can make the event stream non-monotone, so the fever walk must take a
    # CONTIGUOUS first-exit, not a global searchsorted (which assumes a sorted array). Here the
    # fever section activates at note 1 (event 0, cutoff 50): note 2 (event 100) is past the cutoff
    # so the run EXITS there; note 3 (event 10) is numerically < 50 but sits AFTER the exit, so it
    # must NOT be pulled into fever. A sorted-array assumption could wrongly absorb it.
    ev = np.array([0, 0, 100, 10], dtype=np.int32)  # non-monotone: note3 (10) < note2 (100)
    _sig, mask, body_fever, _body_normal = compute_fever_timeline_signature(
        ev, non_fever_base=2, real_fever_time_ms=50
    )
    # note0 filled (non_fever_base-1=1); section activates at note1, contiguous run = {note1} only.
    assert mask.tolist() == [False, True, False, False]
    assert body_fever == 0  # only 4 notes, all in the head region


def test_sampler_reaches_full_held_tail_window_independently():
    # Independent lanes: the held tail must reach beyond the chord-narrow +-40-cap region,
    # proving the sampler is NOT collapsed to the chord intersection [-20,+40].
    prepared = _prepare([1.0, 1.0], [_HELD_TAIL_TYPE, 1])
    held = np.array(
        [_per_group_offsets(prepared, generate_perfect_timing_events_ms(prepared, seed=s))[0] for s in range(500)]
    )
    assert held.max() > 40   # reaches the held tail's exclusive [+41,+80] band
    assert held.min() < -20  # reaches the held tail's exclusive [-40,-21] band
