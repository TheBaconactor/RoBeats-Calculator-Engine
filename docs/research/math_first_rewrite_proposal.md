# Math-First Rewrite Proposal: Exact State-Space Reductions for the GPU-Resident GA→FG Pipeline

## Thesis

This rewrite assumes the baseline already contains the ordinary systems machinery: exact-reuse plumbing, GPU-resident GA→FG candidate staging, and frontier-style FG candidate management. Under that stricter lens, the proposal should claim novelty only where it provably reduces the **amount or cost of exact work**. The revised design therefore moves the headline away from caching/scheduling and toward two theorem-grade reductions:

1. **Primary deployable contribution:** an exact FG interval-path dynamic program whose transition cost is an order statistic over prefix penalties, together with a dual safe upper bound.
2. **Primary GA contribution:** an exact song-specific topology-cell reduction for best gem allocation, so each GA miss is cheaper even when duplicate rates are low.
3. **Supporting contribution, not the headline:** retain the existing exact-only reuse and GPU handoff mechanisms as infrastructure rather than as the claimed breakthrough.

## 1. Problem statement and constraints

The KPI is integrated songs/hour with FG fully completed, under GPU-first execution, no score-semantic changes, and deterministic benchmarking. The provided baseline profile makes the strategic target clear:

- `ga_gpu`: 47.8% of mean stage time
- `fg_run`: 22.3%
- all remaining stages combined: 29.9%

So a mathematically serious throughput plan has to reduce exact work in `ga_gpu` and/or `fg_run`; ordinary scheduling wins alone are not enough.

## 2. Facts, assumptions, and validation

### Facts from the prompt

- The baseline already has a GPU-native candidate table and exact-only canonical reuse.
- GA evaluation includes a best gem allocation over a fixed ten-stat vector.
- FG decisions cascade because early fever delays shift later sections.
- The design space explicitly allows mathematical reductions, DP reframes, and provably safe bounds.

### Assumptions introduced in this rewrite

- The production base scorer factors through the fixed-point stat vector plus a small set of discrete score-relevant flags.
- A material fraction of `ga_gpu` is currently spent inside the best-gem allocator rather than only in trivial stat aggregation.
- Great penalties and fever bonuses are already available in exact fixed-point units or can be emitted that way from the exact scorer.

### Validation gates before deployment

- Golden-corpus equivalence: rewritten GA miss path must match the current exact base scorer bit-for-bit.
- Golden-corpus equivalence: rewritten FG solver must match the current exact FG result bit-for-bit.
- Break-even accounting: if the topology-cell lookup or FG bound overhead dominates on some songs, the system must be able to fall back to the current exact path.

## 3. What changes and what does not

This rewrite is intentionally narrow.

### Not the novelty claim

The proposal does **not** take credit for:
- GPU-resident handoff by itself,
- generic dedup tables by themselves,
- frontier-style FG staging by itself,
- host/device boundary smoothing by itself.

Those may all exist already and can remain in the implementation.

### The actual novelty claim

The novelty is that the exact work units themselves become smaller:

| Baseline exact work | Rewritten exact work |
|---|---|
| For each GA miss, run a generic best-gem optimizer over the full search space. | For each GA miss, locate a song-specific `(FF, FT)` topology cell and solve a smaller exact subproblem inside that cell. |
| For each FG solve, repeatedly recompute the direct cost of delaying activation by forcing Greats in a prefix. | For each FG solve, use an interval-DP in which the delay cost is the sum of the `k` cheapest prefix penalties, maintained incrementally. |
| Optional pruning depends on generic heuristics or none at all. | Use two exact-safe bounds: a song-local FG envelope and a dual upper bound inside the FG DP. |

## 4. Mathematical core I: exact FG reduction

### 4.1 Setup

For a fixed candidate and song, let:

- `raw_fill = (N - L) * 0.333 * FF`
- `notes_to_fill(k) = ceil(raw_fill + 0.5k)`
- `p_i` = exact direct score loss from forcing note `i` from Perfect to Great outside fever
- `b_i` = exact fever bonus of note `i` if it lands in fever

The key property from the prompt is that forcing `k` Greats before activation changes the next activation index only through the **count** `k`, because `notes_to_fill(k)` depends only on `k`.

### 4.2 Prefix-separability theorem

**Theorem 1 (prefix-separability).** Fix a non-fever segment and suppose the next fever activation is required to happen at eligible rank `m`. Then:

