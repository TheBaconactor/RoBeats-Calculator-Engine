from __future__ import annotations

import logging
import multiprocessing
import os
import time

from gear_optimizer.core.constants import BIN_DIR
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.parsing import env_get, truthy
from gear_optimizer.core.utils import safe_int
from gear_optimizer.domain.jobs import task_cfg_dict
from gear_optimizer.engine.native import NativeOptimizationEngine, NativeOptimizationRequest

logger = logging.getLogger(__name__)


class TaskExecutionMixin:
    def _status_listener(self, q):
            while True:
                try:
                    msg = q.get()
                except (EOFError, BrokenPipeError, OSError):
                    break
                if msg is None:
                    break
                self._handle_status_message(msg)

    def _execute_tasks(
            self,
            tasks,
            eval_cpu_limit,
            parallel_workers,
            memory_resume_tracker,
            loop_forever,
        ):
            """Execute tasks with automatic parallelism."""
            if self._stop_requested_now():
                return
            inflight_songs = 0
            try:
                cfg_dict0 = task_cfg_dict(tasks[0]) if tasks else {}
                ie = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}
                if isinstance(ie, dict):
                    inflight_songs = safe_int(ie.get("inflightsongs", 0), 0)
            except (TypeError, ValueError):
                inflight_songs = 0

            logical_cpus = os.cpu_count() or 1
            available_cpus = logical_cpus
            if eval_cpu_limit and eval_cpu_limit > 0:
                available_cpus = max(1, min(logical_cpus, eval_cpu_limit))

            # GPU-only policy: run songs in a single process and use in-flight scheduling
            # for parallelism instead of per-song process pools.
            max_workers = 1

            if available_cpus != logical_cpus:
                logger.info(f"EvalCPUCores cap applied: using {available_cpus} of {logical_cpus} cores.")

            if inflight_songs > 1 and len(tasks) > 1:
                logger.debug(f"[InFlight] Requested: InFlightSongs={inflight_songs} (single-process).")

            logger.info(
                f"Parallel plan -> songs: {len(tasks)}, concurrent workers: {max_workers}, cores per song: {parallel_workers}"
            )
            logger.info(f"Using {available_cpus} logical CPU cores")

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
                if loop_forever:
                    logger.warning("[MemoryGuard] LoopForever enabled; scheduling automatic restart.")

            if memory_resume_tracker:
                memory_resume_tracker.finalize(memory_release_requested())
            self._stop_hotkeys()

    def _run_sequential(self, tasks, completed_songs, memory_resume_tracker):
            """Run the current queue through the native in-flight production engine."""
            if self._stop_requested_now():
                return
            if not tasks:
                return

            cfg_dict0 = task_cfg_dict(tasks[0]) if tasks else {}
            song_task_count = max(0, int(len(tasks)))
            total_tasks = self._effective_total_tasks(tasks if isinstance(tasks, list) else [])
            inflight_songs = 0
            try:
                ie = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}
                raw = ie.get("inflightsongs", 0) if isinstance(ie, dict) else 0
                inflight_songs = safe_int(raw, 0)
            except (TypeError, ValueError):
                inflight_songs = 0

            if inflight_songs <= 0:
                inflight_songs = min(12, max(1, song_task_count))
                try:
                    logger.debug(f"[InFlight] Defaulting native InFlightSongs={int(inflight_songs)}.")
                except Exception as e:
                    logger.debug(f"task_execution:_run_sequential: {e}")
            elif song_task_count > 1 and int(inflight_songs) < 2:
                inflight_songs = min(12, max(2, song_task_count))
                try:
                    logger.debug(f"[InFlight] Raising native InFlightSongs to {int(inflight_songs)} for multi-song queue.")
                except Exception as e:
                    logger.debug(f"task_execution:_run_sequential: {e}")

            inflight_songs = max(1, min(int(inflight_songs), int(song_task_count)))

            post_queue = None
            post_proc = None
            inflight_fatal_gpu_err = False
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
                inflight_fatal_gpu_err = self._is_fatal_inflight_exception(inflight_err)
                logger.error(f"[InFlight] Disabled: {type(inflight_err).__name__}: {inflight_err}")
                if inflight_fatal_gpu_err:
                    logger.error(
                        "[InFlight] Fatal GPU runtime failure detected; aborting so the supervisor can restart cleanly.",
                    )
                try:
                    import traceback

                    tb = traceback.format_exc()
                    try:
                        logging.error("[InFlight] Traceback:\\n" + tb)
                    except Exception as e:
                        logger.debug(f"task_execution:_run_sequential: {e}")
                    try:
                        trace_path = os.path.join(BIN_DIR, "inflight_disabled_traceback.log")
                        ts = time.strftime("%Y-%m-%d %H:%M:%S")
                        with open(trace_path, "a", encoding="utf-8") as fh:
                            fh.write(f"\n[{ts}] {type(inflight_err).__name__}: {inflight_err}\n")
                            fh.write(tb)
                    except Exception as e:
                        logger.debug(f"task_execution:_run_sequential: {e}")
                    if truthy(env_get("INFLIGHT_PRINT_TRACE", "0")):
                        try:
                            logger.error(tb)
                        except Exception as e:
                            logger.debug(f"task_execution:_run_sequential: {e}")
                except Exception as e:
                    logger.debug(f"task_execution:_run_sequential: {e}")
                if inflight_fatal_gpu_err:
                    raise
                raise RuntimeError(
                    "Native in-flight pipeline failed; no sequential path remains."
                ) from inflight_err
            finally:
                self._progress_counts_driven = False
                self._stop_post_processor(post_queue, post_proc)

    def _start_post_processor(self, total_tasks: int):
            from gear_optimizer.pipeline.post_processor import run_post_processor

            post_queue_size = safe_int(env_get("POST_PIPELINE_QUEUE", 0), 0)
            post_queue_maxsize = 0 if post_queue_size <= 0 else max(1, post_queue_size)
            post_queue = multiprocessing.Queue(maxsize=post_queue_maxsize)
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
            try:
                if post_queue is not None:
                    # Bounded post queues (POST_PIPELINE_QUEUE) can be full at shutdown. A single short
                    # timeout can miss the sentinel and make the join wait the full timeout.
                    t0 = time.perf_counter()
                    while True:
                        try:
                            post_queue.put(None, block=True, timeout=0.5)
                            sentinel_sent = True
                            break
                        except Exception as e:
                            logger.debug(f"task_execution:_stop_post_processor: {e}")
                            try:
                                if post_proc is None or not post_proc.is_alive():
                                    break
                            except Exception as e:
                                logger.debug(f"task_execution:_stop_post_processor: {e}")
                                break
                            if (time.perf_counter() - t0) >= 15.0:
                                break
                            continue
            except Exception as e:
                logger.debug(f"task_execution:_stop_post_processor: {e}")
            try:
                if post_proc is not None:
                    if not sentinel_sent:
                        try:
                            logger.warning(
                                "[POST] Failed to enqueue shutdown sentinel in time; forcing post-processor shutdown."
                            )
                        except Exception as e:
                            logger.debug(f"task_execution:_stop_post_processor: {e}")
                    post_proc.join(timeout=120.0 if sentinel_sent else 5.0)
            except Exception as e:
                logger.debug(f"task_execution:_stop_post_processor: {e}")
            try:
                if post_proc is not None and post_proc.is_alive():
                    post_proc.terminate()
                    post_proc.join(timeout=5.0)
            except Exception as e:
                logger.debug(f"task_execution:_stop_post_processor: {e}")

