from __future__ import annotations

import os
import time
import zlib
from pathlib import Path
from typing import Any


def _truthy_env(name: str) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _shard_index_for_song(song_name: str, difficulty: str, *, instances: int) -> int:
    n = max(1, int(instances or 1))
    key = f"{str(song_name)}|{str(difficulty)}".encode("utf-8", errors="replace")
    return int(zlib.crc32(key) & 0xFFFFFFFF) % int(n)


def shard_inflight_tasks(tasks: list[tuple], *, instances: int) -> list[list[tuple]]:
    """
    Deterministically shard in-flight task tuples across worker processes.

    - Shard key is (song_name, difficulty) so SongRepeats stay on the same worker.
    - Per-shard order preserves the original queue order.
    """
    n = max(1, int(instances or 1))
    shards: list[list[tuple]] = [[] for _ in range(n)]
    for task in tasks or []:
        try:
            song_name = task[1]
            difficulty = task[2]
        except Exception:
            song_name = "Unknown"
            difficulty = "Unknown"
        shards[_shard_index_for_song(str(song_name), str(difficulty), instances=n)].append(task)
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
