# Exact Base Semiring Production Migration

Date: 2026-07-14
Updated: 2026-07-15

## Decision

The canonical outer optimizer is now an exact, request-local Base search followed by the native Force Greats scorer. The production pipeline is:

1. build exact domains from the gear and Mini catalog supplied to the request;
2. load the startup-prebuilt song context;
3. perform two Vulkan semiring joins per reachable response component and an admissibly bounded
   exact scan;
4. certify the globally optimal Base top-1 loadout;
5. effective-deduplicate and refill the exact-scored witness pool to 51 candidates, or
   until the joined-state frontier is exhausted; and
6. score those retained candidates with native exact FG in the same GPU-owner turn.

The genetic search, its stochastic effort knobs, seeds, populations, generations, recovery policy, resident candidate table, and compatibility routes are retired rather than retained behind a switch.

## Exact Base search shape

`exact_base_domains.py` reduces the two three-slot gear products and unordered distinct-Mini triples for the live catalog. It preserves signed partial statistics and validates the scalar Base quotient required by the semiring.

Perfect Points is handled by an exact request-local component decomposition, not by rejecting catalogs. Mini triples are partitioned by their exact Mini PP total. For every reachable completed PP value, the solver computes the full PP-gem-versus-overflow response over every gem budget and groups identical response vectors into response-profile classes. A `(Mini PP total, reachable response class)` pair is one scalar semiring component. Every reachable component is certified and its witnesses are unioned, so nonuniform Mini PP totals and catalogs where a PP gem is optimal remain exact. A request that reaches one component keeps the one-component hot path; the default-catalog `00 (Hard)` benchmark request did so. Other official or custom requests pay only for the additional components their actual Mini PP totals and reachable completed PP values create. No component or catalog frontier is prebuilt.

`exact_base_song_context.py` constructs the song-only fixed-timing skyline, timing-response antichain, multiplier bounds, and reference-table inputs. These artifacts do not depend on gear or Minis.

`exact_base_semiring.py` performs the compact gear and gear-plus-Mini joins on Vulkan for each reachable response component. Complete loadout statistics are clamped to the game range at the join boundary. `exact_base_search.py` scans bound-ordered witness batches with the exact batch scorer until no unseen row in that component can beat its incumbent, then selects the best certified result across components.

After top-1 certification, `exact_base_search.py` continues from the highest remaining admissible bounds whenever raw witnesses collapse to an already-seen effective loadout. It refills until it has 51 effective candidates or every joined state is exhausted. `exact_base_candidate_surface.py` then effective-deduplicates and ranks the unioned exact-scored witnesses and materializes their typed result rows. The global certificate applies to Base top-1. The retained surface is not claimed to be the globally certified Base top-51; it is the highest-ranked effective subset of the exact-scored witness pool used by the FG product funnel.

## Pipeline ownership

The GPU executor exposes one `EXACT_BASE_SEARCH` request. Its response is a typed `ExactBaseOwnerResult` containing an `ExactBasePipelineResult` and the native FG owner score map. Candidate IDs, scores, exact result rows, and `base_stats7` remain aligned typed arrays through the owner turn. The owner scores FG directly from `base_stats7`; decode emits `LoadoutIDs` and registry-decoded `Loadout` values without reconstructing a packed candidate ABI or reranking the already-ranked surface.

The task ABI no longer contains search depth or a stochastic seed. Runtime configuration no longer exposes mutation, tournament, population, multistart, or generation controls. Website `reasoning` input remains harmless as an unknown external field, but it no longer changes optimizer behavior because exact search has no effort level.

## Cache and custom-catalog behavior

The production startup order is strict:

1. timeline frontier cache;
2. exact Base song-context cache; and
3. native FG response-frontier cache.

Native song preparation only loads prebuilt timeline and Base-context artifacts. A missing or invalid required artifact fails loudly. The exact Base context key is semantic and path-independent, and a shared multiplier artifact avoids duplicating the largest catalog-independent tensor per song.

Gear and Mini catalogs are intentionally absent from the song-context key. A request with added custom gear or Minis rebuilds only its request-local domains and reachable PP-response components; it does not rebuild the song context or either native timing frontier. A custom chart is prepared by the normal startup phase before its native solve.

Catalog-derived in-memory caches are keyed by stable content fingerprints, not object identity alone. Mutating the name, slot, order, or nested stats of a reused custom gear/Mini object invalidates the pruned-pool, item-registry, Mini-equivalence, and effective-table entries that depend on it. This keeps website requests safe while retaining memoization for unchanged catalogs.

Corpus Base-context prebuild partitions missing paths into caller-owned spawn generations. Each
generation admits at most eight tasks per worker and keeps a rolling pending queue of at most two
tasks per worker. The caller creates the executor outside the submit loop, drains every future,
and exits the executor context before it starts the next generation. This ownership avoids the
Windows queue-manager deadlock seen when pool recycling was triggered from inside submission, while
the bounded worker lifetime releases native/NumPy allocator commit that otherwise ratchets upward
in a never-ending pool. A single missing context is still built in-process.

