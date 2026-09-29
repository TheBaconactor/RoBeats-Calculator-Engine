from pathlib import Path

import pytest

from gear_optimizer.solver.gpu_executor_lifecycle import (
    build_taichi_init_failure_report,
    load_executor_start_settings,
    send_shutdown_request,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequestType


def test_load_executor_start_settings_uses_fixed_heartbeat():
    settings = load_executor_start_settings(
        in_process=False,
        os_name="posix",
        default_heartbeat_path_fn=lambda: Path("default.json"),
    )

    assert settings.heartbeat_path == Path("default.json")
    assert settings.heartbeat_interval_sec == 2.0
    assert settings.enable_high_res_timer is False


def test_load_executor_start_settings_enables_high_res_timer_for_inproc_windows_only():
    def _timer(*, in_process: bool, os_name: str) -> bool:
        return load_executor_start_settings(
            in_process=in_process,
            os_name=os_name,
            default_heartbeat_path_fn=lambda: Path("default.json"),
        ).enable_high_res_timer

    assert _timer(in_process=True, os_name="nt") is True
    assert _timer(in_process=False, os_name="nt") is False
    assert _timer(in_process=True, os_name="posix") is False


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
