"""The GPU's copy of a song's timeline frontier: the cached payload (frontier.timeline_cache) uploaded into the fields
of a song slot."""

import numpy as np
import taichi as ti

from gear_optimizer.frontier.timeline_cache import build_or_load_timeline_frontier_payload, build_timeline_payload
from gear_optimizer.frontier.timeline_producer import MAX_TIMELINE_FRONTIER_SURFACES, TimelineFrontierGridPayload
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.timing_envelope import TimedSong

from .. import fields
from ..fields import MAX_SONG_SLOTS
from ..runtime import on_hard_reset
from .ga_eval_cache import reset_ga_evaluation_cache
from .initialization import ensure_ready


@ti.kernel
def _upload_timeline_grid_slot_i32_kernel(
    dst: ti.template(),
    song_slot: ti.i32,
    src: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    for ft, ff in ti.ndrange(fields.GRID_SIZE, fields.GRID_SIZE):
        dst[song_slot, ft, ff] = src[ft, ff]


@ti.kernel
def _upload_timeline_grid_slot_i8_kernel(
    dst: ti.template(),
    song_slot: ti.i32,
    src: ti.types.ndarray(dtype=ti.i8, ndim=2),
):
    for ft, ff in ti.ndrange(fields.GRID_SIZE, fields.GRID_SIZE):
        dst[song_slot, ft, ff] = src[ft, ff]


@ti.kernel
def _upload_timeline_grid_masks_bits_slot_kernel(
    song_slot: ti.i32,
    src: ti.types.ndarray(dtype=ti.u32, ndim=3),
):
    for ft, ff, word in ti.ndrange(fields.GRID_SIZE, fields.GRID_SIZE, 4):
        fields.grid_fever_masks_bits[song_slot, ft, ff, word] = src[ft, ff, word]


@ti.kernel
def _upload_timeline_pool_slot_i32_kernel(
    dst: ti.template(),
    song_slot: ti.i32,
    n: ti.i32,
    src: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for i in range(n):
        dst[song_slot, i] = src[i]


@ti.kernel
def _upload_timeline_pool_masks_bits_slot_kernel(
    song_slot: ti.i32,
    n: ti.i32,
    src: ti.types.ndarray(dtype=ti.u32, ndim=2),
):
    for i, word in ti.ndrange(n, 4):
        fields.grid_frontier_masks_bits_pool[song_slot, i, word] = src[i, word]


@ti.kernel
def _upload_timeline_pool_head_coeffs_slot_kernel(
    song_slot: ti.i32,
    n: ti.i32,
    src: ti.types.ndarray(dtype=ti.i16, ndim=2),
):
    for i, coeff in ti.ndrange(n, 4):
        fields.grid_frontier_head_coeffs_pool[song_slot, i, coeff] = src[i, coeff]


def _slot_payload(payload: np.ndarray, dtype) -> np.ndarray:
    return np.ascontiguousarray(np.asarray(payload, dtype=dtype)[0])


def _upload_timeline_frontier_payload_slot(payload: TimelineFrontierGridPayload, song_slot: int) -> None:
    """Upload a cached frontier into one song slot: the prefix kernels touch only that slot, so the other slots' fields
    are neither downloaded nor uploaded again (a large forced transfer on Vulkan)."""
    reset_ga_evaluation_cache()

    def upload_i32_grid(dst, arr: np.ndarray) -> None:
        _upload_timeline_grid_slot_i32_kernel(dst, song_slot, _slot_payload(arr, np.int32))

    upload_i32_grid(fields.grid_count_body_fever, payload.grid_count_body_fever)
    upload_i32_grid(fields.grid_count_body_normal, payload.grid_count_body_normal)
    _upload_timeline_grid_slot_i8_kernel(fields.grid_head_len, song_slot, _slot_payload(payload.grid_head_len, np.int8))
    _upload_timeline_grid_masks_bits_slot_kernel(song_slot, _slot_payload(payload.grid_fever_masks_bits, np.uint32))
    upload_i32_grid(fields.grid_frontier_count, payload.grid_frontier_count)
    upload_i32_grid(fields.grid_frontier_offset, payload.grid_frontier_offset)
    upload_i32_grid(fields.grid_gap, payload.grid_gap)
    upload_i32_grid(fields.grid_fever_activations, payload.grid_fever_activations)

    pool_used = max(0, min(int(payload.frontier_pool_used), MAX_TIMELINE_FRONTIER_SURFACES))
    if pool_used > 0:
        def pool(array: np.ndarray, dtype) -> np.ndarray:
            return np.ascontiguousarray(np.asarray(array[0, :pool_used], dtype=dtype))

        fever_pool, normal_pool = fields.grid_frontier_body_fever_pool, fields.grid_frontier_body_normal_pool
        _upload_timeline_pool_slot_i32_kernel(fever_pool, song_slot, pool_used, pool(payload.grid_frontier_body_fever_pool, np.int32))
        _upload_timeline_pool_slot_i32_kernel(normal_pool, song_slot, pool_used, pool(payload.grid_frontier_body_normal_pool, np.int32))
        _upload_timeline_pool_masks_bits_slot_kernel(song_slot, pool_used, pool(payload.grid_frontier_masks_bits_pool, np.uint32))
        _upload_timeline_pool_head_coeffs_slot_kernel(song_slot, pool_used, pool(payload.grid_frontier_head_coeffs_pool, np.int16))


_gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS  # Track last song per slot


def precompute_timeline_gpu(
    song: TimedSong,
    curves: StatCurves,
    song_slot: int = 0,
    *,
    prebuilt_payload: TimelineFrontierGridPayload | None = None,
) -> None:
    """Upload the song's timeline frontier into `song_slot` (0-7), once per song and slot: the per-slot fields the GA
    scoring kernels read. `prebuilt_payload` is uploaded by value instead of the cache's (the synthetic GPU warmup's
    disposable payload)."""
    song_slot = int(song_slot)
    if song_slot < 0 or song_slot >= MAX_SONG_SLOTS:
        raise ValueError(f"song_slot out of range: {song_slot}")

    # Ensure GPU is ready with refs and grid fields (even on cache hit).
    ensure_ready(curves)

    song_key = song.timeline_key
    if _gpu_timeline_song_id_by_slot[song_slot] == song_key:
        return
    payload = prebuilt_payload if prebuilt_payload is not None else build_or_load_timeline_frontier_payload(song, curves).payload
    if int(payload.grid_frontier_count.shape[1]) < MAX_STAT + 1 or int(payload.grid_frontier_count.shape[2]) < MAX_STAT + 1:
        raise ValueError(
            "Timeline frontier payload is incomplete. Startup cache prebuild must build the "
            "candidate-independent all-FT/FF timeline frontier before runtime scoring."
        )
    _upload_timeline_frontier_payload_slot(payload, song_slot)
    _gpu_timeline_song_id_by_slot[song_slot] = song_key


def precompute_timeline_gpu_for_warmup(song: TimedSong, curves: StatCurves, song_slot: int = 0) -> None:
    """The GPU JIT warmup's upload: its synthetic chart is not in the song queue, so its payload is built here and never
    cached. The GPU is made ready first, so a cold-init Vulkan reset happens before the build."""
    ensure_ready(curves)
    precompute_timeline_gpu(song, curves, song_slot=song_slot, prebuilt_payload=build_timeline_payload(song, curves))


def uploaded_timeline_song_key(song_slot: int) -> tuple | None:
    """The timeline key of the song whose frontier is uploaded in `song_slot` (None before any upload)."""
    return _gpu_timeline_song_id_by_slot[int(song_slot)]


@on_hard_reset
def reset_timeline_state() -> None:
    """Forget the uploads after `ti.reset()`."""
    global _gpu_timeline_song_id_by_slot
    _gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS
