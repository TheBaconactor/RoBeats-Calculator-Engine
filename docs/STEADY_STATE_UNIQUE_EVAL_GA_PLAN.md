# Steady-State GA + Global Unique-Eval Plan

This document captures a follow-on GA architecture idea for the optimizer: replace repeated micro-run work with a single steady-state search per song, backed by a global unique-eval table that prevents exact duplicate scoring.

The goal is not "push more priors into initialization." The goal is:

- keep broad discovery pressure
- stop re-evaluating the same loadout families
- spend more GPU budget on genuinely new candidates
- converge faster without making alternative loadouts impossible to find

## Problem Statement

The current GPU-native GA path still pays for redundant search in a few ways:

- multiple short runs can rediscover the same genome families
- DB-seed and heuristic-heavy initialization can improve time-to-first-good-result but can also narrow coverage if overused
- partitioning the population into separate seeded/exploratory islands reduces collapse risk, but it also creates duplicate exploration work between islands
- the system has no single song-level "already exact-scored" memory inside the active GA search itself

This matters because recent investigations showed that some meaningful improvements were not deep-evolution discoveries. They appeared when an already-known loadout was revisited and re-evaluated cleanly.

That means the highest-value optimization is not necessarily "stronger priors." It is "less repeated work plus better admission of genuinely new candidates."

## Design Goals

- Preserve global search coverage.
- Avoid seed-heavy search collapse.
- Avoid duplicated work between islands/runs.
- Reuse exact evaluations safely.
- Keep GPU-native production flow as the default path.
- Make approximate versus exact scores explicit so cache reuse is correct.

## Non-Goals

- This is not a proposal to make DB seeds dominant.
- This is not a proposal to rely on permanently isolated islands.
- This is not a proposal to deduplicate approximate warm-start scores as if they were canonical.

## Current Architecture Pressure Points

Relevant current behavior:

- Multi-start GA is split across runs in `gear_optimizer/solver/genetic.py`.
- GPU-side initial populations already support heuristic copies and DB-seed injection.
- The solver already distinguishes warm-start versus cold-tail behavior for canonical winner selection.

That is good for throughput, but it still leaves three structural inefficiencies:

1. duplicate evaluation across runs
2. restart overhead after search state has already learned something useful
3. poor visibility into which mutation operators are actually creating new frontier candidates

## Proposed Architecture

### 1. Single steady-state search per song

Replace multiple short GA restarts with one continuous per-song search:

- keep one live population
- produce a small batch of children each cycle
- evaluate only the children that are actually new
- admit the strongest and/or most novel children
- evict stale or redundant tail members

This keeps useful search state alive instead of throwing it away every restart.

### 2. Global unique-eval table

Maintain a per-song unique-eval table keyed by the canonical loadout identity:

- song identity
- canonical loadout hash
- relevant fixed-context flags if they change scoring semantics

The table stores:

- exact canonical base score
- exact canonical best result row
- evaluation provenance
- optional novelty metadata

If a child matches a previously exact-scored loadout, the GA reuses the cached exact result instead of re-running full scoring.

This is the core duplicate-work reduction.

### 3. Exact-only reuse contract

The unique-eval table must not treat approximate warm-start results as canonical.

The safe contract is:

- `approx`: warm-start / hint-assisted / provisional score, usable for local ranking only
- `exact`: cold-tail or otherwise canonical score, reusable across the whole song search

Only `exact` entries may be inserted into the global reuse table.

This prevents the dedup layer from freezing in under-scored or non-canonical winners.

### 4. Novelty-gated admission

A child should not enter the active population just because it exists.

Admit a child if at least one is true:

- it improves the score frontier
- it is sufficiently novel relative to the active archive
- it fills an underrepresented structural bucket

Novelty can be approximated cheaply by:

- slot-wise Hamming distance on the 9-slot genome
- effective mini-signature difference
- coarse stat-signature bucket difference

This keeps coverage broad without needing multiple duplicate-prone island partitions.

