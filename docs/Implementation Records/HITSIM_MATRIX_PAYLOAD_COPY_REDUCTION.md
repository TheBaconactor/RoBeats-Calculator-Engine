# HitSim Matrix Payload Copy Reduction (CPU Overhead)

Date: 2026-03-20

## Context

HitSim "matrix" mode evaluates a candidate pool across multiple planned regimes and uses GPU registry solves to score
each (candidate, regime) pair. The CPU side then merges results into:
- per-regime candidate funnels (`fg_regime_groups_by_id[regime_id]["ga_candidates"]`)
- per-identity best payloads (`merged_by_identity`)
- best/winner payload metadata persisted into `song._hitsim_last_refine_info`

This path is performance-sensitive because it runs per song-repeat and can generate many payload objects.

## Problem

`gear_optimizer/solver/native_inflight_stages.py` constructed and stored these payloads with repeated
`copy.deepcopy(...)` calls:
- Deepcopying freshly-constructed list slices (e.g., `copy.deepcopy(list(...))`).
- Deepcopying the same payload dict multiple times to store it in parallel collections.
- Deepcopying entire payload dicts (including nested `Data/Stats`) during merged-candidate finalization just to add two
  metadata fields.

This inflated CPU overhead and memory churn without improving correctness (payload objects are treated as immutable
after construction).

## Decision

Treat per-result HitSim matrix payload dicts as immutable and:
- store/append them by reference (no deepcopy between collections),
- remove redundant deepcopies of list slices,
- add merged-candidate metadata in-place during finalization (no deep copy of the entire payload).

This preserves correctness because the payloads are newly-constructed per result row and are not mutated by candidate
selection or persistence code paths.

## Implementation

Changes (all in `gear_optimizer/solver/native_inflight_stages.py`):
- `_normalize_hitsim_matrix_candidate`: stop deep-copying freshly-built `Genome/Gear/Minis` list slices.
- `_build_hitsim_matrix_candidate_payload`: remove redundant deepcopies for list extraction and payload assembly.
- `_run_hitsim_matrix_jobs_sync`:
  - store payloads in `fg_regime_groups_by_id` and `merged_by_identity` by reference.
  - avoid redundant deepcopy of `baseline_gear/baseline_minis` list copies.
- `_finalize_hitsim_matrix_merged_candidates`: update `payload` and `payload["Data"]` in-place instead of deep-copying.

## Verification

2026-03-20:
- Lint: `python -m ruff check gear_optimizer/solver/native_inflight_stages.py`
- Tests:
  - `python -m pytest tests/test_native_inflight_decode_hitsim_candidate_pool.py tests/test_hit_simulation.py`
  - `python -m pytest -m gpu tests/test_gpu_hitsim_exact_refine_parity.py tests/test_high_level_optimizer_vs_db_smoke.py`
- Root DB pool compare sanity:
  - `python tools/bench/bench_compare_optimizer_to_root_db_pool.py --count 25 --repeats 25`

## Risk Notes

This change assumes downstream code treats payload dicts (and the item dicts within `Gear/Minis`) as read-only. If a
future change introduces in-place mutation of these payload objects, it could reintroduce cross-collection coupling.
The HitSim+in-flight tests above are the primary guardrails for this contract.
