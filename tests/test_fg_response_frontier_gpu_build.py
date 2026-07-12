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
    from gear_optimizer.solver.input_engine_breakpoints import latest_activation_hit_for_contiguous_great_run
    from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
        activation_hit_is_reachable_weighted_lane_aware,
        server_fill_crossing_run,
    )
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_batch import (
        _combine_surfaces,
        _reduce_surfaces,
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
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_precompute

    timestamps = np.arange(12, dtype=np.float32) * np.float32(0.1)
    perfect_hi = timestamps + np.float32(0.04)
    great_hi = timestamps + np.float32(0.09)
    _hit_values, hit_token_to_id = response_build_gpu_precompute._region_hit_value_universe(
        timestamps,
        perfect_hi,
        great_hi,
    )
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
        0.1,
        timestamps - np.float32(0.04),
        perfect_hi,
        timestamps - np.float32(0.09),
        great_hi,
        np.arange(12, dtype=np.int32),
        hit_token_to_id,
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


def test_fg_region_hit_universe_resolves_exact_producer_values() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import (
        response_build_gpu_numba,
        response_build_gpu_precompute,
    )

    timestamps = np.asarray([0.0, 0.3, 0.3, 0.8, 1.1, 1.6, 2.0, 2.0], dtype=np.float32)
    perfect_hi = timestamps + np.asarray(
        [0.04, -0.01, 0.07, 0.0, 0.05, 0.03, 0.08, 0.02], dtype=np.float32
    )
    great_hi = timestamps + np.asarray(
        [0.12, 0.08, 0.19, 0.11, 0.2, 0.09, 0.16, 0.14], dtype=np.float32
    )
    hit_values, token_to_id = response_build_gpu_precompute._region_hit_value_universe(
        timestamps,
        perfect_hi,
        great_hi,
    )

    expected_token_values = np.concatenate(
        (
            timestamps.astype(np.float64),
            perfect_hi.astype(np.float64),
            great_hi.astype(np.float64),
            perfect_hi.astype(np.float64) - 1.0e-6,
            great_hi.astype(np.float64) - 1.0e-6,
        )
    )
    np.testing.assert_array_equal(hit_values[token_to_id], expected_token_values)

    n = int(timestamps.shape[0])
    for activation in range(n):
        for great_start, great_count in ((activation, 0), (max(0, activation - 1), 2)):
            for selector in (
                response_build_gpu_numba._numba_perfect_activation_hit_for_run,
                response_build_gpu_numba._numba_late_great_activation_hit_for_run,
            ):
                hit, valid, token = selector(
                    activation,
                    timestamps,
                    perfect_hi,
                    great_hi,
                    great_start,
                    great_count,
                    n,
                )
                if int(valid) != 0:
                    assert 0 <= int(token) < int(token_to_id.shape[0])
                    assert float(hit_values[int(token_to_id[int(token)])]) == float(hit)
                else:
                    assert int(token) == -1


def test_fg_region_hit_endpoint_tables_match_scalar_production_search() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import (
        response_build_gpu_numba,
        response_build_gpu_precompute,
    )

    timestamps = np.asarray([0.0, 0.2, 0.55, 0.9, 1.4, 1.4, 2.1], dtype=np.float32)
    perfect_hi = timestamps + np.float32(0.04)
    great_hi = timestamps + np.float32(0.13)
    perfect_floor = timestamps - np.float32(0.035)
    great_floor = timestamps - np.float32(0.11)
    hit_values, _token_to_id = response_build_gpu_precompute._region_hit_value_universe(
        timestamps,
        perfect_hi,
        great_hi,
    )

    real_times = np.asarray([0.0, 0.37, 1.75], dtype=np.float64)
    perfect_end_table, great_end_table = (
        response_build_gpu_precompute._region_hit_end_index_tables(
            hit_values,
            real_times,
            perfect_floor,
            great_floor,
        )
    )
    n = int(timestamps.shape[0])
    for real_time_idx, real_fever_time in enumerate(real_times):
        perfect_end = perfect_end_table[int(real_time_idx)]
        great_end = great_end_table[int(real_time_idx)]
        for activation in range(n):
            for hit_id, hit in enumerate(hit_values):
                expected_perfect = response_build_gpu_numba._numba_edge_end_idx_at_hit(
                    n,
                    activation,
                    float(hit),
                    real_fever_time,
                    perfect_floor,
                )
                expected_great = response_build_gpu_numba._numba_great_floor_extended_end_at_hit(
                    n,
                    activation,
                    float(hit),
                    real_fever_time,
                    great_floor,
                )
                actual_perfect = response_build_gpu_numba._numba_clamped_end_idx(
                    n,
                    activation,
                    int(perfect_end[hit_id]),
                )
                actual_great = response_build_gpu_numba._numba_clamped_end_idx(
                    n,
                    activation,
                    int(great_end[hit_id]),
                )
                assert int(actual_perfect) == int(expected_perfect)
                assert int(actual_great) == int(expected_great)


@pytest.mark.parametrize(
    ("real_times", "message"),
    [
        (np.asarray([1.0, 1.0], dtype=np.float64), "strictly increasing"),
        (np.asarray([2.0, 1.0], dtype=np.float64), "strictly increasing"),
        (np.asarray([1.0, np.inf], dtype=np.float64), "non-finite"),
    ],
)
def test_fg_region_hit_endpoint_tables_reject_invalid_real_time_axis(
    real_times: np.ndarray,
    message: str,
) -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_precompute

    with pytest.raises(ValueError, match=message):
        response_build_gpu_precompute._region_hit_end_index_tables(
            np.asarray([0.0], dtype=np.float64),
            real_times,
            np.asarray([0.0], dtype=np.float32),
            np.asarray([0.0], dtype=np.float32),
        )


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

    relative_sources = {
        source.relative_to(response_cache_types._SOLVER_DIR.parent).as_posix()
        for source in response_cache_types._FG_GAME_ENGINE_SOURCES
    }
    assert relative_sources == {
        "core/constants.py",
        "core/time_quantize.py",
        "solver/fg_response_scoring/note_graph.py",
        "solver/input_engine_breakpoints.py",
        "solver/scoring/fg_policy.py",
        "solver/timing_envelope.py",
    }
    assert set(response_cache_types._FG_GAME_ENGINE_SOURCES).issubset(
        response_cache_types._FG_DP_SOURCES
    )


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
    assert stats["region_hit_values"] == 0
    assert stats["region_hit_endpoint_bytes"] == 0


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
    )

    for activation in range(n):
        expected_hit, expected_valid, _expected_token = rb._numba_perfect_activation_hit_for_run(
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

        expected_late_hit, expected_late_valid, _expected_late_token = (
            rb._numba_late_great_activation_hit_for_run(
                activation,
                timestamps,
                perfect_hi,
                great_hi,
                activation,
                1,
                n,
            )
        )
        assert int(late_valid[activation]) == int(expected_late_valid)
        assert float(late_hit[activation]) == pytest.approx(float(expected_late_hit))

        for great_start in range(max(0, activation - 3), activation + 1):
            great_count = max(0, activation - great_start)
            direct_hit, direct_valid, _direct_token = rb._numba_perfect_activation_hit_for_run(
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

            direct_late_hit, direct_late_valid, _direct_late_token = (
                rb._numba_late_great_activation_hit_for_run(
                    activation,
                    timestamps,
                    perfect_hi,
                    great_hi,
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
    hit_values, hit_token_to_id = response_build_gpu_precompute._region_hit_value_universe(
        timestamps,
        perfect_candidates,
        great_candidates,
    )
    perfect_end_table, great_end_table = (
        response_build_gpu_precompute._region_hit_end_index_tables(
            hit_values,
            np.asarray([1.75], dtype=np.float64),
            perfect_floor,
            great_floor,
        )
    )
    perfect_end_by_hit = perfect_end_table[0]
    great_end_by_hit = great_end_table[0]
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
                    0.190001,
                    perfect_floor,
                    perfect_candidates,
                    great_floor,
                    great_candidates,
                    lanes,
                    hit_token_to_id,
                    perfect_end_by_hit,
                    great_end_by_hit,
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
    region_calls = 0
    real_precompute = response_build_gpu_precompute._precompute_end_indices
    real_region_precompute = response_build_gpu_batch._region_hit_end_index_tables
    previous_threads = response_build_gpu_reducer.configure_force_greats_response_first_frontier_threads(1)

    def _record_precompute(**kwargs):
        nonlocal calls
        calls += 1
        return real_precompute(**kwargs)

    def _fake_first_frontier(**_kwargs):
        return result

    def _record_region_precompute(*args, **kwargs):
        nonlocal region_calls
        region_calls += 1
        return real_region_precompute(*args, **kwargs)

    monkeypatch.setattr(response_build_gpu_precompute, "_precompute_end_indices", _record_precompute)
    monkeypatch.setattr(
        response_build_gpu_batch,
        "_region_hit_end_index_tables",
        _record_region_precompute,
    )
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
    assert region_calls == 1
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
    perfect_candidates = timestamps.copy()
    perfect_candidates[2] = np.float32(2.5)
    great_candidates = timestamps.copy()

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
            lanes=_lanes_for(timestamps),
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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
            lanes=_lanes_for(timestamps),
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
            lanes=_lanes_for(timestamps),
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
        _numba_edge_end_idx_from_tables,
    )

    timestamps = np.asarray([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float32)
    great_candidates = timestamps.copy()
    great_candidates[0] = np.float32(2.4)
    great_candidates[1] = np.float32(1.1)
    timestamp_end_idx = np.searchsorted(timestamps, timestamps + np.float32(1.0), side="left").astype(np.int32)
    perfect_end_idx = timestamp_end_idx.copy()
    great_end_idx = np.searchsorted(timestamps, great_candidates + np.float32(1.0), side="left").astype(np.int32)
    # A later Great end at the activation index that a PERFECT activation must NOT carry.
    great_end_idx[2] = 4

    edge_end = _numba_edge_end_idx_from_tables(
        int(timestamps.shape[0]),
        2,
        0,
        1,
        timestamp_end_idx.reshape(1, -1),
        perfect_end_idx.reshape(1, -1),
        great_end_idx.reshape(1, -1),
        0,
    )

    assert edge_end == 3


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
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as rb

    prefix_perfect_hit, _prefix_perfect_valid, prefix_late_hit, _prefix_late_valid = (
        rb._numba_build_prefix_activation_hit_tables(
            int(song_inputs.timestamps.shape[0]),
            song_inputs.timestamps,
            song_inputs.perfect_candidates,
            song_inputs.great_candidates,
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
    ) = _precompute_end_indices(
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        prefix_perfect_hit=prefix_perfect_hit,
        prefix_late_hit=prefix_late_hit,
        lanes=song_inputs.lanes,
        real_times=np.asarray([real_fever_time], dtype=np.float64),
    )
    rt_idx = int(real_time_index[0])
    # Input-engine-aware precompute preserves the raw per-note Perfect clock. Reachability is checked
    # later by reconstruction/persistence with lane and surface context.
    reachable_pc = song_inputs.perfect_candidates

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
    perfect_candidates = timestamps + np.float32(0.04)
    great_candidates = timestamps + np.float32(0.18)
    perfect_floor = timestamps - np.float32(0.019)
    great_floor = timestamps - np.float32(0.094)
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
        and int(option.get("forced_run_count", option["forced_prefix_count"])) == 1
        for option in options
    )
    bundle = [
        option
        for option in options
        if int(option["activation_index"]) == 102
        and str(option["activation_judgment"]) == "late_great"
        and int(option.get("forced_run_start_index", option["forced_start_index"])) == 102
        and int(option.get("forced_run_count", option["forced_prefix_count"])) == 2
    ]
    assert bundle
    assert any(int(option["surface"].body_fever_great) >= 2 for option in bundle)


def test_fg_response_frontier_caps_activation_at_following_label_breakpoint() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
        _action_table,
        _edge_surface_option_details,
    )

    timestamps = np.asarray([0.0, 0.5, 1.0, 1.13, 2.10, 2.22, 2.50, 3.0], dtype=np.float32)
    perfect_candidates = timestamps + np.float32(0.04)
    great_candidates = timestamps + np.float32(0.19)
    perfect_floor = timestamps - np.float32(0.019)
    great_floor = timestamps - np.float32(0.094)
    raw_fever_fill = 2.25
    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=raw_fever_fill,
        non_fever_base=6,
        use_forced_great_timing=True,
    )
    options = _edge_surface_option_details(
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
    assert min(float(option["activation_hit_offset_upper_ms"]) for option in capped) == pytest.approx(
        169.999,
        abs=0.01,
    )
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
        _input_engine_rebuild_first_frontier,
        build_force_greats_response_first_frontiers_gpu_batch,
    )

    timestamps = np.asarray([0.0, 0.5, 1.0, 1.13, 2.10, 2.22, 2.50, 3.0], dtype=np.float32)
    perfect_candidates = timestamps + np.float32(0.04)
    great_candidates = timestamps + np.float32(0.19)
    perfect_floor = timestamps - np.float32(0.019)
    great_floor = timestamps - np.float32(0.094)
    lanes = _lanes_for(timestamps)

    oracle = _input_engine_rebuild_first_frontier(
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
    ) = _precompute_end_indices(
        timestamps=timestamps,
        perfect_candidate_timestamps=perfect_candidates,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=perfect_floor,
        great_floor_timestamps=great_floor,
        prefix_perfect_hit=prefix_perfect_hit,
        prefix_late_hit=prefix_late_hit,
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
            common["later_fill"],
            common["first_fill"],
            common["later_activation_forced"],
            common["first_activation_forced"],
            perfect_run_starts,
            perfect_run_ends,
            late_run_starts,
            late_run_ends,
            common["prefix_perfect_hit"],
            common["prefix_perfect_valid"],
            common["prefix_late_hit"],
            common["prefix_late_valid"],
            common["capped_perfect_edge_e"],
            common["capped_late_edge_e"],
            common["capped_eg_perfect_e"],
            common["capped_eg_late_e"],
            float(common["real_fever_time"]),
            int(common["real_time_idx"]),
            int(common["use_forced_great_timing_i"]),
            common["region_starts"],
            common["region_offsets"],
            common["region_activations"],
            common["region_great_ends"],
            common["region_is_greats"],
            empty_i32,
            empty_i32,
            common["region_perfect_valids"],
            empty_i32,
            empty_i32,
            common["perfect_floor_timestamps"],
            common["great_floor_timestamps"],
            perfect_successor,
            perfect_successor_stamps,
            late_successor,
            late_successor_stamps,
            1,
        )
        assert np.array_equal(actual_reachable, expected_reachable), case_idx
        assert int(actual_width) == int(expected_width), case_idx


def test_fg_response_reachability_prefix_reduction_matches_full_scan() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_activation_reachable_contiguous_run,
        _numba_region2_k_scan_stop,
        _numba_region2_offset_for_count,
    )

    def full_scan(
        *,
        activation_index: int,
        activation_hit_timestamp: float,
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
        h_a = np.float32(float(activation_hit_timestamp))
        lane_a = int(lanes[a])
        activation_is_great = int(activation_great_i) != 0 or (g0 <= a < g1)
        lo_a = great_floor_timestamps[a] if activation_is_great else perfect_floor_timestamps[a]
        unit_a = 0.5 if activation_is_great else 1.0
        forced_units = 0.0
        optional_units = 0.0
        for j in range(start, end):
            if j == a:
                continue
            is_great = g0 <= j < g1
            lo_j = great_floor_timestamps[j] if is_great else perfect_floor_timestamps[j]
            hi_j = great_candidate_timestamps[j] if is_great else perfect_candidate_timestamps[j]
            unit_j = 0.5 if is_great else 1.0
            same_lane = int(lanes[j]) == lane_a
            if same_lane and j > a and hi_j < h_a and lo_a <= hi_j:
                return False
            forced_any_lane = hi_j < h_a
            forced_same_lane_older = same_lane and j < a and lo_j <= h_a
            if forced_any_lane or forced_same_lane_older:
                forced_units += float(unit_j)
                if forced_units >= float(fever_fill_denom):
                    return False
                continue
            if lo_j <= h_a:
                if same_lane and j > a:
                    continue
                optional_units += float(unit_j)
        needed_before_activation = max(0.0, float(fever_fill_denom) - float(unit_a))
        return bool(forced_units < float(fever_fill_denom) and forced_units + optional_units >= needed_before_activation)

    rng = np.random.default_rng(20260706)
    gaps = rng.uniform(0.04, 0.31, size=48).astype(np.float64)
    timestamps = np.cumsum(gaps).astype(np.float32)
    timestamps -= timestamps[0]
    perfect_floor = np.maximum.accumulate((timestamps.astype(np.float64) - 0.019).astype(np.float32))
    great_floor = np.maximum.accumulate((timestamps.astype(np.float64) - 0.095).astype(np.float32))
    perfect_candidates = (timestamps.astype(np.float64) + rng.uniform(0.035, 0.045, size=48)).astype(np.float32)
    great_candidates = (timestamps.astype(np.float64) + rng.uniform(0.18, 0.19, size=48)).astype(np.float32)
    lanes = rng.integers(0, 4, size=48, dtype=np.int32)
    high_delta = float(
        np.float32(max(0.0, float(np.max(np.maximum(perfect_candidates, great_candidates) - timestamps))) + 1.0e-6)
    )

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
                high_delta,
                timestamps,
                perfect_floor,
                perfect_candidates,
                great_floor,
                great_candidates,
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


def test_fg_response_pattern_indexed_reducer_matches_sequential_semantics() -> None:
    from numba.typed import List

    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _NUMBA_SURFACE_TYPE,
        _numba_reduce,
        _numba_reduce_pattern_runs,
    )

    def dominates(left, right):
        lf0, lf1, lg0, lg1, lbf, lbg, lbfg = (int(value) for value in left)
        rf0, rf1, rg0, rg1, rbf, rbg, rbfg = (int(value) for value in right)
        return (
            (lf0 & lg0, lf1 & lg1) == (rf0 & rg0, rf1 & rg1)
            and lbf >= rbf
            and lbg - lbfg <= rbg - rbfg
            and lbfg <= rbfg
            and (rf0 & ~lf0) == 0
            and (rf1 & ~lf1) == 0
            and (lg0 & ~rg0) == 0
            and (lg1 & ~rg1) == 0
        )

    def sequential(rows):
        kept = []
        for candidate in rows:
            if any(dominates(row, candidate) for row in kept):
                continue
            kept = [row for row in kept if not dominates(candidate, row)]
            kept.append(candidate)
        return kept

    def assert_matches(rows):
        surfaces = List.empty_list(_NUMBA_SURFACE_TYPE)
        for row in rows:
            surfaces.append(tuple(np.uint64(value) for value in row))
        expected = sequential(rows)
        assert list(_numba_reduce(surfaces)) == expected
        assert list(_numba_reduce_pattern_runs(surfaces)) == expected

    pattern_a = (0b0011, 0, 0b0101, 0)
    pattern_b = (0b1011, 0, 0b0001, 0)
    directed_rows = []
    for pattern, fever_bias, normal_bias in (
        (pattern_a, 0, 3),
        (pattern_b, 5, 0),
        (pattern_a, 2, 1),
    ):
        for value in range(24):
            fever_great = value % 4
            directed_rows.append(
                (
                    *pattern,
                    fever_bias + value,
                    normal_bias + value + fever_great,
                    fever_great,
                )
            )
    directed_rows.extend((directed_rows[3], directed_rows[27], directed_rows[3]))
    assert_matches(directed_rows)

    rng = np.random.default_rng(116)
    for _case in range(24):
        rows = []
        patterns = []
        overlaps = [
            (int(rng.integers(0, 1 << 8)), int(rng.integers(0, 1 << 8)))
            for _ in range(3)
        ]
        for pattern_idx in range(12):
            overlap0, overlap1 = overlaps[int(pattern_idx) % len(overlaps)]
            fever0 = overlap0 | int(rng.integers(0, 1 << 16))
            fever1 = overlap1 | int(rng.integers(0, 1 << 16))
            great0 = overlap0 | (int(rng.integers(0, 1 << 16)) & ~fever0)
            great1 = overlap1 | (int(rng.integers(0, 1 << 16)) & ~fever1)
            patterns.append((fever0, fever1, great0, great1))
        for row_idx in range(96):
            pattern = patterns[int(rng.integers(0, len(patterns)))]
            body_fever_great = int(rng.integers(0, 20))
            normal_great = int(rng.integers(0, 20))
            row = (
                *pattern,
                int(rng.integers(0, 40)),
                normal_great + body_fever_great,
                body_fever_great,
            )
            rows.append(row)
            if row_idx % 17 == 0:
                rows.append(row)

        assert_matches(rows)


def test_fg_response_same_end_head_edge_prune_keeps_different_end_edges() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_append_head_edge_to_end_chains,
    )

    def _surface(values):
        return tuple(np.uint64(v) for v in values)

    def _chain(bucket_head, node_next, node_surface, end_e):
        out = []
        pos = int(bucket_head[end_e])
        while pos != -1:
            out.append(tuple(np.uint64(v) for v in node_surface[pos]))
            pos = int(node_next[pos])
        return out

    weak = _surface((0, 0, 0, 0, 0, 0, 0))
    stronger_same_end = _surface((1, 0, 0, 0, 0, 0, 0))

    node_surface = np.empty((1, 7), dtype=np.uint64)
    node_next = np.empty(1, dtype=np.int64)
    bucket_head = np.full(8, -1, dtype=np.int64)
    bucket_tail = np.full(8, -1, dtype=np.int64)
    pending_ends = np.empty(8, dtype=np.int64)
    cursor = 0
    pending = 0

    node_surface, node_next, cursor, pending, kept = _numba_append_head_edge_to_end_chains(
        node_surface, node_next, cursor, bucket_head, bucket_tail, pending_ends, pending, weak, 4
    )
    assert kept == 1

    node_surface, node_next, cursor, pending, kept = _numba_append_head_edge_to_end_chains(
        node_surface, node_next, cursor, bucket_head, bucket_tail, pending_ends, pending,
        stronger_same_end, 4
    )
    assert kept == 1
    assert _chain(bucket_head, node_next, node_surface, 4) == [stronger_same_end]
    assert list(pending_ends[:pending]) == [4]

    node_surface, node_next, cursor, pending, kept = _numba_append_head_edge_to_end_chains(
        node_surface, node_next, cursor, bucket_head, bucket_tail, pending_ends, pending, weak, 5
    )
    assert kept == 1
    assert _chain(bucket_head, node_next, node_surface, 4) == [stronger_same_end]
    assert _chain(bucket_head, node_next, node_surface, 5) == [weak]
    assert list(pending_ends[:pending]) == [4, 5]


