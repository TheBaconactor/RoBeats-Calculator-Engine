from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from gear_optimizer.core.parsing import env_get
from gear_optimizer.solver.gpu_executor_types import GpuRequest


@dataclass(frozen=True)
class NativeGaBatchLimits:
    max_reqs: int
    max_work_units: float


def load_native_ga_batch_limits(
    *,
    env_get_fn: Callable[[str, Any], Any] = env_get,
) -> NativeGaBatchLimits:
    try:
        max_reqs = int(env_get_fn("GPU_NATIVE_GA_BATCH_COALESCE_MAX_REQS", "1") or "1")
    except (ValueError, TypeError):
        max_reqs = 1
    max_reqs = max(1, min(int(max_reqs), 128))

    try:
        max_work_units = float(env_get_fn("GPU_NATIVE_GA_BATCH_COALESCE_MAX_WORK_UNITS", "720000") or "720000")
    except (ValueError, TypeError):
        max_work_units = 720000.0
    if max_work_units <= 0.0:
        max_work_units = float("inf")

    return NativeGaBatchLimits(max_reqs=int(max_reqs), max_work_units=float(max_work_units))


def plan_native_ga_batch_chunks(
    requests: list[GpuRequest],
    *,
    limits: NativeGaBatchLimits,
    estimate_work_units_fn: Callable[[GpuRequest], float],
) -> list[list[GpuRequest]]:
    chunks: list[list[GpuRequest]] = []
    chunk: list[GpuRequest] = []
    chunk_units = 0.0

    for req in requests:
        req_units = max(1.0, float(estimate_work_units_fn(req)))
        if chunk and (
            len(chunk) >= int(limits.max_reqs)
            or (float(chunk_units) + float(req_units)) > float(limits.max_work_units)
        ):
            chunks.append(chunk)
            chunk = []
            chunk_units = 0.0
        chunk.append(req)
        chunk_units += float(req_units)

    if chunk:
        chunks.append(chunk)
    return chunks
