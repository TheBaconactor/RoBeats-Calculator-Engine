# In-Flight GA+FG Throughput Architecture

This document describes the native in-flight architecture changes focused on improving **integrated GA+FG throughput** (not GA-only throughput).

Important scope note:

- These in-flight changes are necessary for the canonical GPU-native GA->FG path.
- The measured gain from scheduling/residency alone is expected to be modest on many workloads.
- A larger FG speedup requires reducing actual FG work, not just reducing handoff overhead.

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
  - dynamic default for `FG_FUSED_PAYLOADS_PER_REQUEST` (`64/96/128` by FG worker count)
- In-process runs always use the fused breakpoint+solve request path.

5. Winner-only FG materialization
- Files:
  - `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`
  - `gear_optimizer/helpers/song_helpers/force_greats/result_application.py`
- GPU FG results are now collected per signature and only materialized onto retained winners at the end of the hot path.

6. Breakpoint-group reuse and explicit FG tiling
- File: `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`
- Added:
  - breakpoint-group cache for identical chart/regime + FT/FF + base-pair families
  - work-budget tiling for FG task batches and fused breakpoint payload batches
- This reduces repeated CPU scaffolding work and keeps FG requests more bounded under heavy workloads.

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

Baseline knobs (single-submit control behavior):

- `INFLIGHT_CONTINUOUS_GA_BURST=32`
- `INFLIGHT_FG_SLOT_RESERVE=1`
- `INFLIGHT_FG_ADAPTIVE_SUBMIT=0`
- `INFLIGHT_FG_ADAPTIVE_MAX_BURST=1`
- `FG_FUSED_PAYLOADS_PER_REQUEST=64`

Candidate knobs (new architecture):

- `INFLIGHT_CONTINUOUS_GA_BURST=2`
- `INFLIGHT_FG_SLOT_RESERVE_RATIO=0.20`
- `INFLIGHT_FG_ADAPTIVE_SUBMIT=1`
- `INFLIGHT_FG_ADAPTIVE_MAX_BURST=3`
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
- This result should be interpreted as an orchestration/scheduling win, not proof that the FG workload itself has been materially reduced.

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

## FG_CandidateLimit quality-drop declaration (February 13, 2026)

Goal:

- Determine whether lowering `FG_CandidateLimit` from `200` to `100` causes a *real* quality drop, using a reproducible A/B protocol with statistical decision gates.

Tools:

- A/B harness: `tools/bench/ab_fg_candidate_limit_quality.py` (writes `analysis_report.json` per cohort)
- Decision engine: `tools/bench/declare_fg_quality_drop.py` (consumes one or more `analysis_report.json` files and declares one of: `REAL_QUALITY_DROP_FOR_B`, `NO_REAL_QUALITY_DROP_FOR_B`, `INCONCLUSIVE`)

Controls used for this declaration runset:

- workload: `SONG_QUEUE_LIMIT=50`
- determinism: fixed `GA_SEED` per cohort, `HumanHitSim.Seed=12345`, `PYTHONHASHSEED=0`
- pipeline: sequential (`InFlightSongs=0` + `ALLOW_SEQUENTIAL_PIPELINE=1`)
- audit safety: `FG_DOWNLOAD_TOPK=0` (avoid reduced-download artifacts during quality audits)

Runset summary:

- 5 GA seeds, 5 reps each (25 paired A/B runs total, 50 songs each)
- Variants:
  - A: `FG_CandidateLimit=200`
  - B: `FG_CandidateLimit=100`

Declaration artifact:

- `artifacts/analysis/fg_quality_drop_decision_20260213_expanded2/quality_drop_declaration.json`

Result:

- Declaration: `NO_REAL_QUALITY_DROP_FOR_B`
- Evidence (pair-level total FG-gain delta A-B):
  - pairs: `25` (pos=7, neg=18, zero=0)
  - one-sided `p_no_drop=0.021643`
  - mean delta CI95: `[-74205.08, -6733.96]` (fully below 0)

Re-run (fresh declaration):

1) Produce cohort reports:

- `python tools/bench/ab_fg_candidate_limit_quality.py --config config.ini --song-limit 50 --reps 5 --a 200 --b 100 --ga-seed 1337 --song-repeats 1 --hitsim-seed 12345 --allow-sequential --inflight-songs 0 --fg-download-topk 0 --outdir artifacts/analysis/ab_fg_candidate_limit_superreliable_seed1337`

2) Declare using the decision engine:

- `python tools/bench/declare_fg_quality_drop.py --a 200 --b 100 --source-report artifacts/analysis/ab_fg_candidate_limit_superreliable_seed1337/analysis_report.json --outdir artifacts/analysis/fg_quality_drop_decision_<ts>`

## What This Does Not Solve Yet

The current in-flight throughput work improves queue behavior and keeps FG current, but it does not by itself guarantee a large single-song or end-to-end FG speedup.

Remaining limitations:

1. Residency alone does not reduce enough FG work
- The current architecture removes some request-boundary and slot-pressure waste.
- It does not yet aggressively reduce the number of FG tasks that must be evaluated.

