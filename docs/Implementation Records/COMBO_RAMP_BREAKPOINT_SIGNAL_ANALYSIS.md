# Combo Ramp + Breakpoint Signal Analysis

Date: 2026-04-28

## Context

After validating that fixed-stat FG futility certificates are not globally safe
for production skipping, we revisited the safer use of combo-ramp identity:

```text
Combo ramp identity alone = not enough to delete FG.
Combo ramp identity + conservative upper bound = safe reduction.
Combo ramp identity + mutation/ranking = faster convergence heuristic.
```

The goal here is not to filter candidates out. The goal is to determine whether
cheap ramp/breakpoint features can guide ranking, scheduling, or mutation
pressure without affecting correctness.

## Implementation

Added an offline analyzer:

```text
tools/verify/analyze_combo_ramp_breakpoints.py
```

It computes, per retained base row:

- baseline fever starts,
- whether fever starts touch the combo-ramp region (`start < 100`),
- nearest `FT`/`FF` stat delta that changes the timeline signature,
- persisted FG lift / FG-overall status from SQLite.

The tool is CPU/offline only and does not submit GPU work.

## Anchor Samples

Command:

```powershell
python tools/verify/analyze_combo_ramp_breakpoints.py --song "Endless Rain (Hard) by seatrus (feat. marumoko)" --song "Daydream (Album Extended ver.) [EXTENDED CUT] (Hard) by RiraN" --song "Space Battle (Easy) by F-777" --max-rows-per-song 51 --max-delta 30
```

Summary:

```text
Endless Rain bucket (`medium`, 51 rows):
  fg_improves=0
  fg_overall=0
  ramp_rows=0

Rich sample rows (`Daydream` + `Space Battle`, 102 rows):
  fg_improves=62
  fg_overall=32
  ramp_rows=51
```

Interpretation:

- `Endless Rain (Hard)` is body-dominant in its retained base surface; combo-ramp
  features explain why the pure ramp-shift path is uninteresting.
- `Space Battle (Easy)` contributes the strong ramp-touch Easy behavior.
- `Daydream` shows that large positive FG lift can still happen with late starts,
  so ramp identity alone cannot explain all useful FG. Timeline density/count
  changes matter.

## Stratified Sample

Command:

```powershell
python tools/verify/analyze_combo_ramp_breakpoints.py --per-bucket 20 --max-rows-per-song 30 --max-delta 30
```

Summary:

```text
checked: 2,130 rows across 71 songs

zero:   fg_improves=0,   fg_overall=0,  ramp_rows=193
tiny:   fg_improves=9,   fg_overall=0,  ramp_rows=234
medium: fg_improves=38,  fg_overall=2,  ramp_rows=141
rich:   fg_improves=257, fg_overall=37, ramp_rows=323
```

The `nearest FT/FF breakpoint` feature was too sensitive in this first version:
almost every row is near *some* timeline signature change. That means raw
"nearest breakpoint" is not useful enough by itself.

## Findings

Useful:

- Combo-ramp touch is a good explanatory feature for Easy/ramp-rich cases.
- Body-dominant retained surfaces like `Endless Rain (Hard)` are identifiable.
- Breakpoint features should be used for ranking/mutation pressure, not deletion.

Not useful enough yet:

- Raw nearest timeline-signature delta. It fires too often because tiny FT/FF
  changes can alter a low-level signature without producing valuable score lift.
- Raw nearest "valuable" timeline delta is still too common. Fever-count/body-count
  changes are often one stat point away on long songs.
- Raw nearest PP/CM/FM score-floor delta is also too common: integer floors often
  change with a single stat point.

Next feature target:

```text
valuable breakpoint magnitude / direction
```

Instead of "is a breakpoint nearby?", compute the size and direction of the
score-relevant change:

- nearest FT/FF delta that changes fever note count,
- nearest delta that moves fever start across note 100,
- nearest delta that moves fever into a denser note cluster,
- nearest CM/PP/FM floor threshold that changes per-note score.
- score-weight those deltas by affected notes, not merely by distance.

## Valuable-Distance Probe

The analyzer was extended to distinguish:

- raw timeline signature breakpoint distance,
- "valuable" FT/FF breakpoint distance (`total_fever`, `head_fever`,
  `body_fever`, or ramp-boundary crossing changes),
