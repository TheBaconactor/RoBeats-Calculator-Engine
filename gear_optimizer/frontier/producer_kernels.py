from collections import namedtuple

import numpy as np
from numba import njit

# The tables a candidate append reads: the body-tail surface arrays and the head-state frontier arena (rows in
# `head_pool`, addressed per state by head_state_start / head_state_count) for the first `head_limit` states.
HeadTables = namedtuple(
    "HeadTables",
    ["body_values", "body_starts", "body_counts", "head_pool", "head_state_start", "head_state_count", "head_limit"],
)
# The first-frontier build's action-region tables (per region, and per song hit token), passed together.
RegionTables = namedtuple(
    "RegionTables",
    [
        "region_starts",
        "region_offsets",
        "region_activations",
        "region_great_ends",
        "region_is_greats",
        "region_act_hit_ids",
        "region_perfect_hit_ids",
        "region_perfect_valids",
        "region_perfect_end_by_hit",
        "region_great_end_by_hit",
    ],
)
# One packet queue's back-segment arrays (alpha, packet offsets, Great-activation bounds, lengths, arenas).
# The Perfect / Great floor and candidate hit times of every note and its earliest planned late-Great hit (the
# reachability and region-core checks).

HitTimes = namedtuple(
    "HitTimes",
    [
        "perfect_floor_timestamps",
        "perfect_candidate_timestamps",
        "great_floor_timestamps",
        "great_candidate_timestamps",
        "late_great_floor_timestamps",
    ],
)
# One fever time's per-activation tables: each note's latest reachable Perfect / late-Great activation hit (valid where
# `*_valid` != 0), the window ends those hits reach on the Perfect floor (`perfect_e`, `late_e`) and on the
# early-Great floor (`eg_perfect_e`, `eg_late_e`), clamped to (activation, n], and the earliest ends a Perfect /
# late-Great activation can exit at (`perfect_exit_e`, `late_exit_e`; its ends are every e from there to `perfect_e` /
# `late_e`).
ActivationEnds = namedtuple(
    "ActivationEnds",
    [
        "perfect_hit",
        "perfect_valid",
        "late_hit",
        "late_valid",
        "perfect_e",
        "late_e",
        "eg_perfect_e",
        "eg_late_e",
        "perfect_exit_e",
        "late_exit_e",
    ],
)
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

# Song tokens ``kind * n + note_index`` name every value activation-hit selection can return (chart / Perfect /
# Great / capped Perfect / capped Great); the song-wide endpoint tables are indexed by them directly.
_REGION_HIT_CHART = 0
_REGION_HIT_PERFECT = 1
_REGION_HIT_GREAT = 2
_REGION_HIT_PERFECT_CAPPED = 3
_REGION_HIT_GREAT_CAPPED = 4
_EXACT_LANE_SIGNATURE_MAX_WORD_CELLS = 16_777_216


@njit(cache=True, nogil=True)
def _numba_mask_segment(start: int, end: int, offset: int) -> np.uint64:
    lo = max(start, offset)
    hi = min(end, offset + 64)
    if hi <= lo:
        return np.uint64(0)
    width = hi - lo
    if width >= 64:
        return np.uint64(0xFFFFFFFFFFFFFFFF)
    return ((np.uint64(1) << np.uint64(width)) - np.uint64(1)) << np.uint64(lo - offset)


@njit(cache=True, nogil=True)
def _numba_range_mask(start: int, end: int, n: int):
    start_i = max(0, min(min(start, n), 100))
    end_i = max(0, min(min(end, n), 100))
    return _numba_mask_segment(start_i, end_i, 0), _numba_mask_segment(start_i, end_i, 64)


@njit(cache=True, nogil=True)
def _numba_body_count(start: int, end: int, n: int) -> np.uint64:
    body_start = max(start, 100)
    body_end = min(end, n)
    if body_end <= body_start:
        return np.uint64(0)
    return np.uint64(body_end - body_start)


@njit(cache=True, nogil=True)
def _numba_body_overlap_count(
    first_start: int, first_end: int, second_start: int, second_end: int, n: int
) -> np.uint64:
    body_start = max(max(first_start, second_start), 100)
    body_end = min(min(first_end, second_end), n)
    if body_end <= body_start:
        return np.uint64(0)
    return np.uint64(body_end - body_start)


@njit(cache=True, nogil=True)
def _numba_single_head_mask(idx: int, n: int):
    idx_i = idx
    if idx_i < 0 or idx_i >= min(n, 100):
        return np.uint64(0), np.uint64(0)
    if idx_i < 64:
        return np.uint64(1) << np.uint64(idx_i), np.uint64(0)
    return np.uint64(0), np.uint64(1) << np.uint64(idx_i - 64)


@njit(cache=True, nogil=True)
def _numba_pack_edge(
    n: int, fever_start: int, fever_end: int, great_start: int, great_end: int, activation_great_idx: int
):
    fever_lo, fever_hi = _numba_range_mask(fever_start, fever_end, n)
    great_lo, great_hi = _numba_range_mask(great_start, great_end, n)
    if activation_great_idx >= 0:
        activation_lo, activation_hi = _numba_single_head_mask(activation_great_idx, n)
        great_lo = great_lo | activation_lo
        great_hi = great_hi | activation_hi
    body_great = _numba_body_count(great_start, great_end, n)
    body_fever_great = _numba_body_overlap_count(fever_start, fever_end, great_start, great_end, n)
    if (
        activation_great_idx >= max(100, fever_start)
        and activation_great_idx < min(fever_end, n)
        and (activation_great_idx < great_start or activation_great_idx >= great_end)
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
        n, fever_start, fever_end, great_start, great_end, activation_great_idx
    )
    if early_great_end > early_great_start:
        eg_lo, eg_hi = _numba_range_mask(early_great_start, early_great_end, n)
        great_lo = great_lo | eg_lo
        great_hi = great_hi | eg_hi
        eg_body = _numba_body_count(early_great_start, early_great_end, n)
        body_great = body_great + eg_body
        # The early-Great tail lies inside [fever_start, fever_end) by construction, so every
        # tail note is also a fever note -> the overlap equals the tail's body count.
        body_fever_great = body_fever_great + _numba_body_overlap_count(
            fever_start, fever_end, early_great_start, early_great_end, n
        )
    return (fever_lo, fever_hi, great_lo, great_hi, body_fever, body_great, body_fever_great)


@njit(cache=True, nogil=True)
def _numba_lower_bound_from(timestamps, value: float) -> int:
    lo = 0
    hi = timestamps.shape[0]
    needle = np.float32(value)
    while lo < hi:
        mid = (lo + hi) // 2
        if timestamps[mid] < needle:
            lo = mid + 1
        else:
            hi = mid
    return lo


@njit(cache=True, nogil=True)
def _numba_latest_activation_hit_for_contiguous_great_run(
    activation_idx: int,
    window,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    run,
    section_end: int,
    hit_hi_token: int,
):
    hit_lo, hit_hi = window
    great_start, great_count = run
    a = activation_idx
    n = min(section_end, timestamps.shape[0])
    if a < 0 or a >= n:
        return 0.0, 0, -1
    lo = hit_lo
    cap = hit_hi
    cap_token = hit_hi_token
    if lo > cap:
        return 0.0, 0, -1

    great_lo = max(0, min(great_start, n))
    great_hi = min(n, great_lo + max(0, great_count))
    for j in range(a + 1, n):
        if float(timestamps[j]) >= cap:
            break
        label_hi = great_candidate_timestamps[j] if great_lo <= j < great_hi else perfect_candidate_timestamps[j]
        capped = float(label_hi) - 1.0e-6
        if capped < cap:
            cap = capped
            in_great_run = great_lo <= j < great_hi
            kind = _REGION_HIT_GREAT_CAPPED if in_great_run else _REGION_HIT_PERFECT_CAPPED
            cap_token = kind * timestamps.shape[0] + j
        if cap < lo:
            return 0.0, 0, -1
    return cap, 1, int(cap_token)


@njit(cache=True, nogil=True)
def _numba_great_floor_extended_end_at_hit(
    n: int, activation_idx: int, hit: float, real_fever_time: float, great_floor_timestamps
) -> int:
    e = _numba_lower_bound_from(great_floor_timestamps, hit + real_fever_time)
    return _numba_clamped_end_idx(n, activation_idx, int(e))


@njit(cache=True, nogil=True)
def _numba_late_edge_extends(edge_e: int, activation_e: int, activation_eg_e: int, edge_eg_e: int) -> bool:
    """Whether the late-Great activation edge carries content the Perfect edge cannot: a strictly
    longer perfect-floor extent OR, on extent ties, a strictly longer early-Great (great-floor)
    reach -- the late hit pushes the fever end further, pulling boundary notes in as fever-Greats
    the Perfect edge's window cannot reach (record 16.33: +337.5 oracle witness). When both tie,
    skipping the late edge stays lossless (its surfaces are the Perfect edge's plus a strictly
    costlier activation Great). The two early-Great (great-floor) extended ends arrive precomputed
    (clamped, `_numba_clamped_end_idx` semantics): `activation_eg_e` at the late-Great hit,
    `edge_eg_e` at the Perfect hit. They are only read when 0 <= activation_e <= edge_e -- both
    edges valid -- so callers may pass any deterministic value on the invalid paths."""
    if activation_e < 0:
        return False
    if activation_e > edge_e:
        return True
    return activation_eg_e > edge_eg_e


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
    a = activation_idx
    n = min(section_end, timestamps.shape[0])
    if a < 0 or a >= n:
        return 0.0, 0, -1
    chart = float(timestamps[a])
    perfect = float(perfect_candidate_timestamps[a])
    lo = chart if chart < perfect else perfect
    hi = perfect if perfect > chart else chart
    return _numba_latest_activation_hit_for_contiguous_great_run(
        a,
        (lo, hi),
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        (great_start, great_count),
        n,
        (_REGION_HIT_PERFECT if perfect > chart else _REGION_HIT_CHART) * timestamps.shape[0] + a,
    )


@njit(cache=True, nogil=True)
def _numba_late_great_activation_hit_for_run(
    activation_idx: int,
    timestamps,
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    late_great_floor_timestamps,
    great_start: int,
    great_count: int,
    section_end: int,
):
    a = activation_idx
    n = min(section_end, timestamps.shape[0])
    if a < 0 or a >= n:
        return 0.0, 0, -1
    hit_lo = float(late_great_floor_timestamps[a])
    hit_hi = float(great_candidate_timestamps[a])
    return _numba_latest_activation_hit_for_contiguous_great_run(
        a,
        (hit_lo, hit_hi),
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        (great_start, great_count),
        n,
        _REGION_HIT_GREAT * timestamps.shape[0] + a,
    )


@njit(cache=True, nogil=True)
def _numba_build_prefix_activation_hit_tables(
    n: int, timestamps, perfect_candidate_timestamps, great_candidate_timestamps, late_great_floor_timestamps
):
    perfect_hit = np.zeros(n, dtype=np.float64)
    perfect_valid = np.zeros(n, dtype=np.int8)
    late_hit = np.zeros(n, dtype=np.float64)
    late_valid = np.zeros(n, dtype=np.int8)
    for activation in range(n):
        hit, valid, _token = _numba_perfect_activation_hit_for_run(
            activation, timestamps, perfect_candidate_timestamps, great_candidate_timestamps, activation, 0, n
        )
        perfect_hit[activation] = float(hit)
        perfect_valid[activation] = np.int8(valid)
        hit, valid, _token = _numba_late_great_activation_hit_for_run(
            activation,
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            late_great_floor_timestamps,
            activation,
            1,
            n,
        )
        late_hit[activation] = float(hit)
        late_valid[activation] = np.int8(valid)
    return perfect_hit, perfect_valid, late_hit, late_valid


@njit(cache=True, nogil=True)
def _numba_fill_crossing_run(start: int, great_run_start: int, k: int, fever_fill_denom: float, n: int):
    s = start
    g0 = great_run_start
    count = k
    total = n
    denom = fever_fill_denom
    run_lo = g0 if g0 > s else s
    run_hi = g0 + count if g0 + count < total else total
    if run_hi <= run_lo:
        idx = s + int(np.ceil(denom)) - 1
        if idx < total:
            return idx, 0
        return -1, 0
    g0 = run_lo
    count = run_hi - run_lo
    perfects_before = g0 - s

    idx = s + int(np.ceil(denom)) - 1
    if idx < g0:
        if idx < total:
            return idx, 0
        return -1, 0

    idx = g0 - 1 + int(np.ceil(2.0 * (denom - float(perfects_before))))
    if idx < g0 + count:
        if idx < g0:
            idx = g0
        if idx < total:
            return idx, 1
        return -1, 0

    idx = (g0 + count) - 1 + int(np.ceil(denom - float(perfects_before) - 0.5 * float(count)))
    if idx < total:
        return idx, 0
    return -1, 0


@njit(cache=True, nogil=True)
def _numba_region2_offset_for_count(start: int, count: int, fever_fill_denom: float, n: int) -> int:
    if count <= 0 or start >= n:
        return -1
    denom = fever_fill_denom
    # Let x = run_start - section_start and m = count. The activation is the m-th Great in
    # the run iff x + 0.5*(m-1) < denom <= x + 0.5*m. That half-open interval has width 0.5,
    # so it contains at most one integer x.
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    # At most one fill unit exists per chart row. This exact no-crossing case must return before
    # any float-to-integer conversion, including legal finite values above the int64 range.
    if denom > float(n):
        return -1
    lo = int(np.ceil(denom - 0.5 * float(count)))
    hi = int(np.ceil(denom - 0.5 * float(count - 1))) - 1
    if lo < 1:
        return -1
    if lo != hi:
        return -1
    if start + lo + count - 1 >= n:
        return -1
    return lo


@njit(cache=True, nogil=True)
def _numba_region2_k_scan_stop(action_count: int, fever_fill_denom: float) -> int:
    count = action_count
    denom = fever_fill_denom
    if count <= 0:
        return 0
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    # min(action_count, ceil(2*denom)+1) is already action_count above this threshold. Compare
    # before multiplication so a legal huge finite denominator cannot overflow to infinity.
    if denom >= 0.5 * float(count - 1):
        return count
    stop = int(np.ceil(2.0 * denom)) + 1
    if stop < 1:
        stop = 1
    if stop > count:
        stop = count
    return stop


