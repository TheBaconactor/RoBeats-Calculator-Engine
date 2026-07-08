from __future__ import annotations

import concurrent.futures
from typing import Any

import numpy as np

from .fill_crossing import late_great_activation_prefix
from .response_builder import _action_table, _edge_surface_options
from .response_build_gpu_precompute import (
    _canonicalize_first_only_prepared_items_with_end_indices,
    _first_only_chunks,
)
from . import response_build_gpu_numba as _rb_numba
from .response_build_gpu_reducer import (
    _first_frontier_results_for_precomputed_range,
    _first_frontier_reducer_executor,
    _resolve_first_only_reducer_threads,
)
from .response_types import FgResponseFrontierResult, FgResponseSurface, _EMPTY_SURFACE


def _combine_surfaces(edge: FgResponseSurface, tail: FgResponseSurface) -> FgResponseSurface:
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
        int(edge.body_fever_great + tail.body_fever_great),
    )


def _surface_dominates(left: FgResponseSurface, right: FgResponseSurface) -> bool:
    left_normal_great = int(left.body_great) - int(left.body_fever_great)
    right_normal_great = int(right.body_great) - int(right.body_fever_great)
    return (
        int(left.body_fever) >= int(right.body_fever)
        and int(left_normal_great) <= int(right_normal_great)
        and int(left.body_fever_great) <= int(right.body_fever_great)
        and (int(right.fever0) & ~int(left.fever0)) == 0
        and (int(right.fever1) & ~int(left.fever1)) == 0
        and (int(right.fever2) & ~int(left.fever2)) == 0
        and (int(right.fever3) & ~int(left.fever3)) == 0
        and (int(left.great0) & ~int(right.great0)) == 0
        and (int(left.great1) & ~int(right.great1)) == 0
        and (int(left.great2) & ~int(right.great2)) == 0
        and (int(left.great3) & ~int(right.great3)) == 0
        and (int(left.fever0 & left.great0), int(left.fever1 & left.great1),
             int(left.fever2 & left.great2), int(left.fever3 & left.great3))
        == (int(right.fever0 & right.great0), int(right.fever1 & right.great1),
            int(right.fever2 & right.great2), int(right.fever3 & right.great3))
    )


def _to_numba_surface(surface: FgResponseSurface) -> tuple[np.uint64, ...]:
    return (
        np.uint64(int(surface.fever0) | (int(surface.fever1) << 32)),
        np.uint64(int(surface.fever2) | (int(surface.fever3) << 32)),
        np.uint64(int(surface.great0) | (int(surface.great1) << 32)),
        np.uint64(int(surface.great2) | (int(surface.great3) << 32)),
        np.uint64(int(surface.body_fever)),
        np.uint64(int(surface.body_great)),
        np.uint64(int(surface.body_fever_great)),
    )


def _from_numba_surface(row) -> FgResponseSurface:
    fever_lo = int(row[0])
    fever_hi = int(row[1])
    great_lo = int(row[2])
    great_hi = int(row[3])
    return FgResponseSurface(
        fever_lo & 0xFFFFFFFF,
        (fever_lo >> 32) & 0xFFFFFFFF,
        fever_hi & 0xFFFFFFFF,
        (fever_hi >> 32) & 0xFFFFFFFF,
        great_lo & 0xFFFFFFFF,
        (great_lo >> 32) & 0xFFFFFFFF,
        great_hi & 0xFFFFFFFF,
        (great_hi >> 32) & 0xFFFFFFFF,
        int(row[4]),
        int(row[5]),
        int(row[6]),
    )


def _head_envelope_reduce_surfaces(
    surfaces: tuple[FgResponseSurface, ...],
    *,
    lo_pos: int,
    hi_pos: int,
) -> tuple[FgResponseSurface, ...]:
    if not surfaces:
        return (_EMPTY_SURFACE,)
    from numba.typed import List

    from .response_build_gpu_numba import (
        _HEAD_FILTER_MIN_SURFACES,
        _NUMBA_SURFACE_TYPE,
        _numba_head_envelope_filter,
        _numba_reduce,
    )

    rows = List.empty_list(_NUMBA_SURFACE_TYPE)
    for surface in surfaces:
        rows.append(_to_numba_surface(surface))
    reduced = _numba_head_envelope_filter(
        _numba_reduce(rows),
        int(lo_pos),
        int(hi_pos),
        int(_HEAD_FILTER_MIN_SURFACES),
    )
    return tuple(_from_numba_surface(reduced[idx]) for idx in range(len(reduced))) or (_EMPTY_SURFACE,)


