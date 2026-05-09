# Skyline GPU Pipeline Handoff for GPT 5.5

Date: 2026-05-08
Branch: research-3
Status: Ready for implementation

---

## Goal

Make the exact skyline solver fast on ALL difficulties (Easy through Hard). The pipeline is mathematically complete — every reduction is proven lossless. The gap is purely engineering: port remaining CPU stages to GPU, batch aggressively, collapse redundant work.

---

## 1. Gear Global Skyline GPU Port

**File**: `gear_optimizer/solver/exact_skyline.py:748-905`  
**Function**: `_global_gear_skyline_points_6d_lane_base_with_codes`

**What it does**: Takes the DP output (`dict[4D-key → frontier-list]`), sorts/flattens per PP layer, scatters into a 4D (CM×FM×FT×FF) grid, runs suffix-max, filters dominated cells, and emits surviving gear points with codes.

**Why GPU**: Same 4D scatter → suffix-max → filter pattern already GPU-accelerated in `combined_skyline_gpu.py` (the combined skyline pairs stage). The gear version is simpler — no mini outer-sum, just flat-index scatter from the DP states. Reuse the existing kernel template directly.

**Exactness**: The scatter atomic-max + suffix-max axis order = lexsort + unique + accumulate. Commutative, associative — identical result. Same proof as `COMBINED_SKYLINE_GPU.md`.

**Template**: `combined_skyline_gpu.py` — scatter kernel, 4× suffix kernels (`_suffix_cm/fm/ft/ff`), filter kernel. Reuse verbatim.

**Wiring**: In `exact_skyline.py:_solve_exact_skyline_ctx`, replace the CPU call with the GPU version. Import from new module `gear_skyline_gpu.py`.

**Memory**: Three int32 grids (layer, owner, higher) at `cm×fm×ft×ff` elements. Guardrail at 250M elements ≈ 2.8 GiB. Fits under 24 GB.

---

## 2. Lambda Class Pareto Collapse

**File**: `gear_optimizer/solver/exact_skyline.py:493`  
**Function**: `_collapse_mini_response_classes_with_codes`

**The theorem**: After grouping minis by `(CM, FM, FT, FF)`, if lambda class A Pareto-dominates class B on all 5 coordinates `(CM, FM, FT, FF, max_base)`, then B is redundant.

**Proof**: For any gear G, `stats(G + A) ≥ stats(G + B)` componentwise. By monotonicity of the score function, `score(G, A) ≥ score(G, B)`. If gear X dominates gear Y on class A, it necessarily dominates Y on class B too. **Strictly lossless**.

**Impact**: Reduces lambda classes by ~30% on Easy (114 → ~80). Since theorem-5 is O(G × L), this directly reduces GPU eval pairs and Python loop iterations by ~30%.

**Implementation**: Already done in `exact_skyline.py` — the function now applies per-lambda-class Pareto dominance after the max-base-per-group step. Verify it's wired into the theorem-5 prune path and produces correct lambda reduction.

---

## 3. 2D Base+FG Frontier (Unified Skyline Dominance)

**File**: `gear_optimizer/solver/exact_skyline.py:_solve_exact_skyline_ctx` (final candidate loop)

**What**: Currently each skyline candidate gets a base score + FG delta computed via exact DP. But the combined skyline dominance check only uses base score to prune — a loadout with lower base but higher FG potential can be prematurely removed.

**Fix**: The combined skyline stage should use 2D Pareto dominance in `(base_score, base_score + fg_delta)` space. A point is only pruned when dominated in BOTH dimensions. This is trivially lossless — it can only keep MORE candidates, never remove an authoritative one.

**Wiring**: In the combined skyline filter or during candidate evaluation, pass both scores. The FG delta is computed per candidate via exact DP (already wired). Just use the effective score as a second dominance dimension.

**Cost**: Zero additional GPU work — FG DP already runs on final candidates. This is just adding a second coordinate to the existing dominance check.

---

## 4. Bulk Batch Assembly (Theorem-5 & Cartesian Eval)

**Files**:
- `gear_optimizer/solver/exact_skyline.py:577` — `_evaluate_response_matrix_exact`
- `gear_optimizer/solver/exact_skyline.py:908` — `_evaluate_product_exact`

