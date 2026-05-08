# Exact Gem-Core Solver via Skyline + Branch-and-Bound (CM/FM 2D + Analytical PP)

## Status (Research shift start: 2026-04-06 03:53:30 AM local)

This note is **gem-solver-only**: it targets the inner allocation problem currently handled by the greedy heuristic `optimize_core_jit`.

**Main result (breakthrough):** For a fixed fever timeline (i.e., fixed FT/FF) and fixed loadout stats, the PP/CM/FM/OV allocation can be solved **exactly** (global optimum) with a fast method:

1. Reduce the 3D discrete search `(PP, CM, FM)` (OV is remainder) to a **2D** enumeration over `(CM, FM)` plus an **analytical PP solve** (maximize `base_value` for each `(CM,FM)` state).
2. Keep only the **Pareto (skyline) frontier** in `(base_value, combo_mul, fever_mul)` since the exact score is monotone in all three.
3. Use a **closed-form O(1) head-score upper bound** (already derived in `tools/bench/research_gem_solve_closed_form.py`) as a branch-and-bound filter, which in practice collapses exact scoring to ~1 evaluation.

This is **provably exact** under the repo’s scoring semantics (`fast_calculate_score`), and it is production-friendly because it avoids deep local-search/greedy failures while keeping evaluation counts tiny.

---

## 1. Problem statement (inner solver)

Fix:
- A fever timeline mask (comes from choosing FT/FF), summarized by:
  - `fever_mask_head` (boolean mask over the first 100 notes)
  - `count_body_fever`, `count_body_normal`
- A loadout’s pre-gem stats:
  - stat indices: `cur_pp`, `cur_cm`, `cur_fm`
  - primary/secondary elemental values: `cur_p_val`, `cur_s_val`
  - color flags determining which gem type contributes to which element (e.g., PP→Chill, CM→Flow, FM→Rush, FT→Beat, FF→Vibe, OV→Selected).
- Remaining gem budget after FT/FF: call it $R$.

Goal:

Choose nonnegative integers
$$(p,c,f,o) \quad \text{with} \quad p + c + f + o = R$$
(respecting caps and gating) to maximize the exact score computed by:

- lookup tables `ref_pp`, `ref_cm`, `ref_fm`
- exact scorer `fast_calculate_score(base_value, combo_mul, fever_mul, ...)`

where
- `combo_mul` depends only on CM stat index,
- `fever_mul` depends only on FM stat index,
- and
  $$base\_value = (2\cdot p\_val + s\_val) + pp\_factor$$
  with `p_val/s_val` updated by gem element contributions.

The current heuristic `optimize_core_jit` is **not globally optimal**; brute-force counterexamples exist (greedy < brute).

---

## 2. Key monotonicity lemma (why skyline pruning is sound)

Let
$$S(B, C, F) := \texttt{fast\_calculate\_score}(B, C, F, \texttt{mask}, \dots)$$

with $B \ge 0$, $C \ge 1$, $F \ge 1$.

### Lemma 1 (monotone in base)
For fixed $(C,F)$ and fixed mask/counts, $S(B,C,F)$ is **nondecreasing** in $B$.

**Reason:** every term is of the form `int( alpha(B,C) * m )` with $m \in \{1,F\}$ and $\alpha$ linear in $B$ with nonnegative coefficient. Integer truncation `int(x)` is nondecreasing in $x$.

### Lemma 2 (monotone in combo and fever)
For fixed $B$ and $F$, $S(B,C,F)$ is nondecreasing in $C$.
For fixed $B$ and $C$, $S(B,C,F)$ is nondecreasing in $F$.

**Reason:** all per-note float expressions multiply by $C$ and/or $F$ with nonnegative coefficients before truncation.

### Corollary (dominance)
If state A has
$$(B_A, C_A, F_A) \succeq (B_B, C_B, F_B)$$
coordinate-wise, then
$$S(B_A, C_A, F_A) \ge S(B_B, C_B, F_B).$$

So any dominated state can be discarded without affecting the optimum.

---

## 3. 2D reduction: for fixed (CM,FM), maximize base_value analytically

Important structural fact: PP and OV gems **do not** affect `combo_mul` or `fever_mul`; they only affect `base_value`.

Fix a choice of `(c,f)` (CM gems and FM gems). Let $L := R - c - f$ be the leftover gems for `(PP, OV)` split.

Write the element-contribution weights:

- PP element weight:
  $$w_{pp} = 3\cdot(2\,\mathbf{1}[p\_color=Chill] + \mathbf{1}[s\_color=Chill])$$
- CM element weight:
  $$w_{cm} = 3\cdot(2\,\mathbf{1}[p\_color=Flow] + \mathbf{1}[s\_color=Flow])$$
- FM element weight:
  $$w_{fm} = 3\cdot(2\,\mathbf{1}[p\_color=Rush] + \mathbf{1}[s\_color=Rush])$$
