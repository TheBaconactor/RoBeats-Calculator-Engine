"""Exact physical replay guard for persisted Perfect-window FG witnesses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numba import njit

from ..taichi_gem.force_greats.response_types import FgResponseSurface
from .note_graph import (
    force_greats_note_graph,
    reconcile_base_note_graph,
    reconcile_force_greats_note_graph,
    timeline_frontier_note_graph,
)

_TAP_EDGES = (430.0, 190.0, 40.0, -20.0, -95.0, -235.0)
_HELD_TAIL_TYPE = 3


@dataclass(frozen=True, slots=True)
class FgPhysicalReplay:
    event_order: tuple[int, ...]
    fever_mask: tuple[bool, ...]
    judgments: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BasePhysicalReplay:
    event_order: tuple[int, ...]
    fever_mask: tuple[bool, ...]


def _judgment_at(delta_ms: float, *, held_tail: bool) -> str:
    scale = 2.0 if held_tail else 1.0
    okay_late, great_late, perfect_late, perfect_early, great_early, okay_early = (
        edge * scale for edge in _TAP_EDGES
    )
    delta = float(delta_ms)
    if delta > okay_late:
        return "Miss"
    if delta > great_late:
        return "Okay"
    if delta > perfect_late:
        return "Great"
    if delta > perfect_early:
        return "Perfect"
    if delta > great_early:
        return "Great"
    if delta > okay_early:
        return "Okay"
    return "Miss"


def _event_time_fever_mask(
    *,
    event_order: Sequence[int],
    event_times_ms: np.ndarray,
    judgments: Sequence[str],
    fever_fill_denom: float,
    fever_time_seconds: float,
) -> tuple[bool, ...]:
    """Replay the decompiled server's event-time powerbar order.

    While fever is active, the current hit is applied to the old bar before elapsed verified event
    time is charged. The first event that drains the bar is therefore the one wasted post-fever hit:
    it is not fevered and does not refill. No independent frame or 1/60 term exists.
    """
    denom = float(fever_fill_denom)
    duration = float(fever_time_seconds)
    if not np.isfinite(denom) or denom <= 0.0:
        raise ValueError("FG physical replay requires a finite positive fever-fill denominator")
    if not np.isfinite(duration) or duration <= 0.0:
        raise ValueError("FG physical replay requires a finite positive fever duration")

    fever = [False] * len(judgments)
    fill = 0.0
    active = False
    active_elapsed_seconds = 0.0
    previous_event_ms: float | None = None
    for index in event_order:
        event_ms = float(event_times_ms[int(index)])
        if previous_event_ms is not None and event_ms < previous_event_ms:
            raise ValueError("FG physical replay event order moved backward in time")

        if active:
            if previous_event_ms is None:
                raise AssertionError("active fever requires a preceding activation event")
            active_elapsed_seconds += (event_ms - float(previous_event_ms)) / 1000.0
            if active_elapsed_seconds >= duration:
                active = False
                active_elapsed_seconds = 0.0
                fill = 0.0
        else:
            fill += 0.5 if str(judgments[int(index)]) == "Great" else 1.0
            if fill >= denom:
                active = True
                active_elapsed_seconds = 0.0
                fill = denom

        fever[int(index)] = bool(active)
        previous_event_ms = event_ms
    return tuple(bool(value) for value in fever)


def _base_graph_physical_replay(
    *,
    frontier_trace: Sequence[Mapping[str, object]],
    response_surface: Sequence[int] | None,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    fill_count: int,
    fever_duration_ms: float,
) -> tuple[list[dict[str, object]], BasePhysicalReplay]:
    """Build and replay one Base graph through the engine's physical input order."""
    ts = np.asarray(timestamps, dtype=np.float64).reshape(-1)
    nt = np.asarray(note_types, dtype=np.int32).reshape(-1)
    lane_arr = np.asarray(lanes, dtype=np.int32).reshape(-1)
    n = int(ts.shape[0])
    if n <= 0 or int(nt.shape[0]) != n or int(lane_arr.shape[0]) != n:
        raise ValueError("Base physical replay chart arrays must be non-empty and exactly aligned")
    if int(fill_count) <= 0 or not np.isfinite(float(fever_duration_ms)) or float(fever_duration_ms) <= 0.0:
        raise ValueError("Base physical replay requires positive fill count and fever duration")

    graph = timeline_frontier_note_graph(
        frontier_trace=frontier_trace,
        total_notes=n,
        timestamps=ts,
        note_types=nt,
        lanes=lane_arr,
        timing_mode="perfect_window",
    )
    if response_surface is not None:
        reconcile_base_note_graph(graph, total_notes=n, response_surface=response_surface)

    event_times_ms = np.empty(n, dtype=np.float64)
    input_orders: list[int] = []
    for index, note in enumerate(graph):
        delta = note.get("delta_ms")
        if delta is None:
            raise ValueError(f"Base physical replay note {index} has no canonical timing witness")
        actual = _judgment_at(float(delta), held_tail=int(nt[index]) == _HELD_TAIL_TYPE)
        if actual != "Perfect":
            raise ValueError(
                f"Base physical replay note {index} judges {actual} at {float(delta):.6f}ms"
            )
        event_times_ms[index] = float(note["hit_time_ms"]) + float(delta)
        input_orders.append(int(note.get("input_order", -1)))
    if tuple(sorted(input_orders)) != tuple(range(n)):
        raise ValueError("Base physical replay graph does not contain one exact input order")

    event_order = tuple(
        sorted(
            range(n),
            key=lambda index: (
                float(event_times_ms[index]),
                int(nt[index]) == _HELD_TAIL_TYPE,
                int(input_orders[index]),
            ),
        )
    )
    expected_by_lane: dict[int, list[int]] = {}
    for index, lane_value in enumerate(lane_arr):
        expected_by_lane.setdefault(int(lane_value), []).append(int(index))
    lane_cursors = {lane: 0 for lane in expected_by_lane}
    for index in event_order:
        lane = int(lane_arr[index])
        cursor = int(lane_cursors[lane])
        expected_index = int(expected_by_lane[lane][cursor])
        if int(index) != expected_index:
            raise ValueError(
                f"Base physical replay lane {lane} matched note {expected_index}, not intended note {index}"
            )
        lane_cursors[lane] = cursor + 1

    replay_fever = _event_time_fever_mask(
        event_order=event_order,
        event_times_ms=event_times_ms,
        judgments=("Perfect",) * n,
        fever_fill_denom=float(fill_count),
        fever_time_seconds=float(fever_duration_ms) / 1000.0,
    )
    if response_surface is not None:
        replay_graph = [
            dict(note, fever=bool(replay_fever[index])) for index, note in enumerate(graph)
        ]
        reconcile_base_note_graph(replay_graph, total_notes=n, response_surface=response_surface)
    return graph, BasePhysicalReplay(event_order=event_order, fever_mask=replay_fever)


