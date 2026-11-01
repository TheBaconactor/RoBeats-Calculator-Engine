"""The run's worker pool (pipeline.workers.solve_queue) with stand-in workers: a task's song name scripts what its
worker does ("ok:<best after>", "fail", "crash", "memory:<best after>", "fatal", "wait")."""

import os

import pytest

from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.domain.jobs import SharedRunContext, SongTask
from gear_optimizer.pipeline import workers
from gear_optimizer.solver.gpu_executor import GpuFatalError


def _scripted_worker(worker, workers_total, pending, events, stop, memory_limit_bytes):
    """A worker main that plays each task's script instead of solving it."""
    while not stop.is_set():
        item = pending.get()
        if item is None:
            return
        index, (_file_path, script, *_rest) = item
        events.send(("start", index))
        kind, _, value = script.partition(":")
        if kind == "ok":
            events.send(("done", 0, int(value)))
        elif kind == "fail":
            events.send(("failed", "ValueError: bad chart", "Traceback"))
        elif kind == "crash":
            os._exit(1)
        elif kind == "memory":
            events.send(("done", 0, int(value)))
            raise SystemExit(workers._EXIT_FOR_MEMORY)
        elif kind == "fatal":
            events.send(("fatal", "GpuFatalError: device lost"))
            return
        else:  # "wait": until the run is stopped
            stop.wait(30)
            return


def _broken_worker(worker, workers_total, pending, events, stop, memory_limit_bytes):
    raise RuntimeError("cannot start")


def _run(monkeypatch, scripts, *, workers_count=2, stop_after=None, main=_scripted_worker):
    monkeypatch.setattr(workers, "_worker_main", main)
    context = SharedRunContext(multi_start=1, curves={}, gears={}, minis={}, ga_depth=1)
    tasks = [SongTask(f"{i}.txt", script, PRECISE, context) for i, script in enumerate(scripts)]
    done, failed = [], []

    def on_done(label, before, after):
        done.append((label, before, after))

    stored = workers.solve_queue(
        tasks, workers=workers_count, memory_limit_bytes=0,
        stop_requested=lambda: stop_after is not None and len(done) >= stop_after,
        on_done=on_done, on_failed=failed.append,
    )
    return stored, sorted(done), sorted(failed)


def test_every_task_is_solved_and_reported_with_its_boards_best(monkeypatch):
    stored, done, failed = _run(monkeypatch, ["ok:1", "ok:2", "ok:3", "ok:4", "ok:5"])
    assert stored == 5 and failed == []
    assert done == [(f"ok:{n} ({PRECISE})", 0, n) for n in range(1, 6)]


def test_a_failed_task_is_reported_and_the_queue_goes_on(monkeypatch):
    stored, done, failed = _run(monkeypatch, ["ok:1", "fail", "ok:2"])
    assert stored == 2 and failed == [f"fail ({PRECISE})"]


def test_a_worker_that_left_for_memory_is_replaced(monkeypatch):
    stored, done, failed = _run(monkeypatch, ["memory:1", "memory:2", "ok:3", "ok:4"], workers_count=1)
    assert stored == 4 and failed == []


def test_a_task_whose_worker_died_fails_and_a_new_worker_goes_on(monkeypatch):
    stored, done, failed = _run(monkeypatch, ["crash", "ok:1", "ok:2"], workers_count=1)
    assert stored == 2 and failed == [f"crash ({PRECISE})"]


def test_a_stop_request_takes_no_further_task(monkeypatch):
    stored, done, failed = _run(monkeypatch, ["ok:1", "wait", "ok:2", "ok:3"], workers_count=2, stop_after=1)
    assert stored < 4 and failed == []


def test_a_lost_gpu_stops_the_run(monkeypatch):
    with pytest.raises(GpuFatalError, match="device lost"):
        _run(monkeypatch, ["fatal", "wait", "ok:1"], workers_count=2)


def test_a_worker_that_cannot_start_ends_the_run(monkeypatch):
    with pytest.raises(RuntimeError, match="died outside a task"):
        _run(monkeypatch, ["ok:1"], workers_count=1, main=_broken_worker)
