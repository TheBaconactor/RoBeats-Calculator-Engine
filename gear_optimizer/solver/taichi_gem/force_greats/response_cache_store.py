from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import uuid
import zipfile
from pathlib import Path
from typing import Iterable

import numpy as np
from numpy.lib import format as np_format

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.frontier_cache import FrontierCache, MemoryLru, write_atomically

from .response_cache_keys import (
    _fg_response_disk_cache_dir,
    _fg_response_disk_cache_path,
    _fg_response_cache_version,
    fg_response_frontier_bundle_cache_key,
)
from .response_cache_patterns import (
    SURFACE_PATTERN_COLUMNS,
    SURFACE_ROW_COLUMNS,
    expand_surface_rows,
    intern_surface_row_words,
    pack_surface_patterns,
    surface_head_coeffs,
    unpack_surface_patterns,
)
from .response_cache_types import (
    _SCORING_BUNDLE_ARRAY_NAMES,
    _SURFACE_BUNDLE_PATH_ARRAY_NAME,
    _SURFACE_GENERATION_ARRAY_NAME,
    FgResponseFrontierCachePayload,
    FgResponseFrontierScoringBundle,
    _normalize_stat_key,
    all_response_stat_keys,
    normalize_fg_response_stat_keys,
)
from .response_types import FgResponseFrontierResult

logger = logging.getLogger(__name__)

# The memory tiers, keyed like the files (version, song key, FT/FF axes signatures, then a stat key, a stat-key
# tuple or the bundle marker): frontiers materialized per stat key, merged bundles and request payloads of builds,
# bundles' slim metadata arrays, and their scoring views. A bundle's metadata is hydrated at prep and read again at
# its GA turn; entries are ~0.2-1MB (metadata members only, never the surface pools).
_geometry_frontier_memory: MemoryLru[FgResponseFrontierResult] = MemoryLru(4096)
_payload_memory: MemoryLru[FgResponseFrontierCachePayload] = MemoryLru(8)
_bundle_array_memory: MemoryLru[dict[str, np.ndarray]] = MemoryLru(40)
_scoring_bundle_memory: MemoryLru[FgResponseFrontierScoringBundle] = MemoryLru(40)
_RESPONSE_BUNDLE_BUILD_PARALLELISM = 1
_response_bundle_build_slots = threading.BoundedSemaphore(int(_RESPONSE_BUNDLE_BUILD_PARALLELISM))
_NPZ_FAST_COMPRESS_LEVEL = 1
# Scoring surfaces live in two uncompressed, C-order, memmap-able sidecars next to the bundle
# .npz. Every logical surface row stores one exact head-pattern ID plus its three body counts;
# every distinct head pattern stores the eight fever/Great mask words plus four uint16 head
# coefficients packed into two uint32 words. The reader expands only requested row ranges, so the
# scorer still sees the canonical 11-word rows and four coefficients while disk traffic scales
# with the interned representation. IDs are uint32 for every chart -- no size-dependent format.
_SURFACE_ROW_SIDECAR_SUFFIX = ".surf_rows.npy"
_SURFACE_PATTERN_SIDECAR_SUFFIX = ".surf_patterns.npy"
_FILESYSTEM_COMPRESSION_MIN_BYTES = 4096
_MACOS_COMPRESSION_BATCH_FILES = 32
_MACOS_COMPRESSION_STAGING_DIR = ".macos_hfs_compression_staging"
# Cleanup-only names from V29. They are never read: the V30 version gate requires the compact
# row/pattern format. The stale-version sweeper must still remove them when it deletes a V29 bundle,
# otherwise every deliberate rotation strands the largest files from the old full pool.
_OBSOLETE_SURFACE_SIDECAR_SUFFIXES = (".surf_pool.npy", ".surf_coeffs.npy")

# Exact cache compatibility is explicit and non-transitive: a version reads an older version's bundles only when it lists
# that version here, after a byte gate proved the persisted bundles identical. The version history is in git.
_EXACT_COMPATIBLE_PREDECESSOR_VERSIONS: dict[str, tuple[str, ...]] = {}


class FgResponseSurfaceSidecarError(RuntimeError):
    """A current-version bundle .npz exists but its uncompressed surface sidecar is missing or
    disagrees in shape/dtype/row-count. This is a desync (e.g. interrupted migration), not a cache
    miss -- it must surface loudly so the human re-runs the re-pack, never silently rebuild."""


_UNSPECIFIED_SURFACE_GENERATION = object()


def _normalize_surface_generation(value: object) -> str | None:
    if value is None:
        return None
    array = np.asarray(value)
    if int(array.size) != 1:
        raise FgResponseSurfaceSidecarError("FG response frontier surface generation metadata is invalid")
    generation = str(array.item())
    if not generation:
        return None
    try:
        normalized = uuid.UUID(hex=generation).hex
    except (AttributeError, ValueError) as exc:
        raise FgResponseSurfaceSidecarError(
            "FG response frontier surface generation metadata is invalid"
        ) from exc
    if normalized != generation:
        raise FgResponseSurfaceSidecarError("FG response frontier surface generation metadata is invalid")
    return generation


