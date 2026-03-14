# GPU-Resident GA->FG Plan

This document captures a follow-on architecture idea for the native in-flight pipeline: keep the GA->FG handoff GPU-resident for the same song/search space, smooth GPU utilization, and retire obsolete fallback paths after cutover.

The goal is not "GA is fast" in isolation. The goal is a single integrated GA+FG product path with fewer host/device boundaries, fewer slot handoffs, and less queue starvation.

Important scope note:

- A resident GA->FG handoff is the right canonical architecture.
- Residency alone is not expected to produce a HitSim-sized speedup.
- The large remaining FG wins require both:
  - fewer host/device boundaries
  - less actual FG work

## Goal

For one song in the native in-flight path:

1. GPU-native GA evaluates genomes in one `song_slot`.
2. GA leaves the timeline grid, candidate table, and best-per-run data resident in that same slot.
3. The scheduler keeps the slot reserved until FG finishes.
4. FG stages genome base stats from the GA candidate table with a GPU->GPU copy.
5. Breakpoint compute, FG solve, and top-K selection run on the GPU owner thread in one fused request whenever possible.
6. Only the final lean persistence payload crosses back to the CPU.

## Why This Exists

The codebase already has most of the pieces required for a resident handoff:

- Native in-flight scheduling is designed to keep the GPU continuously busy:
  - `gear_optimizer/solver/native_inflight_orchestrator.py`
- GA packs a compact GA->FG candidate table into a per-song slot:
  - `gear_optimizer/solver/genetic.py`
  - `gear_optimizer/solver/taichi_gem/api/ga_operations.py`
- FG can stage base stats directly from that candidate table without a host upload:
  - `gear_optimizer/solver/taichi_gem/api/ga_operations.py`
- FG global-best accumulation is already GPU-resident and indexed by `song_slot`:
  - `gear_optimizer/solver/taichi_gem/force_greats/fields.py`
- A fused owner-thread GA+FG breakpoint+solve request already exists:
  - `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`
  - `gear_optimizer/solver/gpu_executor.py`

So this is not a new subsystem. It is a proposal to make the resident path the canonical path and then delete the branches we no longer need.

## Current Sources Of GPU Stall / Spike Behavior

These are the specific problems this plan is meant to eliminate or reduce.

### 1. Request-boundary bubbles between GA and FG

FG still has paths where work is split across multiple executor requests:

- reset
- solve
- download

That creates queue gaps and allows unrelated GPU work to interleave between phases.

Primary files:

- `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`
- `gear_optimizer/solver/gpu_executor.py`

### 2. GA host downloads still exist in active paths

The code already minimizes downloads, but native GA still has host-side payload download paths used for result/candidate materialization.

Primary files:

- `gear_optimizer/solver/genetic.py`
- `gear_optimizer/solver/taichi_gem/api/parallel_solvers.py`
- `gear_optimizer/solver/taichi_gem/api/ga_operations.py`

### 3. FG still has a Python-side apply/materialization boundary

Even after GPU solve, FG results are still downloaded and applied to entries in Python for ranking, persistence, and debug payloads.

Primary files:

- `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`
- `gear_optimizer/helpers/song_helpers/force_greats/result_application.py`

### 4. Slot release / reacquire can break residency

If GA releases the `song_slot` before FG runs, another song can overwrite the candidate table or timeline state for that slot. FG then falls back to slower/non-resident behavior.

Primary files:

- `gear_optimizer/solver/native_inflight_orchestrator.py`
- `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`

### 5. Legacy and fallback branches increase synchronization risk

The code carries multiple fallback paths for:

- host-built `genome_stats_arr`
- separate breakpoint request submission
- multi-request FG execution
- full GA payload download

Some of these are still needed as safety valves. Some should become degraded-mode fallbacks only. Some should be deleted after cutover.

## Known Risks And Required Mitigations

These are the main reasons this plan could under-deliver if it is implemented too literally.

### 1. Residency alone may only produce a modest speedup

If the pipeline still evaluates roughly the same FG task volume, then keeping the handoff resident mostly removes transfer/orchestration overhead. That is good, but it is not enough to replicate the structural win we got from eliminating repeat-based HitSim luck.

Required mitigation:

- add GPU-side FG frontier reduction before solve
- dedupe near-equivalent candidates by FG signature bucket on GPU
- keep only bounded top-N / diverse representatives per signature bucket
- treat "less FG work" as a first-class goal alongside "less transfer"

### 2. Fused requests can reduce bubbles but still create bursty spikes

One giant fused FG request can flatten request boundaries while still producing long monopolizing GPU bursts. That is smoother at the queue layer but not actually smooth at the device layer.

Required mitigation:

- make FG execution tiled/resident rather than monolithic
- bound work by candidate tiles, FT/FF tiles, or section-group tiles
- keep global-best / top-K accumulators resident across tiles
- prefer many bounded resident chunks over one mega-request

