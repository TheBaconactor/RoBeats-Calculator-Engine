# Exact Skyline: Local PP/OV Envelope Reduction

Date: 2026-04-06

## Context

The production `exact_skyline` outer solver already had:

- exact gear DP over `(PP, CM, FM, FT)` with local `(FF, base_lane)` frontiers,
- exact gear global skyline,
- exact mini skyline,
- exact combined skyline pruning before GPU scoring.

Research showed that the gear global skyline was still not the minimal exact objective.

For fixed loadout stats `(CM, FM, FT, FF)`, the downstream gem solver does not care about raw `(PP, base_lane)` directly.
It cares about the best achievable `PP + OV` closure for each leftover budget after the FT/FF/FM/CM choices are fixed.

That means two gear points with the same `(CM, FM, FT, FF)` can be compared by an exact leftover-budget envelope instead of
raw skyline coordinates.

## Problem

The production exact skyline path kept some gear states that were already exact-safe dominated once the final `PP/OV`
gem closure was taken into account.

That inflated:

- the gear skyline size,
- the downstream combined skyline candidate surface,
- the number of GPU registry solves required before FG/post-processing.

## Decision

Add an exact same-stat envelope reduction step to the production `exact_skyline` solver:

- after the gear global skyline,
- before mini combination and combined skyline evaluation.

For fixed `(CM, FM, FT, FF)`, define the exact leftover-budget envelope over `L in [0, TOTAL_GEM_BUDGET]`:

- `base_lane + L * w_ov + max_p [ ref_pp(pp + 2p) + p * (w_pp - w_ov) ]`

where:

- `w_pp` is the elemental contribution of PP gems to the song lane base (`Chill` contribution),
- `w_ov` is the elemental contribution of overflow gems to the selected element,
- `ref_pp(...)` is the Perfect Points lookup table.

If one point's envelope pointwise dominates another's for all leftover budgets, the dominated point is removed.

This reduction is exact because all future FT/FF/FM/CM gem choices affect both same-stat points identically; only the
`PP/OV` closure differs.

## Implementation

- `gear_optimizer/solver/exact_skyline.py`
  - added exact local envelope helpers:
    - `_pp_ov_envelope_curve(...)`
    - `_reduce_same_stat_envelope_frontier_with_codes(...)`
  - wired the envelope reduction into `solve_exact_skyline(...)` immediately after the gear global skyline.
  - kept the reduction exact and always-on for the `exact_skyline` path; no heuristic flag or CPU-mode fallback was added.

- `tests/test_exact_skyline_envelope_reduction.py`
  - added a deterministic regression that proves:
    - a strictly dominated same-stat point is removed,
    - an incomparable point whose envelope wins at different leftover budgets is preserved,
    - the surviving gear codes stay aligned with the surviving skyline rows.

### Update (2026-04-07)

Extended the same exact envelope-dominance idea to the combined (gear⊕mini) skyline candidates:

- `gear_optimizer/solver/exact_skyline.py`
  - After combined-skyline selection, apply `_reduce_same_stat_envelope_frontier_with_codes(...)` again on the **pair** points.
  - Packed `(gear_idx, mini_idx)` into a `uint64` code so pruning preserves pair identity and alignment.
  - Reduced combined-skyline grid memory (int16 when safe + in-place per-layer suffix max) so the combined prune runs in more cases.

- `tests/test_exact_skyline_envelope_reduction.py`
  - Added pair-code pack/unpack roundtrip + alignment regression.

### Update (2026-04-07, delta-table acceleration)

Kept the same exact envelope-dominance objective but replaced per-candidate envelope grid comparison with a
precomputed threshold table:

- `gear_optimizer/solver/exact_skyline.py`
  - Added `_build_envelope_dominance_lut(...)` that precomputes `delta_max[p,q]` and `delta_min[p,q]` from the
    exact `G_p(L)` closure curves.
  - Updated `_reduce_same_stat_envelope_frontier_with_codes(...)` to test dominance by the theorem threshold
    `base_diff >= delta_max[p,q]` plus strictness checks, instead of building and comparing full envelope vectors for
    every pair.
  - Reused a single per-song LUT across both local gear-envelope prune and combined pair-envelope prune.

