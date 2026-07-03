"""Unit coverage for the fever-exit push-out witness (`_mark_fever_exit_push_delta`).

The BASE/FG note graph must push the FIRST NON-FEVER note at a fever-end boundary to its latest
legal Perfect hit when the replay's drain would otherwise reclaim it into fever -- the mirror of the
claw-IN-early endpoint logic. These tests drive `timeline_frontier_note_graph` directly (pure Python,
no GPU) so the behavior is pinned independently of the WebPort replay fixture. CPU-only, deterministic.
"""

import numpy as np

from gear_optimizer.solver.fg_response_scoring.note_graph import timeline_frontier_note_graph


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
        timing_mode="perfect_window",
    )


def test_exit_note_reclaimed_at_chart_time_is_pushed_to_perfect_hi():
    # Exit note 5 chart = 500 ms; cutoff 520 ms -> at d=0 the drain reclaims it (500 < 520).
    # Push to its latest legal Perfect hit (+40) so hit 540 >= cutoff -> stays out.
    notes = _graph([1] * 10, cutoff_ms=520.0)
    assert notes[5]["delta_ms"] == 40.0
    assert notes[5]["fever"] is False
    # Notes 2,3,4 are the fever run (comfortably inside the cutoff) -> untouched.
    assert [notes[i]["fever"] for i in (2, 3, 4)] == [True, True, True]
    assert notes[4]["delta_ms"] == 0.0
    # Note 6 is past the cutoff already (600 >= 520) -> not touched, and the scan stops there.
    assert notes[6]["delta_ms"] == 0.0


def test_exit_note_already_past_cutoff_stays_zero():
    # Exit note 5 chart = 500 ms; cutoff 450 ms -> the drain already excludes it at d=0. No push.
    notes = _graph([1] * 10, cutoff_ms=450.0)
    assert notes[5]["delta_ms"] == 0.0


def test_held_tail_exit_note_uses_the_wider_bound():
    # A held tail (note_type == 3) has a x2 Perfect window, so its latest legal hit is +80, not +40.
    note_types = [1] * 10
    note_types[5] = 3
    notes = _graph(note_types, cutoff_ms=560.0)  # 500 < 560 <= 500+80 -> pushable only via the wide bound
    assert notes[5]["delta_ms"] == 80.0


def test_a_cluster_of_reclaimed_exit_notes_is_all_pushed():
    # Two same-region non-fever notes both before the cutoff must BOTH be pushed, else the replay
    # reclaims the second. Notes 5 (500) and 6 (600) both < cutoff 640; note 7 (700) is past it.
    notes = _graph([1] * 12, cutoff_ms=640.0, fever_end_index=5)
    assert notes[5]["delta_ms"] == 40.0
    assert notes[6]["delta_ms"] == 40.0
    assert notes[7]["delta_ms"] == 0.0


def test_fever_run_to_end_of_song_has_no_exit_note():
    # fever_end_index == n: fever runs to the last note, so there is no note to push. No crash, no push.
    n = 8
    timestamps = (np.arange(n) * 0.1).astype(np.float32)
    notes = timeline_frontier_note_graph(
        frontier_trace=_trace(2, n, 5000.0),
        total_notes=n,
        timestamps=timestamps,
        note_types=np.ones(n, dtype=np.int16),
        timing_mode="perfect_window",
    )
    assert all(note["delta_ms"] in (0.0, None) for note in notes)


def test_zero_ms_mode_never_pushes():
    # zero_ms ships every hit at chart time; the exit push (like every witness offset) must not apply.
    n = 10
    timestamps = (np.arange(n) * 0.1).astype(np.float32)
    notes = timeline_frontier_note_graph(
        frontier_trace=_trace(2, 5, 520.0),
        total_notes=n,
        timestamps=timestamps,
        note_types=np.ones(n, dtype=np.int16),
        timing_mode="zero_ms",
    )
    assert notes[5]["delta_ms"] == 0.0
