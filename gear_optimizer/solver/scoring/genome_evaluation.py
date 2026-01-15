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
from typing import Optional, Callable

import numpy as np

from ..base_stats import build_base_fixed_stats_array
from ...core.constants import (
    TOTAL_GEM_BUDGET,
    GEM_SCALE_NORMAL,
    GEM_SCALE_FEVER,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
)
from ...core.color_flags import build_color_flags
from ...core.constants import SKIP_ITEM_KEYS
from ...core.env_config import ENV
from ...core.utils import stats_signature

from .gpu_solver import _GPU_LOCK, GEM_SOLVER_CACHE
from .fever_solver import solve_best_fever_combination


@dataclass
class GpuBatchEvalPlan:
    """Prepared (CPU-side) batch evaluation plan with a deferred GPU solve step."""

    population: list
    base_stats_fixed: dict
    cfg_data: dict
    calc_song: dict
    ref_arrays: dict

    # Caching inputs (optional)
    genome_key_fn: Optional[Callable]
    evaluation_cache: Optional[dict]
    use_cache: bool

    # Partitioning
    cached_results: dict
    uncached_genomes: list
    uncached_indices: list

    # Per-uncached genome stats aggregation
    all_stats: list
    sel_color: str
    config_sig: tuple

    # Unique-signature grouping
    sig_to_result: dict
    unique_stats: list
    unique_members: list

    # GPU request payload parts
    genome_stats_list: list
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

    use_gpu = bool(cfg_data.get("use_gpu", False))
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

    # Aggregate stats for each uncached genome (simple dict accumulation)
    all_stats = []
    for genome in uncached_genomes:
        current_stats = base_stats_fixed.copy()
        for item in genome:
            for k, v in item.items():
                if k not in SKIP_ITEM_KEYS:
                    current_stats[k] = current_stats.get(k, 0) + v
        all_stats.append(current_stats)

    # Fix regression: cache key must include user gem config.
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

    # No GPU work needed (everything cache hit) or GPU disabled: finalize synchronously.
    if (not unique_stats) or (not use_gpu):
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

    # Build genome stats list for GPU kernel (one entry per unique signature).
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")

    user_ft = cfg_data["user_ft"]
    user_ff = cfg_data["user_ff"]
    user_pp = cfg_data["user_pp"]
    user_cm = cfg_data["user_cm"]
    user_fm = cfg_data["user_fm"]
    static_elem_input = cfg_data["static_elem_input"]

    genome_stats_list = []
    for _unique_idx, (sig, stats) in enumerate(unique_stats):
        base_pp = stats.get("Perfect Points", 0) - user_pp * GEM_SCALE_NORMAL
        base_cm = stats.get("Combo Multiplier", 0) - user_cm * GEM_SCALE_NORMAL
        base_fm = stats.get("Fever Multiplier", 0) - user_fm * GEM_SCALE_FEVER
        base_ft_stat = stats.get("Fever Time", 0) - user_ft * GEM_SCALE_FEVER
        base_ff_stat = stats.get("Fever Fill Rate", 0) - user_ff * GEM_SCALE_FEVER

        base_beat = stats.get("Beat", 0) - user_ft * GEM_STAT_TO_ELEMENT_SCALE
        base_vibe = stats.get("Vibe", 0) - user_ff * GEM_STAT_TO_ELEMENT_SCALE
        base_rush = stats.get("Rush", 0) - user_fm * GEM_STAT_TO_ELEMENT_SCALE
        base_flow = stats.get("Flow", 0) - user_cm * GEM_STAT_TO_ELEMENT_SCALE
        base_chill = stats.get("Chill", 0) - user_pp * GEM_STAT_TO_ELEMENT_SCALE

        if sel_color == "Beat":
            base_beat -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Vibe":
            base_vibe -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Rush":
            base_rush -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Flow":
            base_flow -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Chill":
            base_chill -= static_elem_input * ELEMENTAL_GEM_SCALE

        color_vals = {
            "Beat": base_beat,
            "Vibe": base_vibe,
            "Rush": base_rush,
            "Flow": base_flow,
            "Chill": base_chill,
        }
        base_p_val = color_vals.get(p_color, 0)
        base_s_val = color_vals.get(s_color, 0)

        genome_stats_list.append(
            {
                "base_pp": int(base_pp),
                "base_cm": int(base_cm),
                "base_fm": int(base_fm),
                "base_p_val": int(base_p_val),
                "base_s_val": int(base_s_val),
                "base_ft_stat": int(base_ft_stat),
                "base_ff_stat": int(base_ff_stat),
            }
        )

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
        genome_stats_list=genome_stats_list,
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
    cfg_data = plan.cfg_data
    calc_song = plan.calc_song
    ref_arrays = plan.ref_arrays
    sel_color = plan.sel_color
    use_gpu_requested = bool((cfg_data or {}).get("use_gpu", False))

    sig_to_result = dict(plan.sig_to_result or {})

    if plan.unique_stats:
        if use_gpu_requested:
            if gpu_results is None:
                raise RuntimeError("GPU batch evaluation produced no results.")
            if len(gpu_results) < len(plan.unique_stats):
                raise RuntimeError(f"GPU returned {len(gpu_results)}/{len(plan.unique_stats)} results.")

        for unique_idx, (sig, rep_stats) in enumerate(plan.unique_stats):
            if gpu_results is None or unique_idx >= len(gpu_results):
                if use_gpu_requested:
                    raise RuntimeError(f"Missing GPU result for unique_idx={unique_idx}: sig={sig!r}")
                # CPU reference path: evaluate missing signatures on CPU.
                override_cfg = dict(cfg_data or {})
                override_cfg["use_gpu"] = False
                res = solve_best_fever_combination(
                    None,
                    rep_stats,
                    calc_song,
                    ref_arrays,
                    silent=True,
                    override_cfg=override_cfg,
                )
                GEM_SOLVER_CACHE[sig] = res
                members = plan.unique_members[unique_idx] if unique_idx < len(plan.unique_members) else []
                for i in members:
                    sig_to_result[i] = res
                continue

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
                final_stats = stats.copy()
                final_stats["Fever Time"] = final_stats.get("Fever Time", 0) + g_ft * GEM_SCALE_FEVER
                final_stats["Fever Fill Rate"] = final_stats.get("Fever Fill Rate", 0) + g_ff * GEM_SCALE_FEVER
                final_stats["Perfect Points"] = final_stats.get("Perfect Points", 0) + g_pp * GEM_SCALE_NORMAL
                final_stats["Combo Multiplier"] = final_stats.get("Combo Multiplier", 0) + g_cm * GEM_SCALE_NORMAL
                final_stats["Fever Multiplier"] = final_stats.get("Fever Multiplier", 0) + g_fm * GEM_SCALE_FEVER
                final_stats["Chill"] = final_stats.get("Chill", 0) + g_pp * GEM_STAT_TO_ELEMENT_SCALE
                final_stats["Flow"] = final_stats.get("Flow", 0) + g_cm * GEM_STAT_TO_ELEMENT_SCALE
                final_stats["Rush"] = final_stats.get("Rush", 0) + g_fm * GEM_STAT_TO_ELEMENT_SCALE
                final_stats["Beat"] = final_stats.get("Beat", 0) + g_ft * GEM_STAT_TO_ELEMENT_SCALE
                final_stats["Vibe"] = final_stats.get("Vibe", 0) + g_ff * GEM_STAT_TO_ELEMENT_SCALE
                if sel_color in final_stats:
                    final_stats[sel_color] = final_stats.get(sel_color, 0) + g_ov * ELEMENTAL_GEM_SCALE

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
                if ENV.gpu_strict and use_gpu_requested:
                    raise RuntimeError(f"Missing GEM_SOLVER_CACHE entry for sig={sig!r} (strict mode).")
                # Safety-net: force CPU-only evaluation for missing signature entries.
                override_cfg = dict(cfg_data or {})
                override_cfg["use_gpu"] = False
                res = solve_best_fever_combination(
                    None,
                    stats,
                    calc_song,
                    ref_arrays,
                    silent=True,
                    override_cfg=override_cfg,
                )
                GEM_SOLVER_CACHE[sig] = res
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

    # Aggregate stats from all items in genome
    for item in genome:
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                cs[k] = cs_get(k, 0) + v

    # Check stat-signature cache before calling the expensive gem solver
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

    # CRITICAL: Inject BaseScore into res so it propagates through all caching layers
    # and reaches build_db_payload for correct DB storage. Without this, the heuristic
    # score would be stored instead of the true base score.
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
    Evaluate a population with caching + optional GPU acceleration.

    This wraps `prepare_gpu_batch_eval_plan()` + `finalize_gpu_batch_eval_plan()` and keeps the
    GPU dispatch logic in one place (worker-mode IPC, in-process direct calls, and an optional
    ItemRegistry fast path for GPU-side stat aggregation).
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
    if plan.unique_stats and bool(plan.cfg_data.get("use_gpu", False)):
        from ..gpu_executor import (
            is_gpu_worker_mode,
            submit_gpu_solve_genomes,
            submit_gpu_solve_genomes_from_registry,
        )
        from ..fever_timeline import get_song_timeline_grid
        from ..taichi_gem_solver import solve_genomes_parallel, solve_genomes_with_ftff

        flags = plan.flags

        try:
            if is_gpu_worker_mode():
                # IPC route to GPU executor (parallel song processing).
                # Pass lightweight `calc_song` dict to avoid pickling a full SongTimelineGrid.
                if registry is not None:
                    # Prefer the GPU-resident stat aggregation path (avoid CPU-side genome_stats uploads).
                    representative_genomes = [
                        plan.uncached_genomes[plan.unique_members[unique_idx][0]]
                        for unique_idx in range(len(plan.unique_stats))
                    ]
                    population_indices = registry.encode_population(representative_genomes)
                    gpu_arrays = registry.to_gpu_arrays()
                    base_stats_arr, _ = build_base_fixed_stats_array(
                        plan.base_stats_fixed,
                        plan.cfg_data,
                        fallback_selected_color=plan.sel_color,
                    )

                    gpu_results = submit_gpu_solve_genomes_from_registry(
                        population_indices,
                        gpu_arrays["item_stats"],
                        gpu_arrays["slot_start"],
                        gpu_arrays["slot_count"],
                        base_stats_arr,
                        plan.calc_song,
                        int(flags.get("is_p_ft", 0)),
                        int(flags.get("is_s_ft", 0)),
                        int(flags.get("is_p_ff", 0)),
                        int(flags.get("is_s_ff", 0)),
                        int(flags.get("is_p_pp", 0)),
                        int(flags.get("is_s_pp", 0)),
                        int(flags.get("is_p_cm", 0)),
                        int(flags.get("is_s_cm", 0)),
                        int(flags.get("is_p_fm", 0)),
                        int(flags.get("is_s_fm", 0)),
                        int(flags.get("is_p_ov", 0)),
                        int(flags.get("is_s_ov", 0)),
                        plan.ref_arrays,
                        total_budget=TOTAL_GEM_BUDGET,
                        gem_scale_fever=GEM_SCALE_FEVER,
                    )
                else:
                    gpu_results = submit_gpu_solve_genomes(
                        plan.genome_stats_list,
                        plan.calc_song,
                        int(flags.get("is_p_ft", 0)),
                        int(flags.get("is_s_ft", 0)),
                        int(flags.get("is_p_ff", 0)),
                        int(flags.get("is_s_ff", 0)),
                        int(flags.get("is_p_pp", 0)),
                        int(flags.get("is_s_pp", 0)),
                        int(flags.get("is_p_cm", 0)),
                        int(flags.get("is_s_cm", 0)),
                        int(flags.get("is_p_fm", 0)),
                        int(flags.get("is_s_fm", 0)),
                        int(flags.get("is_p_ov", 0)),
                        int(flags.get("is_s_ov", 0)),
                        plan.ref_arrays,
                        total_budget=TOTAL_GEM_BUDGET,
                        gem_scale_fever=GEM_SCALE_FEVER,
                    )
            else:
                # In-process path:
                # - Default: reuse cached per-song CPU timeline grid (then upload to GPU).
                # - GPU_TIMELINE_ONLY=1: always use GPU timeline precompute path by passing calc_song dict.
                prefer_gpu_timeline = bool(ENV.gpu_timeline_only)
                prefer_ftff_solver = bool(ENV.gpu_use_ftff_solver)
                song_slot = 0
                if prefer_gpu_timeline:
                    try:
                        song_slot = int((plan.calc_song or {}).get("_gpu_song_slot", 0) or 0)
                    except Exception:
                        song_slot = 0
                if not prefer_gpu_timeline:
                    grid = get_song_timeline_grid(plan.calc_song, plan.ref_arrays)
                    grid.precompute_all()

                if registry is not None:
                    # GPU-resident aggregation path: encode representative genomes and aggregate stats on GPU.
                    from ..taichi_gem.api import (
                        ga_upload_base_fixed_stats,
                        ga_upload_item_stats,
                        solve_genomes_from_registry,
                    )

                    representative_genomes = [
                        plan.uncached_genomes[plan.unique_members[unique_idx][0]]
                        for unique_idx in range(len(plan.unique_stats))
                    ]
                    population_indices = registry.encode_population(representative_genomes)

                    gpu_arrays = registry.to_gpu_arrays()
                    ga_upload_item_stats(
                        gpu_arrays["item_stats"],
                        gpu_arrays["slot_start"],
                        gpu_arrays["slot_count"],
                    )

                    base_stats_arr, _ = build_base_fixed_stats_array(
                        plan.base_stats_fixed,
                        plan.cfg_data,
                        fallback_selected_color=plan.sel_color,
                    )

                    ga_upload_base_fixed_stats(base_stats_arr)

                    with _GPU_LOCK:
                        gpu_results = solve_genomes_from_registry(
                            population_indices,
                            plan.calc_song if prefer_gpu_timeline else grid,
                            int(flags.get("is_p_ft", 0)),
                            int(flags.get("is_s_ft", 0)),
                            int(flags.get("is_p_ff", 0)),
                            int(flags.get("is_s_ff", 0)),
                            int(flags.get("is_p_pp", 0)),
                            int(flags.get("is_s_pp", 0)),
                            int(flags.get("is_p_cm", 0)),
                            int(flags.get("is_s_cm", 0)),
                            int(flags.get("is_p_fm", 0)),
                            int(flags.get("is_s_fm", 0)),
                            int(flags.get("is_p_ov", 0)),
                            int(flags.get("is_s_ov", 0)),
                            plan.ref_arrays,
                            total_budget=TOTAL_GEM_BUDGET,
                            gem_scale_fever=GEM_SCALE_FEVER,
                            song_slot=int(song_slot),
                        )
                else:
                    with _GPU_LOCK:
                        solve_fn = solve_genomes_with_ftff if prefer_ftff_solver else solve_genomes_parallel
                        gpu_results = solve_fn(
                            plan.genome_stats_list,
                            plan.calc_song if prefer_gpu_timeline else grid,
                            int(flags.get("is_p_ft", 0)),
                            int(flags.get("is_s_ft", 0)),
                            int(flags.get("is_p_ff", 0)),
                            int(flags.get("is_s_ff", 0)),
                            int(flags.get("is_p_pp", 0)),
                            int(flags.get("is_s_pp", 0)),
                            int(flags.get("is_p_cm", 0)),
                            int(flags.get("is_s_cm", 0)),
                            int(flags.get("is_p_fm", 0)),
                            int(flags.get("is_s_fm", 0)),
                            int(flags.get("is_p_ov", 0)),
                            int(flags.get("is_s_ov", 0)),
                            plan.ref_arrays,
                            total_budget=TOTAL_GEM_BUDGET,
                            gem_scale_fever=GEM_SCALE_FEVER,
                            song_slot=int(song_slot),
                        )
        except Exception as e:
            raise RuntimeError(f"GPU path failed: {type(e).__name__}: {e}") from e

    return finalize_gpu_batch_eval_plan(plan, gpu_results)
