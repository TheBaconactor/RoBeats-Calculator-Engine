import numpy as np

from gear_optimizer.pipeline import prepare
from tests.items_support import make_gear, make_song_mini

SLOTS = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")
MINIS = [make_song_mini(f"Mini {i}", Vibe=20 + i) for i in range(4)]


def _catalog(version: int) -> dict:
    return {f"{slot} {version}": make_gear(f"{slot} {version}", slot, Vibe=10 + version) for slot in SLOTS}


def _registry(version: int):
    return prepare._ga_registry(_catalog(version), MINIS, "Vibe", "Flow", np.zeros(10, dtype=np.int32))[0]


def test_ga_registry_reuses_a_pool_key_and_evicts_the_least_recently_used():
    prepare._PREP_CACHE.clear()
    first = _registry(0)
    assert _registry(0) is first
    for version in range(1, prepare._PREP_CACHE_MAX):
        _registry(version)
    assert _registry(0) is first  # reused, and now the most recently used
    second = _registry(1)
    _registry(prepare._PREP_CACHE_MAX)  # one key past the bound: the least recently used (2) goes
    assert len(prepare._PREP_CACHE) == prepare._PREP_CACHE_MAX
    assert _registry(0) is first and _registry(1) is second
    prepare._PREP_CACHE.clear()


def test_in_place_gear_catalog_mutations_invalidate_digest_and_pruned_pools():
    from dataclasses import replace
    from gear_optimizer.pipeline import pools

    prepare._PREP_CACHE.clear()
    pools._PRUNED_GEAR_POOL_CACHE.clear()
    fixed = np.zeros(10, dtype=np.int32)
    gears = _catalog(0)

    reg0, gpu0, *_rest, key0 = prepare._ga_registry(gears, MINIS, "Vibe", "Flow", fixed)
    # Replacing an item in place on the same dict object must not hit stale digest or pruned pool caches.
    gears["Hat 0"] = make_gear("Hat 0", "Hat", Vibe=95)
    reg1, gpu1, *_rest, key1 = prepare._ga_registry(gears, MINIS, "Vibe", "Flow", fixed)
    assert key1 != key0 and reg1 is not reg0
    assert not np.array_equal(gpu0["item_stats"], gpu1["item_stats"])

    # Mutating a Gear's stats mapping in place must also invalidate both caches.
    gears["Hat 0"].stats["Vibe"] = 120
    reg2, gpu2, *_rest, key2 = prepare._ga_registry(gears, MINIS, "Vibe", "Flow", fixed)
    assert key2 != key1 and reg2 is not reg1
    assert not np.array_equal(gpu1["item_stats"], gpu2["item_stats"])

    # Changing Perfect Time in place must produce a distinct registry holding the updated Perfect Time.
    gears["Hat 0"] = replace(gears["Hat 0"], perfect_time=12)
    reg3, *_rest, key3 = prepare._ga_registry(gears, MINIS, "Vibe", "Flow", fixed)
    assert key3 != key2 and reg3 is not reg2
    assert reg3.id_to_item[reg3.slot_start[0]].perfect_time == 12

    prepare._PREP_CACHE.clear()
    pools._PRUNED_GEAR_POOL_CACHE.clear()
