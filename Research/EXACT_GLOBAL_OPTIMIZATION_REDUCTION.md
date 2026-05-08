# Mathematical Reduction for Exact Global Optimization (GA to DP)

## Status (Audit 2026-04-06)

This document’s central claim — that the exact score factorizes as
$$\text{Score} = X \cdot Y \cdot \big(W_{normal}(FT,FF) + Z \cdot W_{fever}(FT,FF)\big)$$
with $W_{normal}, W_{fever}$ depending **only** on $(FT,FF)$ — is **false under the repo’s exact scoring semantics**.

What is verified true:

- The **base fever timeline / fever mask** (for fixed timestamps) depends only on the two multipliers derived from **Fever Time** and **Fever Fill Rate** (plus the song timestamps / HitSim-adjusted timestamps). This is already exploited by `SongTimelineGrid` and `precompute_fever_timelines(...)`.

What is not true (and why):

- The score does **not** separate multiplicatively into “timeline-only weights” and “loadout-only multipliers” because:
	- The **head combo ramp is affine** in `combo_mul` (it contains a constant `1.0` term), so you cannot pull out a global `combo_mul` factor.
	- The implementation applies **per-note integer truncation** (`int(...)` / `floor(...)`) and truncation does not distribute over sums/products.
- Force Greats (FG) is not a function of $(FT,FF)$ alone: the *optimal* forced-Great counts depend on the Great penalty surface, which depends on `base_value` and `combo_mul` (and the fever benefit depends on `fever_mul`).

### Concrete counterexample (exact repo math)

Using `gear_optimizer.solver.scoring_core.fast_calculate_score` with a **single head note** (no body notes), fixed `base_value=1000.7`, and varying `combo_mul`:

```
combo=1.0 -> score=1000
combo=2.0 -> score=1010
combo=3.0 -> score=1020
combo=4.0 -> score=1030
```

If the bilinear factorization were correct with a timeline-only weight, the score would be proportional to `combo_mul` for fixed $X,Z,W$, which is visibly not the case.

### Concrete counterexample: FG depends on non-(FT,FF) stats

Using the repo’s exact DP reference implementation `gear_optimizer.solver.fg_exact_dp.solve_force_greats_exact_dp` on a synthetic chart with a large timestamp gap (so delaying activation by 1 note jumps the gap):

- With `fever_mul = 1.0`, the exact best FG configuration is all zeros.
- With `fever_mul = 2.0` (all else equal, including the same FT/FF), the exact best FG configuration forces 1 Great in section 1.

Therefore the *optimal* FG choice is not determined by $(FT,FF)$ alone.

## 1. Objective and Breakthrough Summary

**Objective:** Design a major multiplicative throughput improvement for the GPU-resident optimizer that finds the **global best** base score and Force-Greats (FG) score for any song, replacing the current heuristic Genetic Algorithm (GA) approach with an exact mathematical formulation suitable for production throughput.

**Important correction:** The originally proposed bilinear “timeline weight × multiplier volume” factorization does **not** hold for the repo’s exact math. The remaining sections below are kept as historical context, but they should be treated as a retracted idea rather than a correct or deployable reduction.

---

## 2. Problem Formalization and Algebraic Reduction

A loadout consists of 9 slots (4 gears, 5 minis) plus a budget of 90 gems. Each valid combination projects into a 10-dimensional stat vector: `[PP, CM, FM, FT, FF, Chill, Flow, Rush, Beat, Vibe]`.

### 2.1 The Timeline Decoupling Theorem
The core mechanical invariant of the scoring engine is that the fever timeline (when fevers start, end, and the note indices that fall within the fever windows) is strictly entirely determined by:
1. `Fever Time` (FT)
2. `Fever Fill Rate` (FF)

Let $T(FT, FF)$ represent this exact fever timeline.

Verified in code: `calculate_fever_timeline_indices(...)` computes the fever mask using only:
`(timestamps, total_notes, long_notes_count, last_note_time, ff_factor, ft_factor)`.

FG note: for a *fixed* forced-count configuration, the induced FG timeline is also determined by `(FT, FF)` plus that configuration (and, in timing-aware mode, the great-candidate timestamps). But the *optimal* FG configuration depends on scoring tradeoffs (penalties vs fever gains), so it is not determined by `(FT, FF)` alone.

### 2.2 Factorization of the Score Function
For a fixed timeline $T$, every note index $i$ is partitioned into Normal notes $N_T$ and Fever notes $F_T$. The score of the song is computed as:
$Score = \sum_{i \in N_T} V_{perfect}(i) + \sum_{j \in F_T} V_{fever}(j)$

