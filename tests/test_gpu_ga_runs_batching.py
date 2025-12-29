import os
import sys

import numpy as np
import pytest

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


pytestmark = pytest.mark.gpu


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_load_initial_populations_batch_roundtrip():
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_initial_populations,
        ga_load_initial_populations_batch,
        ga_download_population_indices,
    )

    n_runs = 4
    n_genomes = 32
    n_slots = 9
    rng = np.random.default_rng(123)
    pops = rng.integers(0, 1000, size=(n_runs, n_genomes, n_slots), dtype=np.int32)

    ga_upload_initial_populations(pops, n_runs=n_runs, n_genomes=n_genomes, n_slots=n_slots)

    # Load runs [1, 2] into a contiguous active population.
    n_total = ga_load_initial_populations_batch(run_idx_start=1, n_runs=2, n_genomes_per_run=n_genomes, n_slots=n_slots)
    out = ga_download_population_indices(n_genomes=n_total, n_slots=n_slots)

    expected = np.concatenate([pops[1], pops[2]], axis=0)
    assert np.array_equal(out, expected)


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_next_generation_fused_runs_matches_sequential():
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_island_boundaries,
        ga_upload_population_indices,
        ga_seed_rng,
        ga_seed_rng_runs,
        ga_set_scores,
        ga_next_generation_fused,
        ga_next_generation_fused_runs,
        ga_download_population_indices,
    )

    n_runs = 2
    n_genomes = 32
    n_slots = 9
    n_total = n_runs * n_genomes
    n_islands = 4
    elites_per_island = 2

    rng = np.random.default_rng(123)

    # Build two disjoint populations (so cross-run mixing is detectable).
    pop0 = rng.integers(0, 10_000, size=(n_genomes, n_slots), dtype=np.int32)
    pop1 = rng.integers(100_000, 110_000, size=(n_genomes, n_slots), dtype=np.int32)

    # Ensure minis [6:9] are unique per genome (avoid uniqueness repair re-rolls).
    for g in range(n_genomes):
        pop0[g, 6] = 50_000 + (g * 3 + 0)
        pop0[g, 7] = 50_000 + (g * 3 + 1)
        pop0[g, 8] = 50_000 + (g * 3 + 2)

        pop1[g, 6] = 150_000 + (g * 3 + 0)
        pop1[g, 7] = 150_000 + (g * 3 + 1)
        pop1[g, 8] = 150_000 + (g * 3 + 2)

    scores0 = rng.integers(0, 1_000_000, size=(n_genomes,), dtype=np.int32)
    scores1 = rng.integers(0, 1_000_000, size=(n_genomes,), dtype=np.int32)

    island_boundaries = np.array([0, 8, 16, 24, 32], dtype=np.int32)

    # Sequential per-run execution.
    seq_out = []
    for pop, scores in [(pop0, scores0), (pop1, scores1)]:
        ga_upload_population_indices(pop, n_slots=n_slots)
        ga_set_scores(scores, n_genomes=n_genomes)
        ga_seed_rng(n_genomes, seed=42)
        ga_upload_island_boundaries(island_boundaries)
        ga_next_generation_fused(
            n_genomes=n_genomes,
            n_slots=n_slots,
            mutation_rate=0.0,
            immigrant_rate=0.0,
            tournament_k=3,
            n_islands=n_islands,
            elites_per_island=elites_per_island,
        )
        seq_out.append(ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots))

    # Batched execution.
    batched_pop = np.concatenate([pop0, pop1], axis=0)
    batched_scores = np.concatenate([scores0, scores1], axis=0)
    ga_upload_population_indices(batched_pop, n_slots=n_slots)
    ga_set_scores(batched_scores, n_genomes=n_total)
    ga_seed_rng_runs(n_runs=n_runs, n_genomes_per_run=n_genomes, seed=42)
    ga_next_generation_fused_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.0,
        immigrant_rate=0.0,
        tournament_k=3,
        n_islands=n_islands,
        elites_per_island=elites_per_island,
    )
    out = ga_download_population_indices(n_genomes=n_total, n_slots=n_slots)

    assert np.array_equal(out[:n_genomes], seq_out[0])
    assert np.array_equal(out[n_genomes:], seq_out[1])


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_island_migration_runs_matches_sequential():
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_island_boundaries,
        ga_upload_population_indices,
        ga_set_scores,
        ga_island_migration,
        ga_island_migration_runs,
        ga_download_population_indices,
    )

    n_runs = 2
    n_genomes = 32
    n_slots = 9
    n_total = n_runs * n_genomes
    n_islands = 4
    migrate_count = 2

    rng = np.random.default_rng(123)

    pop0 = rng.integers(0, 10_000, size=(n_genomes, n_slots), dtype=np.int32)
    pop1 = rng.integers(100_000, 110_000, size=(n_genomes, n_slots), dtype=np.int32)
    scores0 = rng.integers(0, 1_000_000, size=(n_genomes,), dtype=np.int32)
    scores1 = rng.integers(0, 1_000_000, size=(n_genomes,), dtype=np.int32)

    island_boundaries = np.array([0, 8, 16, 24, 32], dtype=np.int32)

    # Sequential per-run migration.
    seq_out = []
    for pop, scores in [(pop0, scores0), (pop1, scores1)]:
        ga_upload_population_indices(pop, n_slots=n_slots)
        ga_set_scores(scores, n_genomes=n_genomes)
        ga_upload_island_boundaries(island_boundaries)
        ga_island_migration(n_genomes, n_islands, migrate_count, n_slots)
        seq_out.append(ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots))

    # Batched migration.
    batched_pop = np.concatenate([pop0, pop1], axis=0)
    batched_scores = np.concatenate([scores0, scores1], axis=0)
    ga_upload_population_indices(batched_pop, n_slots=n_slots)
    ga_set_scores(batched_scores, n_genomes=n_total)
    ga_island_migration_runs(
        n_runs=n_runs,
        n_genomes_per_run=n_genomes,
        n_islands=n_islands,
        migrate_count=migrate_count,
        n_slots=n_slots,
    )
    out = ga_download_population_indices(n_genomes=n_total, n_slots=n_slots)

    assert np.array_equal(out[:n_genomes], seq_out[0])
    assert np.array_equal(out[n_genomes:], seq_out[1])
