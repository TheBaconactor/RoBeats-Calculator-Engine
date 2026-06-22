# zero_ms FG paired-base score fix

## Problem

The on-demand `zero_ms` FG replay could emit a `ForceGreats` row whose config was effectively no-op
(`NonFever1=0`, `NonFever2=0`) while the visible score/gems were the base/meta result. Dark Sheep
Hard T5 exposed this as the FG leaderboard rank #1 showing the base zero_ms score.

## Broken invariant

A row is only a valid FG leaderboard row when the exact forced-greats score beats the exact non-FG
score for the same loadout, tier, timing model, and served gem/stat surface.

The `zero_ms` gem re-solve violated that in two places:

1. `build_fixed_timing_fg_replays` materialized the paired `BaseScore` from the gem-less seed stats.
   A no-force surface with resolved gems could score like base (~112M) but compare against the
   zero-gem score (~43M), so it looked like a valid FG improvement.
2. `compute_team_buff_tier_leaderboards` then overwrote the fixed-timing witness `BaseScore` with a
   replay from the persisted perfect-window FG snapshot. That reintroduced the same bad pairing even
   after the materializer contract was corrected.

## Fix

`solver/fg_response_scoring/fixed_timing.py::build_fixed_timing_fg_replays` now derives paired base
rows from `result.stats`, the resolved gem-full stats returned by the exact FG search. The
materialized `BaseScore` and `BaseStats` therefore describe the same stat surface that is served and
scored as FG.

`helpers/song_helpers/team_buff_tiers.py::compute_team_buff_tier_leaderboards` now treats the
`zero_ms` force witness as the paired-base authority. It filters any zero_ms FG row whose
`Score <= BaseScore` before ranking and never recomputes zero_ms `fg_base_score` from the persisted
perfect-window FG snapshot.

No feature flag or alternate path was added. This is a contract correction at the materialization
boundary.

The website on-demand cache schema was bumped separately (`v11` -> `v12`) so existing bad cached
FG zero_ms buckets are invalidated on deploy.

## Verification

- New regression test:
  `tests/test_fixed_timing_fg_replay_paired_base.py::test_fixed_timing_fg_replay_pairs_base_to_resolved_stats`
- New regression test:
  `tests/test_zero_ms_fg_leaderboard_paired_base.py::test_zero_ms_fg_leaderboard_uses_force_witness_base_score`
- Manual reproduction before fix:
  Dark Sheep Hard T5 `mode=fg&timing_mode=zero_ms` recomputed cold in ~82s and produced score
  `112366848`, config `0/0`, with paired base incorrectly sourced from gem-less stats.
- Expected after fix:
  no-op FG surfaces compare equal to base and are filtered out by the existing `fg_score > fg_base_score`
  tier-batch serializer invariant.
