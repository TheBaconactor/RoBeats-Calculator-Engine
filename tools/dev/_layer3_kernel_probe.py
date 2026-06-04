"""Throwaway GPU parity probe (Layer 3): the FULL FG first-frontier kernel.

Assembles the entire ``_first_frontier_from_precomputed_end_indices_numba``
reference (gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu_numba.py:714-1319)
into ONE Taichi/Vulkan ``@ti.kernel`` with ONE LANE per ``(ft,ff)`` geometry key
(``for lane in range(n_lanes)`` is the GPU-parallel domain). Each lane runs the
entire serial DP for one geometry, reading its action arrays + the shared
end-index tables and writing its first-frontier to an output slab.

The Layer-1/2a/2b ``@ti.func`` building blocks are imported UNCHANGED from the
production module ``response_build_gpu_taichi.py`` (already GPU-parity-validated
bit-exact vs their Numba twins). This probe only adds:
  * ``_reduce_touched_body_pairs_at`` / ``_reduce_into_bucket`` thin copy wrappers
    that route the validated reducers' output into the state-offset scratch slabs
    (``body_tails`` / ``head_frontiers`` are per-state lists in Numba),
  * a couple of small @ti.func helpers that are still pure ports of Numba leaf
    helpers not in the validated module (``_numba_body_count`` reused; the
    fast-path body-fever DP, and the ``_numba_*`` append/combine tail emit), and
  * the orchestrating ``first_frontier_kernel``.

This is a probe under tools/dev/. It does NOT modify any production module. The
@ti.func/@ti.kernel bodies here are the deliverable to be integrated separately.

Run:  python tools/dev/_layer3_kernel_probe.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()

import taichi as ti  # noqa: E402

# Reuse the validated leaf/reduction @ti.func building blocks UNCHANGED.
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_taichi import (  # noqa: E402
    vec7u64,
    _body_count,
    _pack_edge,
    _body_prefix_surface,
    _first_edge,
    _later_edge,
    _first_activation_edge,
    _later_activation_edge,
    _touch_body_candidate,
    _reduce_touched_body_pairs,
    _append_surface,
)

# Parity oracle bundle builder + oracle runner.
from tests.parity.force_greats.fg_frontier_kernel_parity import (  # noqa: E402
    build_kernel_args,
    numba_first_frontier,
)
from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_precompute import (  # noqa: E402
    _precompute_end_indices,
)


# =========================================================================== #
# NEW @ti.func ports (deliverable).
#
# 1. _reduce_touched_body_pairs_at : run the validated body-skyline reducer into
#    a per-lane scratch (red3), then COPY its emitted (fever,great,fevergreat)
#    triples into the state-offset region of body_tails_vals. Numba stores the
#    reduced body frontier as body_tails[state_i] (a per-state list of 3-tuples).
#
# 2. _zero_forced_body_fever / _max_body_fever : the fast-path body-fever DP.
#    Pure ports of Numba _numba_zero_forced_body_fever_precomputed (485-541) and
#    _numba_max_body_fever_precomputed (542-710). These reuse the validated edge
#    helpers; the small per-lane DP arrays (reachable, best) live in scratch.
# =========================================================================== #


@ti.func
def _emit_tail_surfaces(
    n: ti.i32,
    edge: vec7u64,
    edge_e: ti.i32,
    head_limit: ti.i32,
    lane: ti.i32,
    cap_bt: ti.i32,
    cap_head: ti.i32,
    body_tails_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    body_tails_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    head_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    head_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bkt_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bkt_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    bkt_cap: ti.i32,
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
) -> ti.i32:
    # Numba head-emit dispatch (used in Phase 2 :1026-1033 and Branch B :1257-1268).
    #   edge_e >= 100        -> _numba_append_body_tail_surfaces: combine edge with
    #                            every body_tails[edge_e] tail (3-tuple) into the bucket.
    #   100 > edge_e >= head_limit -> _numba_append_terminal_tail_surface: append edge.
    #   edge_e < head_limit  -> _numba_append_surface_tail_surfaces: combine edge with
    #                            every head_frontiers[edge_e] surface (7-tuple).
    # Each emitted surface is run through the validated dominance reducer
    # (_append_surface into the per-lane bucket). Returns the GENERATED count
    # (number of surfaces emitted BEFORE dominance pruning), matching Numba's
    # generated_count accounting.
    count = ti.i32(0)
    if edge_e >= 100:
        tail_cnt = body_tails_cnt[lane, edge_e]
        for tail_idx in range(tail_cnt):
            tf = body_tails_vals[lane, edge_e * cap_bt + tail_idx, 0]
            tg = body_tails_vals[lane, edge_e * cap_bt + tail_idx, 1]
            tfg = body_tails_vals[lane, edge_e * cap_bt + tail_idx, 2]
            surf = vec7u64(
                edge[0], edge[1], edge[2], edge[3],
                edge[4] + tf, edge[5] + tg, edge[6] + tfg,
            )
            _append_surface(bkt_vals, bkt_cnt, error_flag, lane, bkt_cap, surf)
            count += 1
    elif edge_e >= head_limit:
        _append_surface(bkt_vals, bkt_cnt, error_flag, lane, bkt_cap, edge)
        count += 1
    else:
        tail_cnt = head_cnt[lane, edge_e]
        for tail_idx in range(tail_cnt):
            surf = vec7u64(
                edge[0] | head_vals[lane, edge_e * cap_head + tail_idx, 0],
                edge[1] | head_vals[lane, edge_e * cap_head + tail_idx, 1],
                edge[2] | head_vals[lane, edge_e * cap_head + tail_idx, 2],
                edge[3] | head_vals[lane, edge_e * cap_head + tail_idx, 3],
                edge[4] + head_vals[lane, edge_e * cap_head + tail_idx, 4],
                edge[5] + head_vals[lane, edge_e * cap_head + tail_idx, 5],
                edge[6] + head_vals[lane, edge_e * cap_head + tail_idx, 6],
            )
            _append_surface(bkt_vals, bkt_cnt, error_flag, lane, bkt_cap, surf)
            count += 1
    return count


@ti.func
def _max_body_fever_flat(
    n: ti.i32,
    action_count: ti.i32,
    base: ti.i32,
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_fgt: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    real_time_idx: ti.i32,
    lane: ti.i32,
    reachable: ti.types.ndarray(dtype=ti.i32, ndim=2),
    best_body: ti.types.ndarray(dtype=ti.i32, ndim=2),
) -> ti.i32:
    # Numba _numba_max_body_fever_precomputed (:542-710). Reachability + backward
    # best-body DP, returns the maximum body_fever achievable. The flat action
    # arrays are indexed with (base + action_idx). Uses per-lane scratch
    # reachable[lane, 0..n] and best_body[lane, 0..n] (RESET here).
    for s in range(n + 1):
        reachable[lane, s] = 0
    reachable[lane, n] = 1
    for action_idx in range(action_count):
        edge_e = _first_edge(
            n, base + action_idx, first_fill, use_fgt,
            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
        )
        if edge_e >= 0:
            reachable[lane, edge_e] = 1
        av = _first_activation_edge(
            n, base + action_idx, first_fill, first_activation_forced, use_fgt,
            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
        )
        activation_e = av[0]
        if activation_e >= 0 and activation_e > edge_e:
            reachable[lane, activation_e] = 1

    for state_i in range(n):
        if reachable[lane, state_i] != 0:
            for action_idx in range(action_count):
                edge_e = _later_edge(
                    n, state_i, base + action_idx, later_fill, use_fgt,
                    timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                )
                if edge_e >= 0:
                    reachable[lane, edge_e] = 1
                av = _later_activation_edge(
                    n, state_i, base + action_idx, later_fill, later_activation_forced, use_fgt,
                    timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                )
                activation_e = av[0]
                if activation_e >= 0 and activation_e > edge_e:
                    reachable[lane, activation_e] = 1

    for s in range(n + 1):
        best_body[lane, s] = 0
    for _rev in range(n):
        state_i = n - 1 - _rev
        if reachable[lane, state_i] != 0:
            best_value = ti.i32(0)
            for action_idx in range(action_count):
                edge_e = _later_edge(
                    n, state_i, base + action_idx, later_fill, use_fgt,
                    timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                )
                if edge_e >= 0:
                    fill = later_fill[base + action_idx]
                    candidate = ti.i32(_body_count(state_i + fill, edge_e, n)) + best_body[lane, edge_e]
                    if candidate > best_value:
                        best_value = candidate
                av = _later_activation_edge(
                    n, state_i, base + action_idx, later_fill, later_activation_forced, use_fgt,
                    timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                )
                activation_e = av[0]
                if activation_e >= 0 and activation_e > edge_e:
                    fill = later_fill[base + action_idx]
                    candidate = ti.i32(_body_count(state_i + fill, activation_e, n)) + best_body[lane, activation_e]
                    if candidate > best_value:
                        best_value = candidate
            best_body[lane, state_i] = best_value

    best_first = ti.i32(0)
    for action_idx in range(action_count):
        edge_e = _first_edge(
            n, base + action_idx, first_fill, use_fgt,
            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
        )
        if edge_e >= 0:
            candidate = ti.i32(_body_count(first_fill[base + action_idx], edge_e, n)) + best_body[lane, edge_e]
            if candidate > best_first:
                best_first = candidate
        av = _first_activation_edge(
            n, base + action_idx, first_fill, first_activation_forced, use_fgt,
            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
        )
        activation_e = av[0]
        if activation_e >= 0 and activation_e > edge_e:
            candidate = ti.i32(_body_count(first_fill[base + action_idx], activation_e, n)) + best_body[lane, activation_e]
            if candidate > best_first:
                best_first = candidate
    return best_first


# =========================================================================== #
# THE FULL KERNEL.
#
# Scratch arg list (all sizes host-chosen; see the host sizing helper below):
#   Per-geometry inputs flattened across lanes via offsets:
#     later_fill/first_fill/later_forced/first_forced/
#     later_activation_forced/first_activation_forced : i32[total_action_rows]
#     action_offset[n_lanes], action_count[n_lanes]
#     n[n_lanes], real_time_idx[n_lanes], use_fgt[n_lanes], pair_mod[n_lanes]
#   Shared tables (one song): timestamps f32[N], great_candidate_timestamps f32[N],
#     timestamp_end_idx i32[R,N], great_end_idx i32[R,N]
#   Scratch (per lane):
#     reachable i32[n_lanes, NMAX1]            (also reused by fast-path DP)
#     best_body i32[n_lanes, NMAX1]            (fast-path DP only)
#     body_tails_vals u64[n_lanes, NMAX1*CAP_BT, 3] + body_tails_cnt i32[n_lanes, NMAX1]
#     head_vals u64[n_lanes, 100*CAP_HEAD, 7]  + head_cnt i32[n_lanes, 100]
#     red3_vals u64[n_lanes, CAP_RED3, 3]      + red3_cnt i32[n_lanes]  (reducer sink)
#     bkt_vals  u64[n_lanes, CAP_HEAD, 7]      + bkt_cnt  i32[n_lanes]  (dominance sink)
#     best_fever_by_pair i32[n_lanes, PAIR_SIZE], pair_stamp i32[n_lanes, PAIR_SIZE],
#     touched_pair i32[n_lanes, PAIR_SIZE], bit_values i32[n_lanes, PAIRMOD1],
#     bit_stamps i32[n_lanes, PAIRMOD1]
#   Output: first_frontier_out u64[n_lanes, CAP_FF, 7] + first_frontier_cnt i32[n_lanes]
#           out_counters i32[n_lanes, 4], error_flag i32[n_lanes]
#
# DEVICE-SCRATCH CONTRACT: Taichi pools/reuses device ndarrays (NOT zeroed across
# launches). The TOP of each lane resets every read-before-write scratch slot.
# =========================================================================== #
@ti.kernel
def first_frontier_kernel(
    n_lanes: ti.i32,
    pair_size_cap: ti.i32,
    pairmod1_cap: ti.i32,
    cap_bt: ti.i32,
    cap_head: ti.i32,
    cap_red3: ti.i32,
    cap_ff: ti.i32,
    # per-geometry flattened action arrays
    later_fill_f: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_fill_f: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_forced_f: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_forced_f: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_activation_forced_f: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_activation_forced_f: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_offset: ti.types.ndarray(dtype=ti.i32, ndim=1),
    action_count_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    n_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    real_time_idx_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_fgt_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_mod_arr: ti.types.ndarray(dtype=ti.i32, ndim=1),
    # shared tables (one song)
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    # scratch
    reachable: ti.types.ndarray(dtype=ti.i32, ndim=2),
    best_body: ti.types.ndarray(dtype=ti.i32, ndim=2),
    body_tails_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    body_tails_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    head_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    head_cnt: ti.types.ndarray(dtype=ti.i32, ndim=2),
    red3_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    red3_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    bkt_vals: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bkt_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    best_fever_by_pair: ti.types.ndarray(dtype=ti.i32, ndim=2),
    pair_stamp: ti.types.ndarray(dtype=ti.i32, ndim=2),
    touched_pair: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    # output
    first_frontier_out: ti.types.ndarray(dtype=ti.u64, ndim=3),
    first_frontier_cnt: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_counters: ti.types.ndarray(dtype=ti.i32, ndim=2),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for lane in range(n_lanes):
        n = n_arr[lane]
        action_count = action_count_arr[lane]
        base = action_offset[lane]
        real_time_idx = real_time_idx_arr[lane]
        use_fgt = use_fgt_arr[lane]
        pair_mod = pair_mod_arr[lane]
        pair_size = (n + 1) * pair_mod
        bit_limit = pair_mod + 1

        # --- per-lane scratch reset (device buffers are pooled / not zeroed) ---
        error_flag[lane] = 0
        first_frontier_cnt[lane] = 0
        out_counters[lane, 0] = 0
        out_counters[lane, 1] = 0
        out_counters[lane, 2] = 0
        out_counters[lane, 3] = 0
        for s in range(n + 1):
            body_tails_cnt[lane, s] = 0
        head_limit = ti.min(n, 100)
        for s in range(head_limit):
            head_cnt[lane, s] = 0
        # Zero the stamp arrays per lane (correct-but-heavy; perf TODO: monotonic
        # per-lane stamp base that starts above any prior value to skip this).
        for s in range(pair_size):
            pair_stamp[lane, s] = 0
        for s in range(bit_limit):
            bit_stamps[lane, s] = 0

        pair_stamp_value = ti.i32(0)
        bit_stamp_value = ti.i32(0)

        # Build flat per-lane action-array views as 0-based slices via base offset.
        # (We index with action_offset[lane] + action_idx everywhere below.)

        # =================================================================== #
        # FAST PATH (Numba :730-764).
        # =================================================================== #
        took_fast_path = 0
        if action_count > 0 and first_fill_f[base + 0] >= 100:
            # zero_body_fever uses action 0 only; reuse flat arrays with base.
            zero_body_fever = ti.i32(-1)
            if first_fill_f[base + 0] < 100:
                zero_body_fever = ti.i32(-1)
            else:
                edge_e = _first_edge(
                    n, base + 0, first_fill_f, use_fgt,
                    timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                )
                if edge_e < 0:
                    zero_body_fever = ti.i32(-1)
                else:
                    total = ti.i32(_body_count(first_fill_f[base + 0], edge_e, n))
                    state_i = edge_e
                    done = 0
                    for _step in range(n + 1):
                        if done == 0:
                            if state_i >= n:
                                zero_body_fever = total
                                done = 1
                            else:
                                next_e = _later_edge(
                                    n, state_i, base + 0, later_fill_f, use_fgt,
                                    timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                                    real_time_idx,
                                )
                                if next_e < 0 or next_e <= state_i:
                                    zero_body_fever = ti.i32(-1)
                                    done = 1
                                else:
                                    total += ti.i32(_body_count(state_i + later_fill_f[base + 0], next_e, n))
                                    state_i = next_e
                    if done == 0:
                        zero_body_fever = ti.i32(-1)

            if zero_body_fever >= 0:
                max_body_fever = _max_body_fever_flat(
                    n, action_count, base,
                    later_fill_f, first_fill_f, later_activation_forced_f, first_activation_forced_f,
                    use_fgt, timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                    real_time_idx, lane, reachable, best_body,
                )
                if zero_body_fever == max_body_fever:
                    # Single body row: out[0,4] = zero_body_fever; counters (0,0,1,1).
                    first_frontier_out[lane, 0, 0] = ti.u64(0)
                    first_frontier_out[lane, 0, 1] = ti.u64(0)
                    first_frontier_out[lane, 0, 2] = ti.u64(0)
                    first_frontier_out[lane, 0, 3] = ti.u64(0)
                    first_frontier_out[lane, 0, 4] = ti.u64(zero_body_fever)
                    first_frontier_out[lane, 0, 5] = ti.u64(0)
                    first_frontier_out[lane, 0, 6] = ti.u64(0)
                    first_frontier_cnt[lane] = 1
                    out_counters[lane, 0] = 0
                    out_counters[lane, 1] = 0
                    out_counters[lane, 2] = 1
                    out_counters[lane, 3] = 1
                    took_fast_path = 1

        if took_fast_path == 0:
            # =============================================================== #
            # body_tails[n] = [(0,0,0)] (Numba :769).
            # =============================================================== #
            body_tails_cnt[lane, n] = 1
            body_tails_vals[lane, n * cap_bt + 0, 0] = ti.u64(0)
            body_tails_vals[lane, n * cap_bt + 0, 1] = ti.u64(0)
            body_tails_vals[lane, n * cap_bt + 0, 2] = ti.u64(0)

            # =============================================================== #
            # REACHABILITY (Numba :771-836).
            # =============================================================== #
            for s in range(n + 1):
                reachable[lane, s] = 0
            reachable[lane, n] = 1
            for action_idx in range(action_count):
                edge_e = _first_edge(
                    n, base + action_idx, first_fill_f, use_fgt,
                    timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                )
                if edge_e >= 0:
                    reachable[lane, edge_e] = 1
                av = _first_activation_edge(
                    n, base + action_idx, first_fill_f, first_activation_forced_f, use_fgt,
                    timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                )
                activation_e = av[0]
                if activation_e >= 0 and activation_e > edge_e:
                    reachable[lane, activation_e] = 1
            for state_i in range(n):
                if reachable[lane, state_i] != 0:
                    for action_idx in range(action_count):
                        edge_e = _later_edge(
                            n, state_i, base + action_idx, later_fill_f, use_fgt,
                            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                            real_time_idx,
                        )
                        if edge_e >= 0:
                            reachable[lane, edge_e] = 1
                        av = _later_activation_edge(
                            n, state_i, base + action_idx, later_fill_f, later_activation_forced_f, use_fgt,
                            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                            real_time_idx,
                        )
                        activation_e = av[0]
                        if activation_e >= 0 and activation_e > edge_e:
                            reachable[lane, activation_e] = 1

            states_evaluated = ti.i32(0)
            retained_total = ti.i32(1)
            max_state_frontier = ti.i32(1)
            generated_surfaces = ti.i32(0)

            # =============================================================== #
            # PHASE 1: body-skyline backward DP, state_i = n-1 .. 100 (Numba :853-977).
            # =============================================================== #
            for _rev in range(ti.max(0, n - 100)):
                state_i = n - 1 - _rev  # descends n-1 .. 100
                if reachable[lane, state_i] != 0:
                    states_evaluated += 1
                    generated_count = ti.i32(0)
                    touched_count = ti.i32(0)
                    pair_stamp_value += 1
                    prev_fill = ti.i32(-1)
                    prev_edge_e = ti.i32(-1)
                    prev_activation_fill = ti.i32(-1)
                    prev_activation_e = ti.i32(-1)
                    for action_idx in range(action_count):
                        fill = later_fill_f[base + action_idx]
                        edge_e = prev_edge_e
                        if fill != prev_fill:
                            edge_e = _later_edge(
                                n, state_i, base + action_idx, later_fill_f, use_fgt,
                                timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                                real_time_idx,
                            )
                        if edge_e >= 0:
                            forced_start = state_i + 1
                            if fill != prev_fill or edge_e != prev_edge_e:
                                prev_fill = fill
                                prev_edge_e = edge_e
                                edge = _pack_edge(
                                    n, state_i + fill, edge_e,
                                    forced_start, ti.min(n, forced_start + later_forced_f[base + action_idx]),
                                    -1,
                                )
                                tail_cnt = body_tails_cnt[lane, edge_e]
                                for tail_idx in range(tail_cnt):
                                    tf = ti.i32(body_tails_vals[lane, edge_e * cap_bt + tail_idx, 0])
                                    tg = ti.i32(body_tails_vals[lane, edge_e * cap_bt + tail_idx, 1])
                                    tfg = ti.i32(body_tails_vals[lane, edge_e * cap_bt + tail_idx, 2])
                                    touched_count = _touch_body_candidate(
                                        ti.i32(edge[4]), ti.i32(edge[5]), ti.i32(edge[6]),
                                        tf, tg, tfg,
                                        pair_mod, pair_stamp_value,
                                        pair_stamp, best_fever_by_pair, touched_pair,
                                        lane, touched_count, pair_size, error_flag,
                                    )
                                    generated_count += 1

                            av = _later_activation_edge(
                                n, state_i, base + action_idx, later_fill_f, later_activation_forced_f, use_fgt,
                                timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                                real_time_idx,
                            )
                            activation_e = av[0]
                            prefix_forced = av[1]
                            if activation_e >= 0 and activation_e > edge_e:
                                if not (fill == prev_activation_fill and activation_e == prev_activation_e):
                                    prev_activation_fill = fill
                                    prev_activation_e = activation_e
                                    activation_edge = _pack_edge(
                                        n, state_i + fill, activation_e,
                                        forced_start, ti.min(n, forced_start + prefix_forced),
                                        state_i + fill,
                                    )
                                    atail_cnt = body_tails_cnt[lane, activation_e]
                                    for tail_idx in range(atail_cnt):
                                        tf = ti.i32(body_tails_vals[lane, activation_e * cap_bt + tail_idx, 0])
                                        tg = ti.i32(body_tails_vals[lane, activation_e * cap_bt + tail_idx, 1])
                                        tfg = ti.i32(body_tails_vals[lane, activation_e * cap_bt + tail_idx, 2])
                                        touched_count = _touch_body_candidate(
                                            ti.i32(activation_edge[4]), ti.i32(activation_edge[5]),
                                            ti.i32(activation_edge[6]),
                                            tf, tg, tfg,
                                            pair_mod, pair_stamp_value,
                                            pair_stamp, best_fever_by_pair, touched_pair,
                                            lane, touched_count, pair_size, error_flag,
                                        )
                                        generated_count += 1

                    generated_surfaces += generated_count
                    # Reduce into body_tails[state_i].
                    if generated_count == 0:
                        body_tails_cnt[lane, state_i] = 1
                        body_tails_vals[lane, state_i * cap_bt + 0, 0] = ti.u64(0)
                        body_tails_vals[lane, state_i * cap_bt + 0, 1] = ti.u64(0)
                        body_tails_vals[lane, state_i * cap_bt + 0, 2] = ti.u64(0)
                    else:
                        bit_stamp_value += 1
                        _reduce_touched_body_pairs(
                            pair_mod, touched_pair, touched_count, best_fever_by_pair,
                            bit_values, bit_stamps, bit_stamp_value, bit_limit,
                            lane, red3_vals, red3_cnt,
                        )
                        m = red3_cnt[lane]
                        if m >= cap_bt:
                            error_flag[lane] = 1
                        body_tails_cnt[lane, state_i] = m
                        for k in range(m):
                            body_tails_vals[lane, state_i * cap_bt + k, 0] = red3_vals[lane, k, 0]
                            body_tails_vals[lane, state_i * cap_bt + k, 1] = red3_vals[lane, k, 1]
                            body_tails_vals[lane, state_i * cap_bt + k, 2] = red3_vals[lane, k, 2]
                    frontier_len = body_tails_cnt[lane, state_i]
                    retained_total += frontier_len
                    if frontier_len > max_state_frontier:
                        max_state_frontier = frontier_len

            # =============================================================== #
            # PHASE 2: head reduce, state_i = head_limit-1 .. 0 (Numba :979-1079).
            # =============================================================== #
            for _rev in range(head_limit):
                state_i = head_limit - 1 - _rev  # descends head_limit-1 .. 0
                if reachable[lane, state_i] != 0:
                    states_evaluated += 1
                    generated_count = ti.i32(0)
                    # bucket reset for this state's _reduce.
                    bkt_cnt[lane] = 0
                    prev_fill = ti.i32(-1)
                    prev_edge_e = ti.i32(-1)
                    prev_activation_fill = ti.i32(-1)
                    prev_activation_e = ti.i32(-1)
                    for action_idx in range(action_count):
                        fill = later_fill_f[base + action_idx]
                        edge_e = prev_edge_e
                        if fill != prev_fill:
                            edge_e = _later_edge(
                                n, state_i, base + action_idx, later_fill_f, use_fgt,
                                timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                                real_time_idx,
                            )
                        if edge_e >= 0:
                            forced_start = state_i + 1
                            if fill != prev_fill or edge_e != prev_edge_e:
                                prev_fill = fill
                                prev_edge_e = edge_e
                                edge = _pack_edge(
                                    n, state_i + fill, edge_e,
                                    forced_start, ti.min(n, forced_start + later_forced_f[base + action_idx]),
                                    -1,
                                )
                                generated_count += _emit_tail_surfaces(
                                    n, edge, edge_e, head_limit, lane, cap_bt, cap_head,
                                    body_tails_vals, body_tails_cnt, head_vals, head_cnt,
                                    bkt_vals, bkt_cnt, cap_head, error_flag,
                                )
                            av = _later_activation_edge(
                                n, state_i, base + action_idx, later_fill_f, later_activation_forced_f, use_fgt,
                                timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                                real_time_idx,
                            )
                            activation_e = av[0]
                            prefix_forced = av[1]
                            if activation_e >= 0 and activation_e > edge_e:
                                if not (fill == prev_activation_fill and activation_e == prev_activation_e):
                                    prev_activation_fill = fill
                                    prev_activation_e = activation_e
                                    activation_edge = _pack_edge(
                                        n, state_i + fill, activation_e,
                                        forced_start, ti.min(n, forced_start + prefix_forced),
                                        state_i + fill,
                                    )
                                    generated_count += _emit_tail_surfaces(
                                        n, activation_edge, activation_e, head_limit, lane, cap_bt, cap_head,
                                        body_tails_vals, body_tails_cnt, head_vals, head_cnt,
                                        bkt_vals, bkt_cnt, cap_head, error_flag,
                                    )
                    generated_surfaces += generated_count
                    # frontier = _numba_reduce(generated): bucket already holds reduced
                    # surfaces; empty -> single all-zero surface.
                    m = bkt_cnt[lane]
                    if m == 0:
                        head_cnt[lane, state_i] = 1
                        for col in ti.static(range(7)):
                            head_vals[lane, state_i * cap_head + 0, col] = ti.u64(0)
                    else:
                        if m > cap_head:
                            error_flag[lane] = 1
                        head_cnt[lane, state_i] = m
                        for k in range(m):
                            for col in ti.static(range(7)):
                                head_vals[lane, state_i * cap_head + k, col] = bkt_vals[lane, k, col]
                    frontier_len = head_cnt[lane, state_i]
                    retained_total += frontier_len
                    if frontier_len > max_state_frontier:
                        max_state_frontier = frontier_len

            # =============================================================== #
            # PHASE 3: first-frontier sweep (Numba :1081-1308).
            # =============================================================== #
            first_generated_count = ti.i32(0)
            if action_count > 0 and first_fill_f[base + 0] >= 100:
                # ---- BRANCH A (first_fill[0] >= 100): head_great_count 0..100. ----
                # bucket = first_frontier accumulator (persists across head counts).
                bkt_cnt[lane] = 0
                for head_great_count in range(101):
                    touched_count = ti.i32(0)
                    pair_stamp_value += 1
                    prev_fill = ti.i32(-1)
                    prev_edge_e = ti.i32(-1)
                    prev_activation_fill = ti.i32(-1)
                    prev_activation_e = ti.i32(-1)
                    for action_idx in range(action_count):
                        edge_e = _first_edge(
                            n, base + action_idx, first_fill_f, use_fgt,
                            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                        )
                        if edge_e >= 100:
                            normal_head_great = ti.min(100, ti.max(0, first_forced_f[base + action_idx]))
                            if normal_head_great == head_great_count:
                                fill = first_fill_f[base + action_idx]
                                if fill != prev_fill or edge_e != prev_edge_e:
                                    prev_fill = fill
                                    prev_edge_e = edge_e
                                    edge = _pack_edge(
                                        n, fill, edge_e,
                                        0, ti.min(n, first_forced_f[base + action_idx]),
                                        -1,
                                    )
                                    tail_cnt = body_tails_cnt[lane, edge_e]
                                    for tail_idx in range(tail_cnt):
                                        tf = ti.i32(body_tails_vals[lane, edge_e * cap_bt + tail_idx, 0])
                                        tg = ti.i32(body_tails_vals[lane, edge_e * cap_bt + tail_idx, 1])
                                        tfg = ti.i32(body_tails_vals[lane, edge_e * cap_bt + tail_idx, 2])
                                        touched_count = _touch_body_candidate(
                                            ti.i32(edge[4]), ti.i32(edge[5]), ti.i32(edge[6]),
                                            tf, tg, tfg,
                                            pair_mod, pair_stamp_value,
                                            pair_stamp, best_fever_by_pair, touched_pair,
                                            lane, touched_count, pair_size, error_flag,
                                        )
                                        first_generated_count += 1
                            av = _first_activation_edge(
                                n, base + action_idx, first_fill_f, first_activation_forced_f, use_fgt,
                                timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx,
                                real_time_idx,
                            )
                            activation_e = av[0]
                            prefix_forced = av[1]
                            if activation_e >= 100 and activation_e > edge_e:
                                activation_head_great = ti.min(100, ti.max(0, prefix_forced))
                                if activation_head_great == head_great_count:
                                    fill = first_fill_f[base + action_idx]
                                    if not (fill == prev_activation_fill and activation_e == prev_activation_e):
                                        prev_activation_fill = fill
                                        prev_activation_e = activation_e
                                        activation_edge = _pack_edge(
                                            n, fill, activation_e,
                                            0, ti.min(n, prefix_forced),
                                            fill,
                                        )
                                        atail_cnt = body_tails_cnt[lane, activation_e]
                                        for tail_idx in range(atail_cnt):
                                            tf = ti.i32(body_tails_vals[lane, activation_e * cap_bt + tail_idx, 0])
                                            tg = ti.i32(body_tails_vals[lane, activation_e * cap_bt + tail_idx, 1])
                                            tfg = ti.i32(body_tails_vals[lane, activation_e * cap_bt + tail_idx, 2])
                                            touched_count = _touch_body_candidate(
                                                ti.i32(activation_edge[4]), ti.i32(activation_edge[5]),
                                                ti.i32(activation_edge[6]),
                                                tf, tg, tfg,
                                                pair_mod, pair_stamp_value,
                                                pair_stamp, best_fever_by_pair, touched_pair,
                                                lane, touched_count, pair_size, error_flag,
                                            )
                                            first_generated_count += 1
                    if touched_count > 0:
                        bit_stamp_value += 1
                        _reduce_touched_body_pairs(
                            pair_mod, touched_pair, touched_count, best_fever_by_pair,
                            bit_values, bit_stamps, bit_stamp_value, bit_limit,
                            lane, red3_vals, red3_cnt,
                        )
                        bm = red3_cnt[lane]
                        for body_idx in range(bm):
                            bf = red3_vals[lane, body_idx, 0]
                            bg = red3_vals[lane, body_idx, 1]
                            bfg = red3_vals[lane, body_idx, 2]
                            surf = _body_prefix_surface(head_great_count, bf, bg, bfg)
                            _append_surface(bkt_vals, bkt_cnt, error_flag, lane, cap_ff, surf)
                # Copy first_frontier accumulator to output.
                m = bkt_cnt[lane]
                first_frontier_cnt[lane] = m
                for k in range(m):
                    for col in ti.static(range(7)):
                        first_frontier_out[lane, k, col] = bkt_vals[lane, k, col]
            else:
                # ---- BRANCH B (first_fill[0] < 100): combine first edges. ----
                bkt_cnt[lane] = 0
                prev_fill = ti.i32(-1)
                prev_edge_e = ti.i32(-1)
                prev_activation_fill = ti.i32(-1)
                prev_activation_e = ti.i32(-1)
                for action_idx in range(action_count):
                    edge_e = _first_edge(
                        n, base + action_idx, first_fill_f, use_fgt,
                        timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                    )
                    if edge_e >= 0:
                        fill = first_fill_f[base + action_idx]
                        if fill != prev_fill or edge_e != prev_edge_e:
                            prev_fill = fill
                            prev_edge_e = edge_e
                            edge = _pack_edge(
                                n, fill, edge_e,
                                0, ti.min(n, first_forced_f[base + action_idx]),
                                -1,
                            )
                            first_generated_count += _emit_tail_surfaces(
                                n, edge, edge_e, head_limit, lane, cap_bt, cap_head,
                                body_tails_vals, body_tails_cnt, head_vals, head_cnt,
                                bkt_vals, bkt_cnt, cap_ff, error_flag,
                            )
                        av = _first_activation_edge(
                            n, base + action_idx, first_fill_f, first_activation_forced_f, use_fgt,
                            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
                        )
                        activation_e = av[0]
                        prefix_forced = av[1]
                        if activation_e >= 0 and activation_e > edge_e:
                            if not (fill == prev_activation_fill and activation_e == prev_activation_e):
                                prev_activation_fill = fill
                                prev_activation_e = activation_e
                                activation_edge = _pack_edge(
                                    n, fill, activation_e,
                                    0, ti.min(n, prefix_forced),
                                    fill,
                                )
                                first_generated_count += _emit_tail_surfaces(
                                    n, activation_edge, activation_e, head_limit, lane, cap_bt, cap_head,
                                    body_tails_vals, body_tails_cnt, head_vals, head_cnt,
                                    bkt_vals, bkt_cnt, cap_ff, error_flag,
                                )
                # frontier = _numba_reduce(first_generated): empty -> single all-zero.
                m = bkt_cnt[lane]
                if m == 0:
                    first_frontier_cnt[lane] = 1
                    for col in ti.static(range(7)):
                        first_frontier_out[lane, 0, col] = ti.u64(0)
                else:
                    first_frontier_cnt[lane] = m
                    for k in range(m):
                        for col in ti.static(range(7)):
                            first_frontier_out[lane, k, col] = bkt_vals[lane, k, col]

            generated_surfaces += first_generated_count
            ff_len = first_frontier_cnt[lane]
            retained_total += ff_len
            if ff_len > max_state_frontier:
                max_state_frontier = ff_len

            out_counters[lane, 0] = states_evaluated
            out_counters[lane, 1] = generated_surfaces
            out_counters[lane, 2] = retained_total
            out_counters[lane, 3] = max_state_frontier


# =========================================================================== #
# HOST: cap sizing + batched launch + bit-exact comparison vs the Numba oracle.
# =========================================================================== #
def _pair_mod_for(n: int, action_count: int, later_fill0: int) -> int:
    # Numba :842-843. min_later_fill = max(1, later_fill[0] if action_count>0 else 1).
    min_later_fill = max(1, int(later_fill0) if int(action_count) > 0 else 1)
    return min(int(n) + 1, int(n) // int(min_later_fill) + 4)


def _run_batch(args_list, real_times_list, *, cap_bt, cap_head, cap_red3, cap_ff):
    """Run one GPU launch with one lane per geometry in ``args_list``.

    The geometries in a batch share the same SONG (timestamps +
    great_candidate_timestamps) but each has its own ``real_fever_time`` -> its
    own end-index table. To reproduce production batching, build ONE combined
    end-index table over all unique real times (exactly as
    ``_precompute_end_indices`` does in production), then give each lane its
    ``real_time_idx`` into that shared table. The per-real-time rows are bit-
    identical to each geometry's standalone single-real-time table, so the
    kernel resolves identical edges to the oracle. Returns a list of
    (out[m,7] uint64, [states_evaluated, generated_surfaces, retained_total,
    max_state_frontier], error_flag) per lane.
    """
    n_lanes = len(args_list)
    a0 = args_list[0]
    n = int(a0["n"])
    # Shared SONG (identical across the batch by construction).
    timestamps = np.ascontiguousarray(a0["timestamps"], dtype=np.float32)
    great_ts = np.ascontiguousarray(a0["great_candidate_timestamps"], dtype=np.float32)
    # Combined end-index tables over the batch's real times.
    real_times = np.asarray([float(rt) for rt in real_times_list], dtype=np.float32)
    real_time_index, timestamp_end_idx, great_end_idx = _precompute_end_indices(
        timestamps=timestamps,
        great_candidate_timestamps=great_ts,
        real_times=real_times,
    )
    timestamp_end_idx = np.ascontiguousarray(timestamp_end_idx, dtype=np.int32)
    great_end_idx = np.ascontiguousarray(great_end_idx, dtype=np.int32)
    R = int(timestamp_end_idx.shape[0])

    # Flatten per-lane action arrays with offsets.
    offsets = np.zeros(n_lanes, dtype=np.int32)
    counts = np.zeros(n_lanes, dtype=np.int32)
    n_arr = np.zeros(n_lanes, dtype=np.int32)
    rt_arr = np.zeros(n_lanes, dtype=np.int32)
    fgt_arr = np.zeros(n_lanes, dtype=np.int32)
    pairmod_arr = np.zeros(n_lanes, dtype=np.int32)
    flats = {k: [] for k in (
        "later_fill", "first_fill", "later_forced", "first_forced",
        "later_activation_forced", "first_activation_forced",
    )}
    running = 0
    for lane, a in enumerate(args_list):
        ac = int(a["action_count"])
        offsets[lane] = running
        counts[lane] = ac
        n_arr[lane] = int(a["n"])
        rt_arr[lane] = int(real_time_index[lane])  # index into the combined table
        fgt_arr[lane] = int(a["use_forced_great_timing_i"])
        lf0 = int(a["later_fill"][0]) if ac > 0 else 1
        pairmod_arr[lane] = _pair_mod_for(int(a["n"]), ac, lf0)
        for k in flats:
            flats[k].append(np.ascontiguousarray(a[k], dtype=np.int32))
        running += ac
    total_rows = max(1, running)
    flat_arrays = {}
    for k in flats:
        if flats[k] and running > 0:
            flat_arrays[k] = np.concatenate(flats[k]).astype(np.int32)
        else:
            flat_arrays[k] = np.zeros(1, dtype=np.int32)
        if flat_arrays[k].shape[0] < total_rows:
            flat_arrays[k] = np.concatenate(
                [flat_arrays[k], np.zeros(total_rows - flat_arrays[k].shape[0], dtype=np.int32)]
            )

    nmax1 = n + 1
    pair_size_cap = int(pairmod_arr.max()) * nmax1
    pairmod1_cap = int(pairmod_arr.max()) + 1

    # Scratch.
    reachable = np.zeros((n_lanes, nmax1), dtype=np.int32)
    best_body = np.zeros((n_lanes, nmax1), dtype=np.int32)
    body_tails_vals = np.zeros((n_lanes, nmax1 * cap_bt, 3), dtype=np.uint64)
    body_tails_cnt = np.zeros((n_lanes, nmax1), dtype=np.int32)
    head_vals = np.zeros((n_lanes, max(1, min(n, 100)) * cap_head, 7), dtype=np.uint64)
    head_cnt = np.zeros((n_lanes, max(1, min(n, 100))), dtype=np.int32)
    red3_vals = np.zeros((n_lanes, cap_red3, 3), dtype=np.uint64)
    red3_cnt = np.zeros((n_lanes,), dtype=np.int32)
    bkt_vals = np.zeros((n_lanes, cap_ff, 7), dtype=np.uint64)
    bkt_cnt = np.zeros((n_lanes,), dtype=np.int32)
    best_fever_by_pair = np.zeros((n_lanes, max(1, pair_size_cap)), dtype=np.int32)
    pair_stamp = np.zeros((n_lanes, max(1, pair_size_cap)), dtype=np.int32)
    touched_pair = np.zeros((n_lanes, max(1, pair_size_cap)), dtype=np.int32)
    bit_values = np.zeros((n_lanes, max(1, pairmod1_cap)), dtype=np.int32)
    bit_stamps = np.zeros((n_lanes, max(1, pairmod1_cap)), dtype=np.int32)

    first_frontier_out = np.zeros((n_lanes, cap_ff, 7), dtype=np.uint64)
    first_frontier_cnt = np.zeros((n_lanes,), dtype=np.int32)
    out_counters = np.zeros((n_lanes, 4), dtype=np.int32)
    error_flag = np.zeros((n_lanes,), dtype=np.int32)

    first_frontier_kernel(
        n_lanes, pair_size_cap, pairmod1_cap, cap_bt, cap_head, cap_red3, cap_ff,
        flat_arrays["later_fill"], flat_arrays["first_fill"],
        flat_arrays["later_forced"], flat_arrays["first_forced"],
        flat_arrays["later_activation_forced"], flat_arrays["first_activation_forced"],
        offsets, counts, n_arr, rt_arr, fgt_arr, pairmod_arr,
        timestamps, great_ts, timestamp_end_idx, great_end_idx,
        reachable, best_body,
        body_tails_vals, body_tails_cnt, head_vals, head_cnt,
        red3_vals, red3_cnt, bkt_vals, bkt_cnt,
        best_fever_by_pair, pair_stamp, touched_pair, bit_values, bit_stamps,
        first_frontier_out, first_frontier_cnt, out_counters, error_flag,
    )
    ti.sync()

    results = []
    for lane in range(n_lanes):
        m = int(first_frontier_cnt[lane])
        out = np.array(first_frontier_out[lane, :m, :], dtype=np.uint64)
        results.append((out, [int(x) for x in out_counters[lane]], int(error_flag[lane])))
    return results


# =========================================================================== #
# Synthetic song / geometry generation.
# =========================================================================== #
def _make_song(rng, n, *, great_later=True):
    """Sorted timestamps + (optionally) later great_candidate_timestamps.

    great_candidate_timestamps strictly later than timestamps exercises the
    activation-edge branches (use_forced_great_timing). Returns (ts, great_ts).
    """
    gaps = rng.uniform(0.02, 0.2, size=n).astype(np.float32)
    ts = np.cumsum(gaps).astype(np.float32)
    if great_later:
        # Push great candidates a bit later (still monotone-ish per index).
        bump = rng.uniform(0.0, 0.12, size=n).astype(np.float32)
        great_ts = (ts + bump).astype(np.float32)
    else:
        great_ts = ts.copy()
    return ts, great_ts


def _regime_of(args):
    ac = int(args["action_count"])
    if ac == 0:
        return "empty_actions"
    return "ge100" if int(args["first_fill"][0]) >= 100 else "lt100"


def _is_fast_path(args, oracle_out, counters):
    # Fast path => single body row (only col 4 set) AND counters (0,0,1,1).
    if int(args["action_count"]) <= 0 or int(args["first_fill"][0]) < 100:
        return False
    if counters != [0, 0, 1, 1]:
        return False
    if oracle_out.shape[0] != 1:
        return False
    row = oracle_out[0]
    return bool(row[0] == 0 and row[1] == 0 and row[2] == 0 and row[3] == 0
                and row[5] == 0 and row[6] == 0)


def main():
    arch = str(ti.cfg.arch)
    print(f"[probe] Taichi arch = {arch}")
    if "vulkan" not in arch.lower():
        print("LAYER 3 PARITY: FAIL (not on Vulkan GPU backend)")
        sys.exit(1)

    rng = np.random.default_rng(20260602)

    # Songs: vary n incl. n<100 edge; great candidates later to exercise activation.
    song_ns = [int(x) for x in os.environ.get("L3_SONG_NS", "40,90,130,300,600").split(",")]
    # raw_fever_fill range gives first_fill[0] both <100 and >=100.
    raw_fills = [20, 40, 60, 75, 88, 96, 100, 108, 120, 140]
    bases = [4, 6, 8, 10, 12]
    real_times = [1.0, 1.4, 1.8, 2.2, 2.5]

    # Cap sizing rationale (host-chosen, generous for the exact/memory-heavy
    # parity mode; memory compaction is a LATER step). All caps are sentinel-
    # guarded: a genuine overflow trips error_flag[lane] and the probe FAILS, so
    # under-sizing can never produce a false PASS.
    #   cap_bt   : max body-frontier rows stored per state (body_tails[state]).
    #              Bounded by distinct (normal_great, fever_great) pairs surviving
    #              the Fenwick skyline; small in practice. 256 is generous.
    #   cap_red3 : reducer sink for one state's body frontier. == cap_bt ceiling.
    #   cap_head : max head-frontier (dominance survivors) per state. Surface sets
    #              grow with n; size proportional to n (observed max_state_frontier
    #              ~754 at n=130). 16*n + 1024 is comfortably generous.
    #   cap_ff   : first-frontier / dominance bucket capacity. Same scale as head.
    # These are per-call; _run_batch sizes its buffers from them.

    total_geoms = 0
    total_mismatch = 0
    regimes = {"lt100": 0, "ge100": 0, "empty_actions": 0}
    fast_path_hits = 0
    first_mismatch = None

    for n in song_ns:
        great_later = True
        ts, great_ts = _make_song(rng, n, great_later=great_later)

        # Per-song caps (scale the surface-set buffers with n). cap_head is the
        # PER-HEAD-STATE storage and is multiplied by min(n,100) head states, so
        # it dominates memory -> keep it modest. cap_ff (final first-frontier +
        # dominance bucket) is the one that must be large (observed ~754 @ n=130).
        # All caps are sentinel-guarded; under-sizing trips error_flag -> FAIL.
        CAP_BT = 256
        CAP_RED3 = 256
        CAP_HEAD = 4 * n + 512
        CAP_FF = 16 * n + 2048

        # Build the full geometry sweep for this song.
        geom_args = []
        geom_meta = []  # (raw, base, rt)
        for raw in raw_fills:
            for base_v in bases:
                for rt in real_times:
                    a = build_kernel_args(
                        timestamps=ts,
                        great_candidate_timestamps=great_ts,
                        raw_fever_fill=float(raw),
                        non_fever_base=int(base_v),
                        real_fever_time=float(rt),
                        use_forced_great_timing=True,
                    )
                    geom_args.append(a)
                    geom_meta.append((raw, base_v, rt))

        # Oracle per geometry.
        oracle = [numba_first_frontier(a) for a in geom_args]

        # Batch GPU launch (one lane per geometry). Chunk to bound device memory:
        # the dense scratch is ~O(n) MB per lane, so shrink the lane count as n
        # grows (the kernel still runs all geometries; just in more launches).
        CHUNK = max(8, min(96, 6_000_000 // max(1, (min(n, 100) * CAP_HEAD + n * CAP_BT * 3))))
        gpu_results = []
        for s in range(0, len(geom_args), CHUNK):
            chunk = geom_args[s:s + CHUNK]
            chunk_rt = [m[2] for m in geom_meta[s:s + CHUNK]]  # real_fever_time per geom
            gpu_results.extend(
                _run_batch(chunk, chunk_rt, cap_bt=CAP_BT, cap_head=CAP_HEAD, cap_red3=CAP_RED3, cap_ff=CAP_FF)
            )

        for gi, (a, (g_out, g_counts, g_err)) in enumerate(zip(geom_args, gpu_results)):
            o_out, o_se, o_gs, o_rt, o_msf = oracle[gi]
            o_counts = [int(o_se), int(o_gs), int(o_rt), int(o_msf)]
            total_geoms += 1
            regimes[_regime_of(a)] += 1
            if _is_fast_path(a, np.asarray(o_out, dtype=np.uint64), o_counts):
                fast_path_hits += 1

            if g_err != 0:
                total_mismatch += 1
                if first_mismatch is None:
                    first_mismatch = ("error_flag", n, geom_meta[gi], g_err)
                continue

            o_arr = np.asarray(o_out, dtype=np.uint64).reshape(-1, 7)
            g_arr = np.asarray(g_out, dtype=np.uint64).reshape(-1, 7)
            ok_rows = (o_arr.shape == g_arr.shape) and bool(np.array_equal(o_arr, g_arr))
            ok_counts = (g_counts == o_counts)
            if not (ok_rows and ok_counts):
                total_mismatch += 1
                if first_mismatch is None:
                    first_mismatch = (
                        "mismatch", n, geom_meta[gi],
                        {"gpu_rows": g_arr.tolist(), "oracle_rows": o_arr.tolist(),
                         "gpu_counts": g_counts, "oracle_counts": o_counts},
                    )

    print(
        f"[probe] songs={len(song_ns)} geometries={total_geoms} mismatches={total_mismatch}"
    )
    print(
        f"[probe] regimes: lt100={regimes['lt100']} ge100={regimes['ge100']} "
        f"empty_actions={regimes['empty_actions']} | fast_path_hits={fast_path_hits}"
    )

    if total_mismatch != 0:
        print("FIRST MISMATCH:")
        kind = first_mismatch[0]
        if kind == "error_flag":
            _, n, meta, err = first_mismatch
            print(f"  error_flag set: n={n} geom(raw,base,rt)={meta} err={err}")
        else:
            _, n, meta, detail = first_mismatch
            print(f"  n={n} geom(raw,base,rt)={meta}")
            print(f"  gpu_counts   = {detail['gpu_counts']}")
            print(f"  oracle_counts= {detail['oracle_counts']}")
            print(f"  gpu_rows   = {detail['gpu_rows']}")
            print(f"  oracle_rows= {detail['oracle_rows']}")
        print("LAYER 3 PARITY: FAIL")
        sys.exit(1)

    # Coverage gate: both regimes AND the fast path must have been exercised.
    if regimes["lt100"] == 0 or regimes["ge100"] == 0 or fast_path_hits == 0:
        print("LAYER 3 PARITY: WEAK (a required regime or the fast path was not exercised)")
        print(f"  lt100={regimes['lt100']} ge100={regimes['ge100']} fast_path={fast_path_hits}")
        sys.exit(1)

    print(
        f"LAYER 3 PARITY: PASS  (songs={len(song_ns)}, geometries={total_geoms}, "
        f"lt100={regimes['lt100']}, ge100={regimes['ge100']}, fast_path={fast_path_hits})"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
