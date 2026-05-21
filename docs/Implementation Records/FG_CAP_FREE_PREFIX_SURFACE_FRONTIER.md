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

## Tests

Updated tests assert that:

- the max-FP breakpoint kernel and `(161, 51)` cap table are removed from the active breakpoint
  kernel module;
- fused breakpoint tasks always use the cap-free GPU prefix-frontier descriptor;
- fused work budgeting uses the prefix-frontier estimate instead of section cap tables;
- implicit packed config decoding no longer depends on `FG_PLATEAU_REP_STRIDE`;
- retired `FG_COMPUTE_BREAKPOINTS` requests fail loudly.

## Complexity impact

This removes the production max-FP table contract, section cap imports, and packed representative
constant. It adds one GPU prefix-frontier kernel and a small exact-capacity overflow check. The
remaining capacity is a compiled scratch-space limit, not a search cap: overflow is an error because
the exact frontier did not fit.
