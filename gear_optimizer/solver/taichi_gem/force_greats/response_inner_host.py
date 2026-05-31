from collections import OrderedDict
import threading
from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.core.constants import (
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    MAX_STAT_INDEX,
)
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.solver.taichi_gem import api as gem_api
from gear_optimizer.solver.scoring.fg_policy import is_single_color_song

from .response_inner_kernels import _fg_response_inner_batch_kernel, _fg_response_inner_group_kernel
from .response_types import FgResponseInnerResult, FgResponseSurface

_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK = 1_000_000_000
_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK = 100_000
_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_GROUPS = 262_144
_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS = 262_144
_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK = 16_000_000_000
_SURFACE_HEAD_COEFF_CACHE_MAX = 4
_U16_HEAD_VALUES = np.arange(1 << 16, dtype=np.uint16)
_U16_HEAD_BITS = np.unpackbits(_U16_HEAD_VALUES.view(np.uint8).reshape(-1, 2), axis=1, bitorder="little").astype(
    np.int32,
    copy=False,
)
_U16_HEAD_COUNT = np.ascontiguousarray(np.sum(_U16_HEAD_BITS, axis=1, dtype=np.int32), dtype=np.int32)
_U16_HEAD_POS_SUM = np.ascontiguousarray(
    np.sum(_U16_HEAD_BITS * np.arange(1, 17, dtype=np.int32).reshape(1, 16), axis=1, dtype=np.int32),
    dtype=np.int32,
)
del _U16_HEAD_BITS
_SURFACE_HEAD_COEFF_CACHE: OrderedDict[tuple[int, int, tuple[int, ...], tuple[int, ...]], np.ndarray] = OrderedDict()
_SURFACE_HEAD_COEFF_CACHE_LOCK = threading.RLock()


def _color_flags(primary_color: str, secondary_color: str, selected_color: str) -> tuple[int, ...]:
    primary = str(primary_color or "")
    secondary = str(secondary_color or "")
    selected = str(selected_color or "")
    return (
        int(primary == "Chill"),
        int(secondary == "Chill"),
        int(primary == "Flow"),
        int(secondary == "Flow"),
        int(primary == "Rush"),
        int(secondary == "Rush"),
        int(primary == selected and bool(selected)),
        int(secondary == selected and bool(selected)),
        int(is_single_color_song(primary, secondary)),
    )


def _validate_surface(surface: FgResponseSurface, *, body_total: int) -> None:
    if int(surface.body_fever) < 0 or int(surface.body_great) < 0:
        raise ValueError("FG response surface body counts must be nonnegative")
    if int(surface.body_fever) > int(body_total) or int(surface.body_great) > int(body_total):
        raise ValueError("FG response surface body count exceeds song body note count")