- PP/CM/FM score-floor breakpoint distance.

Command:

```powershell
python tools/verify/analyze_combo_ramp_breakpoints.py --per-bucket 20 --max-rows-per-song 30 --max-delta 30
```

Result:

```text
checked: 2,130 rows across 71 songs

zero:   near_value=495/540, score_floor=540/540
tiny:   near_value=600/600, score_floor=600/600
medium: near_value=420/420, score_floor=420/420
rich:   near_value=569/570, score_floor=570/570
```

Conclusion: distance alone is too broad to drive ranking. It can still guide a
mutation direction, but only if paired with a magnitude score such as:

```text
expected_delta_score(axis) / stat_delta
```

or a sparse "large breakpoint" gate.

## Magnitude / Direction Probe

The analyzer was extended again to compute weighted marginal breakpoint
features:

- `FT`/`FF` timeline marginal: positive fever-note changes weighted by the
  row's fever score premium, with extra weight for head/ramp-boundary movement.
- `PP`/`CM`/`FM` score-floor marginal: per-note floor deltas weighted by the
  number of normal and fever notes affected.
- split summaries for blended marginal, timeline-only marginal, and score-floor
  marginal.

Command:

```powershell
python tools/verify/analyze_combo_ramp_breakpoints.py --per-bucket 20 --max-rows-per-song 30 --max-delta 30
```

Result:

```text
checked: 2,130 rows across 71 songs

zero:   top10% blended fg+=0/54,  overall=0, avg_lift=-7,190.556
tiny:   top10% blended fg+=0/60,  overall=0, avg_lift=-8,073.033
medium: top10% blended fg+=5/42,  overall=0, avg_lift=-100,309.929
rich:   top10% blended fg+=27/57, overall=3, avg_lift=7,546

rich top10% timeline-only:   fg+=26/57, overall=3, avg_lift=4,094.035
rich top10% score-floor-only: fg+=21/57, overall=2, avg_lift=10,974.333
```

Interpretation:

- Magnitude/direction is more meaningful than raw distance, especially in rich
  FG landscapes.
- It still lights up sparse buckets because large generic score-floor mass does
  not imply FG usefulness.
- The feature is therefore suitable for mutation pressure or candidate ranking
  experiments, not for deletion or exact reduction.
- `Endless Rain (Hard)` remains correctly uninteresting from this lens: the
  anchor run had `fg_improves=0`, `fg_overall=0`, and no ramp-start rows.

## Candidate-Ranking Experiment

Added:

```text
tools/bench/bench_breakpoint_candidate_ranking.py
```

This is an offline equal-budget experiment. It does not run production, does
not submit GPU work, and does not change candidate selection. It asks whether
different orderings capture more persisted FG-improving or FG-overall rows at
the same top-K rows per song.

Command:

```powershell
python tools\bench\bench_breakpoint_candidate_ranking.py --per-bucket 20 --max-rows-per-song 30 --max-delta 30 --budgets 3,5,10
```

Overall result:

```text
top-3 score_rank:        fg_rows=29,  overall=21
top-3 timeline_marginal: fg_rows=44,  overall=12
top-3 score2+timeline:   fg_rows=34,  overall=19

top-5 score_rank:        fg_rows=52,  overall=27
top-5 timeline_marginal: fg_rows=79,  overall=17
top-5 score2+timeline:   fg_rows=61,  overall=23

top-10 score_rank:        fg_rows=101, overall=30
top-10 timeline_marginal: fg_rows=146, overall=24
top-10 score2+timeline:   fg_rows=137, overall=28
```

Bucket detail:

```text
medium top-10 score_rank:        fg_rows=9,  overall=2
medium top-10 score2+timeline:   fg_rows=24, overall=2

rich top-10 score_rank:          fg_rows=92,  overall=28
rich top-10 score2+timeline:     fg_rows=111, overall=26
rich top-10 score2+blended:      fg_rows=111, overall=27
```

Interpretation:

- Pure breakpoint ordering captures substantially more FG-improving rows.
- Pure breakpoint ordering loses FG-overall rows because it can demote
  base-near winners.
