# HitSim Boundary-Dimension Plan

This document captures a forward-looking architecture idea discussed for HumanHitSim, song repeats, and boundary-sensitive score search.

The short version:

- Today, `SongRepeats` is partly acting as a queue-level GA restart hack to find "lucky" HumanHitSim boundary flips.
- A cleaner future model is to replace luck-driven repeats with deterministic, analytically derived HitSim boundary regimes.
- That future model fits the codebase well, but the exact integration depends on whether HitSim applies to `FG` only or to `ALL` scoring.

## Goal

Replace "retry the whole song with another random seed and hope a fever boundary flips" with a deterministic search model that:

1. Analytically identifies where boundary flips can occur.
2. Builds explicit timing regimes or dimensions that are guaranteed to realize those flips.
3. Evaluates those regimes under one higher-level song attempt instead of treating each as a separate opaque repeat.
4. Reuses work aggressively where the timing regime does not actually change the GA objective.

## Implemented Direct Upgrade

The current codebase now has an incremental step toward this architecture in the existing `ApplyTo=ALL` post-GA refinement path:

- refinement supports an `exact` deterministic boundary-table mode over the timing envelope
- exact mode evaluates deterministic boundary regimes against a full `161 x 161` FT/FF boundary domain
- legacy sampled/seeded refine modes have been removed as separate implementations
- old `RefineMode`/`RefineDevice` values are accepted only as aliases and normalize onto the exact GPU path
- refinement can score a bounded top GA candidate pool and replace the final winner when another candidate wins under a refined timing variant

This is a concrete step into the boundary-regime architecture described below.
It is still limited to the current global timing-envelope model rather than a richer multi-axis perturbation space.

## Current Exact-Mode Audit

The newly implemented `exact` refinement mode is useful, but it should be understood correctly.

What it does well:

- it removes seed luck from the post-GA refinement path
- it evaluates deterministic timing regimes instead of random repeats
- it uses the full `161 x 161` FT/FF boundary domain to derive boundary-row families
- it prunes FT/FF rows that never change across the timing envelope
- it persists regime identity, scope, and interval bounds on the selected winner

What it does not yet do:

- it still starts from the global alpha-envelope intervals and then lets boundary rows collapse them
- it still materializes raw alpha intervals before a fully symbolic table-driven regime planner could prune them
- it is still a post-GA refinement stage, not the final `song -> candidate pool -> regime fanout -> merged result` scheduler

So the current `exact` mode should be treated as:

- a stronger deterministic direct upgrade
- not the final form of the architecture described in this document

## Current Phase 2a Status

The latest implementation slice tightened two architectural gaps that mattered for same-process multi-regime execution:

- timing-sensitive caches are now regime-aware, so gem/timeline cache entries no longer alias across `ApplyTo=ALL` regimes
- exact-mode planning now uses a compact planner-only signature path, which removes full head-mask allocation from the regime-family discovery loop
- exact-mode planning is now candidate-aware: the full `161 x 161` FT/FF domain is still preloaded for counts/audit, but runtime regime families are derived from the candidate-relevant timeline rows inside the current witness pool
- exact mode also supports an optional capped-regime benchmark path (`RefineMaxRegimes` + `RefineRegimeSelection`) so top-1 preservation can be measured against the uncapped exact reference

What the latest benchmark showed:

- before the candidate-aware planner change, `BUBBLE TEA (Hard)` needed about `55s` for isolated exact refinement even when the capped path kept only `18` regimes, because the full-domain planner still dominated the runtime
- after the candidate-aware planner change, the same isolated `BUBBLE TEA (Hard)` exact refinement dropped to about `0.67s`, and the capped `18`-regime path still matched the full-exact top-1
- on `Aether (Hard)`, the candidate-aware exact refinement used `8` candidate witnesses, changed the winning loadout, and still matched the capped `18`-regime path in about `0.56s`

So the next real performance phase is unchanged:

- move from `raw-interval enumeration -> collapse -> optional cap`
- to `table-derived regime generation -> early pruning -> evaluate only retained regimes`

The main remaining con is now narrower:

- raw alpha-interval enumeration still happens before runtime regimes are collapsed
- even on GPU, dense songs still pay for walking the full envelope before table-aware pruning
- the next planner correction should therefore derive cuts directly from the table-aware candidate rows instead of walking the full raw interval list first

## Current Phase 2b Status (GPU-Resident Exact Refinement)

