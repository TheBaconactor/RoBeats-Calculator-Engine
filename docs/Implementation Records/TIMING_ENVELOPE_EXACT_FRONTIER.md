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
- generalized that reuse from adjacent plateaus to trace-equivalent `d_ms` values anywhere later in the axis; if every reachable first-exit transition in the representative's DP trace is identical for another `d_ms`, the recursive frontier is identical by induction
- cached first-exit transition tuples across representative solves and certificate checks, keyed by `(activation_group, act_lo, act_hi, d_ms)`
- vectorized the song-wide exit-envelope context construction by rewriting the scalar carry recurrence as prefix maxima in carry-adjusted coordinates:
  - `lower(s,g) = max(CARRY_L, max(low(h) + P(h)) - P(g))`
  - `cap(s,g) = min(CARRY_U, max(min(CARRY_U, high(h)) + P(h)) - P(g))`
  - where `P` is cumulative clipped carry distance and `h` ranges over groups after activation `s` through `g`
- added exact fast paths for singleton frontier reduction, repeated all-normal terminal surfaces, monotone prefix stop detection, and repeated head-mask coefficient calculation
- added a terminal-fever transition shortcut: if even the earliest activation carry puts the fever cutoff after every remaining group's latest feasible event time, the first-exit enumerator returns the terminal exit directly
- short-circuited terminal recursive exits by materializing the known all-normal empty tail instead of recursing into `gcount`
- cached carry propagation results across the song payload build; the cache is exact because propagation depends only on `(start_group, lo, hi, target_group)`, not `d_ms`
- replaced per-cell Python grid materialization with dense `(unique_d_ms, unique_fill_count)` matrices and NumPy remapping back to the 161x161 grid
- precomputed all possible head-range masks for the first 100 notes so combining a future surface with a fever interval is four ORs instead of a per-note loop

Measured after the reductions:

- on `#include <signal.h> (Hard) by Kurokotei`, first-build `pair_builds` dropped from about `188.5s` to about `34.8s`
- repeated slots for the same song became frontier cache hits at about `0.003 ms`
- repeated-slot `precompute_timeline_gpu` dropped to about `0.4s`, dominated by field merge
- later process runs can load the exact packed payload from disk instead of rebuilding the frontier
- after vectorized first-exit enumeration, `%UnDeciphered-CryptoGraph in the Edifice% (Hard)` cold no-disk-cache `pair_builds` measured about `1.66s` for `18,998` exact pairs; total `precompute_timeline_gpu` measured about `4.29s`
- after certified plateau reuse, `Double Helix (Easy)` cold no-disk-cache solved `7,025` representative pairs and reused `6,660` certified plateau pairs out of `13,685`; `pair_builds` measured about `0.72s`
- after vectorized exit-envelope context construction and micro fast paths, cold direct payload builds using the real `Data/Gear/Stats.txt` FT/FF curves measured:
  - `Double Helix (Easy)`: about `0.68s`
  - `Double Helix (Normal)`: about `1.63s-1.64s`
  - `Double Helix (Hard)`: about `1.97s`
- after terminal-transition, dense-grid, and head-mask fast paths, cold direct payload builds measured:
  - `Double Helix (Easy)`: about `0.45s-0.52s`
  - `Double Helix (Normal)`: about `1.29s-1.35s`
  - `Double Helix (Hard)`: best observed about `1.50s-1.55s`, with noisy repeated-process runs up to about `2.47s`
  - `UnDeciphered-CryptoGraph in the Edifice (Hard)`: about `1.13s`
  - `#include signal.h (Hard)`: about `1.41s`

The trace-equivalence generalization keeps the same safety condition as adjacent plateau reuse, but removes the requirement that equivalent `d_ms` values be consecutive. This keeps `d_ms` as the physical fever-duration axis while treating boundary behavior as the reusable mathematical object.

## Unified CPU Prewarm Lookahead

Native in-flight scheduling now separates CPU host-side exact frontier construction from GPU field upload.

The scheduler uses one shared lookahead setting for expensive CPU-only future-song work:

- config: `IterationEngine.InFlight_CPUPrewarmLookahead`
- env override: `INFLIGHT_CPU_PREWARM_LOOKAHEAD`
- default: `5`

For prepared songs within that lookahead window, the scheduler may prewarm:

