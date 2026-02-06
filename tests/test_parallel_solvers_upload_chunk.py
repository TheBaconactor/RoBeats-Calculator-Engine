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
