from __future__ import annotations

import configparser
import io
import json
import queue

from gear_optimizer import robeatsmeta_service as service
from gear_optimizer import service_worker as worker


def test_persistent_worker_reuses_one_process(monkeypatch):
    starts = 0
    worker = service._PersistentSolveWorker()

    class FakeStdin:
        def write(self, line: str) -> int:
            payload = json.loads(line)
            worker._responses.put({"ok": True, "loadouts": [{"mode": payload["mode"]}]})
            return len(line)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            return None

    class FakeProcess:
        stdin = FakeStdin()
        stdout = None
        stderr = None
        pid = 1

        @staticmethod
        def poll():
            return None

    def fake_start():
        nonlocal starts
        starts += 1
        worker._responses = queue.Queue()
        worker._proc = FakeProcess()
        return worker._proc

    monkeypatch.setattr(worker, "_start_locked", fake_start)

    assert worker.request({"mode": "default"}) == [{"mode": "default"}]
    assert worker.request({"mode": "zero_ms"}) == [{"mode": "zero_ms"}]
    assert starts == 1


def test_persistent_worker_stop_is_idempotent(monkeypatch):
    worker = service._PersistentSolveWorker()
    stopped: list[int] = []

    class FakeProcess:
        pid = 123
        stdin = None
        stdout = None
        stderr = None

        @staticmethod
        def poll():
            return None

        @staticmethod
        def wait(timeout=None):
            stopped.append(1)
            return 0

    worker._proc = FakeProcess()
    monkeypatch.setattr(service, "_kill_process_group", lambda _proc: stopped.append(1))

    worker.stop()
    worker.stop()

    assert stopped == [1, 1]


def test_service_worker_marks_daemon_before_native_startup(monkeypatch):
    import gear_optimizer.cli as cli
    import gear_optimizer.core.logging_config as logging_config

    events: list[str] = []
    monkeypatch.setattr(worker, "make_process_background_only", lambda: events.append("background"))
    monkeypatch.setattr(worker, "reassert_process_background_only", lambda: events.append("reassert"))
    monkeypatch.setattr(cli, "common_init", lambda: events.append("common_init"))
    monkeypatch.setattr(logging_config, "configure_default_logging", lambda: events.append("logging"))
    monkeypatch.setattr(cli, "_apply_taichi_shell_env", lambda: events.append("taichi_env"))
    monkeypatch.setattr(cli, "_apply_throughput_mode_env", lambda: events.append("throughput_env"))
    monkeypatch.setattr(cli, "_apply_service_mode_frontier_threads", lambda: events.append("frontier_threads"))

    class FakeSession:
        def __init__(self):
            events.append("session")

    monkeypatch.setattr(worker, "PersistentOptimizerSession", FakeSession)
    monkeypatch.setattr(worker.sys, "stdin", io.StringIO(""))

    assert worker.main() == 0
    assert events == [
        "background",
        "common_init",
        "logging",
        "taichi_env",
        "throughput_env",
        "frontier_threads",
        "reassert",
        "session",
    ]


def test_service_worker_reasserts_daemon_policy_after_native_prewarm(monkeypatch, tmp_path):
    events: list[str] = []

    class FakeApp:
        def _preload_ref_arrays(self, _stats_table):
            events.append("preload")
            return object()

        def _configure_execution_and_prewarm(self, _cfg):
            events.append("native_prewarm")

    class FakeRuntimeSettings:
        @classmethod
        def from_config(cls, _cfg):
            return object()

    session = object.__new__(worker.PersistentOptimizerSession)
    session._app = FakeApp()
    session._data_root = tmp_path / "Data"

    monkeypatch.setattr(worker, "AppRuntimeSettings", FakeRuntimeSettings)
    monkeypatch.setattr(worker, "load_paths_cache", lambda: {"Stats": str(tmp_path / "Stats.txt")})
    monkeypatch.setattr(worker, "read_table", lambda _path: {})
    monkeypatch.setattr(worker, "load_all_gears_list", lambda _paths: [{"Name": "gear"}])
    monkeypatch.setattr(worker, "load_all_minis_list", lambda _paths: [{"Name": "mini"}])
    monkeypatch.setattr(worker, "reassert_process_background_only", lambda: events.append("reassert"))

    session._initialize(configparser.ConfigParser())

    assert events == ["preload", "native_prewarm", "reassert"]
