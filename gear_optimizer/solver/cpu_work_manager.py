from __future__ import annotations

import logging
import sys
import time
from typing import TextIO

from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.fg_response_frontier_cache_prebuild import run_fg_response_frontier_cache_prebuild

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
    message = (
        "[Startup][Cache] Timing-play frontier prebuild disabled; "
        f"building required fixed-0ms FG response data for {len(queue_items)} queued song(s)."
    )
    stream.write(f"{message}\n")
    stream.flush()
    logger.info(message)
    started = time.perf_counter()
    fg_summary = run_fg_response_frontier_cache_prebuild(
        cfg=cfg,
        song_queue=queue_items,
        ref_arrays=ref_arrays,
        data_root=data_root,
    )
    elapsed_ms = float((time.perf_counter() - started) * 1000.0)
    summary_message = (
        f"[Startup][Cache] Fixed-0ms FG response data ready: total={int(fg_summary.total)} "
        f"built={int(fg_summary.built)} disk={int(fg_summary.disk)} "
        f"memory={int(fg_summary.memory)} failures={int(fg_summary.failures)} "
        f"elapsed={elapsed_ms / 1000.0:.1f}s"
    )
    stream.write(f"{summary_message}\n")
    stream.flush()
    logger.info(summary_message)
    emit_profile_event(
        component="cpu_work_manager",
        event="startup_cpu_work_done",
        metrics={
            "phase": "fixed_zero_ms_fg_response_data",
            "total": int(fg_summary.total),
            "completed": int(fg_summary.completed),
            "failures": int(fg_summary.failures),
            "built": int(fg_summary.built),
            "disk": int(fg_summary.disk),
            "memory": int(fg_summary.memory),
            "elapsed_ms": elapsed_ms,
        },
    )
    if int(fg_summary.failures):
        raise RuntimeError(
            "Startup fixed-0ms FG response-data build failed: "
            f"failures={int(fg_summary.failures)}"
        )
