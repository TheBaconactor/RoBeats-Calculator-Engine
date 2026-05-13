"""GPU startup for the native in-flight optimizer."""

from __future__ import annotations

import logging
from typing import Any, Callable

from gear_optimizer.solver.gpu_executor import get_gpu_executor
from gear_optimizer.solver.gpu_service import GpuServiceClient

logger = logging.getLogger(__name__)

ProgressCallback = Callable[..., Any]


def _emit_startup_status(progress_cb: ProgressCallback | None, status: str) -> None:
    if progress_cb is None:
        return
    try:
        progress_cb(completed_delta=0, failed_delta=0, record_info={"status": status})
    except Exception as e:
        logger.debug(f"native_inflight_gpu_startup:_emit_startup_status: {e}")


def start_native_inflight_gpu_client(icfg, *, progress_cb: ProgressCallback | None = None):
    """Start the native GPU executor and return its service client."""
    gpu_executor = get_gpu_executor()
    _emit_startup_status(progress_cb, "GPU init (Taichi/Vulkan)")
    gpu_executor.start(in_process=True)

    # GPU readiness includes Taichi/Vulkan init plus the configured GA/FG warmups. On cold
    # Windows/Vulkan caches, that warmup can be minute-scale; do not let work queue behind an
    # owner that is not accepting requests yet.
    init_timeout = float(icfg.runtime.gpu_executor_init_timeout_sec)
    if not gpu_executor.wait_until_ready(timeout=init_timeout):
        err = getattr(gpu_executor, "last_init_error", None)
        msg = "[InFlight] GPU executor Taichi init failed or timed out"
        if err:
            msg = f"{msg} ({err})"
        try:
            gpu_executor.stop()
        except Exception as e:
            logger.debug(f"native_inflight_gpu_startup:start_native_inflight_gpu_client: {e}")
        raise RuntimeError(msg)

    _emit_startup_status(progress_cb, "GPU warmup (Taichi JIT)")
    gpu_client = GpuServiceClient(gpu_executor)
    gpu_client.start(start_executor=False)
    return gpu_executor, gpu_client
