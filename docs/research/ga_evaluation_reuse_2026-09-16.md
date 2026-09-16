# Exact GA evaluation reuse — implementation and review

Target: **RoBeats-Calculator-Engine**. Baseline: `65787ab5`, with the preceding startup-compression fix applied to both versions. Measurements used Apple M4 / 16 GB, Python 3.11.9, Taichi 1.7.4 / Vulkan.

## Patch report

1. **Invariant:** reusing an evaluation must preserve its complete winner: score, FT/FF combination, gem counts, and tie ordering. The original scoring was correct but repeated work across generations.
2. **First violation point:** generation preparation discarded winners before the evaluator searched the same seven aggregated stats again. Review also caught a draft bug: changing budget without reaggregating could retain a stale live winner.
3. **Fix:** device lookup restores only entries whose complete seven-stat key and scoring context match. Every miss clears its live winner before exact evaluation. One deterministic writer publishes each cache slot. Hash collisions cause recomputation, never result substitution.
4. **Tests:** the repeated-generation regression failed before with 61 pending unique rows; it now has zero, with identical packed keys and gems. Exhaustive evaluation, complete GA payload, collision, context, database, and service checks are described below.
5. **Complexity:** 226 fewer production lines in this GA change. Removed obsolete sorting/reuse kernels and duplicated aggregation; added one 81-line device module. Fixed cache storage is 896 KiB. No dependencies, settings, fallback modes, or per-generation host readbacks were added.

The genetic search remains heuristic. This change preserves its existing search and results; it does not establish a globally optimal loadout.

## Performance

Real runs used default search settings: 125 generations, three starts, 705 genomes per start, seed `20260915`. Existing timeline/FG frontiers were reused. Each process wrote to a separate temporary `evolution.db`.

| Measurement | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Comfort Zone, T5 / perfect window: warmed full process | 27.54 s | 27.26 s | 1.0% |
| Comfort Zone: recorded search stage | 21.85 s | 18.55 s | 15.1% |
| Aurora, T4 / zero ms: warmed full process | 23.08 s | 21.74 s | 5.8% |
| Aurora: recorded search stage | 17.02 s | 13.57 s | 20.3% |
| Controlled GA fixture: median of five alternating trials | 2.506 s | 0.532 s | 78.8% |

The recorded `ga_gpu` stage includes GA and exact FG candidate scoring; it is not pure GPU execution time. The controlled fixture runs the production GA with a deterministic 400-note chart, three starts, 64 genomes, and 125 generations. Both implementations were warmed first; every complete returned payload matched. Its high reuse rate makes it unsuitable as an end-to-end speedup claim for arbitrary songs.

Fresh-process startup varied substantially. For example, the first Comfort run after the final kernel-source edits took 50.02 s; its subsequent run took 27.26 s. Taichi's existing offline-cache directory hashes all kernel-package source contents, so edits cause compilation again. No cold-start improvement is claimed. Overall runtime gains are smaller than evaluation gains.

## Correctness and impact review

| Area | Check and outcome |
| --- | --- |
| Exact winner and ties | Full packed score/combination key and all four inner gem counts are restored. Exhaustive-reference parity passes; the reference explicitly clears memoized results. |
| Collisions and bounds | Full seven-stat equality guards every hit. Forced collisions pass at two rows and the full 4,608-row capacity, including coherent keys/gems, signed stat extremes, duplicates, and missing winners. |
| Context changes | Budget, gem scale, slot, FT/FF caps, and all 12 color flags invalidate reuse. Actual reference-table and timeline uploads clear it, including replacement in the same slot and timing-mode changes. |
| Lifecycle | New run batches and runtime resets discard entries. No changes to population identities or RNG. Batch-width and fused/standalone generation parity tests pass. |
| Candidate selection and FG | Complete old/new GA payloads match. Candidate decoding, sufficient-key, FG selection, deferred payload, and native pipeline checks run. Final materialization still uses the existing exact solver. |
| Shared Skyline state | Live Skyline field aliases were retained. Its macOS Vulkan warmup/evaluation smoke test passes. |
| Disk caches | Frontier producer fingerprints and formats are unchanged. Compatibility/manifest tests and real cache-hit runs were checked. One already-failing test expects an obsolete literal fingerprint. |
| Database | Compared every table and every non-timestamp column, including raw packed BLOBs, encoding IDs, gems, FG details, hashes, and counters. All match; SQLite integrity checks return `ok`, with no foreign-key violations. |
| Service | The first real JSON worker response contains 51 identical complete loadouts. The second request fails during GPU runtime initialization on both baseline and changed code; a successful multi-request worker run could not be verified. |

### Database evidence

The production database was not modified. Real pipeline runs used isolated databases, starting empty and then reusing saved results. Final comparisons used SQLite's backup API so committed WAL contents were included.

| Final table | Comfort Zone, each version | Aurora, each version |
| --- | ---: | ---: |
| `songs` | 1 | 1 |
| `gear_name_encoding` | 271 | 271 |
| `mini_name_encoding` | 90 | 90 |
| `team_buff_loadouts` | 51 | 51 |
| `team_buff_fg_loadouts` | 41 | 15 |
| Song lifetime / since-improvement attempts | 4 / 4 | 2 / 2 |

Best base/FG scores remain **2,631,111 / 2,640,066** for Comfort and **11,265,750 / 11,276,863** for Aurora. No database migration or persisted cache is introduced.

## Verification results and limits

Final selected suite: **358 passed, 23 failed, 1 skipped across 60 files**. Every failure was rerun against the baseline and reproduced. They concern canonical FG persistence fixtures, progress expectations, malformed chart fixtures, and the obsolete fingerprint assertion. The skipped test requires Windows NTFS compression. A separate legacy retry-fixture suite also reproduced six baseline failures involving its incomplete fake GPU fields. These tests were not weakened or removed.

All new cache regressions, exhaustive GPU parity, batching, decoding, and Skyline smoke checks pass. Ruff and `git diff --check` pass. Tests run on this Mac do not verify other GPU drivers or the entire repository.

### Ponytail review

Reviewed the final diff using [ponytail-review](/Users/server/.codex/skills/ponytail-review/SKILL.md). Related obsolete kernels, duplicated aggregation, redundant fixture wrapping, and stale benchmark assumptions were removed. The four cache fields serve exact matching, the complete winner, and deterministic publication; none is speculative.

Complexity-only conclusion: **Lean already. Ship.** The baseline failures and worker limitation above remain separate correctness concerns.

## Reproduction artifacts

Raw logs, baseline source, benchmark scripts, complete worker responses, environment/configuration, and verified database snapshots: `/tmp/robeats-ga-reuse-review/` (temporary storage).

- `benchmark_warm_ga.py`, `warm_ga_benchmark.json`: warmed alternating comparison with complete-payload assertions.
- `warm_real_runtimes.json`, `final_runtimes.json`, per-case stage logs: real-process measurements.
- `compare_databases.py`, `database_comparison.json`: all-table comparison and integrity checks.
- `review_test_files.json`, `broad_tests.log`, `baseline_failures.log`: exact test selection and baseline reproduction.

From the repository, rerun the recorded selection with `python3 -m pytest -q` followed by the paths in `review_test_files.json`. The temporary macOS test launcher used `-ApplePersistenceIgnoreState YES` solely to suppress Python's restore-windows dialog after an earlier shader compilation crash; it did not change global settings.