def _reduce_surfaces(
    surfaces: tuple[FgResponseSurface, ...],
    *,
    lo_pos: int = 0,
    hi_pos: int = 100,
) -> tuple[FgResponseSurface, ...]:
    if not surfaces:
        return (_EMPTY_SURFACE,)
    kept: list[FgResponseSurface] = []
    for surface in surfaces:
        if any(_surface_dominates(other, surface) for other in kept):
            continue
        kept = [other for other in kept if not _surface_dominates(surface, other)]
        if surface not in kept:
            kept.append(surface)
    reduced = tuple(kept) if kept else (_EMPTY_SURFACE,)
    if len(reduced) > 96 and int(hi_pos) > int(lo_pos):
        return _head_envelope_reduce_surfaces(reduced, lo_pos=int(lo_pos), hi_pos=int(hi_pos))
    return reduced


def _input_engine_rebuild_first_frontier(
    *,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
    use_forced_great_timing: bool,
) -> FgResponseFrontierResult:
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=max(0, int(non_fever_base)),
        use_forced_great_timing=bool(use_forced_great_timing),
    )
    n = int(timestamps.shape[0])
    memo: dict[tuple[int, bool], tuple[FgResponseSurface, ...]] = {}
    states_evaluated = 0
    generated_surfaces = 0
    retained_surfaces_total = 0
    max_state_frontier = 1

    def _frontier(state: int, first: bool) -> tuple[FgResponseSurface, ...]:
        nonlocal states_evaluated, generated_surfaces, retained_surfaces_total, max_state_frontier
        if int(state) >= int(n):
            return (_EMPTY_SURFACE,)
        key = (int(state), bool(first))
        cached = memo.get(key)
        if cached is not None:
            return cached
        states_evaluated += 1
        generated: list[FgResponseSurface] = []
        for option in _edge_surface_options(
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
            timestamps=timestamps,
            perfect_candidate_timestamps=perfect_candidate_timestamps,
            great_candidate_timestamps=great_candidate_timestamps,
            perfect_floor_timestamps=perfect_floor_timestamps,
            great_floor_timestamps=great_floor_timestamps,
            lanes=lanes,
            raw_fever_fill=float(raw_fever_fill),
        ):
            edge = option["surface"]
            next_state = int(option["next_state"])
            if next_state <= int(state):
                raise ValueError("FG input-engine frontier emitted a non-advancing section")
            tails = (_EMPTY_SURFACE,) if next_state >= int(n) else _frontier(next_state, False)
            for tail in tails:
                generated.append(_combine_surfaces(edge, tail))
        generated_surfaces += len(generated)
        reduced = _reduce_surfaces(tuple(generated), lo_pos=int(state), hi_pos=min(int(n), 100))
        retained_surfaces_total += len(reduced)
        max_state_frontier = max(int(max_state_frontier), int(len(reduced)))
        memo[key] = reduced
        return reduced

    first_frontier = _frontier(0, True)
    return FgResponseFrontierResult(
        first_frontier=first_frontier,
        state_frontiers={},
        states_evaluated=int(states_evaluated),
        actions=int(len(actions)),
        transitions_evaluated=int(generated_surfaces),
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_surfaces_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=int(non_fever_base),
        seconds=0.0,
    )


