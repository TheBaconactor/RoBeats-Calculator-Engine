from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from gear_optimizer.core.utils import cfg_from_dict
from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
from gear_optimizer.solver.song_db_context import PreparedSongDbContext, load_prepared_song_db_context

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
    force_greats_finder: bool
    force_greats_config: Any
    manual_force_greats: bool


@dataclass(frozen=True, slots=True)
class PreparedSongCore:
    cfg: Any
    calc_song: dict[str, Any]
    prepared_calc_song: PreparedCalcSong
    prepared_config: PreparedSongConfig
    db_context: PreparedSongDbContext
    meta_primary_color: str
    meta_secondary_color: str
    setup_sec: float
    db_load_sec: float


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


def build_prepared_song_core(
    *,
    fp: str,
    found_song_name: str,
    cfg_dict: dict[str, Any],
    auto_buff: bool,
    paths,
    gears_by_name: dict,
    minis_by_name: dict,
    cfg: Any | None = None,
    preloaded_calc_song: dict[str, Any] | None = None,
    load_known_loadouts: bool,
    allow_fallback: bool = False,
    cache_seed_context: bool = False,
) -> PreparedSongCore:
    cfg_obj = cfg if cfg is not None else cfg_from_dict(cfg_dict)
    prepared_calc_song = build_prepared_calc_song(
        fp=fp,
        cfg_dict=cfg_dict,
        preloaded_calc_song=preloaded_calc_song,
    )
    calc_song = prepared_calc_song.calc_song

    t_setup0 = time.perf_counter()
    prepared_config = build_prepared_song_config(
        cfg=cfg_obj,
        calc_song=calc_song,
        auto_buff=bool(auto_buff),
        paths=paths,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
    )
    setup_sec = time.perf_counter() - t_setup0

    t_db0 = time.perf_counter()
    db_context = load_prepared_song_db_context(
        found_song_name=found_song_name,
        calc_song=calc_song,
        cfg=cfg_obj,
        cfg_dict=cfg_dict,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        load_known_loadouts=bool(load_known_loadouts),
        allow_fallback=bool(allow_fallback),
        cache_seed_context=bool(cache_seed_context),
    )
    db_load_sec = time.perf_counter() - t_db0

    metadata = calc_song.get("metadata", {}) if isinstance(calc_song, dict) else {}
    return PreparedSongCore(
        cfg=cfg_obj,
        calc_song=calc_song,
        prepared_calc_song=prepared_calc_song,
        prepared_config=prepared_config,
        db_context=db_context,
        meta_primary_color=str(metadata.get("Primary Color", "") or ""),
        meta_secondary_color=str(metadata.get("Secondary Color", "") or ""),
        setup_sec=float(setup_sec),
        db_load_sec=float(db_load_sec),
    )
