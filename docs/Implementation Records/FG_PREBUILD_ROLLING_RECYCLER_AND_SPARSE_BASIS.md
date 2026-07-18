# FG Prebuild Rolling Recycler and Sparse Head Basis

## Trigger

The 2026-07-17 production cold prebuild completed all `2,249 / 2,249` chart bundles but took
approximately `4 h 07 min`, versus about three hours for the previous full build. The user required
an exact build-time improvement: no stat projection, sampled keys, candidate-dependent cache,
frontier approximation, changed tie/witness policy, or CPU fallback.

## First violations

### Whole-pool recycle barrier

`BoundedRecyclingProcessPool` bounded allocator retention by collecting
`max_workers * max_tasks_per_worker` submissions, waiting for every future in that generation,
and replacing the complete executor. On this machine the completed run used a 14-worker bound and
16 tasks per worker, so admission stopped every 224 submissions until the slowest remaining chart
finished. This is a global barrier in a deliberately heavy-tailed workload.

The cache timestamps contain a direct certificate. The inter-completion gap at every exact
224-bundle boundary was:

`23.2, 43.0, 26.2, 21.2, 23.0, 10.1, 17.3, 11.8, 8.7, 4.1 seconds`

Those ten boundary gaps total `188.6 s`; they do not include the earlier utilization taper while
the other workers in each generation sit idle waiting for the straggler.

### Dense head-position scan

Every unique bounded head surface built its six mask-derived basis sums by scanning all
`head_len <= 100` positions. Preserved monster streams showed only `46.28` union-mask bits per
M1LLI0N pattern and `49.16` per Calamity pattern on average. The old loop therefore spent about
half its iterations proving that no bit was present.

## Changes

### Independently recycled worker slots

`BoundedRecyclingProcessPool` now owns one single-worker `ProcessPoolExecutor` per slot. Each slot
retains the same hard `max_tasks_per_worker` lifetime. A drained slot is recycled immediately and
independently; unrelated workers continue running. General burst callers still receive normal
`Future` objects and may queue work up to every slot's lifetime bound. If all slots are full, the
pool waits for the first slot's final future, replaces only that slot, and proceeds.

Native worker exit now poisons and replaces only its owning slot. Futures already returned from
that slot retain their explicit `BrokenProcessPool` failures. Task exceptions remain ordinary
future failures. Initializer, spawn context, public API, task results, and shutdown semantics are
unchanged.

Complexity changes from a periodic `wait(all W workers)` generation barrier to `wait(first drained
slot)` only when a burst fills every lifetime queue. Worker lifetime and retained-memory bounds
remain `T` tasks and at most `W` live worker processes.

### Ordered sparse head-basis construction

`_numba_head_surface_basis` now enumerates set bits from least to greatest with a 64-bit De Bruijn
trailing-zero index. It visits `popcount(fever_mask | great_mask)` positions instead of every
position in the head range. Fever, Great, and overlap accumulators receive the same terms in the
same ascending-position order as before; no floating-point operation is reassociated. Arbitrary
`[lo, hi)` ranges remain masked explicitly across the two 64-bit words.

The expected work changes from `O(hi - lo)` to
`O(popcount((fever | great) & range_mask))`, with the same `O(1)` storage.

## Exactness and measurements

- A 64-position trailing-zero test plus 300 randomized four-word masks over six ranges requires
  bit-identical basis tuples versus the retired ordered position scan.
- Expanded logical-bundle comparison passed all `25,921` stat keys, ordered surfaces,
  coefficients, and metadata for M1LLI0N PP Extended and Calamity Fortune.
- Preserved-stream cone replay kept the same ordered SHA-256 digests. Sparse basis construction
  improved the M1LLI0N blocked replay from `1.263 s` to `0.976 s` (`1.294x`) and Calamity from
  `0.432 s` to `0.409 s` (`1.055x`).
- Two reverse-order full-grid M1LLI0N Extended pairs measured mean frontier build
  `26.477 s -> 26.011 s` (`1.018x`) and aggregate reducer work
  `344.206 CPU-s -> 338.835 CPU-s` (`1.016x`). Calamity was neutral (`3.940 s -> 3.938 s`), as
  expected where this subphase is a small share.
- A controlled heavy-tail recycle schedule with the same tasks/results measured
  `4.180782 s -> 2.472913 s` (`1.691x`) by overlapping the next slot generation with the slow
  worker instead of imposing the complete-pool barrier.
- A real one-song production-prebuild invocation built `1 / 1` bundles with zero failures through
  the rolling pool.

No full-pool speedup is claimed without another full cold run. The timestamp certificate proves
the removed barriers existed in the completed production run; the exact wall benefit will depend
on which charts straddle future lifetime boundaries.

## Rejected exact alternatives

Preserved streams were also used to test exact contiguous-pattern local frontiers, fixed-size
hierarchical maximal-set chunks, a custom flat open-addressed seven-word seen set, and mask-ID plus
packed-body duplicate keys. Every variant produced the same ordered digest, but each added more
CPU work than it removed on at least one monster (`M1LLI0N` or `Calamity`) and was removed. The
hierarchical reducer remains a plausible Vulkan batch/tree design because its independent blocks
expose GPU parallelism, but the measured CPU implementation is not a production improvement.

There is no alternate production route, feature flag, song exception, compatibility mode, stat
projector, partial-key prefetch, or changed frontier contract.

## Verification

- `python -m pytest -q tests/test_recycling_process_pool.py` -> `5 passed`
- `python -m pytest -q tests/test_recycling_process_pool.py tests/test_startup_frontier_cache_prebuild.py tests/test_frontier_cache_prebuild_paths.py` -> `37 passed`
- `python -m pytest -q tests/test_cpu_affinity_frontier_prebuild.py` -> `8 passed`
- `python -m pytest -q tests/test_fg_response_frontier_gpu_build.py` -> `74 passed`
- `python -m pytest -q tests/test_fg_greats_side_early_fever.py` -> `10 passed`
- `python -m ruff check gear_optimizer/core/recycling_process_pool.py tests/test_recycling_process_pool.py` -> passed
- `python -m ruff check .` -> passed
- Targeted sparse-basis differential tests -> passed
- M1LLI0N and Calamity logical-bundle oracle -> passed, `25,921` stat keys each
- Full `pytest -m "not gpu" tests/` was attempted while a separate user-owned optimizer run was
  active, but produced no final result before the 10-minute command timeout; it is not counted as
  a pass.
