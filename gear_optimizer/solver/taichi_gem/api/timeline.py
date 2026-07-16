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

from gear_optimizer.core.constants import PATHS, TOTAL_ROWS
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.env_config import ENV as _ENV
from gear_optimizer.core.logic_fingerprint import module_logic_fingerprint
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.utils import timing_envelope_timing_context
from gear_optimizer.solver.timeline_exact_frontier import (
    TimelineFrontierGridPayload,
    _head_mask_coefficients_py,
    build_timeline_frontier_grid_payload,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import (
    _FG_SHARED_FRONTIER_PRODUCER_SOURCES,
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
        "grid_fever_masks_bits",
        "grid_frontier_count",
        "grid_frontier_offset",
        "grid_frontier_body_fever_pool",
        "grid_frontier_body_normal_pool",
        "grid_frontier_masks_bits_pool",
        "grid_frontier_head_coeffs_pool",
        "grid_gap",
        "grid_fever_activations",
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


@ti.kernel
def _upload_timeline_pool_head_coeffs_slot_kernel(
    song_slot: ti.i32,
    n: ti.i32,
    src: ti.types.ndarray(dtype=ti.i16, ndim=2),
):
    for i, coeff in ti.ndrange(n, 4):
        fields.grid_frontier_head_coeffs_pool[song_slot, i, coeff] = src[i, coeff]


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
        coeff_pool = np.ascontiguousarray(
            np.asarray(payload.grid_frontier_head_coeffs_pool[source_slot_i, :pool_used, :], dtype=np.int16)
        )
        upload_bytes += int(coeff_pool.nbytes)
        _upload_timeline_pool_slot_i32_kernel(fields.grid_frontier_body_fever_pool, song_slot_i, pool_used, fever_pool)
        _upload_timeline_pool_slot_i32_kernel(fields.grid_frontier_body_normal_pool, song_slot_i, pool_used, normal_pool)
        _upload_timeline_pool_masks_bits_slot_kernel(song_slot_i, pool_used, mask_pool)
        _upload_timeline_pool_head_coeffs_slot_kernel(song_slot_i, pool_used, coeff_pool)

    return int(upload_bytes)


# ============================================================================
# GPU TIMELINE PRECOMPUTATION (eliminates Numba typeof overhead)
# ============================================================================

_gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS  # Track last song per slot
# Sized to cover the native in-flight prep window (prep_limit tops out around 36):
# prep workers hydrate a song's payload ahead of its GA turn, and the entry must
# survive in this LRU until the owner uploads it. Payloads run ~1-2MB typical.
_FRONTIER_PAYLOAD_CACHE_MAX = 40
_frontier_payload_cache: "OrderedDict[tuple, object]" = OrderedDict()
_frontier_payload_last_access: dict[tuple, float] = {}
_frontier_payload_cache_lock = threading.RLock()
# Bump whenever the base frontier OUTPUT changes in a way the cache key does NOT capture.
# The key (_frontier_payload_cache_key -> song_key) hashes raw song inputs + window settings,
# NOT the grouping/DP logic, so a pure logic change is invisible to it and only the version
# invalidates stale disk payloads. v6: the chord-tied held-tail grouping split (issue #42 /
# PR #45) changed the base frontier for held-tail-chord songs without touching any key input,
# so pre-fix v5 payloads in bin/timeline_frontier_cache/ must not be reused.
# v7: per-cell N_hn/N_hf/Sigma_hn/Sigma_hf grids replaced by the per-VARIANT
# grid_frontier_head_coeffs_pool (the eval kernel needs coefficients for every pool
# row; the per-cell grids were never read on the live GPU path).
# v8: STALE-CACHE INVALIDATION (2026-07-04). The base DP (_build_exact_timeline_frontier_
# from_context) is floor-aware / endpoint-early exact -- a note whose EARLIEST legal hit
# (perfect_floor = chart-20ms, held-tail -40) lands inside the fever window is counted even
# when its nominal chart time falls outside. Pre-existing v7 disk payloads on some machines
# were built by an older DP that omitted that boundary note, and no version moved when the DP
# gained it, so a pure-logic change went invisible to the (input+window)-hashed key. Symptom:
# Bopeebo Easy T5 Vibe persisted base 1,360,389 (nominal ff24) from a stale v7 payload while a
# fresh build of the SAME loadout selects the floor-optimal ff22 -> 1,364,025 (bit-exact to the
# website's live re-solve). Bumping forces a rebuild from the current floor-aware DP. Strictly
# regression-safe: perfect_floor <= chart pointwise, so a rebuilt cell's body_fever only rises
# or stays equal; songs with no endpoint-early boundary note are byte-identical.
# v9: fold a DP-LOGIC FINGERPRINT into the version (Fix 1, 2026-07-04). The base string above is the
# human backstop + semantic history; the appended `+logic-<fp>` is an ast-level digest of the
# timeline DP module (timeline_exact_frontier.py). A change to the DP body (as in the v7->v8 floor-
# aware regression that went invisible) now shifts the fingerprint automatically, so stale disk
# payloads built by the old logic no longer validate against the new code -- killing the silent
# stale-cache bug class rather than relying on someone remembering to bump the string. Docstring/
# comment/whitespace edits do NOT move it (see logic_fingerprint.py). Over-invalidation is safe.
# v9 -> v10: hit-time chord-reachability -- the base activation clock is now capped to the reachable
# value (a wide-window group can no longer claim a late activation a later-indexed overlapping
# sibling, hit first, forecloses), so stale bundles carry a phantom over-extended drain window (and,
# where it captured a note, an over-count). The DP fingerprint over timeline_exact_frontier.py
# already shifts automatically; this backstop bump records the behaviour change.
# v10->v11: BUG-1 judgment-edge inclusivity fix. The base drain searches the Perfect FLOOR envelope
# (build_perfect_floor_envelope_sec), whose early edge shifted +1ms to the engine's exclusive-early
# boundary (-20/-40 -> -19/-39). The historical single-source fingerprint did not include
# timing_envelope.py, so this explicit bump invalidated the stale (1ms-over-generous) membership
# floor. Re-solve to re-persist best_score.
# v11->v12: Base no longer has a body-only large-fill shortcut. Every Base geometry runs through
# the shared lane-aware recurrence with Perfect-only actions. The old shortcut used an activation's
# raw latest Perfect edge instead of the capped input-engine owner and could retain phantom fever
# notes. Base cache identity now fingerprints the complete shared producer, not only this wrapper,
# so a future shared recurrence change cannot silently reuse stale Base payloads.
_FRONTIER_DISK_CACHE_BASE_VERSION = "exact-frontier-v12"
_FG_SCORING_POLICY_SOURCE = Path(__file__).resolve().parents[2] / "scoring" / "fg_policy.py"
# Base persists timing geometry and Perfect-only recurrence output, never Great score valuation.
# Excluding the FG scoring policy keeps a Force-Greats-only score correction from rotating every
# Base frontier cache key. The remaining shared sources are the exact recurrence/geometry producer.
_BASE_SHARED_FRONTIER_PRODUCER_SOURCES = tuple(
    source for source in _FG_SHARED_FRONTIER_PRODUCER_SOURCES if source != _FG_SCORING_POLICY_SOURCE
)
_TIMELINE_DP_SOURCES = (
    Path(__file__).resolve().parents[2] / "timeline_exact_frontier.py",
    *_BASE_SHARED_FRONTIER_PRODUCER_SOURCES,
)
_FRONTIER_DISK_CACHE_VERSION = (
    f"{_FRONTIER_DISK_CACHE_BASE_VERSION}+logic-{module_logic_fingerprint(_TIMELINE_DP_SOURCES)}"
)
# Exact cache compatibility is deliberately explicit and non-transitive. A predecessor is listed
# only after a byte gate proves its persisted payload identical to the current producer. Issue #161
# proved the 1f182e5b89af, 4c69b48f08bb, and 9dfe907e66fb lineages diverge; they must rebuild.
_EXACT_COMPATIBLE_TIMELINE_PREDECESSOR_VERSIONS: dict[str, tuple[str, ...]] = {
    # Compact session pruning and exact-signature trace witness selection live in shared source
    # files but run only after a frontier has been loaded. They cannot reach the Perfect-only
    # recurrence or persisted Base arrays, so retain only the byte-proven v12 lineage.
    "exact-frontier-v12+logic-61d6f59cade0": (
        "exact-frontier-v12+logic-12c8db234d06",
        "exact-frontier-v12+logic-e0b0e8ef6411",
    ),
    # FG trace-materialization host-path batching in the shared producer sources: identical
    # predicates hoisted into vectorized precomputes (fill_crossing witness scheduler), two
    # response_builder helpers routed through their existing numba twins, three zero-reference
    # interval helpers deleted. The Perfect-only recurrence and every persisted Base payload
    # member are unchanged (byte-identical 132-trace materialization oracle); ratify only that
    # proven predecessor.
    "exact-frontier-v12+logic-12c8db234d06": (
        "exact-frontier-v12+logic-e0b0e8ef6411",
    ),
}


def timeline_frontier_compatible_cache_versions() -> tuple[str, ...]:
    current = str(_FRONTIER_DISK_CACHE_VERSION)
    return (current, *_EXACT_COMPATIBLE_TIMELINE_PREDECESSOR_VERSIONS.get(current, ()))


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
    return Path(PATHS.bin_path("timeline_frontier_cache"))


def _frontier_disk_cache_path(cache_key: tuple) -> Path:
    digest = hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()
    return _frontier_disk_cache_dir() / f"{digest}.npz"


def _live_frontier_disk_cache_path(cache_key: tuple) -> Path | None:
    path = _frontier_disk_cache_path(cache_key)
    if path.exists():
        return path
    if cache_key and str(cache_key[0]) == str(_FRONTIER_DISK_CACHE_VERSION):
        for predecessor in timeline_frontier_compatible_cache_versions()[1:]:
            predecessor_path = _frontier_disk_cache_path((predecessor, *cache_key[1:]))
            if predecessor_path.exists():
                return predecessor_path
    return None


def _load_frontier_payload_from_disk(cache_key: tuple) -> TimelineFrontierGridPayload | None:
    path = _live_frontier_disk_cache_path(cache_key)
    if path is None:
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version not in timeline_frontier_compatible_cache_versions():
                return None
            grid_count_body_fever = np.asarray(data["grid_count_body_fever"], dtype=np.int32)
            grid_count_body_normal = np.asarray(data["grid_count_body_normal"], dtype=np.int32)
            grid_head_len = np.asarray(data["grid_head_len"], dtype=np.int8)
            grid_fever_masks_bits = np.asarray(data["grid_fever_masks_bits"], dtype=np.uint32)
            grid_frontier_count = np.asarray(data["grid_frontier_count"], dtype=np.int32)
            grid_frontier_offset = np.asarray(data["grid_frontier_offset"], dtype=np.int32)
            grid_frontier_body_fever_pool = np.asarray(data["grid_frontier_body_fever_pool"], dtype=np.int32)
            grid_frontier_body_normal_pool = np.asarray(data["grid_frontier_body_normal_pool"], dtype=np.int32)
            grid_frontier_masks_bits_pool = np.asarray(data["grid_frontier_masks_bits_pool"], dtype=np.uint32)
            grid_frontier_head_coeffs_pool = np.asarray(data["grid_frontier_head_coeffs_pool"], dtype=np.int16)
            grid_gap = np.asarray(data["grid_gap"], dtype=np.int32)
            grid_fever_activations = np.asarray(data["grid_fever_activations"], dtype=np.int32)

            # Compact on-disk format stores a single source slot; runtime upload remaps it.
            if grid_count_body_fever.ndim == 2:
                grid_count_body_fever = np.expand_dims(grid_count_body_fever, axis=0)
            if grid_count_body_normal.ndim == 2:
                grid_count_body_normal = np.expand_dims(grid_count_body_normal, axis=0)
            if grid_head_len.ndim == 2:
                grid_head_len = np.expand_dims(grid_head_len, axis=0)
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
            if grid_frontier_head_coeffs_pool.ndim == 2:
                grid_frontier_head_coeffs_pool = np.expand_dims(grid_frontier_head_coeffs_pool, axis=0)
            if grid_gap.ndim == 2:
                grid_gap = np.expand_dims(grid_gap, axis=0)
            if grid_fever_activations.ndim == 2:
                grid_fever_activations = np.expand_dims(grid_fever_activations, axis=0)
            payload = TimelineFrontierGridPayload(
                grid_count_body_fever=grid_count_body_fever,
                grid_count_body_normal=grid_count_body_normal,
                grid_head_len=grid_head_len,
                grid_fever_masks_bits=grid_fever_masks_bits,
                grid_frontier_count=grid_frontier_count,
                grid_frontier_offset=grid_frontier_offset,
                grid_frontier_body_fever_pool=grid_frontier_body_fever_pool,
                grid_frontier_body_normal_pool=grid_frontier_body_normal_pool,
                grid_frontier_masks_bits_pool=grid_frontier_masks_bits_pool,
                grid_frontier_head_coeffs_pool=grid_frontier_head_coeffs_pool,
                grid_gap=grid_gap,
                grid_fever_activations=grid_fever_activations,
                frontier_pool_used=int(data["frontier_pool_used"].item()),
            )
            return payload
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
            if version not in timeline_frontier_compatible_cache_versions():
                return False
            pool_used = int(np.asarray(data["frontier_pool_used"]).item())
            if pool_used < 0:
                return False
            for name in (
                "grid_count_body_fever",
                "grid_count_body_normal",
                "grid_head_len",
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
            if tuple(np.asarray(data["grid_frontier_head_coeffs_pool"]).shape) != (pool_used, 4):
                return False
            frontier_count = np.asarray(data["grid_frontier_count"], dtype=np.int64)
            frontier_offset = np.asarray(data["grid_frontier_offset"], dtype=np.int64)
            if bool(np.any(frontier_count < 0)) or bool(np.any(frontier_offset < 0)):
                return False
            if bool(np.any(frontier_offset + frontier_count > pool_used)):
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
    moment = time.monotonic()
    with _frontier_payload_cache_lock:
        cached = _frontier_payload_cache.get(cache_key)
        if isinstance(cached, TimelineFrontierGridPayload):
            _frontier_payload_cache.move_to_end(cache_key)
            _frontier_payload_last_access[cache_key] = moment
            return cached, "memory"

    cached = _load_frontier_payload_from_disk(cache_key)
    if isinstance(cached, TimelineFrontierGridPayload):
        moment = time.monotonic()
        with _frontier_payload_cache_lock:
            _frontier_payload_cache[cache_key] = cached
            _frontier_payload_cache.move_to_end(cache_key)
            _frontier_payload_last_access[cache_key] = moment
            while len(_frontier_payload_cache) > int(_FRONTIER_PAYLOAD_CACHE_MAX):
                stale_key, _stale_value = _frontier_payload_cache.popitem(last=False)
                _frontier_payload_last_access.pop(stale_key, None)
        return cached, "disk"
    return None, "missing"


def _save_frontier_payload_to_disk(
    cache_key: tuple,
    payload: TimelineFrontierGridPayload,
) -> None:
    path = _frontier_disk_cache_path(cache_key)
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz")
        source_slot_i = 0
        pool_used = max(0, int(payload.frontier_pool_used))
        np.savez_compressed(
            tmp,
            version=np.asarray(_FRONTIER_DISK_CACHE_VERSION),
            frontier_pool_used=np.asarray(pool_used, dtype=np.int32),
            grid_count_body_fever=np.asarray(payload.grid_count_body_fever[source_slot_i], dtype=np.int32),
            grid_count_body_normal=np.asarray(payload.grid_count_body_normal[source_slot_i], dtype=np.int32),
            grid_head_len=np.asarray(payload.grid_head_len[source_slot_i], dtype=np.int8),
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
            grid_frontier_head_coeffs_pool=np.asarray(
                payload.grid_frontier_head_coeffs_pool[source_slot_i, :pool_used, :], dtype=np.int16
            ),
            grid_gap=np.asarray(payload.grid_gap[source_slot_i], dtype=np.int32),
            grid_fever_activations=np.asarray(payload.grid_fever_activations[source_slot_i], dtype=np.int32),
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
    if isinstance(cached, tuple) and len(cached) == 12:
        return cached
    chart_ts = song_data.get("chart_timestamps", None)
    timestamps = chart_ts if chart_ts is not None else song_data.get("timestamps", ())
    # The physical input engine consumes chart order and lane-local matcher order. Hash the exact
    # aligned arrays in producer order; sorting or omitting lanes can alias charts whose abstract
    # timestamp/type sets match but whose legal fever surfaces differ.
    ts_arr = np.asarray(timestamps, dtype=np.float32).reshape(-1)
    n_notes = int(ts_arr.shape[0])
    ts_sig = array_sig16(np.ascontiguousarray(ts_arr))
    if _timeline_calc_song_is_zero_ms(calc_song):
        # Fixed chart-time fever membership depends on timestamps, long-note count, and the
        # FT/FF axes only. Note type, lane, and Perfect-window geometry are not inputs to the
        # zero_ms singleton and must not become accidental requirements of that cheaper model.
        nt_sig = b"zero_ms"
        lane_sig = b"zero_ms"
    else:
        nt_raw = song_data.get("note_types")
        if nt_raw is None or len(nt_raw) != n_notes:
            raise ValueError("timeline frontier requires one chart note type per note")
        nt_arr = np.asarray(nt_raw, dtype=np.int16).reshape(-1)
        lanes_raw = song_data.get("lanes")
        if lanes_raw is None or len(lanes_raw) != n_notes:
            raise ValueError("timeline frontier requires one chart lane per note")
        lane_arr = np.asarray(lanes_raw, dtype=np.int32).reshape(-1)
        nt_sig = array_sig16(np.ascontiguousarray(nt_arr))
        lane_sig = array_sig16(np.ascontiguousarray(lane_arr))
    key = (
        str(meta.get("Song Name", "")),
        str(meta.get("Difficulty", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        bytes(ts_sig),
        bytes(nt_sig),
        bytes(lane_sig),
    ) + timing_envelope_timing_context(calc_song)
    # Cache on the calc_song dict to avoid repeated full-array hashing when the
    # same song is revisited and precompute_timeline_gpu() hits the slot cache.
    calc_song["_gpu_timing_cache_key_frontier"] = key
    return key


def _get_or_build_frontier_payload_with_source(
    song_key: tuple,
    *,
    song_slot: int,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    song_profile_key: str | None = None,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
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
        timestamps=np.asarray(timestamps, dtype=np.float32),
        perfect_candidate_timestamps=np.asarray(perfect_candidate_timestamps, dtype=np.float32),
        perfect_floor_timestamps=np.asarray(perfect_floor_timestamps, dtype=np.float32),
        lanes=np.asarray(lanes, dtype=np.int32),
        ref_ft=np.asarray(ref_ft, dtype=np.float32),
        ref_ff=np.asarray(ref_ff, dtype=np.float32),
    )

    _save_frontier_payload_to_disk(cache_key, payload)
    moment = time.monotonic()
    with _frontier_payload_cache_lock:
        cached = _frontier_payload_cache.get(cache_key)
        if isinstance(cached, TimelineFrontierGridPayload):
            _frontier_payload_cache.move_to_end(cache_key)
            _frontier_payload_last_access[cache_key] = moment
            return cached, "memory"
        _frontier_payload_cache[cache_key] = payload
        _frontier_payload_cache.move_to_end(cache_key)
        _frontier_payload_last_access[cache_key] = moment
        while len(_frontier_payload_cache) > int(_FRONTIER_PAYLOAD_CACHE_MAX):
            stale_key, _stale_value = _frontier_payload_cache.popitem(last=False)
            _frontier_payload_last_access.pop(stale_key, None)

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
    perfect_candidates = song_data.get("fg_perfect_candidate_timestamps")
    perfect_floor = song_data.get("fg_perfect_floor_timestamps")
    lanes = song_data.get("lanes")
    if _timeline_calc_song_is_zero_ms(calc_song):
        # The zero_ms payload is a deterministic singleton built from fixed hit timestamps.
        # These physical Perfect-window inputs are intentionally absent and never consumed.
        perfect_candidates_arr = np.empty(0, dtype=np.float32)
        perfect_floor_arr = np.empty(0, dtype=np.float32)
        lanes_arr = np.empty(0, dtype=np.int32)
    else:
        if perfect_candidates is None or len(perfect_candidates) != total_notes:
            raise ValueError("timeline frontier requires the canonical Perfect candidate envelope")
        if perfect_floor is None or len(perfect_floor) != total_notes:
            raise ValueError("timeline frontier requires the canonical Perfect floor envelope")
        if lanes is None or len(lanes) != total_notes:
            raise ValueError("timeline frontier requires one chart lane per note")
        perfect_candidates_arr = np.asarray(perfect_candidates, dtype=np.float32)
        perfect_floor_arr = np.asarray(perfect_floor, dtype=np.float32)
        lanes_arr = np.asarray(lanes, dtype=np.int32)
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
        "perfect_candidates": perfect_candidates_arr,
        "perfect_floor": perfect_floor_arr,
        "lanes": lanes_arr,
    }


def _prepare_timeline_frontier_calc_song(calc_song: dict, *, timing_mode: str | None = None) -> str:
    """Make the frontier input canonical before any key, cache, or scorer can consume it."""

    if not isinstance(calc_song, dict):
        raise TypeError("calc_song must be a dict")
    metadata = calc_song.get("metadata") if isinstance(calc_song.get("metadata"), dict) else {}
    normalized = str(
        timing_mode
        if timing_mode is not None
        else metadata.get("TimingEnvelopeMode") or metadata.get("Timing Mode") or "perfect_window"
    ).strip().lower()
    if normalized not in {"perfect_window", "zero_ms"}:
        raise ValueError(f"unknown timeline frontier timing mode {timing_mode!r}")

    existing_mode = str(metadata.get("TimingEnvelopeMode") or "").strip().lower()

    # A custom fixed-timing input may carry a nonzero baseline that cannot be reconstructed from
    # its hash. Preserve an already-canonical zero-ms object; raw zero-ms inputs are materialized.
    if (
        normalized == "zero_ms"
        and metadata.get("TimingEnvelopeApplied") is True
        and existing_mode == "zero_ms"
    ):
        return normalized

    if existing_mode != normalized:
        calc_song.pop("_gpu_timing_cache_key_frontier", None)
    prepared = apply_timing_envelope(calc_song, mode=normalized)
    if prepared is None:
        raise ValueError("timeline frontier requires chart timestamps")
    return normalized


def timeline_frontier_payload_cache_info(
    calc_song: dict,
    ref_arrays: dict,
    *,
    timing_mode: str | None = None,
) -> TimelineFrontierCacheInfo:
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

    _prepare_timeline_frontier_calc_song(calc_song, timing_mode=timing_mode)

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
    # Report the file that actually serves this key: the current-version path when it
    # exists, else the ratified predecessor's. Returning the (possibly nonexistent)
    # current-version path here made the prebuild manifest unable to validate/record
    # predecessor hits, so startup re-verified those songs every run instead of taking
    # the manifest fast path.
    live_path = _live_frontier_disk_cache_path(cache_key)
    disk_path = live_path if live_path is not None else _frontier_disk_cache_path(cache_key)
    if cache_source == "missing" and live_path is not None:
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


def _timeline_calc_song_is_zero_ms(calc_song: dict) -> bool:
    """True when a calc_song was prepared for the fixed chart-time (zero_ms) timing model."""
    metadata = calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}
    return str((metadata or {}).get("TimingEnvelopeMode", "") or "").strip().lower() == "zero_ms"


def _build_zero_ms_timeline_payload(calc_song: dict, ref_arrays: dict) -> TimelineFrontierGridPayload:
    """Build the exact singleton chart-time surface for every FT/FF cell.

    zero_ms is fixed timing (every hit at its chart timestamp), so each (Fever Time, Fever Fill)
    cell has exactly ONE deterministic fever surface -- there is no Perfect-window candidate
    frontier to search. This is the cheap "partial" build: it reuses the same per-cell fever kernel
    (``calculate_fever_timeline_indices``) the fixed-timing base scorer uses, so the payload scores
    bit-identically to ``score_stats_fixed_timing_exact`` while costing a fraction of the full
    carry-envelope DP that ``build_timeline_frontier_grid_payload`` runs for perfect_window. It is
    the subset of the shared representation the user's thin gate promotes to a full frontier only
    when perfect_window is actually requested.
    """
    metadata = calc_song.get("metadata", {}) or {}
    if str(metadata.get("TimingEnvelopeMode", "") or "").strip().lower() != "zero_ms":
        raise ValueError("fixed chart-time timeline payload requires TimingEnvelopeMode='zero_ms'")

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = np.asarray(
        song_data.get("fg_timestamps", song_data.get("chart_timestamps", song_data.get("timestamps", ()))),
        dtype=np.float32,
    ).reshape(-1)
    total_notes = int(timestamps.shape[0])
    if total_notes > 1 and bool(np.any(np.diff(timestamps) < np.float32(0.0))):
        raise ValueError("zero_ms chart timestamps must be non-decreasing")

    ref_ft = np.asarray(ref_arrays.get("Fever Time", ()), dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays.get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    grid_size = TOTAL_ROWS + 1
    if ref_ft.shape != (grid_size,) or ref_ff.shape != (grid_size,):
        raise ValueError(f"zero_ms timeline axes must both have shape ({grid_size},)")

    shape = (1, grid_size, grid_size)
    grid_count_body_fever = np.zeros(shape, dtype=np.int32)
    grid_count_body_normal = np.zeros(shape, dtype=np.int32)
    grid_head_len = np.full(shape, min(total_notes, 100), dtype=np.int8)
    grid_fever_masks_bits = np.zeros((*shape, 4), dtype=np.uint32)
    grid_frontier_count = np.ones(shape, dtype=np.int32)
    grid_frontier_offset = np.zeros(shape, dtype=np.int32)
    grid_gap = np.zeros(shape, dtype=np.int32)
    grid_fever_activations = np.zeros(shape, dtype=np.int32)

    pool_cap = int(fields.MAX_TIMELINE_FRONTIER_SURFACES)
    body_fever_pool = np.zeros((1, pool_cap), dtype=np.int32)
    body_normal_pool = np.zeros((1, pool_cap), dtype=np.int32)
    masks_pool = np.zeros((1, pool_cap, 4), dtype=np.uint32)
    head_coeffs_pool = np.zeros((1, pool_cap, 4), dtype=np.int16)
    long_notes = int(metadata.get("Long Notes", 0) or 0)
    last_note_time = float(metadata.get("Last Note Time", float(timestamps[-1]) if total_notes else 0.0) or 0.0)
    pool_by_surface: dict[tuple[int, int, tuple[int, int, int, int], int, int], int] = {}

    from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_surface_grid

    last_fever_end = np.zeros((grid_size, grid_size), dtype=np.int32)
    calculate_fever_timeline_surface_grid(
        timestamps,
        total_notes,
        ref_ft,
        ref_ff,
        long_notes,
        last_note_time,
        grid_count_body_fever[0],
        grid_count_body_normal[0],
        grid_fever_masks_bits[0],
        grid_fever_activations[0],
        last_fever_end,
    )
    grid_gap[0] = int(total_notes) - last_fever_end

    for ft_idx in range(grid_size):
        for ff_idx in range(grid_size):
            body_fever = int(grid_count_body_fever[0, ft_idx, ff_idx])
            body_normal = int(grid_count_body_normal[0, ft_idx, ff_idx])
            word_tuple = tuple(int(word) for word in grid_fever_masks_bits[0, ft_idx, ff_idx])
            activations = int(grid_fever_activations[0, ft_idx, ff_idx])
            gap = int(grid_gap[0, ft_idx, ff_idx])
            surface = (int(body_fever), int(body_normal), word_tuple, int(activations), gap)
            pool_idx = pool_by_surface.get(surface)
            if pool_idx is None:
                pool_idx = len(pool_by_surface)
                if pool_idx >= pool_cap:
                    raise RuntimeError(f"zero_ms timeline surface pool overflow: cap={pool_cap}")
                pool_by_surface[surface] = pool_idx
                body_fever_pool[0, pool_idx] = int(body_fever)
                body_normal_pool[0, pool_idx] = int(body_normal)
                masks_pool[0, pool_idx, :] = np.asarray(word_tuple, dtype=np.uint32)
                head_coeffs_pool[0, pool_idx, :] = np.asarray(
                    _head_mask_coefficients_py(*word_tuple, head_len=min(total_notes, 100)),
                    dtype=np.int16,
                )
            grid_frontier_offset[0, ft_idx, ff_idx] = int(pool_idx)

    return TimelineFrontierGridPayload(
        grid_count_body_fever=grid_count_body_fever,
        grid_count_body_normal=grid_count_body_normal,
        grid_head_len=grid_head_len,
        grid_fever_masks_bits=grid_fever_masks_bits,
        grid_frontier_count=grid_frontier_count,
        grid_frontier_offset=grid_frontier_offset,
        grid_frontier_body_fever_pool=body_fever_pool,
        grid_frontier_body_normal_pool=body_normal_pool,
        grid_frontier_masks_bits_pool=masks_pool,
        grid_frontier_head_coeffs_pool=head_coeffs_pool,
        grid_gap=grid_gap,
        grid_fever_activations=grid_fever_activations,
        frontier_pool_used=len(pool_by_surface),
    )


def _zero_ms_timeline_result(calc_song: dict, ref_arrays: dict) -> TimelineFrontierPrewarmResult:
    """Wrap the cheap zero_ms singleton payload as a prewarm result (in-memory, never persisted).

    zero_ms is the fixed chart-time subset of the shared frontier representation: it is built on
    demand and NOT written to the perfect_window disk cache, so a strict-zero_ms deployment never
    pays -- or stores -- the full candidate-frontier build. cache_source ``"fixed_zero_ms"`` marks
    the provenance for telemetry.
    """
    t0 = time.perf_counter()
    lookup = _timeline_payload_lookup_context(calc_song, ref_arrays)
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])
    payload = _build_zero_ms_timeline_payload(calc_song, ref_arrays)
    return TimelineFrontierPrewarmResult(
        payload=payload,
        cache_key=cache_key,
        disk_path=_frontier_disk_cache_path(cache_key),
        cache_source="fixed_zero_ms",
        elapsed_ms=float((time.perf_counter() - t0) * 1000.0),
        song_profile_key=lookup["song_profile_key"],
        total_notes=int(lookup["total_notes"]),
        long_notes=int(lookup["long_notes"]),
    )


def build_or_load_timeline_frontier_payload(
    calc_song: dict,
    ref_arrays: dict,
    *,
    timing_mode: str | None = None,
) -> TimelineFrontierPrewarmResult:
    """
    Build or load the reusable exact frontier payload without touching Taichi fields.

    This is the shared host-side entrypoint for background lookahead and offline
    disk-cache prebuilding, so cache signatures stay identical to runtime scoring.
    """
    resolved_timing_mode = _prepare_timeline_frontier_calc_song(calc_song, timing_mode=timing_mode)
    if resolved_timing_mode == "zero_ms":
        # zero_ms is fixed timing: serve the cheap chart-time singleton (the "partial" build) and
        # never touch the perfect_window candidate-frontier build or its disk cache.
        return _zero_ms_timeline_result(calc_song, ref_arrays)
    t0 = time.perf_counter()
    lookup = _timeline_payload_lookup_context(calc_song, ref_arrays)
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])
    payload, cache_source = _get_cached_frontier_payload_with_source(
        lookup["song_key"],
        ref_ft=lookup["ref_ft"],
        ref_ff=lookup["ref_ff"],
    )
    if payload is None:
        ctx = lookup
        payload, cache_source = _get_or_build_frontier_payload_with_source(
            ctx["song_key"],
            song_slot=0,
            total_notes=int(ctx["total_notes"]),
            long_notes=int(ctx["long_notes"]),
            last_note_time=float(ctx["last_note_time"]),
            song_profile_key=ctx["song_profile_key"],
            timestamps=ctx["timestamps"],
            perfect_candidate_timestamps=ctx["perfect_candidates"],
            perfect_floor_timestamps=ctx["perfect_floor"],
            lanes=ctx["lanes"],
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


def load_timeline_frontier_payload(
    calc_song: dict,
    ref_arrays: dict,
    *,
    timing_mode: str | None = None,
) -> TimelineFrontierPrewarmResult:
    """Load the timeline frontier, building and persisting a live cache miss."""
    resolved_timing_mode = _prepare_timeline_frontier_calc_song(calc_song, timing_mode=timing_mode)
    if resolved_timing_mode == "zero_ms":
        # zero_ms serves the cheap chart-time singleton on demand -- it is never persisted to the
        # perfect_window disk cache, so probing it here would be a miss anyway; build directly.
        return _zero_ms_timeline_result(calc_song, ref_arrays)
    t0 = time.perf_counter()
    lookup = _timeline_payload_lookup_context(calc_song, ref_arrays)
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])
    payload, cache_source = _get_cached_frontier_payload_with_source(
        lookup["song_key"],
        ref_ft=lookup["ref_ft"],
        ref_ff=lookup["ref_ff"],
    )
    if payload is None:
        return build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
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
            Production runtime leaves this None so load_timeline_frontier_payload() can reuse or
            build the canonical persistent cache artifact.
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
        else (
            build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
            if _ENV.serving_api
            else load_timeline_frontier_payload(calc_song, ref_arrays)
        )
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

    Production scoring consumes the canonical frontier cache via precompute_timeline_gpu(),
    building a persistent miss if deployment prebuild did not cover it. GPU JIT warmups use synthetic charts that are not
    part of the song queue, so they explicitly build their own disposable payload
    and hand it to the upload BY VALUE.

    Robustness: ensure GPU/fields are ready first (so any cold-init Vulkan reset, which
    clears the in-memory frontier cache via reset_timeline_state(), happens before the
    build), then build the disposable payload and pass it straight to the upload. Carrying
    the payload by value means a cache clear/eviction between build and upload can no longer
    lose the cache artifact between build and upload.
    """
    ensure_ready(ref_arrays)
    started = time.perf_counter()
    lookup = _timeline_payload_lookup_context(calc_song, ref_arrays)
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])
    payload = build_timeline_frontier_grid_payload(
        song_slot=0,
        total_notes=int(lookup["total_notes"]),
        long_notes=int(lookup["long_notes"]),
        last_note_time=float(lookup["last_note_time"]),
        song_key=lookup["song_profile_key"],
        timestamps=np.asarray(lookup["timestamps"], dtype=np.float32),
        perfect_candidate_timestamps=np.asarray(lookup["perfect_candidates"], dtype=np.float32),
        perfect_floor_timestamps=np.asarray(lookup["perfect_floor"], dtype=np.float32),
        lanes=np.asarray(lookup["lanes"], dtype=np.int32),
        ref_ft=np.asarray(lookup["ref_ft"], dtype=np.float32),
        ref_ff=np.asarray(lookup["ref_ff"], dtype=np.float32),
    )
    frontier_result = TimelineFrontierPrewarmResult(
        payload=payload,
        cache_key=cache_key,
        disk_path=_frontier_disk_cache_path(cache_key),
        cache_source="warmup_disposable",
        elapsed_ms=float((time.perf_counter() - started) * 1000.0),
        song_profile_key=lookup["song_profile_key"],
        total_notes=int(lookup["total_notes"]),
        long_notes=int(lookup["long_notes"]),
    )
    precompute_timeline_gpu(
        calc_song,
        ref_arrays,
        song_slot=song_slot,
        prebuilt_frontier=frontier_result,
    )


def reset_timeline_state() -> None:
    """Reset module-level timeline upload caches after `ti.reset()`."""
    global _gpu_timeline_song_id_by_slot
    global _frontier_payload_cache
    _gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS
    with _frontier_payload_cache_lock:
        _frontier_payload_cache.clear()
        _frontier_payload_last_access.clear()
