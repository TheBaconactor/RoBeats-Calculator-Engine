import time
from concurrent.futures import ThreadPoolExecutor
from os import cpu_count
from typing import Any

import numpy as np
import taichi as ti
from numba import njit, types
from numba.typed import List

from gear_optimizer.solver.taichi_gem.runtime import init_taichi

from .response_builder import _action_table
from .response_types import FgResponseFrontierResult, FgResponseSurface, _EMPTY_SURFACE

_GPU_EDGE_BATCH_MAX_BYTES = 4 * 1024 * 1024 * 1024
_FIRST_FRONTIER_REDUCER_THREADS = max(1, int(cpu_count() or 1))
_PackedSurface = tuple[int, int, int, int]
_NUMBA_SURFACE_TYPE = types.UniTuple(types.uint64, 6)
_NUMBA_SURFACE_LIST_TYPE = types.ListType(_NUMBA_SURFACE_TYPE)
_NUMBA_BODY_PAIR_TYPE = types.UniTuple(types.uint64, 2)
_NUMBA_BODY_PAIR_LIST_TYPE = types.ListType(_NUMBA_BODY_PAIR_TYPE)


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
def _numba_zero_forced_body_fever(
    n: int,
    later_next,
    later_fill,
    first_next,
    first_fill,
) -> int:
    if int(first_fill[0]) < 100:
        return -1
    edge_e = int(first_next[0])
    if edge_e < 0:
        return -1
    total = int(_numba_body_count(int(first_fill[0]), edge_e, int(n)))
    state_i = edge_e
    for _step in range(int(n) + 1):
        if state_i >= int(n):
            return total
        next_i = int(later_next[state_i, 0])
        if next_i < 0 or next_i <= state_i:
            return -1
        total += int(_numba_body_count(state_i + int(later_fill[0]), next_i, int(n)))
        state_i = next_i
    return -1


@njit(cache=True, nogil=True)
def _numba_max_body_fever(
    n: int,
    action_count: int,
    later_next,
    later_fill,
    first_next,
    first_fill,
) -> int:
    reachable = np.zeros(int(n) + 1, dtype=np.bool_)
    reachable[int(n)] = True
    for action_idx in range(int(action_count)):
        if int(first_fill[action_idx]) >= int(n):
            break
        edge_e = int(first_next[action_idx])
        if edge_e >= 0:
            reachable[edge_e] = True
    for state_i in range(int(n)):
        if not reachable[state_i]:
            continue
        for action_idx in range(int(action_count)):
            if state_i + int(later_fill[action_idx]) >= int(n):
                break
            edge_e = int(later_next[state_i, action_idx])
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
            edge_e = int(later_next[state_i, action_idx])
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
        edge_e = int(first_next[action_idx])
        if edge_e < 0:
            continue
        fever_count = int(_numba_body_count(int(first_fill[action_idx]), edge_e, int(n)))
        candidate = fever_count + int(best[edge_e])
        if candidate > best_first:
            best_first = candidate
    return best_first


@njit(cache=True, nogil=True)
def _numba_single_body_frontier_row(body_fever: int):
    out = np.zeros((1, 6), dtype=np.uint64)
    out[0, 4] = np.uint64(body_fever)
    return out


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
) -> int:
    forced_end = int(forced_start) + int(forced_applied) - 1
    start_time = timestamps[int(activation_idx)]
    e = int(timestamp_end_idx[int(activation_idx)])
    if (
        int(use_forced_great_timing_i) != 0
        and int(forced_applied) > 0
        and int(forced_end) >= int(forced_start)
        and int(forced_end) < int(activation_idx)
        and int(forced_end) < int(n)
    ):
        forced_t = great_candidate_timestamps[int(forced_end)]
        if forced_t > start_time:
            e = int(great_end_idx[int(forced_end)])
    if e <= int(activation_idx):
        e = int(activation_idx) + 1
    if e > int(n):
        e = int(n)
    return int(e)


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
) -> int:
    fill = int(later_fill[int(action_idx)])
    activation = int(state_i) + fill
    if activation >= int(n):
        return -1
    edge_e = _numba_edge_end_idx_precomputed(
        int(n),
        int(activation),
        int(state_i) + 1,
        int(later_forced[int(action_idx)]),
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
    )
    if int(action_idx) > 0 and fill == int(later_fill[int(action_idx) - 1]):
        prev_e = _numba_edge_end_idx_precomputed(
            int(n),
            int(state_i) + int(later_fill[int(action_idx) - 1]),
            int(state_i) + 1,
            int(later_forced[int(action_idx) - 1]),
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
        )
        if edge_e == prev_e:
            return -1
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
) -> int:
    fill = int(first_fill[int(action_idx)])
    if fill >= int(n):
        return -1
    edge_e = _numba_edge_end_idx_precomputed(
        int(n),
        fill,
        0,
        int(first_forced[int(action_idx)]),
        int(use_forced_great_timing_i),
        timestamps,
        great_candidate_timestamps,
        timestamp_end_idx,
        great_end_idx,
    )
    if int(action_idx) > 0 and fill == int(first_fill[int(action_idx) - 1]):
        prev_e = _numba_edge_end_idx_precomputed(
            int(n),
            int(first_fill[int(action_idx) - 1]),
            0,
            int(first_forced[int(action_idx) - 1]),
            int(use_forced_great_timing_i),
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
        )
        if edge_e == prev_e:
            return -1
    return int(edge_e)


