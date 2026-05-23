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

from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.utils import safe_int
from gear_optimizer.solver.timeline_frontier_cache_prebuild import ordered_timeline_frontier_cache_paths

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FgResponseFrontierCacheBuildResult:
    path: str
    song: str
    source: str
    ms: float
    frontier_ms: float
    notes: int
    long_notes: int
    frontier_count: int
    cache_file: str
    skipped: bool = False


@dataclass(frozen=True)
class FgResponseFrontierCachePrebuildSummary:
    total: int = 0
    completed: int = 0
    failures: int = 0
    built: int = 0
    disk: int = 0
    memory: int = 0
    elapsed_ms: float = 0.0


@dataclass(frozen=True)
class FgResponseFrontierCachePrebuildSettings:
    scope: str = "pool"
    workers: int = 0
    max_songs: int = 0
    executor: str = "process"
    stat_keys: tuple[tuple[int, int], ...] = ()


_PREBUILD_WORKER_REF_ARRAYS: dict | None = None
_PREBUILD_WORKER_STAT_KEYS: tuple[tuple[int, int], ...] = ()


def _init_prebuild_worker(ref_arrays: dict, stat_keys: tuple[tuple[int, int], ...]) -> None:
    global _PREBUILD_WORKER_REF_ARRAYS, _PREBUILD_WORKER_STAT_KEYS
    _PREBUILD_WORKER_REF_ARRAYS = dict(ref_arrays or {})
    _PREBUILD_WORKER_STAT_KEYS = tuple(stat_keys or ())


def _build_fg_response_frontier_cache_for_path_shared(song_path_text: str) -> FgResponseFrontierCacheBuildResult:
    shared = _PREBUILD_WORKER_REF_ARRAYS if isinstance(_PREBUILD_WORKER_REF_ARRAYS, dict) else {}
    return build_fg_response_frontier_cache_for_path(
        song_path_text,
        shared,
        stat_keys=_PREBUILD_WORKER_STAT_KEYS,
    )


class FgResponseFrontierCachePrebuilder:
    def __init__(
        self,
        *,
        settings: FgResponseFrontierCachePrebuildSettings,
        song_paths: list[str],
        ref_arrays: dict,
    ):
        self.settings = settings
        self.song_paths = list(song_paths)
        self.ref_arrays = dict(ref_arrays)
        self._executor: concurrent.futures.Executor | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self.summary = FgResponseFrontierCachePrebuildSummary(total=len(self.song_paths))
        self.completed_results: list[FgResponseFrontierCacheBuildResult] = []

    def start(self) -> None:
        if not self.song_paths:
            return
        worker_count = _resolve_prebuild_worker_count(self.settings.workers)
        self._executor = _build_prebuild_executor(
            executor_kind=self.settings.executor,
            worker_count=worker_count,
            ref_arrays=self.ref_arrays,
            stat_keys=self.settings.stat_keys,
        )
        self._thread = threading.Thread(
            target=self.run_to_completion,
            name="FgResponseFrontierCachePrebuild",
            daemon=True,
        )
        self._thread.start()

    def run_to_completion(self) -> FgResponseFrontierCachePrebuildSummary:
        if not self.song_paths:
            self.summary = FgResponseFrontierCachePrebuildSummary(total=0)
            return self.summary
        worker_count = _resolve_prebuild_worker_count(self.settings.workers)
        owns_executor = self._executor is None
        if owns_executor:
            self._executor = _build_prebuild_executor(
                executor_kind=self.settings.executor,
                worker_count=worker_count,
                ref_arrays=self.ref_arrays,
                stat_keys=self.settings.stat_keys,
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
        thread = self._thread
        if wait and thread is not None and thread.is_alive():
            thread.join(timeout=5.0)

    def _run(self) -> FgResponseFrontierCachePrebuildSummary:
        executor = self._executor
        if executor is None:
            self.summary = FgResponseFrontierCachePrebuildSummary(total=0)
            return self.summary
        self.completed_results = []
        t0 = time.perf_counter()
        source_counts: Counter[str] = Counter()
        failures = 0
        completed = 0
        if isinstance(executor, concurrent.futures.ProcessPoolExecutor):
            futures = {
                executor.submit(_build_fg_response_frontier_cache_for_path_shared, path): path
                for path in self.song_paths
                if not self._stop.is_set()
            }
        else:
            futures = {
                executor.submit(
                    build_fg_response_frontier_cache_for_path,
                    path,
                    self.ref_arrays,
                    stat_keys=self.settings.stat_keys,
                ): path
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
                    logger.warning("[FGResponseCache] Failed to prebuild %s: %s", path, exc)
                    continue
                completed += 1
                self.completed_results.append(result)
                source_counts[result.source] += 1
                if completed == 1 or completed % 10 == 0:
                    logger.info(
                        "[FGResponseCache] %s/%s complete (built=%s disk=%s memory=%s, latest=%s %.1fms)",
                        completed,
                        len(futures),
                        int(source_counts.get("built", 0)),
                        int(source_counts.get("disk", 0)),
                        int(source_counts.get("memory", 0)),
                        result.source,
                        float(result.frontier_ms),
                    )
        finally:
            elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
            self.summary = FgResponseFrontierCachePrebuildSummary(
                total=int(len(futures)),
                completed=int(completed),
                failures=int(failures),
                built=int(source_counts.get("built", 0)),
                disk=int(source_counts.get("disk", 0)),
                memory=int(source_counts.get("memory", 0)),
                elapsed_ms=elapsed_ms,
            )
            logger.info(
                "[FGResponseCache] Response-frontier prebuild stopped: completed=%s/%s failures=%s built=%s disk=%s memory=%s elapsed=%.1fs",
                completed,
                len(futures),
                failures,
                int(source_counts.get("built", 0)),
                int(source_counts.get("disk", 0)),
                int(source_counts.get("memory", 0)),
                elapsed_ms / 1000.0,
            )
            emit_profile_event(
                component="fg_response_cache",
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


def _cfg_get(cfg, option: str, fallback: str) -> str:
    if cfg is None:
        return fallback
    try:
        return str(cfg.get("IterationEngine", option, fallback=fallback) or fallback)
    except Exception as exc:
        logger.debug("fg_response_frontier_cache_prebuild:_cfg_get: %s", exc)
        return fallback


def _full_budget_ftff_stat_keys() -> tuple[tuple[int, int], ...]:
    from gear_optimizer.core.constants import TOTAL_GEM_BUDGET, TOTAL_ROWS
    from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
    from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats

    out: set[tuple[int, int]] = set()
    ft_values, ff_values, _remaining = ftff_combo_arrays(int(TOTAL_GEM_BUDGET))
    for ft, ff in zip(ft_values, ff_values, strict=True):
        stats = apply_gems_to_base_stats({}, "", int(ft), int(ff), 0, 0, 0, 0)
        out.add(
            (
                max(0, min(int(TOTAL_ROWS), int(stats.get("Fever Time", 0) or 0))),
                max(0, min(int(TOTAL_ROWS), int(stats.get("Fever Fill Rate", 0) or 0))),
            )
        )
    return tuple(sorted(out))


def _parse_stat_keys(raw: str | None) -> tuple[tuple[int, int], ...]:
    text = str(raw or "").strip()
    if not text:
        return ()
    normalized = text.strip().lower().replace("_", "-")
    if normalized in {"full", "full-budget", "budget", "budget-90", "all-budget"}:
        return _full_budget_ftff_stat_keys()
    out: set[tuple[int, int]] = set()
    for token in text.replace(";", ",").split(","):
        item = token.strip()
        if not item:
            continue
        normalized_item = item.lower().replace("_", "-")
        if normalized_item in {"full", "full-budget", "budget", "budget-90", "all-budget"}:
            out.update(_full_budget_ftff_stat_keys())
            continue
        parts = item.replace(":", "/").split("/")
        if len(parts) != 2:
            raise ValueError(f"invalid FG response prebuild stat key: {item!r}")
        out.add((safe_int(parts[0], 0), safe_int(parts[1], 0)))
    return tuple(sorted(out))


def read_fg_response_frontier_cache_prebuild_settings(cfg) -> FgResponseFrontierCachePrebuildSettings:
    scope = _cfg_get(
        cfg,
        "FGResponseFrontierCachePrebuildScope",
        _cfg_get(cfg, "TimelineFrontierCachePrebuildScope", "pool"),
    )
    workers = safe_int(
        _cfg_get(
            cfg,
            "FGResponseFrontierCachePrebuildWorkers",
            "0",
        ),
        0,
    )
    max_songs = safe_int(
        _cfg_get(
            cfg,
            "FGResponseFrontierCachePrebuildMaxSongs",
            _cfg_get(cfg, "TimelineFrontierCachePrebuildMaxSongs", "0"),
        ),
        0,
    )
    executor = _cfg_get(
        cfg,
        "FGResponseFrontierCachePrebuildExecutor",
        "process",
    )
    stat_keys = _parse_stat_keys(_cfg_get(cfg, "FGResponseFrontierCachePrebuildStatKeys", ""))

    raw_scope = env_get("FG_RESPONSE_FRONTIER_CACHE_PREBUILD_SCOPE")
    if raw_scope is not None and str(raw_scope).strip():
        scope = str(raw_scope).strip()
    raw_workers = env_get("FG_RESPONSE_FRONTIER_CACHE_PREBUILD_WORKERS")
    if raw_workers is not None and str(raw_workers).strip():
        workers = safe_int(raw_workers, workers)
    raw_max = env_get("FG_RESPONSE_FRONTIER_CACHE_PREBUILD_MAX_SONGS")
    if raw_max is not None and str(raw_max).strip():
        max_songs = safe_int(raw_max, max_songs)
    raw_executor = env_get("FG_RESPONSE_FRONTIER_CACHE_PREBUILD_EXECUTOR")
    if raw_executor is not None and str(raw_executor).strip():
        executor = str(raw_executor).strip()
    raw_stat_keys = env_get("FG_RESPONSE_FRONTIER_CACHE_PREBUILD_STAT_KEYS")
    if raw_stat_keys is not None and str(raw_stat_keys).strip():
        stat_keys = _parse_stat_keys(raw_stat_keys)

    scope_key = str(scope or "pool").strip().lower()
    if scope_key not in {"queue", "pool", "all"}:
        scope_key = "pool"

    executor_key = str(executor or "process").strip().lower()
    if executor_key not in {"process", "thread"}:
        executor_key = "process"

    return FgResponseFrontierCachePrebuildSettings(
        scope=scope_key,
        workers=int(workers),
        max_songs=max(0, int(max_songs or 0)),
        executor=executor_key,
        stat_keys=tuple(stat_keys),
    )


def _resolve_prebuild_worker_count(raw_workers: int) -> int:
    try:
        workers = int(raw_workers)
    except Exception as exc:
        logger.debug("fg_response_frontier_cache_prebuild:_resolve_prebuild_worker_count: %s", exc)
        workers = 0
    if workers <= 0:
        workers = min(8, int(os.cpu_count() or 1))
    return max(1, workers)


def _build_prebuild_executor(
    *,
    executor_kind: str,
    worker_count: int,
    ref_arrays: dict,
    stat_keys: tuple[tuple[int, int], ...],
) -> concurrent.futures.Executor:
    kind = str(executor_kind or "process").strip().lower()
    if kind == "thread":
        return concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(worker_count)),
            thread_name_prefix="FGResponseCacheBuild",
        )
    return concurrent.futures.ProcessPoolExecutor(
        max_workers=max(1, int(worker_count)),
        initializer=_init_prebuild_worker,
        initargs=(dict(ref_arrays or {}), tuple(stat_keys or ())),
    )


def build_fg_response_frontier_cache_for_path(
    song_path_text: str,
    ref_arrays: dict,
    *,
    stat_keys: Iterable[tuple[int, int]],
    skip_cached: bool = True,
) -> FgResponseFrontierCacheBuildResult:
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        fg_response_frontier_payload_cache_info,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    song_path = Path(song_path_text)
    t0 = time.perf_counter()
    calc_song = get_base_calc_song(str(song_path), {})
    apply_timing_envelope(calc_song)
    if skip_cached:
        cache_info = fg_response_frontier_payload_cache_info(calc_song, ref_arrays, stat_keys=stat_keys)
        if cache_info.cache_source in {"disk", "memory"}:
            return FgResponseFrontierCacheBuildResult(
                path=str(song_path),
                song=str(calc_song.get("metadata", {}).get("Song Name") or song_path.stem),
                source=str(cache_info.cache_source),
                ms=float((time.perf_counter() - t0) * 1000.0),
                frontier_ms=0.0,
                notes=int(cache_info.total_notes),
                long_notes=int(cache_info.long_notes),
                frontier_count=int(cache_info.frontier_count),
                cache_file=str(cache_info.disk_path),
                skipped=True,
            )
    result = build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=stat_keys)
    return FgResponseFrontierCacheBuildResult(
        path=str(song_path),
        song=str(calc_song.get("metadata", {}).get("Song Name") or song_path.stem),
        source=str(result.cache_source),
        ms=float((time.perf_counter() - t0) * 1000.0),
        frontier_ms=float(result.elapsed_ms),
        notes=int(result.total_notes),
        long_notes=int(result.long_notes),
        frontier_count=int(result.frontier_count),
        cache_file=str(result.disk_path),
        skipped=False,
    )


