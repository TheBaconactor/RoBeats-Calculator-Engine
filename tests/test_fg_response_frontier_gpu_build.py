from __future__ import annotations

import hashlib
import os
import threading
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def _lanes_for(timestamps):
    return np.arange(int(np.asarray(timestamps).reshape(-1).shape[0]), dtype=np.int32)


def _engine_envelopes(timestamps, note_types=None):
    from gear_optimizer.solver.timing_envelope import precise_envelopes

    ts = np.asarray(timestamps, dtype=np.float32)
    types = np.ones(int(ts.shape[0]), dtype=np.int16) if note_types is None else note_types
    env = precise_envelopes(ts, types)
    return env.perfect_candidates, env.great_candidates, env.perfect_floor, env.great_floor


def _bruteforce_pg_contiguous_run_first_frontier(
    *,
    timestamps: np.ndarray,
    perfect_candidate_timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    perfect_floor_timestamps: np.ndarray,
    great_floor_timestamps: np.ndarray,
    lanes: np.ndarray,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
):
    from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
        activation_hit_is_reachable_weighted_lane_aware,
        server_fill_crossing_run,
    )
    from tests.fg_response_frontier_oracles import (
        _combine_surfaces,
        _reduce_surfaces,
        latest_activation_hit_for_contiguous_great_run,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _edge_end_at_hit,
        _edge_surface,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import _EMPTY_SURFACE

    n = int(timestamps.shape[0])
    lane_arr = np.asarray(lanes, dtype=np.int32).reshape(-1)

    def _latest_hit(
        *,
        activation_index: int,
        hit_lo: float,
        hit_hi: float,
        great_start: int,
        great_count: int,
    ) -> float | None:
        return latest_activation_hit_for_contiguous_great_run(
            activation_index=int(activation_index),
            hit_lo=float(hit_lo),
            hit_hi=float(hit_hi),
            chart_timestamps=timestamps,
            perfect_high_timestamps=perfect_candidate_timestamps,
            great_high_timestamps=great_candidate_timestamps,
            great_start=int(great_start),
            great_count=int(great_count),
            section_end=int(n),
        )

    def _activation_reachable(
        *,
        activation_index: int,
        hit: float,
        section_start: int,
        great_start: int,
        great_count: int,
        activation_great: bool,
    ) -> bool:
        lo = np.asarray(perfect_floor_timestamps, dtype=np.float32).copy()
        hi = np.asarray(perfect_candidate_timestamps, dtype=np.float32).copy()
        units = np.ones((n,), dtype=np.float32)
        great_start_i = max(0, min(int(great_start), n))
        great_end_i = min(n, great_start_i + max(0, int(great_count)))
        if great_end_i > great_start_i:
            lo[great_start_i:great_end_i] = np.asarray(great_floor_timestamps, dtype=np.float32)[
                great_start_i:great_end_i
            ]
            hi[great_start_i:great_end_i] = np.asarray(great_candidate_timestamps, dtype=np.float32)[
                great_start_i:great_end_i
            ]
            units[great_start_i:great_end_i] = np.float32(0.5)
        if bool(activation_great):
            lo[int(activation_index)] = np.asarray(great_floor_timestamps, dtype=np.float32)[int(activation_index)]
            hi[int(activation_index)] = np.asarray(great_candidate_timestamps, dtype=np.float32)[
                int(activation_index)
            ]
            units[int(activation_index)] = np.float32(0.5)
        return activation_hit_is_reachable_weighted_lane_aware(
            activation_index=int(activation_index),
            activation_hit_timestamp=float(hit),
            low_hit_timestamps=lo,
            high_hit_timestamps=hi,
            lanes=lane_arr,
            fill_units=units,
            fever_fill_denom=float(raw_fever_fill),
            section_start=int(section_start),
            section_end=int(n),
        )

    def _great_floor_end(start_time: float, activation_index: int) -> int:
        end = int(np.searchsorted(great_floor_timestamps, np.float32(float(start_time) + float(real_fever_time))))
        if end <= int(activation_index):
            end = int(activation_index) + 1
        return min(end, n)

    def _append_with_early_great_tails(
        surfaces: list,
        *,
        activation_index: int,
        activation_hit: float,
        activation_great: bool,
        great_start: int,
        great_end: int,
    ) -> None:
        fever_end, start_time, _carry_idx = _edge_end_at_hit(
            n=n,
            a=int(activation_index),
            hit=float(activation_hit),
            activation_great=bool(activation_great),
            real_fever_time=float(real_fever_time),
            perfect_floor_timestamps=perfect_floor_timestamps,
        )
        activation_great_idx = int(activation_index) if bool(activation_great) else -1
        surfaces.append(
            _edge_surface(
                n=n,
                fever_start=int(activation_index),
                fever_end=int(fever_end),
                great_start=int(great_start),
                great_end=int(great_end),
                activation_great_idx=int(activation_great_idx),
            )
        )
        for early_great_end in range(int(fever_end) + 1, _great_floor_end(float(start_time), int(activation_index)) + 1):
            surfaces.append(
                _edge_surface(
                    n=n,
                    fever_start=int(activation_index),
                    fever_end=int(early_great_end),
                    great_start=int(great_start),
                    great_end=int(great_end),
                    activation_great_idx=int(activation_great_idx),
                    early_great_start=int(fever_end),
                    early_great_end=int(early_great_end),
                )
            )

    def _edge_surfaces(state: int, first: bool) -> tuple:
        section_start = 0 if bool(first) else int(state) + 1
        if section_start >= n:
            return (_EMPTY_SURFACE,)
        generated = []
        for run_start in range(section_start, n):
            max_count = min(n - int(run_start), max(n, int(non_fever_base) + 4))
            for great_count in range(0, max_count + 1):
                if great_count == 0 and run_start != section_start:
                    continue
                crossing, crossing_is_great = server_fill_crossing_run(
                    int(section_start),
                    int(run_start),
                    int(great_count),
                    float(raw_fever_fill),
                    int(n),
                )
                if crossing is None or int(crossing) >= n:
                    continue
                activation_index = int(crossing)
                great_end = min(n, int(run_start) + int(great_count))
                if bool(crossing_is_great):
                    great_end = max(great_end, activation_index + 1)
                    hit_lo = float(
                        np.float32(
                            np.float32(perfect_candidate_timestamps[activation_index]) + np.float32(0.001)
                        )
                    )
                    hit_hi = float(great_candidate_timestamps[activation_index])
                    max_great_end = great_end
                    while max_great_end < n and float(perfect_candidate_timestamps[max_great_end]) < hit_hi:
                        max_great_end += 1
                    for legal_great_end in range(great_end, max_great_end + 1):
                        hit = _latest_hit(
                            activation_index=activation_index,
                            hit_lo=hit_lo,
                            hit_hi=hit_hi,
                            great_start=run_start,
                            great_count=int(legal_great_end) - int(run_start),
                        )
                        if hit is None:
                            continue
                        if not _activation_reachable(
                            activation_index=activation_index,
                            hit=float(hit),
                            section_start=section_start,
                            great_start=run_start,
                            great_count=int(legal_great_end) - int(run_start),
                            activation_great=True,
                        ):
                            continue
                        _append_with_early_great_tails(
                            generated,
                            activation_index=activation_index,
                            activation_hit=float(hit),
                            activation_great=True,
                            great_start=run_start,
                            great_end=int(legal_great_end),
                        )
                        break
                    continue
                if int(great_count) > 0 and activation_index < great_end:
                    continue
                hit = _latest_hit(
                    activation_index=activation_index,
                    hit_lo=min(
                        float(timestamps[activation_index]),
                        float(perfect_candidate_timestamps[activation_index]),
                    ),
                    hit_hi=max(
                        float(timestamps[activation_index]),
                        float(perfect_candidate_timestamps[activation_index]),
                    ),
                    great_start=run_start,
                    great_count=int(great_end) - int(run_start),
                )
                if hit is None:
                    continue
                if not _activation_reachable(
                    activation_index=activation_index,
                    hit=float(hit),
                    section_start=section_start,
                    great_start=run_start,
                    great_count=int(great_end) - int(run_start),
                    activation_great=False,
                ):
                    continue
                _append_with_early_great_tails(
                    generated,
                    activation_index=activation_index,
                    activation_hit=float(hit),
                    activation_great=False,
                    great_start=run_start,
                    great_end=int(great_end),
                )
        return _reduce_surfaces(tuple(generated), lo_pos=int(state), hi_pos=min(n, 100))

    memo: dict[tuple[int, bool], tuple] = {}

    def _surface_fever_end(surface) -> int:
        words = (int(surface.fever0), int(surface.fever1), int(surface.fever2), int(surface.fever3))
        for idx in range(min(n, 100) - 1, -1, -1):
            word = words[idx // 32]
            if word & (1 << (idx % 32)):
                return idx + 1
        return int(surface.body_fever)

    def _frontier(state: int, first: bool) -> tuple:
        if int(state) >= n:
            return (_EMPTY_SURFACE,)
        key = (int(state), bool(first))
        cached = memo.get(key)
        if cached is not None:
            return cached
        generated = []
        for edge in _edge_surfaces(int(state), bool(first)):
            if edge == _EMPTY_SURFACE:
                generated.append(edge)
                continue
            next_state = _surface_fever_end(edge)
            if next_state <= int(state):
                raise ValueError("bruteforce P/G oracle emitted a non-advancing section")
            tails = (_EMPTY_SURFACE,) if next_state >= n else _frontier(next_state, False)
            for tail in tails:
                generated.append(_combine_surfaces(edge, tail))
        reduced = _reduce_surfaces(tuple(generated), lo_pos=int(state), hi_pos=min(n, 100))
        memo[key] = reduced
        return reduced

    return _frontier(0, True)


def _missing_pg_oracle_surfaces(production_surfaces, oracle_surfaces) -> list[tuple[int, ...]]:
    def _score_dominates(left, right) -> bool:
        left_normal_great = int(left.body_great) - int(left.body_fever_great)
        right_normal_great = int(right.body_great) - int(right.body_fever_great)
        return (
            int(left.body_fever) >= int(right.body_fever)
            and int(left_normal_great) <= int(right_normal_great)
            and int(left.body_fever_great) <= int(right.body_fever_great)
            and (int(right.fever0) & ~int(left.fever0)) == 0
            and (int(right.fever1) & ~int(left.fever1)) == 0
            and (int(right.fever2) & ~int(left.fever2)) == 0
            and (int(right.fever3) & ~int(left.fever3)) == 0
            and (int(left.great0) & ~int(right.great0)) == 0
            and (int(left.great1) & ~int(right.great1)) == 0
            and (int(left.great2) & ~int(right.great2)) == 0
            and (int(left.great3) & ~int(right.great3)) == 0
        )

    missing = []
    for oracle_surface in oracle_surfaces:
        if not any(_score_dominates(production_surface, oracle_surface) for production_surface in production_surfaces):
            missing.append(tuple(map(int, oracle_surface)))
    return missing


def test_fg_response_first_frontier_region_groups_partition_in_canonical_order() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_precompute

    action_row = np.asarray([1, 2, 3, 4], dtype=np.int32)

    def _item(idx: int, non_fever_base: int, raw_fill: float) -> tuple:
        return (idx, non_fever_base, raw_fill, 1.0, action_row, action_row, action_row)

    items = [_item(0, 3, 2.5), _item(1, 3, 2.5), _item(2, 4, 2.5), _item(3, 3, 2.5), _item(4, 4, 7.0)]

    groups = response_build_gpu_precompute._first_only_region_groups(items)

    # Keys keep first-appearance order and items keep canonical order within each independent
    # table group; concurrent completion therefore cannot change returned geometry order.
    assert list(groups.keys()) == [(2.5, 3), (2.5, 4), (7.0, 4)]
    assert groups[(2.5, 3)] == [items[0], items[1], items[3]]
    assert groups[(2.5, 4)] == [items[2]]
    assert groups[(7.0, 4)] == [items[4]]
    # Fills with the same half-unit count share a table, keyed by the first one's fill.
    shared = response_build_gpu_precompute._first_only_region_groups([_item(5, 3, 2.2), _item(6, 3, 2.4), _item(7, 3, 2.6)])
    assert list(shared.keys()) == [(2.2, 3), (2.6, 3)]
    assert [item[0] for item in shared[(2.2, 3)]] == [5, 6]
    # The pre-song-context chunk machinery is gone: one canonical grouped route only.
    assert not hasattr(response_build_gpu_precompute, "_first_only_chunks")
    assert not hasattr(response_build_gpu_precompute, "_batch_chunk_size")
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


def test_fg_region_core_candidate_capacity_bounds_exact_arrays() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba

    timestamps = np.arange(12, dtype=np.float32) * np.float32(0.1)
    perfect_hi = timestamps + np.float32(0.04)
    great_hi = timestamps + np.float32(0.09)
    action_k = np.asarray([0, 1, 2, 3], dtype=np.int32)
    capacity = response_build_gpu_numba._numba_region_core_candidate_capacity(
        12,
        4,
        action_k,
        4.0,
    )
    brute_capacity = 0
    region_stop = response_build_gpu_numba._numba_region2_k_scan_stop(4, 4.0)
    for section_start in range(13):
        shifted = 1 if response_build_gpu_numba._numba_has_shifted_head_region(section_start, 4.0) else -1
        for action_idx, k in enumerate(action_k):
            region = -1
            if action_idx < region_stop:
                region = response_build_gpu_numba._numba_region2_offset_for_count(
                    section_start, int(k), 4.0, 12
                )
            brute_capacity += int(region >= 1)
            brute_capacity += int(shifted >= 1 and shifted != region)
    assert capacity == brute_capacity
    table = response_build_gpu_numba._numba_build_region_core_table(
        12,
        4,
        action_k,
        4.0,
        timestamps,
        response_build_gpu_numba.HitTimes(
            timestamps - np.float32(0.04), perfect_hi, timestamps - np.float32(0.09),
            great_hi, perfect_hi + np.float32(0.001),
        ),
        np.arange(12, dtype=np.int32),
    )

    starts, *columns = table
    retained = int(starts[-1])
    assert retained > 0
    assert retained <= capacity < (13 * 4 * 2)
    assert np.all(starts[1:] >= starts[:-1])
    assert all(column.shape == (retained,) for column in columns)
    assert all(column.flags.c_contiguous for column in columns)
    assert [column.dtype for column in columns] == [
        np.dtype(np.int32),
        np.dtype(np.int32),
        np.dtype(np.int32),
        np.dtype(np.int32),
        np.dtype(np.int32),
        np.dtype(np.int32),
        np.dtype(np.int32),
    ]


def test_region_packet_missing_core_receives_its_endpoint_tables(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as rb

    n = 120
    empty = np.empty(0, dtype=np.int32)
    limits = np.full(n, n, dtype=np.int32)
    perfect_ends, great_ends = np.arange(3, dtype=np.int32), np.arange(4, dtype=np.int32)
    region = rb.RegionTables(np.zeros(n + 2, dtype=np.int64), *(empty for _ in range(7)), perfect_ends, great_ends)
    calls = []

    def edge(*args):
        assert args[-2] is perfect_ends and args[-1] is great_ends
        calls.append(args)
        return -1, -1, -1, -1, -1, -1, 0

    monkeypatch.setattr(rb, "_numba_region_run_edge_for_offset", edge)
    ts = np.arange(n, dtype=np.float32)
    rb._numba_region2_packet_queue_push_activation.py_func(
        n, 20, -31, 110, 4.0, empty, empty, empty, ts, ts, ts, ts, ts, ts,
        np.arange(n), region, limits, 0, 0, 1, (empty,) * 7,
    )
    assert len(calls) == 1


def test_fg_response_region_group_admission_validates_exact_memory_bounds() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_scheduler

    assert response_build_gpu_scheduler._validate_region_group_memory_bounds(
        build_peak_bounds=(20, 40, 30),
        retained_peak_bounds=(10, 20, 15),
        legacy_single_peak_bound=70,
    ) is None
    assert response_build_gpu_scheduler._validate_region_group_memory_bounds(
        build_peak_bounds=(),
        retained_peak_bounds=(),
        legacy_single_peak_bound=0,
    ) is None
    with pytest.raises(ValueError, match="memory bounds must be nonnegative"):
        response_build_gpu_scheduler._validate_region_group_memory_bounds(
            build_peak_bounds=(20, -1),
            retained_peak_bounds=(10, 1),
            legacy_single_peak_bound=70,
        )
    with pytest.raises(ValueError, match="must align"):
        response_build_gpu_scheduler._validate_region_group_memory_bounds(
            build_peak_bounds=(20, 30),
            retained_peak_bounds=(10,),
            legacy_single_peak_bound=70,
        )
    with pytest.raises(ValueError, match="cannot exceed"):
        response_build_gpu_scheduler._validate_region_group_memory_bounds(
            build_peak_bounds=(20,),
            retained_peak_bounds=(21,),
            legacy_single_peak_bound=70,
        )
    with pytest.raises(MemoryError, match="historical single-table peak bound"):
        response_build_gpu_scheduler._validate_region_group_memory_bounds(
            build_peak_bounds=(71,),
            retained_peak_bounds=(35,),
            legacy_single_peak_bound=70,
        )


def test_fg_response_group_scheduler_is_part_of_logic_fingerprint() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_types

    assert "response_build_gpu_scheduler.py" in {
        source.name for source in response_cache_types._FG_DP_SOURCES
    }


def test_fg_response_game_engine_inputs_are_part_of_logic_fingerprint() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_cache_types

    fingerprinted = {
        source.relative_to(response_cache_types._SOLVER_DIR.parent).as_posix()
        for source in response_cache_types._FG_DP_SOURCES
    }
    # The game-engine inputs (timing, input order, lane reachability, fever, witnesses) must rotate the FG cache.
    assert {
        "core/time_quantize.py",
        "rules.py",
        "solver/fg_response_scoring/note_graph.py",
        "solver/input_engine_breakpoints.py",
        "solver/scoring/fg_policy.py",
        "solver/timing_envelope.py",
    } <= fingerprinted


def test_fg_response_region_group_peak_bound_covers_build_and_trimmed_arrays() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import (
        response_build_gpu_numba,
        response_build_gpu_scheduler,
    )

    n = 12
    action_k = np.asarray([0, 1, 2, 3], dtype=np.int32)
    capacity = response_build_gpu_numba._numba_region_core_candidate_capacity(
        n,
        int(action_k.shape[0]),
        action_k,
        4.0,
    )
    expected = (n + 2) * np.dtype(np.int64).itemsize + 2 * int(capacity) * 28
    assert response_build_gpu_scheduler._region_table_build_peak_bound_bytes(
        n=n,
        action_k=action_k,
        raw_fever_fill=4.0,
    ) == expected
    assert response_build_gpu_scheduler._region_table_retained_bound_bytes(
        n=n,
        action_k=action_k,
        raw_fever_fill=4.0,
    ) == (n + 2) * np.dtype(np.int64).itemsize + int(capacity) * 28
    assert response_build_gpu_scheduler._legacy_single_region_table_peak_bound_bytes(
        n=n,
        region_action_count=int(action_k.shape[0]),
    ) == (n + 2) * 8 + 2 * ((n + 1) * 4 * 2) * 28


def test_fg_response_first_frontier_runs_admitted_groups_concurrently(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import (
        response_build_gpu_batch,
        response_build_gpu_reducer,
        response_build_gpu_scheduler,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    build_barrier = threading.Barrier(2, timeout=5.0)
    reduce_barrier = threading.Barrier(2, timeout=5.0)
    caller_id = threading.get_ident()
    builder_ids: list[int] = []
    worker_ids: list[int] = []
    result = FgResponseFrontierResult(
        (FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0),),
        {},
        1,
        4,
        0,
        1,
        1,
        1,
        3,
        0.0,
    )

    empty_table = (
        np.zeros(5, dtype=np.int64),
        np.empty(0, dtype=np.int32),
        np.empty(0, dtype=np.int32),
        np.empty(0, dtype=np.int32),
        np.empty(0, dtype=np.int32),
        np.empty(0, dtype=np.float64),
        np.empty(0, dtype=np.float64),
        np.empty(0, dtype=np.int32),
    )

    def _fake_build(*_args):
        builder_ids.append(threading.get_ident())
        build_barrier.wait()
        return empty_table

    def _fake_reduce(**kwargs):
        worker_ids.append(threading.get_ident())
        reduce_barrier.wait()
        return [(int(item[0]), result) for item in kwargs["group_items"]]

    monkeypatch.setattr(response_build_gpu_scheduler, "_region_table_build_peak_bound_bytes", lambda **_kwargs: 200)
    monkeypatch.setattr(response_build_gpu_scheduler, "_region_table_retained_bound_bytes", lambda **_kwargs: 100)
    monkeypatch.setattr(
        response_build_gpu_scheduler,
        "_legacy_single_region_table_peak_bound_bytes",
        lambda **_kwargs: 400,
    )
    monkeypatch.setattr(response_build_gpu_scheduler._rb_numba, "_numba_build_region_core_table", _fake_build)
    monkeypatch.setattr(response_build_gpu_scheduler, "_reduce_first_frontier_group", _fake_reduce)
    previous_threads = response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(2)
    stats: dict = {}
    try:
        frontiers = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            perfect_floor_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            great_floor_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            lanes=np.arange(3, dtype=np.int32),
            geometries=((2.0, 3, 1.0), (3.0, 4, 1.0)),
            use_forced_great_timing=True,
            stats_sink=stats,
        )
    finally:
        response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(previous_threads)

    assert frontiers == (result, result)
    assert caller_id not in builder_ids
    assert len(set(builder_ids)) == 2
    assert len(set(worker_ids)) == 2
    assert stats["region_table_groups"] == 2
    assert stats["region_table_parallelism"] == 2
    assert stats["region_table_parallel_peak_bound_bytes"] == 400
    assert stats["region_table_legacy_single_peak_bound_bytes"] == 400
    assert stats["executor_creations"] == 2


def test_fg_response_single_group_retains_within_group_reducer(monkeypatch) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import (
        response_build_gpu_batch,
        response_build_gpu_reducer,
        response_build_gpu_scheduler,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import (
        FgResponseFrontierResult,
        FgResponseSurface,
    )

    result = FgResponseFrontierResult(
        (FgResponseSurface(1, 0, 0, 0, 0, 0, 0, 0, 0, 0),),
        {},
        1,
        4,
        0,
        1,
        1,
        1,
        3,
        0.0,
    )
    calls: list[tuple[int, int]] = []

    def _fake_range(**kwargs):
        start = int(kwargs["start"])
        stop = int(kwargs["stop"])
        calls.append((start, stop))
        return [(int(kwargs["chunk"][idx][0]), result) for idx in range(start, stop)]

    monkeypatch.setattr(response_build_gpu_scheduler, "_first_frontier_results_for_precomputed_range", _fake_range)
    previous_threads = response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(2)
    stats: dict = {}
    try:
        frontiers = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
            timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            perfect_floor_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            great_floor_timestamps=np.asarray([0.0, 1.0, 2.0], dtype=np.float32),
            lanes=np.arange(3, dtype=np.int32),
            geometries=((2.0, 3, 1.0), (2.0, 3, 2.0)),
            use_forced_great_timing=False,
            stats_sink=stats,
        )
    finally:
        response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(previous_threads)

    assert frontiers == (result, result)
    assert sorted(calls) == [(0, 1), (1, 2)]
    assert stats["region_table_groups"] == 1
    assert stats["region_table_parallelism"] == 1
    assert stats["executor_creations"] == 1


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


def test_fg_response_prefix_activation_hit_table_matches_direct_scan() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as rb

    timestamps = np.asarray([0.000, 0.018, 0.041, 0.060, 0.083, 0.140, 0.161, 0.184], dtype=np.float32)
    perfect_hi = np.asarray([0.040, 0.058, 0.081, 0.100, 0.123, 0.180, 0.201, 0.224], dtype=np.float32)
    great_hi = np.asarray([0.095, 0.113, 0.136, 0.155, 0.178, 0.235, 0.256, 0.279], dtype=np.float32)
    n = int(timestamps.shape[0])

    perfect_hit, perfect_valid, late_hit, late_valid = rb._numba_build_prefix_activation_hit_tables(
        n,
        timestamps,
        perfect_hi,
        great_hi,
        perfect_hi + np.float32(0.001),
    )

    for activation in range(n):
        expected_hit, expected_valid, _token = rb._numba_perfect_activation_hit_for_run(
            activation,
            timestamps,
            perfect_hi,
            great_hi,
            activation,
            0,
            n,
        )
        assert int(perfect_valid[activation]) == int(expected_valid)
        assert float(perfect_hit[activation]) == pytest.approx(float(expected_hit))

        expected_late_hit, expected_late_valid, _token = (
            rb._numba_late_great_activation_hit_for_run(
                activation,
                timestamps,
                perfect_hi,
                great_hi,
                perfect_hi + np.float32(0.001),
                activation,
                1,
                n,
            )
        )
        assert int(late_valid[activation]) == int(expected_late_valid)
        assert float(late_hit[activation]) == pytest.approx(float(expected_late_hit))

        for great_start in range(max(0, activation - 3), activation + 1):
            great_count = max(0, activation - great_start)
            direct_hit, direct_valid, _token = rb._numba_perfect_activation_hit_for_run(
                activation,
                timestamps,
                perfect_hi,
                great_hi,
                great_start,
                great_count,
                n,
            )
            assert int(perfect_valid[activation]) == int(direct_valid)
            assert float(perfect_hit[activation]) == pytest.approx(float(direct_hit))

            direct_late_hit, direct_late_valid, _token = (
                rb._numba_late_great_activation_hit_for_run(
                    activation,
                    timestamps,
                    perfect_hi,
                    great_hi,
                    perfect_hi + np.float32(0.001),
                    great_start,
                    great_count,
                    n,
                )
            )
            assert int(late_valid[activation]) == int(direct_late_valid)
            assert float(late_hit[activation]) == pytest.approx(float(direct_late_hit))


def test_fg_response_region2_packet_family_matches_direct_edges() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import (
        response_build_gpu_numba as rb,
        response_build_gpu_precompute,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table

    timestamps = np.asarray([idx * 0.071 for idx in range(180)], dtype=np.float32)
    timestamps[28:31] = timestamps[28]
    timestamps[63:65] = timestamps[63]
    perfect_candidates = timestamps + np.float32(0.04)
    great_candidates = timestamps + np.float32(0.19)
    perfect_floor = timestamps - np.float32(0.019)
    great_floor = timestamps - np.float32(0.095)
    lanes = np.asarray([(idx * 3) % 4 for idx in range(int(timestamps.shape[0]))], dtype=np.int32)
    raw_fever_fill = 8.2
    actions, *_rest = _action_table(
        raw_fever_fill=raw_fever_fill,
        non_fever_base=9,
        use_forced_great_timing=True,
    )
    action_k = np.asarray(actions, dtype=np.int32)

    family_count, family_defect, family_start, family_end = rb._numba_build_region2_packet_families(
        int(action_k.shape[0]),
        float(raw_fever_fill),
        action_k,
        int(timestamps.shape[0]),
    )
    assert any(int(family_end[idx]) > int(family_start[idx]) for idx in range(int(family_count)))

    capped = (perfect_candidates.astype(np.float64) - 0.000001, great_candidates.astype(np.float64) - 0.000001)
    tokens = np.concatenate((timestamps, perfect_candidates, great_candidates, *capped))
    cutoffs = (tokens + 1.75).astype(np.float32)
    perfect_ends, great_ends = (np.searchsorted(f, cutoffs).astype(np.int32) for f in (perfect_floor, great_floor))
    checked = 0
    for family_idx in range(int(family_count)):
        start = int(family_start[family_idx])
        end = int(family_end[family_idx])
        defect = int(family_defect[family_idx])
        if end <= start:
            continue
        first_activation = max(100 + int(end), int(end) + 4)
        for activation in range(first_activation, min(int(timestamps.shape[0]) - 4, first_activation + 18)):
            expected = None
            for activation_offset in range(start, end + 1):
                k = 2 * int(activation_offset) + int(defect) + 1
                region_offset = int(activation_offset) - int(k)
                state_i = int(activation) - int(activation_offset)
                section_start = int(state_i) + 1
                assert region_offset >= 1
                direct = rb._numba_region_run_edge_for_offset(
                    int(timestamps.shape[0]),
                    int(section_start),
                    int(region_offset),
                    int(k),
                    float(raw_fever_fill),
                    timestamps,
                    rb.HitTimes(perfect_floor,
                    perfect_candidates,
                    great_floor,
                    great_candidates,
                    perfect_candidates + np.float32(0.001)),
                    lanes,
                    perfect_ends,
                    great_ends,
                )
                activation_i, edge_e, run_start, great_end, activation_great_idx, _eg_e, valid = direct
                assert int(activation_i) == int(activation)
                assert int(valid) != 0
                assert int(activation_great_idx) == int(activation)
                edge = rb._numba_pack_edge(
                    int(timestamps.shape[0]),
                    int(activation_i),
                    int(edge_e),
                    int(run_start),
                    int(great_end),
                    int(activation_i),
                )
                edge_normal = int(edge[5]) - int(edge[6])
                extra_normal = int(edge_normal) - ((2 * int(activation_offset)) + int(defect))
                signature = (
                    int(edge_e),
                    int(great_end),
                    int(extra_normal),
                    int(edge[4]),
                    int(edge[6]),
                )
                if expected is None:
                    expected = signature
                else:
                    assert signature == expected
                checked += 1
    assert checked > 0


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
            lanes=np.arange(3, dtype=np.int32),
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
            lanes=np.arange(3, dtype=np.int32),
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
            lanes=_lanes_for(timestamps),
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
    perfect_candidates, great_candidates, perfect_floor, great_floor = _engine_envelopes(timestamps)

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
            lanes=_lanes_for(timestamps),
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
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
            lanes=_lanes_for(timestamps),
        raw_fever_fill=2.25,
        real_fever_time=1.0,
        use_forced_great_timing=True,
    )

    assert trace[0]["activation_judgment"] == "perfect"
    assert trace[0]["fever_start_source"] == "precise"
    assert trace[0]["fever_end_index"] == 4
    assert trace[0]["activation_hit_offset_ms"] == pytest.approx(19.999980926513672)
    assert trace[0]["activation_hit_offset_lower_ms"] == pytest.approx(0.0)
    assert trace[0]["activation_hit_offset_upper_ms"] == pytest.approx(39.999961853027344)
    assert trace[0]["activation_hit_window_width_ms"] == pytest.approx(39.999961853027344)
    assert trace[0]["fever_window_end_ms"] == pytest.approx(
        trace[0]["activation_hit_ms"] + trace[0]["fever_duration_ms"]
    )


def test_body_pair_radix_round_trips_high_fever_great_counts() -> None:
    """Issue #44 radix: the body skyline packs (normal_great, body_fever_great) as
    normal_great*pair_mod + body_fever_great. With pair_mod sized past the geometry's max
    body_fever_great, every distinct (normal_great, fever_great) -- including the high fever-great
    counts the early-Great band produces -- must get its OWN slot and decode back exactly, with no
    aliasing onto a phantom cell."""
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        HitTimes,
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
        HitTimes,
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
        3,
        0,
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
            lanes=_lanes_for(timestamps),
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

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 3.1, 3.4], dtype=np.float32)
    perfect_candidates, great_candidates, perfect_floor, great_floor = _engine_envelopes(timestamps)

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
            lanes=_lanes_for(timestamps),
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
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
            lanes=_lanes_for(timestamps),
        raw_fever_fill=2.25,
        real_fever_time=1.0,
        use_forced_great_timing=True,
    )

    assert trace[0]["activation_judgment"] == "late_great"
    assert trace[0]["fever_start_source"] == "activation_late_great"
    assert trace[0]["fever_end_index"] == 5
    assert trace[0]["activation_hit_offset_ms"] == pytest.approx(135.5001926422119)
    assert trace[0]["activation_hit_offset_lower_ms"] == pytest.approx(81.00032806396484)
    assert trace[0]["activation_hit_offset_upper_ms"] == pytest.approx(190.00005722045898)
    assert trace[0]["activation_hit_window_width_ms"] == pytest.approx(108.99972915649414)


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
            lanes=_lanes_for(timestamps),
        geometries=((102.25, 103, 1.0),),
        use_forced_great_timing=True,
    )[0]

    assert any(int(surface.body_fever_great) > 0 for surface in frontier.first_frontier)


