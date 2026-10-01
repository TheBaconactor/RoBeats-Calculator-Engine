"""The process's GPU owner: one thread initializes Taichi (its Vulkan runtime belongs to that thread), warms the GA and
FG kernels, then runs the calls submitted to it, one at a time, in order.

    executor = get_gpu_executor()
    executor.start()                            # returns at once; the owner thread initializes in the background
    result = executor.call(fn, *args)           # fn(*args) on the owner thread, once the init is done
    executor.stop()                             # finalizes Taichi on the owner thread (persists the offline cache)

Under the :8765 service a call still running after _CALL_TIMEOUT_S means a stuck GPU: it raises GpuServiceTimeoutError
and the process stops itself (the service then fails the solve). Standalone runs wait.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import queue
import signal
import threading
import time
from collections.abc import Callable
from typing import Any

from gear_optimizer import settings
from gear_optimizer.solver.windows_timer import acquire_windows_timer_period_1ms, release_windows_timer_period_1ms

logger = logging.getLogger(__name__)

# Taichi init + the kernel warmup (cold: compiling every kernel).
_INIT_TIMEOUT_S = 600.0
_CALL_TIMEOUT_S = 240.0
_STOP = None


class GpuFatalError(RuntimeError):
    """The GPU can no longer serve this process (a hung call, a failed Taichi init); a service-mode run stops."""


class GpuServiceTimeoutError(GpuFatalError):
    """A call on the GPU owner thread exceeded the service-mode watchdog."""


# GPU driver errors (raised through Taichi) that mean the device is gone; only their messages say so.
_FATAL_DRIVER_MARKERS = (
    "device lost",
    "device removed",
    "device hung",
    "dxgi_error_device_hung",
    "dxgi_error_device_removed",
    "cudaerrorlaunchtimeout",
    "watchdog timeout",
    "tdr",
    "waituntilcompleted",
    "metaldevice::wait_idle",
)


def is_fatal_gpu_error(exc: BaseException) -> bool:
    """Whether `exc`, or an exception it was raised from, means this process can no longer use its GPU: the engine's
    own GpuFatalError or a driver's device loss."""
    seen: set[int] = set()
    pending: list[BaseException | None] = [exc]
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, GpuFatalError):
            return True
        if any(marker in f"{type(current).__name__}: {current}".lower() for marker in _FATAL_DRIVER_MARKERS):
            return True
        pending += [current.__cause__, current.__context__]
    return False


def is_stop_abort_exception(exc: BaseException) -> bool:
    """Whether `exc` is a GPU call stopped or refused by request_abort ("GpuExecutor aborted: <reason>")."""
    return "GpuExecutor aborted:" in str(exc)


def _stop_this_process(message: str) -> None:
    """SIGTERM this process shortly, after the caller has raised (a stuck GPU call cannot be interrupted)."""

    def stop() -> None:
        print(f"[GpuService] Fatal request timeout: {message}")
        time.sleep(0.1)
        try:
            os.kill(os.getpid(), signal.SIGTERM)
        except OSError:
            os._exit(124)

    threading.Thread(target=stop, name="GpuTimeoutStop", daemon=True).start()


def _init_gpu() -> None:
    """Taichi init + the FG and GA kernel warmups, on the owner thread."""
    # Import order matters: nothing that allocates Taichi fields is imported before init_taichi.
    from .taichi_gem import runtime as ti_runtime

    ti_runtime.init_taichi()
    # The FG group-row builder's warm flag is not thread-safe: warmed here, no other thread dispatches first.
    from .taichi_gem.force_greats.response_frontier import warmup_response_frontier_group_builder

    warmup_response_frontier_group_builder()
    from .taichi_gem.api import ga_operations as ga_ops

    with ti_runtime.offline_cache_lock(timeout_sec=None):
        from .taichi_gem.force_greats import fields as fg_fields

        fg_fields.ensure_ready_with_warmup()
        ga_ops.warmup_ga_kernels_light()


