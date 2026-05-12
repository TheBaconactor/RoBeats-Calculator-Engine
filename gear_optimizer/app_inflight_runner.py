from __future__ import annotations

import logging
import os
import sys
from typing import Any

from gear_optimizer.core.parsing import env_get, truthy
from gear_optimizer.core.utils import safe_int

logger = logging.getLogger(__name__)


class InflightRunner:
    """Owns app-level in-flight configuration normalization and sizing policy."""

    def __init__(self, app: Any):
        self._app = app

    def get_inflight_songs_requested(self, cfg) -> int:
        inflight_songs = int(self._app._current_runtime_settings(cfg).inflight.songs)

        try:
            inflight_songs_env = safe_int(env_get("IN_FLIGHT_SONGS", 0), 0)
            if inflight_songs_env > 0:
                inflight_songs = inflight_songs_env
        except Exception as e:
            logger.debug(f"app_inflight_runner:get_inflight_songs_requested: {e}")

        return inflight_songs

    def maybe_apply_ram_mode(self, cfg) -> None:
        runtime_settings = self._app._current_runtime_settings(cfg)
        inflight_songs = int(runtime_settings.inflight.songs)
        if int(inflight_songs) <= 1:
            return

        raw_env = env_get("INFLIGHT_RAM_MODE")
        env_set = raw_env is not None and str(raw_env).strip() != ""
        ram_mode = truthy(raw_env) if env_set else bool(runtime_settings.inflight.ram_mode)

        if not ram_mode:
            return

        os.environ.setdefault("INFLIGHT_RAM_MODE", "1")

        if env_get("INFLIGHT_SONG_FILE_CACHE_MAX") in {None, ""}:
            cache_max = int(runtime_settings.inflight.song_file_cache_max)
            if cache_max <= 0:
                cache_max = 2048
            os.environ["INFLIGHT_SONG_FILE_CACHE_MAX"] = str(cache_max)

        if env_get("TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX") in {None, ""}:
            tb_cache = int(runtime_settings.inflight.team_buff_calc_cache_max)
            if tb_cache <= 0:
                tb_cache = 256
            os.environ["TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX"] = str(tb_cache)

        try:
            logger.debug(
                "[InFlight][RAM] enabled: INFLIGHT_SONG_FILE_CACHE_MAX={} TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX={}".format(
                    env_get("INFLIGHT_SONG_FILE_CACHE_MAX"),
                    env_get("TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX"),
                )
            )
        except Exception as e:
            logger.debug(f"app_inflight_runner:maybe_apply_ram_mode: {e}")

    def maybe_autoset_gpu_song_slots(self, cfg) -> None:
        raw = env_get("GPU_SONG_SLOTS")
        if raw is not None and str(raw).strip() != "":
            return

        runtime_settings = self._app._current_runtime_settings(cfg)
        cfg_slots = int(runtime_settings.gpu.gpu_song_slots)
        if int(cfg_slots) > 0:
            os.environ["GPU_SONG_SLOTS"] = str(cfg_slots)
            try:
                logger.debug(
                    "[GPU] Set GPU_SONG_SLOTS={} from config (IterationEngine.GPU_SongSlots). Set GPU_SONG_SLOTS env var to override.".format(
                        int(cfg_slots)
                    )
                )
            except Exception as e:
                logger.debug(f"app_inflight_runner:maybe_autoset_gpu_song_slots: {e}")
            return

        inflight_songs = self.get_inflight_songs_requested(cfg)
        if int(inflight_songs) <= 1:
            return

        try:
            if "gear_optimizer.solver.taichi_gem.fields" in sys.modules:
                logger.debug("[GPU] Auto GPU_SONG_SLOTS skipped: taichi_gem.fields already imported.")
                return
        except Exception as e:
            logger.debug(f"app_inflight_runner:maybe_autoset_gpu_song_slots: {e}")

        ga_queue_mult = int(runtime_settings.gpu.ga_queue_mult)
        raw = env_get("INFLIGHT_GA_QUEUE_MULT")
        if raw is not None and str(raw).strip() != "":
            try:
                ga_queue_mult = int(raw)
            except Exception as e:
                logger.debug(f"app_inflight_runner:maybe_autoset_gpu_song_slots: {e}")
        if ga_queue_mult <= 0:
            raw_env = env_get("INFLIGHT_RAM_MODE")
            if raw_env is not None and str(raw_env).strip() != "":
                ram_mode = truthy(raw_env)
            else:
                ram_mode = bool(runtime_settings.inflight.ram_mode)
            ga_queue_mult = 4 if ram_mode else 2
        ga_queue_mult = max(1, min(int(ga_queue_mult), 8))

        required = int(inflight_songs) * int(ga_queue_mult) + 2
        slots = min(max(24, int(required)), 256)

        os.environ["GPU_SONG_SLOTS"] = str(slots)
        try:
            logger.debug(
                "[GPU] Auto-set GPU_SONG_SLOTS={} (InFlightSongs={}, InFlight_GA_QueueMult={}). Set GPU_SONG_SLOTS to override.".format(
                    int(slots),
                    int(inflight_songs),
                    int(ga_queue_mult),
                )
            )
        except Exception as e:
            logger.debug(f"app_inflight_runner:maybe_autoset_gpu_song_slots: {e}")
