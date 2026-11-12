"""Which gear + mini sets win an elemental category's songs, from each song's stored leaderboard rows."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from gear_optimizer.core.team_buff import OPTIMIZER_BASELINE_TEAM_BUFF
from gear_optimizer.data.loadout_equivalence import normalize_minis_groups_for_display, representative_mini_names
from gear_optimizer.gamedata import Gear, Mini, ascended_mini_stats
from gear_optimizer.rules import GEM_BUDGET

ELEMENT_ORDER: tuple[str, ...] = ("Chill", "Flow", "Rush", "Beat", "Vibe")
_ELEMENT_RANK = {name: idx for idx, name in enumerate(ELEMENT_ORDER)}
_GEM_KEYS = ("PP", "CM", "FM", "FT", "FF", "Element")  # the order of stats.GEM_KINDS: a row's stored gems
_SLOT_ORDER = {"Hat": 0, "Neck": 1, "Face": 2, "Shirt": 3, "Back": 4, "Pants": 5, "Pant": 5}


@dataclass(frozen=True, slots=True)
class Song:
    """An official chart as General Meta groups it (its header fields, stripped by chart.read_header)."""

    name: str
    difficulty: str  # the chart library folder: Easy songs count in the averages, not in the ranking
    primary: str
    secondary: str


@dataclass(frozen=True, slots=True)
class Row:
    """One stored leaderboard row of a song, with the gems of the board it is served from."""

    loadout_hash: str  # unique among a song's rows (the loadouts table's key)
    score: int
    fg_score: int  # 0: never evaluated with Force Greats
    gear: tuple[str, ...]
    minis: tuple[tuple[str, ...], ...]  # per equipped mini, the names equivalent for this song
    gems: tuple[int, ...]  # counts in _GEM_KEYS order

    @property
    def fg_won(self) -> bool:
        return self.fg_score > self.score

    @property
    def best_score(self) -> int:
        """The row's best achievable score: its FG score when Force Greats beat the base score."""
        return max(self.score, self.fg_score)


@dataclass(frozen=True, slots=True)
class RankedSet:
    """A gear + mini-effect set of a category: what it won and its averages over every song it won."""

    rank: int
    loadout_key: str
    gear: tuple[str, ...]  # slot order
    mini_groups: tuple[tuple[str, ...], ...]  # the most frequent mini variant of its ranked wins
    peak_in_songs: list[str]
    peak_in_songs_meta: list[str]
    peak_in_songs_fg: list[str]
    song_wins: list[dict]
    wins: int  # ranked (non-Easy) songs won
    avg_score: int
    avg_gems: dict[str, int]


def relevant_elements(songs: Sequence[Song]) -> tuple[str, ...]:
    """The elements whose stats can score in these songs: their colors, in element order."""
    elements = {color for song in songs for color in (song.primary, song.secondary) if color}
    return tuple(sorted(elements, key=lambda el: _ELEMENT_RANK.get(el, 999)))


def sort_gears_by_slot(gear_names: Sequence[str], gears_by_name: Mapping[str, Gear]) -> list[str]:
    """Gear in slot order (Hat to Pants); a name the catalog lacks goes last."""

    def slot_index(name: str) -> int:
        gear = gears_by_name.get(name)
        slot = gear.slot if gear is not None else ""
        return next((idx for prefix, idx in _SLOT_ORDER.items() if slot.startswith(prefix)), 99)

    return sorted(gear_names, key=slot_index)


def _mini_set_effect_signature(
    mini_names: tuple[str, ...],
    minis_by_name: Mapping[str, Mini],
    elements: tuple[str, ...],
    songs: tuple[Song, ...],
) -> tuple[Any, ...]:
    """
    The category-wide scoring signature of a mini set: its summed stats in each song of the category.

    Mini variants that differ only in stats no song of the category scores with (extra Rush in a Vibe/Vibe
    category) share a signature; variants with different song-target Ascension effects do not.
    """
    if not mini_names:
        return ("stats", 0, 0, 0, 0, 0, *([0] * len(elements)))
    if any(name not in minis_by_name for name in mini_names):
        return ("names", mini_names)

    per_song_stats: list[tuple[Any, ...]] = []
    for song in songs:
        pp = cm = fm = ft = ff = 0
        elem_totals = [0] * len(elements)
        for name in mini_names:
            stats = ascended_mini_stats(minis_by_name[name], song.name, song.primary, song.secondary)
            pp += stats["Perfect Points"]
            cm += stats["Combo Multiplier"]
            fm += stats["Fever Multiplier"]
            ft += stats["Fever Time"]
            ff += stats["Fever Fill Rate"]
            for idx, element in enumerate(elements):
                elem_totals[idx] += stats.get(element, 0)
        per_song_stats.append((song.name, pp, cm, fm, ft, ff, *elem_totals))
    return ("song-aware-stats", *per_song_stats)


def _rank_index(rows: list[Row], best: Row) -> int | None:
    """`best`'s place among its song's rows in the mode it won (an FG win ranks among the rows FG won), by score
    then loadout hash; None when it does not rank there (a base score of 0)."""
    fg = best.fg_won
    ranked = sorted(
        (row for row in rows if (row.fg_score > 0 and row.fg_won if fg else row.score > 0)),
        key=lambda row: (-(row.fg_score if fg else row.score), row.loadout_hash),
    )
    return next((idx for idx, row in enumerate(ranked) if row is best), None)


