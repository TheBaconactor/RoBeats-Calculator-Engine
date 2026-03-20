# HitSim Regime Materialization: Shallow Clone `calc_song` (Avoid Deepcopy Overhead)

Date: 2026-03-20

## Context

The in-flight pipeline may materialize multiple HumanHitSim regimes per song:
- HitSim matrix planning (`_plan_hitsim_matrix`) builds per-regime jobs.
- HitSim continuation planning builds additional per-regime jobs.

Historically these paths cloned the per-song `calc_song` payload via `copy.deepcopy(...)` per regime.

`calc_song` can contain large nested payloads and numpy arrays, so `deepcopy` is expensive and increases CPU overhead.

## Root Cause

HitSim materializers mutate only a small, well-defined subset of `calc_song`:
- `calc_song["metadata"]` top-level keys (seed, mode, regime identity)
- `calc_song["song_data"]` keys (timestamps arrays are replaced, not mutated in-place)

We do not need to recursively duplicate all nested payloads and arrays to isolate regimes.

## Fix

In `gear_optimizer/solver/native_inflight_stages.py`:
- Added `_clone_calc_song_for_hitsim(calc_song)`:
  - shallow-copies the top-level dict
  - shallow-copies `metadata` and `song_data` dicts
  - keeps numpy arrays by reference (they are treated as immutable inputs; HitSim replaces arrays)
- Replaced `copy.deepcopy(song.calc_song)` with `_clone_calc_song_for_hitsim(...)` at the regime materialization call sites:
  - HitSim matrix regime jobs
  - HitSim continuation regime jobs

This is a targeted performance fix with correctness isolation preserved.

## Verification

- Tests:
  - `python -m pytest tests/test_native_inflight_decode_hitsim_candidate_pool.py`
  - `python -m pytest tests/test_hit_simulation.py`
- Reference DB bench:
  - `python tools/bench/bench_compare_optimizer_to_root_db_pool.py --count 25 --repeats 25`
    - base misses stayed at 0; FG misses 0; score recompute mismatches 0

