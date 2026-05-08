# HITSim Exact Sparse Frontier Batch Plan

Date: 2026-04-09

## Context

Two research results now constrain the next exact GPU attempt:

1. The dense one-cell Taichi value prototype was correct but far too slow.
2. The hostile frontier sweep shows the exact phase-collapsed frontier is tiny even on the worst cells found so far.

That means the next GPU/native attempt should not operate on dense `(lo, hi)` planes at all.

## Inputs

Hostile sweep artifact:

- `artifacts/bench/exact_timeline_frontier_hostile_sweep.json`

Packed hostile batch artifact:

- `artifacts/bench/exact_timeline_frontier_hostile_batch.npz`

Supporting code:

- frontier exporter:
  - `gear_optimizer/solver/hitsim_ceiling_frontier_research.py`
- sparse batch packer:
  - `gear_optimizer/solver/hitsim_ceiling_sparse_batch_research.py`
- hostile sweep tool:
  - `tools/bench/bench_exact_timeline_frontier_hostile_sweep.py`

## Hostile Sweep Result

Songs swept across all unique representative cells:

- `00 (Hard)`
- `Bopeebo`
- `[@_@]`

Worst cells found:

- `[@_@]`:
  - `ft=3`, `ff=137`
  - reachable states: `26`
  - max row states: `2`
  - total exit intervals: `44`
- `Bopeebo`:
  - `ft=0`, `ff=64`
  - reachable states: `23`
  - max row states: `2`
  - total exit intervals: `26`
- `00 (Hard)`:
  - `ft=0`, `ff=150`
  - reachable states: `23`
  - max row states: `2`
  - total exit intervals: `24`

Dense-lattice occupancy on those hostile cells remained around `2e-6` to `5e-6`.

## Packed Top-8 Batch

The hostile top-8 cells were repacked into flat arrays.

Resulting packed sizes:

- cells: `8`
- rows: `162`
- states: `186`
- child edges: `261`

This is the concrete sparse target shape.

## Recommended GPU Shape

### Batch unit

One batch should contain many cells from the same song:

- grouped-window arrays uploaded once
- all cells share:
  - `group_starts`
  - `group_base`
  - `group_low`
  - `group_high`
  - `note_group_idx`

### Flat arrays

The next sparse prototype should operate over the packed arrays already emitted by:

- `pack_frontier_batch(...)`

Important arrays:

- cell arrays:
  - `cell_*`
- row arrays:
  - `row_phase`
  - `row_start_group`
  - `row_state_offset`
  - `row_state_count`
- state arrays:
  - `state_start_note`
  - `state_start_group`
  - `state_lo`
  - `state_hi`
  - `state_phase`
  - `state_activation_note`
  - `state_activation_group`
  - `state_act_lo`
  - `state_act_hi`
  - `state_child_offset`
  - `state_child_count`
- child arrays:
  - `child_boundary_note`
  - `child_exit_group`
  - `child_exit_lo`
  - `child_exit_hi`
  - `child_child_phase`

### Kernel strategy

Do not search for frontier states on GPU.

Instead:

1. Enumerate / export the sparse frontier on CPU.
2. Upload the packed batch.
3. Evaluate DP rows over only the packed state list.

The GPU work should therefore be:

- one kernel family per row phase / topological layer,
- or one kernel over all states in reverse topological order if row ordering is precomputed.

## Immediate Prototype Goal

The next sparse GPU prototype should compute only:

- exact countmax or exact proxy value over the packed frontier states

It still should not attempt full signature reconstruction yet.

## Consequences

1. The exporter + hostile sweep provide a real bounded target for sparse GPU work.
2. The next prototype can be judged on a much smaller packed state graph instead of the impossible dense lattice.
3. If a sparse GPU prototype still loses badly on this packed shape, the right fallback is likely compiled native CPU, not more dense Taichi work.
