# Navigation Guide

## Documentation Map

- Human-friendly index: `docs/README.md`
- Current architecture: `docs/ARCHITECTURE.md`
- Historical implementation records: `docs/Implementation Records/README.md`
- Research bundles: `docs/research/README.md`
- Legacy archive: `docs/archive/README.md`

## Primary Entry Points

- Optimizer: `main.py` -> `gear_optimizer/app.py` (`GearOptimizerApp.run`)
- GeneralMeta: `general_meta_main.py` -> `general_meta/` (`run_general_meta`)
- Service: `gear_optimizer/robeatsmeta_service.py`

## Production Optimizer Flow

- Config and paths: `gear_optimizer/core/config.py`, `gear_optimizer/core/constants.py`
- Song/task queue: `gear_optimizer/pipeline/queue_task_coordinator.py`
- Startup cache ownership: `gear_optimizer/solver/cpu_work_manager.py`
  - Timeline frontier prebuild: `gear_optimizer/solver/timeline_frontier_cache_prebuild.py`
  - Exact Base song-context prebuild: `gear_optimizer/solver/exact_base_song_context_cache_prebuild.py`
  - Native FG frontier prebuild: `gear_optimizer/solver/fg_response_frontier_cache_prebuild.py`
- Native in-flight orchestration: `gear_optimizer/solver/native_inflight_orchestrator.py`
- Per-song preparation: `gear_optimizer/solver/native_inflight_lifecycle_prepare.py`
- Exact Base queue and slot ownership: `gear_optimizer/solver/native_inflight_pipeline_base.py`
- Exact result decode: `gear_optimizer/solver/exact_base_pipeline_decode.py`
- Post-processing: `gear_optimizer/pipeline/post_processor.py`
- Database/persistence: `gear_optimizer/data/database/`

## Exact Base Search

- Request-local domain construction: `gear_optimizer/solver/exact_base_domains.py`
  - Mini-PP and PP-gem/overflow response-component decomposition lives in the same owner.
- Request-local catalog content fingerprints: `gear_optimizer/core/catalog_fingerprint.py`
- Song timing-response context: `gear_optimizer/solver/exact_base_song_context.py`
- Song-context cache: `gear_optimizer/solver/exact_base_song_context_cache.py`
- GPU-owner search and certificate: `gear_optimizer/solver/exact_base_search.py`
- Effective refill and up-to-51 candidate surface:
  `gear_optimizer/solver/exact_base_search.py`,
  `gear_optimizer/solver/exact_base_candidate_surface.py`
- Fixed-timing prefix reduction: `gear_optimizer/solver/fixed_timing_skyline.py`
- Timing-response antichains: `gear_optimizer/solver/timing_response_antichain.py`

## Native Force Greats

- Base-to-FG owner handoff: `gear_optimizer/solver/native_fg_owner.py`
- FG planning/materialization: `gear_optimizer/solver/fg_response_scoring/`
- Response-frontier construction and scoring: `gear_optimizer/solver/taichi_gem/force_greats/`
- FG cache prebuild/store ownership: `gear_optimizer/solver/fg_response_frontier_cache_prebuild.py`,
  `gear_optimizer/solver/fg_response_scoring/store.py`

## GPU / Taichi

- GPU executor/IPC: `gear_optimizer/solver/gpu_executor.py`,
  `gear_optimizer/solver/gpu_service.py`
- Typed request/result contract: `gear_optimizer/solver/gpu_executor_types.py`
- Taichi solver API: `gear_optimizer/solver/taichi_gem/api/`
- Taichi fields/runtime: `gear_optimizer/solver/taichi_gem/fields.py`,
  `gear_optimizer/solver/taichi_gem/runtime.py`
- Exact Base semiring kernels: `gear_optimizer/solver/taichi_gem/kernels/exact_base_semiring.py`
- Exact inner scorer/materialization kernels:
  `gear_optimizer/solver/taichi_gem/kernels/skyline_eval/`
- Shared scoring and timeline kernels:
  `gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py`,
  `gear_optimizer/solver/taichi_gem/kernels/kernels_timeline.py`

## Supporting Folders

- `scripts/`: ad-hoc utilities organized by category
- `tools/`: maintained benchmarks, profiles, verifiers, database tools and development checks
- Unified script discovery: `python -m tools list` (`--all` includes private/scratch scripts)
- Unified inventory audit: `python -m tools audit`
- Unified script execution: `python -m tools run <id> -- <args>`

## Reference Docs

- Engineering doctrine: `docs/ENGINEERING_PRINCIPLES.md`
- Architecture overview: `docs/ARCHITECTURE.md`
- Database schema: `docs/DATABASE_SCHEMA.md`
- Frontend DB readiness: `docs/integration/DB_READY_FOR_FRONTEND.md`
- Fever timeline math: `docs/FEVER_TIMELINE_MATH.md`
- Timing envelope details: `docs/Implementation Records/TIMING_ENVELOPE_EXACT_FRONTIER.md`
- Runtime/GPU maintenance: `docs/MAINTENANCE_PLAYBOOK.md`
- Historical decisions: `docs/Implementation Records/README.md`
