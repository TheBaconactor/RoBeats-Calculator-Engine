# Stats Integrity Verifier (Retired)

> **Status:** Removed. `gear_optimizer/data/stats_verifier.py`, the optimizer startup hook, and
> `scripts/stats/_demo_stats_verifier.py` were deleted during the finder/dead-LOC cleanup. The verifier
> no longer runs on `main.py` startup.

## Current operator path

Repair missing or empty `Stats` in tier tables manually:

```bash
python tools/db/backfill_stats.py
```

Related inspection helpers under `scripts/stats/` (`_find_bad_stats.py`, `_validate_stats.py`, etc.)
remain available for ad-hoc DB checks.

## Historical behavior (pre-removal)

The retired verifier used to:

- Run once at the start of fresh queue runs (not resume)
- Sample then full-scan `team_buff_*` rows for missing/empty/zero `Stats`
- Recompute loadout-only `Stats` from gear/minis/gems and commit repairs in-place
- Print a prominent warning when many rows needed repair

That automatic startup repair path is intentionally gone; use `backfill_stats.py` when you need
explicit, operator-controlled DB maintenance.