def validate_base_physical_replay(
    *,
    frontier_trace: Sequence[Mapping[str, object]],
    response_surface: Sequence[int],
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    fill_count: int,
    fever_duration_ms: float,
) -> BasePhysicalReplay:
    """Fail loudly unless a persisted Base witness is already canonical and score-exact."""
    graph, replay = _base_graph_physical_replay(
        frontier_trace=frontier_trace,
        response_surface=response_surface,
        timestamps=timestamps,
        note_types=note_types,
        lanes=lanes,
        fill_count=fill_count,
        fever_duration_ms=fever_duration_ms,
    )
    expected_fever = tuple(bool(note["fever"]) for note in graph)
    if replay.fever_mask != expected_fever:
        mismatch = next(
            index
            for index, (actual, expected) in enumerate(
                zip(replay.fever_mask, expected_fever, strict=True)
            )
            if actual != expected
        )
        raise ValueError(
            "Base physical replay fever membership disagrees with its canonical trace at note "
            f"{mismatch}: replay={replay.fever_mask[mismatch]}, trace={expected_fever[mismatch]}"
        )
    return replay


# Judgment codes shared between the Python extract loop and the numba replay kernel.
_MISS_CODE = 0
_OKAY_CODE = 1
_GREAT_CODE = 2
_PERFECT_CODE = 3
_RESULT_CODE = {"Miss": _MISS_CODE, "Okay": _OKAY_CODE, "Great": _GREAT_CODE, "Perfect": _PERFECT_CODE}
_JUDGMENT_NAME = ("Miss", "Okay", "Great", "Perfect")

# Kernel status codes returned to the Python wrapper so it can raise the exact dynamic ValueError.
_REPLAY_OK = 0
_REPLAY_ERR_JUDGMENT = 1
_REPLAY_ERR_INPUT_ORDER = 2
_REPLAY_ERR_LANE = 3
_REPLAY_ERR_FEVER_MEMBERSHIP = 4
_REPLAY_ERR_BACKWARD_TIME = 5
_REPLAY_ERR_FILL_DENOM = 6
_REPLAY_ERR_FEVER_DURATION = 7


@njit(cache=True, nogil=True)
def _judgment_code(delta_ms, held_tail):
    """Numba twin of ``_judgment_at`` returning an integer judgment code."""
    scale = 2.0 if held_tail else 1.0
    okay_late = 430.0 * scale
    great_late = 190.0 * scale
    perfect_late = 40.0 * scale
    perfect_early = -20.0 * scale
    great_early = -95.0 * scale
    okay_early = -235.0 * scale
    if delta_ms > okay_late:
        return _MISS_CODE
    if delta_ms > great_late:
        return _OKAY_CODE
    if delta_ms > perfect_late:
        return _GREAT_CODE
    if delta_ms > perfect_early:
        return _PERFECT_CODE
    if delta_ms > great_early:
        return _GREAT_CODE
    if delta_ms > okay_early:
        return _OKAY_CODE
    return _MISS_CODE


