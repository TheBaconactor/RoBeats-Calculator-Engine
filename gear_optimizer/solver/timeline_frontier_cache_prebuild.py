from __future__ import annotations

import concurrent.futures
import logging
import os
import threading
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from gear_optimizer.core.constants import DIFFICULTIES, PATHS
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.utils import safe_int
from gear_optimizer.solver.timeline_frontier_cache_manifest import (
    apply_manifest_results,
    build_manifest_plan,
)

from gear_optimizer.core.parsing import env_get
logger = logging.getLogger(__name__)
@dataclass(frozen=True)
class TimelineFrontierCacheBuildResult:
    path: str
    song: str
    source: str
    ms: float
    timeline_ms: float
    notes: int
    long_notes: int
    frontier_pool_used: int
    cache_file: str
    skipped: bool = False


@dataclass(frozen=True)
class TimelineFrontierCachePrebuildSummary:
    total: int = 0
    completed: int = 0
    failures: int = 0
    built: int = 0
    disk: int = 0
    memory: int = 0
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class TimelineFrontierCachePrebuildSettings:
    scope: str = "pool"
    workers: int = 0
    max_songs: int = 0
    executor: str = "process"


_PREBUILD_WORKER_REF_ARRAYS: dict | None = None


def _init_prebuild_worker(ref_arrays: dict) -> None:
    global _PREBUILD_WORKER_REF_ARRAYS
    _PREBUILD_WORKER_REF_ARRAYS = dict(ref_arrays or {})


def _build_timeline_frontier_cache_for_path_shared(song_path_text: str) -> "TimelineFrontierCacheBuildResult":
    shared = _PREBUILD_WORKER_REF_ARRAYS if isinstance(_PREBUILD_WORKER_REF_ARRAYS, dict) else {}
    return build_timeline_frontier_cache_for_path(song_path_text, shared)


