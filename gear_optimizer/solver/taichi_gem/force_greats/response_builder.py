from __future__ import annotations

import time
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


def _lower_bound_from(timestamps: np.ndarray, value: float, lo_start: int) -> int:
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
    e = _lower_bound_from(timestamps, start_time + float(real_fever_time), int(a))
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


def _append_response_edge_bucket(bucket: list[FgResponseSurface], surface: FgResponseSurface) -> bool:
    for kept_surface in bucket:
        if response_surface_dominates(kept_surface, surface):
            return False
    write = 0
    for kept_surface in bucket:
        if not response_surface_dominates(surface, kept_surface):
            bucket[write] = kept_surface
            write += 1
    del bucket[write:]
    bucket.append(surface)
    return True


def _combine(edge: FgResponseSurface, tail: FgResponseSurface) -> FgResponseSurface:
    return FgResponseSurface(
        int(edge.fever0 | tail.fever0),
        int(edge.fever1 | tail.fever1),
        int(edge.fever2 | tail.fever2),
        int(edge.fever3 | tail.fever3),
        int(edge.great0 | tail.great0),
        int(edge.great1 | tail.great1),
        int(edge.great2 | tail.great2),
        int(edge.great3 | tail.great3),
        int(edge.body_fever + tail.body_fever),
        int(edge.body_great + tail.body_great),
    )


def response_surface_dominates(a: FgResponseSurface, b: FgResponseSurface) -> bool:
    return (
        int(a.body_fever) >= int(b.body_fever)
        and int(a.body_great) <= int(b.body_great)
        and (int(b.fever0) & ~int(a.fever0)) == 0
        and (int(b.fever1) & ~int(a.fever1)) == 0
        and (int(b.fever2) & ~int(a.fever2)) == 0
        and (int(b.fever3) & ~int(a.fever3)) == 0
        and (int(a.great0) & ~int(b.great0)) == 0
        and (int(a.great1) & ~int(b.great1)) == 0
        and (int(a.great2) & ~int(b.great2)) == 0
        and (int(a.great3) & ~int(b.great3)) == 0
    )


def _reduce_frontier(surfaces: list[FgResponseSurface]) -> tuple[FgResponseSurface, ...]:
    if not surfaces:
        return (_EMPTY_SURFACE,)
    kept: list[FgResponseSurface] = []
    seen: set[FgResponseSurface] = set()
    for cand in surfaces:
        if cand in seen:
            continue
        seen.add(cand)
        cf0 = cand.fever0
        cf1 = cand.fever1
        cf2 = cand.fever2
        cf3 = cand.fever3
        cg0 = cand.great0
        cg1 = cand.great1
        cg2 = cand.great2
        cg3 = cand.great3
        cbf = cand.body_fever
        cbg = cand.body_great
        for kept_surface in kept:
            kf0 = kept_surface.fever0
            kf1 = kept_surface.fever1
            kf2 = kept_surface.fever2
            kf3 = kept_surface.fever3
            kg0 = kept_surface.great0
            kg1 = kept_surface.great1
            kg2 = kept_surface.great2
            kg3 = kept_surface.great3
            kbf = kept_surface.body_fever
            kbg = kept_surface.body_great
            if (
                kbf >= cbf
                and kbg <= cbg
                and (cf0 & ~kf0) == 0
                and (cf1 & ~kf1) == 0
                and (cf2 & ~kf2) == 0
                and (cf3 & ~kf3) == 0
                and (kg0 & ~cg0) == 0
                and (kg1 & ~cg1) == 0
                and (kg2 & ~cg2) == 0
                and (kg3 & ~cg3) == 0
            ):
                break
        else:
            write = 0
            for kept_surface in kept:
                kf0 = kept_surface.fever0
                kf1 = kept_surface.fever1
                kf2 = kept_surface.fever2
                kf3 = kept_surface.fever3
                kg0 = kept_surface.great0
                kg1 = kept_surface.great1
                kg2 = kept_surface.great2
                kg3 = kept_surface.great3
                kbf = kept_surface.body_fever
                kbg = kept_surface.body_great
                if not (
                    cbf >= kbf
                    and cbg <= kbg
                    and (kf0 & ~cf0) == 0
                    and (kf1 & ~cf1) == 0
                    and (kf2 & ~cf2) == 0
                    and (kf3 & ~cf3) == 0
                    and (cg0 & ~kg0) == 0
                    and (cg1 & ~kg1) == 0
                    and (cg2 & ~kg2) == 0
                    and (cg3 & ~kg3) == 0
                ):
                    kept[write] = kept_surface
                    write += 1
            del kept[write:]
            kept.append(cand)
    return tuple(kept)


