"""The FG response-frontier cache's startup prebuild: duplicate charts build once, heaviest first, admitted by their
estimated memory weight under a RAM guard; maintenance purges superseded versions.

The driver (manifest, build lock, recording) is cache.prebuild_frontier_cache.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
from pathlib import Path

import psutil

from gear_optimizer.chart import load_chart
from gear_optimizer.core.cpu_affinity import frontier_prebuild_cpu_count, frontier_prebuild_worker_count
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
from gear_optimizer.frontier.producer_reducer import configure_frontier_build_threads
from gear_optimizer.frontier.fg_cache import ensure_response_frontier_cache_for_song
from gear_optimizer.frontier.fg_cache_keys import fg_response_frontier_bundle_cache_key
from gear_optimizer.frontier.fg_cache_store import (
    FG_RESPONSE_FRONTIER_CACHE,
    purge_stale_version_cache_files,
)
from gear_optimizer.solver.timing_envelope import time_song

logger = logging.getLogger(__name__)

_MAX_TASKS_PER_WORKER = 16

# Memory-weighted admission of the cold FG build. A build's commit climbs for its whole 30-70 minutes and spans ~4x between
# charts, so concurrency is admitted per song, and the weights below are only a prior for ordering and backfill: the
# ledger counts max(prior, measured worker commit), admission re-runs on a timer, and an emergency guard suspends climbing
# workers before the OS runs out of commit (a box without a pagefile crashes instead of slowing down).
_FLOOR_COMMIT_GB = 2.0  # ~1.76 GB retained worker baseline + headroom
_PEAK_COMMIT_GB = 7.0  # the giants: ~1.05 GB baseline + ~1.0 GB per thread of 4 + live packets, with margin
_PEAK_COMMIT_NOTES = 7000.0  # the note count of the charts that anchored the prior
_SYSTEM_RESERVE_GB = 6.0  # main process + OS headroom the pool never claims
_SUSPEND_FLOOR_GB = 2.0  # below this free RAM, suspend the youngest workers
_RESUME_FLOOR_GB = 4.0  # above this free RAM, resume one suspended worker per poll
_GUARD_POLL_SECONDS = 5.0
# On a RAM-starved host free RAM may never reach the resume floor: after this many polls without a resume, the
# oldest-suspended worker resumes anyway, so the build cannot hang forever holding the single-builder lock.
_RESUME_STALL_POLLS = 12
_ADMIT_POLL_SECONDS = 10.0  # admission re-runs as in-flight commits materialize
# The measured useful range of a chart's reducer threads (Calamity at 11: 10m36s -> 3m57s at 1.085 GB peak).
_MAX_REDUCER_THREADS = 11


def _fg_prebuild_song_weight_gb(note_count: int) -> float:
    """Estimated peak worker commit (GB) of a song's build: linear in notes, anchored at the measured giants."""
    slope = (_PEAK_COMMIT_GB - _FLOOR_COMMIT_GB) / _PEAK_COMMIT_NOTES
    return _FLOOR_COMMIT_GB + max(0, int(note_count)) * slope


def _fg_prebuild_available_ram_gb() -> float:
    return psutil.virtual_memory().available / 1e9


def _fg_prebuild_pool_worker_processes() -> list:
    """The live pool workers (direct python children of this process)."""
    workers = []
    for child in psutil.Process().children(recursive=False):
        try:
            if "python" in (child.name() or "").lower():
                workers.append(child)
        except psutil.Error:
            continue  # the child exited while we looked
    return workers


def _fg_prebuild_live_worker_commit_gb() -> float:
    """The pool workers' measured committed memory (GB): the closed-loop half of the admission ledger."""
    total = 0.0
    for proc in _fg_prebuild_pool_worker_processes():
        try:
            memory = proc.memory_info()
        except psutil.Error:
            continue  # the worker exited while we looked
        total += float(getattr(memory, "private", 0) or memory.vms) / 1e9
    return total


