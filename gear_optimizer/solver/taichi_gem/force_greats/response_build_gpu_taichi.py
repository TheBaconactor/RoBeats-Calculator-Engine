"""Taichi/Vulkan port of the FG first-frontier construction kernel.

Bit-exact reimplementation of the Numba reference
``response_build_gpu_numba._first_frontier_from_precomputed_end_indices_numba``,
built to keep the RX 7900 XTX saturated by running one ``(ft,ff)`` geometry key
per GPU lane (see docs/Implementation Records/FG_FRONTIER_VULKAN_PORT.md).

The Numba kernel remains the canonical parity ORACLE; this module must reproduce
its output bit-for-bit. Surfaces use the identical 7x uint64 representation as
Numba's ``UniTuple(uint64, 7)``:
    (fever_lo, fever_hi, great_lo, great_hi, body_fever, body_great, body_fever_great)
Head masks cover note indices [0,100); body fields are counts.

WORK IN PROGRESS: Layer 1 (leaf @ti.func helpers). Reductions and the per-lane
kernel land in later layers.

Note: this module must NOT use ``from __future__ import annotations`` — Taichi
introspects real type objects from the annotations (``ti.i32`` etc.), and
stringized annotations break ``@ti.func``/``@ti.kernel`` argument typing.
"""

import taichi as ti

vec2u64 = ti.types.vector(2, ti.u64)
vec7u64 = ti.types.vector(7, ti.u64)
vec2i32 = ti.types.vector(2, ti.i32)


# --------------------------------------------------------------------------- #
# Head/body mask + count primitives (head region = note indices [0,100)).
# --------------------------------------------------------------------------- #
@ti.func
def _mask_segment(start: ti.i32, end: ti.i32, offset: ti.i32) -> ti.u64:
    # Numba _numba_mask_segment (response_build_gpu_numba.py:10-19).
    lo = ti.max(start, offset)
    hi = ti.min(end, offset + 64)
    result = ti.u64(0)
    if hi > lo:
        width = hi - lo
        if width >= 64:
            result = ti.u64(0xFFFFFFFFFFFFFFFF)
        else:
            result = ((ti.u64(1) << ti.u64(width)) - ti.u64(1)) << ti.u64(lo - offset)
    return result


@ti.func
def _range_mask(start: ti.i32, end: ti.i32, n: ti.i32) -> vec2u64:
    # Numba _numba_range_mask (:22-26).
    start_i = ti.max(0, ti.min(ti.min(start, n), 100))
    end_i = ti.max(0, ti.min(ti.min(end, n), 100))
    return vec2u64(_mask_segment(start_i, end_i, 0), _mask_segment(start_i, end_i, 64))


@ti.func
def _body_count(start: ti.i32, end: ti.i32, n: ti.i32) -> ti.u64:
    # Numba _numba_body_count (:29-35).
    body_start = ti.max(start, 100)
    body_end = ti.min(end, n)
    result = ti.u64(0)
    if body_end > body_start:
        result = ti.u64(body_end - body_start)
    return result


@ti.func
def _body_overlap_count(
    first_start: ti.i32, first_end: ti.i32, second_start: ti.i32, second_end: ti.i32, n: ti.i32
) -> ti.u64:
    # Numba _numba_body_overlap_count (:38-44).
    body_start = ti.max(ti.max(first_start, second_start), 100)
    body_end = ti.min(ti.min(first_end, second_end), n)
    result = ti.u64(0)
    if body_end > body_start:
        result = ti.u64(body_end - body_start)
    return result


@ti.func
def _single_head_mask(idx: ti.i32, n: ti.i32) -> vec2u64:
    # Numba _numba_single_head_mask (:47-54).
    lo = ti.u64(0)
    hi = ti.u64(0)
    if 0 <= idx < ti.min(n, 100):
        if idx < 64:
            lo = ti.u64(1) << ti.u64(idx)
        else:
            hi = ti.u64(1) << ti.u64(idx - 64)
    return vec2u64(lo, hi)


@ti.func
def _prefix_head_great_mask(count: ti.i32) -> vec2u64:
    # Numba _numba_prefix_head_great_mask (:174-179).
    clipped = ti.max(0, ti.min(count, 100))
    return vec2u64(_mask_segment(0, ti.min(clipped, 64), 0), _mask_segment(64, clipped, 64))


