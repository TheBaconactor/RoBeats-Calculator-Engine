from __future__ import annotations

from gear_optimizer.data import loadout_equivalence, song_io
from gear_optimizer.helpers import pool_initialization
from gear_optimizer.solver import item_registry
from gear_optimizer.solver import fg_effective_dedup
from gear_optimizer.solver.item_registry import ItemRegistry


SLOTS = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]


def _gear(name: str, slot: str, pp: int) -> dict:
    return {"Name": name, "type": slot, "Perfect Points": pp, "Rush": 1}


def _gear_pool() -> dict[str, list[dict]]:
    return {
        slot: [_gear(f"{slot}-item", slot, index + 1)]
        for index, slot in enumerate(SLOTS)
    }


def test_pruned_gear_pool_cache_invalidates_same_object_content_mutations() -> None:
    pool_initialization._PRUNED_GEAR_POOL_CACHE.clear()
    gears = [_gear("first", "Hat", 1), _gear("second", "Neck", 2)]

    first, _before, _after = pool_initialization._get_pruned_gear_pool(
        gears, SLOTS, "Rush", "Flow"
    )
    gears[0]["Name"] = "renamed"
    gears[0]["Perfect Points"] = 99
    gears[0]["type"] = "Face"
    second, _before, _after = pool_initialization._get_pruned_gear_pool(
        gears, SLOTS, "Rush", "Flow"
    )

    assert first["Hat"][0]["Name"] == "renamed"
    assert second["Hat"] == []
    assert second["Face"][0]["Name"] == "renamed"
    assert second["Face"][0]["Perfect Points"] == 99
    assert any(entry[0] is gears for entry in pool_initialization._PRUNED_GEAR_POOL_CACHE.values())


def test_item_registry_cache_invalidates_same_object_name_stat_and_slot_mutations() -> None:
    item_registry._GEAR_REGISTRY_CACHE.clear()
    gear_pool = _gear_pool()
    minis = [{"Name": f"mini-{index}", "Rush": index + 1} for index in range(3)]

    first = ItemRegistry(gear_pool, minis, SLOTS)
    hat_item = gear_pool["Hat"][0]
    neck_item = gear_pool["Neck"][0]
    hat_item["Name"] = "renamed-hat"
    hat_item["Perfect Points"] = 77
    gear_pool["Hat"][0], gear_pool["Neck"][0] = neck_item, hat_item
    second = ItemRegistry(gear_pool, minis, SLOTS)

    assert (0, "Neck-item") in second.item_to_id
    renamed_id = second.item_to_id[(1, "renamed-hat")]
    assert int(second.to_gpu_arrays()["item_stats"][renamed_id, 0]) == 77
    assert (0, "Hat-item") in first.item_to_id
    assert (1, "renamed-hat") not in first.item_to_id
    assert any(entry[0] is gear_pool for entry in item_registry._GEAR_REGISTRY_CACHE.values())


def test_mini_signature_cache_invalidates_same_object_name_and_stat_mutations() -> None:
    loadout_equivalence._MINI_SIG_TO_NAMES_CACHE.clear()
    minis = {
        "alpha": {"Name": "alpha", "Perfect Points": 1, "Rush": 2},
        "beta": {"Name": "beta", "Perfect Points": 2, "Rush": 2},
    }

    first = loadout_equivalence.minis_signature_to_names_map(minis, "Rush", "Flow", "Rush")
    alpha_sig = loadout_equivalence.effective_mini_signature(minis["alpha"], "Rush", "Flow", "Rush")
    assert first[alpha_sig] == ["alpha"]

    beta = minis.pop("beta")
    beta["Perfect Points"] = 1
    beta["Name"] = "gamma"
    minis["gamma"] = beta
    second = loadout_equivalence.minis_signature_to_names_map(minis, "Rush", "Flow", "Rush")

    assert second[alpha_sig] == ["alpha", "gamma"]
    assert any(entry[0] is minis for entry in loadout_equivalence._MINI_SIG_TO_NAMES_CACHE.values())


def test_config_hash_changes_after_same_object_nested_mutation() -> None:
    cfg = {"Optimizer": {"Mode": "first"}}
    first = song_io._stable_cfg_hash(cfg)

    cfg["Optimizer"]["Mode"] = "second"

    assert song_io._stable_cfg_hash(cfg) != first


def test_effective_table_cache_invalidates_same_registry_content_mutations() -> None:
    fg_effective_dedup._CONTEXT_TABLES_CACHE.clear()
    gear_pool = _gear_pool()
    minis = [
        {"Name": "mini-a", "Perfect Points": 1, "Rush": 2},
        {"Name": "mini-b", "Perfect Points": 2, "Rush": 3},
        {"Name": "mini-c", "Perfect Points": 3, "Rush": 4},
    ]
    registry = ItemRegistry(gear_pool, minis, SLOTS)
    first_gear, first_mini = fg_effective_dedup.effective_tables_for_context(
        registry,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
    )
    hat_id = registry.item_to_id[(0, "Hat-item")]
    neck_id = registry.item_to_id[(1, "Neck-item")]
    mini_a_id = registry.item_to_id[(6, "mini-a")]
    mini_b_id = registry.item_to_id[(6, "mini-b")]
    assert first_gear[hat_id] != first_gear[neck_id]
    assert first_mini[mini_a_id] != first_mini[mini_b_id]

    registry.id_to_item[neck_id]["Name"] = "Hat-item"
    for key, value in registry.id_to_item[mini_a_id].items():
        if key != "Name":
            registry.id_to_item[mini_b_id][key] = value
    second_gear, second_mini = fg_effective_dedup.effective_tables_for_context(
        registry,
        primary_color="Rush",
        secondary_color="Flow",
        selected_color="Rush",
    )

    assert second_gear[hat_id] == second_gear[neck_id]
    assert second_mini[mini_a_id] == second_mini[mini_b_id]
    assert any(entry[0] is registry for entry in fg_effective_dedup._CONTEXT_TABLES_CACHE.values())