@njit(cache=True, nogil=True)
def _force_greats_replay_kernel(
    delta_ms,
    hit_time_ms,
    input_order,
    expected_result_code,
    expected_fever,
    note_types,
    lanes,
    raw_fever_fill,
    real_fever_time,
    event_order,
    replay_fever,
):
    """One GIL-free pass: judge, order, lane-check, and fever-replay a persisted witness.

    Returns ``(status, arg_a, arg_b)``. On error the Python wrapper reconstructs the exact
    dynamic ValueError message from the status code and the two integer arguments; on success it
    reads the filled ``event_order`` and ``replay_fever`` output arrays.
    """
    n = delta_ms.shape[0]

    # Per-note judgment agreement plus event-time accumulation (was the :267-279 Python loop).
    event_times_ms = np.empty(n, dtype=np.float64)
    for i in range(n):
        actual = _judgment_code(delta_ms[i], note_types[i] == _HELD_TAIL_TYPE)
        if actual != expected_result_code[i]:
            return _REPLAY_ERR_JUDGMENT, i, actual
        event_times_ms[i] = hit_time_ms[i] + delta_ms[i]

    # input_order must be one exact permutation of range(n); event_order is its inverse.
    seen = np.zeros(n, dtype=np.int8)
    for i in range(n):
        v = input_order[i]
        if v < 0 or v >= n or seen[v] != 0:
            return _REPLAY_ERR_INPUT_ORDER, -1, -1
        seen[v] = 1
    for i in range(n):
        event_order[input_order[i]] = i

    # Lane-cursor scan: within each lane the event order must consume notes in ascending index
    # order (was the :281-298 dict/cursor scan). Lanes are offset to a dense [0, span) id space.
    if n > 0:
        lane_min = lanes[0]
        lane_max = lanes[0]
        for i in range(1, n):
            if lanes[i] < lane_min:
                lane_min = lanes[i]
            if lanes[i] > lane_max:
                lane_max = lanes[i]
        span = lane_max - lane_min + 1
        lane_offset = np.zeros(span + 1, dtype=np.int64)
        for i in range(n):
            lane_offset[lanes[i] - lane_min + 1] += 1
        for s in range(span):
            lane_offset[s + 1] += lane_offset[s]
        lane_members = np.empty(n, dtype=np.int64)
        fill_cursor = lane_offset[:span].copy()
        for i in range(n):
            li = lanes[i] - lane_min
            lane_members[fill_cursor[li]] = i
            fill_cursor[li] += 1
        lane_next = lane_offset[:span].copy()
        for pos in range(n):
            idx = event_order[pos]
            li = lanes[idx] - lane_min
            expected_index = lane_members[lane_next[li]]
            if idx != expected_index:
                return _REPLAY_ERR_LANE, idx, expected_index
            lane_next[li] += 1

    # Event-time fever replay (was ``_event_time_fever_mask`` at :300).
    if not np.isfinite(raw_fever_fill) or raw_fever_fill <= 0.0:
        return _REPLAY_ERR_FILL_DENOM, -1, -1
    if not np.isfinite(real_fever_time) or real_fever_time <= 0.0:
        return _REPLAY_ERR_FEVER_DURATION, -1, -1
    fill = 0.0
    active = False
    active_elapsed_seconds = 0.0
    has_prev = False
    previous_event_ms = 0.0
    for pos in range(n):
        idx = event_order[pos]
        event_ms = event_times_ms[idx]
        if has_prev and event_ms < previous_event_ms:
            return _REPLAY_ERR_BACKWARD_TIME, -1, -1
        if active:
            active_elapsed_seconds += (event_ms - previous_event_ms) / 1000.0
            if active_elapsed_seconds >= real_fever_time:
                active = False
                active_elapsed_seconds = 0.0
                fill = 0.0
        else:
            fill += 0.5 if expected_result_code[idx] == _GREAT_CODE else 1.0
            if fill >= raw_fever_fill:
                active = True
                active_elapsed_seconds = 0.0
                fill = raw_fever_fill
        replay_fever[idx] = 1 if active else 0
        has_prev = True
        previous_event_ms = event_ms

    # Fever membership must match the response surface note-for-note.
    for i in range(n):
        if replay_fever[i] != expected_fever[i]:
            return _REPLAY_ERR_FEVER_MEMBERSHIP, i, -1

    return _REPLAY_OK, -1, -1


