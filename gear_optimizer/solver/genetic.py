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

# Support deterministic testing via GA_SEED environment variable
_GA_SEED = os.environ.get("GA_SEED")
if _GA_SEED is not None:
    _GA_SEED = int(_GA_SEED)
    random.seed(_GA_SEED)
    print(f"[GA] Deterministic mode: seed={_GA_SEED}")

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
        print(f"[GA Error] initialize_pools failed for song {calc_song['metadata'].get('Song Name', 'Unknown')}")
        return None, [], [], None, [], [], []

    # Build configuration data
    # Read GPU mode setting from config
    use_gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False) if hasattr(cfg, 'getboolean') else False
    # FG heuristic DISABLED: GA now optimizes for true base score (all perfects)
    # The FG finder separately evaluates all loadouts with FG configs to find the best FG score.
    # This gives two independent optimal results: best raw base score + best FG score.
    if use_gpu_mode:
        print("[GPU] GPU_Mode enabled for GA evaluation")
    
    cfg_data = {
        "selected_color": selected_color,
        "use_gpu": use_gpu_mode,
        "fg_heuristic": cfg.getboolean("IterationEngine", "ForceGreatsHeuristic", fallback=False) if hasattr(cfg, 'getboolean') else False,
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
        batch_evaluator,
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

    # Build ranked candidate caches
    gear_rank_max = 25  # expanded to help find items heuristic underranks
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
    run_local_search, polish_best_genome, memetic_local_search, batch_memetic_local_search = create_local_search_function(
        evaluate_genome_local,
        batch_evaluator,
        gear_rank_cache,
        mini_rank_cache,
        mini_pool,
        gear_pool,
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

    # Store each run's best for comparison at the end
    run_results = []  # List of (score, genome, data) tuples

    # Cross-run elite sharing: DISABLED - each run is independent now
    # global_elites = []

    # Soft non-regression guard:
    # Evaluate DB seed once up-front and cache it, but DON'T lock it as global best.
    # This allows the GA to explore freely without being anchored to the DB score.
    # We only use the DB seed for non-regression comparison at the END.
    db_seed_score = -1
    db_seed_genome = None
    db_seed_data = None
    if db_seed:
        try:
            seed_list = build_seed_list_from_record(db_seed)
            if seed_list:
                seed_genome = reconstruct_genome_from_db_list(seed_list)
                seed_res = worker_coevolution_evaluate(
                    (seed_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
                )
                evaluation_cache[genome_key(seed_genome)] = seed_res
                # CRITICAL: Use BaseScore (true score) for DB comparison, not Score
                # which may include FG heuristic boost. This ensures consistent
                # comparison between what's stored in DB and new GA results.
                db_seed_score = seed_res.get("BaseScore") or seed_res["Score"]
                db_seed_genome = seed_genome
                db_seed_data = seed_res["Data"]
                print(
                    f" >> [Evolution] DB seed baseline (soft): {db_seed_score}"
                )
        except Exception as exc:
            print(f" >> [Evolution] Warning: failed to evaluate DB seed: {exc}")

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
            force_db_seed=False,  # Use db_seed_prob probability instead of guaranteed injection
        )

        # Track progress within THIS run (not global best).
        # This avoids "false stagnation" when the global best is already locked.
        best_run_score = -1
        last_improvement_gen = 0

        # Reset global best at start of each run to ensure independence
        # The best across all runs will be selected after all runs complete
        best_global_score = -1
        best_global_genome = []
        best_global_data = {}

        base_stagnation_limit = max(8, gens_per_run // 2)
        explore_stagnation_limit = max(8, gens_per_run // 3)
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
                use_gpu_batch=cfg_data.get("use_gpu", False),
            )

            # Track best candidate (global best with tie-awareness)
            def consider_candidate(cand):
                nonlocal best_global_score, best_global_genome, best_global_data
                cand_score = cand["Score"]
                cand_genome = cand["Genome"]
                cand_data = cand["Data"]
                # CRITICAL: Inject BaseScore into cand_data so build_db_payload can access it.
                # The outer wrapper has BaseScore (true score), but cand_data (inner dict) doesn't.
                # Without this, build_db_payload uses cand_data["Score"] which may be outdated.
                if "BaseScore" in cand:
                    cand_data["BaseScore"] = cand["BaseScore"]
                best_key = genome_key(best_global_genome) if best_global_genome else None
                cand_key = genome_key(cand_genome)

                if cand_score > best_global_score:
                    best_global_score = cand_score
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return 2  # strict improvement

                if cand_score == best_global_score and cand_key != best_key:
                    # Same score, different loadout: treat as a variant, not an improvement.
                    best_global_genome = cand_genome
                    best_global_data = cand_data
                    return 1  # tie variant

                return 0

            # --- MEMETIC GA STEP: local search on top elites ---
            if ga_settings.memetic_elites > 0 and ga_settings.memetic_steps > 0:
                elite_count = min(ga_settings.memetic_elites, len(results))
                
                # BATCHED PATH: Process all elites simultaneously
                # This reduces kernel launch overhead by packing all neighbors into fewer batches.
                seed_genomes = [results[i]["Genome"] for i in range(elite_count)]
                improved_results = batch_memetic_local_search(
                    seed_genomes,
                    ga_settings.memetic_steps,
                    ga_settings.memetic_top_gear,
                    ga_settings.memetic_top_minis,
                )
                
                # Update population with improved versions if score increased
                for i, improved_res in enumerate(improved_results):
                    if improved_res["Score"] > results[i]["Score"]:
                        results[i] = improved_res
                
                # Resort after memetic improvements
                results.sort(key=lambda x: x["Score"], reverse=True)

            # Best candidate AFTER memetic (this is the generation winner)
            best_cand = results[0]

            # Update run-best tracking (used for stagnation handling)
            if best_cand["Score"] > best_run_score:
                best_run_score = best_cand["Score"]
                last_improvement_gen = generation
                mutation_rate = GA_MUTATION_RATE

            promote_status = consider_candidate(best_cand)
            if promote_status == 2:
                m_names = best_cand["MiniNames"]
                print(
                    f"  >> Gen {generation} (Run {run_idx + 1}): New Best {best_global_score} (Minis: {m_names})"
                )
                if status_cb:
                    status_cb(
                        f"Run {run_idx + 1}/{num_runs} Gen {generation}: New Best {best_global_score}"
                    )
            elif promote_status == 1:
                # Tie score, but a different loadout at the same global score.
                # Don't call it a "new best" to avoid confusing plateaus with improvements.
                if generation % 10 == 0:
                    m_names = best_cand["MiniNames"]
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): "
                        f"BestVariant {best_global_score} (Minis: {m_names})"
                    )
            else:
                if generation % 10 == 0:
                    print(
                        f"  >> Gen {generation} (Run {run_idx + 1}): "
                        f"BestInRun {best_cand['Score']} | GlobalBest {best_global_score}"
                    )
                    if status_cb:
                        status_cb(
                            f"Run {run_idx + 1}/{num_runs} Gen {generation}: "
                            f"BestInRun {best_cand['Score']} | GlobalBest {best_global_score}"
                        )

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
                global_elites=None,  # Cross-run sharing disabled - runs are independent
            )

            population = next_gen
            next_gen = None  # Break reference to help GC

            # Compute dynamic mutation rate and generation limit
            current_mutation_rate, current_run_gens = compute_dynamic_mutation(
                mutation_rate,
                cache_hits_tracker[0],
                generation,
                current_run_gens,
                gens_per_run,
                ga_settings,
            )

            # Cache-hit driven exploration boost is only applied when DeepMining is enabled.
            total_evals_so_far = generation * GA_POPULATION_SIZE
            hit_ratio = cache_hits_tracker[0] / max(1, total_evals_so_far)
            exploration_boost = min(0.2, hit_ratio * 0.5) if ga_settings.deep_mining_enabled else 0.0

            # Handle stagnation
            # If this run is far below the global best, trigger diversity injection sooner
            # to avoid wasting many generations in a clearly inferior basin.
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

        # Cross-run elite sharing: add this run's best to the global elite pool.
        # This makes discoveries available for crossover in subsequent runs.
        if best_run_score > 0:
            # Store this run's best result (using heuristic Score for GA selection)
            run_best_genome = results[0]["Genome"] if results else None
            run_best_score = results[0]["Score"] if results else -1
            run_best_data = results[0]["Data"] if results else {}
            if run_best_genome and run_best_score > 0:
                run_results.append((run_best_score, run_best_genome, run_best_data))

    # Select the best result across all independent runs (using true base scores)
    for run_score, run_genome, run_data in run_results:
        if run_score > best_global_score:
            best_global_score = run_score
            best_global_genome = run_genome
            best_global_data = run_data

    # Polish best genome with exhaustive local search
    if best_global_genome:
        polished_result, polished_genome = polish_best_genome(best_global_genome)

        # If result was cached, re-evaluate fully to get all details
        if polished_result.get("_cached"):
            polished_result = worker_coevolution_evaluate(
                (polished_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
            )

        # Use heuristic Score for GA selection (BaseScore only for DB comparisons)
        polished_score = polished_result["Score"]

        if polished_score > best_global_score:
            best_global_score = polished_score
            best_global_data = polished_result["Data"]
            best_global_genome = polished_genome

    # Soft non-regression guard: If GA's best is worse than DB seed, fall back.
    # This ensures we never regress while still allowing free exploration.
    # CRITICAL: Get the TRUE base score from best_global_data["Score"] for comparison,
    # since best_global_score may still contain heuristic boost from GA selection.
    ga_true_score = best_global_data.get("Score", 0) if best_global_data else best_global_score
    if db_seed_score > ga_true_score and db_seed_genome:
        print(f" >> [Evolution] GA best ({ga_true_score}) < DB seed ({db_seed_score}); using DB seed.")
        best_global_score = db_seed_score
        best_global_genome = db_seed_genome
        best_global_data = db_seed_data

    # CRITICAL: Re-evaluate if best_global_data is missing GemCounts (from DB cache path).
    # This ensures the final result always has complete gem allocation details for display.
    if best_global_genome and best_global_data and "GemCounts" not in best_global_data:
        full_result = worker_coevolution_evaluate(
            (best_global_genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        )
        best_global_data = full_result["Data"]

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
    
    if not best_global_data:
        print(f"[GA Error] GA completed but found no valid candidates (best_global_score={best_global_score})")

    # Inject the heuristic score into the data packet if it differs from the base score.
    # This helps explain why GA picked a loadout with a lower base score (due to expected FG boost).
    if best_global_data and best_global_score != best_global_data.get("Score", 0):
        best_global_data["HeuristicScore"] = best_global_score

    return (
        best_global_data if best_global_data else None,
        best_gear,
        best_minis,
        None,
        [],
        [],
        all_evaluated,  # All unique loadouts evaluated by GA (capped before DB persistence)
    )
