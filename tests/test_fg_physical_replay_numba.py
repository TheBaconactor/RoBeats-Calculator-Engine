"""Bit-exactness guards for the numba-fied FG physical-replay pass.

``validate_force_greats_physical_replay`` used to run its per-note judgment check, event-time
accumulation, lane-cursor scan and event-time fever replay in Python. Those loops now live in
``_force_greats_replay_kernel`` (numba, nogil). These tests pin the kernel to a Python golden
reference built from the *original* helper functions (``_judgment_at`` / ``_event_time_fever_mask``
are still the Base-path implementations), and pin the wrapper's fail-loud messages byte-for-byte.
"""

from __future__ import annotations

import random

import numpy as np
import pytest

from gear_optimizer.solver.fg_response_scoring import physical_replay as pr
from gear_optimizer.solver.fg_response_scoring.physical_replay import (
    _GREAT_CODE,
    _HELD_TAIL_TYPE,
    _JUDGMENT_NAME,
    _REPLAY_ERR_BACKWARD_TIME,
    _REPLAY_ERR_FEVER_DURATION,
    _REPLAY_ERR_FEVER_MEMBERSHIP,
    _REPLAY_ERR_FILL_DENOM,
    _REPLAY_ERR_INPUT_ORDER,
    _REPLAY_ERR_JUDGMENT,
    _REPLAY_ERR_LANE,
    _REPLAY_OK,
    _RESULT_CODE,
    _event_time_fever_mask,
    _force_greats_replay_kernel,
    _judgment_at,
    _judgment_code,
    validate_force_greats_physical_replay,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface


def _reference(
    delta_ms,
    hit_time_ms,
    input_order,
    expected_code,
    expected_fever,
    note_types,
    lanes,
    denom,
    duration,
):
    """Golden port of the *original* wrapper body, returning a status instead of raising."""
    n = len(delta_ms)
    event_times = np.empty(n, dtype=np.float64)
    for i in range(n):
        actual = _judgment_at(float(delta_ms[i]), held_tail=int(note_types[i]) == _HELD_TAIL_TYPE)
        if _RESULT_CODE[actual] != int(expected_code[i]):
            return (_REPLAY_ERR_JUDGMENT, i, _RESULT_CODE[actual], None, None)
        event_times[i] = float(hit_time_ms[i]) + float(delta_ms[i])

    input_orders = tuple(int(v) for v in input_order)
    if tuple(sorted(input_orders)) != tuple(range(n)):
        return (_REPLAY_ERR_INPUT_ORDER, -1, -1, None, None)
    event_order = tuple(int(idx) for idx in sorted(range(n), key=input_orders.__getitem__))

    expected_by_lane: dict[int, list[int]] = {}
    for idx, lane in enumerate(lanes):
        expected_by_lane.setdefault(int(lane), []).append(int(idx))
    lane_cursors = {lane: 0 for lane in expected_by_lane}
    for idx in event_order:
        lane = int(lanes[idx])
        cur = lane_cursors[lane]
        exp = expected_by_lane[lane][cur]
        if idx != exp:
            return (_REPLAY_ERR_LANE, idx, exp, None, None)
        lane_cursors[lane] = cur + 1

    judgments = ["Great" if int(expected_code[i]) == _GREAT_CODE else "Perfect" for i in range(n)]
    try:
        replay = _event_time_fever_mask(
            event_order=event_order,
            event_times_ms=event_times,
            judgments=judgments,
            fever_fill_denom=float(denom),
            fever_time_seconds=float(duration),
        )
    except ValueError as exc:
        msg = str(exc)
        if "fever-fill denominator" in msg:
            return (_REPLAY_ERR_FILL_DENOM, -1, -1, None, None)
        if "fever duration" in msg:
            return (_REPLAY_ERR_FEVER_DURATION, -1, -1, None, None)
        if "moved backward" in msg:
            return (_REPLAY_ERR_BACKWARD_TIME, -1, -1, None, None)
        raise

    for i in range(n):
        if bool(replay[i]) != bool(int(expected_fever[i])):
            return (_REPLAY_ERR_FEVER_MEMBERSHIP, i, -1, event_order, tuple(bool(x) for x in replay))
    return (_REPLAY_OK, -1, -1, event_order, tuple(bool(x) for x in replay))


def _run_kernel(delta_ms, hit_time_ms, input_order, expected_code, expected_fever, note_types, lanes, denom, duration):
    n = len(delta_ms)
    event_order = np.empty(n, dtype=np.int64)
    replay_fever = np.empty(n, dtype=np.int8)
    status, a, b = _force_greats_replay_kernel(
        np.asarray(delta_ms, dtype=np.float64),
        np.asarray(hit_time_ms, dtype=np.float64),
        np.asarray(input_order, dtype=np.int64),
        np.asarray(expected_code, dtype=np.int8),
        np.asarray(expected_fever, dtype=np.int8),
        np.asarray(note_types, dtype=np.int32),
        np.asarray(lanes, dtype=np.int32),
        float(denom),
        float(duration),
        event_order,
        replay_fever,
    )
    return int(status), int(a), int(b), event_order, replay_fever


def _assert_agrees(case):
    ref = _reference(*case)
    k_status, k_a, k_b, k_event, k_fever = _run_kernel(*case)
    r_status, r_a, r_b, r_event, r_fever = ref
    assert k_status == r_status, f"status mismatch: kernel={k_status} ref={r_status}"
    assert (k_a, k_b) == (r_a, r_b), f"args mismatch: kernel={(k_a, k_b)} ref={(r_a, r_b)}"
    if r_event is not None:
        assert tuple(int(x) for x in k_event) == tuple(r_event)
        assert tuple(bool(x) for x in k_fever) == tuple(r_fever)


def _judgment_code_of(delta, held_tail):
    return _RESULT_CODE[_judgment_at(float(delta), held_tail=held_tail)]


def test_judgment_code_matches_python_across_all_window_edges():
    for held_tail in (False, True):
        for delta in np.arange(-500.0, 500.0, 0.5):
            assert int(_judgment_code(float(delta), held_tail)) == _judgment_code_of(delta, held_tail)


def test_kernel_matches_reference_distinct_lane_permutations():
    rng = random.Random(20260716)
    for _ in range(300):
        n = rng.randint(1, 40)
        note_types = [rng.choice([1, 1, 1, 2, _HELD_TAIL_TYPE]) for _ in range(n)]
        delta_ms = [rng.uniform(-500.0, 500.0) for _ in range(n)]
        expected_code = []
        for i in range(n):
            true_code = _judgment_code_of(delta_ms[i], note_types[i] == _HELD_TAIL_TYPE)
            # Mostly agree; sometimes inject a wrong expected code to exercise the judgment error.
            if rng.random() < 0.12:
                expected_code.append((true_code + 1) % 4)
            else:
                expected_code.append(true_code)
        lanes = list(range(n))  # distinct lanes => any permutation is lane-legal
        input_order = list(range(n))
        rng.shuffle(input_order)
        expected_fever = [rng.randint(0, 1) for _ in range(n)]
        denom = rng.choice([0.5, 1.0, 2.0, 3.5])
        duration = rng.choice([0.05, 0.2, 1.0, 50.0])
        hit_time_ms = sorted(rng.uniform(0.0, 5000.0) for _ in range(n))
        _assert_agrees(
            (delta_ms, hit_time_ms, input_order, expected_code, expected_fever, note_types, lanes, denom, duration)
        )


def test_kernel_matches_reference_shared_lanes_lane_legal():
    """Interleave per-lane ascending-index runs so the lane cursor scan passes with shared lanes."""
    rng = random.Random(777)
    for _ in range(300):
        n = rng.randint(2, 40)
        lanes = [rng.randint(0, 3) for _ in range(n)]
        # Build a lane-legal event order: repeatedly pop the smallest-remaining index of a random lane.
        remaining: dict[int, list[int]] = {}
        for idx, lane in enumerate(lanes):
            remaining.setdefault(lane, []).append(idx)
        event_order: list[int] = []
        while any(remaining.values()):
            lane = rng.choice([lane for lane, idxs in remaining.items() if idxs])
            event_order.append(remaining[lane].pop(0))
        input_order = [0] * n
        for pos, idx in enumerate(event_order):
            input_order[idx] = pos
        note_types = [rng.choice([1, 2, _HELD_TAIL_TYPE]) for _ in range(n)]
        delta_ms = [rng.uniform(-260.0, 460.0) for _ in range(n)]
        expected_code = [_judgment_code_of(delta_ms[i], note_types[i] == _HELD_TAIL_TYPE) for i in range(n)]
        expected_fever = [rng.randint(0, 1) for _ in range(n)]
        denom = rng.choice([0.5, 1.0, 2.0])
        duration = rng.choice([0.1, 1.0, 30.0])
        # Monotonic event times along event_order so we exercise the fever replay, not the backward guard.
        base = sorted(rng.uniform(0.0, 5000.0) for _ in range(n))
        hit_time_ms = [0.0] * n
        for pos, idx in enumerate(event_order):
            hit_time_ms[idx] = base[pos] - delta_ms[idx]
        _assert_agrees(
            (delta_ms, hit_time_ms, input_order, expected_code, expected_fever, note_types, lanes, denom, duration)
        )


def test_kernel_matches_reference_random_possibly_invalid_lanes():
    rng = random.Random(31337)
    for _ in range(300):
        n = rng.randint(1, 30)
        lanes = [rng.randint(0, 2) for _ in range(n)]
        input_order = list(range(n))
        rng.shuffle(input_order)
        note_types = [rng.choice([1, _HELD_TAIL_TYPE]) for _ in range(n)]
        delta_ms = [rng.uniform(-300.0, 500.0) for _ in range(n)]
        expected_code = [_judgment_code_of(delta_ms[i], note_types[i] == _HELD_TAIL_TYPE) for i in range(n)]
        expected_fever = [rng.randint(0, 1) for _ in range(n)]
        denom = rng.choice([1.0, 2.0])
        duration = rng.choice([0.2, 10.0])
        hit_time_ms = [rng.uniform(0.0, 5000.0) for _ in range(n)]
        _assert_agrees(
            (delta_ms, hit_time_ms, input_order, expected_code, expected_fever, note_types, lanes, denom, duration)
        )


def test_kernel_non_permutation_and_degenerate_inputs():
    # Empty traces retain the original no-op replay behavior.
    _assert_agrees(([], [], [], [], [], [], [], 1.0, 10.0))
    # Non-permutation input order (duplicate).
    _assert_agrees(([0.0, 0.0], [0.0, 1.0], [0, 0], [3, 3], [0, 0], [1, 1], [0, 1], 1.0, 10.0))
    # Out-of-range input order.
    _assert_agrees(([0.0, 0.0], [0.0, 1.0], [0, 5], [3, 3], [0, 0], [1, 1], [0, 1], 1.0, 10.0))
    # Invalid denom / duration.
    _assert_agrees(([0.0], [0.0], [0], [3], [1], [1], [0], 0.0, 10.0))
    _assert_agrees(([0.0], [0.0], [0], [3], [1], [1], [0], 1.0, 0.0))
    _assert_agrees(([0.0], [0.0], [0], [3], [1], [1], [0], float("nan"), 10.0))


# ----- wrapper-level fail-loud message parity via a synthetic (monkeypatched) note graph -----


def _install_graph(monkeypatch, graph):
    monkeypatch.setattr(pr, "force_greats_note_graph", lambda **_kwargs: graph)
    monkeypatch.setattr(pr, "reconcile_force_greats_note_graph", lambda *_a, **_k: None)


_DUMMY_SURFACE = FgResponseSurface(0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0)


def _call(graph, *, note_types, lanes, denom=1.0, duration=10.0):
    n = len(graph)
    return validate_force_greats_physical_replay(
        frontier_trace=[{}],
        surface=_DUMMY_SURFACE,
        timestamps=np.zeros(n, dtype=np.float64),
        note_types=np.asarray(note_types, dtype=np.int32),
        lanes=np.asarray(lanes, dtype=np.int32),
        raw_fever_fill=denom,
        real_fever_time=duration,
    )


def test_wrapper_happy_path_returns_exact_event_order_and_fever(monkeypatch):
    graph = [
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 0, "fever": True},
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 100.0, "input_order": 1, "fever": True},
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 200.0, "input_order": 2, "fever": True},
    ]
    _install_graph(monkeypatch, graph)
    replay = _call(graph, note_types=[1, 1, 1], lanes=[0, 1, 2], denom=1.0, duration=10.0)
    assert replay.event_order == (0, 1, 2)
    assert replay.judgments == ("Perfect", "Perfect", "Perfect")
    assert replay.fever_mask == (True, True, True)


