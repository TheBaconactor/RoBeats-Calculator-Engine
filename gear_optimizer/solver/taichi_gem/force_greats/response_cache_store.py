"""The FG response-frontier cache on disk: one .npz bundle per song timing and stat curves, and the process memory tiers
in front of it.

A bundle holds the frontier metadata and two surface tables. rows (n, 4) uint32: one head-pattern ID and three body
counts per logical surface row, in producer order. patterns (m, 10) uint32: each distinct head pattern's eight
fever/Great mask words and its four uint16 head coefficients packed into two words. A table is stored column by
column, each column's little-endian bytes as four byte planes (plane 4j + b holds byte b of column j), which the
archive's deflate shrinks to ~9% of the raw table (row-major bytes: ~26%). A reader decodes a whole bundle at once,
so its metadata and tables always come from one write.
"""

from __future__ import annotations

import logging
import threading
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np
from numpy.lib import format as np_format

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.solver.frontier_cache import FrontierCache, MemoryLru, write_atomically

from .response_cache_keys import (
    _fg_response_disk_cache_dir,
    _fg_response_disk_cache_path,
    _fg_response_cache_version,
    fg_response_frontier_bundle_cache_key,
)
from .response_cache_patterns import (
    intern_surface_row_words,
    pack_surface_patterns,
    surface_head_coeffs,
    unpack_surface_patterns,
)
from .response_cache_types import (
    _BUNDLE_ARRAY_NAMES,
    FgResponseFrontierCachePayload,
    FgResponseFrontierScoringBundle,
    _normalize_stat_key,
    all_response_stat_keys,
    normalize_fg_response_stat_keys,
)
from .response_types import FgResponseFrontierResult

logger = logging.getLogger(__name__)

# The memory tiers, keyed like the files (version, song key, FT/FF axes signatures, then a stat key, a stat-key tuple
# or the bundle marker): frontiers materialized per stat key, merged bundles and request payloads of builds, and
# scoring bundles (metadata plus the decoded surface tables: a few MB each, up to ~100 MB on the longest charts).
_geometry_frontier_memory: MemoryLru[FgResponseFrontierResult] = MemoryLru(4096)
_payload_memory: MemoryLru[FgResponseFrontierCachePayload] = MemoryLru(8)
_scoring_bundle_memory: MemoryLru[FgResponseFrontierScoringBundle] = MemoryLru(8)
_RESPONSE_BUNDLE_BUILD_PARALLELISM = 1
_response_bundle_build_slots = threading.BoundedSemaphore(int(_RESPONSE_BUNDLE_BUILD_PARALLELISM))
_NPZ_FAST_COMPRESS_LEVEL = 1
_SURFACE_TABLES = ("surface_rows", "surface_patterns")
# What reading a damaged or truncated bundle file raises (a bad CRC is a BadZipFile).
_UNREADABLE = (OSError, ValueError, KeyError, IndexError, EOFError, zipfile.BadZipFile)

# Exact cache compatibility is explicit and non-transitive: a version reads an older version's bundles only when it lists
# that version here, after a byte gate proved the persisted bundles identical. The version history is in git.
_EXACT_COMPATIBLE_PREDECESSOR_VERSIONS: dict[str, tuple[str, ...]] = {
    # The trace reconstruction left the fingerprint and its witnesses left fill_crossing.py; no producer output
    # changed: the 40-chart sample's bundles (both modes) hold the same arrays, chart by chart, as the 38e82e26a8ec
    # producer's (the 2026-10-10 recompute's engine; its gate digests, lists/ref40_head_digests.tsv).
    "fg-response-frontier-visible-first-v32+logic-2653d51a312d": (
        "fg-response-frontier-visible-first-v32+logic-38e82e26a8ec",
    ),
}


def _byte_planes(table: np.ndarray) -> np.ndarray:
    """(n, k) uint32 -> (4k, n) uint8: plane 4j + b holds byte b of column j."""
    n, k = table.shape
    columns = np.ascontiguousarray(table.T, dtype="<u4")
    return np.ascontiguousarray(columns.view(np.uint8).reshape(k, n, 4).transpose(0, 2, 1)).reshape(4 * k, n)


