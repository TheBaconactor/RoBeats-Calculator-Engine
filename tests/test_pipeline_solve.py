import threading
from types import SimpleNamespace

import pytest

from gear_optimizer.domain.jobs import SharedRunContext, SongJob, task_queue_label, task_song_name
from gear_optimizer.domain.jobs import task_tuple_from_job_context
from gear_optimizer.pipeline import solve as solve_module
from gear_optimizer.solver import native_inflight_lifecycle


def _task(name: str) -> tuple:
    context = SharedRunContext(multi_start=3, curves={}, gears={}, minis={}, ga_depth=1, parallel_workers=1)
    return task_tuple_from_job_context(SongJob(file_path=f"{name}.txt", song_name=name, difficulty="Hard"), context)


def _song(task: tuple) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(song_name=task_song_name(task), task_key=task_queue_label(task), fp=""),
        runtime=SimpleNamespace(bundle=SimpleNamespace(bundle_parent_task=None), db=SimpleNamespace(record_info=None)),
    )


def _stages(monkeypatch, *, prepare=_song, run_ga=None, finish=None) -> None:
    monkeypatch.setattr(native_inflight_lifecycle, "prepare_native_song", prepare)
    monkeypatch.setattr(solve_module, "run_ga", run_ga or (lambda song, _ctx: f"ga {song.config.song_name}"))
    monkeypatch.setattr(solve_module, "finish_song", finish or (lambda song, _ga: song.config.task_key))


def _run(names, *, ctx=None, stop_requested=None) -> tuple[list, set]:
    posted: list = []
    completed: set[str] = {"Done Before"}
    solve_module.run_queue([_task(n) for n in names], ctx, post=posted.append, completed_songs=completed,
                           stop_requested=stop_requested)
    return posted, completed - {"Done Before"}


def _labels(posted: list) -> list:
    return [p if isinstance(p, str) else (p["_song_name"], p["_error"]) for p in posted]


def test_the_queue_is_solved_and_posted_in_order_and_each_task_completes(monkeypatch):
    _stages(monkeypatch)
    posted, completed = _run(["A", "Done Before", "B", "C"])
    assert posted == ["A", "B", "C"]
    assert completed == {"A", "B", "C"}


def test_failures_in_any_stage_are_posted_in_queue_order_and_the_queue_goes_on(monkeypatch):
    def prepare(task):
        if task_song_name(task) == "Prep Fails":
            raise RuntimeError("bad chart")
        return _song(task)

    def run_ga(song, _ctx):
        if song.config.song_name == "GA Fails":
            raise RuntimeError("gpu boom")
        return "ga"

    def finish(song, _ga):
        if song.config.song_name == "Finish Fails":
            raise RuntimeError("fg boom")
        return song.config.task_key

    _stages(monkeypatch, prepare=prepare, run_ga=run_ga, finish=finish)
    posted, completed = _run(["A", "Prep Fails", "GA Fails", "Finish Fails", "B"])
    assert _labels(posted) == ["A", ("Prep Fails", "bad chart"), ("GA Fails", "gpu boom"),
                               ("Finish Fails", "fg boom"), "B"]
    assert completed == {"A", "Prep Fails", "GA Fails", "Finish Fails", "B"}  # as in the in-flight pipeline


def test_while_a_ga_runs_the_previous_song_finishes_and_the_next_is_prepared(monkeypatch):
    a_finished, c_prepared = threading.Event(), threading.Event()

    def prepare(task):
        if task_song_name(task) == "C":
            c_prepared.set()
        return _song(task)

    def run_ga(song, _ctx):
        if song.config.song_name == "B" and not (a_finished.wait(5) and c_prepared.wait(5)):
            raise AssertionError("A was not finished or C not prepared while B's GA ran")
        return "ga"

    def finish(song, _ga):
        if song.config.song_name == "A":
            a_finished.set()
        return song.config.task_key

    _stages(monkeypatch, prepare=prepare, run_ga=run_ga, finish=finish)
    assert _run(["A", "B", "C"])[0] == ["A", "B", "C"]


def test_a_stop_request_leaves_the_rest_of_the_queue_pending(monkeypatch):
    stop = threading.Event()

    def finish(song, _ga):
        stop.set()
        return song.config.task_key

    _stages(monkeypatch, finish=finish)
    posted, completed = _run(["A", "B", "C"], ctx=SimpleNamespace(abort=lambda reason: None),
                             stop_requested=stop.is_set)
    assert posted[0] == "A" and set(posted) <= {"A", "B"} and completed == set(posted)


def test_a_stop_request_aborts_the_ga_in_progress_and_its_song_stays_pending(monkeypatch):
    stop, aborted = threading.Event(), threading.Event()

    def run_ga(song, _ctx):
        if song.config.song_name == "B":
            stop.set()
            if not aborted.wait(5):
                raise AssertionError("the stop request did not abort the GA")
            raise RuntimeError("GpuExecutor aborted: stop requested")
        return "ga"

    _stages(monkeypatch, run_ga=run_ga)
    posted, completed = _run(["A", "B", "C"], ctx=SimpleNamespace(abort=lambda reason: aborted.set()),
                             stop_requested=stop.is_set)
    assert posted == ["A"] and completed == {"A"}


def test_a_fatal_gpu_error_ends_the_run_after_the_songs_past_their_ga_finish(monkeypatch):
    from gear_optimizer.solver.gpu_service import GpuServiceTimeoutError

    def run_ga(song, _ctx):
        if song.config.song_name == "B":
            raise GpuServiceTimeoutError("GA watchdog timeout")
        return "ga"

    _stages(monkeypatch, run_ga=run_ga)
    posted: list = []
    with pytest.raises(GpuServiceTimeoutError):
        solve_module.run_queue([_task("A"), _task("B"), _task("C")], None, post=posted.append, completed_songs=set())
    assert posted == ["A"]


class _Executor:
    def __init__(self, *, ready: bool) -> None:
        self.ready, self.started, self.stopped, self.waited = ready, False, False, False
        self.last_init_error = None if ready else "no Vulkan device"

    def start(self, *, in_process: bool) -> None:
        self.started = in_process

    def wait_until_ready(self, timeout: float) -> bool:
        self.waited = True
        return self.ready

    def stop(self) -> None:
        self.stopped = True


def test_the_solve_context_starts_the_gpu_without_waiting_and_a_failed_init_is_fatal(monkeypatch):
    from gear_optimizer.solver import gpu_executor
    from gear_optimizer.solver.gpu_service import GpuFatalError

    executor = _Executor(ready=False)
    monkeypatch.setattr(gpu_executor, "get_gpu_executor", lambda: executor)
    ctx = solve_module.SolveContext()
    assert executor.started and not executor.waited  # the first songs prepare while Taichi initializes
    with pytest.raises(GpuFatalError, match="no Vulkan device"):
        ctx.gpu_client
    assert executor.stopped


def test_only_a_cancelled_future_or_an_executor_abort_counts_as_a_stop_abort():
    import concurrent.futures

    from gear_optimizer.solver.native_inflight_lifecycle import is_stop_abort_exception

    assert is_stop_abort_exception(concurrent.futures.CancelledError()) is True
    assert is_stop_abort_exception(RuntimeError("GpuExecutor aborted: hotkey stop")) is True
    assert is_stop_abort_exception(RuntimeError("other failure")) is False
