# FG Futility Certificate Validation

Date: 2026-04-28

## Context

We investigated whether a cheap Force Greats futility certificate can be applied
globally before FG dispatch:

```text
if certified_max_fg_lift(loadout) <= best_base_score(song) - base_score(loadout):
    skip FG for this loadout
```

The production requirement is strict: no certificate may filter a loadout that
could become the song's overall winner after FG.

## Candidate Tested

The tempting cheap candidate was:

1. Compute exact fixed-stat FG lift with `solve_force_greats_exact_dp(...)`.
2. Compare that fixed-stat lift against the loadout's base deficit.
3. Skip when `fixed_stat_lift <= deficit - margin`.

This is attractive because it includes exact timeline/carry semantics for one
resolved stat point and is much cheaper than full GPU FG. It is not, however,
the same domain as production FG because production can re-optimize gems.

## Validation Harness

Added:

```text
tools/verify/validate_fg_futility_certificate.py
```

The verifier is offline/shadow-mode only. It does not submit GPU work and does
not change production behavior. It stratifies songs by retained FG-row density
(`zero`, `tiny`, `medium`, `rich`), computes candidate skip decisions, and checks
whether any would-skip row has persisted FG context that beats `songs.best_score`.

## Results

Command:

```powershell
python tools/verify/validate_fg_futility_certificate.py --per-bucket 40 --max-rows-per-song 51 --margins 0,50000,100000,200000,500000 --json
```

Summary on `evolution.db`, `T5`:

```text
loadouts checked: 7,650
songs cached: 150

margin 0:
  would_skip: 7,516
  false_skips: 59

margin 50,000:
  would_skip: 6,182
  false_skips: 3

margin 100,000:
  would_skip: 4,999
  false_skips: 0 in this stratified sample

margin 200,000:
  would_skip: 3,009
  false_skips: 0 in this stratified sample

margin 500,000:
  would_skip: 569
  false_skips: 0 in this stratified sample
```

False-skip examples at margin `0` include rich/tiny songs such as:

- `Better Run (Hard) by Rutra`
- `Body (Hard) by Rutra`
- `00 (Hard) by garlagan`
- `-feeding- (Hard) by naruto2413 (feat. Aya Majiro)`
- `2 Sides by KepoWorld`
- `2NITE by nanobii`

## Endless Rain Sample

`Endless Rain (Hard) by seatrus (feat. marumoko)` remains a strong example of
the desired behavior:

```text
best_base: 47,102,747
best_fg:   46,647,059
retained FG rows: 4
top-51 base rows: fixed-stat DP lift = 0 for all checked rows
```

Its retained FG rows improve their paired loadouts but remain far below the
global base winner, so they are overall-doomed. This validates the theory for
that sparse surface, but not the global production rule.

## Decision

Do not enable a production FG skip based on fixed-stat DP or combo-ramp-only
logic.

Reasons:

- Fixed-stat DP ignores production gem re-optimization.
- Combo-ramp-only reasoning ignores timeline-count/density changes and gem
  re-optimization.
- Empirical safety margins can pass a sample but are not an exact certificate.

The only safe production path is a one-sided upper bound over the same domain
that production FG can search. Until that bound is proven and shadow-validated,
the verifier should remain a research/guardrail tool only.

## Follow-Up

Next viable target:

```text
cheap_upper_bound(loadout) >= actual_best_fg_lift(loadout)
```

The bound must include:

- timeline-count/density changes,
- timing-aware carry when enabled,
- gem re-optimization over the configured FG search domain,
- score penalties as an underestimate only when used in an upper bound.

Only when `cheap_upper_bound <= deficit` is proven should production skip FG.
