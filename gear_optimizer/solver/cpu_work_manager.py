from __future__ import annotations

import logging
import time

from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.frontier_cache_prebuild import run_frontier_cache_prebuilds

logger = logging.getLogger(__name__)


class CpuWorkManager:
    """
    Central coordinator for startup CPU work that must complete before GPU init.

    This keeps expensive host-side preparation out of live GA/FG dispatch and
    gives the app one place to report CPU startup phases.
    """

    def run_startup(
        self,
        *,
        cfg,
        song_queue,
        ref_arrays: dict,
        data_root,
    ) -> None:
        t0 = time.perf_counter()
        logger.info("[Startup][CPU] Building exact frontier caches before Taichi init...")
        emit_profile_event(
            component="cpu_work_manager",
            event="startup_cpu_work_start",
            metrics={"phase": "frontier_caches"},
        )
        summary = run_frontier_cache_prebuilds(
            cfg=cfg,
            song_queue=song_queue,
            ref_arrays=ref_arrays,
            data_root=data_root,
        )
        elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
        timeline_summary = summary.timeline
        fg_summary = summary.fg_response
        logger.info(
            "[Startup][CPU] Timeline frontier cache ready: total=%s built=%s disk=%s memory=%s failures=%s elapsed=%.1fs",
            int(timeline_summary.total),
            int(timeline_summary.built),
            int(timeline_summary.disk),
            int(timeline_summary.memory),
            int(timeline_summary.failures),
            elapsed_ms / 1000.0,
        )
        emit_profile_event(
            component="cpu_work_manager",
            event="startup_cpu_work_done",
            metrics={
                "phase": "timeline_frontier_cache",
                "total": int(timeline_summary.total),
                "completed": int(timeline_summary.completed),
                "failures": int(timeline_summary.failures),
                "built": int(timeline_summary.built),
                "disk": int(timeline_summary.disk),
                "memory": int(timeline_summary.memory),
                "elapsed_ms": elapsed_ms,
            },
        )
        logger.info(
            "[Startup][CPU] FG response-frontier cache ready: total=%s built=%s disk=%s memory=%s failures=%s elapsed=%.1fs",
            int(fg_summary.total),
            int(fg_summary.built),
            int(fg_summary.disk),
            int(fg_summary.memory),
            int(fg_summary.failures),
            elapsed_ms / 1000.0,
        )
        emit_profile_event(
            component="cpu_work_manager",
            event="startup_cpu_work_done",
            metrics={
                "phase": "fg_response_frontier_cache",
                "total": int(fg_summary.total),
                "completed": int(fg_summary.completed),
                "failures": int(fg_summary.failures),
                "built": int(fg_summary.built),
                "disk": int(fg_summary.disk),
                "memory": int(fg_summary.memory),
                "elapsed_ms": elapsed_ms,
            },
        )
        return None
