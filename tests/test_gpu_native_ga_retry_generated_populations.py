import sys
import types

import numpy as np
import pytest


class _FakeGpuApi:
    def __init__(self, *, fail_once: bool = True) -> None:
        self.generate_calls = 0
        self.upload_calls = 0
        self.reset_calls = 0
        self.evaluate_calls = 0
        self.next_generation_calls = 0
        self.fused_refresh_next_generation_calls = 0
        self.refresh_scores_and_update_runs_best_calls = 0
        self._fail_once = bool(fail_once)
        self._current_population = np.zeros((8, 9), dtype=np.int32)
        self._staged_population = np.zeros((1, 8, 9), dtype=np.int32)

    def _make_population(self, n_genomes: int, n_slots: int) -> np.ndarray:
        pop = np.zeros((int(n_genomes), int(n_slots)), dtype=np.int32)
        for i in range(int(n_genomes)):
            pop[i, : min(6, int(n_slots))] = np.arange(1, 1 + min(6, int(n_slots)), dtype=np.int32) + i
            if int(n_slots) >= 9:
                pop[i, 6:9] = np.asarray([101 + i, 201 + i, 301 + i], dtype=np.int32)
        return pop

    def _ensure_ftff_combo_tables(self, _total_budget, **_kwargs):
        return 1

    def ga_upload_item_stats(self, *_args, **_kwargs):
        return None

    def ga_upload_base_fixed_stats(self, *_args, **_kwargs):
        return None

    def ga_upload_init_heuristic_topk(self, *_args, **_kwargs):
        return None

    def ga_upload_initial_populations(self, *_args, **_kwargs):
        self.upload_calls += 1

    def ga_generate_initial_populations(self, *, n_runs=1, n_genomes=8, n_slots=9, **_kwargs):
        self.generate_calls += 1
        self._staged_population = np.zeros((int(n_runs), int(n_genomes), int(n_slots)), dtype=np.int32)
        for run_idx in range(int(n_runs)):
            self._staged_population[run_idx] = self._make_population(int(n_genomes), int(n_slots)) + run_idx

    def ga_init_runs_best(self, *_args, **_kwargs):
        return None

    def hard_reset_taichi(self, *_args, **_kwargs):
        self.reset_calls += 1

    def ga_load_initial_populations_batch(self, *_args, **_kwargs):
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("failed to create semaphore")
        run_idx_start = int(_kwargs.get("run_idx_start", 0))
        n_runs = int(_kwargs.get("n_runs", 1))
        n_genomes_per_run = int(_kwargs.get("n_genomes_per_run", 8))
        n_slots = int(_kwargs.get("n_slots", 9))
        end_run = run_idx_start + n_runs
        self._current_population = self._staged_population[
            run_idx_start:end_run, :n_genomes_per_run, :n_slots
        ].reshape(n_runs * n_genomes_per_run, n_slots)
        return int(n_runs * n_genomes_per_run)

    def ga_seed_rng_runs(self, *_args, **_kwargs):
        return None

    def ga_prepare_population_base_stats(self, *_args, **_kwargs):
        return None

    def ga_evaluate_prepared_population(self, *_args, **_kwargs):
        self.evaluate_calls += 1
        self.last_evaluate_kwargs = dict(_kwargs)
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("failed to create semaphore")
        return None

    def ga_update_runs_best(self, *_args, **_kwargs):
        return None

    def ga_refresh_scores_and_update_runs_best(self, *_args, **_kwargs):
        self.refresh_scores_and_update_runs_best_calls += 1
        return None

    def ga_island_migration_runs(self, *_args, **_kwargs):
        return None

    def ga_next_generation_fused_runs(self, *_args, **_kwargs):
        self.next_generation_calls += 1
        return None

    def ga_refresh_scores_update_runs_best_and_next_generation_fused_runs(self, *_args, **_kwargs):
        self.fused_refresh_next_generation_calls += 1
        return None

    def ga_pack_fg_candidates_table_segmented(self, *_args, **_kwargs):
        return None

    def ga_download_fg_selected_payload(self, *_args, **_kwargs):
        return np.zeros((1, 26), dtype=np.int32)


def _ref_arrays() -> dict[str, np.ndarray]:
    return {
        "Perfect Points": np.arange(161, dtype=np.float32),
        "Combo Multiplier": np.arange(161, dtype=np.float32),
        "Fever Multiplier": np.arange(161, dtype=np.float32),
        "Fever Time": np.arange(161, dtype=np.float32),
        "Fever Fill Rate": np.arange(161, dtype=np.float32),
    }


