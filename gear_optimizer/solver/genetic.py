"""
Genetic algorithm solver for gear and mini co-evolution.

This module contains the main GA that optimizes both gear (6 slots) and minis (3 slots)
simultaneously to find optimal loadouts. Uses tournament selection, crossover, mutation,
and memetic local search.

The main function solve_coevolution_genetic() has been refactored to use helper functions
from helpers.ga_helpers for improved modularity and maintainability.
"""
import os
import random

from ..core.constants import (
    GA_POPULATION_SIZE,
    GA_GENERATIONS,
    GA_MUTATION_RATE,
    GA_ELITISM,
    GA_MUTATION_RATE_MAX,
    GA_MULTI_RUNS_DEFAULT,
)
from ..core.utils import prune_dominated_gear, safe_int
from ..data.database import get_loadout_hash
from .scoring import worker_coevolution_evaluate, GEM_SOLVER_CACHE, FG_CACHE, FEVER_TIMELINE_CACHE
from ..data.models import GASettings
from ..helpers.ga_helpers import (
    initialize_pools,
    create_genome_functions,
    create_evaluation_functions,
    create_local_search_function,
    build_initial_population,
    perform_crossover_mutation,
    evaluate_population_parallel,
    update_mutation_and_diversity,
    compute_dynamic_mutation,
)


