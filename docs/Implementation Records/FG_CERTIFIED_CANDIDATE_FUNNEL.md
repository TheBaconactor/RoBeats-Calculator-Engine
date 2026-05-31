# FG Certified Candidate Funnel

## Date
- 2026-05-31

## Broken Invariant
- Mixed candidate selection is an ordering/output compaction policy, not an exact pruning proof.
- A response-frontier FG candidate can be removed before exact scoring only when an admissible upper bound `U` is no greater than an already feasible lower bound `L`.

## First Violation Point
- Production still carried selector modes and environment knobs (`FG_CANDIDATE_SELECTOR_MODE`, `FG_PROMISING_*`, `FG_SLOT_DIVERSE_*`) that could change retention policy without a proof.
- Response-frontier FG had no owner-layer certificate for the proof rule `U <= L`; it either scored candidates or relied on upstream retention.

## Fix Shape
- Added `certified_fg_candidate_upper_bound(...)`, a conservative relaxed upper bound:
  - assumes every note may score as fever/perfect,
  - ignores forced-Great penalties,
  - lets each score-driving stat independently receive the full gem budget.
- `prepare_force_greats_response_frontier_plan(...)` now:
  - computes feasible `L` from cached exact FG variants and candidate base scores,
  - computes one `U` per unique `(selected, base_stats)` response row,
  - removes only rows where `U <= L`,
  - exact-scores every unresolved row.
- Removed selector environment modes and archive branches from `select_fg_candidates(...)`; the helper is now deterministic output compaction only.

## Verification
- `python -m ruff check gear_optimizer/helpers/song_helpers/fg_candidate_selector.py gear_optimizer/helpers/song_helpers/force_greats/candidate_certificate.py gear_optimizer/helpers/song_helpers/force_greats/response_frontier_adapter.py gear_optimizer/solver/native_inflight_pipeline.py tests/test_fg_candidate_certificate.py tests/test_force_greats_response_frontier_route.py tests/test_decode_gpu_native_ga_runs_payload.py` -> passed
- `python -m pytest tests/test_decode_gpu_native_ga_runs_payload.py tests/test_force_greats_response_frontier_route.py tests/test_native_inflight_deferred_post_payload.py tests/test_fg_response_frontier_gpu.py tests/test_fg_candidate_certificate.py -q` -> `47 passed`
- Real `00 (Hard) by garlagan` warm probe:
  - artifact: `artifacts/codex_fg_probe_00 (Hard) by garlagan_20260531_011057`
  - events: `artifacts/certified_fg_funnel_probe_20260531_011057.jsonl`
  - warm wall: `5.175s`
  - warm `ga_gpu`: `1.746s`
  - warm `fg_run`: `1.270s`
  - warm candidate counts: `preselect_ga_candidates=189`, `ga_candidates=189`
  - certified pruned rows: `0`
  - `certificate_lower_bound=34253930`
  - `certificate_max_kept_upper_bound=53168575`

## Complexity Impact
- Added a small certificate owner and two regression tests.
- Deleted the old selector feature-routing branches and env knobs, producing a net LOC reduction.
- The bound is intentionally conservative; it may prune nothing on normal charts, but it is lossless and refuses to remove candidates without proof.
