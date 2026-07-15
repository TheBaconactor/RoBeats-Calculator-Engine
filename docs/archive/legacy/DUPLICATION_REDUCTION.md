# Duplication Reduction / Refactor Map

This document tracks intentional deduplication work in `robeats-metafinder`, focusing on keeping CPU/GPU parity math consistent and preventing copy/paste drift across modules.

## Implemented Shared Helpers

### Selected Element normalization
- Helper: `gear_optimizer/core/utils.py::get_selected_element`
- Replaces repeated `"Selected Element"` vs `"SelectedElement"` key checks across persistence, FG, and loadout helpers.

### Color flag derivation (CPU/GPU parity)
- Helper: `gear_optimizer/core/color_flags.py::build_color_flags`
- Centralizes `is_p_*` / `is_s_*` flags used by CPU JIT and GPU kernels.

### Item name normalization
- Helper: `gear_optimizer/helpers/song_helpers/item_utils.py::names_list`
- Replaces duplicated “dict vs str item name” loops across song/persistence helpers and pipeline compaction.

### Gem/stat application
- Helper: `gear_optimizer/solver/scoring/stats_ops.py::apply_gems_to_base_stats`
- Centralizes “apply FT/FF/PP/CM/FM/OV gem effects to a stats dict” and is used by:
  - `gear_optimizer/solver/scoring/fever_solver.py`
  - `gear_optimizer/solver/scoring/force_greats.py`
  - `gear_optimizer/helpers/song_helpers/force_greats/result_application.py`
  - `gear_optimizer/helpers/song_helpers/fg_candidate_stats.py`

### Base fixed stats vector construction (GPU upload)
- Helpers: `gear_optimizer/solver/base_stats.py::{build_base_fixed_stats_list, build_base_fixed_stats_array}`
- Centralizes “subtract user-fixed gems + static overflow gems from base fixed stats” and is used by:
  - `gear_optimizer/solver/genetic.py`
  - `gear_optimizer/solver/native_inflight_orchestrator.py`
  - `gear_optimizer/solver/scoring/genome_evaluation.py`
  - `gear_optimizer/helpers/song_helpers/fg_candidate_stats.py`

### Canonical fixed-gem solver rows
- Helpers: `gear_optimizer/solver/base_stats.py::{build_base_fixed_stats_dict, build_solver_stat_row}`
- Centralizes fixed user-gem subtraction for dict-based solver stats and solver-row projection.
- Used by:
  - `gear_optimizer/solver/scoring/fever_solver.py`
  - `gear_optimizer/solver/scoring/genome_evaluation.py`

### FT/FF gem-pair enumeration
- Helper: `gear_optimizer/solver/ftff_combos.py`
- Centralizes the triangular `(FT, FF)` pair order used by GA's GPU-resident combo table and FG's finder windows.
- Full-window FG now uses the same pair order as GA; radius-limited FG windows keep the historical sorted order.

### Loadout retention selection
- Helper: `gear_optimizer/helpers/song_helpers/retention.py::select_retained_hashes`
- Centralizes “top-N by base + top-N by FG (valid, FG beats base)” logic used by:
  - `gear_optimizer/helpers/song_helpers/persistence.py`
  - `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`

### ForceGreats config validation
- Helper: `gear_optimizer/helpers/song_helpers/fg_config.py`
- Centralizes extraction + non-zero validation of `ForceGreats.config` across:
  - result-entry payloads (`entry["data"]["ForceGreats"]["config"]`)
  - persisted force payloads (`force["ForceGreats"]["config"]`)
  - retained entry rows (`entry["force"]`)
- Used by:
  - `gear_optimizer/helpers/song_helpers/persistence.py`
  - `gear_optimizer/helpers/song_helpers/results_printer.py`
  - `gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py`

### Deferred-post payload compaction
- Helper: `gear_optimizer/helpers/song_helpers/payload_compaction.py`
- Centralizes compact serialization helpers for deferred-post/in-flight payloads:
  - item-name compaction
  - previous-record compaction
  - FG variants compaction
  - GA candidates compaction
  - loadout-entry compaction
- Used by:
  - `gear_optimizer/legacy/song_processor.py`
  - `gear_optimizer/solver/inflight_utils.py`

## Monolith Split (Force Greats GPU dispatch)

`gear_optimizer/helpers/song_helpers/force_greats/gpu_dispatch.py` remains the main orchestrator, but low-level FT/FF pair logic is extracted:
- New module: `gear_optimizer/helpers/song_helpers/force_greats/ftff_pairs.py`
  - `_group_ftff_pairs_by_max_fp_matrix`
