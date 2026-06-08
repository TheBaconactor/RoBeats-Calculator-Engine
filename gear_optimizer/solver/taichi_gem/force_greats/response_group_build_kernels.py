"""GPU (Taichi/Vulkan) port of the FG response-frontier group-row reduction.

Bit-exact reimplementation of `_build_response_group_rows_numba`
(see response_frontier.py). Integer-only and serialized per candidate, so the
Vulkan result is identical to the CPU/Numba oracle by construction.

The Numba builder remains the parity oracle in tests. Production uses this GPU
builder as the single group-row construction path; no toggles / no fallbacks
(CLAUDE.md).

Scratch (head/tail/next/ordered/best/keep_mask) lives in persistent Taichi fields,
NOT in read/write ndarray kernel args: mixing read/write ndarray scratch with
read-only ndarray inputs triggers a device-buffer aliasing bug across launches
(read-only inputs get clobbered on re-launch). The proven-repeatable kernels in
this package (response_inner_host) pass only read-only input ndarrays + write-only
output ndarrays, which is the pattern mirrored here.

Two-phase count-then-emit (host computes the exclusive prefix sum of keep_counts
between launches, because the total output length is data-dependent).
"""
import numpy as np
import taichi as ti

from gear_optimizer.core.constants import GEM_SCALE_FEVER, TOTAL_GEM_BUDGET, TOTAL_ROWS
from gear_optimizer.solver.taichi_gem import api as gem_api

_INT_MIN = -2147483648

# Capacity bounds (GPU-safety: real shape bounds, fail-loud if exceeded).
_MAX_PAIRS = (TOTAL_GEM_BUDGET + 1) * (TOTAL_GEM_BUDGET + 2) // 2  # ftff combo count at full budget (4186 @ B=90)
_MAX_FRONTIERS = (TOTAL_ROWS + 1) * (TOTAL_ROWS + 1)  # frontier ids come from the full clipped stat grid
_MAX_CAND = 256  # candidate batch cap; production funnel is LOADOUTS_PER_SONG_LIMIT=51

# scratch_frontier columns
_H = 0  # head
_T = 1  # tail
_BP = 2  # best_pos
_BR = 3  # best_residual
# scratch_pos columns
_NX = 0  # next_idx
_OF = 1  # ordered_frontiers
# group_ftff columns
_FT = 0
_FF = 1
_FTS = 2
_FFS = 3

# Persistent scratch fields (allocated lazily on first use via an independent
# FieldsBuilder tree, so this module is self-contained and does not require
# wiring into the main fields allocation).
_FB = None
_sf = None  # scratch_frontier (_MAX_FRONTIERS, 4)
_sp = None  # scratch_pos (_MAX_PAIRS, 2)
_km = None  # keep_mask (_MAX_CAND, _MAX_PAIRS)
_kc = None  # keep_counts (_MAX_CAND,)
_wb = None  # write_base (_MAX_CAND,)
_err = None  # (1,)
_BUILT_AGAINST = None  # gpu_fields.ga_fg_candidates_packed handle the FieldsBuilder was finalized against


