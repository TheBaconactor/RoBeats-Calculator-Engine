from __future__ import annotations

import os
import time
import zlib
from pathlib import Path
from typing import Any

from gear_optimizer.core.parsing import env_flag
from gear_optimizer.core.utils import safe_int


def _truthy_env(name: str) -> bool:
    return env_flag(name)


def _env_override_present(name: str) -> bool:
    raw = os.environ.get(name)
    return raw is not None and str(raw).strip() != ""


def _ceil_div(n: int, d: int) -> int:
    nn = int(n)
    dd = max(1, int(d))
    return int((nn + dd - 1) // dd)


def _read_cfg_int(cfg_dict: dict | None, *, section: str, key: str, default: int = 0) -> int:
    if not isinstance(cfg_dict, dict):
        return int(default)
    sec = cfg_dict.get(section)
    if not isinstance(sec, dict):
        return int(default)
    return safe_int(sec.get(key), int(default))


def recommend_dual_process_inflight_thread_overrides(
    cfg_dict: dict | None,
    *,
    inflight_limit: int,
    instances: int,
    logical_cpus: int | None = None,
) -> dict[str, int]:
    """
    Recommend conservative per-process thread pool sizes for dual-process in-flight mode.

    Dual-process mode creates multiple independent thread pools per worker. Reusing the
    single-process `InFlight_*Workers` defaults/config verbatim can oversubscribe the CPU.
    This helper:
    - splits configured worker counts across instances
    - caps per-pool worker counts based on per-worker CPU budget
    - returns values suitable for `INFLIGHT_*_WORKERS` env overrides

    Note: this is a heuristic default. If it causes regressions (GPU underfeed, FG backlog
    growth, slower wall time), set explicit `INFLIGHT_*_WORKERS` env vars to take control
    and bypass these recommendations.
    """
    try:
        n_instances = max(1, int(instances or 1))
    except Exception:
        n_instances = 1
    if n_instances <= 1:
        return {}

    inflight_limit_i = max(1, int(inflight_limit or 1))

    ncpu = logical_cpus if logical_cpus is not None else (os.cpu_count() or 1)
    try:
        ncpu = int(ncpu)
    except Exception:
        ncpu = 1
    ncpu = max(1, int(ncpu))

    per_worker_cpu = max(1, int(ncpu) // int(n_instances))

    # Cap: 1..4 threads for the heavier pools, scaled by available CPU per worker.
    # Example: 16 logical CPUs, 2 instances => per_worker_cpu=8 => cap=2.
    heavy_cap = max(1, min(4, int((per_worker_cpu + 1) // 4)))
    aux_cap = max(1, min(2, int(heavy_cap)))

    prep_cfg = _read_cfg_int(cfg_dict, section="IterationEngine", key="inflight_prepworkers", default=0)
    decode_cfg = _read_cfg_int(cfg_dict, section="IterationEngine", key="inflight_decodeworkers", default=0)
    fg_cfg = _read_cfg_int(cfg_dict, section="IterationEngine", key="inflight_fgworkers", default=0)
    fg_prep_cfg = _read_cfg_int(cfg_dict, section="IterationEngine", key="inflight_fgprepworkers", default=0)
    db_prefetch_cfg = _read_cfg_int(cfg_dict, section="IterationEngine", key="inflight_dbprefetchworkers", default=0)

    def _scaled(cfg_val: int, *, default: int, cap: int) -> int:
        val = safe_int(cfg_val, 0)
        if val > 0:
            val = _ceil_div(int(val), int(n_instances))
        else:
            val = int(default)
        val = max(1, min(int(val), int(cap), int(inflight_limit_i)))
        return int(val)

    prep = _scaled(prep_cfg, default=heavy_cap, cap=heavy_cap)
    decode = _scaled(decode_cfg, default=heavy_cap, cap=heavy_cap)
    fg_prep = _scaled(fg_prep_cfg, default=aux_cap, cap=aux_cap)
    db_prefetch = _scaled(db_prefetch_cfg, default=aux_cap, cap=aux_cap)
    fg_default = min(4, int(inflight_limit_i))
    fg = _scaled(fg_cfg, default=fg_default, cap=min(4, int(heavy_cap)))

    return {
        "INFLIGHT_PREP_WORKERS": int(prep),
        "INFLIGHT_DECODE_WORKERS": int(decode),
        "INFLIGHT_FG_WORKERS": int(fg),
        "INFLIGHT_FG_PREP_WORKERS": int(fg_prep),
        "INFLIGHT_DB_PREFETCH_WORKERS": int(db_prefetch),
    }


def _apply_thread_overrides(thread_overrides: dict[str, int] | None) -> None:
    if not isinstance(thread_overrides, dict) or not thread_overrides:
        return
    for name, value in thread_overrides.items():
        if not isinstance(name, str) or not name.strip():
            continue
        if _env_override_present(name):
            continue
        try:
            os.environ[str(name).strip()] = str(int(value))
        except Exception:
            continue


def _shard_index_for_song(song_name: str, difficulty: str, *, instances: int) -> int:
    n = max(1, int(instances or 1))
    key = f"{str(song_name)}|{str(difficulty)}".encode("utf-8", errors="replace")
    return int(zlib.crc32(key) & 0xFFFFFFFF) % int(n)


def _difficulty_weight(difficulty: str) -> int:
    d = str(difficulty or "").strip().lower()
    if d == "easy":
        return 1
    if d == "normal":
        return 2
    if d == "hard":
        return 3
    return 2


def shard_inflight_tasks(tasks: list[tuple], *, instances: int) -> list[list[tuple]]:
    """
    Deterministically shard in-flight task tuples across worker processes.

    - Shard key is (song_name, difficulty) so SongRepeats stay on the same worker.
    - Uses deterministic greedy balancing so dual-process workers get closer load.
    - Per-shard task order preserves the original queue order.
    """
    n = max(1, int(instances or 1))
    shards: list[list[tuple]] = [[] for _ in range(n)]
    if n <= 1:
        return [list(tasks or [])]

    grouped: dict[tuple[str, str], list[tuple]] = {}
    for task in tasks or []:
        try:
            song_name = str(task[1] or "")
            difficulty = str(task[2] or "")
        except Exception:
            song_name = "Unknown"
            difficulty = "Unknown"
        grouped.setdefault((song_name, difficulty), []).append(task)

    # Deterministic greedy assignment:
    # - heavier groups first (repeat count * coarse difficulty proxy)
    # - stable tie-break by crc32(song|difficulty)
    # This keeps same (song,diff) together but avoids severe shard skew.
    groups_sorted: list[tuple[str, str, int, int]] = []
    for (song_name, difficulty), group_tasks in grouped.items():
        key_bytes = f"{song_name}|{difficulty}".encode("utf-8", errors="replace")
        key_hash = int(zlib.crc32(key_bytes) & 0xFFFFFFFF)
        weight = max(1, len(group_tasks)) * _difficulty_weight(difficulty)
        groups_sorted.append((song_name, difficulty, int(weight), int(key_hash)))
    groups_sorted.sort(key=lambda x: (-int(x[2]), int(x[3]), str(x[0]), str(x[1])))

    shard_loads = [0 for _ in range(n)]
    group_to_shard: dict[tuple[str, str], int] = {}
    for song_name, difficulty, weight, _key_hash in groups_sorted:
        target_idx = min(range(n), key=lambda i: (int(shard_loads[i]), int(i)))
        group_to_shard[(str(song_name), str(difficulty))] = int(target_idx)
        shard_loads[target_idx] = int(shard_loads[target_idx]) + int(weight)

    # Preserve per-shard order as seen in the original queue.
    for task in tasks or []:
        try:
            song_name = str(task[1] or "")
            difficulty = str(task[2] or "")
        except Exception:
            song_name = "Unknown"
            difficulty = "Unknown"
        idx = int(
            group_to_shard.get((song_name, difficulty), _shard_index_for_song(song_name, difficulty, instances=n))
        )
        shards[idx].append(task)
    return shards


def _suffix_path(path: str, *, suffix: str) -> str:
    root, ext = os.path.splitext(str(path))
    if ext:
        return f"{root}{suffix}{ext}"
    return f"{root}{suffix}"


def _default_repo_root() -> Path:
    # This module lives at gear_optimizer/solver/*.py, so parents[2] is repo root.
    return Path(__file__).resolve().parents[2]


def _configure_worker_disk_artifacts(worker_index: int) -> None:
    suffix = f".w{int(worker_index)}"

    trace_path = str(os.environ.get("GPU_EXECUTOR_TRACE_PATH", "") or "").strip()
    if trace_path:
        os.environ["GPU_EXECUTOR_TRACE_PATH"] = _suffix_path(trace_path, suffix=suffix)

    heartbeat_path = str(os.environ.get("GPU_EXECUTOR_HEARTBEAT_PATH", "") or "").strip()
    if heartbeat_path:
        os.environ["GPU_EXECUTOR_HEARTBEAT_PATH"] = _suffix_path(heartbeat_path, suffix=suffix)
    else:
        repo_root = _default_repo_root()
        os.environ["GPU_EXECUTOR_HEARTBEAT_PATH"] = str(repo_root / "bin" / f"gpu_executor_heartbeat{suffix}.json")

    if _truthy_env("INFLIGHT_STAGE_PROFILE"):
        stage_path = str(os.environ.get("INFLIGHT_STAGE_PROFILE_PATH", "") or "").strip()
        if stage_path:
            os.environ["INFLIGHT_STAGE_PROFILE_PATH"] = _suffix_path(stage_path, suffix=suffix)
        else:
            repo_root = _default_repo_root()
            os.environ["INFLIGHT_STAGE_PROFILE_PATH"] = str(repo_root / "bin" / f"inflight_stage_profile{suffix}.json")


def _configure_worker_vulkan_device(worker_index: int, *, instances: int) -> None:
    raw = str(os.environ.get("INFLIGHT_VULKAN_VISIBLE_DEVICES", "") or "").strip()
    if not raw:
        return
    parts = [p.strip() for p in raw.split(",")]
    idx = int(worker_index)
    if idx < 0 or idx >= len(parts):
        return
    dev = str(parts[idx] or "").strip()
    if dev:
        # Keep the repo alias and Taichi's standard selector synchronized.
        os.environ["TAICHI_VULKAN_VISIBLE_DEVICE"] = dev
        os.environ["TI_VISIBLE_DEVICE"] = dev


def dual_process_inflight_worker_main(
    worker_index: int,
    instances: int,
    *,
    shared_ctx: tuple,
    work_items: list[tuple],
    inflight_songs: int,
    post_queue: Any,
    control_queue: Any,
    stop_event: Any,
    thread_overrides: dict[str, int] | None = None,
    initial_completed_keys: list[str] | None = None,
) -> None:
    """
    Worker entrypoint for dual-process native in-flight mode.

    This intentionally imports the Taichi/Vulkan owner pipeline lazily so the coordinator can
    import this module without initializing Taichi.
    """
    try:
        _configure_worker_vulkan_device(int(worker_index), instances=int(instances))
    except Exception:
        pass
    try:
        _configure_worker_disk_artifacts(int(worker_index))
    except Exception:
        pass

    # In dual-process mode, each worker creates multiple ThreadPoolExecutors. Apply
    # conservative per-pool sizes by default to avoid CPU oversubscription.
    try:
        _apply_thread_overrides(thread_overrides)
    except Exception:
        pass

    def _progress_cb(*, completed_delta: int = 0, failed_delta: int = 0, record_info: dict | None = None) -> None:
        try:
            control_queue.put(
                {
                    "type": "progress",
                    "worker": int(worker_index),
                    "completed_delta": int(completed_delta or 0),
                    "failed_delta": int(failed_delta or 0),
                    "record_info": record_info if isinstance(record_info, dict) else None,
                }
            )
        except Exception:
            pass

    def _bundle_completed_cb(task_key: str, _completed: set[str]) -> None:
        try:
            control_queue.put(
                {
                    "type": "completed",
                    "worker": int(worker_index),
                    "task_key": str(task_key or "").strip(),
                }
            )
        except Exception:
            pass

    def _stop_requested() -> bool:
        try:
            return bool(stop_event.is_set())
        except Exception:
            return False

    try:
        (
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
        ) = shared_ctx
    except Exception:
        cfg_dict = {}
        paths = None
        ref_arrays = None
        all_gears = None
        all_minis = None
        gears_by_name = None
        minis_by_name = None
        use_evo_db = True
        auto_buff = False
        ga_depth = 1
        parallel_workers = 1
        fg_debug = False

    tasks: list[tuple] = []
    for item in work_items or []:
        try:
            fp, song_name, diff, extras = item
        except Exception:
            continue
        if extras is None:
            extras_list: list[Any] = []
        elif isinstance(extras, list):
            extras_list = extras
        else:
            extras_list = [extras]
        tasks.append(
            tuple(
                [
                    fp,
                    song_name,
                    diff,
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
                    None,  # status_queue (unused in native in-flight)
                    parallel_workers,
                    fg_debug,
                ]
                + list(extras_list)
            )
        )

    completed_init = set(str(x) for x in (initial_completed_keys or []) if str(x or "").strip())

    try:
        from gear_optimizer.solver.native_inflight_orchestrator import run_native_inflight_song_pipeline

        run_native_inflight_song_pipeline(
            tasks,
            in_flight_songs=max(1, int(inflight_songs or 1)),
            completed_songs=completed_init,
            memory_resume_tracker=None,  # coordinator owns resume tracking
            post_queue=post_queue,
            total_tasks=None,
            stop_requested=_stop_requested,
            progress_cb=_progress_cb,
            bundle_completed_cb=_bundle_completed_cb,
        )
    except Exception as exc:
        try:
            tb = __import__("traceback").format_exc()
        except Exception:
            tb = ""
        try:
            control_queue.put(
                {
                    "type": "fatal",
                    "worker": int(worker_index),
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": tb,
                }
            )
        except Exception:
            pass
        try:
            stop_event.set()
        except Exception:
            pass
        raise
    finally:
        # Best-effort: signal we're exiting so the coordinator can stop waiting promptly.
        try:
            control_queue.put({"type": "exited", "worker": int(worker_index), "ts": time.time()})
        except Exception:
            pass
