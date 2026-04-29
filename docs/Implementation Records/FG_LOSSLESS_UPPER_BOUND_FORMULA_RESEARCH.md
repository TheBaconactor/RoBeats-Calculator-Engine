# FG Lossless Upper-Bound Formula Research

Date: 2026-04-28

## Context

The Near-Winner Frontier verifier showed that FG-overall winners live in a
small frontier:

```text
FG-overall iff fg_lift > base_deficit
```

The open question is whether there is a fast production-safe formula that can
prove:

```text
candidate_base_score + max_possible_fg_lift <= current_top_base_score
```

If true, FG can be skipped for that candidate without changing the product
objective.

## Production Domain

The formula must cover the same domain as production FG:

- full or configured FT/FF search surface,
- forced-Great count choices,
- timing-envelope carry when present,
- exact inner PP/CM/FM/OV gem re-optimization,
- current selected element and primary/secondary colors.

Any fixed-stat or current-gem-only formula is not lossless for production.

## Rejected Simple Ceilings

### Absolute all-fever stat ceiling

Tested shape:

```text
UB_score =
  score if every note were fever
  with independently maximized PP/CM/FM/color stats
```

Verdict:

- lossless-shaped but far too loose,
- filtered `0 / 3,621` sampled rows across `80` songs,
- not worth production work.

Reason: independent stat maxima ignore the 90-gem budget and make every
candidate look potentially competitive.

### Budget-respecting super-surface ceiling

Tested shape:

```text
UB_score =
  exact inner solve over a synthetic fever surface
  that places all bounded fever notes in best-scoring positions
```

Small scratch result:

```text
357 rows across 12 songs
filtered 0 rows
runtime ~348s in scalar Python
```

Verdict:

- safer than independent stat maxima,
- still too loose when the fever surface over-approximates coverage,
- not "super fast" in this naive CPU shape.

### Base-dominance lift ceiling with loose added-note bands

Important improvement:

For any gem allocation `a`:

```text
normal_score(loadout, a) <= exact_base_score(loadout)
```

Therefore:

```text
FG_score(loadout, a, config)
  <= exact_base_score(loadout)
   + newly_fevered_note_value_delta(loadout, a, config)
```

This removes the need to upper-bound the whole re-optimized absolute score.
Only the additional value from notes that FG can newly turn into fever matters.

A loose recursive added-note band was still too broad:

```text
51 rows across 4 songs
median added-note bound: 225
median lift bound: ~8.2M
filtered 0 rows
```

For comparison, the retained DB surface has:

```text
base_deficit median: 150,911
base_deficit p99:    1,058,926
base_deficit max:    2,146,396
```

Any useful bound must often land below a few hundred thousand points. A
multi-million-point bound is lossless but operationally useless.

## Promising Formula

The viable lossless formula is:

```text
UB_lift(loadout) =
  max over production FT/FF pairs p:
    max over legal PP/CM/FM/OV allocations g:
      score_delta(AddedEnvelope(song, p), g)
```

Then:

```text
if exact_base_score(loadout) + UB_lift(loadout) <= current_top_base_score:
    FG cannot become overall for this loadout
```

Where `AddedEnvelope(song, p)` is an exact superset of notes that any
production forced-Great config can make fever when those notes are not fever in
the same pair's zero-forced base timeline.

This is lossless because:

1. exact base score already dominates every normal-timeline gem allocation for
   the loadout,
2. penalties are ignored, so the bound can only overestimate FG,
3. the added-note envelope is a superset of all possible newly fevered notes,
4. the inner allocation maximization respects the real 90-gem budget.

## Added-Fever Envelope DP

A small exact DP prototype over one `(song, FT, FF)` pair tracks reachable
post-fever indices by section and maximizes newly fevered notes against the
zero-forced base mask.

Scratch anchor results:

