"""Real GA seeds and canonical replay for the outer-core experiment."""

from dataclasses import dataclass
import time

import numpy as np

from gear_optimizer.core.color_flags import build_color_flags
from gear_optimizer.core.constants import GEM_SCALE_FEVER, GEM_SCALE_NORMAL, MAX_STAT_INDEX
from gear_optimizer.core.config import load_config
from gear_optimizer.data.csv_parser import get_fixed_stats
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.helpers.ga_helpers.pool_initialization import initialize_pools
from gear_optimizer.helpers.song_helpers.song_config import apply_baseline_team_buff_config
from gear_optimizer.solver.base_stats import build_base_fixed_stats_array, build_stats_dict
from gear_optimizer.solver.fg_effective_dedup import effective_tables_for_context
from gear_optimizer.solver.genetic_pipeline import run_gpu_native_ga_runs_payload_prebuilt
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.registry_solve_request import RegistrySolveRequest, dispatch_registry_solve
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact_batch
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.solver.solver_common import GEAR_SLOTS, build_solver_cfg_data
from gear_optimizer.solver.taichi_gem.api.timeline import (
    build_or_load_timeline_frontier_payload, precompute_timeline_gpu,
)
from gear_optimizer.solver.timing_envelope import apply_timing_envelope
from tools.research._core_bound_domain import catalog_domain


@dataclass(frozen=True)
class PreparedChart:
    song: dict
    refs: dict
    domain: object
    registry: object
    arrays: dict
    base: np.ndarray
    ga_kwargs: dict
    timeline: object


def prepare_chart(path, refs, gears, minis):
    song = get_base_calc_song(str(path), {})
    apply_timing_envelope(song, mode="perfect_window")
    primary, secondary = (song["metadata"][k] for k in ("Primary Color", "Secondary Color"))
    cfg = load_config()
    apply_baseline_team_buff_config(cfg, song)
    fixed = get_fixed_stats(cfg)
    cfg_data = build_solver_cfg_data(cfg, p_color=primary, s_color=secondary, selected_color=primary)
    base, _ = build_base_fixed_stats_array(fixed, cfg_data)
    domain = catalog_domain(gears, minis, song=song, fixed=build_stats_dict(base))
    gear_pool, mini_pool, *_ = initialize_pools(gears, list(domain.mini_items), primary,
                                               list(GEAR_SLOTS), s_color=secondary)
    registry = ItemRegistry(gear_pool, mini_pool, list(GEAR_SLOTS))
    arrays = registry.to_gpu_arrays()
    gear_rank, mini_sig = effective_tables_for_context(registry, primary_color=primary,
                                                       secondary_color=secondary, selected_color=primary)
    timeline = build_or_load_timeline_frontier_payload(song, refs)
    precompute_timeline_gpu(song, refs, song_slot=0, prebuilt_frontier=timeline)
    kwargs = dict(calc_song=song, ref_arrays=refs, song_slot=0, item_stats=arrays["item_stats"],
                  slot_start=arrays["slot_start"], slot_count=arrays["slot_count"], base_fixed_stats_arr=base,
                  initial_populations=None, color_flags=build_color_flags(primary, secondary, primary),
                  cfg_data=cfg_data, fg_gear_name_rank=gear_rank, fg_mini_sig_id=mini_sig)
    return PreparedChart(song, refs, domain, registry, arrays, base, kwargs, timeline.payload)


