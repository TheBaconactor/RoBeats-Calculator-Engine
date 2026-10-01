import gc
import logging
import multiprocessing
import os
import re
import sys
import threading
import time
from gear_optimizer.solver.genetic_pipeline import GA_POPULATION_SIZE
from gear_optimizer.core.output import suppress_stdout, restore_stdout, suppress_stderr, restore_stderr
from gear_optimizer.store import schema
from gear_optimizer.core.memory import (
    compute_memory_guard_limit,
    set_memory_watchdog_limit,
    memory_release_requested,
    build_memory_guard_resume_context,
    MemoryGuardResumeTracker,
    restart_process_for_memory_guard,
    MEMORY_GUARD_RESUME_FILE,
)
from gear_optimizer.domain.jobs import (
    effective_task_count,
)
from gear_optimizer.data.exported_game_data_sync import sync_exported_game_data
from gear_optimizer.gamedata import load_gears, load_minis, load_stat_curves
from gear_optimizer.client_update import update_and_restart_client
from gear_optimizer.frontier_client import sync_frontiers_from_server
from gear_optimizer.solver.cpu_work_manager import run_startup_cpu_work
from gear_optimizer.app_stop_control import StopController
from gear_optimizer.ui.progress import (
    ProgressUI as _ProgressUI,
    _progress_ui_enabled_default,
    _stream_is_tty,
)
from gear_optimizer.pipeline.queue_task_coordinator import QueueTaskCoordinator
from gear_optimizer import settings
from gear_optimizer.settings import RunSettings, paths
from gear_optimizer.ui.runtime_ui import RuntimeUiMixin
from gear_optimizer.task_execution import TaskExecutionMixin

logger = logging.getLogger(__name__)


