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
```

When enabled, the run prints a one-line summary (including the chosen seed):

`[HumanHitSim] Enabled (ApplyTo=..., dist=..., seed=..., groups=..., forced_monotonic=...)`

## Limitations / Next Steps

- Current implementation simulates **Perfect-only** offsets (it does not yet model Great-only offset ranges when forcing Greats).
- Great timing is modeled in a low-overhead way via a “carry” rule using the precomputed great-candidate times; it does not attempt to simulate arbitrary Great distributions across the whole chart.
- The goal is to capture *fever boundary sensitivity* to realistic timing jitter; it does not attempt to reproduce full server resync behavior or player input scheduling beyond monotonicity.
