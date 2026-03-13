# GPU-Resident GA->FG Plan

This document captures a follow-on architecture idea for the native in-flight pipeline: keep the GA->FG handoff GPU-resident for the same song/search space, smooth GPU utilization, and retire obsolete fallback paths after cutover.

The goal is not "GA is fast" in isolation. The goal is a single integrated GA+FG product path with fewer host/device boundaries, fewer slot handoffs, and less queue starvation.

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

### Phase 3: Shrink the FG host boundary

- Download only selected top-K packed rows.
- Persist lean raw payloads by default.
- Move heavyweight stats/detail materialization out of the critical GPU path where possible.
- Eliminate Python-side apply over candidates that will not be persisted or surfaced.

### Phase 4: Delete non-canonical legacy paths

Delete only after parity, performance, and operational telemetry prove the resident path is stable.

Candidate deletions or demotions:

- Full GA run-payload download path used only for FG candidate selection in native in-flight mode.
- Host-built `genome_stats_arr` when same-slot candidate-table staging is available.
- Separate in-process breakpoint request path where fused request parity is already proven.
- Multi-request FG reset->solve->download path for the native in-process production path.
- Clearly marked unused GPU-native GA operator scaffolding that is not part of the final canonical implementation.

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
- GA->FG fused work executes as one owner-thread request per chunk in the common case.
- FG host downloads are limited to selected top-K persistence payloads.
- GPU idle gaps and slot-block oscillation are measurably reduced in throughput benchmarks.
- FG completion/quality is preserved; no "GA-only throughput win" is accepted.

## Non-Goals

This plan should reduce a real class of stalls and spikes, but it will not make the GPU utilization graph perfectly flat.

Expected remaining variance:

- workload-dependent kernel sizes
- queue competition across songs
- final host persistence/materialization
- backend/runtime variance

The objective is to remove avoidable pipeline bubbles, not to eliminate all runtime variability.

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
