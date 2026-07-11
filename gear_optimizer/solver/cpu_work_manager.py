from __future__ import annotations

import logging
import sys
import time
from typing import TextIO

from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.fg_response_frontier_cache_prebuild import run_fg_response_frontier_cache_prebuild
from gear_optimizer.solver.timeline_frontier_cache_prebuild import run_timeline_frontier_cache_prebuild

logger = logging.getLogger(__name__)


def run_startup_cpu_work(
    *,
    cfg,
    song_queue,
    ref_arrays: dict,
    data_root,
    announce_stream: TextIO | None = None,
) -> None:
    stream = announce_stream or sys.stdout
    queue_items = list(song_queue or [])
    message = f"[Startup][Cache] Filling missing timeline and FG frontiers for {len(queue_items)} queued song(s)."
    stream.write(f"{message}\n")
    stream.flush()
    logger.info(message)
    started = time.perf_counter()
    timeline_summary = run_timeline_frontier_cache_prebuild(
        cfg=cfg,
        song_queue=queue_items,
        ref_arrays=ref_arrays,
        data_root=data_root,
    )
    fg_summary = run_fg_response_frontier_cache_prebuild(
        cfg=cfg,
        song_queue=queue_items,
        ref_arrays=ref_arrays,
        data_root=data_root,
    )
    elapsed_ms = float((time.perf_counter() - started) * 1000.0)
    summary_message = (
        f"[Startup][Cache] Frontier caches ready: timeline_total={int(timeline_summary.total)} "
        f"timeline_built={int(timeline_summary.built)} timeline_disk={int(timeline_summary.disk)} "
        f"timeline_failures={int(timeline_summary.failures)} fg_total={int(fg_summary.total)} "
        f"fg_built={int(fg_summary.built)} fg_disk={int(fg_summary.disk)} "
        f"fg_failures={int(fg_summary.failures)} "
        f"elapsed={elapsed_ms / 1000.0:.1f}s"
    )
    stream.write(f"{summary_message}\n")
    stream.flush()
    logger.info(summary_message)
    emit_profile_event(
        component="cpu_work_manager",
        event="startup_cpu_work_done",
        metrics={
            "phase": "timeline_and_fg_frontier_data",
            "timeline_total": int(timeline_summary.total),
            "timeline_completed": int(timeline_summary.completed),
            "timeline_failures": int(timeline_summary.failures),
            "timeline_built": int(timeline_summary.built),
            "timeline_disk": int(timeline_summary.disk),
            "fg_total": int(fg_summary.total),
            "fg_completed": int(fg_summary.completed),
            "fg_failures": int(fg_summary.failures),
            "fg_built": int(fg_summary.built),
            "fg_disk": int(fg_summary.disk),
            "elapsed_ms": elapsed_ms,
        },
    )
    if int(timeline_summary.failures) or int(fg_summary.failures):
        raise RuntimeError(
            "Startup frontier cache build failed: "
            f"timeline_failures={int(timeline_summary.failures)} "
            f"fg_failures={int(fg_summary.failures)}"
        )