@njit(cache=True, nogil=True)
def _first_frontier_from_body_tail_next_arrays_numba(
    n: int,
    action_count: int,
    later_next,
    later_fill,
    later_forced,
    first_next,
    first_fill,
    first_forced,
):
    zero_body_fever = _numba_zero_forced_body_fever(
        int(n),
        later_next,
        later_fill,
        first_next,
        first_fill,
    )
    if zero_body_fever >= 0:
        max_body_fever = _numba_max_body_fever(
            int(n),
            int(action_count),
            later_next,
            later_fill,
            first_next,
            first_fill,
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
        edge_e = int(first_next[action_idx])
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
            edge_e = int(later_next[state_i, action_idx])
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
            edge_e = int(later_next[state_i, action_idx])
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
def _first_frontier_from_next_arrays_numba(
    n: int,
    action_count: int,
    later_next,
    later_fill,
    later_forced,
    first_next,
    first_fill,
    first_forced,
):
    if int(first_fill[0]) >= 100:
        return _first_frontier_from_body_tail_next_arrays_numba(
            int(n),
            int(action_count),
            later_next,
            later_fill,
            later_forced,
            first_next,
            first_fill,
            first_forced,
        )

    reachable = np.zeros(n + 1, dtype=np.bool_)
    reachable[n] = True
    state_frontiers = List.empty_list(_NUMBA_SURFACE_LIST_TYPE)
    for _idx in range(n + 1):
        state_frontiers.append(List.empty_list(_NUMBA_SURFACE_TYPE))
    state_frontiers[n] = _numba_frontier_with_empty_surface()

    first_edges_e = List.empty_list(types.int64)
    first_edges_surface = List.empty_list(_NUMBA_SURFACE_TYPE)
    for action_idx in range(action_count):
        if int(first_fill[action_idx]) >= int(n):
            break
        edge_e = int(first_next[action_idx])
        if edge_e < 0:
            continue
        forced = int(first_forced[action_idx])
        edge_surface = _numba_pack_edge(
            int(n),
            int(first_fill[action_idx]),
            edge_e,
            0,
            min(int(n), forced),
        )
        first_edges_e.append(edge_e)
        first_edges_surface.append(edge_surface)
        reachable[edge_e] = True

    for state_i in range(n):
        if not reachable[state_i]:
            continue
        for action_idx in range(action_count):
            if state_i + int(later_fill[action_idx]) >= int(n):
                break
            edge_e = int(later_next[state_i, action_idx])
            if edge_e >= 0:
                reachable[edge_e] = True

    states_evaluated = 0
    retained_total = 1
    max_state_frontier = 1
    generated_surfaces = 0
    for state_i in range(n - 1, -1, -1):
        if not reachable[state_i]:
            continue
        states_evaluated += 1
        frontier = List.empty_list(_NUMBA_SURFACE_TYPE)
        generated_count = 0
        for action_idx in range(action_count):
            if state_i + int(later_fill[action_idx]) >= int(n):
                break
            edge_e = int(later_next[state_i, action_idx])
            if edge_e < 0:
                continue
            tail_frontier = state_frontiers[edge_e]
            if len(tail_frontier) == 0:
                continue
            forced = int(later_forced[action_idx])
            forced_start = state_i + 1
            edge_surface = _numba_pack_edge(
                int(n),
                state_i + int(later_fill[action_idx]),
                edge_e,
                forced_start,
                min(int(n), forced_start + forced),
            )
            for tail_idx in range(len(tail_frontier)):
                generated_count += 1
                _numba_append_surface(frontier, _numba_combine(edge_surface, tail_frontier[tail_idx]))
        generated_surfaces += generated_count
        if generated_count == 0:
            frontier = _numba_frontier_with_empty_surface()
        state_frontiers[state_i] = frontier
        retained_total += len(frontier)
        if len(frontier) > max_state_frontier:
            max_state_frontier = len(frontier)

    first_frontier = List.empty_list(_NUMBA_SURFACE_TYPE)
    first_generated_count = 0
    for idx in range(len(first_edges_e)):
        edge_e = first_edges_e[idx]
        tail_frontier = state_frontiers[edge_e]
        for tail_idx in range(len(tail_frontier)):
            first_generated_count += 1
            _numba_append_surface(first_frontier, _numba_combine(first_edges_surface[idx], tail_frontier[tail_idx]))
    generated_surfaces += first_generated_count
    if first_generated_count == 0:
        first_frontier = _numba_frontier_with_empty_surface()
    retained_total += len(first_frontier)
    if len(first_frontier) > max_state_frontier:
        max_state_frontier = len(first_frontier)

    out = np.zeros((len(first_frontier), 6), dtype=np.uint64)
    for idx in range(len(first_frontier)):
        surface = first_frontier[idx]
        for col in range(6):
            out[idx, col] = surface[col]
    return out, states_evaluated, generated_surfaces, retained_total, max_state_frontier


@ti.func
def _lower_bound_ts(ts: ti.template(), n, value):
    lo = ti.i32(0)
    hi = n
    while lo < hi:
        mid = (lo + hi) // 2
        if ts[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return lo


@ti.func
def _edge_end_idx(
    n,
    activation_idx,
    forced_start,
    forced_applied,
    real_fever_time,
    use_forced_great_timing_i,
    timestamps: ti.template(),
    great_candidate_timestamps: ti.template(),
):
    forced_end = forced_start + forced_applied - 1
    start_time = timestamps[activation_idx]
    if (
        use_forced_great_timing_i != 0
        and forced_applied > 0
        and forced_end >= forced_start
        and forced_end < activation_idx
        and forced_end < n
    ):
        forced_t = great_candidate_timestamps[forced_end]
        if forced_t > start_time:
            start_time = forced_t
    e = _lower_bound_ts(timestamps, n, ti.cast(start_time + real_fever_time, ti.f32))
    if e <= activation_idx:
        e = activation_idx + 1
    if e > n:
        e = n
    return e, start_time


@ti.func
def _edge_end_idx_precomputed(
    n,
    activation_idx,
    forced_start,
    forced_applied,
    use_forced_great_timing_i,
    timestamps: ti.template(),
    great_candidate_timestamps: ti.template(),
    timestamp_end_idx: ti.template(),
    great_end_idx: ti.template(),
    real_time_idx,
):
    forced_end = forced_start + forced_applied - 1
    start_time = timestamps[activation_idx]
    e = timestamp_end_idx[real_time_idx, activation_idx]
    if (
        use_forced_great_timing_i != 0
        and forced_applied > 0
        and forced_end >= forced_start
        and forced_end < activation_idx
        and forced_end < n
    ):
        forced_t = great_candidate_timestamps[forced_end]
        if forced_t > start_time:
            start_time = forced_t
            e = great_end_idx[real_time_idx, forced_end]
    if e <= activation_idx:
        e = activation_idx + 1
    if e > n:
        e = n
    return e, start_time


@ti.func
def _mask_word(start, end, n, word_idx):
    start_i = ti.max(ti.i32(0), ti.min(ti.min(start, n), ti.i32(100)))
    end_i = ti.max(ti.i32(0), ti.min(ti.min(end, n), ti.i32(100)))
    out = ti.u32(0)
    lo = word_idx * 32
    hi = ti.min(lo + 32, ti.i32(100))
    a = ti.max(start_i, lo)
    b = ti.min(end_i, hi)
    if b > a:
        width = b - a
        out = ti.cast((ti.u64(1) << width) - ti.u64(1), ti.u32) << (a - lo)
    return out


@ti.func
def _body_count(start, end, n):
    return ti.max(ti.i32(0), ti.min(end, n) - ti.max(start, ti.i32(100)))


@ti.func
def _write_edge(
    n,
    row,
    action_idx,
    state_i,
    first_i,
    fill,
    forced_applied,
    real_fever_time,
    use_forced_great_timing_i,
    timestamps: ti.template(),
    great_candidate_timestamps: ti.template(),
    valid: ti.template(),
    next_idx: ti.template(),
    fever_masks: ti.template(),
    great_masks: ti.template(),
    body_counts: ti.template(),
):
    activation = fill
    forced_start = ti.i32(0)
    if first_i == 0:
        activation = state_i + fill
        forced_start = state_i + 1

    edge_e = ti.i32(-1)
    start_time = ti.f32(-1.0)
    if activation < n:
        e, computed_start = _edge_end_idx(
            n,
            activation,
            forced_start,
            forced_applied,
            real_fever_time,
            use_forced_great_timing_i,
            timestamps,
            great_candidate_timestamps,
        )
        edge_e = e
        start_time = computed_start
        valid[row, action_idx] = ti.i8(1)
        next_idx[row, action_idx] = e
        great_end = ti.min(n, forced_start + forced_applied)
        for word in ti.static(range(4)):
            fever_masks[row, action_idx, word] = _mask_word(activation, e, n, word)
            great_masks[row, action_idx, word] = _mask_word(forced_start, great_end, n, word)
        body_counts[row, action_idx, 0] = _body_count(activation, e, n)
        body_counts[row, action_idx, 1] = _body_count(forced_start, great_end, n)
    return edge_e, start_time


@ti.kernel
def _build_fg_response_edges_kernel(
    n: ti.i32,
    action_count: ti.i32,
    real_fever_time: ti.f32,
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_valid: ti.types.ndarray(dtype=ti.i8, ndim=2),
    later_next: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    later_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    later_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=3),
    first_valid: ti.types.ndarray(dtype=ti.i8, ndim=2),
    first_next: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=3),
):
    for state_i, action_idx in ti.ndrange(n, action_count):
        fill = later_fill[action_idx]
        forced = later_forced[action_idx]
        e, start_time = _write_edge(
            n,
            state_i,
            action_idx,
            state_i,
            ti.i32(0),
            fill,
            forced,
            real_fever_time,
            use_forced_great_timing_i,
            timestamps,
            great_candidate_timestamps,
            later_valid,
            later_next,
            later_fever_masks,
            later_great_masks,
            later_body_counts,
        )
        if action_idx > 0 and later_valid[state_i, action_idx] != 0:
            prev_fill = later_fill[action_idx - 1]
            if fill == prev_fill:
                prev_e, prev_start_time = _edge_end_idx(
                    n,
                    state_i + prev_fill,
                    state_i + 1,
                    later_forced[action_idx - 1],
                    real_fever_time,
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                )
                if start_time == prev_start_time or e == prev_e:
                    later_valid[state_i, action_idx] = ti.i8(0)

    for action_idx in range(action_count):
        fill = first_fill[action_idx]
        forced = first_forced[action_idx]
        e, start_time = _write_edge(
            n,
            ti.i32(0),
            action_idx,
            ti.i32(0),
            ti.i32(1),
            fill,
            forced,
            real_fever_time,
            use_forced_great_timing_i,
            timestamps,
            great_candidate_timestamps,
            first_valid,
            first_next,
            first_fever_masks,
            first_great_masks,
            first_body_counts,
        )
        if action_idx > 0 and first_valid[0, action_idx] != 0:
            prev_fill = first_fill[action_idx - 1]
            if fill == prev_fill:
                prev_e, prev_start_time = _edge_end_idx(
                    n,
                    prev_fill,
                    ti.i32(0),
                    first_forced[action_idx - 1],
                    real_fever_time,
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                )
                if start_time == prev_start_time or e == prev_e:
                    first_valid[0, action_idx] = ti.i8(0)


@ti.kernel
def _build_fg_response_edges_batch_kernel(
    n: ti.i32,
    geometry_count: ti.i32,
    max_action_count: ti.i32,
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    real_time_index: ti.types.ndarray(dtype=ti.i32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    action_count_by_geometry: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_forced: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_valid: ti.types.ndarray(dtype=ti.i8, ndim=3),
    later_next: ti.types.ndarray(dtype=ti.i32, ndim=3),
    later_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=4),
    later_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=4),
    later_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=4),
    first_valid: ti.types.ndarray(dtype=ti.i8, ndim=2),
    first_next: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fever_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_great_masks: ti.types.ndarray(dtype=ti.u32, ndim=3),
    first_body_counts: ti.types.ndarray(dtype=ti.i32, ndim=3),
):
    for geometry_idx, state_i, action_idx in ti.ndrange(geometry_count, n, max_action_count):
        if action_idx < action_count_by_geometry[geometry_idx]:
            rt_idx = real_time_index[geometry_idx]
            fill = later_fill[geometry_idx, action_idx]
            forced = later_forced[geometry_idx, action_idx]
            activation = state_i + fill
            forced_start = state_i + 1
            edge_e = ti.i32(-1)
            start_time = ti.f32(-1.0)
            if activation < n:
                e, computed_start = _edge_end_idx_precomputed(
                    n,
                    activation,
                    forced_start,
                    forced,
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                    timestamp_end_idx,
                    great_end_idx,
                    rt_idx,
                )
                edge_e = e
                start_time = computed_start
                later_valid[geometry_idx, state_i, action_idx] = ti.i8(1)
                later_next[geometry_idx, state_i, action_idx] = e
                great_end = ti.min(n, forced_start + forced)
                for word in ti.static(range(4)):
                    later_fever_masks[geometry_idx, state_i, action_idx, word] = _mask_word(activation, e, n, word)
                    later_great_masks[geometry_idx, state_i, action_idx, word] = _mask_word(
                        forced_start, great_end, n, word
                    )
                later_body_counts[geometry_idx, state_i, action_idx, 0] = _body_count(activation, e, n)
                later_body_counts[geometry_idx, state_i, action_idx, 1] = _body_count(forced_start, great_end, n)

            if action_idx > 0 and later_valid[geometry_idx, state_i, action_idx] != 0:
                prev_fill = later_fill[geometry_idx, action_idx - 1]
                if fill == prev_fill:
                    prev_e, prev_start_time = _edge_end_idx_precomputed(
                        n,
                        state_i + prev_fill,
                        state_i + 1,
                        later_forced[geometry_idx, action_idx - 1],
                        use_forced_great_timing_i,
                        timestamps,
                        great_candidate_timestamps,
                        timestamp_end_idx,
                        great_end_idx,
                        rt_idx,
                    )
                    if start_time == prev_start_time or edge_e == prev_e:
                        later_valid[geometry_idx, state_i, action_idx] = ti.i8(0)

    for geometry_idx, action_idx in ti.ndrange(geometry_count, max_action_count):
        if action_idx < action_count_by_geometry[geometry_idx]:
            rt_idx = real_time_index[geometry_idx]
            fill = first_fill[geometry_idx, action_idx]
            forced = first_forced[geometry_idx, action_idx]
            activation = fill
            edge_e = ti.i32(-1)
            start_time = ti.f32(-1.0)
            if activation < n:
                e, computed_start = _edge_end_idx_precomputed(
                    n,
                    activation,
                    ti.i32(0),
                    forced,
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                    timestamp_end_idx,
                    great_end_idx,
                    rt_idx,
                )
                edge_e = e
                start_time = computed_start
                first_valid[geometry_idx, action_idx] = ti.i8(1)
                first_next[geometry_idx, action_idx] = e
                great_end = ti.min(n, forced)
                for word in ti.static(range(4)):
                    first_fever_masks[geometry_idx, action_idx, word] = _mask_word(activation, e, n, word)
                    first_great_masks[geometry_idx, action_idx, word] = _mask_word(0, great_end, n, word)
                first_body_counts[geometry_idx, action_idx, 0] = _body_count(activation, e, n)
                first_body_counts[geometry_idx, action_idx, 1] = _body_count(0, great_end, n)

            if action_idx > 0 and first_valid[geometry_idx, action_idx] != 0:
                prev_fill = first_fill[geometry_idx, action_idx - 1]
                if fill == prev_fill:
                    prev_e, prev_start_time = _edge_end_idx_precomputed(
                        n,
                        prev_fill,
                        ti.i32(0),
                        first_forced[geometry_idx, action_idx - 1],
                        use_forced_great_timing_i,
                        timestamps,
                        great_candidate_timestamps,
                        timestamp_end_idx,
                        great_end_idx,
                        rt_idx,
                    )
                    if start_time == prev_start_time or edge_e == prev_e:
                        first_valid[geometry_idx, action_idx] = ti.i8(0)


