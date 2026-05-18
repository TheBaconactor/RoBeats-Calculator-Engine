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

# ---- merged from gpu_executor_trace.py ----
from pathlib import Path
from time import perf_counter
import time

from gear_optimizer.core.profile_events import emit_profile_event


TRACE_HEADER = (
    "wall_ts,rel_ts,event,wait_sec,exec_sec,batch_size,types,in_process,"
    "planner_mode,queue_depth_hint,pressure_hint,work_units,dominant_type,"
    "dominant_share_pct,diversity_pct,avg_submit_age_ms\n"
)


class ExecutorTraceWriter:
    def __init__(self) -> None:
        self._fp = None
        self._start_perf: float | None = None
        self._start_wall: float | None = None

    @property
    def has_file(self) -> bool:
        return self._fp is not None

    def open(self, trace_path: str) -> None:
        self.close()
        self._start_perf = None
        self._start_wall = None
        path_text = str(trace_path or "").strip()
        if not path_text:
            return
        try:
            path = Path(path_text)
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fp = open(path, "a", encoding="utf-8", buffering=1)
            if self._fp.tell() == 0:
                self._fp.write(TRACE_HEADER)
        except (OSError, ValueError):
            self._fp = None

    def close(self) -> None:
        fp = self._fp
        if fp is not None:
            try:
                fp.close()
            except Exception:
                pass
        self._fp = None

    def write_event(
        self,
        *,
        event: str,
        in_process: bool,
        wait_sec: float = 0.0,
        exec_sec: float = 0.0,
        batch_size: int = 0,
        types: str = "",
        planner_mode: str = "",
        queue_depth_hint: int = -1,
        pressure_hint: float = 0.0,
        work_units: float = 0.0,
        dominant_type: str = "",
        dominant_share_pct: float = 0.0,
        diversity_pct: float = 0.0,
        avg_submit_age_ms: float = 0.0,
    ) -> None:
        if self._start_perf is None:
            self._start_perf = perf_counter()
        if self._start_wall is None:
            self._start_wall = time.time()
        rel_ts = perf_counter() - float(self._start_perf)
        wall_ts = time.time()
        try:
            if self._fp is not None:
                self._fp.write(
                    f"{wall_ts:.6f},{rel_ts:.6f},{event},{float(wait_sec):.6f},{float(exec_sec):.6f},"
                    f"{int(batch_size)},{types},{int(bool(in_process))},{str(planner_mode)},"
                    f"{int(queue_depth_hint)},{float(pressure_hint):.3f},{float(work_units):.3f},"
                    f"{str(dominant_type)},{float(dominant_share_pct):.2f},{float(diversity_pct):.2f},"
                    f"{float(avg_submit_age_ms):.3f}\n"
                )
        except (OSError, ValueError):
            pass
        emit_profile_event(
            component="gpu_executor",
            event=f"trace::{str(event or '').strip().lower()}",
            metrics={
                "rel_ts": float(rel_ts),
                "wait_sec": float(wait_sec),
                "exec_sec": float(exec_sec),
                "batch_size": int(batch_size),
                "types": str(types or ""),
                "in_process": int(bool(in_process)),
                "planner_mode": str(planner_mode or ""),
                "queue_depth_hint": int(queue_depth_hint),
                "pressure_hint": float(pressure_hint),
                "work_units": float(work_units),
                "dominant_type": str(dominant_type or ""),
                "dominant_share_pct": float(dominant_share_pct),
                "diversity_pct": float(diversity_pct),
                "avg_submit_age_ms": float(avg_submit_age_ms),
            },
            ts_wall=float(wall_ts),
        )

# ---- merged from gpu_executor_workload.py ----
import math
from collections import defaultdict
from dataclasses import dataclass

from gear_optimizer.solver.gpu_executor_batching import COALESCABLE_REQUEST_TYPES, FG_REQUEST_TYPES
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


@dataclass(frozen=True)
class WorkloadProfileSettings:
    enabled: bool
    interval_sec: float


@dataclass(frozen=True)
class WorkloadWindowEmitResult:
    last_emit_ts: float | None
    events_emitted: int