### 3. Full slot holds can create head-of-line blocking

Holding an entire `song_slot` through FG completion is simple, but it can over-reserve memory/state and reduce fairness when FG jobs are long or irregular.

A permanently exclusive FG slot is not the target architecture. That would protect residency at the cost of cadence: the slot can sit idle when FG demand is low, then accumulate backlog and "backslot" the queue when FG demand spikes.

Required mitigation:

- separate "timeline residency" from "FG resident buffers" where possible
- pin only the assets FG still needs
- consider a dedicated FG resident arena or sub-allocation instead of a blunt full-slot hold
- do not rely on a permanently exclusive FG slot as the steady-state design
- prefer dynamic reserve/credit behavior over static slot ownership
- measure queue starvation and slot-block time before treating slot hold as a default good

### 4. Python-side grouping/materialization can cap the upside

If Python still performs most of the signature grouping, candidate filtering, and result application, the pipeline remains partially host-bound even when the solver itself is resident.

Required mitigation:

- move FG signature construction and bucket reduction onto GPU
- move retained top-K / keep-mask selection onto GPU
- download only compact selected winner rows
- materialize full details only for persisted or surfaced winners

### 5. Too much FG work may still be structurally redundant

Even with a GPU-resident handoff, the pipeline can still waste substantial compute if it fully evaluates many candidates that collapse to the same effective FG structure or have no realistic chance to survive top-K.

Common waste patterns:

- near-equivalent candidates that map to the same FG signature class
- repeated breakpoint/scaffolding construction for equivalent structure families
- oversized fused batches that do valid work but monopolize the device too long
- host-side grouping/application on rows that will never be persisted or surfaced
- resident state that pins more memory or slot ownership than the FG stage actually needs

Required mitigation:

- reduce candidates on GPU before exact solve by signature bucket
- reuse FG scaffolding where the `(chart, regime, signature bucket)` structure is equivalent
- keep FG execution tiled and time-bounded rather than monolithic
- perform GPU-side keep-mask/top-K reduction so CPU only sees winners
- pin only the resident assets that materially reduce recomputation

### 6. Longer-lived GPU state raises correctness and isolation risk

The more state we keep resident across GA->FG boundaries, the more expensive silent ownership bugs become.

Required mitigation:

- key resident buffers by explicit ownership tuple such as `(session_id, song_slot, phase_id)`
- fail loudly in debug/parity mode on ownership mismatch
- log degraded-mode causes explicitly
- count residency misses, slot loss, and host rebuilds as first-class telemetry

## Target Canonical Path

This should become the production-default path for native in-process GPU mode.

### Canonical flow

1. `native_inflight_orchestrator` acquires a `song_slot` for the song.
2. GPU-native GA runs in that slot and writes:
   - timeline grid
   - GA candidate table
   - best-per-run payload
3. If FG is required, the scheduler keeps the same slot reserved through FG completion.
4. FG stages genome base stats from the candidate table using GPU->GPU copy.
5. FG breakpoint generation and solve execute in one fused owner-thread request.
6. GPU performs top-K selection/packing before any host download.
7. CPU receives only the lean selected payload required for persistence.

### Degraded mode

Only when residency cannot be preserved:

- slot lost
- unsupported backend/runtime mode
- debug/parity forcing a slower path
- strict fallback after fused-request failure

In degraded mode, host uploads/downloads are allowed. They should be clearly logged and counted, not silently treated as equivalent to the canonical path.

## Upgrade Plan

Implemented on the current FG branch:

- bounded signature-frontier reduction before exact solve
- winner-only FG result materialization with lean raw payload persistence
- breakpoint-group scaffolding reuse for identical chart/regime + FT/FF + base-pair families
- max-FP breakpoint-matrix reuse for identical chart/regime + FT/FF + base-pair families
- explicit work-budget tiling for FG task batches and fused breakpoint payload batches
- held-slot GA candidate-table staging is now canonical in the live path; the old env gate is removed
- explicit FG resident-owner metadata now guards GA->FG candidate-table staging instead of relying on a loose held-slot boolean

### Phase 1: Canonicalize same-slot GA->FG residency

- Make "hold the GA slot through FG" the default whenever FG is pending and slot budget allows it.
- Treat slot release before FG as explicit degraded mode.
- Promote fused breakpoint+solve as the default in-process FG path.
- Add counters for:
  - resident handoff hit/miss
  - slot reacquire count
  - fused FG request count
  - degraded FG fallback count

### Phase 2: Remove host-side GA candidate selection from native in-flight

- Use the GPU candidate table as the canonical source for FG candidate staging.
- Stop relying on large GA run-payload downloads for FG candidate selection in the native in-flight path.
- Keep lean selected payload download only for persistence/materialization boundaries.

