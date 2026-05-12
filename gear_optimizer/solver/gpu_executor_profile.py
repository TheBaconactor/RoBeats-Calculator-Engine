from __future__ import annotations

from dataclasses import dataclass
import logging
import random
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_types import GpuRequestType


logger = logging.getLogger(__name__)


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
    total_sec: float
    max_sec: float
    p95_sec: float
    initial_sec: float
    tail_sec: float


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

    def format_log_part(self) -> str:
        return (
            f"{self.request_type.value}:n={int(self.count)} "
            f"total_avg={self.total_avg_sec * 1000:.1f}ms p95={self.total_p95_sec * 1000:.1f}ms "
            f"queue_avg={self.queue_avg_sec * 1000:.1f}ms p95={self.queue_p95_sec * 1000:.1f}ms "
            f"in_exec_avg={self.in_exec_avg_sec * 1000:.1f}ms p95={self.in_exec_p95_sec * 1000:.1f}ms"
        )


@dataclass(frozen=True)
class ExecBreakdownSummaryRow:
    request_type: GpuRequestType
    exec_sec: float
    host_sec: float
    gpu_kernel_sec: float
    gpu_upload_sec: float
    gpu_download_sec: float

    def format_log_part(self) -> str:
        return (
            f"{self.request_type.value}:exec={float(self.exec_sec):.2f}s host~={self.host_sec:.2f}s "
            f"gpu_kernel~={self.gpu_kernel_sec:.2f}s up~={self.gpu_upload_sec:.2f}s "
            f"down~={self.gpu_download_sec:.2f}s"
        )


@dataclass(frozen=True)
class IdleTransitionSummaryRow:
    previous_type: GpuRequestType | None
    next_type: GpuRequestType | None
    sec: float
    count: int

    def format_log_part(self) -> str:
        prev_s = self.previous_type.value if self.previous_type is not None else "<start>"
        next_s = self.next_type.value if self.next_type is not None else "<none>"
        return f"{prev_s}->{next_s}:{self.sec:.2f}s({int(self.count)})"


@dataclass(frozen=True)
class FgTaskBatchStats:
    batches: int
    total: int
    max_tasks: int


def exec_breakdown_enabled(
    *,
    profile_enabled: bool,
    gpu_profiler_enabled: bool,
    env_flag_fn: Callable[[str, str], bool],
) -> bool:
    return bool(profile_enabled or gpu_profiler_enabled or env_flag_fn("GPU_EXECUTOR_EXEC_BREAKDOWN", "0"))


def profile_events_output_enabled(env_get_fn: Callable[..., Any]) -> bool:
    try:
        metafinder_path = str(env_get_fn("METAFINDER_PROFILE_EVENTS_PATH") or "").strip()
        generic_path = str(env_get_fn("PROFILE_EVENTS_PATH") or "").strip()
    except (ValueError, TypeError):
        return False
    return bool(metafinder_path or generic_path)


def record_fg_task_batch_stats(
    task_count: int,
    *,
    batches: int,
    total: int,
    max_tasks: int,
    batch_hist: Any,
) -> FgTaskBatchStats:
    try:
        task_count_i = int(task_count)
    except (ValueError, TypeError):
        task_count_i = 0
    try:
        batches_i = int(batches)
    except (ValueError, TypeError):
        batches_i = 0
    try:
        total_i = int(total)
    except (ValueError, TypeError):
        total_i = 0
    try:
        max_tasks_i = int(max_tasks)
    except (ValueError, TypeError):
        max_tasks_i = 0
    if task_count_i <= 0:
        return FgTaskBatchStats(batches=batches_i, total=total_i, max_tasks=max_tasks_i)

    batch_hist[task_count_i] += 1
    return FgTaskBatchStats(
        batches=batches_i + 1,
        total=total_i + task_count_i,
        max_tasks=max(max_tasks_i, task_count_i),
    )


def record_pack_stats(
    request_type: GpuRequestType,
    dt_sec: float,
    *,
    pack_sec: float,
    req_type_pack_sec: Any,
) -> float:
    try:
        current_pack_sec = float(pack_sec)
    except (ValueError, TypeError):
        current_pack_sec = 0.0
    try:
        dt = float(dt_sec)
    except (ValueError, TypeError):
        return current_pack_sec
    if dt <= 0.0:
        return current_pack_sec

    try:
        req_type_pack_sec[request_type] += dt
    except (ValueError, TypeError, KeyError):
        return current_pack_sec
    return current_pack_sec + dt


def executor_profile_log_message(
    *,
    wait_sec: float,
    exec_sec: float,
    requests_processed: int,
    batch_size_sum: int,
    batches_observed: int,
    pack_sec: float,
    req_type_exec_sec: Any,
    req_type_counts: Any,
    req_type_pack_sec: Any,
    batch_size_counts: Any,
    fg_tasks_batches: int,
    fg_tasks_total: int,
    fg_tasks_max: int,
    fg_tasks_batch_hist: Any,
    idle_gaps_count: int,
    idle_summary: ExecutorIdleSummary,
) -> str:
    wait_sec = float(wait_sec)
    exec_sec = float(exec_sec)
    total = wait_sec + exec_sec
    util = (exec_sec / total * 100.0) if total > 0 else 0.0
    avg = (exec_sec / int(requests_processed)) if int(requests_processed) else 0.0
    avg_batch = (int(batch_size_sum) / int(batches_observed)) if int(batches_observed) else 0.0

    top_types = sorted(getattr(req_type_exec_sec, "items", lambda: [])(), key=lambda kv: kv[1], reverse=True)[:6]
    top_types_str = ", ".join(
        f"{req_type.value}:{int(req_type_counts.get(req_type, 0) or 0)} ({float(sec):.2f}s)"
        for req_type, sec in top_types
    )
    top_pack = sorted(getattr(req_type_pack_sec, "items", lambda: [])(), key=lambda kv: kv[1], reverse=True)[:6]
    top_pack_str = ", ".join(f"{req_type.value}:{float(sec):.2f}s" for req_type, sec in top_pack if float(sec) > 0.0)
    top_batch_sizes = sorted(getattr(batch_size_counts, "items", lambda: [])(), key=lambda kv: kv[0])[:16]
    batch_hist_str = ", ".join(f"{int(size)}:{int(count)}" for size, count in top_batch_sizes if count)

    fg_tasks_avg = (int(fg_tasks_total) / int(fg_tasks_batches)) if int(fg_tasks_batches) else 0.0
    fg_tasks_hist = ""
    if int(fg_tasks_batches):
        top_fg = sorted(getattr(fg_tasks_batch_hist, "items", lambda: [])(), key=lambda kv: (-kv[1], kv[0]))[:8]
        fg_tasks_hist = ", ".join(f"{int(size)}:{int(count)}" for size, count in top_fg if count)

    return (
        "[GpuExecutor][PROFILE] "
        f"wait={wait_sec:.2f}s exec={exec_sec:.2f}s busy={util:.1f}% (executor) "
        f"avg_exec_per_req={avg:.3f}s avg_batch={avg_batch:.2f} "
        f"pack={float(pack_sec):.2f}s pack_types=[{top_pack_str}] "
        f"idle_gaps={int(idle_gaps_count)} idle_sum={idle_summary.total_sec:.2f}s "
        f"idle_max={idle_summary.max_sec:.3f}s idle_p95={idle_summary.p95_sec:.3f}s "
        f"idle_initial={idle_summary.initial_sec:.3f}s idle_tail={idle_summary.tail_sec:.3f}s "
        f"types=[{top_types_str}] batch_sizes=[{batch_hist_str}] "
        f"fg_task_batches={int(fg_tasks_batches)} fg_tasks_total={int(fg_tasks_total)} "
        f"fg_tasks_avg={fg_tasks_avg:.1f} fg_tasks_max={int(fg_tasks_max)} fg_tasks_hist=[{fg_tasks_hist}]"
    )


