from __future__ import annotations

from typing import Any

import numpy as np

from .fill_crossing import late_great_activation_prefix, perfect_crossing_is_region3
from .response_builder import (
    _action_table,
    _build_activation_reachability_context,
    _edge_surface_options,
)
from .response_build_gpu_precompute import (
    _canonicalize_first_only_prepared_items_with_end_indices,
    _first_only_region_groups,
    _region_hit_end_index_tables,
    _region_hit_value_universe,
)
from . import response_build_gpu_numba as _rb_numba
from .response_build_gpu_reducer import (
    _early_great_extension_gap_bound,
    _FirstFrontierWorkspacePlan,
    _song_first_frontier_pair_mod_bound,
)
from .response_build_gpu_scheduler import (
    _FirstFrontierGroupContext,
    _schedule_first_frontier_region_groups,
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
    reachability_context = _build_activation_reachability_context(
        timestamps=timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
        perfect_candidate_timestamps=perfect_candidate_timestamps,
        great_floor_timestamps=great_floor_timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        lanes=lanes,
        fever_fill_denom=float(raw_fever_fill),
    )
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
            reachability_context=reachability_context,
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
            # Normal (Perfect-activation) edges exist only for region-3 rows: the forced run must
            # fit before the activation and leave the bar short of full (perfect_crossing_is_region3;
            # record 16.28 follow-up -- the k >= 2*denom rows' normal edges packed the activation
            # inside the forced run and emitted unreconstructable phantom surfaces). The -1 sentinel
            # suppresses the normal edge per section kind; late-activation variants gate separately.
            later_forced_out = (
                int(later_forced[int(action_idx)])
                if perfect_crossing_is_region3(int(later), int(k), first=False, fever_fill_denom=float(raw_fever_fill))
                else -1
            )
            first_forced_out = (
                int(first_forced[int(action_idx)])
                if perfect_crossing_is_region3(int(first), int(k), first=True, fever_fill_denom=float(raw_fever_fill))
                else -1
            )
            row_by_fill[key] = len(rows)
            rows.append(
                (
                    int(k),
                    int(later),
                    int(first),
                    int(later_forced_out),
                    int(first_forced_out),
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
    stats_sink: dict[str, Any] | None = None,
) -> tuple[FgResponseFrontierResult, ...]:
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    geometry_rows = tuple(geometries or ())
    if stats_sink is not None:
        # Baseline for the degenerate early returns below; the main path overwrites every key.
        stats_sink.update(
            {
                "end_table_precomputes": 0,
                "executor_creations": 0,
                "workspace_allocations": 0,
                "workspace_bytes": 0,
                "region_tables_built": 0,
                "region_table_peak_live": 0,
                "region_table_peak_live_bytes": 0,
                "region_table_parallelism": 1,
                "region_table_parallel_peak_bound_bytes": 0,
                "region_table_legacy_single_peak_bound_bytes": 0,
                "region_table_build_work_ms": 0.0,
                "region_group_reduce_work_ms": 0.0,
                "region_table_groups": 0,
                "geometries_in": int(len(geometry_rows)),
                "geometries_canonical": 0,
                "pair_mod_bound": 0,
            }
        )
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
    if bool(use_forced_great_timing):
        region_hit_values, region_hit_token_to_id = _region_hit_value_universe(
            ts,
            perfect_ts,
            great_ts,
        )
    else:
        region_hit_values = np.empty(0, dtype=np.float64)
        region_hit_token_to_id = np.empty(0, dtype=np.int32)
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
    # ONE end-index precompute per song build: the canonicalization covers every unique
    # real_fever_time of the whole request, so the streamed region-table groups below never
    # rebuild end tables (pre-song-context, each per-group call re-derived its rt subset).
    end_table_precomputes = 1
    canonical = _canonicalize_first_only_prepared_items_with_end_indices(
        prepared=prepared,
        timestamps=ts,
        perfect_candidate_timestamps=perfect_ts,
        great_candidate_timestamps=great_ts,
        perfect_floor_timestamps=floor_ts,
        great_floor_timestamps=great_floor_ts,
        prefix_perfect_hit=prefix_perfect_hit,
        prefix_late_hit=prefix_late_hit,
        lanes=lane_arr,
    )
    prepared = canonical.prepared
    duplicate_sources_by_source = canonical.duplicate_sources_by_source
    region_perfect_end_by_real_time, region_great_end_by_real_time = (
        _region_hit_end_index_tables(
            region_hit_values,
            canonical.unique_real_times,
            floor_ts,
            great_floor_ts,
        )
    )

    # Region-core-table grouping (song-context orchestration): the region-run core work depends
    # on the geometry only through (raw_fever_fill, non_fever_base), never real_fever_time, so it
    # is computed ONCE per key and shared read-only across every rt variant of that key. The
    # producer-owned candidate bounds below admit as many independent reductions as fit within the
    # historical exhaustive one-live-table allocation. The coordinator builds tables serially to
    # avoid temporary-allocation contention, then pipelines their reductions through that strict
    # width. This uses the RAM eliminated by exact capacity without exceeding the safe envelope.
    # Entry order replicates the per-geometry enumeration exactly (bit-exact stream for the
    # order-sensitive consumers). Without forced-great timing the region family is never
    # enumerated, so every key shares one contentless table.
    grouped_items = _first_only_region_groups(prepared)

    # Song-level per-thread workspace plan: every geometry's pair radix is bounded up front
    # (provably, see _song_first_frontier_pair_mod_bound), so the stamp workspaces are right-sized
    # once and persist -- with their carried epochs -- across every region-table group.
    workspace_plan = _FirstFrontierWorkspacePlan(
        n=int(n),
        pair_mod_bound=_song_first_frontier_pair_mod_bound(
            n=int(n),
            prepared=prepared,
            eg_gap_bound=_early_great_extension_gap_bound(floor_ts, great_floor_ts),
        ),
    )

    empty_region_table: tuple | None = None
    if not bool(use_forced_great_timing):
        empty_region_table = (
            np.zeros(int(n) + 2, dtype=np.int64),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
        )

    group_results, schedule_stats = _schedule_first_frontier_region_groups(
        grouped_items=grouped_items,
        context=_FirstFrontierGroupContext(
            n=int(n),
            timestamps=ts,
            candidate_high_delta_max=float(candidate_high_delta_max),
            perfect_candidate_timestamps=perfect_ts,
            great_candidate_timestamps=great_ts,
            perfect_floor_timestamps=floor_ts,
            great_floor_timestamps=great_floor_ts,
            lanes=lane_arr,
            prefix_perfect_hit=prefix_perfect_hit,
            prefix_perfect_valid=prefix_perfect_valid,
            prefix_late_hit=prefix_late_hit,
            prefix_late_valid=prefix_late_valid,
            region_hit_token_to_id=region_hit_token_to_id,
            region_perfect_end_by_real_time=region_perfect_end_by_real_time,
            region_great_end_by_real_time=region_great_end_by_real_time,
            canonical=canonical,
            use_forced_great_timing=bool(use_forced_great_timing),
            empty_region_table=empty_region_table,
            workspace_plan=workspace_plan,
        ),
    )
    for result_rows in group_results:
        for source_idx, frontier in result_rows:
            for duplicate_source_idx in duplicate_sources_by_source[int(source_idx)]:
                out[int(duplicate_source_idx)] = frontier

    if stats_sink is not None:
        stats_sink.update(
            {
                "end_table_precomputes": int(end_table_precomputes),
                "region_hit_values": int(region_hit_values.shape[0]),
                "region_hit_endpoint_bytes": int(
                    region_perfect_end_by_real_time.nbytes
                    + region_great_end_by_real_time.nbytes
                ),
                "executor_creations": int(schedule_stats.executor_creations),
                "workspace_allocations": int(workspace_plan.allocations),
                "workspace_bytes": int(workspace_plan.allocated_bytes),
                "region_tables_built": int(schedule_stats.region_tables_built),
                "region_table_peak_live": int(schedule_stats.region_table_peak_live),
                "region_table_peak_live_bytes": int(schedule_stats.region_table_peak_live_bytes),
                "region_table_parallelism": int(schedule_stats.region_table_parallelism),
                "region_table_parallel_peak_bound_bytes": int(
                    schedule_stats.region_table_parallel_peak_bound_bytes
                ),
                "region_table_legacy_single_peak_bound_bytes": int(
                    schedule_stats.region_table_legacy_single_peak_bound_bytes
                ),
                "region_table_build_work_ms": float(schedule_stats.region_table_build_work_ms),
                "region_group_reduce_work_ms": float(schedule_stats.region_group_reduce_work_ms),
                "region_table_groups": int(len(grouped_items)),
                "geometries_in": int(len(geometry_rows)),
                "geometries_canonical": int(len(prepared)),
                "pair_mod_bound": int(workspace_plan.pair_mod_bound),
            }
        )

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
    stats_sink: dict[str, Any] | None = None,
) -> tuple[FgResponseFrontierResult, ...]:
    """Build the exact FG first frontier for every geometry of ONE song, in one call.

    Song-invariant work (chart array coercion, prefix activation-hit tables, end-index tables for
    every unique real_fever_time, global geometry canonicalization, the reducer executor and its
    per-thread right-sized stamp workspaces) happens exactly once. Per-key region core tables build
    serially and their independent reductions overlap only when the sum of their producer-owned
    build-peak bounds fits the historical exhaustive one-table allocation. Returns frontiers
    aligned to the input geometry order.
    ``stats_sink``, when given, is filled with orchestration counters (telemetry only).
    """
    return _build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidate_timestamps,
        great_candidate_timestamps=great_candidate_timestamps,
        perfect_floor_timestamps=perfect_floor_timestamps,
        great_floor_timestamps=great_floor_timestamps,
        geometries=geometries,
        lanes=lanes,
        use_forced_great_timing=bool(use_forced_great_timing),
        stats_sink=stats_sink,
    )
