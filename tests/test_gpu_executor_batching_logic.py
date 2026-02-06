import types
import sys

from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType, GpuResponse


def _make_req(request_id: int, *, song_slot: int) -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_PARALLEL,
        request_id=int(request_id),
        worker_id=1,
        payload={
            "genome_stats_list": [{"base_pp": 1}],
            "timeline_grid": {"metadata": {}, "song_data": {}},
            "total_budget": 90,
            "gem_scale_fever": 3,
            "song_slot": int(song_slot),
        },
    )


def _install_fake_taichi_api(monkeypatch):
    calls = []

    fake_api = types.ModuleType("gear_optimizer.solver.taichi_gem.api")

    def _fake_merged(payloads, *, total_budget: int, gem_scale_fever: int):
        calls.append(
            {
                "payloads": [dict(p) for p in payloads],
                "total_budget": int(total_budget),
                "gem_scale_fever": int(gem_scale_fever),
            }
        )
        return [[f"merged-{idx}"] for idx in range(len(payloads))]

    fake_api.solve_genomes_parallel_merged = _fake_merged

    fake_parent = types.ModuleType("gear_optimizer.solver.taichi_gem")
    fake_parent.__path__ = []
    fake_parent.fields = types.SimpleNamespace(MAX_SONG_SLOTS=8)
    fake_parent.api = fake_api

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem", fake_parent)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api", fake_api)
    return calls


def test_execute_solve_batch_treats_slot_zero_as_unspecified(monkeypatch):
    executor = GpuExecutor()
    calls = _install_fake_taichi_api(monkeypatch)
    fallback_calls = []

    def _fake_single(req, song_slot: int = 0):
        fallback_calls.append((int(req.request_id), int(song_slot)))
        return GpuResponse(request_id=int(req.request_id), success=True, result=["single"])

    monkeypatch.setattr(executor, "_execute_solve_genomes", _fake_single)

    reqs = [_make_req(1, song_slot=0), _make_req(2, song_slot=0)]
    responses = executor._execute_solve_batch(reqs)

    assert not fallback_calls
    assert len(calls) == 1
    assert all("song_slot" not in p for p in calls[0]["payloads"])
    assert [r.request_id for r in responses] == [1, 2]
    assert all(r.success for r in responses)


def test_execute_solve_batch_merges_nonzero_song_slots(monkeypatch):
    executor = GpuExecutor()
    calls = _install_fake_taichi_api(monkeypatch)
    fallback_calls = []

    def _fake_single(req, song_slot: int = 0):
        fallback_calls.append((int(req.request_id), int(song_slot)))
        return GpuResponse(request_id=int(req.request_id), success=True, result=["single"])

    monkeypatch.setattr(executor, "_execute_solve_genomes", _fake_single)

    reqs = [_make_req(10, song_slot=1), _make_req(11, song_slot=1), _make_req(12, song_slot=2)]
    responses = executor._execute_solve_batch(reqs)

    # Duplicate explicit slots are split into separate merged calls.
    assert len(calls) == 2
    for call in calls:
        slots = [int(p["song_slot"]) for p in call["payloads"] if "song_slot" in p]
        assert len(slots) == len(set(slots))

    assert not fallback_calls
    assert [r.request_id for r in responses] == [10, 11, 12]
    assert all(r.success for r in responses)
