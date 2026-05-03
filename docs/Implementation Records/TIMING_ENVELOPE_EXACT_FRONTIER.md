# Timing Envelope Exact Frontier

- Date: 2026-05-03
- Status: Implemented

## Context

The timeline kernel now treats fever timing as a symbolic frontier problem, not a selected timeline problem.
For a fixed song and a fixed `(fill_count, d_ms)` cell, the production goal is to keep every non-dominated feasible
fever surface and discard the raw timing path.

The retired 4-variant ceiling path (`hi_max`, `hi_min`, `lo_max`, `lo_min`) is gone. The legacy ceiling-envelope
dedupe knob is also retired.

## Decision

Introduce `gear_optimizer/solver/timeline_exact_frontier.py` as the exact frontier builder and packer.

The core surfaced data types are:

- `TimelineExactSignature`
- `TimelineFrontierPack`
- `TimelineFrontierGridPayload`

The builder now:

- derives all feasible symbolic surfaces for a song/cell
- reduces them with structural dominance pruning
- keeps the retained surfaces in a flat packed pool
- emits canonical per-cell metadata plus frontier count and offset

The GPU upload path now:

- builds or reuses the packed frontier payload for the active song and reference signature
- merges only the active `song_slot` into the live Taichi fields so other slots remain intact
- uploads canonical cell stats, frontier count/offset, packed frontier pools, signatures, gap, and activation counts

Runtime consumers now:

- read `grid_frontier_count`
- iterate the full retained frontier with `read_timeline_frontier_variant(...)`
- treat an empty retained frontier as a bug rather than silently falling back

Compatibility removal pass:

- removed `_upload_timeline_grid` and the old slot-0 upload kernels
- removed the `SongTimelineGrid` fallback from fixed scoring and parallel solvers
- removed the canonical-grid fallback branch from the exact BnB scorer
- made the GPU-facing API require a `calc_song` dict with `metadata` and `song_data`

## Frontier Model

The symbolic surface is the score-relevant object:

```text
S = (M_head, F_body, N_body, A, p, C)
```

The exact frontier is the non-dominated set of reachable surfaces:

```text
ND({S(pi) : pi in feasible paths})
```

The packed frontier is keyed by the song timing signature and the `(fill_count, d_ms)` cell.
The in-memory payload cache is slot-aware because the backing arrays are slot-shaped.

## Reduction

Dominance is structural, not score-based. A surface can be removed when another surface is at least as good on the
retained symbolic dimensions:

- head mask superset
- body fever count greater or equal
- body normal count less or equal
- compatible activation state
- no worse reachable continuation
- no worse carry permissiveness

`reduce_timeline_frontier(...)` removes duplicates and dominated surfaces, then returns the retained set in a stable
order. The packed frontier builder uses that reducer before the payload is materialized.

## Runtime Behavior

Base scoring and exact BnB both consume the same packed frontier.

The important runtime pieces are:

- `grid_frontier_count` and `grid_frontier_offset` describe the packed pool for each cell
- `read_timeline_frontier_variant(...)` reads one retained surface at a time
- `kernels_scoring.py` and `api/fixed_scoring.py` iterate the whole frontier instead of a fixed 4-way guess
- `compute_timeline_grid_kernel(...)` no longer emits legacy four-variant frontier arrays

The slot-preserving upload fix matters here: precomputing slot 1 must not clobber slot 0, so the host merge only updates
the active slot in each Taichi field.

## Performance

This is heavier than the retired 4-variant ceiling path at precompute time, but it is much more reusable at score time.

Expected behavior:

- precompute is slower per unique song and cell
- repeated GA scoring is cleaner because all loadouts share the same cached frontier
- frontier memory remains bounded by `MAX_TIMELINE_FRONTIER_SURFACES`
- realistic songs should usually keep the retained frontier small

## Verification

- `python -m py_compile gear_optimizer/solver/timeline_exact_frontier.py gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/taichi_gem/api/fixed_scoring.py gear_optimizer/solver/taichi_gem/fields.py gear_optimizer/solver/taichi_gem/kernels/kernels_helpers.py gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py gear_optimizer/solver/taichi_gem/kernels/kernels_timeline.py gear_optimizer/solver/taichi_gem/kernels_metal.py gear_optimizer/solver/taichi_gem/kernels/__init__.py tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py tests/test_gpu_timeline_frontier_exact_bnb.py tests/test_timeline_frontier_reduction.py`
- `python -m pytest -q tests/test_timeline_frontier_reduction.py --tb=short` -> 2 passed
- `python -m pytest -m gpu -q tests/test_parity_smoke.py::test_gem_solver_cpu_gpu_exact_parity_smoke tests/test_gpu_integration.py tests/test_gpu_timeline_frontier_exact_bnb.py tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py --tb=short` -> 7 passed

