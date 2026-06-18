# Candidate Cache Implementation - Issue #46

## Summary

Issue #46 adds a canonical Candidate Cache for repeated exact candidate work. The
cache is both live and disk-backed:

- live: a process-wide in-memory cache is loaded before optimizer work and checked in
  the hot host-side candidate seams;
- disk-backed: entries persist in SQLite under `bin/candidate_cache/` by default and
  are warmed into memory on the next session;
- lossless: cache hits reconstruct the same downstream payload shape as a fresh solve;
- canonical: Base and ForceGreats entries are separate namespaces, with no feature
  flag, compatibility route, song exception, or CPU production fallback.

This cache is intentionally different from the older GPU-native GA base-candidate
cache route removed on 2026-05-30. It does not upload cache shards into the GA kernel
or insert cache round trips inside the per-generation GPU evaluator. It sits at host
candidate/result boundaries where full result payloads already exist.

## Storage

`gear_optimizer/solver/candidate_cache.py` owns the cache.

- Default path: `bin/candidate_cache/candidate_cache.sqlite3`
- Test/external override: `CANDIDATE_CACHE_DIR`
- Table: `candidate_cache(namespace, key_digest, key_repr, payload_json)`
- Runtime stores: independent in-memory dicts for `base` and `fg`
- Runtime admissions update the live dict immediately and queue compact rows for
  SQLite batch flush
- Flush boundaries: batch-size threshold, explicit flush, test reset, and process
  shutdown
- Startup reads warm the live dicts

The cache validates every payload on put, get, and disk load. Unknown namespaces,
invalid key shapes, corrupt JSON, missing payload fields, negative counts, and
malformed response surfaces fail loudly.

## Keys

### Base

The Base key includes:

- candidate-cache version and `base` namespace
- content-derived song timing key
- all five scoring reference-array signatures
- the 10-stat base tuple
- primary, secondary, and selected colors
- color contribution flags
- total gem budget and fever gem scale

This lets GA-decoded Base candidates, standalone Base solves, and Skyline batch Base
evaluation reuse the same exact Base result when the semantic inputs match.

### ForceGreats

The FG key includes:

- candidate-cache version and `fg` namespace
- the existing FG response-frontier song key
- the existing FG response-frontier bundle key
- all five scoring reference-array signatures
- selected color
- exact seven-component FG scoring input
- total gem budget

Using the same response-frontier key material keeps invalidation aligned with the
frontier disk caches.

## Payloads

### Base Payload

Base entries store the exact result fields consumed downstream:

- `Score`, `FT`, `FF`
- `GemCounts` plus `gem_counts`
- final 10-stat `Stats`
- `Selected Element`
- compatibility fields such as `config`, `FT_gems`, and `FF_gems`

On a hit, `solve_best_fever_combination` and Skyline batch evaluation return the same
shape they would have produced from a fresh exact solve.

### FG Payload

FG entries store enough to reconstruct the materialized ForceGreats payload without
rerunning the frontier/BnB/exact replay:

- raw frontier best score for ranking before exact materialization
- exact final score
- `FT`, `FF`, and gem counts
- forced counts
- the 11-int response surface
- `ForceGreats` trace/metadata

On a hit, `materialize_fg_payload_from_cache` overlays the cached exact FG fields onto
the current candidate's `eval_data`, preserving candidate identity fields such as
GenomeIDs while reusing the solved FG result.

## Interception Points

### Base / GA

- `solve_best_fever_combination` checks and admits standalone exact Base solves.
- `batched_registry_eval` checks each Skyline/Base row, dispatches only misses, and
  admits full seven-column exact results when no score-cull threshold is active.
- `decode_ga_payload_sync` admits decoded GA selected Base results when the payload
  carries `Data.BaseStats`, preserving the production GA GPU evaluator path.

### ForceGreats / Skyline

- `score_fused_fg_from_selected_payload` filters disk-warmed FG hits before the fused
  GA->FG owner scorer, so an all-hit selected payload submits no owner scoring work.
- `FgResponseScoringService.score_prepared_plan` and
  `materialize_from_owner_score_map` build miss-only plans and materialize the original
  plan from cached payloads plus miss results.
- `FgResultReducer.materialize` admits fresh miss results after exact
  materialization and reconstructs cached hits losslessly.

## Invariants

- Base and FG caches are physically and semantically separate.
- Cache hits never synthesize placeholder data.
- Cache misses run the same canonical exact implementation as before.
- Hot-path hits are memory-only; disk is used for startup warmup and batched
  persistence, not per-hit I/O.
- Score-culled Base rows are not admitted because their full allocation payload is not
  available.
- Disk corruption is an internal cache invariant violation and raises instead of
  becoming a silent miss.
- Deleting `bin/candidate_cache/` only deletes cache material; it does not affect
  `songs.best_score`, `songs.best_fg_score`, evolution DBs, or leaderboard state.

## Verification

Focused verification for this implementation:

- `python -m py_compile` on the touched runtime and test modules
- `python -m pytest tests/test_candidate_cache.py -q`
- targeted native/Skyline/decoder regression tests around the touched seams
- `python -m ruff check` on the touched files