def _response_inner_combo_count(
    *,
    residual_budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    allow_pp: bool,
) -> int:
    residual = max(0, int(residual_budget))
    max_pp_gems = 0
    if bool(allow_pp) and int(cur_pp) < MAX_STAT_INDEX:
        rem_pp = MAX_STAT_INDEX - int(cur_pp)
        max_pp_gems = rem_pp // GEM_SCALE_NORMAL
        if rem_pp % GEM_SCALE_NORMAL != 0:
            max_pp_gems += 1

    max_cm_gems = 0
    if int(cur_cm) < MAX_STAT_INDEX:
        rem_cm = MAX_STAT_INDEX - int(cur_cm)
        max_cm_gems = rem_cm // GEM_SCALE_NORMAL
        if rem_cm % GEM_SCALE_NORMAL != 0:
            max_cm_gems += 1

    max_fm_gems = 0
    if int(cur_fm) < MAX_STAT_INDEX:
        rem_fm = MAX_STAT_INDEX - int(cur_fm)
        max_fm_gems = rem_fm // GEM_SCALE_FEVER
        if rem_fm % GEM_SCALE_FEVER != 0:
            max_fm_gems += 1

    max_pp_gems = min(int(max_pp_gems), int(residual))
    max_cm_gems = min(int(max_cm_gems), int(residual))
    max_fm_gems = min(int(max_fm_gems), int(residual))

    # Exact count of feasible (g_cm, g_fm, g_pp) tuples under:
    # g_cm + g_fm + g_pp <= residual
    # g_cm <= max_cm_gems, g_fm <= max_fm_gems, g_pp <= max_pp_gems
    #
    # We keep a single loop over g_cm and use a closed-form arithmetic sum for
    # the g_fm dimension so planner overhead stays low on large warm batches.
    count = 0
    cm_limit = min(int(max_cm_gems), int(residual))
    pp_cap = int(max_pp_gems)
    fm_cap = int(max_fm_gems)
    for g_cm in range(int(cm_limit) + 1):
        leftover_after_cm = int(residual) - int(g_cm)
        if leftover_after_cm < 0:
            break
        fm_limit = min(int(fm_cap), int(leftover_after_cm))
        if fm_limit < 0:
            continue
        term_count = int(fm_limit) + 1
        if pp_cap >= int(leftover_after_cm):
            # sum_{g_fm=0..fm_limit} (leftover_after_cm - g_fm + 1)
            count += int(term_count) * (int(leftover_after_cm) + 1) - (
                int(fm_limit) * (int(fm_limit) + 1) // 2
            )
            continue

        # g_fm in [0, split-1] saturates at pp_cap, remainder is arithmetic.
        split = int(leftover_after_cm) - int(pp_cap)
        if split < 0:
            split = 0
        if split > int(term_count):
            split = int(term_count)
        count += int(split) * (int(pp_cap) + 1)
        tail_terms = int(term_count) - int(split)
        if tail_terms > 0:
            # sum_{g_fm=split..fm_limit} (leftover_after_cm - g_fm + 1)
            count += int(tail_terms) * (int(leftover_after_cm) + 1) - (
                (int(split) + int(fm_limit)) * int(tail_terms) // 2
            )
    return max(1, int(count))


def _response_inner_combo_counts(group_meta: np.ndarray, *, allow_pp: bool) -> np.ndarray:
    group_meta_arr = np.ascontiguousarray(np.asarray(group_meta, dtype=np.int32))
    if int(group_meta_arr.ndim) != 2 or int(group_meta_arr.shape[1]) < 4:
        raise ValueError("response frontier combo-count estimator requires group metadata columns 0..3")
    row_count = int(group_meta_arr.shape[0])
    if row_count <= 0:
        return np.zeros((0,), dtype=np.int64)
    combo_inputs = np.ascontiguousarray(group_meta_arr[:, :4], dtype=np.int32)
    unique_inputs, inverse = np.unique(combo_inputs, axis=0, return_inverse=True)
    unique_counts = np.asarray(
        [
            _response_inner_combo_count(
                residual_budget=int(row[0]),
                cur_pp=int(row[1]),
                cur_cm=int(row[2]),
                cur_fm=int(row[3]),
                allow_pp=allow_pp,
            )
            for row in unique_inputs
        ],
        dtype=np.int64,
    )
    return np.ascontiguousarray(unique_counts[np.asarray(inverse, dtype=np.intp)], dtype=np.int64)


