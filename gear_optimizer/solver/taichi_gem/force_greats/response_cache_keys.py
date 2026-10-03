from __future__ import annotations

import hashlib
from math import ceil
from pathlib import Path
from typing import Any, Iterable

import numpy as np

from gear_optimizer.solver.timing_envelope import TimedSong, fever_fill_raw, fever_window_times
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.rules import MAX_STAT
from gear_optimizer.solver.frontier_cache_scope import scoped_frontier_cache_dir
from gear_optimizer.settings import paths

from . import response_cache_types
from .response_cache_types import (
    _BUNDLE_KEY_MARKER,
    _normalize_stat_key,
    normalize_fg_response_stat_keys,
)
from .response_types import FgResponseSurface


def _fg_response_cache_version() -> str:
    return str(response_cache_types._FG_RESPONSE_CACHE_VERSION)


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


def fg_response_frontier_song_cache_key(song: TimedSong) -> tuple:
    song_inputs = song.fg_inputs
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
        # The windowed modes carry their cache revisions; zero_ms's key stays as built.
        *((song.cache_mode,) if song.mode != "zero_ms" else ()),
    )


def _ref_axes_cache_key(curves: StatCurves) -> tuple[bytes, bytes]:
    ref_ft = curves.f32["Fever Time"]
    ref_ff = curves.f32["Fever Fill Rate"]
    return bytes(array_sig16(ref_ft)), bytes(array_sig16(ref_ff))


def fg_response_frontier_payload_cache_key(
    song: TimedSong,
    curves: StatCurves,
    stat_keys: Iterable[tuple[int, int]] | None,
) -> tuple:
    return (
        _fg_response_cache_version(),
        fg_response_frontier_song_cache_key(song),
        *_ref_axes_cache_key(curves),
        normalize_fg_response_stat_keys(stat_keys),
    )


def fg_response_frontier_bundle_cache_key(song: TimedSong, curves: StatCurves) -> tuple:
    return (
        _fg_response_cache_version(),
        fg_response_frontier_song_cache_key(song),
        *_ref_axes_cache_key(curves),
        _BUNDLE_KEY_MARKER,
    )


def fg_response_frontier_geometry_cache_key(
    song: TimedSong,
    curves: StatCurves,
    *,
    ft_stat: int,
    ff_stat: int,
) -> tuple:
    return (
        _fg_response_cache_version(),
        fg_response_frontier_song_cache_key(song),
        *_ref_axes_cache_key(curves),
        _normalize_stat_key((ft_stat, ff_stat)),
    )


def _fg_response_disk_cache_dir() -> Path:
    scoped = scoped_frontier_cache_dir("fg_response")
    return scoped if scoped is not None else paths().fg_cache


def _fg_response_disk_cache_path(cache_key: tuple) -> Path:
    digest = hashlib.blake2b(repr(cache_key).encode("utf-8"), digest_size=16).hexdigest()
    return _fg_response_disk_cache_dir() / f"{digest}.npz"


def _response_axes(song: TimedSong, curves: StatCurves) -> tuple[Any, np.ndarray, np.ndarray, np.ndarray]:
    song_inputs = song.fg_inputs
    ref_ft = curves.f32["Fever Time"]
    ref_ff = curves.f32["Fever Fill Rate"]
    if int(ref_ft.shape[0]) <= MAX_STAT or int(ref_ff.shape[0]) <= MAX_STAT:
        raise ValueError("FG response cache requires full Fever Time and Fever Fill Rate ref arrays")
    hit_objects = max(0, int(song_inputs.total_notes) - int(song_inputs.long_notes))
    raw_fill_by_ff = fever_fill_raw(hit_objects, ref_ff[: MAX_STAT + 1], song.mode)
    non_fever_base_by_ff = np.asarray([int(ceil(float(v))) for v in raw_fill_by_ff], dtype=np.int32)
    real_time_by_ft = fever_window_times(song_inputs.last_note_time, ref_ft[: MAX_STAT + 1], song.mode)
    return song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft
