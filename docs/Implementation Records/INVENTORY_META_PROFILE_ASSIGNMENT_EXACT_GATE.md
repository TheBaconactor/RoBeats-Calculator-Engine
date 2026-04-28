# Inventory Meta Profile-Assignment Exact Gate

Date: 2026-04-27

## Context

The proposed exact formulation is a profile-weighted local-assignment CP-SAT/MILP for the production inventory-meta
contract:

- `InventoryCap = 100`
- no song or element filters
- `TopCandidates = 1`
- one exact-peak candidate per song
- target order `(PP, CM, FM, FT, FF, OV)`
- minis ignored
- zero-OV variants normalized to color `""`

The formulation aggregates equivalent songs by gear multiset, target vector, and selected element when `OV > 0`; it
drops element from the profile key when `OV = 0`.

## Result

The profile reduction is semantically valid for the tested production snapshot, but the direct CP-SAT formulation is not
accepted as production behavior because it failed the user's one-minute quality gate.

Measured production snapshot after compact details unpacking:

- selected songs: `2,216`
- weighted profiles: `1,188`
- profile weight sum: `2,216`
- profile duplicate groups: `441`
- required gear names: `56`
- duplicate gear occurrences inside profiles: `0`
- support-pruned local columns:
  - min: `1`
  - median: `126`
  - p90: `440`
  - max: `1,556`
  - sum: `229,717`
- assignment binaries in the direct formulation: `1,378,302`
- reduced global variants: `100,674`

Direct CP-SAT prototype result:

- preparation: `0.682s`
- model build: `66.637s`
- CP-SAT search limit: `20s`
- total wall time: `91.982s`
- status: `UNKNOWN`
- objective: `0`
- bound: `0`

The active environment also has an OR-Tools/protobuf mismatch:

- OR-Tools: `9.14.6206`
- protobuf runtime: `5.29.6`
- generated protobuf requirement: `6.31.1`

The prototype bypassed the version guard in process only for measurement. That is not production-ready.

## Production Change Made

Inventory candidate parsing now unpacks compact `details_json` with the canonical database helper before reading
`GemCounts` and selected element. Without this, the root `evolution.db` snapshot parsed `0` inventory-meta candidates
and reported all `2,216` songs as missing.

## Production Decision

Do not replace the GPU production path with the direct exact CP-SAT/MILP. The direct formulation is useful as a proof
object and future research direction, but it is too large in its straightforward materialization and cannot currently
produce a useful result inside the one-minute gate.

Future work, if exact production coverage is still desired:

- design a smaller exact model, decomposition, or column-generation flow that avoids materializing all local assignment
  binaries up front;
- fix and pin any exact-solver dependency before enabling it;
- keep the GPU heuristic path as production until the exact path demonstrates a bounded non-regressing runtime on the
  real snapshot.

## Verification

- `python -m pytest -q tests/test_inventory_db_baseline_team_buff_resolution.py --tb=short`
- real snapshot extraction check:
  - candidate songs: `2,216`
  - missing: `0`
  - selected: `2,216`
  - profiles: `1,188`
  - weight sum: `2,216`
- `python -m ruff check inventory_optimizer\db.py tests\test_inventory_db_baseline_team_buff_resolution.py`
- `python -m pytest -m gpu -q tests/test_inventory_meta_coverage.py::test_inventory_meta_coverage_reuses_variants --tb=short`
