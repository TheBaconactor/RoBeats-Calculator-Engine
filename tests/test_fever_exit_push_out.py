"""The first non-fever note at a fever end: the plan keeps it past the cutoff, the mirror of a fever note clawed in early.
These tests drive `timeline_frontier_note_graph` directly (no GPU). CPU-only, deterministic.
"""

import numpy as np
import pytest

from gear_optimizer.solver.timing_envelope import FRAME_MARGIN_MS
from gear_optimizer.trace.reconstruct import UnplayableTrace
from tests.trace_support import timeline_frontier_note_graph


def _trace(activation_index, fever_end_index, cutoff_ms, *, section=1):
    # fever_start_note_index == activation_index (no chorded-held-tail witness split here);
    # activation_hit_offset_ms is required by the builder and irrelevant to the exit push.
    return [{
        "section": section,
        "activation_index": int(activation_index),
        "fever_end_index": int(fever_end_index),
        "fever_start_note_index": int(activation_index),
        "activation_hit_offset_ms": 0.0,
        "fever_window_end_ms": float(cutoff_ms),
    }]


def _graph(note_types, cutoff_ms, activation_index=2, fever_end_index=5):
    n = int(len(note_types))
    timestamps = (np.arange(n) * 0.1).astype(np.float32)  # 0,100,200,... ms
    return timeline_frontier_note_graph(
        frontier_trace=_trace(activation_index, fever_end_index, cutoff_ms),
        total_notes=n,
        timestamps=timestamps,
        note_types=np.asarray(note_types, dtype=np.int16),
        timing_mode="precise",
        perfect_time=0,
    )


def _press(note):
    return note["hit_time_ms"] + note["delta_ms"]


def test_exit_note_reclaimed_at_chart_time_stays_a_frame_margin_past_the_cutoff():
    # Exit note 5 chart = 500 ms; cutoff 520 ms -> at d=0 the drain reclaims it (500 < 520). The window lasts 320 ms
    # from the activation, which moves up in its band so that both stay under their bands' frame-safe tops.
    notes = _graph([1] * 10, cutoff_ms=520.0)
    assert _press(notes[5]) >= _press(notes[2]) + 320.0 + FRAME_MARGIN_MS - 1e-3
    assert notes[5]["delta_ms"] <= 40.0 - FRAME_MARGIN_MS + 1e-9
    assert notes[5]["fever"] is False
    # Notes 2,3,4 are the fever run (comfortably inside the cutoff) -> untouched.
    assert [notes[i]["fever"] for i in (2, 3, 4)] == [True, True, True]
    assert notes[4]["delta_ms"] == 0.0
    # Note 6 is past the cutoff already (600 >= 520) -> not touched, and the scan stops there.
    assert notes[6]["delta_ms"] == 0.0


def test_exit_note_with_a_frame_of_room_is_planned_frame_safe():
    # Exit note 5 chart = 500 ms with a cutoff of 501 ms: it stays under the latest Perfect every frame timing judges and
    # a frame margin past the window.
    notes = _graph([1] * 10, cutoff_ms=501.0)
    assert notes[5]["delta_ms"] <= 40.0 - FRAME_MARGIN_MS
    assert _press(notes[5]) >= _press(notes[2]) + 301.0 + FRAME_MARGIN_MS - 1e-3
    assert notes[5]["fever"] is False


def test_exit_note_already_past_cutoff_stays_zero():
    # Exit note 5 chart = 500 ms; cutoff 450 ms -> the drain already excludes it at d=0. No push.
    notes = _graph([1] * 10, cutoff_ms=450.0)
    assert notes[5]["delta_ms"] == 0.0


def test_held_tail_exit_note_uses_the_wider_bound():
    # A held tail (note_type == 3) has a x2 Perfect window, so its latest legal hit is +80, not +40.
    note_types = [1] * 10
    note_types[5] = 3
    notes = _graph(note_types, cutoff_ms=560.0)  # 500 < 560 <= 500+80 -> pushable only via the wide bound
    assert 40.0 < notes[5]["delta_ms"] <= 80.0 - FRAME_MARGIN_MS + 1e-9
    assert _press(notes[5]) >= _press(notes[2]) + 360.0


def test_a_window_whose_exit_note_lands_inside_it_has_no_plan():
    # Note 5 (500 ms) ends a window that lasts 440 ms from note 2 (200 ms): every Perfect of note 5 lands inside it.
    with pytest.raises(UnplayableTrace, match="no frame of its own"):
        _graph([1] * 12, cutoff_ms=640.0, fever_end_index=5)


def test_fever_run_to_end_of_song_has_no_exit_note():
    # fever_end_index == n: fever runs to the last note, so there is no note to push. No crash, no push.
    n = 8
    timestamps = (np.arange(n) * 0.1).astype(np.float32)
    notes = timeline_frontier_note_graph(
        frontier_trace=_trace(2, n, 5000.0),
        total_notes=n,
        timestamps=timestamps,
        note_types=np.ones(n, dtype=np.int16),
        timing_mode="precise",
        perfect_time=0,
    )
    assert all(note["delta_ms"] in (0.0, None) for note in notes)


def test_non_precise_mode_never_pushes():
    # non-precise ships every hit at chart time; the exit push (like every witness offset) must not apply.
    n = 10
    timestamps = (np.arange(n) * 0.1).astype(np.float32)
    notes = timeline_frontier_note_graph(
        frontier_trace=_trace(2, 5, 520.0),
        total_notes=n,
        timestamps=timestamps,
        note_types=np.ones(n, dtype=np.int16),
        timing_mode="non-precise",
        perfect_time=0,
    )
    assert notes[5]["delta_ms"] == 0.0