def fg_tasks_per_sec_log_message(
    *,
    req_type_exec_sec: Any,
    fg_tasks_total: int,
    request_type: GpuRequestType = GpuRequestType.SOLVE_FORCE_GREATS_FINDER,
) -> str | None:
    try:
        fg_exec = float(req_type_exec_sec.get(request_type, 0.0) or 0.0)
        fg_tasks_total_i = int(fg_tasks_total)
    except (ValueError, TypeError, AttributeError):
        return None
    if fg_exec <= 0.0 or fg_tasks_total_i <= 0:
        return None
    fg_tasks_per_s = float(fg_tasks_total_i) / float(fg_exec)
    return f"[GpuExecutor][FG] tasks_per_sec~={fg_tasks_per_s:.1f} (executor-wall) fg_exec={fg_exec:.2f}s"


def gpu_profiler_snapshot(
    *,
    enabled: bool,
    get_gpu_profiler_fn: Callable[[], Any] | None = None,
) -> tuple[float, float, float]:
    if not bool(enabled):
        return (0.0, 0.0, 0.0)
    try:
        if get_gpu_profiler_fn is None:
            from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

            get_gpu_profiler_fn = get_gpu_profiler
        summary = get_gpu_profiler_fn().summary()
        return (
            float(summary.get("total_kernel_sec", 0.0) or 0.0),
            float(summary.get("total_upload_sec", 0.0) or 0.0),
            float(summary.get("total_download_sec", 0.0) or 0.0),
        )
    except Exception as e:
        logger.debug(f"gpu_executor_profile:gpu_profiler_snapshot: {e}")
        return (0.0, 0.0, 0.0)


def _percentile95(values: Any) -> float:
    try:
        items = list(values or [])
    except (ValueError, TypeError, KeyError, AttributeError):
        items = []
    if not items:
        return 0.0
    data = sorted(float(value) for value in items)
    idx = int(round(0.95 * (len(data) - 1)))
    idx = max(0, min(idx, len(data) - 1))
    return float(data[idx])


def build_executor_idle_summary(
    *,
    idle_gaps: Any,
    loop_start_ts: float | None,
    first_work_ts: float | None,
    shutdown_ts: float | None,
    last_work_end_ts: float | None,
) -> ExecutorIdleSummary:
    try:
        gaps = [float(value) for value in list(idle_gaps or [])]
    except (ValueError, TypeError, AttributeError):
        gaps = []

    idle_total = float(sum(gaps))
    idle_max = float(max(gaps)) if gaps else 0.0
    idle_p95 = 0.0
    if gaps:
        gaps_sorted = sorted(gaps)
        idx = int(round(0.95 * (len(gaps_sorted) - 1)))
        idx = max(0, min(idx, len(gaps_sorted) - 1))
        idle_p95 = float(gaps_sorted[idx])

    idle_initial = 0.0
    if loop_start_ts is not None and first_work_ts is not None:
        try:
            idle_initial = float(max(0.0, float(first_work_ts) - float(loop_start_ts)))
        except (ValueError, TypeError):
            idle_initial = 0.0

    idle_tail = 0.0
    if shutdown_ts is not None and last_work_end_ts is not None:
        try:
            idle_tail = float(max(0.0, float(shutdown_ts) - float(last_work_end_ts)))
        except (ValueError, TypeError):
            idle_tail = 0.0

    return ExecutorIdleSummary(
        total_sec=float(idle_total),
        max_sec=float(idle_max),
        p95_sec=float(idle_p95),
        initial_sec=float(idle_initial),
        tail_sec=float(idle_tail),
    )


