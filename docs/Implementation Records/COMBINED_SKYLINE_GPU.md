# Combined Skyline GPU Acceleration

## Context

The exact skyline solver spends most of its unfixed-mini runtime in
`_combined_global_skyline_pairs_6d_lane_base_with_indices`: for each PP layer it forms
the gear x mini product, clamps the four non-PP stat coordinates, keeps the best
base-lane value per clamped coordinate, runs a 4D suffix maximum, and filters dominated
cells against both same-PP and higher-PP layers.

The documented baseline in `docs/research/SKYLINE_BASELINE_EXPERIMENT.md` records:

- reference song: `Data/Hard/00 (Hard) by garlagan.txt`
- GA score: `33,061,828`
- exact skyline score: `33,061,828`
- combined skyline pairs stage: about `111s` of about `113s`

## Decision

Move the combined gear x mini skyline stage to Taichi/Vulkan in
`gear_optimizer/solver/combined_skyline_gpu.py`.

The production entry point in `gear_optimizer/solver/exact_skyline.py` now calls the GPU
implementation. The previous NumPy implementation remains available as
`_combined_global_skyline_pairs_6d_lane_base_with_indices_cpu_reference` for parity
checks only.

The GPU pipeline per PP layer is:

1. Atomic scatter max base-lane value into the clamped 4D stat grid.
2. Atomic scatter the deterministic owner product for each cell whose base equals the
   cell maximum.
3. Run four suffix-max passes over the grid.
4. Filter each cell owner against strict same-layer suffix neighbors and the higher-PP
   suffix grid.
5. Compact surviving gear/mini index pairs on GPU.
6. Scatter survivors into the higher-PP exact-cell grid, copy it to the suffix buffer,
   and run the same 4D suffix passes for cross-layer dominance.

## Exactness Lemma

For a fixed PP layer `p`, let `P_p` be every product `(gear, mini)` with gear PP `p`.
Each product maps to a clamped coordinate `x=(CM,FM,FT,FF)` and base value `b`.

The CPU path sorts by `(x, -b)` and keeps the first row for each `x`, so its retained
cell value is:

```text
L_p[x] = max { b(q) | q in P_p and coord(q)=x }
```

The GPU scatter computes the same `L_p[x]` with `atomic_max`. Owner selection is not
part of skyline dominance; it only chooses a carrier pair for a maximized cell. The GPU
owner kernel atomically keeps the lowest layer product ordinal among products whose
base equals `L_p[x]`, giving one deterministic carrier for the same cell value.

The CPU suffix buffer after `_suffix_max_4d` is:

```text
S_p[x] = max { L_p[y] | y >= x componentwise }
```

The GPU suffix passes perform the same inclusive dynamic program along CM, FM, FT, and
FF in that order. Max is associative, commutative, and idempotent, so the axis order
matches the CPU repeated `maximum.accumulate` result.

For strict same-layer dominance, both implementations compare `L_p[x]` with:

```text
max(
  S_p[x + e_CM],
  S_p[x + e_FM],
  S_p[x + e_FT],
  S_p[x + e_FF]
)
```

where out-of-range neighbors contribute `-1`. This exactly represents any same-PP cell
that is componentwise greater in at least one non-PP coordinate and no smaller in the
others.

For cross-layer dominance, after processing all layers `p' > p`, both implementations
maintain:

```text
H_p[x] = max { L_{p'}[y] | p' > p and y >= x componentwise and y survived }
```

The CPU updates an exact-cell higher grid with current survivors and recomputes its
suffix. The GPU performs the same survivor scatter and suffix recomputation. Therefore
the keep predicate:

```text
L_p[x] > strict_same_layer[x] and L_p[x] > H_p[x]
```

is identical. The returned carrier pair may differ only among products with identical
clamped stats and identical base, which are score-equivalent by construction.

## Memory Budget

The GPU implementation stores four `int32` grids of `grid_elems = CM * FM * FT * FF`:

- current layer base/suffix grid
- current layer owner grid
- higher-layer exact-cell grid
- higher-layer suffix grid

Memory is `grid_elems * 16` bytes, plus small per-layer product output buffers. At the
existing `250,000,000` element guardrail this is about `3.73 GiB`, comfortably below a
24 GiB target even with existing Taichi scoring allocations. The implementation keeps
the existing element-count guard and adds an `8 GiB` bytes guard.

The design deliberately avoids overengineering:

- no host materialization of the gear x mini product
- no global product sort
- no generic sparse-grid framework
- no CPU production fallback
- no feature flag path split

## Verification

Focused checks:

- Synthetic GPU-vs-CPU reference parity over duplicated/clamped cells.
- `python -m ruff check gear_optimizer/solver/combined_skyline_gpu.py gear_optimizer/solver/exact_skyline.py`
- `python tools/experiments/skyline_single_song.py --song "Data/Hard/00 (Hard) by garlagan.txt" --ga-depth 25 --ga-seed 123 --pre-prune auto --no-fix-minis`

Reference-song result after the change:

- GA score: `32,564,133`
- exact skyline score: `33,061,828`
- delta: `+497,695`
- combined skyline prune stage: about `1.8s`
- exact skyline end-to-end time: about `4.06s`
