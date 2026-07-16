# Design Record: Tightening the GA Combo-Cull Upper Bound

**Status:** Decision-ready. Recommends one design for implementation.
**Target:** `response_score_upper_bound_relaxed` — `gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py:197-260`
**Motivation (2026-07-15 GA_CULL_PROBE, seeded q24):** eval kernel = 72.5% of GPU device time; examines 3.98B combos; current relaxed UB culls ~39%; 61% run the full exact inner solve; a perfect incumbent changes nothing (lag 0.0%). The bound is the only lever. Halving hopeless solves ≈ 20%+ of total GPU.
**Hard contract:** for every reachable input `UB ≥ exact_combo` (an under-estimate silently corrupts `best_score` corpus-wide). The bound may only get *tighter*; determinism and tie-order must be bit-unchanged. This is a cull-only change → the seeded A/B must be **byte-identical**, never merely "close."

---

## 1. Decision

**Implement Design 1 (Lagrangian / exchange-argument bound, `min(current, UB_fm, UB_cm)` over precomputed concave hulls).** It is the only design that is both **sound** (survived 171,200 adversarial trials with 0 violations, and its soundness rests on LUT monotonicity verified against real `Data/Gear/Stats.txt`) and **profitable** (point estimate ~10% total-GPU reduction; break-even at converting only 0.14% of survivors).

The other three do not survive as their authors wrote them:
- **Design 2** (in-kernel scan `Q* = fl(B̂·F̂)`) is **BROKEN** — a concrete reachable counterexample under-estimates by 976 points.
- **Design 3** (precomputed `M̂ = CF_env`) is **BROKEN-as-written** by the *same* f32 reassociation bug, but its *idea* is salvageable with an association fix and is worth grafting as a follow-on. Payoff is MARGINAL and gated on an unmeasured saturation histogram.
- **Design 4** (delta / FT-row hierarchy) is **SOUND but UNPROFITABLE** — it provably culls a strict subset of what the per-combo bound already culls (zero exact-solve reduction).

---

## 2. Ranking (soundness first, payoff second)

| Rank | Design | Soundness | Payoff | Disposition |
|---|---|---|---|---|
| **1** | **Lagrangian exchange** — `min(current, UB_fm, UB_cm)`, concave hulls of refcm/reffm, couples base-lane ↔ CM & FM | **SOUND** (171k trials, 0 viol.; monotonicity verified on real data) | **PROFITABLE** ~10% GPU; break-even 0.14% | **IMPLEMENT** |
| 2 | **Monotone-table** — precomputed constrained envelope `M̂ = max_{i+j≤k} refcm[·]·reffm[·]`, genome-invariant | **BROKEN as written** (f32 body reassociation); **FIXABLE** by carrying split multipliers | **MARGINAL** (net −3% to +14%, rides on saturation histogram) | **GRAFT idea only** (see §7), not the scalar-`M̂` mechanism |
| 3 | **Delta / FT-row hierarchy** — Facet A `row_ub(ft)`, Facet B neighbor-anchored `exact(c')+Δ` | Facet A **SOUND**; Facet B **UNPROVEN** | **UNPROFITABLE** (0 additional culls, both facets) | **REJECT** |
| 4 | **Pairwise-joint scan** — `Q* = max_j B̂(j)·F̂(j)`, `body = ⌊Q*·C*⌋` | **BROKEN** (reachable counterexample, deficit 976) | (would be profitable if sound) | **REJECT** |

---

## 3. Recommended design — full math

### 3.1 Constants / notation (identical to shipped bound)

| Symbol | Value / definition |
|---|---|
| `GEM_SCALE_NORMAL / FEVER` | 2 / 3 |
| `MAX_STAT` | 160 (LUT clamp ceiling) |
| `UB_EPS` | 1024.0 (retained unchanged) |
| `w_pp, w_cm, w_fm, w_ov` | per-gem base-lane element weights (`kernels_scoring.py:222-234`) |
| `w_max` | `max(w_pp, w_cm, w_fm, w_ov)` |
| `refpp/refcm/reffm[·]` | monotone non-decreasing LUTs, clamped `[0,160]` (`kernels_helpers.py:211-250`) |

