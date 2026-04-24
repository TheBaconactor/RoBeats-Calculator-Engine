"""
API Timeline - GPU timeline precomputation and grid upload.

This module provides GPU-accelerated timeline precomputation:
- precompute_timeline_gpu: Compute all 161×161 fever timelines on GPU
- _upload_timeline_grid: Upload timeline grid to GPU fields with caching
"""

import time
import os
from collections import OrderedDict
import numpy as np
import taichi as ti

from gear_optimizer.core.env_config import env_flag
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.utils import timing_envelope_timing_context
from gear_optimizer.solver.gpu_profiler import get_gpu_profiler
from gear_optimizer.solver.timeline_exact_dp import (
    build_score_bonus_prefix,
    count_activation_upper_bound,
    solve_timeline_signature_exact_scoremax_from_grouped_windows,
)
from ..fields import (
    GRID_SIZE,
    MAX_HEAD_NOTES,
    MAX_SONG_SLOTS,
    get_last_uploaded_grid_id,
    set_last_uploaded_grid_id,
)
from .. import fields
from ..kernel_loader import get_kernels

from .initialization import ensure_ready, _maybe_sync, _SYNC_FOR_TIMING, _FORCE_SYNC

_profiler = get_gpu_profiler()

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


@ti.kernel
def _upload_song_timestamps_kernel(n: ti.i32, timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1)):
    """
    Upload song timestamps without padding to MAX_SONG_NOTES.

    This reduces CPU->GPU transfer volume vs `field.from_numpy(padded)` while
    preserving behavior (kernels only read indices < total_notes).
    """
    for i in range(n):
        fields.song_timestamps[i] = timestamps[i]


@ti.kernel
def _upload_song_note_group_idx_kernel(n: ti.i32, note_group_idx: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    """Upload note_idx -> group_idx mapping without padding."""
    for i in range(n):
        fields.song_note_group_idx[i] = note_group_idx[i]


@ti.kernel
def _upload_song_groups_kernel(
    n_groups: ti.i32,
    group_starts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_base_t_ms: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_low_ms: ti.types.ndarray(dtype=ti.i32, ndim=1),
    group_high_ms: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """Upload chord-group arrays used by the analytical timing-envelope ceiling kernel."""
    for g in range(n_groups):
        fields.song_group_starts[g] = group_starts[g]
        fields.song_group_base_t_ms[g] = group_base_t_ms[g]
        fields.song_group_low_ms[g] = group_low_ms[g]
        fields.song_group_high_ms[g] = group_high_ms[g]


@ti.kernel
def _upload_exact_timeline_overrides_kernel(
    n_rows: ti.i32,
    song_slot: ti.i32,
    ft_idx_arr: ti.types.ndarray(dtype=ti.i16, ndim=1),
    ff_idx_arr: ti.types.ndarray(dtype=ti.i16, ndim=1),
    head_len_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    body_fever_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    body_normal_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    gap_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    fever_activations_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    m0_arr: ti.types.ndarray(dtype=ti.u32, ndim=1),
    m1_arr: ti.types.ndarray(dtype=ti.u32, ndim=1),
    m2_arr: ti.types.ndarray(dtype=ti.u32, ndim=1),
    m3_arr: ti.types.ndarray(dtype=ti.u32, ndim=1),
):
    for row in range(n_rows):
        ft_idx = ti.cast(ft_idx_arr[row], ti.i32)
        ff_idx = ti.cast(ff_idx_arr[row], ti.i32)
        fields.grid_count_body_fever[song_slot, ft_idx, ff_idx] = ti.cast(body_fever_arr[row], ti.i16)
        fields.grid_count_body_normal[song_slot, ft_idx, ff_idx] = ti.cast(body_normal_arr[row], ti.i16)
        fields.grid_head_len[song_slot, ft_idx, ff_idx] = ti.cast(head_len_arr[row], ti.i8)
        fields.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0] = m0_arr[row]
        fields.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1] = m1_arr[row]
        fields.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2] = m2_arr[row]
        fields.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3] = m3_arr[row]
        fields.grid_gap[song_slot, ft_idx, ff_idx] = ti.cast(gap_arr[row], ti.i16)
        fields.grid_fever_activations[song_slot, ft_idx, ff_idx] = ti.cast(fever_activations_arr[row], ti.i8)


# ============================================================================
# GPU TIMELINE PRECOMPUTATION (eliminates Numba typeof overhead)
# ============================================================================

_gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS  # Track last song per slot
_CEILING_GROUP_PAYLOAD_CACHE_MAX = max(1, int(os.environ.get("CEILING_GROUP_PAYLOAD_CACHE_MAX", "32") or "32"))
_ceiling_group_payload_cache: "OrderedDict[tuple, dict]" = OrderedDict()


