import sys
import types

import numpy as np

from gear_optimizer.solver.gpu_executor import GpuExecutor
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType, GpuResponse


def _install_fake_registry_api(monkeypatch):
    calls = {"solve": 0}

    fake_api = types.ModuleType("gear_optimizer.solver.taichi_gem.api")

    def _solve_genomes_from_registry(*, population_indices, **_kwargs):
        calls["solve"] += 1
        n = int(np.asarray(population_indices, dtype=np.int32).shape[0])
        return [(int(i), 0, 0, 0, 0, 0, 0) for i in range(n)]

    fake_api.ga_upload_base_fixed_stats = lambda *_args, **_kwargs: None
    fake_api.ga_upload_item_stats = lambda *_args, **_kwargs: None
    fake_api.load_ref_arrays = lambda *_args, **_kwargs: None
    fake_api.solve_genomes_from_registry = _solve_genomes_from_registry

    fake_parent = types.ModuleType("gear_optimizer.solver.taichi_gem")
    fake_parent.__path__ = []
    fake_parent.fields = types.SimpleNamespace(MAX_GENOMES=4096)
    fake_parent.api = fake_api

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem", fake_parent)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api", fake_api)
    return calls


def _make_registry_req(request_id: int, *, timestamps: np.ndarray) -> GpuRequest:
    payload = {
        "population_indices": np.arange(9, dtype=np.int32).reshape(1, 9),
        "timeline_grid": {
            "metadata": {"Song Name": "sig-test"},
            "song_data": {
                "timestamps": timestamps,
                "chart_timestamps": None,
                "note_types": None,
            },
        },
        "ref_arrays": {"Perfect Points": np.arange(8, dtype=np.float64)},
        "item_stats": np.arange(12, dtype=np.int16).reshape(3, 4),
        "slot_start": np.arange(9, dtype=np.int32),
        "slot_count": np.ones(9, dtype=np.int32),
        "base_fixed_stats": np.arange(10, dtype=np.int32),
        "song_slot": 1,
        "total_budget": 90,
        "gem_scale_fever": 3,
        "is_p_ft": 0,
        "is_s_ft": 0,
        "is_p_ff": 0,
        "is_s_ff": 0,
        "is_p_pp": 0,
        "is_s_pp": 0,
        "is_p_cm": 0,
        "is_s_cm": 0,
        "is_p_fm": 0,
        "is_s_fm": 0,
        "is_p_ov": 0,
        "is_s_ov": 0,
    }
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=int(request_id),
        worker_id=1,
        payload=payload,
    )


def test_registry_coalesce_signature_distinguishes_transposed_views(monkeypatch):
    executor = GpuExecutor()
    calls = _install_fake_registry_api(monkeypatch)

    fallback_ids = []

    def _fake_execute_request(req):
        fallback_ids.append(int(req.request_id))
        return GpuResponse(request_id=int(req.request_id), success=True, result=[("fallback", int(req.request_id))])

    monkeypatch.setattr(executor, "_execute_request", _fake_execute_request, raising=False)

    # Same pointer/shape/dtype, different strides and value layout.
    base = np.arange(16, dtype=np.float32).reshape(4, 4)
    req_a = _make_registry_req(1, timestamps=base)
    req_b = _make_registry_req(2, timestamps=base.T)

    responses = executor._coalesce_solve_genomes_from_registry([req_a, req_b])

    assert calls["solve"] == 0
    assert fallback_ids == [1, 2]
    assert [int(r.request_id) for r in responses] == [1, 2]
    assert [r.result[0][0] for r in responses] == ["fallback", "fallback"]