def load_workload_profile_settings(
    *,
    profile_enabled: bool,
    env_flag_fn: Callable[[str, str], bool],
    env_get_fn: Callable[[str, str], Any],
) -> WorkloadProfileSettings:
    workload_enabled = bool(profile_enabled or env_flag_fn("GPU_EXECUTOR_WORKLOAD_PROFILE", "0"))
    try:
        interval_raw = float(str(env_get_fn("GPU_EXECUTOR_WORKLOAD_PROFILE_INTERVAL_SEC", "2.0") or "2.0").strip())
    except (ValueError, TypeError):
        interval_raw = 2.0
    return WorkloadProfileSettings(
        enabled=bool(workload_enabled),
        interval_sec=max(0.2, float(interval_raw)),
    )


def size_hint(value: Any) -> int:
    if value is None:
        return 0
    try:
        shape = getattr(value, "shape", None)
        if shape is not None and len(shape) > 0:
            return max(0, int(shape[0]))
    except (AttributeError, TypeError):
        pass
    try:
        return max(0, int(len(value)))
    except (ValueError, TypeError):
        return 0


def payload_dict(req: GpuRequest) -> dict[str, Any]:
    payload = getattr(req, "payload", None)
    return payload if isinstance(payload, dict) else {}


def percentile95(values: Any) -> float:
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


def estimate_request_work_units(request: GpuRequest, *, size_hint_fn: Callable[[Any], int] = size_hint) -> float:
    req_type = getattr(request, "request_type", None)
    payload = payload_dict(request)

    if req_type == GpuRequestType.SOLVE_GENOMES_FROM_REGISTRY:
        n = size_hint_fn(payload.get("population_indices"))
        return float(max(1, n))

    if req_type == GpuRequestType.GPU_NATIVE_GA_RUN:
        n_genomes = int(payload.get("n_genomes", 0) or 0)
        if n_genomes <= 0:
            n_genomes = size_hint_fn(payload.get("initial_populations"))
        n_generations = max(1, int(payload.get("n_generations", 1) or 1))
        runs = max(1, int(payload.get("num_runs", 1) or 1))
        return float(max(1, n_genomes) * n_generations * runs)

    if req_type == GpuRequestType.SOLVE_FORCE_GREATS_FINDER:
        kwargs = payload.get("kwargs")
        if not isinstance(kwargs, dict):
            return 1.0
        fg_tasks = kwargs.get("fg_tasks")
        if isinstance(fg_tasks, (list, tuple)) and fg_tasks:
            pair_total = 0
            for task in fg_tasks:
                if isinstance(task, dict):
                    pair_total += max(1, size_hint_fn(task.get("ftff_pairs")))
            n_genomes = int(kwargs.get("n_genomes_override", 0) or 0)
            if n_genomes <= 0:
                args = payload.get("args")
                if isinstance(args, (list, tuple)) and args:
                    n_genomes = size_hint_fn(args[0])
            n_genomes = max(1, n_genomes)
            return float(max(1, pair_total) * n_genomes)
        ftff_chunks = kwargs.get("ftff_chunks")
        if isinstance(ftff_chunks, (list, tuple)) and ftff_chunks:
            return float(max(1, len(ftff_chunks)))
        return 1.0

    if req_type == GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS_BATCH:
        payloads = payload.get("payloads")
        if not isinstance(payloads, (list, tuple)):
            return 1.0
        pair_total = 0
        for item in payloads:
            if isinstance(item, dict):
                pair_total += max(1, size_hint_fn(item.get("ftff_pairs")))
            else:
                pair_total += 1
        return float(max(1, pair_total))

    if req_type in (GpuRequestType.FG_SOLVE_WITH_BREAKPOINTS, GpuRequestType.GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS):
        return float(max(1, size_hint_fn(payload.get("ftff_pairs"))))

    if req_type == GpuRequestType.LOAD_REF_ARRAYS:
        return 0.25

    if req_type == GpuRequestType.SHUTDOWN:
        return 0.0

    return 1.0


