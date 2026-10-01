"""Scoring-context changes must invalidate device memoization."""

from types import SimpleNamespace

import pytest

from gear_optimizer.solver.taichi_gem.api import ga_eval_cache
from gear_optimizer.solver.taichi_gem.api import ga_operations as ga


@pytest.mark.parametrize("change", [
    {"total_budget": 12}, {"gem_scale_fever": 2}, {"song_slot": 1},
    {"max_ft_gems_global": 1}, {"max_ff_gems_global": 1},
    *({f"is_{color}_{stat}": 1} for color in ("p", "s") for stat in ("ft", "ff", "pp", "cm", "fm", "ov")),
])
def test_every_scoring_argument_invalidates_cached_results(monkeypatch, change):
    clears = []
    monkeypatch.setattr(ga, "ensure_ready", lambda: None)
    monkeypatch.setattr(ga, "_ensure_ftff_combo_tables", lambda *_a, **_k: 1)
    monkeypatch.setattr(ga_eval_cache, "_context", None)
    monkeypatch.setattr(ga.fields, "ga_eval_cache_key", SimpleNamespace(fill=lambda value: clears.append(value)))
    monkeypatch.setattr(ga, "kernels", SimpleNamespace(**{
        name: lambda *_args: None for name in (
            "ga_compute_exact_eval_rep_kernel", "ga_build_unique_slot_table_kernel",
            "ga_find_best_combo_warmstart_kernel", "ga_finalize_warmstart_lane_best_kernel",
            "ga_scatter_dup_results_kernel",
        )
    }))
    original = {"total_budget": 9}
    ga.ga_evaluate_prepared_population(3, **original)
    ga.ga_evaluate_prepared_population(3, **original)
    assert clears == [0]
    ga.ga_evaluate_prepared_population(3, **(original | change))
    assert clears == [0, 0]
