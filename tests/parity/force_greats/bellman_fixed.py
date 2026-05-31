from dataclasses import dataclass
from math import ceil
from typing import Any

import numpy as np
import taichi as ti

from gear_optimizer.solver.taichi_gem import api as gem_api


@dataclass(frozen=True)
class FgBellmanFixedStatsResult:
    best_score: int
    best_delta: int
    best_forced_counts: tuple[int, ...]
    states_evaluated: int
    transitions_evaluated: int
    max_k_used: int
    section_count: int
    non_fever_base: int


@ti.func
def _fg_bellman_lower_bound_from(timestamps: ti.template(), n, value, lo_start):
    lo: ti.i32 = lo_start
    hi: ti.i32 = n
    while lo < hi:
        mid: ti.i32 = (lo + hi) // 2
        if timestamps[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return lo


@ti.func
def _fg_bellman_edge_end(
    n,
    a,
    forced_start,
    forced_applied,
    real_fever_time,
    use_forced_great_timing,
    timestamps: ti.template(),
    great_candidate_timestamps: ti.template(),
):
    forced_end_for_timing: ti.i32 = forced_start + forced_applied - 1
    start_time: ti.f32 = timestamps[a]
    if (
        use_forced_great_timing != 0
        and forced_applied > 0
        and forced_end_for_timing >= forced_start
        and forced_end_for_timing < a
        and forced_end_for_timing < n
    ):
        forced_t: ti.f32 = great_candidate_timestamps[forced_end_for_timing]
        if forced_t > start_time:
            start_time = forced_t
    e: ti.i32 = _fg_bellman_lower_bound_from(timestamps, n, start_time + real_fever_time, a)
    if e <= a:
        e = a + 1
    if e > n:
        e = n
    return e, start_time


@ti.kernel
def _fg_bellman_build_prefix_kernel(
    n: ti.i32,
    normal_score_per_note: ti.types.ndarray(dtype=ti.i32, ndim=1),
    fever_score_per_note: ti.types.ndarray(dtype=ti.i32, ndim=1),
    fever_gain_prefix: ti.types.ndarray(dtype=ti.i64, ndim=1),
    normal_total_out: ti.types.ndarray(dtype=ti.i64, ndim=1),
):
    ti.loop_config(serialize=True)
    total: ti.i64 = 0
    gain: ti.i64 = 0
    fever_gain_prefix[0] = 0
    for i in range(n):
        normal_i: ti.i64 = ti.cast(normal_score_per_note[i], ti.i64)
        fever_i: ti.i64 = ti.cast(fever_score_per_note[i], ti.i64)
        total += normal_i
        gain += fever_i - normal_i
        fever_gain_prefix[i + 1] = gain
    normal_total_out[0] = total


@ti.kernel
def _fg_bellman_reachable_kernel(
    n: ti.i32,
    action_count: ti.i32,
    action_fill_later: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_forced_later: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_fill_first: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_forced_first: ti.types.ndarray(dtype=ti.i32, ndim=1),
    real_fever_time: ti.f32,
    use_forced_great_timing: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    reachable: ti.types.ndarray(dtype=ti.i32, ndim=1),
    reach_debug_out: ti.types.ndarray(dtype=ti.i64, ndim=1),
):
    ti.loop_config(serialize=True)
    for i in range(n + 1):
        reachable[i] = 0
    reachable[n] = 1

    first_action_idx: ti.i32 = 0
    first_scan_active: ti.i32 = 1
    while first_action_idx < action_count and first_scan_active != 0:
        notes_to_fill: ti.i32 = action_fill_first[first_action_idx]
        a: ti.i32 = notes_to_fill
        if a >= n:
            first_scan_active = 0
        else:
            forced_applied: ti.i32 = action_forced_first[first_action_idx]
            e, _start_time = _fg_bellman_edge_end(
                n,
                a,
                0,
                forced_applied,
                real_fever_time,
                use_forced_great_timing,
                timestamps,
                great_candidate_timestamps,
            )
            reachable[e] = 1
            first_action_idx += 1

    ti.loop_config(serialize=True)
    for i in range(n):
        if reachable[i] != 0:
            action_idx: ti.i32 = 0
            later_scan_active: ti.i32 = 1
            while action_idx < action_count and later_scan_active != 0:
                notes_to_fill: ti.i32 = action_fill_later[action_idx]
                a: ti.i32 = i + notes_to_fill
                if a >= n:
                    later_scan_active = 0
                else:
                    forced_applied: ti.i32 = action_forced_later[action_idx]
                    forced_start: ti.i32 = i + 1
                    e, _start_time = _fg_bellman_edge_end(
                        n,
                        a,
                        forced_start,
                        forced_applied,
                        real_fever_time,
                        use_forced_great_timing,
                        timestamps,
                        great_candidate_timestamps,
                    )
                    reachable[e] = 1
                    action_idx += 1

    reachable_count: ti.i64 = 0
    ti.loop_config(serialize=True)
    for i in range(n):
        if reachable[i] != 0:
            reachable_count += 1
    reach_debug_out[0] = reachable_count


@ti.kernel
def _fg_bellman_solve_kernel(
    n: ti.i32,
    action_count: ti.i32,
    action_values: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_fill_later: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_forced_later: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_fill_first: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_forced_first: ti.types.ndarray(dtype=ti.i32, ndim=1),
    real_fever_time: ti.f32,
    use_forced_great_timing: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    fever_gain_prefix: ti.types.ndarray(dtype=ti.i64, ndim=1),
    forced_penalty_prefix: ti.types.ndarray(dtype=ti.i64, ndim=1),
    later_value: ti.types.ndarray(dtype=ti.i64, ndim=1),
    later_choice: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_next: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_out: ti.types.ndarray(dtype=ti.i64, ndim=1),
    solve_debug_out: ti.types.ndarray(dtype=ti.i64, ndim=1),
    reachable: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    later_value[n] = 0
    later_choice[n] = 0
    later_next[n] = n
    transitions: ti.i64 = 0

    ti.loop_config(serialize=True)
    for offset in range(n):
        i: ti.i32 = n - 1 - offset
        best: ti.i64 = 0
        best_k: ti.i32 = 0
        best_next: ti.i32 = n
        if reachable[i] != 0:
            prev_fill: ti.i32 = -1
            prev_start_time: ti.f32 = -1.0
            prev_e: ti.i32 = -1
            action_idx: ti.i32 = 0
            active: ti.i32 = 1
            while action_idx < action_count and active != 0:
                k: ti.i32 = action_values[action_idx]
                notes_to_fill: ti.i32 = action_fill_later[action_idx]
                a: ti.i32 = i + notes_to_fill
                if a >= n:
                    active = 0
                else:
                    forced_applied: ti.i32 = action_forced_later[action_idx]
                    forced_start: ti.i32 = i + 1
                    e, start_time = _fg_bellman_edge_end(
                        n,
                        a,
                        forced_start,
                        forced_applied,
                        real_fever_time,
                        use_forced_great_timing,
                        timestamps,
                        great_candidate_timestamps,
                    )
                    if not (notes_to_fill == prev_fill and start_time == prev_start_time):
                        if not (notes_to_fill == prev_fill and e == prev_e):
                            transitions += 1
                            penalty_end: ti.i32 = forced_start + forced_applied
                            if penalty_end > n:
                                penalty_end = n
                            if forced_start > n:
                                forced_start = n
                            val: ti.i64 = (
                                fever_gain_prefix[e]
                                - fever_gain_prefix[a]
                                - (forced_penalty_prefix[penalty_end] - forced_penalty_prefix[forced_start])
                                + later_value[e]
                            )
                            if val > best:
                                best = val
                                best_k = k
                                best_next = e
                        prev_e = e
                    prev_fill = notes_to_fill
                    prev_start_time = start_time
                    action_idx += 1
        later_value[i] = best
        later_choice[i] = best_k
        later_next[i] = best_next

    first_best: ti.i64 = 0
    first_k: ti.i32 = 0
    first_next: ti.i32 = n
    first_active: ti.i32 = 0
    first_transitions: ti.i64 = 0
    prev_fill: ti.i32 = -1
    prev_start_time: ti.f32 = -1.0
    prev_e: ti.i32 = -1
    action_idx: ti.i32 = 0
    active: ti.i32 = 1
    while action_idx < action_count and active != 0:
        k: ti.i32 = action_values[action_idx]
        notes_to_fill: ti.i32 = action_fill_first[action_idx]
        a: ti.i32 = notes_to_fill
        if a >= n:
            active = 0
        else:
            forced_applied: ti.i32 = action_forced_first[action_idx]
            e, start_time = _fg_bellman_edge_end(
                n,
                a,
                0,
                forced_applied,
                real_fever_time,
                use_forced_great_timing,
                timestamps,
                great_candidate_timestamps,
            )
            if not (notes_to_fill == prev_fill and start_time == prev_start_time):
                if not (notes_to_fill == prev_fill and e == prev_e):
                    first_transitions += 1
                    penalty_end: ti.i32 = forced_applied
                    if penalty_end > n:
                        penalty_end = n
                    val: ti.i64 = (
                        fever_gain_prefix[e]
                        - fever_gain_prefix[a]
                        - (forced_penalty_prefix[penalty_end] - forced_penalty_prefix[0])
                        + later_value[e]
                    )
                    if val > first_best:
                        first_best = val
                        first_k = k
                        first_next = e
                        first_active = 1
                prev_e = e
            prev_fill = notes_to_fill
            prev_start_time = start_time
            action_idx += 1

    first_out[0] = first_best
    first_out[1] = ti.cast(first_k, ti.i64)
    first_out[2] = ti.cast(first_next, ti.i64)
    first_out[3] = ti.cast(first_active, ti.i64)
    first_out[4] = first_transitions
    solve_debug_out[0] = transitions


def _fg_bellman_action_table(*, raw_fever_fill: float, non_fever_base: int, use_forced_great_timing: bool):
    b = max(0, int(non_fever_base))
    actions: list[int] = []
    later_fill: list[int] = []
    first_fill: list[int] = []
    later_forced: list[int] = []
    first_forced: list[int] = []
    last_notes_to_fill: int | None = None
    for k in range(b + 1):
        notes_to_fill = int(ceil(float(raw_fever_fill) + (float(k) * 0.5)))
        if bool(use_forced_great_timing) or last_notes_to_fill is None or notes_to_fill != last_notes_to_fill:
            first_notes_to_fill = max(0, int(notes_to_fill) - 1)
            actions.append(int(k))
            later_fill.append(int(notes_to_fill))
            first_fill.append(int(first_notes_to_fill))
            later_forced.append(min(int(k), int(notes_to_fill)))
            first_forced.append(min(int(k), int(first_notes_to_fill)))
        last_notes_to_fill = int(notes_to_fill)
    if not actions:
        actions.append(0)
        later_fill.append(0)
        first_fill.append(0)
        later_forced.append(0)
        first_forced.append(0)
    return (
        np.ascontiguousarray(np.asarray(actions, dtype=np.int32)),
        np.ascontiguousarray(np.asarray(later_fill, dtype=np.int32)),
        np.ascontiguousarray(np.asarray(first_fill, dtype=np.int32)),
        np.ascontiguousarray(np.asarray(later_forced, dtype=np.int32)),
        np.ascontiguousarray(np.asarray(first_forced, dtype=np.int32)),
    )


@ti.kernel
def _fg_bellman_reconstruct_kernel(
    n: ti.i32,
    first_out: ti.types.ndarray(dtype=ti.i64, ndim=1),
    later_choice: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_next: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    debug_out: ti.types.ndarray(dtype=ti.i64, ndim=1),
):
    count: ti.i32 = 0
    max_k: ti.i32 = 0
    if first_out[3] != 0 and n > 0:
        k0: ti.i32 = ti.cast(first_out[1], ti.i32)
        out_counts[0] = k0
        if k0 > max_k:
            max_k = k0
        count = 1
        idx: ti.i32 = ti.cast(first_out[2], ti.i32)
        while idx < n and count < n:
            k: ti.i32 = later_choice[idx]
            out_counts[count] = k
            if k > max_k:
                max_k = k
            next_idx: ti.i32 = later_next[idx]
            count += 1
            if next_idx <= idx:
                idx = n
            else:
                idx = next_idx
    debug_out[0] = count
    debug_out[1] = max_k


def solve_force_greats_bellman_fixed_stats_gpu(
    *,
    timestamps: Any,
    great_candidate_timestamps: Any | None = None,
    raw_fever_fill: float,
    non_fever_base: int,
    real_fever_time: float,
    normal_score_per_note: Any,
    fever_score_per_note: Any,
    forced_great_penalty_prefix: Any,
    use_forced_great_timing: bool = True,
) -> FgBellmanFixedStatsResult:
    """
    Exact cap-free ForceGreats Bellman DP for fixed scoring stats.

    This solver intentionally does not perform PP/CM/FM/OV gem reoptimization,
    heuristic section caps, max-FP cap tables, caches, or prebuilt FT/FF grids.
    """
    gem_api.ensure_ready()

    ts = np.ascontiguousarray(np.asarray(timestamps, dtype=np.float32).reshape(-1))
    n = int(ts.shape[0])
    if n <= 0:
        return FgBellmanFixedStatsResult(0, 0, (), 0, 0, 0, 0, max(0, int(non_fever_base)))
    if great_candidate_timestamps is None:
        great_ts = ts
    else:
        great_ts = np.ascontiguousarray(np.asarray(great_candidate_timestamps, dtype=np.float32).reshape(-1))
        if int(great_ts.shape[0]) != n:
            raise ValueError("great_candidate_timestamps length must match timestamps")
    if bool(np.any(ts[1:] < ts[:-1])):
        raise ValueError("timestamps must be sorted in nondecreasing order")

    normal = np.ascontiguousarray(np.asarray(normal_score_per_note, dtype=np.int32).reshape(-1))
    fever = np.ascontiguousarray(np.asarray(fever_score_per_note, dtype=np.int32).reshape(-1))
    penalty_prefix = np.ascontiguousarray(np.asarray(forced_great_penalty_prefix, dtype=np.int64).reshape(-1))
    if int(normal.shape[0]) != n or int(fever.shape[0]) != n:
        raise ValueError("normal_score_per_note and fever_score_per_note must match timestamps length")
    if int(penalty_prefix.shape[0]) < n + 1:
        raise ValueError("forced_great_penalty_prefix must have length at least len(timestamps)+1")
    if bool(np.any(penalty_prefix[1 : n + 1] < penalty_prefix[:n])):
        raise ValueError("forced_great_penalty_prefix must be nondecreasing")

    b = max(0, int(non_fever_base))
    fever_gain_prefix = np.zeros((n + 1,), dtype=np.int64)
    normal_total = np.zeros((1,), dtype=np.int64)
    later_value = np.zeros((n + 1,), dtype=np.int64)
    later_choice = np.zeros((n + 1,), dtype=np.int32)
    later_next = np.full((n + 1,), n, dtype=np.int32)
    first_out = np.zeros((5,), dtype=np.int64)
    out_counts = np.zeros((n,), dtype=np.int32)
    debug_out = np.zeros((2,), dtype=np.int64)
    solve_debug = np.zeros((1,), dtype=np.int64)
    reachable = np.zeros((n + 1,), dtype=np.int32)
    reach_debug = np.zeros((1,), dtype=np.int64)
    action_values, action_fill_later, action_fill_first, action_forced_later, action_forced_first = (
        _fg_bellman_action_table(
            raw_fever_fill=float(raw_fever_fill),
            non_fever_base=int(b),
            use_forced_great_timing=bool(use_forced_great_timing),
        )
    )
    action_count = int(action_values.shape[0])

    _fg_bellman_build_prefix_kernel(n, normal, fever, fever_gain_prefix, normal_total)
    _fg_bellman_reachable_kernel(
        n,
        int(action_count),
        action_fill_later,
        action_forced_later,
        action_fill_first,
        action_forced_first,
        float(real_fever_time),
        1 if bool(use_forced_great_timing) else 0,
        ts,
        great_ts,
        reachable,
        reach_debug,
    )
    _fg_bellman_solve_kernel(
        n,
        int(action_count),
        action_values,
        action_fill_later,
        action_forced_later,
        action_fill_first,
        action_forced_first,
        float(real_fever_time),
        1 if bool(use_forced_great_timing) else 0,
        ts,
        great_ts,
        fever_gain_prefix,
        penalty_prefix,
        later_value,
        later_choice,
        later_next,
        first_out,
        solve_debug,
        reachable,
    )
    _fg_bellman_reconstruct_kernel(n, first_out, later_choice, later_next, out_counts, debug_out)
    ti.sync()

    section_count = int(debug_out[0])
    best_delta = int(first_out[0])
    best_score = int(normal_total[0]) + best_delta
    return FgBellmanFixedStatsResult(
        best_score=max(0, int(best_score)),
        best_delta=int(best_delta),
        best_forced_counts=tuple(int(v) for v in out_counts[:section_count]),
        states_evaluated=int(reach_debug[0]),
        transitions_evaluated=int(solve_debug[0]) + int(first_out[4]),
        max_k_used=int(debug_out[1]),
        section_count=int(section_count),
        non_fever_base=int(b),
    )
