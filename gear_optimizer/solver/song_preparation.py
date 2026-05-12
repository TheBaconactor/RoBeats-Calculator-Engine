from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PreparedCalcSong:
    calc_song: dict[str, Any]
    read_sec: float
    timing_envelope_sec: float
    timing_envelope_info: Any = None


@dataclass(frozen=True, slots=True)
class PreparedSongConfig:
    ga_settings: Any
    fixed_stats: dict[str, Any]
    current_gear_stats: dict[str, Any]
    current_gear_list: list[dict]
    current_mini_stats: dict[str, Any]
    current_mini_list: list[dict]
    meta_finder: bool
    enable_fever: bool
    enable_mini: bool
    enable_gear: bool
    force_greats_mode: bool
    force_greats_finder: bool
    force_greats_config: Any
    manual_force_greats: bool


def _apply_timing_envelope(calc_song: dict[str, Any]) -> Any:
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    return apply_timing_envelope(calc_song)


def _setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name):
    from gear_optimizer.helpers.song_helpers.song_config import setup_song_config

    return setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name)


def build_prepared_song_config(
    *,
    cfg,
    calc_song: dict[str, Any],
    auto_buff: bool,
    paths,
    gears_by_name: dict,
    minis_by_name: dict,
) -> PreparedSongConfig:
    (
        ga_settings,
        fixed_stats,
        current_gear_stats,
        current_gear_list,
        current_mini_stats,
        current_mini_list,
        meta_finder,
        enable_fever,
        enable_mini,
        enable_gear,
        force_greats_mode,
        force_greats_finder,
        force_greats_config,
        manual_force_greats,
    ) = _setup_song_config(cfg, calc_song, bool(auto_buff), paths, gears_by_name, minis_by_name)

    return PreparedSongConfig(
        ga_settings=ga_settings,
        fixed_stats=fixed_stats if isinstance(fixed_stats, dict) else {},
        current_gear_stats=current_gear_stats if isinstance(current_gear_stats, dict) else {},
        current_gear_list=current_gear_list if isinstance(current_gear_list, list) else [],
        current_mini_stats=current_mini_stats if isinstance(current_mini_stats, dict) else {},
        current_mini_list=current_mini_list if isinstance(current_mini_list, list) else [],
        meta_finder=bool(meta_finder),
        enable_fever=bool(enable_fever),
        enable_mini=bool(enable_mini),
        enable_gear=bool(enable_gear),
        force_greats_mode=bool(force_greats_mode),
        force_greats_finder=bool(force_greats_finder),
        force_greats_config=force_greats_config,
        manual_force_greats=bool(manual_force_greats),
    )


def build_prepared_calc_song(
    *,
    fp: str,
    cfg_dict: dict[str, Any] | None,
    preloaded_calc_song: dict[str, Any] | None = None,
) -> PreparedCalcSong:
    if isinstance(preloaded_calc_song, dict) and preloaded_calc_song.get("song_data"):
        calc_song = clone_calc_song(preloaded_calc_song)
        read_sec = 0.0
    else:
        t_read0 = time.perf_counter()
        calc_song = clone_calc_song(get_base_calc_song(fp, cfg_dict))
        read_sec = time.perf_counter() - t_read0

    song_data = calc_song.get("song_data", {}) or {}
    if "chart_timestamps" not in song_data and song_data.get("timestamps") is not None:
        song_data["chart_timestamps"] = np.asarray(song_data.get("timestamps"), dtype=np.float32)

    timing_envelope_sec = 0.0
    timing_envelope_info = None
    try:
        t_sim0 = time.perf_counter()
        timing_envelope_info = _apply_timing_envelope(calc_song)
        if timing_envelope_info is not None:
            timing_envelope_sec = time.perf_counter() - t_sim0
    except Exception as e:
        logger.debug(f"song_preparation:build_prepared_calc_song: {e}")

    return PreparedCalcSong(
        calc_song=calc_song,
        read_sec=float(read_sec),
        timing_envelope_sec=float(timing_envelope_sec),
        timing_envelope_info=timing_envelope_info,
    )
