from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.core.catalog_validation import build_validated_catalog_name_maps, validate_unique_catalog_names
from gear_optimizer.solver.exact_base_domains import encode_pool_stats
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.solver_common import _build_registry_item_id_arrays


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def test_encode_loadouts_handles_identity_name_and_string_paths() -> None:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        "Hat": [_mk_item("Hat_A"), _mk_item("Hat_B")],
        "Neck": [_mk_item("Neck_A"), _mk_item("Neck_B")],
        "Face": [_mk_item("Face_A"), _mk_item("Face_B")],
        "Shirt": [_mk_item("Shirt_A"), _mk_item("Shirt_B")],
        "Back": [_mk_item("Back_A"), _mk_item("Back_B")],
        "Pants": [_mk_item("Pants_A"), _mk_item("Pants_B")],
    }
    mini_pool = [_mk_item("Mini_A"), _mk_item("Mini_B"), _mk_item("Mini_C")]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    pooled_loadout = [
        gear_pool["Hat"][0],
        gear_pool["Neck"][0],
        gear_pool["Face"][0],
        gear_pool["Shirt"][0],
        gear_pool["Back"][0],
        gear_pool["Pants"][0],
        mini_pool[0],
        mini_pool[1],
        mini_pool[2],
    ]
    copied_loadout = [dict(item) for item in pooled_loadout]
    string_loadout = [item["Name"] for item in pooled_loadout]

    expected = registry.encode_loadout(pooled_loadout)
    encoded = registry.encode_loadouts([pooled_loadout, copied_loadout, string_loadout])

    assert encoded.shape == (3, 9)
    assert np.array_equal(encoded[0], expected)
    assert np.array_equal(encoded[1], expected)
    assert np.array_equal(encoded[2], expected)


def test_encode_loadouts_unknown_items_fall_back_to_zero_ids() -> None:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [_mk_item(f"{slot}_A")] for slot in slots}
    mini_pool = [_mk_item("Mini_A")]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    loadout = [dict(item) for item in [gear_pool["Hat"][0], gear_pool["Neck"][0], gear_pool["Face"][0], gear_pool["Shirt"][0], gear_pool["Back"][0], gear_pool["Pants"][0], mini_pool[0], mini_pool[0], mini_pool[0]]]
    loadout[3]["Name"] = "Unknown_Shirt"
    loadout[8] = {"Name": "Unknown_Mini"}

    encoded = registry.encode_loadouts([loadout])[0]

    assert int(encoded[3]) == 0
    assert int(encoded[8]) == 0
    assert int(encoded[0]) > 0
    assert int(encoded[6]) > 0


def test_catalog_rejects_duplicate_identity_before_stats_and_ids_are_built() -> None:
    gears = [
        {"Name": "Duplicate Hat", "type": "Hat", "Perfect Points": 1},
        {"Name": "Duplicate Hat", "type": "Hat", "Perfect Points": 99},
    ]
    minis = [
        {"Name": "Duplicate Mini", "Perfect Points": 2},
        {"Name": "Duplicate Mini", "Perfect Points": 88},
    ]

    with pytest.raises(ValueError, match="misalign encoded stats and reconstructed item IDs") as excinfo:
        build_validated_catalog_name_maps(gears, minis)

    assert "gear slot 'Hat': 'Duplicate Hat'" in str(excinfo.value)
    assert "Minis: 'Duplicate Mini'" in str(excinfo.value)


def test_valid_catalog_rows_encode_and_reconstruct_through_the_same_item_ids() -> None:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {
        slot: [
            {"Name": f"{slot} A", "type": slot, "Perfect Points": index + 1, "Rush": index + 11},
            {"Name": f"{slot} B", "type": slot, "Perfect Points": index + 21, "Rush": index + 31},
        ]
        for index, slot in enumerate(slots)
    }
    mini_pool = [
        {"Name": f"Mini {index}", "Perfect Points": index + 41, "Rush": index + 51}
        for index in range(3)
    ]
    all_gears = [item for slot in slots for item in gear_pool[slot]]
    validate_unique_catalog_names(all_gears, mini_pool)

    registry = ItemRegistry(gear_pool, mini_pool, slots)
    slot_item_ids, mini_item_ids = _build_registry_item_id_arrays(registry, gear_pool, mini_pool)

    for slot_index, slot in enumerate(slots):
        encoded = encode_pool_stats(gear_pool[slot], p_color="Rush", s_color="Flow")
        reconstructed = [registry.id_to_item[int(item_id)] for item_id in slot_item_ids[slot_index]]
        assert np.array_equal(
            encoded,
            encode_pool_stats(reconstructed, p_color="Rush", s_color="Flow"),
        )

    encoded_minis = encode_pool_stats(mini_pool, p_color="Rush", s_color="Flow")
    reconstructed_minis = [registry.id_to_item[int(item_id)] for item_id in mini_item_ids]
    assert np.array_equal(
        encoded_minis,
        encode_pool_stats(reconstructed_minis, p_color="Rush", s_color="Flow"),
    )
