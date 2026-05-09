# Skyline Speedup & Theorem Revisit Analysis

Date: 2026-05-08
Branch: research-3
Song: Data/Hard/00 (Hard) by garlagan.txt (33,061,828 baseline)

---

## 1. Current Baseline (speedup anchor)

| Stage | Time | % of total | GPU migration target |
|-------|------|------------|---------------------|
| gear DP | ~0.1s | 0.1% | Low priority |
| gear global skyline | ~0.7s | 0.6% | 3-8x via 4D suffix-max GPU kernel |
| gear local envelope prune | ~0.0s | — | Not bottleneck |
| theorem5 response prune | skipped | — | Gear cap (768) blocks 1,443 gears → revisit |
| **combined skyline pairs** | **~111s** | **98%** | **10-50x via Taichi outer-sum + grid scatter + 4D suffix-max** |
| combined envelope prune | ~0.06s | — | Not bottleneck |
| final pair eval (GPU) | ~0.8s | 0.7% | Already GPU |
| fever solver wrap-up | ~0.3s | 0.3% | Already exact (bounded BnB inner solver) |
| **Total** | **113.5s** | | **Target: 4-13s (match GA's 4s)** |

---

## 2. Moonshot/Theorems Revisit — What's Worth Pursuing Now

### HIGH IMPACT — Proven, Needs Engineering

#### Moonshot 6: Cross-Candidate FG Timeline Amortization
- **Verdict**: PROVEN for timeline/frontier artifacts
- **What**: Config enumeration + dedupe cost paid O(|FT/FF pairs|) instead of O(|candidates| × |FT/FF pairs|)
- **Speedup**: ~50x reduction in FG config enumeration cost per song-wide run
- **Risk**: None for timeline/frontier artifacts (PP/CM/FM not involved in timeline computation)
- **Action**: Shift config frontier computation from per-candidate to per-(FT,FF) pair level

#### Moonshot 5: Unified Sufficient State Key
- **Verdict**: READY (from implementation checklist)
- **What**: Compressed key using effective multiplier buckets (current + next-gem marginals)
- **Speedup**: 2-4x memory reduction for GlobalUniqueEvalTable + cache key size
- **Risk**: Low (existing correctness tests in test_theorem_readiness_moonshot5_key.py)
- **Action**: Implement as exact-eval cache key replacement

#### Theorem 5 Guardrails
- **Verdict**: Caps are research-era safety limits, not mathematical bounds
- **Problem**: `EXACT_SKYLINE_THEOREM5_MAX_GEARS=768` blocks 1,443 gears
- **What theorem-5 does**: Evaluates gear × lambda-response-class matrix, removes gears dominated across all mini response classes — an additional ~23-25% gear reduction
- **Why blocked**: O(G² × L) dominance check is CPU-bound at high G
- **Action**: Raise cap to 2,000 (with timing measurement), or GPU-accelerate the response dominance check

### MEDIUM IMPACT — Proven But Needs Real-Song Validation

#### Moonshot 2: FG Automaton DP Sufficiency
- **Verdict**: PROVEN with production-equivalent DP state (reference code exists in fg_exact_dp.py)
- **What**: DP over (section_index, activation_carry) finds globally optimal FG configs
- **Speedup**: DP takes 2-26ms CPU per solve vs production GPU FG at 1-7.5s per run
- **Risk**: Production parity on real songs remains unproven (synthetic parity tests pass)
- **Action**: Validate DP output against production GPU FG on real songs

### LONG-TERM — Needs Production-Domain Proof

#### S9: FG Dual-Mechanism Decomposition
- **Verdict**: BLOCKED_CONDITIONAL for production skip (loose bound = safe but not useful)
- **What**: FG score change decomposes into Window Shift + Activation Creation → O(1) upper bound
- **Potential**: If production-domain admissibility is proven, could pre-skip FG for loadouts where bound ≤ 0
- **Action**: Prove admissibility over full production domain (FT/FF choice, retained frontiers, HitSim, tie policy)

### DO NOT PURSUE
- **Moonshot 3** (FT/FF language dominance — strong form FALSE)
- **Moonshot 4** (greedy-exact — FALSE, BnB is necessary)
- **Moonshot 7** (full 8D envelope — 10^12 skyline points, astronomically large)
- **S1/S5** (activation-count FG skips — unsafe, needs exact mask certificate)
- **S8** (near-tie composite key — FALSE, can select lower exact score)

---

## 3. FG Integration Analysis

### Current Architecture
```
GA (outer search) → persist loadout → FG Optimizer (separate pipeline, re-solving stats)
```

FG re-solves (FT, FF, FG_config, gem_allocation) from scratch for each candidate using its own GPU kernels — completely separate from GA's registry solve. FG uses a flat 3D work grid of (genome, FT/FF, config_chunk) items.

### Can FG Be Folded Into Skyline?

**Technically yes, but NOT via per-point full FG evaluation during GA generations.**

The cleanest approach is a **two-stage skyline with FG-awareness**:

#### Stage 1: GA Skyline (base scores only — fast)
- Evaluate (gear, minis) pairs via existing gem solver
- Use 2D Pareto frontier in (base_score, fg_proxy_score) space for dominance
- fg_proxy_score already computed in `fg_candidate_selector.py`

#### Stage 2: FG Skyline (on top-K survivors only)
- Run full FG finder on surviving skyline candidates
- Amortize config frontier per (FT,FF) pair via Moonshot 6
- Keep the better of (base result, FG result) per candidate

This preserves GA throughput while making skyline FG-aware at negligible Stage 1 cost. The fg_proxy_score prevents pruning low-base/high-FG-potential loadouts.

### Why NOT Naive Integration

| Approach | FG evals | Wall time | Feasible? |
|----------|---------|-----------|-----------|
| Per-point FG during GA generations | 10,000 × FG | ~2-15s additional per generation | **No** — kills GA throughput |
| Aggressive caching (same 7-tuple stats reuse) | ~500 FG | ~0.5-2s | Marginal, still too slow per gen |
| Post-skyline FG only (current) | ~50 FG | ~0.02-0.15s | **Yes**, but FG-unaware dominance |
| **Two-stage with fg_proxy frontier** | ~50 FG + proxy scores | ~0.02-0.15s | **Yes**, FG-aware at Stage 1 |

---

## 4. Action Plan — Ranked by Impact

### Priority 1: GPU-accelerate combined skyline pairs
- **Impact**: 10-50x (111s → 2-11s)
- **Approach**: Taichi kernel for outer-sum + grid scatter + 4D suffix-max
- **Risk**: Medium (1.5 GiB GPU memory, grid allocation)

### Priority 2: Raise Theorem 5 caps + benchmark
- **Impact**: ~25% gear reduction (1,443 → ~1,082) → smaller combined skyline
- **Approach**: Set `EXACT_SKYLINE_THEOREM5_MAX_GEARS=2000`, `EXACT_SKYLINE_THEOREM5_MAX_EVALS=262144`
- **Risk**: Low (just changing env vars, measuring CPU cost)

### Priority 3: Implement Moonshot 6 (FG amortization)
- **Impact**: ~50x reduction in FG config enumeration across skyline candidates
- **Approach**: Shift frontier computation to per-(FT,FF) pair level
- **Risk**: Low (proven safe, architectural change only)

### Priority 4: Two-stage skyline with FG proxy frontier
- **Impact**: Prevents pruning low-base/high-FG candidates during skyline
- **Approach**: 2D (base_score, fg_proxy_score) frontier for dominance checks
- **Risk**: Low (fg_proxy_score already exists, just added to dominance key)

### Priority 5: Implement Moonshot 5 (compressed cache key)
- **Impact**: 2-4x memory savings, modest speedup
- **Approach**: Effective multiplier bucket key replacement
- **Risk**: Low (existing tests)

### Priority 6: Validate Moonshot 2 (FG DP) on real songs
- **Impact**: Potential to replace GPU FG with 2-26ms CPU DP
- **Approach**: Run DP parity benchmark against production FG
- **Risk**: Medium (real-song parity not yet proven)
