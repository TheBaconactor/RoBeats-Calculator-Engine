# HITSim Proxy Order Theorem and Limits

- Date: 2026-04-09
- Scope: research-only exact ceiling timeline analysis on `codex/research-2`
- Status: proven for the production proxy comparator; no change to `main`

## Context

The interval-band research record noted that the production proxy comparator looked aligned with the
countmax lexicographic objective because:

- head bonuses were strictly increasing, and
- the body bonus matched the last head bonus on the production `head_len=100` path.

That observation was not strong enough to prove the broader claim
`production proxy score ordering == countmax lexicographic ordering`, and in fact that broader
claim is false on unconstrained signature space.

This record pins down the exact theorem we can prove and the exact boundary where the proof stops.

## Proven Statements

### 1. `build_score_bonus_prefix(...)` exactly matches the production comparator minus the all-normal baseline

Let:

- `S(mask, body_fever)` be the production comparator `_ceiling_compare_score(...)`
- `S0` be the score of the same `(head_len, body_total)` signature with no fever bits and `body_fever=0`

Then:

- `S(mask, body_fever) - S0`

is exactly the bonus sum encoded by `build_score_bonus_prefix(...)`.

This was exhaustively checked over:

- `head_len = 0..10`
- `body_total = 0..4`
- every head mask in `0..(1 << head_len)-1`
- every feasible `body_fever`

### 2. The production proxy increment collapses to an affine weighted-slot objective

For the production constants:

- `base = 10000`
- `combo_mul = 2.6`
- `fever_mul = 5.25`

the baseline-subtracted increment is exactly:

- `42500 * total_fever + 680 * weighted_position_sum`

where:

- `total_fever = head_fever_count + body_fever`
- `weighted_position_sum = sum(head fever note 1-based positions) + 100 * body_fever`

So body fever behaves like a synthetic "head position 100" slot, regardless of the actual current
`head_len`.

### 3. Within a fixed total-fever stratum, production order is:

1. maximize `weighted_position_sum`
2. tie-break by `body_fever`
3. tie-break by later head mask bits (`m3, m2, m1, m0`)

This was exhaustively checked over:

- `head_len = 0..8`
- `body_total = 0..4`
- every feasible signature in each fixed-total-fever stratum

## Disproven Overclaims

### 1. Global countmax ordering is not a theorem on unconstrained signatures

Counterexample:

- `head_len = 100`
- `body_total = 0`
- signature A: fever only on head note 100
- signature B: fever only on head notes 1 and 2

Then:

- countmax lex order prefers B because `2 fever notes > 1 fever note`
- production proxy score prefers A:
  - A increment = `110500`
  - B increment = `87040`

So the broad theorem
`production proxy score ordering == countmax lexicographic ordering`
is false on unconstrained signature space.

### 2. Later-head lex order is not a theorem even with fixed total fever

Counterexample:

- `head_len = 5`
- `body_total = 0`
- total fever count fixed at `2`
- signature A: fever on notes `{1, 5}`
- signature B: fever on notes `{3, 4}`

Then:

- later-bit lex order prefers A (`10001b > 01100b`)
- production proxy prefers B because:
  - A weighted position sum = `1 + 5 = 6`
  - B weighted position sum = `3 + 4 = 7`

So later-bit lex order is only a tie-breaker after the weighted-position objective, not a primary
ordering rule.

## Consequences

1. The existing empirical result `scoremax == countmax` on actual sampled charts remains useful, but it is
   **not** explained by raw bonus monotonicity alone.
2. Any future proof of `scoremax == countmax` must use the feasible-set structure of real ceiling
   timelines, not just the production weight vector.
3. Proof-first work should now target:
   - structural constraints on feasible signatures,
   - frontier motif restrictions,
   - or chart-derived invariants that collapse the weighted-slot objective back to countmax on the
     reachable set.

## Reachable-Set Exhaustive Evidence

Although the unconstrained theorem is false, the reachable-set audits remain clean so far.

Using the exhaustive tiny-chart verifier on chart-feasible exact signatures:

### Default family

- charts: `1104`
- cells: `13248`
- score triples per cell: `6`
- results:
  - no DP mismatch
  - no `scoremax != countmax` winner mismatch
  - no pairwise reachable order reversal between countmax and scoremax

Artifact:

- `artifacts/verify/tiny_ceiling_reachable_order_audit.json`

### Expanded family

- charts: `16708`
- cells: `150372`
- score triples per cell: `6`
- results:
  - no DP mismatch
  - no `scoremax != countmax` winner mismatch
  - no pairwise reachable order reversal between countmax and scoremax

Artifact:

- `artifacts/verify/tiny_ceiling_reachable_order_expanded.json`

Interpretation:

- The unconstrained counterexamples are real, but they do not appear in the tested reachable tiny
  exact-signature families.
- On the tested reachable sets, the two objectives induce the same total order, not just the same
  winner.
- This is still evidence, not proof, but it materially strengthens the case that the missing theorem
  must come from feasible-set structure rather than from the raw proxy weights alone.

## Verification

- `python -m pytest tests/test_ceiling_exact_band_formula.py tests/test_ceiling_proxy_order_theorem.py -q`
- `python tools/verify/verify_tiny_ceiling_scoremax_vs_countmax.py --out artifacts/verify/tiny_ceiling_reachable_order_audit.json`
- `python tools/verify/verify_tiny_ceiling_scoremax_vs_countmax.py --max-groups 5 --max-total-notes 8 --group-sizes 1,2,3 --delta-ms 120,180,300,420 --fill-counts 1,2,3 --d-ms-values 150,500,1000 --out artifacts/verify/tiny_ceiling_reachable_order_expanded.json`

## Files

- `tests/test_ceiling_exact_band_formula.py`
- `tests/test_ceiling_proxy_order_theorem.py`
