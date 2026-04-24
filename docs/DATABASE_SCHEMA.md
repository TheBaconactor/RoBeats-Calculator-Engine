# Database Schema & Developer Guide

## Overview

The Gear Optimizer uses a SQLite database to store song metadata and loadout configurations.

Default persistence behavior (`evolution.db`):

- Persist only the **baseline** TeamBuff tier rows (typically `T5`).
- Derived tiers (`NONE/T1/T10/T20/T50/T51`) are computed **on demand** (not persisted).
- On-demand scoring entrypoint: `gear_optimizer.helpers.song_helpers.team_buff_tiers.compute_team_buff_tier_leaderboards(...)`
  (tool helper: `tools/db/compute_team_buff_tiers_on_demand.py`).
- Guide: `docs/ON_DEMAND_TEAM_BUFF_TIER_SCORING.md`
- Storage is compact by default:
  - Gear/minis are persisted as compact integer IDs via encoding tables + BLOB columns (not repeated JSON strings).
  - `details_json` stores packed Stats as a short fixed-order array (`st`), not verbose `Stats` keys.
  - Large derived fields (notably `hitsim_offset_deltas_ms`) are computed on demand and not persisted.

`EVOLUTION_DB_PATH` always overrides the resolved DB path for the current process.

The schema below describes the canonical tables. The optimizer only writes baseline-tier rows into the tiered tables.
When upgrading an older DB that still stores `gear_json` / `minis_json`, schema init backfills the compact BLOB columns
in place so current readers can decode those rows without a separate conversion step.

## Schema Definitions

### 1. `songs` Table
Stores high-level metadata and best known scores for each song.

```sql
CREATE TABLE songs (
    name TEXT PRIMARY KEY,          -- Unique song name
    best_score INTEGER DEFAULT 0,   -- Best Base Score
    best_fg_score INTEGER DEFAULT 0,-- Best Force Greats Score
    last_updated REAL               -- Timestamp of last update
);
```

### 2. `pending_fg_jobs` Table (Explicit Deferred Force Greats Work)
Stores a compact snapshot of GA candidates only for songs whose Force Greats
evaluation is explicitly made durable for later work.

This table is **not** the retained coverage frontier and should not be populated
by the normal in-process FG queue. Normal GPU-native in-flight runs drain FG in
memory; writing every in-memory FG job into SQLite creates large transient JSON
pages that SQLite may keep after delete.

Rules:
- `team_buff_loadouts` remains the retained base coverage frontier.
- Nonzero pending rows after a normal drained run should be treated as FG debt or
  an interrupted/deferred run, not as healthy coverage.
- A large pending row count is intentionally diagnostic: audit tooling warns when
  `pending_fg_jobs` exceeds `100` rows so the run can be inspected instead of
  silently hiding the backlog.

```sql
CREATE TABLE pending_fg_jobs (
    song_name TEXT PRIMARY KEY,
    candidates_json TEXT NOT NULL,  -- JSON array of compact GA candidates
    created_ts REAL,
    updated_ts REAL
);
```

### 3. `team_buff_loadouts` Table (Baseline TeamBuff Base Leaderboard)
Stores the **baseline** base leaderboard for a song under the run's baseline TeamBuff tier (typically `T5`).

Note:
- The schema allows `team_buff` values like `NONE/T1/T10/T20/T50/T51`, but the optimizer does not persist derived tiers.
- `NONE` is the true zero-effect view; the `51st+` non-zero cutoff is modeled separately as `T51`.
- Historical DBs may still contain the stale `T15` label, but current readers no longer alias those rows into canonical lookups.

```sql
CREATE TABLE team_buff_loadouts (
    song_name TEXT,
    team_buff TEXT,                -- 'NONE' | 'T1' | 'T5' | 'T10' | 'T20' | 'T50' | 'T51'
    loadout_hash TEXT,             -- Effective hash of (gear + mini signatures)
    score INTEGER,                 -- Base Score under this TeamBuff tier (PRIMARY RANKING METRIC)
    fg_score INTEGER DEFAULT 0,    -- Force Greats score under this tier (Contextual; may be 0)
    gear_ids_blob BLOB,            -- Compact gear IDs (varint list) into `gear_name_encoding`
    minis_ids_blob BLOB,           -- Compact mini variant-group IDs into `mini_name_encoding`
    details_json TEXT,
    force_details_json TEXT,
    timestamp REAL,
    PRIMARY KEY (song_name, team_buff, loadout_hash),
    FOREIGN KEY (song_name) REFERENCES songs(name)
);
```

### 4. `team_buff_fg_loadouts` Table (Baseline TeamBuff Force Greats Leaderboard)
Stores the **Force Greats leaderboard** re-scored under Team Buff tiers.
Only includes rows where `fg_score > score`.

Note:
- As with `team_buff_loadouts`, only baseline-tier rows are written by the optimizer.

