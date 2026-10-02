"""
API Timeline - cached exact frontier load and GPU grid upload.

Startup builds the candidate-independent timeline frontier cache; runtime uploads
the cached grid/frontier payload for the active song slot.
"""

import io
import time
from pathlib import Path
import logging
import numpy as np
import taichi as ti

from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.logic_fingerprint import module_logic_fingerprint
from gear_optimizer.settings import paths
from gear_optimizer.solver.timeline_exact_frontier import (
    TimelineFrontierGridPayload,
    _head_mask_coefficients_py,
    build_timeline_frontier_grid_payload,
)
from gear_optimizer.solver.frontier_cache import (
    FrontierCache,
    FrontierCacheInfo,
    FrontierCacheLoad,
    MemoryLru,
    content_addressed_path,
    write_atomically,
)
from gear_optimizer.solver.frontier_cache_scope import scoped_frontier_cache_dir
from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import (
    _FG_SHARED_FRONTIER_PRODUCER_SOURCES,
)
from ..fields import (
    MAX_SONG_SLOTS,
)
from .. import fields
from ..kernel_loader import get_kernels

from ..runtime import on_hard_reset
from .ga_eval_cache import reset_ga_evaluation_cache
from .initialization import ensure_ready


logger = logging.getLogger(__name__)

# Get appropriate kernels for current platform (Metal-safe on macOS)
kernels = get_kernels()

# The payload arrays in file order: (name, dtype, rank in the file). A file holds the one song slot of a payload,
# whose arrays carry a leading slot axis in memory; pools hold their rows in use only.
_PAYLOAD_ARRAYS = (
    ("grid_count_body_fever", np.int32, 2),
    ("grid_count_body_normal", np.int32, 2),
    ("grid_head_len", np.int8, 2),
    ("grid_fever_masks_bits", np.uint32, 3),
    ("grid_frontier_count", np.int32, 2),
    ("grid_frontier_offset", np.int32, 2),
    ("grid_frontier_body_fever_pool", np.int32, 1),
    ("grid_frontier_body_normal_pool", np.int32, 1),
    ("grid_frontier_masks_bits_pool", np.uint32, 2),
    ("grid_frontier_head_coeffs_pool", np.int16, 2),
    ("grid_gap", np.int32, 2),
    ("grid_fever_activations", np.int32, 2),
)
_TIMELINE_FRONTIER_CACHE_ARRAY_NAMES = frozenset(
    ("version", "frontier_pool_used", *(name for name, _, _ in _PAYLOAD_ARRAYS))
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
) -> None:
    """
    Upload one cached frontier slot without GPU->CPU round-tripping existing fields.

    The old merge path used `field.to_numpy()` to preserve other song slots, patched
    one slot on the CPU, then `from_numpy()` uploaded the whole field again. On
    Vulkan that is a large forced download plus a large upload. These prefix kernels
    update only the active slot.
    """
    reset_ga_evaluation_cache()
    source_slot_i = int(source_slot_i)
    song_slot_i = int(song_slot_i)

    def upload_i32_grid(dst, arr: np.ndarray) -> None:
        _upload_timeline_grid_slot_i32_kernel(dst, song_slot_i, _slot_payload(arr, source_slot_i, np.int32))

    def upload_i8_grid(dst, arr: np.ndarray) -> None:
        _upload_timeline_grid_slot_i8_kernel(dst, song_slot_i, _slot_payload(arr, source_slot_i, np.int8))

    upload_i32_grid(fields.grid_count_body_fever, payload.grid_count_body_fever)
    upload_i32_grid(fields.grid_count_body_normal, payload.grid_count_body_normal)
    upload_i8_grid(fields.grid_head_len, payload.grid_head_len)

    masks = _slot_payload(payload.grid_fever_masks_bits, source_slot_i, np.uint32)
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
        coeff_pool = np.ascontiguousarray(
            np.asarray(payload.grid_frontier_head_coeffs_pool[source_slot_i, :pool_used, :], dtype=np.int16)
        )
        _upload_timeline_pool_slot_i32_kernel(fields.grid_frontier_body_fever_pool, song_slot_i, pool_used, fever_pool)
        _upload_timeline_pool_slot_i32_kernel(fields.grid_frontier_body_normal_pool, song_slot_i, pool_used, normal_pool)
        _upload_timeline_pool_masks_bits_slot_kernel(song_slot_i, pool_used, mask_pool)
        _upload_timeline_pool_head_coeffs_slot_kernel(song_slot_i, pool_used, coeff_pool)


