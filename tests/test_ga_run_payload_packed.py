import numpy as np
import pytest


pytestmark = pytest.mark.gpu


def _has_taichi() -> bool:
    try:
        import taichi as _  # noqa: F401
    except Exception:
        return False
    return True


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_download_run_payload_matches_individual_downloads():
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import (
        ga_download_population_indices,
        ga_download_results,
        ga_download_run_payload,
        ga_download_scores,
        ga_init_global_best,
    )

    n_genomes = 4
    n_slots = 9

    # Ensure the runtime exists; also resets global best score to a known value.
    ga_init_global_best()

    pop = np.zeros((fields.MAX_GENOMES, fields.MAX_SLOTS), dtype=np.int32)
    pop[:n_genomes, :n_slots] = np.arange(n_genomes * n_slots, dtype=np.int32).reshape(n_genomes, n_slots)
    fields.population_indices.from_numpy(pop)

    scores = np.full((fields.MAX_GENOMES,), -1, dtype=np.int32)
    scores[:n_genomes] = np.array([10, 20, 30, 40], dtype=np.int32)
    fields.ga_scores.from_numpy(scores)

    res = np.zeros((fields.MAX_GENOMES, 7), dtype=np.int32)
    res[:n_genomes, :] = np.array(
        [
            [10, 1, 2, 3, 4, 5, 6],
            [20, 2, 3, 4, 5, 6, 7],
            [30, 3, 4, 5, 6, 7, 8],
            [40, 4, 5, 6, 7, 8, 9],
        ],
        dtype=np.int32,
    )
    fields.genome_result_stats.from_numpy(res)

    fields.ga_global_best_score.from_numpy(np.array([999], dtype=np.int32))
    fields.ga_global_best_genome.from_numpy(np.arange(n_slots, dtype=np.int32) + 100)
    fields.ga_global_best_results.from_numpy(np.array([999, 7, 6, 5, 4, 3, 2], dtype=np.int32))

    (
        best_score,
        best_genome_ids,
        best_results,
        pop_snapshot,
        results_snapshot,
        scores_snapshot,
    ) = ga_download_run_payload(n_genomes=n_genomes, n_slots=n_slots)

    assert best_score == 999
    assert np.array_equal(best_genome_ids, np.arange(n_slots, dtype=np.int32) + 100)
    assert np.array_equal(best_results, np.array([999, 7, 6, 5, 4, 3, 2], dtype=np.int32))

    assert pop_snapshot.shape == (n_genomes, n_slots)
    assert results_snapshot.shape == (n_genomes, 7)
    assert scores_snapshot.shape == (n_genomes,)

    # Baseline downloads (current public API)
    pop2 = ga_download_population_indices(n_genomes=n_genomes, n_slots=n_slots)
    res2 = ga_download_results(n_genomes)
    scores2 = ga_download_scores(n_genomes)

    assert np.array_equal(pop_snapshot, pop2)
    assert np.array_equal(results_snapshot, res2)
    assert np.array_equal(scores_snapshot, scores2)
