from __future__ import annotations

import concurrent.futures
import logging
import time
from dataclasses import dataclass
from typing import Iterable

from gear_optimizer.solver.fg_response_frontier_cache_prebuild import (
    FgResponseFrontierCachePrebuildSummary,
    run_fg_response_frontier_cache_prebuild,
)
from gear_optimizer.solver.timeline_frontier_cache_prebuild import (
    TimelineFrontierCachePrebuildSummary,
    run_timeline_frontier_cache_prebuild,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FrontierCachePrebuildSummary:
    timeline: TimelineFrontierCachePrebuildSummary
    fg_response: FgResponseFrontierCachePrebuildSummary
    elapsed_ms: float


def _empty_timeline_summary() -> TimelineFrontierCachePrebuildSummary:
    return TimelineFrontierCachePrebuildSummary(total=0)


def _empty_fg_summary() -> FgResponseFrontierCachePrebuildSummary:
    return FgResponseFrontierCachePrebuildSummary(total=0)


def run_frontier_cache_prebuilds(
    *,
    cfg,
    song_queue: Iterable[tuple],
    ref_arrays: dict,
    data_root,
) -> FrontierCachePrebuildSummary:
    """
    Coordinate exact frontier cache construction before Taichi scoring.

    Timeline frontier construction intentionally remains on the existing CPU
    path. FG response-frontier construction uses the exact full-budget FT/FF
    cache owner and runs unconditionally during startup.
    """
    queue_items = list(song_queue or [])
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="FrontierCache") as executor:
        timeline_future = executor.submit(
            run_timeline_frontier_cache_prebuild,
            cfg=cfg,
            song_queue=queue_items,
            ref_arrays=ref_arrays,
            data_root=data_root,
        )
        fg_future = executor.submit(
            run_fg_response_frontier_cache_prebuild,
            cfg=cfg,
            song_queue=queue_items,
            ref_arrays=ref_arrays,
            data_root=data_root,
        )
        timeline_summary = timeline_future.result() if timeline_future is not None else _empty_timeline_summary()
        fg_summary = fg_future.result() if fg_future is not None else _empty_fg_summary()
    elapsed_ms = float((time.perf_counter() - started) * 1000.0)
    logger.info(
        "[FrontierCache] Prebuild phases ready: timeline built=%s disk=%s failures=%s; fg built=%s disk=%s failures=%s; elapsed=%.1fs",
        int(timeline_summary.built),
        int(timeline_summary.disk),
        int(timeline_summary.failures),
        int(fg_summary.built),
        int(fg_summary.disk),
        int(fg_summary.failures),
        elapsed_ms / 1000.0,
    )
    return FrontierCachePrebuildSummary(
        timeline=timeline_summary,
        fg_response=fg_summary,
        elapsed_ms=elapsed_ms,
    )


__all__ = [
    "FrontierCachePrebuildSummary",
    "run_frontier_cache_prebuilds",
]
