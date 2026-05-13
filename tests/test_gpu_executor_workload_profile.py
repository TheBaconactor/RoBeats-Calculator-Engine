import queue

import pytest

import gear_optimizer.solver.gpu_executor as gpu_executor_module
from gear_optimizer.solver.gpu_executor import GpuExecutor
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType
from gear_optimizer.solver.gpu_executor_batching import BatchPlan as _BatchPlan
from gear_optimizer.solver.gpu_executor_workload import (
    batch_trace_context,
    estimate_request_work_units,
    load_workload_profile_settings,
    payload_dict,
    percentile95,
    size_hint,
    summarize_batch,
)
from gear_optimizer.solver.gpu_executor_workload import (
    should_emit_workload_batch_event,
    record_workload_batch_state,
    emit_workload_stop_summary,
    workload_batch_event_metrics,
    workload_stop_summary_metrics,
    workload_stop_summary_event_metrics,
    workload_stop_summary_log_message,
    workload_window_event_metrics,
    workload_window_log_message,
)


def _fresh_executor() -> GpuExecutor:
    GpuExecutor._instance = None
    return GpuExecutor()


def test_summarize_batch_reports_workload_shape():
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
    metrics = summarize_batch(reqs, plan=plan, wait_sec=0.004, batch_id=7)

    assert metrics["batch_id"] == 7
    assert metrics["size"] == 3
    assert metrics["distinct_types"] == 2
    assert metrics["dominant_type"] == GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY.value
    assert metrics["dominant_share_pct"] > 60.0
    assert metrics["work_units"] >= 80.0
    assert metrics["avg_submit_age_ms"] > 0.0
    assert metrics["queue_depth_hint"] == 12


def test_workload_module_estimates_native_ga_and_fused_fg_units():
    native_ga = GpuRequest(
        request_type=GpuRequestType.GPU_NATIVE_GA_RUN,
        request_id=10,
        worker_id=0,
        payload={"n_genomes": 12, "n_generations": 5, "num_runs": 2},
    )
    fused = GpuRequest(
        request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
        request_id=11,
        worker_id=0,
        payload={"ftff_pairs": [(0, 0), (1, 1), (2, 2)]},
    )

    assert estimate_request_work_units(native_ga) == 120.0
    assert estimate_request_work_units(fused) == 3.0


def test_load_workload_profile_settings_enables_from_parent_profile_or_env():
    disabled = load_workload_profile_settings(
        profile_enabled=False,
        env_flag_fn=lambda _key, _default: False,
        env_get_fn=lambda _key, default: default,
    )
    parent_enabled = load_workload_profile_settings(
        profile_enabled=True,
        env_flag_fn=lambda _key, _default: False,
        env_get_fn=lambda _key, default: default,
    )
    env_enabled = load_workload_profile_settings(
        profile_enabled=False,
        env_flag_fn=lambda _key, _default: True,
        env_get_fn=lambda _key, default: default,
    )

    assert not disabled.enabled
    assert disabled.interval_sec == 2.0
    assert parent_enabled.enabled
    assert env_enabled.enabled


def test_load_workload_profile_settings_clamps_invalid_interval():
    low = load_workload_profile_settings(
        profile_enabled=True,
        env_flag_fn=lambda _key, _default: False,
        env_get_fn=lambda _key, _default: "0.01",
    )
    invalid = load_workload_profile_settings(
        profile_enabled=True,
        env_flag_fn=lambda _key, _default: False,
        env_get_fn=lambda _key, _default: "bad",
    )

    assert low.interval_sec == 0.2
    assert invalid.interval_sec == 2.0


def test_payload_dict_normalizes_non_dict_payloads():
    good = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=20,
        worker_id=0,
        payload={"population_indices": [1, 2, 3]},
    )
    bad = GpuRequest(
        request_type=GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY,
        request_id=21,
        worker_id=0,
        payload=None,
    )

    assert payload_dict(good) == {"population_indices": [1, 2, 3]}
    assert payload_dict(bad) == {}


