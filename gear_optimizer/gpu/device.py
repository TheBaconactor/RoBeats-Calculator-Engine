"""A process's GPU state: Taichi, the fields and the tables that never change (ensure_ready), then what a song uploads."""

from __future__ import annotations

import numpy as np

from gear_optimizer.frontier.timeline_producer import GRID_SIZE, TimelineFrontierGridPayload
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.rules import GEM_BUDGET, STAT_GEM_GAIN_NORMAL
from gear_optimizer.solver.ftff_combos import FtffShortlist, ftff_combo_arrays

from . import fields, kernels
from .runtime import init_taichi, reset_taichi, ti

_ready = False
_timeline_key: tuple | None = None


def _pp_best_gems_prefix(pp_ref: np.ndarray) -> np.ndarray:
    """(flags, PP stat, gems) -> the PP gems of the best PP/element split of at most `gems` gems: removes the inner O(B)
    PP scan from each (CM, FM) pair of the exact gem search (O(B^3) -> O(B^2))."""
    gems = np.arange(GEM_BUDGET + 1, dtype=np.int32)
    cur_pp = np.arange(GRID_SIZE, dtype=np.int32)[:, None]
    pp_extra = pp_ref[np.minimum(cur_pp + (gems[None, :] * STAT_GEM_GAIN_NORMAL), GRID_SIZE - 1)]
    deltas = np.array([((6 * (flags & 1)) + (3 * ((flags >> 1) & 1))) - ((12 * ((flags >> 2) & 1)) + (6 * ((flags >> 3) & 1)))
                       for flags in range(16)], dtype=np.int32)
    extra = pp_extra[None, :, :] + (deltas[:, None, None].astype(np.float32) * gems[None, None, :])
    best_idx = np.zeros((16, GRID_SIZE, GEM_BUDGET + 1), dtype=np.int16)
    best_val = extra[:, :, 0].copy()
    for g_pp in range(1, GEM_BUDGET + 1):
        best_idx[:, :, g_pp] = best_idx[:, :, g_pp - 1]
        better = extra[:, :, g_pp] > best_val
        best_idx[:, :, g_pp][better] = g_pp
        best_val[better] = extra[:, :, g_pp][better]
    return best_idx


def ensure_ready() -> None:
    global _ready
    if _ready:
        return
    init_taichi()
    fields.allocate_fields()
    curves = stat_curves().f32
    fields.ref_pp_field.from_numpy(curves["Perfect Points"])
    fields.ref_cm_field.from_numpy(curves["Combo Multiplier"])
    fields.ref_fm_field.from_numpy(curves["Fever Multiplier"])
    fields.exact_pp_best_gems_prefix.from_numpy(_pp_best_gems_prefix(curves["Perfect Points"]))
    ft, ff, _budget_left = ftff_combo_arrays(GEM_BUDGET)
    fields.ftff_combo_ft.from_numpy(ft.astype(np.int32))
    fields.ftff_combo_ff.from_numpy(ff.astype(np.int32))
    _ready = True


def hard_reset(reason: str) -> None:
    """Taichi reset (frees its Vulkan resources; every field is gone): the next ensure_ready starts over."""
    global _ready, _timeline_key
    reset_taichi(reason=reason)
    _ready = False
    _timeline_key = None


def upload_timeline(key: tuple, payload: TimelineFrontierGridPayload) -> None:
    """The song's timeline frontier, once per song. A new timeline also ends the evaluation memo, whose results hold for
    one song (its genomes' pre-gem stats are the memo's key, so it outlives the batches of a song)."""
    global _timeline_key
    if key == _timeline_key:
        return
    fields.ga_eval_cache_key.fill(0)

    def cell(array: np.ndarray, dtype) -> np.ndarray:
        return np.ascontiguousarray(np.asarray(array, dtype=dtype)[0])

    fields.grid_body_total.from_numpy(
        cell(payload.grid_count_body_fever, np.int32) + cell(payload.grid_count_body_normal, np.int32)
    )
    fields.grid_head_len.from_numpy(cell(payload.grid_head_len, np.int8))
    fields.grid_frontier_count.from_numpy(cell(payload.grid_frontier_count, np.int32))
    fields.grid_frontier_offset.from_numpy(cell(payload.grid_frontier_offset, np.int32))
    used = int(payload.frontier_pool_used)
    kernels.upload_surfaces_kernel(
        used,
        cell(payload.grid_frontier_body_fever_pool, np.int32)[:used],
        cell(payload.grid_frontier_body_normal_pool, np.int32)[:used],
        cell(payload.grid_frontier_masks_bits_pool, np.uint32)[:used],
        cell(payload.grid_frontier_head_coeffs_pool, np.int16)[:used],
    )
    _timeline_key = key


def upload_items(item_stats: np.ndarray, slot_start: np.ndarray, slot_count: np.ndarray, base_fixed_stats: np.ndarray) -> None:
    n_items = len(item_stats)
    if n_items > fields.MAX_ITEMS:
        raise ValueError(f"Too many items: {n_items} > {fields.MAX_ITEMS}")
    kernels.upload_items_kernel(
        np.ascontiguousarray(item_stats[:, : fields.ITEM_STAT_DIM], dtype=np.int32),
        n_items,
        np.ascontiguousarray(slot_start, dtype=np.int32),
        np.ascontiguousarray(slot_count, dtype=np.int32),
    )
    fields.base_fixed_stats.from_numpy(np.asarray(base_fixed_stats, dtype=np.int32))


def upload_shortlist(shortlist: FtffShortlist) -> tuple:
    """A song's FT/FF combo shortlist on the device: search_combos_kernel's arguments."""
    arrays = []
    for values in (shortlist.start, shortlist.count, shortlist.combos):
        array = ti.ndarray(dtype=ti.i32, shape=(max(1, len(values)),))
        if len(values):
            array.from_numpy(np.ascontiguousarray(values, dtype=np.int32))
        arrays.append(array)
    return tuple(arrays)