# --------------------------------------------------------------------------- #
# Edge packing.
# --------------------------------------------------------------------------- #
@ti.func
def _pack_edge(
    n: ti.i32,
    fever_start: ti.i32,
    fever_end: ti.i32,
    great_start: ti.i32,
    great_end: ti.i32,
    activation_great_idx: ti.i32,
) -> vec7u64:
    # Numba _numba_pack_edge (:57-89).
    fm = _range_mask(fever_start, fever_end, n)
    gm = _range_mask(great_start, great_end, n)
    great_lo = gm[0]
    great_hi = gm[1]
    if activation_great_idx >= 0:
        am = _single_head_mask(activation_great_idx, n)
        great_lo = great_lo | am[0]
        great_hi = great_hi | am[1]
    body_great = _body_count(great_start, great_end, n)
    body_fever_great = _body_overlap_count(fever_start, fever_end, great_start, great_end, n)
    if (
        activation_great_idx >= ti.max(100, fever_start)
        and activation_great_idx < ti.min(fever_end, n)
        and (activation_great_idx < great_start or activation_great_idx >= great_end)
    ):
        body_great = body_great + ti.u64(1)
        body_fever_great = body_fever_great + ti.u64(1)
    return vec7u64(
        fm[0], fm[1], great_lo, great_hi, _body_count(fever_start, fever_end, n), body_great, body_fever_great
    )


@ti.func
def _body_prefix_surface(
    head_great_count: ti.i32, body_fever: ti.u64, body_great: ti.u64, body_fever_great: ti.u64
) -> vec7u64:
    # Numba _numba_body_prefix_surface (:182-193).
    gm = _prefix_head_great_mask(head_great_count)
    return vec7u64(ti.u64(0), ti.u64(0), gm[0], gm[1], body_fever, body_great, body_fever_great)


# --------------------------------------------------------------------------- #
# Edge-end resolution from precomputed searchsorted tables.
# The Numba twins also return ``start_time``; every caller discards it, so the
# port returns only ``edge_e`` (and ``prefix_forced`` for activation edges).
# --------------------------------------------------------------------------- #
@ti.func
def _edge_end_idx(
    n: ti.i32,
    activation_idx: ti.i32,
    activation_great_i: ti.i32,
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    real_time_idx: ti.i32,
) -> ti.i32:
    # Numba _numba_edge_end_idx_precomputed (:329-352). start_time is internal.
    start_time = timestamps[activation_idx]
    edge_e = ti.i32(timestamp_end_idx[real_time_idx, activation_idx])
    if use_forced_great_timing_i != 0 and activation_great_i != 0 and activation_idx < n:
        activation_t = great_candidate_timestamps[activation_idx]
        if activation_t > start_time:
            edge_e = ti.i32(great_end_idx[real_time_idx, activation_idx])
    if edge_e <= activation_idx:
        edge_e = activation_idx + 1
    if edge_e > n:
        edge_e = n
    return edge_e


@ti.func
def _later_edge(
    n: ti.i32,
    state_i: ti.i32,
    action_idx: ti.i32,
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    real_time_idx: ti.i32,
) -> ti.i32:
    # Numba _numba_later_edge_from_precomputed (:355-384).
    edge_e = ti.i32(-1)
    activation = state_i + ti.i32(later_fill[action_idx])
    if activation < n:
        edge_e = _edge_end_idx(
            n, activation, 0, use_forced_great_timing_i,
            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
        )
    return edge_e


@ti.func
def _first_edge(
    n: ti.i32,
    action_idx: ti.i32,
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    real_time_idx: ti.i32,
) -> ti.i32:
    # Numba _numba_first_edge_from_precomputed (:387-414).
    edge_e = ti.i32(-1)
    fill = ti.i32(first_fill[action_idx])
    if fill < n:
        edge_e = _edge_end_idx(
            n, fill, 0, use_forced_great_timing_i,
            timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
        )
    return edge_e