def _ordered_rows_digest(value) -> str:
    return hashlib.blake2b(repr(value).encode("utf-8"), digest_size=16).hexdigest()


class _BodyReducerDifferentialHarness:
    def __init__(self, *, pair_mod: int = 33, normal_great_capacity: int = 65) -> None:
        from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
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


class _ChainedRegionBucketHarness:
    def __init__(self, *, end_capacity: int = 32) -> None:
        from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
            _numba_append_head_edge_to_end_chains,
        )

        self._append = _numba_append_head_edge_to_end_chains
        self.node_surface = np.empty((1, 7), dtype=np.uint64)
        self.node_next = np.empty((1,), dtype=np.int64)
        self.bucket_head = np.full((end_capacity,), -1, dtype=np.int64)
        self.bucket_tail = np.full((end_capacity,), -1, dtype=np.int64)
        self.pending_ends = np.empty((end_capacity,), dtype=np.int64)
        self.cursor = 0
        self.pending_count = 0

    def append(self, end_e: int, edge) -> bool:
        surface = tuple(np.uint64(value) for value in edge)
        (
            self.node_surface,
            self.node_next,
            self.cursor,
            self.pending_count,
            kept,
        ) = self._append(
            self.node_surface,
            self.node_next,
            int(self.cursor),
            self.bucket_head,
            self.bucket_tail,
            self.pending_ends,
            int(self.pending_count),
            surface,
            int(end_e),
        )
        return bool(kept)

    def pending(self) -> list[int]:
        return [int(value) for value in self.pending_ends[: int(self.pending_count)]]

    def bucket(self, end_e: int) -> list[tuple[int, ...]]:
        rows = []
        pos = int(self.bucket_head[int(end_e)])
        while pos != -1:
            rows.append(tuple(int(value) for value in self.node_surface[int(pos)]))
            pos = int(self.node_next[int(pos)])
        return rows

    def drain(self) -> list[tuple[int, tuple[int, ...]]]:
        rows = []
        for end_e in self.pending():
            rows.extend((int(end_e), row) for row in self.bucket(int(end_e)))
            self.bucket_head[int(end_e)] = -1
            self.bucket_tail[int(end_e)] = -1
        self.cursor = 0
        self.pending_count = 0
        return rows


