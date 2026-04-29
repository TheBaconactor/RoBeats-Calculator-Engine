# Proven Pruner Research: CEM, Timing Dominance, and FG Frontier

Date: 2026-04-28
Branch: `research-probability-analysis`

## Goal

Research candidates that could become proven faster winner finders or safe pruners:

- stronger exact/lossless pruning,
- CEM as a waste pruner rather than a winner finder,
- admissible FG/frontier pruning,
- timing/stat dominance extensions.

Production behavior remains unchanged unless a candidate has proof or very strong
shadow validation plus an explicit experimental gate.

## Findings

### Timing Dominance Is Not Safe

Naive dominance of higher Fever Time / Fever Fill Rate is unsafe. Real chart samples
show score drops when FF increases, because fever windows move onto worse note
positions. Easy charts also showed FT-adjacent drops.

Artifact:

- `artifacts/runcheck/proven_pruner_research/timing_monotonicity_sample.json`

Example:

- `2NITE (Hard) by nanobii`, fixed FT `0`, FF `0 -> 1`: score dropped by `129,625`.
- `A Starry Night and a Single Flower (Easy) by seatrus`, fixed FF `40`, FT `0 -> 1`:
  score dropped by `1,831`.

Verdict: do not broaden current timing-neutral dominance into raw timing dominance.

### Current Lossless Pre-Pool Pruning Is Already Material

Sample over 90 chart/color contexts:

- gear rows before pruning: mean `267.0`
- gear rows after pruning: mean `140.47`
- mini rows after song/color filtering and exact pruning: mean `31.62`

Artifact:

- `artifacts/runcheck/proven_pruner_research/pool_pruning_sample.json`

Verdict: current exact pruning is valuable, but the obvious FT/FF dominance extension
is invalid.

### CEM As Plateau Waste Hygiene

After removing the implicit `0.15` immigrant-rate floor, CEM is cleaner:

- default CEM at depth `50` reduced duplicate-genome ratio in `5 / 6` cases,
- it had one base-score gain, one base-score loss, and four ties at depth `50`,
- it still lagged standard on base score in `5 / 6` cases at depth `25`,
- delayed CEM with refresh `50` truly matches standard before refresh, but did not
  reduce duplicates meaningfully until depth `200`.

Artifact:

- `artifacts/runcheck/cem_delayed_plateau_no_immigrant_floor/summary.json`

Verdict: CEM remains experimental. It is not a proven faster winner finder, but it
may be useful as optional duplicate hygiene around plateau depths.

### Simple FG Deficit Cutoffs Are Unsafe

Full-bucket DB shadow validation covered:

- `102,255` retained rows,
- `2,005` chart-backed songs,
- `771` observed FG-overall rows.

Simple deficit thresholds miss real FG-overall rows:

- `deficit > 100k`: `33` observed misses,
- `deficit > 200k`: `8` observed misses.

Direct DB inspection found FG-overall rows with deficits over `500k`, including
`Embraced by the Flame (English version) (Hard)`, where retained rows more than
`500k` below base still became FG-overall due to multi-million FG lift.

Artifacts:

- `artifacts/runcheck/proven_pruner_research/near_winner_frontier_p1000_r51.json`
- `artifacts/runcheck/proven_pruner_research/fg_futility_certificate_p200_r51.json`

Verdict: no global base-deficit cutoff is safe.

### FG Frontier Bounds Are Promising But Not Proven

Oracle controls prove the frontier shape is powerful:

- `oracle_actual_lift`, margin `0`: would prune `97.47%` with zero misses, but it
  requires knowing the exact lift, so it is not a production shortcut.
- `observed_song_best_lift`, margin `0`: would prune `92.93%` with zero misses, but
  it uses observed DB knowledge and is not production-usable.

Practical proxy bounds with zero observed misses on this snapshot exist, but coverage
is small and they are not proven conservative:

- `breakpoint_weighted`, margin `100k`, scale `2`: pruned `7.13%`.
- `score_floor_weighted`, margin `200k`, scale `2`: pruned `5.25%`.
- `timeline_weighted`, margin `200k`, scale `4`: pruned `3.97%`.

Verdict: these are shadow-mode candidates only. The next proof target is a real
admissible possible-lift bound, not a constant or heuristic proxy.

## Current Promotion Verdict

No new pruner is ready for production promotion yet.

Safe to keep:

- existing exact song-aware pre-pool pruning,
- exact unique/effective-genome dedupe,
- default-off CEM as an experimental duplicate hygiene mode with no immigrant-floor
  side effect.

Rejected for production:

- raw FT/FF timing dominance,
- simple base-deficit cutoffs,
- CEM as a faster winner finder.

Next best research target:

- a proven admissible FG possible-lift bound that is tighter than current top-K /
  added-fever bounds and accounts for rare giant-lift songs.
