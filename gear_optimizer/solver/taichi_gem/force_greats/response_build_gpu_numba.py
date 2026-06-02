import numpy as np
from numba import njit, types
from numba.typed import List

_NUMBA_SURFACE_TYPE = types.UniTuple(types.uint64, 7)
_NUMBA_BODY_PAIR_TYPE = types.UniTuple(types.uint64, 3)
_NUMBA_BODY_PAIR_LIST_TYPE = types.ListType(_NUMBA_BODY_PAIR_TYPE)
_NUMBA_SURFACE_LIST_TYPE = types.ListType(_NUMBA_SURFACE_TYPE)

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
def _numba_append_surface(bucket, surface) -> bool:
    cf_lo, cf_hi, cg_lo, cg_hi, cbf, cbg, cbfg = surface
    original_len = len(bucket)
    for idx in range(original_len):
        kept = bucket[idx]
        kf_lo, kf_hi, kg_lo, kg_hi, kbf, kbg, kbfg = kept
        exact_overlap = cbfg == kbfg and (cf_lo & cg_lo) == (kf_lo & kg_lo) and (cf_hi & cg_hi) == (kf_hi & kg_hi)
        if (
            kbf >= cbf
            and kbg <= cbg
            and kbfg <= cbfg
            and exact_overlap
            and (cf_lo & ~kf_lo) == 0
            and (cf_hi & ~kf_hi) == 0
            and (kg_lo & ~cg_lo) == 0
            and (kg_hi & ~cg_hi) == 0
        ):
            return False

    write = 0
    for idx in range(original_len):
        kept = bucket[idx]
        kf_lo, kf_hi, kg_lo, kg_hi, kbf, kbg, kbfg = kept
        exact_overlap = cbfg == kbfg and (cf_lo & cg_lo) == (kf_lo & kg_lo) and (cf_hi & cg_hi) == (kf_hi & kg_hi)
        if not (
            cbf >= kbf
            and cbg <= kbg
            and cbfg <= kbfg
            and exact_overlap
            and (kf_lo & ~cf_lo) == 0
            and (kf_hi & ~cf_hi) == 0
            and (cg_lo & ~kg_lo) == 0
            and (cg_hi & ~kg_hi) == 0
        ):
            bucket[write] = kept
            write += 1
    while len(bucket) > write:
        bucket.pop()
    bucket.append(surface)
    return True


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
    if len(surfaces) == 0:
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
    for idx in range(len(surfaces)):
        _numba_append_surface(kept, surfaces[idx])
    return kept


@njit(cache=True, nogil=True)
def _numba_body_pair_with_empty_surface():
    kept = List.empty_list(_NUMBA_BODY_PAIR_TYPE)
    kept.append((np.uint64(0), np.uint64(0), np.uint64(0)))
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
def _numba_single_body_frontier_row(body_fever: int):
    out = np.zeros((1, 7), dtype=np.uint64)
    out[0, 4] = np.uint64(body_fever)
    return out


@njit(cache=True, nogil=True)
def _numba_append_body_tail_surfaces(generated, edge, body_frontier) -> int:
    count = 0
    for tail_idx in range(len(body_frontier)):
        tail_fever, tail_great, tail_fever_great = body_frontier[tail_idx]
        generated.append((
            edge[0],
            edge[1],
            edge[2],
            edge[3],
            edge[4] + tail_fever,
            edge[5] + tail_great,
            edge[6] + tail_fever_great,
        ))
        count += 1
    return count


@njit(cache=True, nogil=True)
def _numba_append_surface_tail_surfaces(generated, edge, tail_frontier) -> int:
    count = 0
    for tail_idx in range(len(tail_frontier)):
        generated.append(_numba_combine(edge, tail_frontier[tail_idx]))
        count += 1
    return count


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
def _numba_great_range_argmax_idx(
    great_candidate_timestamps,
    great_range_argmax,
    great_range_log2,
    start: int,
    count: int,
    n: int,
) -> int:
    if int(count) <= 0:
        return -1
    start_i = max(0, int(start))
    stop_i = min(int(n), int(start_i) + int(count))
    if int(stop_i) <= int(start_i):
        return -1
    length = int(stop_i) - int(start_i)
    level = int(great_range_log2[int(length)])
    span = int(1) << int(level)
    left_idx = int(great_range_argmax[int(level), int(start_i)])
    right_idx = int(great_range_argmax[int(level), int(stop_i) - int(span)])
    if great_candidate_timestamps[int(right_idx)] >= great_candidate_timestamps[int(left_idx)]:
        return int(right_idx)
    return int(left_idx)


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
    return frontier


