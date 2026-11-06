"""A song's exact timeline frontier payload on disk and in memory: one compressed .npz per song timing and FT/FF axes.

Host-side, no Taichi: scoring, the prebuild and the website read it here; gpu.device uploads it into a song slot.
"""

import io
import logging
import time
from pathlib import Path

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.logic_fingerprint import module_logic_fingerprint
from gear_optimizer.frontier.cache import (
    FrontierCache,
    FrontierCacheInfo,
    FrontierCacheLoad,
    MemoryLru,
    content_addressed_path,
    write_atomically,
)
from gear_optimizer.frontier.cache_scope import scoped_frontier_cache_dir
from gear_optimizer.frontier.fg_cache_types import _FG_SHARED_FRONTIER_PRODUCER_SOURCES, _SCORING_POLICY_SOURCE
from gear_optimizer.frontier.timeline_producer import (
    MAX_TIMELINE_FRONTIER_SURFACES,
    TimelineFrontierGridPayload,
    _head_mask_coefficients_py,
    build_timeline_frontier_grid_payload,
)
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.settings import paths
from gear_optimizer.solver.timing_envelope import TimedSong, fever_axes


logger = logging.getLogger(__name__)

# The longest chart scoring accepts: the real maximum is ~7,027 notes (M1LLI0N PP (Full Version) [EXTENDED CUT]), and the
# GPU's per-note arrays scale with this. A longer chart fails loud in `_check_note_count`, never truncated.
MAX_SONG_NOTES = 32768

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


