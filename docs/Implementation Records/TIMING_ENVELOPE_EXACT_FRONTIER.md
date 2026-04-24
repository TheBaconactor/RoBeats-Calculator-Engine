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
- FG exact DP uses `prepare_timeline_analysis_inputs(..., mode="fg")`
- FG's only specialization is deterministic late-Great carry via `fg_great_candidate_timestamps`
- the exact frontier cap is now `TimelineAnalysisMaxWindows = 3`
- legacy `FG_ExactDPMaxBaselineWindows` / `FG_EXACT_DP_MAX_BASELINE_WINDOWS` remain accepted aliases during migration

Production song prep now calls `apply_timing_envelope(...)`. Root configs no longer ship a sampled-timing section.

Native in-flight deferred post no longer attaches sampled seeds or sampled offset-delta backfills. The old live modules,
tools, tests, and config surface were removed as part of the migration.

## Reduction

The shared engine computes fixed-stat fill and fever duration once, then counts the all-normal timeline activations.
That count is an exact upper bound on any FG forced-Great path for the same stat point because forced Greats only delay
fill and Great carry can only keep fever ending at the same note or later.

This is the same reduction for base analysis and FG. FG adds only the carry stream needed by the exact-DP objective.

## Performance

The migration keeps the hot path cheap:

- timing-envelope FG streams are deterministic and per-song
- the timeline ceiling group payload remains cached by song timing signature
- minimized GPU registry payloads preserve chart timestamps, note types, and timing-envelope metadata
- all-skipped FG exact-DP batches still return before GEM/Taichi readiness, uploads, and exact-DP kernel launch
- dedup timeline execution remains opt-in via `GPU_TIMELINE_CEILING_DEDUP=1`

## Verification

Current full-removal verification (2026-04-24):

- active code/tests/tools/config/current-doc grep for old sampled-timing names: no matches
- `python -m ruff check gear_optimizer tests tools`
- `python -m pytest -q tests/test_fg_exact_dp_correctness.py::test_fg_exact_dp_timing_aware_beats_count_only_baseline_on_carry_set tests/test_timing_envelope.py tests/test_timing_envelope_cache_keys.py tests/test_ceiling_envelope_feasible_signature.py --tb=short`
  - `7 passed`
- `python -m pytest -q tests/test_fg_exact_dp_correctness.py::test_fg_exact_dp_beats_greedy_on_three_window_frontier --tb=short`
  - `1 passed`
  - bounded proof case: `n=20`, `spacing=0.08`, `FF=0.35`, `FT=0.65`, baseline windows `=3`
  - exact DP matches brute force and beats a one-step greedy section policy by `8297`
- `python -m pytest -q tests/test_fg_exact_dp_correctness.py tests/test_fg_exact_dp_pipeline_gpu_dispatch.py tests/test_gpu_service_fused_submit.py tests/test_native_inflight_stages_db_prefetch.py::test_prepare_fg_static_sync_builds_fg_timing_envelope_clone_without_mutating_base_calc_song tests/test_native_inflight_stages_db_prefetch.py::test_prepare_fg_job_sync_warms_fg_jit_for_finder tests/test_bench_ga_winner_stability.py tests/test_verify_sanity_output_script.py --tb=short`
  - `25 passed`
- `python -m pytest -m gpu -q tests/test_gpu_timeline_ceiling_envelope_smoke.py tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py tests/test_gpu_timeline_ceiling_envelope_mc_upper_bound.py tests/test_fg_exact_dp_gpu_parity.py --tb=short`
  - `10 passed, 2 deselected`
- `python -m py_compile gear_optimizer/solver/timing_envelope.py gear_optimizer/solver/fg_exact_dp.py gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/taichi_gem/force_greats/api.py gear_optimizer/solver/taichi_gem/force_greats/fields.py gear_optimizer/pipeline/song_processor.py gear_optimizer/solver/native_inflight_stages.py gear_optimizer/solver/inflight_utils.py gear_optimizer/core/config.py gear_optimizer/data/database.py`
- `git diff --check`

Initial migration verification:

- `python -m py_compile gear_optimizer/solver/timing_envelope.py gear_optimizer/solver/fg_exact_dp.py gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/taichi_gem/force_greats/api.py gear_optimizer/pipeline/song_processor.py gear_optimizer/solver/native_inflight_stages.py gear_optimizer/solver/inflight_utils.py gear_optimizer/core/config.py`
- `python -m py_compile gear_optimizer/solver/timing_envelope.py gear_optimizer/solver/gpu_executor.py gear_optimizer/solver/native_inflight_orchestrator.py tests/test_timing_envelope.py`
- `python -m ruff check gear_optimizer/solver/timing_envelope.py gear_optimizer/solver/fg_exact_dp.py gear_optimizer/solver/taichi_gem/api/timeline.py gear_optimizer/solver/taichi_gem/force_greats/api.py gear_optimizer/pipeline/song_processor.py gear_optimizer/solver/native_inflight_stages.py gear_optimizer/solver/native_inflight_orchestrator.py gear_optimizer/solver/inflight_utils.py gear_optimizer/solver/gpu_executor.py gear_optimizer/solver/scoring/force_greats.py gear_optimizer/core/config.py tests/test_timing_envelope.py tests/test_timing_envelope_cache_keys.py tests/test_timeline_grid_cache_key.py tests/test_full_pipeline_sufficient_key.py tests/test_fg_exact_dp_correctness.py tests/test_fg_exact_dp_gpu_parity.py tests/test_fg_exact_dp_pipeline_gpu_dispatch.py tests/test_gpu_service_fused_submit.py`
- `python -m pytest -q tests/test_timing_envelope.py tests/test_timing_envelope_cache_keys.py tests/test_timeline_grid_cache_key.py tests/test_full_pipeline_sufficient_key.py tests/test_native_inflight_stages_db_prefetch.py::test_prepare_fg_static_sync_builds_fg_timing_envelope_clone_without_mutating_base_calc_song tests/test_native_inflight_stages_db_prefetch.py::test_prepare_fg_job_sync_warms_fg_jit_for_finder tests/test_fg_exact_dp_correctness.py tests/test_fg_exact_dp_pipeline_gpu_dispatch.py tests/test_gpu_service_fused_submit.py --tb=short`
- `python -m pytest -q tests/test_fg_exact_dp_gpu_parity.py::test_fg_exact_dp_public_gpu_api_skips_bad_window_pairs tests/test_fg_exact_dp_gpu_parity.py::test_fg_exact_dp_public_gpu_api_reuses_first_prepared_row tests/test_fg_exact_dp_gpu_parity.py::test_fg_exact_dp_public_gpu_api_matches_cpu_timing_aware --tb=short`
- `python -m pytest -q tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py::test_gpu_ceiling_timeline_matches_cpu_reference tests/test_gpu_timeline_ceiling_envelope_cpu_gpu_exact.py::test_gpu_ceiling_timeline_dedup_matches_baseline --tb=short`
- `python -m pytest -q tests/test_gpu_timeline_ceiling_envelope_mc_upper_bound.py::test_gpu_ceiling_timeline_is_upper_bound_over_mc_samples tests/test_gpu_timeline_ceiling_envelope_mc_upper_bound.py::test_gpu_ceiling_timeline_regression_normal_hi_can_underperform_mc --tb=short`
