from __future__ import annotations

import logging
import os
import sys
from typing import Any

from gear_optimizer.core.parsing import env_get, truthy
from gear_optimizer.core.profile_events import emit_profile_event
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

    def get_inflight_instances_requested(self, cfg_or_dict) -> int:
        inflight_instances = 1
        try:
            if isinstance(cfg_or_dict, dict):
                ie = cfg_or_dict.get("IterationEngine")
                if not isinstance(ie, dict):
                    ie = cfg_or_dict.get("iterationengine", {})
                inflight_instances = safe_int(
                    ie.get("inflightinstances", ie.get("InFlightInstances", 1)) if isinstance(ie, dict) else 1,
                    1,
                )
            else:
                inflight_instances = int(self._app._current_runtime_settings(cfg_or_dict).inflight.instances)
        except Exception as e:
            logger.debug(f"app_inflight_runner:get_inflight_instances_requested: {e}")
            inflight_instances = 1

        raw_env_instances = env_get("INFLIGHT_INSTANCES")
        if raw_env_instances is not None and str(raw_env_instances).strip() != "":
            inflight_instances = max(1, safe_int(raw_env_instances, inflight_instances))

        return max(1, min(int(inflight_instances), 8))

    @staticmethod
    def dual_process_inflight_allowed() -> bool:
        return truthy(env_get("INFLIGHT_ALLOW_DUAL_PROCESS", "0"))

    def get_effective_inflight_instances(self, cfg_or_dict) -> int:
        requested_instances = self.get_inflight_instances_requested(cfg_or_dict)
        if int(requested_instances) <= 1:
            return 1
        if self.dual_process_inflight_allowed():
            return int(requested_instances)

        if not bool(getattr(self._app, "_logged_dual_process_quarantine", False)):
            try:
                logger.warning(
                    "[InFlight] Dual-process mode is quarantined on main; forcing single-process GPU ownership. "
                    "Set INFLIGHT_ALLOW_DUAL_PROCESS=1 to re-enable the experimental path."
                )
            except Exception as e:
                logger.debug(f"app_inflight_runner:get_effective_inflight_instances: {e}")
            try:
                emit_profile_event(
                    component="app",
                    event="inflight_dual_process_quarantined",
                    metrics={"requested_instances": int(requested_instances)},
                )
            except Exception as e:
                logger.debug(f"app_inflight_runner:get_effective_inflight_instances: {e}")
            try:
                self._app._logged_dual_process_quarantine = True
            except Exception as e:
                logger.debug(f"app_inflight_runner:get_effective_inflight_instances: {e}")

        return 1

    def apply_overrides(self, cfg) -> None:
        """Normalize config so InFlightSongs behaves predictably."""
        runtime_settings = self._app._current_runtime_settings(cfg)
        inflight_songs = int(runtime_settings.inflight.songs)
        if inflight_songs > 0:
            if not cfg.has_section("IterationEngine"):
                cfg.add_section("IterationEngine")
            cfg.set("IterationEngine", "InFlightSongs", str(inflight_songs))

        if inflight_songs <= 1:
            return

        gpu_mode_requested = bool(runtime_settings.gpu.gpu_mode)
        if not gpu_mode_requested:
            logger.warning(
                "[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); enabling GPU_Mode for in-flight."
            )
            try:
                cfg.set("IterationEngine", "GPU_Mode", "true")
            except Exception as e:
                logger.debug(f"app_inflight_runner:apply_overrides: {e}")

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