# The compressed .npz bytes (~20-90KB, the exact disk form) of recently used payloads, not the ~1.1MB decoded
# payloads: a song prepared ahead of its GA turn is decoded (<1ms) from here instead of re-read from disk.
_frontier_payload_memory: MemoryLru[bytes] = MemoryLru(40)
# The last payload served, as (its memory-tier bytes, payload): a solve reads one song's payload once per scored
# loadout (~50 times), every reader only reads it, so it is decoded once.
_last_served_payload: tuple[bytes, TimelineFrontierGridPayload] | None = None
# The timeline cache version: a hand-kept base version plus a fingerprint (an AST digest, see logic_fingerprint.py) of
# the Base producer sources, so a logic change there rotates it by itself. The cache key hashes the song inputs and the
# FT/FF axes, never the producer, so bump the base version when the payload changes in a way neither sees (e.g. a
# dependency's behavior). A new version reads an older version's files only when it lists that version below, after a
# byte gate proved them identical. The version history is in git.
_FRONTIER_DISK_CACHE_BASE_VERSION = "exact-frontier-v12"
# Base persists timing geometry and Perfect-only recurrence output, never Great score valuation.
# Excluding the FG scoring policy keeps a Force-Greats-only score correction from rotating every
# Base frontier cache key. The remaining shared sources are the exact recurrence/geometry producer.
_BASE_SHARED_FRONTIER_PRODUCER_SOURCES = tuple(
    source for source in _FG_SHARED_FRONTIER_PRODUCER_SOURCES if source != _SCORING_POLICY_SOURCE
)
_TIMELINE_DP_SOURCES = (
    Path(__file__).resolve().parent / "timeline_producer.py",
    Path(__file__).resolve().parents[1] / "solver" / "fever_timeline.py",
    *_BASE_SHARED_FRONTIER_PRODUCER_SOURCES,
)
_FRONTIER_DISK_CACHE_VERSION = (
    f"{_FRONTIER_DISK_CACHE_BASE_VERSION}+logic-{module_logic_fingerprint(_TIMELINE_DP_SOURCES)}"
)
# Exact cache compatibility is explicit and non-transitive: a version reads an older version's payloads only when it
# lists that version here, after a byte gate proved the persisted payloads identical. The version history is in git.
_EXACT_COMPATIBLE_TIMELINE_PREDECESSOR_VERSIONS: dict[str, tuple[str, ...]] = {
    # judgment_bounds reads the game's Perfect Time curve, which at stat 0 gives the frontiers the same bands; no output
    # changed: the 2026-11-05 gate (16 charts) and sample (40 charts, both modes) payloads hold the same arrays as the
    # db3c419e0279 producer's, which ratified 3879362bd129's and so the 35c21d69e3b1 recompute's.
    # workspace/_rewrite_state_2026-11-05.
    "exact-frontier-v12+logic-adffed7e46af": (
        "exact-frontier-v12+logic-db3c419e0279",
        "exact-frontier-v12+logic-3879362bd129",
        "exact-frontier-v12+logic-35c21d69e3b1",
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
    global _last_served_payload
    raw = _frontier_payload_memory.get(cache_key)
    if raw is not None:
        if _last_served_payload is not None and _last_served_payload[0] is raw:
            return _last_served_payload[1], "memory"
        cached = _decode_frontier_payload_npz(raw)
        if cached is None:
            raise ValueError("timeline frontier memory cache holds an incompatible payload")
        _last_served_payload = (raw, cached)
        return cached, "memory"
    loaded = _load_frontier_payload(cache_key)
    if loaded is None:
        return None, "missing"
    cached, raw = loaded
    _frontier_payload_memory.put(cache_key, raw)
    _last_served_payload = (raw, cached)
    return cached, "disk"


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


def _build_non_precise_timeline_payload(song: TimedSong, curves: StatCurves) -> TimelineFrontierGridPayload:
    """Build the exact singleton chart-time surface for every FT/FF cell.

    non-precise is fixed timing (every hit at its chart timestamp), so each (Fever Time, Fever Fill)
    cell has exactly ONE deterministic fever surface -- there is no Perfect-window candidate
    frontier to search. This is the cheap "partial" build: it reuses the same per-cell fever kernel
    (``calculate_fever_timeline_indices``) the fixed-timing base scorer uses, so the payload scores
    bit-identically to ``score_stats_fixed_timing_exact`` while costing a fraction of the full
    carry-envelope DP that ``build_timeline_frontier_grid_payload`` runs for precise. It is
    the subset of the shared representation the user's thin gate promotes to a full frontier only
    when precise is actually requested.
    """
    if song.mode != "non-precise":
        raise ValueError("fixed chart-time timeline payload requires a non-precise song")
    timestamps = song.hit_timestamps
    total_notes = int(timestamps.shape[0])
    if total_notes > 1 and bool(np.any(np.diff(timestamps) < np.float32(0.0))):
        raise ValueError("non-precise chart timestamps must be non-decreasing")

    fever_durations, fill_thresholds = fever_axes(total_notes, song.chart.long_notes, song.chart.last_note_time, curves)
    fill_notes = np.ceil(fill_thresholds).astype(np.int64)
    grid_size = MAX_STAT + 1

    shape = (1, grid_size, grid_size)
    grid_count_body_fever = np.zeros(shape, dtype=np.int32)
    grid_count_body_normal = np.zeros(shape, dtype=np.int32)
    grid_head_len = np.full(shape, min(total_notes, 100), dtype=np.int8)
    grid_fever_masks_bits = np.zeros((*shape, 4), dtype=np.uint32)
    grid_frontier_count = np.ones(shape, dtype=np.int32)
    grid_frontier_offset = np.zeros(shape, dtype=np.int32)
    grid_gap = np.zeros(shape, dtype=np.int32)
    grid_fever_activations = np.zeros(shape, dtype=np.int32)

    pool_cap = MAX_TIMELINE_FRONTIER_SURFACES
    body_fever_pool = np.zeros((1, pool_cap), dtype=np.int32)
    body_normal_pool = np.zeros((1, pool_cap), dtype=np.int32)
    masks_pool = np.zeros((1, pool_cap, 4), dtype=np.uint32)
    head_coeffs_pool = np.zeros((1, pool_cap, 4), dtype=np.int16)
    pool_by_surface: dict[tuple[int, int, tuple[int, int, int, int], int, int], int] = {}

    from gear_optimizer.solver.fever_timeline import calculate_fever_timeline_surface_grid

    last_fever_end = np.zeros((grid_size, grid_size), dtype=np.int32)
    calculate_fever_timeline_surface_grid(
        timestamps,
        total_notes,
        fever_durations,
        fill_notes,
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
                    raise RuntimeError(f"non-precise timeline surface pool overflow: cap={pool_cap}")
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


def _check_note_count(song: TimedSong) -> None:
    total_notes = song.chart.total_notes
    if total_notes > MAX_SONG_NOTES:
        raise ValueError(f"Song has {total_notes} notes, max is {MAX_SONG_NOTES}")


def build_timeline_payload(song: TimedSong, curves: StatCurves) -> TimelineFrontierGridPayload:
    """The song's payload, built and not cached."""
    _check_note_count(song)
    if song.mode == "non-precise":
        return _build_non_precise_timeline_payload(song, curves)
    chart = song.chart
    fever_durations, fill_thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, curves)
    return build_timeline_frontier_grid_payload(
        total_notes=chart.total_notes,
        timestamps=chart.timestamps,
        perfect_candidate_timestamps=song.perfect_candidates,
        perfect_floor_timestamps=song.perfect_floor,
        exit_ceiling_timestamps=song.exit_ceiling,
        lanes=chart.lanes,
        fever_times=fever_durations,
        fever_fills=fill_thresholds,
    )


def build_or_load_timeline_frontier_payload(
    song: TimedSong, curves: StatCurves
) -> FrontierCacheLoad[TimelineFrontierGridPayload]:
    """
    The song's exact timeline frontier payload: the memory or disk cache's, else built and persisted.

    The one entry point of runtime scoring, background lookahead and offline disk-cache prebuilding, so they share the
    cache signatures. non-precise is fixed timing: its payload is the cheap chart-time singleton, never the precise
    candidate frontier.
    """
    t0 = time.perf_counter()
    _check_note_count(song)
    cache_key = _song_cache_key(song, curves)
    payload, cache_source = _cached_frontier_payload(cache_key)
    if payload is None:
        payload = build_timeline_payload(song, curves)
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
