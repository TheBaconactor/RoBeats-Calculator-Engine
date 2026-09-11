# Adaptive core database audit

The database replay covers every saved Base and FG witness in a read-only SQLite
snapshot of production `evolution.db`, taken at 2026-09-11 22:41:09 UTC.
It does not certify the best score over unseen loadouts, other team buffs, or all
allocations discarded by float32 selection. No production data was modified.

## Database consistency

- SQLite integrity: `ok`; no foreign-key violations.
- 115,463 Base rows across 2,264 charts: all canonical scores replay correctly.
- 42,122 FG rows across 2,131 charts: all canonical response-surface scores replay correctly.
- All 157,585 witnesses reconstruct from real catalog gear, three distinct Mini
  representatives, T5 fixed stats, and legal 90-gem allocations.
- Stored song-level Base and FG best scores match their corresponding tables.
- All 42,122 FG visible witnesses agree with their reconstructed scoring inputs.

FG's paired `score` is the source Base score; its visible allocation can have been
reoptimized for FG. The audit checks this pairing separately from the FG replay.
It does not mistake these different values for corruption. Primary and secondary
inputs are retained separately; no Base/FG scalar-equivalence assumption is used.

## Regional winner preservation

Every one of the **2,264 Base charts** preserves its best saved score. Across
**1,609,775 loadout/region evaluations**, no stored chart winner was lost and no
new chart best was found. No stored winning loadout lost its achieved score in
the restricted handoff. All stored allocations admitted by surviving timing
regions obeyed their constrained gem bounds; no checked affine bound fell below
an achieved score. The full production-control solve also matched all chart bests.

This checks the actual 64-region/nine-bound bank, region-specific gem limits,
queue pruning, real restricted GPU solve, returned witness legality, and canonical
replay on every stored Base loadout. The database best supplies the incumbent and
fit anchor, but its gem allocation is not injected into the returned result.

This is **not** a fresh full-catalog search on every chart. It cannot measure
whether a capped enumeration discovers an unseen winner, or prove that the
float32 inner selection retains every canonical contender. Matching a database
of GA results establishes best-known agreement, not global optimality. T5 is the
only team-buff domain present in this snapshot. FG witnesses were validated;
FG search speed and completeness were not benchmarked.

## Bugs reproduced and fixed

The regional solver previously assumed its prepared chart remained resident on
the GPU. After preparing B, solving A could use B's timeline. The A/B/A regression
failed with scores near 20 million instead of 2.6 million. The solver now binds
its chart through the existing timeline owner under the GPU lock before dispatch.

The host registry cache keyed gear by object identity, item counts, and fixed-item
names. Replacing a pool or fixed item without changing those keys reused stale
items. The cache is deleted; each constructor derives its IDs and maps from its
actual inputs. The changed-pool regression fails before deletion and passes after.
These changes add no fallback or recovery path. The host registry change removes
72 net lines.

The separate shared GA/core upload-ownership fix was already part of this PR.
All three state regressions have been observed failing before their fixes.
The focused current suite passes 45 tests; the full suite comparison and existing
baseline failures are documented in the main research report.

## Remaining allocation-selection counterexample

On **Kanpai (Hard) by Kagi**, loadout
`ff9cb536a04531f106e5eb8f2c044d63` has saved canonical score **66,024,847**.
The full control solver selects an allocation replaying to **66,023,473**,
**1,374 points lower**. The same result reproduces on clean main `7b46703b`.

| Allocation | FT | FF | PP | CM | FM | Overflow | GPU score | Canonical score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full timing selection | 0 | 19 | 0 | 0 | 7 | 64 | 66,025,156 | 66,023,473 |
| Saved timing pair | 0 | 20 | 0 | 0 | 7 | 63 | 66,024,847 | 66,024,847 |

Restricting the inner solve to the saved timing pair recovers its saved score.
The regional kernel over the whole timing domain reproduces the full solver's
lower canonical choice. This isolates a disagreement in timing selection and
shows why replaying one returned allocation cannot establish canonical optimality.
This is an existing solver limitation, not a new regional-pruning regression.
Both methods still recover the chart's best stored score, **66,305,104**, from
another loadout. It remains visible in the audit data instead of being called a
clean per-loadout optimality result.

## Reproduction and evidence

Run `python tools/research/audit_core_database.py --help`. Use an independent
SQLite backup made through a read-only source connection and a private cache root.
For each index 0 through 3, run:

```bash
python tools/research/audit_core_database.py \
  --db /path/to/snapshot.db --cache /path/to/private-cache \
  --regional-check --shard 0 4 --output /path/to/regional-0.jsonl
```

Change both the shard index and output name for each partition. The summarizer
requires all four completed, disjoint partitions, matching source hashes, every
chart exactly once, and exact row-count reconciliation. An incomplete run cannot
be labeled global.

```bash
python tools/research/summarize_core_database_audit.py \
  /path/to/regional-0.jsonl /path/to/regional-1.jsonl \
  /path/to/regional-2.jsonl /path/to/regional-3.jsonl \
  --output /path/to/combined.json
```

The regional workers included the chart-state and bound-preparation fixes. They
started before the host registry cache deletion. A subsequent exhaustive
comparison of all 2,264 catalog registries established identical IDs and GPU input
arrays before/after that deletion. All 157,585 rows were then reconstructed and
replayed again using the updated constructor. The artifact records these distinct
provenance steps rather than presenting them as one run of identical source.

Snapshot SHA-256:
`144b52a1000ca532c74775c17b2e42e3dc017d97d6d20b45ead922df97bd85c2`.
The four workers ran on the live production Apple M4 host with isolated caches.
Their overlapping elapsed times are not solver latency benchmarks.

[Per-chart audit results, source hashes, provenance, and the main/branch allocation diagnostic](adaptive_core_database_audit_2026-09-11.json)

[Search implementation, performance experiments, tests, and patch report](adaptive_region_core_search.md)