- OV element weight (selected color):
  $$w_{ov} = 6\cdot(2\,\mathbf{1}[p\_color=Selected] + \mathbf{1}[s\_color=Selected])$$

Then for any split $p \in [0,L]$ and $o=L-p$:

$$\begin{aligned}
base\_value(p) &= base_0 + c\,w_{cm} + f\,w_{fm} + p\,w_{pp} + (L-p)\,w_{ov} + pp\_factor(cur\_pp + 2p) \\
&= \underbrace{base_0 + c\,w_{cm} + f\,w_{fm} + L\,w_{ov}}_{\text{constant for fixed }(c,f,L)}
+ \big(p\,(w_{pp}-w_{ov}) + pp\_factor(cur\_pp + 2p)\big)
\end{aligned}$$

So for each leftover $L$ we only need:

$$H[L] = \max_{0 \le p \le \min(L, p\_cap)} \Big(p\,(w_{pp}-w_{ov}) + pp\_factor(cur\_pp + 2p)\Big)$$

and the corresponding argmax `p*`.

**Compute $H$ once** by precomputing $F[p] := p\,(w_{pp}-w_{ov}) + pp\_factor(cur\_pp + 2p)$ and taking prefix maxima.

Then the best achievable base for a `(c,f)` pair is:

$$base\_best(c,f) = base_0 + c\,w_{cm} + f\,w_{fm} + (R-c-f)\,w_{ov} + H[R-c-f]$$

This collapses the inner search from 3D to 2D.

---

## 4. Skyline construction over (combo_idx, fever_idx, base_best)

Each `(c,f)` implies stat indices:
- `cm_stat = cur_cm + 2c`
- `fm_stat = cur_fm + 3f`

and lookup indices are clamped.

For each pair of clamped indices `(cm_idx, fm_idx)`, keep only the maximum `base_best`.

Then compute the skyline of points in the partial order:

