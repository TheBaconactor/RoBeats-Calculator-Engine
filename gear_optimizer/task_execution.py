from __future__ import annotations

from concurrent.futures.process import BrokenProcessPool
import logging
import multiprocessing
import os
import time

from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.parsing import env_get
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.utils import safe_int
from gear_optimizer.pipeline.song_processor import safe_process_song_task

logger = logging.getLogger(__name__)

def _gpu_worker_initializer(registrations, counter, lock):
    """
    Initialize GPU worker mode in spawned process.

    Each spawned process claims a unique (worker_id, response_queue) registration.
    """
    from gear_optimizer.solver.gpu_executor import set_gpu_worker_mode

    with lock:
        idx = int(counter.value)
        counter.value = idx + 1

    if idx < 0 or idx >= len(registrations):
        # Defensive fallback: disable GPU worker mode if we ran out of registrations.
        return

    worker_id, request_queue, response_queue = registrations[idx]
    set_gpu_worker_mode(worker_id, request_queue, response_queue)
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
            manager,
            status_queue,
            status_thread,
            loop_forever,
        ):
            """Execute tasks through the direct skyline path."""
            if self._stop_requested_now():
                return
            logical_cpus = os.cpu_count() or 1
            available_cpus = logical_cpus
            if eval_cpu_limit and eval_cpu_limit > 0:
                available_cpus = max(1, min(logical_cpus, eval_cpu_limit))

            # GPU-only policy: run songs in a single process through skyline.
            max_workers = 1

            if available_cpus != logical_cpus:
                logger.info(f"EvalCPUCores cap applied: using {available_cpus} of {logical_cpus} cores.")

            logger.info(
                f"Parallel plan -> songs: {len(tasks)}, concurrent workers: {max_workers}, cores per song: {parallel_workers}"
            )
            logger.info(f"Using {available_cpus} logical CPU cores")

            completed_songs = set()
            # Hotkeys need access to the current queue and completion set.
            self._run_tasks_ref = tasks if isinstance(tasks, list) else None
            self._run_completed_ref = completed_songs
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
            self._run_tasks_ref = None
            self._run_completed_ref = None
            self._stop_hotkeys()

    def _run_sequential(self, tasks, completed_songs, memory_resume_tracker):
            """Run the current queue through the skyline song path."""
            if self._stop_requested_now():
                return
            if not tasks:
                return

            logger.info("[Skyline] Running direct exact skyline task path.")
            self._consume_results(
                (safe_process_song_task(task) for task in tasks),
                completed_songs=completed_songs,
                memory_resume_tracker=memory_resume_tracker,
                total_tasks=self._effective_total_tasks(tasks if isinstance(tasks, list) else []),
            )
            return

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

    def _consume_results(
            self,
            results_iter,
            future_map=None,
            propagate_broken_pool=False,
            completed_songs=None,
            completed_offset=0,
            memory_resume_tracker=None,
            total_tasks=0,
            throughput_t0: float | None = None,
            ref_arrays=None,
        ):
            completed = completed_offset
            failed = 0
            total = total_tasks or 0  # approximate if unknown
            t0 = float(throughput_t0) if throughput_t0 is not None else time.perf_counter()
            if self._progress is not None:
                self._progress.update_counts(completed=completed, total=total)
            else:
                self._tui_publish(
                    song="",
                    status=str(self._runtime_status_name or "running"),
                    completed=int(completed or 0),
                    total=int(total or 0),
                    failed=int(failed or 0),
                    new_records=int(self._session_new_records or 0),
                )
            self._set_runtime_progress_counts(completed=completed, total=total, failed=failed)
            self._progress_counts_driven = True

            for item in results_iter:
                if self._stop_requested_now():
                    # Best-effort: cancel pending futures so the pool can wind down after
                    # current GPU work finishes.
                    if isinstance(future_map, dict):
                        for f in list(future_map.keys()):
                            try:
                                f.cancel()
                            except Exception as e:
                                logger.debug(f"task_execution:_consume_results: {e}")
                    break
                completed += 1
                if future_map:
                    future = item
                    song_name = future_map.get(future, "Unknown")
                    try:
                        res = future.result()
                    except Exception as task_err:
                        failed += 1
                        err_msg = f"[{completed}/{total}] FAILED: {song_name} - {type(task_err).__name__}: {task_err}"
                        logger.error(err_msg)
                        self._progress_on_result(None, completed=completed, total=total, failed_delta=1)
                        if propagate_broken_pool and isinstance(task_err, BrokenProcessPool):
                            raise
                        continue

                    # safe_process_song_task can return an error payload; treat it as a failure here too.
                    if isinstance(res, dict) and "_error" in res:
                        failed += 1
                        err_type = res.get("_error_type") or type(res.get("_error")).__name__
                        err_msg = f"[{completed}/{total}] FAILED: {song_name} - {err_type}: {res.get('_error')}"
                        logger.error(err_msg)
                        if res.get("_trace"):
                            logger.error(res.get("_trace"))
                        self._progress_on_result(None, completed=completed, total=total, failed_delta=1)
                        continue
                else:
                    res = item
                    if isinstance(res, dict) and "_error" in res:
                        failed += 1
                        err_name = res.get("_queue_label") or res.get("_song_name") or res.get("song")
                        err_type = res.get("_error_type") or type(res.get("_error")).__name__
                        err_msg = f"[{completed}/{total}] FAILED: {err_name} - {err_type}: {res.get('_error')}"
                        logger.error(err_msg)
                        if res.get("_trace"):
                            logger.error(res.get("_trace"))
                        self._progress_on_result(None, completed=completed, total=total, failed_delta=1)
                        continue

                song_name = res.get("song", "Unknown")
                task_label = res.get("_queue_label") or res.get("_queue_key") or song_name
                task_key = res.get("_queue_key") or task_label or song_name
                if completed_songs is not None and task_key:
                    completed_songs.add(task_key)
                if memory_resume_tracker and song_name:
                    memory_resume_tracker.mark_completed(song_name)
                self._maybe_mark_robeatsmeta_song_batch_computed(str(task_label or song_name or ""), completed_songs)

                self._progress_on_result(res, completed=completed, total=total)

                if memory_release_requested():
                    logger.warning("[MemoryGuard] Early stop in consume_results")
                    break

                logger.info(f"[{completed}/{total}] Completed: {task_label}")
                emit_profile_event(
                    component="app",
                    event="task_completed",
                    song_key=str(task_key) if task_key else None,
                    metrics={
                        "completed": int(completed),
                        "total": int(total),
                        "failed": int(failed),
                    },
                )
                processed = int(completed - completed_offset)
                if processed > 0:
                    try:
                        elapsed_s = max(1e-9, float(time.perf_counter() - t0))
                        per_h = float(processed) * 3600.0 / float(elapsed_s)
                        avg_s = float(elapsed_s) / float(processed)
                        rem = max(0, int(total) - int(completed)) if total > 0 else 0
                        eta_s = float(rem) * avg_s if rem > 0 else 0.0
                        if rem > 0:
                            logger.info(
                                f"[Throughput] {per_h:.1f} tasks/hour (avg {avg_s:.2f}s/task, ETA {eta_s / 60.0:.1f}m)"
                            )
                        else:
                            logger.info(f"[Throughput] {per_h:.1f} tasks/hour (avg {avg_s:.2f}s/task)")
                        emit_profile_event(
                            component="app",
                            event="throughput_snapshot",
                            metrics={
                                "processed": int(processed),
                                "completed": int(completed),
                                "total": int(total),
                                "failed": int(failed),
                                "tasks_per_hour": float(per_h),
                                "avg_task_sec": float(avg_s),
                                "remaining": int(rem),
                                "eta_sec": float(eta_s),
                            },
                        )
                    except Exception as e:
                        logger.debug(f"task_execution:_consume_results: {e}")
                logger.info("=" * 60)
                logger.info(f"PROCESSING SONG: {task_label}")
                logger.info("=" * 60)

                # DB Stuff - Only save valid entries (non-zero score, has gear/minis)
                persisted = res.get("persist_entries")
                if persisted:
                    # Filter: only save entries with score > 0 and at least some gear
                    def _force_score_hint(entry: dict) -> int:
                        try:
                            force_obj = entry.get("force")
                        except Exception as e:
                            logger.debug(f"task_execution:_force_score_hint: {e}")
                            force_obj = None
                        if not isinstance(force_obj, dict):
                            return 0
                        try:
                            s = int(force_obj.get("score", 0) or 0)
                        except Exception as e:
                            logger.debug(f"task_execution:_force_score_hint: {e}")
                            s = 0
                        if s > 0:
                            return s
                        det = force_obj.get("details") or {}
                        if not isinstance(det, dict):
                            return 0
                        fg = det.get("ForceGreats") or {}
                        if not isinstance(fg, dict):
                            return 0
                        try:
                            return int(fg.get("final_score", 0) or 0)
                        except Exception as e:
                            logger.debug(f"task_execution:_force_score_hint: {e}")
                            return 0

                    valid_entries = []
                    for e in persisted:
                        if not isinstance(e, dict):
                            continue
                        if not (e.get("gear") or e.get("minis")):
                            continue
                        try:
                            score_i = int(e.get("score", 0) or 0)
                        except Exception as e:
                            logger.debug(f"task_execution:_force_score_hint: {e}")
                            score_i = 0
                        try:
                            fg_i = int(e.get("fg_score", 0) or 0)
                        except Exception as e:
                            logger.debug(f"task_execution:_force_score_hint: {e}")
                            fg_i = 0
                        if max(score_i, fg_i, _force_score_hint(e)) <= 0:
                            continue
                        valid_entries.append(e)
                    if valid_entries:
                        self._async_db_saver.submit(
                            res["song"],
                            valid_entries,
                            meta={
                                "file_path": res.get("file_path"),
                                "cfg_dict": res.get("cfg_dict"),
                                "db_key": res.get("db_key"),
                                "ref_arrays": ref_arrays,
                            },
                        )
                    else:
                        logger.warning(f"[DB] Skipped save for {res['song']}: no valid entries (score=0 or empty loadout)")
                        # Still count as a processed run for per-song attempt counters.
                        try:
                            self._async_db_saver.submit(
                                res["song"],
                                [],
                                meta={
                                    "db_key": res.get("db_key") or res["song"],
                                    "_processed_run": True,
                                    "file_path": res.get("file_path"),
                                    "cfg_dict": res.get("cfg_dict"),
                                    "ref_arrays": ref_arrays,
                                },
                            )
                        except Exception as e:
                            logger.debug(f"task_execution:_force_score_hint: {e}")
                elif res.get("db_payload"):
                    pl = res["db_payload"]
                    # Only save if score > 0 and has gear/minis (prevents tainting on errors)
                    if pl.get("score", 0) > 0 and (pl.get("gear") or pl.get("minis")):
                        self._async_db_saver.submit(
                            res["song"],
                            [
                                {
                                    "score": pl.get("score", 0),
                                    "fg_score": pl.get("fg_score", 0),
                                    "gear": pl.get("gear", []),
                                    "minis": pl.get("minis", []),
                                    "details": pl.get("details", {}),
                                    "force": pl.get("force"),
                                }
                            ],
                            meta={
                                "file_path": res.get("file_path"),
                                "cfg_dict": res.get("cfg_dict"),
                                "db_key": res.get("db_key"),
                                "ref_arrays": ref_arrays,
                            },
                        )
                    else:
                        logger.warning(f"[DB] Skipped save for {res['song']}: invalid payload (score=0 or empty loadout)")
                        # Still count as a processed run for per-song attempt counters.
                        try:
                            self._async_db_saver.submit(
                                res["song"],
                                [],
                                meta={
                                    "db_key": res.get("db_key") or res["song"],
                                    "_processed_run": True,
                                    "file_path": res.get("file_path"),
                                    "cfg_dict": res.get("cfg_dict"),
                                    "ref_arrays": ref_arrays,
                                },
                            )
                        except Exception as e:
                            logger.debug(f"task_execution:_force_score_hint: {e}")

                log_content = (res.get("log") or "").strip()
                if log_content:
                    # Worker/post-processor output is printed locally; avoid duplicating large logs.
                    pass

                # Cleanup
                res["log"] = None
                if "persist_entries" in res:
                    res["persist_entries"] = None
                if "db_payload" in res:
                    res["db_payload"] = None

                # Surface async DB failures promptly so the optimizer can't silently keep running
                # without persistence.
                self._async_db_saver.raise_if_failed()

            self._progress_counts_driven = False

            if failed > 0:
                logger.warning(f"[SUMMARY] {failed}/{total} songs failed.")