def test_wrapper_judgment_mismatch_message(monkeypatch):
    graph = [
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 0, "fever": False},
        {"delta_ms": 0.0, "note_result": "Great", "hit_time_ms": 100.0, "input_order": 1, "fever": False},
    ]
    _install_graph(monkeypatch, graph)
    with pytest.raises(ValueError, match=r"FG physical replay note 1 judges Perfect, expected Great at 0\.000000ms"):
        _call(graph, note_types=[1, 1], lanes=[0, 1])


def test_wrapper_missing_delta_message(monkeypatch):
    graph = [
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 0, "fever": False},
        {"delta_ms": None, "note_result": "Perfect", "hit_time_ms": 100.0, "input_order": 1, "fever": False},
    ]
    _install_graph(monkeypatch, graph)
    with pytest.raises(ValueError, match=r"FG physical replay note 1 has no canonical timing witness"):
        _call(graph, note_types=[1, 1], lanes=[0, 1])


def test_wrapper_input_order_not_permutation_message(monkeypatch):
    graph = [
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 0, "fever": False},
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 100.0, "input_order": 0, "fever": False},
    ]
    _install_graph(monkeypatch, graph)
    with pytest.raises(ValueError, match=r"FG physical replay graph does not contain one exact input order"):
        _call(graph, note_types=[1, 1], lanes=[0, 1])


