# ADR: Timing-Lane Exact Response Signature Prune

Date: 2026-05-12

Status: Accepted

## Context

The mini response and product response-envelope prunes were originally blocked whenever `Fever Time` or `Fever Fill Rate` gems contributed to the song's primary or secondary lane base. That blocker was correct for the old certificate because the old response envelope tracked timing reachability and remaining non-timing budget, but not the lane value created by the timing gems themselves.

Songs such as `2 Sides (Hard)` use primary/secondary lanes where Beat/Vibe timing gems can affect lane base. Those songs are counterexamples to applying the non-lane-aware mini/product response certificates, not counterexamples to response-envelope pruning in general.

## Decision

Add a conservative exact-signature timing-lane certificate.

For a start timing cell and legal timing spend `(g_ft, g_ff)`, define:

```text
remaining = 90 - g_ft - g_ff
lambda = w_ft * g_ft + w_ff * g_ff + w_ov * remaining
```

where `w_ft`, `w_ff`, and `w_ov` are the exact lane-base values of one FT gem, one FF gem, and one overflow gem for the active primary/secondary lanes.

For every start cell, build the nondominated set of strict response points:

```text
(exact_base_timeline_pack, remaining, lambda)
```

under same-pack dominance with no less `remaining` and no less `lambda`. Two timing cells have the same lane-aware response signature only when those complete nondominated response-point sets are byte-identical.

Production now uses this signature in two places:

- Mini response prune: timing-lane-active mini `A` may remove mini `B` only when every actual gear timing cell gives the same lane-aware exact response signature and `A` has no-worse `CM/FM/base`.
- Product response prune: timing-lane-active product candidate `x` may remove `y` only inside the same lane-aware exact response signature, with sorted `PP` order and no-worse `CM/FM/lane` dominance.

The older timing-lane blocker remains the default for callers of `_fast_path_blocker(...)`; the new path must opt into lane-aware signatures explicitly.

## Safety Shape

The certificate is intentionally stricter than the maximal response-envelope theorem. It does not attempt cross-signature containment for timing-lane-active cells. It only prunes by exact equality of the visible timing response menu, including lane opportunity.

This is lossless for base scoring because any deleted candidate can be replayed by the kept candidate with:

```text
same exact base-visible timing frontier pack
same remaining non-timing gem budget
same timing-gem/overflow lane-base opportunity
no-worse PP/CM/FM/base-lane state
```

The score formula is monotone in `PP`, `CM`, `FM`, and lane base for a fixed exact timing frontier. The implementation keeps the existing monotone-reference and overflow-dominance gates.

This certificate is still base-scope. It does not claim to prune full FG-all search; current production FG remains exact over the retained base top-k candidate set.

## Runtime Guardrail

The exact timing-lane signature can be expensive on huge frontiers. Production therefore uses resource caps as safe no-ops, not fallback scoring paths:

```text
response product candidates > 2,000,000 -> keep all candidates
mini unique start cells > 5,000 -> keep all minis / local pairs
```

No candidate is removed when a cap trips. This preserves score correctness and prevents the theorem from creating runtime regressions on large timing-lane songs.

The rejected uncapped experiments on `2 Sides (Hard)` were score-stable but not production-shaped:

```text
uncapped mini timing-lane exact signature: pruned 20 minis, but hot wall regressed to about 54.98s
uncapped product timing-lane exact signature: pruned 2,463,052 products, but response prune CPU was about 121.82s and wall regressed to about 174.43s
```

The shipped behavior keeps the proof path for small/medium timing-lane cases and refuses the large case instead of hiding a slowdown behind a flag.

## Verification

- `python -m py_compile gear_optimizer/solver/response_envelope_prune.py gear_optimizer/solver/mini_response_prune.py tests/test_response_envelope_prune.py tests/test_mini_response_prune.py`
- `python -m ruff check gear_optimizer/solver/response_envelope_prune.py gear_optimizer/solver/mini_response_prune.py tests/test_response_envelope_prune.py tests/test_mini_response_prune.py`
- `python -m pytest -q tests/test_response_envelope_prune.py tests/test_mini_response_prune.py tests/test_timing_response_antichain.py tests/test_gpu_local_search_cm_plateau.py tests/test_gpu_exact_inner_registry_solve.py`

Profile guardrails:

- `00 (Hard) by garlagan`, `artifacts/profile/timing_lane_signature_20260511_00`: hot wall `18.855s`; base/FG parity `34,253,930` / `34,259,925`; mini and response prunes still certify normally; `base_pair_eval_gpu` `8.465s`.
- `2 Sides (Hard) by KepoWorld`, `artifacts/profile/2_sides_hard_20260511`: score `29,850,000`; mini/response timing-lane exact-signature prunes no-op by resource cap; wall `47.226s`; `base_pair_eval_gpu` `24.572s`.

## Consequences

Positive:

- timing-lane songs are no longer theorem-incomplete; they have a lossless exact-signature certificate
- large timing-lane songs do not pay the rejected CPU scan cost
- no production default-off flag was added

Tradeoffs:

- the shipped certificate is conservative; it does not prune large `2 Sides` mini/product frontiers yet
- completing the broader cross-signature containment theorem still needs a better index before it is production-safe