def _ensure_fields() -> None:
    """Allocate the scratch fields, rebuilding after a Taichi reset.

    `hard_reset_taichi` (Vulkan recovery / periodic reset / pytest module isolation)
    re-initializes the runtime and frees ALL SNode trees, including this independent
    FieldsBuilder tree, leaving the cached field handles dangling (a hard crash on next
    access). We detect a reset by keying on a core GA field handle that the main
    allocation re-creates on every (re)init: if it changed, our tree was freed too and
    we rebuild.
    """
    global _FB, _sf, _sp, _km, _kc, _wb, _err, _BUILT_AGAINST
    gem_api.ensure_ready()
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

    sentinel = gpu_fields.ga_fg_candidates_packed
    if _FB is not None and _BUILT_AGAINST is sentinel:
        return
    sf = ti.field(ti.i32)
    sp = ti.field(ti.i32)
    km = ti.field(ti.i32)
    kc = ti.field(ti.i32)
    wb = ti.field(ti.i32)
    err = ti.field(ti.i32)
    fb = ti.FieldsBuilder()
    fb.dense(ti.ij, (_MAX_FRONTIERS, 4)).place(sf)
    fb.dense(ti.ij, (_MAX_PAIRS, 2)).place(sp)
    fb.dense(ti.ij, (_MAX_CAND, _MAX_PAIRS)).place(km)
    fb.dense(ti.i, _MAX_CAND).place(kc)
    fb.dense(ti.i, _MAX_CAND).place(wb)
    fb.dense(ti.i, 1).place(err)
    fb.finalize()
    _sf, _sp, _km, _kc, _wb, _err, _FB, _BUILT_AGAINST = sf, sp, km, kc, wb, err, fb, sentinel


@ti.func
def _clip_stat(value: ti.i32) -> ti.i32:
    out = value
    if out < 0:
        out = 0
    if out > TOTAL_ROWS:
        out = TOTAL_ROWS
    return out