def _response_group_logical_surface_plan(
    group_lengths: np.ndarray,
    combo_counts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    group_lengths_arr = np.ascontiguousarray(np.asarray(group_lengths, dtype=np.int32))
    combo_counts_arr = np.ascontiguousarray(np.asarray(combo_counts, dtype=np.int64))
    if int(group_lengths_arr.ndim) != 1 or int(combo_counts_arr.ndim) != 1:
        raise ValueError("response frontier logical surface plan requires one-dimensional inputs")
    if int(group_lengths_arr.shape[0]) != int(combo_counts_arr.shape[0]):
        raise ValueError("response frontier logical surface plan inputs have inconsistent lengths")
    if bool(np.any(group_lengths_arr < 0)):
        raise ValueError("response frontier logical surface plan received a negative group length")
    logical_surface_rows = int(np.sum(group_lengths_arr, dtype=np.int64))
    if logical_surface_rows <= 0:
        empty_i32 = np.zeros((0,), dtype=np.int32)
        return empty_i32, empty_i32, np.zeros((1,), dtype=np.int64)

    owners = np.ascontiguousarray(
        np.repeat(np.arange(int(group_lengths_arr.shape[0]), dtype=np.int32), group_lengths_arr),
        dtype=np.int32,
    )
    group_starts = np.empty((int(group_lengths_arr.shape[0]),), dtype=np.int64)
    group_starts[0] = 0
    if int(group_lengths_arr.shape[0]) > 1:
        group_starts[1:] = np.cumsum(group_lengths_arr[:-1], dtype=np.int64)
    local_surfaces = np.ascontiguousarray(
        np.arange(logical_surface_rows, dtype=np.int64) - group_starts[owners],
        dtype=np.int32,
    )
    logical_work = np.ascontiguousarray(combo_counts_arr[owners], dtype=np.int64)
    work_cumsum = np.empty((logical_surface_rows + 1,), dtype=np.int64)
    work_cumsum[0] = 0
    np.cumsum(logical_work, dtype=np.int64, out=work_cumsum[1:])
    return owners, local_surfaces, np.ascontiguousarray(work_cumsum, dtype=np.int64)
@jit(nopython=True, cache=True)
def _reduce_response_inner_chunk_jit(
    row_count,
    chunk_scores,
    chunk_details,
    chunk_owners,
    chunk_local_surfaces,
    best_scores,
    out_rows,
):
    row = 0
    while row < row_count:
        owner = int(chunk_owners[row])
        best_row = row
        best_score = int(chunk_scores[row])
        row += 1
        while row < row_count and int(chunk_owners[row]) == owner:
            score = int(chunk_scores[row])
            if score > best_score:
                best_score = score
                best_row = row
            row += 1
        if best_score > int(best_scores[owner]):
            best_scores[owner] = best_score
            out_rows[owner, 0] = best_score
            out_rows[owner, 1] = int(chunk_local_surfaces[best_row])
            for col in range(9):
                out_rows[owner, col + 2] = int(chunk_details[best_row, col])
def optimize_response_frontier_inner_exact_gpu(
    surfaces: tuple[FgResponseSurface, ...] | list[FgResponseSurface],
    *,
    total_notes: int,
    residual_budget: int,
    stats_after_ftff: dict[str, Any],
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
) -> FgResponseInnerResult:
    result, _rows = _optimize_response_surfaces_gpu(
        [(int(residual_budget), stats_after_ftff, tuple(surfaces or ()))],
        total_notes=int(total_notes),
        primary_color=str(primary_color or ""),
        secondary_color=str(secondary_color or ""),
        selected_color=str(selected_color or ""),
        ref_arrays=ref_arrays,
    )
    if not result:
        raise ValueError("response frontier GPU inner solve requires at least one surface")
    row = result[0]
    return FgResponseInnerResult(
        best_score=int(row[0]),
        surface_index=int(row[1]),
        g_pp=int(row[2]),
        g_cm=int(row[3]),
        g_fm=int(row[4]),
        g_ov=int(row[5]),
        final_pp=int(row[6]),
        final_cm=int(row[7]),
        final_fm=int(row[8]),
        final_primary=int(row[9]),
        final_secondary=int(row[10]),
    )


def _inner_stat_values_for_colors(
    stats_after_ftff: dict[str, Any] | tuple[int, ...],
    *,
    primary_color: str,
    secondary_color: str,
) -> tuple[int, int, int, int, int]:
    if isinstance(stats_after_ftff, tuple):
        return (
            int(stats_after_ftff[0]),
            int(stats_after_ftff[1]),
            int(stats_after_ftff[2]),
            int(stats_after_ftff[3]),
            int(stats_after_ftff[4]),
        )
    return (
        int(stats_after_ftff.get("Perfect Points", 0) or 0),
        int(stats_after_ftff.get("Combo Multiplier", 0) or 0),
        int(stats_after_ftff.get("Fever Multiplier", 0) or 0),
        int(stats_after_ftff.get(str(primary_color or ""), 0) or 0),
        int(stats_after_ftff.get(str(secondary_color or ""), 0) or 0),
    )


def _precompute_surface_head_coeffs(
    surface_words: np.ndarray,
    *,
    head_len: int,
) -> np.ndarray:
    source = np.asarray(surface_words)
    cacheable = bool(source.dtype == np.uint32 and source.flags.c_contiguous)
    words = source if cacheable else np.ascontiguousarray(source, dtype=np.uint32)
    key = (int(id(words)), int(head_len), tuple(int(v) for v in words.shape), tuple(int(v) for v in words.strides))
    if cacheable:
        with _SURFACE_HEAD_COEFF_CACHE_LOCK:
            cached = _SURFACE_HEAD_COEFF_CACHE.get(key)
            if cached is not None:
                _SURFACE_HEAD_COEFF_CACHE.move_to_end(key)
                return cached
    row_count = int(words.shape[0])
    coeffs = np.zeros((row_count, 4), dtype=np.int32)
    head = max(0, min(int(head_len), 100))
    if row_count > 0 and head > 0:
        if int(words.ndim) != 2 or int(words.shape[1]) < 4:
            raise ValueError("response frontier GPU head-coeff precompute requires packed fever words")
        for block in range(4):
            start = int(block * 32)
            if start >= int(head):
                break
            take = min(32, int(head) - int(start))
            if take <= 0:
                continue
            block_words = np.asarray(words[:, block], dtype=np.uint32)
            low_take = min(16, int(take))
            low_mask = (1 << int(low_take)) - 1
            low = np.asarray(block_words & np.uint32(low_mask), dtype=np.uint16)
            fever_count = np.asarray(_U16_HEAD_COUNT[low], dtype=np.int32)
            local_sigma_hf = np.asarray(_U16_HEAD_POS_SUM[low], dtype=np.int32)
            if int(take) > 16:
                high_take = int(take) - 16
                high_mask = (1 << int(high_take)) - 1
                high = np.asarray((block_words >> np.uint32(16)) & np.uint32(high_mask), dtype=np.uint16)
                high_count = np.asarray(_U16_HEAD_COUNT[high], dtype=np.int32)
                fever_count = np.asarray(fever_count + high_count, dtype=np.int32)
                local_sigma_hf = np.asarray(
                    local_sigma_hf + _U16_HEAD_POS_SUM[high] + (16 * high_count),
                    dtype=np.int32,
                )
            coeffs[:, 1] += fever_count
            coeffs[:, 0] += int(take) - fever_count
            sigma_hf = np.asarray(local_sigma_hf + (int(start) * fever_count), dtype=np.int32)
            coeffs[:, 3] += sigma_hf
            sigma_total = int(take) * ((2 * int(start)) + int(take) + 1) // 2
            coeffs[:, 2] += int(sigma_total) - sigma_hf
    coeffs = np.ascontiguousarray(coeffs, dtype=np.int32)
    if cacheable:
        with _SURFACE_HEAD_COEFF_CACHE_LOCK:
            _SURFACE_HEAD_COEFF_CACHE[key] = coeffs
            _SURFACE_HEAD_COEFF_CACHE.move_to_end(key)
            while len(_SURFACE_HEAD_COEFF_CACHE) > int(_SURFACE_HEAD_COEFF_CACHE_MAX):
                _SURFACE_HEAD_COEFF_CACHE.popitem(last=False)
    return coeffs


def _score_response_group_meta_gpu(
    *,
    group_meta: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
    surface_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_head_coeffs: np.ndarray | None = None,
    logical_owners: np.ndarray | None = None,
    logical_surfaces: np.ndarray | None = None,
    logical_work_cumsum: np.ndarray | None = None,
) -> tuple[np.ndarray, int]:
    group_count = int(group_meta.shape[0])
    if group_count != int(group_offsets.shape[0]) or group_count != int(group_lengths.shape[0]):
        raise ValueError("response frontier GPU group metadata arrays have inconsistent lengths")
    logical_surface_rows = int(np.sum(group_lengths, dtype=np.int64))
    if logical_surface_rows <= 0:
        return np.zeros((0, 11), dtype=np.int32), 0

    gem_api.ensure_ready()
    flags = np.ascontiguousarray(np.asarray(_color_flags(primary_color, secondary_color, selected_color), dtype=np.int32))
    ref_pp = np.ascontiguousarray(np.asarray(ref_arrays["Perfect Points"], dtype=np.float32))
    ref_cm = np.ascontiguousarray(np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32))
    ref_fm = np.ascontiguousarray(np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32))
    surface_words_all = np.ascontiguousarray(surface_words, dtype=np.uint32)
    surface_counts_all = np.ascontiguousarray(surface_counts, dtype=np.int32)
    group_meta_all = np.ascontiguousarray(group_meta, dtype=np.int32)
    group_offsets_all = np.ascontiguousarray(group_offsets, dtype=np.int32)
    group_lengths_all = np.ascontiguousarray(group_lengths, dtype=np.int32)

    if int(surface_words_all.shape[0]) != int(surface_counts_all.shape[0]):
        raise ValueError("response frontier GPU surface arrays have inconsistent lengths")
    if int(surface_words_all.shape[1]) != 8 or int(surface_counts_all.shape[1]) != 2:
        raise ValueError("response frontier GPU surface arrays have invalid shape")
    if int(group_meta_all.shape[1]) < 8:
        raise ValueError("response frontier GPU group metadata requires head/body columns")
    head_lengths = np.unique(np.ascontiguousarray(group_meta_all[:, 6], dtype=np.int32))
    if int(head_lengths.shape[0]) != 1:
        raise ValueError("response frontier GPU group metadata has inconsistent head length")
    if surface_head_coeffs is None:
        surface_head_coeffs_all = _precompute_surface_head_coeffs(surface_words_all, head_len=int(head_lengths[0]))
    else:
        surface_head_coeffs_all = np.ascontiguousarray(np.asarray(surface_head_coeffs, dtype=np.int32))
        if (
            int(surface_head_coeffs_all.ndim) != 2
            or int(surface_head_coeffs_all.shape[0]) != int(surface_words_all.shape[0])
            or int(surface_head_coeffs_all.shape[1]) != 4
        ):
            raise ValueError("response frontier GPU surface head coefficients have invalid shape")

    flags_tuple = _color_flags(primary_color, secondary_color, selected_color)
    allow_pp = bool(int(flags_tuple[0]) != 0 or int(flags_tuple[1]) != 0)
    combo_counts = _response_inner_combo_counts(group_meta_all, allow_pp=allow_pp)
    work_by_group = np.asarray(group_lengths_all, dtype=np.int64) * combo_counts
    total_work = int(np.sum(work_by_group, dtype=np.int64))
    max_group_work = int(np.max(work_by_group)) if group_count > 0 else 0
    max_dispatch_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK))
    max_thread_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK))
    max_dispatch_groups = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_GROUPS))
    max_surface_dispatch_rows = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS))
    max_surface_dispatch_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK))
    out_rows = np.zeros((group_count, 11), dtype=np.int32)
    if (
        group_count <= max_dispatch_groups
        and total_work <= max_dispatch_work
        and max_group_work <= max_thread_work
    ):
        _fg_response_inner_group_kernel(
            int(group_count),
            surface_words_all,
            surface_counts_all,
            surface_head_coeffs_all,
            group_offsets_all,
            group_lengths_all,
            group_meta_all,
            flags,
            ref_pp,
            ref_cm,
            ref_fm,
            out_rows,
            bool(allow_pp),
        )
        ti.sync()
        return out_rows, int(logical_surface_rows)

    valid_group_indices = np.flatnonzero(np.asarray(group_lengths_all > 0, dtype=np.bool_)).astype(
        np.int32,
        copy=False,
    )
    if int(valid_group_indices.shape[0]) <= 0:
        return out_rows, int(logical_surface_rows)

    best_scores = np.full((group_count,), np.iinfo(np.int32).min, dtype=np.int32)
    if logical_owners is None or logical_surfaces is None or logical_work_cumsum is None:
        logical_owners_all, logical_surfaces_all, logical_work_cumsum_all = _response_group_logical_surface_plan(
            group_lengths_all,
            combo_counts,
        )
    else:
        logical_owners_all = np.ascontiguousarray(np.asarray(logical_owners, dtype=np.int32))
        logical_surfaces_all = np.ascontiguousarray(np.asarray(logical_surfaces, dtype=np.int32))
        logical_work_cumsum_all = np.ascontiguousarray(np.asarray(logical_work_cumsum, dtype=np.int64))
    if int(logical_owners_all.shape[0]) != int(logical_surface_rows) or int(logical_surfaces_all.shape[0]) != int(
        logical_surface_rows
    ):
        raise ValueError("response frontier logical surface plan has inconsistent row counts")
    if int(logical_work_cumsum_all.shape[0]) != int(logical_surface_rows) + 1:
        raise ValueError("response frontier logical surface work plan has inconsistent row count")
    if bool(np.any(logical_owners_all < 0)) or bool(np.any(logical_owners_all >= int(group_count))):
        raise ValueError("response frontier logical surface plan references an invalid group")
    surface_indices = group_offsets_all[logical_owners_all] + logical_surfaces_all
    if bool(np.any(logical_surfaces_all < 0)) or bool(np.any(surface_indices < 0)) or bool(
        np.any(surface_indices >= int(surface_words_all.shape[0]))
    ):
        raise ValueError("response frontier logical surface plan references an invalid surface")

    chunk_capacity = max(1, min(int(max_surface_dispatch_rows), int(logical_surface_rows)))
    chunk_scores = np.empty((chunk_capacity,), dtype=np.int32)
    chunk_details = np.empty((chunk_capacity, 9), dtype=np.int32)
    chunk_start = 0
    while chunk_start < int(logical_surface_rows):
        row_stop = min(int(logical_surface_rows), int(chunk_start) + int(max_surface_dispatch_rows))
        work_limit = int(logical_work_cumsum_all[int(chunk_start)]) + int(max_surface_dispatch_work)
        work_stop = int(np.searchsorted(logical_work_cumsum_all, work_limit, side="right") - 1)
        if work_stop <= int(chunk_start):
            work_stop = int(chunk_start) + 1
        chunk_stop = min(int(row_stop), int(work_stop), int(logical_surface_rows))
        row_count = int(chunk_stop) - int(chunk_start)
        if row_count <= 0:
            raise ValueError("response frontier logical surface chunk planner produced an empty chunk")
        scores_view = chunk_scores[:row_count]
        details_view = chunk_details[:row_count]
        _fg_response_inner_batch_kernel(
            int(row_count),
            surface_words_all,
            surface_counts_all,
            surface_head_coeffs_all,
            group_offsets_all,
            logical_owners_all[int(chunk_start) : int(chunk_stop)],
            logical_surfaces_all[int(chunk_start) : int(chunk_stop)],
            group_meta_all,
            flags,
            ref_pp,
            ref_cm,
            ref_fm,
            scores_view,
            details_view,
            bool(allow_pp),
        )
        ti.sync()
        _reduce_response_inner_chunk_jit(
            int(row_count),
            scores_view,
            details_view,
            logical_owners_all[int(chunk_start) : int(chunk_stop)],
            logical_surfaces_all[int(chunk_start) : int(chunk_stop)],
            best_scores,
            out_rows,
        )
        chunk_start = int(chunk_stop)
    return out_rows, int(logical_surface_rows)