```sql
CREATE TABLE team_buff_fg_loadouts (
    song_name TEXT,
    team_buff TEXT,                -- 'NONE' | 'T1' | 'T5' | 'T10' | 'T20' | 'T50' | 'T51'
    loadout_hash TEXT,
    score INTEGER,                 -- Base score under this TeamBuff tier (Contextual)
    fg_score INTEGER,              -- Force Greats score under this tier (PRIMARY RANKING METRIC)
    gear_ids_blob BLOB,            -- Compact gear IDs (varint list) into `gear_name_encoding`
    minis_ids_blob BLOB,           -- Compact mini variant-group IDs into `mini_name_encoding`
    details_json TEXT,
    force_details_json TEXT,
    timestamp REAL,
    PRIMARY KEY (song_name, team_buff, loadout_hash),
    FOREIGN KEY (song_name) REFERENCES songs(name)
);
```

---

## Compact Name Encoding (Schema v18+)

To keep the DB tiny, piece names are de-duplicated into encoding tables and persisted rows store only short integer IDs.

### `gear_name_encoding`

```sql
CREATE TABLE gear_name_encoding (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
```

### `mini_name_encoding`

```sql
CREATE TABLE mini_name_encoding (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
```

Notes:
- IDs are assigned deterministically in sorted order when initialized from the dataset, and then appended in sorted order
  for any newly-seen names.
- In the compact/default workflow, consumers decode piece names via encoding tables + `*_ids_blob`. Prefer the Python
  DB helpers/manager (see below) instead of reimplementing decoding logic.

## Compact `details_json` Payload

To reduce row size, some fields are stored in a compact form.

### Packed Stats (`details_json.st`)

Instead of persisting a verbose `details_json.Stats` dict, rows store:

- `details_json.st`: fixed-order integer list (length 10)

Order:
1. Perfect Points
2. Combo Multiplier
3. Fever Multiplier
4. Fever Fill Rate
5. Fever Time
6. Chill
7. Flow
8. Rush
9. Beat
10. Vibe

When loading via `gear_optimizer.data.database.get_best_loadouts(...)` (or via the manager), this is unpacked back into
`details["Stats"]` for consumers.

### HumanHitSim Context (`details_json.hs`)

To make on-demand recomputation deterministic when `HumanHitSim.Seed=0` (random-per-run), rows persist a compact timing
context:

- `details_json.hs = [seed, apply_to_code, dist_code, great_mode_code]`

This is used by on-demand tier recomputation to re-apply HumanHitSim per persisted row before scoring.

### Not Persisted

Some large derived fields are intentionally not persisted (computed on demand), including:

- `hitsim_offset_deltas_ms` (per-window timing deltas)

## Developer Guide: How to Query

### Prefer the DB Manager (Recommended)

Most consumers should not query SQLite directly anymore. Use the centralized manager API:

- `EvolutionDbManager.get_song_catalog(...)`: list songs + available ranks for base/FG leaderboards
- `EvolutionDbManager.get_leaderboard_entry(...)`: view a single (song, tier, leaderboard, rank) entry

Example:

```python
from gear_optimizer.data.db_manager import EvolutionDbManager

db = EvolutionDbManager.from_env()

catalog = db.get_song_catalog(max_rank=51)

row = db.get_leaderboard_entry(
    "Rainshower (Easy) by Silentroom",
    leaderboard="fg",   # "base" or "fg"
    tier="T10",         # NONE/T1/T5/T10/T20/T50/T51 (computed on demand)
    rank=1,
    element="selected", # selected|primary|secondary
)
```

This returns decoded `gear`/`minis` names and scores computed on demand.

See: `docs/DB_MANAGER.md`.

### Raw SQL (Use With Care)

If you only need scalar counts/scores, direct SQL is fine. Decoding `*_ids_blob` is intentionally a Python-level operation.

### Key Differences for Developers

| Feature | `team_buff_loadouts` Table | `team_buff_fg_loadouts` Table |
| :--- | :--- | :--- |
| **Primary Metric** | `score` (Base Score) | `fg_score` (Force Greats Score) |
| **Content** | All Loadouts (per tier) | Only Valid FG Loadouts (per tier) |
| **Garbage Collection** | Keeps Top N by Score | Keeps Top N by FG Score |
| **Use Case** | General Gameplay, Leaderboards | FG Research, Simulation Analysis |

### Maintenance

*   **Migration**: Schema is managed by `PRAGMA user_version` migrations in `gear_optimizer/data/migrations/`.
*   **Deduplication**: Both tables use `loadout_hash` as part of the composite primary key to prevent duplicate entries for the same *effective* gear+mini loadout (song-context mini equivalence).

### Mini Variant Groups

Mini slots are persisted as `minis_ids_blob` (encoding-table IDs) as a list of **variant groups**.

Conceptually this decodes to:

- `[[\"MiniA\",\"MiniA2\"],[\"MiniB\"],[\"MiniC\"]]`

Variant groups are populated *deterministically* from `Data/Gear/Minis.csv` using the song context
(primary/secondary/selected element), not based on which mini-name variants happened to appear during GA exploration.

Within a group, all names are considered equivalent for this song context (core stats + only the relevant element stats).
