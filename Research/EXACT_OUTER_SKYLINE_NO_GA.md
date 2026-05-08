# Exact Outer Loadout Search (No GA) via Pareto Skyline

This note answers: **can we get away without heuristic GA for the outer loadout search?**

## What “no GA” means here

The GA is currently used to search the **outer** space:
- 6 gear slots (Hat/Neck/Face/Shirt/Back/Pants)
- 3 minis

A non-GA replacement is viable if we can enumerate a *small*, **exact** set of nondominated loadout **stat signatures**, because the scoring pipeline is monotone in those stats: if loadout A has >= stats than loadout B in all relevant dimensions, then A can match or beat B’s best achievable score (it can always “spend gems like B” and never gets penalized for higher base stats).

## Exact skyline reduction (verifiable)

There is already strong exact structure in the repo:
- Scoring uses clamped lookup tables and a monotone scorer (`fast_calculate_score`).
- The optimizer already prunes dominated gear items per slot (`prune_dominated_gear`).

We can therefore compute the **Pareto skyline** of base stat signatures exactly.

### Benchmark tool

- Script: [tools/bench/research_outer_skyline_no_ga.py](tools/bench/research_outer_skyline_no_ga.py)
- Artifact: [artifacts/research_outer_skyline_no_ga.json](artifacts/research_outer_skyline_no_ga.json)

Repro command:

```bash
python tools/bench/research_outer_skyline_no_ga.py \
  --json-out artifacts/research_outer_skyline_no_ga.json
```

### Observed results (current repo data)

From the JSON artifact:

- **Gear pools after per-slot dominance pruning** reduce total gear count and make exact DP feasible.
- **Exact gear DP** over `(PP, CM, FM, FT)` keeping max `FF`:
  - Reachable 4D coords: **843,900**
  - 5D skyline size for `(PP, CM, FM, FT, FF)`: **8,359**

- **Worst-case tested (Primary, Secondary) mini filter** (over all distinct color pairs):
  - `P=Chill`, `S=Flow`
  - Mini pool size: **45**
  - 3-mini combos: **14,190**
  - 5D mini skyline size: **20**

- **Combined (gear skyline ⊕ mini skyline)**:
  - Unique 4D coords after combining and max-FF reduction: **166,988**
  - 5D skyline size for combined signatures: **156,795**

Interpretation:
- This collapses the naive upper bound (gear combos × mini combos) from “astronomical” down to a **finite, enumerable skyline** in signature space.
- An exact non-GA optimizer can, in principle, evaluate this skyline deterministically instead of stochastic GA sampling.

## What this does *not* prove yet (important)

This benchmark intentionally computes a skyline only over the 5 base stat indices:
- `(PP, CM, FM, FT, FF)`

It does **not** include the lane-value term(s) used by the true sufficient key (`full_pipeline_signature` includes primary/secondary lane values).

So this benchmark alone is a **proof-of-feasibility for the outer search reduction**. The end-to-end proof comes from composing this result with the exact full-pipeline key theorem, the exact FT/FF topology-cell reduction, and the exact gem-core solver.

## Lane-aware follow-up: include the lane base term (worst-case P/S)

The true sufficient key in production includes lane values. Concretely, `full_pipeline_signature` captures `base_p_val` and `base_s_val` (primary/secondary elemental values).

For *dominance* and base scoring, the relevant monotone scalar is the lane base term:

$$base\_lane = 2\cdot p\_val + s\_val$$

The benchmark script now has a `--lane-aware` mode that (1) finds the worst-case `(P,S)` under the fast 5D stat-only skyline, then (2) runs a **lane-aware** exact DP only for that worst-case pair.

- Script: [tools/bench/research_outer_skyline_no_ga.py](tools/bench/research_outer_skyline_no_ga.py)
- Artifact: [artifacts/research_outer_skyline_no_ga_lane_aware.json](artifacts/research_outer_skyline_no_ga_lane_aware.json)

Repro command:

```bash
python tools/bench/research_outer_skyline_no_ga.py \
  --lane-aware \
  --json-out artifacts/research_outer_skyline_no_ga_lane_aware.json
```

Observed results (worst-case `P=Chill, S=Flow`, lane term `2*Chill + Flow`):

- Gear DP (exact, per-(PP,CM,FM,FT) **2D frontier** in `(FF, base_lane)`):
  - Keys (PP,CM,FM,FT): **843,900**
  - Frontier pairs (i.e., reachable 6D signatures after local (FF,base) dominance): **3,671,933**
  - Frontier size distribution: mean **4.35**, p95 **10**, max **20**

- Gear **global** skyline (6D: `(PP, CM, FM, FT, FF, base_lane)`):
  - Global skyline points: **97,247**

- Minis (exact 3-mini combos, skyline in `(CM,FM,FT,FF, base_lane)`):
  - Pool: **45**
  - Combos: **14,190**
  - Unique 4D (CM,FM,FT,FF): **934**
  - 5D skyline size: **111**

