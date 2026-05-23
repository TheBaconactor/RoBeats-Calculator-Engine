from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


@dataclass(frozen=True)
class GpuExecBreakdown:
    host_sec: float
    gpu_kernel_sec: float
    gpu_upload_sec: float
    gpu_download_sec: float


@dataclass(frozen=True)
class RequestLatencyWindow:
    request_type: GpuRequestType
    queue_sec: float
    in_exec_sec: float
    total_sec: float


@dataclass(frozen=True)
class ExecutorIdleSummary:
    total_sec: float = 0.0
    max_sec: float = 0.0
    p95_sec: float = 0.0
    initial_sec: float = 0.0
    tail_sec: float = 0.0


@dataclass(frozen=True)
class RequestLatencySummaryRow:
    request_type: GpuRequestType
    count: int
    total_avg_sec: float
    total_p95_sec: float
    queue_avg_sec: float
    queue_p95_sec: float
    in_exec_avg_sec: float
    in_exec_p95_sec: float


@dataclass(frozen=True)
class ExecBreakdownSummaryRow:
    request_type: GpuRequestType
    exec_sec: float
    host_sec: float
    gpu_kernel_sec: float
    gpu_upload_sec: float
    gpu_download_sec: float


@dataclass(frozen=True)
class IdleTransitionSummaryRow:
    previous_type: GpuRequestType | None
    next_type: GpuRequestType | None
    sec: float
    count: int


@dataclass(frozen=True)
class FgTaskBatchStats:
    batches: int
    total: int
    max_tasks: int


@dataclass(frozen=True)
class WorkloadProfileSettings:
    enabled: bool = False
    window_size: int = 0
    interval_sec: float = 0.0


@dataclass(frozen=True)
class WorkloadWindowEmitResult:
    emitted: bool
    window: list[dict[str, Any]]
    last_emit_ts: float | None = None
    events_emitted: int = 0


def exec_breakdown_enabled(
    *,
    profile_enabled: bool,
    gpu_profiler_enabled: bool,
    env_flag_fn: Callable[[str, str], bool],
) -> bool:
    _ = profile_enabled, gpu_profiler_enabled, env_flag_fn
    return False


def profile_events_output_enabled(env_get_fn: Callable[..., Any]) -> bool:
    _ = env_get_fn
    return False


def record_fg_task_batch_stats(
    task_count: int,
    *,
    batches: int,
    total: int,
    max_tasks: int,
    batch_hist: Any,
) -> FgTaskBatchStats:
    _ = task_count, batch_hist
    return FgTaskBatchStats(batches=int(batches), total=int(total), max_tasks=int(max_tasks))


def record_pack_stats(
    request_type: GpuRequestType,
    dt_sec: float,
    **kwargs: Any,
) -> float:
    _ = request_type, dt_sec
    return float(kwargs.get("pack_sec", kwargs.get("current_pack_sec", 0.0)) or 0.0)


def executor_profile_log_message(**kwargs: Any) -> str:
    requests_processed = int(kwargs.get("requests_processed", 0) or 0)
    registered_workers = int(kwargs.get("registered_workers", 0) or 0)
    return f"[GpuExecutor] requests={requests_processed} registered_workers={registered_workers}"


def fg_tasks_per_sec_log_message(**kwargs: Any) -> str | None:
    _ = kwargs
    return None


def gpu_profiler_snapshot(**kwargs: Any) -> tuple[float, float, float]:
    _ = kwargs
    return (0.0, 0.0, 0.0)


def build_executor_idle_summary(**kwargs: Any) -> ExecutorIdleSummary:
    _ = kwargs
    return ExecutorIdleSummary()


def build_request_latency_summary(**kwargs: Any) -> list[RequestLatencySummaryRow]:
    _ = kwargs
    return []


def record_request_latency_stats(
    latency: RequestLatencyWindow,
    **kwargs: Any,
) -> None:
    _ = latency, kwargs


def build_idle_transition_summary(**kwargs: Any) -> list[IdleTransitionSummaryRow]:
    _ = kwargs
    return []


def request_latency_summary_log_message(rows: list[RequestLatencySummaryRow]) -> str | None:
    _ = rows
    return None


def exec_breakdown_summary_log_message(rows: list[ExecBreakdownSummaryRow]) -> str | None:
    _ = rows
    return None


def idle_transition_summary_log_message(rows: list[IdleTransitionSummaryRow]) -> str | None:
    _ = rows
    return None


def build_exec_breakdown_summary(**kwargs: Any) -> list[ExecBreakdownSummaryRow]:
    _ = kwargs
    return []