class TimelineFrontierCachePrebuilder:
    def __init__(self, *, settings: TimelineFrontierCachePrebuildSettings, song_paths: list[str], ref_arrays: dict):
        self.settings = settings
        self.song_paths = list(song_paths)
        self.ref_arrays = dict(ref_arrays)
        self._executor: concurrent.futures.Executor | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.summary = TimelineFrontierCachePrebuildSummary(total=len(self.song_paths))
        self.completed_results: list[TimelineFrontierCacheBuildResult] = []

    def start(self) -> None:
        if not self.song_paths:
            return
        worker_count = _resolve_prebuild_worker_count(self.settings.workers)
        self._executor = _build_prebuild_executor(
            executor_kind=self.settings.executor,
            worker_count=worker_count,
            ref_arrays=self.ref_arrays,
        )
        self._thread = threading.Thread(
            target=self.run_to_completion,
            name="TimelineFrontierCachePrebuild",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "[TimelineCache] Background exact frontier prebuild started: songs=%s workers=%s scope=%s",
            len(self.song_paths),
            worker_count,
            self.settings.scope,
        )
        emit_profile_event(
            component="timeline_cache",
            event="prebuild_start",
            metrics={
                "songs": int(len(self.song_paths)),
                "workers": int(worker_count),
                "scope": str(self.settings.scope),
            },
        )

    def run_to_completion(self) -> TimelineFrontierCachePrebuildSummary:
        if not self.song_paths:
            self.summary = TimelineFrontierCachePrebuildSummary(total=0)
            return self.summary
        worker_count = _resolve_prebuild_worker_count(self.settings.workers)
        owns_executor = self._executor is None
        if owns_executor:
            self._executor = _build_prebuild_executor(
                executor_kind=self.settings.executor,
                worker_count=worker_count,
                ref_arrays=self.ref_arrays,
            )
        try:
            return self._run()
        finally:
            if owns_executor and self._executor is not None:
                self._executor.shutdown(wait=True, cancel_futures=False)
                self._executor = None

    def shutdown(self, *, wait: bool = False) -> None:
        self._stop.set()
        executor = self._executor
        if executor is not None:
            try:
                executor.shutdown(wait=wait, cancel_futures=True)
            except TypeError:
                executor.shutdown(wait=wait)
            except Exception as e:
                logger.debug(f"timeline_frontier_cache_prebuild:shutdown: {e}")
        thread = self._thread
        if wait and thread is not None and thread.is_alive():
            thread.join(timeout=5.0)

    def _run(self) -> TimelineFrontierCachePrebuildSummary:
        executor = self._executor
        if executor is None:
            self.summary = TimelineFrontierCachePrebuildSummary(total=0)
            return self.summary
        self.completed_results = []
        t0 = time.perf_counter()
        source_counts: Counter[str] = Counter()
        failures = 0
        completed = 0
        if isinstance(executor, concurrent.futures.ProcessPoolExecutor):
            futures = {
                executor.submit(_build_timeline_frontier_cache_for_path_shared, path): path
                for path in self.song_paths
                if not self._stop.is_set()
            }
        else:
            futures = {
                executor.submit(build_timeline_frontier_cache_for_path, path, self.ref_arrays): path
                for path in self.song_paths
                if not self._stop.is_set()
            }
        try:
            for future in concurrent.futures.as_completed(futures):
                if self._stop.is_set():
                    break
                path = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    failures += 1
                    logger.warning("[TimelineCache] Failed to prebuild %s: %s", path, exc)
                    continue
                completed += 1
                self.completed_results.append(result)
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
                        float(result.timeline_ms),
                    )
        finally:
            elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
            self.summary = TimelineFrontierCachePrebuildSummary(
                total=int(len(futures)),
                completed=int(completed),
                failures=int(failures),
                built=int(source_counts.get("built", 0)),
                disk=int(source_counts.get("disk", 0)),
                memory=int(source_counts.get("memory", 0)),
                elapsed_ms=elapsed_ms,
            )
            logger.info(
                "[TimelineCache] Exact frontier prebuild stopped: completed=%s/%s failures=%s built=%s disk=%s memory=%s elapsed=%.1fs",
                completed,
                len(futures),
                failures,
                int(source_counts.get("built", 0)),
                int(source_counts.get("disk", 0)),
                int(source_counts.get("memory", 0)),
                elapsed_ms / 1000.0,
            )
            emit_profile_event(
                component="timeline_cache",
                event="prebuild_stop",
                metrics={
                    "completed": int(completed),
                    "total": int(len(futures)),
                    "failures": int(failures),
                    "built": int(source_counts.get("built", 0)),
                    "disk": int(source_counts.get("disk", 0)),
                    "memory": int(source_counts.get("memory", 0)),
                    "elapsed_ms": elapsed_ms,
                },
            )
        return self.summary


def iter_timeline_frontier_cache_song_paths(
    data_root: str | os.PathLike[str] | None = None,
    difficulties: Iterable[str] = DIFFICULTIES,
) -> list[str]:
    root = Path(data_root or PATHS.data_dir)
    paths: list[Path] = []
    for difficulty in difficulties:
        folder = root / str(difficulty)
        if not folder.exists():
            continue
        paths.extend(path for path in folder.rglob("*.txt") if path.is_file())
    return [str(path) for path in sorted(paths, key=lambda item: str(item).lower())]


def ordered_timeline_frontier_cache_paths(
    *,
    queue_paths: Iterable[str],
    data_root: str | os.PathLike[str] | None = None,
    scope: str = "pool",
) -> list[str]:
    scope_key = str(scope or "pool").strip().lower()
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

    if scope_key in {"pool", "all"}:
        for path in iter_timeline_frontier_cache_song_paths(data_root=data_root):
            add(path)

    return ordered


