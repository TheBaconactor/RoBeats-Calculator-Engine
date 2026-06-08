from __future__ import annotations

import threading
import time
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from numpy.lib import format as np_format

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.profile_events import emit_profile_event

from .response_cache_keys import _fg_response_disk_cache_path, _fg_response_cache_version
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
_frontier_cache_lock = threading.RLock()
_RESPONSE_BUNDLE_BUILD_PARALLELISM = 1
_response_bundle_build_slots = threading.BoundedSemaphore(int(_RESPONSE_BUNDLE_BUILD_PARALLELISM))
_NPZ_FAST_COMPRESS_LEVEL = 1
# Row granularity for on-disk first-surface npz members. This is a fetch-granularity knob
# (smaller chunks -> more members but less over-read per live fetch), not a GPU/TDR dispatch
# bound -- these rows never size a kernel launch.
_FIRST_SURFACE_CHUNK_ROWS = 32768


def _first_surface_pool_chunk_name(chunk_idx: int) -> str:
    return f"first_surface_pool_chunk_{int(chunk_idx):05d}"


def _first_surface_head_coeff_chunk_name(chunk_idx: int) -> str:
    return f"first_surface_head_coeffs_chunk_{int(chunk_idx):05d}"


def _named_row_chunks(
    rows: np.ndarray,
    name_fn: Callable[[int], str],
    transform: Callable[[np.ndarray], np.ndarray],
) -> dict[str, np.ndarray]:
    row_count = int(rows.shape[0])
    chunks: dict[str, np.ndarray] = {}
    for chunk_idx, start in enumerate(range(0, row_count, int(_FIRST_SURFACE_CHUNK_ROWS))):
        end = min(row_count, int(start) + int(_FIRST_SURFACE_CHUNK_ROWS))
        chunks[name_fn(chunk_idx)] = transform(rows[int(start) : int(end)])
    return chunks


def _as_uint8_exact(name: str, values: np.ndarray) -> np.ndarray:
    array = np.asarray(values)
    if array.size:
        min_value = int(np.min(array))
        max_value = int(np.max(array))
        info = np.iinfo(np.uint8)
        if min_value < int(info.min) or max_value > int(info.max):
            raise ValueError(f"{name} exceeds persisted uint8 bounds: {min_value}..{max_value}")
    return np.asarray(array, dtype=np.uint8)


