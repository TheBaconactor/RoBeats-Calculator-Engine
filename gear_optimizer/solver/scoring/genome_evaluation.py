"""
Genome Evaluation - Batch Genome Evaluation for Genetic Algorithm.
This module provides high-performance genome evaluation for the co-evolution genetic algorithm:
- worker_coevolution_evaluate: Evaluates a single genome (gear + minis) in parallel worker
- batch_evaluate_genomes: Evaluates entire population in SINGLE GPU kernel launch
Key optimizations:
- Stat-signature caching: Reuse gem solver results for genomes with identical effective stats
- GPU mega-batch: Flatten ALL timelines from ALL genomes into one work list
- Signature deduplication: Evaluate unique stat combinations only once
- IPC routing: Route GPU calls through executor for parallel song processing
"""
from dataclasses import dataclass
from typing import Any, Callable, Optional
import logging
import numpy as np
from ...core.color_flags import build_color_flags
from ...core.constants import SKIP_ITEM_KEYS
from ...core.utils import stats_signature
from .runtime_state import GEM_SOLVER_CACHE
from .fever_solver import solve_best_fever_combination
from .stats_ops import apply_gems_to_base_stats
from ..base_stats import build_solver_stat_row
from ..registry_solve_request import (
    build_registry_solve_request,
    dispatch_registry_solve,
    registry_batch_solve_supported,
)

logger = logging.getLogger(__name__)


@dataclass
class GpuBatchEvalPlan:
    """Prepared (CPU-side) batch evaluation plan with a deferred GPU solve step."""
    population: list
    base_stats_fixed: dict
    cfg_data: dict
    calc_song: dict
    ref_arrays: dict
    genome_key_fn: Optional[Callable]
    evaluation_cache: Optional[dict]
    use_cache: bool
    cached_results: dict
    uncached_genomes: list
    uncached_indices: list
    all_stats: list
    sel_color: str
    config_sig: tuple
    sig_to_result: dict
    unique_stats: list
    unique_members: list
    genome_stats_list: Any
    flags: dict


def prepare_gpu_batch_eval_plan(
    population: list,
    base_stats_fixed: dict,
    cfg_data: dict,
    calc_song: dict,
    ref_arrays: dict,
    *,
    genome_key_fn: Optional[Callable] = None,
    evaluation_cache: Optional[dict] = None,
) -> tuple[Optional[GpuBatchEvalPlan], Optional[list]]:
    """
    Prepare a GPU batch evaluation plan without executing the GPU solve.
    Returns:
        (plan, results)
        - If `plan` is not None, caller must run a GPU solve and then call
          `finalize_gpu_batch_eval_plan(plan, gpu_results)`.
        - If `plan` is None, `results` is the fully evaluated result list.
    """
    if not population:
        return None, []
    use_cache = genome_key_fn is not None and evaluation_cache is not None
    cached_results = {}
    uncached_genomes = []
    uncached_indices = []
    for i, genome in enumerate(population):
        if use_cache:
            key = genome_key_fn(genome)
            if key in evaluation_cache:
                cached_results[i] = evaluation_cache[key]
                continue
        uncached_genomes.append(genome)
        uncached_indices.append(i)
    if not uncached_genomes:
        return None, [cached_results[i] for i in range(len(population))]
    sel_color = cfg_data["selected_color"]
    all_stats = []
    for genome in uncached_genomes:
        current_stats = base_stats_fixed.copy()
        for item in genome:
            for k, v in item.items():
                if k not in SKIP_ITEM_KEYS:
                    current_stats[k] = current_stats.get(k, 0) + v
        all_stats.append(current_stats)
    config_sig = (
        cfg_data["user_ft"],
        cfg_data["user_ff"],
        cfg_data["user_pp"],
        cfg_data["user_cm"],
        cfg_data["user_fm"],
        cfg_data["static_elem_input"],
    )
    sig_to_result = {}
    unique_stats = []  # [(sig, representative_stats)]
    sig_to_unique_idx = {}  # sig -> unique_idx
    unique_members = []  # unique_idx -> [uncached_idx]
    for i, stats in enumerate(all_stats):
        base_sig = stats_signature(stats, calc_song, sel_color)
        sig = base_sig + config_sig
        cached = GEM_SOLVER_CACHE.get(sig)
        if cached is not None:
            sig_to_result[i] = cached
            continue
        unique_idx = sig_to_unique_idx.get(sig)
        if unique_idx is None:
            unique_idx = len(unique_stats)
            sig_to_unique_idx[sig] = unique_idx
            unique_stats.append((sig, stats))
            unique_members.append([i])
        else:
            unique_members[unique_idx].append(i)
    if not unique_stats:
        plan = GpuBatchEvalPlan(
            population=population,
            base_stats_fixed=base_stats_fixed,
            cfg_data=cfg_data,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            genome_key_fn=genome_key_fn,
            evaluation_cache=evaluation_cache,
            use_cache=use_cache,
            cached_results=cached_results,
            uncached_genomes=uncached_genomes,
            uncached_indices=uncached_indices,
            all_stats=all_stats,
            sel_color=sel_color,
            config_sig=config_sig,
            sig_to_result=sig_to_result,
            unique_stats=unique_stats,
            unique_members=unique_members,
            genome_stats_list=[],
            flags={},
        )
        return None, finalize_gpu_batch_eval_plan(plan, gpu_results=None)
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    n_unique = len(unique_stats)
    genome_stats_np = np.empty((n_unique, 7), dtype=np.int16)
    for unique_idx, (_sig, stats) in enumerate(unique_stats):
        row = build_solver_stat_row(
            stats,
            cfg_data,
            primary_color=str(p_color or ""),
            secondary_color=str(s_color or ""),
            fallback_selected_color=str(sel_color or ""),
        )
        genome_stats_np[unique_idx, 0] = int(row[0])
        genome_stats_np[unique_idx, 1] = int(row[1])
        genome_stats_np[unique_idx, 2] = int(row[2])
        genome_stats_np[unique_idx, 3] = int(row[3])
        genome_stats_np[unique_idx, 4] = int(row[4])
        genome_stats_np[unique_idx, 5] = int(row[5])
        genome_stats_np[unique_idx, 6] = int(row[6])
    flags = build_color_flags(p_color, s_color, sel_color)
    plan = GpuBatchEvalPlan(
        population=population,
        base_stats_fixed=base_stats_fixed,
        cfg_data=cfg_data,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        genome_key_fn=genome_key_fn,
        evaluation_cache=evaluation_cache,
        use_cache=use_cache,
        cached_results=cached_results,
        uncached_genomes=uncached_genomes,
        uncached_indices=uncached_indices,
        all_stats=all_stats,
        sel_color=sel_color,
        config_sig=config_sig,
        sig_to_result=sig_to_result,
        unique_stats=unique_stats,
        unique_members=unique_members,
        genome_stats_list=genome_stats_np,
        flags=flags,
    )
    return plan, None


