import numpy as np
import pytest

from gear_optimizer.solver.timing_envelope import FRAME_MARGIN_MS, precise_envelopes


def test_same_lane_constraints_propagate_through_intervening_lanes():
    ts = np.asarray([1.0, 1.005, 1.010, 1.015], dtype=np.float32)
    nt = np.ones(4, dtype=np.int16)
    lanes = np.asarray([0, 1, 0, 1], dtype=np.int32)
    env = precise_envelopes(ts, nt, "frame_robust", lanes=lanes)
    gap = (FRAME_MARGIN_MS + 0.001) / 1000.0
    for floor in (env.perfect_floor, env.great_floor):
        assert np.all(np.diff(floor) >= 0)
        assert float(floor[2]) - float(floor[0]) >= gap
        assert float(floor[3]) - float(floor[1]) >= gap
    assert float(env.exit_ceiling[2]) - float(env.exit_ceiling[0]) >= gap
    assert float(env.exit_ceiling[3]) - float(env.exit_ceiling[1]) >= gap


def test_hold_release_needs_no_same_lane_press_gap():
    ts = np.asarray([1.0, 1.001], dtype=np.float32)
    nt = np.asarray([2, 3], dtype=np.int16)
    lanes = np.zeros(2, dtype=np.int32)
    env = precise_envelopes(ts, nt, "frame_robust", lanes=lanes)
    assert float(env.perfect_floor[1]) - float(env.perfect_floor[0]) < FRAME_MARGIN_MS / 1000.0


@pytest.mark.parametrize("lanes, note_types", [([0, 1, 0], [1, 1, 1]), ([0, 1, 1], [1, 1, 1]), ([0, 1, 0], [2, 1, 3])])
def test_late_activation_respects_conditional_follower_lane_bounds(lanes, note_types):
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import _numba_late_great_activation_hit_for_run

    ts = np.asarray([1.0, 1.15, 1.15], dtype=np.float32)
    env = precise_envelopes(ts, np.asarray(note_types), "frame_robust", lanes=np.asarray(lanes))
    hit, valid = _numba_late_great_activation_hit_for_run(
        0, ts, env.perfect_candidates, env.great_candidates, env.late_great_floor, 0, 2, 3, env.lane_bounds
    )
    gap = float(env.lane_bounds[2, 1])
    assert valid
    assert hit == pytest.approx(min(float(env.great_candidates[0]), float(env.perfect_candidates[2]) - gap), abs=1e-7)


def test_frame_robust_envelopes_require_lanes():
    ts = np.asarray([1.0, 1.010], dtype=np.float32)
    nt = np.ones(2, dtype=np.int16)
    with pytest.raises(ValueError, match="require chart lanes"):
        precise_envelopes(ts, nt, "frame_robust")


def test_fever_reach_is_conditioned_on_the_activation_lane_chain():
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import _numba_lane_chain_end_table

    ts = np.arange(12, dtype=np.float32) * np.float32(0.02)
    env = precise_envelopes(ts, np.ones(12), "frame_robust", lanes=np.zeros(12))
    ends = _numba_lane_chain_end_table(12, env.lane_bounds, np.asarray([0.01, 0.14]))
    assert ends[:, 0].tolist() == [1, 8]
    assert ends[:, 3].tolist() == [4, 11]
