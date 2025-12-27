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

from ...core.utils import prune_dominated_gear


def initialize_pools(all_gears, all_minis, p_color, slots, s_color=None):
    """
    Initialize and prune gear and mini pools.

    Creates per-slot gear pools and filters minis based on color matching.
    A mini is included if:
    - Mini primary matches song primary OR secondary, OR
    - Mini secondary matches song primary
    Applies dominance pruning to remove strictly inferior gear items.

    Args:
        all_gears: List of all gear items
        all_minis: List of all mini items
        p_color: Song's primary color
        slots: List of gear slot names
        s_color: Song's secondary color (optional)

    Returns:
        tuple: (gear_pool, mini_pool, total_before, total_after, [])
            - gear_pool: Dict mapping slot names to lists of gear
            - mini_pool: List of valid minis (matching song colors)
            - total_before: Total gear count before pruning
            - total_after: Total gear count after pruning
            - Empty list (legacy compatibility, whitelisting removed)
    """
    # Color stats to check for mini primary/secondary determination
    color_stats = ["Rush", "Flow", "Chill", "Beat", "Vibe"]

    def get_mini_colors(mini):
        """Get a mini's primary and secondary colors (top 2 highest stat colors)."""
        color_values = [(c, mini.get(c, 0)) for c in color_stats]
        # Sort by value descending
        sorted_colors = sorted(color_values, key=lambda x: x[1], reverse=True)
        primary = sorted_colors[0][0] if sorted_colors[0][1] > 0 else None
        secondary = sorted_colors[1][0] if len(sorted_colors) > 1 and sorted_colors[1][1] > 0 else None
        return primary, secondary

    def mini_matches_song(mini, song_primary, song_secondary):
        """
        Check if mini matches song colors for pool inclusion.
        - Mini primary matches song primary OR secondary, OR
        - Mini secondary matches song primary
        """
        mini_primary, mini_secondary = get_mini_colors(mini)

        # Mini primary color matches song's primary OR secondary
        if mini_primary == song_primary:
            return True
        if song_secondary and mini_primary == song_secondary:
            return True

        # Mini secondary matches song primary
        if mini_secondary == song_primary:
            return True

        return False

    # Filter minis: include only if mini's PRIMARY color matches song's primary/secondary
    mini_pool = [m for m in all_minis if mini_matches_song(m, p_color, s_color)]

    if not mini_pool:
        print("No valid minis found (Primary Color check).")
        return None, [], 0, 0, []

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

    return gear_pool, mini_pool, total_before, total_after, []  # No more whitelisted minis

