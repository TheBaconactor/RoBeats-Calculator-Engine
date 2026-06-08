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
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.solver.frontier_cache_manifest import (
    apply_manifest_results as _shared_apply_manifest_results,
    build_manifest_plan as _shared_build_manifest_plan,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys
from gear_optimizer.solver.timeline_frontier_cache_prebuild import ordered_frontier_cache_song_paths

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
def _prebuild_cpu_count() -> int:
    return max(1, int(os.cpu_count() or 1))


def _resolve_prebuild_reducer_threads() -> int:
    return _prebuild_cpu_count()


def _resolve_prebuild_worker_count() -> int:
    return 3 if _prebuild_cpu_count() >= 8 else 2 if _prebuild_cpu_count() >= 4 else 1


_PREBUILD_WORKERS = _resolve_prebuild_worker_count()
_MANIFEST_FILE_NAME = "fg_response_manifest_v1.json"


def _init_prebuild_worker(
    ref_arrays: dict,
    stat_keys: tuple[tuple[int, int], ...],
    reducer_threads: int = 1,
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_reducer

    global _PREBUILD_WORKER_REF_ARRAYS, _PREBUILD_WORKER_STAT_KEYS
    _PREBUILD_WORKER_REF_ARRAYS = dict(ref_arrays or {})
    _PREBUILD_WORKER_STAT_KEYS = tuple(stat_keys or ())
    response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(max(1, int(reducer_threads)))


def _build_fg_response_frontier_cache_for_path_shared(song_path_text: str) -> FgResponseFrontierCacheBuildResult:
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
    )


def _apply_manifest_results(*, plan, results: Iterable[object]) -> int:
    return _shared_apply_manifest_results(
        plan=plan,
        manifest_path=_manifest_path(),
        cache_version=_cache_version(),
        version_field="cache_version",
        results=results,
    )


def _build_prebuild_executor(
    *,
    worker_count: int,
    ref_arrays: dict,
    stat_keys: tuple[tuple[int, int], ...],
) -> concurrent.futures.ProcessPoolExecutor:
    reducer_threads = _resolve_prebuild_reducer_threads()
    return concurrent.futures.ProcessPoolExecutor(
        max_workers=max(1, int(worker_count)),
        initializer=_init_prebuild_worker,
        initargs=(dict(ref_arrays or {}), tuple(stat_keys or ()), int(reducer_threads)),
    )


def _dedupe_paths_by_response_bundle_key(paths: Iterable[str], ref_arrays: dict) -> tuple[list[str], dict[str, tuple[str, ...]]]:
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import fg_response_frontier_bundle_cache_key
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    representatives: list[str] = []
    duplicates: dict[str, list[str]] = {}
    representative_by_key: dict[tuple, str] = {}
    for path_text in paths:
        path = str(path_text)
        calc_song = get_base_calc_song(path, {})
        apply_timing_envelope(calc_song)
        key = fg_response_frontier_bundle_cache_key(calc_song, ref_arrays)
        representative = representative_by_key.get(key)
        if representative is None:
            representative_by_key[key] = path
            representatives.append(path)
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
    result = build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=stat_keys)
    return FgResponseFrontierCacheBuildResult(
        path=str(song_path),
        source=str(result.cache_source),
        build_ms=float(result.elapsed_ms),
        cache_file=str(result.disk_path),
    )


def _fg_response_frontier_prebuild_priority(path_text: str) -> tuple[int, str]:
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.timing_envelope import apply_timing_envelope

    calc_song = get_base_calc_song(str(path_text), {})
    apply_timing_envelope(calc_song)
    timestamps = calc_song.get("song_data", {}).get("timestamps", ())
    return (-int(len(timestamps) if timestamps is not None else 0), str(path_text).lower())


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
    worker_count = _PREBUILD_WORKERS
    build_paths, duplicate_paths_by_representative = _dedupe_paths_by_response_bundle_key(paths, ref_arrays)
    if len(build_paths) == 1:
        path = str(build_paths[0])
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
    with _build_prebuild_executor(worker_count=worker_count, ref_arrays=ref_arrays, stat_keys=stat_keys) as executor:
        futures = {executor.submit(_build_fg_response_frontier_cache_for_path_shared, path): path for path in build_paths}
        for future in concurrent.futures.as_completed(futures):
            path = futures[future]
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
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache import cleanup_fg_response_frontier_cache_temp_files

    started = time.perf_counter()
    stat_keys = all_response_stat_keys()
    queue_paths = [str(item[0]) for item in song_queue if isinstance(item, tuple) and item]
    paths = ordered_frontier_cache_song_paths(queue_paths=queue_paths, data_root=data_root)
    if not paths:
        return FgResponseFrontierCachePrebuildSummary(total=0)

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

    missing_paths = sorted(manifest_plan.missing_paths, key=_fg_response_frontier_prebuild_priority)
    run_summary, results = _run_missing_fg_prebuild(list(missing_paths), ref_arrays, stat_keys)
    _apply_manifest_results(plan=manifest_plan, results=results)
    elapsed_ms = float((time.perf_counter() - started) * 1000.0)
    return FgResponseFrontierCachePrebuildSummary(
        total=int(manifest_plan.total_paths),
        completed=int(manifest_hits + run_summary.completed),
        failures=int(run_summary.failures),
        built=int(run_summary.built),
        disk=int(manifest_hits + run_summary.disk),
        memory=int(run_summary.memory),
        elapsed_ms=elapsed_ms,
    )
