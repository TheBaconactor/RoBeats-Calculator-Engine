"""Resource shutdown for the native in-flight optimizer."""

from __future__ import annotations

import logging
from collections.abc import Callable

from gear_optimizer.solver.native_inflight_config import inflight_shutdown_debug_enabled

logger = logging.getLogger(__name__)


def _shutdown_step(label: str, action: Callable[[], None], *, shutdown_debug: bool) -> None:
    try:
        if shutdown_debug:
            logger.debug("[InFlight][SHUTDOWN] %s", label)
        action()
    except Exception as e:
        logger.debug(f"native_inflight_shutdown:_shutdown_step: {e}")


def shutdown_native_inflight_resources(
    *,
    fg_pipeline,
    decode_queue,
    db_persistence,
    cpu_prewarm_queue,
    prep_queue,
    post_sender,
    gpu_client,
    gpu_executor,
) -> None:
    """Shutdown native in-flight resources in dependency order."""
    shutdown_debug = inflight_shutdown_debug_enabled()
    _shutdown_step(
        "fg_executor.shutdown",
        lambda: fg_pipeline.shutdown_fg(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    _shutdown_step(
        "decode_executor.shutdown",
        lambda: decode_queue.shutdown(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    _shutdown_step(
        "db_prefetch_executor.shutdown",
        lambda: db_persistence.shutdown_prefetch(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    _shutdown_step(
        "fg_prep_executor.shutdown",
        lambda: fg_pipeline.shutdown_prep(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    _shutdown_step(
        "cpu_prewarm_executor.shutdown",
        lambda: cpu_prewarm_queue.shutdown(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    _shutdown_step(
        "prep_executor.shutdown",
        lambda: prep_queue.shutdown(wait=True, cancel_futures=True),
        shutdown_debug=shutdown_debug,
    )
    if post_sender is not None:
        _shutdown_step("post_sender.close", lambda: post_sender.close(timeout=10.0), shutdown_debug=shutdown_debug)
    _shutdown_step("gpu_client.close", lambda: gpu_client.close(timeout=2.0), shutdown_debug=shutdown_debug)

    def _stop_gpu_executor_if_running() -> None:
        if gpu_executor.is_running:
            gpu_executor.stop()

    _shutdown_step("gpu_executor.stop", _stop_gpu_executor_if_running, shutdown_debug=shutdown_debug)
