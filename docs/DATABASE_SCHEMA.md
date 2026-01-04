# Database Schema & Developer Guide

## Overview

The Gear Optimizer uses a SQLite database (`evolution.db`) to store song metadata and loadout configurations.
As of **December 2025**, the database uses a **Dual-Table Architecture** to separate Base Scores (regular gameplay) from Force Greats Scores (simulation).

## Schema Definitions

### 1. `songs` Table
Stores high-level metadata and best known scores for each song.

```sql
CREATE TABLE songs (
    name TEXT PRIMARY KEY,          -- Unique song name
    best_score INTEGER DEFAULT 0,   -- Best Base Score
    best_fg_score INTEGER DEFAULT 0,-- Best Force Greats Score
    last_updated REAL,              -- Timestamp of last update
);
```

### 2. `loadouts` Table (Base Score Leaderboard)
Stores the primary leaderboard for normal gameplay. Contains **ALL** loadouts found, ranked by `score`.

> [!NOTE]
> This table may contain entries with invalid/empty Force Greats configs if they produced a high base score.

```sql
CREATE TABLE loadouts (
    song_name TEXT,
    loadout_hash TEXT,              -- Unique hash of (Gear + Minis effective signature for this song)
    score INTEGER,                  -- Base Score (PRIMARY RANKING METRIC)
    fg_score INTEGER DEFAULT 0,     -- Force Greats Score (Contextual)
    gear_json TEXT,                 -- JSON array of gear names
    minis_json TEXT,                -- JSON array of mini-variant groups (see notes below)
    details_json TEXT,              -- JSON details (GemCounts, etc.)
    force_details_json TEXT,        -- JSON Force Greats config (May be NULL/Empty)
    timestamp REAL,
    PRIMARY KEY (song_name, loadout_hash),
    FOREIGN KEY (song_name) REFERENCES songs(name)
);
```

### 3. `fg_loadouts` Table (Force Greats Leaderboard)
Stores the specialized leaderboard for Force Greats simulations. Contains **ONLY** loadouts with valid Force Greats configurations.

> [!IMPORTANT]
> This table is a **Clean Subset**. It strictly filters out "Base Score Champions" that do not use Force Greats.

```sql
CREATE TABLE fg_loadouts (
    song_name TEXT,
    loadout_hash TEXT,
    score INTEGER,                  -- Base Score (Contextual)
    fg_score INTEGER,               -- Force Greats Score (PRIMARY RANKING METRIC)
    gear_json TEXT,
    minis_json TEXT,
    details_json TEXT,
    force_details_json TEXT,        -- JSON Force Greats config (GUARANTEED VALID)
    timestamp REAL,
    PRIMARY KEY (song_name, loadout_hash),
    FOREIGN KEY (song_name) REFERENCES songs(name)
);
```

### 4. `pending_fg_jobs` Table (Deferred Force Greats Work)
Stores a compact snapshot of GA candidates for songs whose Force Greats evaluation is **deferred** (e.g. GPU-native in-flight mode that interleaves FG at a fixed cadence).

This exists to:
- Keep FG candidates safe even if the base leaderboards are pruned (`LOADOUTS_PER_SONG_LIMIT`).
- Allow FG work to be resumed later without rerunning GA (best-effort; depends on config consistency).

```sql
CREATE TABLE pending_fg_jobs (
    song_name TEXT PRIMARY KEY,
    candidates_json TEXT NOT NULL,  -- JSON array of compact GA candidates
    created_ts REAL,
    updated_ts REAL
);
```

---

## Developer Guide: How to Query

### Python (Using `sqlite3`)

#### Querying Base Scores (Standard Leaderboard)
To get the top loadouts for normal gameplay, query the `loadouts` table ordered by `score`:

```python
cursor.execute("""
    SELECT score, gear_json 
    FROM loadouts 
    WHERE song_name = ? 
    ORDER BY score DESC 
    LIMIT 10
""", (song_name,))
```

#### Querying Force Greats Scores (FG Leaderboard)
To get the top loadouts for Force Greats, query the `fg_loadouts` table ordered by `fg_score`:

```python
cursor.execute("""
    SELECT fg_score, force_details_json 
    FROM fg_loadouts 
    WHERE song_name = ? 
    ORDER BY fg_score DESC 
    LIMIT 10
""", (song_name,))
```

### Key Differences for Developers

| Feature | `loadouts` Table | `fg_loadouts` Table |
| :--- | :--- | :--- |
| **Primary Metric** | `score` (Base Score) | `fg_score` (Force Greats Score) |
| **Content** | All Loadouts | Only Valid FG Loadouts |
| **Garbage Collection** | Keeps Top N by Score | Keeps Top N by FG Score |
| **Use Case** | General Gameplay, Leaderboards | FG Research, Simulation Analysis |

### Maintenance

*   **Migration**: If you have old data, use `scripts/migrate_fg_data.py` (if available) or simply re-run the optimizer. The system auto-populates `fg_loadouts` for new valid entries.
*   **Deduplication**: Both tables use `loadout_hash` as part of the composite primary key to prevent duplicate entries for the same *effective* gear+mini loadout (song-context mini equivalence).

### `minis_json` format (mini variants)

`minis_json` is stored as a JSON array where each element represents one equipped mini as a **variant group**.

Variant groups are populated *deterministically* from `Data/Gear/Minis.csv` using the song context
(primary/secondary/selected element), not based on which mini-name variants happened to appear during GA exploration.

- New format: `[[\"MiniA\",\"MiniA2\"],[\"MiniB\"],[\"MiniC\"]]`
- Legacy format (still readable): `[\"MiniA\",\"MiniB\",\"MiniC\"]`

Within a group, all names are considered equivalent for this song context (core stats + only the relevant element stats).