def finalize_gpu_batch_eval_plan(plan: GpuBatchEvalPlan, gpu_results: Optional[list]) -> list:
    """
    Finalize a prepared GPU batch evaluation plan using optional GPU results.
    Args:
        plan: Prepared plan from `prepare_gpu_batch_eval_plan`
        gpu_results: list of (score, ft, ff, pp, cm, fm, ov) tuples, aligned with plan.unique_stats
    Returns:
        list of evaluation dicts aligned with `plan.population`
    """
    population = plan.population
    calc_song = plan.calc_song
    sel_color = plan.sel_color
    sig_to_result = dict(plan.sig_to_result or {})
    if plan.unique_stats:
        if gpu_results is None:
            raise RuntimeError("GPU batch evaluation produced no results.")
        if len(gpu_results) < len(plan.unique_stats):
            raise RuntimeError(f"GPU returned {len(gpu_results)}/{len(plan.unique_stats)} results.")
        for unique_idx, (sig, _rep_stats) in enumerate(plan.unique_stats):
            score, g_ft, g_ff, g_pp, g_cm, g_fm, g_ov = gpu_results[unique_idx]
            score = int(score)
            g_ft = int(g_ft)
            g_ff = int(g_ff)
            g_pp = int(g_pp)
            g_cm = int(g_cm)
            g_fm = int(g_fm)
            g_ov = int(g_ov)
            members = plan.unique_members[unique_idx] if unique_idx < len(plan.unique_members) else []
            cache_written = False
            for i in members:
                if i in sig_to_result:
                    continue
                stats = plan.all_stats[i]
                final_stats = apply_gems_to_base_stats(
                    stats,
                    sel_color,
                    g_ft,
                    g_ff,
                    g_pp,
                    g_cm,
                    g_fm,
                    g_ov,
                )
                res = {
                    "Score": score,
                    "FT": g_ft,
                    "FF": g_ff,
                    "GemCounts": {
                        "Perfect Points": g_pp,
                        "Combo Multiplier": g_cm,
                        "Fever Multiplier": g_fm,
                        "Element": g_ov,
                    },
                    "Stats": final_stats,
                    "Selected Element": sel_color,
                }
                sig_to_result[i] = res
                if not cache_written:
                    GEM_SOLVER_CACHE[sig] = res
                    cache_written = True
    uncached_results = {}
    for i, (genome, stats) in enumerate(zip(plan.uncached_genomes, plan.all_stats)):
        res = sig_to_result.get(i)
        if res is None:
            base_sig = stats_signature(stats, calc_song, sel_color)
            sig = base_sig + plan.config_sig
            res = GEM_SOLVER_CACHE.get(sig)
            if res is None:
                raise RuntimeError(f"Missing GEM_SOLVER_CACHE entry for sig={sig!r}.")
            sig_to_result[i] = res
        gear_part = genome[:6]
        mini_part = genome[6:]
        mini_names = [m["Name"] for m in mini_part]
        base_score = res["Score"]
        res["BaseScore"] = base_score
        result = {
            "Score": base_score,
            "BaseScore": base_score,
            "Genome": genome,
            "Gear": gear_part,
            "Minis": mini_part,
            "MiniNames": mini_names,
            "Data": res,
        }
        uncached_results[plan.uncached_indices[i]] = result
        if plan.use_cache:
            key = plan.genome_key_fn(genome)
            plan.evaluation_cache[key] = result
    all_results = []
    for i in range(len(population)):
        if i in plan.cached_results:
            all_results.append(plan.cached_results[i])
        else:
            all_results.append(uncached_results[i])
    return all_results


