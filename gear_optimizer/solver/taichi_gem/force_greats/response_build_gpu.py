import time
from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem.runtime import init_taichi

from .response_builder import _action_table, _combine, _reduce_frontier
from .response_types import FgResponseFrontierResult, FgResponseSurface, _EMPTY_SURFACE

_GPU_EDGE_BATCH_MAX_BYTES = 1024 * 1024 * 1024


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


@ti.kernel
def _build_fg_response_edges_batch_kernel(
    n: ti.i32,
    geometry_count: ti.i32,
    max_action_count: ti.i32,
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    real_fever_time: ti.types.ndarray(dtype=ti.f32, ndim=1),
    action_count_by_geometry: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_forced: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_valid: ti.types.ndarray(dtype=ti.i8, ndim=3),
    later_next: ti.types.ndarray(dtype=ti.i32, ndim=3),
    later_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=4),
    later_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=4),
    later_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=4),
    first_valid: ti.types.ndarray(dtype=ti.i8, ndim=2),
    first_next: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=3),
):
    for geometry_idx, state_i, action_idx in ti.ndrange(geometry_count, n, max_action_count):
        if action_idx < action_count_by_geometry[geometry_idx]:
            fill = later_fill[geometry_idx, action_idx]
            forced = later_forced[geometry_idx, action_idx]
            activation = state_i + fill
            forced_start = state_i + 1
            edge_e = ti.i32(-1)
            start_time = ti.f32(-1.0)
            if activation < n:
                e, computed_start = _edge_end_idx(
                    n,
                    activation,
                    forced_start,
                    forced,
                    real_fever_time[geometry_idx],
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                )
                edge_e = e
                start_time = computed_start
                later_valid[geometry_idx, state_i, action_idx] = ti.i8(1)
                later_next[geometry_idx, state_i, action_idx] = e
                great_end = ti.min(n, forced_start + forced)
                for word in ti.static(range(4)):
                    later_fever_masks[geometry_idx, state_i, action_idx, word] = _mask_word(activation, e, n, word)
                    later_great_masks[geometry_idx, state_i, action_idx, word] = _mask_word(
                        forced_start, great_end, n, word
                    )
                later_body_counts[geometry_idx, state_i, action_idx, 0] = _body_count(activation, e, n)
                later_body_counts[geometry_idx, state_i, action_idx, 1] = _body_count(forced_start, great_end, n)

            if action_idx > 0 and later_valid[geometry_idx, state_i, action_idx] != 0:
                prev_fill = later_fill[geometry_idx, action_idx - 1]
                if fill == prev_fill:
                    prev_e, prev_start_time = _edge_end_idx(
                        n,
                        state_i + prev_fill,
                        state_i + 1,
                        later_forced[geometry_idx, action_idx - 1],
                        real_fever_time[geometry_idx],
                        use_forced_great_timing_i,
                        timestamps,
                        great_candidate_timestamps,
                    )
                    if start_time == prev_start_time or edge_e == prev_e:
                        later_valid[geometry_idx, state_i, action_idx] = ti.i8(0)

    for geometry_idx, action_idx in ti.ndrange(geometry_count, max_action_count):
        if action_idx < action_count_by_geometry[geometry_idx]:
            fill = first_fill[geometry_idx, action_idx]
            forced = first_forced[geometry_idx, action_idx]
            activation = fill
            edge_e = ti.i32(-1)
            start_time = ti.f32(-1.0)
            if activation < n:
                e, computed_start = _edge_end_idx(
                    n,
                    activation,
                    ti.i32(0),
                    forced,
                    real_fever_time[geometry_idx],
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                )
                edge_e = e
                start_time = computed_start
                first_valid[geometry_idx, action_idx] = ti.i8(1)
                first_next[geometry_idx, action_idx] = e
                great_end = ti.min(n, forced)
                for word in ti.static(range(4)):
                    first_fever_masks[geometry_idx, action_idx, word] = _mask_word(activation, e, n, word)
                    first_great_masks[geometry_idx, action_idx, word] = _mask_word(0, great_end, n, word)
                first_body_counts[geometry_idx, action_idx, 0] = _body_count(activation, e, n)
                first_body_counts[geometry_idx, action_idx, 1] = _body_count(0, great_end, n)

            if action_idx > 0 and first_valid[geometry_idx, action_idx] != 0:
                prev_fill = first_fill[geometry_idx, action_idx - 1]
                if fill == prev_fill:
                    prev_e, prev_start_time = _edge_end_idx(
                        n,
                        prev_fill,
                        ti.i32(0),
                        first_forced[geometry_idx, action_idx - 1],
                        real_fever_time[geometry_idx],
                        use_forced_great_timing_i,
                        timestamps,
                        great_candidate_timestamps,
                    )
                    if start_time == prev_start_time or edge_e == prev_e:
                        first_valid[geometry_idx, action_idx] = ti.i8(0)


