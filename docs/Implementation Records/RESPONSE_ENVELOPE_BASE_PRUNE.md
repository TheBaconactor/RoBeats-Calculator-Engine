# ADR: Response-Envelope Base Candidate Prune

Date: 2026-05-11

Status: Accepted

## Context

The fixed-final-timing skyline only compares candidates inside identical final
`(FT, FF)` timing cells. That is lossless, but it misses candidates whose raw
timing cells differ while their purchasable timing response is still covered by
another candidate.

The expensive downstream phase is exact base scoring over the combined fixed
timing frontier. For `00 (Hard) by garlagan`, that frontier is about `9.0M`
candidates, and the exact GPU base pass remains the dominant cost.

## Decision

Add a conservative response-envelope prune between the combined fixed-timing
frontier and exact base scoring:

- new module: `gear_optimizer/solver/response_envelope_prune.py`
- mini-layer module: `gear_optimizer/solver/mini_response_prune.py`
- integration: `gear_optimizer/solver/exact_skyline.py`
- active only for the default retained-candidate `SKYLINE_FG_CANDIDATES=topk`
  scope
- skipped for `SKYLINE_FG_CANDIDATES=all` and `sample`, because those modes are
  used to inspect or expand the FG candidate universe

The prune is base-score lossless under this certificate:

1. The dominator is an actual candidate from the combined frontier.
2. It has no-worse `PP`, `CM`, and `FM`.
3. It has strictly higher lane-base under the same skyline lane convention.
4. For every timing response pack reachable by the deleted candidate, the
   dominator can reach a timing pack that dominates it with at least the same
   remaining non-timing gem budget.

Timing pack dominance is exact for base scoring:

```text
head_fever_mask_A is a superset of head_fever_mask_B
body_fever_A >= body_fever_B
body_normal_A <= body_normal_B
```

The implementation does not attempt the full quadratic response-envelope
containment relation. It uses two bounded, lossless owner indexes:

```text
(FT + FF, lane_base)
(min(FT, FF), lane_base)
```

Each index returns one real candidate from the `PP/CM/FM` suffix region. The
returned owner is then checked against the exact timing-envelope containment
  test before any deletion occurs. These owner indexes are incomplete but safe:
failure to find a witness keeps the candidate.

Add a second, earlier mini-team-layer prune after the gear frontier is known and
before gear x mini multiplication. Mini team `A` deletes mini team `B` only when:

1. `A` has no-worse mini `CM`, `FM`, and lane-base.
2. For every gear timing cell in the gear frontier, every exact base-visible
   timing pack reachable by `B` is reachable by `A` with at least the same
   remaining non-timing gem budget.

The proof is same-gear replay: any solution using `(gear, B)` can use the same
gear with `A`, buy the same fever timeline signature at no greater timing-gem
cost, and then replay the non-timing gem allocation under the same conservative
overflow/cap gates used by the product response prune. This exact-signature
certificate is stricter than full surface dominance. The stricter form is the
production implementation for the default retained-candidate top-k scope. The
mini pass is engineered as an exact-signature certificate, not a broad
surface-dominance scan: it uses a mini-specific timing response index, avoids the
product pack-dominance matrix, and prefilters pair checks by the zero-spend raw
timing signature before scanning response envelopes.

The broader surface-dominance mini certificate removed more teams but did not
pay for its scan cost in profiling, so it is not used by the production path.

Add a third mini-layer reduction at gear-cell granularity. For each gear timing
cell, the solver builds a local allowed-mini mask. The production certificate is
a fast sufficient form of local response-envelope dominance:

1. `A` has no-worse mini `CM`, `FM`, and lane-base than `B`.
2. For that gear timing cell, `A` and `B` have identical exact timing response
   envelopes, including every reachable exact base-visible timing pack and its
   remaining non-timing gem budget.

Then `(gear, B)` is removed for gear candidates in that timing cell. This is
lossless by the same same-gear replay proof: the replacement mini has the same
timing response menu for that cell and no-worse non-timing scoring inputs. The
full local containment theorem is broader, but the first implementation that
checked full per-cell containment was too expensive on `00 Hard`; the accepted
production version uses exact response-envelope equality as the cheap local
certificate and applies it as a vectorized pair filter after the fixed-timing
combined skyline, before product response pruning and exact base scoring.

The local filter is explicitly bounded: if the estimated local response matrix
would exceed `MAX_LOCAL_RESPONSE_MATRIX_CELLS`, the solver keeps the global
mini prune result and skips the local pair filter as a safe no-op. The mini
response contract is fixed at five return values; no compatibility branch for a
four-tuple return remains in production.

## Safety Gates

The fast certificate only runs when:

- `FT` and `FF` gems do not contribute to scoring lane base
- overflow lane gain is at least as good as any displaced non-timing stat gem
  lane gain
- `Perfect Points`, `Combo Multiplier`, and `Fever Multiplier` reference arrays
  are nondecreasing
- `Fever Multiplier >= 1` for all stat indices
- mini data still has zero mini `Perfect Points` when using the fast point-array
  state extraction path
