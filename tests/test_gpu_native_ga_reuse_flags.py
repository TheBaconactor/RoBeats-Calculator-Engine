from __future__ import annotations

from types import SimpleNamespace


def _reset_ga_exact_stats_reuse_cache(ga_operations) -> None:
    ga_operations._GA_EXACT_STATS_REUSE_RAW = None
    ga_operations._GA_EXACT_STATS_REUSE_ENABLED = 0


def test_gpu_native_ga_exact_stats_reuse_defaults_off(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    monkeypatch.delenv("GPU_NATIVE_GA_EXACT_STATS_REUSE", raising=False)
    monkeypatch.delenv("GPU_NATIVE_GA_SCORE_SIGNATURE_REUSE", raising=False)
    _reset_ga_exact_stats_reuse_cache(ga_operations)

    assert ga_operations._ga_exact_genome_stats_signature_reuse_enabled() == 0


def test_ga_prepare_population_skips_exact_stats_reuse_map_by_default(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls: list[str] = []
    fake_kernels = SimpleNamespace(
        ga_build_exact_eval_reuse_map_kernel=lambda *_args: calls.append("raw_reuse"),
        ga_aggregate_and_init_best_kernel=lambda *_args: calls.append("aggregate"),
        ga_propagate_exact_eval_reuse_base_stats_kernel=lambda *_args: calls.append("propagate_base_stats"),
        ga_build_exact_eval_reuse_map_from_base_stats_kernel=lambda *_args: calls.append("stats_reuse"),
    )

    monkeypatch.delenv("GPU_NATIVE_GA_BASE_STATS_REUSE", raising=False)
    monkeypatch.delenv("GPU_NATIVE_GA_EXACT_EVAL_RESULTS_REUSE", raising=False)
    monkeypatch.delenv("GPU_NATIVE_GA_EXACT_EVAL_REUSE", raising=False)
    monkeypatch.delenv("GPU_NATIVE_GA_EXACT_STATS_REUSE", raising=False)
    monkeypatch.delenv("GPU_NATIVE_GA_SCORE_SIGNATURE_REUSE", raising=False)
    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", fake_kernels)
    ga_operations._GA_BASE_STATS_REUSE_RAW = None
    ga_operations._GA_BASE_STATS_REUSE_ENABLED = 0
    ga_operations._GA_EXACT_EVAL_RESULTS_REUSE_RAW = None
    ga_operations._GA_EXACT_EVAL_RESULTS_REUSE_ENABLED = 0
    _reset_ga_exact_stats_reuse_cache(ga_operations)

    ga_operations.ga_prepare_population_base_stats(12, n_slots=9)

    assert calls == ["aggregate"]


def test_ga_prepare_population_exact_stats_reuse_is_opt_in(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    calls: list[str] = []
    fake_kernels = SimpleNamespace(
        ga_build_exact_eval_reuse_map_kernel=lambda *_args: calls.append("raw_reuse"),
        ga_aggregate_and_init_best_kernel=lambda *_args: calls.append("aggregate"),
        ga_propagate_exact_eval_reuse_base_stats_kernel=lambda *_args: calls.append("propagate_base_stats"),
        ga_build_exact_eval_reuse_map_from_base_stats_kernel=lambda *_args: calls.append("stats_reuse"),
    )

    monkeypatch.delenv("GPU_NATIVE_GA_BASE_STATS_REUSE", raising=False)
    monkeypatch.delenv("GPU_NATIVE_GA_EXACT_EVAL_RESULTS_REUSE", raising=False)
    monkeypatch.delenv("GPU_NATIVE_GA_EXACT_EVAL_REUSE", raising=False)
    monkeypatch.setenv("GPU_NATIVE_GA_EXACT_STATS_REUSE", "1")
    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", fake_kernels)
    ga_operations._GA_BASE_STATS_REUSE_RAW = None
    ga_operations._GA_BASE_STATS_REUSE_ENABLED = 0
    ga_operations._GA_EXACT_EVAL_RESULTS_REUSE_RAW = None
    ga_operations._GA_EXACT_EVAL_RESULTS_REUSE_ENABLED = 0
    _reset_ga_exact_stats_reuse_cache(ga_operations)

    ga_operations.ga_prepare_population_base_stats(12, n_slots=9)

    assert calls == ["aggregate", "stats_reuse"]


def test_gpu_native_ga_exact_stats_reuse_is_explicit_opt_in(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.api import ga_operations

    monkeypatch.setenv("GPU_NATIVE_GA_EXACT_STATS_REUSE", "1")
    _reset_ga_exact_stats_reuse_cache(ga_operations)

    assert ga_operations._ga_exact_genome_stats_signature_reuse_enabled() == 1

    monkeypatch.setenv("GPU_NATIVE_GA_EXACT_STATS_REUSE", "0")
    _reset_ga_exact_stats_reuse_cache(ga_operations)

    assert ga_operations._ga_exact_genome_stats_signature_reuse_enabled() == 0
