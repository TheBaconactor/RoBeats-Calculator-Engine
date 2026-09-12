from __future__ import annotations

import numpy as np

from gear_optimizer.solver.item_registry import ItemRegistry


def _mk_item(name: str, **stats: int) -> dict:
    out = {"Name": name}
    out.update({k: int(v) for k, v in (stats or {}).items()})
    return out


def test_new_registry_uses_current_pool_contents_even_when_counts_are_unchanged():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    pool = {slot: [_mk_item(f"{slot}_A")] for slot in slots}
    minis = [_mk_item(f"Mini_{i}") for i in range(3)]
    original = ItemRegistry(pool, minis, slots)
    pool["Hat"] = [_mk_item("Hat_B", **{"Perfect Points": 23})]
    current = ItemRegistry(pool, minis, slots)
    assert (0, "Hat_B") in current.item_to_id
    assert (0, "Hat_A") not in current.item_to_id
    item_id = current.item_to_id[(0, "Hat_B")]
    assert current.to_gpu_arrays()["item_stats"][item_id, 0] == 23
    assert (0, "Hat_A") in original.item_to_id

    # A fixed item can also be replaced without changing its name.
    fixed = [_mk_item("Fixed", **{"Perfect Points": 11})]
    ItemRegistry(pool, minis, slots, fixed_gear=fixed)
    fixed[0] = _mk_item("Fixed", **{"Perfect Points": 29})
    current = ItemRegistry(pool, minis, slots, fixed_gear=fixed)
    assert current.to_gpu_arrays()["item_stats"][current.item_to_id[(0, "Fixed")], 0] == 29


def test_encode_population_handles_identity_name_and_string_paths() -> None:
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

    pooled_genome = [
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
    copied_genome = [dict(item) for item in pooled_genome]
    string_genome = [item["Name"] for item in pooled_genome]

    expected = registry.encode_genome(pooled_genome)
    encoded = registry.encode_population([pooled_genome, copied_genome, string_genome])

    assert encoded.shape == (3, 9)
    assert np.array_equal(encoded[0], expected)
    assert np.array_equal(encoded[1], expected)
    assert np.array_equal(encoded[2], expected)


def test_encode_population_unknown_items_fall_back_to_zero_ids() -> None:
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    gear_pool = {slot: [_mk_item(f"{slot}_A")] for slot in slots}
    mini_pool = [_mk_item("Mini_A")]
    registry = ItemRegistry(gear_pool, mini_pool, slots)

    genome = [dict(item) for item in [gear_pool["Hat"][0], gear_pool["Neck"][0], gear_pool["Face"][0], gear_pool["Shirt"][0], gear_pool["Back"][0], gear_pool["Pants"][0], mini_pool[0], mini_pool[0], mini_pool[0]]]
    genome[3]["Name"] = "Unknown_Shirt"
    genome[8] = {"Name": "Unknown_Mini"}

    encoded = registry.encode_population([genome])[0]

    assert int(encoded[3]) == 0
    assert int(encoded[8]) == 0
    assert int(encoded[0]) > 0
    assert int(encoded[6]) > 0
