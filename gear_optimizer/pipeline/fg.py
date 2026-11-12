"""A song's Force Greats stage, around its GA.

Before the GA: the song's FG scoring bundle (prepare_fg_static). In the GA turn: the FG score rows of the loadouts the
GA selected, keyed by their pre-gem totals (equal totals score alike; score_payload_fg). After it (finish_fg, host
only): the stored surface, i.e. the best LOADOUTS_PER_SONG_LIMIT selected loadouts by the GA's Base score, one per
effective loadout, with their validated FG results, as the song's SongSolve.
"""

from __future__ import annotations

import logging
from heapq import heapify, heappop, heappush
from typing import Any

import numpy as np

from gear_optimizer.core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from gear_optimizer.data.loadout_equivalence import effective_loadout_hash_from_names, effective_mini_signature_for_name
from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.pipeline.results import SolvedLoadout, SongSolve, solved_fg
from gear_optimizer.pipeline.song import NativeSong
from gear_optimizer.solver.base_stats import COLOR_TO_STAT_INDEX, build_stats_dict, loadout_totals
from gear_optimizer.solver.fg_search import search_fg_loadouts
from gear_optimizer.solver.ga_selection import GaSelection
from gear_optimizer.solver.gem_search import GemMemo
from gear_optimizer.trace.materialize import (
    FgTraceMaterializationCache,
    materialize_force_payload_from_response_frontier,
)
from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination_batch
from gear_optimizer.trace.reconstruct import UnplayableTrace
from gear_optimizer.frontier.fg_cache import load_response_frontier_scoring_bundle, release_fg_response_song_memory
from gear_optimizer.solver.fg_scoring import bundle_without_surface, fg_solve_result, score_fg_base_components
from gear_optimizer.stats import GEM_KINDS, apply_gems, gems

logger = logging.getLogger(__name__)
# The FG search's beam: this many loadouts per GA run (the reasoning level sets the runs: 5 / 10 / 20).
FG_SEARCH_BEAM_PER_GA_RUN = 1
# A loadout's FG plans tried before it goes without a result: a surface with no frames is rare, and its neighbours may be too.
FG_PLAN_TRIES = 8


def prepare_fg_static(song: NativeSong) -> None:
    """The song's FG scoring bundle, loaded while nothing waits on it."""
    gpu_inputs = song.gpu_inputs
    song.runtime.fg.fg_response_scoring_bundle = load_response_frontier_scoring_bundle(gpu_inputs.timed_song,
                                                                                       gpu_inputs.curves)


def fg_turn(song: NativeSong, selection: GaSelection) -> tuple[GaSelection, dict]:
    """In the GA turn (GPU owner): the GA's selection and its FG score rows, with the FG search's board candidates added
    to both: the best LOADOUTS_PER_SONG_LIMIT loadouts the search scored outside the selection whose FG score beats their
    own Base score (re-solved on the GPU). A candidate whose Base score beats the selection's best becomes its best. The
    search widens with the GA's runs, i.e. the reasoning level."""
    inputs = song.gpu_inputs
    timed, curves, selected_color = inputs.timed_song, inputs.curves, inputs.meta_primary_color
    fg_scoring_bundle = song.runtime.fg.fg_response_scoring_bundle
    memo = GemMemo()

    def score(rows: np.ndarray, floors: np.ndarray | None = None) -> dict:
        return score_fg_base_components(base_components=rows, song=timed, curves=curves, selected_color=selected_color,
                                        scoring_bundle=fg_scoring_bundle, floors=floors, memo=memo)

    fg_rows = score(selection.base_stats) if selection.scores.shape[0] else {}
    if not fg_rows:
        return selection, fg_rows
    stats, fixed = inputs.item_stats.astype(np.int64), inputs.base_fixed_stats_arr.astype(np.int64)
    columns = [0, 1, 2, COLOR_TO_STAT_INDEX[timed.fg_inputs.primary_color],
               COLOR_TO_STAT_INDEX[timed.fg_inputs.secondary_color], 3, 4]
    found = search_fg_loadouts(seeds=selection.genomes, seed_rows=fg_rows,
                               totals=lambda genomes: (fixed + stats[genomes].sum(axis=1))[:, columns], score=score,
                               slot_start=inputs.slot_start, slot_count=inputs.slot_count,
                               beam_width=FG_SEARCH_BEAM_PER_GA_RUN * inputs.num_runs)
    seeded = {tuple(row) for row in selection.base_stats.tolist()}
    outside = sorted((key for key in found if key not in seeded), key=lambda key: -found[key][1].inner_row[0])
    genomes = [found[key][0] for key in outside]
    bases = solve_best_fever_combination_batch(
        [build_stats_dict(fixed + stats[list(genome)].sum(axis=0)) for genome in genomes], timed, curves,
        selected_color=selected_color,
    ) if genomes else []
    added = []
    for key, genome, base in zip(outside, genomes, bases, strict=True):
        if found[key][1].inner_row[0] > base.score and len(added) < LOADOUTS_PER_SONG_LIMIT:
            gem = dict(zip(GEM_KINDS, base.gems, strict=True))
            added.append((base.score, genome, (base.score, gem["Fever Time"], gem["Fever Fill Rate"], gem["Perfect Points"],
                                               gem["Combo Multiplier"], gem["Fever Multiplier"], gem["Element"]), key))
    if not added:
        return selection, fg_rows
    scores, new_genomes, results, keys = (np.asarray(column, dtype=np.int32) for column in zip(*added))
    top = int(np.argmax(scores))
    merged = GaSelection(
        selection.best_score, selection.best_genome, selection.best_results,
        np.concatenate([selection.scores, scores]), np.concatenate([selection.genomes, new_genomes]),
        np.concatenate([selection.results, results]), np.concatenate([selection.base_stats, keys]),
    )
    if scores[top] > selection.best_score:  # the search found a better Base loadout than the GA
        merged = merged._replace(best_score=int(scores[top]), best_genome=new_genomes[top], best_results=results[top])
    return merged, {**fg_rows, **{key: found[key][1] for key in outside}}


