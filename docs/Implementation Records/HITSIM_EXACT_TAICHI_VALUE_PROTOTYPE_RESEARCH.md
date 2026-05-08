# HITSim Exact Taichi Value Prototype Research

Date: 2026-04-09

## Context

After the interval-band collapse, the exact single-cell solver moved from multi-minute territory
 down to tens of seconds for full-grid estimates on sampled hard songs. That made a native/GPU port
 worth testing.

The immediate question was not "can we reconstruct the whole exact signature on GPU?" but the
 narrower and cheaper question:

1. Can the interval-band recurrence be ported correctly to Taichi/Vulkan?
2. If so, is a direct dense GPU formulation already competitive with the current Python exact solver?

## Decision

Build a research-only Taichi/Vulkan prototype for the exact proxy-value objective:

- exact scalar proxy bonus only
- one `(fill_count, d_ms)` cell at a time
- no mask/path reconstruction yet
- no production integration

This isolates the port risk before spending effort on full signature reconstruction.

## Implementation

Added research-only components:

- kernel module:
  - `gear_optimizer/solver/taichi_gem/kernels/kernels_timeline_exact_research.py`
- API / reusable solver:
  - `gear_optimizer/solver/taichi_gem/api/timeline_exact_research.py`
- GPU regression tests:
  - `tests/test_gpu_timeline_exact_intervalband_value.py`
- benchmark harness:
  - `tools/bench/bench_gpu_exact_timeline_value_prototype.py`

### Kernel shape

The prototype computes an exact dense DP over:

- `start_group`
- carry interval `[lo, hi]` over the bounded carry domain `[-40, 80]`
- `first_section` flag

The recurrence uses the interval-band exact transition and reads future rows from the
 previously-computed DP table.

### Reusable solver

The first draft rebuilt all Taichi arrays per call. That would have made the timing mostly about
 Python-side upload/allocation overhead, so the API was reshaped around a reusable research solver:

- upload grouped-window arrays once per song
- allocate DP buffers once per song
- solve multiple `(fill_count, d_ms)` cells against the same resident buffers

This is still not a production batching strategy, but it removes the most obvious wrapper overhead.

## Verification

### Static / unit checks

- `python -m py_compile gear_optimizer/solver/taichi_gem/kernels/kernels_timeline_exact_research.py gear_optimizer/solver/taichi_gem/api/timeline_exact_research.py tests/test_gpu_timeline_exact_intervalband_value.py tools/bench/bench_gpu_exact_timeline_value_prototype.py`
  - result: passed
- `python -m ruff check gear_optimizer/solver/taichi_gem/kernels/kernels_timeline_exact_research.py gear_optimizer/solver/taichi_gem/api/timeline_exact_research.py tests/test_gpu_timeline_exact_intervalband_value.py tools/bench/bench_gpu_exact_timeline_value_prototype.py`
  - result: `All checks passed!`
- `python -m pytest -m gpu tests/test_gpu_timeline_exact_intervalband_value.py -q`
  - result: `2 passed`

### Benchmark

- `python tools/bench/bench_gpu_exact_timeline_value_prototype.py`
  - artifact:
    - `artifacts/bench/hitsim_exact_taichi_value_prototype.json`

The benchmark used the production proxy score triple:

- `base_value = 10000.0`
- `combo_mul = 2.6`
- `fever_mul = 5.25`

It sampled representative unique `(fill_count, d_ms)` cells on:

- `00 (Hard)`
- `Bopeebo`
- `Baby I Don't Care`
- `[@_@]`

Every sampled cell matched the CPU exact reference value.

## Measured Result

Correctness:

- all sampled cells matched exactly
- `all_equal=True` on all four benchmark songs

Hot reused-solver timing:

- `00 (Hard)`:
  - CPU cell mean: `0.00156s`
  - GPU cell mean: `0.65190s`
  - GPU/CPU speed ratio: `0.00240x`
- `Bopeebo`:
  - CPU cell mean: `0.00086s`
  - GPU cell mean: `0.33197s`
  - GPU/CPU speed ratio: `0.00260x`
- `Baby I Don't Care`:
  - CPU cell mean: `0.00106s`
  - GPU cell mean: `0.42780s`
  - GPU/CPU speed ratio: `0.00248x`
- `[@_@]`:
  - CPU cell mean: `0.00198s`
  - GPU cell mean: `0.65947s`
  - GPU/CPU speed ratio: `0.00300x`

Estimated full-grid times from sampled-cell means:

- `00 (Hard)`: CPU `25.19s`, GPU `10495.64s`
- `Bopeebo`: CPU `9.52s`, GPU `3664.99s`
- `Baby I Don't Care`: CPU `14.52s`, GPU `5854.38s`
- `[@_@]`: CPU `30.88s`, GPU `10298.97s`

## Interpretation

This is a mixed but useful result.

What succeeded:

1. The interval-band exact recurrence ports cleanly to Taichi/Vulkan.
2. The reusable GPU solver is bit-for-bit correct on sampled real cells.
3. The benchmark harness now gives a clean baseline for any future GPU redesign.

What failed:

1. A direct dense one-cell GPU DP is not competitive with the current Python exact solver.
2. Even after removing per-call upload/allocation overhead, the GPU prototype is hundreds of times slower.

## Why The Prototype Is Slow

The current GPU formulation is the wrong execution shape:

1. It evaluates a dense interval lattice (`121 x 121`) for every group row.
2. It launches one row kernel per `start_group` and per `first_section`, so host-side dispatch remains large.
3. It does not preserve the CPU solver's sparsity/memo collapse; it brute-forces many states the Python exact solver
   never visits.

So the interval-band math itself was not the blocker. The blocker is the dense DP realization.

## Consequences

1. "Port the current exact solver to GPU" is not a sufficient strategy.
2. Any viable GPU/native follow-on needs a different execution shape:
   - preserve sparsity,
   - batch many cells coherently,
   - or collapse the state space again before dispatch.
3. The current research prototype should be treated as a correctness bridge, not a performance solution.

## Follow-on

The next GPU research step should not be "add full signature reconstruction to this dense prototype."
It should be one of:

1. design a sparse/bucketed GPU formulation that respects the interval-band collapse,
2. batch many cells in a way that amortizes row dispatch and resident data,
3. or derive another exact collapse that removes the dense interval lattice entirely.

Until one of those lands, the Python exact solver remains the better exact implementation.
