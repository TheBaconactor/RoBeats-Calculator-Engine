from __future__ import annotations

from math import ceil
from typing import Any

import numpy as np

from .response_types import FgResponseFrontierResult, FgResponseSurface, _EMPTY_SURFACE


def _action_table(*, raw_fever_fill: float, non_fever_base: int, use_forced_great_timing: bool):
    actions: list[int] = []
    later_fill: list[int] = []
    first_fill: list[int] = []
    later_forced: list[int] = []
    first_forced: list[int] = []
    last_fill: int | None = None
    for k in range(max(0, int(non_fever_base)) + 1):
        fill = int(ceil(float(raw_fever_fill) + (float(k) * 0.5)))
        if bool(use_forced_great_timing) or last_fill is None or fill != last_fill:
            fill_first = max(0, fill - 1)
            actions.append(int(k))
            later_fill.append(int(fill))
            first_fill.append(int(fill_first))
            later_forced.append(min(int(k), int(fill)))
            first_forced.append(min(int(k), int(fill_first)))
        last_fill = int(fill)
    if not actions:
        actions.append(0)
        later_fill.append(0)
        first_fill.append(0)
        later_forced.append(0)
        first_forced.append(0)
    return actions, later_fill, first_fill, later_forced, first_forced


def _lower_bound_from(timestamps: np.ndarray, value: float) -> int:
    return int(np.searchsorted(timestamps, np.float32(value), side="left", sorter=None))


def _edge_end(
    *,
    n: int,
    a: int,
    forced_start: int,
    forced_applied: int,
    real_fever_time: float,
    use_forced_great_timing: bool,
    timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
) -> tuple[int, float]:
    forced_end = int(forced_start) + int(forced_applied) - 1
    start_time = float(timestamps[int(a)])
    if (
        bool(use_forced_great_timing)
        and int(forced_applied) > 0
        and forced_end >= int(forced_start)
        and forced_end < int(a)
        and forced_end < int(n)
    ):
        forced_t = float(great_candidate_timestamps[forced_end])
        if forced_t > start_time:
            start_time = forced_t
    e = _lower_bound_from(timestamps, start_time + float(real_fever_time))
    if e <= int(a):
        e = int(a) + 1
    if e > int(n):
        e = int(n)
    return int(e), float(start_time)


def _range_head_mask(start: int, end: int, *, n: int) -> tuple[int, int, int, int]:
    start_i = max(0, min(int(start), int(n), 100))
    end_i = max(0, min(int(end), int(n), 100))
    words = [0, 0, 0, 0]
    if end_i <= start_i:
        return 0, 0, 0, 0
    for word_idx in range(4):
        lo = word_idx * 32
        hi = min(lo + 32, 100)
        a = max(start_i, lo)
        b = min(end_i, hi)
        if b <= a:
            continue
        width = b - a
        words[word_idx] = ((1 << width) - 1) << (a - lo)
    return int(words[0]), int(words[1]), int(words[2]), int(words[3])


def _range_body_count(start: int, end: int, *, n: int) -> int:
    return max(0, min(int(end), int(n)) - max(int(start), 100))


def _edge_surface(*, n: int, fever_start: int, fever_end: int, great_start: int, great_end: int) -> FgResponseSurface:
    f0, f1, f2, f3 = _range_head_mask(fever_start, fever_end, n=int(n))
    g0, g1, g2, g3 = _range_head_mask(great_start, great_end, n=int(n))
    return FgResponseSurface(
        f0,
        f1,
        f2,
        f3,
        g0,
        g1,
        g2,
        g3,
        _range_body_count(fever_start, fever_end, n=int(n)),
        _range_body_count(great_start, great_end, n=int(n)),
    )


