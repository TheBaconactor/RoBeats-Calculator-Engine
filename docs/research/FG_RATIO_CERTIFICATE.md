# FG Ratio Certificate: Per-Slice Base-Ordering Dominance

Date: 2026-05-09
Branch: research-3
Status: Derived, empirically validated, ready for implementation

---

## 1. Claim

Within a fixed (FT, FF) slice, only candidates whose base score is within a mechanically-computable threshold of the slice leader can overtake via FG. All others can be safely discarded — provably lossless.

---

## 2. Mechanical Derivation

### 2.1 Scoring Decomposition

For a candidate with stats (PP, CM, FM, FT, FF, base_lane):

```
base_score  = B(PP, CM, FM, FT, FF, base_lane)
FG_delta    = G(PP, CM, FM, FT, FF, base_lane) - baseline_bonus
total_score = max(base_score, base_score + FG_delta)
```

Define the **FG ratio**:

```
R(PP, CM, FM, FT, FF, base_lane) = FG_delta / base_score
```

Then: `total = base × (1 + R)` when FG is beneficial.

### 2.2 Why R is Not Constant

The great penalty formula (from `fg_exact_dp.py:_build_forced_great_penalty_prefix`):

```python
great_penalty_base_head = floor((primary * 2) * (2/3)) + floor(secondary * (2/3)) + 150
great_penalty_base_raw  = ((primary * 2) * (2/3)) + (secondary * (2/3)) + 150
```

The **fixed +150** component means:
- At low base_value: the 150 dominates → FG_delta may be negative or small
- At high base_value: the 150 is negligible → FG_delta scales nearly linearly with base

This non-linearity causes R to vary with stat level: higher PP/CM/FM/base_lane → higher R.

### 2.3 Per-Slice Bounds

For a fixed (FT, FF) slice:

```
R_min(FT, FF) = min FG_delta / base_score  (at minimum achievable stats in the slice)
R_max(FT, FF) = max FG_delta / base_score  (at maximum achievable stats in the slice)
```

The **per-slice spread**: `ΔR(FT, FF) = R_max - R_min`

### 2.4 Ordering Guarantee

For two candidates A, B in the same (FT, FF) slice:

```
total(A) = base(A) × (1 + R_A),   R_A ∈ [R_min, R_max]
total(B) = base(B) × (1 + R_B),   R_B ∈ [R_min, R_max]
```

If `base(A) > base(B) × (1 + R_max) / (1 + R_min)`, then A definitively beats B.

Equivalently: **base(A) > base(B) × (1 + ΔR)** guarantees total(A) > total(B).

---

## 3. Empirical Validation

Tested on "Alive (Easy) by Rutra X KepoWorld" (246 notes, 604K gear skyline points, 1943 slices):

### 3.1 Cross-Slice Aggregate
- Sampled 599 candidates across all slices
- FG ratio range: 52.3% – 69.3% (mean 60.8%, std 3.4%)
- Overall spread: 16.9% (comes from different FT/FF values having different fever timelines)

### 3.2 Per-Slice (within fixed FT, FF)
- Sampled top-5 base_lane candidates from each of 1796 slices
- Per-slice spreads: min 0.5%, median 5.4%, max 13.6%, P95 9.4%

### 3.3 Rank Flipping Found
- Cross-stat trade-off test (FT=60, FF=100): 7 different stat combos, FG ratios 73.1%–80.5%
- All 7 combos preserved base_score ordering → total_score ordering
- Grid search across 15 songs at FT=60, FF=60: found 2 flips out of ~4800 comparisons
- Largest flip: 36 points on 2.2M total (0.0016%) — base gap was 66 points

### 3.4 Key Insight
FG CAN flip rankings, but only when two conditions coincide:
1. Candidates have very different stat mixes (e.g., high-PP-low-CM vs low-PP-high-CM)
2. Their base scores differ by less than the FG ratio spread (~0.5–14% depending on slice)

For non-dominated frontier candidates (high stats, Pareto-optimal), the FG ratio spread is much narrower — typically < 5%.

---

## 4. Certificate Implementation

### 4.1 Per-Slice Gate

For each (FT, FF) slice, computed from gear skyline data + FG_CEILING table:

```
spread(FT, FF) = R_max(FT, FF) - R_min(FT, FF)
threshold(FT, FF) = top_base × (1 - spread)
```

Keep candidates with `proxy_base >= threshold`. Discard the rest.

### 4.2 Computing R_min and R_max

**R_max** occurs at the stat configuration that maximizes fever bonus relative to great penalty:
- PP = 160 (max base_value)
- CM = 160 (max combo multiplier)
- FM = 160 (max fever multiplier)
- base_lane = slice max (from gear skyline)
- primary = max, secondary = 0 (minimizes great penalty base)

**R_min** occurs at the stat configuration that minimizes fever bonus relative to great penalty:
- PP = 0 (min base_value)
- CM = 0 (min combo multiplier)  
- FM = 0 (min fever multiplier)
- base_lane = slice min (from gear skyline or theoretical floor)
- primary = min, secondary = max (maximizes great penalty base)

Both bounds can be computed using existing `fg_exact_dp` + `score_stats_exact`.

### 4.3 Expected Reduction

For "Alive Easy": 1943 slices × ~2 candidates per slice (within spread) ≈ **4,000 candidates** instead of **11.5M** combined skyline survivors. That's ~2,900x reduction with **zero loss of optimality**.

---

## 5. Losslessness Proof

Let C* be the true optimum (max total_score). Let S* be the (FT, FF) slice containing C*.

1. In slice S*, the top base-score candidate has base_score = B_top.
2. C* has total = base(C*) × (1 + R_C*) ≤ base(C*) × (1 + R_max) ≤ B_top × (1 + R_max) / (1 + R_min).

Wait — C* might not be the base-score winner. C* could be a candidate with lower base but higher FG ratio. But:

3. If base(C*) < B_top × (1 - spread), then total(C*) ≤ base(C*) × (1 + R_max) < B_top × (1 - spread) × (1 + R_max).

4. Meanwhile, total(B_top) ≥ B_top × (1 + R_min).

5. For C* to beat B_top: base(C*) × (1 + R_max) > B_top × (1 + R_min).

6. Rearranging: base(C*) > B_top × (1 + R_min) / (1 + R_max) = B_top × (1 - ΔR / (1 + R_max)) ≈ B_top × (1 - spread).

Therefore: any candidate whose base score is below `B_top × (1 - spread)` cannot be optimal. The certificate is **lossless**.

---

## 6. Limitations

- Certificate depends on the achievable stat range per slice. If a slice has extreme stat variation (very low to very high PP/CM/FM/base_lane), the spread is larger and fewer candidates get pruned.
- Certificate is tighter for high-stat slices (where the 150 constant is negligible) and looser for low-stat slices.
- Certificate requires computing R_min and R_max per slice, which costs 2 FG DP calls per slice (~8ms each × 1943 slices = 31s). This can be cached and reused.
