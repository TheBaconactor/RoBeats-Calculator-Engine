import numpy as np
import pytest


pytestmark = pytest.mark.gpu


def test_fg_bellman_fixed_stats_gpu_smoke():
    from gear_optimizer.solver.taichi_gem.force_greats import solve_force_greats_bellman_fixed_stats_gpu

    result = solve_force_greats_bellman_fixed_stats_gpu(
        timestamps=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.float32),
        great_candidate_timestamps=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.float32),
        raw_fever_fill=2.0,
        non_fever_base=2,
        real_fever_time=1.5,
        normal_score_per_note=np.asarray([10, 10, 10, 10, 10, 10], dtype=np.int32),
        fever_score_per_note=np.asarray([20, 20, 20, 20, 20, 20], dtype=np.int32),
        forced_great_penalty_prefix=np.asarray([0, 1, 2, 3, 4, 5, 6], dtype=np.int64),
    )

    assert result.best_score == 78
    assert result.best_delta == 18
    assert result.best_forced_counts == (2, 0)
    assert result.transitions_evaluated == 21
