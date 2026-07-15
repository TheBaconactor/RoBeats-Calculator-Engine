"""Startup owner for catalog-independent exact Base song-context artifacts."""

from __future__ import annotations

import concurrent.futures
from collections import Counter
from dataclasses import dataclass
import logging
import multiprocessing
import os
from pathlib import Path
import time
from typing import Iterable

import numpy as np

from gear_optimizer.core.array_signature import arrays_sig16
from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.cpu_affinity import (
    init_process_pool_worker_band,
    timeline_prebuild_worker_count,
)
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.exact_base_song_context import ExactBaseSongContextInputs
from gear_optimizer.solver.exact_base_song_context_cache import (
    EXACT_BASE_SONG_CONTEXT_CACHE_VERSION,
    exact_base_song_context_cache_file_is_complete,
    exact_base_song_context_cache_path,
    exact_base_song_context_manifest_path,
    load_or_build_exact_base_song_context,
)
from gear_optimizer.solver.frontier_cache_build_lock import FrontierBuildLock
from gear_optimizer.solver.frontier_cache_manifest import (
    apply_manifest_results as _shared_apply_manifest_results,
    build_manifest_plan as _shared_build_manifest_plan,
)
from gear_optimizer.solver.timeline_frontier_cache_prebuild import (
    ordered_frontier_cache_song_paths,
)


logger = logging.getLogger(__name__)

_MANIFEST_FILE_NAME = "exact_base_song_context_startup_manifest_v1.json"
_PREBUILD_PENDING_PER_WORKER = 2
_PREBUILD_TASKS_PER_WORKER = 8
_PREBUILD_WORKER_REF_ARRAYS: dict | None = None


@dataclass(frozen=True)
class ExactBaseSongContextCacheBuildResult:
    path: str
    source: str
    build_ms: float
    cache_file: str


@dataclass(frozen=True)
class ExactBaseSongContextCachePrebuildSummary:
    total: int = 0
    completed: int = 0
    failures: int = 0
    built: int = 0
    disk: int = 0
    memory: int = 0
    elapsed_ms: float = 0.0


def _cache_root() -> Path:
    return exact_base_song_context_manifest_path().parent


def _manifest_path() -> Path:
    return _cache_root() / _MANIFEST_FILE_NAME


def _manifest_lock_dir() -> Path:
    return _cache_root() / ".startup_manifest_lock"


def _ref_axes_signature(ref_arrays: dict) -> str:
    names = (
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Time",
        "Fever Fill Rate",
    )
    arrays = tuple(
        np.asarray((ref_arrays or {}).get(name, ())).reshape(-1)
        for name in names
    )
    return bytes(arrays_sig16(*arrays)).hex()


def _context_inputs_for_calc_song(
    calc_song: dict,
    ref_arrays: dict,
) -> ExactBaseSongContextInputs:
    metadata = dict((calc_song or {}).get("metadata", {}) or {})
    primary_color = str(metadata.get("Primary Color", "Rush") or "Rush")
    secondary_color = str(metadata.get("Secondary Color", "") or "")
    return ExactBaseSongContextInputs(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        color_flags=build_color_flags(
            primary_color,
            secondary_color,
            primary_color,
        ),
    )


def _load_prebuilt_song_inputs(
    song_path_text: str,
    ref_arrays: dict,
):
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.api.timeline import (
        load_prebuilt_timeline_frontier_payload,
    )
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    calc_song = get_base_calc_song(str(song_path_text), {})
    if not calc_song:
        raise ValueError(f"Could not parse song for exact Base context prebuild: {song_path_text}")
    apply_timing_envelope(calc_song)
    timeline = load_prebuilt_timeline_frontier_payload(calc_song, ref_arrays)
    return _context_inputs_for_calc_song(calc_song, ref_arrays), timeline


def _derived_cache_file(song_path: str, ref_arrays: dict) -> str:
    inputs, timeline = _load_prebuilt_song_inputs(song_path, ref_arrays)
    return str(exact_base_song_context_cache_path(inputs, timeline.payload))


def _build_manifest_plan(
    song_paths: Iterable[str],
    ref_arrays: dict,
    *,
    persist_validated_entries: bool = True,
):
    return _shared_build_manifest_plan(
        song_paths,
        manifest_path=_manifest_path(),
        cache_version=EXACT_BASE_SONG_CONTEXT_CACHE_VERSION,
        version_field="context_version",
        ref_sig_hex=_ref_axes_signature(ref_arrays),
        cache_file_validator=exact_base_song_context_cache_file_is_complete,
        derived_cache_file_fn=lambda song_path: _derived_cache_file(song_path, ref_arrays),
        persist_validated_entries=persist_validated_entries,
    )


