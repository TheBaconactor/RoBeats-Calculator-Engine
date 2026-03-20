# ADR: Fix FT/FF Parallel Solver Parity (Disable Vulkan Block Kernel by Default)

Date: 2026-03-20

Status: Accepted

## Context

A GPU regression test (`tests/test_solve_genomes_from_registry_score_parity.py`) showed that the "parallel"
FT/FF solver (`solve_genomes_with_ftff`) can return per-genome scores that differ from the canonical GPU
registry-eval path (`solve_genomes_from_registry`) on Taichi/Vulkan (AMD).

The mismatch is not just tie-breaking. We observed the same allocation tuple `(ft, ff, pp, cm, fm, ov)`
being returned with different scores, which is impossible unless the score itself is wrong. This makes GA
selection untrustworthy and can create "hidden" top-1 regressions even when runs appear healthy.

The portable kernel (`kernels.solve_genomes_with_ftff_kernel`) matches the registry path exactly. The Vulkan
block/subgroup kernel (`kernels.solve_genomes_with_ftff_block_kernel`) does not.

Separately, GA eval kernels under `gear_optimizer/solver/taichi_gem/kernels/ga_eval/` used `simt.subgroup.elect()`
while assuming the elected lane is the argmax lane. This assumption is not guaranteed across Vulkan
implementations and can cause payloads (PP/CM/FM/OV) to be dropped even when the best key is computed correctly.

## Decision

1. Make the portable per-genome FT/FF kernel the default implementation for `solve_genomes_with_ftff()` on Vulkan.
2. Keep the block/subgroup FT/FF kernel opt-in only behind `GPU_FTFF_BLOCK_KERNEL=1` and emit a warning when enabled.
3. Fix subgroup payload writes in GA eval kernels by reducing payload components gated by the winner predicate, so the
   elected lane can write deterministically.

## Consequences

Positive:
- Restores score parity between registry eval and parallel FT/FF eval, preventing hidden GA regressions.
- Keeps an explicit escape hatch for benchmarking/experiments without silently risking correctness.
- Hardens subgroup writes against backend-dependent elect semantics.

Negative / Risks:
- The portable kernel is slower than the intended block kernel on Vulkan; throughput may decrease until a safe,
  validated optimized kernel replaces it.
- Users enabling `GPU_FTFF_BLOCK_KERNEL=1` may still see incorrect results; the warning exists to prevent accidental use.

## Verification

- `python -m pytest -m gpu tests/test_solve_genomes_from_registry_score_parity.py`
- `python -m pytest -m gpu tests/test_parity_smoke.py::test_gem_solver_cpu_gpu_exact_parity_smoke`
- `python -m pytest -m gpu tests/test_gpu_ga_ops.py`
- `python -m pytest -m gpu tests/test_gpu_ga_eval_race_free.py`

## References

- Repro script: `scripts/debug/repro_registry_parallel_parity.py`
- FT/FF dispatch: `gear_optimizer/solver/taichi_gem/api/parallel_solvers.py`
