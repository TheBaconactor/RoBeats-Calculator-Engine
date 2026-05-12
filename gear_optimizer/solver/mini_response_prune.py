from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX, TOTAL_GEM_BUDGET
from gear_optimizer.core.jit_setup import HAS_NUMBA, jit
from gear_optimizer.solver.response_envelope_prune import (
    _GRID,
    _env_active_csr,
    _fast_path_blocker,
    _mini_points_have_no_pp,
    _timeline_pack_grid,
    _timing_envelopes_for_cells,
)

MAX_LOCAL_RESPONSE_MATRIX_CELLS = 8_000_000


@dataclass(frozen=True)
class MiniResponsePruneStats:
    enabled: bool
    reason: str
    minis_in: int
    minis_out: int
    pruned: int
    seconds_total: float
    seconds_timing: float = 0.0
    seconds_query: float = 0.0
    gear_timing_cells: int = 0
    start_cells: int = 0
    timing_packs: int = 0
    candidate_pairs: int = 0
    timing_cover_hits: int = 0
    local_candidate_pairs: int = 0
    local_timing_cover_hits: int = 0
    local_pruned_entries: int = 0
    seconds_local_query: float = 0.0
    local_reason: str = ""


@dataclass(frozen=True)
class MiniLocalResponseFilter:
    cell_to_row: np.ndarray
    allowed: np.ndarray


@dataclass(frozen=True)
class _MiniTimingResponseIndex:
    cells: np.ndarray
    cell_to_row: np.ndarray
    env: np.ndarray
    needed_offsets: np.ndarray
    needed_packs: np.ndarray
    needed_requirements: np.ndarray
    pack_count: int


def mini_response_phase_counts(stats: MiniResponsePruneStats) -> dict[str, int]:
    return {
        "mini_response_enabled": 1 if stats.enabled else 0,
        "mini_response_minis_in": int(stats.minis_in),
        "mini_response_minis_out": int(stats.minis_out),
        "mini_response_pruned": int(stats.pruned),
        "mini_response_gear_timing_cells": int(stats.gear_timing_cells),
        "mini_response_start_cells": int(stats.start_cells),
        "mini_response_timing_packs": int(stats.timing_packs),
        "mini_response_candidate_pairs": int(stats.candidate_pairs),
        "mini_response_timing_cover_hits": int(stats.timing_cover_hits),
        "mini_response_local_candidate_pairs": int(stats.local_candidate_pairs),
        "mini_response_local_timing_cover_hits": int(stats.local_timing_cover_hits),
        "mini_response_local_pruned_entries": int(stats.local_pruned_entries),
    }


def mini_response_phase_seconds(stats: MiniResponsePruneStats) -> dict[str, float]:
    return {
        "mini_response_prune_cpu": float(stats.seconds_total),
        "mini_response.timing": float(stats.seconds_timing),
        "mini_response.query": float(stats.seconds_query),
        "mini_response.local_query": float(stats.seconds_local_query),
    }