Verified against real `Data/Gear/Stats.txt` (161 rows): `refcm ∈ [2.00, 2.67]`, `reffm ∈ [3.00, 5.425]`, `refpp ∈ [200, 485]`, **all non-decreasing with argmax = 160** (0 decreases). This endpoint-is-max fact is load-bearing (see §4).

### 3.2 Reused current-bound quantities (so the new bound is provably ≤ current)

```
B0     = (2·cur_p_val + cur_s_val) + budget·w_max + refpp[clamp(cur_pp + 2·budget)]   # current base_value, :242
C*     = refcm[clamp(cur_cm + 2·budget)]        # current combo mult, :243  (≥ any reachable C_a, ≤ refcm[160])
F*     = reffm[clamp(cur_fm + 3·budget)]        # current fever mult, :244  (≥ any reachable F_a, ≤ reffm[160])
Δc     = w_max − w_cm ≥ 0                        # base-lane opportunity cost of a CM gem
Δf     = w_max − w_fm ≥ 0                        # base-lane opportunity cost of an FM gem
N      = max(0, body_total)                      # :248
L      = clamp(head_len, 0, 100)                 # :246
Σ      = L·(L+1)/2                                # :247
k_cm   = min(max_cm_gems, budget)                # gems to saturate CM, capped (:400-419)
k_fm   = min(max_fm_gems, budget)
a2     = N + Σ/100   (≥ 0)
a1     = L − Σ/100   (> 0 for all L ≤ 100, since a1 = L·(199−L)/200)
```

### 3.3 Folded closed form (algebraically identical to `:189-194`, body/head floors dropped upward)

```
Ψ(B, C, F) ≤ B·F·(C·a2 + a1) + UB_EPS
```
Derivation: `body = N·⌊B·C·F⌋`, `head = F·B·L + factor·F·Σ` with `factor = (C−1)·B/100`; drop the body floor upward, factor out `B·F`, collect `C`.

### 3.4 The two one-axis-coupled sub-bounds

`Ĉ_cm(·)`, `Ĉ_fm(·)` = **upper concave hulls of the integer LUTs** `refcm`, `reffm` over `[0,160]` (piecewise-linear, ≤4 segments each, `≥` every LUT entry by construction; precomputed once per run — the LUTs are fixed game constants, **genome-invariant**).

```
UB_fm = UB_EPS + max_{f ∈ [0, k_fm]}  (B0 − f·Δf) · Ĉ_fm(f) · (C*·a2 + a1)     # couples FM ↔ base; C pinned at C*
UB_cm = UB_EPS + max_{c ∈ [0, k_cm]}  (B0 − c·Δc) · F* · (Ĉ_cm(c)·a2 + a1)      # couples CM ↔ base; F pinned at F*
```
Each maximand is a **concave quadratic** on each hull segment (leading coeff ≤ 0), solved in closed form by clamping the analytic vertex to `[seg_lo, seg_hi] ∩ [0, k]` and evaluating — O(1) per segment, ≤4 segments.

> **Graft applied (from the payoff review):** the design's original text pinned `C_max = refcm[160]` / `F_max = reffm[160]`. Using the current-corner `C*` / `F*` instead is uniformly `≤` and still a valid upper bound on every reachable factor (`g_cm, g_fm ≤ budget`, monotone LUT), so it improves `min()` on strictly more combos at zero cost. Re-verify with `C*`/`F*` in the on-device sweep (§6).

### 3.5 Final gate bound

```
UB_gate = min( response_score_upper_bound_relaxed(...) ,  UB_fm ,  UB_cm )
```
Since each `(B0 − ·Δ) ≤ B0`, each hull `≤` the pinned factor's ceiling, and `min` picks the smallest sound value, `UB_gate ≤ current` always — strictly tighter whenever `Δc > 0` or `Δf > 0` and the caps cost real budget. Zero change on genomes where the best element weight already sits on CM or FM (`Δ = 0`), which is correct.

---

## 4. Soundness proof obligations

