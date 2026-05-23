from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.solver.response_envelope_prune import (
    _GRID,
    _fast_path_blocker,
    _timeline_pack_grid,
    _timing_envelopes_for_cells,
)

MAX_LOCAL_GEAR_RESPONSE_MATRIX_CELLS = 64_000_000
MAX_LOCAL_GEAR_RESPONSE_BUCKET_CELLS = 8_000_000


@dataclass(frozen=True)
class GearLocalResponsePruneStats:
    enabled: bool
    reason: str
    candidates_in: int
    candidates_out: int
    pruned: int
    seconds_total: float
    seconds_timing: float = 0.0
    seconds_index: float = 0.0
    seconds_query: float = 0.0
    gear_rows: int = 0
    matrix_cells: int = 0
    mini_groups: int = 0
    response_buckets: int = 0
    timing_cells: int = 0
    timing_packs: int = 0
    dominance_pairs: int = 0
    response_equal_hits: int = 0
    skipped_buckets: int = 0


def gear_response_phase_counts(stats: GearLocalResponsePruneStats) -> dict[str, int]:
    return {
        "gear_response_enabled": 1 if stats.enabled else 0,
        "gear_response_candidates_in": int(stats.candidates_in),
        "gear_response_candidates_out": int(stats.candidates_out),
        "gear_response_pruned": int(stats.pruned),
        "gear_response_gear_rows": int(stats.gear_rows),
        "gear_response_matrix_cells": int(stats.matrix_cells),
        "gear_response_mini_groups": int(stats.mini_groups),
        "gear_response_response_buckets": int(stats.response_buckets),
        "gear_response_timing_cells": int(stats.timing_cells),
        "gear_response_timing_packs": int(stats.timing_packs),
        "gear_response_dominance_pairs": int(stats.dominance_pairs),
        "gear_response_equal_hits": int(stats.response_equal_hits),
        "gear_response_skipped_buckets": int(stats.skipped_buckets),
    }


def gear_response_phase_seconds(stats: GearLocalResponsePruneStats) -> dict[str, float]:
    return {
        "gear_response_prune_cpu": float(stats.seconds_total),
        "gear_response.timing": float(stats.seconds_timing),
        "gear_response.index": float(stats.seconds_index),
        "gear_response.query": float(stats.seconds_query),
    }


