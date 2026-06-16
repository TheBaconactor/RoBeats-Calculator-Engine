"""
API Timeline - cached exact frontier load and GPU grid upload.

Startup builds the candidate-independent timeline frontier cache; runtime uploads
the cached grid/frontier payload for the active song slot.
"""

import time
import hashlib
import threading
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import logging
import numpy as np
import taichi as ti

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.utils import timing_envelope_timing_context
from gear_optimizer.solver.frontier_cache_errors import MissingFrontierCacheError
from gear_optimizer.solver.timeline_exact_frontier import (
    TimelineFrontierGridPayload,
    build_timeline_frontier_grid_payload,
)
from ..fields import (
    MAX_SONG_SLOTS,
)
from .. import fields
from ..kernel_loader import get_kernels

from .initialization import ensure_ready, _maybe_sync, _SYNC_FOR_TIMING, _FORCE_SYNC

from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()

_TIMELINE_FRONTIER_CACHE_ARRAY_NAMES = frozenset(
    (
        "version",
        "frontier_pool_used",
        "grid_count_body_fever",
        "grid_count_body_normal",
        "grid_head_len",
        "grid_N_hn",
        "grid_N_hf",
        "grid_Sigma_hn",
        "grid_Sigma_hf",
        "grid_fever_masks_bits",
        "grid_frontier_count",
        "grid_frontier_offset",
        "grid_frontier_body_fever_pool",
        "grid_frontier_body_normal_pool",
        "grid_frontier_masks_bits_pool",
        "grid_gap",
        "grid_fever_activations",
        "group_n",
        "group_count",
        "group_starts",
        "group_ends",
        "group_base_t_ms",
        "group_low_ms",
        "group_high_ms",
        "note_group_idx",
    )
)


