from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np

from .fill_crossing import late_great_activation_prefix, perfect_crossing_is_region3, perfect_fill_crossing_offset
from .response_build_gpu_precompute import (
    _canonicalize_first_only_prepared_items_with_end_indices,
    _first_only_region_groups,
)
from . import response_build_gpu_numba as _rb_numba
from .response_build_gpu_reducer import (
    _admit_first_frontier_workspace,
    _early_great_extension_gap_bound,
    _FirstFrontierWorkspacePlan,
    _resolve_first_only_reducer_threads,
    _song_first_frontier_pair_mod_bound,
)
from .response_build_gpu_scheduler import (
    _FirstFrontierGroupContext,
    _schedule_first_frontier_region_groups,
)
from .response_types import FgResponseFrontierResult, _EMPTY_SURFACE
from ...timing_envelope import FRAME_MARGIN_MS


def early_exit_min_fill(perfect_floor_timestamps: np.ndarray, perfect_candidate_timestamps: np.ndarray) -> int:
    """The smallest fill count at which no early fever exit can delay the next activation.

    The search state is a fever's end, not its cutoff, and every note after an early exit is hit at or past the cutoff,
    so an early exit is planned only where the activation `fill` notes past any note has its earliest Perfect two frame
    margins past that note's (and every later note's) latest Perfect: past any cutoff a fever can end there at, its
    conservative separation from the cutoff and next press."""
    floor = np.asarray(perfect_floor_timestamps, dtype=np.float64)
    latest = np.asarray(perfect_candidate_timestamps, dtype=np.float64)
    reach = np.minimum.accumulate(latest[::-1])[::-1] + 2.0 * FRAME_MARGIN_MS / 1000.0
    n = int(floor.shape[0])
    lo, hi = 1, max(1, n)
    while lo < hi:  # the condition only gets easier as the fill grows
        mid = (lo + hi) // 2
        if bool(np.all(floor[mid:] >= reach[: n - mid])):
            hi = mid
        else:
            lo = mid + 1
    return int(lo)


def song_arrays(
    timestamps: Any,
    perfect_candidate_timestamps: Any | None,
    great_candidate_timestamps: Any | None,
    perfect_floor_timestamps: Any,
    great_floor_timestamps: Any,
    late_great_floor_timestamps: Any | None,
    exit_ceiling_timestamps: Any | None,
    lanes: Any | None,
) -> tuple[np.ndarray, ...]:
    """Coerce and check one song's per-note arrays (candidates default to the chart timestamps, the late-Great floor to
    1 ms past the latest Perfect and the exit ceiling to the suffix minimum of the latest Perfects: precise's).
    """
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    if bool(np.any(ts[1:] < ts[:-1])):
        raise ValueError("timestamps must be sorted in nondecreasing order")

    def _f32(values: Any, name: str) -> np.ndarray:
        arr = np.ascontiguousarray(np.asarray(values, dtype=np.float32).reshape(-1))
        if int(arr.shape[0]) != n:
            raise ValueError(f"{name} length must match timestamps")
        return arr

    perfect_ts, great_ts = (
        ts if values is None else _f32(values, name)
        for values, name in (
            (perfect_candidate_timestamps, "perfect_candidate_timestamps"),
            (great_candidate_timestamps, "great_candidate_timestamps"),
        )
    )
    # Both floors are REQUIRED (issues #42/#44): searching chart instead would under-count endpoint-early fever.
    floor_ts = _f32(perfect_floor_timestamps, "perfect_floor_timestamps")
    great_floor_ts = _f32(great_floor_timestamps, "great_floor_timestamps")
    late_great_floor_ts = (
        perfect_ts + np.float32(0.001)
        if late_great_floor_timestamps is None
        else _f32(late_great_floor_timestamps, "late_great_floor_timestamps")
    )
    exit_ceiling_ts = (
        np.ascontiguousarray(np.minimum.accumulate(perfect_ts[::-1])[::-1])
        if exit_ceiling_timestamps is None
        else _f32(exit_ceiling_timestamps, "exit_ceiling_timestamps")
    )
    if lanes is None:
        raise ValueError("lanes are required for input-engine-aware FG response build")
    lane_arr = np.ascontiguousarray(np.asarray(lanes, dtype=np.int32).reshape(-1))
    if int(lane_arr.shape[0]) != n:
        raise ValueError("lanes length must match timestamps")
    return ts, perfect_ts, great_ts, floor_ts, great_floor_ts, late_great_floor_ts, exit_ceiling_ts, lane_arr


