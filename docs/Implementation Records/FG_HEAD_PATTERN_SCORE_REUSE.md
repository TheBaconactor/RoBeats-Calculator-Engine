# FG Exact Head-Pattern Score Reuse

**Date:** 2026-07-11
**Status:** CANDIDATE; VULKAN PARITY PASSED, PERFORMANCE GATE PENDING
**Tracking:** Issue #116

## Broken invariant

The response-inner GPU scorer evaluated the complete head score once for every retained surface and
gem allocation even when multiple surfaces had byte-identical engine-owned head inputs. Those rows
can have different body counts and can win under different allocations, so collapsing them to one
representative would be incorrect. Repeating their identical head calculation is unnecessary.

## Canonical implementation

`response_inner_patterns.py` builds an owner-major CSR plan for exact `(group, head-pattern)` pairs.
Patterns retain first-seen order, and every body's original local-surface ordinal remains explicit.
The one production kernel in `response_inner_pattern_kernels.py` evaluates the head once per
allocation and pattern pair, evaluates every distinct body, and compares the full winner key:

```text
maximum score, minimum original surface ordinal, minimum (g_cm, g_fm, g_pp)
```

The host reducer applies the same score/ordinal rule across pattern pairs and dispatch chunks.
Chunking is only a dispatch-work and shape safety boundary. There is no feature flag, workload mode,
song exception, old/new route, or semantic fallback. The superseded group and per-surface kernels
and their routing branches are deleted.

The cache logic fingerprint includes the new kernel owner. Any future game-engine change to the
canonical head pattern or score formula therefore rotates incompatible cache data rather than
silently reusing it.

## Exactness

The independent native-f64 authority remains exhaustive: it enumerates every surface in original
order and does not group identical heads. A controlled Vulkan test contains repeated exact heads
with different bodies and compares all 11 winner columns for both PP-disabled and PP-enabled gem
searches. Both variants pass on the RX 7900 XTX. Focused randomized score decomposition separately
checks that `head(pattern, allocation) + body(body, allocation)` equals the original complete score.

Group upper-bound equality remains live because an equal-score row may have an earlier ordinal.
Hashes are not used for semantic equality; grouping uses exact integer pattern IDs backed by the
byte-exact pattern table.

## Measured planning memory

The CSR plan uses int32 owners, pattern IDs, offsets, and local surface ordinals. On preserved real
frontier corpora:

| Corpus | Logical rows | Exact pairs | Head reuse | New host plan | Retired host plan |
|---|---:|---:|---:|---:|---:|
| Calamity Fortune | 1,083,334 | 151,065 | 7.1713x | 6,146,120 B | 17,333,344 B |
| 200-note light chart | 262,282 | 230,524 | 1.1378x | 3,815,420 B | 4,196,512 B |

This is 64.5% less host planning memory on Calamity and 9.1% less on the light chart. Warm plan
construction measured 8.3 ms and 2.5 ms respectively. The GPU retains one int32 local-ordinal array
so it is uploaded once instead of once per dispatch.

## Acceptance gate

The candidate is not accepted on proof or reuse ratio alone. It still requires interleaved
same-session A/B builds against its immediate parent on multiple monster charts and the designated
light chart, completed-build memory anchors, ratified cache parity, and no worse than approximately
5% light regression. Any winner, witness, tie, physicality, D-bis, or cache-oracle mismatch rejects
the candidate.
