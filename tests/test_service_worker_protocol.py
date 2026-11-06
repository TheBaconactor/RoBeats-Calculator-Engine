from __future__ import annotations

import io
import json
import subprocess
import sys
import textwrap

import pytest

from gear_optimizer import robeatsmeta_service as service
from gear_optimizer import service_worker as worker
from gear_optimizer.gpu.executor import GpuServiceTimeoutError

# The worker's side of the protocol, for the tests of the service's side.
_FAKE_WORKER = textwrap.dedent("""
    import json, sys, time
    for line in sys.stdin:
        request = json.loads(line)
        action = request.get("action")
        if action == "exit":
            raise SystemExit(1)
        if action == "hang":
            time.sleep(60)
        if action == "noise":
            print("not json", flush=True)
        if action == "lost-gpu":
            print(json.dumps({"ok": False, "error": "GPU gone", "restart": True}), flush=True)
        elif action == "fail":
            print(json.dumps({"ok": False, "error": "bad chart", "restart": False}), flush=True)
        else:
            print(json.dumps({"ok": True, "loadouts": [request]}), flush=True)
""")


@pytest.fixture
def solve_worker(tmp_path, monkeypatch):
    """A _SolveWorker on a fake worker process; `.starts` counts its processes."""
    real_popen = subprocess.Popen
    subject = service._SolveWorker(tmp_path / "worker")
    subject.starts = 0

    def popen(_command, **kwargs):
        subject.starts += 1
        subject.env = kwargs["env"]
        return real_popen([sys.executable, "-c", _FAKE_WORKER], **kwargs)

    monkeypatch.setattr(service.subprocess, "Popen", popen)
    yield subject
    subject.stop()


def test_one_process_answers_every_request(solve_worker):
    assert solve_worker.request({"n": 1}) == [{"n": 1}]
    assert solve_worker.request({"n": 2}) == [{"n": 2}]
    assert solve_worker.starts == 1


def test_a_failed_request_keeps_the_process(solve_worker):
    with pytest.raises(RuntimeError, match="bad chart"):
        solve_worker.request({"action": "fail"})
    assert solve_worker.request({"n": 1}) == [{"n": 1}]
    assert solve_worker.starts == 1


@pytest.mark.parametrize(("action", "message"), [("lost-gpu", "GPU gone"), ("exit", "exited")])
def test_a_lost_process_fails_its_request_and_the_next_one_starts_fresh(solve_worker, action, message):
    with pytest.raises(RuntimeError, match=message):
        solve_worker.request({"action": action})
    assert solve_worker.request({"n": 1}) == [{"n": 1}]
    assert solve_worker.starts == 2


def test_stray_output_is_not_an_answer(solve_worker):
    assert solve_worker.request({"action": "noise", "n": 1}) == [{"action": "noise", "n": 1}]


def test_a_solve_past_the_timeout_kills_the_process(solve_worker, monkeypatch):
    monkeypatch.setattr(service, "_SOLVE_TIMEOUT_S", 0.5)
    with pytest.raises(RuntimeError, match="timed out"):
        solve_worker.request({"action": "hang"})
    assert solve_worker.request({"n": 1}) == [{"n": 1}]
    assert solve_worker.starts == 2


def test_stop_twice_is_stop_once(solve_worker):
    solve_worker.request({"n": 1})
    solve_worker.stop()
    solve_worker.stop()
    assert solve_worker._proc is None


def test_each_worker_has_its_own_result_database_and_frontier_caches_when_asked(solve_worker, tmp_path, monkeypatch):
    monkeypatch.setenv("TIMELINE_FRONTIER_CACHE_DIR", "/shared/timeline")
    monkeypatch.setenv("FG_RESPONSE_FRONTIER_CACHE_DIR", "/shared/fg")
    solve_worker.request({"n": 1})
    assert solve_worker.env["EVOLUTION_DB_PATH"] == str(tmp_path / "worker" / "bin" / "service_result.db")
    assert solve_worker.env["TIMELINE_FRONTIER_CACHE_DIR"] == "/shared/timeline"

    uploaded = service._SolveWorker(tmp_path / "upload", frontier_root=tmp_path / "upload")
    uploaded.starts = 0
    env = uploaded._frontier_env()
    assert env == {
        "TIMELINE_FRONTIER_CACHE_DIR": str(tmp_path / "upload" / "timeline"),
        "FG_RESPONSE_FRONTIER_CACHE_DIR": str(tmp_path / "upload" / "fg"),
    }