def test_fg_response_edge_end_does_not_let_prefix_great_carry_perfect_activation() -> None:
    from tests.fg_response_frontier_oracles import edge_end_oracle

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    great_candidates = timestamps.copy()
    great_candidates[0] = np.float32(2.4)
    great_candidates[1] = np.float32(1.1)

    edge_end, start_time, carry_idx = edge_end_oracle(
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


def test_fg_response_precomputed_end_indices_match_exact_edge_end_at_float32_boundaries() -> None:
    from gear_optimizer.gamedata import load_stat_curves
    from gear_optimizer.chart import load_chart
    from gear_optimizer.solver.timing_envelope import time_song
    from tests.fg_response_frontier_oracles import edge_end_oracle
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import _precompute_end_indices
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes

    song = time_song(load_chart(str(ROOT / "Data" / "Normal" / "Retaliation by Juggernaut.txt")), "precise")
    curves = load_stat_curves(ROOT / "Data" / "Gear" / "Stats.txt")
    song_inputs, _raw_fill_by_ff, _non_fever_base_by_ff, real_time_by_ft = _response_axes(song, curves)
    real_fever_time = float(real_time_by_ft[51])
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as rb

    prefix_perfect_hit, _prefix_perfect_valid, prefix_late_hit, _prefix_late_valid = (
        rb._numba_build_prefix_activation_hit_tables(
            int(song_inputs.timestamps.shape[0]),
            song_inputs.timestamps,
            song_inputs.perfect_candidates,
            song_inputs.great_candidates,
            song_inputs.late_great_floor,
        )
    )
    (
        real_time_index,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        _great_floor_end_idx,
        _capped_perfect_edge_e,
        _capped_late_edge_e,
        _capped_eg_perfect_e,
        _capped_eg_late_e,
        _capped_perfect_exit_e,
        _capped_late_exit_e,
    ) = _precompute_end_indices(
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        prefix_perfect_hit=prefix_perfect_hit,
        prefix_late_hit=prefix_late_hit,
        exit_ceiling_timestamps=song_inputs.exit_ceiling,
        late_great_floor_timestamps=song_inputs.late_great_floor,
        lanes=song_inputs.lanes,
        real_times=np.asarray([real_fever_time], dtype=np.float64),
    )
    rt_idx = int(real_time_index[0])
    # Input-engine-aware precompute preserves the raw per-note Perfect clock. Reachability is checked
    # later by reconstruction/persistence with lane and surface context.
    reachable_pc = song_inputs.perfect_candidates

    for note_idx in range(int(song_inputs.timestamps.shape[0])):
        timestamp_e, _timestamp_start, _timestamp_carry = edge_end_oracle(
            n=int(song_inputs.timestamps.shape[0]),
            a=note_idx,
            activation_great=False,
            real_fever_time=real_fever_time,
            use_forced_great_timing=False,
            timestamps=song_inputs.timestamps,
            perfect_floor_timestamps=song_inputs.perfect_floor,
        )
        perfect_e, _perfect_start, _perfect_carry = edge_end_oracle(
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
        great_e, _great_start, _great_carry = edge_end_oracle(
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
        # Input-engine-aware precompute preserves the raw late-Great edge. Legality is checked later
        # by reconstruction/persistence with lane and surface context.
        assert int(great_end_idx[rt_idx, note_idx]) == int(great_e)

    # Note 164's late-Great reaches note 845 -- assert that only if it is reachable (no earlier-hit
    # note forecloses it); if forbidden it is clamped to the Perfect edge.
    assert int(great_end_idx[rt_idx, 164]) == 845


def test_fg_response_activation_great_requires_same_fill_ordinal() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _action_table,
        _build_activation_reachability_context,
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
    lanes = _lanes_for(timestamps)
    reachability_context = _build_activation_reachability_context(
        timestamps=timestamps,
        perfect_floor_timestamps=timestamps,
        perfect_candidate_timestamps=timestamps,
        great_floor_timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        lanes=lanes,
        fever_fill_denom=2.0,
    )

    options = _edge_surface_options(
        reachability_context=reachability_context,
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
        lanes=lanes,
        raw_fever_fill=2.0,
    )

    assert not any(int(option["k"]) == 1 and int(option["next_state"]) == 5 for option in options)


def test_fg_response_frontier_emits_reconstructable_non_prefix_great_run() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )

    timestamps = np.asarray([float(idx) * 0.3 for idx in range(20)], dtype=np.float32)
    perfect_candidates, great_candidates, perfect_floor, great_floor = _engine_envelopes(timestamps)
    raw_fever_fill = 2.25
    real_fever_time = 0.5
    lanes = _lanes_for(timestamps)

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=lanes,
        geometries=((raw_fever_fill, 20, real_fever_time),),
        use_forced_great_timing=True,
    )[0]

    found = False
    for surface in frontier.first_frontier:
        trace = reconstruct_force_greats_response_trace(
            non_fever_base=int(frontier.non_fever_base),
            target_surface=surface,
            timestamps=timestamps,
            perfect_candidate_timestamps=perfect_candidates,
            great_candidate_timestamps=great_candidates,
            perfect_floor_timestamps=perfect_floor,
            great_floor_timestamps=great_floor,
            lanes=lanes,
            raw_fever_fill=raw_fever_fill,
            real_fever_time=real_fever_time,
            use_forced_great_timing=True,
        )
        if any(
            int(row.get("forced_run_count", 0)) > 0
            and int(row.get("forced_run_start_index", row["forced_start_index"])) != int(row["forced_start_index"])
            for row in trace
        ):
            found = True
            break
    assert found


def test_fg_response_region_late_great_forces_same_time_sibling_bundle() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _action_table,
        _build_activation_reachability_context,
        _edge_surface_options,
    )

    timestamps = np.asarray([float(idx) * 0.1 for idx in range(130)], dtype=np.float32)
    timestamps[103] = timestamps[102]
    perfect_candidates = timestamps + np.float32(0.04)
    great_candidates = timestamps + np.float32(0.19)
    perfect_floor = timestamps - np.float32(0.019)
    great_floor = timestamps - np.float32(0.094)
    raw_fever_fill = 2.25
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=raw_fever_fill,
        non_fever_base=3,
        use_forced_great_timing=True,
    )
    lanes = _lanes_for(timestamps)
    reachability_context = _build_activation_reachability_context(
        timestamps=timestamps,
        perfect_floor_timestamps=perfect_floor,
        perfect_candidate_timestamps=perfect_candidates,
        great_floor_timestamps=great_floor,
        great_candidate_timestamps=great_candidates,
        lanes=lanes,
        fever_fill_denom=raw_fever_fill,
    )

    options = _edge_surface_options(
        reachability_context=reachability_context,
        i=99,
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
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=lanes,
        raw_fever_fill=raw_fever_fill,
    )

    assert not any(
        int(option["activation_index"]) == 102
        and str(option["activation_judgment"]) == "late_great"
        and int(option.get("forced_run_start_index", option["forced_start_index"])) == 102
        and int(option["forced_run_count"]) == 1
        for option in options
    )
    bundle = [
        option
        for option in options
        if int(option["activation_index"]) == 102
        and str(option["activation_judgment"]) == "late_great"
        and int(option.get("forced_run_start_index", option["forced_start_index"])) == 102
        and int(option["forced_run_count"]) == 2
    ]
    assert bundle
    assert any(int(option["surface"].body_fever_great) >= 2 for option in bundle)


