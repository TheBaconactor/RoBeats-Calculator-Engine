import json
from pathlib import Path
import queue
from types import SimpleNamespace

import pytest

from gear_optimizer.solver.gpu_executor_lifecycle import (
    WARMUP_SENTINEL_SCHEMA,
    build_taichi_init_failure_report,
    build_warmup_sentinel_payload,
    configure_executor_server_state,
    executor_auto_stop_enabled,
    load_executor_start_settings,
    load_executor_stop_profiler_settings,
    print_taichi_kernel_profiler,
    send_shutdown_request,
    signal_executor_ready,
    stop_executor_if_running,
    try_send_shutdown_request,
    warmup_sentinel_is_fresh,
    warmup_sentinel_path,
    write_warmup_sentinel_payload,
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


def test_try_send_shutdown_request_reports_put_failure_as_false():
    class _Queue:
        @staticmethod
        def put(_request):
            raise RuntimeError("queue failed")

    assert try_send_shutdown_request(_Queue()) is False


def test_configure_executor_server_state_wires_server_fields_and_clears_ready():
    request_queue = queue.Queue()
    response_queue = object()

    class _ReadyEvent:
        def __init__(self) -> None:
            self.cleared = False

        def clear(self) -> None:
            self.cleared = True

    ready_event = _ReadyEvent()
    executor = SimpleNamespace(_ready_event=ready_event)

    assert (
        configure_executor_server_state(
            executor,
            request_queue=request_queue,
            response_queues={7: response_queue},
        )
        is True
    )

    assert executor._request_queue is request_queue
    assert executor._response_queues == {7: response_queue}
    assert executor._in_process_queues is True
    assert executor._running is True
    assert executor._taichi_ready is False
    assert executor._last_init_error is None
    assert ready_event.cleared is True


def test_configure_executor_server_state_tolerates_ready_event_clear_failure():
    class _ReadyEvent:
        @staticmethod
        def clear() -> None:
            raise RuntimeError("clear failed")

    request_queue = object()
    executor = SimpleNamespace(_ready_event=_ReadyEvent())

    assert (
        configure_executor_server_state(
            executor,
            request_queue=request_queue,
            response_queues=None,
        )
        is False
    )

    assert executor._request_queue is request_queue
    assert executor._response_queues == {}
    assert executor._in_process_queues is False
    assert executor._running is True
    assert executor._taichi_ready is False
    assert executor._last_init_error is None


def test_signal_executor_ready_sets_event_and_puts_status():
    calls: list[str] = []
    payloads: list[dict] = []

    class _Event:
        @staticmethod
        def set():
            calls.append("set")

    class _Queue:
        @staticmethod
        def put(payload):
            payloads.append(payload)

    signal_executor_ready(
        ready_event=_Event(),
        ready_queue=_Queue(),
        wait_fn=lambda: calls.append("wait"),
        ready_state_fn=lambda: True,
        init_error_fn=lambda: None,
    )

    assert calls == ["wait", "set"]
    assert payloads == [{"ok": True, "error": None}]


def test_signal_executor_ready_still_signals_after_wait_or_queue_failures():
    calls: list[str] = []

    class _Event:
        @staticmethod
        def set():
            calls.append("set")

    class _Queue:
        @staticmethod
        def put(_payload):
            raise RuntimeError("queue failed")

    with pytest.raises(RuntimeError, match="wait failed"):
        signal_executor_ready(
            ready_event=_Event(),
            ready_queue=_Queue(),
            wait_fn=lambda: (_ for _ in ()).throw(RuntimeError("wait failed")),
            ready_state_fn=lambda: False,
            init_error_fn=lambda: "boom",
        )

    assert calls == ["set"]


def test_build_warmup_sentinel_payload_uses_lifecycle_schema():
    payload = build_warmup_sentinel_payload(
        ok=True,
        error="",
        pid=123,
        warmed_at_ms=456,
        warmup_fg=True,
        warmup_ga=True,
    )

    assert payload == {
        "schema": WARMUP_SENTINEL_SCHEMA,
        "ok": True,
        "error": "",
        "pid": 123,
        "warmed_at": 456,
        "warmup_fg": True,
        "warmup_ga": True,
    }


def test_warmup_sentinel_path_returns_cache_sentinel_or_none():
    assert warmup_sentinel_path("") is None
    assert warmup_sentinel_path(" ") is None
    assert warmup_sentinel_path("cache") == Path("cache") / "metafinder_warmup_done.json"


def test_write_warmup_sentinel_payload_writes_atomic_json(tmp_path):
    sentinel = tmp_path / "cache" / "metafinder_warmup_done.json"
    replacements: list[tuple[str, str]] = []

    def _replace(src, dst):
        replacements.append((Path(src).name, Path(dst).name))
        Path(src).replace(dst)

    assert write_warmup_sentinel_payload(
        sentinel_path=sentinel,
        payload={"b": 2, "a": 1},
        replace_fn=_replace,
    )

    assert replacements == [("metafinder_warmup_done.tmp", "metafinder_warmup_done.json")]
    assert json.loads(sentinel.read_text(encoding="utf-8")) == {"a": 1, "b": 2}


def test_write_warmup_sentinel_payload_reports_invalid_payload_as_false(tmp_path):
    assert not write_warmup_sentinel_payload(
        sentinel_path=tmp_path / "metafinder_warmup_done.json",
        payload={"bad": object()},
    )


def test_warmup_sentinel_requires_ga_warmup_match(tmp_path):
    sentinel = tmp_path / "metafinder_warmup_done.json"
    sentinel.write_text(
        json.dumps(
            {
                "schema": WARMUP_SENTINEL_SCHEMA,
                "ok": True,
                "error": "",
                "pid": 123,
                "warmed_at": 456,
                "warmup_fg": True,
                "warmup_ga": False,
            }
        ),
        encoding="utf-8",
    )

    assert not warmup_sentinel_is_fresh(
        sentinel_path=sentinel,
        warmup_fg=True,
        warmup_ga=True,
    )


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
