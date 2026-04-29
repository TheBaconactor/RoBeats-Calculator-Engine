# Timeline V2 Fast Exact Envelope Research

- Date: 2026-04-28
- Branch: `research-probability-analysis`
- Status: Research-only; not implemented in production
- Scope: cheap exact timing-envelope certificates, explicitly avoiding full Bellman / interval DP

## Question

The full Bellman / interval DP direction was previously documented as too slow for the production runtime. The target here is narrower:

- exact where a cheap certificate proves exactness
- super fast and GPU-shaped
- no full exact fallback
- no CPU production stall
- no increase in search depth

The right contract is therefore not "full timing exactness". It is:

> Return an exact singleton timing surface when a cheap proof holds; otherwise return unknown and keep the existing bounded frontier behavior.

## Current Baseline

`compute_timeline_grid_ceiling_envelope_kernel(...)` already contains most of the analytical machinery:

- chord grouping from chart timestamps
- Perfect-window carry interval propagation
- boundary-band search around each fever deadline
- four generated timing surfaces per `(FT, FF)` cell
- exact duplicate / universal dominance compaction over the generated surfaces
- optional exact representative-cell dedup by `(fill_count, d_ms)`, default off because it can lose Vulkan parallelism

The important correction is that representative-cell dedup is already implemented as an exact experimental path. It is not a missing 5,000x item.

## V2 Candidate: Zero-Swing Singleton Certificate

For a fixed song and `(fill_count, d_ms)` cell, maintain a reachable activation-carry interval `[r_lo, r_hi]`.

For a fever activation at chord group `s`:

- `Q_min = group_base[s] + r_lo + d_ms`
- `Q_max = group_base[s] + r_hi + d_ms`
- `global_high = max(group_high)`
- `global_low = min(group_low)`

Any group with base time inside this band may swing fever membership:

```text
[Q_min - global_high, Q_max - global_low)
```

If there is no chord group in that band after the activation group, then every later group is classified identically across all feasible Perfect-window paths:

- groups before the gap are always in fever
- the first group after the gap is always out of fever
- the fever end note index is deterministic

Apply this inductively across all fever activations. If every activation has no reachable swing band, the timing surface is a singleton:

```text
(head fever mask, body fever count, body normal count)
```

This is exact over the modeled grouped Perfect-window timing paths. It may reject exact cells because the carry interval and global low/high band are conservative, but it should not accept an inexact cell.

## What It Is Not

- Not full Bellman exactness.
- Not expected value / Q2 Markov DP.
- Not a replacement for the current generated frontier on unknown cells.
- Not a proof that the four generated surfaces are sufficient globally.
- Not a production implementation.

If implemented later, the safe production shape would be:

```text
if zero_swing_singleton_certified:
    write one exact timing surface
else:
    keep current generated compacted frontier
```

That preserves correctness scope because it only narrows cells that have a proof.

## Research Harness

Added `tools/verify/audit_timeline_v2_envelope.py`.

It provides:

- `certify_zero_swing_singleton(...)`
- tiny brute-force validation for synthetic grouped envelopes
- real-song auditing over unique `(fill_count, d_ms)` pairs and weighted 161x161 grid-cell coverage

Added `tests/test_timeline_v2_envelope_research.py`.

The test covers:

- a separated-boundary synthetic envelope where the certificate matches exhaustive brute force
- a boundary-band synthetic envelope where the certificate correctly refuses to certify

## Experiment Results

Commands:

```powershell
python tools\verify\audit_timeline_v2_envelope.py --self-test
python tools\verify\audit_timeline_v2_envelope.py --song "Data\Hard\Endless Rain (Hard) by seatrus (feat. marumoko).txt"
python tools\verify\audit_timeline_v2_envelope.py --song "Data\Easy\Endless Rain (Easy) by seatrus (feat. marumoko).txt"
python tools\verify\audit_timeline_v2_envelope.py --song "Data\Normal\Endless Rain by seatrus (feat. marumoko).txt"
python tools\verify\audit_timeline_v2_envelope.py --song "Data\Easy\Aether (Easy) by Geoxor.txt"
python tools\verify\audit_timeline_v2_envelope.py --song "Data\Hard\Body (Hard) by Rutra.txt"
python tools\verify\audit_timeline_v2_envelope.py --song "Data\Hard\Everything Will Freeze (Hard) by UNDEAD CORPORATION.txt"
python tools\verify\audit_timeline_v2_envelope.py --song "Data\Hard\Exit This Earth's Atomosphere (Hard) by Camellia.txt"
```

| Song | Notes | Unique-pair coverage | Grid-cell coverage |
| --- | ---: | ---: | ---: |
| Aether (Easy) | 231 | 4,980 / 7,245 = 68.74% | 14,733 / 25,921 = 56.84% |
| Endless Rain (Easy) | 628 | 4,502 / 13,685 = 32.90% | 6,667 / 25,921 = 25.72% |
| Endless Rain (Normal) | 981 | 3,156 / 15,456 = 20.42% | 3,765 / 25,921 = 14.52% |
| Endless Rain (Hard) | 2,281 | 174 / 18,998 = 0.92% | 203 / 25,921 = 0.78% |
| Body (Hard) | 753 | 1,602 / 14,490 = 11.06% | 2,910 / 25,921 = 11.23% |
| Everything Will Freeze (Hard) | 3,046 | 533 / 22,701 = 2.35% | 546 / 25,921 = 2.11% |
| Exit This Earth's Atomosphere (Hard) | 1,878 | 3,442 / 18,676 = 18.43% | 4,351 / 25,921 = 16.79% |

The Python verifier wall time is not the production-speed estimate. It is a scalar audit implementation. The useful measurement is coverage: how often this exact certificate would replace the current generated frontier.

## Verdict

The zero-swing singleton certificate is clean, exact, and GPU-shaped.

It is not enough to be the main Timeline V2 win on hard landscapes. Endless Rain Hard, the motivating hard-landscape sample, certified less than 1% of grid cells. That means this should not be pursued as a universal replacement for the current ceiling frontier.

It is still useful as a small exact fast path, especially for Easy/less dense charts, but only if a future benchmark shows that replacing current four-variant work with singleton writes improves wall time without harming GPU occupancy. Given the current evidence, it is Tier 3/4, not the next big theorem.

## Next Theorem Target

The next promising exact direction is not more zero-swing checking. It is a small exact Pareto frontier theorem:

> Can all feasible timing surfaces be reduced to a bounded non-dominated frontier under the existing score-monotone dominance rule?

If that frontier is not bounded tightly, full exactness remains incompatible with the production speed target.
