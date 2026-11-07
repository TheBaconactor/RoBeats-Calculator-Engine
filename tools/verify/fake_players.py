#!/usr/bin/env python3
"""Fake players for the reverse-lookup benchmark: a real set, a pair of hands, and the Play Info their best play leaves.

Sets come from the game's rules (decompile paths, `file:line`): six gear slots, any of them empty; 0 to 15 gems per gear of
any of the 22 kinds, Perfect Time gems among them (EquipmentUpgradesSet1.lua); up to three minis of any rank, level and
ascension (PetUtils.lua:291-306, 433-464, 1221-1239); any TeamBuff on any color (GearStats.lua:628-679). A Top Scores row is a
player's best Score over their plays (ServerPlayerSongStatsDatastoreManager.lua:503-524).

Hands are models, shaped on how people play: timing holds while the chart is within reach and goes past it, errors carry from
note to note, a chord is one movement, mistakes come in bursts, and a row is the best of several attempts. The numbers are mine;
what each press does to a play is the game's, through tools/verify/frame_play.py.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from gear_optimizer.chart import Chart
from gear_optimizer.core.team_buff import team_buff_effect
from gear_optimizer.gamedata import ELEMENTS, Mini, ascension_element_bonus, empty_stats
from gear_optimizer.reverse.lookup import PlayInfo, ReverseSong
from gear_optimizer.score import best_timeline_score, factors
from gear_optimizer.solver.fever_timeline import fixed_timeline_cell
from gear_optimizer.solver.timing_envelope import HELD_TAIL_TYPE, fever_axes
from tools.verify.frame_play import Played, Plan, frame_clock, play, shown_accuracy

_FIVE = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Time", "Fever Fill Rate")
_STAT_GEM_COLORS = dict(zip(_FIVE, ("Chill", "Flow", "Rush", "Beat", "Vibe")))
_LAG_SKIP_MS = 160.0
GEMS_PER_GEAR = 15


def gem_table() -> dict[str, tuple[dict[str, int], int]]:
    """Every live gem: its stat changes and Perfect Time (EquipmentUpgradesSet1.lua, the color branch)."""
    table: dict[str, tuple[dict[str, int], int]] = {}
    for stat, color in _STAT_GEM_COLORS.items():
        gain = 2 if stat in _FIVE[:2] else 3
        table[f"{stat}++"] = ({stat: gain, color: 3}, 0)
        table[f"{stat}+"] = ({stat: 1, color: 1}, 0)
    for color in ELEMENTS:
        table[f"{color}++"] = ({color: 6}, 0)
        table[f"{color}+"] = ({color: 3}, 0)
    table["PerfectTime+"] = ({"Chill": 1, "Perfect Points": -1}, 1)
    table["PerfectTime++"] = ({"Chill": 3, "Combo Multiplier": -2}, 2)
    return table


GEMS = gem_table()


@dataclass(frozen=True, slots=True)
class WornMini:
    name: str
    rank: int
    level: int
    ascension: int


@dataclass(frozen=True, slots=True)
class Hands:
    """How a player plays. sigma: timing noise in ms where the chart is within reach; comfort: the notes per second that are;
    bias: where they aim, past 0 ms since a player tunes to the Perfect window's middle; carry: how much of a note's error
    carries to the next; slip: chance of a mistake per note at twice the comfort, a burst of a few wrong notes;
    fps, jitter: the device; hitches: long frames per minute; attempts: plays behind their best."""

    sigma: float
    comfort: float
    bias: float
    carry: float
    slip: float
    fps: float = 60.0
    jitter: float = 0.0
    hitches: float = 0.0
    attempts: int = 1


# Per skill: sigma, comfort, slip, most attempts. Top Scores rows of an Easy chart run 98.8 to 100.00%.
SKILLS: dict[str, tuple[float, float, float, int]] = {
    "machine": (2.5, 40.0, 0.0, 1),
    "pro": (6.0, 15.0, 0.002, 12),
    "good": (9.0, 10.0, 0.006, 8),
    "average": (13.0, 7.0, 0.015, 5),
    "bad": (19.0, 5.0, 0.03, 3),
    "awful": (28.0, 3.5, 0.06, 2),
}
_FRAME_RATES = (30.0, 60.0, 60.0, 60.0, 120.0, 144.0, 240.0)
# TeamBuff tiers as guilds have them: most players sit in the low tiers or have none.
_TIER_ODDS = (("NONE", 30), ("T51", 25), ("T50", 15), ("T20", 10), ("T10", 8), ("T5", 7), ("T1", 5))


@dataclass(frozen=True, slots=True)
class Player:
    kind: str
    skill: str
    tier: str
    team_color: str
    gear: tuple[str, ...]
    minis: tuple[WornMini, ...]
    gems: dict[str, int]
    stats: dict[str, int]
    perfect_time: int
    hands: Hands
    match_mode: str
    exploit: str = ""


@dataclass(frozen=True, slots=True)
class Row:
    """What the Top Scores menu shows of a player on a song, and what the play was."""

    player: Player
    info: PlayInfo
    played: Played = field(repr=False)


def gear_power(stats: dict[str, int], chart: Chart) -> int:
    """PlayerBlobAvatar.lua:677-710."""
    return 5 * sum(stats[stat] for stat in _FIVE) + 4 * stats[chart.primary] + 2 * stats[chart.secondary]


def play_info(played: Played, power: int, match_mode: str) -> PlayInfo:
    """The Top Scores row and its View popup."""
    return PlayInfo(played.score, shown_accuracy(played.accuracy), played.casual, float(f"{played.score / max(played.casual, 1):.2f}"), power, match_mode)


def worn_mini_stats(mini: Mini, worn: WornMini, song_name: str, primary: str, secondary: str) -> dict[str, int]:
    """A mini at a rank, level and ascension on a song (PetUtils.lua:433-464, 1221-1239; ascension_element_bonus)."""
    stats = empty_stats()
    for stat in _FIVE[1:]:
        stats[stat] = mini.stats[stat] // 4 * worn.rank
    line = 1.0 + (worn.level - 1) * 4.0 / 49.0
    for color, value in mini.level1_elements.items():
        stats[color] = math.floor(value * line)
    stats["Perfect Points"] = 2 * worn.ascension
    if song_name in mini.song_targets:
        for color, amount in ascension_element_bonus(mini, primary, secondary, worn.ascension).items():
            stats[color] += amount
    return stats


def _sum_stats(start: dict[str, int], items: list[dict[str, int]], gems: dict[str, int]) -> tuple[dict[str, int], int]:
    stats = dict(start)
    for item in items:
        for stat, value in item.items():
            stats[stat] += value
    time = 0
    for name, count in gems.items():
        changes, perfect_time = GEMS[name]
        time += perfect_time * count
        for stat, value in changes.items():
            stats[stat] += value * count
    return stats, time


def _chart_time_score(song: ReverseSong, stats: dict[str, int]) -> int:
    chart = song.chart
    durations, thresholds = fever_axes(chart.total_notes, chart.long_notes, chart.last_note_time, song.curves)
    ft, ff = min(max(stats["Fever Time"], 0), 160), min(max(stats["Fever Fill Rate"], 0), 160)
    cache = _CELLS.setdefault(chart.name, {})
    if (ft, ff) not in cache:
        cache[ft, ff] = fixed_timeline_cell(chart.timestamps, fill_notes=math.ceil(thresholds[ff]), fever_duration=float(durations[ft]))
    clamped = {stat: max(value, 0) for stat, value in stats.items()}
    return best_timeline_score(factors(clamped, song.curves, chart.primary, chart.secondary), cache[ft, ff], chart.total_notes)[0]


_CELLS: dict[str, dict] = {}


# Per kind: the share of the song's best-colored items a player owns (of how many per slot), minis likewise, gem slots used,
# the share of strong gems among them, and how many steps they spent improving the set.
_KINDS = {
    "top": (1.0, 6, 1.0, 8, 1.0, 1.0, 600),
    "solid": (0.4, 40, 0.4, 40, 1.0, 1.0, 400),
    "casual": (0.15, 276, 0.2, 92, 0.75, 0.6, 150),
    "any": (1.0, 276, 1.0, 92, 0.5, 0.5, 0),
    "starter": (0.1, 276, 0.1, 92, 0.2, 0.3, 0),
}


def _owned_mini(rng: random.Random, kind: str, name: str) -> WornMini:
    if kind == "top":
        return WornMini(name, 4, 50, 10)
    if kind == "solid":
        return WornMini(name, rng.randint(3, 4), rng.randint(35, 50), rng.randint(0, 10))
    rank = rng.randint(1, 4)
    return WornMini(name, rank, rng.randint(1, 20 + 10 * (rank - 1)), rng.randint(0, 4))


def _inventory(rng: random.Random, song: ReverseSong, kind: str) -> tuple[dict[str, list], dict[str, WornMini]]:
    """What a player owns: per slot its gear, and its minis at their rank, level and ascension."""
    chart = song.chart
    gear_share, gear_pool, mini_share, mini_pool, _, _, _ = _KINDS[kind]

    def color_value(stats) -> int:
        return 2 * stats[chart.primary] + stats[chart.secondary]

    by_slot: dict[str, list] = defaultdict(list)
    for item in song.gears.values():
        by_slot[item.slot].append(item)
    owned = {}
    for slot, items in by_slot.items():
        ranked = sorted(items, key=lambda item: color_value(item.stats), reverse=True)[:gear_pool]
        owned[slot] = [item for item in ranked if rng.random() < gear_share] or ranked[-1:]
    ranked_minis = sorted(song.minis, key=lambda name: color_value(song.minis[name].stats), reverse=True)[:mini_pool]
    minis = {name: _owned_mini(rng, kind, name) for name in ranked_minis if rng.random() < mini_share}
    return owned, minis


def _first_gems(rng: random.Random, chart: Chart, kind: str, slots: int) -> dict[str, int]:
    _, _, _, _, used, strong_share, _ = _KINDS[kind]
    count = rng.randint(int(slots * used * 0.6), int(slots * used)) if used < 1.0 else slots
    strong = [name for name in GEMS if name.endswith("++") and name != "PerfectTime++"]
    weak = [name for name in GEMS if not name.endswith("++") and name != "PerfectTime+"]
    gems: dict[str, int] = defaultdict(int)
    for _ in range(count):
        if strong_share < 1.0 and rng.random() < 0.08:
            gems[rng.choice(("PerfectTime+", "PerfectTime++"))] += 1
        else:
            gems[rng.choice(strong if rng.random() < strong_share else weak)] += 1
    return dict(gems)


def _improved(rng: random.Random, song: ReverseSong, kind: str, start: dict[str, int], held: tuple, owned: tuple) -> tuple[dict, list[WornMini], dict[str, int]]:
    """The set after a player's steps: a swap of gear, a mini or a few gems, kept when the chart-time score does not fall."""
    gear, minis, gems = held
    by_slot, owned_minis = owned
    chart = song.chart

    def score_of(worn, three, allocation) -> int:
        return _chart_time_score(song, _sum_stats(start, _item_stats(song, worn, three), allocation)[0])

    best = score_of(gear, minis, gems)
    kinds = sorted({name for name in GEMS if name.endswith("++") and name != "PerfectTime++"} | set(gems))
    for _ in range(_KINDS[kind][6]):
        worn, three, allocation = dict(gear), list(minis), dict(gems)
        move = rng.random()
        spare = [mini for mini in owned_minis.values() if mini not in three]
        if move < 0.3 and worn:
            slot = rng.choice(tuple(worn))
            worn[slot] = rng.choice(by_slot[slot])
        elif move < 0.5 and three and spare:
            three[rng.randrange(len(three))] = rng.choice(spare)
        elif allocation:
            source = rng.choice([name for name, value in allocation.items() if value] or [None])
            if source is None:
                continue
            moved = min(allocation[source], rng.choice((1, 1, 2, 3, 5)))
            allocation[source] -= moved
            target = rng.choice(kinds)
            allocation[target] = allocation.get(target, 0) + moved
        value = score_of(worn, three, allocation)
        if value >= best:
            best, gear, minis, gems = value, worn, three, allocation
    return gear, minis, {name: count for name, count in gems.items() if count}


def _item_stats(song: ReverseSong, gear: dict, minis: list[WornMini]) -> list[dict[str, int]]:
    chart = song.chart
    return [item.stats for item in gear.values()] + [worn_mini_stats(_CATALOG[mini.name], mini, chart.name, chart.primary, chart.secondary) for mini in minis]


_CATALOG: dict[str, Mini] = {}


def fake_player(rng: random.Random, song: ReverseSong, catalog_minis: dict[str, Mini], kind: str, skill: str, exploit: str = "") -> Player:
    """A player of one kind (see _KINDS): what they own, the set they made of it, and their hands."""
    chart = song.chart
    _CATALOG.update(catalog_minis)
    by_slot, owned_minis = _inventory(rng, song, kind)
    gear = {slot: rng.choice(items) for slot, items in by_slot.items()}
    empty = {"starter": rng.randint(1, 4), "any": rng.choice((0, 0, 0, 1))}.get(kind, 0)
    for slot in rng.sample(sorted(gear), empty):
        del gear[slot]
    worn = 3 if kind in ("top", "solid") else rng.choice((0, 1, 2, 3, 3, 3))
    minis = rng.sample(list(owned_minis.values()), min(worn, len(owned_minis)))
    tier = rng.choices([name for name, _ in _TIER_ODDS], [odds for _, odds in _TIER_ODDS])[0]
    team = rng.choice((chart.primary, chart.primary, chart.secondary, *ELEMENTS))
    start = {**empty_stats(), **team_buff_effect(tier, team)}
    gems = _first_gems(rng, chart, kind, len(gear) * GEMS_PER_GEAR)
    gear, minis, gems = _improved(rng, song, kind, start, (gear, minis, gems), (by_slot, owned_minis))
    stats, gem_time = _sum_stats(start, _item_stats(song, gear, minis), gems)
    perfect_time = sum(item.perfect_time for item in gear.values()) + gem_time
    sigma, comfort, slip, attempts = SKILLS[skill]
    hands = Hands(
        sigma * rng.uniform(0.85, 1.15), comfort * rng.uniform(0.8, 1.2), rng.uniform(2.0, 16.0), rng.uniform(0.3, 0.7), slip,
        rng.choice(_FRAME_RATES), rng.choice((0.0, 0.05, 0.2)), rng.choice((0.0, 0.0, 0.0, 0.2, 1.0)), rng.randint(1, attempts),
    )
    match_mode = "Casual" if rng.random() < 0.1 else "Compete"
    return Player(kind, skill, tier, team, tuple(item.name for item in gear.values()), tuple(minis), gems, stats, perfect_time, hands, match_mode, exploit)


