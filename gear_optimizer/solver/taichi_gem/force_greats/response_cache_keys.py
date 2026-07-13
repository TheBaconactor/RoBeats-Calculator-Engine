from __future__ import annotations

import hashlib
from math import ceil
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.constants import PATHS, FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE, TOTAL_ROWS
from gear_optimizer.core.parsing import env_get
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs

from .response_cache_types import (
    _BUNDLE_KEY_MARKER,
    _normalize_stat_key,
    normalize_fg_response_stat_keys,
)
from .response_types import FgResponseSurface


def _fg_response_cache_version() -> str:
    from . import response_cache

    return str(response_cache._FG_RESPONSE_CACHE_VERSION)


def _surface_from_values_cached(
    values: tuple[int, ...], cache: dict[tuple[int, ...], FgResponseSurface]
) -> FgResponseSurface:
    surface = cache.get(values)
    if surface is None:
        if len(values) != 11:
            raise ValueError("FG response cache surface row must contain 11 values")
        surface = FgResponseSurface(*values)
        cache[values] = surface
    return surface


def _surface_from_row_cached(row: np.ndarray, cache: dict[tuple[int, ...], FgResponseSurface]) -> FgResponseSurface:
    return _surface_from_values_cached(tuple(int(v) for v in row[:11]), cache)


def fg_response_frontier_song_cache_key(calc_song: dict[str, Any]) -> tuple:
    song_inputs = extract_fg_song_inputs(calc_song)
    timestamps = np.asarray(song_inputs.timestamps, dtype=np.float32).reshape(-1)
    perfect_candidates = np.asarray(song_inputs.perfect_candidates, dtype=np.float32).reshape(-1)
    great_candidates = np.asarray(song_inputs.great_candidates, dtype=np.float32).reshape(-1)
    perfect_floor = np.asarray(song_inputs.perfect_floor, dtype=np.float32).reshape(-1)
    # Issue #44: the early-Great floor is part of the frontier inputs, so it joins the cache key.
    # Pre-#44 bundles (built without the early-Great surfaces) thus cannot be silently reused.
    great_floor = np.asarray(song_inputs.great_floor, dtype=np.float32).reshape(-1)
    lanes = np.asarray(song_inputs.lanes, dtype=np.int32).reshape(-1)
    if int(lanes.shape[0]) != int(timestamps.shape[0]):
        raise ValueError("FG response lanes length must match timestamps")
    return (
        int(song_inputs.total_notes),
        int(song_inputs.long_notes),
        float(song_inputs.last_note_time),
        bool(song_inputs.use_forced_great_timing),
        bytes(array_sig16(timestamps)),
        bytes(array_sig16(perfect_candidates)),
        bytes(array_sig16(great_candidates)),
        bytes(array_sig16(perfect_floor)),
        bytes(array_sig16(great_floor)),
        bytes(array_sig16(lanes)),
    )


def _ref_axes_cache_key(ref_arrays: dict[str, Any]) -> tuple[bytes, bytes]:
    ref_ft = np.asarray(ref_arrays.get("Fever Time", ()), dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays.get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    return bytes(array_sig16(ref_ft)), bytes(array_sig16(ref_ff))


def fg_response_frontier_payload_cache_key(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    stat_keys: Iterable[tuple[int, int]] | None,
) -> tuple:
    return (
        _fg_response_cache_version(),
        fg_response_frontier_song_cache_key(calc_song),
        *_ref_axes_cache_key(ref_arrays),
        normalize_fg_response_stat_keys(stat_keys),
    )


def fg_response_frontier_bundle_cache_key(calc_song: dict[str, Any], ref_arrays: dict[str, Any]) -> tuple:
    return (
        _fg_response_cache_version(),
        fg_response_frontier_song_cache_key(calc_song),
        *_ref_axes_cache_key(ref_arrays),
        _BUNDLE_KEY_MARKER,
    )


def fg_response_frontier_geometry_cache_key(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    ft_stat: int,
    ff_stat: int,
) -> tuple:
    return (
        _fg_response_cache_version(),
        fg_response_frontier_song_cache_key(calc_song),
        *_ref_axes_cache_key(ref_arrays),
        _normalize_stat_key((ft_stat, ff_stat)),
    )


def _fg_response_disk_cache_dir() -> Path:
    override = str(env_get("FG_RESPONSE_FRONTIER_CACHE_DIR", "") or "").strip()
    if override:
        return Path(override)
    return Path(PATHS.bin_path("fg_response_frontier_cache"))


def _fg_response_disk_cache_path(cache_key: tuple) -> Path:
    digest = hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()
    return _fg_response_disk_cache_dir() / f"{digest}.npz"


def _response_axes(calc_song: dict[str, Any], ref_arrays: dict[str, Any]) -> tuple[Any, np.ndarray, np.ndarray, np.ndarray]:
    song_inputs = extract_fg_song_inputs(calc_song)
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32).reshape(-1)
    if int(ref_ft.shape[0]) <= TOTAL_ROWS or int(ref_ff.shape[0]) <= TOTAL_ROWS:
        raise ValueError("FG response cache requires full Fever Time and Fever Fill Rate ref arrays")
    base_fill = max(0.0, float(song_inputs.total_notes - int(song_inputs.long_notes)) * float(FEVER_FILL_BASE_RATE))
    base_time = float(song_inputs.last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    raw_fill_by_ff = np.asarray([base_fill * float(ref_ff[idx]) for idx in range(TOTAL_ROWS + 1)], dtype=np.float64)
    non_fever_base_by_ff = np.asarray([int(ceil(float(v))) for v in raw_fill_by_ff], dtype=np.int32)
    real_time_by_ft = np.asarray([base_time * float(ref_ft[idx]) for idx in range(TOTAL_ROWS + 1)], dtype=np.float64)
    return song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft
