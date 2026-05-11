# Remove Uncertified Gem Gates And Envelope Pruning

Date: 2026-05-11

## Context

The exact bounded gem solver is the correctness owner for fixed-timing gem
allocation.  Legacy domain gates still encoded assumptions that were not proven
by a per-state certificate:

- PP gems were allowed only when Chill was a primary or secondary lane.
- CM gems were fully allowed only when Flow was a primary or secondary lane;
  otherwise CM was capped around stat 50.
- The exact skyline PP/overflow local envelope pruned gear and combined
  candidates using the same old PP/overflow-only allocation model.

These rules are not lossless under the current model because PP can still gain
reference-table value without a Chill lane, and CM can still gain multiplier
value without a Flow lane.

## Change

- Removed the hardcoded PP and CM lane gates from the CPU exact bounded solver.
- Removed the same PP and CM gates from the Taichi exact-bound GPU solver.
- Removed the PP/overflow envelope reducer and its gear/combined skyline wiring.
- Replaced envelope-specific tests with the remaining exact skyline frontier
  contract tests.
- Added CPU and GPU regressions proving:
  - CM above 50 can be allocated without a Flow lane.
  - PP can be allocated without a Chill lane.
  - CM plateau crossing remains handled by exact-bound enumeration.

## Invariant

Gem allocation feasibility is stat-cap based unless an explicit game rule says
otherwise.  The solver may skip a branch only when the exact-bound allocator's
dynamic admissible upper-bound certificate proves that the branch cannot beat
the current incumbent.  Candidate pruning must not use PP/CM/overflow allocation
assumptions unless it carries a full exact response certificate.

## Verification

Run:

```text
python -m pytest tests/test_scoring_core_exact_bounded.py tests/test_exact_skyline_frontier_contracts.py tests/test_fixed_timing_prefix_skyline.py
python -m pytest tests/test_theorem_readiness_base5_fg7_margins.py
python -m pytest -m gpu tests/test_gpu_local_search_cm_plateau.py tests/test_gpu_exact_inner_registry_solve.py
python -m py_compile gear_optimizer/solver/exact_skyline.py gear_optimizer/solver/scoring_core.py gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py tests/test_scoring_core_exact_bounded.py tests/test_exact_skyline_frontier_contracts.py tests/test_gpu_local_search_cm_plateau.py tests/test_theorem_readiness_base5_fg7_margins.py
python -m ruff check gear_optimizer/solver/exact_skyline.py gear_optimizer/solver/scoring_core.py gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py tests/test_scoring_core_exact_bounded.py tests/test_exact_skyline_frontier_contracts.py tests/test_gpu_local_search_cm_plateau.py tests/test_theorem_readiness_base5_fg7_margins.py
```