def build_request_latency_summary(
    *,
    lat_counts: Any,
    lat_total_sec: Any,
    lat_samples: Any,
    lat_queue_total_sec: Any,
    lat_queue_samples: Any,
    lat_in_exec_total_sec: Any,
    lat_in_exec_samples: Any,
    limit: int = 6,
) -> list[RequestLatencySummaryRow]:
    rows: list[RequestLatencySummaryRow] = []
    items = getattr(lat_counts, "items", lambda: [])()
    for req_type, count in items:
        try:
            n = int(count or 0)
        except (ValueError, TypeError):
            continue
        if n <= 0:
            continue
        try:
            total_avg = float(lat_total_sec.get(req_type, 0.0) or 0.0) / n
            queue_avg = float(lat_queue_total_sec.get(req_type, 0.0) or 0.0) / n
            in_exec_avg = float(lat_in_exec_total_sec.get(req_type, 0.0) or 0.0) / n
        except (ValueError, TypeError, AttributeError):
            continue
        rows.append(
            RequestLatencySummaryRow(
                request_type=req_type,
                count=int(n),
                total_avg_sec=float(total_avg),
                total_p95_sec=float(_percentile95(lat_samples.get(req_type) if hasattr(lat_samples, "get") else [])),
                queue_avg_sec=float(queue_avg),
                queue_p95_sec=float(
                    _percentile95(lat_queue_samples.get(req_type) if hasattr(lat_queue_samples, "get") else [])
                ),
                in_exec_avg_sec=float(in_exec_avg),
                in_exec_p95_sec=float(
                    _percentile95(lat_in_exec_samples.get(req_type) if hasattr(lat_in_exec_samples, "get") else [])
                ),
            )
        )
    rows.sort(key=lambda row: row.total_avg_sec, reverse=True)
    return rows[: max(0, int(limit))]


def record_request_latency_stats(
    latency: RequestLatencyWindow,
    *,
    lat_counts: Any,
    lat_total_sec: Any,
    lat_max_sec: Any,
    lat_samples: Any,
    lat_queue_total_sec: Any,
    lat_queue_max_sec: Any,
    lat_queue_samples: Any,
    lat_in_exec_total_sec: Any,
    lat_in_exec_max_sec: Any,
    lat_in_exec_samples: Any,
    sample_cap: int,
    randint_fn: Callable[[int, int], int] = random.randint,
) -> bool:
    req_type = latency.request_type
    total_sec = float(latency.total_sec)
    queue_sec = float(latency.queue_sec)
    in_exec_sec = float(latency.in_exec_sec)

    try:
        lat_counts[req_type] += 1
        n = int(lat_counts[req_type])
        lat_total_sec[req_type] += float(total_sec)
        if total_sec > float(lat_max_sec[req_type]):
            lat_max_sec[req_type] = float(total_sec)
        lat_queue_total_sec[req_type] += float(queue_sec)
        if queue_sec > float(lat_queue_max_sec[req_type]):
            lat_queue_max_sec[req_type] = float(queue_sec)
        lat_in_exec_total_sec[req_type] += float(in_exec_sec)
        if in_exec_sec > float(lat_in_exec_max_sec[req_type]):
            lat_in_exec_max_sec[req_type] = float(in_exec_sec)
    except (ValueError, TypeError, KeyError):
        return False

    try:
        cap = int(sample_cap)
    except (ValueError, TypeError):
        cap = 0
    if cap <= 0:
        return True

    try:
        total_samples = lat_samples[req_type]
        queue_samples = lat_queue_samples[req_type]
        in_exec_samples = lat_in_exec_samples[req_type]
        if len(total_samples) < cap:
            total_samples.append(float(total_sec))
            queue_samples.append(float(queue_sec))
            in_exec_samples.append(float(in_exec_sec))
        elif n > 0:
            j = randint_fn(0, n - 1)
            if j < cap:
                total_samples[j] = float(total_sec)
                queue_samples[j] = float(queue_sec)
                in_exec_samples[j] = float(in_exec_sec)
    except (ValueError, TypeError, IndexError, KeyError):
        return True
    return True


def build_idle_transition_summary(
    *,
    idle_transitions_sec: Any,
    idle_transitions_count: Any,
    limit: int = 6,
) -> list[IdleTransitionSummaryRow]:
    rows: list[IdleTransitionSummaryRow] = []
    items = getattr(idle_transitions_sec, "items", lambda: [])()
    for transition, sec in items:
        try:
            prev_t, next_t = transition
        except (TypeError, ValueError):
            continue
        try:
            sec_f = float(sec)
            count = int(idle_transitions_count.get((prev_t, next_t), 0) or 0)
        except (ValueError, TypeError, AttributeError):
            continue
        rows.append(
            IdleTransitionSummaryRow(
                previous_type=prev_t,
                next_type=next_t,
                sec=float(sec_f),
                count=int(count),
            )
        )
    rows.sort(key=lambda row: row.sec, reverse=True)
    return rows[: max(0, int(limit))]


