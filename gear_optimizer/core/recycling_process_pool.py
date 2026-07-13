"""Python 3.10-compatible process pool with bounded whole-pool generations."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import threading
from collections.abc import Callable
from concurrent.futures.process import BrokenProcessPool
from typing import Any


class BoundedRecyclingProcessPool:
    """Spawn executor recycled after a bounded aggregate number of submissions.

    ``ProcessPoolExecutor(max_tasks_per_child=...)`` is unavailable on Python 3.10
    and can deadlock when every original worker reaches its task cap. Recycling the
    complete executor after ``max_workers * max_tasks_per_worker`` submissions keeps
    allocator retention bounded without relying on that worker-replacement path.
    """

    def __init__(
        self,
        *,
        max_workers: int,
        max_tasks_per_worker: int,
        initializer: Callable[..., None] | None = None,
        initargs: tuple[Any, ...] = (),
    ) -> None:
        if int(max_workers) < 1:
            raise ValueError("max_workers must be positive")
        if int(max_tasks_per_worker) < 1:
            raise ValueError("max_tasks_per_worker must be positive")
        self._max_workers = int(max_workers)
        self._generation_capacity = self._max_workers * int(max_tasks_per_worker)
        self._initializer = initializer
        self._initargs = tuple(initargs)
        self._context = multiprocessing.get_context("spawn")
        self._lock = threading.Lock()
        self._closed = False
        self._executor: concurrent.futures.ProcessPoolExecutor | None = None
        self._generation_futures: list[concurrent.futures.Future] = []
        self._start_generation()

    def _start_generation(self) -> None:
        self._executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=self._max_workers,
            mp_context=self._context,
            initializer=self._initializer,
            initargs=self._initargs,
        )
        self._generation_futures = []

    def _finish_generation(self) -> None:
        executor = self._executor
        if executor is None:
            return
        if self._generation_futures:
            concurrent.futures.wait(self._generation_futures)
        executor.shutdown(wait=True)
        self._executor = None
        self._generation_futures = []

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> concurrent.futures.Future:
        with self._lock:
            if self._closed:
                raise RuntimeError("cannot schedule new futures after shutdown")
            if len(self._generation_futures) >= self._generation_capacity:
                self._finish_generation()
                self._start_generation()
            executor = self._executor
            if executor is None:
                raise RuntimeError("process pool generation is not initialized")
            try:
                future = executor.submit(fn, *args, **kwargs)
            except BrokenProcessPool:
                # Native exits and initializer failures break every Future in the generation.
                # Drain those explicit failures, replace the whole generation, and preserve
                # forward progress for work that was not yet submitted.
                self._finish_generation()
                self._start_generation()
                executor = self._executor
                if executor is None:
                    raise RuntimeError("replacement process pool generation is not initialized")
                future = executor.submit(fn, *args, **kwargs)
            self._generation_futures.append(future)
            return future

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._finish_generation()

    def __enter__(self) -> BoundedRecyclingProcessPool:
        return self

    def __exit__(self, *_exc_info: object) -> bool:
        self.shutdown()
        return False