def _append_edge_from_arrays(
    bucket: list[FgResponseSurface],
    fever_masks: np.ndarray,
    great_masks: np.ndarray,
    body_counts: np.ndarray,
    row: int,
    action_idx: int,
) -> bool:
    cf0 = int(fever_masks[row, action_idx, 0])
    cf1 = int(fever_masks[row, action_idx, 1])
    cf2 = int(fever_masks[row, action_idx, 2])
    cf3 = int(fever_masks[row, action_idx, 3])
    cg0 = int(great_masks[row, action_idx, 0])
    cg1 = int(great_masks[row, action_idx, 1])
    cg2 = int(great_masks[row, action_idx, 2])
    cg3 = int(great_masks[row, action_idx, 3])
    cbf = int(body_counts[row, action_idx, 0])
    cbg = int(body_counts[row, action_idx, 1])
    write = 0
    kept_new = True
    for kept_surface in bucket:
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
            kept_new = False
            break
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
            bucket[write] = kept_surface
            write += 1
    if not kept_new:
        return False
    del bucket[write:]
    bucket.append(FgResponseSurface(cf0, cf1, cf2, cf3, cg0, cg1, cg2, cg3, cbf, cbg))
    return True


def _frontier_from_edge_arrays(
    *,
    n: int,
    action_count: int,
    non_fever_base: int,
    later_valid: np.ndarray,
    later_next: np.ndarray,
    later_fever_masks: np.ndarray,
    later_great_masks: np.ndarray,
    later_body_counts: np.ndarray,
    first_valid: np.ndarray,
    first_next: np.ndarray,
    first_fever_masks: np.ndarray,
    first_great_masks: np.ndarray,
    first_body_counts: np.ndarray,
    seconds: float,
) -> FgResponseFrontierResult:
    reachable = np.zeros((n + 1,), dtype=np.bool_)
    reachable[n] = True
    state_frontiers: dict[int, tuple[FgResponseSurface, ...]] = {n: (_EMPTY_SURFACE,)}
    transitions = 0
    generated_surfaces = 0
    retained_total = 1
    max_state_frontier = 1

    first_edge_buckets: dict[int, list[FgResponseSurface]] = {}
    for action_idx in range(action_count):
        if int(first_valid[0, action_idx]) == 0:
            continue
        e = int(first_next[0, action_idx])
        _append_edge_from_arrays(
            first_edge_buckets.setdefault(e, []),
            first_fever_masks,
            first_great_masks,
            first_body_counts,
            0,
            action_idx,
        )
    first_edges = [(int(e), surface) for e, bucket in first_edge_buckets.items() for surface in bucket]
    transitions += len(first_edges)
    for e, _edge in first_edges:
        reachable[int(e)] = True

    later_edges_by_state: dict[int, list[tuple[int, FgResponseSurface]]] = {}
    for i in range(n):
        if not bool(reachable[i]):
            continue
        edge_buckets: dict[int, list[FgResponseSurface]] = {}
        for action_idx in range(action_count):
            if int(later_valid[i, action_idx]) == 0:
                continue
            e = int(later_next[i, action_idx])
            _append_edge_from_arrays(
                edge_buckets.setdefault(e, []),
                later_fever_masks,
                later_great_masks,
                later_body_counts,
                i,
                action_idx,
            )
        edges = [(int(e), surface) for e, bucket in edge_buckets.items() for surface in bucket]
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
        seconds=float(seconds),
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

    return _frontier_from_edge_arrays(
        n=int(n),
        action_count=int(action_count),
        non_fever_base=max(0, int(non_fever_base)),
        later_valid=later_valid,
        later_next=later_next,
        later_fever_masks=later_fever_masks,
        later_great_masks=later_great_masks,
        later_body_counts=later_body_counts,
        first_valid=first_valid,
        first_next=first_next,
        first_fever_masks=first_fever_masks,
        first_great_masks=first_great_masks,
        first_body_counts=first_body_counts,
        seconds=float(time.perf_counter() - started),
    )


