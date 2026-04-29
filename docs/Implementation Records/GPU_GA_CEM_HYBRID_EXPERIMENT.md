# GPU GA CEM Hybrid Experiment

Date: 2026-04-28
Branch: `research-probability-analysis`

## Context

The optimizer already has exact-safe song-aware pre-pool pruning, exact candidate
dedupe, GPU-native GA Hybrid V2, and novelty repair. Those remove duplicate or
provably dominated work, but they do not make the remaining search converge faster
when many candidates are merely low-value rather than losslessly removable.

The new experiment adds a Cross-Entropy Method / Estimation of Distribution
tail sampler without replacing the production GA path.

## Decision

- Default production behavior stays unchanged with `GPU_GA_SearchMode = standard`.
- `GPU_GA_SearchMode = cem_hybrid` enables a host-side experimental CEM tail patch
  inside the GPU-native GA loop.
- The GPU still evaluates exact scores and performs the normal fused GA transition.
- At configured refresh intervals, the owner thread downloads the scored active
  population, learns per-slot item probability tables from per-run elites, runs the
  normal next-generation transition, then overwrites only a bounded tail slice with
  CEM-sampled genomes.
- Rare-item protection is enforced through a non-zero probability floor in the CEM
  tables. Trash suppression and breakpoint mutation bias are
  sampling weights only; they never delete items from the pool.
- Exact-safe waste removal remains the first layer. Audit-only diagnostics now expose
  gear/mini survivors, same-projection removals, and timing-neutral dominance removals
  without changing the production pruning path.

Experimental config:

```ini
GPU_GA_SearchMode = standard
GPU_GA_CEMEliteFrac = 0.10
GPU_GA_CEMSmoothing = 0.25
GPU_GA_CEMMinProb = 0.002
GPU_GA_CEMRefreshEvery = 5
GPU_GA_CEMTailReplaceFrac = 0.30
GPU_GA_RareItemProtection = true
GPU_GA_TrashSuppression = false
GPU_GA_BreakpointMutationBias = false
```

## Guardrails

- CEM cannot own the whole population; `tail_replace_frac` is clamped to `<= 0.50`.
- CEM does not remove items; every probability table is floor-normalized.
- Minis are sampled without replacement when at least three minis are available.
- Hybrid mode no longer raises the normal GA random-immigrant rate by default. The
  initial `0.15` floor caused shallow-depth base-score regressions and prevented
  delayed CEM from being a true plateau-only intervention.
- Lossless pruning diagnostics are explanatory only; the runtime pruning rules remain
  the existing same-slot relevant-stat equivalence, timing-neutral dominance, mini
  multiplicity, and current-three-dominator checks.
- Promotion requires A/B evidence including FG-overall retention and no FG backlog
  regression, not GA-only songs/hour.

## Verification

- `python -m pytest -q tests/test_song_aware_pre_ga_pruning.py tests/test_ga_cem_hybrid.py tests/test_gpu_native_ga_retry_generated_populations.py --tb=short`
- `python -m pytest -q -m gpu tests/test_gpu_ga_ops.py::test_gpu_ga_initial_population_buffer_roundtrip --tb=short`
- `python -m ruff check gear_optimizer/core/utils.py gear_optimizer/helpers/ga_helpers/cem_hybrid.py gear_optimizer/solver/genetic.py gear_optimizer/solver/native_inflight_prepare.py gear_optimizer/solver/solver_common.py tests/test_ga_cem_hybrid.py tests/test_gpu_native_ga_retry_generated_populations.py tests/test_song_aware_pre_ga_pruning.py`
- `python -m ruff format --check gear_optimizer/core/utils.py gear_optimizer/helpers/ga_helpers/cem_hybrid.py gear_optimizer/solver/genetic.py gear_optimizer/solver/native_inflight_prepare.py gear_optimizer/solver/solver_common.py tests/test_ga_cem_hybrid.py tests/test_gpu_native_ga_retry_generated_populations.py tests/test_song_aware_pre_ga_pruning.py`
- `git diff --check`

## A/B Reproduction

Added `tools/bench/bench_cem_hybrid_ab.py` to create paired standard/CEM configs,
run the existing GA winner-stability benchmark, and report base, FG, duplicate, and
FG-debt deltas.

Current measured signal on `2NITE (Hard) by nanobii`:

- Direct pipeline, depths `25,50,75`, seeds `1337,1338,1339`:
  - depth 25: CEM was worse on mean base score by `239,465` and duplicate ratio was
    slightly higher.
  - depth 50: CEM matched base/FG means and reduced duplicate-genome ratio by `7.85`
    percentage points.
  - depth 75: CEM matched base/FG means and reduced duplicate-genome ratio by `6.65`
    percentage points.
- Inflight pipeline, depth `50`, seed `1337`:
  - CEM matched base score, improved FG score by `22,521`, reduced duplicate-genome
    ratio by `9.41` percentage points, and added no FG debt.

Conclusion: the feature has a reproducible waste-reduction signal and can preserve or
slightly improve FG in at least one production-like run, but it does not yet show a
reliable top-base-score convergence win. Keep default `standard` and treat CEM as
experimental until broader A/B proves score gains without rare-winner regressions.

Broader direct-pipeline peak check:

- Command family: six Easy/Normal/Hard songs, depths `15,25,50,100,200`, seeds
  `1337,1338`, paired `standard` vs `cem_hybrid`.
- Output: `artifacts/runcheck/cem_broad_peak/summary.json`.
- Observed best base score was reached by depth `100` for all six cases; depth `200`
  did not improve the observed base mean in any case.
- CEM first reached the best observed base mean earlier than standard in `0 / 6`
  cases, tied standard in `4 / 6`, and lagged standard in `2 / 6`.
- At depth `50`, CEM was closer to the best observed base mean in `1 / 6` cases
  (`(The) Red Room (Hard)`), tied in `3 / 6`, and lagged in `2 / 6`.
- At depth `25`, CEM lagged standard in all six cases.
- Duplicate-genome ratio improved at depth `50` in `5 / 6` cases and at depth `100`
  in `5 / 6` cases, but was not reliably better at depth `200`.

Updated conclusion: the default CEM hybrid is not ready as a convergence-depth
reducer. It is still useful as evidence that elite-guided tail sampling can cut
duplicate waste around the plateau, but promotion should wait for a schedule/tuning
change that improves pre-peak scores rather than only plateau hygiene.

Follow-up after removing the implicit immigrant floor:

- Output: `artifacts/runcheck/cem_delayed_plateau_no_immigrant_floor/summary.json`.
- Default CEM at depth `50` improved duplicate-genome ratio in `5 / 6` cases, had
  one base-score gain, one base-score loss, and four ties versus standard.
- Default CEM at depth `25` still lagged standard in `5 / 6` cases, but the average
  base-score regression dropped versus the earlier immigrant-floor run.
- Delayed CEM with `GPU_GA_CEMRefreshEvery = 50` now truly matches standard at depths
  `25`, `50`, and `100`; it did not produce meaningful duplicate reduction until
  depth `200`, so it is not useful as configured.

Conclusion after the floor removal: keeping CEM isolated from GA immigrant policy is
better and safer, but CEM is still not a proven faster winner finder. The best current
role is optional plateau duplicate hygiene.
