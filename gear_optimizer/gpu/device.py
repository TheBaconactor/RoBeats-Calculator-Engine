"""A process's GPU state: Taichi, the fields and the tables that never change (ensure_ready), then what a song uploads."""

from __future__ import annotations

import numpy as np

from gear_optimizer.frontier.timeline_producer import GRID_SIZE, TimelineFrontierGridPayload
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.rules import GEM_BUDGET, STAT_GEM_GAIN_NORMAL
from gear_optimizer.solver.ftff_combos import FtffShortlist, ftff_combo_arrays

from . import fields, kernels
from .runtime import init_taichi, register_reset_hook, reset_taichi, ti
from .scoring import float64_words

_ready = False
_timeline_key: tuple | None = None
# Byte-identical inputs already on the device need no second transfer: each label's last uploaded copies, and the
# shortlist's device arrays (reused as kernel arguments).
_ga_uploads: dict[str, tuple[np.ndarray, ...]] = {}
_shortlist_arrays: tuple | None = None


def _uploads_unchanged(label: str, arrays: tuple[np.ndarray, ...]) -> bool:
    last = _ga_uploads.get(label)
    if last is not None and all(np.array_equal(a, b) for a, b in zip(last, arrays, strict=True)):
        return True
    _ga_uploads.pop(label, None)
    return False


def _uploads_commit(label: str, arrays: tuple[np.ndarray, ...]) -> None:
    """The label's just-transferred arrays as its last known device copies: recorded only after the upload succeeded,
    so a failed transfer cannot leave a hit on data the device never got."""
    _ga_uploads[label] = tuple(np.asarray(a).copy() for a in arrays)


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
    # No claimant yet on any memo slot: the sentinel must top every claim's atomic_min, whatever n_genomes is.
    fields.ga_eval_cache_owner.fill(fields.MAX_GENOMES)
    all_curves = stat_curves()
    curves = all_curves.f32
    fields.ref_pp_field.from_numpy(curves["Perfect Points"])
    fields.ref_cm_field.from_numpy(curves["Combo Multiplier"])
    fields.ref_fm_field.from_numpy(curves["Fever Multiplier"])
    fields.exact_pp_best_gems_prefix.from_numpy(_pp_best_gems_prefix(curves["Perfect Points"]))
    note_combo = np.column_stack((all_curves.combo_ramp, all_curves.f64["Combo Multiplier"]))
    fields.note_combo.from_numpy(note_combo.astype(np.float32))
    fields.note_combo_bits.from_numpy(float64_words(note_combo))
    fields.fever_bits.from_numpy(float64_words(all_curves.f64["Fever Multiplier"]))
    ft, ff, _budget_left = ftff_combo_arrays(GEM_BUDGET)
    fields.ftff_combo_ft.from_numpy(ft.astype(np.int32))
    fields.ftff_combo_ff.from_numpy(ff.astype(np.int32))
    _ready = True


def _clear_device_state() -> None:
    global _ready, _timeline_key, _shortlist_arrays
    _ready = False
    _timeline_key = None
    _ga_uploads.clear()
    _shortlist_arrays = None


register_reset_hook(_clear_device_state)


def hard_reset(reason: str) -> None:
    """Taichi reset (frees its Vulkan resources; every field is gone): the next ensure_ready starts over."""
    reset_taichi(reason=reason)
    _clear_device_state()


def has_timeline(key: tuple) -> bool:
    """Whether `key`'s timeline frontier is already uploaded on the initialized device."""
    return _ready and key == _timeline_key


def upload_timeline(key: tuple, payload: TimelineFrontierGridPayload) -> None:
    """The song's timeline frontier, once per song. A new timeline also ends the evaluation memo, whose results hold for
    one song (its genomes' pre-gem stats are the memo's key, so it outlives the batches of a song)."""
    global _timeline_key
    if key == _timeline_key:
        return
    fields.ga_eval_cache_results.fill(0)

    def cell(array: np.ndarray, dtype) -> np.ndarray:
        return np.ascontiguousarray(np.asarray(array, dtype=dtype)[0])

    fields.song_head_len[0] = int(payload.grid_head_len[0, 0, 0])
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
    """The song's item table on the device, skipped when the pool did not change (same-color songs, repeat solves)."""
    n_items = len(item_stats)
    if n_items > fields.MAX_ITEMS:
        raise ValueError(f"Too many items: {n_items} > {fields.MAX_ITEMS}")
    arrays = (
        np.ascontiguousarray(item_stats[:, : fields.ITEM_STAT_DIM], dtype=np.int32),
        np.ascontiguousarray(slot_start, dtype=np.int32),
        np.ascontiguousarray(slot_count, dtype=np.int32),
        np.asarray(base_fixed_stats, dtype=np.int32),
    )
    if _uploads_unchanged("items", arrays):
        return
    kernels.upload_items_kernel(arrays[0], n_items, arrays[1], arrays[2])
    fields.base_fixed_stats.from_numpy(arrays[3])
    _uploads_commit("items", arrays)


def upload_init_topk(topk: np.ndarray) -> None:
    """The heuristic seed items on the device, skipped while the pool's topk is unchanged."""
    array = np.ascontiguousarray(topk, dtype=np.int32)
    if _uploads_unchanged("topk", (array,)):
        return
    fields.ga_init_heuristic_topk.from_numpy(array)
    _uploads_commit("topk", (array,))


def upload_shortlist(shortlist: FtffShortlist) -> tuple:
    """A song's FT/FF combo shortlist on the device: search_combos_kernel's arguments. An unchanged shortlist keeps its
    device arrays."""
    global _shortlist_arrays
    keys = tuple(
        np.ascontiguousarray(values, dtype=np.int32)
        for values in (shortlist.start, shortlist.count, shortlist.combos)
    )
    if _uploads_unchanged("shortlist", keys):
        return _shortlist_arrays
    arrays = []
    for values in keys:
        array = ti.ndarray(dtype=ti.i32, shape=(max(1, len(values)),))
        if len(values):
            array.from_numpy(values)
        arrays.append(array)
    _shortlist_arrays = tuple(arrays)
    _uploads_commit("shortlist", keys)
    return _shortlist_arrays
