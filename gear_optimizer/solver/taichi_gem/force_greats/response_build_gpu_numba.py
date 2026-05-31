import numpy as np
from numba import njit, types
from numba.typed import List

_NUMBA_SURFACE_TYPE = types.UniTuple(types.uint64, 6)
_NUMBA_BODY_PAIR_TYPE = types.UniTuple(types.uint64, 2)
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
def _numba_pack_edge(n: int, fever_start: int, fever_end: int, great_start: int, great_end: int):
    fever_lo, fever_hi = _numba_range_mask(fever_start, fever_end, n)
    great_lo, great_hi = _numba_range_mask(great_start, great_end, n)
    return (
        fever_lo,
        fever_hi,
        great_lo,
        great_hi,
        _numba_body_count(fever_start, fever_end, n),
        _numba_body_count(great_start, great_end, n),
    )


@njit(cache=True, nogil=True)
def _numba_append_surface(bucket, surface) -> bool:
    cf_lo, cf_hi, cg_lo, cg_hi, cbf, cbg = surface
    original_len = len(bucket)
    for idx in range(original_len):
        kept = bucket[idx]
        kf_lo, kf_hi, kg_lo, kg_hi, kbf, kbg = kept
        if (
            kbf >= cbf
            and kbg <= cbg
            and (cf_lo & ~kf_lo) == 0
            and (cf_hi & ~kf_hi) == 0
            and (kg_lo & ~cg_lo) == 0
            and (kg_hi & ~cg_hi) == 0
        ):
            return False

    write = 0
    for idx in range(original_len):
        kept = bucket[idx]
        kf_lo, kf_hi, kg_lo, kg_hi, kbf, kbg = kept
        if not (
            cbf >= kbf
            and cbg <= kbg
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
        ))
        return kept
    for idx in range(len(surfaces)):
        _numba_append_surface(kept, surfaces[idx])
    return kept


@njit(cache=True, nogil=True)
def _numba_body_pair_with_empty_surface():
    kept = List.empty_list(_NUMBA_BODY_PAIR_TYPE)
    kept.append((np.uint64(0), np.uint64(0)))
    return kept


@njit(cache=True, nogil=True)
def _numba_frontier_with_empty_surface():
    kept = List.empty_list(_NUMBA_SURFACE_TYPE)
    kept.append((
        np.uint64(0),
        np.uint64(0),
        np.uint64(0),
        np.uint64(0),
        np.uint64(0),
        np.uint64(0),
    ))
    return kept


@njit(cache=True, nogil=True)
def _numba_single_body_frontier_row(body_fever: int):
    out = np.zeros((1, 6), dtype=np.uint64)
    out[0, 4] = np.uint64(body_fever)
    return out


@njit(cache=True, nogil=True)
def _numba_append_body_tail_surfaces(generated, edge, body_frontier) -> int:
    count = 0
    for tail_idx in range(len(body_frontier)):
        tail_fever, tail_great = body_frontier[tail_idx]
        generated.append((
            edge[0],
            edge[1],
            edge[2],
            edge[3],
            edge[4] + tail_fever,
            edge[5] + tail_great,
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
def _numba_prefix_max_query(bit, idx: int) -> int:
    best = -1
    cursor = int(idx) + 1
    while cursor > 0:
        value = int(bit[cursor])
        if value > best:
            best = value
        cursor -= cursor & -cursor
    return best


@njit(cache=True, nogil=True)
def _numba_prefix_max_update(bit, idx: int, value: int) -> None:
    cursor = int(idx) + 1
    limit = int(bit.shape[0])
    while cursor < limit:
        if int(value) > int(bit[cursor]):
            bit[cursor] = int(value)
        cursor += cursor & -cursor


@njit(cache=True, nogil=True)
def _numba_edge_end_idx_precomputed(
    n: int,
    activation_idx: int,
    forced_start: int,
    forced_applied: int,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    real_time_idx: int,
):
    forced_end = int(forced_start) + int(forced_applied) - 1
    start_time = timestamps[int(activation_idx)]
    edge_e = int(timestamp_end_idx[int(real_time_idx), int(activation_idx)])
    if (
        int(use_forced_great_timing_i) != 0
        and int(forced_applied) > 0
        and int(forced_end) >= int(forced_start)
        and int(forced_end) < int(activation_idx)
        and int(forced_end) < int(n)
    ):
        forced_t = great_candidate_timestamps[int(forced_end)]
        if forced_t > start_time:
            start_time = forced_t
            edge_e = int(great_end_idx[int(real_time_idx), int(forced_end)])
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
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
        int(real_time_idx),
    )
    if int(edge_e) >= 0 and int(action_idx) > 0:
        prev_fill = int(later_fill[int(action_idx) - 1])
        if int(fill) == int(prev_fill):
            prev_e, prev_start_time = _numba_edge_end_idx_precomputed(
                int(n),
                int(state_i) + int(prev_fill),
                int(state_i) + 1,
                int(later_forced[int(action_idx) - 1]),
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                int(real_time_idx),
            )
            if start_time == prev_start_time or int(edge_e) == int(prev_e):
                return -1, start_time
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
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
        int(real_time_idx),
    )
    if int(edge_e) >= 0 and int(action_idx) > 0:
        prev_fill = int(first_fill[int(action_idx) - 1])
        if int(fill) == int(prev_fill):
            prev_e, prev_start_time = _numba_edge_end_idx_precomputed(
                int(n),
                int(prev_fill),
                0,
                int(first_forced[int(action_idx) - 1]),
                int(use_forced_great_timing_i),
                timestamps,
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                int(real_time_idx),
            )
            if start_time == prev_start_time or int(edge_e) == int(prev_e):
                return -1, start_time
    return int(edge_e), start_time