@njit(cache=True, nogil=True)
def _numba_exact_surface_signature_lane_prefix_reachable(
    activation_index: int,
    activation_hit_timestamp: float,
    hit_times,
    lanes,
    section,
    run,
    activation_is_great: int,
    target,
) -> bool:
    """Exact exceptional-path test for one score-bearing prefix signature.

    The common producer witness is the global chart prefix and is certified without allocation by
    the caller.  When timing windows force a cross-lane swap, each lane still contributes one
    chart-order prefix.  This packed DP decides the exact pair ``(event count, Great count)``;
    full lane-ID equality owns identity and hashes are not involved.
    """
    section_start, section_end = section
    great_start, great_end = run
    target_event_count, target_great_count = target
    (
        perfect_floor_timestamps,
        perfect_candidate_timestamps,
        great_floor_timestamps,
        great_candidate_timestamps,
        late_great_floor_timestamps,
    ) = hit_times
    a = activation_index
    start = section_start
    end = section_end
    target_count = target_event_count
    target_great = target_great_count
    section_length = end - start
    if target_count < 0 or target_count > section_length - 1 or target_great < 0 or target_great > target_count:
        return False
    if lanes.shape[0] < end:
        raise ValueError("FG lane-prefix signature lanes are not aligned")

    word_count = (target_great + 64) // 64
    word_cells = (target_count + 1) * word_count
    if word_cells <= 0 or word_cells > int(_EXACT_LANE_SIGNATURE_MAX_WORD_CELLS):
        raise MemoryError("FG exact lane-prefix signature DP exceeds its fail-loud capacity")
    reachable = np.zeros((target_count + 1, word_count), dtype=np.uint64)
    merged = np.zeros_like(reachable)
    reachable[0, 0] = np.uint64(1)

    unique_lanes = np.empty(max(1, section_length), dtype=np.int64)
    unique_count = 0
    for note_idx in range(start, end):
        lane_id = np.int64(lanes[note_idx])
        found = False
        for lane_idx in range(unique_count):
            if unique_lanes[lane_idx] == lane_id:
                found = True
                break
        if not found:
            unique_lanes[unique_count] = lane_id
            unique_count += 1

    activation_lane = np.int64(lanes[a])
    prefix_greats = np.empty(section_length + 1, dtype=np.int32)
    h_a = np.float32(activation_hit_timestamp)
    g0 = great_start
    g1 = great_end
    for lane_idx in range(unique_count):
        lane_id = unique_lanes[lane_idx]
        note_count = 0
        minimum_count = 0
        maximum_count = -1
        activation_position = -1
        head_note_count = 0
        target_head_count = 0
        lane_clock = -np.inf
        prefix_greats[0] = np.int32(0)
        for note_idx in range(start, end):
            if np.int64(lanes[note_idx]) != lane_id:
                continue
            is_great = bool((g0 <= note_idx and note_idx < g1) or (note_idx == a and activation_is_great != 0))
            low = great_floor_timestamps[note_idx] if is_great else perfect_floor_timestamps[note_idx]
            high = great_candidate_timestamps[note_idx] if is_great else perfect_candidate_timestamps[note_idx]
            lane_clock = max(float(lane_clock), float(low))
            if lane_clock > float(high):
                raise ValueError("FG lane label windows cannot realize chart-order full combo")
            if high < h_a:
                minimum_count = note_count + 1
            if low > h_a and maximum_count < 0:
                maximum_count = note_count
            if note_idx == a:
                activation_position = note_count
            if note_idx < 100:
                head_note_count += 1
                if note_idx < a:
                    target_head_count += 1
            prefix_greats[note_count + 1] = np.int32(int(prefix_greats[note_count]) + int(is_great))
            note_count += 1
        if maximum_count < 0:
            maximum_count = note_count
        if minimum_count > maximum_count:
            return False

        option_start = minimum_count
        option_end = maximum_count
        if lane_id == activation_lane:
            if activation_position < 0:
                raise ValueError("FG activation note is absent from its exact lane")
            if not (minimum_count <= activation_position <= maximum_count):
                return False
            option_start = activation_position
            option_end = activation_position
        if target_head_count < head_note_count:
            option_start = max(option_start, target_head_count)
            option_end = min(option_end, target_head_count)
        else:
            option_start = max(option_start, target_head_count)
        if option_start > option_end:
            return False

        for count_idx in range(target_count + 1):
            for word_idx in range(word_count):
                merged[count_idx, word_idx] = np.uint64(0)
        for option_count in range(option_start, option_end + 1):
            option_great = int(prefix_greats[option_count])
            if option_count > target_count or option_great > target_great:
                continue
            word_shift = option_great // 64
            bit_shift = option_great % 64
            for prior_count in range(target_count - option_count + 1):
                output_count = prior_count + option_count
                for source_word in range(word_count):
                    bits = reachable[prior_count, source_word]
                    if bits == np.uint64(0):
                        continue
                    output_word = source_word + word_shift
                    if output_word < word_count:
                        merged[output_count, output_word] |= np.uint64(bits << np.uint64(bit_shift))
                    if bit_shift != 0 and output_word + 1 < word_count:
                        merged[output_count, output_word + 1] |= np.uint64(bits >> np.uint64(64 - bit_shift))
        temporary = reachable
        reachable = merged
        merged = temporary

    target_word = target_great // 64
    target_bit = target_great % 64
    return bool(reachable[target_count, target_word] & (np.uint64(1) << np.uint64(target_bit)))


@njit(cache=True, nogil=True)
def _numba_activation_reachable_contiguous_run(
    activation_index: int,
    activation_hit_timestamp: float,
    timestamps,
    hit_times,
    lanes,
    fever_fill_denom: float,
    bounds,
    activation_great_i: int,
) -> bool:
    section_start, section_end, great_start, great_count = bounds
    (
        perfect_floor_timestamps,
        perfect_candidate_timestamps,
        great_floor_timestamps,
        great_candidate_timestamps,
        late_great_floor_timestamps,
    ) = hit_times
    a = activation_index
    start = section_start
    end = section_end
    if start < 0 or end < start or not (start <= a < end):
        return False
    denom = fever_fill_denom
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    total = perfect_candidate_timestamps.shape[0]
    if end > total:
        return False
    if (
        timestamps.shape[0] < total
        or perfect_floor_timestamps.shape[0] < total
        or great_floor_timestamps.shape[0] < total
        or great_candidate_timestamps.shape[0] < total
        or lanes.shape[0] < total
    ):
        raise ValueError("FG activation reachability timing arrays are not aligned")
    # Every row contributes at most one fill unit, including the activation.
    if denom > float(end - start):
        return False

    g0 = great_start
    if g0 < start:
        g0 = start
    if g0 < 0:
        g0 = 0
    g1 = great_start + great_count
    if g1 > end:
        g1 = end
    if g1 < g0:
        g1 = g0

    h_a = np.float32(activation_hit_timestamp)
    activation_is_great = activation_great_i != 0 or (g0 <= a and a < g1)
    activation_low = great_floor_timestamps[a] if activation_is_great else perfect_floor_timestamps[a]
    activation_high = great_candidate_timestamps[a] if activation_is_great else perfect_candidate_timestamps[a]
    if h_a < activation_low or h_a > activation_high:
        return False

    # The producer's common witness consumes [section_start, activation) before activation. That
    # exact chart prefix is an O(1) certificate for the score-bearing signature. If its timing is
    # illegal, the exceptional DP below may replace body identities only; head identities remain
    # position-exact and body event/Great counts remain identical to the cached surface.
    preactivation_count = a - start
    great_before = max(0, min(a, g1) - max(start, g0))
    preactivation_half = 2 * preactivation_count - great_before
    activation_half = 1 if activation_is_great else 2
    fill_before = 0.5 * float(preactivation_half)
    if not (fill_before < denom and denom <= fill_before + 0.5 * float(activation_half)):
        return False

    # Both floor streams are monotone prefix maxima.  Check the last row of each constant-label
    # segment: that is necessary and sufficient for every chart-prefix event to have a legal hit no
    # later than h_a.
    chart_prefix_legal = True
    perfect_before_end = min(a, g0)
    if perfect_before_end > start and perfect_floor_timestamps[perfect_before_end - 1] > h_a:
        chart_prefix_legal = False
    great_before_start = max(start, g0)
    great_before_end = min(a, g1)
    if great_before_end > great_before_start and great_floor_timestamps[great_before_end - 1] > h_a:
        chart_prefix_legal = False
    perfect_after_run_start = max(start, g1)
    if a > perfect_after_run_start and perfect_floor_timestamps[a - 1] > h_a:
        chart_prefix_legal = False

    # Every remaining chart-order event must stay at/after the activation.  Candidate highs are
    # per-note (held-tail aware), so inspect only later notes whose chart timestamp is still before
    # h_a; once chart >= h_a, the canonical judgment windows guarantee high >= chart >= h_a.
    for j in range(a + 1, end):
        if timestamps[j] >= h_a:
            break
        is_great = g0 <= j and j < g1
        label_high = great_candidate_timestamps[j] if is_great else perfect_candidate_timestamps[j]
        if label_high < h_a:
            chart_prefix_legal = False
            break
    if bool(chart_prefix_legal):
        return True

    return bool(
        _numba_exact_surface_signature_lane_prefix_reachable(
            a,
            float(h_a),
            hit_times,
            lanes,
            (start, end),
            (g0, g1),
            int(activation_is_great),
            (preactivation_count, great_before),
        )
    )


@njit(cache=True, nogil=True)
def _numba_minimal_reachable_region_great_end(
    activation: int, section_start: int, run_start: int, raw_fever_fill: float, timestamps, hit_times, lanes, n: int
):
    (
        perfect_floor_timestamps,
        perfect_candidate_timestamps,
        great_floor_timestamps,
        great_candidate_timestamps,
        late_great_floor_timestamps,
    ) = hit_times
    a = activation
    hit_hi = great_candidate_timestamps[a]
    max_great_end = a + 1
    while max_great_end < n and perfect_candidate_timestamps[max_great_end] < hit_hi:
        max_great_end += 1
    for great_end in range(a + 1, max_great_end + 1):
        hit, valid, token = _numba_late_great_activation_hit_for_run(
            a,
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            late_great_floor_timestamps,
            run_start,
            great_end - run_start,
            n,
        )
        if int(valid) == 0:
            continue
        if _numba_activation_reachable_contiguous_run(
            a,
            float(hit),
            timestamps,
            hit_times,
            lanes,
            raw_fever_fill,
            (section_start, n, run_start, great_end - run_start),
            1,
        ):
            return great_end, int(token)
    return -1, -1


@njit(cache=True, nogil=True)
def _numba_has_shifted_head_region(section_start: int, raw_fever_fill: float) -> int:
    if section_start >= 99:
        return 0
    return 1 if int(np.ceil(raw_fever_fill)) > 1 else 0


@njit(cache=True, nogil=True)
def _numba_region_core_candidate_capacity(n: int, region_action_count: int, action_k, raw_fever_fill: float) -> int:
    """Exact count of offsets that can reach the expensive region-core producer.

    This is an allocation bound only: validity still belongs exclusively to
    ``_numba_region_run_core_for_offset``. Counting repeats the cheap offset arithmetic but never
    reconstructs semantics, and the fill pass retains the canonical section/action/offset order.
    """
    region_k_stop = _numba_region2_k_scan_stop(region_action_count, raw_fever_fill)
    denom = raw_fever_fill
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("raw_fever_fill must be finite and > 0")
    if denom > float(n):
        return 0
    shifted_sections = 0
    if int(np.ceil(raw_fever_fill)) > 1:
        shifted_sections = min(99, n + 1)
    # Every action owns the shifted-head offset in the first 99 sections. A region-2 offset is
    # independent of section_start until its final chart-boundary cutoff, so each action's count
    # is one interval length. If that offset is also 1, subtract the overlapping shifted rows.
    candidate_count = shifted_sections * region_action_count
    for action_idx in range(int(region_k_stop)):
        k = int(action_k[action_idx])
        region_offset = _numba_region2_offset_for_count(0, k, raw_fever_fill, n)
        if int(region_offset) < 1:
            continue
        section_count = max(0, n - int(region_offset) - k + 1)
        candidate_count += section_count
        if int(region_offset) == 1:
            candidate_count -= min(shifted_sections, section_count)
    maximum = (n + 1) * max(1, region_action_count) * 2
    if candidate_count > maximum:
        raise ValueError("FG region-core candidate capacity exceeds its exhaustive bound")
    return candidate_count


@njit(cache=True, nogil=True, inline="always")
def _numba_region_run_core_for_offset(
    n: int, section_start: int, offset: int, k: int, raw_fever_fill: float, timestamps, hit_times, lanes
):
    """The rt-independent core of a region-run candidate: fill crossing, minimal reachable region
    Great end, capped activation/perfect hits, and the weighted lane-aware reachability check.
    Depends on the geometry only through the fever-fill denom (never real_fever_time), so results
    are shareable across every geometry of one (raw_fever_fill, non_fever_base) group.

    Returns ``(activation, great_end, is_great, perfect_valid, activation_token,
    perfect_token, valid)``, the hits as song tokens."""
    run_start = section_start + offset
    activation, is_great = _numba_fill_crossing_run(section_start, run_start, k, raw_fever_fill, n)
    if int(activation) < 0:
        return -1, -1, 0, 0, -1, -1, 0

    if int(is_great) != 0:
        great_end, activation_token = _numba_minimal_reachable_region_great_end(
            int(activation), section_start, run_start, raw_fever_fill, timestamps, hit_times, lanes, n
        )
        if int(great_end) < 0:
            return -1, -1, 0, 0, -1, -1, 0
        perfect_hit, perfect_valid, perfect_token = _numba_perfect_activation_hit_for_run(
            int(activation),
            timestamps,
            hit_times.perfect_candidate_timestamps,
            hit_times.great_candidate_timestamps,
            run_start,
            int(great_end) - run_start,
            n,
        )
        return (int(activation), int(great_end), 1, int(perfect_valid), int(activation_token), int(perfect_token), 1)

    great_end = min(n, run_start + k)
    if int(great_end) <= run_start:
        return -1, -1, 0, 0, -1, -1, 0
    perfect_hit, perfect_valid, perfect_token = _numba_perfect_activation_hit_for_run(
        int(activation),
        timestamps,
        hit_times.perfect_candidate_timestamps,
        hit_times.great_candidate_timestamps,
        run_start,
        int(great_end) - run_start,
        n,
    )
    if int(perfect_valid) == 0:
        return -1, -1, 0, 0, -1, -1, 0
    if not _numba_activation_reachable_contiguous_run(
        int(activation),
        float(perfect_hit),
        timestamps,
        hit_times,
        lanes,
        raw_fever_fill,
        (section_start, n, run_start, int(great_end) - run_start),
        0,
    ):
        return -1, -1, 0, 0, -1, -1, 0
    return (int(activation), int(great_end), 0, 1, -1, int(perfect_token), 1)


