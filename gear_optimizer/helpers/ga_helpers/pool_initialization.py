"""
Helper functions for genetic algorithm pool initialization.

Production runs are GPU-native; this module keeps the small CPU helpers that remain
useful for pool construction and reference-only tuning logic.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from gear_optimizer.gamedata import Gear, SongMini, song_secondary


def _relevant_row_projection(row: Gear | SongMini, primary_color, secondary_color=""):
    """
    Project a row onto the exact score-relevant axes for the current single-song GA pool build.

    The current runtime fixes `selected_color = primary_color` before `initialize_pools(...)`
    is used, so only the song's primary/secondary elemental lanes remain score-relevant here.
    """
    stats = row.stats
    return (
        stats["Perfect Points"],
        stats["Combo Multiplier"],
        stats["Fever Multiplier"],
        stats["Fever Time"],
        stats["Fever Fill Rate"],
        stats.get(primary_color, 0) if primary_color else 0,
        stats.get(secondary_color, 0) if secondary_color else 0,
    )


def _timing_neutral_relevant_dominates(candidate, other, primary_color, secondary_color=""):
    """
    Return True when `candidate` exactly-safe dominates `other` for the current song context.

    Safe dominance for the live single-song pool build requires:
    - equal timing coordinates `(FT, FF)`, and
    - coordinatewise dominance on the remaining score-relevant axes
      `(PP, CM, FM, val_primary, val_secondary)`,
    - with at least one strict improvement.
    """
    cand_sig = _relevant_row_projection(candidate, primary_color, secondary_color)
    other_sig = _relevant_row_projection(other, primary_color, secondary_color)

    if cand_sig[3] != other_sig[3] or cand_sig[4] != other_sig[4]:
        return False

    strictly_better = False
    for idx in (0, 1, 2, 5, 6):
        if cand_sig[idx] < other_sig[idx]:
            return False
        if cand_sig[idx] > other_sig[idx]:
            strictly_better = True
    return strictly_better


def prune_gear_pool_lossless_for_song(gear_list, primary_color, secondary_color=""):
    """
    Exact-safe pre-GA gear pruning for the current single-song pool initialization path.

    Steps:
    1. Collapse same-slot rows with identical relevant projections (keep the first witness).
    2. Remove rows timing-neutrally dominated in the same song context.
    """
    gear_items = list(gear_list or [])
    if len(gear_items) <= 1:
        return gear_items

    unique_rows = []
    seen_signatures = set()
    for row in gear_items:
        sig = _relevant_row_projection(row, primary_color, secondary_color)
        if sig in seen_signatures:
            continue
        seen_signatures.add(sig)
        unique_rows.append(row)

    pruned = []
    for idx, row in enumerate(unique_rows):
        dominated = False
        for other_idx, other in enumerate(unique_rows):
            if other_idx == idx:
                continue
            if _timing_neutral_relevant_dominates(other, row, primary_color, secondary_color):
                dominated = True
                break
        if not dominated:
            pruned.append(row)
    return pruned


def prune_mini_pool_lossless_for_song(mini_list, primary_color, secondary_color=""):
    """
    Exact-safe pre-GA mini pruning for the current single-song shared distinct-3 pool.

    Safe reductions:
    - cap exact relevant-signature multiplicity at 3 (any legal triple can use at most 3 rows),
    - iteratively remove a row only when 3 distinct dominators still remain in the *current* pool.
    """
    mini_items = list(mini_list or [])
    if len(mini_items) <= 1:
        return mini_items

    capped_rows = []
    multiplicities = {}
    for row in mini_items:
        sig = _relevant_row_projection(row, primary_color, secondary_color)
        seen = multiplicities.get(sig, 0)
        if seen >= 3:
            continue
        multiplicities[sig] = seen + 1
        capped_rows.append(row)

    survivors = list(capped_rows)
    while len(survivors) > 3:
        removed_any = False
        for idx, row in enumerate(survivors):
            dominators = 0
            for other_idx, other in enumerate(survivors):
                if other_idx == idx:
                    continue
                if _timing_neutral_relevant_dominates(other, row, primary_color, secondary_color):
                    dominators += 1
                    if dominators >= 3:
                        break
            if dominators >= 3:
                del survivors[idx]
                removed_any = True
                break
        if not removed_any:
            break

    return survivors


# (primary, secondary, slots) -> (the gear catalog the pools were built from, pools). The entry keeps
# that catalog alive, so the identity check can never match a different, later catalog.
_PRUNED_GEAR_POOL_CACHE: dict[tuple[str, str, tuple[str, ...]], tuple[Mapping[str, Gear], dict[str, list[Gear]]]] = {}


def _get_pruned_gear_pool(gears: Mapping[str, Gear], slots, p_color, s_color=None) -> dict[str, list[Gear]]:
    slots_key = tuple(str(s) for s in slots)
    cache_key = (str(p_color or ""), str(s_color or ""), slots_key)
    cached = _PRUNED_GEAR_POOL_CACHE.get(cache_key)
    if cached is not None and cached[0] is gears:
        return cached[1]

    gear_pool: dict[str, list[Gear]] = {s: [] for s in slots_key}
    for gear in gears.values():
        if gear.slot in gear_pool:
            gear_pool[gear.slot].append(gear)
    for s in slots_key:
        gear_pool[s] = prune_gear_pool_lossless_for_song(gear_pool[s], p_color, s_color)

    if len(_PRUNED_GEAR_POOL_CACHE) >= 8:
        _PRUNED_GEAR_POOL_CACHE.clear()
    _PRUNED_GEAR_POOL_CACHE[cache_key] = (gears, gear_pool)
    return gear_pool


_MINI_COLOR_ORDER = ("Rush", "Flow", "Chill", "Beat", "Vibe")


def _mini_colors(mini: SongMini) -> tuple[str | None, str | None]:
    """A mini's two highest colors (ties keep _MINI_COLOR_ORDER; a zero color counts as none)."""
    ranked = sorted(((c, mini.stats[c]) for c in _MINI_COLOR_ORDER), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0] if ranked[0][1] > 0 else None
    secondary = ranked[1][0] if ranked[1][1] > 0 else None
    return primary, secondary


