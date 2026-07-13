"""Exact physical replay guard for persisted Perfect-window FG witnesses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ..taichi_gem.force_greats.response_types import FgResponseSurface
from .note_graph import force_greats_note_graph, reconcile_force_greats_note_graph

_TAP_EDGES = (430.0, 190.0, 40.0, -20.0, -95.0, -235.0)
_HELD_TAIL_TYPE = 3


@dataclass(frozen=True, slots=True)
class FgPhysicalReplay:
    event_order: tuple[int, ...]
    fever_mask: tuple[bool, ...]
    judgments: tuple[str, ...]


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

    event_times_ms = np.empty(n, dtype=np.float64)
    judgments: list[str] = []
    for index, note in enumerate(graph):
        delta = note.get("delta_ms")
        if delta is None:
            raise ValueError(f"FG physical replay note {index} has no canonical timing witness")
        expected = str(note.get("note_result", ""))
        actual = _judgment_at(float(delta), held_tail=int(nt[index]) == _HELD_TAIL_TYPE)
        if actual != expected:
            raise ValueError(
                f"FG physical replay note {index} judges {actual}, expected {expected} "
                f"at {float(delta):.6f}ms"
            )
        event_times_ms[index] = float(note["hit_time_ms"]) + float(delta)
        judgments.append(expected)

    input_orders = tuple(int(note.get("input_order", -1)) for note in graph)
    if tuple(sorted(input_orders)) != tuple(range(n)):
        raise ValueError("FG physical replay graph does not contain one exact input order")
    event_order = tuple(int(index) for index in sorted(range(n), key=input_orders.__getitem__))

    expected_by_lane: dict[int, list[int]] = {}
    for index, lane_value in enumerate(lane_arr):
        expected_by_lane.setdefault(int(lane_value), []).append(int(index))
    lane_cursors = {lane: 0 for lane in expected_by_lane}
    for index in event_order:
        lane = int(lane_arr[index])
        cursor = int(lane_cursors[lane])
        expected_index = int(expected_by_lane[lane][cursor])
        if int(index) != int(expected_index):
            raise ValueError(
                f"FG physical replay lane {lane} matched note {expected_index}, not intended note {index}"
            )
        lane_cursors[lane] = int(cursor) + 1

    replay_fever = _event_time_fever_mask(
        event_order=event_order,
        event_times_ms=event_times_ms,
        judgments=judgments,
        fever_fill_denom=float(raw_fever_fill),
        fever_time_seconds=float(real_fever_time),
    )
    expected_fever = tuple(bool(note.get("fever")) for note in graph)
    if replay_fever != expected_fever:
        mismatch = next(
            index
            for index, (actual, expected) in enumerate(
                zip(replay_fever, expected_fever, strict=True)
            )
            if actual != expected
        )
        raise ValueError(
            "FG physical replay fever membership disagrees with the response surface at note "
            f"{mismatch}: replay={replay_fever[mismatch]}, surface={expected_fever[mismatch]}"
        )

    return FgPhysicalReplay(
        event_order=event_order,
        fever_mask=replay_fever,
        judgments=tuple(judgments),
    )