def _request_type_value(request_type: Any) -> str:
    try:
        return str(getattr(request_type, "value", request_type))
    except (AttributeError, TypeError):
        return ""


def summarize_batch(
    batch: list[GpuRequest],
    *,
    plan: Any,
    wait_sec: float,
    batch_id: int,
    estimate_work_units_fn: Callable[[GpuRequest], float] = estimate_request_work_units,
    coalescable_request_types: frozenset[GpuRequestType] = COALESCABLE_REQUEST_TYPES,
    fg_request_types: frozenset[GpuRequestType] = FG_REQUEST_TYPES,
) -> dict[str, Any]:
    non_shutdown = [req for req in (batch or []) if req.request_type != GpuRequestType.SHUTDOWN]
    by_type = defaultdict(int)
    coalescable_count = 0
    fg_count = 0
    units_total = 0.0
    age_ms: list[float] = []

    for req in non_shutdown:
        rt = req.request_type
        by_type[rt] += 1
        if rt in coalescable_request_types:
            coalescable_count += 1
        if rt in fg_request_types:
            fg_count += 1
        units_total += float(estimate_work_units_fn(req))

        try:
            submit_ns = int(getattr(req, "submit_perf_ns", 0) or 0)
            dequeue_ns = int(getattr(req, "dequeue_perf_ns", 0) or 0)
            if submit_ns > 0 and dequeue_ns > submit_ns:
                age_ms.append(max(0.0, float(dequeue_ns - submit_ns) / 1e6))
        except (ValueError, TypeError, AttributeError):
            continue

    total = int(len(non_shutdown))
    distinct = int(len(by_type))
    dominant_type = ""
    dominant_count = 0
    if by_type:
        dominant_rt, dominant_count = max(by_type.items(), key=lambda kv: kv[1])
        dominant_type = _request_type_value(dominant_rt)

    dominant_share_pct = (float(dominant_count) / float(total) * 100.0) if total > 0 else 0.0
    diversity_pct = 0.0
    if total > 0 and distinct > 1:
        entropy = 0.0
        for count in by_type.values():
            p = float(count) / float(total)
            if p > 0.0:
                entropy -= p * math.log(p, 2)
        max_entropy = math.log(float(distinct), 2)
        if max_entropy > 0.0:
            diversity_pct = float(entropy / max_entropy * 100.0)

    oldest_age_ms = float(max(age_ms)) if age_ms else 0.0
    avg_age_ms = (float(sum(age_ms)) / float(len(age_ms))) if age_ms else 0.0

    type_compact = ";".join(
        f"{_request_type_value(rt)}:{int(n)}" for rt, n in sorted(by_type.items(), key=lambda kv: _request_type_value(kv[0]))
    )
    return {
        "batch_id": int(batch_id),
        "mode": str(plan.mode),
        "wait_ms": float(max(0.0, float(wait_sec) * 1000.0)),
        "batch_wait_ms_target": int(plan.wait_ms),
        "batch_max_target": int(plan.max_batch),
        "queue_depth_hint": int(plan.queue_depth_hint),
        "pressure_hint": float(plan.pressure_hint),
        "size": int(total),
        "distinct_types": int(distinct),
        "coalescable_count": int(coalescable_count),
        "fg_count": int(fg_count),
        "dominant_type": str(dominant_type),
        "dominant_share_pct": float(dominant_share_pct),
        "diversity_pct": float(diversity_pct),
        "work_units": float(max(0.0, units_total)),
        "avg_work_units_per_req": (float(units_total) / float(total)) if total > 0 else 0.0,
        "oldest_submit_age_ms": float(oldest_age_ms),
        "avg_submit_age_ms": float(avg_age_ms),
        "types": str(type_compact),
    }


def should_emit_workload_batch_event(metrics: dict[str, Any]) -> bool:
    batch_id = int(metrics.get("batch_id", 0) or 0)
    pressure = float(metrics.get("pressure_hint", 0.0) or 0.0)
    mode = str(metrics.get("mode") or "")
    return batch_id <= 12 or (batch_id % 64 == 0) or pressure >= 1.0 or mode in {"fg_recovery", "throughput"}