def _song_win(song_name: str, best: Row, rows: list[Row]) -> dict:
    out = {
        "song_id": song_name,
        "song_name": song_name,
        "mode": "fg" if best.fg_won else "meta",
        "score": best.fg_score if best.fg_won else best.score,
        "base_score": best.score,
        "fg_score": best.fg_score,
        "team_buff": OPTIMIZER_BASELINE_TEAM_BUFF,  # the tier the stored rows were solved at
    }
    if best.loadout_hash:
        out["loadout_hash"] = best.loadout_hash
    rank_index = _rank_index(rows, best)
    if rank_index is not None:
        out["rank_index"] = rank_index
        out["rank"] = rank_index + 1
    return out


@dataclass
class _SetWins:
    """What one gear + mini-effect set won in a category."""

    wins: list[tuple[str, Row]] = field(default_factory=list)  # its winning rows in ranked songs, by song name
    all_rows: list[Row] = field(default_factory=list)  # its winning rows in every song (the gem/score averages)
    variants: Counter = field(default_factory=Counter)  # mini variant groups of the ranked wins
    song_wins: list[dict] = field(default_factory=list)


def _category_wins(
    songs: Sequence[Song],
    rows_by_song: Mapping[str, list[Row]],
    minis_by_name: Mapping[str, Mini],
    gears_by_name: Mapping[str, Gear],
) -> dict[tuple, _SetWins]:
    """Each song's best row (by best score), grouped by its gear set + mini effect signature."""
    songs_by_name = {song.name: song for song in songs}
    elements = relevant_elements(songs)
    signature_songs = tuple(sorted(songs_by_name.values(), key=lambda song: song.name))
    signatures: dict[tuple[str, ...], tuple[Any, ...]] = {}
    sets: dict[tuple, _SetWins] = {}
    for song_name in sorted(songs_by_name):
        rows = rows_by_song.get(song_name)
        if not rows:
            continue
        best = max(rows, key=lambda row: row.best_score)
        groups = normalize_minis_groups_for_display(best.minis)
        rep_names = tuple(sorted(representative_mini_names(groups)))
        if rep_names not in signatures:
            signatures[rep_names] = _mini_set_effect_signature(rep_names, minis_by_name, elements, signature_songs)
        gears = tuple(sort_gears_by_slot(best.gear, gears_by_name))
        won = sets.setdefault((gears, signatures[rep_names]), _SetWins())
        won.all_rows.append(best)
        if songs_by_name[song_name].difficulty != "Easy":
            won.wins.append((song_name, best))
            won.variants[tuple(sorted(tuple(group) for group in groups))] += 1
            won.song_wins.append(_song_win(song_name, best, rows))
    return sets


def _round_mean_gems(gem_sums: dict[str, int], denom: int) -> dict[str, int]:
    """
    Per-kind gem sums as an integer mean allocation that sums to the gem budget.

    A largest-remainder allocation: the vector is as close as possible to the true mean, and the sum is exact (no
    89/91 gem artifacts from independent rounding).
    """
    keys = _GEM_KEYS
    means = {k: gem_sums[k] / denom for k in keys}
    floors = {k: math.floor(means[k]) for k in keys}

    remaining = GEM_BUDGET - sum(floors.values())
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

    # Sums far from the budget (rows without a full gem set) leave a remainder: spread it round-robin.
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


def _ranked_set(rank: int, key: tuple, won: _SetWins) -> RankedSet:
    gears, signature = key
    gem_sums = dict(zip(_GEM_KEYS, map(sum, zip(*(row.gems for row in won.all_rows)))))
    denom = len(won.all_rows)
    most = max(won.variants.values())
    return RankedSet(
        rank=rank,
        loadout_key=hashlib.sha1(
            json.dumps([list(gears), list(signature)], separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        gear=gears,
        mini_groups=min(variant for variant, count in won.variants.items() if count == most),  # ties: the first by name
        peak_in_songs=[song for song, _ in won.wins],
        peak_in_songs_meta=[song for song, row in won.wins if not row.fg_won],
        peak_in_songs_fg=[song for song, row in won.wins if row.fg_won],
        song_wins=won.song_wins,
        wins=len(won.wins),
        avg_score=int(sum(row.best_score for row in won.all_rows) / denom),
        avg_gems=_round_mean_gems(gem_sums, denom) if sum(gem_sums.values()) > 0 else dict.fromkeys(_GEM_KEYS, 0),
    )


def ranked_sets(
    songs: Sequence[Song],
    rows_by_song: Mapping[str, list[Row]],
    minis_by_name: Mapping[str, Mini],
    gears_by_name: Mapping[str, Gear],
) -> list[RankedSet]:
    """
    The gear + mini sets that win this category's songs, most ranked (non-Easy) wins first, with their gems and
    scores averaged over every song they win (Easy included).
    """
    sets = _category_wins(songs, rows_by_song, minis_by_name, gears_by_name)
    ranked = sorted(((key, won) for key, won in sets.items() if won.wins), key=lambda kv: (-len(kv[1].wins), kv[0]))
    return [_ranked_set(rank, key, won) for rank, (key, won) in enumerate(ranked, start=1)]