@njit(cache=True, nogil=True)
def _numba_edge_end_idx_precomputed(
    n: int,
    activation_idx: int,
    forced_start: int,
    forced_applied: int,
    activation_great_i: int,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    great_range_argmax,
    great_range_log2,
    real_time_idx: int,
):
    start_time = timestamps[int(activation_idx)]
    edge_e = int(timestamp_end_idx[int(real_time_idx), int(activation_idx)])
    if (
        int(use_forced_great_timing_i) != 0
        and int(forced_applied) > 0
        and int(forced_start) < int(activation_idx)
    ):
        carry_idx = _numba_great_range_argmax_idx(
            great_candidate_timestamps,
            great_range_argmax,
            great_range_log2,
            int(forced_start),
            min(int(forced_applied), max(0, int(activation_idx) - int(forced_start))),
            int(n),
        )
        if int(carry_idx) >= 0:
            forced_t = great_candidate_timestamps[int(carry_idx)]
        else:
            forced_t = start_time
        if forced_t > start_time:
            start_time = forced_t
            edge_e = int(great_end_idx[int(real_time_idx), int(carry_idx)])
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
def _numba_later_edge_from_precomputed(
    n: int,
    state_i: int,
    action_idx: int,
    later_fill,
    later_forced,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    great_range_argmax,
    great_range_log2,
    real_time_idx: int,
):
    fill = int(later_fill[int(action_idx)])
    activation = int(state_i) + int(fill)
    if int(activation) >= int(n):
        return -1, np.float32(-1.0)
    edge_e, start_time = _numba_edge_end_idx_precomputed(
        int(n),
        int(activation),
        int(state_i) + 1,
        int(later_forced[int(action_idx)]),
        0,
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
        great_range_argmax,
        great_range_log2,
        int(real_time_idx),
    )
    return int(edge_e), start_time


@njit(cache=True, nogil=True)
def _numba_first_edge_from_precomputed(
    n: int,
    action_idx: int,
    first_fill,
    first_forced,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    great_range_argmax,
    great_range_log2,
    real_time_idx: int,
):
    fill = int(first_fill[int(action_idx)])
    if int(fill) >= int(n):
        return -1, np.float32(-1.0)
    edge_e, start_time = _numba_edge_end_idx_precomputed(
        int(n),
        int(fill),
        0,
        int(first_forced[int(action_idx)]),
        0,
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
        great_range_argmax,
        great_range_log2,
        int(real_time_idx),
    )
    return int(edge_e), start_time


@njit(cache=True, nogil=True)
def _numba_later_activation_edge_from_precomputed(
    n: int,
    state_i: int,
    action_idx: int,
    actions,
    later_fill,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    great_range_argmax,
    great_range_log2,
    real_time_idx: int,
):
    if int(use_forced_great_timing_i) == 0 or int(actions[int(action_idx)]) <= 0:
        return -1, np.float32(-1.0), np.int64(0)
    fill = int(later_fill[int(action_idx)])
    activation = int(state_i) + int(fill)
    if int(activation) >= int(n):
        return -1, np.float32(-1.0), np.int64(0)
    forced_start = int(state_i) + 1
    prefix_forced = min(max(0, int(actions[int(action_idx)]) - 1), max(0, int(activation) - int(forced_start)))
    edge_e, start_time = _numba_edge_end_idx_precomputed(
        int(n),
        int(activation),
        int(forced_start),
        int(prefix_forced),
        1,
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
        great_range_argmax,
        great_range_log2,
        int(real_time_idx),
    )
    return int(edge_e), start_time, np.int64(prefix_forced)


@njit(cache=True, nogil=True)
def _numba_first_activation_edge_from_precomputed(
    n: int,
    action_idx: int,
    actions,
    first_fill,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    great_range_argmax,
    great_range_log2,
    real_time_idx: int,
):
    if int(use_forced_great_timing_i) == 0 or int(actions[int(action_idx)]) <= 0:
        return -1, np.float32(-1.0), np.int64(0)
    activation = int(first_fill[int(action_idx)])
    if int(activation) >= int(n):
        return -1, np.float32(-1.0), np.int64(0)
    prefix_forced = min(max(0, int(actions[int(action_idx)]) - 1), max(0, int(activation)))
    edge_e, start_time = _numba_edge_end_idx_precomputed(
        int(n),
        int(activation),
        0,
        int(prefix_forced),
        1,
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
        great_range_argmax,
        great_range_log2,
        int(real_time_idx),
    )
    return int(edge_e), start_time, np.int64(prefix_forced)


