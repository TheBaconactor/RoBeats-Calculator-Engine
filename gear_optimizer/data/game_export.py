"""The game's items, read straight from Data/exported_game_data.json (the export ExportGameData.lua writes).

A gear's export stats are its final ones. A mini's are its level-1 stats: at max level its colors are x5 and its fever
stats x4. Song targets (Mini Ascension) name songs by the game's `title by artist`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gear_optimizer.gamedata import ELEMENTS, Gear, Mini, empty_stats, load_cached

_GEAR_SLOTS = {"1": "Shirt", "2": "Pants", "3": "Hat", "4": "Face", "5": "Neck", "6": "Back"}
_COLOR_STATS = {"Chill": "ColorBlue", "Flow": "ColorPurple", "Rush": "ColorRed", "Beat": "ColorOrange", "Vibe": "ColorGreen"}
_FEVER_STATS = {
    "Combo Multiplier": "ComboMultiplier",
    "Fever Multiplier": "FeverMultiplier",
    "Fever Time": "FeverTime",
    "Fever Fill Rate": "FeverFillRate",
}
_GEAR_STATS = {**_COLOR_STATS, "Perfect Points": "PerfectPoints", **_FEVER_STATS}
_MINI_MAX_LEVEL_COLOR, _MINI_MAX_LEVEL_FEVER = 5, 4
# A service request's custom item keys.
_CUSTOM_COLORS = {color.lower(): color for color in ELEMENTS}
CUSTOM_GEAR_STATS = {
    **_CUSTOM_COLORS, "ppoint": "Perfect Points", "cmult": "Combo Multiplier", "fmult": "Fever Multiplier",
    "time": "Fever Time", "fill": "Fever Fill Rate",
}
CUSTOM_MINI_STATS = {
    **_CUSTOM_COLORS, "cbmlt": "Combo Multiplier", "fvmlt": "Fever Multiplier", "fvtim": "Fever Time",
    "fvfil": "Fever Fill Rate",
}


@dataclass(frozen=True, slots=True)
class Catalog:
    """The items a solve picks from, by name, in export order."""

    gears: Mapping[str, Gear]
    minis: Mapping[str, Mini]


def _items(section: Mapping[str, Any], key: str) -> Iterator[dict[str, Any]]:
    """The items of one export section ({source id: {key: [item, ...]}})."""
    for entry in section.values():
        yield from entry[key]


def _unique(names: Iterable[str], kind: str) -> None:
    seen: set[str] = set()
    for name in names:
        if not name.strip():
            raise ValueError(f"game export: a {kind} has no name")
        if name in seen:
            raise ValueError(f"game export: duplicate {kind} {name!r}")
        seen.add(name)


def _song_names(payload: Mapping[str, Any]) -> dict[int, str]:
    """Song id -> the game's Song Name, which charts carry in their header."""
    names: dict[int, str] = {}
    for song in _items(payload["songs"], "songs"):
        song_id, name = song["songid"], f"{song['displayname']} by {song['artist']}".strip()
        if song_id in names:
            raise ValueError(f"game export: duplicate song id {song_id}")
        names[song_id] = name
    _unique(names.values(), "song")
    return names


def _gear(raw: Mapping[str, Any]) -> Gear:
    stats = empty_stats() | {stat: raw["stats"][key] for stat, key in _GEAR_STATS.items()}
    return Gear(raw["name"].strip(), _GEAR_SLOTS[str(raw["slot"])], stats, raw["stats"]["PerfectTime"])


def _mini(raw: Mapping[str, Any], song_names: Mapping[int, str]) -> Mini:
    name, level1 = raw["name"].strip(), raw["stats"]
    colors = {color: level1[key] for color, key in _COLOR_STATS.items()}
    stats = empty_stats()
    for color, value in colors.items():
        stats[color] = value * _MINI_MAX_LEVEL_COLOR
    for stat, key in _FEVER_STATS.items():
        stats[stat] = level1[key] * _MINI_MAX_LEVEL_FEVER
    target_ids = [target.get("song_id", target.get("songid")) for target in raw.get("ascension_songs") or ()]
    if len(set(target_ids)) != len(target_ids):
        raise ValueError(f"game export: mini {name!r} targets a song twice")
    for song_id in target_ids:
        if song_id not in song_names:
            raise ValueError(f"game export: mini {name!r} references unknown song_id {song_id}")
    return Mini(
        name=name,
        element=max(ELEMENTS, key=colors.__getitem__),
        stats=stats,
        level1_elements={color: value for color, value in colors.items() if value},
        song_targets=frozenset(song_names[song_id] for song_id in target_ids),
    )


def read_catalog(path: Path) -> Catalog:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    song_names = _song_names(payload)
    gears = [_gear(raw) for raw in _items(payload["gears"], "gears")]
    minis = [_mini(raw, song_names) for raw in _items(payload["minis"], "minis")]
    _unique((gear.name for gear in gears), "gear")
    _unique((mini.name for mini in minis), "mini")
    return Catalog({gear.name: gear for gear in gears}, {mini.name: mini for mini in minis})


def load_catalog(path: Path) -> Catalog:
    """The export's catalog, cached until the file changes. Callers share it and must not mutate it."""
    return load_cached(path, read_catalog)


def game_song_names(path: Path) -> set[str]:
    """Every Song Name the export describes."""
    return set(_song_names(json.loads(Path(path).read_text(encoding="utf-8"))).values())


def _custom_stats(item: Mapping[str, Any], keys: Mapping[str, str]) -> dict[str, int]:
    return empty_stats() | {stat: item[key] for key, stat in keys.items()}


def custom_catalog(catalog: Catalog, pool: Mapping[str, list]) -> Catalog:
    """The catalog of one solve: without the items a validated pool excludes (case-insensitive; a name the catalog no
    longer has is ignored), with its custom items. A custom mini targets no song."""
    excluded_gear = {name.casefold() for name in pool["excludeGear"]}
    excluded_minis = {name.casefold() for name in pool["excludeMinis"]}
    gears = {name: gear for name, gear in catalog.gears.items() if name.casefold() not in excluded_gear}
    minis = {name: mini for name, mini in catalog.minis.items() if name.casefold() not in excluded_minis}
    for item in pool["customGear"]:
        gears[item["name"]] = Gear(item["name"], item["type"], _custom_stats(item, CUSTOM_GEAR_STATS))
    for item in pool["customMinis"]:
        minis[item["name"]] = Mini(item["name"], item["type"], _custom_stats(item, CUSTOM_MINI_STATS), {}, frozenset())
    return Catalog(gears, minis)