def test_fg_response_frontier_caps_activation_at_following_label_breakpoint() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import _action_table
    from tests.fg_response_frontier_oracles import edge_surface_option_details

    timestamps = np.asarray([0.0, 0.5, 1.0, 1.13, 2.10, 2.22, 2.50, 3.0], dtype=np.float32)
    perfect_candidates, great_candidates, perfect_floor, great_floor = _engine_envelopes(timestamps)
    raw_fever_fill = 2.25
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=raw_fever_fill,
        non_fever_base=6,
        use_forced_great_timing=True,
    )
    options = edge_surface_option_details(
        i=0,
        first=True,
        n=int(timestamps.shape[0]),
        actions=actions,
        later_fill=later_fill,
        first_fill=first_fill,
        later_forced=later_forced,
        first_forced=first_forced,
        real_fever_time=1.0,
        use_forced_great_timing=True,
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=_lanes_for(timestamps),
        raw_fever_fill=raw_fever_fill,
    )

    capped = [
        option
        for option in options
        if int(option["activation_index"]) == 2
        and str(option["activation_judgment"]) == "late_great"
        and int(option.get("forced_run_count", 0)) == 0
    ]

    assert capped
    # The full window's activation is capped at the breakpoint; a fever that ends early caps it lower still, since its
    # cutoff must stay under the first out note's exit ceiling.
    longest = max(int(option["fever_end_index"]) for option in capped)
    full = [option for option in capped if int(option["fever_end_index"]) == longest]
    assert min(float(option["activation_hit_offset_upper_ms"]) for option in full) == pytest.approx(169.999, abs=0.01)
    assert all(float(option["activation_hit_offset_upper_ms"]) < 190.0 for option in capped)


