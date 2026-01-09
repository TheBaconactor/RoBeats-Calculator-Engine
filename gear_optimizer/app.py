import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import configparser
import gc
import logging
import multiprocessing
import os
import queue as queue_module
import re
import secrets
import signal
import sys
import threading
import time

import numpy as np

# Import from refactored modules
from gear_optimizer.core.constants import PATHS, SCRIPT_DIR, BIN_DIR, TOTAL_ROWS, GA_POPULATION_SIZE
from gear_optimizer.core.config import (
    compute_memory_guard_limit,
    load_paths_cache,
    read_iteration_engine_settings,
)
from gear_optimizer.data.database import (
    init_db,
    save_loadouts_batch,
    get_evolution_db_path,
    prioritize_song_queue_missing_db,
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
from gear_optimizer.data.discord_reporter import DiscordReporter, build_stats_summary, setup_discord_reporter
from gear_optimizer.pipeline.song_processor import safe_process_song_task, scan_song_header
from gear_optimizer.data.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from gear_optimizer.core.utils import safe_int, cfg_to_dict, cfg_from_dict
from gear_optimizer.solver.scoring import FEVER_TIMELINE_CACHE, FG_CACHE
from gear_optimizer.solver.genetic import GEM_SOLVER_CACHE


# Module-level worker initializer for GPU executor (must be picklable)
def _gpu_worker_initializer(request_queue, registrations, counter, lock):
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

    worker_id, response_queue = registrations[idx]
    set_gpu_worker_mode(worker_id, request_queue, response_queue)


class _AsyncDbSaver:
    """
    Background DB writer to avoid blocking the main loop between songs.

    This keeps `save_loadouts_batch()` off the critical path so the next song can
    start immediately (GPU stays busier) while DB inserts/dedup/prune run in a
    background thread.
    """

    def __init__(self, discord_reporter: DiscordReporter | None = None):
        self._discord_reporter = discord_reporter
        self._queue: queue_module.Queue = queue_module.Queue()
        self._thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._loop,
                name="AsyncDbSaver",
                daemon=True,
            )
            self._thread.start()

    def submit(self, song_name: str, entries: list[dict], *, meta: dict | None = None) -> None:
        if not entries:
            return
        if not self._running:
            self.start()
        self._queue.put((song_name, entries, meta or {}))

    def flush(self, timeout: float = 30.0) -> None:
        if not self._running:
            return
        deadline = time.monotonic() + max(0.0, float(timeout))
        while getattr(self._queue, "unfinished_tasks", 0) > 0:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.05, remaining))

        if getattr(self._queue, "unfinished_tasks", 0) > 0:
            try:
                pending = int(getattr(self._queue, "unfinished_tasks", 0))
            except Exception:
                pending = -1
            msg = f"[DB] Warning: async DB flush timed out; pending_tasks={pending}"
            try:
                print(msg)
            except Exception:
                pass
            try:
                logging.warning(msg)
            except Exception:
                pass
            try:
                if self._discord_reporter is not None:
                    self._discord_reporter.send_log(msg)
            except Exception:
                pass

    def shutdown(self, timeout: float = 30.0) -> None:
        if not self._running:
            return

        # Best-effort flush before stopping.
        self.flush(timeout=timeout)

        try:
            self._queue.put(None)
        except Exception:
            pass

        try:
            if self._thread is not None:
                self._thread.join(timeout=timeout)
        except Exception:
            pass

        with self._lock:
            self._running = False
            self._thread = None

    def _loop(self) -> None:
        while True:
            item = self._queue.get()
            try:
                if item is None:
                    return
                song_name, entries, meta = item
                if not isinstance(meta, dict):
                    meta = {}

                try:
                    save_loadouts_batch(song_name, entries)
                except Exception as exc:
                    msg = f"[DB] Async save failed for {song_name}: {type(exc).__name__}: {exc}"
                    try:
                        print(msg)
                    except Exception:
                        pass
                    try:
                        logging.error(msg)
                    except Exception:
                        pass
                    try:
                        if self._discord_reporter is not None:
                            self._discord_reporter.send_log(msg)
                    except Exception:
                        pass
            finally:
                try:
                    self._queue.task_done()
                except Exception:
                    pass