def _quiet_startup(monkeypatch, events: list[str] | None = None) -> None:
    import gear_optimizer.cli as cli
    import gear_optimizer.core.logging_config as logging_config

    def note(name: str):
        return lambda: None if events is None else events.append(name)

    monkeypatch.setattr(worker, "make_process_background_only", note("background"))
    monkeypatch.setattr(worker, "reassert_process_background_only", note("reassert"))
    monkeypatch.setattr(logging_config, "configure_default_logging", note("logging"))
    monkeypatch.setattr(cli, "apply_service_frontier_threads", note("frontier_threads"))
    monkeypatch.setattr(sys, "__stdout__", sys.__stdout__)  # the worker keeps its own stdout from everything else


def test_the_worker_marks_itself_a_daemon_before_native_startup(monkeypatch):
    events: list[str] = []
    _quiet_startup(monkeypatch, events)
    monkeypatch.setattr(worker.sys, "stdin", io.StringIO(""))
    assert worker.main() == 0
    assert events == ["background", "logging", "frontier_threads", "reassert"]


@pytest.mark.parametrize(("request_fields", "multi_start"), [
    ({"reasoning": "default", "uploaded": False}, 20),  # the warm worker takes any reasoning level
    ({"reasoning": "default", "uploaded": True}, 5),
])
def test_the_executor_is_sized_for_the_requests_a_worker_can_get(monkeypatch, request_fields, multi_start):
    from gear_optimizer.gpu import executor as gpu_executor

    events: list[str] = []
    monkeypatch.setattr(gpu_executor, "start_gpu_executor", lambda runs: events.append(f"start:{runs}"))
    monkeypatch.setattr(worker, "reassert_process_background_only", lambda: events.append("reassert"))
    worker._started_executor(request_fields)
    assert events == [f"start:{multi_start}", "reassert"]


def _serve(monkeypatch, failures: list) -> tuple[list[dict], int]:
    """worker.main over one request per entry of `failures` (the exception that request's solve raises, or None).
    Returns the protocol answers and the number of solves."""
    _quiet_startup(monkeypatch)
    solves: list[dict] = []
    starts: list[dict] = []

    def solve(request, _executor):
        failure = failures[len(solves)]
        solves.append(request)
        if failure is not None:
            raise failure
        return [{"score": 1}]

    monkeypatch.setattr(worker, "solve", solve)
    monkeypatch.setattr(worker, "_started_executor", lambda request: starts.append(request) or object())
    line = json.dumps({"chartText": "c", "songName": "Song"}) + "\n"
    monkeypatch.setattr(worker.sys, "stdin", io.StringIO(line * len(failures)))
    out = io.StringIO()
    monkeypatch.setattr(worker.sys, "stdout", out)
    assert worker.main() == 0
    assert len(starts) == min(1, len(failures))
    return [json.loads(answer) for answer in out.getvalue().splitlines()], len(solves)


def test_a_failed_request_is_answered_and_the_worker_keeps_serving(monkeypatch):
    answers, solves = _serve(monkeypatch, [ValueError("bad chart"), None])
    assert answers == [
        {"ok": False, "error": "ValueError: bad chart", "restart": False},
        {"ok": True, "loadouts": [{"score": 1}]},
    ]
    assert solves == 2


@pytest.mark.parametrize("failure", [
    GpuServiceTimeoutError("GPU service request timed out"),
    RuntimeError("Vulkan: VK_ERROR_DEVICE_LOST (device lost)"),
])
def test_a_request_that_lost_the_gpu_ends_the_worker(monkeypatch, failure):
    answers, solves = _serve(monkeypatch, [failure, None])
    assert [answer["restart"] for answer in answers] == [True]
    assert solves == 1


def test_past_the_memory_guard_the_worker_exits_after_answering(monkeypatch):
    monkeypatch.setattr(worker, "memory_release_requested", lambda: True)
    answers, solves = _serve(monkeypatch, [None, None])
    assert answers == [{"ok": True, "loadouts": [{"score": 1}]}]
    assert solves == 1