def _optimize_response_surfaces_gpu(
    groups: list[tuple[int, dict[str, Any] | tuple[int, ...], tuple[FgResponseSurface, ...]]],
    *,
    total_notes: int,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
) -> tuple[list[tuple[int, int, int, int, int, int, int, int, int, int, int]], int]:
    head_len = min(int(total_notes), 100)
    body_total = max(0, int(total_notes) - 100)
    surface_cache: dict[int, tuple[int, int]] = {}
    surface_word_blocks: list[np.ndarray] = []
    surface_count_blocks: list[np.ndarray] = []
    group_meta = np.zeros((len(groups), 8), dtype=np.int32)
    group_offsets = np.zeros(len(groups), dtype=np.int32)
    group_lengths = np.zeros(len(groups), dtype=np.int32)
    logical_surface_rows = 0
    unique_surface_rows = 0

    def _surface_block(surfaces: tuple[FgResponseSurface, ...]) -> tuple[int, int]:
        nonlocal unique_surface_rows
        key = id(surfaces)
        cached = surface_cache.get(key)
        if cached is not None:
            return cached
        words = np.empty((len(surfaces), 8), dtype=np.uint32)
        counts = np.empty((len(surfaces), 2), dtype=np.int32)
        for idx, surface in enumerate(surfaces):
            _validate_surface(surface, body_total=int(body_total))
            words[idx, 0] = int(surface.fever0)
            words[idx, 1] = int(surface.fever1)
            words[idx, 2] = int(surface.fever2)
            words[idx, 3] = int(surface.fever3)
            words[idx, 4] = int(surface.great0)
            words[idx, 5] = int(surface.great1)
            words[idx, 6] = int(surface.great2)
            words[idx, 7] = int(surface.great3)
            counts[idx, 0] = int(surface.body_fever)
            counts[idx, 1] = int(surface.body_great)
        cached = (int(unique_surface_rows), int(words.shape[0]))
        surface_cache[key] = cached
        surface_word_blocks.append(words)
        surface_count_blocks.append(counts)
        unique_surface_rows += int(words.shape[0])
        return cached

    for group_idx, (residual_budget, stats_after_ftff, surfaces) in enumerate(groups):
        cur_pp, cur_cm, cur_fm, cur_primary, cur_secondary = _inner_stat_values_for_colors(
            stats_after_ftff,
            primary_color=str(primary_color or ""),
            secondary_color=str(secondary_color or ""),
        )
        surfaces_tuple = tuple(surfaces or ())
        if not surfaces_tuple:
            continue
        offset, length = _surface_block(surfaces_tuple)
        logical_surface_rows += int(length)
        group_offsets[group_idx] = int(offset)
        group_lengths[group_idx] = int(length)
        group_meta[group_idx] = (
            max(0, int(residual_budget)),
            int(cur_pp),
            int(cur_cm),
            int(cur_fm),
            int(cur_primary),
            int(cur_secondary),
            int(head_len),
            int(body_total),
        )
    if logical_surface_rows <= 0:
        return [], 0

    gem_api.ensure_ready()
    if unique_surface_rows <= 0:
        raise ValueError("response frontier GPU inner solve has groups but no packed surfaces")
    surface_words = np.ascontiguousarray(np.concatenate(surface_word_blocks, axis=0))
    surface_counts = np.ascontiguousarray(np.concatenate(surface_count_blocks, axis=0))
    surface_head_coeffs = _precompute_surface_head_coeffs(surface_words, head_len=int(head_len))

    flags_tuple = _color_flags(primary_color, secondary_color, selected_color)
    allow_pp = bool(int(flags_tuple[0]) != 0 or int(flags_tuple[1]) != 0)
    flags = np.ascontiguousarray(np.asarray(flags_tuple, dtype=np.int32))
    ref_pp = np.ascontiguousarray(np.asarray(ref_arrays["Perfect Points"], dtype=np.float32))
    ref_cm = np.ascontiguousarray(np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32))
    ref_fm = np.ascontiguousarray(np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32))
    out_rows = np.zeros((len(groups), 11), dtype=np.int32)
    _fg_response_inner_group_kernel(
        int(len(groups)),
        surface_words,
        surface_counts,
        surface_head_coeffs,
        group_offsets,
        group_lengths,
        group_meta,
        flags,
        ref_pp,
        ref_cm,
        ref_fm,
        out_rows,
        bool(allow_pp),
    )
    ti.sync()

    best_by_group: list[tuple[int, int, int, int, int, int, int, int, int, int, int] | None] = [None] * len(groups)
    for group_idx in range(len(groups)):
        if int(group_lengths[group_idx]) <= 0:
            continue
        raw = out_rows[group_idx]
        candidate = (
            int(raw[0]),
            int(raw[1]),
            int(raw[2]),
            int(raw[3]),
            int(raw[4]),
            int(raw[5]),
            int(raw[6]),
            int(raw[7]),
            int(raw[8]),
            int(raw[9]),
            int(raw[10]),
        )
        best_by_group[int(group_idx)] = candidate
    return [row for row in best_by_group if row is not None], int(logical_surface_rows)
