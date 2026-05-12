# ADR: Local Gear Response Prune

Date: 2026-05-12

Status: Accepted

## Context

The skyline path already has three exact reductions before exact base scoring:
fixed-final-timing gear reduction, mini response-envelope reduction, and product
response-envelope reduction. The missing symmetric case was a local gear theorem:
a gear row may be unsafe to delete globally because it is useful with some minis,
but a concrete `(gear, mini)` pair can be replayable by another gear with the
same mini after the fixed-timing combined frontier is known.

FG remains the retained-candidate mechanic: production still scans the configured
Top-51 base loadouts in the default `SKYLINE_FG_CANDIDATES=topk` scope. This
record does not claim a full-FG frontier theorem. It adds a base-score certificate
that removes work before exact base scoring in the same default retained-candidate
scope used by the existing mini and product response reductions.

## Decision

Add `gear_optimizer/solver/gear_response_prune.py` and wire it into
`exact_skyline.py` after the local mini pair filter and before the product
response-envelope prune.

For a fixed retained candidate set from the combined timing-cell skyline, pair
`(gear_a, mini_m)` may delete `(gear_b, mini_m)` only when:

1. the source pair is already present in the current candidate array;
2. both pairs use the same mini row;
3. `gear_a` has no-worse `PP`, `CM`, `FM`, and lane-base than `gear_b`, with a
   strict improvement or deterministic canonical tie;
4. both concrete pairs have the exact same timing response envelope: for every
   base-visible timing pack, the maximum residual non-timing gem budget is the
   same.

The theorem is pair-local. It does not remove `gear_b` from the gear frontier and
it never invents a replacement pair that was not already admitted by the combined
frontier.

## Proof Sketch

For any exact base solution using `(gear_b, mini_m)`, choose the same timing pack
and residual non-timing gem budget from `(gear_a, mini_m)`. Exact timing response
equality guarantees that this replay is feasible. The mini contribution is
identical, and `gear_a` supplies no-worse `PP`, `CM`, `FM`, and lane-base before
the non-timing gem allocator. Under the existing response-prune monotonicity
gates, replaying the target's non-timing gem allocation on the source pair cannot
lower the exact base score. Therefore the deleted pair cannot uniquely improve
the base candidate set.

The implemented equality certificate is intentionally narrower than full local
response containment. Full containment would allow a source pair to have a
strictly better timing menu, but that requires a more expensive target/source
cover index. Equality is the production-shaped certificate because it is cheap to
bucket and query after the combined frontier is already materialized.

## Safety Gates

The reducer returns the input frontier unchanged when any gate fails:

- `FT` or `FF` gems contribute to lane base;
- overflow lane gain is below a displaced non-timing stat-gem lane gain;
- `Perfect Points`, `Combo Multiplier`, or `Fever Multiplier` reference arrays
  are missing or nonmonotone;
- `Fever Multiplier` can drop below `1.0`;
- pre-gem visible stats or timing coordinates are negative;
- the unique-gear dominance matrix would exceed
  `MAX_LOCAL_GEAR_RESPONSE_MATRIX_CELLS`;
- an individual `(mini, response_signature)` bucket would exceed
  `MAX_LOCAL_GEAR_RESPONSE_BUCKET_CELLS`.

If a bucket exceeds the bound, only that bucket is skipped. Other buckets remain
eligible for certified deletion.

## FG Scope

The pass is enabled only for `SKYLINE_FG_CANDIDATES=topk`. It is skipped for
`all` and `sample`, preserving those modes as research/inspection modes for the
full or expanded frontier. The native FG summary records the skip/certification
reason so telemetry can distinguish a theorem miss from a mode guard.

## Telemetry

The native FG summary now records:

```text
gear_response_reason
gear_response_enabled
gear_response_candidates_in
gear_response_candidates_out
gear_response_pruned
gear_response_gear_rows
gear_response_matrix_cells
gear_response_mini_groups
gear_response_response_buckets
gear_response_timing_cells
gear_response_timing_packs
gear_response_dominance_pairs
gear_response_equal_hits
gear_response_skipped_buckets
```

