import numpy as np
import pytest


pytestmark = pytest.mark.gpu


def test_ga_update_global_best_is_consistent():
    from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready
    from gear_optimizer.solver.taichi_gem.api.ga_operations import (
        ga_download_global_best,
        ga_init_global_best,
        ga_update_global_best,
    )
    from gear_optimizer.solver.taichi_gem import fields

    ensure_ready()

    n_genomes = 512
    n_slots = 9

    max_genomes = int(fields.MAX_GENOMES)
    max_slots = int(fields.MAX_SLOTS)

    scores_full = np.zeros((max_genomes,), dtype=np.int32)
    pop_full = np.zeros((max_genomes, max_slots), dtype=np.int32)
    res_full = np.zeros((max_genomes, 7), dtype=np.int32)

    for g in range(n_genomes):
        pop_full[g, :n_slots] = g

    rng = np.random.default_rng(0)
    scores = rng.integers(low=0, high=1000, size=n_genomes, dtype=np.int32)
    max_idx = int(rng.integers(0, n_genomes))
    scores[max_idx] = 2000

    scores_full[:n_genomes] = scores
    res_full[:n_genomes, 0] = scores

    fields.ga_scores.from_numpy(scores_full)
    fields.population_indices.from_numpy(pop_full)
    fields.genome_result_stats.from_numpy(res_full)

    ga_init_global_best()
    ga_update_global_best(n_genomes=n_genomes, n_slots=n_slots)
    best_score, best_genome_ids, best_results = ga_download_global_best()

    assert best_score == int(scores[max_idx])
    assert int(best_results[0]) == best_score
    assert np.all(best_genome_ids[:n_slots] == max_idx)
