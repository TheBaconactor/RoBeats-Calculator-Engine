# Analytical HitSim Ceiling GPU Timeline (Taichi/Vulkan)

- Date: 2026-03-23
- Status: Implemented (GPU path)

## Context

The real game’s fever state depends on hit timing, not just chart timing. When HumanHitSim is disabled,
the optimizer implicitly assumes every note is hit at exactly the chart timestamp, which is not realistic
and can materially change fever boundaries (and therefore score).

Historically, the repo worked around this by running multiple seeded HitSim repeats (`SongRepeats`) and
keeping the best outcome. That is expensive and still probabilistic.

We want a deterministic, one-shot “ceiling” timeline outcome that approximates the best-case fever
window boundaries achievable under the Perfect timing window with the monotonic event-time constraint.

## Decision

Implement an Analytical HitSim “ceiling” fever timeline as a GPU (Taichi/Vulkan) timeline precompute:

- Replace the “zero-offset” timeline (chart timestamps only) with a deterministic upper envelope over
  allowed Perfect-window offsets.
- Keep the output contract unchanged: per-(FT, FF) grid writes the same
  `(fever_mask_head_bits, count_body_fever, count_body_normal, signatures, gap, activations)` fields used
  downstream.
- Gate the behavior behind an env flag so parity/diagnostics can still run the deterministic kernel.

## Implementation

### New GPU fields (per-song inputs)

Uploaded once per song (only when ceiling mode is enabled):

- `song_note_group_idx[note] -> group`
- `song_group_starts[group] -> first note idx`
- `song_group_base_t_ms[group] -> chart ms (quantized)`
- `song_group_low_ms[group]`, `song_group_high_ms[group]` -> nominal carry window per chord group

These are derived on CPU using `prepare_perfect_hit_simulation()` (same chord grouping + per-note window
semantics as HumanHitSim) and uploaded to GPU.

To keep this CPU preprocessing from becoming a throughput bottleneck, the GPU timeline API caches the
derived chord-group payload (bounded LRU) keyed by the song timing signature (timestamps + note types).
This makes repeated evaluations of the same song effectively GPU-only after the first call.

### New Taichi kernel

`compute_timeline_grid_ceiling_hitsim_kernel(...)` computes the full 161x161 grid per song slot:

- For each (FT, FF) cell it computes `fill_count` and `d_ms` (same formulas as the deterministic kernel).
- For each fever activation it:
  - Propagates the carry forward through the normal fill section(s), choosing the **latest feasible carry** in normal
    segments, so the activation carry `r_act` is the latest reachable carry at the activation chord group (can exceed
    the nominal `group_high` under monotonic forcing).
  - Uses the boundary band `[Q-80, Q+40]` (where `Q = c_s + r_act + d_ms`) to avoid scanning all future notes.
  - Propagates reachable carry intervals forward and finds the earliest chord group where the in-fever
    reachable interval becomes empty; that boundary determines `fever_end_idx`.
  - Carries a feasible (max) carry value at the last in-fever group forward so subsequent windows see the correct
    monotone carry state (no per-window carry reset).
- Writes to the same timeline grid fields as `compute_timeline_grid_kernel`.

### Wiring / behavior control

- Env flag: `GPU_TIMELINE_CEILING_HITSIM` (default: enabled in production).
  - `0`: use deterministic timeline (`compute_timeline_grid_kernel` + `precompute_fever_end_idx_kernel`).
  - `1`: use ceiling timeline (`compute_timeline_grid_ceiling_hitsim_kernel`).
- GPU timeline cache key (`_song_timing_cache_key`) includes:
  - the ceiling-mode bit,
  - stable digests for the relevant timestamp array (`chart_timestamps` in ceiling mode; otherwise `timestamps`),
  - note types (ceiling mode depends on held-tail window semantics),
  - and the ref-array signature (timeline grid depends on FT/FF tables).

## Tests / Verification

- Added GPU smoke test for ceiling mode: `tests/test_gpu_timeline_ceiling_hitsim_smoke.py`.
- Added GPU regression test for exact CPU/GPU signature equality (ceiling mode): `tests/test_gpu_timeline_ceiling_hitsim_cpu_gpu_exact.py`.
- Added GPU invariant test that ceiling is an upper bound over sampled Perfect-window Monte Carlo seeds:
  `tests/test_gpu_timeline_ceiling_hitsim_mc_upper_bound.py`.
- The test suite defaults `GPU_TIMELINE_CEILING_HITSIM=0` in `tests/conftest.py` to keep existing CPU/GPU parity tests
  stable. Ceiling mode is exercised explicitly by the new test.

Verified locally (GPU):

- `python -m pytest -m gpu tests/test_gpu_timeline_ceiling_hitsim_smoke.py`
- `python -m pytest -m gpu tests/test_gpu_timeline_ceiling_hitsim_cpu_gpu_exact.py`
- `python -m pytest -m gpu tests/test_gpu_timeline_ceiling_hitsim_mc_upper_bound.py`
- `python -m pytest -m gpu tests/test_gpu_timeline_parity.py`
- `python -m pytest -m gpu tests/test_fg_breakpoints_maxfp_gpu.py`
- `python -m pytest -m gpu tests/test_parity_smoke.py::test_gem_solver_cpu_gpu_exact_parity_smoke`

