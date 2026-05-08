"""Centralized loadout hashing utilities.

All loadout hash computation lives here so callers share one implementation
instead of maintaining duplicate MD5 logic across packages.
"""

from __future__ import annotations

import hashlib
from typing import Any, List
import logging



logger = logging.getLogger(__name__)
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
    try:
        from ...data.database import get_loadout_hash

        return str(get_loadout_hash(gear_items, mini_items))
    except Exception as e:
        logger.debug(f"loadout_hashing:resolve_loadout_hash: {e}")
        return str((tuple(gear_items or []), tuple(mini_items or [])))