@njit(cache=True, nogil=True, inline="always")
def _numba_region_run_edge_from_core(
    n: int, section_start: int, offset: int, core, perfect_end_by_hit, great_end_by_hit
):
    (
        core_activation,
        core_great_end,
        core_is_great,
        core_activation_hit_id,
        core_perfect_hit_id,
        core_perfect_valid,
        core_valid,
    ) = core
    if core_valid == 0:
        return -1, -1, -1, -1, -1, -1, 0
    run_start = section_start + offset
    perfect_e, perfect_eg_e = -1, -1
    if core_perfect_valid != 0:
        perfect_e = _numba_clamped_end_idx(n, core_activation, int(perfect_end_by_hit[core_perfect_hit_id]))
        perfect_eg_e = _numba_clamped_end_idx(n, core_activation, int(great_end_by_hit[core_perfect_hit_id]))
    if core_is_great == 0:
        return core_activation, int(perfect_e), run_start, core_great_end, -1, int(perfect_eg_e), 1
    activation_e = _numba_clamped_end_idx(n, core_activation, int(perfect_end_by_hit[core_activation_hit_id]))
    activation_eg_e = _numba_clamped_end_idx(n, core_activation, int(great_end_by_hit[core_activation_hit_id]))
    if int(perfect_e) >= 0 and not _numba_late_edge_extends(
        int(perfect_e), int(activation_e), int(activation_eg_e), int(perfect_eg_e)
    ):
        return -1, -1, -1, -1, -1, -1, 0
    return (core_activation, int(activation_e), run_start, core_great_end, core_activation, int(activation_eg_e), 1)


