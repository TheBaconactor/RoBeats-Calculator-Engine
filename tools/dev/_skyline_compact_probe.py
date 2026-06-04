"""Throwaway GPU parity probe: SCALABLE memory-compact FG body-skyline.

Goal
----
Replace the DENSE per-lane body-skyline grid in
``gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu_taichi.py``
(``_touch_body_candidate`` + ``_reduce_touched_body_pairs``, which allocate an
O((n+1)*pair_mod) dense grid per lane -> O(n^2) blowup for low-FF/large-n keys)
with a memory-compact, O(k log k) candidate-buffer + merge-sort skyline that is
BIT-IDENTICAL to the dense reduction.

Two new ``@ti.func`` are the deliverable (integration-ready, reuse the existing
Fenwick funcs ``_prefix_max_query_stamped`` / ``_prefix_max_update_stamped``):

    _append_cand(...)     -> append (pair_idx, body_fever) into cand[L, cap_cand, 2]
    _skyline_compact(...) -> merge-sort cand by pair_idx, coalesce-MAX body_fever,
                             stamped-Fenwick skyline -> frontier triples (u64)

Parity strategy
---------------
The DENSE path (``_touch_body_candidate`` + ``_reduce_touched_body_pairs``) is
ALREADY bit-exact vs the Numba oracle (proved by _layer2a_skyline_probe.py). So
this probe feeds the SAME candidate stream through BOTH GPU paths and asserts the
emitted frontier matches bit-exact (same triples, same order, same count) for
every lane. Dense == Numba and Compact == Dense  =>  Compact == Numba.

TDR SAFETY
----------
A long Vulkan dispatch (>~2s) trips the Windows watchdog and resets the driver.
This probe NEVER launches more than ``MAX_LANES_PER_LAUNCH`` (<=16) lanes per
kernel launch and keeps per-lane work O(k log k). All batches are chunked over
lanes. The merge sort is bottom-up (NOT insertion sort) so a single lane with
~50k candidates stays well sub-second.

Run:  python tools/dev/_skyline_compact_probe.py
"""

import os
import sys
import time

# Repo root on sys.path so the runtime/init helper imports cleanly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

# Init Taichi on the production Vulkan backend BEFORE anything touches the GPU.
init_taichi()

import taichi as ti  # noqa: E402

# Reuse the dense path verbatim as the reference oracle on-GPU. The
# response_build_gpu_taichi.py dev/reference module lives beside this probe under
# tools/dev/; ensure this directory is importable so the sibling module resolves.
sys.path.insert(0, os.path.dirname(__file__))
from response_build_gpu_taichi import (  # noqa: E402
    _prefix_max_query_stamped,
    _prefix_max_update_stamped,
    _reduce_touched_body_pairs,
    _touch_body_candidate,
)


# =========================================================================== #
# DELIVERABLE 1/2:  _append_cand
#
# Replaces _touch_body_candidate. NO dedup here (dedup/MAX happens in the
# skyline coalesce pass). Computes the same body_* sums + the same pair_idx
# encoding, drops body_fever_great > body_great, appends (pair_idx, body_fever)
# into the per-lane compact buffer cand[L, cap_cand, 2] at slot `cc`.
#
# FAIL-LOUD: GPU code cannot raise. On buffer overflow (cc >= cap_cand) set
# error_flag[lane] = 1 and return cc unchanged; the host MUST inspect
# error_flag after the launch and raise. (The dense twin raises on an
# out-of-bounds pair_idx; here the only unbounded resource is the candidate
# buffer, so that is what we guard.)
# =========================================================================== #
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
        # Same encoding as the dense path:
        #   normal_great = body_great - body_fever_great
        #   pair_idx     = normal_great * pair_mod + body_fever_great
        pair_idx = (body_great - body_fever_great) * pair_mod + body_fever_great
        if cc >= cap_cand:
            error_flag[lane] = 1
            result = cc
        else:
            cand[lane, cc, 0] = pair_idx
            cand[lane, cc, 1] = body_fever
            result = cc + 1
    return result


