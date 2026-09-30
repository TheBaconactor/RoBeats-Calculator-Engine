"""Centralized loadout hashing utilities.

All loadout hash computation lives here so callers share one implementation
instead of maintaining duplicate MD5 logic across packages.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, List

from ...gamedata import Gear, Mini, SongMini



def loadout_hash_from_names(gear_names: list[str], mini_names: list[str]) -> str:
    g = sorted([n for n in (gear_names or []) if n])
    m = sorted([n for n in (mini_names or []) if n])
    payload = f"GEAR:{'|'.join(g)}::MINIS:{'|'.join(m)}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def effective_loadout_hash_from_names(
    gear_names: List[str],
    mini_sigs: List[tuple[Any, ...]],
) -> str:
    g = sorted([n for n in (gear_names or []) if n])
    m = sorted("|".join(str(x) for x in sig) for sig in (mini_sigs or []))
    payload = f"GEAR:{'|'.join(g)}::MINIS:{'|'.join(m)}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def resolve_loadout_hash(gear_items, mini_items) -> str:
    """The loadout hash of gear and minis given as items or names (a mini variant group counts as its first name)."""
    return loadout_hash_from_names(compact_gear_names(gear_items), compact_mini_names(mini_items))


def compact_gear_names(gear_items) -> list[str]:
    """Gear given as Gear items or names, as names (empty entries dropped)."""
    out: list[str] = []
    for item in gear_items or []:
        name = item.name if isinstance(item, Gear) else (str(item) if item else "")
        if name:
            out.append(name)
    return out


def compact_mini_names(mini_items) -> list[str]:
    """Minis given as items, names or variant groups (first name of a group), as names; a name written as a
    JSON-ish list string ("['A', 'B']") counts as its first element."""

    def first_name(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (Mini, SongMini)):
            return value.name
        if isinstance(value, (list, tuple)):
            for item in value:
                name = first_name(item)
                if name:
                    return name
            return ""
        if isinstance(value, str):
            text = value.strip()
            if text.startswith("[") and text.endswith("]"):
                match = re.search(r"[\"']([^\"']+)[\"']", text)
                if match:
                    return match.group(1).strip()
            return text
        return str(value).strip()

    return [name for name in (first_name(m) for m in mini_items or []) if name]