@njit(cache=True, nogil=True)
def _numba_region_run_edge_for_offset(
    where, raw_fever_fill: float, timestamps, hit_times, lanes, perfect_end_by_hit, great_end_by_hit
):
    n, section_start, offset, k = where
    core = _numba_region_run_core_for_offset(n, section_start, offset, k, raw_fever_fill, timestamps, hit_times, lanes)
    return _numba_region_run_edge_from_core(
        n,
        section_start,
        offset,
        (core[0], core[1], core[2], core[4], core[5], core[3], core[6]),
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
    if base_e < 0 or activation < 0 or activation >= n:
        return 0
    eg_e = _numba_great_floor_extended_end_at_hit(
        n, activation, activation_hit, real_fever_time, great_floor_timestamps
    )
    for e in range(base_e + 1, int(eg_e) + 1):
        reachable[e] = True
    return max(0, int(eg_e) - base_e)


@njit(cache=True, nogil=True)
def _numba_build_region_core_table(
    n: int, region_action_count: int, action_k, raw_fever_fill: float, timestamps, hit_times, lanes
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
    perfect_hit_ids, perfect_valids)`` (hit IDs are song tokens) with ``starts`` of length ``n + 2``."""
    if lanes.shape[0] != n:
        raise ValueError("FG region-core lane rows must match n")
    denom = raw_fever_fill
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("raw_fever_fill must be finite and > 0")
    if denom > float(n):
        return (
            np.zeros(n + 2, dtype=np.int64),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
            np.empty(0, dtype=np.int32),
        )
    cap = _numba_region_core_candidate_capacity(n, region_action_count, action_k, raw_fever_fill)
    starts = np.zeros(n + 2, dtype=np.int64)
    e_offset = np.empty(int(cap), dtype=np.int32)
    e_activation = np.empty(int(cap), dtype=np.int32)
    e_great_end = np.empty(int(cap), dtype=np.int32)
    e_is_great = np.empty(int(cap), dtype=np.int32)
    e_act_hit_id = np.empty(int(cap), dtype=np.int32)
    e_perfect_hit_id = np.empty(int(cap), dtype=np.int32)
    e_perfect_valid = np.empty(int(cap), dtype=np.int32)
    region_k_stop = _numba_region2_k_scan_stop(region_action_count, raw_fever_fill)
    cursor = 0
    for section_start in range(0, n + 1):
        starts[section_start] = cursor
        shifted_head_offset = 1 if _numba_has_shifted_head_region(section_start, raw_fever_fill) else -1
        for action_idx in range(region_action_count):
            k = int(action_k[action_idx])
            region_offset = -1
            if action_idx < int(region_k_stop):
                region_offset = _numba_region2_offset_for_count(section_start, k, raw_fever_fill, n)
            for offset_idx in range(2):
                if offset_idx == 0:
                    offset = int(region_offset)
                else:
                    offset = shifted_head_offset
                    if offset == int(region_offset):
                        continue
                if offset < 1:
                    continue
                (activation, great_end, is_great, perfect_valid, act_hit_id, perfect_hit_id, valid) = (
                    _numba_region_run_core_for_offset(
                        n, section_start, offset, k, raw_fever_fill, timestamps, hit_times, lanes
                    )
                )
                if int(valid) == 0:
                    continue
                if cursor >= int(cap):
                    raise ValueError("FG region-core rows exceed the producer-owned candidate capacity")
                e_offset[cursor] = offset
                e_activation[cursor] = int(activation)
                e_great_end[cursor] = int(great_end)
                e_is_great[cursor] = int(is_great)
                e_act_hit_id[cursor] = int(act_hit_id) if int(is_great) != 0 else -1
                e_perfect_hit_id[cursor] = int(perfect_hit_id) if int(perfect_valid) != 0 else -1
                e_perfect_valid[cursor] = int(perfect_valid)
                cursor += 1
    starts[n + 1] = cursor
    return (
        starts,
        e_offset[:cursor].copy(),
        e_activation[:cursor].copy(),
        e_great_end[:cursor].copy(),
        e_is_great[:cursor].copy(),
        e_act_hit_id[:cursor].copy(),
        e_perfect_hit_id[:cursor].copy(),
        e_perfect_valid[:cursor].copy(),
    )


@njit(cache=True, nogil=True)
def _numba_mark_region_entries_for_section(
    reachable, n: int, section_start: int, region, perfect_exit_e, late_exit_e
) -> int:
    """rt-finish + reachability marking for every valid region core of one section row. Returns
    the max early-Great extension width, exactly like the per-candidate marking it replaces."""
    (
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
    ) = region
    max_width = 0
    for idx in range(int(region_starts[section_start]), int(region_starts[section_start + 1])):
        activation, edge_e, _run_start, _great_end, activation_great_idx, eg_e, valid = (
            _numba_region_run_edge_from_core(
                n,
                section_start,
                int(region_offsets[idx]),
                (
                    int(region_activations[idx]),
                    int(region_great_ends[idx]),
                    int(region_is_greats[idx]),
                    int(region_act_hit_ids[idx]),
                    int(region_perfect_hit_ids[idx]),
                    int(region_perfect_valids[idx]),
                    1,
                ),
                region_perfect_end_by_hit,
                region_great_end_by_hit,
            )
        )
        if int(valid) == 0:
            continue
        # The activation can also end its fever early.
        exit_e = perfect_exit_e if int(activation_great_idx) < 0 else late_exit_e
        for end_e in range(min(int(exit_e[int(activation)]), int(edge_e)), int(eg_e) + 1):
            reachable[end_e] = True
        width = max(0, int(eg_e) - int(edge_e))
        if width > max_width:
            max_width = width
    return max_width


@njit(cache=True, nogil=True, inline="always")
def _numba_successor_find(successor, successor_stamps, successor_epoch: int, index: int) -> int:
    """Return the first live index at/after ``index`` in one stamped successor epoch."""
    root = index
    while int(successor_stamps[root]) == successor_epoch:
        root = int(successor[root])
    cursor = index
    while int(successor_stamps[cursor]) == successor_epoch:
        next_cursor = int(successor[cursor])
        successor[cursor] = root
        cursor = next_cursor
    return root


@njit(cache=True, nogil=True, inline="always")
def _numba_successor_remove(successor, successor_stamps, successor_epoch: int, index: int) -> int:
    """Remove one live index and return its next live successor."""
    next_index = _numba_successor_find(successor, successor_stamps, successor_epoch, index + 1)
    successor[index] = int(next_index)
    successor_stamps[index] = successor_epoch
    return int(next_index)


@njit(cache=True, nogil=True, inline="always")
def _numba_mark_perfect_activation_closure(
    reachable, n: int, activation: int, ends, great_floor_timestamps, real_fever_time: float
) -> int:
    if int(ends.perfect_valid[activation]) == 0:
        return 0
    edge_e = int(ends.perfect_e[activation])
    if edge_e < 0:
        return 0
    # The activation can also end its fever early (an earlier hit, the boundary notes late): every end in
    # [perfect_exit_e, edge_e] is a state.
    for end_e in range(min(int(ends.perfect_exit_e[activation]), edge_e), edge_e + 1):
        reachable[end_e] = True
    return _numba_mark_early_great_reachable_from_hit(
        reachable, n, activation, edge_e, float(ends.perfect_hit[activation]), great_floor_timestamps, real_fever_time
    )


@njit(cache=True, nogil=True, inline="always")
def _numba_mark_late_activation_closure(
    reachable, n: int, activation: int, ends, great_floor_timestamps, real_fever_time: float
) -> int:
    edge_e = -1
    edge_eg_e = 0
    if int(ends.perfect_valid[activation]) != 0:
        edge_e = int(ends.perfect_e[activation])
        edge_eg_e = int(ends.eg_perfect_e[activation])
    activation_e = -1
    activation_eg_e = 0
    if int(ends.late_valid[activation]) != 0:
        activation_e = int(ends.late_e[activation])
        activation_eg_e = int(ends.eg_late_e[activation])
    if not _numba_late_edge_extends(edge_e, activation_e, activation_eg_e, edge_eg_e):
        return 0
    # The activation can also end its fever early: every end in [late_exit_e, activation_e] is a state.
    for end_e in range(min(int(ends.late_exit_e[activation]), activation_e), activation_e + 1):
        reachable[end_e] = True
    return _numba_mark_early_great_reachable_from_hit(
        reachable,
        n,
        activation,
        activation_e,
        float(ends.late_hit[activation]),
        great_floor_timestamps,
        real_fever_time,
    )


@njit(cache=True, nogil=True)
def _numba_first_frontier_reachability_prepass(
    n: int, action_count: int, plan, runs, ends, fever, region_floor, successors
):
    """Build the exact reachable-state closure with interval successor traversal.

    The former nested scan probed every action for every reachable state even after an absolute
    activation had already been evaluated. Exact fill runs turn each state's action set into
    activation intervals; disjoint-set successors skip globally processed activations. Perfect and
    late-Great closures remain separate because only some action routes permit a late activation.
    """
    first_fill, first_activation_forced = plan
    perfect_run_starts, perfect_run_ends, late_run_starts, late_run_ends = runs
    real_fever_time, use_forced_great_timing_i = fever
    region, great_floor_timestamps = region_floor
    perfect_successor, perfect_successor_stamps, late_successor, late_successor_stamps, successor_epoch = successors
    if n < 0 or action_count < 0:
        raise ValueError("FG reachability dimensions must be nonnegative")
    if first_fill.shape[0] < action_count:
        raise ValueError("FG first-fill offsets are shorter than action_count")
    if first_activation_forced.shape[0] < action_count:
        raise ValueError("FG first activation-forced rows are shorter than action_count")
    if perfect_run_starts.shape[0] != perfect_run_ends.shape[0]:
        raise ValueError("FG Perfect fill-run arrays must align")
    if late_run_starts.shape[0] != late_run_ends.shape[0]:
        raise ValueError("FG late-Great fill-run arrays must align")
    previous_end = -2
    for run_idx in range(perfect_run_starts.shape[0]):
        run_start = int(perfect_run_starts[run_idx])
        run_end = int(perfect_run_ends[run_idx])
        if run_start < 0 or run_end < run_start or run_start <= previous_end:
            raise ValueError("FG Perfect fill runs must be nonnegative, ordered, and disjoint")
        previous_end = run_end
    previous_end = -2
    for run_idx in range(late_run_starts.shape[0]):
        run_start = int(late_run_starts[run_idx])
        run_end = int(late_run_ends[run_idx])
        if run_start < 0 or run_end < run_start or run_start <= previous_end:
            raise ValueError("FG late-Great fill runs must be nonnegative, ordered, and disjoint")
        previous_end = run_end
    if successor_epoch < 1:
        raise ValueError("FG successor epoch must be positive")
    if (
        perfect_successor.shape[0] < n + 1
        or perfect_successor_stamps.shape[0] < n + 1
        or late_successor.shape[0] < n + 1
        or late_successor_stamps.shape[0] < n + 1
    ):
        raise ValueError("FG successor workspace is shorter than n + 1")

    reachable = np.zeros(n + 1, dtype=np.bool_)
    reachable[n] = True

    # First-section actions retain their original producer order. Removing an activation from its
    # successor set is exactly the former processed-bit write, with the same Perfect/late split.
    max_eg_width = 0
    for action_idx in range(action_count):
        fill = int(first_fill[action_idx])
        if fill < 0:
            raise ValueError("FG first-fill offsets must be nonnegative")
        if fill >= n:
            continue
        if int(_numba_successor_find(perfect_successor, perfect_successor_stamps, successor_epoch, fill)) == fill:
            width = _numba_mark_perfect_activation_closure(
                reachable, n, fill, ends, great_floor_timestamps, real_fever_time
            )
            _numba_successor_remove(perfect_successor, perfect_successor_stamps, successor_epoch, fill)
            if int(width) > int(max_eg_width):
                max_eg_width = int(width)
        if (
            use_forced_great_timing_i != 0
            and int(first_activation_forced[action_idx]) >= 0
            and int(_numba_successor_find(late_successor, late_successor_stamps, successor_epoch, fill)) == fill
        ):
            width = _numba_mark_late_activation_closure(
                reachable, n, fill, ends, great_floor_timestamps, real_fever_time
            )
            _numba_successor_remove(late_successor, late_successor_stamps, successor_epoch, fill)
            if int(width) > int(max_eg_width):
                max_eg_width = int(width)

    if use_forced_great_timing_i != 0:
        max_eg_width = max(
            int(max_eg_width),
            _numba_mark_region_entries_for_section(reachable, n, 0, region, ends.perfect_exit_e, ends.late_exit_e),
        )

    for state_i in range(n):
        if not reachable[state_i]:
            continue

        for run_idx in range(perfect_run_starts.shape[0]):
            interval_start = state_i + int(perfect_run_starts[run_idx])
            if interval_start >= n:
                continue
            interval_end = min(n - 1, state_i + int(perfect_run_ends[run_idx]))
            activation = _numba_successor_find(
                perfect_successor, perfect_successor_stamps, successor_epoch, interval_start
            )
            while int(activation) <= interval_end:
                width = _numba_mark_perfect_activation_closure(
                    reachable, n, int(activation), ends, great_floor_timestamps, real_fever_time
                )
                activation = _numba_successor_remove(
                    perfect_successor, perfect_successor_stamps, successor_epoch, int(activation)
                )
                if int(width) > int(max_eg_width):
                    max_eg_width = int(width)

        if use_forced_great_timing_i != 0:
            for run_idx in range(late_run_starts.shape[0]):
                interval_start = state_i + int(late_run_starts[run_idx])
                if interval_start >= n:
                    continue
                interval_end = min(n - 1, state_i + int(late_run_ends[run_idx]))
                activation = _numba_successor_find(
                    late_successor, late_successor_stamps, successor_epoch, interval_start
                )
                while int(activation) <= interval_end:
                    width = _numba_mark_late_activation_closure(
                        reachable, n, int(activation), ends, great_floor_timestamps, real_fever_time
                    )
                    activation = _numba_successor_remove(
                        late_successor, late_successor_stamps, successor_epoch, int(activation)
                    )
                    if int(width) > int(max_eg_width):
                        max_eg_width = int(width)

            max_eg_width = max(
                int(max_eg_width),
                _numba_mark_region_entries_for_section(
                    reachable, n, state_i + 1, region, ends.perfect_exit_e, ends.late_exit_e
                ),
            )
    return reachable, int(max_eg_width)


@njit(cache=True, nogil=True)
def _numba_prefix_max_query_stamped(values, stamps, stamp: int, idx: int) -> int:
    best = -1
    cursor = idx + 1
    while cursor > 0:
        if int(stamps[cursor]) == stamp:
            value = int(values[cursor])
            if value > best:
                best = value
        cursor -= cursor & -cursor
    return best


@njit(cache=True, nogil=True)
def _numba_prefix_max_update_stamped(values, stamps, stamp: int, idx: int, value: int) -> None:
    cursor = idx + 1
    limit = values.shape[0]
    while cursor < limit:
        if int(stamps[cursor]) != stamp:
            stamps[cursor] = stamp
            values[cursor] = value
        elif value > int(values[cursor]):
            values[cursor] = value
        cursor += cursor & -cursor


@njit(cache=True, nogil=True)
def _numba_touch_body_candidate(
    edge, tail, pair_mod, pair_stamp, best_fever_by_pair, touched_pair, stamp: int, touched_count: int
) -> int:
    edge_fever, edge_great, edge_fever_great = edge
    tail_fever, tail_great, tail_fever_great = tail
    body_fever = int(edge_fever + tail_fever)
    body_great = int(edge_great + tail_great)
    body_fever_great = int(edge_fever_great + tail_fever_great)
    if body_fever_great > body_great:
        return touched_count
    normal_great = body_great - body_fever_great
    # Fail loud on radix overflow. The pack normal_great*pair_mod + body_fever_great is injective
    # ONLY while body_fever_great < pair_mod; otherwise it silently ALIASES onto a different
    # (normal_great, fever_great) cell -- a phantom surface that the decoder later materialises with
    # the wrong Great counts (it scores higher, wins, and corrupts best_fg_score / breaks trace
    # reconstruction). pair_mod is sized to this geometry's true max body_fever_great, so this must
    # never fire; raising beats silently mis-scoring.
    if body_fever_great < 0 or body_fever_great >= pair_mod:
        raise ValueError("FG response body skyline fever-great exceeded pair radix")
    pair_idx = normal_great * pair_mod + body_fever_great
    if pair_idx < 0 or pair_idx >= best_fever_by_pair.shape[0]:
        raise ValueError("FG response body skyline pair bound was too small")
    if int(pair_stamp[pair_idx]) != stamp:
        pair_stamp[pair_idx] = stamp
        best_fever_by_pair[pair_idx] = body_fever
        touched_pair[touched_count] = pair_idx
        return touched_count + 1
    if body_fever > int(best_fever_by_pair[pair_idx]):
        best_fever_by_pair[pair_idx] = body_fever
    return touched_count


# Body-tail hull: the Pareto reduce and the per-normal-Great upper-hull filter are fused into
# `_numba_reduce_touched_body_pairs`; see its docstring for the exactness and ordering proof.


# The realizable stat box (lossless head prune). The head+body score is MULTILINEAR in
# (v=base_value, c=combo_mul, f=fever_mul, g=great_base) on the realizable region (g<=v, c,f>=1, so
# every floor's max/min is resolved), and a multilinear function attains its extrema at the box
# VERTICES -- so a surface's exact dominance over the WHOLE box is decided at its 16 corners, with
# the integer floors bounded by a per-pair margin. No probe sampling. `c`/`f` are the gear's
# combo/fever-multiplier ranges (gamedata.stat_curves); `v`/`g` are a generous superset of every
# realizable base_value / great_base. assert_head_dominance_box (fg_cache) fails loud if a
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
# skipping the prune there is exact and cheap. Genuine
# cascades still cross the threshold and get pruned (preventing the exponential blow-up).
_HEAD_FILTER_MIN_SURFACES = 96


@njit(cache=True, nogil=True)
def _numba_head_surface_margin(left, right) -> float:
    """The most the score's integer floors can move the gap between two surface rows: their head-class Hamming distance
    + the body floor weight x their body-count L1 distance."""
    bw = _HEAD_DOM_BODY_FLOOR_W
    return float(
        _numba_popcount64((left[0] ^ right[0]) | (left[2] ^ right[2]))
        + _numba_popcount64((left[1] ^ right[1]) | (left[3] ^ right[3]))
        + bw
        * (
            abs(int(np.int64(left[4]) - np.int64(right[4])))
            + abs(int((np.int64(left[5]) - np.int64(left[6])) - (np.int64(right[5]) - np.int64(right[6]))))
            + abs(int(np.int64(left[6]) - np.int64(right[6])))
        )
    )


@njit(cache=True, nogil=True)
def _numba_head_basis_corner_score(basis, v, c, f, g, use_hi_c: int) -> float:
    gv = g - v
    body_dn = v * c * (f - 1.0)
    pen_n = c * gv
    pen_f = c * f * gv
    if use_hi_c == 0:
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
def _numba_head_corner_scores(rows, terms, term_of):
    """(m, 16) each surface row's relative score at the 16 corners of the _HEAD_DOM box (v, c, f, g, each low and high);
    row i's head terms are terms[term_of[i]] (_numba_head_pattern_basis's b, c, d at the low and high combo)."""
    m = rows.shape[0]
    scores = np.empty((m, 16), dtype=np.float64)
    for i in range(m):
        head = terms[term_of[i]]
        basis = (
            rows[i, 0],
            rows[i, 1],
            rows[i, 2],
            rows[i, 3],
            np.int64(rows[i, 4]),
            np.int64(rows[i, 5]) - np.int64(rows[i, 6]),
            np.int64(rows[i, 6]),
            head[0],
            head[1],
            head[2],
            head[3],
            head[4],
            head[5],
        )
        col = 0
        for v in _HEAD_DOM_V:
            for ic in range(2):
                for f in _HEAD_DOM_F:
                    for g in _HEAD_DOM_G:
                        scores[i, col] = _numba_head_basis_corner_score(basis, v, _HEAD_DOM_C[ic], f, g, ic)
                        col += 1
    return scores


@njit(cache=True, nogil=True)
def _numba_cone_kept(rows, scores):
    """The rows no other row dominates (score gap >= the pair's margin at all 16 corners), by descending corner-score
    sum. Dominance is transitive, since the margin (head-class Hamming distance + 2 x body-count L1) is a metric and
    gaps add, and a dominator's sum exceeds the dominated row's by at least 16 margins (> 0 unless the rows are
    identical). So in that order a dominated row always meets a kept dominator first, no kept row is ever evicted, and
    the kept set is exactly the non-dominated rows whatever the input order. The margin is non-negative, so the
    zero-threshold corner pre-pass rejects most pairs before the margin popcounts run."""
    m = rows.shape[0]
    sums = np.empty(m, dtype=np.float64)
    for i in range(m):
        total = 0.0
        for corner in range(16):
            total += scores[i, corner]
        sums[i] = -total
    order = np.argsort(sums)
    kept_rows = np.empty(m, dtype=np.int64)
    kept_count = 0
    for pos in range(m):
        i = order[pos]
        dominated = False
        for ki in range(kept_count):
            k = kept_rows[ki]
            if not _numba_head_scores_dominate(scores, k, i, 0.0):
                continue
            if _numba_head_scores_dominate(scores, k, i, _numba_head_surface_margin(rows[k], rows[i])):
                dominated = True
                break
        if not dominated:
            kept_rows[kept_count] = i
            kept_count += 1
    return kept_rows[:kept_count]


@njit(cache=True, nogil=True)
def _numba_head_scores_dominate(scores, left_idx: int, right_idx: int, margin: float) -> bool:
    for cc in range(16):
        if scores[left_idx, cc] - scores[right_idx, cc] < margin:
            return False
    return True


@njit(cache=True, nogil=True)
def _numba_head_envelope_filter(frontier, lo_pos, hi_pos, min_surfaces):
    """LOSSLESS prune of the head frontier to its cone-Pareto set -- the surfaces
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
    m = frontier.shape[0]
    if m <= min_surfaces:
        return frontier
    if int(hi_pos) - int(lo_pos) <= 0:
        return frontier
    # Head sums are computed once per run of rows with the same masks (same floats).
    terms = np.empty((m, 6), dtype=np.float64)
    term_of = np.empty(m, dtype=np.int64)
    runs = 0
    for i in range(m):
        fl, fh, gl, gh = frontier[i, 0], frontier[i, 1], frontier[i, 2], frontier[i, 3]
        if (
            i == 0
            or fl != frontier[i - 1, 0]
            or fh != frontier[i - 1, 1]
            or gl != frontier[i - 1, 2]
            or gh != frontier[i - 1, 3]
        ):
            head = _numba_head_pattern_basis(fl, fh, gl, gh, lo_pos, hi_pos)
            for t in range(6):
                terms[runs, t] = head[t]
            runs += 1
        term_of[i] = runs - 1
    kept_rows = _numba_cone_kept(frontier, _numba_head_corner_scores(frontier, terms, term_of))
    out = np.empty((kept_rows.shape[0], 7), dtype=np.uint64)
    for ki in range(kept_rows.shape[0]):
        out[ki] = frontier[kept_rows[ki]]
    return out


@njit(cache=True, nogil=True)
def _numba_head_pattern_basis(fl, fh, gl, gh, lo_pos: int, hi_pos: int):
    """Head-only portion of a surface's basis at the box's low and high combo, shared by every row with this mask
    pattern."""
    lo = lo_pos
    hi = hi_pos
    hlen = hi - lo
    one = np.uint64(1)
    k_lo = (_HEAD_DOM_C[0] - 1.0) / 100.0
    k_hi = (_HEAD_DOM_C[1] - 1.0) / 100.0
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
    return b_lo, c_lo_arr, d_lo, b_hi, c_hi_arr, d_hi


@njit(cache=True, nogil=True, inline="always")
def _numba_skyline_hull_push(stack, count: int, group, point, fen_values, fen_stamps, fen_stamp):
    """One candidate of a skyline with per-normal-Great upper hulls, fed in (normal Greats asc, fever Greats asc) order
    with one candidate per pair: kept iff its body fever beats every earlier candidate with fever Greats <= (stamped
    Fenwick prefix maxima), which includes the kept rows of its own normal-Great group, so a group's kept rows have
    strictly increasing body fever and its upper hull of (body fever, -fever Greats) runs incrementally on the `stack`
    rows (body fever, normal Greats, fever Greats, tag). Returns (count, group_base, group_ng)."""
    group_base, group_ng = group
    bf, ng, fg, tag = point
    if bf > _numba_prefix_max_query_stamped(fen_values, fen_stamps, fen_stamp, fg):
        if ng != group_ng:
            group_ng = ng
            group_base = count
        while count - group_base >= 2:
            cross = (stack[count - 1, 0] - stack[count - 2, 0]) * (stack[count - 2, 2] - fg) - (
                stack[count - 2, 2] - stack[count - 1, 2]
            ) * (bf - stack[count - 2, 0])
            if cross >= 0:
                count -= 1
            else:
                break
        stack[count, 0] = bf
        stack[count, 1] = ng
        stack[count, 2] = fg
        stack[count, 3] = tag
        count += 1
    _numba_prefix_max_update_stamped(fen_values, fen_stamps, fen_stamp, fg, bf)
    return count, group_base, group_ng


@njit(cache=True, nogil=True, inline="always")
def _numba_reduce_touched_body_pairs(
    pair_mod: int, touched_pair, touched_count: int, best_fever_by_pair, bit_values, bit_stamps, bit_stamp: int, stack
):
    """Fused Pareto reduce + body-tail hull filter, allocation-free.

    Emits the surviving (body_fever, normal_great, fever_great, 0) rows into the reusable grow-doubling (cap, 4)
    int64 `stack` and returns (stack, count). One pass is exact because:

    - `touched_pair[:touched_count]` holds DISTINCT pair indices (`_numba_touch_body_candidate` appends a pair_idx
      only on its first stamp-set; every touch batch bumps the stamp and resets touched_count), and nothing reads
      their insertion order afterwards, so the live slice is sorted in place.
    - Pairs are visited in ascending pair_idx = normal_great*pair_mod + fever_great, i.e. (normal_great asc,
      fever_great asc). A kept entry's body_fever strictly exceeds the stamped-Fenwick prefix max over everything
      already processed with fever_great' <= fever_great, which includes every earlier kept entry of the same
      normal_great group, so within a group kept rows have strictly increasing body_fever and the per-group upper
      hull of (body_fever, -fever_great) runs incrementally over the kept stream (_numba_skyline_hull_push; the
      finished-groups prefix of `stack` doubles as the current group's stack).
    - The Fenwick gets one update per distinct pair, in pair order (hull pops never touch it), so the carried
      bit_values/bit_stamps workspace does not depend on what the hull removes. It spans the batch's fever-Great
      range only.

    For a fixed (PP/combo/fever/color) cell the body score is LINEAR in the three body counts:
    `A*body_fever - pnp*normal_great - pfp*fever_great` with A,pnp,pfp >= 0. The early-Great
    extension adds points at CONSTANT normal_great, so within each normal_great level the useful
    set is the 2-D upper hull in (body_fever, -fever_great); pruning to it is bit-exact for every
    cone direction, shift-invariant, and composition-safe as the DP adds section counts."""
    if touched_count <= 0:
        return stack, 0
    touched_pair[:touched_count].sort()
    stack = _numba_i64_rows_ensure(stack, 0, touched_count)
    max_fever_great = 0
    for idx in range(touched_count):
        max_fever_great = max(max_fever_great, int(touched_pair[idx]) % pair_mod)
    bit_values = bit_values[: max_fever_great + 2]
    bit_stamps = bit_stamps[: max_fever_great + 2]
    count = 0
    group_base = 0
    group_ng = -1
    for idx in range(touched_count):
        pair_idx = int(touched_pair[idx])
        normal_great = pair_idx // pair_mod
        count, group_base, group_ng = _numba_skyline_hull_push(
            stack,
            count,
            (group_base, group_ng),
            (
                np.int64(best_fever_by_pair[pair_idx]),
                np.int64(normal_great),
                np.int64(pair_idx - normal_great * pair_mod),
                0,
            ),
            bit_values,
            bit_stamps,
            bit_stamp,
        )
    return stack, int(count)


@njit(cache=True, nogil=True)
def _numba_packet_points_append(buf, base: int, write: int, cf: int, cn: int, cq: int) -> int:
    """Packet-point Pareto insert: a dominated candidate is dropped, the points it dominates are compacted out in
    order, and the candidate is appended last. The working set is
    buf rows [base, write); returns the new write cursor."""
    for idx in range(base, write):
        if buf[idx, 0] >= cf and buf[idx, 1] <= cn and buf[idx, 2] <= cq:
            return write

    out = base
    for idx in range(base, write):
        kf = buf[idx, 0]
        kn = buf[idx, 1]
        kq = buf[idx, 2]
        if not (cf >= kf and cn <= kn and cq <= kq):
            if out != idx:
                buf[out, 0] = kf
                buf[out, 1] = kn
                buf[out, 2] = kq
            out += 1
    buf[out, 0] = np.int64(cf)
    buf[out, 1] = np.int64(cn)
    buf[out, 2] = np.int64(cq)
    return out + 1


@njit(cache=True, nogil=True)
def _numba_packet_points_skyline(buf, start: int, end: int) -> int:
    """Reduce rows [start, end) to their Pareto skyline in place (the dominance of `_numba_packet_points_append`); returns
    the new end. A packet spanning several fever ends can hold points one end dominates with another's, and the queue's
    unions keep a packet verbatim when it is the only operand."""
    kept = start
    for idx in range(start, end):
        cf = buf[idx, 0]
        cn = buf[idx, 1]
        cq = buf[idx, 2]
        kept = _numba_packet_points_append(buf, start, int(kept), int(cf), int(cn), int(cq))
    return int(kept)


@njit(cache=True, nogil=True)
def _numba_build_packet_families(action_count: int, later_fill, later_forced, later_activation_forced):
    cap = max(1, action_count * 2)
    family_mode = np.empty(cap, dtype=np.int32)
    family_defect = np.empty(cap, dtype=np.int32)
    family_start = np.empty(cap, dtype=np.int32)
    family_end = np.empty(cap, dtype=np.int32)
    family_count = 0

    prev_defect = 0
    prev_offset = -1000000000
    for action_idx in range(action_count):
        offset = int(later_fill[action_idx])
        defect = int(later_forced[action_idx]) - (2 * offset)
        if (
            family_count > 0
            and int(family_mode[family_count - 1]) == 0
            and prev_defect == defect
            and offset == prev_offset + 1
        ):
            family_end[family_count - 1] = offset
        else:
            family_mode[family_count] = 0
            family_defect[family_count] = defect
            family_start[family_count] = offset
            family_end[family_count] = offset
            family_count += 1
        prev_defect = defect
        prev_offset = offset

    prev_defect = 0
    prev_offset = -1000000000
    have_late = False
    for action_idx in range(action_count):
        offset = int(later_fill[action_idx])
        prefix = int(later_activation_forced[action_idx])
        if prefix < 0:
            continue
        defect = prefix - (2 * offset)
        if (
            bool(have_late)
            and family_count > 0
            and int(family_mode[family_count - 1]) == 1
            and prev_defect == defect
            and offset == prev_offset + 1
        ):
            family_end[family_count - 1] = offset
        else:
            family_mode[family_count] = 1
            family_defect[family_count] = defect
            family_start[family_count] = offset
            family_end[family_count] = offset
            family_count += 1
        prev_defect = defect
        prev_offset = offset
        have_late = True

    return family_count, family_mode, family_defect, family_start, family_end


@njit(cache=True, nogil=True)
def _numba_build_region2_packet_families(action_count: int, raw_fever_fill: float, action_k, n: int):
    family_defect = np.empty(max(1, action_count), dtype=np.int32)
    family_start = np.empty(max(1, action_count), dtype=np.int32)
    family_end = np.empty(max(1, action_count), dtype=np.int32)
    family_count = 0

    prev_defect = 0
    prev_offset = -1000000000
    stop = _numba_region2_k_scan_stop(action_count, raw_fever_fill)
    for action_idx in range(1, int(stop)):
        k = int(action_k[action_idx])
        region_offset = _numba_region2_offset_for_count(0, k, raw_fever_fill, n + k + 2)
        if int(region_offset) < 1:
            continue
        activation_offset = int(region_offset) + k
        defect = k - 1 - (2 * activation_offset)
        if family_count > 0 and prev_defect == defect and activation_offset == prev_offset + 1:
            family_end[family_count - 1] = activation_offset
        else:
            family_defect[family_count] = defect
            family_start[family_count] = activation_offset
            family_end[family_count] = activation_offset
            family_count += 1
        prev_defect = defect
        prev_offset = activation_offset
    return family_count, family_defect, family_start, family_end


@njit(cache=True, nogil=True)
def _numba_clamped_end_idx(n: int, activation_idx: int, raw_end_idx: int) -> int:
    edge_e = raw_end_idx
    if edge_e <= activation_idx:
        edge_e = activation_idx + 1
    if edge_e > n:
        edge_e = n
    return edge_e


@njit(cache=True, nogil=True, inline="always")
def _numba_activation_packet(
    where, body_values, body_starts, body_counts, use_forced_great_timing_i: int, ends, pk_buf
):
    """One section activation's packet: its edge (Perfect activation, or late-Great when `mode` != 0) at every end in
    [exit, early-Great reach] joined with that end's body tail, as rows (body fever, normal Greats + 2 x activation +
    defect, fever Greats) in pk_buf [0, count). The rows do not depend on the state: state s reads normal Greats as the
    second column - 2s. Returns (pk_buf, count); count 0 when the activation is invalid or no end has a tail."""
    n, mode, defect, activation = where
    if activation < 100 or activation >= n:
        return pk_buf, 0
    if int(ends.perfect_valid[activation]) == 0:
        return pk_buf, 0
    perfect_e = int(ends.perfect_e[activation])
    edge_e = perfect_e
    edge_eg_e = int(ends.eg_perfect_e[activation])
    fever_great_delta = 0
    if mode != 0:
        if use_forced_great_timing_i == 0:
            return pk_buf, 0
        if int(ends.late_valid[activation]) == 0:
            return pk_buf, 0
        late_e = int(ends.late_e[activation])
        late_eg_e = int(ends.eg_late_e[activation])
        if not _numba_late_edge_extends(perfect_e, late_e, late_eg_e, edge_eg_e):
            return pk_buf, 0
        edge_e = late_e
        edge_eg_e = late_eg_e
        fever_great_delta = 1

    # Early Greats: extend the fever end from `edge_e` (the Perfect/late boundary) up to the
    # earliest-Great floor boundary `eg_e`. Each e in [edge_e, eg_e] is its own Pareto surface;
    # the notes [edge_e, e) are pulled into fever as GREATS (all body, since activation >= 100),
    # so each such e contributes (e - edge_e) extra fever-greats on top of the section's fever
    # length. eg_e == edge_e on the overwhelming majority of activations, so the loop usually runs once.
    eg_e = edge_eg_e
    # The activation can also end its fever early, at every end in [perfect_exit_e / late_exit_e, edge_e).
    exit_e = ends.perfect_exit_e if mode == 0 else ends.late_exit_e
    lo_e = min(int(exit_e[activation]), edge_e)
    total_points = 0
    for end_e in range(lo_e, eg_e + 1):
        total_points += int(body_counts[end_e])
    if total_points <= 0:
        return pk_buf, 0
    pk_buf = _numba_i64_rows_ensure(pk_buf, 0, total_points)
    write = 0
    for end_e in range(lo_e, eg_e + 1):
        tail_count = int(body_counts[end_e])
        if tail_count <= 0:
            continue
        fever_len = end_e - activation
        extra_fever_great = max(0, end_e - edge_e)
        tail_start = int(body_starts[end_e])
        for tail_idx in range(tail_count):
            value_idx = tail_start + tail_idx
            tail_fever = body_values[value_idx, 0]
            tail_great = body_values[value_idx, 1]
            tail_fever_great = body_values[value_idx, 2]
            tail_normal_great = int(tail_great) - int(tail_fever_great)
            shifted_normal_great = tail_normal_great + (2 * activation) + defect
            packet_fever_great = int(tail_fever_great) + fever_great_delta + extra_fever_great
            pk_buf[int(write), 0] = np.int64(int(tail_fever) + fever_len)
            pk_buf[int(write), 1] = np.int64(shifted_normal_great)
            pk_buf[int(write), 2] = np.int64(packet_fever_great)
            write += 1
    if lo_e < eg_e:
        write = _numba_packet_points_skyline(pk_buf, 0, int(write))
    return pk_buf, int(write)


@njit(cache=True, nogil=True, inline="always")
def _numba_region2_activation_packet(where, body_values, body_starts, body_counts, chart, region, late_exit_e, pk_buf):
    """One region-2 activation's packet (a forced-Great run moves the activation; the run's core comes from the
    shared region table, or live when the table skipped it), rows as in _numba_activation_packet. Returns (pk_buf,
    count)."""
    n, activation_offset, defect, activation, raw_fever_fill = where
    (
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
    ) = region
    if activation < 100 or activation >= n:
        return pk_buf, 0
    k = (2 * activation_offset) + defect + 1
    region_offset = activation_offset - k
    if k <= 0 or region_offset < 1:
        return pk_buf, 0
    state_i = activation - activation_offset
    section_start = state_i + 1
    if section_start < 0 or section_start >= n:
        return pk_buf, 0

    # Shared-core lookup: the great-branch region-run core (great_end, capped hits) is a pure
    # function of (section_start, run_start, activation) -- k participates only via the
    # within-run test of the fill crossing -- so a stored CSR entry matching (offset, activation,
    # is_great) with the activation inside THIS push's k-run is byte-identical to re-deriving the
    # core live. Entries the table's fits-in-chart guard skipped (clamped near-end runs) miss the
    # lookup and take the exact live path below, preserving current emitted frontiers verbatim.
    push_run_start = section_start + region_offset
    looked_up = 0
    activation_i = -1
    edge_e = -1
    run_start = -1
    great_end = -1
    activation_great_idx = -1
    eg_e = -1
    valid = 0
    for entry_idx in range(int(region_starts[section_start]), int(region_starts[section_start + 1])):
        if (
            int(region_offsets[entry_idx]) == region_offset
            and int(region_activations[entry_idx]) == activation
            and int(region_is_greats[entry_idx]) == 1
            and int(region_activations[entry_idx]) < push_run_start + k
        ):
            (activation_i, edge_e, run_start, great_end, activation_great_idx, eg_e, valid) = (
                _numba_region_run_edge_from_core(
                    n,
                    section_start,
                    region_offset,
                    (
                        int(region_activations[entry_idx]),
                        int(region_great_ends[entry_idx]),
                        1,
                        int(region_act_hit_ids[entry_idx]),
                        int(region_perfect_hit_ids[entry_idx]),
                        int(region_perfect_valids[entry_idx]),
                        1,
                    ),
                    region_perfect_end_by_hit,
                    region_great_end_by_hit,
                )
            )
            looked_up = 1
            break
    if looked_up == 0:
        timestamps, perfect_ts, great_ts, perfect_floor, great_floor, late_great_floor, lanes = chart
        (activation_i, edge_e, run_start, great_end, activation_great_idx, eg_e, valid) = (
            _numba_region_run_edge_for_offset(
                (n, section_start, region_offset, k),
                raw_fever_fill,
                timestamps,
                HitTimes(perfect_floor, perfect_ts, great_floor, great_ts, late_great_floor),
                lanes,
                region_perfect_end_by_hit,
                region_great_end_by_hit,
            )
        )
    if int(valid) == 0 or int(activation_great_idx) < 0 or int(activation_i) != activation:
        return pk_buf, 0

    # The activation can also end its fever early, at every end in [late_exit_e, edge_e).
    lo_e = min(int(late_exit_e[activation]), int(edge_e))
    total_points = 0
    for end_e in range(lo_e, int(eg_e) + 1):
        total_points += int(body_counts[end_e])
    if total_points <= 0:
        return pk_buf, 0
    pk_buf = _numba_i64_rows_ensure(pk_buf, 0, total_points)
    write = 0
    for end_e in range(lo_e, int(eg_e) + 1):
        tail_count = int(body_counts[end_e])
        if tail_count <= 0:
            continue
        if end_e <= int(edge_e):
            edge = _numba_pack_edge(n, activation, end_e, int(run_start), int(great_end), activation)
        else:
            edge = _numba_pack_edge_eg(
                n, activation, end_e, int(run_start), int(great_end), activation, int(edge_e), end_e
            )
        edge_fever = int(edge[4])
        edge_fever_great = int(edge[6])
        edge_normal = int(edge[5]) - int(edge[6])
        extra_normal = edge_normal - ((2 * activation_offset) + defect)
        tail_start = int(body_starts[end_e])
        for tail_idx in range(tail_count):
            value_idx = tail_start + tail_idx
            tail_fever = body_values[value_idx, 0]
            tail_great = body_values[value_idx, 1]
            tail_fever_great = body_values[value_idx, 2]
            tail_normal_great = int(tail_great) - int(tail_fever_great)
            pk_buf[int(write), 0] = np.int64(int(tail_fever) + edge_fever)
            pk_buf[int(write), 1] = np.int64(tail_normal_great + (2 * activation) + defect + extra_normal)
            pk_buf[int(write), 2] = np.int64(int(tail_fever_great) + edge_fever_great)
            write += 1
    if lo_e < int(eg_e):
        write = _numba_packet_points_skyline(pk_buf, 0, int(write))
    return pk_buf, int(write)


@njit(cache=True, nogil=True, inline="always")
def _numba_touch_packet_points_for_state(
    points, point_range, state_i: int, key, pair_stamp, best_fever_by_pair, touched_pair, touched_count: int
):
    point_start, point_end = point_range
    pair_mod, pair_stamp_value = key
    generated_count = 0
    for packet_idx in range(point_start, point_end):
        body_fever = points[packet_idx, 0]
        shifted_normal = points[packet_idx, 1]
        fever_great = points[packet_idx, 2]
        true_normal_great = int(shifted_normal) - (2 * state_i)
        touched_count = _numba_touch_body_candidate(
            (np.uint64(int(body_fever)), np.uint64(true_normal_great + int(fever_great)), np.uint64(int(fever_great))),
            (np.uint64(0), np.uint64(0), np.uint64(0)),
            pair_mod,
            pair_stamp,
            best_fever_by_pair,
            touched_pair,
            pair_stamp_value,
            int(touched_count),
        )
        generated_count += 1
    return touched_count, generated_count


@njit(cache=True, nogil=True)
def _numba_store_shared_empty_body_tail(body_starts, body_counts, state: int) -> None:
    body_starts[state] = 0
    body_counts[state] = 1


@njit(cache=True, nogil=True)
def _numba_u64_rows_ensure(values, used: int, extra: int):
    """Grow-doubling reservation on a flat (cap, w) uint64 row store (body-tail values, the fused
    reduce+hull output buffer, the flat head-state pool). Rows [0, used) are live and preserved
    verbatim; stored offsets stay valid."""
    need = used + extra
    cap = values.shape[0]
    if need <= cap:
        return values
    new_cap = cap
    while new_cap < need:
        new_cap *= 2
    grown = np.empty((new_cap, values.shape[1]), dtype=np.uint64)
    grown[:used] = values[:used]
    return grown


@njit(cache=True, nogil=True, inline="always")
def _numba_store_body_tail_frontier(
    body_values, body_starts, body_counts, state: int, cursor: int, frontier_values, frontier_count: int
):
    count = frontier_count
    grown = _numba_u64_rows_ensure(body_values, cursor, count)
    body_starts[state] = cursor
    body_counts[state] = count
    for idx in range(count):
        grown[cursor + idx, 0] = np.uint64(frontier_values[idx, 0])
        grown[cursor + idx, 1] = np.uint64(frontier_values[idx, 1] + frontier_values[idx, 2])
        grown[cursor + idx, 2] = np.uint64(frontier_values[idx, 2])
    return grown, cursor + count


@njit(cache=True, nogil=True, inline="always")
def _numba_skyline_queue_push(queue, heads, tails, family_idx: int, activation: int, pk_buf, count: int):
    """Append one activation's packet rows (pk_buf [0, count)) to its family's skyline queue: rows (body fever, shifted
    normal Greats, fever Greats, activation) in push order, so activations descend from head to tail and expired ones
    leave at the head. A queued row a new row dominates is dropped: the new activation is smaller, so it stays in every
    later window the old one is in. The queue keeps every point of its window's Pareto set (in practice exactly that
    set). Returns the (possibly grown) queue array."""
    f = family_idx
    head = int(heads[f])
    write = head
    for row in range(head, int(tails[f])):
        dominated = False
        for p in range(count):
            if (
                pk_buf[p, 0] >= queue[f, row, 0]
                and pk_buf[p, 1] <= queue[f, row, 1]
                and pk_buf[p, 2] <= queue[f, row, 2]
            ):
                dominated = True
                break
        if not dominated:
            if write != row:
                for col in range(4):
                    queue[f, write, col] = queue[f, row, col]
            write += 1
    if write + count > queue.shape[1]:
        for row in range(head, write):
            for col in range(4):
                queue[f, row - head, col] = queue[f, row, col]
        write -= head
        head = 0
        if write + count > queue.shape[1]:
            cap = queue.shape[1]
            while cap < write + count:
                cap *= 2
            grown = np.empty((queue.shape[0], cap, 4), dtype=np.int64)
            grown[:, : queue.shape[1]] = queue
            queue = grown
    for p in range(count):
        queue[f, write, 0] = pk_buf[p, 0]
        queue[f, write, 1] = pk_buf[p, 1]
        queue[f, write, 2] = pk_buf[p, 2]
        queue[f, write, 3] = activation
        write += 1
    heads[f] = head
    tails[f] = write
    return queue


@njit(cache=True, nogil=True)
def _numba_packet_body_tails_from_precomputed_end_indices(
    sizes, raw_fever_fill: float, plan, reachable, use_forced_great_timing_i: int, chart, tables, scratch
):
    n, action_count, region_action_count = sizes
    action_k, later_fill, later_forced, later_activation_forced = plan
    (
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        perfect_floor_timestamps,
        great_floor_timestamps,
        late_great_floor_timestamps,
        lanes,
    ) = chart
    region, ends = tables
    (
        pair_mod,
        best_fever_by_pair,
        pair_stamp,
        touched_pair,
        pair_stamp_value,
        bit_values,
        bit_stamps,
        bit_stamp_value,
    ) = scratch
    body_values = np.empty((1024, 3), dtype=np.uint64)
    body_starts = np.zeros(n + 1, dtype=np.int32)
    body_counts = np.zeros(n + 1, dtype=np.int32)
    body_values[0, 0] = np.uint64(0)
    body_values[0, 1] = np.uint64(0)
    body_values[0, 2] = np.uint64(0)
    _numba_store_shared_empty_body_tail(body_starts, body_counts, n)
    body_cursor = 1
    # Reusable output buffer for the fused per-state reduce+hull (grow-doubling, rewritten from
    # row 0 each state; survivors are copied into body_values before the next state runs).
    reduce_values = np.empty((1024, 4), dtype=np.int64)

    family_count, family_mode, family_defect, family_start, family_end = _numba_build_packet_families(
        action_count, later_fill, later_forced, later_activation_forced
    )
    region_family_count, region_family_defect, region_family_start, region_family_end = (
        _numba_build_region2_packet_families(region_action_count, raw_fever_fill, action_k, n)
    )
    # One skyline queue per packet family (the section families, then the region-2 families) holding the packets of
    # its live activation window [state + start, state + end] (_numba_skyline_queue_push); each activation is built
    # once, when its window first reaches it.
    families = int(family_count) + (int(region_family_count) if use_forced_great_timing_i != 0 else 0)
    queue = np.empty((max(1, families), 16, 4), dtype=np.int64)
    queue_heads = np.zeros(max(1, families), dtype=np.int64)
    queue_tails = np.zeros(max(1, families), dtype=np.int64)
    next_push_state = np.full(max(1, families), n - 1, dtype=np.int64)
    pk_buf = np.empty((64, 3), dtype=np.int64)

    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0

    for state_i in range(n - 1, 99, -1):
        if not reachable[state_i]:
            continue
        for q in range(families):
            region_family = q >= int(family_count)
            start = int(region_family_start[q - int(family_count)]) if region_family else int(family_start[q])
            high_alpha = state_i + (
                int(region_family_end[q - int(family_count)]) if region_family else int(family_end[q])
            )
            while queue_heads[q] < queue_tails[q] and queue[q, queue_heads[q], 3] > high_alpha:
                queue_heads[q] += 1
            push_state = min(next_push_state[q], high_alpha - start)
            while push_state >= state_i:
                activation = push_state + start
                if region_family:
                    pk_buf, count = _numba_region2_activation_packet(
                        (n, start, int(region_family_defect[q - int(family_count)]), activation, raw_fever_fill),
                        body_values,
                        body_starts,
                        body_counts,
                        chart,
                        region,
                        ends.late_exit_e,
                        pk_buf,
                    )
                else:
                    pk_buf, count = _numba_activation_packet(
                        (n, int(family_mode[q]), int(family_defect[q]), activation),
                        body_values,
                        body_starts,
                        body_counts,
                        use_forced_great_timing_i,
                        ends,
                        pk_buf,
                    )
                if count > 0:
                    queue = _numba_skyline_queue_push(queue, queue_heads, queue_tails, q, activation, pk_buf, count)
                push_state -= 1
            next_push_state[q] = state_i - 1

        states_evaluated += 1
        touched_count = 0
        pair_stamp_value += 1
        for q in range(families):
            if queue_tails[q] > queue_heads[q]:
                touched_count, generated_count = _numba_touch_packet_points_for_state(
                    queue[q],
                    (queue_heads[q], queue_tails[q]),
                    state_i,
                    (pair_mod, pair_stamp_value),
                    pair_stamp,
                    best_fever_by_pair,
                    touched_pair,
                    int(touched_count),
                )
                generated_surfaces += int(generated_count)

        if int(touched_count) == 0:
            _numba_store_shared_empty_body_tail(body_starts, body_counts, state_i)
            frontier_len = 1
        else:
            bit_stamp_value += 1
            reduce_values, frontier_len = _numba_reduce_touched_body_pairs(
                pair_mod,
                touched_pair,
                int(touched_count),
                best_fever_by_pair,
                bit_values,
                bit_stamps,
                bit_stamp_value,
                reduce_values,
            )
            body_values, body_cursor = _numba_store_body_tail_frontier(
                body_values, body_starts, body_counts, state_i, int(body_cursor), reduce_values, int(frontier_len)
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
def _numba_i64_rows_ensure(values, used: int, extra: int):
    """Grow-doubling reservation on a flat (cap, w) int64 row store; rows [0, used) are kept."""
    need = used + extra
    cap = values.shape[0]
    if need <= cap:
        return values
    while cap < need:
        cap *= 2
    grown = np.empty((cap, values.shape[1]), dtype=np.int64)
    grown[:used] = values[:used]
    return grown


@njit(cache=True, nogil=True, inline="always")
def _numba_add_entry(entries, count: int, activation: int, section_ends, run, activation_great_idx: int) -> int:
    """Write one activation section into reserved rows: (activation, base end, earliest early end, early-Great reach,
    Great run start, Great run end, the activation's own Great or -1). Its ends are base_e, every e in
    [exit_e, base_e) and every e in (base_e, eg_e]."""
    base_e, exit_e, eg_e = section_ends
    great_start, great_end = run
    entries[count, 0] = activation
    entries[count, 1] = base_e
    entries[count, 2] = min(exit_e, base_e)
    entries[count, 3] = eg_e
    entries[count, 4] = great_start
    entries[count, 5] = great_end
    entries[count, 6] = activation_great_idx
    return count + 1


@njit(cache=True, nogil=True)
def _numba_section_entries(
    entries, count: int, section, fills, forced, activation_forced, ends, use_forced_great_timing_i: int
):
    """Every action's activation sections for one section starting at `section_start` (activation = state + fill):
    the Perfect activation and, when it carries more than that edge (see _numba_late_edge_extends), the late-Great
    one."""
    n, action_count, state, section_start = section
    entries = _numba_i64_rows_ensure(entries, int(count), 2 * action_count)
    prev_fill = -1
    prev_edge_e = -1
    prev_activation_fill = -1
    prev_activation_e = -1
    prev_activation_prefix = -1
    for action_idx in range(action_count):
        fill = int(fills[action_idx])
        activation = state + fill
        if activation >= n:
            break
        if activation < section_start:
            continue
        forced_count = int(forced[action_idx])
        # forced_count < 0 = region-3 sentinel from the compaction: the forced run would swallow or pre-cross the
        # Perfect activation; the normal edge (and its early-Great extension) must not exist. Late-activation
        # variants gate separately on their own sentinel.
        if int(ends.perfect_valid[activation]) == 0 or forced_count < 0:
            edge_e = -1
        else:
            edge_e = int(ends.perfect_e[activation])
        if edge_e >= 0 and (fill != prev_fill or edge_e != prev_edge_e):
            prev_fill = fill
            prev_edge_e = edge_e
            count = _numba_add_entry(
                entries,
                count,
                activation,
                (edge_e, int(ends.perfect_exit_e[activation]), int(ends.eg_perfect_e[activation])),
                (section_start, min(n, section_start + forced_count)),
                -1,
            )
        prefix_forced = int(activation_forced[action_idx])
        activation_e = -1
        if use_forced_great_timing_i != 0 and prefix_forced >= 0:
            if int(ends.late_valid[activation]) != 0:
                activation_e = int(ends.late_e[activation])
        if not _numba_late_edge_extends(
            edge_e, activation_e, int(ends.eg_late_e[activation]), int(ends.eg_perfect_e[activation])
        ):
            continue
        if (
            fill == prev_activation_fill
            and activation_e == prev_activation_e
            and prefix_forced == prev_activation_prefix
        ):
            continue
        prev_activation_fill = fill
        prev_activation_e = activation_e
        prev_activation_prefix = prefix_forced
        count = _numba_add_entry(
            entries,
            count,
            activation,
            (activation_e, int(ends.late_exit_e[activation]), int(ends.eg_late_e[activation])),
            (section_start, min(n, section_start + prefix_forced)),
            activation,
        )
    return entries, int(count)


@njit(cache=True, nogil=True)
def _numba_region2_entries(
    entries, count: int, n: int, section_start: int, region, perfect_exit_e, late_exit_e, use_forced_great_timing_i: int
):
    """The region-2 activation sections of one section start (a forced-Great run moves the activation): the region
    core table's entries for `section_start`, each finished for this fever time (its ends and early-Great reach)."""
    if use_forced_great_timing_i == 0:
        return entries, int(count)
    (
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
    ) = region
    entries = _numba_i64_rows_ensure(
        entries, int(count), int(region_starts[section_start + 1]) - int(region_starts[section_start])
    )
    for entry_idx in range(int(region_starts[section_start]), int(region_starts[section_start + 1])):
        activation, edge_e, run_start, great_end, activation_great_idx, eg_e, valid = _numba_region_run_edge_from_core(
            n,
            section_start,
            int(region_offsets[entry_idx]),
            (
                int(region_activations[entry_idx]),
                int(region_great_ends[entry_idx]),
                int(region_is_greats[entry_idx]),
                int(region_act_hit_ids[entry_idx]),
                int(region_perfect_hit_ids[entry_idx]),
                int(region_perfect_valids[entry_idx]),
                1,
            ),
            region_perfect_end_by_hit,
            region_great_end_by_hit,
        )
        if int(valid) == 0:
            continue
        exit_e = perfect_exit_e if int(activation_great_idx) < 0 else late_exit_e
        count = _numba_add_entry(
            entries,
            count,
            int(activation),
            (int(edge_e), int(exit_e[int(activation)]), int(eg_e)),
            (int(run_start), int(great_end)),
            int(activation_great_idx),
        )
    return entries, int(count)


@njit(cache=True, nogil=True, inline="always")
def _numba_mask_hash(w0, w1, w2, w3):
    h = w0 * np.uint64(0x9E3779B97F4A7C15)
    h = (h ^ (h >> np.uint64(29)) ^ w1) * np.uint64(0xBF58476D1CE4E5B9)
    h = (h ^ (h >> np.uint64(31)) ^ w2) * np.uint64(0x94D049BB133111EB)
    h = (h ^ (h >> np.uint64(29)) ^ w3) * np.uint64(0x9E3779B97F4A7C15)
    return h ^ (h >> np.uint64(32))


@njit(cache=True, nogil=True)
def _numba_pattern_id(slots, masks, patterns: int, w0, w1, w2, w3):
    """Id of the head-mask pattern (w0..w3) in an open-addressing table; a new pattern gets the next id (the table
    and the mask rows grow as needed). Returns (slots, masks, id, patterns)."""
    if 2 * (patterns + 1) > slots.shape[0]:
        cap = 2 * slots.shape[0]
        slots = np.full(cap, -1, dtype=np.int64)
        for pid in range(patterns):
            slot = np.int64(
                _numba_mask_hash(masks[pid, 0], masks[pid, 1], masks[pid, 2], masks[pid, 3]) & np.uint64(cap - 1)
            )
            while slots[slot] >= 0:
                slot = (slot + 1) & (cap - 1)
            slots[slot] = pid
    if patterns >= masks.shape[0]:
        grown = np.empty((2 * masks.shape[0], 4), dtype=np.uint64)
        grown[:patterns] = masks[:patterns]
        masks = grown
    cap = slots.shape[0]
    slot = np.int64(_numba_mask_hash(w0, w1, w2, w3) & np.uint64(cap - 1))
    while True:
        pid = slots[slot]
        if pid < 0:
            slots[slot] = patterns
            masks[patterns, 0] = w0
            masks[patterns, 1] = w1
            masks[patterns, 2] = w2
            masks[patterns, 3] = w3
            return slots, masks, patterns, patterns + 1
        if masks[pid, 0] == w0 and masks[pid, 1] == w1 and masks[pid, 2] == w2 and masks[pid, 3] == w3:
            return slots, masks, pid, patterns
        slot = (slot + 1) & (cap - 1)


@njit(cache=True, nogil=True)
def _numba_entry_end_points(points, m: int, slots, masks, patterns: int, edge, end_e: int, head):
    """The candidates of one edge ending at `end_e`, joined with that state's tail frontier: body tail points, the
    terminal state (the edge alone), or a head state's rows (their masks combine with the edge's)."""
    body_values, body_starts, body_counts, head_pool, head_state_start, head_state_count, head_limit = head
    if end_e >= 100 or end_e >= int(head_limit):
        slots, masks, pid, patterns = _numba_pattern_id(slots, masks, patterns, edge[0], edge[1], edge[2], edge[3])
        bf0 = np.int64(edge[4])
        ng0 = np.int64(edge[5]) - np.int64(edge[6])
        fg0 = np.int64(edge[6])
        if end_e >= 100:
            tails = int(body_counts[end_e])
            start = int(body_starts[end_e])
            points = _numba_i64_rows_ensure(points, m, tails)
            for idx in range(tails):
                points[m, 0] = bf0 + np.int64(body_values[start + idx, 0])
                points[m, 1] = ng0 + np.int64(body_values[start + idx, 1]) - np.int64(body_values[start + idx, 2])
                points[m, 2] = fg0 + np.int64(body_values[start + idx, 2])
                points[m, 3] = pid
                m += 1
        else:
            points = _numba_i64_rows_ensure(points, m, 1)
            points[m, 0] = bf0
            points[m, 1] = ng0
            points[m, 2] = fg0
            points[m, 3] = pid
            m += 1
        return points, m, slots, masks, int(patterns)
    start = int(head_state_start[end_e])
    rows = int(head_state_count[end_e])
    points = _numba_i64_rows_ensure(points, m, rows)
    for idx in range(rows):
        row = start + idx
        slots, masks, pid, patterns = _numba_pattern_id(
            slots,
            masks,
            patterns,
            edge[0] | head_pool[row, 0],
            edge[1] | head_pool[row, 1],
            edge[2] | head_pool[row, 2],
            edge[3] | head_pool[row, 3],
        )
        bg = np.int64(edge[5]) + np.int64(head_pool[row, 5])
        bfg = np.int64(edge[6]) + np.int64(head_pool[row, 6])
        points[m, 0] = np.int64(edge[4]) + np.int64(head_pool[row, 4])
        points[m, 1] = bg - bfg
        points[m, 2] = bfg
        points[m, 3] = pid
        m += 1
    return points, m, slots, masks, int(patterns)


@njit(cache=True, nogil=True, inline="always")
def _numba_pattern_dominates(masks, q: int, p: int) -> bool:
    """Whether head pattern q can dominate pattern p: equal fever/Great overlap, q's fever mask a superset and its
    Great mask a subset of p's (a same-pattern pair qualifies)."""
    return (
        (masks[q, 0] & masks[q, 2]) == (masks[p, 0] & masks[p, 2])
        and (masks[q, 1] & masks[q, 3]) == (masks[p, 1] & masks[p, 3])
        and (masks[p, 0] & ~masks[q, 0]) == 0
        and (masks[p, 1] & ~masks[q, 1]) == 0
        and (masks[q, 2] & ~masks[p, 2]) == 0
        and (masks[q, 3] & ~masks[p, 3]) == 0
    )


@njit(cache=True, nogil=True, inline="always")
def _numba_int_slot(slot_key, key: int, cap: int) -> int:
    """The slot of a non-negative key in an open-addressing table (`slot_key` = -1 when empty): the slot holding it,
    else the empty slot where it goes."""
    slot = np.int64((np.uint64(key) * np.uint64(0x9E3779B97F4A7C15)) >> np.uint64(32)) & (cap - 1)
    while slot_key[slot] >= 0 and slot_key[slot] != key:
        slot = (slot + 1) & (cap - 1)
    return slot


@njit(cache=True, nogil=True, inline="always")
def _numba_intern_reserved(slots, masks, patterns: int, w0, w1, w2, w3):
    """_numba_pattern_id on tables with room reserved for every new pattern: returns (id, patterns)."""
    cap = slots.shape[0]
    slot = np.int64(_numba_mask_hash(w0, w1, w2, w3) & np.uint64(cap - 1))
    while True:
        pid = int(slots[slot])
        if pid < 0:
            slots[slot] = patterns
            masks[patterns, 0] = w0
            masks[patterns, 1] = w1
            masks[patterns, 2] = w2
            masks[patterns, 3] = w3
            return patterns, patterns + 1
        if masks[pid, 0] == w0 and masks[pid, 1] == w1 and masks[pid, 2] == w2 and masks[pid, 3] == w3:
            return pid, patterns
        slot = (slot + 1) & (cap - 1)


@njit(cache=True, nogil=True)
def _numba_state_points(entries, count: int, n: int, head, points, slots, masks, arena):
    """All candidate points (body fever, normal Greats, fever Greats, pattern id) of one state's activation sections.

    A section whose activation and ends all lie in the body, with Great counts constant over its early ends and
    growing one per step over its early-Great ends (only the fever window's overlap with the Great run can change
    them), is a shift (-activation, normal Greats, fever Greats) of its windows' skylines. Such sections are grouped
    by their window pair: each group's skylines are computed once, and a section whose shift a section of a dominating
    pattern (or its own) dominates adds nothing. Any other section is joined end by end.
    Returns (points, m, slots, masks, patterns, arena)."""
    width = n + 2
    rows = max(1, count)
    # Room for every section's pattern, so interning below never reallocates.
    cap = slots.shape[0]
    while cap < 2 * rows:
        cap *= 2
    if cap != slots.shape[0]:
        slots = np.empty(cap, dtype=np.int64)
    slots[:] = -1
    if masks.shape[0] < rows:
        masks = np.empty((rows, 4), dtype=np.uint64)
    patterns = 0
    # Per section: pattern id (-1: joined end by end, -2: dropped), normal and fever Greats at the base end, next
    # section of its group. A group is keyed by its exit window [lo, base] and early-Great window (base, eg].
    info = np.empty((rows, 4), dtype=np.int64)
    table_cap = 16
    while table_cap < 2 * rows:
        table_cap *= 2
    table_key = np.full(table_cap, -1, dtype=np.int64)
    table_head = np.empty(table_cap, dtype=np.int64)
    group_slots = np.empty(rows, dtype=np.int64)
    groups = 0
    prev_pid = -1
    for idx in range(count):
        info[idx, 0] = -1
        activation, base_e, lo_e, eg_e = entries[idx, 0], entries[idx, 1], entries[idx, 2], entries[idx, 3]
        great_start, great_end, agi = entries[idx, 4], entries[idx, 5], entries[idx, 6]
        if activation < 100 or lo_e < 100:
            continue
        run_lo = max(int(activation), int(great_start), 100)
        overlap_base = max(0, min(int(base_e), int(great_end), n) - run_lo)
        if max(0, min(int(lo_e), int(great_end), n) - run_lo) != overlap_base:
            continue
        if eg_e > base_e and max(0, min(int(eg_e), int(great_end), n) - run_lo) != overlap_base:
            continue
        at_base = _numba_pack_edge(n, int(activation), int(base_e), int(great_start), int(great_end), int(agi))
        if (
            prev_pid >= 0
            and masks[prev_pid, 0] == at_base[0]
            and masks[prev_pid, 1] == at_base[1]
            and masks[prev_pid, 2] == at_base[2]
            and masks[prev_pid, 3] == at_base[3]
        ):
            pid = prev_pid
        else:
            pid, patterns = _numba_intern_reserved(
                slots, masks, patterns, at_base[0], at_base[1], at_base[2], at_base[3]
            )
        prev_pid = pid
        key = (lo_e * width + base_e) * width + (eg_e if eg_e > base_e else 0)
        info[idx, 0] = pid
        info[idx, 1] = np.int64(at_base[5]) - np.int64(at_base[6])
        info[idx, 2] = np.int64(at_base[6])
        info[idx, 3] = -1
        slot = _numba_int_slot(table_key, int(key), table_cap)
        if table_key[slot] < 0:
            table_key[slot] = key
            group_slots[groups] = slot
            groups += 1
        else:
            info[idx, 3] = table_head[slot]
        table_head[slot] = idx
    body_values, body_starts, body_counts = head.body_values, head.body_starts, head.body_counts
    m = 0
    for group in range(groups):
        first = table_head[group_slots[group]]
        a_idx = first
        while a_idx >= 0 and info[first, 3] >= 0:
            b_idx = first
            while b_idx >= 0:
                if (
                    b_idx != a_idx
                    and info[b_idx, 0] >= 0
                    and entries[b_idx, 0] <= entries[a_idx, 0]
                    and info[b_idx, 1] <= info[a_idx, 1]
                    and info[b_idx, 2] <= info[a_idx, 2]
                    and _numba_pattern_dominates(masks, info[b_idx, 0], info[a_idx, 0])
                ):
                    info[a_idx, 0] = -2
                    break
                b_idx = info[b_idx, 3]
            a_idx = info[a_idx, 3]
        # The group's window skylines: the exact Pareto set of every end's tail points shifted by the end (by the end
        # on the fever-Great count too for the early-Great window), exit window rows first.
        exit_rows = 0
        all_rows = 0
        for kind in range(2):
            if kind == 0:
                lo_e, hi_e = int(entries[first, 2]), int(entries[first, 1])
            else:
                lo_e, hi_e = int(entries[first, 1]) + 1, int(entries[first, 3])
            for end_e in range(lo_e, hi_e + 1):
                start = int(body_starts[end_e])
                tails = int(body_counts[end_e])
                if all_rows + tails > arena.shape[0]:
                    arena = _numba_i64_rows_ensure(arena, all_rows, tails)
                for t in range(tails):
                    bf = end_e + np.int64(body_values[start + t, 0])
                    ng = np.int64(body_values[start + t, 1]) - np.int64(body_values[start + t, 2])
                    fg = np.int64(body_values[start + t, 2]) + (end_e if kind == 1 else 0)
                    all_rows = _numba_packet_points_append(arena, exit_rows if kind == 1 else 0, all_rows, bf, ng, fg)
            if kind == 0:
                exit_rows = all_rows
        idx = first
        while idx >= 0:
            if info[idx, 0] >= 0:
                activation, base_e = entries[idx, 0], entries[idx, 1]
                pid, ng, fg = info[idx, 0], info[idx, 1], info[idx, 2]
                if m + all_rows > points.shape[0]:
                    points = _numba_i64_rows_ensure(points, m, all_rows)
                for row in range(all_rows):
                    points[m, 0] = arena[row, 0] - activation
                    points[m, 1] = arena[row, 1] + ng
                    points[m, 2] = arena[row, 2] + fg - (base_e if row >= exit_rows else 0)
                    points[m, 3] = pid
                    m += 1
            idx = info[idx, 3]
    for idx in range(count):
        if info[idx, 0] != -1:
            continue
        activation, base_e, lo_e, eg_e = entries[idx, 0], entries[idx, 1], entries[idx, 2], entries[idx, 3]
        great_start, great_end, agi = entries[idx, 4], entries[idx, 5], entries[idx, 6]
        points, m, slots, masks, patterns = _numba_entry_end_points(
            points,
            m,
            slots,
            masks,
            patterns,
            _numba_pack_edge(n, int(activation), int(base_e), int(great_start), int(great_end), int(agi)),
            int(base_e),
            head,
        )
        for end_e in range(int(base_e) + 1, int(eg_e) + 1):
            edge = _numba_pack_edge_eg(
                n, int(activation), end_e, int(great_start), int(great_end), int(agi), int(base_e), end_e
            )
            points, m, slots, masks, patterns = _numba_entry_end_points(
                points, m, slots, masks, patterns, edge, end_e, head
            )
        for end_e in range(int(lo_e), int(base_e)):
            edge = _numba_pack_edge(n, int(activation), end_e, int(great_start), int(great_end), int(agi))
            points, m, slots, masks, patterns = _numba_entry_end_points(
                points, m, slots, masks, patterns, edge, end_e, head
            )
    return points, int(m), slots, masks, int(patterns), arena


@njit(cache=True, nogil=True)
def _numba_points_frontier(points, masks, sizes, head, fen_values, fen_stamps, fen_stamp):
    """A state's frontier from its candidate points, by three reductions, cheapest and strongest first:

    1. Each pattern's skyline (exact): a pattern's points in (normal Greats, fever Greats, body fever desc) order; a
       point is kept iff its body fever beats every earlier point with fever Greats <= (stamped Fenwick prefix
       maxima), then each normal-Great level is pruned to its upper hull of (body fever, -fever Great) by
       `_numba_skyline_hull_push`, the body DP's pair reduce (same-pattern points share their head score and the
       body score is linear in the three counts). The Fenwick spans the state's fever-Great range only.
    2. The head envelope (cone) filter across patterns (`_numba_head_envelope_filter`, lossless by its 16-corner
       proof): it compares surfaces of different head patterns, which structural dominance cannot.
    3. The exact structural Pareto set of what remains: rows visited by body fever desc, normal Greats asc, fever
       Greats asc, then pattern rank (Great bits minus fever bits) asc; a row is kept unless a kept row of a
       dominating pattern (same fever/Great overlap, fever-mask superset, Great-mask subset) has normal and fever
       Greats <= (its body fever is >= by the order). A dominator always comes first in that order and dominance is
       transitive, so this keeps exactly the non-dominated rows.
    No points gives the zero surface (the play that never activates) when `empty_is_zero`, else nothing. Returns
    (frontier, Fenwick stamp)."""
    m, patterns, n = sizes
    lo_pos, hi_pos, min_surfaces, empty_is_zero = head
    if m == 0:
        return np.zeros((1 if empty_is_zero else 0, 7), dtype=np.uint64), fen_stamp
    radix = n + 1
    keys = np.empty(m, dtype=np.int64)
    max_fg = 0
    for idx in range(m):
        bf, ng, fg = points[idx, 0], points[idx, 1], points[idx, 2]
        if bf < 0 or ng < 0 or fg < 0 or bf >= radix or ng >= radix or fg >= radix:
            raise ValueError("FG response candidate body counts out of range")
        keys[idx] = ((points[idx, 3] * radix + ng) * radix + fg) * radix + (radix - 1 - bf)
        max_fg = max(max_fg, fg)
    order = np.argsort(keys)
    fen_values = fen_values[: max_fg + 2]
    fen_stamps = fen_stamps[: max_fg + 2]
    stack = np.empty((m, 4), dtype=np.int64)
    count = 0
    group_base = 0
    group_ng = -1
    pid = -1
    prev_pair = -1
    for pos in range(m):
        idx = int(order[pos])
        if points[idx, 3] != pid:
            pid = points[idx, 3]
            fen_stamp += 1
            group_ng = -1
            prev_pair = -1
        bf, ng, fg = points[idx, 0], points[idx, 1], points[idx, 2]
        pair = ng * radix + fg
        if pair == prev_pair:
            continue
        prev_pair = pair
        count, group_base, group_ng = _numba_skyline_hull_push(
            stack, count, (group_base, group_ng), (bf, ng, fg, pid), fen_values, fen_stamps, fen_stamp
        )
    frontier = np.empty((count, 7), dtype=np.uint64)
    for k in range(count):
        p = stack[k, 3]
        for col in range(4):
            frontier[k, col] = masks[p, col]
        frontier[k, 4] = np.uint64(stack[k, 0])
        frontier[k, 6] = np.uint64(stack[k, 2])
        frontier[k, 5] = np.uint64(stack[k, 1]) + frontier[k, 6]
    frontier = _numba_head_envelope_filter(frontier, lo_pos, hi_pos, min_surfaces)
    rows = frontier.shape[0]
    rank_keys = np.empty(rows, dtype=np.int64)
    for k in range(rows):
        row = frontier[k]
        rank = (
            128
            + np.int64(_numba_popcount64(row[2]))
            + np.int64(_numba_popcount64(row[3]))
            - np.int64(_numba_popcount64(row[0]))
            - np.int64(_numba_popcount64(row[1]))
        )
        rank_keys[k] = (
            ((radix - 1 - np.int64(row[4])) * radix + (np.int64(row[5]) - np.int64(row[6]))) * radix + np.int64(row[6])
        ) * 257 + rank
    rank_order = np.argsort(rank_keys)
    kept = np.empty(max(1, rows), dtype=np.int64)
    kept_count = 0
    for pos in range(rows):
        i = int(rank_order[pos])
        cand = frontier[i]
        dominated = False
        for kk in range(kept_count):
            k = frontier[kept[kk]]
            if (
                k[5] - k[6] <= cand[5] - cand[6]
                and k[6] <= cand[6]
                and (k[0] & k[2]) == (cand[0] & cand[2])
                and (k[1] & k[3]) == (cand[1] & cand[3])
                and (cand[0] & ~k[0]) == 0
                and (cand[1] & ~k[1]) == 0
                and (k[2] & ~cand[2]) == 0
                and (k[3] & ~cand[3]) == 0
            ):
                dominated = True
                break
        if not dominated:
            kept[kept_count] = i
            kept_count += 1
    out = np.empty((kept_count, 7), dtype=np.uint64)
    for kk in range(kept_count):
        out[kk] = frontier[kept[kk]]
    return out, fen_stamp


@njit(cache=True, nogil=True)
def _first_frontier_from_precomputed_end_indices_numba(sizes, actions, runs, chart, hits, fever, regions, workspace):
    n, action_count, region_action_count = sizes
    action_k, later_fill, first_fill, later_forced, first_forced, later_activation_forced, first_activation_forced = (
        actions
    )
    perfect_run_starts, perfect_run_ends, late_run_starts, late_run_ends = runs
    (
        timestamps,
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        perfect_floor_timestamps,
        great_floor_timestamps,
        late_great_floor_timestamps,
        lanes,
    ) = chart
    (
        prefix_perfect_hit,
        prefix_perfect_valid,
        prefix_late_hit,
        prefix_late_valid,
        capped_perfect_edge_e,
        capped_late_edge_e,
        capped_eg_perfect_e,
        capped_eg_late_e,
        capped_perfect_exit_e,
        capped_late_exit_e,
    ) = hits
    raw_fever_fill, real_fever_time, real_time_idx, use_forced_great_timing_i, head_filter_min = fever
    (
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
    ) = regions
    (
        ws_pair_values,
        ws_pair_stamps,
        ws_pair_touched,
        ws_bit_values,
        ws_bit_stamps,
        ws_perfect_successor,
        ws_perfect_successor_stamps,
        ws_late_successor,
        ws_late_successor_stamps,
        successor_epoch_in,
        pair_epoch_in,
        bit_epoch_in,
    ) = workspace
    rt = real_time_idx
    ends = ActivationEnds(
        prefix_perfect_hit,
        prefix_perfect_valid,
        prefix_late_hit,
        prefix_late_valid,
        capped_perfect_edge_e[rt],
        capped_late_edge_e[rt],
        capped_eg_perfect_e[rt],
        capped_eg_late_e[rt],
        capped_perfect_exit_e[rt],
        capped_late_exit_e[rt],
    )
    region = RegionTables(
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
    )
    reachable, max_eg_width = _numba_first_frontier_reachability_prepass(
        n,
        action_count,
        (first_fill, first_activation_forced),
        (perfect_run_starts, perfect_run_ends, late_run_starts, late_run_ends),
        ends,
        (real_fever_time, use_forced_great_timing_i),
        (region, great_floor_timestamps),
        (
            ws_perfect_successor,
            ws_perfect_successor_stamps,
            ws_late_successor,
            ws_late_successor_stamps,
            successor_epoch_in,
        ),
    )
    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0
    min_later_fill = max(1, int(later_fill[0]) if action_count > 0 else 1)
    # Body-pair radix sizing. pair_idx packs (normal_great, body_fever_great) as
    # normal_great*pair_mod + body_fever_great, injective only while body_fever_great < pair_mod.
    # body_fever_great sums, per section, <=1 boundary Great plus the issue-#44 early-Great band
    # (<= max_eg_width extras), over at most `section_bound` sections -> true max is
    # section_bound*(1 + max_eg_width). Size pair_mod one past that (max_eg_width == 0 on the common no-early-Great
    # path). Capped at n+1 since body_fever_great <= body_great <= n always; a smaller radix would alias pairs.
    section_bound = n // min_later_fill + 4
    pair_mod = min(n + 1, section_bound * (1 + int(max_eg_width)) + 1)
    pair_size = (n + 1) * pair_mod
    # Workspace capacity guard (fail loud, never resize): the host sizes the per-thread pair
    # workspaces to a provable song-level pair_mod bound (_song_first_frontier_pair_mod_bound) and the
    # Fenwick workspace to n + 2 (the head states' fever-Great counts reach n).
    # If this geometry's true radix ever escaped that bound, numpy's silent slice truncation
    # below would hand the stamp loops short arrays -> out-of-bounds writes under njit. Raise
    # instead; a violation means the host bound derivation is wrong, never a recoverable state.
    if (
        ws_pair_values.shape[0] < pair_size
        or ws_pair_stamps.shape[0] < pair_size
        or ws_pair_touched.shape[0] < pair_size
        or ws_bit_values.shape[0] < n + 2
        or ws_bit_stamps.shape[0] < n + 2
    ):
        raise ValueError("FG first-frontier stamp workspace is undersized for this geometry's pair radix")
    # Reused per-thread stamp-radix workspace (allocation-lifetime change only). A cell is valid
    # iff its stamp equals the current epoch, and epochs carry monotonically across calls (the
    # incoming epoch is the max stamp any earlier call wrote), so stale cells from earlier
    # geometries hold older epochs and are invisible -- the same invariant that hides stale cells
    # between consecutive states within one call. The views are sliced to this geometry's exact
    # sizes so every shape-derived bound (pair radix guard, stamped-Fenwick ascent limits) is identical to the
    # fresh-allocation behavior.
    best_fever_by_pair = ws_pair_values[:pair_size]
    pair_stamp = ws_pair_stamps[:pair_size]
    touched_pair = ws_pair_touched[:pair_size]
    pair_stamp_value = pair_epoch_in
    bit_values = ws_bit_values[: pair_mod + 1]
    bit_stamps = ws_bit_stamps[: pair_mod + 1]
    bit_stamp_value = bit_epoch_in

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
        (n, action_count, region_action_count),
        raw_fever_fill,
        (action_k, later_fill, later_forced, later_activation_forced),
        reachable,
        use_forced_great_timing_i,
        (
            timestamps,
            perfect_candidate_timestamps,
            great_candidate_timestamps,
            perfect_floor_timestamps,
            great_floor_timestamps,
            late_great_floor_timestamps,
            lanes,
        ),
        (region, ends),
        (
            pair_mod,
            best_fever_by_pair,
            pair_stamp,
            touched_pair,
            int(pair_stamp_value),
            bit_values,
            bit_stamps,
            int(bit_stamp_value),
        ),
    )

    head_limit = min(n, 100)
    # Flat head-state store: retained per-state head frontiers live in one grow-doubling
    # (cap, 7) uint64 arena addressed by a state -> (start, count) CSR. Rows are written in the
    # envelope filter's retained order, and a state's rows are final before any earlier state composes against
    # them (states run descending). Unreachable states keep count 0.
    head_pool = np.empty((256, 7), dtype=np.uint64)
    head_pool_cursor = 0
    head_state_start = np.zeros(max(1, head_limit), dtype=np.int64)
    head_state_count = np.zeros(max(1, head_limit), dtype=np.int64)
    head = HeadTables(body_values, body_starts, body_counts, head_pool, head_state_start, head_state_count, head_limit)
    # Per-state scratch reused by every state of this build: activation sections, candidate points, the
    # head-mask pattern table and the window skyline arena. The states' Fenwick is the bit workspace, its epoch
    # carried on from the body tails.
    entries = np.empty((256, 7), dtype=np.int64)
    points = np.empty((1024, 4), dtype=np.int64)
    slots = np.full(1024, -1, dtype=np.int64)
    masks = np.empty((256, 4), dtype=np.uint64)
    arena = np.empty((1024, 3), dtype=np.int64)

    # Head states (descending), then the first section from the song start (state 0 with the first-section action
    # arrays): each state's frontier from its activation sections (_numba_state_points, _numba_points_frontier).
    first_frontier = np.zeros((0, 7), dtype=np.uint64)
    for state_i in range(head_limit - 1, -2, -1):
        first = state_i < 0
        if not first and not reachable[state_i]:
            continue
        state = 0 if first else state_i
        if first:
            entries, count = _numba_section_entries(
                entries,
                0,
                (n, action_count, 0, 0),
                first_fill,
                first_forced,
                first_activation_forced,
                ends,
                use_forced_great_timing_i,
            )
        else:
            states_evaluated += 1
            entries, count = _numba_section_entries(
                entries,
                0,
                (n, action_count, state, state + 1),
                later_fill,
                later_forced,
                later_activation_forced,
                ends,
                use_forced_great_timing_i,
            )
        entries, count = _numba_region2_entries(
            entries,
            count,
            n,
            0 if first else state + 1,
            region,
            ends.perfect_exit_e,
            ends.late_exit_e,
            use_forced_great_timing_i,
        )
        points, m, slots, masks, patterns, arena = _numba_state_points(
            entries, count, n, head, points, slots, masks, arena
        )
        generated_surfaces += m
        # A first section whose activations all lie in the body keeps no surface when none reaches it.
        frontier, bit_stamp_value = _numba_points_frontier(
            points,
            masks,
            (m, patterns, n),
            (state, head_limit, head_filter_min, not (first and action_count > 0 and int(first_fill[0]) >= 100)),
            ws_bit_values,
            ws_bit_stamps,
            int(bit_stamp_value),
        )
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)
        if first:
            first_frontier = frontier
            break
        head_pool = _numba_u64_rows_ensure(head_pool, int(head_pool_cursor), len(frontier))
        head = HeadTables(
            body_values, body_starts, body_counts, head_pool, head_state_start, head_state_count, head_limit
        )  # the arena may have regrown
        head_state_start[state] = int(head_pool_cursor)
        head_state_count[state] = len(frontier)
        head_pool[int(head_pool_cursor) : int(head_pool_cursor) + len(frontier)] = frontier
        head_pool_cursor += len(frontier)

    return (
        first_frontier,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        int(pair_stamp_value),
        int(bit_stamp_value),
    )


