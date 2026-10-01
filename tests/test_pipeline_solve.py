import threading
from types import SimpleNamespace

import pytest

from gear_optimizer.domain.jobs import SharedRunContext, SongJob, task_queue_label, task_song_name
from gear_optimizer.domain.jobs import task_tuple_from_job_context
from gear_optimizer.pipeline import solve as solve_module
from gear_optimizer.pipeline import prepare as prepare_module


def _task(name: str) -> tuple:
    context = SharedRunContext(multi_start=3, curves={}, gears={}, minis={}, ga_depth=1, parallel_workers=1)
    return task_tuple_from_job_context(SongJob(file_path=f"{name}.txt", song_name=name, difficulty="Hard"), context)


def _song(task: tuple) -> SimpleNamespace:
    return SimpleNamespace(
        config=SimpleNamespace(song_name=task_song_name(task), task_key=task_queue_label(task), fp="",
                               db_key=task_song_name(task)),
        runtime=SimpleNamespace(db=SimpleNamespace(record_info=None, db_best_score=100, db_best_fg_score=90,
                                                   db_baseline_valid=True)),
    )


def _stages(monkeypatch, *, prepare=_song, run_ga=None, finish=None) -> None:
    monkeypatch.setattr(prepare_module, "prepare_native_song", prepare)
    monkeypatch.setattr(solve_module, "run_ga", run_ga or (lambda song, _executor: f"ga {song.config.song_name}"))
    monkeypatch.setattr(solve_module, "finish_song", finish or (lambda song, _ga, _tracker: song.config.task_key))


