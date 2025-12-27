"""
API Timeline - GPU timeline precomputation and grid upload.

This module provides GPU-accelerated timeline precomputation:
- precompute_timeline_gpu: Compute all 161×161 fever timelines on GPU
- _upload_timeline_grid: Upload timeline grid to GPU fields with caching
"""
import time
import numpy as np
import taichi as ti

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

from .initialization import ensure_ready, _maybe_sync, _SYNC_FOR_TIMING, _FORCE_SYNC

_profiler = get_gpu_profiler()

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()


# ============================================================================
# GPU TIMELINE PRECOMPUTATION (eliminates Numba typeof overhead)
# ============================================================================

_gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS  # Track last song per slot


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

    # Check if we already computed for this song
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("timestamps", ())
    first_ms = 0
    last_ms = 0
    try:
        if hasattr(timestamps, "__len__") and len(timestamps):
            first_ms = int(float(timestamps[0]) * 1000.0)
            last_ms = int(float(timestamps[len(timestamps) - 1]) * 1000.0)
    except Exception:
        first_ms = 0
        last_ms = 0

    try:
        human_seed = int(meta.get("HumanHitSimSeed") or 0)
    except Exception:
        human_seed = 0
    human_apply_to = str(meta.get("HumanHitSimApplyTo", "")).strip().upper()
    human_dist = str(meta.get("HumanHitSimDistribution", "")).strip().lower()
    human_great_mode = str(meta.get("HumanHitSimGreatMode", "")).strip().lower()

    song_key = (
        str(meta.get("Song Name", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        int(first_ms),
        int(last_ms),
        int(human_seed),
        human_apply_to,
        human_dist,
        human_great_mode,
    )
    song_slot = int(song_slot)
    if song_slot < 0 or song_slot >= MAX_SONG_SLOTS:
        raise ValueError(f"song_slot out of range: {song_slot}")

    if _gpu_timeline_song_id_by_slot[song_slot] == song_key:
        return  # Already computed

    # Ensure GPU is ready with refs and grid fields
    ensure_ready(ref_arrays)

    # Upload song timestamps
    timestamps = np.asarray(calc_song["song_data"]["timestamps"], dtype=np.float32)
    total_notes = len(timestamps)

    # Pad to MAX_SONG_NOTES if needed
    if total_notes > fields.MAX_SONG_NOTES:
        raise ValueError(f"Song has {total_notes} notes, max is {fields.MAX_SONG_NOTES}")

    # Create padded array
    ts_padded = np.zeros(fields.MAX_SONG_NOTES, dtype=np.float32)
    ts_padded[:total_notes] = timestamps
    fields.song_timestamps.from_numpy(ts_padded)

    # Extract song metadata
    long_notes = int(calc_song["metadata"].get("Long Notes", 0))
    last_note_time = float(calc_song["metadata"].get("Last Note Time", 0))

    # Sync before timing
    _maybe_sync(for_timing=True)
    _t0 = time.perf_counter()

    # Launch GPU kernel to compute all 161×161 timelines for this song slot
    kernels.compute_timeline_grid_kernel(
        total_notes,
        long_notes,
        last_note_time,
        song_slot,  # Grid slot for batch coalescing
    )

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

    # Avoid allocating giant (MAX_SONG_SLOTS, ...) CPU staging arrays when users
    # increase `GPU_SONG_SLOTS` for VRAM timeline caching. For large slot counts
    # we only stage slot 0 on CPU and upload it via small Taichi kernels.
    kernel_upload = MAX_SONG_SLOTS > 32
    if kernel_upload:
        cbf_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        cbn_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        hl_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        masks_np = np.zeros((GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES), dtype=np.int32)
        masks_bits_np = np.zeros((GRID_SIZE, GRID_SIZE, 4), dtype=np.uint32)
        gap_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
        fevact_np = np.zeros((GRID_SIZE, GRID_SIZE), dtype=np.int32)
    else:
        # Allocate 3D arrays matching slotted grid fields (slot 0 for CPU upload path)
        cbf_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int16)
        cbn_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int16)
        hl_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE), dtype=np.int8)
        masks_np = np.zeros((MAX_SONG_SLOTS, GRID_SIZE, GRID_SIZE, MAX_HEAD_NOTES), dtype=np.int8)
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
                    masks_np[ft_idx, ff_idx, :head_len] = fever_mask_head[:head_len].astype(np.int32)
                else:
                    hl_np[song_slot, ft_idx, ff_idx] = head_len
                    masks_np[song_slot, ft_idx, ff_idx, :head_len] = fever_mask_head[:head_len].astype(np.int8)

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
        _upload_grid_slot0_masks_kernel(GRID_SIZE, masks_np, masks_bits_np)
    else:
        fields.grid_count_body_fever.from_numpy(cbf_np)
        fields.grid_count_body_normal.from_numpy(cbn_np)
        fields.grid_head_len.from_numpy(hl_np)
        fields.grid_fever_masks.from_numpy(masks_np)
        fields.grid_fever_masks_bits.from_numpy(masks_bits_np)
        fields.grid_gap.from_numpy(gap_np)
        fields.grid_fever_activations.from_numpy(fevact_np)
    _profiler.record_upload(time.perf_counter() - _t_gpu_upload)

    _grid_uploaded = True
    set_last_uploaded_grid_id(grid_id)


def reset_timeline_state() -> None:
    """Reset module-level timeline upload caches after `ti.reset()`."""
    global _grid_uploaded, _gpu_timeline_song_id_by_slot
    _grid_uploaded = False
    _gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS
