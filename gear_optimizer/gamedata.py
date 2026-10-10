"""Game data: gear, minis, the game's stat curves, TeamBuff tiers and Mini Ascension.

Gear and minis are read from Data/Gear (Gears.csv, Minis.csv, generated from the game's exported_game_data.json);
the stat curves are the game's own formulas (GearStats.lua), computed here. All of it is immutable once built.
"""

from __future__ import annotations

import csv
import functools
import json
import math
import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .rules import MAX_STAT

ELEMENTS = ("Chill", "Flow", "Rush", "Beat", "Vibe")
# The five stats that map through one of the game's stat curves (StatCurves).
CURVE_STATS = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time")
# Every stat, in the order evolution.db stores them (details "st").
STATS = (*CURVE_STATS, *ELEMENTS)

Stats = dict[str, int]

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
# Every mini gains 2 Perfect Points per ascension level, whatever the song.
ASCENSION_PERFECT_POINTS = 2 * ASCENSION_LEVEL
# Stored in row details ("Mini Ascension Source Version") when a row's minis were ascended.
MINI_ASCENSION_VERSION = "mini-ascension-v4"
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
class SongMini:
    """A mini as one song sees it: its stats with Mini Ascension applied (see song_minis)."""

    name: str
    stats: Mapping[str, int]
    # The song is one of the mini's Song Targets, so its stats include the elemental bonus.
    targets_song: bool


@dataclass(frozen=True, slots=True, eq=False)
class StatCurves:
    """What each curve stat value 0..MAX_STAT gives in the game (GearStats.lua).

    Perfect Points: a Perfect's base points; Combo Multiplier: the full combo multiplier; Fever Multiplier: the fever
    multiplier; Fever Fill Rate: the fever fill base (a Perfect adds 1 / (hit objects x base) to the fever bar, a
    Great half of that); Fever Time: the base decay rate (fever lasts the song's approximate length x rate seconds).
    f64 holds the game's values; exact scores and fever timing use it (the game computes in float64). f32 holds the
    same values rounded to float32, which is what the GPU search and the frontier cache keys use. combo_ramp[v] holds
    the combo multiplier at combos 1..COMBO_RAMP_NOTES for Combo Multiplier value v; after them a note gets
    f64["Combo Multiplier"].
    """

    f64: Mapping[str, np.ndarray]
    f32: Mapping[str, np.ndarray]
    combo_ramp: np.ndarray

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> StatCurves:
        """Curves from one array per curve stat (MAX_STAT + 1 values each)."""
        f64: dict[str, np.ndarray] = {}
        for stat in CURVE_STATS:
            column = np.array(values[stat], dtype=np.float64).reshape(-1)
            if column.shape != (MAX_STAT + 1,):
                raise ValueError(f"{stat} curve needs {MAX_STAT + 1} values, got {column.shape[0]}")
            f64[stat] = column
        return cls._of(f64, f64["Combo Multiplier"] - 1.0)

    @classmethod
    def _of(cls, f64: dict[str, np.ndarray], combo_gains: np.ndarray) -> StatCurves:
        return cls(
            f64=f64,
            f32={stat: column.astype(np.float32) for stat, column in f64.items()},
            combo_ramp=_combo_ramp(combo_gains),
        )

    def factor(self, stat: str, value: int) -> float:
        return float(self.f64[stat][max(0, min(MAX_STAT, int(value)))])

    def ramp(self, combo_multiplier: int) -> np.ndarray:
        return self.combo_ramp[max(0, min(MAX_STAT, int(combo_multiplier)))]


# The game's stat curve: GearStats.lua stat_eased_curve_extended (with ExtendedGearStatCap160) over BezierDist.lua and
# CurveUtil.lua, in float64 and in the Lua's operation order, so exact scores floor the game's own products.
def _line(x1: float, y1: float, x2: float, y2: float, x: float) -> float:
    slope = (y1 - y2) / (x1 - x2)
    return slope * x + (y1 - slope * x1)


def _bezier(a: float, b: float, c: float, d: float, t: float) -> float:
    return (1 - t) * (1 - t) * (1 - t) * a + 3 * t * (1 - t) * (1 - t) * b + 3 * t * t * (1 - t) * c + t * t * t * d


def _lerp(a: float, b: float, t: float) -> float:
    return (b - a) * t + a


class _Ease:
    """A cubic Bezier from (0, 0) to (1, 1) read at a fraction of its arc length (10 chords, as BezierDist)."""

    def __init__(self, x2: float, y2: float, x3: float, y3: float):
        self.y = (0.0, y2, y3, 1.0)
        self.ts, self.lengths = [0.0], [0.0]
        x, y, t, length = 0.0, 0.0, 0.0, 0.0
        for _ in range(10):
            t = t + 1 / 10
            nx, ny = _bezier(0.0, x2, x3, 1.0, t), _bezier(*self.y, t)
            # SPVector.magnitude: math.sqrt(math.pow(x, 2) + math.pow(y, 2)), each square correctly rounded.
            length = length + math.sqrt((nx - x) * (nx - x) + (ny - y) * (ny - y))
            self.ts.append(t)
            self.lengths.append(length)
            x, y = nx, ny

    def __call__(self, fraction: float) -> float:
        target = min(max(self.lengths[-1] * fraction, 0.0), self.lengths[-1])
        if target == self.lengths[-1]:
            return _bezier(*self.y, 1.0)
        lo, hi = 0, len(self.lengths) - 1
        while hi - lo > 1:
            mid = math.floor(_lerp(lo, hi, 0.5))
            lo, hi = (mid, hi) if self.lengths[mid] < target else (lo, mid)
        t = _lerp(self.ts[lo], self.ts[lo + 1], (target - self.lengths[lo]) / (self.lengths[lo + 1] - self.lengths[lo]))
        return _bezier(*self.y, t)


_EASE_0_40 = _Ease(0.0, 0.4, 0.7, 0.9)
_EASE_40_80 = _Ease(0.2, 0.1, 0.4, 1.0)
_EASE_80_160 = _Ease(0.0, 0.5, 0.6, 1.0)


def _stat_curve(a0: float, a40: float, a80: float, stat: int) -> float:
    """The curve through a0 at stat 0, a40 at 40 and a80 at 80 (it keeps rising to 160), at a stat value 0..MAX_STAT."""
    if stat == 0:
        return a0
    if stat < 40:
        return _lerp(a0, a40, _EASE_0_40(_line(0, 0, 40, 1, stat)))
    if stat <= 80:
        return _lerp(a40, a80, _EASE_40_80(_line(40, 0, 80, 1, stat)))
    return _lerp(a80, a80 + (a80 - a40) * 0.35, _EASE_80_160(_line(80, 0, 160, 1, stat)))


# The combo multiplier ramps to its full value over the first combos through the game's thresholds (get_combo_thresholds
# at Combo Threshold 0; no gear or mini raises it) and gains (get_combo_multiplier: 1 + gain / 4, 1 + gain / 2,
# 1 + gain); get_continuous_combo_multiplier_for_combo reads the line through them.
_COMBO_THRESHOLDS = (25, 50, 100)
COMBO_RAMP_NOTES = _COMBO_THRESHOLDS[-1]


def _combo_ramp(gains: np.ndarray) -> np.ndarray:
    """The combo multiplier at combos 1..COMBO_RAMP_NOTES (columns) per gain (rows), as _line computes it."""
    points = [(0, np.ones_like(gains))] + [(t, 1 + gains * share) for t, share in zip(_COMBO_THRESHOLDS, (0.25, 0.5, 1))]
    combos = np.arange(1, COMBO_RAMP_NOTES + 1, dtype=np.float64)
    ramp = np.empty((gains.shape[0], COMBO_RAMP_NOTES))
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        slope = (y1 - y2) / (x1 - x2)
        ramp[:, x1:x2] = slope[:, None] * combos[x1:x2] + (y1 - slope * x1)[:, None]
    return ramp


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
        targets = json.loads(row[-1]) if row[-1].strip() else []
        if not isinstance(targets, list) or not all(isinstance(song, str) for song in targets):
            raise ValueError(f"{path}: Song Target for {name!r} must be a JSON list of song names")
        # Level-1 values only rank colors for the elemental bonus, which only a targeted song gets.
        # The service's custom minis target no song and leave the level-1 block blank.
        missing_level1 = [color for color in ELEMENTS if stats[color] > 0 and color not in level1_elements]
        if missing_level1 and targets:
            raise ValueError(f"{path}: {name!r} has no level-1 value for {missing_level1}")
        minis[name] = Mini(
            name=name,
            element=row[header.index("Type")].strip(),
            stats=stats,
            level1_elements=level1_elements,
            song_targets=frozenset(song.strip() for song in targets if song.strip()),
        )
    return minis


def _curve(a0: float, a40: float, a80: float) -> np.ndarray:
    return np.array([_stat_curve(a0, a40, a80, value) for value in range(MAX_STAT + 1)])


@functools.cache
def stat_curves() -> StatCurves:
    """The game's curves: GearStats get_perfect_points (floored), get_combo_multiplier, get_powerbar_multiplier,
    get_fever_fill_base and get_base_decay_rate at every stat value 0..MAX_STAT. Callers share it and must not
    mutate it."""
    gains = _curve(1, 1.4, 1.6)
    f64 = {
        "Perfect Points": np.floor(_curve(200, 350, 450)),
        "Combo Multiplier": 1 + gains,
        "Fever Multiplier": _curve(3, 4.75, 5.25),
        "Fever Fill Rate": _curve(0.333, 0.166, 0.1),
        "Fever Time": _curve(0.15, 0.35, 0.4),
    }
    return StatCurves._of(f64, gains)


_FILE_CACHE: dict[tuple[str, Path], tuple[tuple[int, int], object]] = {}
_FILE_CACHE_LOCK = threading.Lock()


def _load_cached(path: Path, read):
    """read(path), cached per file until the file changes (a new Data revision reloads it).

    Callers share the cached value and must not mutate it.
    """
    resolved = Path(path).resolve()
    stat = resolved.stat()
    stamp = (stat.st_mtime_ns, stat.st_size)
    key = (read.__name__, resolved)
    with _FILE_CACHE_LOCK:
        cached = _FILE_CACHE.get(key)
        if cached is not None and cached[0] == stamp:
            return cached[1]
    value = read(resolved)
    with _FILE_CACHE_LOCK:
        _FILE_CACHE[key] = (stamp, value)
    return value


def load_gears(path: Path) -> dict[str, Gear]:
    """Gears.csv by name, in file order."""
    return _load_cached(path, read_gears)


def load_minis(path: Path) -> dict[str, Mini]:
    """Minis.csv by name, in file order."""
    return _load_cached(path, read_minis)


def song_secondary(primary: str, secondary: str | None) -> str:
    """A song's second element, or "" for a one-color song (whose header repeats its primary)."""
    return "" if not secondary or secondary == primary else secondary


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
    secondary = song_secondary(primary, secondary)
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
    stats["Perfect Points"] += ASCENSION_PERFECT_POINTS
    if song_name in mini.song_targets:
        for color, amount in ascension_element_bonus(mini, primary, secondary).items():
            stats[color] += amount
    return stats


def song_minis(minis: Iterable[Mini], song_name: str, primary: str, secondary: str) -> list[SongMini]:
    """Every mini as the song sees it, in the given order."""
    song = song_name.strip()
    if not song:
        raise ValueError("Mini Ascension needs a song name")
    return [
        SongMini(
            name=mini.name,
            stats=ascended_mini_stats(mini, song, primary, secondary),
            targets_song=song in mini.song_targets,
        )
        for mini in minis
    ]
