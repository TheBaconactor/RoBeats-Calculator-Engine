from __future__ import annotations

import concurrent.futures
import logging
import os
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from gear_optimizer.core.array_signature import array_sig16
from gear_optimizer.core.cpu_affinity import (
    frontier_prebuild_cpu_count,
    frontier_prebuild_worker_count,
    init_process_pool_worker_band,
)
from gear_optimizer.solver.frontier_cache_build_lock import FrontierBuildLock
from gear_optimizer.core.profile_events import emit_profile_event, profile_events_active
from gear_optimizer.solver.frontier_cache_manifest import (
    apply_manifest_results as _shared_apply_manifest_results,
    build_manifest_plan as _shared_build_manifest_plan,
)
from gear_optimizer.solver.timeline_frontier_cache_prebuild import ordered_frontier_cache_song_paths
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FgResponseFrontierCacheBuildResult:
    path: str
    source: str
    build_ms: float
    cache_file: str


@dataclass(frozen=True)
class FgResponseFrontierCachePrebuildSummary:
    total: int = 0
    completed: int = 0
    failures: int = 0
    built: int = 0
    disk: int = 0
    memory: int = 0
    elapsed_ms: float = 0.0


_PREBUILD_WORKER_REF_ARRAYS: dict | None = None
_PREBUILD_WORKER_STAT_KEYS: tuple[tuple[int, int], ...] = ()
_MANIFEST_FILE_NAME = "fg_response_manifest_v1.json"

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
_FG_PREBUILD_SUSPEND_FLOOR_GB = 5.0  # guard: below this free RAM, suspend the youngest workers
_FG_PREBUILD_RESUME_FLOOR_GB = 12.0  # guard: above this free RAM, resume one suspended worker per poll
_FG_PREBUILD_GUARD_POLL_SECONDS = 5.0
_FG_PREBUILD_ADMIT_POLL_SECONDS = 10.0  # re-run admission as in-flight commits materialize
# Widened 2 -> 4 with the workspace-reuse kernel: per-thread scratch is now a PREALLOCATED
# ~1.0 GB ceiling (stamp radix sized to the chart's hard maxima) instead of an unbounded
# per-call transient, so the peak prior above covers 4 threads arithmetically. The historical
# rule stands: this cap and the peak prior must move together, anchored on guard telemetry.
_FG_PREBUILD_MAX_REDUCER_THREADS = 4


def _fg_prebuild_song_weight_gb(note_count: int) -> float:
    """Estimated peak worker commit (GB) for one song build, linear in note count.

    Anchored at the measured giant peak and extrapolating above it (a future bigger chart must
    weigh more, never clamp down); floored at the per-process baseline for tiny charts.
    """
    slope = (_FG_PREBUILD_PEAK_COMMIT_GB - _FG_PREBUILD_FLOOR_COMMIT_GB) / _FG_PREBUILD_PEAK_COMMIT_NOTES
    return _FG_PREBUILD_FLOOR_COMMIT_GB + max(0, int(note_count)) * slope


def _fg_prebuild_available_ram_gb() -> float | None:
    """Currently-available RAM in GB, or None when psutil is unavailable (optional dependency
    boundary, mirroring cpu_affinity: without it admission falls back to the core-derived cap)."""
    try:
        import psutil

        return float(psutil.virtual_memory().available) / 1e9
    except Exception:
        return None


def _fg_prebuild_pool_worker_processes() -> list:
    """psutil handles for the live pool workers (direct python children of this process)."""
    try:
        import psutil

        children = psutil.Process().children(recursive=False)
    except Exception:
        return []
    workers = []
    for child in children:
        try:
            if "python" in (child.name() or "").lower():
                workers.append(child)
        except Exception:
            continue
    return workers


