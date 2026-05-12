import json
from pathlib import Path
import queue
from types import SimpleNamespace

import pytest

from gear_optimizer.solver.gpu_executor_lifecycle import (
    GA_WARMUP_PROFILE,
    WARMUP_SENTINEL_SCHEMA,
    apply_vulkan_visible_device,
    build_taichi_init_failure_report,
    build_warmup_sentinel_payload,
    configure_executor_server_state,
    executor_auto_stop_enabled,
    executor_visible_device_label,
    ga_light_warmup_enabled,
    load_executor_start_settings,
    load_executor_stop_profiler_settings,
    print_taichi_kernel_profiler,
    report_gpu_profiler,
    send_shutdown_request,
    signal_executor_ready,
    start_executor_ready_signal_thread,
    stop_executor_if_running,
    try_send_shutdown_request,
    warmup_sentinel_path,
    write_warmup_sentinel_payload,
)
from gear_optimizer.solver.gpu_executor_types import GpuRequestType


def _env_get(values):
    return lambda name, default=None: values.get(name, default)


def _env_flag(values):
    return lambda name: str(values.get(name, "")).lower() in {"1", "true", "yes", "on"}


def test_load_executor_start_settings_parses_live_trace_and_heartbeat(tmp_path):
    heartbeat_path = tmp_path / "heartbeat.json"
    values = {
        "GPU_EXECUTOR_IDLE_SAMPLE_THRESHOLD_MS": "2.5",
        "GPU_EXECUTOR_LIVE": "1",
        "GPU_EXECUTOR_LIVE_INTERVAL_SEC": "0.75",
        "GPU_EXECUTOR_TRACE_PATH": "trace.csv",
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

    assert settings.idle_sample_threshold_sec == 0.0025
    assert settings.live_enabled is True
    assert settings.live_interval_sec == 0.75
    assert settings.trace_path == "trace.csv"
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

    assert settings.idle_sample_threshold_sec == 0.001
    assert settings.live_enabled is False
    assert settings.live_interval_sec == 1.0
    assert settings.trace_path == "bad"
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
        env_config=SimpleNamespace(gpu_profiler=False),
    )
    enabled = load_executor_stop_profiler_settings(
        env_flag_fn=lambda _name: True,
        env_config=SimpleNamespace(gpu_profiler=True),
    )

    assert disabled.print_taichi_kernel_profiler is False
    assert disabled.report_gpu_profiler is False
    assert enabled.print_taichi_kernel_profiler is True
    assert enabled.report_gpu_profiler is True


def test_ga_light_warmup_enabled_requires_ga_warmup_and_phase_timing():
    assert ga_light_warmup_enabled(warmup_ga=True, env_flag_fn=lambda _name, _default: True)
    assert not ga_light_warmup_enabled(warmup_ga=False, env_flag_fn=lambda _name, _default: True)
    assert not ga_light_warmup_enabled(warmup_ga=True, env_flag_fn=lambda _name, _default: False)
    assert not ga_light_warmup_enabled(
        warmup_ga=True,
        env_flag_fn=lambda _name, _default: (_ for _ in ()).throw(TypeError("bad flag")),
    )


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


def test_apply_vulkan_visible_device_sets_taichi_device_env_vars():
    environ: dict[str, str] = {}

    assert apply_vulkan_visible_device(None, environ=environ) is None
    assert apply_vulkan_visible_device(" ", environ=environ) is None
    assert environ == {}

    assert apply_vulkan_visible_device(" 1 ", environ=environ) == "1"
    assert environ == {
        "TAICHI_VULKAN_VISIBLE_DEVICE": "1",
        "TI_VISIBLE_DEVICE": "1",
    }


def test_executor_visible_device_label_reports_env_or_default():
    assert executor_visible_device_label(env_get_fn=lambda _name, _default: "2") == "2"
    assert executor_visible_device_label(env_get_fn=lambda _name, _default: "") == "default"
    assert (
        executor_visible_device_label(
            env_get_fn=lambda _name, _default: (_ for _ in ()).throw(TypeError("bad env")),
        )
        == "default"
    )


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


def test_start_executor_ready_signal_thread_skips_without_ready_event():
    thread_calls = []

    assert (
        start_executor_ready_signal_thread(
            ready_event=None,
            ready_queue=None,
            label="Server",
            wait_fn=lambda: None,
            ready_state_fn=lambda: True,
            init_error_fn=lambda: None,
            thread_factory=lambda **kwargs: thread_calls.append(kwargs),
        )
        is False
    )
    assert thread_calls == []


def test_start_executor_ready_signal_thread_starts_named_daemon_bridge():
    calls: list[str] = []
    payloads: list[dict] = []
    threads: list[tuple[str, bool]] = []

    class _Event:
        @staticmethod
        def set():
            calls.append("set")

    class _Queue:
        @staticmethod
        def put(payload):
            payloads.append(payload)

    class _Thread:
        def __init__(self, *, target, name: str, daemon: bool) -> None:
            self._target = target
            threads.append((name, daemon))

        def start(self) -> None:
            calls.append("start")
            self._target()

    assert (
        start_executor_ready_signal_thread(
            ready_event=_Event(),
            ready_queue=_Queue(),
            label="FG",
            wait_fn=lambda: calls.append("wait"),
            ready_state_fn=lambda: True,
            init_error_fn=lambda: None,
            thread_factory=_Thread,
        )
        is True
    )

    assert threads == [("GpuExecutorReady[FG]", True)]
    assert calls == ["start", "wait", "set"]
    assert payloads == [{"ok": True, "error": None}]


def test_build_warmup_sentinel_payload_uses_lifecycle_schema_and_profile():
    payload = build_warmup_sentinel_payload(
        ok=True,
        error="",
        pid=123,
        warmed_at_ms=456,
        warmup_fg=True,
        warmup_ga=False,
    )

    assert payload == {
        "schema": WARMUP_SENTINEL_SCHEMA,
        "ok": True,
        "error": "",
        "pid": 123,
        "warmed_at": 456,
        "warmup_fg": True,
        "warmup_ga": False,
        "ga_warmup_profile": GA_WARMUP_PROFILE,
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


def test_report_gpu_profiler_runs_verbose_report_when_enabled():
    calls: list[bool] = []

    class _Profiler:
        @staticmethod
        def report(*, verbose: bool):
            calls.append(bool(verbose))

    assert report_gpu_profiler(enabled=False, get_gpu_profiler_fn=lambda: _Profiler()) is False
    assert calls == []
    assert report_gpu_profiler(enabled=True, get_gpu_profiler_fn=lambda: _Profiler()) is True
    assert calls == [True]


def test_report_gpu_profiler_reports_failure_as_false():
    assert (
        report_gpu_profiler(
            enabled=True,
            get_gpu_profiler_fn=lambda: (_ for _ in ()).throw(RuntimeError("no profiler")),
        )
        is False
    )
