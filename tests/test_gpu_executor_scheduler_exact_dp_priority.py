from __future__ import annotations

from collections import deque
import time

from gear_optimizer.solver.gpu_executor import GpuExecutor, GpuRequest, GpuRequestType


def _req(req_id: int, req_type: GpuRequestType, payload: dict | None = None) -> GpuRequest:
    return GpuRequest(
        request_type=req_type,
        request_id=int(req_id),
        worker_id=1,
        payload=dict(payload or {}),
    )


def _thin_exact_dp(req_id: int, rows: int = 8) -> GpuRequest:
    return _req(
        req_id,
        GpuRequestType.SOLVE_FORCE_GREATS_EXACT_DP,
        {"stats_list": [{"row": idx} for idx in range(rows)]},
    )


def _ga(req_id: int) -> GpuRequest:
    return _req(
        req_id,
        GpuRequestType.GPU_NATIVE_GA_RUN,
        {"n_genomes": 705, "n_generations": 125, "num_runs": 3},
    )


def test_pop_seed_defers_thin_exact_dp_when_ga_ready(monkeypatch):
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._ga_owner_turn_streak = 0
    executor._staged_requests = deque([_thin_exact_dp(701), _ga(702)])
    monkeypatch.setenv("GPU_EXECUTOR_EXACT_DP_RECOVERY_MIN_ROWS", "128")
    monkeypatch.setenv("GPU_EXECUTOR_EXACT_DP_RECOVERY_MAX_AGE_MS", "4000")

    picked = executor._pop_seed_request(timeout=0.0, deadline=time.perf_counter(), batch_max_size=8)

    assert picked.request_id == 702
    assert [req.request_id for req in executor._staged_requests] == [701]


def test_pop_seed_runs_aged_thin_exact_dp_before_ga(monkeypatch):
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._ga_owner_turn_streak = 0
    exact_dp = _thin_exact_dp(711)
    exact_dp.dequeue_perf_ns = time.perf_counter_ns() - 10_000_000
    executor._staged_requests = deque([exact_dp, _ga(712)])
    monkeypatch.setenv("GPU_EXECUTOR_EXACT_DP_RECOVERY_MIN_ROWS", "128")
    monkeypatch.setenv("GPU_EXECUTOR_EXACT_DP_RECOVERY_MAX_AGE_MS", "1")

    picked = executor._pop_seed_request(timeout=0.0, deadline=time.perf_counter(), batch_max_size=8)

    assert picked.request_id == 711
    assert [req.request_id for req in executor._staged_requests] == [712]


def test_pop_seed_runs_large_exact_dp_before_ga(monkeypatch):
    executor = GpuExecutor()
    executor._in_process_queues = True
    executor._ga_owner_turn_streak = 0
    executor._staged_requests = deque([_thin_exact_dp(721, rows=256), _ga(722)])
    monkeypatch.setenv("GPU_EXECUTOR_EXACT_DP_RECOVERY_MIN_ROWS", "128")
    monkeypatch.setenv("GPU_EXECUTOR_EXACT_DP_RECOVERY_MAX_AGE_MS", "4000")

    picked = executor._pop_seed_request(timeout=0.0, deadline=time.perf_counter(), batch_max_size=8)

    assert picked.request_id == 721
    assert [req.request_id for req in executor._staged_requests] == [722]