```text
Body (Hard) by Rutra:
  FT/FF stats 40/40: 47 newly feverable notes
  FT/FF stats 80/80: 63
  FT/FF stats 160/160: 48

Endless Rain (Hard) by seatrus (feat. marumoko):
  FT/FF stats 40/40: 39 newly feverable notes
  FT/FF stats 80/80: 43
  FT/FF stats 160/160: 70
```

This is much tighter than the loose 225-note recursive band and is the first
research direction that looks both lossless-shaped and potentially useful.

## Shadow Verifier: Top-K / Added-DP Bounds

Follow-up verifier:

```text
tools/verify/validate_fg_added_value_bound.py
```

This verifier tested DeepSeek's suggested two-stage direction against retained
DB rows:

- `topk_total`: production-safe but deliberately loose. It bounds newly fevered
  value by taking the top-K note bonuses where `K` is a safe total-FG-fever-note
  upper bound over the full legal FT/FF surface.
- `topk_minus_base_diagnostic`: unsafe diagnostic. It subtracts base fever note
  count from the K bound without a proven overlap guarantee.
- `added_dp_base_current`: diagnostic only. It runs an added-fever DP at the
  row's current stat point / base FTFF pair, so it does not cover production
  FT/FF + gem re-optimization.
- `added_dp_base_ceiling`: diagnostic only. It uses the base FTFF pair and a
  conservative score ceiling, still not the full production surface.

Large stratified run:

```text
python tools\verify\validate_fg_added_value_bound.py --per-bucket 20 --max-rows-per-song 51 --json
```

Result:

```text
Rows: 3,621 across 71 chart-backed songs
Observed FG-overall rows: 41

topk_total:
  skipped 0 / 3,621
  false skips 0 / 41
  bound p50 38,085,087
  bound p90 71,225,146

topk_minus_base_diagnostic:
  skipped 0 / 3,621
  false skips 0 / 41
  bound p50 12,586,464
  bound p90 22,752,939

added_dp_base_current:
  skipped 5 / 3,621
  false skips 0 / 41
  bound p50 1,482,738
  bound p90 3,638,520

added_dp_base_ceiling:
  skipped 0 / 3,621
  false skips 0 / 41
  bound p50 2,138,368
  bound p90 5,393,232

base_deficit:
  p50 169,444
  p90 394,486
  p99 885,428
```

Interpretation:

- DeepSeek's cheap top-K proposal is not breakthrough-grade in this repo shape.
  The only production-safe verifier variant filtered nothing.
- Even the unsafe subtract-base-count diagnostic filtered nothing, so the
  problem is not just a missing overlap proof.
- The exact added-fever DP direction is also not enough by itself if penalties
  are ignored and score stats are independently ceilinged. Median bounds remain
  multi-million while median deficits are only hundreds of thousands.
- The fixed-current-stat DP can be very strong only when it includes the exact
  fixed stat point and/or penalties; existing futility validation showed that
  such a fixed-stat certificate creates false skips once production gem
  re-optimization is allowed.

## Why This Is Not Ready Yet

The formula needs a maintained verifier before production discussion:

- exact DP must preserve enough note-position information, not just added-note
  count, because head/body/ramp positions have different value,
- exact or admissible budget-respecting premium maximization must replace
  independent stat maxima,
- full FT/FF production mode means the envelope should be cached per song and
  pair surface, ideally GPU-shaped,
- validation must prove zero misses against persisted FG-overall rows and
  report real filter rate.

## Current Verdict

Do not ship a production skip yet.

The cheap "sort top-K note values" path is not a major breakthrough candidate.

The only remaining plausible formula family is narrower and harder:

```text
exact base dominance
+ exact production FT/FF added-fever DP
+ budget-coupled premium maximization
+ admissible forced-Great penalty lower bound
```

The rejected formula family is:

```text
absolute score ceiling,
broad scalar fever-note ceiling,
top-K total fever-note ceiling,
fixed-stat/current-gem-only certificates
```

The next implementation should not be another scalar proxy. If this thread is
continued, target a penalty-aware, budget-coupled DP verifier over reduced
FT/FF surface keys and compare its cost directly against production FG work.