class _FgPrebuildRamGuard:
    """Emergency brake of the cold build: below the suspend floor the youngest workers are suspended (nothing is lost, a
    suspended build resumes where it stopped) and at least one keeps running, so completions keep freeing RAM. Suspension
    is the only bound available mid-flight: ProcessPoolExecutor cannot survive killing a worker."""

    def __init__(self) -> None:
        import threading

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="fg-prebuild-ram-guard", daemon=True)
        self._suspended: list = []

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=_GUARD_POLL_SECONDS * 3)
        for proc in list(self._suspended):
            self._resume(proc)

    def _resume(self, proc) -> None:
        try:
            proc.resume()
        except psutil.Error:
            pass  # the worker already exited
        if proc in self._suspended:
            self._suspended.remove(proc)

    def _run(self) -> None:
        polls_since_resume = 0
        while not self._stop.wait(_GUARD_POLL_SECONDS):
            free_gb = _fg_prebuild_available_ram_gb()
            workers = _fg_prebuild_pool_worker_processes()
            suspended_pids = {proc.pid for proc in self._suspended}
            self._suspended = [proc for proc in self._suspended if proc.is_running()]
            running = [proc for proc in workers if proc.pid not in suspended_pids]

            force_resume = bool(self._suspended) and (
                not running or polls_since_resume >= _RESUME_STALL_POLLS
            )

            if free_gb < _SUSPEND_FLOOR_GB and len(running) > 1 and not force_resume:
                # Youngest first: it has the least sunk work and the steepest remaining climb.
                youngest = max(running, key=lambda proc: proc.create_time())
                try:
                    youngest.suspend()
                except psutil.Error:
                    pass  # the worker already exited
                else:
                    self._suspended.append(youngest)
                    logger.warning(
                        "[FGResponseCache] RAM guard: %.1f GB free < %.1f floor; suspended worker %s "
                        "(%s/%s workers now suspended).",
                        free_gb,
                        _SUSPEND_FLOOR_GB,
                        youngest.pid,
                        len(self._suspended),
                        len(workers),
                    )
                polls_since_resume += 1
            elif self._suspended and (free_gb > _RESUME_FLOOR_GB or force_resume):
                # One per poll: a thundering resume would re-create the climb that tripped the guard.
                proc = self._suspended[0] if force_resume else self._suspended[-1]
                self._resume(proc)
                polls_since_resume = 0
                logger.info(
                    "[FGResponseCache] RAM guard: %.1f GB free; resumed worker %s (forced=%s, %s still suspended).",
                    free_gb,
                    proc.pid,
                    force_resume,
                    len(self._suspended),
                )
            else:
                polls_since_resume += 1


