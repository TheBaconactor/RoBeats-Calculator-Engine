"""A song's Force Greats stage, around its GA.

Before the GA: the song's FG scoring bundle (prepare_fg_static). In the GA turn: the FG score rows of the loadouts the
GA selected, keyed by their pre-gem totals (equal totals score alike; score_payload_fg). After it (finish_fg, host
only): the stored surface, i.e. the best LOADOUTS_PER_SONG_LIMIT selected loadouts by the GA's Base score, one per
effective loadout, with their exact Base scores and validated FG results, as the song's SongSolve.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import numpy as np

from gear_optimizer.core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from gear_optimizer.data.loadout_equivalence import effective_loadout_hash_from_names, effective_mini_signature_for_name
from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from gear_optimizer.pipeline.progress import evaluate_fg_progress_record_update
from gear_optimizer.pipeline.results import SolvedLoadout, SongSolve, solved_fg
from gear_optimizer.pipeline.song import NativeSong
from gear_optimizer.solver.base_stats import COLOR_TO_STAT_INDEX, build_stats_dict
from gear_optimizer.solver.fg_search import search_fg_loadouts
from gear_optimizer.solver.fg_response_scoring.note_graph import UnplayableTrace
from gear_optimizer.solver.fg_response_scoring.reducer import (
    FgTraceMaterializationCache,
    materialize_force_payload_from_response_frontier,
)
from gear_optimizer.solver.force_greats_common import response_frontier_base_components_row
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact_batch
from gear_optimizer.solver.scoring.fever_solver import solve_best_fever_combination_batch
from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
    load_response_frontier_scoring_bundle,
    session_prune_scoring_bundle,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_store import release_fg_response_song_memory
from gear_optimizer.solver.taichi_gem.force_greats.response_cache_types import all_response_stat_keys
from gear_optimizer.solver.taichi_gem.force_greats.response_frontier import fg_solve_result, score_fg_base_components
from gear_optimizer.stats import GEM_KINDS, apply_gems, gems

if TYPE_CHECKING:
    from gear_optimizer.pipeline.progress import ProgressTracker

logger = logging.getLogger(__name__)
# The FG search's beam: this many loadouts per GA run (the reasoning level sets the runs: 5 / 10 / 20).
FG_SEARCH_BEAM_PER_GA_RUN = 1


def prepare_fg_static(song: NativeSong) -> None:
    """The song's FG scoring bundle, loaded and session-pruned while nothing waits on it: rows no cell this inventory
    can reach could win are dropped (identical winners, fewer scored rows)."""
    gpu_inputs = song.gpu_inputs
    bundle = load_response_frontier_scoring_bundle(gpu_inputs.timed_song, gpu_inputs.curves,
                                                   stat_keys=all_response_stat_keys())
    song.runtime.fg.fg_response_scoring_bundle = session_prune_scoring_bundle(bundle, gpu_inputs.curves)


def fg_turn(runs_payload: np.ndarray, *, song, curves, selected_color: str, fg_scoring_bundle, item_stats: np.ndarray,
            slot_start: np.ndarray, slot_count: np.ndarray, base_fixed_stats_arr: np.ndarray,
            beam_width: int) -> tuple[np.ndarray, dict]:
    """In the GA turn (GPU owner): the GA's selected payload and its FG score rows (rows 1.., device base_stats7 in
    columns 19-25), with the FG search's board candidates added to both: the best LOADOUTS_PER_SONG_LIMIT loadouts the
    search scored outside the payload whose FG score beats their own Base score (re-solved on the GPU). A candidate
    whose Base score beats the payload's best becomes its header best."""
    payload = np.asarray(runs_payload, dtype=np.int32)
    selected = payload[1 : 1 + int(payload[0, 0])]

    def score(rows: np.ndarray, floors: np.ndarray | None = None) -> dict:
        return score_fg_base_components(base_components=rows, song=song, curves=curves, selected_color=selected_color,
                                        scoring_bundle=fg_scoring_bundle, floors=floors)

    fg_rows = score(selected[:, 19:26]) if selected.shape[0] else {}
    if not fg_rows or beam_width <= 0:
        return payload, fg_rows
    stats, fixed = item_stats.astype(np.int64), base_fixed_stats_arr.astype(np.int64)
    columns = [0, 1, 2, COLOR_TO_STAT_INDEX[song.fg_inputs.primary_color],
               COLOR_TO_STAT_INDEX[song.fg_inputs.secondary_color], 3, 4]
    found = search_fg_loadouts(seeds=selected[:, 3:12], seed_rows=fg_rows,
                               totals=lambda genomes: (fixed + stats[genomes].sum(axis=1))[:, columns], score=score,
                               slot_start=slot_start, slot_count=slot_count, beam_width=beam_width)
    seeded = {tuple(row) for row in selected[:, 19:26].tolist()}
    outside = sorted((key for key in found if key not in seeded), key=lambda key: -found[key][1].inner_row[0])
    genomes = [found[key][0] for key in outside]
    bases = solve_best_fever_combination_batch(
        [build_stats_dict(fixed + stats[list(genome)].sum(axis=0)) for genome in genomes], song, curves,
        selected_color=selected_color,
    ) if genomes else []
    rows = []
    for key, genome, base in zip(outside, genomes, bases, strict=True):
        if found[key][1].inner_row[0] > base.score and len(rows) < LOADOUTS_PER_SONG_LIMIT:
            gem = dict(zip(GEM_KINDS, base.gems, strict=True))
            rows.append([-1, -1, base.score, *genome, base.score, gem["Fever Time"], gem["Fever Fill Rate"],
                         gem["Perfect Points"], gem["Combo Multiplier"], gem["Fever Multiplier"], gem["Element"], *key])
    if not rows:
        return payload, fg_rows
    rows = np.asarray(rows, dtype=np.int32)
    header = payload[0].copy()
    header[0] += len(rows)
    top = rows[int(np.argmax(rows[:, 2]))]
    if top[2] > header[1]:  # the search found a better Base loadout than the GA
        header[1:19] = [top[2], *top[3:12], *top[12:19], -1]
    return np.concatenate([header[None], selected, rows]), {**fg_rows, **{key: found[key][1] for key in outside}}


