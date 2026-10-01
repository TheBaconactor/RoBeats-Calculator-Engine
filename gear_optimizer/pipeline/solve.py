"""Songs end to end in this process.

A song: prepare_native_song (incl. the GA-invariant FG static prep) -> run_ga (the GA with its fused FG owner score,
on the GPU executor) -> finish_song (decode -> FG plan -> FG materialization -> SongSolve, host only). No per-song
process or pool (the in-flight pipeline spawns an FG process pool per run and schedules up to 12 songs at once).

solve_song: one song on the calling thread (the persistent worker).

run_queue: a queue with the GPU going from one GA to the next: while a song's GA runs, a helper thread prepares the
next songs and another finishes the previous ones (on the M4 one GA at a time beats twelve songs in flight:
bench/BASELINE.md). Finished songs go to the run's post-processor, whose own GPU context canonicalizes and stores them.
"""

from __future__ import annotations

import collections
import concurrent.futures
import threading
import traceback
from collections.abc import Callable
from typing import Any

from gear_optimizer.pipeline.results import SongSolve, song_solve

# Slot 0 is the registry solves' (the meta gem re-solve); GA runs use 1..N-1 (song_slot_pool).
_GA_SLOT = 1
# run_queue: songs prepared ahead of the GA and finishing behind it. Under a GA a song's preparation or finish takes
# about one GA (they share the GIL with the GA's kernel launches; bench/ga_timeline.py), so 2 keeps the GPU on GAs.
_PREP_AHEAD = 2
_FINISH_BEHIND = 2
# Taichi init + the GA kernel warmup (cold: compiling every kernel).
_GPU_INIT_TIMEOUT_S = 600.0


class SolveContext:
    """A process's GPU executor and its client, started once (the executor keeps Taichi and the GA kernels warm).

    The executor initializes Taichi and warms the GA kernels on its own thread; the first GA waits for that, so the
    first songs' preparation overlaps it."""

    def __init__(self) -> None:
        from gear_optimizer.solver.gpu_executor import get_gpu_executor

        self._executor = get_gpu_executor()
        self._executor.start(in_process=True)
        self._client = None

    @property
    def gpu_client(self) -> Any:
        """The executor's client once its GPU init finished; GpuFatalError if the init failed or timed out."""
        if self._client is None:
            from gear_optimizer.solver.gpu_service import GpuFatalError, GpuServiceClient

            if not self._executor.wait_until_ready(timeout=_GPU_INIT_TIMEOUT_S):
                error = self._executor.last_init_error
                self._executor.stop()
                raise GpuFatalError(f"GPU executor Taichi init failed or timed out ({error})")
            client = GpuServiceClient(self._executor)
            client.start(start_executor=False)
            self._client = client
        return self._client

    def close(self, *, stop_executor: bool = False) -> None:
        """Close the client; `stop_executor` also stops the executor (it persists Taichi's offline kernel cache)."""
        if self._client is not None:
            self._client.close(timeout=2.0)
        if stop_executor and self._executor.is_running:
            self._executor.stop()

    def abort(self, reason: str) -> None:
        """Abort the GA running on the executor: its future raises "GpuExecutor aborted: <reason>"."""
        self._executor.request_abort(reason)


def run_ga(song: Any, ctx: SolveContext) -> Any:
    """The GA result of a prepared song (prepare_native_song)."""
    from gear_optimizer.solver.native_inflight_pipeline_ga import InflightGAPipeline

    song.runtime.song_slot = _GA_SLOT
    try:
        InflightGAPipeline.prepare_submit(song)
        return ctx.gpu_client.submit_gpu_native_ga_run(InflightGAPipeline.build_payload(song)).future.result()
    finally:
        song.runtime.song_slot = 0


def finish_song(song: Any, ga_result: Any) -> SongSolve:
    """The SongSolve of a song from its GA result (no GPU work)."""
    from gear_optimizer.solver.fg_materialization_worker import (
        build_fg_materialization_request,
        materialize_fg_request,
    )
    from gear_optimizer.solver.native_inflight_pipeline import decode_ga_payload_sync, prepare_fg_job_sync
    from gear_optimizer.solver.native_inflight_pipeline_fg import (
        apply_fg_materialization_result,
        release_fg_song_surfaces,
    )
    from gear_optimizer.solver.native_inflight_pipeline_ga import InflightGAPipeline

    InflightGAPipeline.store_decode_result(song, decode_ga_payload_sync(song, ga_result))
    try:
        prepare_fg_job_sync(song)
        song.runtime.fg.fg_dynamic_prep_done = True
        apply_fg_materialization_result(song, materialize_fg_request(build_fg_materialization_request(song)))
    finally:
        release_fg_song_surfaces(song)
    return song_solve(song)