def test_fg_response_numba_frontier_emits_capped_activation_breakpoints() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    timestamps = np.asarray([0.0, 0.5, 1.0, 1.13, 2.10, 2.22, 2.50, 3.0], dtype=np.float32)
    perfect_candidates = timestamps + np.float32(0.04)
    great_candidates = timestamps + np.float32(0.19)
    perfect_floor = timestamps - np.float32(0.019)
    great_floor = timestamps - np.float32(0.094)
    lanes = _lanes_for(timestamps)

    numba_frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=[timestamps],
        perfect_candidate_timestamps=[perfect_candidates],
        great_candidate_timestamps=[great_candidates],
        perfect_floor_timestamps=[perfect_floor],
        great_floor_timestamps=[great_floor],
        lanes=[lanes],
        geometries=[(2.25, 6, 1.0)],
        use_forced_great_timing=True,
    )[0]
    surfaces = {tuple(map(int, row)) for row in numba_frontier.first_frontier}
    assert (28, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0) in surfaces
    assert (60, 0, 0, 0, 36, 0, 0, 0, 0, 0, 0) in surfaces


def test_fg_response_numba_frontier_matches_shifted_head_region_offsets() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from tests.fg_response_frontier_oracles import input_engine_rebuild_first_frontier

    timestamps = np.asarray([0.0, 0.5, 1.0, 1.13, 2.10, 2.22, 2.50, 3.0], dtype=np.float32)
    perfect_candidates = timestamps + np.float32(0.04)
    great_candidates = timestamps + np.float32(0.19)
    perfect_floor = timestamps - np.float32(0.019)
    great_floor = timestamps - np.float32(0.094)
    lanes = _lanes_for(timestamps)

    oracle = input_engine_rebuild_first_frontier(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=lanes,
        raw_fever_fill=2.25,
        non_fever_base=6,
        real_fever_time=1.0,
        use_forced_great_timing=True,
    )
    numba_frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=[timestamps],
        perfect_candidate_timestamps=[perfect_candidates],
        great_candidate_timestamps=[great_candidates],
        perfect_floor_timestamps=[perfect_floor],
        great_floor_timestamps=[great_floor],
        lanes=[lanes],
        geometries=[(2.25, 6, 1.0)],
        use_forced_great_timing=True,
    )[0]

    oracle_surfaces = {tuple(map(int, row)) for row in oracle.first_frontier}
    numba_surfaces = {tuple(map(int, row)) for row in numba_frontier.first_frontier}

    assert (24, 0, 0, 0, 6, 0, 0, 0, 0, 0, 0) in oracle_surfaces
    assert (56, 0, 0, 0, 38, 0, 0, 0, 0, 0, 0) in oracle_surfaces
    assert numba_surfaces == oracle_surfaces


