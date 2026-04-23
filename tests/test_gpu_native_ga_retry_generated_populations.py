import sys
import types

import numpy as np
import pytest


class _FakeGpuApi:
    def __init__(self, *, fail_once: bool = True) -> None:
        self.generate_calls = 0
        self.upload_calls = 0
        self.population_upload_calls = 0
        self.reset_calls = 0
        self.snapshot_calls = 0
        self.download_runs_calls = 0
        self.store_payload_calls = 0
        self.download_run_payload_calls = 0
        self.global_best_init_calls = 0
        self.global_best_update_calls = 0
        self.global_best_download_calls = 0
        self.evaluate_calls = 0
        self.next_generation_calls = 0
        self.write_best_results_and_update_runs_best_calls = 0
        self.refresh_scores_and_update_runs_best_calls = 0
        self.write_best_results_from_key_calls = 0
        self.population_upload_history: list[np.ndarray] = []
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

    def ga_upload_population_indices(self, population_indices_np, *, n_slots=9):
        self.population_upload_calls += 1
        arr = np.asarray(population_indices_np, dtype=np.int32)
        self._current_population = arr[:, : int(n_slots)].copy()
        self.population_upload_history.append(self._current_population.copy())
        return int(arr.shape[0])

    def ga_upload_initial_populations(self, *_args, **_kwargs):
        self.upload_calls += 1

    def ga_generate_initial_populations(self, *, n_runs=1, n_genomes=8, n_slots=9, **_kwargs):
        self.generate_calls += 1
        self._staged_population = np.zeros((int(n_runs), int(n_genomes), int(n_slots)), dtype=np.int32)
        for run_idx in range(int(n_runs)):
            self._staged_population[run_idx] = self._make_population(int(n_genomes), int(n_slots)) + run_idx

    def ga_load_initial_population(self, *, run_idx, n_genomes, n_slots=9):
        self._current_population = self._staged_population[int(run_idx), : int(n_genomes), : int(n_slots)].copy()
        return None

    def ga_init_runs_best(self, *_args, **_kwargs):
        return None

    def hard_reset_taichi(self, *_args, **_kwargs):
        self.reset_calls += 1

    def ga_load_initial_populations_batch(self, *_args, **_kwargs):
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("failed to create semaphore")
        return None

    def ga_seed_rng(self, *_args, **_kwargs):
        return None

    def ga_seed_rng_runs(self, *_args, **_kwargs):
        return None

    def ga_evaluate_population(self, *_args, **_kwargs):
        self.evaluate_calls += 1
        if self._fail_once:
            self._fail_once = False
            raise RuntimeError("failed to create semaphore")
        return None

    def ga_update_runs_best(self, *_args, **_kwargs):
        return None

    def ga_write_best_results_and_update_runs_best(self, *_args, **_kwargs):
        self.write_best_results_and_update_runs_best_calls += 1
        return None

    def ga_refresh_scores_and_update_runs_best(self, *_args, **_kwargs):
        self.refresh_scores_and_update_runs_best_calls += 1
        return None

    def ga_write_best_results_from_key(self, *_args, **_kwargs):
        self.write_best_results_from_key_calls += 1
        return None

    def ga_init_global_best(self, *_args, **_kwargs):
        self.global_best_init_calls += 1
        return None

    def ga_update_global_best(self, *_args, **_kwargs):
        self.global_best_update_calls += 1
        return None

    def ga_download_global_best(self, *_args, **_kwargs):
        self.global_best_download_calls += 1
        return 123, np.zeros((9,), dtype=np.int32), np.array([123, 1, 2, 3, 4, 5, 6], dtype=np.int32)

    def ga_upload_island_boundaries(self, *_args, **_kwargs):
        return None

    def ga_island_migration(self, *_args, **_kwargs):
        return None

    def ga_island_migration_runs(self, *_args, **_kwargs):
        return None

    def ga_next_generation_fused(self, *_args, **_kwargs):
        return None

    def ga_next_generation_fused_runs(self, *_args, **_kwargs):
        self.next_generation_calls += 1
        return None

    def ga_store_run_payload(self, *_args, **_kwargs):
        self.store_payload_calls += 1
        return None

    def ga_download_run_payload(self, *, n_genomes, n_slots=9):
        self.download_run_payload_calls += 1
        pop = self._current_population[: int(n_genomes), : int(n_slots)].copy()
        results = np.zeros((int(n_genomes), 7), dtype=np.int32)
        scores = np.arange(int(n_genomes), 0, -1, dtype=np.int32) * 100
        best_ids = pop[0].copy() if int(n_genomes) > 0 else np.zeros((int(n_slots),), dtype=np.int32)
        best_result = np.asarray([int(scores[0]) if int(n_genomes) > 0 else 0, 0, 0, 0, 0, 0, 0], dtype=np.int32)
        best_score = int(scores[0]) if int(n_genomes) > 0 else 0
        return best_score, best_ids, best_result, pop, results, scores

    def ga_download_population_indices(self, *, n_genomes, n_slots=9):
        return self._current_population[: int(n_genomes), : int(n_slots)].copy()

    def ga_pack_fg_candidates_table_segmented(self, *_args, **_kwargs):
        return None

    def ga_store_runs_payload_snapshot_segmented(self, *_args, **_kwargs):
        self.snapshot_calls += 1
        return None

    def ga_download_runs_payload(self, *, n_runs, n_genomes, n_slots=9):
        self.download_runs_calls += 1
        width = 1 + int(n_slots) + 7
        return np.zeros((int(n_runs), int(n_genomes) + 1, width), dtype=np.int32)

    def ga_download_fg_selected_payload(self, *_args, **_kwargs):
        return np.zeros((1, 1, 1), dtype=np.int32)


