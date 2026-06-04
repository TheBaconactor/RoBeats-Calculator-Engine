"""Throwaway GPU parity probe: Layer-2a FG body-skyline reduction.

Ports four Numba reference functions from
``gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu_numba.py``
to Taichi ``@ti.func`` form and proves bit-exact parity on the GPU
(RX 7900 XTX / ``ti.vulkan``):

    _numba_prefix_max_query_stamped   -> _prefix_max_query_stamped
    _numba_prefix_max_update_stamped  -> _prefix_max_update_stamped
    _numba_touch_body_candidate       -> _touch_body_candidate
    _numba_reduce_touched_body_pairs  -> _reduce_touched_body_pairs

LANE-INDEXED scratch design (matches the eventual per-lane-parallel kernel:
one geometry key per GPU lane, ``for lane in range(n_lanes)`` at kernel top).
Each @ti.func takes the 2D scratch ndarray + a ``lane: ti.i32`` and operates
on ``scratch[lane, ...]``.

This is a probe under tools/dev/. It does NOT modify any production module.
The @ti.func bodies here are the deliverable to be integrated into
response_build_gpu_taichi.py separately.

Run:  python tools/dev/_layer2a_skyline_probe.py
"""

import os
import sys

# Repo root on sys.path so the runtime/init helper imports cleanly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import numpy as np  # noqa: E402

from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

# Init Taichi on the production Vulkan backend BEFORE importing the Numba twins
# (Numba import is cheap and order-independent, but keep GPU init first to match
# the production startup ordering).
init_taichi()

import taichi as ti  # noqa: E402

from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (  # noqa: E402
    _numba_prefix_max_query_stamped,
    _numba_prefix_max_update_stamped,
    _numba_reduce_touched_body_pairs,
    _numba_touch_body_candidate,
)


# =========================================================================== #
# DELIVERABLE: Taichi @ti.func port of the body-skyline reduction.
#
# Conventions match response_build_gpu_taichi.py:
#   - import taichi as ti
#   - NO ``from __future__ import annotations``
#   - inline type constructors inside funcs (module-level ti.u64(...) FAILS)
#   - @ti.func args are annotated with real ti type objects / ndarray specs.
#
# Lane-indexed scratch (all 2D ndarrays, indexed [lane, slot]):
#   best_fever_by_pair[n_lanes, pair_size]  (i32)  pair_size = (n+1)*pair_mod
#   pair_stamp        [n_lanes, pair_size]  (i32)
#   touched_pair      [n_lanes, pair_size]  (i32)
#   bit_values        [n_lanes, pair_mod+1] (i32)
#   bit_stamps        [n_lanes, pair_mod+1] (i32)
#   error_flag        [n_lanes]             (i32)  <- fail-loud overflow sentinel
# Output body frontier per lane:
#   frontier          [n_lanes, cap, 3]     (u64)
#   frontier_count    [n_lanes]             (i32)
# =========================================================================== #


@ti.func
def _prefix_max_query_stamped(
    bit_values: ti.types.ndarray(dtype=ti.i32, ndim=2),
    bit_stamps: ti.types.ndarray(dtype=ti.i32, ndim=2),
    lane: ti.i32,
    stamp: ti.i32,
    idx: ti.i32,
) -> ti.i32:
    # Numba _numba_prefix_max_query_stamped (response_build_gpu_numba.py:236-246).
    # Stamped Fenwick/BIT PREFIX-MAX over [0..idx]; 1-indexed; returns -1 for an
    # empty (all-stale) prefix. Only entries whose stamp == stamp are counted.
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
    # ``limit`` is the per-lane Fenwick width (= bit_values.shape[1] = pair_mod+1);
    # the Numba twin reads it from ``values.shape[0]``.
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
    # Numba _numba_touch_body_candidate (:262-293).
    # Accumulates one body candidate into the dense pair grid keyed by
    #   pair_idx = normal_great * pair_mod + body_fever_great
    # where normal_great = body_great - body_fever_great. Keeps MAX body_fever per
    # pair via epoch stamping; drops candidates with body_fever_great > body_great.
    #
    # FAIL-LOUD: the Numba twin RAISES ValueError when pair_idx is out of bounds.
    # GPU code cannot raise, so we set error_flag[lane] = 1 and return the count
    # unchanged; the host MUST inspect error_flag after the launch and raise.
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
    # Numba _numba_reduce_touched_body_pairs (:296-326).
    # Sorts touched pair indices ASCENDING, coalesces duplicates, then for each
    # distinct pair emits (body_fever, normal_great+fever_great, fever_great) iff
    #   best_fever > prefix_max_query(bit_values, bit_stamps, bit_stamp, fever_great)
    # (STRICT >), updating the Fenwick afterward. Emission order follows ascending
    # pair_idx. Returns the number of emitted triples (also written to
    # frontier_count[lane]).
    out_count = ti.i32(0)
    if touched_count > 0:
        # In-place ascending insertion sort of touched_pair[lane, 0:touched_count].
        # Matches np.sort (ascending integer); touched_count is small per call.
        # NB: within one epoch the touched_pair entries are already DISTINCT
        # pair indices (touch only appends on a fresh stamp), so sort stability is
        # moot; the duplicate-coalescing below is kept for fidelity with Numba.
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


