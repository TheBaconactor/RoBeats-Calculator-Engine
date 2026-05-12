from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path
import logging
import queue
import threading
import traceback
from typing import Any

from gear_optimizer.core.env_config import ENV
from gear_optimizer.core.parsing import env_flag, env_get
from gear_optimizer.solver.gpu_executor_types import build_shutdown_request

from gear_optimizer.solver.windows_timer import (
    acquire_windows_timer_period_1ms as _acquire_windows_timer_period_1ms_shared,
    release_windows_timer_period_1ms as _release_windows_timer_period_1ms_shared,
    system_timer_override_allowed as _system_timer_override_allowed_shared,
)


logger = logging.getLogger(__name__)
WARMUP_SENTINEL_SCHEMA = 3
GA_WARMUP_PROFILE = "v4_live_request_setup_refresh"


@dataclass(frozen=True)
class ExecutorStartSettings:
    idle_sample_threshold_sec: float
    live_enabled: bool
    live_interval_sec: float
    trace_path: str
    heartbeat_path: Path
    heartbeat_interval_sec: float
    enable_high_res_timer: bool


@dataclass(frozen=True)
class ExecutorStopProfilerSettings:
    print_taichi_kernel_profiler: bool
    report_gpu_profiler: bool


@dataclass(frozen=True)
class TaichiInitFailureReport:
    error: str
    trace_path: Path | None


def default_executor_heartbeat_path() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "bin" / "gpu_executor_heartbeat.json"


def load_executor_start_settings(
    *,
    in_process: bool,
    env_get_fn: Callable[..., Any] = env_get,
    env_flag_fn: Callable[..., bool] = env_flag,
    os_name: str,
    env_config: Any = ENV,
    system_timer_override_allowed_fn: Callable[[], bool] | None = None,
    default_heartbeat_path_fn: Callable[[], Path] = default_executor_heartbeat_path,
) -> ExecutorStartSettings:
    try:
        idle_ms = float(env_get_fn("GPU_EXECUTOR_IDLE_SAMPLE_THRESHOLD_MS", "1.0"))
    except (ValueError, TypeError):
        idle_ms = 1.0

    try:
        live_interval_sec = float(env_get_fn("GPU_EXECUTOR_LIVE_INTERVAL_SEC", "1.0"))
    except (ValueError, TypeError):
        live_interval_sec = 1.0

    heartbeat_raw = str(env_get_fn("GPU_EXECUTOR_HEARTBEAT_PATH", "") or "").strip()
    try:
        heartbeat_interval_sec = max(
            0.1,
            float(env_get_fn("GPU_EXECUTOR_HEARTBEAT_INTERVAL_SEC", "2.0") or "2.0"),
        )
    except (ValueError, TypeError):
        heartbeat_interval_sec = 2.0

    enable_high_res_timer = False
    if system_timer_override_allowed_fn is None:
        system_timer_override_allowed_fn = system_timer_override_allowed
    if bool(in_process) and str(os_name) == "nt" and bool(system_timer_override_allowed_fn()):
        try:
            raw_wait = env_get_fn("GPU_EXECUTOR_BATCH_WAIT_MS")
            if raw_wait is None or str(raw_wait).strip() == "":
                base_wait_ms = int(getattr(env_config, "gpu_executor_batch_wait_ms", 10) or 10)
                batch_wait_ms = min(int(base_wait_ms), 6)
            else:
                batch_wait_ms = int(str(raw_wait).strip())
        except (ValueError, TypeError):
            batch_wait_ms = 6
        try:
            after_first_ms = int(env_get_fn("GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS", "2") or "2")
        except (ValueError, TypeError):
            after_first_ms = 2
        enable_high_res_timer = (0 < int(batch_wait_ms) <= 4) or (0 < int(after_first_ms) <= 4)

    return ExecutorStartSettings(
        idle_sample_threshold_sec=max(0.0, float(idle_ms) / 1000.0),
        live_enabled=bool(env_flag_fn("GPU_EXECUTOR_LIVE")),
        live_interval_sec=float(live_interval_sec),
        trace_path=str(env_get_fn("GPU_EXECUTOR_TRACE_PATH", "") or "").strip(),
        heartbeat_path=Path(heartbeat_raw) if heartbeat_raw else default_heartbeat_path_fn(),
        heartbeat_interval_sec=float(heartbeat_interval_sec),
        enable_high_res_timer=bool(enable_high_res_timer),
    )