@njit(cache=True, nogil=True)
def _numba_later_next_precomputed(
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
    real_time_idx: int,
) -> int:
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
        int(real_time_idx),
    )
    return int(edge_e)


@njit(cache=True, nogil=True)
def _numba_first_next_precomputed(
    n: int,
    action_idx: int,
    first_fill,
    first_forced,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    real_time_idx: int,
) -> int:
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
        int(real_time_idx),
    )
    return int(edge_e)


@njit(cache=True, nogil=True)
def _numba_reduce_body_first_frontier(
    n: int,
    first_edges_e,
    first_edges_fill,
    first_edges_forced,
    state_frontiers,
):
    candidate_count = 0
    for idx in range(len(first_edges_e)):
        candidate_count += len(state_frontiers[int(first_edges_e[idx])])
    if candidate_count == 0:
        return _numba_frontier_with_empty_surface(), 0

    great_mod = int(n) + 1
    keys = np.empty(candidate_count, dtype=np.int64)
    fevers = np.empty(candidate_count, dtype=np.int32)
    write = 0
    for idx in range(len(first_edges_e)):
        edge_e = int(first_edges_e[idx])
        tail_frontier = state_frontiers[edge_e]
        forced = int(first_edges_forced[idx])
        head_great = min(min(int(n), forced), 100)
        edge_fever = int(_numba_body_count(int(first_edges_fill[idx]), edge_e, int(n)))
        edge_great = int(_numba_body_count(0, min(int(n), forced), int(n)))
        for tail_idx in range(len(tail_frontier)):
            tail_fever, tail_great = tail_frontier[tail_idx]
            great_value = int(edge_great + tail_great)
            fever_value = int(edge_fever + tail_fever)
            keys[write] = np.int64(int(head_great) * int(great_mod) + int(great_value))
            fevers[write] = int(fever_value)
            write += 1

    order = np.argsort(keys)
    best_by_great = np.full(int(n) + 2, -1, dtype=np.int32)
    first_frontier = List.empty_list(_NUMBA_SURFACE_TYPE)
    idx = 0
    while idx < candidate_count:
        source_idx = int(order[idx])
        key = int(keys[source_idx])
        head_great = key // int(great_mod)
        body_great = key - int(head_great) * int(great_mod)
        best_fever = int(fevers[source_idx])
        idx += 1
        while idx < candidate_count and int(keys[int(order[idx])]) == key:
            fever_value = int(fevers[int(order[idx])])
            if fever_value > best_fever:
                best_fever = fever_value
            idx += 1
        if best_fever > _numba_prefix_max_query(best_by_great, int(body_great)):
            great_lo, great_hi = _numba_range_mask(0, int(head_great), int(n))
            first_frontier.append(
                (
                    np.uint64(0),
                    np.uint64(0),
                    great_lo,
                    great_hi,
                    np.uint64(best_fever),
                    np.uint64(body_great),
                )
            )
        _numba_prefix_max_update(best_by_great, int(body_great), int(best_fever))
    if len(first_frontier) == 0:
        return _numba_frontier_with_empty_surface(), candidate_count
    return first_frontier, candidate_count


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
    real_time_idx: int,
) -> int:
    if int(first_fill[0]) < 100:
        return -1
    edge_e = _numba_first_next_precomputed(
        int(n),
        0,
        first_fill,
        first_forced,
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
        int(real_time_idx),
    )
    if edge_e < 0:
        return -1
    total = int(_numba_body_count(int(first_fill[0]), edge_e, int(n)))
    state_i = edge_e
    for _step in range(int(n) + 1):
        if state_i >= int(n):
            return total
        next_i = _numba_later_next_precomputed(
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
            int(real_time_idx),
        )
        if next_i < 0 or next_i <= state_i:
            return -1
        total += int(_numba_body_count(state_i + int(later_fill[0]), next_i, int(n)))
        state_i = next_i
    return -1


