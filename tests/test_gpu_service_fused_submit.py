import queue

import numpy as np

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


def test_fg_submit_splits_single_oversized_payload_and_merges_full_results(monkeypatch):
    executor = _DummyExecutor()
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAIRS", "2")
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAYLOADS", "64")
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "64")
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)

    try:
        payload = {"ftff_pairs": [(i, i) for i in range(5)]}
        job = client.submit_fg_solve_with_breakpoints_batch([payload])

        reqs = [executor._request_q.get(timeout=1.0) for _ in range(3)]
        assert [len(req.payload["payloads"][0]["ftff_pairs"]) for req in reqs] == [2, 2, 1]

        tile_results = [
            {
                "final_score": np.array([10, 20, 30], dtype=np.int32),
                "base_score": np.array([0, 0, 0], dtype=np.int32),
                "cfg_idx": np.array([0, 0, 0], dtype=np.int32),
                "FT": np.array([1, 1, 1], dtype=np.int32),
                "FF": np.array([1, 1, 1], dtype=np.int32),
                "g_pp": np.array([0, 0, 0], dtype=np.int32),
                "g_cm": np.array([0, 0, 0], dtype=np.int32),
                "g_fm": np.array([0, 0, 0], dtype=np.int32),
                "g_ov": np.array([0, 0, 0], dtype=np.int32),
                "cfg_counts": np.zeros((3, 2), dtype=np.int32),
            },
            {
                "final_score": np.array([15, 19, 31], dtype=np.int32),
                "base_score": np.array([0, 0, 0], dtype=np.int32),
                "cfg_idx": np.array([1, 1, 1], dtype=np.int32),
                "FT": np.array([2, 2, 2], dtype=np.int32),
                "FF": np.array([2, 2, 2], dtype=np.int32),
                "g_pp": np.array([0, 0, 0], dtype=np.int32),
                "g_cm": np.array([0, 0, 0], dtype=np.int32),
                "g_fm": np.array([0, 0, 0], dtype=np.int32),
                "g_ov": np.array([0, 0, 0], dtype=np.int32),
                "cfg_counts": np.ones((3, 2), dtype=np.int32),
            },
            {
                "final_score": np.array([14, 25, 29], dtype=np.int32),
                "base_score": np.array([0, 0, 0], dtype=np.int32),
                "cfg_idx": np.array([2, 2, 2], dtype=np.int32),
                "FT": np.array([3, 3, 3], dtype=np.int32),
                "FF": np.array([3, 3, 3], dtype=np.int32),
                "g_pp": np.array([0, 0, 0], dtype=np.int32),
                "g_cm": np.array([0, 0, 0], dtype=np.int32),
                "g_fm": np.array([0, 0, 0], dtype=np.int32),
                "g_ov": np.array([0, 0, 0], dtype=np.int32),
                "cfg_counts": np.full((3, 2), 2, dtype=np.int32),
            },
        ]
        for req, result in zip(reqs, tile_results):
            executor._response_q.put(GpuResponse(request_id=req.request_id, success=True, result=[result]))

        merged = job.future.result(timeout=1.0)
        assert len(merged) == 1
        assert merged[0]["final_score"].tolist() == [15, 25, 31]
        assert merged[0]["FT"].tolist() == [2, 3, 2]
        assert merged[0]["cfg_idx"].tolist() == [1, 2, 1]
    finally:
        client.close(timeout=0.5)


def test_fg_submit_splits_single_oversized_payload_and_merges_topk_results(monkeypatch):
    executor = _DummyExecutor()
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAIRS", "2")
    monkeypatch.setenv("FG_COALESCE_BREAKPOINTS_MAX_PAYLOADS", "64")
    monkeypatch.setenv("FG_BREAKPOINTS_BATCH_COALESCE_MAX_PAYLOADS", "64")
    client = GpuServiceClient(executor=executor)
    client.start(start_executor=False, in_process_queues=True)

    try:
        payload = {
            "ftff_pairs": [(i, i) for i in range(5)],
            "fg_download_topk": 2,
            "fg_download_base_scores": np.array([100, 100, 100, 100], dtype=np.int32),
            "fg_download_keep_mask": np.array([0, 1, 0, 0], dtype=np.int32),
        }
        job = client.submit_fg_solve_with_breakpoints_batch([payload])

        reqs = [executor._request_q.get(timeout=1.0) for _ in range(3)]
        tile_results = [
            {
                "selected_indices": np.array([0, 1], dtype=np.int32),
                "final_score": np.array([150, 110], dtype=np.int32),
                "base_score": np.array([0, 0], dtype=np.int32),
                "cfg_idx": np.array([10, 11], dtype=np.int32),
                "FT": np.array([1, 1], dtype=np.int32),
                "FF": np.array([1, 1], dtype=np.int32),
                "g_pp": np.array([0, 0], dtype=np.int32),
                "g_cm": np.array([0, 0], dtype=np.int32),
                "g_fm": np.array([0, 0], dtype=np.int32),
                "g_ov": np.array([0, 0], dtype=np.int32),
                "cfg_counts": np.zeros((2, 2), dtype=np.int32),
            },
            {
                "selected_indices": np.array([2, 1], dtype=np.int32),
                "final_score": np.array([170, 130], dtype=np.int32),
                "base_score": np.array([0, 0], dtype=np.int32),
                "cfg_idx": np.array([20, 21], dtype=np.int32),
                "FT": np.array([2, 2], dtype=np.int32),
                "FF": np.array([2, 2], dtype=np.int32),
                "g_pp": np.array([0, 0], dtype=np.int32),
                "g_cm": np.array([0, 0], dtype=np.int32),
                "g_fm": np.array([0, 0], dtype=np.int32),
                "g_ov": np.array([0, 0], dtype=np.int32),
                "cfg_counts": np.ones((2, 2), dtype=np.int32),
            },
            {
                "selected_indices": np.array([3], dtype=np.int32),
                "final_score": np.array([160], dtype=np.int32),
                "base_score": np.array([0], dtype=np.int32),
                "cfg_idx": np.array([30], dtype=np.int32),
                "FT": np.array([3], dtype=np.int32),
                "FF": np.array([3], dtype=np.int32),
                "g_pp": np.array([0], dtype=np.int32),
                "g_cm": np.array([0], dtype=np.int32),
                "g_fm": np.array([0], dtype=np.int32),
                "g_ov": np.array([0], dtype=np.int32),
                "cfg_counts": np.full((1, 2), 2, dtype=np.int32),
            },
        ]
        for req, result in zip(reqs, tile_results):
            executor._response_q.put(GpuResponse(request_id=req.request_id, success=True, result=[result]))

        merged = job.future.result(timeout=1.0)
        assert len(merged) == 1
        assert merged[0]["selected_indices"].tolist() == [2, 3, 1]
        assert merged[0]["final_score"].tolist() == [170, 160, 130]
        assert merged[0]["FT"].tolist() == [2, 3, 2]
        assert merged[0]["cfg_idx"].tolist() == [20, 30, 21]
    finally:
        client.close(timeout=0.5)