def _selected_surface(song: NativeSong, payload: np.ndarray, fg_rows: dict) -> list[tuple]:
    """The payload's loadouts (its header best, then its rows), one per effective loadout (the higher GA Base score,
    then the earlier row), as (genome ids with the minis sorted, GA Base score, Base results [score, FT, FF, PP, CM,
    FM, element gems], item names, pre-gem stats): the Meta board's candidates (the best LOADOUTS_PER_SONG_LIMIT by
    Base score), then the FG board's not among them (the best by FG score of those whose FG score beats their Base
    score), each ordered by score, then loadout hash, descending."""
    gpu_inputs = song.gpu_inputs
    song_inputs = gpu_inputs.timed_song.fg_inputs
    primary, secondary = gpu_inputs.meta_primary_color, gpu_inputs.meta_secondary_color
    pool = [(payload[0, 2:11], int(payload[0, 1]), payload[0, 11:18])]
    pool += [(row[3:12], int(row[2]), row[12:19]) for row in payload[1 : 1 + int(payload[0, 0])]]
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
        totals = response_frontier_base_components_row(
            loadout[4], None, primary_color=song_inputs.primary_color, secondary_color=song_inputs.secondary_color
        )
        row = fg_rows.get(totals)
        return -1 if row is None else row.inner_row[0]

    meta = sorted(best.items(), key=lambda item: (item[1][1], item[0]), reverse=True)[:LOADOUTS_PER_SONG_LIMIT]
    taken = {key for key, _loadout in meta}
    fg_board = sorted(((key, loadout) for key, loadout in best.items()
                       if key not in taken and fg_score(loadout) > loadout[1]),
                      key=lambda item: (fg_score(item[1]), item[0]), reverse=True)[:LOADOUTS_PER_SONG_LIMIT]
    return [loadout for _key, loadout in meta + fg_board]


