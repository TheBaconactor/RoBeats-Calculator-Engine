from collections import OrderedDict
import threading
import time
import weakref
from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_ROWS,
)
from gear_optimizer.core.jit_setup import jit
from gear_optimizer.core.profile_events import emit_profile_event, profile_events_active
from gear_optimizer.helpers.song_helpers.ref_array_builder import resolve_exact_replay_ref_arrays
from gear_optimizer.solver.taichi_gem import api as gem_api
from gear_optimizer.solver.scoring.fg_policy import is_single_color_song

from .response_inner_kernels import (
    SOLVER_NP_FP,
    _fg_response_inner_batch_kernel,
    _fg_response_inner_group_kernel,
)
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
_EXACT_REPLAY_REF_NAMES = (
    "Perfect Points",
    "Combo Multiplier",
    "Fever Multiplier",
    "Fever Fill Rate",
    "Fever Time",
)


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
    if int(surface.body_fever) < 0 or int(surface.body_great) < 0 or int(surface.body_fever_great) < 0:
        raise ValueError("FG response surface body counts must be nonnegative")
    if int(surface.body_fever) > int(body_total) or int(surface.body_great) > int(body_total):
        raise ValueError("FG response surface body count exceeds song body note count")
    if int(surface.body_fever_great) > int(surface.body_fever) or int(surface.body_fever_great) > int(surface.body_great):
        raise ValueError("FG response surface body Fever-Great count exceeds its parent counts")
    if int(surface.body_fever) + int(surface.body_great) - int(surface.body_fever_great) > int(body_total):
        raise ValueError("FG response surface body categories exceed song body note count")


def _response_inner_score_ref_arrays(ref_arrays: dict[str, Any]) -> dict[str, Any]:
    if not all(name in ref_arrays for name in _EXACT_REPLAY_REF_NAMES):
        return ref_arrays
    return resolve_exact_replay_ref_arrays(ref_arrays)


