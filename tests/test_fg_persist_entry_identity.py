"""Loadout identity is required state: decode and persistence fail loudly.

A persisted loadout cannot be wrong — unknown item ids must not decode to
placeholder names, and an FG winner with no resolvable gear/mini identity
must not be persisted.
"""

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


def test_decode_genome_raises_on_unknown_item_id():
    registry = _registry()
    bogus = np.asarray([999_999, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.int64)
    with pytest.raises(ValueError, match="unknown item id"):
        registry.decode_genome(bogus)


def test_build_fg_persist_entries_refuses_identityless_winner(monkeypatch):
    from gear_optimizer.solver import native_inflight_fg_payload as payload_mod
    from gear_optimizer.solver.native_inflight_config import make_native_song

    monkeypatch.setattr(
        payload_mod,
        "materialize_entry_names",
        lambda _entry, *, mutate=True: ([], []),
    )
    monkeypatch.setattr(payload_mod, "has_valid_fg_config", lambda data: isinstance(data, dict))
    monkeypatch.setattr(payload_mod, "read_visible_stats", lambda obj, *, mutate_payload=True: obj)

    song = make_native_song(
        song_name="Identityless (Hard) by pytest",
        db_key="identityless-hard",
        fg_variants=[
            {
                "base_score": 100,
                "fg_score": 130,
                "gear": [],
                "minis": [],
                "data": {"ForceGreats": {"config": {"NonFever1": 1}}},
                "_entry_ref": {},
            }
        ],
    )

    with pytest.raises(RuntimeError, match="no resolvable gear/mini names"):
        payload_mod.build_fg_persist_entries(song)
