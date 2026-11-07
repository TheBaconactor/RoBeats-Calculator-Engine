"""The FG score of loadouts over a song's scoring bundle: the exact gem search, and its winners as solve results."""

from __future__ import annotations

from typing import Any

import numpy as np

from gear_optimizer.core.gem_defs import build_gem_counts
from gear_optimizer.frontier.fg_cache_types import FgResponseFrontierScoringBundle
from gear_optimizer.frontier.types import FgResponseFrontierSolveResult, FgResponseSurface
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT, STAT_GEM_GAIN_FEVER
from gear_optimizer.solver.base_stats import loadout_totals
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.solver.gem_search import GemMemo, GemWinner, gem_groups, gem_winners
from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.stats import apply_gems, gems


def required_response_stat_keys(base_stats: list[dict[str, Any]]) -> np.ndarray:
    """The sorted (n, 2) FT/FF cells a batch of pre-gem stats can reach over every gem split: a reachability projection
    of the full search space, so no candidate is removed and a cell outside it cannot be indexed by the exact solve."""
    ft_gems, ff_gems, _remaining = ftff_combo_arrays(GEM_BUDGET)
    ft_base = np.asarray([stats["Fever Time"] for stats in base_stats], dtype=np.int32)[:, None]
    ff_base = np.asarray([stats["Fever Fill Rate"] for stats in base_stats], dtype=np.int32)[:, None]
    ft_stats = np.clip(ft_base + ft_gems[None, :] * STAT_GEM_GAIN_FEVER, 0, MAX_STAT)
    ff_stats = np.clip(ff_base + ff_gems[None, :] * STAT_GEM_GAIN_FEVER, 0, MAX_STAT)
    axis = MAX_STAT + 1
    cells = np.unique((ft_stats * axis + ff_stats).ravel())
    return np.stack((cells // axis, cells % axis), axis=1)


def score_fg_base_components(
    *,
    base_components: np.ndarray,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
    floors: np.ndarray | None = None,
    memo: GemMemo | None = None,
) -> dict[tuple[int, ...], GemWinner]:
    """The FG score row of each distinct 7-vector of pre-gem totals (PP, CM, FM, primary, secondary, FT, FF), keyed by
    it (CPU only); equal 7-vectors have equal FG results, so each is scored once. ``selected_color`` is the song's
    selected element; every other input is song-level (the scoring bundle). With `floors` (a score per row) a 7-vector
    below its floor (the lowest of its floors) has no row; `memo` carries what a song's calls share."""
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
        memo=memo,
    )
    winners = gem_winners(
        groups,
        scoring_bundle.pool,
        colors=(inputs.primary_color, inputs.secondary_color, selected_color),
        curves=curves,
        floors=None if floors is None else np.asarray(list(floor_of.values())),
    )
    return {key: winner for key, winner in zip(floor_of, winners, strict=True) if winner is not None}


def fg_solve_result(
    *,
    score_row: GemWinner,
    base_stats: dict[str, Any],
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
) -> FgResponseFrontierSolveResult:
    """A loadout's FG solve result from its score row and its pre-gem stats (all 10)."""
    best_score, _surface, pp, cm, fm, element = score_row.inner_row[:6]
    return FgResponseFrontierSolveResult(
        best_score=best_score,
        ft=score_row.ft,
        ff=score_row.ff,
        gem_counts=build_gem_counts(pp, cm, fm, element),
        stats=apply_gems(base_stats, gems(pp=pp, cm=cm, fm=fm, ft=score_row.ft, ff=score_row.ff, element=element),
                         str(selected_color or "")),
        surface=FgResponseSurface(*score_row.surface),
        non_fever_base=int(scoring_bundle.non_fever_base_by_ff[score_row.ff_stat]),
        raw_fever_fill=float(scoring_bundle.raw_fill_by_ff[score_row.ff_stat]),
        real_fever_time=float(scoring_bundle.real_time_by_ft[score_row.ft_stat]),
    )


def fg_solve_results(
    stats_rows,
    *,
    song: TimedSong,
    curves: StatCurves,
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
) -> list[FgResponseFrontierSolveResult]:
    """Each row of pre-gem stats' FG solve result."""
    song_inputs = song.fg_inputs
    totals = [loadout_totals(stats, song_inputs.primary_color, song_inputs.secondary_color) for stats in stats_rows]
    rows = score_fg_base_components(
        base_components=np.asarray(totals, dtype=np.int32), song=song, curves=curves, selected_color=selected_color,
        scoring_bundle=scoring_bundle,
    )
    return [
        fg_solve_result(score_row=rows[key], base_stats=dict(stats), selected_color=selected_color,
                        scoring_bundle=scoring_bundle)
        for key, stats in zip(totals, stats_rows, strict=True)
    ]