# =========================================================================== #
# Probe kernel: drive the reduction for many lanes in ONE launch.
#
# Per lane we replay a sequence of (edge, tail) candidate touches whose
# boundaries are precomputed on the host into a flat candidate buffer, then run
# the reduce. This mirrors how the production kernel will accumulate body
# candidates for a geometry key before reducing.
#
# Candidate layout: cand[lane, slot, 0..5] =
#   (edge_fever, edge_great, edge_fever_great, tail_fever, tail_great, tail_fever_great)
# cand_count[lane] = number of valid candidate slots for that lane.
# =========================================================================== #
CAND_FIELDS = 6


@ti.kernel
def _run_skyline(
    n_lanes: ti.i32,
    pair_mod: ti.i32,
    pair_size: ti.i32,
    bit_limit: ti.i32,
    stamp: ti.i32,
    bit_stamp: ti.i32,
    cand: ti.types.ndarray(dtype=ti.i32, ndim=3),
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
        # Per-lane kernel cannot assume device scratch is zero: Taichi pools/reuses
        # ndarray device buffers across launches, so a lane that never hits the
        # overflow branch would otherwise read stale garbage. Initialize the
        # fail-loud flag here. (The eventual production kernel must do the same.)
        error_flag[lane] = 0
        touched_count = ti.i32(0)
        c = cand_count[lane]
        for slot in range(c):
            touched_count = _touch_body_candidate(
                cand[lane, slot, 0],
                cand[lane, slot, 1],
                cand[lane, slot, 2],
                cand[lane, slot, 3],
                cand[lane, slot, 4],
                cand[lane, slot, 5],
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


# =========================================================================== #
# Numba reference replay (per state) for one lane's candidate sequence.
# =========================================================================== #
def _numba_reference_lane(cand_rows, pair_mod, pair_size, stamp, bit_stamp, bit_limit):
    """Drive the Numba twins for one lane, mirroring the GPU's overflow policy.

    The GPU @ti.func cannot raise: on an out-of-bounds pair_idx it sets the
    fail-loud flag and SKIPS that candidate (touched_count unchanged), then
    continues. ``_numba_touch_body_candidate`` raises ValueError *before*
    mutating any state, so catching it and continuing reproduces the GPU branch
    exactly. This lets us assert bit-exact parity on BOTH the overflow flag AND
    the emitted frontier for every lane, including lanes that contain overflow
    candidates mixed with in-bounds ones.
    """
    pair_stamp = np.full(pair_size, -1, dtype=np.int64)
    best_fever_by_pair = np.zeros(pair_size, dtype=np.int64)
    touched_pair = np.zeros(max(pair_size, 1), dtype=np.int64)
    bit_values = np.zeros(bit_limit, dtype=np.int64)
    bit_stamps = np.full(bit_limit, -1, dtype=np.int64)

    touched_count = 0
    overflow = False
    for row in cand_rows:
        ef, eg, efg, tf, tg, tfg = (int(x) for x in row)
        try:
            touched_count = _numba_touch_body_candidate(
                ef, eg, efg, tf, tg, tfg,
                int(pair_mod), int(stamp),
                pair_stamp, best_fever_by_pair, touched_pair, int(touched_count),
            )
        except ValueError:
            # Mirror the GPU: flag and skip this candidate, keep going.
            overflow = True

    frontier = _numba_reduce_touched_body_pairs(
        int(pair_mod), touched_pair, int(touched_count),
        best_fever_by_pair, bit_values, bit_stamps, int(bit_stamp),
    )
    triples = [(int(a), int(b), int(c)) for (a, b, c) in frontier]
    return triples, overflow


# =========================================================================== #
# Case generation.
# =========================================================================== #
def _gen_case(rng, n, pair_mod, n_lanes, max_cand, force_overflow_prob=0.0):
    """Build a randomized batch of lanes.

    Each candidate's (edge_*, tail_*) counts are drawn so that the derived
    body_great / body_fever_great land mostly in-range for the given
    pair_mod/n, but a fraction deliberately exceed pair_mod or n to exercise
    the body_fever_great>body_great drop AND the overflow flag.
    """
    pair_size = (n + 1) * pair_mod
    cand_counts = rng.integers(0, max_cand + 1, size=n_lanes).astype(np.int32)
    max_slots = int(max(1, cand_counts.max(initial=1)))
    cand = np.zeros((n_lanes, max_slots, CAND_FIELDS), dtype=np.int32)

    want_overflow = rng.random() < force_overflow_prob

    for lane in range(n_lanes):
        c = int(cand_counts[lane])
        for slot in range(c):
            # Compose body_great in a range that usually fits normal_great<=n,
            # fever_great<pair_mod, but occasionally overshoots.
            if want_overflow and slot == 0:
                # Force a clearly out-of-bounds pair_idx.
                body_great = pair_mod + n + rng.integers(1, 5)
                body_fever_great = rng.integers(0, body_great + 1)
            else:
                # normal_great in [0, n+overshoot], fever_great in [0, pair_mod-1+overshoot]
                normal_great = int(rng.integers(0, n + 2))
                fever_great = int(rng.integers(0, pair_mod + 1))
                body_great = normal_great + fever_great
                body_fever_great = fever_great
                # Sometimes flip so body_fever_great > body_great (drop path).
                if rng.random() < 0.15:
                    body_fever_great = body_great + int(rng.integers(1, 3))
            body_fever = int(rng.integers(0, 40))

            # Split body_* into edge + tail parts (both non-negative).
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

    return pair_size, cand, cand_counts


def _gen_skyline_case(rng, n, pair_mod, n_lanes, max_cand):
    """Skyline-focused generator.

    Targets the Fenwick prefix-max domination + strict-`>` tie-break by packing
    each lane with MANY in-bounds candidates whose (normal_great, fever_great)
    cover overlapping fever_great columns with a wide spread of body_fever,
    including deliberate exact ties (same body_fever at equal/lower fever_great)
    so the STRICT `>` non-emission boundary is exercised. All candidates are
    kept in-bounds (no overflow) so the full frontier is compared.
    """
    pair_size = (n + 1) * pair_mod
    cand_counts = rng.integers(0, max_cand + 1, size=n_lanes).astype(np.int32)
    max_slots = int(max(1, cand_counts.max(initial=1)))
    cand = np.zeros((n_lanes, max_slots, CAND_FIELDS), dtype=np.int32)

    # A small pool of body_fever values forces frequent exact ties.
    fever_pool = np.array([0, 1, 1, 2, 3, 3, 5, 8], dtype=np.int64)

    for lane in range(n_lanes):
        c = int(cand_counts[lane])
        for slot in range(c):
            # normal_great in [0, n] keeps pair_idx < pair_size when fever_great<pair_mod.
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

    return pair_size, cand, cand_counts


def _run_one_batch(rng, n, pair_mod, n_lanes, max_cand, force_overflow_prob, cap, skyline=False):
    if skyline:
        pair_size, cand, cand_counts = _gen_skyline_case(rng, n, pair_mod, n_lanes, max_cand)
    else:
        pair_size, cand, cand_counts = _gen_case(
            rng, n, pair_mod, n_lanes, max_cand, force_overflow_prob
        )
    bit_limit = pair_mod + 1
    stamp = int(rng.integers(1, 1000))
    bit_stamp = int(rng.integers(1, 1000))

    # GPU scratch (fresh, zero/stale-initialized so stamps never collide).
    g_pair_stamp = np.full((n_lanes, pair_size), -1, dtype=np.int32)
    g_best = np.zeros((n_lanes, pair_size), dtype=np.int32)
    g_touched = np.zeros((n_lanes, max(pair_size, 1)), dtype=np.int32)
    g_bit_values = np.zeros((n_lanes, bit_limit), dtype=np.int32)
    g_bit_stamps = np.full((n_lanes, bit_limit), -1, dtype=np.int32)
    g_error = np.zeros((n_lanes,), dtype=np.int32)
    g_frontier = np.zeros((n_lanes, cap, 3), dtype=np.uint64)
    g_frontier_count = np.zeros((n_lanes,), dtype=np.int32)

    _run_skyline(
        n_lanes, pair_mod, pair_size, bit_limit, stamp, bit_stamp,
        cand, cand_counts,
        g_pair_stamp, g_best, g_touched, g_bit_values, g_bit_stamps, g_error,
        g_frontier, g_frontier_count,
    )
    ti.sync()

    # Numba reference per lane.
    mismatches = 0
    for lane in range(n_lanes):
        rows = cand[lane, : int(cand_counts[lane])]
        ref_triples, ref_overflow = _numba_reference_lane(
            rows, pair_mod, pair_size, stamp, bit_stamp, bit_limit
        )
        gpu_overflow = bool(g_error[lane])

        # Fail-loud flag must agree bit-for-bit.
        if ref_overflow != gpu_overflow:
            mismatches += 1
            print(f"  [overflow-flag mismatch] lane={lane} ref={ref_overflow} gpu={gpu_overflow}")
            print(f"    n={n} pair_mod={pair_mod} pair_size={pair_size}")
            print(f"    cand_count={int(cand_counts[lane])} rows={rows.tolist()}")
            continue

        # Frontier (emitted body-pair triples) must match as an ORDERED sequence.
        gc = int(g_frontier_count[lane])
        gpu_triples = [
            (int(g_frontier[lane, k, 0]), int(g_frontier[lane, k, 1]), int(g_frontier[lane, k, 2]))
            for k in range(gc)
        ]
        if gpu_triples != ref_triples:
            mismatches += 1
            print(f"  [MISMATCH] lane={lane}")
            print(f"    n={n} pair_mod={pair_mod} cand_count={int(cand_counts[lane])}")
            print(f"    overflow ref={ref_overflow} gpu={gpu_overflow}")
            print(f"    ref={ref_triples}")
            print(f"    gpu={gpu_triples}")
            print(f"    rows={rows.tolist()}")

    return n_lanes, mismatches


def main():
    # Sanity: confirm we are actually on the Vulkan GPU backend.
    arch = str(ti.cfg.arch)
    print(f"[probe] Taichi arch = {arch}")
    if "vulkan" not in arch.lower():
        print("LAYER 2a PARITY: FAIL (not on Vulkan GPU backend)")
        sys.exit(1)

    rng = np.random.default_rng(20260602)

    total_lanes = 0
    total_mismatch = 0
    total_batches = 0

    # Sweep n, pair_mod, lane counts, candidate depth, overflow probability.
    configs = []
    for n in (1, 2, 3, 5, 8, 13):
        for pair_mod in (1, 2, 3, 4, 7, 11):
            configs.append((n, pair_mod))

    # Many randomized batches per config.
    BATCHES_PER_CONFIG = 12
    for (n, pair_mod) in configs:
        for b in range(BATCHES_PER_CONFIG):
            n_lanes = int(rng.integers(1, 17))
            max_cand = int(rng.integers(0, 25))
            cap = (n + 1) * pair_mod + 4  # generous; >= max distinct pairs
            force_overflow_prob = 0.25 if (b % 4 == 0) else 0.0
            lanes, mism = _run_one_batch(
                rng, n, pair_mod, n_lanes, max_cand, force_overflow_prob, cap
            )
            total_lanes += lanes
            total_mismatch += mism
            total_batches += 1

    # A few large stress batches (many lanes, deep candidate streams).
    for _ in range(20):
        n = int(rng.integers(1, 16))
        pair_mod = int(rng.integers(1, 13))
        n_lanes = int(rng.integers(8, 65))
        max_cand = int(rng.integers(10, 60))
        cap = (n + 1) * pair_mod + 4
        lanes, mism = _run_one_batch(rng, n, pair_mod, n_lanes, max_cand, 0.1, cap)
        total_lanes += lanes
        total_mismatch += mism
        total_batches += 1

    # SKYLINE-FOCUSED stress: deep in-bounds candidate streams that pack many
    # distinct pairs with overlapping fever_great columns and frequent exact
    # body_fever ties, so the Fenwick prefix-max domination and the STRICT-`>`
    # tie-break (non-emission on equal best_fever) are heavily exercised, and the
    # full frontier is compared on every lane (no overflow short-circuit).
    sky_configs = [(n, pm) for n in (1, 2, 3, 5, 8) for pm in (1, 2, 3, 4, 6, 9)]
    for (n, pair_mod) in sky_configs:
        for _ in range(10):
            n_lanes = int(rng.integers(1, 33))
            # Deep streams (often >> pair_size) so every pair gets revisited and
            # the per-pair MAX body_fever accumulation is stressed too.
            max_cand = int(rng.integers(0, 4 * (n + 1) * pair_mod + 8))
            cap = (n + 1) * pair_mod + 4
            lanes, mism = _run_one_batch(
                rng, n, pair_mod, n_lanes, max_cand, 0.0, cap, skyline=True
            )
            total_lanes += lanes
            total_mismatch += mism
            total_batches += 1

    print(
        f"[probe] batches={total_batches} lanes={total_lanes} mismatches={total_mismatch}"
    )
    if total_mismatch == 0:
        print(f"LAYER 2a PARITY: PASS  (batches={total_batches}, lanes={total_lanes})")
        sys.exit(0)
    print(f"LAYER 2a PARITY: FAIL  (mismatches={total_mismatch})")
    sys.exit(1)


if __name__ == "__main__":
    main()
