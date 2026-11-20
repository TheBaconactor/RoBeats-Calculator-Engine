"""The FG score of loadouts over a song's scoring bundle: the exact gem search, and its winners as solve results."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np

from gear_optimizer.core.gem_defs import build_gem_counts
from gear_optimizer.frontier.fg_cache_types import FgResponseFrontierScoringBundle
from gear_optimizer.frontier.types import FgResponseFrontierSolveResult, FgResponseSurface
from gear_optimizer.gamedata import StatCurves
from gear_optimizer.rules import GEM_BUDGET, MAX_STAT, STAT_GEM_GAIN_FEVER
from gear_optimizer.solver.base_stats import loadout_totals
from gear_optimizer.solver.ftff_combos import ftff_combo_arrays
from gear_optimizer.solver.gem_search import GemMemo, GemWinner, gem_winners
from gear_optimizer.solver.timing_envelope import TimedSong
from gear_optimizer.stats import apply_gems, gems


def required_response_stat_keys(base_stats: list[dict[str, Any]], *, budget: int | None = None) -> np.ndarray:
    """The sorted (n, 2) FT/FF cells a batch of pre-gem stats can reach over every gem split: a reachability projection
    of the full search space, so no candidate is removed and a cell outside it cannot be indexed by the exact solve."""
    ft_gems, ff_gems, _remaining = ftff_combo_arrays(GEM_BUDGET if budget is None else budget)
    unique_pairs = list(dict.fromkeys((stats["Fever Time"], stats["Fever Fill Rate"]) for stats in base_stats))
    pairs = np.asarray(unique_pairs, dtype=np.int32)
    ft_stats = np.clip(pairs[:, 0:1] + ft_gems[None, :] * STAT_GEM_GAIN_FEVER, 0, MAX_STAT)
    ff_stats = np.clip(pairs[:, 1:2] + ff_gems[None, :] * STAT_GEM_GAIN_FEVER, 0, MAX_STAT)
    axis = MAX_STAT + 1
    seen = np.zeros(axis * axis, dtype=np.bool_)
    seen[(ft_stats * axis + ff_stats).ravel()] = True
    cells = np.flatnonzero(seen).astype(np.int32)
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
    budget: int | None = None,
) -> dict[tuple[int, ...], GemWinner]:
    """The FG score row of each distinct 7-vector of pre-gem totals (PP, CM, FM, primary, secondary, FT, FF), keyed by
    it (CPU only); equal 7-vectors have equal FG results, so each is scored once. ``selected_color`` is the song's
    selected element; every other input is song-level (the scoring bundle). With `floors` (a score per row) a 7-vector
    below its floor (the lowest of its floors) has no row; `memo` carries what a song's calls share."""
    arr = np.asarray(base_components, dtype=np.int32)
    n = int(arr.shape[0])
    if n == 0:
        return {}
    floors_arr = None if floors is None else np.asarray(floors, dtype=np.int64)
    floor_list = None if floors_arr is None else floors_arr.tolist()
    pos_of: dict[tuple[int, ...], int] = {}
    keep_idx: list[int] = []
    keep_floors: list[int] = []
    for idx, row in enumerate(arr.tolist()):
        key = tuple(row)
        prev = pos_of.get(key)
        if prev is None:
            pos_of[key] = len(keep_idx)
            keep_idx.append(idx)
            if floor_list is not None:
                keep_floors.append(floor_list[idx])
        elif floor_list is not None and floor_list[idx] < keep_floors[prev]:
            keep_floors[prev] = floor_list[idx]
    all_unique = len(keep_idx) == n
    unique_arr = arr if all_unique else arr[keep_idx]
    unique_floors = floors_arr if all_unique else (None if floors_arr is None else np.asarray(keep_floors, dtype=np.int64))
    inputs = song.fg_inputs
    total_notes = int(inputs.total_notes)
    active_budget = GEM_BUDGET if budget is None else budget
    budgets = None if active_budget == GEM_BUDGET else np.full(len(pos_of), active_budget, dtype=np.int32)
    winners = gem_winners(
        unique_arr,
        (scoring_bundle.frontier_idx_by_stat, scoring_bundle.pool),
        colors=(inputs.primary_color, inputs.secondary_color, selected_color),
        curves=curves,
        notes=(min(total_notes, 100), max(0, total_notes - 100)),
        budgets=budgets,
        floors=unique_floors,
        memo=memo,
    )
    return {key: winner for key, winner in zip(pos_of, winners, strict=True) if winner is not None}


def bundle_without_surface(
    bundle: FgResponseFrontierScoringBundle, surface: FgResponseSurface
) -> FgResponseFrontierScoringBundle:
    """The bundle with `surface` gone from every frontier: what a loadout scores when its plan on `surface` is unplayable."""
    pool = bundle.pool
    words = np.asarray(surface[:8], dtype=pool.pattern_words.dtype)
    matching_patterns = np.flatnonzero((pool.pattern_words == words).all(axis=1))
    if matching_patterns.size == 0:
        return bundle
    pat_match = (
        pool.pattern_ids == int(matching_patterns[0])
        if matching_patterns.size == 1
        else np.isin(pool.pattern_ids, matching_patterns)
    )
    candidate_rows = np.flatnonzero(pat_match)
    if candidate_rows.size == 0:
        return bundle
    body = np.asarray(surface[8:], dtype=pool.counts.dtype)
    dropped_rows = candidate_rows[(pool.counts[candidate_rows] == body).all(axis=1)]
    if dropped_rows.size == 0:
        return bundle
    keep = np.ones(pool.pattern_ids.shape[0], dtype=np.bool_)
    keep[dropped_rows] = False
    kept_before = np.concatenate(([0], np.cumsum(keep, dtype=np.int32)), dtype=np.int32)
    offsets = kept_before[pool.frontier_offsets]
    return replace(bundle, pool=replace(
        pool,
        frontier_offsets=offsets,
        frontier_lengths=kept_before[pool.frontier_offsets + pool.frontier_lengths] - offsets,
        pattern_ids=pool.pattern_ids[keep],
        counts=pool.counts[keep],
    ))


def fg_solve_result(
    *,
    score_row: GemWinner,
    base_stats: dict[str, Any],
    selected_color: str,
    scoring_bundle: FgResponseFrontierScoringBundle,
) -> FgResponseFrontierSolveResult:
    """A loadout's FG solve result from its score row and its pre-gem stats (all 10)."""
    best_score, _surface, pp, cm, fm, element = score_row.inner_row
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
    memo: GemMemo | None = None,
    budget: int | None = None,
) -> list[FgResponseFrontierSolveResult]:
    """Each row of pre-gem stats' FG solve result."""
    song_inputs = song.fg_inputs
    totals = [loadout_totals(stats, song_inputs.primary_color, song_inputs.secondary_color) for stats in stats_rows]
    rows = score_fg_base_components(
        base_components=np.asarray(totals, dtype=np.int32), song=song, curves=curves, selected_color=selected_color,
        scoring_bundle=scoring_bundle, memo=memo, budget=budget,
    )
    return [
        fg_solve_result(score_row=rows[key], base_stats=dict(stats), selected_color=selected_color,
                        scoring_bundle=scoring_bundle)
        for key, stats in zip(totals, stats_rows, strict=True)
    ]
