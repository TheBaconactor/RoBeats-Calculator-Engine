# FG GA Payload Full Staging Bound

## Date
- 2026-05-31

## Broken Invariant
- Exact FG cannot be lossless over generated GA candidates if GA first applies a smaller heuristic payload funnel.
- `FG_CandidateLimit` is an output/persistence retention size, not a proof that generated candidates outside that count cannot win FG.

## First Violation Point
- `gear_optimizer/solver/genetic_pipeline.py`: `_resolve_ga_payload_candidate_limit(...)` defaulted the GA->FG payload to a 4x overselect capped by `GPU_GA_FG_PAYLOAD_OVERSELECT_MAX=256`.
- Downstream FG prep could keep all decoded candidates, but candidates discarded before payload materialization were unrecoverable.

## Fix Shape
- Replace the configurable overselect cap with the canonical GPU staging boundary of 5000 rows.
- GA may still order candidates to fill the fixed staging buffer, but it no longer applies a smaller default or env-controlled heuristic pruning cap before FG.
- The 5000-row limit is the existing Vulkan staging/memory boundary; certified `U <= L` pruning must live in an explicit exact FG owner before any smaller reduction is allowed.

## Verification
- Added regression coverage that env overselect knobs no longer affect the GA->FG staging bound.
- Added FG prep coverage that the mixed selector cannot receive a limit smaller than the decoded candidate count.
- `python -m pytest tests/test_decode_gpu_native_ga_runs_payload.py tests/test_force_greats_response_frontier_route.py tests/test_native_inflight_deferred_post_payload.py tests/test_fg_response_frontier_gpu.py -q` -> `45 passed`
- Real `00 (Hard) by garlagan` warm probe:
  - artifact: `artifacts/codex_fg_probe_00 (Hard) by garlagan_20260531_004206`
  - events: `artifacts/lossless_candidate_probe_20260531_004206.jsonl`
  - warm wall: `5.176s`
  - warm `ga_gpu`: `1.703s`
  - warm `fg_run`: `1.293s`
  - warm candidate counts: `preselect_ga_candidates=189`, `ga_candidates=189`
  - warm prep total: `1551.5ms`

## Complexity Impact
- Removed env-controlled routing from the payload bound.
- Net behavior is simpler: one canonical GA->FG staging size, followed by exact FG reduction/scoring.
