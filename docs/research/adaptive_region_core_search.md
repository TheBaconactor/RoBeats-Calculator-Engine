# Adaptive regional Base core search

This iteration optimizes time to a strong **canonical Base score**. It is a research
runner, not the production search policy, an FG solver, or an optimality claim.
The default production GA still runs as before. Its only new observer argument is
unused by production callers.

## Handoff and search

`CoreEnumeration` now retains each catalog identity and its `(region, upper-log)`
witnesses. The existing complete gear/distinct-Mini enumeration and integer log
certificates are preserved. Incomplete enumeration explicitly retains the current
and subsequent regions as unresolved. The scorer processes known live regions
while returning that pending ledger;
unvisited regions and unseen identities remain unresolved globally. Exhausting
the known queue does not imply completing enumeration.

After the cheap family bound, each surviving loadout/region gets legal lower and
upper gem counts. For FT/FF, these use **raw** region endpoints, integer ceiling and
floor division, and the production stat-gem caps. A base above a lookup cap still
admits zero gems in its raw tail. Other stat gems obey their production caps;
overflow can consume the remainder of the shared budget.

For each affine objective, mandatory gems are paid first. Remaining units go to
positive coefficients in descending order up to their capacities. This is exact
for the *linear support function*, not a greedy solution to game scoring. The
relaxed `sum(gems) <= 90` domain contains the legal `sum(gems) == 90` domain. Only
an integer upper log strictly below the incumbent's lower log excludes work;
ties remain live.

`score_adaptive` builds the surviving queue once. A cheap estimate using a repaired
seed allocation orders loadouts; it never excludes them. Each scored batch raises
the incumbent only from canonical replay. Remaining cached regional bounds are
compared against the new threshold before dispatch. A time cutoff leaves the queue
and enumeration completion flags explicit.

The existing timing-list API is score-only: its normal materializer interprets
indices in the full timing table. The research kernel instead calls the existing
`solve_best_combo_uncached` scoring function over each surviving rectangle, returning
one allocation per region. Regions form a disjoint partition, so this evaluates
their union without rescoring excluded timing pairs. Each GPU row owns its domain;
identical loadouts with different domains cannot share the wrong result. Ascending
FT/FF order with the highest index on equal scores retains the full-table timing
tie rule. This restricted solve must not substitute for full per-genome GA fitness.

## Fitting and allocation selection

The LP matrix is constructed once per region; only its right-hand side changes
across lambda values. The selected configuration keeps all nine freshly validated
bounds in every region. A smaller, inherited bank was tested and rejected: reduced
fitting time sometimes increased survivors enough to hit enumeration limits.
The inherited-fit policy and its runtime switches were deleted. No persistent
HiGHS state is added.

Canonical replay compares the winners from all surviving timing regions, so it
retains several allocations for loadouts that survive in several regions. A
further one- and two-gem neighborhood was tested: 2,050 alternative allocations
across the 24 selected-seed development runs yielded zero additional score. That
pass and its runtime switch were removed. The finite regional shortlist still
does not resolve every f32 selection ambiguity; replay alone cannot recover an
allocation discarded inside a region. No inner-optimum certificate is claimed.
Paired gear/Mini neighborhoods and stored-witness ingestion are not included.

The selected initial seed uses four independent runs of 64 genomes and 10
generations in one GA call. This replaces the one-run seed; there is no subsequent
recovery GA phase or fallback solver. Seed work, including the GA's existing final
local refinement, is included in elapsed time. Larger primary seed configurations
were tested on the sparse development case and cost more without improving its
best-known score. Complete Base input duplication is counted with P and S separate,
and with regional identity included separately. There is no persistent evaluation
cache or Base/FG equivalence assumption.

## Shared GPU upload ownership

Alternating core and GA calls exposed a pre-existing correctness bug: both upload
APIs write the same item, slot, and fixed-base fields, but their independent caches
could each claim its registry was still resident after the other API replaced it.
The next GA could then generate IDs for the wrong slot pools.

