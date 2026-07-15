"""Loadout identity is required state: unknown IDs fail loudly."""

from __future__ import annotations

import numpy as np
import pytest


def _registry():
    from gear_optimizer.solver.item_registry import ItemRegistry

    stats = {"Perfect Points": 1}
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [{"Name": f"{slot}0", "Stats": dict(stats)}] for slot in slots}
    mini_pool = [{"Name": f"M{i}", "Stats": dict(stats)} for i in range(3)]
    return ItemRegistry(gear_pool, mini_pool, slots)


def test_decode_names_raises_on_unknown_item_id():
    registry = _registry()
    known = registry.decode_names(np.asarray([0] * 9, dtype=np.int64))
    assert known == ["None"] * 9

    bogus = np.asarray([0, 0, 0, 0, 0, 0, 0, 0, 999_999], dtype=np.int64)
    with pytest.raises(ValueError, match="unknown item id"):
        registry.decode_names(bogus)


def test_decode_loadout_raises_on_unknown_item_id():
    registry = _registry()
    bogus = np.asarray([999_999, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.int64)
    with pytest.raises(ValueError, match="unknown item id"):
        registry.decode_loadout(bogus)