@ti.kernel
def _fg_count_group_rows_kernel(
    candidate_count: ti.i32,
    pair_count: ti.i32,
    max_frontier: ti.i32,
    score_elements_constant: ti.i32,
    base_components: ti.types.ndarray(dtype=ti.i32, ndim=2),
    ft_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ff_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    residual_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    frontier_idx_by_stat: ti.types.ndarray(dtype=ti.i32, ndim=2),
    primary_ftff_delta_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    secondary_ftff_delta_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    ti.loop_config(serialize=True)
    for candidate_idx in range(candidate_count):
        base_primary = base_components[candidate_idx, 3]
        base_secondary = base_components[candidate_idx, 4]
        base_ft = base_components[candidate_idx, 5]
        base_ff = base_components[candidate_idx, 6]
        for pos in range(pair_count):
            _km[candidate_idx, pos] = 0
        if score_elements_constant != 0:
            for fid in range(max_frontier + 1):
                _sf[fid, _BP] = -1
                _sf[fid, _BR] = _INT_MIN
            for pos in range(pair_count):
                ft_stat = _clip_stat(base_ft + ft_values[pos] * GEM_SCALE_FEVER)
                ff_stat = _clip_stat(base_ff + ff_values[pos] * GEM_SCALE_FEVER)
                frontier_id = frontier_idx_by_stat[ft_stat, ff_stat]
                if frontier_id < 0:
                    _err[0] = 1
                else:
                    residual = residual_values[pos]
                    current_pos = _sf[frontier_id, _BP]
                    if (
                        current_pos < 0
                        or residual > _sf[frontier_id, _BR]
                        or (residual == _sf[frontier_id, _BR] and pos < current_pos)
                    ):
                        _sf[frontier_id, _BP] = pos
                        _sf[frontier_id, _BR] = residual
            kept_count = 0
            for pos in range(pair_count):
                ft_stat = _clip_stat(base_ft + ft_values[pos] * GEM_SCALE_FEVER)
                ff_stat = _clip_stat(base_ff + ff_values[pos] * GEM_SCALE_FEVER)
                frontier_id = frontier_idx_by_stat[ft_stat, ff_stat]
                if frontier_id >= 0 and _sf[frontier_id, _BP] == pos:
                    _km[candidate_idx, pos] = 1
                    kept_count += 1
            _kc[candidate_idx] = kept_count
        else:
            for fid in range(max_frontier + 1):
                _sf[fid, _H] = -1
                _sf[fid, _T] = -1
            for pos in range(pair_count):
                _sp[pos, _NX] = -1
            ordered_count = 0
            for pos in range(pair_count):
                ft_stat = _clip_stat(base_ft + ft_values[pos] * GEM_SCALE_FEVER)
                ff_stat = _clip_stat(base_ff + ff_values[pos] * GEM_SCALE_FEVER)
                frontier_id = frontier_idx_by_stat[ft_stat, ff_stat]
                if frontier_id < 0:
                    _err[0] = 1
                else:
                    if _sf[frontier_id, _H] < 0:
                        _sf[frontier_id, _H] = pos
                        _sf[frontier_id, _T] = pos
                        _sp[ordered_count, _OF] = frontier_id
                        ordered_count += 1
                    else:
                        _sp[_sf[frontier_id, _T], _NX] = pos
                        _sf[frontier_id, _T] = pos
            kept_count = 0
            for order_idx in range(ordered_count):
                frontier_id = _sp[order_idx, _OF]
                first = _sf[frontier_id, _H]
                first_primary = base_primary + primary_ftff_delta_values[first]
                first_secondary = base_secondary + secondary_ftff_delta_values[first]
                same_score_elements = 1
                best_idx = first
                best_res = residual_values[first]
                row = _sp[first, _NX]
                while row >= 0:
                    primary = base_primary + primary_ftff_delta_values[row]
                    secondary = base_secondary + secondary_ftff_delta_values[row]
                    if primary != first_primary or secondary != first_secondary:
                        same_score_elements = 0
                        break
                    residual = residual_values[row]
                    if residual > best_res:
                        best_idx = row
                        best_res = residual
                    row = _sp[row, _NX]
                if same_score_elements != 0:
                    _km[candidate_idx, best_idx] = 1
                    kept_count += 1
                else:
                    row = first
                    while row >= 0:
                        row_residual = residual_values[row]
                        row_primary = base_primary + primary_ftff_delta_values[row]
                        row_secondary = base_secondary + secondary_ftff_delta_values[row]
                        dominated = 0
                        other = first
                        while other >= 0:
                            if other != row:
                                other_residual = residual_values[other]
                                other_primary = base_primary + primary_ftff_delta_values[other]
                                other_secondary = base_secondary + secondary_ftff_delta_values[other]
                                if (
                                    other_residual >= row_residual
                                    and other_primary >= row_primary
                                    and other_secondary >= row_secondary
                                    and (
                                        other_residual > row_residual
                                        or other_primary > row_primary
                                        or other_secondary > row_secondary
                                        or other < row
                                    )
                                ):
                                    dominated = 1
                                    break
                            other = _sp[other, _NX]
                        if dominated == 0:
                            _km[candidate_idx, row] = 1
                            kept_count += 1
                        row = _sp[row, _NX]
            _kc[candidate_idx] = kept_count


@ti.kernel
def _fg_emit_group_rows_kernel(
    candidate_count: ti.i32,
    pair_count: ti.i32,
    max_frontier: ti.i32,
    score_elements_constant: ti.i32,
    head_len: ti.i32,
    body_total: ti.i32,
    base_components: ti.types.ndarray(dtype=ti.i32, ndim=2),
    ft_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ff_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    residual_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    frontier_idx_by_stat: ti.types.ndarray(dtype=ti.i32, ndim=2),
    primary_ftff_delta_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    secondary_ftff_delta_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_meta: ti.types.ndarray(dtype=ti.i32, ndim=2),
    group_ftff: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    ti.loop_config(serialize=True)
    for candidate_idx in range(candidate_count):
        base_pp = base_components[candidate_idx, 0]
        base_cm = base_components[candidate_idx, 1]
        base_fm = base_components[candidate_idx, 2]
        base_primary = base_components[candidate_idx, 3]
        base_secondary = base_components[candidate_idx, 4]
        base_ft = base_components[candidate_idx, 5]
        base_ff = base_components[candidate_idx, 6]
        write = _wb[candidate_idx]
        for fid in range(max_frontier + 1):
            _sf[fid, _H] = -1
            _sf[fid, _T] = -1
            _sf[fid, _BP] = -1
            _sf[fid, _BR] = _INT_MIN
        for pos in range(pair_count):
            _sp[pos, _NX] = -1
        ordered_count = 0
        for pos in range(pair_count):
            ft_stat = _clip_stat(base_ft + ft_values[pos] * GEM_SCALE_FEVER)
            ff_stat = _clip_stat(base_ff + ff_values[pos] * GEM_SCALE_FEVER)
            frontier_id = frontier_idx_by_stat[ft_stat, ff_stat]
            if frontier_id < 0:
                _err[0] = 1
            else:
                if _sf[frontier_id, _H] < 0:
                    _sf[frontier_id, _H] = pos
                    _sf[frontier_id, _T] = pos
                    _sp[ordered_count, _OF] = frontier_id
                    ordered_count += 1
                else:
                    _sp[_sf[frontier_id, _T], _NX] = pos
                    _sf[frontier_id, _T] = pos
                if score_elements_constant != 0:
                    residual = residual_values[pos]
                    current_pos = _sf[frontier_id, _BP]
                    if (
                        current_pos < 0
                        or residual > _sf[frontier_id, _BR]
                        or (residual == _sf[frontier_id, _BR] and pos < current_pos)
                    ):
                        _sf[frontier_id, _BP] = pos
                        _sf[frontier_id, _BR] = residual
        for order_idx in range(ordered_count):
            frontier_id = _sp[order_idx, _OF]
            if score_elements_constant != 0:
                pos = _sf[frontier_id, _BP]
                if pos >= 0:
                    ft = ft_values[pos]
                    ff = ff_values[pos]
                    ft_stat = _clip_stat(base_ft + ft * GEM_SCALE_FEVER)
                    ff_stat = _clip_stat(base_ff + ff * GEM_SCALE_FEVER)
                    group_meta[write, 0] = residual_values[pos]
                    group_meta[write, 1] = base_pp
                    group_meta[write, 2] = base_cm
                    group_meta[write, 3] = base_fm
                    group_meta[write, 4] = base_primary + primary_ftff_delta_values[pos]
                    group_meta[write, 5] = base_secondary + secondary_ftff_delta_values[pos]
                    group_meta[write, 6] = head_len
                    group_meta[write, 7] = body_total
                    group_ftff[write, _FT] = ft
                    group_ftff[write, _FF] = ff
                    group_ftff[write, _FTS] = ft_stat
                    group_ftff[write, _FFS] = ff_stat
                    write += 1
            else:
                row = _sf[frontier_id, _H]
                while row >= 0:
                    if _km[candidate_idx, row] != 0:
                        ft = ft_values[row]
                        ff = ff_values[row]
                        ft_stat = _clip_stat(base_ft + ft * GEM_SCALE_FEVER)
                        ff_stat = _clip_stat(base_ff + ff * GEM_SCALE_FEVER)
                        group_meta[write, 0] = residual_values[row]
                        group_meta[write, 1] = base_pp
                        group_meta[write, 2] = base_cm
                        group_meta[write, 3] = base_fm
                        group_meta[write, 4] = base_primary + primary_ftff_delta_values[row]
                        group_meta[write, 5] = base_secondary + secondary_ftff_delta_values[row]
                        group_meta[write, 6] = head_len
                        group_meta[write, 7] = body_total
                        group_ftff[write, _FT] = ft
                        group_ftff[write, _FF] = ff
                        group_ftff[write, _FTS] = ft_stat
                        group_ftff[write, _FFS] = ff_stat
                        write += 1
                    row = _sp[row, _NX]


def build_response_group_rows_gpu(
    base_components: np.ndarray,
    ft_values: np.ndarray,
    ff_values: np.ndarray,
    residual_values: np.ndarray,
    frontier_idx_by_stat: np.ndarray,
    primary_ftff_delta_values: np.ndarray,
    secondary_ftff_delta_values: np.ndarray,
    score_elements_constant: bool,
    head_len: int,
    body_total: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """GPU equivalent of `_build_response_group_rows_numba`; identical 6-tuple result.

    Returns (group_meta, group_ft, group_ff, group_ft_stat, group_ff_stat, candidate_slices).
    """
    base_components = np.ascontiguousarray(base_components, dtype=np.int32)
    ft_values = np.ascontiguousarray(ft_values, dtype=np.int32)
    ff_values = np.ascontiguousarray(ff_values, dtype=np.int32)
    residual_values = np.ascontiguousarray(residual_values, dtype=np.int32)
    frontier_idx_by_stat = np.ascontiguousarray(frontier_idx_by_stat, dtype=np.int32)
    primary_ftff_delta_values = np.ascontiguousarray(primary_ftff_delta_values, dtype=np.int32)
    secondary_ftff_delta_values = np.ascontiguousarray(secondary_ftff_delta_values, dtype=np.int32)

    candidate_count = int(base_components.shape[0])
    pair_count = int(ft_values.shape[0])
    if candidate_count <= 0 or pair_count <= 0:
        raise ValueError("response frontier exact group builder received no work")
    max_frontier = int(frontier_idx_by_stat.max())
    if max_frontier < 0:
        raise ValueError("response frontier exact group builder received no loaded frontiers")
    if candidate_count > _MAX_CAND:
        raise ValueError(f"response frontier group builder candidate_count {candidate_count} exceeds cap {_MAX_CAND}")
    if pair_count > _MAX_PAIRS:
        raise ValueError(f"response frontier group builder pair_count {pair_count} exceeds cap {_MAX_PAIRS}")
    if max_frontier >= _MAX_FRONTIERS:
        raise ValueError(f"response frontier group builder max_frontier {max_frontier} exceeds cap {_MAX_FRONTIERS}")

    _ensure_fields()
    _err[0] = 0
    _fg_count_group_rows_kernel(
        candidate_count,
        pair_count,
        max_frontier,
        1 if bool(score_elements_constant) else 0,
        base_components,
        ft_values,
        ff_values,
        residual_values,
        frontier_idx_by_stat,
        primary_ftff_delta_values,
        secondary_ftff_delta_values,
    )
    ti.sync()
    if int(_err[0]) != 0:
        raise ValueError("FG response frontier prewarmed scoring bundle does not cover requested stat keys")

    keep_counts = _kc.to_numpy()[:candidate_count]
    write_base = np.zeros((candidate_count,), dtype=np.int32)
    running = 0
    for candidate_idx in range(candidate_count):
        count = int(keep_counts[candidate_idx])
        if count <= 0:
            raise ValueError("response frontier exact GPU batch produced no pair result")
        write_base[candidate_idx] = running
        _wb[candidate_idx] = running
        running += count
    total_count = running

    group_meta = np.zeros((total_count, 8), dtype=np.int32)
    group_ftff = np.zeros((total_count, 4), dtype=np.int32)
    _fg_emit_group_rows_kernel(
        candidate_count,
        pair_count,
        max_frontier,
        1 if bool(score_elements_constant) else 0,
        int(head_len),
        int(body_total),
        base_components,
        ft_values,
        ff_values,
        residual_values,
        frontier_idx_by_stat,
        primary_ftff_delta_values,
        secondary_ftff_delta_values,
        group_meta,
        group_ftff,
    )
    ti.sync()
    if int(_err[0]) != 0:
        raise ValueError("FG response frontier prewarmed scoring bundle does not cover requested stat keys")

    candidate_slices = np.empty((candidate_count, 2), dtype=np.int32)
    candidate_slices[:, 0] = write_base
    candidate_slices[:, 1] = np.asarray(keep_counts, dtype=np.int32)
    group_ft = np.ascontiguousarray(group_ftff[:, _FT])
    group_ff = np.ascontiguousarray(group_ftff[:, _FF])
    group_ft_stat = np.ascontiguousarray(group_ftff[:, _FTS])
    group_ff_stat = np.ascontiguousarray(group_ftff[:, _FFS])
    return group_meta, group_ft, group_ff, group_ft_stat, group_ff_stat, candidate_slices