def _density(times: np.ndarray) -> np.ndarray:
    """Notes per second around each note, over a second."""
    return (np.searchsorted(times, times + 0.5) - np.searchsorted(times, times - 0.5)).astype(np.float64)


def _offsets(rng: np.random.Generator, chart: Chart, hands: Hands) -> tuple[np.ndarray, tuple[tuple[float, int], ...]]:
    """Planned presses and stray presses. A hand holds its timing while the chart is within reach and loses it past that;
    an error carries to the next notes, a chord is one movement, a mistake comes in a burst, a hold's tail is let go looser
    than a tap is hit, and a frame's wait is the device's, so a hand aims half a frame ahead."""
    times = np.asarray(chart.timestamps, dtype=np.float64)
    count = chart.total_notes
    strain = np.maximum(_density(times) / hands.comfort - 1.0, 0.0)
    noise = rng.standard_normal(count)
    for k in range(1, count):
        noise[k] = hands.carry * noise[k - 1] + (1.0 - hands.carry * hands.carry) ** 0.5 * noise[k]
    same_time = np.concatenate(([False], np.diff(times) < 0.0015))
    for k in np.flatnonzero(same_time):
        noise[k] = noise[k - 1]
    planned = hands.bias - 500.0 / hands.fps + hands.sigma * (1.0 + 1.5 * strain) * noise + rng.normal(0.0, 1.5, count)
    is_tail = chart.note_types == HELD_TAIL_TYPE
    planned[is_tail] = hands.bias - 500.0 / hands.fps - 12.0 + hands.sigma * 2.0 * (1.0 + strain[is_tail]) * rng.standard_normal(int(is_tail.sum()))
    strays: list[tuple[float, int]] = []
    if hands.slip:
        for at in np.flatnonzero(rng.random(count) < hands.slip * (strain + 0.15)).tolist():
            burst = rng.integers(1, 5)
            planned[at : at + burst] += rng.normal(0.0, 70.0, planned[at : at + burst].shape[0])
            gone = at + rng.integers(0, burst)
            if gone < count and rng.random() < 0.6:
                planned[gone] = np.nan
            if rng.random() < 0.4:
                strays.append((float(times[at]) * 1000.0 + float(rng.normal(30.0, 40.0)), int(rng.integers(1, 5))))
    return np.clip(planned, -300.0, 300.0), tuple(strays)


