from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from gear_optimizer.core.types import JsonDict


class GpuRequestType(Enum):
    """Types of GPU requests that can be submitted.

    The native GA run carries the fused GA->FG owner continuation (Slice 3): the GPU
    owner scores FG in the GA turn and returns {runs_payload, fg_owner_score}. There is
    no separate FG response-frontier batch request type anymore.
    """

    LOAD_REF_ARRAYS = "load_ref_arrays"
    GPU_NATIVE_GA_RUN = "gpu_native_ga_run"
    SHUTDOWN = "shutdown"


@dataclass
class GpuRequest:
    """A request to execute on the GPU executor."""

    request_type: GpuRequestType
    request_id: int
    worker_id: int
    payload: JsonDict
    # Perf timestamps (best-effort, optional). `perf_counter_ns()` is monotonic and comparable across processes.
    submit_perf_ns: int = 0
    dequeue_perf_ns: int = 0


@dataclass
class GpuResponse:
    """Response from GPU executor."""

    request_id: int
    success: bool
    result: Any = None
    error: Optional[str] = None


def build_shutdown_request() -> GpuRequest:
    return GpuRequest(
        request_type=GpuRequestType.SHUTDOWN,
        request_id=-1,
        worker_id=-1,
        payload={},
    )