$$(cm\_idx, fm\_idx, base) \preceq (cm\_idx', fm\_idx', base')$$
if all coordinates are `<=`.

All dominated points can be discarded by Lemma 1–2.

---

## 5. Branch-and-bound using a closed-form O(1) head upper bound

The exact score is:

- body (already O(1)):
  $$body = n_{nf}\,\lfloor BC \rfloor + n_f\,\lfloor BCF \rfloor$$
- head (first 100 notes):
  $$head = \sum_{i=0}^{H-1} \left\lfloor (B + (i+1)\,factor)\,m_i \right\rfloor$$
  where $factor = (C-1)B/100$ and $m_i \in \{1,F\}$.

Upper bound trick:

$$\sum_i \lfloor x_i \rfloor \le \left\lfloor \sum_i x_i \right\rfloor$$

So we can compute

$$head\_ub = \left\lfloor \sum_{i=0}^{H-1} (B + (i+1)\,factor)\,m_i \right\rfloor$$

in O(1) using 4 mask-dependent coefficients:
- $N_{hn}$, $N_{hf}$ = counts of head notes that are normal/fever
- $\Sigma_{hn}$, $\Sigma_{hf}$ = sums of $(i+1)$ over those sets

Then:

$$head\_ub = \left\lfloor B\,(N_{hn} + F N_{hf}) + factor\,(\Sigma_{hn} + F \Sigma_{hf}) \right\rfloor$$

And:

$$score\_ub = body + head\_ub$$

This is exactly the “semi-exact” score used in `tools/bench/research_gem_solve_closed_form.py`, but here it is used as a **guaranteed upper bound**.

Algorithm:
- Compute `score_ub` for each skyline point.
- Process points in decreasing `score_ub`.
- Maintain `best_exact` from exact evaluation.
- Skip any point with `score_ub <= best_exact`.

This is exact and typically collapses exact evaluations to ~1.

---

## 6. Empirical validation (randomized)

All tests below used:
- exact scorer: `fast_calculate_score`
- exact brute force enumeration over `(p,c,f)` with OV remainder
- the same overshoot caps as the repo (see note below)
- a synthetic timeline (`N=600`, timestamps every `0.1s`, `ft_idx=80`, `ff_idx=80`) for `fever_mask_head`

### 6.1 Correctness vs brute force
Across multiple randomized trials (varying colors, selected color, starting stat indices, and element values), the skyline method matched brute force exactly in every sampled case.

### 6.2 Skyline sizes (without UB pruning)
Example skyline sizes (40 trials each):

- Budget 20: median 12, mean 43.9, max 231
- Budget 30: median 30, mean 97.25, max 496
- Budget 40: median 15, mean 91.95, max 575
- Budget 60: median 1,  mean 105.63, max 1045
- Budget 90: median 1,  mean 31.53, max 805

(Exact numbers depend on the random distribution of flags/stats; worst-cases in random sampling were still well below the full 2D grid.)

### 6.3 Exact eval count with UB pruning (key throughput metric)
With the closed-form upper bound and processing points in decreasing `score_ub`, the number of **exact** `fast_calculate_score` evaluations was extremely small:

(80 trials each)

- Budget 20: median exact evals 1 (max 1)
- Budget 30: median exact evals 1 (max 1)
- Budget 40: median exact evals 1 (max 2)
- Budget 60: median exact evals 1 (max 1)
- Budget 90: median exact evals 1 (max 1)

This strongly suggests the UB is tight enough to make exact scoring practically constant-time per FT/FF cell.

### 6.4 Repo benchmark (real song data, verifiable artifact)

The repo now contains a reproducible benchmark harness that exercises this method against the existing greedy inner solver on real songs:

- Tool: `tools/bench/research_gem_solve_closed_form.py`
- Flags added:
  - `--exact-skyline` (enable exact skyline solver)
  - `--skyline-bnb` (enable UB-based branch-and-bound pruning)
  - `--ft-max-gems/--ff-max-gems` (control FT/FF sampling range)
  - `--bruteforce-max-budget` (verify exactness vs brute force for small remaining budgets)
  - `--json-out` (write results as an artifact)

Example command (used for the results below):

```bash
python tools/bench/research_gem_solve_closed_form.py \
  --difficulty Hard --songs 1 --configs 10 --ft-ff-samples 20 --seed 1 \
  --exact-skyline --skyline-bnb \
  --ft-max-gems 45 --ff-max-gems 45 \
  --bruteforce-max-budget 30 \
  --json-out artifacts/bench_exact_gem_skyline_bnb_sample.json
```

Observed output summary for song `#include signal.h (Hard) by Kurokotei.txt`:

- Total cases: 190
- Greedy suboptimality (exact skyline beats greedy): 43/190 (22.6%)
  - Mean uplift when it wins: +56,283 (+0.2782%)
  - Median uplift when it wins: +33,549 (+0.1416%)
  - Max uplift: +298,954 (+1.6962%)
- Reduction / throughput-relevant metric:
  - Mean skyline points: ~904
  - Mean exact `fast_calculate_score` evals with BnB: 1.0 (p95 1, max 2)
- Exactness check: skyline result matched brute force in 60/60 cases where `budget <= 30` (no mismatches)

The full per-case details are captured in the JSON artifact written by the command above.

---

## 7. Implementation notes (if/when this becomes code)

- **Caps / overshoot behavior:** `optimize_core_jit` checks `< MAX_STAT_INDEX` *before* incrementing, which allows one “overshoot gem”. The correct cap is:

  $$cap = \left\lceil \frac{MAX - cur}{step} \right\rceil$$

  not `floor((MAX-cur)/step)`.

- **Reconstructing an allocation:** store `(c,f,L)` per point plus the argmax `p*` from `H[L]` so you can return exact `(pp,cm,fm,ov)`.

- **Precompute by remaining budget:** For a fixed loadout (fixed `cur_pp/cur_cm/cur_fm` and flags), skyline points can be precomputed for each `R ∈ [0,90]` once, then reused across the FT/FF enumeration. FT/FF only shifts `base_0` by a constant and changes mask coefficients.

- **GPU friendliness:** Each point’s UB and exact score evaluation are independent; the UB pass is embarrassingly parallel.

---

## 8. What this fixes

- Removes the greedy/local-search failure mode: the inner solver becomes **provably globally optimal** for PP/CM/FM/OV allocation.
- Likely improves throughput: greedy evaluates ~`4*R` exact head loops per timeline; UB-pruned skyline needs ~`1` exact head loop in practice.

---

## Appendix: Pseudocode

```
precompute H[L] for L=0..R
for c in feasible CM gems:
  for f in feasible FM gems with c+f<=R:
    L = R-c-f
    base_best = base0 + c*w_cm + f*w_fm + L*w_ov + H[L]
    (cm_idx,fm_idx) = (clamp(cur_cm+2c), clamp(cur_fm+3f))
    best_base[cm_idx,fm_idx] = max(best_base[cm_idx,fm_idx], base_best)

skyline = pareto_frontier(best_base)

for each point in skyline:
  ub = score_upper_bound_closed_form(base_best, cm_idx, fm_idx, mask_coeffs)

sort skyline by ub desc
best_exact = -inf
for point in skyline:
  if ub <= best_exact: continue
  exact = fast_calculate_score(...)
  best_exact = max(best_exact, exact)
return best_exact (+ arg state)
```

---

## Related: removing GA (outer search)

This note only covers the *inner* gem-core allocation. For evidence and a proof-of-feasibility that the *outer* loadout search can be reduced exactly to an enumerable Pareto skyline (supporting a no-GA optimizer), see:

- [Research/EXACT_OUTER_SKYLINE_NO_GA.md](Research/EXACT_OUTER_SKYLINE_NO_GA.md)
