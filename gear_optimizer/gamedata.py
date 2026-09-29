"""Game data: gear, minis, the Stats.txt curves, TeamBuff tiers and Mini Ascension.

Everything here is read from Data/Gear (Gears.csv, Minis.csv, Stats.txt, generated from the game's
exported_game_data.json) and is immutable once loaded.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .rules import MAX_STAT

ELEMENTS = ("Chill", "Flow", "Rush", "Beat", "Vibe")
# The five stats with a Stats.txt curve, in the file's column order.
CURVE_STATS = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time")
# Every stat, in the order evolution.db stores them (details "st").
STATS = (*CURVE_STATS, *ELEMENTS)

Stats = dict[str, int]

# Keys of the old item dicts (csv_parser, Mini Ascension) that are metadata, not stats.
SKIP_ITEM_KEYS = frozenset(
    {
        "Name",
        "type",
        "Song Target",
        "Mini Ascension Enabled",
        "Mini Ascension Level",
        "Mini Ascension Source Version",
        "Mini Ascension Song Target Applied",
        "Mini Ascension Elemental Bonus",
        "Mini Ascension Match Qualities",
        "Mini Ascension Materialized",
        "Mini Ascension Materialized Song",
        "Mini Ascension Materialized Primary Color",
        "Mini Ascension Materialized Secondary Color",
        "Mini Ascension Base Chill",
        "Mini Ascension Base Flow",
        "Mini Ascension Base Rush",
        "Mini Ascension Base Beat",
        "Mini Ascension Base Vibe",
    }
)

_GEAR_COLUMNS = {
    "Chill": "Chill",
    "Flow": "Flow",
    "Rush": "Rush",
    "Beat": "Beat",
    "Vibe": "Vibe",
    "PPoint": "Perfect Points",
    "CMult": "Combo Multiplier",
    "FMult": "Fever Multiplier",
    "Time": "Fever Time",
    "Fill": "Fever Fill Rate",
}
# Gears.csv also carries PTime (Perfect Time), a different mechanic that no score reads.
_GEAR_IGNORED_COLUMNS = {"Type", "Gear Name", "PTime"}
_MINI_COLUMNS = {
    "Chill": "Chill",
    "Flow": "Flow",
    "Rush": "Rush",
    "Beat": "Beat",
    "Vibe": "Vibe",
    "CbMlt": "Combo Multiplier",
    "FvMlt": "Fever Multiplier",
    "FvTim": "Fever Time",
    "FvFil": "Fever Fill Rate",
}

# TeamBuff: Perfect Points plus a bonus to the team color (always the song's primary element).
TEAM_BUFFS: dict[str, tuple[int, int]] = {
    "NONE": (0, 0),
    "T1": (25, 35),
    "T5": (25, 30),
    "T10": (20, 25),
    "T20": (15, 20),
    "T50": (10, 15),
    "T51": (5, 10),
}
BASELINE_TEAM_BUFF = "T5"

ASCENSION_LEVEL = 10
_ASCENSION_PP_PER_LEVEL = 2
# Ranking tie-break for a mini's colors (the game's order).
_ASCENSION_COLOR_ORDER = ("Chill", "Vibe", "Beat", "Flow", "Rush")


def empty_stats() -> Stats:
    return dict.fromkeys(STATS, 0)


@dataclass(frozen=True, slots=True)
class Gear:
    name: str
    slot: str
    stats: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class Mini:
    name: str
    element: str
    stats: Mapping[str, int]
    # Level-1 element stats (non-empty cells; required for every element the mini has):
    # Mini Ascension ranks a mini's colors by these.
    level1_elements: Mapping[str, int]
    # Songs whose Mini Ascension elemental bonus this mini receives.
    song_targets: frozenset[str]


@dataclass(frozen=True, slots=True)
class StatCurves:
    """Stats.txt: the multiplier each curve stat value 0..MAX_STAT maps to (float64)."""

    values: Mapping[str, np.ndarray]

    def factor(self, stat: str, value: int) -> float:
        return float(self.values[stat][max(0, min(MAX_STAT, int(value)))])


@dataclass(frozen=True, slots=True)
class GameData:
    gears: Mapping[str, Gear]
    minis: Mapping[str, Mini]
    curves: StatCurves


def _int_cell(value: str, *, column: str, item: str) -> int:
    text = value.strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"{column} for {item!r} must be an integer, got {value!r}") from exc


def _read_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = [row for row in csv.reader(fh) if any(cell.strip() for cell in row)]
    if not rows:
        raise ValueError(f"{path} is empty")
    return [cell.strip() for cell in rows[0]], rows[1:]


def read_gears(path: Path) -> dict[str, Gear]:
    header, rows = _read_rows(path)
    unknown = set(header) - set(_GEAR_COLUMNS) - _GEAR_IGNORED_COLUMNS
    if unknown or "Gear Name" not in header or "Type" not in header:
        raise ValueError(f"{path}: unexpected header {header}")
    gears: dict[str, Gear] = {}
    for row in rows:
        cells = dict(zip(header, row, strict=True))
        name = cells["Gear Name"].strip()
        stats = empty_stats()
        for column, stat in _GEAR_COLUMNS.items():
            stats[stat] = _int_cell(cells[column], column=column, item=name)
        if not name or name in gears:
            raise ValueError(f"{path}: missing or duplicate gear name {name!r}")
        gears[name] = Gear(name=name, slot=cells["Type"].strip(), stats=stats)
    return gears


def read_minis(path: Path) -> dict[str, Mini]:
    """Minis.csv: max-level stats, then an "L1 Stats" block repeating the columns at level 1."""
    header, rows = _read_rows(path)
    split = header.index("L1 Stats")
    main, level1 = header[:split], header[split + 1 :]
    if level1[-1] != "Song Target":
        raise ValueError(f"{path}: expected Song Target as the last column, got {header}")
    minis: dict[str, Mini] = {}
    for row in rows:
        if len(row) != len(header):
            raise ValueError(f"{path}: row has {len(row)} cells, header has {len(header)}: {row[:3]}")
        name = row[header.index("Mini Name")].strip()
        if not name or name in minis:
            raise ValueError(f"{path}: missing or duplicate mini name {name!r}")
        # The blank-headed columns are the Perfect Points slot; minis have none, so they must stay empty.
        for index, column in enumerate(header[:-1]):
            if not column and row[index].strip():
                raise ValueError(f"{path}: {name!r} has a value under a blank header (column {index})")
        stats = empty_stats()
        for index, column in enumerate(main):
            if column in _MINI_COLUMNS:
                stats[_MINI_COLUMNS[column]] = _int_cell(row[index], column=column, item=name)
        level1_elements = {
            column: _int_cell(row[split + 1 + index], column=f"L1 {column}", item=name)
            for index, column in enumerate(level1)
            if column in ELEMENTS and row[split + 1 + index].strip()
        }
        missing_level1 = [color for color in ELEMENTS if stats[color] > 0 and color not in level1_elements]
        if missing_level1:
            raise ValueError(f"{path}: {name!r} has no level-1 value for {missing_level1}")
        targets = json.loads(row[-1]) if row[-1].strip() else []
        if not isinstance(targets, list) or not all(isinstance(song, str) for song in targets):
            raise ValueError(f"{path}: Song Target for {name!r} must be a JSON list of song names")
        minis[name] = Mini(
            name=name,
            element=row[header.index("Type")].strip(),
            stats=stats,
            level1_elements=level1_elements,
            song_targets=frozenset(song.strip() for song in targets if song.strip()),
        )
    return minis


def read_curves(path: Path) -> StatCurves:
    """Stats.txt lists rows from stat value MAX_STAT down to 0 after one header line."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    table = [[float(cell) for cell in line.split()] for line in lines[1:] if line.split()]
    if len(table) != MAX_STAT + 1 or any(len(row) != len(CURVE_STATS) for row in table):
        raise ValueError(f"{path}: expected {MAX_STAT + 1} rows of {len(CURVE_STATS)} values")
    columns = np.asarray(table, dtype=np.float64)[::-1]
    return StatCurves(values={stat: np.ascontiguousarray(columns[:, i]) for i, stat in enumerate(CURVE_STATS)})


def load_game_data(gear_dir: Path) -> GameData:
    return GameData(
        gears=read_gears(gear_dir / "Gears.csv"),
        minis=read_minis(gear_dir / "Minis.csv"),
        curves=read_curves(gear_dir / "Stats.txt"),
    )


def team_buff_stats(tier: str, team_color: str) -> Stats:
    """The fixed stats a TeamBuff tier adds for a team color."""
    perfect_points, element_bonus = TEAM_BUFFS[tier]
    stats = empty_stats()
    stats["Perfect Points"] = perfect_points
    if team_color in ELEMENTS:
        stats[team_color] = element_bonus
    return stats


def _song_secondary(primary: str, secondary: str) -> str:
    """A one-color song repeats its primary as the secondary; treat that as no secondary."""
    return "" if secondary == primary else secondary


def ascension_element_bonus(mini: Mini, primary: str, secondary: str) -> dict[str, int]:
    """Mini Ascension elemental bonus for a mini that targets the song (in-game two-component model).

    For each of the mini's two highest level-1 colors (value v, ascension level A):
      1. a pool gets floor(v * A * 0.5), split 2/3 + 1/3 across a two-color song's primary and
         secondary, or given whole to a one-color song's primary;
      2. a color matching a song element also adds floor(v * A * 0.5) to it when the positions match
         (mini top color = song primary, mini second color = song secondary) and floor(v * A * 0.25)
         when they cross.
    Verified in game: Zara/Canon +62 at A5, +125 at A10; Monstercat own Chill/Flow +131/+68 at A10.
    """
    if primary not in ELEMENTS:
        raise ValueError(f"Mini Ascension needs a song primary element, got {primary!r}")
    secondary = _song_secondary(primary, secondary)
    ranked = sorted(
        ((color, mini.level1_elements.get(color, 0)) for color in _ASCENSION_COLOR_ORDER),
        key=lambda item: -item[1],
    )
    ranked = [(color, value) for color, value in ranked if value > 0][:2]
    pool = 0
    bonus: dict[str, int] = {}
    for position, (color, value) in enumerate(ranked):
        pool += math.floor(value * ASCENSION_LEVEL * 0.5)
        if color == primary:
            extra_share = 0.5 if position == 0 else 0.25
        elif secondary and color == secondary:
            extra_share = 0.25 if position == 0 else 0.5
        else:
            continue
        bonus[color] = bonus.get(color, 0) + math.floor(value * ASCENSION_LEVEL * extra_share)
    if secondary:
        split = {primary: math.floor(pool * 2 / 3), secondary: math.floor(pool / 3)}
    else:
        split = {primary: pool}
    for color, amount in split.items():
        bonus[color] = bonus.get(color, 0) + amount
    return {color: amount for color, amount in bonus.items() if amount}


def ascended_mini_stats(mini: Mini, song_name: str, primary: str, secondary: str) -> Stats:
    """A mini's stats in one song: every mini gains Perfect Points; song targets also gain elements."""
    stats = dict(mini.stats)
    stats["Perfect Points"] += _ASCENSION_PP_PER_LEVEL * ASCENSION_LEVEL
    if song_name in mini.song_targets:
        for color, amount in ascension_element_bonus(mini, primary, secondary).items():
            stats[color] += amount
    return stats


def ascended_minis(minis: Iterable[Mini], song_name: str, primary: str, secondary: str) -> dict[str, Stats]:
    return {mini.name: ascended_mini_stats(mini, song_name, primary, secondary) for mini in minis}
