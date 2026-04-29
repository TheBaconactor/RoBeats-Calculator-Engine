# Near-Winner Frontier Validation

Date: 2026-04-28

## Context

The target theorem is:

```text
Only candidates with base_deficit <= conservative_possible_lift
need FG-overall attention.
```

Where:

```text
base_deficit = best_base_score_for_song - candidate_base_score
```

This aligns directly with the product objective:

```text
FG-overall iff FG_lift > base_deficit
```

The important distinction is that this theorem is exact only if
`conservative_possible_lift` is a true upper bound over the same domain that
production FG can search, including gem re-optimization. If the lift estimate is
only a heuristic, the frontier is a ranking/filtering experiment, not a safe
production reduction.

## Verifier

Added:

```text
tools/verify/validate_near_winner_frontier.py
```

The verifier is offline/shadow-mode only. It reuses the breakpoint analyzer's
retained base-row records and checks candidate possible-lift bounds against
observed FG-overall rows:

```text
in_frontier = base_deficit <= possible_lift(candidate)
miss = observed_fg_overall and not in_frontier
```

Any miss means the tested bound is not safe for production filtering.

Tested bound families:

- `oracle_actual_lift`: actual persisted FG lift for that row; not usable in
  production, but proves the theorem shape.
- `observed_song_best_lift`: max retained FG lift for the song; also not
  production-usable, but shows the potential of song-local caps.
- `global_constant`: fixed score cap.
- `breakpoint_weighted`: current weighted breakpoint proxy.
- `timeline_weighted`: FT/FF timeline-only weighted proxy.
- `score_floor_weighted`: PP/CM/FM score-floor weighted proxy.

## Larger Stratified Result

Command:

```powershell
python tools\verify\validate_near_winner_frontier.py --per-bucket 40 --max-rows-per-song 51 --max-delta 30 --margins 0,50000,100000,200000,500000 --scales 1,2,4,8 --json
```

Sample:

```text
7,650 rows across 150 songs
88 observed FG-overall rows
```

Key results:

```text
oracle_actual_lift, margin 0:
  kept 222 / 7,650
  outside frontier 97.10%
  missed FG-overall 0 / 88

observed_song_best_lift, margin 0:
  kept 540 / 7,650
  outside frontier 92.94%
  missed FG-overall 0 / 88

global_constant 100,000:
  kept 2,502 / 7,650
  outside frontier 67.29%
  missed FG-overall 1 / 88

global_constant 200,000:
  kept 4,528 / 7,650
  outside frontier 40.81%
  missed FG-overall 0 / 88

timeline_weighted scale 1:
  kept 2,954 / 7,650
  outside frontier 61.39%
  missed FG-overall 2 / 88

breakpoint_weighted scale 1:
  kept 4,772 / 7,650
  outside frontier 37.62%
  missed FG-overall 2 / 88

score_floor_weighted scale 1:
  kept 3,277 / 7,650
  outside frontier 57.16%
  missed FG-overall 12 / 88

score_floor_weighted scale 2:
  kept 4,608 / 7,650
  outside frontier 39.76%
  missed FG-overall 2 / 88
```

The main counterexample for cheap constant/proxy bounds was:

```text
Body (Hard) by Rutra
base_deficit = 105,289
fg_lift      = 2,034,419
```

This row proves that a small global deficit cap, even one that looked safe in a
smaller sample, is not enough.

## Interpretation

The theorem shape is very strong:

- oracle actual lift filters `97.10%` of sampled rows with no missed FG-overall,
- observed song-best lift filters `92.94%` of sampled rows with no missed
  FG-overall.

That means the frontier concept is pointed at the right object. The hard part is
constructing a cheap possible-lift bound that is truly conservative.

Current cheap breakpoint proxies are not exact:

- They can miss rare large-lift rows such as `Body (Hard) by Rutra`.
- Scaling or adding large margins can remove misses empirically, but that turns
  the frontier into an empirical heuristic unless the margin is proven.
- A broad constant like `200,000` had zero misses in this sample but kept
  `59.19%` of rows, and still is not a proof.

## Decision

Do not implement production filtering from the current cheap frontier proxies.

The Near-Winner Frontier remains the best theorem direction, but the next step
must be a real upper-bound proof, not another ranking heuristic.

## Next Proof Target

A production-safe bound must dominate:

- fever timeline shift,
- carry-time extension,
- note-density/timeline-count changes,
- PP/CM/FM floor changes,
- FT/FF gem reallocation,
- full gem re-optimization inside the configured FG search domain.

The most promising form is:

```text
possible_lift =
    max_timeline_extra_fever_notes * max_reoptimized_fever_premium
  + max_score_floor_gain_from_reoptimized_stats
  - min_great_penalty
```

Then production filtering would only be valid when:

```text
possible_lift <= base_deficit
```

Until that same-domain upper bound exists, use this verifier for shadow
validation only.
