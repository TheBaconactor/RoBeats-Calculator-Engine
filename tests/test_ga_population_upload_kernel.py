import numpy as np
import pytest


def _has_taichi() -> bool:
    try:
        import taichi  # noqa: F401

        return True
    except Exception:
        return False


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_upload_population_indices_uses_ndarray_kernel(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations as ga

    monkeypatch.setattr(ga, "ensure_ready", lambda *args, **kwargs: None)
    monkeypatch.setattr(ga.fields, "MAX_GENOMES", 64, raising=False)
    monkeypatch.setattr(ga.fields, "MAX_SLOTS", 9, raising=False)

    called = {"n_genomes": None, "n_slots": None, "shape": None}

    def _fake_kernel(n_genomes: int, n_slots: int, src):
        called["n_genomes"] = int(n_genomes)
        called["n_slots"] = int(n_slots)
        called["shape"] = tuple(src.shape)

    monkeypatch.setattr(ga.kernels, "ga_copy_population_indices_from_ndarray_kernel", _fake_kernel, raising=False)

    fallback_calls = {"n": 0}

    class _Field:
        def from_numpy(self, _arr):
            fallback_calls["n"] += 1

    monkeypatch.setattr(ga.fields, "population_indices", _Field(), raising=False)

    pop = np.arange(27, dtype=np.int32).reshape(3, 9)
    n = ga.ga_upload_population_indices(pop, n_slots=9)

    assert n == 3
    assert called["n_genomes"] == 3
    assert called["n_slots"] == 9
    assert called["shape"] == (3, 9)
    assert fallback_calls["n"] == 0


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_upload_population_indices_falls_back_on_kernel_error(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations as ga

    monkeypatch.setattr(ga, "ensure_ready", lambda *args, **kwargs: None)
    monkeypatch.setattr(ga.fields, "MAX_GENOMES", 16, raising=False)
    monkeypatch.setattr(ga.fields, "MAX_SLOTS", 9, raising=False)

    def _bad_kernel(_n_genomes: int, _n_slots: int, _src):
        raise RuntimeError("kernel unavailable")

    monkeypatch.setattr(ga.kernels, "ga_copy_population_indices_from_ndarray_kernel", _bad_kernel, raising=False)

    observed = {"shape": None}

    class _Field:
        def from_numpy(self, arr):
            observed["shape"] = tuple(arr.shape)

    monkeypatch.setattr(ga.fields, "population_indices", _Field(), raising=False)

    pop = np.arange(18, dtype=np.int32).reshape(2, 9)
    n = ga.ga_upload_population_indices(pop, n_slots=9)

    assert n == 2
    assert observed["shape"] == (16, 9)