2. Fused requests can still be bursty
- A larger fused FG submit removes queue bubbles, but it can still create long monopolizing GPU bursts.
- That improves orchestration while still leaving device-level smoothness suboptimal.

3. Slot reservation is still somewhat blunt
- Reserving capacity for FG protects correctness and keeps FG current.
- It can still over-reserve resources when long FG jobs are active.
- A permanently exclusive FG slot would make this worse by creating idle reserve during light load and backlog-driven backslotting during FG spikes.

4. Python-side grouping/materialization still caps upside
- As long as significant candidate grouping, signature construction, or result application remains on the host, the path is only partially GPU-native.

5. Wasted FG computation can still dominate
- Even with better residency and scheduling, throughput will stay capped if many near-equivalent FG candidates still go through full exact solve.
- Rebuilding equivalent breakpoint/scaffolding structures and processing non-winning rows is still wasted work.

## Next Architecture Steps For A Larger FG Win

To move from "modest positive throughput gain" to a materially faster canonical FG path, the next work should focus on workload reduction and bounded residency.

### 1. GPU-side FG frontier reduction

- Build signature buckets directly from the resident GA candidate table.
- Keep only bounded top-N and diverse representatives per bucket.
- Treat this as workload reduction, not just transport optimization.

Expected effect:

- less actual FG solve work
- fewer host-side candidates to materialize

### 1B. Eliminate redundant FG solve work

- identify near-equivalent candidates by FG signature class before exact solve
- reuse breakpoint/scaffolding structures where the `(chart, regime, signature bucket)` family is equivalent
- avoid running full FG solve on rows that cannot survive the bounded frontier

Expected effect:

- less wasted exact FG compute
- better throughput/hour than residency-only optimization

### 2. Tiled resident FG execution

- Replace mega fused FG submissions with bounded resident tiles.
- Keep global-best and top-K accumulators resident across tiles.
- Schedule tiles under explicit credit to reduce burstiness and head-of-line blocking.

Expected effect:

- smoother GPU usage
- lower latency jitter
- better fairness under queue pressure

### 3. Narrower FG residency ownership

- Move from blunt slot holds toward explicit ownership of only the FG-resident assets that must survive the GA->FG boundary.
- Keep full-slot holds only as compatibility or degraded mode where finer-grained residency is not yet stable.
- Do not treat a permanently exclusive FG slot as the destination architecture; prefer a bounded FG resident arena plus dynamic reserve/credit control.

Expected effect:

- lower slot pressure
- fewer residency-induced queue stalls

### 4. GPU-side top-K / keep-mask / signature packing

- Move grouping, retention, and keep-mask construction onto the GPU.
- Download only compact selected winner rows.
- Materialize full detail payloads only for rows that are actually persisted or surfaced.

Expected effect:

- less Python hot-path work
- better chance of a truly GPU-native FG pipeline

## Throughput-First Optimization Order

If the KPI is completed songs/hour with FG fully done, optimize in this order:

1. GPU-side FG frontier reduction
2. redundant FG solve elimination / scaffolding reuse
3. GPU-side keep-mask / top-K / winner-only materialization
4. tiled resident FG execution
5. narrower FG residency ownership

Reasoning:

- deleting FG work should beat merely rescheduling FG work
- deleting host work should beat larger fused bursts
- residency should support throughput, not become the goal by itself

## Practical Performance Expectation

The likely outcome of the remaining FG architecture work is:

- lower burstiness
- lower latency jitter
- better queue throughput under load
- moderate single-song speedups on FG-heavy workloads
- steadier queue rhythm without FG backlog accumulating behind a static exclusive slot

It should not be assumed that GA->FG residency by itself will reproduce the kind of structural speedup achieved by the deterministic HitSim rewrite. That earlier win came from deleting large amounts of duplicated work; the remaining FG win depends on deleting or compressing actual FG workload.

## Deferred Watchlist

These are not mandatory architecture changes right now. The current plan is to monitor them with tests, benchmark slices, and reporting so we only spend implementation time if the data shows a real issue.

1. VRAM pressure and spill behavior
- report peak resident usage, arena pressure, and any spill/degraded events during throughput runs

2. Determinism and parity drift
- keep seeded top-1 / FG top-1 parity reports across supported environments

3. Cache/reuse correctness
- add tests and counters for breakpoint/signature-family reuse hit/miss behavior

4. Tile cancellation / stale work
- report whether queued FG tiles continue running after they are no longer competitive or useful

5. GA admission vs FG backlog balance
- track FG queue age, slot-block time, and GA throttling behavior in throughput reports

6. Workload-class blind spots
- keep separate benchmark slices for FG-heavy, timing-sensitive, and mixed-queue workloads

7. Non-canonical execution in production benchmarks
- report `degraded_mode_count` and resident-handoff misses explicitly so throughput numbers stay honest

8. Top-K surface quality
- track retained-surface quality, not just final top-1 quality, when frontier reduction changes