def _body_only_surface(body_fever: int, normal_great: int, fever_great: int = 0) -> tuple[int, ...]:
    return (0, 0, 0, 0, body_fever, normal_great + fever_great, fever_great)


def _range_mask_words(start: int, end: int) -> tuple[int, int]:
    width = int(end) - int(start)
    mask = ((1 << width) - 1) << int(start) if width > 0 else 0
    return int(mask & ((1 << 64) - 1)), int(mask >> 64)


def _range_surface(
    *,
    fever: tuple[int, int],
    great: tuple[int, int],
    body_fever: int,
    normal_great: int,
    fever_great: int,
) -> tuple[int, ...]:
    fever_lo, fever_hi = _range_mask_words(*fever)
    great_lo, great_hi = _range_mask_words(*great)
    return (
        fever_lo,
        fever_hi,
        great_lo,
        great_hi,
        int(body_fever),
        int(normal_great) + int(fever_great),
        int(fever_great),
    )


def _assert_region_buckets_match_retired(actual, retired) -> None:
    assert actual.pending() == retired.pending_ends
    for end_e in retired.pending_ends:
        assert actual.bucket(end_e) == retired.bucket(end_e)


def test_fg_response_chained_region_duplicate_is_first_wins_without_cursor_growth() -> None:
    from tests.retired_fg_frontier_semantics import RetiredRegionEndBuckets

    edge = (0, 0xF0, 0, 0xC0, 12, 3, 2)
    actual = _ChainedRegionBucketHarness()
    retired = RetiredRegionEndBuckets()

    assert actual.append(4, edge) == retired.append(4, edge) is True
    cursor_after_first = int(actual.cursor)
    assert actual.append(4, edge) == retired.append(4, edge) is False

    assert cursor_after_first == actual.cursor == 1
    assert actual.bucket(4) == retired.bucket(4) == [edge]
    assert actual.node_surface.dtype == np.dtype(np.uint64)
    assert actual.node_next.dtype == np.dtype(np.int64)
    assert actual.bucket_head.dtype == np.dtype(np.int64)
    assert actual.bucket_tail.dtype == np.dtype(np.int64)
    assert actual.pending_ends.dtype == np.dtype(np.int64)


