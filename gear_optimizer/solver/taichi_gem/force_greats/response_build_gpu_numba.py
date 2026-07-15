import numpy as np
from numba import njit, types
from numba.typed import Dict, List

_NUMBA_SURFACE_TYPE = types.UniTuple(types.uint64, 7)
_NUMBA_HEAD_OVERLAP_KEY_TYPE = types.UniTuple(types.uint64, 2)
# Full head-mask group key (fever lo/hi, great lo/hi) for the region2 same-mask pre-reduction.
_NUMBA_MASK_GROUP_KEY_TYPE = types.UniTuple(types.uint64, 4)
# Packet-point arena rows: (body_fever, shifted normal-great, fever_great) int64 triples in a
# cursor-managed flat (cap, 3) array, one arena per packet family (grow-doubling).
_NUMBA_PACKET_ARENA_TYPE = types.int64[:, ::1]
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
# Cached 16-corner score row per retained envelope surface (same floats the per-pair dominance
# checks would recompute from the basis; caching them cannot change any comparison outcome).
_NUMBA_HEAD_SCORES_TYPE = types.float64[::1]
_NUMBA_HEAD_SCORE_MATRIX_TYPE = types.float64[:, ::1]
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

# Exact producer tokens for every value that activation-hit selection can return. Each token is
# ``kind * n + note_index``; the host interns equal float64 values once per song before region-table
# construction, so table rows store compact deterministic IDs rather than repeated timestamps.
_REGION_HIT_CHART = 0
_REGION_HIT_PERFECT = 1
_EXACT_LANE_SIGNATURE_MAX_WORD_CELLS = 16_777_216
_REGION_HIT_GREAT = 2
_REGION_HIT_PERFECT_CAPPED = 3
_REGION_HIT_GREAT_CAPPED = 4

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
    hit_hi_token: int,
):
    a = int(activation_idx)
    n = min(int(section_end), int(timestamps.shape[0]))
    if int(a) < 0 or int(a) >= int(n):
        return 0.0, 0, -1
    lo = float(hit_lo)
    cap = float(hit_hi)
    cap_token = int(hit_hi_token)
    if lo > cap:
        return 0.0, 0, -1

    great_lo = max(0, min(int(great_start), int(n)))
    great_hi = min(int(n), int(great_lo) + max(0, int(great_count)))
    for j in range(int(a) + 1, int(n)):
        if float(timestamps[int(j)]) >= cap:
            break
        label_hi = great_candidate_timestamps[int(j)] if int(great_lo) <= int(j) < int(great_hi) else perfect_candidate_timestamps[int(j)]
        capped = float(label_hi) - 1.0e-6
        if capped < cap:
            cap = capped
            cap_token = (
                int(_REGION_HIT_GREAT_CAPPED) * int(timestamps.shape[0]) + int(j)
                if int(great_lo) <= int(j) < int(great_hi)
                else int(_REGION_HIT_PERFECT_CAPPED) * int(timestamps.shape[0]) + int(j)
            )
        if cap < lo:
            return 0.0, 0, -1
    return float(cap), 1, int(cap_token)


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
def _numba_late_edge_extends(
    edge_e: int,
    activation_e: int,
    activation_eg_e: int,
    edge_eg_e: int,
) -> bool:
    """Whether the late-Great activation edge carries content the Perfect edge cannot: a strictly
    longer perfect-floor extent OR, on extent ties, a strictly longer early-Great (great-floor)
    reach -- the late hit pushes the fever end further, pulling boundary notes in as fever-Greats
    the Perfect edge's window cannot reach (record 16.33: +337.5 oracle witness). When both tie,
    skipping the late edge stays lossless (its surfaces are the Perfect edge's plus a strictly
    costlier activation Great). The two early-Great (great-floor) extended ends arrive precomputed
    (clamped, `_numba_clamped_end_idx` semantics): `activation_eg_e` at the late-Great hit,
    `edge_eg_e` at the Perfect hit. They are only read when 0 <= activation_e <= edge_e -- both
    edges valid -- so callers may pass any deterministic value on the invalid paths."""
    if int(activation_e) < 0:
        return False
    if int(activation_e) > int(edge_e):
        return True
    return int(activation_eg_e) > int(edge_eg_e)


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
        return 0.0, 0, -1
    chart = float(timestamps[int(a)])
    perfect = float(perfect_candidate_timestamps[int(a)])
    lo = chart if chart < perfect else perfect
    hi = perfect if perfect > chart else chart
    hi_token = (
        int(_REGION_HIT_PERFECT) * int(timestamps.shape[0]) + int(a)
        if perfect > chart
        else int(_REGION_HIT_CHART) * int(timestamps.shape[0]) + int(a)
    )
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
        int(hi_token),
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
        return 0.0, 0, -1
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
        int(_REGION_HIT_GREAT) * int(timestamps.shape[0]) + int(a),
    )


@njit(cache=True, nogil=True)
def _numba_build_prefix_activation_hit_tables(
    n: int,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
):
    perfect_hit = np.zeros(int(n), dtype=np.float64)
    perfect_valid = np.zeros(int(n), dtype=np.int8)
    late_hit = np.zeros(int(n), dtype=np.float64)
    late_valid = np.zeros(int(n), dtype=np.int8)
    for activation in range(int(n)):
        hit, valid, _token = _numba_perfect_activation_hit_for_run(
            int(activation),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            int(activation),
            0,
            int(n),
        )
        perfect_hit[int(activation)] = float(hit)
        perfect_valid[int(activation)] = np.int8(valid)
        hit, valid, _token = _numba_late_great_activation_hit_for_run(
            int(activation),
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            int(activation),
            1,
            int(n),
        )
        late_hit[int(activation)] = float(hit)
        late_valid[int(activation)] = np.int8(valid)
    return perfect_hit, perfect_valid, late_hit, late_valid


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
def _numba_region2_offset_for_count(start: int, count: int, fever_fill_denom: float, n: int) -> int:
    if int(count) <= 0 or int(start) >= int(n):
        return -1
    denom = float(fever_fill_denom)
    # Let x = run_start - section_start and m = count. The activation is the m-th Great in
    # the run iff x + 0.5*(m-1) < denom <= x + 0.5*m. That half-open interval has width 0.5,
    # so it contains at most one integer x.
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    # At most one fill unit exists per chart row. This exact no-crossing case must return before
    # any float-to-integer conversion, including legal finite values above the int64 range.
    if float(denom) > float(n):
        return -1
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
def _numba_region2_k_scan_stop(action_count: int, fever_fill_denom: float) -> int:
    count = int(action_count)
    denom = float(fever_fill_denom)
    if count <= 0:
        return 0
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    # min(action_count, ceil(2*denom)+1) is already action_count above this threshold. Compare
    # before multiplication so a legal huge finite denominator cannot overflow to infinity.
    if denom >= 0.5 * float(count - 1):
        return int(count)
    stop = int(np.ceil(2.0 * denom)) + 1
    if int(stop) < 1:
        stop = 1
    if int(stop) > int(count):
        stop = int(count)
    return int(stop)


@njit(cache=True, nogil=True)
def _numba_exact_surface_signature_lane_prefix_reachable(
    activation_index: int,
    activation_hit_timestamp: float,
    perfect_floor_timestamps,
    perfect_candidate_timestamps,
    great_floor_timestamps,
    great_candidate_timestamps,
    lanes,
    section_start: int,
    section_end: int,
    great_start: int,
    great_end: int,
    activation_is_great: int,
    target_event_count: int,
    target_great_count: int,
) -> bool:
    """Exact exceptional-path test for one score-bearing prefix signature.

    The common producer witness is the global chart prefix and is certified without allocation by
    the caller.  When timing windows force a cross-lane swap, each lane still contributes one
    chart-order prefix.  This packed DP decides the exact pair ``(event count, Great count)``;
    full lane-ID equality owns identity and hashes are not involved.
    """
    a = int(activation_index)
    start = int(section_start)
    end = int(section_end)
    target_count = int(target_event_count)
    target_great = int(target_great_count)
    section_length = int(end) - int(start)
    if (
        target_count < 0
        or target_count > int(section_length) - 1
        or target_great < 0
        or target_great > int(target_count)
    ):
        return False
    if int(lanes.shape[0]) < int(end):
        raise ValueError("FG lane-prefix signature lanes are not aligned")

    word_count = (int(target_great) + 64) // 64
    word_cells = (int(target_count) + 1) * int(word_count)
    if int(word_cells) <= 0 or int(word_cells) > int(_EXACT_LANE_SIGNATURE_MAX_WORD_CELLS):
        raise MemoryError("FG exact lane-prefix signature DP exceeds its fail-loud capacity")
    reachable = np.zeros((int(target_count) + 1, int(word_count)), dtype=np.uint64)
    merged = np.zeros_like(reachable)
    reachable[0, 0] = np.uint64(1)

    unique_lanes = np.empty(max(1, int(section_length)), dtype=np.int64)
    unique_count = 0
    for note_idx in range(int(start), int(end)):
        lane_id = np.int64(lanes[int(note_idx)])
        found = False
        for lane_idx in range(int(unique_count)):
            if unique_lanes[int(lane_idx)] == lane_id:
                found = True
                break
        if not found:
            unique_lanes[int(unique_count)] = lane_id
            unique_count += 1

    activation_lane = np.int64(lanes[int(a)])
    prefix_greats = np.empty(int(section_length) + 1, dtype=np.int32)
    h_a = np.float32(float(activation_hit_timestamp))
    g0 = int(great_start)
    g1 = int(great_end)
    for lane_idx in range(int(unique_count)):
        lane_id = unique_lanes[int(lane_idx)]
        note_count = 0
        minimum_count = 0
        maximum_count = -1
        activation_position = -1
        head_note_count = 0
        target_head_count = 0
        lane_clock = -np.inf
        prefix_greats[0] = np.int32(0)
        for note_idx in range(int(start), int(end)):
            if np.int64(lanes[int(note_idx)]) != lane_id:
                continue
            is_great = bool(
                (int(g0) <= int(note_idx) and int(note_idx) < int(g1))
                or (int(note_idx) == int(a) and int(activation_is_great) != 0)
            )
            low = (
                great_floor_timestamps[int(note_idx)]
                if is_great
                else perfect_floor_timestamps[int(note_idx)]
            )
            high = (
                great_candidate_timestamps[int(note_idx)]
                if is_great
                else perfect_candidate_timestamps[int(note_idx)]
            )
            lane_clock = max(float(lane_clock), float(low))
            if lane_clock > float(high):
                raise ValueError("FG lane label windows cannot realize chart-order full combo")
            if high < h_a:
                minimum_count = int(note_count) + 1
            if low > h_a and int(maximum_count) < 0:
                maximum_count = int(note_count)
            if int(note_idx) == int(a):
                activation_position = int(note_count)
            if int(note_idx) < 100:
                head_note_count += 1
                if int(note_idx) < int(a):
                    target_head_count += 1
            prefix_greats[int(note_count) + 1] = np.int32(
                int(prefix_greats[int(note_count)]) + int(is_great)
            )
            note_count += 1
        if int(maximum_count) < 0:
            maximum_count = int(note_count)
        if int(minimum_count) > int(maximum_count):
            return False

        option_start = int(minimum_count)
        option_end = int(maximum_count)
        if lane_id == activation_lane:
            if int(activation_position) < 0:
                raise ValueError("FG activation note is absent from its exact lane")
            if not (
                int(minimum_count) <= int(activation_position) <= int(maximum_count)
            ):
                return False
            option_start = int(activation_position)
            option_end = int(activation_position)
        if int(target_head_count) < int(head_note_count):
            option_start = max(int(option_start), int(target_head_count))
            option_end = min(int(option_end), int(target_head_count))
        else:
            option_start = max(int(option_start), int(target_head_count))
        if int(option_start) > int(option_end):
            return False

        for count_idx in range(int(target_count) + 1):
            for word_idx in range(int(word_count)):
                merged[int(count_idx), int(word_idx)] = np.uint64(0)
        for option_count in range(int(option_start), int(option_end) + 1):
            option_great = int(prefix_greats[int(option_count)])
            if int(option_count) > int(target_count) or int(option_great) > int(target_great):
                continue
            word_shift = int(option_great) // 64
            bit_shift = int(option_great) % 64
            for prior_count in range(int(target_count) - int(option_count) + 1):
                output_count = int(prior_count) + int(option_count)
                for source_word in range(int(word_count)):
                    bits = reachable[int(prior_count), int(source_word)]
                    if bits == np.uint64(0):
                        continue
                    output_word = int(source_word) + int(word_shift)
                    if int(output_word) < int(word_count):
                        merged[int(output_count), int(output_word)] |= np.uint64(
                            bits << np.uint64(bit_shift)
                        )
                    if int(bit_shift) != 0 and int(output_word) + 1 < int(word_count):
                        merged[int(output_count), int(output_word) + 1] |= np.uint64(
                            bits >> np.uint64(64 - int(bit_shift))
                        )
        temporary = reachable
        reachable = merged
        merged = temporary

    target_word = int(target_great) // 64
    target_bit = int(target_great) % 64
    return bool(
        reachable[int(target_count), int(target_word)]
        & (np.uint64(1) << np.uint64(target_bit))
    )