def _run(names, *, executor=None, stop_requested=None) -> tuple[list, set]:
    posted: list = []
    completed: set[str] = {"Done Before"}
    solve_module.run_queue([_task(n) for n in names], executor, post=posted.append, completed_songs=completed,
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

    def run_ga(song, _executor):
        if song.config.song_name == "GA Fails":
            raise RuntimeError("gpu boom")
        return "ga"

    def finish(song, _ga, _tracker):
        if song.config.song_name == "Finish Fails":
            raise RuntimeError("fg boom")
        return song.config.task_key

    _stages(monkeypatch, prepare=prepare, run_ga=run_ga, finish=finish)
    posted, completed = _run(["A", "Prep Fails", "GA Fails", "Finish Fails", "B"])
    assert _labels(posted) == ["A", ("Prep Fails", "bad chart"), ("GA Fails", "gpu boom"),
                               ("Finish Fails", "fg boom"), "B"]
    assert completed == {"A", "Prep Fails", "GA Fails", "Finish Fails", "B"}


def test_each_song_is_judged_against_the_runs_bests_starting_from_the_stored_ones(monkeypatch):
    trackers = []

    def finish(song, _ga, tracker):
        trackers.append((tracker, tracker.snapshot(song.config.db_key)))
        tracker.update(song.config.db_key, best_score=150)  # as a record would: the next song must beat it
        return song.config.task_key

    _stages(monkeypatch, finish=finish)
    _run(["A", "A"])
    assert trackers[0][0] is trackers[1][0]
    assert [snapshot for _, snapshot in trackers] == [(100, 90, True), (150, 90, True)]


def test_while_a_ga_runs_the_previous_song_finishes_and_the_next_is_prepared(monkeypatch):
    a_finished, c_prepared = threading.Event(), threading.Event()

    def prepare(task):
        if task_song_name(task) == "C":
            c_prepared.set()
        return _song(task)

    def run_ga(song, _executor):
        if song.config.song_name == "B" and not (a_finished.wait(5) and c_prepared.wait(5)):
            raise AssertionError("A was not finished or C not prepared while B's GA ran")
        return "ga"

    def finish(song, _ga, _tracker):
        if song.config.song_name == "A":
            a_finished.set()
        return song.config.task_key

    _stages(monkeypatch, prepare=prepare, run_ga=run_ga, finish=finish)
    assert _run(["A", "B", "C"])[0] == ["A", "B", "C"]


def test_a_stop_request_leaves_the_rest_of_the_queue_pending(monkeypatch):
    stop = threading.Event()

    def finish(song, _ga, _tracker):
        stop.set()
        return song.config.task_key

    _stages(monkeypatch, finish=finish)
    posted, completed = _run(["A", "B", "C"], executor=SimpleNamespace(request_abort=lambda reason: None),
                             stop_requested=stop.is_set)
    assert posted[0] == "A" and set(posted) <= {"A", "B"} and completed == set(posted)


def test_a_stop_request_aborts_the_ga_in_progress_and_its_song_stays_pending(monkeypatch):
    stop, aborted = threading.Event(), threading.Event()

    def run_ga(song, _executor):
        if song.config.song_name == "B":
            stop.set()
            if not aborted.wait(5):
                raise AssertionError("the stop request did not abort the GA")
            raise RuntimeError("GpuExecutor aborted: stop requested")
        return "ga"

    _stages(monkeypatch, run_ga=run_ga)
    posted, completed = _run(["A", "B", "C"], executor=SimpleNamespace(request_abort=lambda reason: aborted.set()),
                             stop_requested=stop.is_set)
    assert posted == ["A"] and completed == {"A"}


def test_a_fatal_gpu_error_ends_the_run_after_the_songs_past_their_ga_finish(monkeypatch):
    from gear_optimizer.solver.gpu_executor import GpuServiceTimeoutError

    def run_ga(song, _executor):
        if song.config.song_name == "B":
            raise GpuServiceTimeoutError("GA watchdog timeout")
        return "ga"

    _stages(monkeypatch, run_ga=run_ga)
    posted: list = []
    with pytest.raises(GpuServiceTimeoutError):
        solve_module.run_queue([_task("A"), _task("B"), _task("C")], None, post=posted.append, completed_songs=set())
    assert posted == ["A"]


def test_the_ga_runs_as_one_executor_call_with_the_payload_as_the_ga_arguments(monkeypatch):
    import inspect

    from gear_optimizer.solver import genetic_pipeline

    bundle, ga_calls, fg_calls = object(), [], []

    def run_ga_runs(**kwargs):
        inspect.signature(real_run).bind(**kwargs)  # every payload key is a GA argument
        ga_calls.append(kwargs)
        return "runs payload"

    def score_fg(**kwargs):
        fg_calls.append(kwargs)
        return "fg owner score"

    real_run = genetic_pipeline.run_gpu_native_ga_runs_payload_prebuilt
    monkeypatch.setattr(genetic_pipeline, "run_gpu_native_ga_runs_payload_prebuilt", run_ga_runs)
    monkeypatch.setattr(genetic_pipeline, "score_fused_fg_from_selected_payload", score_fg)
    inputs = SimpleNamespace(timed_song="timed song", curves="curves", item_stats=1, slot_start=2, slot_count=3,
                             base_fixed_stats_arr=4, num_runs=3, n_genomes=128, init_heuristic_topk=None,
                             init_heuristic_k=0, init_heuristic_copies=25, gens_per_run=42,
                             color_flags={"rush": True}, cfg_data={"selected_color": "rush"}, fg_gear_name_rank=5,
                             fg_mini_sig_id=6)
    song = SimpleNamespace(gpu_inputs=inputs, config=SimpleNamespace(ga_seed=7),
                           runtime=SimpleNamespace(song_slot=0,
                                                   fg=SimpleNamespace(fg_response_scoring_bundle=bundle)))
    abort = threading.Event()

    class _Executor:
        abort_requested = abort.is_set

        def call(self, fn, *args):
            assert song.runtime.song_slot == solve_module._GA_SLOT
            return fn(*args)

    assert solve_module.run_ga(song, _Executor()) == {"runs_payload": "runs payload", "fg_owner_score": "fg owner score"}
    assert song.runtime.song_slot == 0
    assert ga_calls[0]["song"] == "timed song" and ga_calls[0]["n_generations"] == 42 and ga_calls[0]["ga_seed"] == 7
    assert ga_calls[0]["abort_requested"] == abort.is_set
    assert fg_calls == [{"runs_payload": "runs payload", "fg_scoring_bundle": bundle, "song": "timed song",
                         "curves": "curves", "cfg_data": {"selected_color": "rush"}}]


def test_only_an_executor_abort_counts_as_a_stop_abort():
    from gear_optimizer.solver.gpu_executor import is_stop_abort_exception

    assert is_stop_abort_exception(RuntimeError("GpuExecutor aborted: hotkey stop")) is True
    assert is_stop_abort_exception(RuntimeError("other failure")) is False
