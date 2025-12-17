"""
Test ga_next_generation_gpu_elites function and verify GPU-resident elitism works correctly.

This test ensures:
1. ga_next_generation_gpu_elites produces valid output (no crashes, correct shapes)
2. Elites are preserved correctly (high-scoring genomes survive)
3. Results match between ga_next_generation (CPU elites) and ga_next_generation_gpu_elites (GPU elites)
"""
import os
import sys
import numpy as np
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_elites_smoke():
    """Basic smoke test for ga_next_generation_gpu_elites."""
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_population_indices,
        ga_seed_rng,
        ga_set_scores,
        ga_next_generation_gpu_elites,
        ga_download_population_indices,
        ga_upload_island_boundaries,
        ga_find_island_elites,
    )

    n_genomes = 64
    n_slots = 9
    n_islands = 4
    elites_per_island = 2

    # Build a population
    pop = np.random.default_rng(123).integers(0, 1000, size=(n_genomes, n_slots), dtype=np.int32)
    ga_upload_population_indices(pop, n_slots=n_slots)

    # Provide fitness scores
    scores = np.arange(n_genomes, dtype=np.int32)
    ga_set_scores(scores, n_genomes=n_genomes)
    ga_seed_rng(n_genomes, seed=42)

    # Upload island boundaries
    island_size = n_genomes // n_islands
    island_starts = np.array([i * island_size for i in range(n_islands)] + [n_genomes], dtype=np.int32)
    ga_upload_island_boundaries(island_starts)

    # Find island elites on GPU
    ga_find_island_elites(n_genomes, n_islands, elites_per_island)

    # Run next generation using GPU-resident elites
    total_elites = n_islands * elites_per_island
    ga_next_generation_gpu_elites(
        n_genomes=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.25,
        tournament_k=3,
        n_elites=total_elites,
    )

    out = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
    assert out.shape == (n_genomes, n_slots)
    assert out.dtype == np.int32
    assert int(out.min()) >= 0
    assert int(out.max()) < 1000


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_elites_preservation():
    """Verify that elite genomes are preserved after ga_next_generation_gpu_elites."""
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_population_indices,
        ga_seed_rng,
        ga_set_scores,
        ga_next_generation_gpu_elites,
        ga_download_population_indices,
        ga_upload_island_boundaries,
        ga_find_island_elites,
    )

    n_genomes = 40
    n_slots = 9
    n_islands = 4
    elites_per_island = 1  # 1 elite per island = 4 total

    # Build a population with distinct elite genomes
    rng = np.random.default_rng(456)
    pop = rng.integers(100, 500, size=(n_genomes, n_slots), dtype=np.int32)
    
    # Make sure top genome per island has unique IDs
    island_size = n_genomes // n_islands
    for isl in range(n_islands):
        elite_idx = (isl + 1) * island_size - 1  # Last genome in each island
        pop[elite_idx, :] = 900 + isl  # Distinct elite values (900, 901, 902, 903)
    
    ga_upload_population_indices(pop, n_slots=n_slots)

    # Give elite genomes the highest scores within their islands
    scores = np.zeros(n_genomes, dtype=np.int32)
    for isl in range(n_islands):
        start = isl * island_size
        end = (isl + 1) * island_size
        scores[start:end] = np.arange(island_size)  # 0-9 within island
    ga_set_scores(scores, n_genomes=n_genomes)
    ga_seed_rng(n_genomes, seed=42)

    # Upload island boundaries
    island_starts = np.array([i * island_size for i in range(n_islands)] + [n_genomes], dtype=np.int32)
    ga_upload_island_boundaries(island_starts)

    # Find elites on GPU
    ga_find_island_elites(n_genomes, n_islands, elites_per_island)

    # Run next generation
    total_elites = n_islands * elites_per_island
    ga_next_generation_gpu_elites(
        n_genomes=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.0,  # No mutation to verify exact preservation
        tournament_k=3,
        n_elites=total_elites,
    )

    out = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
    
    # First n_elites genomes should be the elites (indices 0..3)
    for i in range(total_elites):
        elite_genome = out[i]
        # Each elite should have one of our distinct values (900-903)
        # Check that at least one slot has the elite marker
        assert any(v in [900, 901, 902, 903] for v in elite_genome), \
            f"Elite {i} should have elite marker values, got {elite_genome}"


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_gpu_elites_vs_cpu_elites_parity():
    """
    Verify ga_next_generation_gpu_elites produces the same result as 
    ga_next_generation when given the same elite indices.
    """
    from gear_optimizer.solver.taichi_gem.api import (
        ga_upload_population_indices,
        ga_seed_rng,
        ga_set_scores,
        ga_next_generation,
        ga_next_generation_gpu_elites,
        ga_download_population_indices,
        ga_download_island_elite_indices,
        ga_upload_island_boundaries,
        ga_find_island_elites,
    )

    n_genomes = 32
    n_slots = 9
    n_islands = 2
    elites_per_island = 2

    # Create initial population
    rng = np.random.default_rng(789)
    pop = rng.integers(0, 500, size=(n_genomes, n_slots), dtype=np.int32)
    scores = np.arange(n_genomes, dtype=np.int32)
    island_size = n_genomes // n_islands
    island_starts = np.array([i * island_size for i in range(n_islands)] + [n_genomes], dtype=np.int32)

    # --- CPU-side elites path ---
    ga_upload_population_indices(pop.copy(), n_slots=n_slots)
    ga_set_scores(scores.copy(), n_genomes=n_genomes)
    ga_seed_rng(n_genomes, seed=42)
    ga_upload_island_boundaries(island_starts)
    ga_find_island_elites(n_genomes, n_islands, elites_per_island)
    
    # Download elite indices (CPU path)
    total_elites = n_islands * elites_per_island
    elite_indices = ga_download_island_elite_indices(total_elites)
    
    ga_next_generation(
        n_genomes=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.0,  # No mutation for deterministic comparison
        tournament_k=3,
        elite_count=len(elite_indices),
        elite_indices=elite_indices,
    )
    cpu_out = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)

    # --- GPU-resident elites path ---
    ga_upload_population_indices(pop.copy(), n_slots=n_slots)
    ga_set_scores(scores.copy(), n_genomes=n_genomes)
    ga_seed_rng(n_genomes, seed=42)  # Same seed!
    ga_upload_island_boundaries(island_starts)
    ga_find_island_elites(n_genomes, n_islands, elites_per_island)
    
    ga_next_generation_gpu_elites(
        n_genomes=n_genomes,
        n_slots=n_slots,
        mutation_rate=0.0,
        tournament_k=3,
        n_elites=total_elites,
    )
    gpu_out = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)

    # Compare outputs
    np.testing.assert_array_equal(cpu_out, gpu_out, 
        err_msg="CPU and GPU elite paths should produce identical results")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