def _surface_generation_from_bundle_data(data) -> str | None:
    if _SURFACE_GENERATION_ARRAY_NAME not in data.files:
        return None
    return _normalize_surface_generation(data[_SURFACE_GENERATION_ARRAY_NAME])


def _surface_generation_from_bundle_path(bundle_path: Path) -> str | None:
    path = Path(bundle_path)
    if not path.is_file():
        return None
    with np.load(path, allow_pickle=False) as data:
        return _surface_generation_from_bundle_data(data)


def _surface_sidecar_paths(
    bundle_path: Path,
    *,
    generation: str | None | object = _UNSPECIFIED_SURFACE_GENERATION,
) -> tuple[Path, Path]:
    """Return the immutable sidecars referenced by one bundle metadata generation.

    Existing V30/V31 bundles have no generation member and retain their fixed legacy sidecars.
    """
    base = Path(bundle_path)
    if base.suffix != ".npz":
        raise ValueError(f"FG response frontier bundle path must be a .npz: {base}")
    stem = base.name[: -len(".npz")]
    if generation is _UNSPECIFIED_SURFACE_GENERATION:
        normalized_generation = _surface_generation_from_bundle_path(base)
    else:
        normalized_generation = _normalize_surface_generation(generation)
    sidecar_stem = stem if normalized_generation is None else f"{stem}.{normalized_generation}"
    return (
        base.with_name(f"{sidecar_stem}{_SURFACE_ROW_SIDECAR_SUFFIX}"),
        base.with_name(f"{sidecar_stem}{_SURFACE_PATTERN_SIDECAR_SUFFIX}"),
    )


def _stale_surface_sidecar_paths(bundle_path: Path) -> tuple[Path, ...]:
    """All known sidecars to delete with a stale bundle; no obsolete format is readable."""
    base = Path(bundle_path)
    stem = base.name[: -len(".npz")]
    current = (
        base.with_name(f"{stem}{_SURFACE_ROW_SIDECAR_SUFFIX}"),
        base.with_name(f"{stem}{_SURFACE_PATTERN_SIDECAR_SUFFIX}"),
        *base.parent.glob(f"{stem}.*{_SURFACE_ROW_SIDECAR_SUFFIX}"),
        *base.parent.glob(f"{stem}.*{_SURFACE_PATTERN_SIDECAR_SUFFIX}"),
    )
    obsolete = tuple(base.with_name(f"{stem}{suffix}") for suffix in _OBSOLETE_SURFACE_SIDECAR_SUFFIXES)
    return tuple(dict.fromkeys((*current, *obsolete)))


def _surface_sidecar_paths_for_key(
    cache_key: tuple,
    *,
    generation: str | None | object = _UNSPECIFIED_SURFACE_GENERATION,
    bundle_path: str | Path | None = None,
) -> tuple[Path, Path]:
    resolved_path = FG_RESPONSE_FRONTIER_CACHE.serving_path(cache_key) if bundle_path is None else Path(bundle_path)
    return _surface_sidecar_paths(resolved_path, generation=generation)


def _remove_fg_response_bundle_files(bundle_path: Path) -> int:
    removed = 0
    for path in (bundle_path, *_stale_surface_sidecar_paths(bundle_path)):
        if not path.exists():
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue
        removed += 1
    return removed


def _surface_sidecar_files(directory: Path) -> tuple[Path, ...]:
    rows = directory.glob(f"*{_SURFACE_ROW_SIDECAR_SUFFIX}")
    patterns = directory.glob(f"*{_SURFACE_PATTERN_SIDECAR_SUFFIX}")
    return tuple(sorted((*rows, *patterns), key=lambda path: path.name))


def _file_allocated_bytes(path: Path) -> int:
    stat = path.stat()
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        get_compressed_size = ctypes.windll.kernel32.GetCompressedFileSizeW
        get_compressed_size.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
        get_compressed_size.restype = wintypes.DWORD
        high = wintypes.DWORD(0)
        low = int(get_compressed_size(str(path), ctypes.byref(high)))
        return (int(high.value) << 32) | low
    blocks = getattr(stat, "st_blocks", None)
    if blocks is not None:
        return int(blocks) * 512
    return int(stat.st_size)


def _sidecar_needs_filesystem_compression(path: Path) -> bool:
    try:
        logical = int(path.stat().st_size)
        if logical < _FILESYSTEM_COMPRESSION_MIN_BYTES:
            return False
        return _file_allocated_bytes(path) >= logical
    except OSError:
        return False