def _apply_manifest_results(*, plan, results: Iterable[object]) -> int:
    return _shared_apply_manifest_results(
        plan=plan,
        manifest_path=_manifest_path(),
        cache_version=EXACT_BASE_SONG_CONTEXT_CACHE_VERSION,
        version_field="context_version",
        results=results,
        cache_file_validator=exact_base_song_context_cache_file_is_complete,
    )


def build_exact_base_song_context_cache_for_path(
    song_path_text: str,
    ref_arrays: dict,
) -> ExactBaseSongContextCacheBuildResult:
    started = time.perf_counter()
    inputs, timeline = _load_prebuilt_song_inputs(song_path_text, ref_arrays)
    result = load_or_build_exact_base_song_context(inputs, timeline.payload)
    return ExactBaseSongContextCacheBuildResult(
        path=str(song_path_text),
        source=str(result.cache_source),
        build_ms=float((time.perf_counter() - started) * 1000.0),
        cache_file=str(result.disk_path),
    )


def _init_prebuild_worker(ref_arrays: dict, total_workers: int) -> None:
    init_process_pool_worker_band(int(total_workers))
    global _PREBUILD_WORKER_REF_ARRAYS
    _PREBUILD_WORKER_REF_ARRAYS = dict(ref_arrays or {})


def _build_exact_base_song_context_cache_for_path_shared(
    song_path_text: str,
) -> ExactBaseSongContextCacheBuildResult:
    if _PREBUILD_WORKER_REF_ARRAYS is None:
        raise RuntimeError("Exact Base context prebuild worker references were not initialized")
    return build_exact_base_song_context_cache_for_path(
        song_path_text,
        _PREBUILD_WORKER_REF_ARRAYS,
    )


