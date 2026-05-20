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
- FG search radius is hard-coded to `-1`, meaning full FT/FF allocation search.
- `FG_SEARCH_RADIUS` and `IterationEngine.FG_SearchRadius` are no longer production tuning knobs.

Code: `gear_optimizer/core/constants.py` (`FG_SEARCH_RADIUS`), `gear_optimizer/core/config.py` (`read_fg_search_radius()`).

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
- `gear_optimizer/core/types.py` (`SolveGenomesFromRegistryPayload`, `SolveForceGreatsFinderPayload`)

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

- Canonical policy implementation: `gear_optimizer/solver/gpu_tuning_policy.py`. Keep `genetic.py` and `force_greats/api.py` as thin callers so GA/FG tuning changes stay in one place.
- `FG_SMALL_WORK_SINGLE_BAND=1` (default): when workloads are small, force a single Stage‑1 band to reduce launch overhead.
- `FG_SMALL_WORK_MAX_WORK_ITEMS` (default `20000`): max `n_genomes * n_ftff` eligible for single‑band.
- `FG_SMALL_WORK_MAX_CFG_LEN` (default `4096`): max cfg window length eligible for single‑band.

You can also sweep the existing knobs for throughput:
- `FG_TARGET_THREADS_PER_KERNEL`: increases/decreases Stage‑1 `cfg_chunk` target (larger = fewer bands).

## Repeatable occupancy sweeps
Use the maintained sweep harness when you want archived apples-to-apples GA / FG knob comparisons:

- GA example:
  - `python tools/bench/bench_gpu_occupancy_matrix.py --mode ga --ga-taichi-block-dims 128,256 --ga-reduce-block-dims 128,256 --ga-batch-runs 0,1 --ga-materialize-modes none,update_global,results --ga-genomes 705 --ga-iters 6 --ga-kernel-profiler`
- FG example:
  - `python tools/bench/bench_gpu_occupancy_matrix.py --mode fg --fg-stage1-block-dims 64,128 --fg-target-threads 2000000,4000000,6000000 --fg-genomes 1024 --fg-ftff 128 --fg-tasks 16 --fg-kernel-profiler`

Underlying benches also support machine-readable output directly:

- `python tools/bench/bench_gpu_native_ga_eval.py --materialize-mode update_global --kernel-profiler --json`
- `python tools/bench/bench_gpu_native_ga_eval.py --materialize-mode results_update_runs --kernel-profiler --json`
- `python tools/bench/bench_fg_batch_throughput.py --mode direct --kernel-profiler --json`

When `--kernel-profiler` is enabled, the bench JSON now includes per-kernel
entries in `kernel_profiler_kernels` plus accounting fields
`kernel_profiler_accounted_total_sec`, `kernel_profiler_unaccounted_total_sec`,
and `kernel_profiler_accounted_pct`. Use those fields to distinguish
"GPU time is genuinely concentrated in these kernels" from "we are still
missing profiler attribution."

For the live steady-state GA path, prefer `--materialize-mode results_update_runs`.
That mode mirrors the shipped orchestration more closely by timing:

- `ga_evaluate_population(..., materialize_mode="none")`
- `ga_write_best_results_and_update_runs_best(...)`

## FG job coalescing (safe, owner-quantum bounded)
These knobs **do not change the search space or scoring math**; they only coalesce small FG batch requests in-process while preserving bounded owner turns:

- `FG_COALESCE_BREAKPOINTS_BATCH=1` (default): enable coalescing of FG breakpoint+solve batches across jobs (in-process only).
- `FG_COALESCE_BREAKPOINTS_MAX_PAYLOADS` (default `8`): max payloads per coalesced request.
- `FG_COALESCE_BREAKPOINTS_MAX_PAIRS` (default follows `FG_BREAKPOINTS_MAX_PAIRS_PER_REQUEST`, capped at `4096`): max FT/FF pair work per coalesced request.
- `FG_COALESCE_BREAKPOINTS_MAX_WAIT_MS` (default `8`): max wait time before flushing a coalesced batch.

## In-flight GA+FG throughput architecture (integrated)

For the GA+FG integrated scheduler updates (continuous GA burst control, FG slot partitioning,
adaptive FG submit burst, fused FG request policy, and reproducible A/B protocol), see:

- `docs/INFLIGHT_GA_FG_THROUGHPUT.md`

## Recent modularization points (where to edit)
- **Env access**: `gear_optimizer/core/env_config.py` (single source of truth for env knobs)
- **Result payload contract**: `gear_optimizer/core/result_payloads.py`
- **App helpers**:
  - `gear_optimizer/app_async_db.py` (async DB saves off the critical path)
  - `gear_optimizer/app_stop_control.py` (stop/signal control)
- **In-flight stages**: `gear_optimizer/solver/native_inflight_stages.py` (decode + FG prep + stage profiling)

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