def worker_coevolution_evaluate(args):
    """
    Evaluates a Co-Evolution Individual (genome = gear + minis).
    Uses a stat-signature cache: if multiple gear+mini combinations produce
    the same effective stats for the song's Primary/Secondary/Selected paths,
    we reuse the gem solver result instead of recomputing.
    This is called in parallel by the genetic algorithm.
    Args:
        args: Tuple of (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
    Returns:
        dict: Evaluation result with score, genome, gear, minis, and data
    """
    (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays) = args
    current_stats = base_stats_fixed.copy()
    cs = current_stats
    cs_get = cs.get
    for item in genome:
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                cs[k] = cs_get(k, 0) + v
    sel_color = cfg_data["selected_color"]
    sig = stats_signature(current_stats, calc_song, sel_color)
    cached = GEM_SOLVER_CACHE.get(sig)
    if cached is None:
        res = solve_best_fever_combination(
            None,
            current_stats,
            calc_song,
            ref_arrays,
            silent=True,
            override_cfg=cfg_data,
        )
        GEM_SOLVER_CACHE[sig] = res
    else:
        res = cached
    gear_part = genome[:6]
    mini_part = genome[6:]
    mini_names = [m["Name"] for m in mini_part]
    base_score = res["Score"]
    res["BaseScore"] = base_score
    return {
        "Score": base_score,  # Used for GA selection
        "BaseScore": base_score,  # True base score (all perfects)
        "Genome": genome,
        "Gear": gear_part,
        "Minis": mini_part,
        "MiniNames": mini_names,
        "Data": res,
    }


def batch_evaluate_genomes(
    population: list,
    base_stats_fixed: dict,
    cfg_data: dict,
    calc_song: dict,
    ref_arrays: dict,
    genome_key_fn=None,
    evaluation_cache: dict = None,
    registry=None,
) -> list:
    """
    Evaluate a population with caching + GPU acceleration.
    This wraps `prepare_gpu_batch_eval_plan()` + `finalize_gpu_batch_eval_plan()` and keeps the
    GPU dispatch logic in one place (worker-mode IPC + in-process registry dispatch).
    GPU execution requires a registry-capable solver payload. Callers must pass an
    ItemRegistry via `registry`.
    """
    if not population:
        return []
    plan, results = prepare_gpu_batch_eval_plan(
        population,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
        genome_key_fn=genome_key_fn,
        evaluation_cache=evaluation_cache,
    )
    if plan is None:
        return results or []
    gpu_results = None
    if plan.unique_stats:
        from ..gpu_executor import is_gpu_worker_mode
        if not registry_batch_solve_supported(registry):
            raise RuntimeError("GPU registry solve is required for batch_evaluate_genomes; missing ItemRegistry.")
        try:
            song_slot = int((plan.calc_song or {}).get("_gpu_song_slot", 0) or 0)
        except Exception as e:
            logger.debug(f"genome_evaluation:batch_evaluate_genomes: {e}")
            song_slot = 0
        try:
            if is_gpu_worker_mode():
                request = build_registry_solve_request(
                    plan=plan,
                    registry=registry,
                    song_slot=int(song_slot),
                    timeline_grid=plan.calc_song,
                )
                if request is None:
                    raise RuntimeError("Failed to build registry solve request for worker-mode GPU dispatch.")
                gpu_results = dispatch_registry_solve(request)
            else:
                request = build_registry_solve_request(
                    plan=plan,
                    registry=registry,
                    song_slot=int(song_slot),
                    timeline_grid=plan.calc_song,
                )
                if request is None:
                    raise RuntimeError("Failed to build registry solve request for in-process GPU dispatch.")
                gpu_results = dispatch_registry_solve(request)
        except Exception as e:
            raise RuntimeError(f"GPU path failed: {type(e).__name__}: {e}") from e
    return finalize_gpu_batch_eval_plan(plan, gpu_results)
