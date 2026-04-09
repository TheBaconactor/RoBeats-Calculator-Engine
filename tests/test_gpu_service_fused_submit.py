import queue

from gear_optimizer.solver.gpu_executor import GpuRequestType, GpuResponse
from gear_optimizer.solver.gpu_service import GpuServiceClient


class _DummyExecutor:
    def __init__(self):
        self.is_running = True
        self._request_q = queue.Queue()
        self._response_q = queue.Queue()

    def register_worker(self):
        return 0, self._request_q, self._response_q

    def unregister_worker(self, _worker_id: int):
        return None


def test_submit_ga_fg_fused_solve_with_breakpoints_routes_new_request_type():
    executor = _DummyExecutor()
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)

    try:
        job = client.submit_ga_fg_fused_solve_with_breakpoints({"n_sections": 7})
        req = executor._request_q.get(timeout=1.0)
        assert req.request_type == GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS
        assert req.payload["n_sections"] == 7

        executor._response_q.put(GpuResponse(request_id=req.request_id, success=True, result={"ok": 1}))
        result = job.future.result(timeout=1.0)
        assert result == {"ok": 1}
    finally:
        client.close(timeout=0.5)


def test_submit_exact_fg_dp_routes_new_request_type():
    executor = _DummyExecutor()
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)

    try:
        job = client.submit_solve_force_greats_exact_dp(
            stats_list=[{"Perfect Points": 1}],
            calc_song={"metadata": {}, "song_data": {}},
            ref_arrays={"dummy": True},
            timing_aware=True,
            prune=True,
            song_slot=5,
        )
        req = executor._request_q.get(timeout=1.0)
        assert req.request_type == GpuRequestType.SOLVE_FORCE_GREATS_EXACT_DP
        assert req.payload["song_slot"] == 5
        assert req.payload["timing_aware"] is True
        assert req.payload["prune"] is True
        assert req.payload["stats_list"] == [{"Perfect Points": 1}]

        executor._response_q.put(GpuResponse(request_id=req.request_id, success=True, result=[{"best_delta": 9}]))
        result = job.future.result(timeout=1.0)
        assert result == [{"best_delta": 9}]
    finally:
        client.close(timeout=0.5)


def test_fg_coalesce_payload_cap_is_clamped_to_executor_limit(monkeypatch):
    executor = _DummyExecutor()
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAYLOADS", "192")
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "16")
    client = GpuServiceClient(executor=executor)
    assert client._fg_coalesce_max_payloads == 16