## Consequences / Follow-ups

- CPU vs GPU parity tests must run with deterministic timeline mode (or be updated to account for the new ceiling behavior).
- Ceiling mode currently relies on CPU preprocessing of chord groups/windows before uploading to GPU.
  If this becomes a measurable bottleneck (very large songs, high churn), consider a GPU-native grouping prepass, or
  persisting the grouping arrays alongside song metadata for reuse across processes/runs.
- The ceiling kernel is designed to be a deterministic upper envelope for fever membership under the modeled Perfect windows,
  not an expected-value estimator. Expected-value/Markov variants remain future work (see `docs/ANALYTICAL_HITSIM_SOLUTION.md`).

### Follow-up: Exact DP reference + counterexample (2026-03-29)

A reference-only exact DP was added to help validate and characterize the ceiling objective:

- `gear_optimizer/solver/hitsim_ceiling_exact_dp_ref.py` implements an exact DP under a score-independent
  "maximize total fever notes" objective with deterministic tie-breaks.
- `tests/test_ceiling_hitsim_exact_dp_counterexample.py` contains a deterministic synthetic chart where the shipped greedy
  ceiling kernel is not optimal under that objective (the DP finds a strictly higher total-fever signature).

This does not change production behavior; the GPU ceiling timeline remains the greedy interval-propagation kernel.

### Follow-up: score-robust ceiling variants (2026-04-04)

A real-song comparison against Monte Carlo best-of-N found a failure mode where the greedy "keep fever as long as
feasible" ceiling can score *below* the best sampled MC seed (even when total fever-note count is unchanged).

Concrete example (via `tools/bench/bench_ceiling_vs_mc25.py`):

- Song: `Data/Hard/Baby I Don't Care (Hard) by Johnny  Michiko Hamada [Nash Music Library].txt`
- Cell: `FT=0, FF=160`
- Symptom (pre-fix): ceiling was `-5440` under MC best-of-500 due to a boundary flip trading `1` body-fever note for
  `1` head-fever note (`i=91`).

Change (GPU + CPU reference + bench):

- `compute_timeline_grid_ceiling_hitsim_kernel` now evaluates 4 fully-feasible per-cell variants:
  - normal-hi / normal-lo: carry choice during non-fever fill segments
  - fever-max / fever-min: extend fever as long as feasible vs end fever at the earliest reachable out-group in the
    swing band
- The kernel emits the best variant using the same deterministic score proxy (`_ceiling_compare_score`) and tie-breaks.

Verification:

- `python -m pytest -m gpu tests/test_gpu_timeline_ceiling_hitsim_cpu_gpu_exact.py`
- `python -m pytest -m gpu tests/test_gpu_timeline_ceiling_hitsim_mc_upper_bound.py`
- `python tools/bench/bench_ceiling_vs_mc25.py --song "Data/Hard/Baby I Don't Care (Hard) by Johnny  Michiko Hamada [Nash Music Library].txt" --ft 0 --ff 160 --seeds 500 --strict`

### Follow-up: exact ceiling-grid deduplication by `(fill_count, d_ms)` (2026-04-05)

The ceiling kernelâ€™s per-cell output for a fixed song is a pure function of the integer pair:

- `fill_count = ceil(non_fever_cas * ff_factor)` (depends only on `ff_idx`)
- `d_ms = ceil(fever_time_cas * ft_factor * 1000)` (depends only on `ft_idx`)

Therefore, if multiple indices map to the same `(fill_count, d_ms)`, they must produce identical final signatures.
This enables an **exact** speed optimization:

- Compute only one deterministic representative cell per unique `(fill_count, d_ms)` pair.
- Scatter/copy those representative outputs to fill the full 161Ã—161 grid.

Implementation:

- New API helper that builds representative maps with float32-matching math:
  - `gear_optimizer/solver/taichi_gem/api/timeline.py::_build_ceiling_cell_rep_maps`
- New Taichi kernels:
  - `compute_timeline_grid_ceiling_hitsim_reps_kernel(...)`
  - `scatter_timeline_grid_ceiling_hitsim_from_reps_kernel(...)`
- Wiring:
  - `precompute_timeline_gpu(...)` uses the dedup path when `GPU_TIMELINE_CEILING_DEDUP=1` (default: **off**) and the
    number of unique pairs is smaller than the full grid.
  - Falls back to `compute_timeline_grid_ceiling_hitsim_kernel(...)` when dedup is not beneficial or on any rep-map error.

Note on default:

- On Taichi/Vulkan (AMD), “dedup then scatter” can reduce parallelism enough to lose against the fully-parallel baseline
  kernel, even when many cells share the same `(fill_count, d_ms)`. The switch remains for experiments/regressions, but
  is not enabled by default.

Verification (GPU):

- `python -m pytest -m gpu tests/test_gpu_timeline_ceiling_hitsim_cpu_gpu_exact.py`
  - Includes `test_gpu_ceiling_timeline_dedup_matches_baseline` (dedup off vs on, exact grid equality).
