from __future__ import annotations

import io
import json
import queue

import pytest

from gear_optimizer import robeatsmeta_service as service
from gear_optimizer import service_worker as worker
from gear_optimizer.solver.gpu_executor import GpuServiceTimeoutError


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
        stdout = io.StringIO()
        stderr = io.StringIO()
        pid = 1

        @staticmethod
        def poll():
            return None

    def fake_start():
        nonlocal starts
        starts += 1
        worker._responses = queue.Queue()
        worker._gear_source = service.GEAR_DIR
        worker._proc = FakeProcess()
        return worker._proc

    monkeypatch.setattr(worker, "_start_locked", fake_start)

    assert worker.request({"mode": "default"}) == [{"mode": "default"}]
    assert worker.request({"mode": "non-precise"}) == [{"mode": "non-precise"}]
    assert starts == 1


def _fake_persistent_worker(monkeypatch):
    starts: list[int] = []
    killed: list[int] = []
    solver = service._PersistentSolveWorker()

    class FakeStdin:
        def write(self, line: str) -> int:
            solver._responses.put({"ok": True, "loadouts": [json.loads(line)]})
            return len(line)

        def flush(self) -> None:
            return None

        def close(self) -> None:
            return None

    class FakeProcess:
        stdin = FakeStdin()
        stdout = io.StringIO()
        stderr = io.StringIO()
        pid = 1

        @staticmethod
        def poll():
            return None

        @staticmethod
        def wait(timeout=None):
            return 0

    def fake_start():
        starts.append(1)
        solver._responses = queue.Queue()
        solver._gear_source = service.GEAR_DIR
        solver._proc = FakeProcess()
        return solver._proc

    monkeypatch.setattr(solver, "_start_locked", fake_start)
    monkeypatch.setattr(service, "_kill_process_group", lambda proc: killed.append(proc.pid))
    return solver, starts, killed


def test_idle_reap_stops_worker_and_next_request_respawns(monkeypatch):
    solver, starts, killed = _fake_persistent_worker(monkeypatch)

    assert solver.request({"mode": "default"}) == [{"mode": "default"}]
    solver._idle_since -= service._PERSISTENT_WORKER_IDLE_EXIT_S + 1

    assert solver.reap_if_idle() is True
    assert solver._proc is None
    assert killed == [1]
    assert solver.request({"mode": "non-precise"}) == [{"mode": "non-precise"}]
    assert len(starts) == 2


def test_idle_reap_skips_when_recent_or_request_in_flight(monkeypatch):
    solver, starts, killed = _fake_persistent_worker(monkeypatch)
    solver.request({"mode": "default"})
    proc = solver._proc

    assert solver.reap_if_idle() is False  # it just served a request

    solver._idle_since -= service._PERSISTENT_WORKER_IDLE_EXIT_S + 1
    with solver._lock:  # a solve in flight holds the lock for its whole duration
        assert solver.reap_if_idle() is False

    assert solver._proc is proc
    assert killed == []
    assert len(starts) == 1


def test_persistent_worker_stop_is_idempotent(monkeypatch):
    worker = service._PersistentSolveWorker()
    stopped: list[int] = []

    class FakeProcess:
        pid = 123
        stdin = io.StringIO()
        stdout = io.StringIO()
        stderr = io.StringIO()

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
        "frontier_threads",
        "reassert",
        "session",
    ]


def test_service_worker_reasserts_daemon_policy_after_native_prewarm(monkeypatch, tmp_path):
    events: list[str] = []

    class FakeApp:
        def _configure_execution_and_prewarm(self, multi_start):
            events.append(f"native_prewarm:{multi_start}")

    session = object.__new__(worker.PersistentOptimizerSession)
    session._app = FakeApp()

    monkeypatch.setattr(worker, "stat_curves", lambda: events.append("load curves") or object())
    monkeypatch.setattr(worker, "load_gears", lambda _path: {})
    monkeypatch.setattr(worker, "load_minis", lambda _path: {})
    monkeypatch.setattr(worker, "reassert_process_background_only", lambda: events.append("reassert"))

    session._initialize()

    assert events == ["load curves", "native_prewarm:20", "reassert"]


