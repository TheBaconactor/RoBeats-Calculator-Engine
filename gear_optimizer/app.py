import gc
import logging
import multiprocessing
import os
import re
import sys
import threading
import time
import numpy as np
from gear_optimizer.core.constants import PATHS, BIN_DIR
from gear_optimizer.core.catalog_validation import build_validated_catalog_name_maps
from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.parsing import config_bool, env_flag, truthy
from gear_optimizer.core.output import suppress_stdout, restore_stdout, suppress_stderr, restore_stderr
from gear_optimizer.core.config import (
    AppRuntimeSettings,
    compute_memory_guard_limit,
    load_config,
    load_paths_cache,
    resolve_inflight_songs,
)
from gear_optimizer.data.database import (
    init_db,
    get_evolution_db_path,
)
from gear_optimizer.core.memory import (
    set_memory_watchdog_limit,
    memory_release_requested,
    build_memory_guard_resume_context,
    MemoryGuardResumeTracker,
    restart_process_for_memory_guard,
    MEMORY_GUARD_RESUME_FILE,
)
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.domain.jobs import (
    effective_task_count,
)
from gear_optimizer.data.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from gear_optimizer.data.exported_game_data_sync import sync_exported_game_data
from gear_optimizer.solver.scoring import FG_CACHE
from gear_optimizer.solver.cpu_work_manager import run_startup_cpu_work
from gear_optimizer.app_async_db import AsyncDbSaver
from gear_optimizer.app_stop_control import StopController
from gear_optimizer.song_queue import (
    infer_song_difficulty_from_path,
)
from gear_optimizer.ui.progress import (
    ProgressUI as _ProgressUI,
    _banner_enabled_default,
    _progress_ui_enabled_default,
    _stream_is_tty,
)
from gear_optimizer.pipeline.queue_task_coordinator import QueueTaskCoordinator
from gear_optimizer.ui.runtime_ui import RuntimeUiMixin
from gear_optimizer.task_execution import TaskExecutionMixin
from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)


