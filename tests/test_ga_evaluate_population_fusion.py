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
        def ga_find_best_combo_warmstart_kernel(*_args):
            calls.append("evaluate")

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
    monkeypatch.setattr(ga_operations, "_ga_exact_genome_eval_results_reuse_enabled", lambda: 0)
    monkeypatch.setattr(ga_operations, "_GA_PLATEAU_PRUNE_ENABLED", 0, raising=False)

    ga_operations.ga_evaluate_population(
        n_genomes=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        materialize_mode="update_global",
    )
    assert calls == ["aggregate", "evaluate", "write_global"]

    calls.clear()
    ga_operations.ga_evaluate_population(
        n_genomes=8,
        n_slots=9,
        total_budget=90,
        gem_scale_fever=3,
        materialize_mode="results_only",
        update_global_best=True,
    )
    assert calls == ["aggregate", "evaluate", "write_results", "update_global"]


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
        def ga_find_best_combo_warmstart_kernel(*args):
            calls.append(("evaluate", args))

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
    assert calls[2][0] == "evaluate"
    assert calls[2][1][-1] == 1
    assert calls[3] == ("propagate_chunk", (8,))
    assert calls[4] == "write_results"


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
