import numpy as np
from numba import njit, types
from numba.typed import Dict, List

_NUMBA_SURFACE_TYPE = types.UniTuple(types.uint64, 7)
_NUMBA_HEAD_OVERLAP_KEY_TYPE = types.UniTuple(types.uint64, 2)
_NUMBA_BODY_PAIR_TYPE = types.UniTuple(types.uint64, 3)
_NUMBA_PACKET_POINT_TYPE = types.UniTuple(types.int64, 3)
_NUMBA_HEAD_BASIS_TYPE = types.Tuple((
    types.uint64,
    types.uint64,
    types.uint64,
    types.uint64,
    types.int64,
    types.int64,
    types.int64,
    types.float64,
    types.float64,
    types.float64,
    types.float64,
    types.float64,
    types.float64,
))
_NUMBA_PACKET_POINT_LIST_TYPE = types.ListType(_NUMBA_PACKET_POINT_TYPE)
_NUMBA_PACKET_POINT_STACK_TYPE = types.ListType(_NUMBA_PACKET_POINT_LIST_TYPE)
_NUMBA_INT_LIST_TYPE = types.ListType(types.int64)
_NUMBA_SURFACE_LIST_TYPE = types.ListType(_NUMBA_SURFACE_TYPE)
_NUMBA_HEAD_BASIS_LIST_TYPE = types.ListType(_NUMBA_HEAD_BASIS_TYPE)
_HEAD_BASIS_FEVER_LO = 0
_HEAD_BASIS_FEVER_HI = 1
_HEAD_BASIS_GREAT_LO = 2
_HEAD_BASIS_GREAT_HI = 3
_HEAD_BASIS_BODY_FEVER = 4
_HEAD_BASIS_BODY_NORMAL_GREAT = 5
_HEAD_BASIS_BODY_FEVER_GREAT = 6
_HEAD_BASIS_B_LO = 7
_HEAD_BASIS_C_LO = 8
_HEAD_BASIS_D_LO = 9
_HEAD_BASIS_B_HI = 10
_HEAD_BASIS_C_HI = 11
_HEAD_BASIS_D_HI = 12

@njit(cache=True, nogil=True)
def _numba_mask_segment(start: int, end: int, offset: int) -> np.uint64:
    lo = max(int(start), int(offset))
    hi = min(int(end), int(offset) + 64)
    if hi <= lo:
        return np.uint64(0)
    width = hi - lo
    if width >= 64:
        return np.uint64(0xFFFFFFFFFFFFFFFF)
    return ((np.uint64(1) << np.uint64(width)) - np.uint64(1)) << np.uint64(lo - int(offset))


@njit(cache=True, nogil=True)
def _numba_range_mask(start: int, end: int, n: int):
    start_i = max(0, min(min(int(start), int(n)), 100))
    end_i = max(0, min(min(int(end), int(n)), 100))
    return _numba_mask_segment(start_i, end_i, 0), _numba_mask_segment(start_i, end_i, 64)


@njit(cache=True, nogil=True)
def _numba_body_count(start: int, end: int, n: int) -> np.uint64:
    body_start = max(int(start), 100)
    body_end = min(int(end), int(n))
    if body_end <= body_start:
        return np.uint64(0)
    return np.uint64(body_end - body_start)


@njit(cache=True, nogil=True)
def _numba_body_overlap_count(first_start: int, first_end: int, second_start: int, second_end: int, n: int) -> np.uint64:
    body_start = max(max(int(first_start), int(second_start)), 100)
    body_end = min(min(int(first_end), int(second_end)), int(n))
    if body_end <= body_start:
        return np.uint64(0)
    return np.uint64(body_end - body_start)


@njit(cache=True, nogil=True)
def _numba_single_head_mask(idx: int, n: int):
    idx_i = int(idx)
    if idx_i < 0 or idx_i >= min(int(n), 100):
        return np.uint64(0), np.uint64(0)
    if idx_i < 64:
        return np.uint64(1) << np.uint64(idx_i), np.uint64(0)
    return np.uint64(0), np.uint64(1) << np.uint64(idx_i - 64)


@njit(cache=True, nogil=True)
def _numba_pack_edge(
    n: int,
    fever_start: int,
    fever_end: int,
    great_start: int,
    great_end: int,
    activation_great_idx: int,
):
    fever_lo, fever_hi = _numba_range_mask(fever_start, fever_end, n)
    great_lo, great_hi = _numba_range_mask(great_start, great_end, n)
    if int(activation_great_idx) >= 0:
        activation_lo, activation_hi = _numba_single_head_mask(int(activation_great_idx), int(n))
        great_lo = great_lo | activation_lo
        great_hi = great_hi | activation_hi
    body_great = _numba_body_count(great_start, great_end, n)
    body_fever_great = _numba_body_overlap_count(fever_start, fever_end, great_start, great_end, n)
    if (
        int(activation_great_idx) >= max(100, int(fever_start))
        and int(activation_great_idx) < min(int(fever_end), int(n))
        and (int(activation_great_idx) < int(great_start) or int(activation_great_idx) >= int(great_end))
    ):
        body_great += np.uint64(1)
        body_fever_great += np.uint64(1)
    return (
        fever_lo,
        fever_hi,
        great_lo,
        great_hi,
        _numba_body_count(fever_start, fever_end, n),
        body_great,
        body_fever_great,
    )


@njit(cache=True, nogil=True)
def _numba_pack_edge_eg(
    n: int,
    fever_start: int,
    fever_end: int,
    great_start: int,
    great_end: int,
    activation_great_idx: int,
    early_great_start: int,
    early_great_end: int,
):
    """`_numba_pack_edge` plus the issue-#44 early-Great tail range [early_great_start,
    early_great_end): notes pulled into fever ONLY as Greats at a section end. They are
    in-fever-and-Great, so they OR into the Great head mask and add to BOTH body_great and
    body_fever_great. The tail is disjoint from the forced-Great prefix [great_start,
    great_end) (forced greats precede the activation), so there is no double count."""
    fever_lo, fever_hi, great_lo, great_hi, body_fever, body_great, body_fever_great = _numba_pack_edge(
        int(n),
        int(fever_start),
        int(fever_end),
        int(great_start),
        int(great_end),
        int(activation_great_idx),
    )
    if int(early_great_end) > int(early_great_start):
        eg_lo, eg_hi = _numba_range_mask(int(early_great_start), int(early_great_end), int(n))
        great_lo = great_lo | eg_lo
        great_hi = great_hi | eg_hi
        eg_body = _numba_body_count(int(early_great_start), int(early_great_end), int(n))
        body_great = body_great + eg_body
        # The early-Great tail lies inside [fever_start, fever_end) by construction, so every
        # tail note is also a fever note -> the overlap equals the tail's body count.
        body_fever_great = body_fever_great + _numba_body_overlap_count(
            int(fever_start), int(fever_end), int(early_great_start), int(early_great_end), int(n)
        )
    return (fever_lo, fever_hi, great_lo, great_hi, body_fever, body_great, body_fever_great)


@njit(cache=True, nogil=True)
def _numba_great_floor_extended_end(
    n: int,
    activation_idx: int,
    activation_great_i: int,
    great_floor_end_idx,
    real_time_idx: int,
) -> int:
    """Issue #44: the early-Great extended fever end for an activation -- searchsorted of the
    earliest-Great floor at the SAME cutoff the perfect/late end used (column 0 = Perfect
    activation, column 1 = late-Great activation). Always >= the perfect/late end (Great reaches
    earlier), clamped to (activation, n]."""
    col = 1 if int(activation_great_i) != 0 else 0
    e = int(great_floor_end_idx[int(real_time_idx), int(activation_idx), int(col)])
    return _numba_clamped_end_idx(int(n), int(activation_idx), int(e))


@njit(cache=True, nogil=True)
def _numba_lower_bound_from(timestamps, value: float) -> int:
    lo = 0
    hi = int(timestamps.shape[0])
    needle = np.float32(float(value))
    while int(lo) < int(hi):
        mid = (int(lo) + int(hi)) // 2
        if timestamps[int(mid)] < needle:
            lo = int(mid) + 1
        else:
            hi = int(mid)
    return int(lo)


@njit(cache=True, nogil=True)
def _numba_latest_activation_hit_for_contiguous_great_run(
    activation_idx: int,
    hit_lo: float,
    hit_hi: float,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    great_start: int,
    great_count: int,
    section_end: int,
):
    a = int(activation_idx)
    n = min(int(section_end), int(timestamps.shape[0]))
    if int(a) < 0 or int(a) >= int(n):
        return 0.0, 0
    lo = float(hit_lo)
    cap = float(hit_hi)
    if lo > cap:
        return 0.0, 0

    great_lo = max(0, min(int(great_start), int(n)))
    great_hi = min(int(n), int(great_lo) + max(0, int(great_count)))
    for j in range(int(a) + 1, int(n)):
        if float(timestamps[int(j)]) >= cap:
            break
        label_hi = great_candidate_timestamps[int(j)] if int(great_lo) <= int(j) < int(great_hi) else perfect_candidate_timestamps[int(j)]
        capped = float(label_hi) - 1.0e-6
        if capped < cap:
            cap = capped
        if cap < lo:
            return 0.0, 0
    return float(cap), 1


@njit(cache=True, nogil=True)
def _numba_edge_end_idx_at_hit(
    n: int,
    activation_idx: int,
    hit: float,
    real_fever_time: float,
    perfect_floor_timestamps,
) -> int:
    e = _numba_lower_bound_from(perfect_floor_timestamps, float(hit) + float(real_fever_time))
    return _numba_clamped_end_idx(int(n), int(activation_idx), int(e))


@njit(cache=True, nogil=True)
def _numba_great_floor_extended_end_at_hit(
    n: int,
    activation_idx: int,
    hit: float,
    real_fever_time: float,
    great_floor_timestamps,
) -> int:
    e = _numba_lower_bound_from(great_floor_timestamps, float(hit) + float(real_fever_time))
    return _numba_clamped_end_idx(int(n), int(activation_idx), int(e))


@njit(cache=True, nogil=True)
def _numba_perfect_activation_hit_for_run(
    activation_idx: int,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    great_start: int,
    great_count: int,
    section_end: int,
):
    a = int(activation_idx)
    n = min(int(section_end), int(timestamps.shape[0]))
    if int(a) < 0 or int(a) >= int(n):
        return 0.0, 0
    chart = float(timestamps[int(a)])
    perfect = float(perfect_candidate_timestamps[int(a)])
    lo = chart if chart < perfect else perfect
    hi = perfect if perfect > chart else chart
    return _numba_latest_activation_hit_for_contiguous_great_run(
        int(a),
        float(lo),
        float(hi),
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        int(great_start),
        int(great_count),
        int(section_end),
    )


@njit(cache=True, nogil=True)
def _numba_late_great_activation_hit_for_run(
    activation_idx: int,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    great_start: int,
    great_count: int,
    section_end: int,
):
    a = int(activation_idx)
    n = min(int(section_end), int(timestamps.shape[0]))
    if int(a) < 0 or int(a) >= int(n):
        return 0.0, 0
    hit_lo = float(np.float32(np.float32(perfect_candidate_timestamps[int(a)]) + np.float32(0.001)))
    hit_hi = float(great_candidate_timestamps[int(a)])
    return _numba_latest_activation_hit_for_contiguous_great_run(
        int(a),
        float(hit_lo),
        float(hit_hi),
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        int(great_start),
        int(great_count),
        int(section_end),
    )


@njit(cache=True, nogil=True)
def _numba_fill_crossing_run(start: int, great_run_start: int, k: int, fever_fill_denom: float, n: int):
    s = int(start)
    g0 = int(great_run_start)
    count = int(k)
    total = int(n)
    denom = float(fever_fill_denom)
    run_lo = g0 if g0 > s else s
    run_hi = g0 + count if g0 + count < total else total
    if run_hi <= run_lo:
        idx = s + int(np.ceil(denom)) - 1
        if idx < total:
            return int(idx), 0
        return -1, 0
    g0 = int(run_lo)
    count = int(run_hi - run_lo)
    perfects_before = int(g0 - s)

    idx = s + int(np.ceil(denom)) - 1
    if idx < g0:
        if idx < total:
            return int(idx), 0
        return -1, 0

    idx = g0 - 1 + int(np.ceil(2.0 * (denom - float(perfects_before))))
    if idx < g0 + count:
        if idx < g0:
            idx = g0
        if idx < total:
            return int(idx), 1
        return -1, 0

    idx = (g0 + count) - 1 + int(np.ceil(denom - float(perfects_before) - 0.5 * float(count)))
    if idx < total:
        return int(idx), 0
    return -1, 0


@njit(cache=True, nogil=True)
def _numba_region2_offset_bounds(start: int, k: int, fever_fill_denom: float, n: int):
    if int(k) <= 0 or int(start) >= int(n):
        return 1, 0
    doubled = int(np.ceil(2.0 * float(fever_fill_denom)))
    lo = int(np.floor(float(doubled - 1 - int(k)) / 2.0)) + 1
    if lo < 1:
        lo = 1
    hi = int(np.floor(float(doubled - 1) / 2.0))
    max_hi = int(n) - int(start) - 1
    if hi > max_hi:
        hi = max_hi
    return int(lo), int(hi)


@njit(cache=True, nogil=True)
def _numba_region2_offset_for_count(start: int, count: int, fever_fill_denom: float, n: int) -> int:
    if int(count) <= 0 or int(start) >= int(n):
        return -1
    denom = float(fever_fill_denom)
    # Let x = run_start - section_start and m = count. The activation is the m-th Great in
    # the run iff x + 0.5*(m-1) < denom <= x + 0.5*m. That half-open interval has width 0.5,
    # so it contains at most one integer x.
    lo = int(np.ceil(denom - 0.5 * float(count)))
    hi = int(np.ceil(denom - 0.5 * float(count - 1))) - 1
    if lo < 1:
        return -1
    if lo != hi:
        return -1
    if int(start) + int(lo) + int(count) - 1 >= int(n):
        return -1
    return int(lo)


