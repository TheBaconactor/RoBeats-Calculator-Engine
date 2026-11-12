import gc
import logging
import multiprocessing
import sys
import time
from gear_optimizer.core.cpu_affinity import solve_worker_count
from gear_optimizer.core.output import suppress_stdout, restore_stdout, suppress_stderr, restore_stderr
from gear_optimizer.store import schema
from gear_optimizer.core.memory import compute_memory_guard_limit
from gear_optimizer.domain.jobs import SharedRunContext
from gear_optimizer.data.game_export import load_catalog
from gear_optimizer.gamedata import stat_curves
from gear_optimizer.frontier.startup_prebuild import run_startup_cpu_work
from gear_optimizer.app_stop_control import StopController
from gear_optimizer.core.logging_config import configure_default_logging
from gear_optimizer.gpu.executor import is_fatal_gpu_error
from gear_optimizer.pipeline.queue import build_queue
from gear_optimizer.pipeline.workers import solve_queue
from gear_optimizer import settings
from gear_optimizer.settings import RunSettings, paths
from gear_optimizer.ui.progress import progress_bar_enabled
from gear_optimizer.ui.runtime_ui import RunConsole

logger = logging.getLogger(__name__)


class GearOptimizerApp:
    def __init__(self):
        configure_default_logging()
        self._stop_control = StopController(bin_dir=str(paths().bin_dir))
        self._output_enabled = settings.output_enabled()
        tty = sys.__stdout__.isatty()
        self._banner_enabled = tty
        progress = progress_bar_enabled(settings.progress(), verbose=self._output_enabled, tty=tty)
        self._console = RunConsole(self._stop_control, progress=progress)
        self._orig_stdout = None
        self._orig_stderr = None

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
            while not self._stop_control.stop_requested_now():
                if not self._run_single_iteration():
                    break
        finally:
            restore_stdout(self._orig_stdout)
            restore_stderr(self._orig_stderr)
        return 1 if self._run_failed else 0

    def _run_single_iteration(self) -> bool:
        """Scan the charts and solve the queue; whether to run another iteration (LoopForever)."""
        start_time = time.time()
        tasks = []
        loop_forever = False
        graceful_stop = False
        fatal = False
        queued_songs = 0
        self._console.completed = 0
        stream = self._orig_stdout or sys.__stdout__
        try:
            run = settings.read_run_settings()
            if self._banner_enabled:
                stream.write("RoBeats Calculator Engine\n")
                stream.flush()
            logger.info(f"[Run] Gear Optimizer started. DB file: {paths().database.name}")
            schema.ensure(paths().database)
            logger.info(" >> [ForceGreats] ResponseFrontier")
            loop_forever = run.loop_forever
            curves = stat_curves()
            catalog = load_catalog(paths().game_export)
            context = SharedRunContext(multi_start=run.multi_start, curves=curves, gears=catalog.gears,
                                       minis=catalog.minis, ga_depth=run.search_depth)
            tasks = build_queue(run, context)
            queued_songs = len({task.song_name for task in tasks})
            charts_by_mode: dict[str, list[str]] = {}
            for task in tasks:
                charts_by_mode.setdefault(task.mode, []).append(task.file_path)
            run_startup_cpu_work(
                charts_by_mode=charts_by_mode,
                curves=curves,
                announce_stream=stream,
            )
            self._solve(tasks, run, stream)
        except KeyboardInterrupt:
            graceful_stop = True
            loop_forever = False
            if self._stop_control.force_exit_requested_event.is_set():
                raise
            self._stop_control.request_stop("KeyboardInterrupt")
        except Exception as exc:
            logger.exception("[Run] Iteration failed")
            self._run_failed = True
            if settings.service_mode() and is_fatal_gpu_error(exc):
                # A lost or hung GPU does not come back in this process: stop so the supervisor restarts it.
                logger.error("[Run] Fatal GPU runtime failure; exiting so the supervisor can restart cleanly.")
                fatal = True
        finally:
            elapsed = time.time() - start_time
            logger.info(f"Run completed in {elapsed:.2f}s")
            if elapsed > 0:
                elapsed_h = elapsed / 3600.0
                completed = self._console.completed
                # Songs are estimated as tasks (capped by the queue): repeats are not told apart.
                songs = min(queued_songs, completed)
                logger.info(
                    f"[Throughput] Completed {completed}/{len(tasks)} task(s) (queue={queued_songs} song(s)) -> "
                    f"{songs / elapsed_h:.1f} songs/hour, {completed / elapsed_h:.1f} tasks/hour"
                )
            gc.collect()
        if graceful_stop or self._stop_control.stop_requested_event.is_set():
            logger.info("[Shutdown] Exiting by user request.")
            return False
        if fatal:
            return False
        if loop_forever:
            logger.info("Restarting song scan immediately...")
            return True
        logger.info("LoopForever=FALSE; exiting after completing queue.")
        return False

    def _solve(self, tasks: list, run: RunSettings, stream) -> None:
        """Solve and store the queue on the run's workers (config.ini Workers, else cpu_affinity.solve_worker_count).
        Raises after the run when a song failed."""
        if not tasks:
            return
        failed: list[str] = []

        def song_failed(label: str) -> None:
            failed.append(label)
            self._console.song_failed(label)

        self._console.start(len(tasks), stream)
        try:
            solve_queue(
                tasks,
                workers=min(run.workers or solve_worker_count(), len(tasks)),
                memory_limit_bytes=compute_memory_guard_limit(run),
                stop_requested=self._stop_control.stop_requested_now,
                on_done=self._console.song_stored,
                on_failed=song_failed,
            )
        finally:
            self._console.stop()
        if failed:
            raise RuntimeError(f"{len(failed)} song(s) failed in this run (see the [Workers] errors)")