def request_latency_summary_log_message(rows: list[RequestLatencySummaryRow]) -> str | None:
    parts = [row.format_log_part() for row in rows]
    if not parts:
        return None
    return "[GpuExecutor][LATENCY] " + "; ".join(parts)


def exec_breakdown_summary_log_message(rows: list[ExecBreakdownSummaryRow]) -> str | None:
    parts = [row.format_log_part() for row in rows]
    if not parts:
        return None
    return "[GpuExecutor][BREAKDOWN] " + "; ".join(parts)


def idle_transition_summary_log_message(rows: list[IdleTransitionSummaryRow]) -> str | None:
    parts = [row.format_log_part() for row in rows]
    if not parts:
        return None
    return "[GpuExecutor][IDLE] transitions=[" + ", ".join(parts) + "]"


def build_exec_breakdown_summary(
    *,
    req_type_exec_sec: Any,
    req_type_host_sec: Any,
    req_type_gpu_kernel_sec: Any,
    req_type_gpu_upload_sec: Any,
    req_type_gpu_download_sec: Any,
    limit: int = 6,
) -> list[ExecBreakdownSummaryRow]:
    rows: list[ExecBreakdownSummaryRow] = []
    items = getattr(req_type_exec_sec, "items", lambda: [])()
    for req_type, total_exec in items:
        try:
            exec_sec = float(total_exec)
        except (ValueError, TypeError):
            continue
        rows.append(
            ExecBreakdownSummaryRow(
                request_type=req_type,
                exec_sec=float(exec_sec),
                host_sec=float(req_type_host_sec.get(req_type, 0.0) or 0.0),
                gpu_kernel_sec=float(req_type_gpu_kernel_sec.get(req_type, 0.0) or 0.0),
                gpu_upload_sec=float(req_type_gpu_upload_sec.get(req_type, 0.0) or 0.0),
                gpu_download_sec=float(req_type_gpu_download_sec.get(req_type, 0.0) or 0.0),
            )
        )
    rows.sort(key=lambda row: row.exec_sec, reverse=True)
    return rows[: max(0, int(limit))]


def compute_exec_breakdown(
    *,
    exec_wall_sec: float,
    prof_before: tuple[float, float, float] | None,
    prof_after: tuple[float, float, float] | None,
) -> GpuExecBreakdown | None:
    try:
        wall = max(0.0, float(exec_wall_sec))
    except (ValueError, TypeError):
        return None
    if wall <= 0.0:
        return None

    kernel = 0.0
    upload = 0.0
    download = 0.0
    if prof_before is not None and prof_after is not None:
        try:
            kernel = max(0.0, float(prof_after[0]) - float(prof_before[0]))
            upload = max(0.0, float(prof_after[1]) - float(prof_before[1]))
            download = max(0.0, float(prof_after[2]) - float(prof_before[2]))
        except (ValueError, TypeError, IndexError):
            kernel = 0.0
            upload = 0.0
            download = 0.0

    gpu_total = max(0.0, kernel + upload + download)
    host = max(0.0, wall - gpu_total)
    return GpuExecBreakdown(
        host_sec=float(host),
        gpu_kernel_sec=float(kernel),
        gpu_upload_sec=float(upload),
        gpu_download_sec=float(download),
    )


def record_exec_breakdown_stats(
    request_type: GpuRequestType,
    breakdown: GpuExecBreakdown,
    *,
    req_type_host_sec: Any,
    req_type_gpu_kernel_sec: Any,
    req_type_gpu_upload_sec: Any,
    req_type_gpu_download_sec: Any,
) -> bool:
    try:
        req_type_host_sec[request_type] += float(breakdown.host_sec)
        req_type_gpu_kernel_sec[request_type] += float(breakdown.gpu_kernel_sec)
        req_type_gpu_upload_sec[request_type] += float(breakdown.gpu_upload_sec)
        req_type_gpu_download_sec[request_type] += float(breakdown.gpu_download_sec)
        return True
    except (ValueError, TypeError, KeyError):
        return False


