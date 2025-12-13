
import concurrent.futures
from concurrent.futures.process import BrokenProcessPool
import configparser
import gc
import json
import logging
import multiprocessing
import os
import re
import threading
import time

import numpy as np

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(_path=None):
        return False

# Import from refactored modules
from gear_optimizer.core.constants import PATHS, SCRIPT_DIR, BIN_DIR, TOTAL_ROWS
from gear_optimizer.core.config import (
    compute_memory_guard_limit,
    load_paths_cache,
)
from gear_optimizer.data.database import (
    init_db,
    save_loadouts_batch,
    get_db_connection,
    get_evolution_db_path,
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
from gear_optimizer.data.discord_reporter import DiscordReporter, build_stats_summary
from gear_optimizer.pipeline.song_processor import safe_process_song_task, scan_song_header
from gear_optimizer.data.csv_parser import (
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from gear_optimizer.core.utils import safe_int, cfg_to_dict
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


class GearOptimizerApp:
    def __init__(self):
        self.setup_logging()
        self.discord_reporter = self.setup_discord()
        self.ensure_directories()

    def setup_logging(self):
        os.makedirs(BIN_DIR, exist_ok=True)
        log_file_path = os.path.join(BIN_DIR, "error.log")
        logging.basicConfig(
            filename=log_file_path,
            level=logging.WARNING,
            format="%(asctime)s %(levelname)s: %(message)s"
        )

    def setup_discord(self):
        env_path = PATHS.discord_env
        if os.path.exists(env_path):
            load_dotenv(env_path)
        else:
            load_dotenv()

        token = os.getenv("DISCORD_TOKEN")
        logging_channel_id = safe_int(os.getenv("LOGGINGCHANNEL"), 0) or None
        stats_channel_id = safe_int(os.getenv("STATSCHANNEL"), 0) or None

        return DiscordReporter(
            token,
            log_channel_id=logging_channel_id,
            stats_channel_id=stats_channel_id,
        )

    def ensure_directories(self):
        os.makedirs(BIN_DIR, exist_ok=True)





    def run(self):
        multiprocessing.freeze_support()
        
        while True:
            should_loop = self._run_single_iteration()
            if not should_loop:
                break

    def _run_single_iteration(self):
        memory_guard_restart = False
        memory_resume_tracker = None
        start_time = time.time()
        loop_forever = False # Default, updated from config

        FEVER_TIMELINE_CACHE.clear()
        GEM_SOLVER_CACHE.clear()
        FG_CACHE.clear()

        manager = None
        status_queue = None
        status_thread = None

        try:
            cfg = configparser.ConfigParser()
            cfg.read("config.ini", encoding="utf-8-sig")
            paths = load_paths_cache()
            set_memory_watchdog_limit(compute_memory_guard_limit(cfg))
            db_display_name = os.path.basename(get_evolution_db_path())
            self.discord_reporter.send_log(
                f"Gear Optimizer run started. DB file: {db_display_name}"
            )

            init_db()
            self._auto_merge_databases()


            # Config reading
            meta_finder = cfg.getboolean("IterationEngine", "MetaFinder", fallback=False)
            enable_auto = bool(meta_finder)
            force_greats_mode = cfg.getboolean("IterationEngine", "ForceGreatsMode", fallback=False)
            force_greats_finder = cfg.getboolean("IterationEngine", "ForceGreatsFinder", fallback=False)
            auto_buff = cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False)
            
            if force_greats_mode:
                fg_status = "ForceGreatsFinder" if force_greats_finder else "Manual Config"
                print(f" >> [ForceGreats] Mode enabled ({fg_status})")

            ga_depth = safe_int(cfg.get("IterationEngine", "GA_SearchDepth", fallback=50))
            use_evo_db = cfg.getboolean("IterationEngine", "UseEvolutionDB", fallback=True)
            loop_forever = cfg.getboolean("IterationEngine", "LoopForever", fallback=False)
            eval_cpu_limit = safe_int(cfg.get("IterationEngine", "EvalCPUCores", fallback=0))

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
            memory_resume_tracker.prime(song_queue, build_memory_guard_resume_context(
                *self._get_filter_params(cfg)
            ))

            manager = multiprocessing.Manager()
            status_queue = manager.Queue()
            
            status_thread = threading.Thread(
                target=self._status_listener, args=(status_queue,), daemon=True
            )
            status_thread.start()

            tasks = self._prepare_tasks(
                song_queue, cfg, paths, ref_arrays, all_gears, all_minis,
                gears_by_name, minis_by_name, use_evo_db, auto_buff,
                ga_depth, status_queue
            )

            parallel_workers = 1
            # MaxParallelSongs limits concurrent song workers to reduce GPU queue contention
            # Default 6 provides good balance between parallelism and per-song latency
            max_parallel_songs = safe_int(cfg.get("IterationEngine", "MaxParallelSongs", fallback=6))
            if max_parallel_songs <= 0:
                max_parallel_songs = 6  # Fallback if invalid
            
            self._execute_tasks(
                tasks, eval_cpu_limit, parallel_workers, memory_resume_tracker, 
                manager, status_queue, status_thread, loop_forever, max_parallel_songs
            )


            # Check if we need to restart due to memory guard
            if memory_release_requested() and loop_forever:
                memory_guard_restart = True

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

        if memory_guard_restart:
            restart_process_for_memory_guard()
            return False # Process replaced
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
                delete_after_merge=True,
                backup_before_merge=True
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
        print(" >> [Auto-Mode] Finders active: Ignoring manual [UserInputStatsGems] & [ElementalGems] to prevent database tainting.")
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
            "Perfect Points", "Combo Multiplier", "Fever Multiplier",
            "Fever Fill Rate", "Fever Time",
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
        
        return (diff_lower, filter_search, target_primary_all, target_primary_colors, target_secondary_all, target_secondary_colors)

    def _build_song_queue(self, cfg, paths, use_evo_db):
        diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols = self._get_filter_params(cfg)
        
        resume_context = build_memory_guard_resume_context(
             diff_lower, filter_search, tp_all, tp_cols, ts_all, ts_cols
        )
        
        resume_seed_queue = load_memory_guard_resume_queue(resume_context)
        if resume_seed_queue:
            print(f"[MemoryGuard] Resuming {len(resume_seed_queue)} song(s) from previous interrupted run.")
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
                        
                        detected_diff = "Unknown"
                        if "(hard)" in name_lower: detected_diff = "Hard"
                        elif "(normal)" in name_lower: detected_diff = "Normal"
                        elif "(easy)" in name_lower: detected_diff = "Easy"
                        else:
                            meta_diff_val = (meta.get("Difficulty") or "").strip().capitalize()
                            if meta_diff_val in ("Hard", "Normal", "Easy"):
                                detected_diff = meta_diff_val

                        if diff_lower in ("easy", "normal", "hard") and detected_diff.lower() != diff_lower:
                            continue

                        primary_color = (meta.get("Primary Color") or "").strip().lower()
                        secondary_color = (meta.get("Secondary Color") or "").strip().lower()

                        if not tp_all and (not primary_color or primary_color not in tp_cols): continue
                        if not ts_all and (not secondary_color or secondary_color not in ts_cols): continue

                        if filter_search and filter_search not in name_lower:
                            continue

                        song_queue.append((fp, name, detected_diff))
                        seen_paths.add(abs_fp)

        if not song_queue:
            print("Error: No matching songs found.")
            return []

        # Queue all discovered songs; filtering is handled by difficulty folder + optional search string.
        if not filter_search:
            return song_queue
         
        print(f"Found {len(song_queue)} songs to process.")
        return song_queue

    def _filter_existing_db_songs(self, song_queue, use_evo_db):
        existing_songs = set()
        if use_evo_db:
            try:
                conn = get_db_connection()
                cursor = conn.execute("SELECT name FROM songs")
                existing_songs = {row[0] for row in cursor}
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    conn.execute("PRAGMA optimize")
                except Exception as e:
                    logging.warning(f"[DB] WAL checkpoint/optimize failed: {e}")
                conn.close()
            except Exception as e:
                print(f"[DB] Error fetching existing songs: {e}")

        # Legacy helper retained for compatibility, but we always process the full queue now.
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

    def _prepare_tasks(self, song_queue, cfg, paths, ref_arrays, all_gears, all_minis,
                      gears_by_name, minis_by_name, use_evo_db, auto_buff, ga_depth, status_queue):
        cfg_dict = cfg_to_dict(cfg)
        tasks = []
        parallel_workers = 1 
        for fp, found_song_name, task_diff in song_queue:
            print(f"[QUEUE] {found_song_name}")
            tasks.append((
                fp, found_song_name, task_diff, cfg_dict, paths, ref_arrays,
                all_gears, all_minis, gears_by_name, minis_by_name,
                use_evo_db, auto_buff, ga_depth, status_queue, parallel_workers,
            ))
        return tasks

    def _execute_tasks(self, tasks, eval_cpu_limit, parallel_workers, memory_resume_tracker,
                       manager, status_queue, status_thread, loop_forever, max_parallel_songs=6):
        """Execute tasks with configurable parallelism.
        
        Args:
            max_parallel_songs: Max concurrent song workers (default 6).
                               This limits GPU executor queue depth to improve
                               per-song latency without affecting total throughput.
        """
        logical_cpus = os.cpu_count() or 1
        available_cpus = logical_cpus
        if eval_cpu_limit and eval_cpu_limit > 0:
            available_cpus = max(1, min(logical_cpus, eval_cpu_limit))
        
        song_worker_limit = max(1, available_cpus // max(1, parallel_workers))
        # Apply MaxParallelSongs cap to reduce GPU executor queue contention
        max_workers = max(1, min(len(tasks), song_worker_limit, max_parallel_songs))
        
        if available_cpus != logical_cpus:
             print(f"EvalCPUCores cap applied: using {available_cpus} of {logical_cpus} cores.")

        print(f"Parallel plan -> songs: {len(tasks)}, concurrent workers: {max_workers}, cores per song: {parallel_workers}")
        print(f"Using {available_cpus} logical CPU cores")


        completed_songs = set()
        
        if len(tasks) > 1 and max_workers > 1:
            self._run_parallel(
                tasks, max_workers, completed_songs, memory_resume_tracker,
                manager, status_queue, status_thread
            )
        else:
            self._run_sequential(tasks, completed_songs, memory_resume_tracker)

        if memory_release_requested():
            print("[MemoryGuard] Soft limit reached; pending songs saved for resume.")
            if loop_forever:
                print("[MemoryGuard] LoopForever enabled; scheduling automatic restart.")
                self.discord_reporter.send_log(
                    "Memory soft limit reached; restarting MetaFinder to release RAM."
                )

        if memory_resume_tracker:
            memory_resume_tracker.finalize(memory_release_requested())

    def _run_sequential(self, tasks, completed_songs, memory_resume_tracker):
        """Sequential song processing with async preloading.
        
        While GPU processes current song, next song is being preloaded in background.
        """
        completed_offset = len(completed_songs)
        
        # Check if GPU preloading should be used
        use_gpu_preload = len(tasks) > 1
        
        if use_gpu_preload:
            try:
                from .helpers.song_preloader import get_song_preloader
                preloader = get_song_preloader()
                preloader.start()
                
                # Queue first 2 songs for preloading
                for i, t in enumerate(tasks[:2]):
                    if t[1] not in completed_songs:
                        self._queue_song_for_preload(preloader, t)
                
                print("[Song Preloader] Async preloading enabled")
            except Exception as e:
                print(f"[Song Preloader] Not available: {e}")
                use_gpu_preload = False
        
        def _safe_sequential_gen(task_list):
            preload_idx = 2  # Start preloading from index 2
            
            for i, t in enumerate(task_list):
                if t[1] in completed_songs:
                    continue
                
                # Queue next song for preloading
                if use_gpu_preload and preload_idx < len(task_list):
                    next_task = task_list[preload_idx]
                    if next_task[1] not in completed_songs:
                        self._queue_song_for_preload(preloader, next_task)
                    preload_idx += 1
                
                try:
                    yield safe_process_song_task(t)
                except Exception as seq_err:
                    yield {"_error": str(seq_err), "_error_type": type(seq_err).__name__, "_song_name": t[1]}

        self._consume_results(
            _safe_sequential_gen(tasks),
            completed_songs=completed_songs,
            completed_offset=completed_offset,
            memory_resume_tracker=memory_resume_tracker,
            total_tasks=len(tasks)
        )
    
    def _queue_song_for_preload(self, preloader, task):
        """Queue a song task for background preloading."""
        try:
            from .helpers.song_preloader import SongLoadRequest
            
            fp, song_name, task_diff, cfg_dict, paths, ref_arrays, \
                all_gears, all_minis, gears_by_name, minis_by_name, \
                use_evo_db, auto_buff, ga_depth, status_queue, parallel_workers = task
            
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
        except Exception as e:
            pass  # Preloading failure is non-fatal

    def _run_parallel(self, tasks, max_workers, completed_songs, memory_resume_tracker, manager, status_queue, status_thread):
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
            print("[GPU Executor] Started for parallel song processing")
        except Exception as e:
            print(f"[GPU Executor] Failed to start: {e} - workers will use direct GPU")
            gpu_executor = None

        while remaining_tasks:
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
                    
                    with concurrent.futures.ProcessPoolExecutor(
                        max_workers=effective_workers,
                        mp_context=mp_ctx,
                        initializer=_gpu_worker_initializer,
                        initargs=(req_q, registrations, reg_counter, reg_lock),
                    ) as executor:
                        future_map = {executor.submit(safe_process_song_task, t): t[1] for t in remaining_tasks}
                        self._consume_results(
                            concurrent.futures.as_completed(future_map),
                            future_map=future_map,
                            propagate_broken_pool=True,
                            completed_songs=completed_songs,
                            completed_offset=completed_offset,
                            memory_resume_tracker=memory_resume_tracker,
                            total_tasks=len(tasks)
                        )
                        
                        if memory_release_requested():
                             print("[MemoryGuard] Stopping parallel loop after soft limit.")
                             break
                else:
                    # Fallback: no GPU executor, workers use direct GPU (may conflict)
                    with concurrent.futures.ProcessPoolExecutor(max_workers=effective_workers, mp_context=mp_ctx) as executor:
                        future_map = {executor.submit(safe_process_song_task, t): t[1] for t in remaining_tasks}
                        self._consume_results(
                            concurrent.futures.as_completed(future_map),
                            future_map=future_map,
                            propagate_broken_pool=True,
                            completed_songs=completed_songs,
                            completed_offset=completed_offset,
                            memory_resume_tracker=memory_resume_tracker,
                            total_tasks=len(tasks)
                        )
                        
                        if memory_release_requested():
                             print("[MemoryGuard] Stopping parallel loop after soft limit.")
                             break

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
                remaining_songs = [t for t in tasks if t[1] not in completed_songs]
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


    def _consume_results(self, results_iter, future_map=None, propagate_broken_pool=False,
                         completed_songs=None, completed_offset=0, memory_resume_tracker=None, total_tasks=0):
        completed = completed_offset
        failed = 0
        total = total_tasks or 0 # approximate if unknown
        
        for item in results_iter:
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
                    err_name = res.get("_song_name") or res.get("song")
                    err_type = res.get("_error_type") or type(res.get("_error")).__name__
                    err_msg = f"[{completed}/{total}] FAILED: {err_name} - {err_type}: {res.get('_error')}"
                    print(err_msg)
                    logging.error(err_msg)
                    if res.get("_trace"):
                        logging.error(res.get("_trace"))
                    self.discord_reporter.send_log(err_msg)
                    continue
            
            song_name = res.get("song", "Unknown")
            if completed_songs is not None and song_name:
                completed_songs.add(song_name)
            if memory_resume_tracker:
                memory_resume_tracker.mark_completed(song_name)

            if memory_release_requested():
                print("[MemoryGuard] Early stop in consume_results")
                break

            print(f"[{completed}/{total}] Completed: {res['song']}")
            print("=" * 60)
            print(f"PROCESSING SONG: {res['song']}")
            print("=" * 60)
            self.discord_reporter.send_stats(build_stats_summary(res, completed, total))
            
            # DB Stuff
            use_evo_db = True # Assumed true if we got here usually, or check config
            persisted = res.get("persist_entries")
            if persisted:
                 save_loadouts_batch(res["song"], persisted)
            elif res.get("db_payload"):
                 pl = res["db_payload"]
                 save_loadouts_batch(res["song"], [{
                     "score": pl.get("score", 0),
                     "fg_score": pl.get("fg_score", 0),
                     "gear": pl.get("gear", []),
                     "minis": pl.get("minis", []),
                     "details": pl.get("details", {}),
                     "force": pl.get("force"),
                 }])

            log_content = (res.get("log") or "").strip()
            if log_content:
                tail = log_content[-3000:] if len(log_content) > 3000 else log_content
                self.discord_reporter.send_log(f"Log for {res['song']}:\n{tail}")

            # Cleanup
            res["log"] = None
            if "persist_entries" in res: res["persist_entries"] = None
            if "db_payload" in res: res["db_payload"] = None

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
