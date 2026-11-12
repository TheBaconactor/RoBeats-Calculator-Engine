"""A song's exact timeline frontier payload on disk and in memory: one compressed .npz per song timing and FT/FF axes.

Host-side, no Taichi: scoring, the prebuild and the website read it here; gpu.device uploads it to the GPU.
"""

import contextlib
import io
import logging
import time
from pathlib import Path

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.frontier.cache import (
    FRONTIER_PRODUCER_SOURCES,
    FrontierCache,
    FrontierCacheInfo,
    FrontierCacheLoad,
    MemoryLru,
    cache_version,
    write_atomically,
)
from gear_optimizer.frontier.cache_scope import scoped_frontier_cache_dir
from gear_optimizer.frontier.timeline_cache_serde import PAYLOAD_ARRAYS, encode_payload_npz
from gear_optimizer.frontier.timeline_producer import (
    TimelineFrontierGridPayload,
    build_fixed_timing_payload,
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

_TIMELINE_FRONTIER_CACHE_ARRAY_NAMES = frozenset(
    ("version", "frontier_pool_used", *(name for name, _, _ in PAYLOAD_ARRAYS))
)


# The compressed .npz bytes (~20-90KB, the exact disk form) of recently used payloads, not the ~1.1MB decoded
# payloads: a song prepared ahead of its GA turn is decoded (<1ms) from here instead of re-read from disk.
_frontier_payload_memory: MemoryLru[bytes] = MemoryLru(40)
# The last payload served, as (its memory-tier bytes, payload): a solve reads one song's payload once per scored
# loadout (~50 times), every reader only reads it, so it is decoded once.
_last_served_payload: tuple[bytes, TimelineFrontierGridPayload] | None = None
# The timeline cache version: a hand-kept base version plus a fingerprint of the Base producer sources. The cache key
# hashes the song inputs and the FT/FF axes, never the producer, so bump the base version when the payload changes in a
# way neither sees (e.g. a dependency's behavior). The version history is in git.
_FRONTIER_DISK_CACHE_BASE_VERSION = "exact-frontier-v12"
_TIMELINE_DP_SOURCES = (
    Path(__file__).resolve().parent / "timeline_producer.py",
    Path(__file__).resolve().parent / "timeline_cache_serde.py",
    Path(__file__).resolve().parents[1] / "solver" / "fever_timeline.py",
    *FRONTIER_PRODUCER_SOURCES,
)
_FRONTIER_DISK_CACHE_VERSION = cache_version(_FRONTIER_DISK_CACHE_BASE_VERSION, _TIMELINE_DP_SOURCES)
# Exact cache compatibility is explicit and non-transitive: a version reads an older version's payloads only when it
# lists that version here, after a byte gate proved the persisted payloads identical. The version history is in git.
_EXACT_COMPATIBLE_TIMELINE_PREDECESSOR_VERSIONS: dict[str, tuple[str, ...]] = {
    # Giving the producer's host layer records and one precompute changed no frontier: the gate (16 charts), the 40-chart
    # sample (2,160 arrays) and the whole catalog (2,287 charts, both timing modes) are identical to the 5f4d8f2f18e7
    # producer's. Evidence in workspace/_engine_round3_2026-11-10.
    "exact-frontier-v12+logic-1d9452c7fd66": (
        "exact-frontier-v12+logic-5f4d8f2f18e7",
    ),
    # The frontier kernels organised by activation, the payload encoder moved into timeline_cache_serde and the
    # fixed-timing builder into timeline_producer changed no stored byte: the gate (16 charts), the 40-chart sample
    # (2,160 arrays and members) and the whole catalog (2,287 charts, both timing modes) are identical to the
    # 1d9452c7fd66 and 5f4d8f2f18e7 producers'. Evidence in workspace/_engine_round3_2026-11-10.
    "exact-frontier-v12+logic-b91994c1695a": (
        "exact-frontier-v12+logic-1d9452c7fd66",
        "exact-frontier-v12+logic-5f4d8f2f18e7",
    ),
}


def _song_cache_key(song: TimedSong, curves: StatCurves) -> tuple:
    """The key of the payload file serving `song`: the version, the song's timing and the FT/FF axes. The payload
    depends on no other curve, so the startup prebuild and runtime scoring share one file."""
    return (
        _FRONTIER_DISK_CACHE_VERSION,
        song.timeline_key,
        bytes(array_sig16(curves.f32["Fever Time"])),
        bytes(array_sig16(curves.f32["Fever Fill Rate"])),
    )


def _frontier_disk_cache_dir() -> Path:
    scoped = scoped_frontier_cache_dir("timeline")
    return scoped if scoped is not None else paths().timeline_cache


def _decode_frontier_payload_npz(raw: bytes) -> TimelineFrontierGridPayload | None:
    """The payload of an .npz form; None when a version outside the compatible lineage wrote it."""
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        if str(data["version"].item()) not in TIMELINE_FRONTIER_CACHE.compatible_versions():
            return None
        arrays = {name: data[name][np.newaxis] for name, _dtype, _rank in PAYLOAD_ARRAYS}
        return TimelineFrontierGridPayload(**arrays, frontier_pool_used=int(data["frontier_pool_used"]))


def timeline_frontier_cache_file_is_complete(cache_file: str | Path) -> bool:
    """A readable payload file of a compatible version, with exactly a payload's arrays in the shapes of one song and
    every cell's frontier inside the pool."""
    grid_shape = (MAX_STAT + 1, MAX_STAT + 1)
    try:
        with np.load(cache_file, allow_pickle=False) as data:
            if set(data.files) != _TIMELINE_FRONTIER_CACHE_ARRAY_NAMES:
                return False
            if str(data["version"].item()) not in TIMELINE_FRONTIER_CACHE.compatible_versions():
                return False
            pool_used = int(data["frontier_pool_used"])
            arrays = {name: data[name] for name, _dtype, _rank in PAYLOAD_ARRAYS}
    except Exception:  # whatever a missing, truncated or damaged file raises: it is not a complete file
        return False
    for name, _dtype, rank in PAYLOAD_ARRAYS:
        leading = (pool_used,) if name.endswith("_pool") else grid_shape
        if arrays[name].shape != ((*leading, 4) if rank > len(leading) else leading):
            return False
    count = arrays["grid_frontier_count"].astype(np.int64)
    offset = arrays["grid_frontier_offset"].astype(np.int64)
    return bool((count >= 0).all() and (offset >= 0).all() and (offset + count <= pool_used).all())


TIMELINE_FRONTIER_CACHE = FrontierCache(
    name="timeline",
    log_label="[TimelineCache]",
    directory=_frontier_disk_cache_dir,
    version=lambda: _FRONTIER_DISK_CACHE_VERSION,
    predecessors=_EXACT_COMPATIBLE_TIMELINE_PREDECESSOR_VERSIONS,
    is_complete=timeline_frontier_cache_file_is_complete,
    song_key=_song_cache_key,
    manifest_name="manifest_v1.json",
    manifest_version_field="frontier_version",
)


def _load_frontier_payload(cache_key: tuple) -> tuple[TimelineFrontierGridPayload, bytes] | None:
    """The key's payload and the bytes of its file; None when no file of a compatible version serves it. A file that
    cannot be read is a miss and is deleted, so the next build writes it again."""
    path = TIMELINE_FRONTIER_CACHE.readable_path(cache_key)
    if path is None:
        return None
    try:
        raw = path.read_bytes()
        payload = _decode_frontier_payload_npz(raw)
    except Exception:  # whatever a truncated or damaged file raises
        logger.warning("[TimelineCache] unreadable payload %s; it is deleted and rebuilt", path, exc_info=True)
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)
        return None
    return None if payload is None else (payload, raw)