def solve_coevolution_genetic(
    cfg,
    base_stats_fixed,
    paths,
    calc_song,
    ref_arrays,
    all_gears,
    all_minis,
    gears_by_name,
    minis_by_name,
    optimize_gear=True,
    optimize_minis=True,
    fixed_gear=None,
    fixed_minis=None,
    ga_depth=75,
    db_seed=None,
    ga_settings=None,
    status_cb=None,
    executor=None,
    known_loadouts=None,
):
    """
    Main genetic algorithm solver for gear and mini co-evolution.

    Features:
    - Multi-start restarts for better global search
    - Memetic local search on elite candidates
    - Deep mining: extends search when cache hits indicate known territory
    - Dynamic mutation rate based on stagnation
    - Polishing phase at end with exhaustive local search

    Args:
        cfg: Configuration object
        base_stats_fixed: Fixed base stats dictionary
        paths: Path configuration
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        all_gears: List of all gear items
        all_minis: List of all mini items
        gears_by_name: Dict mapping gear names to gear objects
        minis_by_name: Dict mapping mini names to mini objects
        optimize_gear: Whether to optimize gear (vs fixed)
        optimize_minis: Whether to optimize minis (vs fixed)
        fixed_gear: Fixed gear loadout if not optimizing
        fixed_minis: Fixed minis if not optimizing
        ga_depth: Total generations across all runs
        db_seed: Previous best loadout from database
        ga_settings: GA configuration settings
        status_cb: Optional status callback function
        executor: Optional process pool executor for parallel evaluation
        known_loadouts: Dict of known loadouts from database

    Returns:
        tuple: (best_data, best_gear, best_minis, None, [], [], all_evaluated)
    """
    # Caches are now cleared in process_song_task, but clearing here is safe redundancy.
    GEM_SOLVER_CACHE.clear()
    FG_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()

    print("\n=== STARTING GENETIC ALGORITHM SOLVER ===")
    print(f"Configuration: GearOptimization={optimize_gear}, MiniOptimization={optimize_minis}")

    ga_settings = ga_settings or GASettings.from_cfg(cfg)

    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    selected_color = p_color

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]

    # Initialize pools and apply dominance pruning
    gear_pool, mini_pool, total_before, total_after = initialize_pools(
        all_gears, all_minis, p_color, slots
    )
    if gear_pool is None:
        return None, [], []

    # Build configuration data
    # Read GPU gem solver setting from config
    use_gpu_gem_solver = cfg.getboolean("IterationEngine", "GPU_GemSolver", fallback=False) if hasattr(cfg, 'getboolean') else False
    if use_gpu_gem_solver:
        print("[GPU] GPU Gem Solver enabled for GA evaluation")
    
    cfg_data = {
        "selected_color": selected_color,
        "use_gpu": use_gpu_gem_solver,
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(
            cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)
        ),
        "user_fm": safe_int(
            cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)
        ),
        "static_elem_input": safe_int(
            cfg.get("ElementalGems", selected_color, fallback=0)
        ),
    }

    # --- MEMETIC GA PARAMETERS (configurable from [IterationEngine]) ---
    if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
        print(
            f"[Memetic GA] Enabled: elites={ga_settings.memetic_elites}, "
            f"steps={ga_settings.memetic_steps}, top_gear={ga_settings.memetic_top_gear}, "
            f"top_minis={ga_settings.memetic_top_minis}"
        )
    else:
        print("[Memetic GA] Disabled (elites or steps <= 0).")

    # Create evaluation functions and caches
    cache_hits_tracker = [0]  # Mutable container for tracking cache hits
    (
        score_candidate,
        genome_key,
        check_persistent_cache,
        evaluate_genome_local,
        evaluation_cache,
    ) = create_evaluation_functions(
        p_color,
        base_stats_fixed,
        cfg_data,
        calc_song,
        ref_arrays,
        known_loadouts,
        cache_hits_tracker,
    )

    # Build ranked candidate caches
    gear_rank_max = 10  # keep gear sweep tight to avoid huge branching
    mini_rank_max = 40  # widen minis to escape local minima
    gear_rank_cache = {
        s: sorted(gear_pool[s], key=score_candidate, reverse=True)[:gear_rank_max]
        for s in slots
    }
    mini_rank_cache = sorted(mini_pool, key=score_candidate, reverse=True)[
        :mini_rank_max
    ]

    # Create genome factory functions
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

    # Create local search functions
    run_local_search, polish_best_genome, memetic_local_search = create_local_search_function(
        evaluate_genome_local,
        gear_rank_cache,
        mini_rank_cache,
        mini_pool,
        slots,
        optimize_gear,
        optimize_minis,
    )

    # Setup multi-start runs
    num_runs = ga_settings.multi_start
    gens_per_run = max(1, (ga_depth + num_runs - 1) // num_runs)
    print(f"Multi-start runs: {num_runs} (generations per run: {gens_per_run})")

    best_global_score = -1
    best_global_genome = []
    best_global_data = {}

    # Read Deep Mining config
    if ga_settings.deep_mining_enabled:
        print(" >> [Deep Mining] Enabled: Will extend search based on cache hits.")
    else:
        print(" >> [Deep Mining] Disabled: Fixed generation count.")

    # Main multi-start GA loop
    for run_idx in range(num_runs):
        print(f"\n--- GA Run {run_idx + 1}/{num_runs} ---")
        if status_cb:
            status_cb(f"Run {run_idx + 1}/{num_runs} starting")

        # Initialize population
        population = build_initial_population(
            create_random_genome,
            create_heuristic_genome,
            reconstruct_genome_from_db_list,
            build_seed_list_from_record,
            mutate_genome_once,
            db_seed,
            ga_settings,
            fixed_gear,
            fixed_minis,
        )

        last_improvement_gen = 0
        stagnation_limit = max(8, gens_per_run // 2)
        mutation_rate = GA_MUTATION_RATE

        # Dynamic generation limit based on cache hits
        current_run_gens = gens_per_run
        cache_hits_tracker[0] = 0  # Reset for each run
        generation = 0
        current_mutation_rate = mutation_rate

        # Evolution loop
        while generation < current_run_gens:
            generation += 1

            # Evaluate population in parallel
            results = evaluate_population_parallel(
                population,
                genome_key,
                evaluation_cache,
                check_persistent_cache,
                base_stats_fixed,
                cfg_data,
                calc_song,
                ref_arrays,
                executor,
                cache_hits_tracker,
            )

            # Track best candidate
            def consider_candidate(cand):
                nonlocal best_global_score, best_global_genome, best_global_data
                cand_score = cand["Score"]
                cand_genome = cand["Genome"]
                cand_data = cand["Data"]
                best_key = genome_key(best_global_genome) if best_global_genome else None
                cand_key = genome_key(cand_genome)

                if (cand_score > best_global_score) or (
                    cand_score == best_global_score and cand_key != best_key
                ):
                    best_global_score = cand_score
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return True
                return False

            promoted = consider_candidate(results[0])

            if promoted:
                m_names = results[0]["MiniNames"]
                print(
                    f"  >> Gen {generation} (Run {run_idx + 1}): New Best {best_global_score} (Minis: {m_names})"
                )
                if status_cb:
                    status_cb(
                        f"Run {run_idx + 1}/{num_runs} Gen {generation}: New Best {best_global_score}"
                    )
                last_improvement_gen = generation
                mutation_rate = GA_MUTATION_RATE
            else:
                if generation % 10 == 0:
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): Best {results[0]['Score']}"
                    )
                    if status_cb:
                        status_cb(
                            f"Run {run_idx + 1}/{num_runs} Gen {generation}: Best {results[0]['Score']}"
                        )

            # --- MEMETIC GA STEP: local search on top elites ---
            if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
                elite_count = min(ga_settings.memetic_elites, len(results))
                for e_idx in range(elite_count):
                    base_res = results[e_idx]
                    improved_res = memetic_local_search(
                        base_res["Genome"],
                        ga_settings.memetic_steps,
                        ga_settings.memetic_top_gear,
                        ga_settings.memetic_top_minis,
                    )
                    if improved_res["Score"] > base_res["Score"]:
                        results[e_idx] = improved_res
                        # Feed improved candidate back into global tracking
                        if consider_candidate(improved_res):
                            m_names = improved_res["MiniNames"]
                            print(
                                f"  >> [Memetic] Gen {generation} "
                                f"(Run {run_idx + 1}): New Best {best_global_score} "
                                f"(Minis: {m_names})"
                            )
                            if status_cb:
                                status_cb(
                                    f"Run {run_idx + 1}/{num_runs} Gen {generation} "
                                    f"Memetic: New Best {best_global_score}"
                                )
                            last_improvement_gen = generation
                            mutation_rate = GA_MUTATION_RATE
                # Resort after memetic improvements
                results.sort(key=lambda x: x["Score"], reverse=True)

            # Generate next generation via crossover and mutation
            next_gen = perform_crossover_mutation(
                results,
                create_random_genome,
                mini_pool,
                gear_pool,
                slots,
                optimize_gear,
                optimize_minis,
                fixed_minis,
                current_mutation_rate,
            )

            population = next_gen
            next_gen = None  # Break reference to help GC

            # Compute dynamic mutation rate and generation limit
            exploration_boost = 0.0
            if ga_settings.deep_mining_enabled or True:  # Always compute for logging
                current_mutation_rate, current_run_gens = compute_dynamic_mutation(
                    mutation_rate,
                    cache_hits_tracker[0],
                    generation,
                    current_run_gens,
                    gens_per_run,
                    ga_settings,
                )
                # Calculate exploration boost for logging
                total_evals_so_far = generation * GA_POPULATION_SIZE
                hit_ratio = cache_hits_tracker[0] / max(1, total_evals_so_far)
                exploration_boost = min(0.2, hit_ratio * 0.5)

            # Handle stagnation
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
            )

    # Polish best genome with exhaustive local search
    if best_global_genome:
        polished_result, polished_genome = polish_best_genome(best_global_genome)

        # If result was cached, re-evaluate fully to get all details
        if polished_result.get("_cached"):
            polished_result = worker_coevolution_evaluate(
                (polished_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
            )

        polished_score = polished_result["Score"]

        if polished_score > best_global_score:
            best_global_score = polished_score
            best_global_data = polished_result["Data"]
            best_global_genome = polished_genome

    best_gear = best_global_genome[:6] if best_global_genome else []
    best_minis = best_global_genome[6:] if best_global_genome else []

    # Return all unique evaluated loadouts from the cache
    all_evaluated = list(evaluation_cache.values())

    # Memory leak fix: Clear cache immediately after extraction
    # This prevents the cache from lingering until function exit
    evaluation_cache.clear()

    # Memory leak fix: Clear all generation-scoped data before returning
    population = None
    results = None

    return (
        best_global_data if best_global_data else None,
        best_gear,
        best_minis,
        None,
        [],
        [],
        all_evaluated,  # All unique loadouts evaluated by GA (capped before DB persistence)
    )