@njit(cache=True, nogil=True)
def _numba_max_body_fever_precomputed(
    n: int,
    action_count: int,
    later_fill,
    later_forced,
    first_fill,
    first_forced,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    real_time_idx: int,
) -> int:
    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    for action_idx in range(int(action_count)):
        if int(first_fill[action_idx]) >= int(n):
            break
        edge_e = _numba_first_next_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if edge_e >= 0:
            reachable[edge_e] = True
    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        for action_idx in range(int(action_count)):
            if state_i + int(later_fill[action_idx]) >= int(n):
                break
            edge_e = _numba_later_next_precomputed(
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
                int(real_time_idx),
            )
            if edge_e >= 0:
                reachable[edge_e] = True

    best = np.zeros(int(n) + 1, dtype=np.int32)
    for state_i in range(int(n) - 1, -1, -1):
        if not reachable[state_i]:
            continue
        best_value = 0
        for action_idx in range(int(action_count)):
            if state_i + int(later_fill[action_idx]) >= int(n):
                break
            edge_e = _numba_later_next_precomputed(
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
                int(real_time_idx),
            )
            if edge_e < 0:
                continue
            fever_count = int(_numba_body_count(state_i + int(later_fill[action_idx]), edge_e, int(n)))
            candidate = fever_count + int(best[edge_e])
            if candidate > best_value:
                best_value = candidate
        best[state_i] = best_value

    best_first = 0
    for action_idx in range(int(action_count)):
        if int(first_fill[action_idx]) >= int(n):
            break
        edge_e = _numba_first_next_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if edge_e < 0:
            continue
        fever_count = int(_numba_body_count(int(first_fill[action_idx]), edge_e, int(n)))
        candidate = fever_count + int(best[edge_e])
        if candidate > best_first:
            best_first = candidate
    return best_first