# ============================================================================
# GPU TIMELINE PRECOMPUTATION (eliminates Numba typeof overhead)
# ============================================================================

_gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS  # Track last song per slot
# The compressed .npz bytes (~20-90KB, the exact disk form) of recently used payloads, not the ~1.1MB decoded
# payloads: a song prepared ahead of its GA turn is decoded (<1ms) from here instead of re-read from disk.
_frontier_payload_memory: MemoryLru[bytes] = MemoryLru(40)
# The timeline cache version: a hand-kept base version plus a fingerprint (an AST digest, see logic_fingerprint.py) of
# the Base producer sources, so a logic change there rotates it by itself. The cache key hashes the song inputs and the
# FT/FF axes, never the producer, so bump the base version when the payload changes in a way neither sees (e.g. a
# dependency's behavior). A new version reads an older version's files only when it lists that version below, after a
# byte gate proved them identical. The version history is in git.
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
    # Engine rewrite R5 (FG builder argument tuples; the builder is a timeline fingerprint input): the 40-chart
    # sample's timeline payloads (both timing modes) are byte-identical, one to one, to the e0f26c1952cc producer's
    # builds (gate r5/g6), as the deployed 56a41dacb9b6's are. Keep everything the deployed service accepts
    # readable (non-transitive).
    "exact-frontier-v12+logic-f06c1b1fe6ca": (
        "exact-frontier-v12+logic-56a41dacb9b6",
        "exact-frontier-v12+logic-e0f26c1952cc",
        "exact-frontier-v12+logic-dac3ca4b6278",
        "exact-frontier-v12+logic-ede645c00a02",
        "exact-frontier-v12+logic-e2108556084d",
        "exact-frontier-v12+logic-920bc4af7ee6",
        "exact-frontier-v12+logic-be26caca62b4",
    ),
    # Engine rewrite R5 (the shared FG builder is a timeline fingerprint input; no producer logic change): the
    # 40-chart sample's timeline payloads (both timing modes) built by this code are byte-identical, one to one, to
    # the deployed e0f26c1952cc producer's builds (gates r5/g1-g4). Keep everything the deployed service accepts
    # readable (non-transitive).
    "exact-frontier-v12+logic-56a41dacb9b6": (
        "exact-frontier-v12+logic-e0f26c1952cc",
        "exact-frontier-v12+logic-dac3ca4b6278",
        "exact-frontier-v12+logic-ede645c00a02",
        "exact-frontier-v12+logic-e2108556084d",
        "exact-frontier-v12+logic-920bc4af7ee6",
        "exact-frontier-v12+logic-be26caca62b4",
    ),
    # Engine rewrite stage 5D (test-only oracles out of the shared producer sources) changes no producer logic:
    # the capture charts' timeline payloads (both timing modes) built by this code are byte-identical, one to one,
    # to the production producer's builds (and to the 52f84d17 snapshot). Keep everything the deployed service
    # accepts readable (non-transitive).
    "exact-frontier-v12+logic-e0f26c1952cc": (
        "exact-frontier-v12+logic-dac3ca4b6278",
        "exact-frontier-v12+logic-ede645c00a02",
        "exact-frontier-v12+logic-e2108556084d",
        "exact-frontier-v12+logic-920bc4af7ee6",
        "exact-frontier-v12+logic-be26caca62b4",
    ),
    # Engine rewrite stage 2 (typed stat curves and songs; timing_envelope builds from a Chart) changes no
    # producer logic: the capture charts' timeline payloads (both timing modes) built by this code are
    # byte-identical, one to one, to the deployed ede645c00a02 producer's builds. Keep everything the deployed
    # service accepts readable (non-transitive).
    "exact-frontier-v12+logic-dac3ca4b6278": (
        "exact-frontier-v12+logic-ede645c00a02",
        "exact-frontier-v12+logic-e2108556084d",
        "exact-frontier-v12+logic-920bc4af7ee6",
        "exact-frontier-v12+logic-be26caca62b4",
    ),
    # Engine rewrite stage 1 changes no producer logic: the capture charts' timeline payloads (both timing
    # modes) rebuilt with this code are byte-identical to the deployed e2108556084d cache. Keep everything the
    # deployed service accepts readable (non-transitive).
    "exact-frontier-v12+logic-ede645c00a02": (
        "exact-frontier-v12+logic-e2108556084d",
        "exact-frontier-v12+logic-920bc4af7ee6",
        "exact-frontier-v12+logic-be26caca62b4",
    ),
    # Custom-cache routing and pre-allocation admission do not alter an admitted frontier.
    "exact-frontier-v12+logic-e2108556084d": (
        # Keep the currently deployed v12 cache lineage readable during the rolling update.
        "exact-frontier-v12+logic-920bc4af7ee6",
        "exact-frontier-v12+logic-be26caca62b4",
    ),
    # Legacy cleanup deleted an orphaned timing-envelope wrapper. The live envelope builders and
    # persisted Base payload bytes are unchanged; retain only the byte-proven Issue #161 lineage.
    "exact-frontier-v12+logic-73245c017cbd": (
        "exact-frontier-v12+logic-61d6f59cade0",
        "exact-frontier-v12+logic-12c8db234d06",
        "exact-frontier-v12+logic-e0b0e8ef6411",
    ),
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