def replay_results(chart, arrays, ids, results):
    """Validate witnesses and replay every row with the authoritative f64 scorer."""
    selected = chart.song["metadata"]["Primary Color"]
    stats_rows = []
    for genome, result in zip(ids, results, strict=True):
        if len(set(map(int, genome[6:]))) != 3:
            raise ValueError("inner solver witness has repeated Minis")
        for slot, item_id in enumerate(genome):
            start, count = int(arrays["slot_start"][slot]), int(arrays["slot_count"][slot])
            if not start <= item_id < start + count:
                raise ValueError("inner solver witness is outside its slot pool")
        gems = list(map(int, result[1:7]))
        if len(gems) != 6 or min(gems) < 0 or sum(gems) != chart.domain.budget:
            raise ValueError("inner solver witness violates the shared gem budget")
        base = build_stats_dict(chart.base + arrays["item_stats"][genome].sum(axis=0))
        names = ("Fever Time", "Fever Fill Rate", "Perfect Points", "Combo Multiplier", "Fever Multiplier")
        scales = (GEM_SCALE_FEVER, GEM_SCALE_FEVER, GEM_SCALE_NORMAL, GEM_SCALE_NORMAL, GEM_SCALE_FEVER)
        if any(g > max(0, (MAX_STAT_INDEX - base[name]) // scale)
               for name, g, scale in zip(names, gems, scales)):
            raise ValueError("inner solver witness exceeds a stat-gem cap")
        stats_rows.append(apply_gems_to_base_stats(base, selected, *gems))
    scores = score_stats_exact_batch(stats_rows, chart.song, chart.refs)
    return scores, stats_rows


def run_ga(chart, *, generations, population, runs, seed, on_improvement=None):
    start = time.perf_counter()
    observed_best, observer_seconds = 0, 0.
    observed_witness = None

    def observe(rows):
        nonlocal observed_best, observer_seconds, observed_witness
        t = time.perf_counter()
        rows = rows[rows[:, 0] > 0]
        if len(rows):
            scores, observed_stats = replay_results(chart, chart.arrays, rows[:, 1:10], rows[:, 10:17])
            score = int(max(scores))
            if score > observed_best:
                observed_best = score
                winner = int(np.argmax(scores))
                observed_witness = (rows[winner, 1:10].copy(), rows[winner, 10:17].copy(), observed_stats[winner])
                on_improvement(score)
        observer_seconds += time.perf_counter() - t

    payload = run_gpu_native_ga_runs_payload_prebuilt(**chart.ga_kwargs, ga_seed=seed,
        n_generations=generations, n_genomes=population, num_runs=runs,
        on_generation=observe if on_improvement is not None else None)
    ga_seconds = time.perf_counter() - start
    ids = np.asarray(payload[:1, 2:11], dtype=np.int32)
    result = np.asarray(payload[:1, 11:18], dtype=np.int64)
    start = time.perf_counter()
    scores, stats = replay_results(chart, chart.arrays, ids, result)
    if observed_best > scores[0]:
        ids[0], result[0], stats[0] = observed_witness
        scores[0] = observed_best
    if on_improvement is not None:
        on_improvement(int(scores[0]))
    return {"score": int(scores[0]), "observer_s": observer_seconds, "gpu_score": int(result[0, 0]), "stats": stats[0],
            "ids": ids[0].tolist(), "gems": result[0, 1:7].tolist(), "ga_s": ga_seconds,
            "replay_s": time.perf_counter() - start,
            "settings": {"generations": generations, "population": population, "runs": runs, "seed": seed}}


def score_core(chart, core, *, on_improvement=None, deadline=None):
    total_start = time.perf_counter()
    if not core.complete:
        raise ValueError("the core enumeration hit its work limit")
    domain = chart.domain
    registry = ItemRegistry(dict(zip(GEAR_SLOTS, domain.gear_items)), list(domain.mini_items), list(GEAR_SLOTS))
    arrays = registry.to_gpu_arrays()
    witnesses = sorted(core.witnesses)
    if not witnesses:
        return {"scored": 0, "best_score": 0, "solve_s": 0., "replay_s": 0.,
                "total_s": time.perf_counter() - total_start}
    ids = np.empty((len(witnesses), 9), dtype=np.int32)
    for i, row in enumerate(witnesses):
        for slot in range(6):
            ids[i, slot] = registry.item_to_id[(slot, domain.gear_items[slot][row[slot]]["Name"])]
        for slot in range(6, 9):
            ids[i, slot] = registry.item_to_id[(6, domain.mini_items[row[slot]]["Name"])]
    best, solve_seconds, replay_seconds = 0, 0., 0.
    best_witness = None
    scored = 0
    for start in range(0, len(ids), 512):
        if deadline is not None and time.perf_counter() >= deadline:
            break
        batch = ids[start:start + 512]
        scored += len(batch)
        t = time.perf_counter()
        result = np.asarray(dispatch_registry_solve(RegistrySolveRequest(
            population_indices=batch, item_stats=arrays["item_stats"], slot_start=arrays["slot_start"],
            slot_count=arrays["slot_count"], base_fixed_stats=chart.base, timeline_grid=chart.song,
            ref_arrays=chart.refs, flags=chart.ga_kwargs["color_flags"], total_budget=domain.budget,
        )), dtype=np.int64)
        solve_seconds += time.perf_counter() - t
        t = time.perf_counter()
        scores, stats = replay_results(chart, arrays, batch, result)
        winner = int(np.argmax(scores))
        if scores[winner] > best:
            best = int(scores[winner])
            if on_improvement is not None:
                on_improvement(best)
            best_witness = {"catalog_indices": witnesses[start + winner], "stats": stats[winner],
                            "gems": result[winner, 1:7].tolist()}
        replay_seconds += time.perf_counter() - t
    return {"scored": scored, "queue_exhausted": scored == len(witnesses), "best_score": best, "best_witness": best_witness,
            "solve_s": solve_seconds, "replay_s": replay_seconds, "total_s": time.perf_counter() - total_start}
