from __future__ import annotations

import numpy as np
import pytest


@pytest.mark.gpu
def test_fg_response_frontier_gpu_build_matches_cpu_reference_small_chart() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu import (
        build_force_greats_response_frontier_gpu,
        build_force_greats_response_frontiers_gpu_batch,
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

    geometries = (
        (2.25, 7, 0.55),
        (2.25, 7, 0.8),
        (1.4, 5, 0.55),
    )
    references = tuple(
        build_force_greats_response_frontier(
            timestamps=timestamps,
            great_candidate_timestamps=great_candidates,
            raw_fever_fill=raw_fill,
            non_fever_base=non_fever_base,
            real_fever_time=real_fever_time,
            use_forced_great_timing=True,
        )
        for raw_fill, non_fever_base, real_fever_time in geometries
    )
    batch = build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )

    assert tuple(frontier.first_frontier for frontier in batch) == tuple(
        frontier.first_frontier for frontier in references
    )
    assert tuple(frontier.state_frontiers for frontier in batch) == tuple(
        frontier.state_frontiers for frontier in references
    )


@pytest.mark.gpu
def test_fg_response_frontier_gpu_first_only_matches_full_first_frontier() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu import (
        build_force_greats_response_frontier_gpu,
    )

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

    full = build_force_greats_response_frontier_gpu(**kwargs, include_state_frontiers=True)
    first_only = build_force_greats_response_frontier_gpu(**kwargs, include_state_frontiers=False)

    assert set(first_only.first_frontier) == set(full.first_frontier)
    assert first_only.state_frontiers == {}


@pytest.mark.gpu
def test_fg_response_frontier_gpu_sparse_body_first_only_matches_full_first_frontier() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu import (
        build_force_greats_response_frontiers_gpu_batch,
    )

    timestamps = np.asarray([float(idx) * 0.11 for idx in range(140)], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0 if idx % 3 else 0.025 for idx in range(140)], dtype=np.float32)
    geometries = (
        (101.25, 108, 0.72),
        (103.5, 112, 0.91),
    )

    full = build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
        include_state_frontiers=True,
    )
    first_only = build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
        include_state_frontiers=False,
    )

    assert tuple(set(frontier.first_frontier) for frontier in first_only) == tuple(
        set(frontier.first_frontier) for frontier in full
    )
    assert all(frontier.state_frontiers == {} for frontier in first_only)