def _frontier_payload_cache_key(song_key: tuple, ref_ft: np.ndarray, ref_ff: np.ndarray) -> tuple:
    return (
        _FRONTIER_DISK_CACHE_VERSION,
        song_key,
        bytes(array_sig16(np.asarray(ref_ft, dtype=np.float32).reshape(-1))),
        bytes(array_sig16(np.asarray(ref_ff, dtype=np.float32).reshape(-1))),
    )


def _song_cache_key(song: TimedSong, curves: StatCurves) -> tuple:
    """The key of the payload file serving `song`: its timing and the FT/FF axes.

    The payload depends on the other curves not at all, so startup prebuild and runtime scoring share one file.
    """
    return _frontier_payload_cache_key(song.timeline_key, curves.f32["Fever Time"], curves.f32["Fever Fill Rate"])


def _frontier_disk_cache_dir() -> Path:
    scoped = scoped_frontier_cache_dir("timeline")
    return scoped if scoped is not None else paths().timeline_cache


def _encode_frontier_payload_npz(payload: TimelineFrontierGridPayload) -> bytes:
    """The compressed .npz form of a payload (the disk file and the memory tier's entry)."""
    pool_used = max(0, int(payload.frontier_pool_used))
    arrays = {}
    for name, dtype, _rank in _PAYLOAD_ARRAYS:
        slot = getattr(payload, name)[0]
        arrays[name] = np.asarray(slot[:pool_used] if name.endswith("_pool") else slot, dtype=dtype)
    buf = io.BytesIO()
    np.savez_compressed(
        buf,
        version=np.asarray(_FRONTIER_DISK_CACHE_VERSION),
        frontier_pool_used=np.asarray(pool_used, dtype=np.int32),
        **arrays,
    )
    return buf.getvalue()


def _decode_frontier_payload_npz(raw: bytes) -> TimelineFrontierGridPayload | None:
    """The payload of an .npz form; None when a version outside the compatible lineage wrote it."""
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        if str(data["version"].item()) not in TIMELINE_FRONTIER_CACHE.compatible_versions():
            return None
        arrays = {}
        for name, dtype, rank in _PAYLOAD_ARRAYS:
            array = np.asarray(data[name], dtype=dtype)
            arrays[name] = np.expand_dims(array, axis=0) if array.ndim == rank else array
        return TimelineFrontierGridPayload(**arrays, frontier_pool_used=int(data["frontier_pool_used"].item()))