def action_table(*, raw_fever_fill: float, non_fever_base: int, use_forced_great_timing: bool):
    actions: list[int] = []
    later_fill: list[int] = []
    first_fill: list[int] = []
    later_forced: list[int] = []
    first_forced: list[int] = []
    last_fill: int | None = None
    for k in range(max(0, int(non_fever_base)) + 1):
        fill = perfect_fill_crossing_offset(float(raw_fever_fill), int(k), first=False)
        if bool(use_forced_great_timing) or last_fill is None or fill != last_fill:
            fill_first = perfect_fill_crossing_offset(float(raw_fever_fill), int(k), first=True)
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


_DEGENERATE_STATS_KEYS = (
    "end_table_precomputes", "executor_creations", "workspace_allocations", "workspace_bytes", "region_tables_built",
    "region_table_peak_live", "region_table_peak_live_bytes", "region_table_parallel_peak_bound_bytes",
    "region_table_legacy_single_peak_bound_bytes", "region_table_groups", "geometries_canonical", "pair_mod_bound",
)


def _prepared_geometries(geometry_rows: tuple, use_forced_great_timing: bool) -> list[tuple]:
    """(source index, non-Fever base, raw fill, fever time, the seven compact action arrays) per geometry; the action
    arrays are shared between geometries with the same (raw fill, non-Fever base)."""
    prepared = []
    action_table_cache: dict[tuple[float, int], tuple[np.ndarray, ...]] = {}
    for idx, (raw_fever_fill, non_fever_base, real_fever_time) in enumerate(geometry_rows):
        key = (float(raw_fever_fill), max(0, int(non_fever_base)))
        action_arrays = action_table_cache.get(key)
        if action_arrays is None:
            action_arrays = action_table_cache[key] = _compact_first_frontier_action_arrays(
                *action_table(
                    raw_fever_fill=key[0], non_fever_base=key[1], use_forced_great_timing=bool(use_forced_great_timing)
                ),
                key[0],
            )
        prepared.append((idx, key[1], key[0], float(real_fever_time), *action_arrays))
    return prepared


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
    late_great_floor_timestamps: Any | None = None,
    exit_ceiling_timestamps: Any | None = None,
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
    geometry_rows = tuple(geometries or ())
    n = int(np.asarray(timestamps).reshape(-1).shape[0])
    if stats_sink is not None:
        # Baseline for the degenerate early returns below; the main path overwrites every key.
        stats_sink.update(dict.fromkeys(_DEGENERATE_STATS_KEYS, 0))
        stats_sink.update(
            region_table_parallelism=1,
            region_table_build_work_ms=0.0,
            region_group_reduce_work_ms=0.0,
            geometries_in=int(len(geometry_rows)),
        )
    if not geometry_rows:
        return ()
    if n <= 0:
        return tuple(FgResponseFrontierResult((_EMPTY_SURFACE,), {}, 0, 0, 0, 0, 1, 1, 0, 0.0) for _ in geometry_rows)
    ts, perfect_ts, great_ts, floor_ts, great_floor_ts, late_great_floor_ts, exit_ceiling_ts, lane_arr = song_arrays(
        timestamps, perfect_candidate_timestamps, great_candidate_timestamps, perfect_floor_timestamps,
        great_floor_timestamps, late_great_floor_timestamps, exit_ceiling_timestamps, lanes,
    )
    prefix_perfect_hit, prefix_perfect_valid, prefix_late_hit, prefix_late_valid = (
        _rb_numba._numba_build_prefix_activation_hit_tables(int(n), ts, perfect_ts, great_ts, late_great_floor_ts)
    )
    prepared = _prepared_geometries(geometry_rows, bool(use_forced_great_timing))

    out: list[FgResponseFrontierResult | None] = [None] * len(geometry_rows)
    # ONE end-index precompute per song build: the canonicalization covers every unique
    # real_fever_time of the whole request, so the streamed region-table groups below never
    # rebuild end tables (pre-song-context, each per-group call re-derived its rt subset).
    canonical = _canonicalize_first_only_prepared_items_with_end_indices(
        prepared=prepared,
        timestamps=ts,
        perfect_candidate_timestamps=perfect_ts,
        great_candidate_timestamps=great_ts,
        perfect_floor_timestamps=floor_ts,
        great_floor_timestamps=great_floor_ts,
        prefix_perfect_hit=prefix_perfect_hit,
        prefix_late_hit=prefix_late_hit,
        exit_ceiling_timestamps=exit_ceiling_ts,
        late_great_floor_timestamps=late_great_floor_ts,
        use_forced_great_timing=bool(use_forced_great_timing),
        lanes=lane_arr,
    )
    prepared = canonical.prepared
    duplicate_sources_by_source = canonical.duplicate_sources_by_source
    # The region-run core table depends on a geometry only through (raw fill, non-Fever base), so each key's table is
    # built once and shared by its fever-time variants (scheduling and memory admission: the scheduler module).
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
    workspace_workers = max(
        _resolve_first_only_reducer_threads(len(grouped_items)),
        max(
            (_resolve_first_only_reducer_threads(len(group_items)) for group_items in grouped_items.values()),
            default=1,
        ),
    )
    _admit_first_frontier_workspace(workspace_plan, worker_count=workspace_workers)

    # Without forced-Great timing every region key shares one contentless table.
    empty_region_table = None if bool(use_forced_great_timing) else (
        np.zeros(int(n) + 2, dtype=np.int64), *(np.empty(0, dtype=np.int32) for _ in range(7)),
    )

    group_results, schedule_stats = _schedule_first_frontier_region_groups(
        grouped_items=grouped_items,
        context=_FirstFrontierGroupContext(
            n=int(n),
            timestamps=ts,
            perfect_candidate_timestamps=perfect_ts,
            great_candidate_timestamps=great_ts,
            perfect_floor_timestamps=floor_ts,
            great_floor_timestamps=great_floor_ts,
            late_great_floor_timestamps=late_great_floor_ts,
            lanes=lane_arr,
            prefix_perfect_hit=prefix_perfect_hit,
            prefix_perfect_valid=prefix_perfect_valid,
            prefix_late_hit=prefix_late_hit,
            prefix_late_valid=prefix_late_valid,
            canonical=canonical,
            use_forced_great_timing=bool(use_forced_great_timing),
            empty_region_table=empty_region_table,
            workspace_plan=workspace_plan,
            early_exit_min_fill=early_exit_min_fill(floor_ts, perfect_ts),
            no_early_exit_e=np.full_like(canonical.capped_perfect_exit_e, int(n)),
        ),
    )
    for result_rows in group_results:
        for source_idx, frontier in result_rows:
            for duplicate_source_idx in duplicate_sources_by_source[int(source_idx)]:
                out[int(duplicate_source_idx)] = frontier

    if stats_sink is not None:
        stats_sink.update(
            dataclasses.asdict(schedule_stats),
            end_table_precomputes=1,
            workspace_allocations=int(workspace_plan.allocations),
            workspace_bytes=int(workspace_plan.allocated_bytes),
            region_table_groups=int(len(grouped_items)),
            geometries_in=int(len(geometry_rows)),
            geometries_canonical=int(len(prepared)),
            pair_mod_bound=int(workspace_plan.pair_mod_bound),
        )

    missing = [idx for idx, frontier in enumerate(out) if frontier is None]
    if missing:
        raise ValueError(f"FG response frontier GPU batch missed geometry indices: {missing[:8]}")
    return tuple(frontier for frontier in out if frontier is not None)
