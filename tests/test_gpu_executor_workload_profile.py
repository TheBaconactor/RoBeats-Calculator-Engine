import queue

import gear_optimizer.solver.gpu_executor as gpu_executor_module
from gear_optimizer.solver.gpu_executor import _BatchPlan, GpuExecutor, GpuRequest, GpuRequestType


def _fresh_executor() -> GpuExecutor:
    GpuExecutor._instance = None
    return GpuExecutor()


def test_summarize_batch_reports_workload_shape():
    ex = _fresh_executor()
    plan = _BatchPlan(wait_ms=2, max_batch=16, mode="inproc", queue_depth_hint=12, pressure_hint=0.75)
    reqs = [
        GpuRequest(
            request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            request_id=1,
            worker_id=0,
            payload={"population_indices": [1] * 24},
            submit_perf_ns=10_000_000,
            dequeue_perf_ns=13_000_000,
        ),
        GpuRequest(
            request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
            request_id=2,
            worker_id=0,
            payload={"population_indices": [1] * 32},
            submit_perf_ns=11_000_000,
            dequeue_perf_ns=15_500_000,
        ),
        GpuRequest(
            request_type=GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
            request_id=3,
            worker_id=0,
            payload={
                "args": ([1] * 20, None, None, 0, 0.0, None, None),
                "kwargs": {
                    "n_genomes_override": 20,
                    "fg_tasks": [
                        {"ftff_pairs": [(0, 0), (1, 1), (2, 2), (3, 3)]},
                    ],
                },
            },
            submit_perf_ns=12_000_000,
            dequeue_perf_ns=17_000_000,
        ),
    ]
    ex._workload_batch_seq = 7
    metrics = ex._summarize_batch(reqs, plan=plan, wait_sec=0.004)

    assert metrics["batch_id"] == 7
    assert metrics["size"] == 3
    assert metrics["distinct_types"] == 2
    assert metrics["dominant_type"] == GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY.value
    assert metrics["dominant_share_pct"] > 60.0
    assert metrics["work_units"] >= 80.0
    assert metrics["avg_submit_age_ms"] > 0.0
    assert metrics["queue_depth_hint"] == 12


def test_record_workload_batch_accumulates_mode_counters():
    ex = _fresh_executor()
    ex._workload_profile_enabled = False

    ex._record_workload_batch(
        {
            "batch_id": 1,
            "mode": "throughput",
            "wait_ms": 1.5,
            "exec_sec": 0.25,
            "size": 8,
            "work_units": 120.0,
            "diversity_pct": 15.0,
            "queue_depth_hint": 20,
            "avg_submit_age_ms": 3.0,
            "pressure_hint": 2.5,
        }
    )
    ex._record_workload_batch(
        {
            "batch_id": 2,
            "mode": "throughput",
            "wait_ms": 1.0,
            "exec_sec": 0.15,
            "size": 6,
            "work_units": 70.0,
            "diversity_pct": 10.0,
            "queue_depth_hint": 12,
            "avg_submit_age_ms": 2.0,
            "pressure_hint": 1.5,
        }
    )

    assert ex._workload_mode_counts["throughput"] == 2
    assert ex._last_batch_plan_mode == "throughput"
    assert len(ex._workload_recent_batches) == 2
    assert sum(ex._workload_units_samples) == 190.0


class _CaptureTimeoutQueue:
    def __init__(self) -> None:
        self.timeouts: list[float] = []

    def get(self, *, timeout: float = 0.0):
        self.timeouts.append(float(timeout))
        raise queue.Empty


def test_gather_batch_inproc_idle_wait_uses_recent_timeout(monkeypatch):
    ex = _fresh_executor()
    ex._in_process_queues = True
    ex._request_queue = _CaptureTimeoutQueue()
    ex._short_wait_spin_sec = 0.0
    ex._last_work_end_ts = 100.0

    monkeypatch.setenv("GPU_EXECUTOR_INPROC_IDLE_WAIT_MS", "100")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_IDLE_RECENT_WAIT_MS", "5")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_IDLE_RECENT_GRACE_MS", "250")
    monkeypatch.setattr(gpu_executor_module, "perf_counter", lambda: 100.05, raising=True)

    out = ex._gather_batch(max_wait_ms=6, max_batch_size=8)

    assert out == []
    assert ex._request_queue.timeouts[0] == 0.005


def test_gather_batch_inproc_idle_wait_falls_back_to_idle_timeout(monkeypatch):
    ex = _fresh_executor()
    ex._in_process_queues = True
    ex._request_queue = _CaptureTimeoutQueue()
    ex._short_wait_spin_sec = 0.0
    ex._last_work_end_ts = 100.0

    monkeypatch.setenv("GPU_EXECUTOR_INPROC_IDLE_WAIT_MS", "100")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_IDLE_RECENT_WAIT_MS", "5")
    monkeypatch.setenv("GPU_EXECUTOR_INPROC_IDLE_RECENT_GRACE_MS", "25")
    monkeypatch.setattr(gpu_executor_module, "perf_counter", lambda: 100.10, raising=True)

    out = ex._gather_batch(max_wait_ms=6, max_batch_size=8)

    assert out == []
    assert ex._request_queue.timeouts[0] == 0.1
