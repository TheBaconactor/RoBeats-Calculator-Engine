"""
GA Population - Population initialization, crossover, and mutation.

This module provides population operations:
- build_initial_population: Heuristic + random + DB seed population
- perform_crossover_mutation: Tournament selection, crossover, mutation, elitism
"""

import os
import random

from ...core.constants import GA_POPULATION_SIZE, GA_ELITISM


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
    force_db_seed=False,
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
    rand_val = random.random()
    should_inject = bool(seed_list) and (force_db_seed or (rand_val < ga_settings.db_seed_prob))
    # Debug logging is intentionally opt-in (printing per-song/run can dominate runtime).
    if (
        seed_list
        and not force_db_seed
        and str(os.environ.get("GA_DEBUG_DB_SEED_GATE", "0")).strip().lower() in {"1", "true", "yes", "on"}
    ):
        print(f" >> [GA][DEBUG] db_seed_prob={ga_settings.db_seed_prob}, random={rand_val:.4f}, inject={should_inject}")
    if seed_list and should_inject:
        try:
            if force_db_seed:
                print(f" >> [Evolution] Injecting previous best (forced) (Score: {db_seed.get('score', 0)})")
            else:
                print(f" >> [Evolution] Injecting previous best (Score: {db_seed.get('score', 0)})")
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

    # Inject more heuristic genomes (25 instead of 10) to ensure each of the
    # top-ranked minis gets tested in at least a few combinations.
    # This helps discover synergistic combos that don't rank highest individually.
    for _ in range(25):
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
    global_elites=None,
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
        global_elites: Optional list of elite genomes from previous runs (cross-run sharing)

    Returns:
        list: Next generation population
    """
    next_gen = [results[i]["Genome"] for i in range(GA_ELITISM)]

    # When exploration is high (e.g., after stagnation/diversity injection),
    # widen parent selection and increase random injection to help cross
    # multi-gene fitness valleys caused by strong stat/gem interactions.
    #
    # current_mutation_rate is already dynamic (see compute_dynamic_mutation),
    # so we use it as a proxy for "how stuck are we?".
    if current_mutation_rate >= 0.35:
        parent_pool_size = 120
        random_inject_prob = 0.35
    elif current_mutation_rate >= 0.30:
        parent_pool_size = 80
        random_inject_prob = 0.25
    else:
        parent_pool_size = 50
        random_inject_prob = 0.18

    parent_pool_size = min(parent_pool_size, len(results))

    # Cross-run elite sharing probability - allows good building blocks from
    # previous runs to propagate via crossover without forcing DB seed injection.
    elite_crossover_prob = 0.15 if global_elites else 0.0

    while len(next_gen) < GA_POPULATION_SIZE:
        if random.random() < random_inject_prob:
            next_gen.append(create_random_genome())
            continue

        # Parent selection with optional cross-run elite sharing
        if global_elites and random.random() < elite_crossover_prob:
            p1 = random.choice(global_elites)
        else:
            p1 = random.choice(results[:parent_pool_size])["Genome"]

        if global_elites and random.random() < elite_crossover_prob:
            p2 = random.choice(global_elites)
        else:
            p2 = random.choice(results[:parent_pool_size])["Genome"]

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

        # Mutation:
        # - Always preserve the existing behavior at low exploration (single-gene mutation).
        # - Under high exploration, allow *macro-mutation* (2-4 independent gene edits)
        #   to jump across fitness valleys where any single edit is detrimental but a
        #   coordinated set is beneficial (common with gem allocation interactions).
        if random.random() < current_mutation_rate:
            # Decide how many independent edits to apply.
            # (This is intentionally small to avoid destabilizing the GA.)
            n_edits = 1
            if current_mutation_rate >= 0.35:
                r = random.random()
                if r < 0.35:
                    n_edits = 4
                elif r < 0.75:
                    n_edits = 3
                else:
                    n_edits = 2
            elif current_mutation_rate >= 0.30 and random.random() < 0.5:
                n_edits = 2

            for _ in range(n_edits):
                mutate_idx = random.randint(0, 8)
                if mutate_idx < 6 and optimize_gear:
                    slot_type = slots[mutate_idx]
                    if gear_pool[slot_type]:
                        child[mutate_idx] = random.choice(gear_pool[slot_type])
                elif mutate_idx >= 6 and optimize_minis:
                    current_mini_names = {m.get("Name") for m in child[6:] if isinstance(m, dict)}
                    candidates = [m for m in mini_pool if m["Name"] not in current_mini_names]
                    if candidates:
                        child[mutate_idx] = random.choice(candidates)

        next_gen.append(child)

    return next_gen
