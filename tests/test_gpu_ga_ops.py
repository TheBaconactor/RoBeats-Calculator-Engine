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
def test_gpu_ga_ops_smoke_valid_ranges():
    """
    Smoke test for GPU-side GA operators:
    - can seed RNG
    - can select parents
    - can crossover+mutate
    - result stays within item_id range and preserves shape
    """
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_population_indices,
        ga_seed_rng,
        ga_set_scores,
        ga_next_generation,
        ga_download_population_indices,
    )

    n_genomes = 64
    n_slots = 9

    # Build a small population of item_ids in range [0..1000]
    pop = np.random.default_rng(123).integers(0, 1000, size=(n_genomes, n_slots), dtype=np.int32)
    ga_upload_population_indices(pop, n_slots=n_slots)

    # Provide fitness scores with a clear ordering
    scores = np.arange(n_genomes, dtype=np.int32)
    ga_set_scores(scores, n_genomes=n_genomes)
    ga_seed_rng(n_genomes, seed=42)

    ga_next_generation(
        n_genomes=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.25,
        tournament_k=3,
        elite_count=4,
    )

    out = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
    assert out.shape == (n_genomes, n_slots)
    assert out.dtype == np.int32
    assert int(out.min()) >= 0
    assert int(out.max()) < 1000


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_initial_population_buffer_roundtrip():
    """
    Ensure the multi-start initial population staging path works:
      upload N populations once -> load run_idx -> matches the uploaded IDs.
    """
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_initial_populations,
        ga_load_initial_population,
        ga_download_population_indices,
    )

    n_runs = 3
    n_genomes = 64
    n_slots = 9
    pops = np.random.default_rng(123).integers(0, 1000, size=(n_runs, n_genomes, n_slots), dtype=np.int32)

    ga_upload_initial_populations(pops, n_runs=n_runs, n_genomes=n_genomes, n_slots=n_slots)

    for r in range(n_runs):
        ga_load_initial_population(run_idx=r, n_genomes=n_genomes, n_slots=n_slots)
        out = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
        assert np.array_equal(out, pops[r])


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_ga_next_generation_fused_smoke_valid_ranges():
    """
    Smoke test for the fused GPU next-generation kernel used by the GPU-native GA:
    - runs without error
    - output stays within the original item_id range and preserves shape
    """
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_island_boundaries,
        ga_upload_population_indices,
        ga_seed_rng,
        ga_set_scores,
        ga_next_generation_fused,
        ga_download_population_indices,
    )

    n_genomes = 64
    n_slots = 9

    pop = np.random.default_rng(123).integers(0, 1000, size=(n_genomes, n_slots), dtype=np.int32)
    ga_upload_population_indices(pop, n_slots=n_slots)

    scores = np.arange(n_genomes, dtype=np.int32)
    ga_set_scores(scores, n_genomes=n_genomes)
    ga_seed_rng(n_genomes, seed=42)

    # 4 equal-sized islands of 16 genomes each.
    ga_upload_island_boundaries(np.array([0, 16, 32, 48, 64], dtype=np.int32))

    ga_next_generation_fused(
        n_genomes=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.25,
        immigrant_rate=0.0,
        tournament_k=3,
        n_islands=4,
        elites_per_island=2,
    )

    out = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
    assert out.shape == (n_genomes, n_slots)
    assert out.dtype == np.int32
    assert int(out.min()) >= 0
    assert int(out.max()) < 1000