@ti.func
def _later_activation_edge(
    n: ti.i32,
    state_i: ti.i32,
    action_idx: ti.i32,
    later_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    later_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    real_time_idx: ti.i32,
) -> vec2i32:
    # Numba _numba_later_activation_edge_from_precomputed (:417-449). Returns (edge_e, prefix_forced).
    edge_e = ti.i32(-1)
    prefix_forced = ti.i32(later_activation_forced[action_idx])
    out_prefix = ti.i32(0)
    if use_forced_great_timing_i != 0 and prefix_forced >= 0:
        activation = state_i + ti.i32(later_fill[action_idx])
        if activation < n:
            edge_e = _edge_end_idx(
                n, activation, 1, use_forced_great_timing_i,
                timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
            )
            out_prefix = prefix_forced
    return vec2i32(edge_e, out_prefix)


@ti.func
def _first_activation_edge(
    n: ti.i32,
    action_idx: ti.i32,
    first_fill: ti.types.ndarray(dtype=ti.i32, ndim=1),
    first_activation_forced: ti.types.ndarray(dtype=ti.i32, ndim=1),
    use_forced_great_timing_i: ti.i32,
    timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    great_candidate_timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1),
    timestamp_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    great_end_idx: ti.types.ndarray(dtype=ti.i32, ndim=2),
    real_time_idx: ti.i32,
) -> vec2i32:
    # Numba _numba_first_activation_edge_from_precomputed (:452-482). Returns (edge_e, prefix_forced).
    edge_e = ti.i32(-1)
    prefix_forced = ti.i32(first_activation_forced[action_idx])
    out_prefix = ti.i32(0)
    if use_forced_great_timing_i != 0 and prefix_forced >= 0:
        activation = ti.i32(first_fill[action_idx])
        if activation < n:
            edge_e = _edge_end_idx(
                n, activation, 1, use_forced_great_timing_i,
                timestamps, great_candidate_timestamps, timestamp_end_idx, great_end_idx, real_time_idx,
            )
            out_prefix = prefix_forced
    return vec2i32(edge_e, out_prefix)


# --------------------------------------------------------------------------- #
# Layer 2a: body-skyline reduction (touch + stamped-Fenwick skyline).
# Lane-indexed scratch: arrays are [n_lanes, capacity]; each @ti.func takes the
# array + a `lane` index. DENSE/EXACT layout (pair_size = (n+1)*pair_mod) for
# parity; memory compaction is a later, parity-preserving step.
#
# DEVICE-SCRATCH CONTRACT: Taichi pools/reuses device ndarrays across launches
# (NOT zero-initialized). The kernel MUST reset every read-before-write scratch
# slot per lane at the top of each lane (error_flag, frontier_count, and the
# stamp arrays unless a globally-monotonic stamp scheme is used).
# --------------------------------------------------------------------------- #
@ti.func
def _prefix_max_query_stamped(
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    lane: ti.i32,
    stamp: ti.i32,
    idx: ti.i32,
) -> ti.i32:
    # Numba _numba_prefix_max_query_stamped (:236-246). 1-indexed Fenwick PREFIX-MAX
    # over [0..idx]; -1 for an empty (all-stale) prefix; only stamp==stamp entries count.
    best = ti.i32(-1)
    cursor = idx + 1
    while cursor > 0:
        if bit_stamps[lane, cursor] == stamp:
            value = bit_values[lane, cursor]
            if value > best:
                best = value
        cursor -= cursor & (-cursor)
    return best


@ti.func
def _prefix_max_update_stamped(
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    lane: ti.i32,
    stamp: ti.i32,
    idx: ti.i32,
    value: ti.i32,
    limit: ti.i32,
):
    # Numba _numba_prefix_max_update_stamped (:249-259). Fenwick point-update max.
    # ``limit`` = Fenwick width = bit_values.shape[1] = pair_mod+1.
    cursor = idx + 1
    while cursor < limit:
        if bit_stamps[lane, cursor] != stamp:
            bit_stamps[lane, cursor] = stamp
            bit_values[lane, cursor] = value
        elif value > bit_values[lane, cursor]:
            bit_values[lane, cursor] = value
        cursor += cursor & (-cursor)


