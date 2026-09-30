from __future__ import annotations

from gear_optimizer.gamedata import Gear, SongMini


def item_name(item) -> str:
    """The name of a loadout item: a Gear or SongMini, a name string, or "" for an empty slot."""
    if isinstance(item, (Gear, SongMini)):
        return item.name
    if isinstance(item, str):
        return item
    if item is None:
        return ""
    raise TypeError(f"expected a Gear, SongMini or item name, got {type(item).__name__}")


def names_list(items) -> list[str]:
    return [item_name(it) for it in (items or [])]
