import sys
import types

import numpy as np


def test_batch_evaluate_worker_mode_forwards_song_slot(monkeypatch):
    from gear_optimizer.solver.scoring import genome_evaluation as ge

    fake_fever = types.ModuleType("gear_optimizer.solver.fever_timeline")
    fake_fever.get_song_timeline_grid = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.fever_timeline", fake_fever)

    fake_solver = types.ModuleType("gear_optimizer.solver.taichi_gem.api")
    fake_solver.solve_genomes_from_registry = lambda *_args, **_kwargs: []
    fake_solver.ga_upload_item_stats = lambda *_args, **_kwargs: None
    fake_solver.ga_upload_base_fixed_stats = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api", fake_solver)

    def _fake_prepare(population, base_stats_fixed, cfg_data, calc_song, ref_arrays, **_kwargs):
        plan = ge.GpuBatchEvalPlan(
            population=list(population),
            base_stats_fixed=dict(base_stats_fixed),
            cfg_data={"use_gpu": True},
            calc_song=dict(calc_song),
            ref_arrays=dict(ref_arrays),
            genome_key_fn=None,
            evaluation_cache=None,
            use_cache=False,
            cached_results={},
            uncached_genomes=[[]],
            uncached_indices=[0],
            all_stats=[{}],
            sel_color="Beat",
            config_sig=(),
            sig_to_result={},
            unique_stats=[(("sig",), {})],
            unique_members=[[0]],
            genome_stats_list=[{"base_pp": 0}],
            flags={},
        )
        return plan, None

    class _Registry:
        def encode_population(self, _population):
            return np.zeros((1, 9), dtype=np.int32)

        def to_gpu_arrays(self):
            return {
                "item_stats": np.zeros((1, 10), dtype=np.int32),
                "slot_start": np.zeros((9,), dtype=np.int32),
                "slot_count": np.zeros((9,), dtype=np.int32),
            }

    captured = {"song_slot": None}

    def _fake_dispatch(request, *, gpu_client=None):
        del gpu_client
        captured["song_slot"] = int(request.song_slot)
        return [(1, 0, 0, 0, 0, 0, 0)]

    def _fake_finalize(_plan, gpu_results):
        return list(gpu_results or [])

    monkeypatch.setattr(ge, "prepare_gpu_batch_eval_plan", _fake_prepare)
    monkeypatch.setattr(ge, "finalize_gpu_batch_eval_plan", _fake_finalize)
    monkeypatch.setattr(ge, "dispatch_registry_solve", _fake_dispatch)

    from gear_optimizer.solver import gpu_executor as gx

    monkeypatch.setattr(gx, "is_gpu_worker_mode", lambda: True)

    out = ge.batch_evaluate_genomes(
        population=[{}],
        base_stats_fixed={},
        cfg_data={"use_gpu": True},
        calc_song={"_gpu_song_slot": 7},
        ref_arrays={},
        genome_key_fn=None,
        evaluation_cache=None,
        registry=_Registry(),
    )

    assert captured["song_slot"] == 7
    assert out == [(1, 0, 0, 0, 0, 0, 0)]
