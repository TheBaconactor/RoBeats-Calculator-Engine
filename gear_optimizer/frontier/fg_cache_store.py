"""The FG response-frontier cache on disk: one .npz bundle per song timing and stat curves.

A bundle holds the frontier metadata and two surface tables. rows (n, 4) uint32: one head-pattern ID and three body
counts per logical surface row, in producer order. patterns (m, 10) uint32: each distinct head pattern's eight
fever/Great mask words and its four uint16 head coefficients packed into two words. A table is stored column by
column, each column's little-endian bytes as four byte planes (plane 4j + b holds byte b of column j), which the
archive's deflate shrinks to ~9% of the raw table (row-major bytes: ~26%). A reader decodes a whole bundle at once,
so its metadata and tables always come from one write.
"""

from __future__ import annotations

import logging
import tokenize
import zipfile
import zlib
from pathlib import Path

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.frontier.cache import FrontierCache, write_atomically
from gear_optimizer.rules import MAX_STAT

from .fg_cache_keys import fg_response_cache_version, fg_response_disk_cache_dir, fg_response_frontier_bundle_cache_key
from .fg_cache_serde import bundle_arrays, byte_plane_columns, unpack_frontiers, write_bundle_npz
from .fg_cache_types import FgResponseFrontierCachePayload, all_response_stat_keys

logger = logging.getLogger(__name__)

# What reading a damaged or truncated bundle file raises: mostly a BadZipFile (a bad CRC is one); a broken deflate
# stream is a zlib.error, a broken member header a ValueError, a TokenError or a NotImplementedError.
_UNREADABLE = (OSError, ValueError, KeyError, IndexError, EOFError, zipfile.BadZipFile, zlib.error, tokenize.TokenError,
               NotImplementedError)
_SURFACE_TABLES = ("surface_rows", "surface_patterns")
# The members of a bundle file, in the order they are written.
_BUNDLE_ARRAY_NAMES = (
    "version", "stat_keys", "frontier_ids", "raw_fill_by_ff", "non_fever_base_by_ff", "real_time_by_ft", "total_notes",
    "long_notes", "use_forced_great_timing", "first_surface_head_len", "frontier_meta", "first_offsets", "first_counts",
    *_SURFACE_TABLES,
)

# Exact cache compatibility is explicit and non-transitive: a version reads an older version's bundles only when it lists
# that version here, after a byte gate proved the persisted bundles identical. The version history is in git.
_EXACT_COMPATIBLE_PREDECESSOR_VERSIONS: dict[str, tuple[str, ...]] = {
    # Giving the producer's host layer records and one precompute changed no frontier: the gate (16 charts), the 40-chart
    # sample (2,160 arrays) and the whole catalog (2,287 charts, both timing modes) are identical to the 74ca016777d4
    # producer's. Evidence in workspace/_engine_round3_2026-11-10.
    "fg-response-frontier-visible-first-v32+logic-980404610015": (
        "fg-response-frontier-visible-first-v32+logic-74ca016777d4",
    ),
    # The frontier kernels organised by activation and the bundle writer moved into fg_cache_serde changed no stored
    # byte: the gate (16 charts), the 40-chart sample (2,160 arrays and members) and the whole catalog (2,287 charts,
    # both timing modes) are identical to the 980404610015 and 74ca016777d4 producers'. Evidence in
    # workspace/_engine_round3_2026-11-10.
    "fg-response-frontier-visible-first-v32+logic-5ed7198b067a": (
        "fg-response-frontier-visible-first-v32+logic-980404610015",
        "fg-response-frontier-visible-first-v32+logic-74ca016777d4",
    ),
}


_PURGED_VERSION_MARKER = ".purged_version"


def purge_stale_version_cache_files(*, authorize_rotation: bool = False) -> int:
    """Delete the bundles no version of the current lineage reads; returns how many.

    They are dead weight (no reader derives their names), but deleting a provisioned pool is an explicit production
    rotation, never routine maintenance: without `authorize_rotation` any such bundle raises before a byte is unlinked.
    The `.purged_version` marker lists the versions every bundle had when the directory was last swept. While the
    lineage still reads all of them no bundle can be stale, so nothing is opened: a restart, and a start after a
    ratified version change, cost one small read. Any other marker (or none) sweeps: every bundle's version is read.
    An unreadable bundle is kept rather than guessed at, and if an unlink fails (a locked file) the marker stays as it
    is, so the next prebuild sweeps again.
    """
    directory = FG_RESPONSE_FRONTIER_CACHE.directory()
    if not directory.exists():
        return 0
    compatible_versions = FG_RESPONSE_FRONTIER_CACHE.compatible_versions()
    marker = directory / _PURGED_VERSION_MARKER
    try:
        swept_versions = marker.read_text(encoding="utf-8").split()
    except OSError:
        swept_versions = []
    stale_bundles: list[Path] = []
    if not swept_versions or not set(swept_versions) <= set(compatible_versions):
        for npz in directory.glob("*.npz"):
            try:
                with np.load(npz, allow_pickle=False) as bundle:
                    version = str(bundle["version"].item())
            except _UNREADABLE:  # not proven stale: keep it
                continue
            if version not in compatible_versions:
                stale_bundles.append(npz)
    if stale_bundles and not authorize_rotation:
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
    if purge_complete and swept_versions != list(compatible_versions):
        try:
            marker.write_text("\n".join(compatible_versions), encoding="utf-8")
        except OSError:
            pass
    return removed