def workload_batch_event_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "batch_id": int(metrics.get("batch_id", 0) or 0),
        "mode": str(metrics.get("mode") or ""),
        "size": int(metrics.get("size", 0) or 0),
        "types": str(metrics.get("types", "")),
        "dominant_type": str(metrics.get("dominant_type", "")),
        "dominant_share_pct": float(metrics.get("dominant_share_pct", 0.0) or 0.0),
        "diversity_pct": float(metrics.get("diversity_pct", 0.0) or 0.0),
        "work_units": float(metrics.get("work_units", 0.0) or 0.0),
        "queue_depth_hint": int(metrics.get("queue_depth_hint", -1) or -1),
        "avg_submit_age_ms": float(metrics.get("avg_submit_age_ms", 0.0) or 0.0),
        "wait_ms": float(metrics.get("wait_ms", 0.0) or 0.0),
        "exec_ms": float(metrics.get("exec_sec", 0.0) or 0.0) * 1000.0,
    }


def emit_workload_batch_profile(metrics: dict[str, Any], *, emit_profile_event_fn: Callable[..., None]) -> bool:
    if not should_emit_workload_batch_event(metrics):
        return False
    emit_profile_event_fn(
        component="gpu_executor",
        event="workload::batch",
        metrics=workload_batch_event_metrics(metrics),
    )
    return True


def batch_trace_context(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "planner_mode": str(metrics.get("mode", "")),
        "queue_depth_hint": int(metrics.get("queue_depth_hint", -1)),
        "pressure_hint": float(metrics.get("pressure_hint", 0.0)),
        "work_units": float(metrics.get("work_units", 0.0)),
        "dominant_type": str(metrics.get("dominant_type", "")),
        "dominant_share_pct": float(metrics.get("dominant_share_pct", 0.0)),
        "diversity_pct": float(metrics.get("diversity_pct", 0.0)),
        "avg_submit_age_ms": float(metrics.get("avg_submit_age_ms", 0.0)),
    }


def record_workload_batch_state(
    metrics: dict[str, Any],
    *,
    recent_batches: Any,
    mode_counts: Any,
    mode_wait_sec: Any,
    mode_exec_sec: Any,
    queue_depth_samples: Any,
    age_ms_samples: Any,
    units_samples: Any,
    diversity_samples: Any,
    pressure_samples: Any,
    last_batch_plan_mode: str,
) -> str:
    if not metrics:
        return str(last_batch_plan_mode)

    mode = str(metrics.get("mode") or "unknown")
    recent_batches.append(dict(metrics))
    mode_counts[mode] += 1
    mode_wait_sec[mode] += float(metrics.get("wait_ms", 0.0) or 0.0) / 1000.0
    mode_exec_sec[mode] += float(metrics.get("exec_sec", 0.0) or 0.0)
    queue_depth_samples.append(float(metrics.get("queue_depth_hint", 0.0) or 0.0))
    age_ms_samples.append(float(metrics.get("avg_submit_age_ms", 0.0) or 0.0))
    units_samples.append(float(metrics.get("work_units", 0.0) or 0.0))
    diversity_samples.append(float(metrics.get("diversity_pct", 0.0) or 0.0))
    pressure_samples.append(float(metrics.get("pressure_hint", 0.0) or 0.0))
    return str(metrics.get("mode") or last_batch_plan_mode)


