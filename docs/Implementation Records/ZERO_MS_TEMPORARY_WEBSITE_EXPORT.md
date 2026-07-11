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