@jit(nopython=True, cache=True)
def _response_inner_combo_count_jit(residual_budget, cur_pp, cur_cm, cur_fm, allow_pp):
    residual = int(residual_budget)
    if residual < 0:
        residual = 0
    max_pp_gems = 0
    if bool(allow_pp) and cur_pp < MAX_STAT_INDEX:
        rem_pp = MAX_STAT_INDEX - cur_pp
        max_pp_gems = rem_pp // GEM_SCALE_NORMAL
        if rem_pp % GEM_SCALE_NORMAL != 0:
            max_pp_gems += 1

    max_cm_gems = 0
    if cur_cm < MAX_STAT_INDEX:
        rem_cm = MAX_STAT_INDEX - cur_cm
        max_cm_gems = rem_cm // GEM_SCALE_NORMAL
        if rem_cm % GEM_SCALE_NORMAL != 0:
            max_cm_gems += 1

    max_fm_gems = 0
    if cur_fm < MAX_STAT_INDEX:
        rem_fm = MAX_STAT_INDEX - cur_fm
        max_fm_gems = rem_fm // GEM_SCALE_FEVER
        if rem_fm % GEM_SCALE_FEVER != 0:
            max_fm_gems += 1

    if max_pp_gems > residual:
        max_pp_gems = residual
    if max_cm_gems > residual:
        max_cm_gems = residual
    if max_fm_gems > residual:
        max_fm_gems = residual

    count = 0
    cm_limit = max_cm_gems
    pp_cap = max_pp_gems
    fm_cap = max_fm_gems
    for g_cm in range(cm_limit + 1):
        leftover_after_cm = residual - g_cm
        if leftover_after_cm < 0:
            break
        fm_limit = fm_cap
        if fm_limit > leftover_after_cm:
            fm_limit = leftover_after_cm
        if fm_limit < 0:
            continue
        term_count = fm_limit + 1
        if pp_cap >= leftover_after_cm:
            count += term_count * (leftover_after_cm + 1) - (fm_limit * (fm_limit + 1) // 2)
            continue

        split = leftover_after_cm - pp_cap
        if split < 0:
            split = 0
        if split > term_count:
            split = term_count
        count += split * (pp_cap + 1)
        tail_terms = term_count - split
        if tail_terms > 0:
            count += tail_terms * (leftover_after_cm + 1) - ((split + fm_limit) * tail_terms // 2)
    if count < 1:
        count = 1
    return int(count)


def _response_inner_combo_count(
    *,
    residual_budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    allow_pp: bool,
) -> int:
    # Exact count of feasible (g_cm, g_fm, g_pp) tuples under:
    # g_cm + g_fm + g_pp <= residual and each gem stat cap.
    return int(
        _response_inner_combo_count_jit(
            int(residual_budget),
            int(cur_pp),
            int(cur_cm),
            int(cur_fm),
            bool(allow_pp),
        )
    )


@jit(nopython=True, cache=True)
def _response_inner_combo_counts_jit(group_meta_arr, allow_pp):
    row_count = int(group_meta_arr.shape[0])
    out = np.empty((row_count,), dtype=np.int64)
    for idx in range(row_count):
        out[idx] = int(
            _response_inner_combo_count_jit(
                int(group_meta_arr[idx, 0]),
                int(group_meta_arr[idx, 1]),
                int(group_meta_arr[idx, 2]),
                int(group_meta_arr[idx, 3]),
                bool(allow_pp),
            )
        )
    return out


def _response_inner_combo_counts(group_meta: np.ndarray, *, allow_pp: bool) -> np.ndarray:
    group_meta_arr = np.ascontiguousarray(np.asarray(group_meta, dtype=np.int32))
    if int(group_meta_arr.ndim) != 2 or int(group_meta_arr.shape[1]) < 4:
        raise ValueError("response frontier combo-count estimator requires group metadata columns 0..3")
    row_count = int(group_meta_arr.shape[0])
    if row_count <= 0:
        return np.zeros((0,), dtype=np.int64)
    return np.ascontiguousarray(
        _response_inner_combo_counts_jit(group_meta_arr[:, :4], bool(allow_pp)),
        dtype=np.int64,
    )


@jit(nopython=True, cache=True)
def _response_group_logical_surface_plan_jit(group_lengths, combo_counts, logical_surface_rows):
    owners = np.empty((int(logical_surface_rows),), dtype=np.int32)
    local_surfaces = np.empty((int(logical_surface_rows),), dtype=np.int32)
    work_cumsum = np.empty((int(logical_surface_rows) + 1,), dtype=np.int64)
    work_cumsum[0] = 0
    row = 0
    work = 0
    for owner in range(int(group_lengths.shape[0])):
        count = int(combo_counts[owner])
        for local_surface in range(int(group_lengths[owner])):
            owners[row] = int(owner)
            local_surfaces[row] = int(local_surface)
            work += count
            work_cumsum[row + 1] = int(work)
            row += 1
    return owners, local_surfaces, work_cumsum


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
    return _response_group_logical_surface_plan_jit(
        group_lengths_arr,
        combo_counts_arr,
        int(logical_surface_rows),
    )


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
        # The key embeds id(words): it identifies THIS array only while the array is alive.
        # Once the pool is garbage-collected the id can be reused by a new same-shaped pool
        # (stale-hit hazard) and the retained coeffs are unreachable dead weight (~370 MB per
        # 23M-row pool in prebuild workers). Evict the entry the moment the source dies.
        weakref.finalize(words, _evict_surface_head_coeff_entry, key)
    return coeffs


def _evict_surface_head_coeff_entry(key: tuple[int, int, tuple[int, ...], tuple[int, ...]]) -> None:
    with _SURFACE_HEAD_COEFF_CACHE_LOCK:
        _SURFACE_HEAD_COEFF_CACHE.pop(key, None)


def _score_response_group_meta_gpu(
    *,
    group_meta: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
    surface_pattern_ids: np.ndarray,
    surface_pattern_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_pattern_head_coeffs: np.ndarray,
) -> tuple[np.ndarray, int]:
    group_count = int(group_meta.shape[0])
    if group_count != int(group_offsets.shape[0]) or group_count != int(group_lengths.shape[0]):
        raise ValueError("response frontier GPU group metadata arrays have inconsistent lengths")
    logical_surface_rows = int(np.sum(group_lengths, dtype=np.int64))
    if logical_surface_rows <= 0:
        return np.zeros((0, 11), dtype=np.int32), 0

    gem_api.ensure_ready()
    flags = np.ascontiguousarray(np.asarray(_color_flags(primary_color, secondary_color, selected_color), dtype=np.int32))
    exact_ref_arrays = _response_inner_score_ref_arrays(ref_arrays)
    ref_pp = np.ascontiguousarray(np.asarray(exact_ref_arrays["Perfect Points"], dtype=SOLVER_NP_FP))
    ref_cm = np.ascontiguousarray(np.asarray(exact_ref_arrays["Combo Multiplier"], dtype=SOLVER_NP_FP))
    ref_fm = np.ascontiguousarray(np.asarray(exact_ref_arrays["Fever Multiplier"], dtype=SOLVER_NP_FP))
    surface_pattern_ids_all = np.ascontiguousarray(surface_pattern_ids, dtype=np.int32)
    surface_pattern_words_all = np.ascontiguousarray(surface_pattern_words, dtype=np.uint32)
    surface_counts_all = np.ascontiguousarray(surface_counts, dtype=np.int32)
    surface_pattern_head_coeffs_all = np.ascontiguousarray(surface_pattern_head_coeffs, dtype=np.int32)
    group_meta_all = np.ascontiguousarray(group_meta, dtype=np.int32)
    group_offsets_all = np.ascontiguousarray(group_offsets, dtype=np.int32)
    group_lengths_all = np.ascontiguousarray(group_lengths, dtype=np.int32)

    if int(surface_pattern_ids_all.shape[0]) != int(surface_counts_all.shape[0]):
        raise ValueError("response frontier GPU surface arrays have inconsistent lengths")
    if (
        int(surface_pattern_ids_all.ndim) != 1
        or int(surface_pattern_words_all.ndim) != 2
        or int(surface_pattern_words_all.shape[1]) != 8
        or int(surface_counts_all.ndim) != 2
        or int(surface_counts_all.shape[1]) != 3
        or int(surface_pattern_head_coeffs_all.ndim) != 2
        or int(surface_pattern_head_coeffs_all.shape[0]) != int(surface_pattern_words_all.shape[0])
        or int(surface_pattern_head_coeffs_all.shape[1]) != 4
    ):
        raise ValueError("response frontier GPU surface arrays have invalid shape")
    if bool(np.any(surface_pattern_ids_all < 0)) or bool(
        np.any(surface_pattern_ids_all >= int(surface_pattern_words_all.shape[0]))
    ):
        raise ValueError("response frontier GPU surface references an invalid head-pattern ID")
    if bool(np.any(surface_counts_all < 0)):
        raise ValueError("response frontier GPU surface counts must be nonnegative")
    body_fever_all = surface_counts_all[:, 0]
    body_great_all = surface_counts_all[:, 1]
    body_fever_great_all = surface_counts_all[:, 2]
    body_total_max = int(np.max(group_meta_all[:, 7])) if int(group_meta_all.shape[0]) else 0
    if bool(np.any(body_fever_all > body_total_max)) or bool(np.any(body_great_all > body_total_max)):
        raise ValueError("response frontier GPU surface body count exceeds song body note count")
    if bool(np.any(body_fever_great_all > body_fever_all)) or bool(np.any(body_fever_great_all > body_great_all)):
        raise ValueError("response frontier GPU surface body Fever-Great count exceeds parent counts")
    if bool(np.any(body_fever_all + body_great_all - body_fever_great_all > body_total_max)):
        raise ValueError("response frontier GPU surface body categories exceed song body note count")
    if int(group_meta_all.shape[1]) < 8:
        raise ValueError("response frontier GPU group metadata requires head/body columns")
    head_lengths = np.unique(np.ascontiguousarray(group_meta_all[:, 6], dtype=np.int32))
    if int(head_lengths.shape[0]) != 1:
        raise ValueError("response frontier GPU group metadata has inconsistent head length")
    flags_tuple = _color_flags(primary_color, secondary_color, selected_color)
    allow_pp = bool(int(flags_tuple[0]) != 0 or int(flags_tuple[1]) != 0)
    combo_counts_all = _response_inner_combo_counts(group_meta_all, allow_pp=allow_pp)
    work_by_group = np.asarray(group_lengths_all, dtype=np.int64) * combo_counts_all
    total_work = int(np.sum(work_by_group, dtype=np.int64))
    max_group_work = int(np.max(work_by_group)) if group_count > 0 else 0
    max_dispatch_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_WORK))
    max_thread_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_THREAD_WORK))
    max_dispatch_groups = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_DISPATCH_GROUPS))
    max_surface_dispatch_rows = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_ROWS))
    max_surface_dispatch_work = max(1, int(_FG_RESPONSE_INNER_GPU_MAX_SURFACE_DISPATCH_WORK))
    out_rows = np.zeros((group_count, 11), dtype=np.int32)
    # The surface pool is invariant across every chunk dispatch below -- only the
    # per-chunk index/output slices change. Passing the numpy pool to the kernel
    # re-transfers it host->device on each launch (ti.types.ndarray semantics), so a
    # 0.5-1.5 GB pool over 143-219 chunks is 90-330 GB of redundant PCIe copy and ~95%
    # of the heavy-song "score loop" wall time (measured 25x, bit-exact via
    # tools/dev/measure_fg_pool_reupload.py). Upload it ONCE to device-resident
    # ndarrays and reuse across all chunks; results are identical (same kernel, same
    # data, fewer copies).
    d_surface_pattern_ids = ti.ndarray(dtype=ti.i32, shape=surface_pattern_ids_all.shape)
    d_surface_pattern_words = ti.ndarray(dtype=ti.u32, shape=surface_pattern_words_all.shape)
    d_surface_counts = ti.ndarray(dtype=ti.i32, shape=surface_counts_all.shape)
    d_surface_pattern_head_coeffs = ti.ndarray(dtype=ti.i32, shape=surface_pattern_head_coeffs_all.shape)
    # No ti.sync() here: the from_numpy uploads and the kernel launches below run on the same
    # Taichi stream, so the uploads are ordered before the first kernel reads them; the
    # per-chunk ti.sync() after each dispatch already gates the host reduce on the outputs.
    d_surface_pattern_ids.from_numpy(surface_pattern_ids_all)
    d_surface_pattern_words.from_numpy(surface_pattern_words_all)
    d_surface_counts.from_numpy(surface_counts_all)
    d_surface_pattern_head_coeffs.from_numpy(surface_pattern_head_coeffs_all)
    if (
        group_count <= max_dispatch_groups
        and total_work <= max_dispatch_work
        and max_group_work <= max_thread_work
    ):
        _fg_response_inner_group_kernel(
            int(group_count),
            d_surface_pattern_ids,
            d_surface_pattern_words,
            d_surface_counts,
            d_surface_pattern_head_coeffs,
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

    if max_group_work <= max_thread_work:
        chunk_start = 0
        while chunk_start < int(group_count):
            chunk_stop = int(chunk_start)
            chunk_work = 0
            while chunk_stop < int(group_count) and (int(chunk_stop) - int(chunk_start)) < int(max_dispatch_groups):
                next_work = int(chunk_work) + int(work_by_group[int(chunk_stop)])
                if chunk_stop > chunk_start and next_work > int(max_dispatch_work):
                    break
                chunk_work = int(next_work)
                chunk_stop += 1
            if chunk_stop <= chunk_start:
                chunk_stop = int(chunk_start) + 1
            _fg_response_inner_group_kernel(
                int(chunk_stop) - int(chunk_start),
                d_surface_pattern_ids,
                d_surface_pattern_words,
                d_surface_counts,
                d_surface_pattern_head_coeffs,
                group_offsets_all[int(chunk_start) : int(chunk_stop)],
                group_lengths_all[int(chunk_start) : int(chunk_stop)],
                group_meta_all[int(chunk_start) : int(chunk_stop)],
                flags,
                ref_pp,
                ref_cm,
                ref_fm,
                out_rows[int(chunk_start) : int(chunk_stop)],
                bool(allow_pp),
            )
            ti.sync()
            chunk_start = int(chunk_stop)
        return out_rows, int(logical_surface_rows)

    valid_group_indices = np.flatnonzero(np.asarray(group_lengths_all > 0, dtype=np.bool_)).astype(
        np.int32,
        copy=False,
    )
    if int(valid_group_indices.shape[0]) <= 0:
        return out_rows, int(logical_surface_rows)

    best_scores = np.full((group_count,), np.iinfo(np.int32).min, dtype=np.int32)
    logical_owners_all, logical_surfaces_all, logical_work_cumsum_all = _response_group_logical_surface_plan(
        group_lengths_all,
        combo_counts_all,
    )
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
        np.any(surface_indices >= int(surface_pattern_ids_all.shape[0]))
    ):
        raise ValueError("response frontier logical surface plan references an invalid surface")

    # NOTE (measured 2026-07-01, net-zero, reverted): device-residency for the
    # chunk-invariant args here (group_offsets/group_meta/flags/refs) was bit-exact
    # but did NOT move enqueue_ms (398.6 -> 402.5ms warm on a 12-chunk heavy song).
    # The enqueue cost is per-launch fixed overhead, not these arrays' re-staging
    # (~5MB/chunk); do not re-attempt residency for them without new evidence.
    chunk_capacity = max(1, min(int(max_surface_dispatch_rows), int(logical_surface_rows)))
    chunk_scores = np.empty((chunk_capacity,), dtype=np.int32)
    chunk_details = np.empty((chunk_capacity, 9), dtype=np.int32)
    # Gated owner-thread phase profiling: split the chunk loop into plan/enqueue/
    # GPU-sync/host-reduce to decide A (move host work off owner) vs B (pipeline the
    # loop). OFF unless METAFINDER_PROFILE_EVENTS_PATH is set; no behavior change.
    _prof = profile_events_active()
    _acc_plan = _acc_enqueue = _acc_sync = _acc_reduce = 0.0
    _n_chunks = 0
    chunk_start = 0
    while chunk_start < int(logical_surface_rows):
        if _prof:
            _t0 = time.perf_counter()
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
        if _prof:
            _t1 = time.perf_counter()
        _fg_response_inner_batch_kernel(
            int(row_count),
            d_surface_pattern_ids,
            d_surface_pattern_words,
            d_surface_counts,
            d_surface_pattern_head_coeffs,
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
        if _prof:
            _t2 = time.perf_counter()
        ti.sync()
        if _prof:
            _t3 = time.perf_counter()
        _reduce_response_inner_chunk_jit(
            int(row_count),
            scores_view,
            details_view,
            logical_owners_all[int(chunk_start) : int(chunk_stop)],
            logical_surfaces_all[int(chunk_start) : int(chunk_stop)],
            best_scores,
            out_rows,
        )
        if _prof:
            _t4 = time.perf_counter()
            _acc_plan += _t1 - _t0
            _acc_enqueue += _t2 - _t1
            _acc_sync += _t3 - _t2
            _acc_reduce += _t4 - _t3
            _n_chunks += 1
        chunk_start = int(chunk_stop)
    if _prof:
        emit_profile_event(
            component="fg_fused",
            event="fg_owner_phase",
            metrics={
                "phase": "score_loop",
                "n_chunks": int(_n_chunks),
                "n_groups": int(group_count),
                "logical_surface_rows": int(logical_surface_rows),
                "total_work": int(total_work),
                "plan_ms": _acc_plan * 1000.0,
                "enqueue_ms": _acc_enqueue * 1000.0,
                "sync_ms": _acc_sync * 1000.0,
                "reduce_ms": _acc_reduce * 1000.0,
            },
        )
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
        counts = np.empty((len(surfaces), 3), dtype=np.int32)
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
            counts[idx, 2] = int(surface.body_fever_great)
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
    surface_pattern_words, surface_pattern_ids = np.unique(
        surface_words,
        axis=0,
        return_inverse=True,
    )
    surface_pattern_words = np.ascontiguousarray(surface_pattern_words, dtype=np.uint32)
    surface_pattern_ids = np.ascontiguousarray(surface_pattern_ids, dtype=np.int32)
    surface_pattern_head_coeffs = _precompute_surface_head_coeffs(
        surface_pattern_words,
        head_len=int(head_len),
    )

    flags_tuple = _color_flags(primary_color, secondary_color, selected_color)
    allow_pp = bool(int(flags_tuple[0]) != 0 or int(flags_tuple[1]) != 0)
    flags = np.ascontiguousarray(np.asarray(flags_tuple, dtype=np.int32))
    exact_ref_arrays = _response_inner_score_ref_arrays(ref_arrays)
    ref_pp = np.ascontiguousarray(np.asarray(exact_ref_arrays["Perfect Points"], dtype=SOLVER_NP_FP))
    ref_cm = np.ascontiguousarray(np.asarray(exact_ref_arrays["Combo Multiplier"], dtype=SOLVER_NP_FP))
    ref_fm = np.ascontiguousarray(np.asarray(exact_ref_arrays["Fever Multiplier"], dtype=SOLVER_NP_FP))
    out_rows = np.zeros((len(groups), 11), dtype=np.int32)
    _fg_response_inner_group_kernel(
        int(len(groups)),
        surface_pattern_ids,
        surface_pattern_words,
        surface_counts,
        surface_pattern_head_coeffs,
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


@jit(nopython=True, cache=True)
def _fg_clamp_ref_idx_native(idx, total_rows):
    if idx < 0:
        return 0
    if idx > total_rows:
        return total_rows
    return idx


@jit(nopython=True, cache=True)
def _fg_response_upper_bound_native_f64(
    base_value,
    combo_mul,
    fever_mul,
    body_fever,
    body_normal,
    n_hn,
    n_hf,
    sigma_hn,
    sigma_hf,
):
    """f64 CPU port of ``_fg_response_surface_upper_bound`` (the gem-search prune bound)."""
    ub_eps = 1024.0
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_score = body_fever * fever_val + body_normal * combo_val
    factor = (combo_mul - 1.0) * base_value / 100.0
    head_upper = base_value * (float(n_hn) + fever_mul * float(n_hf)) + factor * (
        float(sigma_hn) + fever_mul * float(sigma_hf)
    )
    return float(body_score) + head_upper + ub_eps


@jit(nopython=True, cache=True)
def _fg_response_surface_score_native_f64(
    surface_words,
    sr,
    body_fever,
    body_great,
    body_fever_great,
    head_len,
    body_total,
    primary_val,
    secondary_val,
    pp_factor,
    combo_mul,
    fever_mul,
    is_single_color,
):
    """f64 CPU port of ``_fg_response_score_device``: exact score of one surface for a fixed
    (gem-allocated) stat line. Same op order / per-term ``floor`` / i32 accumulation as the
    GPU device function, run in CPU doubles (no MoltenVK shaderFloat64 needed)."""
    base_value = float((primary_val * 2) + secondary_val) + pp_factor
    combo_val = int(np.floor(base_value * combo_mul))
    fever_val = int(np.floor(base_value * combo_mul * fever_mul))
    body_normal = body_total - body_fever
    if body_normal < 0:
        body_normal = 0
    score = body_fever * fever_val + body_normal * combo_val
    combo_slope = (combo_mul - 1.0) / 100.0

    for i in range(head_len):
        wi = i >> 5
        b = i & 31
        is_fever = (int(surface_words[sr, wi]) >> b) & 1
        scaling = combo_slope * float(i + 1) + 1.0
        if is_fever != 0:
            score += int(np.floor(base_value * scaling * fever_mul))
        else:
            score += int(np.floor(base_value * scaling))

    great_or = (
        int(surface_words[sr, 4])
        | int(surface_words[sr, 5])
        | int(surface_words[sr, 6])
        | int(surface_words[sr, 7])
    )
    if body_great > 0 or great_or != 0:
        if is_single_color != 0:
            great_head_base = (primary_val * 2) + 150
        else:
            great_head_base = (
                int(np.floor(float(primary_val) * (4.0 / 3.0)))
                + int(np.floor(float(secondary_val) * (2.0 / 3.0)))
                + 150
            )
        great_base = float(great_head_base)
        great_combo_val = int(np.floor(great_base * combo_mul))
        great_fever_val = int(np.floor(great_base * combo_mul * fever_mul))
        if body_great > 0:
            body_normal_great = body_great - body_fever_great
            if body_normal_great < 0:
                body_normal_great = 0
            body_normal_penalty = combo_val - great_combo_val
            if body_normal_penalty < 0:
                body_normal_penalty = 0
            body_fever_penalty = fever_val - great_fever_val
            if body_fever_penalty < 0:
                body_fever_penalty = 0
            score -= body_normal_great * body_normal_penalty
            score -= body_fever_great * body_fever_penalty
        if great_or != 0:
            for i in range(head_len):
                wi = i >> 5
                b = i & 31
                if ((int(surface_words[sr, 4 + wi]) >> b) & 1) != 0:
                    is_fever = (int(surface_words[sr, wi]) >> b) & 1
                    scaling = combo_slope * float(i + 1) + 1.0
                    if is_fever != 0:
                        perfect_val = int(np.floor(base_value * scaling * fever_mul))
                        great_val = int(np.floor(great_base * scaling * fever_mul))
                    else:
                        perfect_val = int(np.floor(base_value * scaling))
                        great_val = int(np.floor(great_base * scaling))
                    penalty = perfect_val - great_val
                    if penalty > 0:
                        score -= penalty
    return score


@jit(nopython=True, cache=True)
def _score_fg_response_groups_native_f64(
    group_offsets,
    group_lengths,
    row_meta,
    surface_pattern_ids,
    surface_pattern_words,
    surface_counts,
    surface_pattern_head_coeffs,
    color_flags,
    ref_pp,
    ref_cm,
    ref_fm,
    allow_pp,
    total_rows,
):
    """Native-f64 CPU twin of ``_fg_response_inner_group_kernel`` INCLUDING the gem search.

    Bit-for-bit f64 port of the GPU owner kernel: per group it enumerates the same gem
    allocations (the g_cm/g_fm/g_pp partition of ``residual_budget``) with the identical
    upper-bound prune, lexicographic tie-break, and per-term ``floor`` op order, scores every
    candidate surface, and keeps the group argmax. Runs in CPU doubles so it needs no GPU
    shaderFloat64 (MoltenVK/Metal has none, where the f32 GPU search mis-floors the razor-thin
    greats argmax and drops every FG candidate). ``residual_budget == 0`` collapses to a single
    allocation == current stats, identical to the prior gems-fixed serving twin.

    Output columns: [best_score, best_surface, g_pp, g_cm, g_fm, g_ov,
    final_pp, final_cm, final_fm, final_primary, final_secondary].
    """
    group_count = int(row_meta.shape[0])
    out = np.zeros((group_count, 11), dtype=np.int64)

    is_p_pp = int(color_flags[0])
    is_s_pp = int(color_flags[1])
    is_p_cm = int(color_flags[2])
    is_s_cm = int(color_flags[3])
    is_p_fm = int(color_flags[4])
    is_s_fm = int(color_flags[5])
    is_p_ov = int(color_flags[6])
    is_s_ov = int(color_flags[7])
    is_single_color = int(color_flags[8])

    pp_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
    pp_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
    cm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
    cm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
    fm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
    fm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
    ov_p_delta = ELEMENTAL_GEM_SCALE * is_p_ov
    ov_s_delta = ELEMENTAL_GEM_SCALE * is_s_ov
    w_pp = (pp_p_delta << 1) + pp_s_delta
    w_cm = (cm_p_delta << 1) + cm_s_delta
    w_fm = (fm_p_delta << 1) + fm_s_delta
    w_ov = (ov_p_delta << 1) + ov_s_delta
    delta_pp_vs_ov = w_pp - w_ov
    pp_primary_delta = pp_p_delta - ov_p_delta
    pp_secondary_delta = pp_s_delta - ov_s_delta

    for g in range(group_count):
        residual_budget = int(row_meta[g, 0])
        cur_pp = int(row_meta[g, 1])
        cur_cm = int(row_meta[g, 2])
        cur_fm = int(row_meta[g, 3])
        cur_primary = int(row_meta[g, 4])
        cur_secondary = int(row_meta[g, 5])
        head_len = int(row_meta[g, 6])
        body_total = int(row_meta[g, 7])
        if head_len > 100:
            head_len = 100

        max_pp_gems = 0
        if allow_pp and cur_pp < MAX_STAT_INDEX:
            rem_pp = MAX_STAT_INDEX - cur_pp
            max_pp_gems = rem_pp // GEM_SCALE_NORMAL
            if rem_pp % GEM_SCALE_NORMAL != 0:
                max_pp_gems += 1
        max_cm_gems = 0
        if cur_cm < MAX_STAT_INDEX:
            rem_cm = MAX_STAT_INDEX - cur_cm
            max_cm_gems = rem_cm // GEM_SCALE_NORMAL
            if rem_cm % GEM_SCALE_NORMAL != 0:
                max_cm_gems += 1
        max_fm_gems = 0
        if cur_fm < MAX_STAT_INDEX:
            rem_fm = MAX_STAT_INDEX - cur_fm
            max_fm_gems = rem_fm // GEM_SCALE_FEVER
            if rem_fm % GEM_SCALE_FEVER != 0:
                max_fm_gems += 1
        if max_pp_gems > residual_budget:
            max_pp_gems = residual_budget
        if max_cm_gems > residual_budget:
            max_cm_gems = residual_budget
        if max_fm_gems > residual_budget:
            max_fm_gems = residual_budget

        base_init = (cur_primary << 1) + cur_secondary
        pp_ref_base = ref_pp[_fg_clamp_ref_idx_native(cur_pp, total_rows)]
        cm_ref_cache = np.empty(max_cm_gems + 1, dtype=np.float64)
        for gc in range(max_cm_gems + 1):
            cm_ref_cache[gc] = ref_cm[_fg_clamp_ref_idx_native(cur_cm + gc * GEM_SCALE_NORMAL, total_rows)]
        fm_ref_cache = np.empty(max_fm_gems + 1, dtype=np.float64)
        for gf in range(max_fm_gems + 1):
            fm_ref_cache[gf] = ref_fm[_fg_clamp_ref_idx_native(cur_fm + gf * GEM_SCALE_FEVER, total_rows)]
        pp_ref_cache = np.empty(max_pp_gems + 1, dtype=np.float64)
        pp_bound_prefix_max = np.empty(max_pp_gems + 1, dtype=np.float64)
        pp_ref_cache[0] = pp_ref_base
        pp_bound_prefix_max[0] = pp_ref_base
        if allow_pp:
            running = -1.0e30
            for gp in range(max_pp_gems + 1):
                v = ref_pp[_fg_clamp_ref_idx_native(cur_pp + gp * GEM_SCALE_NORMAL, total_rows)]
                pp_ref_cache[gp] = v
                bound = float(gp * delta_pp_vs_ov) + v
                if bound > running:
                    running = bound
                pp_bound_prefix_max[gp] = running

        group_best_score = -1
        group_best_surface = 0
        group_best_pp = 0
        group_best_cm = 0
        group_best_fm = 0
        group_best_ov = residual_budget
        group_best_final_pp = cur_pp
        group_best_final_cm = cur_cm
        group_best_final_fm = cur_fm
        group_best_final_primary = cur_primary + group_best_ov * ov_p_delta
        group_best_final_secondary = cur_secondary + group_best_ov * ov_s_delta

        start = int(group_offsets[g])
        length = int(group_lengths[g])
        for ls in range(length):
            sr = start + ls
            pattern_row = int(surface_pattern_ids[sr])
            body_fever = int(surface_counts[sr, 0])
            body_great = int(surface_counts[sr, 1])
            body_fever_great = int(surface_counts[sr, 2])
            body_normal = body_total - body_fever
            if body_normal < 0:
                body_normal = 0
            n_hn = int(surface_pattern_head_coeffs[pattern_row, 0])
            n_hf = int(surface_pattern_head_coeffs[pattern_row, 1])
            sigma_hn = int(surface_pattern_head_coeffs[pattern_row, 2])
            sigma_hf = int(surface_pattern_head_coeffs[pattern_row, 3])

            best_score = group_best_score
            best_pp = group_best_pp
            best_cm = group_best_cm
            best_fm = group_best_fm
            best_ov = group_best_ov
            best_final_pp = group_best_final_pp
            best_final_cm = group_best_final_cm
            best_final_fm = group_best_final_fm
            best_final_primary = group_best_final_primary
            best_final_secondary = group_best_final_secondary

            g_cm = 0
            while g_cm <= max_cm_gems:
                leftover_after_cm = residual_budget - g_cm
                if leftover_after_cm < 0:
                    break
                cm_stat = cur_cm + g_cm * GEM_SCALE_NORMAL
                cm_mul = cm_ref_cache[g_cm]
                g_fm_max = max_fm_gems
                if g_fm_max > leftover_after_cm:
                    g_fm_max = leftover_after_cm
                g_fm = 0
                while g_fm <= g_fm_max:
                    leftover_after_fm = leftover_after_cm - g_fm
                    fm_stat = cur_fm + g_fm * GEM_SCALE_FEVER
                    fm_mul = fm_ref_cache[g_fm]
                    g_pp_max = max_pp_gems
                    if g_pp_max > leftover_after_fm:
                        g_pp_max = leftover_after_fm

                    base_linear_common = base_init + (g_cm * w_cm) + (g_fm * w_fm) + (leftover_after_fm * w_ov)
                    if allow_pp:
                        max_base_value = float(base_linear_common) + pp_bound_prefix_max[g_pp_max]
                    else:
                        max_base_value = float(base_linear_common) + pp_ref_base
                    ub = _fg_response_upper_bound_native_f64(
                        max_base_value, cm_mul, fm_mul, body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf
                    )

                    if ub > float(best_score):
                        primary_base = cur_primary + g_cm * cm_p_delta + g_fm * fm_p_delta + leftover_after_fm * ov_p_delta
                        secondary_base = (
                            cur_secondary + g_cm * cm_s_delta + g_fm * fm_s_delta + leftover_after_fm * ov_s_delta
                        )
                        if allow_pp and max_pp_gems > 0:
                            g_pp = 0
                            while g_pp <= g_pp_max:
                                g_ov = leftover_after_fm - g_pp
                                pp_stat = cur_pp + g_pp * GEM_SCALE_NORMAL
                                primary_val = primary_base + g_pp * pp_primary_delta
                                secondary_val = secondary_base + g_pp * pp_secondary_delta
                                pp_base_value = float(base_linear_common + g_pp * delta_pp_vs_ov) + pp_ref_cache[g_pp]
                                pp_ub = _fg_response_upper_bound_native_f64(
                                    pp_base_value, cm_mul, fm_mul, body_fever, body_normal, n_hn, n_hf, sigma_hn, sigma_hf
                                )
                                if pp_ub >= float(best_score):
                                    score = _fg_response_surface_score_native_f64(
                                        surface_pattern_words,
                                        pattern_row,
                                        body_fever,
                                        body_great,
                                        body_fever_great,
                                        head_len,
                                        body_total,
                                        primary_val,
                                        secondary_val,
                                        pp_ref_cache[g_pp],
                                        cm_mul,
                                        fm_mul,
                                        is_single_color,
                                    )
                                    if score > best_score or (
                                        score == best_score
                                        and (
                                            g_cm < best_cm
                                            or (
                                                g_cm == best_cm
                                                and (g_fm < best_fm or (g_fm == best_fm and g_pp < best_pp))
                                            )
                                        )
                                    ):
                                        best_score = score
                                        best_pp = g_pp
                                        best_cm = g_cm
                                        best_fm = g_fm
                                        best_ov = g_ov
                                        best_final_pp = pp_stat
                                        best_final_cm = cm_stat
                                        best_final_fm = fm_stat
                                        best_final_primary = primary_val
                                        best_final_secondary = secondary_val
                                g_pp += 1
                        else:
                            pp_factor = pp_ref_cache[0] if allow_pp else pp_ref_base
                            score = _fg_response_surface_score_native_f64(
                                surface_pattern_words,
                                pattern_row,
                                body_fever,
                                body_great,
                                body_fever_great,
                                head_len,
                                body_total,
                                primary_base,
                                secondary_base,
                                pp_factor,
                                cm_mul,
                                fm_mul,
                                is_single_color,
                            )
                            if score > best_score or (
                                score == best_score
                                and (
                                    g_cm < best_cm
                                    or (g_cm == best_cm and (g_fm < best_fm or (g_fm == best_fm and 0 < best_pp)))
                                )
                            ):
                                best_score = score
                                best_pp = 0
                                best_cm = g_cm
                                best_fm = g_fm
                                best_ov = leftover_after_fm
                                best_final_pp = cur_pp
                                best_final_cm = cm_stat
                                best_final_fm = fm_stat
                                best_final_primary = primary_base
                                best_final_secondary = secondary_base
                    g_fm += 1
                g_cm += 1

            if best_score > group_best_score:
                group_best_score = best_score
                group_best_surface = ls
                group_best_pp = best_pp
                group_best_cm = best_cm
                group_best_fm = best_fm
                group_best_ov = best_ov
                group_best_final_pp = best_final_pp
                group_best_final_cm = best_final_cm
                group_best_final_fm = best_final_fm
                group_best_final_primary = best_final_primary
                group_best_final_secondary = best_final_secondary

        out[g, 0] = group_best_score
        out[g, 1] = group_best_surface
        out[g, 2] = group_best_pp
        out[g, 3] = group_best_cm
        out[g, 4] = group_best_fm
        out[g, 5] = group_best_ov
        out[g, 6] = group_best_final_pp
        out[g, 7] = group_best_final_cm
        out[g, 8] = group_best_final_fm
        out[g, 9] = group_best_final_primary
        out[g, 10] = group_best_final_secondary
    return out


def _score_response_group_meta_cpu(
    *,
    group_meta: np.ndarray,
    group_offsets: np.ndarray,
    group_lengths: np.ndarray,
    primary_color: str,
    secondary_color: str,
    selected_color: str,
    ref_arrays: dict[str, Any],
    surface_pattern_ids: np.ndarray,
    surface_pattern_words: np.ndarray,
    surface_counts: np.ndarray,
    surface_pattern_head_coeffs: np.ndarray,
) -> tuple[np.ndarray, int]:
    """Native-f64 CPU twin of ``_score_response_group_meta_gpu`` for BOTH the gems-fixed
    (zero_ms / total_budget == 0) on-demand serving path AND the gem-search (total_budget > 0)
    optimizer path. Same exact algorithm and exact f64 arithmetic as the GPU kernel (including
    the gem-allocation enumeration, upper-bound prune, and lexicographic tie-break); runs on
    CPU doubles so it needs no GPU shaderFloat64 (MoltenVK/Metal has none -- there the f32 GPU
    search mis-floors the razor-thin greats argmax and drops every FG candidate). Parallelizes
    per request across cores instead of serializing on the single GPU."""
    group_count = int(group_meta.shape[0])
    if group_count != int(group_offsets.shape[0]) or group_count != int(group_lengths.shape[0]):
        raise ValueError("response frontier CPU group metadata arrays have inconsistent lengths")
    logical_surface_rows = int(np.sum(group_lengths, dtype=np.int64))
    if logical_surface_rows <= 0:
        return np.zeros((0, 11), dtype=np.int32), 0

    group_meta_all = np.ascontiguousarray(group_meta, dtype=np.int32)
    if int(group_meta_all.shape[1]) < 8:
        raise ValueError("response frontier CPU group metadata requires head/body columns")

    flags = _color_flags(primary_color, secondary_color, selected_color)
    color_flags_all = np.ascontiguousarray(np.asarray(flags, dtype=np.int32))
    # PP gems are the Chill element; the GPU search only enumerates PP gems when the song
    # carries a Chill color (flags[0]/[1]). Mirror that gate exactly.
    allow_pp = bool(int(flags[0]) != 0 or int(flags[1]) != 0)
    exact_ref_arrays = _response_inner_score_ref_arrays(ref_arrays)
    # CPU exact-rescore path stays float64 (the numba scorer is the f64 authority), independent
    # of the GPU search fp.
    ref_pp = np.ascontiguousarray(np.asarray(exact_ref_arrays["Perfect Points"], dtype=np.float64))
    ref_cm = np.ascontiguousarray(np.asarray(exact_ref_arrays["Combo Multiplier"], dtype=np.float64))
    ref_fm = np.ascontiguousarray(np.asarray(exact_ref_arrays["Fever Multiplier"], dtype=np.float64))
    surface_pattern_ids_all = np.ascontiguousarray(surface_pattern_ids, dtype=np.int32)
    surface_pattern_words_all = np.ascontiguousarray(surface_pattern_words, dtype=np.uint32)
    surface_counts_all = np.ascontiguousarray(surface_counts, dtype=np.int32)
    surface_pattern_head_coeffs_all = np.ascontiguousarray(surface_pattern_head_coeffs, dtype=np.int32)
    if int(surface_pattern_ids_all.shape[0]) != int(surface_counts_all.shape[0]):
        raise ValueError("response frontier CPU surface arrays have inconsistent lengths")
    if (
        int(surface_pattern_ids_all.ndim) != 1
        or int(surface_pattern_words_all.ndim) != 2
        or int(surface_pattern_words_all.shape[1]) != 8
        or int(surface_counts_all.ndim) != 2
        or int(surface_counts_all.shape[1]) != 3
        or int(surface_pattern_head_coeffs_all.ndim) != 2
        or int(surface_pattern_head_coeffs_all.shape[0]) != int(surface_pattern_words_all.shape[0])
        or int(surface_pattern_head_coeffs_all.shape[1]) != 4
    ):
        raise ValueError("response frontier CPU surface arrays have invalid shape")
    if bool(np.any(surface_pattern_ids_all < 0)) or bool(
        np.any(surface_pattern_ids_all >= int(surface_pattern_words_all.shape[0]))
    ):
        raise ValueError("response frontier CPU surface references an invalid head-pattern ID")
    if bool(np.any(surface_counts_all < 0)):
        raise ValueError("response frontier CPU surface counts must be nonnegative")

    head_lengths = np.unique(np.ascontiguousarray(group_meta_all[:, 6], dtype=np.int32))
    if int(head_lengths.shape[0]) != 1:
        raise ValueError("response frontier CPU group metadata has inconsistent head length")
    out_rows = _score_fg_response_groups_native_f64(
        np.ascontiguousarray(group_offsets, dtype=np.int64),
        np.ascontiguousarray(group_lengths, dtype=np.int64),
        group_meta_all,
        surface_pattern_ids_all,
        surface_pattern_words_all,
        surface_counts_all,
        surface_pattern_head_coeffs_all,
        color_flags_all,
        ref_pp,
        ref_cm,
        ref_fm,
        bool(allow_pp),
        int(TOTAL_ROWS),
    )
    return np.asarray(out_rows, dtype=np.int32), int(logical_surface_rows)
