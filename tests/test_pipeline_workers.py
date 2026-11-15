"""The run's worker pool (pipeline.workers.solve_queue) with stand-in workers: a task's song name scripts what its
worker does ("ok:<best after>", "gpu:<best after>", "fail", "crash", "memory:<best after>", "fatal", "wait"); and the
GPU process's protocol (_GpuClient, _serve) in one process."""

import multiprocessing
import os
import threading

import pytest

from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.domain.jobs import SharedRunContext, SongTask
from gear_optimizer.pipeline import workers
from gear_optimizer.gpu.executor import GpuFatalError, is_stop_abort_exception


def _scripted_worker(worker, workers_total, pending, events, stop, memory_limit_bytes, executor):
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
        elif kind == "gpu":  # the best after, squared on the GPU process
            events.send(("done", 0, executor.call(pow, int(value), 2)))
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


def _broken_worker(worker, workers_total, pending, events, stop, memory_limit_bytes, executor):
    raise RuntimeError("cannot start")


class _HostExecutor:
    """A GPU executor that runs each call on the calling thread."""

    def call(self, fn, *args):
        return fn(*args)

    def stop(self):
        pass


def _host_gpu(calls, replies, stop):
    """A GPU process main without Taichi."""
    workers._serve(calls, replies, stop, _HostExecutor())


def _dead_gpu(calls, replies, stop):
    os._exit(1)


def _run(monkeypatch, scripts, *, workers_count=2, stop_after=None, main=_scripted_worker, gpu=_host_gpu):
    monkeypatch.setattr(workers, "_worker_main", main)
    monkeypatch.setattr(workers, "_gpu_main", gpu)
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


def test_every_worker_reaches_the_gpu_processes(monkeypatch):
    stored, done, failed = _run(monkeypatch, ["gpu:1", "gpu:2", "gpu:3", "memory:4", "gpu:5"], workers_count=2)
    assert stored == 5 and failed == []
    assert sorted(after for _label, _before, after in done) == [1, 4, 4, 9, 25]


def test_a_gpu_process_that_exits_stops_the_run(monkeypatch):
    with pytest.raises(GpuFatalError, match=r"GPU process \d exited"):
        _run(monkeypatch, ["wait", "wait"], workers_count=2, gpu=_dead_gpu)


def _fail(message):
    raise ValueError(message)


def _lose_device():
    raise RuntimeError("Vulkan device lost")


@pytest.fixture
def gpu_process():
    """A GPU process loop on a thread, serving two workers' clients; yields (client 0, client 1, the reply queues,
    the stop event)."""
    ctx = multiprocessing.get_context("spawn")
    calls, replies, stop = ctx.Queue(), [ctx.Queue(), ctx.Queue()], ctx.Event()
    server = threading.Thread(target=workers._serve, args=(calls, replies, stop, _HostExecutor()), daemon=True)
    server.start()
    yield workers._GpuClient(0, calls, replies[0], stop), workers._GpuClient(1, calls, replies[1], stop), replies, stop
    stop.set()
    server.join(5)


def test_a_gpu_call_returns_its_result_to_the_worker_that_made_it(gpu_process):
    first, second, _replies, _stop = gpu_process
    assert first.call(pow, 3, 2) == 9
    assert second.call(pow, 2, 5) == 32
    assert first.call(divmod, 7, 2) == (3, 1)


def test_a_gpu_call_error_comes_back_with_the_gpu_process_traceback(gpu_process):
    first, _second, _replies, _stop = gpu_process
    with pytest.raises(RuntimeError, match=r"bad chart\nGPU process Traceback[\s\S]*ValueError: bad chart"):
        first.call(_fail, "bad chart")
    with pytest.raises(GpuFatalError, match="Vulkan device lost"):
        first.call(_lose_device)


def test_an_answer_left_for_a_replaced_worker_is_skipped(gpu_process):
    first, _second, replies, _stop = gpu_process
    replies[0].put(((0, 1), "the dead worker's table", None))
    assert first.call(pow, 4, 2) == 16


def test_a_stop_ends_the_wait_with_the_stop_abort(gpu_process):
    first, _second, _replies, stop = gpu_process
    stop.set()
    with pytest.raises(RuntimeError) as raised:
        first.call(threading.Event().wait, 1)
    assert is_stop_abort_exception(raised.value)