def timeline_frontier_cache_file_is_complete(cache_file: str | Path) -> bool:
    try:
        path = Path(cache_file)
    except TypeError:
        return False
    if not path.exists():
        return False
    grid_shape = (MAX_STAT + 1, MAX_STAT + 1)
    try:
        with np.load(path, allow_pickle=False) as data:
            files = set(data.files)
            if files != _TIMELINE_FRONTIER_CACHE_ARRAY_NAMES:
                return False
            version = str(data["version"].item())
            if version not in TIMELINE_FRONTIER_CACHE.compatible_versions():
                return False
            pool_used = int(np.asarray(data["frontier_pool_used"]).item())
            if pool_used < 0:
                return False
            for name, _dtype, rank in _PAYLOAD_ARRAYS:
                leading = (pool_used,) if name.endswith("_pool") else grid_shape
                expected = (*leading, 4) if rank > len(leading) else leading
                if tuple(np.asarray(data[name]).shape) != expected:
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


TIMELINE_FRONTIER_CACHE = FrontierCache(
    name="timeline",
    log_label="[TimelineCache]",
    directory=_frontier_disk_cache_dir,
    file_path=lambda cache_key: content_addressed_path(_frontier_disk_cache_dir(), cache_key),
    version=lambda: _FRONTIER_DISK_CACHE_VERSION,
    predecessors=_EXACT_COMPATIBLE_TIMELINE_PREDECESSOR_VERSIONS,
    is_complete=timeline_frontier_cache_file_is_complete,
    song_key=_song_cache_key,
    manifest_name="manifest_v1.json",
    manifest_version_field="frontier_version",
)


def _load_frontier_payload(cache_key: tuple) -> tuple[TimelineFrontierGridPayload, bytes] | None:
    path = TIMELINE_FRONTIER_CACHE.readable_path(cache_key)
    if path is None:
        return None
    try:
        raw = path.read_bytes()
        payload = _decode_frontier_payload_npz(raw)
    except Exception as e:
        # An unreadable or corrupt payload is a cache miss: drop it so the next build rewrites it.
        logger.debug(f"timeline:_load_frontier_payload: {e}")
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    return None if payload is None else (payload, raw)


def _save_frontier_payload(cache_key: tuple, raw: bytes) -> None:
    try:
        write_atomically(TIMELINE_FRONTIER_CACHE.file_path(cache_key), lambda tmp: tmp.write_bytes(raw))
    except OSError as e:
        # The disk tier is an optimization: a failed write leaves the in-memory payload in use.
        logger.debug(f"timeline:_save_frontier_payload: {e}")


def _cached_frontier_payload(cache_key: tuple) -> tuple[TimelineFrontierGridPayload | None, str]:
    raw = _frontier_payload_memory.get(cache_key)
    if raw is not None:
        cached = _decode_frontier_payload_npz(raw)
        if cached is None:
            raise ValueError("timeline frontier memory cache holds an incompatible payload")
        return cached, "memory"
    loaded = _load_frontier_payload(cache_key)
    if loaded is None:
        return None, "missing"
    cached, raw = loaded
    _frontier_payload_memory.put(cache_key, raw)
    return cached, "disk"


def _timeline_payload_lookup_context(song: TimedSong, curves: StatCurves) -> dict:
    """The frontier inputs of a timed song: its cache key, the chart and the FT/FF axes.

    The payload depends on song timing and the FT/FF axes only, so the key leaves the other curves out
    and startup prebuild and runtime scoring share one disk artifact.
    """
    chart = song.chart
    total_notes = chart.total_notes
    if total_notes > fields.MAX_SONG_NOTES:
        raise ValueError(f"Song has {total_notes} notes, max is {fields.MAX_SONG_NOTES}")
    if song.mode == "zero_ms":
        # The zero_ms payload is a deterministic singleton built from fixed hit timestamps; the
        # physical Perfect-window inputs are absent and never consumed.
        perfect_candidates = np.empty(0, dtype=np.float32)
        perfect_floor = np.empty(0, dtype=np.float32)
        lanes = np.empty(0, dtype=np.int32)
    else:
        perfect_candidates, perfect_floor, lanes = song.perfect_candidates, song.perfect_floor, chart.lanes
    return {
        "song_key": song.timeline_key,
        "timestamps": chart.timestamps,
        "total_notes": total_notes,
        "long_notes": chart.long_notes,
        "last_note_time": chart.last_note_time,
        "ref_ft": curves.f32["Fever Time"],
        "ref_ff": curves.f32["Fever Fill Rate"],
        "perfect_candidates": perfect_candidates,
        "perfect_floor": perfect_floor,
        "lanes": lanes,
    }


