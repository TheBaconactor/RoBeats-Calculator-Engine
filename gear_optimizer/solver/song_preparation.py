from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from gear_optimizer.data.mini_ascension import MiniAscensionSongContext, materialize_minis_for_song
from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
from gear_optimizer.helpers.song_helpers.song_config import baseline_fixed_stats
from gear_optimizer.solver.song_db_context import PreparedSongDbContext, load_prepared_song_db_context

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedCalcSong:
    calc_song: dict[str, Any]
    read_sec: float
    timing_envelope_sec: float
    timing_envelope_info: Any = None


@dataclass(frozen=True, slots=True)
class PreparedSongCore:
    calc_song: dict[str, Any]
    prepared_calc_song: PreparedCalcSong
    fixed_stats: dict[str, int]
    db_context: PreparedSongDbContext
    all_minis: list[dict[str, Any]]
    minis_by_name: dict[str, dict[str, Any]]
    mini_ascension_context: MiniAscensionSongContext
    meta_primary_color: str
    meta_secondary_color: str
    setup_sec: float
    db_load_sec: float


def _apply_timing_envelope(calc_song: dict[str, Any]) -> Any:
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    return apply_timing_envelope(calc_song)


def build_prepared_calc_song(
    *,
    fp: str,
    preloaded_calc_song: dict[str, Any] | None = None,
) -> PreparedCalcSong:
    if isinstance(preloaded_calc_song, dict) and preloaded_calc_song.get("song_data"):
        calc_song = clone_calc_song(preloaded_calc_song)
        read_sec = 0.0
    else:
        t_read0 = time.perf_counter()
        calc_song = clone_calc_song(get_base_calc_song(fp))
        read_sec = time.perf_counter() - t_read0

    song_data = calc_song.get("song_data", {}) or {}
    if "chart_timestamps" not in song_data and song_data.get("timestamps") is not None:
        song_data["chart_timestamps"] = np.asarray(song_data.get("timestamps"), dtype=np.float32)

    t_sim0 = time.perf_counter()
    timing_envelope_info = _apply_timing_envelope(calc_song)
    timing_envelope_sec = (time.perf_counter() - t_sim0) if timing_envelope_info is not None else 0.0

    return PreparedCalcSong(
        calc_song=calc_song,
        read_sec=float(read_sec),
        timing_envelope_sec=float(timing_envelope_sec),
        timing_envelope_info=timing_envelope_info,
    )


def build_prepared_song_core(
    *,
    fp: str,
    found_song_name: str,
    gears_by_name: dict,
    minis_by_name: dict,
    all_minis: list[dict] | None = None,
    preloaded_calc_song: dict[str, Any] | None = None,
    cache_db_context: bool = False,
) -> PreparedSongCore:
    prepared_calc_song = build_prepared_calc_song(
        fp=fp,
        preloaded_calc_song=preloaded_calc_song,
    )
    calc_song = prepared_calc_song.calc_song
    materialized_minis, materialized_minis_by_name, mini_ascension_context = materialize_minis_for_song(
        all_minis=all_minis,
        minis_by_name=minis_by_name,
        calc_song=calc_song,
        song_name=found_song_name,
    )

    t_setup0 = time.perf_counter()
    fixed_stats = baseline_fixed_stats(calc_song)
    setup_sec = time.perf_counter() - t_setup0

    t_db0 = time.perf_counter()
    db_context = load_prepared_song_db_context(
        found_song_name=found_song_name,
        calc_song=calc_song,
        gears_by_name=gears_by_name,
        minis_by_name=materialized_minis_by_name,
        cache_db_context=bool(cache_db_context),
    )
    db_load_sec = time.perf_counter() - t_db0

    metadata = calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}
    return PreparedSongCore(
        calc_song=calc_song,
        prepared_calc_song=prepared_calc_song,
        fixed_stats=fixed_stats,
        db_context=db_context,
        all_minis=materialized_minis,
        minis_by_name=materialized_minis_by_name,
        mini_ascension_context=mini_ascension_context,
        meta_primary_color=str(metadata.get("Primary Color", "") or ""),
        meta_secondary_color=str(metadata.get("Secondary Color", "") or ""),
        setup_sec=float(setup_sec),
        db_load_sec=float(db_load_sec),
    )
