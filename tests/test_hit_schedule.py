"""The hit schedule through the plans: what a plan keeps, the room each input gets, and the plans no frame timing plays."""

import numpy as np
import pytest

from gear_optimizer.solver.timing_envelope import FRAME_MARGIN_MS
from gear_optimizer.trace.hit_schedule import input_order, warm
from gear_optimizer.trace.reconstruct import UnplayableTrace
from tests.trace_support import force_greats_note_graph


_FASTEST_FRAME_MS = 1000.0 / 360.0


def _press(note):
    return note["hit_time_ms"] + note["delta_ms"]


def _section(activation, fever_end, cutoff_ms, **fields):
    return {"section": 1, "activation_index": activation, "fever_end_index": fever_end, "forced_start_index": 0,
            "forced_run_start_index": 0, "forced_run_count": 0, "activation_judgment": "perfect",
            "activation_hit_offset_ms": 0.0, "fever_window_end_ms": cutoff_ms, **fields}


def _plan(times_ms, lanes, trace, *, note_types=None, timing_mode="precise"):
    n = len(times_ms)
    return force_greats_note_graph(
        frontier_trace=trace, total_notes=n, timestamps=np.asarray(times_ms, dtype=np.float64) / 1000.0,
        note_types=np.ones(n, dtype=np.int16) if note_types is None else np.asarray(note_types, dtype=np.int16),
        lanes=np.asarray(lanes, dtype=np.int32), timing_mode=timing_mode,
    )


def _late_activation_chord(follower_ms, last_fever_ms):
    """A late-Great activation on lane 4 with a forced Great of its chord on lane 3, the next Perfect of lane 3 at
    `follower_ms`, and a last fever note that holds the activation late: the window lasts 8,000 ms."""
    times = [0, 500, 1000, 1000, follower_ms, 1400, last_fever_ms, 12000, 12500]
    lanes = [1, 2, 4, 3, 3, 1, 2, 1, 2]
    trace = [_section(2, 7, 9000.0 + 1000.0 + 149.0, forced_run_start_index=2, forced_run_count=2,
                      activation_judgment="late_great", activation_hit_offset_ms=149.0, fever_duration_ms=8000.0)]
    return times, lanes, trace


def test_a_tie_on_one_lane_shares_the_room_its_bands_leave():
    # The activation lands no earlier than 1,132 for the last fever note, and the next Perfect of lane 3 no later than
    # 1,150: the Great before it and that Perfect share those 18 ms.
    times, lanes, trace = _late_activation_chord(1110, 9150)
    graph = _plan(times, lanes, trace)

    great, perfect = graph[3], graph[4]
    assert great["input_order"] < perfect["input_order"]
    assert _press(perfect) - _press(great) >= _FASTEST_FRAME_MS
    assert 1150.0 - _press(perfect) >= _FASTEST_FRAME_MS


def test_inputs_with_no_frame_of_their_own_have_no_plan():
    # The same, with 1 ms between the activation's earliest hit and the Perfect's latest.
    times, lanes, trace = _late_activation_chord(1110, 9167)
    with pytest.raises(UnplayableTrace, match="no frame of its own"):
        _plan(times, lanes, trace)


def test_a_pair_just_a_fastest_frame_apart_has_a_plan():
    times, lanes, trace = _late_activation_chord(1110, 9165)
    graph = _plan(times, lanes, trace)
    assert _press(graph[4]) > _press(graph[3])


def test_one_tight_place_costs_only_its_own_inputs():
    # Notes 2 and 3 share lane 3 far from the tight chord: they are 20 ms apart and keep a frame margin.
    times, lanes, trace = _late_activation_chord(1110, 9150)
    times = [0, 500, *times[2:6], 5000, 5020, *times[6:]]
    lanes = [1, 2, *lanes[2:6], 3, 3, *lanes[6:]]
    trace[0]["fever_end_index"] += 2
    graph = _plan(times, lanes, trace)

    assert _press(graph[7]) - _press(graph[6]) >= FRAME_MARGIN_MS
    assert _press(graph[4]) - _press(graph[3]) < FRAME_MARGIN_MS


