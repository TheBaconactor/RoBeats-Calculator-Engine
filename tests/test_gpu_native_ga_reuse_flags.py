from __future__ import annotations

from types import SimpleNamespace


def test_ga_prepare_population_never_builds_exact_reuse_map(monkeypatch) -> None:
    """The per-generation exact-eval reuse-map path was removed: it added a
    host/driver/submit/sort overhead every GA generation that starved the GPU
    (host_fraction ~65.8% -> ~0.9% once disabled). The opt-in env vars are gone,
    so setting them must have NO effect and the reuse kernels must never dispatch.
    """
    from gear_optimizer.solver.taichi_gem.api import ga_operations
    from gear_optimizer.solver.taichi_gem.kernels.kernels_helpers import gpu_color_flags

    calls: list[str] = []
    fake_kernels = SimpleNamespace(
        ga_aggregate_genome_stats_kernel=lambda *_a: calls.append("aggregate"),
    )

    # All former opt-in env vars (and their legacy aliases) must now be inert.
    for name in (
        "GPU_NATIVE_GA_BASE_STATS_REUSE",
        "GPU_NATIVE_GA_EXACT_EVAL_RESULTS_REUSE",
        "GPU_NATIVE_GA_EXACT_EVAL_REUSE",
        "GPU_NATIVE_GA_EXACT_STATS_REUSE",
        "GPU_NATIVE_GA_SCORE_SIGNATURE_REUSE",
    ):
        monkeypatch.setenv(name, "1")
    monkeypatch.setattr(ga_operations, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga_operations, "kernels", fake_kernels)

    ga_operations.ga_prepare_population_base_stats(12, n_slots=9, flags=gpu_color_flags(None))

    assert calls == ["aggregate"]
