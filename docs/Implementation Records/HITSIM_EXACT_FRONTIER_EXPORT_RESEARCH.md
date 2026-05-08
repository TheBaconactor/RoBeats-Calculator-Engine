# HITSim Exact Frontier Export Research

Date: 2026-04-09

## Context

The direct dense Taichi/Vulkan value prototype proved the interval-band recurrence ports correctly,
 but it was still hundreds of times slower than the Python exact solver.

That changed the next question from:

- "can we port the recurrence?"

to:

- "what sparse state shape does the exact solver actually visit?"

Without that data, a second GPU attempt would still be guesswork.

## Decision

Add a research-only CPU frontier exporter that emits the reachable exact countmax state graph in the
 same phase-collapsed form a sparse GPU solver would want:

- state key:
  - `(start_note, start_group, lo, hi, section_phase)`
- where:
  - `section_phase = 0` only for the first fill segment
  - `section_phase = 1` for every later segment

This is a deliberate collapse relative to the historical exact solver cache key, which used the raw
 section index even though only the first section changes the recurrence.

## Implementation

Added:

- research helper:
  - `gear_optimizer/solver/hitsim_ceiling_frontier_research.py`
- export tool:
  - `tools/bench/bench_exact_timeline_frontier_export.py`
- smoke regression:
  - `tests/test_exact_timeline_frontier_research.py`

### Exported data

Per sampled cell the exporter records:

- exact signature and canonical-signature check
- per-row frontier widths:
  - `(section_phase, start_group) -> state_count, occupancy, exit counts, activation span`
- per-state payload:
  - activation group / activation band
  - merged exit intervals
  - terminal reason if no continuation exists
- global metrics:
  - reachable state count
  - dense-lattice occupancy
  - max row frontier width
  - total merged exit interval count

## Verification

- `python -m py_compile gear_optimizer/solver/hitsim_ceiling_frontier_research.py tools/bench/bench_exact_timeline_frontier_export.py tests/test_exact_timeline_frontier_research.py`
  - result: passed
- `python -m ruff check gear_optimizer/solver/hitsim_ceiling_frontier_research.py tools/bench/bench_exact_timeline_frontier_export.py tests/test_exact_timeline_frontier_research.py`
  - result: `All checks passed!`
- `python -m pytest tests/test_exact_timeline_frontier_research.py -q`
  - result: `1 passed`

Artifact runs:

- default export:
  - `python tools/bench/bench_exact_timeline_frontier_export.py`
  - artifact:
    - `artifacts/bench/exact_timeline_frontier_export.json`
- wider representative sweep:
  - `python tools/bench/bench_exact_timeline_frontier_export.py --song "Data/Hard/00 (Hard) by garlagan.txt" --song "Data/Hard/Bopeebo (Hard) by Kawai Sprite.txt" --song "Data/Hard/[@_@] (Hard) by Chroma.txt" --sample-reps 8 --out artifacts/bench/exact_timeline_frontier_export_sample8.json`
  - artifact:
    - `artifacts/bench/exact_timeline_frontier_export_sample8.json`

## Measured Result

On the sampled representative cells, the phase-collapsed reachable frontier was extremely sparse.

Selected maxima from the sample-8 sweep:

- `00 (Hard)`:
  - max sampled cell:
    - `ft=0`, `ff=0`
    - reachable states: `8`
    - max row states: `1`
    - total merged exit intervals: `7`
- `Bopeebo`:
  - max sampled cell:
    - `ft=0`, `ff=0`
    - reachable states: `9`
    - max row states: `2`
    - total merged exit intervals: `12`
- `[@_@]`:
  - max sampled cell:
    - `ft=45`, `ff=148`
    - reachable states: `9`
    - max row states: `2`
    - total merged exit intervals: `12`

Observed global occupancies on these sampled cells were around `1e-6` relative to the dense
 `(start_group, lo, hi, phase)` lattice.

## Interpretation

This is the opposite of the dense Taichi prototype:

1. The exact solver does not appear to visit anything close to the full interval lattice.
2. On the sampled cells, the phase-collapsed frontier looks almost path-like.
3. A sparse GPU/native attempt should be designed around frontier lists / small state buckets,
   not around dense DP planes.

## Consequences

1. The next GPU attempt should preserve the sparse frontier explicitly.
2. A dense `(121 x 121)` row kernel should be treated as a dead end for this problem shape.
3. The next benchmark should search for worst-case frontier width across a larger cell sweep,
   but the initial exporter already shows that the sparse target is tiny on representative cells.

## Follow-on

1. Add a hostile sweep that searches for the maximum frontier-width cells, not just representative reps.
2. Design a sparse batched GPU prototype over frontier lists / buckets.
3. Keep the phase-collapsed state key as the target shape for any future GPU/native design.
