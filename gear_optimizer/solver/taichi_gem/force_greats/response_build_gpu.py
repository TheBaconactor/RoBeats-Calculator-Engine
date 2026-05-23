import time
from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem.runtime import init_taichi

from .response_builder import _action_table, _combine, _reduce_frontier
from .response_types import FgResponseFrontierResult, FgResponseSurface, _EMPTY_SURFACE


@ti.func
def _lower_bound_ts(ts: ti.template(), n, value):
    lo = ti.i32(0)
    hi = n
    while lo < hi:
        mid = (lo + hi) // 2
        if ts[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return lo


@ti.func
def _edge_end_idx(
    n,
    activation_idx,
    forced_start,
    forced_applied,
    real_fever_time,
    use_forced_great_timing_i,
    timestamps: ti.template(),
    great_candidate_timestamps: ti.template(),
):
    forced_end = forced_start + forced_applied - 1
    start_time = timestamps[activation_idx]
    if (
        use_forced_great_timing_i != 0
        and forced_applied > 0
        and forced_end >= forced_start
        and forced_end < activation_idx
        and forced_end < n
    ):
        forced_t = great_candidate_timestamps[forced_end]
        if forced_t > start_time:
            start_time = forced_t
    e = _lower_bound_ts(timestamps, n, ti.cast(start_time + real_fever_time, ti.f32))
    if e <= activation_idx:
        e = activation_idx + 1
    if e > n:
        e = n
    return e, start_time


@ti.func
def _mask_word(start, end, n, word_idx):
    start_i = ti.max(ti.i32(0), ti.min(ti.min(start, n), ti.i32(100)))
    end_i = ti.max(ti.i32(0), ti.min(ti.min(end, n), ti.i32(100)))
    out = ti.u32(0)
    lo = word_idx * 32
    hi = ti.min(lo + 32, ti.i32(100))
    a = ti.max(start_i, lo)
    b = ti.min(end_i, hi)
    if b > a:
        width = b - a
        out = ti.cast((ti.u64(1) << width) - ti.u64(1), ti.u32) << (a - lo)
    return out


@ti.func
def _body_count(start, end, n):
    return ti.max(ti.i32(0), ti.min(end, n) - ti.max(start, ti.i32(100)))


@ti.func
def _write_edge(
    n,
    row,
    action_idx,
    state_i,
    first_i,
    fill,
    forced_applied,
    real_fever_time,
    use_forced_great_timing_i,
    timestamps: ti.template(),
    great_candidate_timestamps: ti.template(),
    valid: ti.template(),
    next_idx: ti.template(),
    fever_masks: ti.template(),
    great_masks: ti.template(),
    body_counts: ti.template(),
):
    activation = fill
    forced_start = ti.i32(0)
    if first_i == 0:
        activation = state_i + fill
        forced_start = state_i + 1

    edge_e = ti.i32(-1)
    start_time = ti.f32(-1.0)
    if activation < n:
        e, computed_start = _edge_end_idx(
            n,
            activation,
            forced_start,
            forced_applied,
            real_fever_time,
            use_forced_great_timing_i,
            timestamps,
            great_candidate_timestamps,
        )
        edge_e = e
        start_time = computed_start
        valid[row, action_idx] = ti.i8(1)
        next_idx[row, action_idx] = e
        great_end = ti.min(n, forced_start + forced_applied)
        for word in ti.static(range(4)):
            fever_masks[row, action_idx, word] = _mask_word(activation, e, n, word)
            great_masks[row, action_idx, word] = _mask_word(forced_start, great_end, n, word)
        body_counts[row, action_idx, 0] = _body_count(activation, e, n)
        body_counts[row, action_idx, 1] = _body_count(forced_start, great_end, n)
    return edge_e, start_time


@ti.kernel
def _build_fg_response_edges_kernel(
    n: ti.i32,
    action_count: ti.i32,
    real_fever_time: ti.f32,
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_valid: ti.types.ndarray(dtype=ti.i8, ndim=2),
    later_next: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    later_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    later_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=3),
    first_valid: ti.types.ndarray(dtype=ti.i8, ndim=2),
    first_next: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=3),
):
    for state_i, action_idx in ti.ndrange(n, action_count):
        fill = later_fill[action_idx]
        forced = later_forced[action_idx]
        e, start_time = _write_edge(
            n,
            state_i,
            action_idx,
            state_i,
            ti.i32(0),
            fill,
            forced,
            real_fever_time,
            use_forced_great_timing_i,
            timestamps,
            great_candidate_timestamps,
            later_valid,
            later_next,
            later_fever_masks,
            later_great_masks,
            later_body_counts,
        )
        if action_idx > 0 and later_valid[state_i, action_idx] != 0:
            prev_fill = later_fill[action_idx - 1]
            if fill == prev_fill:
                prev_e, prev_start_time = _edge_end_idx(
                    n,
                    state_i + prev_fill,
                    state_i + 1,
                    later_forced[action_idx - 1],
                    real_fever_time,
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                )
                if start_time == prev_start_time or e == prev_e:
                    later_valid[state_i, action_idx] = ti.i8(0)

    for action_idx in range(action_count):
        fill = first_fill[action_idx]
        forced = first_forced[action_idx]
        e, start_time = _write_edge(
            n,
            ti.i32(0),
            action_idx,
            ti.i32(0),
            ti.i32(1),
            fill,
            forced,
            real_fever_time,
            use_forced_great_timing_i,
            timestamps,
            great_candidate_timestamps,
            first_valid,
            first_next,
            first_fever_masks,
            first_great_masks,
            first_body_counts,
        )
        if action_idx > 0 and first_valid[0, action_idx] != 0:
            prev_fill = first_fill[action_idx - 1]
            if fill == prev_fill:
                prev_e, prev_start_time = _edge_end_idx(
                    n,
                    prev_fill,
                    ti.i32(0),
                    first_forced[action_idx - 1],
                    real_fever_time,
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                )
                if start_time == prev_start_time or e == prev_e:
                    first_valid[0, action_idx] = ti.i8(0)


