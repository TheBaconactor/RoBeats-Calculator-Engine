# Maintenance Playbook (Runtime + GPU Stack)

This document is a practical guide for making safe, performance-oriented changes to the optimizer runtime and GPU stack.

## Effective config + env precedence

### Config path resolution
- **Primary**: `METAFINDER_CONFIG_PATH` (when set and non-empty)
- **Fallback**: `config.ini`

Code: `gear_optimizer/core/config.py` (`get_config_path()`, `load_config()`).

### Debug-profile gating (profiling knobs)
`main.py` gates certain overhead-heavy env toggles behind DebugProfile:
- If DebugProfile is **off**, it clears profiling flags such as `PERF_TIMING`,
  `GPU_SERVICE_PROFILE`, and `TAICHI_KERNEL_PROFILER`.
- If DebugProfile is **on**, it sets `METAFINDER_DEBUG_PROFILE=1`.

`gear_optimizer/core/env_config.py` reads `DEBUG_PROFILE` / `METAFINDER_DEBUG_PROFILE` once and exposes a typed `ENV` singleton.

### Search semantics are not tuning knobs

- Production always runs the exact request-local Base search and native exact FG scorer.
- The exact Base result is certified independently of queue depth, worker count, and cache state.
- The Base-to-FG funnel refills and retains up to 51 highest-ranked effective loadouts from the
  exact-scored witness pool, stopping early only when the joined states are exhausted.
- There are no production search-effort, randomization, FG radius, or alternate-scorer knobs.

Code: `gear_optimizer/solver/exact_base_search.py`,
`gear_optimizer/solver/native_fg_owner.py`.

## Key runtime data shapes (boundary contracts)

### `calc_song`
Canonical per-song payload passed through CPU prep → scoring → GPU timeline:
- `calc_song["metadata"]`: header dict (Song Name, Primary/Secondary Color, Difficulty, etc.)
- `calc_song["song_data"]`: arrays (timestamps, note_types, …)

Type reference: `gear_optimizer/core/types.py` (`CalcSong`, `CalcSongData`).

### Per-song result payload (pipeline → app/post-processor)
Core keys (success and error payloads share the same identity/error contract):
- `song`, `_queue_key`, `_queue_label`
- `_error`, `_error_type`, `_trace` (when returning failures instead of raising)

Type reference: `gear_optimizer/core/types.py` (`SongResultPayload`).
Builder: `gear_optimizer/core/result_payloads.py` (`build_error_payload()`).

### DB persistence entries
Batch inserts are built from lists of dict entries:
- `score`, `fg_score`, `gear`, `minis`, `details`, `force`

Type reference: `gear_optimizer/core/types.py` (`PersistenceEntry`).
Write path: `gear_optimizer/data/database/persistence.py` (`save_loadouts_batch()`).

### GPU IPC request payloads
GPU executor request payloads are dicts keyed by request type.
Type reference:
- `gear_optimizer/solver/gpu_executor_types.py` (`GpuRequestType`: `LOAD_REF_ARRAYS`, `EXACT_BASE_SEARCH`, `SHUTDOWN`)
- payload bodies are `JsonDict` values on `GpuRequest.payload`

`EXACT_BASE_SEARCH` owns one fused exact Base plus native FG turn and returns an
`ExactBaseOwnerResult`. Its Base surface and FG score map must cover the same
typed seven-component candidate keys.

Executor: `gear_optimizer/solver/gpu_executor.py`.

## Profiling checklist (GPU executor + kernels)

### 1) Confirm the run is allowed to profile
- Ensure DebugProfile is enabled (via config or env) so `main.py` doesn’t clear profiling env vars.

### 2) Executor-level utilization (queue + Python overhead)
- Enable the live executor report:
  - `GPU_EXECUTOR_LIVE=1`
  - Optional cadence: `GPU_EXECUTOR_LIVE_INTERVAL_SEC=1.0`

Interpreting output:
- `wait=` is time spent blocked waiting for work.
- `exec=` is time spent executing requests on the GPU owner thread (includes some host-side overhead).
- `pack=` is time spent preparing/coalescing request batches inside the executor.

### 3) End-to-end request latency
- Enable:
  - `GPU_SERVICE_PROFILE=1`
  - `GPU_SERVICE_PROFILE_PRINT=1`

This reports:
- submit-to-response count, total, mean, percentiles, and maximum by request type;
- the fused `EXACT_BASE_SEARCH` latency, which includes exact Base plus native FG owner work.

Code: `gear_optimizer/solver/gpu_service.py`.

### 4) Taichi kernel profiler (deep kernel breakdown)
- Enable (DebugProfile recommended):
  - `TAICHI_KERNEL_PROFILER=1`
  - `TAICHI_KERNEL_PROFILER_PRINT=1`

Note: this can add overhead; use for targeted investigations.

### 5) In-flight stage profiling (CPU prep/Base/decode/FG overlap)
- Enable:
  - `INFLIGHT_STAGE_PROFILE=1`
  - Optional output: `INFLIGHT_STAGE_PROFILE_PATH=...`

Stages are aggregated in:
- `gear_optimizer/solver/native_inflight_pipeline.py` (`InFlightStageProfiler`)

## Production Exact Base and Native FG Path

Per-song CPU preparation builds request-local item domains, loads the exact
timeline and Base song-context artifacts, and loads the candidate-independent
native FG scoring bundle. The single GPU owner then:

1. partitions the request into only its reachable Mini-PP/PP-response components;
2. performs the two Base semiring joins for each component;
3. certifies Base top-1 with admissible song-specific bounds;
4. refills, materializes, and ranks up to 51 effective Base loadouts, or exhausts the joined states;
   and
5. scores every retained loadout through the native response-frontier FG implementation.

One-component requests keep the hot path exercised by the default-catalog `00 (Hard)` benchmark.
Nonuniform Mini PP totals and allocations where a PP gem beats overflow are exact; every official
or custom request adds only its reachable components and does not require a catalog frontier build.

Primary owners:

- Base domains/context/search: `gear_optimizer/solver/exact_base_*.py`
- Semiring kernels: `gear_optimizer/solver/taichi_gem/kernels/exact_base_semiring.py`
- Native FG owner handoff: `gear_optimizer/solver/native_fg_owner.py`
- FG response-frontier runtime: `gear_optimizer/solver/taichi_gem/force_greats/response_frontier.py`
- Fused scheduling: `gear_optimizer/solver/native_inflight_orchestrator.py`

Do not benchmark a Base-only substitute when assessing production throughput;
native FG completion is part of the owner-turn contract.

The Base-context startup prebuilder owns bounded spawn generations outside the submit loop. Each
generation handles at most eight tasks per worker, keeps at most two pending tasks per worker,
drains all futures, and exits its executor before the next generation begins. Do not move pool
recycling into submission: that caused a Windows queue-manager deadlock. Do not replace the bounded
generations with a never-ending pool either; native/NumPy allocator commit ratchets upward while
those workers remain alive.

## Repeatable Performance Measurements

Measure the canonical exact Base search on a real catalog and song with:

```powershell
python tools/bench/bench_exact_base_production.py --song 00 --difficulty Hard --warmups 1 --runs 3
```

The tool reports cold timeline, catalog-domain, and song-context preparation
separately from warm exact Base wall time. Use warm measurements for per-song
search latency, and retain the reported domain/candidate cardinalities when
comparing changes.

Exercise the full exact Base-to-native-FG production pipeline with the bounded
smoke profile:

```powershell
$env:METAFINDER_CONFIG_PATH = "configs/smoke/config_smoke_queue1_fast.ini"
python main.py
```

For multi-song throughput work, use a fixed song queue and compare end-to-end
completion time plus in-flight stage profiles. Queue depth and host worker count
may change utilization, but they must not change the certified Base result or
native FG result.

## Recent modularization points (where to edit)
- **Env access**: `gear_optimizer/core/env_config.py` (single source of truth for env knobs)
- **Result payload contract**: `gear_optimizer/core/result_payloads.py`
- **App helpers**:
  - `gear_optimizer/app_async_db.py` (async DB saves off the critical path)
  - `gear_optimizer/app_stop_control.py` (stop/signal control)
- **In-flight orchestration**: `gear_optimizer/solver/native_inflight_orchestrator.py`
- **Exact Base queue/decode**: `gear_optimizer/solver/native_inflight_pipeline_base.py`,
  `gear_optimizer/solver/exact_base_pipeline_decode.py`
- **Native FG preparation/materialization**: `gear_optimizer/solver/native_inflight_pipeline_fg.py`

## Repo guardrails (avoid removed-path regressions)

### Guardrail tests
- Removed-symbol gate + import-surface gate live in: `tests/test_repo_guardrails.py`
- Included in the dev quality check: `tools/dev/quality_check.ps1`

### Deprecation/removal checklist (when adding a new GPU path)
1. Rewire production call sites first (scoring + executor submit paths). Avoid landing a "new path" that isn't used.
2. Update maintained tooling (`tools/bench/`, `tools/verify/`) to use the new surface, not the old helpers.
3. Add/adjust parity tests that cover the new implementation (CPU reference vs GPU, plus at least one integration).
4. Delete the superseded implementation (requests/types/kernels/fields), and extend the guardrail forbidden-symbol list if needed.
5. Run at least:
   - `python -m ruff check .`
   - `python -m pytest -m "not gpu" tests/`
   - `python -m pytest -m gpu tests/` (on a Vulkan-capable machine)
