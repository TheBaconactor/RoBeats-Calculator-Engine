import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ensure_ftff_combo_tables_order_and_cache(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import initialization as init

    monkeypatch.setattr(init, "ensure_ready", lambda *args, **kwargs: None)

    uploads = {"ft": None, "ff": None, "calls": 0}

    class _Field:
        def __init__(self, key: str):
            self._key = key

        def from_numpy(self, arr):
            uploads["calls"] += 1
            uploads[self._key] = np.asarray(arr, dtype=np.int32).copy()

    monkeypatch.setattr(init.fields, "MAX_TOTAL_BUDGET", 90, raising=False)
    monkeypatch.setattr(init.fields, "MAX_FTFF_COMBOS", (90 + 1) * (90 + 2) // 2, raising=False)
    monkeypatch.setattr(init.fields, "ftff_combo_ft", _Field("ft"), raising=False)
    monkeypatch.setattr(init.fields, "ftff_combo_ff", _Field("ff"), raising=False)

    init._FTFF_COMBO_CACHE = {"budget": None, "n_combos": 0}
    n = init._ensure_ftff_combo_tables(3)
    assert n == 10

    ft = uploads["ft"][:n]
    ff = uploads["ff"][:n]

    expected_ft = np.array([0, 0, 0, 0, 1, 1, 1, 2, 2, 3], dtype=np.int32)
    expected_ff = np.array([0, 1, 2, 3, 0, 1, 2, 0, 1, 0], dtype=np.int32)
    assert np.array_equal(ft, expected_ft)
    assert np.array_equal(ff, expected_ff)

    calls_after_first = int(uploads["calls"])
    n_again = init._ensure_ftff_combo_tables(3)
    assert n_again == 10
    assert int(uploads["calls"]) == calls_after_first