def _compact_first_frontier_action_arrays(
    actions: list[int],
    later_fill: list[int],
    first_fill: list[int],
    later_forced: list[int],
    first_forced: list[int],
    raw_fever_fill: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    rows: list[tuple[int, int, int, int, int, int, int]] = []
    row_by_fill: dict[tuple[int, int], int] = {}
    for action_idx, k in enumerate(actions):
        later = int(later_fill[int(action_idx)])
        first = int(first_fill[int(action_idx)])
        key = (int(later), int(first))
        row_idx = row_by_fill.get(key)
        later_activation = -1
        first_activation = -1
        if row_idx is not None:
            (
                _normal_k,
                normal_later,
                normal_first,
                normal_later_forced,
                normal_first_forced,
                later_activation,
                first_activation,
            ) = rows[int(row_idx)]
        # Late-Great activation (single-sourced with the reconstruct mirror `_edge_surface_options`
        # via late_great_activation_prefix): the forced-Great prefix when the activation Great IS the
        # server fill-crossing, else None -> the -1 sentinel stays, so the phantom late-Great
        # over-report (a Perfect crosses first) can never be selected on any vendor.
        if int(action_idx) > 0 and int(later_fill[int(action_idx) - 1]) == int(later):
            candidate = late_great_activation_prefix(int(later), int(k), first=False, fever_fill_denom=float(raw_fever_fill))
            if candidate is not None:
                later_activation = int(candidate) if int(later_activation) < 0 else min(int(later_activation), int(candidate))
        if int(action_idx) > 0 and int(first_fill[int(action_idx) - 1]) == int(first):
            candidate = late_great_activation_prefix(int(first), int(k), first=True, fever_fill_denom=float(raw_fever_fill))
            if candidate is not None:
                first_activation = int(candidate) if int(first_activation) < 0 else min(int(first_activation), int(candidate))
        if row_idx is None:
            row_by_fill[key] = len(rows)
            rows.append(
                (
                    int(k),
                    int(later),
                    int(first),
                    int(later_forced[int(action_idx)]),
                    int(first_forced[int(action_idx)]),
                    int(later_activation),
                    int(first_activation),
                )
            )
        else:
            rows[int(row_idx)] = (
                int(_normal_k),
                int(normal_later),
                int(normal_first),
                int(normal_later_forced),
                int(normal_first_forced),
                int(later_activation),
                int(first_activation),
            )
    if not rows:
        rows.append((0, 0, 0, 0, 0, -1, -1))
    row_arr = np.asarray(rows, dtype=np.int32)
    return (
        np.ascontiguousarray(np.asarray(actions if actions else [0], dtype=np.int32), dtype=np.int32),
        np.ascontiguousarray(row_arr[:, 1], dtype=np.int32),
        np.ascontiguousarray(row_arr[:, 2], dtype=np.int32),
        np.ascontiguousarray(row_arr[:, 3], dtype=np.int32),
        np.ascontiguousarray(row_arr[:, 4], dtype=np.int32),
        np.ascontiguousarray(row_arr[:, 5], dtype=np.int32),
        np.ascontiguousarray(row_arr[:, 6], dtype=np.int32),
    )


def _build_force_greats_response_first_frontiers_gpu_batch(
    *,
    timestamps: Any,
    perfect_candidate_timestamps: Any | None = None,
    great_candidate_timestamps: Any | None = None,
    perfect_floor_timestamps: Any,
    great_floor_timestamps: Any,
    geometries: Any,
    lanes: Any | None = None,
    use_forced_great_timing: bool = True,
) -> tuple[FgResponseFrontierResult, ...]:
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    geometry_rows = tuple(geometries or ())
    if not geometry_rows:
        return ()
    if n <= 0:
        return tuple(FgResponseFrontierResult((_EMPTY_SURFACE,), {}, 0, 0, 0, 0, 1, 1, 0, 0.0) for _ in geometry_rows)
    if bool(np.any(ts[1:] < ts[:-1])):
        raise ValueError("timestamps must be sorted in nondecreasing order")
    if perfect_candidate_timestamps is None:
        perfect_ts = ts
    else:
        perfect_ts = np.ascontiguousarray(np.asarray(perfect_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(perfect_ts.shape[0]) != n:
            raise ValueError("perfect_candidate_timestamps length must match timestamps")
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")
    # perfect_floor (issue #42 fever-boundary basis) is REQUIRED: no chart fallback, since
    # silently searching chart would under-count endpoint-early fever -- a wrong best_fg_score.
    floor_ts = np.ascontiguousarray(np.asarray(perfect_floor_timestamps, dtype=np.float32).reshape(-1))
    if int(floor_ts.shape[0]) != n:
        raise ValueError("perfect_floor_timestamps length must match timestamps")
    # great_floor (issue #44 greats-side fever-boundary basis) is REQUIRED for the same fail-loud
    # reason as perfect_floor: searching only the Perfect floor would miss the early-Great
    # boundary surfaces -> an under-counted best_fg_score.
    great_floor_ts = np.ascontiguousarray(np.asarray(great_floor_timestamps, dtype=np.float32).reshape(-1))
    if int(great_floor_ts.shape[0]) != n:
        raise ValueError("great_floor_timestamps length must match timestamps")
    if lanes is None:
        raise ValueError("lanes are required for input-engine-aware FG response build")
    lane_arr = np.ascontiguousarray(np.asarray(lanes, dtype=np.int32).reshape(-1))
    if int(lane_arr.shape[0]) != n:
        raise ValueError("lanes length must match timestamps")
    candidate_high_delta_max = float(
        np.float32(max(0.0, float(np.max(np.maximum(perfect_ts, great_ts) - ts))) + 1.0e-6)
    )
    prefix_perfect_hit, prefix_perfect_valid, prefix_late_hit, prefix_late_valid = (
        _rb_numba._numba_build_prefix_activation_hit_tables(
            int(n),
            ts,
            perfect_ts,
            great_ts,
        )
    )

    prepared = []
    action_table_cache: dict[
        tuple[float, int, bool],
        tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray],
    ] = {}
    for idx, row in enumerate(geometry_rows):
        raw_fever_fill, non_fever_base, real_fever_time = row
        action_key = (float(raw_fever_fill), max(0, int(non_fever_base)), bool(use_forced_great_timing))
        action_arrays = action_table_cache.get(action_key)
        if action_arrays is None:
            actions, later_fill, first_fill, later_forced, first_forced = _action_table(
                raw_fever_fill=float(raw_fever_fill),
                non_fever_base=max(0, int(non_fever_base)),
                use_forced_great_timing=bool(use_forced_great_timing),
            )
            action_arrays = _compact_first_frontier_action_arrays(
                actions,
                later_fill,
                first_fill,
                later_forced,
                first_forced,
                float(raw_fever_fill),
            )
            action_table_cache[action_key] = action_arrays
        (
            action_k_arr,
            later_fill_arr,
            first_fill_arr,
            later_forced_arr,
            first_forced_arr,
            later_activation_forced_arr,
            first_activation_forced_arr,
        ) = action_arrays
        prepared.append(
            (
                idx,
                max(0, int(non_fever_base)),
                float(raw_fever_fill),
                float(real_fever_time),
                action_k_arr,
                later_fill_arr,
                first_fill_arr,
                later_forced_arr,
                first_forced_arr,
                later_activation_forced_arr,
                first_activation_forced_arr,
            )
        )

    out: list[FgResponseFrontierResult | None] = [None] * len(geometry_rows)
    canonical = _canonicalize_first_only_prepared_items_with_end_indices(
        prepared=prepared,
        timestamps=ts,
        perfect_candidate_timestamps=perfect_ts,
        great_candidate_timestamps=great_ts,
        perfect_floor_timestamps=floor_ts,
        great_floor_timestamps=great_floor_ts,
        lanes=lane_arr,
    )
    prepared = canonical.prepared
    duplicate_sources_by_source = canonical.duplicate_sources_by_source
    chunk_iter = _first_only_chunks(n=int(n), items=prepared)

    first_only_executor: concurrent.futures.ThreadPoolExecutor | None = None
    try:
        for action_count, chunk in chunk_iter:
            geometry_count = len(chunk)
            real_time_index = np.ascontiguousarray(
                np.asarray(
                    [canonical.real_time_index_by_source[int(item[0])] for item in chunk],
                    dtype=np.int32,
                )
            )
            reducer_threads = _resolve_first_only_reducer_threads(int(geometry_count))
            if int(reducer_threads) <= 1:
                range_results = (
                    _first_frontier_results_for_precomputed_range(
                        n=int(n),
                        chunk=chunk,
                        start=0,
                        stop=int(geometry_count),
                        timestamps=ts,
                        candidate_high_delta_max=candidate_high_delta_max,
                        perfect_candidate_timestamps=perfect_ts,
                        great_candidate_timestamps=great_ts,
                        perfect_floor_timestamps=floor_ts,
                        great_floor_timestamps=great_floor_ts,
                        lanes=lane_arr,
                        prefix_perfect_hit=prefix_perfect_hit,
                        prefix_perfect_valid=prefix_perfect_valid,
                        prefix_late_hit=prefix_late_hit,
                        prefix_late_valid=prefix_late_valid,
                        timestamp_end_idx=canonical.timestamp_end_idx,
                        perfect_end_idx=canonical.perfect_end_idx,
                        great_end_idx=canonical.great_end_idx,
                        great_floor_end_idx=canonical.great_floor_end_idx,
                        real_time_index=real_time_index,
                        use_forced_great_timing=bool(use_forced_great_timing),
                    ),
                )
            else:
                target_ranges = max(int(reducer_threads), int(reducer_threads) * 256)
                step = max(1, (int(geometry_count) + int(target_ranges) - 1) // int(target_ranges))
                ranges = tuple(
                    (start, min(int(geometry_count), start + int(step)))
                    for start in range(0, int(geometry_count), int(step))
                )
                if first_only_executor is None:
                    first_only_executor = _first_frontier_reducer_executor(int(reducer_threads))
                futures = tuple(
                    first_only_executor.submit(
                        _first_frontier_results_for_precomputed_range,
                        n=int(n),
                        chunk=chunk,
                        start=int(start),
                        stop=int(stop),
                        timestamps=ts,
                        candidate_high_delta_max=candidate_high_delta_max,
                        perfect_candidate_timestamps=perfect_ts,
                        great_candidate_timestamps=great_ts,
                        perfect_floor_timestamps=floor_ts,
                        great_floor_timestamps=great_floor_ts,
                        lanes=lane_arr,
                        prefix_perfect_hit=prefix_perfect_hit,
                        prefix_perfect_valid=prefix_perfect_valid,
                        prefix_late_hit=prefix_late_hit,
                        prefix_late_valid=prefix_late_valid,
                        timestamp_end_idx=canonical.timestamp_end_idx,
                        perfect_end_idx=canonical.perfect_end_idx,
                        great_end_idx=canonical.great_end_idx,
                        great_floor_end_idx=canonical.great_floor_end_idx,
                        real_time_index=real_time_index,
                        use_forced_great_timing=bool(use_forced_great_timing),
                    )
                    for start, stop in ranges
                )
                range_results = tuple(future.result() for future in futures)
            for result_rows in range_results:
                for source_idx, frontier in result_rows:
                    for duplicate_source_idx in duplicate_sources_by_source[int(source_idx)]:
                        out[int(duplicate_source_idx)] = frontier
    finally:
        if first_only_executor is not None:
            first_only_executor.shutdown(wait=True)

    missing = [idx for idx, frontier in enumerate(out) if frontier is None]
    if missing:
        raise ValueError(f"FG response frontier GPU batch missed geometry indices: {missing[:8]}")
    return tuple(frontier for frontier in out if frontier is not None)

def build_force_greats_response_first_frontiers_gpu_batch(
    *,
    timestamps: Any,
    perfect_candidate_timestamps: Any | None = None,
    great_candidate_timestamps: Any | None = None,
    perfect_floor_timestamps: Any,
    great_floor_timestamps: Any,
    geometries: Any,
    lanes: Any | None = None,
    use_forced_great_timing: bool = True,
) -> tuple[FgResponseFrontierResult, ...]:
    return _build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidate_timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
        great_floor_timestamps=great_floor_timestamps,
        geometries=geometries,
        lanes=lanes,
        use_forced_great_timing=bool(use_forced_great_timing),
    )
