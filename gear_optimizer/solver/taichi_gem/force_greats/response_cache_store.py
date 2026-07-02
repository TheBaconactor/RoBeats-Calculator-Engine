from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

import numpy as np
from numpy.lib import format as np_format

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.profile_events import emit_profile_event

from .response_cache_keys import (
    _fg_response_disk_cache_dir,
    _fg_response_disk_cache_path,
    _fg_response_cache_version,
)
from .response_cache_types import (
    _BUNDLE_ARRAY_CACHE_MAX,
    _MEMORY_CACHE_MAX,
    _PAYLOAD_CACHE_MAX,
    _SCORING_BUNDLE_ARRAY_NAMES,
    FgResponseFrontierCachePayload,
    FgResponseFrontierScoringBundle,
    _normalize_stat_key,
    normalize_fg_response_stat_keys,
)
from .response_types import FgResponseFrontierResult

_frontier_cache: OrderedDict[tuple, FgResponseFrontierResult] = OrderedDict()
_payload_cache: OrderedDict[tuple, FgResponseFrontierCachePayload] = OrderedDict()
_bundle_array_cache: OrderedDict[tuple, dict[str, np.ndarray]] = OrderedDict()
_scoring_bundle_cache: OrderedDict[tuple, FgResponseFrontierScoringBundle] = OrderedDict()
_frontier_cache_last_access: dict[tuple, float] = {}
_payload_cache_last_access: dict[tuple, float] = {}
_bundle_array_cache_last_access: dict[tuple, float] = {}
_scoring_bundle_cache_last_access: dict[tuple, float] = {}
_frontier_cache_lock = threading.RLock()
_RESPONSE_BUNDLE_BUILD_PARALLELISM = 1
_response_bundle_build_slots = threading.BoundedSemaphore(int(_RESPONSE_BUNDLE_BUILD_PARALLELISM))
_NPZ_FAST_COMPRESS_LEVEL = 1
# Scoring surfaces (the first-frontier pool + head coeffs) live in uncompressed, C-order,
# memmap-able sidecar .npy files next to the bundle .npz. The reader pages only the requested
# rows through the OS mmap instead of inflating + fully materializing the whole pool, which is
# what made the per-song disk load (Issue #34) bandwidth-bound. The bundle .npz keeps every
# non-surface metadata array plus a `first_surface_row_count` scalar that pins the sidecar shape.
_SURFACE_POOL_SIDECAR_SUFFIX = ".surf_pool.npy"
_SURFACE_COEFF_SIDECAR_SUFFIX = ".surf_coeffs.npy"
_SURFACE_POOL_COLUMNS = 11
_SURFACE_COEFF_COLUMNS = 4


def _fg_response_idle_ttl_seconds() -> float | None:
    raw = str(env_get("ROBEATSMETA_LIVE_CACHE_IDLE_TTL_SECONDS", "") or "").strip()
    if not raw:
        return None
    try:
        ttl = float(raw)
    except (TypeError, ValueError):
        return None
    return ttl if ttl > 0.0 else None


_LIVE_CACHE_DISK_IDLE_TTL_MULTIPLIER = 2.0


def _fg_response_disk_idle_ttl_seconds(idle_ttl_seconds: float | None = None) -> float | None:
    ram_ttl = _fg_response_idle_ttl_seconds() if idle_ttl_seconds is None else idle_ttl_seconds
    if ram_ttl is None or float(ram_ttl) <= 0.0:
        return None
    return float(ram_ttl) * _LIVE_CACHE_DISK_IDLE_TTL_MULTIPLIER


def _fg_response_entry_idle_expired(
    last_access: float | None,
    *,
    idle_ttl_seconds: float | None,
    moment: float,
) -> bool:
    return idle_ttl_seconds is not None and idle_ttl_seconds > 0.0 and (
        last_access is None or moment - float(last_access) > float(idle_ttl_seconds)
    )