- Shared GA/FG enumeration lives in `gear_optimizer/solver/ftff_combos.py`.
- The older Taichi-package re-export was removed; GPU modules import the canonical owner directly.

This keeps the heavy “GPU-resident pipeline” logic in one place while moving reusable pure helpers out.

### Additional FG dispatch extraction
- New module: `gear_optimizer/helpers/song_helpers/force_greats/entry_resolution.py`
- Centralizes FG-entry predicates and direct-GA retention helpers:
  - `entry_fg_score`
  - `entry_fg_config_dict`
  - `entry_has_valid_fg_config`
  - `is_valid_fg_config`
  - `build_direct_ga_entry_items`
  - `merge_retained_direct_ga_entries`
  - `sig_results_has_fg_improvement`
  - `selected_count`
- `gpu_dispatch.py` now imports these helpers instead of defining them inline.

### Retained FG variant materialization owner
- New module: `gear_optimizer/helpers/song_helpers/force_greats/retained_variants.py`
- Owns retained-hash selection + signature-result application + UI/debug FG variant construction for retained entries.
- `gpu_dispatch.py` now delegates retained FG variant build to this module.

## Persistence decomposition

### Record evaluation owner
- New module: `gear_optimizer/helpers/song_helpers/persistence_records.py`
- Owns:
  - `RECORD_UPDATE_SCORE_EPSILON`
  - `evaluate_record_update`
  - `evaluate_progress_record_update`
- `persistence.py` now routes to this owner and re-exports compatibility symbols used by app/orchestrators.

### Persist-entry merge owner
- New module: `gear_optimizer/helpers/song_helpers/persistence_entry_merge.py`
- Owns:
  - loadout-hash resolution fallback logic
  - duplicate-hash merge policy (best base + best FG/force payload preservation)
  - retained-entry replay canonicalization routing
- `persistence.py::build_persistence_entries(...)` now delegates low-level entry merge logic to this module.

### Persistence payload owner
- New module: `gear_optimizer/helpers/song_helpers/persistence_payload.py`
- Owns:
  - ForceGreats payload normalization for DB writes
  - persistence detail payload construction via `make_build_details_fn(...)`
  - top-level DB payload assembly via `build_db_payload(...)`
- `persistence.py` keeps compatibility exports while focusing on persist-entry selection/retention orchestration.
- Detail materialization now imports the canonical FG stats materializer directly instead of swallowing import/materialization errors.

### Persistence entry-selection owner
- New module: `gear_optimizer/helpers/song_helpers/persistence_entry_selection.py`
- Owns:
  - top-base and best-FG priority entry emission
  - GA-candidate persistence rows when no DB+GA union is available
  - retained loadout-entry pruning and row materialization
- `persistence.py::build_persistence_entries(...)` now delegates candidate-selection policy to this module and only handles final merge/canonicalization flow.
- Lazy detail construction for retained entries now lets detail-building errors surface instead of suppressing them.

### Deferred FG persistence details owner alignment
- `gear_optimizer/solver/native_inflight_orchestrator.py::_build_fg_persist_entries` now reuses `make_build_details_fn(...)` instead of duplicating payload-detail assembly branches.
- Force payload validity in deferred FG persistence now routes through `has_valid_fg_config(...)`.

## Dead-Code Removal

### Continuous scheduler parameter cleanup
- Removed unused `ga_inflight_count` parameters from private continuous FG/GA scheduler helpers and their local callers/tests:
  - `gear_optimizer/solver/native_inflight_scheduler.py`
  - `gear_optimizer/solver/native_inflight_orchestrator.py`
  - `tests/test_native_inflight_continuous_scheduler.py`

### FG API parameter cleanup
- Removed unused `n_genomes_override` parameters from the concrete Taichi FG API functions.
- Kept request-level `n_genomes_override` metadata in `gpu_executor.py` where it is still used for sizing/reset decisions, then strips it before invoking callee APIs that do not consume it.
- `python -m vulture gear_optimizer --min-confidence 90` now reports no high-confidence unused-code findings.

### Non-Skyline compatibility shim cleanup
- Removed the obsolete `gear_optimizer/solver/taichi_gem/ftff_combos.py` re-export; callers import `gear_optimizer.solver.ftff_combos` directly.
- Removed the obsolete FG response build and inner re-export modules:
  - `gear_optimizer/solver/taichi_gem/force_greats/response_build_gpu.py`
  - `gear_optimizer/solver/taichi_gem/force_greats/response_inner.py`
