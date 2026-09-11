# Shared-budget outer-core search

Experiment date: 2026-09-11. Scope: Base top-1 research, with a separate broad FG bound.

This is the real-catalog go/no-go experiment for replacing full loadout-frontier
construction with inexpensive exclusion proofs. Run it separately from the
production GA+FG pipeline:

```bash
python -m pip install -r requirements-dev.txt
python -m tools.research.measure_core_bounds \
  --song 'Data/Hard/Aurora (Hard) by Creo.txt' \
  --song 'Data/Hard/All Right There (Hard) by BSlick feat CG5.txt' \
  --output core-bounds.json
```

The tool verifies that production `gear_optimizer/` code matches its requested
`--baseline-ref` (default `origin/main`). It creates temporary runtime/cache
directories, uses the canonical T5 configuration and Perfect-window timeline,
and writes only its requested JSON report. It does not update leaderboards.
SciPy is a development dependency for coefficient fitting, not a runtime
dependency of the production optimizer.

## Search and coverage

1. Materialize every catalog Mini for this song, including ascension and song
   targets. Preserve all six gear pools and all distinct named Mini witnesses.
   The bound domain does not use the GA's Mini color filter, pool quotient, or
   skyline. There is no cross-song item-bound cache.
2. Run a short legal GA seed (64 genomes, 10 generations, one run), and replay
   its returned gems with the authoritative f64 Base scorer. The reference GA
   uses 705 genomes, 125 generations and three runs. The report includes every
   timed sample and all settings. Repeated seeds do not supply a stronger
   incumbent: the core uses the first short seed's witness.
3. Fit and validate a bank of nine log-affine bounds over raw additive
   `(PP, CM, FM, FT, FF, 2*primary + secondary)` coordinates. Apply caps only
   inside the lookup functions, including their negative and over-cap tails.
4. Bound all-Perfect fever counts using **every** response in each canonical
   Base timing cell. Start with the whole raw timing region, then split the
   unresolved region with the largest bound. Maxima cover the entire rectangle,
   not just its endpoints. Raw intervals include the lookup cap tails.
5. Accumulate item losses and visit only surviving partial gear/Mini families.
   A suffix's Mini support uses its top three distinct remaining indices.
   Deduplicate completed witnesses across timing regions before scoring.
6. Submit every surviving loadout to the existing exact-inner registry GPU
   solver in batches, validate its slot membership, distinct Minis, gem budget
   and stat-gem caps, then canonically replay every returned allocation.

`--regions`, `--max-nodes`, and `--max-witnesses` bound experimental work.
Hitting an enumeration limit returns `core_complete=false` and does not report
an improvement or a certificate. A timing refinement limit leaves unresolved
regions available for the family search; it is not a candidate cutoff.

## The bound and its arithmetic

For a completed loadout, let `B = 2*P + S + R_PP(PP)`, `c = R_CM(CM)`, and
`f = R_FM(FM)`. A count bound is `B*c*(N-F + F*f)`. Removing floors and Great
penalties is optimistic; head notes can be bounded more tightly than treating
them all as full combo.

Let `a_i = min(i/100, 1)`, `A = sum(a_i)`, and `A_F` be the sum of the largest
`F` ramp coefficients. For `c_min <= c`, define:

```
d = F - A_F
normal = (N - A - d)/c_min + A - A_F
fever  = A_F + d/c_min
S <= B*c*(normal + fever*f)
```

This optimistically puts fever on the largest ramp positions. All coefficients
are nonnegative. The same penalty-free inequality covers FG schedules when
their fever count is covered; the probe uses `F=N` for its separate FG bound.
**A Base timing cache is never used to certify FG.**

For positive `lambda`, `log(B) <= lambda*B - log(lambda) - 1`. Each other
intercept is the maximum residual over the actual finite lookup values. No
concavity or local-tangent assumption is required. Timing-region terms have
the form `w*z - min(w*lo,w*hi) >= 0` on the region.

The resulting affine support is the fixed contribution, six slot maxima,
three largest distinct Mini contributions, and
`90 * max(0, max_gem(weight dot gem_delta))`. The shared budget is spent once.
Different stat-gem and elemental contributions come from the production stat
writer rather than a second set of gem constants.

LP fitting uses ordinary floats inside a bounded coefficient box. It proposes
coefficients only: even imperfect fitting cannot authorize an invalid prune.
The coefficients are quantized to integer multiples of `2^-36`, and all
intercepts are recomputed after quantization. Logs are enclosed by a rational
atanh series after power-of-two range reduction, with an explicit geometric
tail bound. The incumbent uses a lower log endpoint and bounds use upper
endpoints. Subsequent support, item-loss, and threshold calculations use
integers. `exp` is only used for human-readable report values.

The score bound includes `gamma_32` for float32 input conversions and pre-floor
operations, which also covers the shorter f64 scoring expressions. The probe
rejects domains outside its normal, non-overflow float32/int32 proof range.
Strict `< incumbent` pruning preserves tied witnesses.