Based on the game's multiplier formulas:
- Base Point Volume $X$: $X = 2 \times PrimaryElement + SecondaryElement + PP$
- Combo Multiplier Volume $Y$: $Y = CM$
- Fever Multiplier Volume $Z$: $Z = FM$

We extract the index-dependent combo ramp ramp(i) into fixed aggregate weights:
$W_{normal}(FT, FF) = \sum_{i \in N_T} \text{ramp}(i)$
$W_{fever}(FT, FF) = \sum_{j \in F_T} \text{ramp}(j)$

**Retraction:** This factorization is not valid for the repo’s exact scoring math.

The repo’s exact score (see `fast_calculate_score`) is a sum of per-note truncated float32 expressions.

High-level structure:

- Body notes (i.e. after the head):
	$$\text{body} = n_{nf} \cdot \lfloor base\cdot combo \rfloor + n_{f} \cdot \lfloor base\cdot combo\cdot fever \rfloor$$
- Head notes (first 100):
	$$\text{head} = \sum_i \left\lfloor base \cdot \Big(1 + (combo-1)\tfrac{i+1}{100}\Big) \cdot m_i \right\rfloor$$
	where $m_i = fever$ if note $i$ is in fever else $m_i = 1$.

Because truncation happens per note, and because the head ramp includes a constant term independent of `combo`, this cannot be collapsed into “timeline-only weights” multiplied by “loadout-only multipliers”.

---

## 3. The Reduction: From GA to Precomputed Envelope Match

**Retraction:** This section depends on the invalid factorization above and should not be treated as an exact or correct reduction.

### Step 1: Offline 5D Pareto Frontier Precomputation (Once per Inventory)
The maximum statutory value for any index is 160. The space of $(FT, FF)$ pairs is $161 \times 161 = 25,921$.
For each valid $(FT, FF)$ pair, we query the gear/mini inventory (plus the 90 gem allocation) to find all possible $(X, Y, Z)$ tuples. Because $X, Y, Z$ are strictly additive/multiplicative goods, we compute the **Upper Envelope (Pareto Frontier)** of $(X, Y, Z)$ for each $(FT, FF)$ bucket.
- Result: A static lookup table mapping each of the 25,921 $(FT, FF)$ pairs to a tiny array of non-dominated $(X, Y, Z, \text{LoadoutHash})$ tuples.

### Step 2: Online Exact O(1) Song Execution (On GPU)
For a new song with $N$ notes, the GPU launches a grid of 25,921 threads (one for each $FT, FF$ pair).
In each thread:
1. **Analytical FG DP:** Compute the optimal Force-Greats timeline analytically. Since the state space is simply the note index, the DAG DP takes $O(N \times \text{breakpoints})$ operations.
2. **Weight Accumulation:** From the optimal timeline, compute $W_{normal}$ and $W_{fever}$.
3. **Envelope Maximization:** Iterate over the precomputed Pareto $(X, Y, Z)$ frontier for this Thread's $(FT, FF)$ bucket. Compute the exact score $X \cdot Y \cdot (W_{normal} + Z \cdot W_{fever})$.
4. **Atomic Max:** Output the geometric maximum score and its associated `LoadoutHash`.

---

## 4. Evaluation and KPIs

### Guaranteed Global Optimum
No “global optimum” guarantee follows from the retracted derivation.

### Multiplicative Speedup Metrics
Current Architecture (GPU Native GA):
- `Population_Size` (250) $\times$ `Generations` (e.g. 50) $\times$ `Multi_Starts` (5) = $\approx 62,500$ timeline evaluations per song.
- Followed by a combinatorial FG expansion on the top candidates.

Proposed Architecture:
- Exactly 25,921 timeline computations per song.
- Zero heuristic overhead (no crossover, no mutation, no RNG scaling).
- Complete vectorization: Each thread has entirely localized memory access (no island migration or shared state synchronization needed until the final atomic reduction).

**Throughput Expectation:** Timeline evaluations drop by roughly 3-5x nominally. However, because thread divergence is eliminated (all threads execute the exact same DP formulation), warp occupancy on the Taichi Vulkan backend reaches theoretical limits. FG is no longer "deferred" or "post-optimized"; the $O(N \times K)$ analytical DP fuses it directly into the initial evaluation pass. Estimated throughput multiplier: **10x - 40x** improvement in songs/hour, operating at the theoretical IO transfer limit of the GPU.

---

## 5. Summary of Design Freedoms Used
- **Correct verified decoupling:** fever timeline depends only on (FT, FF) multipliers + timestamps.
- **Incorrect (retracted):** bilinear separation of score into timeline-only weights and loadout-only multipliers.