import numpy as np
from numba import njit, types
from numba.typed import Dict, List

_NUMBA_SURFACE_TYPE = types.UniTuple(types.uint64, 7)
_NUMBA_EXACT_OVERLAP_KEY_TYPE = types.UniTuple(types.uint64, 3)
_NUMBA_BODY_PAIR_TYPE = types.UniTuple(types.uint64, 3)
_NUMBA_PACKET_POINT_TYPE = types.UniTuple(types.int64, 3)
_NUMBA_PACKET_POINT_LIST_TYPE = types.ListType(_NUMBA_PACKET_POINT_TYPE)
_NUMBA_PACKET_POINT_STACK_TYPE = types.ListType(_NUMBA_PACKET_POINT_LIST_TYPE)
_NUMBA_INT_LIST_TYPE = types.ListType(types.int64)
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
    # Exact-overlap-bucketed Pareto maxima. The `_numba_append_surface` dominance gate requires
    # exact_overlap = (equal body_fever_great, equal head fever&great masks); surfaces in different
    # exact_overlap classes can never dominate each other, so confine every dominance scan to its
    # class. Buckets are intrusive hash chains: `bucket_head[key]` is the latest kept position in the
    # class, `prev_same[pos]` links to the previous kept position in the same class, `kept_flag`
    # tracks which positions are currently retained. Survivors are emitted in original index order,
    # so the output is BIT-IDENTICAL to the unbucketed reduce (validated: byte-identical caches).
    # Measured ~3.4x faster on median-size charts (the pool bulk); neutral on the heaviest charts
    # (whose cost is generation, not reduction). Cost: O(sum_class |class|^2) instead of O(F^2).
    kept_flag = np.zeros(n, dtype=np.bool_)
    prev_same = np.full(n, -1, dtype=np.int64)
    bucket_head = Dict.empty(_NUMBA_EXACT_OVERLAP_KEY_TYPE, types.int64)
    for idx in range(n):
        cf_lo, cf_hi, cg_lo, cg_hi, cbf, cbg, cbfg = surfaces[idx]
        key = (cbfg, cf_lo & cg_lo, cf_hi & cg_hi)
        head = bucket_head[key] if key in bucket_head else -1
        # phase 1: dominated by a currently-kept surface in the same class?
        dominated = False
        pos = head
        while pos != -1:
            if kept_flag[pos]:
                kf_lo, kf_hi, kg_lo, kg_hi, kbf, kbg, kbfg = surfaces[pos]
                # exact_overlap is guaranteed within a class; only directional conditions remain.
                if (
                    kbf >= cbf
                    and kbg <= cbg
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
                if (
                    cbf >= kbf
                    and cbg <= kbg
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
def _numba_branch_a_prefix_max_query_stamped(values, stamps, stamp: int, bfg: int, idx: int, width: int) -> int:
    best = -1
    base = int(bfg) * int(width)
    cursor = int(idx) + 1
    while cursor > 0:
        flat_idx = int(base) + int(cursor)
        if int(stamps[int(flat_idx)]) == int(stamp):
            value = int(values[int(flat_idx)])
            if int(value) > int(best):
                best = int(value)
        cursor -= cursor & -cursor
    return int(best)


@njit(cache=True, nogil=True)
def _numba_branch_a_prefix_max_update_stamped(
    values,
    stamps,
    stamp: int,
    bfg: int,
    idx: int,
    value: int,
    width: int,
) -> None:
    base = int(bfg) * int(width)
    cursor = int(idx) + 1
    while cursor < int(width):
        flat_idx = int(base) + int(cursor)
        if int(stamps[int(flat_idx)]) != int(stamp):
            stamps[int(flat_idx)] = int(stamp)
            values[int(flat_idx)] = int(value)
        elif int(value) > int(values[int(flat_idx)]):
            values[int(flat_idx)] = int(value)
        cursor += cursor & -cursor


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
    if int(bg) < 0 or int(bg) + 1 >= int(width) or int(bfg) < 0 or (int(bfg) + 1) * int(width) > len(values):
        raise ValueError("Branch-A FG response prefix reducer received an out-of-bounds body pair")
    prev = _numba_branch_a_prefix_max_query_stamped(
        values,
        stamps,
        int(stamp),
        int(bfg),
        int(bg),
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
    _numba_branch_a_prefix_max_update_stamped(
        values,
        stamps,
        int(stamp),
        int(bfg),
        int(bg),
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
    great_end_idx,
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
        int(timestamp_end_idx[int(real_time_idx), int(activation)]),
    )
    edge_e = int(perfect_e)
    fever_great_delta = 0
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

    tail_count = int(body_counts[int(edge_e)])
    if int(tail_count) <= 0:
        return
    fever_len = int(edge_e) - int(activation)
    tail_start = int(body_starts[int(edge_e)])
    packet = List.empty_list(_NUMBA_PACKET_POINT_TYPE)
    for tail_idx in range(int(tail_count)):
        value_idx = int(tail_start) + int(tail_idx)
        tail_fever, tail_great, tail_fever_great = body_values[int(value_idx)]
        tail_normal_great = int(tail_great) - int(tail_fever_great)
        shifted_normal_great = int(tail_normal_great) + (2 * int(activation)) + int(defect)
        packet_fever_great = int(tail_fever_great) + int(fever_great_delta)
        packet.append((
            np.int64(int(tail_fever) + int(fever_len)),
            np.int64(int(shifted_normal_great)),
            np.int64(int(packet_fever_great)),
        ))
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
    great_end_idx,
    real_time_idx: int,
) -> int:
    edge_e = int(timestamp_end_idx[int(real_time_idx), int(activation_idx)])
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
    great_candidate_timestamps,
    timestamp_end_idx,
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
            great_end_idx,
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
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    use_forced_great_timing_i: int,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
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
                        great_end_idx,
                        int(real_time_idx),
                    )
                    if int(late_e) > int(perfect_e):
                        edge_e = int(late_e)
                    else:
                        edge_e = -1
                if int(edge_e) >= 0:
                    candidate = int(_numba_body_count(int(activation), int(edge_e), int(n))) + int(best[int(edge_e)])
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
            great_end_idx,
            int(real_time_idx),
        )
        if int(edge_e) >= 0:
            candidate = int(_numba_body_count(int(first_fill[int(action_idx)]), int(edge_e), int(n))) + int(
                best[int(edge_e)]
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
            great_end_idx,
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
def _numba_packet_body_tails_from_precomputed_end_indices(
    n: int,
    action_count: int,
    later_fill,
    later_forced,
    later_activation_forced,
    reachable,
    use_forced_great_timing_i: int,
    timestamp_end_idx,
    great_end_idx,
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

    family_count, family_mode, family_defect, family_start, family_end = _numba_build_packet_families(
        int(action_count),
        later_fill,
        later_forced,
        later_activation_forced,
    )
    front_alpha_by_family = List.empty_list(_NUMBA_INT_LIST_TYPE)
    back_alpha_by_family = List.empty_list(_NUMBA_INT_LIST_TYPE)
    back_packet_by_family = List.empty_list(_NUMBA_PACKET_POINT_STACK_TYPE)
    front_aggregate_by_family = List.empty_list(_NUMBA_PACKET_POINT_STACK_TYPE)
    back_aggregate_by_family = List.empty_list(_NUMBA_PACKET_POINT_STACK_TYPE)
    for _family_idx in range(int(family_count)):
        front_alpha_by_family.append(List.empty_list(types.int64))
        back_alpha_by_family.append(List.empty_list(types.int64))
        back_packet_by_family.append(List.empty_list(_NUMBA_PACKET_POINT_LIST_TYPE))
        front_aggregate_by_family.append(List.empty_list(_NUMBA_PACKET_POINT_LIST_TYPE))
        back_aggregate_by_family.append(List.empty_list(_NUMBA_PACKET_POINT_LIST_TYPE))
    next_push_state_by_family = np.empty(int(family_count), dtype=np.int32)
    for family_idx in range(int(family_count)):
        next_push_state_by_family[int(family_idx)] = int(n) - 1

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
                front_alpha_by_family[int(family_idx)],
                front_aggregate_by_family[int(family_idx)],
                back_alpha_by_family[int(family_idx)],
                back_packet_by_family[int(family_idx)],
                back_aggregate_by_family[int(family_idx)],
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
                    timestamp_end_idx,
                    great_end_idx,
                    int(real_time_idx),
                    back_alpha_by_family[int(family_idx)],
                    back_packet_by_family[int(family_idx)],
                    back_aggregate_by_family[int(family_idx)],
                )
                push_state -= 1
            next_push_state_by_family[int(family_idx)] = int(state_i) - 1

        states_evaluated += 1
        touched_count = 0
        pair_stamp_value += 1
        for family_idx in range(int(family_count)):
            front_aggregate = front_aggregate_by_family[int(family_idx)]
            if len(front_aggregate) > 0:
                touched_count, generated_count = _numba_touch_packet_points_for_state(
                    front_aggregate[len(front_aggregate) - 1],
                    int(state_i),
                    int(pair_mod),
                    int(pair_stamp_value),
                    pair_stamp,
                    best_fever_by_pair,
                    touched_pair,
                    int(touched_count),
                )
                generated_surfaces += int(generated_count)
            back_aggregate = back_aggregate_by_family[int(family_idx)]
            if len(back_aggregate) > 0:
                touched_count, generated_count = _numba_touch_packet_points_for_state(
                    back_aggregate[len(back_aggregate) - 1],
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
    later_fill,
    first_fill,
    later_forced,
    first_forced,
    later_activation_forced,
    first_activation_forced,
    timestamps,
    great_candidate_timestamps,
    timestamp_end_idx,
    great_end_idx,
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
            later_activation_forced,
            first_activation_forced,
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
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
                great_candidate_timestamps,
                timestamp_end_idx,
                great_end_idx,
                int(real_time_idx),
            )
            if int(zero_body_fever) == int(max_body_fever):
                return _numba_single_body_frontier_row(int(zero_body_fever)), 0, 0, 1, 1

    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    for action_idx in range(int(action_count)):
        edge_e = _numba_first_edge_from_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_forced,
            int(use_forced_great_timing_i),
            timestamp_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if int(edge_e) >= 0:
            reachable[int(edge_e)] = True
        activation_e, _prefix_forced = _numba_first_activation_edge_from_precomputed(
            int(n),
            int(action_idx),
            first_fill,
            first_activation_forced,
            int(use_forced_great_timing_i),
            timestamp_end_idx,
            great_end_idx,
            int(real_time_idx),
        )
        if int(activation_e) >= 0 and int(activation_e) > int(edge_e):
            reachable[int(activation_e)] = True

    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        for action_idx in range(int(action_count)):
            edge_e = _numba_later_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                later_fill,
                later_forced,
                int(use_forced_great_timing_i),
                timestamp_end_idx,
                great_end_idx,
                int(real_time_idx),
            )
            if int(edge_e) >= 0:
                reachable[int(edge_e)] = True
            activation_e, _prefix_forced = _numba_later_activation_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                later_fill,
                later_activation_forced,
                int(use_forced_great_timing_i),
                timestamp_end_idx,
                great_end_idx,
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
        later_fill,
        later_forced,
        later_activation_forced,
        reachable,
        int(use_forced_great_timing_i),
        timestamp_end_idx,
        great_end_idx,
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
        generated_count = 0
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        for action_idx in range(int(action_count)):
            fill = int(later_fill[int(action_idx)])
            if int(fill) == int(prev_fill):
                edge_e = int(prev_edge_e)
            else:
                edge_e = _numba_later_edge_from_precomputed(
                    int(n),
                    int(state_i),
                    int(action_idx),
                    later_fill,
                    later_forced,
                    int(use_forced_great_timing_i),
                    timestamp_end_idx,
                    great_end_idx,
                    int(real_time_idx),
                )
            if int(edge_e) < 0:
                continue
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
                    generated_count += _numba_append_body_tail_array_surfaces(
                        generated,
                        edge,
                        body_values,
                        body_starts,
                        body_counts,
                        int(edge_e),
                    )
                elif int(edge_e) >= head_limit:
                    generated_count += _numba_append_terminal_tail_surface(generated, edge)
                else:
                    generated_count += _numba_append_surface_tail_surfaces(
                        generated, edge, head_frontiers[int(edge_e)]
                    )
            activation_e, prefix_forced = _numba_later_activation_edge_from_precomputed(
                int(n),
                int(state_i),
                int(action_idx),
                later_fill,
                later_activation_forced,
                int(use_forced_great_timing_i),
                timestamp_end_idx,
                great_end_idx,
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
                    generated_count += _numba_append_body_tail_array_surfaces(
                        generated,
                        activation_edge,
                        body_values,
                        body_starts,
                        body_counts,
                        int(activation_e),
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
        first_edge_e_by_action = np.empty(int(action_count), dtype=np.int32)
        first_normal_head_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_e_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_prefix_by_action = np.empty(int(action_count), dtype=np.int32)
        first_activation_head_by_action = np.empty(int(action_count), dtype=np.int32)
        for action_idx in range(int(action_count)):
            edge_e = _numba_first_edge_from_precomputed(
                int(n),
                int(action_idx),
                first_fill,
                first_forced,
                int(use_forced_great_timing_i),
                timestamp_end_idx,
                great_end_idx,
                int(real_time_idx),
            )
            first_edge_e_by_action[int(action_idx)] = int(edge_e)
            first_normal_head_by_action[int(action_idx)] = min(100, max(0, int(first_forced[int(action_idx)])))
            activation_e, prefix_forced = _numba_first_activation_edge_from_precomputed(
                int(n),
                int(action_idx),
                first_fill,
                first_activation_forced,
                int(use_forced_great_timing_i),
                timestamp_end_idx,
                great_end_idx,
                int(real_time_idx),
            )
            first_activation_e_by_action[int(action_idx)] = int(activation_e)
            first_activation_prefix_by_action[int(action_idx)] = int(prefix_forced)
            first_activation_head_by_action[int(action_idx)] = min(100, max(0, int(prefix_forced)))
        branch_a_width = int(n) + 2
        branch_a_size = int(pair_mod) * int(branch_a_width)
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
            prev_activation_fill = -1
            prev_activation_e = -1
            for bucket_idx in range(
                int(normal_bucket_offsets[int(head_great_count)]),
                int(normal_bucket_offsets[int(head_great_count) + 1]),
            ):
                action_idx = int(normal_actions_by_head[int(bucket_idx)])
                edge_e = int(first_edge_e_by_action[int(action_idx)])
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
            for bucket_idx in range(
                int(activation_bucket_offsets[int(head_great_count)]),
                int(activation_bucket_offsets[int(head_great_count) + 1]),
            ):
                action_idx = int(activation_actions_by_head[int(bucket_idx)])
                edge_e = int(first_edge_e_by_action[int(action_idx)])
                activation_e = int(first_activation_e_by_action[int(action_idx)])
                fill = int(first_fill[int(action_idx)])
                if int(fill) == int(prev_activation_fill) and int(activation_e) == int(prev_activation_e):
                    continue
                prev_activation_fill = int(fill)
                prev_activation_e = int(activation_e)
                prefix_forced = int(first_activation_prefix_by_action[int(action_idx)])
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
    else:
        first_generated = List.empty_list(_NUMBA_SURFACE_TYPE)
        prev_fill = -1
        prev_edge_e = -1
        prev_activation_fill = -1
        prev_activation_e = -1
        for action_idx in range(int(action_count)):
            edge_e = _numba_first_edge_from_precomputed(
                int(n),
                int(action_idx),
                first_fill,
                first_forced,
                int(use_forced_great_timing_i),
                timestamp_end_idx,
                great_end_idx,
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
                    first_generated_count += _numba_append_body_tail_array_surfaces(
                        first_generated,
                        edge,
                        body_values,
                        body_starts,
                        body_counts,
                        int(edge_e),
                    )
                elif int(edge_e) >= head_limit:
                    first_generated_count += _numba_append_terminal_tail_surface(first_generated, edge)
                else:
                    first_generated_count += _numba_append_surface_tail_surfaces(
                        first_generated,
                        edge,
                        head_frontiers[int(edge_e)],
                    )
            activation_e, prefix_forced = _numba_first_activation_edge_from_precomputed(
                int(n),
                int(action_idx),
                first_fill,
                first_activation_forced,
                int(use_forced_great_timing_i),
                timestamp_end_idx,
                great_end_idx,
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
                    first_generated_count += _numba_append_body_tail_array_surfaces(
                        first_generated,
                        activation_edge,
                        body_values,
                        body_starts,
                        body_counts,
                        int(activation_e),
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
