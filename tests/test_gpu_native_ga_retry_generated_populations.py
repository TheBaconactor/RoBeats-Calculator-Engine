import sys
import types

import numpy as np


def test_run_gpu_native_ga_retry_with_generated_initial_populations(monkeypatch):
    from gear_optimizer.solver import genetic

    class _FakeGpuApi:
        def __init__(self) -> None:
            self.generate_calls = 0
            self.upload_calls = 0
            self.reset_calls = 0
            self._fail_once = True

        def _ensure_ftff_combo_tables(self, _total_budget):
            return 1

        def ga_upload_item_stats(self, *_args, **_kwargs):
            return None

        def ga_upload_base_fixed_stats(self, *_args, **_kwargs):
            return None

        def ga_upload_init_heuristic_topk(self, *_args, **_kwargs):
            return None

        def ga_upload_initial_populations(self, *_args, **_kwargs):
            self.upload_calls += 1

        def ga_generate_initial_populations(self, *_args, **_kwargs):
            self.generate_calls += 1

        def ga_init_runs_best(self, *_args, **_kwargs):
            return None

        def hard_reset_taichi(self, *_args, **_kwargs):
            self.reset_calls += 1

        def ga_load_initial_populations_batch(self, *_args, **_kwargs):
            if self._fail_once:
                self._fail_once = False
                raise RuntimeError("failed to create semaphore")
            return None

        def ga_seed_rng_runs(self, *_args, **_kwargs):
            return None

        def ga_evaluate_population(self, *_args, **_kwargs):
            return None

        def ga_write_best_and_store_hints(self, *_args, **_kwargs):
            return None

        def ga_update_runs_best(self, *_args, **_kwargs):
            return None

        def ga_island_migration_runs(self, *_args, **_kwargs):
            return None

        def ga_next_generation_fused_runs(self, *_args, **_kwargs):
            return None

        def ga_pack_fg_candidates_table_segmented(self, *_args, **_kwargs):
            return None

        def ga_download_fg_selected_payload(self, *_args, **_kwargs):
            return np.zeros((1, 1, 1), dtype=np.int32)

    fake_gpu = _FakeGpuApi()

    fake_api_module = types.ModuleType("gear_optimizer.solver.taichi_gem.api")
    fake_api_module.load_ref_arrays = lambda _ref_arrays: None
    fake_api_module.precompute_timeline_gpu = lambda _calc_song, _ref_arrays, song_slot=0: int(song_slot)

    fake_fields_module = types.ModuleType("gear_optimizer.solver.taichi_gem.fields")
    fake_fields_module.MAX_WORK_ITEMS = 1_000_000
    fake_fields_module.MAX_GENOMES = 1_000_000
    fake_fields_module.MAX_GA_RUNS = 64
    fake_fields_module.configure_ga_run_buffers = lambda max_runs, max_genomes: (int(max_runs), int(max_genomes))

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api", fake_api_module)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.fields", fake_fields_module)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 1, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "_require_gpu_api", lambda: fake_gpu, raising=True)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "retry"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays={},
        song_slot=0,
        item_stats=np.zeros((1, 10), dtype=np.int32),
        slot_start=np.zeros((9,), dtype=np.int32),
        slot_count=np.zeros((9,), dtype=np.int32),
        base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
        n_generations=1,
        initial_populations=None,
        num_runs=2,
        n_genomes=8,
        color_flags={},
        cfg_data={"TotalBudget": 90, "GemScaleFever": 3, "fg_candidate_limit": 51},
        ga_seed=123,
    )

    assert isinstance(out, np.ndarray)
    assert fake_gpu.reset_calls >= 1
    assert fake_gpu.generate_calls >= 2
    assert fake_gpu.upload_calls == 0
