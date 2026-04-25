# Timing Envelope Exact Frontier

- Date: 2026-04-24
- Status: Implemented

## Context

The previous seeded sampling layer made FG timing depend on legacy config knobs, random seeds, and repeat policy. The
optimizer now has a deterministic timing-envelope model for Perfect windows and GPU timeline ceiling analysis, so
production should route through the shared timing envelope instead of sampled timing.

The exact goal is intentionally bounded: exact inside the retained reduced frontier, not full exact across every possible
FF/FT timing path.

## Decision

Introduce `gear_optimizer/solver/timing_envelope.py` as the shared timing engine for base and FG:

- base timeline ceiling uses `prepare_perfect_timing_envelope(...)` for chord-group Perfect-window payloads
- base production uses the GPU-resident timing-envelope ceiling frontier; the old CPU-built exact score-proxy timeline
  override hook has been removed from production
- FG exact DP uses `prepare_timeline_analysis_inputs(..., mode="fg")`
- FG finder pre-filters resolved `(base FT/FF + FG FT/FF gems)` pairs with the same shared window counter before
  breakpoint generation and exact inner gem solving; production keeps pairs at or below the three-window resolved
  frontier and removes the heavier admissible score-bound attempt from the producer path
- FG's only specialization is deterministic late-Great carry via `fg_great_candidate_timestamps`
- production FG pair rejection at this stage is the explicit resolved-window frontier; surviving pairs still route
  through exact-inner BnB

Production song prep now calls `apply_timing_envelope(...)`. Root configs no longer ship a sampled-timing section.

Native in-flight deferred post no longer attaches sampled seeds or sampled offset-delta backfills. The old live modules,
tools, tests, and config surface were removed as part of the migration.

## Reduction

The shared engine computes fixed-stat fill and fever duration once, then counts the all-normal timeline activations.
That count is an exact upper bound on any FG forced-Great path for the same stat point because forced Greats only delay
fill and Great carry can only keep fever ending at the same note or later.

This is the same reduction for base analysis and FG. FG adds only the carry stream needed by the exact-DP objective.

Update on 2026-04-25: the FG finder applies a lossless FT/FF pair reduction before the resolved-window filter and before
genome chunking. For each generated pair, it resolves the pair against every retained base row into concrete
`(Fever Time, Fever Fill Rate)` table cells. Pairs sharing the same resolved-cell vector have identical downstream
timing generation, but they are not necessarily interchangeable because FT/FF gems can also change remaining gem budget
and elemental primary/secondary values. Production therefore keeps a Pareto frontier per resolved-cell vector and drops a
pair only when another pair leaves at least as much remaining budget and at least as much post-pair elemental value on
both lanes. This cuts saturated plateau states without pruning on a score guess or on timing identity alone.

The same reducer is memoized across FG groups by its full pure input key: raw FT/FF pair list, retained base FT/FF rows,
fever gem scale, total budget, and FT/FF color flags. Cache hits reuse the exact same retained-pair list and drop count;
they do not change the search surface.

Update on 2026-04-24: `prepare_timeline_window_counter(...)` exposes the shared all-normal window count without building a
full fixed-stat scoring input. It caches the fever-end table per resolved FT index and the final count per resolved
`(FT, FF)` cell. The FG finder now uses that count as a mathematical ingredient instead of a policy cap: for a resolved
pair with `w` all-normal windows and fill count `f`, any FG path must pay at least `w*f - 1` non-fever fill notes because
forced Greats can only delay fill. Production computes an optimistic score upper bound from that minimum normal-note
count and the remaining gem budget, then drops a pair only when every pending base row's bound cannot beat the group's
known base incumbent. The filter runs once per group before genome chunking, not once per chunk, so it cannot starve the
GPU owner between submissions.

## Base Exactness

Base and FG now share the same bounded exact-frontier policy, but they are not exact in the same sense:

- FG exact DP is exact for one fixed resolved stat point
- base exact DP is exact for the cached reference-max score-proxy objective on the retained frontier

Why base is not fully exact across all stat triples:

- the production base path caches one timeline signature per `(FT, FF)` cell and reuses it across many PP/CM/FM/base
  combinations during GA
- different stat triples can prefer different feasible fever signatures for the same timing cell
- therefore one cached base signature cannot be simultaneously globally exact for every genome unless production stores a
  frontier of signatures or solves per genome, which is a much larger architecture change

The shipped migration still supersedes the old single greedy ceiling behavior with the broader GPU timing-envelope ceiling.
The CPU-built exact score-proxy DP remains available for proof/regression runs, but is no longer part of the default
GPU-owner hot path because building overrides synchronously can starve later GPU submissions.

The reviewed breakthrough path is to move the same bounded timing DP to the scoring surface instead of caching one
signature too early: either solve timing after `(FT, FF, PP, CM, FM, base)` is known, or store a small per-cell Pareto
frontier of exact signatures and let the scoring kernel choose the best signature per genome. A single cached signature
per `(FT, FF)` cell cannot prove full base exactness for every genome.