def _hitches(rng: np.random.Generator, hands: Hands, last_ms: float) -> tuple[tuple[tuple[float, float], ...], tuple[tuple[float, float], ...]]:
    """Long frames: (gaps the clock jumps over, spans the lag sync skips, where a press is lost). Past 2 s a frame over the
    threshold is skipped whole; a shorter one, or one before 2 s, moves the clock (GameLagDelaySync.lua:36-79)."""
    threshold = max(_LAG_SKIP_MS, 10000.0 / hands.fps)
    gaps, lost = [], []
    for at in rng.uniform(0.0, last_ms, rng.poisson(hands.hitches * last_ms / 60000.0)).tolist():
        length = float(rng.lognormal(math.log(120.0), 0.7))
        (lost if length > threshold and at > 2000.0 else gaps).append((at, min(length, 1000.0)))
    return tuple((at, length) for at, length in gaps), tuple((at, at + length) for at, length in lost)


def _one_play(rng: np.random.Generator, chart: Chart, player: Player) -> Played:
    hands = player.hands
    last_ms = float(chart.timestamps[-1]) * 1000.0
    gaps, lost = _hitches(rng, hands, last_ms)
    frames = frame_clock(rng, last_ms, hands.fps, hands.jitter, gaps)
    offsets, strays = _offsets(rng, chart, hands)
    plan = Plan(
        offsets, states_perfect=player.exploit == "accuracy", casual=player.match_mode == "Casual",
        strays=strays, lost=lost, omits_misses=player.exploit == "omitted-misses",
    )
    return play(chart, player.stats, player.perfect_time, plan, frames)


def top_scores_row(rng: np.random.Generator, chart: Chart, player: Player) -> Row:
    """The player's best Score over their attempts, as the menu shows it; a tie keeps the newest."""
    best = _one_play(rng, chart, player)
    for _ in range(player.hands.attempts - 1):
        played = _one_play(rng, chart, player)
        if played.score >= best.score:
            best = played
    return Row(player, play_info(best, gear_power(player.stats, chart), player.match_mode), best)