## What the result means

`core_complete=true` means that every catalog loadout was either excluded by
the regional bounds or retained for an inner solve. It does **not** mean that
f32 GPU gem selection has proved the f64 optimum. Canonical replay validates
returned allocations; it cannot recover an allocation lost to GPU rounding.
`optimality_certified` is therefore only true when bounds alone exclude all
remaining regions around the legal incumbent.

The comparison measures Base top-1 work. It does not implement FG regional
coverage, prove either complete top-51 ranking, or replace the production
GA+FG contract. The FG count-bound report uses the legal all-Perfect incumbent
and covers all schedules with `F=N`; it does not assert FG certification.

The timing report separates shared chart preparation from search work. Its
core total includes obtaining the short seed, fitting and validating bounds,
family enumeration, registry/witness preparation, inner scoring and canonical
replay. The GA timing is the median of the reported warm repetitions; the
bound/core stages are measured once per chart. This is a benchmark, not a
whole-service throughput or latency-distribution claim.

## Measured results (2026-09-11)

[Full machine-readable results](shared_budget_core_results_2026-09-11.json) preserve every GA timing sample, seed, returned witness, and phase time.

Baseline: `e7b80c06bca6028764d10af2002c9375e66aaaa5`. Host: macOS 26.5.2, ARM64, Python 3.11.9, NumPy 2.3.5, Numba 0.62.1, SciPy 1.15.3, Taichi 1.7.4 / MoltenVK. The source and host runtime are identical for both arms. These installed NumPy/Numba versions differ from the repository runtime pins; the result is a host benchmark, not a pinned-environment release qualification.

| Chart | Notes | Core loadouts | GA + replay | Seed + bounds + core + replay | Speedup | Canonical Base score, both |
|---|---:|---:|---:|---:|---:|---:|
| Aurora (Hard) | 1,709 | 15,844 | 44.01s | 26.47s | 1.66x | 55,268,089 |
| All Right There (Hard) | 1,048 | 1,542 | 41.69s | 11.38s | 3.66x | 31,110,912 |
| Sky Gazer (Hard) | 1,659 | 16,032 | 45.17s | 27.92s | 1.62x | 44,378,197 |
| Scattered Faith (Full Version, Hard) | 6,503 | 17,282 | 45.47s | 31.15s | 1.46x | 151,280,505 |

Each catalog contains 767,196,551,721,600 six-gear/distinct-three-Mini loadouts. Every tested core enumeration completed, and every retained loadout received an inner solve and canonical replay. Both the short and baseline GA scores repeated identically across their three timed runs. The core recovered the higher baseline score from its own weaker short seed on three charts; the Scattered Faith short seed already matched the baseline.

Shared chart preparation was recorded separately: 31.73s for the first cold chart and 0.63–0.95s for the later charts. Adding that shared cost to both arms still leaves every measured case faster. The core stages were measured once per chart, so these results do not establish a production latency distribution.

The broad FG bound excluded none of the 106,470 three-slot gear prefixes on these four charts. No FG speedup or full f64 optimality certificate is established. The go/no-go result is **promising for Base top-1; further FG and numerical work is required before production adoption**.

## Validation

- `python -m pytest -q tests/test_core_bound_probe.py tests/test_repo_guardrails.py tests/test_profile_loop_forever_guard.py`: **44 passed**, including 22 new bound/core tests.
- `python -m ruff check .`: passed.
- `python -m tools audit`: passed (existing `__init__` short-name ambiguity reported).
- The four-chart GPU benchmark above completed with all retained loadouts scored and identical canonical best scores.
- `python -m pytest -m 'not gpu' tests/`: 1,366 passed, 134 failed, three skipped and 103 deselected in the initial full-suite run. Replaying all 134 failing test IDs on a clean checkout of baseline `e7b80c06` reproduced **133 failures**. The remaining profiling-flag test passed in that rerun and in the final focused branch run. The broad suite is not green; no unrelated tests were changed or weakened.

## Patch report

- **Invariant:** exclude a family only if every legal completion is below a
  canonically scored incumbent. Budget, raw-stat, timing and numerical coverage
  are all part of that statement.
- **First violation point to avoid:** constructing an outer candidate shortlist
  before establishing coverage. A heuristic pool or a Base-only timing bound
  cannot silently become a global FG search universe.
- **Fix shape:** establish coverage at the catalog/family producer, then reuse
  existing inner scoring for survivors. Production solver behavior is unchanged.
- **Tests:** exhaustive small universes cover shared gems, negative raw stats,
  cap tails, non-concave tables, accumulated losses and tied witnesses. Separate
  tests cover forced-Great masks, f32 rounding, region limits/interior maxima,
  full timing-surface coverage, and song-specific Mini materialization.
- **Complexity:** adds a focused research probe, its arithmetic/fit/domain/search
  helpers and one development dependency. It constructs no gear/Mini skyline,
  adds no production feature flag, and introduces no replacement scoring model.
