# Gem Solver: O(1) Closed-Form Scoring and 2D Enumeration Research

## Status: Research validated, pending GPU implementation

## Context

The gem solver (`optimize_core_device` / `optimize_core_jit`) is the innermost hot function in the
GA evaluation pipeline. It runs once per (genome x FT/FF combo) pair, with ~512 genomes and ~4,186
combos per generation = ~2.1M calls per GA generation.

The current implementation uses a greedy algorithm with 90 iterations, each evaluating up to 4 gem
options. Each evaluation calls `calc_score_with_grid_bits` which loops over the head notes (up to
100 iterations). A refinement pass adds ~725 additional evaluations.

Total work per gem solve: ~636K ops (greedy: 90 x 2,400 + refinement: 725 x 600).

## Problem

1. The O(head_len) inner loop is a serial bottleneck within each GPU thread, limiting ALU utilization
   and occupancy on the RX 7900 XTX.

2. The greedy algorithm is not globally optimal. It can get stuck in local optima, particularly
   around CM stat breakpoints (discrete multiplier lookup table). The existing refinement pass
   partially addresses this but is itself expensive and incomplete.

## Decision: Two-Part Decomposition

### Part 1: O(1) Head Score via Precomputed Coefficients

The head score formula:
```
head_score = sum_{i=0}^{H-1} floor((base + (i+1) * factor) * mul_i)
```
where `factor = (combo_mul - 1) * base / 100` and `mul_i = fever_mul if fever[i] else 1`.

Observation: for a fixed fever mask, the head score depends on only 4 mask-derived constants:
- `N_hn` = count of normal notes in head
- `N_hf` = count of fever notes in head
- `Sigma_hn` = sum of (i+1) for normal head notes (position-weighted count)
- `Sigma_hf` = sum of (i+1) for fever head notes (position-weighted count)

The semi-exact score uses:
- Exact body score (already O(1): 2 multiplies + 2 truncations)
- Approximate head score: `base * (N_hn + F * N_hf) + factor * (Sigma_hn + F * Sigma_hf)` [O(1)]

Error bound: at most H points (100 max) from dropped floor() operations.

### Part 2: Direct 2D (CM, FM) Enumeration

With O(1) scoring, the gem allocation problem can be reformulated:
- score(pp, cm, fm, ov) = base(pp, cm, fm, ov) * G(C(cm), F(fm)) approximately
- For fixed (gems_cm, gems_fm): C and F are determined, remaining budget splits between PP and OV
- PP/OV split maximizes base_value, which is concave in gems_pp -> ternary search O(log R)
- Enumerate all valid (CM, FM) pairs: ~1,500-4,374 depending on budget and stat caps

This replaces the 90-iteration greedy loop + refinement with a single pass that finds the
globally optimal allocation.

## Validation Results

Tested on 10 Hard songs x 30 gear configs x 15 FT/FF combos = 4,500 cases.

### O(1) Scoring Accuracy
- Allocation match with exact greedy: 99.9% (4,498/4,500)
- Score match: 99.9% (4,498/4,500)
- **O(1) greedy never scores worse**: 4,500/4,500 cases >= exact greedy
- In 2 mismatched cases, O(1) scoring found BETTER allocations

### 2D Enumeration vs Greedy
- **Beats greedy in 23.9% of cases** (359/1,500 in focused run)
- Score uplift when enum wins:
  - Mean: +147,660 points (+0.74%)
  - Median: +76,340 points (+0.39%)
  - Max: +1,077,662 points (+2.65%)
  - p90: +345,161 points (+2.02%)

## GPU Implementation Plan

### Phase 1: Precompute Mask Coefficients
- Add 4 Taichi fields: `grid_N_hn`, `grid_N_hf`, `grid_Sigma_hn`, `grid_Sigma_hf`
  - Shape: (MAX_SONG_SLOTS, 161, 161) i32
  - Compute in `compute_timeline_grid_kernel` alongside existing grid fields
  - VRAM: 4 x 4 bytes x slots x 161 x 161 = ~413 KB per slot

### Phase 2: O(1) Scoring Function
- New `@ti.func calc_score_o1_device(base, combo_mul, fever_mul, N_hn, N_hf, Sigma_hn, Sigma_hf, count_fever, count_normal) -> i32`
- Exact body + approximate head in ~10 ops

### Phase 3: 2D Enumeration Solver
- New `@ti.func enumerate_2d_solve_device(...)` replaces `optimize_core_device_refined`
- Enumerate valid (CM, FM) pairs with ternary-search PP solve
- Expected: ~15K-90K ops vs ~636K current -> 7-42x faster per gem solve

### Phase 4: Integration
- Replace refined solver calls in `combo_search.py`, `warmstart.py`, `write_results.py`
- Final score materialization uses exact scoring (one O(head_len) evaluation per winner)
- Run GPU parity tests with relaxed tolerance (2D enum may find higher scores)

## Expected Impact
- **Score quality**: +0.74% average in affected evaluations (24% of all evaluations)
- **Throughput**: 7-42x per-gem-solve speedup; estimated 2-5x overall GA generation improvement
- **GPU utilization**: Eliminates serial head loop, better ALU pipelining

## Risks
- Floor() approximation error could cause wrong selection in rare edge cases (mitigated by
  the empirical 99.9% match rate and the fact that mismatches produced BETTER scores)
- 2D enumeration compute cost scales with max_cm x max_fm; need to confirm GPU thread budget
- Changes to scoring kernels have wide blast radius; thorough parity testing required

## Artifacts
- Research tool: `tools/bench/research_gem_solve_closed_form.py`
- Key functions: `precompute_mask_coefficients()`, `score_semi_exact()`, `enumerate_2d_solve()`
- Worklog: `docs/CODEX_WORKLOG.md` (session: "Research - O(1) Closed-Form Gem Solving Breakthrough")
