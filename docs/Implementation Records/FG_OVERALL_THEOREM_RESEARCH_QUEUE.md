# FG-Overall Theorem Research Queue

Date: 2026-04-28

## Context

Recent combo-ramp and breakpoint experiments showed an important distinction:

```text
FG-improving != FG-overall
```

A candidate is FG-improving if Force Greats improves that candidate over its
own base score. It is FG-overall only if the FG result beats the song's current
best base winner.

The raw breakpoint selector found more FG-improving rows but lost FG-overall
rows. That makes it unsuitable as a global replacement. Future theorem work
should target FG-overall directly.

## Research Candidates

### 1. Near-Winner Frontier Theorem

Claim target:

```text
Only candidates with base_deficit <= conservative_possible_FG_lift need FG-overall attention.
```

Where:

```text
base_deficit = best_base_score_for_song - candidate_base_score
```

Why this is interesting:

- It matches the real objective: can this candidate cross the top-base line?
- It can preserve default score-ranked safety while allowing a tiny additive
  exploration lane.
- It can be used as ranking, budget allocation, or eventually a conservative
  skip only if the upper bound is proven safe.

What would make it safe:

- The possible-lift bound must dominate actual FG lift over the same domain that
  production FG searches.
- It must include gem re-optimization effects or explicitly bound them.
- It must be validated against replayed FG results, not only persisted scores.

Status:

- Best current theory candidate.
- Shadow verifier added in `tools/verify/validate_near_winner_frontier.py`.
- Validation record: `NEAR_WINNER_FRONTIER_VALIDATION.md`.
- Do not implement as production skip until a same-domain upper-bound proof exists.

### 2. Deficit-Dominance Bound

Claim target:

```text
If upper_bound_FG_lift(candidate) < base_deficit, then candidate cannot be FG-overall.
```

Why this is interesting:

- This is the cleanest safe-reduction shape.
- It directly avoids the mistake of optimizing for FG-improving rows.
- Even a weak but cheap bound could be useful as a shadow-mode certificate.

What would make it safe:

- The bound must be conservative for:
  - fever timeline movement,
  - carry-time extension,
  - great penalty effects,
  - PP/CM/FM floor changes,
  - FT/FF gem reallocation,
  - overflow/element effects.

Known risk:

- The earlier fixed-stat DP certificate failed because gem re-optimization can
  create lift outside the fixed-stat domain.

Status:

- Promising, but harder than it looks.
- Start in verifier/shadow mode only.

### 3. Fever-Coverage Upper Bound

Claim target:

```text
max_FG_lift <= max_extra_fever_notes * max_fever_premium + combo_ramp_correction - min_great_penalty
```

Why this is interesting:

- It turns timeline structure into a cheap, interpretable upper bound.
- It can explain why body-dominant sparse surfaces rarely produce FG-overall.
- It can reuse the combo-ramp identity:
  pure fever-shift gain vanishes when entering/leaving notes are both in the
  constant body-value region.

What would make it safe:

- Need a conservative bound for extra fever notes from both shift and carry-time
  effects.
- Need a conservative bound for the maximum score premium per note after gem
  re-optimization.
- Need to avoid assuming equal stats when FG can reallocate gems.

Status:

- Good candidate for a cheap upper-bound component.
- Not enough alone for exact skipping.

### 4. Top-Base Invariance Theorem

Claim target:

```text
For some song/loadout regimes, every FG-overall winner is contained in the top-K base-ranked frontier.
```

Why this is interesting:

- It would justify keeping the current default selector.
- It can identify when extra exploration lanes are unnecessary.
- It turns the current empirical observation into a theorem: score-near
  candidates are safest for FG-overall.

What would make it safe:

- Need a bound showing candidates outside top-K cannot close their base deficit.
- Equivalent to a deficit-dominance bound applied to the cutoff candidate.

Status:

- Probably useful as a corollary of Near-Winner Frontier or Deficit-Dominance.
- Not a standalone proof unless it has a safe FG-lift upper bound.

### 5. Landscape Ruggedness Predictor

Claim target:

```text
Classify songs/loadout frontiers as sparse/body-dominant or breakpoint-rich before choosing an FG strategy.
```

Why this is interesting:

- Easy maps and short maps often have chunkier timeline breakpoints.
- Dense-window or extended maps can still have useful late-body timeline changes.
- Sparse/body-dominant songs like Endless Rain should not receive much
  breakpoint exploration pressure.

What would make it useful:

- Must predict FG-overall opportunity, not just FG row count.
- Should use cheap chart/frontier features:
  - retained FG row density,
  - base-deficit distribution,
  - ramp-start presence,
  - valuable breakpoint magnitude,
  - note-density clusters near fever boundaries.

Status:

- Useful for strategy selection and observability.
- Not a correctness certificate.

## Current Decision

Keep production selection at the default score/protected frontier:

```text
FG_CandidateSelectorMode =
```

Do not enable raw breakpoint ranking or deficit-aware breakpoint ranking
globally. The next research pass should prioritize the Near-Winner Frontier and
Deficit-Dominance Bound because they optimize for FG-overall directly.