def _install_fake_taichi_modules(monkeypatch) -> None:
    fake_api_module = types.ModuleType("gear_optimizer.solver.taichi_gem.api")
    fake_api_module.load_ref_arrays = lambda _ref_arrays: None
    fake_api_module.precompute_timeline_gpu = lambda _calc_song, _ref_arrays, song_slot=0: int(song_slot)

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


def test_run_gpu_native_ga_retry_with_generated_initial_populations(monkeypatch):
    from gear_optimizer.solver import genetic

    fake_gpu = _FakeGpuApi(fail_once=True)
    _install_fake_taichi_modules(monkeypatch)

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
    assert fake_gpu.generate_calls == 1
    assert fake_gpu.download_run_payload_calls == 1
    assert fake_gpu.store_payload_calls == 2
    assert fake_gpu.upload_calls == 0
    assert fake_gpu.population_upload_calls >= 3


def test_run_gpu_native_ga_trace_enabled_smoke(tmp_path, monkeypatch):
    from gear_optimizer.solver import genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "_require_gpu_api", lambda: fake_gpu, raising=True)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "trace-smoke", "Difficulty": "Hard", "HumanHitSimSeed": 11},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays={},
        song_slot=0,
        item_stats=np.zeros((1, 10), dtype=np.int32),
        slot_start=np.zeros((9,), dtype=np.int32),
        slot_count=np.zeros((9,), dtype=np.int32),
        base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
        n_generations=2,
        initial_populations=None,
        num_runs=1,
        n_genomes=8,
        color_flags={},
        cfg_data={
            "TotalBudget": 90,
            "GemScaleFever": 3,
            "fg_candidate_limit": 51,
            "ga_convergence_trace_enabled": True,
            "ga_convergence_trace_every": 1,
            "ga_convergence_trace_out_dir": str(tmp_path / "ga_trace"),
            "ga_convergence_trace_song_filter": "trace",
        },
        ga_seed=123,
    )

    assert isinstance(out, np.ndarray)
    assert fake_gpu.global_best_init_calls >= 1
    assert fake_gpu.global_best_update_calls >= 1
    assert fake_gpu.global_best_download_calls >= 1
    assert fake_gpu.write_best_results_and_update_runs_best_calls >= 1
    assert fake_gpu.refresh_scores_and_update_runs_best_calls == 0