def _fg_response_frontier_prebuild_paths(
    *,
    cfg,
    song_queue: Iterable[tuple],
    data_root: str | os.PathLike[str] | None = None,
) -> tuple[FgResponseFrontierCachePrebuildSettings, list[str]]:
    settings = read_fg_response_frontier_cache_prebuild_settings(cfg)
    queue_paths = [str(item[0]) for item in song_queue if isinstance(item, tuple) and item]
    paths = ordered_timeline_frontier_cache_paths(
        queue_paths=queue_paths,
        data_root=data_root,
        scope=settings.scope,
    )
    if settings.max_songs > 0:
        paths = paths[: int(settings.max_songs)]
    return settings, paths


def run_fg_response_frontier_cache_prebuild(
    *,
    cfg,
    song_queue: Iterable[tuple],
    ref_arrays: dict,
    data_root: str | os.PathLike[str] | None = None,
) -> FgResponseFrontierCachePrebuildSummary:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        cleanup_fg_response_frontier_cache_temp_files,
    )

    settings, paths = _fg_response_frontier_prebuild_paths(cfg=cfg, song_queue=song_queue, data_root=data_root)
    if not paths:
        return FgResponseFrontierCachePrebuildSummary(total=0)
    if not settings.stat_keys:
        logger.info(
            "[FGResponseCache] Startup prebuild skipped: response-frontier cache is sparse and requires loadout FT/FF stat keys."
        )
        return FgResponseFrontierCachePrebuildSummary(total=0)

    removed_tmp = cleanup_fg_response_frontier_cache_temp_files()
    if int(removed_tmp) > 0:
        logger.info("[FGResponseCache] Removed %s stale temporary cache file(s).", int(removed_tmp))

    prebuilder = FgResponseFrontierCachePrebuilder(settings=settings, song_paths=paths, ref_arrays=ref_arrays)
    return prebuilder.run_to_completion()


__all__ = [
    "FgResponseFrontierCacheBuildResult",
    "FgResponseFrontierCachePrebuildSettings",
    "FgResponseFrontierCachePrebuildSummary",
    "FgResponseFrontierCachePrebuilder",
    "build_fg_response_frontier_cache_for_path",
    "read_fg_response_frontier_cache_prebuild_settings",
    "run_fg_response_frontier_cache_prebuild",
]