def _run_missing_context_prebuild(
    paths: list[str],
    ref_arrays: dict,
) -> tuple[
    ExactBaseSongContextCachePrebuildSummary,
    list[ExactBaseSongContextCacheBuildResult],
]:
    if not paths:
        return ExactBaseSongContextCachePrebuildSummary(total=0), []
    started = time.perf_counter()
    sources: Counter[str] = Counter()
    failures = 0
    completed = 0
    results: list[ExactBaseSongContextCacheBuildResult] = []

    if len(paths) == 1:
        path = str(paths[0])
        try:
            result = build_exact_base_song_context_cache_for_path(path, ref_arrays)
        except Exception as exc:
            failures = 1
            logger.warning("[ExactBaseContextCache] Failed to prebuild %s: %s", path, exc)
        else:
            completed = 1
            results.append(result)
            sources[result.source] += 1
    else:
        worker_count = max(
            1,
            min(
                int(timeline_prebuild_worker_count()),
                len(paths),
            ),
        )
        generation_capacity = int(worker_count) * int(_PREBUILD_TASKS_PER_WORKER)
        for generation_start in range(0, len(paths), generation_capacity):
            generation_paths = paths[
                generation_start : generation_start + generation_capacity
            ]
            generation_workers = min(int(worker_count), len(generation_paths))

            # Native array allocations are not reliably returned to Windows while
            # a worker remains alive. Bound that retained commit by giving each
            # spawn pool a fixed amount of work, then fully drain its futures and
            # leave the executor context before constructing the next generation.
            # Pool ownership stays outside submit(), avoiding queue-manager
            # shutdown races at a generation boundary.
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=generation_workers,
                mp_context=multiprocessing.get_context("spawn"),
                initializer=_init_prebuild_worker,
                initargs=(dict(ref_arrays or {}), int(generation_workers)),
            ) as executor:
                path_iter = iter(generation_paths)
                in_flight: dict[concurrent.futures.Future, str] = {}

                def _submit_one() -> bool:
                    try:
                        path = next(path_iter)
                    except StopIteration:
                        return False
                    future = executor.submit(
                        _build_exact_base_song_context_cache_for_path_shared,
                        path,
                    )
                    in_flight[future] = path
                    return True

                pending_limit = min(
                    len(generation_paths),
                    int(generation_workers) * int(_PREBUILD_PENDING_PER_WORKER),
                )
                for _ in range(pending_limit):
                    _submit_one()

                while in_flight:
                    done, _not_done = concurrent.futures.wait(
                        in_flight,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    for future in done:
                        path = in_flight.pop(future)
                        try:
                            result = future.result()
                        except Exception as exc:
                            failures += 1
                            logger.warning(
                                "[ExactBaseContextCache] Failed to prebuild %s: %s",
                                path,
                                exc,
                            )
                        else:
                            completed += 1
                            results.append(result)
                            sources[result.source] += 1
                            if completed == 1 or completed % 25 == 0:
                                logger.info(
                                    "[ExactBaseContextCache] %s/%s complete "
                                    "(built=%s disk=%s memory=%s, latest=%s %.1fms)",
                                    completed,
                                    len(paths),
                                    int(sources.get("built", 0)),
                                    int(sources.get("disk", 0)),
                                    int(sources.get("memory", 0)),
                                    result.source,
                                    float(result.build_ms),
                                )
                        _submit_one()

    elapsed_ms = float((time.perf_counter() - started) * 1000.0)
    summary = ExactBaseSongContextCachePrebuildSummary(
        total=len(paths),
        completed=completed,
        failures=failures,
        built=int(sources.get("built", 0)),
        disk=int(sources.get("disk", 0)),
        memory=int(sources.get("memory", 0)),
        elapsed_ms=elapsed_ms,
    )
    logger.info(
        "[ExactBaseContextCache] Song-context prebuild ready: "
        "completed=%s/%s failures=%s built=%s disk=%s memory=%s elapsed=%.1fs",
        completed,
        len(paths),
        failures,
        int(summary.built),
        int(summary.disk),
        int(summary.memory),
        elapsed_ms / 1000.0,
    )
    return summary, results


def run_exact_base_song_context_cache_prebuild(
    *,
    cfg,
    song_queue: Iterable[tuple],
    ref_arrays: dict,
    data_root: str | os.PathLike[str] | None = None,
) -> ExactBaseSongContextCachePrebuildSummary:
    """Provision every queued (or corpus) song context before GPU scoring starts."""

    del cfg
    started = time.perf_counter()
    queue_paths = [
        str(item[0])
        for item in song_queue
        if isinstance(item, tuple) and item
    ]
    paths = ordered_frontier_cache_song_paths(
        queue_paths=queue_paths,
        data_root=data_root,
    )
    if not paths:
        return ExactBaseSongContextCachePrebuildSummary(total=0)

    optimistic_plan = _build_manifest_plan(
        paths,
        ref_arrays,
        persist_validated_entries=False,
    )
    if (
        not optimistic_plan.missing_paths
        and int(optimistic_plan.validated_entry_count) == 0
    ):
        return ExactBaseSongContextCachePrebuildSummary(
            total=int(optimistic_plan.total_paths),
            completed=int(optimistic_plan.hit_count),
            disk=int(optimistic_plan.hit_count),
            elapsed_ms=float((time.perf_counter() - started) * 1000.0),
        )

    # This lock coordinates startup manifest repair/build admission across deployments. The
    # content cache itself retains its narrower per-semantic-key locks, so worker builds for
    # different songs still proceed concurrently and duplicate song keys serialize safely.
    with FrontierBuildLock(_manifest_lock_dir(), label="exact_base_context_prebuild"):
        plan = _build_manifest_plan(paths, ref_arrays)
        manifest_hits = int(plan.hit_count)
        if manifest_hits > 0:
            logger.info(
                "[ExactBaseContextCache] Manifest fast-hit skipped %s/%s song(s).",
                manifest_hits,
                int(plan.total_paths),
            )
        if not plan.missing_paths:
            return ExactBaseSongContextCachePrebuildSummary(
                total=int(plan.total_paths),
                completed=manifest_hits,
                disk=manifest_hits,
                elapsed_ms=float((time.perf_counter() - started) * 1000.0),
            )

        run_summary, results = _run_missing_context_prebuild(
            list(plan.missing_paths),
            ref_arrays,
        )
        _apply_manifest_results(plan=plan, results=results)
        elapsed_ms = float((time.perf_counter() - started) * 1000.0)
        combined = ExactBaseSongContextCachePrebuildSummary(
            total=int(plan.total_paths),
            completed=int(manifest_hits + run_summary.completed),
            failures=int(run_summary.failures),
            built=int(run_summary.built),
            disk=int(manifest_hits + run_summary.disk),
            memory=int(run_summary.memory),
            elapsed_ms=elapsed_ms,
        )
        emit_profile_event(
            component="exact_base_context_cache",
            event="prebuild_with_manifest",
            metrics={
                "manifest_hits": manifest_hits,
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


__all__ = [
    "ExactBaseSongContextCacheBuildResult",
    "ExactBaseSongContextCachePrebuildSummary",
    "build_exact_base_song_context_cache_for_path",
    "run_exact_base_song_context_cache_prebuild",
]
