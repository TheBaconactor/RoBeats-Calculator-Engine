import numpy as np
import pytest


pytestmark = pytest.mark.gpu


def test_fg_bellman_fixed_stats_gpu_smoke():
    from tests.parity.force_greats.bellman_fixed import solve_force_greats_bellman_fixed_stats_gpu

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

    assert result.best_score == 90
    assert result.best_delta == 30
    assert result.best_forced_counts == (0, 0)
    assert result.states_evaluated == 2
    assert result.transitions_evaluated == 3


def test_fg_bellman_fixed_stats_gpu_prunes_fill_plateaus_without_timing():
    from tests.parity.force_greats.bellman_fixed import solve_force_greats_bellman_fixed_stats_gpu

    result = solve_force_greats_bellman_fixed_stats_gpu(
        timestamps=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.float32),
        great_candidate_timestamps=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.float32),
        raw_fever_fill=2.0,
        non_fever_base=2,
        real_fever_time=1.5,
        normal_score_per_note=np.asarray([10, 10, 10, 10, 10, 10], dtype=np.int32),
        fever_score_per_note=np.asarray([20, 20, 20, 20, 20, 20], dtype=np.int32),
        forced_great_penalty_prefix=np.asarray([0, 1, 2, 3, 4, 5, 6], dtype=np.int64),
        use_forced_great_timing=False,
    )

    assert result.best_score == 90
    assert result.best_delta == 30
    assert result.best_forced_counts == (0, 0)
    assert result.states_evaluated == 2
    assert result.transitions_evaluated == 3


def test_fg_bellman_fixed_stats_gpu_keeps_timing_distinct_plateau_rep():
    from tests.parity.force_greats.bellman_fixed import solve_force_greats_bellman_fixed_stats_gpu

    result = solve_force_greats_bellman_fixed_stats_gpu(
        timestamps=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.float32),
        great_candidate_timestamps=np.asarray([0, 3.9, 2, 3, 4, 5], dtype=np.float32),
        raw_fever_fill=2.0,
        non_fever_base=2,
        real_fever_time=1.2,
        normal_score_per_note=np.asarray([0, 0, 0, 0, 0, 0], dtype=np.int32),
        fever_score_per_note=np.asarray([10, 10, 10, 100, 100, 100], dtype=np.int32),
        forced_great_penalty_prefix=np.asarray([0, 1, 2, 3, 4, 5, 6], dtype=np.int64),
    )

    assert result.best_forced_counts[0] == 2
    assert result.best_score == 308


def test_fg_bellman_fixed_stats_gpu_prunes_same_activation_end_edge():
    from tests.parity.force_greats.bellman_fixed import solve_force_greats_bellman_fixed_stats_gpu

    result = solve_force_greats_bellman_fixed_stats_gpu(
        timestamps=np.asarray([0, 1, 2, 3, 4, 5], dtype=np.float32),
        great_candidate_timestamps=np.asarray([0, 2.2, 2, 3, 4, 5], dtype=np.float32),
        raw_fever_fill=2.0,
        non_fever_base=2,
        real_fever_time=2.1,
        normal_score_per_note=np.asarray([0, 0, 0, 0, 0, 0], dtype=np.int32),
        fever_score_per_note=np.asarray([10, 10, 10, 10, 10, 10], dtype=np.int32),
        forced_great_penalty_prefix=np.asarray([0, 1, 2, 3, 4, 5, 6], dtype=np.int64),
    )

    assert result.best_score == 30
    assert result.transitions_evaluated == 2
