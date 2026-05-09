# Gear Skyline GPU Acceleration

## Context

`_global_gear_skyline_points_6d_lane_base_with_codes` consumes the gear DP frontier:

```text
(PP, CM, FM, FT) -> [(FF, base_lane, code)]
```

The CPU implementation flattened each PP layer, sorted by grid cell and base, kept the
best representative per `(CM, FM, FT, FF)` cell, ran a 4D suffix maximum, then filtered
same-layer and higher-PP dominated cells.

This is the same grid pattern used by the combined gear plus mini skyline.

## Decision

Move the production gear global skyline to Taichi/Vulkan:

- `gear_optimizer/solver/skyline_grid_gpu.py` owns shared GPU fill and 4D suffix-max
  kernels.
- `gear_optimizer/solver/gear_skyline_gpu.py` owns the gear-DP flatten, scatter, owner,
  filter, compaction, and higher-layer propagation kernels.
- `gear_optimizer/solver/combined_skyline_gpu.py` now reuses the shared suffix kernels.
- `gear_optimizer/solver/exact_skyline.py` keeps the NumPy implementation as
  `_global_gear_skyline_points_6d_lane_base_with_codes_cpu_reference`, while the
  production `_global_gear_skyline_points_6d_lane_base_with_codes` entry calls GPU.

## Exactness Lemma

For a fixed PP layer `p`, each DP frontier row maps to:

```text
x = (CM, FM, FT, FF)
b = base_lane
c = gear code
```

The CPU path sorts by `(x, -b)` and keeps the first row per `x`, which computes:

```text
L_p[x] = max { b(q) | q is in layer p and coord(q) = x }
```

The GPU path computes the same `L_p[x]` with `atomic_max`. A second owner pass chooses
the row whose base equals `L_p[x]`; under the DP frontier invariant there is at most one
row for a `(PP, CM, FM, FT, FF)` cell, so the emitted code matches the CPU reference.

Both implementations then compute:

```text
S_p[x] = max { L_p[y] | y >= x componentwise }
```

The GPU suffix passes apply the same inclusive max recurrence along CM, FM, FT, and FF.
Max is associative, commutative, and idempotent, so the axis-wise accumulation is exactly
equivalent to NumPy's repeated `maximum.accumulate`.

Same-layer strict dominance checks:

```text
max(S_p[x + e_CM], S_p[x + e_FM], S_p[x + e_FT], S_p[x + e_FF])
```

Higher-layer dominance checks use the maintained suffix grid over all already-kept
higher-PP layers. The GPU updates this suffix grid with each layer's survivors and then
re-applies the same 4D suffix recurrence. Therefore the GPU keep predicate is identical
to the CPU keep predicate.

## Memory

The gear skyline GPU path uses three `int32` grids:

- current layer base/suffix grid
- current layer owner grid
- higher-PP suffix grid

Memory is `grid_elems * 12` bytes plus compact per-layer output buffers. The existing
`250,000,000` element guard remains, which is about `2.79 GiB` for the three grids.
An additional `8 GiB` byte guard prevents accidental over-allocation under the 24 GiB
VRAM target.

## Verification

- `python -m pytest tests/test_gear_skyline_gpu_parity.py tests/test_combined_skyline_gpu_parity.py -q`
- 20 randomized gear-DP skyline parity cases against the CPU reference.
- `python tools/experiments/skyline_single_song.py --song "Data/Hard/00 (Hard) by garlagan.txt" --ga-depth 25 --ga-seed 123 --pre-prune auto --no-fix-minis`
  - Skyline score: `33,061,828`
  - GA score: `32,564,133`
  - Delta: `+497,695`
