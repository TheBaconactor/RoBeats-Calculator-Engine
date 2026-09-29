import json
from pathlib import Path
import queue
from types import SimpleNamespace

import pytest

from gear_optimizer.solver.gpu_executor_lifecycle import (
    build_taichi_init_failure_report,
    executor_auto_stop_enabled,
    load_executor_start_settings,
    load_executor_stop_profiler_settings,
    print_taichi_kernel_profiler,
    send_shutdown_request,
    stop_executor_if_running,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequestType


def _env_get(values):
    return lambda name, default=None: values.get(name, default)


def _env_flag(values):
    return lambda name: str(values.get(name, "")).lower() in {"1", "true", "yes", "on"}


def test_load_executor_start_settings_parses_live_and_heartbeat(tmp_path):
    heartbeat_path = tmp_path / "heartbeat.json"
    values = {
        "GPU_EXECUTOR_LIVE": "1",
        "GPU_EXECUTOR_LIVE_INTERVAL_SEC": "0.75",
        "GPU_EXECUTOR_HEARTBEAT_PATH": str(heartbeat_path),
        "GPU_EXECUTOR_HEARTBEAT_INTERVAL_SEC": "0.05",
    }

    settings = load_executor_start_settings(
        in_process=False,
        env_get_fn=_env_get(values),
        env_flag_fn=_env_flag(values),
        os_name="nt",
        system_timer_override_allowed_fn=lambda: True,
        default_heartbeat_path_fn=lambda: Path("default.json"),
    )

    assert settings.live_enabled is True
    assert settings.live_interval_sec == 0.75
    assert settings.heartbeat_path == heartbeat_path
    assert settings.heartbeat_interval_sec == 0.1
    assert settings.enable_high_res_timer is False


def test_load_executor_start_settings_uses_defaults_for_invalid_values():
    settings = load_executor_start_settings(
        in_process=False,
        env_get_fn=lambda _name, _default=None: "bad",
        env_flag_fn=lambda _name: False,
        os_name="posix",
        system_timer_override_allowed_fn=lambda: False,
        default_heartbeat_path_fn=lambda: Path("default.json"),
    )

    assert settings.live_enabled is False
    assert settings.live_interval_sec == 1.0
    assert settings.heartbeat_path == Path("bad")
    assert settings.heartbeat_interval_sec == 2.0
    assert settings.enable_high_res_timer is False


def test_load_executor_start_settings_enables_high_res_timer_for_short_inproc_wait():
    values = {
        "GPU_EXECUTOR_BATCH_WAIT_MS": "",
        "GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS": "2",
    }

    settings = load_executor_start_settings(
        in_process=True,
        env_get_fn=_env_get(values),
        env_flag_fn=_env_flag(values),
        os_name="nt",
        env_config=SimpleNamespace(gpu_executor_batch_wait_ms=10),
        system_timer_override_allowed_fn=lambda: True,
        default_heartbeat_path_fn=lambda: Path("default.json"),
    )

    assert settings.enable_high_res_timer is True


def test_load_executor_start_settings_requires_timer_opt_in_and_windows():
    values = {
        "GPU_EXECUTOR_BATCH_WAIT_MS": "2",
        "GPU_EXECUTOR_INPROC_COALESCE_AFTER_FIRST_MS": "2",
    }

    no_opt_in = load_executor_start_settings(
        in_process=True,
        env_get_fn=_env_get(values),
        env_flag_fn=_env_flag(values),
        os_name="nt",
        system_timer_override_allowed_fn=lambda: False,
        default_heartbeat_path_fn=lambda: Path("default.json"),
    )
    non_windows = load_executor_start_settings(
        in_process=True,
        env_get_fn=_env_get(values),
        env_flag_fn=_env_flag(values),
        os_name="posix",
        system_timer_override_allowed_fn=lambda: True,
        default_heartbeat_path_fn=lambda: Path("default.json"),
    )

    assert no_opt_in.enable_high_res_timer is False
    assert non_windows.enable_high_res_timer is False


def test_load_executor_stop_profiler_settings_reads_reporter_flags():
    disabled = load_executor_stop_profiler_settings(
        env_flag_fn=lambda _name: False,
    )
    enabled = load_executor_stop_profiler_settings(
        env_flag_fn=lambda _name: True,
    )

    assert disabled.print_taichi_kernel_profiler is False
    assert enabled.print_taichi_kernel_profiler is True


def test_executor_auto_stop_enabled_reads_env_flag_safely():
    assert executor_auto_stop_enabled(env_flag_fn=lambda _name: True)
    assert not executor_auto_stop_enabled(env_flag_fn=lambda _name: False)
    assert not executor_auto_stop_enabled(
        env_flag_fn=lambda _name: (_ for _ in ()).throw(TypeError("bad flag")),
    )


def test_stop_executor_if_running_only_stops_live_executor():
    class _Executor:
        def __init__(self, *, running: bool) -> None:
            self.is_running = running
            self.stops = 0

        def stop(self) -> None:
            self.stops += 1

    stopped = _Executor(running=False)
    running = _Executor(running=True)

    assert stop_executor_if_running(None) is False
    assert stop_executor_if_running(stopped) is False
    assert stopped.stops == 0
    assert stop_executor_if_running(running) is True
    assert running.stops == 1


def test_send_shutdown_request_puts_canonical_shutdown_sentinel():
    requests = []

    class _Queue:
        @staticmethod
        def put(request):
            requests.append(request)

    send_shutdown_request(_Queue())

    assert len(requests) == 1
    request = requests[0]
    assert request.request_type is GpuRequestType.SHUTDOWN
    assert request.request_id == -1
    assert request.worker_id == -1
    assert request.payload == {}


def test_send_shutdown_request_propagates_put_failure():
    class _Queue:
        @staticmethod
        def put(_request):
            raise RuntimeError("queue failed")

    with pytest.raises(RuntimeError, match="queue failed"):
        send_shutdown_request(_Queue())


def test_build_taichi_init_failure_report_writes_trace_file(tmp_path):
    report = build_taichi_init_failure_report(
        RuntimeError("boom"),
        heartbeat_path=tmp_path / "gpu_executor_heartbeat.json",
        traceback_format_fn=lambda: "trace body",
    )

    assert report.trace_path == tmp_path / "gpu_executor_heartbeat_taichi_init_error.log"
    assert report.trace_path.read_text(encoding="utf-8") == "trace body"
    assert str(report.trace_path) in report.error
    assert report.error.startswith("RuntimeError: boom")


def test_build_taichi_init_failure_report_tolerates_traceback_format_failure(tmp_path):
    report = build_taichi_init_failure_report(
        RuntimeError("boom"),
        heartbeat_path=tmp_path / "gpu_executor_heartbeat.json",
        traceback_format_fn=lambda: (_ for _ in ()).throw(RuntimeError("format failed")),
    )

    assert report.trace_path == tmp_path / "gpu_executor_heartbeat_taichi_init_error.log"
    assert report.trace_path.read_text(encoding="utf-8") == ""


def test_print_taichi_kernel_profiler_runs_sync_and_print_when_enabled():
    calls: list[str] = []

    class _Profiler:
        @staticmethod
        def print_kernel_profiler_info():
            calls.append("print")

    class _Taichi:
        profiler = _Profiler()

        @staticmethod
        def sync():
            calls.append("sync")

    assert print_taichi_kernel_profiler(enabled=False, import_module_fn=lambda _name: _Taichi) is False
    assert calls == []
    assert print_taichi_kernel_profiler(enabled=True, import_module_fn=lambda _name: _Taichi) is True
    assert calls == ["sync", "print"]


def test_print_taichi_kernel_profiler_reports_failure_as_false():
    assert (
        print_taichi_kernel_profiler(
            enabled=True,
            import_module_fn=lambda _name: (_ for _ in ()).throw(RuntimeError("no taichi")),
        )
        is False
    )