@ti.kernel
def _upload_timeline_grid_slot_i32_kernel(
    dst: ti.template(),
    song_slot: ti.i32,
    src: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    for ft, ff in ti.ndrange(fields.GRID_SIZE, fields.GRID_SIZE):
        dst[song_slot, ft, ff] = src[ft, ff]


@ti.kernel
def _upload_timeline_grid_slot_i16_kernel(
    dst: ti.template(),
    song_slot: ti.i32,
    src: ti.types.ndarray(dtype=ti.i16, ndim=2),
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


def _slot_payload(payload: np.ndarray, source_slot_i: int, dtype) -> np.ndarray:
    return np.ascontiguousarray(np.asarray(payload, dtype=dtype)[int(source_slot_i)])


def _upload_timeline_frontier_payload_slot(
    payload: TimelineFrontierGridPayload,
    song_slot_i: int,
    *,
    source_slot_i: int = 0,
) -> int:
    """
    Upload one cached frontier slot without GPU->CPU round-tripping existing fields.

    The old merge path used `field.to_numpy()` to preserve other song slots, patched
    one slot on the CPU, then `from_numpy()` uploaded the whole field again. On
    Vulkan that is a large forced download plus a large upload. These prefix kernels
    update only the active slot.
    """
    source_slot_i = int(source_slot_i)
    song_slot_i = int(song_slot_i)
    upload_bytes = 0

    def upload_i32_grid(dst, arr: np.ndarray) -> None:
        nonlocal upload_bytes
        src = _slot_payload(arr, source_slot_i, np.int32)
        upload_bytes += int(src.nbytes)
        _upload_timeline_grid_slot_i32_kernel(dst, song_slot_i, src)

    def upload_i16_grid(dst, arr: np.ndarray) -> None:
        nonlocal upload_bytes
        src = _slot_payload(arr, source_slot_i, np.int16)
        upload_bytes += int(src.nbytes)
        _upload_timeline_grid_slot_i16_kernel(dst, song_slot_i, src)

    def upload_i8_grid(dst, arr: np.ndarray) -> None:
        nonlocal upload_bytes
        src = _slot_payload(arr, source_slot_i, np.int8)
        upload_bytes += int(src.nbytes)
        _upload_timeline_grid_slot_i8_kernel(dst, song_slot_i, src)

    upload_i32_grid(fields.grid_count_body_fever, payload.grid_count_body_fever)
    upload_i32_grid(fields.grid_count_body_normal, payload.grid_count_body_normal)
    upload_i8_grid(fields.grid_head_len, payload.grid_head_len)
    upload_i16_grid(fields.grid_N_hn, payload.grid_N_hn)
    upload_i16_grid(fields.grid_N_hf, payload.grid_N_hf)
    upload_i16_grid(fields.grid_Sigma_hn, payload.grid_Sigma_hn)
    upload_i16_grid(fields.grid_Sigma_hf, payload.grid_Sigma_hf)

    masks = _slot_payload(payload.grid_fever_masks_bits, source_slot_i, np.uint32)
    upload_bytes += int(masks.nbytes)
    _upload_timeline_grid_masks_bits_slot_kernel(song_slot_i, masks)

    upload_i32_grid(fields.grid_frontier_count, payload.grid_frontier_count)
    upload_i32_grid(fields.grid_frontier_offset, payload.grid_frontier_offset)
    upload_i32_grid(fields.grid_gap, payload.grid_gap)
    upload_i32_grid(fields.grid_fever_activations, payload.grid_fever_activations)

    pool_used = max(0, min(int(payload.frontier_pool_used), int(fields.MAX_TIMELINE_FRONTIER_SURFACES)))
    if pool_used > 0:
        fever_pool = np.ascontiguousarray(
            np.asarray(payload.grid_frontier_body_fever_pool[source_slot_i, :pool_used], dtype=np.int32)
        )
        normal_pool = np.ascontiguousarray(
            np.asarray(payload.grid_frontier_body_normal_pool[source_slot_i, :pool_used], dtype=np.int32)
        )
        mask_pool = np.ascontiguousarray(
            np.asarray(payload.grid_frontier_masks_bits_pool[source_slot_i, :pool_used, :], dtype=np.uint32)
        )
        upload_bytes += int(fever_pool.nbytes + normal_pool.nbytes + mask_pool.nbytes)
        _upload_timeline_pool_slot_i32_kernel(fields.grid_frontier_body_fever_pool, song_slot_i, pool_used, fever_pool)
        _upload_timeline_pool_slot_i32_kernel(fields.grid_frontier_body_normal_pool, song_slot_i, pool_used, normal_pool)
        _upload_timeline_pool_masks_bits_slot_kernel(song_slot_i, pool_used, mask_pool)

    return int(upload_bytes)


# ============================================================================
# GPU TIMELINE PRECOMPUTATION (eliminates Numba typeof overhead)
# ============================================================================

_gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS  # Track last song per slot
_FRONTIER_GROUP_PAYLOAD_CACHE_MAX = 32
_frontier_group_payload_cache: "OrderedDict[tuple, dict]" = OrderedDict()
_FRONTIER_PAYLOAD_CACHE_MAX = 8
_frontier_payload_cache: "OrderedDict[tuple, object]" = OrderedDict()
_frontier_payload_cache_lock = threading.RLock()
# Bump whenever the base frontier OUTPUT changes in a way the cache key does NOT capture.
# The key (_frontier_payload_cache_key -> song_key) hashes raw song inputs + window settings,
# NOT the grouping/DP logic, so a pure logic change is invisible to it and only the version
# invalidates stale disk payloads. v6: the chord-tied held-tail grouping split (issue #42 /
# PR #45) changed the base frontier for held-tail-chord songs without touching any key input,
# so pre-fix v5 payloads in bin/timeline_frontier_cache/ must not be reused.
_FRONTIER_DISK_CACHE_VERSION = "exact-frontier-v6"


@dataclass(frozen=True)
class TimelineFrontierPrewarmResult:
    payload: TimelineFrontierGridPayload
    cache_key: tuple
    disk_path: Path
    cache_source: str
    elapsed_ms: float
    song_profile_key: str | None
    total_notes: int
    long_notes: int


@dataclass(frozen=True)
class TimelineFrontierCacheInfo:
    cache_key: tuple
    disk_path: Path
    cache_source: str
    song_profile_key: str | None
    total_notes: int
    long_notes: int


def _frontier_payload_cache_key(song_key: tuple, ref_ft: np.ndarray, ref_ff: np.ndarray) -> tuple:
    return (
        _FRONTIER_DISK_CACHE_VERSION,
        song_key,
        bytes(array_sig16(np.asarray(ref_ft, dtype=np.float32).reshape(-1))),
        bytes(array_sig16(np.asarray(ref_ff, dtype=np.float32).reshape(-1))),
    )


def _frontier_disk_cache_dir() -> Path:
    override = str(env_get("TIMELINE_FRONTIER_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[4] / "bin" / "timeline_frontier_cache"


def _frontier_disk_cache_path(cache_key: tuple) -> Path:
    digest = hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()
    return _frontier_disk_cache_dir() / f"{digest}.npz"


def _group_payload_from_cache_arrays(
    *,
    group_starts: np.ndarray,
    group_ends: np.ndarray,
    group_base_t_ms: np.ndarray,
    group_low_ms: np.ndarray,
    group_high_ms: np.ndarray,
    note_group_idx: np.ndarray,
    group_n: int,
    group_count: int,
    expected_n: int | None = None,
) -> dict | None:
    try:
        n = int(group_n)
        gcount = int(group_count)
    except Exception as e:
        logger.debug(f"timeline:_group_payload_from_cache_arrays: {e}")
        return None
    if n < 0 or gcount < 0:
        return None
    if expected_n is not None and int(expected_n) != int(n):
        return None
    starts = np.ascontiguousarray(np.asarray(group_starts, dtype=np.int32).reshape(-1))
    ends = np.ascontiguousarray(np.asarray(group_ends, dtype=np.int32).reshape(-1))
    base_t = np.ascontiguousarray(np.asarray(group_base_t_ms, dtype=np.int32).reshape(-1))
    low = np.ascontiguousarray(np.asarray(group_low_ms, dtype=np.int32).reshape(-1))
    high = np.ascontiguousarray(np.asarray(group_high_ms, dtype=np.int32).reshape(-1))
    idx = np.ascontiguousarray(np.asarray(note_group_idx, dtype=np.int32).reshape(-1))
    if int(idx.shape[0]) != int(n):
        return None
    if int(starts.shape[0]) != int(gcount):
        return None
    if int(ends.shape[0]) != int(gcount):
        return None
    if int(base_t.shape[0]) != int(gcount):
        return None
    if int(low.shape[0]) != int(gcount):
        return None
    if int(high.shape[0]) != int(gcount):
        return None
    if int(n) > 0 and int(gcount) <= 0:
        return None
    return {
        "n": int(n),
        "group_count": int(gcount),
        "note_group_idx": idx,
        "group_starts": starts,
        "group_ends": ends,
        "group_base_t_ms": base_t,
        "group_low_ms": low,
        "group_high_ms": high,
    }


def _group_payload_from_npz(data: object, *, expected_n: int | None = None) -> dict | None:
    keys = (
        "group_starts",
        "group_ends",
        "group_base_t_ms",
        "group_low_ms",
        "group_high_ms",
        "note_group_idx",
        "group_n",
        "group_count",
    )
    try:
        if not all(k in data for k in keys):
            return None
        return _group_payload_from_cache_arrays(
            group_starts=np.asarray(data["group_starts"], dtype=np.int32),
            group_ends=np.asarray(data["group_ends"], dtype=np.int32),
            group_base_t_ms=np.asarray(data["group_base_t_ms"], dtype=np.int32),
            group_low_ms=np.asarray(data["group_low_ms"], dtype=np.int32),
            group_high_ms=np.asarray(data["group_high_ms"], dtype=np.int32),
            note_group_idx=np.asarray(data["note_group_idx"], dtype=np.int32),
            group_n=int(np.asarray(data["group_n"]).item()),
            group_count=int(np.asarray(data["group_count"]).item()),
            expected_n=expected_n,
        )
    except Exception as e:
        logger.debug(f"timeline:_group_payload_from_npz: {e}")
        return None


def _group_cache_get(base_song_key: tuple, *, expected_n: int) -> dict | None:
    with _frontier_payload_cache_lock:
        cached = _frontier_group_payload_cache.get(base_song_key)
        if not isinstance(cached, dict):
            return None
        try:
            if int(cached.get("n", -1) or -1) != int(expected_n):
                return None
            if int(cached.get("group_count", 0) or 0) <= 0 and int(expected_n) > 0:
                return None
        except Exception as e:
            logger.debug(f"timeline:_group_cache_get: {e}")
            return None
        _frontier_group_payload_cache.move_to_end(base_song_key)
        return cached


def _group_cache_put(base_song_key: tuple, payload: dict) -> None:
    with _frontier_payload_cache_lock:
        _frontier_group_payload_cache[base_song_key] = payload
        _frontier_group_payload_cache.move_to_end(base_song_key)
        while len(_frontier_group_payload_cache) > int(_FRONTIER_GROUP_PAYLOAD_CACHE_MAX):
            _frontier_group_payload_cache.popitem(last=False)


def _load_group_payload_from_frontier_disk(cache_key: tuple, *, expected_n: int) -> dict | None:
    path = _frontier_disk_cache_path(cache_key)
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version != _FRONTIER_DISK_CACHE_VERSION:
                return None
            return _group_payload_from_npz(data, expected_n=expected_n)
    except Exception as e:
        logger.debug(f"timeline:_load_group_payload_from_frontier_disk: {e}")
        return None


def _load_frontier_payload_from_disk(cache_key: tuple) -> TimelineFrontierGridPayload | None:
    path = _frontier_disk_cache_path(cache_key)
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version != _FRONTIER_DISK_CACHE_VERSION:
                return None
            grid_count_body_fever = np.asarray(data["grid_count_body_fever"], dtype=np.int32)
            grid_count_body_normal = np.asarray(data["grid_count_body_normal"], dtype=np.int32)
            grid_head_len = np.asarray(data["grid_head_len"], dtype=np.int8)
            grid_N_hn = np.asarray(data["grid_N_hn"], dtype=np.int16)
            grid_N_hf = np.asarray(data["grid_N_hf"], dtype=np.int16)
            grid_Sigma_hn = np.asarray(data["grid_Sigma_hn"], dtype=np.int16)
            grid_Sigma_hf = np.asarray(data["grid_Sigma_hf"], dtype=np.int16)
            grid_fever_masks_bits = np.asarray(data["grid_fever_masks_bits"], dtype=np.uint32)
            grid_frontier_count = np.asarray(data["grid_frontier_count"], dtype=np.int32)
            grid_frontier_offset = np.asarray(data["grid_frontier_offset"], dtype=np.int32)
            grid_frontier_body_fever_pool = np.asarray(data["grid_frontier_body_fever_pool"], dtype=np.int32)
            grid_frontier_body_normal_pool = np.asarray(data["grid_frontier_body_normal_pool"], dtype=np.int32)
            grid_frontier_masks_bits_pool = np.asarray(data["grid_frontier_masks_bits_pool"], dtype=np.uint32)
            grid_gap = np.asarray(data["grid_gap"], dtype=np.int32)
            grid_fever_activations = np.asarray(data["grid_fever_activations"], dtype=np.int32)

            # Compact on-disk format stores a single source slot; runtime upload remaps it.
            if grid_count_body_fever.ndim == 2:
                grid_count_body_fever = np.expand_dims(grid_count_body_fever, axis=0)
            if grid_count_body_normal.ndim == 2:
                grid_count_body_normal = np.expand_dims(grid_count_body_normal, axis=0)
            if grid_head_len.ndim == 2:
                grid_head_len = np.expand_dims(grid_head_len, axis=0)
            if grid_N_hn.ndim == 2:
                grid_N_hn = np.expand_dims(grid_N_hn, axis=0)
            if grid_N_hf.ndim == 2:
                grid_N_hf = np.expand_dims(grid_N_hf, axis=0)
            if grid_Sigma_hn.ndim == 2:
                grid_Sigma_hn = np.expand_dims(grid_Sigma_hn, axis=0)
            if grid_Sigma_hf.ndim == 2:
                grid_Sigma_hf = np.expand_dims(grid_Sigma_hf, axis=0)
            if grid_fever_masks_bits.ndim == 3:
                grid_fever_masks_bits = np.expand_dims(grid_fever_masks_bits, axis=0)
            if grid_frontier_count.ndim == 2:
                grid_frontier_count = np.expand_dims(grid_frontier_count, axis=0)
            if grid_frontier_offset.ndim == 2:
                grid_frontier_offset = np.expand_dims(grid_frontier_offset, axis=0)
            if grid_frontier_body_fever_pool.ndim == 1:
                grid_frontier_body_fever_pool = np.expand_dims(grid_frontier_body_fever_pool, axis=0)
            if grid_frontier_body_normal_pool.ndim == 1:
                grid_frontier_body_normal_pool = np.expand_dims(grid_frontier_body_normal_pool, axis=0)
            if grid_frontier_masks_bits_pool.ndim == 2:
                grid_frontier_masks_bits_pool = np.expand_dims(grid_frontier_masks_bits_pool, axis=0)
            if grid_gap.ndim == 2:
                grid_gap = np.expand_dims(grid_gap, axis=0)
            if grid_fever_activations.ndim == 2:
                grid_fever_activations = np.expand_dims(grid_fever_activations, axis=0)
            return TimelineFrontierGridPayload(
                grid_count_body_fever=grid_count_body_fever,
                grid_count_body_normal=grid_count_body_normal,
                grid_head_len=grid_head_len,
                grid_N_hn=grid_N_hn,
                grid_N_hf=grid_N_hf,
                grid_Sigma_hn=grid_Sigma_hn,
                grid_Sigma_hf=grid_Sigma_hf,
                grid_fever_masks_bits=grid_fever_masks_bits,
                grid_frontier_count=grid_frontier_count,
                grid_frontier_offset=grid_frontier_offset,
                grid_frontier_body_fever_pool=grid_frontier_body_fever_pool,
                grid_frontier_body_normal_pool=grid_frontier_body_normal_pool,
                grid_frontier_masks_bits_pool=grid_frontier_masks_bits_pool,
                grid_gap=grid_gap,
                grid_fever_activations=grid_fever_activations,
                frontier_pool_used=int(data["frontier_pool_used"].item()),
            )
    except Exception as e:
        logger.debug(f"timeline:_load_frontier_payload_from_disk: {e}")
        try:
            path.unlink(missing_ok=True)
        except Exception as e:
            logger.debug(f"timeline:_load_frontier_payload_from_disk: {e}")
        return None


def timeline_frontier_cache_file_is_complete(cache_file: str | Path) -> bool:
    try:
        path = Path(cache_file)
    except TypeError:
        return False
    if not path.exists():
        return False
    grid_shape = (TOTAL_ROWS + 1, TOTAL_ROWS + 1)
    try:
        with np.load(path, allow_pickle=False) as data:
            files = set(data.files)
            if files != _TIMELINE_FRONTIER_CACHE_ARRAY_NAMES:
                return False
            version = str(data["version"].item())
            if version != _FRONTIER_DISK_CACHE_VERSION:
                return False
            pool_used = int(np.asarray(data["frontier_pool_used"]).item())
            if pool_used < 0:
                return False
            for name in (
                "grid_count_body_fever",
                "grid_count_body_normal",
                "grid_head_len",
                "grid_N_hn",
                "grid_N_hf",
                "grid_Sigma_hn",
                "grid_Sigma_hf",
                "grid_frontier_count",
                "grid_frontier_offset",
                "grid_gap",
                "grid_fever_activations",
            ):
                if tuple(np.asarray(data[name]).shape) != grid_shape:
                    return False
            if tuple(np.asarray(data["grid_fever_masks_bits"]).shape) != (*grid_shape, 4):
                return False
            if tuple(np.asarray(data["grid_frontier_body_fever_pool"]).shape) != (pool_used,):
                return False
            if tuple(np.asarray(data["grid_frontier_body_normal_pool"]).shape) != (pool_used,):
                return False
            if tuple(np.asarray(data["grid_frontier_masks_bits_pool"]).shape) != (pool_used, 4):
                return False
            frontier_count = np.asarray(data["grid_frontier_count"], dtype=np.int64)
            frontier_offset = np.asarray(data["grid_frontier_offset"], dtype=np.int64)
            if bool(np.any(frontier_count < 0)) or bool(np.any(frontier_offset < 0)):
                return False
            if bool(np.any(frontier_offset + frontier_count > pool_used)):
                return False
            if _group_payload_from_npz(data, expected_n=None) is None:
                return False
    except Exception:
        return False
    return True


def _get_cached_frontier_payload_with_source(
    song_key: tuple,
    *,
    ref_ft: np.ndarray,
    ref_ff: np.ndarray,
) -> tuple[TimelineFrontierGridPayload | None, str]:
    cache_key = _frontier_payload_cache_key(song_key, ref_ft, ref_ff)
    with _frontier_payload_cache_lock:
        cached = _frontier_payload_cache.get(cache_key)
        if isinstance(cached, TimelineFrontierGridPayload):
            _frontier_payload_cache.move_to_end(cache_key)
            return cached, "memory"

    cached = _load_frontier_payload_from_disk(cache_key)
    if isinstance(cached, TimelineFrontierGridPayload):
        with _frontier_payload_cache_lock:
            _frontier_payload_cache[cache_key] = cached
            _frontier_payload_cache.move_to_end(cache_key)
        return cached, "disk"
    return None, "missing"


def _save_frontier_payload_to_disk(
    cache_key: tuple,
    payload: TimelineFrontierGridPayload,
    *,
    group_payload: dict | None = None,
) -> None:
    path = _frontier_disk_cache_path(cache_key)
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz")
        source_slot_i = 0
        pool_used = max(0, int(payload.frontier_pool_used))
        save_kwargs: dict[str, object] = {}
        if isinstance(group_payload, dict):
            persisted_group = _group_payload_from_cache_arrays(
                group_starts=np.asarray(group_payload.get("group_starts", ()), dtype=np.int32),
                group_ends=np.asarray(group_payload.get("group_ends", ()), dtype=np.int32),
                group_base_t_ms=np.asarray(group_payload.get("group_base_t_ms", ()), dtype=np.int32),
                group_low_ms=np.asarray(group_payload.get("group_low_ms", ()), dtype=np.int32),
                group_high_ms=np.asarray(group_payload.get("group_high_ms", ()), dtype=np.int32),
                note_group_idx=np.asarray(group_payload.get("note_group_idx", ()), dtype=np.int32),
                group_n=int(group_payload.get("n", 0) or 0),
                group_count=int(group_payload.get("group_count", 0) or 0),
                expected_n=None,
            )
            if isinstance(persisted_group, dict):
                save_kwargs.update(
                    {
                        "group_n": np.asarray(int(persisted_group["n"]), dtype=np.int32),
                        "group_count": np.asarray(int(persisted_group["group_count"]), dtype=np.int32),
                        "group_starts": np.asarray(persisted_group["group_starts"], dtype=np.int32),
                        "group_ends": np.asarray(persisted_group["group_ends"], dtype=np.int32),
                        "group_base_t_ms": np.asarray(persisted_group["group_base_t_ms"], dtype=np.int32),
                        "group_low_ms": np.asarray(persisted_group["group_low_ms"], dtype=np.int32),
                        "group_high_ms": np.asarray(persisted_group["group_high_ms"], dtype=np.int32),
                        "note_group_idx": np.asarray(persisted_group["note_group_idx"], dtype=np.int32),
                    }
                )
        np.savez_compressed(
            tmp,
            version=np.asarray(_FRONTIER_DISK_CACHE_VERSION),
            frontier_pool_used=np.asarray(pool_used, dtype=np.int32),
            grid_count_body_fever=np.asarray(payload.grid_count_body_fever[source_slot_i], dtype=np.int32),
            grid_count_body_normal=np.asarray(payload.grid_count_body_normal[source_slot_i], dtype=np.int32),
            grid_head_len=np.asarray(payload.grid_head_len[source_slot_i], dtype=np.int8),
            grid_N_hn=np.asarray(payload.grid_N_hn[source_slot_i], dtype=np.int16),
            grid_N_hf=np.asarray(payload.grid_N_hf[source_slot_i], dtype=np.int16),
            grid_Sigma_hn=np.asarray(payload.grid_Sigma_hn[source_slot_i], dtype=np.int16),
            grid_Sigma_hf=np.asarray(payload.grid_Sigma_hf[source_slot_i], dtype=np.int16),
            grid_fever_masks_bits=np.asarray(payload.grid_fever_masks_bits[source_slot_i], dtype=np.uint32),
            grid_frontier_count=np.asarray(payload.grid_frontier_count[source_slot_i], dtype=np.int32),
            grid_frontier_offset=np.asarray(payload.grid_frontier_offset[source_slot_i], dtype=np.int32),
            grid_frontier_body_fever_pool=np.asarray(
                payload.grid_frontier_body_fever_pool[source_slot_i, :pool_used], dtype=np.int32
            ),
            grid_frontier_body_normal_pool=np.asarray(
                payload.grid_frontier_body_normal_pool[source_slot_i, :pool_used], dtype=np.int32
            ),
            grid_frontier_masks_bits_pool=np.asarray(
                payload.grid_frontier_masks_bits_pool[source_slot_i, :pool_used, :], dtype=np.uint32
            ),
            grid_gap=np.asarray(payload.grid_gap[source_slot_i], dtype=np.int32),
            grid_fever_activations=np.asarray(payload.grid_fever_activations[source_slot_i], dtype=np.int32),
            **save_kwargs,
        )
        tmp.replace(path)
    except Exception as e:
        logger.debug(f"timeline:_save_frontier_payload_to_disk: {e}")
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except Exception as e:
                logger.debug(f"timeline:_save_frontier_payload_to_disk: {e}")


def _timeline_song_profile_key(calc_song: dict | None) -> str | None:
    try:
        meta = (calc_song or {}).get("metadata", {}) or {}
        song_name = str(meta.get("Song Name") or meta.get("Song") or "").strip()
        if not song_name:
            return None
        diff = str(meta.get("Difficulty") or "").strip()
        return f"{song_name} ({diff})" if diff else song_name
    except Exception as e:
        logger.debug(f"timeline:_timeline_song_profile_key: {e}")
        return None


def _emit_timeline_phase(
    *,
    phase: str,
    start: float,
    calc_song: dict | None,
    song_slot: int,
    **metrics,
) -> None:
    payload = {
        "phase": str(phase),
        "ms": float((time.perf_counter() - float(start)) * 1000.0),
        "song_slot": int(song_slot),
    }
    payload.update(metrics)
    emit_profile_event(
        component="gpu_executor",
        event="timeline_precompute_phase",
        song_key=_timeline_song_profile_key(calc_song),
        metrics=payload,
    )


def _song_timing_cache_key(calc_song: dict) -> tuple:
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    cached = calc_song.get("_gpu_timing_cache_key_frontier", None)
    if isinstance(cached, tuple) and len(cached) == 11:
        return cached
    chart_ts = song_data.get("chart_timestamps", None)
    timestamps = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    ts_sig = song_data.get("_chart_timestamps_sig", None)
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
        bytes(ts_sig),
        bytes(nt_sig),
    ) + timing_envelope_timing_context(calc_song)
    # Cache on the calc_song dict to avoid repeated full-array hashing when the
    # same song is revisited and precompute_timeline_gpu() hits the slot cache.
    calc_song["_gpu_timing_cache_key_frontier"] = key
    return key


def _get_or_build_frontier_group_payload(
    base_song_key: tuple,
    *,
    timestamps: np.ndarray,
    note_types: object,
) -> dict:
    """
    Prepare and cache chord-group payloads used by the exact timeline frontier.

    This CPU preprocessing is a pure function of chart timestamps + note types (and the
    fixed Perfect window constants). Caching avoids recomputing grouping + dense note->group
    maps when the same song is revisited across slots or after timeline cache resets.
    """
    n = int(getattr(timestamps, "shape", (0,))[0] or 0)
    cached = _group_cache_get(base_song_key, expected_n=n)
    if isinstance(cached, dict):
        return cached

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
        except Exception as e:
            logger.debug(f"timeline:_get_or_build_frontier_group_payload: {e}")
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
        "group_ends": np.ascontiguousarray(group_ends),
        "group_base_t_ms": np.ascontiguousarray(group_base_t_ms),
        "group_low_ms": np.ascontiguousarray(group_low_ms),
        "group_high_ms": np.ascontiguousarray(group_high_ms),
    }
    validated = _group_payload_from_cache_arrays(
        group_starts=np.asarray(payload["group_starts"], dtype=np.int32),
        group_ends=np.asarray(payload["group_ends"], dtype=np.int32),
        group_base_t_ms=np.asarray(payload["group_base_t_ms"], dtype=np.int32),
        group_low_ms=np.asarray(payload["group_low_ms"], dtype=np.int32),
        group_high_ms=np.asarray(payload["group_high_ms"], dtype=np.int32),
        note_group_idx=np.asarray(payload["note_group_idx"], dtype=np.int32),
        group_n=int(payload["n"]),
        group_count=int(payload["group_count"]),
        expected_n=n,
    )
    if isinstance(validated, dict):
        _group_cache_put(base_song_key, validated)
        return validated
    return payload


def _get_or_build_frontier_payload_with_source(
    song_key: tuple,
    *,
    song_slot: int,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    song_profile_key: str | None = None,
    group_payload: dict,
    ref_ft: np.ndarray,
    ref_ff: np.ndarray,
) -> tuple[TimelineFrontierGridPayload, str]:
    """Build and cache the packed exact frontier grid for a song/ref signature."""
    global _frontier_payload_cache

    cache_key = _frontier_payload_cache_key(song_key, ref_ft, ref_ff)
    cached, cache_source = _get_cached_frontier_payload_with_source(
        song_key,
        ref_ft=np.asarray(ref_ft, dtype=np.float32),
        ref_ff=np.asarray(ref_ff, dtype=np.float32),
    )
    if isinstance(cached, TimelineFrontierGridPayload):
        return cached, cache_source

    payload = build_timeline_frontier_grid_payload(
        song_slot=0,
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        song_key=song_profile_key,
        group_starts=np.asarray(group_payload.get("group_starts", ()), dtype=np.int32),
        group_ends=np.asarray(group_payload.get("group_ends", ()), dtype=np.int32),
        group_base_t_ms=np.asarray(group_payload.get("group_base_t_ms", ()), dtype=np.int32),
        group_low_ms=np.asarray(group_payload.get("group_low_ms", ()), dtype=np.int32),
        group_high_ms=np.asarray(group_payload.get("group_high_ms", ()), dtype=np.int32),
        note_group_idx=np.asarray(group_payload.get("note_group_idx", ()), dtype=np.int32),
        ref_ft=np.asarray(ref_ft, dtype=np.float32),
        ref_ff=np.asarray(ref_ff, dtype=np.float32),
    )

    _save_frontier_payload_to_disk(cache_key, payload, group_payload=group_payload)
    with _frontier_payload_cache_lock:
        cached = _frontier_payload_cache.get(cache_key)
        if isinstance(cached, TimelineFrontierGridPayload):
            _frontier_payload_cache.move_to_end(cache_key)
            return cached, "memory"
        _frontier_payload_cache[cache_key] = payload
        _frontier_payload_cache.move_to_end(cache_key)
        while len(_frontier_payload_cache) > int(_FRONTIER_PAYLOAD_CACHE_MAX):
            _frontier_payload_cache.popitem(last=False)

    return payload, "built"


def _timeline_payload_lookup_context(calc_song: dict, ref_arrays: dict, *, ref_sig: bytes | None = None) -> dict:
    if not isinstance(calc_song, dict):
        raise TypeError("calc_song must be a dict")
    if not isinstance(ref_arrays, dict):
        raise TypeError("ref_arrays must be a dict")

    base_song_key = _song_timing_cache_key(calc_song)
    # Timeline frontier payload depends on song timing + FT/FF axes only.
    # Keep key independent of unrelated ref tables (PP/CM/FM/etc.) so startup
    # prebuild and runtime scoring reuse the same disk artifact.
    _ = ref_sig
    song_key = base_song_key
    song_data = calc_song.get("song_data", {}) or {}
    chart_ts = song_data.get("chart_timestamps", None)
    src = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    timestamps = np.asarray(src, dtype=np.float32)
    total_notes = int(len(timestamps))
    if total_notes > fields.MAX_SONG_NOTES:
        raise ValueError(f"Song has {total_notes} notes, max is {fields.MAX_SONG_NOTES}")

    ref_ft = np.asarray(ref_arrays.get("Fever Time", ()), dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays.get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    return {
        "base_song_key": base_song_key,
        "song_key": song_key,
        "timestamps": timestamps,
        "total_notes": int(total_notes),
        "long_notes": int(calc_song["metadata"].get("Long Notes", 0)),
        "last_note_time": float(calc_song["metadata"].get("Last Note Time", 0)),
        "song_profile_key": _timeline_song_profile_key(calc_song),
        "ref_ft": ref_ft,
        "ref_ff": ref_ff,
        "note_types": song_data.get("note_types", None),
    }


def _timeline_payload_context(
    calc_song: dict,
    ref_arrays: dict,
    *,
    ref_sig: bytes | None = None,
    lookup_ctx: dict | None = None,
    require_cached_group_payload: bool = False,
) -> dict:
    lookup = dict(lookup_ctx or _timeline_payload_lookup_context(calc_song, ref_arrays, ref_sig=ref_sig))
    base_song_key = lookup["base_song_key"]
    total_notes = int(lookup["total_notes"])
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])

    group_payload = _group_cache_get(base_song_key[:-1], expected_n=int(total_notes))
    if group_payload is None:
        disk_group_payload = _load_group_payload_from_frontier_disk(cache_key, expected_n=int(total_notes))
        if isinstance(disk_group_payload, dict):
            _group_cache_put(base_song_key[:-1], disk_group_payload)
            group_payload = disk_group_payload
        else:
            if bool(require_cached_group_payload):
                raise ValueError(
                    "Timeline frontier group payload is missing. Startup cache prebuild must build the "
                    "candidate-independent all-FT/FF timeline frontier before runtime scoring."
                )
            group_payload = _get_or_build_frontier_group_payload(
                base_song_key[:-1],
                timestamps=np.asarray(lookup["timestamps"], dtype=np.float32),
                note_types=lookup.get("note_types", None),
            )
    payload_n = int(group_payload.get("n", 0) or 0)
    if int(payload_n) != int(total_notes):
        raise ValueError("prepare_perfect_timing_envelope produced mismatched note count")
    if total_notes > 0 and int(group_payload.get("group_count", 0) or 0) <= 0:
        raise ValueError("prepare_perfect_timing_envelope produced no chord groups")

    lookup["group_payload"] = group_payload
    return lookup


def timeline_frontier_payload_cache_info(calc_song: dict, ref_arrays: dict) -> TimelineFrontierCacheInfo:
    """
    Return exact-frontier cache status without building group payloads or loading `.npz`.

    Startup prebuild uses this to skip already-built songs cheaply. It still
    parses/hash-checks the chart timing data so the decision uses the exact same
    key that runtime upload will use.
    """
    if not isinstance(calc_song, dict):
        raise TypeError("calc_song must be a dict")
    if not isinstance(ref_arrays, dict):
        raise TypeError("ref_arrays must be a dict")

    base_song_key = _song_timing_cache_key(calc_song)
    song_key = base_song_key
    ref_ft = np.asarray(ref_arrays.get("Fever Time", ()), dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays.get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    cache_key = _frontier_payload_cache_key(song_key, ref_ft, ref_ff)

    cache_source = "missing"
    with _frontier_payload_cache_lock:
        cached = _frontier_payload_cache.get(cache_key)
        if isinstance(cached, TimelineFrontierGridPayload):
            cache_source = "memory"
    disk_path = _frontier_disk_cache_path(cache_key)
    if cache_source == "missing" and disk_path.exists():
        cache_source = "disk"

    song_data = calc_song.get("song_data", {}) or {}
    chart_ts = song_data.get("chart_timestamps", None)
    src = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    return TimelineFrontierCacheInfo(
        cache_key=cache_key,
        disk_path=disk_path,
        cache_source=cache_source,
        song_profile_key=_timeline_song_profile_key(calc_song),
        total_notes=int(len(src)),
        long_notes=int((calc_song.get("metadata", {}) or {}).get("Long Notes", 0) or 0),
    )


def build_or_load_timeline_frontier_payload(calc_song: dict, ref_arrays: dict) -> TimelineFrontierPrewarmResult:
    """
    Build or load the reusable exact frontier payload without touching Taichi fields.

    This is the shared host-side entrypoint for background lookahead and offline
    disk-cache prebuilding, so cache signatures stay identical to runtime scoring.
    """
    t0 = time.perf_counter()
    lookup = _timeline_payload_lookup_context(calc_song, ref_arrays)
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])
    payload, cache_source = _get_cached_frontier_payload_with_source(
        lookup["song_key"],
        ref_ft=lookup["ref_ft"],
        ref_ff=lookup["ref_ff"],
    )
    if payload is None:
        ctx = _timeline_payload_context(calc_song, ref_arrays, lookup_ctx=lookup)
        payload, cache_source = _get_or_build_frontier_payload_with_source(
            ctx["song_key"],
            song_slot=0,
            total_notes=int(ctx["total_notes"]),
            long_notes=int(ctx["long_notes"]),
            last_note_time=float(ctx["last_note_time"]),
            song_profile_key=ctx["song_profile_key"],
            group_payload=ctx["group_payload"],
            ref_ft=ctx["ref_ft"],
            ref_ff=ctx["ref_ff"],
        )
    return TimelineFrontierPrewarmResult(
        payload=payload,
        cache_key=cache_key,
        disk_path=_frontier_disk_cache_path(cache_key),
        cache_source=cache_source,
        elapsed_ms=float((time.perf_counter() - t0) * 1000.0),
        song_profile_key=lookup["song_profile_key"],
        total_notes=int(lookup["total_notes"]),
        long_notes=int(lookup["long_notes"]),
    )


