import gc
import logging
import multiprocessing
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
    restart_process_for_memory_guard,
)
from gear_optimizer.domain.jobs import SharedRunContext
from gear_optimizer.data.exported_game_data_sync import sync_exported_game_data
from gear_optimizer.gamedata import load_gears, load_minis, stat_curves
from gear_optimizer.client_update import update_and_restart_client
from gear_optimizer.frontier_client import sync_frontiers_from_server
from gear_optimizer.solver.cpu_work_manager import run_startup_cpu_work
from gear_optimizer.app_stop_control import StopController
from gear_optimizer.ui.progress import (
    ProgressUI as _ProgressUI,
    _progress_ui_enabled_default,
    _stream_is_tty,
)
from gear_optimizer.pipeline.queue import build_queue
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
        stdout_is_tty = _stream_is_tty(getattr(sys, "__stdout__", None) or sys.stdout)
        progress = settings.progress()
        self._progress_enabled = _progress_ui_enabled_default(
            configured_enabled=progress is not False,
            output_enabled=self._output_enabled,
            progress_env_present=progress is not None,
            stream_is_tty=stdout_is_tty,
        )
        self._banner_enabled = stdout_is_tty
        self._progress: _ProgressUI | None = None
        self._orig_stdout = None
        self._orig_stderr = None
        self._hotkey_thread: threading.Thread | None = None
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
        # The last run's completed and total tasks (_execute_tasks), for the throughput line.
        self._last_completed_tasks = 0
        self._last_total_tasks = 0
        self._passes_begun = 0

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
        if now < self._stop_next_check_monotonic:
            return False
        if self._stop_control.stop_requested_now():
            self._stop_cached_result = True
            return True
        self._stop_next_check_monotonic = now + self._stop_poll_interval_sec
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

        gpu_fields.configure_ga_run_buffers(max_runs=max(1, multi_start), max_genomes=GA_POPULATION_SIZE)
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

        get_gpu_executor().start()
        logger.info("[Startup][GPU] Taichi/Vulkan init ready.")

    def _set_runtime_progress_counts(
        self,
        *,
        completed: int | None = None,
        total: int | None = None,
        failed: int | None = None,
    ) -> None:
        if completed is not None:
            self._runtime_completed_count = max(0, completed)
        if total is not None:
            self._runtime_total_count = max(0, total)
        if failed is not None:
            self._runtime_failed_count = max(0, failed)

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
        start_time = time.time()
        # A run relaunched after a memory-guard restart continues its pass; every other iteration begins one.
        relaunched_pass = settings.pass_started() if not self._passes_begun else None
        self._passes_begun += 1
        pass_started = relaunched_pass if relaunched_pass is not None else start_time
        tasks = []
        loop_forever = False  # Default, updated from config.ini
        graceful_stop = False
        fatal = False
        queued_songs = 0
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
            curves = stat_curves()
            gears = load_gears(paths().gears_csv)
            minis = load_minis(paths().minis_csv)
            context = SharedRunContext(
                multi_start=run.multi_start, curves=curves, gears=gears, minis=minis, ga_depth=run.search_depth
            )
            tasks = build_queue(run, context, solved_before=relaunched_pass)
            queued_songs = len({task.song_name for task in tasks})
            charts_by_mode: dict[str, list[str]] = {}
            for task in tasks:
                charts_by_mode.setdefault(task.mode, []).append(task.file_path)
            run_startup_cpu_work(
                charts_by_mode=charts_by_mode,
                curves=curves,
                announce_stream=self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout,
                build_missing=not frontier_sync.enabled,
            )
            self._configure_execution_and_prewarm(run.multi_start)
            self._start_progress(len(tasks))
            self._execute_tasks(tasks)
            memory_guard_restart = memory_release_requested() and self._last_completed_tasks < len(tasks)
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
            logger.info(f"Run completed in {elapsed:.2f}s")
            if elapsed > 0:
                elapsed_h = elapsed / 3600.0
                completed, total = self._last_completed_tasks, self._last_total_tasks
                # Songs are estimated as tasks (capped by the queue): repeats are not told apart.
                songs = min(queued_songs, completed)
                logger.info(
                    f"[Throughput] Completed {completed}/{total} task(s) (queue={queued_songs} song(s)) -> "
                    f"{songs / elapsed_h:.1f} songs/hour, {completed / elapsed_h:.1f} tasks/hour"
                )
            gc.collect()
        if graceful_stop or self._stop_requested.is_set():
            logger.info("[Shutdown] Exiting by user request.")
            return False
        if fatal:
            return False
        if memory_guard_restart:
            restart_process_for_memory_guard(pass_started)
            return False  # Process replaced
        elif loop_forever:
            logger.info("Restarting song scan immediately...")
            return True
        else:
            logger.info("LoopForever=FALSE; exiting after completing queue.")
            return False

    def _fatal_gpu_errors_enabled(self) -> bool:
        return settings.service_mode()

    def _is_fatal_inflight_exception(self, exc: BaseException) -> bool:
        from gear_optimizer.solver.gpu_executor import is_fatal_gpu_error

        return self._fatal_gpu_errors_enabled() and is_fatal_gpu_error(exc)
