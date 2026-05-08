# Outer Search Engine: Marginal-Prune Heuristic Pipeline

Date: 2026-04-07

Status: **Superseded** by `OUTER_ENGINE_ORTHOGONAL_PREPRUNE_FG_MODES.md` (2026-04-07). The
`marginal` and `marginal_fused` names now survive only as backward-compatible
config aliases for `OuterSearchEngine=exact` plus `PrePruneMode=marginal`
and, for `marginal_fused`, `FG_SolverMode=exact_dp`.

## Context

- The exact skyline outer solver is correct but can become expensive on large pools due to DP + skyline memory/runtime.
- Research in `tools/bench/research_slot_pruning.py` showed that a human-like per-slot pruning strategy
  (naive ranking + marginal-value ranking, then union top-K) can dramatically shrink the gear search surface.
- Existing production architecture already has a robust exact GPU scoring path (`RegistrySolveRequest` +
  `dispatch_registry_solve`) and downstream FG/persistence contracts that should remain unchanged.

## Problem

The original proposal framed K=3 and top-N filtering as universally exact. That claim was stronger than the current
evidence:

- validated strongly on proxy objective across sampled songs,
- not yet proven as a theorem for end-to-end exact score ranking on all songs.

We needed a production path that captures the speed breakthrough while keeping explicit safety controls.

## Decision

Add new outer engine values:

- `OuterSearchEngine=marginal`
- `OuterSearchEngine=marginal_fused` (marginal outer + exact FG DP)

Pipeline:

1. Build gear/mini pools via existing `initialize_pools`.
2. Rank each slot two ways:
   - naive per-item proxy ranking,
   - iterative marginal swap ranking (fever-aware proxy).
3. Keep union top-K per slot (`MarginalPruneK`, default 3).
4. Enumerate only selected gear combinations.
5. Build mini skyline with existing exact helper.
6. Proxy-score selected gear x mini product on CPU (vectorized NumPy batches) and keep top-N (`MarginalPruneGpuTopN`, default 2048).
7. Exact-score that top-N through existing GPU registry solve path.
8. Return payload in the same tuple and candidate format as `solve_exact_skyline`.

`marginal`/`marginal_fused` are intentionally heuristic outer engines, not replacements for exact skyline correctness claims.

## Implementation

- New file:
  - `gear_optimizer/solver/marginal_pruning.py`
    - `solve_marginal_prune(...)` with same call/return contract as `solve_exact_skyline(...)`
    - naive + marginal per-slot rankers
    - proxy scorer with fever timeline cache
    - exact GPU refinement over proxy top-N
    - fallback to `solve_exact_skyline` if selected K-space exceeds a configurable cap

- Updated files:
  - `gear_optimizer/core/config.py`
    - `read_outer_search_engine()` now recognizes `marginal`, `marginal_fused`, and aliases.
  - `gear_optimizer/pipeline/song_processor.py`
    - routes `OuterSearchEngine=marginal`/`marginal_fused` to `solve_marginal_prune(...)`
    - routes `marginal_fused` FG stage through `process_fg_exact_dp(...)`
  - `gear_optimizer/solver/native_inflight_prepare.py`
    - switched fallback/default outer-engine selection to `marginal`
  - `gear_optimizer/solver/native_inflight_orchestrator.py`
    - handles `marginal`/`marginal_fused` in the exact-like in-flight branch
    - runs exact FG DP for `fused_exact` and `marginal_fused` in `_run_fg_job_sync(...)`
    - keeps single in-flight guard for exact-like engines (`exact_skyline`, `fused_exact`, `marginal`, `marginal_fused`)
  - `config.ini`
    - default engine switched to `marginal`
    - documents `marginal`/`marginal_fused` and tuning knobs:
      - `MarginalPruneK`
      - `MarginalPruneGpuTopN`
      - `MarginalPruneProxyBatch`

- New tests:
  - `tests/test_exact_skyline_routing_switch.py`
    - added `test_process_song_task_routes_marginal_when_enabled`
    - added `test_process_song_task_routes_marginal_fused_and_uses_exact_fg`
  - `tests/test_outer_search_engine_config.py`
    - validates config/env canonicalization for `marginal` and `marginal_fused`

## Consequences / Tradeoffs

Positive:

- Large reduction in candidate surface before exact GPU scoring.
- Reuses existing exact GPU path and downstream FG logic (no GPU kernel changes).
- Keeps exact skyline available as correctness anchor.

Tradeoffs:

- `marginal`/`marginal_fused` are heuristic on the outer search; quality depends on K and proxy top-N settings.
- Very aggressive top-N can miss the global best; default set wider than final keep-top-k to reduce risk.
- `marginal_fused` uses exact FG DP, but that does not make the full pipeline globally exact because the outer stage remains heuristic.

## Verification

Research evidence captured during implementation:

- `tools/bench/research_slot_pruning.py` on
  - `Pixel Galaxy (Hard)`
  - `Aether (Hard)`
  - `AfterLife (Hard)`
- For the proxy objective, K=3 union achieved 0.0000% gap vs DP proxy optimum in all three sampled songs.

Code-level verification commands:

- `python -m pytest -q tests/test_exact_skyline_routing_switch.py tests/test_outer_search_engine_config.py`

Recommended follow-up validation before default changes:

- multi-song GPU-exact parity sweep comparing `marginal` vs `exact_skyline` winners and score gaps.
- sensitivity sweep over `MarginalPruneK` and `MarginalPruneGpuTopN`.