def workload_window_event_metrics(window: list[dict[str, Any]]) -> dict[str, Any]:
    if not window:
        return {}

    n = float(len(window))
    total_wait = float(sum(float(item.get("wait_ms", 0.0) or 0.0) for item in window))
    total_exec_ms = float(sum(float(item.get("exec_sec", 0.0) or 0.0) for item in window) * 1000.0)
    total = total_wait + total_exec_ms
    busy_pct = (total_exec_ms / total * 100.0) if total > 0 else 0.0
    avg_batch = float(sum(float(item.get("size", 0.0) or 0.0) for item in window) / n)
    avg_units = float(sum(float(item.get("work_units", 0.0) or 0.0) for item in window) / n)
    avg_diversity = float(sum(float(item.get("diversity_pct", 0.0) or 0.0) for item in window) / n)
    avg_qdepth = float(sum(float(item.get("queue_depth_hint", 0.0) or 0.0) for item in window) / n)
    size_total = sum(float(item.get("size", 0.0) or 0.0) for item in window)
    fg_share = float(sum(float(item.get("fg_count", 0.0) or 0.0) for item in window) / max(1.0, size_total) * 100.0)

    mode_counts = defaultdict(int)
    for item in window:
        mode_counts[str(item.get("mode") or "unknown")] += 1
    top_modes = sorted(mode_counts.items(), key=lambda kv: kv[1], reverse=True)[:3]
    mode_str = ",".join(f"{key}:{int(value)}" for key, value in top_modes)

    return {
        "batches": int(len(window)),
        "busy_pct": float(busy_pct),
        "avg_batch": float(avg_batch),
        "avg_work_units": float(avg_units),
        "avg_diversity_pct": float(avg_diversity),
        "avg_queue_depth_hint": float(avg_qdepth),
        "fg_share_pct": float(fg_share),
        "mode_top": str(mode_str),
    }


def workload_window_log_message(metrics: dict[str, Any]) -> str:
    return (
        "[GpuExecutor][WORKLOAD] "
        f"window_batches={int(metrics.get('batches', 0) or 0)} "
        f"busy={float(metrics.get('busy_pct', 0.0) or 0.0):.1f}% "
        f"avg_batch={float(metrics.get('avg_batch', 0.0) or 0.0):.2f} "
        f"avg_units={float(metrics.get('avg_work_units', 0.0) or 0.0):.1f} "
        f"fg_share={float(metrics.get('fg_share_pct', 0.0) or 0.0):.1f}% "
        f"qdepth~={float(metrics.get('avg_queue_depth_hint', 0.0) or 0.0):.1f} "
        f"diversity={float(metrics.get('avg_diversity_pct', 0.0) or 0.0):.1f}% "
        f"modes=[{str(metrics.get('mode_top', ''))}]"
    )


def emit_workload_window_profile(
    window: list[dict[str, Any]],
    *,
    log_enabled: bool,
    log_debug: Callable[[str], None],
    emit_profile_event_fn: Callable[..., None],
) -> bool:
    metrics = workload_window_event_metrics(window)
    if not metrics:
        return False

    emit_profile_event_fn(
        component="gpu_executor",
        event="workload::window",
        metrics=metrics,
    )
    if log_enabled:
        log_debug(workload_window_log_message(metrics))
    return True


def maybe_emit_workload_window_profile(
    *,
    enabled: bool,
    force: bool,
    now: float,
    last_emit_ts: float | None,
    interval_sec: float,
    recent_batches: Any,
    events_emitted: int,
    log_enabled: bool,
    log_debug: Callable[[str], None],
    emit_profile_event_fn: Callable[..., None],
) -> WorkloadWindowEmitResult:
    if not enabled:
        return WorkloadWindowEmitResult(last_emit_ts=last_emit_ts, events_emitted=int(events_emitted))

    if not force:
        if last_emit_ts is None:
            return WorkloadWindowEmitResult(last_emit_ts=float(now), events_emitted=int(events_emitted))
        if (float(now) - float(last_emit_ts)) < float(interval_sec):
            return WorkloadWindowEmitResult(last_emit_ts=last_emit_ts, events_emitted=int(events_emitted))

    window = list(recent_batches)
    if not window:
        return WorkloadWindowEmitResult(last_emit_ts=float(now), events_emitted=int(events_emitted))

    emitted = emit_workload_window_profile(
        window,
        log_enabled=bool(log_enabled),
        log_debug=log_debug,
        emit_profile_event_fn=emit_profile_event_fn,
    )
    next_events_emitted = int(events_emitted) + (1 if emitted else 0)
    return WorkloadWindowEmitResult(last_emit_ts=float(now), events_emitted=int(next_events_emitted))