@njit(cache=True, nogil=True)
def _numba_activation_reachable_contiguous_run(
    activation_index: int,
    activation_hit_timestamp: float,
    perfect_floor_timestamps,
    perfect_candidate_timestamps,
    great_floor_timestamps,
    great_candidate_timestamps,
    lanes,
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
    denom = float(fever_fill_denom)
    if denom <= 0.0:
        raise ValueError("fever_fill_denom must be > 0")
    total = int(perfect_candidate_timestamps.shape[0])
    if int(end) > int(total):
        return False

    g0 = int(great_start)
    if g0 < start:
        g0 = start
    if g0 < 0:
        g0 = 0
    g1 = int(great_start) + int(great_count)
    if g1 > end:
        g1 = end
    if g1 < g0:
        g1 = g0

    h_a = np.float32(float(activation_hit_timestamp))
    activation_lane = int(lanes[a])
    activation_is_great = int(activation_great_i) != 0 or (int(g0) <= int(a) and int(a) < int(g1))
    lo_a = great_floor_timestamps[a] if activation_is_great else perfect_floor_timestamps[a]
    unit_a = 0.5 if activation_is_great else 1.0
    forced_units = 0.0
    optional_units = 0.0
    for j in range(start, end):
        if int(j) == int(a):
            continue
        is_great = int(g0) <= int(j) and int(j) < int(g1)
        lo_j = great_floor_timestamps[j] if is_great else perfect_floor_timestamps[j]
        hi_j = great_candidate_timestamps[j] if is_great else perfect_candidate_timestamps[j]
        unit_j = 0.5 if is_great else 1.0
        same_lane = int(lanes[j]) == int(activation_lane)
        if same_lane and int(j) > int(a) and hi_j < h_a and lo_a <= hi_j:
            return False
        forced_any_lane = hi_j < h_a
        forced_same_lane_older = same_lane and int(j) < int(a) and lo_j <= h_a
        if forced_any_lane or forced_same_lane_older:
            forced_units += float(unit_j)
            if forced_units >= denom:
                return False
            continue
        if lo_j <= h_a:
            if same_lane and int(j) > int(a):
                continue
            optional_units += float(unit_j)

    needed_before_activation = max(0.0, denom - float(unit_a))
    return bool(forced_units < denom and forced_units + optional_units >= needed_before_activation)


@njit(cache=True, nogil=True)
def _numba_minimal_reachable_region_great_end(
    activation: int,
    section_start: int,
    run_start: int,
    raw_fever_fill: float,
    timestamps,
    perfect_floor_timestamps,
    perfect_candidate_timestamps,
    great_floor_timestamps,
    great_candidate_timestamps,
    lanes,
    n: int,
) -> tuple[int, float]:
    a = int(activation)
    hit_hi = great_candidate_timestamps[a]
    max_great_end = int(a) + 1
    while int(max_great_end) < int(n) and perfect_candidate_timestamps[int(max_great_end)] < hit_hi:
        max_great_end += 1
    for great_end in range(int(a) + 1, int(max_great_end) + 1):
        hit, valid = _numba_late_great_activation_hit_for_run(
            int(a),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            int(run_start),
            int(great_end) - int(run_start),
            int(n),
        )
        if int(valid) == 0:
            continue
        if _numba_activation_reachable_contiguous_run(
            int(a),
            float(hit),
            perfect_floor_timestamps,
            perfect_candidate_timestamps,
            great_floor_timestamps,
            great_candidate_timestamps,
            lanes,
            float(raw_fever_fill),
            int(section_start),
            int(n),
            int(run_start),
            int(great_end) - int(run_start),
            1,
        ):
            return int(great_end), float(hit)
    return -1, 0.0


@njit(cache=True, nogil=True)
def _numba_has_shifted_head_region(section_start: int, raw_fever_fill: float) -> int:
    if int(section_start) >= 99:
        return 0
    return 1 if int(np.ceil(float(raw_fever_fill))) > 1 else 0


@njit(cache=True, nogil=True)
def _numba_region_run_edge_for_offset(
    n: int,
    section_start: int,
    offset: int,
    k: int,
    raw_fever_fill: float,
    timestamps,
    perfect_floor_timestamps,
    perfect_candidate_timestamps,
    great_floor_timestamps,
    great_candidate_timestamps,
    lanes,
    real_fever_time: float,
):
    run_start = int(section_start) + int(offset)
    activation, is_great = _numba_fill_crossing_run(
        int(section_start), int(run_start), int(k), float(raw_fever_fill), int(n)
    )
    if int(activation) < 0:
        return -1, -1, -1, -1, -1, 0.0, 0

    if int(is_great) != 0:
        great_end, activation_hit = _numba_minimal_reachable_region_great_end(
            int(activation),
            int(section_start),
            int(run_start),
            float(raw_fever_fill),
            timestamps,
            perfect_floor_timestamps,
            perfect_candidate_timestamps,
            great_floor_timestamps,
            great_candidate_timestamps,
            lanes,
            int(n),
        )
        if int(great_end) < 0:
            return -1, -1, -1, -1, -1, 0.0, 0
        perfect_hit, perfect_valid = _numba_perfect_activation_hit_for_run(
            int(activation),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            int(run_start),
            int(great_end) - int(run_start),
            int(n),
        )
        perfect_e = -1
        if int(perfect_valid) != 0:
            perfect_e = _numba_edge_end_idx_at_hit(
                int(n),
                int(activation),
                float(perfect_hit),
                float(real_fever_time),
                perfect_floor_timestamps,
            )
        activation_e = _numba_edge_end_idx_at_hit(
            int(n),
            int(activation),
            float(activation_hit),
            float(real_fever_time),
            perfect_floor_timestamps,
        )
        if int(activation_e) <= int(perfect_e):
            return -1, -1, -1, -1, -1, 0.0, 0
        return (
            int(activation),
            int(activation_e),
            int(run_start),
            int(great_end),
            int(activation),
            float(activation_hit),
            1,
        )

    great_end = min(int(n), int(run_start) + int(k))
    if int(great_end) <= int(run_start):
        return -1, -1, -1, -1, -1, 0.0, 0
    perfect_hit, perfect_valid = _numba_perfect_activation_hit_for_run(
        int(activation),
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        int(run_start),
        int(great_end) - int(run_start),
        int(n),
    )
    if int(perfect_valid) == 0:
        return -1, -1, -1, -1, -1, 0.0, 0
    if not _numba_activation_reachable_contiguous_run(
        int(activation),
        float(perfect_hit),
        perfect_floor_timestamps,
        perfect_candidate_timestamps,
        great_floor_timestamps,
        great_candidate_timestamps,
        lanes,
        float(raw_fever_fill),
        int(section_start),
        int(n),
        int(run_start),
        int(great_end) - int(run_start),
        0,
    ):
        return -1, -1, -1, -1, -1, 0.0, 0
    edge_e = _numba_edge_end_idx_at_hit(
        int(n),
        int(activation),
        float(perfect_hit),
        float(real_fever_time),
        perfect_floor_timestamps,
    )
    return (
        int(activation),
        int(edge_e),
        int(run_start),
        int(great_end),
        -1,
        float(perfect_hit),
        1,
    )


@njit(cache=True, nogil=True)
def _numba_mark_region_run_reachable_for_offset(
    reachable,
    n: int,
    section_start: int,
    offset: int,
    k: int,
    raw_fever_fill: float,
    timestamps,
    perfect_floor_timestamps,
    perfect_candidate_timestamps,
    great_floor_timestamps,
    great_candidate_timestamps,
    lanes,
    real_fever_time: float,
):
    activation, edge_e, _run_start, _great_end, _activation_great_idx, activation_hit, valid = (
        _numba_region_run_edge_for_offset(
            int(n),
            int(section_start),
            int(offset),
            int(k),
            float(raw_fever_fill),
            timestamps,
            perfect_floor_timestamps,
            perfect_candidate_timestamps,
            great_floor_timestamps,
            great_candidate_timestamps,
            lanes,
            float(real_fever_time),
        )
    )
    if int(valid) == 0:
        return 0
    reachable[int(edge_e)] = True
    return _numba_mark_early_great_reachable_from_hit(
        reachable,
        int(n),
        int(activation),
        int(edge_e),
        float(activation_hit),
        great_floor_timestamps,
        float(real_fever_time),
    )


@njit(cache=True, nogil=True)
def _numba_mark_early_great_reachable(
    reachable,
    n: int,
    activation: int,
    base_e: int,
    activation_great_i: int,
    great_floor_end_idx,
    real_time_idx: int,
) -> int:
    """Issue #44: every early-Great extended end e in (base_e, eg_e] becomes a section boundary,
    so mark it reachable for the downstream DP. No-op when the Great floor reaches no further
    than the Perfect/late boundary (the common case).

    Returns the early-Great band width `eg_e - base_e` (0 in the common case). The caller maxes this
    over every enumerated activation to size the body-pair radix `pair_mod`: each section contributes
    at most `1 + band_width` fever-greats (one boundary Great plus the band's `end_e - edge_e` extras,
    line ~1398), so the radix must clear `(sections) * (1 + max band width)`."""
    if int(base_e) < 0 or int(activation) < 0 or int(activation) >= int(n):
        return 0
    eg_e = _numba_great_floor_extended_end(
        int(n), int(activation), int(activation_great_i), great_floor_end_idx, int(real_time_idx)
    )
    for e in range(int(base_e) + 1, int(eg_e) + 1):
        reachable[int(e)] = True
    return max(0, int(eg_e) - int(base_e))


@njit(cache=True, nogil=True)
def _numba_mark_early_great_reachable_from_hit(
    reachable,
    n: int,
    activation: int,
    base_e: int,
    activation_hit: float,
    great_floor_timestamps,
    real_fever_time: float,
) -> int:
    if int(base_e) < 0 or int(activation) < 0 or int(activation) >= int(n):
        return 0
    eg_e = _numba_great_floor_extended_end_at_hit(
        int(n), int(activation), float(activation_hit), float(real_fever_time), great_floor_timestamps
    )
    for e in range(int(base_e) + 1, int(eg_e) + 1):
        reachable[int(e)] = True
    return max(0, int(eg_e) - int(base_e))


@njit(cache=True, nogil=True)
def _numba_append_edge_tail(
    generated,
    edge,
    end_e: int,
    body_values,
    body_starts,
    body_counts,
    head_frontiers,
    head_limit: int,
) -> int:
    """Append `edge` joined with the tail frontier at state `end_e`, dispatching to the body /
    terminal / head-frontier tail exactly like the inline Perfect-edge append. Used for the
    issue-#44 early-Great extended edges (which can land in any of the three regions)."""
    if int(end_e) >= 100:
        return _numba_append_body_tail_array_surfaces(
            generated, edge, body_values, body_starts, body_counts, int(end_e)
        )
    elif int(end_e) >= int(head_limit):
        return _numba_append_terminal_tail_surface(generated, edge)
    return _numba_append_surface_tail_surfaces(generated, edge, head_frontiers[int(end_e)])


@njit(cache=True, nogil=True)
def _numba_combine(edge, tail):
    return (
        edge[0] | tail[0],
        edge[1] | tail[1],
        edge[2] | tail[2],
        edge[3] | tail[3],
        edge[4] + tail[4],
        edge[5] + tail[5],
        edge[6] + tail[6],
    )


@njit(cache=True, nogil=True)
def _numba_reduce(surfaces):
    kept = List.empty_list(_NUMBA_SURFACE_TYPE)
    n = len(surfaces)
    if n == 0:
        kept.append((
            np.uint64(0),
            np.uint64(0),
            np.uint64(0),
            np.uint64(0),
            np.uint64(0),
            np.uint64(0),
            np.uint64(0),
        ))
        return kept
    # Head-overlap-bucketed Pareto maxima. Head fever/great overlap must match inside a dominance
    # scan; body Greats are compared in scorer-visible coordinates:
    #   normal_great = body_great - body_fever_great, fever_great = body_fever_great.
    # This keeps the reduction candidate-independent and lossless while allowing a surface with no
    # more normal Greats and no more fever Greats to dominate one with the same head-overlap class.
    kept_flag = np.zeros(n, dtype=np.bool_)
    prev_same = np.full(n, -1, dtype=np.int64)
    bucket_head = Dict.empty(_NUMBA_HEAD_OVERLAP_KEY_TYPE, types.int64)
    for idx in range(n):
        cf_lo, cf_hi, cg_lo, cg_hi, cbf, cbg, cbfg = surfaces[idx]
        cng = cbg - cbfg
        key = (cf_lo & cg_lo, cf_hi & cg_hi)
        head = bucket_head[key] if key in bucket_head else -1
        # phase 1: dominated by a currently-kept surface in the same class?
        dominated = False
        pos = head
        while pos != -1:
            if kept_flag[pos]:
                kf_lo, kf_hi, kg_lo, kg_hi, kbf, kbg, kbfg = surfaces[pos]
                kng = kbg - kbfg
                if (
                    kbf >= cbf
                    and kng <= cng
                    and kbfg <= cbfg
                    and (cf_lo & ~kf_lo) == 0
                    and (cf_hi & ~kf_hi) == 0
                    and (kg_lo & ~cg_lo) == 0
                    and (kg_hi & ~cg_hi) == 0
                ):
                    dominated = True
                    break
            pos = prev_same[pos]
        if dominated:
            continue
        # phase 2: retire currently-kept surfaces in the same class that this one dominates.
        pos = head
        while pos != -1:
            if kept_flag[pos]:
                kf_lo, kf_hi, kg_lo, kg_hi, kbf, kbg, kbfg = surfaces[pos]
                kng = kbg - kbfg
                if (
                    cbf >= kbf
                    and cng <= kng
                    and cbfg <= kbfg
                    and (kf_lo & ~cf_lo) == 0
                    and (kf_hi & ~cf_hi) == 0
                    and (cg_lo & ~kg_lo) == 0
                    and (cg_hi & ~kg_hi) == 0
                ):
                    kept_flag[pos] = False
            pos = prev_same[pos]
        prev_same[idx] = head
        bucket_head[key] = idx
        kept_flag[idx] = True
    for idx in range(n):
        if kept_flag[idx]:
            kept.append(surfaces[idx])
    return kept


@njit(cache=True, nogil=True)
def _numba_prefix_head_great_mask(count: int):
    clipped = max(0, min(int(count), 100))
    lo = _numba_mask_segment(0, min(clipped, 64), 0)
    hi = _numba_mask_segment(64, clipped, 64)
    return lo, hi


@njit(cache=True, nogil=True)
def _numba_body_prefix_surface(head_great_count: int, body_fever, body_great, body_fever_great):
    great_lo, great_hi = _numba_prefix_head_great_mask(int(head_great_count))
    return (
        np.uint64(0),
        np.uint64(0),
        great_lo,
        great_hi,
        np.uint64(body_fever),
        np.uint64(body_great),
        np.uint64(body_fever_great),
    )


@njit(cache=True, nogil=True)
def _numba_branch_a_body_max_query_stamped(
    values,
    stamps,
    stamp: int,
    fever_great_idx: int,
    normal_great_idx: int,
    width: int,
) -> int:
    best = -1
    fever_cursor = int(fever_great_idx) + 1
    while fever_cursor > 0:
        base = int(fever_cursor) * int(width)
        normal_cursor = int(normal_great_idx) + 1
        while normal_cursor > 0:
            flat_idx = int(base) + int(normal_cursor)
            if int(stamps[int(flat_idx)]) == int(stamp):
                value = int(values[int(flat_idx)])
                if int(value) > int(best):
                    best = int(value)
            normal_cursor -= normal_cursor & -normal_cursor
        fever_cursor -= fever_cursor & -fever_cursor
    return int(best)


@njit(cache=True, nogil=True)
def _numba_branch_a_body_max_update_stamped(
    values,
    stamps,
    stamp: int,
    fever_great_idx: int,
    normal_great_idx: int,
    value: int,
    width: int,
) -> None:
    fever_limit = int(values.shape[0]) // int(width)
    fever_cursor = int(fever_great_idx) + 1
    while fever_cursor < int(fever_limit):
        base = int(fever_cursor) * int(width)
        normal_cursor = int(normal_great_idx) + 1
        while normal_cursor < int(width):
            flat_idx = int(base) + int(normal_cursor)
            if int(stamps[int(flat_idx)]) != int(stamp):
                stamps[int(flat_idx)] = int(stamp)
                values[int(flat_idx)] = int(value)
            elif int(value) > int(values[int(flat_idx)]):
                values[int(flat_idx)] = int(value)
            normal_cursor += normal_cursor & -normal_cursor
        fever_cursor += fever_cursor & -fever_cursor


@njit(cache=True, nogil=True)
def _numba_append_branch_a_body_prefix_surface(
    bucket,
    head_great_count: int,
    body_fever,
    body_great,
    body_fever_great,
    values,
    stamps,
    stamp: int,
    width: int,
) -> bool:
    bg = int(body_great)
    bfg = int(body_fever_great)
    normal_great = int(bg) - int(bfg)
    if (
        int(bg) < 0
        or int(normal_great) < 0
        or int(normal_great) + 1 >= int(width)
        or int(bfg) < 0
        or (int(bfg) + 1) * int(width) >= len(values)
    ):
        raise ValueError("Branch-A FG response prefix reducer received an out-of-bounds body pair")
    prev = _numba_branch_a_body_max_query_stamped(
        values,
        stamps,
        int(stamp),
        int(bfg),
        int(normal_great),
        int(width),
    )
    if int(prev) >= int(body_fever):
        return False
    bucket.append(
        _numba_body_prefix_surface(
            int(head_great_count),
            body_fever,
            body_great,
            body_fever_great,
        )
    )
    _numba_branch_a_body_max_update_stamped(
        values,
        stamps,
        int(stamp),
        int(bfg),
        int(normal_great),
        int(body_fever),
        int(width),
    )
    return True


@njit(cache=True, nogil=True)
def _numba_single_body_frontier_row(body_fever: int):
    out = np.zeros((1, 7), dtype=np.uint64)
    out[0, 4] = np.uint64(body_fever)
    return out


@njit(cache=True, nogil=True)
def _numba_append_body_tail_array_surfaces(generated, edge, body_values, body_starts, body_counts, state: int) -> int:
    count = int(body_counts[int(state)])
    start = int(body_starts[int(state)])
    for tail_idx in range(count):
        value_idx = int(start) + int(tail_idx)
        tail_fever, tail_great, tail_fever_great = body_values[int(value_idx)]
        generated.append((
            edge[0],
            edge[1],
            edge[2],
            edge[3],
            edge[4] + tail_fever,
            edge[5] + tail_great,
            edge[6] + tail_fever_great,
        ))
    return int(count)


@njit(cache=True, nogil=True)
def _numba_append_surface_tail_surfaces(generated, edge, tail_frontier) -> int:
    count = 0
    for tail_idx in range(len(tail_frontier)):
        generated.append(_numba_combine(edge, tail_frontier[tail_idx]))
        count += 1
    return count


@njit(cache=True, nogil=True)
def _numba_emit_early_great_edges(
    generated,
    generated_basis,
    n: int,
    fill_pos: int,
    base_e: int,
    activation_hit: float,
    great_start: int,
    great_end: int,
    activation_great_idx: int,
    great_floor_timestamps,
    real_fever_time: float,
    body_values,
    body_starts,
    body_counts,
    head_frontiers,
    head_limit: int,
    lo_pos: int,
    hi_pos: int,
    min_surfaces: int,
    bounded_mode: int,
):
    """Issue #44: emit one activation's early-Great extended edges. Each end e in (base_e, eg_e]
    adds the tail [base_e, e) as fever-Greats and is composed via `_numba_append_edge_tail` exactly
    like the base edge. Shared by the Perfect- and late-Great-activation branches of both the
    per-state and first-frontier build loops (the CPU twin in response_builder.py factors the same
    logic into `_early_great_options`)."""
    eg_e = _numba_great_floor_extended_end_at_hit(
        int(n), int(fill_pos), float(activation_hit), float(real_fever_time), great_floor_timestamps
    )
    added = 0
    for end_e in range(int(base_e) + 1, int(eg_e) + 1):
        edge_eg = _numba_pack_edge_eg(
            int(n),
            int(fill_pos),
            int(end_e),
            int(great_start),
            int(great_end),
            int(activation_great_idx),
            int(base_e),
            int(end_e),
        )
        generated, generated_basis, edge_added, bounded_mode = _numba_append_head_generated_candidate(
            generated,
            generated_basis,
            edge_eg,
            int(end_e),
            body_values,
            body_starts,
            body_counts,
            head_frontiers,
            int(head_limit),
            int(lo_pos),
            int(hi_pos),
            int(min_surfaces),
            int(bounded_mode),
        )
        added += int(edge_added)
    return generated, generated_basis, int(added), int(bounded_mode)


@njit(cache=True, nogil=True)
def _numba_emit_region2_head_edges(
    generated,
    generated_basis,
    n: int,
    section_start: int,
    action_count: int,
    raw_fever_fill: float,
    action_k,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing_i: int,
    body_values,
    body_starts,
    body_counts,
    head_frontiers,
    head_limit: int,
    lo_pos: int,
    hi_pos: int,
    min_surfaces: int,
    bounded_mode: int,
):
    if int(use_forced_great_timing_i) == 0:
        return generated, generated_basis, 0, int(bounded_mode)
    added_total = 0
    shifted_head_offset = 1 if _numba_has_shifted_head_region(int(section_start), float(raw_fever_fill)) else -1
    for action_idx in range(int(action_count)):
        k = int(action_k[int(action_idx)])
        region_offset = _numba_region2_offset_for_count(int(section_start), int(k), float(raw_fever_fill), int(n))
        for offset_idx in range(2):
            if int(offset_idx) == 0:
                offset = int(region_offset)
            else:
                # For region-3 shifted-head runs, activation/end are offset-invariant for a fixed
                # k. The earliest run is the score-dominant representative because head Great
                # penalty is nondecreasing with chart index; later starts only move the same Great
                # count onto higher-ramp notes.
                offset = int(shifted_head_offset)
                if int(offset) == int(region_offset):
                    continue
            if int(offset) < 1:
                continue
            activation, edge_e, run_start, great_end, activation_great_idx, activation_hit, valid = (
                _numba_region_run_edge_for_offset(
                    int(n),
                    int(section_start),
                    int(offset),
                    int(k),
                    float(raw_fever_fill),
                    timestamps,
                    perfect_floor_timestamps,
                    perfect_candidate_timestamps,
                    great_floor_timestamps,
                    great_candidate_timestamps,
                    lanes,
                    float(real_fever_time),
                )
            )
            if int(valid) == 0:
                continue
            edge = _numba_pack_edge(
                int(n),
                int(activation),
                int(edge_e),
                int(run_start),
                int(great_end),
                int(activation_great_idx),
            )
            generated, generated_basis, added, bounded_mode = _numba_append_head_generated_candidate(
                generated,
                generated_basis,
                edge,
                int(edge_e),
                body_values,
                body_starts,
                body_counts,
                head_frontiers,
                int(head_limit),
                int(lo_pos),
                int(hi_pos),
                int(min_surfaces),
                int(bounded_mode),
            )
            added_total += int(added)
            generated, generated_basis, added_eg, bounded_mode = _numba_emit_early_great_edges(
                generated,
                generated_basis,
                int(n),
                int(activation),
                int(edge_e),
                float(activation_hit),
                int(run_start),
                int(great_end),
                int(activation_great_idx),
                great_floor_timestamps,
                float(real_fever_time),
                body_values,
                body_starts,
                body_counts,
                head_frontiers,
                int(head_limit),
                int(lo_pos),
                int(hi_pos),
                int(min_surfaces),
                int(bounded_mode),
            )
            added_total += int(added_eg)
    return generated, generated_basis, int(added_total), int(bounded_mode)


@njit(cache=True, nogil=True)
def _numba_append_terminal_tail_surface(generated, edge) -> int:
    generated.append(edge)
    return 1


@njit(cache=True, nogil=True)
def _numba_prefix_max_query_stamped(values, stamps, stamp: int, idx: int) -> int:
    best = -1
    cursor = int(idx) + 1
    while cursor > 0:
        if int(stamps[cursor]) == int(stamp):
            value = int(values[cursor])
            if value > best:
                best = value
        cursor -= cursor & -cursor
    return best


@njit(cache=True, nogil=True)
def _numba_prefix_max_update_stamped(values, stamps, stamp: int, idx: int, value: int) -> None:
    cursor = int(idx) + 1
    limit = int(values.shape[0])
    while cursor < limit:
        if int(stamps[cursor]) != int(stamp):
            stamps[cursor] = int(stamp)
            values[cursor] = int(value)
        elif int(value) > int(values[cursor]):
            values[cursor] = int(value)
        cursor += cursor & -cursor


@njit(cache=True, nogil=True)
def _numba_touch_body_candidate(
    edge_fever,
    edge_great,
    edge_fever_great,
    tail_fever,
    tail_great,
    tail_fever_great,
    pair_mod: int,
    stamp: int,
    pair_stamp,
    best_fever_by_pair,
    touched_pair,
    touched_count: int,
) -> int:
    body_fever = int(edge_fever + tail_fever)
    body_great = int(edge_great + tail_great)
    body_fever_great = int(edge_fever_great + tail_fever_great)
    if body_fever_great > body_great:
        return int(touched_count)
    normal_great = int(body_great - body_fever_great)
    # Fail loud on radix overflow. The pack normal_great*pair_mod + body_fever_great is injective
    # ONLY while body_fever_great < pair_mod; otherwise it silently ALIASES onto a different
    # (normal_great, fever_great) cell -- a phantom surface that the decoder later materialises with
    # the wrong Great counts (it scores higher, wins, and corrupts best_fg_score / breaks trace
    # reconstruction). pair_mod is sized to this geometry's true max body_fever_great, so this must
    # never fire; raising beats silently mis-scoring.
    if int(body_fever_great) < 0 or int(body_fever_great) >= int(pair_mod):
        raise ValueError("FG response body skyline fever-great exceeded pair radix")
    pair_idx = int(normal_great) * int(pair_mod) + int(body_fever_great)
    if int(pair_idx) < 0 or int(pair_idx) >= int(best_fever_by_pair.shape[0]):
        raise ValueError("FG response body skyline pair bound was too small")
    if int(pair_stamp[pair_idx]) != int(stamp):
        pair_stamp[pair_idx] = int(stamp)
        best_fever_by_pair[pair_idx] = int(body_fever)
        touched_pair[int(touched_count)] = int(pair_idx)
        return int(touched_count) + 1
    if int(body_fever) > int(best_fever_by_pair[pair_idx]):
        best_fever_by_pair[pair_idx] = int(body_fever)
    return int(touched_count)


@njit(cache=True, nogil=True)
def _numba_hull_filter_body_pairs(frontier):
    """Issue #44: drop the Pareto-interior body-tail points that NO stat cell can select.

    For a fixed (PP/combo/fever/color) cell the body score is LINEAR in the three body counts:
    `A*body_fever - pnp*normal_great - pfp*fever_great` with A,pnp,pfp >= 0 (A=fever_val-combo_val>=0
    since fever_mul>=1). So the max over the frontier is always on its convex hull; the full Pareto
    staircase keeps interior points that are optimal for NO cell. The early-Great extension adds
    points at CONSTANT normal_great (it bumps body_fever and fever_great together), so within each
    normal_great level the objective is the 2-D functional `A*body_fever - pfp*fever_great` and the
    useful set is the 2-D upper hull in `(body_fever, -fever_great)`. Pruning to that hull is
    bit-exact (the per-cell max is preserved for every cone direction) and O(m log m); it is shift-
    invariant, so it stays exact as the DP adds section counts and composes with the head. Removing
    these dead points shrinks every downstream frontier -> the early-Great build/solve overhead
    drops to the minimal set actually reachable by some loadout."""
    m = len(frontier)
    if m <= 2:
        return frontier
    bf = np.empty(m, dtype=np.int64)
    bg = np.empty(m, dtype=np.int64)
    bfg = np.empty(m, dtype=np.int64)
    ng = np.empty(m, dtype=np.int64)
    for i in range(m):
        a, b, c = frontier[i]
        bf[i] = np.int64(a)
        bg[i] = np.int64(b)
        bfg[i] = np.int64(c)
        ng[i] = np.int64(b) - np.int64(c)
    # Sort by (normal_great asc, body_fever asc). Body counts are < total_notes (a few thousand),
    # so a 2^24 stride keeps the composite key collision-free in int64.
    stride = np.int64(1) << np.int64(24)
    order = np.argsort(ng * stride + bf)
    out = List.empty_list(_NUMBA_BODY_PAIR_TYPE)
    stack = np.empty(m, dtype=np.int64)
    pos = 0
    while pos < m:
        group_ng = ng[order[pos]]
        group_start = pos
        while pos < m and ng[order[pos]] == group_ng:
            pos += 1
        count = pos - group_start
        if count <= 2:
            for j in range(group_start, pos):
                gi = order[j]
                out.append((np.uint64(bf[gi]), np.uint64(bg[gi]), np.uint64(bfg[gi])))
            continue
        # Upper hull of (body_fever, -fever_great): keep right turns (cross < 0).
        top = 0
        for j in range(group_start, pos):
            gi = order[j]
            x = bf[gi]
            y = -bfg[gi]
            while top >= 2:
                i1 = stack[top - 2]
                i2 = stack[top - 1]
                cross = (bf[i2] - bf[i1]) * (y + bfg[i1]) - ((-bfg[i2]) + bfg[i1]) * (x - bf[i1])
                if cross >= 0:
                    top -= 1
                else:
                    break
            stack[top] = gi
            top += 1
        for s in range(top):
            gi = stack[s]
            out.append((np.uint64(bf[gi]), np.uint64(bg[gi]), np.uint64(bfg[gi])))
    return out


# Issue #44 Route A (LOSSLESS): the realizable stat box. The head+body score is MULTILINEAR in
# (v=base_value, c=combo_mul, f=fever_mul, g=great_base) on the realizable region (g<=v, c,f>=1, so
# every floor's max/min is resolved), and a multilinear function attains its extrema at the box
# VERTICES -- so a surface's exact dominance over the WHOLE box is decided at its 16 corners, with
# the integer floors bounded by a per-pair margin. No probe sampling. `c`/`f` are the gear's
# combo/fever-multiplier ranges from Data/Gear/Stats.txt; `v`/`g` are a generous superset of every
# realizable base_value / great_base. assert_head_dominance_box (response_cache) fails loud if a
# gear rebalance pushes c/f outside this box, so the box can never silently under-cover.
_HEAD_DOM_V = (200.0, 8000.0)
_HEAD_DOM_C = (1.95, 2.72)
_HEAD_DOM_F = (2.95, 5.48)
_HEAD_DOM_G = (150.0, 5500.0)
# Body floors hit combo_val/fever_val plus the two great penalties; 2x per body-count delta is a
# safe (over-)estimate of how far they can perturb a pairwise score difference.
_HEAD_DOM_BODY_FLOOR_W = 2


@njit(cache=True, nogil=True)
def _numba_popcount64(x):
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return int((x * np.uint64(0x0101010101010101)) >> np.uint64(56))

# Only run the lossless cone-envelope prune once a head state's reduced frontier exceeds this size.
# The early-Great cascade is what inflates a frontier past it; an ordinary (no-early-Great) head
# state stays well under, and its Pareto set already IS small and a superset of the envelope, so
# skipping the prune there is exact and keeps the build cost at the pre-#44 baseline. Genuine
# cascades still cross the threshold and get pruned (preventing the exponential blow-up).
_HEAD_FILTER_MIN_SURFACES = 96
_HEAD_GENERATED_BOUND_MULTIPLIER = 64
_HEAD_GENERATED_BOUND_MIN = 4096


@njit(cache=True, nogil=True)
def _numba_head_generated_threshold(min_surfaces: int) -> int:
    threshold = int(min_surfaces) * int(_HEAD_GENERATED_BOUND_MULTIPLIER)
    if int(threshold) < int(_HEAD_GENERATED_BOUND_MIN):
        threshold = int(_HEAD_GENERATED_BOUND_MIN)
    return int(threshold)


@njit(cache=True, nogil=True)
def _numba_head_surface_basis(surface, lo_pos, hi_pos):
    lo = int(lo_pos)
    hi = int(hi_pos)
    hlen = hi - lo
    fl, fh, gl, gh, bf, bg, bfg = surface
    one = np.uint64(1)
    c_lo = _HEAD_DOM_C[0]
    c_hi = _HEAD_DOM_C[1]
    k_lo = (c_lo - 1.0) / 100.0
    k_hi = (c_hi - 1.0) / 100.0
    b_lo = 0.0
    c_lo_arr = 0.0
    d_lo = 0.0
    b_hi = 0.0
    c_hi_arr = 0.0
    d_hi = 0.0
    for idx in range(hlen):
        pos = lo + idx
        if pos < 64:
            fbit = (fl >> np.uint64(pos)) & one
            gbit = (gl >> np.uint64(pos)) & one
        else:
            fbit = (fh >> np.uint64(pos - 64)) & one
            gbit = (gh >> np.uint64(pos - 64)) & one
        if fbit == 0 and gbit == 0:
            continue
        slo = 1.0 + k_lo * float(lo + idx + 1)
        shi = 1.0 + k_hi * float(lo + idx + 1)
        if fbit != 0:
            b_lo += slo
            b_hi += shi
        if gbit != 0:
            c_lo_arr += slo
            c_hi_arr += shi
        if fbit != 0 and gbit != 0:
            d_lo += slo
            d_hi += shi
    return (
        fl,
        fh,
        gl,
        gh,
        np.int64(bf),
        np.int64(bg) - np.int64(bfg),
        np.int64(bfg),
        b_lo,
        c_lo_arr,
        d_lo,
        b_hi,
        c_hi_arr,
        d_hi,
    )


@njit(cache=True, nogil=True)
def _numba_head_basis_margin(left, right) -> float:
    bw = _HEAD_DOM_BODY_FLOOR_W
    return float(
        _numba_popcount64(
            (left[_HEAD_BASIS_FEVER_LO] ^ right[_HEAD_BASIS_FEVER_LO])
            | (left[_HEAD_BASIS_GREAT_LO] ^ right[_HEAD_BASIS_GREAT_LO])
        )
        + _numba_popcount64(
            (left[_HEAD_BASIS_FEVER_HI] ^ right[_HEAD_BASIS_FEVER_HI])
            | (left[_HEAD_BASIS_GREAT_HI] ^ right[_HEAD_BASIS_GREAT_HI])
        )
        + bw
        * (
            abs(int(left[_HEAD_BASIS_BODY_FEVER] - right[_HEAD_BASIS_BODY_FEVER]))
            + abs(int(left[_HEAD_BASIS_BODY_NORMAL_GREAT] - right[_HEAD_BASIS_BODY_NORMAL_GREAT]))
            + abs(int(left[_HEAD_BASIS_BODY_FEVER_GREAT] - right[_HEAD_BASIS_BODY_FEVER_GREAT]))
        )
    )


@njit(cache=True, nogil=True)
def _numba_head_basis_corner_score(basis, v, c, f, g, use_hi_c: int) -> float:
    gv = g - v
    body_dn = v * c * (f - 1.0)
    pen_n = c * gv
    pen_f = c * f * gv
    if int(use_hi_c) == 0:
        head = (
            gv * basis[_HEAD_BASIS_C_LO]
            + v * (f - 1.0) * basis[_HEAD_BASIS_B_LO]
            + gv * (f - 1.0) * basis[_HEAD_BASIS_D_LO]
        )
    else:
        head = (
            gv * basis[_HEAD_BASIS_C_HI]
            + v * (f - 1.0) * basis[_HEAD_BASIS_B_HI]
            + gv * (f - 1.0) * basis[_HEAD_BASIS_D_HI]
        )
    return (
        head
        + float(basis[_HEAD_BASIS_BODY_FEVER]) * body_dn
        + float(basis[_HEAD_BASIS_BODY_NORMAL_GREAT]) * pen_n
        + float(basis[_HEAD_BASIS_BODY_FEVER_GREAT]) * pen_f
    )


@njit(cache=True, nogil=True)
def _numba_head_basis_corner_scores_into(basis, scores, row_idx: int) -> None:
    col = 0
    for iv in range(2):
        v = _HEAD_DOM_V[iv]
        for ic in range(2):
            c = _HEAD_DOM_C[ic]
            for iff in range(2):
                f = _HEAD_DOM_F[iff]
                for ig in range(2):
                    g = _HEAD_DOM_G[ig]
                    scores[int(row_idx), int(col)] = _numba_head_basis_corner_score(
                        basis, float(v), float(c), float(f), float(g), int(ic)
                    )
                    col += 1


@njit(cache=True, nogil=True)
def _numba_head_scores_dominate(scores, left_idx: int, right_idx: int, margin: float) -> bool:
    for cc in range(16):
        if scores[int(left_idx), int(cc)] - scores[int(right_idx), int(cc)] < margin:
            return False
    return True


@njit(cache=True, nogil=True)
def _numba_head_basis_dominates(left, right) -> bool:
    margin = _numba_head_basis_margin(left, right)
    for iv in range(2):
        v = _HEAD_DOM_V[iv]
        for ic in range(2):
            c = _HEAD_DOM_C[ic]
            for iff in range(2):
                f = _HEAD_DOM_F[iff]
                for ig in range(2):
                    g = _HEAD_DOM_G[ig]
                    left_score = _numba_head_basis_corner_score(
                        left, float(v), float(c), float(f), float(g), int(ic)
                    )
                    right_score = _numba_head_basis_corner_score(
                        right, float(v), float(c), float(f), float(g), int(ic)
                    )
                    if left_score - right_score < margin:
                        return False
    return True


@njit(cache=True, nogil=True)
def _numba_head_envelope_insert(frontier, candidate, lo_pos, hi_pos):
    if len(frontier) <= 0:
        out = List.empty_list(_NUMBA_SURFACE_TYPE)
        out.append(candidate)
        return out
    candidate_basis = _numba_head_surface_basis(candidate, int(lo_pos), int(hi_pos))
    for idx in range(len(frontier)):
        if _numba_head_basis_dominates(
            _numba_head_surface_basis(frontier[idx], int(lo_pos), int(hi_pos)),
            candidate_basis,
        ):
            return frontier
    out = List.empty_list(_NUMBA_SURFACE_TYPE)
    for idx in range(len(frontier)):
        kept = frontier[idx]
        if not _numba_head_basis_dominates(
            candidate_basis,
            _numba_head_surface_basis(kept, int(lo_pos), int(hi_pos)),
        ):
            out.append(kept)
    out.append(candidate)
    return out


@njit(cache=True, nogil=True)
def _numba_head_basis_frontier(frontier, lo_pos, hi_pos):
    out = List.empty_list(_NUMBA_HEAD_BASIS_TYPE)
    for idx in range(len(frontier)):
        out.append(_numba_head_surface_basis(frontier[idx], int(lo_pos), int(hi_pos)))
    return out


@njit(cache=True, nogil=True)
def _numba_head_envelope_insert_with_basis(frontier, frontier_basis, candidate, candidate_basis):
    if len(frontier) <= 0:
        out = List.empty_list(_NUMBA_SURFACE_TYPE)
        out_basis = List.empty_list(_NUMBA_HEAD_BASIS_TYPE)
        out.append(candidate)
        out_basis.append(candidate_basis)
        return out, out_basis
    for idx in range(len(frontier_basis)):
        if _numba_head_basis_dominates(frontier_basis[idx], candidate_basis):
            return frontier, frontier_basis
    out = List.empty_list(_NUMBA_SURFACE_TYPE)
    out_basis = List.empty_list(_NUMBA_HEAD_BASIS_TYPE)
    for idx in range(len(frontier)):
        kept_basis = frontier_basis[idx]
        if not _numba_head_basis_dominates(candidate_basis, kept_basis):
            out.append(frontier[idx])
            out_basis.append(kept_basis)
    out.append(candidate)
    out_basis.append(candidate_basis)
    return out, out_basis


@njit(cache=True, nogil=True)
def _numba_append_edge_tail_bounded(
    frontier,
    frontier_basis,
    edge,
    end_e: int,
    body_values,
    body_starts,
    body_counts,
    head_frontiers,
    head_limit: int,
    lo_pos: int,
    hi_pos: int,
):
    count = 0
    if int(end_e) >= 100:
        tail_count = int(body_counts[int(end_e)])
        tail_start = int(body_starts[int(end_e)])
        for tail_idx in range(int(tail_count)):
            value_idx = int(tail_start) + int(tail_idx)
            tail_fever, tail_great, tail_fever_great = body_values[int(value_idx)]
            candidate = (
                edge[0],
                edge[1],
                edge[2],
                edge[3],
                edge[4] + tail_fever,
                edge[5] + tail_great,
                edge[6] + tail_fever_great,
            )
            frontier, frontier_basis = _numba_head_envelope_insert_with_basis(
                frontier,
                frontier_basis,
                candidate,
                _numba_head_surface_basis(candidate, int(lo_pos), int(hi_pos)),
            )
            count += 1
        return frontier, frontier_basis, int(count)
    if int(end_e) >= int(head_limit):
        frontier, frontier_basis = _numba_head_envelope_insert_with_basis(
            frontier,
            frontier_basis,
            edge,
            _numba_head_surface_basis(edge, int(lo_pos), int(hi_pos)),
        )
        return frontier, frontier_basis, 1
    tail_frontier = head_frontiers[int(end_e)]
    for tail_idx in range(len(tail_frontier)):
        candidate = _numba_combine(edge, tail_frontier[tail_idx])
        frontier, frontier_basis = _numba_head_envelope_insert_with_basis(
            frontier,
            frontier_basis,
            candidate,
            _numba_head_surface_basis(candidate, int(lo_pos), int(hi_pos)),
        )
        count += 1
    return frontier, frontier_basis, int(count)


@njit(cache=True, nogil=True)
def _numba_append_head_generated_candidate(
    generated,
    generated_basis,
    edge,
    end_e: int,
    body_values,
    body_starts,
    body_counts,
    head_frontiers,
    head_limit: int,
    lo_pos: int,
    hi_pos: int,
    min_surfaces: int,
    bounded_mode: int,
):
    if int(bounded_mode) != 0:
        generated, generated_basis, added = _numba_append_edge_tail_bounded(
            generated,
            generated_basis,
            edge,
            int(end_e),
            body_values,
            body_starts,
            body_counts,
            head_frontiers,
            int(head_limit),
            int(lo_pos),
            int(hi_pos),
        )
        return generated, generated_basis, int(added), 1
    added = _numba_append_edge_tail(
        generated,
        edge,
        int(end_e),
        body_values,
        body_starts,
        body_counts,
        head_frontiers,
        int(head_limit),
    )
    generated, generated_basis, bounded_mode = _numba_maybe_promote_head_generated_with_basis(
        generated,
        generated_basis,
        int(lo_pos),
        int(hi_pos),
        int(min_surfaces),
        int(bounded_mode),
    )
    return generated, generated_basis, int(added), int(bounded_mode)


@njit(cache=True, nogil=True)
def _numba_maybe_promote_head_generated(generated, lo_pos, hi_pos, min_surfaces, bounded_mode: int):
    if int(bounded_mode) != 0:
        return generated, 1
    if len(generated) <= int(_numba_head_generated_threshold(int(min_surfaces))):
        return generated, 0
    return (
        _numba_head_envelope_filter(_numba_reduce(generated), int(lo_pos), int(hi_pos), int(min_surfaces)),
        1,
    )


@njit(cache=True, nogil=True)
def _numba_maybe_promote_head_generated_with_basis(
    generated,
    generated_basis,
    lo_pos,
    hi_pos,
    min_surfaces,
    bounded_mode: int,
):
    if int(bounded_mode) != 0:
        return generated, generated_basis, 1
    if len(generated) <= int(_numba_head_generated_threshold(int(min_surfaces))):
        return generated, generated_basis, 0
    promoted = _numba_head_envelope_filter(
        _numba_reduce(generated), int(lo_pos), int(hi_pos), int(min_surfaces)
    )
    return promoted, _numba_head_basis_frontier(promoted, int(lo_pos), int(hi_pos)), 1


@njit(cache=True, nogil=True)
def _numba_head_envelope_filter(frontier, lo_pos, hi_pos, min_surfaces):
    """Issue #44 Route A: LOSSLESS prune of the head frontier to its cone-Pareto set -- the surfaces
    that are best for SOME realizable stat cell. The head+body score is multilinear in (v,c,f,g) on
    the realizable region (g<=v, c,f>=1 resolve every floor's max/min), so its unfloored value hits
    its box extrema at the 16 corners. Surface K dominates C over the WHOLE realizable box iff
    unfloored score(K)-score(C) >= the per-pair floor margin (head-class Hamming distance + body-count
    delta -- the most the integer floors can move the difference) at all 16 corners. This is the head
    analog of the closed-form body hull `_numba_hull_filter_body_pairs`: best-preserving for EVERY
    realizable cell, by a 16-corner proof, not probe sampling. Composition-safe (the score is additive
    over disjoint edge/tail head ranges), so an envelope-minimal tail stays representative as the DP
    prepends edges. `min_surfaces` gates the prune for small (no-cascade) frontiers; skipping only
    RETAINS surfaces, so it stays lossless."""
    m = len(frontier)
    if m <= min_surfaces:
        return frontier
    if int(hi_pos) - int(lo_pos) <= 0:
        return frontier
    basis = _numba_head_basis_frontier(frontier, int(lo_pos), int(hi_pos))
    # 16 corner relative-scores, (m, 16).
    scores = np.empty((m, 16), dtype=np.float64)
    for i in range(m):
        _numba_head_basis_corner_scores_into(basis[i], scores, int(i))
    # Incremental cone-Pareto: keep C unless some kept K dominates it (gap >= margin at all 16).
    kept = List.empty_list(types.int64)
    for i in range(m):
        dominated = False
        for ki in range(len(kept)):
            k = kept[ki]
            if _numba_head_scores_dominate(
                scores,
                int(k),
                int(i),
                _numba_head_basis_margin(basis[k], basis[i]),
            ):
                dominated = True
                break
        if dominated:
            continue
        survivors = List.empty_list(types.int64)
        for ki in range(len(kept)):
            k = kept[ki]
            if not _numba_head_scores_dominate(
                scores,
                int(i),
                int(k),
                _numba_head_basis_margin(basis[i], basis[k]),
            ):
                survivors.append(k)
        survivors.append(np.int64(i))
        kept = survivors
    out = List.empty_list(_NUMBA_SURFACE_TYPE)
    for ki in range(len(kept)):
        out.append(frontier[kept[ki]])
    return out


@njit(cache=True, nogil=True)
def _numba_bound_head_generated(generated, lo_pos, hi_pos, min_surfaces):
    threshold = int(_numba_head_generated_threshold(int(min_surfaces)))
    if len(generated) <= int(threshold):
        return generated
    return _numba_head_envelope_filter(
        _numba_reduce(generated),
        int(lo_pos),
        int(hi_pos),
        int(min_surfaces),
    )


@njit(cache=True, nogil=True)
def _numba_reduce_touched_body_pairs(
    pair_mod: int,
    touched_pair,
    touched_count: int,
    best_fever_by_pair,
    bit_values,
    bit_stamps,
    bit_stamp: int,
):
    frontier = List.empty_list(_NUMBA_BODY_PAIR_TYPE)
    if int(touched_count) <= 0:
        return frontier
    sorted_pairs = np.sort(touched_pair[: int(touched_count)])
    idx = 0
    while idx < int(touched_count):
        pair_idx = int(sorted_pairs[idx])
        normal_great = int(pair_idx) // int(pair_mod)
        fever_great = int(pair_idx) - int(normal_great) * int(pair_mod)
        best_fever = int(best_fever_by_pair[pair_idx])
        idx += 1
        while idx < int(touched_count) and int(sorted_pairs[idx]) == int(pair_idx):
            idx += 1
        if best_fever > _numba_prefix_max_query_stamped(bit_values, bit_stamps, int(bit_stamp), int(fever_great)):
            frontier.append((
                np.uint64(best_fever),
                np.uint64(normal_great + fever_great),
                np.uint64(fever_great),
            ))
        _numba_prefix_max_update_stamped(bit_values, bit_stamps, int(bit_stamp), int(fever_great), int(best_fever))
    return _numba_hull_filter_body_pairs(frontier)


@njit(cache=True, nogil=True)
def _numba_append_packet_point(bucket, point) -> bool:
    cf, cn, cq = point
    original_len = len(bucket)
    for idx in range(original_len):
        kept = bucket[idx]
        kf, kn, kq = kept
        if kf >= cf and kn <= cn and kq <= cq:
            return False

    write = 0
    for idx in range(original_len):
        kept = bucket[idx]
        kf, kn, kq = kept
        if not (cf >= kf and cn <= kn and cq <= kq):
            bucket[write] = kept
            write += 1
    while len(bucket) > write:
        bucket.pop()
    bucket.append((np.int64(cf), np.int64(cn), np.int64(cq)))
    return True


@njit(cache=True, nogil=True)
def _numba_packet_union(left, right):
    if len(left) <= 0:
        return right
    if len(right) <= 0:
        return left
    if len(left) == 1:
        cf, cn, cq = left[0]
        original_len = len(right)
        for idx in range(original_len):
            kept = right[idx]
            kf, kn, kq = kept
            if kf >= cf and kn <= cn and kq <= cq:
                return right

        out = List.empty_list(_NUMBA_PACKET_POINT_TYPE)
        out.append((np.int64(cf), np.int64(cn), np.int64(cq)))
        for idx in range(original_len):
            kept = right[idx]
            kf, kn, kq = kept
            if not (cf >= kf and cn <= kn and cq <= kq):
                out.append(kept)
        return out
    if len(right) == 1:
        cf, cn, cq = right[0]
        original_len = len(left)
        for idx in range(original_len):
            kept = left[idx]
            kf, kn, kq = kept
            if kf >= cf and kn <= cn and kq <= cq:
                return left

        out = List.empty_list(_NUMBA_PACKET_POINT_TYPE)
        for idx in range(original_len):
            kept = left[idx]
            kf, kn, kq = kept
            if not (cf >= kf and cn <= kn and cq <= kq):
                out.append(kept)
        out.append((np.int64(cf), np.int64(cn), np.int64(cq)))
        return out
    out = List.empty_list(_NUMBA_PACKET_POINT_TYPE)
    for idx in range(len(left)):
        out.append(left[idx])
    for idx in range(len(right)):
        _numba_append_packet_point(out, right[idx])
    return out


@njit(cache=True, nogil=True)
def _numba_build_packet_families(action_count: int, later_fill, later_forced, later_activation_forced):
    cap = max(1, int(action_count) * 2)
    family_mode = np.empty(cap, dtype=np.int32)
    family_defect = np.empty(cap, dtype=np.int32)
    family_start = np.empty(cap, dtype=np.int32)
    family_end = np.empty(cap, dtype=np.int32)
    family_count = 0

    prev_defect = 0
    prev_offset = -1000000000
    for action_idx in range(int(action_count)):
        offset = int(later_fill[int(action_idx)])
        defect = int(later_forced[int(action_idx)]) - (2 * int(offset))
        if int(family_count) > 0 and int(family_mode[family_count - 1]) == 0 and int(prev_defect) == int(defect) and int(offset) == int(prev_offset) + 1:
            family_end[family_count - 1] = int(offset)
        else:
            family_mode[family_count] = 0
            family_defect[family_count] = int(defect)
            family_start[family_count] = int(offset)
            family_end[family_count] = int(offset)
            family_count += 1
        prev_defect = int(defect)
        prev_offset = int(offset)

    prev_defect = 0
    prev_offset = -1000000000
    have_late = False
    for action_idx in range(int(action_count)):
        offset = int(later_fill[int(action_idx)])
        prefix = int(later_activation_forced[int(action_idx)])
        if int(prefix) < 0:
            continue
        defect = int(prefix) - (2 * int(offset))
        if bool(have_late) and int(family_count) > 0 and int(family_mode[family_count - 1]) == 1 and int(prev_defect) == int(defect) and int(offset) == int(prev_offset) + 1:
            family_end[family_count - 1] = int(offset)
        else:
            family_mode[family_count] = 1
            family_defect[family_count] = int(defect)
            family_start[family_count] = int(offset)
            family_end[family_count] = int(offset)
            family_count += 1
        prev_defect = int(defect)
        prev_offset = int(offset)
        have_late = True

    return family_count, family_mode, family_defect, family_start, family_end


@njit(cache=True, nogil=True)
def _numba_packet_queue_transfer(front_alpha, front_aggregate, back_alpha, back_packet, back_aggregate):
    aggregate = List.empty_list(_NUMBA_PACKET_POINT_TYPE)
    while len(back_alpha) > 0:
        alpha = int(back_alpha.pop())
        packet = back_packet.pop()
        back_aggregate.pop()
        if len(aggregate) <= 0:
            aggregate = packet
        else:
            aggregate = _numba_packet_union(packet, aggregate)
        front_alpha.append(np.int64(alpha))
        front_aggregate.append(aggregate)


@njit(cache=True, nogil=True)
def _numba_packet_queue_pop_expired_after(
    high_alpha: int,
    front_alpha,
    front_aggregate,
    back_alpha,
    back_packet,
    back_aggregate,
):
    while True:
        if len(front_alpha) <= 0:
            _numba_packet_queue_transfer(front_alpha, front_aggregate, back_alpha, back_packet, back_aggregate)
        if len(front_alpha) <= 0:
            return
        if int(front_alpha[len(front_alpha) - 1]) <= int(high_alpha):
            return
        front_alpha.pop()
        front_aggregate.pop()


@njit(cache=True, nogil=True)
def _numba_packet_queue_push_back(alpha: int, packet, back_alpha, back_packet, back_aggregate):
    if len(packet) <= 0:
        return
    if len(back_aggregate) > 0:
        aggregate = _numba_packet_union(back_aggregate[len(back_aggregate) - 1], packet)
    else:
        aggregate = packet
    back_alpha.append(np.int64(alpha))
    back_packet.append(packet)
    back_aggregate.append(aggregate)


@njit(cache=True, nogil=True)
def _numba_clamped_end_idx(n: int, activation_idx: int, raw_end_idx: int) -> int:
    edge_e = int(raw_end_idx)
    if int(edge_e) <= int(activation_idx):
        edge_e = int(activation_idx) + 1
    if int(edge_e) > int(n):
        edge_e = int(n)
    return int(edge_e)


@njit(cache=True, nogil=True)
def _numba_packet_queue_push_activation(
    n: int,
    mode: int,
    defect: int,
    activation: int,
    body_values,
    body_starts,
    body_counts,
    use_forced_great_timing_i: int,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    real_time_idx: int,
    back_alpha,
    back_packet,
    back_aggregate,
):
    if int(activation) < 100 or int(activation) >= int(n):
        return
    perfect_e = _numba_clamped_end_idx(
        int(n),
        int(activation),
        int(perfect_end_idx[int(real_time_idx), int(activation)]),
    )
    edge_e = int(perfect_e)
    fever_great_delta = 0
    activation_great_i = 0
    if int(mode) != 0:
        if int(use_forced_great_timing_i) == 0:
            return
        late_e = _numba_clamped_end_idx(
            int(n),
            int(activation),
            int(great_end_idx[int(real_time_idx), int(activation)]),
        )
        if int(late_e) <= int(perfect_e):
            return
        edge_e = int(late_e)
        fever_great_delta = 1
        activation_great_i = 1

    # Issue #44: extend the fever end from `edge_e` (the Perfect/late boundary) up to the
    # earliest-Great floor boundary `eg_e`. Each e in [edge_e, eg_e] is its own Pareto surface;
    # the notes [edge_e, e) are pulled into fever as GREATS (all body, since activation >= 100),
    # so each such e contributes (e - edge_e) extra fever-greats on top of the section's fever
    # length. eg_e == edge_e on the overwhelming majority of activations -> the loop runs once
    # and this is bit-for-bit the pre-#44 behaviour at zero added cost.
    eg_e = _numba_great_floor_extended_end(
        int(n), int(activation), int(activation_great_i), great_floor_end_idx, int(real_time_idx)
    )
    packet = List.empty_list(_NUMBA_PACKET_POINT_TYPE)
    for end_e in range(int(edge_e), int(eg_e) + 1):
        tail_count = int(body_counts[int(end_e)])
        if int(tail_count) <= 0:
            continue
        fever_len = int(end_e) - int(activation)
        extra_fever_great = int(end_e) - int(edge_e)
        tail_start = int(body_starts[int(end_e)])
        for tail_idx in range(int(tail_count)):
            value_idx = int(tail_start) + int(tail_idx)
            tail_fever, tail_great, tail_fever_great = body_values[int(value_idx)]
            tail_normal_great = int(tail_great) - int(tail_fever_great)
            shifted_normal_great = int(tail_normal_great) + (2 * int(activation)) + int(defect)
            packet_fever_great = int(tail_fever_great) + int(fever_great_delta) + int(extra_fever_great)
            packet.append((
                np.int64(int(tail_fever) + int(fever_len)),
                np.int64(int(shifted_normal_great)),
                np.int64(int(packet_fever_great)),
            ))
    if len(packet) <= 0:
        return
    _numba_packet_queue_push_back(
        int(activation),
        packet,
        back_alpha,
        back_packet,
        back_aggregate,
    )


@njit(cache=True, nogil=True)
def _numba_touch_packet_points_for_state(
    packet,
    state_i: int,
    pair_mod: int,
    pair_stamp_value: int,
    pair_stamp,
    best_fever_by_pair,
    touched_pair,
    touched_count: int,
):
    generated_count = 0
    for packet_idx in range(len(packet)):
        body_fever, shifted_normal, fever_great = packet[packet_idx]
        true_normal_great = int(shifted_normal) - (2 * int(state_i))
        touched_count = _numba_touch_body_candidate(
            np.uint64(int(body_fever)),
            np.uint64(int(true_normal_great) + int(fever_great)),
            np.uint64(int(fever_great)),
            np.uint64(0),
            np.uint64(0),
            np.uint64(0),
            int(pair_mod),
            int(pair_stamp_value),
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            int(touched_count),
        )
        generated_count += 1
    return touched_count, generated_count


@njit(cache=True, nogil=True)
def _numba_store_shared_empty_body_tail(body_starts, body_counts, state: int) -> None:
    body_starts[int(state)] = 0
    body_counts[int(state)] = 1


@njit(cache=True, nogil=True)
def _numba_store_body_tail_frontier(body_values, body_starts, body_counts, state: int, cursor: int, frontier) -> int:
    count = len(frontier)
    body_starts[int(state)] = int(cursor)
    body_counts[int(state)] = int(count)
    for idx in range(count):
        body_values.append(frontier[idx])
    return int(cursor) + int(count)


@njit(cache=True, nogil=True)
def _numba_touch_body_tail_array_candidates(
    edge,
    state: int,
    body_values,
    body_starts,
    body_counts,
    pair_mod: int,
    pair_stamp_value: int,
    pair_stamp,
    best_fever_by_pair,
    touched_pair,
    touched_count: int,
):
    count = int(body_counts[int(state)])
    start = int(body_starts[int(state)])
    for tail_idx in range(count):
        value_idx = int(start) + int(tail_idx)
        tail_fever, tail_great, tail_fever_great = body_values[int(value_idx)]
        touched_count = _numba_touch_body_candidate(
            edge[4],
            edge[5],
            edge[6],
            tail_fever,
            tail_great,
            tail_fever_great,
            int(pair_mod),
            int(pair_stamp_value),
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            int(touched_count),
        )
    return int(touched_count), int(count)


@njit(cache=True, nogil=True)
def _numba_touch_prefix_body_candidates(
    n: int,
    state_i: int,
    action_count: int,
    raw_fever_fill: float,
    later_fill,
    later_forced,
    later_activation_forced,
    use_forced_great_timing_i: int,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    real_fever_time: float,
    real_time_idx: int,
    body_values,
    body_starts,
    body_counts,
    pair_mod: int,
    pair_stamp_value: int,
    pair_stamp,
    best_fever_by_pair,
    touched_pair,
    touched_count: int,
):
    generated = 0
    section_start = int(state_i) + 1
    for action_idx in range(int(action_count)):
        fill = int(later_fill[int(action_idx)])
        activation = int(state_i) + int(fill)
        if int(activation) < int(section_start) or int(activation) >= int(n):
            continue
        forced_count = int(later_forced[int(action_idx)])
        perfect_hit, perfect_valid = _numba_perfect_activation_hit_for_run(
            int(activation),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            int(section_start),
            int(forced_count),
            int(n),
        )
        if int(perfect_valid) == 0:
            edge_e = -1
        else:
            edge_e = _numba_edge_end_idx_at_hit(
                int(n),
                int(activation),
                float(perfect_hit),
                float(real_fever_time),
                perfect_floor_timestamps,
            )
        forced_count = int(later_forced[int(action_idx)])
        if int(edge_e) >= 0 and _numba_activation_reachable_contiguous_run(
            int(activation),
            float(perfect_hit),
            perfect_floor_timestamps,
            perfect_candidate_timestamps,
            great_floor_timestamps,
            great_candidate_timestamps,
            lanes,
            float(raw_fever_fill),
            int(section_start),
            int(n),
            int(section_start),
            int(forced_count),
            0,
        ):
            edge = _numba_pack_edge(
                int(n),
                int(activation),
                int(edge_e),
                int(section_start),
                min(int(n), int(section_start) + int(forced_count)),
                -1,
            )
            touched_count, added = _numba_touch_body_tail_array_candidates(
                edge,
                int(edge_e),
                body_values,
                body_starts,
                body_counts,
                int(pair_mod),
                int(pair_stamp_value),
                pair_stamp,
                best_fever_by_pair,
                touched_pair,
                int(touched_count),
            )
            generated += int(added)
            eg_e = _numba_great_floor_extended_end_at_hit(
                int(n), int(activation), float(perfect_hit), float(real_fever_time), great_floor_timestamps
            )
            for end_e in range(int(edge_e) + 1, int(eg_e) + 1):
                edge_eg = _numba_pack_edge_eg(
                    int(n),
                    int(activation),
                    int(end_e),
                    int(section_start),
                    min(int(n), int(section_start) + int(forced_count)),
                    -1,
                    int(edge_e),
                    int(end_e),
                )
                touched_count, added_eg = _numba_touch_body_tail_array_candidates(
                    edge_eg,
                    int(end_e),
                    body_values,
                    body_starts,
                    body_counts,
                    int(pair_mod),
                    int(pair_stamp_value),
                    pair_stamp,
                    best_fever_by_pair,
                    touched_pair,
                    int(touched_count),
                )
                generated += int(added_eg)

        activation_e = -1
        prefix_forced = int(later_activation_forced[int(action_idx)])
        activation_hit = 0.0
        if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
            activation_hit, activation_valid = _numba_late_great_activation_hit_for_run(
                int(activation),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
                int(section_start),
                int(prefix_forced),
                int(n),
            )
            if int(activation_valid) != 0:
                activation_e = _numba_edge_end_idx_at_hit(
                    int(n),
                    int(activation),
                    float(activation_hit),
                    float(real_fever_time),
                    perfect_floor_timestamps,
                )
        if int(activation_e) < 0 or int(activation_e) <= int(edge_e):
            continue
        if not _numba_activation_reachable_contiguous_run(
            int(activation),
            float(activation_hit),
            perfect_floor_timestamps,
            perfect_candidate_timestamps,
            great_floor_timestamps,
            great_candidate_timestamps,
            lanes,
            float(raw_fever_fill),
            int(section_start),
            int(n),
            int(section_start),
            int(prefix_forced),
            1,
        ):
            continue
        activation_edge = _numba_pack_edge(
            int(n),
            int(activation),
            int(activation_e),
            int(section_start),
            min(int(n), int(section_start) + int(prefix_forced)),
            int(activation),
        )
        touched_count, added = _numba_touch_body_tail_array_candidates(
            activation_edge,
            int(activation_e),
            body_values,
            body_starts,
            body_counts,
            int(pair_mod),
            int(pair_stamp_value),
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            int(touched_count),
        )
        generated += int(added)
        eg_e_late = _numba_great_floor_extended_end_at_hit(
            int(n), int(activation), float(activation_hit), float(real_fever_time), great_floor_timestamps
        )
        for end_e in range(int(activation_e) + 1, int(eg_e_late) + 1):
            activation_edge_eg = _numba_pack_edge_eg(
                int(n),
                int(activation),
                int(end_e),
                int(section_start),
                min(int(n), int(section_start) + int(prefix_forced)),
                int(activation),
                int(activation_e),
                int(end_e),
            )
            touched_count, added_eg = _numba_touch_body_tail_array_candidates(
                activation_edge_eg,
                int(end_e),
                body_values,
                body_starts,
                body_counts,
                int(pair_mod),
                int(pair_stamp_value),
                pair_stamp,
                best_fever_by_pair,
                touched_pair,
                int(touched_count),
            )
            generated += int(added_eg)
    return int(touched_count), int(generated)


@njit(cache=True, nogil=True)
def _numba_touch_region2_body_candidates(
    n: int,
    section_start: int,
    action_count: int,
    raw_fever_fill: float,
    action_k,
    use_forced_great_timing_i: int,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    real_fever_time: float,
    real_time_idx: int,
    body_values,
    body_starts,
    body_counts,
    pair_mod: int,
    pair_stamp_value: int,
    pair_stamp,
    best_fever_by_pair,
    touched_pair,
    touched_count: int,
):
    if int(use_forced_great_timing_i) == 0:
        return int(touched_count), 0
    generated = 0
    for action_idx in range(int(action_count)):
        k = int(action_k[int(action_idx)])
        offset = _numba_region2_offset_for_count(int(section_start), int(k), float(raw_fever_fill), int(n))
        if int(offset) < 0:
            continue
        run_start = int(section_start) + int(offset)
        activation, is_great = _numba_fill_crossing_run(
            int(section_start), int(run_start), int(k), float(raw_fever_fill), int(n)
        )
        if int(activation) < 0 or int(is_great) == 0:
            continue
        great_end, activation_hit = _numba_minimal_reachable_region_great_end(
            int(activation),
            int(section_start),
            int(run_start),
            float(raw_fever_fill),
            timestamps,
            perfect_floor_timestamps,
            perfect_candidate_timestamps,
            great_floor_timestamps,
            great_candidate_timestamps,
            lanes,
            int(n),
        )
        if int(great_end) < 0:
            continue
        perfect_hit, perfect_valid = _numba_perfect_activation_hit_for_run(
            int(activation),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            int(run_start),
            int(great_end) - int(run_start),
            int(n),
        )
        if int(perfect_valid) == 0:
            continue
        perfect_e = _numba_edge_end_idx_at_hit(
            int(n),
            int(activation),
            float(perfect_hit),
            float(real_fever_time),
            perfect_floor_timestamps,
        )
        activation_e = _numba_edge_end_idx_at_hit(
            int(n),
            int(activation),
            float(activation_hit),
            float(real_fever_time),
            perfect_floor_timestamps,
        )
        if int(activation_e) <= int(perfect_e):
            continue
        edge = _numba_pack_edge(
            int(n),
            int(activation),
            int(activation_e),
            int(run_start),
            int(great_end),
            int(activation),
        )
        touched_count, added = _numba_touch_body_tail_array_candidates(
            edge,
            int(activation_e),
            body_values,
            body_starts,
            body_counts,
            int(pair_mod),
            int(pair_stamp_value),
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            int(touched_count),
        )
        generated += int(added)
        eg_e = _numba_great_floor_extended_end_at_hit(
            int(n), int(activation), float(activation_hit), float(real_fever_time), great_floor_timestamps
        )
        for end_e in range(int(activation_e) + 1, int(eg_e) + 1):
            edge_eg = _numba_pack_edge_eg(
                int(n),
                int(activation),
                int(end_e),
                int(run_start),
                int(great_end),
                int(activation),
                int(activation_e),
                int(end_e),
            )
            touched_count, added_eg = _numba_touch_body_tail_array_candidates(
                edge_eg,
                int(end_e),
                body_values,
                body_starts,
                body_counts,
                int(pair_mod),
                int(pair_stamp_value),
                pair_stamp,
                best_fever_by_pair,
                touched_pair,
                int(touched_count),
            )
            generated += int(added_eg)
    return int(touched_count), int(generated)


@njit(cache=True, nogil=True)
def _numba_edge_end_idx_precomputed(
    n: int,
    activation_idx: int,
    activation_great_i: int,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    real_time_idx: int,
):
    start_time = timestamps[int(activation_idx)]
    edge_e = int(timestamp_end_idx[int(real_time_idx), int(activation_idx)])
    if int(use_forced_great_timing_i) != 0 and int(activation_great_i) != 0 and int(activation_idx) < int(n):
        activation_t = great_candidate_timestamps[int(activation_idx)]
        if activation_t > start_time:
            start_time = activation_t
            edge_e = int(great_end_idx[int(real_time_idx), int(activation_idx)])
    if int(edge_e) <= int(activation_idx):
        edge_e = int(activation_idx) + 1
    if int(edge_e) > int(n):
        edge_e = int(n)
    return edge_e, start_time


@njit(cache=True, nogil=True)
def _numba_edge_end_idx_from_tables(
    n: int,
    activation_idx: int,
    activation_great_i: int,
    use_forced_great_timing_i: int,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    real_time_idx: int,
) -> int:
    edge_e = int(perfect_end_idx[int(real_time_idx), int(activation_idx)])
    if int(use_forced_great_timing_i) != 0 and int(activation_great_i) != 0 and int(activation_idx) < int(n):
        late_e = int(great_end_idx[int(real_time_idx), int(activation_idx)])
        if int(late_e) > int(edge_e):
            edge_e = int(late_e)
    if int(edge_e) <= int(activation_idx):
        edge_e = int(activation_idx) + 1
    if int(edge_e) > int(n):
        edge_e = int(n)
    return int(edge_e)


@njit(cache=True, nogil=True)
def _numba_later_edge_from_precomputed(
    n: int,
    state_i: int,
    action_idx: int,
    later_fill,
    later_forced,
    use_forced_great_timing_i: int,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    real_time_idx: int,
) -> int:
    fill = int(later_fill[int(action_idx)])
    activation = int(state_i) + int(fill)
    if int(activation) >= int(n):
        return -1
    edge_e = _numba_edge_end_idx_from_tables(
        int(n),
        int(activation),
        0,
        int(use_forced_great_timing_i),
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        int(real_time_idx),
    )
    return int(edge_e)


@njit(cache=True, nogil=True)
def _numba_first_edge_from_precomputed(
    n: int,
    action_idx: int,
    first_fill,
    first_forced,
    use_forced_great_timing_i: int,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    real_time_idx: int,
) -> int:
    fill = int(first_fill[int(action_idx)])
    if int(fill) >= int(n):
        return -1
    edge_e = _numba_edge_end_idx_from_tables(
        int(n),
        int(fill),
        0,
        int(use_forced_great_timing_i),
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        int(real_time_idx),
    )
    return int(edge_e)


@njit(cache=True, nogil=True)
def _numba_later_activation_edge_from_precomputed(
    n: int,
    state_i: int,
    action_idx: int,
    later_fill,
    later_activation_forced,
    use_forced_great_timing_i: int,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    real_time_idx: int,
):
    prefix_forced = int(later_activation_forced[int(action_idx)])
    if int(use_forced_great_timing_i) == 0 or int(prefix_forced) < 0:
        return -1, np.int64(0)
    fill = int(later_fill[int(action_idx)])
    activation = int(state_i) + int(fill)
    if int(activation) >= int(n):
        return -1, np.int64(0)
    edge_e = _numba_edge_end_idx_from_tables(
        int(n),
        int(activation),
        1,
        int(use_forced_great_timing_i),
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        int(real_time_idx),
    )
    return int(edge_e), np.int64(prefix_forced)


@njit(cache=True, nogil=True)
def _numba_first_activation_edge_from_precomputed(
    n: int,
    action_idx: int,
    first_fill,
    first_activation_forced,
    use_forced_great_timing_i: int,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    real_time_idx: int,
):
    prefix_forced = int(first_activation_forced[int(action_idx)])
    if int(use_forced_great_timing_i) == 0 or int(prefix_forced) < 0:
        return -1, np.int64(0)
    activation = int(first_fill[int(action_idx)])
    if int(activation) >= int(n):
        return -1, np.int64(0)
    edge_e = _numba_edge_end_idx_from_tables(
        int(n),
        int(activation),
        1,
        int(use_forced_great_timing_i),
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        int(real_time_idx),
    )
    return int(edge_e), np.int64(prefix_forced)


@njit(cache=True, nogil=True)
def _numba_zero_forced_body_fever_precomputed(
    n: int,
    later_fill,
    later_forced,
    first_fill,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    use_forced_great_timing_i: int,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    real_time_idx: int,
) -> int:
    if int(first_fill[0]) < 100:
        return -1
    edge_e = _numba_first_edge_from_precomputed(
        int(n),
        0,
        first_fill,
        first_forced,
        int(use_forced_great_timing_i),
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        int(real_time_idx),
    )
    if int(edge_e) < 0:
        return -1
    total = int(_numba_body_count(int(first_fill[0]), int(edge_e), int(n)))
    state_i = int(edge_e)
    for _step in range(int(n) + 1):
        if int(state_i) >= int(n):
            return int(total)
        next_e = _numba_later_edge_from_precomputed(
            int(n),
            int(state_i),
            0,
            later_fill,
            later_forced,
            int(use_forced_great_timing_i),
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if int(next_e) < 0 or int(next_e) <= int(state_i):
            return -1
        total += int(_numba_body_count(int(state_i) + int(later_fill[0]), int(next_e), int(n)))
        state_i = int(next_e)
    return -1


@njit(cache=True, nogil=True)
def _numba_max_body_candidate(
    n: int,
    activation: int,
    edge_e: int,
    activation_great_i: int,
    great_floor_end_idx,
    real_time_idx: int,
    best,
) -> int:
    """Max body-fever contribution of `activation`, over the early-Great extended fever ends
    e in [edge_e, eg_e] (issue #44): body_count(activation, e) + best[e]. eg_e == edge_e on the
    common path, so this is just `body_count(activation, edge_e) + best[edge_e]`."""
    eg_e = _numba_great_floor_extended_end(
        int(n), int(activation), int(activation_great_i), great_floor_end_idx, int(real_time_idx)
    )
    best_cand = -1
    for e in range(int(edge_e), int(eg_e) + 1):
        cand = int(_numba_body_count(int(activation), int(e), int(n))) + int(best[int(e)])
        if int(cand) > int(best_cand):
            best_cand = int(cand)
    return int(best_cand)


@njit(cache=True, nogil=True)
def _numba_max_body_fever_precomputed(
    n: int,
    action_count: int,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    use_forced_great_timing_i: int,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    real_time_idx: int,
) -> int:
    best = np.zeros(int(n) + 1, dtype=np.int32)
    family_count, family_mode, _family_defect, family_start, family_end = _numba_build_packet_families(
        int(action_count),
        later_fill,
        later_forced,
        later_activation_forced,
    )
    deque_alpha = np.empty((int(family_count), int(n) + 1), dtype=np.int32)
    deque_value = np.empty((int(family_count), int(n) + 1), dtype=np.int32)
    deque_head = np.zeros(int(family_count), dtype=np.int32)
    deque_tail = np.zeros(int(family_count), dtype=np.int32)

    for state_i in range(int(n) - 1, -1, -1):
        best_value = 0
        for family_idx in range(int(family_count)):
            head = int(deque_head[int(family_idx)])
            tail = int(deque_tail[int(family_idx)])
            high_activation = int(state_i) + int(family_end[int(family_idx)])
            while int(head) < int(tail) and int(deque_alpha[int(family_idx), int(head)]) > int(high_activation):
                head += 1

            activation = int(state_i) + int(family_start[int(family_idx)])
            if int(activation) >= 0 and int(activation) < int(n):
                perfect_e = _numba_edge_end_idx_from_tables(
                    int(n),
                    int(activation),
                    0,
                    int(use_forced_great_timing_i),
                    timestamp_end_idx,
                    perfect_end_idx,
                    great_end_idx,
                    int(real_time_idx),
                )
                edge_e = int(perfect_e)
                if int(family_mode[int(family_idx)]) != 0:
                    late_e = _numba_edge_end_idx_from_tables(
                        int(n),
                        int(activation),
                        1,
                        int(use_forced_great_timing_i),
                        timestamp_end_idx,
                        perfect_end_idx,
                        great_end_idx,
                        int(real_time_idx),
                    )
                    if int(late_e) > int(perfect_e):
                        edge_e = int(late_e)
                    else:
                        edge_e = -1
                if int(edge_e) >= 0:
                    candidate = _numba_max_body_candidate(
                        int(n), int(activation), int(edge_e),
                        1 if int(family_mode[int(family_idx)]) != 0 else 0,
                        great_floor_end_idx, int(real_time_idx), best,
                    )
                    while int(head) < int(tail) and int(deque_value[int(family_idx), int(tail) - 1]) <= int(candidate):
                        tail -= 1
                    deque_alpha[int(family_idx), int(tail)] = int(activation)
                    deque_value[int(family_idx), int(tail)] = int(candidate)
                    tail += 1
            if int(head) < int(tail) and int(deque_value[int(family_idx), int(head)]) > int(best_value):
                best_value = int(deque_value[int(family_idx), int(head)])
            deque_head[int(family_idx)] = int(head)
            deque_tail[int(family_idx)] = int(tail)
        best[state_i] = int(best_value)

    best_first = 0
    for action_idx in range(int(action_count)):
        edge_e = _numba_first_edge_from_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if int(edge_e) >= 0:
            candidate = _numba_max_body_candidate(
                int(n), int(first_fill[int(action_idx)]), int(edge_e), 0,
                great_floor_end_idx, int(real_time_idx), best,
            )
            if int(candidate) > int(best_first):
                best_first = int(candidate)
        activation_e, _prefix_forced = _numba_first_activation_edge_from_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_activation_forced,
            int(use_forced_great_timing_i),
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
            candidate = _numba_max_body_candidate(
                int(n), int(first_fill[int(action_idx)]), int(activation_e), 1,
                great_floor_end_idx, int(real_time_idx), best,
            )
            if int(candidate) > int(best_first):
                best_first = int(candidate)
    return int(best_first)


@njit(cache=True, nogil=True)
def _numba_packet_body_tails_from_precomputed_end_indices(
    n: int,
    action_count: int,
    raw_fever_fill: float,
    action_k,
    later_fill,
    later_forced,
    later_activation_forced,
    reachable,
    use_forced_great_timing_i: int,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    real_fever_time: float,
    real_time_idx: int,
    pair_mod: int,
    best_fever_by_pair,
    pair_stamp,
    touched_pair,
    pair_stamp_value: int,
    bit_values,
    bit_stamps,
    bit_stamp_value: int,
):
    body_values = List.empty_list(_NUMBA_BODY_PAIR_TYPE)
    body_starts = np.zeros(int(n) + 1, dtype=np.int32)
    body_counts = np.zeros(int(n) + 1, dtype=np.int32)
    body_values.append((np.uint64(0), np.uint64(0), np.uint64(0)))
    _numba_store_shared_empty_body_tail(body_starts, body_counts, int(n))
    body_cursor = 1

    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0

    for state_i in range(int(n) - 1, 99, -1):
        if not reachable[int(state_i)]:
            continue

        states_evaluated += 1
        touched_count = 0
        pair_stamp_value += 1
        touched_count, generated_count = _numba_touch_prefix_body_candidates(
            int(n),
            int(state_i),
            int(action_count),
            float(raw_fever_fill),
            later_fill,
            later_forced,
            later_activation_forced,
            int(use_forced_great_timing_i),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            perfect_floor_timestamps,
            great_floor_timestamps,
            lanes,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            float(real_fever_time),
            int(real_time_idx),
            body_values,
            body_starts,
            body_counts,
            int(pair_mod),
            int(pair_stamp_value),
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            int(touched_count),
        )
        generated_surfaces += int(generated_count)

        touched_count, generated_count = _numba_touch_region2_body_candidates(
            int(n),
            int(state_i) + 1,
            int(action_count),
            float(raw_fever_fill),
            action_k,
            int(use_forced_great_timing_i),
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            perfect_floor_timestamps,
            great_floor_timestamps,
            lanes,
            float(real_fever_time),
            int(real_time_idx),
            body_values,
            body_starts,
            body_counts,
            int(pair_mod),
            int(pair_stamp_value),
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            int(touched_count),
        )
        generated_surfaces += int(generated_count)

        if int(touched_count) == 0:
            _numba_store_shared_empty_body_tail(body_starts, body_counts, int(state_i))
            frontier_len = 1
        else:
            bit_stamp_value += 1
            frontier = _numba_reduce_touched_body_pairs(
                int(pair_mod),
                touched_pair,
                int(touched_count),
                best_fever_by_pair,
                bit_values,
                bit_stamps,
                int(bit_stamp_value),
            )
            frontier_len = len(frontier)
            body_cursor = _numba_store_body_tail_frontier(
                body_values,
                body_starts,
                body_counts,
                int(state_i),
                int(body_cursor),
                frontier,
            )
        retained_total += int(frontier_len)
        if int(frontier_len) > max_state_frontier:
            max_state_frontier = int(frontier_len)

    return (
        body_values,
        body_starts,
        body_counts,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        pair_stamp_value,
        bit_stamp_value,
    )


@njit(cache=True, nogil=True)
def _first_frontier_from_precomputed_end_indices_numba(
    n: int,
    action_count: int,
    raw_fever_fill: float,
    action_k,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing_i: int,
    head_filter_min: int,
):
    if int(use_forced_great_timing_i) == 0 and int(action_count) > 0 and int(first_fill[0]) >= 100:
        zero_body_fever = _numba_zero_forced_body_fever_precomputed(
            int(n),
            later_fill,
            later_forced,
            first_fill,
            first_forced,
            later_activation_forced,
            first_activation_forced,
            int(use_forced_great_timing_i),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if int(zero_body_fever) >= 0:
            if int(zero_body_fever) >= max(0, int(n) - 100):
                return _numba_single_body_frontier_row(int(zero_body_fever)), 0, 0, 1, 1
            max_body_fever = _numba_max_body_fever_precomputed(
                int(n),
                int(action_count),
                later_fill,
                first_fill,
                later_forced,
                first_forced,
                later_activation_forced,
                first_activation_forced,
                int(use_forced_great_timing_i),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                perfect_end_idx,
                great_end_idx,
                great_floor_end_idx,
                int(real_time_idx),
            )
            if int(zero_body_fever) == int(max_body_fever):
                return _numba_single_body_frontier_row(int(zero_body_fever)), 0, 0, 1, 1

    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    # Issue #44: widest early-Great band over every enumerated activation -> sizes the body-pair radix.
    max_eg_width = 0
    for action_idx in range(int(action_count)):
        fill = int(first_fill[int(action_idx)])
        edge_hit, edge_valid = _numba_perfect_activation_hit_for_run(
            int(fill),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            0,
            int(first_forced[int(action_idx)]),
            int(n),
        )
        edge_e = -1
        if int(edge_valid) != 0:
            edge_e = _numba_edge_end_idx_at_hit(
                int(n), int(fill), float(edge_hit), float(real_fever_time), perfect_floor_timestamps
            )
        if int(edge_e) >= 0:
            reachable[int(edge_e)] = True
            max_eg_width = max(
                max_eg_width,
                _numba_mark_early_great_reachable_from_hit(
                    reachable,
                    int(n),
                    int(fill),
                    int(edge_e),
                    float(edge_hit),
                    great_floor_timestamps,
                    float(real_fever_time),
                ),
            )
        prefix_forced = int(first_activation_forced[int(action_idx)])
        activation_e = -1
        activation_hit = 0.0
        if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
            activation_hit, activation_valid = _numba_late_great_activation_hit_for_run(
                int(fill),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
                0,
                int(prefix_forced),
                int(n),
            )
            if int(activation_valid) != 0:
                activation_e = _numba_edge_end_idx_at_hit(
                    int(n), int(fill), float(activation_hit), float(real_fever_time), perfect_floor_timestamps
                )
        if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
            reachable[int(activation_e)] = True
            max_eg_width = max(
                max_eg_width,
                _numba_mark_early_great_reachable_from_hit(
                    reachable,
                    int(n),
                    int(fill),
                    int(activation_e),
                    float(activation_hit),
                    great_floor_timestamps,
                    float(real_fever_time),
                ),
            )
        if int(use_forced_great_timing_i) != 0:
            k = int(action_k[int(action_idx)])
            region_offset = _numba_region2_offset_for_count(0, int(k), float(raw_fever_fill), int(n))
            shifted_head_offset = 1 if _numba_has_shifted_head_region(0, float(raw_fever_fill)) else -1
            for offset_idx in range(2):
                if int(offset_idx) == 0:
                    offset = int(region_offset)
                else:
                    offset = int(shifted_head_offset)
                    if int(offset) == int(region_offset):
                        continue
                if int(offset) < 1:
                    continue
                max_eg_width = max(
                    int(max_eg_width),
                    _numba_mark_region_run_reachable_for_offset(
                        reachable,
                        int(n),
                        0,
                        int(offset),
                        int(k),
                        float(raw_fever_fill),
                        timestamps,
                        perfect_floor_timestamps,
                        perfect_candidate_timestamps,
                        great_floor_timestamps,
                        great_candidate_timestamps,
                        lanes,
                        float(real_fever_time),
                    ),
                )
    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        for action_idx in range(int(action_count)):
            section_start = int(state_i) + 1
            activation = int(state_i) + int(later_fill[int(action_idx)])
            edge_hit, edge_valid = _numba_perfect_activation_hit_for_run(
                int(activation),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
                int(section_start),
                int(later_forced[int(action_idx)]),
                int(n),
            )
            edge_e = -1
            if int(edge_valid) != 0:
                edge_e = _numba_edge_end_idx_at_hit(
                    int(n), int(activation), float(edge_hit), float(real_fever_time), perfect_floor_timestamps
                )
            if int(edge_e) >= 0:
                reachable[int(edge_e)] = True
                max_eg_width = max(
                    max_eg_width,
                    _numba_mark_early_great_reachable_from_hit(
                        reachable,
                        int(n),
                        int(activation),
                        int(edge_e),
                        float(edge_hit),
                        great_floor_timestamps,
                        float(real_fever_time),
                    ),
                )
            prefix_forced = int(later_activation_forced[int(action_idx)])
            activation_hit = 0.0
            activation_e = -1
            if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
                activation_hit, activation_valid = _numba_late_great_activation_hit_for_run(
                    int(activation),
                    timestamps,
                    perfect_candidate_timestamps,
                    great_candidate_timestamps,
                    int(section_start),
                    int(prefix_forced),
                    int(n),
                )
                if int(activation_valid) != 0:
                    activation_e = _numba_edge_end_idx_at_hit(
                        int(n),
                        int(activation),
                        float(activation_hit),
                        float(real_fever_time),
                        perfect_floor_timestamps,
                    )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                reachable[int(activation_e)] = True
                max_eg_width = max(
                    max_eg_width,
                    _numba_mark_early_great_reachable_from_hit(
                        reachable,
                        int(n),
                        int(activation),
                        int(activation_e),
                        float(activation_hit),
                        great_floor_timestamps,
                        float(real_fever_time),
                    ),
                )
            if int(use_forced_great_timing_i) != 0:
                k = int(action_k[int(action_idx)])
                region_offset = _numba_region2_offset_for_count(
                    int(section_start), int(k), float(raw_fever_fill), int(n)
                )
                shifted_head_offset = (
                    1 if _numba_has_shifted_head_region(int(section_start), float(raw_fever_fill)) else -1
                )
                for offset_idx in range(2):
                    if int(offset_idx) == 0:
                        offset = int(region_offset)
                    else:
                        offset = int(shifted_head_offset)
                        if int(offset) == int(region_offset):
                            continue
                    if int(offset) < 1:
                        continue
                    max_eg_width = max(
                        int(max_eg_width),
                        _numba_mark_region_run_reachable_for_offset(
                            reachable,
                            int(n),
                            int(section_start),
                            int(offset),
                            int(k),
                            float(raw_fever_fill),
                            timestamps,
                            perfect_floor_timestamps,
                            perfect_candidate_timestamps,
                            great_floor_timestamps,
                            great_candidate_timestamps,
                            lanes,
                            float(real_fever_time),
                        ),
                    )
    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0
    min_later_fill = max(1, int(later_fill[0]) if int(action_count) > 0 else 1)
    # Body-pair radix sizing. pair_idx packs (normal_great, body_fever_great) as
    # normal_great*pair_mod + body_fever_great, injective only while body_fever_great < pair_mod.
    # body_fever_great sums, per section, <=1 boundary Great plus the issue-#44 early-Great band
    # (<= max_eg_width extras), over at most `section_bound` sections -> true max is
    # section_bound*(1 + max_eg_width). Size pair_mod one past that. max_eg_width == 0 on the common
    # (no early-Great) path, collapsing this to the pre-#44 section-count bound (zero regression).
    # Capped at n+1 since body_fever_great <= body_great <= n always. (Before this fix pair_mod was
    # the bare section count, so a wide early-Great band overflowed the radix and aliased silently.)
    section_bound = int(n) // int(min_later_fill) + 4
    pair_mod = min(int(n) + 1, int(section_bound) * (1 + int(max_eg_width)) + 1)
    pair_size = (int(n) + 1) * int(pair_mod)
    best_fever_by_pair = np.zeros(int(pair_size), dtype=np.int32)
    pair_stamp = np.zeros(int(pair_size), dtype=np.int32)
    touched_pair = np.empty(int(pair_size), dtype=np.int32)
    pair_stamp_value = 0
    bit_values = np.zeros(int(pair_mod) + 1, dtype=np.int32)
    bit_stamps = np.zeros(int(pair_mod) + 1, dtype=np.int32)
    bit_stamp_value = 0

    (
        body_values,
        body_starts,
        body_counts,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        pair_stamp_value,
        bit_stamp_value,
    ) = _numba_packet_body_tails_from_precomputed_end_indices(
        int(n),
        int(action_count),
        float(raw_fever_fill),
        action_k,
        later_fill,
        later_forced,
        later_activation_forced,
        reachable,
        int(use_forced_great_timing_i),
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        perfect_floor_timestamps,
        great_floor_timestamps,
        lanes,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
        float(real_fever_time),
        int(real_time_idx),
        int(pair_mod),
        best_fever_by_pair,
        pair_stamp,
        touched_pair,
        int(pair_stamp_value),
        bit_values,
        bit_stamps,
        int(bit_stamp_value),
    )

    head_limit = min(int(n), 100)
    head_frontiers = List.empty_list(_NUMBA_SURFACE_LIST_TYPE)
    for _idx in range(head_limit):
        head_frontiers.append(List.empty_list(_NUMBA_SURFACE_TYPE))

    for state_i in range(head_limit - 1, -1, -1):
        if not reachable[state_i]:
            continue
        states_evaluated += 1
        generated = List.empty_list(_NUMBA_SURFACE_TYPE)
        generated_basis = List.empty_list(_NUMBA_HEAD_BASIS_TYPE)
        generated_count = 0
        bounded_mode = 0
        prev_fill = -1
        prev_edge_e = -1
        prev_forced_count = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        prev_activation_prefix = -1
        for action_idx in range(int(action_count)):
            fill = int(later_fill[int(action_idx)])
            forced_start = int(state_i) + 1
            activation = int(state_i) + int(fill)
            forced_count = int(later_forced[int(action_idx)])
            perfect_hit, perfect_valid = _numba_perfect_activation_hit_for_run(
                int(activation),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
                int(forced_start),
                int(forced_count),
                int(n),
            )
            if int(perfect_valid) == 0:
                edge_e = -1
            else:
                edge_e = _numba_edge_end_idx_at_hit(
                    int(n),
                    int(activation),
                    float(perfect_hit),
                    float(real_fever_time),
                    perfect_floor_timestamps,
                )
            if (
                int(edge_e) >= 0
                and (
                    int(fill) != int(prev_fill)
                    or int(edge_e) != int(prev_edge_e)
                    or int(forced_count) != int(prev_forced_count)
                )
                and _numba_activation_reachable_contiguous_run(
                    int(activation),
                    float(perfect_hit),
                    perfect_floor_timestamps,
                    perfect_candidate_timestamps,
                    great_floor_timestamps,
                    great_candidate_timestamps,
                    lanes,
                    float(raw_fever_fill),
                    int(forced_start),
                    int(n),
                    int(forced_start),
                    int(forced_count),
                    0,
                )
            ):
                prev_fill = int(fill)
                prev_edge_e = int(edge_e)
                prev_forced_count = int(forced_count)
                edge = _numba_pack_edge(
                    int(n),
                    int(activation),
                    int(edge_e),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(forced_count)),
                    -1,
                )
                generated, generated_basis, added, bounded_mode = _numba_append_head_generated_candidate(
                    generated,
                    generated_basis,
                    edge,
                    int(edge_e),
                    body_values,
                    body_starts,
                    body_counts,
                    head_frontiers,
                    int(head_limit),
                    int(state_i),
                    int(head_limit),
                    int(head_filter_min),
                    int(bounded_mode),
                )
                generated_count += int(added)
                # Issue #44: early-Great extension of the Perfect-activation fever section. Each
                # end e in (edge_e, eg_e] adds the tail [edge_e, e) as fever-greats.
                generated, generated_basis, added, bounded_mode = _numba_emit_early_great_edges(
                    generated,
                    generated_basis,
                    int(n),
                    int(activation),
                    int(edge_e),
                    float(perfect_hit),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(forced_count)),
                    -1,
                    great_floor_timestamps,
                    float(real_fever_time),
                    body_values,
                    body_starts,
                    body_counts,
                    head_frontiers,
                    int(head_limit),
                    int(state_i),
                    int(head_limit),
                    int(head_filter_min),
                    int(bounded_mode),
                )
                generated_count += int(added)
            prefix_forced = int(later_activation_forced[int(action_idx)])
            activation_hit = 0.0
            activation_e = -1
            if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
                activation_hit, activation_valid = _numba_late_great_activation_hit_for_run(
                    int(activation),
                    timestamps,
                    perfect_candidate_timestamps,
                    great_candidate_timestamps,
                    int(forced_start),
                    int(prefix_forced),
                    int(n),
                )
                if int(activation_valid) != 0:
                    activation_e = _numba_edge_end_idx_at_hit(
                        int(n),
                        int(activation),
                        float(activation_hit),
                        float(real_fever_time),
                        perfect_floor_timestamps,
                    )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                if (
                    int(fill) == int(prev_activation_fill)
                    and int(activation_e) == int(prev_activation_e)
                    and int(prefix_forced) == int(prev_activation_prefix)
                ):
                    continue
                if not _numba_activation_reachable_contiguous_run(
                    int(activation),
                    float(activation_hit),
                    perfect_floor_timestamps,
                    perfect_candidate_timestamps,
                    great_floor_timestamps,
                    great_candidate_timestamps,
                    lanes,
                    float(raw_fever_fill),
                    int(forced_start),
                    int(n),
                    int(forced_start),
                    int(prefix_forced),
                    1,
                ):
                    continue
                prev_activation_fill = int(fill)
                prev_activation_e = int(activation_e)
                prev_activation_prefix = int(prefix_forced)
                activation_edge = _numba_pack_edge(
                    int(n),
                    int(activation),
                    int(activation_e),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(prefix_forced)),
                    int(activation),
                )
                generated, generated_basis, added, bounded_mode = _numba_append_head_generated_candidate(
                    generated,
                    generated_basis,
                    activation_edge,
                    int(activation_e),
                    body_values,
                    body_starts,
                    body_counts,
                    head_frontiers,
                    int(head_limit),
                    int(state_i),
                    int(head_limit),
                    int(head_filter_min),
                    int(bounded_mode),
                )
                generated_count += int(added)
                # Issue #44: early-Great extension of the late-Great-activation fever section.
                generated, generated_basis, added, bounded_mode = _numba_emit_early_great_edges(
                    generated,
                    generated_basis,
                    int(n),
                    int(activation),
                    int(activation_e),
                    float(activation_hit),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(prefix_forced)),
                    int(activation),
                    great_floor_timestamps,
                    float(real_fever_time),
                    body_values,
                    body_starts,
                    body_counts,
                    head_frontiers,
                    int(head_limit),
                    int(state_i),
                    int(head_limit),
                    int(head_filter_min),
                    int(bounded_mode),
                )
                generated_count += int(added)
        generated, generated_basis, added, bounded_mode = _numba_emit_region2_head_edges(
            generated,
            generated_basis,
            int(n),
            int(state_i) + 1,
            int(action_count),
            float(raw_fever_fill),
            action_k,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            perfect_floor_timestamps,
            great_floor_timestamps,
            lanes,
            float(real_fever_time),
            int(real_time_idx),
            int(use_forced_great_timing_i),
            body_values,
            body_starts,
            body_counts,
            head_frontiers,
            int(head_limit),
            int(state_i),
            int(head_limit),
            int(head_filter_min),
            int(bounded_mode),
        )
        generated_count += int(added)
        generated_surfaces += generated_count
        # Issue #44 Route A: prune each head-state tail set to its parametric upper envelope
        # (positions [state_i, head_limit)) before any earlier state composes against it, so the
        # early-Great head cascade never forms the exponential product. Bit-exact under the
        # additive edge/tail decomposition; see _numba_head_envelope_filter.
        frontier = _numba_head_envelope_filter(
            _numba_reduce(generated), int(state_i), int(head_limit), int(head_filter_min)
        )
        head_frontiers[state_i] = frontier
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)

    first_generated_count = 0
    first_frontier = List.empty_list(_NUMBA_SURFACE_TYPE)
    first_region_generated = List.empty_list(_NUMBA_SURFACE_TYPE)
    first_region_basis = List.empty_list(_NUMBA_HEAD_BASIS_TYPE)
    first_region_bounded = 0
    if int(action_count) > 0 and int(first_fill[0]) >= 100:
        first_edge_e_by_action = np.empty(int(action_count), dtype=np.int32)
        first_edge_hit_by_action = np.empty(int(action_count), dtype=np.float64)
        first_normal_head_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_e_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_hit_by_action = np.empty(int(action_count), dtype=np.float64)
        first_activation_prefix_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_head_by_action = np.empty(int(action_count), dtype=np.int32)
        for action_idx in range(int(action_count)):
            fill = int(first_fill[int(action_idx)])
            forced_count = int(first_forced[int(action_idx)])
            edge_hit, edge_valid = _numba_perfect_activation_hit_for_run(
                int(fill),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
                0,
                int(forced_count),
                int(n),
            )
            edge_e = -1
            if int(edge_valid) != 0:
                edge_e = _numba_edge_end_idx_at_hit(
                    int(n),
                    int(fill),
                    float(edge_hit),
                    float(real_fever_time),
                    perfect_floor_timestamps,
                )
            first_edge_e_by_action[int(action_idx)] = int(edge_e)
            first_edge_hit_by_action[int(action_idx)] = float(edge_hit)
            first_normal_head_by_action[int(action_idx)] = min(100, max(0, int(forced_count)))
            prefix_forced = int(first_activation_forced[int(action_idx)])
            activation_hit = 0.0
            activation_e = -1
            if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
                activation_hit, activation_valid = _numba_late_great_activation_hit_for_run(
                    int(fill),
                    timestamps,
                    perfect_candidate_timestamps,
                    great_candidate_timestamps,
                    0,
                    int(prefix_forced),
                    int(n),
                )
                if int(activation_valid) != 0:
                    activation_e = _numba_edge_end_idx_at_hit(
                        int(n),
                        int(fill),
                        float(activation_hit),
                        float(real_fever_time),
                        perfect_floor_timestamps,
                    )
            first_activation_e_by_action[int(action_idx)] = int(activation_e)
            first_activation_hit_by_action[int(action_idx)] = float(activation_hit)
            first_activation_prefix_by_action[int(action_idx)] = int(prefix_forced)
            first_activation_head_by_action[int(action_idx)] = min(100, max(0, int(prefix_forced)))
        branch_a_width = int(n) + 2
        branch_a_size = (int(pair_mod) + 1) * int(branch_a_width)
        branch_a_values = np.zeros(int(branch_a_size), dtype=np.int32)
        branch_a_stamps = np.zeros(int(branch_a_size), dtype=np.int32)
        branch_a_stamp = 1
        normal_bucket_offsets = np.zeros(102, dtype=np.int32)
        activation_bucket_offsets = np.zeros(102, dtype=np.int32)
        for action_idx in range(int(action_count)):
            edge_e = int(first_edge_e_by_action[int(action_idx)])
            if int(edge_e) >= 100:
                hgc = int(first_normal_head_by_action[int(action_idx)])
                normal_bucket_offsets[int(hgc) + 1] += 1
            activation_e = int(first_activation_e_by_action[int(action_idx)])
            if int(activation_e) >= 100 and int(activation_e) > int(edge_e):
                hgc = int(first_activation_head_by_action[int(action_idx)])
                activation_bucket_offsets[int(hgc) + 1] += 1
        for head_great_count in range(101):
            normal_bucket_offsets[int(head_great_count) + 1] += normal_bucket_offsets[int(head_great_count)]
            activation_bucket_offsets[int(head_great_count) + 1] += activation_bucket_offsets[int(head_great_count)]
        normal_actions_by_head = np.empty(int(normal_bucket_offsets[101]), dtype=np.int32)
        activation_actions_by_head = np.empty(int(activation_bucket_offsets[101]), dtype=np.int32)
        normal_bucket_write = np.zeros(101, dtype=np.int32)
        activation_bucket_write = np.zeros(101, dtype=np.int32)
        for action_idx in range(int(action_count)):
            edge_e = int(first_edge_e_by_action[int(action_idx)])
            if int(edge_e) >= 100:
                hgc = int(first_normal_head_by_action[int(action_idx)])
                pos = int(normal_bucket_offsets[int(hgc)]) + int(normal_bucket_write[int(hgc)])
                normal_actions_by_head[int(pos)] = int(action_idx)
                normal_bucket_write[int(hgc)] += 1
            activation_e = int(first_activation_e_by_action[int(action_idx)])
            if int(activation_e) >= 100 and int(activation_e) > int(edge_e):
                hgc = int(first_activation_head_by_action[int(action_idx)])
                pos = int(activation_bucket_offsets[int(hgc)]) + int(activation_bucket_write[int(hgc)])
                activation_actions_by_head[int(pos)] = int(action_idx)
                activation_bucket_write[int(hgc)] += 1
        for head_great_count in range(101):
            touched_count = 0
            pair_stamp_value += 1
            prev_fill = -1
            prev_edge_e = -1
            prev_forced_count = -1
            prev_activation_fill = -1
            prev_activation_e = -1
            prev_activation_prefix = -1
            for bucket_idx in range(
                int(normal_bucket_offsets[int(head_great_count)]),
                int(normal_bucket_offsets[int(head_great_count) + 1]),
            ):
                action_idx = int(normal_actions_by_head[int(bucket_idx)])
                edge_e = int(first_edge_e_by_action[int(action_idx)])
                fill = int(first_fill[int(action_idx)])
                forced_count = int(first_forced[int(action_idx)])
                edge_hit = float(first_edge_hit_by_action[int(action_idx)])
                if (
                    int(fill) != int(prev_fill)
                    or int(edge_e) != int(prev_edge_e)
                    or int(forced_count) != int(prev_forced_count)
                ):
                    if not _numba_activation_reachable_contiguous_run(
                        int(fill),
                        float(edge_hit),
                        perfect_floor_timestamps,
                        perfect_candidate_timestamps,
                        great_floor_timestamps,
                        great_candidate_timestamps,
                        lanes,
                        float(raw_fever_fill),
                        0,
                        int(n),
                        0,
                        int(first_forced[int(action_idx)]),
                        0,
                    ):
                        continue
                    prev_fill = int(fill)
                    prev_edge_e = int(edge_e)
                    prev_forced_count = int(forced_count)
                    edge = _numba_pack_edge(
                        int(n),
                        int(fill),
                        int(edge_e),
                        0,
                        min(int(n), int(forced_count)),
                        -1,
                    )
                    touched_count, added_count = _numba_touch_body_tail_array_candidates(
                        edge,
                        int(edge_e),
                        body_values,
                        body_starts,
                        body_counts,
                        int(pair_mod),
                        int(pair_stamp_value),
                        pair_stamp,
                        best_fever_by_pair,
                        touched_pair,
                        int(touched_count),
                    )
                    first_generated_count += int(added_count)
                    # Issue #44: early-Great extension of the first Perfect-activation section.
                    # first_fill >= 100, so every extended end is in the body (head_great_count
                    # unchanged -> same bucket).
                    eg_e = _numba_great_floor_extended_end_at_hit(
                        int(n), int(fill), float(edge_hit), float(real_fever_time), great_floor_timestamps
                    )
                    for end_e in range(int(edge_e) + 1, int(eg_e) + 1):
                        edge_eg = _numba_pack_edge_eg(
                            int(n), int(fill), int(end_e), 0,
                            min(int(n), int(forced_count)), -1,
                            int(edge_e), int(end_e),
                        )
                        touched_count, added_eg = _numba_touch_body_tail_array_candidates(
                            edge_eg, int(end_e), body_values, body_starts, body_counts,
                            int(pair_mod), int(pair_stamp_value), pair_stamp,
                            best_fever_by_pair, touched_pair, int(touched_count),
                        )
                        first_generated_count += int(added_eg)
            for bucket_idx in range(
                int(activation_bucket_offsets[int(head_great_count)]),
                int(activation_bucket_offsets[int(head_great_count) + 1]),
            ):
                action_idx = int(activation_actions_by_head[int(bucket_idx)])
                edge_e = int(first_edge_e_by_action[int(action_idx)])
                activation_e = int(first_activation_e_by_action[int(action_idx)])
                fill = int(first_fill[int(action_idx)])
                prefix_forced = int(first_activation_prefix_by_action[int(action_idx)])
                activation_hit = float(first_activation_hit_by_action[int(action_idx)])
                if (
                    int(fill) == int(prev_activation_fill)
                    and int(activation_e) == int(prev_activation_e)
                    and int(prefix_forced) == int(prev_activation_prefix)
                ):
                    continue
                if not _numba_activation_reachable_contiguous_run(
                    int(fill),
                    float(activation_hit),
                    perfect_floor_timestamps,
                    perfect_candidate_timestamps,
                    great_floor_timestamps,
                    great_candidate_timestamps,
                    lanes,
                    float(raw_fever_fill),
                    0,
                    int(n),
                    0,
                    int(prefix_forced),
                    1,
                ):
                    continue
                prev_activation_fill = int(fill)
                prev_activation_e = int(activation_e)
                prev_activation_prefix = int(prefix_forced)
                activation_edge = _numba_pack_edge(
                    int(n),
                    int(fill),
                    int(activation_e),
                    0,
                    min(int(n), int(prefix_forced)),
                    int(fill),
                )
                touched_count, added_count = _numba_touch_body_tail_array_candidates(
                    activation_edge,
                    int(activation_e),
                    body_values,
                    body_starts,
                    body_counts,
                    int(pair_mod),
                    int(pair_stamp_value),
                    pair_stamp,
                    best_fever_by_pair,
                    touched_pair,
                    int(touched_count),
                )
                first_generated_count += int(added_count)
                # Issue #44: early-Great extension of the first late-Great-activation section.
                eg_e_late = _numba_great_floor_extended_end_at_hit(
                    int(n), int(fill), float(activation_hit), float(real_fever_time), great_floor_timestamps
                )
                for end_e in range(int(activation_e) + 1, int(eg_e_late) + 1):
                    activation_edge_eg = _numba_pack_edge_eg(
                        int(n), int(fill), int(end_e), 0,
                        min(int(n), int(prefix_forced)), int(fill),
                        int(activation_e), int(end_e),
                    )
                    touched_count, added_eg = _numba_touch_body_tail_array_candidates(
                        activation_edge_eg, int(end_e), body_values, body_starts, body_counts,
                        int(pair_mod), int(pair_stamp_value), pair_stamp,
                        best_fever_by_pair, touched_pair, int(touched_count),
                    )
                    first_generated_count += int(added_eg)

            if int(touched_count) <= 0:
                continue
            bit_stamp_value += 1
            body_frontier = _numba_reduce_touched_body_pairs(
                int(pair_mod),
                touched_pair,
                int(touched_count),
                best_fever_by_pair,
                bit_values,
                bit_stamps,
                int(bit_stamp_value),
            )
            for body_idx in range(len(body_frontier)):
                body_fever, body_great, body_fever_great = body_frontier[body_idx]
                _numba_append_branch_a_body_prefix_surface(
                    first_frontier,
                    int(head_great_count),
                    body_fever,
                    body_great,
                    body_fever_great,
                    branch_a_values,
                    branch_a_stamps,
                    int(branch_a_stamp),
                    int(branch_a_width),
                )
        first_region_generated, first_region_basis, added, first_region_bounded = _numba_emit_region2_head_edges(
            first_region_generated,
            first_region_basis,
            int(n),
            0,
            int(action_count),
            float(raw_fever_fill),
            action_k,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            perfect_floor_timestamps,
            great_floor_timestamps,
            lanes,
            float(real_fever_time),
            int(real_time_idx),
            int(use_forced_great_timing_i),
            body_values,
            body_starts,
            body_counts,
            head_frontiers,
            int(head_limit),
            0,
            int(head_limit),
            int(head_filter_min),
            int(first_region_bounded),
        )
        first_generated_count += int(added)
    else:
        first_generated = List.empty_list(_NUMBA_SURFACE_TYPE)
        first_generated_basis = List.empty_list(_NUMBA_HEAD_BASIS_TYPE)
        first_bounded_mode = 0
        prev_fill = -1
        prev_edge_e = -1
        prev_forced_count = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        prev_activation_prefix = -1
        for action_idx in range(int(action_count)):
            fill = int(first_fill[int(action_idx)])
            forced_count = int(first_forced[int(action_idx)])
            perfect_hit, perfect_valid = _numba_perfect_activation_hit_for_run(
                int(fill),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
                0,
                int(forced_count),
                int(n),
            )
            if int(perfect_valid) == 0:
                edge_e = -1
            else:
                edge_e = _numba_edge_end_idx_at_hit(
                    int(n),
                    int(fill),
                    float(perfect_hit),
                    float(real_fever_time),
                    perfect_floor_timestamps,
                )
            if (
                int(edge_e) >= 0
                and (
                    int(fill) != int(prev_fill)
                    or int(edge_e) != int(prev_edge_e)
                    or int(forced_count) != int(prev_forced_count)
                )
                and _numba_activation_reachable_contiguous_run(
                    int(fill),
                    float(perfect_hit),
                    perfect_floor_timestamps,
                    perfect_candidate_timestamps,
                    great_floor_timestamps,
                    great_candidate_timestamps,
                    lanes,
                    float(raw_fever_fill),
                    0,
                    int(n),
                    0,
                    int(forced_count),
                    0,
                )
            ):
                prev_fill = int(fill)
                prev_edge_e = int(edge_e)
                prev_forced_count = int(forced_count)
                edge = _numba_pack_edge(
                    int(n),
                    int(fill),
                    int(edge_e),
                    0,
                    min(int(n), int(forced_count)),
                    -1,
                )
                first_generated, first_generated_basis, added, first_bounded_mode = _numba_append_head_generated_candidate(
                    first_generated,
                    first_generated_basis,
                    edge,
                    int(edge_e),
                    body_values,
                    body_starts,
                    body_counts,
                    head_frontiers,
                    int(head_limit),
                    0,
                    int(head_limit),
                    int(head_filter_min),
                    int(first_bounded_mode),
                )
                first_generated_count += int(added)
                # Issue #44: early-Great extension (first section, head activation).
                first_generated, first_generated_basis, added, first_bounded_mode = _numba_emit_early_great_edges(
                    first_generated,
                    first_generated_basis,
                    int(n),
                    int(fill),
                    int(edge_e),
                    float(perfect_hit),
                    0,
                    min(int(n), int(forced_count)),
                    -1,
                    great_floor_timestamps,
                    float(real_fever_time),
                    body_values,
                    body_starts,
                    body_counts,
                    head_frontiers,
                    int(head_limit),
                    0,
                    int(head_limit),
                    int(head_filter_min),
                    int(first_bounded_mode),
                )
                first_generated_count += int(added)
            prefix_forced = int(first_activation_forced[int(action_idx)])
            activation_hit = 0.0
            activation_e = -1
            if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
                activation_hit, activation_valid = _numba_late_great_activation_hit_for_run(
                    int(fill),
                    timestamps,
                    perfect_candidate_timestamps,
                    great_candidate_timestamps,
                    0,
                    int(prefix_forced),
                    int(n),
                )
                if int(activation_valid) != 0:
                    activation_e = _numba_edge_end_idx_at_hit(
                        int(n),
                        int(fill),
                        float(activation_hit),
                        float(real_fever_time),
                        perfect_floor_timestamps,
                    )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                if (
                    int(fill) == int(prev_activation_fill)
                    and int(activation_e) == int(prev_activation_e)
                    and int(prefix_forced) == int(prev_activation_prefix)
                ):
                    continue
                if not _numba_activation_reachable_contiguous_run(
                    int(fill),
                    float(activation_hit),
                    perfect_floor_timestamps,
                    perfect_candidate_timestamps,
                    great_floor_timestamps,
                    great_candidate_timestamps,
                    lanes,
                    float(raw_fever_fill),
                    0,
                    int(n),
                    0,
                    int(prefix_forced),
                    1,
                ):
                    continue
                prev_activation_fill = int(fill)
                prev_activation_e = int(activation_e)
                prev_activation_prefix = int(prefix_forced)
                activation_edge = _numba_pack_edge(
                    int(n),
                    int(fill),
                    int(activation_e),
                    0,
                    min(int(n), int(prefix_forced)),
                    int(fill),
                )
                first_generated, first_generated_basis, added, first_bounded_mode = _numba_append_head_generated_candidate(
                    first_generated,
                    first_generated_basis,
                    activation_edge,
                    int(activation_e),
                    body_values,
                    body_starts,
                    body_counts,
                    head_frontiers,
                    int(head_limit),
                    0,
                    int(head_limit),
                    int(head_filter_min),
                    int(first_bounded_mode),
                )
                first_generated_count += int(added)
                # Issue #44: early-Great extension (first section, head late-Great activation).
                first_generated, first_generated_basis, added, first_bounded_mode = _numba_emit_early_great_edges(
                    first_generated,
                    first_generated_basis,
                    int(n),
                    int(fill),
                    int(activation_e),
                    float(activation_hit),
                    0,
                    min(int(n), int(prefix_forced)),
                    int(fill),
                    great_floor_timestamps,
                    float(real_fever_time),
                    body_values,
                    body_starts,
                    body_counts,
                    head_frontiers,
                    int(head_limit),
                    0,
                    int(head_limit),
                    int(head_filter_min),
                    int(first_bounded_mode),
                )
                first_generated_count += int(added)
        first_generated, first_generated_basis, added, first_bounded_mode = _numba_emit_region2_head_edges(
            first_generated,
            first_generated_basis,
            int(n),
            0,
            int(action_count),
            float(raw_fever_fill),
            action_k,
            timestamp_end_idx,
            perfect_end_idx,
            great_end_idx,
            great_floor_end_idx,
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            perfect_floor_timestamps,
            great_floor_timestamps,
            lanes,
            float(real_fever_time),
            int(real_time_idx),
            int(use_forced_great_timing_i),
            body_values,
            body_starts,
            body_counts,
            head_frontiers,
            int(head_limit),
            0,
            int(head_limit),
            int(head_filter_min),
            int(first_bounded_mode),
        )
        first_generated_count += int(added)
        # Issue #44 Route A: same upper-envelope prune for the first-frontier head-activation
        # branch (full plays from cursor 0, head positions [0, head_limit)).
        first_frontier = _numba_head_envelope_filter(
            _numba_reduce(first_generated), 0, int(head_limit), int(head_filter_min)
        )
    if len(first_region_generated) > 0:
        for idx in range(len(first_frontier)):
            first_region_generated.append(first_frontier[idx])
        first_frontier = _numba_head_envelope_filter(
            _numba_reduce(first_region_generated), 0, int(head_limit), int(head_filter_min)
        )
    generated_surfaces += first_generated_count
    retained_total += len(first_frontier)
    if len(first_frontier) > max_state_frontier:
        max_state_frontier = len(first_frontier)

    out = np.zeros((len(first_frontier), 7), dtype=np.uint64)
    for idx in range(len(first_frontier)):
        surface = first_frontier[idx]
        for col in range(7):
            out[idx, col] = surface[col]
    return out, states_evaluated, generated_surfaces, retained_total, max_state_frontier
