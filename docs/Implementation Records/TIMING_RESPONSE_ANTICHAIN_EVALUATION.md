# ADR: Timing Response Antichain Evaluation

Date: 2026-05-11

Status: Accepted

## Context

After fixed-timing, response-envelope, and mini-layer pruning, the dominant `00 (Hard)` phase was still exact base scoring in `base_pair_eval_gpu`. The scorer was spending work on many `(FT gems, FF gems)` timing spends per candidate even when some spends were already simulated by another spend from the same pre-gem timing cell.

The safe invariant is candidate-local: for a fixed start timing cell, a timing spend may be removed only when another legal spend reaches the same exact base-scorer-visible timing frontier pack with no less remaining non-timing budget and no less timing-gem lane-base opportunity.

## Decision

Add a strict score-only timing-response antichain for base evaluation:

- new module: `gear_optimizer/solver/timing_response_antichain.py`
- integration: `exact_skyline.py` builds one table for the concrete product start timing cells before `_evaluate_pairs_exact`
- GPU execution: the registry score-only request carries a flattened antichain table plus per-genome offsets/lengths
- kernel behavior: `skyline_find_best_combo_warmstart_kernel` loops over the compact per-genome timing menu instead of the full triangular FT/FF table when the request supplies an antichain

The strict dominance rule for two timing spends `a` and `b` from the same start cell is:

```text
pack(a) == pack(b)
remaining_budget(a) >= remaining_budget(b)
lane_value(a) >= lane_value(b)
```

where:

```text
lane_value = w_ft * ft_gems + w_ff * ff_gems + w_ov * remaining_budget
```

The timing pack key is built from the exact retained timeline frontier surfaces used by the GPU base scorer:

```text
head_len
all retained frontier masks
all retained body_fever/body_normal counts
```

This deliberately avoids the older canonical timing signature as a certificate key.

## Scope

The antichain is base-score safe and score-only. It is not used for materialized payload generation, and the GPU API raises if a caller tries to use it with result materialization. Retained candidates are still rebuilt through the full payload path later, so FG payload correctness is not delegated to the base antichain.

The table is default-on when it fits the configured GPU table capacity. If the flattened table would exceed `GPU_TIMING_RESPONSE_ANTICHAIN_COMBOS`, the solver keeps the full FT/FF table. This is a resource-bound safe no-op, not an alternate scoring path.

## Consequences

Positive:

- removes redundant inner timing spends in the dominant base scoring phase
- keeps one GPU scorer path; the kernel only changes how FT/FF combos are enumerated
- supports timing gems that affect lane base by including lane opportunity in the dominance certificate

Tradeoffs:

- adds GPU fields for flattened timing-response combo tables and per-genome offsets
- the score-only restriction is explicit because combo indices are local to the antichain table and are not valid payload identifiers
- the strict equality certificate prunes less than a future surface-dominance antichain, but it is cheaper and simpler to certify

## Verification

- `python -m pytest -q tests/test_timing_response_antichain.py tests/test_mini_response_prune.py tests/test_response_envelope_prune.py tests/test_gpu_exact_inner_registry_solve.py`
- `python -m py_compile gear_optimizer/solver/timing_response_antichain.py gear_optimizer/solver/exact_skyline.py gear_optimizer/solver/solver_common.py gear_optimizer/solver/registry_solve_request.py gear_optimizer/solver/gpu_executor.py gear_optimizer/solver/taichi_gem/api/initialization.py gear_optimizer/solver/taichi_gem/api/skyline_operations.py gear_optimizer/solver/taichi_gem/api/parallel_solvers.py gear_optimizer/solver/taichi_gem/fields.py gear_optimizer/solver/taichi_gem/kernels/kernels_helpers.py gear_optimizer/solver/taichi_gem/kernels/skyline_eval/warmstart.py`
- `python -m ruff check gear_optimizer/solver/timing_response_antichain.py gear_optimizer/solver/exact_skyline.py gear_optimizer/solver/solver_common.py gear_optimizer/solver/registry_solve_request.py gear_optimizer/solver/gpu_executor.py gear_optimizer/solver/taichi_gem/api/initialization.py gear_optimizer/solver/taichi_gem/api/skyline_operations.py gear_optimizer/solver/taichi_gem/api/parallel_solvers.py gear_optimizer/solver/taichi_gem/fields.py gear_optimizer/solver/taichi_gem/kernels/kernels_helpers.py gear_optimizer/solver/taichi_gem/kernels/skyline_eval/warmstart.py tests/test_timing_response_antichain.py`
- Vulkan smoke parity: a capped registry solve with only `(0, 0)` legal produced identical full-table and antichain scores.
- `00 (Hard) by garlagan` profile (`artifacts/profile/timing_response_antichain_20260511`): disabled hot wall `43.834s`; enabled/default hot wall `29.254s`; base/FG parity `34,253,930` / `34,259,925`; timing spends `12,640,957 -> 852,729` (`14.82x`); `base_pair_eval_gpu` `32.076s -> 17.846s`; hot solve total `41.672s -> 27.129s`.
