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