@njit(cache=True, nogil=True)
def _first_frontier_from_body_tail_precomputed_numba(
    n: int,
    action_count: int,
    later_fill,
    later_forced,
    first_fill,
    first_forced,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    real_time_idx: int,
):
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
        int(real_time_idx),
    )
    if zero_body_fever >= 0:
        max_body_fever = _numba_max_body_fever_precomputed(
            int(n),
            int(action_count),
            later_fill,
            later_forced,
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if int(zero_body_fever) == int(max_body_fever):
            return _numba_single_body_frontier_row(zero_body_fever), 0, 0, 1, 1

    reachable = np.zeros(n + 1, dtype=np.bool_)
    reachable[n] = True
    state_frontiers = List.empty_list(_NUMBA_BODY_PAIR_LIST_TYPE)
    for _idx in range(n + 1):
        state_frontiers.append(List.empty_list(_NUMBA_BODY_PAIR_TYPE))
    state_frontiers[n] = _numba_body_pair_with_empty_surface()

    first_edges_e = List.empty_list(types.int64)
    first_edges_fill = List.empty_list(types.int64)
    first_edges_forced = List.empty_list(types.int64)
    for action_idx in range(action_count):
        if int(first_fill[action_idx]) >= int(n):
            break
        edge_e = _numba_first_next_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if edge_e < 0:
            continue
        first_edges_e.append(edge_e)
        first_edges_fill.append(int(first_fill[action_idx]))
        first_edges_forced.append(int(first_forced[action_idx]))
        reachable[edge_e] = True

    for state_i in range(n):
        if not reachable[state_i]:
            continue
        for action_idx in range(action_count):
            if state_i + int(later_fill[action_idx]) >= int(n):
                break
            edge_e = _numba_later_next_precomputed(
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
                int(real_time_idx),
            )
            if edge_e >= 0:
                reachable[edge_e] = True

    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0
    best_fever_by_great = np.zeros(int(n) + 1, dtype=np.int32)
    great_stamp = np.zeros(int(n) + 1, dtype=np.int32)
    touched_great = np.empty(int(n) + 1, dtype=np.int32)
    stamp = 0
    seen_next_stamp = np.zeros(int(n) + 1, dtype=np.int32)
    next_stamp = 0
    for state_i in range(n - 1, -1, -1):
        if not reachable[state_i]:
            continue
        states_evaluated += 1
        frontier = List.empty_list(_NUMBA_BODY_PAIR_TYPE)
        generated_count = 0
        next_stamp += 1
        kept_e = np.empty(int(action_count), dtype=np.int64)
        kept_fever = np.empty(int(action_count), dtype=np.uint64)
        kept_great = np.empty(int(action_count), dtype=np.uint64)
        kept_len = 0
        for action_idx in range(action_count):
            if state_i + int(later_fill[action_idx]) >= int(n):
                break
            edge_e = _numba_later_next_precomputed(
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
                int(real_time_idx),
            )
            if edge_e < 0:
                continue
            if seen_next_stamp[edge_e] == next_stamp:
                continue
            seen_next_stamp[edge_e] = next_stamp
            forced_start = state_i + 1
            kept_e[kept_len] = edge_e
            kept_fever[kept_len] = _numba_body_count(state_i + int(later_fill[action_idx]), edge_e, int(n))
            kept_great[kept_len] = _numba_body_count(
                forced_start,
                min(int(n), forced_start + int(later_forced[action_idx])),
                int(n),
            )
            kept_len += 1

        if kept_len > 0:
            stamp += 1
            touched_count = 0
            for kept_idx in range(kept_len):
                tail_frontier = state_frontiers[int(kept_e[kept_idx])]
                edge_fever = kept_fever[kept_idx]
                edge_great = kept_great[kept_idx]
                for tail_idx in range(len(tail_frontier)):
                    tail_fever, tail_great = tail_frontier[tail_idx]
                    generated_count += 1
                    great_value = int(edge_great + tail_great)
                    fever_value = int(edge_fever + tail_fever)
                    if great_stamp[great_value] != stamp:
                        great_stamp[great_value] = stamp
                        touched_great[touched_count] = great_value
                        touched_count += 1
                        best_fever_by_great[great_value] = fever_value
                    elif fever_value > int(best_fever_by_great[great_value]):
                        best_fever_by_great[great_value] = fever_value
            sorted_great = np.sort(touched_great[:touched_count])
            best_fever_seen = -1
            has_best = False
            idx = 0
            while idx < touched_count:
                great_value = int(sorted_great[idx])
                best_for_great = int(best_fever_by_great[great_value])
                if (not has_best) or best_for_great > best_fever_seen:
                    frontier.append((np.uint64(best_for_great), np.uint64(great_value)))
                    best_fever_seen = best_for_great
                    has_best = True
                idx += 1

        generated_surfaces += generated_count
        if generated_count == 0:
            frontier = _numba_body_pair_with_empty_surface()
        state_frontiers[state_i] = frontier
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)

    first_frontier, first_generated_count = _numba_reduce_body_first_frontier(
        int(n),
        first_edges_e,
        first_edges_fill,
        first_edges_forced,
        state_frontiers,
    )
    generated_surfaces += first_generated_count
    retained_total += len(first_frontier)
    if len(first_frontier) > max_state_frontier:
        max_state_frontier = len(first_frontier)

    out = np.zeros((len(first_frontier), 6), dtype=np.uint64)
    for idx in range(len(first_frontier)):
        surface = first_frontier[idx]
        for col in range(6):
            out[idx, col] = surface[col]
    return out, states_evaluated, generated_surfaces, retained_total, max_state_frontier


