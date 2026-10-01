"""The timeline frontier cache's startup prebuild: missing charts build in a RAM-capped recycling process pool.

The driver (manifest, build lock, recording) is frontier_cache.prebuild_frontier_cache.
"""

from __future__ import annotations

import concurrent.futures
from pathlib import Path

from gear_optimizer.core.cpu_affinity import frontier_prebuild_intra_worker_threads, timeline_prebuild_worker_count
from gear_optimizer.core.recycling_process_pool import BoundedRecyclingProcessPool
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.solver.frontier_cache import (
    FrontierCacheBuildResult,
    FrontierCacheManifestPlan,
    FrontierCachePrebuild,
    PrebuildTally,
    build_frontier_cache_for_chart,
    init_prebuild_worker,
    prebuild_worker_curves,
)
from gear_optimizer.solver.taichi_gem.api.timeline import (
    TIMELINE_FRONTIER_CACHE,
    build_or_load_timeline_frontier_payload,
    timeline_frontier_payload_cache_info,
)
from gear_optimizer.solver.timeline_exact_frontier import configure_timeline_pair_build_threads
from gear_optimizer.solver.timing_envelope import TimedSong

# Release native/NumPy allocator high-water before a full-pool worker reaches the heavy chart tail. Persistent
# workers exhausted commit after ~2,216 successes and then failed allocations as small as 1 MiB on the production
# 2,249-song pool.
_TIMELINE_PREBUILD_MAX_TASKS_PER_WORKER = 64


def _ensure_timeline_frontier_cache(song: TimedSong, curves: StatCurves) -> tuple[str, float, Path]:
    info = timeline_frontier_payload_cache_info(song, curves)
    if info.cache_source in {"disk", "memory"}:
        return info.cache_source, 0.0, info.disk_path
    result = build_or_load_timeline_frontier_payload(song, curves)
    return result.cache_source, result.elapsed_ms, result.disk_path


def _build_timeline_chart(chart_path: str, timing_mode: str) -> FrontierCacheBuildResult:
    return build_frontier_cache_for_chart(
        chart_path, prebuild_worker_curves(), timing_mode, _ensure_timeline_frontier_cache
    )


def _build_timeline_songs(song_paths: list[str], curves: StatCurves, timing_mode: str) -> PrebuildTally:
    tally = PrebuildTally(TIMELINE_FRONTIER_CACHE, len(song_paths), progress_every=25)
    if len(song_paths) == 1:
        try:
            result = build_frontier_cache_for_chart(song_paths[0], curves, timing_mode, _ensure_timeline_frontier_cache)
        except Exception as exc:
            tally.fail(song_paths[0], exc)
        else:
            tally.add(result)
        return tally
    worker_count = timeline_prebuild_worker_count()
    with BoundedRecyclingProcessPool(
        max_workers=worker_count,
        initializer=init_prebuild_worker,
        initargs=(curves, configure_timeline_pair_build_threads, frontier_prebuild_intra_worker_threads(worker_count)),
        max_tasks_per_worker=_TIMELINE_PREBUILD_MAX_TASKS_PER_WORKER,
    ) as executor:
        futures = {executor.submit(_build_timeline_chart, path, timing_mode): path for path in song_paths}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                tally.fail(futures[future], exc)
                continue
            tally.add(result)
            tally.log_progress(result)
    tally.log_ready()
    return tally


def _maintain_timeline_cache(
    _plan: FrontierCacheManifestPlan, _build_missing: bool, _authorize_destructive_rotation: bool
) -> None:
    TIMELINE_FRONTIER_CACHE.remove_temp_files()


TIMELINE_FRONTIER_PREBUILD = FrontierCachePrebuild(
    cache=TIMELINE_FRONTIER_CACHE,
    build_songs=_build_timeline_songs,
    maintain=_maintain_timeline_cache,
)