- Hybrid "preserve top score rows, fill the rest by breakpoint magnitude" is
  safer and looks promising, especially for medium/rich buckets.
- This still should not replace production selection yet. The next safe
  production-facing experiment would be a feature-flagged secondary exploration
  lane or mutation pressure, not deletion and not a hard reorder of the only FG
  queue.

## Feature-Flagged Protected Hybrid Lane

Implemented an explicit selector mode:

```text
FG_CandidateSelectorMode = breakpoint_hybrid
```

Scope:

- Preserves the existing top base-score slice (`LOADOUTS_PER_SONG_LIMIT`) before
  adding breakpoint-directed candidates.
- Uses timeline-breakpoint magnitude only when song timeline context is
  available (`calc_song` + `ref_arrays`).
- Does not silently fall back to the existing FG proxy when breakpoint context is
  missing. If enabled without `calc_song`/`ref_arrays` or explicit
  `_breakpoint_marginal` values, it fails loudly.
- Does not delete candidates globally and does not skip FG.
- Default code path is unchanged. The repo `config.ini` was returned to blank
  after the initial result showed this objective was too broad for production.

Implementation:

- `gear_optimizer/helpers/song_helpers/fg_candidate_selector.py`
- `gear_optimizer/pipeline/song_processor.py`
- `gear_optimizer/solver/native_inflight_stages.py`
- `gear_optimizer/solver/genetic.py`

Notes:

- CPU-side selectors can compute breakpoint priority from `Stats`, or from
  `BaseStats + GemCounts` when full `Stats` are absent.
- The GPU-native 3D decode path has a matching protected hybrid ordering for
  non-GPU-selected payloads.
- GPU-selected payloads now re-run selector only for this explicit mode so the
  protected hybrid lane is actually active in live GPU-native runs.
- Existing default selection parity tests still pass.

Verification:

```powershell
python -m pytest -q tests\test_fg_candidate_selector.py tests\test_fg_candidate_selector_regression.py --tb=short
python -m pytest -q tests\test_decode_gpu_native_ga_runs_payload.py::test_decode_gpu_native_ga_runs_payload_matches_fg_candidate_selector tests\test_gpu_ga_fg_candidate_selection.py::test_gpu_ga_fg_selection_matches_cpu_candidate_selector --tb=short
python -m ruff check gear_optimizer\helpers\song_helpers\fg_candidate_selector.py gear_optimizer\solver\genetic.py gear_optimizer\pipeline\song_processor.py gear_optimizer\solver\native_inflight_stages.py tests\test_fg_candidate_selector.py
```

## Decision

Do not implement deletion changes.

Do not enable raw `breakpoint_hybrid` by default. It optimizes for
FG-improving exploration, which can trade away FG-overall winners.

The corrected target is deficit-aware breakpoint value:

```text
breakpoint_value - base_deficit_to_best_base
```

New offline result:

```text
top-10 score_rank:              fg_rows=101, overall=30
top-10 deficit_aware_timeline:  fg_rows=119, overall=31
top-10 deficit_aware_blended:   fg_rows=112, overall=31
```

Larger stratified check:

```text
checked: 7,650 rows across 150 songs

top-3 score_rank:                 fg_rows=70,  overall=49
top-3 deficit_aware_blended:       fg_rows=84,  overall=53

top-5 score_rank:                 fg_rows=115, overall=59
top-5 deficit_aware_blended:       fg_rows=128, overall=60

top-10 score_rank:                fg_rows=211, overall=73
top-10 deficit_aware_blended:      fg_rows=243, overall=70

top-20 score_rank:                fg_rows=416, overall=84
top-20 deficit_aware_blended:      fg_rows=468, overall=82
```

Interpretation:

- Deficit-aware ranking is directionally better than raw breakpoint ranking.
- It improves FG-overall capture at very small budgets (`top-3`, `top-5`) in
  this sample.
- It still loses FG-overall capture at wider budgets (`top-10`, `top-20`),
  especially in rich buckets.
- Therefore it is not yet good enough to replace score-rank selection globally.

Current recommendation: keep `FG_CandidateSelectorMode` blank. If this is
pursued further, it should be a narrow budget-capped overlay, not a replacement
of the normal score-rank frontier.
