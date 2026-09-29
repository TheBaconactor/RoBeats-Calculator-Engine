"""CPU-only tests for the GA->FG effective-dedup equivalence tables (Slice 1).

The tables must collapse exactly the loadouts the host folds (same gear name, color-equivalent minis).
No GPU / Taichi.
"""

from __future__ import annotations

import pytest

from gear_optimizer.solver.fg_effective_dedup import (
    MINI_SLOT_INDICES,
    build_gear_name_rank,
    build_mini_sig_id,
)
from gear_optimizer.solver.item_registry import ItemRegistry

# Six gear slot names matching the production 6-gear layout.
SLOTS = ["Arms", "Back", "Body", "Face", "Feet", "Head"]


# ---------------------------------------------------------------------------
# Registry fixtures
# ---------------------------------------------------------------------------


def _gear(name: str, **stats: int) -> dict:
    return {"Name": name, **stats}


def _mini(name: str, **stats: int) -> dict:
    return {"Name": name, **stats}


def _build_registry(
    *,
    gear_pool: dict[str, list[dict]],
    mini_pool: list[dict],
) -> ItemRegistry:
    return ItemRegistry(gear_pool=gear_pool, mini_pool=mini_pool, slots=list(SLOTS))


def _name_to_id(registry: ItemRegistry, slot_idx: int, name: str) -> int:
    return registry.item_to_id[(slot_idx, name)]


# ---------------------------------------------------------------------------
# Table-builder tests
# ---------------------------------------------------------------------------


def test_gear_name_rank_same_name_same_rank() -> None:
    # Two slots carry a gear item with the SAME name -> ids differ, rank equal.
    gear_pool = {
        "Arms": [_gear("DupGear"), _gear("ArmsOnly")],
        "Back": [_gear("DupGear"), _gear("BackOnly")],
        "Body": [_gear("BodyOnly")],
        "Face": [_gear("FaceOnly")],
        "Feet": [_gear("FeetOnly")],
        "Head": [_gear("HeadOnly")],
    }
    registry = _build_registry(gear_pool=gear_pool, mini_pool=[_mini("M")])
    rank = build_gear_name_rank(registry)

    dup_arms = _name_to_id(registry, 0, "DupGear")
    dup_back = _name_to_id(registry, 1, "DupGear")
    arms_only = _name_to_id(registry, 0, "ArmsOnly")

    assert dup_arms != dup_back  # distinct ids
    assert rank[dup_arms] == rank[dup_back]  # same name -> same rank
    assert rank[dup_arms] != rank[arms_only]  # different name -> different rank
    assert rank[0] == 0  # reserved empty id


def test_mini_sig_id_color_equivalent_same_id() -> None:
    # Two minis identical except in an IRRELEVANT element stat fold together;
    # a mini differing in the PRIMARY color stat stays distinct.
    primary, secondary, selected = "Beat", "Vibe", "Beat"
    mini_pool = [
        # Equal core + equal Beat/Vibe; differ only in Rush (irrelevant here).
        _mini("EquivA", **{"Perfect Points": 5, "Beat": 3, "Vibe": 1, "Rush": 7}),
        _mini("EquivB", **{"Perfect Points": 5, "Beat": 3, "Vibe": 1, "Rush": 99}),
        # Differs in the PRIMARY (Beat) stat -> must NOT fold.
        _mini("DiffPrimary", **{"Perfect Points": 5, "Beat": 4, "Vibe": 1, "Rush": 7}),
    ]
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    registry = _build_registry(gear_pool=gear_pool, mini_pool=mini_pool)

    tab = build_mini_sig_id(
        registry, primary_color=primary, secondary_color=secondary, selected_color=selected
    )
    mini_slot = MINI_SLOT_INDICES[0]
    id_a = registry.item_to_id[(mini_slot, "EquivA")]
    id_b = registry.item_to_id[(mini_slot, "EquivB")]
    id_diff = registry.item_to_id[(mini_slot, "DiffPrimary")]

    assert id_a != id_b
    assert tab.sig_id[id_a] == tab.sig_id[id_b]  # color-equivalent -> same sig id
    assert tab.sig_id[id_a] != tab.sig_id[id_diff]  # primary-color diff -> distinct
    assert tab.sig_id[0] == 0


def test_mini_sig_id_is_color_context_dependent() -> None:
    # Under a context where Rush is the SELECTED color, EquivA/EquivB diverge.
    mini_pool = [
        _mini("EquivA", **{"Perfect Points": 5, "Beat": 3, "Rush": 7}),
        _mini("EquivB", **{"Perfect Points": 5, "Beat": 3, "Rush": 99}),
    ]
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    registry = _build_registry(gear_pool=gear_pool, mini_pool=mini_pool)
    mini_slot = MINI_SLOT_INDICES[0]
    id_a = registry.item_to_id[(mini_slot, "EquivA")]
    id_b = registry.item_to_id[(mini_slot, "EquivB")]

    folded = build_mini_sig_id(registry, primary_color="Beat", secondary_color="", selected_color="Beat")
    assert folded.sig_id[id_a] == folded.sig_id[id_b]

    split = build_mini_sig_id(registry, primary_color="Beat", secondary_color="", selected_color="Rush")
    assert split.sig_id[id_a] != split.sig_id[id_b]


def test_table_builders_fail_loudly_on_malformed_entry() -> None:
    gear_pool = {s: [_gear(f"{s}G")] for s in SLOTS}
    registry = _build_registry(gear_pool=gear_pool, mini_pool=[_mini("M")])
    # Corrupt a gear id's item to have an empty name.
    some_gear_id = _name_to_id(registry, 0, "ArmsG")
    registry.id_to_item[some_gear_id] = {"Name": ""}
    with pytest.raises(ValueError):
        build_gear_name_rank(registry)


# ---------------------------------------------------------------------------
# Golden parity tests: reference selected SET == host selected SET
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Canonical tie-break (Slice 1 STEP A decision): canonical-IDs descending.
# This pins the GPU `_better_base` rule (payload.py:429-452) on the reference so
# STEP C can match it bit-for-bit. Exercised only by a constructed base-score tie
# (production base scores are distinct), so it has no real-pool A/B impact.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Randomized fuzz parity
# ---------------------------------------------------------------------------