def _edge_surface_options(
    *,
    i: int,
    first: bool,
    n: int,
    actions: list[int],
    later_fill: list[int],
    first_fill: list[int],
    later_forced: list[int],
    first_forced: list[int],
    real_fever_time: float,
    use_forced_great_timing: bool,
    timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
) -> list[tuple[int, int, FgResponseSurface]]:
    out: list[tuple[int, int, FgResponseSurface]] = []
    fills = first_fill if first else later_fill
    forced_values = first_forced if first else later_forced
    prev_fill = -1
    prev_start_time = -1.0
    prev_e = -1
    for action_idx, k in enumerate(actions):
        fill = int(fills[action_idx])
        a = int(fill if first else int(i) + fill)
        if a >= n:
            break
        forced_start = 0 if first else int(i) + 1
        forced_applied = int(forced_values[action_idx])
        e, start_time = _edge_end(
            n=int(n),
            a=int(a),
            forced_start=int(forced_start),
            forced_applied=int(forced_applied),
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(use_forced_great_timing),
            timestamps=timestamps,
            great_candidate_timestamps=great_candidate_timestamps,
        )
        if fill == prev_fill and (start_time == prev_start_time or e == prev_e):
            prev_fill = fill
            prev_start_time = start_time
            prev_e = e
            continue
        great_end = min(int(n), int(forced_start) + int(forced_applied))
        out.append(
            (
                int(k),
                int(e),
                _edge_surface(
                    n=int(n),
                    fever_start=int(a),
                    fever_end=int(e),
                    great_start=int(forced_start),
                    great_end=int(great_end),
                ),
            )
        )
        prev_fill = fill
        prev_start_time = start_time
        prev_e = e
    return out


def reconstruct_force_greats_response_counts(
    *,
    frontier: FgResponseFrontierResult,
    target_surface: FgResponseSurface,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    raw_fever_fill: float,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
) -> tuple[int, ...]:
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    if n <= 0 or target_surface == _EMPTY_SURFACE:
        return ()
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")

    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=int(frontier.non_fever_base),
        use_forced_great_timing=bool(use_forced_great_timing),
    )

    target_words = (
        int(target_surface.fever0),
        int(target_surface.fever1),
        int(target_surface.fever2),
        int(target_surface.fever3),
        int(target_surface.great0),
        int(target_surface.great1),
        int(target_surface.great2),
        int(target_surface.great3),
        int(target_surface.body_fever),
        int(target_surface.body_great),
    )

    def _empty(words: tuple[int, ...]) -> bool:
        return not any(int(value) for value in words)

    def _edge_words(edge: FgResponseSurface) -> tuple[int, ...]:
        return (
            int(edge.fever0),
            int(edge.fever1),
            int(edge.fever2),
            int(edge.fever3),
            int(edge.great0),
            int(edge.great1),
            int(edge.great2),
            int(edge.great3),
            int(edge.body_fever),
            int(edge.body_great),
        )

    def _subtract_edge(words: tuple[int, ...], edge: FgResponseSurface) -> tuple[int, ...] | None:
        edge_values = _edge_words(edge)
        for idx in range(8):
            if int(edge_values[idx]) & ~int(words[idx]):
                return None
        if int(edge_values[8]) > int(words[8]) or int(edge_values[9]) > int(words[9]):
            return None
        return (
            int(words[0]) & ~int(edge_values[0]),
            int(words[1]) & ~int(edge_values[1]),
            int(words[2]) & ~int(edge_values[2]),
            int(words[3]) & ~int(edge_values[3]),
            int(words[4]) & ~int(edge_values[4]),
            int(words[5]) & ~int(edge_values[5]),
            int(words[6]) & ~int(edge_values[6]),
            int(words[7]) & ~int(edge_values[7]),
            int(words[8]) - int(edge_values[8]),
            int(words[9]) - int(edge_values[9]),
        )

    memo: set[tuple[int, bool, tuple[int, ...]]] = set()

    def _search(state: int, first: bool, remaining: tuple[int, ...]) -> tuple[int, ...] | None:
        if _empty(remaining):
            return ()
        key = (int(state), bool(first), remaining)
        if key in memo:
            return None
        for k, next_state, edge in _edge_surface_options(
            i=int(state),
            first=bool(first),
            n=int(n),
            actions=actions,
            later_fill=later_fill,
            first_fill=first_fill,
            later_forced=later_forced,
            first_forced=first_forced,
            real_fever_time=float(real_fever_time),
            use_forced_great_timing=bool(use_forced_great_timing),
            timestamps=ts,
            great_candidate_timestamps=great_ts,
        ):
            next_remaining = _subtract_edge(remaining, edge)
            if next_remaining is None:
                continue
            if _empty(next_remaining):
                return (int(k),)
            if int(next_state) >= int(n):
                continue
            tail = _search(int(next_state), False, next_remaining)
            if tail is not None:
                return (int(k),) + tail
        memo.add(key)
        return None

    counts = _search(0, True, target_words)
    if counts is None:
        raise ValueError("could not reconstruct forced-count path for FG response surface")
    return tuple(int(value) for value in counts)