The provisioned FG pool contains `fg-response-frontier-visible-first-v31+logic-b4ffccc942cf`.
Retiring GA removed only unused GA constants from the conservatively fingerprinted
`core/constants.py`; no FG producer, serializer, bundle schema, ordered surface, or compact-sidecar
logic changed. The resulting `8f06577b631d` runtime therefore accepts exactly that provisioned
predecessor, explicitly and non-transitively. The timeline pool has a complete current-version
artifact set and destination-local manifest. Neither cache depends on the gear or Mini catalog.

Unexpected run-iteration failures are re-raised after the existing cleanup `finally` completes.
This makes `main.py` return a failing process status through `cli.run()` instead of logging an
incomplete startup or solve and exiting successfully.

## Development benchmark evidence

An earlier production-shaped development checkpoint on `Data/Hard/00 (Hard) by garlagan.txt`, whose default-catalog request reached one response component, recorded with copied caches:

- Base score: `40,133,861`, matching the prior production GA result;
- exact-scored witnesses: `4,608`;
- retained Base/FG surface: `51`;
- hot exact Base wall times: `0.612 s`, `0.604 s`, `0.616 s`;
- median hot wall time: `0.612 s`;
- cold request-local catalog/domain preparation: about `0.059 s`;
- first Taichi compilation warmup: `12.293 s`, excluded from hot timing; and
- observed cold song-context builds: approximately `6.78-15.52 s`, followed by millisecond cache hits.

These numbers are development evidence, not a claim about the final all-song production run or final-tree release checks. Per the experiment contract, the migration does not add a second exhaustive verifier to the live path.

## Complexity and deletion impact

Catalog changes now pay request-local domain construction plus the exact joins for reachable response components, not a per-catalog frontier build. Requests that reach one component keep the single-component cost. Song-dependent timing work is amortized by the mandatory semantic context cache. The hot exact scorer evaluates bound-ordered witnesses and refills only when effective deduplication requires more candidates.

The migration deletes the GA engine and its renamed remnants: generation/RNG/island machinery, GA executor requests and recovery, configuration policy, helper routes, benchmarks, tests, and active planning documents. Shared exact scoring primitives remain under neutral ownership because Base materialization, database replay, and native FG still consume them.

## Validation contract

Required release checks are:

- focused exact-domain, context-cache, semiring, candidate-surface, executor, native-pipeline, persistence, and startup tests;
- Vulkan-facing exact Base and native FG tests;
- a full CPU/reference suite and repository quality check;
- all-song startup context prebuild using copied timeline/FG caches; and
- an actual `main.py` production run from the isolated migration worktree.

## 2026-07-15 addendum: dead-atomics grid fix and cold-build vectorization

Corpus sweeping exposed a production-fatal Taichi/Vulkan defect: a u64 grid ndarray can land in a
device-allocation layout where the join scatters' `ti.atomic_max` writes are silently dropped
(plain stores and host round-trips still succeed), tripping the fail-loud
`gear compaction violated capacity: count=0` guard on layout-dependent songs (4 of 11 GPU-tested;
deterministic per song via the song-sized timeline/bound uploads that precede the grid
allocation). The join grids now come from grow-only, module-level `_VerifiedU64Scratch` buffers in
`exact_base_search.py`: every (re)allocation is probe-verified with the same atomic op the joins
use, dead allocations are held during retry so the allocator cannot return the same region, and
verification failure after three attempts raises. Verified buffers are reused across requests and
components, so the production owner no longer re-rolls the allocator layout per song. Join kernels
only touch the `[0, elems)` prefix they are launched with, so serving from a larger verified
buffer is exact.

The cold song-context build was rewritten vectorized with byte-identical output (8-song oracle,
all 37 context arrays equal): `_timing_bound_programs` is one numpy pass instead of the
row/combo/pool Python triple loop, the antichain keep-mask runs as one batched call over all
25,921 cells via composite row/pack segment keys, and the song-invariant joint multiplier tables
are memoized on reference bytes. Cold builds dropped from 8.6-29.0 s to 3.8-8.5 s per song
(2.2-3.5x). These producer changes bump the context cache version
(`exact-base-song-context-v1+logic-63bc27f3145c`); the previously provisioned context pool is
stale and must be rebuilt, and the cache still lacks a purge mechanism for prior versions.

The `frontier_bound` stage (51-58% of a hot request) was restructured to remove redundant loads
(bit-identical bound values) but is f64-ALU-bound on RDNA3, so its cost is intrinsic to the exact
bound formula; materially reducing it requires a semantic change to bound evaluation that would
alter witness-pool composition and needs an explicit owner decision. Witness-pool tails may swap
score-tied rows across kernel-recompile or allocation-layout changes because compaction
materializes rows with `ti.atomic_add`; the certified top-1, winner IDs, and the ranked 51-row
surface are layout-independent and were verified byte-identical across all changes above.