@ti.func
def _touch_body_candidate(
    edge_fever: ti.i32,
    edge_great: ti.i32,
    edge_fever_great: ti.i32,
    tail_fever: ti.i32,
    tail_great: ti.i32,
    tail_fever_great: ti.i32,
    pair_mod: ti.i32,
    stamp: ti.i32,
    pair_stamp: ti.types.ndarray(dtype=ti.i32, ndim=2),
    best_fever_by_pair: ti.types.ndarray(dtype=ti.i32, ndim=2),
    touched_pair: ti.types.ndarray(dtype=ti.i32, ndim=2),
    lane: ti.i32,
    touched_count: ti.i32,
    pair_size: ti.i32,
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
) -> ti.i32:
    # Numba _numba_touch_body_candidate (:262-293). Keeps MAX body_fever per
    # (normal_great, fever_great) pair via epoch stamping; drops body_fever_great
    # > body_great. FAIL-LOUD: Numba RAISES on out-of-bounds pair_idx; GPU sets
    # error_flag[lane]=1 (host must inspect after the launch and raise).
    body_fever = edge_fever + tail_fever
    body_great = edge_great + tail_great
    body_fever_great = edge_fever_great + tail_fever_great
    result = touched_count
    if body_fever_great > body_great:
        result = touched_count
    else:
        normal_great = body_great - body_fever_great
        pair_idx = normal_great * pair_mod + body_fever_great
        if pair_idx < 0 or pair_idx >= pair_size:
            error_flag[lane] = 1
            result = touched_count
        elif pair_stamp[lane, pair_idx] != stamp:
            pair_stamp[lane, pair_idx] = stamp
            best_fever_by_pair[lane, pair_idx] = body_fever
            touched_pair[lane, touched_count] = pair_idx
            result = touched_count + 1
        else:
            if body_fever > best_fever_by_pair[lane, pair_idx]:
                best_fever_by_pair[lane, pair_idx] = body_fever
            result = touched_count
    return result


@ti.func
def _reduce_touched_body_pairs(
    pair_mod: ti.i32,
    touched_pair: ti.types.ndarray(dtype=ti.i32, ndim=2),
    touched_count: ti.i32,
    best_fever_by_pair: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamp: ti.i32,
    bit_limit: ti.i32,
    lane: ti.i32,
    frontier: ti.types.ndarray(dtype=ti.u64, ndim=3),
    frontier_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
) -> ti.i32:
    # Numba _numba_reduce_touched_body_pairs (:296-326). Ascending sort of touched
    # pair indices, coalesce dups, emit (body_fever, normal_great+fever_great,
    # fever_great) iff best_fever > prefix_max (STRICT >). Emission order = ascending
    # pair_idx. Within one epoch all touched pair indices are distinct.
    out_count = ti.i32(0)
    if touched_count > 0:
        for i in range(1, touched_count):
            key = touched_pair[lane, i]
            j = i - 1
            while j >= 0 and touched_pair[lane, j] > key:
                touched_pair[lane, j + 1] = touched_pair[lane, j]
                j -= 1
            touched_pair[lane, j + 1] = key

        idx = 0
        while idx < touched_count:
            pair_idx = touched_pair[lane, idx]
            normal_great = pair_idx // pair_mod
            fever_great = pair_idx - normal_great * pair_mod
            best_fever = best_fever_by_pair[lane, pair_idx]
            idx += 1
            while idx < touched_count and touched_pair[lane, idx] == pair_idx:
                idx += 1
            prev = _prefix_max_query_stamped(bit_values, bit_stamps, lane, bit_stamp, fever_great)
            if best_fever > prev:
                frontier[lane, out_count, 0] = ti.u64(best_fever)
                frontier[lane, out_count, 1] = ti.u64(normal_great + fever_great)
                frontier[lane, out_count, 2] = ti.u64(fever_great)
                out_count += 1
            _prefix_max_update_stamped(
                bit_values, bit_stamps, lane, bit_stamp, fever_great, best_fever, bit_limit
            )
    frontier_count[lane] = out_count
    return out_count


