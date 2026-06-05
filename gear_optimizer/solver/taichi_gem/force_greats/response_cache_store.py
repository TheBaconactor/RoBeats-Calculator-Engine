from __future__ import annotations

import threading
import time
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

import numpy as np
from numpy.lib import format as np_format

from gear_optimizer.core.constants import TOTAL_ROWS

from .response_cache_keys import _fg_response_disk_cache_path, _fg_response_cache_version
from .response_cache_types import (
    _BUNDLE_ARRAY_CACHE_MAX,
    _MEMORY_CACHE_MAX,
    _PAYLOAD_CACHE_MAX,
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
                "stat_keys": np.asarray([key for key, _frontier in sorted_items], dtype=np.int32),
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
                "first_surface_head_len": np.asarray(int(first_surface_head_len), dtype=np.int32),
                "first_surface_head_coeffs": np.ascontiguousarray(first_surface_head_coeffs, dtype=np.uint16),
                **packed_frontiers,
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


def _payload_disk_info_if_complete(
    cache_key: tuple,
    keys: Iterable[tuple[int, int]],
) -> tuple[int, int, int] | None:
    requested = set(normalize_fg_response_stat_keys(keys))
    path = _fg_response_disk_cache_path(cache_key)
    if not path.exists():
        return None
    required = {
        "version",
        "stat_keys",
        "frontier_ids",
        "frontier_meta",
        "first_offsets",
        "first_counts",
        "first_surface_pool",
        "total_notes",
        "long_notes",
    }
    try:
        with np.load(path, allow_pickle=False) as data:
            if not required.issubset(set(data.files)):
                return None
            version = str(data["version"].item())
            if version != _fg_response_cache_version():
                return None
            stat_keys = np.asarray(data["stat_keys"], dtype=np.int32)
            frontier_ids = np.asarray(data["frontier_ids"], dtype=np.int32)
            meta = np.asarray(data["frontier_meta"], dtype=np.int32)
            if int(stat_keys.shape[0]) != int(frontier_ids.shape[0]):
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
                int(np.asarray(data["total_notes"]).item()),
                int(np.asarray(data["long_notes"]).item()),
                int(len(requested)),
            )
    except Exception:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        return None


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


def _load_bundle_array_members_if_present(cache_key: tuple, *, names: Iterable[str]) -> dict[str, np.ndarray]:
    requested = tuple(dict.fromkeys(str(name) for name in names))
    if not requested:
        return {}
    with _frontier_cache_lock:
        cached = _bundle_array_cache.get(cache_key)
        if cached is not None and all(name in cached for name in requested):
            _bundle_array_cache.move_to_end(cache_key)
            return {name: cached[name] for name in requested}
    path = _fg_response_disk_cache_path(cache_key)
    if not path.exists():
        return {}
    with np.load(path, allow_pickle=False) as data:
        version = str(data["version"].item())
        if version != _fg_response_cache_version():
            return {}
        present = [name for name in requested if name in data.files]
        loaded = {name: np.asarray(data[name]) for name in present}
    if not loaded:
        return {}
    with _frontier_cache_lock:
        cached = _bundle_array_cache.get(cache_key)
        if cached is None:
            cached = {}
            _bundle_array_cache[cache_key] = cached
        cached.update(loaded)
        while len(_bundle_array_cache) > int(_BUNDLE_ARRAY_CACHE_MAX):
            _bundle_array_cache.popitem(last=False)
        _bundle_array_cache.move_to_end(cache_key)
        return {name: cached[name] for name in present}


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
