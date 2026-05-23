from __future__ import annotations

import numpy as np
import pytest


@pytest.mark.gpu
def test_fg_response_frontier_gpu_build_matches_cpu_reference_small_chart() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu import (
        build_force_greats_response_frontier_gpu,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import build_force_greats_response_frontier

    timestamps = np.asarray([0.0, 0.18, 0.41, 0.64, 0.95, 1.21, 1.5], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0, 0.05, 0.0, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)
    kwargs = dict(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        raw_fever_fill=2.25,
        non_fever_base=7,
        real_fever_time=0.55,
        use_forced_great_timing=True,
    )

    reference = build_force_greats_response_frontier(**kwargs)
    gpu = build_force_greats_response_frontier_gpu(**kwargs)

    assert gpu.first_frontier == reference.first_frontier
    assert gpu.state_frontiers == reference.state_frontiers
    assert gpu.states_evaluated == reference.states_evaluated
    assert gpu.actions == reference.actions
    assert gpu.transitions_evaluated == reference.transitions_evaluated
