# Skyline Exact Speedup Plan — FINALIZED

Status: finalized 2026-06-13. Companions: memory `skyline-vs-ga-parity-infeasible`,
`skyline-fg-fold-exactness-gap`; independent review corrections are folded in below.

## 1. Objective (finalized)

Build a **completely exact, self-contained, exact-BY-CONSTRUCTION** single-song optimizer that can
replace GA:
- **Completely exact** = true global `max(base, FG)`, bit-exact — including the `(P,S)`-Pareto FG fix
  (today's engine folds `(P,S)→2P+S`, a real but ≤25 pt / ~0.001% FG error; "completely exact" closes it).
- **By construction** = the algorithm converges to the proven optimum in a SINGLE search and returns the
  right loadout directly. NO separate pick-then-verify / certification pass. Exactness is structural.
  ("Allowed to be wrong" is confined to SPEED-only guidance — the incumbent and visit order; the pruning
  rule must be an admissible bound or lossless dominance, so there is nothing to verify.)
- **Self-contained** = pure function of cold static inputs (gear pool, mini pool, chart, config). No GA
  results, no DB, no persisted candidate set. A cold ordering rule computed at solve time (incumbent/order) is fine.
- **Speed bar = a corpus throughput SLO you set, NOT "GA-speed per song."** Judge against GA's
  cost-to-a-CORRECT-answer (its restarts + its wrongness on breakpoint songs), not its best-case raw speed.
  Whether it reaches near-GA is **measured, not promised** (§3).

## 2. The math, stated precisely

Runtime `≈ N_evaluated × cost_per_candidate`. These are two independent levers; do not conflate them.

- **The exact frontier is `(PP,CM,FM,P,S)`-Pareto per `(FT,FF)` cell.** Within a fixed cell the timing is
  frozen and `max(base,FG)` is **monotone non-decreasing in every stat `(PP,CM,FM,P,S)`** (raising any one
  raises every note's value for any forcing pattern ⇒ raises base and the FG optimum). So the lossless
  candidate set is that 5-D Pareto frontier. MEASURED: ~17.5M candidates / Easy song (~1,900/cell ×
  ~15,000 cells), ~440× GA's ~40k. Generation is ~10–15s (NOT the bottleneck); evaluating the ~17.5M is.
- **Lossless DOMINANCE is exhausted** — and FG-exactness makes it *slightly larger* (the `(P,S)`-Pareto is
  ⊇ today's `2P+S`-folded set). A "DP over a richer state" can't escape: that 5-D Pareto **is** the state.
- **`N_evaluated` is NOT bounded below by the frontier size.** Exact branch-and-bound (admissible upper
  bound + incumbent) can evaluate far fewer while staying exact-by-construction. The earlier "irreducible"
  applied ONLY to dominance, not to bounding. Whether B&B actually prunes the bulk is unknown until §3.
- **`cost_per_candidate` is shared with GA** (same inner kernel), so engineering lowers absolute time but
  does NOT close the ~440× ratio. Only `N_evaluated` (B&B) can close the ratio.
- **base vs FG — two exact targets, very different cost.** The product keeps `songs.best_score` (base) and
  `songs.best_fg_score` (FG) separate, and they may be different loadouts. `best_score` (base) is ~FREE — the
  max-base point falls out of frontier generation with no ForceGreats DP, and is already exact today (the
  `2P+S` fold is fine for base). `best_fg_score` (FG) IS the cost problem: evaluating the ForceGreats DP over
  the ~17.5M frontier is the slow part. So everything below (M1's bound/incumbent, Track A's Direction-1
  fusion, Track B's pruning, the §6 `(P,S)` fix) targets the **FG** calculation specifically. The same
  `(PP,CM,FM,P,S)`-Pareto frontier is lossless for BOTH, so no separate frontier is built.

## 3. Gate measurements — DO FIRST (cheap, decisive, parallel)

**M1 — oracle prune-rate (the "is fast-exact even possible" gate).**
Use the TRUE best score as the incumbent, apply the proposed cheap *admissible* FG upper bound per
candidate AND per `(FT,FF)` cell, and measure the **maximum possible** bulk-prune %. Then repeat with a
realistic cold incumbent (base-max FG-floor). The relevant test is `UB(candidate) ≤ incumbent`, not
"UB close to exact." Because the frontier is a Pareto trade-off curve, its scores span a wide range, so
bulk pruning is plausible.
- **Decision:** oracle prune ≳95–99% ⇒ Track B is alive (near-GA exact-by-construction is real).
  Oracle prune poor ⇒ **B&B is dead, no ordering saves it** ⇒ the honest ceiling is Track A (~5–10×).
- Tool: extend `tools/bench/measure_skyline_candidate_work.py`.

**M2 — GA-vs-exact error distribution (the "is exact-everywhere worth it" gate).**
How often is GA wrong, by how much, on which song classes (esp. Easy breakpoint songs), and at what
restart cost. Decides **exact-everywhere vs exact-where-it-matters** (the product question). Needs a
GA run + the exact solve on a sample per difficulty.

## 4. Track A — `cost_per_candidate` (UNCONDITIONAL; exact; ~5–10×; do regardless of M1)

- **A1. Direction-1 eval fusion (~5×).** Fold the FT/FF gem-allocation loop into the FG response-frontier
  DP. Files: `taichi_gem/api/skyline_operations.py`, `skyline_eval/warmstart.py`, `force_greats/response_frontier.py`.
- **A2. Cell-major fusion / locality.** Group work by `(ft_idx,ff_idx)` so each cell's timeline grid +
  frontier variants load once; fixes the warmstart per-lane load imbalance.
- **A3. SoA layout / memory traffic.** Pack `genome_base_stats`/frontier variants; cut `grid_frontier_count` re-reads.
- **A4. Mixed-precision search + f64 final.** Search in f32 (fast), re-score the winner + anything within the
  f32 margin in f64. Resolves the Direction-1 f32/f64 obligation as the *final* step (still exact, no separate verify pass).

## 5. Track B — `N_evaluated` (ONLY if M1 favorable; exact BY CONSTRUCTION; closes the ratio)

- **B1. Cell-level FG envelopes (best line, flagged by the external review).** Tight admissible upper bound on
  the best FG achievable in an entire `(FT,FF)` cell; if ceiling ≤ incumbent, skip ALL ~1,900 of its points
  with one check. ~15,000 cell-checks can retire most of the 17.5M in bulk.
- **B2. Per-candidate admissible bound.** Cheap FG ceiling from `(PP,CM,FM,P,S)` + cell timing; prune candidates
  whose UB ≤ incumbent before they enter the inner solve (their reads never happen). Admissible ⇒ no verify pass.
- **B3. Best-first ordering.** Visit by descending UB so the incumbent rises fast and the tail prunes harder
  (ordering may be imperfect → speed-only).
- **C1. Cold incumbent.** Free from the base-max loadout (FG ≥ base); optionally a millisecond cold greedy +
  hill-climb. Self-contained (NOT GA, NOT the DB). Stronger incumbent ⇒ more pruning.
- **C2. Lazy/streaming generation.** Generate cell-by-cell and prune against the incumbent during generation;
  never materialize 17.5M (also fixes the census OOM).
- **C3. Tighter admissible bound.** The known bound is within ~0.01% of exact; a tighter per-cell ceiling
  directly raises every prune rate above (proof obligation; gates how well B1/B2 work).

## 6. Correctness — the `(P,S)`-Pareto FG-exact fix (required for "completely exact")

Carry `(P,S)` (not the `2P+S` fold) through gear DP → gear skyline → combined skyline and keep the
`(PP,CM,FM,P,S)`-Pareto per cell. Fold it into whichever generation path wins (Track A/B). Slightly widens
the frontier. Already bounded + tested (`tests/test_skyline_fg_fold_bound.py`); promote from "documented
bound" to "closed" here. Bit-exact A/B vs a brute-force reference on a small pool.

## 7. Finalized sequence

1. **M1 + M2** (§3) — parallel, cheap, decisive. They gate everything below.
2. **A1 (Direction-1)** — the guaranteed ~5×; exact; worth it no matter what M1 says.
3. **Branch on M1:**
   - Favorable → build **Track B** (B1 cell envelopes → B2/B3/C1/C2) → near-GA exact-by-construction.
   - Poor → accept the **Track A ceiling (~5–10×)**, set the corpus SLO, and use **M2** to decide
     exact-everywhere vs exact-where-it-matters.
4. **(P,S)-Pareto fix** (§6) folded into the winning generation path.
5. A2/A3 locality/layout as ongoing constant-factor wins.

Every step gated by a single-GPU A/B with **bit-exact `best_score`/`best_fg_score` parity** vs the current
enumerate-all path. "Allowed to be wrong" applies only to the internal incumbent/ordering; the gate is exactness.

## 8. What we are NOT promising

Exact at GA speed on all songs — that is a moonshot with bad odds (per the measurements + the independent
review). We promise: **completely exact, self-contained, exact-by-construction, as fast as the method
allows, with a measured throughput SLO and a measured fallback** (exact-where-it-matters if M1 is poor and
M2 says GA is only badly wrong on breakpoint songs).