def _surface_from_arrays(
    fever_masks: np.ndarray,
    great_masks: np.ndarray,
    body_counts: np.ndarray,
    row: int,
    action_idx: int,
) -> FgResponseSurface:
    return FgResponseSurface(
        int(np.uint32(fever_masks[row, action_idx, 0])),
        int(np.uint32(fever_masks[row, action_idx, 1])),
        int(np.uint32(fever_masks[row, action_idx, 2])),
        int(np.uint32(fever_masks[row, action_idx, 3])),
        int(np.uint32(great_masks[row, action_idx, 0])),
        int(np.uint32(great_masks[row, action_idx, 1])),
        int(np.uint32(great_masks[row, action_idx, 2])),
        int(np.uint32(great_masks[row, action_idx, 3])),
        int(body_counts[row, action_idx, 0]),
        int(body_counts[row, action_idx, 1]),
    )


def build_force_greats_response_frontier_gpu(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
) -> FgResponseFrontierResult:
    init_taichi()
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

    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=max(0, int(non_fever_base)),
        use_forced_great_timing=bool(use_forced_great_timing),
    )
    action_count = int(len(actions))
    later_valid = np.zeros((n, action_count), dtype=np.int8)
    later_next = np.full((n, action_count), -1, dtype=np.int32)
    later_fever_masks = np.zeros((n, action_count, 4), dtype=np.uint32)
    later_great_masks = np.zeros((n, action_count, 4), dtype=np.uint32)
    later_body_counts = np.zeros((n, action_count, 2), dtype=np.int32)
    first_valid = np.zeros((1, action_count), dtype=np.int8)
    first_next = np.full((1, action_count), -1, dtype=np.int32)
    first_fever_masks = np.zeros((1, action_count, 4), dtype=np.uint32)
    first_great_masks = np.zeros((1, action_count, 4), dtype=np.uint32)
    first_body_counts = np.zeros((1, action_count, 2), dtype=np.int32)

    _build_fg_response_edges_kernel(
        int(n),
        int(action_count),
        np.float32(real_fever_time),
        1 if bool(use_forced_great_timing) else 0,
        ts,
        great_ts,
        np.asarray(later_fill, dtype=np.int32),
        np.asarray(first_fill, dtype=np.int32),
        np.asarray(later_forced, dtype=np.int32),
        np.asarray(first_forced, dtype=np.int32),
        later_valid,
        later_next,
        later_fever_masks,
        later_great_masks,
        later_body_counts,
        first_valid,
        first_next,
        first_fever_masks,
        first_great_masks,
        first_body_counts,
    )

    reachable = np.zeros((n + 1,), dtype=np.bool_)
    reachable[n] = True
    state_frontiers: dict[int, tuple[FgResponseSurface, ...]] = {n: (_EMPTY_SURFACE,)}
    transitions = 0
    generated_surfaces = 0
    retained_total = 1
    max_state_frontier = 1

    first_edges: list[tuple[int, FgResponseSurface]] = []
    for action_idx in range(action_count):
        if int(first_valid[0, action_idx]) == 0:
            continue
        first_edges.append(
            (
                int(first_next[0, action_idx]),
                _surface_from_arrays(first_fever_masks, first_great_masks, first_body_counts, 0, action_idx),
            )
        )
    transitions += len(first_edges)
    for e, _edge in first_edges:
        reachable[int(e)] = True

    later_edges_by_state: dict[int, list[tuple[int, FgResponseSurface]]] = {}
    for i in range(n):
        if not bool(reachable[i]):
            continue
        edges: list[tuple[int, FgResponseSurface]] = []
        for action_idx in range(action_count):
            if int(later_valid[i, action_idx]) == 0:
                continue
            edges.append(
                (
                    int(later_next[i, action_idx]),
                    _surface_from_arrays(later_fever_masks, later_great_masks, later_body_counts, i, action_idx),
                )
            )
        transitions += len(edges)
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
        actions=int(action_count),
        transitions_evaluated=int(transitions),
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=max(0, int(non_fever_base)),
        seconds=float(time.perf_counter() - started),
    )


__all__ = ["build_force_greats_response_frontier_gpu"]
