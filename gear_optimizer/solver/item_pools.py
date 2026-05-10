from __future__ import annotations

from gear_optimizer.core.utils import prune_gear_pool_lossless_for_song, prune_mini_pool_lossless_for_song


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
        return gear_pool_cached, int(total_before), int(total_after)

    gear_pool = {s: [] for s in slots_key}
    for gear in all_gears:
        slot_name = gear.get("type")
        if slot_name in gear_pool:
            gear_pool[slot_name].append(gear)

    total_before = sum(len(gear_pool[s]) for s in slots_key)
    for slot_name in slots_key:
        gear_pool[slot_name] = prune_gear_pool_lossless_for_song(gear_pool[slot_name], p_color, s_color)
    total_after = sum(len(gear_pool[s]) for s in slots_key)

    _PRUNED_GEAR_POOL_CACHE[cache_key] = (gear_pool, total_before, total_after)
    if len(_PRUNED_GEAR_POOL_CACHE) > 8:
        _PRUNED_GEAR_POOL_CACHE.clear()
        _PRUNED_GEAR_POOL_CACHE[cache_key] = (gear_pool, total_before, total_after)
    return gear_pool, int(total_before), int(total_after)


def initialize_item_pools(all_gears, all_minis, p_color, slots, s_color=None):
    color_stats = ("Rush", "Flow", "Chill", "Beat", "Vibe")

    def get_mini_colors(mini):
        color_values = [(color, mini.get(color, 0)) for color in color_stats]
        sorted_colors = sorted(color_values, key=lambda row: row[1], reverse=True)
        primary = sorted_colors[0][0] if sorted_colors[0][1] > 0 else None
        secondary = sorted_colors[1][0] if len(sorted_colors) > 1 and sorted_colors[1][1] > 0 else None
        return primary, secondary

    def mini_matches_song(mini, song_primary, song_secondary):
        mini_primary, mini_secondary = get_mini_colors(mini)
        if mini_primary == song_primary:
            return True
        if song_secondary and mini_primary == song_secondary:
            return True
        return mini_secondary == song_primary

    mini_pool = [mini for mini in all_minis if mini_matches_song(mini, p_color, s_color)]
    mini_pool = prune_mini_pool_lossless_for_song(mini_pool, p_color, s_color)
    if not mini_pool:
        print("No valid minis found (Primary Color check).")
        return None, [], 0, 0, []

    gear_pool, total_before, total_after = _get_pruned_gear_pool(all_gears, slots, p_color, s_color)
    return gear_pool, mini_pool, total_before, total_after, []
