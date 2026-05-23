from __future__ import annotations

import time
from math import ceil
from typing import Any

import numpy as np

from gear_optimizer.core.constants import (
    FEVER_FILL_BASE_RATE,
    FEVER_TIME_OFFSET,
    FEVER_TIME_SCALE,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)
from gear_optimizer.core.gem_defs import build_gem_counts
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.solver.scoring.fg_policy import extract_fg_song_inputs
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats

from .response_builder import (
    build_force_greats_response_frontier,
    reconstruct_force_greats_response_counts,
    response_surface_dominates,
)
from .response_inner import (
    _optimize_response_surfaces_gpu,
    optimize_response_frontier_inner_exact,
    optimize_response_frontier_inner_exact_gpu,
    score_response_surface_exact,
)
from .response_types import (
    FgResponseFrontierResult,
    FgResponseFrontierSolveResult,
    FgResponseInnerResult,
    FgResponseSurface,
)

__all__ = [
    "FgResponseFrontierResult",
    "FgResponseFrontierSolveResult",
    "FgResponseInnerResult",
    "FgResponseSurface",
    "build_force_greats_response_frontier",
    "optimize_response_frontier_inner_exact",
    "optimize_response_frontier_inner_exact_gpu",
    "reconstruct_force_greats_response_counts",
    "response_surface_dominates",
    "score_response_surface_exact",
    "solve_force_greats_response_frontier_batch_gpu",
    "solve_force_greats_response_frontier_exact",
    "solve_force_greats_response_frontier_for_ftff",
]


