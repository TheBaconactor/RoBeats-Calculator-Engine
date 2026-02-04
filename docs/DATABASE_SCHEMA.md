# Database Schema & Developer Guide

## Overview

The Gear Optimizer uses a SQLite database (`evolution.db`) to store song metadata and loadout configurations.
As of **February 2026**, the database uses **TeamBuff-tiered leaderboards** to separate Base Scores (regular gameplay) from Force Greats Scores (simulation), per tier.

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

### 2. `pending_fg_jobs` Table (Deferred Force Greats Work)
Stores a compact snapshot of GA candidates for songs whose Force Greats evaluation is **deferred** (e.g. GPU-native in-flight mode that batches FG work and may drain later).

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

### 3. `team_buff_loadouts` Table (TeamBuff-Tier Base Leaderboard)
Stores the **base leaderboard** re-scored under specific Team Buff tiers (`T1`, `T5`, `T10`, `T15`).
This is populated in **post-processing** for new runs (no extra GPU work).

```sql
CREATE TABLE team_buff_loadouts (
    song_name TEXT,
    team_buff TEXT,                -- 'NONE' | 'T1' | 'T5' | 'T10' | 'T15'
    loadout_hash TEXT,             -- Effective hash of (gear + mini signatures)
    score INTEGER,                 -- Base Score under this TeamBuff tier (PRIMARY RANKING METRIC)
    fg_score INTEGER DEFAULT 0,    -- Force Greats score under this tier (Contextual; may be 0)
    gear_json TEXT,
    minis_json TEXT,
    details_json TEXT,
    force_details_json TEXT,
    timestamp REAL,
    PRIMARY KEY (song_name, team_buff, loadout_hash),
    FOREIGN KEY (song_name) REFERENCES songs(name)
);
```

### 4. `team_buff_fg_loadouts` Table (TeamBuff-Tier Force Greats Leaderboard)
Stores the **Force Greats leaderboard** re-scored under Team Buff tiers.
Only includes rows where `fg_score > score`.

```sql
CREATE TABLE team_buff_fg_loadouts (
    song_name TEXT,
    team_buff TEXT,                -- 'NONE' | 'T1' | 'T5' | 'T10' | 'T15'
    loadout_hash TEXT,
    score INTEGER,                 -- Base score under this TeamBuff tier (Contextual)
    fg_score INTEGER,              -- Force Greats score under this tier (PRIMARY RANKING METRIC)
    gear_json TEXT,
    minis_json TEXT,
    details_json TEXT,
    force_details_json TEXT,
    timestamp REAL,
    PRIMARY KEY (song_name, team_buff, loadout_hash),
    FOREIGN KEY (song_name) REFERENCES songs(name)
);
```

---

## Convenience Views (Frontend/Exports)

These views provide stable query surfaces for consumers that want:
- A single FG leaderboard surface with `team_buff` always present.
- A single base leaderboard surface across tiers.
- Deterministic "best row" selection for each `(song_name, team_buff)`.

### `fg_loadouts_unified`
Unifies FG rows across:
- `team_buff_fg_loadouts`

### `loadouts_unified` (schema v15+)
Unifies base rows across:
- `team_buff_loadouts`

### Frontend helpers (schema v15+)
- `frontend_best_base_loadouts`: best base row per `(song_name, team_buff)` (ranked by `score DESC`, then `fg_score`, then `timestamp`).
- `frontend_best_fg_loadouts`: best FG row per `(song_name, team_buff)` (ranked by `fg_score DESC`, then `score`, then `timestamp`).
- `frontend_base_top51_by_song_tier`: top 51 base rows per `(song_name, team_buff)` with derived `song_title`/`difficulty`.
- `frontend_fg_top51_by_song_tier`: top 51 FG rows per `(song_name, team_buff)` with derived `song_title`/`difficulty`.

---

## Developer Guide: How to Query

### Python (Using `sqlite3`)

#### Querying Base Scores (Standard Leaderboard)
To get the top loadouts for normal gameplay, query the `team_buff_loadouts` table ordered by `score`:

```python
cursor.execute("""
    SELECT score, gear_json 
    FROM team_buff_loadouts 
    WHERE song_name = ? AND team_buff = ?
    ORDER BY score DESC 
    LIMIT 10
""", (song_name, "T5"))
```

#### Querying Force Greats Scores (FG Leaderboard)
To get the top loadouts for Force Greats, query the `team_buff_fg_loadouts` table ordered by `fg_score`:

```python
cursor.execute("""
    SELECT fg_score, force_details_json 
    FROM team_buff_fg_loadouts 
    WHERE song_name = ? AND team_buff = ?
    ORDER BY fg_score DESC 
    LIMIT 10
""", (song_name, "T5"))
```

#### Querying TeamBuff-Tier Base Scores
```python
cursor.execute("""
    SELECT score, gear_json
    FROM team_buff_loadouts
    WHERE song_name = ? AND team_buff = ?
    ORDER BY score DESC
    LIMIT 10
""", (song_name, "T10"))
```

#### Querying TeamBuff-Tier Force Greats Scores
```python
cursor.execute("""
    SELECT fg_score, force_details_json
    FROM team_buff_fg_loadouts
    WHERE song_name = ? AND team_buff = ?
    ORDER BY fg_score DESC
    LIMIT 10
""", (song_name, "T10"))
```

### Key Differences for Developers

| Feature | `team_buff_loadouts` Table | `team_buff_fg_loadouts` Table |
| :--- | :--- | :--- |
| **Primary Metric** | `score` (Base Score) | `fg_score` (Force Greats Score) |
| **Content** | All Loadouts (per tier) | Only Valid FG Loadouts (per tier) |
| **Garbage Collection** | Keeps Top N by Score | Keeps Top N by FG Score |
| **Use Case** | General Gameplay, Leaderboards | FG Research, Simulation Analysis |

### Maintenance

*   **Migration**: Re-run the optimizer to repopulate tiered tables. Schema v16+ drops deprecated base/FG tables.
*   **Deduplication**: Both tables use `loadout_hash` as part of the composite primary key to prevent duplicate entries for the same *effective* gear+mini loadout (song-context mini equivalence).

### `minis_json` format (mini variants)

`minis_json` is stored as a JSON array where each element represents one equipped mini as a **variant group**.

Variant groups are populated *deterministically* from `Data/Gear/Minis.csv` using the song context
(primary/secondary/selected element), not based on which mini-name variants happened to appear during GA exploration.

- New format: `[[\"MiniA\",\"MiniA2\"],[\"MiniB\"],[\"MiniC\"]]`

Within a group, all names are considered equivalent for this song context (core stats + only the relevant element stats).
