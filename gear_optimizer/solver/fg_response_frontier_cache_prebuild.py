"""The FG response-frontier cache's startup prebuild: duplicate charts build once, heaviest first, admitted by their
estimated memory weight under a RAM guard; maintenance purges superseded versions and compresses sidecars.

The driver (manifest, build lock, recording) is frontier_cache.prebuild_frontier_cache.
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
from gear_optimizer.solver.frontier_cache import (
    FrontierCacheBuildResult,
    FrontierCacheManifestPlan,
    FrontierCachePrebuild,
    PrebuildTally,
    build_frontier_cache_for_chart,
    init_prebuild_worker,
    prebuild_worker_curves,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (
    configure_force_greats_response_first_frontier_threads,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache import ensure_response_frontier_cache_for_song
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import fg_response_frontier_bundle_cache_key
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import (
    FG_RESPONSE_FRONTIER_CACHE,
    compress_cache_dir_sidecars,
    purge_stale_version_cache_files,
)
from gear_optimizer.solver.timing_envelope import time_song

logger = logging.getLogger(__name__)

_FG_PREBUILD_MAX_TASKS_PER_WORKER = 16

# Memory-weighted admission model for the cold FG build. Per-song peak worker COMMIT spans ~4x
# (median ~1k-note chart vs ~7k-note EXTENDED CUT giants), so concurrency is admitted per song by
# estimated weight instead of a flat worker count. Admission is CLOSED-LOOP: a build's commit
# climbs for its whole 30-70 minute run, so every point sample understates its peak (2026-07-09
# history: 7.0 GB at the crash snapshot -> 10.3 GB at the 4-thread abort -> >=14.8 GB and still
# climbing at 2 threads), and the new Gear/Mini data grew the response grid so no historical
# baseline binds. The weights below are therefore a THROUGHPUT PRIOR for ordering/backfill only;
# the memory invariant is enforced directly against reality: (a) the admission ledger counts
# max(model prior, live measured worker commit), (b) admission re-evaluates on a timer as commits
# materialize, and (c) an emergency guard SUSPENDS climbing workers (losslessly -- they resume
# when siblings complete and free RAM) before the OS runs out of commit (this box has no
# pagefile; overshoot is a hard system crash, not a slowdown).
_FG_PREBUILD_FLOOR_COMMIT_GB = 2.0  # prior: measured ~1.76 GB retained worker baseline + working headroom
# Giant prior, re-anchored on run-6 telemetry (region-fix kernel, 2 reducer threads): peak
# single-worker commit over 105 guard samples spanning the giant wave was 2.64 GB (~1.05 GB
# baseline+table + ~0.8 GB/thread live). The workspace-reuse kernel preallocates the stamp radix
# per thread (~1.0 GB ceiling on 7k-note charts), so 4 threads bound at ~1.05 + 4x~1.0 + live
# packet Lists ~= 5.5-6.5 GB; 7.0 keeps the margin. The closed-loop ledger and suspend guard
# remain the enforced bound; this prior only shapes admission width.
_FG_PREBUILD_PEAK_COMMIT_GB = 7.0
_FG_PREBUILD_PEAK_COMMIT_NOTES = 7000.0  # note count of the charts that anchored the prior
_FG_PREBUILD_SYSTEM_RESERVE_GB = 6.0  # main process + OS/desktop headroom the pool must never claim
_FG_PREBUILD_SUSPEND_FLOOR_GB = 2.0  # guard: below this free RAM, suspend the youngest workers (lowered: macOS memory compression handles pressure)
_FG_PREBUILD_RESUME_FLOOR_GB = 4.0  # guard: above this free RAM, resume one suspended worker per poll (lowered to match)
_FG_PREBUILD_GUARD_POLL_SECONDS = 5.0
# Deadlock breaker: on a RAM-starved host free RAM may never reach the resume floor, so after this
# many consecutive polls suspended without a normal resume (~60s at the poll interval) force-resume
# the oldest-suspended worker so the build cannot hang forever holding the single-builder lock.
_FG_PREBUILD_RESUME_STALL_POLLS = 12
_FG_PREBUILD_ADMIT_POLL_SECONDS = 10.0  # re-run admission as in-flight commits materialize
# Layer-3 blocked scans plus exact pair-radix workspace sizing measured the complete Stars build
# at 4/8/9 admitted group threads: 29.06/16.14/15.19 s, with 9-thread peak working set only
# 265 MB. Calamity's exact region-table bound admits 11 and measured 10m36s -> 3m57s at 1.085 GB
# peak working set. Region-table scheduling separately proves live memory against the historical
# one-table envelope; this cap prevents a short queue from claiming every logical CPU after the
# measured useful range.
_FG_PREBUILD_MAX_REDUCER_THREADS = 11


def _fg_prebuild_song_weight_gb(note_count: int) -> float:
    """Estimated peak worker commit (GB) for one song build, linear in note count.

    Anchored at the measured giant peak and extrapolating above it (a future bigger chart must
    weigh more, never clamp down); floored at the per-process baseline for tiny charts.
    """
    slope = (_FG_PREBUILD_PEAK_COMMIT_GB - _FG_PREBUILD_FLOOR_COMMIT_GB) / _FG_PREBUILD_PEAK_COMMIT_NOTES
    return _FG_PREBUILD_FLOOR_COMMIT_GB + max(0, int(note_count)) * slope


def _fg_prebuild_available_ram_gb() -> float:
    """Currently-available RAM in GB."""
    return float(psutil.virtual_memory().available) / 1e9


def _fg_prebuild_pool_worker_processes() -> list:
    """psutil handles for the live pool workers (direct python children of this process)."""
    workers = []
    for child in psutil.Process().children(recursive=False):
        try:
            if "python" in (child.name() or "").lower():
                workers.append(child)
        except psutil.Error:
            continue  # the child exited while we looked
    return workers


def _fg_prebuild_live_worker_commit_gb() -> float:
    """Sum of the pool workers' MEASURED committed memory (GB). This is the closed-loop half of
    the admission ledger: builds climb for their whole run, so the model prior alone under-admits
    protection -- reality wins whenever it exceeds the prior."""
    total = 0.0
    for proc in _fg_prebuild_pool_worker_processes():
        try:
            memory = proc.memory_info()
        except psutil.Error:
            continue  # the worker exited while we looked
        total += float(getattr(memory, "private", 0) or memory.vms) / 1e9
    return total


class _FgPrebuildRamGuard:
    """Emergency brake for the cold build on a no-pagefile box: when free RAM falls below the
    suspend floor, SUSPEND the youngest pool workers (their commit stops climbing; nothing is
    lost -- a suspended build resumes exactly where it stopped once siblings complete and free
    their memory). At least one worker always keeps running so completions keep freeing RAM.
    Suspension is the only hard bound available mid-flight: an admitted build's true peak is
    unknowable up front and ProcessPoolExecutor cannot survive killing a worker."""

    def __init__(self) -> None:
        import threading

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="fg-prebuild-ram-guard", daemon=True)
        self._suspended: list = []

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=_FG_PREBUILD_GUARD_POLL_SECONDS * 3)
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
        while not self._stop.wait(_FG_PREBUILD_GUARD_POLL_SECONDS):
            free_gb = _fg_prebuild_available_ram_gb()
            workers = _fg_prebuild_pool_worker_processes()
            suspended_pids = {proc.pid for proc in self._suspended}
            self._suspended = [proc for proc in self._suspended if proc.is_running()]
            running = [proc for proc in workers if proc.pid not in suspended_pids]

            # Deadlock breaker: the build must always be able to make forward progress. On a
            # RAM-starved host free RAM can stay permanently below the resume floor, so a worker
            # suspended to save memory would never resume -- its ProcessPoolExecutor task never
            # returns, the main thread blocks on that future forever, and the single-builder lock
            # is held indefinitely, hanging every request behind it. Force-resume the
            # oldest-suspended worker when nothing is left running to free RAM, or when
            # suspensions have stalled past the timeout without a normal (RAM-recovered) resume.
            force_resume = bool(self._suspended) and (
                not running or polls_since_resume >= _FG_PREBUILD_RESUME_STALL_POLLS
            )

            if free_gb < _FG_PREBUILD_SUSPEND_FLOOR_GB and len(running) > 1 and not force_resume:
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
                        _FG_PREBUILD_SUSPEND_FLOOR_GB,
                        youngest.pid,
                        len(self._suspended),
                        len(workers),
                    )
                polls_since_resume += 1
            elif self._suspended and (free_gb > _FG_PREBUILD_RESUME_FLOOR_GB or force_resume):
                # One per poll: a thundering resume would re-create the climb that tripped the
                # guard. When breaking a stall, resume the oldest-suspended (it has waited longest).
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


def _start_fg_prebuild_ram_guard() -> _FgPrebuildRamGuard:
    guard = _FgPrebuildRamGuard()
    guard.start()
    return guard


def _fg_prebuild_reducer_threads(
    weight_gb: float,
    *,
    budget_gb: float,
    max_workers: int,
    frontier_cpus: int,
    workload_count: int | None = None,
) -> int:
    """Intra-worker reducer threads for one song, sized to the concurrency its weight class allows.

    A giant that memory-admits ~5-at-once gets the cores those absent siblings free up (capped at
    the measured-safe thread count); a light chart that runs ~20-wide gets 1. Thread count never
    changes results -- the reducer is exact at any width -- so this is placement, not semantics.
    """
    concurrency = max(1, min(int(max_workers), int(float(budget_gb) / max(float(weight_gb), _FG_PREBUILD_FLOOR_COMMIT_GB))))
    if workload_count is not None:
        if int(workload_count) < 1:
            raise ValueError("FG prebuild reducer workload count must be positive")
        concurrency = min(int(concurrency), int(workload_count))
    return max(1, min(_FG_PREBUILD_MAX_REDUCER_THREADS, int(frontier_cpus) // concurrency))


def _dedupe_paths_by_response_bundle_key(
    song_paths: list[str],
    curves: StatCurves,
    timing_mode: str,
) -> tuple[list[tuple[str, int]], dict[str, tuple[str, ...]]]:
    """Deduplicate songs by response bundle key; representatives carry their note count.

    This is the single full-pool parse pass: the note count feeds both heaviest-first ordering and
    the admission memory weights, so no second per-song parse happens on the coordinating process.
    Duplicates share the bundle key (same chart timing content), hence the same note count.
    """
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
    configure_force_greats_response_first_frontier_threads(int(reducer_threads))
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
    tally.log_ready()
    return tally


def _build_admitted_by_weight(
    tally: PrebuildTally,
    build_items: list[tuple[str, int]],
    duplicates_of: dict[str, tuple[str, ...]],
    curves: StatCurves,
    timing_mode: str,
) -> None:
    available_gb = _fg_prebuild_available_ram_gb()
    # Never below one giant: paired with the always-admit-one guarantee below, a single
    # heaviest build alone in the machine is always schedulable.
    budget_gb = max(_FG_PREBUILD_PEAK_COMMIT_GB, float(available_gb) - _FG_PREBUILD_SYSTEM_RESERVE_GB)
    max_workers = min(frontier_prebuild_worker_count(), max(1, int(budget_gb / _FG_PREBUILD_FLOOR_COMMIT_GB)))
    frontier_cpus = frontier_prebuild_cpu_count()
    heaviest_weight = _fg_prebuild_song_weight_gb(int(build_items[0][1]))
    logger.info(
        "[FGResponseCache] Weighted admission: %s song(s), budget=%.1f GB (available=%.1f GB, reserve=%.1f GB), "
        "max_workers=%s, heaviest=%s notes (~%.1f GB).",
        len(build_items),
        budget_gb,
        available_gb,
        _FG_PREBUILD_SYSTEM_RESERVE_GB,
        int(max_workers),
        int(build_items[0][1]),
        float(heaviest_weight),
    )
    pending: list[tuple[str, int]] = list(build_items)
    in_flight: dict[concurrent.futures.Future, tuple[str, float]] = {}
    admitted_weight_gb = 0.0

    def _admit_ready(executor: BoundedRecyclingProcessPool) -> None:
        # First-fit over the heaviest-first queue: the head giant is admitted the moment it fits;
        # when it does not, lighter charts backfill the remaining budget instead of idling cores.
        nonlocal admitted_weight_gb
        while pending and len(in_flight) < max_workers:
            live_available_gb = _fg_prebuild_available_ram_gb()
            # Closed-loop ledger: builds climb for their whole run, so whenever measured worker
            # commit exceeds the model prior, reality replaces the prior in the admission bound.
            effective_ledger_gb = max(float(admitted_weight_gb), _fg_prebuild_live_worker_commit_gb())
            admit_index: int | None = None
            weight_gb = 0.0
            for index, (_path, note_count) in enumerate(pending):
                weight_gb = _fg_prebuild_song_weight_gb(int(note_count))
                if not in_flight:
                    # Progress guarantee: one build is always admitted, whatever the ledger says.
                    admit_index = index
                    break
                if effective_ledger_gb + weight_gb > budget_gb:
                    continue
                if weight_gb > live_available_gb - _FG_PREBUILD_SYSTEM_RESERVE_GB:
                    # Live backstop: already-materialized commit (model shortfall, other apps,
                    # allocator ratchet) throttles admission before the OS runs out.
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
                # Include the song just removed from pending. In the one-worker tail both
                # collections are empty here, but this admission still owns one unit of work.
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

    ram_guard = _start_fg_prebuild_ram_guard()
    try:
        # Bounded worker lifetimes release allocator high-water
        # (~1.76 GB measured idle after a giant; the 2026-07-09 overnight run pinned ~26 GB of
        # retained commit across the pool and thrashed the RAM guard for hours). Recycling a
        # whole pool after a bounded aggregate generation releases ALL retained commit; the
        # respawn cost is a warm numba cache load (~seconds), amortized over
        # max_workers * 16 songs.
        with BoundedRecyclingProcessPool(
            max_workers=max_workers,
            initializer=init_prebuild_worker,
            initargs=(curves, configure_force_greats_response_first_frontier_threads, 1),
            max_tasks_per_worker=_FG_PREBUILD_MAX_TASKS_PER_WORKER,
        ) as executor:
            _admit_ready(executor)
            while in_flight:
                # Timed wait: admission must re-evaluate as in-flight commits materialize, not
                # only at completions (builds run 30-70 minutes; the ledger is closed-loop).
                done, _not_done = concurrent.futures.wait(
                    in_flight,
                    timeout=_FG_PREBUILD_ADMIT_POLL_SECONDS,
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


def _maintain_fg_cache(
    plan: FrontierCacheManifestPlan, build_missing: bool, authorize_destructive_rotation: bool
) -> None:
    # Hits only read or repair manifest metadata. Purging and compression belong to builders and to an authorized
    # rotation: incompressible sidecars must not trigger them on every solve.
    if not (build_missing and (plan.missing_paths or authorize_destructive_rotation)):
        return
    FG_RESPONSE_FRONTIER_CACHE.remove_temp_files()
    removed = purge_stale_version_cache_files(authorize_rotation=authorize_destructive_rotation)
    if removed:
        logger.info("[FGResponseCache] Purged %s file(s) from superseded cache versions.", removed)
    compress_cache_dir_sidecars()


def _compress_built_sidecars(built: int) -> None:
    # Newly written sidecars are compressed once, with the platform's transparent filesystem codec.
    if built:
        compress_cache_dir_sidecars()


FG_RESPONSE_FRONTIER_PREBUILD = FrontierCachePrebuild(
    cache=FG_RESPONSE_FRONTIER_CACHE,
    build_songs=_build_fg_songs,
    maintain=_maintain_fg_cache,
    after_build=_compress_built_sidecars,
)
