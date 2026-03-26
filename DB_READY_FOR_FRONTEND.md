# DB Ready for Frontend - Summary

**Date:** February 3, 2026  
**DB Schema Version:** 18
**Branch:** n/a  
**Commit:** n/a

## Note (2026-03-25)

This document describes the **compact/default** workflow where TeamBuff derived tiers are **not** materialized into
SQLite by default.

By default, only the baseline tier rows (typically `T5`) are stored; derived tiers (`NONE/T1/T10/T15`) are recomputed on
demand (not persisted).

## Changes Made

### 1. Legacy Tables Removed (OK)
- **Change:** Deprecated `loadouts` / `fg_loadouts` tables are dropped at schema v16.
- **Result:** Canonical tables are `team_buff_loadouts` and `team_buff_fg_loadouts` (no legacy view surfaces).

### 2. Code Organization (OK)
- Moved all debug scripts from root to proper locations:
  - `scripts/db/` - Database verification scripts
  - `scripts/stats/` - Stats validation scripts
  - `tests/` - Test files (test_fg_persistence.py)

### 3. DB Verification (OK)
- Schema version confirmed: **v18** (up to date)
- DB manager APIs tested (catalog + leaderboard entry recompute)
- Tier breakdown verified for sample songs

## Frontend Integration Guide

### Preferred Integration (No Direct SQL)

The compact/default DB intentionally:
- Persists only the baseline tier rows (usually `T5`).
- Stores gear/minis via encoding tables + BLOB ID columns.
- Repairs legacy compact upgrades in place on schema init by backfilling missing `gear_ids_blob` / `minis_ids_blob`
  from older `gear_json` / `minis_json` payloads.

Instead of querying SQLite directly, have your backend use `EvolutionDbManager`:

```python
from gear_optimizer.data.db_manager import EvolutionDbManager

db = EvolutionDbManager.from_env()

# 1) Discover songs + ranks available in the DB
#    (defaults to the resolved baseline tier for the current config)
catalog = db.get_song_catalog(max_rank=51)

# 2) View a specific row on-demand (tier score is computed on demand)
row = db.get_leaderboard_entry(
    \"Rainshower (Easy) by Silentroom\",
    leaderboard=\"fg\",
    tier=\"T10\",
    rank=1,
    element=\"selected\",
)
```

### Tier Counts (Compact DB)

By default, only the baseline tier is stored in SQLite (typically `T5`).

- Stored tiers: baseline only (usually `T5`)
- Derived tiers (`NONE/T1/T10/T15`): computed on demand

### Raw SQL (Not Recommended)

If you only need scalar counts/scores, direct SQL is fine. Decoding `gear_ids_blob` / `minis_ids_blob` into piece names
is intentionally a Python-level operation; prefer `EvolutionDbManager` for reads.

### How Tiers Work

1. **Optimizer generates one loadout** (baseline tier, usually T5) and persists baseline rows only.
2. **Derived tiers are recomputed on demand** from the persisted baseline candidates (`NONE/T1/T10/T15`).
3. **On-demand scorer**: see `docs/ON_DEMAND_TEAM_BUFF_TIER_SCORING.md` (tool: `tools/db/compute_team_buff_tiers_on_demand.py`).

### Expected Behavior

- Baseline tier rows present in SQLite (typically `T5`).
- Derived tiers are computed on demand (not stored).
- Per-tier scores differ because TeamBuff affects the calculation.

## Verification Commands

If you need to verify the DB yourself:

```bash
# Check schema version
python -c "import sqlite3; conn=sqlite3.connect('evolution.db'); print('Version:', conn.execute('PRAGMA user_version').fetchone()[0]); conn.close()"

# Check dedup/top-N invariants
python scripts/db/_verify_deduplication.py

# Check a specific song for songs-table consistency vs tiered tables
python scripts/db/check_db_consistency.py --song \"Rainshower (Easy) by Silentroom\" --strict
```

## Database Location
- **Path:** `./evolution.db` (baseline-only; derived tiers on demand)

---

**Status:** Ready for frontend integration
**Contact:** GitHub @TheBaconactor if issues arise