def load_timeline_frontier_payload(calc_song: dict, ref_arrays: dict) -> TimelineFrontierPrewarmResult:
    """Load the required timeline-frontier cache artifact without building it."""
    t0 = time.perf_counter()
    lookup = _timeline_payload_lookup_context(calc_song, ref_arrays)
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])
    payload, cache_source = _get_cached_frontier_payload_with_source(
        lookup["song_key"],
        ref_ft=lookup["ref_ft"],
        ref_ff=lookup["ref_ff"],
    )
    if payload is None:
        raise MissingFrontierCacheError(
            "Timeline frontier payload is missing. Startup cache prebuild must build the "
            "candidate-independent all-FT/FF timeline frontier before runtime scoring."
        )
    return TimelineFrontierPrewarmResult(
        payload=payload,
        cache_key=cache_key,
        disk_path=_frontier_disk_cache_path(cache_key),
        cache_source=cache_source,
        elapsed_ms=float((time.perf_counter() - t0) * 1000.0),
        song_profile_key=lookup["song_profile_key"],
        total_notes=int(lookup["total_notes"]),
        long_notes=int(lookup["long_notes"]),
    )


def precompute_timeline_gpu(
    calc_song: dict,
    ref_arrays: dict,
    song_slot: int = 0,
    *,
    prebuilt_frontier: "TimelineFrontierPrewarmResult | None" = None,
) -> None:
    """
    Upload the startup-built exact timeline frontier for one song slot.

    Runtime is cache-consumer only: the candidate-independent startup cache owns
    group-envelope construction and frontier building. The live GPU path uploads
    only the per-slot fields read by GA scoring kernels.

    Args:
        calc_song: Song calculation context with timestamps/metadata
        ref_arrays: Reference lookup arrays (must include Fever Time/Fill Rate)
        song_slot: Grid slot to write to (0-7, default 0 for single-song mode)
        prebuilt_frontier: Optional already-resolved frontier payload to upload BY VALUE.
            Production runtime leaves this None so the path stays cache-consumer-only and
            fails loud via load_timeline_frontier_payload() when the startup cache is missing.
            The synthetic GPU warmup (which is not part of the song queue and builds its own
            disposable payload) passes it in so the upload never re-reads the clearable
            in-memory frontier cache between build and upload.

    After calling this, the grid fields for song_slot are populated:
    - grid_count_body_fever[song_slot, ft, ff]
    - grid_count_body_normal[song_slot, ft, ff]
    - grid_head_len[song_slot, ft, ff]
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

    lookup = _timeline_payload_lookup_context(calc_song, ref_arrays, ref_sig=ref_sig)
    # Check if we already computed for this song+ref set.
    song_key = lookup["song_key"]
    if _gpu_timeline_song_id_by_slot[song_slot] == song_key:
        return  # Already computed
    frontier_result = (
        prebuilt_frontier
        if prebuilt_frontier is not None
        else load_timeline_frontier_payload(calc_song, ref_arrays)
    )
    total_notes = int(lookup["total_notes"])
    long_notes = int(lookup["long_notes"])

    # Sync before timing
    _maybe_sync(for_timing=True)
    _t0 = time.perf_counter()

    song_slot_i = int(song_slot)
    t_frontier = time.perf_counter()
    frontier_payload = frontier_result.payload
    frontier_cache_source = frontier_result.cache_source
    if int(frontier_payload.grid_frontier_count.shape[1]) < TOTAL_ROWS + 1 or int(
        frontier_payload.grid_frontier_count.shape[2]
    ) < TOTAL_ROWS + 1:
        raise ValueError(
            "Timeline frontier payload is incomplete. Startup cache prebuild must build the "
            "candidate-independent all-FT/FF timeline frontier before runtime scoring."
        )

    cache_phase = "frontier_payload_cache_hit"
    if str(frontier_cache_source) == "memory":
        cache_phase = "frontier_payload_cache_hit_memory"
    elif str(frontier_cache_source) == "disk":
        cache_phase = "frontier_payload_cache_hit_disk"
    _emit_timeline_phase(
        phase=cache_phase,
        start=t_frontier,
        calc_song=calc_song,
        song_slot=song_slot_i,
        cache_source=str(frontier_cache_source),
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        frontier_pool_used=int(frontier_payload.frontier_pool_used),
    )
    t_merge = time.perf_counter()
    payload_slot_i = 0
    upload_bytes = _upload_timeline_frontier_payload_slot(
        frontier_payload,
        song_slot_i,
        source_slot_i=payload_slot_i,
    )
    _emit_timeline_phase(
        phase="frontier_field_upload",
        start=t_merge,
        calc_song=calc_song,
        song_slot=song_slot_i,
        upload_bytes=int(upload_bytes),
        frontier_count=int(
            np.count_nonzero(np.asarray(frontier_payload.grid_frontier_count[payload_slot_i], dtype=np.int32))
        ),
        frontier_variants=int(np.sum(np.asarray(frontier_payload.grid_frontier_count[payload_slot_i], dtype=np.int64))),
    )
    _maybe_sync(for_timing=True)
    _t1 = time.perf_counter()

    _gpu_timeline_song_id_by_slot[song_slot] = song_key

    if _SYNC_FOR_TIMING or _FORCE_SYNC:
        print(f"[GPU Timeline] Computed 161×161 grid in {(_t1 - _t0) * 1000:.1f}ms")


def precompute_timeline_gpu_for_warmup(calc_song: dict, ref_arrays: dict, song_slot: int = 0) -> None:
    """
    Warmup-only entrypoint for synthetic charts.

    Production scoring must consume the startup-built frontier cache via
    precompute_timeline_gpu(). GPU JIT warmups use synthetic charts that are not
    part of the song queue, so they explicitly build their own disposable payload
    and hand it to the upload BY VALUE.

    Robustness: ensure GPU/fields are ready first (so any cold-init Vulkan reset, which
    clears the in-memory frontier cache via reset_timeline_state(), happens before the
    build), then build the disposable payload and pass it straight to the upload. Carrying
    the payload by value means a cache clear/eviction between build and upload can no longer
    raise MissingFrontierCacheError -- the exact failure this entrypoint exists to prevent.
    """
    ensure_ready(ref_arrays)
    frontier_result = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    precompute_timeline_gpu(
        calc_song,
        ref_arrays,
        song_slot=song_slot,
        prebuilt_frontier=frontier_result,
    )


def reset_timeline_state() -> None:
    """Reset module-level timeline upload caches after `ti.reset()`."""
    global _gpu_timeline_song_id_by_slot
    global _frontier_group_payload_cache, _frontier_payload_cache
    _gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS
    with _frontier_payload_cache_lock:
        _frontier_group_payload_cache.clear()
        _frontier_payload_cache.clear()