def _memory_cache_get_locked(
    cache: OrderedDict,
    last_access: dict[tuple, float],
    cache_key: tuple,
):
    cached = cache.get(cache_key)
    if cached is None:
        return None
    ttl = _fg_response_idle_ttl_seconds()
    moment = time.monotonic()
    if _fg_response_entry_idle_expired(
        last_access.get(cache_key),
        idle_ttl_seconds=ttl,
        moment=moment,
    ):
        cache.pop(cache_key, None)
        last_access.pop(cache_key, None)
        return None
    cache.move_to_end(cache_key)
    last_access[cache_key] = moment
    return cached


def _memory_cache_put_locked(
    cache: OrderedDict,
    last_access: dict[tuple, float],
    cache_key: tuple,
    value,
    *,
    max_entries: int,
) -> None:
    moment = time.monotonic()
    cache[cache_key] = value
    cache.move_to_end(cache_key)
    last_access[cache_key] = moment
    while len(cache) > int(max_entries):
        stale_key, _stale_value = cache.popitem(last=False)
        last_access.pop(stale_key, None)


def _sweep_fg_response_memory_cache_locked(
    cache: OrderedDict,
    last_access: dict[tuple, float],
    *,
    idle_ttl_seconds: float | None,
    moment: float,
) -> int:
    if idle_ttl_seconds is None or idle_ttl_seconds <= 0.0:
        return 0
    removed = 0
    while cache:
        oldest_key = next(iter(cache))
        if not _fg_response_entry_idle_expired(
            last_access.get(oldest_key),
            idle_ttl_seconds=idle_ttl_seconds,
            moment=moment,
        ):
            break
        cache.pop(oldest_key, None)
        last_access.pop(oldest_key, None)
        removed += 1
    return removed


class FgResponseSurfaceSidecarError(RuntimeError):
    """A current-version bundle .npz exists but its uncompressed surface sidecar is missing or
    disagrees in shape/dtype/row-count. This is a desync (e.g. interrupted migration), not a cache
    miss -- it must surface loudly so the human re-runs the re-pack, never silently rebuild."""


def _surface_sidecar_paths(bundle_path: Path) -> tuple[Path, Path]:
    """Return (pool_sidecar, coeff_sidecar) paths for a bundle .npz path.

    Both sidecars share the bundle digest stem so they migrate/evict as one unit.
    """
    base = Path(bundle_path)
    if base.suffix != ".npz":
        raise ValueError(f"FG response frontier bundle path must be a .npz: {base}")
    stem = base.name[: -len(".npz")]
    return (
        base.with_name(f"{stem}{_SURFACE_POOL_SIDECAR_SUFFIX}"),
        base.with_name(f"{stem}{_SURFACE_COEFF_SIDECAR_SUFFIX}"),
    )


def _surface_sidecar_paths_for_key(cache_key: tuple) -> tuple[Path, Path]:
    return _surface_sidecar_paths(_fg_response_disk_cache_path(cache_key))


def warm_surface_sidecar_page_cache(cache_key: tuple) -> None:
    """Sequentially read both surface sidecars to warm the OS page cache.

    Runs on prep workers so the fused turn's owner-thread sidecar gather reads from
    memory instead of cold (WOF-compressed) disk. Best-effort readahead only -- a
    missing/unreadable sidecar fails loud later at the gather that actually needs it.
    """
    for path in _surface_sidecar_paths_for_key(cache_key):
        try:
            with open(path, "rb") as fh:
                while fh.read(8 * 1024 * 1024):
                    pass
        except OSError:
            return


def _touch_fg_response_bundle_files(bundle_path: Path) -> None:
    for path in (bundle_path, *_surface_sidecar_paths(bundle_path)):
        try:
            os.utime(path, None)
        except OSError:
            pass


def _remove_fg_response_bundle_files(bundle_path: Path) -> int:
    removed = 0
    for path in (bundle_path, *_surface_sidecar_paths(bundle_path)):
        if not path.exists():
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue
        removed += 1
    return removed


def _live_fg_response_bundle_path(
    bundle_path: Path,
    *,
    idle_ttl_seconds: float | None = None,
    now: float | None = None,
) -> Path | None:
    if not bundle_path.exists():
        return None
    ttl = _fg_response_idle_ttl_seconds() if idle_ttl_seconds is None else idle_ttl_seconds
    disk_ttl = _fg_response_disk_idle_ttl_seconds(ttl)
    if disk_ttl is not None and disk_ttl > 0.0:
        try:
            stat = bundle_path.stat()
        except OSError:
            return None
        moment = time.time() if now is None else float(now)
        if moment - float(stat.st_mtime) > float(disk_ttl):
            _remove_fg_response_bundle_files(bundle_path)
            return None
    return bundle_path