def _persisted_packed_frontiers(packed_frontiers: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    first_surface_pool = np.asfortranarray(np.asarray(packed_frontiers["first_surface_pool"], dtype=np.uint32))
    row_count = int(first_surface_pool.shape[0])
    chunk_offsets = np.asarray(
        list(range(0, row_count, int(_FIRST_SURFACE_CHUNK_ROWS))) + [row_count],
        dtype=np.int32,
    )
    return {
        "frontier_meta": np.asfortranarray(np.asarray(packed_frontiers["frontier_meta"], dtype=np.int32)),
        "first_offsets": np.asarray(packed_frontiers["first_offsets"], dtype=np.int32),
        "first_counts": np.asarray(packed_frontiers["first_counts"], dtype=np.int32),
        "first_surface_chunk_offsets": chunk_offsets,
        **_named_row_chunks(first_surface_pool, _first_surface_pool_chunk_name, np.asfortranarray),
    }


def _persisted_surface_head_coeff_chunks(first_surface_head_coeffs: np.ndarray) -> dict[str, np.ndarray]:
    coeffs = np.ascontiguousarray(np.asarray(first_surface_head_coeffs, dtype=np.uint16))
    return _named_row_chunks(coeffs, _first_surface_head_coeff_chunk_name, np.ascontiguousarray)


def _memory_get(cache_key: tuple) -> FgResponseFrontierResult | None:
    with _frontier_cache_lock:
        frontier = _frontier_cache.get(cache_key)
        if frontier is not None:
            _frontier_cache.move_to_end(cache_key)
        return frontier


def _frontier_is_complete(frontier: FgResponseFrontierResult | None) -> bool:
    return frontier is not None and bool(frontier.first_frontier)


def _memory_put(cache_key: tuple, frontier: FgResponseFrontierResult) -> None:
    if not frontier.first_frontier:
        raise ValueError("FG response frontier cache requires first-frontier surfaces")
    with _frontier_cache_lock:
        _frontier_cache[cache_key] = frontier
        _frontier_cache.move_to_end(cache_key)
        while len(_frontier_cache) > int(_MEMORY_CACHE_MAX):
            _frontier_cache.popitem(last=False)


def _payload_memory_get(cache_key: tuple) -> FgResponseFrontierCachePayload | None:
    with _frontier_cache_lock:
        payload = _payload_cache.get(cache_key)
        if payload is not None:
            _payload_cache.move_to_end(cache_key)
        return payload


def _payload_memory_put(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    with _frontier_cache_lock:
        _payload_cache[cache_key] = payload
        _payload_cache.move_to_end(cache_key)
        while len(_payload_cache) > int(_PAYLOAD_CACHE_MAX):
            _payload_cache.popitem(last=False)


def reset_fg_response_frontier_payload_cache() -> None:
    with _frontier_cache_lock:
        _frontier_cache.clear()
        _payload_cache.clear()
        _bundle_array_cache.clear()
        _scoring_bundle_cache.clear()


def _save_payload(cache_key: tuple, payload: FgResponseFrontierCachePayload) -> None:
    from .response_cache_serde import _pack_frontiers
    from .response_inner_host import _precompute_surface_head_coeffs

    path = _fg_response_disk_cache_path(cache_key)
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{threading.get_ident()}.{time.perf_counter_ns()}.tmp.npz")
        frontiers = payload.frontiers
        frontier_id_by_object = {id(frontier): idx for idx, frontier in enumerate(frontiers)}
        sorted_items = sorted(payload.frontier_by_key.items())
        packed_frontiers = _pack_frontiers(frontiers)
        first_surface_pool = np.asarray(packed_frontiers["first_surface_pool"], dtype=np.uint32)
        stat_keys = np.asarray([key for key, _frontier in sorted_items], dtype=np.int32)
        first_surface_head_len = min(int(payload.total_notes), 100)
        first_surface_head_coeffs = _precompute_surface_head_coeffs(
            first_surface_pool,
            head_len=int(first_surface_head_len),
        )
        if bool(np.any(first_surface_head_coeffs < 0)) or bool(np.any(first_surface_head_coeffs > np.iinfo(np.uint16).max)):
            raise ValueError("FG response surface head coefficients exceed persisted uint16 bounds")
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
                **_persisted_packed_frontiers(packed_frontiers),
                **_persisted_surface_head_coeff_chunks(first_surface_head_coeffs),
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

    path = _fg_response_disk_cache_path(cache_key)
    if not path.exists():
        return None
    try:
        with np.load(path, allow_pickle=False) as data:
            version = str(data["version"].item())
            if version != _fg_response_cache_version():
                return None
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            frontiers = _unpack_frontiers(data)
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
            return payload
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def _npz_array_header(archive: zipfile.ZipFile, array_name: str) -> tuple[tuple[int, ...], np.dtype] | None:
    try:
        with archive.open(f"{array_name}.npy", mode="r") as handle:
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


def _payload_file_info_if_complete(path: Path, keys: Iterable[tuple[int, int]]) -> tuple[int, int, int] | None:
    requested = set(normalize_fg_response_stat_keys(keys))
    if not path.exists():
        return None
    required = {"version", *_SCORING_BUNDLE_ARRAY_NAMES}
    try:
        with np.load(path, allow_pickle=False) as data:
            files = set(data.files)
            if not required.issubset(files):
                return None
            version = str(data["version"].item())
            if version != _fg_response_cache_version():
                return None
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            meta = np.asarray(data["frontier_meta"], dtype=np.int32)
            chunk_offsets = np.asarray(data["first_surface_chunk_offsets"], dtype=np.int64).reshape(-1)
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
            if int(chunk_offsets.shape[0]) < 2 or int(chunk_offsets[0]) != 0:
                return None
            if bool(np.any(chunk_offsets[1:] < chunk_offsets[:-1])):
                return None
            if bool(np.any(first_offsets < 0)) or bool(np.any(first_counts <= 0)):
                return None
            max_surface_end = int(np.max(first_offsets + first_counts))
            if int(chunk_offsets[-1]) < max_surface_end:
                return None
            expected_files = set(required)
            archive = data.zip
            for chunk_idx in range(int(chunk_offsets.shape[0]) - 1):
                start = int(chunk_offsets[int(chunk_idx)])
                end = int(chunk_offsets[int(chunk_idx) + 1])
                row_count = int(end - start)
                pool_name = _first_surface_pool_chunk_name(chunk_idx)
                coeff_name = _first_surface_head_coeff_chunk_name(chunk_idx)
                expected_files.add(pool_name)
                expected_files.add(coeff_name)
                if pool_name not in files or coeff_name not in files:
                    return None
                pool_header = _npz_array_header(archive, pool_name)
                coeff_header = _npz_array_header(archive, coeff_name)
                if pool_header != ((row_count, 11), np.dtype(np.uint32)):
                    return None
                if coeff_header != ((row_count, 4), np.dtype(np.uint16)):
                    return None
            if files != expected_files:
                return None
            present: set[tuple[int, int]] = set()
            for idx, key_row in enumerate(stat_keys):
                frontier_idx = int(frontier_ids[int(idx)])
                if frontier_idx < 0 or frontier_idx >= int(meta.shape[0]):
                    return None
                present.add(_normalize_stat_key((int(key_row[0]), int(key_row[1]))))
            if not requested.issubset(present):
                return None
            return (
                int(total_notes),
                int(long_notes),
                int(len(requested)),
            )
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
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
        cached = _bundle_array_cache.get(cache_key)
        if cached is not None and all(name in cached for name in requested):
            _bundle_array_cache.move_to_end(cache_key)
            return {name: cached[name] for name in requested}
    path = _fg_response_disk_cache_path(cache_key)
    if not path.exists():
        raise ValueError(f"FG response frontier bundle cache is missing: {path}")
    with np.load(path, allow_pickle=False) as data:
        version = str(data["version"].item())
        if version != _fg_response_cache_version():
            raise ValueError("FG response frontier bundle cache version is invalid")
        missing = [name for name in requested if name not in data.files]
        if missing:
            raise ValueError(f"FG response frontier bundle cache is missing arrays: {missing[:5]!r}")
        loaded = {name: np.asarray(data[name]) for name in requested}
    with _frontier_cache_lock:
        cached = _bundle_array_cache.get(cache_key)
        if cached is None:
            cached = {}
            _bundle_array_cache[cache_key] = cached
        cached.update(loaded)
        while len(_bundle_array_cache) > int(_BUNDLE_ARRAY_CACHE_MAX):
            _bundle_array_cache.popitem(last=False)
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


def _chunk_span_for_range(offsets: np.ndarray, start: int, end: int) -> tuple[int, int]:
    first_chunk = int(np.searchsorted(offsets, int(start), side="right") - 1)
    last_chunk = int(np.searchsorted(offsets, int(end) - 1, side="right") - 1)
    return first_chunk, last_chunk


def _surface_chunk_indices_for_ranges(chunk_offsets: np.ndarray, ranges: tuple[tuple[int, int], ...]) -> tuple[int, ...]:
    offsets = np.asarray(chunk_offsets, dtype=np.int64).reshape(-1)
    if int(offsets.shape[0]) < 2 or int(offsets[0]) != 0 or bool(np.any(offsets[1:] < offsets[:-1])):
        raise ValueError("FG response surface chunk offsets are invalid")
    total_rows = int(offsets[-1])
    needed: set[int] = set()
    for start, count in ranges:
        end = int(start) + int(count)
        if end > total_rows:
            raise ValueError("FG response surface range exceeds cached rows")
        first_chunk, last_chunk = _chunk_span_for_range(offsets, int(start), end)
        if first_chunk < 0 or last_chunk >= int(offsets.shape[0]) - 1:
            raise ValueError("FG response surface range resolved outside chunk offsets")
        needed.update(range(first_chunk, last_chunk + 1))
    return tuple(sorted(needed))


def _copy_chunked_rows(
    *,
    out: np.ndarray,
    column_count: int,
    chunk_offsets: np.ndarray,
    chunks: dict[int, np.ndarray],
    ranges: tuple[tuple[int, int], ...],
) -> None:
    offsets = np.asarray(chunk_offsets, dtype=np.int64).reshape(-1)
    out_cursor = 0
    for start, count in ranges:
        end = int(start) + int(count)
        first_chunk, last_chunk = _chunk_span_for_range(offsets, int(start), end)
        for chunk_idx in range(first_chunk, last_chunk + 1):
            chunk_start = int(offsets[int(chunk_idx)])
            chunk_end = int(offsets[int(chunk_idx) + 1])
            copy_start = max(int(start), chunk_start)
            copy_end = min(end, chunk_end)
            chunk = np.asarray(chunks[int(chunk_idx)])
            if int(chunk.ndim) != 2 or int(chunk.shape[1]) != int(column_count):
                raise ValueError("FG response surface chunk shape is invalid")
            local_start = int(copy_start) - chunk_start
            local_end = int(copy_end) - chunk_start
            out[out_cursor : out_cursor + (copy_end - copy_start)] = chunk[local_start:local_end]
            out_cursor += int(copy_end - copy_start)
    if out_cursor != int(out.shape[0]):
        raise ValueError("FG response surface chunk copy produced the wrong row count")


def load_first_surface_scoring_rows(
    cache_key: tuple,
    ranges: Iterable[tuple[int, int]],
) -> tuple[np.ndarray, np.ndarray]:
    started = time.perf_counter()
    normalized = _normalize_surface_ranges(ranges)
    offsets = np.asarray(
        _load_bundle_array_members(cache_key, names=("first_surface_chunk_offsets",))["first_surface_chunk_offsets"],
        dtype=np.int64,
    )
    chunk_indices = _surface_chunk_indices_for_ranges(offsets, normalized)
    pool_names = tuple(_first_surface_pool_chunk_name(chunk_idx) for chunk_idx in chunk_indices)
    coeff_names = tuple(_first_surface_head_coeff_chunk_name(chunk_idx) for chunk_idx in chunk_indices)
    loaded = _load_bundle_array_members(cache_key, names=pool_names + coeff_names)
    pool_chunks = {chunk_idx: np.asarray(loaded[_first_surface_pool_chunk_name(chunk_idx)], dtype=np.uint32) for chunk_idx in chunk_indices}
    coeff_chunks = {
        chunk_idx: np.asarray(loaded[_first_surface_head_coeff_chunk_name(chunk_idx)], dtype=np.int32)
        for chunk_idx in chunk_indices
    }
    row_count = sum(int(count) for _start, count in normalized)
    rows = np.empty((int(row_count), 11), dtype=np.uint32)
    coeffs = np.empty((int(row_count), 4), dtype=np.int32)
    _copy_chunked_rows(
        out=rows,
        column_count=11,
        chunk_offsets=offsets,
        chunks=pool_chunks,
        ranges=normalized,
    )
    _copy_chunked_rows(
        out=coeffs,
        column_count=4,
        chunk_offsets=offsets,
        chunks=coeff_chunks,
        ranges=normalized,
    )
    emit_profile_event(
        component="fg_response_cache",
        event="surface_chunk_load",
        metrics={
            "ranges": int(len(normalized)),
            "chunks": int(len(chunk_indices)),
            "rows": int(row_count),
            "elapsed_ms": float((time.perf_counter() - started) * 1000.0),
        },
    )
    return np.ascontiguousarray(rows, dtype=np.uint32), np.ascontiguousarray(coeffs, dtype=np.int32)


def _invalidate_bundle_array_views(bundle_key: tuple) -> None:
    with _frontier_cache_lock:
        _bundle_array_cache.pop(bundle_key, None)
        _scoring_bundle_cache.pop(bundle_key, None)


def _scoring_bundle_memory_get(bundle_key: tuple) -> FgResponseFrontierScoringBundle | None:
    with _frontier_cache_lock:
        cached = _scoring_bundle_cache.get(bundle_key)
        if cached is not None:
            _scoring_bundle_cache.move_to_end(bundle_key)
        return cached


def _scoring_bundle_memory_put(bundle_key: tuple, scoring_bundle: FgResponseFrontierScoringBundle) -> None:
    with _frontier_cache_lock:
        _scoring_bundle_cache[bundle_key] = scoring_bundle
        _scoring_bundle_cache.move_to_end(bundle_key)
        while len(_scoring_bundle_cache) > int(_BUNDLE_ARRAY_CACHE_MAX):
            _scoring_bundle_cache.popitem(last=False)
