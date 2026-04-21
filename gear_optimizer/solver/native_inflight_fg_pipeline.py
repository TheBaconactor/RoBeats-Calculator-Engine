from __future__ import annotations

import concurrent.futures
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable

from gear_optimizer.core.utils import safe_int
from gear_optimizer.solver.native_inflight_types import _NativeSong


@dataclass(frozen=True)
class NativeFGPipelineSettings:
    workers: int
    batch_max: int
    prep_workers: int
    ga_credit_budget: int


def read_native_fg_pipeline_settings(
    cfg0: Any,
    *,
    inflight_limit: int,
    ga_credit_budget_cfg: int,
    default_worker_threads: Callable[..., int],
) -> NativeFGPipelineSettings:
    inflight_limit_i = max(1, int(inflight_limit))

    fg_workers_default = min(4, inflight_limit_i)
    fg_workers = fg_workers_default
    if cfg0 is not None:
        try:
            fg_workers = safe_int(
                cfg0.get("IterationEngine", "InFlight_FGWorkers", fallback=str(fg_workers_default)),
                fg_workers_default,
            )
        except Exception:
            fg_workers = fg_workers_default
    raw = os.environ.get("INFLIGHT_FG_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_workers = int(raw)
        except Exception:
            pass
    fg_workers = max(1, min(int(fg_workers), inflight_limit_i))

    fg_batch_max = int(fg_workers)
    try:
        raw = os.environ.get("INFLIGHT_FG_BATCH_MAX")
        if raw is not None and str(raw).strip() != "":
            fg_batch_max = int(raw)
    except Exception:
        fg_batch_max = int(fg_workers)
    fg_batch_max = max(1, min(int(fg_batch_max), int(fg_workers)))

    fg_prep_workers = 0
    if cfg0 is not None:
        try:
            fg_prep_workers = safe_int(cfg0.get("IterationEngine", "InFlight_FGPrepWorkers", fallback="0"), 0)
        except Exception:
            fg_prep_workers = 0
    raw = os.environ.get("INFLIGHT_FG_PREP_WORKERS")
    if raw is not None and str(raw).strip() != "":
        try:
            fg_prep_workers = int(raw)
        except Exception:
            pass
    if fg_prep_workers <= 0:
        fg_prep_workers = default_worker_threads(inflight_limit=inflight_limit_i, kind="fg_prep")
    fg_prep_workers = max(1, min(int(fg_prep_workers), inflight_limit_i))

    return NativeFGPipelineSettings(
        workers=int(fg_workers),
        batch_max=int(fg_batch_max),
        prep_workers=int(fg_prep_workers),
        ga_credit_budget=max(1, int(ga_credit_budget_cfg)),
    )


class NativeFGPipeline:
    """
    Host-side ForceGreats pipeline for native in-flight mode.

    The pipeline owns FG queueing, FG prep workers, FG worker submissions, and
    FG fairness credit. GPU execution still goes through the shared single owner.
    """

    def __init__(self, settings: NativeFGPipelineSettings) -> None:
        self.settings = settings
        self.pending: deque[_NativeSong] = deque()
        self.prep_inflight: deque[_NativeSong] = deque()
        self.futures: deque[tuple[_NativeSong, concurrent.futures.Future, float]] = deque()
        self.ga_credit_budget = max(1, int(settings.ga_credit_budget))
        self.ga_credit = int(self.ga_credit_budget)
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(settings.workers)),
            thread_name_prefix="FG",
        )
        self.prep_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, int(settings.prep_workers)),
            thread_name_prefix="FGPrep",
        )

    @property
    def workers(self) -> int:
        return int(self.settings.workers)

    @property
    def batch_max(self) -> int:
        return int(self.settings.batch_max)

    @property
    def prep_workers(self) -> int:
        return int(self.settings.prep_workers)

    def queue(self, song: _NativeSong, *, now_s: float | None = None) -> None:
        self.pending.append(song)
        try:
            if not isinstance(getattr(song, "fg_queued_t0", None), (int, float)):
                song.fg_queued_t0 = float(time.monotonic() if now_s is None else now_s)
        except Exception:
            pass

    def requeue_front(self, song: _NativeSong) -> None:
        self.pending.appendleft(song)

    def start_prep(
        self,
        song: _NativeSong,
        prep_fn: Callable[..., Any],
        *,
        gpu_client: Any,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> bool:
        if song.fg_prep_future is not None:
            return False
        setattr(song, "_fg_prep_submit_t0", time.perf_counter())
        song.fg_prep_future = self.prep_executor.submit(prep_fn, song, gpu_client=gpu_client)
        if register_future is not None:
            register_future(song.fg_prep_future)
        self.prep_inflight.append(song)
        return True

    def submit_warmup(
        self,
        warmup_fn: Callable[..., Any],
        calc_song: dict,
        ref_arrays: dict,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> concurrent.futures.Future:
        fut = self.prep_executor.submit(warmup_fn, calc_song, ref_arrays)
        if register_future is not None:
            register_future(fut)
        return fut

    def pop_next(self, *, allow_not_ready: bool) -> _NativeSong | None:
        """
        Pick a song for FG submission.

        Normally, only pop songs whose FG prep is complete. When slot pressure
        blocks GA, allow a not-yet-ready song so the FG worker can wait on prep
        instead of losing the job or stalling the owner loop.
        """
        for candidate in list(self.pending):
            fut = candidate.fg_prep_future
            if fut is None:
                try:
                    self.pending.remove(candidate)
                except Exception:
                    pass
                return candidate
            if allow_not_ready:
                try:
                    self.pending.remove(candidate)
                except Exception:
                    pass
                return candidate
            try:
                if fut.done():
                    self.pending.remove(candidate)
                    return candidate
            except Exception:
                continue
        return None

    def oldest_wait_s(self, now_s: float) -> float:
        if not self.pending:
            return 0.0
        oldest_t0 = None
        for candidate in self.pending:
            t0 = getattr(candidate, "fg_queued_t0", None)
            if not isinstance(t0, (int, float)) or float(t0) <= 0.0:
                try:
                    candidate.fg_queued_t0 = float(now_s)
                except Exception:
                    pass
                t0 = float(now_s)
            if oldest_t0 is None or float(t0) < float(oldest_t0):
                oldest_t0 = float(t0)
        if oldest_t0 is None:
            return 0.0
        return max(0.0, float(now_s) - float(oldest_t0))

    def ready_count(self) -> int:
        ready = 0
        for candidate in self.pending:
            fut = candidate.fg_prep_future
            if fut is None:
                ready += 1
                continue
            try:
                if fut.done():
                    ready += 1
            except Exception:
                continue
        return int(ready)

    def submit_job(
        self,
        run_fn: Callable[..., Any],
        song: _NativeSong,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
        **kwargs: Any,
    ) -> concurrent.futures.Future:
        try:
            song.fg_queued_t0 = None
        except Exception:
            pass
        t_submit = time.perf_counter()
        future = self.executor.submit(run_fn, song, **kwargs)
        if register_future is not None:
            register_future(future)
        self.futures.append((song, future, t_submit))
        self.note_fg_submit()
        return future

    def replace_futures(self, futures: deque[tuple[_NativeSong, concurrent.futures.Future, float]]) -> None:
        self.futures.clear()
        self.futures.extend(futures)

    def note_ga_submit(self) -> None:
        if self.pending:
            self.ga_credit = max(-int(self.ga_credit_budget), int(self.ga_credit) - 1)
        else:
            self.ga_credit = int(self.ga_credit_budget)

    def note_fg_submit(self) -> None:
        self.ga_credit = int(self.ga_credit_budget)

    def reset_credit_if_empty(self) -> None:
        if not self.pending:
            self.ga_credit = int(self.ga_credit_budget)

    def active_song_keys(self) -> set[str]:
        keys: set[str] = set()
        for song in self.pending:
            key = self._song_key(song)
            if key:
                keys.add(key)
        for song in self.prep_inflight:
            key = self._song_key(song)
            if key:
                keys.add(key)
        for song, _fut, _t_submit in self.futures:
            key = self._song_key(song)
            if key:
                keys.add(key)
        return keys

    def shutdown_fg(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def shutdown_prep(self, *, wait: bool = True, cancel_futures: bool = True) -> None:
        self.prep_executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    @staticmethod
    def _song_key(song: _NativeSong) -> str:
        try:
            return str(getattr(song, "task_key", "") or getattr(song, "song_name", "")).strip()
        except Exception:
            return ""
