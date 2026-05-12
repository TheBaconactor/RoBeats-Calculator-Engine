# CM/FM Rectangle Branch Bound

Date: 2026-05-11

## Invariant

Inside a fixed exact-inner scoring invocation, a block of `(CM gems, FM gems)` cells may be skipped only when a certified upper bound proves that no allocation in the block can beat the invocation's current legal incumbent.

The production rule is:

```text
skip block Q when UB(Q) <= best_score
```

where `best_score` is a real score already achieved by the same exact-inner solve.

## Bound

For a rectangle:

```text
Q = [cm0, cm1] x [fm0, fm1]
```

the bound independently maximizes:

```text
CM multiplier at cm1
FM multiplier at fm1
PP/overflow prefix value using the largest leftover budget at cm0 + fm0
lane-base value at the best CM endpoint and best FM endpoint relative to overflow
```

The lane-base upper value is:

```text
base_init
+ budget * w_OV
+ cm_endpoint * (w_CM - w_OV)
+ fm_endpoint * (w_FM - w_OV)
+ best_pp_prefix_extra(max_leftover)
```

where `cm_endpoint` is `cm1` when `w_CM >= w_OV`, otherwise `cm0`, and `fm_endpoint` is chosen the same way.

These maxima need not be jointly achievable. That is intentional: the relaxation can overestimate every legal cell in the rectangle, but cannot underestimate one.

The resulting relaxed `(base, CM, FM)` triple is passed through the existing semi-exact score upper bound. If the block survives, the existing per-cell upper bound and exact score calculation still run unchanged.

## Production Placement

The branch bound lives in `optimize_core_device_exact_bound_preloaded_bits(...)`, wrapping the existing CM/FM cell enumeration in the shared Taichi exact-inner allocator.

The block size is fixed in code at:

```text
CM block = 4
FM block = 8
```

This is intentionally not a behavior flag. It is a local proof-preserving search-order optimization in the exact-inner solver.

## Why It Is Lossless

For every legal cell `(cm, fm)` inside a block:

```text
CM(cm) <= CM(cm1)
FM(fm) <= FM(fm1)
PP/OV best for leftover(cm, fm) <= PP/OV best for max_leftover
lane_base(cm, fm) <= relaxed lane endpoint bound
```

under the project invariant that the reference arrays are nondecreasing by stat index.

The exact score formula for a fixed fever mask is monotone in `base`, `CM`, and `FM`. Therefore every exact score in the block is at most `UB(Q)`.

If `UB(Q) <= best_score`, the block cannot improve the current exact-inner result, so skipping it preserves the exact optimum for that invocation.

## Scope

This is not a candidate prune and not a base-to-FG theorem. It does not remove loadouts, mini teams, timing responses, or retained FG candidates.

It only avoids allocator work inside one fixed timeline/mask scoring invocation. The same proof applies to generated FG fixed-mask inner scoring because any FG penalty or outer state is outside the non-timing allocation block and is constant for that invocation.

## Profile

Profile target:

```text
00 (Hard) by garlagan
```

Compared against the previous default with timing response antichain and certified response upper-bound cull:

```text
wall:               29.636s -> 19.652s
solve_total:         27.432s -> 17.513s
base_pair_eval_gpu:  17.662s ->  8.384s
base score:       34,253,930 unchanged
FG score:         34,259,925 unchanged
```

The bound attacks the exact-inner allocator directly, which was the remaining dominant cost after timing-response antichain pruning.