def test_service_worker_passes_the_promotion_target_to_the_solve(monkeypatch):
    import gear_optimizer.cli as cli
    import gear_optimizer.core.logging_config as logging_config

    for name in ("common_init", "_apply_taichi_shell_env", "_apply_service_mode_frontier_threads"):
        monkeypatch.setattr(cli, name, lambda: None)
    monkeypatch.setattr(logging_config, "configure_default_logging", lambda: None)
    monkeypatch.setattr(worker, "make_process_background_only", lambda: None)
    monkeypatch.setattr(worker, "reassert_process_background_only", lambda: None)
    calls = []

    class FakeSession:
        def solve(self, **kwargs):
            calls.append(kwargs)
            return [{"score": 1}]

    monkeypatch.setattr(worker, "PersistentOptimizerSession", FakeSession)
    lines = [
        {"chartText": "c", "songName": "Song", "promoteTo": "/catalog/evolution.db"},
        {"chartText": "c", "songName": "Song"},
    ]
    monkeypatch.setattr(worker.sys, "stdin", io.StringIO("".join(json.dumps(x) + "\n" for x in lines)))
    monkeypatch.setattr(worker.sys, "stdout", io.StringIO())

    assert worker.main() == 0
    assert [c["promote_to"] for c in calls] == ["/catalog/evolution.db", None]


def _serve(monkeypatch, failures: list) -> tuple[list[dict], int]:
    """worker.main over one request per entry of `failures` (the exception that request's solve raises, or None).
    Returns the protocol responses and the number of solves."""
    import gear_optimizer.cli as cli
    import gear_optimizer.core.logging_config as logging_config

    for name in ("common_init", "_apply_taichi_shell_env", "_apply_service_mode_frontier_threads"):
        monkeypatch.setattr(cli, name, lambda: None)
    monkeypatch.setattr(logging_config, "configure_default_logging", lambda: None)
    monkeypatch.setattr(worker, "make_process_background_only", lambda: None)
    monkeypatch.setattr(worker, "reassert_process_background_only", lambda: None)
    solves: list[dict] = []

    class FakeSession:
        def solve(self, **kwargs):
            failure = failures[len(solves)]
            solves.append(kwargs)
            if failure is not None:
                raise failure
            return [{"score": 1}]

    monkeypatch.setattr(worker, "PersistentOptimizerSession", FakeSession)
    request = json.dumps({"chartText": "c", "songName": "Song"}) + "\n"
    monkeypatch.setattr(worker.sys, "stdin", io.StringIO(request * len(failures)))
    out = io.StringIO()
    monkeypatch.setattr(worker.sys, "stdout", out)
    assert worker.main() == 0
    return [json.loads(line) for line in out.getvalue().splitlines()], len(solves)


def test_a_failed_request_is_answered_and_the_worker_keeps_serving(monkeypatch):
    responses, solves = _serve(monkeypatch, [ValueError("bad chart"), None])
    assert responses == [
        {"ok": False, "error": "ValueError: bad chart", "restart": False},
        {"ok": True, "loadouts": [{"score": 1}]},
    ]
    assert solves == 2


@pytest.mark.parametrize("failure", [
    GpuServiceTimeoutError("GPU service request timed out"),
    RuntimeError("Vulkan: VK_ERROR_DEVICE_LOST (device lost)"),
])
def test_a_request_that_lost_the_gpu_ends_the_worker(monkeypatch, failure):
    responses, solves = _serve(monkeypatch, [failure, None])
    assert [r["restart"] for r in responses] == [True]
    assert solves == 1


def test_past_the_memory_guard_the_worker_exits_after_answering(monkeypatch):
    monkeypatch.setattr(worker, "memory_release_requested", lambda: True)
    responses, solves = _serve(monkeypatch, [None, None])
    assert responses == [{"ok": True, "loadouts": [{"score": 1}]}]
    assert solves == 1