def _columns(planes: np.ndarray) -> np.ndarray:
    """(4k, n) uint8 byte planes -> the table's (k, n) uint32 columns."""
    k4, n = planes.shape
    return np.ascontiguousarray(planes.reshape(k4 // 4, 4, n).transpose(0, 2, 1)).view("<u4").reshape(k4 // 4, n)


_PURGED_VERSION_MARKER = ".purged_version"


def purge_stale_version_cache_files(*, authorize_rotation: bool = False) -> int:
    """Delete bundles outside the current exact compatibility lineage.

    Versions outside the explicit compatible set are dead weight because every reader rejects them, but deleting a
    provisioned full pool is an explicit production rotation, never routine startup maintenance. Without
    ``authorize_rotation`` this function detects any incompatible bundle and fails loudly before unlinking a byte. An
    authorized prebuild sweeps once per compatibility-lineage change, guarded by a `.purged_version` marker so later
    startup stays O(1). Returns the number of files removed. Unreadable bundles are left in place rather than guessed
    at, and if any unlink fails (e.g. a locked file) the marker remains unwritten so the next authorized prebuild
    retries.
    """
    directory = FG_RESPONSE_FRONTIER_CACHE.directory()
    if not directory.exists():
        return 0
    compatible_versions = FG_RESPONSE_FRONTIER_CACHE.compatible_versions()
    marker_value = "\n".join(compatible_versions)
    marker = directory / _PURGED_VERSION_MARKER
    try:
        if marker.read_text(encoding="utf-8").strip() == marker_value:
            return 0
    except OSError:
        pass
    stale_bundles: list[Path] = []
    for npz in directory.glob("*.npz"):
        try:
            with np.load(npz, allow_pickle=False) as bundle:
                version = str(bundle["version"].item())
        except _UNREADABLE:  # not proven stale: keep it
            continue
        if version not in compatible_versions:
            stale_bundles.append(npz)
    if stale_bundles and not bool(authorize_rotation):
        raise RuntimeError(
            "FG response frontier cache contains "
            f"{len(stale_bundles)} incompatible bundle(s); preserved them because destructive "
            "cache rotation was not explicitly authorized"
        )
    removed = 0
    purge_complete = True
    for npz in stale_bundles:
        try:
            npz.unlink()
            removed += 1
        except FileNotFoundError:
            pass
        except OSError:
            purge_complete = False  # locked/in-use: leave the marker unwritten, retry next prebuild
    if purge_complete:
        try:
            marker.write_text(marker_value, encoding="utf-8")
        except OSError:
            pass
    return removed


_DENSE_RANK_BLOCK_ROWS = 1 << 18


def _dense_rank_pattern_ids_inplace(ids: np.ndarray, pattern_count: int) -> np.ndarray:
    """Rewrite in-range head-pattern IDs in place to their dense rank among the IDs present.

    Returns the sorted used IDs and leaves ``ids`` equal to the int32 inverse -- exactly
    ``np.unique(ids, return_inverse=True)`` -- via a ``pattern_count``-sized presence table instead
    of an N-row sort. ``ids`` must be a contiguous 1-D int32 array; blocks bound the intp index
    temporaries. Out-of-range IDs (a u32 >= 2**31 wraps negative in int32) fail loud."""
    row_count = int(ids.shape[0])
    used = np.zeros(int(pattern_count), dtype=np.bool_)
    for start in range(0, row_count, _DENSE_RANK_BLOCK_ROWS):
        block = ids[start : start + _DENSE_RANK_BLOCK_ROWS]
        if int(block.min()) < 0 or int(block.max()) >= int(pattern_count):
            raise ValueError("FG response surface row references an invalid head-pattern ID")
        used[block] = True
    dense_by_id = np.cumsum(used, dtype=np.int32)
    dense_by_id -= 1
    for start in range(0, row_count, _DENSE_RANK_BLOCK_ROWS):
        block = ids[start : start + _DENSE_RANK_BLOCK_ROWS]
        block[...] = dense_by_id[block]
    return np.flatnonzero(used)


def gather_surface_patterns(
    rows: np.ndarray, patterns: np.ndarray, ranges: Iterable[tuple[int, int]]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """The compact scoring arrays of `ranges` of a bundle's surface rows (its (4, n) row and (10, m) pattern columns):
    ``(surface_pattern_ids, surface_counts, pattern_words, pattern_coeffs)``. Pattern IDs are renumbered densely for
    the gather but row order is untouched, so exact-score ties keep the producer's first-row priority."""
    ranges = tuple((int(start), int(count)) for start, count in ranges)
    row_count = sum(count for _start, count in ranges)
    surface_pattern_ids = np.empty((row_count,), dtype=np.int32)
    surface_counts = np.empty((row_count, 3), dtype=np.int32)
    cursor = 0
    for start, count in ranges:
        if start < 0 or count <= 0 or start + count > int(rows.shape[1]):
            raise ValueError("FG response surface range is outside the bundle's rows")
        surface_pattern_ids[cursor : cursor + count] = rows[0, start : start + count]
        surface_counts[cursor : cursor + count] = rows[1:4, start : start + count].T
        cursor += count
    used = _dense_rank_pattern_ids_inplace(surface_pattern_ids, int(patterns.shape[1]))
    pattern_words, pattern_coeffs = unpack_surface_patterns(patterns[:, used].T)
    return surface_pattern_ids, surface_counts, pattern_words, pattern_coeffs


def _as_uint8_exact(name: str, values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if array.size:
        min_value = int(np.min(array))
        max_value = int(np.max(array))
        info = np.iinfo(np.uint8)
        if min_value < int(info.min) or max_value > int(info.max):
            raise ValueError(f"{name} exceeds persisted uint8 bounds: {min_value}..{max_value}")
    return np.asarray(array, dtype=np.uint8)


def _memory_get(cache_key: tuple) -> FgResponseFrontierResult | None:
    return _geometry_frontier_memory.get(cache_key)


def _frontier_is_complete(frontier: FgResponseFrontierResult | None) -> bool:
    return frontier is not None and bool(frontier.first_frontier)


def _memory_put(cache_key: tuple, frontier: FgResponseFrontierResult) -> None:
    if not frontier.first_frontier:
        raise ValueError("FG response frontier cache requires first-frontier surfaces")
    _geometry_frontier_memory.put(cache_key, frontier)


def reset_fg_response_frontier_payload_cache() -> None:
    for memory in (_geometry_frontier_memory, _payload_memory, _scoring_bundle_memory):
        memory.clear()


def release_fg_response_song_memory(bundle_key: tuple) -> int:
    """Evict every in-memory cache entry for one song's response-frontier surfaces.

    Called once a song's FG scoring is complete: the surface tables and frontiers it loaded are no longer needed for
    the rest of this run, so drop them from every memory tier instead of letting them sit until the tier's
    entry-count LRU evicts them (they would trip the memory guard after a few dozen songs). Lossless: any later
    access reloads the bundle from disk.

    Every cache keys its entries as ``(version, song_key, *ref_axes, <suffix>)`` (bundle marker, stat key, or stat-key
    tuple); the shared per-song prefix is the bundle key without its trailing marker. Returns the number of entries
    removed.
    """
    if not bundle_key:
        return 0
    prefix = tuple(bundle_key[:-1])
    if not prefix:
        return 0
    return sum(
        memory.pop_prefix(prefix) for memory in (_scoring_bundle_memory, _geometry_frontier_memory, _payload_memory)
    )


def _save_payload(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    from .response_cache_serde import _pack_frontiers

    frontiers = payload.frontiers
    frontier_id_by_object = {id(frontier): idx for idx, frontier in enumerate(frontiers)}
    sorted_items = sorted(payload.frontier_by_key.items())
    packed_frontiers = _pack_frontiers(frontiers)
    head_len = min(int(payload.total_notes), 100)
    # Pattern identity is established from every exact mask word before coefficient work: head coefficients depend
    # only on those words and head_len, so they are computed once per pattern instead of once per row.
    rows, pattern_words = intern_surface_row_words(
        np.ascontiguousarray(np.asarray(packed_frontiers["first_surface_pool"], dtype=np.uint32))
    )
    patterns = pack_surface_patterns(pattern_words, surface_head_coeffs(pattern_words, head_len=head_len))
    stat_keys = np.asarray([key for key, _frontier in sorted_items], dtype=np.int32)
    arrays = {
        "version": np.asarray(FG_RESPONSE_FRONTIER_CACHE.version()),
        "stat_keys": np.asfortranarray(_as_uint8_exact("FG response stat keys", stat_keys)),
        "frontier_ids": np.asarray(
            [frontier_id_by_object[id(frontier)] for _key, frontier in sorted_items], dtype=np.int32
        ),
        "raw_fill_by_ff": np.asarray(payload.raw_fill_by_ff, dtype=np.float64),
        "non_fever_base_by_ff": np.asarray(payload.non_fever_base_by_ff, dtype=np.int32),
        "real_time_by_ft": np.asarray(payload.real_time_by_ft, dtype=np.float64),
        "total_notes": np.asarray(int(payload.total_notes), dtype=np.int32),
        "long_notes": np.asarray(int(payload.long_notes), dtype=np.int32),
        "use_forced_great_timing": np.asarray(int(payload.use_forced_great_timing), dtype=np.int8),
        "first_surface_head_len": _as_uint8_exact(
            "FG response first surface head length", np.asarray(head_len, dtype=np.int32)
        ),
        "frontier_meta": np.asfortranarray(np.asarray(packed_frontiers["frontier_meta"], dtype=np.int32)),
        "first_offsets": np.asarray(packed_frontiers["first_offsets"], dtype=np.int32),
        "first_counts": np.asarray(packed_frontiers["first_counts"], dtype=np.int32),
        "surface_rows": _byte_planes(rows),
        "surface_patterns": _byte_planes(patterns),
    }
    write_atomically(FG_RESPONSE_FRONTIER_CACHE.file_path(cache_key), lambda tmp: _save_npz_fast_compressed(tmp, arrays))


def _save_npz_fast_compressed(path: Path, arrays: dict[str, np.ndarray]) -> None:
    with zipfile.ZipFile(
        path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=int(_NPZ_FAST_COMPRESS_LEVEL),
        allowZip64=True,
    ) as archive:
        for name, array in arrays.items():
            with archive.open(f"{name}.npy", mode="w", force_zip64=True) as handle:
                np_format.write_array(handle, np.asanyarray(array), allow_pickle=False)


def _read_bundle(path: Path) -> dict[str, np.ndarray]:
    """Every array of a bundle file, its surface tables decoded to (columns, rows) uint32."""
    with np.load(path, allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files}
    for name in _SURFACE_TABLES:
        arrays[name] = _columns(arrays[name])
    return arrays


def read_compatible_bundle(cache_key: tuple) -> dict[str, np.ndarray] | None:
    """The arrays of the key's bundle file (`_read_bundle`); None when no file of a compatible version exists."""
    path = FG_RESPONSE_FRONTIER_CACHE.readable_path(cache_key)
    if path is None:
        return None
    arrays = _read_bundle(path)
    if str(arrays["version"].item()) not in FG_RESPONSE_FRONTIER_CACHE.compatible_versions():
        return None
    return arrays


def _load_payload(cache_key: tuple) -> FgResponseFrontierCachePayload | None:
    """The key's bundle as a payload; None when there is none. An unreadable file is deleted (it is rebuilt)."""
    from .response_cache_serde import _unpack_frontiers

    try:
        arrays = read_compatible_bundle(cache_key)
        if arrays is None:
            return None
        frontiers = _unpack_frontiers(arrays)
        frontier_by_key = {
            _normalize_stat_key((int(key_row[0]), int(key_row[1]))): frontiers[int(frontier_idx)]
            for key_row, frontier_idx in zip(np.asarray(arrays["stat_keys"], dtype=np.int32), arrays["frontier_ids"])
        }
        return FgResponseFrontierCachePayload(
            frontier_by_key=frontier_by_key,
            raw_fill_by_ff=np.asarray(arrays["raw_fill_by_ff"], dtype=np.float64),
            non_fever_base_by_ff=np.asarray(arrays["non_fever_base_by_ff"], dtype=np.int32),
            real_time_by_ft=np.asarray(arrays["real_time_by_ft"], dtype=np.float64),
            total_notes=int(arrays["total_notes"].item()),
            long_notes=int(arrays["long_notes"].item()),
            use_forced_great_timing=bool(int(arrays["use_forced_great_timing"].item())),
        )
    except _UNREADABLE:  # a damaged cache file is rebuilt, never served
        path = FG_RESPONSE_FRONTIER_CACHE.serving_path(cache_key)
        logger.warning("[FGResponseCache] unreadable bundle %s; it is deleted and rebuilt", path, exc_info=True)
        path.unlink(missing_ok=True)
        return None


def _payload_file_is_complete(path: Path, keys: Iterable[tuple[int, int]]) -> bool:
    """A bundle of a compatible version with every member that covers `keys` (an unreadable file is deleted)."""
    requested = set(normalize_fg_response_stat_keys(keys))
    if not path.exists():
        return False
    try:
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != _BUNDLE_ARRAY_NAMES:
                return False
            if str(data["version"].item()) not in FG_RESPONSE_FRONTIER_CACHE.compatible_versions():
                return False
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
    except _UNREADABLE:  # a damaged cache file is rebuilt, never served
        logger.warning("[FGResponseCache] unreadable bundle %s; it is deleted and rebuilt", path, exc_info=True)
        path.unlink(missing_ok=True)
        return False
    return requested <= {_normalize_stat_key((int(row[0]), int(row[1]))) for row in stat_keys}


def fg_response_cache_file_is_complete(cache_file: str | Path) -> bool:
    """A complete bundle of a compatible version covering every FT/FF stat key."""
    return _payload_file_is_complete(Path(cache_file), all_response_stat_keys())


FG_RESPONSE_FRONTIER_CACHE = FrontierCache(
    name="fg_response",
    log_label="[FGResponseCache]",
    directory=_fg_response_disk_cache_dir,
    file_path=_fg_response_disk_cache_path,
    version=_fg_response_cache_version,
    predecessors=_EXACT_COMPATIBLE_PREDECESSOR_VERSIONS,
    is_complete=fg_response_cache_file_is_complete,
    song_key=fg_response_frontier_bundle_cache_key,
    manifest_name="fg_response_manifest_v1.json",
    manifest_version_field="cache_version",
    manifest_stat_signature=bytes(array_sig16(np.asarray(all_response_stat_keys(), dtype=np.int32).reshape(-1))).hex(),
)


def _payload_disk_is_complete(cache_key: tuple, keys: Iterable[tuple[int, int]]) -> bool:
    return _payload_file_is_complete(FG_RESPONSE_FRONTIER_CACHE.serving_path(cache_key), keys)
