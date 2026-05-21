# FG Cap-Free Prefix Surface Frontier

- Date: 2026-05-20
- Status: implemented for the production GPU fused FG solve path

## Broken invariant

ForceGreats production search must not depend on arbitrary section forced-count caps or on a
packed FP/representative encoding. The exact search bound is the production-visible natural count
domain, and pruning is valid only when two prefixes are at the same future-visible timeline state.

## First violation point

The previous fused path generated max-FP rectangles before solving and carried older assumptions:
section cap tables, a standalone max-FP breakpoint request, and packed `p + 64 * rep_flag` config
values. Those were search-shaping artifacts, not optimizer invariants.

## Fix

Production fused FG tasks now submit a GPU prefix-frontier descriptor. Stage 1 expands direct
forced-count actions from `0..ceil(raw_fever_fill)` for each section, simulates the production
timeline transition, and keeps only exact non-dominated 11-word FG surfaces at the same
future-visible state.

The frontier state is `current_idx` after each section transition. The carry variables are not a
separate key in this implementation because the transition consumes `carry_time` and `carry_idx`
before insertion; every retained prefix is inserted only after fever has advanced to the next
non-fever start. If future code retains prefixes mid-transition, the key must be widened to include
those carry variables losslessly.

Materialized configs now store direct forced counts. The standalone max-FP table request is retired,
and missing frontier capacity raises at the host boundary instead of silently falling back.

## Disk cache

The cold frontier build is still expensive for large natural caps, so the GPU path now persists the
compact frontier artifact under `bin/fg_prefix_frontier_cache`, mirroring the timeline frontier cache
shape. The cache key includes:

- song timestamp signature;
- Great-candidate timestamp signature;
- total notes, long notes, and section count;
- Fever Time and Fever Fill Rate lookup signatures;
- effective `ft_idx` and `ff_idx`;
- cache algorithm version.

The payload stores only score-sufficient FG surfaces and one representative direct forced-count row
per surface:

```text
surface_signature[count, 11]
forced_counts[count, n_sections]
```

It does not cache final candidate scores. PP/CM/FM/value stats and gem budget are still scored live,
so the artifact is reusable across candidates that share the same song and effective FT/FF indices
without crossing candidate-specific scoring boundaries.

Startup now prebuilds the complete effective-FT/FF grid before live FG scoring. For each required
section count, the prebuild walks all `161 x 161` effective stat cells, skips cells already on disk,
and builds missing prefix-frontier surfaces on the GPU. Native FG prep and the finder also enforce
the same prebuild invariant for non-app entrypoints. Live scoring no longer builds missing
frontiers; a cache miss during live scoring is an error.

Measured on a synthetic high-cap probe (`natural_cap=201`, `sections=4`, equivalent explicit rows
`1,664,966,416`), cold build took about `7.01s`, the first warm run took about `1.44s` including
cached-score kernel compilation, and a disk-hot run after compilation took about `0.016s` with
identical scores.

## Tests

Updated tests assert that:

- the max-FP breakpoint kernel and `(161, 51)` cap table are removed from the active breakpoint
  kernel module;
- fused breakpoint tasks always use the cap-free GPU prefix-frontier descriptor;
- fused work budgeting uses the prefix-frontier estimate instead of section cap tables;
- implicit packed config decoding no longer depends on `FG_PLATEAU_REP_STRIDE`;
- retired `FG_COMPUTE_BREAKPOINTS` requests fail loudly.
- prefix-frontier disk artifacts round-trip exact signatures/counts and are keyed by effective
  FT/FF indices;
- full-grid prebuild visits every effective FT/FF cell and skips cells already on disk;
- a live GPU solve can load that prebuilt disk artifact and skip the frontier build kernel.

## Complexity impact

This removes the production max-FP table contract, section cap imports, and packed representative
constant. It adds one GPU prefix-frontier kernel and a small exact-capacity overflow check. The
remaining capacity is a compiled scratch-space limit, not a search cap: overflow is an error because
the exact frontier did not fit.

The cache adds a small persistent artifact owner plus upload/download staging kernels. That is extra
surface area, but it moves repeated work to a reusable exact artifact rather than reintroducing
section caps or CPU config generation.
