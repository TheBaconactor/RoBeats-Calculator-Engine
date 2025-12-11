"""
Helper functions for genetic algorithm operations.

This module contains helper functions extracted from solve_coevolution_genetic()
to improve code modularity and maintainability. These functions handle:
- Pool initialization and pruning
- Genome factory functions
- Evaluation and caching
- Local search operations
- Population initialization
- Crossover and mutation
- Parallel evaluation
- Diversity and stagnation handling
"""
import os
import random

from ..core.constants import GA_POPULATION_SIZE, GA_MUTATION_RATE, GA_MUTATION_RATE_MAX, GA_ELITISM
from ..core.utils import prune_dominated_gear
from ..data.database import get_loadout_hash
from ..solver.scoring import worker_coevolution_evaluate


def initialize_pools(all_gears, all_minis, p_color, slots):
    """
    Initialize and prune gear and mini pools.

    Creates per-slot gear pools and filters minis by primary color.
    Applies dominance pruning to remove strictly inferior gear items.

    Args:
        all_gears: List of all gear items
        all_minis: List of all mini items
        p_color: Primary color for mini filtering
        slots: List of gear slot names

    Returns:
        tuple: (gear_pool, mini_pool, total_before, total_after)
            - gear_pool: Dict mapping slot names to lists of gear
            - mini_pool: List of valid minis
            - total_before: Total gear count before pruning
            - total_after: Total gear count after pruning
    """
    # Filter minis by primary color
    mini_pool = [m for m in all_minis if m.get(p_color, 0) > 0]
    if not mini_pool:
        print("No valid minis found (Primary Color check).")
        return None, [], 0, 0

    # Initialize gear pools by slot
    gear_pool = {s: [] for s in slots}
    for g in all_gears:
        if g["type"] in gear_pool:
            gear_pool[g["type"]].append(g)

    # Apply dominance pruning per slot to remove strictly inferior gear
    total_before = sum(len(gear_pool[s]) for s in slots)
    for s in slots:
        gear_pool[s] = prune_dominated_gear(gear_pool[s])
    total_after = sum(len(gear_pool[s]) for s in slots)

    if total_before > total_after:
        print(f"[Dominance Pruning] Removed {total_before - total_after} dominated gear items.")

    return gear_pool, mini_pool, total_before, total_after


