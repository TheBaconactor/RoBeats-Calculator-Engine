import threading
from types import SimpleNamespace

from gear_optimizer.pipeline import solve as solve_module


def test_the_ga_and_the_fg_turn_are_one_executor_call(monkeypatch):
    from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
    from gear_optimizer.gpu import ga
    from gear_optimizer.pipeline import fg as fg_stage
    from gear_optimizer.solver import ga_selection

    ga_calls, selections, fg_calls = [], [], []

    def run_ga(inputs, seed, abort_requested):
        ga_calls.append((inputs, seed, abort_requested))
        return "table"

    def select(table, gear_rank, mini_sig, limit):
        selections.append((table, gear_rank, mini_sig, limit))
        return "selection"

    def fg_turn(song, selection):
        fg_calls.append((song, selection))
        return "ga result"

    monkeypatch.setattr(ga, "run_ga", run_ga)
    monkeypatch.setattr(ga_selection, "select_ga_loadouts", select)
    monkeypatch.setattr(fg_stage, "fg_turn", fg_turn)
    inputs = SimpleNamespace(fg_gear_name_rank=5, fg_mini_sig_id=6)
    song = SimpleNamespace(gpu_inputs=inputs, config=SimpleNamespace(ga_seed=7))
    abort = threading.Event()

    class _Executor:
        abort_requested = abort.is_set

        def call(self, fn, *args):
            return fn(*args)

    assert solve_module.run_ga(song, _Executor()) == "ga result"
    assert ga_calls == [(inputs, 7, abort.is_set)]
    assert selections == [("table", 5, 6, LOADOUTS_PER_SONG_LIMIT)]
    assert fg_calls == [(song, "selection")]


def test_only_an_executor_abort_counts_as_a_stop_abort():
    from gear_optimizer.gpu.executor import is_stop_abort_exception

    assert is_stop_abort_exception(RuntimeError("GpuExecutor aborted: hotkey stop")) is True
    assert is_stop_abort_exception(RuntimeError("other failure")) is False
