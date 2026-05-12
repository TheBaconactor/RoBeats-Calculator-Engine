# Local gear response dedupe theorem

## Scope

Native ForceGreats (FG) scoring is evaluated only for the retained local loadout basin. This change adds a lossless equivalence reducer inside the native FG batch path. It does not change the FG search space, gem budget, forced-great configuration list, score formula, GPU kernels, or base/FG leaderboard separation.

## Theorem

For a fixed native FG topology group consisting of:

- selected element/color flags,
- non-fever section count,
- non-fever base count,
- FT/FF search window,
- song timeline and reference tables,

The section topology computation is a deterministic function only of base `Fever Time`, base `Fever Fill Rate`, and song/reference data. Base PP/CM/FM/element stats and selected element do not participate in that timeline walk. Reusing the topology for equal base FT/FF values inside one batch is therefore lossless.

After topology grouping, FG's joint gem/config result for one retained loadout is a deterministic function only of this seven-value local stat response row:

```text
(Perfect Points,
 Combo Multiplier,
 Fever Multiplier,
 primary element stat,
 secondary element stat,
 Fever Time,
 Fever Fill Rate)
```

If two retained loadouts have identical topology-group keys and identical local stat response rows, they have identical native FG search surfaces. Evaluating one representative and scattering its FG result to the other equal-row loadouts is therefore lossless.

## Proof sketch

The native FG batch path passes each candidate to `solve_force_greats_finder_gpu` as exactly the seven values above plus group-constant data: timestamps, optional great-candidate timestamps, long-note count, last-note time, forced-count configs, FT/FF gem pairs, selected-color flags, reference arrays, total gem budget, and fever gem scale. Gear names, genome IDs, mini identities, and original record metadata are not solver inputs.

Within a fixed topology group, the non-row inputs are identical for every member. Equal local stat response rows therefore produce equal solver inputs. Because the solver is deterministic for a given input surface, the best `cfg_idx`, gem counts, FT/FF values, penalties, and final score are equal. The scatter step copies only the FG result; per-loadout metadata is materialized later from the original retained record, so no loadout identity is collapsed.

## Implementation

- Added `_timing_response_key()` and `_local_gear_response_key()` in `gear_optimizer/solver/native_force_greats.py`.
- Cached native FG section summaries by base FT/FF timing response inside each batch.
- Added in-group representative dedupe in `solve_native_force_greats_gpu_batch()` before GPU dispatch.
- Scattered a copied materialized FG result to each original loadout in the representative fanout.
- Kept selected-color responses separate by retaining selected color in the outer topology grouping key.
- Added telemetry counters:
  - `input_genomes`
  - `unique_genomes`
  - `deduped_genomes`
  - `dedupe_groups`
  - `section_summary_cache_hits`
  - `section_summary_cache_misses`
- Surfaced these counters in skyline FG summary as `fg_batch_*` and `fg_section_summary_*` fields.

## Losslessness constraints

The reducer is intentionally narrow. It does not dedupe across selected color, section topology, non-fever base count, or FT/FF search windows. It does not infer dominance between nearby stats, forced-count plateaus, gem allocations, or timing states. Only byte-for-byte equal local solver inputs inside the same topology group share work.

## Verification

Added `tests/test_native_force_greats_batch_dedupe.py`:

- verifies identical local response rows are sent to the fake GPU solver once and scattered back to both original candidates,
- verifies scattered result dictionaries are copied rather than aliased,
- verifies a distinct row remains distinct,
- verifies equal rows with different selected colors remain in separate GPU groups,
- verifies telemetry counters report input, unique, deduped, dedupe-group, and section-summary cache counts.

Additional local validation:

- `python -m pytest tests/test_fg_baseline_params_grid_parity.py`
- `python -m pytest tests/test_theorem_readiness_base5_fg7_margins.py tests/test_theorem_readiness_fg3_s3_certifier.py`
- `git diff --check`
