"""A run's queue solved by worker processes around a few GPU processes.

Each worker owns a database connection and takes one task at a time: it solves the song and stores it
(pipeline.solve.solve_song, pipeline.storing.store_solve: the service worker's path), its GA on whichever of the run's
GPU processes takes it first. Each GPU process owns a Taichi runtime and runs one GA at a time: a runtime commits
~1.3 GiB up front on Windows, too much to hold one per worker. The parent hands out the tasks, counts progress from the
workers' events, replaces a worker that left to release memory or died in a task, and stops them all on a stop request
or a lost GPU. A task travels without its run context: each worker loads the run's catalog. Each worker reports on a
pipe of its own: a sent event is in the pipe even if the worker dies next.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import queue
import signal
import threading
import traceback
from collections.abc import Callable
from multiprocessing.connection import wait

from gear_optimizer.domain.jobs import SongTask
from gear_optimizer.gpu.executor import GpuFatalError, is_fatal_gpu_error

logger = logging.getLogger(__name__)

# How long the parent waits for an event or an exit before it looks at the stop request again.
_POLL_S = 0.2
# A worker's exit code when it left to release memory (0: the queue ended, a stop request or a lost GPU).
_EXIT_FOR_MEMORY = 3
# The run's GPU processes, each with its own Taichi runtime: one song's GA leaves the GPU mostly idle, so a few run side
# by side. 16 workers, 200 solves on an RX 7900 XTX: 19.9 s with 1, 14.2 s with 2, 12.5 s with 3, 12.2 s with 4.
_GPU_PROCESSES = 3
# How long a GPU process may take to finalize Taichi (persisting the offline kernel cache) once the run ends.
_GPU_EXIT_S = 60.0


def solve_queue(
    tasks: list[SongTask],
    *,
    workers: int,
    memory_limit_bytes: int,
    stop_requested: Callable[[], bool],
    on_done: Callable[[str, int, int], None],
    on_failed: Callable[[str], None],
) -> int:
    """Solve and store `tasks` on `workers` processes; the number of tasks stored.

    A worker's RSS stays under memory_limit_bytes / workers (0: no limit): past it the worker leaves after its task and
    a new one takes its place. on_done(label, the board's best before, after) and on_failed(label) report each task; a
    task whose worker died fails. A stop request takes no further task and aborts the GAs in progress. Raises
    GpuFatalError when the GPU is lost and RuntimeError when a worker died outside a task, after stopping the
    others."""
    ctx = multiprocessing.get_context("spawn")
    pending, stop = ctx.Queue(), ctx.Event()
    pending.cancel_join_thread()  # a stopped run leaves tasks unread; exiting must not wait for them
    for index, task in enumerate(tasks):
        pending.put((index, (task.file_path, task.song_name, task.mode, task.ga_seed, task.repeat_index,
                             task.repeat_total)))
    for _ in range(workers):
        pending.put(None)
    # The run's processes call no BLAS: one OpenBLAS thread, where one per core commits ~0.7 GiB per process on import.
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    gpu_calls, gpu_replies = ctx.Queue(), [ctx.Queue() for _ in range(workers)]
    gpus = [ctx.Process(target=_gpu_main, args=(gpu_calls, gpu_replies, stop), name=f"SolveGpu-{index}", daemon=True)
            for index in range(min(workers, _GPU_PROCESSES))]
    for gpu in gpus:
        gpu.start()
    running: dict[int, tuple[multiprocessing.process.BaseProcess, object]] = {}  # worker -> (process, its pipe)
    working: dict[int, int] = {}  # worker -> the task it is solving
    finished = stored = 0
    error: Exception | None = None

    def spawn(worker: int) -> None:
        reader, writer = ctx.Pipe(duplex=False)
        executor = _GpuClient(worker, gpu_calls, gpu_replies[worker], stop)
        process = ctx.Process(target=_worker_main, args=(worker, workers, pending, writer, stop,
                                                         memory_limit_bytes // workers, executor),
                              name=f"SolveWorker-{worker}", daemon=True)
        process.start()
        writer.close()  # the worker holds the only writer: its exit ends the pipe
        running[worker] = (process, reader)

    def receive(worker: int, event: tuple) -> None:
        nonlocal finished, stored, error
        kind = event[0]
        if kind == "start":
            working[worker] = event[1]
        elif kind == "done":
            on_done(tasks[working.pop(worker)].label, event[1], event[2])
            finished += 1
            stored += 1
        elif kind == "failed":
            label = tasks[working.pop(worker)].label
            logger.error("[Workers] %s failed: %s\n%s", label, event[1], event[2])
            on_failed(label)
            finished += 1
        else:  # "fatal": this worker's GPU is gone
            working.pop(worker, None)
            error = error or GpuFatalError(event[1])
            stop.set()

    def drain(worker: int, reader) -> None:
        try:
            while reader.poll():
                receive(worker, reader.recv())
        except (EOFError, BrokenPipeError):
            pass  # the worker exited (POSIX: EOF, Windows: a broken pipe) and its events are all read

    def exited(worker: int) -> None:
        nonlocal finished, error
        process, reader = running.pop(worker)
        drain(worker, reader)
        reader.close()
        process.join()
        if process.exitcode not in (0, _EXIT_FOR_MEMORY):
            if worker not in working:
                error = error or RuntimeError(f"solve worker {worker} died outside a task (exit code "
                                              f"{process.exitcode})")
                stop.set()
                return
            label = tasks[working.pop(worker)].label
            logger.error("[Workers] worker %d died solving %s (exit code %s)", worker, label, process.exitcode)
            on_failed(label)
            finished += 1
        elif process.exitcode == 0:
            return
        if not stop.is_set() and finished < len(tasks):
            spawn(worker)

    for worker in range(workers):
        spawn(worker)
    while running:
        if not stop.is_set() and stop_requested():
            stop.set()
        by_handle = {gpu.sentinel: (index, "gpu") for index, gpu in enumerate(gpus) if gpu.exitcode is None}
        for worker, (process, reader) in running.items():
            by_handle[reader] = (worker, "pipe")
            by_handle[process.sentinel] = (worker, "exit")
        ready = wait(list(by_handle), timeout=_POLL_S)
        for handle in ready:
            worker, kind = by_handle[handle]
            if kind == "pipe" and worker in running:
                drain(worker, handle)
            elif kind == "gpu" and not stop.is_set():
                error = error or GpuFatalError(f"GPU process {worker} exited (exit code {gpus[worker].exitcode})")
                stop.set()
        for handle in ready:
            worker, kind = by_handle[handle]
            if kind == "exit" and worker in running:
                exited(worker)
    stop.set()  # the GPU processes end with the workers
    for index, gpu in enumerate(gpus):
        gpu.join(_GPU_EXIT_S)
        if gpu.exitcode is None:
            logger.warning("[Workers] GPU process %d did not exit in %.0f s; terminating it", index, _GPU_EXIT_S)
            gpu.terminate()
    if error is not None:
        raise error
    return stored


def _worker_main(worker: int, workers: int, pending, events, stop, memory_limit_bytes: int,
                 executor: _GpuClient) -> None:
    """One worker: solve and store tasks until the queue ends, a stop request or a lost GPU (exit code 0), or until its
    memory limit (exit code _EXIT_FOR_MEMORY). `events` is the write end of its pipe to the parent; `executor` runs its
    GAs on the run's GPU processes."""
    from gear_optimizer import settings
    from gear_optimizer.core.cpu_affinity import pin_solve_worker
    from gear_optimizer.core.logging_config import configure_default_logging
    from gear_optimizer.core.memory import memory_release_requested, set_memory_watchdog_limit
    from gear_optimizer.core.output import suppress_stderr, suppress_stdout
    from gear_optimizer.domain.jobs import SharedRunContext
    from gear_optimizer.data.game_export import load_catalog
    from gear_optimizer.gamedata import stat_curves
    from gear_optimizer.pipeline.solve import solve_song
    from gear_optimizer.pipeline.storing import store_solve
    from gear_optimizer.gpu.executor import is_stop_abort_exception
    from gear_optimizer.store import schema

    # Ctrl+C reaches every process of the console: the parent turns it into the stop event the worker watches.
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if not settings.output_enabled():
        suppress_stdout(True)
        suppress_stderr(True)
    configure_default_logging()
    pin_solve_worker(worker, workers)
    run, paths = settings.read_run_settings(), settings.paths()
    catalog = load_catalog(paths.game_export)
    gears, minis = catalog.gears, catalog.minis
    context = SharedRunContext(multi_start=run.multi_start, curves=stat_curves(), gears=gears, minis=minis,
                               ga_depth=run.search_depth)
    set_memory_watchdog_limit(memory_limit_bytes)
    conn = schema.connect(paths.database, write=True)
    try:
        while not stop.is_set():
            item = pending.get()
            if item is None:
                return
            index, (file_path, song_name, mode, seed, repeat_index, repeat_total) = item
            events.send(("start", index))
            try:
                solved = solve_song(SongTask(file_path, song_name, mode, context, seed, repeat_index, repeat_total),
                                    executor)
                events.send(("done", *store_solve(conn, solved, gears, minis)))
            except GpuFatalError as exc:
                events.send(("fatal", f"{type(exc).__name__}: {exc}"))
                return
            except Exception as exc:
                if stop.is_set() and is_stop_abort_exception(exc):
                    return
                events.send(("failed", f"{type(exc).__name__}: {exc}", traceback.format_exc()))
            if memory_release_requested():
                raise SystemExit(_EXIT_FOR_MEMORY)
    finally:
        conn.close()
        executor.stop()


class _GpuClient:
    """A worker's GPU executor: call(fn, *args) runs fn(*args) on one of the run's GPU processes and returns its result.
    A stop request ends the wait with the executor's stop abort; the GPU process's error comes back as GpuFatalError
    when the GPU is lost, else as RuntimeError, with its traceback."""

    def __init__(self, worker: int, calls, replies, stop) -> None:
        self._worker, self._calls, self._replies, self._stop = worker, calls, replies, stop
        self._sent = 0

    def call(self, fn, *args):
        self._sent += 1
        tag = (os.getpid(), self._sent)
        self._calls.put((self._worker, tag, fn, args))
        while True:
            try:
                reply_tag, result, error = self._replies.get(timeout=_POLL_S)
            except queue.Empty:
                if self._stop.is_set():
                    raise RuntimeError("GpuExecutor aborted: stop requested") from None
                continue
            if reply_tag != tag:
                continue  # the answer to a call of the worker this one replaced
            if error is None:
                return result
            fatal, message, remote_traceback = error
            raise (GpuFatalError if fatal else RuntimeError)(f"{message}\nGPU process {remote_traceback}")

    def stop(self) -> None:
        """Exit without waiting to send a call no GPU process will read (they left with the run's stop)."""
        self._calls.cancel_join_thread()


def _gpu_main(calls, replies, stop) -> None:
    """One of the run's GPU processes: a GPU executor (its Taichi runtime) running the workers' calls it takes, one at a
    time, until the run stops. A call answers on its worker's reply queue: (tag, result, None) or (tag, None, (fatal,
    str(error), traceback))."""
    from gear_optimizer import settings
    from gear_optimizer.core.logging_config import configure_default_logging
    from gear_optimizer.core.output import suppress_stderr, suppress_stdout
    from gear_optimizer.gpu.executor import start_gpu_executor

    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if not settings.output_enabled():
        suppress_stdout(True)
        suppress_stderr(True)
    configure_default_logging()
    executor = start_gpu_executor()

    def abort_on_stop() -> None:
        stop.wait()
        executor.request_abort("stop requested")

    threading.Thread(target=abort_on_stop, name="StopWatch", daemon=True).start()
    try:
        _serve(calls, replies, stop, executor)
    finally:
        executor.stop()


def _serve(calls, replies, stop, executor) -> None:
    """Run each call on `executor` and answer it, until the stop event."""
    for reply in replies:
        reply.cancel_join_thread()  # the answer to a worker that died is never read; exiting must not wait for it
    while not stop.is_set():
        try:
            worker, tag, fn, args = calls.get(timeout=_POLL_S)
        except queue.Empty:
            continue
        try:
            answer = (tag, executor.call(fn, *args), None)
        except Exception as exc:
            answer = (tag, None, (is_fatal_gpu_error(exc), str(exc), traceback.format_exc()))
        replies[worker].put(answer)