Exact-mode post-GA refinement now runs its heavy compute path fully on GPU (Taichi). `HumanHitSim.RefineDevice=gpu` is the canonical setting; legacy `cpu` / `auto` values are normalized onto this same path:

- grouped-window event generation for alpha regimes (monotonic clamp) runs on GPU
- per-row fever timeline signatures (head mask bits + body counts) run on GPU
- per-candidate scoring over those signatures runs on GPU
- active-row detection and regime collapse (merge adjacent intervals when signatures match) runs on GPU
- capped regime selection (`RefineMaxRegimes` + `RefineRegimeSelection`) runs on GPU
- best regime/candidate selection runs on GPU
- final best `timestamps` and `fg_great_candidate_timestamps` are materialized on GPU and downloaded once

What is still on CPU (by design, low volume):

- quantizing chart timestamps to integer ms uses a CPU float32-first snap quantizer (avoids 1ms underflow near integer ms)
  - the optimizer uploads `ts_ms` to GPU once per refinement call
- exact alpha envelope buffers are bounded by:
  - `GPU_HITSIM_MAX_ALPHAS` (max raw regimes, default `4096`)
  - `GPU_HITSIM_MAX_SPAN` (max span width in ms, default `4096`)
- collecting the candidate pool + score inputs
- deriving the final `regime_id` string and writing metadata (uses the downloaded compact signature rows)

This keeps the refinement stage GPU-friendly and avoids the previous `for regime in regimes: generate event_ms -> searchsorted -> score` CPU loop.
It also preserves the “shared GA, then vary deterministic HitSim regimes” architecture goal while keeping CPU↔GPU transfers bounded.

## Current Phase 3 Status (Regime Fanout + Merged Candidate Surface)

The architecture has now moved past "pick one refined winner and discard the rest."

What is implemented:

- `refine_human_hit_sim_after_ga()` now emits:
  - local per-regime winners
  - merged cross-regime candidates
  - counts for both surfaces
- exact GPU refinement now exposes the selected regime winners instead of only the single best regime
- native in-flight decode now merges the refined regime winners back into the GA candidate pool instead of appending only one post-refine winner
- when refinement changes the winning loadout, native decode now also updates the returned `best_gear` / `best_minis` to match the selected refined winner
- merged refine candidates are funneled back through the same bounded FG candidate selector, so the refined regime surface is not silently dropped by the later GPU-selected-payload fast path

What this means architecturally:

- the runtime shape is now closer to:
  - `song -> GA candidate pool -> regime fanout -> merged candidate surface`
- local-per-regime winners are explicit rather than implicit
- the merged surface can now feed downstream FG / gem work without requiring a full outer repeat duplication

What is still not implemented:

- a fully table-first regime generator that avoids walking the raw alpha interval list before collapse
- true full-population warm continuation from the original scout GA internals

## Current Phase 4 Status (Selective Regime-Local Continuation)

The first selective-continuation slice is now implemented for `ApplyTo=ALL`, but it is intentionally bounded and opt-in.

What is implemented:

- the native in-flight path now runs a deterministic `candidate x regime x gem-allocation` pass over the merged post-refine candidate surface before any continuation
- that matrix stage reuses one shared GA candidate surface, solves the best gem allocation for every retained candidate under every retained regime, and merges the resulting surface back into the final top pool
- the active GPU-native runtime now executes that matrix as one shared GPU batch: candidate stats/population are uploaded once, retained regimes are precomputed into GPU song slots, per-regime results are stored in the GPU multi-run payload buffer, and the matrix is downloaded once at the end
- continuation is driven by the scout/refine surface, not by outer repeat duplication
- only regimes whose local winner differs from the shared selected winner are considered divergent enough to continue
- each continued regime rebuilds its deterministic timestamps from stored regime metadata
- the continuation pass seeds a prebuilt GA population from:
  - the local regime winner
  - the merged cross-regime candidate surface
  - the retained GA candidates from the scout pass
- the GPU-native in-flight orchestrator can now resubmit bounded regime-local GA jobs before FG / persistence

What is still missing:

- a true full-population warm continuation from the original scout GA internals
- richer divergence criteria than “different local winner identity than the shared selected winner”

So Phase 4 now exists as a practical hybrid continuation path, but not yet as the final fully generalized architecture.

## Current Behavior

### 1. `SongRepeats` is still a queue-level GA seed axis outside the deterministic `ApplyTo=ALL` path

The current repeat axis is created in `gear_optimizer/app.py::_prepare_tasks`.