def test_run_gpu_native_ga_raises_when_abort_requested(monkeypatch):
    from gear_optimizer.solver import genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "_require_gpu_api", lambda: fake_gpu, raising=True)

    with pytest.raises(RuntimeError, match="GpuExecutor aborted:"):
        genetic.run_gpu_native_ga_runs_payload_prebuilt(
            calc_song={
                "metadata": {"Song Name": "abort-smoke", "Difficulty": "Hard"},
                "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
            },
            ref_arrays={},
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
    assert fake_gpu.global_best_update_calls == 0


def test_run_gpu_native_ga_steady_state_raises_when_abort_requested(monkeypatch):
    from gear_optimizer.solver import genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "_require_gpu_api", lambda: fake_gpu, raising=True)

    with pytest.raises(RuntimeError, match="GpuExecutor aborted:"):
        genetic.run_gpu_native_ga_runs_payload_prebuilt(
            calc_song={
                "metadata": {"Song Name": "steady-abort-smoke", "Difficulty": "Hard"},
                "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
            },
            ref_arrays={},
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
                "ga_steady_state_enabled": True,
                "ga_steady_state_refresh_pct": 0.25,
                "ga_steady_state_min_refresh": 2,
            },
            ga_seed=123,
            abort_requested=lambda: fake_gpu.evaluate_calls >= 1,
        )

    assert fake_gpu.evaluate_calls == 1
    assert fake_gpu.store_payload_calls == 0
    assert fake_gpu.download_run_payload_calls == 0


def test_run_gpu_native_ga_steady_state_forwards_global_ftff_caps(monkeypatch):
    from gear_optimizer.solver import genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch)

    evaluate_kwargs: list[dict] = []
    original_evaluate = fake_gpu.ga_evaluate_population

    def _capture_evaluate(*args, **kwargs):
        evaluate_kwargs.append(dict(kwargs))
        return original_evaluate(*args, **kwargs)

    fake_gpu.ga_evaluate_population = _capture_evaluate

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "_require_gpu_api", lambda: fake_gpu, raising=True)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "steady-ftff-smoke", "Difficulty": "Hard"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays={},
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
            "ga_steady_state_enabled": True,
            "ga_steady_state_refresh_pct": 0.25,
            "ga_steady_state_min_refresh": 2,
        },
        ga_seed=123,
    )

    assert isinstance(out, np.ndarray)
    assert evaluate_kwargs
    assert all("max_ft_gems_global" in kwargs for kwargs in evaluate_kwargs)
    assert all("max_ff_gems_global" in kwargs for kwargs in evaluate_kwargs)


def test_run_gpu_native_ga_steady_state_emits_phase_events(monkeypatch):
    from gear_optimizer.solver import genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch)
    _install_fake_taichi_sync(monkeypatch)

    events: list[dict] = []

    monkeypatch.setenv("GPU_NATIVE_GA_PHASE_TIMING", "1")
    monkeypatch.setenv("METAFINDER_PROFILE_EVENTS", "1")
    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "_require_gpu_api", lambda: fake_gpu, raising=True)
    monkeypatch.setattr(genetic, "emit_profile_event", lambda **kwargs: events.append(dict(kwargs)), raising=True)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "steady-phase-smoke", "Difficulty": "Hard"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays={},
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
            "ga_steady_state_enabled": True,
            "ga_steady_state_refresh_pct": 0.25,
            "ga_steady_state_min_refresh": 2,
        },
        ga_seed=123,
    )

    phase_events = [event for event in events if event.get("event") == "ga_gpu_phase"]
    flag_events = [event for event in events if event.get("event") == "ga_gpu_phase_flags"]

    assert isinstance(out, np.ndarray)
    assert len(flag_events) == 1
    assert len(phase_events) == 3
    assert all(event.get("metrics", {}).get("phase") == "evaluate" for event in phase_events)
    assert all(int(event.get("metrics", {}).get("batch_runs", 0)) == 1 for event in phase_events)