def save_payload(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    """Write the payload as the key's bundle file (atomically: readers see the old file or the whole new one)."""
    arrays = bundle_arrays(payload, FG_RESPONSE_FRONTIER_CACHE.version())
    write_atomically(FG_RESPONSE_FRONTIER_CACHE.file_path(cache_key), lambda tmp: write_bundle_npz(tmp, arrays))


def read_bundle(path: Path) -> dict[str, np.ndarray]:
    """Every array of a bundle file, its surface tables decoded to (columns, rows) uint32."""
    with np.load(path, allow_pickle=False) as data:
        arrays = {name: data[name] for name in data.files}
    for name in _SURFACE_TABLES:
        arrays[name] = byte_plane_columns(arrays[name])
    return arrays


def read_compatible_bundle(cache_key: tuple) -> dict[str, np.ndarray] | None:
    """The arrays of the key's bundle file (`read_bundle`); None when no file of a compatible version exists."""
    path = FG_RESPONSE_FRONTIER_CACHE.readable_path(cache_key)
    if path is None:
        return None
    arrays = read_bundle(path)
    if str(arrays["version"].item()) not in FG_RESPONSE_FRONTIER_CACHE.compatible_versions():
        return None
    return arrays


def _delete_unreadable(path: Path) -> None:
    """A damaged bundle file is rebuilt, never served."""
    logger.warning("[FGResponseCache] unreadable bundle %s; it is deleted and rebuilt", path, exc_info=True)
    path.unlink(missing_ok=True)


def load_payload(cache_key: tuple) -> FgResponseFrontierCachePayload | None:
    """The key's bundle as a payload; None when there is none. An unreadable file is deleted (it is rebuilt)."""
    try:
        arrays = read_compatible_bundle(cache_key)
        if arrays is None:
            return None
        frontiers = unpack_frontiers(arrays)
        frontier_by_key = {
            tuple(key): frontiers[frontier_idx]
            for key, frontier_idx in zip(arrays["stat_keys"].tolist(), arrays["frontier_ids"].tolist(), strict=True)
        }
        return FgResponseFrontierCachePayload(
            frontier_by_key=frontier_by_key,
            raw_fill_by_ff=arrays["raw_fill_by_ff"],
            non_fever_base_by_ff=arrays["non_fever_base_by_ff"],
            real_time_by_ft=arrays["real_time_by_ft"],
            total_notes=int(arrays["total_notes"]),
            long_notes=int(arrays["long_notes"]),
            use_forced_great_timing=bool(arrays["use_forced_great_timing"]),
        )
    except _UNREADABLE:
        _delete_unreadable(FG_RESPONSE_FRONTIER_CACHE.serving_path(cache_key))
        return None


def bundle_file_holds(path: Path, keys: np.ndarray) -> bool:
    """Whether `path` is a bundle of a compatible version with every member that holds the stat keys `keys` (an
    unreadable file is deleted)."""
    if not path.exists():
        return False
    try:
        with np.load(path, allow_pickle=False) as data:
            if set(data.files) != set(_BUNDLE_ARRAY_NAMES):
                return False
            if str(data["version"].item()) not in FG_RESPONSE_FRONTIER_CACHE.compatible_versions():
                return False
            held = data["stat_keys"].astype(np.intp)
    except _UNREADABLE:
        _delete_unreadable(path)
        return False
    present = np.zeros((MAX_STAT + 1, MAX_STAT + 1), dtype=np.bool_)
    present[held[:, 0], held[:, 1]] = True
    return bool(present[keys[:, 0], keys[:, 1]].all())


def fg_response_cache_file_is_complete(cache_file: str | Path) -> bool:
    """A complete bundle of a compatible version holding every FT/FF stat key."""
    return bundle_file_holds(Path(cache_file), all_response_stat_keys())


FG_RESPONSE_FRONTIER_CACHE = FrontierCache(
    name="fg_response",
    log_label="[FGResponseCache]",
    directory=fg_response_disk_cache_dir,
    version=fg_response_cache_version,
    predecessors=_EXACT_COMPATIBLE_PREDECESSOR_VERSIONS,
    is_complete=fg_response_cache_file_is_complete,
    song_key=fg_response_frontier_bundle_cache_key,
    manifest_name="fg_response_manifest_v1.json",
    manifest_version_field="cache_version",
    manifest_stat_signature=bytes(array_sig16(all_response_stat_keys().reshape(-1))).hex(),
)
