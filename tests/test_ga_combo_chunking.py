from __future__ import annotations

from gear_optimizer.solver.taichi_gem.ga_chunking import compute_ga_combo_chunk


def test_compute_ga_combo_chunk_returns_full_when_within_budget() -> None:
    chunk = compute_ga_combo_chunk(
        n_genomes=100,
        n_combos=10,
        max_evals=1000,
        chunk_min=64,
        chunk_max=4096,
    )
    assert chunk == 10


def test_compute_ga_combo_chunk_respects_budget_even_if_chunk_min_is_high() -> None:
    # Budget-based target is 100 combos, but chunk_min is 1024. The helper must clamp
    # to the budget to avoid overly-long dispatches.
    chunk = compute_ga_combo_chunk(
        n_genomes=100,
        n_combos=1000,
        max_evals=10_000,
        chunk_min=1024,
        chunk_max=4096,
    )
    assert chunk == 100
    assert 100 * chunk <= 10_000


def test_compute_ga_combo_chunk_handles_extreme_low_budget() -> None:
    # If max_evals is below n_genomes, the best we can do is 1 combo per dispatch.
    chunk = compute_ga_combo_chunk(
        n_genomes=1000,
        n_combos=1000,
        max_evals=100,
        chunk_min=1024,
        chunk_max=4096,
    )
    assert chunk == 1


def test_compute_ga_combo_chunk_returns_zero_when_no_combos() -> None:
    chunk = compute_ga_combo_chunk(
        n_genomes=10,
        n_combos=0,
        max_evals=100,
        chunk_min=1,
        chunk_max=1,
    )
    assert chunk == 0
