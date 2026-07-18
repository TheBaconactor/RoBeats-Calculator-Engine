"""Python 3.10-compatible process pool with independently recycled workers."""

from __future__ import annotations

import concurrent.futures
import multiprocessing
import threading
from collections.abc import Callable
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from typing import Any


@dataclass
class _WorkerSlot:
    executor: concurrent.futures.ProcessPoolExecutor
    futures: list[concurrent.futures.Future]
    submitted: int = 0


class BoundedRecyclingProcessPool:
    """Spawn workers recycled independently after a bounded number of submissions.

    ``ProcessPoolExecutor(max_tasks_per_child=...)`` is unavailable on Python 3.10
    and can deadlock when every original worker reaches its task cap. One single-worker
    executor per slot gives the same hard lifetime bound without a whole-pool generation
    barrier: when every slot is full, only the first slot to drain is replaced while the
    other workers keep running.
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
        self._max_tasks_per_worker = int(max_tasks_per_worker)
        self._initializer = initializer
        self._initargs = tuple(initargs)
        self._context = multiprocessing.get_context("spawn")
        self._lock = threading.Lock()
        self._closed = False
        self._next_slot = 0
        self._slots = [self._start_slot() for _ in range(self._max_workers)]

    def _start_slot(self) -> _WorkerSlot:
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=1,
            mp_context=self._context,
            initializer=self._initializer,
            initargs=self._initargs,
        )
        return _WorkerSlot(executor=executor, futures=[])

    def _finish_slot(self, slot_index: int) -> None:
        slot = self._slots[int(slot_index)]
        if slot.futures:
            concurrent.futures.wait(slot.futures)
        slot.executor.shutdown(wait=True)

    def _recycle_slot(self, slot_index: int) -> None:
        self._finish_slot(int(slot_index))
        self._slots[int(slot_index)] = self._start_slot()

    def _cyclic_distance(self, slot_index: int) -> int:
        return (int(slot_index) - int(self._next_slot)) % int(self._max_workers)

    def _submission_slot(self) -> int:
        idle = [
            index
            for index, slot in enumerate(self._slots)
            if not slot.futures or slot.futures[-1].done()
        ]
        if idle:
            slot_index = min(
                idle,
                key=lambda index: (
                    int(self._slots[int(index)].submitted),
                    self._cyclic_distance(int(index)),
                ),
            )
            if int(self._slots[int(slot_index)].submitted) >= int(
                self._max_tasks_per_worker
            ):
                self._recycle_slot(int(slot_index))
        else:
            available = [
                index
                for index, slot in enumerate(self._slots)
                if int(slot.submitted) < int(self._max_tasks_per_worker)
            ]
            if available:
                # General callers may submit more futures than workers. Keep their queues even;
                # the frontier prebuilders normally arrive here only during their initial fill.
                slot_index = min(
                    available,
                    key=lambda index: (
                        sum(not future.done() for future in self._slots[int(index)].futures),
                        int(self._slots[int(index)].submitted),
                        self._cyclic_distance(int(index)),
                    ),
                )
            else:
                # Every worker has its full lifetime queued. Wait only for the earliest worker's
                # final task, recycle that one slot, and leave every other worker undisturbed.
                tails = [slot.futures[-1] for slot in self._slots]
                done, _pending = concurrent.futures.wait(
                    tails,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                drained = [
                    index
                    for index, future in enumerate(tails)
                    if future in done
                ]
                if not drained:
                    raise RuntimeError(
                        "recycling process pool did not identify a drained worker"
                    )
                slot_index = min(drained, key=self._cyclic_distance)
                self._recycle_slot(int(slot_index))
        self._next_slot = (int(slot_index) + 1) % int(self._max_workers)
        return int(slot_index)

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> concurrent.futures.Future:
        with self._lock:
            if self._closed:
                raise RuntimeError("cannot schedule new futures after shutdown")
            slot_index = self._submission_slot()
            slot = self._slots[int(slot_index)]
            try:
                future = slot.executor.submit(fn, *args, **kwargs)
            except BrokenProcessPool:
                # A native exit poisons only this one-worker executor. Its already-returned
                # futures retain their explicit failures; replace the slot and retry only the
                # work that had not yet been submitted.
                self._recycle_slot(int(slot_index))
                slot = self._slots[int(slot_index)]
                future = slot.executor.submit(fn, *args, **kwargs)
            slot.futures.append(future)
            slot.submitted += 1
            return future

    def shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for slot_index in range(self._max_workers):
                self._finish_slot(int(slot_index))

    def __enter__(self) -> BoundedRecyclingProcessPool:
        return self

    def __exit__(self, *_exc_info: object) -> bool:
        self.shutdown()
        return False
