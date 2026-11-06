import threading
from types import SimpleNamespace

from gear_optimizer.pipeline import solve as solve_module


def test_the_ga_runs_as_one_executor_call_with_the_payload_as_the_ga_arguments(monkeypatch):
    import inspect

    from gear_optimizer.pipeline import fg as fg_stage
    from gear_optimizer.solver import genetic_pipeline

    bundle, ga_calls, fg_calls = object(), [], []

    def run_ga_runs(**kwargs):
        inspect.signature(real_run).bind(**kwargs)  # every payload key is a GA argument
        ga_calls.append(kwargs)
        return "runs payload"

    def fg_turn(runs_payload, **kwargs):
        fg_calls.append({"runs_payload": runs_payload, **kwargs})
        return runs_payload, "fg owner score"

    real_run = genetic_pipeline.run_gpu_native_ga_runs_payload_prebuilt
    monkeypatch.setattr(genetic_pipeline, "run_gpu_native_ga_runs_payload_prebuilt", run_ga_runs)
    monkeypatch.setattr(fg_stage, "fg_turn", fg_turn)
    inputs = SimpleNamespace(timed_song="timed song", curves="curves", item_stats=1, slot_start=2, slot_count=3,
                             base_fixed_stats_arr=4, num_runs=3, n_genomes=128, init_heuristic_topk=None,
                             init_heuristic_k=0, init_heuristic_copies=25, gens_per_run=42,
                             color_flags={"rush": True}, meta_primary_color='rush', fg_gear_name_rank=5,
                             fg_mini_sig_id=6, ftff_shortlist="shortlist")
    song = SimpleNamespace(gpu_inputs=inputs, config=SimpleNamespace(ga_seed=7),
                           runtime=SimpleNamespace(song_slot=0,
                                                   fg=SimpleNamespace(fg_response_scoring_bundle=bundle)))
    abort = threading.Event()

    class _Executor:
        abort_requested = abort.is_set

        def call(self, fn, *args):
            assert song.runtime.song_slot == solve_module._GA_SLOT
            return fn(*args)

    assert solve_module.run_ga(song, _Executor()) == ("runs payload", "fg owner score")
    assert song.runtime.song_slot == 0
    assert ga_calls[0]["song"] == "timed song" and ga_calls[0]["n_generations"] == 42 and ga_calls[0]["ga_seed"] == 7
    assert ga_calls[0]["abort_requested"] == abort.is_set
    assert ga_calls[0]["ftff_shortlist"] == "shortlist"
    assert fg_calls == [{"runs_payload": "runs payload", "fg_scoring_bundle": bundle, "song": "timed song",
                         "curves": "curves", "selected_color": "rush", "item_stats": 1, "slot_start": 2,
                         "slot_count": 3, "base_fixed_stats_arr": 4,
                         "beam_width": fg_stage.FG_SEARCH_BEAM_PER_GA_RUN * 3}]


def test_only_an_executor_abort_counts_as_a_stop_abort():
    from gear_optimizer.gpu.executor import is_stop_abort_exception

    assert is_stop_abort_exception(RuntimeError("GpuExecutor aborted: hotkey stop")) is True
    assert is_stop_abort_exception(RuntimeError("other failure")) is False
