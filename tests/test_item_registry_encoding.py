from __future__ import annotations

from gear_optimizer.solver.item_registry import ItemRegistry
from tests.items_support import make_gear, make_song_mini


def test_new_registry_uses_current_pool_contents_even_when_counts_are_unchanged():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    pool = {slot: [make_gear(f"{slot}_A", slot)] for slot in slots}
    minis = [make_song_mini(f"Mini_{i}") for i in range(3)]
    original = ItemRegistry(pool, minis, slots)
    pool["Hat"] = [make_gear("Hat_B", "Hat", **{"Perfect Points": 23})]
    current = ItemRegistry(pool, minis, slots)
    assert (0, "Hat_B") in current.item_to_id
    assert (0, "Hat_A") not in current.item_to_id
    item_id = current.item_to_id[(0, "Hat_B")]
    assert current.to_gpu_arrays()["item_stats"][item_id, 0] == 23
    assert (0, "Hat_A") in original.item_to_id


def test_registry_ids_follow_name_order_not_pool_order():
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    pool = {slot: [make_gear(f"{slot}_B", slot), make_gear(f"{slot}_A", slot)] for slot in slots}
    minis = [make_song_mini("Mini_C"), make_song_mini("Mini_A"), make_song_mini("Mini_B")]
    registry = ItemRegistry(pool, minis, slots)
    assert registry.item_to_id[(0, "Hat_A")] < registry.item_to_id[(0, "Hat_B")]
    mini_ids = [registry.item_to_id[(6, name)] for name in ("Mini_A", "Mini_B", "Mini_C")]
    assert mini_ids == sorted(mini_ids)
    assert registry.decode_names(mini_ids[:1] * 9) == ["Mini_A"] * 9