@njit(cache=True, nogil=True)
def _numba_zero_forced_body_fever_precomputed(
    n: int,
    later_fill,
    later_forced,
    first_fill,
    first_forced,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    great_range_argmax,
    great_range_log2,
    real_time_idx: int,
) -> int:
    if int(first_fill[0]) < 100:
        return -1
    edge_e, _start_time = _numba_first_edge_from_precomputed(
        int(n),
        0,
        first_fill,
        first_forced,
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
        great_range_argmax,
        great_range_log2,
        int(real_time_idx),
    )
    if int(edge_e) < 0:
        return -1
    total = int(_numba_body_count(int(first_fill[0]), int(edge_e), int(n)))
    state_i = int(edge_e)
    for _step in range(int(n) + 1):
        if int(state_i) >= int(n):
            return int(total)
        next_e, _later_start_time = _numba_later_edge_from_precomputed(
            int(n),
            int(state_i),
            0,
            later_fill,
            later_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            great_range_argmax,
            great_range_log2,
            int(real_time_idx),
        )
        if int(next_e) < 0 or int(next_e) <= int(state_i):
            return -1
        total += int(_numba_body_count(int(state_i) + int(later_fill[0]), int(next_e), int(n)))
        state_i = int(next_e)
    return -1


@njit(cache=True, nogil=True)
def _numba_max_body_fever_precomputed(
    n: int,
    action_count: int,
    actions,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    great_range_argmax,
    great_range_log2,
    real_time_idx: int,
) -> int:
    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    for action_idx in range(int(action_count)):
        edge_e, _start_time = _numba_first_edge_from_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            great_range_argmax,
            great_range_log2,
            int(real_time_idx),
        )
        if int(edge_e) >= 0:
            reachable[int(edge_e)] = True
        activation_e, _activation_start_time, _prefix_forced = _numba_first_activation_edge_from_precomputed(
            int(n),
            int(action_idx),
            actions,
            first_fill,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            great_range_argmax,
            great_range_log2,
            int(real_time_idx),
        )
        if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
            reachable[int(activation_e)] = True

    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        for action_idx in range(int(action_count)):
            edge_e, _start_time = _numba_later_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                later_fill,
                later_forced,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(edge_e) >= 0:
                reachable[int(edge_e)] = True
            activation_e, _activation_start_time, _prefix_forced = _numba_later_activation_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                actions,
                later_fill,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                reachable[int(activation_e)] = True

    best = np.zeros(int(n) + 1, dtype=np.int32)
    for state_i in range(int(n) - 1, -1, -1):
        if not reachable[state_i]:
            continue
        best_value = 0
        for action_idx in range(int(action_count)):
            edge_e, _start_time = _numba_later_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                later_fill,
                later_forced,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(edge_e) >= 0:
                fill = int(later_fill[int(action_idx)])
                candidate = int(_numba_body_count(int(state_i) + int(fill), int(edge_e), int(n))) + int(best[int(edge_e)])
                if int(candidate) > int(best_value):
                    best_value = int(candidate)
            activation_e, _activation_start_time, _prefix_forced = _numba_later_activation_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                actions,
                later_fill,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                fill = int(later_fill[int(action_idx)])
                candidate = int(_numba_body_count(int(state_i) + int(fill), int(activation_e), int(n))) + int(
                    best[int(activation_e)]
                )
                if int(candidate) > int(best_value):
                    best_value = int(candidate)
        best[state_i] = int(best_value)

    best_first = 0
    for action_idx in range(int(action_count)):
        edge_e, _start_time = _numba_first_edge_from_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            great_range_argmax,
            great_range_log2,
            int(real_time_idx),
        )
        if int(edge_e) >= 0:
            candidate = int(_numba_body_count(int(first_fill[int(action_idx)]), int(edge_e), int(n))) + int(
                best[int(edge_e)]
            )
            if int(candidate) > int(best_first):
                best_first = int(candidate)
        activation_e, _activation_start_time, _prefix_forced = _numba_first_activation_edge_from_precomputed(
            int(n),
            int(action_idx),
            actions,
            first_fill,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            great_range_argmax,
            great_range_log2,
            int(real_time_idx),
        )
        if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
            candidate = int(_numba_body_count(int(first_fill[int(action_idx)]), int(activation_e), int(n))) + int(
                best[int(activation_e)]
            )
            if int(candidate) > int(best_first):
                best_first = int(candidate)
    return int(best_first)