- By default, each queued song is duplicated `SongRepeats` times.
- When deterministic HumanHitSim `ApplyTo=ALL` refinement is enabled, `_prepare_tasks()` now collapses outer repeats back to a single song attempt and moves that work into the inner regime scheduler.
- Each repeat gets its own `repeat_ctx`.
- `repeat_ctx` currently carries:
  - `repeat_index`
  - `repeat_total`
  - `ga_seed`

Relevant code:

- `gear_optimizer/app.py`

This means repeats are still modeled as separate full song tasks for the legacy non-deterministic paths, but the deterministic `ApplyTo=ALL` architecture now treats the HitSim fanout as inner dimensions instead.

### 2. HumanHitSim can change the objective seen by GA

`gear_optimizer/pipeline/song_processor.py` applies HumanHitSim before GA runs.

- If `HumanHitSim.ApplyTo=FG`, simulated timestamps are prepared for FG logic.
- If `HumanHitSim.ApplyTo=ALL`, HumanHitSim overwrites `song_data["timestamps"]`.

Relevant code:

- `gear_optimizer/pipeline/song_processor.py`
- `gear_optimizer/solver/hit_simulation.py::apply_human_hit_sim`

This distinction is the main architectural constraint.

### 3. FG-only HitSim is already deferred in the native in-flight path

The native in-flight path already postpones expensive FG-only HitSim work until FG prep.

Relevant code:

- `gear_optimizer/solver/native_inflight_stages.py`

This is important because it shows the codebase already supports the idea that some HitSim dimensions are downstream-only and should not force a separate GA run.

### 4. The codebase already has a limited "shared GA, then vary HitSim" mechanism

There is already a post-GA refinement path for `HumanHitSim.ApplyTo=ALL`.

- It keeps the final GA winner fixed.
- It tries multiple deterministic seeds after GA.
- It reevaluates the fixed winning stats over those timing variants.
- It keeps the best variant without allowing score regression.

Relevant code:

- `gear_optimizer/solver/hit_simulation.py::refine_human_hit_sim_after_ga`
- `gear_optimizer/pipeline/song_processor.py`
- `gear_optimizer/solver/native_inflight_stages.py`

This is a useful precedent, but it is intentionally bounded and heuristic. It does not prove that one GA winner is optimal for every timing regime.

### 5. The current implementation still acknowledges bounded regime scans can miss the best variant

The test suite explicitly encodes the idea that limited post-GA trial counts can miss a better timing variant.

Relevant tests:

- `tests/test_hit_simulation.py`

That matters because any future "shared GA across dimensions" design must decide whether it is:

- exact, or
- a strong heuristic with bounded search

## Current Problem Statement

The present repeat model is doing multiple jobs at once:

1. GA restart diversity
2. HumanHitSim timing diversity
3. DB-seeded variance recovery
4. Boundary-flip discovery

That is workable, but structurally messy.

When HumanHitSim is being used to search for boundary-sensitive wins, `SongRepeats` becomes a blunt instrument:

- we rerun full GA even when only a narrow timing regime changed
- we do not expose cross-regime comparisons inside one song attempt
- we cannot cleanly distinguish "GA needed another search trajectory" from "same loadout, different timing regime won"

## Proposed Future Model

The proposed replacement is not "random HitSim with better seeds."

It is:

1. Build or reuse an analytical `161 x 161` FT/FF timing table.
2. Determine where fever-boundary flips can occur.
3. Compute the positive or negative millisecond perturbations required to cause each flip.
4. Collapse the continuous timing space into a finite set of boundary regimes.
5. Generate deterministic HitSim realizations from those regimes instead of from luck.

Under that model, a "HitSim dimension" is no longer a seed.
It is a deterministic boundary regime with a known semantic meaning.

## Why This Fits Better Than Random Repeats

With deterministic regimes:

- the search space becomes finite and explainable
- the optimizer can compare regimes directly inside one song context
- repeats become a meaningful scheduler axis rather than a luck proxy
- caches and persistence can reason about regime identity explicitly

This is much closer to a proper product surface than the current "run the song again and maybe get lucky" behavior.

## Architecture Assessment

## Case A: `HumanHitSim.ApplyTo=FG`

This case fits very well.

Why:

- GA is still optimizing against the normal chart timestamps.
- The timing regime only affects FG-side timeline behavior.
- The code already defers FG-only HitSim until FG prep in native in-flight mode.

Implication:

- one GA run can be reused across many deterministic HitSim boundary dimensions
- downstream FG work can fan out across those dimensions
- gem optimization can run per dimension without forcing a new outer GA repeat