class GearOptimizerApp(RuntimeUiMixin, TaskExecutionMixin):
    def __init__(self):
        self.setup_logging()
        self._stop_control = StopController(bin_dir=str(paths().bin_dir))
        self._stop_requested = self._stop_control.stop_requested_event
        self._force_exit_requested = self._stop_control.force_exit_requested_event
        self._output_enabled = settings.output_enabled()
        ui_stream = getattr(sys, "__stdout__", None) or sys.stdout
        self._stdout_is_tty = _stream_is_tty(ui_stream)
        progress = settings.progress()
        self._progress_enabled = _progress_ui_enabled_default(
            configured_enabled=progress is not False,
            output_enabled=bool(self._output_enabled),
            progress_env_present=progress is not None,
            stream_is_tty=bool(self._stdout_is_tty),
        )
        self._banner_enabled = bool(self._stdout_is_tty)
        self._progress_interval = 0.2
        self._progress_bar_width = 24
        self._progress: _ProgressUI | None = None
        self._orig_stdout = None
        self._orig_stderr = None
        self._progress_counts_driven = False
        self._hotkey_thread: threading.Thread | None = None
        self._hotkeys_enabled = True
        self._run_current_song_label = ""
        self._runtime_status_name = "idle"
        self._stop_poll_interval_sec = 0.05
        self._stop_next_check_monotonic = 0.0
        self._stop_cached_result = False
        self._session_new_records = 0
        self._session_new_record_keys: set[str] = set()
        self._session_new_record_best_by_song: dict[str, int] = {}
        self._runtime_completed_count = 0
        self._runtime_total_count = 0
        self._runtime_failed_count = 0

    def setup_logging(self) -> None:
        from gear_optimizer.core.logging_config import configure_default_logging

        configure_default_logging()

    def request_stop(self, reason: str, *, force: bool = False) -> None:
        try:
            return self._stop_control.request_stop(reason, force=force)
        finally:
            from gear_optimizer.solver.gpu_executor import get_gpu_executor

            gpu_executor = get_gpu_executor()
            if gpu_executor.is_running:
                gpu_executor.request_abort(f"stop requested ({reason})")

    def _stop_requested_now(self) -> bool:
        if self._stop_cached_result:
            return True
        now = time.monotonic()
        if now < float(self._stop_next_check_monotonic):
            return False
        stop_now = bool(self._stop_control.stop_requested_now())
        if stop_now:
            self._stop_cached_result = True
            return True
        self._stop_next_check_monotonic = now + float(self._stop_poll_interval_sec)
        return False

    def _install_signal_handlers(self) -> None:
        return self._stop_control.install_signal_handlers()

    def _materialize_gpu_runtime_on_main_thread(self) -> None:
        """
        Materialize the Taichi/Vulkan GPU runtime once, on the OS main thread.

        Required OS/GPU dispatch-safety boundary (the only kind of branch the
        canonical-path rule permits): ``ti.vulkan`` lowers through MoltenVK on
        macOS, and Taichi acquires a GLFW/Cocoa context inside
        ``VulkanProgramImpl::materialize_runtime``. GLFW/AppKit initialization
        traps (SIGTRAP) unless it runs on the OS main thread. The GPU executor
        owns all *subsequent* GPU command submission on its own thread, but that
        one-time runtime materialization must be pinned to the main thread first.
        This mirrors the hub's ``_materialize_optimizer_runtime_on_main_thread``,
        which is why the live API serves GPU scores on this same Mac without
        trapping.

        Idempotent (guarded by ``is_initialized()``) and completes synchronously
        BEFORE the GPU executor thread is started, giving a strict happens-before
        ordering with no concurrent GPU access (no races). Gated to darwin at the
        call site: Linux/Windows have no main-thread GLFW requirement and keep
        their prior lazy executor-thread init, so this does not add an eager
        startup GPU dependency there. On darwin a materialization failure is a
        genuine GPU-first fatal (the lazy path would otherwise SIGTRAP), so it
        intentionally fails loud rather than being swallowed.
        """
        from gear_optimizer.solver.taichi_gem.runtime import is_initialized

        if is_initialized():
            return
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError(
                "GPU runtime must be materialized on the OS main thread; got thread "
                f"'{threading.current_thread().name}'. On macOS this is fatal: "
                "Taichi/MoltenVK acquires a GLFW/Cocoa context during "
                "materialize_runtime, which traps off the main thread."
            )
        from gear_optimizer.solver.taichi_gem import api as gpu_api
        from gear_optimizer.solver.taichi_gem.runtime import ti

        logger.info("[Startup][GPU] Materializing Taichi/Vulkan runtime on main thread...")
        gpu_api.ensure_ready()
        # Force full runtime materialization here on the main thread (GLFW/Cocoa
        # init) rather than letting it happen lazily on the executor thread.
        ti.sync()
        logger.info("[Startup][GPU] Taichi/Vulkan runtime materialized on main thread.")

    def _configure_execution_and_prewarm(self, multi_start: int) -> None:
        from gear_optimizer.solver.taichi_gem import fields as gpu_fields

        gpu_fields.configure_ga_run_buffers(max_runs=max(1, int(multi_start)), max_genomes=int(GA_POPULATION_SIZE))
        # macOS-only required dispatch-safety boundary: on darwin `ti.vulkan` lowers through
        # MoltenVK and Taichi acquires a GLFW/Cocoa context during materialize_runtime, which
        # traps off the OS main thread. Pin that one-time materialization to the main thread
        # before any GPU executor thread spawns. Placed AFTER configure_ga_run_buffers (which
        # MUST precede the first ensure_fields_allocated) and BEFORE the executor start below /
        # the lazy executor start on the single-song (inflight<=1) task path. On Linux/Windows
        # there is no main-thread requirement, so we leave their startup path exactly as before
        # (lazy init on the executor thread) and do not introduce an eager startup GPU dependency.
        if sys.platform == "darwin":
            self._materialize_gpu_runtime_on_main_thread()
        logger.info("[Startup][GPU] Taichi/Vulkan init starting...")
        from gear_optimizer.solver.gpu_executor import get_gpu_executor

        get_gpu_executor().start(in_process=True)
        logger.info("[Startup][GPU] Taichi/Vulkan init ready.")

    def _set_runtime_progress_counts(
        self,
        *,
        completed: int | None = None,
        total: int | None = None,
        failed: int | None = None,
    ) -> None:
        if completed is not None:
            self._runtime_completed_count = max(0, int(completed))
        if total is not None:
            self._runtime_total_count = max(0, int(total))
        if failed is not None:
            self._runtime_failed_count = max(0, int(failed))

    def run(self) -> int:
        """Run iterations until the queue is done (forever with LoopForever). Returns the process exit status:
        1 when an iteration failed (a song or the pipeline), else 0."""
        multiprocessing.freeze_support()
        self._run_failed = False
        self._install_signal_handlers()
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(line_buffering=True)
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(line_buffering=True)
        try:
            if not self._output_enabled:
                self._orig_stdout = suppress_stdout(True)
                self._orig_stderr = suppress_stderr(True)
            while True:
                if self._stop_requested_now():
                    break
                should_loop = self._run_single_iteration()
                if not should_loop:
                    break
        finally:
            restore_stdout(self._orig_stdout)
            restore_stderr(self._orig_stderr)
        return 1 if self._run_failed else 0

    def _run_single_iteration(self):
        memory_guard_restart = False
        memory_resume_tracker = None
        start_time = time.time()
        loop_forever = False  # Default, updated from config.ini
        graceful_stop = False
        fatal = False
        queued_songs = 0
        queued_tasks = 0
        try:
            if self._stop_requested_now():
                graceful_stop = True
                loop_forever = False
                return False
            update_and_restart_client()
            frontier_sync = sync_frontiers_from_server()
            run = settings.read_run_settings()
            set_memory_watchdog_limit(compute_memory_guard_limit(run))
            db_display_name = paths().database.name
            if self._banner_enabled:
                self._print_banner()
            logger.info(f"[Run] Gear Optimizer started. DB file: {db_display_name}")
            schema.ensure(paths().database)
            logger.info(" >> [ForceGreats] ResponseFrontier")
            loop_forever = run.loop_forever
            sync_exported_game_data()
            curves = load_stat_curves(paths().stats_txt)
            gears = load_gears(paths().gears_csv)
            minis = load_minis(paths().minis_csv)
            song_queue = self._build_song_queue(run)
            queued_songs = len(song_queue)
            logger.info(f"[Run] Queued {len(song_queue)} song(s) for processing.")
            run_startup_cpu_work(
                song_queue=song_queue,
                curves=curves,
                data_root=str(paths().data_dir),
                announce_stream=self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout,
                build_missing=not frontier_sync.enabled,
            )
            self._configure_execution_and_prewarm(run.multi_start)
            memory_resume_tracker = MemoryGuardResumeTracker(MEMORY_GUARD_RESUME_FILE)
            memory_resume_tracker.prime(song_queue, build_memory_guard_resume_context(*self._get_filter_params(run)))
            tasks = self._prepare_tasks(
                song_queue,
                run,
                curves,
                gears,
                minis,
            )
            queued_tasks = self._effective_total_tasks(tasks)
            self._start_progress(queued_tasks)
            self._execute_tasks(tasks, memory_resume_tracker)
            memory_guard_restart = self._memory_guard_restart_needed(memory_resume_tracker)
        except KeyboardInterrupt:
            graceful_stop = True
            loop_forever = False
            if self._force_exit_requested.is_set():
                raise
            try:
                self.request_stop("KeyboardInterrupt")
            except KeyboardInterrupt:
                raise
        except Exception as exc:
            logger.exception("[Run] Iteration failed")
            self._run_failed = True
            if self._is_fatal_inflight_exception(exc):
                # A lost or hung GPU does not come back in this process: stop so the supervisor restarts it.
                logger.error("[Run] Fatal GPU runtime failure; exiting so the supervisor can restart cleanly.")
                fatal = True
        finally:
            self._stop_progress()
            elapsed = time.time() - start_time
            done_msg = f"Run completed in {elapsed:.2f}s"
            logger.info(done_msg)
            try:
                elapsed_h = float(elapsed) / 3600.0 if elapsed and elapsed > 0 else 0.0
            except (ValueError, TypeError):
                elapsed_h = 0.0
            if elapsed_h > 0:
                completed_tasks = getattr(self, "_last_completed_tasks", None)
                if completed_tasks is None:
                    completed_tasks = int(queued_tasks)
                completed_tasks = max(0, int(completed_tasks))
                total_tasks = getattr(self, "_last_total_tasks", None)
                if total_tasks is None:
                    total_tasks = int(queued_tasks)
                total_tasks = max(0, int(total_tasks))
                repeats_est = 1
                try:
                    if int(queued_songs) > 0 and int(queued_tasks) > 0:
                        repeats_est = max(1, int(round(float(queued_tasks) / float(queued_songs))))
                except (ValueError, TypeError):
                    repeats_est = 1
                try:
                    completed_songs_est = int(round(float(completed_tasks) / float(repeats_est)))
                except (ValueError, TypeError):
                    completed_songs_est = int(completed_tasks)
                completed_songs_est = min(int(queued_songs), max(0, int(completed_songs_est)))
                songs_per_h = float(completed_songs_est) / elapsed_h if completed_songs_est > 0 else 0.0
                tasks_per_h = float(completed_tasks) / elapsed_h if completed_tasks > 0 else 0.0
                logger.info(
                    f"[Throughput] Completed {completed_tasks}/{total_tasks} task(s) "
                    f"(queue={queued_songs} song(s)) -> {songs_per_h:.1f} songs/hour, {tasks_per_h:.1f} tasks/hour"
                )
            gc.collect()
        if graceful_stop or self._stop_requested.is_set():
            logger.info("[Shutdown] Exiting by user request.")
            return False
        if fatal:
            return False
        if memory_guard_restart:
            restart_process_for_memory_guard()
            return False  # Process replaced
        elif loop_forever:
            self._handle_loop_restart()
            return True
        else:
            logger.info("LoopForever=FALSE; exiting after completing queue.")
            return False

    def _queue_task_coordinator(self) -> QueueTaskCoordinator:
        """Queue/task logic lives in QueueTaskCoordinator; app state reaches it
        only through these two callables (unit-testable without GPU/DB/app)."""
        return QueueTaskCoordinator(stop_requested_fn=self._stop_requested_now)

    def _get_filter_params(self, run: RunSettings):
        return self._queue_task_coordinator().get_filter_params(run)

    def _build_song_queue(self, run: RunSettings):
        return self._queue_task_coordinator().build_song_queue(run)

    def _normalize_song_label(self, label: str) -> str:
        s = str(label or "").strip()
        if not s:
            return s
        try:
            return re.sub(r"\s*\(Run\s+\d+\s*/\s*\d+\)\s*$", "", s).strip()
        except (ValueError, TypeError, re.error):
            return s

    def _prepare_tasks(
        self,
        song_queue,
        run: RunSettings,
        curves,
        gears,
        minis,
    ):
        return self._queue_task_coordinator().prepare_tasks(song_queue, run, curves, gears, minis)

    @staticmethod
    def _effective_total_tasks(tasks: list) -> int:
        """
        Compute the logical "task" count used for progress + throughput.
        - Non-bundled repeats: each queued tuple is already one task => `len(tasks)`.
        - Bundled repeats: each queued tuple expands into N repeat runs;
          count those runs so the UI doesn't look stuck at 0 until the entire bundle completes.
        """
        return effective_task_count(tasks)

    def _fatal_gpu_errors_enabled(self) -> bool:
        return settings.service_mode()

    def _memory_guard_restart_needed(self, memory_resume_tracker) -> bool:
        if not memory_release_requested():
            return False
        return memory_resume_tracker is not None and memory_resume_tracker.pending_count() > 0

    def _is_fatal_inflight_exception(self, exc: BaseException) -> bool:
        from gear_optimizer.solver.gpu_service import is_fatal_gpu_error

        return self._fatal_gpu_errors_enabled() and is_fatal_gpu_error(exc)

    def _handle_loop_restart(self):
        logger.info("Restarting song scan immediately...")
        try:
            if os.path.exists(MEMORY_GUARD_RESUME_FILE):
                os.remove(MEMORY_GUARD_RESUME_FILE)
                logger.info("[LoopForever] Cleared resume file")
        except (OSError, IOError) as e:
            logging.warning(f"Failed to delete resume file: {e}")
