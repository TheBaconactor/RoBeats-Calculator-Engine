# Human Hit-Time Simulation (Server-Parity Fever Timing)

RoBeats’ authoritative fever/score state is time-based: the server advances fever using **verified note event timestamps in integer milliseconds** (and `dt` between them), not just the chart timestamps.

This repo’s optimizer normally assumes “perfectly on-time” hits (event time == chart time). For a small set of edge-case charts, tiny timing differences can flip fever boundaries by 1 note and cause mismatches.

This feature generates a synthetic “human” hit-time stream (seeded RNG) and routes ForceGreats modeling to use it.

## What It Does

- Builds `calc_song["song_data"]["fg_timestamps"]` from the original chart timestamps by:
  - Quantizing chart timestamps to **integer ms** using **floor**
  - Sampling an offset in the **Perfect timing window** (ms)
  - Applying the **held tail window multiplier (x2)** for tail notes
  - Grouping identical timestamps (chords) so they share the same sampled offset
- Enforcing **non-decreasing event times** at the chord-group level (so searchsorted-based fever logic remains valid)
- Also builds `calc_song["song_data"]["fg_great_candidate_timestamps"]` using a **late-only Great band**
  (outside Perfect but inside Great), which the FG timeline uses as a *carry* time to model how forced-Great
  notes can delay fever start times when notes are tightly spaced.
  - In the source `GearStats.get_note_times`, the Great window is computed as **Perfect + GreatTime** (an extension),
    so the late-only band is `[perfect_upper+1, perfect_upper+great_extra_upper]` (and multiplied by x2 for held tails).

## Where It Applies

- Default: **ForceGreats-only** (FG) logic uses `fg_timestamps` when present.
- Optional: apply to **all** scoring/timeline logic by overriding `song_data["timestamps"]`.

## Configuration

`config.ini`:

```ini
[HumanHitSim]
Enabled = False
ApplyTo = FG        ; FG or ALL
Seed = 0            ; 0 => random seed per song/run (the chosen seed is printed and stored in metadata)
Distribution = uniform
RefineAfterGA = false
RefineDevice = gpu
RefineMode = exact
RefineTrials = 0
RefineCandidateLimit = 8
RefineMaxRegimes = 0
RefineRegimeSelection = all
MatrixAfterRefine = true
MatrixCandidateLimit = 0
ContinueMaxRegimes = 0
ContinueRuns = 1
ContinuePopulation = 256
ContinueGenerations = 8
ContinueSeedCandidateLimit = 24
ContinueMutationsPerCopy = 1
```

When enabled, the run prints a one-line summary (including the chosen seed):

`[HumanHitSim] Enabled (ApplyTo=..., dist=..., seed=..., groups=..., forced_monotonic=...)`

## Post-GA Refinement for `ApplyTo=ALL`

When `RefineAfterGA=true`, the optimizer can refine the final `ApplyTo=ALL` timing choice inside one song run instead of relying on outer `SongRepeats`. In deterministic `ApplyTo=ALL` mode, task preparation now collapses queue-level repeats back to one song attempt and moves that work into the inner regime scheduler.

- `RefineMode`:
  - `exact`: preload the full deterministic `161 x 161` FT/FF boundary domain, then derive runtime regimes from the candidate-relevant timeline rows inside the current GA witness pool
  - legacy values `analytical`, `seed`, `table`, and `boundary_table` are accepted only as aliases and normalize to `exact`
- `RefineDevice`:
  - `gpu` (default): run exact-mode boundary-regime planning + scoring on the GPU (Taichi)
  - legacy values `cpu` and `auto` are accepted only as aliases and normalize to `gpu`
- `RefineTrials`:
  - any non-zero value enables the full regime-table pass
- `RefineCandidateLimit`: number of top GA candidates cross-checked during refinement
- `RefineMaxRegimes`: optional exact-mode cap for benchmarking or bounded-overhead runs (`0` => evaluate all planned regimes)
- `RefineRegimeSelection`: how exact mode chooses a capped subset (`all`, `head`, or `even`)
- `MatrixAfterRefine`: run the deterministic `candidate x regime x gem-allocation` pass before any continuation
- `MatrixCandidateLimit`: optional cap for the matrix candidate pool (`0` => reuse `fg_candidate_limit`)
- `ContinueMaxRegimes`: opt-in selective continuation budget for `ApplyTo=ALL` (`0` disables continuation)
- `ContinueRuns`: GA multi-start count for each continued regime
- `ContinuePopulation`: GA population size for each continued regime-local rescout
- `ContinueGenerations`: GA generations for each continued regime-local rescout
- `ContinueSeedCandidateLimit`: how many scout/merged candidates seed the continuation population
- `ContinueMutationsPerCopy`: CPU-side slot mutations applied when expanding seeded continuation populations

This mode is a direct upgrade over pure seed luck:

- exact mode removes sampling from the refinement step and collapses search into deterministic boundary regimes
- exact mode now keeps the full FT/FF domain for preload/count metadata, but uses candidate-relevant timeline rows to build the actual runtime regime families
- exact mode therefore prunes most non-impactful boundary rows before candidate scoring begins
- exact mode now records both raw alpha-interval count and collapsed regime count, plus regime id / family / scope / bounds in metadata
- exact mode now uses regime-aware cache identity, so same-process multi-regime runs do not alias gem/timeline cache entries
- exact planning now uses a compact signature path that avoids building full head-mask arrays during regime-family discovery
- legacy sampled/seeded refine branches no longer exist as separate implementations; old config values are normalized onto the exact GPU path and recorded in metadata as requested aliases
- refinement can switch the final winner to another top GA candidate if that candidate scores better under a refined timing variant
- the native in-flight path now runs a deterministic `candidate x regime x gem-allocation` matrix pass over the merged post-refine candidate surface and promotes the best regime-local gem result before continuation / FG
- on the active GPU-native path, that matrix pass stages the shared candidate population once, streams retained regimes through GPU song slots, stores per-regime results in the GPU multi-run buffer, and downloads the matrix in one transfer instead of doing a CPU-driven submit loop per regime
- opt-in continuation now takes divergent regimes from that post-matrix surface, rebuilds their timestamps deterministically, seeds a bounded prebuilt GA population from the merged matrix surface, and runs a regime-local GPU-native rescout before FG / persistence

## Limitations / Next Steps

- Current implementation simulates **Perfect-only** offsets (it does not yet model Great-only offset ranges when forcing Greats).
- Great timing is modeled in a low-overhead way via a “carry” rule using the precomputed great-candidate times; it does not attempt to simulate arbitrary Great distributions across the whole chart.
- Selective continuation is intentionally bounded and warm-started from the scout surface; it is not yet a true full-population warm continuation from the original GA internals.
- The regime-by-gem matrix is currently wired through the GPU-native in-flight path; non-native fallback paths still stop at exact refine.
- The goal is to capture *fever boundary sensitivity* to realistic timing jitter; it does not attempt to reproduce full server resync behavior or player input scheduling beyond monotonicity.
