"""
API Timeline - GPU timeline precomputation and grid upload.

This module provides GPU-accelerated timeline precomputation:
- precompute_timeline_gpu: Compute all 161×161 fever timelines on GPU
- _upload_timeline_grid: Upload timeline grid to GPU fields with caching
"""

import time
import hashlib
import numpy as np
import taichi as ti

from gear_optimizer.core.env_config import env_flag
from gear_optimizer.core.utils import human_hitsim_timing_context
from gear_optimizer.solver.gpu_profiler import get_gpu_profiler
from ..fields import (
    GRID_SIZE,
    MAX_HEAD_NOTES,
    MAX_SONG_SLOTS,
    get_last_uploaded_grid_id,
    set_last_uploaded_grid_id,
)
from .. import fields
from ..kernel_loader import get_kernels

from .initialization import ensure_ready, _ref_arrays_sig, _maybe_sync, _SYNC_FOR_TIMING, _FORCE_SYNC

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
    """Upload chord-group arrays used by the analytical ceiling HitSim timeline kernel."""
    for g in range(n_groups):
        fields.song_group_starts[g] = group_starts[g]
        fields.song_group_base_t_ms[g] = group_base_t_ms[g]
        fields.song_group_low_ms[g] = group_low_ms[g]
        fields.song_group_high_ms[g] = group_high_ms[g]


# ============================================================================
# GPU TIMELINE PRECOMPUTATION (eliminates Numba typeof overhead)
# ============================================================================

_gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS  # Track last song per slot


def _array_sig(v: object) -> bytes:
    """
    Stable content signature for cache keys.

    Timeline caching must account for note types and timestamps content; first/last
    samples are insufficient (distinct charts can alias).
    """
    if v is None:
        return b"\x00"
    try:
        arr = np.asarray(v)
    except Exception:
        return bytes(repr(v), "utf-8")
    if arr.ndim == 0:
        try:
            arr = np.asarray([arr.item()], dtype=arr.dtype)
        except Exception:
            arr = np.asarray([repr(arr)], dtype=np.uint8)
    try:
        is_contig = bool(arr.flags["C_CONTIGUOUS"])
    except Exception:
        is_contig = False
    arr_c = arr if is_contig else np.ascontiguousarray(arr)
    h = hashlib.blake2b(digest_size=16)
    h.update(str(arr_c.dtype).encode("utf-8"))
    h.update(int(arr_c.ndim).to_bytes(1, "little", signed=False))
    for d in arr_c.shape:
        h.update(int(d).to_bytes(4, "little", signed=False))
    h.update(memoryview(arr_c).cast("B"))
    return h.digest()


def _song_timing_cache_key(calc_song: dict) -> tuple:
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    use_ceiling = bool(env_flag("GPU_TIMELINE_CEILING_HITSIM", "1"))
    if use_ceiling:
        chart_ts = song_data.get("chart_timestamps", None)
        timestamps = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    else:
        timestamps = song_data.get("timestamps", ())
    return (
        str(meta.get("Song Name", "")),
        str(meta.get("Difficulty", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        int(1 if use_ceiling else 0),
        _array_sig(timestamps),
        _array_sig(song_data.get("note_types")),
    ) + (() if use_ceiling else human_hitsim_timing_context(calc_song))


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
    ensure_ready(ref_arrays)

    # Check if we already computed for this song+ref set.
    ref_sig = _ref_arrays_sig(ref_arrays) if isinstance(ref_arrays, dict) else b""
    song_key = _song_timing_cache_key(calc_song) + (bytes(ref_sig),)
    if _gpu_timeline_song_id_by_slot[song_slot] == song_key:
        return  # Already computed

    song_data = calc_song.get("song_data", {}) or {}
    use_ceiling = bool(env_flag("GPU_TIMELINE_CEILING_HITSIM", "1"))

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
    if _profiler.enabled:
        _t_ts = time.perf_counter()
        _upload_song_timestamps_kernel(int(total_notes), timestamps)
        _profiler.record_upload(time.perf_counter() - _t_ts, bytes_count=int(timestamps.nbytes))
    else:
        _upload_song_timestamps_kernel(int(total_notes), timestamps)

    group_count = 0
    if use_ceiling:
        from gear_optimizer.solver.hit_simulation import prepare_perfect_hit_simulation

        note_types = song_data.get("note_types", None)
        prepared = prepare_perfect_hit_simulation(
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
        if int(prepared.get("n", total_notes) or 0) != int(total_notes):
            raise ValueError("prepare_perfect_hit_simulation produced mismatched note count")
        if total_notes > 0 and group_count <= 0:
            raise ValueError("prepare_perfect_hit_simulation produced no chord groups")

        note_group_idx = np.full(int(total_notes), -1, dtype=np.int32)
        for g in range(group_count):
            s = int(group_starts[g])
            e = int(group_ends[g])
            if e > s:
                note_group_idx[s:e] = int(g)
        if total_notes > 0 and int(np.any(note_group_idx < 0)):
            raise ValueError("prepare_perfect_hit_simulation produced uncovered note indices")

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
        kernels.compute_timeline_grid_ceiling_hitsim_kernel(
            total_notes,
            long_notes,
            last_note_time,
            int(group_count),
            song_slot,  # Grid slot for batch coalescing
            int(write_unpacked_masks),
        )
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
