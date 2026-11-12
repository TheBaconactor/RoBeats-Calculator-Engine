from collections import namedtuple

import numpy as np
from numba import njit

# What a head state's candidates read: every body state's tail frontier (rows of `body_values`, addressed per state by
# body_starts / body_counts) and the frontiers of the head states already built (rows of `head_pool`, addressed by
# head_state_start / head_state_count) for the first `head_limit` states.
_HeadTables = namedtuple(
    "_HeadTables",
    ["body_values", "body_starts", "body_counts", "head_pool", "head_state_start", "head_state_count", "head_limit"],
)
# A group's region table (region_core_table) and one fever time's end of every hit token on the Perfect and the Great
# floor.
RegionTables = namedtuple(
    "RegionTables", ["head_starts", "head_rows", "key_starts", "key_rows", "perfect_end_by_hit", "great_end_by_hit"]
)
# Every note's earliest (floor) and latest (candidate) Perfect and Great hit, and its earliest late-Great hit.
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
# One fever time's per-activation tables: whether a note has a reachable Perfect / late-Great activation hit
# (`*_valid` != 0), the ends its latest such hit reaches on the Perfect floor (`perfect_e`, `late_e`) and on the Great
# floor (`eg_perfect_e`, `eg_late_e`: its early-Great reach), clamped to (activation, n], and the earliest end a
# Perfect / late-Great activation can exit at (`perfect_exit_e`, `late_exit_e`; its ends are every e from there to
# its early-Great reach).
ActivationEnds = namedtuple(
    "ActivationEnds",
    [
        "perfect_valid",
        "late_valid",
        "perfect_e",
        "late_e",
        "eg_perfect_e",
        "eg_late_e",
        "perfect_exit_e",
        "late_exit_e",
    ],
)
# A surface's basis for the corner scores: its body counts, then its head sums at the box's low and high combo.
_BASIS_BODY_FEVER = 0
_BASIS_BODY_NORMAL_GREAT = 1
_BASIS_BODY_FEVER_GREAT = 2
_BASIS_B_LO = 3
_BASIS_C_LO = 4
_BASIS_D_LO = 5
_BASIS_B_HI = 6
_BASIS_C_HI = 7
_BASIS_D_HI = 8

# Song tokens ``kind * n + note_index`` name every value activation-hit selection can return (chart / Perfect /
# Great / capped Perfect / capped Great); the song-wide endpoint tables are indexed by them directly.
_REGION_HIT_CHART = 0
_REGION_HIT_PERFECT = 1
_REGION_HIT_GREAT = 2
_REGION_HIT_PERFECT_CAPPED = 3
_REGION_HIT_GREAT_CAPPED = 4
_EXACT_LANE_SIGNATURE_MAX_WORD_CELLS = 16_777_216
# The kinds of a body state's activation families (packet_families). A late-Great activation is itself one fever Great.
_PERFECT_FAMILY = 0
_LATE_FAMILY = 1
_REGION_FAMILY = 2
# Columns of a region table's rows (region_core_table). A head row holds a run's offset and activation, a key row the
# section starts a run of its activation holds at; both end with the run's Great end and the song tokens of its
# late-Great and Perfect activation hits (-1: it has none).
_HEAD_OFFSET = 0
_HEAD_ACTIVATION = 1
_KEY_FIRST_SECTION = 0
_KEY_LAST_SECTION = 1
_ROW_GREAT_END = 2
_ROW_LATE_HIT = 3
_ROW_PERFECT_HIT = 4


@njit(cache=True, nogil=True)
def _mask_segment(start: int, end: int, offset: int) -> np.uint64:
    lo = max(start, offset)
    hi = min(end, offset + 64)
    if hi <= lo:
        return np.uint64(0)
    width = hi - lo
    if width >= 64:
        return np.uint64(0xFFFFFFFFFFFFFFFF)
    return ((np.uint64(1) << np.uint64(width)) - np.uint64(1)) << np.uint64(lo - offset)


@njit(cache=True, nogil=True)
def _range_mask(start: int, end: int, n: int):
    start_i = max(0, min(min(start, n), 100))
    end_i = max(0, min(min(end, n), 100))
    return _mask_segment(start_i, end_i, 0), _mask_segment(start_i, end_i, 64)


@njit(cache=True, nogil=True)
def _body_count(start: int, end: int, n: int) -> np.uint64:
    body_start = max(start, 100)
    body_end = min(end, n)
    if body_end <= body_start:
        return np.uint64(0)
    return np.uint64(body_end - body_start)


@njit(cache=True, nogil=True)
def _single_head_mask(idx: int, n: int):
    if idx < 0 or idx >= min(n, 100):
        return np.uint64(0), np.uint64(0)
    if idx < 64:
        return np.uint64(1) << np.uint64(idx), np.uint64(0)
    return np.uint64(0), np.uint64(1) << np.uint64(idx - 64)


@njit(cache=True, nogil=True)
def pack_edge(
    n: int, fever_start: int, fever_end: int, great_start: int, great_end: int, activation_great_idx: int
):
    fever_lo, fever_hi = _range_mask(fever_start, fever_end, n)
    great_lo, great_hi = _range_mask(great_start, great_end, n)
    if activation_great_idx >= 0:
        activation_lo, activation_hi = _single_head_mask(activation_great_idx, n)
        great_lo = great_lo | activation_lo
        great_hi = great_hi | activation_hi
    body_great = _body_count(great_start, great_end, n)
    body_fever_great = _body_count(max(fever_start, great_start), min(fever_end, great_end), n)
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
        _body_count(fever_start, fever_end, n),
        body_great,
        body_fever_great,
    )


@njit(cache=True, nogil=True)
def pack_edge_eg(
    n: int,
    fever_start: int,
    fever_end: int,
    great_start: int,
    great_end: int,
    activation_great_idx: int,
    early_great_start: int,
    early_great_end: int,
):
    """`pack_edge` plus the early-Great tail [early_great_start, early_great_end): notes pulled into the fever only as
    Greats at a section end. They are in fever and Great, so they join the Great head mask and add to both body_great
    and body_fever_great. The tail is disjoint from the forced-Great run [great_start, great_end) (forced Greats
    precede the activation), so nothing is counted twice."""
    fever_lo, fever_hi, great_lo, great_hi, body_fever, body_great, body_fever_great = pack_edge(
        n, fever_start, fever_end, great_start, great_end, activation_great_idx
    )
    if early_great_end > early_great_start:
        eg_lo, eg_hi = _range_mask(early_great_start, early_great_end, n)
        great_lo = great_lo | eg_lo
        great_hi = great_hi | eg_hi
        eg_body = _body_count(early_great_start, early_great_end, n)
        body_great = body_great + eg_body
        # The early-Great tail lies inside [fever_start, fever_end) by construction, so every
        # tail note is also a fever note -> the overlap equals the tail's body count.
        body_fever_great = body_fever_great + _body_count(
            max(fever_start, early_great_start), min(fever_end, early_great_end), n
        )
    return (fever_lo, fever_hi, great_lo, great_hi, body_fever, body_great, body_fever_great)