`api/registry_upload.py` now owns these shared fields and their cache. Both API
families delegate to it. Content snapshots also detect in-place edits and avoid
Python object-ID reuse hazards. This deletes duplicated upload/cache code and the now-unused GA upload kernel.
No cross-invalidation flags or silent upload exceptions remain in that path. The GPU regression reproduces the wrong
resident item table on main and passes after the ownership fix.

Two further state invariants were tested during the database audit:

- A regional solve must bind its own chart and reference tables under the GPU
  lock. Previously, preparing chart B and then reusing chart A could score A with
  B's resident timeline. The regression failed with scores around 20 million in
  place of 2.6 million. `solve_regions` now calls the existing timeline owner
  before dispatch; the A/B/A regression passes.
- A newly constructed `ItemRegistry` must represent the supplied items. Its host
  cache used pool object identity, slot counts, and fixed-item names, so a changed
  pool with the same counts or a replacement fixed item could reuse old gear.
  The cache and its key builders are deleted. Construction now derives the maps
  directly from the supplied items. The regression fails before deletion and
  passes afterward. All 2,264 database chart catalogs produce byte-identical GPU
  arrays and identical IDs with the old and new constructors.

The host registry deletion also affects production callers. The timeline fix is
confined to the research regional solver. Neither change adds a fallback.

## Bound preparation follow-up

The exact rational logarithm enclosure now stops once its outward-rounded integer
bounds are adjacent. Every iteration includes an analytic upper bound on the
remaining positive series tail, and the enclosure of log(2) is computed once.
This retains the pruning certificate while avoiding unnecessary rational terms.
Tests compare the resulting enclosures against 400-digit Decimal logarithms,
including values near powers of two from exponents -1,000 to 1,000.

Candidate-to-registry mapping and raw-stat accumulation now use array indexing.
Named catalog witnesses test the mapping, all ten raw stats, separate primary and
secondary projections, same-color charts, and an empty candidate set.

## Measurement contract

Run `python -m tools.research.measure_adaptive_core --help` for the maintained
harness. It compares the GA, the actual #180 certificate arithmetic, fitter, refiner, and enumerator loaded from
commit `7b46703b`, and the adaptive runner. All arms use the same cache-corrected
scoring backend and canonical observation harness. The latter downloads tracked
GA leaders after generations without feeding canonical scores back into GA
selection. Observed canonical leaders are retained by the research seed helper.
This makes intermediate achieved scores measurable; it does not change production
GA defaults. Total time includes observation, downloads, fitting, enumeration,
GPU solving, and canonical replay. `observer_s` measures callback CPU time;
it excludes the preceding download, which is included in total time.

Kernels are warmed before timed arms. Shared chart preparation is reported
separately. The harness also records its warmup phase, which includes discarded
search runs and is not a production cold-start estimate. Earlier development
artifacts do not record warmup duration. These are warmed-search measurements,
not a cold-start latency claim. Search curves contain timestamped canonical improvements;
a fixed-budget score uses only events at or before that budget. Core scoring stops
between batches at the configured 60-second budget, so final wall time can slightly
overshoot. The GA retains its stock 705 x 125 x 3 configuration.

The original held-out diagnostic set became development data when it informed
the seed and fitting choices. Final held-out charts are identified separately. Random seeds vary and arm order
rotates. The target is the live production host (Apple M4, 16 GiB, macOS/MoltenVK),
using isolated runtime/cache paths. Production stays running, so measurements
include ordinary host variability. This is not qualification of a different GPU
or OS. Best-known reference scores are the best observed across the comparison;
no certified reference optimum is available. FG is not measured, and these Base
results supply no evidence of FG speed or coverage.

## Measured results

The following 30-run results were measured at `09af4f9c`, before the database-audit
state fixes and bound-preparation follow-up. They remain historical measurements;
they are not timings of the later changes.

Eight development charts and two held-out charts, three random seeds each
(`1337`, `2027`, `9041`), cover all five primary colors, one- and two-color
charts, and 145–6,503 notes. The selected method matched the best-known canonical
score in **30/30 runs**. The GA also matched 30/30; #180 matched 26/30.

