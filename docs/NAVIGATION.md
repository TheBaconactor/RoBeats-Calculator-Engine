# Navigation Guide

## Documentation Map

- Human-friendly index: `docs/README.md`
- Current code map: this file
- Historical implementation records: `docs/Implementation Records/README.md`
- Research bundles: `docs/research/README.md`
- Legacy archive: `docs/archive/README.md`

## Primary Entry Points

- Optimizer: `main.py` -> `gear_optimizer/app.py` (`GearOptimizerApp.run`)
- GeneralMeta: `general_meta_main.py` -> `general_meta/` (`run_general_meta`)
- Inventory Meta coverage: `inventory_meta_coverage_main.py` -> `inventory_optimizer/`

## Typical Optimizer Flow

- Config load (`config.ini` or `METAFINDER_CONFIG_PATH`) -> path discovery (`bin/paths_cache.json`) -> song queue -> per-song processing -> solver -> DB write
- Per-song execution: `gear_optimizer/pipeline/song_processor.py`
- GA loop: `gear_optimizer/solver/genetic.py`
- In-flight (single-process, multi-song): `gear_optimizer/solver/inflight_orchestrator.py`, `gear_optimizer/solver/native_inflight_orchestrator.py`
- Scoring (CPU/GPU dispatch): `gear_optimizer/solver/scoring/`
- Database/persistence: `gear_optimizer/data/database.py`
- Config + paths: `gear_optimizer/core/config.py`, `gear_optimizer/core/constants.py`

## GPU / Taichi

- GPU executor/IPC: `gear_optimizer/solver/gpu_executor.py`
- Taichi solver API: `gear_optimizer/solver/taichi_gem/api/`
- Taichi kernels (core): `gear_optimizer/solver/taichi_gem/kernels/`
  - GA ops (selection/crossover/mutation/elitism): `gear_optimizer/solver/taichi_gem/kernels/kernels_ga.py`
  - Scoring + gem optimization: `gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py`
  - Timeline grid computation: `gear_optimizer/solver/taichi_gem/kernels/kernels_timeline.py`
  - GA evaluation/reduction (split): `gear_optimizer/solver/taichi_gem/kernels/ga_eval/`
    - Reductions + packed-key helpers: `gear_optimizer/solver/taichi_gem/kernels/ga_eval/reduction.py`
    - FT/FF combo search: `gear_optimizer/solver/taichi_gem/kernels/ga_eval/combo_search.py`
    - Materialize best results: `gear_optimizer/solver/taichi_gem/kernels/ga_eval/write_results.py`
    - Global-best tracking: `gear_optimizer/solver/taichi_gem/kernels/ga_eval/global_best.py`
    - Payload packing (CPU download): `gear_optimizer/solver/taichi_gem/kernels/ga_eval/payload.py`
    - Island elitism + migration: `gear_optimizer/solver/taichi_gem/kernels/ga_eval/islands.py`, `gear_optimizer/solver/taichi_gem/kernels/ga_eval/migration.py`
    - Warm-start evaluation: `gear_optimizer/solver/taichi_gem/kernels/ga_eval/warmstart.py`

## Supporting Folders

- `scripts/`: ad-hoc utilities, organized by category (`scripts/profile/`, `scripts/db/`, `scripts/fg/`, `scripts/query/`, `scripts/data/`, `scripts/debug/`, `scripts/regression/`)
- `tools/`: maintained utilities and benchmarks, organized by category (`tools/bench/`, `tools/profile/`, `tools/db/`, `tools/verify/`, `tools/data/`, `tools/dev/`, `tools/ml/`)
- Unified script discovery: `python -m tools list` (`--all` includes private/scratch scripts)
- Unified inventory audit: `python -m tools audit`
- Unified script execution: `python -m tools run <id> -- <args>`
- Repo-local MCP harness: `python -m tools.mcp_server`
- GeneralMeta: `python general_meta_main.py`

## Reference Docs

- Engineering doctrine and harness layout: `docs/ENGINEERING_PRINCIPLES.md`
- MCP harness contract: `docs/MCP_HARNESS_CHARTER.md`
- Architecture overview: `docs/ARCHITECTURE.md`
- Database schema: `docs/DATABASE_SCHEMA.md`
- Frontend DB readiness note: `docs/integration/DB_READY_FOR_FRONTEND.md`
- Fever timeline math: `docs/FEVER_TIMELINE_MATH.md`
- Human HitSim details: `docs/HUMAN_HIT_SIM.md`
- Stats verifier: `docs/STATS_VERIFIER.md`

## Refactoring and Maintenance Notes

- Duplication reduction map: `docs/DUPLICATION_REDUCTION.md`
- Runtime/GPU maintenance playbook: `docs/MAINTENANCE_PLAYBOOK.md`
- In-flight integrated throughput architecture and A/B protocol: `docs/INFLIGHT_GA_FG_THROUGHPUT.md`
- Same-slot GPU-resident GA->FG handoff and legacy-path cleanup: `docs/GPU_RESIDENT_GA_FG_PLAN.md`
- Steady-state GA plus global unique-eval proposal: `docs/STEADY_STATE_UNIQUE_EVAL_GA_PLAN.md`
- Historical implementation records index: `docs/Implementation Records/README.md`