def workload_stop_summary_metrics(
    window: list[dict[str, Any]],
    *,
    age_ms_samples: Any,
    units_samples: Any,
    diversity_samples: Any,
    queue_depth_samples: Any,
    mode_counts: Any,
    events_emitted: int,
    last_mode: str,
) -> dict[str, Any]:
    if not window:
        return {}

    n = float(len(window))
    avg_units = float(sum(float(item.get("work_units", 0.0) or 0.0) for item in window) / n)
    avg_diversity = float(sum(float(item.get("diversity_pct", 0.0) or 0.0) for item in window) / n)
    avg_qdepth = float(sum(float(item.get("queue_depth_hint", 0.0) or 0.0) for item in window) / n)
    avg_age_ms = float(sum(float(item.get("avg_submit_age_ms", 0.0) or 0.0) for item in window) / n)

    mode_items = getattr(mode_counts, "items", lambda: [])()
    mode_top = sorted(mode_items, key=lambda kv: kv[1], reverse=True)[:5]
    mode_str = ", ".join(f"{name}:{int(count)}" for name, count in mode_top)

    return {
        "batches": int(len(window)),
        "avg_work_units": float(avg_units),
        "p95_work_units": float(percentile95(units_samples)),
        "avg_diversity_pct": float(avg_diversity),
        "p95_diversity_pct": float(percentile95(diversity_samples)),
        "avg_queue_depth_hint": float(avg_qdepth),
        "p95_queue_depth_hint": float(percentile95(queue_depth_samples)),
        "avg_submit_age_ms": float(avg_age_ms),
        "p95_submit_age_ms": float(percentile95(age_ms_samples)),
        "events_emitted": int(events_emitted),
        "last_mode": str(last_mode),
        "mode_top": str(mode_str),
    }


def workload_stop_summary_log_message(metrics: dict[str, Any]) -> str:
    return (
        "[GpuExecutor][WORKLOAD][SUMMARY] "
        f"batches={int(metrics.get('batches', 0) or 0)} "
        f"avg_units={float(metrics.get('avg_work_units', 0.0) or 0.0):.1f} "
        f"p95_units={float(metrics.get('p95_work_units', 0.0) or 0.0):.1f} "
        f"avg_diversity={float(metrics.get('avg_diversity_pct', 0.0) or 0.0):.1f}% "
        f"p95_diversity={float(metrics.get('p95_diversity_pct', 0.0) or 0.0):.1f}% "
        f"avg_qdepth={float(metrics.get('avg_queue_depth_hint', 0.0) or 0.0):.1f} "
        f"p95_qdepth={float(metrics.get('p95_queue_depth_hint', 0.0) or 0.0):.1f} "
        f"avg_submit_age={float(metrics.get('avg_submit_age_ms', 0.0) or 0.0):.2f}ms "
        f"p95_submit_age={float(metrics.get('p95_submit_age_ms', 0.0) or 0.0):.2f}ms "
        f"events={int(metrics.get('events_emitted', 0) or 0)} modes=[{str(metrics.get('mode_top', ''))}]"
    )


def workload_stop_summary_event_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metrics.items() if key != "mode_top"}


def emit_workload_stop_summary(
    window: list[dict[str, Any]],
    *,
    age_ms_samples: Any,
    units_samples: Any,
    diversity_samples: Any,
    queue_depth_samples: Any,
    mode_counts: Any,
    events_emitted: int,
    last_mode: str,
    log_debug: Callable[[str], None],
    emit_profile_event_fn: Callable[..., None],
) -> bool:
    metrics = workload_stop_summary_metrics(
        window,
        age_ms_samples=age_ms_samples,
        units_samples=units_samples,
        diversity_samples=diversity_samples,
        queue_depth_samples=queue_depth_samples,
        mode_counts=mode_counts,
        events_emitted=int(events_emitted),
        last_mode=str(last_mode),
    )
    if not metrics:
        return False

    log_debug(workload_stop_summary_log_message(metrics))
    emit_profile_event_fn(
        component="gpu_executor",
        event="workload::summary",
        metrics=workload_stop_summary_event_metrics(metrics),
    )
    return True
