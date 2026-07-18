from __future__ import annotations

import concurrent.futures
import logging
import os
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from gear_optimizer.core.constants import DIFFICULTIES, PATHS
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.recycling_process_pool import BoundedRecyclingProcessPool
from gear_optimizer.solver.frontier_cache_manifest import (
    _ref_axes_signature,
    apply_manifest_results as _shared_apply_manifest_results,
    build_manifest_plan as _shared_build_manifest_plan,
)
from gear_optimizer.core.cpu_affinity import (
    frontier_prebuild_intra_worker_threads,
    init_process_pool_worker_band,
    timeline_prebuild_worker_count,
)
from gear_optimizer.solver.frontier_cache_build_lock import FrontierBuildLock
from gear_optimizer.solver.timeline_exact_frontier import configure_timeline_pair_build_threads

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimelineFrontierCacheBuildResult:
    path: str
    source: str
    build_ms: float
    cache_file: str


@dataclass(frozen=True)
class TimelineFrontierCachePrebuildSummary:
    total: int = 0
    completed: int = 0
    failures: int = 0
    built: int = 0
    disk: int = 0
    memory: int = 0
    elapsed_ms: float = 0.0


_PREBUILD_WORKER_REF_ARRAYS: dict | None = None
_MANIFEST_FILE_NAME = "manifest_v1.json"
_TIMELINE_PREBUILD_MAX_TASKS_PER_WORKER = 64


def _init_prebuild_worker(ref_arrays: dict, pair_build_threads: int, total_workers: int) -> None:
    init_process_pool_worker_band(int(total_workers))
    configure_timeline_pair_build_threads(max(1, int(pair_build_threads)))
    global _PREBUILD_WORKER_REF_ARRAYS
    _PREBUILD_WORKER_REF_ARRAYS = dict(ref_arrays or {})


def _build_timeline_frontier_cache_for_path_shared(song_path_text: str) -> TimelineFrontierCacheBuildResult:
    shared = _PREBUILD_WORKER_REF_ARRAYS if isinstance(_PREBUILD_WORKER_REF_ARRAYS, dict) else {}
    return build_timeline_frontier_cache_for_path(song_path_text, shared)


def iter_timeline_frontier_cache_song_paths(
    data_root: str | os.PathLike[str] | None = None,
    difficulties: Iterable[str] = DIFFICULTIES,
) -> list[str]:
    root = Path(data_root or PATHS.data_dir)
    paths: list[Path] = []
    for difficulty in difficulties:
        folder = root / str(difficulty)
        if folder.exists():
            paths.extend(path for path in folder.rglob("*.txt") if path.is_file())
    return [str(path) for path in sorted(paths, key=lambda item: str(item).lower())]