### 5. Partial tail refresh instead of full restart

If the population stalls:

- keep the top archive
- reinitialize only the worst or most redundant tail slice
- bias refresh toward underexplored regions, not toward the current best

This gives fresh search pressure without discarding the useful frontier.

### 6. Adaptive operator credit

Track which mutation/crossover operators produce:

- unique candidates
- frontier-improving candidates
- novelty-bucket coverage

Increase budget for productive operators and reduce budget for dead ones.

This is safer than seed-heavy biasing because it adapts from observed song-local success instead of imposing a prior family.

## Why This Is Safer Than Better Starting Points

The main objection to stronger initialization is correct:

- it can make alternative loadouts harder to discover

This proposal avoids that trap by shifting the optimization target:

- not "start closer to the old winner"
- but "stop wasting evaluations on already-proven duplicates"

Coverage is preserved because random discovery is still allowed to enter the system. Duplicate evaluations are what get cut, not unexplored structures.

## Why This Is Safer Than More Islands

Heavy island partitioning can protect diversity, but it also duplicates work:

- multiple islands can spend budget discovering the same family independently
- migration timing becomes another tuning surface
- seed-heavy islands can still dominate if they win too early

The steady-state + unique-eval approach keeps one shared song-level memory, so diversity is enforced through admission and novelty policy rather than through partially isolated repeated searches.

## Suggested Data Model

Minimal per-song unique-eval record:

```text
UniqueEvalEntry
- loadout_hash
- score_mode: approx | exact
- base_score
- result_row
- ff_ft_signature
- discovered_gen
- last_seen_gen
- operator_tag
```

Minimal active-population record:

```text
ActiveGenome
- genome_ids
- cached_hash
- score
- novelty_bucket
- age
- exact_status
```

## GPU-Fit Considerations

The first implementation does not need a full device-resident hash table.

Pragmatic rollout:

1. keep the GA population and scoring on GPU
2. maintain the unique-eval table on the host side for decoded candidate identities
3. reuse exact results at the orchestration boundary
4. only move dedup structures onto GPU if host-side bookkeeping becomes the bottleneck

This keeps the architecture change smaller while still cutting most redundant exact evaluations.

## Rollout Plan

### Phase 1: Exact-reuse foundation

- add per-song unique-eval table
- tag evaluations as `approx` or `exact`
- reuse exact results only
- record duplicate-hit metrics

### Phase 2: Steady-state replacement for micro-runs

- replace multi-start restart loop with steady-state admission/eviction
- keep a bounded archive and bounded active population
- add partial tail refresh on stagnation

### Phase 3: Novelty and operator adaptation

- add novelty buckets
- add novelty-aware survivor quota
- add operator credit tracking and adaptive offspring mix

### Phase 4: Optional GPU-resident dedup support

- only if profiling shows host dedup bookkeeping is material

## Acceptance Criteria

This architecture is only a win if it improves all of the following together:

- fewer exact duplicate evaluations per song
- equal or better best-score discovery
- equal or better FG candidate coverage
- no increase in silent fallback or provenance ambiguity

The implementation should report at least:

- unique candidates evaluated
- duplicate candidates skipped
- approx-to-exact conversions
- novelty-admitted survivors
- operator hit rate

## Open Questions

- Is canonical reuse keyed only by `loadout_hash`, or do some runtime flags need to enter the key?
- How much host-side bookkeeping is acceptable before dedup itself becomes overhead?
- Should novelty buckets be based on structure, stats, or both?
- Should FG candidate extraction draw from the active population, the archive, or both?

## Summary

If the optimization target is "faster convergence without making non-seeded loadouts disappear," then the right lever is not heavier initialization bias.

The better architecture is:

- steady-state search instead of repeated micro-restarts
- one global per-song unique-eval memory
- exact-only score reuse
- novelty-gated admission
- partial tail refresh instead of full restart

That cuts duplicated work directly while keeping the search surface open.