def compute_exec_breakdown(**kwargs: Any) -> GpuExecBreakdown | None:
    _ = kwargs
    return None


def record_exec_breakdown_stats(
    request_type: GpuRequestType,
    breakdown: GpuExecBreakdown,
    **kwargs: Any,
) -> None:
    _ = request_type, breakdown, kwargs


def compute_request_latency_window(request: GpuRequest, **kwargs: Any) -> RequestLatencyWindow | None:
    _ = request, kwargs
    return None


def build_executor_profile_stats(**kwargs: Any) -> dict[str, Any]:
    _ = kwargs
    return {}


def build_executor_stats(**kwargs: Any) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "requests_processed": int(kwargs.get("requests_processed", 0) or 0),
        "registered_workers": int(kwargs.get("registered_workers", 0) or 0),
    }
    profile = kwargs.get("profile")
    if profile:
        stats["profile"] = profile
    return stats


class ExecutorTraceWriter:
    @property
    def has_file(self) -> bool:
        return False

    def open(self, trace_path: str | None) -> None:
        _ = trace_path

    def close(self) -> None:
        return None

    def write(self, event: str, **kwargs: Any) -> None:
        _ = event, kwargs


def load_workload_profile_settings(**kwargs: Any) -> WorkloadProfileSettings:
    _ = kwargs
    return WorkloadProfileSettings()


def size_hint(value: Any) -> int:
    try:
        return int(len(value))
    except (TypeError, ValueError):
        return 0


def payload_dict(req: GpuRequest) -> dict[str, Any]:
    payload = getattr(req, "payload", None)
    return payload if isinstance(payload, dict) else {}


def percentile95(values: Any) -> float:
    _ = values
    return 0.0


def estimate_request_work_units(request: GpuRequest, *, size_hint_fn: Callable[[Any], int] = size_hint) -> float:
    payload = payload_dict(request)
    for key in ("tasks", "payloads", "genomes", "population"):
        if key in payload:
            return float(size_hint_fn(payload.get(key)))
    return 1.0


def summarize_batch(
    batch: list[GpuRequest],
    *,
    queue_depth_hint: int = 0,
    pressure_hint: float = 0.0,
    age_samples: list[float] | None = None,
    work_units_samples: list[float] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    _ = age_samples, work_units_samples, kwargs
    dominant_type = batch[0].request_type if batch else None
    return {
        "batch_size": int(len(batch)),
        "queue_depth_hint": int(queue_depth_hint),
        "pressure_hint": float(pressure_hint),
        "dominant_type": dominant_type.value if dominant_type is not None else "",
        "dominant_share_pct": 100.0 if batch else 0.0,
        "diversity_pct": 0.0,
        "work_units": float(len(batch)),
        "avg_submit_age_ms": 0.0,
    }


def should_emit_workload_batch_event(metrics: dict[str, Any]) -> bool:
    _ = metrics
    return False


def workload_batch_event_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return dict(metrics or {})


def emit_workload_batch_profile(metrics: dict[str, Any], *, emit_profile_event_fn: Callable[..., None]) -> bool:
    _ = metrics, emit_profile_event_fn
    return False


def batch_trace_context(metrics: dict[str, Any]) -> dict[str, Any]:
    return dict(metrics or {})


def record_workload_batch_state(
    metrics: dict[str, Any],
    **kwargs: Any,
) -> str:
    _ = metrics, kwargs
    return ""


def workload_window_event_metrics(window: list[dict[str, Any]]) -> dict[str, Any]:
    _ = window
    return {}


def workload_window_log_message(metrics: dict[str, Any]) -> str:
    _ = metrics
    return ""


def emit_workload_window_profile(
    window: list[dict[str, Any]],
    *,
    emit_profile_event_fn: Callable[..., None],
) -> bool:
    _ = window, emit_profile_event_fn
    return False


def maybe_emit_workload_window_profile(**kwargs: Any) -> WorkloadWindowEmitResult:
    recent = kwargs.get("recent_batches", kwargs.get("window", []))
    events = int(kwargs.get("events_emitted", 0) or 0)
    last_emit_ts = kwargs.get("last_emit_ts")
    return WorkloadWindowEmitResult(
        emitted=False,
        window=list(recent or []),
        last_emit_ts=last_emit_ts,
        events_emitted=events,
    )


def workload_stop_summary_metrics(**kwargs: Any) -> dict[str, Any]:
    _ = kwargs
    return {}


def workload_stop_summary_log_message(metrics: dict[str, Any]) -> str:
    _ = metrics
    return ""


def workload_stop_summary_event_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    _ = metrics
    return {}


def emit_workload_stop_summary(**kwargs: Any) -> bool:
    _ = kwargs
    return False