## Phase Timing Investigation

A live optimizer run with profile-event instrumentation confirmed the long request window is dominated by exact frontier construction, not the slot merge or upload path.

Observed timings on `#include <signal.h> (Hard) by Kurokotei`:

- `timeline_frontier_phase / pair_builds`: about `188,484.9 ms`
- `timeline_frontier_phase / grid_fill`: about `306.4 ms`
- `timeline_precompute_phase / frontier_field_merge`: about `664.1 ms`
- `ga_gpu_setup_phase / precompute_timeline_gpu`: about `189,506.2 ms`
- `ga_gpu_setup_phase / restore_song_gpu_state`: about `189,667.8 ms`

Observed frontier shape for that run:

- `unique_fill_counts=129`
- `unique_d_ms=161`
- `pair_count=20769`
- `pair_surface_total=20769`
- `pair_surface_max=1`
- `frontier_pool_used=20769`
- `frontier_cells=25921`
- `frontier_variants=25921`

Interpretation:

- the expensive part is the exact per-pair builder
- the packed frontier merge is sub-second
- the run completed normally, so the stall was performance cost rather than a deadlock

Follow-up lossless reductions:

- hoisted song-invariant grouped timing context and carry-propagation jump tables out of the per-pair builder
- reused the same cached packed frontier payload across song slots, with upload remapping from cached slot `0` into the active slot
- included FT/FF reference-axis signatures in the reusable frontier cache key
- shared duplicate packed frontier pool entries when different `(fill_count, d_ms)` pairs produce identical retained surfaces
- added a persistent exact frontier disk cache under `bin/timeline_frontier_cache` keyed by song timing, timing-envelope context, FT/FF axes, and cache version
- precomputed exit-envelope prefix thresholds per activation group and vectorized first-exit enumeration while preserving the scalar recurrence exactly
- added certified plateau reuse over sorted `d_ms` values for each `fill_count`; a later `d_ms` reuses a representative pack only when every recorded first-exit transition call returns the exact same exit tuple list

Measured after the reductions:

- on `#include <signal.h> (Hard) by Kurokotei`, first-build `pair_builds` dropped from about `188.5s` to about `34.8s`
- repeated slots for the same song became frontier cache hits at about `0.003 ms`
- repeated-slot `precompute_timeline_gpu` dropped to about `0.4s`, dominated by field merge
- later process runs can load the exact packed payload from disk instead of rebuilding the frontier
- after vectorized first-exit enumeration, `%UnDeciphered-CryptoGraph in the Edifice% (Hard)` cold no-disk-cache `pair_builds` measured about `1.66s` for `18,998` exact pairs; total `precompute_timeline_gpu` measured about `4.29s`
- after certified plateau reuse, `Double Helix (Easy)` cold no-disk-cache solved `7,025` representative pairs and reused `6,660` certified plateau pairs out of `13,685`; `pair_builds` measured about `0.72s`

## Unified CPU Prewarm Lookahead

Native in-flight scheduling now separates CPU host-side exact frontier construction from GPU field upload.

The scheduler uses one shared lookahead setting for expensive CPU-only future-song work:

- config: `IterationEngine.InFlight_CPUPrewarmLookahead`
- env override: `INFLIGHT_CPU_PREWARM_LOOKAHEAD`
- default: `5`

For prepared songs within that lookahead window, the scheduler may prewarm:

- exact symbolic timeline frontier payloads and the persistent payload cache
- FG baseline point work
- FG static prep, bounded by worker availability and legacy explicit caps

This does not reintroduce CPU production scoring. The CPU work is host payload construction for the GPU/Taichi product path; `precompute_timeline_gpu(...)` still owns field upload/merge when a song is dispatched to GA or FG.

The older `InFlight_FGStaticPrepMaxInflight` / `INFLIGHT_FG_STATIC_PREP_MAX_INFLIGHT` control remains as a narrower override, but the default admission now comes from the unified CPU prewarm lookahead.

Verification after this scheduler refactor:

- `python -m py_compile gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/native_inflight_orchestrator.py gear_optimizer/solver/native_inflight_stages.py gear_optimizer/solver/native_inflight_types.py tests/test_native_inflight_continuous_scheduler.py`
- `python -m pytest -q tests/test_native_inflight_continuous_scheduler.py tests/test_timeline_frontier_reduction.py tests/test_gpu_timeline_frontier_exact_bnb.py tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py --tb=short` -> 45 passed