**No final-score losses and no score deficits in 300 paired checkpoint
comparisons** against the GA and #180 at 5, 10, 20, 40, and 60 seconds.
This is a finite measured score gate, not a claim of dominance at every instant
or on untested charts. All references are best-known scores, not certified optima.

| Search budget | GA best-known hits | #180 hits | Selected method hits |
|---:|---:|---:|---:|
| 5s | 1/30 | 17/30 | 28/30 |
| 10s | 25/30 | 19/30 | 30/30 |
| 20s | 29/30 | 23/30 | 30/30 |
| 40s | 29/30 | 26/30 | 30/30 |
| 60s | 30/30 | 26/30 | 30/30 |

Search completion times below are medians of three runs, including seed,
fitting, enumeration, scoring, and replay. Time to the best-known score is
reported separately because continuing to process bounded work is a different
quantity from finding the winner.

| Chart | Canonical score | GA finish | #180 finish | New finish | New time to best-known |
|---|---:|---:|---:|---:|---:|
| Comfort Zone (Easy) | 2,631,111 | 39.78s | 4.68s | 5.85s | 1.60s |
| The Vocab Quiz | 27,773,717 | 36.86s | 31.16s | 8.84s | 1.37s |
| Overkill | 62,691,097 | 46.27s | 9.87s | 9.05s | 2.22s |
| Galaxy Collapse | 196,630,021 | 46.81s | 33.36s | 17.30s | 1.40s |
| Aurora | 55,268,089 | 44.85s | 28.56s | 9.85s | 1.53s |
| All Right There | 31,110,912 | 41.86s | 11.10s | 9.59s | 1.36s |
| Sky Gazer | 44,378,197 | 48.09s | 18.75s | 10.16s | 1.95s |
| Scattered Faith | 151,280,505 | 48.03s | 30.62s | 14.60s | 1.99s |
| crystallized (Easy)† | 4,859,453 | 71.25s | 4.91s | 7.56s | 1.90s |
| MARENOL† | 53,364,332 | 46.23s | 12.13s | 9.87s | 1.40s |

† Held-out: crystallized and MARENOL were not used to choose the seed or bounds.

**Completion-time tradeoff:** the selected search takes 1.17s longer than
#180 on Comfort Zone and 2.66s longer on crystallized (median). Both searches
hit the 100,000-witness limit on these charts. #180 stops without an inner
solve; the selected method scores known surviving regions and returns the
unvisited-region ledger. Its stronger seed improves best-known agreement
from 0/3 to 3/3 on Comfort Zone and from 2/3 to 3/3 on crystallized.
Thus there is **no claim of zero completion-latency regressions**.
The other eight charts have lower median completion time and complete
enumeration in the selected method. This does not certify their f64 optimum.

The core improves its four-run seed on Overkill seed 2027 (+144,819) and
Aurora seed 9041 (+94,977). Those improvements subsequently prune 496 and
1,422 queued regions. Every other selected seed already matches its chart's
best-known reference. Input-duplication and evaluated timing-pair counts
are retained per run in the data; no evaluation cache was added.

[Full curves, per-run measurements, and discarded experiment data](adaptive_region_core_results_2026-09-11.json)

The source and runtime are common to the measured arms except for the
explicitly loaded #180 fitting/enumeration modules. NumPy 2.3.5 and Numba
0.62.1 match this host, not the repository's runtime pins. These results
qualify this measured host/workload; they do not establish a release-wide
latency distribution. FG was not benchmarked by the Base search.

## Post-audit sparse-chart follow-up

After the state fixes and preparation changes, the two previously slower charts
were rerun at `47f3ae81` with seeds 1337, 2027, and 9041. All audit workers had
exited before measurements. These are development follow-ups on known charts,
not new held-out evidence. The baseline also loads #180's original certificate
math so the optimized logarithm does not silently benefit both arms.

| Chart | #180 median finish | Updated median finish | Difference | #180 best-known hits | Updated hits |
|---|---:|---:|---:|---:|---:|
| Comfort Zone (Easy) | 4.71s | 5.67s | +0.97s | 0/3 | 3/3 |
| crystallized (Easy) | 4.94s | 7.82s | +2.87s | 2/3 | 3/3 |

