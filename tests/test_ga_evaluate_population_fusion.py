import numpy as np


def test_ga_evaluate_population_materialize_mode_dispatch(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls = []

    class _Kernels:
        @staticmethod
        def ga_build_exact_eval_reuse_map_kernel(*args):
            calls.append(("build_reuse", args))

        @staticmethod
        def ga_aggregate_and_init_best_kernel(*_args):
            calls.append("aggregate")

        @staticmethod
        def ga_apply_base_candidate_cache_kernel(*_args):
            calls.append("apply_base_cache")

        @staticmethod
        def ga_find_best_combo_warmstart_kernel(*_args):
            calls.append("evaluate")

        @staticmethod
        def ga_finalize_warmstart_lane_best_kernel(*_args):
            calls.append("finalize_warmstart")

        @staticmethod
        def ga_insert_base_candidate_cache_results_kernel(*_args):
            calls.append("insert_base_cache")

        @staticmethod
        def ga_propagate_exact_eval_reuse_chunk_best_kernel(*args):
            calls.append(("propagate_chunk", args))

        @staticmethod
        def ga_write_best_and_update_global_kernel(*_args):
            calls.append("write_global")

        @staticmethod
        def ga_write_best_results_from_key_kernel(*_args):
            calls.append("write_results")

        @staticmethod
        def ga_update_global_best_kernel(*_args):
            calls.append("update_global")

    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", _Kernels())
    monkeypatch.setattr(ga_operations, "_ensure_ftff_combo_tables", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(ga_operations, "compute_ga_combo_chunk", lambda **_kwargs: 1)
    monkeypatch.setattr(ga_operations, "_ga_eval_budget", lambda: 1024)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_base_stats_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_stats_signature_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_eval_results_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_GA_PLATEAU_PRUNE_ENABLED", 0, raising=False)

    ga_operations.ga_evaluate_population(
        n_genomes=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        materialize_mode="update_global",
    )
    assert calls == [
        "aggregate",
        "apply_base_cache",
        "evaluate",
        "finalize_warmstart",
        "insert_base_cache",
        "write_global",
    ]

    calls.clear()
    ga_operations.ga_evaluate_population(
        n_genomes=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        materialize_mode="results_only",
        update_global_best=True,
    )
    assert calls == [
        "aggregate",
        "apply_base_cache",
        "evaluate",
        "finalize_warmstart",
        "insert_base_cache",
        "write_results",
        "update_global",
    ]


def test_ga_evaluate_population_reuses_exact_eval_results(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls = []

    class _Kernels:
        @staticmethod
        def ga_build_exact_eval_reuse_map_kernel(*args):
            calls.append(("build_reuse", args))

        @staticmethod
        def ga_aggregate_and_init_best_kernel(*_args):
            calls.append("aggregate")

        @staticmethod
        def ga_apply_base_candidate_cache_kernel(*_args):
            calls.append("apply_base_cache")

        @staticmethod
        def ga_find_best_combo_warmstart_kernel(*args):
            calls.append(("evaluate", args))

        @staticmethod
        def ga_finalize_warmstart_lane_best_kernel(*args):
            calls.append(("finalize_warmstart", args))

        @staticmethod
        def ga_insert_base_candidate_cache_results_kernel(*args):
            calls.append(("insert_base_cache", args))

        @staticmethod
        def ga_propagate_exact_eval_reuse_chunk_best_kernel(*args):
            calls.append(("propagate_chunk", args))

        @staticmethod
        def ga_write_best_results_from_key_kernel(*_args):
            calls.append("write_results")

    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", _Kernels())
    monkeypatch.setattr(ga_operations, "_ensure_ftff_combo_tables", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(ga_operations, "compute_ga_combo_chunk", lambda **_kwargs: 1)
    monkeypatch.setattr(ga_operations, "_ga_eval_budget", lambda: 1024)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_base_stats_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_stats_signature_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_eval_results_reuse_enabled", lambda: 1)
    monkeypatch.setattr(ga_operations, "_GA_PLATEAU_PRUNE_ENABLED", 0, raising=False)

    ga_operations.ga_evaluate_population(
        n_genomes=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        materialize_mode="results_only",
    )

    assert calls[0] == ("build_reuse", (8, 9))
    assert calls[1] == "aggregate"
    assert calls[2] == "apply_base_cache"
    assert calls[3][0] == "evaluate"
    assert calls[3][1][-1] == 1
    assert calls[4] == ("finalize_warmstart", (8,))
    assert calls[5][0] == "insert_base_cache"
    assert calls[5][1][-1] == 1
    assert calls[6] == ("propagate_chunk", (8,))
    assert calls[7] == "write_results"


def test_ga_evaluate_population_can_disable_base_candidate_cache(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls = []

    class _Kernels:
        @staticmethod
        def ga_aggregate_and_init_best_kernel(*_args):
            calls.append("aggregate")

        @staticmethod
        def ga_apply_base_candidate_cache_kernel(*_args):
            calls.append("apply_base_cache")

        @staticmethod
        def ga_find_best_combo_warmstart_kernel(*_args):
            calls.append("evaluate")

        @staticmethod
        def ga_finalize_warmstart_lane_best_kernel(*_args):
            calls.append("finalize_warmstart")

        @staticmethod
        def ga_insert_base_candidate_cache_results_kernel(*_args):
            calls.append("insert_base_cache")

        @staticmethod
        def ga_write_best_results_from_key_kernel(*_args):
            calls.append("write_results")

    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", _Kernels())
    monkeypatch.setattr(ga_operations, "_ensure_ftff_combo_tables", lambda *_args, **_kwargs: 1)
    monkeypatch.setattr(ga_operations, "compute_ga_combo_chunk", lambda **_kwargs: 1)
    monkeypatch.setattr(ga_operations, "_ga_eval_budget", lambda: 1024)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_base_stats_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_stats_signature_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_eval_results_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_GA_PLATEAU_PRUNE_ENABLED", 0, raising=False)

    ga_operations.ga_evaluate_population(
        n_genomes=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        materialize_mode="results_only",
        use_base_candidate_cache=False,
    )

    assert calls == ["aggregate", "evaluate", "finalize_warmstart", "write_results"]


def test_ga_write_best_results_and_update_runs_best_dispatch(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls = []

    class _Kernels:
        @staticmethod
        def ga_write_best_results_and_update_runs_best_kernel(*args):
            calls.append(args)

    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", _Kernels())
    monkeypatch.setattr(ga_operations.fields, "MAX_GA_RUNS", 16, raising=False)
    monkeypatch.setattr(ga_operations.fields, "MAX_GA_RUN_GENOMES", 128, raising=False)
    monkeypatch.setattr(ga_operations.fields, "MAX_GENOMES", 1024, raising=False)

    ga_operations.ga_write_best_results_and_update_runs_best(
        run_idx_start=2,
        n_runs=3,
        n_genomes_per_run=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        song_slot=5,
        is_p_ft=1,
        is_s_ff=1,
    )

    assert calls == [(2, 3, 8, 9, 90, 3, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 5, 1)]


def test_ga_write_best_results_from_key_dispatch(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls = []

    class _Kernels:
        @staticmethod
        def ga_write_best_results_from_key_kernel(*args):
            calls.append(args)

    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", _Kernels())

    ga_operations.ga_write_best_results_from_key(
        n_genomes=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        song_slot=5,
        is_p_ft=1,
        is_s_ff=1,
    )

    assert calls == [(8, 90, 3, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 5, 1)]


def test_ga_refresh_scores_and_update_runs_best_dispatch(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls = []

    class _Kernels:
        @staticmethod
        def ga_refresh_scores_and_update_runs_best_kernel(*args):
            calls.append(args)

    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", _Kernels())
    monkeypatch.setattr(ga_operations.fields, "MAX_GA_RUNS", 16, raising=False)
    monkeypatch.setattr(ga_operations.fields, "MAX_GA_RUN_GENOMES", 128, raising=False)
    monkeypatch.setattr(ga_operations.fields, "MAX_GENOMES", 1024, raising=False)

    ga_operations.ga_refresh_scores_and_update_runs_best(
        run_idx_start=2,
        n_runs=3,
        n_genomes_per_run=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        song_slot=5,
        is_p_ft=1,
        is_s_ff=1,
    )

    assert calls == [(2, 3, 8, 9, 90, 3, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 5, 1)]


def test_ga_refresh_scores_update_runs_best_and_next_generation_fused_runs_dispatch(monkeypatch):
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls = []
    swaps = []

    class _Kernels:
        @staticmethod
        def ga_refresh_scores_update_runs_best_and_next_generation_full_runs_kernel(*args):
            calls.append(args)

        @staticmethod
        def ga_swap_population_kernel(*args):
            swaps.append(args)

    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", _Kernels())
    monkeypatch.setattr(ga_operations.fields, "MAX_GA_RUNS", 16, raising=False)
    monkeypatch.setattr(ga_operations.fields, "MAX_GA_RUN_GENOMES", 128, raising=False)
    monkeypatch.setattr(ga_operations.fields, "MAX_GENOMES", 1024, raising=False)

    ga_operations.ga_refresh_scores_update_runs_best_and_next_generation_fused_runs(
        run_idx_start=2,
        n_runs=3,
        n_genomes_per_run=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        song_slot=5,
        is_p_ft=1,
        is_s_ff=1,
        mutation_rate=0.0,
        immigrant_rate=0.0,
        tournament_k=4,
        n_islands=2,
        elites_per_island=1,
        novelty_repair_attempts=3,
    )

    assert calls == [
        (
            2,
            3,
            8,
            9,
            90,
            3,
            1,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            5,
            1,
            2,
            1,
            4,
            np.uint32(0),
            np.uint32(0),
            3,
        )
    ]
    assert swaps == [(24, 9)]