class GearOptimizerApp:
    def __init__(self):
        self.setup_logging()
        self.discord_reporter = self.setup_discord()
        self._async_db_saver = _AsyncDbSaver(self.discord_reporter)
        self._stop_requested = threading.Event()
        self._force_exit_requested = threading.Event()
        self._signal_handlers_installed = False
        self._signal_prev_handlers: dict[int, object] = {}

    def setup_logging(self):
        os.makedirs(BIN_DIR, exist_ok=True)
        log_file_path = os.path.join(BIN_DIR, "error.log")
        logging.basicConfig(
            filename=log_file_path, level=logging.WARNING, format="%(asctime)s %(levelname)s: %(message)s"
        )

    def setup_discord(self):
        return setup_discord_reporter(stats_batch_size=500)

    def request_stop(self, reason: str, *, force: bool = False) -> None:
        """
        Request a graceful stop (finish current work, flush DB, then exit).

        - First request sets a stop flag checked between songs / futures.
        - Second request (force=True) escalates to KeyboardInterrupt.
        """
        if force:
            self._force_exit_requested.set()

        if not self._stop_requested.is_set():
            self._stop_requested.set()
            msg = f"[Shutdown] Stop requested ({reason}). Finishing current work then exiting. Press Ctrl+C again to force."
            try:
                print(msg, flush=True)
            except Exception:
                pass
            try:
                self.discord_reporter.send_log(msg)
            except Exception:
                pass

        if force:
            raise KeyboardInterrupt

    def _stop_file_path(self) -> str:
        p = str(os.environ.get("METAFINDER_STOP_FILE", "") or "").strip()
        if p:
            return p
        return os.path.join(BIN_DIR, "STOP")

    def _stop_requested_now(self) -> bool:
        if self._stop_requested.is_set():
            return True
        try:
            stop_file = self._stop_file_path()
            if stop_file and os.path.exists(stop_file):
                self.request_stop(f"stop file detected: {stop_file!r}")
                return True
        except Exception:
            pass
        return self._stop_requested.is_set()

    def _install_signal_handlers(self) -> None:
        if self._signal_handlers_installed:
            return
        if threading.current_thread() is not threading.main_thread():
            return

        def _handler(signum, _frame):
            # First signal -> graceful stop, second -> force exit.
            if self._stop_requested.is_set():
                self.request_stop(f"signal {signum}", force=True)
            else:
                self.request_stop(f"signal {signum}", force=False)

        for sig in (
            getattr(signal, "SIGINT", None),
            getattr(signal, "SIGTERM", None),
            getattr(signal, "SIGBREAK", None),
        ):
            if sig is None:
                continue
            try:
                self._signal_prev_handlers[int(sig)] = signal.getsignal(sig)
                signal.signal(sig, _handler)
            except Exception:
                pass

        self._signal_handlers_installed = True

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

        while True:
            if self._stop_requested_now():
                break
            should_loop = self._run_single_iteration()
            if not should_loop:
                break

    def _run_single_iteration(self):
        memory_guard_restart = False
        memory_resume_tracker = None
        start_time = time.time()
        loop_forever = False  # Default, updated from config
        graceful_stop = False

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

            cfg = configparser.ConfigParser()
            cfg_path = os.environ.get("METAFINDER_CONFIG_PATH", "config.ini")
            cfg.read(cfg_path, encoding="utf-8-sig")
            paths = load_paths_cache()
            set_memory_watchdog_limit(compute_memory_guard_limit(cfg))
            db_display_name = os.path.basename(get_evolution_db_path())
            self.discord_reporter.send_log(f"Gear Optimizer run started. DB file: {db_display_name}")

            init_db()
            self._auto_merge_databases()

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

                print(f" >> [ForceGreats] {fg_status}")

            ga_depth = safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=50))
            use_evo_db = cfg.getboolean("IterationEngine", "UseEvolutionDB", fallback=True)
            loop_forever = cfg.getboolean("IterationEngine", "LoopForever", fallback=False)
            eval_cpu_limit = safe_int(cfg.get("IterationEngine", "EvalCPUCores", fallback=0))
            self._apply_inflight_overrides(cfg)

            # If the GPU executor initializes Taichi before the GA code runs, Taichi fields can be allocated with
            # default (padded) GA run buffers, making GPU-native GA payload downloads significantly slower.
            # Publish a conservative sizing hint early so any first-use allocation can pick tighter shapes.
            try:
                gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)
                gpu_native_ga = cfg.getboolean("IterationEngine", "GPU_Native_GA", fallback=False)
            except Exception:
                gpu_mode = False
                gpu_native_ga = False
            if gpu_mode and gpu_native_ga:
                ga_multistart = safe_int(cfg.get("IterationEngine", "GA_MultiStart", fallback=1), 1)
                ga_multistart = max(1, int(ga_multistart))
                os.environ.setdefault("GPU_NATIVE_GA_MAX_RUNS", str(ga_multistart))
                os.environ.setdefault("GPU_NATIVE_GA_MAX_GENOMES", str(int(GA_POPULATION_SIZE)))
                try:
                    from gear_optimizer.solver.taichi_gem import fields as gpu_fields

                    gpu_fields.configure_ga_run_buffers(max_runs=ga_multistart, max_genomes=int(GA_POPULATION_SIZE))
                except Exception:
                    pass

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

            self.discord_reporter.send_log(f"Queued {len(song_queue)} song(s) for processing.")

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

            parallel_workers = 1

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
            logging.error(f"Error: {e}")
            print(f"Error: {e}")
            self.discord_reporter.send_log(f"Error encountered: {e}")

        finally:
            self._cleanup_resources(status_queue, status_thread, manager)

            elapsed = time.time() - start_time
            done_msg = f"Run completed in {elapsed:.2f}s"
            print(done_msg)
            self.discord_reporter.send_log(done_msg)
            gc.collect()

        if graceful_stop or self._stop_requested.is_set():
            try:
                print("[Shutdown] Exiting by user request.")
            except Exception:
                pass
            try:
                self.discord_reporter.send_log("Exiting by user request.")
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
            print("LoopForever=FALSE; exiting after completing queue.")
            self.discord_reporter.send_log("LoopForever disabled; exiting.")
            return False

    def _auto_merge_databases(self):
        try:
            from gear_optimizer.data.db_merge import auto_merge_secondary_databases

            merge_success, merge_message = auto_merge_secondary_databases(
                delete_after_merge=True, backup_before_merge=True
            )
            if merge_success and "No secondary databases" not in merge_message:
                print(f"[DB Merge] {merge_message}")
                self.discord_reporter.send_log(f"Database merge: {merge_message}")
            elif not merge_success:
                print(f"[DB Merge] Warning: {merge_message}")
                logging.warning(f"[DB Merge] {merge_message}")
        except Exception as e:
            logging.error(f"[DB Merge] Unexpected error: {e}")
            print(f"[DB Merge] Error: {e}")

    def _disable_inputs_to_prevent_taint(self, cfg):
        print(
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
            ref_arrays[name] = np.array(temp_list, dtype=np.float64)
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
        legacy_target_raw = cfg.get("CalculateSong", "TargetColor", fallback="")

        if not target_primary_raw and legacy_target_raw:
            target_primary_raw = legacy_target_raw
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

    def _build_song_queue(self, cfg, paths, use_evo_db):
        diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols = self._get_filter_params(cfg)

        resume_context = build_memory_guard_resume_context(diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols)

        ignore_resume = False
        try:
            ignore_resume = cfg.getboolean("IterationEngine", "IgnoreResumeQueue", fallback=False)
        except Exception:
            ignore_resume = False
        if self._truthy(os.environ.get("METAFINDER_IGNORE_RESUME_QUEUE", "")):
            ignore_resume = True

        if not ignore_resume:
            resume_seed_queue = load_memory_guard_resume_queue(resume_context)
            if resume_seed_queue:
                print(f"[MemoryGuard] Resuming {len(resume_seed_queue)} song(s) from previous interrupted run.")
                # Optional deterministic limit (useful for benchmarks / iteration), even in resume mode.
                song_queue_limit = 0
                try:
                    song_queue_limit = safe_int(cfg.get("IterationEngine", "SongQueueLimit", fallback="0"), 0)
                except Exception:
                    song_queue_limit = 0
                if song_queue_limit and song_queue_limit > 0 and len(resume_seed_queue) > song_queue_limit:
                    resume_seed_queue = resume_seed_queue[: int(song_queue_limit)]
                    print(
                        f"[Queue] SongQueueLimit={song_queue_limit}: running {len(resume_seed_queue)} song(s) (resume)"
                    )
                return resume_seed_queue

        diff = cfg.get("CalculateSong", "Difficulty", fallback="Hard")
        search_dir = paths.get(diff, SCRIPT_DIR)

        song_queue = []
        seen_paths = set()

        if diff_lower not in ("easy", "normal", "hard"):
            data_root = PATHS.data_dir
            dirs_to_search = [data_root] if os.path.exists(data_root) else [SCRIPT_DIR]
        else:
            dirs_to_search = [search_dir]

        for d in dirs_to_search:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
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

                        # Infer difficulty from parent folder name
                        parent_folder = os.path.basename(root).lower()
                        if parent_folder == "hard":
                            detected_diff = "Hard"
                        elif parent_folder == "normal":
                            detected_diff = "Normal"
                        elif parent_folder == "easy":
                            detected_diff = "Easy"
                        else:
                            detected_diff = "Unknown"

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

        if not song_queue:
            print("Error: No matching songs found.")
            return []

        if use_evo_db:
            try:
                song_queue = prioritize_song_queue_missing_db(song_queue)
            except Exception as exc:
                logging.warning(f"[DB] Failed to prioritize song queue: {type(exc).__name__}: {exc}")

        # Optional deterministic limit (useful for benchmarks / iteration).
        song_queue_limit = 0
        try:
            song_queue_limit = safe_int(cfg.get("IterationEngine", "SongQueueLimit", fallback="0"), 0)
        except Exception:
            song_queue_limit = 0
        if song_queue_limit and song_queue_limit > 0 and len(song_queue) > song_queue_limit:
            try:
                song_queue = sorted(
                    song_queue,
                    key=lambda t: (
                        str(t[1] or "").casefold(),
                        str(t[2] or "").casefold(),
                        os.path.abspath(str(t[0] or "")).casefold(),
                    ),
                )
            except Exception:
                pass
            song_queue = song_queue[: int(song_queue_limit)]
            print(f"[Queue] SongQueueLimit={song_queue_limit}: running {len(song_queue)} song(s)")

        # Queue all discovered songs; filtering is handled by difficulty folder + optional search string.
        if not filter_search:
            return song_queue

        print(f"Found {len(song_queue)} songs to process.")
        return song_queue

    def _status_listener(self, q):
        while True:
            try:
                msg = q.get()
            except (EOFError, BrokenPipeError, OSError):
                break
            if msg is None:
                break
            try:
                print(msg, flush=True)
            except (ValueError, OSError):
                # Handle "I/O operation on closed file" during shutdown
                pass
            self.discord_reporter.send_log(str(msg))

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
        used_ga_seeds: set[int] = set()

        for fp, found_song_name, task_diff in song_queue:
            if song_repeats <= 1:
                print(f"[QUEUE] {found_song_name}")
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

            for repeat_index in range(1, song_repeats + 1):
                ga_seed = int(secrets.randbits(32) or 1)
                while ga_seed in used_ga_seeds:
                    ga_seed = int(secrets.randbits(32) or 1)
                used_ga_seeds.add(ga_seed)

                repeat_ctx = {
                    "repeat_index": int(repeat_index),
                    "repeat_total": int(song_repeats),
                    "ga_seed": int(ga_seed),
                }

                print(f"[QUEUE] {found_song_name} (Run {repeat_index}/{song_repeats})")
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
    def _clone_calc_song_for_run(calc_song: dict) -> dict:
        if not isinstance(calc_song, dict):
            return calc_song
        out = dict(calc_song)
        try:
            out["metadata"] = dict(out.get("metadata") or {})
        except Exception:
            pass
        try:
            out["song_data"] = dict(out.get("song_data") or {})
        except Exception:
            pass
        return out

    @staticmethod
    def _truthy(v) -> bool:
        return str(v or "").strip().lower() in {"1", "true", "yes", "on"}

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
        inflight_songs = self._get_inflight_songs_requested(cfg)
        if inflight_songs > 0:
            if not cfg.has_section("IterationEngine"):
                cfg.add_section("IterationEngine")
            cfg.set("IterationEngine", "InFlightSongs", str(int(inflight_songs)))

        if inflight_songs <= 1:
            return

        gpu_mode = False
        try:
            gpu_mode = cfg.getboolean("IterationEngine", "GPU_Mode", fallback=False)
        except Exception:
            gpu_mode = False

        if not gpu_mode:
            print("[InFlight] InFlightSongs>1 requires GPU_Mode=true; disabling in-flight pipeline.")
            cfg.set("IterationEngine", "InFlightSongs", "0")
            return

        # GPU_Native_GA is supported by a dedicated GPU-native in-flight orchestrator.

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
        gpu_mode_cfg = False
        try:
            cfg_dict0 = tasks[0][3] if tasks else {}
            ie = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}
            if isinstance(ie, dict):
                inflight_songs = safe_int(ie.get("inflightsongs", 0), 0)
                gpu_mode_cfg = self._truthy(ie.get("gpu_mode", "0"))
        except Exception:
            inflight_songs = 0
            gpu_mode_cfg = False

        logical_cpus = os.cpu_count() or 1
        available_cpus = logical_cpus
        if eval_cpu_limit and eval_cpu_limit > 0:
            available_cpus = max(1, min(logical_cpus, eval_cpu_limit))

        if gpu_mode_cfg:
            max_workers = 1
        else:
            max_workers = max(1, min(len(tasks), max(1, available_cpus - 1)))

        if available_cpus != logical_cpus:
            print(f"EvalCPUCores cap applied: using {available_cpus} of {logical_cpus} cores.")

        if inflight_songs > 1 and len(tasks) > 1:
            print(f"[InFlight] Requested: InFlightSongs={inflight_songs} (single-process).")

        print(
            f"Parallel plan -> songs: {len(tasks)}, concurrent workers: {max_workers}, cores per song: {parallel_workers}"
        )
        print(f"Using {available_cpus} logical CPU cores")

        completed_songs = set()

        if len(tasks) > 1 and max_workers > 1:
            self._run_parallel(
                tasks, max_workers, completed_songs, memory_resume_tracker, manager, status_queue, status_thread
            )
        else:
            self._run_sequential(tasks, completed_songs, memory_resume_tracker)

        if memory_release_requested():
            print("[MemoryGuard] Soft limit reached; pending songs saved for resume.")
            if loop_forever:
                print("[MemoryGuard] LoopForever enabled; scheduling automatic restart.")
                self.discord_reporter.send_log("Memory soft limit reached; restarting MetaFinder to release RAM.")

        if memory_resume_tracker:
            memory_resume_tracker.finalize(memory_release_requested())

    def _run_sequential(self, tasks, completed_songs, memory_resume_tracker):
        """Sequential song processing with async preloading and GPU look-ahead prefetch.

        While GPU processes current song, next songs are being:
        1. CPU preloaded (file I/O, parsing) in background thread
        2. GPU prefetched (timeline kernel) for slots 1-5
        """
        completed_offset = len(completed_songs)
        if self._stop_requested_now():
            return

        # ------------------------------------------------------------------
        # In-flight multi-song pipeline (opt-in):
        # Interleave multiple songs' CPU GA orchestration while a single GPU-owner
        # thread runs Taichi kernels via the GPU executor. This is different from
        # per-song multiprocessing: it stays within one process and avoids per-song
        # worker overhead.
        # Enable via IterationEngine.InFlightSongs (or env var IN_FLIGHT_SONGS).
        # ------------------------------------------------------------------
        inflight_songs = 0
        try:
            cfg_dict0 = tasks[0][3] if tasks else {}
            ie = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}
            if isinstance(ie, dict):
                raw = ie.get("inflightsongs", 0)
            else:
                raw = 0
            inflight_songs = safe_int(raw, 0)
        except Exception:
            inflight_songs = 0

        # Check if GPU preloading should be used (sequential/non-inflight path).
        use_gpu_preload = len(tasks) > 1
        preloader = None
        if not (inflight_songs and inflight_songs > 1 and len(tasks) > 1):
            if use_gpu_preload:
                try:
                    preloader = self._start_song_preloader(tasks, completed_songs)
                except Exception as e:
                    print(f"[Song Preloader] Not available: {e}")
                    use_gpu_preload = False

        if inflight_songs and inflight_songs > 1 and len(tasks) > 1:
            # In-flight is a CPU GA driver (with GPU evaluation). It is incompatible with
            # GPU_Native_GA unless we use the dedicated GPU-native in-flight orchestrator.
            gpu_native_ga = False
            try:
                cfg_dict0 = tasks[0][3] if tasks else {}
                cfg0 = cfg_from_dict(cfg_dict0) if cfg_dict0 else configparser.ConfigParser()
                gpu_native_ga = cfg0.getboolean("IterationEngine", "GPU_Native_GA", fallback=False)
            except Exception:
                gpu_native_ga = False

            inflight_ok = False
            post_queue = None
            post_proc = None
            try:
                from gear_optimizer.pipeline.post_processor import run_post_processor

                post_queue_size = safe_int(os.environ.get("POST_PIPELINE_QUEUE", 8), 8)
                post_queue = multiprocessing.Queue(maxsize=max(1, post_queue_size))
                post_proc = multiprocessing.Process(
                    target=run_post_processor,
                    args=(post_queue, len(tasks)),
                    daemon=True,
                    name="SongPostProcessor",
                )
                post_proc.start()

                if gpu_native_ga:
                    from gear_optimizer.solver.native_inflight_orchestrator import run_native_inflight_song_pipeline

                    run_native_inflight_song_pipeline(
                        tasks,
                        in_flight_songs=int(inflight_songs),
                        completed_songs=completed_songs,
                        memory_resume_tracker=memory_resume_tracker,
                        post_queue=post_queue,
                        total_tasks=len(tasks),
                        stop_requested=self._stop_requested_now,
                    )
                else:
                    from gear_optimizer.solver.inflight_orchestrator import run_inflight_song_pipeline

                    run_inflight_song_pipeline(
                        tasks,
                        in_flight_songs=int(inflight_songs),
                        completed_songs=completed_songs,
                        memory_resume_tracker=memory_resume_tracker,
                        post_queue=post_queue,
                        total_tasks=len(tasks),
                        stop_requested=self._stop_requested_now,
                    )
                inflight_ok = True
            except Exception as inflight_err:
                print(f"[InFlight] Disabled: {type(inflight_err).__name__}: {inflight_err}", flush=True)
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
                            print(tb)
                        except Exception:
                            pass
                except Exception:
                    pass
            finally:
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
                try:
                    if use_gpu_preload and preloader is not None:
                        preloader.stop()
                except Exception:
                    pass
            if inflight_ok:
                return

            # If inflight was configured but failed to start, fall through to the normal
            # sequential pipeline. Ensure the preloader is running for that path.
            if use_gpu_preload and preloader is None:
                try:
                    preloader = self._start_song_preloader(tasks, completed_songs)
                except Exception as e:
                    print(f"[Song Preloader] Not available: {e}")
                    use_gpu_preload = False

        # ------------------------------------------------------------------
        # Continuous pipeline mode (major refactor):
        # Offload CPU-heavy reporting/persistence to a background process so the
        # main process can continuously feed the GPU with the next song.
        # ------------------------------------------------------------------
        pipeline_enabled = False
        try:
            cfg_dict0 = tasks[0][3] if tasks else {}
            ie = cfg_dict0.get("IterationEngine", {}) if isinstance(cfg_dict0, dict) else {}

            def _get_ci(d: dict, key: str, default=None):
                if not isinstance(d, dict):
                    return default
                if key in d:
                    return d[key]
                lk = str(key).lower()
                if lk in d:
                    return d[lk]
                return d.get(lk, default)

            raw = _get_ci(ie, "ContinuousPipeline", None)
            if raw is None:
                # Default: enable for single-worker GPU runs where post-processing stalls are noticeable.
                pipeline_enabled = self._truthy(_get_ci(ie, "GPU_Mode", "0")) and len(tasks) > 1
            else:
                pipeline_enabled = self._truthy(raw)
        except Exception:
            pipeline_enabled = False

        if pipeline_enabled:
            post_queue = None
            post_proc = None
            pipeline_ok = False
            try:
                from gear_optimizer.pipeline.post_processor import run_post_processor

                post_queue_size = safe_int(os.environ.get("POST_PIPELINE_QUEUE", 8), 8)
                post_queue = multiprocessing.Queue(maxsize=max(1, post_queue_size))
                post_proc = multiprocessing.Process(
                    target=run_post_processor,
                    args=(post_queue, len(tasks)),
                    daemon=True,
                    name="SongPostProcessor",
                )
                post_proc.start()

                preload_idx = 5  # Start preloading from index 5
                preloaded_by_path = {}

                # GPU prefetch manager for ahead-of-time timeline computation
                _gpu_prefetch_mgr, gpu_prefetch_enabled = self._init_gpu_prefetch_manager(use_gpu_preload)

                gpu_prefetched_set = set()

                for i, t in enumerate(tasks):
                    if self._stop_requested_now():
                        break
                    task_key = self._task_queue_label(t)
                    if task_key in completed_songs:
                        continue

                    song_name = t[1]
                    song_path_key = os.path.abspath(str(t[0]))

                    # Drain any newly preloaded songs into a local map for reuse.
                    if use_gpu_preload and preloader is not None:
                        try:
                            while True:
                                preloaded = preloader.get_if_ready()
                                if preloaded is None:
                                    break
                                preloaded_by_path[os.path.abspath(str(preloaded.file_path))] = preloaded
                        except Exception:
                            pass

                    # Prefer preloaded calc_song for this song (skips disk I/O + parsing).
                    task_args = t
                    preloaded_current = preloaded_by_path.get(song_path_key)
                    if preloaded_current is not None and preloaded_current.calc_song and not preloaded_current.error:
                        cloned = self._clone_calc_song_for_run(preloaded_current.calc_song)
                        task_args = t + (cloned, True)
                    else:
                        task_args = t + (True,)

                    # Queue next song for CPU preloading
                    if use_gpu_preload and preload_idx < len(tasks):
                        next_task = tasks[preload_idx]
                        if self._task_queue_label(next_task) not in completed_songs:
                            self._queue_song_for_preload(preloader, next_task)
                        preload_idx += 1

                    try:
                        res = safe_process_song_task(task_args)
                    except Exception as seq_err:
                        res = {
                            "_error": str(seq_err),
                            "_error_type": type(seq_err).__name__,
                            "_song_name": song_name,
                            "song": song_name,
                        }

                    # POST-SONG GPU PREFETCH: Kick off the next song's timeline kernel
                    # while the post-processor builds payloads/prints/saves DB.
                    if gpu_prefetch_enabled and _gpu_prefetch_mgr is not None:
                        try:
                            pick = None
                            if i + 1 < len(tasks):
                                next_path_key = os.path.abspath(str(tasks[i + 1][0]))
                                cand = preloaded_by_path.get(next_path_key)
                                if cand is not None and cand.calc_song and not cand.error:
                                    pick = cand

                            if pick is None:
                                for cand in preloaded_by_path.values():
                                    if cand is not None and cand.calc_song and not cand.error:
                                        pick = cand
                                        break

                            pick_key = os.path.abspath(str(getattr(pick, "file_path", ""))) if pick is not None else ""
                            if pick is not None and pick_key and pick_key not in gpu_prefetched_set:
                                slot = _gpu_prefetch_mgr.prefetch(pick.calc_song, pick.ref_arrays)
                                if slot is not None:
                                    gpu_prefetched_set.add(pick_key)
                        except Exception:
                            pass

                        if i > 0 and i % 10 == 0:
                            stats = _gpu_prefetch_mgr.stats()
                            if stats["prefetch_count"] > 0:
                                print(
                                    f"[GPU Prefetch] Songs prefetched: {stats['prefetch_count']}, "
                                    f"cache hits: {stats['cache_hits']}, "
                                    f"avg time: {stats['avg_prefetch_ms']:.1f}ms"
                                )

                    # Enqueue for post-processing (non-blocking relative to GPU compute).
                    enqueued = True
                    if post_queue is not None:
                        enqueued = False
                        while True:
                            if self._stop_requested_now():
                                break
                            if post_proc is not None and not post_proc.is_alive():
                                self.request_stop("post-processor died")
                                break
                            try:
                                post_queue.put(res, block=True, timeout=0.5)
                                enqueued = True
                                break
                            except Exception:
                                continue

                    # Track completion for resume queue (only for successful compute payloads).
                    if enqueued and isinstance(res, dict) and "_error" not in res:
                        done_name = res.get("song") or song_name
                        done_key = res.get("_queue_key") or res.get("_queue_label") or task_key
                        if done_key:
                            completed_songs.add(done_key)
                        if memory_resume_tracker and done_name:
                            memory_resume_tracker.mark_completed(done_name)

                    if memory_release_requested():
                        print("[MemoryGuard] Early stop in sequential pipeline loop")
                        break
                    if self._stop_requested_now():
                        break
                pipeline_ok = True

            finally:
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
                try:
                    if pipeline_ok and use_gpu_preload and preloader is not None:
                        preloader.stop()
                except Exception:
                    pass
            if pipeline_ok:
                return

        def _safe_sequential_gen(task_list):
            preload_idx = 5  # Start preloading from index 5
            preloaded_by_path = {}

            # GPU prefetch manager for ahead-of-time timeline computation
            _gpu_prefetch_mgr, gpu_prefetch_enabled = self._init_gpu_prefetch_manager(use_gpu_preload)

            # Track which songs we've GPU-prefetched
            gpu_prefetched_set = set()

            for i, t in enumerate(task_list):
                if self._stop_requested_now():
                    break
                task_key = self._task_queue_label(t)
                if task_key in completed_songs:
                    continue

                song_name = t[1]
                song_path_key = os.path.abspath(str(t[0]))

                # Drain any newly preloaded songs into a local map for reuse.
                if use_gpu_preload and preloader is not None:
                    try:
                        while True:
                            preloaded = preloader.get_if_ready()
                            if preloaded is None:
                                break
                            preloaded_by_path[os.path.abspath(str(preloaded.file_path))] = preloaded
                    except Exception:
                        pass

                # Prefer preloaded calc_song for this song (skips disk I/O + parsing).
                task_args = t
                preloaded_current = preloaded_by_path.get(song_path_key)
                if preloaded_current is not None and preloaded_current.calc_song and not preloaded_current.error:
                    cloned = self._clone_calc_song_for_run(preloaded_current.calc_song)
                    task_args = t + (cloned,)

                # Queue next song for CPU preloading
                if use_gpu_preload and preload_idx < len(task_list):
                    next_task = task_list[preload_idx]
                    if self._task_queue_label(next_task) not in completed_songs:
                        self._queue_song_for_preload(preloader, next_task)
                    preload_idx += 1

                try:
                    res = safe_process_song_task(task_args)
                except Exception as seq_err:
                    res = {"_error": str(seq_err), "_error_type": type(seq_err).__name__, "_song_name": t[1]}

                # POST-SONG GPU PREFETCH: Kick off the next song's timeline kernel
                # now so it can run while we do CPU-only result handling (DB, logs).
                if gpu_prefetch_enabled and _gpu_prefetch_mgr is not None:
                    try:
                        # Pick the immediate next song if it has been preloaded; else pick any ready one.
                        pick = None
                        if i + 1 < len(task_list):
                            next_path_key = os.path.abspath(str(task_list[i + 1][0]))
                            cand = preloaded_by_path.get(next_path_key)
                            if cand is not None and cand.calc_song and not cand.error:
                                pick = cand

                        if pick is None:
                            for cand in preloaded_by_path.values():
                                if cand is not None and cand.calc_song and not cand.error:
                                    pick = cand
                                    break

                        pick_key = os.path.abspath(str(getattr(pick, "file_path", ""))) if pick is not None else ""
                        if pick is not None and pick_key and pick_key not in gpu_prefetched_set:
                            slot = _gpu_prefetch_mgr.prefetch(pick.calc_song, pick.ref_arrays)
                            if slot is not None:
                                gpu_prefetched_set.add(pick_key)
                    except Exception:
                        pass

                    # Log prefetch stats periodically
                    if i > 0 and i % 10 == 0:
                        stats = _gpu_prefetch_mgr.stats()
                        if stats["prefetch_count"] > 0:
                            print(
                                f"[GPU Prefetch] Songs prefetched: {stats['prefetch_count']}, "
                                f"cache hits: {stats['cache_hits']}, "
                                f"avg time: {stats['avg_prefetch_ms']:.1f}ms"
                            )

                yield res

                # After processing, release the slot for this song to free it for reuse
                if gpu_prefetch_enabled and _gpu_prefetch_mgr is not None and song_path_key in gpu_prefetched_set:
                    try:
                        # Find and release the slot for this song
                        # The manager keeps track of song_key -> slot mapping internally
                        pass  # Release happens in song_processor.py after GA completes
                    except Exception:
                        pass

        self._consume_results(
            _safe_sequential_gen(tasks),
            completed_songs=completed_songs,
            completed_offset=completed_offset,
            memory_resume_tracker=memory_resume_tracker,
            total_tasks=len(tasks),
        )

    def _queue_song_for_preload(self, preloader, task):
        """Queue a song task for background preloading."""
        try:
            from .helpers.song_preloader import SongLoadRequest

            (
                fp,
                song_name,
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
            ) = task[:16]

            request = SongLoadRequest(
                song_name=song_name,
                file_path=fp,
                difficulty=task_diff,
                cfg_dict=cfg_dict,
                paths=paths,
                ref_arrays=ref_arrays,
                all_gears=all_gears,
                all_minis=all_minis,
                gears_by_name=gears_by_name,
                minis_by_name=minis_by_name,
                use_evo_db=use_evo_db,
                auto_buff=auto_buff,
            )
            preloader.queue_song(request)
        except Exception:
            pass  # Preloading failure is non-fatal

    def _start_song_preloader(self, tasks, completed_songs):
        from .helpers.song_preloader import get_song_preloader

        preloader = get_song_preloader()
        preloader.start()

        # Queue first 5 songs for preloading
        for t in tasks[:5]:
            if self._task_queue_label(t) not in completed_songs:
                self._queue_song_for_preload(preloader, t)

        print("[Song Preloader] Async preloading enabled")
        return preloader

    def _init_gpu_prefetch_manager(self, use_gpu_preload: bool):
        if not use_gpu_preload:
            return None, False
        try:
            from gear_optimizer.solver.taichi_gem.api.gpu_prefetch import get_gpu_prefetch_manager

            prefetch_slots = safe_int(os.environ.get("GPU_PREFETCH_SLOTS", 0))
            if prefetch_slots <= 0:
                prefetch_slots = 5  # default
            keep_slots = self._truthy(os.environ.get("GPU_PREFETCH_KEEP_SLOTS", "0"))
            return (
                get_gpu_prefetch_manager(
                    num_slots=prefetch_slots,
                    keep_slots=keep_slots,
                ),
                True,
            )
        except Exception:
            return None, False

    def _run_parallel(
        self, tasks, max_workers, completed_songs, memory_resume_tracker, manager, status_queue, status_thread
    ):
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
                msg = "[GPU Executor] Taichi init failed or timed out; falling back to direct GPU"
                if err:
                    msg = f"{msg} ({err})"
                print(msg)
                try:
                    gpu_executor.stop()
                except Exception:
                    pass
                gpu_executor = None
            if gpu_executor is not None and gpu_executor.is_running:
                print("[GPU Executor] Started for parallel song processing")
        except Exception as e:
            print(f"[GPU Executor] Failed to start: {e} - workers will use direct GPU")
            gpu_executor = None

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
                if gpu_executor and gpu_executor.is_running:
                    for _ in range(effective_workers):
                        worker_id, req_q, resp_q = gpu_executor.register_worker()
                        worker_registrations.append((worker_id, req_q, resp_q))

                # Use module-level initializer (local functions can't be pickled for spawn)
                if worker_registrations:
                    # All workers share the same request queue, but each worker must have its
                    # own response queue and worker_id to avoid response cross-talk.
                    req_q = worker_registrations[0][1]
                    registrations = [(wid, resp_q) for (wid, _req_q, resp_q) in worker_registrations]
                    reg_counter = mp_ctx.Value("i", 0)
                    reg_lock = mp_ctx.Lock()

                    executor = concurrent.futures.ProcessPoolExecutor(
                        max_workers=effective_workers,
                        mp_context=mp_ctx,
                        initializer=_gpu_worker_initializer,
                        initargs=(req_q, registrations, reg_counter, reg_lock),
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
                        )

                        if self._stop_requested_now():
                            break
                        if memory_release_requested():
                            print("[MemoryGuard] Stopping parallel loop after soft limit.")
                            break
                    finally:
                        try:
                            executor.shutdown(wait=True, cancel_futures=bool(self._stop_requested.is_set()))
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
                        )

                        if self._stop_requested_now():
                            break
                        if memory_release_requested():
                            print("[MemoryGuard] Stopping parallel loop after soft limit.")
                            break
                    finally:
                        try:
                            executor.shutdown(wait=True, cancel_futures=bool(self._stop_requested.is_set()))
                        except Exception:
                            pass

            except BrokenProcessPool as bpp:
                broken_pool_failures += 1
                warn_msg = f"[Auto-Recover] Process pool broke; attempt {broken_pool_failures}/{max_pool_retries}. Reason: {bpp}"
                print(warn_msg)
                logging.error(warn_msg)
                self.discord_reporter.send_log(warn_msg)

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
                    print("[Auto-Recover] Max retries hit; sequential fallback.")
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
    ):
        completed = completed_offset
        failed = 0
        total = total_tasks or 0  # approximate if unknown

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
                    print(err_msg)
                    logging.error(err_msg)
                    self.discord_reporter.send_log(err_msg)
                    if propagate_broken_pool and isinstance(task_err, BrokenProcessPool):
                        raise
                    continue

                # safe_process_song_task can return an error payload; treat it as a failure here too.
                if isinstance(res, dict) and "_error" in res:
                    failed += 1
                    err_type = res.get("_error_type") or type(res.get("_error")).__name__
                    err_msg = f"[{completed}/{total}] FAILED: {song_name} - {err_type}: {res.get('_error')}"
                    print(err_msg)
                    logging.error(err_msg)
                    if res.get("_trace"):
                        logging.error(res.get("_trace"))
                    self.discord_reporter.send_log(err_msg)
                    continue
            else:
                res = item
                if isinstance(res, dict) and "_error" in res:
                    failed += 1
                    err_name = res.get("_queue_label") or res.get("_song_name") or res.get("song")
                    err_type = res.get("_error_type") or type(res.get("_error")).__name__
                    err_msg = f"[{completed}/{total}] FAILED: {err_name} - {err_type}: {res.get('_error')}"
                    print(err_msg)
                    logging.error(err_msg)
                    if res.get("_trace"):
                        logging.error(res.get("_trace"))
                    self.discord_reporter.send_log(err_msg)
                    continue

            song_name = res.get("song", "Unknown")
            task_label = res.get("_queue_label") or res.get("_queue_key") or song_name
            task_key = res.get("_queue_key") or task_label or song_name
            if completed_songs is not None and task_key:
                completed_songs.add(task_key)
            if memory_resume_tracker and song_name:
                memory_resume_tracker.mark_completed(song_name)

            if memory_release_requested():
                print("[MemoryGuard] Early stop in consume_results")
                break

            print(f"[{completed}/{total}] Completed: {task_label}")
            print("=" * 60)
            print(f"PROCESSING SONG: {task_label}")
            print("=" * 60)
            self.discord_reporter.send_stats(build_stats_summary(res, completed, total))

            # DB Stuff - Only save valid entries (non-zero score, has gear/minis)
            persisted = res.get("persist_entries")
            if persisted:
                # Filter: only save entries with score > 0 and at least some gear
                valid_entries = [e for e in persisted if e.get("score", 0) > 0 and (e.get("gear") or e.get("minis"))]
                if valid_entries:
                    self._async_db_saver.submit(
                        res["song"],
                        valid_entries,
                        meta={
                            "file_path": res.get("file_path"),
                            "cfg_dict": res.get("cfg_dict"),
                            "db_key": res.get("db_key"),
                        },
                    )
                else:
                    print(f"[DB] Skipped save for {res['song']}: no valid entries (score=0 or empty loadout)")
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
                        },
                    )
                else:
                    print(f"[DB] Skipped save for {res['song']}: invalid payload (score=0 or empty loadout)")

            log_content = (res.get("log") or "").strip()
            if log_content:
                tail = log_content[-3000:] if len(log_content) > 3000 else log_content
                self.discord_reporter.send_log(f"Log for {res['song']}:\n{tail}")

            # Cleanup
            res["log"] = None
            if "persist_entries" in res:
                res["persist_entries"] = None
            if "db_payload" in res:
                res["db_payload"] = None

        if failed > 0:
            print(f"[SUMMARY] {failed}/{total} songs failed.")

    def _cleanup_resources(self, status_queue, status_thread, manager):
        try:
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
            # Graceful shutdown of async Discord reporter
            if hasattr(self.discord_reporter, "shutdown"):
                try:
                    self.discord_reporter.shutdown(timeout=5.0)
                except Exception:
                    pass
            # Force GC on manager
            old_manager = manager
            del old_manager
            gc.collect(generation=0)

        except Exception:
            pass

    def _handle_loop_restart(self, wait_time=3):
        print(f"Restarting song scan in {wait_time} seconds...")
        try:
            if os.path.exists(MEMORY_GUARD_RESUME_FILE):
                os.remove(MEMORY_GUARD_RESUME_FILE)
                print("[LoopForever] Cleared resume file")
        except Exception as e:
            logging.warning(f"Failed to delete resume file: {e}")
        time.sleep(wait_time)
