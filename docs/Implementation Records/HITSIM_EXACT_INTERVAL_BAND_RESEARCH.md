# HITSim Exact Interval-Band Research

- Date: 2026-04-09
- Scope: research-only exact ceiling timeline solver (`codex/research-2`)
- Status: implemented and benchmarked in research; not merged to `main`

## Context

The research exact timeline solver had already gained a large win from merged-exit interval
union, but it still expanded every activation carry in `[act_lo, act_hi]` and then merged the
resulting boundary intervals. That left exact full-grid estimates in the multi-minute range.

During follow-on research, the local first-exit scan was re-derived from the actual survivor
semantics instead of the earlier over-approximate band scan.

## Decision

Replace per-activation-carry exit enumeration with an exact interval-band rule:

1. For a fixed activation group `s` and activation-carry interval `[act_lo, act_hi]`,
   feasible carries that first-exit at a given later group form a single interval.
2. The exact lower survivor threshold is driven only by the propagated lower bound constant.
3. The exact exit upper threshold at group `g` is driven only by `group_high[g]`.

This yields a direct merged boundary enumerator:

- survivor lower recurrence:
  - `L_g = max(group_low[g], L_{g-1} - delta_g)` with clamping to `[_CARRY_L, _CARRY_U]`
- first-exit activation-carry interval at group `g`:
  - `r in [max(act_lo, survive_lo), min(act_hi, group_high[g] + D_g - d_ms)]`
- merged exit-carry interval at group `g`:
  - `[max(L_g, r_lo - D_g + d_ms), group_high[g]]`

where `D_g = group_base[g] - group_base[s]`.

The canonical research solver now uses this exact interval-band enumerator for both:

- `solve_ceiling_signature_exact_countmax_from_grouped_windows(...)`
- `solve_ceiling_signature_exact_scoremax_from_grouped_windows(...)`

## Correctness Notes

### Actual first-exit semantics

The interval-band rule was validated against corrected pointwise first-exit enumeration:

- new helper:
  - `_enumerate_first_exit_point(...)`
- new direct helper:
  - `_enumerate_first_exit_boundary_intervals_from_activation_band(...)`

The direct helper matched exact pointwise enumeration on:

- a deterministic smoke chart test
- `2000` random local activation states each on:
  - `00 (Hard)`
  - `Bopeebo`
  - `[@_@]`

### Tiny exhaustive verifier

The tiny exhaustive verifier was corrected to use actual first-exit semantics rather than the
older over-approximate "forced later boundary" local scan. After that correction:

- `charts=1104`
- `cases=13248`
- `dp_mismatch=False`
- `scoremax_ne_countmax=False`

### Proxy objective ordering

The earlier version of this record stated the proxy objective alignment too strongly.

What is actually proven is:

- `build_score_bonus_prefix(...)` exactly matches the production comparator minus the all-normal
  baseline.
- for the production constants, the resulting increment is an affine weighted-slot objective:
  - `42500 * total_fever + 680 * weighted_position_sum`
  - where `weighted_position_sum = sum(head fever positions) + 100 * body_fever`

What is **not** proven here:

- global equivalence between production proxy ordering and the countmax lexicographic objective on
  unconstrained signature space.

That broader theorem is false on unconstrained signatures; see:

- `docs/Implementation Records/HITSIM_PROXY_ORDER_THEOREM_AND_LIMITS.md`

## Measured Impact

Compared with the prior merged-exit-only solver:

- `00 (Hard)`:
  - proxy exact: `542.719s -> 21.462s` (`25.29x`)
  - countmax: `501.715s -> 20.759s` (`24.17x`)
- `Bopeebo`:
  - proxy exact: `272.004s -> 9.138s` (`29.77x`)
  - countmax: `267.350s -> 9.276s` (`28.82x`)
- `Baby I Don't Care`:
  - proxy exact: `309.501s -> 12.945s` (`23.91x`)
  - countmax: `309.276s -> 12.561s` (`24.62x`)
- `[@_@]`:
  - proxy exact: `643.112s -> 29.380s` (`21.89x`)
  - countmax: `655.954s -> 28.401s` (`23.10x`)

Deep hostile probe (`[@_@]`, 20 cells, 50 score triples):

- proxy exact full-grid estimate: `677.390s -> 57.967s`
- countmax full-grid estimate: `625.123s -> 27.540s`
- `proxy_match_all=True`
- `invariant=True`
- `countmax_match_all=True`

## Consequences

1. This is another genuine algorithmic collapse, not a micro-optimization.
2. Exact full-grid runtime moved from multi-minute territory down to tens of seconds on the
   sampled hard songs.
3. The exact solver is still slower than production GA, but it is now close enough that a
   native/GPU exact implementation looks materially more plausible.
4. The local state transition is now simple enough to reason about in a GPU/native port:
   the heavy per-carry expansion has been replaced by interval arithmetic over boundary groups.

## Artifacts

- `artifacts/verify/tiny_ceiling_scoremax_vs_countmax_smoke_intervalband.json`
- `artifacts/verify/tiny_ceiling_scoremax_vs_countmax_default_intervalband.json`
- `artifacts/bench/hitsim_exact_timeline_feasibility_multi_intervalband.json`
- `artifacts/bench/hitsim_exact_timeline_feasibility_deep_atat_intervalband.json`

## Follow-on

1. Rework the research state-space bench around the new interval-band helper so the counters
   reflect the new algorithm instead of the historical per-carry expansion.
2. Prototype a native/GPU exact countmax cell kernel around the interval-band rule.
3. Decide whether the older over-approximate local scan should be preserved anywhere for
   historical comparison, or removed entirely from research tooling.
