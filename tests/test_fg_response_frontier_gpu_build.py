from __future__ import annotations

import os

import numpy as np
import pytest


def test_fg_response_first_frontier_reducer_uses_one_canonical_chunk() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_precompute

    action_row = np.asarray([1, 2, 3, 4], dtype=np.int32)
    items = [(idx, 0, 1.0, action_row, action_row, action_row, action_row) for idx in range(5)]

    chunks = response_build_gpu_precompute._first_only_chunks(n=10, items=items)

    assert chunks == [(0, items)]
    assert not hasattr(response_build_gpu_precompute, "_FIRST_ONLY_REDUCER_BATCH_MAX_BYTES")


def test_fg_response_first_frontier_reducer_thread_count_is_capped() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_reducer

    previous = response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(9999)
    try:
        cpu_count = max(1, int(os.cpu_count() or 1))
        assert 1 <= response_build_gpu_reducer._resolve_first_only_reducer_threads(9999) <= cpu_count
        response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(0)
        assert response_build_gpu_reducer._resolve_first_only_reducer_threads(9999) == 1
        response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(4)
        assert response_build_gpu_reducer._resolve_first_only_reducer_threads(2) == 2
    finally:
        response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(previous)


def test_fg_response_first_frontier_reducer_executor_uses_normal_worker_priority(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_reducer

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

    monkeypatch.setattr(response_build_gpu_reducer.concurrent.futures, "ThreadPoolExecutor", FakeExecutor)

    with response_build_gpu_reducer._first_frontier_reducer_executor(3):
        pass

    assert calls == [3]


def test_fg_response_first_frontier_reducer_has_no_public_warmup_route() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_reducer

    assert not hasattr(response_build_gpu_reducer, "warm_force_greats_response_first_frontier_reducer")


def test_fg_response_first_frontier_canonicalizes_equivalent_geometries(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_batch, response_build_gpu_reducer
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    result = FgResponseFrontierResult((surface,), {}, 1, 4, 0, 1, 1, 1, 3, 0.0)
    calls: list[dict] = []
    previous_threads = response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(1)

    def _fake_first_frontier(**kwargs):
        calls.append(dict(kwargs))
        return result

    monkeypatch.setattr(
        response_build_gpu_reducer,
        "_first_frontier_result_from_precomputed_end_indices",
        _fake_first_frontier,
    )
    try:
        frontiers = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            great_candidate_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            geometries=((2.1, 3, 10.0), (2.2, 3, 11.0)),
            use_forced_great_timing=True,
        )
    finally:
        response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(previous_threads)

    assert len(calls) == 1
    assert len(frontiers) == 2
    assert frontiers[0] is frontiers[1]


def test_fg_response_first_frontier_reuses_canonical_end_indices(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import (
        response_build_gpu_batch,
        response_build_gpu_precompute,
        response_build_gpu_reducer,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    surface = FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    result = FgResponseFrontierResult((surface,), {}, 1, 4, 0, 1, 1, 1, 3, 0.0)
    calls = 0
    real_precompute = response_build_gpu_precompute._precompute_end_indices
    previous_threads = response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(1)

    def _record_precompute(**kwargs):
        nonlocal calls
        calls += 1
        return real_precompute(**kwargs)

    def _fake_first_frontier(**_kwargs):
        return result

    monkeypatch.setattr(response_build_gpu_precompute, "_precompute_end_indices", _record_precompute)
    monkeypatch.setattr(
        response_build_gpu_reducer,
        "_first_frontier_result_from_precomputed_end_indices",
        _fake_first_frontier,
    )
    try:
        frontiers = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            great_candidate_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            geometries=((2.1, 3, 10.0), (2.2, 3, 11.0)),
            use_forced_great_timing=True,
        )
    finally:
        response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(previous_threads)

    assert calls == 1
    assert len(frontiers) == 2


def test_fg_response_first_frontier_emits_activation_great_head_overlap() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    great_candidates = np.asarray([0.0, 1.0, 2.5, 3.0, 4.0], dtype=np.float32)

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=((2.25, 3, 1.0),),
        use_forced_great_timing=True,
    )[0]

    assert any((int(surface.fever0) & int(surface.great0)) != 0 for surface in frontier.first_frontier)


def test_fg_response_first_frontier_emits_optimized_perfect_activation_edge() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    perfect_candidates = timestamps.copy()
    perfect_candidates[2] = np.float32(2.5)
    great_candidates = timestamps.copy()

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        geometries=((2.25, 3, 1.0),),
        use_forced_great_timing=True,
    )[0]

    target = next(
        surface
        for surface in frontier.first_frontier
        if int(surface.fever0) == 0b1100 and int(surface.great0) == 0
    )
    trace = reconstruct_force_greats_response_trace(
        frontier=frontier,
        target_surface=target,
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        raw_fever_fill=2.25,
        real_fever_time=1.0,
        use_forced_great_timing=True,
    )

    assert trace[0]["activation_judgment"] == "perfect"
    assert trace[0]["fever_start_source"] == "perfect_window"
    assert trace[0]["activation_hit_offset_ms"] == pytest.approx(500.0)


def test_fg_response_late_great_activation_is_dominated_when_perfect_reaches_same_end() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 3.4, 4.0], dtype=np.float32)
    perfect_candidates = timestamps.copy()
    perfect_candidates[2] = np.float32(2.5)
    great_candidates = timestamps.copy()
    great_candidates[2] = np.float32(2.5)

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        geometries=((2.25, 3, 1.0),),
        use_forced_great_timing=True,
    )[0]

    assert any(int(surface.fever0) == 0b11100 and int(surface.great0) == 0 for surface in frontier.first_frontier)
    assert not any(
        int(surface.fever0) == 0b11100 and (int(surface.great0) & 0b00100)
        for surface in frontier.first_frontier
    )


def test_fg_response_late_great_activation_counts_when_it_beats_optimized_perfect() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 3.4, 4.0], dtype=np.float32)
    perfect_candidates = timestamps.copy()
    perfect_candidates[2] = np.float32(2.1)
    great_candidates = timestamps.copy()
    great_candidates[2] = np.float32(2.5)

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        geometries=((2.25, 3, 1.0),),
        use_forced_great_timing=True,
    )[0]

    assert any(
        int(surface.fever0) == 0b11100
        and (int(surface.great0) & 0b00100)
        and (int(surface.fever0) & int(surface.great0) & 0b00100)
        for surface in frontier.first_frontier
    )


def test_force_greats_replay_uses_optimized_perfect_activation_edge() -> None:
    from gear_optimizer.solver.scoring.exact_rescore import _compute_force_greats_timeline

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    perfect_candidates = timestamps.copy()
    perfect_candidates[2] = np.float32(2.5)
    great_candidates = timestamps.copy()

    (
        fever_mask_head,
        _count_body_fever,
        _count_body_normal,
        non_fever_base,
        _section_details,
    ) = _compute_force_greats_timeline(
        timestamps,
        perfect_candidates,
        great_candidates,
        int(timestamps.shape[0]),
        1.5,
        4.0 / 3.0,
        0,
        4.0,
        [],
        clamp_base_notes_nonnegative=True,
        clamp_forced_to_section_notes=True,
        use_forced_great_timing=True,
    )

    assert non_fever_base == 3
    assert fever_mask_head.tolist() == [False, False, True, True, False]


def test_fg_response_first_frontier_emits_activation_great_body_overlap() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    timestamps = np.asarray([float(idx) for idx in range(110)], dtype=np.float32)
    great_candidates = timestamps.copy()
    great_candidates[102] = np.float32(102.5)

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=((102.25, 103, 1.0),),
        use_forced_great_timing=True,
    )[0]

    assert any(int(surface.body_fever_great) > 0 for surface in frontier.first_frontier)


def test_fg_response_edge_end_does_not_let_prefix_great_carry_perfect_activation() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _edge_end

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    great_candidates = timestamps.copy()
    great_candidates[0] = np.float32(2.4)
    great_candidates[1] = np.float32(1.1)

    edge_end, start_time, carry_idx = _edge_end(
        n=int(timestamps.shape[0]),
        a=2,
        activation_great=False,
        real_fever_time=1.0,
        use_forced_great_timing=True,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
    )

    assert edge_end == 3
    assert start_time == pytest.approx(2.0)
    assert carry_idx == -1


def test_fg_response_numba_edge_end_does_not_let_prefix_great_carry_perfect_activation() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_edge_end_idx_precomputed,
    )

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    great_candidates = timestamps.copy()
    great_candidates[0] = np.float32(2.4)
    great_candidates[1] = np.float32(1.1)
    timestamp_end_idx = np.searchsorted(timestamps, timestamps + np.float32(1.0), side="left").astype(np.int32)
    great_end_idx = np.searchsorted(timestamps, great_candidates + np.float32(1.0), side="left").astype(np.int32)

    edge_end, start_time = _numba_edge_end_idx_precomputed(
        int(timestamps.shape[0]),
        2,
        0,
        1,
        timestamps,
        great_candidates,
        timestamp_end_idx.reshape(1, -1),
        great_end_idx.reshape(1, -1),
        0,
    )

    assert edge_end == 3
    assert start_time == pytest.approx(2.0)


def test_fg_response_activation_great_requires_same_fill_ordinal() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _action_table,
        _edge_surface_options,
    )

    timestamps = np.asarray([float(idx) for idx in range(8)], dtype=np.float32)
    great_candidates = timestamps.copy()
    great_candidates[3] = np.float32(3.5)
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=2.0,
        non_fever_base=7,
        use_forced_great_timing=True,
    )

    options = _edge_surface_options(
        i=0,
        first=False,
        n=int(timestamps.shape[0]),
        actions=actions,
        later_fill=later_fill,
        first_fill=first_fill,
        later_forced=later_forced,
        first_forced=first_forced,
        real_fever_time=1.0,
        use_forced_great_timing=True,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
    )

    assert not any(int(k) == 1 and int(next_state) == 5 for k, next_state, _surface in options)


def test_fg_response_branch_a_prunes_body_dominated_fever_great_overlap() -> None:
    from numba.typed import List

    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _NUMBA_SURFACE_TYPE,
        _numba_append_branch_a_body_prefix_surface,
    )

    bucket = List.empty_list(_NUMBA_SURFACE_TYPE)
    width = 8
    values = np.zeros((width * width,), dtype=np.int32)
    stamps = np.zeros((width * width,), dtype=np.int32)

    assert _numba_append_branch_a_body_prefix_surface(
        bucket,
        0,
        np.uint64(10),
        np.uint64(1),
        np.uint64(0),
        values,
        stamps,
        1,
        width,
    )
    assert not _numba_append_branch_a_body_prefix_surface(
        bucket,
        0,
        np.uint64(9),
        np.uint64(3),
        np.uint64(1),
        values,
        stamps,
        1,
        width,
    )
    assert _numba_append_branch_a_body_prefix_surface(
        bucket,
        0,
        np.uint64(9),
        np.uint64(0),
        np.uint64(0),
        values,
        stamps,
        1,
        width,
    )

    assert list(bucket) == [
        (0, 0, 0, 0, 10, 1, 0),
        (0, 0, 0, 0, 9, 0, 0),
    ]


def test_fg_response_reducer_prunes_body_dominated_same_head_overlap() -> None:
    from numba.typed import List

    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _NUMBA_SURFACE_TYPE,
        _numba_reduce,
    )

    surfaces = List.empty_list(_NUMBA_SURFACE_TYPE)
    surfaces.append(tuple(np.uint64(v) for v in (0, 0, 0, 0, 10, 1, 0)))
    surfaces.append(tuple(np.uint64(v) for v in (0, 0, 0, 0, 9, 3, 1)))
    surfaces.append(tuple(np.uint64(v) for v in (0, 0, 0, 0, 9, 0, 0)))

    assert list(_numba_reduce(surfaces)) == [
        (0, 0, 0, 0, 10, 1, 0),
        (0, 0, 0, 0, 9, 0, 0),
    ]