@pytest.mark.parametrize(
    ("fills", "eligible", "require_late", "expected_starts", "expected_ends"),
    [
        ([], [], False, [], []),
        ([4], [-1], False, [4], [4]),
        ([7, 2, 3, 3, 5, 6, 12], [0, 0, -1, 2, 3, -1, 0], False, [2, 5, 12], [3, 7, 12]),
        (
            [7, 2, 3, 3, 5, 6, 12],
            [0, 0, -1, 2, 3, -1, 0],
            True,
            [2, 5, 7, 12],
            [3, 5, 7, 12],
        ),
        ([9, 8, 7, 4, 2, 1, 0], [0] * 7, False, [0, 4, 7], [2, 4, 9]),
    ],
)
def test_fg_response_exact_fill_runs_preserve_arbitrary_membership(
    fills: list[int],
    eligible: list[int],
    require_late: bool,
    expected_starts: list[int],
    expected_ends: list[int],
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (
        _exact_action_fill_runs,
    )

    starts, ends = _exact_action_fill_runs(
        np.asarray(fills, dtype=np.int32),
        np.asarray(eligible, dtype=np.int32) if require_late else None,
    )
    assert starts.tolist() == expected_starts
    assert ends.tolist() == expected_ends


def test_fg_response_exact_fill_runs_reject_negative_offsets() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (
        _exact_action_fill_runs,
    )

    with pytest.raises(ValueError, match="must be nonnegative"):
        _exact_action_fill_runs(
            np.asarray([2, -1], dtype=np.int32),
        )


def test_fg_response_interval_successor_skips_removed_indices() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        HitTimes,
        _numba_successor_find,
        _numba_successor_remove,
    )

    successor = np.empty(9, dtype=np.int32)
    stamps = np.zeros(9, dtype=np.int32)
    epoch = 1
    assert _numba_successor_remove(successor, stamps, epoch, 2) == 3
    assert _numba_successor_remove(successor, stamps, epoch, 5) == 6
    assert _numba_successor_remove(successor, stamps, epoch, 3) == 4
    assert _numba_successor_remove(successor, stamps, epoch, 4) == 6
    assert _numba_successor_find(successor, stamps, epoch, 2) == 6
    assert _numba_successor_find(successor, stamps, epoch, 5) == 6
    assert _numba_successor_find(successor, stamps, epoch, 6) == 6

    # A new epoch makes every old removal logically live without clearing either scratch array.
    next_epoch = 2
    assert _numba_successor_find(successor, stamps, next_epoch, 2) == 2
    assert _numba_successor_find(successor, stamps, next_epoch, 5) == 5
    assert _numba_successor_remove(successor, stamps, next_epoch, 2) == 3
    assert _numba_successor_find(successor, stamps, next_epoch, 2) == 3


