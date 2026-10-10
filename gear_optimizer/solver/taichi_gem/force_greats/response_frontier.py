from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT, STAT_GEM_GAIN_FEVER
from gear_optimizer.core.gem_defs import build_gem_counts
from gear_optimizer.solver.force_greats_common import response_frontier_base_components_row
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.solver.gem_search import GemWinner, SurfacePool, gem_groups, gem_winners
from gear_optimizer.stats import apply_gems, gems

from .response_cache_serde import frontier_result_from_scoring_bundle_for_stats
from .response_cache_store import gather_surface_patterns
from .response_cache_types import FgResponseFrontierScoringBundle
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
    "score_fg_base_components",
    "fg_solve_result",
    "fg_solve_results",
    "required_response_stat_keys_for_scoring_batch",
]

_ResponsePair = tuple[int, int, FgResponseFrontierResult, float, float]


def _required_response_stat_keys(
    base_components: np.ndarray,
    ft_values: np.ndarray,
    ff_values: np.ndarray,
) -> tuple[tuple[int, int], ...]:
    """Return every clipped FT/FF cell reachable by the exact candidate batch."""
    components = np.asarray(base_components, dtype=np.int32)
    ft_gems = np.asarray(ft_values, dtype=np.int32).reshape(-1)
    ff_gems = np.asarray(ff_values, dtype=np.int32).reshape(-1)
    if components.ndim != 2 or int(components.shape[1]) != 7:
        raise ValueError("response frontier base_components must have shape (N, 7)")
    if int(components.shape[0]) <= 0:
        raise ValueError("response frontier stat-key reachability requires at least one candidate")
    if ft_gems.shape != ff_gems.shape or int(ft_gems.shape[0]) <= 0:
        raise ValueError("response frontier FT/FF gem arrays must be aligned and non-empty")

    ft_stats = np.clip(
        components[:, 5, None] + (ft_gems[None, :] * int(STAT_GEM_GAIN_FEVER)),
        0,
        int(MAX_STAT),
    )
    ff_stats = np.clip(
        components[:, 6, None] + (ff_gems[None, :] * int(STAT_GEM_GAIN_FEVER)),
        0,
        int(MAX_STAT),
    )
    axis = int(MAX_STAT) + 1
    encoded = np.asarray((ft_stats * axis) + ff_stats, dtype=np.int32).reshape(-1)
    unique_encoded = np.unique(encoded)
    return tuple((int(value // axis), int(value % axis)) for value in unique_encoded)


def required_response_stat_keys_for_scoring_batch(
    *,
    base_stats_list: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    total_budget: int = GEM_BUDGET,
    base_stats7_list: list[Any] | tuple[Any, ...] | None = None,
) -> tuple[tuple[int, int], ...]:
    """Return the exact response-cache cells addressable by a scoring batch.

    This is a reachability projection of the canonical candidate inputs and the complete
    ``ftff_combo_arrays`` search space. It removes no candidate and performs no score-based
    pruning; cells outside this set cannot be indexed by the corresponding exact solve.
    """
    stats_inputs = tuple(dict(stats) for stats in (base_stats_list or []))
    if not stats_inputs:
        raise ValueError("response frontier stat-key reachability requires at least one candidate")
    if base_stats7_list is None:
        base_stats7_inputs: tuple[Any, ...] = (None,) * len(stats_inputs)
    else:
        base_stats7_inputs = tuple(base_stats7_list)
        if len(base_stats7_inputs) != len(stats_inputs):
            raise ValueError(
                "response frontier base_stats7_list must align 1:1 with base_stats_list "
                f"({len(base_stats7_inputs)} != {len(stats_inputs)})"
            )
    base_components = np.asarray(
        [
            response_frontier_base_components_row(
                base_stats,
                base_stats7,
                primary_color="",
                secondary_color="",
            )
            for base_stats, base_stats7 in zip(stats_inputs, base_stats7_inputs, strict=True)
        ],
        dtype=np.int32,
    )
    ft_values, ff_values, _remaining = ftff_combo_arrays(int(total_budget))
    return _required_response_stat_keys(base_components, ft_values, ff_values)


def _solve_result_from_row(
    *,
    base_stats: dict[str, Any],
    selected_color: str,
    pair: _ResponsePair,
    row: tuple[int, int, int, int, int, int, int, int, int, int, int],
    surface: FgResponseSurface,
) -> FgResponseFrontierSolveResult:
    ft, ff, frontier, raw_fill, real_fever_time = pair
    inner = FgResponseInnerResult(
        best_score=int(row[0]),
        surface_index=int(row[1]),
        g_pp=int(row[2]),
        g_cm=int(row[3]),
        g_fm=int(row[4]),
        g_ov=int(row[5]),
        final_pp=int(row[6]),
        final_cm=int(row[7]),
        final_fm=int(row[8]),
        final_primary=int(row[9]),
        final_secondary=int(row[10]),
    )
    final_stats = apply_gems(
        base_stats,
        gems(pp=inner.g_pp, cm=inner.g_cm, fm=inner.g_fm, ft=ft, ff=ff, element=inner.g_ov),
        selected_color,
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
        seconds=0.0,
        raw_fever_fill=float(raw_fill),
        real_fever_time=float(real_fever_time),
    )


def _scoring_pool(bundle: FgResponseFrontierScoringBundle, frontiers: np.ndarray) -> SurfacePool:
    """The bundle's surfaces for `frontiers`: an in-memory (session-pruned) pool whole; else the frontiers' rows
    gathered from the bundle's tables, adjacent ranges merged and each frontier's offset remapped into the gathered
    rows."""
    if bundle.surface_pattern_ids.shape[0]:
        return SurfacePool(
            bundle.frontier_offsets,
            bundle.frontier_lengths,
            bundle.surface_pattern_ids,
            bundle.surface_pattern_words,
            bundle.surface_counts,
            bundle.surface_pattern_head_coeffs,
        )
    used = np.unique(frontiers)
    segments = sorted({(int(bundle.frontier_offsets[f]), int(bundle.frontier_lengths[f])) for f in used})
    ranges: list[list[int]] = []
    gathered: dict[tuple[int, int], int] = {}
    cursor = 0
    for start, length in segments:
        if ranges and ranges[-1][0] + ranges[-1][1] == start:
            ranges[-1][1] += length
        else:
            ranges.append([start, length])
        gathered[(start, length)] = cursor
        cursor += length
    offsets = np.full(bundle.frontier_offsets.shape, -1, dtype=np.int32)
    for f in used:
        offsets[f] = gathered[(int(bundle.frontier_offsets[f]), int(bundle.frontier_lengths[f]))]
    pattern_ids, counts, pattern_words, head_coeffs = gather_surface_patterns(
        bundle.surface_rows, bundle.surface_patterns, tuple((start, length) for start, length in ranges)
    )
    return SurfacePool(offsets, bundle.frontier_lengths, pattern_ids, pattern_words, counts, head_coeffs)


def score_fg_base_components(
    *,
    base_components: np.ndarray,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
    total_budget: int = GEM_BUDGET,
    floors: np.ndarray | None = None,
) -> dict[tuple[int, ...], GemWinner]:
    """The FG score row of each distinct 7-vector of pre-gem totals (PP, CM, FM, primary, secondary, FT, FF), keyed by
    it (CPU only); equal 7-vectors have equal FG results, so each is scored once. ``selected_color`` is the song's
    selected element; every other input is song-level (the scoring bundle). With `floors` (a score per row) a row is
    exact only when it reaches its floor (the lowest of a 7-vector's floors); below it, its score is only known to be
    lower."""
    floor_of: dict[tuple[int, ...], int] = {}
    for idx, row in enumerate(np.asarray(base_components, dtype=np.int32).tolist()):
        key = tuple(row)
        floor = -1 if floors is None else int(floors[idx])
        floor_of[key] = min(floor_of.get(key, floor), floor)
    if not floor_of:
        return {}
    inputs = song.fg_inputs
    groups = gem_groups(
        np.asarray(list(floor_of), dtype=np.int32),
        primary_color=inputs.primary_color,
        secondary_color=inputs.secondary_color,
        frontier_idx_by_stat=scoring_bundle.frontier_idx_by_stat,
        total_notes=int(inputs.total_notes),
        total_budget=total_budget,
    )
    winners = gem_winners(
        groups,
        _scoring_pool(scoring_bundle, groups.frontiers),
        colors=(inputs.primary_color, inputs.secondary_color, selected_color),
        curves=curves,
        floors=None if floors is None else np.asarray(list(floor_of.values())),
    )
    return dict(zip(floor_of, winners, strict=True))


def fg_solve_result(
    *,
    score_row: GemWinner,
    base_stats: dict[str, Any],
    selected_color: str,
    song: TimedSong,
    curves: StatCurves,
    scoring_bundle: FgResponseFrontierScoringBundle,
    frontier_by_stat_key: dict[tuple[int, int], FgResponseFrontierResult],
) -> FgResponseFrontierSolveResult:
    """A loadout's FG solve result from its score row and its pre-gem stats (all 10). The frontier of the winning stat
    key comes from the scoring bundle, once per key for the callers sharing `frontier_by_stat_key`."""
    stat_key = (score_row.ft_stat, score_row.ff_stat)
    frontier = frontier_by_stat_key.get(stat_key)
    if frontier is None:
        frontier = frontier_result_from_scoring_bundle_for_stats(
            song, curves, scoring_bundle, ft_stat=score_row.ft_stat, ff_stat=score_row.ff_stat
        )
        frontier_by_stat_key[stat_key] = frontier
    pair: _ResponsePair = (
        score_row.ft,
        score_row.ff,
        frontier,
        float(scoring_bundle.raw_fill_by_ff[score_row.ff_stat]),
        float(scoring_bundle.real_time_by_ft[score_row.ft_stat]),
    )
    return _solve_result_from_row(
        base_stats=base_stats,
        selected_color=str(selected_color or ""),
        pair=pair,
        row=score_row.inner_row,
        surface=FgResponseSurface(*score_row.surface),
    )


def fg_solve_results(
    stats_rows,
    *,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
    total_budget: int = GEM_BUDGET,
) -> list[FgResponseFrontierSolveResult]:
    """Each stats row's FG solve result: rows of pre-gem stats re-solve the gems within total_budget; with
    total_budget=0 the rows are allocated stats and only the FG plan is solved."""
    song_inputs = song.fg_inputs
    totals = [
        response_frontier_base_components_row(
            stats, None, primary_color=song_inputs.primary_color, secondary_color=song_inputs.secondary_color
        )
        for stats in stats_rows
    ]
    rows = score_fg_base_components(
        base_components=np.asarray(totals, dtype=np.int32), song=song, curves=curves, selected_color=selected_color,
        scoring_bundle=scoring_bundle, total_budget=total_budget,
    )
    frontiers: dict[tuple[int, int], FgResponseFrontierResult] = {}
    return [
        fg_solve_result(score_row=rows[key], base_stats=dict(stats), selected_color=selected_color, song=song,
                        curves=curves, scoring_bundle=scoring_bundle, frontier_by_stat_key=frontiers)
        for key, stats in zip(totals, stats_rows, strict=True)
    ]
