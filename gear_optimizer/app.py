import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import gc
import logging
import multiprocessing
import queue
import os
import re
import shutil
import secrets
import sys
import zlib
import threading
import time
import typing

import numpy as np

# Import from refactored modules
from gear_optimizer.core.constants import PATHS, SCRIPT_DIR, BIN_DIR, TOTAL_ROWS, GA_POPULATION_SIZE
from gear_optimizer.core.env_config import ENV, TRUTHY_ENV_VALUES
from gear_optimizer.core.output import suppress_stdout, restore_stdout, suppress_stderr, restore_stderr
from gear_optimizer.core.config import (
    compute_memory_guard_limit,
    load_config,
    load_paths_cache,
    read_iteration_engine_settings,
)
from gear_optimizer.data.database import (
    init_db,
    get_evolution_db_path,
    get_song_names_present_in_db,
    get_song_counters,
    get_best_loadouts,
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
from gear_optimizer.core.fallback_monitor import warn_fallback
from gear_optimizer.pipeline.song_processor import safe_process_song_task, scan_song_header
from gear_optimizer.data.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from gear_optimizer.core.utils import safe_int, cfg_to_dict
from gear_optimizer.solver.scoring import FEVER_TIMELINE_CACHE, FG_CACHE
from gear_optimizer.solver.genetic import GEM_SOLVER_CACHE
from gear_optimizer.app_async_db import AsyncDbSaver
from gear_optimizer.data.stats_verifier import verify_and_repair_stats, print_verification_warning
from gear_optimizer.app_stop_control import StopController
from gear_optimizer.helpers.song_helpers.persistence import evaluate_record_update
from gear_optimizer.robeatsmeta_api import RoBeatsMetaOptimizerApi

logger = logging.getLogger(__name__)


# Module-level worker initializer for GPU executor (must be picklable)
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


class _ProgressUI:
    """Lightweight single-line progress renderer with spinner + ETA."""

    def __init__(
        self,
        total: int,
        *,
        completed: int = 0,
        failed: int = 0,
        new_records: int = 0,
        enabled: bool = True,
        bar_width: int = 24,
        update_interval: float = 0.2,
        stream=None,
    ) -> None:
        self._enabled = bool(enabled)
        self._total = max(0, int(total or 0))
        self._completed = max(0, int(completed or 0))
        self._failed = max(0, int(failed or 0))
        self._new_records = max(0, int(new_records or 0))
        self._bar_width = max(10, int(bar_width or 24))
        self._interval = max(0.05, float(update_interval or 0.2))
        self._stream = stream or getattr(sys, "__stdout__", None) or sys.stdout
        self._start = time.perf_counter()
        self._status = ""
        self._song = ""
        self._spinner = ["|", "/", "-", "\\"]
        self._frame = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self._enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="ProgressUI", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if not self._enabled:
            return
        self._stop.set()
        if self._thread is not None:
            try:
                self._thread.join(timeout=2.0)
            except Exception:
                pass
        self._render(final=True)

    def update_counts(
        self, *, completed: int | None = None, total: int | None = None, failed: int | None = None
    ) -> None:
        if not self._enabled:
            return
        with self._lock:
            if completed is not None:
                self._completed = max(0, int(completed))
            if total is not None:
                self._total = max(0, int(total))
            if failed is not None:
                self._failed = max(0, int(failed))
        self._render()

    def add_new_record(self, count: int = 1) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._new_records = max(0, int(self._new_records + int(count)))
        self._render()

    def add_completed(self, count: int = 1) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._completed = max(0, int(self._completed + int(count)))
        self._render()

    def add_failed(self, count: int = 1) -> None:
        if not self._enabled:
            return
        with self._lock:
            self._failed = max(0, int(self._failed + int(count)))
        self._render()

    def set_status(self, song: str | None, status: str | None) -> None:
        if not self._enabled:
            return
        with self._lock:
            if song is not None:
                self._song = str(song)
            if status is not None:
                self._status = str(status)
        self._render()

    def emit_block(self, lines: list[str]) -> None:
        """Print a multi-line block without fighting the single-line renderer."""
        if not self._enabled or self._stream is None:
            return
        try:
            with self._lock:
                self._stream.write("\r\x1b[K")
                self._stream.write("\n")
                for line in lines:
                    self._stream.write(str(line) + "\n")
                self._stream.flush()
        except Exception:
            pass
        self._render()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._render()
            self._stop.wait(self._interval)

    def _render(self, *, final: bool = False) -> None:
        if not self._enabled:
            return
        try:
            now = time.perf_counter()
            with self._lock:
                completed = int(self._completed)
                total = int(self._total)
                failed = int(self._failed)
                new_records = int(self._new_records)
                status = str(self._status or "")
                status_clean = status.strip()
                if status_clean.upper() == "DONE":
                    status_clean = ""
                song = str(self._song or "")
                frame = self._frame
                self._frame = (self._frame + 1) % len(self._spinner)
            elapsed = max(0.0, float(now - self._start))
            eta_s = None
            if completed > 0 and total > 0 and completed <= total:
                avg = float(elapsed) / float(completed)
                eta_s = max(0.0, float(total - completed) * avg)

            spinner = self._spinner[frame % len(self._spinner)]
            pct = (float(completed) / float(total) * 100.0) if total > 0 else 0.0
            filled = int(round((float(completed) / float(total)) * self._bar_width)) if total > 0 else 0
            filled = max(0, min(self._bar_width, filled))
            bar = "=" * filled + "-" * (self._bar_width - filled)

            eta_str = self._format_duration(eta_s) if eta_s is not None else "--:--"
            elapsed_str = self._format_duration(elapsed)

            tail = ""
            if song:
                tail += f" | Song: {song}"
            if status_clean:
                tail += f" | {status_clean}"
            if len(tail) > 60:
                tail = tail[:57] + "..."

            # Colors (best-effort); they render fine in Windows Terminal / modern consoles.
            def c(text: str, code: str) -> str:
                return f"\x1b[{code}m{text}\x1b[0m"

            spinner_s = c(spinner, "36")  # cyan
            bar_s = c(bar, "96")  # bright cyan
            pct_s = c(f"{pct:5.1f}%", "92" if pct >= 99.9 else "36")
            new_s = c(str(new_records), "92")  # green
            failed_s = c(str(failed), "91")  # red
            line = (
                f"{spinner_s} [{bar_s}] {completed}/{total} {pct_s} "
                f"| ETA {eta_str} | Elapsed {elapsed_str} | New: {new_s} | Failed: {failed_s}{tail}"
            )
            self._write(line, final=final)
        except Exception:
            pass

    def _write(self, line: str, *, final: bool = False) -> None:
        if not self._enabled or self._stream is None:
            return
        try:
            term_width = 0
            try:
                term_width = int(shutil.get_terminal_size(fallback=(0, 0)).columns or 0)
            except Exception:
                term_width = 0
            if term_width > 0:
                line = self._truncate_ansi(line, max_len=max(1, term_width - 1))
            # `\x1b[K` clears to end-of-line, avoiding needing to pad (and avoiding ANSI-length math).
            self._stream.write("\r" + line + "\x1b[K")
            if final:
                self._stream.write("\n")
            self._stream.flush()
        except Exception:
            pass

    @staticmethod
    def _truncate_ansi(text: str, *, max_len: int) -> str:
        if max_len <= 0:
            return ""
        ansi_re = re.compile(r"\x1b\[[0-9;]*m")
        out = []
        visible = 0
        i = 0
        n = len(text)
        while i < n and visible < max_len:
            if text[i] == "\x1b":
                m = ansi_re.match(text, i)
                if m:
                    out.append(m.group(0))
                    i = m.end()
                    continue
            out.append(text[i])
            visible += 1
            i += 1
        out.append("\x1b[0m")
        return "".join(out)

    @staticmethod
    def _format_duration(seconds: float | None) -> str:
        if seconds is None:
            return "--:--"
        try:
            total = int(max(0.0, float(seconds)))
        except Exception:
            total = 0
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


def _stream_is_tty(stream) -> bool:
    try:
        isatty = getattr(stream, "isatty", None)
        if callable(isatty):
            return bool(isatty())
    except Exception:
        return False
    return False


def _progress_ui_enabled_default(
    *,
    configured_enabled: bool,
    output_enabled: bool,
    progress_env_present: bool,
    stream_is_tty: bool,
) -> bool:
    if not bool(configured_enabled):
        return False
    if bool(output_enabled) and not bool(progress_env_present):
        return False
    if (not bool(progress_env_present)) and (not bool(stream_is_tty)):
        return False
    return True


def _banner_enabled_default(*, stream_is_tty: bool, banner_env: str | None) -> bool:
    raw = str(banner_env or "").strip().lower()
    if not raw:
        return bool(stream_is_tty)
    return raw in TRUTHY_ENV_VALUES


class GearOptimizerApp:
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
            banner_env=os.environ.get("METAFINDER_BANNER"),
        )
        self._progress_interval = float(getattr(ENV, "progress_interval_sec", 0.2))
        self._progress_bar_width = int(getattr(ENV, "progress_bar_width", 24))
        self._progress: _ProgressUI | None = None
        # Separate-process TUI (default) keeps console IO out of the compute/GPU owner process.
        self._tui_enabled = True
        try:
            raw = os.environ.get("METAFINDER_UI_PROCESS")
            if raw is not None and str(raw).strip() != "":
                self._tui_enabled = self._truthy(raw)
        except Exception:
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
        self._runtime_completed_count = 0
        self._runtime_total_count = 0
        self._runtime_failed_count = 0
        self._backend_priority_song_names: set[str] = set()
        # Optional override for pending-visit songs. 0 means "use SongRepeats".
        try:
            self._backend_priority_song_repeat_count = max(
                0,
                int(os.environ.get("ROBEATSMETA_OPTIMIZER_PRIORITY_REPEAT_COUNT", "0") or "0"),
            )
        except Exception:
            self._backend_priority_song_repeat_count = 0
        self._song_path_index_lock = threading.Lock()
        self._song_path_index: dict[str, list[dict[str, str]]] = {}
        self._song_path_index_ready = False
        self._song_path_index_roots: tuple[str, ...] = ()
        self._song_path_index_last_force_attempt_monotonic = 0.0
        self._song_path_index_force_cooldown_sec = 60.0
        self._robeatsmeta_api: RoBeatsMetaOptimizerApi | None = None

    def setup_logging(self) -> None:
        # Keep stdout clean for result printers; send diagnostics to stderr.
        try:
            from gear_optimizer.core.logging_config import configure_logging

            log_file_path = os.path.join(BIN_DIR, "error.log")
            console_level = logging.INFO if bool(getattr(ENV, "output_enabled", False)) else logging.ERROR
            configure_logging(log_file_path=log_file_path, console_level=console_level, file_level=logging.WARNING)
        except Exception:
            pass

    def request_stop(self, reason: str, *, force: bool = False) -> None:
        return self._stop_control.request_stop(reason, force=force)

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
        try:
            return bool(cfg.getboolean(section, key, fallback=fallback))
        except Exception:
            try:
                raw = str(cfg.get(section, key, fallback=str(int(bool(fallback)))) or "").strip().lower()
                return raw in TRUTHY_ENV_VALUES
            except Exception:
                return bool(fallback)

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
            if str(os.environ.get(key, "") or "").strip().lower() in TRUTHY_ENV_VALUES:
                return True

        path_keys = (
            "GPU_EXECUTOR_TRACE_PATH",
            "INFLIGHT_STAGE_PROFILE_PATH",
            "METAFINDER_PROFILE_EVENTS_PATH",
            "PROFILE_EVENTS_PATH",
        )
        for key in path_keys:
            if str(os.environ.get(key, "") or "").strip():
                return True

        # DEV / DEBUG: profile-only config overrides (Debug.DebugProfile, IterationEngine.DebugProfile).
        if cfg is not None:
            if self._cfg_truthy(cfg, "Debug", "DebugProfile", fallback=False):
                return True
            if self._cfg_truthy(cfg, "IterationEngine", "DebugProfile", fallback=False):
                return True
        return False

    def _optimizer_priority_api_enabled(self) -> bool:
        api = getattr(self, "_robeatsmeta_api", None)
        if api is None:
            return False
        try:
            return bool(api.priority_queue_enabled())
        except Exception:
            return bool(api.backend_mode_enabled())

    def _prioritize_robeatsmeta_song_queue(
        self,
        song_queue: list[tuple[str, str, str]],
    ) -> list[tuple[str, str, str]]:
        if not song_queue or not self._optimizer_priority_api_enabled():
            return song_queue
        api = self._robeatsmeta_api
        if api is None:
            return song_queue
        try:
            priority_names = {
                str(name or "").strip()
                for name in getattr(self, "_backend_priority_song_names", set())
                if str(name or "").strip()
            }
            if priority_names:
                priority_front = [item for item in song_queue if str(item[1] or "").strip() in priority_names]
                remainder = [item for item in song_queue if str(item[1] or "").strip() not in priority_names]
                prioritized_remainder = api.prioritize_song_queue(remainder)
                return priority_front + prioritized_remainder
            return api.prioritize_song_queue(song_queue)
        except Exception as exc:
            logging.warning(f"[RoBeatsMeta] Failed to prioritize song queue: {type(exc).__name__}: {exc}")
            return song_queue

    def _filter_robeatsmeta_recently_computed_song_queue(
        self,
        song_queue: list[tuple[str, str, str]],
    ) -> list[tuple[str, str, str]]:
        if not song_queue or not self._optimizer_priority_api_enabled():
            return song_queue
        api = self._robeatsmeta_api
        if api is None:
            return song_queue
        try:
            recent_bundle_keys = api.recently_computed_bundle_keys()
        except Exception as exc:
            logging.warning(f"[RoBeatsMeta] Failed to read recently computed bundles: {type(exc).__name__}: {exc}")
            return song_queue
        if not recent_bundle_keys:
            return song_queue

        filtered: list[tuple[str, str, str]] = []
        for item in song_queue:
            try:
                song_name = str(item[1] or "").strip()
            except Exception:
                filtered.append(item)
                continue
            try:
                bundle_key = api._bundle_key_for_song_id(song_name)
            except Exception:
                filtered.append(item)
                continue
            if str(bundle_key or "").strip() in recent_bundle_keys:
                continue
            filtered.append(item)
        return filtered

    def _maybe_mark_robeatsmeta_song_batch_computed(
        self,
        song_name: str | None,
        completed_songs: set[str] | None = None,
    ) -> bool:
        if not song_name or not self._optimizer_priority_api_enabled():
            return False
        api = self._robeatsmeta_api
        if api is None:
            return False
        tasks = getattr(self, "_run_tasks_ref", None)
        if not isinstance(tasks, list) or not tasks:
            return False
        completed = completed_songs if isinstance(completed_songs, set) else getattr(self, "_run_completed_ref", None)
        if not isinstance(completed, set):
            return False

        try:
            target_bundle_key = api._bundle_key_for_song_id(str(song_name))
        except Exception:
            return False
        if not str(target_bundle_key or "").strip():
            return False

        for task in tasks:
            try:
                task_label = self._task_queue_label(task)
            except Exception:
                continue
            if not task_label or task_label in completed:
                continue
            try:
                task_bundle_key = api._bundle_key_for_song_id(str(task_label))
            except Exception:
                continue
            if str(task_bundle_key or "").strip() == str(target_bundle_key or "").strip():
                return False

        try:
            api.mark_song_computed(song_id=str(song_name))
            return True
        except Exception as exc:
            logging.warning(f"[RoBeatsMeta] Failed to mark song batch computed: {type(exc).__name__}: {exc}")
            return False

    def _mark_robeatsmeta_song_started(self, song_name: str | None) -> None:
        if not song_name or not self._optimizer_priority_api_enabled():
            return
        api = self._robeatsmeta_api
        if api is None:
            return
        try:
            api.mark_song_started(song_id=str(song_name))
            # Keep runtime status aligned with backend queue state. Some execution
            # paths can mark a song active before the next progress event lands.
            # Without this, the frontend may keep showing idle while work is active.
            api.update_runtime_status(
                status="running",
                current_song=str(song_name),
                completed=int(self._runtime_completed_count or 0),
                total=int(self._runtime_total_count or 0),
                failed=int(self._runtime_failed_count or 0),
            )
        except Exception as exc:
            logging.warning(f"[RoBeatsMeta] Failed to mark song started: {type(exc).__name__}: {exc}")

    def _update_robeatsmeta_runtime_status(
        self,
        *,
        status: str | None = None,
        current_song: str | None = None,
        completed: int | None = None,
        total: int | None = None,
        failed: int | None = None,
    ) -> None:
        api = getattr(self, "_robeatsmeta_api", None)
        if api is None:
            return
        try:
            api.update_runtime_status(
                status=status,
                current_song=current_song,
                completed=completed,
                total=total,
                failed=failed,
            )
        except Exception as exc:
            logging.warning(f"[RoBeatsMeta] Failed to update runtime status: {type(exc).__name__}: {exc}")

    def _clear_robeatsmeta_runtime_status(self, *, status: str = "idle", available: bool = True) -> None:
        api = getattr(self, "_robeatsmeta_api", None)
        if api is None:
            return
        try:
            api.clear_runtime_status(status=status, available=available)
        except Exception as exc:
            logging.warning(f"[RoBeatsMeta] Failed to clear runtime status: {type(exc).__name__}: {exc}")

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
        except Exception:
            pass

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
                    loop_forever_effective = cfg.get("IterationEngine", "LoopForever", fallback="?")
                    song_repeats_effective = cfg.get("IterationEngine", "SongRepeats", fallback="?")
                    inflight_songs_effective = cfg.get("IterationEngine", "InFlightSongs", fallback="?")
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

    def _configure_gpu_execution_and_prewarm(self, cfg) -> None:
        # If the GPU executor initializes Taichi before the GA code runs, Taichi fields can be allocated with
        # default (padded) GA run buffers, making GPU-native GA payload downloads significantly slower.
        # Publish a conservative sizing hint early so any first-use allocation can pick tighter shapes.
        # PRODUCTION: GPU execution flags (GPU_Mode, GPU_Native_GA, GA_MultiStart).
        gpu_mode_requested = True
        try:
            gpu_mode_requested = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=True)
        except Exception:
            gpu_mode_requested = True
        if not gpu_mode_requested:
            logger.warning("[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); forcing GPU_Mode=true.")
            try:
                if not cfg.has_section("IterationEngine"):
                    cfg.add_section("IterationEngine")
                cfg.set("IterationEngine", "GPU_Mode", "true")
            except Exception:
                pass

        gpu_native_ga = True
        try:
            gpu_native_ga = cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=True)
        except Exception:
            gpu_native_ga = True

        if gpu_native_ga:
            ga_multistart = safe_int(cfg.get("IterationEngine", "GA_MultiStart", fallback=1), 1)
            ga_multistart = max(1, int(ga_multistart))
            os.environ.setdefault("GPU_NATIVE_GA_MAX_RUNS", str(ga_multistart))
            os.environ.setdefault("GPU_NATIVE_GA_MAX_GENOMES", str(int(GA_POPULATION_SIZE)))
            try:
                from gear_optimizer.solver.taichi_gem import fields as gpu_fields

                gpu_fields.configure_ga_run_buffers(max_runs=ga_multistart, max_genomes=int(GA_POPULATION_SIZE))
            except Exception:
                pass

        # InFlightSongs uses the singleton in-process GPU executor. Start it early so
        # Taichi init + kernel warmups overlap with CPU-heavy data/path loading.
        # This improves first-task latency on macOS where Metal JIT can be costly.
        # PRODUCTION: in-flight overlap flag (InFlightSongs).
        try:
            inflight_req = int(self._get_inflight_songs_requested(cfg) or 0)
        except Exception:
            inflight_req = 0
        if inflight_req > 1:
            try:
                from gear_optimizer.solver.gpu_executor import get_gpu_executor

                get_gpu_executor().start(in_process=True)
            except Exception:
                pass

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
            ignore_resume = os.environ.get("METAFINDER_IGNORE_RESUME_QUEUE", "").lower() in ("1", "true", "yes")
            memory_resume_exists = os.path.exists(MEMORY_GUARD_RESUME_FILE)
            is_fresh_queue = ignore_resume or not memory_resume_exists
            skip_stats_verify = bool(self._truthy(os.environ.get("METAFINDER_SKIP_STATS_INTEGRITY_VERIFY", "")))

            if is_fresh_queue:
                if skip_stats_verify:
                    if not self._stats_verified_once:
                        logger.info("[Benchmark] Skipping stats integrity verification.")
                        self._stats_verified_once = True
                elif not self._stats_verified_once:
                    self._verify_stats_integrity()
                    self._stats_verified_once = True

            # Config reading
            ie = read_iteration_engine_settings(cfg)
            meta_finder = bool(ie.meta_finder)
            enable_auto = bool(meta_finder)
            auto_buff = bool(ie.auto_select_buff_and_color)
            fg_debug = bool(ie.force_greats_debug)

            if ie.force_greats_mode:
                if ie.force_greats_finder:
                    fg_status = "ForceGreatsFinder"
                elif ie.manual_force_greats:
                    fg_status = f"Manual Config {list(ie.force_greats_config or [])}"
                else:
                    fg_status = "Enabled but inactive (no manual config; ForceGreatsFinder=false)"

                logger.info(f" >> [ForceGreats] {fg_status}")

            # PRODUCTION: runtime / persistence flags (GA_SearchDepth, UseEvolutionDB, LoopForever, EvalCPUCores).
            ga_depth = safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=50))
            use_evo_db = cfg.getboolean("IterationEngine", "UseEvolutionDB", fallback=True)
            loop_forever = cfg.getboolean("IterationEngine", "LoopForever", fallback=False)
            if self._profiling_mode_enabled(cfg):
                if loop_forever:
                    logger.warning("[Profiling] LoopForever=true ignored; forcing LoopForever=false.")
                    emit_profile_event(
                        component="app",
                        event="profiling_forced_loop_forever_off",
                        metrics={"requested_loop_forever": 1},
                    )
                loop_forever = False
            eval_cpu_limit = safe_int(cfg.get("IterationEngine", "EvalCPUCores", fallback=0))
            self._apply_inflight_overrides(cfg)
            self._maybe_apply_inflight_ram_mode(cfg)
            self._maybe_autoset_gpu_song_slots(cfg)

            self._configure_gpu_execution_and_prewarm(cfg)

            stats_table = read_table(paths.get("Stats", "") or PATHS.stats_csv)

            # CRITICAL FIX: Prevent DB tainting by disabling inputs in auto mode
            if enable_auto:
                self._disable_inputs_to_prevent_taint(cfg)

            ref_arrays = self._preload_ref_arrays(stats_table)
            all_gears = load_all_gears_list(paths)
            all_minis = load_all_minis_list(paths)
            gears_by_name = {g["Name"]: g for g in all_gears}
            minis_by_name = {m["Name"]: m for m in all_minis}

            song_queue = self._build_song_queue(cfg, paths, use_evo_db)
            queued_songs = len(song_queue)
            try:
                logger.info(f"[Run] Queued {len(song_queue)} song(s) for processing.")
            except Exception:
                pass
            emit_profile_event(
                component="app",
                event="queue_built",
                metrics={"queued_songs": int(queued_songs)},
            )

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
                use_evo_db,
                auto_buff,
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
                manager,
                status_queue,
                status_thread,
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
            except Exception:
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
                    except Exception:
                        repeats_est = 1
                    try:
                        completed_songs_est = int(round(float(completed_tasks) / float(repeats_est)))
                    except Exception:
                        completed_songs_est = int(completed_tasks)
                    completed_songs_est = min(int(queued_songs), max(0, int(completed_songs_est)))

                    songs_per_h = float(completed_songs_est) / elapsed_h if completed_songs_est > 0 else 0.0
                    tasks_per_h = float(completed_tasks) / elapsed_h if completed_tasks > 0 else 0.0
                    logger.info(
                        f"[Throughput] Completed {completed_tasks}/{total_tasks} task(s) "
                        f"(queue={queued_songs} song(s)) -> {songs_per_h:.1f} songs/hour, {tasks_per_h:.1f} tasks/hour"
                    )
                except Exception:
                    pass
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
            except Exception:
                pass
            return False

        if memory_guard_restart:
            restart_process_for_memory_guard()
            return False  # Process replaced
        elif loop_forever:
            self._handle_loop_restart(wait_time=3)
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
        stat_names = [
            "Perfect Points",
            "Combo Multiplier",
            "Fever Multiplier",
            "Fever Fill Rate",
            "Fever Time",
        ]
        ref_arrays = {}
        for i, name in enumerate(stat_names):
            temp_list = []
            for v in range(TOTAL_ROWS + 1):
                lookup_index = TOTAL_ROWS - v
                try:
                    val = stats_table[lookup_index][i] if stats_table else 0
                except Exception:
                    val = 0
                temp_list.append(val)
            ref_arrays[name] = np.array(temp_list, dtype=np.float32)
        return ref_arrays

    def _get_filter_params(self, cfg):
        diff = cfg.get("CalculateSong", "Difficulty", fallback="Hard")
        diff_lower = diff.strip().lower()
        filter_search = cfg.get("CalculateSong", "Song_Name", fallback="").strip().lower()

        def _parse_color_targets(raw_val):
            tokens = [c.strip().lower() for c in re.split(r"[,\|/]", raw_val or "") if c and c.strip()]
            is_all = not tokens or any(c in ("all", "any", "*") for c in tokens)
            return is_all, set() if is_all else set(tokens)

        target_primary_raw = cfg.get("CalculateSong", "TargetPrimary", fallback="")
        target_secondary_raw = cfg.get("CalculateSong", "TargetSecondary", fallback="")
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
        parent_folder = os.path.basename(str(root or "")).lower()
        if parent_folder == "hard":
            return "Hard"
        if parent_folder == "normal":
            return "Normal"
        if parent_folder == "easy":
            return "Easy"
        return "Unknown"

    def _song_index_roots(self) -> list[str]:
        data_root = PATHS.data_dir
        if os.path.exists(data_root):
            return [data_root]
        return [SCRIPT_DIR]

    def _scan_song_paths_for_index(self, roots: typing.Sequence[str]) -> dict[str, list[dict[str, str]]]:
        index: dict[str, list[dict[str, str]]] = {}
        seen_paths: set[str] = set()
        for root_dir in roots:
            if not os.path.exists(root_dir):
                continue
            if self._stop_requested_now():
                break
            for current_root, _, files in os.walk(root_dir):
                if self._stop_requested_now():
                    break
                for file_name in files:
                    if self._stop_requested_now():
                        break
                    if not str(file_name or "").lower().endswith(".txt"):
                        continue
                    fp = os.path.join(current_root, file_name)
                    abs_fp = os.path.abspath(fp)
                    if abs_fp in seen_paths:
                        continue
                    seen_paths.add(abs_fp)

                    meta = scan_song_header(fp)
                    if not meta:
                        continue
                    song_name = str(meta.get("Song Name") or "").strip()
                    if not song_name:
                        continue

                    detected_diff = self._infer_song_difficulty_from_path(current_root)
                    index.setdefault(song_name, []).append(
                        {
                            "fp": fp,
                            "abs_fp": abs_fp,
                            "song_name": song_name,
                            "song_name_lower": song_name.lower(),
                            "detected_diff": detected_diff,
                            "primary_color": str(meta.get("Primary Color") or "").strip().lower(),
                            "secondary_color": str(meta.get("Secondary Color") or "").strip().lower(),
                        }
                    )
        return index

    def _ensure_song_path_index(self, *, force: bool = False) -> None:
        roots = tuple(self._song_index_roots())
        with self._song_path_index_lock:
            if not force and self._song_path_index_ready and roots == self._song_path_index_roots:
                return
        index = self._scan_song_paths_for_index(roots)
        with self._song_path_index_lock:
            self._song_path_index = index
            self._song_path_index_ready = True
            self._song_path_index_roots = roots

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
        self._ensure_song_path_index(force=False)
        with self._song_path_index_lock:
            index_snapshot = dict(self._song_path_index)

        song_queue: list[tuple[str, str, str]] = []
        unresolved_song_ids: list[str] = []
        seen_paths: set[str] = set()
        for pending_song_id in pending_song_ids:
            song_id = str(pending_song_id or "").strip()
            if not song_id:
                continue
            entries = index_snapshot.get(song_id)
            if not isinstance(entries, list) or not entries:
                unresolved_song_ids.append(song_id)
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                detected_diff = str(entry.get("detected_diff") or "Unknown").strip() or "Unknown"
                if diff_lower in ("easy", "normal", "hard") and detected_diff.lower() != diff_lower:
                    continue

                primary_color = str(entry.get("primary_color") or "").strip().lower()
                secondary_color = str(entry.get("secondary_color") or "").strip().lower()
                if not target_primary_all and (not primary_color or primary_color not in target_primary_colors):
                    continue
                if not target_secondary_all and (not secondary_color or secondary_color not in target_secondary_colors):
                    continue

                song_name_lower = str(entry.get("song_name_lower") or "").strip().lower()
                if filter_search and filter_search not in song_name_lower:
                    continue

                fp = str(entry.get("fp") or "").strip()
                abs_fp = str(entry.get("abs_fp") or "").strip()
                if not fp:
                    continue
                if abs_fp and abs_fp in seen_paths:
                    continue
                if abs_fp:
                    seen_paths.add(abs_fp)
                song_name = str(entry.get("song_name") or song_id).strip() or song_id
                song_queue.append((fp, song_name, detected_diff))
        return song_queue, unresolved_song_ids

    def _build_song_queue(self, cfg, paths, use_evo_db):
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
            limit = 0
            # PRODUCTION: queue / resume flag (SongQueueLimit).
            try:
                limit = safe_int(cfg.get("IterationEngine", "SongQueueLimit", fallback="0"), 0)
            except Exception:
                limit = 0
            for env_key in ("SONG_QUEUE_LIMIT", "METAFINDER_SONG_QUEUE_LIMIT"):
                raw = os.environ.get(env_key)
                if raw is None:
                    continue
                try:
                    env_val = safe_int(raw, 0)
                except Exception:
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
        ignore_resume = False
        # PRODUCTION: queue / resume flag (IgnoreResumeQueue).
        try:
            ignore_resume = cfg.getboolean("IterationEngine", "IgnoreResumeQueue", fallback=False)
        except Exception:
            ignore_resume = False
        if backend_service_mode:
            # Backend queue order and persistence come from the API bridge state file.
            # Ignore memory-guard resume files to avoid replaying stale broad queues.
            ignore_resume = True
        if self._truthy(os.environ.get("METAFINDER_IGNORE_RESUME_QUEUE", "")):
            ignore_resume = True

        if not ignore_resume:
            resume_seed_queue = load_memory_guard_resume_queue(resume_context)
            if resume_seed_queue:
                logger.info(f"[MemoryGuard] Resuming {len(resume_seed_queue)} song(s) from previous interrupted run.")
                if use_evo_db:
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
                else:
                    # Optional deterministic limit (useful for benchmarks / iteration), even in resume mode.
                    song_queue_limit = _read_song_queue_limit()
                    if song_queue_limit and song_queue_limit > 0 and len(resume_seed_queue) > song_queue_limit:
                        resume_seed_queue = resume_seed_queue[: int(song_queue_limit)]
                        logger.info(
                            f"[Queue] SongQueueLimit={song_queue_limit}: running {len(resume_seed_queue)} song(s) (resume)"
                        )
                    return resume_seed_queue

        pending_song_ids = _pending_backend_song_ids()
        pending_set = set(pending_song_ids)
        pending_only_mode = bool(
            backend_service_mode and self._truthy(os.environ.get("ROBEATSMETA_OPTIMIZER_PENDING_ONLY", ""))
        )
        diff = cfg.get("CalculateSong", "Difficulty", fallback="Hard")
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
                except Exception:
                    pass

        if not song_queue and not resume_seed_queue:
            if backend_service_mode:
                return []
            logger.error("Error: No matching songs found.")
            return []

        try:
            logger.info(f"[Queue] Discovered {len(song_queue)} song(s) (Difficulty={diff})")
        except Exception:
            pass

        song_names_present_in_db: set[str] = set()
        song_names_present_loaded = False
        if use_evo_db:
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
        apply_limit = not (resume_seed_queue and use_evo_db)
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
                if use_evo_db:
                    present = song_names_present_in_db if song_names_present_loaded else set()
                    if present:
                        missing: list[tuple[str, str, str]] = []
                        existing: list[tuple[str, str, str]] = []
                        for item in song_queue:
                            (existing if item[1] in present else missing).append(item)
                        try:
                            missing = sorted(missing, key=_queue_sort_key)
                            existing = sorted(existing, key=_queue_sort_key)
                        except Exception:
                            pass
                        song_queue = missing + existing
                    else:
                        try:
                            song_queue = sorted(song_queue, key=_queue_sort_key)
                        except Exception:
                            pass
                else:
                    try:
                        song_queue = sorted(song_queue, key=_queue_sort_key)
                    except Exception:
                        pass
                song_queue = song_queue[: int(song_queue_limit)]
                logger.info(f"[Queue] SongQueueLimit={song_queue_limit}: running {len(song_queue)} song(s)")

        if resume_seed_queue and use_evo_db:
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
                    except Exception:
                        pass
                    if item[1] not in present:
                        new_missing.append(item)
            except Exception as exc:
                logging.warning(f"[DB] Failed to detect new missing songs: {type(exc).__name__}: {exc}")

            if new_missing:
                try:
                    logger.info(f"[Queue] Prepending {len(new_missing)} new missing song(s) ahead of resume queue.")
                except Exception:
                    pass
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

    def _start_progress(self, total_tasks: int, *, completed: int = 0) -> None:
        self._set_runtime_progress_counts(completed=int(completed or 0), total=int(total_tasks or 0), failed=0)
        self._runtime_status_name = "queued"
        self._update_robeatsmeta_runtime_status(
            status="queued",
            current_song="",
            completed=int(completed or 0),
            total=int(total_tasks or 0),
            failed=0,
        )
        if not self._progress_enabled:
            return
        if self._tui_enabled:
            self._start_tui(total_tasks=total_tasks, completed=completed)
            return
        stream = self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout
        self._progress = _ProgressUI(
            total_tasks,
            completed=completed,
            new_records=self._session_new_records,
            enabled=True,
            bar_width=self._progress_bar_width,
            update_interval=self._progress_interval,
            stream=stream,
        )
        self._progress.start()

    def _stop_progress(self) -> None:
        self._runtime_status_name = "idle"
        self._clear_robeatsmeta_runtime_status(status="idle", available=True)
        self._stop_tui()
        if self._progress is None:
            return
        try:
            self._progress.stop()
        finally:
            self._progress = None

    def _tui_active(self) -> bool:
        proc = getattr(self, "_tui_process", None)
        if proc is None:
            return False
        try:
            return bool(proc.is_alive())
        except Exception:
            return True

    def _start_tui(self, *, total_tasks: int, completed: int = 0) -> None:
        if self._tui_active():
            # New run/iteration: bump epoch so the UI resets its elapsed/ETA.
            try:
                self._tui_epoch = int(self._tui_epoch) + 1
            except Exception:
                self._tui_epoch = 1
            self._tui_publish(song="", status=str(self._runtime_status_name or "queued"))
            return

        try:
            from gear_optimizer.ui.progress_ipc import SharedProgress
            from gear_optimizer.ui.tui_process import run_tui_process

            ctx = multiprocessing.get_context("spawn") if os.name == "nt" else multiprocessing.get_context()
            self._tui_epoch = int(self._tui_epoch) + 1
            self._tui_progress = SharedProgress.create()
            self._tui_stop_event = ctx.Event()
            self._tui_cmd_queue = ctx.Queue(maxsize=64)
            self._tui_resp_queue = ctx.Queue(maxsize=64)
            self._tui_process = ctx.Process(
                target=run_tui_process,
                kwargs={
                    "progress_shm_name": str(self._tui_progress.name),
                    "stop_event": self._tui_stop_event,
                    "cmd_queue": self._tui_cmd_queue,
                    "resp_queue": self._tui_resp_queue,
                    "bar_width": int(self._progress_bar_width),
                    "update_interval": float(self._progress_interval),
                },
                name="MetaFinderTUI",
                daemon=True,
            )
            self._tui_process.start()
            self._disable_console_logging_for_tui()
        except Exception:
            # Best-effort: if we can't start UI, keep compute safe by disabling progress (no fallback to in-proc prints).
            self._tui_enabled = False
            self._progress_enabled = False
            try:
                if self._tui_progress is not None:
                    self._tui_progress.close()
                    self._tui_progress.unlink()
            except Exception:
                pass
            self._tui_progress = None
            self._tui_process = None
            self._tui_stop_event = None
            self._tui_cmd_queue = None
            self._tui_resp_queue = None
            return

        self._tui_publish(
            song="",
            status=str(self._runtime_status_name or "queued"),
            completed=int(completed or 0),
            total=int(total_tasks or 0),
            failed=0,
        )

    def _disable_console_logging_for_tui(self) -> None:
        if self._output_enabled:
            return
        root = logging.getLogger()
        try:
            stderr = sys.stderr
        except Exception:
            stderr = None
        try:
            real_stderr = getattr(sys, "__stderr__", None)
        except Exception:
            real_stderr = None

        for handler in list(getattr(root, "handlers", []) or []):
            stream = getattr(handler, "stream", None)
            if stream is None:
                continue
            if stderr is not None and stream is stderr:
                try:
                    root.removeHandler(handler)
                except Exception:
                    pass
                try:
                    handler.close()
                except Exception:
                    pass
                continue
            if real_stderr is not None and stream is real_stderr:
                try:
                    root.removeHandler(handler)
                except Exception:
                    pass
                try:
                    handler.close()
                except Exception:
                    pass
                continue

    def _stop_tui(self) -> None:
        proc = getattr(self, "_tui_process", None)
        if proc is None:
            return
        try:
            if self._tui_stop_event is not None:
                self._tui_stop_event.set()
        except Exception:
            pass
        try:
            proc.join(timeout=2.0)
        except Exception:
            pass
        try:
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=2.0)
        except Exception:
            pass
        self._tui_process = None
        self._tui_stop_event = None
        self._stop_tui_command_thread()
        try:
            if self._tui_cmd_queue is not None:
                self._tui_cmd_queue.close()
        except Exception:
            pass
        try:
            if self._tui_resp_queue is not None:
                self._tui_resp_queue.close()
        except Exception:
            pass
        self._tui_cmd_queue = None
        self._tui_resp_queue = None
        try:
            if self._tui_progress is not None:
                self._tui_progress.close()
                self._tui_progress.unlink()
        except Exception:
            pass
        self._tui_progress = None

    def _tui_publish(
        self,
        *,
        song: str | None,
        status: str | None,
        completed: int | None = None,
        total: int | None = None,
        failed: int | None = None,
        new_records: int | None = None,
    ) -> None:
        progress = getattr(self, "_tui_progress", None)
        if progress is None:
            return
        try:
            c = int(self._runtime_completed_count or 0) if completed is None else int(completed or 0)
            t = int(self._runtime_total_count or 0) if total is None else int(total or 0)
            f = int(self._runtime_failed_count or 0) if failed is None else int(failed or 0)
            n = int(self._session_new_records or 0) if new_records is None else int(new_records or 0)
        except Exception:
            c = int(completed or 0)
            t = int(total or 0)
            f = int(failed or 0)
            n = int(new_records or 0)
        try:
            progress.update(
                epoch=int(self._tui_epoch),
                completed=max(0, int(c)),
                total=max(0, int(t)),
                failed=max(0, int(f)),
                new_records=max(0, int(n)),
                song=str(song or ""),
                status=str(status or ""),
            )
        except Exception:
            return

    def _progress_event(
        self,
        *,
        completed_delta: int = 0,
        failed_delta: int = 0,
        record_info: dict | None = None,
    ) -> None:
        song_label = ""
        status_label = ""
        record_update = bool(record_info and record_info.get("record_update"))
        if record_update:
            try:
                self._session_new_records = int(self._session_new_records) + 1
            except Exception:
                self._session_new_records = 1
        if completed_delta:
            self._runtime_completed_count = max(
                0,
                int(self._runtime_completed_count or 0) + int(completed_delta or 0),
            )
        if failed_delta:
            self._runtime_failed_count = max(
                0,
                int(self._runtime_failed_count or 0) + int(failed_delta or 0),
            )
        if isinstance(record_info, dict):
            try:
                song_label = str(
                    record_info.get("song") or record_info.get("_song_name") or record_info.get("_queue_label") or ""
                ).strip()
                status_label = str(record_info.get("status") or "").strip()
                if song_label:
                    self._run_current_song_label = str(song_label)
                    if not status_label:
                        status_label = "running"
            except Exception:
                pass
        if not status_label:
            if failed_delta:
                status_label = "failed"
            elif completed_delta:
                status_label = "done"
            elif self._run_current_song_label:
                status_label = str(self._runtime_status_name or "running")
            else:
                status_label = "running"
        self._runtime_status_name = str(status_label or self._runtime_status_name or "running")
        status_lower = str(self._runtime_status_name or "").strip().lower()
        if song_label:
            try:
                if status_lower.startswith("running"):
                    self._mark_robeatsmeta_song_started(str(song_label))
            except Exception:
                pass
        if self._progress is not None:
            try:
                if song_label:
                    self._progress.set_status(str(song_label), str(status_label))
                elif self._run_current_song_label:
                    self._progress.set_status(str(self._run_current_song_label), str(status_label))
            except Exception:
                pass
            if completed_delta:
                self._progress.add_completed(int(completed_delta))
            if failed_delta:
                self._progress.add_failed(int(failed_delta))
            if record_update:
                score = int(record_info.get("score", 0) or 0)
                best_fg = int(record_info.get("best_fg_score_run", 0) or 0)
                if score > 0 or best_fg > 0:
                    self._progress.add_new_record(1)
        else:
            try:
                current_song = str(song_label or self._run_current_song_label or "").strip()
            except Exception:
                current_song = ""
            self._tui_publish(song=current_song, status=str(status_label or self._runtime_status_name or ""))
        self._update_robeatsmeta_runtime_status(
            status=self._runtime_status_name,
            current_song=str(song_label or self._run_current_song_label or ""),
            completed=int(self._runtime_completed_count or 0),
            total=int(self._runtime_total_count or 0),
            failed=int(self._runtime_failed_count or 0),
        )

    def _handle_status_message(self, msg: str) -> None:
        if not msg:
            return
        song = None
        status = str(msg)
        if status.startswith("[") and "]" in status:
            try:
                end = status.index("]")
                song = status[1:end]
                status = status[end + 1 :].strip()
            except Exception:
                song = None
        if not self._progress_counts_driven and status.upper().startswith("DONE"):
            self._runtime_completed_count = max(0, int(self._runtime_completed_count or 0) + 1)
            if self._progress is not None:
                self._progress.add_completed(1)
            else:
                self._tui_publish(song=str(song or self._run_current_song_label or ""), status=str(status or ""))
        if song:
            self._run_current_song_label = str(song)
            if status.strip().lower().startswith("running"):
                self._mark_robeatsmeta_song_started(str(song))
        self._runtime_status_name = str(status or self._runtime_status_name or "running")
        if self._progress is not None:
            self._progress.set_status(song, status)
        else:
            self._tui_publish(song=str(song or self._run_current_song_label or ""), status=str(status or ""))
        self._update_robeatsmeta_runtime_status(
            status=self._runtime_status_name,
            current_song=str(song or self._run_current_song_label or ""),
            completed=int(self._runtime_completed_count or 0),
            total=int(self._runtime_total_count or 0),
            failed=int(self._runtime_failed_count or 0),
        )
        if self._progress is not None or self._tui_progress is not None:
            return
        try:
            logger.info(str(msg))
        except (ValueError, OSError):
            pass

    def _start_hotkeys(self) -> None:
        if self._tui_progress is not None:
            self._start_tui_command_thread()
            return

        if not self._hotkeys_enabled or self._hotkey_thread is not None:
            return
        # Windows-only hotkeys (best-effort; no-op on other platforms).
        try:
            import msvcrt  # noqa: F401
        except Exception:
            return

        def _runner() -> None:
            import msvcrt

            # Print once (in quiet mode too).
            if self._progress is not None:
                self._progress.emit_block(
                    [
                        "\x1b[90m[Hotkeys]\x1b[0m n=next 10  d=db best  c=db counters  ?=help  q=stop",
                    ]
                )
            while True:
                if self._stop_requested_now():
                    return
                try:
                    if not msvcrt.kbhit():
                        time.sleep(0.05)
                        continue
                    ch = msvcrt.getwch()
                except Exception:
                    time.sleep(0.05)
                    continue
                if not ch:
                    continue
                key = str(ch).strip().lower()
                if key == "q":
                    try:
                        self.request_stop("hotkey stop")
                    except Exception:
                        pass
                    return
                if key in {"?", "h"}:
                    self._hotkey_help()
                elif key == "n":
                    self._hotkey_next_songs(10)
                elif key == "d":
                    self._hotkey_db_best()
                elif key == "c":
                    self._hotkey_db_counters()

        self._hotkey_thread = threading.Thread(target=_runner, name="Hotkeys", daemon=True)
        self._hotkey_thread.start()

    def _stop_hotkeys(self) -> None:
        self._stop_tui_command_thread()
        self._hotkey_thread = None

    def _start_tui_command_thread(self) -> None:
        if self._tui_cmd_queue is None or self._tui_resp_queue is None:
            return
        t = getattr(self, "_tui_cmd_thread", None)
        if isinstance(t, threading.Thread) and t.is_alive():
            return
        self._tui_cmd_stop.clear()

        def _runner() -> None:
            while not self._tui_cmd_stop.is_set():
                try:
                    cmd = self._tui_cmd_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                except Exception:
                    continue
                if not isinstance(cmd, dict):
                    continue
                op = str(cmd.get("cmd") or "").strip().lower()
                if op == "stop":
                    reason = str(cmd.get("reason") or "ui stop")
                    try:
                        self.request_stop(reason)
                    except Exception:
                        pass
                    continue
                if op == "next":
                    try:
                        n = int(cmd.get("n") or 10)
                    except Exception:
                        n = 10
                    lines = self._tui_up_next_lines(n)
                    self._tui_emit_block(lines)
                    continue

        self._tui_cmd_thread = threading.Thread(target=_runner, name="TuiCommands", daemon=True)
        self._tui_cmd_thread.start()

    def _stop_tui_command_thread(self) -> None:
        t = getattr(self, "_tui_cmd_thread", None)
        if not isinstance(t, threading.Thread):
            self._tui_cmd_thread = None
            return
        try:
            self._tui_cmd_stop.set()
        except Exception:
            pass
        try:
            t.join(timeout=1.0)
        except Exception:
            pass
        self._tui_cmd_thread = None

    def _tui_emit_block(self, lines: list[str]) -> None:
        q = getattr(self, "_tui_resp_queue", None)
        if q is None:
            return
        try:
            payload = {"lines": list(lines or [])}
        except Exception:
            payload = {"lines": []}
        try:
            put_nowait = getattr(q, "put_nowait", None)
            if callable(put_nowait):
                put_nowait(payload)
            else:
                q.put(payload, block=False)
        except Exception:
            return

    def _tui_up_next_lines(self, n: int) -> list[str]:
        tasks = self._run_tasks_ref
        completed = self._run_completed_ref
        if not isinstance(tasks, list) or not isinstance(completed, set):
            return ["\x1b[91m[Hotkeys]\x1b[0m No active queue."]
        out: list[str] = ["\x1b[96mUp Next\x1b[0m"]
        shown = 0
        for t in tasks:
            label = self._task_queue_label(t)
            if label in completed:
                continue
            try:
                diff = str(t[2] or "")
            except Exception:
                diff = ""
            out.append(f"  {shown + 1:>2}. \x1b[93m{label}\x1b[0m \x1b[90m[{diff}]\x1b[0m")
            shown += 1
            if shown >= int(n):
                break
        if shown <= 0:
            out.append("  (none)")
        return out

    def _emit_block(self, lines: list[str]) -> None:
        if self._tui_progress is not None:
            self._tui_emit_block(lines)
            return
        if self._progress is not None:
            self._progress.emit_block(lines)
            return
        stream = self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout
        try:
            for line in lines:
                stream.write(str(line) + "\n")
            stream.flush()
        except Exception:
            pass

    def _normalize_song_label(self, label: str) -> str:
        # Strip "(Run x/y)" suffix so DB queries map to the base song key.
        s = str(label or "").strip()
        if not s:
            return s
        try:
            return re.sub(r"\s*\(Run\s+\d+\s*/\s*\d+\)\s*$", "", s).strip()
        except Exception:
            return s

    def _hotkey_help(self) -> None:
        self._emit_block(
            [
                "\x1b[96mRoBeats MetaFinder Hotkeys\x1b[0m",
                "  n  show next 10 songs in queue",
                "  d  show best loadout from DB for current song",
                "  c  show DB counters/best scores for current song",
                "  q  request graceful stop",
            ]
        )

    def _hotkey_next_songs(self, n: int) -> None:
        tasks = self._run_tasks_ref
        completed = self._run_completed_ref
        if not isinstance(tasks, list) or not isinstance(completed, set):
            self._emit_block(["\x1b[91m[Hotkeys]\x1b[0m No active queue."])
            return
        out: list[str] = ["\x1b[96mUp Next\x1b[0m"]
        shown = 0
        for t in tasks:
            label = self._task_queue_label(t)
            if label in completed:
                continue
            try:
                diff = str(t[2] or "")
            except Exception:
                diff = ""
            out.append(f"  {shown + 1:>2}. \x1b[93m{label}\x1b[0m \x1b[90m[{diff}]\x1b[0m")
            shown += 1
            if shown >= int(n):
                break
        if shown <= 0:
            out.append("  (none)")
        self._emit_block(out)

    def _hotkey_db_counters(self) -> None:
        label = self._normalize_song_label(self._run_current_song_label)
        if not label:
            self._emit_block(["\x1b[91m[DB]\x1b[0m No current song yet."])
            return
        try:
            a, af, bs, bfg = get_song_counters(label)
        except Exception as e:
            self._emit_block([f"\x1b[91m[DB]\x1b[0m Error: {type(e).__name__}: {e}"])
            return
        self._emit_block(
            [
                f"\x1b[96mDB Counters\x1b[0m \x1b[93m{label}\x1b[0m",
                f"  attempts_lifetime: {a}",
                f"  attempts_first:    {af}",
                f"  best_score:        {bs}",
                f"  best_fg_score:     {bfg}",
            ]
        )

    def _hotkey_db_best(self) -> None:
        label = self._normalize_song_label(self._run_current_song_label)
        if not label:
            self._emit_block(["\x1b[91m[DB]\x1b[0m No current song yet."])
            return
        try:
            rows = get_best_loadouts(label, limit=3, gears_by_name=None, minis_by_name=None, team_buff="T5")
        except Exception as e:
            self._emit_block([f"\x1b[91m[DB]\x1b[0m Error: {type(e).__name__}: {e}"])
            return
        if not rows:
            self._emit_block([f"\x1b[90m[DB]\x1b[0m No loadouts found for \x1b[93m{label}\x1b[0m"])
            return
        best = rows[0]
        gear = best.get("gear") or []
        minis = best.get("minis") or []
        score = best.get("score", 0)
        fg_score = best.get("fg_score", 0)
        out = [
            f"\x1b[96mDB Best Loadout\x1b[0m \x1b[93m{label}\x1b[0m",
            f"  score:    \x1b[92m{score}\x1b[0m",
            f"  fg_score: \x1b[92m{fg_score}\x1b[0m",
            "  gear:",
        ]
        for g in gear:
            out.append(f"    - {g}")
        out.append("  minis:")
        for m in minis:
            out.append(f"    - {m}")
        self._emit_block(out)

    def _print_banner(self) -> None:
        stream = self._orig_stdout or getattr(sys, "__stdout__", None) or sys.stdout
        import textwrap

        banner = textwrap.dedent(
            """\
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠶⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠲⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣸⡒⠢⠤⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠄⠄⠀⠀⠄⠀⠤⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡖⢒⣒⡒⡆⠀⠀⠀⠀⠀⠀⣿⠹⡘⣷⣦⣤⣍⣒⠢⡀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠃⡎⠉⠉⠉⠉⠉⠙⢦⢱⠀⠀⠀⣀⡀⠀⠀⠀⠀⠀⢀⣀⠀⠀⠰⣧⢰⠀⢁⢠⠀⠀⠀⠀⠀⠀⠘⣄⠱⡘⣿⣿⣿⣿⡆⢇⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣀⣀⣀⣀⣀⣀⣀⣀⣀⡎⡜⠀⡰⠒⠒⠒⢲⠀⢘⡎⠗⢊⡭⠤⠭⣑⠢⣀⠔⣊⠭⠤⢍⡑⢎⣉⣘⠆⠸⣌⣀⣀⡀⠖⢂⣉⣀⣉⣉⣁⠙⣿⣿⣿⣷⠸⡀⠀⠀⠀
⠀⠀⠀⢀⠌⣤⣤⣤⣤⣤⡤⢤⣤⣤⢰⠁⢠⣃⣀⣀⣠⠜⠀⡜⢠⠞⠁⢀⣀⠀⠀⢳⢁⠞⠀⢀⣀⡀⠈⠛⢸⠇⠀⠀⠀⠀⠀⢡⢰⠁⠀⠀⠀⠀⠈⣆⠹⣿⣿⣿⡇⠇⠀⠀⠀
⠀⠀⢀⠎⣼⠏⣠⣤⠟⣡⣶⠀⣿⢏⠃⠀⠀⠀⠀⠀⠀⠀⡞⢠⠇⢀⡞⢁⠞⠀⡰⠁⡎⢀⡴⠁⠀⠈⢦⠀⠸⡄⢱⠀⢸⠀⠀⠈⠸⡀⠸⣅⣀⣀⣀⠈⠀⠹⣿⣿⣷⠸⡀⠀⠀
⠀⢠⢎⣼⢃⣾⣿⡏⠸⣿⠟⣰⡟⣾⣿⡿⠛⠛⠓⠛⣿⣿⣿⣼⣿⡟⣠⣿⣼⡟⠁⠀⣷⣾⡇⠀⠀⠀⠈⣿⣷⡇⠘⣿⣿⡇⠀⠀⠀⠙⣿⣷⣾⣿⣿⣿⣶⡄⠙⠿⠿⡇⠇⠀⠀
⢠⢂⣾⣧⣾⣿⣿⣧⣤⣤⣾⡿⣼⣿⣿⠃⠀⠀⠀⣠⣿⣿⡟⣿⣿⣿⣿⣿⠋⣠⣆⠀⣿⣿⣷⡀⠀⠀⣸⣿⣿⣇⢀⢻⣿⣷⡄⠀⠀⠀⠈⠙⠛⠛⠛⠛⣿⣿⣆⣠⣶⣤⡘⢄⠀
⡧⠤⠤⠤⠤⠤⠤⠤⠤⠤⡤⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣁⢹⣿⣿⣿⣷⣾⣿⣿⡧⠹⣿⣿⣿⣶⣾⣿⣿⣿⣿⢸⣎⢿⣿⣿⣿⣿⣷⢻⣿⣿⣿⣿⣿⣿⣿⣿⠿⣿⣿⣿⣆⢣
⠸⠦⠤⠤⠤⠤⢤⣾⣶⣶⢃⣿⣿⣿⣿⣿⣿⣿⣿⡿⢋⡔⣻⣎⠻⣿⣿⣿⣿⣿⢟⡴⣳⡙⢿⣿⣿⣿⣿⠿⡙⣿⡎⡯⢢⡙⢿⣿⣿⣿⣯⣿⣿⣿⣿⣿⣿⣿⣿⢠⡙⢿⣿⣿⠘
⠀⠐⠶⣷⣿⣷⣻⣿⣿⣯⠬⠭⠭⠭⠭⠭⠭⠭⣄⠞⢻⡵⡏⣿⡓⡬⠭⣭⠭⠔⢛⣷⡷⡹⠒⠬⢭⡭⢥⢞⣗⡬⡤⣿⣮⡊⡓⠢⠭⠭⠭⠬⠭⠭⠭⠭⠭⢭⢴⣏⠹⠢⢭⣭⡼
⠀⠀⠀⠀⠀⠀⠀⢿⡿⠿⠤⠤⠤⠤⠤⠤⢤⣭⣽⣿⡟⡇⡇⣿⢿⢦⠀⢴⠤⠶⠋⠉⠣⡏⠷⠄⠰⡦⠴⠛⠣⠭⠴⠇⠈⠿⣿⢯⢭⢯⢿⢭⣭⡤⠤⠤⠴⠶⠛⠿⠷⠴⠾⠿⠁
⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⢹⣿⣿⡇⡇⡇⣿⠈⠿⠀⠀⠀⠀⠀⠀⠀⠓⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣼⢸⢸⢸⢸⡏⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠹⢿⡇⡇⡧⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣸⢸⢸⣸⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢃⡗⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""
        ).splitlines()
        try:
            for line in banner:
                stream.write(line + "\n")
            stream.flush()
        except Exception:
            pass

    def _extract_record_info(self, res: dict | None) -> dict | None:
        if not isinstance(res, dict):
            return None
        record_info = res.get("_record")
        if not record_info:
            db_payload = res.get("db_payload")
            if isinstance(db_payload, dict):
                record_info = db_payload.get("_record")
        if record_info:
            return record_info
        best_data = res.get("best_data")
        prev_record = res.get("prev_record")
        fg_variants = res.get("fg_variants")
        db_best_fg_score = res.get("db_best_fg_score")
        if isinstance(best_data, dict) and (prev_record is not None or fg_variants):
            try:
                return evaluate_record_update(best_data, prev_record, fg_variants, db_best_fg_score=db_best_fg_score)
            except Exception:
                return None
        return None

    def _progress_on_result(
        self,
        res: dict | None,
        *,
        completed: int,
        total: int,
        failed_delta: int = 0,
    ) -> None:
        try:
            if isinstance(res, dict):
                song_label = (
                    res.get("_queue_label") or res.get("_queue_key") or res.get("song") or res.get("_song_name")
                )
            else:
                song_label = None
        except Exception:
            song_label = None
        record_info = None if failed_delta else self._extract_record_info(res)
        record_update = bool(record_info and record_info.get("record_update"))
        if record_update:
            try:
                self._session_new_records = int(self._session_new_records) + 1
            except Exception:
                self._session_new_records = 1
        if song_label:
            try:
                self._run_current_song_label = str(song_label)
                if self._progress is not None:
                    self._progress.set_status(str(song_label), "FAILED" if failed_delta else "DONE")
            except Exception:
                pass
        if failed_delta:
            self._runtime_failed_count = int(self._runtime_failed_count or 0) + int(failed_delta or 0)
            if self._progress is not None:
                self._progress.add_failed(failed_delta)
        if record_update:
            score = int(record_info.get("score", 0) or 0)
            best_fg = int(record_info.get("best_fg_score_run", 0) or 0)
            if self._progress is not None and (score > 0 or best_fg > 0):
                self._progress.add_new_record(1)
        self._set_runtime_progress_counts(
            completed=int(completed or 0),
            total=int(total or 0),
            failed=int(self._runtime_failed_count or 0),
        )
        self._runtime_status_name = "failed" if failed_delta else "done"
        if self._progress is not None:
            self._progress.update_counts(completed=completed, total=total)
        else:
            try:
                current_song = str(song_label or self._run_current_song_label or "").strip()
            except Exception:
                current_song = ""
            self._tui_publish(
                song=current_song,
                status=str(self._runtime_status_name or ""),
                completed=int(completed or 0),
                total=int(total or 0),
                failed=int(self._runtime_failed_count or 0),
                new_records=int(self._session_new_records or 0),
            )
        self._update_robeatsmeta_runtime_status(
            status=self._runtime_status_name,
            current_song=str(song_label or self._run_current_song_label or ""),
            completed=int(self._runtime_completed_count or 0),
            total=int(self._runtime_total_count or 0),
            failed=int(self._runtime_failed_count or 0),
        )

    def _status_listener(self, q):
        while True:
            try:
                msg = q.get()
            except (EOFError, BrokenPipeError, OSError):
                break
            if msg is None:
                break
            self._handle_status_message(msg)

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
        use_evo_db,
        auto_buff,
        ga_depth,
        status_queue,
        fg_debug,
    ):
        cfg_dict = cfg_to_dict(cfg)
        tasks = []
        parallel_workers = 1

        def _truthy_cfg(raw) -> bool:
            return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}

        # When GA_SEED is set, users expect reproducible A/B comparisons.
        # Historically we still generated per-repeat seeds via `secrets.randbits`,
        # which made runs non-reproducible even in "deterministic mode".
        ga_seed_base: int | None = None
        raw_ga_seed = os.environ.get("GA_SEED")
        if raw_ga_seed is not None and str(raw_ga_seed).strip() != "":
            try:
                ga_seed_base = int(str(raw_ga_seed).strip()) & 0xFFFFFFFF
            except Exception:
                ga_seed_base = None

        # PRODUCTION: repeat / HitSim flags
        # (SongRepeats, BundleSongRepeats, HumanHitSim.Enabled, HumanHitSim.ApplyTo,
        #  HumanHitSim.Seed, HumanHitSim.Distribution, HumanHitSim.GreatMode).
        song_repeats = 1
        try:
            song_repeats = safe_int(cfg.get("IterationEngine", "SongRepeats", fallback="1"), 1)
        except Exception:
            song_repeats = 1
        try:
            song_repeats_env = safe_int(os.environ.get("SONG_REPEATS", 0), 0)
            if song_repeats_env > 0:
                song_repeats = song_repeats_env
        except Exception:
            pass
        song_repeats = max(1, min(int(song_repeats), 100))
        bundle_song_repeats = False
        try:
            bundle_song_repeats = _truthy_cfg(cfg.get("IterationEngine", "BundleSongRepeats", fallback="0"))
        except Exception:
            bundle_song_repeats = False
        try:
            raw_bundle = os.environ.get("BUNDLE_SONG_REPEATS")
            if raw_bundle is not None and str(raw_bundle).strip() != "":
                bundle_song_repeats = _truthy_cfg(raw_bundle)
        except Exception:
            pass
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
            return int(seed or 1)

        def _build_repeat_ctx(song_name: str, *, repeat_index: int, repeat_total: int) -> dict:
            if ga_seed_base is not None:
                ga_seed = _stable_ga_seed_for_song_repeat(str(song_name), int(repeat_index))
                while ga_seed in used_ga_seeds:
                    # Extremely unlikely, but keep the uniqueness guarantee across the queue.
                    ga_seed = int((ga_seed + 1) & 0xFFFFFFFF) or 1
            else:
                ga_seed = int(secrets.randbits(32) or 1)
                while ga_seed in used_ga_seeds:
                    ga_seed = int(secrets.randbits(32) or 1)
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

                if ga_seed_base is not None:
                    # Use repeat_ctx even when SongRepeats=1 so per-song GA can seed deterministically.
                    repeat_ctx = _build_repeat_ctx(str(found_song_name), repeat_index=1, repeat_total=1)
                    tasks.append(
                        (
                            fp,
                            found_song_name,
                            task_diff,
                            cfg_dict,
                            paths,
                            ref_arrays,
                            all_gears,
                            all_minis,
                            gears_by_name,
                            minis_by_name,
                            use_evo_db,
                            auto_buff,
                            ga_depth,
                            status_queue,
                            parallel_workers,
                            fg_debug,
                            repeat_ctx,
                        )
                    )
                else:
                    tasks.append(
                        (
                            fp,
                            found_song_name,
                            task_diff,
                            cfg_dict,
                            paths,
                            ref_arrays,
                            all_gears,
                            all_minis,
                            gears_by_name,
                            minis_by_name,
                            use_evo_db,
                            auto_buff,
                            ga_depth,
                            status_queue,
                            parallel_workers,
                            fg_debug,
                        )
                    )
                continue

            if bundle_song_repeats:
                repeat_runs = [
                    _build_repeat_ctx(
                        str(found_song_name),
                        repeat_index=int(repeat_index),
                        repeat_total=int(repeats_for_song),
                    )
                    for repeat_index in range(1, repeats_for_song + 1)
                ]
                repeat_bundle = {
                    "repeat_bundle": True,
                    "repeat_total": int(repeats_for_song),
                    "runs": repeat_runs,
                }
                logger.info(f"[QUEUE] {found_song_name}")
                tasks.append(
                    (
                        fp,
                        found_song_name,
                        task_diff,
                        cfg_dict,
                        paths,
                        ref_arrays,
                        all_gears,
                        all_minis,
                        gears_by_name,
                        minis_by_name,
                        use_evo_db,
                        auto_buff,
                        ga_depth,
                        status_queue,
                        parallel_workers,
                        fg_debug,
                        repeat_bundle,
                    )
                )
                continue

            for repeat_index in range(1, repeats_for_song + 1):
                repeat_ctx = _build_repeat_ctx(
                    str(found_song_name),
                    repeat_index=int(repeat_index),
                    repeat_total=int(repeats_for_song),
                )

                logger.info(f"[QUEUE] {found_song_name} (Run {repeat_index}/{repeats_for_song})")
                tasks.append(
                    (
                        fp,
                        found_song_name,
                        task_diff,
                        cfg_dict,
                        paths,
                        ref_arrays,
                        all_gears,
                        all_minis,
                        gears_by_name,
                        minis_by_name,
                        use_evo_db,
                        auto_buff,
                        ga_depth,
                        status_queue,
                        parallel_workers,
                        fg_debug,
                        repeat_ctx,
                    )
                )
        return tasks

    @staticmethod
    def _extract_repeat_ctx(task) -> dict | None:
        if not isinstance(task, (tuple, list)) or len(task) <= 16:
            return None
        for extra in task[16:]:
            if not isinstance(extra, dict):
                continue
            if "repeat_index" in extra and "repeat_total" in extra and "ga_seed" in extra:
                return extra
        return None

    @staticmethod
    def _effective_total_tasks(tasks: list) -> int:
        """
        Compute the logical "task" count used for progress + throughput.

        - Non-bundled repeats: each queued tuple is already one task => `len(tasks)`.
        - Bundled repeats (`BundleSongRepeats=true`): each queued tuple expands into N repeat runs;
          count those runs so the UI doesn't look stuck at 0 until the entire bundle completes.
        """
        if not isinstance(tasks, list) or not tasks:
            return 0
        total = 0
        for task in tasks:
            repeats = 1
            try:
                if isinstance(task, (tuple, list)) and len(task) > 16:
                    for extra in task[16:]:
                        if not isinstance(extra, dict) or not bool(extra.get("repeat_bundle")):
                            continue
                        try:
                            repeats = int(extra.get("repeat_total") or 0)
                        except Exception:
                            repeats = 0
                        if repeats <= 0:
                            runs = extra.get("runs")
                            repeats = len(runs) if isinstance(runs, list) else 0
                        repeats = max(1, int(repeats))
                        break
            except Exception:
                repeats = 1
            total += max(1, int(repeats))
        return max(0, int(total))

    def _task_queue_label(self, task) -> str:
        if not isinstance(task, (tuple, list)) or len(task) < 2:
            return "Unknown"
        base = str(task[1])
        repeat_ctx = self._extract_repeat_ctx(task)
        if repeat_ctx:
            try:
                idx = int(repeat_ctx.get("repeat_index") or 0)
                total = int(repeat_ctx.get("repeat_total") or 0)
            except Exception:
                idx = 0
                total = 0
            if idx > 0 and total > 1:
                return f"{base} (Run {idx}/{total})"
        return base

    @staticmethod
    def _truthy(v) -> bool:
        return str(v or "").strip().lower() in {"1", "true", "yes", "on"}

    def _fatal_gpu_errors_enabled(self) -> bool:
        raw = str(os.environ.get("METAFINDER_FATAL_GPU_ERRORS", "") or "").strip()
        if raw:
            return self._truthy(raw)
        if self._truthy(os.environ.get("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "0")):
            return True
        try:
            api = getattr(self, "_robeatsmeta_api", None)
            if api is not None and callable(getattr(api, "service_mode_enabled", None)):
                return bool(api.service_mode_enabled())
        except Exception:
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
            except Exception:
                pass
            try:
                pending.append(getattr(current, "__context__", None))
            except Exception:
                pass

    def _is_fatal_inflight_exception(self, exc: BaseException) -> bool:
        if not self._fatal_gpu_errors_enabled():
            return False

        try:
            from gear_optimizer.solver.gpu_service import GpuServiceTimeoutError
        except Exception:
            GpuServiceTimeoutError = ()

        fatal_markers = (
            "gpu executor timeout after",
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
            except Exception:
                message = ""
            if any(marker in message for marker in fatal_markers):
                return True
        return False

    def _get_inflight_songs_requested(self, cfg) -> int:
        inflight_songs = 0
        try:
            inflight_songs = safe_int(cfg.get("IterationEngine", "InFlightSongs", fallback="0"), 0)
        except Exception:
            inflight_songs = 0

        try:
            inflight_songs_env = safe_int(os.environ.get("IN_FLIGHT_SONGS", 0), 0)
            if inflight_songs_env > 0:
                inflight_songs = inflight_songs_env
        except Exception:
            pass

        return inflight_songs

    def _apply_inflight_overrides(self, cfg) -> None:
        """Normalize config so InFlightSongs behaves predictably.

        - InFlightSongs is a single-process, GPU-backed pipeline.
        - It supports both CPU GA (GPU eval) and GPU_Native_GA via separate orchestrators.
        """
        # PRODUCTION: in-flight overlap flag (InFlightSongs) and GPU runtime flag (GPU_Mode).
        inflight_songs = self._get_inflight_songs_requested(cfg)
        if inflight_songs > 0:
            if not cfg.has_section("IterationEngine"):
                cfg.add_section("IterationEngine")
            cfg.set("IterationEngine", "InFlightSongs", str(int(inflight_songs)))

        if inflight_songs <= 1:
            return

        try:
            gpu_mode_requested = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=True)
        except Exception:
            gpu_mode_requested = True

        if not gpu_mode_requested:
            logger.warning(
                "[GPU] IterationEngine.GPU_Mode=false ignored (GPU-only policy); enabling GPU_Mode for in-flight."
            )
            try:
                cfg.set("IterationEngine", "GPU_Mode", "true")
            except Exception:
                pass

        # GPU_Native_GA is supported by a dedicated GPU-native in-flight orchestrator.

    def _maybe_apply_inflight_ram_mode(self, cfg) -> None:
        """
        Opt-in "RAM mode" for in-flight runs.

        Goal: reduce periodic GPU starvation on very fast GPUs by increasing CPU-side buffering/caching.

        Enable via:
        - config: IterationEngine.InFlight_RamMode=true
        - env: INFLIGHT_RAM_MODE=1
        """
        # PRODUCTION: in-flight RAM/cache flags
        # (InFlight_RamMode, InFlight_SongFileCacheMax, TeamBuff_BaseCalcSongCacheMax).
        inflight_songs = self._get_inflight_songs_requested(cfg)
        if int(inflight_songs) <= 1:
            return

        raw_env = os.environ.get("INFLIGHT_RAM_MODE")
        env_set = raw_env is not None and str(raw_env).strip() != ""
        ram_mode = self._truthy(raw_env) if env_set else False
        if not env_set:
            try:
                ram_mode = cfg.getboolean("IterationEngine", "InFlight_RamMode", fallback=False)
            except Exception:
                ram_mode = False

        if not ram_mode:
            return

        os.environ.setdefault("INFLIGHT_RAM_MODE", "1")

        # Cache parsed song files across repeats/LoopForever (system RAM).
        if os.environ.get("INFLIGHT_SONG_FILE_CACHE_MAX") in {None, ""}:
            cache_max = 0
            try:
                cache_max = safe_int(cfg.get("IterationEngine", "InFlight_SongFileCacheMax", fallback="0"), 0)
            except Exception:
                cache_max = 0
            if cache_max <= 0:
                cache_max = 2048
            os.environ["INFLIGHT_SONG_FILE_CACHE_MAX"] = str(int(cache_max))

        # TeamBuff post-processing can re-parse base calc_song; enlarge cache when allowed.
        if os.environ.get("TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX") in {None, ""}:
            tb_cache = 0
            try:
                tb_cache = safe_int(cfg.get("IterationEngine", "TeamBuff_BaseCalcSongCacheMax", fallback="0"), 0)
            except Exception:
                tb_cache = 0
            if tb_cache <= 0:
                tb_cache = 256
            os.environ["TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX"] = str(int(tb_cache))

        try:
            logger.info(
                "[InFlight][RAM] enabled: INFLIGHT_SONG_FILE_CACHE_MAX={} TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX={}".format(
                    os.environ.get("INFLIGHT_SONG_FILE_CACHE_MAX"),
                    os.environ.get("TEAM_BUFF_BASE_CALC_SONG_CACHE_MAX"),
                )
            )
        except Exception:
            pass

    def _maybe_autoset_gpu_song_slots(self, cfg) -> None:
        """
        Best-effort auto sizing for `GPU_SONG_SLOTS` when native in-flight mode is enabled.

        This targets a common throughput/stability failure mode on Vulkan:
        the GPU owner thread goes idle because GA submission stalls on song-slot acquisition
        (slot pressure), which users often interpret as the GPU executor "hanging".

        Notes:
        - Only applies when `GPU_SONG_SLOTS` is not already set in the environment.
        - Must run before `gear_optimizer.solver.taichi_gem.fields` is imported.
        - Users can always override by setting `GPU_SONG_SLOTS` explicitly.
        """
        # PRODUCTION: GPU slot sizing flag (GPU_SongSlots).
        raw = os.environ.get("GPU_SONG_SLOTS")
        if raw is not None and str(raw).strip() != "":
            return

        # Allow config to explicitly set song slots (useful when users want more slot slack
        # than the conservative auto-sizing heuristic provides).
        try:
            cfg_slots = safe_int(cfg.get("IterationEngine", "GPU_SongSlots", fallback="0"), 0)
        except Exception:
            cfg_slots = 0
        if int(cfg_slots) > 0:
            os.environ["GPU_SONG_SLOTS"] = str(int(cfg_slots))
            try:
                logger.info(
                    "[GPU] Set GPU_SONG_SLOTS={} from config (IterationEngine.GPU_SongSlots). Set GPU_SONG_SLOTS env var to override.".format(
                        int(cfg_slots)
                    )
                )
            except Exception:
                pass
            return

        inflight_songs = self._get_inflight_songs_requested(cfg)
        if int(inflight_songs) <= 1:
            return

        try:
            if "gear_optimizer.solver.taichi_gem.fields" in sys.modules:
                logger.info("[GPU] Auto GPU_SONG_SLOTS skipped: taichi_gem.fields already imported.")
                return
        except Exception:
            pass

        ga_queue_mult = 0
        # PRODUCTION: in-flight overlap flag (InFlight_GA_QueueMult).
        try:
            ga_queue_mult = safe_int(cfg.get("IterationEngine", "InFlight_GA_QueueMult", fallback="0"), 0)
        except Exception:
            ga_queue_mult = 0
        raw = os.environ.get("INFLIGHT_GA_QUEUE_MULT")
        if raw is not None and str(raw).strip() != "":
            try:
                ga_queue_mult = int(raw)
            except Exception:
                pass
        if ga_queue_mult <= 0:
            # Match the in-flight orchestrator defaults, but allow "RAM mode" to opt
            # into a deeper GA backlog (reduces starvation at the cost of VRAM).
            ram_mode = False
            try:
                raw_env = os.environ.get("INFLIGHT_RAM_MODE")
                if raw_env is not None and str(raw_env).strip() != "":
                    ram_mode = self._truthy(raw_env)
                else:
                    ram_mode = cfg.getboolean("IterationEngine", "InFlight_RamMode", fallback=False)
            except Exception:
                ram_mode = False
            ga_queue_mult = 4 if ram_mode else 2
        ga_queue_mult = max(1, min(int(ga_queue_mult), 8))

        # Slot 0 is reserved. In-flight also reserves at least one free slot so FG can submit without deadlocking.
        # Make the default large enough that `ga_queue_mult` isn't immediately capped by slot availability.
        required = int(inflight_songs) * int(ga_queue_mult) + 2
        slots = max(24, int(required))

        # Keep auto-sizing conservative to avoid surprising VRAM growth on smaller GPUs.
        # Power users can opt in to larger values by setting `GPU_SONG_SLOTS` explicitly.
        slots = min(int(slots), 256)

        os.environ["GPU_SONG_SLOTS"] = str(int(slots))
        try:
            logger.info(
                "[GPU] Auto-set GPU_SONG_SLOTS={} (InFlightSongs={}, InFlight_GA_QueueMult={}). Set GPU_SONG_SLOTS to override.".format(
                    int(slots),
                    int(inflight_songs),
                    int(ga_queue_mult),
                )
            )
        except Exception:
            pass

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
            cfg_dict0 = tasks[0][3] if tasks else {}
            ie = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}
            if isinstance(ie, dict):
                inflight_songs = safe_int(ie.get("inflightsongs", 0), 0)
        except Exception:
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
            logger.info(f"[InFlight] Requested: InFlightSongs={inflight_songs} (single-process).")

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
        except Exception:
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
        """Legacy entry point retained for compatibility; all runs now use native in-flight."""
        if self._stop_requested_now():
            return
        if not tasks:
            return

        song_task_count = max(0, int(len(tasks)))
        total_tasks = self._effective_total_tasks(tasks if isinstance(tasks, list) else [])
        inflight_songs = 0
        inflight_instances = 1
        try:
            cfg_dict0 = tasks[0][3] if tasks else {}
            ie = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}
            raw = ie.get("inflightsongs", 0) if isinstance(ie, dict) else 0
            inflight_songs = safe_int(raw, 0)
            raw_instances = ie.get("inflightinstances", 1) if isinstance(ie, dict) else 1
            inflight_instances = max(1, safe_int(raw_instances, 1))
        except Exception:
            inflight_songs = 0
            inflight_instances = 1

        raw_env_instances = os.environ.get("INFLIGHT_INSTANCES")
        if raw_env_instances is not None and str(raw_env_instances).strip() != "":
            inflight_instances = max(1, safe_int(raw_env_instances, inflight_instances))
        # Defensive cap: avoid accidental huge process counts from env/config typos.
        inflight_instances = max(1, min(int(inflight_instances), 8))

        if inflight_songs <= 0:
            inflight_songs = min(12, max(1, song_task_count))
            try:
                logger.info(f"[InFlight] Sequential pipeline removed; defaulting InFlightSongs={int(inflight_songs)}.")
            except Exception:
                pass
        elif song_task_count > 1 and int(inflight_songs) < 2:
            inflight_songs = min(12, max(2, song_task_count))
            try:
                logger.info(
                    "[InFlight] Sequential pipeline removed; "
                    f"raising InFlightSongs to {int(inflight_songs)} for multi-song queue."
                )
            except Exception:
                pass

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
                except Exception:
                    pass
                try:
                    trace_path = os.path.join(BIN_DIR, "inflight_disabled_traceback.log")
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    with open(trace_path, "a", encoding="utf-8") as fh:
                        fh.write(f"\n[{ts}] {type(inflight_err).__name__}: {inflight_err}\n")
                        fh.write(tb)
                except Exception:
                    pass
                if self._truthy(os.environ.get("INFLIGHT_PRINT_TRACE", "0")):
                    try:
                        logger.error(tb)
                    except Exception:
                        pass
            except Exception:
                pass
            if inflight_fatal_gpu_err:
                raise
            raise RuntimeError(
                "Native in-flight pipeline failed and legacy sequential fallback has been removed."
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
        except Exception:
            instances = 2
        instances = max(2, min(instances, 8))

        try:
            from gear_optimizer.solver.dual_process_inflight import (
                dual_process_inflight_worker_main,
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
        (
            _fp0,
            _song0,
            _diff0,
            cfg_dict,
            paths,
            ref_arrays,
            all_gears,
            all_minis,
            gears_by_name,
            minis_by_name,
            use_evo_db,
            auto_buff,
            ga_depth,
            _status_queue,
            parallel_workers,
            fg_debug,
        ) = tasks[0][:16]
        shared_ctx = (
            cfg_dict,
            paths,
            ref_arrays,
            all_gears,
            all_minis,
            gears_by_name,
            minis_by_name,
            use_evo_db,
            auto_buff,
            ga_depth,
            parallel_workers,
            fg_debug,
        )

        # Coordinator-owned completion state.
        task_key_to_song_name: dict[str, str] = {}
        for t in tasks:
            try:
                task_key_to_song_name[_task_key(t)] = str(t[1] or "").strip()
            except Exception:
                continue

        # Log effective per-worker thread settings (same formula as native in-flight).
        try:
            ga_seed = str(os.environ.get("GA_SEED") or "").strip()

            def _default_worker_threads(*, inflight_limit: int, kind: str) -> int:
                ncpu = os.cpu_count() or 1
                try:
                    ncpu = int(ncpu)
                except Exception:
                    ncpu = 1
                ncpu = max(1, int(ncpu))
                inflight_limit = max(1, int(inflight_limit))
                kind = str(kind or "").strip().lower()
                base = max(1, ncpu // 2)
                if ncpu <= 4:
                    base = min(base, 2)
                elif ncpu <= 8:
                    base = min(base, 3)
                if kind in {"fg_prep", "fgprep"}:
                    base = max(1, min(base, 2 if ncpu <= 8 else base))
                return max(1, min(int(inflight_limit), int(base)))

            ie = cfg_dict.get("IterationEngine", {}) if isinstance(cfg_dict, dict) else {}

            def _env_int(name: str, default: int) -> int:
                raw = os.environ.get(name)
                if raw is None or str(raw).strip() == "":
                    return int(default)
                try:
                    return int(str(raw).strip())
                except Exception:
                    return int(default)

            def _cfg_int(name: str, default: int) -> int:
                if not isinstance(ie, dict):
                    return int(default)
                return safe_int(ie.get(str(name)), int(default))

            for shard_idx, shard in shard_items:
                inflight_limit = max(1, min(int(inflight_songs or 1), int(len(shard))))

                prep_workers = _env_int("INFLIGHT_PREP_WORKERS", _cfg_int("inflight_prepworkers", 0))
                if prep_workers <= 0:
                    prep_workers = 1 if ga_seed else _default_worker_threads(inflight_limit=inflight_limit, kind="prep")

                decode_workers = _env_int("INFLIGHT_DECODE_WORKERS", _cfg_int("inflight_decodeworkers", 0))
                if decode_workers <= 0:
                    decode_workers = _default_worker_threads(inflight_limit=inflight_limit, kind="decode")

                fg_workers_default = min(4, inflight_limit)
                fg_workers = _env_int(
                    "INFLIGHT_FG_WORKERS",
                    _cfg_int("inflight_fgworkers", int(fg_workers_default)),
                )
                fg_workers = max(1, min(int(fg_workers), int(inflight_limit)))

                fg_prep_workers = _env_int("INFLIGHT_FG_PREP_WORKERS", _cfg_int("inflight_fgprepworkers", 0))
                if fg_prep_workers <= 0:
                    fg_prep_workers = _default_worker_threads(inflight_limit=inflight_limit, kind="fg_prep")

                db_prefetch_workers = _env_int(
                    "INFLIGHT_DB_PREFETCH_WORKERS", _cfg_int("inflight_dbprefetchworkers", 0)
                )
                if db_prefetch_workers <= 0:
                    db_prefetch_workers = max(1, min(int(fg_prep_workers), 4))

                logger.info(
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
        except Exception:
            pass

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
                    fp = t[0]
                    song_name = t[1]
                    diff = t[2]
                except Exception:
                    continue
                extras = list(t[16:]) if isinstance(t, (tuple, list)) and len(t) > 16 else []
                work_items.append((fp, song_name, diff, extras))

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
            except Exception:
                pass

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
                except Exception:
                    pass
                return
            if kind == "completed":
                try:
                    task_key = str(msg.get("task_key") or "").strip()
                except Exception:
                    task_key = ""
                if task_key:
                    try:
                        completed_songs.add(task_key)
                    except Exception:
                        pass
                    song_name = task_key_to_song_name.get(task_key)
                    if memory_resume_tracker and song_name:
                        try:
                            memory_resume_tracker.mark_completed(str(song_name))
                        except Exception:
                            pass
                    try:
                        self._maybe_mark_robeatsmeta_song_batch_computed(str(task_key), completed_songs)
                    except Exception:
                        pass
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
                except Exception:
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
                except Exception:
                    break
                if isinstance(msg, dict):
                    _handle_msg(msg)

            # Graceful join, then terminate stragglers.
            for p in processes:
                try:
                    p.join(timeout=10.0)
                except Exception:
                    pass
            for p in processes:
                if not p.is_alive():
                    continue
                try:
                    p.terminate()
                except Exception:
                    pass
                try:
                    p.join(timeout=5.0)
                except Exception:
                    pass

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
            except Exception:
                processed = 0
            per_h = float(processed) * 3600.0 / float(elapsed_s) if processed > 0 else 0.0
            logger.info(
                "[InFlight][Dual] Completed %s tasks in %.2fs (%.1f tasks/hour)", int(processed), elapsed_s, per_h
            )
        except Exception:
            pass

    def _start_post_processor(self, total_tasks: int):
        from gear_optimizer.pipeline.post_processor import run_post_processor

        post_queue_size = safe_int(os.environ.get("POST_PIPELINE_QUEUE", 0), 0)
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
        try:
            if post_queue is not None:
                post_queue.put(None, block=True, timeout=1.0)
        except Exception:
            pass
        try:
            if post_proc is not None:
                post_proc.join(timeout=120.0)
        except Exception:
            pass
        try:
            if post_proc is not None and post_proc.is_alive():
                post_proc.terminate()
                post_proc.join(timeout=5.0)
        except Exception:
            pass

    def _run_parallel(
        self, tasks, max_workers, completed_songs, memory_resume_tracker, manager, status_queue, status_thread
    ):
        ref_arrays = None
        try:
            ref_arrays = tasks[0][5] if tasks and len(tasks[0]) > 5 else None
        except Exception:
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
                init_timeout = float(os.environ.get("GPU_EXECUTOR_INIT_TIMEOUT_SEC", "30"))
            except Exception:
                init_timeout = 30.0
            if not gpu_executor.wait_until_ready(timeout=init_timeout):
                err = getattr(gpu_executor, "last_init_error", None)
                msg = "[GPU Executor] Taichi init failed or timed out; falling back to single-process in-flight"
                if err:
                    msg = f"{msg} ({err})"
                warn_fallback("app.gpu_executor.single_process", msg, fatal=False)
                try:
                    gpu_executor.stop()
                except Exception:
                    pass
                gpu_executor = None
            if gpu_executor is not None and gpu_executor.is_running:
                logger.info("[GPU Executor] Started for parallel song processing")
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
                        secondary_workers = int(os.environ.get("GPU_EXECUTOR_SECONDARY_WORKERS", "0") or 0)
                    except Exception:
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
                                os.environ.get("GPU_EXECUTOR_SECONDARY_VULKAN_VISIBLE_DEVICE", "0") or ""
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
                                init_timeout = float(os.environ.get("GPU_EXECUTOR_INIT_TIMEOUT_SEC", "30"))
                            except Exception:
                                init_timeout = 30.0
                            if not secondary_ready.wait(timeout=max(0.0, float(init_timeout))):
                                logger.warning(
                                    "[GPU Executor][Secondary] Init timed out; disabling secondary executor for this pool"
                                )
                                try:
                                    secondary_gpu_proc.terminate()
                                except Exception:
                                    pass
                                secondary_gpu_proc = None
                                secondary_gpu_req_q = None
                            else:
                                ok = True
                                err = None
                                try:
                                    status = secondary_status_q.get(timeout=1.0)
                                    ok = bool(status.get("ok", False)) if isinstance(status, dict) else True
                                    err = status.get("error") if isinstance(status, dict) else None
                                except Exception:
                                    ok = True
                                    err = None

                                if not ok:
                                    msg = "[GPU Executor][Secondary] Taichi init failed; disabling secondary executor for this pool"
                                    if err:
                                        msg = f"{msg} ({err})"
                                    logger.warning(msg)
                                    try:
                                        secondary_gpu_proc.terminate()
                                    except Exception:
                                        pass
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
                        except Exception:
                            pass

                        if secondary_gpu_req_q is not None and secondary_gpu_proc is not None:
                            try:
                                from gear_optimizer.solver.gpu_executor import send_gpu_executor_shutdown

                                send_gpu_executor_shutdown(secondary_gpu_req_q)
                            except Exception:
                                pass
                            try:
                                secondary_gpu_proc.join(timeout=10.0)
                            except Exception:
                                pass
                            if secondary_gpu_proc.is_alive():
                                try:
                                    secondary_gpu_proc.terminate()
                                except Exception:
                                    pass
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
                        except Exception:
                            pass

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
                    # Recreate tuple with new status queue
                    new_t = list(t)
                    new_t[13] = status_queue
                    remaining_tasks.append(tuple(new_t))

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
            except Exception:
                pass

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
                        except Exception:
                            pass
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
                except Exception:
                    pass
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
                    except Exception:
                        force_obj = None
                    if not isinstance(force_obj, dict):
                        return 0
                    try:
                        s = int(force_obj.get("score", 0) or 0)
                    except Exception:
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
                    except Exception:
                        return 0

                valid_entries = []
                for e in persisted:
                    if not isinstance(e, dict):
                        continue
                    if not (e.get("gear") or e.get("minis")):
                        continue
                    try:
                        score_i = int(e.get("score", 0) or 0)
                    except Exception:
                        score_i = 0
                    try:
                        fg_i = int(e.get("fg_score", 0) or 0)
                    except Exception:
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
                    except Exception:
                        pass
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
                    except Exception:
                        pass

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

        self._progress_counts_driven = False

        if failed > 0:
            logger.warning(f"[SUMMARY] {failed}/{total} songs failed.")

    def _cleanup_resources(self, status_queue, status_thread, manager):
        try:
            self._clear_robeatsmeta_runtime_status(status="idle", available=True)
            api = getattr(self, "_robeatsmeta_api", None)
            if api is not None:
                try:
                    api.flush_runtime_status(timeout=1.0)
                except Exception:
                    pass
                try:
                    api.stop_runtime_status_loop(timeout=1.0)
                except Exception:
                    pass
            if status_queue:
                try:
                    status_queue.put(None)
                except Exception:
                    pass
            if status_thread:
                try:
                    status_thread.join(timeout=2)
                except Exception:
                    pass
            if manager:
                try:
                    manager.shutdown()
                except Exception:
                    pass
            # Flush pending DB writes (best-effort)
            if hasattr(self, "_async_db_saver"):
                try:
                    self._async_db_saver.shutdown(timeout=30.0)
                except Exception:
                    pass
            # Force GC on manager
            old_manager = manager
            del old_manager
            gc.collect(generation=0)

        except Exception:
            pass

    def _handle_loop_restart(self, wait_time=3):
        logger.info(f"Restarting song scan in {wait_time} seconds...")
        try:
            if os.path.exists(MEMORY_GUARD_RESUME_FILE):
                os.remove(MEMORY_GUARD_RESUME_FILE)
                logger.info("[LoopForever] Cleared resume file")
        except Exception as e:
            logging.warning(f"Failed to delete resume file: {e}")
        time.sleep(wait_time)