@njit(cache=True, nogil=True)
def _first_frontier_from_precomputed_end_indices_numba(
    n: int,
    action_count: int,
    actions,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    great_range_argmax,
    great_range_log2,
    real_time_idx: int,
    use_forced_great_timing_i: int,
):
    if int(action_count) > 0 and int(first_fill[0]) >= 100:
        zero_body_fever = _numba_zero_forced_body_fever_precomputed(
            int(n),
            later_fill,
            later_forced,
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            great_range_argmax,
            great_range_log2,
            int(real_time_idx),
        )
        if int(zero_body_fever) >= 0:
            max_body_fever = _numba_max_body_fever_precomputed(
                int(n),
                int(action_count),
                actions,
                later_fill,
                first_fill,
                later_forced,
                first_forced,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(zero_body_fever) == int(max_body_fever):
                return _numba_single_body_frontier_row(int(zero_body_fever)), 0, 0, 1, 1

    body_tails = List.empty_list(_NUMBA_BODY_PAIR_LIST_TYPE)
    for _idx in range(int(n) + 1):
        body_tails.append(List.empty_list(_NUMBA_BODY_PAIR_TYPE))
    body_tails[int(n)] = _numba_body_pair_with_empty_surface()

    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    for action_idx in range(int(action_count)):
        edge_e, _start_time = _numba_first_edge_from_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            great_range_argmax,
            great_range_log2,
            int(real_time_idx),
        )
        if int(edge_e) >= 0:
            reachable[int(edge_e)] = True
        activation_e, _activation_start_time, _prefix_forced = _numba_first_activation_edge_from_precomputed(
            int(n),
            int(action_idx),
            actions,
            first_fill,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            great_range_argmax,
            great_range_log2,
            int(real_time_idx),
        )
        if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
            reachable[int(activation_e)] = True

    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        for action_idx in range(int(action_count)):
            edge_e, _start_time = _numba_later_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                later_fill,
                later_forced,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(edge_e) >= 0:
                reachable[int(edge_e)] = True
            activation_e, _activation_start_time, _prefix_forced = _numba_later_activation_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                actions,
                later_fill,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                reachable[int(activation_e)] = True

    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0
    min_later_fill = max(1, int(later_fill[0]) if int(action_count) > 0 else 1)
    pair_mod = min(int(n) + 1, int(n) // int(min_later_fill) + 4)
    pair_size = (int(n) + 1) * int(pair_mod)
    best_fever_by_pair = np.zeros(int(pair_size), dtype=np.int32)
    pair_stamp = np.zeros(int(pair_size), dtype=np.int32)
    touched_pair = np.empty(int(pair_size), dtype=np.int32)
    pair_stamp_value = 0
    bit_values = np.zeros(int(pair_mod) + 1, dtype=np.int32)
    bit_stamps = np.zeros(int(pair_mod) + 1, dtype=np.int32)
    bit_stamp_value = 0

    for state_i in range(int(n) - 1, 99, -1):
        if not reachable[state_i]:
            continue
        states_evaluated += 1
        generated_count = 0
        touched_count = 0
        pair_stamp_value += 1
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        for action_idx in range(int(action_count)):
            edge_e, _start_time = _numba_later_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                later_fill,
                later_forced,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(edge_e) < 0:
                continue
            fill = int(later_fill[int(action_idx)])
            forced_start = int(state_i) + 1
            if int(fill) != int(prev_fill) or int(edge_e) != int(prev_edge_e):
                prev_fill = int(fill)
                prev_edge_e = int(edge_e)
                edge = _numba_pack_edge(
                    int(n),
                    int(state_i) + int(fill),
                    int(edge_e),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(later_forced[int(action_idx)])),
                    -1,
                )
                tail_frontier = body_tails[int(edge_e)]
                for tail_idx in range(len(tail_frontier)):
                    tail_fever, tail_great, tail_fever_great = tail_frontier[tail_idx]
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
                    generated_count += 1

            activation_e, _activation_start_time, prefix_forced = _numba_later_activation_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                actions,
                later_fill,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                if int(fill) == int(prev_activation_fill) and int(activation_e) == int(prev_activation_e):
                    continue
                prev_activation_fill = int(fill)
                prev_activation_e = int(activation_e)
                activation_edge = _numba_pack_edge(
                    int(n),
                    int(state_i) + int(fill),
                    int(activation_e),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(prefix_forced)),
                    int(state_i) + int(fill),
                )
                activation_tail = body_tails[int(activation_e)]
                for tail_idx in range(len(activation_tail)):
                    tail_fever, tail_great, tail_fever_great = activation_tail[tail_idx]
                    touched_count = _numba_touch_body_candidate(
                        activation_edge[4],
                        activation_edge[5],
                        activation_edge[6],
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
                    generated_count += 1

        generated_surfaces += generated_count
        if generated_count == 0:
            frontier = _numba_body_pair_with_empty_surface()
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
        body_tails[state_i] = frontier
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)

    head_limit = min(int(n), 100)
    head_frontiers = List.empty_list(_NUMBA_SURFACE_LIST_TYPE)
    for _idx in range(head_limit):
        head_frontiers.append(List.empty_list(_NUMBA_SURFACE_TYPE))

    for state_i in range(head_limit - 1, -1, -1):
        if not reachable[state_i]:
            continue
        states_evaluated += 1
        generated = List.empty_list(_NUMBA_SURFACE_TYPE)
        generated_count = 0
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        for action_idx in range(int(action_count)):
            edge_e, _start_time = _numba_later_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                later_fill,
                later_forced,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(edge_e) < 0:
                continue
            fill = int(later_fill[int(action_idx)])
            forced_start = int(state_i) + 1
            if int(fill) != int(prev_fill) or int(edge_e) != int(prev_edge_e):
                prev_fill = int(fill)
                prev_edge_e = int(edge_e)
                edge = _numba_pack_edge(
                    int(n),
                    int(state_i) + int(fill),
                    int(edge_e),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(later_forced[int(action_idx)])),
                    -1,
                )
                if int(edge_e) >= 100:
                    generated_count += _numba_append_body_tail_surfaces(generated, edge, body_tails[int(edge_e)])
                elif int(edge_e) >= head_limit:
                    generated_count += _numba_append_terminal_tail_surface(generated, edge)
                else:
                    generated_count += _numba_append_surface_tail_surfaces(
                        generated, edge, head_frontiers[int(edge_e)]
                    )
            activation_e, _activation_start_time, prefix_forced = _numba_later_activation_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                actions,
                later_fill,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                if int(fill) == int(prev_activation_fill) and int(activation_e) == int(prev_activation_e):
                    continue
                prev_activation_fill = int(fill)
                prev_activation_e = int(activation_e)
                activation_edge = _numba_pack_edge(
                    int(n),
                    int(state_i) + int(fill),
                    int(activation_e),
                    int(forced_start),
                    min(int(n), int(forced_start) + int(prefix_forced)),
                    int(state_i) + int(fill),
                )
                if int(activation_e) >= 100:
                    generated_count += _numba_append_body_tail_surfaces(
                        generated,
                        activation_edge,
                        body_tails[int(activation_e)],
                    )
                elif int(activation_e) >= head_limit:
                    generated_count += _numba_append_terminal_tail_surface(generated, activation_edge)
                else:
                    generated_count += _numba_append_surface_tail_surfaces(
                        generated,
                        activation_edge,
                        head_frontiers[int(activation_e)],
                    )
        generated_surfaces += generated_count
        frontier = _numba_reduce(generated)
        head_frontiers[state_i] = frontier
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)

    first_generated_count = 0
    first_frontier = List.empty_list(_NUMBA_SURFACE_TYPE)
    if int(action_count) > 0 and int(first_fill[0]) >= 100:
        for head_great_count in range(101):
            touched_count = 0
            pair_stamp_value += 1
            prev_fill = -1
            prev_edge_e = -1
            prev_activation_fill = -1
            prev_activation_e = -1
            for action_idx in range(int(action_count)):
                edge_e, _start_time = _numba_first_edge_from_precomputed(
                    int(n),
                    int(action_idx),
                    first_fill,
                    first_forced,
                    int(use_forced_great_timing_i),
                    timestamps,
                    great_candidate_timestamps,
                    timestamp_end_idx,
                    great_end_idx,
                    great_range_argmax,
                    great_range_log2,
                    int(real_time_idx),
                )
                if int(edge_e) < 100:
                    continue
                normal_head_great = min(100, max(0, int(first_forced[int(action_idx)])))
                if int(normal_head_great) == int(head_great_count):
                    fill = int(first_fill[int(action_idx)])
                    if int(fill) != int(prev_fill) or int(edge_e) != int(prev_edge_e):
                        prev_fill = int(fill)
                        prev_edge_e = int(edge_e)
                        edge = _numba_pack_edge(
                            int(n),
                            int(fill),
                            int(edge_e),
                            0,
                            min(int(n), int(first_forced[int(action_idx)])),
                            -1,
                        )
                        tail_frontier = body_tails[int(edge_e)]
                        for tail_idx in range(len(tail_frontier)):
                            tail_fever, tail_great, tail_fever_great = tail_frontier[tail_idx]
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
                            first_generated_count += 1
                activation_e, _activation_start_time, prefix_forced = _numba_first_activation_edge_from_precomputed(
                    int(n),
                    int(action_idx),
                    actions,
                    first_fill,
                    int(use_forced_great_timing_i),
                    timestamps,
                    great_candidate_timestamps,
                    timestamp_end_idx,
                    great_end_idx,
                    great_range_argmax,
                    great_range_log2,
                    int(real_time_idx),
                )
                if int(activation_e) < 100 or int(activation_e) <= int(edge_e):
                    continue
                activation_head_great = min(100, max(0, int(prefix_forced)))
                if int(activation_head_great) != int(head_great_count):
                    continue
                fill = int(first_fill[int(action_idx)])
                if int(fill) == int(prev_activation_fill) and int(activation_e) == int(prev_activation_e):
                    continue
                prev_activation_fill = int(fill)
                prev_activation_e = int(activation_e)
                activation_edge = _numba_pack_edge(
                    int(n),
                    int(fill),
                    int(activation_e),
                    0,
                    min(int(n), int(prefix_forced)),
                    int(fill),
                )
                activation_tail = body_tails[int(activation_e)]
                for tail_idx in range(len(activation_tail)):
                    tail_fever, tail_great, tail_fever_great = activation_tail[tail_idx]
                    touched_count = _numba_touch_body_candidate(
                        activation_edge[4],
                        activation_edge[5],
                        activation_edge[6],
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
                    first_generated_count += 1

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
                _numba_append_surface(
                    first_frontier,
                    _numba_body_prefix_surface(
                        int(head_great_count),
                        body_fever,
                        body_great,
                        body_fever_great,
                    ),
                )
    else:
        first_generated = List.empty_list(_NUMBA_SURFACE_TYPE)
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        for action_idx in range(int(action_count)):
            edge_e, _start_time = _numba_first_edge_from_precomputed(
                int(n),
                int(action_idx),
                first_fill,
                first_forced,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(edge_e) < 0:
                continue
            fill = int(first_fill[int(action_idx)])
            if int(fill) != int(prev_fill) or int(edge_e) != int(prev_edge_e):
                prev_fill = int(fill)
                prev_edge_e = int(edge_e)
                edge = _numba_pack_edge(
                    int(n),
                    int(fill),
                    int(edge_e),
                    0,
                    min(int(n), int(first_forced[int(action_idx)])),
                    -1,
                )
                if int(edge_e) >= 100:
                    first_generated_count += _numba_append_body_tail_surfaces(
                        first_generated, edge, body_tails[int(edge_e)]
                    )
                elif int(edge_e) >= head_limit:
                    first_generated_count += _numba_append_terminal_tail_surface(first_generated, edge)
                else:
                    first_generated_count += _numba_append_surface_tail_surfaces(
                        first_generated,
                        edge,
                        head_frontiers[int(edge_e)],
                    )
            activation_e, _activation_start_time, prefix_forced = _numba_first_activation_edge_from_precomputed(
                int(n),
                int(action_idx),
                actions,
                first_fill,
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                great_range_argmax,
                great_range_log2,
                int(real_time_idx),
            )
            if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
                if int(fill) == int(prev_activation_fill) and int(activation_e) == int(prev_activation_e):
                    continue
                prev_activation_fill = int(fill)
                prev_activation_e = int(activation_e)
                activation_edge = _numba_pack_edge(
                    int(n),
                    int(fill),
                    int(activation_e),
                    0,
                    min(int(n), int(prefix_forced)),
                    int(fill),
                )
                if int(activation_e) >= 100:
                    first_generated_count += _numba_append_body_tail_surfaces(
                        first_generated,
                        activation_edge,
                        body_tails[int(activation_e)],
                    )
                elif int(activation_e) >= head_limit:
                    first_generated_count += _numba_append_terminal_tail_surface(first_generated, activation_edge)
                else:
                    first_generated_count += _numba_append_surface_tail_surfaces(
                        first_generated,
                        activation_edge,
                        head_frontiers[int(activation_e)],
                    )
        first_frontier = _numba_reduce(first_generated)
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
