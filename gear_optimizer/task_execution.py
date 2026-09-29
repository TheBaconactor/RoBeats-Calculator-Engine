from __future__ import annotations

import logging
import multiprocessing
import queue
import time

from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.engine.native import NativeOptimizationEngine, NativeOptimizationRequest
from gear_optimizer.solver.native_inflight_config import IN_FLIGHT_SONGS

logger = logging.getLogger(__name__)


class TaskExecutionMixin:
    def _execute_tasks(self, tasks, memory_resume_tracker):
            """Run the queue through the native in-flight engine, then record completion counts."""
            if self._stop_requested_now():
                return
            completed_songs = set()
            self._run_current_song_label = ""
            self._start_hotkeys()

            self._run_sequential(tasks, completed_songs, memory_resume_tracker)

            # Expose completion stats for end-of-iteration throughput reporting.
            try:
                completed = int(self._runtime_completed_count or 0)
                total = int(self._runtime_total_count or 0)
                if total <= 0:
                    total = self._effective_total_tasks(tasks if isinstance(tasks, list) else [])
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
            """Run the current queue through the native in-flight production engine."""
            if self._stop_requested_now():
                return
            if not tasks:
                return

            total_tasks = self._effective_total_tasks(tasks if isinstance(tasks, list) else [])
            inflight_songs = min(IN_FLIGHT_SONGS, len(tasks))

            post_queue = None
            post_proc = None
            try:
                post_queue, post_proc = self._start_post_processor(total_tasks)

                self._progress_counts_driven = True
                if self._progress is not None:
                    self._progress.update_counts(completed=0, total=int(total_tasks))
                self._set_runtime_progress_counts(completed=0, total=int(total_tasks))
                NativeOptimizationEngine().run(
                    NativeOptimizationRequest(
                        tasks=tasks,
                        in_flight_songs=int(inflight_songs),
                        completed_songs=completed_songs,
                        memory_resume_tracker=memory_resume_tracker,
                        post_queue=post_queue,
                        stop_requested=self._stop_requested_now,
                        progress_cb=self._progress_event,
                    )
                )
                return
            except Exception as inflight_err:
                logger.exception("[InFlight] Native in-flight pipeline failed")
                if self._is_fatal_inflight_exception(inflight_err):
                    logger.error(
                        "[InFlight] Fatal GPU runtime failure detected; aborting so the supervisor can restart cleanly.",
                    )
                    raise
                raise RuntimeError(
                    "Native in-flight pipeline failed; no sequential path remains."
                ) from inflight_err
            finally:
                self._progress_counts_driven = False
                self._stop_post_processor(post_queue, post_proc)

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

    def _stop_post_processor(self, post_queue, post_proc):
            sentinel_sent = False
            if post_queue is not None:
                # Bounded post queues (POST_PIPELINE_QUEUE) can be full at shutdown. A single short
                # timeout can miss the sentinel and make the join wait the full timeout.
                deadline = time.perf_counter() + 15.0
                while not sentinel_sent:
                    try:
                        post_queue.put(None, block=True, timeout=0.5)
                        sentinel_sent = True
                    except queue.Full:
                        if post_proc is None or not post_proc.is_alive() or time.perf_counter() >= deadline:
                            break
            if post_proc is not None:
                if not sentinel_sent:
                    logger.warning(
                        "[POST] Failed to enqueue shutdown sentinel in time; forcing post-processor shutdown."
                    )
                post_proc.join(timeout=120.0 if sentinel_sent else 5.0)
            if post_proc is not None and post_proc.is_alive():
                post_proc.terminate()
                post_proc.join(timeout=5.0)
