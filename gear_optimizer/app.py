import gc
import logging
import multiprocessing
import sys
import threading
import time
from gear_optimizer.core.cpu_affinity import solve_worker_count
from gear_optimizer.core.output import suppress_stdout, restore_stdout, suppress_stderr, restore_stderr
from gear_optimizer.store import schema
from gear_optimizer.core.memory import compute_memory_guard_limit
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
from gear_optimizer.pipeline.workers import solve_queue
from gear_optimizer import settings
from gear_optimizer.settings import RunSettings, paths
from gear_optimizer.ui.runtime_ui import RuntimeUiMixin

logger = logging.getLogger(__name__)


class GearOptimizerApp(RuntimeUiMixin):
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
        self._stop_next_check_monotonic = 0.0
        self._stop_cached_result = False
        self._session_new_records = 0
        self._session_new_record_best_by_song: dict[str, int] = {}
        self._completed_tasks = 0

    def setup_logging(self) -> None:
        from gear_optimizer.core.logging_config import configure_default_logging

        configure_default_logging()

    def request_stop(self, reason: str, *, force: bool = False) -> None:
        """Stop the run: the workers take no further song and abort the GAs in progress."""
        self._stop_control.request_stop(reason, force=force)

    def _stop_requested_now(self) -> bool:
        if self._stop_cached_result:
            return True
        now = time.monotonic()
        if now < self._stop_next_check_monotonic:
            return False
        if self._stop_control.stop_requested_now():
            self._stop_cached_result = True
            return True
        self._stop_next_check_monotonic = now + 0.05
        return False

    def run(self) -> int:
        """Run iterations until the queue is done (forever with LoopForever). Returns the process exit status:
        1 when an iteration failed (a song or the pipeline), else 0."""
        multiprocessing.freeze_support()
        self._run_failed = False
        self._stop_control.install_signal_handlers()
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

    def _run_single_iteration(self) -> bool:
        """Scan the charts and solve the queue; whether to run another iteration (LoopForever)."""
        start_time = time.time()
        tasks = []
        loop_forever = False  # Default, updated from config.ini
        graceful_stop = False
        fatal = False
        queued_songs = 0
        self._completed_tasks = 0
        try:
            if self._stop_requested_now():
                return False
            update_and_restart_client()
            frontier_sync = sync_frontiers_from_server()
            run = settings.read_run_settings()
            if self._banner_enabled:
                self._print_banner()
            logger.info(f"[Run] Gear Optimizer started. DB file: {paths().database.name}")
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
            tasks = build_queue(run, context)
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
            self._solve(tasks, run)
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
            elapsed = time.time() - start_time
            logger.info(f"Run completed in {elapsed:.2f}s")
            if elapsed > 0:
                elapsed_h = elapsed / 3600.0
                completed = self._completed_tasks
                # Songs are estimated as tasks (capped by the queue): repeats are not told apart.
                songs = min(queued_songs, completed)
                logger.info(
                    f"[Throughput] Completed {completed}/{len(tasks)} task(s) (queue={queued_songs} song(s)) -> "
                    f"{songs / elapsed_h:.1f} songs/hour, {completed / elapsed_h:.1f} tasks/hour"
                )
            gc.collect()
        if graceful_stop or self._stop_requested.is_set():
            logger.info("[Shutdown] Exiting by user request.")
            return False
        if fatal:
            return False
        if loop_forever:
            logger.info("Restarting song scan immediately...")
            return True
        logger.info("LoopForever=FALSE; exiting after completing queue.")
        return False

    def _solve(self, tasks: list, run: RunSettings) -> None:
        """Solve and store the queue on the run's workers (config.ini Workers, else cpu_affinity.solve_worker_count).
        Raises after the run when a song failed."""
        if not tasks:
            return
        failed: list[str] = []

        def song_failed(label: str) -> None:
            failed.append(label)
            self._song_failed(label)

        self._start_progress(len(tasks))
        self._start_hotkeys()
        try:
            solve_queue(
                tasks,
                workers=min(run.workers or solve_worker_count(), len(tasks)),
                memory_limit_bytes=compute_memory_guard_limit(run),
                stop_requested=self._stop_requested_now,
                on_done=self._song_stored,
                on_failed=song_failed,
            )
        finally:
            self._stop_hotkeys()
            self._stop_progress()
        if failed:
            raise RuntimeError(f"{len(failed)} song(s) failed in this run (see the [Workers] errors)")

    def _is_fatal_inflight_exception(self, exc: BaseException) -> bool:
        from gear_optimizer.solver.gpu_executor import is_fatal_gpu_error

        return settings.service_mode() and is_fatal_gpu_error(exc)