@njit(cache=True, nogil=True)
def _latest_activation_hit(
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
def late_edge_extends(edge_e: int, activation_e: int, activation_eg_e: int, edge_eg_e: int) -> bool:
    """Whether the late-Great activation edge carries content the Perfect edge cannot: a strictly
    longer perfect-floor extent OR, on extent ties, a strictly longer early-Great (great-floor)
    reach -- the late hit pushes the fever end further, pulling boundary notes in as fever-Greats
    the Perfect edge's window cannot reach (record 16.33: +337.5 oracle witness). When both tie,
    skipping the late edge stays lossless (its surfaces are the Perfect edge's plus a strictly
    costlier activation Great). The two early-Great (great-floor) extended ends arrive precomputed
    (clamped, `_clamped_end` semantics): `activation_eg_e` at the late-Great hit,
    `edge_eg_e` at the Perfect hit. They are only read when 0 <= activation_e <= edge_e -- both
    edges valid -- so callers may pass any deterministic value on the invalid paths."""
    if activation_e < 0:
        return False
    if activation_e > edge_e:
        return True
    return activation_eg_e > edge_eg_e


@njit(cache=True, nogil=True)
def perfect_activation_hit_for_run(
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
    return _latest_activation_hit(
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
def late_great_activation_hit_for_run(
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
    return _latest_activation_hit(
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
def activation_hit_tables(
    n: int, timestamps, perfect_candidate_timestamps, great_candidate_timestamps, late_great_floor_timestamps
):
    perfect_hit = np.zeros(n, dtype=np.float64)
    perfect_valid = np.zeros(n, dtype=np.int8)
    late_hit = np.zeros(n, dtype=np.float64)
    late_valid = np.zeros(n, dtype=np.int8)
    for activation in range(n):
        hit, valid, _token = perfect_activation_hit_for_run(
            activation, timestamps, perfect_candidate_timestamps, great_candidate_timestamps, activation, 0, n
        )
        perfect_hit[activation] = float(hit)
        perfect_valid[activation] = np.int8(valid)
        hit, valid, _token = late_great_activation_hit_for_run(
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
def fill_crossing_run(start: int, great_run_start: int, k: int, fever_fill_denom: float, n: int):
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
def region2_offset_for_count(start: int, count: int, fever_fill_denom: float, n: int) -> int:
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
def region2_k_scan_stop(action_count: int, fever_fill_denom: float) -> int:
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
def _lane_prefix_signature_reachable(
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
def _fill_window_holds(denom: float, preactivation_count: int, great_before: int, activation_is_great: bool) -> bool:
    """Whether the bar fills on the activation: `preactivation_count` notes of the section precede it, `great_before`
    of them Greats (half a fill unit each), and the activation adds a unit as a Perfect and half as a Great."""
    preactivation_half = 2 * preactivation_count - great_before
    activation_half = 1 if activation_is_great else 2
    fill_before = 0.5 * float(preactivation_half)
    return fill_before < denom and denom <= fill_before + 0.5 * float(activation_half)


@njit(cache=True, nogil=True)
def _later_notes_allow(a: int, h_a, timestamps, perfect_candidate_timestamps, great_candidate_timestamps, run) -> bool:
    """Whether every note after activation `a` can stay at or after its hit `h_a`. Candidate highs are per note (aware
    of held tails), so only the later notes whose chart time is still before the hit are read: once a chart time is
    at or past it, the judgment windows put that note's high there too. run = (Great run start, Great run end, the
    section's end)."""
    g0, g1, end = run
    for j in range(a + 1, end):
        if timestamps[j] >= h_a:
            break
        label_high = great_candidate_timestamps[j] if g0 <= j and j < g1 else perfect_candidate_timestamps[j]
        if label_high < h_a:
            return False
    return True


@njit(cache=True, nogil=True)
def activation_reachable_contiguous_run(
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
    if not _fill_window_holds(denom, preactivation_count, great_before, activation_is_great):
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

    if chart_prefix_legal and _later_notes_allow(
        a, h_a, timestamps, perfect_candidate_timestamps, great_candidate_timestamps, (g0, g1, end)
    ):
        return True

    return bool(
        _lane_prefix_signature_reachable(
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
def minimal_reachable_region_great_end(
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
        hit, valid, token = late_great_activation_hit_for_run(
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
        if activation_reachable_contiguous_run(
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
def has_shifted_head_region(section_start: int, raw_fever_fill: float) -> int:
    if section_start >= 99:
        return 0
    return 1 if int(np.ceil(raw_fever_fill)) > 1 else 0


@njit(cache=True, nogil=True)
def region_core_candidate_capacity(n: int, region_action_count: int, action_k, raw_fever_fill: float) -> int:
    """Exact count of offsets that can reach the expensive region-core producer.

    This is an allocation bound only: validity still belongs exclusively to
    ``_region_run_core``. Counting repeats the cheap offset arithmetic but never
    reconstructs semantics, and the fill pass retains the canonical section/action/offset order.
    """
    region_k_stop = region2_k_scan_stop(region_action_count, raw_fever_fill)
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
        region_offset = region2_offset_for_count(0, k, raw_fever_fill, n)
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


@njit(cache=True, nogil=True)
def _region_run_core(n: int, section_start: int, offset: int, k: int, raw_fever_fill: float, timestamps, hit_times, lanes):
    """The core of the run of `k` forced Greats from `section_start` + `offset`, by the general route: its fill
    crossing, its minimal reachable Great end, its capped activation hits and the lane-aware reachability of its
    activation. Returns (activation, Great end, late-Great hit token, Perfect hit token), a token -1 where the run has
    no such hit, or activation -1 when the run is not valid."""
    run_start = section_start + offset
    activation, is_great = fill_crossing_run(section_start, run_start, k, raw_fever_fill, n)
    if activation < 0:
        return -1, -1, -1, -1
    perfect_candidates, great_candidates = hit_times.perfect_candidate_timestamps, hit_times.great_candidate_timestamps
    if is_great != 0:
        great_end, late_token = minimal_reachable_region_great_end(
            activation, section_start, run_start, raw_fever_fill, timestamps, hit_times, lanes, n
        )
        if great_end < 0:
            return -1, -1, -1, -1
        _hit, _valid, perfect_token = perfect_activation_hit_for_run(
            activation, timestamps, perfect_candidates, great_candidates, run_start, great_end - run_start, n
        )
        return activation, great_end, late_token, perfect_token
    great_end = min(n, run_start + k)
    if great_end <= run_start:
        return -1, -1, -1, -1
    perfect_hit, perfect_valid, perfect_token = perfect_activation_hit_for_run(
        activation, timestamps, perfect_candidates, great_candidates, run_start, great_end - run_start, n
    )
    if perfect_valid == 0 or not activation_reachable_contiguous_run(
        activation,
        float(perfect_hit),
        timestamps,
        hit_times,
        lanes,
        raw_fever_fill,
        (section_start, n, run_start, great_end - run_start),
        0,
    ):
        return -1, -1, -1, -1
    return activation, great_end, -1, perfect_token


@njit(cache=True, nogil=True)
def region_edge(n: int, activation: int, late_hit_id: int, perfect_hit_id: int, perfect_end_by_hit, great_end_by_hit):
    """A region run's edge at one fever time, from the ends its hits reach: (base end, early-Great end), both clamped
    to (activation, n], or (-1, -1) when the run has no edge there. `perfect_hit_id` is the token of its Perfect
    activation hit (-1: none), `late_hit_id` that of its late-Great activation hit (-1: a Perfect crosses the fill). A
    late-Great activation is kept only where it carries more than the Perfect one (late_edge_extends)."""
    perfect_e, perfect_eg_e = -1, -1
    if perfect_hit_id >= 0:
        perfect_e = _clamped_end(n, activation, int(perfect_end_by_hit[perfect_hit_id]))
        perfect_eg_e = _clamped_end(n, activation, int(great_end_by_hit[perfect_hit_id]))
    if late_hit_id < 0:
        return perfect_e, perfect_eg_e
    late_e = _clamped_end(n, activation, int(perfect_end_by_hit[late_hit_id]))
    late_eg_e = _clamped_end(n, activation, int(great_end_by_hit[late_hit_id]))
    if perfect_e >= 0 and not late_edge_extends(perfect_e, late_e, late_eg_e, perfect_eg_e):
        return -1, -1
    return late_e, late_eg_e


@njit(cache=True, nogil=True)
def region_core_table(action_k, raw_fever_fill: float, timestamps, hit_times, lanes):
    """The region runs of one (fill, non-Fever base) group: at a section start, an action's k forced Greats from its
    region-2 offset (where the k-th Great of the run crosses the fill, so the run's last Great activates) and, at the
    first 99 section starts, from the shifted-head offset 1. A run's core (_region_run_core) reads the fill only,
    never a fever time, so every fever time of the group shares the table.

    No fever ends before note ceil(fill), because an activation needs that many notes of its section: the section
    starts 1 .. ceil(fill) are never enumerated, and the table holds no head row and no shifted-head run for them.

    Returns four arrays:
    - head_starts, head_rows: per section start up to note 100 (those the head states and the first section list) its
      valid runs in enumeration order, action ascending and the region-2 offset before the shifted-head one, as rows
      (offset, activation, Great end, late-Great hit, Perfect hit);
    - key_starts, key_rows: per activation its distinct runs as rows (first section start, last section start, Great
      end, late-Great hit, Perfect hit), every section start of a row's interval holding that run. A fever time
      finishes a run from these alone, so the reachability prepass and the body states find a run by its activation
      instead of walking the rows of every (section start, action).

    A region-2 run of activation `a` with k Greats starts at a - k + 1 in the section starting at a - offset - k + 1.
    Its late-Great hit and the notes after it do not depend on k, so per activation they are found once, for the
    first Great end with a valid hit, and a run is valid at once when its chart prefix is legal there (the test of
    activation_reachable_contiguous_run, whose pieces this shares); any other run takes the general route."""
    n = timestamps.shape[0]
    actions = action_k.shape[0]
    if lanes.shape[0] != n:
        raise ValueError("FG region-core lane rows must match n")
    if raw_fever_fill <= 0.0 or not np.isfinite(raw_fever_fill):
        raise ValueError("raw_fever_fill must be finite and > 0")
    head_limit = min(n, 100)
    head_starts = np.zeros(head_limit + 2, dtype=np.int64)
    key_starts = np.zeros(n + 1, dtype=np.int64)
    if raw_fever_fill > float(n):
        return head_starts, np.empty((0, 5), dtype=np.int32), key_starts, np.empty((0, 5), dtype=np.int32)
    perfect_floor, great_floor = hit_times.perfect_floor_timestamps, hit_times.great_floor_timestamps
    perfect_candidates, great_candidates = hit_times.perfect_candidate_timestamps, hit_times.great_candidate_timestamps
    late_great_floor = hit_times.late_great_floor_timestamps
    first_later_section = int(np.ceil(raw_fever_fill)) + 1

    # The actions with a region-2 run: k, the activation's distance from the section start, and its fill window.
    run_action = np.empty(actions, dtype=np.int64)
    run_k = np.empty(actions, dtype=np.int64)
    run_reach = np.empty(actions, dtype=np.int64)
    run_fills = np.empty(actions, dtype=np.bool_)
    runs = 0
    for action in range(region2_k_scan_stop(actions, raw_fever_fill)):
        k = int(action_k[action])
        offset = region2_offset_for_count(0, k, raw_fever_fill, n + k + 2)
        if offset < 1:
            continue
        run_action[runs] = action
        run_k[runs] = k
        run_reach[runs] = offset + k - 1
        run_fills[runs] = _fill_window_holds(raw_fever_fill, offset + k - 1, k - 1, True)
        runs += 1

    # Region-2 runs, activation by activation. keys: rows (activation, first section start, last section start,
    # Great end, late-Great hit, Perfect hit); head_runs: the runs of the head section starts, for the head rows.
    keys = np.empty((n + 64, 6), dtype=np.int32)
    key_count = 0
    head_runs = np.full(((head_limit + 1) * max(1, runs), 3), -1, dtype=np.int32)
    for activation in range(n):
        # The first Great end with a valid late-Great hit: the hit does not depend on where the run starts.
        hit_high = great_candidates[activation]
        last_great_end = activation + 1
        while last_great_end < n and perfect_candidates[last_great_end] < hit_high:
            last_great_end += 1
        great_end = -1
        hit, late_token = 0.0, -1
        for candidate in range(activation + 1, last_great_end + 1):
            hit, valid, late_token = late_great_activation_hit_for_run(
                activation, timestamps, perfect_candidates, great_candidates, late_great_floor, activation,
                candidate - activation, n,
            )
            if valid != 0:
                great_end = candidate
                break
        if great_end < 0:
            continue
        h_a = np.float32(hit)
        legal = not (h_a < great_floor[activation] or h_a > great_candidates[activation]) and _later_notes_allow(
            activation, h_a, timestamps, perfect_candidates, great_candidates, (activation, great_end, n)
        )
        greats_before_legal = activation == 0 or not (great_floor[activation - 1] > h_a)
        _hit, _valid, perfect_token = perfect_activation_hit_for_run(
            activation, timestamps, perfect_candidates, great_candidates, activation, great_end - activation, n
        )
        open_key = -1
        for run in range(runs):
            section_start = activation - run_reach[run]
            if section_start < 0:
                continue
            k = run_k[run]
            run_start = activation - k + 1
            if (
                legal
                and run_fills[run]
                and not (raw_fever_fill > float(n - section_start))
                and not (perfect_floor[run_start - 1] > h_a)
                and (k < 2 or greats_before_legal)
            ):
                run_great_end, run_late, run_perfect = great_end, late_token, perfect_token
            else:
                run_great_end, run_late = minimal_reachable_region_great_end(
                    activation, section_start, run_start, raw_fever_fill, timestamps, hit_times, lanes, n
                )
                if run_great_end < 0:
                    continue
                _hit, _valid, run_perfect = perfect_activation_hit_for_run(
                    activation, timestamps, perfect_candidates, great_candidates, run_start, run_great_end - run_start, n
                )
            if section_start <= head_limit and (section_start == 0 or section_start >= first_later_section):
                head_runs[section_start * runs + run, 0] = run_great_end
                head_runs[section_start * runs + run, 1] = run_late
                head_runs[section_start * runs + run, 2] = run_perfect
            if (
                open_key >= 0
                and keys[open_key, 3] == run_great_end
                and keys[open_key, 4] == run_late
                and keys[open_key, 5] == run_perfect
                and keys[open_key, 1] - 1 <= section_start <= keys[open_key, 2] + 1
            ):
                keys[open_key, 1] = min(keys[open_key, 1], section_start)
                keys[open_key, 2] = max(keys[open_key, 2], section_start)
                continue
            if key_count == keys.shape[0]:
                keys = _rows_ensure(keys, key_count, 1)
            keys[key_count, 0] = activation
            keys[key_count, 1] = section_start
            keys[key_count, 2] = section_start
            keys[key_count, 3] = run_great_end
            keys[key_count, 4] = run_late
            keys[key_count, 5] = run_perfect
            open_key = key_count
            key_count += 1

    # The head rows, section start by section start, and the keys of the shifted-head runs (a run of the same
    # activation at the next section start extends the key its activation made last).
    head = np.empty((256, 5), dtype=np.int32)
    head_count = 0
    last_shifted_key = np.full(n, -1, dtype=np.int32)
    for section_start in range(head_limit + 1):
        head_starts[section_start] = head_count
        if 0 < section_start < first_later_section:
            continue
        run = 0
        for action in range(actions):
            k = int(action_k[action])
            region_offset = -1
            if run < runs and run_action[run] == action:
                if section_start + run_reach[run] < n:
                    region_offset = run_reach[run] - k + 1
                    if head_runs[section_start * runs + run, 0] >= 0:
                        if head_count == head.shape[0]:
                            head = _rows_ensure(head, head_count, 1)
                        head[head_count, _HEAD_OFFSET] = region_offset
                        head[head_count, _HEAD_ACTIVATION] = section_start + run_reach[run]
                        head[head_count, _ROW_GREAT_END] = head_runs[section_start * runs + run, 0]
                        head[head_count, _ROW_LATE_HIT] = head_runs[section_start * runs + run, 1]
                        head[head_count, _ROW_PERFECT_HIT] = head_runs[section_start * runs + run, 2]
                        head_count += 1
                run += 1
            if has_shifted_head_region(section_start, raw_fever_fill) == 0 or region_offset == 1:
                continue
            activation, great_end, late_token, perfect_token = _region_run_core(
                n, section_start, 1, k, raw_fever_fill, timestamps, hit_times, lanes
            )
            if activation < 0:
                continue
            if head_count == head.shape[0]:
                head = _rows_ensure(head, head_count, 1)
            head[head_count, _HEAD_OFFSET] = 1
            head[head_count, _HEAD_ACTIVATION] = activation
            head[head_count, _ROW_GREAT_END] = great_end
            head[head_count, _ROW_LATE_HIT] = late_token
            head[head_count, _ROW_PERFECT_HIT] = perfect_token
            head_count += 1
            key = last_shifted_key[activation]
            if (
                key >= 0
                and keys[key, 3] == great_end
                and keys[key, 4] == late_token
                and keys[key, 5] == perfect_token
                and section_start <= keys[key, 2] + 1
            ):
                keys[key, 2] = section_start
                continue
            if key_count == keys.shape[0]:
                keys = _rows_ensure(keys, key_count, 1)
            keys[key_count, 0] = activation
            keys[key_count, 1] = section_start
            keys[key_count, 2] = section_start
            keys[key_count, 3] = great_end
            keys[key_count, 4] = late_token
            keys[key_count, 5] = perfect_token
            last_shifted_key[activation] = key_count
            key_count += 1
    head_starts[head_limit + 1] = head_count

    # The keys by activation.
    for key in range(key_count):
        key_starts[keys[key, 0] + 1] += 1
    for activation in range(n):
        key_starts[activation + 1] += key_starts[activation]
    key_rows = np.empty((key_count, 5), dtype=np.int32)
    next_row = key_starts[:n].copy()
    for key in range(key_count):
        row = next_row[keys[key, 0]]
        next_row[keys[key, 0]] = row + 1
        for column in range(5):
            key_rows[row, column] = keys[key, column + 1]
    return head_starts, head[:head_count].copy(), key_starts, key_rows


@njit(cache=True, nogil=True)
def reachability_prepass(n: int, first_activations, runs, ends, forced_timing: int, region):
    """The states a play can reach at one fever time, as a mask over the fever ends 0 .. n (n is always reached), and
    the largest early-Great width of an activation that reaches one.

    A fever ends past its activation, so when the notes are taken in ascending order every state before a note is
    final by the time the note is tried as an activation. Its Perfect activation is live when the first section
    activates there (`first_activations` bit 1) or a reached state has it at one of its fill offsets (`runs`: the
    inclusive runs of the later-section offsets); its late-Great activation likewise (bit 2, the late-Great runs);
    a region run of it is live when a section start it holds at is enumerated: the song start, or the note after a
    reached state. A live activation marks every end from its exit end to its early-Great reach. Reached states are
    counted in a prefix sum, so a note costs a few lookups however many states and actions reach it.
    Returns (reachable, width)."""
    perfect_run_starts, perfect_run_ends, late_run_starts, late_run_ends = runs
    for run in range(perfect_run_starts.shape[0]):
        if perfect_run_starts[run] < 0:
            raise ValueError("FG Perfect fill runs must be nonnegative")
    for run in range(late_run_starts.shape[0]):
        if late_run_starts[run] < 0:
            raise ValueError("FG late-Great fill runs must be nonnegative")
    perfect_valid, late_valid = ends.perfect_valid, ends.late_valid
    perfect_e, late_e = ends.perfect_e, ends.late_e
    eg_perfect_e, eg_late_e = ends.eg_perfect_e, ends.eg_late_e
    perfect_exit_e, late_exit_e = ends.perfect_exit_e, ends.late_exit_e
    key_starts, key_rows = region.key_starts, region.key_rows
    perfect_end_by_hit, great_end_by_hit = region.perfect_end_by_hit, region.great_end_by_hit

    reachable = np.zeros(n + 1, dtype=np.bool_)
    reachable[n] = True
    reached = np.zeros(n + 2, dtype=np.int64)
    width = 0
    for activation in range(n):
        reached[activation + 1] = reached[activation] + reachable[activation]
        live = first_activations[activation] & 1
        for run in range(perfect_run_starts.shape[0]):
            if live != 0:
                break
            newest = activation - perfect_run_starts[run]
            if newest >= 0 and reached[newest + 1] > reached[max(0, activation - perfect_run_ends[run])]:
                live = 1
        if live != 0 and perfect_valid[activation] != 0:
            edge_e, eg_e = perfect_e[activation], eg_perfect_e[activation]
            for end in range(min(perfect_exit_e[activation], edge_e), max(edge_e, eg_e) + 1):
                reachable[end] = True
            width = max(width, eg_e - edge_e)
        if forced_timing == 0:
            continue
        live = first_activations[activation] & 2
        for run in range(late_run_starts.shape[0]):
            if live != 0:
                break
            newest = activation - late_run_starts[run]
            if newest >= 0 and reached[newest + 1] > reached[max(0, activation - late_run_ends[run])]:
                live = 1
        if live != 0 and late_valid[activation] != 0:
            edge_e, eg_e = late_e[activation], eg_late_e[activation]
            if perfect_valid[activation] == 0 or late_edge_extends(
                perfect_e[activation], edge_e, eg_e, eg_perfect_e[activation]
            ):
                for end in range(min(late_exit_e[activation], edge_e), max(edge_e, eg_e) + 1):
                    reachable[end] = True
                width = max(width, eg_e - edge_e)
        for key in range(key_starts[activation], key_starts[activation + 1]):
            first_section = key_rows[key, _KEY_FIRST_SECTION]
            if first_section > 0 and reached[key_rows[key, _KEY_LAST_SECTION]] == reached[first_section - 1]:
                continue
            late_hit = key_rows[key, _ROW_LATE_HIT]
            edge_e, eg_e = region_edge(
                n, activation, late_hit, key_rows[key, _ROW_PERFECT_HIT], perfect_end_by_hit, great_end_by_hit
            )
            if edge_e < 0:
                continue
            exit_e = perfect_exit_e[activation] if late_hit < 0 else late_exit_e[activation]
            for end in range(min(exit_e, edge_e), eg_e + 1):
                reachable[end] = True
            width = max(width, eg_e - edge_e)
    return reachable, width


@njit(cache=True, nogil=True)
def touch_body_rows(queue, heads, tails, state: int, key, pair_stamp, best_fever_by_pair, touched_pair):
    """Register the live rows [heads, tails) of every family's queue as the body candidates of `state`: per (normal
    Greats, fever Greats) pair the largest body fever, in the stamped pair table. A row holds (body fever, normal
    Greats + 2 x its reader's state, fever Greats, activation); a row whose normal Greats come out negative for this
    state belongs to none of its plays. key = (pair radix, stamp). Returns (pairs touched, rows read).

    The pack normal Greats x radix + fever Greats is injective only while fever Greats < radix: past it a pair would
    alias another cell, a surface with the wrong Great counts that the decoder then materialises. The radix is sized
    to the geometry's largest fever-Great count, so the check must never fire, and a build that reaches it fails."""
    pair_mod, stamp = key
    touched = 0
    rows = 0
    for family in range(heads.shape[0]):
        for row in range(heads[family], tails[family]):
            rows += 1
            normal_great = queue[family, row, 1] - 2 * state
            if normal_great < 0:
                continue
            fever_great = queue[family, row, 2]
            if fever_great < 0 or fever_great >= pair_mod:
                raise ValueError("FG response body skyline fever-great exceeded pair radix")
            pair = normal_great * pair_mod + fever_great
            if pair >= best_fever_by_pair.shape[0]:
                raise ValueError("FG response body skyline pair bound was too small")
            body_fever = queue[family, row, 0]
            if pair_stamp[pair] != stamp:
                pair_stamp[pair] = stamp
                best_fever_by_pair[pair] = body_fever
                touched_pair[touched] = pair
                touched += 1
            elif body_fever > best_fever_by_pair[pair]:
                best_fever_by_pair[pair] = body_fever
    return touched, rows


# The realizable stat box of the lossless cone filters. A surface's score is MULTILINEAR in (E = 2 x primary + secondary,
# b = the Perfect Points bonus, c = combo_mul, f = fever_mul): the base value v is E + b and the Great base g is 2E/3 + 150, so
# g < v everywhere (v - g >= 50) and every floor's max/min is resolved, and a multilinear function attains its extrema at the
# box VERTICES. A surface's exact dominance over the WHOLE box is decided at its 16 corners, with the integer floors bounded
# by a per-pair margin. No probe sampling. `b`, `c` and `f` span the gear's curves (gamedata.stat_curves), E every stat
# line. fg_cache._assert_head_dominance_box_covers fails loud if a gear rebalance leaves the box.
_HEAD_DOM_E = (0.0, 7600.0)
HEAD_DOM_B = (200.0, 485.0)
HEAD_DOM_C = (1.95, 2.72)
HEAD_DOM_F = (2.95, 5.48)
# Body floors hit combo_val/fever_val plus the two great penalties; 2x per body-count delta is a
# safe (over-)estimate of how far they can perturb a pairwise score difference.
_HEAD_DOM_BODY_FLOOR_W = 2
# The Great base's two floors put it up to 2 under 2E/3 + 150: at most 2 x c x f on each note judged Great in one row only.
_HEAD_DOM_GREAT_FLOOR_W = 30


@njit(cache=True, nogil=True)
def _popcount64(x):
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return int((x * np.uint64(0x0101010101010101)) >> np.uint64(56))


@njit(cache=True, nogil=True)
def _surface_margin(left, right) -> float:
    """The most the score's integer floors can move the gap between two surface rows: their head-class Hamming distance
    + the body floor weight x their body-count L1 distance + the Great floor weight x the Great notes they differ on."""
    normal_greats = abs(int((np.int64(left[5]) - np.int64(left[6])) - (np.int64(right[5]) - np.int64(right[6]))))
    fever_greats = abs(int(np.int64(left[6]) - np.int64(right[6])))
    return float(
        _popcount64((left[0] ^ right[0]) | (left[2] ^ right[2]))
        + _popcount64((left[1] ^ right[1]) | (left[3] ^ right[3]))
        + _HEAD_DOM_BODY_FLOOR_W * (abs(int(np.int64(left[4]) - np.int64(right[4]))) + normal_greats + fever_greats)
        + _HEAD_DOM_GREAT_FLOOR_W
        * (
            _popcount64(left[2] ^ right[2])
            + _popcount64(left[3] ^ right[3])
            + normal_greats
            + fever_greats
        )
    )


@njit(cache=True, nogil=True)
def _corner_score(basis, v, c, f, g, use_hi_c: int) -> float:
    gv = g - v
    body_dn = v * c * (f - 1.0)
    pen_n = c * gv
    pen_f = c * f * gv
    if use_hi_c == 0:
        head = (
            gv * basis[_BASIS_C_LO]
            + v * (f - 1.0) * basis[_BASIS_B_LO]
            + gv * (f - 1.0) * basis[_BASIS_D_LO]
        )
    else:
        head = (
            gv * basis[_BASIS_C_HI]
            + v * (f - 1.0) * basis[_BASIS_B_HI]
            + gv * (f - 1.0) * basis[_BASIS_D_HI]
        )
    return (
        head
        + float(basis[_BASIS_BODY_FEVER]) * body_dn
        + float(basis[_BASIS_BODY_NORMAL_GREAT]) * pen_n
        + float(basis[_BASIS_BODY_FEVER_GREAT]) * pen_f
    )


@njit(cache=True, nogil=True)
def _corner_scores(rows, terms, term_of):
    """(m, 16) each surface row's relative score at the 16 corners of the _HEAD_DOM box (E, c, f, b, each low and high);
    row i's head terms are terms[term_of[i]] (_head_pattern_basis's b, c, d at the low and high combo)."""
    m = rows.shape[0]
    scores = np.empty((m, 16), dtype=np.float64)
    for i in range(m):
        head = terms[term_of[i]]
        basis = (
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
        for e in _HEAD_DOM_E:
            g = e * 2.0 / 3.0 + 150.0
            for ic in range(2):
                for f in HEAD_DOM_F:
                    for b in HEAD_DOM_B:
                        scores[i, col] = _corner_score(basis, e + b, HEAD_DOM_C[ic], f, g, ic)
                        col += 1
    return scores


@njit(cache=True, nogil=True)
def _cone_kept(rows, scores):
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
            if not _scores_dominate(scores, k, i, 0.0):
                continue
            if _scores_dominate(scores, k, i, _surface_margin(rows[k], rows[i])):
                dominated = True
                break
        if not dominated:
            kept_rows[kept_count] = i
            kept_count += 1
    return kept_rows[:kept_count]


@njit(cache=True, nogil=True)
def _scores_dominate(scores, left_idx: int, right_idx: int, margin: float) -> bool:
    for cc in range(16):
        if scores[left_idx, cc] - scores[right_idx, cc] < margin:
            return False
    return True


@njit(cache=True, nogil=True)
def head_envelope_filter(frontier, lo_pos, hi_pos):
    """LOSSLESS prune of the head frontier to its cone-Pareto set -- the surfaces that are best for SOME realizable stat
    cell. The head+body score is multilinear on the _HEAD_DOM box, so its unfloored value hits its extrema at the 16 corners.
    Surface K dominates C over the WHOLE box iff unfloored score(K)-score(C) >= the per-pair floor margin at all 16 corners.
    This is the head analog of `_body_cone_filter`: best-preserving for EVERY realizable cell, by a 16-corner proof, not
    probe sampling. Composition-safe (the score is additive over disjoint edge/tail head ranges), so an envelope-minimal
    tail stays representative as the DP prepends edges."""
    m = frontier.shape[0]
    if m < 2:
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
            head = _head_pattern_basis(fl, fh, gl, gh, lo_pos, hi_pos)
            for t in range(6):
                terms[runs, t] = head[t]
            runs += 1
        term_of[i] = runs - 1
    kept_rows = _cone_kept(frontier, _corner_scores(frontier, terms, term_of))
    out = np.empty((kept_rows.shape[0], 7), dtype=np.uint64)
    for ki in range(kept_rows.shape[0]):
        out[ki] = frontier[kept_rows[ki]]
    return out


@njit(cache=True, nogil=True)
def _body_cone_filter(values, count: int) -> int:
    """Drops the rows (body fever, normal Greats, fever Greats, _) of a body state's frontier that another row of it dominates
    at every corner of the stat box. Every play through the state adds the same counts and head to both, so the dominance
    holds for all of them. Keeps the rows' order; returns their new count."""
    if count < 2:
        return count
    rows = np.zeros((count, 7), dtype=np.uint64)
    for i in range(count):
        rows[i, 4] = np.uint64(values[i, 0])
        rows[i, 5] = np.uint64(values[i, 1] + values[i, 2])
        rows[i, 6] = np.uint64(values[i, 2])
    kept = np.sort(_cone_kept(rows, _corner_scores(rows, np.zeros((1, 6)), np.zeros(count, np.int64))))
    for i in range(kept.shape[0]):
        values[i] = values[kept[i]]
    return kept.shape[0]


@njit(cache=True, nogil=True)
def _head_pattern_basis(fl, fh, gl, gh, lo_pos: int, hi_pos: int):
    """Head-only portion of a surface's basis at the box's low and high combo, shared by every row with this mask
    pattern."""
    lo = lo_pos
    hi = hi_pos
    hlen = hi - lo
    one = np.uint64(1)
    k_lo = (HEAD_DOM_C[0] - 1.0) / 100.0
    k_hi = (HEAD_DOM_C[1] - 1.0) / 100.0
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


@njit(cache=True, nogil=True)
def _skyline_hulls(points, count: int, limit: int, fen_values, fen_stamps, fen_stamp: int):
    """Each tag's skyline with per-normal-Great upper hulls, in place: `points` rows (body fever, normal Greats, fever
    Greats, tag) come sorted by tag, normal Greats, fever Greats and then body fever descending, and a row repeating
    the (tag, normal Greats, fever Greats) of the row before it is skipped.

    A point is kept iff its body fever beats every earlier point of its tag with fever Greats <= its own (stamped
    Fenwick prefix maxima over fever Greats below `limit` - 1, one stamp per tag). Those include the kept rows of its
    own normal-Great level, so a level's kept rows have strictly increasing body fever, and its upper hull of (body
    fever, -fever Greats) runs incrementally on them. The Fenwick takes one update per point, kept or not, so it does
    not depend on what the hull removes. Kept rows go to the front of `points`: a kept row never lies past its own
    point. Returns (kept rows, the last stamp used)."""
    kept = 0
    level = -1
    level_base = 0
    tag = -1
    seen_level = -1
    seen_fever_great = -1
    for index in range(count):
        bf, ng, fg = points[index, 0], points[index, 1], points[index, 2]
        if points[index, 3] != tag:
            tag = points[index, 3]
            fen_stamp += 1
            level = -1
        elif ng == seen_level and fg == seen_fever_great:
            continue
        seen_level = ng
        seen_fever_great = fg
        best = -1
        cursor = fg + 1
        while cursor > 0:
            if fen_stamps[cursor] == fen_stamp and fen_values[cursor] > best:
                best = fen_values[cursor]
            cursor -= cursor & -cursor
        if bf > best:
            if ng != level:
                level = ng
                level_base = kept
            while kept - level_base >= 2:
                cross = (points[kept - 1, 0] - points[kept - 2, 0]) * (points[kept - 2, 2] - fg) - (
                    points[kept - 2, 2] - points[kept - 1, 2]
                ) * (bf - points[kept - 2, 0])
                if cross >= 0:
                    kept -= 1
                else:
                    break
            points[kept, 0] = bf
            points[kept, 1] = ng
            points[kept, 2] = fg
            points[kept, 3] = tag
            kept += 1
        cursor = fg + 1
        while cursor < limit:
            if fen_stamps[cursor] != fen_stamp:
                fen_stamps[cursor] = fen_stamp
                fen_values[cursor] = bf
            elif bf > fen_values[cursor]:
                fen_values[cursor] = bf
            cursor += cursor & -cursor
    return kept, fen_stamp


@njit(cache=True, nogil=True)
def reduce_touched_body_pairs(
    pair_mod: int, touched_pair, touched_count: int, best_fever_by_pair, bit_values, bit_stamps, bit_stamp: int, stack
):
    """A body state's frontier from its touched pairs: rows (body fever, normal Greats, fever Greats, 0) in the reusable
    `stack`, which grows as needed. Returns (stack, rows).

    `touched_pair[:touched_count]` holds distinct pair indices (touch_body_rows adds a pair on its first stamp only),
    and nothing reads their insertion order, so they are sorted in place: ascending pair index is (normal Greats,
    fever Greats) ascending, the order `_skyline_hulls` reduces. The Fenwick spans the batch's fever-Great range and
    is stamped `bit_stamp`.

    For a fixed stat cell the body score is linear in the three counts, A x body fever - p x normal Greats - q x fever
    Greats with A, p, q >= 0, and an early-Great extension adds points at a constant normal-Great count. So within a
    normal-Great level the useful set is the upper hull in (body fever, -fever Greats): pruning to it loses nothing
    for any cell, is invariant under shifts, and survives the DP adding section counts."""
    if touched_count <= 0:
        return stack, 0
    touched_pair[:touched_count].sort()
    stack = _rows_ensure(stack, 0, touched_count)
    max_fever_great = 0
    for index in range(touched_count):
        pair = touched_pair[index]
        normal_great = pair // pair_mod
        fever_great = pair - normal_great * pair_mod
        stack[index, 0] = best_fever_by_pair[pair]
        stack[index, 1] = normal_great
        stack[index, 2] = fever_great
        stack[index, 3] = 0
        max_fever_great = max(max_fever_great, fever_great)
    count, _stamp = _skyline_hulls(
        stack, touched_count, min(max_fever_great + 2, bit_values.shape[0]), bit_values, bit_stamps, bit_stamp - 1
    )
    return stack, count


@njit(cache=True, nogil=True)
def _points_append(buf, base: int, write: int, cf: int, cn: int, cq: int) -> int:
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
def _points_skyline(buf, start: int, end: int) -> int:
    """Reduce rows [start, end) to their Pareto skyline in place (the dominance of `_points_append`); returns
    the new end. A packet spanning several fever ends can hold points one end dominates with another's, and the queue's
    unions keep a packet verbatim when it is the only operand."""
    kept = start
    for idx in range(start, end):
        cf = buf[idx, 0]
        cn = buf[idx, 1]
        cq = buf[idx, 2]
        kept = _points_append(buf, start, int(kept), int(cf), int(cn), int(cq))
    return int(kept)


@njit(cache=True, nogil=True)
def packet_families(sizes, raw_fever_fill: float, plan, forced_timing: int):
    """The activation families of a body state, as rows (kind, defect, first offset, last offset): a family is a run of
    consecutive activation offsets past the state whose forced Greats grow by two per offset, so `defect` = forced
    Greats - 2 x offset is one number and an activation's packet serves every state that reaches it (_body_tails).
    Perfect activations come first, then with forced-Great timing the late-Great activations (their forced Greats
    are the ones before the activation) and the region-2 runs (an action's k Greats end on the activation: offset =
    its region offset + k, forced Greats k - 1)."""
    n, action_count, region_action_count = sizes
    action_k, later_fill, later_forced, later_activation_forced = plan
    families = np.empty((2 * action_count + region_action_count, 4), dtype=np.int64)
    count = 0
    for kind in range(3 if forced_timing != 0 else 1):
        first_action, actions = 0, action_count
        if kind == _REGION_FAMILY:
            first_action, actions = 1, region2_k_scan_stop(region_action_count, raw_fever_fill)
        previous_offset = -2
        previous_defect = 0
        for action in range(first_action, actions):
            if kind == _REGION_FAMILY:
                k = int(action_k[action])
                region_offset = region2_offset_for_count(0, k, raw_fever_fill, n + k + 2)
                if region_offset < 1:
                    continue
                offset = region_offset + k
                forced = k - 1
            else:
                offset = int(later_fill[action])
                forced = int(later_forced[action]) if kind == _PERFECT_FAMILY else int(later_activation_forced[action])
                if kind == _LATE_FAMILY and forced < 0:
                    continue
            defect = forced - 2 * offset
            if offset == previous_offset + 1 and defect == previous_defect:
                families[count - 1, 3] = offset
            else:
                families[count, 0] = kind
                families[count, 1] = defect
                families[count, 2] = offset
                families[count, 3] = offset
                count += 1
            previous_offset = offset
            previous_defect = defect
    return families[:count]


@njit(cache=True, nogil=True)
def _clamped_end(n: int, activation_idx: int, raw_end_idx: int) -> int:
    edge_e = raw_end_idx
    if edge_e <= activation_idx:
        edge_e = activation_idx + 1
    if edge_e > n:
        edge_e = n
    return edge_e


@njit(cache=True, nogil=True)
def _body_tails(n: int, families, reachable, region, ends, scratch):
    """The tail frontier of every reachable body state, states n - 1 down to 100: rows (body fever, body Greats, fever
    Greats) of `body_values`, addressed per state by body_starts / body_counts. State n holds the tail of a play that
    never activates again, and a state with no candidate shares it.

    A state's candidates are the packets of its families' activations (packet_families): an activation's edge at each
    of its fever ends, joined with that end's tail frontier. A packet row (body fever, normal Greats + 2 x activation
    + defect, fever Greats) does not depend on the state it serves, which reads its normal Greats as the second column
    - 2 x state. So each family keeps the packets of its live window [state + first offset, state + last offset] in a
    queue, rows (.., activation) in push order: an activation is built once, when a window first reaches it, and
    leaves at the head when the windows have passed it. A queued row that a new row dominates is dropped: the new
    activation is smaller, so it stays in every later window the old one is in. The queue so keeps every point of its
    window's Pareto set.

    An activation's ends are its base end, every earlier end from its exit end (the fever can end early) and every
    later end up to its early-Great reach (the notes from the base end on join the fever as Greats). A region-2
    activation takes its run from the region table: the late-Great run of the activation at the section start its
    family's first offset puts it at. Where the table holds none, the run has no valid core.

    The per-activation and per-row loops are written out in this function: a helper that takes arrays costs the
    kernel several times its own work on every call.

    Returns (body_values, body_starts, body_counts, states evaluated, rows generated, rows retained, the largest
    frontier, the pair epoch, the bit epoch)."""
    pair_mod, best_fever_by_pair, pair_stamp, touched_pair, pair_epoch, bit_values, bit_stamps, bit_epoch = scratch
    perfect_valid, late_valid = ends.perfect_valid, ends.late_valid
    perfect_e, late_e = ends.perfect_e, ends.late_e
    eg_perfect_e, eg_late_e = ends.eg_perfect_e, ends.eg_late_e
    perfect_exit_e, late_exit_e = ends.perfect_exit_e, ends.late_exit_e
    key_starts, key_rows = region.key_starts, region.key_rows
    perfect_end_by_hit, great_end_by_hit = region.perfect_end_by_hit, region.great_end_by_hit

    body_values = np.empty((1024, 3), dtype=np.uint64)
    body_values[0, 0] = 0
    body_values[0, 1] = 0
    body_values[0, 2] = 0
    body_starts = np.zeros(n + 1, dtype=np.int32)
    body_counts = np.zeros(n + 1, dtype=np.int32)
    body_counts[n] = 1
    cursor = 1
    family_count = families.shape[0]
    queue = np.empty((max(1, family_count), 16, 4), dtype=np.int64)
    heads = np.zeros(max(1, family_count), dtype=np.int64)
    tails = np.zeros(max(1, family_count), dtype=np.int64)
    next_push = np.full(max(1, family_count), n - 1, dtype=np.int64)
    packet = np.empty((64, 3), dtype=np.int64)
    kept = np.empty((1024, 4), dtype=np.int64)
    states = 0
    generated = 0
    retained = 1
    largest = 1
    for state in range(n - 1, 99, -1):
        if not reachable[state]:
            continue
        for family in range(family_count):
            kind, defect, first_offset = families[family, 0], families[family, 1], families[family, 2]
            newest = state + families[family, 3]
            head = heads[family]
            while head < tails[family] and queue[family, head, 3] > newest:
                head += 1
            heads[family] = head
            first_push = min(next_push[family], newest - first_offset) + first_offset
            next_push[family] = state - 1
            for activation in range(first_push, state + first_offset - 1, -1):
                if activation >= n:
                    continue
                # The activation's edge: its base end, early-Great reach and earliest end.
                run_start, great_end = 0, 0
                if kind == _REGION_FAMILY:
                    k = 2 * first_offset + defect + 1
                    run_start = activation - k + 1
                    section_start = activation - first_offset + 1
                    key = -1
                    for candidate in range(key_starts[activation], key_starts[activation + 1]):
                        if (
                            key_rows[candidate, _ROW_LATE_HIT] >= 0
                            and key_rows[candidate, _KEY_FIRST_SECTION] <= section_start
                            and section_start <= key_rows[candidate, _KEY_LAST_SECTION]
                        ):
                            key = candidate
                            break
                    if key < 0:
                        continue
                    edge_e, eg_e = region_edge(
                        n, activation, key_rows[key, _ROW_LATE_HIT], key_rows[key, _ROW_PERFECT_HIT], perfect_end_by_hit,
                        great_end_by_hit,
                    )
                    if edge_e < 0:
                        continue
                    great_end = key_rows[key, _ROW_GREAT_END]
                    lo_e = min(late_exit_e[activation], edge_e)
                elif perfect_valid[activation] == 0:
                    continue
                elif kind == _PERFECT_FAMILY:
                    edge_e, eg_e = perfect_e[activation], eg_perfect_e[activation]
                    lo_e = min(perfect_exit_e[activation], edge_e)
                else:
                    if late_valid[activation] == 0:
                        continue
                    edge_e, eg_e = late_e[activation], eg_late_e[activation]
                    if not late_edge_extends(perfect_e[activation], edge_e, eg_e, eg_perfect_e[activation]):
                        continue
                    lo_e = min(late_exit_e[activation], edge_e)
                need = 0
                for end in range(lo_e, eg_e + 1):
                    need += body_counts[end]
                if need <= 0:
                    continue
                if need > packet.shape[0]:
                    packet = _rows_ensure(packet, 0, need)
                # The packet: per end, its tail rows moved by the edge's counts there.
                rows = 0
                for end in range(lo_e, eg_e + 1):
                    if body_counts[end] <= 0:
                        continue
                    if kind == _REGION_FAMILY:
                        if end <= edge_e:
                            edge = pack_edge(n, activation, end, run_start, great_end, activation)
                        else:
                            edge = pack_edge_eg(n, activation, end, run_start, great_end, activation, edge_e, end)
                        fever = np.int64(edge[4])
                        fever_great = np.int64(edge[6])
                        normal = 2 * activation + (np.int64(edge[5]) - fever_great) - 2 * first_offset
                    else:
                        fever = end - activation
                        fever_great = kind + max(0, end - edge_e)
                        normal = 2 * activation + defect
                    for tail in range(body_starts[end], body_starts[end] + body_counts[end]):
                        tail_fever_great = np.int64(body_values[tail, 2])
                        packet[rows, 0] = np.int64(body_values[tail, 0]) + fever
                        packet[rows, 1] = np.int64(body_values[tail, 1]) - tail_fever_great + normal
                        packet[rows, 2] = tail_fever_great + fever_great
                        rows += 1
                if lo_e < eg_e:
                    rows = _points_skyline(packet, 0, rows)
                # Into the family's queue: drop the rows the packet dominates, then append it.
                write = head
                for queued in range(head, tails[family]):
                    dominated = False
                    for p in range(rows):
                        if (
                            packet[p, 0] >= queue[family, queued, 0]
                            and packet[p, 1] <= queue[family, queued, 1]
                            and packet[p, 2] <= queue[family, queued, 2]
                        ):
                            dominated = True
                            break
                    if not dominated:
                        if write != queued:
                            for column in range(4):
                                queue[family, write, column] = queue[family, queued, column]
                        write += 1
                if write + rows > queue.shape[1]:
                    for queued in range(head, write):
                        for column in range(4):
                            queue[family, queued - head, column] = queue[family, queued, column]
                    write -= head
                    head = 0
                    if write + rows > queue.shape[1]:
                        capacity = queue.shape[1]
                        while capacity < write + rows:
                            capacity *= 2
                        grown = np.empty((queue.shape[0], capacity, 4), dtype=np.int64)
                        grown[:, : queue.shape[1]] = queue
                        queue = grown
                for p in range(rows):
                    queue[family, write, 0] = packet[p, 0]
                    queue[family, write, 1] = packet[p, 1]
                    queue[family, write, 2] = packet[p, 2]
                    queue[family, write, 3] = activation
                    write += 1
                heads[family] = head
                tails[family] = write

        states += 1
        pair_epoch += 1
        touched, read = touch_body_rows(
            queue, heads, tails, state, (pair_mod, pair_epoch), pair_stamp, best_fever_by_pair, touched_pair
        )
        generated += read
        frontier = 1
        if touched > 0:
            bit_epoch += 1
            kept, frontier = reduce_touched_body_pairs(
                pair_mod, touched_pair, touched, best_fever_by_pair, bit_values, bit_stamps, bit_epoch, kept
            )
            frontier = _body_cone_filter(kept, frontier)
            body_values = _rows_ensure(body_values, cursor, frontier)
            body_starts[state] = cursor
            for row in range(frontier):
                body_values[cursor + row, 0] = np.uint64(kept[row, 0])
                body_values[cursor + row, 1] = np.uint64(kept[row, 1] + kept[row, 2])
                body_values[cursor + row, 2] = np.uint64(kept[row, 2])
            cursor += frontier
        body_counts[state] = frontier
        retained += frontier
        largest = max(largest, frontier)
    return body_values, body_starts, body_counts, states, generated, retained, largest, pair_epoch, bit_epoch


@njit(cache=True, nogil=True)
def _rows_ensure(values, used: int, extra: int):
    """Room for `extra` more rows in a (cap, w) row store, which doubles until they fit; rows [0, used) are kept, so
    offsets into them stay valid."""
    need = used + extra
    cap = values.shape[0]
    if need <= cap:
        return values
    while cap < need:
        cap *= 2
    grown = np.empty((cap, values.shape[1]), dtype=values.dtype)
    grown[:used] = values[:used]
    return grown


@njit(cache=True, nogil=True, inline="always")
def _add_entry(entries, count: int, activation: int, section_ends, run, activation_great_idx: int) -> int:
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
def _section_entries(
    entries, count: int, section, fills, forced, activation_forced, ends, use_forced_great_timing_i: int
):
    """Every action's activation sections for one section starting at `section_start` (activation = state + fill):
    the Perfect activation and, when it carries more than that edge (see late_edge_extends), the late-Great
    one."""
    n, action_count, state, section_start = section
    entries = _rows_ensure(entries, int(count), 2 * action_count)
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
            count = _add_entry(
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
        if not late_edge_extends(
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
        count = _add_entry(
            entries,
            count,
            activation,
            (activation_e, int(ends.late_exit_e[activation]), int(ends.eg_late_e[activation])),
            (section_start, min(n, section_start + prefix_forced)),
            activation,
        )
    return entries, int(count)


@njit(cache=True, nogil=True)
def _region2_entries(entries, count: int, n: int, section_start: int, region, perfect_exit_e, late_exit_e):
    """The region-run activation sections of one head section start (a forced-Great run moves the activation): the
    region table's head rows for `section_start`, each finished for this fever time (its ends and early-Great
    reach)."""
    head_starts, head_rows = region.head_starts, region.head_rows
    entries = _rows_ensure(entries, count, head_starts[section_start + 1] - head_starts[section_start])
    for row in range(head_starts[section_start], head_starts[section_start + 1]):
        activation = int(head_rows[row, _HEAD_ACTIVATION])
        late_hit = int(head_rows[row, _ROW_LATE_HIT])
        edge_e, eg_e = region_edge(
            n, activation, late_hit, int(head_rows[row, _ROW_PERFECT_HIT]), region.perfect_end_by_hit,
            region.great_end_by_hit,
        )
        if edge_e < 0:
            continue
        exit_e = perfect_exit_e if late_hit < 0 else late_exit_e
        count = _add_entry(
            entries,
            count,
            activation,
            (edge_e, int(exit_e[activation]), eg_e),
            (section_start + int(head_rows[row, _HEAD_OFFSET]), int(head_rows[row, _ROW_GREAT_END])),
            activation if late_hit >= 0 else -1,
        )
    return entries, count


@njit(cache=True, nogil=True, inline="always")
def mask_hash(w0, w1, w2, w3):
    h = w0 * np.uint64(0x9E3779B97F4A7C15)
    h = (h ^ (h >> np.uint64(29)) ^ w1) * np.uint64(0xBF58476D1CE4E5B9)
    h = (h ^ (h >> np.uint64(31)) ^ w2) * np.uint64(0x94D049BB133111EB)
    h = (h ^ (h >> np.uint64(29)) ^ w3) * np.uint64(0x9E3779B97F4A7C15)
    return h ^ (h >> np.uint64(32))


@njit(cache=True, nogil=True, inline="always")
def _intern_reserved(slots, masks, patterns: int, w0, w1, w2, w3):
    """Id of the head-mask pattern (w0..w3) in an open-addressing table with room for one more pattern; a new pattern
    gets the next id. Returns (id, patterns)."""
    cap = slots.shape[0]
    slot = np.int64(mask_hash(w0, w1, w2, w3) & np.uint64(cap - 1))
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
def _pattern_id(slots, masks, patterns: int, w0, w1, w2, w3):
    """`_intern_reserved` on tables that grow as needed. Returns (slots, masks, id, patterns)."""
    if 2 * (patterns + 1) > slots.shape[0]:
        cap = 2 * slots.shape[0]
        slots = np.full(cap, -1, dtype=np.int64)
        for pid in range(patterns):
            slot = np.int64(
                mask_hash(masks[pid, 0], masks[pid, 1], masks[pid, 2], masks[pid, 3]) & np.uint64(cap - 1)
            )
            while slots[slot] >= 0:
                slot = (slot + 1) & (cap - 1)
            slots[slot] = pid
    if patterns >= masks.shape[0]:
        grown = np.empty((2 * masks.shape[0], 4), dtype=np.uint64)
        grown[:patterns] = masks[:patterns]
        masks = grown
    pid, patterns = _intern_reserved(slots, masks, patterns, w0, w1, w2, w3)
    return slots, masks, pid, patterns


@njit(cache=True, nogil=True)
def _entry_end_points(points, m: int, slots, masks, patterns: int, edge, end_e: int, head):
    """The candidates of one edge ending at `end_e`, joined with that state's tail frontier: body tail points, the
    terminal state (the edge alone), or a head state's rows (their masks combine with the edge's)."""
    body_values, body_starts, body_counts, head_pool, head_state_start, head_state_count, head_limit = head
    if end_e >= 100 or end_e >= int(head_limit):
        slots, masks, pid, patterns = _pattern_id(slots, masks, patterns, edge[0], edge[1], edge[2], edge[3])
        bf0 = np.int64(edge[4])
        ng0 = np.int64(edge[5]) - np.int64(edge[6])
        fg0 = np.int64(edge[6])
        if end_e >= 100:
            tails = int(body_counts[end_e])
            start = int(body_starts[end_e])
            points = _rows_ensure(points, m, tails)
            for idx in range(tails):
                points[m, 0] = bf0 + np.int64(body_values[start + idx, 0])
                points[m, 1] = ng0 + np.int64(body_values[start + idx, 1]) - np.int64(body_values[start + idx, 2])
                points[m, 2] = fg0 + np.int64(body_values[start + idx, 2])
                points[m, 3] = pid
                m += 1
        else:
            points = _rows_ensure(points, m, 1)
            points[m, 0] = bf0
            points[m, 1] = ng0
            points[m, 2] = fg0
            points[m, 3] = pid
            m += 1
        return points, m, slots, masks, int(patterns)
    start = int(head_state_start[end_e])
    rows = int(head_state_count[end_e])
    points = _rows_ensure(points, m, rows)
    for idx in range(rows):
        row = start + idx
        slots, masks, pid, patterns = _pattern_id(
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
def _pattern_dominates(masks, q: int, p: int) -> bool:
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
def _int_slot(slot_key, key: int, cap: int) -> int:
    """The slot of a non-negative key in an open-addressing table (`slot_key` = -1 when empty): the slot holding it,
    else the empty slot where it goes."""
    slot = np.int64((np.uint64(key) * np.uint64(0x9E3779B97F4A7C15)) >> np.uint64(32)) & (cap - 1)
    while slot_key[slot] >= 0 and slot_key[slot] != key:
        slot = (slot + 1) & (cap - 1)
    return slot


@njit(cache=True, nogil=True)
def _state_points(entries, count: int, n: int, head, points, slots, masks, arena):
    """All candidate points (body fever, normal Greats, fever Greats, pattern id) of one state's activation sections.

    A section whose activation and ends all lie in the body, with Great counts constant over its early ends and
    growing one per step over its early-Great ends (only the fever window's overlap with the Great run can change
    them), is a shift (-activation, normal Greats, fever Greats) of its windows' skylines. Such sections are grouped
    by their window pair: each group's skylines are computed once, and a section whose shift a section of a dominating
    pattern (or its own) dominates adds nothing. Any other section is joined end by end.
    Returns (points, m, slots, masks, arena)."""
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
        at_base = pack_edge(n, int(activation), int(base_e), int(great_start), int(great_end), int(agi))
        if (
            prev_pid >= 0
            and masks[prev_pid, 0] == at_base[0]
            and masks[prev_pid, 1] == at_base[1]
            and masks[prev_pid, 2] == at_base[2]
            and masks[prev_pid, 3] == at_base[3]
        ):
            pid = prev_pid
        else:
            pid, patterns = _intern_reserved(
                slots, masks, patterns, at_base[0], at_base[1], at_base[2], at_base[3]
            )
        prev_pid = pid
        key = (lo_e * width + base_e) * width + (eg_e if eg_e > base_e else 0)
        info[idx, 0] = pid
        info[idx, 1] = np.int64(at_base[5]) - np.int64(at_base[6])
        info[idx, 2] = np.int64(at_base[6])
        info[idx, 3] = -1
        slot = _int_slot(table_key, int(key), table_cap)
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
                    and _pattern_dominates(masks, info[b_idx, 0], info[a_idx, 0])
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
                    arena = _rows_ensure(arena, all_rows, tails)
                for t in range(tails):
                    bf = end_e + np.int64(body_values[start + t, 0])
                    ng = np.int64(body_values[start + t, 1]) - np.int64(body_values[start + t, 2])
                    fg = np.int64(body_values[start + t, 2]) + (end_e if kind == 1 else 0)
                    all_rows = _points_append(arena, exit_rows if kind == 1 else 0, all_rows, bf, ng, fg)
            if kind == 0:
                exit_rows = all_rows
        idx = first
        while idx >= 0:
            if info[idx, 0] >= 0:
                activation, base_e = entries[idx, 0], entries[idx, 1]
                pid, ng, fg = info[idx, 0], info[idx, 1], info[idx, 2]
                if m + all_rows > points.shape[0]:
                    points = _rows_ensure(points, m, all_rows)
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
        points, m, slots, masks, patterns = _entry_end_points(
            points,
            m,
            slots,
            masks,
            patterns,
            pack_edge(n, int(activation), int(base_e), int(great_start), int(great_end), int(agi)),
            int(base_e),
            head,
        )
        for end_e in range(int(base_e) + 1, int(eg_e) + 1):
            edge = pack_edge_eg(
                n, int(activation), end_e, int(great_start), int(great_end), int(agi), int(base_e), end_e
            )
            points, m, slots, masks, patterns = _entry_end_points(
                points, m, slots, masks, patterns, edge, end_e, head
            )
        for end_e in range(int(lo_e), int(base_e)):
            edge = pack_edge(n, int(activation), end_e, int(great_start), int(great_end), int(agi))
            points, m, slots, masks, patterns = _entry_end_points(
                points, m, slots, masks, patterns, edge, end_e, head
            )
    return points, int(m), slots, masks, arena


@njit(cache=True, nogil=True)
def _points_frontier(points, masks, sizes, head, fen_values, fen_stamps, fen_stamp):
    """A state's frontier from its candidate points, by three reductions, cheapest and strongest first:

    1. Each pattern's skyline with per-normal-Great upper hulls (`_skyline_hulls`, the body states' reduction, with
       the pattern as the tag): exact, since same-pattern points share their head score and the body score is linear
       in the three counts. The Fenwick spans the state's fever-Great range only.
    2. The head envelope (cone) filter across patterns (`head_envelope_filter`, lossless by its 16-corner
       proof): it compares surfaces of different head patterns, which structural dominance cannot.
    3. The exact structural Pareto set of what remains: rows visited by body fever desc, normal Greats asc, fever
       Greats asc, then pattern rank (Great bits minus fever bits) asc; a row is kept unless a kept row of a
       dominating pattern (same fever/Great overlap, fever-mask superset, Great-mask subset) has normal and fever
       Greats <= (its body fever is >= by the order). A dominator always comes first in that order and dominance is
       transitive, so this keeps exactly the non-dominated rows.
    No points gives the zero surface (the play that never activates) when `empty_is_zero`, else nothing. Returns
    (frontier, Fenwick stamp)."""
    m, n = sizes
    lo_pos, hi_pos, empty_is_zero = head
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
    stack = np.empty((m, 4), dtype=np.int64)
    for pos in range(m):
        idx = order[pos]
        for col in range(4):
            stack[pos, col] = points[idx, col]
    count, fen_stamp = _skyline_hulls(
        stack, m, min(max_fg + 2, fen_values.shape[0]), fen_values, fen_stamps, fen_stamp
    )
    frontier = np.empty((count, 7), dtype=np.uint64)
    for k in range(count):
        p = stack[k, 3]
        for col in range(4):
            frontier[k, col] = masks[p, col]
        frontier[k, 4] = np.uint64(stack[k, 0])
        frontier[k, 6] = np.uint64(stack[k, 2])
        frontier[k, 5] = np.uint64(stack[k, 1]) + frontier[k, 6]
    frontier = head_envelope_filter(frontier, lo_pos, hi_pos)
    rows = frontier.shape[0]
    rank_keys = np.empty(rows, dtype=np.int64)
    for k in range(rows):
        row = frontier[k]
        rank = (
            128
            + np.int64(_popcount64(row[2]))
            + np.int64(_popcount64(row[3]))
            - np.int64(_popcount64(row[0]))
            - np.int64(_popcount64(row[1]))
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
def _frontier_of_fever_time(sizes, actions, runs, group, ends, forced_timing: int, region, workspace):
    """One fever time's frontier: its reachable states (reachability_prepass), the body states' tail frontiers
    (_body_tails), then the head states from 99 down and last the first section from the song start, each from its
    activation sections (_state_points, _points_frontier). group = what the group's fever times share: (the packet
    families, the first section's activations).
    Returns (frontier rows, states evaluated, surfaces generated, surfaces retained, the largest state frontier, the
    pair epoch, the bit epoch)."""
    n, action_count = sizes
    later_fill, first_fill, later_forced, first_forced, later_activation_forced, first_activation_forced = actions
    families, first_activations = group
    pair_values, pair_stamps, pair_touched, bit_values, bit_stamps, pair_epoch, bit_epoch = workspace
    reachable, max_eg_width = reachability_prepass(n, first_activations, runs, ends, forced_timing, region)
    # The pair radix: a pair packs (normal Greats, fever Greats) as normal Greats x pair_mod + fever Greats, injective
    # while fever Greats < pair_mod. A play's body fever Greats are at most one boundary Great and max_eg_width early
    # Greats per section, over at most section_bound sections, and never more than n.
    section_bound = n // max(1, int(later_fill[0]) if action_count > 0 else 1) + 4
    pair_mod = min(n + 1, section_bound * (1 + max_eg_width) + 1)
    pair_size = (n + 1) * pair_mod
    # The host sizes a thread's pair workspace for the song's largest radix (producer_reducer.pair_mod_bound) and its
    # Fenwick for n + 2 (a head state's fever Greats reach n). A smaller workspace would be sliced short below and
    # written past its end: it fails here instead.
    if (
        pair_values.shape[0] < pair_size
        or pair_stamps.shape[0] < pair_size
        or pair_touched.shape[0] < pair_size
        or bit_values.shape[0] < n + 2
        or bit_stamps.shape[0] < n + 2
    ):
        raise ValueError("FG first-frontier stamp workspace is undersized for this geometry's pair radix")
    # A workspace cell counts as written when its stamp equals the current epoch, and epochs only grow, so the cells of
    # earlier geometries stay invisible, as the cells of earlier states do. The slices give every bound read from a
    # shape (the pair guard, the Fenwick's limit) this geometry's own size.
    (
        body_values,
        body_starts,
        body_counts,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        pair_epoch,
        bit_epoch,
    ) = _body_tails(
        n,
        families,
        reachable,
        region,
        ends,
        (
            pair_mod,
            pair_values[:pair_size],
            pair_stamps[:pair_size],
            pair_touched[:pair_size],
            pair_epoch,
            bit_values[: pair_mod + 1],
            bit_stamps[: pair_mod + 1],
            bit_epoch,
        ),
    )

    head_limit = min(n, 100)
    # The head states' frontiers live in one row store, addressed per state by (start, count); a state's rows are
    # final before an earlier state joins against them (states run descending), and an unreachable state has none.
    head_pool = np.empty((256, 7), dtype=np.uint64)
    head_pool_cursor = 0
    head_state_start = np.zeros(max(1, head_limit), dtype=np.int64)
    head_state_count = np.zeros(max(1, head_limit), dtype=np.int64)
    head = _HeadTables(body_values, body_starts, body_counts, head_pool, head_state_start, head_state_count, head_limit)
    # Scratch every state of this build reuses: activation sections, candidate points, the head-mask pattern table and
    # the window skyline arena. The states' Fenwick is the bit workspace, its epoch carried on from the body tails.
    entries = np.empty((256, 7), dtype=np.int64)
    points = np.empty((1024, 4), dtype=np.int64)
    slots = np.full(1024, -1, dtype=np.int64)
    masks = np.empty((256, 4), dtype=np.uint64)
    arena = np.empty((1024, 3), dtype=np.int64)

    first_frontier = np.zeros((0, 7), dtype=np.uint64)
    for state_i in range(head_limit - 1, -2, -1):
        first = state_i < 0
        if not first and not reachable[state_i]:
            continue
        state = 0 if first else state_i
        if first:
            entries, count = _section_entries(
                entries, 0, (n, action_count, 0, 0), first_fill, first_forced, first_activation_forced, ends, forced_timing
            )
        else:
            states_evaluated += 1
            entries, count = _section_entries(
                entries,
                0,
                (n, action_count, state, state + 1),
                later_fill,
                later_forced,
                later_activation_forced,
                ends,
                forced_timing,
            )
        if forced_timing != 0:
            entries, count = _region2_entries(
                entries, count, n, 0 if first else state + 1, region, ends.perfect_exit_e, ends.late_exit_e
            )
        points, m, slots, masks, arena = _state_points(entries, count, n, head, points, slots, masks, arena)
        generated_surfaces += m
        # A first section whose activations all lie in the body keeps no surface when none reaches it.
        frontier, bit_epoch = _points_frontier(
            points,
            masks,
            (m, n),
            (state, head_limit, not (first and action_count > 0 and int(first_fill[0]) >= 100)),
            bit_values,
            bit_stamps,
            bit_epoch,
        )
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)
        if first:
            first_frontier = frontier
            break
        head_pool = _rows_ensure(head_pool, head_pool_cursor, len(frontier))
        # The row store may have grown.
        head = _HeadTables(
            body_values, body_starts, body_counts, head_pool, head_state_start, head_state_count, head_limit
        )
        head_state_start[state] = head_pool_cursor
        head_state_count[state] = len(frontier)
        head_pool[head_pool_cursor : head_pool_cursor + len(frontier)] = frontier
        head_pool_cursor += len(frontier)

    return (
        first_frontier,
        states_evaluated,
        generated_surfaces,
        retained_total,
        max_state_frontier,
        pair_epoch,
        bit_epoch,
    )


@njit(cache=True, nogil=True)
def frontiers_of_fever_times(sizes, actions, runs, ends, fever, regions, workspace):
    """The frontier of each fever time of one (fill, non-Fever base) group, with no call back into Python between them.
    sizes: (notes, action rows, actions); actions: the action table's seven arrays; runs: the fill runs of its later
    offsets, then of those a late Great can activate at; ends: each note's Perfect and late-Great activation validity,
    then the six fever-end tables per fever-time row (ActivationEnds); fever: (raw fill, the fever times' rows,
    forced-Great timing); regions: the group's region table (region_core_table), then each hit token's end on the
    Perfect and the Great floor per fever-time row; workspace: a thread's five stamp arrays, then its pair and bit
    epochs.
    Returns the frontiers' rows, each one's first row (with the end), per fever time (states, generated surfaces,
    retained surfaces, largest state frontier), and the pair and bit epochs."""
    n, action_count, _region_action_count = sizes
    action_k, later_fill, first_fill, later_forced, first_forced, later_activation_forced, first_activation_forced = (
        actions
    )
    perfect_valid, late_valid, perfect_e, late_e, eg_perfect_e, eg_late_e, perfect_exit_e, late_exit_e = ends
    raw_fever_fill, fever_rows, forced_timing = fever
    head_starts, head_rows, key_starts, key_rows, perfect_ends, great_ends = regions
    w0, w1, w2, w3, w4, pair_epoch, bit_epoch = workspace
    families = packet_families(
        sizes, raw_fever_fill, (action_k, later_fill, later_forced, later_activation_forced), forced_timing
    )
    # The first section's activations: bit 1 where a Perfect activates, bit 2 where a late Great may.
    first_activations = np.zeros(n, dtype=np.int8)
    for action in range(action_count):
        fill = first_fill[action]
        if fill < 0:
            raise ValueError("FG first-fill offsets must be nonnegative")
        if fill < n:
            first_activations[fill] |= 1 if first_activation_forced[action] < 0 else 3
    count = fever_rows.shape[0]
    offsets = np.zeros(count + 1, dtype=np.int64)
    stats = np.empty((count, 4), dtype=np.int64)
    frontiers = []
    for index in range(count):
        row = fever_rows[index]
        frontier, states, generated, retained, largest, pair_epoch, bit_epoch = _frontier_of_fever_time(
            (n, action_count),
            (later_fill, first_fill, later_forced, first_forced, later_activation_forced, first_activation_forced),
            runs,
            (families, first_activations),
            ActivationEnds(
                perfect_valid,
                late_valid,
                perfect_e[row],
                late_e[row],
                eg_perfect_e[row],
                eg_late_e[row],
                perfect_exit_e[row],
                late_exit_e[row],
            ),
            forced_timing,
            RegionTables(head_starts, head_rows, key_starts, key_rows, perfect_ends[row], great_ends[row]),
            (w0, w1, w2, w3, w4, pair_epoch, bit_epoch),
        )
        frontiers.append(frontier)
        offsets[index + 1] = offsets[index] + frontier.shape[0]
        stats[index, 0], stats[index, 1], stats[index, 2], stats[index, 3] = states, generated, retained, largest
    rows = np.empty((offsets[count], 7), dtype=np.uint64)
    for index in range(count):
        rows[offsets[index] : offsets[index + 1]] = frontiers[index]
    return rows, offsets, stats, pair_epoch, bit_epoch
