"""Persistent-identity ``canonical_form`` for reverse score engine v2.

Binding contract: ``CLASS_EQUIVALENCE_RESOLUTION.md`` §1–§2 and
``CANONICAL_FORM_SPEC.md`` (persistent-identities freeze). Two physical
loadouts are the same class member iff their canonical keys are equal.
No fiber type collapses identity by contribution vector.
"""
from __future__ import annotations

from reverse_score_v2.domain import GEAR_SLOTS, Loadout, Tables, compose_stats


def visible_stat_projection(
    loadout: Loadout,
    tables: Tables,
    *,
    song_name: str,
    song_colors: tuple[str, ...],
) -> tuple[int, ...]:
    """7-dim (or 6-dim single-color) visible-stat projection.

    Carries raw ``(c1[, c2])`` — NO ``v = 2*c1+c2`` collapse. The
    projection is a derived quantity for search/scoring, not the
    identity key itself.
    """
    if len(song_colors) == 0 or len(song_colors) > 2:
        raise ValueError(f"song_colors must have length 1 or 2, got {song_colors!r}")
    primary = song_colors[0]
    secondary = song_colors[1] if len(song_colors) == 2 else ""
    stats = compose_stats(
        loadout,
        tables,
        song_name=song_name,
        primary_color=primary,
        secondary_color=secondary,
    )
    if len(song_colors) == 2:
        color_part = (
            int(stats.get(song_colors[0], 0)),
            int(stats.get(song_colors[1], 0)),
        )
    else:
        color_part = (int(stats.get(song_colors[0], 0)),)
    main_part = tuple(
        int(stats.get(k, 0))
        for k in (
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Time",
            "Fever Fill Rate",
        )
    )
    return color_part + main_part


def canonical_form(
    loadout: Loadout,
    tables: Tables,
    *,
    song_name: str,
    song_colors: tuple[str, ...],
) -> tuple:
    """Persistent-identity class key.

    Carries the FULL physical loadout identity. Upgrade placements are
    per-(slot, type) — NOT aggregate counts. Two-color ``v`` collapse is
    NOT applied. Mini identities stay distinct.
    """
    gear_fiber = tuple(loadout.gear.get(slot) for slot in GEAR_SLOTS)

    # Per-(slot, type) placement — sorted for determinism. NOT aggregate.
    upgrade_items: list[tuple[str, int]] = []
    for slot in GEAR_SLOTS:
        for uid in loadout.upgrades.get(slot, ()):
            upgrade_items.append((slot, int(uid)))
    upgrade_fiber = tuple(sorted(upgrade_items))

    mini_fiber = tuple(
        sorted((m.name, m.level, m.rank, m.ascension) for m in loadout.minis)
    )

    gem_fiber = (
        loadout.gems.perfect_points,
        loadout.gems.combo_multiplier,
        loadout.gems.fever_multiplier,
        loadout.gems.fever_time,
        loadout.gems.fever_fill,
        loadout.gems.elemental,
        loadout.gems.selected_element,
    )

    buff_fiber = loadout.team_buff

    projection = visible_stat_projection(
        loadout,
        tables,
        song_name=song_name,
        song_colors=song_colors,
    )

    return (
        gear_fiber,
        upgrade_fiber,
        mini_fiber,
        gem_fiber,
        buff_fiber,
        projection,
    )
