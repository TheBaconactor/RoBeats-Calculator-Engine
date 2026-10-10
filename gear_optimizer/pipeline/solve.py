"""Songs end to end in this process.

A song: prepare_native_song (incl. the GA-invariant FG static prep) -> run_ga (the GA with its fused FG owner score,
a call on the GPU executor) -> finish_song (decode -> FG plan -> FG materialization -> SongSolve, host only). No per-song
process or pool.

solve_song: one song on the calling thread (the persistent worker).

run_queue: a queue with the GPU going from one GA to the next: while a song's GA runs, a helper thread prepares the
next songs and another finishes the previous ones (on the M4 one GA at a time beats twelve songs in flight:
bench/BASELINE.md). Finished songs go to the run's post-processor, which canonicalizes and stores them on the CPU.
"""

from __future__ import annotations

import collections
import concurrent.futures
import threading
import traceback
from collections.abc import Callable
from typing import Any

from gear_optimizer.domain.jobs import SongTask
from gear_optimizer.pipeline.results import SongSolve

# The GPU song slot of a song's GA runs.
_GA_SLOT = 1
# run_queue: songs prepared ahead of the GA and finishing behind it. Under a GA a song's preparation or finish takes
# about one GA (they share the GIL with the GA's kernel launches; bench/ga_timeline.py), so 2 keeps the GPU on GAs.
_PREP_AHEAD = 2
_FINISH_BEHIND = 2


def _ga_turn(payload: dict, abort_requested: Callable[[], bool]) -> dict:
    """On the GPU owner thread: the song's GA runs, then the FG turn on the payload they select (its FG scores and the
    FG search's board candidates; the search widens with the GA's runs, i.e. the reasoning level)."""
    from gear_optimizer.pipeline.fg import FG_SEARCH_BEAM_PER_GA_RUN, fg_turn
    from gear_optimizer.solver.genetic_pipeline import run_gpu_native_ga_runs_payload_prebuilt

    ga_kwargs = dict(payload)
    fg_scoring_bundle = ga_kwargs.pop("fg_scoring_bundle")
    selected_color = ga_kwargs.pop("selected_color")
    runs_payload = run_gpu_native_ga_runs_payload_prebuilt(**ga_kwargs, abort_requested=abort_requested)
    runs_payload, fg_owner_score = fg_turn(
        runs_payload, song=ga_kwargs["song"], curves=ga_kwargs["curves"], selected_color=selected_color,
        fg_scoring_bundle=fg_scoring_bundle, item_stats=ga_kwargs["item_stats"], slot_start=ga_kwargs["slot_start"],
        slot_count=ga_kwargs["slot_count"], base_fixed_stats_arr=ga_kwargs["base_fixed_stats_arr"],
        beam_width=FG_SEARCH_BEAM_PER_GA_RUN * ga_kwargs["num_runs"],
    )
    return {"runs_payload": runs_payload, "fg_owner_score": fg_owner_score}


def run_ga(song: Any, executor: Any) -> dict:
    """The GA result of a prepared song (prepare_native_song) on the GPU executor (started)."""
    from gear_optimizer.pipeline.ga import ga_payload

    song.runtime.song_slot = _GA_SLOT
    try:
        return executor.call(_ga_turn, ga_payload(song), executor.abort_requested)
    finally:
        song.runtime.song_slot = 0


def finish_song(song: Any, ga_result: Any, progress_tracker=None) -> SongSolve:
    """The SongSolve of a song from its GA result (no GPU work). `progress_tracker` (a run's) judges its records."""
    from gear_optimizer.pipeline.fg import finish_fg

    return finish_fg(song, ga_result, progress_tracker)


def solve_song(task: SongTask, executor: Any) -> SongSolve:
    """The SongSolve of one queue task."""
    from gear_optimizer.pipeline.prepare import prepare_native_song

    song = prepare_native_song(task)
    return finish_song(song, run_ga(song, executor))


def run_queue(
    tasks: list[SongTask],
    executor: Any,
    *,
    post: Callable[[Any], None],
    stop_requested: Callable[[], bool] | None = None,
    progress_cb=None,
) -> None:
    """Solve `tasks` (queue tasks; SongRepeats are separate tasks); post each SongSolve or error payload in queue order.

    A stop request or a memory release takes no further task (the next run's queue begins with them); a stop request
    also aborts the GA in progress. Songs past their GA still finish. A GpuFatalError (GPU init failed, a GA past its
    watchdog) ends the run: the process cannot use its GPU any more. Any other error fails that song only."""
    from gear_optimizer.core.memory import memory_release_requested
    from gear_optimizer.pipeline.prepare import prepare_native_song
    from gear_optimizer.pipeline.progress import ProgressTracker, song_error_payload, task_error_payload
    from gear_optimizer.solver.gpu_executor import GpuFatalError, is_stop_abort_exception

    progress = ProgressTracker()

    def stopping() -> bool:
        return bool((stop_requested is not None and stop_requested()) or memory_release_requested())

    def abort_on_stop(done: threading.Event) -> None:
        while not done.wait(0.05):
            if stop_requested():
                executor.request_abort("stop requested")
                return

    # The finisher thread posts every task, so they are posted in queue order.
    def fail(item: dict) -> None:
        post(item)
        progress.emit_error_item_progress(progress_cb, item)

    def finish(song: Any, ga_result: Any) -> None:
        try:
            post(finish_song(song, ga_result, progress))
        except Exception as exc:
            fail(song_error_payload(song, exc=exc, trace=traceback.format_exc()))
            return
        progress.emit_done_song_progress(progress_cb, song)

    queue = tasks
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
                    finisher.submit(fail, task_error_payload(
                        song_name=task.song_name, queue_key=task.label, exc=exc, trace=traceback.format_exc()))
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
                    finisher.submit(fail, song_error_payload(song, exc=exc, trace=traceback.format_exc()))
                    continue
                while len(finishing) >= _FINISH_BEHIND:  # bounded: finishing songs hold their surfaces
                    finishing.popleft().result()
                finishing.append(finisher.submit(finish, song, ga_result))
            for future in preparing:
                future.cancel()
    finally:
        done.set()