This is the cleanest target for the proposed architecture.

### Recommended shape for `FG`

For one song attempt:

1. Run GA once.
2. Keep a bounded candidate pool, not just one winner.
3. Enumerate deterministic FG timing regimes.
4. Evaluate FG and per-regime gem allocation across those regimes.
5. Merge and rank winners across all regimes.

In this mode, "multiple HitSim dimensions under one repeat" is a natural fit.

## Case B: `HumanHitSim.ApplyTo=ALL`

This case fits, but with an important limitation:

- HitSim changes the timestamps that base scoring and GA see.
- That means the objective itself can change per timing regime.

So a single shared GA is not automatically exact across all deterministic regimes.

### What shared GA means in `ALL`

Under `ApplyTo=ALL`, shared GA should be treated as:

- a candidate generator
- a witness-pool generator
- a warm-start mechanism

It should not be assumed to be a proof that the best loadout under regime A is also the best loadout under regime B.

### Recommended shape for `ALL`

The stronger architecture is:

1. Run GA once or a small number of times to build a strong candidate pool.
2. Enumerate deterministic timing regimes.
3. Reevaluate that pool under each regime.
4. Re-run gem optimization per regime.
5. If some regimes diverge materially, optionally continue GA inside only those regimes.

This is still much better than blind `SongRepeats`, but it is not the same as "one GA is enough."

## What Changes Once Regimes Are Deterministic

The biggest conceptual shift is this:

- Today: repeats discover timing wins by luck.
- Future: regimes are explicit search states.

That means the planner can reason about:

- which regime flipped which boundary
- whether two regimes are equivalent
- whether a regime only affects FG or affects full GA scoring
- whether a cached result is still valid for a regime

This makes it realistic to collapse the current repeat axis into a multi-dimensional in-task scheduler.

## Scheduler Direction

The likely target scheduler is not:

- one queue item per random repeat

It is closer to:

- one outer song attempt
- one GA candidate pool
- one set of deterministic timing dimensions
- one merged result surface

Conceptually:

1. CPU/GPU build or fetch baseline analytical timing state.
2. GA produces candidate pool.
3. Deterministic boundary regimes are expanded.
4. Candidate-by-regime evaluation runs in parallel.
5. Results are merged into one leaderboard.

## Cache Implications

This plan fits the existing cache direction, but cache identity will need to become more explicit.

### Timeline caches already understand timing context

Existing timeline/GPU precompute keys already include HumanHitSim metadata such as:

- seed
- apply mode
- distribution
- great mode

Relevant code:

- `gear_optimizer/solver/taichi_gem/api/timeline.py`
- `gear_optimizer/solver/scoring/stats_scoring.py::_song_cache_key`

That is a good sign: the codebase already treats timing context as part of the timeline identity.

### Gem-solver caching is still coarser

The batch gem-evaluation cache key is primarily stats-based.

Relevant code:

- `gear_optimizer/core/utils.py::stats_signature`
- `gear_optimizer/solver/scoring/genome_evaluation.py`

That is fine today, but if the same stats are evaluated under multiple explicit timing regimes in the same process, the system must ensure that:

- any regime-sensitive result is keyed by regime identity, not just by stats

Otherwise a deterministic multi-regime evaluator could accidentally reuse a result from the wrong timing context.

## Persistence Implications

The repo currently has a strong DB policy:

- HumanHitSim parameters must not change the song DB namespace.

That policy should still hold.

What should change is the detail payload:

- the winning result should be able to say which boundary regime or dimension produced it
- regime metadata should be stored as descriptive context, not as a separate song key

This keeps one song namespace while still exposing why a regime won.

## Product Framing

This proposal improves the product model in two ways.

### 1. Cross-context evaluation becomes first-class

Instead of comparing independent repeated runs after the fact, the optimizer can compare regimes as sibling outcomes inside one song attempt.

### 2. Parallelism becomes more intentional

The current repeat model parallelizes by duplicating full song tasks.
The proposed model can parallelize at finer granularity:

- candidate pool generation
- regime expansion
- candidate-by-regime gem optimization
- FG evaluation

That is likely a better fit for the existing in-flight GPU-owner design than repeated whole-task queue inflation.

## Regime x Gem-Allocation Layer

One important extension to this architecture is to evaluate multiple deterministic HitSim regimes against multiple gem allocations inside the same shared candidate space.

Conceptually:

