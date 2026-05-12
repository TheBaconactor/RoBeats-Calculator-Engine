from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
from typing import Any

import numpy as np

from gear_optimizer.core.constants import GEM_SCALE_FEVER, MAX_STAT_INDEX, TOTAL_GEM_BUDGET
from gear_optimizer.solver.taichi_gem.ftff_combos import ftff_combo_arrays
from gear_optimizer.solver.taichi_gem.api.timeline import build_or_load_timeline_frontier_payload


_GRID = int(MAX_STAT_INDEX) + 1
_ANTICHAIN_TABLE_CACHE_MAX = 4
_ANTICHAIN_TABLE_CACHE: "OrderedDict[tuple[Any, ...], TimingResponseAntichainTable]" = OrderedDict()


@dataclass(frozen=True)
class TimingResponseAntichainTable:
    cells: np.ndarray
    cell_to_row: np.ndarray
    offsets_by_row: np.ndarray
    lengths_by_row: np.ndarray
    flat_ft: np.ndarray
    flat_ff: np.ndarray
    max_len: int
    legal_combo_count: int
    kept_combo_count: int
    pack_count: int
    cache_key: tuple[Any, ...]


@dataclass(frozen=True)
class TimingResponseAntichainStats:
    enabled: bool
    reason: str
    start_cells: int
    legal_combo_count: int = 0
    kept_combo_count: int = 0
    max_len: int = 0
    pack_count: int = 0
    flat_combo_count: int = 0


def timing_response_phase_counts(stats: TimingResponseAntichainStats) -> dict[str, int]:
    return {
        "timing_response_antichain_enabled": 1 if stats.enabled else 0,
        "timing_response_antichain_start_cells": int(stats.start_cells),
        "timing_response_antichain_legal_combos": int(stats.legal_combo_count),
        "timing_response_antichain_kept_combos": int(stats.kept_combo_count),
        "timing_response_antichain_max_len": int(stats.max_len),
        "timing_response_antichain_packs": int(stats.pack_count),
        "timing_response_antichain_flat_combos": int(stats.flat_combo_count),
    }


