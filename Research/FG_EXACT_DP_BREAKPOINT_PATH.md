# Force Greats: Exact DP vs Breakpoint Enumeration

## Status

Research-only. No production wiring in this note.

## Hypothesis

The next major non-skyline breakthrough path is likely **Force Greats**, not another outer-search tweak.

Current GPU-facing FG search still thinks in terms of:

- breakpoint/config enumeration,
- local search windows,
- batching many `(FT, FF, cfg)` evaluations.

But the exact FG objective for a **fixed stat point** is already a dynamic program:

- section state advances monotonically through the chart,
- the reward is prefix-separable,
- forced-Great counts collapse to small fill-penalty plateaus,
- timing-aware carry can be canonicalized.

That suggests the real objective is not "enumerate configs and score them", but:

`best_fg_delta = DP(section_start_idx, carry_state)`

If that DP remains small on real charts, a Taichi/Vulkan implementation could replace a large amount of breakpoint/config work with an exact solve.

## Tooling

Extended:

- [tools/bench/bench_fg_exact_dp_cost.py](tools/bench/bench_fg_exact_dp_cost.py)

New capability:

- `--compare-breakpoints`
  - computes the **current GPU breakpoint-range config space** for the same fixed stat point using the existing
    Taichi breakpoint max-FP kernel,
  - then prints the exact FG DP state/transition counts and wall time beside it.
- `--sample-hard`
  - runs a deterministic Hard-chart sample chosen by note-count quantiles,
  - evaluates one or more fixed `(FT, FF)` points per chart,
  - writes an optional JSON artifact with per-chart rows plus aggregate summary blocks.

This keeps the comparison anchored to the repo's current GPU-side FG search surface.

## Repro commands

### `#include signal.h (Hard)` baseline point

```bash
<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe tools/bench/bench_fg_exact_dp_cost.py \
  --song-fp "Data/Hard/#include signal.h (Hard) by Kurokotei.txt" \
  --mode timing_aware --hitsim 1 --compare-breakpoints 1
```

```bash
<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe tools/bench/bench_fg_exact_dp_cost.py \
  --song-fp "Data/Hard/#include signal.h (Hard) by Kurokotei.txt" \
  --mode timing_aware --hitsim 1 --prune 1 --compare-breakpoints 1
```

Observed:

- GPU breakpoint surface:
  - useful sections: **2**
  - max-FP vector: **`[25, 15]`**
  - config count: **416**
- Exact DP:
  - prune off: **171 states**, **81,823 transitions**, **0.114s**
  - prune on: **171 states**, **915 transitions**, **0.003s**
  - same optimum in both runs (`best_delta=644,800`)

### `#include signal.h (Hard)` high-section point

First scan the stat grid for the largest useful-section point:

- observed max: **`(useful_sections=4, gap=56, ft=0, ff=160)`**

Repro:

```bash
<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe tools/bench/bench_fg_exact_dp_cost.py \
  --song-fp "Data/Hard/#include signal.h (Hard) by Kurokotei.txt" \
  --mode timing_aware --hitsim 1 --ft 0 --ff 160 --compare-breakpoints 1
```

```bash
<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe tools/bench/bench_fg_exact_dp_cost.py \
  --song-fp "Data/Hard/#include signal.h (Hard) by Kurokotei.txt" \
  --mode timing_aware --hitsim 1 --ft 0 --ff 160 --prune 1 --compare-breakpoints 1
```

Observed:

- GPU breakpoint surface:
  - useful sections: **4**
  - max-FP vector: **`[25, 15, 7, 5]`**
  - config count: **19,968**
- Exact DP:
  - prune off: **324 states**, **48,430 transitions**, **0.073s**
  - prune on: **324 states**, **21,765 transitions**, **0.038s**
  - same optimum in both runs (`best_delta=1,235,721`)

### `00 (Hard)` high-section point

Observed max useful-section point was again **`(ft=0, ff=160)`**.

Repro:

```bash
<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe tools/bench/bench_fg_exact_dp_cost.py \
  --song-fp "Data/Hard/00 (Hard) by garlagan.txt" \
  --mode timing_aware --hitsim 1 --ft 0 --ff 160 --compare-breakpoints 1
```