1. Build or fetch the deterministic regime set.
2. For one loadout candidate, materialize the regime-specific fever timeline signature once.
3. Score many gem allocations against that regime-specific timeline.
4. Repeat for the other regimes.
5. Merge the resulting regime-by-allocation surface.

This is now implemented in the GPU-native in-flight path.

What exists now:

- the current refinement already does `candidate x regime` rescoring with `fast_calculate_score`
- it now also preserves both local-per-regime winners and merged cross-regime winners
- the native in-flight path now also runs the full retained `candidate x regime x gem-allocation` matrix through the registry gem solver before continuation / FG

### Why this layer is attractive

- it makes cross-context gem evaluation first-class
- it is much cheaper than rerunning full GA for every regime
- it lets the optimizer compare whether a gem allocation is regime-fragile or regime-robust
- it fits the proposed "shared candidate pool -> regime fanout -> merged result" model very naturally

### Where it fits best

- `FG`: extremely clean; shared GA plus per-regime gem evaluation is the intended shape
- `ALL`: still useful, but it only improves evaluation of the shared pool; it does not recover a missing loadout identity by itself

### Pros

- strong reuse of candidate generation work
- direct visibility into score benefit per regime
- good compatibility with a merged top-`1` or merged top-`51` product surface
- `fast_calculate_score` is cheap once the regime-specific timeline signature is known

### Cons

- the matrix can become large if candidate count, regime count, and gem-allocation count all grow together
- cache identity must include regime identity
- if the shared candidate pool misses the right loadout, no amount of per-regime gem rescoring can recover it
- under `ApplyTo=ALL`, this is still an evaluation layer, not a proof that shared GA is exact

### Reliability / Speed / Overhead

If this layer is built on top of table-derived regimes and up-front regime pruning, it should be:

- more reliable than random repeats
- more reliable than the current post-hoc duplicate collapse
- much faster than cold full-GA-per-regime search

The main overhead comes from:

- analytical preprocessing to derive the regime set
- regime-aware cache keys
- the size of the `candidate x regime x gem-allocation` score surface

So the intended role of this layer is:

- a fast shared evaluation layer
- a pruning layer
- and a strong precursor to selective per-regime continuation under `ApplyTo=ALL`

## Recommended Phased Plan

## Phase 1: Formalize the concept of a HitSim dimension

Define a dimension as an explicit regime object, not a seed.

A dimension should minimally encode:

- whether it is `FG`-only or `ALL`
- which boundary family it targets
- the timing perturbation interval or construction rule
- a stable regime identity for caching and logging

## Phase 2: Build deterministic regime generation on top of analytical timing state

Use the future analytical `161 x 161` timing table to derive regimes that:

- guarantee a specific boundary flip, or
- guarantee no flip within a region

At this stage, random HitSim can still exist as fallback or validation, but it should stop being the primary search path.

### Phase 2a: Correct the current exact-mode implementation toward the real architecture

The current `exact` mode should be evolved in the following order:

1. Make the FT/FF analytical table generate the regime intervals directly.
2. Treat the analytical table as the source of regime families, not only as a dedupe signature domain.
3. Prune non-flipping / equivalent regions before event-stream generation.
4. Persist explicit regime metadata:
   - interval bounds
   - stable regime identity
   - boundary family
   - whether the regime is `FG`-only or `ALL`
5. Keep the current deterministic refinement path as a fallback / transitional mode until the new regime generator is benchmarked.

This correction matters because the architecture is strongest when the regime set is:

- table-derived
- semantically meaningful
- sparse before scoring work begins
- stable enough for caching and logging

## Phase 3: Reframe repeats as inner dimensions

Replace or demote outer `SongRepeats` for the deterministic regime path.

Instead of:

- `repeat -> full GA -> FG`

move toward:

- `song -> GA candidate pool -> regime fanout -> merged result`

### Phase 3a: Add a regime-by-gem evaluation stage

Once dimensions are explicit, add a dedicated layer that evaluates:

- candidate loadout
- deterministic regime
- gem allocation

inside one shared search context.

That stage should:

- build regime-specific timeline signatures once
- reuse `fast_calculate_score` across many gem allocations
- expose both local-per-regime winners and merged cross-regime winners
- feed a selective continuation policy for `ApplyTo=ALL`

## Phase 4: Add selective per-regime continuation for `ApplyTo=ALL`

Do not force a full per-regime GA immediately.

Instead:

- reevaluate the shared candidate pool first
- identify regimes with meaningful divergence
- continue GA only where needed

This keeps most of the benefit without assuming false equivalence across regimes.

