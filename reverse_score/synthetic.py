"""Seeded synthetic labeled-data generator over the reverse-engine domain.

Samples loadouts strictly inside a ``DomainSpec`` (the same spec the engine
enumerates -- round-trips are closed by construction), runs them through the
forward oracle, and yields ``(loadout, observables)`` labeled pairs.

This is the "nearly unlimited data" source: partial gear sets, arbitrary
upgrade placements, unmaxed minis (level/rank/ascension), gem spreads, and
team-buff states -- none of which the optimizer's meta-focused output covers.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from typing import Iterator

from .domain import (
    GEAR_SLOTS,
    GemAlloc,
    Loadout,
    MiniState,
    Tables,
)
from .engine import DomainSpec
from .oracle import Observables, SongOracle, forward_many
from .webport_extract import UPGRADES_PER_PIECE_MAX


@dataclass(frozen=True)
class LabeledSample:
    loadout: Loadout
    observables: Observables


def sample_loadout(rng: random.Random, spec: DomainSpec, tables: Tables) -> Loadout:
    """Archetype-weighted sampling: real players are 'light' (few upgrades or
    gems), 'mid', or 'stacked' (heavy concentrated investment) -- not uniform
    draws across every axis, which produce adversarial mid-P monsters no
    human wears. All archetypes stay strictly inside the spec caps, so the
    engine's enumerated domain remains a superset and round-trips stay
    closed."""
    if spec.force_archetype:
        archetype = spec.force_archetype
    else:
        archetype = rng.choices(("light", "mid", "stacked"), weights=(3, 4, 3))[0]

    gear: dict[str, str | None] = {}
    for slot in GEAR_SLOTS:
        names = sorted(tables.gear_by_slot[slot])
        if spec.gear_pool is not None:
            allowed = spec.gear_pool.get(slot)
            if allowed is not None:
                names = [n for n in names if n in allowed]
        pool: list[str | None] = list(names)
        if spec.allow_empty_gear_slots and archetype != "stacked":
            pool.append(None)
        gear[slot] = rng.choice(pool)

    if archetype == "light":
        total_budget = min(4, spec.upgrade_total_max)
        n_types = min(2, len(spec.upgrade_type_ids))
    elif archetype == "mid":
        total_budget = min(12, spec.upgrade_total_max)
        n_types = min(4, len(spec.upgrade_type_ids))
    else:
        # Stacked = a genuinely maxed player: fill the budget across ALL
        # visible types at (or near) the per-type cap. This is the band real
        # top-1 rows occupy (thin P-tail), so the bench must cover it.
        total_budget = spec.upgrade_total_max
        n_types = len(spec.upgrade_type_ids)

    upgrade_counts: dict[int, int] = {}
    budget = total_budget
    type_pool = list(spec.upgrade_type_ids)
    rng.shuffle(type_pool)
    for uid in type_pool[:n_types]:
        if budget <= 0:
            break
        hi = min(spec.upgrade_max_per_type, budget)
        if archetype == "stacked":
            count = hi if rng.random() < 0.7 else rng.randint(hi // 2, hi)
        else:
            count = rng.randint(0, hi)
        if count:
            upgrade_counts[uid] = count
            budget -= count

    occupied = [s for s in GEAR_SLOTS if gear.get(s) is not None]
    upgrades: dict[str, tuple[int, ...]] = {}
    flat: list[int] = []
    for uid, count in sorted(upgrade_counts.items()):
        flat.extend([uid] * count)
    rng.shuffle(flat)
    if flat and not occupied:
        flat = []  # naked gear cannot carry upgrades
    idx = 0
    for slot in occupied:
        if idx >= len(flat):
            break
        take = rng.randint(0, min(UPGRADES_PER_PIECE_MAX, len(flat) - idx))
        if take:
            upgrades[slot] = tuple(flat[idx : idx + take])
            idx += take
    if idx < len(flat) and occupied:
        slot = occupied[-1]
        existing = list(upgrades.get(slot, ()))
        room = UPGRADES_PER_PIECE_MAX - len(existing)
        existing.extend(flat[idx : idx + room])
        if existing:
            upgrades[slot] = tuple(existing)

    distinct_names = len({m.name for m in spec.mini_options})
    if archetype == "light":
        n_minis = rng.randint(0, min(1, spec.mini_max_equipped, distinct_names))
    else:
        n_minis = rng.randint(0, min(spec.mini_max_equipped, distinct_names))
    minis: list[MiniState] = []
    seen: set[str] = set()
    options = list(spec.mini_options)
    rng.shuffle(options)
    if archetype == "stacked":
        # Prefer maxed/ascended states, as real invested players do.
        options.sort(key=lambda m: (m.ascension, m.level, m.rank), reverse=True)
    for mini in options:
        if len(minis) >= n_minis:
            break
        if mini.name in seen:
            continue
        seen.add(mini.name)
        minis.append(mini)

    gcap = spec.gem_max_per_type
    gfloor = spec.gem_min_per_type  # ladder specs pin gems near the cap
    if archetype == "light":
        hi = max(gfloor, gcap // 4)
        gems = GemAlloc(
            perfect_points=rng.randint(gfloor, hi),
            combo_multiplier=rng.randint(gfloor, hi),
            fever_multiplier=rng.randint(gfloor, hi),
            fever_time=rng.randint(gfloor, hi),
            fever_fill=rng.randint(gfloor, hi),
        )
    elif archetype == "mid":
        hi = max(gfloor, gcap // 2)
        gems = GemAlloc(
            perfect_points=rng.randint(gfloor, hi),
            combo_multiplier=rng.randint(gfloor, hi),
            fever_multiplier=rng.randint(gfloor, hi),
            fever_time=rng.randint(gfloor, hi),
            fever_fill=rng.randint(gfloor, hi),
        )
    else:
        # Maxed players sit at or just under the gem caps.
        lo = max(gfloor, gcap - 2)
        gems = GemAlloc(
            perfect_points=rng.randint(lo, gcap),
            combo_multiplier=rng.randint(lo, gcap),
            fever_multiplier=rng.randint(lo, gcap),
            fever_time=rng.randint(lo, gcap),
            fever_fill=rng.randint(lo, gcap),
        )

    loadout = Loadout(
        gear=gear,
        upgrades=upgrades,
        minis=tuple(minis),
        gems=gems,
        team_buff=rng.choice(list(spec.team_buff_options)),
    )
    loadout.validate(tables)
    return loadout


def _sample_composable(
    rng: random.Random, spec: DomainSpec, tables: Tables, oracle: SongOracle
) -> Loadout:
    """Sample a loadout that composes cleanly for this song. Specs that list
    negative-stat upgrade types can draw net-negative visible stats (outside
    the exact scorer's domain); resample a bounded number of times, then
    surface the domain error."""
    from .domain import DomainError

    last_error: DomainError | None = None
    for _ in range(20):
        loadout = sample_loadout(rng, spec, tables)
        try:
            compose_stats_probe(loadout, tables, oracle)
        except DomainError as exc:
            last_error = exc
            continue
        return loadout
    raise DomainError(
        f"could not sample a composable loadout after 20 draws: {last_error}"
    )


def compose_stats_probe(loadout: Loadout, tables: Tables, oracle: SongOracle) -> None:
    from .domain import compose_stats

    compose_stats(
        loadout,
        tables,
        song_name=oracle.song_display,
        primary_color=oracle.primary_color,
        secondary_color=oracle.secondary_color,
    )


def sample_elemental_gems(
    rng: random.Random, spec: DomainSpec, oracle: SongOracle
) -> GemAlloc:
    """Optional elemental-overflow sampling helper (visible elements only)."""
    count = rng.randint(0, spec.elemental_gem_max)
    if count == 0:
        return GemAlloc()
    return GemAlloc(elemental=count, selected_element=rng.choice(oracle.song_colors))


def generate(
    oracle: SongOracle,
    tables: Tables,
    spec: DomainSpec,
    *,
    n: int,
    seed: int,
) -> list[LabeledSample]:
    rng = random.Random(seed)
    loadouts: list[Loadout] = []
    for _ in range(n):
        loadout = _sample_composable(rng, spec, tables, oracle)
        if spec.elemental_gem_max > 0 and rng.random() < 0.5:
            elem = sample_elemental_gems(rng, spec, oracle)
            loadout = Loadout(
                gear=loadout.gear,
                upgrades=loadout.upgrades,
                minis=loadout.minis,
                gems=GemAlloc(
                    perfect_points=loadout.gems.perfect_points,
                    combo_multiplier=loadout.gems.combo_multiplier,
                    fever_multiplier=loadout.gems.fever_multiplier,
                    fever_time=loadout.gems.fever_time,
                    fever_fill=loadout.gems.fever_fill,
                    elemental=elem.elemental,
                    selected_element=elem.selected_element,
                ),
                team_buff=loadout.team_buff,
            )
            loadout.validate(tables)
        loadouts.append(loadout)
    observables = forward_many(oracle, tables, loadouts)
    return [LabeledSample(lo, obs) for lo, obs in zip(loadouts, observables)]


def to_json_rows(samples: list[LabeledSample], song_file: str) -> Iterator[str]:
    for sample in samples:
        row = {
            "song_file": song_file,
            "observables": {
                "score": sample.observables.score,
                "naked_score": sample.observables.naked_score,
                "gear_power": sample.observables.gear_power,
                "accuracy": sample.observables.accuracy,
                "gear_mult": round(sample.observables.gear_mult, 2),
            },
            "loadout": {
                "gear": sample.loadout.gear,
                "upgrades": {k: list(v) for k, v in sample.loadout.upgrades.items()},
                "minis": [asdict(m) for m in sample.loadout.minis],
                "gems": asdict(sample.loadout.gems),
                "team_buff": list(sample.loadout.team_buff)
                if sample.loadout.team_buff
                else None,
            },
        }
        yield json.dumps(row, separators=(",", ":"))
