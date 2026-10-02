import os
import sys

import numpy as np
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


pytestmark = pytest.mark.gpu


def _stage_population(population: np.ndarray, *, n_slots: int = 9) -> None:
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import ensure_ready

    ensure_ready()
    src = np.asarray(population, dtype=np.int32)
    buf = np.zeros((int(fields.MAX_GENOMES), int(fields.MAX_SLOTS)), dtype=np.int32)
    buf[: int(src.shape[0]), : int(n_slots)] = src[:, : int(n_slots)]
    fields.population_indices.from_numpy(buf)


def test_ga_aggregate_genome_stats_kernel_always_aggregates_every_genome():
    from gear_optimizer.solver.taichi_gem.kernels.kernels_helpers import gpu_color_flags
    from gear_optimizer.solver.taichi_gem import fields
    from gear_optimizer.solver.taichi_gem.api import ensure_ready
    from gear_optimizer.solver.taichi_gem.kernel_loader import get_kernels

    ensure_ready()
    kernels = get_kernels()

    _stage_population(np.asarray([[1], [2]], dtype=np.int32), n_slots=1)

    base_fixed = np.zeros((10,), dtype=np.int32)
    fields.base_fixed_stats.from_numpy(base_fixed)

    item_stats = np.zeros((fields.MAX_ITEMS, 10), dtype=np.int32)
    item_stats[1, 0] = 10
    item_stats[2, 0] = 20
    fields.item_stats.from_numpy(item_stats)

    rep_idx = np.zeros((fields.MAX_GENOMES,), dtype=np.int32)
    fields.ga_exact_eval_rep_idx.from_numpy(rep_idx)

    kernels.ga_aggregate_genome_stats_kernel(2, 1, gpu_color_flags(None))

    out = np.asarray(fields.genome_base_stats.to_numpy()[:2], dtype=np.int32)
    assert int(out[0][0]) == 10
    assert int(out[1][0]) == 20
