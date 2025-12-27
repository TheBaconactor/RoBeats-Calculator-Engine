"""
In-flight (resumable) co-evolution GA driver.

This is an opt-in, generator-based variant of the CPU GA path that yields at
GPU-evaluation boundaries. It is intended for a multi-song in-flight
orchestrator that can interleave many songs while the GPU executor stays busy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, Optional, Any

from gear_optimizer.core.constants import (
    GA_MUTATION_RATE,
    GA_POPULATION_SIZE,
    GA_MULTI_RUNS_DEFAULT,
    TOTAL_GEM_BUDGET,
    GEM_SCALE_FEVER,
)
from gear_optimizer.core.utils import safe_int
from gear_optimizer.data.models import GASettings
from gear_optimizer.solver.scoring.genome_evaluation import (
    GpuBatchEvalPlan,
    prepare_gpu_batch_eval_plan,
    finalize_gpu_batch_eval_plan,
)


@dataclass(frozen=True)
class SolveGenomesJob:
    """A request to evaluate a population (unique stat signatures) on the GPU."""

    plan: GpuBatchEvalPlan
    payload: dict


@dataclass(frozen=True)
class InflightGAResult:
    best_score: int
    best_genome: list
    best_data: dict
    all_evaluated: list


def solve_coevolution_genetic_inflight(
    *,
    cfg: Any,
    ga_depth: int,
    base_stats_fixed: dict,
    calc_song: dict,
    ref_arrays: dict,
    all_gears: list,
    all_minis: list,
    gears_by_name: dict,
    minis_by_name: dict,
    optimize_gear: bool,
    optimize_minis: bool,
    fixed_gear: list,
    fixed_minis: list,
    known_loadouts: Optional[dict],
    db_seed: Optional[dict],
    song_slot: int,
    status_cb=None,
) -> Generator[SolveGenomesJob, Optional[list], InflightGAResult]:
    """
    Generator-based GA solver that yields GPU solve jobs and resumes with their results.

    Notes/limitations (initial version):
    - CPU GA path only (does not support GPU-native GA).
    - Memetic search + polishing are disabled to keep the yield surface minimal.
      (They can be added later by turning `batch_evaluator` into a resumable step.)
    """
    ga_settings = GASettings.from_cfg(cfg) if cfg is not None else GASettings.from_cfg(None)

    # Disable GPU-heavy local search in the first in-flight implementation.
    ga_settings = GASettings(
        db_seed_prob=ga_settings.db_seed_prob,
        fixed_seed_copies=ga_settings.fixed_seed_copies,
        memetic_elites=0,
        memetic_steps=0,
        memetic_top_gear=ga_settings.memetic_top_gear,
        memetic_top_minis=ga_settings.memetic_top_minis,
        multi_start=ga_settings.multi_start,
        deep_mining_enabled=ga_settings.deep_mining_enabled,
        heuristic_mode=ga_settings.heuristic_mode,
        allow_3_swap=False,
        gear_rank_max=ga_settings.gear_rank_max,
        mini_rank_max=ga_settings.mini_rank_max,
    )

    # Import helper functions lazily to avoid import-time costs in orchestration loops.
    from gear_optimizer.helpers.ga_helpers import (
        create_genome_functions,
        create_evaluation_functions,
        compute_dynamic_mutation,
        initialize_pools,
        build_initial_population,
        perform_crossover_mutation,
        update_mutation_and_diversity,
    )

    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    selected_color = p_color

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    pools = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)
    if pools is None:
        raise RuntimeError("initialize_pools returned None (in-flight GA requires pools)")

    # `initialize_pools` returns (gear_pool, mini_pool, total_before, total_after[, whitelist]).
    if len(pools) >= 2:
        gear_pool = pools[0]
        mini_pool = pools[1]

    cfg_data = {
        "selected_color": selected_color,
        "use_gpu": True,
        "use_gpu_native": False,
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0)),
    }

    cache_hits_tracker = [0]
    (
        _score_candidate,
        genome_key,
        check_persistent_cache,
        _evaluate_genome_local,
        evaluation_cache,
        _batch_evaluator,
    ) = create_evaluation_functions(
        p_color,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
        known_loadouts,
        cache_hits_tracker,
        getattr(ga_settings, "heuristic_mode", "modern"),
    )

    # Rank caches for genome factory.
    gear_rank_max = getattr(ga_settings, "gear_rank_max", 40)
    mini_rank_max = getattr(ga_settings, "mini_rank_max", 40)
    gear_rank_cache = {s: gear_pool[s][:] for s in slots if s in gear_pool}
    for s in list(gear_rank_cache.keys()):
        gear_rank_cache[s] = sorted(gear_rank_cache[s], key=_score_candidate, reverse=True)[:gear_rank_max]
    mini_rank_cache = sorted(mini_pool, key=_score_candidate, reverse=True)[:mini_rank_max]

    (
        create_random_genome,
        create_heuristic_genome,
        reconstruct_genome_from_db_list,
        build_seed_list_from_record,
        mutate_genome_once,
    ) = create_genome_functions(
        gear_pool,
        mini_pool,
        gear_rank_cache,
        mini_rank_cache,
        gears_by_name,
        minis_by_name,
        slots,
        optimize_gear,
        optimize_minis,
        fixed_gear,
        fixed_minis,
    )

    num_runs = max(1, int(getattr(ga_settings, "multi_start", GA_MULTI_RUNS_DEFAULT) or 1))
    gens_per_run = max(1, (int(ga_depth) + num_runs - 1) // num_runs)

    best_global_score = -1
    best_global_genome: list = []
    best_global_data: dict = {}
    run_results: list[tuple[int, list, dict]] = []

    for run_idx in range(num_runs):
        if status_cb:
            status_cb(f"Run {run_idx + 1}/{num_runs} starting")

        population = build_initial_population(
            create_random_genome,
            create_heuristic_genome,
            reconstruct_genome_from_db_list,
            build_seed_list_from_record,
            mutate_genome_once,
            db_seed=db_seed,
            ga_settings=ga_settings,
            fixed_gear=fixed_gear,
            fixed_minis=fixed_minis,
            force_db_seed=False,
        )

        best_run_score = -1
        last_improvement_gen = 0
        base_stagnation_limit = max(8, gens_per_run // 2)
        explore_stagnation_limit = max(8, gens_per_run // 3)
        mutation_rate = GA_MUTATION_RATE
        current_run_gens = gens_per_run
        cache_hits_tracker[0] = 0
        generation = 0
        current_mutation_rate = mutation_rate

        while generation < current_run_gens:
            generation += 1

            # Persistent cache check (matches evaluate_population_parallel GPU path).
            key_to_genome = {}
            for genome in population:
                k = genome_key(genome)
                if k in key_to_genome:
                    continue
                key_to_genome[k] = genome
                if k not in evaluation_cache:
                    cached_res = check_persistent_cache(genome)
                    if cached_res:
                        evaluation_cache[k] = cached_res
                        cache_hits_tracker[0] += 1

            plan, immediate = prepare_gpu_batch_eval_plan(
                population,
                base_stats_fixed,
                cfg_data,
                calc_song,
                ref_arrays,
                genome_key_fn=genome_key,
                evaluation_cache=evaluation_cache,
            )

            if plan is None:
                results = immediate or []
            else:
                payload = {
                    "genome_stats_list": plan.genome_stats_list,
                    "timeline_grid": calc_song,
                    "is_p_ft": plan.flags["is_p_ft"],
                    "is_s_ft": plan.flags["is_s_ft"],
                    "is_p_ff": plan.flags["is_p_ff"],
                    "is_s_ff": plan.flags["is_s_ff"],
                    "is_p_pp": plan.flags["is_p_pp"],
                    "is_s_pp": plan.flags["is_s_pp"],
                    "is_p_cm": plan.flags["is_p_cm"],
                    "is_s_cm": plan.flags["is_s_cm"],
                    "is_p_fm": plan.flags["is_p_fm"],
                    "is_s_fm": plan.flags["is_s_fm"],
                    "is_p_ov": plan.flags["is_p_ov"],
                    "is_s_ov": plan.flags["is_s_ov"],
                    "ref_arrays": ref_arrays,
                    "total_budget": int(TOTAL_GEM_BUDGET),
                    "gem_scale_fever": int(GEM_SCALE_FEVER),
                    "song_slot": int(song_slot),
                }
                gpu_results = yield SolveGenomesJob(plan=plan, payload=payload)
                results = finalize_gpu_batch_eval_plan(plan, gpu_results=gpu_results)

            results.sort(key=lambda x: x["Score"], reverse=True)
            if not results:
                break

            best_cand = results[0]
            if best_cand["Score"] > best_run_score:
                best_run_score = best_cand["Score"]
                last_improvement_gen = generation

            if best_cand["Score"] > best_global_score:
                best_global_score = best_cand["Score"]
                best_global_genome = best_cand["Genome"]
                best_global_data = best_cand["Data"]

            population = perform_crossover_mutation(
                results,
                create_random_genome,
                mini_pool,
                gear_pool,
                slots,
                optimize_gear,
                optimize_minis,
                fixed_minis,
                current_mutation_rate,
                global_elites=None,
            )

            current_mutation_rate, current_run_gens = compute_dynamic_mutation(
                mutation_rate,
                cache_hits_tracker[0],
                generation,
                current_run_gens,
                gens_per_run,
                ga_settings,
            )

            total_evals_so_far = generation * GA_POPULATION_SIZE
            hit_ratio = cache_hits_tracker[0] / max(1, total_evals_so_far)
            exploration_boost = min(0.2, hit_ratio * 0.5) if ga_settings.deep_mining_enabled else 0.0

            stagnation_limit = base_stagnation_limit
            if best_global_score > 0 and best_run_score > 0 and best_run_score < best_global_score:
                stagnation_limit = explore_stagnation_limit

            population, mutation_rate, last_improvement_gen = update_mutation_and_diversity(
                population,
                results,
                generation,
                last_improvement_gen,
                stagnation_limit,
                mutation_rate,
                create_random_genome,
                create_heuristic_genome,
                run_idx,
                current_mutation_rate,
                exploration_boost,
                mini_pool=mini_pool,
                gear_pool=gear_pool,
                slots=slots,
                optimize_gear=optimize_gear,
                optimize_minis=optimize_minis,
            )

        if results:
            run_results.append((results[0]["Score"], results[0]["Genome"], results[0]["Data"]))

    for score, genome, data in run_results:
        if score > best_global_score:
            best_global_score = score
            best_global_genome = genome
            best_global_data = data

    all_evaluated = list(evaluation_cache.values())
    evaluation_cache.clear()

    return InflightGAResult(
        best_score=int(best_global_score),
        best_genome=list(best_global_genome or []),
        best_data=dict(best_global_data or {}),
        all_evaluated=all_evaluated,
    )