1. the resulting fever timeline depends only on `m`, not on which particular prefix notes were downgraded;
2. the minimum direct penalty needed to realize that delay is the sum of the `k_min(m)` smallest penalties in the relevant prefix, where

`k_min(m) = min { k >= 0 : ceil(raw_fill + 0.5k) = m }`.

**Proof sketch.** The activation rule depends only on the number of Greats introduced before activation. Any subset of `k` forced Greats in the prefix produces the same fill deficit and therefore the same activation rank. Once `m` is fixed, the direct loss is minimized by choosing the `k_min(m)` smallest prefix penalties.

### 4.3 Exact DP recurrence

Let state `s` be the start of a non-fever segment after accounting for the transition-note rule. Let `u_1, u_2, ...` be the fill-eligible notes reachable from `s`. For activation rank `m` define:

- `a_s(m) = u_m`
- `C_s(m)` = sum of the `k_min(m)` smallest penalties among `{ p_{u_1}, ..., p_{u_{m-1}} }`
- `B_s(m)` = sum of fever bonuses collected by the fever window that starts at `a_s(m)`
- `next(s, m)` = the next non-fever state after that fever window ends

Then the exact FG value satisfies:

`DP(s) = max_m [ B_s(m) - C_s(m) + DP(next(s, m)) ]`.

This is an exact longest-path / weighted-interval DP on a DAG of fever activations.

### 4.4 Dual safe upper bound

The prefix-cost functional has the dual identity

`P_k(prefix) = max_tau [ k*tau - sum_j (tau - p_j)_+ ]`.

Therefore for any chosen `tau`, the FG value from a candidate activation satisfies

`value <= reward - k*tau + sum_j (tau - p_j)_+ + future_upper_bound`.

This yields a family of safe upper bounds. On GPU, a small fixed bank of `tau` values can be evaluated cheaply; the maximum bound controls pruning of late activations without risking false prune.

### 4.5 GPU mapping

The rewritten FG kernel keeps the existing batching/frontier infrastructure but changes the exact solver:

1. stream penalties and bonuses in note order,
2. maintain prefix order-statistic state (for example a histogram/Fenwick structure over exact fixed-point penalty buckets or an incremental selection heap),
3. compute `C_s(m)` incrementally,
4. apply the dual upper bound,
5. recurse or iterate over interval-DP states.

### 4.6 Why this remains net-new under a strong baseline

Even if the current baseline already groups FG candidates well, this reduction still matters because it lowers the **cost per exact FG solve**. The claim is about the exact kernel, not about frontier plumbing.

## 5. Mathematical core II: exact GA miss-cost reduction via topology cells

The stronger GA rewrite is not “find a better cache key.” It is “solve each exact GA miss in a smaller exact state space.”

### 5.1 Chart-dependent topology parameters

For song `S`, define the chart constants

- `alpha_S = (N - L) * 0.333`
- `beta_S = t_{N-1} * 0.15 + 0.15`

For any candidate gem allocation:

- `q = ceil(alpha_S * FF)` is the fill count
- `D = beta_S * FT` is the fever duration

The discrete fever topology of the base scorer depends on the candidate mainly through `(q, D)`.

### 5.2 Breakpoint-cell theorem

**Theorem 2 (topology-cell partition).** The feasible `(FF, FT)` plane is partitioned into finitely many cells such that within any one cell:

1. `q = ceil(alpha_S * FF)` is constant;
2. every fever-window end index is constant;
3. therefore the fever/non-fever note membership of the base scorer is constant.

**Why the partition is finite.**
Boundaries occur only when one of two events happens:

- `alpha_S * FF` crosses an integer threshold;
- `beta_S * FT` crosses a note-gap threshold `t_j - t_i`.

Between those boundaries, the fever walk is unchanged.

### 5.3 Consequence for exact gem optimization

Within one topology cell, the timeline part of the base scorer is frozen. The exact best-gem problem therefore reduces from a generic ten-dimensional discrete search to:

1. enumerate reachable topology cells,
2. for each cell, solve a much smaller exact subproblem under fixed fever topology,
3. take the best exact result across cells.

The inner subproblem can be implemented as a small integer DP / knapsack over the remaining gem budget dimensions, because the expensive chart-timeline combinatorics have already been collapsed by the cell identity.

### 5.4 Why this is stronger than cache-centric reuse