def create_genome_functions(
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
):
    """
    Create genome factory and manipulation functions.

    Returns closures for creating random/heuristic genomes, reconstructing from DB,
    building seed lists, and mutating genomes.

    Args:
        gear_pool: Dict mapping slot names to gear lists
        mini_pool: List of valid minis
        gear_rank_cache: Dict mapping slots to ranked gear lists
        mini_rank_cache: Ranked list of minis
        gears_by_name: Dict mapping gear names to gear objects
        minis_by_name: Dict mapping mini names to mini objects
        slots: List of gear slot names
        optimize_gear: Whether to optimize gear
        optimize_minis: Whether to optimize minis
        fixed_gear: Fixed gear loadout if not optimizing
        fixed_minis: Fixed minis if not optimizing

    Returns:
        tuple: (create_random_genome, create_heuristic_genome,
                reconstruct_genome_from_db_list, build_seed_list_from_record,
                mutate_genome_once)
    """

    def create_random_genome():
        """Create a random genome from available pools."""
        genome = []
        if optimize_gear:
            for s in slots:
                genome.append(random.choice(gear_pool[s]) if gear_pool[s] else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            if len(mini_pool) >= 3:
                genome.extend(random.sample(mini_pool, 3))
            else:
                genome.extend(random.sample(mini_pool, len(mini_pool)))
                while len(genome) < 9:
                    genome.append({})
        else:
            genome.extend(fixed_minis)
        return genome

    def create_heuristic_genome():
        """Create a genome biased toward high-ranked items."""
        genome = []
        if optimize_gear:
            for s in slots:
                candidates = gear_rank_cache.get(s, [])
                genome.append(random.choice(candidates[:5]) if candidates else {})
        else:
            genome.extend(fixed_gear)

        if optimize_minis:
            if len(mini_rank_cache) >= 3:
                genome.extend(random.sample(mini_rank_cache[:10], 3))
            else:
                genome.extend(random.sample(mini_pool, 3))
        else:
            genome.extend(fixed_minis)
        return genome

    def reconstruct_genome_from_db_list(db_list):
        """Rebuild full stats from just the names in the DB."""
        r_genome = []
        for i in range(6):
            name = db_list[i] if i < len(db_list) else ""
            if name in gears_by_name:
                r_genome.append(gears_by_name[name])
            else:
                r_genome.append({"Name": "(Empty)", "type": slots[i]})
        for i in range(6, 9):
            if i < len(db_list):
                name = db_list[i]
                if name in minis_by_name:
                    r_genome.append(minis_by_name[name])
                else:
                    r_genome.append({"Name": "(Empty)", "type": "Mini"})
            else:
                r_genome.append({"Name": "(Empty)", "type": "Mini"})
        return r_genome

    def build_seed_list_from_record(record):
        """
        Normalize any stored record into a compact list of names for seeding.
        Handles both dict format (with 'Name' key) and plain string names.
        Priority: legacy loadout -> gear + minis.
        """
        if not record:
            return None

        def extract_name(item):
            """Extract name from either a dict or string."""
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""

        if "loadout" in record:
            load = record.get("loadout") or []
            if isinstance(load, list):
                return [extract_name(item) for item in load]

        gear_items = record.get("gear") or []
        mini_items = record.get("minis") or []

        if gear_items or mini_items:
            gear_names = [extract_name(g) for g in gear_items]
            mini_names = [extract_name(m) for m in mini_items]
            return gear_names + mini_names
        return None

    def mutate_genome_once(genome):
        """Soft mutation around a seed genome for DB seeding."""
        g = list(genome)
        mutate_idx = random.randint(0, 8)

        if mutate_idx < 6 and optimize_gear:
            slot_type = slots[mutate_idx]
            if gear_pool[slot_type]:
                g[mutate_idx] = random.choice(gear_pool[slot_type])
        elif mutate_idx >= 6 and optimize_minis:
            # Extract current mini names, handling both dict and string formats
            current_mini_names = set()
            for m in g[6:]:
                if isinstance(m, dict):
                    current_mini_names.add(m.get("Name", ""))
                elif m:
                    current_mini_names.add(str(m))
            candidates = [m for m in mini_pool if m["Name"] not in current_mini_names]
            if candidates:
                g[mutate_idx] = random.choice(candidates)

        return g

    return (
        create_random_genome,
        create_heuristic_genome,
        reconstruct_genome_from_db_list,
        build_seed_list_from_record,
        mutate_genome_once,
    )


def create_evaluation_functions(
    p_color,
    base_stats_fixed,
    cfg_data,
    calc_song,
    ref_arrays,
    known_loadouts,
    cache_hits_tracker,
):
    """
    Create evaluation and caching functions.

    Returns closures for scoring candidates, genome keying, and cache operations.

    Args:
        p_color: Primary color for scoring
        base_stats_fixed: Fixed base stats dictionary
        cfg_data: Configuration data for evaluation
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        known_loadouts: Dict of known loadouts from database
        cache_hits_tracker: List [count] for tracking cache hits (mutable)

    Returns:
        tuple: (score_candidate, genome_key, check_persistent_cache,
                evaluate_genome_local, evaluation_cache)
    """

    def score_candidate(x):
        """Simple heuristic scoring for ranking items."""
        return (
            x.get(p_color, 0) * 3
            + x.get("Perfect Points", 0) * 2
            + x.get("Combo Multiplier", 0) * 2
            + x.get("Fever Multiplier", 0) * 2
        )

    def genome_key(genome):
        """Generate a unique key for a genome for caching."""
        # Helper to extract name from dict or string
        def get_name(item):
            if isinstance(item, dict):
                return item.get("Name", "")
            return str(item) if item else ""

        # Gear (first 6 slots): order matters because slots are positional.
        gear_names = tuple(get_name(item) for item in genome[:6])
        # Minis (last 3 slots): order-invariant - only the set/multiset matters.
        # Sorting canonicalizes permutations so [A,B,C] and [C,B,A] share a key.
        mini_names = tuple(sorted(get_name(item) for item in genome[6:]))
        return gear_names + mini_names

    evaluation_cache = {}

    def check_persistent_cache(genome):
        """Check if genome exists in persistent database cache."""
        if known_loadouts:
            gear_part = genome[:6]
            mini_part = genome[6:]
            h = get_loadout_hash(gear_part, mini_part)
            if h in known_loadouts:
                entry = known_loadouts[h]

                # DB rows are stored as (score, fg_score, force_data); fall back gracefully
                score = fg_score = force_data = None
                if isinstance(entry, dict):
                    score = entry.get("score")
                    fg_score = entry.get("fg_score")
                    force_data = entry.get("force_data") or entry.get("force_details")
                elif isinstance(entry, (list, tuple)):
                    if len(entry) >= 2:
                        score, fg_score = entry[0], entry[1]
                    if len(entry) >= 3:
                        force_data = entry[2]
                else:
                    # Unknown shape; skip cache usage rather than crashing
                    return None

                if score is None or fg_score is None:
                    return None

                return {
                    "Score": score,
                    "FG_Score": fg_score,
                    "Genome": genome,
                    "Gear": gear_part,
                    "Minis": mini_part,
                    "MiniNames": [
                        m.get("Name", "") if isinstance(m, dict) else str(m) for m in mini_part
                    ],
                    "Data": {
                        "Score": score,
                        "_cached_db": True,
                        "ForceDetails": force_data,
                    },
                    "_cached": True,  # Flag so we force a full re-eval when polishing
                }
        return None

    def evaluate_genome_local(genome):
        """Evaluate a genome with in-memory and persistent caching."""
        k = genome_key(genome)
        if k in evaluation_cache:
            return evaluation_cache[k]

        cached_res = check_persistent_cache(genome)
        if cached_res:
            evaluation_cache[k] = cached_res
            cache_hits_tracker[0] += 1
            return cached_res

        res = worker_coevolution_evaluate(
            (genome, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        )
        evaluation_cache[k] = res
        return res

    return (
        score_candidate,
        genome_key,
        check_persistent_cache,
        evaluate_genome_local,
        evaluation_cache,
    )


def create_local_search_function(
    evaluate_genome_local,
    gear_rank_cache,
    mini_rank_cache,
    mini_pool,
    slots,
    optimize_gear,
    optimize_minis,
):
    """
    Create local search function for memetic GA and polishing.

    Args:
        evaluate_genome_local: Function to evaluate genomes
        gear_rank_cache: Dict mapping slots to ranked gear lists
        mini_rank_cache: Ranked list of minis
        mini_pool: List of valid minis
        slots: List of gear slot names
        optimize_gear: Whether to optimize gear
        optimize_minis: Whether to optimize minis

    Returns:
        tuple: (run_local_search, polish_best_genome, memetic_local_search)
    """

    def run_local_search(start_genome, max_steps, top_k_gear, top_k_minis, is_polishing=False):
        """
        Unified local search logic for both Memetic Search and Polishing.
        Iteratively improves the genome by checking neighbors in ranked lists.
        """
        best_genome = list(start_genome)
        best_result = evaluate_genome_local(best_genome)
        best_score = best_result["Score"]

        # Pre-trim candidate lists
        local_gear_rank = {
            s: gear_rank_cache.get(s, [])[:top_k_gear] for s in slots
        }
        local_mini_rank = mini_rank_cache[:top_k_minis]

        steps = 0
        # Polishing runs until no improvement (or very high limit), Memetic runs fixed steps
        limit = 999999 if is_polishing else max_steps

        while steps < limit:
            improved = False

            # Gear neighbourhood
            if optimize_gear:
                for idx, slot in enumerate(slots):
                    curr_item = best_genome[idx]
                    current_name = curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                    for cand in local_gear_rank.get(slot, []):
                        if cand.get("Name") == current_name:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        trial_res = evaluate_genome_local(trial)
                        if trial_res["Score"] > best_score:
                            best_score = trial_res["Score"]
                            best_result = trial_res
                            best_genome = trial
                            improved = True
                            steps += 1
                            break
                    if improved or (not is_polishing and steps >= limit):
                        break

            if not is_polishing and steps >= limit:
                break

            # Mini neighbourhood
            if (not improved or is_polishing) and optimize_minis:
                # Extract existing mini names, handling both dict and string formats
                existing = set()
                for m in best_genome[6:]:
                    if isinstance(m, dict):
                        existing.add(m.get("Name", ""))
                    elif m:
                        existing.add(str(m))
                for idx in range(6, 9):
                    curr_item = best_genome[idx]
                    curr_name = curr_item.get("Name") if isinstance(curr_item, dict) else str(curr_item) if curr_item else ""
                    for cand in local_mini_rank:
                        c_name = cand.get("Name")
                        if c_name == curr_name:
                            continue
                        if c_name in existing - {curr_name}:
                            continue
                        trial = best_genome[:]
                        trial[idx] = cand
                        trial_res = evaluate_genome_local(trial)
                        if trial_res["Score"] > best_score:
                            best_score = trial_res["Score"]
                            best_result = trial_res
                            best_genome = trial
                            improved = True
                            steps += 1
                            break
                    if improved or (not is_polishing and steps >= limit):
                        break

            if not improved:
                break

        return best_result, best_genome

    def polish_best_genome(best_genome):
        """Local sweep on top candidates per slot/mini to escape near-misses."""
        top_k_gear = 8
        top_k_minis = min(25, len(mini_rank_cache))
        return run_local_search(best_genome, 0, top_k_gear, top_k_minis, is_polishing=True)

    def memetic_local_search(start_genome, max_steps, top_k_gear, top_k_minis):
        """Lightweight local search around a genome."""
        if max_steps <= 0:
            res = evaluate_genome_local(start_genome)
            return res

        res, _ = run_local_search(start_genome, max_steps, top_k_gear, top_k_minis, is_polishing=False)
        return res

    return run_local_search, polish_best_genome, memetic_local_search


def build_initial_population(
    create_random_genome,
    create_heuristic_genome,
    reconstruct_genome_from_db_list,
    build_seed_list_from_record,
    mutate_genome_once,
    db_seed,
    ga_settings,
    fixed_gear,
    fixed_minis,
):
    """
    Build the initial population for a GA run.

    Injects DB seeds, fixed loadouts, heuristic genomes, and random genomes.

    Args:
        create_random_genome: Function to create random genomes
        create_heuristic_genome: Function to create heuristic genomes
        reconstruct_genome_from_db_list: Function to reconstruct genome from DB
        build_seed_list_from_record: Function to build seed list from record
        mutate_genome_once: Function to mutate a genome once
        db_seed: Previous best loadout from database
        ga_settings: GA configuration settings
        fixed_gear: Fixed gear loadout if not optimizing
        fixed_minis: Fixed minis if not optimizing

    Returns:
        list: Initial population of genomes
    """
    population = []
    seed_list = build_seed_list_from_record(db_seed)
    if seed_list and random.random() < ga_settings.db_seed_prob:
        try:
            print(
                f" >> [Evolution] Injecting previous best (Score: {db_seed.get('score', 0)})"
            )
            seed_genome = reconstruct_genome_from_db_list(seed_list)
            population.append(seed_genome[:])
            population.append(mutate_genome_once(seed_genome))
        except Exception as e:
            print(f" >> [Evolution] Failed to inject seed: {e}")
    elif seed_list:
        print(" >> [Evolution] Skipping DB seed this run (probability gate).")

    if fixed_gear and fixed_minis:
        seed_genome = fixed_gear + fixed_minis
        for _ in range(ga_settings.fixed_seed_copies):
            population.append(seed_genome[:])

    for _ in range(10):
        population.append(create_heuristic_genome())

    while len(population) < GA_POPULATION_SIZE:
        population.append(create_random_genome())
    return population


def perform_crossover_mutation(
    results,
    create_random_genome,
    mini_pool,
    gear_pool,
    slots,
    optimize_gear,
    optimize_minis,
    fixed_minis,
    current_mutation_rate,
):
    """
    Perform crossover and mutation to create next generation.

    Args:
        results: Evaluated population sorted by score
        create_random_genome: Function to create random genomes
        mini_pool: List of valid minis
        gear_pool: Dict mapping slot names to gear lists
        slots: List of gear slot names
        optimize_gear: Whether to optimize gear
        optimize_minis: Whether to optimize minis
        fixed_minis: Fixed minis if not optimizing
        current_mutation_rate: Current mutation rate

    Returns:
        list: Next generation population
    """
    next_gen = [results[i]["Genome"] for i in range(GA_ELITISM)]

    while len(next_gen) < GA_POPULATION_SIZE:
        if random.random() < 0.18:
            next_gen.append(create_random_genome())
            continue

        p1 = random.choice(results[:50])["Genome"]
        p2 = random.choice(results[:50])["Genome"]

        child = []
        L = min(len(p1), len(p2))
        for i in range(L):
            child.append(p1[i] if random.random() > 0.5 else p2[i])

        child_gear = child[:6]
        child_minis = child[6:]

        seen_names = set()
        unique_minis = []
        for m in child_minis:
            name = m.get("Name", None) if isinstance(m, dict) else None
            if name and name not in seen_names and name != "(Empty)":
                unique_minis.append(m)
                seen_names.add(name)

        if optimize_minis:
            while len(unique_minis) < 3:
                candidates = [m for m in mini_pool if m["Name"] not in seen_names]
                if candidates:
                    new_m = random.choice(candidates)
                    unique_minis.append(new_m)
                    seen_names.add(new_m["Name"])
                else:
                    break
        else:
            # Shallow copy suffices; minis are read-only dicts.
            unique_minis = list(fixed_minis)

        child = child_gear + unique_minis

        # Use current_mutation_rate instead of mutation_rate
        if random.random() < current_mutation_rate:
            mutate_idx = random.randint(0, 8)
            if mutate_idx < 6 and optimize_gear:
                slot_type = slots[mutate_idx]
                if gear_pool[slot_type]:
                    child[mutate_idx] = random.choice(gear_pool[slot_type])
            elif mutate_idx >= 6 and optimize_minis:
                current_mini_names = {
                    m.get("Name") for m in child[6:] if isinstance(m, dict)
                }
                candidates = [
                    m for m in mini_pool if m["Name"] not in current_mini_names
                ]
                if candidates:
                    child[mutate_idx] = random.choice(candidates)

        next_gen.append(child)

    return next_gen


def evaluate_population_parallel(
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
):
    """
    Evaluate population in parallel using process pool.

    Args:
        population: List of genomes to evaluate
        genome_key: Function to generate genome keys
        evaluation_cache: Dict of cached evaluations
        check_persistent_cache: Function to check persistent cache
        base_stats_fixed: Fixed base stats dictionary
        cfg_data: Configuration data for evaluation
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        executor: Process pool executor (or None for serial)
        cache_hits_tracker: List [count] for tracking cache hits (mutable)

    Returns:
        list: Evaluated results sorted by score
    """
    key_to_genome = {}
    pending_keys = []
    tasks = []
    for genome in population:
        k = genome_key(genome)
        if k in key_to_genome:
            continue
        key_to_genome[k] = genome
        if k not in evaluation_cache:
            pending_keys.append(k)
            tasks.append((genome, base_stats_fixed, cfg_data, calc_song, ref_arrays))

    if pending_keys:
        keys_to_calc = []
        tasks_to_calc = []

        for k, genome, task_payload in zip(pending_keys, [key_to_genome[k] for k in pending_keys], tasks):
            # Check persistent cache first
            cached_res = check_persistent_cache(genome)
            if cached_res:
                evaluation_cache[k] = cached_res
                cache_hits_tracker[0] += 1
            else:
                keys_to_calc.append(k)
                tasks_to_calc.append(task_payload)

        if keys_to_calc:
            if executor:
                worker_count = getattr(executor, "_max_workers", None) or (
                    os.cpu_count() or 1
                )
                chunk = max(1, len(tasks_to_calc) // (worker_count * 4))
                for k, res in zip(
                    keys_to_calc,
                    executor.map(
                        worker_coevolution_evaluate, tasks_to_calc, chunksize=chunk
                    ),
                ):
                    evaluation_cache[k] = res
            else:
                for k, payload in zip(keys_to_calc, tasks_to_calc):
                    evaluation_cache[k] = worker_coevolution_evaluate(payload)

    results = [evaluation_cache[genome_key(g)] for g in population]
    results.sort(key=lambda x: x["Score"], reverse=True)

    return results


def update_mutation_and_diversity(
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
):
    """
    Update mutation rate and inject diversity if stagnated.

    Args:
        population: Current population
        results: Evaluated results
        generation: Current generation number
        last_improvement_gen: Last generation with improvement
        stagnation_limit: Generations before injecting diversity
        mutation_rate: Base mutation rate
        create_random_genome: Function to create random genomes
        create_heuristic_genome: Function to create heuristic genomes
        run_idx: Current run index
        current_mutation_rate: Current mutation rate with exploration boost
        exploration_boost: Exploration boost amount

    Returns:
        tuple: (updated_population, updated_mutation_rate, updated_last_improvement_gen)
    """
    if generation - last_improvement_gen >= stagnation_limit:
        mutation_rate = min(GA_MUTATION_RATE_MAX, mutation_rate + 0.08)
        print(
            f"  >> Stagnation detected (Run {run_idx + 1}), mutation -> {current_mutation_rate:.3f} (Boost: {exploration_boost:.3f}), injecting diversity"
        )
        elites = [r["Genome"] for r in results[:GA_ELITISM]]
        population = elites[:]
        reinject_target = int(GA_POPULATION_SIZE * 0.4)
        while len(population) < reinject_target:
            population.append(create_random_genome())
        while len(population) < GA_POPULATION_SIZE:
            population.append(create_heuristic_genome())
        last_improvement_gen = generation

    return population, mutation_rate, last_improvement_gen


def compute_dynamic_mutation(
    mutation_rate,
    cache_hits_in_run,
    generation,
    current_run_gens,
    gens_per_run,
    ga_settings,
):
    """
    Compute dynamic mutation rate and generation limit based on cache hits.

    Implements "deep mining" - extends search when cache hits indicate known territory
    and increases mutation rate to explore more aggressively.

    Args:
        mutation_rate: Base mutation rate
        cache_hits_in_run: Number of cache hits in current run
        generation: Current generation number
        current_run_gens: Current generation limit for this run
        gens_per_run: Base generations per run
        ga_settings: GA configuration settings

    Returns:
        tuple: (current_mutation_rate, updated_current_run_gens)
    """
    # Update dynamic generation limit
    # "run longer about 1 gen for each hit"
    # We add the hits to the base limit.
    if ga_settings.deep_mining_enabled:
        current_run_gens = gens_per_run + cache_hits_in_run

    # "increase the exploration"
    # If we have many cache hits, we are in known territory. Increase mutation.
    # Base mutation is ~0.275. Max is 0.45.
    # If we have > 10% cache hits in the run, boost mutation.
    # Let's calculate a dynamic boost based on hit density.
    total_evals_so_far = generation * GA_POPULATION_SIZE
    hit_ratio = cache_hits_in_run / max(1, total_evals_so_far)

    # Boost mutation by up to 0.2 if hit ratio is high
    exploration_boost = min(0.2, hit_ratio * 0.5)
    current_mutation_rate = min(0.6, mutation_rate + exploration_boost)  # Allow going slightly higher than normal max

    # Cap the extension to avoid infinite loops (e.g. max 5000 gens)
    if current_run_gens > 5000:
        current_run_gens = 5000

    return current_mutation_rate, current_run_gens