def test_fg_response_region_structural_dominance_low_high_word_contracts() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _numba_surface_structurally_dominates,
    )
    from tests.retired_fg_frontier_semantics import (
        RetiredRegionEndBuckets,
        retired_surface_structurally_dominates,
    )

    high_strong = (0, 0xF0, 0, 0xC0, 12, 3, 2)
    high_weak = (0, 0xC0, 0, 0x3C0, 10, 7, 4)
    cross_word_strong = _range_surface(
        fever=(60, 68), great=(62, 66), body_fever=12, normal_great=1, fever_great=2
    )
    cross_word_weak = _range_surface(
        fever=(62, 66), great=(62, 66), body_fever=10, normal_great=3, fever_great=4
    )
    great_subset_strong = _range_surface(
        fever=(60, 64), great=(66, 68), body_fever=12, normal_great=1, fever_great=2
    )
    great_subset_weak = _range_surface(
        fever=(60, 64), great=(65, 69), body_fever=10, normal_great=3, fever_great=4
    )
    same_masks = _range_surface(
        fever=(10, 15), great=(11, 13), body_fever=12, normal_great=1, fever_great=2
    )
    worse_normal = _range_surface(
        fever=(10, 15), great=(11, 13), body_fever=12, normal_great=3, fever_great=2
    )
    worse_fever_great = _range_surface(
        fever=(10, 15), great=(11, 13), body_fever=12, normal_great=1, fever_great=4
    )
    intersection_mismatch_right = (0, 0x30, 0, 0xF0, 10, 7, 4)
    fever_blocker_left = _range_surface(
        fever=(10, 15), great=(20, 22), body_fever=12, normal_great=1, fever_great=2
    )
    fever_blocker_right = _range_surface(
        fever=(9, 15), great=(20, 22), body_fever=10, normal_great=3, fever_great=4
    )
    great_blocker_left = _range_surface(
        fever=(10, 15), great=(20, 23), body_fever=12, normal_great=1, fever_great=2
    )
    great_blocker_right = _range_surface(
        fever=(10, 15), great=(20, 22), body_fever=10, normal_great=3, fever_great=4
    )
    cases = [
        ("high-half exact intersection", high_strong, high_weak, True),
        ("cross-word fever superset", cross_word_strong, cross_word_weak, True),
        ("low-high Great subset", great_subset_strong, great_subset_weak, True),
        ("normal-Great improvement", same_masks, worse_normal, True),
        ("fever-Great improvement", same_masks, worse_fever_great, True),
        ("intersection mismatch", high_strong, intersection_mismatch_right, False),
        ("fever non-superset", fever_blocker_left, fever_blocker_right, False),
        ("Great non-subset", great_blocker_left, great_blocker_right, False),
        ("worse normal-Great", worse_normal, same_masks, False),
        ("worse fever-Great", worse_fever_great, same_masks, False),
    ]
    for name, left, right, expected in cases:
        retired = retired_surface_structurally_dominates(left, right)
        production = bool(
            _numba_surface_structurally_dominates(
                tuple(np.uint64(value) for value in left),
                tuple(np.uint64(value) for value in right),
            )
        )
        assert retired is expected, name
        assert production is expected, name

    actual = _ChainedRegionBucketHarness()
    retired_buckets = RetiredRegionEndBuckets()
    assert actual.append(6, high_weak) == retired_buckets.append(6, high_weak) is True
    assert actual.append(6, high_weak) == retired_buckets.append(6, high_weak) is False
    assert actual.append(6, high_strong) == retired_buckets.append(6, high_strong) is True
    assert actual.append(6, high_weak) == retired_buckets.append(6, high_weak) is False
    assert actual.bucket(6) == retired_buckets.bucket(6) == [high_strong]