Fix any feasible allocation `a` (`g_pp + g_cm + g_fm + g_ov = budget`, caps at `kernels_scoring.py:414-419`) and any frontier variant `v`. Required lemmas (all verified by the soundness attacker over 171,200 trials, 0 violations):

1. **Base-lane exchange:** `B_a ≤ B0 − f·Δf` and `B_a ≤ B0 − c·Δc`. Holds termwise: non-FM gems each weigh ≤ `w_max`, and `refpp[clamp(cur_pp + 2·g_pp)] ≤ refpp[clamp(cur_pp + 2·budget)]` by monotonicity. Also forces `B0 − f·Δf ≥ B_a ≥ 0` (no negativity corruption of the max).
2. **Factor domination:** `C_a ≤ Ĉ_cm(c) ≤ C*` and `F_a ≤ Ĉ_fm(f) ≤ F*`. **Requires LUT monotone with endpoint = argmax** — verified true on real data. *If either LUT had an interior peak, `UB_fm`/`UB_cm` (which pin the off-axis factor) would under-estimate.* This is the single most load-bearing fact; re-assert it in the property test.
3. **Ψ monotone ↑ in B, C, F:** all coefficients `N, L, Σ, a1, a2 ≥ 0`, `B0 > 0`. So `Score(a,v) ≤ Ψ(B_a, C_a, F_a) ≤ UB_fm` and `≤ UB_cm` for every `(a,v)`, hence `≥ max_{a,v} Score = exact_combo`.
4. **Floors dropped upward:** exact truncates each body term and each of ≤`L` head terms; the sub-bounds drop them upward (`x ≤ real value`), and `UB_EPS = 1024` absorbs the drop (≤ `N` inside a floored term on the current side, ≤ `L ≤ 100` head, plus f32 rounding). Verified min slack ≥ 710 in-replica.
5. **Frontier / all-fever:** uses aggregate `body_total` and full ramp `Σ`; since `F ≥ 1` and every real variant's fever subset ⊆ full, aggregate ≥ `max_v`. Untouched by the coupling.
6. **`min` gives no backstop:** it takes the *smaller* value, so **each of `UB_fm`, `UB_cm` must be independently sound** — an under-estimating sub-bound is NOT rescued by the current arm. Soundness rests entirely on the concave-hull construction. Mandatory mitigation: the on-device parity sweep (§6).

**Determinism / tie-order:** the value only feeds `ub < threshold ⇒ prune` (`warmstart_common.py:106-107`, `threshold = incumbent`, ties `ub == threshold` survive). A sound `UB_gate ≥ exact` can only prune combos that could not reach the incumbent, so winner selection (`kernels_scoring.py:757-782`) and `best_score`/`best_fg_score` are bit-unchanged.

**Residual (must clear before ship):** the sub-bounds evaluate `B·F·(C·a2 + a1)` as one f32 chain at magnitudes ~4.4e9 where 1 ULP ≈ 512; the observed min sub-bound margin (710) is ~1.4 ULP. The CPU replica cannot certify the last ~2 ULP of GPU rounding order → the on-device `UB ≥ exact` sweep is **not optional**.

---

## 5. Kernel implementation sketch