def test_a_window_keeps_a_frame_margin_on_both_sides_of_its_cutoff():
    # The window lasts 1,000 ms from note 1: note 2 at 1,950 stays in it, note 3 at 2,020 out.
    graph = _plan([0, 1000, 1950, 2020, 3000], [1, 2, 3, 4, 1], [_section(1, 3, 2000.0)])
    cutoff = graph[2]["fever_end_ms"]

    assert cutoff == _press(graph[1]) + 1000.0
    assert _press(graph[2]) <= cutoff - FRAME_MARGIN_MS + 1e-6
    assert _press(graph[3]) >= cutoff + FRAME_MARGIN_MS - 1e-6
    assert [note["fever"] for note in graph] == [False, True, True, False, False]


def test_an_on_time_activation_moves_only_as_far_as_its_window_needs():
    graph = _plan([0, 1000, 1950, 3000], [1, 2, 3, 4], [_section(1, 3, 2000.0)])
    assert graph[1]["delta_ms"] == 0.0


def test_a_great_goes_early_when_its_order_leaves_it_no_late_hit():
    # Through the ramp a chord keeps its chart order: the Great goes first, and a late hit would pass the Perfect's band.
    graph = _plan([0, 1000, 1000, 2000], [1, 2, 3, 4], [_section(3, 4, 3000.0, forced_run_start_index=1, forced_run_count=1)])

    assert graph[1]["delta_ms"] == pytest.approx(-20.0 - FRAME_MARGIN_MS)
    assert graph[2]["delta_ms"] == 0.0
    assert graph[1]["input_order"] < graph[2]["input_order"]


def test_non_precise_perfects_stay_on_time_and_a_tie_on_one_lane_has_no_plan():
    # A Great's first late hit lands on the next press of its lane, and the press before it leaves it no early hit.
    trace = [_section(4, 5, 2500.0, forced_run_start_index=1, forced_run_count=1)]
    with pytest.raises(UnplayableTrace, match="no frame of its own"):
        _plan([0, 10, 51, 1000, 1500], [1, 1, 1, 2, 3], trace, timing_mode="non-precise")


def test_non_precise_only_moves_greats():
    times = [0, 300, 395, 395, 1000, 1500]
    lanes, note_types = [1, 1, 1, 2, 3, 4], [2, 3, 1, 1, 1, 1]
    trace = [_section(5, 6, 2500.0, forced_run_start_index=1, forced_run_count=2)]
    graph = _plan(times, lanes, trace, note_types=note_types, timing_mode="non-precise")

    assert [note["delta_ms"] for note in graph if note["note_result"] == "Perfect"] == [0.0] * 4
    assert [note["input_order"] for note in graph] == sorted(note["input_order"] for note in graph)


def test_plans_use_the_games_whole_ms_chart_times():
    # float32 seconds carry noise that could invert the tie: chart times come back whole.
    seconds = np.asarray([0.095, 104.363, 104.363], dtype=np.float32)
    graph = force_greats_note_graph(
        frontier_trace=[_section(1, 3, 200000.0)], total_notes=3, timestamps=seconds,
        note_types=np.ones(3, dtype=np.int16), lanes=np.asarray([1, 2, 3], dtype=np.int32),
    )
    assert [note["hit_time_ms"] for note in graph] == [95.0, 104363.0, 104363.0]


def _order(lanes, ranks, links=()):
    pairs = np.asarray(links, dtype=np.int64).reshape(-1, 2)
    return input_order(np.asarray(lanes, dtype=np.int64), np.asarray(ranks, dtype=np.int64), pairs[:, 0], pairs[:, 1]).tolist()


def test_input_order_merges_the_lanes_by_rank():
    assert _order([1, 2, 1, 2], [0, 3, 1, 2]) == [0, 2, 1, 3]


def test_input_order_keeps_a_lanes_chart_order_whatever_the_rank():
    assert _order([1, 1, 2], [2, 0, 1]) == [2, 0, 1]


def test_input_order_holds_a_note_for_its_link():
    assert _order([1, 2, 3], [0, 1, 2], [(2, 0)]) == [1, 2, 0]


def test_input_order_of_contradictory_links_is_empty():
    assert _order([1, 2], [0, 1], [(0, 1), (1, 0)]) == []


def test_warm_runs_the_kernels():
    warm()
