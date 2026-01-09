# Navigation Guide

## Start Here (Typical Run)

- Entry point: `main.py` -> `gear_optimizer/app.py` (`GearOptimizerApp.run`)
- Per-song execution: `gear_optimizer/pipeline/song_processor.py`
- GA loop (CPU): `gear_optimizer/solver/genetic.py`
- In-flight (single-process, multi-song): `gear_optimizer/solver/inflight_orchestrator.py`, `gear_optimizer/solver/native_inflight_orchestrator.py`
- Scoring (CPU/GPU dispatch): `gear_optimizer/solver/scoring/`
- Database/persistence: `gear_optimizer/data/database.py`
- Config + paths: `gear_optimizer/core/config.py`, `gear_optimizer/core/constants.py`

## GPU / Taichi

- GPU executor/IPC: `gear_optimizer/solver/gpu_executor.py`
- Taichi solver facade: `gear_optimizer/solver/taichi_gem_solver.py`
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

## One-Offs / Debugging

- `scripts/`: ad-hoc utilities, organized by category (`scripts/profile/`, `scripts/db/`, `scripts/fg/`, `scripts/query/`, `scripts/data/`, `scripts/debug/`, `scripts/regression/`)
- `tools/`: heavier utilities/benchmarks, organized by category (`tools/bench/`, `tools/profile/`, `tools/db/`, `tools/verify/`, `tools/data/`, `tools/meta/`, `tools/dev/`)
- GeneralMeta: `python general_meta_main.py`

## Refactoring Notes

- Duplication reduction map: `docs/DUPLICATION_REDUCTION.md`
