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
            max_baseline_windows=3,
        )
        req = executor._request_q.get(timeout=1.0)
        assert req.request_type == GpuRequestType.SOLVE_FORCE_GREATS_EXACT_DP
        assert req.payload["song_slot"] == 5
        assert req.payload["timing_aware"] is True
        assert req.payload["prune"] is True
        assert req.payload["max_baseline_windows"] == 3
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


def test_fg_coalesce_preserves_pair_work_quantum(monkeypatch):
    executor = _DummyExecutor()
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAYLOADS", "64")
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "64")
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAIRS", "4")
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_WAIT_MS", "100000")
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)

    try:
        p1 = {"ftff_pairs": [(1, 1), (2, 2), (3, 3)]}
        p2 = {"ftff_pairs": [(4, 4), (5, 5), (6, 6)]}
        p3 = {"ftff_pairs": [(7, 7)]}

        job1 = client.submit_fg_solve_with_breakpoints_batch([p1])
        assert executor._request_q.empty()

        job2 = client.submit_fg_solve_with_breakpoints_batch([p2])
        req1 = executor._request_q.get(timeout=1.0)
        assert req1.request_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
        assert req1.payload["payloads"] == [p1]

        job3 = client.submit_fg_solve_with_breakpoints_batch([p3])
        req2 = executor._request_q.get(timeout=1.0)
        assert req2.request_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
        assert req2.payload["payloads"] == [p2, p3]

        executor._response_q.put(GpuResponse(request_id=req1.request_id, success=True, result=["a"]))
        executor._response_q.put(GpuResponse(request_id=req2.request_id, success=True, result=["b", "c"]))

        assert job1.future.result(timeout=1.0) == ["a"]
        assert job2.future.result(timeout=1.0) == ["b"]
        assert job3.future.result(timeout=1.0) == ["c"]
    finally:
        client.close(timeout=0.5)


def test_fg_submit_splits_oversized_payload_list_before_service_coalesce(monkeypatch):
    executor = _DummyExecutor()
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAYLOADS", "64")
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "64")
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAIRS", "4")
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)

    try:
        payloads = [
            {"ftff_pairs": [(1, 1), (2, 2), (3, 3)]},
            {"ftff_pairs": [(4, 4), (5, 5), (6, 6)]},
            {"ftff_pairs": [(7, 7)]},
        ]
        job = client.submit_fg_solve_with_breakpoints_batch(payloads)

        req1 = executor._request_q.get(timeout=1.0)
        req2 = executor._request_q.get(timeout=1.0)
        assert req1.request_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
        assert req2.request_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH
        assert req1.payload["payloads"] == [payloads[0]]
        assert req2.payload["payloads"] == [payloads[1], payloads[2]]

        executor._response_q.put(GpuResponse(request_id=req2.request_id, success=True, result=["b", "c"]))
        executor._response_q.put(GpuResponse(request_id=req1.request_id, success=True, result=["a"]))
        assert job.future.result(timeout=1.0) == ["a", "b", "c"]
    finally:
        client.close(timeout=0.5)
