from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem.force_greats.fill_crossing import (
    activation_schedule_witnesses_weighted_lane_aware,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
    _numba_activation_reachable_contiguous_run,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_builder import (
    _activation_reachable,
    _build_activation_reachability_context,
)


def _retired_boolean_prefix_reachable(
    activation_index: int,
    activation_hit_timestamp: float,
    candidate_high_delta_max: float,
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
    """Allocation-heavy exact lane-prefix owner retained only as a differential oracle."""
    a = int(activation_index)
    start = int(section_start)
    end = int(section_end)
    if start < 0 or end < start or not (start <= a < end):
        return False
    denom = float(fever_fill_denom)
    if denom <= 0.0:
        raise ValueError("fever_fill_denom must be > 0")
    total = int(perfect_candidate_timestamps.shape[0])
    if end > total:
        return False

    del candidate_high_delta_max, timestamps
    g0 = max(start, int(great_start), 0)
    g1 = max(g0, min(end, int(great_start) + int(great_count)))
    is_great = np.zeros(total, dtype=np.bool_)
    is_great[g0:g1] = True
    if int(activation_great_i) != 0:
        is_great[a] = True
    low = np.where(is_great, great_floor_timestamps, perfect_floor_timestamps)
    high = np.where(is_great, great_candidate_timestamps, perfect_candidate_timestamps)
    fill_units = np.where(is_great, 0.5, 1.0).astype(np.float32)
    preactivation_count = int(a) - int(start)
    preactivation_great_count = int(np.count_nonzero(is_great[start:a]))
    return bool(
        activation_schedule_witnesses_weighted_lane_aware(
            activation_index=a,
            activation_hit_timestamp=float(activation_hit_timestamp),
            low_hit_timestamps=low,
            high_hit_timestamps=high,
            lanes=lanes,
            fill_units=fill_units,
            fever_fill_denom=denom,
            section_start=start,
            section_end=end,
            required_preactivation_fill_half_units=(
                2 * int(preactivation_count) - int(preactivation_great_count)
            ),
            required_preactivation_event_count=int(preactivation_count),
        )
    )


def _dense_inputs(n: int = 96) -> tuple[np.ndarray, ...]:
    timestamps = np.arange(n, dtype=np.float32) * np.float32(0.0001)
    perfect_floor = (timestamps.astype(np.float64) - 0.080).astype(np.float32)
    great_floor = (timestamps.astype(np.float64) - 0.190).astype(np.float32)
    perfect_candidates = (timestamps.astype(np.float64) + 0.080).astype(np.float32)
    great_candidates = (timestamps.astype(np.float64) + 0.190).astype(np.float32)
    lane_values = np.asarray(
        [np.iinfo(np.int32).min + 7, -1_000_003, 17, 999_999_937, np.iinfo(np.int32).max - 11],
        dtype=np.int32,
    )
    lanes = np.resize(lane_values, n).astype(np.int32, copy=False)
    lanes[-1] = np.int32(123_456_789)
    return timestamps, perfect_floor, perfect_candidates, great_floor, great_candidates, lanes


def _exact_surface_query(*args) -> bool:
    """Call the canonical query from the retired oracle's wider historical signature."""
    return bool(
        _numba_activation_reachable_contiguous_run(
            args[0],
            args[1],
            args[3],
            args[4],
            args[5],
            args[6],
            args[7],
            args[8],
            args[9],
            args[10],
            args[11],
            args[12],
            args[13],
            args[14],
        )
    )


@pytest.mark.parametrize("denom", [30.5, 31.0, 31.5, 32.0, 32.5, 63.5, 64.0])
def test_exact_surface_query_matches_schedule_oracle_across_fill_boundaries(denom: float) -> None:
    timestamps, perfect_floor, perfect_candidates, great_floor, great_candidates, lanes = _dense_inputs()
    args = (
        95,
        float(timestamps[95]),
        0.200001,
        timestamps,
        perfect_floor,
        perfect_candidates,
        great_floor,
        great_candidates,
        lanes,
        float(denom),
        0,
        96,
        8,
        55,
        0,
    )
    assert _exact_surface_query(*args) is _retired_boolean_prefix_reachable(*args)


def test_exact_surface_query_preserves_legal_body_cross_lane_prefix_swap() -> None:
    n = 104
    timestamps = np.zeros(n, dtype=np.float32)
    timestamps[100:] = np.asarray([0.0, 0.1, 0.2, 0.3], dtype=np.float32)
    perfect_floor = np.zeros(n, dtype=np.float32)
    perfect_candidates = np.ones(n, dtype=np.float32)
    perfect_candidates[103] = np.float32(0.4)
    great_floor = np.zeros(n, dtype=np.float32)
    great_candidates = perfect_candidates.copy()
    lanes = np.arange(n, dtype=np.int32)
    lanes[100:] = np.asarray([0, 1, 2, 1], dtype=np.int32)
    args = (
        102,
        0.5,
        1.0,
        timestamps,
        perfect_floor,
        perfect_candidates,
        great_floor,
        great_candidates,
        lanes,
        2.5,
        100,
        104,
        104,
        0,
        0,
    )

    # Body note 103 must occur before activation, but its lane requires note 101 first. Delaying
    # optional note 100 preserves the exact two-Perfect body signature via order (101, 103).
    assert _retired_boolean_prefix_reachable(*args) is True
    assert _exact_surface_query(*args) is True

    forced_note_zero_high = perfect_candidates.copy()
    forced_note_zero_high[100] = np.float32(0.4)
    impossible_args = (*args[:5], forced_note_zero_high, *args[6:])
    assert _retired_boolean_prefix_reachable(*impossible_args) is False
    assert _exact_surface_query(*impossible_args) is False


def test_exact_surface_query_matches_randomized_schedule_oracle() -> None:
    timestamps, perfect_floor, perfect_candidates, great_floor, great_candidates, lanes = _dense_inputs()
    denom = 37.25
    rng = np.random.default_rng(20260712)
    for _case_idx in range(240):
        start = int(rng.integers(0, 72))
        end = int(rng.integers(start + 1, 97))
        activation = int(rng.integers(start, end))
        great_start = int(rng.integers(max(0, start - 3), end))
        great_count = int(rng.integers(0, min(70, 96 - great_start) + 1))
        activation_great = int(rng.integers(0, 2))
        hit_kind = int(rng.integers(0, 3))
        if hit_kind == 0:
            hit = timestamps[activation]
        elif hit_kind == 1:
            hit = perfect_candidates[activation]
        else:
            hit = great_candidates[activation]
        args = (
            activation,
            float(hit),
            0.200001,
            timestamps,
            perfect_floor,
            perfect_candidates,
            great_floor,
            great_candidates,
            lanes,
            denom,
            start,
            end,
            great_start,
            great_count,
            activation_great,
        )
        actual = _exact_surface_query(*args)
        assert bool(actual) is _retired_boolean_prefix_reachable(*args), _case_idx


def test_exact_surface_query_matches_randomized_cross_lane_swaps() -> None:
    rng = np.random.default_rng(149)
    n = 18
    timestamps = np.zeros(n, dtype=np.float32)
    perfect_floor = np.zeros(n, dtype=np.float32)
    great_floor = np.zeros(n, dtype=np.float32)
    lanes = rng.integers(-2, 3, size=n, dtype=np.int32)
    for case_idx in range(240):
        activation = int(rng.integers(1, n - 1))
        great_start = int(rng.integers(0, n))
        great_count = int(rng.integers(0, n - great_start + 1))
        activation_great = int(rng.integers(0, 2))
        perfect_candidates = rng.choice(
            np.asarray([0.4, 1.0], dtype=np.float32), size=n
        ).astype(np.float32)
        great_candidates = rng.choice(
            np.asarray([0.4, 1.0], dtype=np.float32), size=n
        ).astype(np.float32)
        perfect_candidates[activation] = np.float32(1.0)
        great_candidates[activation] = np.float32(1.0)
        activation_is_great = bool(
            activation_great
            or int(great_start) <= int(activation) < int(great_start) + int(great_count)
        )
        great_before = max(
            0,
            min(int(activation), int(great_start) + int(great_count))
            - max(0, int(great_start)),
        )
        fill_before = float(activation) - 0.5 * float(great_before)
        denom = fill_before + (0.25 if activation_is_great else 0.5)
        args = (
            activation,
            0.5,
            1.0,
            timestamps,
            perfect_floor,
            perfect_candidates,
            great_floor,
            great_candidates,
            lanes,
            denom,
            0,
            n,
            great_start,
            great_count,
            activation_great,
        )
        assert _exact_surface_query(*args) is _retired_boolean_prefix_reachable(*args), case_idx


def test_trace_reachability_context_uses_exact_surface_query() -> None:
    timestamps, perfect_floor, perfect_candidates, great_floor, great_candidates, lanes = _dense_inputs()
    denom = 37.25
    context = _build_activation_reachability_context(
        timestamps=timestamps,
        perfect_floor_timestamps=perfect_floor,
        perfect_candidate_timestamps=perfect_candidates,
        great_floor_timestamps=great_floor,
        great_candidate_timestamps=great_candidates,
        lanes=lanes,
        fever_fill_denom=denom,
    )
    rng = np.random.default_rng(20260713)
    for case_idx in range(240):
        start = int(rng.integers(0, 72))
        end = int(timestamps.shape[0])
        activation = int(rng.integers(start, end))
        great_start = int(rng.integers(start, end))
        great_count = int(rng.integers(0, min(70, 96 - great_start) + 1))
        activation_great = bool(int(rng.integers(0, 2)))
        hit = (timestamps, perfect_candidates, great_candidates)[int(rng.integers(0, 3))][activation]
        args = (
            activation,
            float(hit),
            0.200001,
            timestamps,
            perfect_floor,
            perfect_candidates,
            great_floor,
            great_candidates,
            lanes,
            denom,
            start,
            end,
            great_start,
            great_count,
            int(activation_great),
        )
        actual = _activation_reachable(
            context=context,
            a=activation,
            hit=float(hit),
            section_start=start,
            great_start=great_start,
            great_count=great_count,
            activation_great=activation_great,
            n=end,
        )
        assert actual is _retired_boolean_prefix_reachable(*args), case_idx
    with pytest.raises(ValueError, match="invalid Great run"):
        _activation_reachable(
            context=context,
            a=40,
            hit=float(timestamps[40]),
            section_start=12,
            great_start=11,
            great_count=3,
            activation_great=False,
            n=int(timestamps.shape[0]),
        )


@pytest.mark.parametrize("denom", [float("inf"), float("nan")])
def test_exact_surface_query_rejects_nonfinite_denominator(denom: float) -> None:
    timestamps, perfect_floor, perfect_candidates, great_floor, great_candidates, lanes = _dense_inputs()
    with pytest.raises(ValueError, match="finite"):
        _numba_activation_reachable_contiguous_run(
            40,
            float(timestamps[40]),
            timestamps,
            perfect_floor,
            perfect_candidates,
            great_floor,
            great_candidates,
            lanes,
            denom,
            0,
            96,
            5,
            30,
            0,
        )


def _retired_boolean_region_core_for_offset(
    rb,
    *,
    n: int,
    section_start: int,
    offset: int,
    k: int,
    raw_fill: float,
    timestamps: np.ndarray,
    candidate_high_delta_max: float,
    perfect_floor: np.ndarray,
    perfect_candidates: np.ndarray,
    great_floor: np.ndarray,
    great_candidates: np.ndarray,
    lanes: np.ndarray,
) -> tuple[int, int, int, int, int, int, int]:
    """Test-only retired Boolean owner for complete ordered region-table differentials."""
    run_start = int(section_start) + int(offset)
    activation, is_great = rb._numba_fill_crossing_run(
        int(section_start), int(run_start), int(k), float(raw_fill), int(n)
    )
    if int(activation) < 0:
        return -1, -1, 0, 0, -1, -1, 0

    if int(is_great) != 0:
        hit_hi = great_candidates[int(activation)]
        max_great_end = int(activation) + 1
        while (
            int(max_great_end) < int(n)
            and perfect_candidates[int(max_great_end)] < hit_hi
        ):
            max_great_end += 1
        great_end = -1
        activation_hit_token = -1
        for candidate_end in range(int(activation) + 1, int(max_great_end) + 1):
            hit, valid, hit_token = rb._numba_late_great_activation_hit_for_run(
                int(activation),
                timestamps,
                perfect_candidates,
                great_candidates,
                int(run_start),
                int(candidate_end) - int(run_start),
                int(n),
            )
            if int(valid) != 0 and _retired_boolean_prefix_reachable(
                int(activation),
                float(hit),
                float(candidate_high_delta_max),
                timestamps,
                perfect_floor,
                perfect_candidates,
                great_floor,
                great_candidates,
                lanes,
                float(raw_fill),
                int(section_start),
                int(n),
                int(run_start),
                int(candidate_end) - int(run_start),
                1,
            ):
                great_end = int(candidate_end)
                activation_hit_token = int(hit_token)
                break
        if int(great_end) < 0:
            return -1, -1, 0, 0, -1, -1, 0
        _perfect_hit, perfect_valid, perfect_hit_token = (
            rb._numba_perfect_activation_hit_for_run(
                int(activation),
                timestamps,
                perfect_candidates,
                great_candidates,
                int(run_start),
                int(great_end) - int(run_start),
                int(n),
            )
        )
        return (
            int(activation),
            int(great_end),
            1,
            int(perfect_valid),
            int(activation_hit_token),
            int(perfect_hit_token),
            1,
        )

    great_end = min(int(n), int(run_start) + int(k))
    if int(great_end) <= int(run_start):
        return -1, -1, 0, 0, -1, -1, 0
    perfect_hit, perfect_valid, perfect_hit_token = rb._numba_perfect_activation_hit_for_run(
        int(activation),
        timestamps,
        perfect_candidates,
        great_candidates,
        int(run_start),
        int(great_end) - int(run_start),
        int(n),
    )
    if int(perfect_valid) == 0 or not _retired_boolean_prefix_reachable(
        int(activation),
        float(perfect_hit),
        float(candidate_high_delta_max),
        timestamps,
        perfect_floor,
        perfect_candidates,
        great_floor,
        great_candidates,
        lanes,
        float(raw_fill),
        int(section_start),
        int(n),
        int(run_start),
        int(great_end) - int(run_start),
        0,
    ):
        return -1, -1, 0, 0, -1, -1, 0
    return (
        int(activation),
        int(great_end),
        0,
        1,
        -1,
        int(perfect_hit_token),
        1,
    )


def test_region_core_table_preserves_exact_schedule_stream() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import (
        response_build_gpu_numba as rb,
        response_build_gpu_precompute,
    )

    n = 48
    timestamps = np.arange(n, dtype=np.float32) * np.float32(0.071)
    timestamps[12:15] = timestamps[12]
    timestamps[31:33] = timestamps[31]
    perfect_candidates = timestamps + np.float32(0.041)
    great_candidates = timestamps + np.float32(0.187)
    perfect_floor = timestamps - np.float32(0.021)
    great_floor = timestamps - np.float32(0.097)
    lanes = np.asarray([(idx * 5 + idx // 7) % 6 - 2 for idx in range(n)], dtype=np.int32)
    raw_fill = 6.5
    action_k = np.arange(0, 15, dtype=np.int32)
    candidate_high_delta_max = float(
        np.float32(np.max(np.maximum(perfect_candidates, great_candidates) - timestamps) + 1.0e-6)
    )
    _hit_values, hit_token_to_id = response_build_gpu_precompute._region_hit_value_universe(
        timestamps,
        perfect_candidates,
        great_candidates,
    )
    table_args = (
        n,
        int(action_k.shape[0]),
        action_k,
        raw_fill,
        timestamps,
        candidate_high_delta_max,
        perfect_floor,
        perfect_candidates,
        great_floor,
        great_candidates,
        lanes,
        hit_token_to_id,
    )
    actual = rb._numba_build_region_core_table(*table_args)
    repeated = rb._numba_build_region_core_table(*table_args)
    assert all(np.array_equal(left, right) for left, right in zip(actual, repeated, strict=True))

    expected_starts: list[int] = []
    expected_columns: list[list[int]] = [[] for _ in range(7)]
    region_stop = int(
        rb._numba_region2_k_scan_stop(int(action_k.shape[0]), float(raw_fill))
    )
    for section_start in range(n + 1):
        expected_starts.append(len(expected_columns[0]))
        shifted = 1 if int(rb._numba_has_shifted_head_region(section_start, raw_fill)) else -1
        for action_idx, k_value in enumerate(action_k):
            k = int(k_value)
            region_offset = -1
            if action_idx < region_stop:
                region_offset = int(
                    rb._numba_region2_offset_for_count(section_start, k, raw_fill, n)
                )
            for offset_idx, offset in enumerate((region_offset, shifted)):
                if int(offset_idx) == 1 and int(shifted) == int(region_offset):
                    continue
                if int(offset) < 1:
                    continue
                (
                    activation,
                    great_end,
                    is_great,
                    perfect_valid,
                    activation_hit_token,
                    perfect_hit_token,
                    valid,
                ) = _retired_boolean_region_core_for_offset(
                    rb,
                    n=n,
                    section_start=section_start,
                    offset=int(offset),
                    k=k,
                    raw_fill=raw_fill,
                    timestamps=timestamps,
                    candidate_high_delta_max=candidate_high_delta_max,
                    perfect_floor=perfect_floor,
                    perfect_candidates=perfect_candidates,
                    great_floor=great_floor,
                    great_candidates=great_candidates,
                    lanes=lanes,
                )
                if int(valid) == 0:
                    continue
                expected_columns[0].append(int(offset))
                expected_columns[1].append(int(activation))
                expected_columns[2].append(int(great_end))
                expected_columns[3].append(int(is_great))
                expected_columns[4].append(
                    int(hit_token_to_id[int(activation_hit_token)]) if int(is_great) else -1
                )
                expected_columns[5].append(
                    int(hit_token_to_id[int(perfect_hit_token)]) if int(perfect_valid) else -1
                )
                expected_columns[6].append(int(perfect_valid))
    expected_starts.append(len(expected_columns[0]))
    assert np.array_equal(actual[0], np.asarray(expected_starts, dtype=np.int64))
    for actual_column, expected_column in zip(actual[1:], expected_columns, strict=True):
        assert np.array_equal(actual_column, np.asarray(expected_column, dtype=np.int32))


def test_region_table_huge_finite_denominator_is_exactly_empty_without_conversion() -> None:
    from gear_optimizer.solver.taichi_gem.force_greats import response_build_gpu_numba as rb

    n = 12
    denom = float(np.finfo(np.float64).max)
    timestamps = np.arange(n, dtype=np.float32)
    action_k = np.arange(8, dtype=np.int32)
    lanes = np.arange(n, dtype=np.int32)
    token_ids = np.arange(5 * n, dtype=np.int32)
    table = rb._numba_build_region_core_table(
        n,
        int(action_k.shape[0]),
        action_k,
        denom,
        timestamps,
        0.2,
        timestamps - np.float32(0.08),
        timestamps + np.float32(0.08),
        timestamps - np.float32(0.19),
        timestamps + np.float32(0.19),
        lanes,
        token_ids,
    )
    assert np.array_equal(table[0], np.zeros(n + 2, dtype=np.int64))
    assert all(column.shape == (0,) for column in table[1:])
    assert rb._numba_region_core_candidate_capacity(
        n, int(action_k.shape[0]), action_k, denom
    ) == 0
    family_count, *_families = rb._numba_build_region2_packet_families(
        int(action_k.shape[0]), denom, action_k, n
    )
    assert int(family_count) == 0
    assert rb._numba_region2_offset_for_count(0, 2, denom, n) == -1
