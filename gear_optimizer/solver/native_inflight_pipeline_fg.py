from __future__ import annotations

import concurrent.futures
import multiprocessing
import time
import traceback
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from gear_optimizer.solver.fg_materialization_worker import (
    FgMaterializationResult,
    build_fg_materialization_request,
    materialize_fg_request,
)
from gear_optimizer.solver.gpu_service import GpuServiceClient
from gear_optimizer.solver.native_inflight_config import NativeSong

if TYPE_CHECKING:
    from gear_optimizer.solver.native_inflight_lifecycle import ProgressTracker



@dataclass(frozen=True)
class NativeFGPipelineSettings:
    workers: int
    batch_max: int
    prep_workers: int


@dataclass(frozen=True)
class NativeFGPrepCompletion:
    song: NativeSong
    submit_t0: float | None
    cpu_seconds: float | None
    error: Exception | None = None
    trace: str = ""
    future_missing: bool = False


@dataclass(frozen=True)
class NativeFGJobCompletion:
    song: NativeSong
    future: concurrent.futures.Future
    submit_t0: float


def read_native_fg_pipeline_settings(
    *,
    inflight_limit: int,
    default_worker_threads: Callable[..., int],
) -> NativeFGPipelineSettings:
    inflight_limit_i = max(1, int(inflight_limit))
    # FG jobs are host-only materialization since the fused GA->FG handoff (the GA
    # turn already carries the owner score map). Two isolated workers overlap this
    # CPU stage with Vulkan while bounding host-core and resident-memory pressure.
    fg_workers = 2 if int(inflight_limit_i) > 1 else 1
    fg_workers = max(1, min(int(fg_workers), int(inflight_limit_i), 8))
    fg_batch_max = max(1, min(int(fg_workers), 8))
    # Dynamic FG prep owns worker-readiness: candidate selection and exact-plan
    # construction happen before a song can be handed to an FG worker. Size this
    # runway from the CPU-aware policy.
    fg_prep_workers = int(
        default_worker_threads(
            inflight_limit=int(inflight_limit_i),
            kind="fg_prep",
        )
    )
    fg_prep_workers = max(1, min(int(fg_prep_workers), int(inflight_limit_i), 8))
    return NativeFGPipelineSettings(
        workers=int(fg_workers),
        batch_max=int(fg_batch_max),
        prep_workers=int(fg_prep_workers),
    )


def _remove_song_by_identity(songs: deque[NativeSong], song: NativeSong) -> bool:
    """Remove a song from a conveyor deque by identity, tolerating absence.

    `deque.remove` compares via `__eq__` and formats the not-found ValueError
    with `repr(value)`; NativeSong is a deep dataclass whose repr renders the
    full song payload (ref arrays, FG plans) — tens of seconds of CPU per miss.
    """
    for idx, existing in enumerate(songs):
        if existing is song:
            del songs[idx]
            return True
    return False


