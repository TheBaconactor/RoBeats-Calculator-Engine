from __future__ import annotations

import time
from typing import Any

from gear_optimizer.core.constants import (
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
from .response_cache import build_or_load_response_frontier_payload
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

_ResponsePair = tuple[int, int, int, dict[str, Any], FgResponseFrontierResult, float, float]


def _ftff_stat_key(stats_after_ftff: dict[str, Any]) -> tuple[int, int]:
    ff_stat = max(0, min(TOTAL_ROWS, int(stats_after_ftff.get("Fever Fill Rate", 0) or 0)))
    ft_stat = max(0, min(TOTAL_ROWS, int(stats_after_ftff.get("Fever Time", 0) or 0)))
    return int(ft_stat), int(ff_stat)


def _score_elements(stats: dict[str, Any], primary_color: str, secondary_color: str) -> tuple[int, int]:
    return (
        int(stats.get(str(primary_color or ""), 0) or 0),
        int(stats.get(str(secondary_color or ""), 0) or 0),
    )


def _response_pair_dominates(
    a: _ResponsePair,
    b: _ResponsePair,
    *,
    primary_color: str,
    secondary_color: str,
) -> bool:
    if a[4] is not b[4]:
        return False
    if int(a[2]) < int(b[2]):
        return False
    a_primary, a_secondary = _score_elements(a[3], primary_color, secondary_color)
    b_primary, b_secondary = _score_elements(b[3], primary_color, secondary_color)
    return int(a_primary) >= int(b_primary) and int(a_secondary) >= int(b_secondary)


def _prune_dominated_ftff_response_pairs(
    pairs: list[_ResponsePair],
    *,
    primary_color: str,
    secondary_color: str,
) -> list[_ResponsePair]:
    by_frontier: dict[int, list[_ResponsePair]] = {}
    for pair in pairs:
        by_frontier.setdefault(id(pair[4]), []).append(pair)

    out: list[_ResponsePair] = []
    for bucket in by_frontier.values():
        kept: list[_ResponsePair] = []
        for pair in bucket:
            if any(
                _response_pair_dominates(
                    other,
                    pair,
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                )
                for other in kept
            ):
                continue
            kept = [
                other
                for other in kept
                if not _response_pair_dominates(
                    pair,
                    other,
                    primary_color=primary_color,
                    secondary_color=secondary_color,
                )
            ]
            kept.append(pair)
        out.extend(kept)
    return out


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
    song_inputs = extract_fg_song_inputs(calc_song)
    ft_stat, ff_stat = _ftff_stat_key(stats_after_ftff)
    payload = build_or_load_response_frontier_payload(
        calc_song,
        ref_arrays,
        stat_keys=((ft_stat, ff_stat),),
    ).payload
    raw_fill, _non_fever_base, real_fever_time = payload.geometry_for_stats(ft_stat=ft_stat, ff_stat=ff_stat)
    frontier = payload.frontier_for_stats(ft_stat=ft_stat, ff_stat=ff_stat)
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
    pair_inputs: list[tuple[int, int, dict[str, Any], tuple[int, int]]] = []
    stat_keys: list[tuple[int, int]] = []
    for ft, ff in zip(ft_values, ff_values, strict=True):
        stats_after_ftff = apply_gems_to_base_stats(base_stats, selected_color, int(ft), int(ff), 0, 0, 0, 0)
        key = _ftff_stat_key(stats_after_ftff)
        pair_inputs.append((int(ft), int(ff), stats_after_ftff, key))
        stat_keys.append(key)
    payload = build_or_load_response_frontier_payload(calc_song, ref_arrays, stat_keys=stat_keys).payload
    pair_records: list[_ResponsePair] = []
    for ft, ff, stats_after_ftff, (ft_stat, ff_stat) in pair_inputs:
        raw_fill, _non_fever_base, real_fever_time = payload.geometry_for_stats(ft_stat=ft_stat, ff_stat=ff_stat)
        frontier = payload.frontier_for_stats(ft_stat=ft_stat, ff_stat=ff_stat)
        residual = int(total_budget) - int(ft) - int(ff)
        pair_records.append((int(ft), int(ff), int(residual), stats_after_ftff, frontier, float(raw_fill), float(real_fever_time)))

    pair_records = _prune_dominated_ftff_response_pairs(
        pair_records,
        primary_color=str(song_inputs.primary_color or ""),
        secondary_color=str(song_inputs.secondary_color or ""),
    )
    groups = [(int(residual), stats_after_ftff, frontier.first_frontier) for _ft, _ff, residual, stats_after_ftff, frontier, _raw_fill, _real_fever_time in pair_records]

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

    ft, ff, _residual, _stats_after_ftff, frontier, raw_fill, real_fever_time = pair_records[best_idx]
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
