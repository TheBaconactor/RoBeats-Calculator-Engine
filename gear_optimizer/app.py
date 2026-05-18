import gc
import logging
import multiprocessing
import os
import re
import secrets
import sys
import zlib
import threading
import time
import typing

import numpy as np

# Import from refactored modules
from gear_optimizer.core.constants import PATHS, SCRIPT_DIR, BIN_DIR, GA_POPULATION_SIZE
from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.parsing import config_bool, env_flag, truthy
from gear_optimizer.core.output import suppress_stdout, restore_stdout, suppress_stderr, restore_stderr
from gear_optimizer.core.config import (
    AppRuntimeSettings,
    compute_memory_guard_limit,
    load_config,
    load_paths_cache,
)
from gear_optimizer.data.database import (
    init_db,
    get_evolution_db_path,
    get_song_names_present_in_db,
)
from gear_optimizer.core.memory import (
    set_memory_watchdog_limit,
    memory_release_requested,
    build_memory_guard_resume_context,
    load_memory_guard_resume_queue,
    MemoryGuardResumeTracker,
    restart_process_for_memory_guard,
    MEMORY_GUARD_RESUME_FILE,
)
from gear_optimizer.core.profile_events import emit_profile_event
from gear_optimizer.domain.jobs import (
    SharedRunContext,
    SongJob,
    effective_task_count,
    legacy_task_tuple_from_job_context,
)
from gear_optimizer.data.song_io import scan_song_header
from gear_optimizer.data.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from gear_optimizer.core.utils import safe_int, cfg_to_dict
from gear_optimizer.solver.scoring import FEVER_TIMELINE_CACHE, FG_CACHE
from gear_optimizer.solver.scoring import GEM_SOLVER_CACHE
from gear_optimizer.solver.cpu_work_manager import CpuWorkManager
from gear_optimizer.app_async_db import AsyncDbSaver
from gear_optimizer.data.stats_verifier import verify_and_repair_stats, print_verification_warning
from gear_optimizer.app_stop_control import StopController
from gear_optimizer.api_integration import (
    clear_robeatsmeta_runtime_status,
    filter_robeatsmeta_recently_computed_song_queue,
    mark_robeatsmeta_song_started,
    maybe_mark_robeatsmeta_song_batch_computed,
    optimizer_priority_api_enabled,
    prioritize_robeatsmeta_song_queue,
    update_robeatsmeta_runtime_status,
)
from gear_optimizer.robeatsmeta_api import RoBeatsMetaOptimizerApi
from gear_optimizer.song_queue import (
    build_song_queue_from_pending_ids,
    ensure_song_path_index,
    infer_song_difficulty_from_path,
    song_index_roots,
)
from gear_optimizer.ui.progress import (
    ProgressUI as _ProgressUI,
    _banner_enabled_default,
    _progress_ui_enabled_default,
    _stream_is_tty,
)
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
            banner_env=env_get("METAFINDER_BANNER"),
        )
        self._progress_interval = float(getattr(ENV, "progress_interval_sec", 0.2))
        self._progress_bar_width = int(getattr(ENV, "progress_bar_width", 24))
        self._progress: _ProgressUI | None = None
        # Separate-process TUI (default) keeps console IO out of the compute/GPU owner process.
        self._tui_enabled = True
        try:
            raw = env_get("METAFINDER_UI_PROCESS")
            if raw is not None and str(raw).strip() != "":
                self._tui_enabled = truthy(raw)
        except (TypeError, ValueError):
            self._tui_enabled = True
        self._tui_epoch = 0
        self._tui_progress = None
        self._tui_process = None
        self._tui_stop_event = None
        self._tui_cmd_queue = None
        self._tui_resp_queue = None
        self._tui_cmd_thread: threading.Thread | None = None
        self._tui_cmd_stop = threading.Event()
        self._orig_stdout = None
        self._orig_stderr = None
        self._progress_counts_driven = False
        self._hotkey_thread: threading.Thread | None = None
        self._hotkeys_enabled = True
        self._run_tasks_ref = None
        self._run_completed_ref = None
        self._run_current_song_label = ""
        self._runtime_status_name = "idle"
        self._stop_poll_interval_sec = 0.05
        self._stop_next_check_monotonic = 0.0
        self._stop_cached_result = False
        # Full DB integrity verification is expensive; only run it once per process.
        self._stats_verified_once = False
        # Session-scoped counters (persist across loop restarts).
        self._session_new_records = 0
        self._session_new_record_keys: set[str] = set()
        self._session_new_record_best_by_song: dict[str, int] = {}
        self._runtime_completed_count = 0
        self._runtime_total_count = 0
        self._runtime_failed_count = 0
        self._backend_priority_song_names: set[str] = set()
        # Optional override for pending-visit songs. 0 means "use SongRepeats".
        try:
            self._backend_priority_song_repeat_count = max(
                0,
                int(env_get("ROBEATSMETA_OPTIMIZER_PRIORITY_REPEAT_COUNT", "0") or "0"),
            )
        except (TypeError, ValueError):
            self._backend_priority_song_repeat_count = 0
        self._song_path_index_lock = threading.Lock()
        self._song_path_index: dict[str, list[dict[str, str]]] = {}
        self._song_path_index_ready = False
        self._song_path_index_roots: tuple[str, ...] = ()
        self._song_path_index_last_force_attempt_monotonic = 0.0
        self._cpu_work_manager = CpuWorkManager()
        self._song_path_index_force_cooldown_sec = 60.0
        self._robeatsmeta_api: RoBeatsMetaOptimizerApi | None = None
        self._runtime_settings: AppRuntimeSettings | None = None

    def setup_logging(self) -> None:
        # Keep stdout clean for result printers; send diagnostics to stderr.
        try:
            from gear_optimizer.core.logging_config import configure_logging

            log_file_path = os.path.join(BIN_DIR, "error.log")
            console_level = logging.INFO if bool(getattr(ENV, "output_enabled", False)) else logging.ERROR
            configure_logging(log_file_path=log_file_path, console_level=console_level, file_level=logging.WARNING)
        except Exception as e:
            logger.warning(f"app:setup_logging: {e}")

    def request_stop(self, reason: str, *, force: bool = False) -> None:
        try:
            return self._stop_control.request_stop(reason, force=force)
        finally:
            # Best-effort: once the user asks to stop, ask the GPU owner to abort
            # long-running in-flight requests so shutdown does not wait for a full GA/FG drain.
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
        inflight_songs = int(runtime_settings.inflight.songs)
        try:
            inflight_songs_env = safe_int(env_get("IN_FLIGHT_SONGS", 0), 0)
            if inflight_songs_env > 0:
                inflight_songs = inflight_songs_env
        except Exception as e:
            logger.debug(f"app:_get_inflight_songs_requested: {e}")
        return int(inflight_songs)

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

        ga_queue_mult = int(runtime_settings.gpu.ga_queue_mult)
        raw = env_get("INFLIGHT_GA_QUEUE_MULT")
        if raw is not None and str(raw).strip() != "":
            try:
                ga_queue_mult = int(raw)
            except Exception as e:
                logger.debug(f"app:_maybe_autoset_gpu_song_slots: {e}")
        if ga_queue_mult <= 0:
            ga_queue_mult = 2
        ga_queue_mult = max(1, min(int(ga_queue_mult), 8))

        required = int(inflight_songs) * int(ga_queue_mult) + 2
        slots = min(max(24, int(required)), 256)

        os.environ["GPU_SONG_SLOTS"] = str(slots)
        try:
            logger.debug(
                "[GPU] Auto-set GPU_SONG_SLOTS={} (InFlightSongs={}, InFlight_GA_QueueMult={}). Set GPU_SONG_SLOTS to override.".format(
                    int(slots),
                    int(inflight_songs),
                    int(ga_queue_mult),
                )
            )
        except Exception as e:
            logger.debug(f"app:_maybe_autoset_gpu_song_slots: {e}")

    def _configure_execution_and_prewarm(self, cfg) -> None:
        runtime_settings = self._current_runtime_settings(cfg)
        ga_multistart = max(1, int(runtime_settings.ga.multi_start))
        os.environ.setdefault("GPU_NATIVE_GA_MAX_RUNS", str(ga_multistart))
        os.environ.setdefault("GPU_NATIVE_GA_MAX_GENOMES", str(GA_POPULATION_SIZE))
        try:
            from gear_optimizer.solver.taichi_gem import fields as gpu_fields

            gpu_fields.configure_ga_run_buffers(max_runs=ga_multistart, max_genomes=int(GA_POPULATION_SIZE))
        except Exception as e:
            logger.warning(f"app:_configure_execution_and_prewarm: {e}")

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
        # Fast path from centralized env snapshot.
        if bool(getattr(ENV, "debug_profile", False)) or bool(getattr(ENV, "perf_timing_unconditional", False)):
            return True

        # Direct env checks (covers runs that don't go through main.py env normalization).
        truthy_keys = (
            "DEBUG_PROFILE",
            "METAFINDER_DEBUG_PROFILE",
            "PERF_TIMING",
            "GPU_EXECUTOR_PROFILE",
            "GPU_PROFILER",
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
            "GPU_EXECUTOR_TRACE_PATH",
            "INFLIGHT_STAGE_PROFILE_PATH",
            "METAFINDER_PROFILE_EVENTS_PATH",
            "PROFILE_EVENTS_PATH",
        )
        for key in path_keys:
            if str(env_get(key, "") or "").strip():
                return True

        # DEV / DEBUG: profile-only config overrides (Debug.DebugProfile, IterationEngine.DebugProfile).
        if cfg is not None:
            if self._cfg_truthy(cfg, "Debug", "DebugProfile", fallback=False):
                return True
            if self._cfg_truthy(cfg, "IterationEngine", "DebugProfile", fallback=False):
                return True
        return False

    def _optimizer_priority_api_enabled(self) -> bool:
        return optimizer_priority_api_enabled(self)

    def _prioritize_robeatsmeta_song_queue(
        self,
        song_queue: list[tuple[str, str, str]],
    ) -> list[tuple[str, str, str]]:
        return prioritize_robeatsmeta_song_queue(self, song_queue)

    def _filter_robeatsmeta_recently_computed_song_queue(
        self,
        song_queue: list[tuple[str, str, str]],
    ) -> list[tuple[str, str, str]]:
        return filter_robeatsmeta_recently_computed_song_queue(self, song_queue)

    def _maybe_mark_robeatsmeta_song_batch_computed(
        self,
        song_name: str | None,
        completed_songs: set[str] | None = None,
    ) -> bool:
        return maybe_mark_robeatsmeta_song_batch_computed(self, song_name, completed_songs)

    def _mark_robeatsmeta_song_started(self, song_name: str | None) -> None:
        mark_robeatsmeta_song_started(self, song_name)

    def _update_robeatsmeta_runtime_status(
        self,
        *,
        status: str | None = None,
        current_song: str | None = None,
        completed: int | None = None,
        total: int | None = None,
        failed: int | None = None,
    ) -> None:
        update_robeatsmeta_runtime_status(
            self,
            status=status,
            current_song=current_song,
            completed=completed,
            total=total,
            failed=failed,
        )

    def _clear_robeatsmeta_runtime_status(self, *, status: str = "idle", available: bool = True) -> None:
        clear_robeatsmeta_runtime_status(self, status=status, available=available)

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

    def _maybe_init_robeatsmeta_api(self, cfg) -> None:
        try:
            self._robeatsmeta_api = RoBeatsMetaOptimizerApi()
            if self._robeatsmeta_api.backend_mode_enabled():
                backend_benchmark_mode = bool(self._robeatsmeta_api.benchmark_mode_enabled())
                if self._robeatsmeta_api.apply_service_defaults(cfg):
                    runtime_settings = AppRuntimeSettings.from_config(cfg)
                    self._runtime_settings = runtime_settings
                    loop_forever_effective = runtime_settings.loop_forever
                    song_repeats_effective = runtime_settings.song_repeats
                    inflight_songs_effective = runtime_settings.inflight.songs
                    if backend_benchmark_mode:
                        logger.info(
                            "[RoBeatsMeta] Service defaults enabled (benchmark): "
                            f"LoopForever={loop_forever_effective}, "
                            f"SongRepeats={song_repeats_effective}, "
                            f"InFlightSongs={inflight_songs_effective}, "
                            "Difficulty=All, QueueScope=PendingSongIds.",
                        )
                    else:
                        logger.info(
                            "[RoBeatsMeta] Service defaults enabled: "
                            f"LoopForever={loop_forever_effective}, "
                            f"SongRepeats={song_repeats_effective}, "
                            f"InFlightSongs={inflight_songs_effective}, "
                            "Difficulty=All, QueueScope=PendingSongIds.",
                        )
                elif not self._robeatsmeta_api.service_defaults_enabled():
                    logger.info(
                        "[RoBeatsMeta] Service mode enabled: keeping IterationEngine/CalculateSong config (service defaults disabled).",
                    )

                # Backend-special behavior: default to headless runtime status via API.
                # Keep CLI progress disabled unless explicitly requested by env.
                if "METAFINDER_PROGRESS" not in os.environ:
                    self._progress_enabled = False
        except Exception as exc:
            self._robeatsmeta_api = None
            logging.warning(f"[RoBeatsMeta] Failed to initialize optimizer API: {type(exc).__name__}: {exc}")

    def _run_single_iteration(self):
        memory_guard_restart = False
        memory_resume_tracker = None
        start_time = time.time()
        loop_forever = False  # Default, updated from config
        graceful_stop = False
        queued_songs = 0
        queued_tasks = 0

        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()
        FG_CACHE.clear()

        manager = None
        status_queue = None
        status_thread = None

        try:
            if self._stop_requested_now():
                graceful_stop = True
                loop_forever = False
                return False

            cfg = load_config()
            self._maybe_init_robeatsmeta_api(cfg)
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

            # Verify Stats integrity (only on fresh queue, not resume)
            # This ensures all database entries have properly populated Stats objects.
            # If issues are detected (missing or empty Stats), the verifier will:
            # 1. Automatically repair them by recomputing Stats
            # 2. Display a prominent warning if any issues were found
            # This prevents frontend/extractors from seeing 0 for elemental stats.
            ignore_resume = truthy(env_get("METAFINDER_IGNORE_RESUME_QUEUE", ""))
            memory_resume_exists = os.path.exists(MEMORY_GUARD_RESUME_FILE)
            is_fresh_queue = ignore_resume or not memory_resume_exists
            # StatsVerifier is a heavyweight DB integrity repair pass intended for debugging/one-off recovery,
            # not a default production startup step. Keep it opt-in.
            enable_stats_verify = bool(truthy(env_get("METAFINDER_VERIFY_STATS_INTEGRITY", "")))
            skip_stats_verify = bool(truthy(env_get("METAFINDER_SKIP_STATS_INTEGRITY_VERIFY", "")))

            if is_fresh_queue:
                if not self._stats_verified_once:
                    if skip_stats_verify or not enable_stats_verify:
                        # Treat the skip env var as an explicit override; the default stays off.
                        self._stats_verified_once = True
                    else:
                        self._verify_stats_integrity()
                        self._stats_verified_once = True

            # Config reading
            ie = runtime_settings.iteration_engine
            fg_debug = bool(ie.force_greats_debug)

            if ie.manual_force_greats:
                fg_status = f"Manual Config {list(ie.force_greats_config or [])}"
            else:
                fg_status = "Finder"

            logger.info(f" >> [ForceGreats] {fg_status}")

            # PRODUCTION: runtime flags (GA_SearchDepth, LoopForever, EvalCPUCores).
            # Evolution DB is always enabled in production.
            ga_depth = int(runtime_settings.ga.search_depth)
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

            stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)

            # CRITICAL FIX: Prevent DB tainting by disabling manual input fields.
            self._disable_inputs_to_prevent_taint(cfg)

            ref_arrays = self._preload_ref_arrays(stats_table)
            all_gears = load_all_gears_list(paths)
            all_minis = load_all_minis_list(paths)
            gears_by_name = {g["Name"]: g for g in all_gears}
            minis_by_name = {m["Name"]: m for m in all_minis}

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

            self._cpu_work_manager.run_startup(
                cfg=cfg,
                song_queue=song_queue,
                ref_arrays=ref_arrays,
                data_root=PATHS.data_dir,
            )
            self._configure_execution_and_prewarm(cfg)

            memory_resume_tracker = MemoryGuardResumeTracker(MEMORY_GUARD_RESUME_FILE)
            memory_resume_tracker.prime(song_queue, build_memory_guard_resume_context(*self._get_filter_params(cfg)))

            manager = multiprocessing.Manager()
            status_queue = manager.Queue()

            status_thread = threading.Thread(target=self._status_listener, args=(status_queue,), daemon=True)
            status_thread.start()

            tasks = self._prepare_tasks(
                song_queue,
                cfg,
                paths,
                ref_arrays,
                all_gears,
                all_minis,
                gears_by_name,
                minis_by_name,
                ga_depth,
                status_queue,
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

            # Check if we need to restart due to memory guard
            if memory_release_requested() and loop_forever:
                memory_guard_restart = True

        except KeyboardInterrupt:
            # First Ctrl+C is handled by the signal handler as a graceful stop request.
            # This catches direct KeyboardInterrupt (or a forced second Ctrl+C).
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

        finally:
            self._stop_progress()
            self._cleanup_resources(status_queue, status_thread, manager)

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

                    # "songs" is approximate when SongRepeats>1; tasks/hour is the reliable metric.
                    # Estimate repeats as queued_tasks/queued_songs (when available) to make songs/hour meaningful.
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

    def _verify_stats_integrity(self):
        """
        Verify and repair database Stats integrity on fresh queue startup.

        Performs a FULL scan of all database entries (not sample-based) to ensure
        no entries with missing/empty Stats slip through. Automatically repairs
        any issues found and displays a prominent warning.
        """
        try:
            # Full scan of all entries - sample-based checks can miss scattered bad entries
            logger.info("[StatsVerifier] Full database integrity check...")
            all_valid, full_stats = verify_and_repair_stats(dry_run=False, verbose=True, sample_size=0)

            if all_valid:
                logger.info(f"[StatsVerifier] All {full_stats['total']:,} entries have valid Stats")
            else:
                # Repairs were made - display prominent warning
                repaired = full_stats.get("repaired", 0)
                logger.info(f"[StatsVerifier] Repaired {repaired:,} entries with invalid Stats")
                if repaired > 100:
                    # Only show prominent warning if many repairs needed
                    print_verification_warning(full_stats)

        except Exception as e:
            logger.error(f"[StatsVerifier] Unexpected error: {e}")
            logger.warning(f"[StatsVerifier] Warning: Could not verify Stats integrity: {e}")

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

        # Runtime/GPU search stays on float32. Exact replay paths resolve their own
        # float64 authority refs so persistence/repair do not inherit search drift.
        return build_ref_arrays_from_stats(stats_table, dtype=np.float32)

    def _get_filter_params(self, cfg):
        song_settings = self._current_runtime_settings(cfg).calculate_song
        diff = song_settings.difficulty or "All"
        diff_lower = diff.strip().lower()
        filter_search = song_settings.song_name.strip().lower()

        def _parse_color_targets(raw_val):
            tokens = [c.strip().lower() for c in re.split(r"[,\|/]", raw_val or "") if c and c.strip()]
            is_all = not tokens or any(c in ("all", "any", "*") for c in tokens)
            return is_all, set() if is_all else set(tokens)

        target_primary_raw = song_settings.target_primary
        target_secondary_raw = song_settings.target_secondary
        if not target_secondary_raw:
            target_secondary_raw = "all"

        target_primary_all, target_primary_colors = _parse_color_targets(target_primary_raw)
        target_secondary_all, target_secondary_colors = _parse_color_targets(target_secondary_raw)

        return (
            diff_lower,
            filter_search,
            target_primary_all,
            target_primary_colors,
            target_secondary_all,
            target_secondary_colors,
        )

    @staticmethod
    def _infer_song_difficulty_from_path(root: str) -> str:
        return infer_song_difficulty_from_path(root)

    def _song_index_roots(self) -> list[str]:
        return song_index_roots(data_root=PATHS.data_dir, script_dir=SCRIPT_DIR)

    def _ensure_song_path_index(self, *, force: bool = False) -> None:
        roots = tuple(self._song_index_roots())
        ensure_song_path_index(self, roots=roots, force=force)

    def _build_song_queue_from_pending_ids(
        self,
        pending_song_ids: typing.Sequence[str],
        *,
        diff_lower: str,
        filter_search: str,
        target_primary_all: bool,
        target_primary_colors: set[str],
        target_secondary_all: bool,
        target_secondary_colors: set[str],
    ) -> tuple[list[tuple[str, str, str]], list[str]]:
        return build_song_queue_from_pending_ids(
            self,
            pending_song_ids,
            diff_lower=diff_lower,
            filter_search=filter_search,
            target_primary_all=target_primary_all,
            target_primary_colors=target_primary_colors,
            target_secondary_all=target_secondary_all,
            target_secondary_colors=target_secondary_colors,
        )

    def _build_song_queue(self, cfg, paths):
        diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols = self._get_filter_params(cfg)
        backend_service_mode = bool(
            getattr(getattr(self, "_robeatsmeta_api", None), "backend_mode_enabled", lambda: False)()
        )
        self._backend_priority_song_names = set()

        def _pending_backend_song_ids() -> list[str]:
            if not backend_service_mode or not self._optimizer_priority_api_enabled():
                return []
            api = self._robeatsmeta_api
            if api is None:
                return []
            try:
                raw_ids = api.pending_song_ids()
            except Exception as exc:
                logging.warning(f"[RoBeatsMeta] Failed to read pending song ids: {type(exc).__name__}: {exc}")
                return []
            cleaned: list[str] = []
            seen: set[str] = set()
            for value in raw_ids or []:
                song_id = str(value or "").strip()
                if not song_id or song_id in seen:
                    continue
                seen.add(song_id)
                cleaned.append(song_id)
            return cleaned

        resume_context = build_memory_guard_resume_context(diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols)

        def _read_song_queue_limit() -> int:
            limit = int(self._current_runtime_settings(cfg).song_queue_limit)
            for env_key in ("SONG_QUEUE_LIMIT", "METAFINDER_SONG_QUEUE_LIMIT"):
                raw = env_get(env_key)
                if raw is None:
                    continue
                try:
                    env_val = safe_int(raw, 0)
                except (ValueError, TypeError):
                    env_val = 0
                if env_val and env_val > 0:
                    limit = int(env_val)
                    break
            return int(limit)

        _presence_lookup_cache: dict[tuple[str, ...], set[str]] = {}

        def _lookup_song_presence(song_names: typing.Iterable[str]) -> set[str]:
            names = tuple(sorted({str(name or "").strip() for name in (song_names or []) if str(name or "").strip()}))
            if not names:
                return set()
            cached = _presence_lookup_cache.get(names)
            if cached is not None:
                return cached
            present = get_song_names_present_in_db(names)
            _presence_lookup_cache[names] = present
            return present

        resume_seed_queue: list[tuple[str, str, str]] = []
        resume_names_present: set[str] = set()
        ignore_resume = bool(self._current_runtime_settings(cfg).ignore_resume_queue)
        if backend_service_mode:
            # Backend queue order and persistence come from the API bridge state file.
            # Ignore memory-guard resume files to avoid replaying stale broad queues.
            ignore_resume = True
        if truthy(env_get("METAFINDER_IGNORE_RESUME_QUEUE", "")):
            ignore_resume = True

        if not ignore_resume:
            resume_seed_queue = load_memory_guard_resume_queue(resume_context)
            if resume_seed_queue:
                logger.info(f"[MemoryGuard] Resuming {len(resume_seed_queue)} song(s) from previous interrupted run.")
                try:
                    resume_names_present = _lookup_song_presence((item[1] for item in resume_seed_queue))
                    if resume_names_present:
                        resume_missing: list[tuple[str, str, str]] = []
                        resume_existing: list[tuple[str, str, str]] = []
                        for item in resume_seed_queue:
                            (resume_existing if item[1] in resume_names_present else resume_missing).append(item)
                        resume_seed_queue = resume_missing + resume_existing
                        if backend_service_mode:
                            self._backend_priority_song_names.update(
                                str(item[1] or "").strip() for item in resume_missing
                            )
                except Exception as exc:
                    logging.warning(
                        f"[DB] Failed to prioritize resume queue: {type(exc).__name__}: {exc}",
                    )

        pending_song_ids = _pending_backend_song_ids()
        pending_set = set(pending_song_ids)
        pending_only_mode = bool(
            backend_service_mode and truthy(env_get("ROBEATSMETA_OPTIMIZER_PENDING_ONLY", ""))
        )
        diff = self._current_runtime_settings(cfg).calculate_song.difficulty or "All"
        search_dir = paths.get(diff, SCRIPT_DIR)
        unresolved_song_ids: list[str] = []
        song_queue: list[tuple[str, str, str]] = []

        if backend_service_mode and pending_set and pending_only_mode:
            song_queue, unresolved_song_ids = self._build_song_queue_from_pending_ids(
                pending_song_ids,
                diff_lower=diff_lower,
                filter_search=filter_search,
                target_primary_all=tp_all,
                target_primary_colors=tp_cols,
                target_secondary_all=ts_all,
                target_secondary_colors=ts_cols,
            )
            if unresolved_song_ids:
                now_monotonic = float(time.monotonic())
                if now_monotonic - float(self._song_path_index_last_force_attempt_monotonic) >= float(
                    self._song_path_index_force_cooldown_sec
                ):
                    self._song_path_index_last_force_attempt_monotonic = now_monotonic
                    self._ensure_song_path_index(force=True)
                    song_queue, unresolved_song_ids = self._build_song_queue_from_pending_ids(
                        pending_song_ids,
                        diff_lower=diff_lower,
                        filter_search=filter_search,
                        target_primary_all=tp_all,
                        target_primary_colors=tp_cols,
                        target_secondary_all=ts_all,
                        target_secondary_colors=ts_cols,
                    )
                if unresolved_song_ids:
                    logging.warning(
                        "[RoBeatsMeta] Pending song ids not found in song path index: %s",
                        ", ".join(unresolved_song_ids[:10]),
                    )
        else:
            seen_paths = set()
            if diff_lower not in ("easy", "normal", "hard"):
                data_root = PATHS.data_dir
                dirs_to_search = [data_root] if os.path.exists(data_root) else [SCRIPT_DIR]
            else:
                dirs_to_search = [search_dir]

            for d in dirs_to_search:
                if not os.path.exists(d):
                    continue
                if self._stop_requested_now():
                    break
                for root, _, files in os.walk(d):
                    if self._stop_requested_now():
                        break
                    for f in files:
                        if self._stop_requested_now():
                            break
                        if f.lower().endswith(".txt"):
                            fp = os.path.join(root, f)
                            abs_fp = os.path.abspath(fp)
                            if abs_fp in seen_paths:
                                continue

                            meta = scan_song_header(fp)
                            if not meta:
                                continue

                            name = meta["Song Name"]
                            name_lower = name.lower()
                            detected_diff = self._infer_song_difficulty_from_path(root)

                            if diff_lower in ("easy", "normal", "hard") and detected_diff.lower() != diff_lower:
                                continue

                            primary_color = (meta.get("Primary Color") or "").strip().lower()
                            secondary_color = (meta.get("Secondary Color") or "").strip().lower()

                            if not tp_all and (not primary_color or primary_color not in tp_cols):
                                continue
                            if not ts_all and (not secondary_color or secondary_color not in ts_cols):
                                continue

                            if filter_search and filter_search not in name_lower:
                                continue

                            song_queue.append((fp, name, detected_diff))
                            seen_paths.add(abs_fp)

        if backend_service_mode:
            if pending_set:
                self._backend_priority_song_names.update(pending_song_ids)
            elif pending_only_mode:
                song_queue = []
                try:
                    logger.info("[Queue] No pending song-id visits; backend service is idle.")
                except Exception as e:
                    logger.warning(f"app:_lookup_song_presence: {e}")

        if not song_queue and not resume_seed_queue:
            if backend_service_mode:
                return []
            logger.error("Error: No matching songs found.")
            return []

        try:
            logger.info(f"[Queue] Discovered {len(song_queue)} song(s) (Difficulty={diff})")
        except Exception as e:
            logger.warning(f"app:_lookup_song_presence: {e}")

        song_names_present_in_db: set[str] = set()
        song_names_present_loaded = False
        try:
            song_names_present_in_db = _lookup_song_presence((item[1] for item in song_queue))
            song_names_present_loaded = True
            if song_names_present_in_db:
                missing: list[tuple[str, str, str]] = []
                existing: list[tuple[str, str, str]] = []
                for item in song_queue:
                    (existing if item[1] in song_names_present_in_db else missing).append(item)
                song_queue = missing + existing
                if backend_service_mode:
                    self._backend_priority_song_names.update(str(item[1] or "").strip() for item in missing)
        except Exception as exc:
            logging.warning(f"[DB] Failed to prioritize song queue: {type(exc).__name__}: {exc}")

        # Optional deterministic limit (useful for benchmarks / iteration).
        # If resuming with DB priority, apply the limit after merging new-missing + resume.
        apply_limit = not resume_seed_queue
        if apply_limit:
            song_queue_limit = _read_song_queue_limit()
            if song_queue_limit and song_queue_limit > 0 and len(song_queue) > song_queue_limit:

                def _queue_sort_key(item: tuple[str, str, str]) -> tuple[str, str, str]:
                    return (
                        str(item[1] or "").casefold(),
                        str(item[2] or "").casefold(),
                        os.path.abspath(str(item[0] or "")).casefold(),
                    )

                # Keep DB-missing songs at the front even when a queue limit is active.
                # Without this, sorting the entire queue before truncation can drop newly
                # added songs from the limited slice.
                present = song_names_present_in_db if song_names_present_loaded else set()
                if present:
                    missing: list[tuple[str, str, str]] = []
                    existing: list[tuple[str, str, str]] = []
                    for item in song_queue:
                        (existing if item[1] in present else missing).append(item)
                    try:
                        missing = sorted(missing, key=_queue_sort_key)
                        existing = sorted(existing, key=_queue_sort_key)
                    except (ValueError, TypeError):
                        pass
                    song_queue = missing + existing
                else:
                    try:
                        song_queue = sorted(song_queue, key=_queue_sort_key)
                    except (ValueError, TypeError):
                        pass
                song_queue = song_queue[: int(song_queue_limit)]
                logger.info(f"[Queue] SongQueueLimit={song_queue_limit}: running {len(song_queue)} song(s)")

        if resume_seed_queue:
            new_missing: list[tuple[str, str, str]] = []
            try:
                if song_names_present_loaded:
                    present = song_names_present_in_db
                else:
                    present = _lookup_song_presence((item[1] for item in song_queue))
                resume_paths = {os.path.abspath(str(item[0] or "")).casefold() for item in (resume_seed_queue or [])}
                for item in song_queue:
                    try:
                        if os.path.abspath(str(item[0] or "")).casefold() in resume_paths:
                            continue
                    except (ValueError, TypeError, AttributeError):
                        pass
                    if item[1] not in present:
                        new_missing.append(item)
            except Exception as exc:
                logging.warning(f"[DB] Failed to detect new missing songs: {type(exc).__name__}: {exc}")

            if new_missing:
                try:
                    logger.info(f"[Queue] Prepending {len(new_missing)} new missing song(s) ahead of resume queue.")
                except Exception as e:
                    logger.warning(f"app:_queue_sort_key: {e}")
                if backend_service_mode:
                    self._backend_priority_song_names.update(str(item[1] or "").strip() for item in new_missing)

            merged_queue = list(new_missing) + list(resume_seed_queue)
            song_queue_limit = _read_song_queue_limit()
            if song_queue_limit and song_queue_limit > 0 and len(merged_queue) > song_queue_limit:
                merged_queue = merged_queue[: int(song_queue_limit)]
                logger.info(
                    f"[Queue] SongQueueLimit={song_queue_limit}: running {len(merged_queue)} song(s) (resume+new)"
                )
            return self._prioritize_robeatsmeta_song_queue(merged_queue)

        # Queue all discovered songs; filtering is handled by difficulty folder + optional search string.
        song_queue = self._prioritize_robeatsmeta_song_queue(song_queue)
        song_queue = self._filter_robeatsmeta_recently_computed_song_queue(song_queue)
        if not filter_search:
            return song_queue

        logger.info(f"Found {len(song_queue)} songs to process.")
        return song_queue

    def _normalize_song_label(self, label: str) -> str:
        # Strip "(Run x/y)" suffix so DB queries map to the base song key.
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
        ga_depth,
        status_queue,
        fg_debug,
    ):
        cfg_dict = cfg_to_dict(cfg)
        tasks = []
        parallel_workers = 1
        run_context = SharedRunContext(
            cfg_dict=cfg_dict,
            paths=paths,
            ref_arrays=ref_arrays,
            all_gears=all_gears,
            all_minis=all_minis,
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            ga_depth=int(ga_depth),
            status_queue=status_queue,
            parallel_workers=int(parallel_workers),
            fg_debug=bool(fg_debug),
        )

        def _append_song_task(
            fp,
            found_song_name: str,
            task_diff: str,
            *,
            repeat_ctx: dict | None = None,
            repeat_bundle: dict | None = None,
        ) -> None:
            repeat_index = 0
            repeat_total = 0
            ga_seed = None
            extras: list[typing.Any] = []
            if repeat_ctx is not None:
                repeat_index = int(repeat_ctx.get("repeat_index") or 0)
                repeat_total = int(repeat_ctx.get("repeat_total") or 0)
                seed_raw = repeat_ctx.get("ga_seed")
                ga_seed = int(seed_raw) if seed_raw is not None else None
                extras.append(repeat_ctx)
            if repeat_bundle is not None:
                repeat_total = int(repeat_bundle.get("repeat_total") or repeat_total or 0)
                extras.append(repeat_bundle)
            job = SongJob(
                file_path=fp,
                song_name=str(found_song_name or ""),
                difficulty=str(task_diff or ""),
                repeat_index=max(0, int(repeat_index)),
                repeat_total=max(0, int(repeat_total)),
                ga_seed=ga_seed,
                repeat_bundle=repeat_bundle is not None,
                queue_source="app_prepare_tasks",
            )
            tasks.append(legacy_task_tuple_from_job_context(job, run_context, *extras))

        # GA_SEED is debug-only. Production runs leave it unset and get fresh
        # per-task seeds on every preparation / LoopForever pass.
        ga_seed_base: int | None = None
        raw_ga_seed = env_get("GA_SEED")
        if raw_ga_seed is not None and str(raw_ga_seed).strip() != "":
            try:
                ga_seed_base = int(str(raw_ga_seed).strip()) & 0xFFFFFFFF
            except (ValueError, TypeError) as exc:
                raise ValueError("GA_SEED must be an integer debug seed when set") from exc

        # PRODUCTION: repeat flags.
        runtime_settings = self._current_runtime_settings(cfg)
        song_repeats = int(runtime_settings.song_repeats)
        try:
            song_repeats_env = safe_int(env_get("SONG_REPEATS", 0), 0)
            if song_repeats_env > 0:
                song_repeats = song_repeats_env
        except (ValueError, TypeError):
            pass
        song_repeats = max(1, min(int(song_repeats), 100))
        used_ga_seeds: set[int] = set()
        backend_service_mode = bool(
            getattr(getattr(self, "_robeatsmeta_api", None), "backend_mode_enabled", lambda: False)()
        )
        backend_priority_song_names = {
            str(name or "").strip()
            for name in getattr(self, "_backend_priority_song_names", set())
            if str(name or "").strip()
        }
        priority_repeat_count = max(0, int(getattr(self, "_backend_priority_song_repeat_count", 0) or 0))
        if priority_repeat_count <= 0:
            priority_repeat_count = int(song_repeats)

        def _stable_ga_seed_for_song_repeat(song_name: str, repeat_index: int) -> int:
            # Stable 32-bit seed, independent of PYTHONHASHSEED and run ordering.
            base = int(ga_seed_base or 0) & 0xFFFFFFFF
            name_crc = int(zlib.crc32(str(song_name).encode("utf-8", errors="replace")) & 0xFFFFFFFF)
            idx = int(repeat_index) & 0xFFFFFFFF
            seed = (base + name_crc + (idx * 0x9E3779B1)) & 0xFFFFFFFF
            return int(seed)

        def _build_repeat_ctx(song_name: str, *, repeat_index: int, repeat_total: int) -> dict:
            if ga_seed_base is not None:
                ga_seed = _stable_ga_seed_for_song_repeat(str(song_name), int(repeat_index))
                while ga_seed in used_ga_seeds:
                    # Extremely unlikely, but keep the uniqueness guarantee across the queue.
                    ga_seed = int((ga_seed + 1) & 0xFFFFFFFF)
            else:
                ga_seed = int(secrets.randbits(32))
                while ga_seed in used_ga_seeds:
                    ga_seed = int(secrets.randbits(32))
            used_ga_seeds.add(int(ga_seed))
            return {
                "repeat_index": int(repeat_index),
                "repeat_total": int(repeat_total),
                "ga_seed": int(ga_seed),
            }

        for fp, found_song_name, task_diff in song_queue:
            repeats_for_song = (
                priority_repeat_count
                if backend_service_mode and str(found_song_name or "").strip() in backend_priority_song_names
                else song_repeats
            )
            if repeats_for_song <= 1:
                logger.info(f"[QUEUE] {found_song_name}")
                # Production native GA must never fall back to its internal fixed seed.
                # Attach a one-run context even when SongRepeats=1 so every song has
                # an explicit per-run seed across LoopForever iterations.
                repeat_ctx = _build_repeat_ctx(str(found_song_name), repeat_index=1, repeat_total=1)
                _append_song_task(fp, found_song_name, task_diff, repeat_ctx=repeat_ctx)
                continue

            for repeat_index in range(1, repeats_for_song + 1):
                repeat_ctx = _build_repeat_ctx(
                    str(found_song_name),
                    repeat_index=int(repeat_index),
                    repeat_total=int(repeats_for_song),
                )

                logger.info(f"[QUEUE] {found_song_name} (Run {repeat_index}/{repeats_for_song})")
                _append_song_task(fp, found_song_name, task_diff, repeat_ctx=repeat_ctx)
        return tasks

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
        try:
            api = getattr(self, "_robeatsmeta_api", None)
            if api is not None and callable(getattr(api, "service_mode_enabled", None)):
                return bool(api.service_mode_enabled())
        except (ValueError, TypeError, AttributeError):
            pass
        return False

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

    def _cleanup_resources(self, status_queue, status_thread, manager):
        try:
            self._clear_robeatsmeta_runtime_status(status="idle", available=True)
            api = getattr(self, "_robeatsmeta_api", None)
            if api is not None:
                try:
                    api.flush_runtime_status(timeout=1.0)
                except Exception as e:
                    logger.warning(f"app:_cleanup_resources: {e}")
                try:
                    api.stop_runtime_status_loop(timeout=1.0)
                except Exception as e:
                    logger.warning(f"app:_cleanup_resources: {e}")
            if status_queue:
                try:
                    status_queue.put(None)
                except Exception as e:
                    logger.warning(f"app:_cleanup_resources: {e}")
            if status_thread:
                try:
                    status_thread.join(timeout=2)
                except Exception as e:
                    logger.warning(f"app:_cleanup_resources: {e}")
            if manager:
                try:
                    manager.shutdown()
                except Exception as e:
                    logger.warning(f"app:_cleanup_resources: {e}")
            # Flush pending DB writes (best-effort)
            if hasattr(self, "_async_db_saver"):
                try:
                    self._async_db_saver.shutdown(timeout=30.0)
                except Exception as e:
                    logger.warning(f"app:_cleanup_resources: {e}")
            # Force GC on manager
            old_manager = manager
            del old_manager
            gc.collect(generation=0)

        except Exception as e:
            logger.warning(f"app:_cleanup_resources: {e}")

    def _loop_restart_wait_seconds(self, cfg=None, *, default_seconds: float = 0.0) -> float:
        wait_s = float(default_seconds)
        try:
            wait_s = float(self._current_runtime_settings(cfg).loop_restart_wait_sec)
        except (ValueError, TypeError):
            pass

        for env_key in ("METAFINDER_LOOP_RESTART_WAIT_SEC", "LOOP_RESTART_WAIT_SEC"):
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