def compress_cache_dir_sidecars() -> None:
    """Bulk-compress the cache directory with NTFS WOF XPRESS16K (~6x measured) at the
    end of a prebuild.

    The `.npy` payload stays uncompressed at the numpy layer, so files remain
    `np.load(mmap_mode="r")`-able — WOF decompresses pages on fault, and the scorer's sparse row
    reads cost only ~0.2ms more (verified bit-identical, memmap intact). One bulk `compact` pass
    (~1 min / 90 GB at ~1.4 GB/s) instead of per-file subprocess spawns; already-compressed files
    are skipped so re-running each build is cheap. Windows-only; a harmless no-op elsewhere or if
    `compact` is unavailable. External OS/filesystem boundary, not an optimizer invariant.
    """
    if sys.platform != "win32":
        return
    directory = _fg_response_disk_cache_dir()
    if not directory.exists():
        return
    try:
        subprocess.run(
            ["compact", "/c", "/exe:XPRESS16K", "/s:" + str(directory)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3600,
            check=False,
        )
    except Exception:
        pass


_PURGED_VERSION_MARKER = ".purged_version"


def purge_stale_version_cache_files() -> int:
    """Delete on-disk cache entries whose embedded version != the current cache version.

    Old-version bundles are already dead weight — the reader rejects any version mismatch — so left
    alone they accumulate ~one full pool per version bump. This sweeps them exactly once per version
    change, guarded by a `.purged_version` marker so the routine startup path stays O(1). Returns the
    number of files removed. External filesystem boundary: unreadable/corrupt bundles are left in
    place rather than guessed at, and if any unlink fails (e.g. a locked file) the marker is left
    unwritten so the sweep retries on the next prebuild instead of permanently stranding the file.
    """
    directory = _fg_response_disk_cache_dir()
    if not directory.exists():
        return 0
    current = _fg_response_cache_version()
    marker = directory / _PURGED_VERSION_MARKER
    try:
        if marker.read_text(encoding="utf-8").strip() == current:
            return 0
    except OSError:
        pass
    removed = 0
    purge_complete = True
    for npz in directory.glob("*.npz"):
        try:
            with np.load(npz, allow_pickle=False) as bundle:
                version = str(bundle["version"].item()) if "version" in bundle.files else None
        except Exception:
            # Any unreadable/corrupt bundle (bad zip, corrupt member, IO error): keep it rather than
            # crash the whole sweep. This is the documented FS boundary, matching the bundle readers.
            version = None
        if version is None or version == current:
            continue
        for stale in (npz, *_surface_sidecar_paths(npz)):
            try:
                stale.unlink()
                removed += 1
            except FileNotFoundError:
                pass  # already absent: nothing to remove, not a retry-worthy failure
            except OSError:
                purge_complete = False  # locked/in-use: leave marker unwritten, retry next prebuild
    if purge_complete:
        try:
            marker.write_text(current, encoding="utf-8")
        except OSError:
            pass
    return removed


def _save_surface_sidecar_atomic(path: Path, array: np.ndarray) -> None:
    """Write `array` as an uncompressed C-order .npy via tmp + os.replace.

    Uncompressed at the numpy layer so the reader can `np.load(..., mmap_mode="r")` and page rows
    lazily; on-disk size is reclaimed by the bulk NTFS pass at prebuild-end (see
    `compress_cache_dir_sidecars`), which keeps the bytes small while preserving the memmap path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp")
    try:
        with open(tmp, "wb") as handle:
            np_format.write_array(handle, np.ascontiguousarray(array), allow_pickle=False)
        os.replace(tmp, path)
    except Exception:
        try:
            Path(tmp).unlink(missing_ok=True)
        except Exception:
            pass
        raise


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
) -> dict[str, np.ndarray]:
    """Slim-.npz metadata for a packed bundle. Surfaces live in the sidecars, not here.

    `first_surface_row_count` pins the pool/coeff sidecar shape so the reader can fail loud
    on any sidecar/npz desync without re-deriving the row count from per-chunk offsets.
    """
    return {
        "frontier_meta": np.asfortranarray(np.asarray(packed_frontiers["frontier_meta"], dtype=np.int32)),
        "first_offsets": np.asarray(packed_frontiers["first_offsets"], dtype=np.int32),
        "first_counts": np.asarray(packed_frontiers["first_counts"], dtype=np.int32),
        "first_surface_row_count": np.asarray(int(surface_row_count), dtype=np.int64),
    }


def _memory_get(cache_key: tuple) -> FgResponseFrontierResult | None:
    with _frontier_cache_lock:
        frontier = _memory_cache_get_locked(_frontier_cache, _frontier_cache_last_access, cache_key)
        return frontier if isinstance(frontier, FgResponseFrontierResult) else None


def _frontier_is_complete(frontier: FgResponseFrontierResult | None) -> bool:
    return frontier is not None and bool(frontier.first_frontier)


def _memory_put(cache_key: tuple, frontier: FgResponseFrontierResult) -> None:
    if not frontier.first_frontier:
        raise ValueError("FG response frontier cache requires first-frontier surfaces")
    with _frontier_cache_lock:
        _memory_cache_put_locked(
            _frontier_cache,
            _frontier_cache_last_access,
            cache_key,
            frontier,
            max_entries=_MEMORY_CACHE_MAX,
        )


def _payload_memory_get(cache_key: tuple) -> FgResponseFrontierCachePayload | None:
    with _frontier_cache_lock:
        payload = _memory_cache_get_locked(_payload_cache, _payload_cache_last_access, cache_key)
        return payload if isinstance(payload, FgResponseFrontierCachePayload) else None


def _payload_memory_put(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    with _frontier_cache_lock:
        _memory_cache_put_locked(
            _payload_cache,
            _payload_cache_last_access,
            cache_key,
            payload,
            max_entries=_PAYLOAD_CACHE_MAX,
        )


def reset_fg_response_frontier_payload_cache() -> None:
    with _frontier_cache_lock:
        _frontier_cache.clear()
        _frontier_cache_last_access.clear()
        _payload_cache.clear()
        _payload_cache_last_access.clear()
        _bundle_array_cache.clear()
        _bundle_array_cache_last_access.clear()
        _scoring_bundle_cache.clear()
        _scoring_bundle_cache_last_access.clear()


def release_fg_response_song_memory(bundle_key: tuple) -> int:
    """Evict every in-memory cache entry for one song's response-frontier surfaces.

    Called once a song's FG scoring is complete: the ~0.5-1.5 GB surface pool it loaded is no
    longer needed for the rest of this run, so drop it from every memory tier instead of letting
    it sit until the entry-count LRU (`_MEMORY_CACHE_MAX`/`_BUNDLE_ARRAY_CACHE_MAX`) or the
    serving-only idle sweep (`sweep_fg_response_frontier_live_cache`) evicts it. A standalone
    optimizer run calls neither, so without this the surfaces accumulate one-per-scored-song and
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
    n = len(prefix)
    removed = 0
    with _frontier_cache_lock:
        for cache, last_access in (
            (_scoring_bundle_cache, _scoring_bundle_cache_last_access),
            (_bundle_array_cache, _bundle_array_cache_last_access),
            (_frontier_cache, _frontier_cache_last_access),
            (_payload_cache, _payload_cache_last_access),
        ):
            stale = [key for key in cache if key[:n] == prefix]
            for key in stale:
                cache.pop(key, None)
                last_access.pop(key, None)
                removed += 1
    return removed


def _save_payload(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    from .response_cache_serde import _pack_frontiers
    from .response_inner_host import _precompute_surface_head_coeffs

    path = _fg_response_disk_cache_path(cache_key)
    pool_sidecar, coeff_sidecar = _surface_sidecar_paths(path)
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz")
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
        first_surface_head_coeffs = _precompute_surface_head_coeffs(
            first_surface_pool,
            head_len=int(first_surface_head_len),
        )
        if bool(np.any(first_surface_head_coeffs < 0)) or bool(np.any(first_surface_head_coeffs > np.iinfo(np.uint16).max)):
            raise ValueError("FG response surface head coefficients exceed persisted uint16 bounds")
        first_surface_head_coeffs = np.ascontiguousarray(np.asarray(first_surface_head_coeffs, dtype=np.uint16))
        # Sidecars first (atomic each), then the slim .npz last: a present .npz implies present sidecars.
        _save_surface_sidecar_atomic(pool_sidecar, first_surface_pool)
        _save_surface_sidecar_atomic(coeff_sidecar, first_surface_head_coeffs)
        _save_npz_fast_compressed(
            tmp,
            {
                "version": np.asarray(_fg_response_cache_version()),
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
                **_persisted_packed_frontier_metadata(packed_frontiers, surface_row_count=surface_row_count),
            },
        )
        tmp.replace(path)
    except Exception:
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
        raise


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

    path = _live_fg_response_bundle_path(_fg_response_disk_cache_path(cache_key))
    if path is None:
        return None
    pool_sidecar, _coeff_sidecar = _surface_sidecar_paths(path)
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version != _fg_response_cache_version():
                return None
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            frontiers = _unpack_frontiers(data, pool_sidecar=pool_sidecar)
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
            if payload.raw_fill_by_ff.shape[0] != TOTAL_ROWS + 1 or payload.real_time_by_ft.shape[0] != TOTAL_ROWS + 1:
                return None
            _touch_fg_response_bundle_files(path)
            return payload
    except FgResponseSurfaceSidecarError:
        # A current-version .npz whose surface sidecar is gone/mismatched is a desync, not a cache
        # miss. Surface it loudly (forces a re-pack) instead of deleting the .npz and silently
        # rebuilding from scratch.
        raise
    except Exception:
        _remove_fg_response_bundle_files(path)
        return None


def _payload_file_info_if_complete(path: Path, keys: Iterable[tuple[int, int]]) -> tuple[int, int, int] | None:
    requested = set(normalize_fg_response_stat_keys(keys))
    path = _live_fg_response_bundle_path(path)
    if path is None:
        return None
    required = {"version", *_SCORING_BUNDLE_ARRAY_NAMES}
    pool_sidecar, coeff_sidecar = _surface_sidecar_paths(path)
    try:
        with np.load(path, allow_pickle=False) as data:
            files = set(data.files)
            # Slim .npz: exactly the metadata set, no surface chunk members. The surfaces are the two
            # uncompressed sidecars validated below.
            if files != required:
                return None
            version = str(data["version"].item())
            if version != _fg_response_cache_version():
                return None
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            meta = np.asarray(data["frontier_meta"], dtype=np.int32)
            surface_row_count = int(np.asarray(data["first_surface_row_count"]).item())
            first_offsets = np.asarray(data["first_offsets"], dtype=np.int64).reshape(-1)
            first_counts = np.asarray(data["first_counts"], dtype=np.int64).reshape(-1)
            raw_fill_by_ff = np.asarray(data["raw_fill_by_ff"])
            non_fever_base_by_ff = np.asarray(data["non_fever_base_by_ff"])
            real_time_by_ft = np.asarray(data["real_time_by_ft"])
            total_notes = int(np.asarray(data["total_notes"]).item())
            long_notes = int(np.asarray(data["long_notes"]).item())
            if int(stat_keys.ndim) != 2 or int(stat_keys.shape[1]) != 2:
                return None
            if int(frontier_ids.ndim) != 1 or int(stat_keys.shape[0]) != int(frontier_ids.shape[0]):
                return None
            if int(meta.ndim) != 2 or int(meta.shape[0]) <= 0:
                return None
            if int(first_offsets.shape[0]) != int(meta.shape[0]) or int(first_counts.shape[0]) != int(meta.shape[0]):
                return None
            if int(raw_fill_by_ff.shape[0]) != TOTAL_ROWS + 1:
                return None
            if int(non_fever_base_by_ff.shape[0]) != TOTAL_ROWS + 1 or int(real_time_by_ft.shape[0]) != TOTAL_ROWS + 1:
                return None
            if total_notes < 0 or long_notes < 0 or long_notes > total_notes:
                return None
            if int(np.asarray(data["first_surface_head_len"]).item()) != min(total_notes, 100):
                return None
            if surface_row_count < 0:
                return None
            if bool(np.any(first_offsets < 0)) or bool(np.any(first_counts <= 0)):
                return None
            max_surface_end = int(np.max(first_offsets + first_counts))
            if surface_row_count < max_surface_end:
                return None
            pool_header = _surface_sidecar_header(pool_sidecar)
            coeff_header = _surface_sidecar_header(coeff_sidecar)
            if pool_header != ((surface_row_count, _SURFACE_POOL_COLUMNS), np.dtype(np.uint32)):
                return None
            if coeff_header != ((surface_row_count, _SURFACE_COEFF_COLUMNS), np.dtype(np.uint16)):
                return None
            present: set[tuple[int, int]] = set()
            for idx, key_row in enumerate(stat_keys):
                frontier_idx = int(frontier_ids[int(idx)])
                if frontier_idx < 0 or frontier_idx >= int(meta.shape[0]):
                    return None
                present.add(_normalize_stat_key((int(key_row[0]), int(key_row[1]))))
            if not requested.issubset(present):
                return None
            _touch_fg_response_bundle_files(path)
            return (
                int(total_notes),
                int(long_notes),
                int(len(requested)),
            )
    except Exception:
        _remove_fg_response_bundle_files(path)
        return None


def fg_response_cache_file_is_complete(cache_file: str | Path, *, stat_keys: Iterable[tuple[int, int]]) -> bool:
    try:
        path = Path(cache_file)
    except TypeError:
        return False
    return _payload_file_info_if_complete(path, stat_keys) is not None


def _payload_disk_info_if_complete(
    cache_key: tuple,
    keys: Iterable[tuple[int, int]],
) -> tuple[int, int, int] | None:
    return _payload_file_info_if_complete(_fg_response_disk_cache_path(cache_key), keys)


def _load_bundle_array_members(cache_key: tuple, *, names: Iterable[str]) -> dict[str, np.ndarray]:
    requested = tuple(dict.fromkeys(str(name) for name in names))
    if not requested:
        raise ValueError("FG response frontier bundle array request was empty")
    with _frontier_cache_lock:
        cached = _memory_cache_get_locked(_bundle_array_cache, _bundle_array_cache_last_access, cache_key)
        if cached is not None and all(name in cached for name in requested):
            return {name: cached[name] for name in requested}
    bundle_path = _fg_response_disk_cache_path(cache_key)
    path = _live_fg_response_bundle_path(bundle_path)
    if path is None:
        raise ValueError(f"FG response frontier bundle cache is missing: {bundle_path}")
    with np.load(path, allow_pickle=False) as data:
        version = str(data["version"].item())
        if version != _fg_response_cache_version():
            raise ValueError("FG response frontier bundle cache version is invalid")
        missing = [name for name in requested if name not in data.files]
        if missing:
            raise ValueError(f"FG response frontier bundle cache is missing arrays: {missing[:5]!r}")
        loaded = {name: np.asarray(data[name]) for name in requested}
    _touch_fg_response_bundle_files(path)
    with _frontier_cache_lock:
        cached = _bundle_array_cache.get(cache_key)
        if cached is None:
            cached = {}
            _bundle_array_cache[cache_key] = cached
        cached.update(loaded)
        _bundle_array_cache_last_access[cache_key] = time.monotonic()
        while len(_bundle_array_cache) > int(_BUNDLE_ARRAY_CACHE_MAX):
            stale_key, _stale_value = _bundle_array_cache.popitem(last=False)
            _bundle_array_cache_last_access.pop(stale_key, None)
        _bundle_array_cache.move_to_end(cache_key)
        return {name: cached[name] for name in requested}


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


def _surface_row_count_for_key(cache_key: tuple) -> int:
    row_count = int(
        np.asarray(
            _load_bundle_array_members(cache_key, names=("first_surface_row_count",))["first_surface_row_count"]
        ).item()
    )
    if row_count < 0:
        raise ValueError("FG response frontier bundle has a negative surface row count")
    return int(row_count)


def load_first_surface_scoring_rows(
    cache_key: tuple,
    ranges: Iterable[tuple[int, int]],
) -> tuple[np.ndarray, np.ndarray]:
    started = time.perf_counter()
    normalized = _normalize_surface_ranges(ranges)
    surface_row_count = _surface_row_count_for_key(cache_key)
    pool_sidecar, coeff_sidecar = _surface_sidecar_paths_for_key(cache_key)
    row_count = sum(int(count) for _start, count in normalized)
    rows = np.empty((int(row_count), _SURFACE_POOL_COLUMNS), dtype=np.uint32)
    coeff_rows = np.empty((int(row_count), _SURFACE_COEFF_COLUMNS), dtype=np.uint16)
    load_t0 = time.perf_counter()
    pool_memmap = _open_surface_sidecar_memmap(
        pool_sidecar, columns=_SURFACE_POOL_COLUMNS, dtype=np.dtype(np.uint32), row_count=surface_row_count
    )
    coeff_memmap = _open_surface_sidecar_memmap(
        coeff_sidecar, columns=_SURFACE_COEFF_COLUMNS, dtype=np.dtype(np.uint16), row_count=surface_row_count
    )
    load_ms = float((time.perf_counter() - load_t0) * 1000.0)
    copy_t0 = time.perf_counter()
    # Slice-copy out of the read-only memmaps into freshly-owned contiguous arrays so the returned
    # arrays never alias a memmap (which could be evicted/closed across songs).
    _gather_surface_ranges(pool_memmap, ranges=normalized, out=rows)
    _gather_surface_ranges(coeff_memmap, ranges=normalized, out=coeff_rows)
    copy_ms = float((time.perf_counter() - copy_t0) * 1000.0)
    coeffs = np.ascontiguousarray(coeff_rows, dtype=np.int32)
    emit_profile_event(
        component="fg_response_cache",
        event="surface_chunk_load",
        metrics={
            "ranges": int(len(normalized)),
            "chunks": 0,
            "rows": int(row_count),
            "load_ms": float(load_ms),
            "copy_ms": float(copy_ms),
            "elapsed_ms": float((time.perf_counter() - started) * 1000.0),
        },
    )
    return np.ascontiguousarray(rows, dtype=np.uint32), coeffs


def _invalidate_bundle_array_views(bundle_key: tuple) -> None:
    with _frontier_cache_lock:
        _bundle_array_cache.pop(bundle_key, None)
        _bundle_array_cache_last_access.pop(bundle_key, None)
        _scoring_bundle_cache.pop(bundle_key, None)
        _scoring_bundle_cache_last_access.pop(bundle_key, None)


def _scoring_bundle_memory_get(bundle_key: tuple) -> FgResponseFrontierScoringBundle | None:
    with _frontier_cache_lock:
        cached = _memory_cache_get_locked(_scoring_bundle_cache, _scoring_bundle_cache_last_access, bundle_key)
        return cached if isinstance(cached, FgResponseFrontierScoringBundle) else None


def _scoring_bundle_memory_put(bundle_key: tuple, scoring_bundle: FgResponseFrontierScoringBundle) -> None:
    with _frontier_cache_lock:
        _memory_cache_put_locked(
            _scoring_bundle_cache,
            _scoring_bundle_cache_last_access,
            bundle_key,
            scoring_bundle,
            max_entries=_BUNDLE_ARRAY_CACHE_MAX,
        )


def _enforce_fg_response_disk_cap(
    *,
    max_disk_bytes: int | None,
    max_disk_files: int | None,
) -> int:
    """Bound the on-disk FG response-frontier cache to a hard size/file budget, evicting the
    least-recently-used bundles (oldest mtime) first. Returns the number of files removed.

    This is a SERVING-mode safety: only ``sweep_fg_response_frontier_live_cache`` (the API's
    periodic live-cache sweep) passes caps, so a standalone optimizer run -- which writes bundles
    but never calls the live sweep -- is never throttled by it (it keeps the idle-TTL-only
    behavior). Lossless: an evicted bundle is rebuilt on next access. Each bundle is sized as its
    .npz plus the two surface sidecars so they evict as one unit (mirrors the on-demand rank
    cache's prune_cache_dir)."""
    cap_bytes = int(max_disk_bytes) if max_disk_bytes and int(max_disk_bytes) > 0 else 0
    cap_files = int(max_disk_files) if max_disk_files and int(max_disk_files) > 0 else 0
    if cap_bytes <= 0 and cap_files <= 0:
        return 0
    try:
        bundles = tuple(_fg_response_disk_cache_dir().glob("*.npz"))
    except OSError:
        return 0
    entries: list[tuple[float, int, Path]] = []
    total_bytes = 0
    for npz in bundles:
        size = 0
        mtime = 0.0
        present = False
        for path in (npz, *_surface_sidecar_paths(npz)):
            try:
                stat = path.stat()
            except OSError:
                continue
            size += int(stat.st_size)
            mtime = max(mtime, float(stat.st_mtime))
            present = True
        if present:
            entries.append((mtime, size, npz))
            total_bytes += size
    entries.sort(key=lambda item: item[0])  # least-recently-used (oldest mtime) first
    remaining_files = len(entries)
    removed = 0
    for _mtime, size, npz in entries:
        over_bytes = cap_bytes > 0 and total_bytes > cap_bytes
        over_files = cap_files > 0 and remaining_files > cap_files
        if not over_bytes and not over_files:
            break
        freed = _remove_fg_response_bundle_files(npz)
        if freed:
            removed += freed
            total_bytes -= size
            remaining_files -= 1
    return removed


def sweep_fg_response_frontier_live_cache(
    *,
    idle_ttl_seconds: float | None = None,
    now_mono: float | None = None,
    now_wall: float | None = None,
    max_disk_bytes: int | None = None,
    max_disk_files: int | None = None,
) -> int:
    ttl = _fg_response_idle_ttl_seconds() if idle_ttl_seconds is None else idle_ttl_seconds
    if ttl is None or ttl <= 0.0:
        return 0
    disk_ttl = _fg_response_disk_idle_ttl_seconds(ttl)
    removed = 0
    moment_mono = time.monotonic() if now_mono is None else float(now_mono)
    with _frontier_cache_lock:
        removed += _sweep_fg_response_memory_cache_locked(
            _frontier_cache,
            _frontier_cache_last_access,
            idle_ttl_seconds=ttl,
            moment=moment_mono,
        )
        removed += _sweep_fg_response_memory_cache_locked(
            _payload_cache,
            _payload_cache_last_access,
            idle_ttl_seconds=ttl,
            moment=moment_mono,
        )
        removed += _sweep_fg_response_memory_cache_locked(
            _bundle_array_cache,
            _bundle_array_cache_last_access,
            idle_ttl_seconds=ttl,
            moment=moment_mono,
        )
        removed += _sweep_fg_response_memory_cache_locked(
            _scoring_bundle_cache,
            _scoring_bundle_cache_last_access,
            idle_ttl_seconds=ttl,
            moment=moment_mono,
        )
    if disk_ttl is not None and disk_ttl > 0.0:
        moment_wall = time.time() if now_wall is None else float(now_wall)
        try:
            bundle_paths = tuple(_fg_response_disk_cache_dir().glob("*.npz"))
        except OSError:
            bundle_paths = ()
        for bundle_path in bundle_paths:
            if not bundle_path.exists():
                continue
            try:
                stat = bundle_path.stat()
            except OSError:
                continue
            if moment_wall - float(stat.st_mtime) <= float(disk_ttl):
                continue
            removed += _remove_fg_response_bundle_files(bundle_path)
    # Hard size/file cap (serving-mode): after the idle-TTL pass, evict the oldest bundles until
    # the on-disk cache is within budget. Runs independently of the disk TTL (the cap bounds total
    # SSD even when many songs are touched inside one TTL window). Pure disk I/O, idempotent.
    removed += _enforce_fg_response_disk_cap(
        max_disk_bytes=max_disk_bytes,
        max_disk_files=max_disk_files,
    )
    return removed
