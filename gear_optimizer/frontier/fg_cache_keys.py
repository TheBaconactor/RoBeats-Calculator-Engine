from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from gear_optimizer.solver.timing_envelope import TimedSong, fever_axes
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.frontier.cache_scope import scoped_frontier_cache_dir
from gear_optimizer.settings import paths

from . import fg_cache_types

_BUNDLE_KEY_MARKER = "all-stat-keys"


def fg_response_cache_version() -> str:
    return fg_cache_types.FG_RESPONSE_CACHE_VERSION


def fg_response_frontier_song_cache_key(song: TimedSong) -> tuple:
    """The song's part of its bundle key: the chart's counts and the FG inputs' float32 timelines and int32 lanes (the
    early-Great floor among them)."""
    song_inputs = song.fg_inputs
    return (
        song_inputs.total_notes,
        song_inputs.long_notes,
        song_inputs.last_note_time,
        song_inputs.use_forced_great_timing,
        array_sig16(song_inputs.timestamps),
        array_sig16(song_inputs.perfect_candidates),
        array_sig16(song_inputs.great_candidates),
        array_sig16(song_inputs.perfect_floor),
        array_sig16(song_inputs.great_floor),
        array_sig16(song_inputs.lanes),
        song.mode,
    )


def fg_response_frontier_bundle_cache_key(song: TimedSong, curves: StatCurves) -> tuple:
    return (
        fg_response_cache_version(),
        fg_response_frontier_song_cache_key(song),
        array_sig16(curves.f32["Fever Time"]),
        array_sig16(curves.f32["Fever Fill Rate"]),
        _BUNDLE_KEY_MARKER,
    )


def fg_response_disk_cache_dir() -> Path:
    scoped = scoped_frontier_cache_dir("fg_response")
    return scoped if scoped is not None else paths().fg_cache


def response_axes(song: TimedSong, curves: StatCurves) -> tuple[Any, np.ndarray, np.ndarray, np.ndarray]:
    """The song's FG inputs and its fever axes: per Fever Fill Rate value the fill threshold and the Perfects that
    fill the bar (its ceiling), per Fever Time value the fever duration."""
    song_inputs = song.fg_inputs
    real_time_by_ft, raw_fill_by_ff = fever_axes(
        song_inputs.total_notes, song_inputs.long_notes, song_inputs.last_note_time, curves
    )
    non_fever_base_by_ff = np.ceil(raw_fill_by_ff).astype(np.int32)
    return song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft
