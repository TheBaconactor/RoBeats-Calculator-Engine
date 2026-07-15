
"""GPU operations for exact loadout-candidate evaluation."""

from __future__ import annotations

import logging

import numpy as np

from .. import fields
from ..fields import MAX_EVALS_PER_DISPATCH
from ..skyline_chunking import compute_skyline_combo_chunk
from ..kernel_loader import get_kernels

from .common_operations import compute_array_sig
from .initialization import (
    ensure_ready,
    _ensure_ftff_combo_tables,
)

logger = logging.getLogger(__name__)

_SKYLINE_COMBO_CHUNK_MIN = 1024
_SKYLINE_COMBO_CHUNK_MAX = 4096

# Merge a tiny remainder into the prior dispatch when it is safe under the max-evals budget.
# This can reduce dispatch count when chunking would otherwise leave a very small "tail" kernel and the
# per-dispatch budget still has slack (e.g. when chunking is capped by `chunk_max` rather than the
# `max_evals` target).
_SKYLINE_COMBO_TAIL_MERGE_MAX = 256


# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


# ============================================================================
# UPLOAD CACHES (avoid redundant uploads over eGPU/Thunderbolt)
# ============================================================================
# Cache item_stats, slot_start, slot_count to avoid re-uploading ~2.6MB per song
# Cache base_fixed_stats (tiny but frequently called)

# Cache state for item_stats + slot boundaries
_ITEM_STATS_CACHE: dict = {"sig": None}

# Cache state for base_fixed_stats (simple tuple comparison)
_BASE_FIXED_STATS_CACHE: tuple | None = None
def reset_skyline_upload_caches() -> None:
    """Reset upload caches after ti.reset() or when switching songs."""
    global _ITEM_STATS_CACHE, _BASE_FIXED_STATS_CACHE, _SKYLINE_KERNELS_LIGHT_WARMED
    _ITEM_STATS_CACHE = {"sig": None}
    _BASE_FIXED_STATS_CACHE = None
    _SKYLINE_KERNELS_LIGHT_WARMED = False


# ============================================================================
# EXACT CANDIDATE OPERATIONS
# ============================================================================
# These functions upload candidate IDs, evaluate them exactly, and download scores/results.
# ============================================================================


def skyline_upload_loadout_indices(loadout_indices_np: np.ndarray, *, n_slots: int = 9) -> int:
    """Upload encoded loadouts to the resident ``fields.loadout_indices`` field."""
    ensure_ready()
    n_loadouts = int(loadout_indices_np.shape[0])
    if n_loadouts <= 0:
        return 0
    if n_loadouts > fields.MAX_LOADOUTS:
        raise ValueError(f"Too many loadouts: {n_loadouts} > {fields.MAX_LOADOUTS}")
    if int(n_slots) > fields.MAX_SLOTS:
        raise ValueError(f"Too many slots: {n_slots} > {fields.MAX_SLOTS}")

    src = np.ascontiguousarray(loadout_indices_np[:n_loadouts, : int(n_slots)], dtype=np.int32)
    kernels.skyline_copy_loadout_indices_from_ndarray_kernel(int(n_loadouts), int(n_slots), src)
    return n_loadouts