Cache hits depend on the workload colliding in the right equivalence class. The topology-cell reduction helps **every exact GA miss** because it lowers the cost of the exact evaluation itself. That is the kind of improvement that still matters when duplicate rates are low or when the baseline already has competent reuse tables.

### 5.5 Parameterized GA speed model

Let:

- `alpha_gem` = measured fraction of `ga_gpu` time spent in the best-gem allocator today,
- `s_cell` = measured speedup of the rewritten topology-cell gem allocator against the current exact allocator.

Then the resulting `ga_gpu` speedup is

`S_GA = 1 / ((1 - alpha_gem) + alpha_gem / s_cell)`.

Illustrative scenarios:

| `alpha_gem` | `s_cell` | implied `S_GA` |
|---:|---:|---:|
| 0.60 | 2.5x | 1.56x |
| 0.70 | 3.0x | 1.88x |
| 0.75 | 4.0x | 2.29x |

This table is deliberately parameterized. The rewrite does not pretend the stronger GA win is anchored until `alpha_gem` is actually profiled in the real implementation.

## 6. Supporting bound: song-local FG envelope

The assignment explicitly encourages safe upper bounds for FG. The strongest cheap one in this rewrite is song-local and precomputable.

### Definition

For a song `S`, fill count `q`, and fever duration `D`, define `U_S(q, D)` as:

> the maximum fever bonus weight coverable on `S` by any fever schedule that obeys the timeline rules for `(q, D)`, while ignoring Great penalties.

### Safety lemma

For any candidate `g` with `(q(g), D(g), fever_mul(g))`,

`FG_gain(g) <= (fever_mul(g) - 1) * U_S(q(g), D(g))`.

This is safe because removing Great penalties can only increase the best achievable FG gain.

### Use in the pipeline

Before running the exact FG interval-DP, compute:

`final_upper_bound = base_score_exact + (fever_mul - 1) * U_S(q, D)`.

If that cannot beat the current best exact final score for the song, the exact FG solve is skipped with zero risk.

This bound is especially valuable because it is independent of raw genome identity. It stays useful even if the baseline already has strong candidate grouping.

## 7. Combined performance model

Let:

- baseline fixed-cost share = `0.299` (all non-`ga_gpu`, non-`fg_run` stages),
- `S_GA` = actual `ga_gpu` speedup from the topology-cell reduction,
- `S_FG_kernel` = actual speedup of the rewritten exact FG kernel,
- `p_prune` = fraction of FG candidates safely pruned by the song-local envelope before exact solve.

Then the effective FG stage speedup is

`S_FG_eff = S_FG_kernel / (1 - p_prune)`

and the total end-to-end speedup is

`S_total = 1 / (0.299 + 0.478 / S_GA + 0.223 / S_FG_eff)`.

Illustrative scenarios:

| Scenario | `S_GA` | `S_FG_kernel` | `p_prune` | `S_FG_eff` | total `S_total` |
|---|---:|---:|---:|---:|---:|
| FG reduction only | 1.00x | 2.4x | 0.00 | 2.40x | 1.15x |
| Conservative | 1.56x | 2.2x | 0.15 | 2.59x | 1.45x |
| Moderate | 1.88x | 2.4x | 0.25 | 3.20x | 1.61x |
| Aggressive but still measurable | 2.29x | 2.5x | 0.30 | 3.57x | 1.75x |

This presentation is intentionally assumption-sensitive. The proposal does not claim the aggressive case is already anchored; it shows what must be measured for the full integrated story to hold.

## 8. Implementation plan

### 8.1 Data structures

1. **SongTopologyCellTable**
   - per-song list of reachable `(FF, FT)` topology cells
   - stores fixed fill count, fever end indices, and any precomputed coefficients needed by the exact per-cell gem subproblem

2. **FGEnvelopeTable**
   - per-song table of `U_S(q, D)` values
   - indexed by discrete fill count and discretized exact fever-duration bucket

3. **FGPrefixCostState**
   - exact prefix order-statistic state for penalty accumulation inside the FG DP
   - supports incremental updates and retrieval of the `k`-smallest prefix penalty sum

4. **Existing `GlobalUniqueEvalTable`**
   - remains the exact-only cache for canonical genome reuse
   - kept as supporting infrastructure, not a novelty claim

### 8.2 Pseudocode

