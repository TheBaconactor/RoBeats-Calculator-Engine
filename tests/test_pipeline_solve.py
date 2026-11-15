import threading
from types import SimpleNamespace

from gear_optimizer.pipeline import solve as solve_module


def test_the_ga_is_the_executor_call_and_the_fg_turn_runs_on_the_host(monkeypatch):
    from gear_optimizer.domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
    from gear_optimizer.gpu import executor as executor_module
    from gear_optimizer.gpu import ga
    from gear_optimizer.pipeline import fg as fg_stage
    from gear_optimizer.solver import ga_selection

    ga_calls, selections, fg_calls, on_executor = [], [], [], threading.Event()
    abort = threading.Event()

    def run_ga(inputs, seed, abort_requested):
        assert on_executor.is_set()
        ga_calls.append((inputs, seed, abort_requested))
        return "table"

    def select(table, gear_rank, mini_sig, limit):
        selections.append((table, gear_rank, mini_sig, limit))
        return "selection"

    def fg_turn(song, selection):
        assert not on_executor.is_set()
        fg_calls.append((song, selection))
        return "ga result"

    monkeypatch.setattr(ga, "run_ga", run_ga)
    monkeypatch.setattr(ga_selection, "select_ga_loadouts", select)
    monkeypatch.setattr(fg_stage, "fg_turn", fg_turn)
    monkeypatch.setattr(executor_module, "get_gpu_executor", lambda: SimpleNamespace(abort_requested=abort.is_set))
    inputs = SimpleNamespace(fg_gear_name_rank=5, fg_mini_sig_id=6)
    song = SimpleNamespace(gpu_inputs=inputs, config=SimpleNamespace(ga_seed=7))

    class _Executor:
        def call(self, fn, *args):
            on_executor.set()
            try:
                return fn(*args)
            finally:
                on_executor.clear()

    assert solve_module.run_ga(song, _Executor()) == "ga result"
    assert ga_calls == [(inputs, 7, abort.is_set)]
    assert selections == [("table", 5, 6, LOADOUTS_PER_SONG_LIMIT)]
    assert fg_calls == [(song, "selection")]


def test_only_an_executor_abort_counts_as_a_stop_abort():
    from gear_optimizer.gpu.executor import is_stop_abort_exception

    assert is_stop_abort_exception(RuntimeError("GpuExecutor aborted: hotkey stop")) is True
    assert is_stop_abort_exception(RuntimeError("other failure")) is False
