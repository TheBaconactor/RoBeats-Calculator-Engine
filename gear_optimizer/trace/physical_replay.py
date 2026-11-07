"""Exact physical replay guard for stored plans, at the hit windows of the build's Perfect Time."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numba import njit

from gear_optimizer.score import HEAD_NOTES
from gear_optimizer.solver.timing_envelope import HELD_TAIL_TYPE, HELD_TAIL_WINDOW_SCALE, judgment_edges
from .reconstruct import UnplayableTrace
from gear_optimizer.frontier.types import FgResponseSurface
from .note_graph import (
    NotePlan,
    force_greats_plan,
    reconcile_base_plan,
    reconcile_force_greats_plan,
    timeline_frontier_plan,
)


@dataclass(frozen=True, slots=True)
class PhysicalReplay:
    event_order: tuple[int, ...]
    fever_mask: tuple[bool, ...]


def _note_edges(note_types: np.ndarray, perfect_time: int) -> np.ndarray:
    """Per note, its six judgment edges (a held tail's are twice as wide) at the build's Perfect Time."""
    tap = np.asarray(judgment_edges(perfect_time), dtype=np.float64)
    return np.where((note_types == HELD_TAIL_TYPE)[:, None], tap * HELD_TAIL_WINDOW_SCALE, tap)


# Judgment codes of the replay kernel.
_MISS_CODE = 0
_OKAY_CODE = 1
_GREAT_CODE = 2
_PERFECT_CODE = 3
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
_REPLAY_ERR_COMBO_ORDER = 8


@njit(cache=True, nogil=True)
def _judgment_code(delta_ms, edges):
    """The judgment of a hit at `delta_ms` on a note with these six edges (SPUtil.timedelta_to_result)."""
    if delta_ms > edges[0]:
        return _MISS_CODE
    if delta_ms > edges[1]:
        return _OKAY_CODE
    if delta_ms > edges[2]:
        return _GREAT_CODE
    if delta_ms > edges[3]:
        return _PERFECT_CODE
    if delta_ms > edges[4]:
        return _GREAT_CODE
    if delta_ms > edges[5]:
        return _OKAY_CODE
    return _MISS_CODE


@njit(cache=True, nogil=True)
def _fever_walk(event_order, event_times_ms, result_codes, fever_fill_denominator, fever_time_seconds, fever_out):
    """The game's event-time powerbar (PlayerScore) over the events in `event_order`; writes 1/0 per note into
    `fever_out` and returns _REPLAY_OK or the error status.

    A Perfect adds 1 / denominator to the float64 bar and a Great 1 / (2 x denominator); the bar is clamped to 1 and
    fever starts on the hit that fills it. While fever is active the current hit is applied to the old bar before the
    elapsed event time is charged, so the first event past the duration is the one wasted post-fever hit: outside
    fever, and it adds no fill. No frame or 1/60 term exists.
    """
    if not np.isfinite(fever_fill_denominator) or fever_fill_denominator <= 0.0:
        return _REPLAY_ERR_FILL_DENOM
    if not np.isfinite(fever_time_seconds) or fever_time_seconds <= 0.0:
        return _REPLAY_ERR_FEVER_DURATION
    perfect_fill = 1.0 / fever_fill_denominator
    great_fill = 1.0 / (2.0 * fever_fill_denominator)
    bar = 0.0
    active = False
    elapsed_seconds = 0.0
    previous_event_ms = 0.0
    for pos in range(event_order.shape[0]):
        idx = event_order[pos]
        event_ms = event_times_ms[idx]
        if pos > 0 and event_ms < previous_event_ms:
            return _REPLAY_ERR_BACKWARD_TIME
        if active:
            elapsed_seconds += (event_ms - previous_event_ms) / 1000.0
            if elapsed_seconds >= fever_time_seconds:
                active = False
                elapsed_seconds = 0.0
                bar = 0.0
        else:
            bar = min(bar + (great_fill if result_codes[idx] == _GREAT_CODE else perfect_fill), 1.0)
            if bar >= 1.0:
                active = True
                elapsed_seconds = 0.0
        fever_out[idx] = 1 if active else 0
        previous_event_ms = event_ms
    return _REPLAY_OK


@njit(cache=True, nogil=True)
def _replay_kernel(plan, edges, lanes, fever_fill_denominator, real_fever_time, replayed, check_combo_order):
    """One GIL-free pass over a plan: judge, order, lane-check and fever-replay it, and check its combo order.

    Returns ``(status, arg_a, arg_b)``; on success ``event_order`` and ``replay_fever`` are filled.
    """
    delta_ms, hit_time_ms, input_order, expected_result_code, expected_fever = plan
    event_order, replay_fever = replayed
    n = delta_ms.shape[0]

    # Per-note judgment agreement plus event-time accumulation.
    event_times_ms = np.empty(n, dtype=np.float64)
    for i in range(n):
        actual = _judgment_code(delta_ms[i], edges[i])
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
    # order. Lanes are offset to a dense [0, span) id space.
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

    status = _fever_walk(
        event_order, event_times_ms, expected_result_code, fever_fill_denominator, real_fever_time, replay_fever
    )
    if status != _REPLAY_OK:
        return status, -1, -1

    # Fever membership must match the response surface note-for-note.
    for i in range(n):
        if replay_fever[i] != expected_fever[i]:
            return _REPLAY_ERR_FEVER_MEMBERSHIP, i, -1

    # The k-th judged input scores at combo k; through the combo ramp it must carry the judgment and fever the
    # surface scores there (note k's).
    for pos in range(min(n, HEAD_NOTES) if check_combo_order else 0):
        idx = event_order[pos]
        if expected_result_code[idx] != expected_result_code[pos] or expected_fever[idx] != expected_fever[pos]:
            return _REPLAY_ERR_COMBO_ORDER, idx, pos

    return _REPLAY_OK, -1, -1


def _replay_plan(
    replay: str,
    plan: NotePlan,
    note_types: np.ndarray,
    lanes: np.ndarray,
    fever_fill_denominator: float,
    fever_seconds: float,
    perfect_time: int,
    *,
    check_combo_order: bool,
) -> PhysicalReplay:
    """Replay a plan through the kernel; returns its event order and fever, or raises what it found."""
    n = len(plan)
    delta_ms = plan.delta
    expected_fever = plan.fever.astype(np.int8)
    expected_code = np.where(plan.great, _GREAT_CODE, _PERFECT_CODE).astype(np.int8)
    event_order, replay_fever = np.empty(n, dtype=np.int64), np.empty(n, dtype=np.int8)
    status, arg_a, arg_b = _replay_kernel(
        (delta_ms, plan.hit_ms, plan.input_order, expected_code, expected_fever),
        _note_edges(note_types, perfect_time),
        lanes,
        float(fever_fill_denominator),
        float(fever_seconds),
        (event_order, replay_fever),
        check_combo_order,
    )
    if status == _REPLAY_ERR_JUDGMENT:
        # The frontier plans on the base windows: a build's Perfect Time can leave a hit in another band.
        raise UnplayableTrace(
            f"{replay} physical replay note {arg_a} judges {_JUDGMENT_NAME[arg_b]}, expected "
            f"{_JUDGMENT_NAME[expected_code[arg_a]]} at {delta_ms[arg_a]:.6f}ms"
        )
    if status == _REPLAY_ERR_INPUT_ORDER:
        raise ValueError(f"{replay} physical replay graph does not contain one exact input order")
    if status == _REPLAY_ERR_LANE:
        # The plan presses or releases a lane before that lane's earlier note is done: no player can play it.
        raise UnplayableTrace(
            f"{replay} physical replay lane {lanes[arg_a]} matched note {arg_b}, not intended note {arg_a}"
        )
    if status == _REPLAY_ERR_FILL_DENOM:
        raise ValueError(f"{replay} physical replay requires a finite positive fever-fill denominator")
    if status == _REPLAY_ERR_FEVER_DURATION:
        raise ValueError(f"{replay} physical replay requires a finite positive fever duration")
    if status == _REPLAY_ERR_BACKWARD_TIME:
        raise ValueError(f"{replay} physical replay event order moved backward in time")
    if status == _REPLAY_ERR_FEVER_MEMBERSHIP:
        # The plan's inputs fill and drain fever otherwise than the surface it scored: it is not playable as scored.
        raise UnplayableTrace(
            f"{replay} physical replay fever membership disagrees with the response surface at note "
            f"{arg_a}: replay={bool(replay_fever[arg_a])}, surface={bool(expected_fever[arg_a])}"
        )
    if status == _REPLAY_ERR_COMBO_ORDER:
        # The plan scores a note at a combo where the surface scores another judgment or fever: not playable as scored.
        raise UnplayableTrace(
            f"{replay} physical replay judges note {arg_a} at combo {arg_b + 1}, where the surface scores note "
            f"{arg_b}: {_JUDGMENT_NAME[expected_code[arg_a]]}/{'fever' if expected_fever[arg_a] else 'no fever'} instead of "
            f"{_JUDGMENT_NAME[expected_code[arg_b]]}/{'fever' if expected_fever[arg_b] else 'no fever'}"
        )
    if status != _REPLAY_OK:
        raise AssertionError(f"{replay} physical replay kernel returned unknown status {status}")
    return PhysicalReplay(tuple(event_order.tolist()), tuple(replay_fever.astype(bool).tolist()))


def validate_base_physical_replay(
    *,
    frontier_trace: Sequence[Mapping[str, object]],
    response_surface: Sequence[int],
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    fever_fill_denominator: float,
    fever_duration_ms: float,
    timing_mode: str,
    perfect_time: int,
) -> PhysicalReplay:
    """Fail loudly unless a persisted Base witness replays to its exact surface in `timing_mode`, at the build's windows."""
    nt, lane_arr = np.asarray(note_types, dtype=np.int32).reshape(-1), np.asarray(lanes, dtype=np.int32).reshape(-1)
    n = int(nt.shape[0])
    plan = timeline_frontier_plan(
        frontier_trace=frontier_trace,
        total_notes=n,
        timestamps=timestamps,
        note_types=nt,
        lanes=lane_arr,
        timing_mode=timing_mode,
        perfect_time=perfect_time,
    )
    reconcile_base_plan(plan, response_surface)
    return _replay_plan(
        "Base", plan, nt, lane_arr, fever_fill_denominator, fever_duration_ms / 1000.0, perfect_time, check_combo_order=False
    )


def validate_force_greats_physical_replay(
    *,
    frontier_trace: Sequence[Mapping[str, object]],
    surface: FgResponseSurface,
    timestamps: Sequence[float] | np.ndarray,
    note_types: Sequence[int] | np.ndarray,
    lanes: Sequence[int] | np.ndarray,
    fever_fill_denominator: float,
    real_fever_time: float,
    timing_mode: str,
    perfect_time: int,
) -> PhysicalReplay:
    """Fail loudly unless the mode's persisted witness replays to its exact score-bearing surface, at the build's windows."""
    nt, lane_arr = np.asarray(note_types, dtype=np.int32).reshape(-1), np.asarray(lanes, dtype=np.int32).reshape(-1)
    n = int(nt.shape[0])
    plan = force_greats_plan(
        frontier_trace=frontier_trace,
        total_notes=n,
        timestamps=timestamps,
        note_types=nt,
        lanes=lane_arr,
        timing_mode=timing_mode,
        perfect_time=perfect_time,
    )
    reconcile_force_greats_plan(
        plan,
        fever_words=(surface.fever0, surface.fever1, surface.fever2, surface.fever3),
        great_words=(surface.great0, surface.great1, surface.great2, surface.great3),
        body_fever=surface.body_fever,
        body_great=surface.body_great,
        body_fever_great=surface.body_fever_great,
    )
    return _replay_plan(
        "FG", plan, nt, lane_arr, fever_fill_denominator, real_fever_time, perfect_time, check_combo_order=True
    )
