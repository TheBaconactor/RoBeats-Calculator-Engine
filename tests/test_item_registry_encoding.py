from __future__ import annotations

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