- FG baseline point work
- FG static prep, bounded by worker availability and legacy explicit caps

Exact symbolic timeline frontier construction moved out of live lookahead. It is now startup CPU work managed before Taichi/Vulkan initialization.

This does not reintroduce CPU production scoring. The CPU work is host payload construction for the GPU/Taichi product path; `precompute_timeline_gpu(...)` still owns field upload when a song is dispatched to GA or FG.

The older `InFlight_FGStaticPrepMaxInflight` / `INFLIGHT_FG_STATIC_PREP_MAX_INFLIGHT` control remains as a narrower override, but the default admission now comes from the unified CPU prewarm lookahead.

Verification after this scheduler refactor:

- `python -m py_compile gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/native_inflight_orchestrator.py gear_optimizer/solver/native_inflight_stages.py gear_optimizer/solver/native_inflight_types.py tests/test_native_inflight_continuous_scheduler.py`
- `python -m pytest -q tests/test_native_inflight_continuous_scheduler.py tests/test_timeline_frontier_reduction.py tests/test_gpu_timeline_frontier_exact_bnb.py tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py --tb=short` -> 45 passed

## Production Whole-Pool Frontier Cache

The exact frontier payload is now a production startup cache, not only a developer tool.

Runtime and tooling share one host-side API:

- `build_or_load_timeline_frontier_payload(calc_song, ref_arrays)`
- `timeline_frontier_payload_cache_info(calc_song, ref_arrays)`

That API owns:

- song timing signature construction
- Stats lookup-axis signatures
- exact frontier payload construction
- memory-cache lookup
- disk-cache lookup/write
- cache source reporting (`memory`, `disk`, or `built`)

During optimizer startup, after the real Stats lookup arrays and song queue are available, `CpuWorkManager` runs exact-frontier cache construction before Taichi/Vulkan init:

- queued songs are submitted first
- the rest of `Data/Easy`, `Data/Normal`, and `Data/Hard` follows when scope is `pool`
- already cached payloads are identified by cache key/path and skipped without loading `.npz`
- missing payloads are built once and written to `bin/timeline_frontier_cache`
- live GA/FG timeline upload only loads/uploads the ready payload
- native in-flight no longer starts live timeline frontier prewarm jobs
- startup logging reports `[Startup][CPU]` cache build and `[Startup][GPU]` Taichi/Vulkan init

Production config:

```ini
TimelineFrontierCachePrebuild = true
TimelineFrontierCachePrebuildScope = pool
TimelineFrontierCachePrebuildWorkers = 0
TimelineFrontierCachePrebuildMaxSongs = 0
TimelineFrontierCachePrebuildExecutor = process
```

Environment overrides:

- `TIMELINE_FRONTIER_CACHE_PREBUILD`
- `TIMELINE_FRONTIER_CACHE_PREBUILD_SCOPE`
- `TIMELINE_FRONTIER_CACHE_PREBUILD_WORKERS`
- `TIMELINE_FRONTIER_CACHE_PREBUILD_MAX_SONGS`
- `TIMELINE_FRONTIER_CACHE_PREBUILD_EXECUTOR`

Additional startup-build hardening:

- startup prebuild uses `ProcessPoolExecutor` by default (`TimelineFrontierCachePrebuildExecutor=process`) so CPU-heavy exact frontier construction can use real multi-core parallelism
- prebuild now applies the same deterministic timing-envelope metadata as runtime before cache-key checks/builds, so startup artifacts are reusable by live queue songs
- cache key no longer includes unrelated ref-table signatures (PP/CM/FM/etc.); frontier keys are now tied to song timing plus FT/FF axes only
- stale `*.tmp.npz` cache artifacts are removed at startup before prebuild begins

The maintained helper remains available for manual backfills and focused verification, but it wraps the same production build function:

- `python tools/dev/prebuild_timeline_frontiers.py`

The helper walks `Data/Easy`, `Data/Normal`, and `Data/Hard` by default, parses each chart through the same `get_base_calc_song(...)` path as runtime, loads the same Stats lookup arrays as TeamBuff replay, and calls the shared production prebuild function. This means generated `.npz` files under `bin/timeline_frontier_cache` are directly reusable by later GA/FG timeline upload.

Disk-cache footprint fix (post-production rollout):

