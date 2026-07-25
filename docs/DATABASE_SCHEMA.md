# Database Schema

RoBeats Calculator Engine stores retained results in SQLite. The canonical
Python surface is `gear_optimizer.data.database`; schema definition and
validation live in `gear_optimizer/data/migrations/`.

## Path and lifecycle

- `EVOLUTION_DB_PATH` overrides the database location for the current process.
- Without an override, the connection layer uses the resolved default
  `evolution.db` location.
- Write connections enable WAL mode and validate schema version 18.
- A new empty database receives the current schema.
- An unversioned, legacy-version, or newer-than-supported existing database
  fails loudly. Rebuild or migrate it explicitly; startup does not guess.

Runtime databases are generated state and must not be committed.

## Tables

### `songs`

Stores per-chart maxima and attempt counters.

```sql
CREATE TABLE songs (
    name TEXT PRIMARY KEY,
    best_score INTEGER DEFAULT 0,
    best_fg_score INTEGER DEFAULT 0,
    last_updated REAL,
    attempt_lifetime INTEGER DEFAULT 0,
    attempts_first INTEGER DEFAULT 0
);
```

### `team_buff_loadouts`

Retains the Base leaderboard. `score` is the ranking authority; `fg_score` is
context only.

```sql
CREATE TABLE team_buff_loadouts (
    song_name TEXT,
    team_buff TEXT,
    loadout_hash TEXT,
    score INTEGER,
    fg_score INTEGER DEFAULT 0,
    gear_ids_blob BLOB,
    minis_ids_blob BLOB,
    details_json TEXT,
    force_details_json TEXT,
    timestamp REAL,
    PRIMARY KEY (song_name, team_buff, loadout_hash),
    FOREIGN KEY (song_name) REFERENCES songs(name)
);
```

### `team_buff_fg_loadouts`

Retains the Force Great leaderboard. `fg_score` is the ranking authority and
the row carries the replayable Force Great payload.

```sql
CREATE TABLE team_buff_fg_loadouts (
    song_name TEXT,
    team_buff TEXT,
    loadout_hash TEXT,
    score INTEGER,
    fg_score INTEGER,
    gear_ids_blob BLOB,
    minis_ids_blob BLOB,
    details_json TEXT,
    force_details_json TEXT,
    timestamp REAL,
    PRIMARY KEY (song_name, team_buff, loadout_hash),
    FOREIGN KEY (song_name) REFERENCES songs(name)
);
```

The two leaderboard tables are intentionally separate. A high Base result may
not be the best Force Great result, and pruning one table by the other
objective would lose valid candidates.

### Name-encoding tables

Gear and Mini names are deduplicated and referenced by compact integer IDs:

```sql
CREATE TABLE gear_name_encoding (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE mini_name_encoding (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
```

`gear_ids_blob` stores a packed ID list. `minis_ids_blob` stores packed Mini
variant groups. Use the Python database package to decode them.

## Indexes

```sql
CREATE INDEX idx_team_buff_loadouts_score
    ON team_buff_loadouts (song_name, team_buff, score DESC);

CREATE INDEX idx_team_buff_loadouts_fg_score
    ON team_buff_loadouts (song_name, team_buff, fg_score DESC);

CREATE INDEX idx_team_buff_fg_loadouts_score
    ON team_buff_fg_loadouts (song_name, team_buff, fg_score DESC);
```

## Payload contracts

- `details_json` describes and replays `score`.
- `force_details_json` on a Force Great row describes and replays `fg_score`.
- Gear and Mini names are represented by the encoding BLOBs, not repeated JSON
  lists.
- Stats and common color/gem fields are compacted for storage and expanded by
  `get_best_loadouts`.
- A Force Great gem allocation must not overwrite the Base details payload.

Default optimizer writes retain the configured baseline Team Buff, normally
`T5`. Other tiers can be recomputed from retained candidates through the
[on-demand tier scoring API](ON_DEMAND_TEAM_BUFF_TIER_SCORING.md).

## Python API

Initialize a database:

```python
from gear_optimizer.data.database import init_db

init_db()
```

Read retained candidates:

```python
from gear_optimizer.data.database import get_best_loadouts

entries = get_best_loadouts(
    "Rainshower (Easy) by Silentroom",
    team_buff="T5",
    limit=51,
)
```

Persist a complete optimizer result atomically:

```python
from gear_optimizer.data.database import save_optimizer_song_result

save_optimizer_song_result(
    song_name,
    entries,
    processed_run=True,
    team_buff="T5",
)
```

`save_optimizer_song_result` commits retained entries and the processed-run
counters in one transaction. Lower-level functions such as
`save_loadouts_batch` exist for scoped maintenance and integration work.

## Raw SQL

Direct SQL is appropriate for scalar inspection. Do not reimplement BLOB or
payload decoding in a separate consumer; use the package facade so schema and
normalization changes remain centralized.
