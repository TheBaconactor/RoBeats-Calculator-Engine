# FG Candidate Funnel Exact Prep Scope

## Broken Invariant

Exact FG prep must not discard an effective-unique GA candidate with a heuristic selector before exact FG scoring.

The mixed candidate selector is useful as an ordering policy, but it is not a lossless pruning certificate. A candidate can only be removed from exact FG scope when a proven upper bound is no better than the current feasible lower bound.

## First Violation Point

`prepare_fg_job_sync(...)` passed `FG_CandidateLimit` into `select_effective_unique_ga_candidates(...)`, so production FG prep could reduce the decoded effective-unique GA candidate set to the default 51-candidate mixed funnel before exact response-frontier scoring.

Recent telemetry showed this in practice:

```text
00 (Hard): preselect_ga_candidates=184 -> ga_candidates=51
```

## Fix Shape

FG prep now uses the incoming candidate count as the minimum selection limit. This preserves effective-loadout dedupe but prevents the mixed selector from acting as a pruning rule before exact FG scoring.

Persistence can still compact output later, but the exact scorer receives the full effective-unique candidate set currently produced by GA decode.

## Verification

```text
python -m pytest tests/test_force_greats_response_frontier_route.py tests/test_native_inflight_deferred_post_payload.py tests/test_fg_response_frontier_gpu.py -q
```

Result: `35 passed`.

Real `00 (Hard) by garlagan` probe after the change:

```text
preselect_ga_candidates=176/189
ga_candidates=176/189
best_score=34,253,930
best_fg_score=34,259,930
warm_seconds=3.320s
warm fg_run=0.698s
```

## Complexity Impact

One-line policy fix. It removes a lossy exactness violation without adding flags, fallback paths, or song-specific logic.

This is not the final upper-bound certified candidate reduction. It is the lossless baseline within the currently decoded effective-unique GA candidate set.