def _compress_cache_dir_sidecars_windows(directory: Path) -> None:
    try:
        result = subprocess.run(
            ["compact", "/c", "/exe:XPRESS16K", "/s:" + str(directory)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3600,
            check=False,
        )
        if int(result.returncode) != 0:
            logger.warning("FG cache XPRESS16K compression exited %s", int(result.returncode))
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("FG cache XPRESS16K compression failed: %s", exc)


def _compress_cache_dir_sidecars_macos(directory: Path) -> None:
    candidates = tuple(
        path for path in _surface_sidecar_files(directory) if _sidecar_needs_filesystem_compression(path)
    )
    if not candidates:
        return
    staging = directory / _MACOS_COMPRESSION_STAGING_DIR
    try:
        shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir()
        for start in range(0, len(candidates), _MACOS_COMPRESSION_BATCH_FILES):
            batch = candidates[start : start + _MACOS_COMPRESSION_BATCH_FILES]
            result = subprocess.run(
                [
                    "/usr/bin/ditto",
                    "--hfsCompression",
                    "--nocache",
                    *(str(path) for path in batch),
                    str(staging),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3600,
                check=False,
            )
            if int(result.returncode) != 0:
                logger.warning("FG cache APFS/HFS+ compression exited %s", int(result.returncode))
                return
            staged_batch = tuple(staging / path.name for path in batch)
            for source, staged in zip(batch, staged_batch, strict=True):
                if not staged.is_file() or int(staged.stat().st_size) != int(source.stat().st_size):
                    logger.warning("FG cache APFS/HFS+ copy validation failed: %s", source)
                    return
            compressed = [
                (source, staged)
                for source, staged in zip(batch, staged_batch, strict=True)
                if not _sidecar_needs_filesystem_compression(staged)
            ]
            if not compressed:
                # ditto wrote plain copies (macOS 27's ditto ignores --hfsCompression): swapping them in would
                # rewrite every sidecar on each prebuild (20.8 GiB per timing mode on the service) for nothing.
                logger.warning("FG cache APFS/HFS+ compression had no effect; sidecars stay uncompressed")
                return
            for source, staged in compressed:
                os.replace(staged, source)
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("FG cache APFS/HFS+ compression failed: %s", exc)
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def compress_cache_dir_sidecars() -> None:
    """Losslessly compress exact sidecars while preserving the mmap-visible file bytes.

    Windows uses one NTFS WOF XPRESS16K pass. macOS copies uncompressed sidecars in bounded batches
    through ``ditto --hfsCompression`` and atomically replaces each original whose copy came out
    compressed (a batch with none stops the pass); APFS/HFS+ then decompresses pages transparently for
    ``np.load(mmap_mode="r")``. Unsupported platforms are a
    no-op because no general filesystem-transparent compressor exists there. This is an external
    filesystem boundary and never changes cache semantics or the logic fingerprint.
    """
    directory = FG_RESPONSE_FRONTIER_CACHE.directory()
    if not directory.exists():
        return
    if sys.platform == "win32":
        _compress_cache_dir_sidecars_windows(directory)
    elif sys.platform == "darwin":
        _compress_cache_dir_sidecars_macos(directory)


_PURGED_VERSION_MARKER = ".purged_version"


def purge_stale_version_cache_files(*, authorize_rotation: bool = False) -> int:
    """Delete bundles outside the current exact compatibility lineage.

    Versions outside the explicit compatible set are dead weight because every reader rejects them,
    but deleting a provisioned full pool is an explicit production rotation, never routine startup
    maintenance. Without ``authorize_rotation`` this function detects any incompatible bundle and
    fails loudly before unlinking a byte. An authorized prebuild sweeps once per compatibility-lineage
    change, guarded by a `.purged_version` marker so later startup stays O(1). Returns the number of
    files removed. External filesystem boundary: unreadable/corrupt bundles are left in place rather
    than guessed at, and if any unlink fails (e.g. a locked file) the marker remains unwritten so the
    next authorized prebuild retries instead of stranding the file.
    """
    directory = FG_RESPONSE_FRONTIER_CACHE.directory()
    if not directory.exists():
        return 0
    compatible_versions = FG_RESPONSE_FRONTIER_CACHE.compatible_versions()
    compatible = frozenset(compatible_versions)
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
                version = str(bundle["version"].item()) if "version" in bundle.files else None
        except Exception:
            # Any unreadable/corrupt bundle (bad zip, corrupt member, IO error): keep it rather than
            # crash the whole sweep. This is the documented FS boundary, matching the bundle readers.
            version = None
        if version is None or version in compatible:
            continue
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
        for stale in (npz, *_stale_surface_sidecar_paths(npz)):
            try:
                stale.unlink()
                removed += 1
            except FileNotFoundError:
                pass  # already absent: nothing to remove, not a retry-worthy failure
            except OSError:
                purge_complete = False  # locked/in-use: leave marker unwritten, retry next prebuild
    if purge_complete:
        try:
            marker.write_text(marker_value, encoding="utf-8")
        except OSError:
            pass
    return removed


def _save_surface_sidecar_atomic(path: Path, array: np.ndarray) -> None:
    """Write `array` atomically as an uncompressed C-order .npy.

    Uncompressed at the numpy layer so the reader can `np.load(..., mmap_mode="r")` and page rows
    lazily; on-disk size is reclaimed by the bulk NTFS pass at prebuild-end (see
    `compress_cache_dir_sidecars`), which keeps the bytes small while preserving the memmap path.
    """
    contiguous = np.ascontiguousarray(array)

    def write(tmp: Path) -> None:
        with open(tmp, "wb") as handle:
            np_format.write_array(handle, contiguous, allow_pickle=False)

    write_atomically(path, write)


def _surface_sidecar_header(path: Path) -> tuple[tuple[int, ...], np.dtype] | None:
    try:
        with open(path, "rb") as handle:
            version = np_format.read_magic(handle)
            if version == (1, 0):
                shape, _fortran_order, dtype = np_format.read_array_header_1_0(handle)
            elif version == (2, 0):
                shape, _fortran_order, dtype = np_format.read_array_header_2_0(handle)
            else:
                return None
    except Exception:
        return None
    return tuple(int(dim) for dim in shape), np.dtype(dtype)


def _open_surface_sidecar_memmap(path: Path, *, columns: int, dtype: np.dtype, row_count: int) -> np.ndarray:
    """Open a surface sidecar read-only memmap and fail loud on any shape/dtype/row-count drift."""
    if not path.exists():
        raise FgResponseSurfaceSidecarError(f"FG response frontier surface sidecar is missing: {path}")
    memmap = np.load(path, mmap_mode="r", allow_pickle=False)
    if int(memmap.ndim) != 2 or int(memmap.shape[1]) != int(columns):
        raise FgResponseSurfaceSidecarError(f"FG response frontier surface sidecar has invalid shape: {path}")
    if memmap.dtype != np.dtype(dtype):
        raise FgResponseSurfaceSidecarError(f"FG response frontier surface sidecar has invalid dtype: {path}")
    if int(memmap.shape[0]) != int(row_count):
        raise FgResponseSurfaceSidecarError(
            "FG response frontier surface sidecar row count disagrees with bundle metadata: "
            f"{int(memmap.shape[0])} != {int(row_count)} ({path})"
        )
    return memmap


def _gather_surface_ranges(
    memmap: np.ndarray,
    *,
    ranges: tuple[tuple[int, int], ...],
    out: np.ndarray,
) -> None:
    """Slice-copy each [start, start+count) row block out of the memmap into `out`, range order preserved."""
    row_count = int(memmap.shape[0])
    out_cursor = 0
    for start, count in ranges:
        end = int(start) + int(count)
        if end > row_count:
            raise ValueError("FG response surface range exceeds cached rows")
        out[out_cursor : out_cursor + int(count)] = memmap[int(start) : end]
        out_cursor += int(count)
    if out_cursor != int(out.shape[0]):
        raise ValueError("FG response surface gather produced the wrong row count")


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


def _as_uint8_exact(name: str, values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if array.size:
        min_value = int(np.min(array))
        max_value = int(np.max(array))
        info = np.iinfo(np.uint8)
        if min_value < int(info.min) or max_value > int(info.max):
            raise ValueError(f"{name} exceeds persisted uint8 bounds: {min_value}..{max_value}")
    return np.asarray(array, dtype=np.uint8)


def _persisted_packed_frontier_metadata(
    packed_frontiers: dict[str, np.ndarray],
    *,
    surface_row_count: int,
    surface_pattern_count: int,
) -> dict[str, np.ndarray]:
    """Slim-.npz metadata for a packed bundle. Surfaces live in the sidecars, not here.

    The explicit row/pattern counts pin both sidecar shapes so the reader can fail loud on any
    sidecar/npz desync without guessing from IDs or per-frontier offsets.
    """
    return {
        "frontier_meta": np.asfortranarray(np.asarray(packed_frontiers["frontier_meta"], dtype=np.int32)),
        "first_offsets": np.asarray(packed_frontiers["first_offsets"], dtype=np.int32),
        "first_counts": np.asarray(packed_frontiers["first_counts"], dtype=np.int32),
        "first_surface_row_count": np.asarray(int(surface_row_count), dtype=np.int64),
        "first_surface_pattern_count": np.asarray(int(surface_pattern_count), dtype=np.int64),
    }


def _memory_get(cache_key: tuple) -> FgResponseFrontierResult | None:
    return _geometry_frontier_memory.get(cache_key)


def _frontier_is_complete(frontier: FgResponseFrontierResult | None) -> bool:
    return frontier is not None and bool(frontier.first_frontier)


def _memory_put(cache_key: tuple, frontier: FgResponseFrontierResult) -> None:
    if not frontier.first_frontier:
        raise ValueError("FG response frontier cache requires first-frontier surfaces")
    _geometry_frontier_memory.put(cache_key, frontier)


def reset_fg_response_frontier_payload_cache() -> None:
    for memory in (_geometry_frontier_memory, _payload_memory, _bundle_array_memory, _scoring_bundle_memory):
        memory.clear()


def release_fg_response_song_memory(bundle_key: tuple) -> int:
    """Evict every in-memory cache entry for one song's response-frontier surfaces.

    Called once a song's FG scoring is complete: the ~0.5-1.5 GB surface pool it loaded is no
    longer needed for the rest of this run, so drop it from every memory tier instead of letting
    it sit until the tier's entry-count LRU evicts it.
    Without this the surfaces accumulate one-per-scored-song and
    trip the memory guard after only a few dozen songs. Lossless: any later access rebuilds from
    the on-disk bundle.

    Every cache keys its entries as ``(version, song_key, *ref_axes, <suffix>)`` (bundle marker,
    stat key, or stat-key tuple); the shared per-song prefix is the bundle key without its
    trailing marker, so match on that to sweep the scoring bundle, slim metadata, frontier and
    payload tiers together. Returns the number of entries removed.
    """
    if not bundle_key:
        return 0
    prefix = tuple(bundle_key[:-1])
    if not prefix:
        return 0
    return sum(
        memory.pop_prefix(prefix)
        for memory in (_scoring_bundle_memory, _bundle_array_memory, _geometry_frontier_memory, _payload_memory)
    )


def _save_payload(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    from .response_cache_serde import _pack_frontiers

    path = FG_RESPONSE_FRONTIER_CACHE.file_path(cache_key)
    surface_generation = uuid.uuid4().hex
    row_sidecar, pattern_sidecar = _surface_sidecar_paths(path, generation=surface_generation)
    frontiers = payload.frontiers
    frontier_id_by_object = {id(frontier): idx for idx, frontier in enumerate(frontiers)}
    sorted_items = sorted(payload.frontier_by_key.items())
    packed_frontiers = _pack_frontiers(frontiers)
    first_surface_pool = np.ascontiguousarray(
        np.asarray(packed_frontiers["first_surface_pool"], dtype=np.uint32)
    )
    surface_row_count = int(first_surface_pool.shape[0])
    stat_keys = np.asarray([key for key, _frontier in sorted_items], dtype=np.int32)
    first_surface_head_len = min(int(payload.total_notes), 100)
    # Pattern identity is established from every exact mask word before coefficient work.
    # Head coefficients depend only on those words plus head_len, so computing them for the
    # unique table is identical to computing N logical rows and selecting each pattern's first
    # row, while deleting the N x 4 int32 + uint16 coefficient staging arrays.
    first_surface_rows, first_surface_pattern_words = intern_surface_row_words(first_surface_pool)
    first_surface_pattern_coeffs = surface_head_coeffs(
        first_surface_pattern_words,
        head_len=int(first_surface_head_len),
    )
    first_surface_patterns = pack_surface_patterns(
        first_surface_pattern_words,
        first_surface_pattern_coeffs,
    )
    surface_pattern_count = int(first_surface_patterns.shape[0])
    # Publish immutable generation sidecars first, then atomically replace the sole metadata
    # pointer. Readers that already opened the old metadata keep resolving the old immutable
    # files; an interruption before the final replace leaves that generation fully readable.
    _save_surface_sidecar_atomic(row_sidecar, first_surface_rows)
    _save_surface_sidecar_atomic(pattern_sidecar, first_surface_patterns)
    metadata = {
        "version": np.asarray(FG_RESPONSE_FRONTIER_CACHE.version()),
        _SURFACE_GENERATION_ARRAY_NAME: np.asarray(surface_generation),
        "stat_keys": np.asfortranarray(_as_uint8_exact("FG response stat keys", stat_keys)),
        "frontier_ids": np.asarray(
            [frontier_id_by_object[id(frontier)] for _key, frontier in sorted_items],
            dtype=np.int32,
        ),
        "raw_fill_by_ff": np.asarray(payload.raw_fill_by_ff, dtype=np.float64),
        "non_fever_base_by_ff": np.asarray(payload.non_fever_base_by_ff, dtype=np.int32),
        "real_time_by_ft": np.asarray(payload.real_time_by_ft, dtype=np.float64),
        "total_notes": np.asarray(int(payload.total_notes), dtype=np.int32),
        "long_notes": np.asarray(int(payload.long_notes), dtype=np.int32),
        "use_forced_great_timing": np.asarray(int(payload.use_forced_great_timing), dtype=np.int8),
        "first_surface_head_len": _as_uint8_exact(
            "FG response first surface head length",
            np.asarray(int(first_surface_head_len), dtype=np.int32),
        ),
        **_persisted_packed_frontier_metadata(
            packed_frontiers,
            surface_row_count=surface_row_count,
            surface_pattern_count=surface_pattern_count,
        ),
    }
    write_atomically(path, lambda tmp: _save_npz_fast_compressed(tmp, metadata))


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


def _load_payload(cache_key: tuple) -> FgResponseFrontierCachePayload | None:
    from .response_cache_serde import _unpack_frontiers

    path = FG_RESPONSE_FRONTIER_CACHE.readable_path(cache_key)
    if path is None:
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version not in FG_RESPONSE_FRONTIER_CACHE.compatible_versions():
                return None
            surface_generation = _surface_generation_from_bundle_data(data)
            row_sidecar, pattern_sidecar = _surface_sidecar_paths(path, generation=surface_generation)
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            frontiers = _unpack_frontiers(
                data,
                row_sidecar=row_sidecar,
                pattern_sidecar=pattern_sidecar,
            )
            frontier_by_key: dict[tuple[int, int], FgResponseFrontierResult] = {}
            for idx, key_row in enumerate(stat_keys):
                frontier_idx = int(frontier_ids[idx])
                if frontier_idx < 0 or frontier_idx >= len(frontiers):
                    return None
                key = _normalize_stat_key((int(key_row[0]), int(key_row[1])))
                frontier_by_key[key] = frontiers[frontier_idx]
            payload = FgResponseFrontierCachePayload(
                frontier_by_key=frontier_by_key,
                raw_fill_by_ff=np.asarray(data["raw_fill_by_ff"], dtype=np.float64),
                non_fever_base_by_ff=np.asarray(data["non_fever_base_by_ff"], dtype=np.int32),
                real_time_by_ft=np.asarray(data["real_time_by_ft"], dtype=np.float64),
                total_notes=int(np.asarray(data["total_notes"]).item()),
                long_notes=int(np.asarray(data["long_notes"]).item()),
                use_forced_great_timing=bool(int(np.asarray(data["use_forced_great_timing"]).item())),
            )
            if payload.raw_fill_by_ff.shape[0] != MAX_STAT + 1 or payload.real_time_by_ft.shape[0] != MAX_STAT + 1:
                return None
            return payload
    except FgResponseSurfaceSidecarError:
        # A current-version .npz whose surface sidecar is gone/mismatched is a desync, not a cache
        # miss. Surface it loudly (forces a re-pack) instead of deleting the .npz and silently
        # rebuilding from scratch.
        raise
    except Exception:
        _remove_fg_response_bundle_files(path)
        return None


def _payload_file_is_complete(path: Path, keys: Iterable[tuple[int, int]]) -> bool:
    """A readable bundle of a compatible version with intact sidecars that covers `keys`."""
    requested = set(normalize_fg_response_stat_keys(keys))
    if not path.exists():
        return False
    required = {"version", *_SCORING_BUNDLE_ARRAY_NAMES}
    legacy_required = required - {_SURFACE_GENERATION_ARRAY_NAME}
    try:
        with np.load(path, allow_pickle=False) as data:
            files = set(data.files)
            # Slim .npz: exactly the metadata set, no surface chunk members. The surfaces are the two
            # uncompressed sidecars validated below. Legacy fixed-sidecar bundles remain readable;
            # every new write includes one immutable sidecar generation.
            if files not in (required, legacy_required):
                return False
            version = str(data["version"].item())
            if version not in FG_RESPONSE_FRONTIER_CACHE.compatible_versions():
                return False
            surface_generation = _surface_generation_from_bundle_data(data)
            row_sidecar, pattern_sidecar = _surface_sidecar_paths(path, generation=surface_generation)
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            meta = np.asarray(data["frontier_meta"], dtype=np.int32)
            surface_row_count = int(np.asarray(data["first_surface_row_count"]).item())
            surface_pattern_count = int(np.asarray(data["first_surface_pattern_count"]).item())
            first_offsets = np.asarray(data["first_offsets"], dtype=np.int64).reshape(-1)
            first_counts = np.asarray(data["first_counts"], dtype=np.int64).reshape(-1)
            raw_fill_by_ff = np.asarray(data["raw_fill_by_ff"])
            non_fever_base_by_ff = np.asarray(data["non_fever_base_by_ff"])
            real_time_by_ft = np.asarray(data["real_time_by_ft"])
            total_notes = int(np.asarray(data["total_notes"]).item())
            long_notes = int(np.asarray(data["long_notes"]).item())
            if int(stat_keys.ndim) != 2 or int(stat_keys.shape[1]) != 2:
                return False
            if int(frontier_ids.ndim) != 1 or int(stat_keys.shape[0]) != int(frontier_ids.shape[0]):
                return False
            if int(meta.ndim) != 2 or int(meta.shape[0]) <= 0:
                return False
            if int(first_offsets.shape[0]) != int(meta.shape[0]) or int(first_counts.shape[0]) != int(meta.shape[0]):
                return False
            if int(raw_fill_by_ff.shape[0]) != MAX_STAT + 1:
                return False
            if int(non_fever_base_by_ff.shape[0]) != MAX_STAT + 1 or int(real_time_by_ft.shape[0]) != MAX_STAT + 1:
                return False
            if total_notes < 0 or long_notes < 0 or long_notes > total_notes:
                return False
            if int(np.asarray(data["first_surface_head_len"]).item()) != min(total_notes, 100):
                return False
            if surface_row_count < 0 or surface_pattern_count <= 0:
                return False
            if bool(np.any(first_offsets < 0)) or bool(np.any(first_counts <= 0)):
                return False
            max_surface_end = int(np.max(first_offsets + first_counts))
            if surface_row_count < max_surface_end:
                return False
            row_header = _surface_sidecar_header(row_sidecar)
            pattern_header = _surface_sidecar_header(pattern_sidecar)
            if row_header != ((surface_row_count, SURFACE_ROW_COLUMNS), np.dtype(np.uint32)):
                return False
            if pattern_header != ((surface_pattern_count, SURFACE_PATTERN_COLUMNS), np.dtype(np.uint32)):
                return False
            present: set[tuple[int, int]] = set()
            for idx, key_row in enumerate(stat_keys):
                frontier_idx = int(frontier_ids[int(idx)])
                if frontier_idx < 0 or frontier_idx >= int(meta.shape[0]):
                    return False
                present.add(_normalize_stat_key((int(key_row[0]), int(key_row[1]))))
            return requested.issubset(present)
    except Exception:
        _remove_fg_response_bundle_files(path)
        return False


def fg_response_cache_file_is_complete(cache_file: str | Path) -> bool:
    """A complete bundle of a compatible version covering every FT/FF stat key."""
    try:
        path = Path(cache_file)
    except TypeError:
        return False
    return _payload_file_is_complete(path, all_response_stat_keys())


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


def _load_bundle_array_members(cache_key: tuple, *, names: Iterable[str]) -> dict[str, np.ndarray]:
    requested = tuple(dict.fromkeys(str(name) for name in names))
    if not requested:
        raise ValueError("FG response frontier bundle array request was empty")
    snapshot_names = tuple(
        dict.fromkeys((*requested, _SURFACE_GENERATION_ARRAY_NAME, _SURFACE_BUNDLE_PATH_ARRAY_NAME))
    )
    cached = _bundle_array_memory.get(cache_key)
    if cached is not None and all(name in cached for name in snapshot_names):
        return {name: cached[name] for name in requested}
    path = FG_RESPONSE_FRONTIER_CACHE.readable_path(cache_key)
    if path is None:
        missing_path = FG_RESPONSE_FRONTIER_CACHE.file_path(cache_key)
        raise ValueError(f"FG response frontier bundle cache is missing: {missing_path}")
    with np.load(path, allow_pickle=False) as data:
        version = str(data["version"].item())
        if version not in FG_RESPONSE_FRONTIER_CACHE.compatible_versions():
            raise ValueError("FG response frontier bundle cache version is invalid")
        missing = [
            name
            for name in snapshot_names
            if name not in (_SURFACE_GENERATION_ARRAY_NAME, _SURFACE_BUNDLE_PATH_ARRAY_NAME)
            and name not in data.files
        ]
        if missing:
            raise ValueError(f"FG response frontier bundle cache is missing arrays: {missing[:5]!r}")
        surface_generation = _surface_generation_from_bundle_data(data)
        loaded = {
            name: np.asarray(data[name])
            for name in snapshot_names
            if name not in (_SURFACE_GENERATION_ARRAY_NAME, _SURFACE_BUNDLE_PATH_ARRAY_NAME)
        }
        loaded[_SURFACE_GENERATION_ARRAY_NAME] = np.asarray(surface_generation or "")
        loaded[_SURFACE_BUNDLE_PATH_ARRAY_NAME] = np.asarray(str(path))
    # Arrays read from the same file generation join the cached ones; any other file replaces them.
    cached = _bundle_array_memory.get(cache_key)
    if (
        cached is not None
        and _SURFACE_GENERATION_ARRAY_NAME in cached
        and _SURFACE_BUNDLE_PATH_ARRAY_NAME in cached
        and _normalize_surface_generation(cached[_SURFACE_GENERATION_ARRAY_NAME]) == surface_generation
        and str(np.asarray(cached[_SURFACE_BUNDLE_PATH_ARRAY_NAME]).item()) == str(path)
    ):
        loaded = {**cached, **loaded}
    _bundle_array_memory.put(cache_key, loaded)
    return {name: loaded[name] for name in requested}


def _normalize_surface_ranges(ranges: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    normalized: list[tuple[int, int]] = []
    for start, count in ranges:
        start_i = int(start)
        count_i = int(count)
        if start_i < 0 or count_i <= 0:
            raise ValueError("FG response surface range is invalid")
        normalized.append((start_i, count_i))
    if not normalized:
        raise ValueError("FG response surface rows require at least one range")
    return tuple(normalized)


def _surface_counts_for_key(cache_key: tuple) -> tuple[int, int, str | None, Path]:
    arrays = _load_bundle_array_members(
        cache_key,
        names=(
            "first_surface_row_count",
            "first_surface_pattern_count",
            _SURFACE_GENERATION_ARRAY_NAME,
            _SURFACE_BUNDLE_PATH_ARRAY_NAME,
        ),
    )
    row_count = int(np.asarray(arrays["first_surface_row_count"]).item())
    pattern_count = int(np.asarray(arrays["first_surface_pattern_count"]).item())
    surface_generation = _normalize_surface_generation(arrays[_SURFACE_GENERATION_ARRAY_NAME])
    bundle_path = Path(str(np.asarray(arrays[_SURFACE_BUNDLE_PATH_ARRAY_NAME]).item()))
    if row_count < 0:
        raise ValueError("FG response frontier bundle has a negative surface row count")
    if pattern_count <= 0:
        raise ValueError("FG response frontier bundle has no surface head patterns")
    return int(row_count), int(pattern_count), surface_generation, bundle_path


def _surface_counts_from_sidecars(row_sidecar: Path, pattern_sidecar: Path) -> tuple[int, int]:
    row_header = _surface_sidecar_header(row_sidecar)
    pattern_header = _surface_sidecar_header(pattern_sidecar)
    if (
        row_header is None
        or len(row_header[0]) != 2
        or int(row_header[0][1]) != SURFACE_ROW_COLUMNS
        or row_header[1] != np.dtype(np.uint32)
    ):
        raise FgResponseSurfaceSidecarError(f"FG response frontier surface sidecar has invalid shape: {row_sidecar}")
    if (
        pattern_header is None
        or len(pattern_header[0]) != 2
        or int(pattern_header[0][1]) != SURFACE_PATTERN_COLUMNS
        or pattern_header[1] != np.dtype(np.uint32)
    ):
        raise FgResponseSurfaceSidecarError(
            f"FG response frontier surface sidecar has invalid shape: {pattern_sidecar}"
        )
    row_count = int(row_header[0][0])
    pattern_count = int(pattern_header[0][0])
    if row_count < 0 or pattern_count <= 0:
        raise FgResponseSurfaceSidecarError("FG response frontier surface sidecar has invalid row counts")
    return row_count, pattern_count


def _surface_sidecar_memmaps(
    cache_key: tuple,
    surface_generation: str | None | object,
    bundle_path: str | Path | None,
) -> tuple[np.ndarray, np.ndarray]:
    """The row and pattern sidecars of a bundle generation as read-only memmaps, checked against their counts: the
    bundle's metadata for an unspecified generation, else the sidecar headers."""
    if surface_generation is _UNSPECIFIED_SURFACE_GENERATION:
        surface_row_count, surface_pattern_count, resolved_generation, resolved_bundle_path = (
            _surface_counts_for_key(cache_key)
        )
        row_sidecar, pattern_sidecar = _surface_sidecar_paths_for_key(
            cache_key,
            generation=resolved_generation,
            bundle_path=resolved_bundle_path,
        )
    else:
        row_sidecar, pattern_sidecar = _surface_sidecar_paths_for_key(
            cache_key,
            generation=surface_generation,
            bundle_path=bundle_path,
        )
        surface_row_count, surface_pattern_count = _surface_counts_from_sidecars(row_sidecar, pattern_sidecar)
    row_memmap = _open_surface_sidecar_memmap(
        row_sidecar, columns=SURFACE_ROW_COLUMNS, dtype=np.dtype(np.uint32), row_count=surface_row_count
    )
    pattern_memmap = _open_surface_sidecar_memmap(
        pattern_sidecar, columns=SURFACE_PATTERN_COLUMNS, dtype=np.dtype(np.uint32), row_count=surface_pattern_count
    )
    return row_memmap, pattern_memmap


def load_first_surface_scoring_rows(
    cache_key: tuple,
    ranges: Iterable[tuple[int, int]],
    *,
    surface_generation: str | None | object = _UNSPECIFIED_SURFACE_GENERATION,
    bundle_path: str | Path | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    normalized = _normalize_surface_ranges(ranges)
    row_memmap, pattern_memmap = _surface_sidecar_memmaps(cache_key, surface_generation, bundle_path)
    row_refs = np.empty((sum(count for _start, count in normalized), SURFACE_ROW_COLUMNS), dtype=np.uint32)
    # Slice-copy out of the read-only memmaps into freshly-owned contiguous arrays so the returned
    # arrays never alias a memmap (which could be evicted/closed across songs).
    _gather_surface_ranges(row_memmap, ranges=normalized, out=row_refs)
    rows, coeffs = expand_surface_rows(row_refs, pattern_memmap)
    return rows, coeffs


def load_first_surface_scoring_patterns(
    cache_key: tuple,
    ranges: Iterable[tuple[int, int]],
    *,
    surface_generation: str | None | object = _UNSPECIFIED_SURFACE_GENERATION,
    bundle_path: str | Path | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Load the canonical compact scoring representation for requested frontier ranges.

    Returns ``(surface_pattern_ids, surface_counts, pattern_words, pattern_coeffs)``. Pattern IDs
    are remapped densely for this gather, but surface-row order is untouched; therefore exact-score
    ties retain the producer's original first-row priority.
    """
    normalized = _normalize_surface_ranges(ranges)
    row_memmap, pattern_memmap = _surface_sidecar_memmaps(cache_key, surface_generation, bundle_path)
    row_count = sum(count for _start, count in normalized)
    surface_pattern_ids = np.empty((int(row_count),), dtype=np.int32)
    surface_counts = np.empty((int(row_count), 3), dtype=np.int32)
    # Split each row-ref block straight into the int32 id/count outputs (no N x 4 staging copy).
    out_cursor = 0
    for start, count in normalized:
        end = int(start) + int(count)
        if end > int(row_memmap.shape[0]):
            raise ValueError("FG response surface range exceeds cached rows")
        block = row_memmap[int(start) : end]
        surface_pattern_ids[out_cursor : out_cursor + int(count)] = block[:, 0]
        surface_counts[out_cursor : out_cursor + int(count)] = block[:, 1:4]
        out_cursor += int(count)
    if out_cursor != int(row_count):
        raise ValueError("FG response surface gather produced the wrong row count")
    unique_ids = _dense_rank_pattern_ids_inplace(surface_pattern_ids, int(pattern_memmap.shape[0]))
    selected_patterns = np.ascontiguousarray(pattern_memmap[unique_ids], dtype=np.uint32)
    pattern_words, pattern_coeffs = unpack_surface_patterns(selected_patterns)
    return surface_pattern_ids, surface_counts, pattern_words, pattern_coeffs


def _invalidate_bundle_array_views(bundle_key: tuple) -> None:
    _bundle_array_memory.pop(bundle_key)
    _scoring_bundle_memory.pop(bundle_key)
