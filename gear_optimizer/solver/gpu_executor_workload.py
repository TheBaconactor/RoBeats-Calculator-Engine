from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor_request_policy import COALESCABLE_REQUEST_TYPES, FG_REQUEST_TYPES
from gear_optimizer.solver.gpu_executor_types import GpuRequest, GpuRequestType


@dataclass(frozen=True)
class WorkloadProfileSettings:
    enabled: bool
    interval_sec: float


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

    if req_type in (GpuRequestType.LOAD_REF_ARRAYS, GpuRequestType.PRECOMPUTE_TIMELINE):
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
