from __future__ import annotations

import concurrent.futures
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SongPrepCompletion:
    task: tuple
    logical_task: tuple
    future: concurrent.futures.Future
    submit_t0: float


class SongPrepQueue:
    def __init__(self, *, max_workers: int, prep_fn: Callable[[tuple], Any]) -> None:
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(max_workers)),
            thread_name_prefix="SongPrep",
        )
        self.prep_fn = prep_fn
        self.inflight: deque[tuple[tuple, tuple, concurrent.futures.Future, float]] = deque()

    def submit(
        self,
        task: tuple,
        logical_task: tuple,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> concurrent.futures.Future:
        future = self.executor.submit(self.prep_fn, logical_task)
        register_future(future)
        self.inflight.append((task, logical_task, future, time.perf_counter()))
        return future

    def pop_completed(self) -> list[SongPrepCompletion]:
        completions: list[SongPrepCompletion] = []
        for task, logical_task, future, submit_t0 in list(self.inflight):
            try:
                done = future.done()
            except Exception as e:
                logger.debug(f"native_inflight_song_prep_queue:pop_completed: {e}")
                done = False
            if not done:
                continue
            self.inflight.remove((task, logical_task, future, submit_t0))
            completions.append(
                SongPrepCompletion(
                    task=task,
                    logical_task=logical_task,
                    future=future,
                    submit_t0=float(submit_t0),
                )
            )
        return completions

    def cancel_all(self) -> None:
        for _task, _logical_task, future, _submit_t0 in list(self.inflight):
            try:
                future.cancel()
            except Exception as e:
                logger.debug(f"native_inflight_song_prep_queue:cancel_all: {e}")
        self.inflight.clear()

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)