### Phase 2B: Add GPU-side FG frontier reduction

- Build FG signature buckets directly from the resident GA candidate table.
- Reduce candidates on GPU before FG solve:
  - top-N per signature bucket
  - bounded diverse frontier
  - regime-aware or center-aware representatives when applicable
- Treat this phase as workload reduction, not just a transport optimization.

Current branch status:

- GPU-side FG frontier reduction is implemented in the production path.
- The hot path now batches FG frontier selection per song/group set, then downloads the reduced frontier once.
- The first naive version regressed throughput because it downloaded one frontier result per group; that per-group boundary is no longer used in production.
- The canonical path now primes compact FG group metadata during FG prep and reuses it in `gpu_dispatch`, so the hot path no longer has to rebuild all group keys/signatures/proxy scores for GA candidates.
- Decode-time priming was tested and reverted from the canonical path because it moved CPU work into a more serial stage and regressed controlled throughput.
- The remaining future opportunity is moving signature bucket construction fully off the host, not rebuilding the same compact metadata inside the current FG hot path.

### Phase 2C: Remove redundant FG solve volume

- identify near-equivalent FG candidates by signature class before exact solve
- avoid full FG solve for rows that cannot survive the current bounded frontier
- reuse breakpoint/scaffolding structures for equivalent `(chart, regime, signature bucket)` families where exactness is preserved
- treat this phase as compute elimination, not just queue smoothing

Current branch status:

- breakpoint-group scaffolding reuse is implemented
- max-FP matrix reuse is implemented
- explicit resident-owner metadata is implemented on the live in-flight path
- production exact-solve reuse currently comes from the max-FP matrix cache plus breakpoint-group cache
- further reuse beyond those caches is a watchlist item, not a remaining blocker for the canonical FG path

### Phase 3: Shrink the FG host boundary

- Download only selected top-K packed rows.
- Persist lean raw payloads by default.
- Move heavyweight stats/detail materialization out of the critical GPU path where possible.
- Eliminate Python-side apply over candidates that will not be persisted or surfaced.

### Phase 3B: Replace mega-fused FG bursts with tiled resident FG execution

- Keep the resident candidate/signature state across multiple FG tiles.
- Run bounded work tiles under scheduler credit rather than one giant fused request.
- Preserve the resident global-best / top-K accumulators across tiles.
- Optimize for lower jitter and better queue fairness, not just fewer request boundaries.

Current branch status:

- explicit work-budget tiling is implemented for FG task batches and fused breakpoint payload batches
- scheduler-credit orchestration is still handled by the in-flight scheduler, not a dedicated FG tile controller

### Phase 3C: Make winner-only materialization the default

- build GPU-side keep-mask and top-K reduction before any host application
- download only compact retained winner rows and persistence payloads
- remove Python-side apply/materialization from non-winning candidates in the hot path

Current branch status:

- retained-winner-only host materialization is implemented
- GPU frontier reduction is active in the canonical path
- the canonical path now primes compact FG grouping metadata before `gpu_dispatch`
- the remaining host-side piece is full signature bucket construction from retained entries before the GPU frontier stage

### Phase 4: Delete non-canonical legacy paths

Delete only after parity, performance, and operational telemetry prove the resident path is stable.

Candidate deletions or demotions:

- Full GA run-payload download path used only for FG candidate selection in native in-flight mode.
- Host-built `genome_stats_arr` when same-slot candidate-table staging is available.
- Separate in-process breakpoint request path where fused request parity is already proven.
- Multi-request FG reset->solve->download path for the native in-process production path.
- Clearly marked unused GPU-native GA operator scaffolding that is not part of the final canonical implementation.

### Phase 4B: Replace blunt slot holds with explicit FG-resident ownership

- Hold only the minimum resident assets required across the GA->FG boundary.
- Move toward explicit FG resident ownership rather than "entire slot is pinned until FG ends."
- Keep full-slot hold only as a degraded or compatibility mode if finer-grained residency is not yet stable.
- Avoid a permanently exclusive FG slot; use a bounded FG resident arena plus dynamic scheduler credits so FG cannot silently accumulate and break queue rhythm.

Current branch status:

- explicit FG resident-owner metadata is implemented on the live in-flight path
- held-slot candidate-table staging now requires owner/slot identity to match before the resident fast path is used
- a dedicated FG resident arena is not required for the current production path and remains a future optimization, not a correctness gap

## Legacy-Removal Policy

Do not delete code based on assumption alone.

A path is eligible for removal only when all of the following are true:

- It is not part of the native in-process production path.
- There is test coverage for the replacement path.
- There is benchmark evidence that the replacement path is better or at least neutral on quality.
- There is no remaining caller that depends on the old path for supported runtime modes.

If a path still exists only for debug, parity, or emergency fallback, it should be clearly labeled as such.