# --------------------------------------------------------------------------- #
# Layer 2b: non-monotone bidirectional dominance reduction over 7-u64 surfaces.
# Per-lane bucket scratch bucket[n_lanes, cap, 7] (u64) + bucket_count[n_lanes].
# --------------------------------------------------------------------------- #
@ti.func
def _append_surface(
    bucket: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bucket_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
    lane: ti.i32,
    cap: ti.i32,
    c: vec7u64,
) -> ti.i32:
    # Numba _numba_append_surface (:92-132). NON-MONOTONE bidirectional dominance.
    # Phase 1: drop c if any kept k dominates it. Phase 2: stable write-pointer
    # compaction dropping kept k that c dominates, then append c LAST. fever uses
    # subset toward the dominator, great toward the dominated; gated by exact_overlap.
    cf_lo = c[0]; cf_hi = c[1]; cg_lo = c[2]; cg_hi = c[3]
    cbf = c[4]; cbg = c[5]; cbfg = c[6]
    zero = ti.u64(0)
    original_len = bucket_count[lane]

    dominated = 0
    for idx in range(original_len):
        kf_lo = bucket[lane, idx, 0]; kf_hi = bucket[lane, idx, 1]
        kg_lo = bucket[lane, idx, 2]; kg_hi = bucket[lane, idx, 3]
        kbf = bucket[lane, idx, 4]; kbg = bucket[lane, idx, 5]; kbfg = bucket[lane, idx, 6]
        exact_overlap = (
            cbfg == kbfg
            and (cf_lo & cg_lo) == (kf_lo & kg_lo)
            and (cf_hi & cg_hi) == (kf_hi & kg_hi)
        )
        if (
            kbf >= cbf and kbg <= cbg and kbfg <= cbfg and exact_overlap
            and (cf_lo & ~kf_lo) == zero and (cf_hi & ~kf_hi) == zero
            and (kg_lo & ~cg_lo) == zero and (kg_hi & ~cg_hi) == zero
        ):
            dominated = 1

    new_count = original_len
    if dominated == 0:
        write = 0
        for idx in range(original_len):
            kf_lo = bucket[lane, idx, 0]; kf_hi = bucket[lane, idx, 1]
            kg_lo = bucket[lane, idx, 2]; kg_hi = bucket[lane, idx, 3]
            kbf = bucket[lane, idx, 4]; kbg = bucket[lane, idx, 5]; kbfg = bucket[lane, idx, 6]
            exact_overlap = (
                cbfg == kbfg
                and (cf_lo & cg_lo) == (kf_lo & kg_lo)
                and (cf_hi & cg_hi) == (kf_hi & kg_hi)
            )
            drop = (
                cbf >= kbf and cbg <= kbg and cbfg <= kbfg and exact_overlap
                and (kf_lo & ~cf_lo) == zero and (kf_hi & ~cf_hi) == zero
                and (cg_lo & ~kg_lo) == zero and (cg_hi & ~kg_hi) == zero
            )
            if drop == 0:
                if write != idx:
                    bucket[lane, write, 0] = kf_lo; bucket[lane, write, 1] = kf_hi
                    bucket[lane, write, 2] = kg_lo; bucket[lane, write, 3] = kg_hi
                    bucket[lane, write, 4] = kbf; bucket[lane, write, 5] = kbg
                    bucket[lane, write, 6] = kbfg
                write += 1
        if write >= cap:
            error_flag[lane] = 1
            new_count = write
        else:
            bucket[lane, write, 0] = cf_lo; bucket[lane, write, 1] = cf_hi
            bucket[lane, write, 2] = cg_lo; bucket[lane, write, 3] = cg_hi
            bucket[lane, write, 4] = cbf; bucket[lane, write, 5] = cbg
            bucket[lane, write, 6] = cbfg
            new_count = write + 1
    bucket_count[lane] = new_count
    return new_count


# --------------------------------------------------------------------------- #
# Layer 2c: COMPACT body-skyline (drop-in replacement for the dense touch+reduce).
# Avoids the O((n+1)*pair_mod) dense grid (which OOMs for low-FF/large-n keys and
# starves the GPU of resident lanes). Per-lane memory is O(cand_count): append
# candidates to `cand`, then merge-sort (scalable) + coalesce-MAX + Fenwick skyline.
# Bit-identical output to `_reduce_touched_body_pairs` (validated 9043 lanes).
# --------------------------------------------------------------------------- #
@ti.func
def _append_cand(
    cand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    lane: ti.i32,
    cc: ti.i32,
    pair_mod: ti.i32,
    edge_fever: ti.i32,
    edge_great: ti.i32,
    edge_fever_great: ti.i32,
    tail_fever: ti.i32,
    tail_great: ti.i32,
    tail_fever_great: ti.i32,
    cap_cand: ti.i32,
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
) -> ti.i32:
    body_fever = edge_fever + tail_fever
    body_great = edge_great + tail_great
    body_fever_great = edge_fever_great + tail_fever_great
    result = cc
    if body_fever_great > body_great:
        result = cc
    else:
        pair_idx = (body_great - body_fever_great) * pair_mod + body_fever_great
        if cc >= cap_cand:
            error_flag[lane] = 1
            result = cc
        else:
            cand[lane, cc, 0] = pair_idx
            cand[lane, cc, 1] = body_fever
            result = cc + 1
    return result


