"""Songs end to end in this process.

A song: prepare_native_song (incl. the GA-invariant FG static prep) -> run_ga (the GA with its fused FG owner score,
a call on the GPU executor) -> finish_song (decode -> FG plan -> FG materialization -> SongSolve, host only). No per-song
process or pool.

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


def _ga_turn(payload: dict, abort_requested: Callable[[], bool]) -> dict:
    """On the GPU owner thread: the song's GA runs, then the fused FG owner score of the payload they select."""
    from gear_optimizer.solver.genetic_pipeline import (
        run_gpu_native_ga_runs_payload_prebuilt,
        score_fused_fg_from_selected_payload,
    )

    ga_kwargs = dict(payload)
    fg_scoring_bundle = ga_kwargs.pop("fg_scoring_bundle")
    runs_payload = run_gpu_native_ga_runs_payload_prebuilt(**ga_kwargs, abort_requested=abort_requested)
    fg_owner_score = score_fused_fg_from_selected_payload(
        runs_payload=runs_payload, fg_scoring_bundle=fg_scoring_bundle, song=ga_kwargs["song"],
        curves=ga_kwargs["curves"], cfg_data=ga_kwargs["cfg_data"])
    return {"runs_payload": runs_payload, "fg_owner_score": fg_owner_score}


def run_ga(song: Any, executor: Any) -> dict:
    """The GA result of a prepared song (prepare_native_song) on the GPU executor (started)."""
    from gear_optimizer.solver.native_inflight_pipeline_ga import InflightGAPipeline

    song.runtime.song_slot = _GA_SLOT
    try:
        InflightGAPipeline.prepare_submit(song)
        return executor.call(_ga_turn, InflightGAPipeline.build_payload(song), executor.abort_requested)
    finally:
        song.runtime.song_slot = 0


def finish_song(song: Any, ga_result: Any, progress_tracker=None) -> SongSolve:
    """The SongSolve of a song from its GA result (no GPU work). `progress_tracker` (a run's) judges its records."""
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
        apply_fg_materialization_result(song, materialize_fg_request(build_fg_materialization_request(song)),
                                        progress_tracker=progress_tracker)
    finally:
        release_fg_song_surfaces(song)
    return song_solve(song)


def solve_song(task: tuple, executor: Any) -> SongSolve:
    """The SongSolve of one queue task (an app task tuple)."""
    from gear_optimizer.solver.native_inflight_lifecycle import prepare_native_song

    song = prepare_native_song(task)
    return finish_song(song, run_ga(song, executor))


def run_queue(
    tasks: list[tuple],
    executor: Any,
    *,
    post: Callable[[Any], None],
    completed_songs: set[str],
    memory_resume_tracker=None,
    stop_requested: Callable[[], bool] | None = None,
    progress_cb=None,
) -> None:
    """Solve `tasks` (queue tasks; SongRepeats are separate tasks); post each SongSolve or error payload in queue order.

    A task is marked completed once finished (also when it failed: its error went to `post`); a stop request or a
    memory release leaves the unfinished tasks pending (the resume journal keeps them). A stop request also aborts the
    GA in progress (its song stays pending); songs past their GA still finish. A GpuFatalError (GPU init failed, a GA
    past its watchdog) ends the run: the process cannot use its GPU any more. Any other error fails that song only."""
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
    from gear_optimizer.solver.gpu_executor import GpuFatalError

    progress = ProgressTracker()

    def stopping() -> bool:
        return bool((stop_requested is not None and stop_requested()) or memory_release_requested())

    def abort_on_stop(done: threading.Event) -> None:
        while not done.wait(0.05):
            if stop_requested():
                executor.request_abort("stop requested")
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
            post(finish_song(song, ga_result, progress))
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
                # A song's records are judged against the run's bests: the stored ones and the earlier songs'.
                progress.seed_valid_baseline(song.config.db_key, best_score=song.runtime.db.db_best_score,
                                             best_fg=song.runtime.db.db_best_fg_score,
                                             baseline_valid=song.runtime.db.db_baseline_valid)
                try:
                    ga_result = run_ga(song, executor)
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