def _selected_surface(song: NativeSong, selection: GaSelection, fg_rows: dict) -> list[tuple]:
    """The selection's loadouts (its best, then its rows), one per effective loadout (the higher GA Base score, then the
    earlier row), as (genome ids with the minis sorted, GA Base score, Base results, item names, pre-gem stats): the Meta
    board's candidates (the best LOADOUTS_PER_SONG_LIMIT by Base score), then the FG board's not among them (the best by
    FG score of those whose FG score beats their Base score), each ordered by score, then loadout hash, descending."""
    gpu_inputs = song.gpu_inputs
    song_inputs = gpu_inputs.timed_song.fg_inputs
    primary, secondary = gpu_inputs.meta_primary_color, gpu_inputs.meta_secondary_color
    pool = [(selection.best_genome, selection.best_score, selection.best_results)]
    pool += zip(selection.genomes, selection.scores.tolist(), selection.results)
    best: dict[str, tuple] = {}
    for ids, score, results in pool:
        genome = (*(int(v) for v in ids[:6]), *sorted(int(v) for v in ids[6:9]))
        names = gpu_inputs.registry.decode_names(np.asarray(genome, dtype=np.int32))
        sigs = [effective_mini_signature_for_name(n, gpu_inputs.minis_by_name, primary, secondary, primary)
                for n in names[6:]]
        key = effective_loadout_hash_from_names(names[:6], sigs)
        if key not in best or score > best[key][1]:
            pre_gem = build_stats_dict(gpu_inputs.base_fixed_stats_arr + gpu_inputs.item_stats[list(genome)].sum(axis=0))
            best[key] = (genome, score, results, names, pre_gem)

    def fg_score(loadout: tuple) -> int:
        row = fg_rows.get(loadout_totals(loadout[4], song_inputs.primary_color, song_inputs.secondary_color))
        return -1 if row is None else row.inner_row[0]

    meta = sorted(best.items(), key=lambda item: (item[1][1], item[0]), reverse=True)[:LOADOUTS_PER_SONG_LIMIT]
    taken = {key for key, _loadout in meta}
    fg_board = sorted(((key, loadout) for key, loadout in best.items()
                       if key not in taken and fg_score(loadout) > loadout[1]),
                      key=lambda item: (fg_score(item[1]), item[0]), reverse=True)[:LOADOUTS_PER_SONG_LIMIT]
    return [loadout for _key, loadout in meta + fg_board]