@njit(cache=True, nogil=True)
def _numba_activation_reachable_contiguous_run(
    activation_index: int,
    activation_hit_timestamp: float,
    timestamps,
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
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    total = int(perfect_candidate_timestamps.shape[0])
    if int(end) > int(total):
        return False
    if (
        int(timestamps.shape[0]) < int(total)
        or int(perfect_floor_timestamps.shape[0]) < int(total)
        or int(great_floor_timestamps.shape[0]) < int(total)
        or int(great_candidate_timestamps.shape[0]) < int(total)
        or int(lanes.shape[0]) < int(total)
    ):
        raise ValueError("FG activation reachability timing arrays are not aligned")
    # Every row contributes at most one fill unit, including the activation.
    if float(denom) > float(int(end) - int(start)):
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
    activation_is_great = int(activation_great_i) != 0 or (int(g0) <= int(a) and int(a) < int(g1))
    activation_low = (
        great_floor_timestamps[int(a)]
        if activation_is_great
        else perfect_floor_timestamps[int(a)]
    )
    activation_high = (
        great_candidate_timestamps[int(a)]
        if activation_is_great
        else perfect_candidate_timestamps[int(a)]
    )
    if h_a < activation_low or h_a > activation_high:
        return False

    # The producer's common witness consumes [section_start, activation) before activation. That
    # exact chart prefix is an O(1) certificate for the score-bearing signature. If its timing is
    # illegal, the exceptional DP below may replace body identities only; head identities remain
    # position-exact and body event/Great counts remain identical to the cached surface.
    preactivation_count = int(a) - int(start)
    great_before = max(
        0,
        min(int(a), int(g1)) - max(int(start), int(g0)),
    )
    preactivation_half = 2 * int(preactivation_count) - int(great_before)
    activation_half = 1 if activation_is_great else 2
    fill_before = 0.5 * float(preactivation_half)
    if not (fill_before < denom and denom <= fill_before + 0.5 * float(activation_half)):
        return False

    # Both floor streams are monotone prefix maxima.  Check the last row of each constant-label
    # segment: that is necessary and sufficient for every chart-prefix event to have a legal hit no
    # later than h_a.
    chart_prefix_legal = True
    perfect_before_end = min(int(a), int(g0))
    if int(perfect_before_end) > int(start) and perfect_floor_timestamps[int(perfect_before_end) - 1] > h_a:
        chart_prefix_legal = False
    great_before_start = max(int(start), int(g0))
    great_before_end = min(int(a), int(g1))
    if int(great_before_end) > int(great_before_start) and great_floor_timestamps[int(great_before_end) - 1] > h_a:
        chart_prefix_legal = False
    perfect_after_run_start = max(int(start), int(g1))
    if int(a) > int(perfect_after_run_start) and perfect_floor_timestamps[int(a) - 1] > h_a:
        chart_prefix_legal = False

    # Every remaining chart-order event must stay at/after the activation.  Candidate highs are
    # per-note (held-tail aware), so inspect only later notes whose chart timestamp is still before
    # h_a; once chart >= h_a, the canonical judgment windows guarantee high >= chart >= h_a.
    for j in range(int(a) + 1, int(end)):
        if timestamps[int(j)] >= h_a:
            break
        is_great = int(g0) <= int(j) and int(j) < int(g1)
        label_high = (
            great_candidate_timestamps[int(j)]
            if is_great
            else perfect_candidate_timestamps[int(j)]
        )
        if label_high < h_a:
            chart_prefix_legal = False
            break
    if bool(chart_prefix_legal):
        return True

    return bool(
        _numba_exact_surface_signature_lane_prefix_reachable(
            int(a),
            float(h_a),
            perfect_floor_timestamps,
            perfect_candidate_timestamps,
            great_floor_timestamps,
            great_candidate_timestamps,
            lanes,
            int(start),
            int(end),
            int(g0),
            int(g1),
            int(activation_is_great),
            int(preactivation_count),
            int(great_before),
        )
    )


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
):
    a = int(activation)
    hit_hi = great_candidate_timestamps[a]
    max_great_end = int(a) + 1
    while int(max_great_end) < int(n) and perfect_candidate_timestamps[int(max_great_end)] < hit_hi:
        max_great_end += 1
    for great_end in range(int(a) + 1, int(max_great_end) + 1):
        hit, valid, hit_token = _numba_late_great_activation_hit_for_run(
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
            timestamps,
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
            return int(great_end), int(hit_token)
    return -1, -1


@njit(cache=True, nogil=True)
def _numba_has_shifted_head_region(section_start: int, raw_fever_fill: float) -> int:
    if int(section_start) >= 99:
        return 0
    return 1 if int(np.ceil(float(raw_fever_fill))) > 1 else 0


@njit(cache=True, nogil=True)
def _numba_region_core_candidate_capacity(
    n: int,
    region_action_count: int,
    action_k,
    raw_fever_fill: float,
) -> int:
    """Exact count of offsets that can reach the expensive region-core producer.

    This is an allocation bound only: validity still belongs exclusively to
    ``_numba_region_run_core_for_offset``. Counting repeats the cheap offset arithmetic but never
    reconstructs semantics, and the fill pass retains the canonical section/action/offset order.
    """
    region_k_stop = _numba_region2_k_scan_stop(int(region_action_count), float(raw_fever_fill))
    denom = float(raw_fever_fill)
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("raw_fever_fill must be finite and > 0")
    if denom > float(n):
        return 0
    shifted_sections = 0
    if int(np.ceil(float(raw_fever_fill))) > 1:
        shifted_sections = min(99, int(n) + 1)
    # Every action owns the shifted-head offset in the first 99 sections. A region-2 offset is
    # independent of section_start until its final chart-boundary cutoff, so each action's count
    # is one interval length. If that offset is also 1, subtract the overlapping shifted rows.
    candidate_count = int(shifted_sections) * int(region_action_count)
    for action_idx in range(int(region_k_stop)):
        k = int(action_k[int(action_idx)])
        region_offset = _numba_region2_offset_for_count(
            0, int(k), float(raw_fever_fill), int(n)
        )
        if int(region_offset) < 1:
            continue
        section_count = max(0, int(n) - int(region_offset) - int(k) + 1)
        candidate_count += int(section_count)
        if int(region_offset) == 1:
            candidate_count -= min(int(shifted_sections), int(section_count))
    maximum = (int(n) + 1) * max(1, int(region_action_count)) * 2
    if int(candidate_count) > int(maximum):
        raise ValueError("FG region-core candidate capacity exceeds its exhaustive bound")
    return int(candidate_count)


@njit(cache=True, nogil=True, inline="always")
def _numba_region_run_core_for_offset(
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
):
    """The rt-independent core of a region-run candidate: fill crossing, minimal reachable region
    Great end, capped activation/perfect hits, and the weighted lane-aware reachability check.
    Depends on the geometry only through the fever-fill denom (never real_fever_time), so results
    are shareable across every geometry of one (raw_fever_fill, non_fever_base) group.

    Returns ``(activation, great_end, is_great, perfect_valid, activation_hit_token,
    perfect_hit_token, valid)``. Tokens are selected alongside the exact producer hit and resolve
    to that value through the song-owned intern table."""
    run_start = int(section_start) + int(offset)
    activation, is_great = _numba_fill_crossing_run(
        int(section_start), int(run_start), int(k), float(raw_fever_fill), int(n)
    )
    if int(activation) < 0:
        return -1, -1, 0, 0, -1, -1, 0

    if int(is_great) != 0:
        great_end, activation_hit_token = _numba_minimal_reachable_region_great_end(
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
            return -1, -1, 0, 0, -1, -1, 0
        perfect_hit, perfect_valid, perfect_hit_token = (
            _numba_perfect_activation_hit_for_run(
                int(activation),
                timestamps,
                perfect_candidate_timestamps,
                great_candidate_timestamps,
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
    perfect_hit, perfect_valid, perfect_hit_token = _numba_perfect_activation_hit_for_run(
        int(activation),
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        int(run_start),
        int(great_end) - int(run_start),
        int(n),
    )
    if int(perfect_valid) == 0:
        return -1, -1, 0, 0, -1, -1, 0
    if not _numba_activation_reachable_contiguous_run(
        int(activation),
        float(perfect_hit),
        timestamps,
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


@njit(cache=True, nogil=True, inline="always")
def _numba_region_run_edge_from_core(
    n: int,
    section_start: int,
    offset: int,
    core_activation: int,
    core_great_end: int,
    core_is_great: int,
    core_activation_hit_id: int,
    core_perfect_hit_id: int,
    core_perfect_valid: int,
    core_valid: int,
    perfect_end_by_hit,
    great_end_by_hit,
):
    """The rt-dependent finish over precomputed endpoints for interned producer hit values."""
    if int(core_valid) == 0:
        return -1, -1, -1, -1, -1, -1, 0
    if int(core_is_great) == 0 or int(core_perfect_valid) != 0:
        if (
            int(core_perfect_hit_id) < 0
            or int(core_perfect_hit_id) >= int(perfect_end_by_hit.shape[0])
            or int(core_perfect_hit_id) >= int(great_end_by_hit.shape[0])
        ):
            raise ValueError("FG region Perfect-hit ID escaped its endpoint table")
    run_start = int(section_start) + int(offset)
    if int(core_is_great) != 0:
        perfect_e = -1
        perfect_eg_e = -1
        if int(core_perfect_valid) != 0:
            perfect_e = _numba_clamped_end_idx(
                int(n), int(core_activation), int(perfect_end_by_hit[int(core_perfect_hit_id)])
            )
            perfect_eg_e = _numba_clamped_end_idx(
                int(n), int(core_activation), int(great_end_by_hit[int(core_perfect_hit_id)])
            )
        if (
            int(core_activation_hit_id) < 0
            or int(core_activation_hit_id) >= int(perfect_end_by_hit.shape[0])
            or int(core_activation_hit_id) >= int(great_end_by_hit.shape[0])
        ):
            raise ValueError("FG region activation-hit ID escaped its endpoint table")
        activation_e = _numba_clamped_end_idx(
            int(n), int(core_activation), int(perfect_end_by_hit[int(core_activation_hit_id)])
        )
        activation_eg_e = _numba_clamped_end_idx(
            int(n), int(core_activation), int(great_end_by_hit[int(core_activation_hit_id)])
        )
        if int(perfect_e) >= 0 and not _numba_late_edge_extends(
            int(perfect_e),
            int(activation_e),
            int(activation_eg_e),
            int(perfect_eg_e),
        ):
            return -1, -1, -1, -1, -1, -1, 0
        return (
            int(core_activation),
            int(activation_e),
            int(run_start),
            int(core_great_end),
            int(core_activation),
            int(activation_eg_e),
            1,
        )
    edge_e = _numba_clamped_end_idx(
        int(n), int(core_activation), int(perfect_end_by_hit[int(core_perfect_hit_id)])
    )
    edge_eg_e = _numba_clamped_end_idx(
        int(n), int(core_activation), int(great_end_by_hit[int(core_perfect_hit_id)])
    )
    return (
        int(core_activation),
        int(edge_e),
        int(run_start),
        int(core_great_end),
        -1,
        int(edge_eg_e),
        1,
    )


@njit(cache=True, nogil=True)
def _numba_region_run_edge_for_offset(
    n: int,
    section_start: int,
    offset: int,
    k: int,
    raw_fever_fill: float,
    timestamps,
    candidate_high_delta_max,
    perfect_floor_timestamps,
    perfect_candidate_timestamps,
    great_floor_timestamps,
    great_candidate_timestamps,
    lanes,
    hit_token_to_id,
    perfect_end_by_hit,
    great_end_by_hit,
):
    (
        activation,
        great_end,
        is_great,
        perfect_valid,
        activation_hit_token,
        perfect_hit_token,
        valid,
    ) = (
        _numba_region_run_core_for_offset(
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
        )
    )
    if int(activation_hit_token) >= int(hit_token_to_id.shape[0]):
        raise ValueError("FG region activation-hit token escaped its song universe")
    if int(perfect_hit_token) >= int(hit_token_to_id.shape[0]):
        raise ValueError("FG region Perfect-hit token escaped its song universe")
    activation_hit_id = (
        int(hit_token_to_id[int(activation_hit_token)])
        if int(activation_hit_token) >= 0
        else -1
    )
    perfect_hit_id = (
        int(hit_token_to_id[int(perfect_hit_token)]) if int(perfect_hit_token) >= 0 else -1
    )
    return _numba_region_run_edge_from_core(
        int(n),
        int(section_start),
        int(offset),
        int(activation),
        int(great_end),
        int(is_great),
        int(activation_hit_id),
        int(perfect_hit_id),
        int(perfect_valid),
        int(valid),
        perfect_end_by_hit,
        great_end_by_hit,
    )


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
def _numba_build_region_core_table(
    n: int,
    region_action_count: int,
    action_k,
    raw_fever_fill: float,
    timestamps,
    candidate_high_delta_max,
    perfect_floor_timestamps,
    perfect_candidate_timestamps,
    great_floor_timestamps,
    great_candidate_timestamps,
    lanes,
    hit_token_to_id,
):
    """Per-denom CSR table of VALID region-run cores.

    The region-run core (fill crossing, minimal reachable region Great end, capped hits, weighted
    lane-aware reachability) depends on the geometry only through the fever-fill denom, never
    real_fever_time — so it is computed ONCE per (raw_fever_fill, non_fever_base) action-key group
    and shared read-only across every rt variant of that group (~115x reuse on a full stat grid).

    Entries for each ``section_start`` row are stored in EXACTLY the enumeration order of the
    per-geometry loops they replace — ``(action_idx asc, offset_kind asc)`` with the same
    region-2 / shifted-head gating — so the rt consumers (reachability prepass marking and the
    order-sensitive same-end head-edge bucket prune) see an identical candidate stream.

    Returns ``(starts, offsets, activations, great_ends, is_greats, act_hit_ids,
    perfect_hit_ids, perfect_valids)`` with ``starts`` of length ``n + 2``. Hit IDs resolve
    through the song-owned exact value universe and remove repeated float64 timestamps from every
    table row."""
    if int(lanes.shape[0]) != int(n):
        raise ValueError("FG region-core lane rows must match n")
    denom = float(raw_fever_fill)
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("raw_fever_fill must be finite and > 0")
    if denom > float(n):
        return (
            np.zeros(int(n) + 2, dtype=np.int64),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
        )
    cap = _numba_region_core_candidate_capacity(
        int(n), int(region_action_count), action_k, float(raw_fever_fill)
    )
    starts = np.zeros(int(n) + 2, dtype=np.int64)
    e_offset = np.empty(int(cap), dtype=np.int32)
    e_activation = np.empty(int(cap), dtype=np.int32)
    e_great_end = np.empty(int(cap), dtype=np.int32)
    e_is_great = np.empty(int(cap), dtype=np.int32)
    e_act_hit_id = np.empty(int(cap), dtype=np.int32)
    e_perfect_hit_id = np.empty(int(cap), dtype=np.int32)
    e_perfect_valid = np.empty(int(cap), dtype=np.int32)
    region_k_stop = _numba_region2_k_scan_stop(int(region_action_count), float(raw_fever_fill))
    cursor = 0
    for section_start in range(0, int(n) + 1):
        starts[int(section_start)] = int(cursor)
        shifted_head_offset = (
            1 if _numba_has_shifted_head_region(int(section_start), float(raw_fever_fill)) else -1
        )
        for action_idx in range(int(region_action_count)):
            k = int(action_k[int(action_idx)])
            region_offset = -1
            if int(action_idx) < int(region_k_stop):
                region_offset = _numba_region2_offset_for_count(
                    int(section_start), int(k), float(raw_fever_fill), int(n)
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
                (
                    activation,
                    great_end,
                    is_great,
                    perfect_valid,
                    act_hit_token,
                    perfect_hit_token,
                    valid,
                ) = (
                    _numba_region_run_core_for_offset(
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
                    )
                )
                if int(valid) == 0:
                    continue
                if int(cursor) >= int(cap):
                    raise ValueError("FG region-core rows exceed the producer-owned candidate capacity")
                if int(is_great) != 0 and (
                    int(act_hit_token) < 0 or int(act_hit_token) >= int(hit_token_to_id.shape[0])
                ):
                    raise ValueError("FG region activation-hit token escaped the song universe")
                if int(perfect_valid) != 0 and (
                    int(perfect_hit_token) < 0
                    or int(perfect_hit_token) >= int(hit_token_to_id.shape[0])
                ):
                    raise ValueError("FG region Perfect-hit token escaped the song universe")
                e_offset[int(cursor)] = int(offset)
                e_activation[int(cursor)] = int(activation)
                e_great_end[int(cursor)] = int(great_end)
                e_is_great[int(cursor)] = int(is_great)
                e_act_hit_id[int(cursor)] = (
                    int(hit_token_to_id[int(act_hit_token)]) if int(is_great) != 0 else -1
                )
                e_perfect_hit_id[int(cursor)] = (
                    int(hit_token_to_id[int(perfect_hit_token)]) if int(perfect_valid) != 0 else -1
                )
                e_perfect_valid[int(cursor)] = int(perfect_valid)
                cursor += 1
    starts[int(n) + 1] = int(cursor)
    return (
        starts,
        e_offset[: int(cursor)].copy(),
        e_activation[: int(cursor)].copy(),
        e_great_end[: int(cursor)].copy(),
        e_is_great[: int(cursor)].copy(),
        e_act_hit_id[: int(cursor)].copy(),
        e_perfect_hit_id[: int(cursor)].copy(),
        e_perfect_valid[: int(cursor)].copy(),
    )


@njit(cache=True, nogil=True)
def _numba_mark_region_entries_for_section(
    reachable,
    n: int,
    section_start: int,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hit_ids,
    region_perfect_hit_ids,
    region_perfect_valids,
    region_perfect_end_by_hit,
    region_great_end_by_hit,
) -> int:
    """rt-finish + reachability marking for every valid region core of one section row. Returns
    the max early-Great extension width, exactly like the per-candidate marking it replaces."""
    max_width = 0
    for idx in range(int(region_starts[int(section_start)]), int(region_starts[int(section_start) + 1])):
        _activation, edge_e, _run_start, _great_end, _activation_great_idx, eg_e, valid = (
            _numba_region_run_edge_from_core(
                int(n),
                int(section_start),
                int(region_offsets[int(idx)]),
                int(region_activations[int(idx)]),
                int(region_great_ends[int(idx)]),
                int(region_is_greats[int(idx)]),
                int(region_act_hit_ids[int(idx)]),
                int(region_perfect_hit_ids[int(idx)]),
                int(region_perfect_valids[int(idx)]),
                1,
                region_perfect_end_by_hit,
                region_great_end_by_hit,
            )
        )
        if int(valid) == 0:
            continue
        for end_e in range(int(edge_e), int(eg_e) + 1):
            reachable[int(end_e)] = True
        width = max(0, int(eg_e) - int(edge_e))
        if int(width) > int(max_width):
            max_width = int(width)
    return int(max_width)


@njit(cache=True, nogil=True, inline="always")
def _numba_successor_find(successor, successor_stamps, successor_epoch: int, index: int) -> int:
    """Return the first live index at/after ``index`` in one stamped successor epoch."""
    root = int(index)
    while int(successor_stamps[int(root)]) == int(successor_epoch):
        root = int(successor[int(root)])
    cursor = int(index)
    while int(successor_stamps[int(cursor)]) == int(successor_epoch):
        next_cursor = int(successor[int(cursor)])
        successor[int(cursor)] = int(root)
        cursor = int(next_cursor)
    return int(root)


@njit(cache=True, nogil=True, inline="always")
def _numba_successor_remove(
    successor,
    successor_stamps,
    successor_epoch: int,
    index: int,
) -> int:
    """Remove one live index and return its next live successor."""
    next_index = _numba_successor_find(
        successor,
        successor_stamps,
        int(successor_epoch),
        int(index) + 1,
    )
    successor[int(index)] = int(next_index)
    successor_stamps[int(index)] = int(successor_epoch)
    return int(next_index)


@njit(cache=True, nogil=True, inline="always")
def _numba_base_perfect_end_is_reachable(
    n: int,
    band_lo: int,
    end_e: int,
    perfect_floor_timestamps,
) -> bool:
    """Whether ``end_e`` is a distinct left-search exit inside a Perfect-hit band."""
    if int(end_e) == int(band_lo) or int(end_e) >= int(n):
        return True
    return float(perfect_floor_timestamps[int(end_e) - 1]) < float(
        perfect_floor_timestamps[int(end_e)]
    )


@njit(cache=True, nogil=True, inline="always")
def _numba_base_perfect_end_band_lo(
    n: int,
    activation: int,
    real_fever_time: float,
    perfect_floor_timestamps,
) -> int:
    end_e = _numba_lower_bound_from(
        perfect_floor_timestamps,
        float(perfect_floor_timestamps[int(activation)]) + float(real_fever_time),
    )
    if int(end_e) <= int(activation):
        end_e = int(activation) + 1
    if int(end_e) > int(n):
        end_e = int(n)
    return int(end_e)


@njit(cache=True, nogil=True, inline="always")
def _numba_mark_perfect_activation_closure(
    reachable,
    n: int,
    activation: int,
    real_time_idx: int,
    use_forced_great_timing_i: int,
    prefix_perfect_hit,
    prefix_perfect_valid,
    capped_perfect_edge_e,
    perfect_floor_timestamps,
    great_floor_timestamps,
    real_fever_time: float,
) -> int:
    if int(prefix_perfect_valid[int(activation)]) == 0:
        return 0
    edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
    if int(edge_e) < 0:
        return 0
    if int(use_forced_great_timing_i) == 0:
        band_lo = _numba_base_perfect_end_band_lo(
            int(n),
            int(activation),
            float(real_fever_time),
            perfect_floor_timestamps,
        )
        for end_e in range(int(band_lo), int(edge_e) + 1):
            if _numba_base_perfect_end_is_reachable(
                int(n), int(band_lo), int(end_e), perfect_floor_timestamps
            ):
                reachable[int(end_e)] = True
        return 0
    reachable[int(edge_e)] = True
    return _numba_mark_early_great_reachable_from_hit(
        reachable,
        int(n),
        int(activation),
        int(edge_e),
        float(prefix_perfect_hit[int(activation)]),
        great_floor_timestamps,
        float(real_fever_time),
    )


@njit(cache=True, nogil=True, inline="always")
def _numba_mark_late_activation_closure(
    reachable,
    n: int,
    activation: int,
    real_time_idx: int,
    prefix_perfect_valid,
    prefix_late_hit,
    prefix_late_valid,
    capped_perfect_edge_e,
    capped_late_edge_e,
    capped_eg_perfect_e,
    capped_eg_late_e,
    great_floor_timestamps,
    real_fever_time: float,
) -> int:
    edge_e = -1
    edge_eg_e = 0
    if int(prefix_perfect_valid[int(activation)]) != 0:
        edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
        edge_eg_e = int(capped_eg_perfect_e[int(real_time_idx), int(activation)])
    activation_e = -1
    activation_eg_e = 0
    if int(prefix_late_valid[int(activation)]) != 0:
        activation_e = int(capped_late_edge_e[int(real_time_idx), int(activation)])
        activation_eg_e = int(capped_eg_late_e[int(real_time_idx), int(activation)])
    if not _numba_late_edge_extends(
        int(edge_e), int(activation_e), int(activation_eg_e), int(edge_eg_e)
    ):
        return 0
    reachable[int(activation_e)] = True
    return _numba_mark_early_great_reachable_from_hit(
        reachable,
        int(n),
        int(activation),
        int(activation_e),
        float(prefix_late_hit[int(activation)]),
        great_floor_timestamps,
        float(real_fever_time),
    )


@njit(cache=True, nogil=True)
def _numba_first_frontier_reachability_prepass(
    n: int,
    action_count: int,
    later_fill,
    first_fill,
    later_activation_forced,
    first_activation_forced,
    perfect_run_starts,
    perfect_run_ends,
    late_run_starts,
    late_run_ends,
    prefix_perfect_hit,
    prefix_perfect_valid,
    prefix_late_hit,
    prefix_late_valid,
    capped_perfect_edge_e,
    capped_late_edge_e,
    capped_eg_perfect_e,
    capped_eg_late_e,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing_i: int,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hit_ids,
    region_perfect_hit_ids,
    region_perfect_valids,
    region_perfect_end_by_hit,
    region_great_end_by_hit,
    perfect_floor_timestamps,
    great_floor_timestamps,
    perfect_successor,
    perfect_successor_stamps,
    late_successor,
    late_successor_stamps,
    successor_epoch: int,
):
    """Build the exact reachable-state closure with interval successor traversal.

    The former nested scan probed every action for every reachable state even after an absolute
    activation had already been evaluated. Exact fill runs turn each state's action set into
    activation intervals; disjoint-set successors skip globally processed activations. Perfect and
    late-Great closures remain separate because only some action routes permit a late activation.
    """
    if int(n) < 0 or int(action_count) < 0:
        raise ValueError("FG reachability dimensions must be nonnegative")
    if int(first_fill.shape[0]) < int(action_count):
        raise ValueError("FG first-fill offsets are shorter than action_count")
    if int(first_activation_forced.shape[0]) < int(action_count):
        raise ValueError("FG first activation-forced rows are shorter than action_count")
    if int(perfect_run_starts.shape[0]) != int(perfect_run_ends.shape[0]):
        raise ValueError("FG Perfect fill-run arrays must align")
    if int(late_run_starts.shape[0]) != int(late_run_ends.shape[0]):
        raise ValueError("FG late-Great fill-run arrays must align")
    previous_end = -2
    for run_idx in range(int(perfect_run_starts.shape[0])):
        run_start = int(perfect_run_starts[int(run_idx)])
        run_end = int(perfect_run_ends[int(run_idx)])
        if int(run_start) < 0 or int(run_end) < int(run_start) or int(run_start) <= int(previous_end):
            raise ValueError("FG Perfect fill runs must be nonnegative, ordered, and disjoint")
        previous_end = int(run_end)
    previous_end = -2
    for run_idx in range(int(late_run_starts.shape[0])):
        run_start = int(late_run_starts[int(run_idx)])
        run_end = int(late_run_ends[int(run_idx)])
        if int(run_start) < 0 or int(run_end) < int(run_start) or int(run_start) <= int(previous_end):
            raise ValueError("FG late-Great fill runs must be nonnegative, ordered, and disjoint")
        previous_end = int(run_end)
    if int(successor_epoch) < 1:
        raise ValueError("FG successor epoch must be positive")
    if (
        int(perfect_successor.shape[0]) < int(n) + 1
        or int(perfect_successor_stamps.shape[0]) < int(n) + 1
        or int(late_successor.shape[0]) < int(n) + 1
        or int(late_successor_stamps.shape[0]) < int(n) + 1
    ):
        raise ValueError("FG successor workspace is shorter than n + 1")

    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True

    # First-section actions retain their original producer order. Removing an activation from its
    # successor set is exactly the former processed-bit write, with the same Perfect/late split.
    max_eg_width = 0
    for action_idx in range(int(action_count)):
        fill = int(first_fill[int(action_idx)])
        if int(fill) < 0:
            raise ValueError("FG first-fill offsets must be nonnegative")
        if int(fill) >= int(n):
            continue
        if int(
            _numba_successor_find(
                perfect_successor,
                perfect_successor_stamps,
                int(successor_epoch),
                int(fill),
            )
        ) == int(fill):
            width = _numba_mark_perfect_activation_closure(
                reachable,
                int(n),
                int(fill),
                int(real_time_idx),
                int(use_forced_great_timing_i),
                prefix_perfect_hit,
                prefix_perfect_valid,
                capped_perfect_edge_e,
                perfect_floor_timestamps,
                great_floor_timestamps,
                float(real_fever_time),
            )
            _numba_successor_remove(
                perfect_successor,
                perfect_successor_stamps,
                int(successor_epoch),
                int(fill),
            )
            if int(width) > int(max_eg_width):
                max_eg_width = int(width)
        if (
            int(use_forced_great_timing_i) != 0
            and int(first_activation_forced[int(action_idx)]) >= 0
            and int(
                _numba_successor_find(
                    late_successor,
                    late_successor_stamps,
                    int(successor_epoch),
                    int(fill),
                )
            )
            == int(fill)
        ):
            width = _numba_mark_late_activation_closure(
                reachable,
                int(n),
                int(fill),
                int(real_time_idx),
                prefix_perfect_valid,
                prefix_late_hit,
                prefix_late_valid,
                capped_perfect_edge_e,
                capped_late_edge_e,
                capped_eg_perfect_e,
                capped_eg_late_e,
                great_floor_timestamps,
                float(real_fever_time),
            )
            _numba_successor_remove(
                late_successor,
                late_successor_stamps,
                int(successor_epoch),
                int(fill),
            )
            if int(width) > int(max_eg_width):
                max_eg_width = int(width)

    if int(use_forced_great_timing_i) != 0:
        max_eg_width = max(
            int(max_eg_width),
            _numba_mark_region_entries_for_section(
                reachable,
                int(n),
                0,
                region_starts,
                region_offsets,
                region_activations,
                region_great_ends,
                region_is_greats,
                region_act_hit_ids,
                region_perfect_hit_ids,
                region_perfect_valids,
                region_perfect_end_by_hit,
                region_great_end_by_hit,
            ),
        )

    for state_i in range(int(n)):
        if not reachable[int(state_i)]:
            continue

        for run_idx in range(int(perfect_run_starts.shape[0])):
            interval_start = int(state_i) + int(perfect_run_starts[int(run_idx)])
            if int(interval_start) >= int(n):
                continue
            interval_end = min(
                int(n) - 1,
                int(state_i) + int(perfect_run_ends[int(run_idx)]),
            )
            activation = _numba_successor_find(
                perfect_successor,
                perfect_successor_stamps,
                int(successor_epoch),
                int(interval_start),
            )
            while int(activation) <= int(interval_end):
                width = _numba_mark_perfect_activation_closure(
                    reachable,
                    int(n),
                    int(activation),
                    int(real_time_idx),
                    int(use_forced_great_timing_i),
                    prefix_perfect_hit,
                    prefix_perfect_valid,
                    capped_perfect_edge_e,
                    perfect_floor_timestamps,
                    great_floor_timestamps,
                    float(real_fever_time),
                )
                activation = _numba_successor_remove(
                    perfect_successor,
                    perfect_successor_stamps,
                    int(successor_epoch),
                    int(activation),
                )
                if int(width) > int(max_eg_width):
                    max_eg_width = int(width)

        if int(use_forced_great_timing_i) != 0:
            for run_idx in range(int(late_run_starts.shape[0])):
                interval_start = int(state_i) + int(late_run_starts[int(run_idx)])
                if int(interval_start) >= int(n):
                    continue
                interval_end = min(
                    int(n) - 1,
                    int(state_i) + int(late_run_ends[int(run_idx)]),
                )
                activation = _numba_successor_find(
                    late_successor,
                    late_successor_stamps,
                    int(successor_epoch),
                    int(interval_start),
                )
                while int(activation) <= int(interval_end):
                    width = _numba_mark_late_activation_closure(
                        reachable,
                        int(n),
                        int(activation),
                        int(real_time_idx),
                        prefix_perfect_valid,
                        prefix_late_hit,
                        prefix_late_valid,
                        capped_perfect_edge_e,
                        capped_late_edge_e,
                        capped_eg_perfect_e,
                        capped_eg_late_e,
                        great_floor_timestamps,
                        float(real_fever_time),
                    )
                    activation = _numba_successor_remove(
                        late_successor,
                        late_successor_stamps,
                        int(successor_epoch),
                        int(activation),
                    )
                    if int(width) > int(max_eg_width):
                        max_eg_width = int(width)

            max_eg_width = max(
                int(max_eg_width),
                _numba_mark_region_entries_for_section(
                    reachable,
                    int(n),
                    int(state_i) + 1,
                    region_starts,
                    region_offsets,
                    region_activations,
                    region_great_ends,
                    region_is_greats,
                    region_act_hit_ids,
                    region_perfect_hit_ids,
                    region_perfect_valids,
                    region_perfect_end_by_hit,
                    region_great_end_by_hit,
                ),
            )
    return reachable, int(max_eg_width)


@njit(cache=True, nogil=True)
def _numba_append_edge_tail(
    generated,
    edge,
    end_e: int,
    body_values,
    body_starts,
    body_counts,
    head_pool,
    head_state_start,
    head_state_count,
    head_limit: int,
) -> int:
    """Append `edge` joined with the tail frontier at state `end_e`, dispatching to the body /
    terminal / head-frontier tail exactly like the inline Perfect-edge append. Used for the
    issue-#44 early-Great extended edges (which can land in any of the three regions). Head-state
    tail frontiers live in the flat (cap, 7) uint64 `head_pool` arena addressed by the
    head_state_start/head_state_count CSR (rows stored in retained-frontier order)."""
    if int(end_e) >= 100:
        return _numba_append_body_tail_array_surfaces(
            generated, edge, body_values, body_starts, body_counts, int(end_e)
        )
    elif int(end_e) >= int(head_limit):
        return _numba_append_terminal_tail_surface(generated, edge)
    return _numba_append_surface_tail_surfaces(
        generated,
        edge,
        head_pool,
        int(head_state_start[int(end_e)]),
        int(head_state_count[int(end_e)]),
    )


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
        # Phase 1: dominated by a currently-kept surface in the same class?
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
        # Phase 2: retire currently-kept surfaces in the same class that this one dominates.
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
def _numba_reduce_pattern_runs(surfaces):
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
    if n > 2_147_483_647:
        raise OverflowError("pattern-run reducer row count exceeds int32 index capacity")
    # Exact head-pattern-run index for the structural Pareto maximum. Dominance requires equal
    # fever/Great overlap, a fever-mask superset, and a Great-mask subset. Grouping live rows by
    # their complete four-word head pattern lets each run test those cheap mask conditions once,
    # then every row in the run scans body triples only in the cached compatible-run lists. The old
    # reducer repeated the same four mask tests for every historical row and candidate.
    #
    # Rows are still processed in producer order. Each per-run list contains only currently
    # live rows; retirement unlinks in place, while kept_flag restores the identical final producer
    # order. A pattern that recurs after another run simply owns another exact run node; no hash,
    # global interning, or equality shortcut participates in semantics.
    overlap_head = Dict.empty(_NUMBA_HEAD_OVERLAP_KEY_TYPE, types.int64)
    pattern_representative = List.empty_list(types.int64)
    previous_pattern = List.empty_list(types.int64)
    pattern_row_head = List.empty_list(types.int64)
    kept_flag = np.zeros(n, dtype=np.bool_)
    # Live-row scans consume only these three body coordinates. Project them once into contiguous
    # columns instead of repeatedly loading a seven-word typed-list tuple and recomputing normal
    # Great. Links and transient run IDs are checked int32 row indices, halving their footprint.
    previous_live = np.full(n, -1, dtype=np.int32)
    body_fever = np.empty(n, dtype=np.uint64)
    body_normal_great = np.empty(n, dtype=np.uint64)
    body_fever_great = np.empty(n, dtype=np.uint64)
    dominator_runs = np.empty(n, dtype=np.int32)
    dominated_runs = np.empty(n, dtype=np.int32)
    dominator_run_count = 0
    dominated_run_count = 0
    candidate_pattern = -1
    for idx in range(n):
        cf_lo, cf_hi, cg_lo, cg_hi, cbf, cbg, cbfg = surfaces[int(idx)]
        cng = cbg - cbfg
        body_fever[int(idx)] = cbf
        body_normal_great[int(idx)] = cng
        body_fever_great[int(idx)] = cbfg
        overlap_key = (cf_lo & cg_lo, cf_hi & cg_hi)
        if int(candidate_pattern) < 0:
            starts_new_run = True
        else:
            current_pattern = surfaces[int(pattern_representative[int(candidate_pattern)])]
            starts_new_run = (
                cf_lo != current_pattern[0]
                or cf_hi != current_pattern[1]
                or cg_lo != current_pattern[2]
                or cg_hi != current_pattern[3]
            )
        if starts_new_run:
            candidate_pattern = len(pattern_representative)
            pattern_representative.append(int(idx))
            previous_pattern.append(
                int(overlap_head[overlap_key]) if overlap_key in overlap_head else -1
            )
            pattern_row_head.append(-1)
            overlap_head[overlap_key] = int(candidate_pattern)

            # Mask compatibility is invariant across this complete contiguous run. Cache the two
            # exact relation lists once here instead of repeating four word tests for every body
            # row. Both arrays have the producer-owned row count as an exact capacity bound.
            dominator_run_count = 0
            dominated_run_count = 0
            pid = int(candidate_pattern)
            while int(pid) >= 0:
                representative = surfaces[int(pattern_representative[int(pid)])]
                if (
                    (cf_lo & ~representative[0]) == 0
                    and (cf_hi & ~representative[1]) == 0
                    and (representative[2] & ~cg_lo) == 0
                    and (representative[3] & ~cg_hi) == 0
                ):
                    dominator_runs[int(dominator_run_count)] = int(pid)
                    dominator_run_count += 1
                if (
                    (representative[0] & ~cf_lo) == 0
                    and (representative[1] & ~cf_hi) == 0
                    and (cg_lo & ~representative[2]) == 0
                    and (cg_hi & ~representative[3]) == 0
                ):
                    dominated_runs[int(dominated_run_count)] = int(pid)
                    dominated_run_count += 1
                pid = int(previous_pattern[int(pid)])

        # Phase 1: does any mask-compatible live pattern contain a body dominator?
        dominated = False
        for run_idx in range(int(dominator_run_count)):
            pid = int(dominator_runs[int(run_idx)])
            pos = int(pattern_row_head[int(pid)])
            while int(pos) >= 0:
                if (
                    body_fever[int(pos)] >= cbf
                    and body_normal_great[int(pos)] <= cng
                    and body_fever_great[int(pos)] <= cbfg
                ):
                    dominated = True
                    break
                pos = int(previous_live[int(pos)])
            if dominated:
                break
        if dominated:
            continue

        # Phase 2: unlink every body row this candidate dominates from compatible patterns.
        for run_idx in range(int(dominated_run_count)):
            pid = int(dominated_runs[int(run_idx)])
            pos = int(pattern_row_head[int(pid)])
            previous = -1
            while int(pos) >= 0:
                next_pos = int(previous_live[int(pos)])
                if (
                    cbf >= body_fever[int(pos)]
                    and cng <= body_normal_great[int(pos)]
                    and cbfg <= body_fever_great[int(pos)]
                ):
                    kept_flag[int(pos)] = False
                    if int(previous) < 0:
                        pattern_row_head[int(pid)] = int(next_pos)
                    else:
                        previous_live[int(previous)] = int(next_pos)
                else:
                    previous = int(pos)
                pos = int(next_pos)

        previous_live[int(idx)] = int(pattern_row_head[int(candidate_pattern)])
        pattern_row_head[int(candidate_pattern)] = int(idx)
        kept_flag[int(idx)] = True
    for idx in range(n):
        if kept_flag[idx]:
            kept.append(surfaces[idx])
    return kept


@njit(cache=True, nogil=True)
def _numba_surface_structurally_dominates(left, right) -> bool:
    lf_lo, lf_hi, lg_lo, lg_hi, lbf, lbg, lbfg = left
    rf_lo, rf_hi, rg_lo, rg_hi, rbf, rbg, rbfg = right
    if (lf_lo & lg_lo) != (rf_lo & rg_lo) or (lf_hi & lg_hi) != (rf_hi & rg_hi):
        return False
    lng = lbg - lbfg
    rng = rbg - rbfg
    return (
        lbf >= rbf
        and lng <= rng
        and lbfg <= rbfg
        and (rf_lo & ~lf_lo) == 0
        and (rf_hi & ~lf_hi) == 0
        and (lg_lo & ~rg_lo) == 0
        and (lg_hi & ~rg_hi) == 0
    )


@njit(cache=True, nogil=True)
def _numba_i64_ensure(values, used: int, extra: int):
    """Grow-doubling reservation on a flat 1-D int64 store (chain next-pointers). Entries
    [0, used) are live and preserved verbatim."""
    need = int(used) + int(extra)
    cap = int(values.shape[0])
    if need <= cap:
        return values
    new_cap = int(cap)
    while new_cap < need:
        new_cap *= 2
    grown = np.empty(int(new_cap), dtype=np.int64)
    grown[: int(used)] = values[: int(used)]
    return grown


@njit(cache=True, nogil=True)
def _numba_node_surface_tuple(node_surface, pos: int):
    return (
        node_surface[int(pos), 0],
        node_surface[int(pos), 1],
        node_surface[int(pos), 2],
        node_surface[int(pos), 3],
        node_surface[int(pos), 4],
        node_surface[int(pos), 5],
        node_surface[int(pos), 6],
    )


@njit(cache=True, nogil=True)
def _numba_append_same_end_head_edge_to_chain(
    node_surface, node_next, node_cursor: int, bucket_head, bucket_tail, end_e: int, edge
):
    """Lossless pre-tail prune inside one `end_e` bucket, on the reusable chained node store.

    Replaces the retired per-call typed Dict of per-end typed Lists: a bucket is a singly linked
    chain of rows in the (cap, 7) uint64 `node_surface` arena. Chain order is insertion order
    with dominated entries unlinked in place -- exactly the retired List's order under its
    scan/pop(idx)/append protocol, so the ORDER-SENSITIVE same-end prune sees an identical
    candidate sequence and retains an identical bucket sequence."""
    # phase 1: dominated by a retained entry? (chain order = retained insertion order)
    pos = int(bucket_head[int(end_e)])
    while pos != -1:
        if _numba_surface_structurally_dominates(_numba_node_surface_tuple(node_surface, pos), edge):
            return node_surface, node_next, int(node_cursor), 0
        pos = int(node_next[pos])
    # phase 2: unlink retained entries this edge dominates (order-preserving)
    prev = -1
    pos = int(bucket_head[int(end_e)])
    while pos != -1:
        nxt = int(node_next[pos])
        if _numba_surface_structurally_dominates(edge, _numba_node_surface_tuple(node_surface, pos)):
            if prev == -1:
                bucket_head[int(end_e)] = nxt
            else:
                node_next[int(prev)] = nxt
            if nxt == -1:
                bucket_tail[int(end_e)] = prev
        else:
            prev = pos
        pos = nxt
    # phase 3: append at the tail
    node_surface = _numba_u64_rows_ensure(node_surface, int(node_cursor), 1)
    node_next = _numba_i64_ensure(node_next, int(node_cursor), 1)
    node_surface[int(node_cursor), 0] = edge[0]
    node_surface[int(node_cursor), 1] = edge[1]
    node_surface[int(node_cursor), 2] = edge[2]
    node_surface[int(node_cursor), 3] = edge[3]
    node_surface[int(node_cursor), 4] = edge[4]
    node_surface[int(node_cursor), 5] = edge[5]
    node_surface[int(node_cursor), 6] = edge[6]
    node_next[int(node_cursor)] = -1
    tail = int(bucket_tail[int(end_e)])
    if tail == -1:
        bucket_head[int(end_e)] = int(node_cursor)
    else:
        node_next[int(tail)] = int(node_cursor)
    bucket_tail[int(end_e)] = int(node_cursor)
    return node_surface, node_next, int(node_cursor) + 1, 1


@njit(cache=True, nogil=True)
def _numba_append_head_edge_to_end_chains(
    node_surface,
    node_next,
    node_cursor: int,
    bucket_head,
    bucket_tail,
    pending_ends,
    pending_count: int,
    edge,
    end_e: int,
):
    """First touch of an end registers it in `pending_ends` (first-seen order, the retired
    pending_edge_ends List); a bucket never empties once created (a dominating edge always
    appends itself), so head == -1 exactly means untouched this call."""
    if int(bucket_head[int(end_e)]) == -1:
        pending_ends[int(pending_count)] = int(end_e)
        pending_count = int(pending_count) + 1
    node_surface, node_next, node_cursor, kept = _numba_append_same_end_head_edge_to_chain(
        node_surface, node_next, int(node_cursor), bucket_head, bucket_tail, int(end_e), edge
    )
    return node_surface, node_next, int(node_cursor), int(pending_count), int(kept)


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
def _numba_append_body_tail_array_surfaces(generated, edge, body_values, body_starts, body_counts, state: int) -> int:
    count = int(body_counts[int(state)])
    start = int(body_starts[int(state)])
    for tail_idx in range(count):
        value_idx = int(start) + int(tail_idx)
        tail_fever = body_values[int(value_idx), 0]
        tail_great = body_values[int(value_idx), 1]
        tail_fever_great = body_values[int(value_idx), 2]
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
def _numba_append_surface_tail_surfaces(generated, edge, head_pool, tail_start: int, tail_count: int) -> int:
    count = 0
    for tail_idx in range(int(tail_count)):
        row = int(tail_start) + int(tail_idx)
        tail = (
            head_pool[row, 0],
            head_pool[row, 1],
            head_pool[row, 2],
            head_pool[row, 3],
            head_pool[row, 4],
            head_pool[row, 5],
            head_pool[row, 6],
        )
        generated.append(_numba_combine(edge, tail))
        count += 1
    return count


@njit(cache=True, nogil=True)
def _numba_emit_early_great_edges(
    generated,
    generated_scores,
    generated_seen,
    generated_score_matrix_holder,
    generated_score_matrix_count,
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
    head_pool,
    head_state_start,
    head_state_count,
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
        generated, generated_scores, edge_added, bounded_mode = (
            _numba_append_head_generated_candidate(
                generated,
                generated_scores,
                generated_seen,
                generated_score_matrix_holder,
                generated_score_matrix_count,
                edge_eg,
                int(end_e),
                body_values,
                body_starts,
                body_counts,
                head_pool,
                head_state_start,
                head_state_count,
                int(head_limit),
                int(lo_pos),
                int(hi_pos),
                int(min_surfaces),
                int(bounded_mode),
            )
        )
        added += int(edge_added)
    return generated, generated_scores, int(added), int(bounded_mode)


@njit(cache=True, nogil=True)
def _numba_collect_early_great_head_edges(
    node_surface,
    node_next,
    node_cursor: int,
    bucket_head,
    bucket_tail,
    pending_ends,
    pending_count: int,
    n: int,
    fill_pos: int,
    base_e: int,
    extended_e: int,
    great_start: int,
    great_end: int,
    activation_great_idx: int,
):
    added = 0
    for end_e in range(int(base_e) + 1, int(extended_e) + 1):
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
        node_surface, node_next, node_cursor, pending_count, kept = (
            _numba_append_head_edge_to_end_chains(
                node_surface,
                node_next,
                int(node_cursor),
                bucket_head,
                bucket_tail,
                pending_ends,
                int(pending_count),
                edge_eg,
                int(end_e),
            )
        )
        added += int(kept)
    return node_surface, node_next, int(node_cursor), int(pending_count), int(added)


@njit(cache=True, nogil=True)
def _numba_same_mask_prereduce_push(
    cand_rows,
    cand_prev,
    cand_kept,
    cand_cursor: int,
    mask_head,
    c0,
    c1,
    c2,
    c3,
    c4,
    c5,
    c6,
):
    """Online same-mask weak count-dominance reduce over composed region2 candidates.

    This is `_numba_reduce`'s dominance RESTRICTED to rows with identical fever and great
    masks, where its mask-subset conditions are trivially true and the head-overlap bucket
    key is equal: weak (body_fever >=, normal_great <=, fever_great <=). Two phases in
    `_numba_reduce`'s order -- a candidate weakly dominated by a kept same-mask row is
    dropped BEFORE it can retire anything (so exact duplicates keep the first occurrence),
    otherwise it retires every kept same-mask row it weakly dominates and is stored.
    Removals are therefore a subset of the removals the downstream `_numba_reduce` performs
    on the same stream, survivors keep arrival order, and dominance is transitive -- the
    final reduce+envelope output over the surviving stream is unchanged. Groups chain
    through `cand_prev` from `mask_head`; retired rows keep their chain slot with
    cand_kept 0, exactly like `_numba_reduce`'s kept_flag."""
    key = (c0, c1, c2, c3)
    cng = c5 - c6
    head = mask_head[key] if key in mask_head else np.int64(-1)
    pos = int(head)
    while pos != -1:
        if int(cand_kept[pos]) != 0:
            kbf = cand_rows[pos, 4]
            kng = cand_rows[pos, 5] - cand_rows[pos, 6]
            kbfg = cand_rows[pos, 6]
            if kbf >= c4 and kng <= cng and kbfg <= c6:
                return cand_rows, cand_prev, cand_kept, int(cand_cursor)
        pos = int(cand_prev[pos])
    pos = int(head)
    while pos != -1:
        if int(cand_kept[pos]) != 0:
            kbf = cand_rows[pos, 4]
            kng = cand_rows[pos, 5] - cand_rows[pos, 6]
            kbfg = cand_rows[pos, 6]
            if c4 >= kbf and cng <= kng and c6 <= kbfg:
                cand_kept[pos] = 0
        pos = int(cand_prev[pos])
    cand_rows = _numba_u64_rows_ensure(cand_rows, int(cand_cursor), 1)
    cand_prev = _numba_i64_ensure(cand_prev, int(cand_cursor), 1)
    cand_kept = _numba_i64_ensure(cand_kept, int(cand_cursor), 1)
    cand_rows[int(cand_cursor), 0] = c0
    cand_rows[int(cand_cursor), 1] = c1
    cand_rows[int(cand_cursor), 2] = c2
    cand_rows[int(cand_cursor), 3] = c3
    cand_rows[int(cand_cursor), 4] = c4
    cand_rows[int(cand_cursor), 5] = c5
    cand_rows[int(cand_cursor), 6] = c6
    cand_prev[int(cand_cursor)] = int(head)
    cand_kept[int(cand_cursor)] = 1
    mask_head[key] = np.int64(int(cand_cursor))
    return cand_rows, cand_prev, cand_kept, int(cand_cursor) + 1


@njit(cache=True, nogil=True)
def _numba_prereduce_edge_tails(
    cand_rows,
    cand_prev,
    cand_kept,
    cand_cursor: int,
    mask_head,
    edge,
    end_e: int,
    body_values,
    body_starts,
    body_counts,
    head_pool,
    head_state_start,
    head_state_count,
    head_limit: int,
):
    """Dispatch twin of `_numba_append_edge_tail` feeding the same-mask pre-reducer: the
    body / terminal / head-frontier tail composition and enumeration order are identical,
    only the destination differs. Body tails keep the edge's masks verbatim; head-frontier
    tails combine masks via `_numba_combine` exactly like the append path. Returns the
    (possibly regrown) reducer state plus the RAW candidate count (dropped candidates
    included), preserving the caller's generated-surfaces accounting."""
    raw = 0
    if int(end_e) >= 100:
        count = int(body_counts[int(end_e)])
        start = int(body_starts[int(end_e)])
        for tail_idx in range(count):
            value_idx = int(start) + int(tail_idx)
            cand_rows, cand_prev, cand_kept, cand_cursor = _numba_same_mask_prereduce_push(
                cand_rows,
                cand_prev,
                cand_kept,
                int(cand_cursor),
                mask_head,
                edge[0],
                edge[1],
                edge[2],
                edge[3],
                edge[4] + body_values[value_idx, 0],
                edge[5] + body_values[value_idx, 1],
                edge[6] + body_values[value_idx, 2],
            )
            raw += 1
    elif int(end_e) >= int(head_limit):
        cand_rows, cand_prev, cand_kept, cand_cursor = _numba_same_mask_prereduce_push(
            cand_rows,
            cand_prev,
            cand_kept,
            int(cand_cursor),
            mask_head,
            edge[0],
            edge[1],
            edge[2],
            edge[3],
            edge[4],
            edge[5],
            edge[6],
        )
        raw = 1
    else:
        tail_start = int(head_state_start[int(end_e)])
        tail_count = int(head_state_count[int(end_e)])
        for tail_idx in range(int(tail_count)):
            row = int(tail_start) + int(tail_idx)
            combined = _numba_combine(
                edge,
                (
                    head_pool[row, 0],
                    head_pool[row, 1],
                    head_pool[row, 2],
                    head_pool[row, 3],
                    head_pool[row, 4],
                    head_pool[row, 5],
                    head_pool[row, 6],
                ),
            )
            cand_rows, cand_prev, cand_kept, cand_cursor = _numba_same_mask_prereduce_push(
                cand_rows,
                cand_prev,
                cand_kept,
                int(cand_cursor),
                mask_head,
                combined[0],
                combined[1],
                combined[2],
                combined[3],
                combined[4],
                combined[5],
                combined[6],
            )
            raw += 1
    return cand_rows, cand_prev, cand_kept, int(cand_cursor), int(raw)


@njit(cache=True, nogil=True)
def _numba_emit_region2_head_edges(
    generated,
    generated_scores,
    generated_seen,
    generated_score_matrix_holder,
    generated_score_matrix_count,
    node_surface,
    node_next,
    bucket_head,
    bucket_tail,
    pending_ends,
    n: int,
    section_start: int,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hit_ids,
    region_perfect_hit_ids,
    region_perfect_valids,
    region_perfect_end_by_hit,
    region_great_end_by_hit,
    use_forced_great_timing_i: int,
    body_values,
    body_starts,
    body_counts,
    head_pool,
    head_state_start,
    head_state_count,
    head_limit: int,
    lo_pos: int,
    hi_pos: int,
    min_surfaces: int,
    bounded_mode: int,
):
    # Candidates come from the per-denom region core table (rt-free work computed once per
    # action-key group); only the rt-dependent finish runs here. Entry order per section row is
    # the exact (action_idx, offset_kind) enumeration order the table build replicated, so the
    # order-sensitive same-end bucket prune below sees an identical candidate stream. The
    # shifted-head earliest-representative rule and region-2 offset gating are applied at build.
    # Buckets live in the caller's reusable chained node store (see
    # _numba_append_same_end_head_edge_to_chain); node rows are call-local (cursor restarts at
    # 0), and the drain below resets every touched end's head/tail to -1, so the tables come
    # back clean for the next call without an O(n) sweep.
    if int(use_forced_great_timing_i) == 0:
        return generated, generated_scores, 0, int(bounded_mode), node_surface, node_next
    added_total = 0
    node_cursor = 0
    pending_count = 0
    for entry_idx in range(int(region_starts[int(section_start)]), int(region_starts[int(section_start) + 1])):
        activation, edge_e, run_start, great_end, activation_great_idx, eg_e, valid = (
            _numba_region_run_edge_from_core(
                int(n),
                int(section_start),
                int(region_offsets[int(entry_idx)]),
                int(region_activations[int(entry_idx)]),
                int(region_great_ends[int(entry_idx)]),
                int(region_is_greats[int(entry_idx)]),
                int(region_act_hit_ids[int(entry_idx)]),
                int(region_perfect_hit_ids[int(entry_idx)]),
                int(region_perfect_valids[int(entry_idx)]),
                1,
                region_perfect_end_by_hit,
                region_great_end_by_hit,
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
        node_surface, node_next, node_cursor, pending_count, _kept = (
            _numba_append_head_edge_to_end_chains(
                node_surface,
                node_next,
                int(node_cursor),
                bucket_head,
                bucket_tail,
                pending_ends,
                int(pending_count),
                edge,
                int(edge_e),
            )
        )
        node_surface, node_next, node_cursor, pending_count, _kept_eg = (
            _numba_collect_early_great_head_edges(
                node_surface,
                node_next,
                int(node_cursor),
                bucket_head,
                bucket_tail,
                pending_ends,
                int(pending_count),
                int(n),
                int(activation),
                int(edge_e),
                int(eg_e),
                int(run_start),
                int(great_end),
                int(activation_great_idx),
            )
        )
    if int(pending_count) == 0:
        return generated, generated_scores, 0, int(bounded_mode), node_surface, node_next
    # Same-mask pre-reduction is exact only while the canonical path is still accumulating
    # rows for its first `_numba_reduce`. Once promotion enters the order-sensitive cone
    # inserter, even a structurally dominated row can affect which harmless extra witnesses
    # survive. Preserve the old per-edge promotion schedule: pre-reduce the unbounded prefix,
    # force the same first promotion after the same raw batch crosses the threshold, then feed
    # every later row through the unchanged bounded inserter in producer order.
    cand_rows = np.empty((256, 7), dtype=np.uint64)
    cand_prev = np.empty(256, dtype=np.int64)
    cand_kept = np.empty(256, dtype=np.int64)
    cand_cursor = 0
    mask_head = Dict.empty(_NUMBA_MASK_GROUP_KEY_TYPE, types.int64)
    raw_unbounded_len = len(generated)
    prereduced_rows_flushed = 0
    promotion_threshold = int(_numba_head_generated_threshold(int(min_surfaces)))
    for pending_end_idx in range(int(pending_count)):
        end_e = int(pending_ends[int(pending_end_idx)])
        pos = int(bucket_head[int(end_e)])
        while pos != -1:
            edge = _numba_node_surface_tuple(node_surface, pos)
            if int(bounded_mode) != 0:
                generated, generated_scores, raw_added, bounded_mode = (
                    _numba_append_head_generated_candidate(
                        generated,
                        generated_scores,
                        generated_seen,
                        generated_score_matrix_holder,
                        generated_score_matrix_count,
                        edge,
                        int(end_e),
                        body_values,
                        body_starts,
                        body_counts,
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        int(lo_pos),
                        int(hi_pos),
                        int(min_surfaces),
                        int(bounded_mode),
                    )
                )
            else:
                cand_rows, cand_prev, cand_kept, cand_cursor, raw_added = (
                    _numba_prereduce_edge_tails(
                        cand_rows,
                        cand_prev,
                        cand_kept,
                        int(cand_cursor),
                        mask_head,
                        edge,
                        int(end_e),
                        body_values,
                        body_starts,
                        body_counts,
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                    )
                )
                raw_unbounded_len += int(raw_added)
                if int(raw_unbounded_len) > int(promotion_threshold):
                    for cand_idx in range(int(cand_cursor)):
                        if int(cand_kept[int(cand_idx)]) != 0:
                            generated.append(
                                (
                                    cand_rows[int(cand_idx), 0],
                                    cand_rows[int(cand_idx), 1],
                                    cand_rows[int(cand_idx), 2],
                                    cand_rows[int(cand_idx), 3],
                                    cand_rows[int(cand_idx), 4],
                                    cand_rows[int(cand_idx), 5],
                                    cand_rows[int(cand_idx), 6],
                                )
                            )
                    generated, generated_scores = _numba_promote_head_generated_with_scores(
                        generated,
                        int(lo_pos),
                        int(hi_pos),
                        int(min_surfaces),
                    )
                    bounded_mode = 1
                    prereduced_rows_flushed = 1
            added_total += int(raw_added)
            pos = int(node_next[pos])
        bucket_head[int(end_e)] = -1
        bucket_tail[int(end_e)] = -1
    if int(prereduced_rows_flushed) == 0:
        for cand_idx in range(int(cand_cursor)):
            if int(cand_kept[int(cand_idx)]) != 0:
                generated.append(
                    (
                        cand_rows[int(cand_idx), 0],
                        cand_rows[int(cand_idx), 1],
                        cand_rows[int(cand_idx), 2],
                        cand_rows[int(cand_idx), 3],
                        cand_rows[int(cand_idx), 4],
                        cand_rows[int(cand_idx), 5],
                        cand_rows[int(cand_idx), 6],
                    )
                )
    return generated, generated_scores, int(added_total), int(bounded_mode), node_surface, node_next


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


# Issue #44 body-tail hull: the Pareto reduce and the per-normal-Great upper-hull filter are fused
# into `_numba_reduce_touched_body_pairs` (allocation-free, byte-identical output); see its
# docstring for the exactness and ordering proof.


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
def _numba_head_surface_margin(left, right) -> float:
    """Value-identical twin of `_numba_head_basis_margin` reading the ORIGINAL surface rows.

    The margin consumes only the basis fields copied/derived verbatim from the surface: masks
    [0..3] are carried unchanged by `_numba_head_surface_basis`, and the three body fields are
    int64(bf), int64(bg) - int64(bfg), int64(bfg). Counts are tiny (< total_notes), so the int64
    arithmetic below reproduces the basis-tuple arithmetic exactly and the integer sum converts
    to the identical float. Build-path margins therefore need no retained basis list; the basis
    twin stays for the serve-time session prune, whose rows only exist in basis form."""
    bw = _HEAD_DOM_BODY_FLOOR_W
    return float(
        _numba_popcount64((left[0] ^ right[0]) | (left[2] ^ right[2]))
        + _numba_popcount64((left[1] ^ right[1]) | (left[3] ^ right[3]))
        + bw
        * (
            abs(int(np.int64(left[4]) - np.int64(right[4])))
            + abs(
                int(
                    (np.int64(left[5]) - np.int64(left[6]))
                    - (np.int64(right[5]) - np.int64(right[6]))
                )
            )
            + abs(int(np.int64(left[6]) - np.int64(right[6])))
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
def _numba_head_basis_corner_scores_row(basis, row) -> None:
    col = 0
    for iv in range(2):
        v = _HEAD_DOM_V[iv]
        for ic in range(2):
            c = _HEAD_DOM_C[ic]
            for iff in range(2):
                f = _HEAD_DOM_F[iff]
                for ig in range(2):
                    g = _HEAD_DOM_G[ig]
                    row[int(col)] = _numba_head_basis_corner_score(
                        basis, float(v), float(c), float(f), float(g), int(ic)
                    )
                    col += 1


@njit(cache=True, nogil=True)
def _numba_head_cached_scores_dominate(left_scores, right_scores, left_surface, right_surface) -> bool:
    """16-corner cone dominance on cached score rows. The margin is non-negative (popcounts plus
    weighted absolute body deltas), so a corner where left trails right already fails the margin
    test -- the corner pre-pass rejects most pairs before the margin popcounts run. Comparison
    outcomes are identical to recomputing the corner scores from the two bases per pair; the
    margin reads the original surface rows (`_numba_head_surface_margin`), which is value-
    identical to the retired basis-tuple margin."""
    for cc in range(16):
        if left_scores[int(cc)] < right_scores[int(cc)]:
            return False
    margin = _numba_head_surface_margin(left_surface, right_surface)
    if margin <= 0.0:
        return True
    for cc in range(16):
        if left_scores[int(cc)] - right_scores[int(cc)] < margin:
            return False
    return True


@njit(cache=True, nogil=True)
def _numba_head_score_matrix_ensure(score_matrix_holder, required: int):
    if len(score_matrix_holder) == 0:
        cap = 256
        while int(cap) < int(required):
            cap *= 2
        score_matrix_holder.append(np.empty((16, int(cap)), dtype=np.float64))
        return score_matrix_holder[0]
    matrix = score_matrix_holder[0]
    if int(matrix.shape[1]) >= int(required):
        return matrix
    cap = int(matrix.shape[1])
    while int(cap) < int(required):
        cap *= 2
    grown = np.empty((16, int(cap)), dtype=np.float64)
    grown[:, : int(matrix.shape[1])] = matrix
    score_matrix_holder[0] = grown
    return grown


@njit(cache=True, nogil=True)
def _numba_head_score_matrix_sync(frontier_scores, score_matrix_holder, score_matrix_count):
    matrix = _numba_head_score_matrix_ensure(score_matrix_holder, len(frontier_scores))
    if int(score_matrix_count[0]) != len(frontier_scores):
        for idx in range(len(frontier_scores)):
            row = frontier_scores[idx]
            for corner in range(16):
                matrix[int(corner), int(idx)] = row[int(corner)]
        score_matrix_count[0] = len(frontier_scores)
    return matrix


@njit(cache=True, nogil=True)
def _numba_head_block_has_dominator(
    frontier,
    score_matrix,
    candidate,
    candidate_scores,
    eligible,
) -> bool:
    block_width = 8
    for start in range(0, len(frontier), int(block_width)):
        width = min(int(block_width), len(frontier) - int(start))
        for lane in range(int(width)):
            eligible[int(lane)] = 1
        for corner in range(16):
            active = 0
            candidate_score = candidate_scores[int(corner)]
            for lane in range(int(width)):
                if (
                    int(eligible[int(lane)]) != 0
                    and score_matrix[int(corner), int(start) + int(lane)] < candidate_score
                ):
                    eligible[int(lane)] = 0
                active += int(eligible[int(lane)])
            if int(active) == 0:
                break
        for lane in range(int(width)):
            if int(eligible[int(lane)]) == 0:
                continue
            idx = int(start) + int(lane)
            retained = frontier[int(idx)]
            margin = _numba_head_surface_margin(retained, candidate)
            if margin <= 0.0:
                return True
            dominates = True
            for corner in range(16):
                if (
                    score_matrix[int(corner), int(idx)] - candidate_scores[int(corner)]
                    < margin
                ):
                    dominates = False
                    break
            if dominates:
                return True
    return False


@njit(cache=True, nogil=True)
def _numba_head_envelope_insert_blocked_with_scores(
    frontier,
    frontier_scores,
    score_matrix_holder,
    score_matrix_count,
    candidate,
    candidate_scores,
    eligible,
):
    """Exact producer-order insert with a corner-major rejection precheck.

    The 16 independent `float64` comparisons are transposed over fixed blocks of eight retained
    rows. No arithmetic is reassociated. The canonical lists still own eviction, compaction,
    witness order, and output; the matrix is only their grow-doubling score mirror.
    """
    score_matrix = _numba_head_score_matrix_sync(
        frontier_scores, score_matrix_holder, score_matrix_count
    )
    if _numba_head_block_has_dominator(
        frontier, score_matrix, candidate, candidate_scores, eligible
    ):
        return frontier, frontier_scores

    dominated_idx = -1
    for idx in range(len(frontier)):
        if _numba_head_cached_scores_dominate(
            candidate_scores, frontier_scores[idx], candidate, frontier[idx]
        ):
            dominated_idx = idx
            break
    if dominated_idx < 0:
        frontier_idx = len(frontier)
        frontier.append(candidate)
        frontier_scores.append(candidate_scores.copy())
        score_matrix = _numba_head_score_matrix_ensure(
            score_matrix_holder, int(frontier_idx) + 1
        )
        for corner in range(16):
            score_matrix[int(corner), int(frontier_idx)] = candidate_scores[int(corner)]
        score_matrix_count[0] = len(frontier)
        return frontier, frontier_scores

    write = int(dominated_idx)
    for idx in range(int(dominated_idx) + 1, len(frontier)):
        kept_scores = frontier_scores[idx]
        if not _numba_head_cached_scores_dominate(
            candidate_scores, kept_scores, candidate, frontier[idx]
        ):
            frontier[int(write)] = frontier[idx]
            frontier_scores[int(write)] = kept_scores
            for corner in range(16):
                score_matrix[int(corner), int(write)] = score_matrix[int(corner), int(idx)]
            write += 1
    while len(frontier) > int(write):
        frontier.pop()
        frontier_scores.pop()
    frontier.append(candidate)
    frontier_scores.append(candidate_scores.copy())
    for corner in range(16):
        score_matrix[int(corner), int(write)] = candidate_scores[int(corner)]
    score_matrix_count[0] = len(frontier)
    return frontier, frontier_scores


@njit(cache=True, nogil=True)
def _numba_mark_head_surface_first_seen(seen, candidate) -> bool:
    """Record one complete bounded-inserter input row.

    A later byte-identical row cannot mutate the cone frontier: if the first copy remains it
    rejects the duplicate, and if it was rejected or evicted the transitive live dominator chain
    rejects the duplicate. The full seven-field tuple is the key; no hash equality is exposed as
    semantic equality. Callers still count every raw row before consulting this set.
    """
    if candidate in seen:
        return False
    seen[candidate] = np.uint8(1)
    return True


@njit(cache=True, nogil=True)
def _numba_append_edge_tail_bounded(
    frontier,
    frontier_scores,
    seen,
    score_matrix_holder,
    score_matrix_count,
    edge,
    end_e: int,
    body_values,
    body_starts,
    body_counts,
    head_pool,
    head_state_start,
    head_state_count,
    head_limit: int,
    lo_pos: int,
    hi_pos: int,
):
    count = 0
    cand_scores = np.empty(16, dtype=np.float64)
    eligible = np.empty(8, dtype=np.uint8)
    if int(end_e) >= 100:
        # Body tails keep the edge's head masks verbatim, so the mask-derived basis floats
        # (b/c/d at both combo corners) are the edge's own: computed once here and reused per
        # tail with only the three integer body fields substituted -- identical values to
        # rebuilding the basis from each candidate. The basis tuple is transient (corner-score
        # input only); margins later come from the retained surface rows.
        edge_basis = _numba_head_surface_basis(edge, int(lo_pos), int(hi_pos))
        tail_count = int(body_counts[int(end_e)])
        tail_start = int(body_starts[int(end_e)])
        for tail_idx in range(int(tail_count)):
            value_idx = int(tail_start) + int(tail_idx)
            tail_fever = body_values[int(value_idx), 0]
            tail_great = body_values[int(value_idx), 1]
            tail_fever_great = body_values[int(value_idx), 2]
            bf = edge[4] + tail_fever
            bg = edge[5] + tail_great
            bfg = edge[6] + tail_fever_great
            candidate = (edge[0], edge[1], edge[2], edge[3], bf, bg, bfg)
            count += 1
            if not _numba_mark_head_surface_first_seen(seen, candidate):
                continue
            candidate_basis = (
                edge_basis[0],
                edge_basis[1],
                edge_basis[2],
                edge_basis[3],
                np.int64(bf),
                np.int64(bg) - np.int64(bfg),
                np.int64(bfg),
                edge_basis[7],
                edge_basis[8],
                edge_basis[9],
                edge_basis[10],
                edge_basis[11],
                edge_basis[12],
            )
            _numba_head_basis_corner_scores_row(candidate_basis, cand_scores)
            frontier, frontier_scores = _numba_head_envelope_insert_blocked_with_scores(
                frontier,
                frontier_scores,
                score_matrix_holder,
                score_matrix_count,
                candidate,
                cand_scores,
                eligible,
            )
        return frontier, frontier_scores, int(count)
    if int(end_e) >= int(head_limit):
        if not _numba_mark_head_surface_first_seen(seen, edge):
            return frontier, frontier_scores, 1
        edge_basis = _numba_head_surface_basis(edge, int(lo_pos), int(hi_pos))
        _numba_head_basis_corner_scores_row(edge_basis, cand_scores)
        frontier, frontier_scores = _numba_head_envelope_insert_blocked_with_scores(
            frontier,
            frontier_scores,
            score_matrix_holder,
            score_matrix_count,
            edge,
            cand_scores,
            eligible,
        )
        return frontier, frontier_scores, 1
    tail_start = int(head_state_start[int(end_e)])
    tail_count = int(head_state_count[int(end_e)])
    for tail_idx in range(int(tail_count)):
        row = int(tail_start) + int(tail_idx)
        tail = (
            head_pool[row, 0],
            head_pool[row, 1],
            head_pool[row, 2],
            head_pool[row, 3],
            head_pool[row, 4],
            head_pool[row, 5],
            head_pool[row, 6],
        )
        candidate = _numba_combine(edge, tail)
        count += 1
        if not _numba_mark_head_surface_first_seen(seen, candidate):
            continue
        candidate_basis = _numba_head_surface_basis(candidate, int(lo_pos), int(hi_pos))
        _numba_head_basis_corner_scores_row(candidate_basis, cand_scores)
        frontier, frontier_scores = _numba_head_envelope_insert_blocked_with_scores(
            frontier,
            frontier_scores,
            score_matrix_holder,
            score_matrix_count,
            candidate,
            cand_scores,
            eligible,
        )
    return frontier, frontier_scores, int(count)


@njit(cache=True, nogil=True)
def _numba_append_head_generated_candidate(
    generated,
    generated_scores,
    generated_seen,
    generated_score_matrix_holder,
    generated_score_matrix_count,
    edge,
    end_e: int,
    body_values,
    body_starts,
    body_counts,
    head_pool,
    head_state_start,
    head_state_count,
    head_limit: int,
    lo_pos: int,
    hi_pos: int,
    min_surfaces: int,
    bounded_mode: int,
):
    if int(bounded_mode) != 0:
        generated, generated_scores, added = _numba_append_edge_tail_bounded(
            generated,
            generated_scores,
            generated_seen,
            generated_score_matrix_holder,
            generated_score_matrix_count,
            edge,
            int(end_e),
            body_values,
            body_starts,
            body_counts,
            head_pool,
            head_state_start,
            head_state_count,
            int(head_limit),
            int(lo_pos),
            int(hi_pos),
        )
        return generated, generated_scores, int(added), 1
    added = _numba_append_edge_tail(
        generated,
        edge,
        int(end_e),
        body_values,
        body_starts,
        body_counts,
        head_pool,
        head_state_start,
        head_state_count,
        int(head_limit),
    )
    generated, generated_scores, bounded_mode = _numba_maybe_promote_head_generated_with_scores(
        generated,
        generated_scores,
        int(lo_pos),
        int(hi_pos),
        int(min_surfaces),
        int(bounded_mode),
    )
    return generated, generated_scores, int(added), int(bounded_mode)


@njit(cache=True, nogil=True)
def _numba_promote_head_generated_with_scores(
    generated,
    lo_pos,
    hi_pos,
    min_surfaces,
):
    promoted = _numba_head_envelope_filter(
        _numba_reduce(generated), int(lo_pos), int(hi_pos), int(min_surfaces)
    )
    promoted_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    for idx in range(len(promoted)):
        row = np.empty(16, dtype=np.float64)
        _numba_head_basis_corner_scores_row(
            _numba_head_surface_basis(promoted[idx], int(lo_pos), int(hi_pos)), row
        )
        promoted_scores.append(row)
    return promoted, promoted_scores


@njit(cache=True, nogil=True)
def _numba_maybe_promote_head_generated_with_scores(
    generated,
    generated_scores,
    lo_pos,
    hi_pos,
    min_surfaces,
    bounded_mode: int,
):
    if int(bounded_mode) != 0:
        return generated, generated_scores, 1
    if len(generated) <= int(_numba_head_generated_threshold(int(min_surfaces))):
        return generated, generated_scores, 0
    promoted, promoted_scores = _numba_promote_head_generated_with_scores(
        generated, int(lo_pos), int(hi_pos), int(min_surfaces)
    )
    return promoted, promoted_scores, 1


@njit(cache=True, nogil=True)
def _numba_head_envelope_filter(frontier, lo_pos, hi_pos, min_surfaces):
    """Issue #44 Route A: LOSSLESS prune of the head frontier to its cone-Pareto set -- the surfaces
    that are best for SOME realizable stat cell. The head+body score is multilinear in (v,c,f,g) on
    the realizable region (g<=v, c,f>=1 resolve every floor's max/min), so its unfloored value hits
    its box extrema at the 16 corners. Surface K dominates C over the WHOLE realizable box iff
    unfloored score(K)-score(C) >= the per-pair floor margin (head-class Hamming distance + body-count
    delta -- the most the integer floors can move the difference) at all 16 corners. This is the head
    analog of the closed-form body hull fused into `_numba_reduce_touched_body_pairs`: best-preserving for EVERY
    realizable cell, by a 16-corner proof, not probe sampling. Composition-safe (the score is additive
    over disjoint edge/tail head ranges), so an envelope-minimal tail stays representative as the DP
    prepends edges. `min_surfaces` gates the prune for small (no-cascade) frontiers; skipping only
    RETAINS surfaces, so it stays lossless."""
    m = len(frontier)
    if m <= min_surfaces:
        return frontier
    if int(hi_pos) - int(lo_pos) <= 0:
        return frontier
    # 16 corner relative-scores, (m, 16). The basis tuple is transient per row (corner-score
    # input only); margins below read the original surface rows, which is value-identical.
    scores = np.empty((m, 16), dtype=np.float64)
    for i in range(m):
        _numba_head_basis_corner_scores_into(
            _numba_head_surface_basis(frontier[i], int(lo_pos), int(hi_pos)), scores, int(i)
        )
    # Incremental cone-Pareto: keep C unless some kept K dominates it (gap >= margin at all 16).
    # The margin is non-negative, so the zero-threshold corner pre-pass rejects most pairs before
    # the margin popcounts run -- outcomes identical to computing the margin unconditionally.
    # Kept set lives in a fixed index array compacted in place on eviction (same pattern as the
    # serve-time `_numba_session_box_keep_mask`); survivor order matches the retired
    # rebuild-a-List formulation exactly.
    kept_rows = np.empty(m, dtype=np.int64)
    kept_count = 0
    for i in range(m):
        dominated = False
        for ki in range(kept_count):
            k = int(kept_rows[int(ki)])
            if not _numba_head_scores_dominate(scores, int(k), int(i), 0.0):
                continue
            if _numba_head_scores_dominate(
                scores,
                int(k),
                int(i),
                _numba_head_surface_margin(frontier[int(k)], frontier[int(i)]),
            ):
                dominated = True
                break
        if dominated:
            continue
        write = 0
        for ki in range(kept_count):
            k = int(kept_rows[int(ki)])
            if _numba_head_scores_dominate(scores, int(i), int(k), 0.0) and _numba_head_scores_dominate(
                scores,
                int(i),
                int(k),
                _numba_head_surface_margin(frontier[int(i)], frontier[int(k)]),
            ):
                continue
            kept_rows[int(write)] = int(k)
            write += 1
        kept_rows[int(write)] = int(i)
        kept_count = int(write) + 1
    out = List.empty_list(_NUMBA_SURFACE_TYPE)
    for ki in range(kept_count):
        out.append(frontier[int(kept_rows[int(ki)])])
    return out


@njit(cache=True, nogil=True)
def _numba_session_surface_basis(
    fl, fh, gl, gh, bf, bg, bfg, lo_pos: int, hi_pos: int, c_lo: float, c_hi: float
):
    """Session-box twin of `_numba_head_surface_basis`: identical construction with the combo
    ramp slopes taken from the SESSION box corners instead of the global _HEAD_DOM_C. Serve-side
    only (the packed uint32 pool format); the build path is untouched."""
    lo = int(lo_pos)
    hi = int(hi_pos)
    hlen = hi - lo
    one = np.uint64(1)
    k_lo = (float(c_lo) - 1.0) / 100.0
    k_hi = (float(c_hi) - 1.0) / 100.0
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
def _numba_session_corner_scores_row(
    basis, row, v_lo: float, v_hi: float, c_lo: float, c_hi: float,
    f_lo: float, f_hi: float, g_lo: float, g_hi: float
) -> None:
    col = 0
    for iv in range(2):
        v = v_lo if iv == 0 else v_hi
        for ic in range(2):
            c = c_lo if ic == 0 else c_hi
            for iff in range(2):
                f = f_lo if iff == 0 else f_hi
                for ig in range(2):
                    g = g_lo if ig == 0 else g_hi
                    row[int(col)] = _numba_head_basis_corner_score(
                        basis, float(v), float(c), float(f), float(g), int(ic)
                    )
                    col += 1


@njit(cache=True, nogil=True)
def _numba_session_box_keep_mask(
    words,
    counts,
    offsets,
    lengths,
    lo_pos: int,
    hi_pos: int,
    v_lo: float,
    v_hi: float,
    c_lo: float,
    c_hi: float,
    f_lo: float,
    f_hi: float,
    g_lo: float,
    g_hi: float,
) -> np.ndarray:
    """Serve-time session-box cone prune over the PACKED first-frontier pool: per frontier, the
    same greedy 16-corner dominance-with-margin filter as `_numba_head_envelope_filter`, with the
    corners at the SESSION's realizable stat box instead of the global _HEAD_DOM box. A dropped
    row is dominated at every session-reachable cell (multilinear extrema at the covering box's
    corners; the per-pair floor margin is box-independent), so the pruned pool serves the SAME
    winner for every cell this solve can evaluate. Rows: words (N,8) uint32 mask words, counts
    (N,3) int32 body counts."""
    total = int(words.shape[0])
    keep = np.zeros(total, dtype=np.bool_)
    frontier_count = int(lengths.shape[0])
    for frontier_idx in range(frontier_count):
        start = int(offsets[int(frontier_idx)])
        length = int(lengths[int(frontier_idx)])
        if length <= 0:
            continue
        basis_list = List.empty_list(_NUMBA_HEAD_BASIS_TYPE)
        scores = np.empty((length, 16), dtype=np.float64)
        kept_rows = np.empty(length, dtype=np.int64)
        kept_count = 0
        for local_idx in range(length):
            row_idx = start + local_idx
            fl = np.uint64(words[row_idx, 0]) | (np.uint64(words[row_idx, 1]) << np.uint64(32))
            fh = np.uint64(words[row_idx, 2]) | (np.uint64(words[row_idx, 3]) << np.uint64(32))
            gl = np.uint64(words[row_idx, 4]) | (np.uint64(words[row_idx, 5]) << np.uint64(32))
            gh = np.uint64(words[row_idx, 6]) | (np.uint64(words[row_idx, 7]) << np.uint64(32))
            basis = _numba_session_surface_basis(
                fl, fh, gl, gh,
                np.uint64(counts[row_idx, 0]), np.uint64(counts[row_idx, 1]), np.uint64(counts[row_idx, 2]),
                int(lo_pos), int(hi_pos), float(c_lo), float(c_hi),
            )
            basis_list.append(basis)
            _numba_session_corner_scores_row(
                basis, scores[int(local_idx)],
                float(v_lo), float(v_hi), float(c_lo), float(c_hi),
                float(f_lo), float(f_hi), float(g_lo), float(g_hi),
            )
        for local_idx in range(length):
            dominated = False
            for ki in range(kept_count):
                k = int(kept_rows[int(ki)])
                if not _numba_head_scores_dominate(scores, int(k), int(local_idx), 0.0):
                    continue
                if _numba_head_scores_dominate(
                    scores, int(k), int(local_idx),
                    _numba_head_basis_margin(basis_list[int(k)], basis_list[int(local_idx)]),
                ):
                    dominated = True
                    break
            if dominated:
                continue
            write = 0
            for ki in range(kept_count):
                k = int(kept_rows[int(ki)])
                if _numba_head_scores_dominate(scores, int(local_idx), int(k), 0.0) and _numba_head_scores_dominate(
                    scores, int(local_idx), int(k),
                    _numba_head_basis_margin(basis_list[int(local_idx)], basis_list[int(k)]),
                ):
                    continue
                kept_rows[int(write)] = int(k)
                write += 1
            kept_rows[int(write)] = int(local_idx)
            kept_count = int(write) + 1
        for ki in range(kept_count):
            keep[start + int(kept_rows[int(ki)])] = True
    return keep


@njit(cache=True, nogil=True)
def _numba_reduce_touched_body_pairs(
    pair_mod: int,
    touched_pair,
    touched_count: int,
    best_fever_by_pair,
    bit_values,
    bit_stamps,
    bit_stamp: int,
    frontier_values,
):
    """Fused Pareto reduce + issue-#44 body-tail hull filter, allocation-free.

    Emits the surviving (body_fever, body_great, body_fever_great) rows into the reusable
    grow-doubling (cap, 3) uint64 `frontier_values` buffer and returns (buffer, count). Fusing the
    two passes and dropping the intermediate typed List / sort copy / hull coordinate arrays is
    byte-identical to the retired two-pass formulation:

    - `touched_pair[:touched_count]` holds DISTINCT pair indices: `_numba_touch_body_candidate`
      appends a pair_idx only on its first stamp-set (later touches only raise
      best_fever_by_pair), and every touch batch bumps the stamp and resets touched_count
      together. The retired duplicate-skipping scan after the sort was therefore dead, and
      sorting the live slice IN PLACE is safe -- nothing reads the insertion order afterwards
      (each batch rewrites [0, its own count) before the next reduce).
    - The reduce visits pairs in ascending pair_idx = normal_great*pair_mod + fever_great order,
      i.e. (normal_great asc, fever_great asc). A kept entry's body_fever strictly exceeds the
      stamped-Fenwick prefix max over everything already processed with fever_great' <=
      fever_great, which includes every earlier kept entry of the SAME normal_great group -- so
      within a group kept rows have strictly increasing body_fever. The retired hull's argsort
      key (normal_great * 2^24 + body_fever; body counts < total_notes << 2^24) is therefore
      strictly increasing over the kept sequence: the argsort was the identity permutation, and
      running the per-group upper hull of (body_fever, -fever_great) incrementally over the kept
      stream (the finished-groups prefix of `frontier_values` doubles as the current group's
      stack) visits the same points in the same order with the same int64 cross products. The
      retired `count <= 2` group short-cut and the `m <= 2` whole-frontier short-cut emitted
      those rows verbatim -- exactly what the chain does (a pop needs two prior in-group rows).
    - The Fenwick update sequence is unchanged (one update per distinct pair, in the same order,
      hull pops never touch it), so the carried bit_values/bit_stamps workspace stays identical.

    For a fixed (PP/combo/fever/color) cell the body score is LINEAR in the three body counts:
    `A*body_fever - pnp*normal_great - pfp*fever_great` with A,pnp,pfp >= 0. The early-Great
    extension adds points at CONSTANT normal_great, so within each normal_great level the useful
    set is the 2-D upper hull in (body_fever, -fever_great); pruning to it is bit-exact for every
    cone direction, shift-invariant, and composition-safe as the DP adds section counts."""
    if int(touched_count) <= 0:
        return frontier_values, 0
    touched_pair[: int(touched_count)].sort()
    frontier_values = _numba_u64_rows_ensure(frontier_values, 0, int(touched_count))
    out_count = 0
    group_base = 0
    group_ng = -1
    for idx in range(int(touched_count)):
        pair_idx = int(touched_pair[idx])
        normal_great = int(pair_idx) // int(pair_mod)
        fever_great = int(pair_idx) - int(normal_great) * int(pair_mod)
        best_fever = int(best_fever_by_pair[pair_idx])
        if best_fever > _numba_prefix_max_query_stamped(bit_values, bit_stamps, int(bit_stamp), int(fever_great)):
            if int(normal_great) != int(group_ng):
                group_ng = int(normal_great)
                group_base = int(out_count)
            # Upper hull of (body_fever, -fever_great): keep right turns (cross < 0).
            x = np.int64(best_fever)
            y = np.int64(-fever_great)
            while int(out_count) - int(group_base) >= 2:
                i1_bf = np.int64(frontier_values[int(out_count) - 2, 0])
                i1_bfg = np.int64(frontier_values[int(out_count) - 2, 2])
                i2_bf = np.int64(frontier_values[int(out_count) - 1, 0])
                i2_bfg = np.int64(frontier_values[int(out_count) - 1, 2])
                cross = (i2_bf - i1_bf) * (y + i1_bfg) - ((-i2_bfg) + i1_bfg) * (x - i1_bf)
                if cross >= 0:
                    out_count -= 1
                else:
                    break
            frontier_values[int(out_count), 0] = np.uint64(best_fever)
            frontier_values[int(out_count), 1] = np.uint64(normal_great + fever_great)
            frontier_values[int(out_count), 2] = np.uint64(fever_great)
            out_count += 1
        _numba_prefix_max_update_stamped(bit_values, bit_stamps, int(bit_stamp), int(fever_great), int(best_fever))
    return frontier_values, int(out_count)


@njit(cache=True, nogil=True)
def _numba_packet_arena_ensure(arenas, family_idx: int, used: int, extra: int):
    """Grow-doubling reservation on one family's flat packet-point arena. Rows [0, used) are
    live and preserved verbatim on growth (ranges are offsets, so every stored (start, end)
    stays valid); returns the (possibly replaced) arena with >= used + extra row capacity."""
    arena = arenas[int(family_idx)]
    need = int(used) + int(extra)
    cap = int(arena.shape[0])
    if need <= cap:
        return arena
    new_cap = int(cap)
    while new_cap < need:
        new_cap *= 2
    grown = np.empty((int(new_cap), 3), dtype=np.int64)
    grown[: int(used)] = arena[: int(used)]
    arenas[int(family_idx)] = grown
    return grown


@njit(cache=True, nogil=True)
def _numba_packet_points_copy(src, src_start: int, src_end: int, dst, dst_cursor: int) -> int:
    write = int(dst_cursor)
    for idx in range(int(src_start), int(src_end)):
        dst[int(write), 0] = src[int(idx), 0]
        dst[int(write), 1] = src[int(idx), 1]
        dst[int(write), 2] = src[int(idx), 2]
        write += 1
    return int(write)


@njit(cache=True, nogil=True)
def _numba_packet_points_append(buf, base: int, write: int, cf: int, cn: int, cq: int) -> int:
    """Flat twin of the retired List-based packet-point Pareto insert: identical dominated
    check, identical survivor compaction order, candidate appended last. The working set is
    buf rows [base, write); returns the new write cursor."""
    for idx in range(int(base), int(write)):
        if buf[int(idx), 0] >= cf and buf[int(idx), 1] <= cn and buf[int(idx), 2] <= cq:
            return int(write)

    out = int(base)
    for idx in range(int(base), int(write)):
        kf = buf[int(idx), 0]
        kn = buf[int(idx), 1]
        kq = buf[int(idx), 2]
        if not (cf >= kf and cn <= kn and cq <= kq):
            if int(out) != int(idx):
                buf[int(out), 0] = kf
                buf[int(out), 1] = kn
                buf[int(out), 2] = kq
            out += 1
    buf[int(out), 0] = np.int64(cf)
    buf[int(out), 1] = np.int64(cn)
    buf[int(out), 2] = np.int64(cq)
    return int(out) + 1


@njit(cache=True, nogil=True)
def _numba_packet_union(
    left_buf,
    left_start: int,
    left_end: int,
    right_buf,
    right_start: int,
    right_end: int,
    out_buf,
    out_cursor: int,
):
    """Flat-range twin of the retired List-based packet union, case for case. Returns
    (code, start, end): code 1 keeps the left range verbatim (the List version returned the
    ``left`` object), code 2 the right range, code 0 wrote a fresh union into ``out_buf`` at
    [out_cursor, end). Content and order match the List version exactly; the caller must
    reserve (left_len + right_len) rows at ``out_cursor`` and guarantee [out_cursor, ...)
    does not overlap either input range (arena writes only ever land at the cursor, past
    every live range, so this holds by construction)."""
    left_len = int(left_end) - int(left_start)
    right_len = int(right_end) - int(right_start)
    if left_len <= 0:
        return 2, int(right_start), int(right_end)
    if right_len <= 0:
        return 1, int(left_start), int(left_end)
    if left_len == 1:
        cf = left_buf[int(left_start), 0]
        cn = left_buf[int(left_start), 1]
        cq = left_buf[int(left_start), 2]
        for idx in range(int(right_start), int(right_end)):
            if right_buf[int(idx), 0] >= cf and right_buf[int(idx), 1] <= cn and right_buf[int(idx), 2] <= cq:
                return 2, int(right_start), int(right_end)

        write = int(out_cursor)
        out_buf[int(write), 0] = cf
        out_buf[int(write), 1] = cn
        out_buf[int(write), 2] = cq
        write += 1
        for idx in range(int(right_start), int(right_end)):
            kf = right_buf[int(idx), 0]
            kn = right_buf[int(idx), 1]
            kq = right_buf[int(idx), 2]
            if not (cf >= kf and cn <= kn and cq <= kq):
                out_buf[int(write), 0] = kf
                out_buf[int(write), 1] = kn
                out_buf[int(write), 2] = kq
                write += 1
        return 0, int(out_cursor), int(write)
    if right_len == 1:
        cf = right_buf[int(right_start), 0]
        cn = right_buf[int(right_start), 1]
        cq = right_buf[int(right_start), 2]
        for idx in range(int(left_start), int(left_end)):
            if left_buf[int(idx), 0] >= cf and left_buf[int(idx), 1] <= cn and left_buf[int(idx), 2] <= cq:
                return 1, int(left_start), int(left_end)

        write = int(out_cursor)
        for idx in range(int(left_start), int(left_end)):
            kf = left_buf[int(idx), 0]
            kn = left_buf[int(idx), 1]
            kq = left_buf[int(idx), 2]
            if not (cf >= kf and cn <= kn and cq <= kq):
                out_buf[int(write), 0] = kf
                out_buf[int(write), 1] = kn
                out_buf[int(write), 2] = kq
                write += 1
        out_buf[int(write), 0] = cf
        out_buf[int(write), 1] = cn
        out_buf[int(write), 2] = cq
        write += 1
        return 0, int(out_cursor), int(write)
    write = int(out_cursor)
    for idx in range(int(left_start), int(left_end)):
        out_buf[int(write), 0] = left_buf[int(idx), 0]
        out_buf[int(write), 1] = left_buf[int(idx), 1]
        out_buf[int(write), 2] = left_buf[int(idx), 2]
        write += 1
    for idx in range(int(right_start), int(right_end)):
        write = _numba_packet_points_append(
            out_buf,
            int(out_cursor),
            int(write),
            int(right_buf[int(idx), 0]),
            int(right_buf[int(idx), 1]),
            int(right_buf[int(idx), 2]),
        )
    return 0, int(out_cursor), int(write)


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
def _numba_build_region2_packet_families(action_count: int, raw_fever_fill: float, action_k, n: int):
    family_defect = np.empty(max(1, int(action_count)), dtype=np.int32)
    family_start = np.empty(max(1, int(action_count)), dtype=np.int32)
    family_end = np.empty(max(1, int(action_count)), dtype=np.int32)
    family_count = 0

    prev_defect = 0
    prev_offset = -1000000000
    stop = _numba_region2_k_scan_stop(int(action_count), float(raw_fever_fill))
    for action_idx in range(1, int(stop)):
        k = int(action_k[int(action_idx)])
        region_offset = _numba_region2_offset_for_count(0, int(k), float(raw_fever_fill), int(n) + int(k) + 2)
        if int(region_offset) < 1:
            continue
        activation_offset = int(region_offset) + int(k)
        defect = int(k) - 1 - (2 * int(activation_offset))
        if (
            int(family_count) > 0
            and int(prev_defect) == int(defect)
            and int(activation_offset) == int(prev_offset) + 1
        ):
            family_end[int(family_count) - 1] = int(activation_offset)
        else:
            family_defect[int(family_count)] = int(defect)
            family_start[int(family_count)] = int(activation_offset)
            family_end[int(family_count)] = int(activation_offset)
            family_count += 1
        prev_defect = int(defect)
        prev_offset = int(activation_offset)
    return family_count, family_defect, family_start, family_end


@njit(cache=True, nogil=True)
def _numba_packet_queue_transfer(
    family_idx: int,
    seg_base: int,
    front_alpha,
    front_ag_start,
    front_ag_end,
    front_len,
    back_alpha,
    back_pk_off,
    back_len,
    back_pk_arenas,
    front_ag_arenas,
) -> None:
    """Flat twin of the retired List-based back->front transfer: pop back entries newest
    first, fold each packet into the running union exactly like ``union(packet, aggregate)``,
    and append (alpha, aggregate range) to the front stack. Alias-returning unions become
    range shares (aggregate kept -> the new front entry reuses the previous entry's range) or
    materialized copies (packet kept -> its points are copied into the front arena, content
    identical to the aliased List object). Front aggregate ends are non-decreasing along the
    stack, so the arena cursor is always the top entry's end and pops rewind losslessly."""
    f = int(family_idx)
    base = int(seg_base)
    pk_buf = back_pk_arenas[f]
    front_count = int(front_len[f])
    front_cursor = int(front_ag_end[base + front_count - 1]) if front_count > 0 else 0
    run_start = 0
    run_end = 0
    back_count = int(back_len[f])
    while back_count > 0:
        entry = int(back_count) - 1
        alpha = int(back_alpha[base + entry])
        pk_start = int(back_pk_off[base + entry])
        pk_end = int(back_pk_off[base + entry + 1])
        back_count = int(entry)
        pk_len = int(pk_end) - int(pk_start)
        if int(run_end) - int(run_start) <= 0:
            front_arena = _numba_packet_arena_ensure(front_ag_arenas, f, int(front_cursor), int(pk_len))
            run_start = int(front_cursor)
            run_end = _numba_packet_points_copy(pk_buf, int(pk_start), int(pk_end), front_arena, int(front_cursor))
            front_cursor = int(run_end)
        else:
            front_arena = _numba_packet_arena_ensure(
                front_ag_arenas, f, int(front_cursor), int(pk_len) + (int(run_end) - int(run_start))
            )
            code, out_start, out_end = _numba_packet_union(
                pk_buf,
                int(pk_start),
                int(pk_end),
                front_arena,
                int(run_start),
                int(run_end),
                front_arena,
                int(front_cursor),
            )
            if int(code) == 1:
                # Union kept the packet alone (the List version aliased the packet object):
                # materialize its points into the front arena, content identical.
                run_start = int(front_cursor)
                run_end = _numba_packet_points_copy(
                    pk_buf, int(pk_start), int(pk_end), front_arena, int(front_cursor)
                )
                front_cursor = int(run_end)
            elif int(code) == 0:
                run_start = int(out_start)
                run_end = int(out_end)
                front_cursor = int(run_end)
            # code 2: union kept the running aggregate -> share the previous entry's range.
        front_alpha[base + front_count] = np.int64(alpha)
        front_ag_start[base + front_count] = np.int64(run_start)
        front_ag_end[base + front_count] = np.int64(run_end)
        front_count += 1
    front_len[f] = np.int64(front_count)
    back_len[f] = np.int64(0)


@njit(cache=True, nogil=True)
def _numba_packet_queue_pop_expired_after(
    high_alpha: int,
    family_idx: int,
    seg_base: int,
    front_alpha,
    front_ag_start,
    front_ag_end,
    front_len,
    back_alpha,
    back_pk_off,
    back_len,
    back_pk_arenas,
    front_ag_arenas,
) -> None:
    f = int(family_idx)
    base = int(seg_base)
    while True:
        if int(front_len[f]) <= 0:
            _numba_packet_queue_transfer(
                f,
                base,
                front_alpha,
                front_ag_start,
                front_ag_end,
                front_len,
                back_alpha,
                back_pk_off,
                back_len,
                back_pk_arenas,
                front_ag_arenas,
            )
        if int(front_len[f]) <= 0:
            return
        if int(front_alpha[base + int(front_len[f]) - 1]) <= int(high_alpha):
            return
        front_len[f] = np.int64(int(front_len[f]) - 1)


@njit(cache=True, nogil=True)
def _numba_packet_queue_push_back(
    alpha: int,
    pk_start: int,
    pk_end: int,
    family_idx: int,
    seg_base: int,
    seg_limit: int,
    back_alpha,
    back_pk_off,
    back_ag_start,
    back_ag_end,
    back_len,
    back_pk_arenas,
    back_ag_arenas,
) -> None:
    """Flat twin of the retired List-based push_back. The packet occupies back-packet-arena
    rows [pk_start, pk_end), already written at the arena cursor by the caller; callers
    return early on empty packets exactly like the List version's length guard. The new top
    aggregate is ``union(old_top, packet)``: fresh unions land at the aggregate-arena cursor,
    an old-top alias shares the old range, and a packet alias (or the empty-back seed, which
    the List version aliased by reference) is materialized with identical content."""
    f = int(family_idx)
    base = int(seg_base)
    count = int(back_len[f])
    if base + count + 1 >= int(seg_limit):
        raise ValueError("FG packet queue exceeded its family window bound")
    pk_len = int(pk_end) - int(pk_start)
    pk_buf = back_pk_arenas[f]
    if count > 0:
        top_start = int(back_ag_start[base + count - 1])
        top_end = int(back_ag_end[base + count - 1])
        ag_cursor = int(top_end)
        ag_buf = _numba_packet_arena_ensure(
            back_ag_arenas, f, int(ag_cursor), (int(top_end) - int(top_start)) + int(pk_len)
        )
        code, out_start, out_end = _numba_packet_union(
            ag_buf,
            int(top_start),
            int(top_end),
            pk_buf,
            int(pk_start),
            int(pk_end),
            ag_buf,
            int(ag_cursor),
        )
        if int(code) == 2:
            # Union kept the packet alone: materialize into the aggregate arena.
            out_start = int(ag_cursor)
            out_end = _numba_packet_points_copy(pk_buf, int(pk_start), int(pk_end), ag_buf, int(ag_cursor))
    else:
        ag_buf = _numba_packet_arena_ensure(back_ag_arenas, f, 0, int(pk_len))
        out_start = 0
        out_end = _numba_packet_points_copy(pk_buf, int(pk_start), int(pk_end), ag_buf, 0)
    back_alpha[base + count] = np.int64(alpha)
    back_ag_start[base + count] = np.int64(out_start)
    back_ag_end[base + count] = np.int64(out_end)
    back_pk_off[base + count + 1] = np.int64(pk_end)
    back_len[f] = np.int64(count + 1)


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
    prefix_perfect_hit,
    prefix_perfect_valid,
    prefix_late_hit,
    prefix_late_valid,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    capped_perfect_edge_e,
    capped_late_edge_e,
    capped_eg_perfect_e,
    capped_eg_late_e,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    real_fever_time: float,
    real_time_idx: int,
    family_idx: int,
    seg_base: int,
    seg_limit: int,
    back_alpha,
    back_pk_off,
    back_ag_start,
    back_ag_end,
    back_len,
    back_pk_arenas,
    back_ag_arenas,
):
    if int(activation) < 100 or int(activation) >= int(n):
        return
    if int(prefix_perfect_valid[int(activation)]) == 0:
        return
    perfect_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
    if int(mode) == 0 and int(use_forced_great_timing_i) == 0:
        band_lo = _numba_base_perfect_end_band_lo(
            int(n),
            int(activation),
            float(real_fever_time),
            perfect_floor_timestamps,
        )
        total_points = 0
        for end_e in range(int(band_lo), int(perfect_e) + 1):
            if _numba_base_perfect_end_is_reachable(
                int(n), int(band_lo), int(end_e), perfect_floor_timestamps
            ):
                total_points += int(body_counts[int(end_e)])
        if int(total_points) <= 0:
            return
        pk_cursor = int(back_pk_off[int(seg_base) + int(back_len[int(family_idx)])])
        pk_buf = _numba_packet_arena_ensure(
            back_pk_arenas, int(family_idx), int(pk_cursor), int(total_points)
        )
        write = int(pk_cursor)
        for end_e in range(int(band_lo), int(perfect_e) + 1):
            if not _numba_base_perfect_end_is_reachable(
                int(n), int(band_lo), int(end_e), perfect_floor_timestamps
            ):
                continue
            tail_count = int(body_counts[int(end_e)])
            tail_start = int(body_starts[int(end_e)])
            fever_len = int(end_e) - int(activation)
            for tail_idx in range(int(tail_count)):
                value_idx = int(tail_start) + int(tail_idx)
                tail_fever = body_values[int(value_idx), 0]
                tail_great = body_values[int(value_idx), 1]
                tail_fever_great = body_values[int(value_idx), 2]
                tail_normal_great = int(tail_great) - int(tail_fever_great)
                pk_buf[int(write), 0] = np.int64(int(tail_fever) + int(fever_len))
                pk_buf[int(write), 1] = np.int64(
                    int(tail_normal_great) + (2 * int(activation)) + int(defect)
                )
                pk_buf[int(write), 2] = np.int64(int(tail_fever_great))
                write += 1
        _numba_packet_queue_push_back(
            int(activation),
            int(pk_cursor),
            int(write),
            int(family_idx),
            int(seg_base),
            int(seg_limit),
            back_alpha,
            back_pk_off,
            back_ag_start,
            back_ag_end,
            back_len,
            back_pk_arenas,
            back_ag_arenas,
        )
        return
    edge_e = int(perfect_e)
    edge_eg_e = int(capped_eg_perfect_e[int(real_time_idx), int(activation)])
    fever_great_delta = 0
    if int(mode) != 0:
        if int(use_forced_great_timing_i) == 0:
            return
        if int(prefix_late_valid[int(activation)]) == 0:
            return
        late_e = int(capped_late_edge_e[int(real_time_idx), int(activation)])
        late_eg_e = int(capped_eg_late_e[int(real_time_idx), int(activation)])
        if not _numba_late_edge_extends(
            int(perfect_e), int(late_e), int(late_eg_e), int(edge_eg_e)
        ):
            return
        edge_e = int(late_e)
        edge_eg_e = int(late_eg_e)
        fever_great_delta = 1

    # Issue #44: extend the fever end from `edge_e` (the Perfect/late boundary) up to the
    # earliest-Great floor boundary `eg_e`. Each e in [edge_e, eg_e] is its own Pareto surface;
    # the notes [edge_e, e) are pulled into fever as GREATS (all body, since activation >= 100),
    # so each such e contributes (e - edge_e) extra fever-greats on top of the section's fever
    # length. eg_e == edge_e on the overwhelming majority of activations -> the loop runs once
    # and this is bit-for-bit the pre-#44 behaviour at zero added cost.
    eg_e = int(edge_eg_e)
    total_points = 0
    for end_e in range(int(edge_e), int(eg_e) + 1):
        total_points += int(body_counts[int(end_e)])
    if int(total_points) <= 0:
        return
    pk_cursor = int(back_pk_off[int(seg_base) + int(back_len[int(family_idx)])])
    pk_buf = _numba_packet_arena_ensure(back_pk_arenas, int(family_idx), int(pk_cursor), int(total_points))
    write = int(pk_cursor)
    for end_e in range(int(edge_e), int(eg_e) + 1):
        tail_count = int(body_counts[int(end_e)])
        if int(tail_count) <= 0:
            continue
        fever_len = int(end_e) - int(activation)
        extra_fever_great = int(end_e) - int(edge_e)
        tail_start = int(body_starts[int(end_e)])
        for tail_idx in range(int(tail_count)):
            value_idx = int(tail_start) + int(tail_idx)
            tail_fever = body_values[int(value_idx), 0]
            tail_great = body_values[int(value_idx), 1]
            tail_fever_great = body_values[int(value_idx), 2]
            tail_normal_great = int(tail_great) - int(tail_fever_great)
            shifted_normal_great = int(tail_normal_great) + (2 * int(activation)) + int(defect)
            packet_fever_great = int(tail_fever_great) + int(fever_great_delta) + int(extra_fever_great)
            pk_buf[int(write), 0] = np.int64(int(tail_fever) + int(fever_len))
            pk_buf[int(write), 1] = np.int64(int(shifted_normal_great))
            pk_buf[int(write), 2] = np.int64(int(packet_fever_great))
            write += 1
    _numba_packet_queue_push_back(
        int(activation),
        int(pk_cursor),
        int(write),
        int(family_idx),
        int(seg_base),
        int(seg_limit),
        back_alpha,
        back_pk_off,
        back_ag_start,
        back_ag_end,
        back_len,
        back_pk_arenas,
        back_ag_arenas,
    )


@njit(cache=True, nogil=True)
def _numba_region2_packet_queue_push_activation(
    n: int,
    activation_offset: int,
    defect: int,
    activation: int,
    raw_fever_fill: float,
    body_values,
    body_starts,
    body_counts,
    timestamps,
    candidate_high_delta_max,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    hit_token_to_id,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hit_ids,
    region_perfect_hit_ids,
    region_perfect_valids,
    region_perfect_end_by_hit,
    region_great_end_by_hit,
    family_idx: int,
    seg_base: int,
    seg_limit: int,
    back_alpha,
    back_pk_off,
    back_ag_start,
    back_ag_end,
    back_len,
    back_pk_arenas,
    back_ag_arenas,
):
    if int(activation) < 100 or int(activation) >= int(n):
        return
    k = (2 * int(activation_offset)) + int(defect) + 1
    region_offset = int(activation_offset) - int(k)
    if int(k) <= 0 or int(region_offset) < 1:
        return
    state_i = int(activation) - int(activation_offset)
    section_start = int(state_i) + 1
    if int(section_start) < 0 or int(section_start) >= int(n):
        return

    # Shared-core lookup: the great-branch region-run core (great_end, capped hits) is a pure
    # function of (section_start, run_start, activation) -- k participates only via the
    # within-run test of the fill crossing -- so a stored CSR entry matching (offset, activation,
    # is_great) with the activation inside THIS push's k-run is byte-identical to re-deriving the
    # core live. Entries the table's fits-in-chart guard skipped (clamped near-end runs) miss the
    # lookup and take the exact live path below, preserving current emitted frontiers verbatim.
    push_run_start = int(section_start) + int(region_offset)
    looked_up = 0
    activation_i = -1
    edge_e = -1
    run_start = -1
    great_end = -1
    activation_great_idx = -1
    eg_e = -1
    valid = 0
    for entry_idx in range(int(region_starts[int(section_start)]), int(region_starts[int(section_start) + 1])):
        if (
            int(region_offsets[int(entry_idx)]) == int(region_offset)
            and int(region_activations[int(entry_idx)]) == int(activation)
            and int(region_is_greats[int(entry_idx)]) == 1
            and int(region_activations[int(entry_idx)]) < int(push_run_start) + int(k)
        ):
            (
                activation_i,
                edge_e,
                run_start,
                great_end,
                activation_great_idx,
                eg_e,
                valid,
            ) = (
                _numba_region_run_edge_from_core(
                    int(n),
                    int(section_start),
                    int(region_offset),
                    int(region_activations[int(entry_idx)]),
                    int(region_great_ends[int(entry_idx)]),
                    1,
                    int(region_act_hit_ids[int(entry_idx)]),
                    int(region_perfect_hit_ids[int(entry_idx)]),
                    int(region_perfect_valids[int(entry_idx)]),
                    1,
                    region_perfect_end_by_hit,
                    region_great_end_by_hit,
                )
            )
            looked_up = 1
            break
    if int(looked_up) == 0:
        (
            activation_i,
            edge_e,
            run_start,
            great_end,
            activation_great_idx,
            eg_e,
            valid,
        ) = (
            _numba_region_run_edge_for_offset(
                int(n),
                int(section_start),
                int(region_offset),
                int(k),
                float(raw_fever_fill),
                timestamps,
                candidate_high_delta_max,
                perfect_floor_timestamps,
                perfect_candidate_timestamps,
                great_floor_timestamps,
                great_candidate_timestamps,
                lanes,
                hit_token_to_id,
                region_perfect_end_by_hit,
                region_great_end_by_hit,
            )
        )
    if int(valid) == 0 or int(activation_great_idx) < 0 or int(activation_i) != int(activation):
        return

    total_points = 0
    for end_e in range(int(edge_e), int(eg_e) + 1):
        total_points += int(body_counts[int(end_e)])
    if int(total_points) <= 0:
        return
    pk_cursor = int(back_pk_off[int(seg_base) + int(back_len[int(family_idx)])])
    pk_buf = _numba_packet_arena_ensure(back_pk_arenas, int(family_idx), int(pk_cursor), int(total_points))
    write = int(pk_cursor)
    for end_e in range(int(edge_e), int(eg_e) + 1):
        tail_count = int(body_counts[int(end_e)])
        if int(tail_count) <= 0:
            continue
        if int(end_e) == int(edge_e):
            edge = _numba_pack_edge(
                int(n),
                int(activation),
                int(edge_e),
                int(run_start),
                int(great_end),
                int(activation),
            )
        else:
            edge = _numba_pack_edge_eg(
                int(n),
                int(activation),
                int(end_e),
                int(run_start),
                int(great_end),
                int(activation),
                int(edge_e),
                int(end_e),
            )
        edge_fever = int(edge[4])
        edge_fever_great = int(edge[6])
        edge_normal = int(edge[5]) - int(edge[6])
        extra_normal = int(edge_normal) - ((2 * int(activation_offset)) + int(defect))
        tail_start = int(body_starts[int(end_e)])
        for tail_idx in range(int(tail_count)):
            value_idx = int(tail_start) + int(tail_idx)
            tail_fever = body_values[int(value_idx), 0]
            tail_great = body_values[int(value_idx), 1]
            tail_fever_great = body_values[int(value_idx), 2]
            tail_normal_great = int(tail_great) - int(tail_fever_great)
            pk_buf[int(write), 0] = np.int64(int(tail_fever) + int(edge_fever))
            pk_buf[int(write), 1] = np.int64(
                int(tail_normal_great) + (2 * int(activation)) + int(defect) + int(extra_normal)
            )
            pk_buf[int(write), 2] = np.int64(int(tail_fever_great) + int(edge_fever_great))
            write += 1
    _numba_packet_queue_push_back(
        int(activation),
        int(pk_cursor),
        int(write),
        int(family_idx),
        int(seg_base),
        int(seg_limit),
        back_alpha,
        back_pk_off,
        back_ag_start,
        back_ag_end,
        back_len,
        back_pk_arenas,
        back_ag_arenas,
    )


@njit(cache=True, nogil=True)
def _numba_touch_packet_points_for_state(
    points,
    point_start: int,
    point_end: int,
    state_i: int,
    pair_mod: int,
    pair_stamp_value: int,
    pair_stamp,
    best_fever_by_pair,
    touched_pair,
    touched_count: int,
):
    generated_count = 0
    for packet_idx in range(int(point_start), int(point_end)):
        body_fever = points[int(packet_idx), 0]
        shifted_normal = points[int(packet_idx), 1]
        fever_great = points[int(packet_idx), 2]
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
def _numba_u64_rows_ensure(values, used: int, extra: int):
    """Grow-doubling reservation on a flat (cap, w) uint64 row store (body-tail values, the fused
    reduce+hull output buffer, the flat head-state pool). Rows [0, used) are live and preserved
    verbatim; stored offsets stay valid."""
    need = int(used) + int(extra)
    cap = int(values.shape[0])
    if need <= cap:
        return values
    new_cap = int(cap)
    while new_cap < need:
        new_cap *= 2
    grown = np.empty((int(new_cap), int(values.shape[1])), dtype=np.uint64)
    grown[: int(used)] = values[: int(used)]
    return grown


@njit(cache=True, nogil=True)
def _numba_store_body_tail_frontier(
    body_values, body_starts, body_counts, state: int, cursor: int, frontier_values, frontier_count: int
):
    count = int(frontier_count)
    grown = _numba_u64_rows_ensure(body_values, int(cursor), int(count))
    body_starts[int(state)] = int(cursor)
    body_counts[int(state)] = int(count)
    for idx in range(count):
        grown[int(cursor) + int(idx), 0] = frontier_values[int(idx), 0]
        grown[int(cursor) + int(idx), 1] = frontier_values[int(idx), 1]
        grown[int(cursor) + int(idx), 2] = frontier_values[int(idx), 2]
    return grown, int(cursor) + int(count)


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
        tail_fever = body_values[int(value_idx), 0]
        tail_great = body_values[int(value_idx), 1]
        tail_fever_great = body_values[int(value_idx), 2]
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
def _numba_packet_body_tails_from_precomputed_end_indices(
    n: int,
    action_count: int,
    region_action_count: int,
    raw_fever_fill: float,
    action_k,
    later_fill,
    later_forced,
    later_activation_forced,
    reachable,
    use_forced_great_timing_i: int,
    timestamps,
    candidate_high_delta_max,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hit_ids,
    region_perfect_hit_ids,
    region_perfect_valids,
    region_hit_token_to_id,
    region_perfect_end_by_hit,
    region_great_end_by_hit,
    prefix_perfect_hit,
    prefix_perfect_valid,
    prefix_late_hit,
    prefix_late_valid,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    capped_perfect_edge_e,
    capped_late_edge_e,
    capped_eg_perfect_e,
    capped_eg_late_e,
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
    body_values = np.empty((1024, 3), dtype=np.uint64)
    body_starts = np.zeros(int(n) + 1, dtype=np.int32)
    body_counts = np.zeros(int(n) + 1, dtype=np.int32)
    body_values[0, 0] = np.uint64(0)
    body_values[0, 1] = np.uint64(0)
    body_values[0, 2] = np.uint64(0)
    _numba_store_shared_empty_body_tail(body_starts, body_counts, int(n))
    body_cursor = 1
    # Reusable output buffer for the fused per-state reduce+hull (grow-doubling, rewritten from
    # row 0 each state; survivors are copied into body_values before the next state runs).
    reduce_values = np.empty((1024, 3), dtype=np.uint64)

    family_count, family_mode, family_defect, family_start, family_end = _numba_build_packet_families(
        int(action_count),
        later_fill,
        later_forced,
        later_activation_forced,
    )
    # Cursor-managed flat packet queues (one two-stack sliding-window queue per family).
    # Stacks live in CSR segments of shared 1D arrays: family f owns slots
    # [seg_off[f], seg_off[f + 1]) sized to its window width plus slack -- the queue holds at
    # most (family_end - family_start + 1) live entries (each alpha is pushed once, expired
    # entries are popped before pushes, and at touch time every entry is window-live).
    # Packet points and aggregates live in per-family grow-doubling (cap, 3) int64 arenas;
    # per-entry (start, end) ranges replace the retired List objects, with union alias
    # returns represented as range shares (see _numba_packet_queue_transfer / push_back).
    seg_off = np.zeros(int(family_count) + 1, dtype=np.int64)
    for family_idx in range(int(family_count)):
        width = int(family_end[int(family_idx)]) - int(family_start[int(family_idx)]) + 1
        seg_off[int(family_idx) + 1] = int(seg_off[int(family_idx)]) + int(width) + 3
    total_slots = max(1, int(seg_off[int(family_count)]))
    front_alpha = np.zeros(int(total_slots), dtype=np.int64)
    front_ag_start = np.zeros(int(total_slots), dtype=np.int64)
    front_ag_end = np.zeros(int(total_slots), dtype=np.int64)
    front_len = np.zeros(max(1, int(family_count)), dtype=np.int64)
    back_alpha = np.zeros(int(total_slots), dtype=np.int64)
    back_pk_off = np.zeros(int(total_slots), dtype=np.int64)
    back_ag_start = np.zeros(int(total_slots), dtype=np.int64)
    back_ag_end = np.zeros(int(total_slots), dtype=np.int64)
    back_len = np.zeros(max(1, int(family_count)), dtype=np.int64)
    back_pk_arenas = List.empty_list(_NUMBA_PACKET_ARENA_TYPE)
    back_ag_arenas = List.empty_list(_NUMBA_PACKET_ARENA_TYPE)
    front_ag_arenas = List.empty_list(_NUMBA_PACKET_ARENA_TYPE)
    for _family_idx in range(int(family_count)):
        back_pk_arenas.append(np.empty((64, 3), dtype=np.int64))
        back_ag_arenas.append(np.empty((64, 3), dtype=np.int64))
        front_ag_arenas.append(np.empty((64, 3), dtype=np.int64))
    next_push_state_by_family = np.empty(int(family_count), dtype=np.int32)
    for family_idx in range(int(family_count)):
        next_push_state_by_family[int(family_idx)] = int(n) - 1

    region_family_count, region_family_defect, region_family_start, region_family_end = _numba_build_region2_packet_families(
        int(region_action_count),
        float(raw_fever_fill),
        action_k,
        int(n),
    )
    region_seg_off = np.zeros(int(region_family_count) + 1, dtype=np.int64)
    for family_idx in range(int(region_family_count)):
        width = int(region_family_end[int(family_idx)]) - int(region_family_start[int(family_idx)]) + 1
        region_seg_off[int(family_idx) + 1] = int(region_seg_off[int(family_idx)]) + int(width) + 3
    region_total_slots = max(1, int(region_seg_off[int(region_family_count)]))
    region_front_alpha = np.zeros(int(region_total_slots), dtype=np.int64)
    region_front_ag_start = np.zeros(int(region_total_slots), dtype=np.int64)
    region_front_ag_end = np.zeros(int(region_total_slots), dtype=np.int64)
    region_front_len = np.zeros(max(1, int(region_family_count)), dtype=np.int64)
    region_back_alpha = np.zeros(int(region_total_slots), dtype=np.int64)
    region_back_pk_off = np.zeros(int(region_total_slots), dtype=np.int64)
    region_back_ag_start = np.zeros(int(region_total_slots), dtype=np.int64)
    region_back_ag_end = np.zeros(int(region_total_slots), dtype=np.int64)
    region_back_len = np.zeros(max(1, int(region_family_count)), dtype=np.int64)
    region_back_pk_arenas = List.empty_list(_NUMBA_PACKET_ARENA_TYPE)
    region_back_ag_arenas = List.empty_list(_NUMBA_PACKET_ARENA_TYPE)
    region_front_ag_arenas = List.empty_list(_NUMBA_PACKET_ARENA_TYPE)
    for _family_idx in range(int(region_family_count)):
        region_back_pk_arenas.append(np.empty((64, 3), dtype=np.int64))
        region_back_ag_arenas.append(np.empty((64, 3), dtype=np.int64))
        region_front_ag_arenas.append(np.empty((64, 3), dtype=np.int64))
    next_push_state_by_region_family = np.empty(max(1, int(region_family_count)), dtype=np.int32)
    for family_idx in range(int(region_family_count)):
        next_push_state_by_region_family[int(family_idx)] = int(n) - 1

    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0

    for state_i in range(int(n) - 1, 99, -1):
        if not reachable[int(state_i)]:
            continue

        for family_idx in range(int(family_count)):
            high_alpha = int(state_i) + int(family_end[int(family_idx)])
            _numba_packet_queue_pop_expired_after(
                int(high_alpha),
                int(family_idx),
                int(seg_off[int(family_idx)]),
                front_alpha,
                front_ag_start,
                front_ag_end,
                front_len,
                back_alpha,
                back_pk_off,
                back_len,
                back_pk_arenas,
                front_ag_arenas,
            )
            push_state = int(next_push_state_by_family[int(family_idx)])
            max_live_push_state = int(high_alpha) - int(family_start[int(family_idx)])
            if int(push_state) > int(max_live_push_state):
                push_state = int(max_live_push_state)
            while int(push_state) >= int(state_i):
                activation = int(push_state) + int(family_start[int(family_idx)])
                _numba_packet_queue_push_activation(
                    int(n),
                    int(family_mode[int(family_idx)]),
                    int(family_defect[int(family_idx)]),
                    int(activation),
                    body_values,
                    body_starts,
                    body_counts,
                    int(use_forced_great_timing_i),
                    prefix_perfect_hit,
                    prefix_perfect_valid,
                    prefix_late_hit,
                    prefix_late_valid,
                    timestamp_end_idx,
                    perfect_end_idx,
                    great_end_idx,
                    great_floor_end_idx,
                    capped_perfect_edge_e,
                    capped_late_edge_e,
                    capped_eg_perfect_e,
                    capped_eg_late_e,
                    perfect_floor_timestamps,
                    great_floor_timestamps,
                    lanes,
                    float(real_fever_time),
                    int(real_time_idx),
                    int(family_idx),
                    int(seg_off[int(family_idx)]),
                    int(seg_off[int(family_idx) + 1]),
                    back_alpha,
                    back_pk_off,
                    back_ag_start,
                    back_ag_end,
                    back_len,
                    back_pk_arenas,
                    back_ag_arenas,
                )
                push_state -= 1
            next_push_state_by_family[int(family_idx)] = int(state_i) - 1

        if int(use_forced_great_timing_i) != 0:
            for family_idx in range(int(region_family_count)):
                high_alpha = int(state_i) + int(region_family_end[int(family_idx)])
                _numba_packet_queue_pop_expired_after(
                    int(high_alpha),
                    int(family_idx),
                    int(region_seg_off[int(family_idx)]),
                    region_front_alpha,
                    region_front_ag_start,
                    region_front_ag_end,
                    region_front_len,
                    region_back_alpha,
                    region_back_pk_off,
                    region_back_len,
                    region_back_pk_arenas,
                    region_front_ag_arenas,
                )
                push_state = int(next_push_state_by_region_family[int(family_idx)])
                max_live_push_state = int(high_alpha) - int(region_family_start[int(family_idx)])
                if int(push_state) > int(max_live_push_state):
                    push_state = int(max_live_push_state)
                while int(push_state) >= int(state_i):
                    activation = int(push_state) + int(region_family_start[int(family_idx)])
                    _numba_region2_packet_queue_push_activation(
                        int(n),
                        int(region_family_start[int(family_idx)]),
                        int(region_family_defect[int(family_idx)]),
                        int(activation),
                        float(raw_fever_fill),
                        body_values,
                        body_starts,
                        body_counts,
                        timestamps,
                        candidate_high_delta_max,
                        perfect_candidate_timestamps,
                        great_candidate_timestamps,
                        perfect_floor_timestamps,
                        great_floor_timestamps,
                        lanes,
                        region_hit_token_to_id,
                        region_starts,
                        region_offsets,
                        region_activations,
                        region_great_ends,
                        region_is_greats,
                        region_act_hit_ids,
                        region_perfect_hit_ids,
                        region_perfect_valids,
                        region_perfect_end_by_hit,
                        region_great_end_by_hit,
                        int(family_idx),
                        int(region_seg_off[int(family_idx)]),
                        int(region_seg_off[int(family_idx) + 1]),
                        region_back_alpha,
                        region_back_pk_off,
                        region_back_ag_start,
                        region_back_ag_end,
                        region_back_len,
                        region_back_pk_arenas,
                        region_back_ag_arenas,
                    )
                    push_state -= 1
                next_push_state_by_region_family[int(family_idx)] = int(state_i) - 1

        states_evaluated += 1
        touched_count = 0
        pair_stamp_value += 1
        for family_idx in range(int(family_count)):
            base = int(seg_off[int(family_idx)])
            fcount = int(front_len[int(family_idx)])
            if fcount > 0:
                touched_count, generated_count = _numba_touch_packet_points_for_state(
                    front_ag_arenas[int(family_idx)],
                    int(front_ag_start[base + fcount - 1]),
                    int(front_ag_end[base + fcount - 1]),
                    int(state_i),
                    int(pair_mod),
                    int(pair_stamp_value),
                    pair_stamp,
                    best_fever_by_pair,
                    touched_pair,
                    int(touched_count),
                )
                generated_surfaces += int(generated_count)
            bcount = int(back_len[int(family_idx)])
            if bcount > 0:
                touched_count, generated_count = _numba_touch_packet_points_for_state(
                    back_ag_arenas[int(family_idx)],
                    int(back_ag_start[base + bcount - 1]),
                    int(back_ag_end[base + bcount - 1]),
                    int(state_i),
                    int(pair_mod),
                    int(pair_stamp_value),
                    pair_stamp,
                    best_fever_by_pair,
                    touched_pair,
                    int(touched_count),
                )
                generated_surfaces += int(generated_count)

        if int(use_forced_great_timing_i) != 0:
            for family_idx in range(int(region_family_count)):
                base = int(region_seg_off[int(family_idx)])
                fcount = int(region_front_len[int(family_idx)])
                if fcount > 0:
                    touched_count, generated_count = _numba_touch_packet_points_for_state(
                        region_front_ag_arenas[int(family_idx)],
                        int(region_front_ag_start[base + fcount - 1]),
                        int(region_front_ag_end[base + fcount - 1]),
                        int(state_i),
                        int(pair_mod),
                        int(pair_stamp_value),
                        pair_stamp,
                        best_fever_by_pair,
                        touched_pair,
                        int(touched_count),
                    )
                    generated_surfaces += int(generated_count)
                bcount = int(region_back_len[int(family_idx)])
                if bcount > 0:
                    touched_count, generated_count = _numba_touch_packet_points_for_state(
                        region_back_ag_arenas[int(family_idx)],
                        int(region_back_ag_start[base + bcount - 1]),
                        int(region_back_ag_end[base + bcount - 1]),
                        int(state_i),
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
            reduce_values, frontier_len = _numba_reduce_touched_body_pairs(
                int(pair_mod),
                touched_pair,
                int(touched_count),
                best_fever_by_pair,
                bit_values,
                bit_stamps,
                int(bit_stamp_value),
                reduce_values,
            )
            body_values, body_cursor = _numba_store_body_tail_frontier(
                body_values,
                body_starts,
                body_counts,
                int(state_i),
                int(body_cursor),
                reduce_values,
                int(frontier_len),
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
    region_action_count: int,
    raw_fever_fill: float,
    action_k,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    perfect_run_starts,
    perfect_run_ends,
    late_run_starts,
    late_run_ends,
    timestamps,
    candidate_high_delta_max,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
    great_floor_timestamps,
    lanes,
    prefix_perfect_hit,
    prefix_perfect_valid,
    prefix_late_hit,
    prefix_late_valid,
    timestamp_end_idx,
    perfect_end_idx,
    great_end_idx,
    great_floor_end_idx,
    capped_perfect_edge_e,
    capped_late_edge_e,
    capped_eg_perfect_e,
    capped_eg_late_e,
    real_fever_time: float,
    real_time_idx: int,
    use_forced_great_timing_i: int,
    head_filter_min: int,
    region_starts,
    region_offsets,
    region_activations,
    region_great_ends,
    region_is_greats,
    region_act_hit_ids,
    region_perfect_hit_ids,
    region_perfect_valids,
    region_hit_token_to_id,
    region_perfect_end_by_hit,
    region_great_end_by_hit,
    ws_pair_values,
    ws_pair_stamps,
    ws_pair_touched,
    ws_bit_values,
    ws_bit_stamps,
    ws_branch_a_values,
    ws_branch_a_stamps,
    ws_perfect_successor,
    ws_perfect_successor_stamps,
    ws_late_successor,
    ws_late_successor_stamps,
    successor_epoch_in: int,
    pair_epoch_in: int,
    bit_epoch_in: int,
    branch_a_epoch_in: int,
):
    reachable, max_eg_width = _numba_first_frontier_reachability_prepass(
        int(n),
        int(action_count),
        later_fill,
        first_fill,
        later_activation_forced,
        first_activation_forced,
        perfect_run_starts,
        perfect_run_ends,
        late_run_starts,
        late_run_ends,
        prefix_perfect_hit,
        prefix_perfect_valid,
        prefix_late_hit,
        prefix_late_valid,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
        float(real_fever_time),
        int(real_time_idx),
        int(use_forced_great_timing_i),
        region_starts,
        region_offsets,
        region_activations,
        region_great_ends,
        region_is_greats,
        region_act_hit_ids,
        region_perfect_hit_ids,
        region_perfect_valids,
        region_perfect_end_by_hit,
        region_great_end_by_hit,
        perfect_floor_timestamps,
        great_floor_timestamps,
        ws_perfect_successor,
        ws_perfect_successor_stamps,
        ws_late_successor,
        ws_late_successor_stamps,
        int(successor_epoch_in),
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
    # Workspace capacity guard (fail loud, never resize): the host sizes the per-thread stamp
    # workspaces to a provable song-level pair_mod bound (_song_first_frontier_pair_mod_bound).
    # If this geometry's true radix ever escaped that bound, numpy's silent slice truncation
    # below would hand the stamp loops short arrays -> out-of-bounds writes under njit. Raise
    # instead; a violation means the host bound derivation is wrong, never a recoverable state.
    branch_a_bound = (int(pair_mod) + 1) * (int(n) + 2)
    if (
        int(ws_pair_values.shape[0]) < int(pair_size)
        or int(ws_pair_stamps.shape[0]) < int(pair_size)
        or int(ws_pair_touched.shape[0]) < int(pair_size)
        or int(ws_bit_values.shape[0]) < int(pair_mod) + 1
        or int(ws_bit_stamps.shape[0]) < int(pair_mod) + 1
        or int(ws_branch_a_values.shape[0]) < int(branch_a_bound)
        or int(ws_branch_a_stamps.shape[0]) < int(branch_a_bound)
    ):
        raise ValueError(
            "FG first-frontier stamp workspace is undersized for this geometry's pair radix"
        )
    # Reused per-thread stamp-radix workspace (allocation-lifetime change only). A cell is valid
    # iff its stamp equals the current epoch, and epochs carry monotonically across calls (the
    # incoming epoch is the max stamp any earlier call wrote), so stale cells from earlier
    # geometries hold older epochs and are invisible -- the same invariant that hides stale cells
    # between consecutive states within one call. The views are sliced to this geometry's exact
    # sizes so every shape-derived bound (pair radix guard, stamped-Fenwick ascent limits,
    # branch-A out-of-bounds guard) is identical to the fresh-allocation behavior.
    best_fever_by_pair = ws_pair_values[: int(pair_size)]
    pair_stamp = ws_pair_stamps[: int(pair_size)]
    touched_pair = ws_pair_touched[: int(pair_size)]
    pair_stamp_value = int(pair_epoch_in)
    bit_values = ws_bit_values[: int(pair_mod) + 1]
    bit_stamps = ws_bit_stamps[: int(pair_mod) + 1]
    bit_stamp_value = int(bit_epoch_in)

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
        int(region_action_count),
        float(raw_fever_fill),
        action_k,
        later_fill,
        later_forced,
        later_activation_forced,
        reachable,
        int(use_forced_great_timing_i),
        timestamps,
        candidate_high_delta_max,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        perfect_floor_timestamps,
        great_floor_timestamps,
        lanes,
        region_starts,
        region_offsets,
        region_activations,
        region_great_ends,
        region_is_greats,
        region_act_hit_ids,
        region_perfect_hit_ids,
        region_perfect_valids,
        region_hit_token_to_id,
        region_perfect_end_by_hit,
        region_great_end_by_hit,
        prefix_perfect_hit,
        prefix_perfect_valid,
        prefix_late_hit,
        prefix_late_valid,
        timestamp_end_idx,
        perfect_end_idx,
        great_end_idx,
        great_floor_end_idx,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
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
    # Flat head-state store: retained per-state head frontiers live in one grow-doubling
    # (cap, 7) uint64 arena addressed by a state -> (start, count) CSR. Rows are written in the
    # envelope filter's retained order (the order the retired per-state typed Lists held), and a
    # state's rows are final before any earlier state composes against them (states run
    # descending). Unreachable states keep count 0 (the retired empty Lists).
    head_pool = np.empty((256, 7), dtype=np.uint64)
    head_pool_cursor = 0
    head_state_start = np.zeros(max(1, int(head_limit)), dtype=np.int64)
    head_state_count = np.zeros(max(1, int(head_limit)), dtype=np.int64)
    # Region-2 same-end bucket scratch, reused across every _numba_emit_region2_head_edges call
    # of this build: chained node store + per-end head/tail tables + first-seen end order. The
    # emit drain resets every touched end to -1, so no per-call clearing is needed.
    region_node_surface = np.empty((64, 7), dtype=np.uint64)
    region_node_next = np.empty(64, dtype=np.int64)
    region_bucket_head = np.full(int(n) + 2, -1, dtype=np.int64)
    region_bucket_tail = np.full(int(n) + 2, -1, dtype=np.int64)
    region_pending_ends = np.empty(int(n) + 2, dtype=np.int64)

    for state_i in range(head_limit - 1, -1, -1):
        if not reachable[state_i]:
            continue
        states_evaluated += 1
        generated = List.empty_list(_NUMBA_SURFACE_TYPE)
        generated_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
        generated_seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
        generated_score_matrix_holder = List.empty_list(_NUMBA_HEAD_SCORE_MATRIX_TYPE)
        generated_score_matrix_count = np.zeros(1, dtype=np.int64)
        generated_count = 0
        bounded_mode = 0
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        prev_activation_prefix = -1
        for action_idx in range(int(action_count)):
            fill = int(later_fill[int(action_idx)])
            forced_start = int(state_i) + 1
            activation = int(state_i) + int(fill)
            if int(activation) >= int(n):
                break
            if int(activation) < int(forced_start):
                continue
            forced_count = int(later_forced[int(action_idx)])
            perfect_hit = float(prefix_perfect_hit[int(activation)])
            perfect_valid = int(prefix_perfect_valid[int(activation)])
            # forced_count < 0 = region-3 sentinel from the compaction: the forced run would
            # swallow or pre-cross the Perfect activation (record 16.28 follow-up); the normal
            # edge (and its early-Great extension) must not exist. Late-activation variants gate
            # separately on their own sentinel.
            if int(perfect_valid) == 0 or int(forced_count) < 0:
                edge_e = -1
            else:
                edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(activation)])
            if int(edge_e) >= 0 and int(use_forced_great_timing_i) == 0:
                band_lo = _numba_base_perfect_end_band_lo(
                    int(n),
                    int(activation),
                    float(real_fever_time),
                    perfect_floor_timestamps,
                )
                for perfect_end in range(int(band_lo), int(edge_e) + 1):
                    if not _numba_base_perfect_end_is_reachable(
                        int(n), int(band_lo), int(perfect_end), perfect_floor_timestamps
                    ):
                        continue
                    edge = _numba_pack_edge(
                        int(n),
                        int(activation),
                        int(perfect_end),
                        int(forced_start),
                        min(int(n), int(forced_start) + int(forced_count)),
                        -1,
                    )
                    generated, generated_scores, added, bounded_mode = (
                        _numba_append_head_generated_candidate(
                            generated,
                            generated_scores,
                            generated_seen,
                            generated_score_matrix_holder,
                            generated_score_matrix_count,
                            edge,
                            int(perfect_end),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            int(state_i),
                            int(head_limit),
                            int(head_filter_min),
                            int(bounded_mode),
                        )
                    )
                    generated_count += int(added)
            elif (
                int(edge_e) >= 0
                and (
                    int(fill) != int(prev_fill)
                    or int(edge_e) != int(prev_edge_e)
                )
            ):
                prev_fill = int(fill)
                prev_edge_e = int(edge_e)
                edge = _numba_pack_edge(
                    int(n),
                    int(activation),
                    int(edge_e),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(forced_count)),
                    -1,
                )
                generated, generated_scores, added, bounded_mode = (
                    _numba_append_head_generated_candidate(
                        generated,
                        generated_scores,
                        generated_seen,
                        generated_score_matrix_holder,
                        generated_score_matrix_count,
                        edge,
                        int(edge_e),
                        body_values,
                        body_starts,
                        body_counts,
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        int(state_i),
                        int(head_limit),
                        int(head_filter_min),
                        int(bounded_mode),
                    )
                )
                generated_count += int(added)
                # Issue #44: early-Great extension of the Perfect-activation fever section. Each
                # end e in (edge_e, eg_e] adds the tail [edge_e, e) as fever-greats.
                generated, generated_scores, added, bounded_mode = (
                    _numba_emit_early_great_edges(
                        generated,
                        generated_scores,
                        generated_seen,
                        generated_score_matrix_holder,
                        generated_score_matrix_count,
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
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        int(state_i),
                        int(head_limit),
                        int(head_filter_min),
                        int(bounded_mode),
                    )
                )
                generated_count += int(added)
            prefix_forced = int(later_activation_forced[int(action_idx)])
            activation_hit = 0.0
            activation_e = -1
            if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
                activation_hit = float(prefix_late_hit[int(activation)])
                activation_valid = int(prefix_late_valid[int(activation)])
                if int(activation_valid) != 0:
                    activation_e = int(capped_late_edge_e[int(real_time_idx), int(activation)])
            if _numba_late_edge_extends(
                int(edge_e),
                int(activation_e),
                int(capped_eg_late_e[int(real_time_idx), int(activation)]),
                int(capped_eg_perfect_e[int(real_time_idx), int(activation)]),
            ):
                if (
                    int(fill) == int(prev_activation_fill)
                    and int(activation_e) == int(prev_activation_e)
                    and int(prefix_forced) == int(prev_activation_prefix)
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
                generated, generated_scores, added, bounded_mode = (
                    _numba_append_head_generated_candidate(
                        generated,
                        generated_scores,
                        generated_seen,
                        generated_score_matrix_holder,
                        generated_score_matrix_count,
                        activation_edge,
                        int(activation_e),
                        body_values,
                        body_starts,
                        body_counts,
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        int(state_i),
                        int(head_limit),
                        int(head_filter_min),
                        int(bounded_mode),
                    )
                )
                generated_count += int(added)
                # Issue #44: early-Great extension of the late-Great-activation fever section.
                generated, generated_scores, added, bounded_mode = (
                    _numba_emit_early_great_edges(
                        generated,
                        generated_scores,
                        generated_seen,
                        generated_score_matrix_holder,
                        generated_score_matrix_count,
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
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        int(state_i),
                        int(head_limit),
                        int(head_filter_min),
                        int(bounded_mode),
                    )
                )
                generated_count += int(added)
        generated, generated_scores, added, bounded_mode, region_node_surface, region_node_next = (
            _numba_emit_region2_head_edges(
                generated,
                generated_scores,
                generated_seen,
                generated_score_matrix_holder,
                generated_score_matrix_count,
                region_node_surface,
                region_node_next,
                region_bucket_head,
                region_bucket_tail,
                region_pending_ends,
                int(n),
                int(state_i) + 1,
                region_starts,
                region_offsets,
                region_activations,
                region_great_ends,
                region_is_greats,
                region_act_hit_ids,
                region_perfect_hit_ids,
                region_perfect_valids,
                region_perfect_end_by_hit,
                region_great_end_by_hit,
                int(use_forced_great_timing_i),
                body_values,
                body_starts,
                body_counts,
                head_pool,
                head_state_start,
                head_state_count,
                int(head_limit),
                int(state_i),
                int(head_limit),
                int(head_filter_min),
                int(bounded_mode),
            )
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
        head_pool = _numba_u64_rows_ensure(head_pool, int(head_pool_cursor), len(frontier))
        head_state_start[int(state_i)] = int(head_pool_cursor)
        head_state_count[int(state_i)] = len(frontier)
        for frontier_idx in range(len(frontier)):
            surface = frontier[frontier_idx]
            pool_row = int(head_pool_cursor) + int(frontier_idx)
            head_pool[pool_row, 0] = surface[0]
            head_pool[pool_row, 1] = surface[1]
            head_pool[pool_row, 2] = surface[2]
            head_pool[pool_row, 3] = surface[3]
            head_pool[pool_row, 4] = surface[4]
            head_pool[pool_row, 5] = surface[5]
            head_pool[pool_row, 6] = surface[6]
        head_pool_cursor += len(frontier)
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)

    first_generated_count = 0
    first_frontier = List.empty_list(_NUMBA_SURFACE_TYPE)
    first_region_generated = List.empty_list(_NUMBA_SURFACE_TYPE)
    first_region_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
    first_region_seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
    first_region_score_matrix_holder = List.empty_list(_NUMBA_HEAD_SCORE_MATRIX_TYPE)
    first_region_score_matrix_count = np.zeros(1, dtype=np.int64)
    first_region_bounded = 0
    # Branch-A workspace epoch: consumed only by the first-fill>=100 branch below; unchanged
    # (and its stamp array untouched) when that branch is not taken.
    branch_a_epoch_out = int(branch_a_epoch_in)
    if (
        int(use_forced_great_timing_i) != 0
        and int(action_count) > 0
        and int(first_fill[0]) >= 100
    ):
        first_edge_e_by_action = np.empty(int(action_count), dtype=np.int32)
        first_normal_head_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_e_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_prefix_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_head_by_action = np.empty(int(action_count), dtype=np.int32)
        for action_idx in range(int(action_count)):
            fill = int(first_fill[int(action_idx)])
            forced_count = int(first_forced[int(action_idx)])
            edge_valid = 0
            if int(fill) < int(n):
                edge_valid = int(prefix_perfect_valid[int(fill)])
            edge_e = -1
            if int(edge_valid) != 0 and int(forced_count) >= 0:
                edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(fill)])
            first_edge_e_by_action[int(action_idx)] = int(edge_e)
            first_normal_head_by_action[int(action_idx)] = min(100, max(0, int(forced_count)))
            prefix_forced = int(first_activation_forced[int(action_idx)])
            activation_e = -1
            if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0 and int(fill) < int(n):
                activation_valid = int(prefix_late_valid[int(fill)])
                if int(activation_valid) != 0:
                    activation_e = int(capped_late_edge_e[int(real_time_idx), int(fill)])
            first_activation_e_by_action[int(action_idx)] = int(activation_e)
            first_activation_prefix_by_action[int(action_idx)] = int(prefix_forced)
            first_activation_head_by_action[int(action_idx)] = min(100, max(0, int(prefix_forced)))
        branch_a_width = int(n) + 2
        branch_a_size = (int(pair_mod) + 1) * int(branch_a_width)
        # Branch-A keeps ONE epoch for the whole call (the stamped Fenwick deliberately
        # accumulates across all 101 head_great_count buckets), so the fresh in-call epoch is
        # incoming+1: strictly above every stamp any earlier call wrote, exactly like the
        # fresh-zeroed arrays' constant stamp 1 sat strictly above the zeroed stamps.
        branch_a_values = ws_branch_a_values[: int(branch_a_size)]
        branch_a_stamps = ws_branch_a_stamps[: int(branch_a_size)]
        branch_a_epoch_out = int(branch_a_epoch_in) + 1
        branch_a_stamp = int(branch_a_epoch_out)
        # Reusable output buffer for the fused per-bucket reduce+hull (grow-doubling, rewritten
        # from row 0 each head_great_count bucket; rows are consumed before the next bucket).
        first_reduce_values = np.empty((1024, 3), dtype=np.uint64)
        normal_bucket_offsets = np.zeros(102, dtype=np.int32)
        activation_bucket_offsets = np.zeros(102, dtype=np.int32)
        for action_idx in range(int(action_count)):
            edge_e = int(first_edge_e_by_action[int(action_idx)])
            if int(edge_e) >= 100:
                hgc = int(first_normal_head_by_action[int(action_idx)])
                normal_bucket_offsets[int(hgc) + 1] += 1
            activation_e = int(first_activation_e_by_action[int(action_idx)])
            # activation_e >= 100 guards the table lookups: it implies fill < n and that both
            # staged hits were the prefix-table values (the `and` short-circuits otherwise).
            if int(activation_e) >= 100 and _numba_late_edge_extends(
                int(edge_e),
                int(activation_e),
                int(capped_eg_late_e[int(real_time_idx), int(first_fill[int(action_idx)])]),
                int(capped_eg_perfect_e[int(real_time_idx), int(first_fill[int(action_idx)])]),
            ):
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
            if int(activation_e) >= 100 and _numba_late_edge_extends(
                int(edge_e),
                int(activation_e),
                int(capped_eg_late_e[int(real_time_idx), int(first_fill[int(action_idx)])]),
                int(capped_eg_perfect_e[int(real_time_idx), int(first_fill[int(action_idx)])]),
            ):
                hgc = int(first_activation_head_by_action[int(action_idx)])
                pos = int(activation_bucket_offsets[int(hgc)]) + int(activation_bucket_write[int(hgc)])
                activation_actions_by_head[int(pos)] = int(action_idx)
                activation_bucket_write[int(hgc)] += 1
        for head_great_count in range(101):
            touched_count = 0
            pair_stamp_value += 1
            prev_fill = -1
            prev_edge_e = -1
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
                if (
                    int(fill) != int(prev_fill)
                    or int(edge_e) != int(prev_edge_e)
                ):
                    prev_fill = int(fill)
                    prev_edge_e = int(edge_e)
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
                    # unchanged -> same bucket). Bucket membership (edge_e >= 100) proves the
                    # staged hit was prefix_perfect_hit[fill] -> the capped table is exact.
                    eg_e = int(capped_eg_perfect_e[int(real_time_idx), int(fill)])
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
                if (
                    int(fill) == int(prev_activation_fill)
                    and int(activation_e) == int(prev_activation_e)
                    and int(prefix_forced) == int(prev_activation_prefix)
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
                # Bucket membership (activation_e >= 100) proves the staged hit was
                # prefix_late_hit[fill] -> the capped table is exact.
                eg_e_late = int(capped_eg_late_e[int(real_time_idx), int(fill)])
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
            first_reduce_values, body_frontier_len = _numba_reduce_touched_body_pairs(
                int(pair_mod),
                touched_pair,
                int(touched_count),
                best_fever_by_pair,
                bit_values,
                bit_stamps,
                int(bit_stamp_value),
                first_reduce_values,
            )
            for body_idx in range(int(body_frontier_len)):
                _numba_append_branch_a_body_prefix_surface(
                    first_frontier,
                    int(head_great_count),
                    first_reduce_values[int(body_idx), 0],
                    first_reduce_values[int(body_idx), 1],
                    first_reduce_values[int(body_idx), 2],
                    branch_a_values,
                    branch_a_stamps,
                    int(branch_a_stamp),
                    int(branch_a_width),
                )
        first_region_generated, first_region_scores, added, first_region_bounded, region_node_surface, region_node_next = (
            _numba_emit_region2_head_edges(
                first_region_generated,
                first_region_scores,
                first_region_seen,
                first_region_score_matrix_holder,
                first_region_score_matrix_count,
                region_node_surface,
                region_node_next,
                region_bucket_head,
                region_bucket_tail,
                region_pending_ends,
                int(n),
                0,
                region_starts,
                region_offsets,
                region_activations,
                region_great_ends,
                region_is_greats,
                region_act_hit_ids,
                region_perfect_hit_ids,
                region_perfect_valids,
                region_perfect_end_by_hit,
                region_great_end_by_hit,
                int(use_forced_great_timing_i),
                body_values,
                body_starts,
                body_counts,
                head_pool,
                head_state_start,
                head_state_count,
                int(head_limit),
                0,
                int(head_limit),
                int(head_filter_min),
                int(first_region_bounded),
            )
        )
        first_generated_count += int(added)
    else:
        first_generated = List.empty_list(_NUMBA_SURFACE_TYPE)
        first_generated_scores = List.empty_list(_NUMBA_HEAD_SCORES_TYPE)
        first_generated_seen = Dict.empty(_NUMBA_SURFACE_TYPE, types.uint8)
        first_generated_score_matrix_holder = List.empty_list(_NUMBA_HEAD_SCORE_MATRIX_TYPE)
        first_generated_score_matrix_count = np.zeros(1, dtype=np.int64)
        first_bounded_mode = 0
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        prev_activation_prefix = -1
        for action_idx in range(int(action_count)):
            fill = int(first_fill[int(action_idx)])
            if int(fill) >= int(n):
                break
            forced_count = int(first_forced[int(action_idx)])
            perfect_hit = float(prefix_perfect_hit[int(fill)])
            perfect_valid = int(prefix_perfect_valid[int(fill)])
            if int(perfect_valid) == 0 or int(forced_count) < 0:
                edge_e = -1
            else:
                edge_e = int(capped_perfect_edge_e[int(real_time_idx), int(fill)])
            if int(edge_e) >= 0 and int(use_forced_great_timing_i) == 0:
                band_lo = _numba_base_perfect_end_band_lo(
                    int(n),
                    int(fill),
                    float(real_fever_time),
                    perfect_floor_timestamps,
                )
                for perfect_end in range(int(band_lo), int(edge_e) + 1):
                    if not _numba_base_perfect_end_is_reachable(
                        int(n), int(band_lo), int(perfect_end), perfect_floor_timestamps
                    ):
                        continue
                    edge = _numba_pack_edge(
                        int(n),
                        int(fill),
                        int(perfect_end),
                        0,
                        min(int(n), int(forced_count)),
                        -1,
                    )
                    first_generated, first_generated_scores, added, first_bounded_mode = (
                        _numba_append_head_generated_candidate(
                            first_generated,
                            first_generated_scores,
                            first_generated_seen,
                            first_generated_score_matrix_holder,
                            first_generated_score_matrix_count,
                            edge,
                            int(perfect_end),
                            body_values,
                            body_starts,
                            body_counts,
                            head_pool,
                            head_state_start,
                            head_state_count,
                            int(head_limit),
                            0,
                            int(head_limit),
                            int(head_filter_min),
                            int(first_bounded_mode),
                        )
                    )
                    first_generated_count += int(added)
            elif (
                int(edge_e) >= 0
                and (
                    int(fill) != int(prev_fill)
                    or int(edge_e) != int(prev_edge_e)
                )
            ):
                prev_fill = int(fill)
                prev_edge_e = int(edge_e)
                edge = _numba_pack_edge(
                    int(n),
                    int(fill),
                    int(edge_e),
                    0,
                    min(int(n), int(forced_count)),
                    -1,
                )
                first_generated, first_generated_scores, added, first_bounded_mode = (
                    _numba_append_head_generated_candidate(
                        first_generated,
                        first_generated_scores,
                        first_generated_seen,
                        first_generated_score_matrix_holder,
                        first_generated_score_matrix_count,
                        edge,
                        int(edge_e),
                        body_values,
                        body_starts,
                        body_counts,
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        0,
                        int(head_limit),
                        int(head_filter_min),
                        int(first_bounded_mode),
                    )
                )
                first_generated_count += int(added)
                # Issue #44: early-Great extension (first section, head activation).
                first_generated, first_generated_scores, added, first_bounded_mode = (
                    _numba_emit_early_great_edges(
                        first_generated,
                        first_generated_scores,
                        first_generated_seen,
                        first_generated_score_matrix_holder,
                        first_generated_score_matrix_count,
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
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        0,
                        int(head_limit),
                        int(head_filter_min),
                        int(first_bounded_mode),
                    )
                )
                first_generated_count += int(added)
            prefix_forced = int(first_activation_forced[int(action_idx)])
            activation_hit = 0.0
            activation_e = -1
            if int(use_forced_great_timing_i) != 0 and int(prefix_forced) >= 0:
                activation_hit = float(prefix_late_hit[int(fill)])
                activation_valid = int(prefix_late_valid[int(fill)])
                if int(activation_valid) != 0:
                    activation_e = int(capped_late_edge_e[int(real_time_idx), int(fill)])
            if _numba_late_edge_extends(
                int(edge_e),
                int(activation_e),
                int(capped_eg_late_e[int(real_time_idx), int(fill)]),
                int(capped_eg_perfect_e[int(real_time_idx), int(fill)]),
            ):
                if (
                    int(fill) == int(prev_activation_fill)
                    and int(activation_e) == int(prev_activation_e)
                    and int(prefix_forced) == int(prev_activation_prefix)
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
                first_generated, first_generated_scores, added, first_bounded_mode = (
                    _numba_append_head_generated_candidate(
                        first_generated,
                        first_generated_scores,
                        first_generated_seen,
                        first_generated_score_matrix_holder,
                        first_generated_score_matrix_count,
                        activation_edge,
                        int(activation_e),
                        body_values,
                        body_starts,
                        body_counts,
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        0,
                        int(head_limit),
                        int(head_filter_min),
                        int(first_bounded_mode),
                    )
                )
                first_generated_count += int(added)
                # Issue #44: early-Great extension (first section, head late-Great activation).
                first_generated, first_generated_scores, added, first_bounded_mode = (
                    _numba_emit_early_great_edges(
                        first_generated,
                        first_generated_scores,
                        first_generated_seen,
                        first_generated_score_matrix_holder,
                        first_generated_score_matrix_count,
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
                        head_pool,
                        head_state_start,
                        head_state_count,
                        int(head_limit),
                        0,
                        int(head_limit),
                        int(head_filter_min),
                        int(first_bounded_mode),
                    )
                )
                first_generated_count += int(added)
        first_generated, first_generated_scores, added, first_bounded_mode, region_node_surface, region_node_next = (
            _numba_emit_region2_head_edges(
                first_generated,
                first_generated_scores,
                first_generated_seen,
                first_generated_score_matrix_holder,
                first_generated_score_matrix_count,
                region_node_surface,
                region_node_next,
                region_bucket_head,
                region_bucket_tail,
                region_pending_ends,
                int(n),
                0,
                region_starts,
                region_offsets,
                region_activations,
                region_great_ends,
                region_is_greats,
                region_act_hit_ids,
                region_perfect_hit_ids,
                region_perfect_valids,
                region_perfect_end_by_hit,
                region_great_end_by_hit,
                int(use_forced_great_timing_i),
                body_values,
                body_starts,
                body_counts,
                head_pool,
                head_state_start,
                head_state_count,
                int(head_limit),
                0,
                int(head_limit),
                int(head_filter_min),
                int(first_bounded_mode),
            )
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
            _numba_reduce_pattern_runs(first_region_generated),
            0,
            int(head_limit),
            int(head_filter_min),
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
    return (
        out,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        int(pair_stamp_value),
        int(bit_stamp_value),
        int(branch_a_epoch_out),
    )
