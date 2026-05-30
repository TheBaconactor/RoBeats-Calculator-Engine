from __future__ import annotations

import numpy as np
import pytest


def test_fg_response_first_frontier_reducer_uses_one_canonical_chunk() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu

    action_row = np.asarray([1, 2, 3, 4], dtype=np.int32)
    items = [(idx, 0, 1.0, action_row, action_row, action_row, action_row) for idx in range(5)]

    chunks = response_build_gpu._first_only_chunks(n=10, items=items)

    assert chunks == [(0, items)]
    assert not hasattr(response_build_gpu, "_FIRST_ONLY_REDUCER_BATCH_MAX_BYTES")


def test_fg_response_first_frontier_reducer_thread_count_is_capped() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu

    previous = response_build_gpu.configure_force_greats_response_first_frontier_threads(9999)
    try:
        assert 1 <= response_build_gpu._resolve_first_only_reducer_threads(9999) <= 8
        response_build_gpu.configure_force_greats_response_first_frontier_threads(0)
        assert response_build_gpu._resolve_first_only_reducer_threads(9999) == 1
        response_build_gpu.configure_force_greats_response_first_frontier_threads(4)
        assert response_build_gpu._resolve_first_only_reducer_threads(2) == 2
    finally:
        response_build_gpu.configure_force_greats_response_first_frontier_threads(previous)


def test_fg_response_first_frontier_reducer_executor_uses_normal_worker_priority(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu

    calls: list[int] = []

    class FakeExecutor:
        def __init__(self, **kwargs):
            calls.append(int(kwargs["max_workers"]))
            self.kwargs = dict(kwargs)

        def __enter__(self):
            assert "initializer" not in self.kwargs
            assert self.kwargs.get("thread_name_prefix") == "FGFirstFrontier"
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(response_build_gpu.concurrent.futures, "ThreadPoolExecutor", FakeExecutor)

    with response_build_gpu._first_frontier_reducer_executor(3):
        pass

    assert calls == [3]


def test_fg_response_first_frontier_reducer_warmup_is_single_owner(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    result = FgResponseFrontierResult((surface,), {}, 1, 1, 1, 1, 1, 1, 0, 0.0)
    calls: list[dict] = []
    previous = response_build_gpu._FIRST_FRONTIER_REDUCER_WARMED

    def _fake_build(**kwargs):
        calls.append(dict(kwargs))
        return (result,)

    monkeypatch.setattr(response_build_gpu, "_FIRST_FRONTIER_REDUCER_WARMED", False)
    monkeypatch.setattr(response_build_gpu, "build_force_greats_response_first_frontiers_gpu_batch", _fake_build)
    try:
        response_build_gpu.warm_force_greats_response_first_frontier_reducer()
        response_build_gpu.warm_force_greats_response_first_frontier_reducer()
    finally:
        monkeypatch.setattr(response_build_gpu, "_FIRST_FRONTIER_REDUCER_WARMED", previous)

    assert len(calls) == 1
    assert calls[0]["geometries"] == ((1.0, 2, 0.2),)
    assert calls[0]["use_forced_great_timing"] is True


def test_fg_response_first_frontier_canonicalizes_equivalent_geometries(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    result = FgResponseFrontierResult((surface,), {}, 1, 4, 0, 1, 1, 1, 3, 0.0)
    calls: list[dict] = []
    previous_threads = response_build_gpu.configure_force_greats_response_first_frontier_threads(1)

    def _fake_first_frontier(**kwargs):
        calls.append(dict(kwargs))
        return result

    monkeypatch.setattr(response_build_gpu, "_first_frontier_result_from_precomputed_end_indices", _fake_first_frontier)
    try:
        frontiers = response_build_gpu.build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            great_candidate_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            geometries=((2.1, 3, 10.0), (2.2, 3, 11.0)),
            use_forced_great_timing=True,
        )
    finally:
        response_build_gpu.configure_force_greats_response_first_frontier_threads(previous_threads)

    assert len(calls) == 1
    assert len(frontiers) == 2
    assert frontiers[0] is frontiers[1]


@pytest.mark.gpu
def test_fg_response_frontier_gpu_build_matches_cpu_reference_small_chart() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu import build_force_greats_response_frontiers_gpu_batch
    from tests.parity.fg_response_frontier_cpu import build_force_greats_response_frontier

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
    geometry = (2.25, 7, 0.55)

    reference = build_force_greats_response_frontier(**kwargs)
    gpu = build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=(geometry,),
        use_forced_great_timing=True,
    )[0]

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
def test_fg_response_frontier_gpu_batch_materializes_state_frontiers() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu import build_force_greats_response_frontiers_gpu_batch

    timestamps = np.asarray([0.0, 0.18, 0.41, 0.64, 0.95, 1.21, 1.5], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0, 0.05, 0.0, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)
    geometry = (2.25, 7, 0.55)

    frontier = build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=(geometry,),
        use_forced_great_timing=True,
    )[0]

    assert frontier.first_frontier
    assert frontier.state_frontiers


@pytest.mark.gpu
def test_fg_response_frontier_gpu_sparse_body_materializes_state_frontiers() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu import (
        build_force_greats_response_frontiers_gpu_batch,
    )

    timestamps = np.asarray([float(idx) * 0.11 for idx in range(140)], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0 if idx % 3 else 0.025 for idx in range(140)], dtype=np.float32)
    geometries = (
        (101.25, 108, 0.72),
        (103.5, 112, 0.91),
    )

    frontiers = build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )

    assert all(frontier.first_frontier for frontier in frontiers)
    assert all(frontier.state_frontiers for frontier in frontiers)


@pytest.mark.gpu
def test_fg_response_first_frontier_batch_uses_slim_exact_route(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu

    timestamps = np.asarray([float(idx) * 0.11 for idx in range(140)], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0 if idx % 3 else 0.025 for idx in range(140)], dtype=np.float32)
    geometries = ((101.25, 108, 0.72),)

    full = response_build_gpu.build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )

    def _reject_full_state_reducer(**_kwargs):
        raise AssertionError("first-frontier cache route must not materialize full state frontiers")

    monkeypatch.setattr(response_build_gpu, "_frontier_from_edge_arrays", _reject_full_state_reducer)
    slim = response_build_gpu.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )

    assert tuple(frontier.first_frontier for frontier in slim) == tuple(frontier.first_frontier for frontier in full)
    assert all(not frontier.state_frontiers for frontier in slim)


@pytest.mark.gpu
def test_fg_response_first_frontier_batch_matches_full_state_head_route() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu

    timestamps = np.asarray([float(idx) * 0.11 for idx in range(60)], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0 if idx % 3 else 0.025 for idx in range(60)], dtype=np.float32)
    geometries = ((2.25, 7, 0.55),)

    full = response_build_gpu.build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )
    slim = response_build_gpu.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )

    assert slim[0].first_frontier == full[0].first_frontier
    assert not slim[0].state_frontiers


@pytest.mark.gpu
def test_fg_response_counts_reconstruct_from_slim_first_frontier() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _EMPTY_SURFACE,
        _action_table,
        _combine,
        _edge_surface_options,
        reconstruct_force_greats_response_counts,
    )

    timestamps = np.asarray([0.0, 0.18, 0.41, 0.64, 0.95, 1.21, 1.5], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0, 0.05, 0.0, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)
    raw_fever_fill = 2.25
    non_fever_base = 7
    real_fever_time = 0.55
    full = response_build_gpu.build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=((raw_fever_fill, non_fever_base, real_fever_time),),
        use_forced_great_timing=True,
    )[0]
    slim = response_build_gpu.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=((raw_fever_fill, non_fever_base, real_fever_time),),
        use_forced_great_timing=True,
    )[0]
    target = full.first_frontier[-1]

    counts = reconstruct_force_greats_response_counts(
        frontier=slim,
        target_surface=target,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
        use_forced_great_timing=True,
    )

    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=raw_fever_fill,
        non_fever_base=non_fever_base,
        use_forced_great_timing=True,
    )
    state = 0
    first = True
    surface = _EMPTY_SURFACE
    for count in counts:
        edge_match = None
        for k, next_state, edge in _edge_surface_options(
            i=state,
            first=first,
            n=int(timestamps.shape[0]),
            actions=actions,
            later_fill=later_fill,
            first_fill=first_fill,
            later_forced=later_forced,
            first_forced=first_forced,
            real_fever_time=real_fever_time,
            use_forced_great_timing=True,
            timestamps=timestamps,
            great_candidate_timestamps=great_candidates,
        ):
            if int(k) == int(count):
                edge_match = (int(next_state), edge)
                break
        assert edge_match is not None
        state, edge = edge_match
        surface = _combine(surface, edge)
        first = False

    assert surface == target
