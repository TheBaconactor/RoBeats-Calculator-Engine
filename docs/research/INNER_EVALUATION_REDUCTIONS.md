# Exact inner-evaluation reductions

Baseline: `7119c0c155562248f93b04ddfada542d2966521f` on `main`.
Measured locally on an Apple M4, Taichi 1.7.4, Python 3.11.9,
NumPy 2.3.5 and Numba 0.62.1. The installed NumPy/Numba versions differ
from the repository pins. GPU FG search uses f32 here; the macOS serving
path uses native CPU f64.

## Patch report

1. **Invariant.** Preserve scores, chosen gems, FT/FF identity, surface
   witnesses and tie ordering while removing repeated exact work. This is
   an optimization, not a correction to the scoring formula.
2. **First redundant work.** The Base warmstart rescored the allocation
   returned by a solver that already searched the same timing frontier.
   FG scored Great head notes as Perfect twice. The GPU surface kernel
   rebuilt a PP bound that depends only on starting PP and color weights.
   Base seed allocations were scored again when identical and when
   encountered in the exhaustive scan.
3. **Fix shape.** Return the Base solver's score; preserve the final canonical
   rescore. Fuse FG head contributions as `min(Perfect, Great)` after the
   unchanged floors, in both GPU and native CPU scorers. Build PP bounds
   once per distinct raw starting PP stat per host call, in the actual
   solver precision, and reuse them across owners and chunks. Tables are
   constructed from that call's reference values, so reference revisions
   cannot reuse stale data. Skip duplicate Base seed evaluations.

   Restrict PP dominance to `pp_primary_delta <= 0` and
   `pp_secondary_delta <= 0`. Both Great coordinates are then
   nonincreasing. For each fixed CM/FM pair, retain only strict prefix
   records of the **actual rounded Perfect base**, preserving the earlier
   PP tie winner. This avoids relying on floating-point reassociation of
   the algebraic `E(x)` expression. Mixed-coordinate cases retain the
   full PP search. No timing surfaces or GA candidates are removed.
4. **Tests.** The new operation-count regression evaluates six PP splits
   on the saved baseline and one after the reduction. Parity tests compare
   2,048 randomized scores with the original two-pass scorers, exhaustive
   FG winner rows in five color configurations, and Base warmstarts with
   unseeded/unpruned CM/FM enumeration across all 16 PP/overflow flag
   cases. Bounds are checked in f32 and f64, including negative starting
   stats, cap crossings, repeated PP states and changed references.
   Real GPU tests compare unchunked, group-chunked and surface-chunked
   output, including owner-to-bound-row mapping.
5. **Complexity.** Production code is slightly smaller overall. The only
   new production module is the surface-independent PP table builder;
   it replaces the two local 91-entry vectors and construction loops.
   It has no persistent cache or fallback path. Shared seed walks and
   deeper incumbent plumbing are intentionally outside this patch.

## Verification

The final focused run passed **26 tests**, with **4 existing platform skips**
for GPU-f64 parity on macOS:

```sh
python3 -m pytest tests/test_fg_inner_reductions.py tests/test_gpu_base_inner_reductions.py tests/test_fg_response_inner_chunking.py tests/test_fg_response_inner_gpu_parity.py tests/test_fg_response_inner_cpu_gpu_parity.py tests/test_gpu_timeline_frontier_exact_bnb.py tests/test_gpu_ga_eval_incumbent_cull.py -q
```

The existing All Right There and Aurora physical-input replay regressions
also passed. Their exact scores remain 29,340,273 and 47,502,604,
respectively. Four additional existing FG inner/batch regressions passed.

One existing test, `test_response_frontier_gpu_inner_matches_exact_replay_on_combo_floor_boundary`,
fails on this machine: GPU 12,344,801 versus expected 12,345,033. Loading
the original host and device modules from the baseline reproduced the
same failure and score. The test was not weakened or skipped.

Ruff passed on every changed Python file, and `git diff --check` passed.
The full repository suite and a production Radeon GPU run were not performed.

## Warm measurements

Each before/after result was checked for equality. Times include the host
work at the stated boundary. Two warmups precede alternating before/after
runs; the values below are medians, not a general speedup guarantee.

| Workload | Before ms | After ms |
|---|---:|---:|
| All Right There, complete CPU FG candidate, 9 gems | 3.066 | 3.014 |
| Aurora, complete CPU FG candidate, 9 gems | 3.989 | 3.367 |
| All Right There, GPU inner host dispatch, 9 gems | 10.095 | 6.736 |
| Aurora, GPU inner host dispatch, 9 gems | 18.948 | 6.126 |
| Aurora, fixed FT/FF cell, CPU inner host, 90 gems | 0.102 | 0.096 |
| Aurora, fixed FT/FF cell, GPU inner host, 90 gems | 4.341 | 3.425 |
| Base population evaluation, 64 genomes, 90 gems | 30.707 | 30.208 |

The two complete FG candidate cases cover 55 FT/FF cells each, with
2,480 and 1,768 logical surfaces. The full-budget fixed-cell case covers
17 surfaces. FG measurements use nine repetitions. The Base measurement
uses 15 repetitions and the deterministic integration fixture's synthetic
chart/loadouts through production kernels. The small Base and ordinary
CPU differences are within the observed timing variation.

These measurements do not time a full GA run. The GPU-f32 measurements
also do not represent the production Radeon GPU-f64 path.

Reproduce against the original revision:

```sh
python3 -m tests.benchmark_inner_reductions --baseline-ref 7119c0c1
python3 -m tests.benchmark_base_inner_reductions --baseline-ref 7119c0c1
```

Both tools isolate database and frontier-cache paths in temporary
directories. They save raw timings under `/tmp/robeats-inner-reductions-benchmark.json`
and `/tmp/robeats-base-inner-reductions-benchmark.json`.

## Deployment note

The existing FG cache identity fingerprints the edited scoring modules.
The new PP-bound module is included in that source list as well. This
changes the cache identity, so deployment must follow the normal frontier
prebuild process. No production caches were rebuilt or modified here.