def _fg_prebuild_live_worker_commit_gb() -> float:
    """Sum of the pool workers' MEASURED committed memory (GB). This is the closed-loop half of
    the admission ledger: builds climb for their whole run, so the model prior alone under-admits
    protection -- reality wins whenever it exceeds the prior."""
    total = 0.0
    for proc in _fg_prebuild_pool_worker_processes():
        try:
            memory = proc.memory_info()
            total += float(getattr(memory, "private", 0) or memory.vms) / 1e9
        except Exception:
            continue
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
        self._samples = 0

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
        except Exception:
            pass
        if proc in self._suspended:
            self._suspended.remove(proc)

    def _run(self) -> None:
        while not self._stop.wait(_FG_PREBUILD_GUARD_POLL_SECONDS):
            free_gb = _fg_prebuild_available_ram_gb()
            if free_gb is None:
                return
            workers = _fg_prebuild_pool_worker_processes()
            suspended_pids = {proc.pid for proc in self._suspended}
            self._suspended = [proc for proc in self._suspended if proc.is_running()]
            running = [proc for proc in workers if proc.pid not in suspended_pids]
            if free_gb < _FG_PREBUILD_SUSPEND_FLOOR_GB and len(running) > 1:
                # Youngest first: it has the least sunk work and the steepest remaining climb.
                youngest = max(running, key=lambda proc: proc.create_time())
                try:
                    youngest.suspend()
                except Exception:
                    pass
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
                    emit_profile_event(
                        component="fg_response_cache",
                        event="ram_guard_suspend",
                        metrics={"free_gb": float(free_gb), "suspended": len(self._suspended), "workers": len(workers)},
                    )
            elif free_gb > _FG_PREBUILD_RESUME_FLOOR_GB and self._suspended:
                # One per poll: a thundering resume would re-create the climb that tripped the guard.
                proc = self._suspended[-1]
                self._resume(proc)
                logger.info(
                    "[FGResponseCache] RAM guard: %.1f GB free; resumed worker %s (%s still suspended).",
                    free_gb,
                    proc.pid,
                    len(self._suspended),
                )
                emit_profile_event(
                    component="fg_response_cache",
                    event="ram_guard_resume",
                    metrics={"free_gb": float(free_gb), "suspended": len(self._suspended)},
                )
            self._samples += 1
            if self._samples % 12 == 0:
                # Once a minute: the per-worker commit climb curves that end anchor guesswork.
                commits = []
                for proc in workers:
                    try:
                        memory = proc.memory_info()
                        commits.append(round(float(getattr(memory, "private", 0) or memory.vms) / 1e9, 2))
                    except Exception:
                        continue
                emit_profile_event(
                    component="fg_response_cache",
                    event="ram_guard_sample",
                    metrics={
                        "free_gb": float(free_gb),
                        "worker_commit_gb": commits,
                        "suspended": len(self._suspended),
                    },
                )


def _start_fg_prebuild_ram_guard() -> _FgPrebuildRamGuard | None:
    if _fg_prebuild_available_ram_gb() is None:
        return None
    guard = _FgPrebuildRamGuard()
    guard.start()
    return guard