# =========================================================================== #
# DELIVERABLE 2/2:  _skyline_compact
#
# 1. SORT cand[lane, 0:cand_count] ascending by column 0 (pair_idx) using a
#    SCALABLE bottom-up MERGE SORT. Scratch buffer scand[L, cap_cand, 2] (i32)
#    is the ping-pong partner. After each merge pass the freshly-merged data
#    lives in the OTHER buffer; we track which buffer is "live" with src_is_cand
#    and copy back into cand only ONCE at the end if needed. O(k log k) work,
#    O(k) extra memory. NEVER insertion sort (O(k^2) would TDR for large k).
#
# 2. Single linear pass over the sorted buffer: for each run of equal pair_idx
#    take MAX body_fever (col 1); decode normal_great = pair_idx // pair_mod,
#    fever_great = pair_idx - normal_great*pair_mod; emit
#       frontier[lane, out, :] = (body_fever_max, normal_great+fever_great, fever_great)
#    as u64 iff  best_fever > _prefix_max_query_stamped(..., fever_great)
#    (STRICT >); then _prefix_max_update_stamped(..., fever_great, best_fever).
#    Write frontier_count[lane] = out.
#
# IDENTICAL output to the dense _reduce_touched_body_pairs:
#   - the per-run MAX over equal pair_idx == the dense grid's per-pair max-keeping;
#   - ascending pair_idx emission order is the same;
#   - the Fenwick (strict-`>`, -1 empty-prefix sentinel) is the same and reused.
# Order among equal pair_idx does NOT matter (we take their max), so merge-sort
# stability is irrelevant.
# =========================================================================== #
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
) -> ti.i32:
    # ---- Bottom-up merge sort by column 0 (pair_idx), ascending. ----------- #
    # `src_is_cand` tracks which buffer currently holds the data to be merged
    # into the other on the NEXT pass. Start: data is in `cand`.
    src_is_cand = 1
    width = ti.i32(1)
    while width < cand_count:
        # Merge adjacent runs of length `width` from src -> dst.
        lo = ti.i32(0)
        while lo < cand_count:
            mid = ti.min(lo + width, cand_count)
            hi = ti.min(lo + 2 * width, cand_count)
            i = lo
            j = mid
            k = lo
            # Two-way merge; tie-break i-first (stable), though stability is moot.
            while i < mid and j < hi:
                # Read keys from the live source buffer.
                ai = cand[lane, i, 0] if src_is_cand == 1 else scand[lane, i, 0]
                aj = cand[lane, j, 0] if src_is_cand == 1 else scand[lane, j, 0]
                if ai <= aj:
                    if src_is_cand == 1:
                        scand[lane, k, 0] = cand[lane, i, 0]
                        scand[lane, k, 1] = cand[lane, i, 1]
                    else:
                        cand[lane, k, 0] = scand[lane, i, 0]
                        cand[lane, k, 1] = scand[lane, i, 1]
                    i += 1
                else:
                    if src_is_cand == 1:
                        scand[lane, k, 0] = cand[lane, j, 0]
                        scand[lane, k, 1] = cand[lane, j, 1]
                    else:
                        cand[lane, k, 0] = scand[lane, j, 0]
                        cand[lane, k, 1] = scand[lane, j, 1]
                    j += 1
                k += 1
            while i < mid:
                if src_is_cand == 1:
                    scand[lane, k, 0] = cand[lane, i, 0]
                    scand[lane, k, 1] = cand[lane, i, 1]
                else:
                    cand[lane, k, 0] = scand[lane, i, 0]
                    cand[lane, k, 1] = scand[lane, i, 1]
                i += 1
                k += 1
            while j < hi:
                if src_is_cand == 1:
                    scand[lane, k, 0] = cand[lane, j, 0]
                    scand[lane, k, 1] = cand[lane, j, 1]
                else:
                    cand[lane, k, 0] = scand[lane, j, 0]
                    cand[lane, k, 1] = scand[lane, j, 1]
                j += 1
                k += 1
            lo += 2 * width
        # Merged data now lives in the OTHER buffer; flip and double the run.
        src_is_cand = 1 - src_is_cand
        width *= 2

    # ---- Coalesce-MAX + stamped-Fenwick skyline over the sorted buffer. ---- #
    out_count = ti.i32(0)
    if cand_count > 0:
        idx = 0
        while idx < cand_count:
            pair_idx = cand[lane, idx, 0] if src_is_cand == 1 else scand[lane, idx, 0]
            best_fever = cand[lane, idx, 1] if src_is_cand == 1 else scand[lane, idx, 1]
            normal_great = pair_idx // pair_mod
            fever_great = pair_idx - normal_great * pair_mod
            idx += 1
            # Coalesce the run of equal pair_idx, keeping MAX body_fever.
            while idx < cand_count and (
                (cand[lane, idx, 0] if src_is_cand == 1 else scand[lane, idx, 0]) == pair_idx
            ):
                f = cand[lane, idx, 1] if src_is_cand == 1 else scand[lane, idx, 1]
                if f > best_fever:
                    best_fever = f
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