def test_fg_response_interval_successor_prepass_matches_retired_nested_scan() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        ActivationEnds,
        HitTimes,
        RegionTables,
        _numba_build_prefix_activation_hit_tables,
        _numba_first_frontier_reachability_prepass,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (
        _precompute_end_indices,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_reducer import (
        _exact_action_fill_runs,
    )
    from tests.retired_fg_frontier_semantics import (
        retired_nested_action_reachability_prepass,
    )

    rng = np.random.default_rng(20260712)
    n = 64
    timestamps = np.cumsum(rng.uniform(0.04, 0.28, size=n)).astype(np.float32)
    timestamps -= timestamps[0]
    perfect_candidates = (timestamps.astype(np.float64) + rng.uniform(0.035, 0.045, size=n)).astype(
        np.float32
    )
    great_candidates = (timestamps.astype(np.float64) + rng.uniform(0.18, 0.19, size=n)).astype(
        np.float32
    )
    perfect_floor = np.maximum.accumulate((timestamps.astype(np.float64) - 0.019).astype(np.float32))
    great_floor = np.maximum.accumulate((timestamps.astype(np.float64) - 0.095).astype(np.float32))
    lanes = rng.integers(0, 4, size=n, dtype=np.int32)
    (
        prefix_perfect_hit,
        prefix_perfect_valid,
        prefix_late_hit,
        prefix_late_valid,
    ) = _numba_build_prefix_activation_hit_tables(
        int(n),
        timestamps,
        perfect_candidates,
        great_candidates,
        perfect_candidates + np.float32(0.001),
    )
    real_times = np.asarray([0.45, 1.0, 2.25], dtype=np.float32)
    (
        real_time_index,
        _timestamp_end_idx,
        _perfect_end_idx,
        _great_end_idx,
        _great_floor_end_idx,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
        capped_perfect_exit_e,
        capped_late_exit_e,
    ) = _precompute_end_indices(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        prefix_perfect_hit=prefix_perfect_hit,
        prefix_late_hit=prefix_late_hit,
        exit_ceiling_timestamps=np.minimum.accumulate(perfect_candidates[::-1])[::-1],
        late_great_floor_timestamps=perfect_candidates + np.float32(0.001),
        lanes=lanes,
        real_times=real_times,
    )
    region_starts = np.zeros(n + 2, dtype=np.int64)
    empty_i32 = np.empty(0, dtype=np.int32)
    empty_f64 = np.empty(0, dtype=np.float64)

    for case_idx in range(80):
        action_count = int(rng.integers(0, 25))
        later_fill = rng.integers(0, n + 8, size=action_count, dtype=np.int32)
        first_fill = rng.integers(0, n + 8, size=action_count, dtype=np.int32)
        later_activation_forced = rng.integers(-1, 4, size=action_count, dtype=np.int32)
        first_activation_forced = rng.integers(-1, 4, size=action_count, dtype=np.int32)
        use_forced = int(case_idx % 2)
        real_time_idx = int(real_time_index[int(case_idx % len(real_times))])
        common = {
            "n": int(n),
            "action_count": int(action_count),
            "later_fill": later_fill,
            "first_fill": first_fill,
            "later_activation_forced": later_activation_forced,
            "first_activation_forced": first_activation_forced,
            "prefix_perfect_hit": prefix_perfect_hit,
            "prefix_perfect_valid": prefix_perfect_valid,
            "prefix_late_hit": prefix_late_hit,
            "prefix_late_valid": prefix_late_valid,
            "capped_perfect_edge_e": capped_perfect_edge_e,
            "capped_late_edge_e": capped_late_edge_e,
            "capped_eg_perfect_e": capped_eg_perfect_e,
            "capped_eg_late_e": capped_eg_late_e,
            "capped_perfect_exit_e": capped_perfect_exit_e,
            "capped_late_exit_e": capped_late_exit_e,
            "real_fever_time": float(real_times[int(case_idx % len(real_times))]),
            "real_time_idx": int(real_time_idx),
            "use_forced_great_timing_i": int(use_forced),
            "region_starts": region_starts,
            "region_offsets": empty_i32,
            "region_activations": empty_i32,
            "region_great_ends": empty_i32,
            "region_is_greats": empty_i32,
            "region_act_hits": empty_f64,
            "region_perfect_hits": empty_f64,
            "region_perfect_valids": empty_i32,
            "perfect_floor_timestamps": perfect_floor,
            "great_floor_timestamps": great_floor,
        }
        expected_reachable, expected_width = retired_nested_action_reachability_prepass(**common)
        perfect_run_starts, perfect_run_ends = _exact_action_fill_runs(later_fill)
        late_run_starts, late_run_ends = _exact_action_fill_runs(
            later_fill, later_activation_forced
        )
        perfect_successor = np.empty(n + 1, dtype=np.int32)
        perfect_successor_stamps = np.zeros(n + 1, dtype=np.int32)
        late_successor = np.empty(n + 1, dtype=np.int32)
        late_successor_stamps = np.zeros(n + 1, dtype=np.int32)
        actual_reachable, actual_width = _numba_first_frontier_reachability_prepass(
            int(common["n"]),
            int(common["action_count"]),
            common["first_fill"],
            common["first_activation_forced"],
            perfect_run_starts,
            perfect_run_ends,
            late_run_starts,
            late_run_ends,
            ActivationEnds(
                common["prefix_perfect_hit"],
                common["prefix_perfect_valid"],
                common["prefix_late_hit"],
                common["prefix_late_valid"],
                *(table[int(real_time_idx)] for table in (
                    capped_perfect_edge_e, capped_late_edge_e, capped_eg_perfect_e, capped_eg_late_e,
                    capped_perfect_exit_e, capped_late_exit_e,
                )),
            ),
            float(common["real_fever_time"]),
            int(common["use_forced_great_timing_i"]),
            RegionTables(
                common["region_starts"], common["region_offsets"], common["region_activations"],
                common["region_great_ends"], common["region_is_greats"], empty_i32, empty_i32,
                common["region_perfect_valids"], perfect_floor, great_floor,
            ),
            common["great_floor_timestamps"],
            perfect_successor,
            perfect_successor_stamps,
            late_successor,
            late_successor_stamps,
            1,
        )
        assert np.array_equal(actual_reachable, expected_reachable), case_idx
        assert int(actual_width) == int(expected_width), case_idx


def test_fg_response_exact_schedule_query_matches_python_witness() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
        activation_schedule_witnesses_weighted_lane_aware,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        HitTimes,
        _numba_activation_reachable_contiguous_run,
        _numba_region2_k_scan_stop,
        _numba_region2_offset_for_count,
    )

    def full_scan(
        *,
        activation_index: int,
        activation_hit_timestamp: float,
        timestamps: np.ndarray,
        perfect_floor_timestamps: np.ndarray,
        perfect_candidate_timestamps: np.ndarray,
        great_floor_timestamps: np.ndarray,
        great_candidate_timestamps: np.ndarray,
        lanes: np.ndarray,
        fever_fill_denom: float,
        section_start: int,
        section_end: int,
        great_start: int,
        great_count: int,
        activation_great_i: int,
    ) -> bool:
        a = int(activation_index)
        start = int(section_start)
        end = int(section_end)
        if start < 0 or end < start or not (start <= a < end):
            return False
        g0 = max(start, int(great_start), 0)
        g1 = min(end, int(great_start) + int(great_count))
        if g1 < g0:
            g1 = g0
        activation_is_great = int(activation_great_i) != 0 or (g0 <= a < g1)
        is_great = np.zeros(int(timestamps.shape[0]), dtype=np.bool_)
        is_great[g0:g1] = True
        if activation_is_great:
            is_great[a] = True
        lows = np.where(is_great, great_floor_timestamps, perfect_floor_timestamps)
        highs = np.where(is_great, great_candidate_timestamps, perfect_candidate_timestamps)
        fill_units = np.where(is_great, 0.5, 1.0).astype(np.float32)
        preactivation_count = int(a) - int(start)
        preactivation_great_count = int(np.count_nonzero(is_great[start:a]))
        return bool(
            activation_schedule_witnesses_weighted_lane_aware(
                activation_index=a,
                activation_hit_timestamp=float(activation_hit_timestamp),
                low_hit_timestamps=lows,
                high_hit_timestamps=highs,
                lanes=lanes,
                fill_units=fill_units,
                fever_fill_denom=float(fever_fill_denom),
                section_start=start,
                section_end=end,
                required_preactivation_fill_half_units=(
                    2 * int(preactivation_count) - int(preactivation_great_count)
                ),
                required_preactivation_event_count=int(preactivation_count),
            )
        )

    rng = np.random.default_rng(20260706)
    gaps = rng.uniform(0.04, 0.31, size=48).astype(np.float64)
    timestamps = np.cumsum(gaps).astype(np.float32)
    timestamps -= timestamps[0]
    perfect_floor = np.maximum.accumulate((timestamps.astype(np.float64) - 0.019).astype(np.float32))
    great_floor = np.maximum.accumulate((timestamps.astype(np.float64) - 0.095).astype(np.float32))
    perfect_candidates = (timestamps.astype(np.float64) + rng.uniform(0.035, 0.045, size=48)).astype(np.float32)
    great_candidates = (timestamps.astype(np.float64) + rng.uniform(0.18, 0.19, size=48)).astype(np.float32)
    lanes = rng.integers(0, 4, size=48, dtype=np.int32)
    for _ in range(300):
        section_start = int(rng.integers(0, 47))
        section_end = int(rng.integers(section_start + 1, 49))
        activation = int(rng.integers(section_start, section_end))
        great_start = int(rng.integers(max(0, section_start - 2), min(48, section_end + 2)))
        great_count = int(rng.integers(0, min(10, 48 - great_start) + 1))
        activation_great_i = int(rng.integers(0, 2))
        hit = (
            great_candidates[activation]
            if activation_great_i or great_start <= activation < great_start + great_count
            else perfect_candidates[activation]
        )
        denom = float(rng.choice(np.asarray([1.25, 2.25, 3.5, 8.0, 63.2118], dtype=np.float64)))
        assert bool(
            _numba_activation_reachable_contiguous_run(
                activation,
                float(hit),
                timestamps,
                HitTimes(perfect_floor,
                perfect_candidates,
                great_floor,
                great_candidates,
                perfect_candidates + np.float32(0.001)),
                lanes,
                denom,
                section_start,
                section_end,
                great_start,
                great_count,
                activation_great_i,
            )
        ) is full_scan(
            activation_index=activation,
            activation_hit_timestamp=float(hit),
            timestamps=timestamps,
            perfect_floor_timestamps=perfect_floor,
            perfect_candidate_timestamps=perfect_candidates,
            great_floor_timestamps=great_floor,
            great_candidate_timestamps=great_candidates,
            lanes=lanes,
            fever_fill_denom=denom,
            section_start=section_start,
            section_end=section_end,
            great_start=great_start,
            great_count=great_count,
            activation_great_i=activation_great_i,
        )

    for action_count in (1, 2, 5, 64, 274):
        for denom in (1.25, 2.25, 3.5, 8.0, 63.2118, 273.726):
            stop = int(_numba_region2_k_scan_stop(int(action_count), float(denom)))
            for start in (0, 1, 17, 46):
                for k in range(stop, int(action_count)):
                    assert _numba_region2_offset_for_count(int(start), int(k), float(denom), 48) < 1