def load_executor_stop_profiler_settings(
    *,
    env_flag_fn: Callable[..., bool] = env_flag,
    env_config: Any = ENV,
) -> ExecutorStopProfilerSettings:
    return ExecutorStopProfilerSettings(
        print_taichi_kernel_profiler=bool(env_flag_fn("TAICHI_KERNEL_PROFILER_PRINT")),
        report_gpu_profiler=bool(getattr(env_config, "gpu_profiler", False)),
    )


def ga_light_warmup_enabled(
    *,
    warmup_ga: bool,
    env_flag_fn: Callable[..., bool] = env_flag,
) -> bool:
    try:
        return bool(warmup_ga) and bool(env_flag_fn("GPU_NATIVE_GA_PHASE_TIMING", "0"))
    except (ValueError, TypeError):
        return False


def executor_auto_stop_enabled(env_flag_fn: Callable[..., bool] = env_flag) -> bool:
    try:
        return bool(env_flag_fn("GPU_EXECUTOR_AUTO_STOP"))
    except (ValueError, TypeError):
        return False


def stop_executor_if_running(executor: Any | None) -> bool:
    if executor is None:
        return False
    if bool(getattr(executor, "is_running", False)):
        executor.stop()
        return True
    return False


def send_shutdown_request(
    request_queue: Any,
    *,
    request_factory: Callable[[], Any] = build_shutdown_request,
) -> None:
    request_queue.put(request_factory())


def try_send_shutdown_request(
    request_queue: Any,
    *,
    request_factory: Callable[[], Any] = build_shutdown_request,
) -> bool:
    try:
        send_shutdown_request(request_queue, request_factory=request_factory)
        return True
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:try_send_shutdown_request: {e}")
        return False


def configure_executor_server_state(
    executor: Any,
    *,
    request_queue: Any,
    response_queues: Mapping[int, Any] | None,
) -> bool:
    executor._request_queue = request_queue
    executor._response_queues = dict(response_queues or {})
    executor._in_process_queues = isinstance(request_queue, queue.Queue)
    executor._running = True
    executor._taichi_ready = False
    executor._last_init_error = None
    try:
        executor._ready_event.clear()
        return True
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:configure_executor_server_state: {e}")
        return False


def apply_vulkan_visible_device(
    vulkan_visible_device: Any,
    *,
    environ: MutableMapping[str, str],
) -> str | None:
    if vulkan_visible_device is None:
        return None
    visible_device = str(vulkan_visible_device).strip()
    if not visible_device:
        return None
    environ["TAICHI_VULKAN_VISIBLE_DEVICE"] = visible_device
    environ["TI_VISIBLE_DEVICE"] = visible_device
    return visible_device


def executor_visible_device_label(env_get_fn: Callable[..., Any] = env_get) -> str:
    try:
        visible_device = str(env_get_fn("TAICHI_VULKAN_VISIBLE_DEVICE", "") or "").strip()
    except (ValueError, TypeError):
        visible_device = ""
    return visible_device or "default"


def build_taichi_init_failure_report(
    exc: BaseException,
    *,
    heartbeat_path: Path,
    traceback_format_fn: Callable[[], str] = traceback.format_exc,
) -> TaichiInitFailureReport:
    err = f"{type(exc).__name__}: {exc}"
    try:
        tb = traceback_format_fn()
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:build_taichi_init_failure_report: {e}")
        tb = ""

    trace_path = None
    try:
        trace_path = heartbeat_path.with_name(heartbeat_path.stem + "_taichi_init_error.log")
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(tb, encoding="utf-8", errors="replace")
    except OSError:
        trace_path = None

    if trace_path is not None:
        err = f"{err} (trace: {trace_path})"
    return TaichiInitFailureReport(error=err, trace_path=trace_path)


def signal_executor_ready(
    *,
    ready_event: Any,
    ready_queue: Any | None,
    wait_fn: Callable[[], Any],
    ready_state_fn: Callable[[], bool],
    init_error_fn: Callable[[], Any],
) -> None:
    try:
        wait_fn()
    finally:
        try:
            ready_event.set()
        except Exception as e:
            logger.debug(f"gpu_executor_lifecycle:signal_executor_ready: {e}")
        if ready_queue is not None:
            try:
                ready_queue.put(
                    {
                        "ok": bool(ready_state_fn()),
                        "error": init_error_fn(),
                    }
                )
            except Exception as e:
                logger.debug(f"gpu_executor_lifecycle:signal_executor_ready: {e}")