def _finalize_gpu() -> None:
    """Taichi finalized on the owner thread, with the Vulkan runtime fully alive: left to interpreter exit, the offline
    kernel cache dump races daemon-thread teardown and truncates (observed: 1-9 of ~40 kernels persisted per run)."""
    try:
        from .taichi_gem.api.initialization import hard_reset_taichi

        hard_reset_taichi(reason="executor shutdown (persist offline kernel cache)")
    except Exception as exc:
        logger.warning("[GpuExecutor] Taichi shutdown finalize failed (offline cache may be stale): %s", exc)


class GpuExecutor:
    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._calls: queue.SimpleQueue = queue.SimpleQueue()
        self._ready = threading.Event()
        self._init_error: str | None = None
        self._abort = threading.Event()
        self._abort_reason = ""
        self._call_timeout_s: float | None = None
        self._timer_1ms = False

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the owner thread (it initializes Taichi and warms the kernels); a no-op until stop()."""
        if self._thread is not None:
            return
        self._calls = queue.SimpleQueue()
        self._ready.clear()
        self._init_error = None
        self._abort.clear()
        self._call_timeout_s = _CALL_TIMEOUT_S if settings.service_mode() else None
        # Windows: a thread waiting for the GIL (prep and finish threads beside the GA) waits 5 ms before asking for
        # it, which the default ~15.6 ms timer stretches.
        self._timer_1ms = acquire_windows_timer_period_1ms()
        self._thread = threading.Thread(target=self._run, name="GpuExecutorThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Abort the call in progress, then finalize Taichi on the owner thread (persists the offline kernel cache)."""
        if self._thread is None:
            return
        self.request_abort("shutdown")
        self._calls.put(_STOP)
        self._thread.join(timeout=10.0)
        if self._thread.is_alive():
            logger.warning("[GpuExecutor] Stop timed out; the owner thread is still alive.")
        self._thread = None
        if self._timer_1ms:
            release_windows_timer_period_1ms()
            self._timer_1ms = False

    def call(self, fn: Callable[..., Any], *args: Any) -> Any:
        """fn(*args) on the owner thread, once the GPU init is done: its result, or its exception. GpuFatalError if
        the init failed or timed out (the executor is stopped)."""
        if not self._ready.wait(_INIT_TIMEOUT_S) or self._init_error is not None:
            error = self._init_error
            self.stop()
            raise GpuFatalError(f"GPU executor Taichi init failed or timed out ({error})")
        future: concurrent.futures.Future = concurrent.futures.Future()
        self._calls.put((future, fn, args))
        done, _ = concurrent.futures.wait([future], timeout=self._call_timeout_s)
        if not done:
            message = f"GPU call {fn.__name__} timed out after {self._call_timeout_s:.1f}s"
            _stop_this_process(message)
            raise GpuServiceTimeoutError(message)
        return future.result()

    def request_abort(self, reason: str) -> None:
        """Abort the call in progress (the GA checks between its steps) and refuse queued calls until start()."""
        self._abort_reason = reason
        self._abort.set()

    def abort_requested(self) -> bool:
        return self._abort.is_set()

    def _run(self) -> None:
        try:
            _init_gpu()
        except Exception as exc:
            self._init_error = f"{type(exc).__name__}: {exc}"
            logger.exception("[GpuExecutor] GPU init failed")
            return
        finally:
            self._ready.set()
        while (item := self._calls.get()) is not _STOP:
            future, fn, args = item
            try:
                if self._abort.is_set():
                    raise RuntimeError(f"GpuExecutor aborted: {self._abort_reason}")
                future.set_result(fn(*args))
            except BaseException as exc:
                future.set_exception(exc)
        _finalize_gpu()


_executor: GpuExecutor | None = None


def get_gpu_executor() -> GpuExecutor:
    """The process's GPU executor."""
    global _executor
    if _executor is None:
        _executor = GpuExecutor()
    return _executor
