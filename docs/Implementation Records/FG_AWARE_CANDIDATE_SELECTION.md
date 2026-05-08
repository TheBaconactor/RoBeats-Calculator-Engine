# ADR: FG-Aware Candidate Selection (Eliminate the Top-K Base-Score Funnel)

Date: 2026-04-07

Status: **Rejected** (experimentally refuted 2026-04-07)

## Context

The current pipeline selects FG candidates using a **base-score-only top-K funnel**:

1. Exact skyline produces N survivors (potentially thousands of combined gear/mini pairs).
2. All N are GPU base-scored via `dispatch_registry_solve`.
3. A min-heap of size `keep_top_k = max(LOADOUTS_PER_SONG_LIMIT, FG_CANDIDATE_LIMIT) = 51` retains only the
   top-51 by base score.
4. Only these 51 enter the FG pipeline.

The problem: the FG delta can be **massive** (749K–1.86M observed on real songs). A loadout ranked #52 by base
score could become #1 after FG. The base-score funnel is lossy — it can silently drop the global winner.

This is a structural gap between the skyline layer (proven minimal for base scoring) and the FG layer (proven
exact for forced-count optimization). The layers are individually optimal, but the funnel between them is not.

## Decision

Replace the base-score-only funnel with an **FG-aware funnel** that accounts for each loadout's FG potential:

1. For each unique topology cell `(FT, FF)` in the search window, precompute the **maximum achievable FG delta**
   using the exact DP. This is cheap: ~300 states × ~20 transitions per cell, and the DP is now production-grade
   (`fg_exact_dp_sparse_full_kernel`).

2. During the skyline scoring pass, for each candidate loadout, compute:
   ```
   fg_aware_score = base_score + max_FG_delta(topology_cell(FT, FF))
   ```
   where `max_FG_delta` uses the precomputed per-cell upper bound.

3. The top-K heap ranks by `fg_aware_score` instead of `base_score`. This guarantees that no loadout whose
   actual `base + FG` could beat the current top-K is discarded.

The per-cell FG delta is an upper bound (computed with representative stats), so the funnel is **safe**: it
may retain more candidates than necessary but will never drop the true winner.

## Consequences

Positive:

- Provably safe funnel: the global winner is never dropped by the top-K selection.
- Cheap overhead: FG DP per topology cell is ~6,000 operations; with ~121 cells in the ±5 search window,
  that is ~726K operations total (sub-millisecond on GPU).
- No change to the downstream FG pipeline — only the candidate selection criterion changes.

Tradeoffs:

- The FG upper bound is computed with representative stats, not per-loadout stats. The bound is safe but
  may over-estimate, causing more candidates to pass the funnel. In practice, FG delta variation across
  loadouts with the same topology cell is small (the delta is dominated by song structure, not loadout stats).
- Requires precomputing per-cell FG deltas before the scoring pass, adding a small upfront cost.
- The `keep_top_k` parameter may need to increase if the FG-aware bound admits more candidates (tunable).

## Verification

- Compare the FG-aware funnel's selected candidates against an exhaustive evaluation (all skyline survivors
  scored with actual FG) to confirm the true winner is always retained.
- Measure overhead: wall-clock cost of per-cell FG precomputation vs total skyline scoring time.

## Experimental Result (2026-04-07)

Tested on 3 songs (362–7,027 notes), 200 random stat vectors each (uniform and adversarial CM/FM distributions).

**Finding:** The (base+FG) winner is always at base rank #1. Pearson correlation between base score and
total score is 0.9997+ across all tests. Worst observed rank shift is ±1 position. The FG/base ratio
varies by only ~2.8% across candidates.

**Root cause:** FG delta scales as `bv × cm × f(fm)`, the same factors that dominate base score. The
proportionality is strong enough that the base-score ranking is virtually identical to the total-score
ranking for any realistic stat distribution.

**Conclusion:** The base-score funnel is inherently safe. This proposal adds complexity for zero
practical benefit. **Rejected.**

See `tools/bench/research_pipeline_breakthroughs.py` and `artifacts/research_pipeline_breakthroughs.json`
for full experimental data.

## References

- `gear_optimizer/solver/exact_skyline.py`: `keep_top_k` heap in `_evaluate_product_gpu_batched` and
  `_evaluate_combined_skyline_gpu_batched`.
- `gear_optimizer/solver/taichi_gem/force_greats/kernels.py`: `fg_exact_dp_sparse_full_kernel`.
- `gear_optimizer/core/constants.py`: `FG_CANDIDATE_LIMIT`, `LOADOUTS_PER_SONG_LIMIT`.
