from __future__ import annotations

import logging
import multiprocessing

from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.settings import persistent_worker

logger = logging.getLogger(__name__)


class TaskExecutionMixin:
    def _execute_tasks(self, tasks, memory_resume_tracker):
            """Solve the queue (_run_sequential), then record completion counts."""
            if self._stop_requested_now():
                return
            completed_songs = set()
            self._run_current_song_label = ""
            self._start_hotkeys()
            try:
                self._run_sequential(tasks, completed_songs, memory_resume_tracker)
            finally:
                # Completion stats for end-of-iteration throughput reporting, and the resume state, also when songs
                # failed (_run_sequential raises after the run).
                try:
                    completed = int(self._runtime_completed_count or 0)
                    total = int(self._runtime_total_count or 0)
                    if total <= 0:
                        total = len(tasks)
                    self._last_completed_tasks = max(0, int(completed))
                    self._last_total_tasks = max(0, int(total))
                except (TypeError, ValueError):
                    self._last_completed_tasks = None
                    self._last_total_tasks = None

                if memory_release_requested():
                    logger.warning("[MemoryGuard] Soft limit reached; pending songs saved for resume.")
                    logger.warning("[MemoryGuard] Scheduling automatic restart if pending songs remain.")

                if memory_resume_tracker:
                    memory_resume_tracker.finalize(memory_release_requested())
                self._stop_hotkeys()

    def _run_sequential(self, tasks, completed_songs, memory_resume_tracker):
            """Solve the current queue in this process (_run_direct) with the run's post-processor storing the results.
            Raises when the run fails, or after the run when any song failed (the post-processor counts and logs them)."""
            if self._stop_requested_now():
                return
            if not tasks:
                return

            total_tasks = len(tasks)

            post_queue = None
            post_proc = None
            songs_failed = False
            try:
                post_queue, post_proc = self._start_post_processor(total_tasks)

                self._progress_counts_driven = True
                if self._progress is not None:
                    self._progress.update_counts(completed=0, total=int(total_tasks))
                self._set_runtime_progress_counts(completed=0, total=int(total_tasks))
                self._run_direct(tasks, post_queue, completed_songs, memory_resume_tracker)
            finally:
                self._progress_counts_driven = False
                songs_failed = not self._stop_post_processor(post_queue, post_proc)
            if songs_failed:
                raise RuntimeError("song(s) failed in this run (see the [POST] FAILED lines)")

    def _run_direct(self, tasks, post_queue, completed_songs, memory_resume_tracker) -> None:
            """The queue solved in this process (pipeline.solve.run_queue), posting to the run's post-processor."""
            from gear_optimizer.pipeline.solve import run_queue
            from gear_optimizer.solver.gpu_executor import get_gpu_executor

            executor = get_gpu_executor()
            executor.start()
            try:
                run_queue(
                    tasks,
                    executor,
                    post=post_queue.put,
                    completed_songs=completed_songs,
                    memory_resume_tracker=memory_resume_tracker,
                    stop_requested=self._stop_requested_now,
                    progress_cb=self._progress_event,
                )
            finally:
                if not persistent_worker():
                    executor.stop()  # persists Taichi's offline kernel cache

    def _start_post_processor(self, total_tasks: int):
            from gear_optimizer.pipeline.post_processor import run_post_processor

            post_queue = multiprocessing.Queue()
            post_proc = multiprocessing.Process(
                target=run_post_processor,
                args=(post_queue, int(total_tasks)),
                daemon=True,
                name="SongPostProcessor",
            )
            post_proc.start()
            return post_queue, post_proc

    def _stop_post_processor(self, post_queue, post_proc) -> bool:
            """Stop the post-processor once it handled every message; True when it stored every song it was given
            without a failure (or never started)."""
            if post_proc is None:
                return True
            post_queue.put(None)
            post_proc.join(timeout=120.0)
            if post_proc.is_alive():
                post_proc.terminate()
                post_proc.join(timeout=5.0)
            return post_proc.exitcode == 0
