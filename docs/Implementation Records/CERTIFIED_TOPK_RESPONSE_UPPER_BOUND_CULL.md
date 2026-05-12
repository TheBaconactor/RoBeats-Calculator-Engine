# Certified Top-K Response Upper-Bound Cull

Date: 2026-05-11

## Invariant

During score-only base candidate retention, a timing response may be skipped only when a certified score upper bound proves it cannot enter the current legal top-k set or improve an already achieved product-local score.

The production cull uses a strict global top-k rule:

```text
skip response r when UB(r) < T_K
```

where `T_K` is the current kth score in the streaming heap and every heap score came from a legal exact GPU evaluation. Strict `<` preserves top-k tie candidates unless the tie-break key is also bounded.

The Vulkan warmstart kernel also uses the same bound against the lane-local legal incumbent as:

```text
skip response r when UB(r) < local_best + 1
```

Because exact scores are integral, this is equivalent to `UB(r) <= local_best`.

## Upper Bound

For a timing response with remaining non-timing budget `L`, current stats:

```text
PP, CM, FM, primary, secondary
```

and lane weights:

```text
w_PP, w_CM, w_FM, w_OV
```

the cull computes a relaxed upper score by simultaneously maximizing:

```text
PP* = min(160, PP + 2L)
CM* = min(160, CM + 2L)
FM* = min(160, FM + 3L)
B*  = 2*primary + secondary + L * max(w_PP, w_CM, w_FM, w_OV)
```

The timing surface is also relaxed by scoring all visible body and head notes as fever. This may overestimate heavily, but it cannot underestimate the exact base score under the project stat-reference invariant that fever multiplier is nondecreasing and never below normal note value.

## Production Placement

The cull is applied in the score-only registry base evaluation path before calling `optimize_core_device_exact_bound(...)`.

Retained candidate materialization still rebuilds payloads through the full evaluator. FG remains scoped to the retained top-k policy and does not use this as an FG-visible prune certificate.

## Why It Is Lossless

If `UB(r) < T_K`, then every exact allocation under response `r` scores below the current kth legal retained score. There are already at least `k` legal candidates at or above `T_K`, so `r` cannot be needed for the final top-k base set.

If `UB(r) <= local_best`, then response `r` cannot improve the product's exact score because the product has already achieved `local_best` legally.

The seed and heap order may be heuristic; correctness only relies on the threshold scores being legal.

