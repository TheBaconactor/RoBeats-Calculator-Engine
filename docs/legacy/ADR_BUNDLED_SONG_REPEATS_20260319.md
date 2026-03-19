# ADR: Bundled Song Repeats Without Queue Inflation

## Status
Accepted

## Context

`SongRepeats` exists to run the full song pipeline multiple times:
- different GA basins
- different per-run HitSim timelines when HitSim is randomized
- different end-to-end outcomes under the same song/loadout search surface

The rejected shortcut was to fold repeats into GA `MultiStart` and/or `SearchDepth`.
That changes semantics:
- it reuses one song/timeline instance
- it does not execute independent full song runs
- it removes the exact source of diversity that `SongRepeats` was supposed to provide

The separate operational problem is queue inflation:
- expanding one song into `N` queue items distorts queue limits, progress totals, and backend priority batching

## Decision

Add an opt-in `IterationEngine.BundleSongRepeats` mode (env override `BUNDLE_SONG_REPEATS=1`).

In this mode:
- app queueing creates one physical task per song
- that task carries a repeat plan with precomputed per-repeat `ga_seed` values
- native in-flight materializes one logical `Run i/N` task at a time from that plan
- each logical repeat still runs the full song pipeline independently
- the next repeat does not start until the current repeat finishes through FG completion
- the physical song task is marked complete only after the last logical repeat finishes

## Consequences

Pros:
- preserves true `SongRepeats` semantics
- removes visible queue inflation
- keeps RoBeatsMeta batch completion keyed to the physical song, not each logical repeat
- allows HitSim `ApplyTo=All` repeat diversity without forcing task explosion

Tradeoffs:
- bundled repeat progress is song-level, not logical-repeat-level
- a stop/restart in the middle of a bundle restarts that song bundle from the beginning
- a bundle can occupy one in-flight slot for longer because repeats are serialized intentionally

## Notes

This mode intentionally does **not** collapse repeats into GA multi-start or search depth.
That behavior is explicitly superseded for the bundled-repeat use case.
