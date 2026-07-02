"""Late-Great deliverability is capped by the engine's note removal, not the
classification window.

Decompiled Constants.lua:19 ``NOTE_REMOVE_TIME = -200``: an unhit note
time-misses once ``now - hit > 200`` ms — the SAME edge for taps
(Note.lua:191), hold heads, and the hold despawn (HeldNote.lua:219/231).
A held tail's late-Great CLASSIFICATION edge reaches +380 (2x (40+150)), but
any input scheduled past +200 races the per-frame sweep and is not guaranteed
to land on any frame rate. The planner must therefore never emit a late-Great
candidate beyond +200 (found live: an FG plan scheduled a +318ms tail
activation the game-port replay missed).
"""

from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.solver.timing_envelope import (
    NOTE_REMOVE_LATE_CAP_MS,
    build_great_candidate_envelope_sec,
    build_per_note_great_window_ms,
    build_per_note_perfect_window_ms,
)

TAP, HEAD, TAIL = 1, 2, 3


def _windows(note_types: list[int], *, great_mode: str, cap: int = NOTE_REMOVE_LATE_CAP_MS):
    nt = np.asarray(note_types, dtype=np.int16)
    perfect_low, _perfect_high = build_per_note_perfect_window_ms(
        nt, perfect_lower_ms=-20, perfect_upper_ms=40, held_tail_type=TAIL, held_tail_time_multiplier=2
    )
    return build_per_note_great_window_ms(
        nt,
        perfect_low_ms=perfect_low,
        perfect_upper_ms=40,
        great_lower_ms=-75,
        great_extra_upper_ms=150,
        great_mode=great_mode,
        held_tail_type=TAIL,
        held_tail_time_multiplier=2,
        late_removal_cap_ms=cap,
    )


def test_tap_late_great_edge_is_inside_the_removal_cap_and_unchanged() -> None:
    low, high = _windows([TAP], great_mode="late")
    assert int(low[0]) == 41
    assert int(high[0]) == 190  # 40 + 150, already deliverable (< 200)


def test_tail_late_great_edge_is_capped_at_note_removal() -> None:
    low, high = _windows([TAIL], great_mode="late")
    assert int(low[0]) == 81  # 40*2 + 1
    assert int(high[0]) == NOTE_REMOVE_LATE_CAP_MS  # was 380 = (40+150)*2


def test_full_mode_caps_only_the_late_edge() -> None:
    low, high = _windows([TAIL], great_mode="full")
    assert int(low[0]) == -190  # perfect_low(-40) + great_lower(-75)*2
    assert int(high[0]) == NOTE_REMOVE_LATE_CAP_MS


def test_early_mode_is_untouched_by_the_cap() -> None:
    low, high = _windows([TAIL], great_mode="early", cap=0)
    assert int(low[0]) == -190
    assert int(high[0]) == -41  # perfect_low(-40) - 1


def test_empty_late_window_fails_loud() -> None:
    with pytest.raises(ValueError, match="late-Great window empty"):
        _windows([TAIL], great_mode="late", cap=60)  # tail late-Great starts at 81


def test_great_candidate_envelope_emits_capped_tail_candidates() -> None:
    ts = np.asarray([1.0, 2.0, 3.0], dtype=np.float32)
    nt = [TAP, TAIL, HEAD]
    out = build_great_candidate_envelope_sec(ts, np.asarray(nt, dtype=np.int16), great_mode="late")
    deltas_ms = np.round((out - ts) * 1000.0).astype(int)
    assert int(deltas_ms[0]) == 190  # tap edge unchanged
    assert int(deltas_ms[1]) == NOTE_REMOVE_LATE_CAP_MS  # tail capped (was 380)
    assert int(deltas_ms[2]) == 190  # head = tap-width window
