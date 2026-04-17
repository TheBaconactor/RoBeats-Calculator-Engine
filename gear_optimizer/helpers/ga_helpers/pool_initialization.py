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

from ...core.utils import prune_gear_pool_lossless_for_song, prune_mini_pool_lossless_for_song

_PRUNED_GEAR_POOL_CACHE: dict[
    tuple[int, int, str, str, tuple[str, ...]], tuple[dict[str, list[dict]], int, int]
] = {}


def _get_pruned_gear_pool(all_gears, slots, p_color, s_color=None):
    slots_key = tuple(str(s) for s in slots)
    cache_key = (
        int(id(all_gears)),
        int(len(all_gears or [])),
        str(p_color or ""),
        str(s_color or ""),
        slots_key,
    )
    cached = _PRUNED_GEAR_POOL_CACHE.get(cache_key)
    if cached is not None:
        gear_pool_cached, total_before, total_after = cached
        return gear_pool_cached, int(total_before), int(total_after), True

    gear_pool = {s: [] for s in slots_key}
    for g in all_gears:
        slot_name = g.get("type")
        if slot_name in gear_pool:
            gear_pool[slot_name].append(g)

    total_before = sum(len(gear_pool[s]) for s in slots_key)
    for s in slots_key:
        gear_pool[s] = prune_gear_pool_lossless_for_song(gear_pool[s], p_color, s_color)
    total_after = sum(len(gear_pool[s]) for s in slots_key)

    _PRUNED_GEAR_POOL_CACHE[cache_key] = (gear_pool, total_before, total_after)
    if len(_PRUNED_GEAR_POOL_CACHE) > 8:
        _PRUNED_GEAR_POOL_CACHE.clear()
        _PRUNED_GEAR_POOL_CACHE[cache_key] = (gear_pool, total_before, total_after)
    return gear_pool, int(total_before), int(total_after), False


def initialize_pools(all_gears, all_minis, p_color, slots, s_color=None):
    """
    Initialize and prune gear and mini pools.

    Creates per-slot gear pools and filters minis based on color matching.
    A mini is included if:
    - Mini primary matches song primary OR secondary, OR
    - Mini secondary matches song primary
    Applies exact-safe song-aware pruning for the current single-song GA runtime:
    - gear: relevant-signature quotient + timing-neutral dominance
    - minis: relevant-signature cap-to-3 + timing-neutral singleton support-set prune

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
            - Empty list (whitelisting removed)
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

    # Filter minis first, then run the exact-safe shared-pool mini prune for this song pair.
    mini_pool = [m for m in all_minis if mini_matches_song(m, p_color, s_color)]
    mini_pool = prune_mini_pool_lossless_for_song(mini_pool, p_color, s_color)

    if not mini_pool:
        print("No valid minis found (Primary Color check).")
        return None, [], 0, 0, []

    # Initialize/prune gear pools once per gear dataset + song color pair.
    gear_pool, total_before, total_after, from_cache = _get_pruned_gear_pool(all_gears, slots, p_color, s_color)

    return gear_pool, mini_pool, total_before, total_after, []  # No more whitelisted minis