def _save_frontier_payload(cache_key: tuple, raw: bytes) -> None:
    try:
        write_atomically(TIMELINE_FRONTIER_CACHE.file_path(cache_key), lambda tmp: tmp.write_bytes(raw))
    except OSError:
        # The disk tier is an optimization: a failed write leaves the in-memory payload in use.
        logger.warning("[TimelineCache] the payload file of a song could not be written", exc_info=True)


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
    """Whether the song's payload is in memory, on disk or missing, found without reading a file. The disk path is the
    file that serves the key (a ratified predecessor's when only that one exists)."""
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


def _check_note_count(song: TimedSong) -> None:
    total_notes = song.chart.total_notes
    if total_notes > MAX_SONG_NOTES:
        raise ValueError(f"Song has {total_notes} notes, max is {MAX_SONG_NOTES}")


def build_timeline_payload(song: TimedSong, curves: StatCurves) -> TimelineFrontierGridPayload:
    """The song's payload, built and not cached."""
    _check_note_count(song)
    if song.mode == "non-precise":
        return build_fixed_timing_payload(song, curves)
    chart = song.chart
    fever_durations, fill_thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, curves)
    return build_timeline_frontier_grid_payload(
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
    """The song's exact timeline frontier payload: the memory or disk cache's, else built and persisted.

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
        raw = encode_payload_npz(payload, _FRONTIER_DISK_CACHE_VERSION)
        _save_frontier_payload(cache_key, raw)
        _frontier_payload_memory.put(cache_key, raw)
        cache_source = "built"
    return FrontierCacheLoad(
        payload=payload,
        cache_key=cache_key,
        disk_path=TIMELINE_FRONTIER_CACHE.file_path(cache_key),
        cache_source=cache_source,
        elapsed_ms=(time.perf_counter() - t0) * 1000.0,
    )


def ensure_timeline_frontier_cache_for_song(song: TimedSong, curves: StatCurves) -> tuple[str, float, Path]:
    """Make sure the song's payload file exists; returns (cache source, build ms, the file). A file that exists is
    not read."""
    info = timeline_frontier_payload_cache_info(song, curves)
    if info.cache_source != "missing":
        return info.cache_source, 0.0, info.disk_path
    load = build_or_load_timeline_frontier_payload(song, curves)
    return load.cache_source, load.elapsed_ms, load.disk_path