Implemented status:

- this is now partially implemented as an opt-in bounded continuation path
- the current version seeds regime-local GPU-native GA rescans from the post-matrix merged candidate surface
- it does not yet do true full-population warm continuation from the original live GA internals

## Hybrid Risks for `ApplyTo=ALL`

The "shared scout GA + selective per-regime continuation" hybrid is still the best practical direction, but it has real failure modes.

### 1. Shared scouting can miss the target regime winner

If the target regime's best loadout is not present in the shared scout pool, downstream reranking cannot recover it.

This is the same core reason pure shared-GA reuse fails under `ApplyTo=ALL`: the target regime can have a genuinely different winner.

### 2. Winner presence is not the same as winner promotion

A shared-plus-local pool can contain the target regime's true best loadout without promoting it to final rank `#1`.

In other words:

- the winner may be in the candidate pool
- the hybrid may still choose a different top result after reranking

This matters because "top-1 recovered somewhere" is weaker than "top-1 actually selected."

### 3. Shared scouting can reduce target-local recall at fixed pool size

When the hybrid merges a shared pool with a target-local pool under a fixed retained budget, anchor-regime candidates can displace target-local candidates.

That means the hybrid can:

- improve best-score diversity
- yet still recover less of the target regime's exact top set than local-only search at the same target-local GA budget

### 4. Proxy hybrid results are not the same as true warm-start continuation

The current benchmarked hybrid is a proxy:

- shared scout pool
- plus separately discovered target-local pools
- then merged and reranked

That is not yet the same as a real implementation that:

- seeds the target regime GA from the shared scout population
- continues mutation/selection inside the target regime

So current hybrid measurements are decision-relevant, but they are not the final word on what a true continuation path could do.

### 5. Cache isolation is mandatory

Any multi-dimension hybrid path must partition gem-solver and timeline-sensitive caches by regime identity.

Current gem-solver cache identity is still primarily stats-based:

- `gear_optimizer/core/utils.py::stats_signature`
- `gear_optimizer/solver/scoring/genome_evaluation.py`

That is too coarse for same-process multi-regime evaluation unless regime identity is added or caches are explicitly reset between regimes.

## Experimental Findings

The codebase now has a benchmark harness for this question:

- `tools/bench/bench_hitsim_shared_pool_recall.py`

The results below are not proofs, but they are strong enough to guide architecture decisions.

### 1. Pure shared reuse failed on `ApplyTo=ALL`

On `Aether (Hard)`, a 4-dimension experiment with 4 GA seeds per dimension showed:

- same-seed control recall around `48-50 / 51`
- cross-seed top-1 match `0 / 12`
- cross-seed top-51 recall mean `0.0441`

Artifact:

- `artifacts/bench/hitsim_shared_pool_recall_aether_hard_d10_r4.json`

Interpretation:

- the different HitSim dimensions did not converge to the same effective top set
- a pure shared-GA architecture is not trustworthy for `ApplyTo=ALL`

### 2. A deeper pair run showed the divergence can be extreme

On the same song, a deeper `22222 <-> 33333` pair run with 8 GA seeds per dimension showed:

- same-seed control `48-50 / 51`
- cross-seed overlap `0 / 51` both directions

Artifact:

- `artifacts/bench/hitsim_shared_pool_recall_aether_hard_22222_33333_d20_r8.json`

Interpretation:

- some regime pairs are not "mostly the same set with different ordering"
- they can be effectively disjoint at the retained top-51 level

### 3. Hybrid proxy was better for candidate discovery than for exact ranking

The benchmark harness now also supports a hybrid proxy:

- one anchor regime provides the shared scout pool
- target regimes add `0 / 1 / 2 / 4 / ...` local GA runs
- the merged pool is reranked under the target regime

Artifact:

- `artifacts/bench/hitsim_hybrid_aether_hard_22222_33333_d20_r8_v2.json`

For the hard `22222 -> 33333` pair:

- at `50%` of full GA-run cost (`8 shared + 0 local`), hybrid found the target top-1 `0 / 1` times
- at `56.25%`, `62.5%`, and `75%` cost, hybrid still found the target top-1 `0 / 1` times
- at `100%` cost (`8 shared + 8 local`), hybrid found the target top-1 `1 / 1` times

However, even at that `100%` cost point:

- hybrid top-51 overlap was only `27 / 51`
- local-only target search at the same local budget recovered `50 / 51`

Interpretation:

