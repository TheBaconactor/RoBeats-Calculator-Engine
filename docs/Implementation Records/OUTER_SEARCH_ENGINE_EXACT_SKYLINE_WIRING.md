# Outer Search Engine: Exact Skyline Production Wiring

Date: 2026-04-07

## Context

- An exact outer search solver ("exact skyline") exists: exact DP + skyline pruning + GPU batch scoring.
- Production has two execution surfaces that perform the outer solve:
  - Legacy per-song pipeline (`gear_optimizer/pipeline/song_processor.py`).
  - Default sequential MetaFinder runs via native in-flight (`gear_optimizer/solver/native_inflight_prepare.py` +
    `gear_optimizer/solver/native_inflight_orchestrator.py`).
- Native in-flight executes Taichi work via a single GPU-service owner thread (`gpu_client`) to avoid unsafe direct
  kernel calls from arbitrary threads.

## Problem

The exact skyline solver was not selectable in production. We needed a production-facing switch that:

- selects GA vs exact skyline deterministically,
- applies to both legacy per-song and native in-flight pipelines,
- preserves native in-flight GPU-safety (GPU-owner thread routing), and
- keeps downstream FG/persistence behavior stable.

## Root Cause

- There was no config/env selector for an "outer search engine".
- Native in-flight's outer stage assumed GA candidate payload encoding/decoding.
- The exact skyline solver and gem/fever helpers could call registry solves directly, which is unsafe under native
  in-flight unless routed through the shared GPU service client.

## Decision

- Add `[IterationEngine] OuterSearchEngine` with supported values:
  - `ga` (default): current behavior.
  - `exact_skyline`: exact skyline outer solver.
- Add environment overrides (highest precedence):
  - `METAFINDER_OUTER_SEARCH_ENGINE`
  - `OUTER_SEARCH_ENGINE`
- Wire this selection into both production paths.
- For native in-flight when `OuterSearchEngine=exact_skyline`:
  - run the CPU-side exact solve in a CPU executor thread,
  - route all GPU registry/gem work through `gpu_client`, and
  - constrain to single in-flight exact submission to avoid CPU/RAM blowups (DP + skyline allocation scale).

## Implementation

- `config.ini`
  - Added `OuterSearchEngine = ga` with a comment documenting `ga | exact_skyline`.

- `gear_optimizer/core/config.py`
  - Added `read_outer_search_engine(cfg, default="ga")`:
    - canonicalizes values to `ga` / `exact_skyline`,
    - supports env overrides.

- `gear_optimizer/pipeline/song_processor.py`
  - Reads `OuterSearchEngine` and branches outer solve:
    - `ga` → existing `solve_coevolution_genetic(...)`.
    - `exact_skyline` → `solve_exact_skyline(...)`.

- `gear_optimizer/solver/native_inflight_prepare.py`
  - Stores `cfg_data["outer_engine"]` so the orchestrator can branch per task.

- `gear_optimizer/solver/native_inflight_orchestrator.py`
  - Branches outer submission based on `song.cfg_data["outer_engine"]`.
  - For `exact_skyline`:
    - runs a CPU executor helper that calls `solve_exact_skyline(..., gpu_client=gpu_client)`.
    - bypasses GA payload decode by carrying `(best_data, best_gear, best_minis, ga_candidates)` directly into the
      existing finalize/FG stages.
    - caps concurrency to a single in-flight exact skyline job.

- `gear_optimizer/solver/exact_skyline.py`
  - Added `gpu_client` plumbing so registry solves and gem refinement can be dispatched through the GPU service.

- `gear_optimizer/solver/scoring/fever_solver.py`
  - Extended `solve_best_fever_combination(..., gpu_client=None)` so exact skyline can route the fever/gem solve through
    the same GPU dispatch mechanism used by native in-flight.

## Consequences / Tradeoffs

- Default production behavior remains GA (`OuterSearchEngine=ga`).
- Exact skyline becomes a supported outer engine, but is intentionally single-in-flight under native in-flight.
- GPU-only policy is preserved: this change does not add CPU fallbacks; it ensures GPU work is correctly routed.

## Verification

- Real-song parity gate:
  - `python -m pytest -q tests/test_exact_skyline_vs_ga_real_song.py -s`
- Static checks:
  - No Pylance errors reported in the touched modules.