def skyline_upload_item_stats(
    item_stats_np: np.ndarray,
    slot_start_np: np.ndarray,
    slot_count_np: np.ndarray,
) -> int:
    """
    Upload item stats and slot pool boundaries for exact candidate evaluation.

    Caches uploads to avoid redundant transfers over Thunderbolt/eGPU.

    Args:
        item_stats_np: (n_items, 10) int32 - per-item stats
        slot_start_np: (9,) int32 - first item_id per slot
        slot_count_np: (9,) int32 - count of items per slot

    Returns:
        Number of items uploaded (or cached)
    """
    global _ITEM_STATS_CACHE

    ensure_ready()
    n_items = int(item_stats_np.shape[0])

    if n_items > fields.MAX_ITEMS:
        raise ValueError(f"Too many items: {n_items} > {fields.MAX_ITEMS}")

    # Content identity is authoritative: website custom catalogs may mutate or
    # replace arrays while reusing a Python object address.
    sig = compute_array_sig(
        np.asarray(item_stats_np[:n_items, : fields.ITEM_STAT_DIM], dtype=np.int32),
        np.asarray(slot_start_np, dtype=np.int32),
        np.asarray(slot_count_np, dtype=np.int32),
    )
    if _ITEM_STATS_CACHE.get("sig") == sig:
        return n_items  # Already uploaded

    # Upload only the active rows instead of a full MAX_ITEMS padded table.
    stats_src = np.ascontiguousarray(item_stats_np[:n_items, : fields.ITEM_STAT_DIM], dtype=np.int32)

    slot_start_arr = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    slot_count_arr = np.zeros(fields.MAX_SLOTS, dtype=np.int32)
    start_np = np.asarray(slot_start_np, dtype=np.int32).reshape(-1)
    count_np = np.asarray(slot_count_np, dtype=np.int32).reshape(-1)
    n_slot_vals = min(int(fields.MAX_SLOTS), int(start_np.shape[0]), int(count_np.shape[0]))
    if n_slot_vals > 0:
        slot_start_arr[:n_slot_vals] = start_np[:n_slot_vals]
        slot_count_arr[:n_slot_vals] = count_np[:n_slot_vals]

    kernels.skyline_upload_item_stats_and_slots_kernel(stats_src, int(n_items), slot_start_arr, slot_count_arr)

    _ITEM_STATS_CACHE["sig"] = sig
    return n_items


def skyline_upload_base_fixed_stats(base_stats_np: np.ndarray) -> None:
    """
    Upload fixed base stats (added to all loadouts during aggregation).

    Caches uploads to avoid redundant transfers.

    Args:
        base_stats_np: (10,) int32 - base stats [PP, CM, FM, FT, FF, Beat, Vibe, Rush, Flow, Chill]
    """
    global _BASE_FIXED_STATS_CACHE

    # Fast tuple comparison for small array
    key = tuple(int(x) for x in base_stats_np[: fields.ITEM_STAT_DIM])
    if _BASE_FIXED_STATS_CACHE == key:
        return  # Already uploaded

    ensure_ready()
    buf = np.zeros(fields.ITEM_STAT_DIM, dtype=np.int32)
    buf[: len(base_stats_np)] = np.asarray(base_stats_np, dtype=np.int32)
    fields.base_fixed_stats.from_numpy(buf)

    _BASE_FIXED_STATS_CACHE = key