def _resolve_ceiling_exact_max_windows(calc_song: dict) -> int:
    meta = calc_song.get("metadata", {}) or {}
    raw = meta.get("TimelineAnalysisMaxWindows", "")
    if raw is None or str(raw).strip() == "":
        raw = os.environ.get("TIMELINE_ANALYSIS_MAX_WINDOWS", "")
    if raw is None or str(raw).strip() == "":
        return 0
    try:
        return max(0, min(int(raw), 64))
    except Exception:
        return 0


def _timeline_exact_overrides_enabled() -> bool:
    """
    Gate CPU-built exact timeline overrides.

    The broad timing-envelope ceiling kernel is GPU-resident and remains the
    production default. Exact overrides are useful for proofs/regressions, but
    building them synchronously in the GPU owner can starve the queue.
    """

    return bool(env_flag("GPU_TIMELINE_EXACT_OVERRIDES", "0"))


def _song_timing_cache_key(calc_song: dict) -> tuple:
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    use_ceiling = bool(env_flag("GPU_TIMELINE_CEILING_ENVELOPE", "1"))
    max_windows = (
        _resolve_ceiling_exact_max_windows(calc_song) if (use_ceiling and _timeline_exact_overrides_enabled()) else 0
    )
    if use_ceiling:
        cached = calc_song.get("_gpu_timing_cache_key_ceiling", None)
        if isinstance(cached, tuple) and len(cached) == 9:
            return cached
    if use_ceiling:
        chart_ts = song_data.get("chart_timestamps", None)
        timestamps = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    else:
        timestamps = song_data.get("timestamps", ())
    ts_sig = song_data.get("_chart_timestamps_sig", None) if use_ceiling else song_data.get("_timestamps_sig", None)
    if not isinstance(ts_sig, (bytes, bytearray, memoryview)) or len(ts_sig) != 16:
        ts_sig = array_sig16(timestamps)
    nt_sig = song_data.get("_note_types_sig", None)
    if not isinstance(nt_sig, (bytes, bytearray, memoryview)) or len(nt_sig) != 16:
        nt_sig = array_sig16(song_data.get("note_types"))
    key = (
        str(meta.get("Song Name", "")),
        str(meta.get("Difficulty", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        int(1 if use_ceiling else 0),
        bytes(ts_sig),
        bytes(nt_sig),
        int(max_windows),
    ) + (() if use_ceiling else timing_envelope_timing_context(calc_song))
    if use_ceiling and isinstance(key, tuple) and len(key) == 9:
        # Cache on the calc_song dict to avoid repeated full-array hashing when the
        # same song is revisited and precompute_timeline_gpu() hits the slot cache.
        calc_song["_gpu_timing_cache_key_ceiling"] = key
    return key


def _get_or_build_ceiling_group_payload(
    base_song_key: tuple,
    *,
    timestamps: np.ndarray,
    note_types: object,
) -> dict:
    """
    Prepare and cache chord-group payloads used by the analytical timing-envelope ceiling kernel.

    This CPU preprocessing is a pure function of chart timestamps + note types (and the
    fixed Perfect window constants). Caching avoids recomputing grouping + dense note->group
    maps when the same song is revisited across slots or after timeline cache resets.
    """
    global _ceiling_group_payload_cache

    n = int(getattr(timestamps, "shape", (0,))[0] or 0)
    cached = _ceiling_group_payload_cache.get(base_song_key)
    if isinstance(cached, dict):
        try:
            if int(cached.get("n", -1) or -1) == int(n) and int(cached.get("group_count", 0) or 0) > 0:
                _ceiling_group_payload_cache.move_to_end(base_song_key)
                return cached
        except Exception:
            pass

    from gear_optimizer.solver.timing_envelope import prepare_perfect_timing_envelope

    prepared = prepare_perfect_timing_envelope(
        timestamps,
        note_types,
        perfect_lower_ms=-20,
        perfect_upper_ms=40,
        held_tail_type=3,
        held_tail_time_multiplier=2,
        quantize_ms=True,
    )
    group_starts = np.asarray(prepared.get("group_starts", ()), dtype=np.int32)
    group_ends = np.asarray(prepared.get("group_ends", ()), dtype=np.int32)
    group_base_t_ms = np.asarray(prepared.get("group_base_t", ()), dtype=np.int32)
    group_low_ms = np.asarray(prepared.get("group_low", ()), dtype=np.int32)
    group_high_ms = np.asarray(prepared.get("group_high", ()), dtype=np.int32)
    group_count = int(group_starts.shape[0])
    if int(prepared.get("n", n) or 0) != int(n):
        raise ValueError("prepare_perfect_timing_envelope produced mismatched note count")
    if n > 0 and group_count <= 0:
        raise ValueError("prepare_perfect_timing_envelope produced no chord groups")

    if n <= 0:
        note_group_idx = np.zeros((0,), dtype=np.int32)
    else:
        # Fast-path: grouping produces a contiguous partition of note indices, so
        # note->group can be constructed via repeat() instead of a Python loop.
        is_partition = False
        try:
            if int(group_starts[0]) == 0 and int(group_ends[-1]) == int(n):
                if group_count == 1 or bool(np.all(group_starts[1:] == group_ends[:-1])):
                    is_partition = True
        except Exception:
            is_partition = False

        if is_partition:
            lengths = (group_ends - group_starts).astype(np.int32, copy=False)
            note_group_idx = np.repeat(np.arange(int(group_count), dtype=np.int32), lengths)
        else:
            note_group_idx = np.full(int(n), -1, dtype=np.int32)
            for g in range(group_count):
                s = int(group_starts[g])
                e = int(group_ends[g])
                if e > s:
                    note_group_idx[s:e] = int(g)
            if int(np.any(note_group_idx < 0)):
                raise ValueError("prepare_perfect_timing_envelope produced uncovered note indices")

    payload = {
        "n": int(n),
        "group_count": int(group_count),
        "note_group_idx": np.ascontiguousarray(note_group_idx),
        "group_starts": np.ascontiguousarray(group_starts),
        "group_base_t_ms": np.ascontiguousarray(group_base_t_ms),
        "group_low_ms": np.ascontiguousarray(group_low_ms),
        "group_high_ms": np.ascontiguousarray(group_high_ms),
    }

    _ceiling_group_payload_cache[base_song_key] = payload
    _ceiling_group_payload_cache.move_to_end(base_song_key)
    while len(_ceiling_group_payload_cache) > int(_CEILING_GROUP_PAYLOAD_CACHE_MAX):
        _ceiling_group_payload_cache.popitem(last=False)

    return payload


def _build_ceiling_cell_rep_maps(
    *,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    ref_arrays: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    """
    Build representative index maps for exact ceiling-grid deduplication.

    For a fixed song, ceiling-kernel outputs for a (ft_idx, ff_idx) cell depend only on:
      - `fill_count = ceil(non_fever_cas * ff_factor)` (clamped to >= 1)
      - `d_ms = ceil(fever_time_cas * ft_factor * 1000)` (clamped to >= 0)

    This helper groups cells by the integer pair (fill_count, d_ms) and assigns a deterministic
    representative cell per pair:
      rep cell = (first ft_idx yielding that d_ms, first ff_idx yielding that fill_count)

    Returns:
      - rep_ft_by_ft[ft] i16: representative ft_idx for each ft_idx (same d_ms)
      - rep_ff_by_ff[ff] i16: representative ff_idx for each ff_idx (same fill_count)
      - rep_ft_values[i] i16: unique representative ft indices (one per unique d_ms)
      - rep_ff_values[i] i16: unique representative ff indices (one per unique fill_count)
      - unique_pairs: number of unique (fill_count, d_ms) pairs in the grid

    NOTE: math uses float32 semantics to match Taichi kernel behavior.
    """
    ff = np.asarray(ref_arrays.get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    ft = np.asarray(ref_arrays.get("Fever Time", ()), dtype=np.float32).reshape(-1)
    if int(ff.shape[0]) != int(GRID_SIZE):
        raise ValueError(f"ref_arrays['Fever Fill Rate'] must be shape ({GRID_SIZE},), got {ff.shape}")
    if int(ft.shape[0]) != int(GRID_SIZE):
        raise ValueError(f"ref_arrays['Fever Time'] must be shape ({GRID_SIZE},), got {ft.shape}")

    non_fever_cas = np.float32(max(0, int(total_notes) - int(long_notes))) * np.float32(0.333)
    fever_time_cas = np.float32(float(last_note_time)) * np.float32(0.15) + np.float32(0.15)

    fill_counts = np.ceil(non_fever_cas * ff).astype(np.int32)
    fill_counts = np.maximum(fill_counts, np.int32(1))

    d_ms = np.ceil(fever_time_cas * ft * np.float32(1000.0)).astype(np.int32)
    d_ms = np.maximum(d_ms, np.int32(0))

    unique_fc, fc_first = np.unique(fill_counts, return_index=True)
    unique_d, d_first = np.unique(d_ms, return_index=True)
    unique_pairs = int(unique_fc.shape[0]) * int(unique_d.shape[0])

    rep_ff_for_fc = dict(zip((int(x) for x in unique_fc.tolist()), (int(x) for x in fc_first.tolist())))
    rep_ft_for_d = dict(zip((int(x) for x in unique_d.tolist()), (int(x) for x in d_first.tolist())))

    rep_ff_by_ff = np.asarray([rep_ff_for_fc[int(x)] for x in fill_counts.tolist()], dtype=np.int16)
    rep_ft_by_ft = np.asarray([rep_ft_for_d[int(x)] for x in d_ms.tolist()], dtype=np.int16)

    rep_ft_values = np.asarray(d_first, dtype=np.int16)
    rep_ff_values = np.asarray(fc_first, dtype=np.int16)
    rep_ft_values.sort()
    rep_ff_values.sort()

    return rep_ft_by_ft, rep_ff_by_ff, rep_ft_values, rep_ff_values, int(unique_pairs)


def precompute_timeline_gpu(calc_song: dict, ref_arrays: dict, song_slot: int = 0) -> None:
    """
    Precompute all 161×161 fever timeline entries on GPU.

    This replaces the CPU Numba path (calculate_fever_timeline_indices) which
    had 28.7s typeof() overhead from 20M calls.

    GPU computes all 26,521 timelines in parallel in ~100ms.

    Args:
        calc_song: Song calculation context with timestamps/metadata
        ref_arrays: Reference lookup arrays (must include Fever Time/Fill Rate)
        song_slot: Grid slot to write to (0-7, default 0 for single-song mode)

    After calling this, the grid fields for song_slot are populated:
    - grid_count_body_fever[song_slot, ft, ff]
    - grid_count_body_normal[song_slot, ft, ff]
    - grid_head_len[song_slot, ft, ff]
    - grid_fever_masks[song_slot, ft, ff, :]
    - grid_fever_masks_bits[song_slot, ft, ff, :]
    - grid_gap[song_slot, ft, ff] (computed by CPU upload path)
    - grid_fever_activations[song_slot, ft, ff] (computed by CPU upload path)
    """
    global _gpu_timeline_song_id_by_slot

    song_slot = int(song_slot)
    if song_slot < 0 or song_slot >= MAX_SONG_SLOTS:
        raise ValueError(f"song_slot out of range: {song_slot}")

    # Ensure GPU is ready with refs and grid fields (even on cache hit).
    # Also reuse the ref signature so callers don't hash refs twice.
    ref_sig = ensure_ready(ref_arrays) if isinstance(ref_arrays, dict) else ensure_ready(None)

    base_song_key = _song_timing_cache_key(calc_song)
    max_exact_windows = _resolve_ceiling_exact_max_windows(calc_song)

    # Check if we already computed for this song+ref set.
    song_key = base_song_key + (bytes(ref_sig),)
    if _gpu_timeline_song_id_by_slot[song_slot] == song_key:
        return  # Already computed

    song_data = calc_song.get("song_data", {}) or {}
    use_ceiling = bool(env_flag("GPU_TIMELINE_CEILING_ENVELOPE", "1"))

    # Upload song timestamps (float seconds). Analytical ceiling uses chart timestamps.
    if use_ceiling:
        chart_ts = song_data.get("chart_timestamps", None)
        src = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
        timestamps = np.asarray(src, dtype=np.float32)
    else:
        timestamps = np.asarray(song_data.get("timestamps", ()), dtype=np.float32)
    total_notes = len(timestamps)

    # Pad to MAX_SONG_NOTES if needed
    if total_notes > fields.MAX_SONG_NOTES:
        raise ValueError(f"Song has {total_notes} notes, max is {fields.MAX_SONG_NOTES}")

    # Upload only the used prefix (avoid padding to MAX_SONG_NOTES).
    #
    # Analytical ceiling mode does not read `fields.song_timestamps`, so skip the upload
    # to reduce CPU->GPU traffic on that path.
    if not use_ceiling:
        if _profiler.enabled:
            _t_ts = time.perf_counter()
            _upload_song_timestamps_kernel(int(total_notes), timestamps)
            _profiler.record_upload(time.perf_counter() - _t_ts, bytes_count=int(timestamps.nbytes))
        else:
            _upload_song_timestamps_kernel(int(total_notes), timestamps)

    group_count = 0
    note_group_idx = None
    group_starts = None
    group_base_t_ms = None
    group_low_ms = None
    group_high_ms = None
    if use_ceiling:
        payload = _get_or_build_ceiling_group_payload(
            base_song_key[:-1],
            timestamps=timestamps,
            note_types=song_data.get("note_types", None),
        )
        payload_n = int(payload.get("n", 0) or 0)
        if int(payload_n) != int(total_notes):
            raise ValueError("prepare_perfect_timing_envelope produced mismatched note count")

        note_group_idx = np.asarray(payload.get("note_group_idx", ()), dtype=np.int32)
        group_starts = np.asarray(payload.get("group_starts", ()), dtype=np.int32)
        group_base_t_ms = np.asarray(payload.get("group_base_t_ms", ()), dtype=np.int32)
        group_low_ms = np.asarray(payload.get("group_low_ms", ()), dtype=np.int32)
        group_high_ms = np.asarray(payload.get("group_high_ms", ()), dtype=np.int32)
        group_count = int(payload.get("group_count", 0) or 0)
        if total_notes > 0 and group_count <= 0:
            raise ValueError("prepare_perfect_timing_envelope produced no chord groups")

        if _profiler.enabled:
            _t_groups = time.perf_counter()
            _upload_song_note_group_idx_kernel(int(total_notes), note_group_idx)
            _upload_song_groups_kernel(
                int(group_count),
                group_starts,
                group_base_t_ms,
                group_low_ms,
                group_high_ms,
            )
            upload_bytes = int(
                note_group_idx.nbytes
                + group_starts.nbytes
                + group_base_t_ms.nbytes
                + group_low_ms.nbytes
                + group_high_ms.nbytes
            )
            _profiler.record_upload(time.perf_counter() - _t_groups, bytes_count=upload_bytes)
        else:
            _upload_song_note_group_idx_kernel(int(total_notes), note_group_idx)
            _upload_song_groups_kernel(
                int(group_count),
                group_starts,
                group_base_t_ms,
                group_low_ms,
                group_high_ms,
            )

    # Extract song metadata
    long_notes = int(calc_song["metadata"].get("Long Notes", 0))
    last_note_time = float(calc_song["metadata"].get("Last Note Time", 0))

    # Sync before timing
    _maybe_sync(for_timing=True)
    _t0 = time.perf_counter()

    if not use_ceiling:
        # Precompute fever end indices for O(1) timeline lookups
        kernels.precompute_fever_end_idx_kernel(
            int(total_notes),
            float(last_note_time),
        )

    # Launch GPU kernel to compute all 161×161 timelines for this song slot.
    #
    # Canonical representation is bitpacked (`grid_fever_masks_bits`). Unpacked
    # masks are only needed for legacy debug/tests.
    write_unpacked_masks = (
        1 if (env_flag("GPU_TIMELINE_WRITE_UNPACKED_MASKS", "0") or fields.grid_fever_masks is not None) else 0
    )
    if write_unpacked_masks != 0:
        fields.ensure_grid_unpacked_masks_allocated()
    if use_ceiling:
        exact_enabled = bool(int(max_exact_windows) > 0 and _timeline_exact_overrides_enabled())
        # Default OFF: On GPU/Vulkan, "dedup then scatter" often reduces parallelism enough
        # to lose against the fully-parallel baseline kernel, even when many cells share
        # identical (fill_count, d_ms) pairs. Keep the option for experiments/regressions.
        use_dedup = bool(env_flag("GPU_TIMELINE_CEILING_DEDUP", "0"))
        rep_ft_by_ft = None
        rep_ff_by_ff = None
        rep_ft_values = None
        rep_ff_values = None
        unique_pairs = GRID_SIZE * GRID_SIZE
        if use_dedup or exact_enabled:
            try:
                rep_ft_by_ft, rep_ff_by_ff, rep_ft_values, rep_ff_values, unique_pairs = _build_ceiling_cell_rep_maps(
                    total_notes=int(total_notes),
                    long_notes=int(long_notes),
                    last_note_time=float(last_note_time),
                    ref_arrays=ref_arrays,
                )
            except Exception:
                rep_ft_by_ft = None
                rep_ff_by_ff = None
                rep_ft_values = None
                rep_ff_values = None
                unique_pairs = GRID_SIZE * GRID_SIZE

        if (
            use_dedup
            and rep_ft_by_ft is not None
            and rep_ff_by_ff is not None
            and rep_ft_values is not None
            and rep_ff_values is not None
            and unique_pairs < (GRID_SIZE * GRID_SIZE)
        ):
            kernels.compute_timeline_grid_ceiling_envelope_reps_kernel(
                total_notes,
                long_notes,
                last_note_time,
                int(group_count),
                song_slot,  # Grid slot for batch coalescing
                int(write_unpacked_masks),
                rep_ft_values,
                rep_ff_values,
                int(rep_ft_values.shape[0]),
                int(rep_ff_values.shape[0]),
            )
            kernels.scatter_timeline_grid_ceiling_envelope_from_reps_kernel(
                int(song_slot),
                rep_ft_by_ft,
                rep_ff_by_ff,
            )
        else:
            kernels.compute_timeline_grid_ceiling_envelope_kernel(
                total_notes,
                long_notes,
                last_note_time,
                int(group_count),
                song_slot,  # Grid slot for batch coalescing
                int(write_unpacked_masks),
            )

        if (
            exact_enabled
            and rep_ft_by_ft is not None
            and rep_ff_by_ff is not None
            and rep_ft_values is not None
            and rep_ff_values is not None
        ):
            note_group_idx_arr = np.asarray(note_group_idx, dtype=np.int32)
            group_starts_arr = np.asarray(group_starts, dtype=np.int32)
            group_base_arr = np.asarray(group_base_t_ms, dtype=np.int32)
            group_low_arr = np.asarray(group_low_ms, dtype=np.int32)
            group_high_arr = np.asarray(group_high_ms, dtype=np.int32)
            pp_vals = np.asarray(ref_arrays.get("Perfect Points", ()), dtype=np.float32).reshape(-1)
            cm_vals = np.asarray(ref_arrays.get("Combo Multiplier", ()), dtype=np.float32).reshape(-1)
            fm_vals = np.asarray(ref_arrays.get("Fever Multiplier", ()), dtype=np.float32).reshape(-1)
            proxy_pp = max(10000.0, float(np.nanmax(pp_vals)) if int(pp_vals.shape[0]) else 10000.0)
            proxy_cm = float(np.nanmax(cm_vals)) if int(cm_vals.shape[0]) else 2.6
            proxy_fm = float(np.nanmax(fm_vals)) if int(fm_vals.shape[0]) else 5.25
            if not np.isfinite(proxy_pp) or proxy_pp <= 0.0:
                proxy_pp = 10000.0
            if not np.isfinite(proxy_cm) or proxy_cm <= 0.0:
                proxy_cm = 2.6
            if not np.isfinite(proxy_fm) or proxy_fm <= 0.0:
                proxy_fm = 5.25
            bonus_prefix = build_score_bonus_prefix(
                total_notes=int(total_notes),
                base_value=float(proxy_pp),
                combo_mul=float(proxy_cm),
                fever_mul=float(proxy_fm),
            )
            ff_vals = np.asarray(ref_arrays.get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
            ft_vals = np.asarray(ref_arrays.get("Fever Time", ()), dtype=np.float32).reshape(-1)

            override_ft: list[int] = []
            override_ff: list[int] = []
            override_hl: list[int] = []
            override_bf: list[int] = []
            override_bn: list[int] = []
            override_gap: list[int] = []
            override_fa: list[int] = []
            override_m0: list[int] = []
            override_m1: list[int] = []
            override_m2: list[int] = []
            override_m3: list[int] = []

            for ft_idx_i16 in np.asarray(rep_ft_values, dtype=np.int16).tolist():
                ft_idx = int(ft_idx_i16)
                ft_factor = float(ft_vals[ft_idx])
                fever_time_cas = float(last_note_time) * 0.15 + 0.15
                d_ms = int(np.ceil(np.float32(fever_time_cas * ft_factor * 1000.0)))
                if d_ms < 0:
                    d_ms = 0

                for ff_idx_i16 in np.asarray(rep_ff_values, dtype=np.int16).tolist():
                    ff_idx = int(ff_idx_i16)
                    ff_factor = float(ff_vals[ff_idx])
                    non_fever_cas = float(max(0, int(total_notes) - int(long_notes))) * 0.333
                    fill_count = int(np.ceil(np.float32(non_fever_cas * ff_factor)))
                    fill_count = max(1, int(fill_count))

                    if count_activation_upper_bound(total_notes=int(total_notes), fill_count=int(fill_count)) > int(
                        max_exact_windows
                    ):
                        continue

                    exact = solve_timeline_signature_exact_scoremax_from_grouped_windows(
                        int(total_notes),
                        group_starts=group_starts_arr,
                        group_base_t_ms=group_base_arr,
                        group_low_ms=group_low_arr,
                        group_high_ms=group_high_arr,
                        note_group_idx=note_group_idx_arr,
                        fill_count=int(fill_count),
                        d_ms=int(d_ms),
                        bonus_prefix=bonus_prefix,
                    )
                    override_ft.append(int(ft_idx))
                    override_ff.append(int(ff_idx))
                    override_hl.append(int(exact.head_len))
                    override_bf.append(int(exact.body_fever))
                    override_bn.append(int(exact.body_normal))
                    override_gap.append(int(exact.gap))
                    override_fa.append(int(exact.fever_activations))
                    override_m0.append(int(exact.head_bits[0]))
                    override_m1.append(int(exact.head_bits[1]))
                    override_m2.append(int(exact.head_bits[2]))
                    override_m3.append(int(exact.head_bits[3]))

            if override_ft:
                _upload_exact_timeline_overrides_kernel(
                    int(len(override_ft)),
                    int(song_slot),
                    np.asarray(override_ft, dtype=np.int16),
                    np.asarray(override_ff, dtype=np.int16),
                    np.asarray(override_hl, dtype=np.int32),
                    np.asarray(override_bf, dtype=np.int32),
                    np.asarray(override_bn, dtype=np.int32),
                    np.asarray(override_gap, dtype=np.int32),
                    np.asarray(override_fa, dtype=np.int32),
                    np.asarray(override_m0, dtype=np.uint32),
                    np.asarray(override_m1, dtype=np.uint32),
                    np.asarray(override_m2, dtype=np.uint32),
                    np.asarray(override_m3, dtype=np.uint32),
                )
                if int(unique_pairs) < (GRID_SIZE * GRID_SIZE):
                    kernels.scatter_timeline_grid_ceiling_envelope_from_reps_kernel(
                        int(song_slot),
                        rep_ft_by_ft,
                        rep_ff_by_ff,
                    )
                kernels.compute_timeline_grid_signatures_kernel(int(song_slot))
    else:
        kernels.compute_timeline_grid_kernel(
            total_notes,
            long_notes,
            last_note_time,
            song_slot,  # Grid slot for batch coalescing
            int(write_unpacked_masks),
        )
    if write_unpacked_masks != 0:
        # Build i8 masks from the bitpacked representation on-GPU (debug/tests only).
        kernels.unpack_timeline_grid_masks_kernel(int(song_slot))

    _maybe_sync(for_timing=True)
    _t1 = time.perf_counter()

    _gpu_timeline_song_id_by_slot[song_slot] = song_key

    if _SYNC_FOR_TIMING or _FORCE_SYNC:
        print(f"[GPU Timeline] Computed 161×161 grid in {(_t1 - _t0) * 1000:.1f}ms")


# ============================================================================
# GRID UPLOAD HELPERS
# ============================================================================

_grid_uploaded = False


@ti.kernel
def _upload_grid_slot0_counts_kernel(
    n: ti.i32,
    cbf: ti.types.ndarray(dtype=ti.i32, ndim=2),
    cbn: ti.types.ndarray(dtype=ti.i32, ndim=2),
    hl: ti.types.ndarray(dtype=ti.i32, ndim=2),
    gap: ti.types.ndarray(dtype=ti.i32, ndim=2),
    fevact: ti.types.ndarray(dtype=ti.i32, ndim=2),
) -> None:
    for i, j in ti.ndrange(n, n):
        fields.grid_count_body_fever[0, i, j] = cbf[i, j]
        fields.grid_count_body_normal[0, i, j] = cbn[i, j]
        fields.grid_head_len[0, i, j] = hl[i, j]
        fields.grid_gap[0, i, j] = gap[i, j]
        fields.grid_fever_activations[0, i, j] = fevact[i, j]


@ti.kernel
def _upload_grid_slot0_masks_kernel(
    n: ti.i32,
    masks: ti.types.ndarray(dtype=ti.i32, ndim=3),
    masks_bits: ti.types.ndarray(dtype=ti.u32, ndim=3),
) -> None:
    for i, j, k in ti.ndrange(n, n, MAX_HEAD_NOTES):
        fields.grid_fever_masks[0, i, j, k] = masks[i, j, k]
    for i, j, k in ti.ndrange(n, n, 4):
        fields.grid_fever_masks_bits[0, i, j, k] = masks_bits[i, j, k]


@ti.kernel
def _upload_grid_slot0_mask_bits_kernel(
    n: ti.i32,
    masks_bits: ti.types.ndarray(dtype=ti.u32, ndim=3),
) -> None:
    for i, j, k in ti.ndrange(n, n, 4):
        fields.grid_fever_masks_bits[0, i, j, k] = masks_bits[i, j, k]


def _upload_timeline_grid(timeline_grid):
    """Upload timeline grid to GPU fields (with caching)."""
    global _grid_uploaded

    # Skip if same grid already uploaded (major optimization!)
    # NOTE: In parallel mode the timeline grid is pickled across processes; `id()`
    # changes on every request, which defeats caching and can force repeated
    # 161x161 precompute + upload. Prefer a stable key when available.
    grid_id = getattr(timeline_grid, "cache_key", None) or id(timeline_grid)
    cached_id = get_last_uploaded_grid_id()
    if _grid_uploaded and cached_id == grid_id:
        return

    # Ensure all timelines are computed
    timeline_grid.precompute_all()

    # Get grid data
    grid_size = timeline_grid.GRID_SIZE

    # OPTIMIZED: Extract all grid data using precomputed cache
    # This avoids 2.6M Python loop iterations!
    _t_extract = time.perf_counter()

    write_unpacked_masks = env_flag("GPU_TIMELINE_WRITE_UNPACKED_MASKS", "0")
    if write_unpacked_masks:
        fields.ensure_grid_unpacked_masks_allocated()

    # Avoid allocating giant (MAX_SONG_SLOTS, ...) CPU staging arrays when users
    # increase `GPU_SONG_SLOTS` for VRAM timeline caching. For large slot counts
    # we only stage slot 0 on CPU and upload it via small Taichi kernels.
    #
    # If unpacked masks are requested, we MUST use kernel upload because the
    # legacy `grid_fever_masks` field only stores slot 0 (shape[0]=1).
    kernel_upload = bool(write_unpacked_masks) or (MAX_SONG_SLOTS > 32)
    if kernel_upload:
        cbf_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        cbn_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        hl_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        masks_np = np.zeros((GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES), dtype=np.int32) if write_unpacked_masks else None
        masks_bits_np = np.zeros((GRID_SIZE, GRID_SIZE, 4), dtype=np.uint32)
        gap_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        fevact_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    else:
        # Allocate 3D arrays matching slotted grid fields (slot 0 for CPU upload path)
        cbf_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int16)
        cbn_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int16)
        hl_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int8)
        masks_np = (
            np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES), dtype=np.int32)
            if write_unpacked_masks
            else None
        )
        masks_bits_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, 4), dtype=np.uint32)
        gap_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int16)
        fevact_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int8)

    # Fill slot 0 with timeline data
    song_slot = 0
    total_notes = timeline_grid.total_notes  # Get total notes for gap calculation

    # Vectorized extraction: iterate once, extract directly into slot 0
    for ft_idx in range(grid_size):
        row = timeline_grid._timeline_grid[ft_idx]
        for ff_idx in range(grid_size):
            timeline = row[ff_idx]
            if timeline is not None:
                fever_mask_head, count_fever, count_normal, fevact, last_fever_end = timeline
                if kernel_upload:
                    cbf_np[ft_idx, ff_idx] = count_fever
                    cbn_np[ft_idx, ff_idx] = count_normal
                    fevact_np[ft_idx, ff_idx] = fevact
                    gap_np[ft_idx, ff_idx] = total_notes - last_fever_end
                else:
                    cbf_np[song_slot, ft_idx, ff_idx] = count_fever
                    cbn_np[song_slot, ft_idx, ff_idx] = count_normal
                    fevact_np[song_slot, ft_idx, ff_idx] = fevact
                    gap_np[song_slot, ft_idx, ff_idx] = total_notes - last_fever_end
                head_len = min(len(fever_mask_head), MAX_HEAD_NOTES)
                if kernel_upload:
                    hl_np[ft_idx, ff_idx] = head_len
                    if masks_np is not None:
                        masks_np[ft_idx, ff_idx, :head_len] = fever_mask_head[:head_len].astype(np.int32)
                else:
                    hl_np[song_slot, ft_idx, ff_idx] = head_len
                    if masks_np is not None:
                        masks_np[song_slot, ft_idx, ff_idx, :head_len] = fever_mask_head[:head_len].astype(np.int32)

                # OPTIMIZED: Vectorized bit packing using NumPy
                # Convert bool array to bit positions, then pack
                if head_len > 0:
                    fever_bits = np.nonzero(fever_mask_head[:head_len])[0]
                    for bit_pos in fever_bits:
                        word_idx = bit_pos >> 5  # bit_pos // 32
                        bit_in_word = bit_pos & 31  # bit_pos % 32
                        if kernel_upload:
                            masks_bits_np[ft_idx, ff_idx, word_idx] |= np.uint32(1) << bit_in_word
                        else:
                            masks_bits_np[song_slot, ft_idx, ff_idx, word_idx] |= np.uint32(1) << bit_in_word

    _profiler.record_upload(time.perf_counter() - _t_extract)

    # Upload to GPU
    _t_gpu_upload = time.perf_counter()
    if kernel_upload:
        _upload_grid_slot0_counts_kernel(GRID_SIZE, cbf_np, cbn_np, hl_np, gap_np, fevact_np)
        if masks_np is not None:
            _upload_grid_slot0_masks_kernel(GRID_SIZE, masks_np, masks_bits_np)
        else:
            _upload_grid_slot0_mask_bits_kernel(GRID_SIZE, masks_bits_np)
    else:
        fields.grid_count_body_fever.from_numpy(cbf_np)
        fields.grid_count_body_normal.from_numpy(cbn_np)
        fields.grid_head_len.from_numpy(hl_np)
        if masks_np is not None:
            fields.grid_fever_masks.from_numpy(masks_np)
        fields.grid_fever_masks_bits.from_numpy(masks_bits_np)
        fields.grid_gap.from_numpy(gap_np)
        fields.grid_fever_activations.from_numpy(fevact_np)
        # Keep signature generation GPU-only: build grid_sig* from the uploaded fields.
        try:
            kernels.compute_timeline_grid_signatures_kernel(int(song_slot))
        except Exception:
            pass

    # Kernel-upload path also needs signatures (slot 0).
    if kernel_upload:
        try:
            kernels.compute_timeline_grid_signatures_kernel(0)
        except Exception:
            pass
    try:
        upload_bytes = int(
            cbf_np.nbytes
            + cbn_np.nbytes
            + hl_np.nbytes
            + (masks_np.nbytes if masks_np is not None else 0)
            + masks_bits_np.nbytes
            + gap_np.nbytes
            + fevact_np.nbytes
        )
    except Exception:
        upload_bytes = 0
    _profiler.record_upload(time.perf_counter() - _t_gpu_upload, bytes_count=upload_bytes)

    _grid_uploaded = True
    set_last_uploaded_grid_id(grid_id)


def reset_timeline_state() -> None:
    """Reset module-level timeline upload caches after `ti.reset()`."""
    global _grid_uploaded, _gpu_timeline_song_id_by_slot
    _grid_uploaded = False
    _gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS
