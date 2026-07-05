from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


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
            perfect_floor_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            great_floor_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
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
            perfect_floor_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            great_floor_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        geometries=((2.25, 3, 1.0),),
        use_forced_great_timing=True,
    )[0]

    assert any((int(surface.fever0) & int(surface.great0)) != 0 for surface in frontier.first_frontier)


def test_fg_response_trace_logs_centered_perfect_witness_for_selected_surface() -> None:
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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        geometries=((2.25, 3, 1.0),),
        use_forced_great_timing=True,
    )[0]

    target = next(
        surface
        for surface in frontier.first_frontier
        if int(surface.fever0) == 0b1100 and int(surface.great0) == 0
    )
    trace = reconstruct_force_greats_response_trace(
        non_fever_base=int(frontier.non_fever_base),
        target_surface=target,
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        raw_fever_fill=2.25,
        real_fever_time=1.0,
        use_forced_great_timing=True,
    )

    assert trace[0]["activation_judgment"] == "perfect"
    assert trace[0]["fever_start_source"] == "perfect_window"
    assert trace[0]["fever_end_index"] == 4
    assert trace[0]["activation_hit_offset_ms"] == pytest.approx(250.0)
    assert trace[0]["activation_hit_offset_lower_ms"] == pytest.approx(0.0002384185791015625)
    assert trace[0]["activation_hit_offset_upper_ms"] == pytest.approx(500.0)
    assert trace[0]["activation_hit_window_width_ms"] == pytest.approx(499.9997615814209)


def test_body_pair_radix_round_trips_high_fever_great_counts() -> None:
    """Issue #44 radix: the body skyline packs (normal_great, body_fever_great) as
    normal_great*pair_mod + body_fever_great. With pair_mod sized past the geometry's max
    body_fever_great, every distinct (normal_great, fever_great) -- including the high fever-great
    counts the early-Great band produces -- must get its OWN slot and decode back exactly, with no
    aliasing onto a phantom cell."""
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_touch_body_candidate,
    )

    pair_mod = 20  # exceeds the max planted fever_great (15) -> the pack is injective
    n = 60
    pair_size = (n + 1) * pair_mod
    best_fever_by_pair = np.zeros(pair_size, dtype=np.int32)
    pair_stamp = np.zeros(pair_size, dtype=np.int32)
    touched_pair = np.empty(pair_size, dtype=np.int32)

    # (normal_great, fever_great, body_fever); fever_great up to 15 -- a bare section-count radix
    # (~5) would alias several of these onto one another.
    planted = [(2, 11, 100), (3, 14, 90), (5, 7, 80), (0, 15, 70), (9, 3, 60)]
    touched = 0
    for normal_great, fever_great, body_fever in planted:
        touched = _numba_touch_body_candidate(
            np.uint64(body_fever),
            np.uint64(normal_great + fever_great),  # body_great
            np.uint64(fever_great),                 # body_fever_great
            np.uint64(0),
            np.uint64(0),
            np.uint64(0),
            int(pair_mod),
            1,
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            int(touched),
        )

    assert int(touched) == len(planted)  # no two distinct pairs collided onto one slot
    decoded = {}
    for i in range(int(touched)):
        idx = int(touched_pair[i])
        decoded[(idx // pair_mod, idx % pair_mod)] = int(best_fever_by_pair[idx])
    assert decoded == {(ng, fg): bf for ng, fg, bf in planted}


def test_body_pair_radix_guard_fails_loud_when_fever_great_exceeds_modulus() -> None:
    """Issue #44 radix safety net: when body_fever_great >= pair_mod the pack stops being injective
    and would silently alias onto a phantom (normal_great+1, ...) surface that over-scores and
    breaks trace reconstruction. The build must FAIL LOUD instead. The chosen pair_idx (3*5+11 = 26)
    stays inside pair_size (205), so the pre-existing pair-size guard does NOT catch it -- only the
    dedicated radix guard does."""
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_touch_body_candidate,
    )

    pair_mod = 5
    n = 40
    pair_size = (n + 1) * pair_mod
    best_fever_by_pair = np.zeros(pair_size, dtype=np.int32)
    pair_stamp = np.zeros(pair_size, dtype=np.int32)
    touched_pair = np.empty(pair_size, dtype=np.int32)

    with pytest.raises(ValueError, match="fever-great"):
        _numba_touch_body_candidate(
            np.uint64(100),
            np.uint64(14),  # body_great = 14
            np.uint64(11),  # body_fever_great = 11 >= pair_mod = 5
            np.uint64(0),
            np.uint64(0),
            np.uint64(0),
            int(pair_mod),
            1,
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            0,
        )


def test_fg_response_trace_witness_search_centers_float32_surface_interval() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _centered_hit_window_for_exit,
        _lower_bound_from,
    )

    timestamps = np.asarray(
        [15.46399974822998, 73.97799682617188, 74.11299896240234],
        dtype=np.float32,
    )

    hit, lo, hi = _centered_hit_window_for_exit(
        timestamps,
        3,
        0,
        15.46399974822998,
        15.46399974822998,
        15.504000663757324,
        58.48316925859451,
        2,
        timestamps,
    )

    assert _lower_bound_from(timestamps, hit + 58.48316925859451) == 2
    assert _lower_bound_from(timestamps, lo + 58.48316925859451) == 2
    assert _lower_bound_from(timestamps, hi + 58.48316925859451) == 2
    assert lo <= hit <= hi
    assert 20.0 < (hit - 15.46399974822998) * 1000.0 < 40.1


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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
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
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        geometries=((2.25, 3, 1.0),),
        use_forced_great_timing=True,
    )[0]

    target = next(
        surface
        for surface in frontier.first_frontier
        if int(surface.fever0) == 0b11100 and (int(surface.great0) & 0b00100)
    )
    assert int(target.fever0) & int(target.great0) & 0b00100

    trace = reconstruct_force_greats_response_trace(
        non_fever_base=int(frontier.non_fever_base),
        target_surface=target,
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        raw_fever_fill=2.25,
        real_fever_time=1.0,
        use_forced_great_timing=True,
    )

    assert trace[0]["activation_judgment"] == "late_great"
    assert trace[0]["fever_start_source"] == "activation_late_great"
    assert trace[0]["fever_end_index"] == 5
    assert trace[0]["activation_hit_offset_ms"] == pytest.approx(450.0002861022949)
    assert trace[0]["activation_hit_offset_lower_ms"] == pytest.approx(400.00009536743164)
    assert trace[0]["activation_hit_offset_upper_ms"] == pytest.approx(500.0)
    assert trace[0]["activation_hit_window_width_ms"] == pytest.approx(99.99966621398926)


def test_force_greats_replay_uses_optimized_perfect_activation_edge() -> None:
    from gear_optimizer.solver.scoring.exact_rescore import _compute_force_greats_timeline
    from gear_optimizer.solver.timing_envelope import build_perfect_floor_envelope_sec

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    perfect_candidates = timestamps.copy()
    perfect_candidates[2] = np.float32(2.5)
    great_candidates = timestamps.copy()
    perfect_floor = build_perfect_floor_envelope_sec(timestamps, None)

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
        perfect_floor,
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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
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
        perfect_floor_timestamps=timestamps,
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


def test_fg_response_precomputed_end_indices_match_exact_edge_end_at_float32_boundaries() -> None:
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.solver.song_preparation import build_prepared_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _edge_end
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import _precompute_end_indices
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes

    calc_song = build_prepared_calc_song(
        fp=str(ROOT / "Data" / "Normal" / "Retaliation by Juggernaut.txt"),
        cfg_dict={},
    ).calc_song
    ref_arrays = build_ref_arrays_from_stats(
        read_table(str(ROOT / "Data" / "Gear" / "Stats.txt")),
        dtype=np.float64,
    )
    song_inputs, _raw_fill_by_ff, _non_fever_base_by_ff, real_time_by_ft = _response_axes(calc_song, ref_arrays)
    real_fever_time = float(real_time_by_ft[51])
    real_time_index, timestamp_end_idx, perfect_end_idx, great_end_idx, _great_floor_end_idx = _precompute_end_indices(
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        real_times=np.asarray([real_fever_time], dtype=np.float64),
    )
    rt_idx = int(real_time_index[0])
    from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
        build_late_great_forbidden_mask, build_reachable_perfect_candidate)
    forbidden = build_late_great_forbidden_mask(
        np.asarray(song_inputs.timestamps, dtype=np.float64),
        np.asarray(song_inputs.perfect_candidates, dtype=np.float64),
        np.asarray(song_inputs.great_candidates, dtype=np.float64),
        int(song_inputs.timestamps.shape[0]),
    )
    # perfect_end_idx is built from the hit-time REACHABLE perfect clock (a held-tail +80 activation
    # capped when a narrower later sibling is hit first), so perfect_e must use the same capped clock.
    reachable_pc = build_reachable_perfect_candidate(
        np.asarray(song_inputs.timestamps, dtype=np.float64),
        np.asarray(song_inputs.perfect_candidates, dtype=np.float64),
        int(song_inputs.timestamps.shape[0]),
    )

    for note_idx in range(int(song_inputs.timestamps.shape[0])):
        timestamp_e, _timestamp_start, _timestamp_carry = _edge_end(
            n=int(song_inputs.timestamps.shape[0]),
            a=note_idx,
            activation_great=False,
            real_fever_time=real_fever_time,
            use_forced_great_timing=False,
            timestamps=song_inputs.timestamps,
            perfect_floor_timestamps=song_inputs.perfect_floor,
        )
        perfect_e, _perfect_start, _perfect_carry = _edge_end(
            n=int(song_inputs.timestamps.shape[0]),
            a=note_idx,
            activation_great=False,
            real_fever_time=real_fever_time,
            use_forced_great_timing=True,
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=reachable_pc,
            great_candidate_timestamps=song_inputs.great_candidates,
            perfect_floor_timestamps=song_inputs.perfect_floor,
        )
        great_e, _great_start, _great_carry = _edge_end(
            n=int(song_inputs.timestamps.shape[0]),
            a=note_idx,
            activation_great=True,
            real_fever_time=real_fever_time,
            use_forced_great_timing=True,
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=song_inputs.perfect_candidates,
            great_candidate_timestamps=song_inputs.great_candidates,
            perfect_floor_timestamps=song_inputs.perfect_floor,
        )

        assert int(timestamp_end_idx[rt_idx, note_idx]) == int(timestamp_e)
        assert int(perfect_end_idx[rt_idx, note_idx]) == int(perfect_e)
        # Hit-time reachability: an UNREACHABLE late-Great (an earlier-hit note completes the bar
        # first) is forbidden in the precompute by clamping great_end_idx down to perfect_end_idx,
        # so its late-Great edge cannot extend fever. Reachable notes keep the raw late-Great edge.
        great_expected = int(perfect_e) if bool(forbidden[note_idx]) else int(great_e)
        assert int(great_end_idx[rt_idx, note_idx]) == great_expected

    # Note 164's late-Great reaches note 845 -- assert that only if it is reachable (no earlier-hit
    # note forecloses it); if forbidden it is clamped to the Perfect edge.
    assert int(great_end_idx[rt_idx, 164]) == (
        int(perfect_end_idx[rt_idx, 164]) if bool(forbidden[164]) else 845
    )


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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        raw_fever_fill=2.0,
    )

    assert not any(int(option["k"]) == 1 and int(option["next_state"]) == 5 for option in options)


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


def test_fg_response_branch_a_prefix_skyline_is_already_reduced() -> None:
    from numba.typed import List

    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _NUMBA_SURFACE_TYPE,
        _numba_append_branch_a_body_prefix_surface,
        _numba_reduce,
    )

    bucket = List.empty_list(_NUMBA_SURFACE_TYPE)
    width = 16
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
    assert not _numba_append_branch_a_body_prefix_surface(
        bucket,
        1,
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
        1,
        np.uint64(11),
        np.uint64(4),
        np.uint64(2),
        values,
        stamps,
        1,
        width,
    )
    assert not _numba_append_branch_a_body_prefix_surface(
        bucket,
        2,
        np.uint64(11),
        np.uint64(4),
        np.uint64(2),
        values,
        stamps,
        1,
        width,
    )

    assert list(bucket) == [
        (0, 0, 0, 0, 10, 1, 0),
        (0, 0, 0, 0, 9, 0, 0),
        (0, 0, 1, 0, 11, 4, 2),
    ]
    assert list(bucket) == list(_numba_reduce(bucket))


def test_fg_response_retaliation_first_frontier_surfaces_reconstruct() -> None:
    from gear_optimizer.helpers.song_helpers.ref_array_builder import build_ref_arrays_from_stats
    from gear_optimizer.data.csv_parser import read_table
    from gear_optimizer.solver.song_preparation import build_prepared_calc_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    calc_song = build_prepared_calc_song(
        fp=str(ROOT / "Data" / "Normal" / "Retaliation by Juggernaut.txt"),
        cfg_dict={},
    ).calc_song
    ref_arrays = build_ref_arrays_from_stats(
        read_table(str(ROOT / "Data" / "Gear" / "Stats.txt")),
        dtype=np.float64,
    )
    song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft = _response_axes(calc_song, ref_arrays)
    raw_fever_fill = float(raw_fill_by_ff[67])
    non_fever_base = int(non_fever_base_by_ff[67])
    real_fever_time = float(real_time_by_ft[51])

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.timestamps,
        great_floor_timestamps=song_inputs.timestamps,
        geometries=((raw_fever_fill, non_fever_base, real_fever_time),),
        use_forced_great_timing=song_inputs.use_forced_great_timing,
    )[0]

    # Every late-Great candidate must respect the engine's note-removal
    # deliverability cap (+200ms, Constants.lua:19) — the classification
    # window's wider +380 tail edge is unreachable in game. Tolerance covers
    # f32-second storage of the int-ms envelope.
    from gear_optimizer.solver.timing_envelope import NOTE_REMOVE_LATE_CAP_MS

    great_deltas_ms = (
        np.asarray(song_inputs.great_candidates, dtype=np.float64)
        - np.asarray(song_inputs.timestamps, dtype=np.float64)
    ) * 1000.0
    assert float(great_deltas_ms.max()) <= float(NOTE_REMOVE_LATE_CAP_MS) + 0.05
    # PR #35 pinned FgResponseSurface(0,0,0,0,3,0,0,0,1256,2,2) as unwitnessable
    # under the UNCAPPED (+380 tail) candidate geometry. Under the removal-capped
    # envelope that surface is legitimately witnessable again (its trace
    # reconstructs below); the universal reconstruct-every-surface loop is the
    # invariant that guards the #35 bug class.
    assert frontier.first_frontier
    for surface in frontier.first_frontier:
        reconstruct_force_greats_response_trace(
            non_fever_base=int(frontier.non_fever_base),
            target_surface=surface,
            timestamps=song_inputs.timestamps,
            perfect_candidate_timestamps=song_inputs.perfect_candidates,
            great_candidate_timestamps=song_inputs.great_candidates,
            perfect_floor_timestamps=song_inputs.timestamps,
            great_floor_timestamps=song_inputs.timestamps,
            raw_fever_fill=raw_fever_fill,
            real_fever_time=real_fever_time,
            use_forced_great_timing=song_inputs.use_forced_great_timing,
        )