def test_wrapper_lane_order_message(monkeypatch):
    # Shared lane 0; input_order = [1, 0, 2] => event_order = [1, 0, 2], violating ascending index.
    graph = [
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 1, "fever": False},
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 100.0, "input_order": 0, "fever": False},
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 200.0, "input_order": 2, "fever": False},
    ]
    _install_graph(monkeypatch, graph)
    with pytest.raises(ValueError, match=r"FG physical replay lane 0 matched note 0, not intended note 1"):
        _call(graph, note_types=[1, 1, 1], lanes=[0, 0, 0])


def test_wrapper_fill_denominator_message(monkeypatch):
    graph = [{"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 0, "fever": False}]
    _install_graph(monkeypatch, graph)
    with pytest.raises(ValueError, match=r"FG physical replay requires a finite positive fever-fill denominator"):
        _call(graph, note_types=[1], lanes=[0], denom=0.0)


def test_wrapper_fever_duration_message(monkeypatch):
    graph = [{"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 0, "fever": False}]
    _install_graph(monkeypatch, graph)
    with pytest.raises(ValueError, match=r"FG physical replay requires a finite positive fever duration"):
        _call(graph, note_types=[1], lanes=[0], duration=0.0)


def test_wrapper_backward_time_message(monkeypatch):
    # Distinct lanes (lane scan passes); event times decrease along event_order.
    graph = [
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 200.0, "input_order": 0, "fever": False},
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 1, "fever": False},
    ]
    _install_graph(monkeypatch, graph)
    with pytest.raises(ValueError, match=r"FG physical replay event order moved backward in time"):
        _call(graph, note_types=[1, 1], lanes=[0, 1], denom=1.0, duration=10.0)


def test_wrapper_fever_membership_message(monkeypatch):
    # Replay makes note 0 fevered (denom=1.0); surface says False => mismatch at note 0.
    graph = [
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 0.0, "input_order": 0, "fever": False},
        {"delta_ms": 0.0, "note_result": "Perfect", "hit_time_ms": 100.0, "input_order": 1, "fever": True},
    ]
    _install_graph(monkeypatch, graph)
    with pytest.raises(
        ValueError,
        match=r"FG physical replay fever membership disagrees with the response surface at note 0: replay=True, surface=False",
    ):
        _call(graph, note_types=[1, 1], lanes=[0, 1], denom=1.0, duration=10.0)


def test_judgment_name_table_matches_result_code():
    for name, code in _RESULT_CODE.items():
        assert _JUDGMENT_NAME[code] == name
