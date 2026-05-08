# Outer Engine Refactor: Orthogonal Pre-Prune and FG Modes

Date: 2026-04-07

## Context

- `OUTER_SEARCH_ENGINE_EXACT_SKYLINE_WIRING.md` added production support for an exact outer solver.
- `MARGINAL_PRUNE_OUTER_ENGINE.md` then promoted `marginal` / `marginal_fused` to first-class outer-engine names.
- `FUSED_EXACT_PIPELINE_NO_GA.md` promoted `fused_exact` as another first-class outer-engine name.

That left the pipeline with five outer-engine spellings encoding two orthogonal concerns:

1. the actual outer search strategy (`ga` vs exact skyline), and
2. what to do around that search (`marginal` pool reduction, exact-DP FG post-processing).

At the same time, `marginal_pruning.py` imported private helpers from `exact_skyline.py`, and multiple solvers rebuilt
the same pools, config payloads, registry state, and mini skyline independently.

## Problem

The old structure had four concrete issues:

- routing complexity: `song_processor` and native in-flight both branched over `ga`, `exact_skyline`, `marginal`,
  `fused_exact`, and `marginal_fused`,
- mode tangling: FG behavior depended on outer-engine names instead of a dedicated FG mode,
- shared-code leakage: `marginal_pruning.py` imported seven `_`-prefixed helpers from `exact_skyline.py`,
- latent bug surface: `song_processor` could reach the FG section with `outer_engine` never assigned.

## Decision

Collapse the public engine surface to:

- `OuterSearchEngine = ga | exact`
- `PrePruneMode = none | marginal | auto`
- `FG_SolverMode = finder | manual | exact_dp | off`

Backward-compatible aliases remain accepted at config/env read time:

- `marginal` => `OuterSearchEngine=exact` + `PrePruneMode=marginal`
- `fused_exact` => `OuterSearchEngine=exact` + `FG_SolverMode=exact_dp`
- `marginal_fused` => `OuterSearchEngine=exact` + `PrePruneMode=marginal` + `FG_SolverMode=exact_dp`

The implementation also makes these structural changes:

- move shared exact-solver infrastructure into `solver_common.py`,
- move mini skyline construction into `mini_skyline.py`,
- rewrite `marginal_pruning.py` as a pure pool reducer,
- preprocess once into a `SolverContext` before outer search,
- split `process_song_task()` into setup / outer / FG / persist phases,
- treat direct-GA FG passthrough as GA+finder-specific behavior, not a general FG path.

## Implementation

New modules:

- `gear_optimizer/solver/solver_common.py`
  - `GEAR_SLOTS`
  - `BitPack` / `make_pack`
  - packed-code decoders
  - solver cfg/payload builders
  - `batched_registry_eval`
  - `SolverContext` / `prepare_solver_context()`
- `gear_optimizer/solver/mini_skyline.py`
  - `LaneAwareMiniSkylineStats`
  - `mini_combo_skyline()`

Solver changes:

- `gear_optimizer/solver/exact_skyline.py`
  - now consumes `SolverContext`
  - keeps private compatibility aliases but the canonical definitions live in shared modules
  - exact GPU batch scoring now reuses `batched_registry_eval`
- `gear_optimizer/solver/marginal_pruning.py`
  - now exports only `prune_gear_pool_marginal(...)`
  - no longer owns registry creation, exact GPU refinement, or exact fallback logic
- `gear_optimizer/solver/genetic.py`
  - accepts an optional prepared solver context
  - removes the dead CPU-GA tail
  - treats `FG_SolverMode=exact_dp` as requiring candidate stats
- `gear_optimizer/solver/fused_exact.py`
  - dropped the unused `fg_search_radius` parameter from `process_fg_exact_dp()`

Pipeline changes:

- `gear_optimizer/pipeline/song_processor.py`
  - canonical routing is now `ga` vs `exact`
  - pre-prune and FG modes are read separately
  - `process_song_task()` now delegates to `_setup_song_context()`, `_run_outer_search()`,
    `_run_force_greats()`, and `_build_and_persist()`
  - fixes the latent `outer_engine` use-before-assignment bug
  - removes the dead `_prefetch_mgr` cleanup branch

Native in-flight changes:

- `gear_optimizer/solver/native_inflight_prepare.py`
  - stages `outer_engine`, `pre_prune_mode`, and `fg_solver_mode` into `cfg_data`
- `gear_optimizer/solver/native_inflight_orchestrator.py`
  - exact-like submission is now `outer_engine != "ga"`
  - exact outer solves always call `solve_exact_skyline(...)` with `pre_prune_mode`
  - FG exact-DP routing keys off `fg_solver_mode`, not outer-engine names
- `gear_optimizer/solver/native_inflight_stages.py`
  - direct-GA FG passthrough is limited to GA + finder/manual FG modes

Config/defaults:

- `config.ini`
  - `OuterSearchEngine = exact`
  - `PrePruneMode = auto`
  - `FG_SolverMode = finder`

## Consequences

Positive:

- The outer engine API is smaller and easier to reason about.
- Marginal pruning is explicitly a preprocessing choice, not a separate solver implementation.
- Exact FG DP becomes available orthogonally to either outer engine.
- Registry and mini skyline preprocessing are now reusable across solvers.

Tradeoffs:

- Legacy configs still work, but now emit deprecation warnings and normalize into the new mode matrix.
- The refactor preserves compatibility wrappers in a few places while shared helpers become canonical; further
  dead-code cleanup can remove now-unused legacy helper bodies later.

## Verification

- `python -m py_compile gear_optimizer/core/config.py gear_optimizer/solver/solver_common.py gear_optimizer/solver/mini_skyline.py gear_optimizer/solver/exact_skyline.py gear_optimizer/solver/marginal_pruning.py gear_optimizer/solver/genetic.py gear_optimizer/solver/fused_exact.py gear_optimizer/pipeline/song_processor.py gear_optimizer/solver/native_inflight_prepare.py gear_optimizer/solver/native_inflight_orchestrator.py gear_optimizer/solver/native_inflight_stages.py`
- `python -m ruff check gear_optimizer/core/config.py gear_optimizer/solver/solver_common.py gear_optimizer/solver/mini_skyline.py gear_optimizer/solver/exact_skyline.py gear_optimizer/solver/marginal_pruning.py gear_optimizer/solver/genetic.py gear_optimizer/solver/fused_exact.py gear_optimizer/pipeline/song_processor.py gear_optimizer/solver/native_inflight_prepare.py gear_optimizer/solver/native_inflight_orchestrator.py gear_optimizer/solver/native_inflight_stages.py`
- `python -m pytest -q tests/test_outer_search_engine_config.py tests/test_exact_skyline_routing_switch.py`
- `python -m pytest -q tests/test_force_greats_direct_ga_fallback.py tests/test_native_inflight_fg_direct_ga_candidates.py`
- `python -m pytest -q tests/test_exact_skyline_envelope_reduction.py`