def build_force_greats_response_frontier(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
) -> FgResponseFrontierResult:
    started = time.perf_counter()
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    if n <= 0:
        return FgResponseFrontierResult((_EMPTY_SURFACE,), {}, 0, 0, 0, 0, 1, 1, 0, 0.0)
    if bool(np.any(ts[1:] < ts[:-1])):
        raise ValueError("timestamps must be sorted in nondecreasing order")
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")

    b = max(0, int(non_fever_base))
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=int(b),
        use_forced_great_timing=bool(use_forced_great_timing),
    )

    reachable = np.zeros((n + 1,), dtype=np.bool_)
    reachable[n] = True
    state_frontiers: dict[int, tuple[FgResponseSurface, ...]] = {n: (_EMPTY_SURFACE,)}
    transitions = 0
    generated_surfaces = 0
    retained_total = 1
    max_state_frontier = 1

    def edge_surfaces_for_state(i: int, *, first: bool) -> list[tuple[int, FgResponseSurface]]:
        nonlocal transitions
        edge_buckets: dict[int, list[FgResponseSurface]] = {}
        fills = first_fill if first else later_fill
        forced_values = first_forced if first else later_forced
        prev_fill = -1
        prev_start_time = -1.0
        prev_e = -1
        for action_idx in range(len(actions)):
            fill = int(fills[action_idx])
            a = int(fill if first else int(i) + fill)
            if a >= n:
                break
            forced_start = 0 if first else int(i) + 1
            forced_applied = int(forced_values[action_idx])
            e, start_time = _edge_end(
                n=n,
                a=a,
                forced_start=int(forced_start),
                forced_applied=int(forced_applied),
                real_fever_time=float(real_fever_time),
                use_forced_great_timing=bool(use_forced_great_timing),
                timestamps=ts,
                great_candidate_timestamps=great_ts,
            )
            if fill == prev_fill and (start_time == prev_start_time or e == prev_e):
                prev_fill = fill
                prev_start_time = start_time
                prev_e = e
                continue
            great_end = min(n, int(forced_start) + int(forced_applied))
            _append_response_edge_bucket(
                edge_buckets.setdefault(int(e), []),
                _edge_surface(
                    n=n,
                    fever_start=int(a),
                    fever_end=int(e),
                    great_start=int(forced_start),
                    great_end=int(great_end),
                ),
            )
            prev_fill = fill
            prev_start_time = start_time
            prev_e = e
        out = [(int(e), surface) for e, bucket in edge_buckets.items() for surface in bucket]
        transitions += len(out)
        return out

    first_edges = edge_surfaces_for_state(0, first=True)
    for e, _edge in first_edges:
        reachable[int(e)] = True

    later_edges_by_state: dict[int, list[tuple[int, FgResponseSurface]]] = {}
    for i in range(n):
        if not bool(reachable[i]):
            continue
        edges = edge_surfaces_for_state(i, first=False)
        later_edges_by_state[int(i)] = edges
        for e, _edge in edges:
            reachable[int(e)] = True

    for i in range(n - 1, -1, -1):
        if not bool(reachable[i]):
            continue
        generated: list[FgResponseSurface] = []
        for e, edge in later_edges_by_state.get(int(i), []):
            tail_frontier = state_frontiers.get(int(e))
            if tail_frontier is None:
                raise ValueError(f"missing tail frontier for reachable state {e}")
            for tail in tail_frontier:
                generated.append(_combine(edge, tail))
        generated_surfaces += len(generated)
        frontier = _reduce_frontier(generated)
        state_frontiers[int(i)] = frontier
        retained_total += len(frontier)
        max_state_frontier = max(max_state_frontier, len(frontier))

    first_generated: list[FgResponseSurface] = []
    for e, edge in first_edges:
        tail_frontier = state_frontiers.get(int(e))
        if tail_frontier is None:
            raise ValueError(f"missing first-tail frontier for reachable state {e}")
        for tail in tail_frontier:
            first_generated.append(_combine(edge, tail))
    generated_surfaces += len(first_generated)
    first_frontier = _reduce_frontier(first_generated)
    retained_total += len(first_frontier)
    max_state_frontier = max(max_state_frontier, len(first_frontier))

    return FgResponseFrontierResult(
        first_frontier=first_frontier,
        state_frontiers=state_frontiers,
        states_evaluated=int(np.count_nonzero(reachable[:n])),
        actions=int(len(actions)),
        transitions_evaluated=int(transitions),
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=int(b),
        seconds=float(time.perf_counter() - started),
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

    counts: list[int] = []
    state = 0
    target = target_surface
    first = True
    for _step in range(n):
        found: tuple[int, int, FgResponseSurface] | None = None
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
            for tail in frontier.state_frontiers.get(int(next_state), ()):
                if _combine(edge, tail) == target:
                    found = (int(k), int(next_state), tail)
                    break
            if found is not None:
                break
        if found is None:
            raise ValueError("could not reconstruct forced-count path for FG response surface")
        k, next_state, target = found
        counts.append(int(k))
        if target == _EMPTY_SURFACE or int(next_state) >= int(n):
            break
        state = int(next_state)
        first = False
    return tuple(counts)