**Per-run precompute (host, once — genome-invariant, ~O(161)):**
- Andrew monotone-chain upper concave hull of `refcm[0..160]` and `reffm[0..160]`. Store ≤4 segments each as `(seg_lo, seg_hi, slope, intercept)` in two tiny `ti.field`s. Cost negligible; **not per-generation** (the payoff review's correction — the original "per-generation" framing was needlessly conservative). Treat the hull fields as required cached data: **fail loud if absent**, do not add a fallback path.

**Per-thread, inside `response_score_upper_bound_relaxed` (replace body of the single bound function — one canonical implementation, no flag/toggle per CLAUDE.md):**
- All arithmetic `i32` index math + `f32` products; **no atomics, no 64-bit**; same numeric regime as existing `_semi_exact_upper_bound`.
- Compute `Δc, Δf` (2 subs), `a1, a2` (already have `N, L, Σ`), reuse `B0, C*, F*` from the current bound (factor out, share).
- `UB_fm`: loop ≤4 FM hull segments; per segment clamp vertex `f* = (B0·slope − intercept·Δf)/(2·Δf·slope)` to `[seg_lo, seg_hi] ∩ [0, k_fm]`, evaluate the concave quadratic. Evaluating at the *continuous* vertex yields a value ≥ the integer-argmax ≥ exact — no integer-neighbor evals needed, stays sound. ~10 flops/segment.
- `UB_cm`: symmetric over CM hull segments.
- `UB_gate = min(current, UB_fm, UB_cm)`; compare to threshold.
- **Per-thread cost:** ~140 extra ops (≈2×4 segment evals + 2 f32 divides) on top of the existing bound call. The exact solve it gates is ~10⁵ ops (`frontier_count` × the `(g_cm,g_fm)` double loop with head-loop rescores). Leverage ratio `S/G ≈ 1800×`.

**The one measure-before-A/B item (payoff review):** the gate inlines into the same kernel as the exact solver. Its ~10-14 f32 temporaries are dead before the solver's high-VGPR region, so a competent SPIR-V allocator should recycle them (peak VGPR rise 0-8). But on RDNA3 an 8-VGPR bump *can* cross one occupancy step; even a one-step loss leaves the change net-positive (~−8% GPU), but it must be checked. **Dump compiled kernel VGPR/occupancy with and without the block before the A/B** — this is the only variable that can demote PROFITABLE → MARGINAL.

---

## 6. Verification plan (repo-required gates — all must pass before merge)

1. **Bruteforce-vs-bound property test.** Over randomized *reachable* `(genome, combo_idx, budget, color-flags, cur_pp/cm/fm, p_val/s_val, head_len, body_total)`, assert `UB_gate ≥ exact_combo` computed by the reference exact solver, **evaluated in f32**. Include structured corners: base-saturated (`cur_pp/cm/fm` near 160), all-OV (`w_max` max, both `Δ` max), no-OV (`Δf=0`), `budget=0`, large `N` (≥60k) at high magnitude. Re-assert LUT monotonicity + endpoint-argmax as a guard. Reuse the attacker's replica scripts as the seed (`scratchpad/bb3.py`, `bb4_minslack.py`).
2. **On-device f32 assertion sweep.** Same `UB_gate ≥ exact` check run **on the Vulkan device at high score magnitude** (long songs, `N ≳ 60k`, `budget ≳ 20`) — certifies the ~2 ULP the CPU replica cannot. Non-optional per §4 residual.
3. **The 17-18 FG GPU parity tests** (`tests/test_fg_response_frontier_gpu.py` and the FG frontier byte/witness suite). Must remain green — the frontier contract is exact ordered rows + ties + witnesses, not score parity.
4. **Interleaved seeded q24 A/B, byte-identical.** Fixed `GA_SEED`, single GPU, main vs branch interleaved. Require **byte-identical** corpus sums `best_score = 1076272869` and `best_fg_score = 1023982456`. A cull-only change removes only provably-hopeless work → any divergence is a soundness failure, not noise.
5. **Re-run GA_CULL_PROBE** to measure achieved cull-rate. Expectation: 61% solve-rate → ~45-55% (a meaningful minority of hopeless-but-surviving solves; the untouched slack ceilings it below the "halving" target). Judge on **net eval-kernel device time**, not cull-rate alone.
6. **VGPR/occupancy delta** (§5) checked before step 4.

Ship only if 1-3 pass, 4 is byte-identical, 6 shows no hard occupancy regression, and 5 shows a real cull lift.

---

## 7. Graft-worthy ideas from runner-ups

- **Current-corner `C*`/`F*` instead of `C_max`/`F_max`** (from Design 1 payoff review): already folded into §3.4. Tighter for free, still sound.
- **Two-tier gating** (from Designs 2/3 payoff): run the cheap current bound first; only compute the coupled arms when tier-1 fails to cull. Keeps the extra cost off the ~39% already culled. For Design 1 the extra cost is small enough (~140 ops, O(1)) that this is optional, but it is the correct pattern if VGPR/occupancy (§5) turns out tight.
- **CF_env constrained envelope, with the association fix** (from Design 3, as a *follow-on* to reclaim the CM×FM double-count that Design 1 leaves partly on the table): precompute genome-invariant `CF_env[genome,k] = max_{i+j≤k} refcm[clamp(cur_cm+2i)]·reffm[clamp(cur_fm+3j)]`. **Do not** collapse it into a scalar body multiplier — instead carry the split argmax pair `(Ĉ_split, F̂_split)` into `_calc_body_score_i32` in the exact left-assoc order `⌊(B̂·Ĉ_split)·F̂_split⌋` (see DO-NOT #2). Only pursue after Design 1 lands, gated on the saturation histogram (§8).
- **Monotone early-exit on any scan** (from Design 2): if a scan form is ever used, break once the fever stat saturates (`cur_fm + 3j ≥ 160`) and the base is non-increasing.
- **The redirect all four designs converged on:** the dominant slack is the shared-budget quadruple-count (`kernels_scoring.py:237-241`) and the uncapped `budget·w_max` base-lane term. Design 1 attacks exactly this. `_exact_bound_ub_for_cm_fm` (`:263-329`) already resolves the shared split inside the solver — a reference for any deeper 2-D tightening.

---

## 8. DO-NOT list (from the broken / rejected designs)

1. **DO NOT pre-form `Q* = fl(B̂·F̂)` then multiply by `C*`** (Design 2). This reassociates the body product to `(B·F)·C`, whereas the exact scorer computes `(B·C)·F` (`kernels_helpers.py:419-420`). The 1-ULP-per-note deficit multiplies by `body_total` and exceeds `UB_EPS=1024`. **Concrete reachable counterexample:** `budget=10, cur_pp=160, cur_cm=140, cur_fm=157, cur_p_val=807, cur_s_val=0, N=2000, head_len=0` → true exact `63,408,000`, `UB_joint = 63,407,024`, **deficit 976** → a genuine winner is culled. ~16% of the integer base-value range flips.
2. **DO NOT fold `C·F` into a precomputed scalar `M̂` for the body term** (Design 3). Same reassociation `bv·(C·F)` vs exact `(bv·C)·F`; at `budget=0` on a base-saturated combo the deficit is up to `body_total − 1024` (negative margin once `body_total ≳ 1124`, ordinary chart sizes). If you use `CF_env`, carry the split multipliers in exact order (see §7 graft).
3. **DO NOT rely on a flat `UB_EPS` to absorb body-scaled drift.** The reassociation error scales with `body_total`; a constant cushion provably cannot cover it. Either preserve the exact multiplication association, or `UB_EPS` must scale with `body_total` (which defeats the cull-rate gain).
4. **DO NOT validate soundness on the CPU replica only.** f32 GPU rounding order differs; the on-device sweep is load-bearing.
5. **DO NOT ternary- or two-pointer-search any concave/coupled sweep.** Floors and `[0,160]` clamps break strict unimodality; a missed maximum under-estimates → corruption. Take the full max (closed-form per hull segment is fine; the vertex is provably ≥ the integer argmax).
6. **DO NOT pursue neighbor-anchored delta bounds** (Design 4B). With incumbent lag 0.0% (`threshold ≈ max_c exact(c)`), a `Δ` tight enough to cull requires `Δ < threshold − exact(c')`, which only the exact shared-budget re-solve certifies. Any cheap `Δ` satisfies `exact(c') + Δ ≥ relaxed_ub(c)` — no tighter than the bound it replaces, and an undercount corrupts `best_score`.
7. **DO NOT pursue FT-row hierarchical culling** (Design 4A). `row_ub(ft) = max_ff relaxed_ub(ft,ff) ≥ relaxed_ub(ft,ff)`, so it culls a strict *subset* of the per-combo bound → **zero** exact-solve reduction. It also does not map to the strided lane loop (`ga_eval/warmstart.py:119-199`, `local_c += block_dim` interleaves rows across lanes), so "skip the rest of a row" is not realizable per-lane. Adds registers to the 72.5%-of-GPU kernel for no gain.
8. **DO NOT add a feature flag / old-new switch / workload-routed variant.** Replace the body of `response_score_upper_bound_relaxed` in place; the hull fields are required cached data (fail-loud if missing), not an optional route. The change is all-or-nothing (CLAUDE.md canonical-path rule).

---

## 9. File index

| Component | Location |
|---|---|
| **Target bound (replace body)** | `kernels_scoring.py:197-260`; substitutions `:237-241`; `B0` `:242`; `C*/F*` `:243-244`; head coeffs `:246-247` |
| `_semi_exact_upper_bound` (current body/head/EPS) | `kernels_scoring.py:176-194`; `_calc_body_score_i32` `:21-32` |
| Exact allocation solver (reference for property test) | `kernels_scoring.py:332-787`; weights `:366-378`; caps `:391-419`; `_exact_bound_ub_for_cm_fm` `:263-329` |
| Frontier max over variants | `kernels_scoring.py:790-846`; rescore `:63-173` |
| Score fn (body/head floors — exact association) | `kernels_helpers.py:394-513`; `:419-420`, `:442-513` |
| LUTs + clamp (monotonicity guard) | `kernels_helpers.py:197-250`; source `Data/Gear/Stats.txt` |
| Cull gate (`ub < threshold ⇒ prune`) | `warmstart_common.py:16`, `:83`, `:87-107` |
| Strided lane loop / incumbent / threshold | `ga_eval/warmstart.py:119-206` |
| Hull-field precompute (new) | co-locate with ref-table load, `api/initialization.py:383-385` |

All kernel paths under `gear_optimizer/solver/taichi_gem/kernels/`. Implementation touches **only** `kernels_scoring.py:197-260` plus the two new hull fields + their once-per-run build; the exact solver (`:332-787`), head closed form, cull gate, and winner selection are unchanged.

---

## 10. Implementation notes (as-built, 2026-07-16)

Shipped per §1 with two deviations forced by the real data; both preserve the hard contract (`UB ≥ exact`, tighten-only) and are recorded in `docs/CODEX_WORKLOG.md`.

**(a) Envelope segment count.** §3.4/§5 projected "≤4 segments each" assuming a piecewise-linear table. `Data/Gear/Stats.txt` CM/FM are a smooth strictly-concave-ish curve (161 samples); the **exact** Andrew concave majorant has ~111/114 segments. Soundness needs only a *concave dominating* envelope, so `concave_hull.py` builds a tight **bounded-segment** envelope — the lower envelope (pointwise `min`) of a greedily selected subset of the exact hull's segment lines (each dominates the LUT), refined to max relative gap `< 0.2%` or a 16-segment cap (`MAX_CONCAVE_HULL_SEGMENTS`). Real data → 9 (CM) / 13 (FM) segments at ~0.2% gap. A 4-segment envelope would be materially looser (less cull profit) with no perf benefit: the in-kernel sweep is a runtime `while` loop, so its iteration count does not raise VGPR/occupancy, and its ALU cost is negligible vs the ~1e5-op exact solve it gates.

**(b) §4.2 `Ê ≤ C*` is tightness, not soundness.** `UB_cm ≥ exact` needs only `C_a ≤ Ê_cm(c)` (dominance) + `Ψ` monotone in `B,C,F`; the pinned-`F*`/`C*` corner needs only `F_a ≤ F*` / `C_a ≤ C*` from LUT monotonicity+endpoint-argmax, which is asserted at build. A bounded envelope may exceed `C*` on some cells, which only loosens `min()` there — never unsound. Endpoint==argmax (the load-bearing fact) is still asserted (fail-loud) at hull build.

**Files.** New: `solver/taichi_gem/concave_hull.py` (Taichi-free host math); kernel arms `_coupled_ub_fm/_cm` + `_eval_coupled_fm/_cm` and the `min()` in `kernels_scoring.py`; hull upload in `api/initialization.py::load_ref_arrays` + `_upload_concave_hull`; fields `hull_{cm,fm}_{seg,count}` across `fields.py` / `kernels_helpers.py` / `kernels/__init__.py`. Tests: `tests/test_ub_cull_hull_dominance.py` (CPU, runnable), `tests/test_gpu_ub_cull_bound_property.py` (gpu-marked, on-device `exact ≤ UB_gate ≤ old`). Fingerprint ledgers untouched (cull-only, byte-identical scoring).