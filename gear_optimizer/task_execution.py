from __future__ import annotations

import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import logging
import multiprocessing
import os
import queue
import threading
import time

from gear_optimizer.core.constants import BIN_DIR
from gear_optimizer.core.fallback_monitor import warn_fallback
from gear_optimizer.core.memory import memory_release_requested
from gear_optimizer.core.parsing import TRUTHY_ENV_VALUES, env_get, env_int, truthy
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.core.utils import safe_int
from gear_optimizer.domain.jobs import (
    task_cfg_dict,
    task_difficulty,
    task_extras,
    task_file_path,
    task_ref_arrays,
    task_song_name,
    task_tuple_to_shared_context,
    task_with_status_queue,
)

logger = logging.getLogger(__name__)


def safe_process_song_task(task):
    """
    Compatibility entrypoint for calculate-only / legacy process-pool execution.

    Keep the old per-song pipeline out of the production native in-flight import
    path; load it only when a compatibility branch actually executes.
    """
    from gear_optimizer.legacy.song_processor_adapter import safe_process_song_task as _safe_process_song_task

    return _safe_process_song_task(task)


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
            # Hotkeys need access to the current queue and completion set.
            self._run_tasks_ref = tasks if isinstance(tasks, list) else None
            self._run_completed_ref = completed_songs
            self._run_current_song_label = ""
            self._start_hotkeys()

            if len(tasks) > 1 and max_workers > 1:
                self._run_parallel(
                    tasks, max_workers, completed_songs, memory_resume_tracker, manager, status_queue, status_thread
                )
            else:
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
            """Run the current queue through native in-flight when supported, else direct per-song processing."""
            if self._stop_requested_now():
                return
            if not tasks:
                return

            cfg_dict0 = task_cfg_dict(tasks[0]) if tasks else {}
            ie0 = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}
            raw_meta_finder = ie0.get("MetaFinder", ie0.get("metafinder", True)) if isinstance(ie0, dict) else True
            meta_finder_enabled = str(raw_meta_finder).strip().lower() in TRUTHY_ENV_VALUES

            if not bool(meta_finder_enabled):
                logger.info(
                    "[InFlight] Native pipeline skipped: calculate-only / gem-only mode keeps the direct per-song path."
                )
                self._consume_results(
                    (safe_process_song_task(task) for task in tasks),
                    completed_songs=completed_songs,
                    memory_resume_tracker=memory_resume_tracker,
                    total_tasks=self._effective_total_tasks(tasks if isinstance(tasks, list) else []),
                )
                return

            song_task_count = max(0, int(len(tasks)))
            total_tasks = self._effective_total_tasks(tasks if isinstance(tasks, list) else [])
            inflight_songs = 0
            try:
                ie = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}
                raw = ie.get("inflightsongs", 0) if isinstance(ie, dict) else 0
                inflight_songs = safe_int(raw, 0)
            except (TypeError, ValueError):
                inflight_songs = 0
            inflight_runner = getattr(self, "_inflight_runner", None)
            if inflight_runner is None:
                from gear_optimizer.app_inflight_runner import InflightRunner

                inflight_runner = InflightRunner(self)
                try:
                    self._inflight_runner = inflight_runner
                except Exception as e:
                    logger.debug(f"task_execution:_run_sequential: {e}")
            inflight_instances = inflight_runner.get_effective_inflight_instances(cfg_dict0)

            if inflight_songs <= 0:
                inflight_songs = min(12, max(1, song_task_count))
                try:
                    logger.debug(f"[InFlight] Sequential pipeline removed; defaulting InFlightSongs={int(inflight_songs)}.")
                except Exception as e:
                    logger.debug(f"task_execution:_run_sequential: {e}")
            elif song_task_count > 1 and int(inflight_songs) < 2:
                inflight_songs = min(12, max(2, song_task_count))
                try:
                    logger.debug(
                        "[InFlight] Sequential pipeline removed; "
                        f"raising InFlightSongs to {int(inflight_songs)} for multi-song queue."
                    )
                except Exception as e:
                    logger.debug(f"task_execution:_run_sequential: {e}")

            inflight_songs = max(1, min(int(inflight_songs), int(song_task_count)))

            post_queue = None
            post_proc = None
            inflight_fatal_gpu_err = False
            try:
                post_queue, post_proc = self._start_post_processor(total_tasks)

                from gear_optimizer.solver.native_inflight_orchestrator import run_native_inflight_song_pipeline

                self._progress_counts_driven = True
                if self._progress is not None:
                    self._progress.update_counts(completed=0, total=int(total_tasks))
                else:
                    self._tui_publish(
                        song="",
                        status=str(getattr(self, "_runtime_status_name", "") or "running"),
                        completed=0,
                        total=int(total_tasks),
                        failed=int(getattr(self, "_runtime_failed_count", 0) or 0),
                        new_records=int(getattr(self, "_session_new_records", 0) or 0),
                    )
                self._set_runtime_progress_counts(completed=0, total=int(total_tasks))
                if int(inflight_instances) > 1 and len(tasks) > 1:
                    self._run_dual_process_inflight(
                        tasks,
                        inflight_instances=int(inflight_instances),
                        inflight_songs=int(inflight_songs),
                        completed_songs=completed_songs,
                        memory_resume_tracker=memory_resume_tracker,
                        post_queue=post_queue,
                        total_tasks=int(total_tasks),
                    )
                else:
                    run_native_inflight_song_pipeline(
                        tasks,
                        in_flight_songs=int(inflight_songs),
                        completed_songs=completed_songs,
                        memory_resume_tracker=memory_resume_tracker,
                        post_queue=post_queue,
                        total_tasks=int(total_tasks),
                        stop_requested=self._stop_requested_now,
                        progress_cb=self._progress_event,
                        bundle_completed_cb=self._maybe_mark_robeatsmeta_song_batch_computed,
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

    def _run_dual_process_inflight(
            self,
            tasks: list,
            *,
            inflight_instances: int,
            inflight_songs: int,
            completed_songs: set[str],
            memory_resume_tracker,
            post_queue,
            total_tasks: int,
        ) -> None:
            if self._stop_requested_now():
                return
            if not isinstance(tasks, list) or not tasks:
                return

            try:
                instances = max(2, int(inflight_instances or 2))
            except Exception as e:
                logger.debug(f"task_execution:_run_dual_process_inflight: {e}")
                instances = 2
            instances = max(2, min(instances, 8))

            try:
                from gear_optimizer.solver.dual_process_inflight import (
                    dual_process_inflight_worker_main,
                    recommend_dual_process_inflight_thread_overrides,
                    shard_inflight_tasks,
                )
                from gear_optimizer.solver.native_inflight_support import _task_key
            except Exception as exc:
                raise RuntimeError(f"Dual-process in-flight import failure: {type(exc).__name__}: {exc}") from exc

            shards = shard_inflight_tasks(tasks, instances=instances)
            # Drop empty shards to avoid spawning idle processes when the queue is small.
            shard_items: list[tuple[int, list[tuple]]] = [(i, s) for i, s in enumerate(shards) if s]
            if len(shard_items) <= 1:
                # Nothing to gain; fall back to current single-process execution.
                from gear_optimizer.solver.native_inflight_orchestrator import run_native_inflight_song_pipeline

                run_native_inflight_song_pipeline(
                    tasks,
                    in_flight_songs=max(1, int(inflight_songs or 1)),
                    completed_songs=completed_songs,
                    memory_resume_tracker=memory_resume_tracker,
                    post_queue=post_queue,
                    total_tasks=int(total_tasks),
                    stop_requested=self._stop_requested_now,
                    progress_cb=self._progress_event,
                    bundle_completed_cb=self._maybe_mark_robeatsmeta_song_batch_computed,
                )
                return

            # Shared immutable context (pickle once per worker, not once per task).
            run_context = task_tuple_to_shared_context(tasks[0])
            shared_ctx = (
                run_context.cfg_dict,
                run_context.paths,
                run_context.ref_arrays,
                run_context.all_gears,
                run_context.all_minis,
                run_context.gears_by_name,
                run_context.minis_by_name,
                run_context.use_evo_db,
                run_context.auto_buff,
                run_context.ga_depth,
                run_context.parallel_workers,
                run_context.fg_debug,
            )

            # Coordinator-owned completion state.
            task_key_to_song_name: dict[str, str] = {}
            for t in tasks:
                try:
                    task_key_to_song_name[_task_key(t)] = task_song_name(t)
                except Exception as e:
                    logger.debug(f"task_execution:_run_dual_process_inflight: {e}")
                    continue

            try:
                mp_ctx = multiprocessing.get_context("spawn")
            except ValueError:
                mp_ctx = multiprocessing.get_context()

            control_queue = mp_ctx.Queue()
            stop_event = mp_ctx.Event()
            initial_completed_keys = list(completed_songs) if isinstance(completed_songs, set) else []

            processes: list[multiprocessing.Process] = []
            for shard_idx, shard in shard_items:
                work_items: list[tuple] = []
                for t in shard:
                    try:
                        fp = task_file_path(t)
                        song_name = task_song_name(t)
                        diff = task_difficulty(t)
                    except Exception as e:
                        logger.debug(f"task_execution:_run_dual_process_inflight: {e}")
                        continue
                    extras = list(task_extras(t))
                    work_items.append((fp, song_name, diff, extras))

                inflight_limit = max(1, min(int(inflight_songs or 1), int(len(shard))))
                thread_overrides = recommend_dual_process_inflight_thread_overrides(
                    run_context.cfg_dict if isinstance(run_context.cfg_dict, dict) else None,
                    inflight_limit=int(inflight_limit),
                    instances=int(instances),
                    logical_cpus=os.cpu_count() or 1,
                )

                try:
                    prep_workers = env_int(
                        "INFLIGHT_PREP_WORKERS", safe_int(thread_overrides.get("INFLIGHT_PREP_WORKERS"), 1)
                    )
                    decode_workers = env_int(
                        "INFLIGHT_DECODE_WORKERS", safe_int(thread_overrides.get("INFLIGHT_DECODE_WORKERS"), 1)
                    )
                    fg_workers = env_int("INFLIGHT_FG_WORKERS", safe_int(thread_overrides.get("INFLIGHT_FG_WORKERS"), 1))
                    fg_prep_workers = env_int(
                        "INFLIGHT_FG_PREP_WORKERS", safe_int(thread_overrides.get("INFLIGHT_FG_PREP_WORKERS"), 1)
                    )
                    db_prefetch_workers = env_int(
                        "INFLIGHT_DB_PREFETCH_WORKERS", safe_int(thread_overrides.get("INFLIGHT_DB_PREFETCH_WORKERS"), 1)
                    )
                    logger.debug(
                        "[InFlight][Dual] worker=%s shard=%s tasks=%s InFlightSongs=%s "
                        "Prep=%s Decode=%s FG=%s FGPrep=%s FGDBPrefetch=%s",
                        int(shard_idx),
                        int(shard_idx),
                        int(len(shard)),
                        int(inflight_songs),
                        int(prep_workers),
                        int(decode_workers),
                        int(fg_workers),
                        int(fg_prep_workers),
                        int(db_prefetch_workers),
                    )
                except Exception as e:
                    logger.debug(f"task_execution:_run_dual_process_inflight: {e}")

                p = mp_ctx.Process(
                    target=dual_process_inflight_worker_main,
                    kwargs={
                        "worker_index": int(shard_idx),
                        "instances": int(instances),
                        "shared_ctx": shared_ctx,
                        "work_items": work_items,
                        "inflight_songs": int(inflight_songs),
                        "post_queue": post_queue,
                        "control_queue": control_queue,
                        "stop_event": stop_event,
                        "thread_overrides": thread_overrides,
                        "initial_completed_keys": initial_completed_keys,
                    },
                    daemon=True,
                    name=f"InFlightDualWorker[{int(shard_idx)}]",
                )
                p.start()
                processes.append(p)

            fatal_err: str | None = None
            fatal_trace: str | None = None

            def _set_fatal(err: str, trace: str | None = None) -> None:
                nonlocal fatal_err, fatal_trace
                if fatal_err is not None:
                    return
                fatal_err = str(err or "").strip() or "unknown fatal"
                fatal_trace = str(trace or "").strip() or None
                try:
                    stop_event.set()
                except Exception as e:
                    logger.debug(f"task_execution:_set_fatal: {e}")

            def _handle_msg(msg: dict) -> None:
                nonlocal fatal_err, fatal_trace
                kind = str(msg.get("type") or "").strip().lower()
                if kind == "progress":
                    try:
                        self._progress_event(
                            completed_delta=int(msg.get("completed_delta", 0) or 0),
                            failed_delta=int(msg.get("failed_delta", 0) or 0),
                            record_info=msg.get("record_info") if isinstance(msg.get("record_info"), dict) else None,
                        )
                    except Exception as e:
                        logger.debug(f"task_execution:_handle_msg: {e}")
                    return
                if kind == "completed":
                    try:
                        task_key = str(msg.get("task_key") or "").strip()
                    except Exception as e:
                        logger.debug(f"task_execution:_handle_msg: {e}")
                        task_key = ""
                    if task_key:
                        try:
                            completed_songs.add(task_key)
                        except Exception as e:
                            logger.debug(f"task_execution:_handle_msg: {e}")
                        song_name = task_key_to_song_name.get(task_key)
                        if memory_resume_tracker and song_name:
                            try:
                                memory_resume_tracker.mark_completed(str(song_name))
                            except Exception as e:
                                logger.debug(f"task_execution:_handle_msg: {e}")
                        try:
                            self._maybe_mark_robeatsmeta_song_batch_computed(str(task_key), completed_songs)
                        except Exception as e:
                            logger.debug(f"task_execution:_handle_msg: {e}")
                    return
                if kind == "fatal":
                    err = str(msg.get("error") or "worker fatal").strip()
                    trace = msg.get("traceback")
                    _set_fatal(err, str(trace) if trace else None)
                    return
                if kind == "exited":
                    return

            start_t0 = time.perf_counter()
            try:
                while True:
                    if self._stop_requested_now():
                        _set_fatal("Stop requested")
                    if memory_release_requested():
                        logger.warning("[MemoryGuard] Dual-process stop requested by soft limit.")
                        _set_fatal("MemoryGuard soft limit")

                    alive = False
                    for p in processes:
                        if p.is_alive():
                            alive = True
                            continue
                        if p.exitcode not in (None, 0):
                            _set_fatal(f"Worker {p.name} exited with code {p.exitcode}")
                    if not alive:
                        break

                    try:
                        msg = control_queue.get(timeout=0.1)
                    except queue.Empty:
                        msg = None
                    except Exception as e:
                        logger.debug(f"task_execution:_handle_msg: {e}")
                        msg = None
                    if isinstance(msg, dict):
                        _handle_msg(msg)
                    if fatal_err is not None:
                        break
            finally:
                # Drain remaining messages so completions/progress are reflected before shutdown.
                while True:
                    try:
                        msg = control_queue.get_nowait()
                    except Exception as e:
                        logger.debug(f"task_execution:_handle_msg: {e}")
                        break
                    if isinstance(msg, dict):
                        _handle_msg(msg)

                # Graceful join, then terminate stragglers.
                for p in processes:
                    try:
                        p.join(timeout=10.0)
                    except Exception as e:
                        logger.debug(f"task_execution:_handle_msg: {e}")
                for p in processes:
                    if not p.is_alive():
                        continue
                    try:
                        p.terminate()
                    except Exception as e:
                        logger.debug(f"task_execution:_handle_msg: {e}")
                    try:
                        p.join(timeout=5.0)
                    except Exception as e:
                        logger.debug(f"task_execution:_handle_msg: {e}")

            if fatal_err is not None:
                if fatal_trace:
                    logger.error("[InFlight][Dual] Fatal traceback:\n%s", fatal_trace)
                raise RuntimeError(f"[InFlight][Dual] {fatal_err}")

            # Throughput snapshot (tasks/hour) for this dual-process section.
            try:
                elapsed_s = max(1e-9, float(time.perf_counter() - start_t0))
                processed = 0
                try:
                    processed = len(completed_songs) if isinstance(completed_songs, set) else 0
                except Exception as e:
                    logger.debug(f"task_execution:_handle_msg: {e}")
                    processed = 0
                per_h = float(processed) * 3600.0 / float(elapsed_s) if processed > 0 else 0.0
                logger.debug(
                    "[InFlight][Dual] Completed %s tasks in %.2fs (%.1f tasks/hour)", int(processed), elapsed_s, per_h
                )
            except Exception as e:
                logger.debug(f"task_execution:_handle_msg: {e}")

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

    def _run_parallel(
            self, tasks, max_workers, completed_songs, memory_resume_tracker, manager, status_queue, status_thread
        ):
            ref_arrays = None
            try:
                ref_arrays = task_ref_arrays(tasks[0]) if tasks else None
            except Exception as e:
                logger.debug(f"task_execution:_run_parallel: {e}")
                ref_arrays = None
            remaining_tasks = list(tasks)
            max_pool_retries = 3
            broken_pool_failures = 0
            current_worker_cap = max_workers

            # Start GPU executor for centralized GPU ownership
            gpu_executor = None
            try:
                from gear_optimizer.solver.gpu_executor import get_gpu_executor

                gpu_executor = get_gpu_executor()
                gpu_executor.start()
                try:
                    init_timeout = float(env_get("GPU_EXECUTOR_INIT_TIMEOUT_SEC", "30"))
                except Exception as e:
                    logger.debug(f"task_execution:_run_parallel: {e}")
                    init_timeout = 30.0
                if not gpu_executor.wait_until_ready(timeout=init_timeout):
                    err = getattr(gpu_executor, "last_init_error", None)
                    msg = "[GPU Executor] Taichi init failed or timed out; falling back to single-process in-flight"
                    if err:
                        msg = f"{msg} ({err})"
                    warn_fallback("app.gpu_executor.single_process", msg, fatal=False)
                    try:
                        gpu_executor.stop()
                    except Exception as e:
                        logger.debug(f"task_execution:_run_parallel: {e}")
                    gpu_executor = None
                if gpu_executor is not None and gpu_executor.is_running:
                    logger.debug("[GPU Executor] Started for parallel song processing")
            except Exception as e:
                logger.error(f"[GPU Executor] Failed to start: {e} - forcing single-process in-flight")
                gpu_executor = None

            # Without the shared GPU executor, multi-process "direct GPU" workers can fight
            # over Vulkan contexts and waste work via resets/crashes. Prefer correctness:
            # fall back to the single-process native in-flight pipeline.
            if gpu_executor is None or not getattr(gpu_executor, "is_running", False):
                current_worker_cap = 1

            throughput_t0 = time.perf_counter()
            while remaining_tasks:
                if self._stop_requested_now():
                    break
                completed_offset = len(completed_songs)
                effective_workers = max(1, min(len(remaining_tasks), current_worker_cap))

                try:
                    mp_ctx = multiprocessing.get_context("spawn")
                except ValueError:
                    mp_ctx = multiprocessing.get_context()

                if effective_workers == 1:
                    self._run_sequential(remaining_tasks, completed_songs, memory_resume_tracker)
                    break

                try:
                    # Register workers with GPU executor (if available)
                    worker_registrations = []
                    secondary_gpu_proc = None
                    secondary_gpu_req_q = None
                    if gpu_executor and gpu_executor.is_running:
                        # Optional: start a secondary GPU executor (separate process) for hybrid/dual-GPU systems.
                        # Each worker is pinned to exactly one executor/request-queue, so we never need Taichi to
                        # drive multiple Vulkan devices from a single process.
                        secondary_workers = 0
                        try:
                            secondary_workers = int(env_get("GPU_EXECUTOR_SECONDARY_WORKERS", "0") or 0)
                        except Exception as e:
                            logger.debug(f"task_execution:_run_parallel: {e}")
                            secondary_workers = 0
                        secondary_workers = max(0, min(int(secondary_workers), int(effective_workers)))
                        primary_workers = int(effective_workers) - int(secondary_workers)

                        # Primary executor registrations (typically discrete GPU).
                        for _ in range(primary_workers):
                            worker_id, req_q, resp_q = gpu_executor.register_worker()
                            worker_registrations.append((worker_id, req_q, resp_q))

                        # Secondary executor registrations (typically iGPU).
                        if secondary_workers > 0:
                            try:
                                from gear_optimizer.solver.gpu_executor import run_gpu_executor_server

                                secondary_gpu_req_q = mp_ctx.Queue()
                                secondary_resp_map = {}
                                secondary_regs = []
                                for wid in range(int(secondary_workers)):
                                    resp_q = mp_ctx.Queue()
                                    secondary_resp_map[int(wid)] = resp_q
                                    secondary_regs.append((int(wid), secondary_gpu_req_q, resp_q))

                                secondary_ready = mp_ctx.Event()
                                secondary_status_q = mp_ctx.Queue()
                                visible_device = str(
                                    env_get("GPU_EXECUTOR_SECONDARY_VULKAN_VISIBLE_DEVICE", "0") or ""
                                ).strip()

                                secondary_gpu_proc = mp_ctx.Process(
                                    target=run_gpu_executor_server,
                                    args=(secondary_gpu_req_q, secondary_resp_map),
                                    kwargs={
                                        "ready_event": secondary_ready,
                                        "ready_queue": secondary_status_q,
                                        "vulkan_visible_device": visible_device,
                                        "label": "Secondary",
                                    },
                                    name="GpuExecutorSecondaryProcess",
                                )
                                secondary_gpu_proc.start()

                                try:
                                    init_timeout = float(env_get("GPU_EXECUTOR_INIT_TIMEOUT_SEC", "30"))
                                except Exception as e:
                                    logger.debug(f"task_execution:_run_parallel: {e}")
                                    init_timeout = 30.0
                                if not secondary_ready.wait(timeout=max(0.0, float(init_timeout))):
                                    logger.warning(
                                        "[GPU Executor][Secondary] Init timed out; disabling secondary executor for this pool"
                                    )
                                    try:
                                        secondary_gpu_proc.terminate()
                                    except Exception as e:
                                        logger.debug(f"task_execution:_run_parallel: {e}")
                                    secondary_gpu_proc = None
                                    secondary_gpu_req_q = None
                                else:
                                    ok = True
                                    err = None
                                    try:
                                        status = secondary_status_q.get(timeout=1.0)
                                        ok = bool(status.get("ok", False)) if isinstance(status, dict) else True
                                        err = status.get("error") if isinstance(status, dict) else None
                                    except Exception as e:
                                        logger.debug(f"task_execution:_run_parallel: {e}")
                                        ok = True
                                        err = None

                                    if not ok:
                                        msg = "[GPU Executor][Secondary] Taichi init failed; disabling secondary executor for this pool"
                                        if err:
                                            msg = f"{msg} ({err})"
                                        logger.warning(msg)
                                        try:
                                            secondary_gpu_proc.terminate()
                                        except Exception as e:
                                            logger.debug(f"task_execution:_run_parallel: {e}")
                                        secondary_gpu_proc = None
                                        secondary_gpu_req_q = None
                                    else:
                                        worker_registrations.extend(secondary_regs)
                                        logger.info(
                                            f"[GPU Executor][Secondary] Started with {secondary_workers} worker(s) "
                                            f"(TAICHI_VULKAN_VISIBLE_DEVICE={visible_device or 'default'})"
                                        )
                            except Exception as e:
                                logger.error(f"[GPU Executor][Secondary] Failed to start: {e}")
                                secondary_gpu_proc = None
                                secondary_gpu_req_q = None

                    # Use module-level initializer (local functions can't be pickled for spawn)
                    if worker_registrations:
                        reg_counter = mp_ctx.Value("i", 0)
                        reg_lock = mp_ctx.Lock()

                        executor = concurrent.futures.ProcessPoolExecutor(
                            max_workers=effective_workers,
                            mp_context=mp_ctx,
                            initializer=_gpu_worker_initializer,
                            initargs=(worker_registrations, reg_counter, reg_lock),
                        )
                        try:
                            future_map = {
                                executor.submit(safe_process_song_task, t): self._task_queue_label(t)
                                for t in remaining_tasks
                            }
                            self._consume_results(
                                concurrent.futures.as_completed(future_map),
                                future_map=future_map,
                                propagate_broken_pool=True,
                                completed_songs=completed_songs,
                                completed_offset=completed_offset,
                                memory_resume_tracker=memory_resume_tracker,
                                total_tasks=len(tasks),
                                throughput_t0=throughput_t0,
                                ref_arrays=ref_arrays,
                            )

                            if self._stop_requested_now():
                                break
                            if memory_release_requested():
                                logger.warning("[MemoryGuard] Stopping parallel loop after soft limit.")
                                break
                        finally:
                            try:
                                executor.shutdown(wait=True, cancel_futures=bool(self._stop_requested.is_set()))
                            except Exception as e:
                                logger.debug(f"task_execution:_run_parallel: {e}")

                            if secondary_gpu_req_q is not None and secondary_gpu_proc is not None:
                                try:
                                    from gear_optimizer.solver.gpu_executor import send_gpu_executor_shutdown

                                    send_gpu_executor_shutdown(secondary_gpu_req_q)
                                except Exception as e:
                                    logger.debug(f"task_execution:_run_parallel: {e}")
                                try:
                                    secondary_gpu_proc.join(timeout=10.0)
                                except Exception as e:
                                    logger.debug(f"task_execution:_run_parallel: {e}")
                                if secondary_gpu_proc.is_alive():
                                    try:
                                        secondary_gpu_proc.terminate()
                                    except Exception as e:
                                        logger.debug(f"task_execution:_run_parallel: {e}")
                    else:
                        # Fallback: no GPU executor, workers use direct GPU (may conflict)
                        executor = concurrent.futures.ProcessPoolExecutor(max_workers=effective_workers, mp_context=mp_ctx)
                        try:
                            future_map = {
                                executor.submit(safe_process_song_task, t): self._task_queue_label(t)
                                for t in remaining_tasks
                            }
                            self._consume_results(
                                concurrent.futures.as_completed(future_map),
                                future_map=future_map,
                                propagate_broken_pool=True,
                                completed_songs=completed_songs,
                                completed_offset=completed_offset,
                                memory_resume_tracker=memory_resume_tracker,
                                total_tasks=len(tasks),
                                throughput_t0=throughput_t0,
                                ref_arrays=ref_arrays,
                            )

                            if self._stop_requested_now():
                                break
                            if memory_release_requested():
                                logger.warning("[MemoryGuard] Stopping parallel loop after soft limit.")
                                break
                        finally:
                            try:
                                executor.shutdown(wait=True, cancel_futures=bool(self._stop_requested.is_set()))
                            except Exception as e:
                                logger.debug(f"task_execution:_run_parallel: {e}")

                except BrokenProcessPool as bpp:
                    broken_pool_failures += 1
                    warn_msg = f"[Auto-Recover] Process pool broke; attempt {broken_pool_failures}/{max_pool_retries}. Reason: {bpp}"
                    logger.error(warn_msg)

                    # Restart status infra
                    self._cleanup_resources(status_queue, status_thread, manager)
                    manager = multiprocessing.Manager()
                    status_queue = manager.Queue()
                    status_thread = threading.Thread(target=self._status_listener, args=(status_queue,), daemon=True)
                    status_thread.start()

                    # Rebuild remaining tasks
                    remaining_songs = [t for t in tasks if self._task_queue_label(t) not in completed_songs]
                    remaining_tasks = []
                    for t in remaining_songs:
                        remaining_tasks.append(task_with_status_queue(t, status_queue))

                    current_worker_cap = max(1, effective_workers - 1)

                    if broken_pool_failures >= max_pool_retries:
                        logger.error("[Auto-Recover] Max retries hit; retrying through native in-flight pipeline.")
                        self._run_sequential(remaining_tasks, completed_songs, memory_resume_tracker)
                        break
                    continue

                break

            # Stop GPU executor
            if gpu_executor and gpu_executor.is_running:
                try:
                    gpu_executor.stop()
                except Exception as e:
                    logger.debug(f"task_execution:_run_parallel: {e}")

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
                    # current in-flight work (running tasks cannot be canceled).
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