- pre-gem timing/stat coordinates are nonnegative

If any gate fails, the reducer returns the original frontier unchanged.

## FG Scope

This is a base-score prune. It does not claim full FG dominance. The production
wire is deliberately conservative around FG research modes:

- `topk`: enabled, because the existing product surface already runs FG only on
  retained top base candidates
- `all`: skipped, preserving the full fixed-timing skyline frontier for
  skyline-to-FG research
- `sample`: skipped, preserving the configured sampling semantics

## Telemetry

The native FG summary records:

```text
combined_fixed_timing_candidates
combined_skyline_candidates
response_envelope_pruned
response_envelope_candidates_in
response_envelope_candidates_out
response_envelope_present_timing_cells
response_envelope_timing_packs
response_envelope_non_timing_owner_hits
response_envelope_timing_cover_hits
response_envelope_reason
mini_response_reason
mini_response_local_pruned_entries
mini_response_local_pair_pruned
```

Phase telemetry records:

```text
mini_response_prune_cpu
mini_response.timing
mini_response.query
mini_response.local_query
mini_response.local_pair_filter_cpu
response_envelope_prune_cpu
response_envelope.states
response_envelope.timing
response_envelope.index
response_envelope.query
base_pair_eval_gpu
```

## Verification

- `python -m pytest tests/test_mini_response_prune.py tests/test_response_envelope_prune.py tests/test_exact_skyline_frontier_contracts.py tests/test_fixed_timing_prefix_skyline.py tests/test_gear_skyline_gpu_parity.py -q`
- `python -m py_compile gear_optimizer/solver/solver_common.py gear_optimizer/solver/mini_response_prune.py gear_optimizer/solver/combined_skyline_sparse.py gear_optimizer/solver/response_envelope_prune.py gear_optimizer/solver/exact_skyline.py artifacts/profile/mini_response_20260511/profile_mini_response_prune.py artifacts/profile/response_envelope_prod_20260511/profile_response_envelope_prune.py`
- `python -m ruff check gear_optimizer/solver/solver_common.py gear_optimizer/solver/mini_response_prune.py gear_optimizer/solver/combined_skyline_sparse.py gear_optimizer/solver/response_envelope_prune.py gear_optimizer/solver/exact_skyline.py tests/test_exact_skyline_frontier_contracts.py tests/test_mini_response_prune.py tests/test_response_envelope_prune.py artifacts/profile/mini_response_20260511/profile_mini_response_prune.py artifacts/profile/response_envelope_prod_20260511/profile_response_envelope_prune.py`
- `00 (Hard) by garlagan` mini-layer before/after profile:
  - artifacts: `artifacts/profile/mini_response_20260511`
  - mini-disabled hot wall: `45.630s`
  - mini-enabled/default hot wall: `42.875s`
  - base score parity: `34,253,930`
  - FG score parity: `34,259,925`
  - mini teams: `151 -> 141`
  - local mini-cell entries removed: `73,326`
  - local pair filter removed: `1,009,036`
  - raw product: `46,320,911 -> 43,253,301`
  - combined fixed-timing frontier after local filter: `9,004,907 -> 7,747,347`
  - response-envelope frontier: `8,066,890 -> 6,868,926`
  - mini prune cost: `0.623s`
  - local response equality query: `0.055s`
  - local pair filter: `0.076s`
  - exact base scoring: `34.669s -> 31.735s`
  - net hot improvement after mini-prune overhead: `2.755s`
  - follow-up engineering pass: bulk bit-pack decode reduced
    `decode_candidate_ids_cpu` from `1.353s` to about `0.012s`; the mini
    response index now avoids the product pack-dominance matrix, and the raw
    zero-spend signature prefilter removes most failed envelope scans before the
    hot inner check.
  - rejected broad local containment pass: preserved scores but regressed hot
    wall to `118.743s` because local query cost `19.697s` and the masked sparse
    combined builder cost `60.207s`; this is why production uses exact local
    response-envelope equality until the full local containment relation has a
    better index.
- `00 (Hard) by garlagan` before/after profile:
  - artifacts: `artifacts/profile/response_envelope_prod_20260511`
  - disabled hot wall: `51.581s`
  - enabled hot wall: `48.490s`
  - base score parity: `34,253,930`
  - FG score parity: `34,259,925`
  - fixed-timing frontier: `9,004,907`
  - response-envelope frontier: `8,066,904`
  - candidates pruned: `938,003`
  - prune cost: `3.164s`
  - exact base scoring: `40.140s -> 34.805s`
  - net hot improvement: `3.091s`

## Consequences

Positive:

- deletes almost one million exact base candidates on `00 Hard`
- preserves base and default retained-candidate FG results in the measured run
- keeps all deletions tied to explicit witnesses, not telemetry heuristics

Tradeoffs:

- adds CPU work before exact GPU scoring
- the implemented owner strategy is intentionally incomplete and leaves many
  theoretically prunable candidates on the frontier
- full response-envelope containment remains a research problem for a better
  indexed certificate
