"""Build exact-safe per-song gear and mini pools."""

from ..core.catalog_fingerprint import catalog_sequence_fingerprint
from ..core.utils import prune_gear_pool_lossless_for_song, prune_mini_pool_lossless_for_song
from ..data.mini_ascension import normalize_song_secondary

_PRUNED_GEAR_POOL_CACHE: dict[
    tuple[int, bytes, str, str, tuple[str, ...]],
    tuple[object, dict[str, list[dict]], int, int],
] = {}


def _get_pruned_gear_pool(all_gears, slots, p_color, s_color=None):
    slots_key = tuple(str(s) for s in slots)
    catalog_fingerprint = catalog_sequence_fingerprint(all_gears)
    cache_key = (
        int(id(all_gears)),
        catalog_fingerprint,
        str(p_color or ""),
        str(s_color or ""),
        slots_key,
    )
    cached = _PRUNED_GEAR_POOL_CACHE.get(cache_key)
    if cached is not None:
        source, gear_pool_cached, total_before, total_after = cached
        if source is all_gears:
            return gear_pool_cached, int(total_before), int(total_after)

    gear_pool = {s: [] for s in slots_key}
    for g in all_gears:
        slot_name = g.get("type")
        if slot_name in gear_pool:
            gear_pool[slot_name].append(g)

    total_before = sum(len(gear_pool[s]) for s in slots_key)
    for s in slots_key:
        gear_pool[s] = prune_gear_pool_lossless_for_song(gear_pool[s], p_color, s_color)
    total_after = sum(len(gear_pool[s]) for s in slots_key)

    # Retaining the source defeats Python object-id reuse while this entry is live;
    # the content digest above also invalidates same-object name/slot/stat edits.
    entry = (all_gears, gear_pool, total_before, total_after)
    _PRUNED_GEAR_POOL_CACHE[cache_key] = entry
    if len(_PRUNED_GEAR_POOL_CACHE) > 8:
        _PRUNED_GEAR_POOL_CACHE.clear()
        _PRUNED_GEAR_POOL_CACHE[cache_key] = entry
    return gear_pool, int(total_before), int(total_after)


def initialize_pools(all_gears, all_minis, p_color, slots, s_color=None):
    """
    Initialize and prune gear and mini pools.

    Creates per-slot gear pools and filters minis based on color matching.
    A mini is included if:
    - Mini primary matches song primary OR secondary, OR
    - Mini secondary matches song primary
    Applies exact-safe song-aware pruning for the current single-song runtime:
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
        normalized_secondary = normalize_song_secondary(song_primary, song_secondary)
        if bool((mini or {}).get("Mini Ascension Song Target Applied")):
            if song_primary and int((mini or {}).get(song_primary, 0) or 0) > 0:
                return True
            if normalized_secondary and int((mini or {}).get(normalized_secondary, 0) or 0) > 0:
                return True

        mini_primary, mini_secondary = get_mini_colors(mini)

        # Mini primary color matches song's primary OR secondary
        if mini_primary == song_primary:
            return True
        if normalized_secondary and mini_primary == normalized_secondary:
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
    gear_pool, total_before, total_after = _get_pruned_gear_pool(all_gears, slots, p_color, s_color)

    return gear_pool, mini_pool, total_before, total_after, []  # No more whitelisted minis