- Production and tests now import the owning split modules directly (`response_build_gpu_batch`, `response_build_gpu_reducer`, `response_build_gpu_precompute`, `response_inner_host`, `response_inner_reference`).
- Removed the old non-exact `gear_optimizer/solver/scoring/force_greats.py` evaluator; exact FG replay is owned by `gear_optimizer/solver/scoring/exact_rescore.py`.
- Removed `gear_optimizer/helpers/song_helpers/stats_gateway.py`; database stats reconstruction, strict persistence canonicalization, and TeamBuff stat deltas now own their local rules directly.
- Removed the catch-all `gear_optimizer/helpers/song_helpers/persistence.py` import surface; callers use `persistence_canon.py`, `persistence_payload.py`, or `persistence_records.py` directly.
- Removed `scripts/regression/gpu_stats_regression.py`, which targeted the deleted `batch_evaluate_genomes` path; remaining side tools import the fever solver owner directly.
- Removed stale direct-GA regression/profile harnesses that imported the deleted `solve_coevolution_genetic` entrypoint:
  - `scripts/regression/regression_ga.py`
  - `scripts/regression/ga_gpu_integration.py`
  - `scripts/profile/profile_ga_gpu.py`
  - `tools/profile/tests/profile_ga.py`
- Removed `scripts/regression/regression_baseline.py`; it wrote a temporary config without routing the app to it and monkeypatched Python RNG state that no longer controls native GPU GA seeds.
- Removed the unused `genetic_pipeline` import from `scripts/profile/profile_main_hot.py`.

## Next Targets (Planned)

These are the remaining high-value duplication hotspots that are safe to tackle next:

1) **`gpu_dispatch.py` further split**
- Current: core orchestration file is still large and mixes task building, dispatch policy, and result materialization.
- Goal: extract additional pure helpers for request/response shaping and breakpoint task tiling while keeping GPU scheduling ownership stable.

2) **`persistence.py` entry assembly split**
- Current: `persistence.py` is now a compact facade for public persistence exports plus final entry merge/canonicalization.
- Goal: move the final retained-baseline canonicalization wrapper into the merge owner if a future slice needs more reduction.

## 2026-06-25 — Issue #56 / #52 sweep

Contract/duplication reductions landed via the #56 code-quality sweep and the #52 architecture split:

- **Element-gem alias soup → one reader** (PR #58): six divergent `{Element, Overflow, Element Overflow, ElementOverflow, OV}` alias sets across `gem_defs`, `stats_calculator`, `result_application`, `fg_candidate_stats`, `force_greats_common`, `database` collapsed to the single canonical `element_gem_count()` (`core/gem_defs.py`). Aliases survive only at the legacy DB-row decode boundary.
- **Int-coercion helper family → two owners** (PR #58): the duplicated `_safe_int`/`_coerce_int`/`_int` helpers were removed in favor of `safe_int` (lenient boundary) and `require_int` (fail-loud authority) in `core/utils.py`. The remaining distinct-semantics helpers (`_read_first_int`, `_coerce_db_int`, `_parse_cfg_int`) are intentionally NOT collapsed — see the CODE_QUALITY_SWEEP audit (F1).
- **Raw env-read alias removed** (#56 D1): `gpu_executor._ENV_GET = os.environ.get` deleted; call sites use the canonical `core/parsing.env_get`.
- **Stat-key registries** (#56 A4): audited — three of the four encode genuinely distinct orderings (DB-packed vs base/GPU-array vs FT/FF-swapped) and MUST stay separate; only the exact-copy pair is a future consolidation target. Recorded to prevent a lossy "dedup."
- **Structural de-bloat** (#52): `data/database.py` (1743 LOC) → `data/database/` package (facade + connection/songs/loadout_io/force_normalize/persistence/leaderboards); GPU-free GA decoder extracted to `solver/genetic_pipeline_decode.py`; `scoring_core.py`→`score_math.py`; `note_graph.py` relocated to `solver/fg_response_scoring/`; `persistence_keys.py` inlined.

The remaining `except Exception` classification, dual gem encoding (A3), and `SelectedElement` dual-key write are tracked with per-item adversarial verdicts in `docs/Implementation Records/CODE_QUALITY_SWEEP.md` (HEAD reconciliation table).
