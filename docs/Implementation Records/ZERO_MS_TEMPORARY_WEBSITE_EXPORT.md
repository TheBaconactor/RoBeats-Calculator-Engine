# Zero-Millisecond Temporary Website Export

## Decision

This temporary release worktree runs production song preparation at fixed chart timing
(`zero_ms`) and does not prebuild whole-pool timing frontiers at startup. It still builds the
fixed-0ms FG response data required by Force Greats scoring.
Base and Force Greats optimization and their separate persisted leaderboards remain enabled.

## Reason

The input-awareness timing model is being developed separately. Building Perfect-window timing
frontiers for the full song pool delays an urgent website data refresh by hours and would publish
results for a timing model that is intentionally out of scope for this release.

## Invariants

- Every production base and FG song is explicitly stamped `TimingEnvelopeMode="zero_ms"`.
- Every playable hit uses its chart timestamp; no Perfect-window timing frontier is consulted.
- Startup skips the Perfect-window timeline frontier and builds only required fixed-0ms FG data.
- Runtime materializes the exact deterministic chart-time timeline directly as one singleton
  surface per FT/FF cell. It writes no timeline-frontier artifact and cannot activate outside
  an explicitly stamped `zero_ms` song.
- Base and FG scoring, persistence, and `songs.best_score` / `songs.best_fg_score` remain separate.
- Missing fixed-timing data still fails loudly through the existing scoring invariants.

This is a branch-specific release policy, not a compatibility flag or a second runtime route.

## Correctness gate

The singleton payload is built from the same `calculate_fever_timeline_indices` rules owner used
by `score_stats_fixed_timing_exact_batch`. Tests compare payload-based replay against that
independent fixed-timing scorer at zero, maximum, mixed, and ordinary FT/FF cells. Perfect-window
songs retain the missing-cache failure.

Persistence uses the independent fixed-timing exact scorer and intentionally omits the
Perfect-window `TimelineFrontier` witness. FG session pruning preserves shared physical response
segments by remapping offsets through the compacted physical-row prefix.

## Temporary serviceability fallback (issue #125)

The invariants above kept "Perfect-window cache misses still fail loudly." Because the
Perfect-window timing frontier is intentionally not built on this branch and only `zero_ms` is
serviceable, that fail-loud path raises `MissingFrontierCacheError` for any request that still
arrives stamped for the (unbuilt) timing model -- breaking callers instead of returning a score.

To keep production answering while only `zero_ms` exists, a **temporary, owner-requested** runtime
fallback coerces such requests to the fixed chart-time (`zero_ms`) payload at the single
base-scoring chokepoint `load_timeline_frontier_payload`, rather than raising. The chart timeline is
identical either way, so the served base score equals the independent `zero_ms` scorer (pinned by
`tests/test_zero_ms_only_temp_fallback.py`). The coercion is loud (warn-once), lives in the
obviously-named shim `gear_optimizer/solver/zero_ms_only_temp.py`, is marked `ZERO_MS_ONLY_TEMP` at
every site, and keeps the original `raise` commented in place.

This deliberately and temporarily bends the repo's fail-loud / no-fallback-branch non-negotiable; it
is a branch-scoped release policy, not a compatibility flag or a second runtime route. **Removal is
tracked in GitHub issue #125**, which lists every temporary site with a cleanup plan. When the
input-aware timing model ships, delete the shim, restore the raise, and restore real timing-mode
selection.