def best_fg_results(jobs, materialize, next_best, song_name: str) -> list[tuple[int, Any]]:
    """The FG results of jobs ((loadout index, FG solve result)), materialized best solve score first, at most
    LOADOUTS_PER_SONG_LIMIT, best exact FG score first. A loadout whose FG plan no legal hit timing plays (materialize
    raises UnplayableTrace) goes back in line with its next best surface (next_best), FG_PLAN_TRIES plans at the most; then
    it keeps no FG result (owner 09-30)."""
    results = []
    line = [(-result.best_score, order, index, result, 1) for order, (index, result) in enumerate(jobs)]
    heapify(line)
    while line and len(results) < LOADOUTS_PER_SONG_LIMIT:
        _score, order, index, result, tries = heappop(line)
        try:
            results.append((index, materialize(index, result)))
        except UnplayableTrace as exc:
            logger.warning("%s: FG plan %d of loadout %d is unplayable: %s", song_name, tries, index, exc)
            if tries < FG_PLAN_TRIES:
                lower = next_best(index, result)
                heappush(line, (-lower.best_score, order, index, lower, tries + 1))
    return sorted(results, key=lambda item: item[1].score, reverse=True)


def finish_fg(song: NativeSong, ga_result: tuple[GaSelection, dict]) -> SongSolve:
    """The song's SongSolve from its GA result (fg_turn's): the selected surface, each loadout's FG solve (loadouts with
    equal pre-gem stats share one) and the FG results best_fg_results keeps."""
    gpu_inputs, fg = song.gpu_inputs, song.runtime.fg
    timed, curves, selected = gpu_inputs.timed_song, gpu_inputs.curves, gpu_inputs.meta_primary_color
    selection, fg_rows = ga_result
    try:
        loadouts, base_stats, perfect_times = [], [], []
        items = gpu_inputs.registry.id_to_item
        for genome, score, (_s, ft, ff, pp, cm, fm, ov), names, pre_gem in _selected_surface(song, selection, fg_rows):
            allocation = gems(pp=pp, cm=cm, fm=fm, ft=ft, ff=ff, element=ov)
            loadouts.append(SolvedLoadout(tuple(names[:6]), tuple(names[6:]), tuple(allocation[k] for k in GEM_KINDS),
                                          apply_gems(pre_gem, allocation, selected), int(score)))
            base_stats.append(pre_gem)
            perfect_times.append(sum(items[item_id].perfect_time for item_id in genome[:6]))
        song_inputs = timed.fg_inputs
        solves: dict[tuple, Any] = {}
        jobs = []
        for index, stats in enumerate(base_stats):
            key = tuple(sorted(stats.items()))
            if key not in solves:
                totals = loadout_totals(stats, song_inputs.primary_color, song_inputs.secondary_color)
                solves[key] = fg_solve_result(score_row=fg_rows[totals], base_stats=stats, selected_color=selected,
                                              scoring_bundle=fg.fg_response_scoring_bundle)
            jobs.append((index, solves[key]))
        trace_cache = FgTraceMaterializationCache()

        def materialize(index: int, result: Any) -> Any:
            payload_fg = materialize_force_payload_from_response_frontier(
                base_stats=base_stats[index], paired_base_score=loadouts[index].score, selected_element=selected,
                result=result, song=timed, curves=curves, trace_cache=trace_cache,
                perfect_time=perfect_times[index],
            )
            return solved_fg(payload_fg, default_element=selected)

        without: dict[int, Any] = {}

        def next_best(index: int, result: Any) -> Any:
            stats = base_stats[index]
            bundle = without[index] = bundle_without_surface(without.get(index, fg.fg_response_scoring_bundle), result.surface)
            totals = loadout_totals(stats, song_inputs.primary_color, song_inputs.secondary_color)
            rows = score_fg_base_components(base_components=np.asarray([totals], dtype=np.int32), song=timed, curves=curves,
                                            selected_color=selected, scoring_bundle=bundle)
            return fg_solve_result(score_row=rows[totals], base_stats=stats, selected_color=selected, scoring_bundle=bundle)

        results = best_fg_results(jobs, materialize, next_best, timed.chart.name)
    finally:
        # The surfaces (~0.5-1.5 GB) are not read again; a later access rebuilds them from the on-disk bundle.
        release_fg_response_song_memory(fg.fg_response_scoring_bundle.cache_key)
        fg.fg_response_scoring_bundle = None
    return SongSolve(song=str(song.config.db_key), tier=OPTIMIZER_BASELINE_TEAM_BUFF, timed=timed, curves=curves,
                     loadouts=tuple(loadouts), fg=tuple(results))