The first implemented step on that path is FG-side: the full FG finder now evaluates generated FG timelines with the
bounded exact inner gem solver, and maintained configs use full FT/FF search (`FG_SearchRadius = -1`). The remaining
timeline gap is base's one-signature cache, not FG's inner gem allocation.

Update on 2026-04-24: base no longer commits exact-inner BnB or fixed-stat GPU scoring to that one proxy-picked
signature when the timing-envelope ceiling kernel has multiple retained variants. The ceiling kernel stores the generated
`normal-hi`, `normal-lo`, `fever-max`, and `fever-min` signatures as a four-entry per-cell frontier. The exact-inner BnB
then evaluates every retained variant for the concrete loadout stats and returns the best score/gem allocation. The
fixed-stat GPU scoring helper uses the same frontier selection, so postprocess/integrity scoring no longer inherits the
old primary-mask-only behavior.

Update on 2026-04-25: the generated four-signature ceiling frontier is now compacted on GPU before exact-inner BnB sees
it. The compactor drops only exact duplicates and surfaces dominated for every loadout on the generated surface:

- the retained surface's head fever mask is a superset of the dropped surface's mask
- the retained surface has at least as many body fever notes
- the retained surface has no more body normal notes

Those conditions are lossless for the scoring objective because any dropped normal note is replaced by a fever note, and
every fever note present in the dropped surface remains fever in the retained surface. The direct ceiling kernel and the
representative-cell dedup kernel both call the same `_write_exact_timeline_frontier4(...)` helper, and the scatter kernel
copies the compacted frontier from representatives into the full grid.

This is still exact over the retained timing-envelope frontier, not a proof that the generated four-signature frontier is
the full mathematical universe of all possible human timing paths. The stale same-signature warmstart pruning is disabled
for multi-variant frontier cells because two cells can share the primary signature while differing in a secondary variant
that is optimal for a specific loadout.

## Performance

The migration keeps the hot path cheap:

- timing-envelope FG streams are deterministic and per-song
- the timeline ceiling group payload remains cached by song timing signature
- the timing cache key follows the GPU-resident ceiling payload and no longer splits on retired exact-override metadata
- minimized GPU registry payloads preserve chart timestamps, note types, and timing-envelope metadata
- all-skipped FG exact-DP batches still return before GEM/Taichi readiness, uploads, and exact-DP kernel launch
- dedup timeline execution remains opt-in via `GPU_TIMELINE_CEILING_DEDUP=1`
- CPU-built base exact timeline overrides are no longer part of production routing

## Verification

Current full-removal verification (2026-04-24):

- active production/config/script/current-doc grep for old sampled-timing entrypoints and knobs: no live usage
- active config/script cleanup also removed stale sampled-timing sections and the removed FG-only window-gate alias
- `python -m ruff check gear_optimizer tests tools`
- `python -m pytest -q tests/test_fg_exact_dp_correctness.py::test_fg_exact_dp_timing_aware_beats_count_only_baseline_on_carry_set tests/test_timing_envelope.py tests/test_timing_envelope_cache_keys.py tests/test_ceiling_envelope_feasible_signature.py --tb=short`
  - `7 passed`
- `python -m pytest -q tests/test_fg_exact_dp_correctness.py::test_fg_exact_dp_beats_greedy_on_three_window_frontier --tb=short`
  - `1 passed`
  - bounded proof case: `n=20`, `spacing=0.08`, `FF=0.35`, `FT=0.65`, baseline windows `=3`
  - exact DP matches brute force and beats a one-step greedy section policy by `8297`
- `python -m pytest -q tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py::test_gpu_ceiling_exact_frontier_beats_heuristic_on_bounded_cell --tb=short`
  - `1 passed`
  - bounded base proof case: `n=120`, `gap=24ms`, `FF=1.0`, `FT=0.8`, activation upper bound `=2`
  - production base exact frontier beats the old heuristic by `159120` under the cached proxy objective
- `python -m pytest -q tests/test_fg_exact_dp_correctness.py tests/test_fg_exact_dp_pipeline_gpu_dispatch.py tests/test_gpu_service_fused_submit.py tests/test_native_inflight_stages_db_prefetch.py::test_prepare_fg_static_sync_builds_fg_timing_envelope_clone_without_mutating_base_calc_song tests/test_native_inflight_stages_db_prefetch.py::test_prepare_fg_job_sync_warms_fg_jit_for_finder tests/test_bench_ga_winner_stability.py tests/test_verify_sanity_output_script.py --tb=short`
  - `25 passed`
- `python -m pytest -m gpu -q tests/test_gpu_timeline_ceiling_envelope_smoke.py tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py tests/test_gpu_timeline_ceiling_envelope_mc_upper_bound.py tests/test_fg_exact_dp_gpu_parity.py --tb=short`
  - `10 passed, 2 deselected`