def _batch_chunk_size(*, n: int, action_count: int, geometry_count: int) -> int:
    bytes_per_edge = 64
    denom = max(1, int(n) * max(1, int(action_count)) * bytes_per_edge)
    return max(1, min(int(geometry_count), int(_GPU_EDGE_BATCH_MAX_BYTES) // denom))


def build_force_greats_response_frontiers_gpu_batch(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    geometries: Any,
    use_forced_great_timing: bool = True,
) -> tuple[FgResponseFrontierResult, ...]:
    init_taichi()
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    geometry_rows = tuple(geometries or ())
    if not geometry_rows:
        return ()
    if n <= 0:
        return tuple(FgResponseFrontierResult((_EMPTY_SURFACE,), {}, 0, 0, 0, 0, 1, 1, 0, 0.0) for _ in geometry_rows)
    if bool(np.any(ts[1:] < ts[:-1])):
        raise ValueError("timestamps must be sorted in nondecreasing order")
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")

    prepared = []
    for idx, row in enumerate(geometry_rows):
        raw_fever_fill, non_fever_base, real_fever_time = row
        actions, later_fill, first_fill, later_forced, first_forced = _action_table(
            raw_fever_fill=float(raw_fever_fill),
            non_fever_base=max(0, int(non_fever_base)),
            use_forced_great_timing=bool(use_forced_great_timing),
        )
        prepared.append(
            (
                idx,
                max(0, int(non_fever_base)),
                float(real_fever_time),
                np.asarray(later_fill, dtype=np.int32),
                np.asarray(first_fill, dtype=np.int32),
                np.asarray(later_forced, dtype=np.int32),
                np.asarray(first_forced, dtype=np.int32),
            )
        )

    groups: dict[int, list[tuple]] = {}
    for item in prepared:
        groups.setdefault(int(item[3].shape[0]), []).append(item)

    out: list[FgResponseFrontierResult | None] = [None] * len(geometry_rows)
    for action_count, items in groups.items():
        chunk_size = _batch_chunk_size(n=int(n), action_count=int(action_count), geometry_count=len(items))
        for start in range(0, len(items), chunk_size):
            chunk = items[start : start + chunk_size]
            geometry_count = len(chunk)
            action_counts = np.full((geometry_count,), int(action_count), dtype=np.int32)
            real_times = np.asarray([item[2] for item in chunk], dtype=np.float32)
            later_fill = np.vstack([item[3] for item in chunk]).astype(np.int32, copy=False)
            first_fill = np.vstack([item[4] for item in chunk]).astype(np.int32, copy=False)
            later_forced = np.vstack([item[5] for item in chunk]).astype(np.int32, copy=False)
            first_forced = np.vstack([item[6] for item in chunk]).astype(np.int32, copy=False)
            later_valid = np.zeros((geometry_count, n, action_count), dtype=np.int8)
            later_next = np.full((geometry_count, n, action_count), -1, dtype=np.int32)
            later_fever_masks = np.zeros((geometry_count, n, action_count, 4), dtype=np.uint32)
            later_great_masks = np.zeros((geometry_count, n, action_count, 4), dtype=np.uint32)
            later_body_counts = np.zeros((geometry_count, n, action_count, 2), dtype=np.int32)
            first_valid = np.zeros((geometry_count, action_count), dtype=np.int8)
            first_next = np.full((geometry_count, action_count), -1, dtype=np.int32)
            first_fever_masks = np.zeros((geometry_count, action_count, 4), dtype=np.uint32)
            first_great_masks = np.zeros((geometry_count, action_count, 4), dtype=np.uint32)
            first_body_counts = np.zeros((geometry_count, action_count, 2), dtype=np.int32)

            _build_fg_response_edges_batch_kernel(
                int(n),
                int(geometry_count),
                int(action_count),
                1 if bool(use_forced_great_timing) else 0,
                ts,
                great_ts,
                real_times,
                action_counts,
                later_fill,
                first_fill,
                later_forced,
                first_forced,
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
            for local_idx, item in enumerate(chunk):
                source_idx = int(item[0])
                out[source_idx] = _frontier_from_edge_arrays(
                    n=int(n),
                    action_count=int(action_count),
                    non_fever_base=int(item[1]),
                    later_valid=later_valid[local_idx],
                    later_next=later_next[local_idx],
                    later_fever_masks=later_fever_masks[local_idx],
                    later_great_masks=later_great_masks[local_idx],
                    later_body_counts=later_body_counts[local_idx],
                    first_valid=first_valid[local_idx : local_idx + 1],
                    first_next=first_next[local_idx : local_idx + 1],
                    first_fever_masks=first_fever_masks[local_idx : local_idx + 1],
                    first_great_masks=first_great_masks[local_idx : local_idx + 1],
                    first_body_counts=first_body_counts[local_idx : local_idx + 1],
                    seconds=0.0,
                )

    missing = [idx for idx, frontier in enumerate(out) if frontier is None]
    if missing:
        raise ValueError(f"FG response frontier GPU batch missed geometry indices: {missing[:8]}")
    return tuple(frontier for frontier in out if frontier is not None)


__all__ = ["build_force_greats_response_frontier_gpu", "build_force_greats_response_frontiers_gpu_batch"]