def _fg_prebuild_reducer_threads(
    weight_gb: float,
    *,
    budget_gb: float,
    max_workers: int,
    frontier_cpus: int,
    workload_count: int,
) -> int:
    """A song's reducer threads: the cores the concurrency of its weight class leaves it (results never depend on them)."""
    concurrency = max(1, min(int(max_workers), int(float(budget_gb) / max(float(weight_gb), _FLOOR_COMMIT_GB))))
    concurrency = min(concurrency, workload_count)
    return max(1, min(_MAX_REDUCER_THREADS, int(frontier_cpus) // concurrency))


def _dedupe_paths_by_response_bundle_key(
    song_paths: list[str],
    curves: StatCurves,
    timing_mode: str,
) -> tuple[list[tuple[str, int]], dict[str, tuple[str, ...]]]:
    """The songs one per response bundle key, with their note counts (for the order and the admission weights), and the
    charts each one's bundle serves too."""
    representatives: list[tuple[str, int]] = []
    duplicates: dict[str, list[str]] = {}
    representative_by_key: dict[tuple, str] = {}
    for path_text in song_paths:
        path = str(path_text)
        song = time_song(load_chart(Path(path)), timing_mode)
        key = fg_response_frontier_bundle_cache_key(song, curves)
        representative = representative_by_key.get(key)
        if representative is None:
            representative_by_key[key] = path
            representatives.append((path, song.chart.total_notes))
            duplicates[path] = []
        else:
            duplicates[representative].append(path)
    return representatives, {
        str(path): tuple(str(value) for value in duplicate_paths)
        for path, duplicate_paths in duplicates.items()
        if duplicate_paths
    }


def _build_fg_chart(chart_path: str, reducer_threads: int, timing_mode: str) -> FrontierCacheBuildResult:
    # Per-task width from the admission scheduler: sized to this song's memory weight class.
    configure_frontier_build_threads(int(reducer_threads))
    return build_frontier_cache_for_chart(
        chart_path, prebuild_worker_curves(), timing_mode, ensure_response_frontier_cache_for_song
    )


def _add_with_duplicates(
    tally: PrebuildTally, result: FrontierCacheBuildResult, duplicate_paths: tuple[str, ...]
) -> None:
    """A built chart and the charts whose songs its bundle serves too."""
    tally.add(result)
    if not duplicate_paths:
        return
    source = "disk" if result.cache_file and os.path.exists(result.cache_file) else result.source
    for duplicate_path in duplicate_paths:
        tally.add(
            FrontierCacheBuildResult(path=duplicate_path, source=source, build_ms=0.0, cache_file=result.cache_file)
        )


def _build_fg_songs(song_paths: list[str], curves: StatCurves, timing_mode: str) -> PrebuildTally:
    tally = PrebuildTally(FG_RESPONSE_FRONTIER_CACHE, len(song_paths), progress_every=10)
    # Sorted input: the representative of duplicate charts does not depend on the queue order. Execution is
    # heaviest first, ordered by the parse pass that also weighs the songs for admission.
    build_items, duplicates_of = _dedupe_paths_by_response_bundle_key(sorted(song_paths), curves, timing_mode)
    build_items.sort(key=lambda item: (-int(item[1]), str(item[0]).lower()))
    if len(build_items) == 1:
        path = build_items[0][0]
        duplicate_paths = duplicates_of.get(path, ())
        try:
            result = build_frontier_cache_for_chart(path, curves, timing_mode, ensure_response_frontier_cache_for_song)
        except Exception as exc:
            tally.fail(path, exc, songs=1 + len(duplicate_paths))
        else:
            _add_with_duplicates(tally, result, duplicate_paths)
        return tally
    if duplicates_of:
        logger.info(
            "[FGResponseCache] Dedupe skipped %s/%s duplicate response bundle path(s) before worker build.",
            sum(len(values) for values in duplicates_of.values()),
            len(song_paths),
        )
    _build_admitted_by_weight(tally, build_items, duplicates_of, curves, timing_mode)
    return tally


def _build_admitted_by_weight(
    tally: PrebuildTally,
    build_items: list[tuple[str, int]],
    duplicates_of: dict[str, tuple[str, ...]],
    curves: StatCurves,
    timing_mode: str,
) -> None:
    available_gb = _fg_prebuild_available_ram_gb()
    budget_gb = max(_PEAK_COMMIT_GB, float(available_gb) - _SYSTEM_RESERVE_GB)
    max_workers = min(frontier_prebuild_worker_count(), max(1, int(budget_gb / _FLOOR_COMMIT_GB)))
    frontier_cpus = frontier_prebuild_cpu_count()
    heaviest_weight = _fg_prebuild_song_weight_gb(int(build_items[0][1]))
    logger.info(
        "[FGResponseCache] Weighted admission: %s song(s), budget=%.1f GB (available=%.1f GB, reserve=%.1f GB), "
        "max_workers=%s, heaviest=%s notes (~%.1f GB).",
        len(build_items),
        budget_gb,
        available_gb,
        _SYSTEM_RESERVE_GB,
        int(max_workers),
        int(build_items[0][1]),
        float(heaviest_weight),
    )
    pending: list[tuple[str, int]] = list(build_items)
    in_flight: dict[concurrent.futures.Future, tuple[str, float]] = {}
    admitted_weight_gb = 0.0

    def _admit_ready(executor: BoundedRecyclingProcessPool) -> None:
        # First-fit over the heaviest-first queue: lighter charts backfill what a giant does not fit.
        nonlocal admitted_weight_gb
        while pending and len(in_flight) < max_workers:
            live_available_gb = _fg_prebuild_available_ram_gb()
            effective_ledger_gb = max(float(admitted_weight_gb), _fg_prebuild_live_worker_commit_gb())
            admit_index: int | None = None
            weight_gb = 0.0
            for index, (_path, note_count) in enumerate(pending):
                weight_gb = _fg_prebuild_song_weight_gb(int(note_count))
                if not in_flight:  # progress: one build always runs
                    admit_index = index
                    break
                if effective_ledger_gb + weight_gb > budget_gb:
                    continue
                if weight_gb > live_available_gb - _SYSTEM_RESERVE_GB:
                    continue
                admit_index = index
                break
            if admit_index is None:
                return
            path, note_count = pending.pop(admit_index)
            reducer_threads = _fg_prebuild_reducer_threads(
                weight_gb,
                budget_gb=budget_gb,
                max_workers=max_workers,
                frontier_cpus=frontier_cpus,
                workload_count=1 + len(pending) + len(in_flight),
            )
            future = executor.submit(_build_fg_chart, path, int(reducer_threads), timing_mode)
            in_flight[future] = (path, float(weight_gb))
            admitted_weight_gb += float(weight_gb)
            if weight_gb >= 4.0:
                logger.info(
                    "[FGResponseCache] Admitted giant %s (%s notes, ~%.1f GB, %s reducer threads); "
                    "in-flight=%s (~%.1f/%.1f GB).",
                    os.path.basename(path),
                    int(note_count),
                    float(weight_gb),
                    int(reducer_threads),
                    len(in_flight),
                    float(admitted_weight_gb),
                    budget_gb,
                )

    ram_guard = _FgPrebuildRamGuard()
    ram_guard.start()
    try:
        # Recycling the pool releases the allocators' high-water (~1.76 GB idle after a giant; ~26 GB across a pool once).
        with BoundedRecyclingProcessPool(
            max_workers=max_workers,
            initializer=init_prebuild_worker,
            initargs=(curves, configure_frontier_build_threads, 1),
            max_tasks_per_worker=_MAX_TASKS_PER_WORKER,
        ) as executor:
            _admit_ready(executor)
            while in_flight:
                done, _not_done = concurrent.futures.wait(
                    in_flight,
                    timeout=_ADMIT_POLL_SECONDS,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                for future in done:
                    path, weight_gb = in_flight.pop(future)
                    admitted_weight_gb -= float(weight_gb)
                    duplicate_paths = duplicates_of.get(path, ())
                    try:
                        result = future.result()
                    except Exception as exc:
                        tally.fail(path, exc, songs=1 + len(duplicate_paths))
                        continue
                    _add_with_duplicates(tally, result, duplicate_paths)
                    tally.log_progress(result)
                _admit_ready(executor)
    finally:
        ram_guard.stop()


def _maintain_fg_cache(plan: FrontierCacheManifestPlan, authorize_destructive_rotation: bool) -> None:
    # Hits only read or repair manifest metadata. Purging belongs to builders and to an authorized rotation.
    if not (plan.missing_paths or authorize_destructive_rotation):
        return
    FG_RESPONSE_FRONTIER_CACHE.remove_temp_files()
    removed = purge_stale_version_cache_files(authorize_rotation=authorize_destructive_rotation)
    if removed:
        logger.info("[FGResponseCache] Purged %s file(s) from superseded cache versions.", removed)


FG_RESPONSE_FRONTIER_PREBUILD = FrontierCachePrebuild(
    cache=FG_RESPONSE_FRONTIER_CACHE,
    build_songs=_build_fg_songs,
    maintain=_maintain_fg_cache,
)