@ti.kernel
def _build_fg_response_next_batch_kernel(
    n: ti.i32,
    geometry_count: ti.i32,
    max_action_count: ti.i32,
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    real_time_index: ti.types.ndarray(dtype=ti.i32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    action_count_by_geometry: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_forced: ti.types.ndarray(dtype=ti.i32, ndim=2),
    first_forced: ti.types.ndarray(dtype=ti.i32, ndim=2),
    later_next: ti.types.ndarray(dtype=ti.i32, ndim=3),
    first_next: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    for geometry_idx, state_i, action_idx in ti.ndrange(geometry_count, n, max_action_count):
        if action_idx < action_count_by_geometry[geometry_idx]:
            rt_idx = real_time_index[geometry_idx]
            fill = later_fill[geometry_idx, action_idx]
            activation = state_i + fill
            edge_e = ti.i32(-1)
            start_time = ti.f32(-1.0)
            if activation < n:
                e, computed_start = _edge_end_idx_precomputed(
                    n,
                    activation,
                    state_i + 1,
                    later_forced[geometry_idx, action_idx],
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                    timestamp_end_idx,
                    great_end_idx,
                    rt_idx,
                )
                edge_e = e
                start_time = computed_start

            if edge_e >= 0 and action_idx > 0:
                prev_fill = later_fill[geometry_idx, action_idx - 1]
                if fill == prev_fill:
                    prev_e, prev_start_time = _edge_end_idx_precomputed(
                        n,
                        state_i + prev_fill,
                        state_i + 1,
                        later_forced[geometry_idx, action_idx - 1],
                        use_forced_great_timing_i,
                        timestamps,
                        great_candidate_timestamps,
                        timestamp_end_idx,
                        great_end_idx,
                        rt_idx,
                    )
                    if start_time == prev_start_time or edge_e == prev_e:
                        edge_e = ti.i32(-1)
            later_next[geometry_idx, state_i, action_idx] = edge_e

    for geometry_idx, action_idx in ti.ndrange(geometry_count, max_action_count):
        if action_idx < action_count_by_geometry[geometry_idx]:
            rt_idx = real_time_index[geometry_idx]
            fill = first_fill[geometry_idx, action_idx]
            edge_e = ti.i32(-1)
            start_time = ti.f32(-1.0)
            if fill < n:
                e, computed_start = _edge_end_idx_precomputed(
                    n,
                    fill,
                    ti.i32(0),
                    first_forced[geometry_idx, action_idx],
                    use_forced_great_timing_i,
                    timestamps,
                    great_candidate_timestamps,
                    timestamp_end_idx,
                    great_end_idx,
                    rt_idx,
                )
                edge_e = e
                start_time = computed_start

            if edge_e >= 0 and action_idx > 0:
                prev_fill = first_fill[geometry_idx, action_idx - 1]
                if fill == prev_fill:
                    prev_e, prev_start_time = _edge_end_idx_precomputed(
                        n,
                        prev_fill,
                        ti.i32(0),
                        first_forced[geometry_idx, action_idx - 1],
                        use_forced_great_timing_i,
                        timestamps,
                        great_candidate_timestamps,
                        timestamp_end_idx,
                        great_end_idx,
                        rt_idx,
                    )
                    if start_time == prev_start_time or edge_e == prev_e:
                        edge_e = ti.i32(-1)
            first_next[geometry_idx, action_idx] = edge_e


def _pack_words(row: np.ndarray) -> int:
    return int(row[0]) | (int(row[1]) << 32) | (int(row[2]) << 64) | (int(row[3]) << 96)


def _unpack_surface(surface: _PackedSurface) -> FgResponseSurface:
    fever, great, body_fever, body_great = surface
    return FgResponseSurface(
        int(fever) & 0xFFFFFFFF,
        (int(fever) >> 32) & 0xFFFFFFFF,
        (int(fever) >> 64) & 0xFFFFFFFF,
        (int(fever) >> 96) & 0xFFFFFFFF,
        int(great) & 0xFFFFFFFF,
        (int(great) >> 32) & 0xFFFFFFFF,
        (int(great) >> 64) & 0xFFFFFFFF,
        (int(great) >> 96) & 0xFFFFFFFF,
        int(body_fever),
        int(body_great),
    )


def _surface_from_numba_row(row: np.ndarray) -> FgResponseSurface:
    fever_lo = int(row[0])
    fever_hi = int(row[1])
    great_lo = int(row[2])
    great_hi = int(row[3])
    return FgResponseSurface(
        fever_lo & 0xFFFFFFFF,
        (fever_lo >> 32) & 0xFFFFFFFF,
        fever_hi & 0xFFFFFFFF,
        (fever_hi >> 32) & 0xFFFFFFFF,
        great_lo & 0xFFFFFFFF,
        (great_lo >> 32) & 0xFFFFFFFF,
        great_hi & 0xFFFFFFFF,
        (great_hi >> 32) & 0xFFFFFFFF,
        int(row[4]),
        int(row[5]),
    )


def _combine_packed(edge: _PackedSurface, tail: _PackedSurface) -> _PackedSurface:
    return (
        int(edge[0]) | int(tail[0]),
        int(edge[1]) | int(tail[1]),
        int(edge[2]) + int(tail[2]),
        int(edge[3]) + int(tail[3]),
    )


def _append_packed_surface(bucket: list[_PackedSurface], surface: _PackedSurface) -> bool:
    cf, cg, cbf, cbg = surface
    for kept_surface in bucket:
        kf, kg, kbf, kbg = kept_surface
        if kbf >= cbf and kbg <= cbg and (cf & ~kf) == 0 and (kg & ~cg) == 0:
            return False
    write = 0
    for kept_surface in bucket:
        kf, kg, kbf, kbg = kept_surface
        if not (cbf >= kbf and cbg <= kbg and (kf & ~cf) == 0 and (cg & ~kg) == 0):
            bucket[write] = kept_surface
            write += 1
    del bucket[write:]
    bucket.append(surface)
    return True


def _reduce_packed_frontier(surfaces: list[_PackedSurface]) -> tuple[_PackedSurface, ...]:
    if not surfaces:
        return ((0, 0, 0, 0),)
    if len(surfaces) > 8:
        surfaces.sort(key=lambda surface: (-int(surface[2]), int(surface[3])))
    kept: list[_PackedSurface] = []
    seen: set[_PackedSurface] = set()
    for surface in surfaces:
        if surface in seen:
            continue
        seen.add(surface)
        _append_packed_surface(kept, surface)
    return tuple(kept)


def _append_edge_from_arrays(
    bucket: list[_PackedSurface],
    fever_masks: np.ndarray,
    great_masks: np.ndarray,
    body_counts: np.ndarray,
    row: int,
    action_idx: int,
) -> bool:
    surface = (
        int(fever_masks[row, action_idx, 0])
        | (int(fever_masks[row, action_idx, 1]) << 32)
        | (int(fever_masks[row, action_idx, 2]) << 64)
        | (int(fever_masks[row, action_idx, 3]) << 96),
        int(great_masks[row, action_idx, 0])
        | (int(great_masks[row, action_idx, 1]) << 32)
        | (int(great_masks[row, action_idx, 2]) << 64)
        | (int(great_masks[row, action_idx, 3]) << 96),
        int(body_counts[row, action_idx, 0]),
        int(body_counts[row, action_idx, 1]),
    )
    return _append_packed_surface(bucket, surface)


def _frontier_from_edge_arrays(
    *,
    n: int,
    action_count: int,
    non_fever_base: int,
    later_valid: np.ndarray,
    later_next: np.ndarray,
    later_fever_masks: np.ndarray,
    later_great_masks: np.ndarray,
    later_body_counts: np.ndarray,
    first_valid: np.ndarray,
    first_next: np.ndarray,
    first_fever_masks: np.ndarray,
    first_great_masks: np.ndarray,
    first_body_counts: np.ndarray,
    seconds: float,
    include_state_frontiers: bool = True,
) -> FgResponseFrontierResult:
    reachable = np.zeros((n + 1,), dtype=np.bool_)
    reachable[n] = True
    empty_surface: _PackedSurface = (0, 0, 0, 0)
    state_frontiers: dict[int, tuple[_PackedSurface, ...]] = {n: (empty_surface,)}
    transitions = 0
    generated_surfaces = 0
    retained_total = 1
    max_state_frontier = 1

    first_edge_buckets: dict[int, list[_PackedSurface]] = {}
    for action_idx in range(action_count):
        if int(first_valid[0, action_idx]) == 0:
            continue
        e = int(first_next[0, action_idx])
        _append_edge_from_arrays(
            first_edge_buckets.setdefault(e, []),
            first_fever_masks,
            first_great_masks,
            first_body_counts,
            0,
            action_idx,
        )
    first_edges = [(int(e), surface) for e, bucket in first_edge_buckets.items() for surface in bucket]
    transitions += len(first_edges)
    for e, _edge in first_edges:
        reachable[int(e)] = True

    later_edges_by_state: dict[int, list[tuple[int, _PackedSurface]]] = {}
    for i in range(n):
        if not bool(reachable[i]):
            continue
        edge_buckets: dict[int, list[_PackedSurface]] = {}
        for action_idx in range(action_count):
            if int(later_valid[i, action_idx]) == 0:
                continue
            e = int(later_next[i, action_idx])
            _append_edge_from_arrays(
                edge_buckets.setdefault(e, []),
                later_fever_masks,
                later_great_masks,
                later_body_counts,
                i,
                action_idx,
            )
        edges = [(int(e), surface) for e, bucket in edge_buckets.items() for surface in bucket]
        transitions += len(edges)
        later_edges_by_state[int(i)] = edges
        for e, _edge in edges:
            reachable[int(e)] = True

    for i in range(n - 1, -1, -1):
        if not bool(reachable[i]):
            continue
        generated: list[_PackedSurface] = []
        for e, edge in later_edges_by_state.get(int(i), []):
            tail_frontier = state_frontiers.get(int(e))
            if tail_frontier is None:
                raise ValueError(f"missing tail frontier for reachable state {e}")
            for tail in tail_frontier:
                generated.append(_combine_packed(edge, tail))
        generated_surfaces += len(generated)
        frontier = _reduce_packed_frontier(generated)
        state_frontiers[int(i)] = frontier
        retained_total += len(frontier)
        max_state_frontier = max(max_state_frontier, len(frontier))

    first_generated: list[_PackedSurface] = []
    for e, edge in first_edges:
        tail_frontier = state_frontiers.get(int(e))
        if tail_frontier is None:
            raise ValueError(f"missing first-tail frontier for reachable state {e}")
        for tail in tail_frontier:
            first_generated.append(_combine_packed(edge, tail))
    generated_surfaces += len(first_generated)
    first_frontier = _reduce_packed_frontier(first_generated)
    retained_total += len(first_frontier)
    max_state_frontier = max(max_state_frontier, len(first_frontier))

    return FgResponseFrontierResult(
        first_frontier=tuple(_unpack_surface(surface) for surface in first_frontier),
        state_frontiers={
            int(state): tuple(_unpack_surface(surface) for surface in frontier)
            for state, frontier in state_frontiers.items()
        }
        if bool(include_state_frontiers)
        else {},
        states_evaluated=int(np.count_nonzero(reachable[:n])),
        actions=int(action_count),
        transitions_evaluated=int(transitions),
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=max(0, int(non_fever_base)),
        seconds=float(seconds),
    )


def build_force_greats_response_frontier_gpu(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
    use_forced_great_timing: bool = True,
    include_state_frontiers: bool = True,
) -> FgResponseFrontierResult:
    init_taichi()
    started = time.perf_counter()
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    if n <= 0:
        return FgResponseFrontierResult((_EMPTY_SURFACE,), {}, 0, 0, 0, 0, 1, 1, 0, 0.0)
    if bool(np.any(ts[1:] < ts[:-1])):
        raise ValueError("timestamps must be sorted in nondecreasing order")
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")

    actions, later_fill, first_fill, later_forced, first_forced = _action_table(
        raw_fever_fill=float(raw_fever_fill),
        non_fever_base=max(0, int(non_fever_base)),
        use_forced_great_timing=bool(use_forced_great_timing),
    )
    action_count = int(len(actions))
    later_valid = np.zeros((n, action_count), dtype=np.int8)
    later_next = np.full((n, action_count), -1, dtype=np.int32)
    later_fever_masks = np.zeros((n, action_count, 4), dtype=np.uint32)
    later_great_masks = np.zeros((n, action_count, 4), dtype=np.uint32)
    later_body_counts = np.zeros((n, action_count, 2), dtype=np.int32)
    first_valid = np.zeros((1, action_count), dtype=np.int8)
    first_next = np.full((1, action_count), -1, dtype=np.int32)
    first_fever_masks = np.zeros((1, action_count, 4), dtype=np.uint32)
    first_great_masks = np.zeros((1, action_count, 4), dtype=np.uint32)
    first_body_counts = np.zeros((1, action_count, 2), dtype=np.int32)

    _build_fg_response_edges_kernel(
        int(n),
        int(action_count),
        np.float32(real_fever_time),
        1 if bool(use_forced_great_timing) else 0,
        ts,
        great_ts,
        np.asarray(later_fill, dtype=np.int32),
        np.asarray(first_fill, dtype=np.int32),
        np.asarray(later_forced, dtype=np.int32),
        np.asarray(first_forced, dtype=np.int32),
        later_valid,
        later_next,
        later_fever_masks,
        later_great_masks,
        later_body_counts,
        first_valid,
        first_next,
        first_fever_masks,
        first_great_masks,
        first_body_counts,
    )

    return _frontier_from_edge_arrays(
        n=int(n),
        action_count=int(action_count),
        non_fever_base=max(0, int(non_fever_base)),
        later_valid=later_valid,
        later_next=later_next,
        later_fever_masks=later_fever_masks,
        later_great_masks=later_great_masks,
        later_body_counts=later_body_counts,
        first_valid=first_valid,
        first_next=first_next,
        first_fever_masks=first_fever_masks,
        first_great_masks=first_great_masks,
        first_body_counts=first_body_counts,
        seconds=float(time.perf_counter() - started),
        include_state_frontiers=bool(include_state_frontiers),
    )


def _batch_chunk_size(*, n: int, action_count: int, geometry_count: int, bytes_per_edge: int = 64) -> int:
    denom = max(1, int(n) * max(1, int(action_count)) * bytes_per_edge)
    return max(1, min(int(geometry_count), int(_GPU_EDGE_BATCH_MAX_BYTES) // denom))


def _first_only_padded_chunks(*, n: int, items: list[tuple]) -> list[tuple[int, list[tuple]]]:
    out: list[tuple[int, list[tuple]]] = []
    chunk: list[tuple] = []
    max_action_count = 0
    for item in sorted(items, key=lambda row: int(row[3].shape[0]), reverse=True):
        action_count = int(item[3].shape[0])
        next_max = max(int(max_action_count), int(action_count))
        next_len = len(chunk) + 1
        if chunk and int(next_len) * int(next_max) * int(n) * 4 > int(_GPU_EDGE_BATCH_MAX_BYTES):
            out.append((int(max_action_count), chunk))
            chunk = []
            max_action_count = 0
        chunk.append(item)
        max_action_count = max(int(max_action_count), int(action_count))
    if chunk:
        out.append((int(max_action_count), chunk))
    return out


def _pad_action_rows(rows: list[np.ndarray], width: int) -> np.ndarray:
    out = np.zeros((len(rows), int(width)), dtype=np.int32)
    for idx, row in enumerate(rows):
        count = int(row.shape[0])
        out[idx, :count] = row
    return out


def _precompute_end_indices(
    *,
    timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    real_times: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    unique_real_times, inverse = np.unique(np.asarray(real_times, dtype=np.float32), return_inverse=True)
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
    timestamp_end_idx = np.empty((int(unique_real_times.shape[0]), int(ts.shape[0])), dtype=np.int32)
    great_end_idx = np.empty_like(timestamp_end_idx)
    for idx, real_time in enumerate(unique_real_times):
        rt = np.float32(real_time)
        timestamp_end_idx[idx] = np.searchsorted(ts, np.asarray(ts + rt, dtype=np.float32), side="left").astype(
            np.int32,
            copy=False,
        )
        great_end_idx[idx] = np.searchsorted(ts, np.asarray(great_ts + rt, dtype=np.float32), side="left").astype(
            np.int32,
            copy=False,
        )
    return (
        np.ascontiguousarray(inverse.astype(np.int32, copy=False)),
        np.ascontiguousarray(timestamp_end_idx),
        np.ascontiguousarray(great_end_idx),
    )


def _first_frontier_result_from_next_arrays(
    *,
    n: int,
    action_count: int,
    non_fever_base: int,
    later_next: np.ndarray,
    later_fill: np.ndarray,
    later_forced: np.ndarray,
    first_next: np.ndarray,
    first_fill: np.ndarray,
    first_forced: np.ndarray,
) -> FgResponseFrontierResult:
    first_rows, states_evaluated, generated_surfaces, retained_total, max_state_frontier = (
        _first_frontier_from_next_arrays_numba(
            int(n),
            int(action_count),
            later_next,
            later_fill,
            later_forced,
            first_next,
            first_fill,
            first_forced,
        )
    )
    return FgResponseFrontierResult(
        first_frontier=tuple(_surface_from_numba_row(first_rows[idx]) for idx in range(int(first_rows.shape[0]))),
        state_frontiers={},
        states_evaluated=int(states_evaluated),
        actions=int(action_count),
        transitions_evaluated=0,
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=int(non_fever_base),
        seconds=0.0,
    )


def _first_frontier_result_from_precomputed_body_tail(
    *,
    n: int,
    action_count: int,
    non_fever_base: int,
    later_fill: np.ndarray,
    later_forced: np.ndarray,
    first_fill: np.ndarray,
    first_forced: np.ndarray,
    use_forced_great_timing: bool,
    timestamps: np.ndarray,
    great_candidate_timestamps: np.ndarray,
    timestamp_end_idx: np.ndarray,
    great_end_idx: np.ndarray,
) -> FgResponseFrontierResult:
    first_rows, states_evaluated, generated_surfaces, retained_total, max_state_frontier = (
        _first_frontier_from_body_tail_precomputed_numba(
            int(n),
            int(action_count),
            later_fill,
            later_forced,
            first_fill,
            first_forced,
            1 if bool(use_forced_great_timing) else 0,
            timestamps,
            great_candidate_timestamps,
            timestamp_end_idx,
            great_end_idx,
        )
    )
    return FgResponseFrontierResult(
        first_frontier=tuple(_surface_from_numba_row(first_rows[idx]) for idx in range(int(first_rows.shape[0]))),
        state_frontiers={},
        states_evaluated=int(states_evaluated),
        actions=int(action_count),
        transitions_evaluated=0,
        generated_surfaces=int(generated_surfaces),
        retained_surfaces_total=int(retained_total),
        max_state_frontier=int(max_state_frontier),
        non_fever_base=int(non_fever_base),
        seconds=0.0,
    )


def build_force_greats_response_frontiers_gpu_batch(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    geometries: Any,
    use_forced_great_timing: bool = True,
    include_state_frontiers: bool = True,
) -> tuple[FgResponseFrontierResult, ...]:
    init_taichi()
    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    geometry_rows = tuple(geometries or ())
    if not geometry_rows:
        return ()
    if n <= 0:
        return tuple(FgResponseFrontierResult((_EMPTY_SURFACE,), {}, 0, 0, 0, 0, 1, 1, 0, 0.0) for _ in geometry_rows)
    if bool(np.any(ts[1:] < ts[:-1])):
        raise ValueError("timestamps must be sorted in nondecreasing order")
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")

    prepared = []
    action_table_cache: dict[tuple[float, int, bool], tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    for idx, row in enumerate(geometry_rows):
        raw_fever_fill, non_fever_base, real_fever_time = row
        action_key = (float(raw_fever_fill), max(0, int(non_fever_base)), bool(use_forced_great_timing))
        action_arrays = action_table_cache.get(action_key)
        if action_arrays is None:
            _actions, later_fill, first_fill, later_forced, first_forced = _action_table(
                raw_fever_fill=float(raw_fever_fill),
                non_fever_base=max(0, int(non_fever_base)),
                use_forced_great_timing=bool(use_forced_great_timing),
            )
            action_arrays = (
                np.asarray(later_fill, dtype=np.int32),
                np.asarray(first_fill, dtype=np.int32),
                np.asarray(later_forced, dtype=np.int32),
                np.asarray(first_forced, dtype=np.int32),
            )
            action_table_cache[action_key] = action_arrays
        later_fill_arr, first_fill_arr, later_forced_arr, first_forced_arr = action_arrays
        prepared.append(
            (
                idx,
                max(0, int(non_fever_base)),
                float(real_fever_time),
                later_fill_arr,
                first_fill_arr,
                later_forced_arr,
                first_forced_arr,
            )
        )

    out: list[FgResponseFrontierResult | None] = [None] * len(geometry_rows)
    if not bool(include_state_frontiers):
        body_items = [item for item in prepared if int(item[4][0]) >= 100]
        head_items = [item for item in prepared if int(item[4][0]) < 100]
        if body_items:
            body_real_times = np.asarray([item[2] for item in body_items], dtype=np.float32)
            body_real_time_index, body_timestamp_end_idx, body_great_end_idx = _precompute_end_indices(
                timestamps=ts,
                great_candidate_timestamps=great_ts,
                real_times=body_real_times,
            )

            def build_body_item(local_idx: int) -> tuple[int, FgResponseFrontierResult]:
                item = body_items[local_idx]
                rt_idx = int(body_real_time_index[local_idx])
                return (
                    int(item[0]),
                    _first_frontier_result_from_precomputed_body_tail(
                        n=int(n),
                        action_count=int(item[3].shape[0]),
                        non_fever_base=int(item[1]),
                        later_fill=item[3],
                        later_forced=item[5],
                        first_fill=item[4],
                        first_forced=item[6],
                        use_forced_great_timing=bool(use_forced_great_timing),
                        timestamps=ts,
                        great_candidate_timestamps=great_ts,
                        timestamp_end_idx=body_timestamp_end_idx[rt_idx],
                        great_end_idx=body_great_end_idx[rt_idx],
                    ),
                )

            reducer_workers = min(
                int(_FIRST_FRONTIER_REDUCER_THREADS),
                int(len(body_items)),
            )
            if reducer_workers <= 1:
                for local_idx in range(len(body_items)):
                    source_idx, frontier = build_body_item(local_idx)
                    out[source_idx] = frontier
            else:
                def build_body_range(bounds: tuple[int, int]) -> list[tuple[int, FgResponseFrontierResult]]:
                    start_idx, end_idx = bounds
                    return [build_body_item(local_idx) for local_idx in range(start_idx, end_idx)]

                block_size = max(1, (int(len(body_items)) + int(reducer_workers) - 1) // int(reducer_workers))
                ranges = [
                    (start_idx, min(int(len(body_items)), start_idx + block_size))
                    for start_idx in range(0, int(len(body_items)), block_size)
                ]
                with ThreadPoolExecutor(max_workers=reducer_workers) as executor:
                    for result_block in executor.map(build_body_range, ranges):
                        for source_idx, frontier in result_block:
                            out[int(source_idx)] = frontier
        chunk_iter = _first_only_padded_chunks(n=int(n), items=head_items)
    else:
        groups: dict[int, list[tuple]] = {}
        for item in prepared:
            groups.setdefault(int(item[3].shape[0]), []).append(item)
        chunk_iter = []
        for action_count, items in groups.items():
            chunk_size = _batch_chunk_size(
                n=int(n),
                action_count=int(action_count),
                geometry_count=len(items),
                bytes_per_edge=64,
            )
            for start in range(0, len(items), chunk_size):
                chunk_iter.append((int(action_count), items[start : start + chunk_size]))

    for action_count, chunk in chunk_iter:
            geometry_count = len(chunk)
            action_counts = np.asarray([int(item[3].shape[0]) for item in chunk], dtype=np.int32)
            real_times = np.asarray([item[2] for item in chunk], dtype=np.float32)
            real_time_index, timestamp_end_idx, great_end_idx = _precompute_end_indices(
                timestamps=ts,
                great_candidate_timestamps=great_ts,
                real_times=real_times,
            )
            if not bool(include_state_frontiers):
                later_fill = _pad_action_rows([item[3] for item in chunk], int(action_count))
                first_fill = _pad_action_rows([item[4] for item in chunk], int(action_count))
                later_forced = _pad_action_rows([item[5] for item in chunk], int(action_count))
                first_forced = _pad_action_rows([item[6] for item in chunk], int(action_count))
                later_next = np.empty((geometry_count, n, action_count), dtype=np.int32)
                first_next = np.empty((geometry_count, action_count), dtype=np.int32)
                _build_fg_response_next_batch_kernel(
                    int(n),
                    int(geometry_count),
                    int(action_count),
                    1 if bool(use_forced_great_timing) else 0,
                    ts,
                    great_ts,
                    real_time_index,
                    timestamp_end_idx,
                    great_end_idx,
                    action_counts,
                    later_fill,
                    first_fill,
                    later_forced,
                    first_forced,
                    later_next,
                    first_next,
                )
                reducer_workers = min(
                    int(_FIRST_FRONTIER_REDUCER_THREADS),
                    int(geometry_count),
                )

                def build_local(local_idx: int) -> tuple[int, FgResponseFrontierResult]:
                    item = chunk[local_idx]
                    return (
                        int(item[0]),
                        _first_frontier_result_from_next_arrays(
                            n=int(n),
                            action_count=int(item[3].shape[0]),
                            non_fever_base=int(item[1]),
                            later_next=later_next[local_idx],
                            later_fill=later_fill[local_idx],
                            later_forced=later_forced[local_idx],
                            first_next=first_next[local_idx],
                            first_fill=first_fill[local_idx],
                            first_forced=first_forced[local_idx],
                        ),
                    )

                if reducer_workers <= 1:
                    for local_idx in range(geometry_count):
                        source_idx, frontier = build_local(local_idx)
                        out[source_idx] = frontier
                else:
                    def build_local_range(bounds: tuple[int, int]) -> list[tuple[int, FgResponseFrontierResult]]:
                        start_idx, end_idx = bounds
                        return [build_local(local_idx) for local_idx in range(start_idx, end_idx)]

                    block_size = max(1, (int(geometry_count) + int(reducer_workers) - 1) // int(reducer_workers))
                    ranges = [
                        (start_idx, min(int(geometry_count), start_idx + block_size))
                        for start_idx in range(0, int(geometry_count), block_size)
                    ]
                    with ThreadPoolExecutor(max_workers=reducer_workers) as executor:
                        for result_block in executor.map(build_local_range, ranges):
                            for source_idx, frontier in result_block:
                                out[int(source_idx)] = frontier
                continue

            later_fill = np.vstack([item[3] for item in chunk]).astype(np.int32, copy=False)
            first_fill = np.vstack([item[4] for item in chunk]).astype(np.int32, copy=False)
            later_forced = np.vstack([item[5] for item in chunk]).astype(np.int32, copy=False)
            first_forced = np.vstack([item[6] for item in chunk]).astype(np.int32, copy=False)
            later_valid = np.zeros((geometry_count, n, action_count), dtype=np.int8)
            later_next = np.full((geometry_count, n, action_count), -1, dtype=np.int32)
            later_fever_masks = np.zeros((geometry_count, n, action_count, 4), dtype=np.uint32)
            later_great_masks = np.zeros((geometry_count, n, action_count, 4), dtype=np.uint32)
            later_body_counts = np.zeros((geometry_count, n, action_count, 2), dtype=np.int32)
            first_valid = np.zeros((geometry_count, action_count), dtype=np.int8)
            first_next = np.full((geometry_count, action_count), -1, dtype=np.int32)
            first_fever_masks = np.zeros((geometry_count, action_count, 4), dtype=np.uint32)
            first_great_masks = np.zeros((geometry_count, action_count, 4), dtype=np.uint32)
            first_body_counts = np.zeros((geometry_count, action_count, 2), dtype=np.int32)

            _build_fg_response_edges_batch_kernel(
                int(n),
                int(geometry_count),
                int(action_count),
                1 if bool(use_forced_great_timing) else 0,
                ts,
                great_ts,
                real_time_index,
                timestamp_end_idx,
                great_end_idx,
                action_counts,
                later_fill,
                first_fill,
                later_forced,
                first_forced,
                later_valid,
                later_next,
                later_fever_masks,
                later_great_masks,
                later_body_counts,
                first_valid,
                first_next,
                first_fever_masks,
                first_great_masks,
                first_body_counts,
            )
            for local_idx, item in enumerate(chunk):
                source_idx = int(item[0])
                out[source_idx] = _frontier_from_edge_arrays(
                    n=int(n),
                    action_count=int(action_count),
                    non_fever_base=int(item[1]),
                    later_valid=later_valid[local_idx],
                    later_next=later_next[local_idx],
                    later_fever_masks=later_fever_masks[local_idx],
                    later_great_masks=later_great_masks[local_idx],
                    later_body_counts=later_body_counts[local_idx],
                    first_valid=first_valid[local_idx : local_idx + 1],
                    first_next=first_next[local_idx : local_idx + 1],
                    first_fever_masks=first_fever_masks[local_idx : local_idx + 1],
                    first_great_masks=first_great_masks[local_idx : local_idx + 1],
                    first_body_counts=first_body_counts[local_idx : local_idx + 1],
                    seconds=0.0,
                    include_state_frontiers=bool(include_state_frontiers),
                )

    missing = [idx for idx, frontier in enumerate(out) if frontier is None]
    if missing:
        raise ValueError(f"FG response frontier GPU batch missed geometry indices: {missing[:8]}")
    return tuple(frontier for frontier in out if frontier is not None)


__all__ = ["build_force_greats_response_frontier_gpu", "build_force_greats_response_frontiers_gpu_batch"]
