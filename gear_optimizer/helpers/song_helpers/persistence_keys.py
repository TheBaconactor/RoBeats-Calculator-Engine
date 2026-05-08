from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def stable_loadout_key(entry_obj: Mapping[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    gear = tuple(sorted(str(item).strip() for item in (entry_obj.get("gear") or []) if str(item).strip()))
    minis = tuple(sorted(str(item).strip() for item in (entry_obj.get("minis") or []) if str(item).strip()))
    return (gear, minis)
