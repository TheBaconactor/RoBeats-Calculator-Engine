import sys
import types

import numpy as np

from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType, GpuResponse


def _install_fake_ftff_api(monkeypatch):
    calls = {"solve": 0}

    fake_api = types.ModuleType("gear_optimizer.solver.taichi_gem.api")

    def _solve_genomes_with_ftff(*, genome_stats_list, **_kwargs):
        calls["solve"] += 1
        arr = np.asarray(genome_stats_list, dtype=np.int16)
        n = int(arr.shape[0]) if arr.ndim == 2 else 0
        return [(int(i), 0, 0, 0, 0, 0, 0) for i in range(n)]

    fake_api.load_ref_arrays = lambda *_args, **_kwargs: None
    fake_api.solve_genomes_with_ftff = _solve_genomes_with_ftff

    fake_parent = types.ModuleType("gear_optimizer.solver.taichi_gem")
    fake_parent.__path__ = []
    fake_parent.fields = types.SimpleNamespace(MAX_GENOMES=4096)
    fake_parent.api = fake_api

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem", fake_parent)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api", fake_api)
    return calls


def _make_ftff_req(request_id: int, *, genome_stats: np.ndarray, timestamps: np.ndarray) -> GpuRequest:
    payload = {
        "genome_stats_list": genome_stats,
        "timeline_grid": {
            "metadata": {"Song Name": "ftff-coalesce"},
            "song_data": {
                "timestamps": timestamps,
                "chart_timestamps": None,
                "note_types": None,
            },
        },
        "ref_arrays": {"Perfect Points": np.arange(8, dtype=np.float64)},
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
        request_type=GpuRequestType.SOLVE_GENOMES_WITH_FTFF,
        request_id=int(request_id),
        worker_id=1,
        payload=payload,
    )


def test_ftff_coalesce_merges_matching_requests(monkeypatch):
    executor = GpuExecutor()
    calls = _install_fake_ftff_api(monkeypatch)

    timestamps = np.array([0.0, 1.0, 2.0], dtype=np.float32)
    req_a = _make_ftff_req(1, genome_stats=np.arange(7, dtype=np.int16).reshape(1, 7), timestamps=timestamps)
    req_b = _make_ftff_req(2, genome_stats=np.arange(14, dtype=np.int16).reshape(2, 7), timestamps=timestamps)

    responses = executor._coalesce_solve_genomes_with_ftff([req_a, req_b])

    assert calls["solve"] == 1
    assert [int(r.request_id) for r in responses] == [1, 2]
    assert [len(r.result) for r in responses] == [1, 2]
    assert responses[0].result[0][0] == 0
    assert responses[1].result[0][0] == 1


def test_ftff_coalesce_signature_distinguishes_transposed_views(monkeypatch):
    executor = GpuExecutor()
    calls = _install_fake_ftff_api(monkeypatch)

    fallback_ids = []

    def _fake_execute_request(req):
        fallback_ids.append(int(req.request_id))
        return GpuResponse(request_id=int(req.request_id), success=True, result=[("fallback", int(req.request_id))])

    monkeypatch.setattr(executor, "_execute_request", _fake_execute_request, raising=False)

    base = np.arange(16, dtype=np.float32).reshape(4, 4)
    genome_stats = np.zeros((1, 7), dtype=np.int16)
    req_a = _make_ftff_req(1, genome_stats=genome_stats, timestamps=base)
    req_b = _make_ftff_req(2, genome_stats=genome_stats, timestamps=base.T)

    responses = executor._coalesce_solve_genomes_with_ftff([req_a, req_b])

    assert calls["solve"] == 0
    assert fallback_ids == [1, 2]
    assert [int(r.request_id) for r in responses] == [1, 2]
    assert [r.result[0][0] for r in responses] == ["fallback", "fallback"]
