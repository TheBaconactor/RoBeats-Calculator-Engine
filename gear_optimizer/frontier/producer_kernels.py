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
    run_lo = max(great_run_start, start)
    run_hi = min(great_run_start + k, n)
    idx = start + int(np.ceil(fever_fill_denom)) - 1
    if run_hi <= run_lo or idx < run_lo:
        return (idx, 0) if idx < n else (-1, 0)
    count = run_hi - run_lo
    perfects_before = run_lo - start
    idx = max(run_lo, run_lo - 1 + int(np.ceil(2.0 * (fever_fill_denom - float(perfects_before)))))
    if idx < run_hi:
        return (idx, 1) if idx < n else (-1, 0)
    idx = run_hi - 1 + int(np.ceil(fever_fill_denom - float(perfects_before) - 0.5 * float(count)))
    return (idx, 0) if idx < n else (-1, 0)


@njit(cache=True, nogil=True)
def region2_offset_for_count(start: int, count: int, fever_fill_denom: float, n: int) -> int:
    if count <= 0 or start >= n:
        return -1
    # Let x = run_start - section_start and m = count. The activation is the m-th Great in the run iff
    # x + 0.5*(m-1) < denom <= x + 0.5*m. That half-open interval of width 0.5 contains at most one integer x.
    if fever_fill_denom <= 0.0 or not np.isfinite(fever_fill_denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    # Guard before float-to-int conversion so legal finite values above int64 range return cleanly.
    if fever_fill_denom > float(n):
        return -1
    lo = int(np.ceil(fever_fill_denom - 0.5 * float(count)))
    hi = int(np.ceil(fever_fill_denom - 0.5 * float(count - 1))) - 1
    if lo < 1 or lo != hi or start + lo + count - 1 >= n:
        return -1
    return lo


@njit(cache=True, nogil=True)
def region2_k_scan_stop(action_count: int, fever_fill_denom: float) -> int:
    if action_count <= 0:
        return 0
    if fever_fill_denom <= 0.0 or not np.isfinite(fever_fill_denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    # Compare before multiplying by 2 so huge finite denominators cannot overflow to infinity.
    if fever_fill_denom >= 0.5 * float(action_count - 1):
        return action_count
    return min(action_count, max(1, int(np.ceil(2.0 * fever_fill_denom)) + 1))


@njit(cache=True, nogil=True)
def _lane_prefix_signature_reachable(
    a: int,
    activation_hit_timestamp: float,
    hit_times,
    lanes,
    section,
    run,
    activation_is_great: int,
    target,
) -> bool:
    """Exact exceptional-path test for one score-bearing prefix signature.

    When timing windows force a cross-lane swap, each lane still contributes one chart-order prefix. This packed DP
    decides the exact pair ``(event count, Great count)``; full lane-ID equality owns identity.
    """
    start, end = section
    g0, g1 = run
    target_count, target_great = target
    perfect_floor, perfect_candidates, great_floor, great_candidates, _late_great_floor = hit_times
    section_length = end - start
    if target_count < 0 or target_count > section_length - 1 or target_great < 0 or target_great > target_count:
        return False
    if lanes.shape[0] < end:
        raise ValueError("FG lane-prefix signature lanes are not aligned")

    word_count = (target_great + 64) // 64
    word_cells = (target_count + 1) * word_count
    if word_cells <= 0 or word_cells > _EXACT_LANE_SIGNATURE_MAX_WORD_CELLS:
        raise MemoryError("FG exact lane-prefix signature DP exceeds its fail-loud capacity")
    reachable = np.zeros((target_count + 1, word_count), dtype=np.uint64)
    merged = np.empty_like(reachable)
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
    for lane_idx in range(unique_count):
        lane_id = unique_lanes[lane_idx]
        note_count = 0
        minimum_count = 0
        maximum_count = -1
        activation_position = -1
        head_note_count = 0
        target_head_count = 0
        lane_clock = -np.inf
        prefix_greats[0] = 0
        for note_idx in range(start, end):
            if np.int64(lanes[note_idx]) != lane_id:
                continue
            is_great = (g0 <= note_idx < g1) or (note_idx == a and activation_is_great != 0)
            low = great_floor[note_idx] if is_great else perfect_floor[note_idx]
            high = great_candidates[note_idx] if is_great else perfect_candidates[note_idx]
            lane_clock = max(lane_clock, float(low))
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
            prefix_greats[note_count + 1] = prefix_greats[note_count] + (1 if is_great else 0)
            note_count += 1
        if maximum_count < 0:
            maximum_count = note_count
        if minimum_count > maximum_count:
            return False

        option_start, option_end = minimum_count, maximum_count
        if lane_id == activation_lane:
            if activation_position < 0:
                raise ValueError("FG activation note is absent from its exact lane")
            if not (minimum_count <= activation_position <= maximum_count):
                return False
            option_start = option_end = activation_position
        option_start = max(option_start, target_head_count)
        if target_head_count < head_note_count:
            option_end = min(option_end, target_head_count)
        if option_start > option_end:
            return False

        merged[:] = np.uint64(0)
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
                        merged[output_count, output_word] |= bits << np.uint64(bit_shift)
                    if bit_shift != 0 and output_word + 1 < word_count:
                        merged[output_count, output_word + 1] |= bits >> np.uint64(64 - bit_shift)
        reachable, merged = merged, reachable

    return bool(reachable[target_count, target_great // 64] & (np.uint64(1) << np.uint64(target_great % 64)))


@njit(cache=True, nogil=True)
def _fill_window_holds(denom: float, preactivation_count: int, great_before: int, activation_is_great: bool) -> bool:
    """Whether the bar fills on the activation: `preactivation_count` notes of the section precede it, `great_before`
    of them Greats (half a fill unit each), and the activation adds a unit as a Perfect and half as a Great."""
    fill_before = 0.5 * float(2 * preactivation_count - great_before)
    return fill_before < denom and denom <= fill_before + (0.5 if activation_is_great else 1.0)


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
        label_high = great_candidate_timestamps[j] if g0 <= j < g1 else perfect_candidate_timestamps[j]
        if label_high < h_a:
            return False
    return True


@njit(cache=True, nogil=True)
def activation_reachable_contiguous_run(
    a: int,
    activation_hit_timestamp: float,
    timestamps,
    hit_times,
    lanes,
    denom: float,
    bounds,
    activation_great_i: int,
) -> bool:
    start, end, great_start, great_count = bounds
    perfect_floor, perfect_candidates, great_floor, great_candidates, _late_great_floor = hit_times
    if start < 0 or end < start or not (start <= a < end):
        return False
    if denom <= 0.0 or not np.isfinite(denom):
        raise ValueError("fever_fill_denom must be finite and > 0")
    total = perfect_candidates.shape[0]
    if end > total:
        return False
    if (
        timestamps.shape[0] < total
        or perfect_floor.shape[0] < total
        or great_floor.shape[0] < total
        or great_candidates.shape[0] < total
        or lanes.shape[0] < total
    ):
        raise ValueError("FG activation reachability timing arrays are not aligned")
    if denom > float(end - start):
        return False

    g0 = max(start, great_start)
    g1 = max(g0, min(end, great_start + great_count))
    h_a = np.float32(activation_hit_timestamp)
    activation_is_great = activation_great_i != 0 or (g0 <= a < g1)
    activation_low = great_floor[a] if activation_is_great else perfect_floor[a]
    activation_high = great_candidates[a] if activation_is_great else perfect_candidates[a]
    if h_a < activation_low or h_a > activation_high:
        return False

    preactivation_count = a - start
    great_before = max(0, min(a, g1) - g0)
    if not _fill_window_holds(denom, preactivation_count, great_before, activation_is_great):
        return False

    # Both floor streams are monotone prefix maxima, so checking the last row of each constant-label segment is
    # necessary and sufficient for every chart-prefix note to have a legal hit <= h_a.
    chart_prefix_legal = True
    perfect_before_end = min(a, g0)
    if perfect_before_end > start and perfect_floor[perfect_before_end - 1] > h_a:
        chart_prefix_legal = False
    great_before_end = min(a, g1)
    if great_before_end > g0 and great_floor[great_before_end - 1] > h_a:
        chart_prefix_legal = False
    if a > g1 and perfect_floor[a - 1] > h_a:
        chart_prefix_legal = False

    if chart_prefix_legal and _later_notes_allow(a, h_a, timestamps, perfect_candidates, great_candidates, (g0, g1, end)):
        return True

    return _lane_prefix_signature_reachable(
        a, float(h_a), hit_times, lanes, (start, end), (g0, g1), 1 if activation_is_great else 0,
        (preactivation_count, great_before),
    )


@njit(cache=True, nogil=True)
def minimal_reachable_region_great_end(
    a: int, section_start: int, run_start: int, raw_fever_fill: float, timestamps, hit_times, lanes, n: int
):
    _pf, perfect_candidates, _gf, great_candidates, late_great_floor = hit_times
    hit_hi = great_candidates[a]
    max_great_end = a + 1
    while max_great_end < n and perfect_candidates[max_great_end] < hit_hi:
        max_great_end += 1
    for great_end in range(a + 1, max_great_end + 1):
        hit, valid, token = late_great_activation_hit_for_run(
            a, timestamps, perfect_candidates, great_candidates, late_great_floor, run_start, great_end - run_start, n
        )
        if valid == 0:
            continue
        if activation_reachable_contiguous_run(
            a, hit, timestamps, hit_times, lanes, raw_fever_fill, (section_start, n, run_start, great_end - run_start), 1
        ):
            return great_end, token
    return -1, -1


@njit(cache=True, nogil=True)
def has_shifted_head_region(section_start: int, raw_fever_fill: float) -> int:
    return 1 if section_start < 99 and int(np.ceil(raw_fever_fill)) > 1 else 0


@njit(cache=True, nogil=True)
def region_core_candidate_capacity(n: int, region_action_count: int, action_k, raw_fever_fill: float) -> int:
    """Exact count of offsets that can reach the region-core producer (allocation bound only)."""
    region_k_stop = region2_k_scan_stop(region_action_count, raw_fever_fill)
    if raw_fever_fill <= 0.0 or not np.isfinite(raw_fever_fill):
        raise ValueError("raw_fever_fill must be finite and > 0")
    if raw_fever_fill > float(n):
        return 0
    shifted_sections = min(99, n + 1) if int(np.ceil(raw_fever_fill)) > 1 else 0
    candidate_count = shifted_sections * region_action_count
    for action_idx in range(region_k_stop):
        k = int(action_k[action_idx])
        region_offset = region2_offset_for_count(0, k, raw_fever_fill, n)
        if region_offset < 1:
            continue
        section_count = max(0, n - region_offset - k + 1)
        candidate_count += section_count
        if region_offset == 1:
            candidate_count -= min(shifted_sections, section_count)
    if candidate_count > (n + 1) * max(1, region_action_count) * 2:
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
def song_region_cores(timestamps, hit_times):
    """Per-activation region-2 core values that depend only on the song, shared across every fill group.

    For each activation note: its first Great end with a valid late-Great hit (-1: none), its late-Great and Perfect
    hit tokens, its hit timestamp (float32), whether the hit and later notes are legal, and whether the Greats before
    it are legal."""
    n = timestamps.shape[0]
    great_floor = hit_times.great_floor_timestamps
    perfect_candidates = hit_times.perfect_candidate_timestamps
    great_candidates = hit_times.great_candidate_timestamps
    late_great_floor = hit_times.late_great_floor_timestamps
    core_great_end = np.full(n, -1, dtype=np.int32)
    core_late_token = np.full(n, -1, dtype=np.int32)
    core_perfect_token = np.full(n, -1, dtype=np.int32)
    core_hit = np.zeros(n, dtype=np.float32)
    core_flags = np.zeros(n, dtype=np.uint8)  # bit 1: legal, bit 2: greats_before_legal
    for activation in range(n):
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
        core_great_end[activation] = great_end
        core_late_token[activation] = late_token
        core_perfect_token[activation] = perfect_token
        core_hit[activation] = h_a
        core_flags[activation] = np.uint8((1 if legal else 0) | (2 if greats_before_legal else 0))
    return core_great_end, core_late_token, core_perfect_token, core_hit, core_flags


@njit(cache=True, nogil=True)
def _region_core_table(action_k, raw_fever_fill: float, timestamps, hit_times, lanes, song_cores):
    """Compiled region-core builder reusing precomputed `song_region_cores` across all fill groups of one song.

    When all region-2 runs advance `run_reach` by 1 and every activation's fast-path prefix test holds across its
    valid run range (the 95%+ common case outside the first 100 head sections), the entire run loop collapses to one
    O(1) key interval instead of O(K) per activation."""
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
    perfect_floor = hit_times.perfect_floor_timestamps
    perfect_candidates, great_candidates = hit_times.perfect_candidate_timestamps, hit_times.great_candidate_timestamps
    core_great_end, core_late_token, core_perfect_token, core_hit, core_flags = song_cores
    first_later_section = int(np.ceil(raw_fever_fill)) + 1

    run_action = np.empty(actions, dtype=np.int64)
    run_k = np.empty(actions, dtype=np.int64)
    run_reach = np.empty(actions, dtype=np.int64)
    run_fills = np.empty(actions, dtype=np.bool_)
    runs = 0
    unit_runs = True
    for action in range(region2_k_scan_stop(actions, raw_fever_fill)):
        k = int(action_k[action])
        offset = region2_offset_for_count(0, k, raw_fever_fill, n + k + 2)
        if offset < 1:
            continue
        reach = offset + k - 1
        fills = _fill_window_holds(raw_fever_fill, reach, k - 1, True)
        if not fills:
            unit_runs = False
        if runs > 0 and (reach != run_reach[runs - 1] + 1 or k < run_k[runs - 1]):
            unit_runs = False
        run_action[runs] = action
        run_k[runs] = k
        run_reach[runs] = reach
        run_fills[runs] = fills
        runs += 1
    if runs == 0:
        unit_runs = False
    max_section = int(np.floor(float(n) - raw_fever_fill))
    while max_section >= 0 and raw_fever_fill > float(n - max_section):
        max_section -= 1
    while max_section + 1 < n and not (raw_fever_fill > float(n - (max_section + 1))):
        max_section += 1

    keys = np.empty((n + 64, 6), dtype=np.int32)
    key_count = 0
    head_runs = np.full(((head_limit + 1) * max(1, runs), 3), -1, dtype=np.int32)
    first_reach = run_reach[0] if runs > 0 else 0
    last_k = run_k[runs - 1] if runs > 0 else 0
    for activation in range(n):
        great_end = int(core_great_end[activation])
        if great_end < 0:
            continue
        late_token = int(core_late_token[activation])
        perfect_token = int(core_perfect_token[activation])
        h_a = core_hit[activation]
        flags = core_flags[activation]
        legal = (flags & np.uint8(1)) != 0
        greats_before_legal = (flags & np.uint8(2)) != 0

        if unit_runs and legal and (greats_before_legal or last_k < 2):
            r_hi = activation - first_reach
            if r_hi >= runs:
                r_hi = runs - 1
            r_lo = activation - first_reach - max_section
            if r_lo < 0:
                r_lo = 0
            if r_lo <= r_hi:
                min_sec = activation - run_reach[r_hi]
                if min_sec > head_limit and not (perfect_floor[activation - run_k[r_lo]] > h_a):
                    if key_count == keys.shape[0]:
                        keys = _rows_ensure(keys, key_count, 1)
                    keys[key_count, 0] = activation
                    keys[key_count, 1] = min_sec
                    keys[key_count, 2] = activation - run_reach[r_lo]
                    keys[key_count, 3] = great_end
                    keys[key_count, 4] = late_token
                    keys[key_count, 5] = perfect_token
                    key_count += 1
                    continue

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


def region_core_table(action_k, raw_fever_fill: float, timestamps, hit_times, lanes, song_cores=None):
    """The region runs of one (fill, non-Fever base) group: head rows for section starts <= 100 and key rows per
    activation. Pass precomputed `song_cores` from `song_region_cores` to share per-activation work across groups."""
    if song_cores is None:
        song_cores = song_region_cores(timestamps, hit_times)
    return _region_core_table(action_k, raw_fever_fill, timestamps, hit_times, lanes, song_cores)


@njit(cache=True, nogil=True)
def reachability_prepass(n: int, first_activations, runs, ends, forced_timing: int, region):
    """The states a play can reach at one fever time, as a mask over the fever ends 0 .. n (n is always reached), and
    the largest early-Great width of an activation that reaches one.

    A fever ends past its activation, so when the notes are taken in ascending order every state before a note is
    final by the time the note is tried as an activation. Forward reach intervals [lo, hi] with lo > activation are
    accumulated in O(1) via a difference array, giving strict O(n + D) work regardless of early-exit width.
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
    diff = np.zeros(n + 2, dtype=np.int32)
    cover = 0
    width = 0
    for activation in range(n):
        cover += diff[activation]
        if cover > 0:
            reachable[activation] = True
        reached[activation + 1] = reached[activation] + reachable[activation]
        perfect_reached = (first_activations[activation] & 1) != 0
        if not perfect_reached:
            for run in range(perfect_run_starts.shape[0]):
                newest = activation - perfect_run_starts[run]
                if newest >= 0 and reached[newest + 1] > reached[max(0, activation - perfect_run_ends[run])]:
                    perfect_reached = True
                    break
        if perfect_reached and perfect_valid[activation] != 0:
            edge_e, eg_e = perfect_e[activation], eg_perfect_e[activation]
            lo = min(perfect_exit_e[activation], edge_e)
            hi = max(edge_e, eg_e)
            if lo > activation:
                diff[lo] += 1
                diff[hi + 1] -= 1
            else:
                for end in range(lo, hi + 1):
                    reachable[end] = True
            if eg_e - edge_e > width:
                width = eg_e - edge_e
        if forced_timing == 0:
            continue
        late_reached = (first_activations[activation] & 2) != 0
        if not late_reached:
            for run in range(late_run_starts.shape[0]):
                newest = activation - late_run_starts[run]
                if newest >= 0 and reached[newest + 1] > reached[max(0, activation - late_run_ends[run])]:
                    late_reached = True
                    break
        if late_reached and late_valid[activation] != 0:
            edge_e, eg_e = late_e[activation], eg_late_e[activation]
            if perfect_valid[activation] == 0 or late_edge_extends(
                perfect_e[activation], edge_e, eg_e, eg_perfect_e[activation]
            ):
                lo = min(late_exit_e[activation], edge_e)
                hi = max(edge_e, eg_e)
                if lo > activation:
                    diff[lo] += 1
                    diff[hi + 1] -= 1
                else:
                    for end in range(lo, hi + 1):
                        reachable[end] = True
                if eg_e - edge_e > width:
                    width = eg_e - edge_e
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
            lo = min(perfect_exit_e[activation] if late_hit < 0 else late_exit_e[activation], edge_e)
            if lo > activation:
                diff[lo] += 1
                diff[eg_e + 1] -= 1
            else:
                for end in range(lo, eg_e + 1):
                    reachable[end] = True
            if eg_e - edge_e > width:
                width = eg_e - edge_e
    return reachable, width


@njit(cache=True, nogil=True)
def touch_body_rows(queue, heads, tails, state: int, key, pair_stamp, best_fever_by_pair, touched_pair):
    """Register the live rows [heads, tails) of every family's queue as the body candidates of `state`: per (normal
    Greats, fever Greats) pair the largest body fever, in the stamped pair table. A row holds (body fever, normal
    Greats + 2 x its reader's state, fever Greats, activation); a row whose normal Greats come out negative for this
    state belongs to none of its plays. key = (pair radix, stamp). Returns (pairs touched, rows read)."""
    pair_mod, stamp = key
    touched = 0
    rows = 0
    pair_size = best_fever_by_pair.shape[0]
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
            if pair >= pair_size:
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


# Precomputed bit-exact head combo weights (pos 0..99) and contiguous prefix sums [0, k) for _head_pattern_basis.
def _precompute_head_basis_tables():
    k_lo = (HEAD_DOM_C[0] - 1.0) / 100.0
    k_hi = (HEAD_DOM_C[1] - 1.0) / 100.0
    slo = np.empty(100, dtype=np.float64)
    shi = np.empty(100, dtype=np.float64)
    pref_lo = np.zeros(101, dtype=np.float64)
    pref_hi = np.zeros(101, dtype=np.float64)
    acc_lo = 0.0
    acc_hi = 0.0
    for pos in range(100):
        v_lo = 1.0 + k_lo * float(pos + 1)
        v_hi = 1.0 + k_hi * float(pos + 1)
        slo[pos] = v_lo
        shi[pos] = v_hi
        acc_lo += v_lo
        acc_hi += v_hi
        pref_lo[pos + 1] = acc_lo
        pref_hi[pos + 1] = acc_hi
    debruijn = np.empty(64, dtype=np.int32)
    magic = 0x03F79D71B4CB0A89
    for bit in range(64):
        idx = (((1 << bit) * magic) & 0xFFFFFFFFFFFFFFFF) >> 58
        debruijn[idx] = bit
    return slo, shi, pref_lo, pref_hi, debruijn


_HEAD_SLO, _HEAD_SHI, _HEAD_PREF_LO, _HEAD_PREF_HI, _DEBRUIJN_CTZ64 = _precompute_head_basis_tables()


def _precompute_cone_constants():
    """Exact 16-corner score multipliers for the _HEAD_DOM box, plus the 4 conic-hull body corners and 16-corner sums."""
    body_dn = np.empty(16, dtype=np.float64)
    pen_n = np.empty(16, dtype=np.float64)
    pen_f = np.empty(16, dtype=np.float64)
    hb = np.empty(16, dtype=np.float64)
    hc = np.empty(16, dtype=np.float64)
    hd = np.empty(16, dtype=np.float64)
    hi_c = np.empty(16, dtype=np.int8)
    col = 0
    for e in _HEAD_DOM_E:
        g = e * 2.0 / 3.0 + 150.0
        for ic in range(2):
            c = HEAD_DOM_C[ic]
            for f in HEAD_DOM_F:
                for b in HEAD_DOM_B:
                    v = e + b
                    gv = g - v
                    body_dn[col] = v * c * (f - 1.0)
                    pen_n[col] = c * gv
                    pen_f[col] = c * f * gv
                    hb[col] = v * (f - 1.0)
                    hc[col] = gv
                    hd[col] = gv * (f - 1.0)
                    hi_c[col] = ic
                    col += 1
    return body_dn, pen_n, pen_f, hb, hc, hd, hi_c, float(body_dn.sum()), float(pen_n.sum()), float(pen_f.sum())


_C16_BDN, _C16_PN, _C16_PF, _C16_HB, _C16_HC, _C16_HD, _C16_HIC, _SUM16_BDN, _SUM16_PN, _SUM16_PF = (
    _precompute_cone_constants()
)
# Compile-time scalar constants for the 4 conic-hull body corners (E=0, c=1.95, f in {2.95, 5.48}, b in {200, 485}):
# every E=7600 corner is a positive linear combination of E=0 corners with weight sum 34.78 > 1 and c=2.72 scales by
# 2.72/1.95 > 1, so dominance at corners 0..3 implies dominance at all 16 corners.
_C0_BDN, _C1_BDN, _C2_BDN, _C3_BDN = map(float, _C16_BDN[:4])
_C0_PN, _C1_PN, _C2_PN, _C3_PN = map(float, _C16_PN[:4])
_C0_PF, _C1_PF, _C2_PF, _C3_PF = map(float, _C16_PF[:4])


@njit(cache=True, nogil=True, inline="always")
def _ctz64(lsb: np.uint64) -> int:
    """Bit index (0..63) of a single-bit uint64 power of two."""
    return int(_DEBRUIJN_CTZ64[int((lsb * np.uint64(0x03F79D71B4CB0A89)) >> np.uint64(58))])


@njit(cache=True, nogil=True, inline="always")
def _insertion_sort_i32(arr, count: int) -> None:
    """Sort arr[:count] ascending in place (used for small batches <= 24 without NumPy sort dispatch)."""
    for i in range(1, count):
        val = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > val:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = val


@njit(cache=True, nogil=True, inline="always")
def _sort_distinct_i32(arr, count: int, sort_bits) -> None:
    """Sort `count` distinct nonnegative int32 values in `arr[:count]` ascending in place.

    Uses a 64-bit word bitset (`O(count + span / 64)`, branch-free) when `count >= 12` and the span fits the
    reusable zeroed `sort_bits` buffer within 4 words per element; otherwise insertion sort (`<= 24`) or `.sort()`."""
    if count <= 1:
        return
    if count < 12:
        _insertion_sort_i32(arr, count)
        return
    if sort_bits.shape[0] > 0:
        lo = int(arr[0])
        hi = lo
        for i in range(1, count):
            v = int(arr[i])
            if v < lo:
                lo = v
            elif v > hi:
                hi = v
        nw = ((hi - lo) >> 6) + 1
        if nw <= sort_bits.shape[0] and nw <= 4 * count:
            for i in range(count):
                d = int(arr[i]) - lo
                sort_bits[d >> 6] |= np.uint64(1) << np.uint64(d & 63)
            k = 0
            for wi in range(nw):
                w = sort_bits[wi]
                if w != np.uint64(0):
                    sort_bits[wi] = np.uint64(0)
                    base = lo + (wi << 6)
                    while w != np.uint64(0):
                        lsb = w & (~w + np.uint64(1))
                        arr[k] = np.int32(base + _ctz64(lsb))
                        k += 1
                        w ^= lsb
            return
    if count <= 24:
        _insertion_sort_i32(arr, count)
    else:
        arr[:count].sort()


@njit(cache=True, nogil=True, inline="always")
def _insertion_sort_order(order, keys, count: int) -> None:
    """Sort order[:count] in place by ascending keys[order[i]]."""
    for i in range(1, count):
        oi = order[i]
        ki = keys[oi]
        j = i - 1
        while j >= 0 and keys[order[j]] > ki:
            order[j + 1] = order[j]
            j -= 1
        order[j + 1] = oi


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
    body_term = _HEAD_DOM_BODY_FLOOR_W * abs(int(np.int64(left[4]) - np.int64(right[4]))) + (
        _HEAD_DOM_BODY_FLOOR_W + _HEAD_DOM_GREAT_FLOOR_W
    ) * (normal_greats + fever_greats)
    if left[0] == right[0] and left[1] == right[1] and left[2] == right[2] and left[3] == right[3]:
        return float(body_term)
    g0 = left[2] ^ right[2]
    g1 = left[3] ^ right[3]
    return float(
        _popcount64((left[0] ^ right[0]) | g0)
        + _popcount64((left[1] ^ right[1]) | g1)
        + _HEAD_DOM_GREAT_FLOOR_W * (_popcount64(g0) + _popcount64(g1))
        + body_term
    )


@njit(cache=True, nogil=True)
def _cone_kept(rows, scores, sums):
    """The rows no other row dominates (score gap >= the pair's margin at all 16 corners), by descending corner-score
    sum. Tracks running maxima at opposite box extrema (corners 1, 14, 2, 0, 15) for O(1) fast-accept and checks those
    opposite trade-off corners first before scanning the remaining corners."""
    m = rows.shape[0]
    order = np.argsort(sums)
    kept_rows = np.empty(m, dtype=np.int64)
    kept_scores = np.empty((m, 16), dtype=np.float64)
    kept_count = 0
    max_s0 = -1.0e300
    max_s1 = -1.0e300
    max_s2 = -1.0e300
    max_s14 = -1.0e300
    max_s15 = -1.0e300
    for pos in range(m):
        i = order[pos]
        s0 = scores[i, 0]
        s1 = scores[i, 1]
        s2 = scores[i, 2]
        s14 = scores[i, 14]
        s15 = scores[i, 15]
        dominated = False
        if s1 <= max_s1 and s14 <= max_s14 and s2 <= max_s2 and s0 <= max_s0 and s15 <= max_s15:
            for ki in range(kept_count):
                d1 = kept_scores[ki, 1] - s1
                if d1 < 0.0:
                    continue
                d14 = kept_scores[ki, 14] - s14
                if d14 < 0.0:
                    continue
                d2 = kept_scores[ki, 2] - s2
                if d2 < 0.0:
                    continue
                d0 = kept_scores[ki, 0] - s0
                if d0 < 0.0:
                    continue
                d15 = kept_scores[ki, 15] - s15
                if d15 < 0.0:
                    continue
                min_diff = d0 if d0 < d1 else d1
                if d2 < min_diff:
                    min_diff = d2
                if d14 < min_diff:
                    min_diff = d14
                if d15 < min_diff:
                    min_diff = d15
                ok = True
                for cc in range(3, 14):
                    d = kept_scores[ki, cc] - scores[i, cc]
                    if d < 0.0:
                        ok = False
                        break
                    if d < min_diff:
                        min_diff = d
                if ok and min_diff >= _surface_margin(rows[kept_rows[ki]], rows[i]):
                    dominated = True
                    break
        if not dominated:
            kept_rows[kept_count] = i
            for cc in range(16):
                kept_scores[kept_count, cc] = scores[i, cc]
            if s0 > max_s0:
                max_s0 = s0
            if s1 > max_s1:
                max_s1 = s1
            if s2 > max_s2:
                max_s2 = s2
            if s14 > max_s14:
                max_s14 = s14
            if s15 > max_s15:
                max_s15 = s15
            kept_count += 1
    return kept_rows[:kept_count]


@njit(cache=True, nogil=True)
def head_envelope_filter(frontier, lo_pos, hi_pos):
    """LOSSLESS prune of the head frontier to its cone-Pareto set -- the surfaces that are best for SOME realizable stat
    cell. The head+body score is multilinear on the _HEAD_DOM box, so its unfloored value hits its extrema at the 16 corners.
    Surface K dominates C over the WHOLE box iff unfloored score(K)-score(C) >= the per-pair floor margin at all 16 corners.
    This is the head analog of `_body_cone_filter_buf`: best-preserving for EVERY realizable cell, by a 16-corner proof, not
    probe sampling. Composition-safe (the score is additive over disjoint edge/tail head ranges), so an envelope-minimal
    tail stays representative as the DP prepends edges."""
    m = frontier.shape[0]
    if m < 2:
        return frontier
    scores = np.empty((m, 16), dtype=np.float64)
    sums = np.empty(m, dtype=np.float64)
    h_corners = np.empty(16, dtype=np.float64)
    for i in range(m):
        fl, fh, gl, gh = frontier[i, 0], frontier[i, 1], frontier[i, 2], frontier[i, 3]
        if (
            i == 0
            or fl != frontier[i - 1, 0]
            or fh != frontier[i - 1, 1]
            or gl != frontier[i - 1, 2]
            or gh != frontier[i - 1, 3]
        ):
            b_lo, c_lo, d_lo, b_hi, c_hi, d_hi = _head_pattern_basis(fl, fh, gl, gh, lo_pos, hi_pos)
            for col in range(16):
                if _C16_HIC[col] == 0:
                    h_corners[col] = _C16_HC[col] * c_lo + _C16_HB[col] * b_lo + _C16_HD[col] * d_lo
                else:
                    h_corners[col] = _C16_HC[col] * c_hi + _C16_HB[col] * b_hi + _C16_HD[col] * d_hi
        bf = float(np.int64(frontier[i, 4]))
        fg = float(np.int64(frontier[i, 6]))
        ng = float(np.int64(frontier[i, 5]) - np.int64(frontier[i, 6]))
        total = 0.0
        for col in range(16):
            val = h_corners[col] + bf * _C16_BDN[col] + ng * _C16_PN[col] + fg * _C16_PF[col]
            scores[i, col] = val
            total += val
        sums[i] = -total
    kept_rows = _cone_kept(frontier, scores, sums)
    out = np.empty((kept_rows.shape[0], 7), dtype=np.uint64)
    for ki in range(kept_rows.shape[0]):
        out[ki] = frontier[kept_rows[ki]]
    return out


@njit(cache=True, nogil=True)
def _body_cone_filter_buf(values, count: int, scores, sums, order, kept_meta, kept_mask) -> int:
    """Zero-allocation body cone filter using the 4 conic-hull corners (E=0, c=1.95, f in {2.95, 5.48}, b in
    {200, 485}) with register-held scalar constants and contiguous L1 kept rows. Keeps original row order."""
    if count < 2:
        return count
    for i in range(count):
        bf = float(values[i, 0])
        ng = float(values[i, 1])
        fg = float(values[i, 2])
        scores[i, 0] = bf * _C0_BDN + ng * _C0_PN + fg * _C0_PF
        scores[i, 1] = bf * _C1_BDN + ng * _C1_PN + fg * _C1_PF
        scores[i, 2] = bf * _C2_BDN + ng * _C2_PN + fg * _C2_PF
        scores[i, 3] = bf * _C3_BDN + ng * _C3_PN + fg * _C3_PF
        sums[i] = -(bf * _SUM16_BDN + ng * _SUM16_PN + fg * _SUM16_PF)
        order[i] = i
        kept_mask[i] = np.uint8(0)
    if count <= 32:
        _insertion_sort_order(order, sums, count)
    else:
        sorted_idx = np.argsort(sums[:count])
        for i in range(count):
            order[i] = sorted_idx[i]
    kept_count = 0
    for pos in range(count):
        i = order[pos]
        bf_i = values[i, 0]
        ng_i = values[i, 1]
        fg_i = values[i, 2]
        a0 = scores[i, 0]
        a1 = scores[i, 1]
        a2 = scores[i, 2]
        a3 = scores[i, 3]
        dominated = False
        for ki in range(kept_count):
            d1 = scores[ki, 5] - a1
            if d1 < 0.0:
                continue
            d0 = scores[ki, 4] - a0
            if d0 < 0.0:
                continue
            d3 = scores[ki, 7] - a3
            if d3 < 0.0:
                continue
            d2 = scores[ki, 6] - a2
            if d2 < 0.0:
                continue
            min_d = d0 if d0 < d1 else d1
            if d2 < min_d:
                min_d = d2
            if d3 < min_d:
                min_d = d3
            dbf = abs(kept_meta[ki, 0] - bf_i)
            dng = abs(kept_meta[ki, 1] - ng_i)
            dfg = abs(kept_meta[ki, 2] - fg_i)
            if min_d >= float(2 * dbf + 32 * (dng + dfg)):
                dominated = True
                break
        if not dominated:
            scores[kept_count, 4] = a0
            scores[kept_count, 5] = a1
            scores[kept_count, 6] = a2
            scores[kept_count, 7] = a3
            kept_meta[kept_count, 0] = bf_i
            kept_meta[kept_count, 1] = ng_i
            kept_meta[kept_count, 2] = fg_i
            kept_mask[i] = np.uint8(1)
            kept_count += 1
    out = 0
    for i in range(count):
        if kept_mask[i] != 0:
            if out != i:
                values[out, 0] = values[i, 0]
                values[out, 1] = values[i, 1]
                values[out, 2] = values[i, 2]
                values[out, 3] = values[i, 3]
            out += 1
    return out


@njit(cache=True, nogil=True, inline="always")
def _head_word_basis(fw: np.uint64, gw: np.uint64, offset: int, acc):
    b_lo, c_lo, d_lo, b_hi, c_hi, d_hi = acc
    w = fw | gw
    while w != np.uint64(0):
        lsb = w & (~w + np.uint64(1))
        pos = offset + _ctz64(lsb)
        slo = _HEAD_SLO[pos]
        shi = _HEAD_SHI[pos]
        fb = (fw & lsb) != np.uint64(0)
        gb = (gw & lsb) != np.uint64(0)
        if fb:
            b_lo += slo
            b_hi += shi
        if gb:
            c_lo += slo
            c_hi += shi
        if fb and gb:
            d_lo += slo
            d_hi += shi
        w ^= lsb
    return b_lo, c_lo, d_lo, b_hi, c_hi, d_hi


@njit(cache=True, nogil=True)
def _head_pattern_basis(fl, fh, gl, gh, lo_pos: int, hi_pos: int):
    """Head-only portion of a surface's basis at the box's low and high combo, bit-identical to the ascending
    bit-by-bit sum over [lo_pos, hi_pos). Prefix-only Great masks hit an O(1) precomputed prefix table; general masks
    walk only set bits in ascending order."""
    mlo, mhi = _range_mask(lo_pos, hi_pos, 100)
    f0, f1 = fl & mlo, fh & mhi
    g0, g1 = gl & mlo, gh & mhi
    if f0 == np.uint64(0) and f1 == np.uint64(0):
        if g0 == np.uint64(0) and g1 == np.uint64(0):
            return 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
        if lo_pos == 0:
            if g1 == np.uint64(0) and (g0 & (g0 + np.uint64(1))) == np.uint64(0):
                k = 64 if g0 == np.uint64(0xFFFFFFFFFFFFFFFF) else _ctz64(g0 + np.uint64(1))
                return 0.0, _HEAD_PREF_LO[k], 0.0, 0.0, _HEAD_PREF_HI[k], 0.0
            if g0 == np.uint64(0xFFFFFFFFFFFFFFFF) and (g1 & (g1 + np.uint64(1))) == np.uint64(0):
                k = 64 + _ctz64(g1 + np.uint64(1))
                return 0.0, _HEAD_PREF_LO[k], 0.0, 0.0, _HEAD_PREF_HI[k], 0.0
    acc = _head_word_basis(f0, g0, 0, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
    return _head_word_basis(f1, g1, 64, acc)


@njit(cache=True, nogil=True)
def _reduce_touched_pairs_inplace(pair_mod: int, touched_pair, touched_count: int, best_fever_by_pair, bit_ws, stack) -> int:
    """In-place fused skyline + per-normal-Great upper-hull reduction of `touched_pair[:touched_count]` into
    pre-sized `stack` (at least `touched_count` rows). Returns only the scalar kept count (no array return/refcount).

    Stride-1 (`pair_mod == 1`) skips all division and Fenwick operations. General strides sort distinct touched pairs
    via `_sort_distinct_i32` (64-bit word bitset when dense) and run a single fused decode + Fenwick + upper-hull pass."""
    bit_values, bit_stamps, bit_stamp, sort_bits = bit_ws
    if touched_count <= 0:
        return 0
    if touched_count <= 2:
        p0 = int(touched_pair[0])
        p1 = 0
        if touched_count == 2:
            p1 = int(touched_pair[1])
            if p0 > p1:
                p0, p1 = p1, p0
        ng0 = p0 if pair_mod == 1 else p0 // pair_mod
        fg0 = 0 if pair_mod == 1 else p0 - ng0 * pair_mod
        bf0 = best_fever_by_pair[p0]
        stack[0, 0], stack[0, 1], stack[0, 2], stack[0, 3] = bf0, ng0, fg0, 0
        if touched_count == 1:
            return 1
        ng1 = p1 if pair_mod == 1 else p1 // pair_mod
        fg1 = 0 if pair_mod == 1 else p1 - ng1 * pair_mod
        bf1 = best_fever_by_pair[p1]
        if fg0 > fg1 or bf1 > bf0:
            stack[1, 0], stack[1, 1], stack[1, 2], stack[1, 3] = bf1, ng1, fg1, 0
            return 2
        return 1
    _sort_distinct_i32(touched_pair, touched_count, sort_bits)
    if pair_mod == 1:
        kept = 0
        best_bf = -1
        for index in range(touched_count):
            ng = int(touched_pair[index])
            bf = best_fever_by_pair[ng]
            if bf > best_bf:
                best_bf = bf
                stack[kept, 0] = bf
                stack[kept, 1] = ng
                stack[kept, 2] = 0
                stack[kept, 3] = 0
                kept += 1
        return kept
    limit = pair_mod + 1
    if limit > bit_values.shape[0]:
        limit = bit_values.shape[0]
    has_fg = False
    best_zero_bf = -1
    kept = 0
    level = -1
    level_base = 0
    ng = 0
    ng_base = 0
    next_base = pair_mod
    for index in range(touched_count):
        pair = int(touched_pair[index])
        if pair >= next_base:
            if pair < next_base + pair_mod:
                ng += 1
                ng_base = next_base
                next_base += pair_mod
            else:
                ng = pair // pair_mod
                ng_base = ng * pair_mod
                next_base = ng_base + pair_mod
        fg = pair - ng_base
        bf = best_fever_by_pair[pair]
        if not has_fg:
            if fg == 0:
                if bf > best_zero_bf:
                    best_zero_bf = bf
                    stack[kept, 0] = bf
                    stack[kept, 1] = ng
                    stack[kept, 2] = 0
                    stack[kept, 3] = 0
                    kept += 1
                continue
            has_fg = True
            if kept > 0:
                cursor = 1
                while cursor < limit:
                    bit_stamps[cursor] = bit_stamp
                    bit_values[cursor] = best_zero_bf
                    cursor += cursor & -cursor
                level = stack[kept - 1, 1]
                level_base = kept - 1
        best = -1
        cursor = fg + 1
        while cursor > 0:
            if bit_stamps[cursor] == bit_stamp and bit_values[cursor] > best:
                best = bit_values[cursor]
            cursor -= cursor & -cursor
        if bf > best:
            if ng != level:
                level = ng
                level_base = kept
            while kept - level_base >= 2:
                cross = (stack[kept - 1, 0] - stack[kept - 2, 0]) * (stack[kept - 2, 2] - fg) - (
                    stack[kept - 2, 2] - stack[kept - 1, 2]
                ) * (bf - stack[kept - 2, 0])
                if cross >= 0:
                    kept -= 1
                else:
                    break
            stack[kept, 0] = bf
            stack[kept, 1] = ng
            stack[kept, 2] = fg
            stack[kept, 3] = 0
            kept += 1
            cursor = fg + 1
            while cursor < limit:
                if bit_stamps[cursor] != bit_stamp:
                    bit_stamps[cursor] = bit_stamp
                    bit_values[cursor] = bf
                elif bf > bit_values[cursor]:
                    bit_values[cursor] = bf
                cursor += cursor & -cursor
    return kept


@njit(cache=True, nogil=True)
def reduce_touched_body_pairs(
    pair_mod: int, touched_pair, touched_count: int, best_fever_by_pair, bit_values, bit_stamps, bit_stamp: int, stack
):
    """A body state's frontier from its touched pairs: rows (body fever, normal Greats, fever Greats, 0) in the
    reusable `stack`, which grows as needed. Returns (stack, rows)."""
    if touched_count <= 0:
        return stack, 0
    if touched_count > stack.shape[0]:
        stack = _rows_ensure(stack, 0, touched_count)
    count = _reduce_touched_pairs_inplace(
        pair_mod,
        touched_pair,
        touched_count,
        best_fever_by_pair,
        (bit_values, bit_stamps, bit_stamp, np.empty(0, dtype=np.uint64)),
        stack,
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
def _points_skyline_sorted(buf, start: int, end: int) -> int:
    """The skyline of rows [start, end) by one sorted pass: a row's dominators (body fever >= its own, normal and
    fever Greats <= its own) all precede it under (normal Greats, -body fever, fever Greats) order, so a point is
    dominated iff the best body fever an earlier point reaches at its fever-Great count is at least its own - one
    Fenwick prefix-maximum per row decides, and kept rows update the tree. O(m log m).

    Not `_reduce_touched_pairs_inplace`: that one prunes further to per-normal-Great upper hulls (which drops
    Pareto-optimal but hull-interior rows) and emits hull order; callers here need the exact Pareto set in the rows'
    original order, so this keeps the first occurrence of an exact duplicate (stable mergesort) just as
    `_points_append` does."""
    m = end - start
    n_lo, n_hi = buf[start, 1], buf[start, 1]
    f_lo, f_hi = buf[start, 0], buf[start, 0]
    q_lo, q_hi = buf[start, 2], buf[start, 2]
    for idx in range(start + 1, end):
        n_lo = min(n_lo, buf[idx, 1])
        n_hi = max(n_hi, buf[idx, 1])
        f_lo = min(f_lo, buf[idx, 0])
        f_hi = max(f_hi, buf[idx, 0])
        q_lo = min(q_lo, buf[idx, 2])
        q_hi = max(q_hi, buf[idx, 2])
    # The sort key packs the three coordinates into one int64, so the product of their ranges must fit: huge spans
    # (an int64 subtraction wraps to a negative range) refuse the packed path and take the fold instead.
    n_rng = n_hi - n_lo + 1
    f_rng = f_hi - f_lo + 1
    q_rng = q_hi - q_lo + 1
    if n_rng > 0 and f_rng > 0 and q_rng > 0 and float(n_rng) * float(f_rng) * float(q_rng) < 4.0e18:
        keys = np.empty(m, dtype=np.int64)
        for i in range(m):
            keys[i] = ((buf[start + i, 1] - n_lo) * f_rng + (f_hi - buf[start + i, 0])) * q_rng + (
                buf[start + i, 2] - q_lo
            )
        order = np.argsort(keys, kind="mergesort")
        q_sorted = np.empty(m, dtype=np.int64)
        for i in range(m):
            q_sorted[i] = buf[start + i, 2]
        q_sorted.sort()
        uniq = np.empty(m, dtype=np.int64)
        width = 0
        for i in range(m):
            if i == 0 or q_sorted[i] != q_sorted[i - 1]:
                uniq[width] = q_sorted[i]
                width += 1
        fenwick = np.full(width + 1, f_lo - 1, dtype=np.int64)
        keep = np.zeros(m, dtype=np.bool_)
        for pos in range(m):
            i = order[pos]
            body_fever = buf[start + i, 0]
            rank = int(np.searchsorted(uniq[:width], buf[start + i, 2])) + 1
            best = f_lo - 1
            j = rank
            while j > 0:
                if fenwick[j] > best:
                    best = fenwick[j]
                j -= j & -j
            if best >= body_fever:
                continue
            keep[i] = True
            j = rank
            while j <= width:
                if body_fever > fenwick[j]:
                    fenwick[j] = body_fever
                j += j & -j
        write = start
        for i in range(m):
            if keep[i]:
                if write != start + i:
                    buf[write, 0] = buf[start + i, 0]
                    buf[write, 1] = buf[start + i, 1]
                    buf[write, 2] = buf[start + i, 2]
                write += 1
        return int(write)
    kept = start
    for idx in range(start, end):
        cf = buf[idx, 0]
        cn = buf[idx, 1]
        cq = buf[idx, 2]
        kept = _points_append(buf, start, int(kept), int(cf), int(cn), int(cq))
    return int(kept)


@njit(cache=True, nogil=True)
def _points_skyline(buf, start: int, end: int) -> int:
    """Reduce rows [start, end) to their Pareto skyline in place (the dominance of `_points_append`); returns
    the new end. A packet spanning several fever ends can hold points one end dominates with another's, and the queue's
    unions keep a packet verbatim when it is the only operand.

    The incremental fold costs O(m x kept), which is O(m) when the skyline stays small - the common case, packets
    and state windows reduce to a handful of rows. Only when the kept set itself grows past the crossover measured
    below (~64 rows: where an insertion's kept-set scan exceeds a Fenwick update's amortized cost) does the fold go
    quadratic, so at that point the unprocessed tail is slid down behind the kept prefix and the window is finished
    by `_points_skyline_sorted`. Rows already dropped are dominated by a kept row, so re-reducing kept prefix + tail
    yields the same set; the prefix and the tail each keep original order, so the output order is unchanged too."""
    kept = start
    for idx in range(start, end):
        cf = buf[idx, 0]
        cn = buf[idx, 1]
        cq = buf[idx, 2]
        kept = _points_append(buf, start, int(kept), int(cf), int(cn), int(cq))
        if kept - start > 64:
            remaining = end - (idx + 1)
            for i in range(remaining):
                buf[kept + i, 0] = buf[idx + 1 + i, 0]
                buf[kept + i, 1] = buf[idx + 1 + i, 1]
                buf[kept + i, 2] = buf[idx + 1 + i, 2]
            return _points_skyline_sorted(buf, start, int(kept + remaining))
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


@njit(cache=True, nogil=True, inline="always")
def _body_end_shifts(end: int, activation: int, edge_e: int, is_region: bool, reg):
    """Per-end (body_fever, normal_great, fever_great) shifts for one body activation packet."""
    kind, normal_base, act_extra, fg_run_lo, great_end = reg
    bf_sh = end - activation
    if is_region:
        fg_run_hi = end if end < great_end else great_end
        overlap_fg = fg_run_hi - fg_run_lo if fg_run_hi > fg_run_lo else 0
        ng_sh = normal_base - overlap_fg
        fg_sh = overlap_fg + act_extra + (end - edge_e if end > edge_e else 0)
    else:
        ng_sh = normal_base
        fg_sh = kind + (end - edge_e if end > edge_e else 0)
    return bf_sh, ng_sh, fg_sh


@njit(cache=True, nogil=True)
def _body_tails_scalar(n: int, offset: int, reachable, ends, pair_epoch: int, bit_epoch: int):
    """O(n) scalar body DP for all-Perfect zero-Great geometries (Timeline Precise and non_fever_base == 0).
    Every body state has at most one (ng=0, fg=0) row, avoiding queue, packet, pair-table and cone allocations."""
    perfect_valid = ends.perfect_valid
    perfect_e = ends.perfect_e
    perfect_exit_e = ends.perfect_exit_e
    cap = (n - 98) if n > 100 else 1
    body_values = np.empty((cap, 3), dtype=np.uint64)
    body_values[0, 0] = 0
    body_values[0, 1] = 0
    body_values[0, 2] = 0
    body_starts = np.zeros(n + 1, dtype=np.int32)
    body_counts = np.zeros(n + 1, dtype=np.int32)
    body_counts[n] = 1
    cursor = 1
    states = 0
    generated = 0
    retained = 1
    for state in range(n - 1, 99, -1):
        if not reachable[state]:
            continue
        states += 1
        activation = state + offset
        if activation < n and perfect_valid[activation] != 0:
            edge_e = int(perfect_e[activation])
            lo_e = int(perfect_exit_e[activation])
            if edge_e < lo_e:
                lo_e = edge_e
            best_bf = -1
            if lo_e == edge_e:
                if body_counts[lo_e] > 0:
                    best_bf = int(body_values[body_starts[lo_e], 0]) + lo_e - activation
            else:
                for end in range(lo_e, edge_e + 1):
                    if body_counts[end] > 0:
                        cand = int(body_values[body_starts[end], 0]) + end - activation
                        if cand > best_bf:
                            best_bf = cand
            if best_bf >= 0:
                generated += 1
                body_starts[state] = cursor
                body_values[cursor, 0] = np.uint64(best_bf)
                body_values[cursor, 1] = np.uint64(0)
                body_values[cursor, 2] = np.uint64(0)
                cursor += 1
        body_counts[state] = 1
        retained += 1
    return body_values, body_starts, body_counts, states, generated, retained, 1, pair_epoch, bit_epoch


@njit(cache=True, nogil=True)
def _body_tails(n: int, families, reachable, region, ends, scratch):
    """The tail frontier of every reachable body state, states n - 1 down to 100: rows (body fever, body Greats, fever
    Greats) of `body_values`, addressed per state by body_starts / body_counts. State n holds the tail of a play that
    never activates again, and a state with no candidate shares it.

    Returns (body_values, body_starts, body_counts, states evaluated, rows generated, rows retained, the largest
    frontier, the pair epoch, the bit epoch)."""
    (
        pair_mod, best_fever_by_pair, pair_stamp, touched_pair, pair_epoch,
        bit_values, bit_stamps, bit_epoch, max_eg_width, sort_bits,
    ) = scratch
    family_count = families.shape[0]
    if (
        family_count == 1
        and families[0, 0] == _PERFECT_FAMILY
        and families[0, 2] == families[0, 3]
        and families[0, 1] == -2 * families[0, 2]
        and max_eg_width == 0
    ):
        return _body_tails_scalar(n, int(families[0, 2]), reachable, ends, pair_epoch, bit_epoch)
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
    queue = np.empty((max(1, family_count), 16, 4), dtype=np.int64)
    heads = np.zeros(max(1, family_count), dtype=np.int64)
    tails = np.zeros(max(1, family_count), dtype=np.int64)
    next_push = np.full(max(1, family_count), n - 1, dtype=np.int64)
    packet = np.empty((64, 3), dtype=np.int64)
    kept = np.empty((1024, 4), dtype=np.int64)
    cone_cap = 64
    cone_scores = np.empty((cone_cap, 8), dtype=np.float64)
    cone_sums = np.empty(cone_cap, dtype=np.float64)
    cone_order = np.empty(cone_cap, dtype=np.int64)
    cone_meta = np.empty((cone_cap, 3), dtype=np.int64)
    cone_mask = np.empty(cone_cap, dtype=np.uint8)
    states = 0
    generated = 0
    retained = 1
    largest = 1
    max_queue_fg = 0
    pair_size = best_fever_by_pair.shape[0]
    for state in range(n - 1, 99, -1):
        if not reachable[state]:
            continue
        for family in range(family_count):
            kind, defect, first_offset = families[family, 0], families[family, 1], families[family, 2]
            newest = state + families[family, 3]
            head = heads[family]
            tail_end = tails[family]
            while head < tail_end and queue[family, head, 3] > newest:
                head += 1
            heads[family] = head
            first_push = min(next_push[family], newest - first_offset) + first_offset
            next_push[family] = state - 1
            for activation in range(first_push, state + first_offset - 1, -1):
                if activation >= n:
                    continue
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

                if lo_e == eg_e:
                    need = int(body_counts[lo_e])
                    if need <= 0:
                        continue
                    n_ends, only_end = 1, lo_e
                else:
                    need, n_ends, only_end = 0, 0, lo_e
                    for end in range(lo_e, eg_e + 1):
                        c_end = int(body_counts[end])
                        if c_end > 0:
                            need += c_end
                            n_ends += 1
                            only_end = end
                    if need == 0:
                        continue
                if need > packet.shape[0]:
                    packet = _rows_ensure(packet, 0, need)
                is_region = kind == _REGION_FAMILY
                if is_region:
                    bg_lo = run_start if run_start > 100 else 100
                    bg_hi = great_end if great_end < n else n
                    body_great_run = bg_hi - bg_lo if bg_hi > bg_lo else 0
                    act_extra = 1 if (activation < run_start or activation >= great_end) else 0
                    fg_run_lo = activation if activation > run_start else run_start
                    normal_base = 2 * activation + body_great_run - 2 * first_offset
                else:
                    act_extra, fg_run_lo, normal_base = 0, 0, 2 * activation + defect
                reg_info = (kind, normal_base, act_extra, fg_run_lo, great_end)
                if n_ends == 1:
                    bf_sh, ng_sh, fg_sh = _body_end_shifts(only_end, activation, edge_e, is_region, reg_info)
                    st = int(body_starts[only_end])
                    for tail in range(need):
                        tfg = np.int64(body_values[st + tail, 2])
                        packet[tail, 0] = np.int64(body_values[st + tail, 0]) + bf_sh
                        packet[tail, 1] = np.int64(body_values[st + tail, 1]) - tfg + ng_sh
                        packet[tail, 2] = tfg + fg_sh
                    rows = need
                else:
                    written = 0
                    for end in range(lo_e, eg_e + 1):
                        cnt = int(body_counts[end])
                        if cnt <= 0:
                            continue
                        bf_sh, ng_sh, fg_sh = _body_end_shifts(end, activation, edge_e, is_region, reg_info)
                        st = int(body_starts[end])
                        for tail in range(cnt):
                            tfg = np.int64(body_values[st + tail, 2])
                            packet[written, 0] = np.int64(body_values[st + tail, 0]) + bf_sh
                            packet[written, 1] = np.int64(body_values[st + tail, 1]) - tfg + ng_sh
                            packet[written, 2] = tfg + fg_sh
                            written += 1
                    rows = _points_skyline(packet, 0, written)
                write = head
                if rows == 1:
                    p0, p1, p2 = packet[0, 0], packet[0, 1], packet[0, 2]
                    for queued in range(head, tail_end):
                        if p0 >= queue[family, queued, 0] and p1 <= queue[family, queued, 1] and p2 <= queue[family, queued, 2]:
                            continue
                        if write != queued:
                            queue[family, write, 0] = queue[family, queued, 0]
                            queue[family, write, 1] = queue[family, queued, 1]
                            queue[family, write, 2] = queue[family, queued, 2]
                            queue[family, write, 3] = queue[family, queued, 3]
                        write += 1
                else:
                    max_p0, min_p1, min_p2 = packet[0, 0], packet[0, 1], packet[0, 2]
                    for p in range(1, rows):
                        if packet[p, 0] > max_p0:
                            max_p0 = packet[p, 0]
                        if packet[p, 1] < min_p1:
                            min_p1 = packet[p, 1]
                        if packet[p, 2] < min_p2:
                            min_p2 = packet[p, 2]
                    for queued in range(head, tail_end):
                        q0, q1, q2 = queue[family, queued, 0], queue[family, queued, 1], queue[family, queued, 2]
                        dominated = False
                        if q0 <= max_p0 and q1 >= min_p1 and q2 >= min_p2:
                            for p in range(rows):
                                if packet[p, 0] >= q0 and packet[p, 1] <= q1 and packet[p, 2] <= q2:
                                    dominated = True
                                    break
                        if not dominated:
                            if write != queued:
                                queue[family, write, 0] = q0
                                queue[family, write, 1] = q1
                                queue[family, write, 2] = q2
                                queue[family, write, 3] = queue[family, queued, 3]
                            write += 1
                if write + rows > queue.shape[1]:
                    for queued in range(head, write):
                        queue[family, queued - head, 0] = queue[family, queued, 0]
                        queue[family, queued - head, 1] = queue[family, queued, 1]
                        queue[family, queued - head, 2] = queue[family, queued, 2]
                        queue[family, queued - head, 3] = queue[family, queued, 3]
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
                    fg_p = packet[p, 2]
                    queue[family, write, 0] = packet[p, 0]
                    queue[family, write, 1] = packet[p, 1]
                    queue[family, write, 2] = fg_p
                    queue[family, write, 3] = activation
                    if fg_p > max_queue_fg:
                        max_queue_fg = int(fg_p)
                    write += 1
                heads[family] = head
                tails[family] = write
                tail_end = write

        states += 1
        total_live = 0
        only_fam = -1
        for f_i in range(family_count):
            cnt_f = tails[f_i] - heads[f_i]
            if cnt_f > 0:
                total_live += cnt_f
                only_fam = f_i
        frontier = 1
        if total_live == 1:
            generated += 1
            r_idx = heads[only_fam]
            normal_great = queue[only_fam, r_idx, 1] - 2 * state
            if normal_great >= 0:
                fever_great = queue[only_fam, r_idx, 2]
                if fever_great < 0 or fever_great >= pair_mod:
                    raise ValueError("FG response body skyline fever-great exceeded pair radix")
                if normal_great * pair_mod + fever_great >= pair_size:
                    raise ValueError("FG response body skyline pair bound was too small")
                if cursor + 1 > body_values.shape[0]:
                    body_values = _rows_ensure(body_values, cursor, 1)
                body_starts[state] = cursor
                body_values[cursor, 0] = np.uint64(queue[only_fam, r_idx, 0])
                body_values[cursor, 1] = np.uint64(normal_great + fever_great)
                body_values[cursor, 2] = np.uint64(fever_great)
                cursor += 1
        elif total_live > 1:
            pair_epoch += 1
            live_mod = max_queue_fg + 1 if max_queue_fg < pair_mod else pair_mod
            touched, read = touch_body_rows(
                queue, heads, tails, state, (live_mod, pair_epoch), pair_stamp, best_fever_by_pair, touched_pair
            )
            generated += read
            if touched > 0:
                if touched > kept.shape[0]:
                    kept = _rows_ensure(kept, 0, touched)
                if live_mod > 1:
                    bit_epoch += 1
                frontier = _reduce_touched_pairs_inplace(
                    live_mod,
                    touched_pair,
                    touched,
                    best_fever_by_pair,
                    (bit_values, bit_stamps, bit_epoch, sort_bits),
                    kept,
                )
                if frontier >= 2:
                    if frontier > cone_cap:
                        while cone_cap < frontier:
                            cone_cap *= 2
                        cone_scores = np.empty((cone_cap, 8), dtype=np.float64)
                        cone_sums = np.empty(cone_cap, dtype=np.float64)
                        cone_order = np.empty(cone_cap, dtype=np.int64)
                        cone_meta = np.empty((cone_cap, 3), dtype=np.int64)
                        cone_mask = np.empty(cone_cap, dtype=np.uint8)
                    frontier = _body_cone_filter_buf(
                        kept, frontier, cone_scores, cone_sums, cone_order, cone_meta, cone_mask
                    )
                if cursor + frontier > body_values.shape[0]:
                    body_values = _rows_ensure(body_values, cursor, frontier)
                body_starts[state] = cursor
                for row in range(frontier):
                    fg_v = kept[row, 2]
                    body_values[cursor + row, 0] = np.uint64(kept[row, 0])
                    body_values[cursor + row, 1] = np.uint64(kept[row, 1] + fg_v)
                    body_values[cursor + row, 2] = np.uint64(fg_v)
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
def _state_points(entries, count: int, n: int, head, scratch):
    """All candidate points (body fever, normal Greats, fever Greats, pattern id) of one state's activation sections.

    Sections whose activation and ends all lie in the body with constant Great overlap are grouped by their
    (exit, early-Great) window pair: dominated group members are dropped in-place (insertion sort when <= 32), and
    each window copies single-end tail slices directly or reduces multi-end slices via `_points_skyline`.
    Returns (points, m, patterns, slots, masks, arena)."""
    points, slots, masks, arena = scratch
    width = n + 2
    rows = max(1, count)
    cap = slots.shape[0]
    while cap < 2 * rows:
        cap *= 2
    if cap != slots.shape[0]:
        slots = np.empty(cap, dtype=np.int64)
    slots[:] = -1
    if masks.shape[0] < rows:
        masks = np.empty((rows, 4), dtype=np.uint64)
    patterns = 0
    info = np.empty((rows, 4), dtype=np.int64)
    table_cap = 16
    while table_cap < 2 * rows:
        table_cap *= 2
    table_key = np.full(table_cap, -1, dtype=np.int64)
    table_head = np.empty(table_cap, dtype=np.int64)
    group_slots = np.empty(rows, dtype=np.int64)
    members = np.empty(rows, dtype=np.int64)
    member_key = np.empty(rows, dtype=np.int64)
    member_radix = n + 2
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
        if great_start < 100 and great_end > great_start:
            great_lo, great_hi = _range_mask(int(great_start), int(great_end), n)
        else:
            great_lo, great_hi = np.uint64(0), np.uint64(0)
        if 0 <= agi < 100:
            act_lo, act_hi = _single_head_mask(int(agi), n)
            great_lo |= act_lo
            great_hi |= act_hi
        bg_lo = great_start if great_start > 100 else 100
        bg_hi = great_end if great_end < n else n
        body_great = bg_hi - bg_lo if bg_hi > bg_lo else 0
        edge_ng = body_great - overlap_base
        edge_fg = overlap_base
        if agi >= activation and agi < min(base_e, n) and (agi < great_start or agi >= great_end):
            edge_fg += 1
        if (
            prev_pid >= 0
            and masks[prev_pid, 0] == np.uint64(0)
            and masks[prev_pid, 1] == np.uint64(0)
            and masks[prev_pid, 2] == great_lo
            and masks[prev_pid, 3] == great_hi
        ):
            pid = prev_pid
        else:
            pid, patterns = _intern_reserved(slots, masks, patterns, np.uint64(0), np.uint64(0), great_lo, great_hi)
        prev_pid = pid
        key = (lo_e * width + base_e) * width + (eg_e if eg_e > base_e else 0)
        info[idx, 0] = pid
        info[idx, 1] = edge_ng
        info[idx, 2] = edge_fg
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
        member_count = 0
        idx = first
        while idx >= 0:
            members[member_count] = idx
            member_key[member_count] = info[idx, 1] * member_radix + info[idx, 2]
            member_count += 1
            idx = info[idx, 3]
        if member_count > 1:
            if member_count <= 32:
                for i in range(1, member_count):
                    mi = members[i]
                    ki = member_key[i]
                    j = i - 1
                    while j >= 0 and member_key[j] > ki:
                        members[j + 1] = members[j]
                        member_key[j + 1] = member_key[j]
                        j -= 1
                    members[j + 1] = mi
                    member_key[j + 1] = ki
            else:
                member_order = np.argsort(member_key[:member_count])
                tmp_members = members[:member_count].copy()
                for i in range(member_count):
                    members[i] = tmp_members[member_order[i]]
            for apos in range(member_count):
                a_idx = members[apos]
                if info[a_idx, 0] < 0:
                    continue
                a_activation = entries[a_idx, 0]
                a_normal = info[a_idx, 1]
                a_fever = info[a_idx, 2]
                for bpos in range(member_count):
                    b_idx = members[bpos]
                    if info[b_idx, 1] > a_normal:
                        break
                    if (
                        b_idx != a_idx
                        and info[b_idx, 0] >= 0
                        and entries[b_idx, 0] <= a_activation
                        and info[b_idx, 2] <= a_fever
                        and _pattern_dominates(masks, info[b_idx, 0], info[a_idx, 0])
                    ):
                        info[a_idx, 0] = -2
                        break
        lo_e = int(entries[first, 2])
        base_e = int(entries[first, 1])
        eg_e = int(entries[first, 3])
        all_rows = 0
        for half in range(2 if eg_e > base_e else 1):
            w_lo = lo_e if half == 0 else base_e + 1
            w_hi = base_e if half == 0 else eg_e
            fg_base = -1 if half == 0 else base_e
            if w_lo == w_hi:
                need = int(body_counts[w_lo])
                n_ends, only_end = (1, w_lo) if need > 0 else (0, w_lo)
            else:
                need, n_ends, only_end = 0, 0, w_lo
                for end_e in range(w_lo, w_hi + 1):
                    tails = int(body_counts[end_e])
                    if tails > 0:
                        need += tails
                        n_ends += 1
                        only_end = end_e
            if need <= 0:
                continue
            if all_rows + need > arena.shape[0]:
                arena = _rows_ensure(arena, all_rows, need)
            if n_ends == 1:
                fg_sh = 0 if fg_base < 0 else only_end - fg_base
                st = int(body_starts[only_end])
                for tail in range(need):
                    tfg = np.int64(body_values[st + tail, 2])
                    arena[all_rows + tail, 0] = np.int64(body_values[st + tail, 0]) + only_end
                    arena[all_rows + tail, 1] = np.int64(body_values[st + tail, 1]) - tfg
                    arena[all_rows + tail, 2] = tfg + fg_sh
                all_rows += need
            else:
                written = all_rows
                for end_e in range(w_lo, w_hi + 1):
                    tails = int(body_counts[end_e])
                    if tails <= 0:
                        continue
                    fg_sh = 0 if fg_base < 0 else end_e - fg_base
                    st = int(body_starts[end_e])
                    for tail in range(tails):
                        tfg = np.int64(body_values[st + tail, 2])
                        arena[written, 0] = np.int64(body_values[st + tail, 0]) + end_e
                        arena[written, 1] = np.int64(body_values[st + tail, 1]) - tfg
                        arena[written, 2] = tfg + fg_sh
                        written += 1
                all_rows = _points_skyline(arena, all_rows, written)
        idx = first
        while idx >= 0:
            if info[idx, 0] >= 0:
                activation = entries[idx, 0]
                pid, ng, fg = info[idx, 0], info[idx, 1], info[idx, 2]
                if m + all_rows > points.shape[0]:
                    points = _rows_ensure(points, m, all_rows)
                for row in range(all_rows):
                    points[m, 0] = arena[row, 0] - activation
                    points[m, 1] = arena[row, 1] + ng
                    points[m, 2] = arena[row, 2] + fg
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
    return points, int(m), int(patterns), slots, masks, arena


@njit(cache=True, nogil=True)
def _reduce_overflow_bucket(bucketed, start: int, end: int, p_stride: int, need_pairs: int, fen_ws, p_stack):
    """Cold fallback when a pattern bucket's pair table exceeds the reusable workspace; uses the same reducer."""
    pv = np.empty(need_pairs, dtype=np.int32)
    ps = np.zeros(need_pairs, dtype=np.int32)
    pt = np.empty(end - start, dtype=np.int32)
    u = 0
    for src in range(start, end):
        bf = bucketed[src, 0]
        pair = bucketed[src, 1] * p_stride + bucketed[src, 2]
        if ps[pair] == 0:
            ps[pair] = 1
            pv[pair] = bf
            pt[u] = pair
            u += 1
        elif bf > pv[pair]:
            pv[pair] = bf
    if u > p_stack.shape[0]:
        p_stack = _rows_ensure(p_stack, 0, u)
    return p_stack, _reduce_touched_pairs_inplace(p_stride, pt, u, pv, fen_ws, p_stack)


@njit(cache=True, nogil=True)
def _points_frontier(points, masks, sizes, head, fen, pair_ws):
    """A state's frontier from its candidate points, by three reductions, cheapest and strongest first:

    1. Counting-sort by integer pattern id (O(m + P)), then per-pattern skyline + upper hulls: singletons and pairs
       emit in O(1); buckets `b >= 3` stamp into the reusable pair table with L1-compact stride `p_max_fg + 1` and
       reduce in one fused pass via `_reduce_touched_pairs_inplace`.
    2. The head envelope (cone) filter across patterns (`head_envelope_filter`, lossless by its 16-corner proof).
    3. The exact structural Pareto set of what remains, chained by fever/Great overlap pair.
    No points gives the zero surface when `empty_is_zero`, else nothing. Returns (frontier, pair_epoch, fen_stamp)."""
    m, n, patterns = sizes
    lo_pos, hi_pos, empty_is_zero = head
    fen_values, fen_stamps, fen_stamp, sort_bits = fen
    pair_values, pair_stamps, pair_touched, pair_epoch = pair_ws
    if m == 0:
        return np.zeros((1 if empty_is_zero else 0, 7), dtype=np.uint64), pair_epoch, fen_stamp
    radix = n + 1
    pair_size = pair_values.shape[0]
    pair_ok = pair_size <= 2147483647
    pat_count = np.zeros(patterns, dtype=np.int64)
    pat_max_ng = np.zeros(patterns, dtype=np.int64)
    pat_max_fg = np.zeros(patterns, dtype=np.int64)
    for idx in range(m):
        bf, ng, fg = points[idx, 0], points[idx, 1], points[idx, 2]
        if bf < 0 or ng < 0 or fg < 0 or bf >= radix or ng >= radix or fg >= radix:
            raise ValueError("FG response candidate body counts out of range")
        pid = points[idx, 3]
        pat_count[pid] += 1
        if ng > pat_max_ng[pid]:
            pat_max_ng[pid] = ng
        if fg > pat_max_fg[pid]:
            pat_max_fg[pid] = fg
    pat_off = np.empty(patterns + 1, dtype=np.int64)
    pat_off[0] = 0
    for p in range(patterns):
        pat_off[p + 1] = pat_off[p] + pat_count[p]
    pat_cur = pat_off[:patterns].copy()
    bucketed = np.empty((m, 3), dtype=np.int64)
    for idx in range(m):
        pid = points[idx, 3]
        pos = pat_cur[pid]
        pat_cur[pid] = pos + 1
        bucketed[pos, 0] = points[idx, 0]
        bucketed[pos, 1] = points[idx, 1]
        bucketed[pos, 2] = points[idx, 2]

    frontier = np.empty((m, 7), dtype=np.uint64)
    out_count = 0
    p_stack = np.empty((64, 4), dtype=np.int64)
    for p in range(patterns):
        start = pat_off[p]
        end = pat_off[p + 1]
        b = end - start
        if b == 0:
            continue
        m0, m1, m2, m3 = masks[p, 0], masks[p, 1], masks[p, 2], masks[p, 3]
        if b == 1:
            p_stack[0, 0], p_stack[0, 1], p_stack[0, 2] = bucketed[start, 0], bucketed[start, 1], bucketed[start, 2]
            kept_p = 1
        elif b == 2:
            bf0, ng0, fg0 = bucketed[start, 0], bucketed[start, 1], bucketed[start, 2]
            bf1, ng1, fg1 = bucketed[start + 1, 0], bucketed[start + 1, 1], bucketed[start + 1, 2]
            if ng1 < ng0 or (ng1 == ng0 and (fg1 < fg0 or (fg1 == fg0 and bf1 > bf0))):
                bf0, bf1, ng0, ng1, fg0, fg1 = bf1, bf0, ng1, ng0, fg1, fg0
            p_stack[0, 0], p_stack[0, 1], p_stack[0, 2] = bf0, ng0, fg0
            if not (ng1 == ng0 and fg1 == fg0) and (fg0 > fg1 or bf1 > bf0):
                p_stack[1, 0], p_stack[1, 1], p_stack[1, 2] = bf1, ng1, fg1
                kept_p = 2
            else:
                kept_p = 1
        else:
            p_stride = pat_max_fg[p] + 1
            need_pairs = (pat_max_ng[p] + 1) * p_stride
            if p_stride > 1:
                fen_stamp += 1
                if fen_stamp > (1 << 30):
                    fen_stamps[:] = 0
                    fen_stamp = 1
            if need_pairs <= pair_size and pair_ok:
                pair_epoch += 1
                if pair_epoch > (1 << 30):
                    pair_stamps[:] = 0
                    pair_epoch = 1
                u = 0
                for src in range(start, end):
                    bf = bucketed[src, 0]
                    pair = bucketed[src, 1] * p_stride + bucketed[src, 2]
                    if pair_stamps[pair] != pair_epoch:
                        pair_stamps[pair] = pair_epoch
                        pair_values[pair] = bf
                        pair_touched[u] = pair
                        u += 1
                    elif bf > pair_values[pair]:
                        pair_values[pair] = bf
                if u > p_stack.shape[0]:
                    p_stack = _rows_ensure(p_stack, 0, u)
                kept_p = _reduce_touched_pairs_inplace(
                    p_stride, pair_touched, u, pair_values, (fen_values, fen_stamps, fen_stamp, sort_bits), p_stack
                )
            else:
                p_stack, kept_p = _reduce_overflow_bucket(
                    bucketed, start, end, p_stride, need_pairs, (fen_values, fen_stamps, fen_stamp, sort_bits), p_stack
                )
        for k in range(kept_p):
            frontier[out_count, 0], frontier[out_count, 1] = m0, m1
            frontier[out_count, 2], frontier[out_count, 3] = m2, m3
            frontier[out_count, 4] = np.uint64(p_stack[k, 0])
            fg_v = np.uint64(p_stack[k, 2])
            frontier[out_count, 5] = np.uint64(p_stack[k, 1]) + fg_v
            frontier[out_count, 6] = fg_v
            out_count += 1

    frontier = head_envelope_filter(frontier[:out_count], lo_pos, hi_pos)
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
    group_cap = 16
    while group_cap < 2 * rows:
        group_cap *= 2
    group_mask = np.empty((group_cap, 2), dtype=np.uint64)
    group_used = np.zeros(group_cap, dtype=np.bool_)
    group_head = np.full(group_cap, -1, dtype=np.int64)
    group_next = np.full(max(1, rows), -1, dtype=np.int64)
    kept = np.empty(max(1, rows), dtype=np.int64)
    kept_count = 0
    for pos in range(rows):
        i = int(rank_order[pos])
        cand = frontier[i]
        pair0 = cand[0] & cand[2]
        pair1 = cand[1] & cand[3]
        slot = np.int64(mask_hash(pair0, pair1, np.uint64(0), np.uint64(0)) & np.uint64(group_cap - 1))
        while group_used[slot] and (group_mask[slot, 0] != pair0 or group_mask[slot, 1] != pair1):
            slot = (slot + 1) & (group_cap - 1)
        dominated = False
        kk = group_head[slot]
        while kk >= 0:
            k = frontier[kept[kk]]
            if (
                k[5] - k[6] <= cand[5] - cand[6]
                and k[6] <= cand[6]
                and (cand[0] & ~k[0]) == 0
                and (cand[1] & ~k[1]) == 0
                and (k[2] & ~cand[2]) == 0
                and (k[3] & ~cand[3]) == 0
            ):
                dominated = True
                break
            kk = group_next[kk]
        if not dominated:
            group_next[kept_count] = group_head[slot]
            group_head[slot] = kept_count
            if not group_used[slot]:
                group_used[slot] = True
                group_mask[slot, 0] = pair0
                group_mask[slot, 1] = pair1
            kept[kept_count] = i
            kept_count += 1
    out = np.empty((kept_count, 7), dtype=np.uint64)
    for kk in range(kept_count):
        out[kk] = frontier[kept[kk]]
    return out, pair_epoch, fen_stamp


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
    pair_values, pair_stamps, pair_touched, bit_values, bit_stamps, pair_epoch, bit_epoch, sort_bits = workspace
    reachable, max_eg_width = reachability_prepass(n, first_activations, runs, ends, forced_timing, region)
    section_bound = n // max(1, int(later_fill[0]) if action_count > 0 else 1) + 4
    pair_mod = min(n + 1, section_bound * (1 + max_eg_width) + 1)
    pair_size = (n + 1) * pair_mod
    if (
        pair_values.shape[0] < pair_size
        or pair_stamps.shape[0] < pair_size
        or pair_touched.shape[0] < pair_size
        or bit_values.shape[0] < n + 2
        or bit_stamps.shape[0] < n + 2
    ):
        raise ValueError("FG first-frontier stamp workspace is undersized for this geometry's pair radix")
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
            max_eg_width,
            sort_bits,
        ),
    )

    head_limit = min(n, 100)
    head_pool = np.empty((256, 7), dtype=np.uint64)
    head_pool_cursor = 0
    head_state_start = np.zeros(max(1, head_limit), dtype=np.int64)
    head_state_count = np.zeros(max(1, head_limit), dtype=np.int64)
    head = _HeadTables(body_values, body_starts, body_counts, head_pool, head_state_start, head_state_count, head_limit)
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
        points, m, patterns, slots, masks, arena = _state_points(
            entries, count, n, head, (points, slots, masks, arena)
        )
        generated_surfaces += m
        frontier, pair_epoch, bit_epoch = _points_frontier(
            points,
            masks,
            (m, n, patterns),
            (state, head_limit, not (first and action_count > 0 and int(first_fill[0]) >= 100)),
            (bit_values, bit_stamps, bit_epoch, sort_bits),
            (pair_values, pair_stamps, pair_touched, pair_epoch),
        )
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)
        if first:
            first_frontier = frontier
            break
        if head_pool_cursor + len(frontier) > head_pool.shape[0]:
            head_pool = _rows_ensure(head_pool, head_pool_cursor, len(frontier))
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
    sort_bits = np.zeros(1024, dtype=np.uint64)
    frontiers = []
    for index in range(count):
        if pair_epoch > (1 << 30):
            w1[:] = 0
            pair_epoch = 0
        if bit_epoch > (1 << 30):
            w4[:] = 0
            bit_epoch = 0
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
            (w0, w1, w2, w3, w4, pair_epoch, bit_epoch, sort_bits),
        )
        frontiers.append(frontier)
        offsets[index + 1] = offsets[index] + frontier.shape[0]
        stats[index, 0], stats[index, 1], stats[index, 2], stats[index, 3] = states, generated, retained, largest
    rows = np.empty((offsets[count], 7), dtype=np.uint64)
    for index in range(count):
        rows[offsets[index] : offsets[index + 1]] = frontiers[index]
    return rows, offsets, stats, pair_epoch, bit_epoch