def test_percentile95_handles_empty_and_sorted_samples():
    assert percentile95([]) == 0.0
    assert percentile95(None) == 0.0
    assert percentile95([10, 1, 5, 20]) == 20.0
    assert percentile95([1, 2, 3]) == 3.0


def test_workload_module_is_single_summarize_batch_owner():
    plan = _BatchPlan(wait_ms=1, max_batch=8, mode="compat", queue_depth_hint=2, pressure_hint=0.5)
    reqs = [
        GpuRequest(
            request_type=GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS,
            request_id=12,
            worker_id=0,
            payload={"ftff_pairs": [(0, 0), (1, 1)]},
        )
    ]

    metrics = summarize_batch(reqs, plan=plan, wait_sec=0.001, batch_id=33)

    assert not hasattr(GpuExecutor, "_summarize_batch")
    assert metrics["fg_count"] == 1
    assert metrics["coalescable_count"] == 1
    assert metrics["work_units"] == 2.0
    assert size_hint([(0, 0), (1, 1), (2, 2)]) == 3


def test_record_workload_batch_state_accumulates_canonical_metrics():
    from collections import defaultdict, deque

    recent_batches = deque(maxlen=4)
    mode_counts = defaultdict(int)
    mode_wait_sec = defaultdict(float)
    mode_exec_sec = defaultdict(float)
    queue_depth_samples = deque(maxlen=4)
    age_ms_samples = deque(maxlen=4)
    units_samples = deque(maxlen=4)
    diversity_samples = deque(maxlen=4)
    pressure_samples = deque(maxlen=4)

    last_mode = record_workload_batch_state(
        {
            "batch_id": 1,
            "mode": "throughput",
            "wait_ms": 1.5,
            "exec_sec": 0.25,
            "work_units": 120.0,
            "diversity_pct": 15.0,
            "queue_depth_hint": 20,
            "avg_submit_age_ms": 3.0,
            "pressure_hint": 2.5,
        },
        recent_batches=recent_batches,
        mode_counts=mode_counts,
        mode_wait_sec=mode_wait_sec,
        mode_exec_sec=mode_exec_sec,
        queue_depth_samples=queue_depth_samples,
        age_ms_samples=age_ms_samples,
        units_samples=units_samples,
        diversity_samples=diversity_samples,
        pressure_samples=pressure_samples,
        last_batch_plan_mode="compat",
    )

    assert last_mode == "throughput"
    assert mode_counts["throughput"] == 1
    assert mode_wait_sec["throughput"] == pytest.approx(0.0015)
    assert mode_exec_sec["throughput"] == 0.25
    assert list(queue_depth_samples) == [20.0]
    assert list(age_ms_samples) == [3.0]
    assert list(units_samples) == [120.0]
    assert list(diversity_samples) == [15.0]
    assert list(pressure_samples) == [2.5]
    assert list(recent_batches)[0]["batch_id"] == 1


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


def test_workload_batch_event_policy_and_payload_shape():
    metrics = {
        "batch_id": 64,
        "mode": "compat",
        "size": 3,
        "types": "solve:3",
        "dominant_type": "solve",
        "dominant_share_pct": 100.0,
        "diversity_pct": 0.0,
        "work_units": 24.0,
        "queue_depth_hint": 8,
        "avg_submit_age_ms": 2.5,
        "wait_ms": 1.25,
        "exec_sec": 0.004,
        "pressure_hint": 0.25,
    }

    assert should_emit_workload_batch_event(metrics)
    assert not should_emit_workload_batch_event(dict(metrics, batch_id=63, pressure_hint=0.25))
    assert should_emit_workload_batch_event(dict(metrics, batch_id=63, pressure_hint=1.0))
    assert should_emit_workload_batch_event(dict(metrics, batch_id=63, pressure_hint=0.25, mode="fg_recovery"))
    assert workload_batch_event_metrics(metrics) == {
        "batch_id": 64,
        "mode": "compat",
        "size": 3,
        "types": "solve:3",
        "dominant_type": "solve",
        "dominant_share_pct": 100.0,
        "diversity_pct": 0.0,
        "work_units": 24.0,
        "queue_depth_hint": 8,
        "avg_submit_age_ms": 2.5,
        "wait_ms": 1.25,
        "exec_ms": 4.0,
    }


def test_batch_trace_context_preserves_trace_field_shape():
    metrics = {
        "mode": "fg_burst",
        "queue_depth_hint": 9,
        "pressure_hint": 0.75,
        "work_units": 33.5,
        "dominant_type": "ga_fg_fused_solve_with_breakpoints",
        "dominant_share_pct": 66.6,
        "diversity_pct": 12.5,
        "avg_submit_age_ms": 4.25,
    }

    assert batch_trace_context(metrics) == {
        "planner_mode": "fg_burst",
        "queue_depth_hint": 9,
        "pressure_hint": 0.75,
        "work_units": 33.5,
        "dominant_type": "ga_fg_fused_solve_with_breakpoints",
        "dominant_share_pct": 66.6,
        "diversity_pct": 12.5,
        "avg_submit_age_ms": 4.25,
    }


def test_workload_window_event_metrics_summarizes_recent_batches():
    window = [
        {
            "mode": "throughput",
            "wait_ms": 2.0,
            "exec_sec": 0.004,
            "size": 4,
            "work_units": 40.0,
            "diversity_pct": 20.0,
            "queue_depth_hint": 10,
            "fg_count": 1,
        },
        {
            "mode": "fg_recovery",
            "wait_ms": 1.0,
            "exec_sec": 0.002,
            "size": 2,
            "work_units": 20.0,
            "diversity_pct": 10.0,
            "queue_depth_hint": 6,
            "fg_count": 2,
        },
    ]

    metrics = workload_window_event_metrics(window)

    assert metrics["batches"] == 2
    assert metrics["busy_pct"] == pytest.approx(66.6666667)
    assert metrics["avg_batch"] == 3.0
    assert metrics["avg_work_units"] == 30.0
    assert metrics["avg_diversity_pct"] == 15.0
    assert metrics["avg_queue_depth_hint"] == 8.0
    assert metrics["fg_share_pct"] == 50.0
    assert metrics["mode_top"] == "throughput:1,fg_recovery:1"
    assert workload_window_event_metrics([]) == {}


def test_workload_window_log_message_preserves_profile_format():
    message = workload_window_log_message(
        {
            "batches": 2,
            "busy_pct": 66.6666667,
            "avg_batch": 3.0,
            "avg_work_units": 30.0,
            "fg_share_pct": 50.0,
            "avg_queue_depth_hint": 8.0,
            "avg_diversity_pct": 15.0,
            "mode_top": "throughput:1,fg_recovery:1",
        }
    )

    assert message == (
        "[GpuExecutor][WORKLOAD] window_batches=2 busy=66.7% avg_batch=3.00 "
        "avg_units=30.0 fg_share=50.0% qdepth~=8.0 diversity=15.0% "
        "modes=[throughput:1,fg_recovery:1]"
    )


def test_workload_stop_summary_metrics_shapes_profile_payload():
    window = [
        {
            "mode": "throughput",
            "work_units": 40.0,
            "diversity_pct": 20.0,
            "queue_depth_hint": 10,
            "avg_submit_age_ms": 2.0,
        },
        {
            "mode": "fg_recovery",
            "work_units": 20.0,
            "diversity_pct": 10.0,
            "queue_depth_hint": 6,
            "avg_submit_age_ms": 4.0,
        },
    ]

    metrics = workload_stop_summary_metrics(
        window,
        age_ms_samples=[1.0, 3.0, 5.0],
        units_samples=[10.0, 20.0, 30.0],
        diversity_samples=[5.0, 15.0, 25.0],
        queue_depth_samples=[2.0, 6.0, 10.0],
        mode_counts={"throughput": 3, "fg_recovery": 2},
        events_emitted=7,
        last_mode="throughput",
    )

    assert metrics == {
        "batches": 2,
        "avg_work_units": 30.0,
        "p95_work_units": 30.0,
        "avg_diversity_pct": 15.0,
        "p95_diversity_pct": 25.0,
        "avg_queue_depth_hint": 8.0,
        "p95_queue_depth_hint": 10.0,
        "avg_submit_age_ms": 3.0,
        "p95_submit_age_ms": 5.0,
        "events_emitted": 7,
        "last_mode": "throughput",
        "mode_top": "throughput:3, fg_recovery:2",
    }
    assert workload_stop_summary_metrics(
        [],
        age_ms_samples=[],
        units_samples=[],
        diversity_samples=[],
        queue_depth_samples=[],
        mode_counts={},
        events_emitted=0,
        last_mode="",
    ) == {}


def test_workload_stop_summary_event_metrics_omits_log_only_mode_top():
    metrics = {
        "batches": 2,
        "avg_work_units": 30.0,
        "mode_top": "throughput:3, fg_recovery:2",
    }

    assert workload_stop_summary_event_metrics(metrics) == {
        "batches": 2,
        "avg_work_units": 30.0,
    }


def test_workload_stop_summary_log_message_preserves_profile_format():
    message = workload_stop_summary_log_message(
        {
            "batches": 2,
            "avg_work_units": 30.0,
            "p95_work_units": 30.0,
            "avg_diversity_pct": 15.0,
            "p95_diversity_pct": 25.0,
            "avg_queue_depth_hint": 8.0,
            "p95_queue_depth_hint": 10.0,
            "avg_submit_age_ms": 3.0,
            "p95_submit_age_ms": 5.0,
            "events_emitted": 7,
            "mode_top": "throughput:3, fg_recovery:2",
        }
    )

    assert message == (
        "[GpuExecutor][WORKLOAD][SUMMARY] batches=2 avg_units=30.0 p95_units=30.0 "
        "avg_diversity=15.0% p95_diversity=25.0% avg_qdepth=8.0 p95_qdepth=10.0 "
        "avg_submit_age=3.00ms p95_submit_age=5.00ms events=7 modes=[throughput:3, fg_recovery:2]"
    )


def test_emit_workload_stop_summary_logs_and_emits_profile_event():
    logs = []
    events = []

    emitted = emit_workload_stop_summary(
        [
            {
                "mode": "throughput",
                "work_units": 40.0,
                "diversity_pct": 20.0,
                "queue_depth_hint": 10,
                "avg_submit_age_ms": 2.0,
            }
        ],
        age_ms_samples=[2.0],
        units_samples=[40.0],
        diversity_samples=[20.0],
        queue_depth_samples=[10.0],
        mode_counts={"throughput": 1},
        events_emitted=3,
        last_mode="throughput",
        log_debug=lambda message: logs.append(message),
        emit_profile_event_fn=lambda **kwargs: events.append(kwargs),
    )

    assert emitted is True
    assert logs == [
        "[GpuExecutor][WORKLOAD][SUMMARY] batches=1 avg_units=40.0 p95_units=40.0 "
        "avg_diversity=20.0% p95_diversity=20.0% avg_qdepth=10.0 p95_qdepth=10.0 "
        "avg_submit_age=2.00ms p95_submit_age=2.00ms events=3 modes=[throughput:1]"
    ]
    assert events == [
        {
            "component": "gpu_executor",
            "event": "workload::summary",
            "metrics": {
                "batches": 1,
                "avg_work_units": 40.0,
                "p95_work_units": 40.0,
                "avg_diversity_pct": 20.0,
                "p95_diversity_pct": 20.0,
                "avg_queue_depth_hint": 10.0,
                "p95_queue_depth_hint": 10.0,
                "avg_submit_age_ms": 2.0,
                "p95_submit_age_ms": 2.0,
                "events_emitted": 3,
                "last_mode": "throughput",
            },
        }
    ]


def test_emit_workload_stop_summary_skips_empty_window():
    assert (
        emit_workload_stop_summary(
            [],
            age_ms_samples=[],
            units_samples=[],
            diversity_samples=[],
            queue_depth_samples=[],
            mode_counts={},
            events_emitted=0,
            last_mode="",
            log_debug=lambda _message: None,
            emit_profile_event_fn=lambda **_kwargs: None,
        )
        is False
    )


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