- `tests/test_exact_skyline_envelope_reduction.py`
  - Added equivalence tests proving:
    - pairwise LUT dominance decisions match full envelope curve comparisons,
    - group-wise reduced survivors match brute-force envelope dominance pruning.

This update is performance-focused only; retained/removed states are exact-equivalent to the prior implementation.

### Update (2026-04-07, theorem-5 response-dominance revision)

Tested the direct theorem-5 idea (cross-stat response-function dominance), then revised it into a production-safe exact pass.

Direct form challenge:

- The exact theorem-5 condition needs a response matrix over `gear x lambda` classes.
- Running this unbounded is too expensive on large charts (`|G| * |Lambda|` can be very large).

Implemented revision (exact when active, bounded when large):

- `gear_optimizer/solver/exact_skyline.py`
  - Added mini lambda-class collapse helper:
    - `_collapse_mini_response_classes_with_codes(...)`
    - collapses minis by `(CM,FM,FT,FF)` and keeps the max-base representative per class (exact class max).
  - Added exact response skyline helpers:
    - `_evaluate_response_matrix_exact(...)`
    - `_response_dominance_keep_mask(...)`
    - `_theorem5_response_prune_gears_exact(...)`
  - Wired theorem-5 pruning immediately after local gear-envelope pruning and before combined skyline.
  - Added bounded guardrails (env-configurable):
    - `EXACT_SKYLINE_THEOREM5_MAX_EVALS` (default `65536`)
    - `EXACT_SKYLINE_THEOREM5_MAX_GEARS` (default `768`)
  - Behavior:
    - if within bounds: apply exact theorem-5 response dominance and prune dominated gears,
    - if out of bounds: skip with status reason and keep prior exact pipeline unchanged.

- `tests/test_exact_skyline_envelope_reduction.py`
  - Added theorem-5 regressions for:
    - lambda-class collapse choosing the max-base representative,
    - response dominance mask equivalence vs brute force,
    - prune behavior with mocked response matrix,
    - budget-guard skip behavior.

This revision keeps exactness guarantees while avoiding unbounded pre-evaluation cost.

## Consequences

Positive:

- The production exact skyline path now uses a strictly stronger exact objective than the previous raw gear skyline.
- Fewer gear points reach the combined skyline/product evaluation stages.
- This directly reduces downstream GPU work for the `exact_skyline` outer engine.

Tradeoffs:

- There is a small CPU-side envelope comparison cost before combined skyline evaluation.
- The theorem-5 response pass is bounded; on very large surfaces it is intentionally skipped to preserve throughput.
- The reduction is currently local to equal `(CM, FM, FT, FF)` groups; it does not yet solve the broader cross-stat
  post-gem sufficient-frontier problem.

## Verification

- `python -m py_compile gear_optimizer/solver/exact_skyline.py tests/test_exact_skyline_envelope_reduction.py`
- `python -m pytest -q tests/test_exact_skyline_envelope_reduction.py`
- `python -m pytest -q tests/test_exact_skyline_routing_switch.py`
- `<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe -m pytest -q tests/test_exact_skyline_vs_ga_real_song.py -s`
- `<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe -m ruff check gear_optimizer/solver/exact_skyline.py tests/test_exact_skyline_envelope_reduction.py`
- `<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe -m pytest -q tests/test_exact_skyline_envelope_reduction.py`
- `<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe -m pytest -q tests/test_exact_skyline_routing_switch.py`

## References

- Production solver: `gear_optimizer/solver/exact_skyline.py`
- Research origin: `Research/EXACT_OUTER_SKYLINE_NO_GA.md`
- Chronological session log: `docs/CODEX_WORKLOG.md`
