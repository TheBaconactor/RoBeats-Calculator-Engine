from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from gear_optimizer.core.types import JsonDict


class GpuRequestType(Enum):
    """Types of GPU requests that can be submitted."""

    SOLVE_GENOMES_FROM_REGISTRY = "solve_genomes_from_registry"
    LOAD_REF_ARRAYS = "load_ref_arrays"
    SOLVE_FORCE_GREATS_FINDER = "solve_force_greats_finder_gpu"
    GPU_NATIVE_GA_RUN = "gpu_native_ga_run"
    FG_RESET_GLOBAL_BEST = "fg_reset_global_best"
    FG_DOWNLOAD_GLOBAL_BEST = "fg_download_global_best"
    FG_SELECT_SIGNATURE_FRONTIER_BATCH = "fg_select_signature_frontier_batch"
    FG_COMPUTE_BREAKPOINTS = "fg_compute_breakpoints"
    FG_SOLVE_WITH_BREAKPOINTS = "fg_solve_with_breakpoints"
    FG_SOLVE_WITH_BREAKPOINTS_BATCH = "fg_solve_with_breakpoints_batch"
    GA_FG_FUSED_SOLVE_WITH_BREAKPOINTS = "ga_fg_fused_solve_with_breakpoints"
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