def ordered_frontier_cache_song_paths(
    *,
    queue_paths: Iterable[str],
    data_root: str | os.PathLike[str] | None = None,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    def add(path_text: str) -> None:
        path = str(path_text or "").strip()
        if not path:
            return
        key = os.path.abspath(path).casefold()
        if key in seen:
            return
        seen.add(key)
        ordered.append(path)

    for path in queue_paths:
        add(path)
    if ordered:
        return ordered
    for path in iter_timeline_frontier_cache_song_paths(data_root=data_root):
        add(path)
    return ordered


def _manifest_path() -> Path:
    from gear_optimizer.solver.taichi_gem.api.timeline import _frontier_disk_cache_dir

    return _frontier_disk_cache_dir() / _MANIFEST_FILE_NAME


def _cache_version() -> str:
    from gear_optimizer.solver.taichi_gem.api.timeline import _FRONTIER_DISK_CACHE_VERSION

    return str(_FRONTIER_DISK_CACHE_VERSION)


def _derived_frontier_cache_file(song_path: str, ref_arrays: dict) -> str | None:
    """Parse one chart and return the cache file its CURRENT frontier key derives (drift probe)."""
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.api.timeline import timeline_frontier_payload_cache_info
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    calc_song = get_base_calc_song(str(song_path), {})
    if not calc_song:
        return None
    apply_timing_envelope(calc_song)
    return str(timeline_frontier_payload_cache_info(calc_song, ref_arrays).disk_path)


def _build_manifest_plan(
    song_paths: Iterable[str],
    ref_arrays: dict,
    *,
    persist_validated_entries: bool = True,
):
    from gear_optimizer.solver.taichi_gem.api.timeline import timeline_frontier_cache_file_is_complete

    return _shared_build_manifest_plan(
        song_paths,
        manifest_path=_manifest_path(),
        cache_version=_cache_version(),
        version_field="frontier_version",
        ref_sig_hex=_ref_axes_signature(ref_arrays),
        cache_file_validator=timeline_frontier_cache_file_is_complete,
        derived_cache_file_fn=lambda song_path: _derived_frontier_cache_file(song_path, ref_arrays),
        persist_validated_entries=persist_validated_entries,
    )


def _apply_manifest_results(*, plan, results: Iterable[object]) -> int:
    from gear_optimizer.solver.taichi_gem.api.timeline import timeline_frontier_cache_file_is_complete

    return _shared_apply_manifest_results(
        plan=plan,
        manifest_path=_manifest_path(),
        cache_version=_cache_version(),
        version_field="frontier_version",
        results=results,
        cache_file_validator=timeline_frontier_cache_file_is_complete,
    )


def cleanup_timeline_frontier_cache_temp_files(cache_dir: str | os.PathLike[str] | None = None) -> int:
    from gear_optimizer.solver.taichi_gem.api.timeline import _frontier_disk_cache_dir

    root = Path(cache_dir) if cache_dir is not None else _frontier_disk_cache_dir()
    if not root.exists():
        return 0
    removed = 0
    for path in root.glob("*.tmp.npz"):
        path.unlink(missing_ok=True)
        removed += 1
    return int(removed)


def build_timeline_frontier_cache_for_path(
    song_path_text: str,
    ref_arrays: dict,
) -> TimelineFrontierCacheBuildResult:
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        timeline_frontier_payload_cache_info,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    song_path = Path(song_path_text)
    calc_song = get_base_calc_song(str(song_path), {})
    apply_timing_envelope(calc_song)
    cache_info = timeline_frontier_payload_cache_info(calc_song, ref_arrays)
    if cache_info.cache_source in {"disk", "memory"}:
        return TimelineFrontierCacheBuildResult(
            path=str(song_path),
            source=str(cache_info.cache_source),
            build_ms=0.0,
            cache_file=str(cache_info.disk_path),
        )
    result = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    return TimelineFrontierCacheBuildResult(
        path=str(song_path),
        source=str(result.cache_source),
        build_ms=float(result.elapsed_ms),
        cache_file=str(result.disk_path),
    )


def _run_missing_timeline_prebuild(paths: list[str], ref_arrays: dict) -> tuple[TimelineFrontierCachePrebuildSummary, list[TimelineFrontierCacheBuildResult]]:
    if not paths:
        return TimelineFrontierCachePrebuildSummary(total=0), []
    t0 = time.perf_counter()
    source_counts: Counter[str] = Counter()
    failures = 0
    completed = 0
    results: list[TimelineFrontierCacheBuildResult] = []
    if len(paths) == 1:
        path = str(paths[0])
        try:
            result = build_timeline_frontier_cache_for_path(path, ref_arrays)
        except Exception as exc:
            failures = 1
            logger.warning("[TimelineCache] Failed to prebuild %s: %s", path, exc)
        else:
            completed = 1
            results.append(result)
            source_counts[result.source] += 1
        elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
        return (
            TimelineFrontierCachePrebuildSummary(
                total=int(len(paths)),
                completed=int(completed),
                failures=int(failures),
                built=int(source_counts.get("built", 0)),
                disk=int(source_counts.get("disk", 0)),
                memory=int(source_counts.get("memory", 0)),
                elapsed_ms=elapsed_ms,
            ),
            results,
        )
    worker_count = timeline_prebuild_worker_count()
    pair_build_threads = frontier_prebuild_intra_worker_threads(worker_count)
    with BoundedRecyclingProcessPool(
        max_workers=worker_count,
        initializer=_init_prebuild_worker,
        initargs=(dict(ref_arrays or {}), int(pair_build_threads), int(worker_count)),
        # Release native/NumPy allocator high-water before a full-pool worker reaches the heavy
        # chart tail. Persistent workers exhausted commit after ~2,216 successes and then failed
        # allocations as small as 1 MiB on the production 2,249-song pool.
        max_tasks_per_worker=_TIMELINE_PREBUILD_MAX_TASKS_PER_WORKER,
    ) as executor:
        futures = {executor.submit(_build_timeline_frontier_cache_for_path_shared, path): path for path in paths}
        for future in concurrent.futures.as_completed(futures):
            path = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                failures += 1
                logger.warning("[TimelineCache] Failed to prebuild %s: %s", path, exc)
                continue
            completed += 1
            results.append(result)
            source_counts[result.source] += 1
            if completed == 1 or completed % 25 == 0:
                logger.info(
                    "[TimelineCache] %s/%s complete (built=%s disk=%s memory=%s, latest=%s %.1fms)",
                    completed,
                    len(futures),
                    int(source_counts.get("built", 0)),
                    int(source_counts.get("disk", 0)),
                    int(source_counts.get("memory", 0)),
                    result.source,
                    float(result.build_ms),
                )
    elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
    summary = TimelineFrontierCachePrebuildSummary(
        total=int(len(paths)),
        completed=int(completed),
        failures=int(failures),
        built=int(source_counts.get("built", 0)),
        disk=int(source_counts.get("disk", 0)),
        memory=int(source_counts.get("memory", 0)),
        elapsed_ms=elapsed_ms,
    )
    logger.info(
        "[TimelineCache] Exact frontier prebuild ready: completed=%s/%s failures=%s built=%s disk=%s memory=%s elapsed=%.1fs",
        completed,
        len(paths),
        failures,
        int(source_counts.get("built", 0)),
        int(source_counts.get("disk", 0)),
        int(source_counts.get("memory", 0)),
        elapsed_ms / 1000.0,
    )
    return summary, results


def run_timeline_frontier_cache_prebuild(
    *,
    cfg,
    song_queue: Iterable[tuple],
    ref_arrays: dict,
    data_root: str | os.PathLike[str] | None = None,
) -> TimelineFrontierCachePrebuildSummary:
    del cfg
    from gear_optimizer.solver.taichi_gem.api.timeline import _frontier_disk_cache_dir

    started = time.perf_counter()
    queue_paths = [str(item[0]) for item in song_queue if isinstance(item, tuple) and item]
    paths = ordered_frontier_cache_song_paths(queue_paths=queue_paths, data_root=data_root)
    if not paths:
        return TimelineFrontierCachePrebuildSummary(total=0)

    # Fully recorded cache hits are readers, not builders. Probe without mutating the manifest so
    # they never wait behind an unrelated deployment prebuild that owns the single-builder lock.
    # Complete derived hits absent from the manifest enter the lock once below to persist metadata.
    optimistic_plan = _build_manifest_plan(paths, ref_arrays, persist_validated_entries=False)
    if not optimistic_plan.missing_paths and int(optimistic_plan.validated_entry_count) == 0:
        return TimelineFrontierCachePrebuildSummary(
            total=int(optimistic_plan.total_paths),
            completed=int(optimistic_plan.hit_count),
            disk=int(optimistic_plan.hit_count),
            elapsed_ms=float((time.perf_counter() - started) * 1000.0),
        )

    # Single-builder lock: a second concurrent process waits here, then re-runs its manifest plan
    # below -- which now fast-hits everything this process wrote -- instead of duplicating the build.
    with FrontierBuildLock(_frontier_disk_cache_dir(), label="timeline"):
        manifest_plan = _build_manifest_plan(paths, ref_arrays)
        manifest_hits = int(manifest_plan.hit_count)
        if manifest_hits > 0:
            logger.info(
                "[TimelineCache] Manifest fast-hit skipped %s/%s song(s) before worker parse/build.",
                manifest_hits,
                int(manifest_plan.total_paths),
            )

        removed_tmp = cleanup_timeline_frontier_cache_temp_files()
        if int(removed_tmp) > 0:
            logger.info("[TimelineCache] Removed %s stale temporary cache file(s).", int(removed_tmp))

        if not manifest_plan.missing_paths:
            return TimelineFrontierCachePrebuildSummary(
                total=int(manifest_plan.total_paths),
                completed=int(manifest_hits),
                disk=int(manifest_hits),
                elapsed_ms=float((time.perf_counter() - started) * 1000.0),
            )

        run_summary, results = _run_missing_timeline_prebuild(list(manifest_plan.missing_paths), ref_arrays)
        _apply_manifest_results(plan=manifest_plan, results=results)
        elapsed_ms = float((time.perf_counter() - started) * 1000.0)
        combined = TimelineFrontierCachePrebuildSummary(
            total=int(manifest_plan.total_paths),
            completed=int(manifest_hits + run_summary.completed),
            failures=int(run_summary.failures),
            built=int(run_summary.built),
            disk=int(manifest_hits + run_summary.disk),
            memory=int(run_summary.memory),
            elapsed_ms=elapsed_ms,
        )
        emit_profile_event(
            component="timeline_cache",
            event="prebuild_with_manifest",
            metrics={
                "manifest_hits": int(manifest_hits),
                "completed": int(combined.completed),
                "total": int(combined.total),
                "failures": int(combined.failures),
                "built": int(combined.built),
                "disk": int(combined.disk),
                "memory": int(combined.memory),
                "elapsed_ms": elapsed_ms,
            },
        )
        return combined