def _install_fake_taichi_modules(monkeypatch, gpu_api=None) -> None:
    fake_api_module = types.ModuleType("gear_optimizer.solver.taichi_gem.api")
    fake_api_module.load_ref_arrays = lambda _ref_arrays: None
    fake_api_module.ensure_ready = lambda _ref_arrays=None, **_kwargs: b""
    fake_api_module.precompute_timeline_gpu = lambda _calc_song, _ref_arrays, song_slot=0: int(song_slot)
    if gpu_api is not None:
        for name in dir(gpu_api):
            if not name.startswith("_") or name == "_ensure_ftff_combo_tables":
                setattr(fake_api_module, name, getattr(gpu_api, name))

    fake_fields_module = types.ModuleType("gear_optimizer.solver.taichi_gem.fields")
    fake_fields_module.MAX_WORK_ITEMS = 1_000_000
    fake_fields_module.MAX_EVALS_PER_DISPATCH = 1_000_000
    fake_fields_module.MAX_GENOMES = 1_000_000
    fake_fields_module.MAX_GA_RUNS = 64
    fake_fields_module.configure_ga_run_buffers = lambda max_runs, max_genomes: (int(max_runs), int(max_genomes))

    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.api", fake_api_module)
    monkeypatch.setitem(sys.modules, "gear_optimizer.solver.taichi_gem.fields", fake_fields_module)


def _install_fake_taichi_sync(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "taichi", types.SimpleNamespace(sync=lambda: None))


def test_run_gpu_native_ga_requires_explicit_seed(monkeypatch):
    from gear_optimizer.solver import genetic_pipeline as genetic

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)

    with pytest.raises(ValueError, match="explicit per-run ga_seed"):
        genetic.run_gpu_native_ga_runs_payload_prebuilt(
            calc_song={"metadata": {"Song Name": "seed-required"}},
            ref_arrays=_ref_arrays(),
            song_slot=0,
            item_stats=np.zeros((1, 10), dtype=np.int32),
            slot_start=np.zeros((9,), dtype=np.int32),
            slot_count=np.zeros((9,), dtype=np.int32),
            base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
            n_generations=1,
            initial_populations=None,
            num_runs=1,
            n_genomes=8,
            color_flags={},
            cfg_data={"TotalBudget": 90, "GemScaleFever": 3, "fg_candidate_limit": 51},
            ga_seed=None,
        )


def test_run_gpu_native_ga_retry_with_generated_initial_populations(monkeypatch):
    from gear_optimizer.solver import genetic_pipeline as genetic

    fake_gpu = _FakeGpuApi(fail_once=True)
    _install_fake_taichi_modules(monkeypatch, fake_gpu)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 1, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "retry"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays=_ref_arrays(),
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
        cfg_data={
            "TotalBudget": 90,
            "GemScaleFever": 3,
            "fg_candidate_limit": 51,
        },
        ga_seed=123,
    )

    assert isinstance(out, np.ndarray)
    assert fake_gpu.reset_calls >= 1
    assert fake_gpu.generate_calls == 2
    assert fake_gpu.refresh_scores_and_update_runs_best_calls == 1
    assert fake_gpu.upload_calls == 0
    assert "use_base_candidate_cache" not in fake_gpu.last_evaluate_kwargs


def test_run_gpu_native_ga_fuses_refresh_with_next_generation(monkeypatch):
    from gear_optimizer.solver import genetic_pipeline as genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch, fake_gpu)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "GPU_GA_GENS_PER_MIGRATION", 9999, raising=False)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "fused-refresh-next", "Difficulty": "Hard"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays=_ref_arrays(),
        song_slot=0,
        item_stats=np.zeros((1, 10), dtype=np.int32),
        slot_start=np.zeros((9,), dtype=np.int32),
        slot_count=np.zeros((9,), dtype=np.int32),
        base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
        n_generations=3,
        initial_populations=None,
        num_runs=1,
        n_genomes=8,
        color_flags={},
        cfg_data={"TotalBudget": 90, "GemScaleFever": 3, "fg_candidate_limit": 51},
        ga_seed=123,
    )

    assert isinstance(out, np.ndarray)
    assert fake_gpu.fused_refresh_next_generation_calls == 2
    assert fake_gpu.next_generation_calls == 0
    assert fake_gpu.refresh_scores_and_update_runs_best_calls == 1


def test_run_gpu_native_ga_raises_when_abort_requested(monkeypatch):
    from gear_optimizer.solver import genetic_pipeline as genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch, fake_gpu)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)

    with pytest.raises(RuntimeError, match="GpuExecutor aborted:"):
        genetic.run_gpu_native_ga_runs_payload_prebuilt(
            calc_song={
                "metadata": {"Song Name": "abort-smoke", "Difficulty": "Hard"},
                "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
            },
            ref_arrays=_ref_arrays(),
            song_slot=0,
            item_stats=np.zeros((1, 10), dtype=np.int32),
            slot_start=np.zeros((9,), dtype=np.int32),
            slot_count=np.zeros((9,), dtype=np.int32),
            base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
            n_generations=3,
            initial_populations=None,
            num_runs=1,
            n_genomes=8,
            color_flags={},
            cfg_data={"TotalBudget": 90, "GemScaleFever": 3, "fg_candidate_limit": 51},
            ga_seed=123,
            abort_requested=lambda: fake_gpu.evaluate_calls >= 1,
    )

    assert fake_gpu.evaluate_calls == 1
    assert fake_gpu.next_generation_calls == 0