class NativeFGPipeline:
    """
    Host-side ForceGreats pipeline for native in-flight mode.
    The pipeline owns FG queueing, FG prep workers, and FG worker submissions.
    FG jobs never touch the GPU owner: the fused GA turn already scored FG, so
    workers only materialize plans against the owner score map.
    """

    def __init__(self, settings: NativeFGPipelineSettings) -> None:
        self.settings = settings
        self.pending: deque[NativeSong] = deque()
        self.prep_inflight: deque[NativeSong] = deque()
        self.futures: deque[tuple[NativeSong, concurrent.futures.Future, float]] = deque()
        # Taichi's synchronous Vulkan calls hold the process GIL while the owner waits
        # for the device. FG materialization is Python/Numba host work; threads therefore
        # cannot drain it concurrently and eventually force the bounded GA conveyor to
        # pause. Spawned workers give this exact host stage independent interpreters.
        self.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=max(1, int(settings.workers)),
            mp_context=multiprocessing.get_context("spawn"),
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

    def queue(self, song: NativeSong) -> None:
        self.pending.append(song)


    def _claim_pending_song(self, song: NativeSong) -> NativeSong:
        _remove_song_by_identity(self.pending, song)
        _remove_song_by_identity(self.prep_inflight, song)
        return song

    def start_prep(
        self,
        song: NativeSong,
        prep_fn: Callable[..., Any],
        *,
        gpu_client: GpuServiceClient | None,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> bool:
        runtime = getattr(song, "runtime", song)
        if runtime.fg.fg_prep_future is not None:
            return False
        song.runtime.fg.fg_dynamic_prep_done = False
        song.runtime.fg.fg_prep_submit_t0 = time.perf_counter()
        runtime.fg.fg_prep_future = self.prep_executor.submit(prep_fn, song, gpu_client=gpu_client)
        if register_future is not None:
            register_future(runtime.fg.fg_prep_future)
        self.prep_inflight.append(song)
        return True

    def active_prep_count(self) -> int:
        active = 0
        seen: set[int] = set()
        for song in self.prep_inflight:
            fut = song.runtime.fg.fg_prep_future
            if fut is None:
                continue
            fut_id = int(id(fut))
            if fut_id and fut_id in seen:
                continue
            if fut_id:
                seen.add(fut_id)
            if fut.done():
                continue
            active += 1
        return int(active)

    def has_active_prep(self) -> bool:
        if self.active_prep_count() > 0:
            return True
        for song in self.pending:
            fut = song.runtime.fg.fg_prep_future
            if fut is None:
                continue
            if not fut.done():
                return True
        return False

    def finish_completed_prep(self) -> list[NativeFGPrepCompletion]:
        completions: list[NativeFGPrepCompletion] = []
        for song in list(self.prep_inflight):
            future = song.runtime.fg.fg_prep_future
            if future is None:
                self.prep_inflight.remove(song)
                completions.append(
                    NativeFGPrepCompletion(
                        song=song,
                        submit_t0=None,
                        cpu_seconds=None,
                        future_missing=True,
                    )
                )
                continue
            if not future.done():
                continue
            self.prep_inflight.remove(song)
            submit_t0 = song.runtime.fg.fg_prep_submit_t0
            cpu_seconds = song.runtime.fg.cpu_fg_prep_s
            error: Exception | None = None
            trace = ""
            try:
                if submit_t0 is not None:
                    song.runtime.fg.fg_prep_submit_t0 = None
                future.result()
                song.runtime.fg.fg_dynamic_prep_done = True
            except Exception as exc:
                error = exc
                trace = traceback.format_exc()
            finally:
                song.runtime.fg.fg_prep_future = None
            completions.append(
                NativeFGPrepCompletion(
                    song=song,
                    submit_t0=submit_t0,
                    cpu_seconds=cpu_seconds,
                    error=error,
                    trace=trace,
                )
            )
        return completions

    def start_pending_prep(
        self,
        prep_fn: Callable[..., Any],
        *,
        gpu_client: GpuServiceClient | None,
        max_new: int | None = None,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> int:
        """
        Top up the dynamic FG-prep runway from pending FG songs.
        This keeps backlog/drain CPU prep in the prep executor instead of letting
        FG worker threads serialize on not-ready songs before each GPU burst.
        """
        budget = max(0, int(self.prep_workers) - int(self.active_prep_count()))
        if max_new is not None:
            budget = min(int(budget), max(0, int(max_new)))
        if budget <= 0:
            return 0
        started = 0
        for song in list(self.pending):
            if started >= budget:
                break
            if bool(song.runtime.fg.fg_dynamic_prep_done):
                continue
            if song.runtime.fg.fg_prep_future is not None:
                continue
            if self.start_prep(
                song,
                prep_fn,
                gpu_client=gpu_client,
                register_future=register_future,
            ):
                started += 1
        return int(started)

    def pop_next(self, *, allow_not_ready: bool) -> NativeSong | None:
        """
        Pick a song for FG submission.
        Normally, only pop songs whose FG prep is complete. During the final FG
        drain (no GA work left), allow a not-yet-ready song so the FG worker can
        wait on prep instead of serializing behind the scheduler loop.
        """
        for candidate in list(self.pending):
            runtime = getattr(candidate, "runtime", candidate)
            fut = runtime.fg.fg_prep_future
            if fut is None:
                if not bool(candidate.runtime.fg.fg_dynamic_prep_done):
                    if not allow_not_ready:
                        continue
                    return self._claim_pending_song(candidate)
                return self._claim_pending_song(candidate)
            if allow_not_ready:
                return self._claim_pending_song(candidate)
            if fut.done():
                return self._claim_pending_song(candidate)
        return None

    def ready_count(self) -> int:
        ready = 0
        for candidate in self.pending:
            runtime = getattr(candidate, "runtime", candidate)
            fut = runtime.fg.fg_prep_future
            if fut is None:
                if not bool(candidate.runtime.fg.fg_dynamic_prep_done):
                    continue
                ready += 1
                continue
            if fut.done():
                ready += 1
        return int(ready)

    def submit_job(
        self,
        run_fn: Callable[..., Any],
        song: NativeSong,
        *args: Any,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
        **kwargs: Any,
    ) -> concurrent.futures.Future:
        t_submit = time.perf_counter()
        future = self.executor.submit(run_fn, *args, **kwargs)
        if register_future is not None:
            register_future(future)
        self.futures.append((song, future, t_submit))
        return future

    def submit_materialization(
        self,
        song: NativeSong,
        *,
        register_future: Callable[[concurrent.futures.Future | None], None] | None = None,
    ) -> concurrent.futures.Future:
        runtime = getattr(song, "runtime", song)
        prep_future = getattr(runtime.fg, "fg_prep_future", None)
        if prep_future is not None:
            try:
                prep_future.result()
                if getattr(runtime.fg, "fg_response_frontier_plan", None) is None:
                    raise RuntimeError(
                        "FG dynamic prep completed without the exact response frontier plan "
                        f"for {self._song_key(song)}"
                    )
                runtime.fg.fg_dynamic_prep_done = True
            except Exception as exc:
                raise RuntimeError(f"FG dynamic prep failed for {self._song_key(song)}") from exc
            finally:
                runtime.fg.fg_prep_future = None

        request = build_fg_materialization_request(song)
        return self.submit_job(
            materialize_fg_request,
            song,
            request,
            register_future=register_future,
        )

    def replace_futures(self, futures: deque[tuple[NativeSong, concurrent.futures.Future, float]]) -> None:
        self.futures.clear()
        self.futures.extend(futures)

    def pop_completed_jobs(self) -> list[NativeFGJobCompletion]:
        completions: list[NativeFGJobCompletion] = []
        still_pending: deque[tuple[NativeSong, concurrent.futures.Future, float]] = deque()
        for song, future, submit_t0 in list(self.futures):
            done = future.done()
            if done:
                completions.append(
                    NativeFGJobCompletion(
                        song=song,
                        future=future,
                        submit_t0=float(submit_t0),
                    )
                )
            else:
                still_pending.append((song, future, submit_t0))
        self.replace_futures(still_pending)
        return completions

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
    def _song_key(song: NativeSong) -> str:
        try:
            return str(song.config.task_key or song.config.song_name).strip()
        except (KeyError, TypeError, ValueError):
            return ""


def release_fg_song_surfaces(song: NativeSong) -> None:
    """Release a song's ~0.5-1.5 GB FG response surfaces once its FG scoring is complete.

    After this job's `materialize_from_owner_score_map`, nothing else reads the per-song scoring
    bundle, prepared plan, or owner score map -- the fused GA turn and the FG planner are the only
    other readers and both run earlier. Left alone, each song's surface pool stays resident, pinned
    by BOTH the per-song bundle handle and the process-global response-frontier caches, until the
    song object is garbage-collected and the entry-count LRU evicts it. A standalone optimizer run
    never runs the serving-mode idle sweep, so ~prep_limit songs' worth accumulates and trips the
    memory guard after only a few dozen songs. Dropping all three references here bounds resident FG
    surfaces to the songs actively scoring. Lossless: any later access rebuilds from the on-disk
    bundle. Best-effort -- a cleanup error must not fail the already-complete FG job.
    """
    fg = song.runtime.fg
    if fg is None:
        return
    bundle = getattr(fg, "fg_response_scoring_bundle", None)
    if bundle is not None:
        from gear_optimizer.solver.taichi_gem.force_greats.response_cache import (
            release_fg_response_song_memory,
        )

        release_fg_response_song_memory(getattr(bundle, "cache_key", ()))
    fg.fg_response_scoring_bundle = None
    fg.fg_response_frontier_plan = None
    fg.fg_owner_score_map = None


def apply_fg_materialization_result(
    song: NativeSong,
    result: FgMaterializationResult,
    *,
    progress_cb=None,
    progress_tracker: ProgressTracker | None = None,
) -> None:
    """Apply a spawned worker's FG results on the driver/persistence owner."""

    if not isinstance(result, FgMaterializationResult):
        raise TypeError("FG materialization worker returned an invalid result")

    from gear_optimizer.solver.native_inflight_lifecycle import evaluate_fg_progress_record_update

    runtime = getattr(song, "runtime", song)
    runtime.fg.fg_results = result.results
    runtime.fg.fg_run_wall_s = max(0.0, float(result.wall_seconds))
    runtime.fg.cpu_fg_run_s = max(0.0, float(result.cpu_seconds))

    runtime.db.record_info = evaluate_fg_progress_record_update(song, progress_tracker)
    if progress_cb is not None:
        progress_cb(completed_delta=0, failed_delta=0, record_info=runtime.db.record_info)