def _fg_prebuild_reducer_threads(weight_gb: float, *, budget_gb: float | None, max_workers: int, frontier_cpus: int) -> int:
    """Intra-worker reducer threads for one song, sized to the concurrency its weight class allows.

    A giant that memory-admits ~5-at-once gets the cores those absent siblings free up (capped at
    the measured-safe thread count); a light chart that runs ~20-wide gets 1. Thread count never
    changes results -- the reducer is exact at any width -- so this is placement, not semantics.
    """
    if budget_gb is None:
        concurrency = max(1, int(max_workers))
    else:
        concurrency = max(1, min(int(max_workers), int(float(budget_gb) / max(float(weight_gb), _FG_PREBUILD_FLOOR_COMMIT_GB))))
    return max(1, min(_FG_PREBUILD_MAX_REDUCER_THREADS, int(frontier_cpus) // concurrency))


def _init_prebuild_worker(
    ref_arrays: dict,
    stat_keys: tuple[tuple[int, int], ...],
    reducer_threads: int = 1,
    total_workers: int = 1,
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_reducer

    init_process_pool_worker_band(int(total_workers))
    global _PREBUILD_WORKER_REF_ARRAYS, _PREBUILD_WORKER_STAT_KEYS
    _PREBUILD_WORKER_REF_ARRAYS = dict(ref_arrays or {})
    _PREBUILD_WORKER_STAT_KEYS = tuple(stat_keys or ())
    response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(max(1, int(reducer_threads)))


def _build_fg_response_frontier_cache_for_path_shared(
    song_path_text: str,
    reducer_threads: int | None = None,
) -> FgResponseFrontierCacheBuildResult:
    if reducer_threads is not None:
        from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_reducer

        # Per-task width from the admission scheduler: sized to this song's memory weight class.
        response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(int(reducer_threads))
    shared = _PREBUILD_WORKER_REF_ARRAYS if isinstance(_PREBUILD_WORKER_REF_ARRAYS, dict) else {}
    return build_fg_response_frontier_cache_for_path(
        song_path_text,
        shared,
        stat_keys=_PREBUILD_WORKER_STAT_KEYS,
    )

def _manifest_path() -> Path:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import _fg_response_disk_cache_dir

    return _fg_response_disk_cache_dir() / _MANIFEST_FILE_NAME


def _cache_version() -> str:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import _FG_RESPONSE_CACHE_VERSION

    return str(_FG_RESPONSE_CACHE_VERSION)


def _ref_axes_signature(ref_arrays: dict) -> str:
    ref_ft = np.asarray((ref_arrays or {}).get("Fever Time", ()), dtype=np.float32).reshape(-1)
    ref_ff = np.asarray((ref_arrays or {}).get("Fever Fill Rate", ()), dtype=np.float32).reshape(-1)
    return bytes(array_sig16(ref_ft) + array_sig16(ref_ff)).hex()


def _stat_keys_signature(stat_keys: Iterable[tuple[int, int]]) -> str:
    rows = np.asarray(tuple((int(ft), int(ff)) for ft, ff in stat_keys), dtype=np.int32).reshape((-1, 2))
    return bytes(array_sig16(rows.reshape(-1))).hex()


def _derived_bundle_cache_file(song_path: str, ref_arrays: dict) -> str | None:
    """Parse one chart and return the cache file its CURRENT bundle key derives (drift probe)."""
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
        _fg_response_disk_cache_path,
        fg_response_frontier_bundle_cache_key,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    calc_song = get_base_calc_song(str(song_path), {})
    if not calc_song:
        return None
    apply_timing_envelope(calc_song)
    return str(_fg_response_disk_cache_path(fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)))


def _build_manifest_plan(song_paths: Iterable[str], ref_arrays: dict, *, stat_keys: Iterable[tuple[int, int]]):
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import fg_response_cache_file_is_complete

    stat_keys_tuple = tuple(stat_keys or ())
    return _shared_build_manifest_plan(
        song_paths,
        manifest_path=_manifest_path(),
        cache_version=_cache_version(),
        version_field="cache_version",
        ref_sig_hex=_ref_axes_signature(ref_arrays),
        stat_sig_hex=_stat_keys_signature(stat_keys_tuple),
        cache_file_validator=lambda cache_file: fg_response_cache_file_is_complete(
            cache_file,
            stat_keys=stat_keys_tuple,
        ),
        derived_cache_file_fn=lambda song_path: _derived_bundle_cache_file(song_path, ref_arrays),
    )


def _apply_manifest_results(*, plan, results: Iterable[object], stat_keys: Iterable[tuple[int, int]]) -> int:
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import fg_response_cache_file_is_complete

    stat_keys_tuple = tuple(stat_keys or ())
    return _shared_apply_manifest_results(
        plan=plan,
        manifest_path=_manifest_path(),
        cache_version=_cache_version(),
        version_field="cache_version",
        results=results,
        cache_file_validator=lambda cache_file: fg_response_cache_file_is_complete(
            cache_file,
            stat_keys=stat_keys_tuple,
        ),
    )


def _dedupe_paths_by_response_bundle_key(
    paths: Iterable[str], ref_arrays: dict
) -> tuple[list[tuple[str, int]], dict[str, tuple[str, ...]]]:
    """Deduplicate songs by response bundle key; representatives carry their note count.

    This is the single full-pool parse pass: the note count feeds both heaviest-first ordering and
    the admission memory weights, so no second per-song parse happens on the coordinating process.
    Duplicates share the bundle key (same chart timing content), hence the same note count.
    """
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import fg_response_frontier_bundle_cache_key
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    representatives: list[tuple[str, int]] = []
    duplicates: dict[str, list[str]] = {}
    representative_by_key: dict[tuple, str] = {}
    for path_text in paths:
        path = str(path_text)
        calc_song = get_base_calc_song(path, {})
        apply_timing_envelope(calc_song)
        key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
        representative = representative_by_key.get(key)
        if representative is None:
            timestamps = calc_song.get("song_data", {}).get("timestamps", ())
            note_count = int(len(timestamps) if timestamps is not None else 0)
            representative_by_key[key] = path
            representatives.append((path, note_count))
            duplicates[path] = []
        else:
            duplicates[representative].append(path)
    return representatives, {
        str(path): tuple(str(value) for value in duplicate_paths)
        for path, duplicate_paths in duplicates.items()
        if duplicate_paths
    }


def build_fg_response_frontier_cache_for_path(
    song_path_text: str,
    ref_arrays: dict,
    *,
    stat_keys: Iterable[tuple[int, int]],
) -> FgResponseFrontierCacheBuildResult:
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        fg_response_frontier_payload_cache_info,
        release_fg_response_song_memory,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import (
        fg_response_frontier_bundle_cache_key,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    song_path = Path(song_path_text)
    calc_song = get_base_calc_song(str(song_path), {})
    apply_timing_envelope(calc_song)
    cache_info = fg_response_frontier_payload_cache_info(calc_song, ref_arrays, stat_keys=stat_keys)
    if cache_info.cache_source in {"disk", "memory"}:
        return FgResponseFrontierCacheBuildResult(
            path=str(song_path),
            source=str(cache_info.cache_source),
            build_ms=0.0,
            cache_file=str(cache_info.disk_path),
        )
    try:
        result = build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=stat_keys)
    finally:
        # The prebuild contract is disk files; build_or_load additionally pins the built
        # bundle+payload (~1 GB of frontier rows on heavy charts) into the process-global
        # payload LRU for live-process reuse that never happens here. Left pinned, a worker
        # building heaviest-first accumulates up to 4 songs' bundles (~4-5 GB dead weight per
        # worker) on top of the current build's transient peak -- the measured OOM/paging
        # driver on EXTENDED CUT charts. Release sweeps every per-song cache tier by key
        # prefix; the bundle just written re-opens from disk wherever it is next needed.
        release_fg_response_song_memory(fg_response_frontier_bundle_cache_key(calc_song, ref_arrays))
    if profile_events_active():
        # Per-song worker memory ground truth: calibrates/validates the admission weight anchors
        # (peak_wset/private are Windows-only psutil fields; 0.0 elsewhere).
        try:
            import psutil

            memory = psutil.Process().memory_info()
        except ImportError:
            memory = None
        if memory is not None:
            timestamps = calc_song.get("song_data", {}).get("timestamps", ())
            emit_profile_event(
                component="fg_response_cache",
                event="prebuild_song_done",
                song_key=song_path.name,
                metrics={
                    "build_ms": float(result.elapsed_ms),
                    "source": str(result.cache_source),
                    "note_count": int(len(timestamps) if timestamps is not None else 0),
                    "rss_gb": float(memory.rss) / 1e9,
                    "peak_wset_gb": float(getattr(memory, "peak_wset", 0)) / 1e9,
                    "private_gb": float(getattr(memory, "private", 0)) / 1e9,
                },
            )
    return FgResponseFrontierCacheBuildResult(
        path=str(song_path),
        source=str(result.cache_source),
        build_ms=float(result.elapsed_ms),
        cache_file=str(result.disk_path),
    )


def ensure_response_frontier_cache_for_calc_song(
    calc_song: dict,
    ref_arrays: dict,
    *,
    stat_keys: Iterable[tuple[int, int]] | None = None,
) -> None:
    """Ensure the response-frontier CACHE (npz bundle + sidecars) exists on disk/in memory.

    In-memory owner entry for callers that hold a prepared calc_song (e.g. fixed-0ms
    tier replay) rather than a song path. The candidate-independent all-FT/FF bundle is
    keyed by the song's timing context, so a chart-only (zero_ms) calc_song builds its
    own bundle distinct from the perfect_window one. Idempotent; keeps the single
    production owner of ``build_or_load_response_frontier_payload`` intact.

    Contract: this guarantees the cache FILES are present; it does NOT materialize the
    full in-memory payload. On a warm hit it returns after a metadata + sidecar-header
    probe and deliberately skips ``build_or_load``'s eager per-row object materialization
    (seconds on heavy bundles), because the scoring batch prepared downstream
    (``prepare_force_greats_response_frontier_scoring_batch``) reads only the slim bundle
    + sidecars, never that payload. A cold miss builds the bundle in full.
    """
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        build_or_load_response_frontier_payload,
        fg_response_frontier_payload_cache_info,
    )

    keys = tuple(stat_keys) if stat_keys is not None else all_response_stat_keys()
    # Existence probe first (npz metadata + sidecar headers): build_or_load eagerly
    # materializes every pool row into Python objects -- seconds on heavy bundles -- and
    # no consumer on this path reads that payload (scoring uses the slim bundle +
    # sidecars). Same fast path as build_fg_response_frontier_cache_for_path above.
    cache_info = fg_response_frontier_payload_cache_info(calc_song, ref_arrays, stat_keys=keys)
    if cache_info.cache_source in {"disk", "memory"}:
        return
    build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=keys)


