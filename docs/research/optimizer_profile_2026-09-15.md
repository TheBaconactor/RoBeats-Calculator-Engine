# Standalone optimizer profile — 2026-09-15

Target: **RoBeats-Calculator-Engine**, running `python3 main.py` directly.

## Measurement

Apple M4, 16 GB RAM, Python 3.11.9, Taichi 1.7.4/Vulkan. Real chart: **Comfort Zone (Easy) by KepoWorld**, T5, perfect-window scoring, default search settings, seed `20260915`. One song/repeat; temporary input copies and separate result databases. Existing disk frontiers were reused; no frontiers were built.

| Run | Process wall time |
| --- | ---: |
| Initial, uninstrumented | 84.37 s |
| Python + GPU profile | 82.10 s |
| Repeat, uninstrumented | 61.30 s |

Each run started a fresh process. These are observations on one chart, not a measured code speedup or steady-state service throughput.

All three returned 51 loadouts with matching loadout hashes and base/FG scores. Best base: **2,631,111**; best FG: **2,640,066**.

## Profile

| Work | Recorded time |
| --- | ---: |
| Taichi native `compile_kernel` calls, including cache handling | 23.07 s |
| Startup filesystem compression, two passes | 18.41 s |
| GA evaluation path | 17.12 s |
| Exact FG CPU scorer invocation, including any first-use JIT overhead | 6.31 s |

These measurements overlap; do not add them. Yappi captured all-thread wall time. Taichi reported **15.54 s** across 976 device launches, including warmup. Largest kernels: generation update **4.71 s**, duplicate detection **3.01 s**, warmstart search **2.54 s**, lane reduction **2.33 s**.

## Optimization opportunities

1. **Remove repeated compression from cache-hit startup — implemented September 16 below.** [The eligibility check](../../gear_optimizer/solver/taichi_gem/force_greats/response_cache_store.py#L679) treats allocated bytes ≥ logical bytes as needing compression. After three runs, 1,720 sidecars still qualified. Startup revisited the entire directory for both timing modes, even on manifest hits.
2. **Reduce first-use compilation.** Inspect the statically unrolled [warmstart lane reduction](../../gear_optimizer/solver/taichi_gem/kernels/ga_eval/warmstart.py#L170). Benchmark a smaller compilation footprint while preserving exact winner/tie selection. The subsequent [reuse review](ga_evaluation_reuse_2026-09-16.md) found a second-request GPU initialization failure in the existing persistent worker on this Mac.
3. **Benchmark cheaper exact deduplication.** [Duplicate detection](../../gear_optimizer/solver/taichi_gem/kernels/ga_eval/reuse.py#L40) compares each genome with preceding genomes: quadratic worst-case work. Any replacement must preserve all seven stats and the lowest-index representative. The subsequent [reuse change](ga_evaluation_reuse_2026-09-16.md) avoids repeat evaluations across generations; pairwise deduplication remains for cache misses.

## Verification and artifacts

The September 15 profiling introduced no production source changes. Focused existing cache tests: **13 passed** (`test_frontier_cache_prebuild_paths.py`, `test_frontier_cache_manifest_mtime_invariance.py`). This does not establish whole-repository correctness or global optimality of the genetic search.

Raw logs, per-run environment/configuration, isolated databases, `python.prof`, `kernels.json`, `stages.json`, and result comparison are under `/tmp/robeats-calculator-engine-profile/` (temporary storage).

## Lossless startup change — September 16

Same chart, seed, settings and existing caches; fresh processes and empty result databases:

| Measurement | Before | After |
| --- | ---: | ---: |
| Full process | 63.28 s | 51.68 s |
| FG cache startup | 32.1 s | 0.1 s |

Observed end-to-end reduction: **18.3%**. One before/after pair; other startup/search costs varied, so the cache-phase saving does not translate directly to total runtime.

1. **Broken invariant:** valid cache reads should not trigger filesystem compression.
2. **First violation:** `_run_fg_response_frontier_cache_prebuild_for_mode` routed manifest hits through maintenance based on compression eligibility; incompressible files kept qualifying.
3. **Fix:** return validated hits without compression. Preserve manifest repair, missing-cache building, and locked explicit maintenance. Restored pools can use the existing `maintain_provisioned_fg_response_frontier_cache()` entry point. Scoring and search settings are unchanged.
4. **Tests:** both cache-hit regressions failed before and passed after; **46 focused tests passed**, plus Ruff. All **51 complete decoded loadout records** matched exactly, including gems, base scores and FG details. Both output hashes: `126f6b125c3806745c3d8b58a29898afa842ea15e1d50d0fd7257b9580529d32`.
5. **Complexity:** removed the obsolete directory-probe helper and exports; **19 fewer production lines**, no new flags or abstractions.

Before/after logs, databases, timing and comparison: `/tmp/robeats-calculator-engine-profile/lossless_2026-09-16/`.
