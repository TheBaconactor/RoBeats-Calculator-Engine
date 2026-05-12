from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
import queue
import threading
import time
from typing import Any

from gear_optimizer.core.env_config import ENV
from gear_optimizer.solver.gpu_executor_types import GpuResponse


class WorkerResponseRouter:
    def __init__(self, *, pending_ttl_sec: float, pending_max: int) -> None:
        self._pending: OrderedDict[int, tuple[GpuResponse, float]] = OrderedDict()
        self._cond = threading.Condition()
        self._pending_ttl_sec = max(0.0, float(pending_ttl_sec))
        self._pending_max = max(0, int(pending_max))
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def reset(self) -> None:
        self._stop_thread()
        self.clear_pending()

    def restart(self) -> None:
        self._stop_thread()
        self._stop.clear()
        self.clear_pending()

    def clear_pending(self) -> None:
        with self._cond:
            self._pending = OrderedDict()
            self._cond.notify_all()

    def prune(self, now: float | None = None) -> None:
        with self._cond:
            self._prune_locked(now)

    def ensure_started(self, response_queue_getter: Callable[[], Any | None], *, label: str) -> None:
        thread = self._thread
        if thread is not None and thread.is_alive():
            return
        self._stop.clear()
        thread = threading.Thread(
            target=self._loop,
            args=(response_queue_getter,),
            name=f"GpuWorkerResponseRouter[{label}]",
            daemon=True,
        )
        self._thread = thread
        thread.start()

    def wait(self, request_id: int, timeout: float) -> GpuResponse:
        deadline = time.monotonic() + float(timeout)
        with self._cond:
            while True:
                self._prune_locked()
                if request_id in self._pending:
                    response, _ts = self._pending.pop(request_id)
                    return response
                remaining = float(deadline - time.monotonic())
                if remaining <= 0:
                    raise RuntimeError(f"GPU executor timeout after {timeout}s")
                self._cond.wait(timeout=remaining)

    def store(self, response: GpuResponse) -> None:
        with self._cond:
            self._store_locked(response)
            self._cond.notify_all()

    def _stop_thread(self) -> None:
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
        thread = self._thread
        if thread is not None:
            try:
                thread.join(timeout=0.25)
            except Exception:
                pass
        self._thread = None

    def _loop(self, response_queue_getter: Callable[[], Any | None]) -> None:
        while True:
            if self._stop.is_set():
                return
            response_queue = response_queue_getter()
            if response_queue is None:
                time.sleep(0.01)
                continue
            try:
                response = response_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            except (OSError, ValueError):
                time.sleep(0.05)
                continue
            if response is None:
                continue
            self.store(response)

    def _store_locked(self, response: GpuResponse) -> None:
        request_id = int(getattr(response, "request_id", 0) or 0)
        now = time.monotonic()
        self._pending[request_id] = (response, now)
        self._pending.move_to_end(request_id)
        self._prune_locked(now)

    def _prune_locked(self, now: float | None = None) -> None:
        if not self._pending:
            return
        if now is None:
            now = time.monotonic()
        if self._pending_ttl_sec > 0.0:
            while self._pending:
                _response, ts = next(iter(self._pending.values()))
                if (now - ts) <= self._pending_ttl_sec:
                    break
                self._pending.popitem(last=False)
        if self._pending_max > 0:
            while len(self._pending) > self._pending_max:
                self._pending.popitem(last=False)


worker_response_router = WorkerResponseRouter(
    pending_ttl_sec=max(0.0, float(getattr(ENV, "gpu_executor_pending_ttl_sec", 300.0) or 0.0)),
    pending_max=max(0, int(getattr(ENV, "gpu_executor_pending_max", 2048) or 0)),
)
