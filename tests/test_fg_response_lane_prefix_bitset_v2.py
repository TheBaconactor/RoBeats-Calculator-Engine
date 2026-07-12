from __future__ import annotations

import numpy as np
import pytest

from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
    _LANE_PREFIX_EPOCH_RESET_LIMIT,
    _numba_activation_reachable_contiguous_run,
    _numba_activation_reachable_contiguous_run_with_scratch,
    _numba_build_activation_reachability_workspace,
    _numba_exact_lane_classes,
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
    """Retired allocation-heavy Boolean lattice, retained only as a differential oracle."""
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

    g0 = max(start, int(great_start), 0)
    g1 = min(end, int(great_start) + int(great_count))
    if g1 < g0:
        g1 = g0
    h_a = np.float32(float(activation_hit_timestamp))
    activation_lane = int(lanes[a])
    activation_is_great = bool(int(activation_great_i) != 0 or g0 <= a < g1)
    lo_a = great_floor_timestamps[a] if activation_is_great else perfect_floor_timestamps[a]
    unit_a = 0.5 if activation_is_great else 1.0
    forced_units = 0.0
    optional_lanes: list[int] = []
    optional_half: list[int] = []

    guaranteed_forced_end = int(
        np.searchsorted(
            timestamps,
            np.float32(float(h_a) - float(candidate_high_delta_max)),
            side="left",
        )
    )
    guaranteed_forced_end = min(guaranteed_forced_end, a, end)
    if guaranteed_forced_end > start:
        overlap_lo = max(start, g0)
        overlap_hi = min(guaranteed_forced_end, g1)
        great_notes = max(0, overlap_hi - overlap_lo)
        forced_units += float(guaranteed_forced_end - start) - 0.5 * float(great_notes)
        if forced_units >= denom:
            return False
    scan_start = max(start, guaranteed_forced_end)

    for j in range(scan_start, end):
        if j == a:
            continue
        if j > a and great_floor_timestamps[j] > h_a:
            break
        is_great = g0 <= j < g1
        lo_j = great_floor_timestamps[j] if is_great else perfect_floor_timestamps[j]
        hi_j = great_candidate_timestamps[j] if is_great else perfect_candidate_timestamps[j]
        unit_j = 0.5 if is_great else 1.0
        same_lane = int(lanes[j]) == activation_lane
        if same_lane and j > a and hi_j < h_a and lo_a <= hi_j:
            return False
        if hi_j < h_a or (same_lane and j < a and lo_j <= h_a):
            forced_units += unit_j
            if forced_units >= denom:
                return False
            continue
        if lo_j <= h_a and not (same_lane and j > a):
            optional_lanes.append(int(lanes[j]))
            optional_half.append(1 if unit_j == 0.5 else 2)

    if forced_units >= denom:
        return False
    lo_needed = max(0.0, denom - unit_a - forced_units)
    hi_open = denom - forced_units
    cap = int(np.ceil(2.0 * hi_open)) + 2
    achievable = np.zeros(cap + 1, dtype=np.bool_)
    achievable[0] = True
    lane_order: list[int] = []
    for lane_id in optional_lanes:
        if all(int(existing) != int(lane_id) for existing in lane_order):
            lane_order.append(int(lane_id))
    for lane_id in lane_order:
        merged = achievable.copy()
        running = 0
        for note_lane, half_units in zip(optional_lanes, optional_half):
            if note_lane != lane_id:
                continue
            running += int(half_units)
            if running > cap:
                break
            merged[running:] |= achievable[: achievable.shape[0] - running]
        achievable = merged
    for s_half in range(cap + 1):
        if achievable[s_half]:
            s_opt = 0.5 * float(s_half)
            if s_opt >= lo_needed and s_opt < hi_open:
                return True
    return False


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


@pytest.mark.parametrize("denom", [30.5, 31.0, 31.5, 32.0, 32.5, 63.5, 64.0])
def test_lane_prefix_bitset_matches_boolean_oracle_across_word_boundaries(denom: float) -> None:
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
    assert bool(_numba_activation_reachable_contiguous_run(*args)) is _retired_boolean_prefix_reachable(*args)


def test_lane_prefix_bitset_reused_scratch_matches_boolean_oracle() -> None:
    timestamps, perfect_floor, perfect_candidates, great_floor, great_candidates, lanes = _dense_inputs()
    denom = 37.25
    workspace = _numba_build_activation_reachability_workspace(lanes, denom)
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
        actual = _numba_activation_reachable_contiguous_run_with_scratch(*args, *workspace)
        assert bool(actual) is _retired_boolean_prefix_reachable(*args), _case_idx


def test_lane_classification_uses_full_signed_integer_equality() -> None:
    lanes = np.asarray(
        [
            np.iinfo(np.int32).min,
            7,
            np.iinfo(np.int32).max,
            -19,
            7,
            np.iinfo(np.int32).min,
        ],
        dtype=np.int32,
    )
    classes, class_count = _numba_exact_lane_classes(lanes)
    assert int(class_count) == 4
    for left in range(len(lanes)):
        for right in range(len(lanes)):
            assert (int(classes[left]) == int(classes[right])) is (int(lanes[left]) == int(lanes[right]))


def test_lane_prefix_bitset_epoch_rollover_clears_stale_lane_state() -> None:
    timestamps, perfect_floor, perfect_candidates, great_floor, great_candidates, lanes = _dense_inputs()
    denom = 31.5
    workspace = _numba_build_activation_reachability_workspace(lanes, denom)
    workspace[1][:] = np.int32(77)
    workspace[2][:] = np.int32(88)
    workspace[3][:] = np.int32(_LANE_PREFIX_EPOCH_RESET_LIMIT)
    workspace[9][0] = np.int32(_LANE_PREFIX_EPOCH_RESET_LIMIT)
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
        denom,
        0,
        96,
        7,
        61,
        0,
    )
    actual = _numba_activation_reachable_contiguous_run_with_scratch(*args, *workspace)
    assert bool(actual) is _retired_boolean_prefix_reachable(*args)
    assert int(workspace[9][0]) == 1


@pytest.mark.parametrize("denom", [float("inf"), float("nan")])
def test_lane_prefix_scratch_rejects_nonfinite_denominator(denom: float) -> None:
    timestamps, perfect_floor, perfect_candidates, great_floor, great_candidates, lanes = _dense_inputs()
    workspace = _numba_build_activation_reachability_workspace(lanes, 10.0)
    with pytest.raises(ValueError, match="finite"):
        _numba_activation_reachable_contiguous_run_with_scratch(
            40,
            float(timestamps[40]),
            0.200001,
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
            *workspace,
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


def test_region_core_table_reused_bitset_workspace_preserves_exact_stream() -> None:
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