```text
for each proposed genome g:
    if GlobalUniqueEvalTable has exact result for canonical genome id:
        reuse it
        continue

    stats = derive_exact_base_stats(g)
    topology_cells = locate_reachable_cells(song, stats)

    best_base = -inf
    for cell in topology_cells:
        base = solve_exact_gem_subproblem(song, stats, cell)
        best_base = max(best_base, base)

    insert exact base result into GlobalUniqueEvalTable

    ub_final = best_base + safe_fg_envelope(song, stats)
    if ub_final <= current_best_final_for_song:
        continue

    fg_exact = exact_fg_interval_dp(song, stats, dual_bound_bank)
    update current_best_final_for_song
```

FG kernel skeleton:

```text
solve_fg(state s):
    best = 0
    init prefix_cost_state

    for activation rank m in feasible_ranks(s):
        update prefix_cost_state with next penalty
        cost = prefix_cost_state.k_smallest_sum(k_min(m))
        ub   = dual_upper_bound(prefix_cost_state, m)

        if ub <= best:
            continue

        value = bonus(s, m) - cost + solve_fg(next_state(s, m))
        best = max(best, value)

    return best
```

## 9. Correctness story

### Exactness boundary

- No approximate score is ever persisted or reported.
- The existing exact-only cache remains exact-only.
- The FG envelope and dual bound are used only for **safe pruning**.
- Any path not covered by the exact proofs falls back to the current exact evaluator.

### Why the FG solver is exact

- Prefix-separability proves that activation choice factors through `k_min(m)` and the `k`-smallest prefix penalties.
- The interval-DP enumerates the same feasible fever schedules as the current exact problem, only in a reduced representation.
- The dual expression lower-bounds the unavoidable penalty and therefore upper-bounds the attainable objective; it cannot prune an actually optimal solution.

### Why the GA miss path is exact

- The topology-cell partition does not merge cells with different fever walks.
- The rewritten per-cell gem optimizer solves the exact objective inside each cell.
- The global optimum is the maximum over all reachable cells.
- If any hidden scoring interaction is discovered that is not captured by the cell identity, that interaction is added to the cell state or the system falls back to the current exact miss path.

## 10. Evaluation and ablations

### Required benchmark mode

- fixed seeds
- fixed queue size and song list
- same FG completion contract
- identical configuration other than the rewritten kernels

### Minimum ablation grid

1. baseline
2. topology-cell GA only
3. FG interval-DP only
4. FG interval-DP + dual bound
5. song-local FG envelope pruning only
6. combined system

### Additional instrumentation

- fraction of `ga_gpu` spent in gem optimization (`alpha_gem`)
- number of topology cells visited per GA miss
- exact base-score equivalence failures (must be zero)
- exact FG equivalence failures (must be zero)
- FG candidates considered vs safely pruned
- activation checks per exact FG solve
- total GPU exact eval count (GA)
- total exact FG solve count
- integrated songs/hour with FG fully completed

## 11. Limitations and rollout order

### Phase 1: strongest deployable piece

Deploy the exact FG interval-DP first, together with the dual safe bound. This is already a crisp theorem-backed exact-work reduction and stands on its own.

### Phase 2: strongest GA proof target

Deploy the topology-cell gem optimizer only after profiling confirms that the best-gem allocator is a substantial component of `ga_gpu` and after the exactness proof is closed on a golden corpus.

### Phase 3: optional research extension

If the score truly factors through the fixed-point stat vector plus small discrete masks, a later extension can search over exact score states rather than raw genomes and use an antichain / dominance frontier. That is attractive, but it is intentionally kept out of the main claim until the factorization is verified.

## 12. Why this rewrite is better than the original proposal

The original proposal risked sounding like a broad systems win even though some of those systems elements may already exist in the real baseline. This rewrite is better because:

- it makes the **net-new** claim narrow and mathematical;
- it centers the strongest theorem-backed result (FG);
- it gives the GA side a sharper target than “better caching”;
- it expresses end-to-end speedup as a parameterized function of measured quantities instead of as an overconfident single-number anchor.

## Closing claim

The best way to make this proposal useful to a strong existing baseline is to state it plainly:

> Keep existing reuse and GPU dataflow if they already exist, but change the exact computation itself.  
> Use an exact FG order-statistic interval-DP with safe bounds, and make each GA miss cheaper by solving gem allocation in song-specific topology cells rather than as a generic black-box search.

That is the math-first rewrite that still looks multiplicative after baseline engineering is subtracted.