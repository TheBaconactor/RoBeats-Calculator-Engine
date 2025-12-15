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

# Support deterministic testing via GA_SEED environment variable
_GA_SEED = os.environ.get("GA_SEED")
if _GA_SEED is not None:
    _GA_SEED = int(_GA_SEED)
    random.seed(_GA_SEED)

from ...core.constants import GA_POPULATION_SIZE, GA_MUTATION_RATE, GA_MUTATION_RATE_MAX, GA_ELITISM
from ...core.utils import prune_dominated_gear, SKIP_ITEM_KEYS
from ...data.database import get_loadout_hash
from ...solver.scoring import worker_coevolution_evaluate, batch_evaluate_genomes


def initialize_pools(all_gears, all_minis, p_color, slots, s_color=None):
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
    
    # Load mini exceptions from CSV (configurable overrides)
    # Format: MiniName,PrimaryColor,SecondaryColor
    try:
        import csv
        from ...core.constants import PATHS
        exceptions_path = os.path.join(PATHS.data_dir, "Gear", "MiniExceptions.csv")
        if os.path.exists(exceptions_path):
            with open(exceptions_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    mini_name = row.get("MiniName", "").strip()
                    req_primary = row.get("PrimaryColor", "").strip()
                    req_secondary = row.get("SecondaryColor", "").strip()
                    
                    # Check if this exception applies to current song
                    if req_primary == p_color:
                        if req_secondary == "Any" or req_secondary == s_color:
                            # Find and add the mini if not already in pool
                            exception_mini = next((m for m in all_minis if m.get("Name") == mini_name), None)
                            if exception_mini and exception_mini not in mini_pool:
                                mini_pool.append(exception_mini)
    except Exception as e:
        # Silently ignore if file doesn't exist or has errors
        pass
    
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