@pytest.mark.gpu
def test_fg_response_frontier_gpu_batch_materializes_state_frontiers() -> None:
    from tests.parity.force_greats.response_build_gpu_batch import build_force_greats_response_frontiers_gpu_batch

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
    from tests.parity.force_greats.response_build_gpu_batch import build_force_greats_response_frontiers_gpu_batch

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
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_batch
    from tests.parity.force_greats import response_build_gpu_batch as parity_response_build_gpu_batch

    timestamps = np.asarray([float(idx) * 0.11 for idx in range(140)], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0 if idx % 3 else 0.025 for idx in range(140)], dtype=np.float32)
    geometries = ((101.25, 108, 0.72),)

    full = parity_response_build_gpu_batch.build_force_greats_response_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )
    assert not hasattr(response_build_gpu_batch, "_frontier_from_edge_arrays")
    assert not hasattr(response_build_gpu_batch, "build_force_greats_response_frontiers_gpu_batch")
    slim = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )

    assert tuple(frontier.first_frontier for frontier in slim) == tuple(frontier.first_frontier for frontier in full)
    assert all(not frontier.state_frontiers for frontier in slim)


@pytest.mark.gpu
def test_fg_response_first_frontier_batch_matches_full_state_head_route() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_batch

    timestamps = np.asarray([float(idx) * 0.11 for idx in range(60)], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0 if idx % 3 else 0.025 for idx in range(60)], dtype=np.float32)
    geometries = ((2.25, 7, 0.55),)

    slim = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=geometries,
        use_forced_great_timing=True,
    )

    assert slim[0].first_frontier
    assert any(int(surface.fever0 | surface.fever1) != 0 for surface in slim[0].first_frontier)
    assert not slim[0].state_frontiers


@pytest.mark.gpu
def test_fg_response_counts_reconstruct_from_slim_first_frontier() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_batch
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _EMPTY_SURFACE,
        _action_table,
        _edge_surface_options,
        reconstruct_force_greats_response_counts,
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    def _combine_surface(edge: FgResponseSurface, tail: FgResponseSurface) -> FgResponseSurface:
        return FgResponseSurface(
            int(edge.fever0 | tail.fever0),
            int(edge.fever1 | tail.fever1),
            int(edge.fever2 | tail.fever2),
            int(edge.fever3 | tail.fever3),
            int(edge.great0 | tail.great0),
            int(edge.great1 | tail.great1),
            int(edge.great2 | tail.great2),
            int(edge.great3 | tail.great3),
            int(edge.body_fever + tail.body_fever),
            int(edge.body_great + tail.body_great),
            int(edge.body_fever_great + tail.body_fever_great),
        )

    timestamps = np.asarray([0.0, 0.18, 0.41, 0.64, 0.95, 1.21, 1.5], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0, 0.05, 0.0, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)
    raw_fever_fill = 2.25
    non_fever_base = 7
    real_fever_time = 0.55
    slim = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        geometries=((raw_fever_fill, non_fever_base, real_fever_time),),
        use_forced_great_timing=True,
    )[0]
    target = slim.first_frontier[-1]

    counts = reconstruct_force_greats_response_counts(
        frontier=slim,
        target_surface=target,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
        use_forced_great_timing=True,
    )
    trace = reconstruct_force_greats_response_trace(
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
    assert [row["forced_count"] for row in trace] == list(counts)
    assert all("activation_ms" in row and "activation_hit_offset_ms" in row and "fever_end_index" in row for row in trace)
    assert all(
        row["activation_hit_offset_ms"] == pytest.approx(row["activation_hit_ms"] - row["activation_ms"])
        for row in trace
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
        surface = _combine_surface(surface, edge)
        first = False

    assert surface == target