def _run_missing_fg_prebuild(
    paths: list[str],
    ref_arrays: dict,
    stat_keys: tuple[tuple[int, int], ...],
) -> tuple[FgResponseFrontierCachePrebuildSummary, list[FgResponseFrontierCacheBuildResult]]:
    if not paths:
        return FgResponseFrontierCachePrebuildSummary(total=0), []
    t0 = time.perf_counter()
    source_counts: Counter[str] = Counter()
    failures = 0
    completed = 0
    results: list[FgResponseFrontierCacheBuildResult] = []
    build_items, duplicate_paths_by_representative = _dedupe_paths_by_response_bundle_key(paths, ref_arrays)
    # Heaviest-first (same makespan ordering as before), note counts from the dedupe parse pass.
    build_items.sort(key=lambda item: (-int(item[1]), str(item[0]).lower()))
    if len(build_items) == 1:
        path = str(build_items[0][0])
        duplicate_paths = duplicate_paths_by_representative.get(path, ())
        try:
            result = build_fg_response_frontier_cache_for_path(path, ref_arrays, stat_keys=stat_keys)
        except Exception as exc:
            failures = 1 + int(len(duplicate_paths))
            logger.warning("[FGResponseCache] Failed to prebuild %s: %s", path, exc)
        else:
            completed = 1
            results.append(result)
            source_counts[result.source] += 1
            if duplicate_paths:
                duplicate_source = "disk" if result.cache_file and os.path.exists(result.cache_file) else result.source
                for duplicate_path in duplicate_paths:
                    completed += 1
                    duplicate_result = FgResponseFrontierCacheBuildResult(
                        path=str(duplicate_path),
                        source=str(duplicate_source),
                        build_ms=0.0,
                        cache_file=str(result.cache_file),
                    )
                    results.append(duplicate_result)
                    source_counts[duplicate_source] += 1
        elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
        return (
            FgResponseFrontierCachePrebuildSummary(
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
    if duplicate_paths_by_representative:
        duplicate_count = sum(len(values) for values in duplicate_paths_by_representative.values())
        logger.info(
            "[FGResponseCache] Dedupe skipped %s/%s duplicate response bundle path(s) before worker build.",
            int(duplicate_count),
            int(len(paths)),
        )
    available_gb = _fg_prebuild_available_ram_gb()
    budget_gb: float | None = None
    if available_gb is not None:
        # Never below one giant: paired with the always-admit-one guarantee below, a single
        # heaviest build alone in the machine is always schedulable.
        budget_gb = max(_FG_PREBUILD_PEAK_COMMIT_GB, float(available_gb) - _FG_PREBUILD_SYSTEM_RESERVE_GB)
    max_workers = frontier_prebuild_worker_count()
    if budget_gb is not None:
        max_workers = min(max_workers, max(1, int(budget_gb / _FG_PREBUILD_FLOOR_COMMIT_GB)))
    frontier_cpus = frontier_prebuild_cpu_count()
    heaviest_weight = _fg_prebuild_song_weight_gb(int(build_items[0][1]))
    logger.info(
        "[FGResponseCache] Weighted admission: %s song(s), budget=%s GB (available=%s GB, reserve=%.1f GB), "
        "max_workers=%s, heaviest=%s notes (~%.1f GB).",
        len(build_items),
        f"{budget_gb:.1f}" if budget_gb is not None else "uncapped",
        f"{available_gb:.1f}" if available_gb is not None else "unknown",
        _FG_PREBUILD_SYSTEM_RESERVE_GB,
        int(max_workers),
        int(build_items[0][1]),
        float(heaviest_weight),
    )
    pending: list[tuple[str, int]] = list(build_items)
    in_flight: dict[concurrent.futures.Future, tuple[str, float]] = {}
    admitted_weight_gb = 0.0

    def _admit_ready(executor: concurrent.futures.ProcessPoolExecutor) -> None:
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
                if budget_gb is not None and effective_ledger_gb + weight_gb > budget_gb:
                    continue
                if live_available_gb is not None and weight_gb > live_available_gb - _FG_PREBUILD_SYSTEM_RESERVE_GB:
                    # Live backstop: already-materialized commit (model shortfall, other apps,
                    # allocator ratchet) throttles admission before the OS runs out.
                    continue
                admit_index = index
                break
            if admit_index is None:
                return
            path, note_count = pending.pop(admit_index)
            reducer_threads = _fg_prebuild_reducer_threads(
                weight_gb, budget_gb=budget_gb, max_workers=max_workers, frontier_cpus=frontier_cpus
            )
            future = executor.submit(_build_fg_response_frontier_cache_for_path_shared, path, int(reducer_threads))
            in_flight[future] = (path, float(weight_gb))
            admitted_weight_gb += float(weight_gb)
            if weight_gb >= 4.0:
                logger.info(
                    "[FGResponseCache] Admitted giant %s (%s notes, ~%.1f GB, %s reducer threads); "
                    "in-flight=%s (~%.1f/%s GB).",
                    os.path.basename(path),
                    int(note_count),
                    float(weight_gb),
                    int(reducer_threads),
                    len(in_flight),
                    float(admitted_weight_gb),
                    f"{budget_gb:.1f}" if budget_gb is not None else "uncapped",
                )
            emit_profile_event(
                component="fg_response_cache",
                event="prebuild_admit",
                song_key=os.path.basename(path),
                metrics={
                    "note_count": int(note_count),
                    "weight_gb": float(weight_gb),
                    "reducer_threads": int(reducer_threads),
                    "in_flight": int(len(in_flight)),
                    "admitted_weight_gb": float(admitted_weight_gb),
                    "effective_ledger_gb": float(effective_ledger_gb),
                    "available_gb": float(live_available_gb) if live_available_gb is not None else -1.0,
                },
            )

    ram_guard = _start_fg_prebuild_ram_guard()
    try:
        # max_tasks_per_child: pool workers permanently retain their allocator high-water
        # (~1.76 GB measured idle after a giant; the 2026-07-09 overnight run pinned ~26 GB of
        # retained commit across the pool and thrashed the RAM guard for hours). Recycling a
        # worker after a bounded number of builds releases ALL its commit; the respawn cost is a
        # warm numba cache load (~seconds), amortized over 16 songs and overlapped with the
        # other workers.
        with concurrent.futures.ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=_init_prebuild_worker,
            initargs=(dict(ref_arrays or {}), tuple(stat_keys or ()), 1, int(max_workers)),
            max_tasks_per_child=16,
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
                    duplicate_paths = duplicate_paths_by_representative.get(path, ())
                    try:
                        result = future.result()
                    except Exception as exc:
                        failures += 1 + int(len(duplicate_paths))
                        logger.warning("[FGResponseCache] Failed to prebuild %s: %s", path, exc)
                        continue
                    completed += 1
                    results.append(result)
                    source_counts[result.source] += 1
                    if duplicate_paths:
                        duplicate_source = "disk" if result.cache_file and os.path.exists(result.cache_file) else result.source
                        for duplicate_path in duplicate_paths:
                            completed += 1
                            duplicate_result = FgResponseFrontierCacheBuildResult(
                                path=str(duplicate_path),
                                source=str(duplicate_source),
                                build_ms=0.0,
                                cache_file=str(result.cache_file),
                            )
                            results.append(duplicate_result)
                            source_counts[duplicate_source] += 1
                    if completed == 1 or completed % 10 == 0:
                        logger.info(
                            "[FGResponseCache] %s/%s complete (built=%s disk=%s memory=%s, latest=%s %.1fms)",
                            completed,
                            len(paths),
                            int(source_counts.get("built", 0)),
                            int(source_counts.get("disk", 0)),
                            int(source_counts.get("memory", 0)),
                            result.source,
                            float(result.build_ms),
                        )
                _admit_ready(executor)
    finally:
        if ram_guard is not None:
            ram_guard.stop()
    elapsed_ms = float((time.perf_counter() - t0) * 1000.0)
    summary = FgResponseFrontierCachePrebuildSummary(
        total=int(len(paths)),
        completed=int(completed),
        failures=int(failures),
        built=int(source_counts.get("built", 0)),
        disk=int(source_counts.get("disk", 0)),
        memory=int(source_counts.get("memory", 0)),
        elapsed_ms=elapsed_ms,
    )
    logger.info(
        "[FGResponseCache] Response-frontier prebuild ready: completed=%s/%s failures=%s built=%s disk=%s memory=%s elapsed=%.1fs",
        completed,
        len(paths),
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
            "total": int(len(paths)),
            "failures": int(failures),
            "built": int(source_counts.get("built", 0)),
            "disk": int(source_counts.get("disk", 0)),
            "memory": int(source_counts.get("memory", 0)),
            "elapsed_ms": elapsed_ms,
        },
    )
    return summary, results


def run_fg_response_frontier_cache_prebuild(
    *,
    cfg,
    song_queue: Iterable[tuple],
    ref_arrays: dict,
    data_root: str | os.PathLike[str] | None = None,
) -> FgResponseFrontierCachePrebuildSummary:
    del cfg
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
        _fg_response_disk_cache_dir,
        cleanup_fg_response_frontier_cache_temp_files,
        compress_cache_dir_sidecars,
        purge_stale_version_cache_files,
    )

    started = time.perf_counter()
    stat_keys = all_response_stat_keys()
    queue_paths = [str(item[0]) for item in song_queue if isinstance(item, tuple) and item]
    paths = ordered_frontier_cache_song_paths(queue_paths=queue_paths, data_root=data_root)
    if not paths:
        return FgResponseFrontierCachePrebuildSummary(total=0)

    # Single-builder lock: a second concurrent process waits here, then re-runs its manifest plan
    # below -- which now fast-hits everything this process wrote -- instead of duplicating the
    # multi-GB cold build and multiplying peak RAM.
    with FrontierBuildLock(_fg_response_disk_cache_dir(), label="fg_response"):
        manifest_plan = _build_manifest_plan(paths, ref_arrays, stat_keys=stat_keys)
        manifest_hits = int(manifest_plan.hit_count)
        if manifest_hits > 0:
            logger.info(
                "[FGResponseCache] Manifest fast-hit skipped %s/%s song(s) before worker parse/build.",
                manifest_hits,
                int(manifest_plan.total_paths),
            )

        removed_tmp = cleanup_fg_response_frontier_cache_temp_files()
        if int(removed_tmp) > 0:
            logger.info("[FGResponseCache] Removed %s stale temporary cache file(s).", int(removed_tmp))

        removed_stale = purge_stale_version_cache_files()
        if int(removed_stale) > 0:
            logger.info(
                "[FGResponseCache] Purged %s file(s) from superseded cache versions.", int(removed_stale)
            )

        # Deterministic input order; heaviest-first execution ordering happens inside
        # _run_missing_fg_prebuild from the same parse pass that computes admission weights.
        missing_paths = sorted(str(path) for path in manifest_plan.missing_paths)
        run_summary, results = _run_missing_fg_prebuild(list(missing_paths), ref_arrays, stat_keys)
        _apply_manifest_results(plan=manifest_plan, results=results, stat_keys=stat_keys)
        elapsed_ms = float((time.perf_counter() - started) * 1000.0)
        if int(run_summary.built) > 0:
            # Bulk-compress newly written sidecars once (NTFS WOF XPRESS16K, ~6x, memmap preserved).
            # Housekeeping after the timed region so elapsed_ms reflects build cost, not compaction.
            compress_cache_dir_sidecars()
        return FgResponseFrontierCachePrebuildSummary(
            total=int(manifest_plan.total_paths),
            completed=int(manifest_hits + run_summary.completed),
            failures=int(run_summary.failures),
            built=int(run_summary.built),
            disk=int(manifest_hits + run_summary.disk),
            memory=int(run_summary.memory),
            elapsed_ms=elapsed_ms,
        )
