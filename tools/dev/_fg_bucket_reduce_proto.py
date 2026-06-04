"""Host-side correctness prototype for Agent-1's bucketed Phase-3 reduction.

The production `_append_surface` (response_build_gpu_taichi.py:433) is the O(F^2)
non-monotone bidirectional dominance reduction that PROFILES as 45-83% of per-key
GPU time. The dominance is GATED by `exact_overlap` = (body_fever_great,
fever&great_lo, fever&great_hi): surfaces in different exact_overlap classes can
NEVER dominate each other. Therefore:

  reduce_allpairs(S)  ==  concat over classes c of  reduce_allpairs(S_c)         (as SETS)

This script PROVES that (set-equality) with randomized structural tests, and also
validates the Branch-A fast path: when fever_mask==0 (every `_body_prefix_surface`
surface), the class key collapses to body_fever_great alone, and within a class the
great mask is a PREFIX so the order is 3-D scalar maxima (bf up, bg down, hgc down),
computable by a sort + 1-D Fenwick prefix-max (the existing `_skyline_compact` shape).

No GPU, no repo imports. Pure logic. Run: python -u tools/dev/_fg_bucket_reduce_proto.py
"""
import random
from collections import defaultdict

# A surface is a 5-tuple of Python ints: (fever_mask, great_mask, bf, bg, bfg).
# fever_mask / great_mask are <=100-bit head sets (single bigint; the kernel splits
# them lo/hi but the dominance is identical on the combined set). bf=body_fever,
# bg=body_great, bfg=body_fever_great are body counts.


def subset(a, b):
    # a ⊆ b  on bit-sets, precision-safe for Python bigints.
    return (a | b) == b


def dominates(k, c):
    # k ⪰ c  (k dominates c; c may be dropped in favor of k). EXACT port of the
    # _append_surface partial order: gated by exact_overlap, then bf>=, bg<=,
    # fever: c⊆k (toward dominator), great: k⊆c (toward dominated). bfg equal by gate.
    kf, kg, kbf, kbg, kbfg = k
    cf, cg, cbf, cbg, cbfg = c
    exact_overlap = (cbfg == kbfg) and ((cf & cg) == (kf & kg))
    return (
        exact_overlap
        and kbf >= cbf and kbg <= cbg
        and subset(cf, kf)   # cf ⊆ kf
        and subset(kg, cg)   # kg ⊆ cg
    )


def reduce_allpairs(surfaces):
    # EXACT incremental algorithm from _numba_append_surface: process in order,
    # drop c if any kept dominates it, else drop kept that c dominates + append c.
    kept = []
    for c in surfaces:
        if any(dominates(k, c) for k in kept):
            continue
        kept = [k for k in kept if not dominates(c, k)]
        kept.append(c)
    return kept


def eo_key(s):
    f, g, bf, bg, bfg = s
    return (bfg, f & g)   # (body_fever_great, fever&great head set)


def reduce_bucketed(surfaces):
    # Partition by exact_overlap key; reduce within each class with the SAME
    # all-pairs logic; concatenate survivors. Should equal reduce_allpairs as a set.
    buckets = defaultdict(list)
    for s in surfaces:
        buckets[eo_key(s)].append(s)
    out = []
    for b in buckets.values():
        out.extend(reduce_allpairs(b))
    return out


# --------------------------------------------------------------------------- #
# Branch-A 3-D Fenwick maxima. Surfaces have fever_mask==0 and great_mask is a
# PREFIX (1<<hgc)-1, so hgc = popcount(great) and great-subset <=> hgc<=. Within a
# bfg-class the order is (bf up, bg down, hgc down). Compute maxima via:
#   sort (hgc asc, bg asc, bf desc); Fenwick prefix-max of bf over bg; keep iff
#   bf STRICTLY exceeds prefix-max over [0..bg]. Mirrors _skyline_compact strict>.
# --------------------------------------------------------------------------- #
class Fenwick:
    def __init__(self, size):
        self.n = size + 2
        self.v = [-1] * (self.n + 1)

    def query(self, idx):  # prefix-max over [0..idx]
        best = -1
        cur = idx + 1
        while cur > 0:
            if self.v[cur] > best:
                best = self.v[cur]
            cur -= cur & (-cur)
        return best

    def update(self, idx, value):  # point-max
        cur = idx + 1
        while cur < self.n:
            if value > self.v[cur]:
                self.v[cur] = value
            cur += cur & (-cur)


def reduce_branchA_fenwick(surfaces):
    # bg-axis variant (Fenwick width ~ max_bg, can be ~n). Kept for cross-check.
    by_bfg = defaultdict(list)
    for s in surfaces:
        f, g, bf, bg, bfg = s
        assert f == 0, "Branch-A requires fever_mask==0"
        hgc = bin(g).count("1")
        assert g == ((1 << hgc) - 1), "Branch-A requires prefix great mask"
        by_bfg[bfg].append((hgc, bf, bg, g))
    out = []
    for bfg, pts in by_bfg.items():
        max_bg = max(p[2] for p in pts)
        fen = Fenwick(max_bg)
        # dominators-first within equal hgc: (hgc asc, bg asc, bf desc)
        pts.sort(key=lambda p: (p[0], p[2], -p[1]))
        for hgc, bf, bg, g in pts:
            prev = fen.query(bg)        # max bf among inserted with bg'<=bg (all hgc'<=hgc)
            if bf > prev:
                out.append((0, g, bf, bg, bfg))
            fen.update(bg, bf)
    return out


