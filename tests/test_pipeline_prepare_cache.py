from gear_optimizer.pipeline import prepare
from tests.items_support import make_gear, make_song_mini

SLOTS = ("Hat", "Neck", "Face", "Shirt", "Back", "Pants")
MINIS = [make_song_mini(f"Mini {i}", Vibe=20 + i) for i in range(4)]


def _catalog(version: int) -> dict:
    return {f"{slot} {version}": make_gear(f"{slot} {version}", slot, Vibe=10 + version) for slot in SLOTS}


def _registry(version: int):
    return prepare._ga_registry(_catalog(version), MINIS, "Vibe", "Flow")[0]


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
