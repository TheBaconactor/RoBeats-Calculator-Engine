# DB Ready for Frontend - Summary

**Date:** January 24, 2026  
**DB Schema Version:** 12  
**Branch:** revert-cpu-opt  
**Commit:** 45210cb

## Changes Made

### 1. Deduplication of T5 Entries ✓
- **Problem:** T5 appeared twice in unified view (once from legacy `fg_loadouts`, once from `team_buff_fg_loadouts`)
- **Solution:** Updated `fg_loadouts_unified` view to prioritize `team_buff_fg_loadouts` and exclude legacy entries when explicit tier data exists
- **Result:** Reduced from 52,321 to 50,903 entries (1,418 duplicates eliminated)

### 2. Code Organization ✓
- Moved all debug scripts from root to proper locations:
  - `scripts/db/` - Database verification scripts
  - `scripts/stats/` - Stats validation scripts
  - `tests/` - Test files (test_fg_persistence.py)

### 3. DB Verification ✓
- Schema version confirmed: **v12** (up to date)
- Unified view tested and working correctly
- Tier breakdown verified for sample songs

## Frontend Integration Guide

### Database Query
Use the **`fg_loadouts_unified`** view instead of querying `fg_loadouts` or `team_buff_fg_loadouts` directly:

```sql
SELECT 
    song_name,
    team_buff,  -- Will always be present (NONE, T1, T5, T10, T15)
    score,      -- Base score context
    fg_score,   -- Force Greats score
    gear_json,
    minis_json,
    details_json,
    force_details_json,
    timestamp
FROM fg_loadouts_unified
WHERE song_name = ?
ORDER BY team_buff, fg_score DESC;
```

### Tier Counts (Current DB State)
| Tier | FG Entries | Base Entries |
|------|------------|--------------|
| NONE | 180 | ~4,000+ |
| T1   | 181 | ~4,000+ |
| T5   | 50,180 | ~4,000+ |
| T10  | 181 | ~4,000+ |
| T15  | 181 | ~4,000+ |

**Note:** T5 dominance is expected - the optimizer default is T5 (`AutoSelectBuffAndColor=true`), and 51,417 songs have only been run with T5.

### Base Loadouts Query
For base (non-FG) loadouts with tier breakdown:

```sql
SELECT 
    song_name,
    team_buff,
    score,
    fg_score,  -- May be 0 if no FG improvement exists
    gear_json,
    minis_json,
    details_json,
    timestamp
FROM team_buff_loadouts
WHERE song_name = ?
ORDER BY team_buff, score DESC;
```

### How Tiers Work

1. **Optimizer generates one loadout** (usually T5 by default)
2. **That loadout is re-scored under all 5 tiers** (NONE, T1, T5, T10, T15)
3. **Both base and FG scores are saved** for each tier in `team_buff_loadouts` and `team_buff_fg_loadouts`
4. **Unified view combines everything** with deduplication

### Expected Behavior

✅ **All 5 tiers present** for songs that have been run through the optimizer  
✅ **Both base and FG scores** available for each tier  
✅ **No duplicate T5 entries** in unified view  
✅ **Each tier has different scores** because team buffs affect the calculation

### Sample Query Result

For song "#include <signal.h> (Hard) by Kurokotei":

```
NONE: fg_score=39,093,571
T1  : fg_score=43,122,896
T5  : fg_score=42,877,293
T10 : fg_score=42,192,404
T15 : fg_score=41,483,578
```

All 5 tiers present with proper scores ✓

## Verification Commands

If you need to verify the DB yourself:

```bash
# Check schema version
python -c "import sqlite3; conn=sqlite3.connect('evolution.db'); print('Version:', conn.execute('PRAGMA user_version').fetchone()[0]); conn.close()"

# Check tier counts
python scripts/db/_verify_deduplication.py

# Check specific song
python scripts/db/_check_fg_unified.py
```

## Database Location
- **Path:** `./evolution.db` (root of repo)
- **Size:** ~500MB+
- **Schema:** v12
- **Safe to copy:** Yes (read-only for frontend)

---

**Status:** ✅ Ready for frontend integration  
**Contact:** GitHub @TheBaconactor if issues arise