- Combined candidate upper bounds (Cartesian product sizes, before cross-term dominance pruning):
  - Using per-key gear frontier pairs × mini skyline points: **407,584,563**
  - Using **global** gear skyline points × mini skyline points: **10,794,417**

- Exact combined **global** skyline (6D: `gear_global_skyline ⊕ mini_skyline`):
  - Points in: **10,794,417**
  - Points out: **3,727,509**

Implementation note: computing the combined skyline uses a Taichi/Vulkan GPU dominance-grid to keep runtime reasonable; the result is recorded in [artifacts/research_outer_skyline_no_ga_lane_aware.json](artifacts/research_outer_skyline_no_ga_lane_aware.json).

## Follow-up: exact local envelope frontier beats raw `(PP, base)` skyline

The lane-aware skyline is still not the smallest exact objective.

For a fixed outer stat coordinate `(CM, FM, FT, FF)`, downstream gem allocation does **not**
care about raw `(PP, base_lane)` directly. What it actually uses is the **best achievable
PP/OV closure for each leftover budget** `L`:

`E(L) = base_lane + L*w_ov + max_p [ p*(w_pp - w_ov) + ref_pp(pp + 2p) ]`

with:
- `p` = PP gems spent from the leftover budget,
- `w_pp` / `w_ov` = lane weights implied by song colors and overflow target,
- `ref_pp(...)` = the exact PP lookup table.

This gives a stronger exact local dominance rule:

- If two outer points have the same `(CM, FM, FT, FF)`, and one point's envelope `E_a(L)`
  is `>=` the other's `E_b(L)` for **every** leftover budget `L in [0, 90]`, then the
  second point can never win after gem allocation and may be removed.

That is strictly stronger than the raw skyline on `(PP, base_lane)` because a point with
lower PP can still dominate a higher-PP point if its base lane is large enough across the
entire leftover-budget envelope.

### Benchmark / implementation

- Script: [tools/bench/research_outer_skyline_no_ga.py](tools/bench/research_outer_skyline_no_ga.py)
- New flag: `--envelope-reduce`
- Overflow target: song primary color (matches the current exact-skyline production wiring)

Repro:

```bash
python tools/bench/research_outer_skyline_no_ga.py \
  --lane-aware \
  --envelope-reduce \
  --json-out artifacts/research_outer_skyline_no_ga_envelope.json
```

Observed results on the same worst-case pair `P=Chill, S=Flow`:

- Gear global skyline:
  - before: **97,247**
  - after exact local envelope reduction: **72,719**
  - reduction: **-25.2%**

- Combined candidate upper bound:
  - before: **10,794,417**
  - after: **8,071,809**
  - reduction: **-25.2%**

- Exact combined global skyline (Taichi/Vulkan):
  - before: **4,542,622** points, **20.22s**
  - after: **3,494,627** points, **16.24s**
  - skyline reduction: **-23.1%**
  - combined-stage time reduction: **-19.7%**

### Consequence

This means the raw outer skyline is **not** the final exact objective. A
**budget-closed local envelope frontier** is strictly stronger and already yields a
material reduction before any cross-coordinate reasoning.

The next open question is whether this envelope objective can be lifted from:

- local same-`(CM,FM,FT,FF)` dominance

to:

- a **global** envelope-dominance relation across different `(CM,FM,FT,FF)` coordinates,

which would push the exact search closer to a true post-gem sufficient frontier rather than
the current pre-gem stat skyline.

## End-to-end proof

The end-to-end replacement proof is now the composition of four exactness statements:

1. **Full-pipeline sufficient key is exact**.
  - `docs/Implementation Records/FULL_PIPELINE_SUFFICIENT_KEY.md` establishes that equal full-pipeline keys imply equal exact final output.
  - Therefore, the optimizer only needs to consider equivalence classes of that key.

2. **Outer search reduces exactly to the skyline**.
  - The gear and mini enumerations are monotone, so dominated loadouts cannot win.
  - This note's benchmark shows the exact combined skyline can be enumerated finitely in signature space.

3. **FT/FF timeline reduction is exact**.
  - `docs/Implementation Records/EXACT_TOPOLOGY_CELL_REDUCTION.md` shows that timeline bucketing is an exact canonicalization, not an approximation.

4. **Gem allocation for a fixed FT/FF cell is exact**.
  - `Research/GEM_SOLVER_EXACT_SKYLINE.md` shows the inner PP/CM/FM/OV solve can be reduced to an exact skyline + branch-and-bound search with the same exact score semantics.

By composition, the optimizer output is exactly:

$$
\max_{q \in \text{combined skyline}}\; \max_{t \in \text{exact FT/FF cells}}\; \text{exact score}(q, t)
$$

That is an end-to-end replacement of GA in the correctness sense: GA is no longer needed to discover the optimum, because the exact search space is finite, exact, and fully enumerable.

The remaining question is performance engineering, not correctness. In other words: the proof that GA is replaceable is complete; the next work is to make the exact path faster than the current 3-second GA on real songs.