def validate_force_greats_physical_replay(
    *,
    frontier_trace: Sequence[Mapping[str, object]],
    surface: FgResponseSurface,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    raw_fever_fill: float,
    real_fever_time: float,
) -> FgPhysicalReplay:
    """Fail loudly unless one persisted witness replays to its exact score-bearing surface."""
    ts = np.asarray(timestamps, dtype=np.float64).reshape(-1)
    nt = np.asarray(note_types, dtype=np.int32).reshape(-1)
    lane_arr = np.asarray(lanes, dtype=np.int32).reshape(-1)
    n = int(ts.shape[0])
    if n <= 0 or int(nt.shape[0]) != n or int(lane_arr.shape[0]) != n:
        raise ValueError("FG physical replay chart arrays must be non-empty and exactly aligned")

    graph = force_greats_note_graph(
        frontier_trace=frontier_trace,
        total_notes=n,
        timestamps=ts,
        note_types=nt,
        lanes=lane_arr,
        timing_mode="perfect_window",
    )
    reconcile_force_greats_note_graph(
        graph,
        total_notes=n,
        fever_words=(surface.fever0, surface.fever1, surface.fever2, surface.fever3),
        great_words=(surface.great0, surface.great1, surface.great2, surface.great3),
        body_fever=surface.body_fever,
        body_great=surface.body_great,
        body_fever_great=surface.body_fever_great,
    )

    # Extract the per-note witness fields the replay depends on into aligned arrays, then run one
    # GIL-free numba pass over them. The graph is a list of dicts owned by note_graph.py, so the
    # gather stays in Python; all per-note arithmetic (judgment, event-time, lane and fever replay)
    # moves into ``_force_greats_replay_kernel``.
    delta_ms = np.empty(n, dtype=np.float64)
    hit_time_ms = np.empty(n, dtype=np.float64)
    input_order = np.empty(n, dtype=np.int64)
    expected_result_code = np.empty(n, dtype=np.int8)
    expected_fever = np.empty(n, dtype=np.int8)
    judgments: list[str] = []
    for index, note in enumerate(graph):
        delta = note.get("delta_ms")
        if delta is None:
            raise ValueError(f"FG physical replay note {index} has no canonical timing witness")
        expected = str(note.get("note_result", ""))
        judgments.append(expected)
        delta_ms[index] = float(delta)
        hit_time_ms[index] = float(note["hit_time_ms"])
        input_order[index] = int(note.get("input_order", -1))
        expected_result_code[index] = _RESULT_CODE.get(expected, -1)
        expected_fever[index] = 1 if note.get("fever") else 0

    event_order_arr = np.empty(n, dtype=np.int64)
    replay_fever_arr = np.empty(n, dtype=np.int8)
    status, arg_a, arg_b = _force_greats_replay_kernel(
        delta_ms,
        hit_time_ms,
        input_order,
        expected_result_code,
        expected_fever,
        nt,
        lane_arr,
        float(raw_fever_fill),
        float(real_fever_time),
        event_order_arr,
        replay_fever_arr,
    )

    if status == _REPLAY_ERR_JUDGMENT:
        i = int(arg_a)
        raise ValueError(
            f"FG physical replay note {i} judges {_JUDGMENT_NAME[int(arg_b)]}, expected {judgments[i]} "
            f"at {float(delta_ms[i]):.6f}ms"
        )
    if status == _REPLAY_ERR_INPUT_ORDER:
        raise ValueError("FG physical replay graph does not contain one exact input order")
    if status == _REPLAY_ERR_LANE:
        raise ValueError(
            f"FG physical replay lane {int(lane_arr[int(arg_a)])} matched note {int(arg_b)}, "
            f"not intended note {int(arg_a)}"
        )
    if status == _REPLAY_ERR_FILL_DENOM:
        raise ValueError("FG physical replay requires a finite positive fever-fill denominator")
    if status == _REPLAY_ERR_FEVER_DURATION:
        raise ValueError("FG physical replay requires a finite positive fever duration")
    if status == _REPLAY_ERR_BACKWARD_TIME:
        raise ValueError("FG physical replay event order moved backward in time")
    if status == _REPLAY_ERR_FEVER_MEMBERSHIP:
        mismatch = int(arg_a)
        raise ValueError(
            "FG physical replay fever membership disagrees with the response surface at note "
            f"{mismatch}: replay={bool(replay_fever_arr[mismatch])}, surface={bool(expected_fever[mismatch])}"
        )
    if status != _REPLAY_OK:
        raise AssertionError(f"FG physical replay kernel returned unknown status {status}")

    return FgPhysicalReplay(
        event_order=tuple(int(index) for index in event_order_arr),
        fever_mask=tuple(bool(value) for value in replay_fever_arr),
        judgments=tuple(judgments),
    )