@ti.func
def _skyline_compact(
    cand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    scand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    cand_count: ti.i32,
    pair_mod: ti.i32,
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamp: ti.i32,
    bit_limit: ti.i32,
    lane: ti.i32,
    frontier: ti.types.ndarray(dtype=ti.u64, ndim=3),
    frontier_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    frontier_cap: ti.i32,
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
) -> ti.i32:
    # Bottom-up merge sort by column 0 (pair_idx), ascending; cand<->scand ping-pong.
    src_is_cand = 1
    width = ti.i32(1)
    while width < cand_count:
        lo = ti.i32(0)
        while lo < cand_count:
            mid = ti.min(lo + width, cand_count)
            hi = ti.min(lo + 2 * width, cand_count)
            i = lo
            j = mid
            k = lo
            while i < mid and j < hi:
                ai = cand[lane, i, 0] if src_is_cand == 1 else scand[lane, i, 0]
                aj = cand[lane, j, 0] if src_is_cand == 1 else scand[lane, j, 0]
                if ai <= aj:
                    if src_is_cand == 1:
                        scand[lane, k, 0] = cand[lane, i, 0]; scand[lane, k, 1] = cand[lane, i, 1]
                    else:
                        cand[lane, k, 0] = scand[lane, i, 0]; cand[lane, k, 1] = scand[lane, i, 1]
                    i += 1
                else:
                    if src_is_cand == 1:
                        scand[lane, k, 0] = cand[lane, j, 0]; scand[lane, k, 1] = cand[lane, j, 1]
                    else:
                        cand[lane, k, 0] = scand[lane, j, 0]; cand[lane, k, 1] = scand[lane, j, 1]
                    j += 1
                k += 1
            while i < mid:
                if src_is_cand == 1:
                    scand[lane, k, 0] = cand[lane, i, 0]; scand[lane, k, 1] = cand[lane, i, 1]
                else:
                    cand[lane, k, 0] = scand[lane, i, 0]; cand[lane, k, 1] = scand[lane, i, 1]
                i += 1
                k += 1
            while j < hi:
                if src_is_cand == 1:
                    scand[lane, k, 0] = cand[lane, j, 0]; scand[lane, k, 1] = cand[lane, j, 1]
                else:
                    cand[lane, k, 0] = scand[lane, j, 0]; cand[lane, k, 1] = scand[lane, j, 1]
                j += 1
                k += 1
            lo += 2 * width
        src_is_cand = 1 - src_is_cand
        width *= 2

    # Coalesce-MAX over equal pair_idx + stamped-Fenwick skyline (strict >, -1 sentinel).
    out_count = ti.i32(0)
    if cand_count > 0:
        idx = 0
        while idx < cand_count:
            pair_idx = cand[lane, idx, 0] if src_is_cand == 1 else scand[lane, idx, 0]
            best_fever = cand[lane, idx, 1] if src_is_cand == 1 else scand[lane, idx, 1]
            normal_great = pair_idx // pair_mod
            fever_great = pair_idx - normal_great * pair_mod
            idx += 1
            while idx < cand_count and (
                (cand[lane, idx, 0] if src_is_cand == 1 else scand[lane, idx, 0]) == pair_idx
            ):
                f = cand[lane, idx, 1] if src_is_cand == 1 else scand[lane, idx, 1]
                if f > best_fever:
                    best_fever = f
                idx += 1
            prev = _prefix_max_query_stamped(bit_values, bit_stamps, lane, bit_stamp, fever_great)
            if best_fever > prev:
                if out_count < frontier_cap:
                    frontier[lane, out_count, 0] = ti.u64(best_fever)
                    frontier[lane, out_count, 1] = ti.u64(normal_great + fever_great)
                    frontier[lane, out_count, 2] = ti.u64(fever_great)
                    out_count += 1
                else:
                    error_flag[lane] = 1
            _prefix_max_update_stamped(bit_values, bit_stamps, lane, bit_stamp, fever_great, best_fever, bit_limit)
    frontier_count[lane] = out_count
    return out_count
