"""Catalog identity invariants shared by request and solver boundaries."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def validate_unique_catalog_names(
    all_gears: Sequence[Mapping[str, Any]],
    all_minis: Sequence[Mapping[str, Any]],
) -> None:
    """Reject name collisions before name-keyed IDs can diverge from row stats."""

    gear_names_by_slot: dict[str, set[str]] = {}
    duplicate_gears: dict[str, set[str]] = {}
    for gear in all_gears:
        name = str((gear or {}).get("Name") or "")
        if not name.strip():
            continue
        slot = str((gear or {}).get("type") or "")
        seen = gear_names_by_slot.setdefault(slot, set())
        if name in seen:
            duplicate_gears.setdefault(slot, set()).add(name)
        seen.add(name)

    mini_names: set[str] = set()
    duplicate_minis: set[str] = set()
    for mini in all_minis:
        name = str((mini or {}).get("Name") or "")
        if not name.strip():
            continue
        if name in mini_names:
            duplicate_minis.add(name)
        mini_names.add(name)

    if not duplicate_gears and not duplicate_minis:
        return

    collisions: list[str] = []
    for slot in sorted(duplicate_gears):
        names = ", ".join(repr(name) for name in sorted(duplicate_gears[slot]))
        collisions.append(f"gear slot {slot!r}: {names}")
    if duplicate_minis:
        names = ", ".join(repr(name) for name in sorted(duplicate_minis))
        collisions.append(f"Minis: {names}")
    raise ValueError(
        "Catalog item names must be unique within each gear slot and across Minis; "
        "duplicate identity would misalign encoded stats and reconstructed item IDs ("
        + "; ".join(collisions)
        + ")"
    )


def build_validated_catalog_name_maps(
    all_gears: Sequence[dict[str, Any]],
    all_minis: Sequence[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build request name maps only after their source catalogs pass identity validation."""

    validate_unique_catalog_names(all_gears, all_minis)
    return (
        {str(gear["Name"]): gear for gear in all_gears},
        {str(mini["Name"]): mini for mini in all_minis},
    )


__all__ = ["build_validated_catalog_name_maps", "validate_unique_catalog_names"]
