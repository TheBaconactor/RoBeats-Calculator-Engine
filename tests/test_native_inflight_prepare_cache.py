from collections import OrderedDict

from gear_optimizer.solver.native_inflight_lifecycle import _lru_get, _lru_put


def test_prepare_lru_helpers_refresh_and_evict_oldest_entry():
    cache = OrderedDict()

    _lru_put(cache, ("a",), 1, maxsize=2)
    _lru_put(cache, ("b",), 2, maxsize=2)
    assert _lru_get(cache, ("a",)) == 1

    _lru_put(cache, ("c",), 3, maxsize=2)

    assert list(cache.keys()) == [("a",), ("c",)]
    assert _lru_get(cache, ("b",)) is None