@pytest.mark.parametrize(
    (
        "timestamps",
        "lanes",
        "raw_fever_fill",
        "non_fever_base",
        "real_fever_time",
    ),
    [
        (
            np.asarray([0.0, 0.5, 1.0, 1.13, 2.10, 2.22, 2.50, 3.0], dtype=np.float32),
            np.arange(8, dtype=np.int32),
            2.25,
            6,
            1.0,
        ),
        (
            np.asarray([0.0, 0.24, 0.48, 0.72, 0.96, 1.10, 1.10, 1.10, 1.32], dtype=np.float32),
            np.asarray([0, 1, 2, 3, 0, 1, 2, 3, 1], dtype=np.int32),
            4.25,
            8,
            0.55,
        ),
        (
            np.asarray([0.0, 0.25, 0.50, 0.76, 1.01, 1.28, 1.55, 1.83, 2.12], dtype=np.float32),
            np.asarray([0, 1, 0, 2, 1, 3, 0, 2, 3], dtype=np.int32),
            2.25,
            6,
            0.42,
        ),
    ],
)
def test_fg_response_frontier_dominates_bruteforce_pg_contiguous_run_oracle(
    timestamps: np.ndarray,
    lanes: np.ndarray,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    perfect_candidates = timestamps + np.float32(0.04)
    great_candidates = timestamps + np.float32(0.19)
    perfect_floor = timestamps - np.float32(0.019)
    great_floor = timestamps - np.float32(0.094)

    oracle_surfaces = _bruteforce_pg_contiguous_run_first_frontier(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=lanes,
        raw_fever_fill=raw_fever_fill,
        non_fever_base=non_fever_base,
        real_fever_time=real_fever_time,
    )
    production = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=lanes,
        geometries=((raw_fever_fill, non_fever_base, real_fever_time),),
        use_forced_great_timing=True,
    )[0]

    missing = _missing_pg_oracle_surfaces(production.first_frontier, oracle_surfaces)
    assert not missing, (
        f"production frontier missed {len(missing)} legal P/G oracle surfaces "
        f"(production={len(production.first_frontier)}, oracle={len(oracle_surfaces)}): {missing[:8]}"
    )


@pytest.mark.parametrize(
    ("timestamps", "lanes", "raw_fever_fill", "non_fever_base", "real_fever_time"),
    [
        (
            np.asarray([0.0, 0.16, 0.31, 0.31, 0.46, 0.62, 0.79], dtype=np.float32),
            np.asarray([0, 1, 0, 2, 1, 3, 0], dtype=np.int32),
            3.25,
            0,
            0.38,
        ),
        (
            np.asarray([0.0, 0.24, 0.48, 0.72, 0.96, 1.10, 1.10, 1.32], dtype=np.float32),
            np.asarray([0, 1, 2, 3, 0, 1, 2, 1], dtype=np.int32),
            4.25,
            0,
            0.55,
        ),
    ],
)
def test_base_response_frontier_preserves_bruteforce_all_perfect_optima(
    timestamps: np.ndarray,
    lanes: np.ndarray,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
) -> None:
    """Base mode may prune only surfaces that cannot win under any legal stat allocation."""
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    perfect_candidates = timestamps + np.float32(0.04)
    perfect_floor = timestamps - np.float32(0.019)
    oracle = _bruteforce_pg_contiguous_run_first_frontier(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=timestamps + np.float32(0.19),
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=timestamps - np.float32(0.094),
        lanes=lanes,
        raw_fever_fill=raw_fever_fill,
        non_fever_base=non_fever_base,
        real_fever_time=real_fever_time,
    )
    all_perfect_oracle = tuple(
        surface
        for surface in oracle
        if int(surface.great0 | surface.great1 | surface.great2 | surface.great3) == 0
        and int(surface.body_great) == 0
        and int(surface.body_fever_great) == 0
    )
    production = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=perfect_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=perfect_floor,
        lanes=lanes,
        geometries=((raw_fever_fill, non_fever_base, real_fever_time),),
        use_forced_great_timing=False,
    )[0].first_frontier

    assert all_perfect_oracle
    assert all(
        int(surface.great0 | surface.great1 | surface.great2 | surface.great3) == 0
        and int(surface.body_great) == 0
        and int(surface.body_fever_great) == 0
        for surface in production
    )
    missing = _missing_pg_oracle_surfaces(production, all_perfect_oracle)
    assert not missing, (
        f"Base producer discarded {len(missing)} legal all-Perfect oracle surfaces "
        f"(production={len(production)}, oracle={len(all_perfect_oracle)}): {missing[:8]}"
    )


def test_base_large_fill_uses_shared_input_engine_recurrence() -> None:
    """A body-only Base chart must not bypass capped activation ownership."""
    from gear_optimizer.chart import load_chart
    from gear_optimizer.solver.timing_envelope import time_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from tests.fg_response_frontier_oracles import input_engine_rebuild_first_frontier

    chart_path = ROOT / "Data" / "Normal" / "Sweat Around The World (Intense Mix) by Just Sweat [Just Dance].txt"
    song_inputs = time_song(load_chart(str(chart_path)), "precise").fg_inputs
    fill_count = 112.0
    real_fever_time = 33.10281210926771

    oracle = input_engine_rebuild_first_frontier(
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.perfect_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.perfect_floor,
        lanes=song_inputs.lanes,
        raw_fever_fill=fill_count,
        non_fever_base=0,
        real_fever_time=real_fever_time,
        use_forced_great_timing=False,
    )
    production = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=[song_inputs.timestamps],
        perfect_candidate_timestamps=[song_inputs.perfect_candidates],
        great_candidate_timestamps=[song_inputs.perfect_candidates],
        perfect_floor_timestamps=[song_inputs.perfect_floor],
        great_floor_timestamps=[song_inputs.perfect_floor],
        lanes=[song_inputs.lanes],
        geometries=[(fill_count, 0, real_fever_time)],
        use_forced_great_timing=False,
    )[0]

    expected = ((0, 0, 0, 0, 0, 0, 0, 0, 640, 0, 0),)
    assert tuple(tuple(map(int, row)) for row in oracle.first_frontier) == expected
    assert tuple(tuple(map(int, row)) for row in production.first_frontier) == expected


def _ordered_rows_digest(value) -> str:
    return hashlib.blake2b(repr(value).encode("utf-8"), digest_size=16).hexdigest()


