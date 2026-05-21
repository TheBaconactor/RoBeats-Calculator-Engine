from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.core.utils import safe_int

from .prefix_frontier_cache import (
    fg_prefix_frontier_cache_dir,
    fg_prefix_frontier_base_cache_key,
    fg_prefix_frontier_cache_key,
    fg_prefix_frontier_cache_path,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FgPrefixFrontierPrebuildSummary:
    section_counts: tuple[int, ...]
    total: int
    disk: int
    built: int
    elapsed_ms: float


_FG_PREFIX_FRONTIER_PREBUILD_DONE: set[tuple] = set()


def _fg_song_timing_inputs(calc_song: dict) -> tuple[np.ndarray, np.ndarray | None, int, float]:
    song_data = calc_song.get("song_data", {}) or {}
    metadata = calc_song.get("metadata", {}) or {}
    timestamps_obj = song_data.get("fg_timestamps", song_data.get("timestamps"))
    timestamps = np.ascontiguousarray(np.asarray(timestamps_obj, dtype=np.float32).reshape(-1))
    if timestamps.size <= 0:
        raise ValueError("FG prefix frontier prebuild requires song timestamps")
    great_obj = song_data.get("fg_great_candidate_timestamps")
    great_candidates = None
    if great_obj is not None:
        great_candidates = np.ascontiguousarray(np.asarray(great_obj, dtype=np.float32).reshape(-1))
        if int(great_candidates.shape[0]) != int(timestamps.shape[0]):
            raise ValueError("FG prefix frontier prebuild great-candidate timestamp length mismatch")
    long_notes = safe_int(metadata.get("Long Notes", 0), 0)
    last_note_time = float(metadata.get("Last Note Time", 0) or 0.0)
    return timestamps, great_candidates, int(long_notes), float(last_note_time)


def resolve_fg_prefix_frontier_section_counts(
    calc_song: dict,
    ref_arrays: dict,
    *,
    stat_max: int = TOTAL_ROWS,
) -> tuple[int, ...]:
    from gear_optimizer.solver.scoring.stats_scoring import fg_baseline_params
    from . import fields as fg_fields

    max_stat = max(0, min(int(stat_max), int(TOTAL_ROWS)))
    observed: set[int] = set()
    stats = {"Fever Time": 0, "Fever Fill Rate": 0}
    for ft_idx in range(max_stat + 1):
        stats["Fever Time"] = int(ft_idx)
        for ff_idx in range(max_stat + 1):
            stats["Fever Fill Rate"] = int(ff_idx)
            n_sections, _non_fever_base = fg_baseline_params(stats, calc_song, ref_arrays, prefer_grid=True)
            n = int(n_sections)
            if n > int(fg_fields.FG_MAX_SECTIONS):
                raise RuntimeError(
                    f"FG prefix frontier needs {n} sections, but compiled capacity is {fg_fields.FG_MAX_SECTIONS}"
                )
            if n > 0:
                observed.add(n)
    if not observed:
        return ()
    return tuple(range(1, max(observed) + 1))


def _missing_cells_for_section(
    *,
    base_key: tuple,
    stat_max: int,
) -> list[tuple[int, int]]:
    missing: list[tuple[int, int]] = []
    for ft_idx in range(int(stat_max) + 1):
        for ff_idx in range(int(stat_max) + 1):
            cache_key = fg_prefix_frontier_cache_key(base_key, ft_idx=int(ft_idx), ff_idx=int(ff_idx))
            if not fg_prefix_frontier_cache_path(cache_key).exists():
                missing.append((int(ft_idx), int(ff_idx)))
    return missing


def _default_solve_tasks_fn() -> Callable[..., Any]:
    from .api import solve_force_greats_finder_gpu_tasks

    return solve_force_greats_finder_gpu_tasks


def _submit_prebuild_chunk(
    *,
    gpu_client: Any,
    solve_tasks_fn: Callable[..., Any] | None,
    genome_stats_arr: np.ndarray,
    timestamps: np.ndarray,
    great_candidates: np.ndarray | None,
    long_notes: int,
    last_note_time: float,
    task: dict[str, Any],
    n_sections: int,
    ref_arrays: dict,
    total_budget: int,
    gem_scale_fever: int,
    song_slot: int,
) -> None:
    flags = {
        "is_p_ft": 0,
        "is_s_ft": 0,
        "is_p_ff": 0,
        "is_s_ff": 0,
        "is_p_pp": 0,
        "is_s_pp": 0,
        "is_p_cm": 0,
        "is_s_cm": 0,
        "is_p_fm": 0,
        "is_s_fm": 0,
        "is_p_ov": 0,
        "is_s_ov": 0,
    }
    kwargs = dict(
        fg_tasks=[task],
        n_sections=int(n_sections),
        ref_arrays=ref_arrays,
        total_budget=int(total_budget),
        gem_scale_fever=int(gem_scale_fever),
        pair_caps_grid=None,
        pair_caps_from_timeline=False,
        song_slot=int(song_slot),
        return_raw=True,
        accumulate_global=True,
        upload_genome_stats=True,
        prebuild_only=True,
        **flags,
    )
    if gpu_client is not None:
        placeholder_counts = [tuple([0] * int(n_sections))]
        placeholder_pairs = [(0, 0)]
        gpu_client.submit_solve_force_greats_finder(
            genome_stats_arr,
            timestamps,
            great_candidates,
            int(long_notes),
            float(last_note_time),
            placeholder_counts,
            placeholder_pairs,
            **kwargs,
        ).future.result()
        return
    fn = solve_tasks_fn or _default_solve_tasks_fn()
    fn(
        genome_stats_arr,
        timestamps,
        great_candidates,
        int(long_notes),
        float(last_note_time),
        **kwargs,
    )


def prebuild_fg_prefix_frontier_cache(
    calc_song: dict,
    ref_arrays: dict,
    *,
    gpu_client: Any = None,
    song_slot: int = 0,
    gem_scale_fever: int = 3,
    total_budget: int = 90,
    n_sections_values: tuple[int, ...] | list[int] | None = None,
    stat_max: int = TOTAL_ROWS,
    chunk_size: int | None = None,
    solve_tasks_fn: Callable[..., Any] | None = None,
) -> FgPrefixFrontierPrebuildSummary:
    from .. import fields as gem_fields

    if not isinstance(calc_song, dict) or not isinstance(ref_arrays, dict):
        raise TypeError("FG prefix frontier prebuild requires calc_song and ref_arrays dicts")
    t0 = time.perf_counter()
    stat_max_i = max(0, min(int(stat_max), int(TOTAL_ROWS)))
    timestamps, great_candidates, long_notes, last_note_time = _fg_song_timing_inputs(calc_song)
    if n_sections_values is None:
        section_counts = resolve_fg_prefix_frontier_section_counts(calc_song, ref_arrays, stat_max=stat_max_i)
    else:
        section_counts = tuple(sorted({int(v) for v in n_sections_values if int(v) > 0}))
    if not section_counts:
        return FgPrefixFrontierPrebuildSummary(
            section_counts=(),
            total=0,
            disk=0,
            built=0,
            elapsed_ms=float((time.perf_counter() - t0) * 1000.0),
        )
    completed_key = (
        tuple(section_counts),
        fg_prefix_frontier_base_cache_key(
            timestamps=timestamps,
            great_candidate_timestamps=timestamps if great_candidates is None else great_candidates,
            total_notes=int(timestamps.shape[0]),
            long_notes=int(long_notes),
            n_sections=0,
            ref_arrays=ref_arrays,
        ),
        int(stat_max_i),
        str(fg_prefix_frontier_cache_dir()),
    )
    if completed_key in _FG_PREFIX_FRONTIER_PREBUILD_DONE:
        total = int(len(section_counts)) * int(stat_max_i + 1) * int(stat_max_i + 1)
        return FgPrefixFrontierPrebuildSummary(
            section_counts=section_counts,
            total=total,
            disk=total,
            built=0,
            elapsed_ms=float((time.perf_counter() - t0) * 1000.0),
        )

    max_genomes = int(getattr(gem_fields, "MAX_GENOMES", 4096) or 4096)
    chunk_n = max(1, min(int(chunk_size or max_genomes), int(max_genomes)))
    total_cells = 0
    disk_cells = 0
    built_cells = 0
    for n_sections in section_counts:
        base_key = fg_prefix_frontier_base_cache_key(
            timestamps=timestamps,
            great_candidate_timestamps=timestamps if great_candidates is None else great_candidates,
            total_notes=int(timestamps.shape[0]),
            long_notes=int(long_notes),
            n_sections=int(n_sections),
            ref_arrays=ref_arrays,
        )
        cells_total = int(stat_max_i + 1) * int(stat_max_i + 1)
        missing = _missing_cells_for_section(base_key=base_key, stat_max=stat_max_i)
        total_cells += int(cells_total)
        disk_cells += int(cells_total - len(missing))
        for offset in range(0, len(missing), chunk_n):
            cells = missing[offset : offset + chunk_n]
            if not cells:
                continue
            stats_arr = np.zeros((len(cells), 7), dtype=np.int32)
            for row_idx, (ft_idx, ff_idx) in enumerate(cells):
                stats_arr[row_idx, 5] = int(ft_idx)
                stats_arr[row_idx, 6] = int(ff_idx)
            task = {
                "counts_list": None,
                "counts_max_fp": {
                    "mode": "gpu",
                    "n_sections": int(n_sections),
                    "song_slot": int(song_slot),
                    "gem_scale_fever": int(gem_scale_fever),
                },
                "ftff_pairs": np.asarray([(0, 0)], dtype=np.int32),
                "base_cfg_offset": 0,
            }
            _submit_prebuild_chunk(
                gpu_client=gpu_client,
                solve_tasks_fn=solve_tasks_fn,
                genome_stats_arr=stats_arr,
                timestamps=timestamps,
                great_candidates=great_candidates,
                long_notes=int(long_notes),
                last_note_time=float(last_note_time),
                task=task,
                n_sections=int(n_sections),
                ref_arrays=ref_arrays,
                total_budget=int(total_budget),
                gem_scale_fever=int(gem_scale_fever),
                song_slot=int(song_slot),
            )
            built_cells += int(len(cells))
    _FG_PREFIX_FRONTIER_PREBUILD_DONE.add(completed_key)
    return FgPrefixFrontierPrebuildSummary(
        section_counts=section_counts,
        total=int(total_cells),
        disk=int(disk_cells),
        built=int(built_cells),
        elapsed_ms=float((time.perf_counter() - t0) * 1000.0),
    )