## Acceptance Criteria

The proposal is successful when all of the following are true in native in-process GPU mode:

- No GA->FG host upload occurs in the resident same-slot path.
- No slot release/reacquire occurs for songs that require FG.
- No full GA payload download is used for FG candidate selection.
- GPU-side FG frontier reduction is active in the canonical path.
- redundant FG solve volume is measurably reduced, not just rescheduled
- GA->FG fused work executes as one owner-thread request per chunk in the common case.
- FG chunks are bounded; no unbounded mega-request is required for the canonical path.
- FG host downloads are limited to selected top-K persistence payloads.
- GPU idle gaps and slot-block oscillation are measurably reduced in throughput benchmarks.
- Python-side grouping/materialization is not in the hot path for non-retained candidates.
- Residency ownership mismatches and degraded-mode causes are explicitly counted and logged.
- FG completion/quality is preserved; no "GA-only throughput win" is accepted.

## Non-Goals

This plan should reduce a real class of stalls and spikes, but it will not make the GPU utilization graph perfectly flat.

Expected remaining variance:

- workload-dependent kernel sizes
- queue competition across songs
- final host persistence/materialization
- backend/runtime variance

The objective is to remove avoidable pipeline bubbles, not to eliminate all runtime variability.

Also not a goal:

- claiming a HitSim-scale speedup from residency alone

If the FG plan is successful, the likely result is:

- lower jitter
- less burstiness
- better queue fairness
- moderate to strong FG-heavy speedups
- resident FG behavior that does not depend on a permanently exclusive slot

The largest remaining gains will come from reducing FG task volume, not just making the existing FG path more resident.

## Throughput-First Optimization Order

If the KPI is completed songs/hour with FG fully finished, the recommended optimization order is:

1. GPU-side FG frontier reduction
2. redundant FG solve elimination / scaffolding reuse
3. GPU-side keep-mask and winner-only materialization
4. tiled resident FG execution
5. narrower FG residency ownership

This order is intentional:

- reducing actual FG work should beat transport-only optimization
- reducing host work should beat over-fusing larger bursts
- smoothing residency should support throughput, not replace workload reduction

## Deferred Risks To Watch With Tests And Reports

The items below do not need immediate architecture work, but they should not be ignored. For now, the plan is to add detection and reporting first, then only implement deeper fixes if the reports show a real problem.

### 1. VRAM pressure and spill behavior

- add a benchmark/report that records peak resident usage, arena pressure, and any spill/degraded events
- treat unexpected overcommit or spill as a visible regression, not a silent behavior change

### 2. Determinism and parity drift

- add seeded parity tests and benchmark reports for top-1 and FG top-1 retention
- watch for backend drift across supported GPU/runtime environments before adding more aggressive reuse

### 3. Cache key or reuse invalidation bugs

- add targeted tests around cache/reuse identity for breakpoint or signature-family reuse
- require reports that show cache hit/miss counts and any reuse-disabled fallbacks

### 4. Tile cancellation and stale work

- add scheduler tests/reports that show whether FG tiles continue running after they are no longer useful
- only implement deeper preemption logic if the reports show meaningful wasted work

### 5. GA admission vs FG backlog imbalance

- add throughput reports that track FG queue age, slot-block time, and GA submit throttling behavior
- only add more complex admission control if those reports show cadence instability

### 6. Benchmark blind spots by workload class

- keep separate benchmark/report slices for FG-heavy songs, lighter songs, timing-sensitive songs, and mixed queues
- do not rely on one average songs/hour number to validate the full architecture

### 7. Production fail-closed expectations

- add a report or benchmark gate that records `degraded_mode_count` and resident-handoff misses
- production throughput runs should surface any non-canonical execution explicitly, even if we do not yet delete every compatibility branch

### 8. Top-K surface quality loss

- add tests/reports for retained-surface quality, not just final top-1 quality
- watch for regressions where frontier reduction preserves top-1 but degrades downstream FG surface quality

## Relevant Code Map

- Scheduler and slot ownership:
  - `gear_optimizer/solver/native_inflight_orchestrator.py`
- GA orchestration and candidate packing:
  - `gear_optimizer/solver/genetic.py`
- GPU executor and fused requests:
  - `gear_optimizer/solver/gpu_executor.py`
  - `gear_optimizer/solver/gpu_service.py`
- FG dispatch and host boundary:
  - `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`
  - `gear_optimizer/helpers/song_helpers/force_greats/result_application.py`
- GA GPU APIs:
  - `gear_optimizer/solver/taichi_gem/api/ga_operations.py`
  - `gear_optimizer/solver/taichi_gem/api/parallel_solvers.py`
- FG GPU APIs and state:
  - `gear_optimizer/solver/taichi_gem/force_greats/api.py`
  - `gear_optimizer/solver/taichi_gem/force_greats/fields.py`