- root cause: startup prebuild serialized full payload tensors keyed by runtime `GPU_SONG_SLOTS` and full `MAX_TIMELINE_FRONTIER_SURFACES` capacity, not only the single source slot/prefix actually used by runtime upload
- effect: with aggressive auto slot sizing, each `.npz` became hundreds of MB and whole-pool prebuild created extreme disk pressure
- fix:
  - payload builder now materializes slot-agnostic cache payloads at one source slot
  - disk writer stores only source-slot arrays and only `frontier_pool_used` prefix rows
  - disk writer uses compressed `.npz` to avoid zero-filled capacity bloat
  - cache version bumped to `exact-frontier-v4` so stale inflated payloads are ignored
- runtime behavior remains exact and unchanged: upload still remaps cached source slot `0` into any active GPU song slot

Example:

```powershell
python tools/dev/prebuild_timeline_frontiers.py --workers 4
```

Targeted examples:

```powershell
python tools/dev/prebuild_timeline_frontiers.py --difficulty Hard --workers 4
python tools/dev/prebuild_timeline_frontiers.py --difficulty Easy --limit 10 --workers 1
```

Timeline upload also stopped using the old slot-merge pattern:

- old: `field.to_numpy()` full field download -> patch one slot -> `field.from_numpy()` full upload
- new: slot-prefix upload kernels update only the active song slot

Measured on a real Easy chart with an already-built payload:

- disk cache skip pass: about `0.5 ms` total per already-cached song in the prebuilder
- warmed `frontier_field_upload`: about `2.3 ms` for `1.7 MB` of active-slot payload
- first upload in a fresh process is higher because it includes Taichi kernel compilation

Verification:

- `python -m py_compile gear_optimizer/app.py gear_optimizer/solver/cpu_work_manager.py gear_optimizer/solver/timeline_frontier_cache_prebuild.py gear_optimizer/solver/taichi_gem/api/timeline.py tools/dev/prebuild_timeline_frontiers.py`
- `python -m ruff check gear_optimizer/app.py gear_optimizer/solver/cpu_work_manager.py gear_optimizer/solver/timeline_frontier_cache_prebuild.py gear_optimizer/solver/taichi_gem/api/timeline.py tools/dev/prebuild_timeline_frontiers.py`
- temp-cache `CpuWorkManager.run_startup(...)` smoke with `TimelineFrontierCachePrebuildScope=queue`, `Workers=0 (auto/all cores)`, `MaxSongs=1` -> passed
- temp-cache manual first pass: `python tools/dev/prebuild_timeline_frontiers.py --difficulty Easy --limit 1 --workers 1` -> `built`, about `463 ms` timeline
- temp-cache manual second pass: same command -> `disk`, `0.0 ms` timeline build/load and about `0.5 ms` total song check
- `python -m pytest -q tests/test_native_inflight_continuous_scheduler.py tests/test_timeline_frontier_reduction.py tests/test_gpu_timeline_frontier_exact_bnb.py tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py --tb=short` -> 45 passed

## Startup Manifest Fast-Hit (Warm Cache)

Warm startup still had deterministic host work that does not affect correctness:

- parse song file into `calc_song`
- apply timing-envelope metadata/streams
- then discover that exact frontier payload already exists on disk

For large warm pools this repeated parse path costs CPU time even though no frontier build is needed.

Implemented:

- added a persistent startup manifest under `bin/timeline_frontier_cache/manifest_v1.json`
- manifest key includes:
  - frontier cache version
  - timing-envelope mode
  - FT/FF ref-axis signatures
  - absolute song path
  - song file `mtime_ns` and `size`
- startup prebuild now performs a fast manifest pass first:
  - manifest hit + existing cache file => skip worker parse/build entirely
  - manifest miss => retain existing worker path (still exact, still skip-safe)
- prebuild then writes successful worker results back into the manifest for future runs

Safety:

- exactness is unchanged; this is startup scheduling only
- stale manifest entries self-heal because key includes file identity and cache version
- worker path remains authoritative for misses and version transitions

Measured with queue scope over 80 songs (thread executor, same process):

- cold run: `44,045.97 ms` (`built=80`)
- warm run with manifest: `5.48 ms` (`disk=80`)
- warm run after deleting manifest only: `85.76 ms` (`disk=80`)

So manifest fast-hit removed most warm startup overhead that was previously spent on deterministic parse/envelope checks.
