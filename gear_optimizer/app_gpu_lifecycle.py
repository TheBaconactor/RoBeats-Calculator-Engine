from __future__ import annotations

import logging
import os
from typing import Any

from gear_optimizer.core.constants import GA_POPULATION_SIZE
from gear_optimizer.core.profile_events import emit_profile_event

logger = logging.getLogger(__name__)


class GPULifecycleManager:
    """Owns app startup GPU policy, buffer sizing, and executor prewarm."""

    def __init__(self, app: Any, inflight_runner: Any):
        self._app = app
        self._inflight_runner = inflight_runner

    def configure_execution_and_prewarm(self, cfg) -> None:
        runtime_settings = self._app._current_runtime_settings(cfg)
        gpu_mode_requested = bool(runtime_settings.gpu.gpu_mode)
        if not gpu_mode_requested:
            logger.warning("[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); forcing GPU_Mode=true.")
            try:
                if not cfg.has_section("IterationEngine"):
                    cfg.add_section("IterationEngine")
                cfg.set("IterationEngine", "GPU_Mode", "true")
            except Exception:
                pass

        if bool(runtime_settings.gpu.gpu_native_ga):
            ga_multistart = max(1, int(runtime_settings.ga.multi_start))
            os.environ.setdefault("GPU_NATIVE_GA_MAX_RUNS", str(ga_multistart))
            os.environ.setdefault("GPU_NATIVE_GA_MAX_GENOMES", str(GA_POPULATION_SIZE))
            try:
                from gear_optimizer.solver.taichi_gem import fields as gpu_fields

                gpu_fields.configure_ga_run_buffers(max_runs=ga_multistart, max_genomes=int(GA_POPULATION_SIZE))
            except Exception:
                pass

        try:
            inflight_req = int(runtime_settings.inflight.songs or 0)
        except Exception:
            inflight_req = 0
        if inflight_req <= 1:
            return

        inflight_instances = self._inflight_runner.get_effective_inflight_instances(cfg)
        if int(inflight_instances) > 1:
            return

        try:
            logger.info("[Startup][GPU] Taichi/Vulkan init starting...")
            emit_profile_event(
                component="app",
                event="taichi_init_start",
                metrics={"in_process": 1},
            )
            from gear_optimizer.solver.gpu_executor import get_gpu_executor

            get_gpu_executor().start(in_process=True)
            logger.info("[Startup][GPU] Taichi/Vulkan init ready.")
            emit_profile_event(
                component="app",
                event="taichi_init_done",
                metrics={"in_process": 1},
            )
        except Exception:
            pass