@pytest.mark.gpu
def test_fg_response_first_frontier_batch_matches_full_state_head_route() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_batch

    timestamps = np.asarray([float(idx) * 0.11 for idx in range(60)], dtype=np.float32)
    great_candidates = timestamps + np.asarray([0.0 if idx % 3 else 0.025 for idx in range(60)], dtype=np.float32)
    geometries = ((2.25, 7, 0.55),)

    slim = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        geometries=((raw_fever_fill, non_fever_base, real_fever_time),),
        use_forced_great_timing=True,
    )[0]
    target = slim.first_frontier[-1]

    counts = reconstruct_force_greats_response_counts(
        frontier=slim,
        target_surface=target,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
        use_forced_great_timing=True,
    )
    trace = reconstruct_force_greats_response_trace(
        non_fever_base=int(slim.non_fever_base),
        target_surface=target,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
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
    assert all(
        "activation_ms" in row
        and "activation_hit_offset_ms" in row
        and "activation_hit_offset_lower_ms" in row
        and "activation_hit_offset_upper_ms" in row
        and "activation_hit_window_width_ms" in row
        and "fever_end_index" in row
        for row in trace
    )
    assert all(
        row["activation_hit_offset_ms"] == pytest.approx(row["activation_hit_ms"] - row["activation_ms"])
        for row in trace
    )
    assert all(
        row["activation_hit_offset_lower_ms"]
        <= row["activation_hit_offset_ms"]
        <= row["activation_hit_offset_upper_ms"]
        for row in trace
    )
    state = 0
    first = True
    surface = _EMPTY_SURFACE
    for count in counts:
        edge_match = None
        for option in _edge_surface_options(
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
            perfect_floor_timestamps=timestamps,
            great_floor_timestamps=timestamps,
            raw_fever_fill=raw_fever_fill,
        ):
            if int(option["k"]) == int(count):
                edge_match = (int(option["next_state"]), option["surface"])
                break
        assert edge_match is not None
        state, edge = edge_match
        surface = _combine_surface(surface, edge)
        first = False

    assert surface == target