class _BodyReducerDifferentialHarness:
    def __init__(self, *, pair_mod: int = 33, normal_great_capacity: int = 65) -> None:
        from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
            HitTimes,
            _numba_reduce_touched_body_pairs,
            _numba_touch_body_candidate,
        )

        self._reduce = _numba_reduce_touched_body_pairs
        self._touch = _numba_touch_body_candidate
        self.pair_mod = int(pair_mod)
        pair_size = int(normal_great_capacity) * int(pair_mod)
        self.pair_stamp = np.zeros((pair_size,), dtype=np.int32)
        self.best_fever_by_pair = np.zeros((pair_size,), dtype=np.int32)
        self.touched_pair = np.empty((pair_size,), dtype=np.int32)
        self.bit_values = np.zeros((int(pair_mod) + 1,), dtype=np.int32)
        self.bit_stamps = np.zeros((int(pair_mod) + 1,), dtype=np.int32)
        self.frontier_values = np.empty((1, 3), dtype=np.uint64)
        self.stamp = 0

    def reduce(self, rows) -> tuple[list[tuple[int, int, int]], list[tuple[int, int, int]]]:
        from tests.retired_fg_frontier_semantics import retired_body_reduce_from_raw_candidates

        self.stamp += 1
        touched_count = 0
        for body_fever, body_great, body_fever_great in rows:
            touched_count = self._touch(
                np.uint64(body_fever),
                np.uint64(body_great),
                np.uint64(body_fever_great),
                np.uint64(0),
                np.uint64(0),
                np.uint64(0),
                int(self.pair_mod),
                int(self.stamp),
                self.pair_stamp,
                self.best_fever_by_pair,
                self.touched_pair,
                int(touched_count),
            )
        self.last_touched_count = int(touched_count)
        self.last_touched_pairs = [
            int(value) for value in self.touched_pair[: int(touched_count)]
        ]
        self.last_best_fever_by_pair = {
            int(pair_idx): int(self.best_fever_by_pair[int(pair_idx)])
            for pair_idx in self.last_touched_pairs
        }
        reference = retired_body_reduce_from_raw_candidates(
            rows,
            pair_mod=int(self.pair_mod),
        )
        self.frontier_values, count = self._reduce(
            int(self.pair_mod),
            self.touched_pair,
            int(touched_count),
            self.best_fever_by_pair,
            self.bit_values,
            self.bit_stamps,
            int(self.stamp),
            self.frontier_values,
        )
        actual = [
            tuple(int(value) for value in row)
            for row in self.frontier_values[: int(count)]
        ]
        return actual, reference


def test_fg_response_fused_body_reduce_matches_retired_edge_case_matrix() -> None:
    cases = [
        ("empty", ()),
        ("one-row", ((4, 0, 0),)),
        ("two-row", ((3, 0, 0), (7, 2, 1))),
        ("dominated-and-duplicate-pair", ((10, 0, 0), (9, 1, 1), (12, 0, 0))),
        ("collinear-hull", ((2, 0, 0), (4, 1, 1), (6, 2, 2), (8, 3, 3))),
        (
            "multiple-normal-great-levels",
            ((2, 0, 0), (5, 2, 1), (7, 4, 2), (8, 4, 1), (11, 7, 3)),
        ),
        (
            "output-growth",
            tuple((normal_great + 1, normal_great, 0) for normal_great in range(20)),
        ),
        ("reuse-after-growth", ((20, 4, 2), (19, 5, 2), (21, 7, 3))),
    ]
    harness = _BodyReducerDifferentialHarness()
    ordered_outputs = []
    for name, rows in cases:
        actual, reference = harness.reduce(rows)
        assert actual == reference, name
        ordered_outputs.append((name, actual))

    assert len(cases) == 8
    assert harness.pair_stamp.dtype == np.dtype(np.int32)
    assert harness.best_fever_by_pair.dtype == np.dtype(np.int32)
    assert harness.touched_pair.dtype == np.dtype(np.int32)
    assert harness.bit_values.dtype == np.dtype(np.int32)
    assert harness.bit_stamps.dtype == np.dtype(np.int32)
    assert harness.frontier_values.dtype == np.dtype(np.uint64)
    assert harness.frontier_values.shape == (32, 3)
    assert _ordered_rows_digest(ordered_outputs) == "caf27bad32e81f377f7f4536b82218fd"


def test_fg_response_body_touch_first_stamp_duplicate_and_tie_contract() -> None:
    from tests.retired_fg_frontier_semantics import (
        retired_touch_body_candidates,
        retired_two_stage_body_reduce,
    )

    harness = _BodyReducerDifferentialHarness(pair_mod=17)
    rows = ((5, 9, 3), (11, 9, 3), (11, 9, 3), (7, 9, 3))
    pair_idx = 6 * 17 + 3

    actual, reference = harness.reduce(rows)
    retired_touched, retired_best = retired_touch_body_candidates(rows, pair_mod=17)

    assert actual == reference == [(11, 9, 3)]
    assert harness.last_touched_count == 1
    assert harness.last_touched_pairs == [pair_idx]
    assert harness.last_best_fever_by_pair == {pair_idx: 11}
    assert retired_touched == [pair_idx]
    assert retired_best == {pair_idx: 11}
    assert retired_two_stage_body_reduce(
        pair_mod=17,
        touched_pair=[pair_idx, pair_idx],
        best_fever_by_pair={pair_idx: 11},
    ) == [(11, 9, 3)]


def test_fg_response_fused_body_reduce_matches_retired_randomized_production_shapes() -> None:
    rng = np.random.default_rng(116_20260710)
    harness = _BodyReducerDifferentialHarness()
    ordered_outputs = []
    for case_idx in range(256):
        row_count = int(rng.integers(0, 81))
        rows = []
        for _ in range(row_count):
            fever_great = int(rng.integers(0, harness.pair_mod))
            normal_great = int(rng.integers(0, 48))
            body_fever = int(rng.integers(fever_great, 181))
            assert 0 <= fever_great <= body_fever
            assert normal_great >= 0
            rows.append((body_fever, normal_great + fever_great, fever_great))
        actual, reference = harness.reduce(rows)
        assert actual == reference, f"randomized body case {case_idx}"
        ordered_outputs.append(actual)

    assert len(ordered_outputs) == 256
    assert _ordered_rows_digest(ordered_outputs) == "df557def33f781b6c69582442ba71e09"


def test_fg_response_retaliation_first_frontier_surfaces_reconstruct() -> None:
    from gear_optimizer.gamedata import load_stat_curves
    from gear_optimizer.chart import load_chart
    from gear_optimizer.solver.timing_envelope import time_song
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        build_force_greats_response_first_frontiers_gpu_batch,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        reconstruct_force_greats_response_trace,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_cache_keys import _response_axes
    from gear_optimizer.solver.taichi_gem.force_greats.response_types import FgResponseSurface

    song = time_song(load_chart(str(ROOT / "Data" / "Normal" / "Retaliation by Juggernaut.txt")), "precise")
    curves = load_stat_curves(ROOT / "Data" / "Gear" / "Stats.txt")
    song_inputs, raw_fill_by_ff, non_fever_base_by_ff, real_time_by_ft = _response_axes(song, curves)
    raw_fever_fill = float(raw_fill_by_ff[67])
    non_fever_base = int(non_fever_base_by_ff[67])
    real_fever_time = float(real_time_by_ft[51])

    frontier = build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        lanes=song_inputs.lanes,
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
            perfect_floor_timestamps=song_inputs.perfect_floor,
            great_floor_timestamps=song_inputs.great_floor,
            lanes=song_inputs.lanes,
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
            lanes=_lanes_for(timestamps),
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
        _build_activation_reachability_context,
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
    perfect_candidates, great_candidates, perfect_floor, great_floor = _engine_envelopes(timestamps)
    raw_fever_fill = 2.25
    non_fever_base = 7
    real_fever_time = 0.55
    lanes = _lanes_for(timestamps)
    slim = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        perfect_candidate_timestamps=perfect_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=lanes,
        geometries=((raw_fever_fill, non_fever_base, real_fever_time),),
        use_forced_great_timing=True,
    )[0]
    target = slim.first_frontier[-1]

    counts = reconstruct_force_greats_response_counts(
        frontier=slim,
        target_surface=target,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        perfect_candidate_timestamps=perfect_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=lanes,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
        use_forced_great_timing=True,
    )
    trace = reconstruct_force_greats_response_trace(
        non_fever_base=int(slim.non_fever_base),
        target_surface=target,
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        perfect_candidate_timestamps=perfect_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        lanes=lanes,
        raw_fever_fill=raw_fever_fill,
        real_fever_time=real_fever_time,
        use_forced_great_timing=True,
    )

    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=raw_fever_fill,
        non_fever_base=non_fever_base,
        use_forced_great_timing=True,
    )
    reachability_context = _build_activation_reachability_context(
        timestamps=timestamps,
        perfect_floor_timestamps=perfect_floor,
        perfect_candidate_timestamps=perfect_candidates,
        great_floor_timestamps=great_floor,
        great_candidate_timestamps=great_candidates,
        lanes=lanes,
        fever_fill_denom=raw_fever_fill,
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
    for row in trace:
        edge_match = None
        for option in _edge_surface_options(
            reachability_context=reachability_context,
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
            perfect_candidate_timestamps=perfect_candidates,
            great_candidate_timestamps=great_candidates,
            perfect_floor_timestamps=perfect_floor,
            great_floor_timestamps=great_floor,
            lanes=lanes,
            raw_fever_fill=raw_fever_fill,
        ):
            if (
                int(option["next_state"]) == int(row["next_state"])
                and int(option["fever_end_index"]) == int(row["fever_end_index"])
                and int(option["activation_index"]) == int(row["activation_index"])
                and str(option["activation_judgment"]) == str(row["activation_judgment"])
                and int(option.get("forced_run_start_index", option["forced_start_index"]))
                == int(row.get("forced_run_start_index", row["forced_start_index"]))
                and int(option["forced_run_count"])
                == int(row["forced_run_count"])
                and int(option.get("early_great_start", -1)) == int(row.get("early_great_start", -1))
                and int(option.get("early_great_end", -1)) == int(row.get("early_great_end", -1))
            ):
                edge_match = (int(option["next_state"]), option["surface"])
                break
        assert edge_match is not None
        state, edge = edge_match
        surface = _combine_surface(surface, edge)
        first = False

    assert surface == target
