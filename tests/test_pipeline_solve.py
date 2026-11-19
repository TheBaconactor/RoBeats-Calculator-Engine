import threading
from types import SimpleNamespace

import pytest

from gear_optimizer.pipeline import solve as solve_module
from gear_optimizer.pipeline.song import NativeSongRuntimeState


def _mock_song():
    inputs = SimpleNamespace(fg_gear_name_rank=5, fg_mini_sig_id=6)
    return SimpleNamespace(gpu_inputs=inputs, config=SimpleNamespace(ga_seed=7), runtime=NativeSongRuntimeState())


def test_the_ga_is_the_executor_call_and_the_fg_turn_runs_on_the_host(monkeypatch):
    from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
    from gear_optimizer.gpu import executor as executor_module
    from gear_optimizer.gpu import ga
    from gear_optimizer.pipeline import fg as fg_stage
    from gear_optimizer.solver import ga_selection

    ga_calls, selections, fg_calls, prep_calls, on_executor = [], [], [], [], threading.Event()
    abort = threading.Event()

    def run_ga(inputs, seed, abort_requested, *, on_submitted=None):
        assert on_executor.is_set()
        ga_calls.append((inputs, seed, abort_requested))
        if on_submitted is not None:
            on_submitted()
        return "table"

    def prepare_fg_static(song):
        prep_calls.append(song)
        song.runtime.fg.fg_response_scoring_bundle = "bundle"

    def select(table, gear_rank, mini_sig, limit):
        selections.append((table, gear_rank, mini_sig, limit))
        return "selection"

    def fg_turn(song, selection):
        assert not on_executor.is_set()
        assert song.runtime.fg.fg_response_scoring_bundle == "bundle"
        fg_calls.append((song, selection))
        return "ga result"

    monkeypatch.setattr(ga, "run_ga", run_ga)
    monkeypatch.setattr(fg_stage, "prepare_fg_static", prepare_fg_static)
    monkeypatch.setattr(ga_selection, "select_ga_loadouts", select)
    monkeypatch.setattr(fg_stage, "fg_turn", fg_turn)
    monkeypatch.setattr(executor_module, "get_gpu_executor", lambda: SimpleNamespace(abort_requested=abort.is_set))
    song = _mock_song()

    class _Executor:
        def call(self, fn, *args, on_submitted=None):
            on_executor.set()
            try:
                return fn(*args, on_submitted=on_submitted)
            finally:
                on_executor.clear()

    assert solve_module.run_ga(song, _Executor()) == "ga result"
    assert ga_calls == [(song.gpu_inputs, 7, abort.is_set)]
    assert prep_calls == [song]
    assert selections == [("table", 5, 6, LOADOUTS_PER_SONG_LIMIT)]
    assert fg_calls == [(song, "selection")]


def test_fg_bundle_prep_skips_reload_when_already_loaded_or_retried(monkeypatch):
    from gear_optimizer.pipeline import fg as fg_stage
    from gear_optimizer.solver import ga_selection

    prep_calls = []

    def prepare_fg_static(song):
        prep_calls.append(song)
        song.runtime.fg.fg_response_scoring_bundle = "bundle"

    monkeypatch.setattr(fg_stage, "prepare_fg_static", prepare_fg_static)
    monkeypatch.setattr(ga_selection, "select_ga_loadouts", lambda *_a: "selection")
    monkeypatch.setattr(fg_stage, "fg_turn", lambda song, sel: (song.runtime.fg.fg_response_scoring_bundle, sel))

    class _RetryingExecutor:
        def call(self, _fn, *_args, on_submitted=None):
            if on_submitted is not None:
                on_submitted()
                on_submitted()  # e.g. Vulkan semaphore retry after bundle already loaded
            return "table"

    song = _mock_song()
    assert solve_module.run_ga(song, _RetryingExecutor()) == ("bundle", "selection")
    assert len(prep_calls) == 1

    # Already-populated song passes no on_submitted callback.
    seen_cb = []

    class _CheckingExecutor:
        def call(self, _fn, *_args, on_submitted=None):
            seen_cb.append(on_submitted)
            return "table"

    assert solve_module.run_ga(song, _CheckingExecutor()) == ("bundle", "selection")
    assert seen_cb == [None] and len(prep_calls) == 1


def test_only_an_executor_abort_counts_as_a_stop_abort():
    from gear_optimizer.gpu.executor import is_stop_abort_exception

    assert is_stop_abort_exception(RuntimeError("GpuExecutor aborted: hotkey stop")) is True
    assert is_stop_abort_exception(RuntimeError("other failure")) is False