Phase telemetry records:

```text
gear_response_prune_cpu
gear_response.timing
gear_response.index
gear_response.query
```

The old top-level import of Taichi-backed skyline modules in `exact_skyline.py`
was also made lazy. This is not a production CPU fallback; it only keeps pure
frontier helpers importable in non-GPU unit tests and moves GPU imports to the
functions that actually execute GPU work. `ftff_combos` was moved to the pure
solver package with a Taichi-package compatibility wrapper for the same reason.

## Follow-up Engineering Optimization

A production 00 (Hard) profile reported `gear_response_reason =
"gear_response_matrix_too_large"` and about `0.266s` CPU overhead. The no-op
path now checks the unique gear-row count before monotonicity scans, negative-row
scans, timing-response construction, or `np.unique(..., return_inverse=True)`.
The matrix gate uses a boolean presence bitmap over gear rows, so an over-budget
case returns after an O(candidate rows + gear rows) probe without sorting.

The pass also builds the gear dominance matrix before timing signatures. If no
gear row can dominate any other active gear row, it returns
`gear_response_reason = "no_gear_dominance"` without building exact timing
envelopes. Negative-row safety checks are limited to active gear and mini rows;
unused legacy/sentinel rows no longer disable a local theorem that never touches
them.

Synthetic no-op experiment on 600,000 candidate pairs with 20,000 active gear
rows, forcing the matrix gate:

```text
old np.unique(return_inverse=True)-style probe mean: 0.051980s
new bitmap matrix-gate path mean:                0.002252s
reason: gear_response_matrix_too_large
gear_rows: 20000
matrix_cells: 400000000
```

## Verification

- `python -m pytest -q tests/test_gear_response_prune.py tests/test_response_envelope_prune.py tests/test_mini_response_prune.py tests/test_timing_response_antichain.py tests/test_fixed_timing_prefix_skyline.py tests/test_exact_skyline_frontier_contracts.py`
  - original result: `27 passed`
  - follow-up result with no-op-gate tests and native FG dedupe tests: `32 passed`
- `python -m py_compile gear_optimizer/solver/gear_response_prune.py gear_optimizer/solver/ftff_combos.py gear_optimizer/solver/taichi_gem/ftff_combos.py gear_optimizer/solver/timing_response_antichain.py gear_optimizer/solver/exact_skyline.py tests/test_gear_response_prune.py`
  - result: passed
- `python -m ruff check ...`
  - not run in this container because `ruff` is not installed in the active
    Python environment.

Synthetic experiments:

- Pure bucket/index experiment: `7,680 -> 5,220` pairs, `2,460` certified
  deletions, dominance-index build `0.000973s`, bucket query `0.012188s`.
- End-to-end local response experiment with timing signatures: `960 -> 210`
  pairs, `750` certified deletions, total `1.055403s`; almost all time was the
  exact timing-envelope signature build (`1.054013s`), while dominance indexing
  and query were sub-millisecond to millisecond scale.

No Vulkan/Taichi profile was run in this container because the `taichi` package
is not installed here. The patch keeps the GPU-first production path intact and
moves only pure-test imports away from eager Taichi loading.

## Consequences

Positive:

- adds the missing symmetric pair-local gear theorem;
- deletes only candidates with an explicit same-mini, same-response witness;
- reports enough telemetry to prove whether runtime is helped on real songs;
- removes an import-time GPU-runtime dependency from pure skyline tests.

Tradeoffs:

- equality response buckets are incomplete and leave broader timing-containment
  opportunities on the table;
- the timing signature build is the dominant CPU overhead, so real-song telemetry
  should decide whether to broaden or narrow the theorem further;
- the pass is intentionally scoped to default top-k retained-candidate mode and
  does not change the all/sample research frontiers.
