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


pytestmark = pytest.mark.gpu


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_exact_eval_reuse_map_ignores_hints_when_hint_matching_disabled():
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import ensure_ready, ga_upload_population_indices
    from gear_optimizer.solver.taichi_gem.kernel_loader import get_kernels

    ensure_ready()
    kernels = get_kernels()

    pop = np.array(
        [
            [11, 12, 13, 14, 15, 16, 101, 102, 103],
            [11, 12, 13, 14, 15, 16, 101, 102, 103],
            [11, 12, 13, 14, 15, 16, 101, 102, 103],
            [21, 22, 23, 24, 25, 26, 201, 202, 203],
        ],
        dtype=np.int32,
    )
    ga_upload_population_indices(pop, n_slots=9)

    hints = np.zeros((fields.MAX_GENOMES, 4), dtype=np.int32)
    hints[0] = np.array([1, 2, 3, 4], dtype=np.int32)
    hints[1] = np.array([1, 2, 3, 4], dtype=np.int32)
    hints[2] = np.array([1, 2, 3, 5], dtype=np.int32)
    hints[3] = np.array([0, 0, 0, 0], dtype=np.int32)
    fields.genome_hint_allocation.from_numpy(hints)

    kernels.ga_build_exact_eval_reuse_map_kernel(4, 9, 0)
    rep = np.asarray(fields.ga_exact_eval_rep_idx.to_numpy()[:4], dtype=np.int32)
    unique_count = int(fields.ga_exact_eval_unique_count.to_numpy()[0])
    assert rep.tolist() == [0, 0, 0, 3]
    assert unique_count == 2


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_exact_eval_reuse_map_includes_hints_when_requested():
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import ensure_ready, ga_upload_population_indices
    from gear_optimizer.solver.taichi_gem.kernel_loader import get_kernels

    ensure_ready()
    kernels = get_kernels()

    pop = np.array(
        [
            [11, 12, 13, 14, 15, 16, 101, 102, 103],
            [11, 12, 13, 14, 15, 16, 101, 102, 103],
            [11, 12, 13, 14, 15, 16, 101, 102, 103],
            [21, 22, 23, 24, 25, 26, 201, 202, 203],
        ],
        dtype=np.int32,
    )
    ga_upload_population_indices(pop, n_slots=9)

    hints = np.zeros((fields.MAX_GENOMES, 4), dtype=np.int32)
    hints[0] = np.array([1, 2, 3, 4], dtype=np.int32)
    hints[1] = np.array([1, 2, 3, 4], dtype=np.int32)
    hints[2] = np.array([1, 2, 3, 5], dtype=np.int32)
    hints[3] = np.array([0, 0, 0, 0], dtype=np.int32)
    fields.genome_hint_allocation.from_numpy(hints)

    kernels.ga_build_exact_eval_reuse_map_kernel(4, 9, 1)
    rep = np.asarray(fields.ga_exact_eval_rep_idx.to_numpy()[:4], dtype=np.int32)
    unique_count = int(fields.ga_exact_eval_unique_count.to_numpy()[0])
    assert rep.tolist() == [0, 0, 2, 3]
    assert unique_count == 3


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_exact_eval_reuse_propagates_base_stats_only():
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import ensure_ready
    from gear_optimizer.solver.taichi_gem.kernel_loader import get_kernels

    ensure_ready()
    kernels = get_kernels()

    n_genomes = 4

    rep_idx = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
    rep_idx[:n_genomes] = np.array([0, 0, 2, 3], dtype=np.int32)
    fields.ga_exact_eval_rep_idx.from_numpy(rep_idx)

    base_stats = np.zeros((fields.MAX_GENOMES, 7), dtype=np.int32)
    base_stats[0] = np.array([10, 20, 30, 40, 50, 60, 70], dtype=np.int32)
    base_stats[1] = np.array([-1, -1, -1, -1, -1, -1, -1], dtype=np.int32)
    base_stats[2] = np.array([12, 22, 32, 42, 52, 62, 72], dtype=np.int32)
    base_stats[3] = np.array([13, 23, 33, 43, 53, 63, 73], dtype=np.int32)
    fields.genome_base_stats.from_numpy(base_stats)

    result_stats = np.zeros((fields.MAX_GENOMES, 7), dtype=np.int32)
    result_stats[0] = np.array([9001, 1, 2, 3, 4, 5, 6], dtype=np.int32)
    result_stats[1] = np.array([8123, 9, 8, 7, 6, 5, 4], dtype=np.int32)
    result_stats[2] = np.array([7777, 2, 3, 4, 5, 6, 7], dtype=np.int32)
    result_stats[3] = np.array([6666, 3, 4, 5, 6, 7, 8], dtype=np.int32)
    fields.genome_result_stats.from_numpy(result_stats)

    scores = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
    scores[:n_genomes] = np.array([9001, 8123, 7777, 6666], dtype=np.int32)
    fields.ga_scores.from_numpy(scores)

    hints = np.zeros((fields.MAX_GENOMES, 4), dtype=np.int32)
    hints[0] = np.array([5, 4, 3, 2], dtype=np.int32)
    hints[1] = np.array([6, 6, 6, 6], dtype=np.int32)
    hints[2] = np.array([1, 1, 1, 1], dtype=np.int32)
    hints[3] = np.array([2, 2, 2, 2], dtype=np.int32)
    fields.genome_hint_allocation.from_numpy(hints)

    best_results = np.zeros((fields.MAX_GENOMES, 4), dtype=np.int32)
    best_results[0] = np.array([7, 8, 9, 10], dtype=np.int32)
    best_results[1] = np.array([10, 9, 8, 7], dtype=np.int32)
    best_results[2] = np.array([1, 2, 3, 4], dtype=np.int32)
    best_results[3] = np.array([4, 5, 6, 7], dtype=np.int32)
    fields.chunk_best_results.from_numpy(best_results)

    if sys.platform == "darwin":
        best_score = np.full((fields.MAX_GENOMES,), -2147483648, dtype=np.int32)
        best_idx = np.full((fields.MAX_GENOMES,), -1, dtype=np.int32)
        best_score[0] = 9001
        best_idx[0] = 77
        best_score[2] = 7777
        best_idx[2] = 55
        best_score[3] = 6666
        best_idx[3] = 44
        fields.chunk_best_score.from_numpy(best_score)
        fields.chunk_best_idx.from_numpy(best_idx)
    else:
        best_key = np.zeros((fields.MAX_GENOMES,), dtype=np.uint64)
        best_key[0] = np.uint64((9002 << 32) | 77)
        best_key[2] = np.uint64((7778 << 32) | 55)
        best_key[3] = np.uint64((6667 << 32) | 44)
        fields.chunk_best_key.from_numpy(best_key)

    kernels.ga_propagate_exact_eval_reuse_base_stats_kernel(n_genomes)

    out_base = np.asarray(fields.genome_base_stats.to_numpy()[:n_genomes], dtype=np.int32)
    out_results = np.asarray(fields.genome_result_stats.to_numpy()[:n_genomes], dtype=np.int32)
    out_scores = np.asarray(fields.ga_scores.to_numpy()[:n_genomes], dtype=np.int32)
    out_hints = np.asarray(fields.genome_hint_allocation.to_numpy()[:n_genomes], dtype=np.int32)
    out_best_results = np.asarray(fields.chunk_best_results.to_numpy()[:n_genomes], dtype=np.int32)

    assert np.array_equal(out_base[1], out_base[0])
    assert np.array_equal(out_results[1], np.array([8123, 9, 8, 7, 6, 5, 4], dtype=np.int32))
    assert int(out_scores[1]) == 8123
    assert np.array_equal(out_hints[1], np.array([6, 6, 6, 6], dtype=np.int32))
    assert np.array_equal(out_best_results[1], np.array([10, 9, 8, 7], dtype=np.int32))
    assert np.array_equal(out_base[2], np.array([12, 22, 32, 42, 52, 62, 72], dtype=np.int32))

    if sys.platform == "darwin":
        out_best_score = np.asarray(fields.chunk_best_score.to_numpy()[:n_genomes], dtype=np.int32)
        out_best_idx = np.asarray(fields.chunk_best_idx.to_numpy()[:n_genomes], dtype=np.int32)
        assert int(out_best_score[1]) == -2147483648
        assert int(out_best_idx[1]) == -1
    else:
        out_best_key = np.asarray(fields.chunk_best_key.to_numpy()[:n_genomes], dtype=np.uint64)
        assert int(out_best_key[1]) == 0


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_exact_eval_reuse_propagates_chunk_best_outputs():
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import ensure_ready
    from gear_optimizer.solver.taichi_gem.kernel_loader import get_kernels

    ensure_ready()
    kernels = get_kernels()

    n_genomes = 4

    rep_idx = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
    rep_idx[:n_genomes] = np.array([0, 0, 2, 2], dtype=np.int32)
    fields.ga_exact_eval_rep_idx.from_numpy(rep_idx)

    best_results = np.zeros((fields.MAX_GENOMES, 4), dtype=np.int32)
    best_results[0] = np.array([7, 8, 9, 10], dtype=np.int32)
    best_results[2] = np.array([1, 2, 3, 4], dtype=np.int32)
    fields.chunk_best_results.from_numpy(best_results)

    if sys.platform == "darwin":
        best_score = np.full((fields.MAX_GENOMES,), -2147483648, dtype=np.int32)
        best_idx = np.full((fields.MAX_GENOMES,), -1, dtype=np.int32)
        best_score[0] = 9001
        best_idx[0] = 77
        best_score[2] = 7777
        best_idx[2] = 55
        fields.chunk_best_score.from_numpy(best_score)
        fields.chunk_best_idx.from_numpy(best_idx)
    else:
        best_key = np.zeros((fields.MAX_GENOMES,), dtype=np.uint64)
        best_key[0] = np.uint64((9002 << 32) | 77)
        best_key[2] = np.uint64((7778 << 32) | 55)
        fields.chunk_best_key.from_numpy(best_key)

    kernels.ga_propagate_exact_eval_reuse_chunk_best_kernel(n_genomes)

    out_best_results = np.asarray(fields.chunk_best_results.to_numpy()[:n_genomes], dtype=np.int32)
    assert np.array_equal(out_best_results[1], np.array([7, 8, 9, 10], dtype=np.int32))
    assert np.array_equal(out_best_results[3], np.array([1, 2, 3, 4], dtype=np.int32))

    if sys.platform == "darwin":
        out_best_score = np.asarray(fields.chunk_best_score.to_numpy()[:n_genomes], dtype=np.int32)
        out_best_idx = np.asarray(fields.chunk_best_idx.to_numpy()[:n_genomes], dtype=np.int32)
        assert int(out_best_score[1]) == 9001
        assert int(out_best_idx[1]) == 77
        assert int(out_best_score[3]) == 7777
        assert int(out_best_idx[3]) == 55
    else:
        out_best_key = np.asarray(fields.chunk_best_key.to_numpy()[:n_genomes], dtype=np.uint64)
        assert int(out_best_key[1]) == int(np.uint64((9002 << 32) | 77))
        assert int(out_best_key[3]) == int(np.uint64((7778 << 32) | 55))


@pytest.mark.skipif(not _has_taichi(), reason="Taichi not available")
def test_ga_aggregate_and_init_best_kernel_ignores_stale_representatives_when_reuse_disabled():
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import ensure_ready, ga_upload_population_indices
    from gear_optimizer.solver.taichi_gem.kernel_loader import get_kernels

    ensure_ready()
    kernels = get_kernels()

    ga_upload_population_indices(np.asarray([[1], [2]], dtype=np.int32), n_slots=1)

    base_fixed = np.zeros((10,), dtype=np.int32)
    fields.base_fixed_stats.from_numpy(base_fixed)

    item_stats = np.zeros((fields.MAX_ITEMS, 10), dtype=np.int32)
    item_stats[1, 0] = 10
    item_stats[2, 0] = 20
    fields.item_stats.from_numpy(item_stats)

    rep_idx = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
    fields.ga_exact_eval_rep_idx.from_numpy(rep_idx)

    kernels.ga_aggregate_and_init_best_kernel(2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    out = np.asarray(fields.genome_base_stats.to_numpy()[:2], dtype=np.int32)
    assert int(out[0][0]) == 10
    assert int(out[1][0]) == 20

