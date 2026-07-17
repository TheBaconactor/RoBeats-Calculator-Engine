"""Loadout domain for the reverse engine: items, upgrades, minis, gems, buffs.

Separated surface: this package composes its own statsdicts from game-law
primitives (``game_model``, ``webport_extract``). It imports from
``gear_optimizer`` only where reuse saves real code:
- gem scale constants (``core.constants``),
- team buff tables (``core.team_buff``),
- mini ascension materialization (``data.mini_ascension``).

Data sources:
- Gear: ``Data/Gear/Gears.csv`` (live gear table; drift-checkable against the
  decompiled Equipment sources).
- Minis: decompiled PetInfo base/color mods (level-1/rank-1 values; verified
  identical to ``Data/Gear/Minis.csv`` rows) scaled by the PetUtils law.
- Mini song targets: ``Data/Gear/Minis.csv`` ``Song Target`` JSON lists.
- Upgrades: decompiled ``EquipmentUpgradesSet1``.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
)
from gear_optimizer.core.team_buff import team_buff_effect
from gear_optimizer.data.mini_ascension import (
    MINI_ASCENSION_BASE_STAT_PREFIX,
    MINI_ASCENSION_MAX_LEVEL,
    materialize_mini_for_song,
)

from .game_model import (
    COLOR_KEYS,
    merge_stats,
    pet_rank_to_max_level,
    pet_stats_delta,
)
from .webport_extract import PetDef, UpgradeDef

GEAR_SLOTS: tuple[str, ...] = ("Hat", "Face", "Neck", "Shirt", "Pants", "Back")
MINI_SLOTS = 3

_GEAR_CSV_COLUMNS: dict[str, str] = {
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
    "PTime": "Perfect Time",
}

# Gem type -> (main stat key, paired color key, per-gem main scale).
GEM_TYPES: tuple[tuple[str, str, str, int], ...] = (
    ("perfect_points", "Perfect Points", "Chill", GEM_SCALE_NORMAL),
    ("combo_multiplier", "Combo Multiplier", "Flow", GEM_SCALE_NORMAL),
    ("fever_multiplier", "Fever Multiplier", "Rush", GEM_SCALE_FEVER),
    ("fever_time", "Fever Time", "Beat", GEM_SCALE_FEVER),
    ("fever_fill", "Fever Fill Rate", "Vibe", GEM_SCALE_FEVER),
)

TEAM_BUFF_TIERS: tuple[str, ...] = ("T1", "T2", "T3", "T4", "T5")


class DomainError(RuntimeError):
    pass


@dataclass(frozen=True)
class GearDef:
    name: str
    slot: str
    stats: dict[str, int]


@dataclass(frozen=True)
class MiniState:
    """One equipped mini: identity + progression state."""

    name: str
    level: int = 1
    rank: int = 1
    ascension: int = 0  # 0 = not ascended; 1..10 per optimizer model

    def validate(self, pets: dict[str, PetDef]) -> None:
        if self.name not in pets:
            raise DomainError(f"unknown mini {self.name!r}")
        if not (1 <= self.rank <= 4):
            raise DomainError(f"mini rank out of range: {self}")
        cap = pet_rank_to_max_level(self.rank)
        if not (1 <= self.level <= cap):
            raise DomainError(f"mini level {self.level} exceeds rank cap {cap}: {self}")
        if not (0 <= self.ascension <= MINI_ASCENSION_MAX_LEVEL):
            raise DomainError(f"mini ascension out of range: {self}")


@dataclass(frozen=True)
class GemAlloc:
    perfect_points: int = 0
    combo_multiplier: int = 0
    fever_multiplier: int = 0
    fever_time: int = 0
    fever_fill: int = 0
    elemental: int = 0          # overflow gems on the selected element
    selected_element: str = ""  # required when elemental > 0

    def counts(self) -> dict[str, int]:
        return {
            "perfect_points": self.perfect_points,
            "combo_multiplier": self.combo_multiplier,
            "fever_multiplier": self.fever_multiplier,
            "fever_time": self.fever_time,
            "fever_fill": self.fever_fill,
        }

    def validate(self) -> None:
        for name, count in self.counts().items():
            if count < 0:
                raise DomainError(f"negative gem count {name}={count}")
        if self.elemental < 0:
            raise DomainError(f"negative elemental gem count {self.elemental}")
        if self.elemental > 0 and self.selected_element not in COLOR_KEYS:
            raise DomainError(
                f"elemental gems require a selected element, got {self.selected_element!r}"
            )


@dataclass(frozen=True)
class Loadout:
    gear: dict[str, str | None]                 # slot -> gear name or None
    upgrades: dict[str, tuple[int, ...]]        # slot -> upgrade ids applied
    minis: tuple[MiniState, ...]
    gems: GemAlloc = field(default_factory=GemAlloc)
    team_buff: tuple[str, str] | None = None    # (tier, color) or None/expired

    def validate(self, tables: "Tables") -> None:
        from .webport_extract import UPGRADES_PER_PIECE_MAX

        for slot in GEAR_SLOTS:
            name = self.gear.get(slot)
            if name is not None and name not in tables.gear_by_slot[slot]:
                raise DomainError(f"unknown gear {name!r} for slot {slot}")
        extra = set(self.gear) - set(GEAR_SLOTS)
        if extra:
            raise DomainError(f"unknown gear slots {sorted(extra)}")
        for slot, ids in self.upgrades.items():
            if slot not in GEAR_SLOTS:
                raise DomainError(f"upgrades on unknown slot {slot!r}")
            if ids and self.gear.get(slot) is None:
                raise DomainError(f"upgrades on empty slot {slot!r}")
            if len(ids) > UPGRADES_PER_PIECE_MAX:
                raise DomainError(
                    f"{len(ids)} upgrades on {slot} exceeds cap {UPGRADES_PER_PIECE_MAX}"
                )
            for uid in ids:
                if uid not in tables.upgrades_by_id:
                    raise DomainError(f"unknown upgrade id {uid}")
        if len(self.minis) > MINI_SLOTS:
            raise DomainError(f"{len(self.minis)} minis exceeds {MINI_SLOTS} slots")
        names = [m.name for m in self.minis]
        if len(set(names)) != len(names):
            raise DomainError(f"duplicate minis equipped: {names}")
        for mini in self.minis:
            mini.validate(tables.pets)
        self.gems.validate()
        if self.team_buff is not None:
            tier, color = self.team_buff
            if tier not in TEAM_BUFF_TIERS:
                raise DomainError(f"unknown team buff tier {tier!r}")
            if color not in COLOR_KEYS:
                raise DomainError(f"unknown team buff color {color!r}")


@dataclass(frozen=True)
class Tables:
    gear_by_slot: dict[str, dict[str, GearDef]]
    pets: dict[str, PetDef]
    pet_song_targets: dict[str, tuple[str, ...]]
    upgrades_by_id: dict[int, UpgradeDef]


def load_gear_table(gears_csv: Path) -> dict[str, dict[str, GearDef]]:
    path = Path(gears_csv)
    if not path.is_file():
        raise DomainError(f"gear table not found: {path}")
    by_slot: dict[str, dict[str, GearDef]] = {slot: {} for slot in GEAR_SLOTS}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            slot = (row.get("Type") or "").strip()
            name = (row.get("Gear Name") or "").strip()
            if slot not in by_slot:
                raise DomainError(f"gear {name!r} has unknown slot {slot!r}")
            stats: dict[str, int] = {}
            for col, key in _GEAR_CSV_COLUMNS.items():
                raw = (row.get(col) or "").strip()
                if raw:
                    stats[key] = int(float(raw))
            if name in by_slot[slot]:
                raise DomainError(f"duplicate gear name {name!r} in slot {slot}")
            by_slot[slot][name] = GearDef(name=name, slot=slot, stats=stats)
    if not any(by_slot.values()):
        raise DomainError(f"no gear rows parsed from {path}")
    return by_slot


def load_pet_song_targets(minis_csv: Path) -> dict[str, tuple[str, ...]]:
    path = Path(minis_csv)
    if not path.is_file():
        raise DomainError(f"minis table not found: {path}")
    targets: dict[str, tuple[str, ...]] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("Mini Name") or "").strip()
            raw = (row.get("Song Target") or "").strip()
            if not name:
                continue
            if raw:
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise DomainError(f"mini {name!r} Song Target is not JSON") from exc
                if not isinstance(parsed, list):
                    raise DomainError(f"mini {name!r} Song Target must be a list")
                targets[name] = tuple(str(s) for s in parsed)
            else:
                targets[name] = ()
    return targets


def build_tables(
    *,
    gears_csv: Path,
    minis_csv: Path,
    pets: dict[str, PetDef],
    upgrades: list[UpgradeDef],
) -> Tables:
    return Tables(
        gear_by_slot=load_gear_table(gears_csv),
        pets=pets,
        pet_song_targets=load_pet_song_targets(minis_csv),
        upgrades_by_id={u.upgrade_id: u for u in upgrades},
    )


def mini_stats_delta(
    mini: MiniState,
    tables: Tables,
    *,
    song_name: str,
    primary_color: str,
    secondary_color: str,
) -> dict[str, int]:
    """Full mini contribution: PetUtils level/rank scaling + ascension.

    Ascension reuses the optimizer's canonical materialization: it expects a
    mini row whose color columns are the base (L1) values -- exactly what the
    PetInfo tables hold.
    """
    pet = tables.pets[mini.name]
    delta = pet_stats_delta(pet.base_mods, pet.color_mods, mini.level, mini.rank)
    if mini.ascension <= 0:
        return delta

    row: dict[str, object] = {
        "Mini Name": mini.name,
        "Song Target": list(tables.pet_song_targets.get(mini.name, ())),
        "Mini Ascension Enabled": True,
        "Mini Ascension Level": int(mini.ascension),
        "Perfect Points": 0,
    }
    for color in COLOR_KEYS:
        base_val = int(pet.color_mods.get(color, 0))
        row[color] = base_val
        row[f"{MINI_ASCENSION_BASE_STAT_PREFIX}{color}"] = base_val
    materialized = materialize_mini_for_song(
        row,
        song_name=song_name,
        primary_color=primary_color,
        secondary_color=secondary_color,
    )
    for key in ("Perfect Points", *COLOR_KEYS):
        gained = int(materialized.get(key, 0)) - int(row.get(key, 0))
        if gained:
            delta[key] = delta.get(key, 0) + gained
    return delta


def gem_stats_delta(gems: GemAlloc) -> dict[str, int]:
    """Optimizer-canonical gem scaling (compute_full_stats semantics)."""
    delta: dict[str, int] = {}
    for attr, main_key, color_key, scale in GEM_TYPES:
        count = int(getattr(gems, attr))
        if count:
            delta[main_key] = delta.get(main_key, 0) + count * scale
            delta[color_key] = (
                delta.get(color_key, 0) + count * GEM_STAT_TO_ELEMENT_SCALE
            )
    if gems.elemental:
        delta[gems.selected_element] = (
            delta.get(gems.selected_element, 0) + gems.elemental * ELEMENTAL_GEM_SCALE
        )
    return delta


def compose_stats(
    loadout: Loadout,
    tables: Tables,
    *,
    song_name: str,
    primary_color: str,
    secondary_color: str = "",
) -> dict[str, int]:
    """Loadout -> total statsdict (mirrors get_playerblob_statsdict order:
    gear + per-piece upgrades, then team buff, then minis; gems last)."""
    loadout.validate(tables)
    stats: dict[str, int] = {}
    for slot in GEAR_SLOTS:
        name = loadout.gear.get(slot)
        if name is None:
            continue
        merge_stats(stats, tables.gear_by_slot[slot][name].stats)
        for uid in loadout.upgrades.get(slot, ()):
            merge_stats(stats, tables.upgrades_by_id[uid].stats)
    if loadout.team_buff is not None:
        tier, color = loadout.team_buff
        merge_stats(stats, {k: int(v) for k, v in team_buff_effect(tier, color).items()})
    for mini in loadout.minis:
        merge_stats(
            stats,
            mini_stats_delta(
                mini,
                tables,
                song_name=song_name,
                primary_color=primary_color,
                secondary_color=secondary_color,
            ),
        )
    merge_stats(stats, gem_stats_delta(loadout.gems))

    # The canonical exact scorer models stats >= 0 (ref tables span 0..160,
    # matching every real loadout). A net-negative visible stat -- possible
    # only by stacking negative-stat upgrades on near-zero gear -- is outside
    # the modeled domain and must fail loudly, not score wrong.
    visible = [primary_color]
    if secondary_color and secondary_color != primary_color:
        visible.append(secondary_color)
    visible.extend(
        (
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Time",
            "Fever Fill Rate",
        )
    )
    negative = {k: stats[k] for k in visible if stats.get(k, 0) < 0}
    if negative:
        raise DomainError(
            f"net-negative visible stats {negative} are outside the exact "
            "scorer's modeled domain (stats >= 0)"
        )
    return stats