@pytest.mark.parametrize(
    ("replacement", "expected"),
    [
        (_body_only_surface(4, 0), [_body_only_surface(5, 3), _body_only_surface(7, 5), _body_only_surface(4, 0)]),
        (_body_only_surface(6, 2), [_body_only_surface(3, 1), _body_only_surface(7, 5), _body_only_surface(6, 2)]),
        (_body_only_surface(8, 4), [_body_only_surface(3, 1), _body_only_surface(5, 3), _body_only_surface(8, 4)]),
    ],
    ids=("head-unlink", "middle-unlink", "tail-unlink"),
)
def test_fg_response_chained_region_bucket_matches_retired_unlink_positions(
    replacement, expected
) -> None:
    from tests.retired_fg_frontier_semantics import RetiredRegionEndBuckets

    initial = [
        _body_only_surface(3, 1),
        _body_only_surface(5, 3),
        _body_only_surface(7, 5),
    ]
    actual = _ChainedRegionBucketHarness()
    retired = RetiredRegionEndBuckets()
    for edge in [*initial, replacement]:
        assert actual.append(4, edge) == retired.append(4, edge)
        _assert_region_buckets_match_retired(actual, retired)
    assert actual.bucket(4) == expected


def test_fg_response_chained_region_bucket_matches_retired_rejection_and_multiple_removal() -> None:
    from tests.retired_fg_frontier_semantics import RetiredRegionEndBuckets

    actual = _ChainedRegionBucketHarness()
    retired = RetiredRegionEndBuckets()
    mutually_nondominating = [
        _body_only_surface(3, 1),
        _body_only_surface(5, 3),
        _body_only_surface(7, 5),
    ]
    for edge in mutually_nondominating:
        assert actual.append(9, edge) == retired.append(9, edge) is True
    rejected = _body_only_surface(2, 6)
    assert actual.append(9, rejected) == retired.append(9, rejected) is False
    assert actual.bucket(9) == mutually_nondominating
    dominates_all = _body_only_surface(8, 0)
    assert actual.append(9, dominates_all) == retired.append(9, dominates_all) is True
    _assert_region_buckets_match_retired(actual, retired)
    assert actual.bucket(9) == [dominates_all]