@njit(cache=True, nogil=True)
def _first_frontier_from_precomputed_end_indices_numba(
    n: int,
    action_count: int,
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
    real_time_idx: int,
    use_forced_great_timing_i: int,
):
    if int(action_count) > 0 and int(first_fill[0]) >= 100:
        return _first_frontier_from_body_tail_precomputed_numba(
            int(n),
            int(action_count),
            later_fill,
            later_forced,
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
            int(real_time_idx),
        )

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
            int(real_time_idx),
        )
        if int(edge_e) >= 0:
            reachable[int(edge_e)] = True

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
                int(real_time_idx),
            )
            if int(edge_e) >= 0:
                reachable[int(edge_e)] = True

    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0
    best_fever_by_great = np.zeros(int(n) + 1, dtype=np.int32)
    great_stamp = np.zeros(int(n) + 1, dtype=np.int32)
    touched_great = np.empty(int(n) + 1, dtype=np.int32)
    stamp = 0
    seen_next_stamp = np.zeros(int(n) + 1, dtype=np.int32)
    next_stamp = 0

    for state_i in range(int(n) - 1, 99, -1):
        if not reachable[state_i]:
            continue
        states_evaluated += 1
        frontier = List.empty_list(_NUMBA_BODY_PAIR_TYPE)
        generated_count = 0
        next_stamp += 1
        kept_e = np.empty(int(action_count), dtype=np.int64)
        kept_fever = np.empty(int(action_count), dtype=np.uint64)
        kept_great = np.empty(int(action_count), dtype=np.uint64)
        kept_len = 0
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
                int(real_time_idx),
            )
            if int(edge_e) < 0:
                continue
            if seen_next_stamp[int(edge_e)] == next_stamp:
                continue
            seen_next_stamp[int(edge_e)] = next_stamp
            fill = int(later_fill[int(action_idx)])
            forced_start = int(state_i) + 1
            kept_e[kept_len] = int(edge_e)
            kept_fever[kept_len] = _numba_body_count(int(state_i) + int(fill), int(edge_e), int(n))
            kept_great[kept_len] = _numba_body_count(
                int(forced_start),
                min(int(n), int(forced_start) + int(later_forced[int(action_idx)])),
                int(n),
            )
            kept_len += 1

        if kept_len > 0:
            stamp += 1
            touched_count = 0
            for kept_idx in range(kept_len):
                tail_frontier = body_tails[int(kept_e[kept_idx])]
                edge_fever = kept_fever[kept_idx]
                edge_great = kept_great[kept_idx]
                for tail_idx in range(len(tail_frontier)):
                    tail_fever, tail_great = tail_frontier[tail_idx]
                    generated_count += 1
                    great_value = int(edge_great + tail_great)
                    fever_value = int(edge_fever + tail_fever)
                    if great_stamp[great_value] != stamp:
                        great_stamp[great_value] = stamp
                        touched_great[touched_count] = great_value
                        touched_count += 1
                        best_fever_by_great[great_value] = fever_value
                    elif fever_value > int(best_fever_by_great[great_value]):
                        best_fever_by_great[great_value] = fever_value
            sorted_great = np.sort(touched_great[:touched_count])
            best_fever_seen = -1
            has_best = False
            idx = 0
            while idx < touched_count:
                great_value = int(sorted_great[idx])
                best_for_great = int(best_fever_by_great[great_value])
                if (not has_best) or best_for_great > best_fever_seen:
                    frontier.append((np.uint64(best_for_great), np.uint64(great_value)))
                    best_fever_seen = best_for_great
                    has_best = True
                idx += 1

        generated_surfaces += generated_count
        if generated_count == 0:
            frontier = _numba_body_pair_with_empty_surface()
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
                int(real_time_idx),
            )
            if int(edge_e) < 0:
                continue
            fill = int(later_fill[int(action_idx)])
            forced_start = int(state_i) + 1
            edge = _numba_pack_edge(
                int(n),
                int(state_i) + int(fill),
                int(edge_e),
                int(forced_start),
                min(int(n), int(forced_start) + int(later_forced[int(action_idx)])),
            )
            if int(edge_e) >= 100:
                generated_count += _numba_append_body_tail_surfaces(generated, edge, body_tails[int(edge_e)])
            elif int(edge_e) >= head_limit:
                generated_count += _numba_append_terminal_tail_surface(generated, edge)
            else:
                generated_count += _numba_append_surface_tail_surfaces(generated, edge, head_frontiers[int(edge_e)])
        generated_surfaces += generated_count
        frontier = _numba_reduce(generated)
        head_frontiers[state_i] = frontier
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)

    first_generated = List.empty_list(_NUMBA_SURFACE_TYPE)
    first_generated_count = 0
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
            int(real_time_idx),
        )
        if int(edge_e) < 0:
            continue
        fill = int(first_fill[int(action_idx)])
        edge = _numba_pack_edge(
            int(n),
            int(fill),
            int(edge_e),
            0,
            min(int(n), int(first_forced[int(action_idx)])),
        )
        if int(edge_e) >= 100:
            first_generated_count += _numba_append_body_tail_surfaces(first_generated, edge, body_tails[int(edge_e)])
        elif int(edge_e) >= head_limit:
            first_generated_count += _numba_append_terminal_tail_surface(first_generated, edge)
        else:
            first_generated_count += _numba_append_surface_tail_surfaces(
                first_generated,
                edge,
                head_frontiers[int(edge_e)],
            )
    generated_surfaces += first_generated_count
    first_frontier = _numba_reduce(first_generated)
    retained_total += len(first_frontier)
    if len(first_frontier) > max_state_frontier:
        max_state_frontier = len(first_frontier)

    out = np.zeros((len(first_frontier), 6), dtype=np.uint64)
    for idx in range(len(first_frontier)):
        surface = first_frontier[idx]
        for col in range(6):
            out[idx, col] = surface[col]
    return out, states_evaluated, generated_surfaces, retained_total, max_state_frontier