**What**: Both functions use nested `for gi... for mi...` Python loops to assemble 9-int genome batches, calling `batch[:n].copy()` per flush, and submitting ~1,600+ individual GPU batches. For 6.7M pairs on Easy, Python overhead dominates.

**Fix**: Pre-build the full (G×M×9) int32 array once via NumPy broadcast/tile, then submit in 4,096-row chunks. This is a mechanical reorder — no math change, the GPU sees the same batches in the same order.

**Impact**: Collapses ~30s of Python assembly per function to <1s. Directly reduces theorem-5 from 198s → ~3s and cartesian eval from 163s → ~3s on Easy.

---

## 5. Per-Slot Pareto Prune (Already Done)

**File**: `gear_optimizer/solver/marginal_pruning.py` — `prune_gear_pool_marginal`

**What**: Replaced the old heuristic scalar-score top-K prune with per-slot 6D Pareto dominance. An item strictly dominated by another in the same slot is provably never optimal (Minkowski-sum property). Already committed.

**Side effect**: True 6D dominance is rare in practice — the prune does little reduction on Easy (from 267 → ~250 items) because elemental base_lane creates genuine tradeoffs (high PP vs high base_lane vs high FT/FF). This is geometrically correct — there's no stronger per-slot theorem.

---

## Pipeline Before vs After (Easy Song Estimate)

| Stage | Before | After | Saving |
|-------|--------|-------|--------|
| Per-slot Pareto prune | <1s | <1s | — |
| Gear DP | ~9s | ~9s | — (sequential by nature) |
| **Gear global skyline** | **8.8s** | **~0.03s** | **8.7s** (GPU port) |
| Envelope prune | ~0.2s | ~0.2s | — (groups too small) |
| **Lambda class collapse** | **114 classes** | **~80 classes** | **30%** (Pareto reduction) |
| **Theorem-5 (matrix + dominance)** | **198s** | **~3s** | **195s** (bulk batch + 30% smaller) |
| Combined skyline | 0.4s | 0.4s | — (already GPU) |
| **Cartesian evaluation** | **163s** | **~3s** | **160s** (bulk batch) |
| FG exact DP scoring | ~0.2s | ~0.2s | — (already fast) |
| **Total** | **~379s** | **~16s** | **363s** |

Hard: ~3s → ~2.5s (same pipeline, smaller frontier).

---

## What NOT to Do

- Do NOT add concurrent interleaving of theorem-5 — can't prove dominance from a subset of lambda classes
- Do NOT add early breakout on partial axes — same issue
- Do NOT add new heuristic prunes — all reductions must have a proof
- Do NOT add CPU fallback paths — research-3 is GPU-first
- Do NOT overengineer the gear skyline port — reuse the existing kernel template, don't build a new framework

---

## Key Files

| File | Role |
|------|------|
| `gear_optimizer/solver/exact_skyline.py` | Main skyline solver (gears skyline, theorem-5, combined, eval) |
| `gear_optimizer/solver/combined_skyline_gpu.py` | GPU template — scatter + 4× suffix + filter kernels |
| `gear_optimizer/solver/marginal_pruning.py` | Per-slot Pareto prune (done) |
| `gear_optimizer/solver/fg_exact_dp.py` | FG exact DP (imported into skyline) |
| `tools/experiments/skyline_single_song.py` | Single-song experiment harness |
| `docs/Implementation Records/COMBINED_SKYLINE_GPU.md` | Exactness lemma |
| `docs/research/SKYLINE_BASELINE_EXPERIMENT.md` | Authority baseline |
| `docs/research/THEOREM_FG_COMPLETENESS_DERIVATION.md` | FG integration theorem |

## Test Song

`Data/Hard/00 (Hard) by garlagan.txt` — authority baseline: GA = 33,061,828, Skyline = 33,061,828.

## Verification

Run `python -m pytest tests/test_combined_skyline_gpu_parity.py -q` for each GPU stage.  
Run `python tools/experiments/skyline_single_song.py --no-fix-minis` on both songs for end-to-end authority.