- the shared scout can help inject strong candidates
- but shared-pool union alone is not enough to preserve exact target-regime ordering or top-set identity

### 4. Broader hybrid top-1 results were mixed

A 4-dimension anchor sweep on `Aether (Hard)` used HitSim seed `11111` as the shared anchor and measured only the 3 non-anchor targets.

Artifact:

- `artifacts/bench/hitsim_hybrid_aether_hard_4seed_anchor11111_d10_r4.json`

Observed top-1 results for the 3 non-anchor targets:

- at `25%` of full GA-run cost: `0 / 3`
- at `43.75%` cost: `0 / 3`
- at `62.5%` cost: `1 / 3`
- at `100%` cost: `1 / 3`

Local-only target search on the same run budgets did better for top-1:

- at `62.5%` cost: `2 / 3`
- at `100%` cost: `3 / 3`

But the hybrid still showed a useful secondary signal:

- at `62.5%` cost, it had the true winner somewhere in the reranked list for `2 / 3` targets
- at `100%` cost, it had the true winner somewhere in the reranked list for `3 / 3` targets, while promoting only `1 / 3` to final rank `#1`

Interpretation:

- the current proxy hybrid is better at "winner enters the pool" than at "winner is selected as final rank `#1`"
- a true warm-start continuation implementation may still outperform this proxy, but that has not yet been demonstrated

## Merged Leaderboard Implications

The product question may be narrower than "solve every dimension exactly."

If the final output is a merged leaderboard such as top `51` across dimensions, then there are two different optimization goals:

- recover the exact merged top `51`
- recover only the final merged top `1`

Those are not the same problem.

### 1. Exact merged top `51` is still the hard mode

Current experiments show that different `ApplyTo=ALL` dimensions can produce materially different winning sets.

That means:

- exact merged top `51` still requires broad dimension coverage
- hybrid pool sharing alone is not enough to guarantee exact merged-set recovery

### 2. Final merged top `1` is easier than exact merged top `51`

If the only thing that matters is the single best final winner after merging dimensions, hybrid becomes more attractive.

Why:

- the winner only needs to emerge from one dimension
- hybrid can still be useful even if it does not perfectly recover each dimension's local top set

### 3. Current data suggests hybrid can help for merged top `1`, but not safely in all cases

In the 4-dimension `Aether (Hard)` run:

- all 4 dimensions had different local top-1 winners
- the final merged global winner came from only one of those dimensions
- the current hybrid proxy recovered that merged global winner at about `62.5%` of full GA-run cost

Artifact:

- `artifacts/bench/hitsim_hybrid_aether_hard_4seed_anchor11111_d10_r4.json`

But in the harder `22222 <-> 33333` pair:

- the merged global winner was not recovered until full no-share cost

Artifact:

- `artifacts/bench/hitsim_hybrid_aether_hard_22222_33333_d20_r8_v2.json`

Interpretation:

- hybrid may be good enough for merged top-1 search on some songs
- hybrid is not yet trustworthy enough to assume early merged-top-1 recovery in general

### 3a. A score-only merged-top-1 benchmark looked better than exact per-dimension top-1

A later benchmark evaluated all 4 anchor choices against the same full reference and asked a narrower question:

- did hybrid recover the final merged global best score across dimensions?

Artifact:

- `artifacts/bench/hitsim_merged_top1_4anchors_aether_hard_d10_r4.json`

Observed result on `Aether (Hard)`:

- at `25%` of full GA-run cost, `1 / 4` anchors recovered the final merged global best score
- at `43.75%` of full GA-run cost, `4 / 4` anchors recovered the final merged global best score

Interpretation:

- if the product target is only the final merged winner by score, hybrid looks substantially more promising
- this is a stronger result than exact per-dimension top-1 recovery
- but it still does not prove that a small fixed dimension sample is always enough on other songs

### 3b. The harder pair still needed full cost even for merged top `1`

On the deeper `22222 <-> 33333` pair benchmark:

- hybrid did not recover the final merged global best score until `100%` of full GA-run cost

Artifact:

- `artifacts/bench/hitsim_hybrid_aether_hard_22222_33333_d20_r8_v2.json`

Interpretation:

- merged-top-1-by-score is easier than exact per-dimension top-1
- but there are still hard regime pairs where hybrid does not save budget

### 4. How many dimensions are needed?

Current evidence does not support a small fixed number such as:

- "one dimension is enough"
- "two dimensions are enough"
- "sample a few and stop"

What the current experiments show is:

