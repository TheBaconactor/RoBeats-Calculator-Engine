from __future__ import annotations

import concurrent.futures
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

from gear_optimizer.solver.native_inflight_types import NativeSong, native_song_label

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CpuPrewarmCompletion:
    song: NativeSong
    submit_t0: float
    label: str
    error: Exception | None = None


class CpuPrewarmQueue:
    def __init__(
        self,
        *,
        max_workers: int,
        lookahead: int,
        prewarm_fn: Callable[[NativeSong], None],
        label_for_song: Callable[[NativeSong], str] | None = None,
    ) -> None:
        self.executor = (
            concurrent.futures.ThreadPoolExecutor(
                max_workers=max(1, int(max_workers)),
                thread_name_prefix="CPUPrewarm",
            )
            if int(max_workers) > 0
            else None
        )
        self.lookahead = max(0, int(lookahead))
        self.prewarm_fn = prewarm_fn
        self.label_for_song = label_for_song or self.default_label_for_song
        self.inflight: deque[tuple[NativeSong, concurrent.futures.Future, float, str]] = deque()
        self.submitted: set[str] = set()

    def __len__(self) -> int:
        return int(len(self.inflight))

    def __bool__(self) -> bool:
        return bool(self.inflight)

    @staticmethod
    def default_label_for_song(song: NativeSong) -> str:
        return native_song_label(song, fallback_id=True)

    def submit(
        self,
        song: NativeSong,
        *,
        label: str | None = None,
        register_future: Callable[[concurrent.futures.Future | None], None],
    ) -> bool:
        if self.executor is None or int(self.lookahead) <= 0:
            return False
        task_key = str(label if label is not None else self.label_for_song(song))
        if task_key in self.submitted:
            return False
        if getattr(song.runtime.prep, "cpu_prewarm_future", None) is not None:
            return False
        self.submitted.add(task_key)
        try:
            song.runtime.prep.cpu_prewarm_submit_t0 = time.perf_counter()
            future = self.executor.submit(self.prewarm_fn, song)
            song.runtime.prep.cpu_prewarm_future = future
            self.inflight.append((song, future, time.perf_counter(), task_key))
            register_future(future)
            return True
        except Exception as e:
            logger.debug(f"native_inflight_cpu_prewarm:submit: {e}")
            self.submitted.discard(task_key)
            try:
                song.runtime.prep.cpu_prewarm_future = None
            except Exception as e:
                logger.debug(f"native_inflight_cpu_prewarm:submit: {e}")
            return False

    def submit_prepared_backlog(
        self,
        prepared,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None],
        extra_submit: Callable[[NativeSong], bool] | None = None,
    ) -> int:
        if int(self.lookahead) <= 0:
            return 0
        started = 0
        for idx, song in enumerate(list(prepared)):
            if idx >= int(self.lookahead):
                break
            if self.submit(
                song,
                register_future=register_future,
            ):
                started += 1
            if extra_submit is not None and extra_submit(song):
                started += 1
        return int(started)

    def finish_completed(self) -> list[CpuPrewarmCompletion]:
        completions: list[CpuPrewarmCompletion] = []
        for song, future, submit_t0, label in list(self.inflight):
            if not future.done():
                continue
            self.inflight.remove((song, future, submit_t0, label))
            error: Exception | None = None
            try:
                future.result()
            except Exception as exc:
                error = exc
                self.submitted.discard(str(label))
            finally:
                try:
                    song.runtime.prep.cpu_prewarm_future = None
                except Exception as e:
                    logger.debug(f"native_inflight_cpu_prewarm:finish_completed: {e}")
            completions.append(
                CpuPrewarmCompletion(
                    song=song,
                    submit_t0=float(submit_t0),
                    label=str(label),
                    error=error,
                )
            )
        return completions

    def shutdown(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        if self.executor is not None:
            self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)