def test_run_gpu_native_ga_hybrid_multirun_raises_when_abort_requested(monkeypatch):
    from gear_optimizer.solver import genetic_pipeline as genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch, fake_gpu)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)

    with pytest.raises(RuntimeError, match="GpuExecutor aborted:"):
        genetic.run_gpu_native_ga_runs_payload_prebuilt(
            calc_song={
                "metadata": {"Song Name": "steady-abort-smoke", "Difficulty": "Hard"},
                "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
            },
            ref_arrays=_ref_arrays(),
            song_slot=0,
            item_stats=np.zeros((1, 10), dtype=np.int32),
            slot_start=np.zeros((9,), dtype=np.int32),
            slot_count=np.zeros((9,), dtype=np.int32),
            base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
            n_generations=3,
            initial_populations=None,
            num_runs=3,
            n_genomes=8,
            color_flags={},
            cfg_data={
                "TotalBudget": 90,
                "GemScaleFever": 3,
                "fg_candidate_limit": 51,
            },
            ga_seed=123,
            abort_requested=lambda: fake_gpu.evaluate_calls >= 1,
        )

    assert fake_gpu.evaluate_calls == 1


def test_run_gpu_native_ga_hybrid_multirun_forwards_global_ftff_caps(monkeypatch):
    from gear_optimizer.solver import genetic_pipeline as genetic

    fake_gpu = _FakeGpuApi(fail_once=False)

    evaluate_kwargs: list[dict] = []
    original_evaluate = fake_gpu.ga_evaluate_prepared_population

    def _capture_evaluate(*args, **kwargs):
        evaluate_kwargs.append(dict(kwargs))
        return original_evaluate(*args, **kwargs)

    fake_gpu.ga_evaluate_prepared_population = _capture_evaluate
    _install_fake_taichi_modules(monkeypatch, fake_gpu)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "steady-ftff-smoke", "Difficulty": "Hard"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays=_ref_arrays(),
        song_slot=0,
        item_stats=np.zeros((16, 10), dtype=np.int32),
        slot_start=np.zeros((9,), dtype=np.int32),
        slot_count=np.zeros((9,), dtype=np.int32),
        base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
        n_generations=1,
        initial_populations=None,
        num_runs=3,
        n_genomes=8,
        color_flags={},
        cfg_data={
            "TotalBudget": 90,
            "GemScaleFever": 3,
            "fg_candidate_limit": 51,
        },
        ga_seed=123,
    )

    assert isinstance(out, np.ndarray)
    assert evaluate_kwargs
    assert all("max_ft_gems_global" in kwargs for kwargs in evaluate_kwargs)
    assert all("max_ff_gems_global" in kwargs for kwargs in evaluate_kwargs)
    assert all("materialize_mode" not in kwargs for kwargs in evaluate_kwargs)
    assert fake_gpu.refresh_scores_and_update_runs_best_calls == 1


def test_run_gpu_native_ga_hybrid_multirun_emits_phase_events(monkeypatch):
    from gear_optimizer.solver import genetic_pipeline as genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch, fake_gpu)
    _install_fake_taichi_sync(monkeypatch)

    events: list[dict] = []

    monkeypatch.setenv("GPU_NATIVE_GA_PHASE_TIMING", "1")
    monkeypatch.setenv("METAFINDER_PROFILE_EVENTS", "1")
    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "emit_profile_event", lambda **kwargs: events.append(dict(kwargs)), raising=True)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "steady-phase-smoke", "Difficulty": "Hard"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays=_ref_arrays(),
        song_slot=0,
        item_stats=np.zeros((16, 10), dtype=np.int32),
        slot_start=np.zeros((9,), dtype=np.int32),
        slot_count=np.zeros((9,), dtype=np.int32),
        base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
        n_generations=1,
        initial_populations=None,
        num_runs=3,
        n_genomes=8,
        color_flags={},
        cfg_data={
            "TotalBudget": 90,
            "GemScaleFever": 3,
            "fg_candidate_limit": 51,
        },
        ga_seed=123,
    )

    phase_events = [event for event in events if event.get("event") == "ga_gpu_phase"]
    flag_events = [event for event in events if event.get("event") == "ga_gpu_phase_flags"]

    assert isinstance(out, np.ndarray)
    assert len(flag_events) == 1
    phases = {event.get("metrics", {}).get("phase") for event in phase_events}
    assert {"evaluate", "update_runs_best", "pack_fg_candidates"}.issubset(phases)
    assert all(int(event.get("metrics", {}).get("batch_runs", 0)) == 3 for event in phase_events)