def compute_request_latency_window(
    request: Any,
    *,
    exec_start_ns: int,
    exec_end_ns: int,
) -> RequestLatencyWindow | None:
    try:
        request_type = request.request_type
    except AttributeError:
        return None
    try:
        submit_ns = int(getattr(request, "submit_perf_ns", 0) or 0)
        dequeue_ns = int(getattr(request, "dequeue_perf_ns", 0) or 0)
        exec_start_ns = int(exec_start_ns or 0)
        exec_end_ns = int(exec_end_ns or 0)
    except (ValueError, TypeError):
        return None
    if submit_ns <= 0 or exec_end_ns <= 0:
        return None
    if dequeue_ns <= 0:
        dequeue_ns = exec_start_ns
    if exec_start_ns < dequeue_ns:
        exec_start_ns = dequeue_ns
    if exec_end_ns < exec_start_ns:
        exec_end_ns = exec_start_ns

    queue_sec = max(0.0, float(dequeue_ns - submit_ns) / 1e9)
    in_exec_sec = max(0.0, float(exec_start_ns - dequeue_ns) / 1e9)
    total_sec = max(0.0, float(exec_end_ns - submit_ns) / 1e9)
    return RequestLatencyWindow(
        request_type=request_type,
        queue_sec=float(queue_sec),
        in_exec_sec=float(in_exec_sec),
        total_sec=float(total_sec),
    )


def build_executor_profile_stats(
    *,
    wait_sec: float,
    exec_sec: float,
    batches_observed: int,
    batch_size_sum: int,
    workload_events_emitted: int,
    last_batch_plan_mode: str,
    workload_units_samples: Any,
    workload_age_ms_samples: Any,
    req_type_counts: Any,
    req_type_host_sec: Any,
    req_type_gpu_kernel_sec: Any,
    req_type_gpu_upload_sec: Any,
    req_type_gpu_download_sec: Any,
) -> dict[str, Any]:
    wait_sec = float(wait_sec)
    exec_sec = float(exec_sec)
    total = wait_sec + exec_sec
    try:
        units_samples = list(workload_units_samples or [])
    except (ValueError, TypeError, AttributeError):
        units_samples = []
    try:
        age_samples = list(workload_age_ms_samples or [])
    except (ValueError, TypeError, AttributeError):
        age_samples = []

    return {
        "wait_sec": wait_sec,
        "exec_sec": exec_sec,
        "utilization_pct": (exec_sec / total * 100.0) if total > 0 else 0.0,
        "batches_observed": int(batches_observed),
        "avg_batch_size": (float(batch_size_sum) / float(batches_observed)) if int(batches_observed) else 0.0,
        "workload_events_emitted": int(workload_events_emitted),
        "last_batch_mode": str(last_batch_plan_mode),
        "avg_work_units": (float(sum(units_samples)) / float(len(units_samples))) if units_samples else 0.0,
        "avg_submit_age_ms": (float(sum(age_samples)) / float(len(age_samples))) if age_samples else 0.0,
        "exec_breakdown_sec_by_type": {
            str(req_type.value): {
                "host_sec": float(req_type_host_sec.get(req_type, 0.0) or 0.0),
                "gpu_kernel_sec": float(req_type_gpu_kernel_sec.get(req_type, 0.0) or 0.0),
                "gpu_upload_sec": float(req_type_gpu_upload_sec.get(req_type, 0.0) or 0.0),
                "gpu_download_sec": float(req_type_gpu_download_sec.get(req_type, 0.0) or 0.0),
            }
            for req_type in req_type_counts.keys()
        },
    }


def build_executor_stats(
    *,
    requests_processed: int,
    registered_workers: int,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out = {
        "requests_processed": int(requests_processed),
        "registered_workers": int(registered_workers),
    }
    if profile is not None:
        out["profile"] = dict(profile)
    return out