def test_fg_response_chained_region_bucket_preserves_pending_drain_growth_and_scratch_reuse() -> None:
    from tests.retired_fg_frontier_semantics import RetiredRegionEndBuckets

    actual = _ChainedRegionBucketHarness()
    retired = RetiredRegionEndBuckets()
    first_batch = [
        (4, _body_only_surface(3, 1)),
        (2, _body_only_surface(4, 2)),
        (4, _body_only_surface(5, 3)),
        (7, _body_only_surface(6, 4)),
        (2, _body_only_surface(7, 5)),
    ]
    for end_e, edge in first_batch:
        assert actual.append(end_e, edge) == retired.append(end_e, edge)
        _assert_region_buckets_match_retired(actual, retired)
    assert actual.pending() == [4, 2, 7]
    assert actual.node_surface.shape == (8, 7)
    assert actual.node_next.shape == (8,)
    assert actual.drain() == retired.drain()
    assert np.all(actual.bucket_head == -1)
    assert np.all(actual.bucket_tail == -1)

    second_batch = [
        (7, _body_only_surface(10, 1)),
        (1, _body_only_surface(11, 2)),
        (7, _body_only_surface(12, 3)),
    ]
    for end_e, edge in second_batch:
        assert actual.append(end_e, edge) == retired.append(end_e, edge)
        _assert_region_buckets_match_retired(actual, retired)
    assert actual.pending() == [7, 1]
    assert actual.drain() == retired.drain()
    assert actual.node_surface.shape == (8, 7)
    assert actual.node_next.shape == (8,)


def test_fg_response_chained_region_bucket_matches_retired_structured_streams() -> None:
    from tests.retired_fg_frontier_semantics import RetiredRegionEndBuckets

    rng = np.random.default_rng(116_20260710)
    actual = _ChainedRegionBucketHarness()
    ordered_drains = []
    accepted_flags = []
    insertion_count = 0
    accepted_count = 0
    rejected_count = 0
    removed_count = 0
    for batch_idx in range(32):
        retired = RetiredRegionEndBuckets()
        for endpoint_idx, end_e in enumerate((2, 5, 8)):
            high_half = (int(batch_idx) + int(endpoint_idx)) % 2 != 0
            overlap_start = (72 if high_half else 8) + int(rng.integers(0, 16))
            overlap_width = int(rng.integers(2, 5))
            fever_extra = int(rng.integers(1, 4))
            great_extra = int(rng.integers(1, 4))
            weak_body_fever = 24 + int(rng.integers(0, 8))
            weak = _range_surface(
                fever=(overlap_start, overlap_start + overlap_width),
                great=(overlap_start, overlap_start + overlap_width + great_extra),
                body_fever=weak_body_fever,
                normal_great=6,
                fever_great=4,
            )
            strong = _range_surface(
                fever=(overlap_start - fever_extra, overlap_start + overlap_width),
                great=(overlap_start, overlap_start + overlap_width),
                body_fever=weak_body_fever + 2,
                normal_great=4,
                fever_great=3,
            )
            tradeoff = _range_surface(
                fever=(overlap_start - fever_extra, overlap_start + overlap_width),
                great=(overlap_start, overlap_start + overlap_width),
                body_fever=weak_body_fever + 5,
                normal_great=7,
                fever_great=3,
            )
            scripted = (
                (weak, True, 0),
                (weak, False, 0),
                (strong, True, 1),
                (weak, False, 0),
                (tradeoff, True, 0),
            )
            for edge, expected_kept, expected_removed in scripted:
                assert 0 <= int(edge[6]) <= int(edge[4])
                assert int(edge[5]) - int(edge[6]) >= 0
                before = len(retired.bucket(end_e))
                actual_before = len(actual.bucket(end_e))
                actual_kept = actual.append(end_e, edge)
                retired_kept = retired.append(end_e, edge)
                after = len(retired.bucket(end_e))
                actual_after = len(actual.bucket(end_e))
                removed = int(before) + int(retired_kept) - int(after)
                actual_removed = int(actual_before) + int(actual_kept) - int(actual_after)
                assert actual_kept == retired_kept == expected_kept, (
                    batch_idx,
                    endpoint_idx,
                    insertion_count,
                )
                assert actual_removed == removed == expected_removed
                accepted_flags.append(actual_kept)
                accepted_count += int(actual_kept)
                rejected_count += int(not actual_kept)
                removed_count += int(removed)
                insertion_count += 1
                _assert_region_buckets_match_retired(actual, retired)
        assert actual.pending() == [2, 5, 8]
        assert actual.node_surface.shape == (16, 7)
        assert actual.node_next.shape == (16,)
        actual_drain = actual.drain()
        retired_drain = retired.drain()
        assert actual_drain == retired_drain, batch_idx
        ordered_drains.append(actual_drain)

    assert insertion_count == 480
    assert accepted_count == 288
    assert rejected_count == 192
    assert removed_count == 96
    assert _ordered_rows_digest(
        (accepted_flags, removed_count, ordered_drains)
    ) == "250a9644c3ff65c07db4b60c80af5c82"


