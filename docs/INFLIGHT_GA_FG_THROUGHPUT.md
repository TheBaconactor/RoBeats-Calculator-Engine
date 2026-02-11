# In-Flight GA+FG Throughput Architecture

This document describes the native in-flight architecture changes focused on improving **integrated GA+FG throughput** (not GA-only throughput).

## Product contract

GA and FG are one product outcome.

- Throughput wins are valid only if FG is also kept current.
- A run that increases songs/hour by deferring FG is not considered an improvement.

## Implemented architecture wins

1. Continuous dual-queue dispatch (reduced GA burstiness)
- File: `gear_optimizer/solver/native_inflight_orchestrator.py`
- Added `InFlight_ContinuousGABurst` / `INFLIGHT_CONTINUOUS_GA_BURST` (default `2`).
- In continuous mode, GA submits are now capped per scheduler cycle so FG gets frequent dispatch opportunities.

2. FG slot partitioning (hard reserve instead of implicit single-slot behavior)
- File: `gear_optimizer/solver/native_inflight_orchestrator.py`
- Added:
  - `InFlight_FGSlotReserve` / `INFLIGHT_FG_SLOT_RESERVE` (absolute)
  - `InFlight_FGSlotReserveRatio` / `INFLIGHT_FG_SLOT_RESERVE_RATIO` (default ratio `0.20`)
- GA queue depth now respects an FG slot partition to reduce slot-pressure oscillation.

3. Adaptive continuous FG submit budget
- File: `gear_optimizer/solver/native_inflight_orchestrator.py`
- Added:
  - `InFlight_FGAdaptiveSubmit` / `INFLIGHT_FG_ADAPTIVE_SUBMIT` (default `true`)
  - `InFlight_FGAdaptiveMaxBurst` / `INFLIGHT_FG_ADAPTIVE_MAX_BURST` (default `3`)
- FG submit budget now scales by queue pressure/aging/slot pressure rather than defaulting to one job in most continuous-mode cycles.

4. Fused FG breakpoint+solve promotion for in-process runs
- File: `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`
- Added:
  - `INFLIGHT_FORCE_FUSED_FG` (default force-on in in-process native inflight)
  - dynamic default for `FG_FUSED_PAYLOADS_PER_REQUEST` (`64/96/128` by FG worker count)
- Fused path remains opt-out via `INFLIGHT_FORCE_FUSED_FG=0` (then legacy `FG_FUSE_BREAKPOINTS_SOLVE` behavior applies).

## Regression coverage

Added/updated tests:

- `tests/test_native_inflight_continuous_scheduler.py`
  - continuous GA burst parsing
  - adaptive FG submit parsing
  - FG slot reserve parsing
  - adaptive FG submit budgeting behavior
- `tests/test_fg_gpu_dispatch_fused_policy.py`
  - fused-policy default/opt-out behavior
  - default fused payload batch sizing

Also validated related suites:

- `tests/test_native_inflight_backlog_threshold_compat.py`
- `tests/test_native_inflight_stages_db_prefetch.py`
- `tests/test_loadout_builder_db_query_gate.py`
- `tests/test_gpu_service_fused_submit.py`
- `tests/test_gpu_executor_native_ga_and_fused_batching.py`
- `tests/test_native_inflight_fg_persistence_consistency.py`

## A/B benchmark protocol (integrated)

Control settings used:

- `SONG_QUEUE_LIMIT=100`
- `SONG_REPEATS=1`
- fixed `GA_SEED=12345`
- `HumanHitSim.Enabled=false` (in benchmark config)
- separate DB per run
- stage profile enabled for integrated FG accounting

Baseline knobs (legacy-like behavior):

- `INFLIGHT_CONTINUOUS_GA_BURST=32`
- `INFLIGHT_FG_SLOT_RESERVE=1`
- `INFLIGHT_FG_ADAPTIVE_SUBMIT=0`
- `INFLIGHT_FG_ADAPTIVE_MAX_BURST=1`
- `INFLIGHT_FORCE_FUSED_FG=0`
- `FG_FUSED_PAYLOADS_PER_REQUEST=64`

Candidate knobs (new architecture):

- `INFLIGHT_CONTINUOUS_GA_BURST=2`
- `INFLIGHT_FG_SLOT_RESERVE_RATIO=0.20`
- `INFLIGHT_FG_ADAPTIVE_SUBMIT=1`
- `INFLIGHT_FG_ADAPTIVE_MAX_BURST=3`
- `INFLIGHT_FORCE_FUSED_FG=1`
- `FG_FUSED_PAYLOADS_PER_REQUEST` unset (dynamic default)

## Latest measured result (February 9, 2026)

Artifact: `artifacts/bench/inflight_ga_fg_ab/ab_summary.json`

Average across two baseline and two candidate runs:

- Baseline: `6839.89 songs/hour`
- Candidate: `6910.12 songs/hour`
- Delta: `+1.03%`

Integrated GA+FG guardrails:

- `fg_run_count=100` in all runs (FG executed for all queued songs)
- `deferred_fg_count=0` in all runs
- `avg_slot_block_count` improved from `17.5` -> `0.0`

Interpretation:

- Throughput improvement is modest but positive on this workload.
- FG completion was preserved (no FG debt deferral).
- Slot-pressure behavior improved materially.

## Stable-vs-current comparison (February 9, 2026)

Baseline reference:

- git commit: `4231274` (`Harden persistence and DB smoke regression tests`)
- worktree path used: `../Gear Optimizer - stable-4231274`

Artifact:

- `artifacts/bench/inflight_ga_fg_ab/stable_vs_current_summary.json`

Average songs/hour (100 songs, repeats=1, fixed seed):

- Stable (`4231274`): `2355.89 songs/hour`
- Current baseline mode: `6839.89 songs/hour` (`+190.33%` vs stable)
- Current candidate mode: `6910.12 songs/hour` (`+193.31%` vs stable)
- Candidate vs current baseline: `+1.03%`

Integrated FG guardrails:

- `fg_run_count=100` in stable and current runs (FG executed for all songs)
- no FG deferral events observed in benchmark logs

## DB persistence audit (stable and current)

Artifact:

- `artifacts/bench/inflight_ga_fg_ab/db_persistence_audit_vs_stable.json`

Checks performed:

- SQLite `PRAGMA integrity_check`
- `songs.best_score` / `songs.best_fg_score` consistency with persisted T5 leaderboard rows
- FG leaderboard invariant (`fg_score > score` and force payload present)
- JSON payload parse/score consistency in `details_json` and `force_details_json`
- duplicate `(song_name, team_buff, loadout_hash)` rows

Result:

- no persistence integrity issues detected in audited DBs
- all T5 song-level score invariants passed (`songs_best_score_underrun_t5=0`, `songs_best_fg_score_underrun_t5=0`)
- all FG-table invariants passed (`fg_table_non_improving_rows=0`, `fg_table_missing_force_rows=0`)

Note:

- `songs_*_underrun_any_tier` is non-zero by design because `songs` tracks canonical (T5) song leaderboards,
  while `team_buff_loadouts` includes multiple team-buff tiers that can exceed T5 values.