@njit(cache=True, nogil=True)
def _first_frontiers_of_fever_times(sizes, actions, runs, chart, hits, fever, regions, workspace):
    """`_first_frontier_from_precomputed_end_indices_numba` for each fever time of one (fill, non-Fever base) group, with
    no call back into Python between them. fever: (raw fill, real fever times, their indices, forced timing, head filter
    size); regions: the eight region tables, then the Perfect and Great end tables per fever-time index; workspace: its
    arrays, then the first successor epoch (one per fever time), and the pair and bit epochs. Returns the frontiers' rows,
    each one's first row (with the end), per fever time (states, generated surfaces, retained surfaces, largest state
    frontier), and the pair and bit epochs."""
    raw_fever_fill, real_fever_times, real_time_idxs, forced_timing, head_filter_min = fever
    r0, r1, r2, r3, r4, r5, r6, r7, perfect_ends, great_ends = regions
    w0, w1, w2, w3, w4, w5, w6, w7, w8, successor_epoch, pair_epoch, bit_epoch = workspace
    count = real_fever_times.shape[0]
    offsets = np.zeros(count + 1, dtype=np.int64)
    stats = np.empty((count, 4), dtype=np.int64)
    frontiers = []
    for index in range(count):
        rt = real_time_idxs[index]
        frontier, states, generated, retained, largest, pair_epoch, bit_epoch = (
            _first_frontier_from_precomputed_end_indices_numba(
                sizes,
                actions,
                runs,
                chart,
                hits,
                (raw_fever_fill, real_fever_times[index], rt, forced_timing, head_filter_min),
                (r0, r1, r2, r3, r4, r5, r6, r7, perfect_ends[rt], great_ends[rt]),
                (w0, w1, w2, w3, w4, w5, w6, w7, w8, successor_epoch + index, pair_epoch, bit_epoch),
            )
        )
        frontiers.append(frontier)
        offsets[index + 1] = offsets[index] + frontier.shape[0]
        stats[index, 0], stats[index, 1], stats[index, 2], stats[index, 3] = states, generated, retained, largest
    rows = np.empty((offsets[count], 7), dtype=np.uint64)
    for index in range(count):
        rows[offsets[index] : offsets[index + 1]] = frontiers[index]
    return rows, offsets, stats, pair_epoch, bit_epoch
