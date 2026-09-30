"""Typed gear and minis for tests: pass stats by their full names, e.g. make_gear("G", **{"Perfect Points": 3})."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from gear_optimizer.gamedata import Gear, Mini, SongMini, empty_stats


def stat_row(stats: Mapping[str, int]) -> dict[str, int]:
    row = empty_stats()
    for stat, value in stats.items():
        if stat not in row:
            raise KeyError(f"unknown stat {stat!r}")
        row[stat] = int(value)
    return row


def make_gear(name: str, slot: str = "Hat", **stats: int) -> Gear:
    return Gear(name=name, slot=slot, stats=stat_row(stats))


def make_song_mini(name: str, *, targets_song: bool = False, **stats: int) -> SongMini:
    return SongMini(name=name, stats=stat_row(stats), targets_song=targets_song)


def make_mini(
    name: str,
    element: str = "Chill",
    *,
    level1: Mapping[str, int] | None = None,
    song_targets: Iterable[str] = (),
    **stats: int,
) -> Mini:
    return Mini(
        name=name,
        element=element,
        stats=stat_row(stats),
        level1_elements=dict(level1 or {}),
        song_targets=frozenset(song_targets),
    )


def minis_from_dicts(rows: Mapping[str, Mapping]) -> dict[str, Mini]:
    """Minis from test tables written as {"Name": ..., "type": ..., <stat>: value, "Song Target": [...],
    "Mini Ascension Base <Color>": level-1 value}; missing stats are 0."""
    stat_names = set(empty_stats())
    prefix = "Mini Ascension Base "
    return {
        name: make_mini(
            name,
            str(row.get("type") or "Chill"),
            level1={k[len(prefix):]: v for k, v in row.items() if k.startswith(prefix)},
            song_targets=row.get("Song Target") or (),
            **{k: v for k, v in row.items() if k in stat_names},
        )
        for name, row in rows.items()
    }