- the merged winner lives in one dimension
- but we do not know which dimension in advance
- in the tested 4-dimension sample, each dimension had a different local winner

So the safe current stance is:

- you still need to touch every dimension you care about
- the optimization target is reducing search cost within each touched dimension, not skipping dimensions blindly

The main ways to eventually reduce the number of dimensions would be:

- analytical regime equivalence / clustering
- score upper bounds that can prune losing regimes early
- benchmarked evidence that some regime families never produce the merged winner

Until one of those exists, hybrid should be viewed as:

- per-dimension search reduction
- not dimension-count reduction

## Acceptance Criteria

The plan is successful when all of the following are true.

### Functional

- boundary-sensitive wins come from explicit deterministic regimes rather than from random luck
- the system can explain which regime produced a win
- FG-only regimes do not require separate outer GA repeats
- the product target is explicit about whether it wants:
  - exact merged top `51`
  - or only final merged top `1`

### Performance

- repeated full-song GA reruns are reduced for regime-only variation
- timeline precompute and analytical state are reused across regimes where valid
- candidate-by-regime evaluation can be parallelized without inflating the outer queue
- if the product target is merged top `1`, hybrid should be benchmarked on:
  - merged winner recovery rate
  - GA-budget ratio versus full no-share search

### Correctness

- `ApplyTo=FG` shared-GA reuse is exact or operationally equivalent
- `ApplyTo=ALL` shared-GA reuse is treated as a heuristic candidate-pool stage unless proven otherwise
- a hybrid `ApplyTo=ALL` path is accepted only if it is benchmarked on top-1 recovery, not just top-set overlap
- the FT/FF analytical table must be able to influence which regimes exist, not only dedupe them after the fact
- regime pruning should happen before most event/timeline work, not primarily after scoring-side duplicate detection
- each persisted winning result should be able to describe the regime interval and family that produced it
- if hybrid is used for top-1 search, the implementation must distinguish:
  - winner present in pool
  - winner promoted to final rank `#1`
- if the final product only cares about merged top `1`, correctness must be stated in terms of:
  - merged global winner recovered
  - not exact per-dimension top-set recovery
- caches are keyed strongly enough to prevent cross-regime contamination

## Non-Goals

This plan does not claim:

- one GA run is always sufficient for all `ApplyTo=ALL` timing regimes
- random HitSim should disappear immediately
- every deterministic regime must be fully enumerated on day one

The aim is to replace luck-driven search with regime-aware search, not to force a premature exact solver for every mode.

## Code Map

Relevant current code paths for this plan:

- Repeat task generation:
  - `gear_optimizer/app.py`
- Per-song HumanHitSim application:
  - `gear_optimizer/pipeline/song_processor.py`
  - `gear_optimizer/solver/hit_simulation.py`
- Post-GA `ApplyTo=ALL` refinement:
  - `gear_optimizer/solver/hit_simulation.py`
  - `gear_optimizer/solver/native_inflight_stages.py`
- FG-only deferred application:
  - `gear_optimizer/solver/native_inflight_stages.py`
- Timeline cache identity:
  - `gear_optimizer/solver/taichi_gem/api/timeline.py`
  - `gear_optimizer/solver/scoring/stats_scoring.py`
- Gem-evaluation cache identity:
  - `gear_optimizer/core/utils.py`
  - `gear_optimizer/solver/scoring/genome_evaluation.py`

## Bottom Line

The proposed future architecture is a good fit for the codebase.

It becomes a very strong architecture if the implementation keeps the following properties together:

- deterministic regimes are derived from the analytical FT/FF state itself
- non-changing regions are pruned before most scoring work
- regime identity is explicit enough for cache keys, logging, and persistence
- shared-space evaluation is widened to `candidate x regime x gem-allocation`, not just `candidate x regime`
- `ApplyTo=ALL` uses shared GA as a scout stage plus selective continuation where divergence remains real

The strongest version of it is:

- deterministic boundary regimes instead of random lucky seeds
- shared GA candidate generation
- per-regime downstream evaluation
- optional selective per-regime continuation only when `ApplyTo=ALL` truly changes the search landscape

In other words:

- for `FG`, this can become a clean canonical path
- for `ALL`, this should become a regime-aware layered search, not a blind assumption that one GA is universally optimal
- hybrid remains the right direction for `ALL`, but the currently benchmarked proxy is not yet reliable enough to guarantee top-1 recovery before full no-share cost
- if the real product target is merged top `1`, the next benchmark priority should be merged-winner recovery versus GA budget, not exact top-51 overlap
