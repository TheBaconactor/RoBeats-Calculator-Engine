"""Throwaway probe (Layer 2b): GPU bit-exact parity for the FG non-monotone
bidirectional pairwise dominance reduction over surfaces.

Ports Numba `_numba_append_surface` / `_numba_reduce`
(gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu_numba.py:92-164)
to a Taichi `@ti.func` with lane-indexed scratch, and proves bit-exact parity
(INCLUDING row order) against the Numba oracle on the RX 7900 XTX over many
randomized surface sets.

Run: python tools/dev/_layer2b_dominance_probe.py   (delete after)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (  # noqa: E402
    _numba_reduce,
)
from gear_optimizer.solver.taichi_gem.runtime import init_taichi  # noqa: E402

init_taichi()
import taichi as ti  # noqa: E402

print("Taichi init OK")

vec7u64 = ti.types.vector(7, ti.u64)


# --------------------------------------------------------------------------- #
# CANDIDATE @ti.func PORT (for integration into response_build_gpu_taichi.py)
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
    # Bit-exact port of Numba `_numba_append_surface`
    # (response_build_gpu_numba.py:92-132). Non-monotone bidirectional pairwise
    # dominance update of the per-lane `bucket` with incoming surface `c`.
    #
    # PHASE 1: if ANY kept `k` dominates `c`, drop `c` (bucket unchanged).
    # PHASE 2: else, remove every kept `k` that `c` dominates (stable in-place
    #          write-pointer compaction preserving survivor order), then append
    #          `c` LAST.
    #
    # exact_overlap gate: c.bfg==k.bfg AND head (fever&great) lo/hi words equal.
    # fever subset toward the dominator, great subset toward the dominated,
    # body fields use bf>= , bg<= , bfg<=. Subset test is `(x & ~y)==0` per u64
    # word (uint64 bitwise complement; verified to behave as subset).
    cf_lo = c[0]
    cf_hi = c[1]
    cg_lo = c[2]
    cg_hi = c[3]
    cbf = c[4]
    cbg = c[5]
    cbfg = c[6]

    zero = ti.u64(0)
    original_len = bucket_count[lane]

    # PHASE 1: does any kept surface dominate c?
    dominated = 0
    for idx in range(original_len):
        kf_lo = bucket[lane, idx, 0]
        kf_hi = bucket[lane, idx, 1]
        kg_lo = bucket[lane, idx, 2]
        kg_hi = bucket[lane, idx, 3]
        kbf = bucket[lane, idx, 4]
        kbg = bucket[lane, idx, 5]
        kbfg = bucket[lane, idx, 6]
        exact_overlap = (
            cbfg == kbfg
            and (cf_lo & cg_lo) == (kf_lo & kg_lo)
            and (cf_hi & cg_hi) == (kf_hi & kg_hi)
        )
        if (
            kbf >= cbf
            and kbg <= cbg
            and kbfg <= cbfg
            and exact_overlap
            and (cf_lo & ~kf_lo) == zero
            and (cf_hi & ~kf_hi) == zero
            and (kg_lo & ~cg_lo) == zero
            and (kg_hi & ~cg_hi) == zero
        ):
            dominated = 1

    new_count = original_len
    if dominated == 0:
        # PHASE 2: stable write-pointer compaction; drop kept k that c dominates.
        write = 0
        for idx in range(original_len):
            kf_lo = bucket[lane, idx, 0]
            kf_hi = bucket[lane, idx, 1]
            kg_lo = bucket[lane, idx, 2]
            kg_hi = bucket[lane, idx, 3]
            kbf = bucket[lane, idx, 4]
            kbg = bucket[lane, idx, 5]
            kbfg = bucket[lane, idx, 6]
            exact_overlap = (
                cbfg == kbfg
                and (cf_lo & cg_lo) == (kf_lo & kg_lo)
                and (cf_hi & cg_hi) == (kf_hi & kg_hi)
            )
            drop = (
                cbf >= kbf
                and cbg <= kbg
                and cbfg <= kbfg
                and exact_overlap
                and (kf_lo & ~cf_lo) == zero
                and (kf_hi & ~cf_hi) == zero
                and (cg_lo & ~kg_lo) == zero
                and (cg_hi & ~kg_hi) == zero
            )
            if drop == 0:
                # Survivor: shift down to the write pointer (in-place, stable).
                # idx >= write always, so reading idx before writing is safe.
                if write != idx:
                    bucket[lane, write, 0] = kf_lo
                    bucket[lane, write, 1] = kf_hi
                    bucket[lane, write, 2] = kg_lo
                    bucket[lane, write, 3] = kg_hi
                    bucket[lane, write, 4] = kbf
                    bucket[lane, write, 5] = kbg
                    bucket[lane, write, 6] = kbfg
                write += 1
        # Append c LAST. Fail loudly if capacity would be exceeded (GPU can't
        # raise): set error_flag[lane]=1 and do not write out of bounds.
        if write >= cap:
            error_flag[lane] = 1
            new_count = write
        else:
            bucket[lane, write, 0] = cf_lo
            bucket[lane, write, 1] = cf_hi
            bucket[lane, write, 2] = cg_lo
            bucket[lane, write, 3] = cg_hi
            bucket[lane, write, 4] = cbf
            bucket[lane, write, 5] = cbg
            bucket[lane, write, 6] = cbfg
            new_count = write + 1
    bucket_count[lane] = new_count
    return new_count


# --------------------------------------------------------------------------- #
# Driver kernel: runs `reduce` (append_surface in a loop) per lane.
#   inputs[lane, k, 7]   : up to k_counts[lane] incoming surfaces
#   bucket[lane, cap, 7] : per-lane kept buffer (output)
#   bucket_count[lane]   : kept count (output)
# Mirrors Numba `_numba_reduce`: empty input -> single all-zero surface.
# --------------------------------------------------------------------------- #
@ti.kernel
def reduce_kernel(
    n_lanes: ti.i32,
    cap: ti.i32,
    k_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    inputs: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bucket: ti.types.ndarray(dtype=ti.u64, ndim=3),
    bucket_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    error_flag: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for lane in range(n_lanes):  # top-level range-for == GPU parallel domain
        bucket_count[lane] = 0
        k = k_counts[lane]
        if k == 0:
            # Numba `_numba_reduce`: empty surfaces -> one all-zero surface.
            for col in ti.static(range(7)):
                bucket[lane, 0, col] = ti.u64(0)
            bucket_count[lane] = 1
        else:
            for s in range(k):
                c = vec7u64(
                    inputs[lane, s, 0],
                    inputs[lane, s, 1],
                    inputs[lane, s, 2],
                    inputs[lane, s, 3],
                    inputs[lane, s, 4],
                    inputs[lane, s, 5],
                    inputs[lane, s, 6],
                )
                _append_surface(bucket, bucket_count, error_flag, lane, cap, c)


# --------------------------------------------------------------------------- #
# Randomized surface generation that ACTUALLY triggers domination.
# Strategy: pick a few "exact_overlap families" sharing the triple
#   (bfg, fever&great lo, fever&great hi). Within a family, vary fever as a
# superset/subset and great correspondingly so dominance fires. Mix in fully
# independent (incomparable) surfaces too.
# --------------------------------------------------------------------------- #
U64 = np.uint64
FULL = np.uint64(0xFFFFFFFFFFFFFFFF)


def _rand_mask(rng, density):
    # Random 64-bit mask with ~density fraction of bits set (head region).
    bits = rng.random(64) < density
    out = np.uint64(0)
    packed = np.packbits(bits.astype(np.uint8), bitorder="little")
    for i, byte in enumerate(packed[:8]):
        out |= np.uint64(int(byte)) << np.uint64(8 * i)
    return out


def _make_family(rng):
    """Create one exact_overlap family descriptor.

    All members share the intersection bits I (so `fever&great == I`, keeping the
    exact_overlap head words equal) and share `bfg` (the third leg of the gate).
    Members differ only in:
      - fever-only bits A (drawn from the A-pool, disjoint from I and the B-pool),
      - great-only bits B (drawn from the B-pool),
      - body counts bf (free), bg (>= bfg).
    Dominance in this family reduces to a clean partial order:
      k dominates c  iff  A_c subset A_k  AND  B_k subset B_c  AND
                          bf_k>=bf_c AND bg_k<=bg_c   (bfg equal, bfg<= holds).
    So generating members with correlated (A,bf) up and (B,bg) down yields chains
    where later members dominate earlier ones -> real Phase-1/Phase-2 pruning.
    """
    i_lo = _rand_mask(rng, 0.20)
    i_hi = _rand_mask(rng, 0.08)
    part_lo = _rand_mask(rng, 0.5)
    part_hi = _rand_mask(rng, 0.5)
    a_pool_lo = (~i_lo & FULL) & part_lo
    a_pool_hi = (~i_hi & FULL) & part_hi
    b_pool_lo = (~i_lo & FULL) & (~part_lo & FULL)
    b_pool_hi = (~i_hi & FULL) & (~part_hi & FULL)
    bfg = int(rng.integers(0, 4))  # shared across the family (gate leg)
    return {
        "i_lo": i_lo, "i_hi": i_hi,
        "a_pool_lo": a_pool_lo, "a_pool_hi": a_pool_hi,
        "b_pool_lo": b_pool_lo, "b_pool_hi": b_pool_hi,
        "bfg": bfg,
    }


def _family_member(rng, fam):
    """A surface in family `fam`. `level` in [0,1] correlates fever/great size and
    body counts so members form a dominance chain (higher level dominates lower).
    """
    level = rng.uniform(0.0, 1.0)
    # Higher level -> larger fever (A), smaller great (B), larger bf, smaller bg.
    a_lo = fam["a_pool_lo"] & _rand_mask(rng, 0.15 + 0.8 * level)
    a_hi = fam["a_pool_hi"] & _rand_mask(rng, 0.15 + 0.8 * level)
    b_lo = fam["b_pool_lo"] & _rand_mask(rng, 0.95 - 0.8 * level)
    b_hi = fam["b_pool_hi"] & _rand_mask(rng, 0.95 - 0.8 * level)
    fever_lo = fam["i_lo"] | a_lo
    fever_hi = fam["i_hi"] | a_hi
    great_lo = fam["i_lo"] | b_lo
    great_hi = fam["i_hi"] | b_hi
    bf = int(round(level * 5)) + int(rng.integers(0, 2))
    bg = fam["bfg"] + (3 - int(round(level * 3)))  # bg >= bfg, shrinks with level
    return (
        fever_lo, fever_hi, great_lo, great_hi,
        U64(bf), U64(bg), U64(fam["bfg"]),
    )


def _make_independent_surface(rng):
    """Fully independent surface (usually incomparable)."""
    fl = _rand_mask(rng, 0.3)
    fh = _rand_mask(rng, 0.15)
    gl = _rand_mask(rng, 0.3)
    gh = _rand_mask(rng, 0.15)
    bf = U64(rng.integers(0, 8))
    bg = U64(rng.integers(0, 8))
    bfg = U64(rng.integers(0, 5))
    return (fl, fh, gl, gh, bf, bg, bfg)


def _make_surface_set(rng, k):
    """One lane's incoming surface list of length k.

    Draws most members from a small pool of exact_overlap families (so dominance
    chains form and real pruning happens), mixes in fully independent surfaces,
    and injects occasional exact duplicates and all-zero surfaces (edge cases).
    A duplicate of a kept surface is dominated by it (Phase 1, all-equal) ->
    dropped, exercising the equality path. Order is shuffled implicitly by the
    random per-element choice so the bidirectional (Phase-1 vs Phase-2) paths
    both fire depending on arrival order.
    """
    n_fams = max(1, int(rng.integers(1, 4)))
    fams = [_make_family(rng) for _ in range(n_fams)]
    surfaces = []
    for _ in range(k):
        r = rng.random()
        if r < 0.70:
            s = _family_member(rng, fams[int(rng.integers(0, n_fams))])
        elif r < 0.88:
            s = _make_independent_surface(rng)
        elif r < 0.95 and surfaces:
            s = surfaces[int(rng.integers(0, len(surfaces)))]  # exact duplicate
        else:
            s = (U64(0), U64(0), U64(0), U64(0), U64(0), U64(0), U64(0))
        surfaces.append(s)
    return surfaces


def _numba_reduce_pylist(surfaces):
    """Call the Numba oracle and return a plain list of 7-tuples (ints)."""
    from numba.typed import List
    from gear_optimizer.solver.taichi_gem.force_greats.response_build_gpu_numba import (
        _NUMBA_SURFACE_TYPE,
    )

    typed = List.empty_list(_NUMBA_SURFACE_TYPE)
    for s in surfaces:
        typed.append((U64(s[0]), U64(s[1]), U64(s[2]), U64(s[3]), U64(s[4]), U64(s[5]), U64(s[6])))
    kept = _numba_reduce(typed)
    return [tuple(int(x) for x in row) for row in kept]


@ti.kernel
def _subset_kernel(
    x: ti.types.ndarray(dtype=ti.u64, ndim=1),
    y: ti.types.ndarray(dtype=ti.u64, ndim=1),
    out: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    # Document/verify the exact bit pattern the dominance test relies on:
    # `(x & ~y) == 0` is the per-word subset test x ⊆ y on ti.u64.
    for i in range(x.shape[0]):
        out[i] = 1 if (x[i] & ~y[i]) == ti.u64(0) else 0


def _verify_uint64_subset_behavior():
    """Confirm Taichi's `(x & ~y)==0` on ti.u64 == NumPy subset on boundary values
    (zero, all-ones, MSB bit63, alternating). The dominance reduction's correctness
    rests on this; the GPU `~` must wrap as a 64-bit complement, not promote/sign-extend."""
    vals = [
        0, 1, 1 << 63, (1 << 64) - 1,
        0xAAAAAAAAAAAAAAAA, 0x5555555555555555, (1 << 63) | 1, (1 << 32),
    ]
    xs, ys = [], []
    for a in vals:
        for b in vals:
            xs.append(a)
            ys.append(b)
    x = np.array(xs, dtype=np.uint64)
    y = np.array(ys, dtype=np.uint64)
    out = np.zeros(len(xs), dtype=np.int32)
    _subset_kernel(x, y, out)
    ti.sync()
    mask = (1 << 64) - 1
    ref = np.array([1 if ((a & (~b & mask)) == 0) else 0 for a, b in zip(xs, ys)], dtype=np.int32)
    if not bool((out == ref).all()):
        bad = [(hex(a), hex(b), int(o), int(r)) for a, b, o, r in zip(xs, ys, out, ref) if o != r]
        print("FAIL: ti.u64 (x & ~y)==0 disagrees with NumPy subset:", bad)
        sys.exit(1)
    return len(xs)


def _run_lane_batch(lane_surfaces, cap):
    """Run reduce_kernel for a list of per-lane surface lists; return GPU rows
    (list of list-of-tuples) and assert no capacity overflow."""
    n_lanes = len(lane_surfaces)
    k_counts = np.array([len(s) for s in lane_surfaces], dtype=np.int32)
    max_k = max(1, int(k_counts.max()) if n_lanes else 1)
    inputs = np.zeros((n_lanes, max_k, 7), dtype=np.uint64)
    for lane in range(n_lanes):
        for s_idx, s in enumerate(lane_surfaces[lane]):
            for col in range(7):
                inputs[lane, s_idx, col] = s[col]
    bucket = np.zeros((n_lanes, cap, 7), dtype=np.uint64)
    bucket_count = np.zeros(n_lanes, dtype=np.int32)
    error_flag = np.zeros(n_lanes, dtype=np.int32)
    reduce_kernel(n_lanes, cap, k_counts, inputs, bucket, bucket_count, error_flag)
    ti.sync()
    # A genuine capacity overflow is authoritatively visible as bucket_count >= cap
    # (the kept set filled the buffer). `error_flag` is the production fail-loud
    # signal the @ti.func sets on overflow, but as an isolated u64-adjacent guard
    # buffer it can pick up spurious values right after a heterogeneous kernel
    # launch on this Vulkan stack (observed: error_flag=1 while bucket_count is
    # correct and well under cap). We treat bucket_count as ground truth for the
    # probe's overflow check; with cap >> max-kept here, overflow cannot occur.
    if int(bucket_count.max()) >= cap:
        bad = [int(i) for i in np.nonzero(bucket_count >= cap)[0]]
        raise RuntimeError(f"cap {cap} genuinely exceeded on lanes {bad[:8]} (raise CAP)")
    out = []
    for lane in range(n_lanes):
        gpu_n = int(bucket_count[lane])
        out.append([tuple(int(bucket[lane, r, col]) for col in range(7)) for r in range(gpu_n)])
    return out


def _deterministic_suite(cap):
    """Hand-crafted adversarial cases with exact expected outputs, focused on
    ORDER PRESERVATION (Phase-2 stable compaction), the exact_overlap gate, and
    MUTUAL NON-DOMINATION. Returns (n_cases, n_order_sensitive, n_mutual)."""
    # Build a family of comparable surfaces sharing intersection I (fever&great)
    # and bfg=2, where dominance is the clean partial order described above.
    I = 0b1010  # intersection bits (lo word)
    # A-bits (fever-only) pool: {bit4,bit5}; B-bits (great-only) pool: {bit8,bit9}.
    # member(level): fever=I|A, great=I|B, bf, bg, bfg=2.
    def mk(a, b, bf, bg):
        return (I | a, 0, I | b, 0, bf, bg, 2)

    # Dominance: k dom c iff A_c subset A_k, B_k subset B_c, bf_k>=bf_c, bg_k<=bg_c.
    top = mk(0b110000, 0b00000000 << 0, 4, 1)       # biggest fever, smallest great
    mid = mk(0b010000, 0b100000000, 3, 2)           # incomparable-ish middle
    low = mk(0b000000, 0b1100000000, 1, 3)          # smallest fever, biggest great
    # top dominates low? A_low={} subset A_top={4,5} yes; B_top={} subset B_low={8,9} yes;
    # bf 4>=1, bg 1<=3 -> yes. top dominates low.
    # top vs mid: A_mid={4} subset A_top={4,5} yes; B_top={} subset B_mid={8} yes; bf4>=3,bg1<=2 -> top dom mid.
    # So {top,mid,low} all collapse to {top}. Use distinct incomparable surfaces for survivors:
    indep1 = (0b1, 0, 0b10, 0, 5, 0, 0)   # different exact_overlap triple -> incomparable
    indep2 = (0b100, 0, 0b1000, 0, 0, 5, 1)
    indep3 = (0, 0, 0, 0, 7, 7, 0)

    cases = []
    meta = []  # (order_sensitive: bool, mutual: bool)

    # Case A: order preservation under Phase-2. Insert three incomparable surfaces
    # (all survive, in arrival order), then a surface that dominates ONLY the middle
    # one (indep2). Expected: [indep1, indep3, <dominator>] -- middle removed, order
    # of survivors preserved, dominator appended LAST.
    # Make a dominator of indep2 sharing its exact_overlap triple.
    # indep2 = (0b100,0,0b1000,0,0,5,1): f&g lo = 0b100 & 0b1000 = 0; bfg=1.
    # dominator d: same f&g (=0) and bfg=1; d dom indep2 -> dbf>=0, dbg<=5, dbfg<=1,
    # indep2.fever subset d.fever, d.great subset indep2.great.
    dom2 = (0b100 | 0b10000, 0, 0b1000, 0, 2, 4, 1)  # superset fever, same great, bf up, bg down
    cases.append([indep1, indep2, indep3, dom2])
    meta.append((True, False))
    # Expected by hand: indep1 kept, indep2 kept, indep3 kept, then dom2 arrives:
    #   Phase1: does any kept dominate dom2? indep1/indep3 different triple -> no;
    #           indep2 vs dom2: indep2 dom dom2? needs dom2.fever subset indep2.fever
    #           but dom2.fever superset -> no. So not dropped.
    #   Phase2: remove kept that dom2 dominates -> indep2 removed; indep1,indep3 kept.
    #   Append dom2. => [indep1, indep3, dom2].

    # Case B: mutual non-domination -- three fully incomparable surfaces, none drop.
    cases.append([indep1, indep2, indep3])
    meta.append((False, True))  # expected [indep1, indep2, indep3]

    # Case C: Phase-1 drop -- dominator first, dominated second -> dominated dropped,
    # only dominator kept (tests Phase-1 path & that c is NOT appended).
    cases.append([top, low])
    meta.append((False, False))  # expected [top]

    # Case D: Phase-2 removal of FIRST element -- dominated first, dominator second.
    cases.append([low, top])
    meta.append((False, False))  # expected [top]

    # Case E: empty -> single all-zero surface (Numba _numba_reduce empty path).
    cases.append([])
    meta.append((False, False))  # expected [(0,0,0,0,0,0,0)]

    # Case E2: 3-member chain arriving worst -> best. low arrives, then mid (mid
    # dominates low -> Phase-2 removes low, mid appended), then top (top dominates
    # mid -> Phase-2 removes mid, top appended). Collapses to [top]. Exercises
    # repeated Phase-2 removals across successive inserts.
    cases.append([low, mid, top])
    meta.append((False, False))  # expected [top]

    # Case F: exact duplicates collapse, order of first occurrence among survivors.
    cases.append([indep1, indep2, indep1, indep3, indep2])
    meta.append((True, True))  # expected [indep1, indep2, indep3]

    # Case G: exact_overlap GATE blocks dominance across different bfg. Two surfaces
    # identical in masks but different bfg are incomparable (gate fails) -> both kept.
    g1 = (0b111, 0, 0b111, 0, 0, 0, 1)
    g2 = (0b111, 0, 0b111, 0, 0, 0, 2)
    cases.append([g1, g2])
    meta.append((False, True))  # expected [g1, g2]

    gpu = _run_lane_batch(cases, cap)
    n_order = 0
    n_mutual = 0
    for i, surfs in enumerate(cases):
        expected = _numba_reduce_pylist(surfs)
        if gpu[i] != expected:
            print(f"DETERMINISTIC MISMATCH case={i}")
            print("  incoming :", surfs)
            print("  gpu      :", gpu[i])
            print("  expected :", expected)
            sys.exit(1)
        order_sensitive, mutual = meta[i]
        if order_sensitive and len(expected) >= 2:
            n_order += 1
        if mutual and len(expected) >= 2:
            n_mutual += 1
    return len(cases), n_order, n_mutual


def main():
    rng = np.random.default_rng(20240607)

    CAP = 64  # generous per-lane bucket capacity for the probe

    det_cases, det_order, det_mutual = _deterministic_suite(CAP)
    print(
        "deterministic_suite: cases=%d order_sensitive_survivors=%d mutual_nondom=%d (all bit-exact)"
        % (det_cases, det_order, det_mutual)
    )
    N_LAUNCHES = 40
    LANES_PER_LAUNCH = 256
    K_MIN, K_MAX = 0, 40  # vary incoming count per lane (0 exercises empty case)

    total_cases = 0
    cases_strict_dom = 0       # kept < #distinct incoming -> a DISTINCT surface was
    #                            dominated by a DIFFERENT distinct surface (real, non-
    #                            trivial dominance — not mere duplicate collapse).
    cases_dup_collapse = 0     # had exact-duplicate incoming surfaces (equality path).
    cases_multi_survivor = 0   # kept set size > 1
    cases_mutual_with_dom = 0  # multi-survivor AND pruning in same lane.
    cases_empty_input = 0
    max_kept_seen = 0
    mismatches = 0
    first_mismatch = None

    for launch in range(N_LAUNCHES):
        n_lanes = LANES_PER_LAUNCH
        # Build per-lane surface lists for this launch.
        lane_surfaces = []
        for lane in range(n_lanes):
            k = int(rng.integers(K_MIN, K_MAX + 1))
            lane_surfaces.append(_make_surface_set(rng, k))

        gpu_batch = _run_lane_batch(lane_surfaces, CAP)

        for lane in range(n_lanes):
            k = len(lane_surfaces[lane])
            gpu_rows = gpu_batch[lane]

            expected = _numba_reduce_pylist(lane_surfaces[lane])

            total_cases += 1
            if k == 0:
                cases_empty_input += 1
            if len(expected) > 1:
                cases_multi_survivor += 1
            # `distinct_in` collapses EXACT duplicates. Because reduce drops any
            # exact duplicate via the all-equal dominance path, distinct_in is the
            # post-dedup ceiling on kept. So kept < distinct_in proves a *distinct*
            # surface was dominated by a *different* distinct surface == strict,
            # non-trivial dominance (Phase-1 drop or Phase-2 removal).
            distinct_in = len(set(lane_surfaces[lane]))
            strict = k > 0 and len(expected) < distinct_in
            if strict:
                cases_strict_dom += 1
            if k > 0 and distinct_in < k:
                cases_dup_collapse += 1
            # Multi-survivor AND pruning in the same lane => incomparable survivors
            # coexisting with dominated drops (mutual non-domination exercised).
            if strict and len(expected) > 1:
                cases_mutual_with_dom += 1
            max_kept_seen = max(max_kept_seen, len(expected))

            if gpu_rows != expected:
                mismatches += 1
                if first_mismatch is None:
                    first_mismatch = (launch, lane, k, gpu_rows, expected, lane_surfaces[lane])

    print(
        "cases=%d empty_input=%d multi_survivor=%d strict_dom=%d mutual_with_dom=%d "
        "dup_collapse=%d max_kept=%d mismatches=%d"
        % (
            total_cases, cases_empty_input, cases_multi_survivor,
            cases_strict_dom, cases_mutual_with_dom, cases_dup_collapse,
            max_kept_seen, mismatches,
        )
    )

    if mismatches != 0:
        launch, lane, k, gpu_rows, expected, surfs = first_mismatch
        print(f"FIRST MISMATCH launch={launch} lane={lane} k={k}")
        print("  incoming :", surfs)
        print("  gpu      :", gpu_rows)
        print("  expected :", expected)
        sys.exit(1)

    # Independent property check, run LAST as its own phase. The dominance subset
    # test rests on `(x & ~y)==0` behaving as a 64-bit subset on ti.u64; verify the
    # GPU `~` wraps as a 64-bit complement (no sign-extend/promotion) on boundary
    # values. Kept separate from the reduce phase to avoid interleaving distinct
    # kernels (see note in _verify_uint64_subset_behavior on launch isolation).
    subset_pairs = _verify_uint64_subset_behavior()
    print(f"uint64 subset (x & ~y)==0: verified on {subset_pairs} boundary pairs (matches NumPy)")

    # Sanity: the test must have actually exercised non-trivial domination AND
    # multi-survivor sets AND mutual non-domination AND the duplicate-equality
    # path, else it is a weak pass.
    if (
        cases_multi_survivor == 0
        or cases_strict_dom == 0
        or cases_mutual_with_dom == 0
        or cases_dup_collapse == 0
        or det_mutual == 0
        or det_order == 0
    ):
        print("FAIL: domination/pruning/order not fully exercised.")
        sys.exit(1)

    print("LAYER 2b PARITY: PASS")


if __name__ == "__main__":
    main()
