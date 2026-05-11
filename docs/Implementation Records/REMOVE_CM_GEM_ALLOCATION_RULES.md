# ADR: Remove CM Gem Allocation Special Rules

Date: 2026-05-11

Status: Accepted

## Context

The gem allocators had CM-specific plateau escape rules in addition to ordinary one-step greedy scoring and exact bounded enumeration:

- CPU greedy `optimize_core_jit()` probed multi-gem CM streaks when OV won the immediate step.
- GPU greedy `_optimize_core_device_impl()` mirrored that CM lookahead.
- GPU warm-start `local_search_from_hint()` had a one-shot CM jump from OV into CM when the hint started at `CM=0`.

These rules made CM allocation behavior depend on special-case breakpoint handling rather than the same local scoring rules used for the other non-timing gems.

## Decision

Remove the CM-specific lookahead/jump rules.

CM remains a normal gem allocation option:

- ordinary greedy can still pick CM when the next CM gem is the best immediate move
- exact bounded solvers still enumerate CM where they own the exact inner search
- no production CPU fallback was introduced

## Consequences

Positive:

- deletes CM-only allocation behavior from CPU and GPU primitives
- keeps greedy/local-search behavior simpler and easier to reason about
- removes stale `CM_LOOKAHEAD_MAX`

Tradeoffs:

- synthetic CM plateau traps no longer get crossed by the greedy/local-search special case
- exact bounded paths remain the source of truth for cases that require non-local CM allocation

## Verification

- `python -m pytest tests/test_gem_optimizer_cm_lookahead.py`

## References

- CPU greedy allocator: `gear_optimizer/solver/scoring_core.py`
- GPU scoring kernels: `gear_optimizer/solver/taichi_gem/kernels/kernels_scoring.py`
- Superseded record: `docs/Implementation Records/GPU_NATIVE_GA_CM_PLATEAU_LOOKAHEAD.md`