All six updated runs match their best-known score, with no deficit in 30 paired
checkpoints at 5, 10, 20, 40, and 60 seconds. **The completion-time regressions
remain.** Both searches hit the witness cap; the updated method processes known
surviving regions and uses a stronger seed. This is not a zero-latency-regression
qualification, and the PR remains a draft for review. The full 30-run comparison
above was not rerun on this revision; its timings remain labeled historical.

[Complete follow-up runs and score curves](adaptive_core_sparse_followup_2026-09-11.json)

## Verification

`python -m ruff check .` passes. After the database-audit fixes, the focused
state, bound, handoff, and audit selection passes **45 tests**. The full suites
were rerun and compared against the clean main baseline (`7b46703b`):

| Suite | Updated branch | Current main baseline |
|---|---|---|
| `pytest -m "not gpu" tests/` | 1,388 passed; 134 failed; 3 skipped | 1,369 passed; 134 failed; 3 skipped |
| `pytest -m gpu tests/` | 69 passed; 28 failed; 3 errors; 5 skipped | 67 passed; 28 failed; 3 errors; 5 skipped |

**All common test statuses match, and all 21 added tests pass.** There are no newly
failing or newly skipped tests. Three failure-message representations differ due
to pytest verbosity/truncation. Rerunning those three tests with the baseline
verbosity produces identical normalized failure messages. The
repository-wide suites are not green. Existing failures were neither loosened
nor skipped. The shared-upload, chart-switch, and changed-pool regressions were
also observed failing before their respective fixes.

[Full validation counts and baseline failure nodes](adaptive_region_core_validation_2026-09-11.json)

The [global database audit](adaptive_core_database_audit_2026-09-11.md) checks stored
witness consistency and regional winner preservation separately from canonical
optimality. It includes the existing Kanpai timing-selection counterexample.

## Reproduce

Install the repository's development requirements, then run the maintained
harness. It isolates database and runtime/cache paths itself. For example, the
untuned held-out comparison is:

```bash
python -m tools.research.measure_adaptive_core \
  --hardware-role production --split held-out \
  --song 'Data/Easy/crystallized (Easy) by Camellia.txt' \
  --song 'Data/Hard/MARENOL (Hard) by LeaF (7eaF).txt' \
  --seeds 1337 2027 9041 \
  --output artifacts/adaptive-heldout.json
```

Use `--hardware-role development` on another machine. Defaults select all three
arms, the four-run initial seed, nine LP members, 64 timing leaves, one million
enumeration nodes, 100,000 witnesses, and a 60-second scoring deadline. Each result
contains its chart path, seed settings, timestamped score improvements, bounds
and enumeration times, workload counts, and completion flags. To reproduce a
checkpoint score, take the largest event score whose timestamp is no greater
than the checkpoint; never use a later final score for an earlier budget.

## Patch report

- **Invariant:** proved timing exclusions must reach the inner search; pruning
  thresholds must be canonically achieved; a shared GPU field has one resident
  registry and therefore one upload-cache owner; each solve must bind its chart;
  registry construction must reflect its input contents.
- **First violation:** #180 discarded regional membership at the identity-only
  handoff; GA and skyline separately memoized writes to the same GPU fields; the regional
  solver assumed its chart was still resident; host registry keys omitted content.
- **Fix:** retain regional upper bounds, restrict real scoring to legal regional
  pairs, feed back canonical improvements, unify GPU registry ownership, bind the chart under the same lock, and delete
  the unsafe host registry cache.
- **Tests:** exhaustive small gem boxes, raw timing boundaries/cap tails, ties,
  incomplete-region coverage, matrix reuse, regional/full GPU comparison, deadline
  retention, GA/core upload switching, A/B/A chart switching, and changed-pool construction. The upload-switch regression fails on
  main with the wrong item table resident.
- **Complexity:** new focused research modules implement regional support,
  scheduling, and materialization; shared production upload code becomes smaller, and the host registry change
  removes 72 net lines.
  No new dependency, outer skyline, persistent solver, or persistent evaluation
  cache is introduced.
