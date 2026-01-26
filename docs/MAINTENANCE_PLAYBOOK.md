# Maintenance Playbook (Runtime + GPU Stack)

This document is a practical guide for making safe, performance-oriented changes to the optimizer runtime and GPU stack.

## Effective config + env precedence

### Config path resolution
- **Primary**: `METAFINDER_CONFIG_PATH` (when set and non-empty)
- **Fallback**: `config.ini`

Code: `gear_optimizer/core/config.py` (`get_config_path()`, `load_config()`).

### Debug-profile gating (profiling knobs)
`main.py` gates certain overhead-heavy env toggles behind DebugProfile:
- If DebugProfile is **off**, it will clear env vars like `PERF_TIMING`, `GPU_EXECUTOR_PROFILE`, `GPU_PROFILER`, etc.
- If DebugProfile is **on**, it sets `METAFINDER_DEBUG_PROFILE=1`.

`gear_optimizer/core/env_config.py` reads `DEBUG_PROFILE` / `METAFINDER_DEBUG_PROFILE` once and exposes a typed `ENV` singleton.

### ForceGreats radius defaults
- `FG_SEARCH_RADIUS` is treated as the **default** FG search radius (legacy env override).
- `IterationEngine.FG_SearchRadius` (config) is used as the per-run explicit radius when set.

Code: `gear_optimizer/core/env_config.py` (`ENV.fg_search_radius`), `gear_optimizer/core/constants.py` (`FG_SEARCH_RADIUS`), `gear_optimizer/core/config.py` (`read_fg_search_radius()`).

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
Write path: `gear_optimizer/data/database.py` (`save_loadouts_batch()`).

### GPU IPC request payloads
GPU executor request payloads are dicts keyed by request type.
Type reference (partial, extended as needed):
- `gear_optimizer/core/types.py` (`SolveGenomesParallelPayload`, `SolveGenomesFromRegistryPayload`, `SolveForceGreatsFinderPayload`)

Executor: `gear_optimizer/solver/gpu_executor.py`.

## Profiling checklist (GPU executor + kernels)

### 1) Confirm the run is allowed to profile
- Ensure DebugProfile is enabled (via config or env) so `main.py` doesn’t clear profiling env vars.

### 2) Executor-level utilization (queue + Python overhead)
- Enable executor profiling:
  - `GPU_EXECUTOR_PROFILE=1`
- Optional live periodic report:
  - Look for `[GpuExecutor][LIVE] ...` prints during runtime.

Interpreting output:
- `wait=` is time spent blocked waiting for work.
- `exec=` is time spent executing requests on the GPU owner thread (includes some host-side overhead).
- `pack=` is time spent preparing/coalescing batches inside the executor (helps spot CPU packing bottlenecks).

### 3) Kernel-level + transfer-level timing (GPU profiler)
- Enable:
  - `GPU_PROFILER=1` (or `PERF_TIMING=1` when DebugProfile is on)

This reports:
- kernel seconds
- upload/download seconds and bytes
- genomes evaluated
- estimated GPU utilization vs wall time

Code: `gear_optimizer/solver/gpu_profiler.py`.

### 4) Taichi kernel profiler (deep kernel breakdown)
- Enable (DebugProfile recommended):
  - `TAICHI_KERNEL_PROFILER=1`
  - `TAICHI_KERNEL_PROFILER_PRINT=1`

Note: this can add overhead; use for targeted investigations.

### 5) In-flight stage profiling (CPU prep/decode/FG overlap)
- Enable:
  - `INFLIGHT_STAGE_PROFILE=1`
  - Optional periodic emit: `INFLIGHT_STAGE_PROFILE_EMIT_SEC=...`

Stages are aggregated in:
- `gear_optimizer/solver/native_inflight_stages.py` (`_InFlightStageProfiler`)

## Safe FG Stage-1 tuning (no quality reduction)
These knobs **do not change the search space or scoring math**; they only affect kernel launch sizing and banding:

- `FG_SMALL_WORK_SINGLE_BAND=1` (default): when workloads are small, force a single Stage‑1 band to reduce launch overhead.
- `FG_SMALL_WORK_MAX_WORK_ITEMS` (default `20000`): max `n_genomes * n_ftff` eligible for single‑band.
- `FG_SMALL_WORK_MAX_CFG_LEN` (default `4096`): max cfg window length eligible for single‑band.

You can also sweep the existing knobs for occupancy:
- `FG_TARGET_THREADS_PER_KERNEL`: increases/decreases Stage‑1 `cfg_chunk` target (larger = fewer bands).
- `FG_STAGE1_CFG_TILE`: configs per thread inside Stage‑1 flat kernels.
- `FG_STAGE1_NO_ATOMICS=1`: force the sequential Stage‑1 kernel (no atomics) on Vulkan for benchmarking; may be slower but avoids atomic contention.

## Recent modularization points (where to edit)
- **Env access**: `gear_optimizer/core/env_config.py` (single source of truth for env knobs)
- **Result payload contract**: `gear_optimizer/core/result_payloads.py`
- **App helpers**:
  - `gear_optimizer/app_async_db.py` (async DB saves off the critical path)
  - `gear_optimizer/app_stop_control.py` (stop/signal control)
- **In-flight stages**: `gear_optimizer/solver/native_inflight_stages.py` (decode + FG prep + stage profiling)