def reduce_branchA_fenwick_hgcaxis(surfaces):
    # hgc-AXIS variant (THE ONE TO PORT): Fenwick over hgc (width<=101, tiny).
    # Sweep bg ASCENDING; Fenwick prefix-max of bf over hgc; keep iff bf>prefix.
    # Sort (bfg, bg asc, hgc asc, bf desc); coalesce equal (bfg,bg,hgc) -> max bf.
    by_bfg = defaultdict(list)
    for s in surfaces:
        f, g, bf, bg, bfg = s
        assert f == 0, "Branch-A requires fever_mask==0"
        hgc = bin(g).count("1")
        assert g == ((1 << hgc) - 1), "Branch-A requires prefix great mask"
        by_bfg[bfg].append((hgc, bf, bg, g))
    out = []
    for bfg, pts in by_bfg.items():
        max_hgc = max(p[0] for p in pts)
        fen = Fenwick(max_hgc)
        pts.sort(key=lambda p: (p[2], p[0], -p[1]))  # bg asc, hgc asc, bf desc
        for hgc, bf, bg, g in pts:
            prev = fen.query(hgc)       # max bf among inserted with hgc'<=hgc (all bg'<=bg)
            if bf > prev:
                out.append((0, g, bf, bg, bfg))
            fen.update(hgc, bf)
    return out


# --------------------------------------------------------------------------- #
# Randomized structural tests.
# --------------------------------------------------------------------------- #
def canon(surfaces):
    return frozenset(surfaces)


def gen_branchB(rng, n_surf, mask_bits=12, cnt_hi=12):
    out = []
    for _ in range(n_surf):
        f = rng.getrandbits(mask_bits)
        g = rng.getrandbits(mask_bits)
        bf = rng.randint(0, cnt_hi)
        bg = rng.randint(0, cnt_hi)
        bfg = rng.randint(0, 4)
        out.append((f, g, bf, bg, bfg))
    return out


def gen_branchA(rng, n_surf, hgc_hi=24, cnt_hi=16, bfg_hi=6):
    out = []
    for _ in range(n_surf):
        hgc = rng.randint(0, hgc_hi)
        g = (1 << hgc) - 1
        bf = rng.randint(0, cnt_hi)
        bg = rng.randint(0, cnt_hi)
        bfg = rng.randint(0, bfg_hi)
        out.append((0, g, bf, bg, bfg))
    return out


def main():
    rng = random.Random(0xF6)
    n_trials = 4000

    # Test 1: bucketing is lossless (Branch B, general masks).
    fails = 0
    bucket_ratio_sum = 0.0
    worst_bucket = 0
    for t in range(n_trials):
        S = gen_branchB(rng, rng.randint(1, 60))
        a = canon(reduce_allpairs(S))
        b = canon(reduce_bucketed(S))
        if a != b:
            fails += 1
            if fails <= 3:
                print(f"  [B] MISMATCH trial {t}: allpairs={len(a)} bucketed={len(b)}")
        # bucket-fragmentation stat on the reduced set
        buckets = defaultdict(int)
        for s in a:
            buckets[eo_key(s)] += 1
        if buckets:
            worst_bucket = max(worst_bucket, max(buckets.values()))
            bucket_ratio_sum += max(buckets.values()) / max(1, len(a))
    print(f"Test 1 (bucketing lossless, Branch B): {n_trials - fails}/{n_trials} pass; "
          f"worst output bucket={worst_bucket}, mean max-bucket/F={bucket_ratio_sum/n_trials:.3f}")

    # Test 2: Branch-A Fenwick maxima == all-pairs (both axis variants).
    failsA = 0
    failsH = 0
    for t in range(n_trials):
        S = gen_branchA(rng, rng.randint(1, 80))
        a = canon(reduce_allpairs(S))
        f = canon(reduce_branchA_fenwick(S))
        h = canon(reduce_branchA_fenwick_hgcaxis(S))
        if a != f:
            failsA += 1
        if a != h:
            failsH += 1
            if failsH <= 5:
                print(f"  [A-hgc] MISMATCH trial {t}: allpairs={len(a)} hgcaxis={len(h)} "
                      f"missing={sorted(a - h)[:2]} extra={sorted(h - a)[:2]}")
    print(f"Test 2a (Branch-A bg-axis Fenwick == all-pairs):  {n_trials - failsA}/{n_trials} pass")
    print(f"Test 2b (Branch-A hgc-axis Fenwick == all-pairs): {n_trials - failsH}/{n_trials} pass  [PORT THIS]")

    # Test 3: stress dedup + degenerate (all identical, all incomparable, single).
    edge_fails = 0
    edge_cases = [
        [(0, 7, 5, 3, 1)] * 10,                                    # all identical
        [(0, (1 << i) - 1, i, i, 0) for i in range(20)],           # chain-ish
        [(0, 0, 0, 0, 0)],                                          # single zero
        [(0, (1 << k) - 1, k % 5, (k * 3) % 7, k % 3) for k in range(50)],
    ]
    for i, S in enumerate(edge_cases):
        a = canon(reduce_allpairs(S))
        b = canon(reduce_bucketed(S))
        ok = a == b
        if all(s[0] == 0 and s[1] == ((1 << bin(s[1]).count("1")) - 1) for s in S):
            f = canon(reduce_branchA_fenwick(S))
            h = canon(reduce_branchA_fenwick_hgcaxis(S))
            ok = ok and (a == f) and (a == h)
        if not ok:
            edge_fails += 1
            print(f"  [E] edge case {i} MISMATCH: allpairs={len(a)}")
    print(f"Test 3 (edge cases): {len(edge_cases) - edge_fails}/{len(edge_cases)} pass")

    ok = (fails == 0 and failsA == 0 and failsH == 0 and edge_fails == 0)
    print("\nRESULT:", "ALL PASS — bucketed + Branch-A Fenwick are set-exact" if ok else "FAILURES PRESENT")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