```bash
<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe tools/bench/bench_fg_exact_dp_cost.py \
  --song-fp "Data/Hard/00 (Hard) by garlagan.txt" \
  --mode timing_aware --hitsim 1 --ft 0 --ff 160 --prune 1 --compare-breakpoints 1
```

Observed:

- GPU breakpoint surface:
  - useful sections: **4**
  - max-FP vector: **`[25, 15, 7, 5]`**
  - config count: **19,968**
- Exact DP:
  - prune off: **114 states**, **6,764 transitions**, **0.013s**
  - prune on: **114 states**, **4,002 transitions**, **0.011s**
  - same optimum in both runs (`best_delta=694,321`)

### Broad Hard-chart sample

Repro:

```bash
<redacted-user-home>/Desktop/RoBeats-Calculator-Engine/.venv/Scripts/python.exe tools/bench/bench_fg_exact_dp_cost.py \
  --mode timing_aware --hitsim 1 --prune 1 --compare-breakpoints 1 \
  --sample-hard 64 \
  --json-out artifacts/bench_fg_exact_dp_sample_hard64.json
```

Sampling policy:

- deterministic note-count-quantile sample over `Data/Hard`
- fixed points: **`(FT,FF)=(0,0)`** and **`(0,160)`**
- fixed HitSim seed and timing-aware carry

Observed aggregate summary:

- Sample coverage:
  - **64** Hard charts
  - note range: **362 .. 7,027**
  - note median: **1,609**
- At **`(FT,FF)=(0,0)`**:
  - useful sections median/max: **2 / 2**
  - breakpoint configs median/max: **416 / 416**
  - exact DP states median/max: **163 / 751**
  - exact DP transitions median/max: **9,154 / 206,487**
  - breakpoint-configs per DP-state median/max: **2.38x / 5.55x**
  - charts where configs > states: **59 / 64**
- At **`(FT,FF)=(0,160)`**:
  - useful sections median/max: **4 / 4**
  - breakpoint configs median/max: **19,968 / 22,464**
  - exact DP states median/max: **199 / 773**
  - exact DP transitions median/max: **11,397 / 214,598**
  - breakpoint-configs per DP-state median/max: **107.36x / 288.00x**
  - charts where configs > states: **64 / 64**
- Extreme observed ratio in the sample:
  - `Be My Time Machine (Hard) by tv room`
  - breakpoint configs: **22,464**
  - exact DP states: **78**
  - ratio: **288.00x**

Artifact:

- [artifacts/bench_fg_exact_dp_sample_hard64.json](../artifacts/bench_fg_exact_dp_sample_hard64.json)

## Interpretation

This is enough to call FG exact DP a **major breakthrough path**, not just an open idea.

Why:

- The current breakpoint objective is still fundamentally **enumerative**.
- The exact DP objective is **structural**: it solves the optimum directly in a much smaller state space.
- On real charts, the exact DP state count stayed in the **hundreds**, while the current breakpoint surface reached
  **19,968 configs** at a tested high-section point.
- The broader 64-chart sample says this is not a narrow chart artifact:
  - even at the conservative `(0,0)` point, configs exceeded states on **59 / 64** charts,
  - at the high-section `(0,160)` point, configs exceeded states on **64 / 64** charts with a
    **107.36x median** config/state ratio.
- The prune rule is real:
  - on `#include signal.h` baseline, transitions collapsed from **81,823 -> 915** with no score change.

Important caveat:

- The current breakpoint path is GPU-batched, while this exact DP is still CPU reference code.
- So these numbers are **not** a production wall-clock proof by themselves.
- They *are* strong evidence that a Taichi/Vulkan DP implementation is a better objective than config enumeration.

## Next step

The next high-upside experiment should be:

1. Keep the exact DP state definition:
  - `(section start index, canonical carry state)`
2. Port that recurrence to Taichi/Vulkan for batched stat points.
3. Compare:
  - current `FG_SOLVE_WITH_BREAKPOINTS` style workload,
  - exact DP batch solve workload,
  - same FT/FF points and same score contract.

If that lands, FG stops being a search-radius/config-enumeration problem and becomes an exact batched DP solve.