def _geometry_for_ftff(
    *,
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    stats_after_ftff: dict[str, Any],
    song_inputs: Any | None = None,
):
    if song_inputs is None:
        song_inputs = extract_fg_song_inputs(calc_song)
    ff_stat = max(0, min(TOTAL_ROWS, int(stats_after_ftff.get("Fever Fill Rate", 0) or 0)))
    ft_stat = max(0, min(TOTAL_ROWS, int(stats_after_ftff.get("Fever Time", 0) or 0)))
    raw_fill = (
        max(0.0, float(song_inputs.total_notes - int(song_inputs.long_notes)) * float(FEVER_FILL_BASE_RATE))
        * float(np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32)[ff_stat])
    )
    real_fever_time = (
        float(song_inputs.last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    ) * float(np.asarray(ref_arrays["Fever Time"], dtype=np.float32)[ft_stat])
    return song_inputs, float(raw_fill), int(ceil(raw_fill)), float(real_fever_time)


def solve_force_greats_response_frontier_for_ftff(
    *,
    base_stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    ft: int,
    ff: int,
    total_budget: int = TOTAL_GEM_BUDGET,
) -> FgResponseFrontierSolveResult:
    started = time.perf_counter()
    if int(ft) < 0 or int(ff) < 0 or int(ft) + int(ff) > int(total_budget):
        raise ValueError("FT/FF gem pair is outside the total gem budget")
    stats_after_ftff = apply_gems_to_base_stats(base_stats, selected_color, int(ft), int(ff), 0, 0, 0, 0)
    song_inputs, raw_fill, non_fever_base, real_fever_time = _geometry_for_ftff(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        stats_after_ftff=stats_after_ftff,
        song_inputs=None,
    )
    frontier = build_force_greats_response_frontier(
        timestamps=song_inputs.timestamps,
        great_candidate_timestamps=song_inputs.great_candidates,
        raw_fever_fill=float(raw_fill),
        non_fever_base=int(non_fever_base),
        real_fever_time=float(real_fever_time),
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )
    inner = optimize_response_frontier_inner_exact_gpu(
        frontier.first_frontier,
        total_notes=int(song_inputs.total_notes),
        residual_budget=int(total_budget) - int(ft) - int(ff),
        stats_after_ftff=stats_after_ftff,
        primary_color=str(song_inputs.primary_color or ""),
        secondary_color=str(song_inputs.secondary_color or ""),
        selected_color=str(selected_color or ""),
        ref_arrays=ref_arrays,
    )
    forced_counts = reconstruct_force_greats_response_counts(
        frontier=frontier,
        target_surface=frontier.first_frontier[int(inner.surface_index)],
        timestamps=song_inputs.timestamps,
        great_candidate_timestamps=song_inputs.great_candidates,
        raw_fever_fill=float(raw_fill),
        real_fever_time=float(real_fever_time),
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )
    final_stats = apply_gems_to_base_stats(
        base_stats,
        selected_color,
        int(ft),
        int(ff),
        int(inner.g_pp),
        int(inner.g_cm),
        int(inner.g_fm),
        int(inner.g_ov),
    )
    return FgResponseFrontierSolveResult(
        best_score=int(inner.best_score),
        ft=int(ft),
        ff=int(ff),
        gem_counts=build_gem_counts(int(inner.g_pp), int(inner.g_cm), int(inner.g_fm), int(inner.g_ov)),
        stats=final_stats,
        surface=frontier.first_frontier[int(inner.surface_index)],
        frontier=frontier,
        inner=inner,
        seconds=float(time.perf_counter() - started),
        forced_counts=tuple(int(v) for v in forced_counts),
    )


def solve_force_greats_response_frontier_exact(
    *,
    base_stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    total_budget: int = TOTAL_GEM_BUDGET,
) -> FgResponseFrontierSolveResult:
    return solve_force_greats_response_frontier_batch_gpu(
        base_stats=base_stats,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        selected_color=selected_color,
        total_budget=int(total_budget),
    )


def solve_force_greats_response_frontier_batch_gpu(
    *,
    base_stats: dict[str, Any],
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    selected_color: str,
    total_budget: int = TOTAL_GEM_BUDGET,
) -> FgResponseFrontierSolveResult:
    started = time.perf_counter()
    ft_values, ff_values, _remaining = ftff_combo_arrays(int(total_budget))
    if int(ft_values.shape[0]) <= 0:
        raise ValueError("response frontier exact solve found no FT/FF pairs")

    song_inputs = extract_fg_song_inputs(calc_song)
    groups: list[tuple[int, dict[str, Any], tuple[FgResponseSurface, ...]]] = []
    pair_records: list[tuple[int, int, dict[str, Any], FgResponseFrontierResult, float, float]] = []
    frontier_cache: dict[tuple[float, int, float, bool], FgResponseFrontierResult] = {}
    for ft, ff in zip(ft_values, ff_values, strict=True):
        stats_after_ftff = apply_gems_to_base_stats(base_stats, selected_color, int(ft), int(ff), 0, 0, 0, 0)
        _song_inputs, raw_fill, non_fever_base, real_fever_time = _geometry_for_ftff(
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            stats_after_ftff=stats_after_ftff,
            song_inputs=song_inputs,
        )
        geometry_key = (
            float(raw_fill),
            int(non_fever_base),
            float(real_fever_time),
            bool(song_inputs.use_forced_great_timing),
        )
        frontier = frontier_cache.get(geometry_key)
        if frontier is None:
            frontier = build_force_greats_response_frontier(
                timestamps=song_inputs.timestamps,
                great_candidate_timestamps=song_inputs.great_candidates,
                raw_fever_fill=float(raw_fill),
                non_fever_base=int(non_fever_base),
                real_fever_time=float(real_fever_time),
                use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
            )
            frontier_cache[geometry_key] = frontier
        groups.append((int(total_budget) - int(ft) - int(ff), stats_after_ftff, frontier.first_frontier))
        pair_records.append((int(ft), int(ff), stats_after_ftff, frontier, float(raw_fill), float(real_fever_time)))

    inner_rows, _surface_rows = _optimize_response_surfaces_gpu(
        groups,
        total_notes=int(song_inputs.total_notes),
        primary_color=str(song_inputs.primary_color or ""),
        secondary_color=str(song_inputs.secondary_color or ""),
        selected_color=str(selected_color or ""),
        ref_arrays=ref_arrays,
    )
    best_idx = -1
    best_row: tuple[int, int, int, int, int, int, int, int, int, int, int] | None = None
    for idx, row in enumerate(inner_rows):
        if best_row is None or int(row[0]) > int(best_row[0]):
            best_row = row
            best_idx = int(idx)
    if best_row is None or best_idx < 0:
        raise ValueError("response frontier exact GPU batch produced no pair result")

    ft, ff, _stats_after_ftff, frontier, raw_fill, real_fever_time = pair_records[best_idx]
    inner = FgResponseInnerResult(
        best_score=int(best_row[0]),
        surface_index=int(best_row[1]),
        g_pp=int(best_row[2]),
        g_cm=int(best_row[3]),
        g_fm=int(best_row[4]),
        g_ov=int(best_row[5]),
        final_pp=int(best_row[6]),
        final_cm=int(best_row[7]),
        final_fm=int(best_row[8]),
        final_primary=int(best_row[9]),
        final_secondary=int(best_row[10]),
    )
    surface = frontier.first_frontier[int(inner.surface_index)]
    forced_counts = reconstruct_force_greats_response_counts(
        frontier=frontier,
        target_surface=surface,
        timestamps=song_inputs.timestamps,
        great_candidate_timestamps=song_inputs.great_candidates,
        raw_fever_fill=float(raw_fill),
        real_fever_time=float(real_fever_time),
        use_forced_great_timing=bool(song_inputs.use_forced_great_timing),
    )
    final_stats = apply_gems_to_base_stats(
        base_stats,
        selected_color,
        int(ft),
        int(ff),
        int(inner.g_pp),
        int(inner.g_cm),
        int(inner.g_fm),
        int(inner.g_ov),
    )
    return FgResponseFrontierSolveResult(
        best_score=int(inner.best_score),
        ft=int(ft),
        ff=int(ff),
        gem_counts=build_gem_counts(int(inner.g_pp), int(inner.g_cm), int(inner.g_fm), int(inner.g_ov)),
        stats=final_stats,
        surface=surface,
        frontier=frontier,
        inner=inner,
        seconds=float(time.perf_counter() - started),
        forced_counts=tuple(int(v) for v in forced_counts),
    )
