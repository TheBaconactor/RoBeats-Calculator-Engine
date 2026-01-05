from __future__ import annotations


def _item_name(item) -> str:
    if isinstance(item, dict):
        return str(item.get("Name", "") or "")
    return str(item) if item else ""