- `python -m py_compile gear_optimizer/solver/timing_envelope.py gear_optimizer/solver/fg_exact_dp.py gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/taichi_gem/force_greats/api.py gear_optimizer/solver/taichi_gem/force_greats/fields.py gear_optimizer/pipeline/song_processor.py gear_optimizer/solver/native_inflight_stages.py gear_optimizer/solver/inflight_utils.py gear_optimizer/core/config.py gear_optimizer/data/database.py`
- `git diff --check`

Throughput-stall follow-up verification (2026-04-24):

- root cause: CPU-built exact timeline override generation ran synchronously inside `precompute_timeline_gpu`, which is
  executed by the single GPU owner before later GPU kernels can be submitted
- follow-up: the CPU exact-override hook was removed after the GPU-resident frontier became the maintained product path
- `python -m py_compile gear_optimizer\solver\taichi_gem\api\timeline.py tests\test_timing_envelope_cache_keys.py tests\test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py`
  - clean
- `python -m pytest -q tests\test_timing_envelope_cache_keys.py tests\test_fg_finder_exact_inner_routing.py tests\test_fg_resolved_window_pair_filter.py --tb=short`
  - `11 passed`
- `python -m pytest -q tests\test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py::test_gpu_ceiling_exact_frontier_beats_heuristic_on_bounded_cell --tb=short`
  - `1 passed`
- `python -m pytest -m gpu tests/test_gpu_timeline_frontier_exact_bnb.py -q`
  - `1 passed`
  - proves exact-inner BnB and fixed-stat GPU scoring both evaluate the retained timeline frontier instead of sticking to
    the primary proxy timeline

Generated-frontier compaction verification (2026-04-25):

- `python -m pytest -q tests/test_timeline_frontier_reduction.py --tb=short`
  - proves duplicate/dominated surface reduction preserves the best score over loadout-like score weights
  - verifies both ceiling envelope kernels call the shared compactor instead of writing an unconditional four-variant
    frontier

Initial migration verification:

- `python -m py_compile gear_optimizer/solver/timing_envelope.py gear_optimizer/solver/fg_exact_dp.py gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/taichi_gem/force_greats/api.py gear_optimizer/pipeline/song_processor.py gear_optimizer/solver/native_inflight_stages.py gear_optimizer/solver/inflight_utils.py gear_optimizer/core/config.py`
- `python -m py_compile gear_optimizer/solver/timing_envelope.py gear_optimizer/solver/gpu_executor.py gear_optimizer/solver/native_inflight_orchestrator.py tests/test_timing_envelope.py`
- `python -m ruff check gear_optimizer/solver/timing_envelope.py gear_optimizer/solver/fg_exact_dp.py gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/taichi_gem/force_greats/api.py gear_optimizer/pipeline/song_processor.py gear_optimizer/solver/native_inflight_stages.py gear_optimizer/solver/native_inflight_orchestrator.py gear_optimizer/solver/inflight_utils.py gear_optimizer/solver/gpu_executor.py gear_optimizer/solver/scoring/force_greats.py gear_optimizer/core/config.py tests/test_timing_envelope.py tests/test_timing_envelope_cache_keys.py tests/test_timeline_grid_cache_key.py tests/test_full_pipeline_sufficient_key.py tests/test_fg_exact_dp_correctness.py tests/test_fg_exact_dp_gpu_parity.py tests/test_fg_exact_dp_pipeline_gpu_dispatch.py tests/test_gpu_service_fused_submit.py`
- `python -m pytest -q tests/test_timing_envelope.py tests/test_timing_envelope_cache_keys.py tests/test_timeline_grid_cache_key.py tests/test_full_pipeline_sufficient_key.py tests/test_native_inflight_stages_db_prefetch.py::test_prepare_fg_static_sync_builds_fg_timing_envelope_clone_without_mutating_base_calc_song tests/test_native_inflight_stages_db_prefetch.py::test_prepare_fg_job_sync_warms_fg_jit_for_finder tests/test_fg_exact_dp_correctness.py tests/test_fg_exact_dp_pipeline_gpu_dispatch.py tests/test_gpu_service_fused_submit.py --tb=short`
- `python -m pytest -q tests/test_fg_exact_dp_gpu_parity.py::test_fg_exact_dp_public_gpu_api_skips_bad_window_pairs tests/test_fg_exact_dp_gpu_parity.py::test_fg_exact_dp_public_gpu_api_reuses_first_prepared_row tests/test_fg_exact_dp_gpu_parity.py::test_fg_exact_dp_public_gpu_api_matches_cpu_timing_aware --tb=short`
- `python -m pytest -q tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py::test_gpu_ceiling_timeline_matches_cpu_reference tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py::test_gpu_ceiling_timeline_dedup_matches_baseline --tb=short`
- `python -m pytest -q tests/test_gpu_timeline_ceiling_envelope_mc_upper_bound.py::test_gpu_ceiling_timeline_is_upper_bound_over_mc_samples tests/test_gpu_timeline_ceiling_envelope_mc_upper_bound.py::test_gpu_ceiling_timeline_regression_normal_hi_can_underperform_mc --tb=short`