# =========================================================================== #
# Probe kernels. Each launch handles <= MAX_LANES_PER_LAUNCH lanes (TDR-safe).
#
# Candidate input layout (host-built, shared by BOTH paths):
#   cand_in[lane, slot, 0..5] =
#     (edge_fever, edge_great, edge_fever_great, tail_fever, tail_great, tail_fever_great)
#   cand_count[lane] = number of valid candidate slots for that lane.
# =========================================================================== #
CAND_FIELDS = 6
MAX_LANES_PER_LAUNCH = 16


@ti.kernel
def _run_dense(
    n_lanes: ti.i32,
    pair_mod: ti.i32,
    pair_size: ti.i32,
    bit_limit: ti.i32,
    stamp: ti.i32,
    bit_stamp: ti.i32,
    cand_in: ti.types.ndarray(dtype=ti.i32, ndim=3),
    cand_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_stamp: ti.types.ndarray(dtype=ti.i32, ndim=2),
    best_fever_by_pair: ti.types.ndarray(dtype=ti.i32, ndim=2),
    touched_pair: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
    frontier: ti.types.ndarray(dtype=ti.u64, ndim=3),
    frontier_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for lane in range(n_lanes):
        error_flag[lane] = 0
        touched_count = ti.i32(0)
        c = cand_count[lane]
        for slot in range(c):
            touched_count = _touch_body_candidate(
                cand_in[lane, slot, 0],
                cand_in[lane, slot, 1],
                cand_in[lane, slot, 2],
                cand_in[lane, slot, 3],
                cand_in[lane, slot, 4],
                cand_in[lane, slot, 5],
                pair_mod,
                stamp,
                pair_stamp,
                best_fever_by_pair,
                touched_pair,
                lane,
                touched_count,
                pair_size,
                error_flag,
            )
        _reduce_touched_body_pairs(
            pair_mod,
            touched_pair,
            touched_count,
            best_fever_by_pair,
            bit_values,
            bit_stamps,
            bit_stamp,
            bit_limit,
            lane,
            frontier,
            frontier_count,
        )


@ti.kernel
def _run_compact(
    n_lanes: ti.i32,
    pair_mod: ti.i32,
    bit_limit: ti.i32,
    bit_stamp: ti.i32,
    cap_cand: ti.i32,
    cand_in: ti.types.ndarray(dtype=ti.i32, ndim=3),
    cand_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    cand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    scand: ti.types.ndarray(dtype=ti.i32, ndim=3),
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
    frontier: ti.types.ndarray(dtype=ti.u64, ndim=3),
    frontier_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for lane in range(n_lanes):
        error_flag[lane] = 0
        cc = ti.i32(0)
        c = cand_count[lane]
        for slot in range(c):
            cc = _append_cand(
                cand,
                lane,
                cc,
                pair_mod,
                cand_in[lane, slot, 0],
                cand_in[lane, slot, 1],
                cand_in[lane, slot, 2],
                cand_in[lane, slot, 3],
                cand_in[lane, slot, 4],
                cand_in[lane, slot, 5],
                cap_cand,
                error_flag,
            )
        _skyline_compact(
            cand,
            scand,
            cc,
            pair_mod,
            bit_values,
            bit_stamps,
            bit_stamp,
            bit_limit,
            lane,
            frontier,
            frontier_count,
        )


# =========================================================================== #
# Host helpers: chunked launches over lanes (TDR-safe, <=16 lanes/launch).
# Both paths receive the SAME cand_in / cand_count.
# =========================================================================== #
def _dense_frontiers(cand_in, cand_count, n, pair_mod, stamp, bit_stamp, cap):
    n_lanes = cand_in.shape[0]
    max_slots = cand_in.shape[1]
    pair_size = (n + 1) * pair_mod
    bit_limit = pair_mod + 1

    out_triples = [None] * n_lanes
    out_overflow = np.zeros(n_lanes, dtype=bool)

    for base in range(0, n_lanes, MAX_LANES_PER_LAUNCH):
        L = min(MAX_LANES_PER_LAUNCH, n_lanes - base)
        sub_cand = np.ascontiguousarray(cand_in[base:base + L])
        sub_count = np.ascontiguousarray(cand_count[base:base + L])

        g_pair_stamp = np.full((L, pair_size), -1, dtype=np.int32)
        g_best = np.zeros((L, pair_size), dtype=np.int32)
        g_touched = np.zeros((L, max(pair_size, 1)), dtype=np.int32)
        g_bit_values = np.zeros((L, bit_limit), dtype=np.int32)
        g_bit_stamps = np.full((L, bit_limit), -1, dtype=np.int32)
        g_error = np.zeros((L,), dtype=np.int32)
        g_frontier = np.zeros((L, cap, 3), dtype=np.uint64)
        g_fcount = np.zeros((L,), dtype=np.int32)

        _run_dense(
            L, pair_mod, pair_size, bit_limit, stamp, bit_stamp,
            sub_cand, sub_count,
            g_pair_stamp, g_best, g_touched, g_bit_values, g_bit_stamps, g_error,
            g_frontier, g_fcount,
        )
        ti.sync()

        for li in range(L):
            gc = int(g_fcount[li])
            out_triples[base + li] = [
                (int(g_frontier[li, k, 0]), int(g_frontier[li, k, 1]), int(g_frontier[li, k, 2]))
                for k in range(gc)
            ]
            out_overflow[base + li] = bool(g_error[li])

    return out_triples, out_overflow


def _compact_frontiers(cand_in, cand_count, n, pair_mod, bit_stamp, cap, cap_cand):
    n_lanes = cand_in.shape[0]
    bit_limit = pair_mod + 1

    out_triples = [None] * n_lanes
    out_overflow = np.zeros(n_lanes, dtype=bool)
    max_launch_time = 0.0

    for base in range(0, n_lanes, MAX_LANES_PER_LAUNCH):
        L = min(MAX_LANES_PER_LAUNCH, n_lanes - base)
        sub_cand = np.ascontiguousarray(cand_in[base:base + L])
        sub_count = np.ascontiguousarray(cand_count[base:base + L])

        g_cand = np.zeros((L, cap_cand, 2), dtype=np.int32)
        g_scand = np.zeros((L, cap_cand, 2), dtype=np.int32)
        g_bit_values = np.zeros((L, bit_limit), dtype=np.int32)
        g_bit_stamps = np.full((L, bit_limit), -1, dtype=np.int32)
        g_error = np.zeros((L,), dtype=np.int32)
        g_frontier = np.zeros((L, cap, 3), dtype=np.uint64)
        g_fcount = np.zeros((L,), dtype=np.int32)

        t0 = time.perf_counter()
        _run_compact(
            L, pair_mod, bit_limit, bit_stamp, cap_cand,
            sub_cand, sub_count,
            g_cand, g_scand, g_bit_values, g_bit_stamps, g_error,
            g_frontier, g_fcount,
        )
        ti.sync()
        dt = time.perf_counter() - t0
        if dt > max_launch_time:
            max_launch_time = dt

        for li in range(L):
            gc = int(g_fcount[li])
            out_triples[base + li] = [
                (int(g_frontier[li, k, 0]), int(g_frontier[li, k, 1]), int(g_frontier[li, k, 2]))
                for k in range(gc)
            ]
            out_overflow[base + li] = bool(g_error[li])

    return out_triples, out_overflow, max_launch_time


def _reuse_stress(rng, n, pair_mod, cap, cap_cand, n_launches):
    """Read-before-write hardening: drive the compact path over MANY sequential
    launches that REUSE one persistent set of device ndarrays, WITHOUT re-zeroing
    the candidate scratch (g_cand/g_scand) between launches. Only g_bit_stamps is
    reset per launch (the same Fenwick stamp contract the dense path requires).

    This mirrors production, where Taichi pools/reuses device buffers across
    launches and the candidate scratch carries stale data from prior, possibly
    LONGER, lanes. Each launch is independently checked against a fresh dense run.
    Proves _append_cand/_skyline_compact never read uninitialized/stale slots.
    Returns (launches_checked, mismatches)."""
    L = MAX_LANES_PER_LAUNCH
    bit_limit = pair_mod + 1
    pair_size = (n + 1) * pair_mod

    # Persistent (reused) compact-path device arrays. Deliberately seeded with
    # garbage so any read-before-write bug surfaces immediately.
    g_cand = rng.integers(0, 1 << 20, size=(L, cap_cand, 2)).astype(np.int32)
    g_scand = rng.integers(0, 1 << 20, size=(L, cap_cand, 2)).astype(np.int32)
    g_bit_values = rng.integers(0, 1 << 20, size=(L, bit_limit)).astype(np.int32)
    g_bit_stamps = np.full((L, bit_limit), -1, dtype=np.int32)
    g_error = np.zeros((L,), dtype=np.int32)
    g_frontier = np.zeros((L, cap, 3), dtype=np.uint64)
    g_fcount = np.zeros((L,), dtype=np.int32)

    mism = 0
    checked = 0
    for _ in range(n_launches):
        # Vary per-lane counts each launch (some lanes shorter than last time, so
        # the tail of g_cand holds stale rows from a previous, deeper launch).
        max_cand = int(rng.integers(0, min(cap_cand - 2, 400)))
        cand_in, cand_count = _gen_skyline_case(rng, n, pair_mod, L, max_cand)
        bit_stamp = int(rng.integers(1, 1_000_000))

        # Pad/truncate cand_in to a fixed slot width for the reused launch.
        slots = cand_in.shape[1]
        sub_cand = np.zeros((L, max(slots, 1), CAND_FIELDS), dtype=np.int32)
        sub_cand[:, :slots, :] = cand_in
        sub_count = np.ascontiguousarray(cand_count)

        # Reset ONLY the Fenwick stamps (host contract) -- NOT the candidate
        # scratch. g_cand/g_scand keep whatever the previous launch left behind.
        g_bit_stamps.fill(-1)

        _run_compact(
            L, pair_mod, bit_limit, bit_stamp, cap_cand,
            sub_cand, sub_count,
            g_cand, g_scand, g_bit_values, g_bit_stamps, g_error,
            g_frontier, g_fcount,
        )
        ti.sync()

        # Fresh dense oracle for this exact launch.
        stamp = int(rng.integers(1, 1_000_000))
        dense_tr, dense_of = _dense_frontiers(
            sub_cand, sub_count, n, pair_mod, stamp, bit_stamp, cap
        )

        for li in range(L):
            if bool(g_error[li]):
                mism += 1
                print(f"  [reuse] COMPACT OVERFLOW lane={li} cap_cand={cap_cand}")
                continue
            if dense_of[li]:
                continue
            gc = int(g_fcount[li])
            comp = [
                (int(g_frontier[li, k, 0]), int(g_frontier[li, k, 1]), int(g_frontier[li, k, 2]))
                for k in range(gc)
            ]
            if comp != dense_tr[li]:
                mism += 1
                print(f"  [reuse] MISMATCH lane={li} n={n} pair_mod={pair_mod} "
                      f"cand_count={int(sub_count[li])}")
                print(f"    dense={dense_tr[li]}")
                print(f"    comp ={comp}")
            checked += 1
    return checked, mism


# =========================================================================== #
# Case generators. (Reused/extended from _layer2a_skyline_probe.py.)
# =========================================================================== #
def _gen_skyline_case(rng, n, pair_mod, n_lanes, max_cand, min_cand=0):
    """In-bounds candidates with overlapping fever_great columns + frequent ties.

    All candidates are in-bounds (no overflow) so the FULL frontier is compared.
    A small body_fever pool forces frequent exact ties so the STRICT-`>`
    non-emission boundary in the Fenwick is exercised.
    """
    cand_counts = rng.integers(min_cand, max_cand + 1, size=n_lanes).astype(np.int32)
    max_slots = int(max(1, cand_counts.max(initial=1)))
    cand = np.zeros((n_lanes, max_slots, CAND_FIELDS), dtype=np.int32)

    fever_pool = np.array([0, 1, 1, 2, 3, 3, 5, 8], dtype=np.int64)

    for lane in range(n_lanes):
        c = int(cand_counts[lane])
        for slot in range(c):
            normal_great = int(rng.integers(0, n + 1))
            fever_great = int(rng.integers(0, pair_mod)) if pair_mod > 0 else 0
            body_great = normal_great + fever_great
            body_fever_great = fever_great
            body_fever = int(fever_pool[rng.integers(0, fever_pool.shape[0])])

            eg = int(rng.integers(0, body_great + 1))
            tg = body_great - eg
            efg = int(rng.integers(0, body_fever_great + 1))
            tfg = body_fever_great - efg
            ef = int(rng.integers(0, body_fever + 1))
            tf = body_fever - ef

            cand[lane, slot, 0] = ef
            cand[lane, slot, 1] = eg
            cand[lane, slot, 2] = efg
            cand[lane, slot, 3] = tf
            cand[lane, slot, 4] = tg
            cand[lane, slot, 5] = tfg

    return cand, cand_counts


def _gen_overflow_case(rng, n, pair_mod, n_lanes, max_cand, force_overflow_prob):
    """Mixed case exercising body_fever_great>body_great drops + (for dense)
    out-of-bounds pair_idx. For the compact path the only overflow is the
    candidate-buffer cap, so we keep counts within cap_cand and instead rely on
    this generator purely to stress the drop path + wide pair spreads."""
    cand_counts = rng.integers(0, max_cand + 1, size=n_lanes).astype(np.int32)
    max_slots = int(max(1, cand_counts.max(initial=1)))
    cand = np.zeros((n_lanes, max_slots, CAND_FIELDS), dtype=np.int32)

    for lane in range(n_lanes):
        c = int(cand_counts[lane])
        for slot in range(c):
            normal_great = int(rng.integers(0, n + 2))
            fever_great = int(rng.integers(0, pair_mod + 1))
            body_great = normal_great + fever_great
            body_fever_great = fever_great
            if rng.random() < 0.15:
                body_fever_great = body_great + int(rng.integers(1, 3))
            body_fever = int(rng.integers(0, 40))

            eg = int(rng.integers(0, body_great + 1)) if body_great >= 0 else 0
            tg = max(0, body_great - eg)
            efg = int(rng.integers(0, body_fever_great + 1)) if body_fever_great >= 0 else 0
            tfg = max(0, body_fever_great - efg)
            ef = int(rng.integers(0, body_fever + 1))
            tf = max(0, body_fever - ef)

            cand[lane, slot, 0] = ef
            cand[lane, slot, 1] = eg
            cand[lane, slot, 2] = efg
            cand[lane, slot, 3] = tf
            cand[lane, slot, 4] = tg
            cand[lane, slot, 5] = tfg

    return cand, cand_counts


def _compare(cand_in, cand_count, n, pair_mod, cap, cap_cand, rng, label):
    """Run both paths over the SAME candidates; assert bit-exact frontier parity.

    Returns (n_lanes, mismatches, max_compact_launch_time, max_cand_count)."""
    stamp = int(rng.integers(1, 1000))
    bit_stamp = int(rng.integers(1, 1000))
    n_lanes = cand_in.shape[0]

    dense_tr, dense_of = _dense_frontiers(
        cand_in, cand_count, n, pair_mod, stamp, bit_stamp, cap
    )
    comp_tr, comp_of, max_t = _compact_frontiers(
        cand_in, cand_count, n, pair_mod, bit_stamp, cap, cap_cand
    )

    mism = 0
    for lane in range(n_lanes):
        # The dense path can flag fail-loud on an out-of-bounds pair_idx; the
        # compact path only flags on candidate-buffer overflow. We size cap_cand
        # >= every lane's count, so the compact path must NEVER overflow here.
        if comp_of[lane]:
            mism += 1
            print(f"  [{label}] COMPACT OVERFLOW lane={lane} (cap_cand={cap_cand} too small)")
            continue
        # When the dense path overflowed (skipped out-of-bounds candidates), its
        # frontier reflects only the in-bounds ones; the compact path indexes
        # pair_idx WITHOUT a pair_size bound, so it would include those. Skip
        # lanes where the dense oracle overflowed (parity is only defined where
        # the dense grid was large enough -- which is the production invariant).
        if dense_of[lane]:
            continue
        if comp_tr[lane] != dense_tr[lane]:
            mism += 1
            print(f"  [{label}] MISMATCH lane={lane} n={n} pair_mod={pair_mod} "
                  f"cand_count={int(cand_count[lane])}")
            print(f"    dense={dense_tr[lane]}")
            print(f"    comp ={comp_tr[lane]}")

    max_cc = int(cand_count.max(initial=0))
    return n_lanes, mism, max_t, max_cc


# =========================================================================== #
# Driver.
# =========================================================================== #
def main():
    arch = str(ti.cfg.arch)
    print(f"[probe] Taichi arch = {arch}")
    if "vulkan" not in arch.lower():
        print("SKYLINE COMPACT PARITY: FAIL (not on Vulkan GPU backend)")
        sys.exit(1)

    rng = np.random.default_rng(20260602)

    total_lanes = 0
    total_mism = 0
    total_batches = 0
    global_max_cc = 0
    large_case_time = 0.0
    large_case_cc = 0

    # --- Sweep: small n / small pair_mod, many randomized batches. ---------- #
    configs = [(n, pm) for n in (1, 2, 3, 5, 8, 13) for pm in (1, 2, 3, 4, 7, 11)]
    BATCHES_PER_CONFIG = 10
    for (n, pair_mod) in configs:
        for b in range(BATCHES_PER_CONFIG):
            n_lanes = int(rng.integers(1, 33))  # spans >1 launch (chunked to <=16)
            max_cand = int(rng.integers(0, 30))
            cap = (n + 1) * pair_mod + 4
            cap_cand = max_cand + 4
            if b % 3 == 0:
                cand_in, cand_count = _gen_overflow_case(
                    rng, n, pair_mod, n_lanes, max_cand, 0.0
                )
            else:
                cand_in, cand_count = _gen_skyline_case(
                    rng, n, pair_mod, n_lanes, max_cand
                )
            lanes, mism, mt, mcc = _compare(
                cand_in, cand_count, n, pair_mod, cap, cap_cand, rng, f"sweep n={n} pm={pair_mod}"
            )
            total_lanes += lanes
            total_mism += mism
            total_batches += 1
            global_max_cc = max(global_max_cc, mcc)

    # --- Deep skyline streams: counts >> pair_size so per-pair MAX + Fenwick
    #     domination + strict-`>` ties are heavily revisited. ---------------- #
    sky_configs = [(n, pm) for n in (1, 2, 3, 5, 8) for pm in (1, 2, 3, 4, 6, 9)]
    for (n, pair_mod) in sky_configs:
        for _ in range(8):
            n_lanes = int(rng.integers(1, 17))
            max_cand = int(rng.integers(0, 4 * (n + 1) * pair_mod + 8))
            cap = (n + 1) * pair_mod + 4
            cap_cand = max_cand + 4
            cand_in, cand_count = _gen_skyline_case(rng, n, pair_mod, n_lanes, max_cand)
            lanes, mism, mt, mcc = _compare(
                cand_in, cand_count, n, pair_mod, cap, cap_cand, rng, f"deep n={n} pm={pair_mod}"
            )
            total_lanes += lanes
            total_mism += mism
            total_batches += 1
            global_max_cc = max(global_max_cc, mcc)

    # --- LARGE-COUNT scalability + timing: ~10k-50k candidates per lane. ----
    #     Proves the bottom-up merge sort scales and stays well sub-second per
    #     launch (insertion sort would TDR here). Use a LOW-FF / LARGE-n shape
    #     (the exact OOM case the dense grid cannot handle: pair_size ~ n^2).
    #     pair_mod kept small so many candidates collide on the same pair_idx,
    #     stressing the coalesce-MAX run merging too. n_lanes small (<=8) so the
    #     per-launch work stays bounded even with 50k-deep lanes.
    print("[probe] running LARGE-COUNT scalability cases (10k-50k cand/lane)...")
    for (n, pair_mod, big) in [
        (60, 3, 10000),
        (80, 2, 20000),
        (120, 2, 35000),
        (160, 3, 50000),
    ]:
        n_lanes = 4
        cap = (n + 1) * pair_mod + 4
        cap_cand = big + 8
        cand_in, cand_count = _gen_skyline_case(
            rng, n, pair_mod, n_lanes, big, min_cand=big
        )
        lanes, mism, mt, mcc = _compare(
            cand_in, cand_count, n, pair_mod, cap, cap_cand, rng, f"LARGE n={n} pm={pair_mod}"
        )
        total_lanes += lanes
        total_mism += mism
        total_batches += 1
        global_max_cc = max(global_max_cc, mcc)
        if mcc > large_case_cc:
            large_case_cc = mcc
            large_case_time = mt
        print(f"  [LARGE] n={n} pair_mod={pair_mod} cand/lane={mcc} "
              f"compact_launch={mt*1000:.1f}ms mism={mism}")

    # --- Read-before-write hardening: reuse ONE persistent device-array set
    #     across many launches WITHOUT re-zeroing the candidate scratch. Proves
    #     the funcs are self-contained vs Taichi's pooled/stale device buffers
    #     (the production reality). ------------------------------------------- #
    print("[probe] running BUFFER-REUSE (stale-scratch) hardening cases...")
    reuse_checked = 0
    for (n, pair_mod) in [(2, 3), (5, 2), (8, 4), (13, 1)]:
        cap = (n + 1) * pair_mod + 4
        cap_cand = 420
        chk, mism = _reuse_stress(rng, n, pair_mod, cap, cap_cand, n_launches=12)
        reuse_checked += chk
        total_mism += mism
        total_batches += 1
        total_lanes += chk
    print(f"  [reuse] launches*lanes checked={reuse_checked}")

    print(
        f"[probe] batches={total_batches} lanes={total_lanes} "
        f"mismatches={total_mism} max_cand_count={global_max_cc}"
    )
    print(
        f"[probe] LARGE case: cand/lane={large_case_cc} "
        f"compact_launch_time={large_case_time*1000:.1f}ms "
        f"({'OK <1s' if large_case_time < 1.0 else 'TOO SLOW >=1s'})"
    )

    if total_mism == 0 and large_case_time < 1.0:
        print(
            f"SKYLINE COMPACT PARITY: PASS  "
            f"(batches={total_batches}, lanes={total_lanes}, "
            f"max_cand_count={global_max_cc}, "
            f"large_case={large_case_cc}@{large_case_time*1000:.1f}ms)"
        )
        sys.exit(0)
    if total_mism != 0:
        print(f"SKYLINE COMPACT PARITY: FAIL  (mismatches={total_mism})")
    else:
        print(f"SKYLINE COMPACT PARITY: FAIL  (large case too slow: {large_case_time*1000:.1f}ms)")
    sys.exit(1)


if __name__ == "__main__":
    main()
