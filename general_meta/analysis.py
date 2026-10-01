from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from collections.abc import Mapping

from gear_optimizer.core.gem_defs import extract_gem_totals
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.gamedata import Gear, Mini, ascended_mini_stats

_ELEMENT_ORDER: Tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")
_GENERAL_META_EXCLUDED_RANK_DIFFICULTIES = frozenset({"Easy"})
_GEM_KEYS = ("PP", "CM", "FM", "FT", "FF", "Element")  # the order of GemTotals.as_tuple()


def _scores(row: dict) -> tuple[int, int]:
    """(base score, FG score) of a stored row (a missing score counts as 0)."""
    return row.get("score") or 0, row.get("fg_score") or 0


def _effective_score(loadout: dict) -> int:
    """The row's best achievable score: its FG score when Force Greats beat the base score."""
    return max(_scores(loadout))


def _song_name(song: dict) -> str:
    return str((song or {}).get("song_name") or "").strip()


def _song_difficulty(song: dict) -> str:
    return str((song or {}).get("difficulty") or "").strip()


def _is_general_meta_ranked_song(song: dict) -> bool:
    return _song_difficulty(song) not in _GENERAL_META_EXCLUDED_RANK_DIFFICULTIES


def _loadout_key_fingerprint(gears: tuple[str, ...], mini_sig: tuple[Any, ...]) -> str:
    """
    Return a stable, category-aware fingerprint for a (gear set + mini effect signature).

    This is used to cheaply compare category winners across TeamBuff tiers without
    being sensitive to representative mini-name choice.
    """
    payload = json.dumps([list(gears), list(mini_sig)], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _relevant_elements_for_category(songs: List[dict]) -> Tuple[str, ...]:
    """
    Determine which element stats can affect scoring for this category.

    Returns the union of all primary/secondary elements present in the provided songs.
    """
    elements = set()
    for song in songs:
        primary = (song.get("primary") or "").strip()
        secondary = (song.get("secondary") or "").strip()
        if primary:
            elements.add(primary)
        if secondary:
            elements.add(secondary)

    order = {name: idx for idx, name in enumerate(_ELEMENT_ORDER)}
    return tuple(sorted(elements, key=lambda el: order.get(el, 999)))


def _mini_set_effect_signature(
    mini_names: Tuple[str, ...],
    minis_by_name: Mapping[str, Mini],
    relevant_elements: Tuple[str, ...],
    songs: Tuple[dict, ...],
) -> Tuple[Any, ...]:
    """
    Build the exact category-wide scoring signature for a mini set.

    This allows GeneralMeta to merge mini variants that differ only in stats that
    cannot affect scoring for the current category (e.g., extra Rush in a Vibe/Vibe category),
    while keeping variants with different song-target Ascension effects distinct.
    """
    if not mini_names:
        return ("stats", 0, 0, 0, 0, 0, *([0] * len(relevant_elements)))

    for name in mini_names:
        if name not in minis_by_name:
            return ("names", mini_names)

    per_song_stats: list[tuple[Any, ...]] = []
    for song in songs:
        song_name = _song_name(song)
        primary = str(song.get("primary") or "").strip()
        secondary = str(song.get("secondary") or "").strip()
        pp = cm = fm = ft = ff = 0
        elem_totals = [0] * len(relevant_elements)
        for name in mini_names:
            stats = ascended_mini_stats(minis_by_name[name], song_name, primary, secondary)
            pp += stats["Perfect Points"]
            cm += stats["Combo Multiplier"]
            fm += stats["Fever Multiplier"]
            ft += stats["Fever Time"]
            ff += stats["Fever Fill Rate"]
            for idx, element in enumerate(relevant_elements):
                elem_totals[idx] += stats.get(element, 0)
        per_song_stats.append((song_name, pp, cm, fm, ft, ff, *elem_totals))

    return ("song-aware-stats", *per_song_stats)


def _pick_representative_variant(variants: Counter) -> Tuple[Any, ...]:
    """
    Pick a deterministic representative from a Counter of name-tuples.

    - Prefer the most frequent variant.
    - Break ties lexicographically for determinism.
    """
    if not variants:
        return ()
    max_count = max(variants.values())
    tied = [variant for variant, count in variants.items() if count == max_count]
    return min(tied)


def _row_mode(row: dict) -> str:
    score, fg_score = _scores(row)
    return "fg" if fg_score > score else "meta"


def _row_mode_score(row: dict, mode: str) -> int:
    return _scores(row)[1 if mode == "fg" else 0]


def _rank_index_for_song_mode(rows: list[dict], target: dict, mode: str) -> int | None:
    ranked = [row for row in rows if _row_mode_score(row, mode) > 0 and (mode != "fg" or _row_mode(row) == "fg")]
    ranked.sort(
        key=lambda row: (
            -_row_mode_score(row, mode),
            str(row.get("loadout_hash") or ""),
            tuple(str(v or "") for v in (row.get("gear") or [])),
            tuple(tuple(str(v or "") for v in group) for group in (row.get("mini_groups") or [])),
        )
    )

    target_hash = str(target.get("loadout_hash") or "").strip()
    for idx, row in enumerate(ranked):
        if target_hash and str(row.get("loadout_hash") or "").strip() == target_hash:
            return idx
        if row is target:
            return idx
    return None


def _song_win_entry(row: dict, *, mode: str, rank_index: int | None, team_buff: str | None = None) -> dict:
    song_name = str(row.get("song_name") or "").strip()
    loadout_hash = str(row.get("loadout_hash") or "").strip()
    score, fg_score = _scores(row)
    out = {
        "song_id": song_name,
        "song_name": song_name,
        "mode": mode,
        "score": _row_mode_score(row, mode),
        "base_score": score,
        "fg_score": fg_score,
    }
    if team_buff:
        out["team_buff"] = team_buff
    if loadout_hash:
        out["loadout_hash"] = loadout_hash
    if rank_index is not None:
        out["rank_index"] = rank_index
        out["rank"] = rank_index + 1
    return out


def _minis_keys_from_groups(mini_groups: object) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
    """
    Convert decoded mini variant groups into:
    - representative mini names (sorted; multiplicity preserved)
    - a canonical "variant key" that preserves per-slot variant groups
    """
    groups: list[list[str]] = []
    if isinstance(mini_groups, list):
        for g0 in mini_groups:
            if not isinstance(g0, list):
                continue
            names = [str(n).strip() for n in g0 if n]
            names = sorted(set([n for n in names if n]))
            if names:
                groups.append(names)

    reps = representative_mini_names(groups)
    rep_key = tuple(sorted([n for n in reps if n]))
    variant_key = tuple(sorted(tuple(g) for g in groups))
    return rep_key, variant_key


@dataclass
class _SetWins:
    """What one gear + mini-effect set won in a category."""

    rows: list[dict] = field(default_factory=list)  # its winning rows in ranked (non-Easy) songs
    all_rows: list[dict] = field(default_factory=list)  # its winning rows in every song (the gem/score averages)
    variants: Counter = field(default_factory=Counter)  # mini variant groups of the ranked wins
    song_wins: list[dict] = field(default_factory=list)


def _category_wins(
    songs: List[dict],
    loadouts_by_song: Mapping[str, list],
    minis_by_name: Mapping[str, Mini],
    gears_by_name: Optional[Mapping[str, Gear]],
) -> dict[tuple, _SetWins]:
    """Each song's best row (by effective score), grouped by its gear set + mini effect signature."""
    songs_by_name = {name: song for song in songs if (name := _song_name(song))}
    relevant_elements = _relevant_elements_for_category(songs)
    signature_songs = tuple(sorted(songs_by_name.values(), key=_song_name))
    signatures: dict[tuple[str, ...], Tuple[Any, ...]] = {}
    sets: dict[tuple, _SetWins] = {}
    for song_name in sorted(songs_by_name):
        loadouts = loadouts_by_song.get(song_name)
        if not loadouts:
            continue
        best = max(loadouts, key=_effective_score)
        rep_names, variant_key = _minis_keys_from_groups(best.get("mini_groups"))
        if rep_names not in signatures:
            signatures[rep_names] = _mini_set_effect_signature(
                rep_names, minis_by_name, relevant_elements, signature_songs
            )
        gears = list(best.get("gear") or [])
        ordered_gears = sort_gears_by_slot(gears, gears_by_name) if gears_by_name else sorted(gears)
        won = sets.setdefault((tuple(ordered_gears), signatures[rep_names]), _SetWins())
        won.all_rows.append(best)
        if _is_general_meta_ranked_song(songs_by_name[song_name]):
            mode = _row_mode(best)
            won.rows.append(best)
            won.variants[variant_key] += 1
            won.song_wins.append(
                _song_win_entry(
                    best,
                    mode=mode,
                    rank_index=_rank_index_for_song_mode(loadouts, best, mode),
                    team_buff=str(best.get("team_buff") or "").strip() or None,
                )
            )
    return sets


def _peak_songs(rows: list[dict], *, fg: bool) -> list[str]:
    """The songs among `rows` won by Force Greats (fg) or by the base score (not fg)."""
    return sorted(
        {str(r.get("song_name") or "") for r in rows if (r.get("song_name") or "").strip() and (_row_mode(r) == "fg") == fg}
    )


def _set_summary(rank: int, key: tuple, won: _SetWins) -> dict:
    gears, signature = key
    gem_sums = dict.fromkeys(_GEM_KEYS, 0)
    for row in won.all_rows:
        totals = extract_gem_totals(json.loads(row.get("details_json") or "{}"))
        for gem, count in zip(_GEM_KEYS, totals.as_tuple()):
            gem_sums[gem] += count
    denom = len(won.all_rows)
    peak_in_songs_meta = _peak_songs(won.rows, fg=False)
    peak_in_songs_fg = _peak_songs(won.rows, fg=True)
    return {
        "rank": rank,
        "loadout_key": _loadout_key_fingerprint(gears, signature),
        "gear_names": list(gears),
        "mini_groups": [list(group) for group in _pick_representative_variant(won.variants)],
        "peak_in_songs": sorted(set(peak_in_songs_meta) | set(peak_in_songs_fg)),
        "peak_in_songs_meta": peak_in_songs_meta,
        "peak_in_songs_fg": peak_in_songs_fg,
        "song_wins": sorted(won.song_wins, key=lambda item: (str(item.get("song_name") or ""), str(item.get("mode") or ""))),
        "songs_with_set": len(won.rows),
        "win_frequency": len(won.rows),
        "avg_score": int(sum(_effective_score(row) for row in won.all_rows) / denom),
        "avg_gems": (
            _round_mean_gems_to_total(gem_sums, denom, total=90)
            if sum(gem_sums.values()) > 0
            else dict.fromkeys(gem_sums, 0)
        ),
    }


def find_most_common_loadout(
    songs: List[dict],
    loadouts_by_song: Mapping[str, list],
    minis_by_name: Mapping[str, Mini],
    *,
    gears_by_name: Optional[Mapping[str, Gear]] = None,
) -> List[dict]:
    """
    The gear + mini sets that win this category's songs, most ranked (non-Easy) wins first, with their gems and
    scores averaged over every song they win (Easy included).
    """
    sets = _category_wins(songs, loadouts_by_song, minis_by_name, gears_by_name)
    ranked = sorted(((key, won) for key, won in sets.items() if won.rows), key=lambda kv: (-len(kv[1].rows), kv[0]))
    return [_set_summary(rank, key, won) for rank, (key, won) in enumerate(ranked, start=1)]


def sort_gears_by_slot(gear_names: List[str], gears_by_name: Mapping[str, Gear]) -> List[str]:
    slot_order = {
        "Hat": 0,
        "Neck": 1,
        "Face": 2,
        "Shirt": 3,
        "Back": 4,
        "Pants": 5,
        "Pant": 5,
    }

    def get_slot_index(gear_name: str) -> int:
        gear = gears_by_name.get(gear_name)
        slot = gear.slot if gear is not None else ""
        for prefix, idx in slot_order.items():
            if slot.startswith(prefix):
                return idx
        return 99

    return sorted(gear_names, key=get_slot_index)


def _round_mean_gems_to_total(gem_sums: Dict[str, int], denom: int, *, total: int) -> Dict[str, int]:
    """
    Convert per-field gem sums into an integer mean allocation that always sums to `total`.

    This uses a largest-remainder style allocation so that:
    - the vector is as close as possible to the true mean,
    - the sum is exact (no 89/91 gem artifacts from independent rounding).
    """
    keys = _GEM_KEYS
    means: Dict[str, float] = {k: gem_sums.get(k, 0) / denom for k in keys}
    floors: Dict[str, int] = {k: math.floor(means[k]) for k in keys}

    remaining = total - sum(floors.values())
    if remaining == 0:
        return floors

    def remainder_order(k: str) -> tuple[float, float, int]:
        # Largest fractional part (then mean) gains a gem first; the smallest loses one first.
        return (means[k] - floors[k], means[k], keys.index(k))

    if remaining > 0:
        for k in sorted(keys, key=remainder_order, reverse=True):
            if remaining <= 0:
                break
            floors[k] += 1
            remaining -= 1
    else:
        for k in sorted(keys, key=remainder_order):
            if remaining >= 0:
                break
            if floors[k] <= 0:
                continue
            floors[k] -= 1
            remaining += 1

    # Sums far from `total` (rows without a full gem set) leave a remainder: spread it round-robin.
    i = 0
    while remaining != 0 and i < 10_000:
        k = keys[i % len(keys)]
        if remaining > 0:
            floors[k] += 1
            remaining -= 1
        elif floors[k] > 0:
            floors[k] -= 1
            remaining += 1
        i += 1

    return floors


def format_gem_counts(avg_gems: Dict[str, int]) -> Dict[str, int]:
    return {
        "Perfect Points": avg_gems["PP"],
        "Combo Multiplier": avg_gems["CM"],
        "Fever Multiplier": avg_gems["FM"],
        "Fever Time": avg_gems["FT"],
        "Fever Fill Rate": avg_gems["FF"],
        "Element": avg_gems["Element"],
    }


__all__ = [
    "find_most_common_loadout",
    "format_gem_counts",
    "sort_gears_by_slot",
]