def test_run_gpu_native_ga_audit_enabled_snapshots_full_runs(monkeypatch):
    from gear_optimizer.solver import genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch)

    audit_calls: list[dict] = []
    written_paths: list[str] = []

    monkeypatch.setenv("GA_REDUNDANCY_AUDIT", "1")
    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "_require_gpu_api", lambda: fake_gpu, raising=True)
    monkeypatch.setattr(
        genetic,
        "analyze_ga_redundancy_from_runs_payload",
        lambda **kwargs: audit_calls.append(kwargs) or {"song_name": "audit", "rows": 16},
        raising=True,
    )
    monkeypatch.setattr(
        genetic,
        "summarize_ga_redundancy_record",
        lambda record: f"audit rows={record['rows']}",
        raising=True,
    )
    monkeypatch.setattr(
        genetic,
        "write_ga_redundancy_audit_record",
        lambda record: written_paths.append(str(record.get("song_name", ""))) or "audit.jsonl",
        raising=True,
    )

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "audit-smoke", "Difficulty": "Hard"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays={},
        song_slot=0,
        item_stats=np.zeros((16, 10), dtype=np.int32),
        slot_start=np.zeros((9,), dtype=np.int32),
        slot_count=np.zeros((9,), dtype=np.int32),
        base_fixed_stats_arr=np.zeros((10,), dtype=np.int32),
        n_generations=1,
        initial_populations=None,
        num_runs=3,
        n_genomes=8,
        color_flags={},
        cfg_data={"TotalBudget": 90, "GemScaleFever": 3, "fg_candidate_limit": 51, "selected_color": "Rush"},
        ga_seed=7,
    )

    assert isinstance(out, np.ndarray)
    assert fake_gpu.snapshot_calls == 0
    assert fake_gpu.download_runs_calls == 1
    assert fake_gpu.store_payload_calls == 3
    assert len(audit_calls) == 1
    assert len(written_paths) == 1


def test_run_gpu_native_ga_steady_state_rejects_archive_rows(monkeypatch):
    from gear_optimizer.solver import genetic

    fake_gpu = _FakeGpuApi(fail_once=False)
    _install_fake_taichi_modules(monkeypatch)

    monkeypatch.setattr(genetic, "_GPU_NATIVE_AVAILABLE", True, raising=True)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RETRIES", 0, raising=False)
    monkeypatch.setattr(genetic, "_GPU_NATIVE_GA_VULKAN_RESET_EVERY_RUNS", 0, raising=False)
    monkeypatch.setattr(genetic, "_require_gpu_api", lambda: fake_gpu, raising=True)

    out = genetic.run_gpu_native_ga_runs_payload_prebuilt(
        calc_song={
            "metadata": {"Song Name": "steady-archive", "Difficulty": "Hard"},
            "song_data": {"timestamps": np.asarray([0.0], dtype=np.float32)},
        },
        ref_arrays={},
        song_slot=0,
        item_stats=np.zeros((512, 10), dtype=np.int32),
        slot_start=np.asarray([1, 32, 64, 96, 128, 160, 192, 0, 0], dtype=np.int32),
        slot_count=np.asarray([31, 31, 31, 31, 31, 31, 31, 0, 0], dtype=np.int32),
        base_fixed_stats_arr=np.zeros((7,), dtype=np.int32),
        n_generations=1,
        initial_populations=None,
        num_runs=3,
        n_genomes=8,
        elite_count=1,
        color_flags={},
        cfg_data={
            "TotalBudget": 90,
            "GemScaleFever": 3,
            "fg_candidate_limit": 51,
            "selected_color": "Rush",
            "ga_steady_state_enabled": True,
            "ga_steady_state_refresh_pct": 0.25,
            "ga_steady_state_min_refresh": 2,
        },
        ga_seed=123,
    )

    assert isinstance(out, np.ndarray)
    assert fake_gpu.population_upload_calls >= 3
    assert len(fake_gpu.population_upload_history) >= 3

    epoch1_population = fake_gpu.population_upload_history[1]
    epoch2_population = fake_gpu.population_upload_history[2]

    epoch1_keys = {tuple(int(x) for x in row.tolist()) for row in epoch1_population}
    epoch2_keys = {tuple(int(x) for x in row.tolist()) for row in epoch2_population}

    assert len(epoch2_keys - epoch1_keys) >= 1