def start_executor_ready_signal_thread(
    *,
    ready_event: Any | None,
    ready_queue: Any | None,
    label: str,
    wait_fn: Callable[[], Any],
    ready_state_fn: Callable[[], bool],
    init_error_fn: Callable[[], Any],
    thread_factory: Callable[..., Any] = threading.Thread,
) -> bool:
    if ready_event is None:
        return False

    def _signal_ready() -> None:
        signal_executor_ready(
            ready_event=ready_event,
            ready_queue=ready_queue,
            wait_fn=wait_fn,
            ready_state_fn=ready_state_fn,
            init_error_fn=init_error_fn,
        )

    thread_factory(
        target=_signal_ready,
        name=f"GpuExecutorReady[{label}]",
        daemon=True,
    ).start()
    return True


def build_warmup_sentinel_payload(
    *,
    ok: bool,
    error: str,
    pid: int,
    warmed_at_ms: int,
    warmup_fg: bool,
    warmup_ga: bool,
) -> dict[str, Any]:
    return {
        "schema": int(WARMUP_SENTINEL_SCHEMA),
        "ok": bool(ok),
        "error": str(error or ""),
        "pid": int(pid),
        "warmed_at": int(warmed_at_ms),
        "warmup_fg": bool(warmup_fg),
        "warmup_ga": bool(warmup_ga),
        "ga_warmup_profile": str(GA_WARMUP_PROFILE),
    }


def warmup_sentinel_path(cache_dir: Any) -> Path | None:
    cache_dir_s = str(cache_dir or "").strip()
    if not cache_dir_s:
        return None
    return Path(cache_dir_s) / "metafinder_warmup_done.json"


def write_warmup_sentinel_payload(
    *,
    sentinel_path: Path,
    payload: dict[str, Any],
    replace_fn: Callable[[Any, Any], Any] = os.replace,
) -> bool:
    try:
        sentinel_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = sentinel_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        replace_fn(tmp_path, sentinel_path)
        return True
    except (OSError, ValueError, TypeError):
        return False


def warmup_sentinel_is_fresh(
    *,
    sentinel_path: Path,
    warmup_fg: bool,
    warmup_ga: bool,
) -> bool:
    try:
        payload = json.loads(sentinel_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:warmup_sentinel_is_fresh: {e}")
        return False
    if not isinstance(payload, dict):
        return False
    try:
        schema = int(payload.get("schema", 0) or 0)
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:warmup_sentinel_is_fresh: {e}")
        schema = 0
    if schema < WARMUP_SENTINEL_SCHEMA:
        return False
    if not bool(payload.get("ok", False)):
        return False
    if bool(payload.get("warmup_fg", False)) != bool(warmup_fg):
        return False
    if bool(payload.get("warmup_ga", False)) != bool(warmup_ga):
        return False
    if str(payload.get("ga_warmup_profile", "") or "") != GA_WARMUP_PROFILE:
        return False
    return True


def system_timer_override_allowed() -> bool:
    # Wrapper kept for monkeypatch-based tests through gpu_executor imports.
    return bool(_system_timer_override_allowed_shared())


def acquire_windows_timer_period_1ms() -> bool:
    # Wrapper kept for monkeypatch-based tests through gpu_executor imports.
    return bool(_acquire_windows_timer_period_1ms_shared())


def release_windows_timer_period_1ms() -> None:
    # Wrapper kept for monkeypatch-based tests through gpu_executor imports.
    _release_windows_timer_period_1ms_shared()


def print_taichi_kernel_profiler(
    *,
    enabled: bool,
    import_module_fn: Callable[[str], Any] = importlib.import_module,
) -> bool:
    if not bool(enabled):
        return False
    try:
        ti = import_module_fn("taichi")
        ti.sync()
        ti.profiler.print_kernel_profiler_info()
        return True
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:print_taichi_kernel_profiler: {e}")
        return False


def report_gpu_profiler(
    *,
    enabled: bool,
    get_gpu_profiler_fn: Callable[[], Any] | None = None,
) -> bool:
    if not bool(enabled):
        return False
    try:
        if get_gpu_profiler_fn is None:
            from gear_optimizer.solver.gpu_profiler import get_gpu_profiler

            get_gpu_profiler_fn = get_gpu_profiler
        get_gpu_profiler_fn().report(verbose=True)
        return True
    except Exception as e:
        logger.debug(f"gpu_executor_lifecycle:report_gpu_profiler: {e}")
        return False