def skyline_evaluate_loadouts(
    n_loadouts: int,
    n_slots: int = 9,
    *,
    total_budget: int,
    gem_scale_fever: int = 3,
    song_slot: int = 0,
    is_p_ft: int = 0,
    is_s_ft: int = 0,
    is_p_ff: int = 0,
    is_s_ff: int = 0,
    is_p_pp: int = 0,
    is_s_pp: int = 0,
    is_p_cm: int = 0,
    is_s_cm: int = 0,
    is_p_fm: int = 0,
    is_s_fm: int = 0,
    is_p_ov: int = 0,
    is_s_ov: int = 0,
    materialize_mode: str,
) -> None:
    """Aggregate and exactly evaluate the resident loadout batch."""
    ensure_ready()
    n_loadouts = int(n_loadouts)
    n_slots = int(n_slots)
    kernels.skyline_aggregate_loadouts_and_init_best_kernel(
        n_loadouts,
        n_slots,
        int(is_p_ft),
        int(is_s_ft),
        int(is_p_ff),
        int(is_s_ff),
        int(is_p_pp),
        int(is_s_pp),
        int(is_p_cm),
        int(is_s_cm),
        int(is_p_fm),
        int(is_s_fm),
        int(is_p_ov),
        int(is_s_ov),
    )

    total_budget_i = int(total_budget)
    gem_scale_fever_i = int(gem_scale_fever)
    song_slot_i = int(song_slot)
    n_combos = _ensure_ftff_combo_tables(total_budget_i)
    max_evals = max(int(MAX_EVALS_PER_DISPATCH), n_loadouts)
    combo_chunk = compute_skyline_combo_chunk(
        n_loadouts=n_loadouts,
        n_combos=n_combos,
        max_evals=max_evals,
        chunk_min=_SKYLINE_COMBO_CHUNK_MIN,
        chunk_max=_SKYLINE_COMBO_CHUNK_MAX,
    )
    if combo_chunk <= 0:
        combo_chunk = int(n_combos)

    offset = 0
    while offset < n_combos:
        chunk_len = int(min(combo_chunk, n_combos - offset))
        # If the remainder is tiny, fold it into this dispatch to avoid a "tail kernel" launch.
        if _SKYLINE_COMBO_TAIL_MERGE_MAX > 0:
            rem = int(n_combos - (offset + chunk_len))
            if 0 < rem <= int(_SKYLINE_COMBO_TAIL_MERGE_MAX):
                merged = int(chunk_len + rem)
                if n_loadouts * int(merged) <= int(max_evals):
                    chunk_len = merged
        kernels.skyline_find_best_combo_warmstart_kernel(
            n_loadouts,
            n_combos,
            int(offset),
            int(chunk_len),
            total_budget_i,
            gem_scale_fever_i,
            int(is_p_ft),
            int(is_s_ft),
            int(is_p_ff),
            int(is_s_ff),
            int(is_p_pp),
            int(is_s_pp),
            int(is_p_cm),
            int(is_s_cm),
            int(is_p_fm),
            int(is_s_fm),
            int(is_p_ov),
            int(is_s_ov),
            song_slot_i,
        )
        offset += int(chunk_len)

    _skyline_materialize_loadout_results(
        n_loadouts=n_loadouts,
        total_budget=total_budget_i,
        gem_scale_fever=gem_scale_fever_i,
        is_p_ft=int(is_p_ft),
        is_s_ft=int(is_s_ft),
        is_p_ff=int(is_p_ff),
        is_s_ff=int(is_s_ff),
        is_p_pp=int(is_p_pp),
        is_s_pp=int(is_s_pp),
        is_p_cm=int(is_p_cm),
        is_s_cm=int(is_s_cm),
        is_p_fm=int(is_p_fm),
        is_s_fm=int(is_s_fm),
        is_p_ov=int(is_p_ov),
        is_s_ov=int(is_s_ov),
        song_slot=song_slot_i,
        materialize_mode=materialize_mode,
    )


def _skyline_materialize_loadout_results(
    *,
    n_loadouts: int,
    total_budget: int,
    gem_scale_fever: int,
    is_p_ft: int,
    is_s_ft: int,
    is_p_ff: int,
    is_s_ff: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    song_slot: int,
    materialize_mode: str,
) -> None:
    mode = str(materialize_mode).strip().lower()
    if mode == "scores":
        kernels.skyline_write_scores_from_key_kernel(int(n_loadouts))
        return

    common_args = (
        int(n_loadouts),
        int(total_budget),
        int(gem_scale_fever),
        int(is_p_ft),
        int(is_s_ft),
        int(is_p_ff),
        int(is_s_ff),
        int(is_p_pp),
        int(is_s_pp),
        int(is_p_cm),
        int(is_s_cm),
        int(is_p_fm),
        int(is_s_fm),
        int(is_p_ov),
        int(is_s_ov),
        int(song_slot),
    )

    if mode == "results":
        kernels.skyline_write_best_results_from_key_kernel(*common_args)
        return

    raise ValueError(f"Unknown skyline materialize_mode: {materialize_mode!r}")


def skyline_download_scores(n_loadouts: int) -> np.ndarray:
    """Download exact candidate scores from GPU."""
    ensure_ready()
    n_loadouts = int(n_loadouts)
    out = fields.skyline_scores.to_numpy()
    return np.asarray(out[:n_loadouts], dtype=np.int32)