def best_fg_results(jobs, materialize, song_name: str) -> list[tuple[int, Any]]:
    """The FG results of jobs ((loadout index, FG solve result)), materialized best solve score first, at most
    LOADOUTS_PER_SONG_LIMIT, best exact FG score first. A loadout whose FG plan no legal hit timing plays (materialize
    raises UnplayableTrace) keeps no FG result and the next takes its place (owner 09-30)."""
    results = []
    for index, result in sorted(jobs, key=lambda job: job[1].best_score, reverse=True):
        if len(results) == LOADOUTS_PER_SONG_LIMIT:
            break
        try:
            results.append((index, materialize(index, result)))
        except UnplayableTrace as exc:
            logger.warning("%s: no FG result for loadout %d, its plan is unplayable: %s", song_name, index, exc)
    return sorted(results, key=lambda item: item[1].score, reverse=True)


def finish_fg(song: NativeSong, ga_result: dict, progress_tracker: ProgressTracker | None = None) -> SongSolve:
    """The song's SongSolve from its GA result ({runs_payload, fg_owner_score}), and its record info: the selected
    surface with exact Base scores, each loadout's FG solve (loadouts with equal pre-gem stats share one) and the FG
    results best_fg_results keeps."""
    gpu_inputs, fg = song.gpu_inputs, song.runtime.fg
    timed, curves, selected = gpu_inputs.timed_song, gpu_inputs.curves, gpu_inputs.meta_primary_color
    payload = np.asarray(ga_result["runs_payload"], dtype=np.int32)
    fg_rows = ga_result["fg_owner_score"]
    try:
        loadouts, base_stats, paired_stats = [], [], []
        for _genome, _score, (_s, ft, ff, pp, cm, fm, ov), names, pre_gem in _selected_surface(song, payload, fg_rows):
            loadouts.append(SolvedLoadout(tuple(names[:6]), tuple(names[6:])))
            base_stats.append(pre_gem)
            paired_stats.append(apply_gems(pre_gem, gems(pp=pp, cm=cm, fm=fm, ft=ft, ff=ff, element=ov), selected))
        paired = score_stats_exact_batch(paired_stats, timed, curves)
        song_inputs = timed.fg_inputs
        solves: dict[tuple, Any] = {}
        frontiers: dict[tuple[int, int], Any] = {}
        jobs = []
        for index, stats in enumerate(base_stats):
            key = tuple(sorted(stats.items()))
            if key not in solves:
                totals = response_frontier_base_components_row(
                    stats, None, primary_color=song_inputs.primary_color, secondary_color=song_inputs.secondary_color
                )
                solves[key] = fg_solve_result(score_row=fg_rows[totals], base_stats=stats, selected_color=selected,
                                              song=timed, curves=curves, scoring_bundle=fg.fg_response_scoring_bundle,
                                              frontier_by_stat_key=frontiers)
            jobs.append((index, solves[key]))
        trace_cache = FgTraceMaterializationCache()

        def materialize(index: int, result: Any) -> Any:
            payload_fg = materialize_force_payload_from_response_frontier(
                base_stats=base_stats[index], paired_base_score=paired[index], selected_element=selected,
                result=result, song=timed, curves=curves, trace_cache=trace_cache,
            )
            return solved_fg(payload_fg, default_element=selected)

        results = best_fg_results(jobs, materialize, timed.chart.name)
    finally:
        # The surfaces (~0.5-1.5 GB) are not read again; a later access rebuilds them from the on-disk bundle.
        release_fg_response_song_memory(fg.fg_response_scoring_bundle.cache_key)
        fg.fg_response_scoring_bundle = None
    song.runtime.db.record_info = evaluate_fg_progress_record_update(
        song, int(payload[0, 1]), [solved for _index, solved in results], progress_tracker
    )
    return SongSolve(song=str(song.config.db_key), tier=OPTIMIZER_BASELINE_TEAM_BUFF, timed=timed, curves=curves,
                     loadouts=tuple(loadouts), fg=tuple(results))
