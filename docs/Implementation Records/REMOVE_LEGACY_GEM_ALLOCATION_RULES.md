# Remove Legacy Gem Allocation Rules

Date: 2026-05-11

## Context

The bounded branch-and-bound gem solver is the canonical exact allocator for
fixed timing.  Older greedy and warm-start refinement rules still existed beside
that path:

- PP tie lookahead in the CPU and GPU greedy allocators.
- GPU warm-start local-search allocation from hints.
- GPU refined-from-hint CM/FM sweeps behind `optimize_core_device_refined`.
- CPU fallback refined-from-hint CM/FM sweeps after greedy selection.

These rules were not part of the exact BnB proof surface and made allocator
behavior depend on which legacy entry point was used.

## Change

- Removed PP tie lookahead from CPU and GPU greedy allocators.
- Deleted the GPU warm-start `local_search_from_hint` function.
- Rewired legacy GPU imports that used `optimize_core_device_refined` to use
  `optimize_core_device_exact_bound` instead, then deleted the refined
  GPU helper functions.
- Deleted the CPU fallback refined-from-hint helper and stopped the CPU fallback
  path from running a post-greedy refine pass.
- Updated GPU regression coverage so plateau crossing is proven by exact-bound
  enumeration rather than by a local-search jump or bounded refinement rule.
- Follow-up audit removed the public GPU greedy allocator export entirely,
  rewired the Metal patched kernels to exact-bound, and flattened vestigial
  `use_exact_inner_solver` branches whose true and false arms both called the
  exact-bound allocator.
- Added regression coverage that `use_exact_inner_solver=True` and
  `use_exact_inner_solver=False` produce the same exact registry-solve result.

## Invariant

Any production or skyline GPU gem solve must use the exact-bound allocator.
Legacy non-exact warm-start/refined gem allocation rules must not remain as
alternate candidate scoring or materialization entry points.
Boolean compatibility selectors must not create a second allocator route.

## Verification

Run:

```text
python -m pytest tests/test_gem_optimizer_cm_lookahead.py tests/test_gem_solver_refine_cm_nonzero_regression.py
python -m pytest -m gpu tests/test_gpu_local_search_cm_plateau.py
python -m pytest -m gpu tests/test_gpu_exact_inner_registry_solve.py
python -m py_compile gear_optimizer/core/constants.py gear_optimizer/solver/scoring_core.py gear_optimizer/solver/scoring/fever_solver.py gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py gear_optimizer/solver/taichi_gem/kernels/__init__.py gear_optimizer/solver/taichi_gem/kernels/kernels_solvers_batch.py gear_optimizer/solver/taichi_gem/kernels/skyline_eval/combo_search.py gear_optimizer/solver/taichi_gem/kernels/skyline_eval/warmstart.py gear_optimizer/solver/taichi_gem/kernels/skyline_eval/write_results.py gear_optimizer/solver/taichi_gem/kernels_metal.py tests/test_gpu_exact_inner_registry_solve.py
python -m ruff check gear_optimizer/core/constants.py gear_optimizer/solver/scoring_core.py gear_optimizer/solver/scoring/fever_solver.py gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py gear_optimizer/solver/taichi_gem/kernels/__init__.py gear_optimizer/solver/taichi_gem/kernels/kernels_solvers_batch.py gear_optimizer/solver/taichi_gem/kernels/skyline_eval/combo_search.py gear_optimizer/solver/taichi_gem/kernels/skyline_eval/warmstart.py gear_optimizer/solver/taichi_gem/kernels/skyline_eval/write_results.py gear_optimizer/solver/taichi_gem/kernels_metal.py tests/test_gem_optimizer_cm_lookahead.py tests/test_gem_solver_refine_cm_nonzero_regression.py tests/test_gpu_local_search_cm_plateau.py tests/test_gpu_exact_inner_registry_solve.py
```
