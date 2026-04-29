# FG Breakpoint Research Synthesis

Date: 2026-04-28

## Context

This record summarizes the recent theorem and experiment thread around:

- sparse FG landscapes,
- combo ramp identity,
- FG futility certificates,
- breakpoint-directed mutation/ranking,
- valuable breakpoint distance,
- the FG-improving vs. FG-overall distinction.

It is the short "start here" map. The detailed records are linked at the end.

## Core Model

For a candidate loadout `l`:

```text
B(l)       = base score for loadout l
F(l)       = best Force Greats score for loadout l
lift(l)    = F(l) - B(l)
B_max      = best base score for the song
deficit(l) = B_max - B(l)
```

FG can become the song's overall winner only when:

```text
lift(l) > deficit(l)
```

This distinction explains most of the confusing observations:

- `FG-improving`: FG improves the candidate's own base score.
- `FG-overall`: FG beats the song's current best base score.

The optimizer must care about FG-overall. A selector that finds more
FG-improving rows but loses FG-overall rows is not a safe production win.

## Rugged Landscape Theory

The score function is a staircase:

- fever fill uses discrete `ceil(...)` transitions,
- combo/perfect/fever/great values use `floor(...)`,
- Easy maps often have fewer notes and larger effective plateau regions,
- random mutation can spend many generations moving around without changing
  score.

The useful theory is not "increase search depth." It is:

```text
same search depth, better mutations toward score breakpoints
```

Breakpoint-directed mutation can be useful because it points search toward the
nearest score-relevant cliff instead of wandering on a flat plateau. This is a
convergence heuristic, not a correctness certificate.

## Combo Ramp Identity

The combo ramp identity is exact for one component of FG:

```text
If both entering and leaving notes are in the constant body-combo region,
pure fever-shift gain from swapping those notes is zero.
```

This is useful for explaining sparse/body-dominant songs such as
`Endless Rain (Hard) by seatrus (feat. marumoko)`.

It is not enough to delete FG because total FG lift can also come from:

- carry-time extension,
- timeline count/density changes,
- PP/CM/FM floor changes,
- FT/FF gem re-optimization,
- full gem re-optimization inside the production FG domain.

Therefore:

```text
Combo ramp identity alone = not enough to delete FG.
Combo ramp identity + conservative upper bound = safe reduction candidate.
Combo ramp identity + mutation/ranking = convergence heuristic.
```

## FG Futility Certificate Verdict

We tested the tempting cheap skip:

```text
skip if exact fixed-stat DP lift <= base_deficit - margin
```

This failed as a global production certificate:

- margin `0`: `59` false skips in the stratified sample,
- margin `50,000`: `3` false skips,
- larger margins had no false skips in that sample, but sample-passing is not
  proof.

The reason is domain mismatch. Fixed-stat DP does not cover production gem
re-optimization. A production skip must upper-bound the same domain production
FG can search.

Decision:

```text
No production FG skip from fixed-stat DP or combo-ramp-only logic.
```

## Endless Rain Anchor

`Endless Rain (Hard) by seatrus (feat. marumoko)` is a good sparse-surface
example:

```text
best_base:        47,102,747
best_fg replayed: 46,647,059
retained FG rows: 4
top base rows:    fixed-stat DP lift = 0 in the checked sample
```

This song validates the intuition that some hard/body-dominant landscapes are
FG-doomed in practice. It does not validate a global exact skip rule.

## Valuable Breakpoint Distance

Raw breakpoint distance was too broad:

- almost every row is near some FT/FF timeline signature breakpoint,
- almost every row is near some PP/CM/FM score-floor breakpoint,
- distance alone did not separate useful FG-overall candidates.

The more meaningful feature was breakpoint magnitude/direction:

```text
expected_score_delta(axis) / stat_delta
```

That feature is useful for ranking and mutation pressure, especially in rich
FG landscapes. It is still not a deletion proof.

## Candidate Selector Experiment

Offline equal-budget ranking showed the trap:

```text
top-10 score_rank:              101 FG-improving, 30 FG-overall
top-10 timeline_marginal:       146 FG-improving, 24 FG-overall
top-10 score2_then_blended:     136 FG-improving, 29 FG-overall
```

Raw breakpoint ranking improved exploration but hurt the true objective by
demoting candidates close to the top base score.

Deficit-aware ranking was better aligned:

```text
top-10 score_rank:              211 FG-improving, 73 FG-overall
top-10 deficit_aware_blended:   243 FG-improving, 70 FG-overall
```

At small budgets it helped FG-overall in the sample, but at wider budgets it
still lost FG-overall rows. That is not globally safe enough for default
production selection.

Decision:

```text
FG_CandidateSelectorMode =
```

Keep the default score/protected selector. The off-by-default
`breakpoint_hybrid` mode remains a research hook, not the recommended default.

## What This Can Be Used For

Safe uses now:

- offline analysis,
- mutation pressure,
- ranking experiments,
- observability/classification of sparse vs. rich FG surfaces,
- theorem mining for upper bounds.

Unsafe uses now:

- deleting FG candidates,
- globally replacing score-ranked candidate selection,
- claiming throughput gains by deferring FG debt,
- using FG-improving capture as the product metric.

Potential future safe-reduction route:

```text
If proven_upper_bound_FG_lift(l) <= deficit(l), skip FG for l.
```

The hard part is proving that the upper bound dominates production FG including
gem re-optimization.

## Best Next Theorem Target

The strongest next direction is the Near-Winner Frontier / Deficit-Dominance
family:

```text
Only candidates with base_deficit <= conservative_possible_FG_lift
need FG-overall attention.
```

This targets the right product question directly:

```text
Can this candidate actually cross the top-base line?
```

Start as a shadow verifier, not production behavior.

## Related Records

- [FG_LANDSCAPE_SPARSE_SURFACE_THEORY.md](FG_LANDSCAPE_SPARSE_SURFACE_THEORY.md)
- [FG_FUTILITY_CERTIFICATE_THEORY.md](FG_FUTILITY_CERTIFICATE_THEORY.md)
- [FG_FUTILITY_CERTIFICATE_VALIDATION.md](FG_FUTILITY_CERTIFICATE_VALIDATION.md)
- [PLATEAU_BOUNDARY_CONVERGENCE_THEORY.md](PLATEAU_BOUNDARY_CONVERGENCE_THEORY.md)
- [COMBO_RAMP_BREAKPOINT_SIGNAL_ANALYSIS.md](COMBO_RAMP_BREAKPOINT_SIGNAL_ANALYSIS.md)
- [FG_OVERALL_THEOREM_RESEARCH_QUEUE.md](FG_OVERALL_THEOREM_RESEARCH_QUEUE.md)
