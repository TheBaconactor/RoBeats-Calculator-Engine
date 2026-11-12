"""The timeline frontier cache's startup prebuild: missing charts build in a RAM-capped recycling process pool.

The driver (manifest, build lock, recording) is cache.prebuild_frontier_cache.
"""

from __future__ import annotations

import concurrent.futures

from gear_optimizer.core.cpu_affinity import frontier_prebuild_intra_worker_threads, timeline_prebuild_worker_count
from gear_optimizer.core.recycling_process_pool import BoundedRecyclingProcessPool
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.frontier.cache import (
    FrontierCacheBuildResult,
    FrontierCacheManifestPlan,
    FrontierCachePrebuild,
    PrebuildTally,
    build_frontier_cache_for_chart,
    init_prebuild_worker,
    prebuild_worker_curves,
)
from gear_optimizer.frontier.timeline_cache import TIMELINE_FRONTIER_CACHE, ensure_timeline_frontier_cache_for_song
from gear_optimizer.frontier.timeline_producer import configure_timeline_pair_build_threads

# Release native/NumPy allocator high-water before a full-pool worker reaches the heavy chart tail. Persistent
# workers exhausted commit after ~2,216 successes and then failed allocations as small as 1 MiB on the production
# 2,249-song pool.
_TIMELINE_PREBUILD_MAX_TASKS_PER_WORKER = 64


def _build_timeline_chart(chart_path: str, timing_mode: str) -> FrontierCacheBuildResult:
    return build_frontier_cache_for_chart(
        chart_path, prebuild_worker_curves(), timing_mode, ensure_timeline_frontier_cache_for_song
    )


def _build_timeline_charts(chart_paths: list[str], curves: StatCurves, timing_mode: str, tally: PrebuildTally) -> None:
    worker_count = timeline_prebuild_worker_count()
    with BoundedRecyclingProcessPool(
        max_workers=worker_count,
        initializer=init_prebuild_worker,
        initargs=(curves, configure_timeline_pair_build_threads, frontier_prebuild_intra_worker_threads(worker_count)),
        max_tasks_per_worker=_TIMELINE_PREBUILD_MAX_TASKS_PER_WORKER,
    ) as executor:
        futures = {executor.submit(_build_timeline_chart, path, timing_mode): path for path in chart_paths}
        for future in concurrent.futures.as_completed(futures):
            tally.collect(futures[future], future.result)


def _maintain_timeline_cache(_plan: FrontierCacheManifestPlan, _authorize_destructive_rotation: bool) -> None:
    TIMELINE_FRONTIER_CACHE.remove_temp_files()


TIMELINE_FRONTIER_PREBUILD = FrontierCachePrebuild(
    cache=TIMELINE_FRONTIER_CACHE,
    ensure=ensure_timeline_frontier_cache_for_song,
    build_in_pool=_build_timeline_charts,
    maintain=_maintain_timeline_cache,
)