def read_timeline_frontier_cache_prebuild_settings(cfg) -> TimelineFrontierCachePrebuildSettings:
    scope = "pool"
    workers = 0
    max_songs = 0
    executor = "process"

    if cfg is not None:
        try:
            scope = str(cfg.get("IterationEngine", "TimelineFrontierCachePrebuildScope", fallback="pool") or "pool")
        except Exception as e:
            logger.debug(f"timeline_frontier_cache_prebuild:read_timeline_frontier_cache_prebuild_settings: {e}")
            scope = "pool"
        try:
            workers = safe_int(cfg.get("IterationEngine", "TimelineFrontierCachePrebuildWorkers", fallback="0"), 0)
        except Exception as e:
            logger.debug(f"timeline_frontier_cache_prebuild:read_timeline_frontier_cache_prebuild_settings: {e}")
            workers = 0
        try:
            max_songs = safe_int(cfg.get("IterationEngine", "TimelineFrontierCachePrebuildMaxSongs", fallback="0"), 0)
        except Exception as e:
            logger.debug(f"timeline_frontier_cache_prebuild:read_timeline_frontier_cache_prebuild_settings: {e}")
            max_songs = 0
        try:
            executor = str(
                cfg.get("IterationEngine", "TimelineFrontierCachePrebuildExecutor", fallback="process") or "process"
            )
        except Exception as e:
            logger.debug(f"timeline_frontier_cache_prebuild:read_timeline_frontier_cache_prebuild_settings: {e}")
            executor = "process"

    raw_scope = env_get("TIMELINE_FRONTIER_CACHE_PREBUILD_SCOPE")
    if raw_scope is not None and str(raw_scope).strip() != "":
        scope = str(raw_scope).strip()
    raw_workers = env_get("TIMELINE_FRONTIER_CACHE_PREBUILD_WORKERS")
    if raw_workers is not None and str(raw_workers).strip() != "":
        workers = safe_int(raw_workers, workers)
    raw_max = env_get("TIMELINE_FRONTIER_CACHE_PREBUILD_MAX_SONGS")
    if raw_max is not None and str(raw_max).strip() != "":
        max_songs = safe_int(raw_max, max_songs)
    raw_executor = env_get("TIMELINE_FRONTIER_CACHE_PREBUILD_EXECUTOR")
    if raw_executor is not None and str(raw_executor).strip() != "":
        executor = str(raw_executor).strip()

    scope_key = str(scope or "pool").strip().lower()
    if scope_key not in {"queue", "pool", "all"}:
        scope_key = "pool"

    executor_key = str(executor or "process").strip().lower()
    if executor_key not in {"process", "thread"}:
        executor_key = "process"

    return TimelineFrontierCachePrebuildSettings(
        scope=scope_key,
        workers=int(workers),
        max_songs=max(0, int(max_songs or 0)),
        executor=executor_key,
    )


def _resolve_prebuild_worker_count(raw_workers: int) -> int:
    # `<= 0` means "auto": use all logical cores for startup prebuild throughput.
    try:
        workers = int(raw_workers)
    except Exception as e:
        logger.debug(f"timeline_frontier_cache_prebuild:_resolve_prebuild_worker_count: {e}")
        workers = 0
    if workers <= 0:
        workers = int(os.cpu_count() or 1)
    return max(1, workers)


def _build_prebuild_executor(*, executor_kind: str, worker_count: int, ref_arrays: dict) -> concurrent.futures.Executor:
    kind = str(executor_kind or "process").strip().lower()
    if kind == "thread":
        return concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(worker_count)),
            thread_name_prefix="TimelineCacheBuild",
        )
    return concurrent.futures.ProcessPoolExecutor(
        max_workers=max(1, int(worker_count)),
        initializer=_init_prebuild_worker,
        initargs=(dict(ref_arrays or {}),),
    )


def cleanup_timeline_frontier_cache_temp_files(
    cache_dir: str | os.PathLike[str] | None = None,
) -> int:
    from gear_optimizer.solver.taichi_gem.api.timeline import _frontier_disk_cache_dir

    root = Path(cache_dir) if cache_dir is not None else _frontier_disk_cache_dir()
    if not root.exists():
        return 0
    removed = 0
    for path in root.glob("*.tmp.npz"):
        try:
            path.unlink(missing_ok=True)
            removed += 1
        except Exception as e:
            logger.debug(f"timeline_frontier_cache_prebuild:cleanup_timeline_frontier_cache_temp_files: {e}")
            continue
    return int(removed)


