from __future__ import annotations

import logging
import os
import sys
from typing import Any

from gear_optimizer.core.parsing import env_get
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
            ga_queue_mult = 2
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
