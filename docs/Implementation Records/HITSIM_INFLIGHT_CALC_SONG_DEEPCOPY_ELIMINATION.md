# HitSim In-Flight Calc Song Deepcopy Elimination

- Date: 2026-03-20
- Status: Accepted

## Context

The in-flight HitSim pipeline builds multiple `calc_song` variants:

- HitSim regime materialization (matrix + continuation) produces per-regime `calc_song` payloads.
- FG then evaluates those regimes (via `hitsim_regime_groups`) and may compute an additional
  hitsim-specific delta metric (`hitsim_offset_delta_ms`) post-FG.

We found several hot-path uses of `copy.deepcopy(calc_song)` (and other deepcopies of calc_song variants):

- HitSim matrix GPU payload construction deepcopied the per-regime `calc_song` repeatedly.
- The matrix winner selection path deepcopied `calc_song` again to store FG regime groups and final selection.
- HitSim continuation planning stored an unused deepcopy of `song.calc_song` in `_hitsim_continuation_base_state`.
- FG hitsim-regime mode deepcopied each group's `calc_song`, and then deepcopied it again into each FG variant
  (`variant["_hitsim_calc_song"]`).

`calc_song` is large (contains song payload + numpy arrays), so deep-copying it:

- Adds significant CPU overhead and memory churn.
- Duplicates numpy arrays unnecessarily.
- Reduces GPU static-handle caching effectiveness (payload caching keys include `id(timeline_grid)`), because
  each deepcopy produces a new object identity.

## Decision

Eliminate unnecessary deepcopies of `calc_song` variants in the in-flight HitSim pipeline:

1. HitSim matrix:
   - Pass the existing per-regime `calc_song` dict directly into GPU solve payloads (no deepcopy).
   - Store per-regime `calc_song` references directly in `fg_regime_groups` (no deepcopy).
   - When writing back to `song.calc_song`, use the existing shallow-clone helper
     (`_clone_calc_song_for_hitsim`) instead of deepcopying large arrays.

2. HitSim continuation:
   - Remove the unused `_hitsim_continuation_base_state["calc_song"]` field (it was deepcopied but never read).
   - Use `_clone_calc_song_for_hitsim` when persisting/restoring `calc_song` across continuation stage changes.

3. FG hitsim regimes:
   - Avoid deepcopying each group's `calc_song` before calling FG.
   - Store only a lightweight reference for post-FG delta calculation (`variant["_hitsim_calc_song"] = calc_song`).
   - Prune `_hitsim_calc_song` immediately in `_attach_hitsim_delta_for_fg_variant` via `pop(...)`.

## Why This Is Root-Cause

The overhead came from unnecessary deepcopies of a large immutable-ish payload (arrays treated as immutable inputs),
not from any required correctness constraint. The fix removes the allocations/copies at the source rather than adding
additional passes or compensating logic.

## Alternatives Considered

- Keep deepcopies for isolation: safest, but preserves major CPU overhead and memory bloat.
- Replace deepcopy with `dict(calc_song)` shallow copies everywhere: reduces some overhead but still loses the
  existing contract that only `metadata` and `song_data` must be isolated for HitSim mutation.
- Store only a regime id and look up `calc_song` later: would reduce variant payload size further, but requires
  additional indexing/plumbing across FG outputs.

## Verification

- Unit tests:
  - `python -m pytest tests/test_native_inflight_decode_hitsim_candidate_pool.py tests/test_hit_simulation.py`
- Root DB compare bench:
  - `python tools/bench/bench_compare_optimizer_to_root_db_pool.py --count 25 --repeats 25`
    - base misses 0, FG misses 0
- Throughput sanity:
  - `python tools/bench/bench_compare_optimizer_to_root_db_pool.py --count 200 --repeats 25`
    - `elapsed=977.1s` for 5000 runs (no throughput regression; slight improvement vs ~980s baseline)

## Notes / Risks

- If any downstream GPU path mutates `calc_song` in-place unexpectedly, sharing references could surface coupling.
  Mitigation:
  - Per-regime `calc_song` objects are already isolated by regime materialization.
  - We still shallow-clone when persisting back onto `song.calc_song`.
  - The HitSim matrix/continuation test suite exercises these paths.