def skyline_download_results(n_loadouts: int) -> np.ndarray:
    """Download ``[score, ft, ff, pp, cm, fm, ov]`` rows from GPU."""
    ensure_ready()
    n_loadouts = int(n_loadouts)
    if n_loadouts <= 0:
        return np.empty((0, 7), dtype=np.int32)

    staging_field = None
    if n_loadouts <= 256:
        staging_field = fields.loadout_result_stats_download_staging_256
    elif n_loadouts <= 1024:
        staging_field = fields.loadout_result_stats_download_staging_1024
    if staging_field is not None:
        kernels.copy_loadout_result_stats_to_download_staging_kernel(staging_field, n_loadouts)
        return np.asarray(staging_field.to_numpy()[:n_loadouts], dtype=np.int32)
    return np.asarray(fields.loadout_result_stats.to_numpy()[:n_loadouts], dtype=np.int32)


_SKYLINE_KERNELS_LIGHT_WARMED = False


def _warmup_ref_arrays() -> dict[str, np.ndarray]:
    x = np.linspace(0.0, 1.0, int(fields.GRID_SIZE), dtype=np.float32)
    return {
        "Perfect Points": (1000.0 + (500.0 * x)).astype(np.float32, copy=False),
        "Combo Multiplier": (1.0 + x).astype(np.float32, copy=False),
        "Fever Multiplier": (1.0 + (0.5 * x)).astype(np.float32, copy=False),
        "Fever Time": (5.0 + (30.0 * x)).astype(np.float32, copy=False),
        "Fever Fill Rate": (1.0 + (4.0 * x)).astype(np.float32, copy=False),
    }


def _warmup_calc_song() -> dict:
    timestamps = np.linspace(0.0, 18.0, 48, dtype=np.float32)
    note_types = np.zeros((timestamps.shape[0],), dtype=np.int32)
    lanes = np.arange(timestamps.shape[0], dtype=np.int32) % 4
    metadata = {
        "Song Name": "__SKYLINE_live_request_warmup__",
        "Difficulty": "Warmup",
        "Long Notes": 0,
        "Last Note Time": float(timestamps[-1]) if timestamps.size else 0.0,
    }
    return {
        "metadata": metadata,
        "song_data": {
            "timestamps": timestamps,
            "chart_timestamps": timestamps,
            "note_types": note_types,
            "lanes": lanes,
            "fg_perfect_candidate_timestamps": timestamps,
            "fg_perfect_floor_timestamps": timestamps,
        },
    }


def warmup_skyline_kernels_light() -> None:
    """Compile the exact candidate-evaluation path used by production."""
    global _SKYLINE_KERNELS_LIGHT_WARMED
    if _SKYLINE_KERNELS_LIGHT_WARMED:
        return

    ensure_ready()

    import taichi as ti

    from .timeline import precompute_timeline_gpu_for_warmup

    n_slots = 9
    n_loadouts = min(64, int(fields.MAX_LOADOUTS))
    total_budget = 1
    song_slot = 0

    ref_arrays = _warmup_ref_arrays()
    ensure_ready(ref_arrays)
    precompute_timeline_gpu_for_warmup(
        _warmup_calc_song(),
        ref_arrays,
        song_slot=song_slot,
    )

    item_stats_np = np.zeros((1, fields.ITEM_STAT_DIM), dtype=np.int32)
    slot_start_np = np.zeros((fields.MAX_SLOTS,), dtype=np.int32)
    slot_count_np = np.ones((fields.MAX_SLOTS,), dtype=np.int32)
    skyline_upload_item_stats(item_stats_np, slot_start_np, slot_count_np)
    skyline_upload_base_fixed_stats(
        np.zeros((fields.ITEM_STAT_DIM,), dtype=np.int32)
    )
    skyline_upload_loadout_indices(
        np.zeros((n_loadouts, n_slots), dtype=np.int32),
        n_slots=n_slots,
    )

    skyline_evaluate_loadouts(
        n_loadouts,
        n_slots=n_slots,
        total_budget=total_budget,
        song_slot=song_slot,
        materialize_mode="scores",
    )
    skyline_evaluate_loadouts(
        n_loadouts,
        n_slots=n_slots,
        total_budget=total_budget,
        song_slot=song_slot,
        materialize_mode="results",
    )
    ti.sync()
    _SKYLINE_KERNELS_LIGHT_WARMED = True