def _mini_matches_song(mini: SongMini, song_primary: str, song_secondary: str) -> bool:
    """
    A mini joins the pool when its primary color is one of the song's colors, its secondary color is
    the song's primary, or it targets the song and has a song color.
    """
    if mini.targets_song:
        if song_primary and mini.stats.get(song_primary, 0) > 0:
            return True
        if song_secondary and mini.stats.get(song_secondary, 0) > 0:
            return True
    mini_primary, mini_secondary = _mini_colors(mini)
    if mini_primary == song_primary:
        return True
    if song_secondary and mini_primary == song_secondary:
        return True
    return mini_secondary == song_primary


def initialize_pools(
    gears: Mapping[str, Gear],
    minis: Sequence[SongMini],
    p_color: str,
    slots,
    s_color: str | None = None,
) -> tuple[dict[str, list[Gear]], list[SongMini]]:
    """
    The song's gear pool per slot (from the gear catalog, by name) and its mini pool, pruned exactly (no
    loadout that can win is lost):
    - gear: relevant-signature quotient + timing-neutral dominance
    - minis: the song-color filter, then relevant-signature cap-to-3 + timing-neutral support-set prune

    Both prunes keep first witnesses, so the input order (the CSV order) matters.
    """
    secondary = song_secondary(p_color, s_color)
    mini_pool = [m for m in minis if _mini_matches_song(m, p_color, secondary)]
    mini_pool = prune_mini_pool_lossless_for_song(mini_pool, p_color, s_color)
    if not mini_pool:
        raise ValueError(f"no mini matches the song colors {p_color!r}/{s_color!r}")
    return _get_pruned_gear_pool(gears, slots, p_color, s_color), mini_pool