def build_timeline_frontier_cache_for_path(
    song_path_text: str,
    ref_arrays: dict,
    *,
    skip_cached: bool = True,
) -> TimelineFrontierCacheBuildResult:
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        build_or_load_timeline_frontier_payload,
        timeline_frontier_payload_cache_info,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    song_path = Path(song_path_text)
    t0 = time.perf_counter()
    calc_song = get_base_calc_song(str(song_path), {})
    # Match runtime timeline key semantics so startup prebuild artifacts are reusable.
    apply_timing_envelope(calc_song)
    if skip_cached:
        cache_info = timeline_frontier_payload_cache_info(calc_song, ref_arrays)
        if cache_info.cache_source in {"disk", "memory"}:
            return TimelineFrontierCacheBuildResult(
                path=str(song_path),
                song=cache_info.song_profile_key or song_path.stem,
                source=str(cache_info.cache_source),
                ms=float((time.perf_counter() - t0) * 1000.0),
                timeline_ms=0.0,
                notes=int(cache_info.total_notes),
                long_notes=int(cache_info.long_notes),
                frontier_pool_used=0,
                cache_file=str(cache_info.disk_path),
                skipped=True,
            )
    result = build_or_load_timeline_frontier_payload(calc_song, ref_arrays)
    return TimelineFrontierCacheBuildResult(
        path=str(song_path),
        song=result.song_profile_key or song_path.stem,
        source=str(result.cache_source),
        ms=float((time.perf_counter() - t0) * 1000.0),
        timeline_ms=float(result.elapsed_ms),
        notes=int(result.total_notes),
        long_notes=int(result.long_notes),
        frontier_pool_used=int(result.payload.frontier_pool_used),
        cache_file=str(result.disk_path),
        skipped=False,
    )


def _timeline_frontier_prebuild_paths(
    *,
    cfg,
    song_queue: Iterable[tuple],
    data_root: str | os.PathLike[str] | None = None,
) -> tuple[TimelineFrontierCachePrebuildSettings, list[str]]:
    settings = read_timeline_frontier_cache_prebuild_settings(cfg)
    queue_paths = [str(item[0]) for item in song_queue if isinstance(item, tuple) and item]
    paths = ordered_timeline_frontier_cache_paths(
        queue_paths=queue_paths,
        data_root=data_root,
        scope=settings.scope,
    )
    if settings.max_songs > 0:
        paths = paths[: int(settings.max_songs)]
    return settings, paths


def run_timeline_frontier_cache_prebuild(
    *,
    cfg,
    song_queue: Iterable[tuple],
    ref_arrays: dict,
    data_root: str | os.PathLike[str] | None = None,
) -> TimelineFrontierCachePrebuildSummary:
    t0 = time.perf_counter()
    settings, paths = _timeline_frontier_prebuild_paths(cfg=cfg, song_queue=song_queue, data_root=data_root)
    if not paths:
        return TimelineFrontierCachePrebuildSummary(total=0)

    manifest_plan = build_manifest_plan(paths, ref_arrays)
    missing_paths = list(manifest_plan.missing_paths)
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

    if not missing_paths:
        elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
        emit_profile_event(
            component="timeline_cache",
            event="prebuild_manifest_only",
            metrics={
                "completed": int(manifest_hits),
                "total": int(manifest_plan.total_paths),
                "elapsed_ms": elapsed_ms,
            },
        )
        return TimelineFrontierCachePrebuildSummary(
            total=int(manifest_plan.total_paths),
            completed=int(manifest_hits),
            failures=0,
            built=0,
            disk=int(manifest_hits),
            memory=0,
            elapsed_ms=elapsed_ms,
        )

    prebuilder = TimelineFrontierCachePrebuilder(settings=settings, song_paths=missing_paths, ref_arrays=ref_arrays)
    run_summary = prebuilder.run_to_completion()
    apply_manifest_results(plan=manifest_plan, results=prebuilder.completed_results)
    elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
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


def start_timeline_frontier_cache_prebuild(
    *,
    cfg,
    song_queue: Iterable[tuple],
    ref_arrays: dict,
    data_root: str | os.PathLike[str] | None = None,
) -> TimelineFrontierCachePrebuilder | None:
    settings, paths = _timeline_frontier_prebuild_paths(cfg=cfg, song_queue=song_queue, data_root=data_root)
    if not paths:
        return None
    manifest_plan = build_manifest_plan(paths, ref_arrays)
    missing_paths = list(manifest_plan.missing_paths)
    if not missing_paths:
        return None
    prebuilder = TimelineFrontierCachePrebuilder(settings=settings, song_paths=missing_paths, ref_arrays=ref_arrays)
    prebuilder.start()
    return prebuilder