def solve_song(task: tuple, ctx: SolveContext) -> SongSolve:
    """The SongSolve of one queue task (an app task tuple)."""
    from gear_optimizer.solver.native_inflight_lifecycle import prepare_native_song

    song = prepare_native_song(task)
    return finish_song(song, run_ga(song, ctx))


def run_queue(
    tasks: list[tuple],
    ctx: SolveContext,
    *,
    post: Callable[[Any], None],
    completed_songs: set[str],
    memory_resume_tracker=None,
    stop_requested: Callable[[], bool] | None = None,
    progress_cb=None,
) -> None:
    """Solve `tasks` (queue tasks; SongRepeats are separate tasks); post each SongSolve or error payload in queue order.

    A task is marked completed once finished (also when it failed: its error went to `post`, as in the in-flight
    pipeline); a stop request or a memory release leaves the unfinished tasks pending (the resume journal keeps them).
    A stop request also aborts the GA in progress (its song stays pending, as in the in-flight pipeline); songs past
    their GA still finish. A GpuFatalError (GPU init failed, a GA past its watchdog) ends the run, as in the in-flight
    pipeline: the process cannot use its GPU any more. Any other error fails that song only."""
    from gear_optimizer.core.memory import memory_release_requested
    from gear_optimizer.domain.jobs import task_file_path, task_queue_label, task_song_name
    from gear_optimizer.solver.native_inflight_completion import (
        build_native_song_error_payload,
        build_native_task_error_payload,
        mark_song_completed,
    )
    from gear_optimizer.solver.native_inflight_lifecycle import (
        ProgressTracker,
        is_stop_abort_exception,
        prepare_native_song,
    )
    from gear_optimizer.solver.gpu_service import GpuFatalError

    progress = ProgressTracker()

    def stopping() -> bool:
        return bool((stop_requested is not None and stop_requested()) or memory_release_requested())

    def abort_on_stop(done: threading.Event) -> None:
        while not done.wait(0.05):
            if stop_requested():
                ctx.abort("stop requested")
                return

    # The finisher thread posts and completes every task, so both happen in queue order.
    def complete(task: tuple) -> None:
        mark_song_completed(completed_songs=completed_songs, task_key=task_queue_label(task),
                            song_name=task_song_name(task), song_path=task_file_path(task),
                            memory_resume_tracker=memory_resume_tracker)

    def fail(task: tuple, item: dict) -> None:
        post(item)
        progress.emit_error_item_progress(progress_cb, item)
        complete(task)

    def finish(task: tuple, song: Any, ga_result: Any) -> None:
        try:
            post(finish_song(song, ga_result))
        except Exception as exc:
            fail(task, build_native_song_error_payload(song, exc=exc, trace=traceback.format_exc()))
            return
        progress.emit_done_song_progress(progress_cb, song)
        complete(task)

    queue = [task for task in tasks if task_queue_label(task) not in completed_songs]
    done = threading.Event()
    if stop_requested is not None:
        threading.Thread(target=abort_on_stop, args=(done,), name="StopWatch", daemon=True).start()
    try:
        with (
            concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="SongPrep") as prep,
            concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="SongFinish") as finisher,
        ):
            preparing = collections.deque(prep.submit(prepare_native_song, t) for t in queue[:_PREP_AHEAD])
            finishing: collections.deque = collections.deque()
            for i, task in enumerate(queue):
                if stopping():
                    break
                prepared = preparing.popleft()
                if i + _PREP_AHEAD < len(queue) and not stopping():
                    preparing.append(prep.submit(prepare_native_song, queue[i + _PREP_AHEAD]))
                try:
                    song = prepared.result()
                except Exception as exc:
                    finisher.submit(fail, task, build_native_task_error_payload(
                        song_name=task_song_name(task), queue_key=task_queue_label(task), exc=exc,
                        trace=traceback.format_exc()))
                    continue
                try:
                    ga_result = run_ga(song, ctx)
                except GpuFatalError:
                    raise
                except Exception as exc:
                    if stop_requested is not None and stop_requested() and is_stop_abort_exception(exc):
                        break
                    finisher.submit(fail, task, build_native_song_error_payload(song, exc=exc,
                                                                                trace=traceback.format_exc()))
                    continue
                while len(finishing) >= _FINISH_BEHIND:  # bounded: finishing songs hold their surfaces
                    finishing.popleft().result()
                finishing.append(finisher.submit(finish, task, song, ga_result))
            for future in preparing:
                future.cancel()
    finally:
        done.set()
