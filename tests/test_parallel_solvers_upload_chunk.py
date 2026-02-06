import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_upload_work_items_chunk_uses_prefix_kernel(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import parallel_solvers as ps

    called = {"n": None, "shape": None}

    def _fake_kernel(n_items: int, src):
        called["n"] = int(n_items)
        called["shape"] = tuple(src.shape)

    monkeypatch.setattr(ps.kernels, "copy_work_items_from_ndarray_kernel", _fake_kernel, raising=False)

    fallback_calls = {"n": 0}

    class _Fallback:
        def from_numpy(self, _arr):
            fallback_calls["n"] += 1

    monkeypatch.setattr(ps.fields, "work_items", _Fallback(), raising=False)

    arr = np.zeros((32, 8), dtype=np.int32)
    ps._upload_work_items_chunk(arr, 7)

    assert called["n"] == 7
    assert called["shape"] == (7, 8)
    assert fallback_calls["n"] == 0


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_upload_work_items_chunk_falls_back_to_from_numpy(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import parallel_solvers as ps

    def _bad_kernel(_n_items: int, _src):
        raise RuntimeError("no kernel")

    monkeypatch.setattr(ps.kernels, "copy_work_items_from_ndarray_kernel", _bad_kernel, raising=False)

    observed = {"shape": None}

    class _Fallback:
        def from_numpy(self, arr):
            observed["shape"] = tuple(arr.shape)

    monkeypatch.setattr(ps.fields, "work_items", _Fallback(), raising=False)

    arr = np.zeros((16, 8), dtype=np.int32)
    ps._upload_work_items_chunk(arr, 5)

    assert observed["shape"] == (16, 8)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_get_ftff_host_combo_arrays_expected_order():
    from gear_optimizer.solver.taichi_gem.api import parallel_solvers as ps

    combo_ft, combo_ff, combo_budget_left = ps._get_ftff_host_combo_arrays(3)

    expected_ft = np.array([0, 0, 0, 0, 1, 1, 1, 2, 2, 3], dtype=np.int32)
    expected_ff = np.array([0, 1, 2, 3, 0, 1, 2, 0, 1, 0], dtype=np.int32)
    expected_budget_left = np.array([3, 2, 1, 0, 2, 1, 0, 1, 0, 0], dtype=np.int32)

    assert np.array_equal(combo_ft, expected_ft)
    assert np.array_equal(combo_ff, expected_ff)
    assert np.array_equal(combo_budget_left, expected_budget_left)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_combo_indices_for_limits_uses_cache_and_filters():
    from gear_optimizer.solver.taichi_gem.api import parallel_solvers as ps

    combo_ft, combo_ff, _combo_budget_left = ps._get_ftff_host_combo_arrays(4)
    cache = {}

    idx = ps._combo_indices_for_limits(combo_ft, combo_ff, max_ft=2, max_ff=1, cache=cache)
    idx_cached = ps._combo_indices_for_limits(combo_ft, combo_ff, max_ft=2, max_ff=1, cache=cache)

    assert idx_cached is idx
    assert np.all(combo_ft[idx] <= 2)
    assert np.all(combo_ff[idx] <= 1)
    assert np.all((4 - combo_ft[idx] - combo_ff[idx]) >= 0)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_results_from_stats_returns_tuple_rows():
    from gear_optimizer.solver.taichi_gem.api import parallel_solvers as ps

    arr = np.array(
        [
            [10, 1, 2, 3, 4, 5, 6],
            [20, 7, 8, 9, 10, 11, 12],
            [30, 13, 14, 15, 16, 17, 18],
        ],
        dtype=np.int32,
    )

    out = ps._results_from_stats(arr, 2)

    assert out == [(10, 1, 2, 3, 4, 5, 6), (20, 7, 8, 9, 10, 11, 12)]