def timeline_frontier_payload_cache_info(song: TimedSong, curves: StatCurves) -> FrontierCacheInfo:
    """
    Return exact-frontier cache status without building group payloads or loading `.npz`.

    Startup prebuild uses this to skip already-built songs cheaply, with the exact key runtime upload
    uses. The disk path is the file that serves the key (a ratified predecessor's when only that one
    exists), so the prebuild manifest records the file that is actually read.
    """
    cache_key = _song_cache_key(song, curves)
    readable = TIMELINE_FRONTIER_CACHE.readable_path(cache_key)
    if cache_key in _frontier_payload_memory:
        cache_source = "memory"
    elif readable is not None:
        cache_source = "disk"
    else:
        cache_source = "missing"
    return FrontierCacheInfo(
        cache_key=cache_key,
        disk_path=readable or TIMELINE_FRONTIER_CACHE.file_path(cache_key),
        cache_source=cache_source,
    )


def _build_zero_ms_timeline_payload(song: TimedSong, curves: StatCurves) -> TimelineFrontierGridPayload:
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
    if song.mode != "zero_ms":
        raise ValueError("fixed chart-time timeline payload requires a zero_ms song")
    timestamps = song.hit_timestamps
    total_notes = int(timestamps.shape[0])
    if total_notes > 1 and bool(np.any(np.diff(timestamps) < np.float32(0.0))):
        raise ValueError("zero_ms chart timestamps must be non-decreasing")

    ref_ft = curves.f32["Fever Time"]
    ref_ff = curves.f32["Fever Fill Rate"]
    grid_size = MAX_STAT + 1
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
    long_notes = song.chart.long_notes
    last_note_time = song.chart.last_note_time
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


def build_or_load_timeline_frontier_payload(
    song: TimedSong, curves: StatCurves
) -> FrontierCacheLoad[TimelineFrontierGridPayload]:
    """
    The song's exact timeline frontier payload: the memory or disk cache's, else built and persisted.

    Host-side (no Taichi fields are touched) and the one entry point of runtime scoring, background
    lookahead and offline disk-cache prebuilding, so they share the cache signatures. zero_ms is fixed
    timing: its payload is the cheap chart-time singleton, never the perfect_window candidate frontier.
    """
    t0 = time.perf_counter()
    lookup = _timeline_payload_lookup_context(song, curves)
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])
    payload, cache_source = _cached_frontier_payload(cache_key)
    if payload is None:
        if song.mode == "zero_ms":
            payload = _build_zero_ms_timeline_payload(song, curves)
        else:
            payload = build_timeline_frontier_grid_payload(
                song_slot=0,
                total_notes=int(lookup["total_notes"]),
                long_notes=int(lookup["long_notes"]),
                last_note_time=float(lookup["last_note_time"]),
                timestamps=lookup["timestamps"],
                perfect_candidate_timestamps=lookup["perfect_candidates"],
                perfect_floor_timestamps=lookup["perfect_floor"],
                lanes=lookup["lanes"],
                ref_ft=lookup["ref_ft"],
                ref_ff=lookup["ref_ff"],
            )
        raw = _encode_frontier_payload_npz(payload)
        _save_frontier_payload(cache_key, raw)
        _frontier_payload_memory.put(cache_key, raw)
        cache_source = "built"
    return FrontierCacheLoad(
        payload=payload,
        cache_key=cache_key,
        disk_path=TIMELINE_FRONTIER_CACHE.file_path(cache_key),
        cache_source=cache_source,
        elapsed_ms=float((time.perf_counter() - t0) * 1000.0),
    )