class GearOptimizerApp(RuntimeUiMixin, TaskExecutionMixin):
    def __init__(self):
        self.setup_logging()
        self._async_db_saver = AsyncDbSaver()
        self._stop_control = StopController(bin_dir=BIN_DIR)
        self._stop_requested = self._stop_control.stop_requested_event
        self._force_exit_requested = self._stop_control.force_exit_requested_event
        self._output_enabled = bool(getattr(ENV, "output_enabled", False))
        ui_stream = getattr(sys, "__stdout__", None) or sys.stdout
        self._stdout_is_tty = _stream_is_tty(ui_stream)
        self._progress_enabled = _progress_ui_enabled_default(
            configured_enabled=bool(getattr(ENV, "progress_enabled", True)),
            output_enabled=bool(self._output_enabled),
            progress_env_present=bool("METAFINDER_PROGRESS" in os.environ),
            stream_is_tty=bool(self._stdout_is_tty),
        )
        self._banner_enabled = _banner_enabled_default(
            stream_is_tty=bool(self._stdout_is_tty),
            banner_env=ENV.banner_env,
        )
        self._progress_interval = float(getattr(ENV, "progress_interval_sec", 0.2))
        self._progress_bar_width = int(getattr(ENV, "progress_bar_width", 24))
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
        self._runtime_settings: AppRuntimeSettings | None = None

    def setup_logging(self) -> None:
        try:
            from gear_optimizer.core.logging_config import configure_default_logging

            configure_default_logging()
        except Exception as e:
            logger.warning(f"app:setup_logging: {e}")

    def request_stop(self, reason: str, *, force: bool = False) -> None:
        try:
            return self._stop_control.request_stop(reason, force=force)
        finally:
            try:
                from gear_optimizer.solver.gpu_executor import get_gpu_executor

                gpu_executor = get_gpu_executor()
                if gpu_executor.is_running:
                    gpu_executor.request_abort(f"stop requested ({reason})")
            except Exception as e:
                logger.warning(f"app:request_stop: {e}")

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

    @staticmethod
    def _cfg_truthy(cfg, section: str, key: str, *, fallback: bool = False) -> bool:
        return config_bool(cfg, section, key, default=fallback)

    def _current_runtime_settings(self, cfg=None) -> AppRuntimeSettings:
        settings = getattr(self, "_runtime_settings", None)
        if isinstance(settings, AppRuntimeSettings):
            return settings
        try:
            return AppRuntimeSettings.from_config(cfg)
        except Exception as e:
            logger.warning(f"app:_current_runtime_settings: {e}")
            return AppRuntimeSettings.from_config(None)

    def _get_inflight_songs_requested(self, cfg) -> int:
        runtime_settings = self._current_runtime_settings(cfg)
        return resolve_inflight_songs(int(runtime_settings.inflight.songs))

    def _maybe_autoset_gpu_song_slots(self, cfg) -> None:
        raw = env_get("GPU_SONG_SLOTS")
        if raw is not None and str(raw).strip() != "":
            return
        runtime_settings = self._current_runtime_settings(cfg)
        cfg_slots = int(runtime_settings.gpu.gpu_song_slots)
        if int(cfg_slots) > 0:
            os.environ["GPU_SONG_SLOTS"] = str(cfg_slots)
            try:
                logger.debug(
                    "[GPU] Set GPU_SONG_SLOTS={} from config (IterationEngine.GPU_SongSlots). Set GPU_SONG_SLOTS env var to override.".format(
                        int(cfg_slots)
                    )
                )
            except Exception as e:
                logger.debug(f"app:_maybe_autoset_gpu_song_slots: {e}")
            return
        inflight_songs = self._get_inflight_songs_requested(cfg)
        if int(inflight_songs) <= 1:
            return
        try:
            if "gear_optimizer.solver.taichi_gem.fields" in sys.modules:
                logger.debug("[GPU] Auto GPU_SONG_SLOTS skipped: taichi_gem.fields already imported.")
                return
        except Exception as e:
            logger.debug(f"app:_maybe_autoset_gpu_song_slots: {e}")
        from gear_optimizer.solver.native_inflight_config import CANONICAL_BASE_QUEUE_MULT

        base_queue_mult = int(CANONICAL_BASE_QUEUE_MULT)
        required = int(inflight_songs) * int(base_queue_mult) + 2
        slots = min(max(24, int(required)), 256)
        os.environ["GPU_SONG_SLOTS"] = str(slots)
        try:
            logger.debug(
                "[GPU] Auto-set GPU_SONG_SLOTS={} (InFlightSongs={}, canonical_base_queue_mult={}). Set GPU_SONG_SLOTS to override.".format(
                    int(slots),
                    int(inflight_songs),
                    int(base_queue_mult),
                )
            )
        except Exception as e:
            logger.debug(f"app:_maybe_autoset_gpu_song_slots: {e}")

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

    def _configure_execution_and_prewarm(self, cfg) -> None:
        runtime_settings = self._current_runtime_settings(cfg)
        # macOS-only required dispatch-safety boundary: on darwin `ti.vulkan` lowers through
        # MoltenVK and Taichi acquires a GLFW/Cocoa context during materialize_runtime, which
        # traps off the OS main thread. Pin that one-time materialization to the main thread
        # before any GPU executor thread spawns and before the lazy executor start on the
        # single-song (inflight<=1) task path. On Linux/Windows
        # there is no main-thread requirement, so we leave their startup path exactly as before
        # (lazy init on the executor thread) and do not introduce an eager startup GPU dependency.
        if sys.platform == "darwin":
            self._materialize_gpu_runtime_on_main_thread()
        try:
            inflight_req = int(runtime_settings.inflight.songs or 0)
        except Exception as e:
            logger.warning(f"app:_configure_execution_and_prewarm: {e}")
            inflight_req = 0
        if inflight_req <= 1:
            return
        try:
            logger.info("[Startup][GPU] Taichi/Vulkan init starting...")
            emit_profile_event(
                component="app",
                event="taichi_init_start",
                metrics={"in_process": 1},
            )
            from gear_optimizer.solver.gpu_executor import get_gpu_executor

            get_gpu_executor().start(in_process=True)
            logger.info("[Startup][GPU] Taichi/Vulkan init ready.")
            emit_profile_event(
                component="app",
                event="taichi_init_done",
                metrics={"in_process": 1},
            )
        except Exception as e:
            logger.warning(f"app:_configure_execution_and_prewarm: {e}")

    def _profiling_mode_enabled(self, cfg=None) -> bool:
        if bool(ENV.debug_profile) or bool(ENV.perf_timing_unconditional):
            return True
        truthy_keys = (
            "DEBUG_PROFILE",
            "METAFINDER_DEBUG_PROFILE",
            "PERF_TIMING",
            "GPU_SERVICE_PROFILE",
            "GPU_SERVICE_PROFILE_PRINT",
            "GPU_SYNC_FOR_TIMING",
            "GPU_FORCE_SYNC",
            "INFLIGHT_STAGE_PROFILE",
            "TAICHI_KERNEL_PROFILER",
            "TAICHI_KERNEL_PROFILER_PRINT",
            "METAFINDER_PROFILE_EVENTS",
            "PROFILE_EVENTS",
            "FG_TASK_TRACE",
        )
        for key in truthy_keys:
            if env_flag(key):
                return True
        path_keys = (
            "INFLIGHT_STAGE_PROFILE_PATH",
            "METAFINDER_PROFILE_EVENTS_PATH",
            "PROFILE_EVENTS_PATH",
        )
        for key in path_keys:
            if str(env_get(key, "") or "").strip():
                return True
        if cfg is not None:
            if self._cfg_truthy(cfg, "Debug", "DebugProfile", fallback=False):
                return True
            if self._cfg_truthy(cfg, "IterationEngine", "DebugProfile", fallback=False):
                return True
        return False

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

    def run(self):
        multiprocessing.freeze_support()
        self._install_signal_handlers()
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(line_buffering=True)
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(line_buffering=True)
        except Exception as e:
            logger.warning(f"app:run: {e}")
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

    def _run_single_iteration(self):
        memory_guard_restart = False
        memory_resume_tracker = None
        start_time = time.time()
        loop_forever = False  # Default, updated from config
        graceful_stop = False
        queued_songs = 0
        queued_tasks = 0
        FG_CACHE.clear()
        try:
            if self._stop_requested_now():
                graceful_stop = True
                loop_forever = False
                return False
            cfg = load_config()
            runtime_settings = self._current_runtime_settings(cfg)
            self._runtime_settings = runtime_settings
            paths = load_paths_cache()
            set_memory_watchdog_limit(compute_memory_guard_limit(cfg))
            db_display_name = os.path.basename(get_evolution_db_path())
            if self._banner_enabled:
                self._print_banner()
            logger.info(f"[Run] Gear Optimizer started. DB file: {db_display_name}")
            emit_profile_event(
                component="app",
                event="run_start",
                metrics={"db_file": str(db_display_name)},
            )
            init_db()
            fg_debug = bool(runtime_settings.iteration_engine.force_greats_debug)
            fg_status = "ResponseFrontier"
            logger.info(f" >> [ForceGreats] {fg_status}")
            loop_forever = bool(runtime_settings.loop_forever)
            if self._profiling_mode_enabled(cfg):
                if loop_forever:
                    logger.warning("[Profiling] LoopForever=true ignored; forcing LoopForever=false.")
                    emit_profile_event(
                        component="app",
                        event="profiling_forced_loop_forever_off",
                        metrics={"requested_loop_forever": 1},
                    )
                loop_forever = False
            eval_cpu_limit = int(runtime_settings.eval_cpu_cores)
            self._maybe_autoset_gpu_song_slots(cfg)
            sync_exported_game_data()
            stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)
            self._disable_inputs_to_prevent_taint(cfg)
            ref_arrays = self._preload_ref_arrays(stats_table)
            all_gears = load_all_gears_list(paths)
            all_minis = load_all_minis_list(paths)
            gears_by_name, minis_by_name = build_validated_catalog_name_maps(all_gears, all_minis)
            song_queue = self._build_song_queue(cfg, paths)
            queued_songs = len(song_queue)
            try:
                logger.info(f"[Run] Queued {len(song_queue)} song(s) for processing.")
            except Exception as e:
                logger.warning(f"app:_run_single_iteration: {e}")
            emit_profile_event(
                component="app",
                event="queue_built",
                metrics={"queued_songs": int(queued_songs)},
            )
            run_startup_cpu_work(
                cfg=cfg,
                song_queue=song_queue,
                ref_arrays=ref_arrays,
                data_root=PATHS.data_dir,
                announce_stream=self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout,
            )
            self._configure_execution_and_prewarm(cfg)
            memory_resume_tracker = MemoryGuardResumeTracker(MEMORY_GUARD_RESUME_FILE)
            memory_resume_tracker.prime(song_queue, build_memory_guard_resume_context(*self._get_filter_params(cfg)))
            tasks = self._prepare_tasks(
                song_queue,
                cfg,
                paths,
                ref_arrays,
                all_gears,
                all_minis,
                gears_by_name,
                minis_by_name,
                fg_debug,
            )
            queued_tasks = self._effective_total_tasks(tasks)
            emit_profile_event(
                component="app",
                event="tasks_prepared",
                metrics={
                    "queued_songs": int(queued_songs),
                    "queued_tasks": int(queued_tasks),
                    "queued_task_bundles": int(len(tasks)),
                },
            )
            parallel_workers = 1
            self._start_progress(queued_tasks)
            self._execute_tasks(
                tasks,
                eval_cpu_limit,
                parallel_workers,
                memory_resume_tracker,
                loop_forever,
            )
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
        except Exception as e:
            logger.error(f"Error: {e}")
            raise
        finally:
            self._stop_progress()
            self._cleanup_resources()
            elapsed = time.time() - start_time
            done_msg = f"Run completed in {elapsed:.2f}s"
            logger.info(done_msg)
            try:
                elapsed_h = float(elapsed) / 3600.0 if elapsed and elapsed > 0 else 0.0
            except (ValueError, TypeError):
                elapsed_h = 0.0
            if elapsed_h > 0:
                try:
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
                except Exception as e:
                    logger.warning(f"app:_run_single_iteration: {e}")
            emit_profile_event(
                component="app",
                event="run_end",
                metrics={
                    "elapsed_sec": float(elapsed),
                    "queued_songs": int(queued_songs),
                    "queued_tasks": int(queued_tasks),
                    "graceful_stop": int(bool(graceful_stop or self._stop_requested.is_set())),
                },
            )
            gc.collect()
        if graceful_stop or self._stop_requested.is_set():
            try:
                logger.info("[Shutdown] Exiting by user request.")
            except Exception as e:
                logger.warning(f"app:_run_single_iteration: {e}")
            return False
        if memory_guard_restart:
            restart_process_for_memory_guard()
            return False  # Process replaced
        elif loop_forever:
            restart_wait_s = self._loop_restart_wait_seconds(cfg, default_seconds=0.0)
            self._handle_loop_restart(wait_time=restart_wait_s)
            return True
        else:
            logger.info("LoopForever=FALSE; exiting after completing queue.")
            return False

    def _disable_inputs_to_prevent_taint(self, cfg):
        logger.info(
            " >> [Auto-Mode] Finders active: Ignoring manual [UserInputStatsGems] & [ElementalGems] to prevent database tainting."
        )
        if not cfg.has_section("UserInputStatsGems"):
            cfg.add_section("UserInputStatsGems")
        for key in ["perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"]:
            cfg.set("UserInputStatsGems", key, "0")
        if not cfg.has_section("ElementalGems"):
            cfg.add_section("ElementalGems")
        for key in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
            cfg.set("ElementalGems", key, "0")

    def _preload_ref_arrays(self, stats_table):
        from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats

        return build_ref_arrays_from_stats(stats_table, dtype=np.float32)

    def _queue_task_coordinator(self) -> QueueTaskCoordinator:
        """Queue/task logic lives in QueueTaskCoordinator; app state reaches it
        only through these two callables (unit-testable without GPU/DB/app)."""
        return QueueTaskCoordinator(
            runtime_settings_fn=self._current_runtime_settings,
            stop_requested_fn=self._stop_requested_now,
        )

    def _get_filter_params(self, cfg):
        return self._queue_task_coordinator().get_filter_params(cfg)

    @staticmethod
    def _infer_song_difficulty_from_path(root: str) -> str:
        return infer_song_difficulty_from_path(root)

    def _build_song_queue(self, cfg, paths):
        return self._queue_task_coordinator().build_song_queue(cfg, paths)

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
        cfg,
        paths,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        fg_debug,
    ):
        return self._queue_task_coordinator().prepare_tasks(
            song_queue,
            cfg,
            paths,
            ref_arrays,
            all_gears,
            all_minis,
            gears_by_name,
            minis_by_name,
            fg_debug,
        )

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
        raw = str(env_get("METAFINDER_FATAL_GPU_ERRORS", "") or "").strip()
        if raw:
            return truthy(raw)
        if truthy(env_get("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "0")):
            return True
        return False

    def _memory_guard_restart_needed(self, memory_resume_tracker) -> bool:
        if not memory_release_requested():
            return False
        try:
            return memory_resume_tracker is not None and memory_resume_tracker.pending_count() > 0
        except Exception as e:
            logger.warning(f"app:_memory_guard_restart_needed: {e}")
            return True

    @staticmethod
    def _iter_exception_chain(exc: BaseException | None):
        seen: set[int] = set()
        pending = [exc]
        while pending:
            current = pending.pop(0)
            if current is None:
                continue
            current_id = id(current)
            if current_id in seen:
                continue
            seen.add(current_id)
            yield current
            try:
                pending.append(getattr(current, "__cause__", None))
            except Exception as e:
                logger.warning(f"app:_iter_exception_chain: {e}")
            try:
                pending.append(getattr(current, "__context__", None))
            except Exception as e:
                logger.warning(f"app:_iter_exception_chain: {e}")

    def _is_fatal_inflight_exception(self, exc: BaseException) -> bool:
        if not self._fatal_gpu_errors_enabled():
            return False
        try:
            from gear_optimizer.solver.gpu_service import GpuServiceTimeoutError
        except Exception as e:
            logger.warning(f"app:_is_fatal_inflight_exception: {e}")
            GpuServiceTimeoutError = ()
        fatal_markers = (
            "gpu executor timeout after",
            "gpu executor taichi init failed",
            "taichi init failed",
            "gpu service request",
            "timed out after",
            "device lost",
            "device removed",
            "device hung",
            "dxgi_error_device_hung",
            "dxgi_error_device_removed",
            "cudaerrorlaunchtimeout",
            "watchdog timeout",
            "tdr",
            "waituntilcompleted",
            "metaldevice::wait_idle",
        )
        for current in self._iter_exception_chain(exc):
            if GpuServiceTimeoutError and isinstance(current, GpuServiceTimeoutError):
                return True
            try:
                message = f"{type(current).__name__}: {current}".lower()
            except Exception as e:
                logger.warning(f"app:_is_fatal_inflight_exception: {e}")
                message = ""
            if any(marker in message for marker in fatal_markers):
                return True
        return False

    def _cleanup_resources(self):
        try:
            if hasattr(self, "_async_db_saver"):
                try:
                    self._async_db_saver.shutdown(timeout=30.0)
                except Exception as e:
                    logger.warning(f"app:_cleanup_resources: {e}")
            gc.collect(generation=0)
        except Exception as e:
            logger.warning(f"app:_cleanup_resources: {e}")

    def _loop_restart_wait_seconds(self, cfg=None, *, default_seconds: float = 0.0) -> float:
        wait_s = float(default_seconds)
        try:
            wait_s = float(self._current_runtime_settings(cfg).loop_restart_wait_sec)
        except (ValueError, TypeError):
            pass
        for env_key in ("METAFINDER_LOOP_RESTART_WAIT_SEC",):
            raw = env_get(env_key)
            if raw is None or str(raw).strip() == "":
                continue
            try:
                wait_s = float(raw)
            except (ValueError, TypeError):
                pass
        return max(0.0, min(float(wait_s), 60.0))

    def _handle_loop_restart(self, wait_time=0):
        wait_s = max(0.0, float(wait_time or 0.0))
        if wait_s > 0.0:
            logger.info(f"Restarting song scan in {wait_s:.2f} seconds...")
        else:
            logger.info("Restarting song scan immediately...")
        try:
            if os.path.exists(MEMORY_GUARD_RESUME_FILE):
                os.remove(MEMORY_GUARD_RESUME_FILE)
                logger.info("[LoopForever] Cleared resume file")
        except (OSError, IOError) as e:
            logging.warning(f"Failed to delete resume file: {e}")
        if wait_s > 0.0:
            time.sleep(wait_s)