def build_timing_response_antichain_table(
    *,
    start_cells: np.ndarray,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    flags: dict[str, int],
    total_budget: int = TOTAL_GEM_BUDGET,
    gem_scale_fever: int = GEM_SCALE_FEVER,
) -> tuple[TimingResponseAntichainTable | None, TimingResponseAntichainStats]:
    cells = np.unique(np.asarray(start_cells, dtype=np.int32).reshape(-1))
    cells = cells[(cells >= 0) & (cells < int(_GRID) * int(_GRID))]
    if cells.size == 0:
        return None, _stats(False, "no_start_cells", 0)

    reason = _reference_blocker(ref_arrays)
    if reason:
        return None, _stats(False, reason, int(cells.shape[0]))

    cell_pack, pack_count, payload_key = _exact_frontier_pack_grid(calc_song=calc_song, ref_arrays=ref_arrays)
    w_ft = _lane_weight(flags, "ft", 3)
    w_ff = _lane_weight(flags, "ff", 3)
    w_ov = _lane_weight(flags, "ov", 6)
    cache_key = (
        "timing-response-antichain-v1",
        payload_key,
        int(total_budget),
        int(gem_scale_fever),
        int(w_ft),
        int(w_ff),
        int(w_ov),
        int(cells.shape[0]),
        _cells_digest(cells),
    )
    cached = _ANTICHAIN_TABLE_CACHE.get(cache_key)
    if cached is not None:
        _ANTICHAIN_TABLE_CACHE.move_to_end(cache_key)
        return cached, TimingResponseAntichainStats(
            enabled=True,
            reason="cache_hit",
            start_cells=int(cached.cells.shape[0]),
            legal_combo_count=int(cached.legal_combo_count),
            kept_combo_count=int(cached.kept_combo_count),
            max_len=int(cached.max_len),
            pack_count=int(cached.pack_count),
            flat_combo_count=int(cached.kept_combo_count),
        )

    offsets = np.zeros(int(cells.shape[0]) + 1, dtype=np.int32)
    lengths = np.zeros(int(cells.shape[0]), dtype=np.int32)
    flat_ft_parts: list[np.ndarray] = []
    flat_ff_parts: list[np.ndarray] = []
    legal_total = 0
    kept_total = 0
    max_len = 0

    for row, cell in enumerate(cells.tolist()):
        start_ft = int(cell) // int(_GRID)
        start_ff = int(cell) % int(_GRID)
        cap_ft = max(0, (int(MAX_STAT_INDEX) - start_ft) // int(gem_scale_fever))
        cap_ff = max(0, (int(MAX_STAT_INDEX) - start_ff) // int(gem_scale_fever))
        ft, ff, rem = ftff_combo_arrays(
            int(total_budget),
            max_ft_gems=int(cap_ft),
            max_ff_gems=int(cap_ff),
        )
        if ft.size == 0:
            ft = np.asarray([0], dtype=np.int32)
            ff = np.asarray([0], dtype=np.int32)
            rem = np.asarray([int(total_budget)], dtype=np.int32)
        final_ft = np.minimum(int(MAX_STAT_INDEX), start_ft + ft.astype(np.int32, copy=False) * int(gem_scale_fever))
        final_ff = np.minimum(int(MAX_STAT_INDEX), start_ff + ff.astype(np.int32, copy=False) * int(gem_scale_fever))
        packs = cell_pack[final_ft, final_ff].astype(np.int32, copy=False)
        lam = (
            int(w_ft) * ft.astype(np.int32, copy=False)
            + int(w_ff) * ff.astype(np.int32, copy=False)
            + int(w_ov) * rem.astype(np.int32, copy=False)
        )
        keep = timing_response_antichain_keep_mask(
            packs=packs,
            remaining=rem.astype(np.int32, copy=False),
            lane_value=lam.astype(np.int32, copy=False),
        )
        kept_ft = np.ascontiguousarray(ft[keep], dtype=np.int32)
        kept_ff = np.ascontiguousarray(ff[keep], dtype=np.int32)
        flat_ft_parts.append(kept_ft)
        flat_ff_parts.append(kept_ff)
        legal_total += int(ft.shape[0])
        kept = int(kept_ft.shape[0])
        kept_total += kept
        lengths[row] = kept
        max_len = max(int(max_len), int(kept))
        offsets[row + 1] = int(kept_total)

    if kept_total <= 0:
        return None, _stats(False, "empty_antichain", int(cells.shape[0]), int(legal_total))

    flat_ft = np.concatenate(flat_ft_parts).astype(np.int32, copy=False)
    flat_ff = np.concatenate(flat_ff_parts).astype(np.int32, copy=False)
    cell_to_row = np.full(int(_GRID) * int(_GRID), -1, dtype=np.int32)
    cell_to_row[cells] = np.arange(int(cells.shape[0]), dtype=np.int32)
    for arr in (cells, cell_to_row, offsets, lengths, flat_ft, flat_ff):
        arr.setflags(write=False)
    table = TimingResponseAntichainTable(
        cells=cells.astype(np.int32, copy=False),
        cell_to_row=cell_to_row,
        offsets_by_row=offsets,
        lengths_by_row=lengths,
        flat_ft=np.ascontiguousarray(flat_ft, dtype=np.int32),
        flat_ff=np.ascontiguousarray(flat_ff, dtype=np.int32),
        max_len=int(max_len),
        legal_combo_count=int(legal_total),
        kept_combo_count=int(kept_total),
        pack_count=int(pack_count),
        cache_key=cache_key,
    )
    _ANTICHAIN_TABLE_CACHE[cache_key] = table
    _ANTICHAIN_TABLE_CACHE.move_to_end(cache_key)
    while len(_ANTICHAIN_TABLE_CACHE) > int(_ANTICHAIN_TABLE_CACHE_MAX):
        _ANTICHAIN_TABLE_CACHE.popitem(last=False)
    return (
        table,
        TimingResponseAntichainStats(
            enabled=True,
            reason="certified",
            start_cells=int(cells.shape[0]),
            legal_combo_count=int(legal_total),
            kept_combo_count=int(kept_total),
            max_len=int(max_len),
            pack_count=int(pack_count),
            flat_combo_count=int(kept_total),
        ),
    )


def timing_response_antichain_keep_mask(
    *,
    packs: np.ndarray,
    remaining: np.ndarray,
    lane_value: np.ndarray,
) -> np.ndarray:
    pack_arr = np.asarray(packs, dtype=np.int32).reshape(-1)
    rem_arr = np.asarray(remaining, dtype=np.int32).reshape(-1)
    lane_arr = np.asarray(lane_value, dtype=np.int32).reshape(-1)
    if not (pack_arr.shape == rem_arr.shape == lane_arr.shape):
        raise ValueError("packs, remaining, and lane_value must have the same shape")
    n = int(pack_arr.shape[0])
    keep = np.zeros(n, dtype=np.bool_)
    if n == 0:
        return keep

    row_idx = np.arange(n, dtype=np.int32)
    order = np.lexsort((row_idx, -lane_arr, -rem_arr, pack_arr))
    sorted_pack = pack_arr[order]
    sorted_lane = lane_arr[order]
    segment_starts = np.flatnonzero(np.r_[True, sorted_pack[1:] != sorted_pack[:-1]])
    segment_ends = np.r_[segment_starts[1:], n]

    keep_sorted = np.zeros(n, dtype=np.bool_)
    for start, end in zip(segment_starts.tolist(), segment_ends.tolist(), strict=True):
        lanes = sorted_lane[start:end]
        if lanes.size == 0:
            continue
        prev_best = np.empty(lanes.shape[0], dtype=np.int32)
        prev_best[0] = np.iinfo(np.int32).min
        if lanes.shape[0] > 1:
            prev_best[1:] = np.maximum.accumulate(lanes[:-1])
        keep_sorted[start:end] = lanes > prev_best
    keep[order] = keep_sorted
    return keep


def _exact_frontier_pack_grid(
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
) -> tuple[np.ndarray, int, tuple[Any, ...]]:
    result = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    payload = result.payload
    counts = np.asarray(payload.grid_frontier_count[0], dtype=np.int32)
    offsets = np.asarray(payload.grid_frontier_offset[0], dtype=np.int32)
    body_fever = np.asarray(payload.grid_frontier_body_fever_pool[0], dtype=np.int32)
    body_normal = np.asarray(payload.grid_frontier_body_normal_pool[0], dtype=np.int32)
    masks = np.asarray(payload.grid_frontier_masks_bits_pool[0], dtype=np.uint32)
    head_len = np.asarray(payload.grid_head_len[0], dtype=np.int32)

    pack_to_id: dict[tuple[Any, ...], int] = {}
    cell_pack = np.empty((int(_GRID), int(_GRID)), dtype=np.int32)
    for ft in range(int(_GRID)):
        for ff in range(int(_GRID)):
            count = int(counts[ft, ff])
            offset = int(offsets[ft, ff])
            surfaces: list[tuple[int, int, int, int, int, int]] = []
            for i in range(count):
                pool_idx = offset + i
                surfaces.append(
                    (
                        int(masks[pool_idx, 0]),
                        int(masks[pool_idx, 1]),
                        int(masks[pool_idx, 2]),
                        int(masks[pool_idx, 3]),
                        int(body_fever[pool_idx]),
                        int(body_normal[pool_idx]),
                    )
                )
            key = (int(head_len[ft, ff]), tuple(surfaces))
            pack_id = pack_to_id.get(key)
            if pack_id is None:
                pack_id = len(pack_to_id)
                pack_to_id[key] = int(pack_id)
            cell_pack[ft, ff] = int(pack_id)

    payload_key = (
        getattr(result, "cache_key", None),
        int(getattr(result, "frontier_pool_used", int(payload.frontier_pool_used))),
        int(len(pack_to_id)),
    )
    return cell_pack, int(len(pack_to_id)), payload_key


def _cells_digest(cells: np.ndarray) -> bytes:
    arr = np.ascontiguousarray(np.asarray(cells, dtype=np.int32).reshape(-1))
    h = hashlib.blake2b(digest_size=16)
    h.update(memoryview(arr).cast("B"))
    return h.digest()


def _reference_blocker(ref_arrays: dict[str, Any]) -> str:
    for key in ("Perfect Points", "Combo Multiplier", "Fever Multiplier"):
        arr = np.asarray(ref_arrays.get(key), dtype=np.float64).reshape(-1)
        if arr.shape[0] <= int(MAX_STAT_INDEX):
            return f"missing_ref_array_{key}"
        if np.any(np.diff(arr[: int(MAX_STAT_INDEX) + 1]) < 0):
            return f"nonmonotone_ref_array_{key}"
    return ""


def _lane_weight(flags: dict[str, int], stat: str, scale: int) -> int:
    return int(scale) * ((2 * int(flags.get(f"is_p_{stat}", 0))) + int(flags.get(f"is_s_{stat}", 0)))


def _stats(
    enabled: bool,
    reason: str,
    start_cells: int,
    legal_combo_count: int = 0,
) -> TimingResponseAntichainStats:
    return TimingResponseAntichainStats(
        enabled=bool(enabled),
        reason=str(reason),
        start_cells=int(start_cells),
        legal_combo_count=int(legal_combo_count),
    )