def prune_mini_response_envelope(
    *,
    gear_points: np.ndarray,
    mini_points: np.ndarray,
    mini_codes: np.ndarray,
    mini_ids: np.ndarray,
    gpu_arrays: dict[str, np.ndarray],
    base_fixed_stats_arr: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    flags: dict[str, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, MiniResponsePruneStats, MiniLocalResponseFilter | None]:
    started = time.perf_counter()
    mp = np.asarray(mini_points, dtype=np.int32)
    n = int(mp.shape[0]) if mp.ndim == 2 else 0
    if n <= 1:
        return mini_points, mini_codes, mini_ids, _stats(False, "too_few_minis", n, n, started), None
    if mp.ndim != 2 or int(mp.shape[1]) != 5:
        return mini_points, mini_codes, mini_ids, _stats(False, "mini_points_shape_not_5d", n, n, started), None

    gp = np.asarray(gear_points, dtype=np.int32)
    if gp.ndim != 2 or int(gp.shape[1]) != 6 or int(gp.shape[0]) <= 0:
        return mini_points, mini_codes, mini_ids, _stats(False, "gear_points_shape_not_6d", n, n, started), None

    reason = _fast_path_blocker(flags=flags, ref_arrays=ref_arrays)
    if reason:
        return mini_points, mini_codes, mini_ids, _stats(False, reason, n, n, started), None

    item_stats = np.asarray(gpu_arrays.get("item_stats"), dtype=np.int32)
    if not _mini_points_have_no_pp(mini_ids=mini_ids, item_stats=item_stats):
        return mini_points, mini_codes, mini_ids, _stats(False, "mini_pp_not_in_frontier_state", n, n, started), None

    base = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    base_ft = int(base[3]) if base.shape[0] > 3 else 0
    base_ff = int(base[4]) if base.shape[0] > 4 else 0
    if base_ft < 0 or base_ff < 0 or np.any(gp[:, 3:5] < 0) or np.any(mp[:, 0:5] < 0):
        return mini_points, mini_codes, mini_ids, _stats(False, "negative_pre_gem_stat", n, n, started), None

    gear_cells = _gear_timing_cells_with_base(gear_points=gp, base_ft=base_ft, base_ff=base_ff)
    gear_cell_to_row = np.full(int(_GRID) * int(_GRID), -1, dtype=np.int32)
    gear_cell_to_row[gear_cells] = np.arange(gear_cells.shape[0], dtype=np.int32)
    start_cells_by_mini = _start_cells_by_mini(gear_cells=gear_cells, mini_points=mp)

    timing_started = time.perf_counter()
    timing = _build_exact_timing_response_index(
        present_cells=np.unique(start_cells_by_mini.reshape(-1).astype(np.int32, copy=False)),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    start_rows_by_mini = timing.cell_to_row[start_cells_by_mini]
    seconds_timing = time.perf_counter() - timing_started

    query_started = time.perf_counter()
    prune_mask, candidate_pairs, cover_hits = _find_dominated_minis(
        mini_points=mp,
        start_rows_by_mini=start_rows_by_mini,
        timing=timing,
        raw_pack_by_row=_raw_pack_by_row(timing.env),
    )
    seconds_query = time.perf_counter() - query_started

    keep = ~prune_mask
    if not np.any(keep):
        keep[0] = True
    out_points = np.asarray(mini_points)[keep]
    out_codes = np.asarray(mini_codes)[keep]
    out_ids = np.asarray(mini_ids)[keep]

    local_started = time.perf_counter()
    local_filter, local_candidate_pairs, local_cover_hits, local_reason = _build_local_response_filter(
        mini_points=mp[keep],
        start_rows_by_mini=start_rows_by_mini[keep],
        timing=timing,
        raw_pack_by_row=_raw_pack_by_row(timing.env),
        gear_cell_to_row=gear_cell_to_row,
    )
    seconds_local_query = time.perf_counter() - local_started
    local_pruned_entries = 0
    if local_filter is not None:
        local_pruned_entries = int(local_filter.allowed.size - np.count_nonzero(local_filter.allowed))

    reason = "certified" if int(n - int(out_points.shape[0])) > 0 or local_pruned_entries > 0 else "no_certified_dominance"
    elapsed = time.perf_counter() - started
    return (
        out_points,
        out_codes,
        out_ids,
        MiniResponsePruneStats(
            enabled=True,
            reason=reason,
            minis_in=n,
            minis_out=int(out_points.shape[0]),
            pruned=int(n - int(out_points.shape[0])),
            seconds_total=float(elapsed),
            seconds_timing=float(seconds_timing),
            seconds_query=float(seconds_query),
            gear_timing_cells=int(gear_cells.shape[0]),
            start_cells=int(timing.cells.shape[0]),
            timing_packs=int(timing.pack_count),
            candidate_pairs=int(candidate_pairs),
            timing_cover_hits=int(cover_hits),
            local_candidate_pairs=int(local_candidate_pairs),
            local_timing_cover_hits=int(local_cover_hits),
            local_pruned_entries=int(local_pruned_entries),
            seconds_local_query=float(seconds_local_query),
            local_reason=str(local_reason),
        ),
        local_filter,
    )


def mini_local_filter_gear_rows(
    *,
    local_filter: MiniLocalResponseFilter,
    gear_points: np.ndarray,
    base_fixed_stats_arr: np.ndarray,
) -> np.ndarray:
    gp = np.asarray(gear_points, dtype=np.int32)
    base = np.asarray(base_fixed_stats_arr, dtype=np.int32).reshape(-1)
    base_ft = int(base[3]) if base.shape[0] > 3 else 0
    base_ff = int(base[4]) if base.shape[0] > 4 else 0
    ft = np.minimum(int(MAX_STAT_INDEX), int(base_ft) + gp[:, 3].astype(np.int32, copy=False))
    ff = np.minimum(int(MAX_STAT_INDEX), int(base_ff) + gp[:, 4].astype(np.int32, copy=False))
    rows = np.asarray(local_filter.cell_to_row, dtype=np.int32)[(ft * int(_GRID) + ff).astype(np.int32, copy=False)]
    if np.any(rows < 0):
        raise ValueError("mini local response filter missing a gear timing cell")
    return rows.astype(np.int32, copy=False)


def _stats(
    enabled: bool,
    reason: str,
    minis_in: int,
    minis_out: int,
    started: float,
    local_reason: str = "",
) -> MiniResponsePruneStats:
    return MiniResponsePruneStats(
        enabled=bool(enabled),
        reason=str(reason),
        minis_in=int(minis_in),
        minis_out=int(minis_out),
        pruned=int(minis_in) - int(minis_out),
        seconds_total=float(time.perf_counter() - float(started)),
        local_reason=str(local_reason),
    )


def _gear_timing_cells_with_base(*, gear_points: np.ndarray, base_ft: int, base_ff: int) -> np.ndarray:
    gp = np.asarray(gear_points, dtype=np.int32)
    ft = np.minimum(int(MAX_STAT_INDEX), int(base_ft) + gp[:, 3].astype(np.int32, copy=False))
    ff = np.minimum(int(MAX_STAT_INDEX), int(base_ff) + gp[:, 4].astype(np.int32, copy=False))
    return np.unique((ft * int(_GRID) + ff).astype(np.int32, copy=False))


def _start_cells_by_mini(*, gear_cells: np.ndarray, mini_points: np.ndarray) -> np.ndarray:
    cells = np.asarray(gear_cells, dtype=np.int32)
    mp = np.asarray(mini_points, dtype=np.int32)
    gear_ft = cells // int(_GRID)
    gear_ff = cells % int(_GRID)
    start_ft = np.minimum(int(MAX_STAT_INDEX), mp[:, 2:3] + gear_ft.reshape(1, -1))
    start_ff = np.minimum(int(MAX_STAT_INDEX), mp[:, 3:4] + gear_ff.reshape(1, -1))
    return (start_ft * int(_GRID) + start_ff).astype(np.int32, copy=False)


def _build_exact_timing_response_index(
    *,
    present_cells: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
) -> _MiniTimingResponseIndex:
    cells = np.asarray(present_cells, dtype=np.int32)
    cell_to_row = np.full(int(_GRID) * int(_GRID), -1, dtype=np.int32)
    cell_to_row[cells] = np.arange(cells.shape[0], dtype=np.int32)

    cell_pack, _pack_bits, _pack_body_fever, pack_body_normal = _timeline_pack_grid(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
    )
    pack_count = int(pack_body_normal.shape[0])
    env = _timing_envelopes_for_cells(cells=cells, cell_pack=cell_pack, pack_count=pack_count)
    needed_offsets, needed_packs, needed_requirements = _env_active_csr(env)
    return _MiniTimingResponseIndex(
        cells=cells,
        cell_to_row=cell_to_row,
        env=env,
        needed_offsets=needed_offsets,
        needed_packs=needed_packs,
        needed_requirements=needed_requirements,
        pack_count=pack_count,
    )


def _find_dominated_minis(
    *,
    mini_points: np.ndarray,
    start_rows_by_mini: np.ndarray,
    timing: _MiniTimingResponseIndex,
    raw_pack_by_row: np.ndarray,
) -> tuple[np.ndarray, int, int]:
    mp = np.asarray(mini_points, dtype=np.int32)
    n = int(mp.shape[0])
    cm = mp[:, 0]
    fm = mp[:, 1]
    base = mp[:, 4]

    strength = (cm.astype(np.int64) << 40) + (fm.astype(np.int64) << 24) + base.astype(np.int64)
    source_order = np.argsort(-strength, kind="stable")
    if HAS_NUMBA:
        prune_mask = np.zeros(n, dtype=np.bool_)
        counts = _find_dominated_minis_jit(
            cm.astype(np.int32, copy=False),
            fm.astype(np.int32, copy=False),
            base.astype(np.int32, copy=False),
            source_order.astype(np.int32, copy=False),
            np.asarray(start_rows_by_mini, dtype=np.int32),
            np.asarray(raw_pack_by_row, dtype=np.int32),
            timing.env,
            timing.needed_offsets,
            timing.needed_packs,
            timing.needed_requirements,
            prune_mask,
        )
        return prune_mask, int(counts[0]), int(counts[1])

    prune_mask = np.zeros(n, dtype=np.bool_)
    candidate_pairs = 0
    cover_hits = 0
    source_order_list = source_order.tolist()
    for b in range(n):
        for a in source_order_list:
            if int(a) == int(b):
                continue
            if cm[a] < cm[b] or fm[a] < fm[b] or base[a] < base[b]:
                continue
            strict = cm[a] > cm[b] or fm[a] > fm[b] or base[a] > base[b]
            if not strict and int(a) >= int(b):
                continue
            candidate_pairs += 1
            if not np.array_equal(raw_pack_by_row[start_rows_by_mini[a]], raw_pack_by_row[start_rows_by_mini[b]]):
                continue
            if _mini_timing_matches_all_gear_cells(
                source_rows=start_rows_by_mini[a],
                target_rows=start_rows_by_mini[b],
                timing=timing,
            ):
                prune_mask[b] = True
                cover_hits += 1
                break
    return prune_mask, int(candidate_pairs), int(cover_hits)


@jit(nopython=True, cache=True)
def _find_dominated_minis_jit(
    cm: np.ndarray,
    fm: np.ndarray,
    base: np.ndarray,
    source_order: np.ndarray,
    start_rows_by_mini: np.ndarray,
    raw_pack_by_row: np.ndarray,
    env: np.ndarray,
    needed_offsets: np.ndarray,
    needed_packs: np.ndarray,
    needed_requirements: np.ndarray,
    prune_mask: np.ndarray,
) -> np.ndarray:
    n = cm.shape[0]
    gear_cells = start_rows_by_mini.shape[1]
    candidate_pairs = 0
    cover_hits = 0

    for b in range(n):
        for order_idx in range(n):
            a = source_order[order_idx]
            if a == b:
                continue
            if cm[a] < cm[b] or fm[a] < fm[b] or base[a] < base[b]:
                continue
            strict = cm[a] > cm[b] or fm[a] > fm[b] or base[a] > base[b]
            if not strict and a >= b:
                continue
            candidate_pairs += 1

            ok = True
            for gear_idx in range(gear_cells):
                if raw_pack_by_row[start_rows_by_mini[a, gear_idx]] != raw_pack_by_row[start_rows_by_mini[b, gear_idx]]:
                    ok = False
                    break
            if not ok:
                continue

            for gear_idx in range(gear_cells):
                source_row = start_rows_by_mini[a, gear_idx]
                target_row = start_rows_by_mini[b, gear_idx]
                start = needed_offsets[target_row]
                end = needed_offsets[target_row + 1]
                for pos in range(start, end):
                    pack = needed_packs[pos]
                    req = needed_requirements[pos]
                    if env[source_row, pack] < req:
                        ok = False
                        break
                if not ok:
                    break

            if ok:
                prune_mask[b] = True
                cover_hits += 1
                break

    return np.asarray((candidate_pairs, cover_hits), dtype=np.int64)


def _build_local_response_filter(
    *,
    mini_points: np.ndarray,
    start_rows_by_mini: np.ndarray,
    timing: _MiniTimingResponseIndex,
    raw_pack_by_row: np.ndarray,
    gear_cell_to_row: np.ndarray,
) -> tuple[MiniLocalResponseFilter | None, int, int, str]:
    del raw_pack_by_row
    mp = np.asarray(mini_points, dtype=np.int32)
    n = int(mp.shape[0]) if mp.ndim == 2 else 0
    rows = np.asarray(start_rows_by_mini, dtype=np.int32)
    if n <= 1 or rows.ndim != 2 or int(rows.shape[0]) != n or int(rows.shape[1]) <= 0:
        return None, 0, 0, "too_small"

    estimated_cells = int(n) * int(n + int(rows.shape[1]))
    if estimated_cells > int(MAX_LOCAL_RESPONSE_MATRIX_CELLS):
        return None, 0, 0, "local_filter_too_large"

    cm = mp[:, 0]
    fm = mp[:, 1]
    base = mp[:, 4]
    strict = (cm[:, None] > cm[None, :]) | (fm[:, None] > fm[None, :]) | (base[:, None] > base[None, :])
    tie = np.arange(n, dtype=np.int32)[:, None] < np.arange(n, dtype=np.int32)[None, :]
    non_timing_dominates = (
        (cm[:, None] >= cm[None, :])
        & (fm[:, None] >= fm[None, :])
        & (base[:, None] >= base[None, :])
        & (strict | tie)
    )
    candidate_pairs = int(np.count_nonzero(non_timing_dominates)) * int(rows.shape[1])
    if not np.any(non_timing_dominates):
        return None, candidate_pairs, 0, "no_local_certified_dominance"

    response_ids = _env_signature_ids(timing.env)[rows]
    allowed = np.ones((int(rows.shape[1]), n), dtype=np.bool_)
    cover_hits = 0
    for gear_idx in range(int(rows.shape[1])):
        response = response_ids[:, gear_idx]
        same_response = response[:, None] == response[None, :]
        dominated = np.any(non_timing_dominates & same_response, axis=0)
        if np.any(dominated):
            allowed[gear_idx, dominated] = False
            cover_hits += int(np.count_nonzero(dominated))
    if np.all(allowed):
        return None, int(candidate_pairs), int(cover_hits), "no_local_certified_dominance"
    return (
        MiniLocalResponseFilter(cell_to_row=np.asarray(gear_cell_to_row, dtype=np.int32), allowed=allowed),
        int(candidate_pairs),
        int(cover_hits),
        "certified",
    )


def _env_signature_ids(env: np.ndarray) -> np.ndarray:
    arr = np.ascontiguousarray(np.asarray(env, dtype=np.int8))
    if arr.ndim != 2 or int(arr.shape[0]) == 0:
        return np.zeros(0, dtype=np.int32)
    row_dtype = np.dtype((np.void, int(arr.dtype.itemsize) * int(arr.shape[1])))
    row_view = arr.view(row_dtype).reshape(arr.shape[0])
    _unique, inverse = np.unique(row_view, return_inverse=True)
    return inverse.astype(np.int32, copy=False)


def _raw_pack_by_row(env: np.ndarray) -> np.ndarray:
    raw = np.asarray(env) == int(TOTAL_GEM_BUDGET)
    return np.argmax(raw, axis=1).astype(np.int32, copy=False)


def _mini_timing_matches_all_gear_cells(
    *,
    source_rows: np.ndarray,
    target_rows: np.ndarray,
    timing: _MiniTimingResponseIndex,
) -> bool:
    source = np.asarray(source_rows, dtype=np.int32)
    target = np.asarray(target_rows, dtype=np.int32)
    if int(source.shape[0]) != int(target.shape[0]):
        return False
    if HAS_NUMBA:
        return bool(
            _mini_timing_matches_all_gear_cells_jit(
                source.astype(np.int32, copy=False),
                target.astype(np.int32, copy=False),
                timing.env,
                timing.needed_offsets,
                timing.needed_packs,
                timing.needed_requirements,
            )
        )
    for source_row, target_row in zip(source.tolist(), target.tolist(), strict=False):
        start = int(timing.needed_offsets[int(target_row)])
        end = int(timing.needed_offsets[int(target_row) + 1])
        for pos in range(start, end):
            pack = int(timing.needed_packs[pos])
            req = int(timing.needed_requirements[pos])
            if int(timing.env[int(source_row), pack]) < req:
                return False
    return True


@jit(nopython=True, cache=True)
def _mini_timing_matches_all_gear_cells_jit(
    source_rows: np.ndarray,
    target_rows: np.ndarray,
    env: np.ndarray,
    needed_offsets: np.ndarray,
    needed_packs: np.ndarray,
    needed_requirements: np.ndarray,
) -> bool:
    for i in range(target_rows.shape[0]):
        source_row = source_rows[i]
        target_row = target_rows[i]
        start = needed_offsets[target_row]
        end = needed_offsets[target_row + 1]
        for pos in range(start, end):
            pack = needed_packs[pos]
            req = needed_requirements[pos]
            if env[source_row, pack] < req:
                return False
    return True
