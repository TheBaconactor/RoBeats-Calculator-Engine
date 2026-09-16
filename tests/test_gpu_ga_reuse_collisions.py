"""Device-level exact keys, collision ownership, and complete-result reuse."""

import numpy as np
import pytest

pytest.importorskip("taichi")

from gear_optimizer.solver.taichi_gem import fields, kernels
from gear_optimizer.solver.taichi_gem.api.ga_operations import reset_ga_evaluation_cache
from gear_optimizer.solver.taichi_gem.api.initialization import ensure_ready

pytestmark = pytest.mark.gpu


def _prepare(stats):
    ensure_ready()
    values = np.zeros((fields.MAX_GENOMES, 7), dtype=np.int16)
    values[:len(stats)] = stats
    fields.genome_base_stats.from_numpy(values)
    fields.chunk_best_key.fill(0)
    fields.chunk_best_results.fill(0)
    kernels.ga_compute_exact_eval_rep_kernel(len(stats))
    kernels.ga_build_unique_slot_table_kernel(len(stats))
    return fields.ga_exact_eval_rep_idx.to_numpy()[:len(stats)]


def _publish(n):
    keys = np.zeros(fields.MAX_GENOMES, dtype=np.uint64)
    keys[:n] = ((np.arange(n, dtype=np.uint64) + 123) << 32) | np.arange(n, dtype=np.uint64)
    gems = np.zeros((fields.MAX_GENOMES, 4), dtype=np.int32)
    gems[:n] = np.arange(n * 4).reshape(n, 4)
    fields.chunk_best_key.from_numpy(keys)
    fields.chunk_best_results.from_numpy(gems)
    kernels.ga_scatter_dup_results_kernel(n)
    return fields.chunk_best_key.to_numpy()[:n], fields.chunk_best_results.to_numpy()[:n]


def test_all_seven_stats_distinguish_misses_and_duplicates():
    ensure_ready()
    reset_ga_evaluation_cache()
    stats = np.tile(np.array([-10, 0, 160, 32767, -32768, 19, 80]), (9, 1))
    for col in range(7):
        stats[col + 1, col] += -1 if col == 3 else 1
    reps = _prepare(stats)
    np.testing.assert_array_equal(reps, [0, 1, 2, 3, 4, 5, 6, 7, 0])
    keys, gems = _publish(9)
    assert keys[8] == keys[0]
    np.testing.assert_array_equal(gems[8], gems[0])
    _prepare(stats[[0, 8]])
    assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == 0
    np.testing.assert_array_equal(fields.chunk_best_key.to_numpy()[:2], keys[[0, 8]])
    np.testing.assert_array_equal(fields.chunk_best_results.to_numpy()[:2], gems[[0, 8]])


def test_hash_collision_never_reuses_another_stat_tuple():
    ensure_ready()
    reset_ga_evaluation_cache()
    # FNV low 14 bits collide when the final input differs by 2**14.
    a = [0] * 7
    b = [0] * 6 + [16384]
    _prepare([a])
    a_keys, a_gems = _publish(1)
    _prepare([b])
    assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == 1
    assert int(fields.chunk_best_key.to_numpy()[0]) == 0
    # Simultaneous colliding misses publish exactly one coherent winner.
    reset_ga_evaluation_cache()
    _prepare([a, b])
    _publish(2)
    _prepare([b, a])
    assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == 1
    assert int(fields.chunk_best_key.to_numpy()[0]) == 0
    assert int(fields.chunk_best_key.to_numpy()[1]) == int(a_keys[0])
    np.testing.assert_array_equal(fields.chunk_best_results.to_numpy()[1], a_gems[0])


def test_missing_winner_is_never_cached():
    ensure_ready()
    reset_ga_evaluation_cache()
    _prepare([[0] * 7])
    kernels.ga_scatter_dup_results_kernel(1)
    _prepare([[0] * 7])
    assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == 1


def test_full_population_collisions_keep_keys_and_gems_together():
    ensure_ready()
    reset_ga_evaluation_cache()
    n = fields.MAX_GENOMES
    indices = np.arange(n)
    stats = np.zeros((n, 7), dtype=np.int16)
    # Every adjacent pair shares a bucket but has distinct full stats.
    stats[:, 6] = indices // 2 + (indices % 2) * 16384
    np.testing.assert_array_equal(_prepare(stats), indices)
    keys, gems = _publish(n)
    _prepare(stats[::-1])
    restored = fields.chunk_best_key.to_numpy()[:n]
    hits = restored != 0
    assert int(hits.sum()) == (n + 1) // 2
    assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == n // 2
    np.testing.assert_array_equal(restored[hits], keys[::-1][hits])
    np.testing.assert_array_equal(fields.chunk_best_results.to_numpy()[:n][hits], gems[::-1][hits])


def test_runtime_reset_discards_cached_winners():
    from gear_optimizer.solver.taichi_gem.api.initialization import hard_reset_taichi

    _prepare([[0] * 7])
    _publish(1)
    assert np.any(fields.ga_eval_cache_key.to_numpy())
    hard_reset_taichi(reason="test evaluation cache lifecycle")
    _prepare([[0] * 7])
    assert int(fields.ga_exact_eval_unique_count.to_numpy()[0]) == 1
    assert not np.any(fields.ga_eval_cache_key.to_numpy())