def test_fg_response_region_emitter_drains_and_reuses_actual_scratch_in_pending_order() -> None:
    from numba import types
    from numba.typed import Dict, List

    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _NUMBA_HEAD_SCORES_TYPE,
        _NUMBA_HEAD_SCORE_MATRIX_TYPE,
        _NUMBA_SURFACE_TYPE,
        _numba_emit_region2_head_edges,
    )
    from tests.retired_fg_frontier_semantics import RetiredRegionEndBuckets

    n = 8
    body_values = np.zeros((1, 3), dtype=np.uint64)
    body_starts = np.zeros((n + 1,), dtype=np.int32)
    body_counts = np.zeros((n + 1,), dtype=np.int32)
    head_pool = np.zeros((n, 7), dtype=np.uint64)
    head_state_start = np.arange(n, dtype=np.int64)
    head_state_count = np.ones((n,), dtype=np.int64)
    node_surface = np.empty((1, 7), dtype=np.uint64)
    node_next = np.empty((1,), dtype=np.int64)
    bucket_head = np.full((n + 2,), -1, dtype=np.int64)
    bucket_tail = np.full((n + 2,), -1, dtype=np.int64)
    pending_ends = np.empty((n + 2,), dtype=np.int64)
    starts = np.full((n + 2,), 2, dtype=np.int64)
    starts[0] = 0
    perfect_end_by_hit = np.asarray([4, 6], dtype=np.int32)
    great_end_by_hit = np.asarray([4, 6], dtype=np.int32)
    table_columns = (
        np.asarray([1, 2], dtype=np.int32),
        np.asarray([2, 3], dtype=np.int32),
        np.asarray([2, 3], dtype=np.int32),
        np.asarray([0, 0], dtype=np.int32),
        np.asarray([0, 1], dtype=np.int32),
        np.asarray([0, 1], dtype=np.int32),
        np.asarray([1, 1], dtype=np.int32),
    )
    row12 = (12, 0, 2, 0, 0, 0, 0)
    row56 = (56, 0, 4, 0, 0, 0, 0)

    def _retired_drain(candidates):
        retired = RetiredRegionEndBuckets()
        for end_e, row in candidates:
            assert retired.append(end_e, row)
        return [row for _end_e, row in retired.drain()]

    def _emit(columns, shared_surface, shared_next):
        generated = List.empty_list(_NUMBA_SURFACE_TYPE)
        generated_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
        generated_seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
        score_matrix_holder = List.empty_list(_NUMBA_HEAD_SCORE_MATRIX_TYPE)
        score_matrix_count = np.zeros(1, dtype=np.int64)
        return _numba_emit_region2_head_edges(
            generated,
            generated_scores,
            generated_seen,
            score_matrix_holder,
            score_matrix_count,
            shared_surface,
            shared_next,
            bucket_head,
            bucket_tail,
            pending_ends,
            n,
            0,
            starts,
            columns[0],
            columns[1],
            columns[2],
            columns[3],
            columns[4],
            columns[5],
            columns[6],
            perfect_end_by_hit,
            great_end_by_hit,
            1,
            body_values,
            body_starts,
            body_counts,
            head_pool,
            head_state_start,
            head_state_count,
            n,
            0,
            n,
            999,
            0,
        )

    first = _emit(table_columns, node_surface, node_next)
    first_generated, _first_scores, first_added, first_bounded, node_surface, node_next = first
    first_rows = [tuple(int(value) for value in row) for row in first_generated]
    assert first_rows == _retired_drain(((4, row12), (6, row56))) == [row12, row56]
    assert first_added == 2
    assert first_bounded == 0
    assert node_surface.shape == (2, 7)
    assert node_next.shape == (2,)
    assert np.all(bucket_head == -1)
    assert np.all(bucket_tail == -1)

    reversed_columns = tuple(column[::-1].copy() for column in table_columns)
    second = _emit(reversed_columns, node_surface, node_next)
    second_generated, _second_scores, second_added, second_bounded, node_surface, node_next = second
    second_rows = [tuple(int(value) for value in row) for row in second_generated]
    assert second_rows == _retired_drain(((6, row56), (4, row12))) == [row56, row12]
    assert second_added == 2
    assert second_bounded == 0
    assert node_surface.shape == (2, 7)
    assert node_next.shape == (2,)
    assert node_surface.dtype == np.dtype(np.uint64)
    assert node_next.dtype == np.dtype(np.int64)
    assert bucket_head.dtype == np.dtype(np.int64)
    assert bucket_tail.dtype == np.dtype(np.int64)
    assert pending_ends.dtype == np.dtype(np.int64)
    assert np.all(bucket_head == -1)
    assert np.all(bucket_tail == -1)


def test_fg_response_region_prereduce_preserves_retired_promotion_schedule() -> None:
    """Same-mask thinning may feed the first exact reduce, never the bounded suffix.

    The bounded cone inserter is deliberately order-sensitive: a structurally dominated row
    can still evict a harmless extra before its own later dominator arrives.  A whole-stream
    pre-reduce therefore changes retained witnesses.  This production-shaped stream crosses
    the 4,096-row promotion threshold in its first edge batch and pins the retired per-edge
    schedule exactly; the second batch must still enter the bounded inserter row by row.
    """
    from numba import types
    from numba.typed import Dict, List

    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _NUMBA_HEAD_SCORES_TYPE,
        _NUMBA_HEAD_SCORE_MATRIX_TYPE,
        _NUMBA_SURFACE_TYPE,
        _numba_append_head_generated_candidate,
        _numba_emit_region2_head_edges,
        _numba_pack_edge,
    )

    n = 128
    first_count = 4_200
    second_count = 800
    rng = np.random.default_rng(0)
    body_fever = rng.integers(0, 80, first_count + second_count, dtype=np.uint64)
    normal_great = rng.integers(0, 80, first_count + second_count, dtype=np.uint64)
    fever_great = rng.integers(0, 40, first_count + second_count, dtype=np.uint64)
    body_values = np.stack(
        (body_fever, normal_great + fever_great, fever_great), axis=1
    )
    body_starts = np.zeros((n + 1,), dtype=np.int32)
    body_counts = np.zeros((n + 1,), dtype=np.int32)
    body_starts[101] = 0
    body_counts[101] = first_count
    body_starts[102] = first_count
    body_counts[102] = second_count
    head_pool = np.zeros((1, 7), dtype=np.uint64)
    head_state_start = np.zeros((n,), dtype=np.int64)
    head_state_count = np.zeros((n,), dtype=np.int64)
    node_surface = np.empty((1, 7), dtype=np.uint64)
    node_next = np.empty((1,), dtype=np.int64)
    bucket_head = np.full((n + 2,), -1, dtype=np.int64)
    bucket_tail = np.full((n + 2,), -1, dtype=np.int64)
    pending_ends = np.empty((n + 2,), dtype=np.int64)
    starts = np.full((n + 2,), 2, dtype=np.int64)
    starts[0] = 0
    perfect_end_by_hit = np.asarray([101, 102], dtype=np.int32)
    great_end_by_hit = np.asarray([101, 102], dtype=np.int32)
    table_columns = (
        np.asarray([1, 1], dtype=np.int32),
        np.asarray([0, 0], dtype=np.int32),
        np.asarray([1, 1], dtype=np.int32),
        np.asarray([0, 0], dtype=np.int32),
        np.asarray([0, 1], dtype=np.int32),
        np.asarray([0, 1], dtype=np.int32),
        np.asarray([1, 1], dtype=np.int32),
    )

    expected = List.empty_list(_NUMBA_SURFACE_TYPE)
    expected_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    expected_seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
    expected_score_matrix_holder = List.empty_list(_NUMBA_HEAD_SCORE_MATRIX_TYPE)
    expected_score_matrix_count = np.zeros(1, dtype=np.int64)
    bounded = 0
    for end_e in (101, 102):
        edge = _numba_pack_edge(n, 0, end_e, 1, 1, -1)
        expected, expected_scores, added, bounded = (
            _numba_append_head_generated_candidate(
                expected,
                expected_scores,
                expected_seen,
                expected_score_matrix_holder,
                expected_score_matrix_count,
                edge,
                end_e,
                body_values,
                body_starts,
                body_counts,
                head_pool,
                head_state_start,
                head_state_count,
                100,
                0,
                100,
                0,
                bounded,
            )
        )
        assert added == body_counts[end_e]
    assert bounded == 1

    actual = List.empty_list(_NUMBA_SURFACE_TYPE)
    actual_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    actual_seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
    actual_score_matrix_holder = List.empty_list(_NUMBA_HEAD_SCORE_MATRIX_TYPE)
    actual_score_matrix_count = np.zeros(1, dtype=np.int64)
    actual, actual_scores, added, actual_bounded, _node_surface, _node_next = (
        _numba_emit_region2_head_edges(
            actual,
            actual_scores,
            actual_seen,
            actual_score_matrix_holder,
            actual_score_matrix_count,
            node_surface,
            node_next,
            bucket_head,
            bucket_tail,
            pending_ends,
            n,
            0,
            starts,
            table_columns[0],
            table_columns[1],
            table_columns[2],
            table_columns[3],
            table_columns[4],
            table_columns[5],
            table_columns[6],
            perfect_end_by_hit,
            great_end_by_hit,
            1,
            body_values,
            body_starts,
            body_counts,
            head_pool,
            head_state_start,
            head_state_count,
            100,
            0,
            100,
            0,
            0,
        )
    )

    assert added == first_count + second_count
    assert actual_bounded == bounded == 1
    assert list(actual) == list(expected)
    assert len(actual_scores) == len(expected_scores) == len(actual)
    for actual_row, expected_row in zip(actual_scores, expected_scores, strict=True):
        np.testing.assert_array_equal(actual_row, expected_row)
    assert np.all(bucket_head == -1)
    assert np.all(bucket_tail == -1)