def precompute_timeline_gpu(
    song: TimedSong,
    curves: StatCurves,
    song_slot: int = 0,
    *,
    prebuilt_frontier: FrontierCacheLoad[TimelineFrontierGridPayload] | None = None,
) -> None:
    """
    Upload the startup-built exact timeline frontier for one song slot.

    Runtime is cache-consumer only: the candidate-independent startup cache owns
    group-envelope construction and frontier building. The live GPU path uploads
    only the per-slot fields read by GA scoring kernels.

    Args:
        song: the timed song
        curves: the stat curves (the FT/FF axes key the frontier)
        song_slot: Grid slot to write to (0-7, default 0 for single-song mode)
        prebuilt_frontier: Optional already-resolved frontier payload to upload BY VALUE.
            Production runtime leaves this None so build_or_load_timeline_frontier_payload() can
            reuse or build the canonical persistent cache artifact.
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
    ensure_ready(curves)

    # Check if we already computed for this song+ref set.
    song_key = song.timeline_key
    if _gpu_timeline_song_id_by_slot[song_slot] == song_key:
        return  # Already computed
    frontier_result = (
        prebuilt_frontier if prebuilt_frontier is not None else build_or_load_timeline_frontier_payload(song, curves)
    )
    song_slot_i = int(song_slot)
    frontier_payload = frontier_result.payload
    if int(frontier_payload.grid_frontier_count.shape[1]) < MAX_STAT + 1 or int(
        frontier_payload.grid_frontier_count.shape[2]
    ) < MAX_STAT + 1:
        raise ValueError(
            "Timeline frontier payload is incomplete. Startup cache prebuild must build the "
            "candidate-independent all-FT/FF timeline frontier before runtime scoring."
        )

    _upload_timeline_frontier_payload_slot(
        frontier_payload,
        song_slot_i,
        source_slot_i=0,
    )

    _gpu_timeline_song_id_by_slot[song_slot] = song_key


def precompute_timeline_gpu_for_warmup(song: TimedSong, curves: StatCurves, song_slot: int = 0) -> None:
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
    ensure_ready(curves)
    started = time.perf_counter()
    lookup = _timeline_payload_lookup_context(song, curves)
    cache_key = _frontier_payload_cache_key(lookup["song_key"], lookup["ref_ft"], lookup["ref_ff"])
    payload = build_timeline_frontier_grid_payload(
        song_slot=0,
        total_notes=int(lookup["total_notes"]),
        long_notes=int(lookup["long_notes"]),
        last_note_time=float(lookup["last_note_time"]),
        timestamps=np.asarray(lookup["timestamps"], dtype=np.float32),
        perfect_candidate_timestamps=np.asarray(lookup["perfect_candidates"], dtype=np.float32),
        perfect_floor_timestamps=np.asarray(lookup["perfect_floor"], dtype=np.float32),
        lanes=np.asarray(lookup["lanes"], dtype=np.int32),
        ref_ft=np.asarray(lookup["ref_ft"], dtype=np.float32),
        ref_ff=np.asarray(lookup["ref_ff"], dtype=np.float32),
    )
    frontier_result = FrontierCacheLoad(
        payload=payload,
        cache_key=cache_key,
        disk_path=TIMELINE_FRONTIER_CACHE.file_path(cache_key),
        cache_source="warmup_disposable",
        elapsed_ms=float((time.perf_counter() - started) * 1000.0),
    )
    precompute_timeline_gpu(
        song,
        curves,
        song_slot=song_slot,
        prebuilt_frontier=frontier_result,
    )


@on_hard_reset
def reset_timeline_state() -> None:
    """Reset module-level timeline upload caches after `ti.reset()`."""
    global _gpu_timeline_song_id_by_slot
    _gpu_timeline_song_id_by_slot = [None] * MAX_SONG_SLOTS
    _frontier_payload_memory.clear()
