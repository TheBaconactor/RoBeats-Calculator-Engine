"""
GA Diversity - stagnation handling for reference GA helpers.

This module provides diversity and stagnation handling:
- update_mutation_and_diversity: Track diversity and adjust mutation dynamically
"""

import random

from ...core.constants import GA_MUTATION_RATE_MAX, GA_POPULATION_SIZE, GA_ELITISM


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
    mini_pool=None,
    gear_pool=None,
    slots=None,
    optimize_gear=True,
    optimize_minis=True,
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
        mini_pool: Optional list of minis for coordinated perturbation
        gear_pool: Optional dict of gear pools for coordinated perturbation
        slots: Optional list of slot names for coordinated perturbation
        optimize_gear: Whether gear optimization is enabled
        optimize_minis: Whether mini optimization is enabled

    Returns:
        tuple: (updated_population, updated_mutation_rate, updated_last_improvement_gen)
    """
    if generation - last_improvement_gen >= stagnation_limit:
        # Bump the *base* mutation rate, then compute an "effective" rate that
        # includes the exploration boost (cache-hit driven) so downstream logic
        # can react immediately in this generation.
        #
        # NOTE: Historically we printed/used the pre-bump `current_mutation_rate`
        # (computed earlier in the loop), which under-reported mutation and
        # made diversity injection less aggressive than intended.
        mutation_rate = min(GA_MUTATION_RATE_MAX, mutation_rate + 0.08)
        effective_mutation_rate = min(0.6, mutation_rate + exploration_boost)
        print(
            f"  >> Stagnation detected (Run {run_idx + 1}), "
            f"mutation_base -> {mutation_rate:.3f} "
            f"(effective: {effective_mutation_rate:.3f}, boost: {exploration_boost:.3f}), "
            f"injecting diversity"
        )
        elites = [r["Genome"] for r in results[:GA_ELITISM]]
        population = elites[:]

        # NEW: Coordinated Elite Perturbation
        # Create variants of each elite with 2-3 genes swapped simultaneously.
        # This helps escape fitness valleys that require coordinated changes
        # (e.g., swapping a mini AND changing gear simultaneously).
        if mini_pool and gear_pool and slots:
            for elite in elites:
                for _ in range(3):  # 3 perturbation variants per elite
                    perturbed = list(elite)
                    n_swaps = random.choice([2, 2, 3])  # Bias toward 2 swaps

                    # Choose swap indices - at least one gear, at least one mini
                    swap_indices = []
                    if optimize_gear and random.random() < 0.7:
                        swap_indices.append(random.randint(0, 5))  # gear
                    if optimize_minis and random.random() < 0.8:
                        swap_indices.append(random.randint(6, 8))  # mini

                    # Fill remaining swaps randomly
                    while len(swap_indices) < n_swaps:
                        idx = random.randint(0, 8)
                        if idx not in swap_indices:
                            swap_indices.append(idx)

                    # Apply swaps
                    for idx in swap_indices:
                        if idx < 6 and optimize_gear:
                            slot_type = slots[idx]
                            if gear_pool.get(slot_type):
                                perturbed[idx] = random.choice(gear_pool[slot_type])
                        elif idx >= 6 and optimize_minis:
                            current_names = {m.get("Name") for m in perturbed[6:] if isinstance(m, dict)}
                            candidates = [m for m in mini_pool if m.get("Name") not in current_names]
                            if candidates:
                                perturbed[idx] = random.choice(candidates)

                    population.append(perturbed)

        # === FIX 2: Diverse Mini Injection ===
        # When stuck, explicitly inject genomes using minis that are NOT in the current best.
        # This forces exploration of alternative mini teams.
        if mini_pool and optimize_minis and results:
            # Get the best genome's minis
            best_genome = results[0]["Genome"]
            best_mini_names = set()
            for m in best_genome[6:]:
                if isinstance(m, dict):
                    best_mini_names.add(m.get("Name", ""))
                elif m:
                    best_mini_names.add(str(m))

            # Get alternative minis (NOT in current best but in top pool)
            # Use broader pool for diversity
            alternative_minis = [m for m in mini_pool if m.get("Name") not in best_mini_names]

            if len(alternative_minis) >= 3:
                # Inject genomes using top 10 alternative minis
                top_alt = alternative_minis[:10]
                for _ in range(8):  # 8 diverse mini genomes
                    # Use random gear from pool + alternative minis
                    genome = []
                    if optimize_gear and gear_pool and slots:
                        for s in slots:
                            genome.append(random.choice(gear_pool[s]) if gear_pool.get(s) else {})
                    else:
                        genome.extend(best_genome[:6])  # Keep current best gear

                    # Sample 3 random minis from alternatives
                    sample_size = min(3, len(top_alt))
                    genome.extend(random.sample(top_alt, sample_size))
                    population.append(genome)

                # Also inject a few genomes using the BEST gear but alternative minis
                # This specifically tests if the current gear + different minis is better
                for _ in range(5):
                    genome = list(best_genome[:6])  # Clone best gear
                    sample_size = min(3, len(top_alt))
                    genome.extend(random.sample(top_alt, sample_size))
                    population.append(genome)

        # More aggressive reinjection when exploration is already high.
        # This helps escape deep local basins where single-gene improvements are rare.
        reinject_frac = 0.4
        if effective_mutation_rate >= 0.35:
            reinject_frac = 0.7
        elif effective_mutation_rate >= 0.30:
            reinject_frac = 0.55

        reinject_target = int(GA_POPULATION_SIZE * reinject_frac)
        while len(population) < reinject_target:
            population.append(create_random_genome())
        while len(population) < GA_POPULATION_SIZE:
            population.append(create_heuristic_genome())
        last_improvement_gen = generation

    return population, mutation_rate, last_improvement_gen