def test_fg_response_bounded_exact_duplicate_skip_matches_every_retired_prefix() -> None:
    """A duplicate remains inert after its first copy is rejected or repeatedly evicted."""
    from numba import types
    from numba.typed import Dict, List

    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _NUMBA_HEAD_SCORES_TYPE,
        _NUMBA_HEAD_SCORE_MATRIX_TYPE,
        _NUMBA_SURFACE_TYPE,
        _numba_head_basis_corner_scores_row,
        _numba_head_envelope_insert_blocked_with_scores,
        _numba_head_envelope_insert_with_scores,
        _numba_head_surface_basis,
        _numba_mark_head_surface_first_seen,
    )

    weak = (0, 0, 0, 0, 25, 50, 25)
    strong = (0, 0, 0, 0, 60, 50, 25)
    strongest = (0, 0, 0, 0, 100, 50, 25)
    stream = (
        weak,
        weak,       # duplicate while the original is retained
        strong,     # evicts weak
        weak,       # duplicate after its original was evicted
        strong,
        strongest,  # evicts strong
        weak,       # duplicate after a two-link dominator chain
        strong,
        strongest,
    )

    retired = List.empty_list(_NUMBA_SURFACE_TYPE)
    retired_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    actual = List.empty_list(_NUMBA_SURFACE_TYPE)
    actual_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
    score_matrix_holder = List.empty_list(_NUMBA_HEAD_SCORE_MATRIX_TYPE)
    score_matrix_count = np.zeros(1, dtype=np.int64)
    eligible = np.empty(8, dtype=np.uint8)
    for prefix_len, candidate in enumerate(stream, start=1):
        row = tuple(np.uint64(value) for value in candidate)
        scores = np.empty(16, dtype=np.float64)
        _numba_head_basis_corner_scores_row(
            _numba_head_surface_basis(row, 0, 100), scores
        )
        retired, retired_scores = _numba_head_envelope_insert_with_scores(
            retired, retired_scores, row, scores
        )
        if _numba_mark_head_surface_first_seen(seen, row):
            actual, actual_scores = _numba_head_envelope_insert_blocked_with_scores(
                actual,
                actual_scores,
                score_matrix_holder,
                score_matrix_count,
                row,
                scores,
                eligible,
            )

        assert list(actual) == list(retired), prefix_len
        assert len(actual_scores) == len(retired_scores)
        for actual_row, retired_row in zip(actual_scores, retired_scores, strict=True):
            np.testing.assert_array_equal(actual_row, retired_row)

    assert list(actual) == [tuple(np.uint64(value) for value in strongest)]
    assert len(seen) == 3


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
            perfect_floor_timestamps=song_inputs.timestamps,
            great_floor_timestamps=song_inputs.timestamps,
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
    great_candidates = timestamps + np.asarray([0.0, 0.05, 0.0, 0.03, 0.0, 0.04, 0.0], dtype=np.float32)
    raw_fever_fill = 2.25
    non_fever_base = 7
    real_fever_time = 0.55
    lanes = _lanes_for(timestamps)
    slim = response_build_gpu_batch.build_force_greats_response_first_frontiers_gpu_batch(
        timestamps=timestamps,
        great_candidate_timestamps=great_candidates,
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
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
        perfect_floor_timestamps=timestamps,
        great_floor_timestamps=timestamps,
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
        perfect_floor_timestamps=timestamps,
        perfect_candidate_timestamps=timestamps,
        great_floor_timestamps=timestamps,
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
            great_candidate_timestamps=great_candidates,
            perfect_floor_timestamps=timestamps,
            great_floor_timestamps=timestamps,
            lanes=lanes,
            raw_fever_fill=raw_fever_fill,
        ):
            if (
                int(option["next_state"]) == int(row["next_state"])
                and int(option["activation_index"]) == int(row["activation_index"])
                and str(option["activation_judgment"]) == str(row["activation_judgment"])
                and int(option.get("forced_run_start_index", option["forced_start_index"]))
                == int(row.get("forced_run_start_index", row["forced_start_index"]))
                and int(option.get("forced_run_count", option["forced_prefix_count"]))
                == int(row.get("forced_run_count", row["forced_prefix_count"]))
            ):
                edge_match = (int(option["next_state"]), option["surface"])
                break
        assert edge_match is not None
        state, edge = edge_match
        surface = _combine_surface(surface, edge)
        first = False

    assert surface == target
