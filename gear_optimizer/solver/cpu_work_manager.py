from __future__ import annotations

import logging
import sys
import time
from typing import TextIO

from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.fg_response_frontier_cache_prebuild import run_fg_response_frontier_cache_prebuild
from gear_optimizer.solver.timeline_frontier_cache_prebuild import (
    TimelineFrontierCachePrebuildSummary,
    run_timeline_frontier_cache_prebuild,
)
from gear_optimizer.solver.timing_service_mode import strict_zero_ms

logger = logging.getLogger(__name__)


def _emit_summary(*, phase: str, label: str, summary, elapsed_ms: float) -> None:
    logger.info(
        "[Startup][CPU] %s ready: total=%s built=%s disk=%s memory=%s failures=%s elapsed=%.1fs",
        label,
        int(summary.total),
        int(summary.built),
        int(summary.disk),
        int(summary.memory),
        int(summary.failures),
        elapsed_ms / 1000.0,
    )
    emit_profile_event(
        component="cpu_work_manager",
        event="startup_cpu_work_done",
        metrics={
            "phase": phase,
            "total": int(summary.total),
            "completed": int(summary.completed),
            "failures": int(summary.failures),
            "built": int(summary.built),
            "disk": int(summary.disk),
            "memory": int(summary.memory),
            "elapsed_ms": elapsed_ms,
        },
    )


def _cache_summary_line(*, label: str, summary, elapsed_ms: float) -> str:
    return (
        f"[Startup][Cache] {label} ready: total={int(summary.total)} "
        f"built={int(summary.built)} disk={int(summary.disk)} memory={int(summary.memory)} "
        f"failures={int(summary.failures)} elapsed={elapsed_ms / 1000.0:.1f}s"
    )


def _announce_cache_summary(stream: TextIO, *, label: str, summary, elapsed_ms: float) -> None:
    stream.write(f"{_cache_summary_line(label=label, summary=summary, elapsed_ms=elapsed_ms)}\n")
    stream.flush()


def run_startup_cpu_work(
    *,
    cfg,
    song_queue,
    ref_arrays: dict,
    data_root,
    announce_stream: TextIO | None = None,
) -> None:
    message = "[Startup][Cache] Building and caching exact timeline + FG response frontiers before scoring..."
    stream = announce_stream or sys.stdout
    emit_profile_event(
        component="cpu_work_manager",
        event="startup_cpu_work_start",
        metrics={"phase": "frontier_caches"},
    )
    queue_items = list(song_queue or [])
    if queue_items:
        verify_message = (
            f"[Startup][Cache] Verifying exact timeline + FG response frontier caches for "
            f"{len(queue_items)} queued song(s) before scoring..."
        )
        stream.write(f"{verify_message}\n")
        stream.flush()
        logger.info(verify_message)
    timeline_t0 = time.perf_counter()
    if strict_zero_ms():
        # Strict zero_ms service mode: the perfect_window timeline frontier is never served here, so
        # its expensive candidate-frontier prebuild is skipped entirely. zero_ms serves the cheap
        # fixed chart-time singleton on demand (see timing_service_mode / _build_zero_ms_timeline_payload).
        # An empty summary keeps every downstream reader (announce/emit/failure gate) behaving exactly
        # as a clean, no-op timeline run would -- the FG prebuild and failure aggregation are unchanged.
        skip_message = (
            "[Startup][Cache] strict_zero_ms: skipping perfect_window timeline frontier prebuild "
            f"for {len(queue_items)} queued song(s); building fixed-0ms FG response data only."
        )
        stream.write(f"{skip_message}\n")
        stream.flush()
        logger.info(skip_message)
        timeline_summary = TimelineFrontierCachePrebuildSummary()
    else:
        timeline_summary = run_timeline_frontier_cache_prebuild(
            cfg=cfg,
            song_queue=queue_items,
            ref_arrays=ref_arrays,
            data_root=data_root,
        )
    timeline_elapsed_ms = float((time.perf_counter() - timeline_t0) * 1000.0)
    _announce_cache_summary(stream, label="Timeline frontier cache", summary=timeline_summary, elapsed_ms=timeline_elapsed_ms)
    fg_t0 = time.perf_counter()
    fg_summary = run_fg_response_frontier_cache_prebuild(
        cfg=cfg,
        song_queue=queue_items,
        ref_arrays=ref_arrays,
        data_root=data_root,
    )
    fg_elapsed_ms = float((time.perf_counter() - fg_t0) * 1000.0)
    _announce_cache_summary(stream, label="FG response-frontier cache", summary=fg_summary, elapsed_ms=fg_elapsed_ms)
    timeline_failures = int(timeline_summary.failures)
    fg_failures = int(fg_summary.failures)
    should_announce = bool(
        int(timeline_summary.built) > 0
        or int(fg_summary.built) > 0
        or timeline_failures > 0
        or fg_failures > 0
    )
    if should_announce:
        stream.write(f"{message}\n")
        stream.flush()
        logger.info(message)
    _emit_summary(
        phase="timeline_frontier_cache",
        label="Timeline frontier cache",
        summary=timeline_summary,
        elapsed_ms=timeline_elapsed_ms,
    )
    _emit_summary(
        phase="fg_response_frontier_cache",
        label="FG response-frontier cache",
        summary=fg_summary,
        elapsed_ms=fg_elapsed_ms,
    )
    if timeline_failures or fg_failures:
        raise RuntimeError(
            "Startup frontier cache prebuild failed: "
            f"timeline_failures={timeline_failures} fg_response_failures={fg_failures}"
        )