def prune_local_gear_response_pairs(
    *,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    gear_points: np.ndarray,
    mini_points: np.ndarray,
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    flags: dict[str, int],
    max_matrix_cells: int = MAX_LOCAL_GEAR_RESPONSE_MATRIX_CELLS,
) -> tuple[np.ndarray, np.ndarray, GearLocalResponsePruneStats]:
    """Delete pair-local gear rows with the same mini and exact timing response.

    For a fixed mini row, gear ``a`` can replay gear ``b`` when ``a`` is no worse
    in PP/CM/FM/lane-base and both pairs expose the same timing-response envelope
    to the non-timing allocator. The deletion is pair-local: the gear row itself is
    not removed globally, and the source pair must already be present in the input
    candidate set.
    """

    started = time.perf_counter()
    pg = np.asarray(pair_gear_idx, dtype=np.int32).reshape(-1)
    pm = np.asarray(pair_mini_idx, dtype=np.int32).reshape(-1)
    n = int(pg.shape[0])
    if n <= 1:
        return pair_gear_idx, pair_mini_idx, _stats(False, "too_few_candidates", n, n, started)
    if int(pm.shape[0]) != n:
        raise ValueError("pair_gear_idx and pair_mini_idx must have the same length")

    gp = np.asarray(gear_points, dtype=np.int32)
    mp = np.asarray(mini_points, dtype=np.int32)
    if gp.ndim != 2 or int(gp.shape[1]) != 6:
        return pair_gear_idx, pair_mini_idx, _stats(False, "gear_points_shape_not_6d", n, n, started)
    if mp.ndim != 2 or int(mp.shape[1]) != 5:
        return pair_gear_idx, pair_mini_idx, _stats(False, "mini_points_shape_not_5d", n, n, started)
    if n > 0:
        min_pg = int(np.min(pg))
        max_pg = int(np.max(pg))
        min_pm = int(np.min(pm))
        max_pm = int(np.max(pm))
        if min_pg < 0 or max_pg >= int(gp.shape[0]) or min_pm < 0 or max_pm >= int(mp.shape[0]):
            raise ValueError("pair indices are out of bounds for gear_points/mini_points")

    unique_probe_started = time.perf_counter()
    present_gears = np.zeros(int(gp.shape[0]), dtype=np.bool_)
    present_gears[pg] = True
    gear_rows = int(np.count_nonzero(present_gears))
    if gear_rows * gear_rows > int(max_matrix_cells):
        return pair_gear_idx, pair_mini_idx, GearLocalResponsePruneStats(
            enabled=False,
            reason="gear_response_matrix_too_large",
            candidates_in=n,
            candidates_out=n,
            pruned=0,
            seconds_total=float(time.perf_counter() - started),
            seconds_index=float(time.perf_counter() - unique_probe_started),
            gear_rows=gear_rows,
            matrix_cells=int(gear_rows * gear_rows),
        )

    reason = _fast_path_blocker(flags=flags, ref_arrays=ref_arrays)
    if reason:
        return pair_gear_idx, pair_mini_idx, _stats(False, reason, n, n, started)

    present_minis = np.zeros(int(mp.shape[0]), dtype=np.bool_)
    present_minis[pm] = True
    unique_gears = np.flatnonzero(present_gears).astype(np.int32, copy=False)
    unique_minis = np.flatnonzero(present_minis).astype(np.int32, copy=False)

    base = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    if _has_negative_pre_gem_state(base=base, gear_points=gp[unique_gears], mini_points=mp[unique_minis]):
        return pair_gear_idx, pair_mini_idx, _stats(False, "negative_pre_gem_stat", n, n, started)

    row_to_local = np.full(int(gp.shape[0]), -1, dtype=np.int32)
    row_to_local[unique_gears] = np.arange(gear_rows, dtype=np.int32)
    local_pg = row_to_local[pg]
    if np.any(local_pg < 0):
        raise ValueError("gear response local index construction failed")

    index_started = time.perf_counter()
    gear_dominates = _gear_non_timing_dominance_matrix(gp[unique_gears], tie_index=unique_gears)
    seconds_index = time.perf_counter() - index_started
    if not np.any(gear_dominates):
        return (
            pg,
            pm,
            GearLocalResponsePruneStats(
                enabled=True,
                reason="no_gear_dominance",
                candidates_in=n,
                candidates_out=n,
                pruned=0,
                seconds_total=float(time.perf_counter() - started),
                seconds_index=float(seconds_index),
                gear_rows=gear_rows,
                matrix_cells=int(gear_rows * gear_rows),
            ),
        )

    timing_started = time.perf_counter()
    response_ids, timing_cells, timing_packs = _pair_response_signature_ids(
        pair_gear_idx=pg,
        pair_mini_idx=pm,
        gear_points=gp,
        mini_points=mp,
        base_fixed_stats_arr=base,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    seconds_timing = time.perf_counter() - timing_started

    query_started = time.perf_counter()
    keep, query_counts = _prune_pairs_by_local_gear_response(
        pair_gear_idx=local_pg.astype(np.int32, copy=False),
        pair_mini_idx=pm,
        pair_response_ids=response_ids,
        gear_dominates=gear_dominates,
    )
    seconds_query = time.perf_counter() - query_started

    if not np.any(keep):
        keep[0] = True
    out_g = pg[keep].astype(np.int32, copy=False)
    out_m = pm[keep].astype(np.int32, copy=False)
    pruned = int(n - int(out_g.shape[0]))
    reason_out = "certified" if pruned > 0 else "no_certified_dominance"
    return (
        out_g,
        out_m,
        GearLocalResponsePruneStats(
            enabled=True,
            reason=reason_out,
            candidates_in=n,
            candidates_out=int(out_g.shape[0]),
            pruned=pruned,
            seconds_total=float(time.perf_counter() - started),
            seconds_timing=float(seconds_timing),
            seconds_index=float(seconds_index),
            seconds_query=float(seconds_query),
            gear_rows=gear_rows,
            matrix_cells=int(gear_rows * gear_rows),
            mini_groups=int(query_counts["mini_groups"]),
            response_buckets=int(query_counts["response_buckets"]),
            timing_cells=int(timing_cells),
            timing_packs=int(timing_packs),
            dominance_pairs=int(query_counts["dominance_pairs"]),
            response_equal_hits=int(query_counts["response_equal_hits"]),
            skipped_buckets=int(query_counts["skipped_buckets"]),
        ),
    )


def _stats(
    enabled: bool,
    reason: str,
    candidates_in: int,
    candidates_out: int,
    started: float,
) -> GearLocalResponsePruneStats:
    return GearLocalResponsePruneStats(
        enabled=bool(enabled),
        reason=str(reason),
        candidates_in=int(candidates_in),
        candidates_out=int(candidates_out),
        pruned=int(candidates_in) - int(candidates_out),
        seconds_total=float(time.perf_counter() - float(started)),
    )


def _has_negative_pre_gem_state(*, base: np.ndarray, gear_points: np.ndarray, mini_points: np.ndarray) -> bool:
    base_arr = np.asarray(base, dtype=np.int32).reshape(-1)
    if base_arr.shape[0] >= 5 and np.any(base_arr[:5] < 0):
        return True
    gp = np.asarray(gear_points, dtype=np.int32)
    mp = np.asarray(mini_points, dtype=np.int32)
    return bool(np.any(gp[:, :5] < 0) or np.any(gp[:, 5] < 0) or np.any(mp[:, :5] < 0))


def _gear_non_timing_dominance_matrix(gear_points: np.ndarray, *, tie_index: np.ndarray) -> np.ndarray:
    gp = np.asarray(gear_points, dtype=np.int32)
    if gp.ndim != 2 or int(gp.shape[1]) != 6:
        raise ValueError("gear_points must have shape (n, 6)")
    key = gp[:, (0, 1, 2, 5)]
    ge = np.all(key[:, None, :] >= key[None, :, :], axis=2)
    strict = np.any(key[:, None, :] > key[None, :, :], axis=2)
    tie = np.asarray(tie_index, dtype=np.int32).reshape(-1)
    if int(tie.shape[0]) != int(gp.shape[0]):
        raise ValueError("tie_index must align with gear_points")
    return ge & (strict | (tie[:, None] < tie[None, :]))


def _pair_response_signature_ids(
    *,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    gear_points: np.ndarray,
    mini_points: np.ndarray,
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
) -> tuple[np.ndarray, int, int]:
    cells = _pair_start_cells(
        pair_gear_idx=pair_gear_idx,
        pair_mini_idx=pair_mini_idx,
        gear_points=gear_points,
        mini_points=mini_points,
        base_fixed_stats_arr=base_fixed_stats_arr,
    )
    present_cells = np.unique(cells.astype(np.int32, copy=False))
    cell_to_row = np.full(int(_GRID) * int(_GRID), -1, dtype=np.int32)
    cell_to_row[present_cells] = np.arange(int(present_cells.shape[0]), dtype=np.int32)
    cell_pack, _pack_bits, _pack_body_fever, pack_body_normal = _timeline_pack_grid(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    env = _timing_envelopes_for_cells(
        cells=present_cells,
        cell_pack=cell_pack,
        pack_count=int(pack_body_normal.shape[0]),
    )
    signature_ids = _response_signature_ids(env)
    pair_rows = cell_to_row[cells]
    if np.any(pair_rows < 0):
        raise ValueError("gear response timing index missing a pair start cell")
    return signature_ids[pair_rows].astype(np.int32, copy=False), int(present_cells.shape[0]), int(pack_body_normal.shape[0])


def _pair_start_cells(
    *,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    gear_points: np.ndarray,
    mini_points: np.ndarray,
    base_fixed_stats_arr: np.ndarray,
) -> np.ndarray:
    base = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    base_ft = int(base[3]) if base.shape[0] > 3 else 0
    base_ff = int(base[4]) if base.shape[0] > 4 else 0
    gp = np.asarray(gear_points, dtype=np.int32)
    mp = np.asarray(mini_points, dtype=np.int32)
    gi = np.asarray(pair_gear_idx, dtype=np.int32)
    mi = np.asarray(pair_mini_idx, dtype=np.int32)
    pair_ft = np.minimum(int(MAX_STAT_INDEX), gp[gi, 3] + mp[mi, 2]) + int(base_ft)
    pair_ff = np.minimum(int(MAX_STAT_INDEX), gp[gi, 4] + mp[mi, 3]) + int(base_ff)
    start_ft = np.minimum(int(MAX_STAT_INDEX), np.maximum(0, pair_ft))
    start_ff = np.minimum(int(MAX_STAT_INDEX), np.maximum(0, pair_ff))
    return (start_ft * int(_GRID) + start_ff).astype(np.int32, copy=False)


def _response_signature_ids(env: np.ndarray) -> np.ndarray:
    arr = np.ascontiguousarray(np.asarray(env, dtype=np.int8))
    if arr.ndim != 2 or int(arr.shape[0]) == 0:
        return np.zeros(0, dtype=np.int32)
    row_dtype = np.dtype((np.void, int(arr.dtype.itemsize) * int(arr.shape[1])))
    row_view = arr.view(row_dtype).reshape(arr.shape[0])
    _unique, inverse = np.unique(row_view, return_inverse=True)
    return inverse.astype(np.int32, copy=False)


def _prune_pairs_by_local_gear_response(
    *,
    pair_gear_idx: np.ndarray,
    pair_mini_idx: np.ndarray,
    pair_response_ids: np.ndarray,
    gear_dominates: np.ndarray,
    max_bucket_cells: int = MAX_LOCAL_GEAR_RESPONSE_BUCKET_CELLS,
) -> tuple[np.ndarray, dict[str, int]]:
    pg = np.asarray(pair_gear_idx, dtype=np.int32).reshape(-1)
    pm = np.asarray(pair_mini_idx, dtype=np.int32).reshape(-1)
    response = np.asarray(pair_response_ids, dtype=np.int32).reshape(-1)
    n = int(pg.shape[0])
    if int(pm.shape[0]) != n or int(response.shape[0]) != n:
        raise ValueError("pair arrays and response ids must have the same length")
    dom = np.asarray(gear_dominates, dtype=np.bool_)
    if dom.ndim != 2 or int(dom.shape[0]) != int(dom.shape[1]):
        raise ValueError("gear_dominates must be a square matrix")
    if np.any(pg < 0) or np.any(pg >= int(dom.shape[0])):
        raise ValueError("pair_gear_idx contains rows outside gear_dominates")

    keep = np.ones(n, dtype=np.bool_)
    if n <= 1:
        return keep, _query_counts()

    order = np.lexsort((response.astype(np.int64, copy=False), pm.astype(np.int64, copy=False)))
    sorted_pm = pm[order]
    sorted_response = response[order]
    group_starts = np.flatnonzero(
        np.r_[True, (sorted_pm[1:] != sorted_pm[:-1]) | (sorted_response[1:] != sorted_response[:-1])]
    )
    group_ends = np.r_[group_starts[1:], n]

    mini_groups = int(np.unique(pm).shape[0])
    response_buckets = int(group_starts.shape[0])
    dominance_pairs = 0
    response_equal_hits = 0
    skipped_buckets = 0

    for start, end in zip(group_starts.tolist(), group_ends.tolist(), strict=True):
        size = int(end) - int(start)
        if size <= 1:
            continue
        if size * size > int(max_bucket_cells):
            skipped_buckets += 1
            continue
        loc = order[start:end]
        gears = pg[loc]
        cert = dom[np.ix_(gears, gears)]
        cert_count = int(np.count_nonzero(cert))
        dominance_pairs += cert_count
        response_equal_hits += cert_count
        if cert_count <= 0:
            continue
        dominated = np.any(cert, axis=0)
        if np.any(dominated):
            keep[loc[dominated]] = False

    return keep, _query_counts(
        mini_groups=mini_groups,
        response_buckets=response_buckets,
        dominance_pairs=dominance_pairs,
        response_equal_hits=response_equal_hits,
        skipped_buckets=skipped_buckets,
    )


def _query_counts(
    *,
    mini_groups: int = 0,
    response_buckets: int = 0,
    dominance_pairs: int = 0,
    response_equal_hits: int = 0,
    skipped_buckets: int = 0,
) -> dict[str, int]:
    return {
        "mini_groups": int(mini_groups),
        "response_buckets": int(response_buckets),
        "dominance_pairs": int(dominance_pairs),
        "response_equal_hits": int(response_equal_hits),
        "skipped_buckets": int(skipped_buckets),
    }
