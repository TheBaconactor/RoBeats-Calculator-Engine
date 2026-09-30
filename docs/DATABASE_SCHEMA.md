# Database Schema

RoBeats Calculator Engine stores retained results in SQLite. `gear_optimizer/store` owns the format:
`records` (typed rows), `schema` (the DDL, connections, migrations), `boards` (board order and the merge of
new results), `db` (reads and writes), `v18` (the previous format's reader and the migration from it).

## Path and lifecycle

- `EVOLUTION_DB_PATH` overrides the database location for the current process; the default is
  `<engine>/evolution.db`.
- `schema.connect(path, write=True)` enables WAL, creates schema version 19 on an empty database and
  migrates a version 18 database (`store.v18.migrate`, one transaction). Any other version fails loudly.
- `schema.connect(path)` opens a read-only connection and requires version 19.

Runtime databases are generated state and must not be committed.

## Tables

### `songs`

One row per song the optimizer has processed (a run that stored nothing still marks the song).

```sql
CREATE TABLE songs (
    name TEXT PRIMARY KEY,
    last_updated REAL NOT NULL
) STRICT;
```

### `loadouts`

One row per loadout of a song and TeamBuff tier. A loadout keeps its results while it is stored: its meta
result (the best gem allocation without Force Greats, scored `score`) and its Force Greats result (scored
`fg_score`). Two boards list loadouts by those results; a loadout is stored while it is on at least one.

```sql
CREATE TABLE loadouts (
    song_name TEXT NOT NULL REFERENCES songs (name),
    team_buff TEXT NOT NULL,
    loadout_hash TEXT NOT NULL,
    gear TEXT NOT NULL,            -- JSON list of gear names, slot order
    minis TEXT NOT NULL,           -- JSON list: per equipped mini, its equivalent names (display order)
    primary_color TEXT NOT NULL,
    secondary_color TEXT NOT NULL,
    mini_ascension TEXT,           -- Mini Ascension version of the row's minis (NULL: an older row)
    score INTEGER NOT NULL,        -- the loadout's base score (single source)
    fg_score INTEGER,              -- its best known Force Greats score (NULL: never evaluated)
    meta_board INTEGER NOT NULL,   -- 1: on the meta board
    fg_board INTEGER NOT NULL,     -- 1: on the Force Greats board
    meta_updated INTEGER,          -- meta result: NULL columns = none
    meta_seq INTEGER,
    meta_result TEXT,              -- JSON {element, gems[6], stats[10]}
    fg_updated INTEGER,            -- Force Greats result: NULL columns = none
    fg_seq INTEGER,
    fg_result TEXT,                -- JSON {element, gems[6], stats[10], surface[11]}
    meta_trace BLOB,               -- zlib JSON: the timeline frontier replay witness
    fg_trace BLOB,                 -- zlib JSON: the Force Greats replay witness (also kept without an FG
                                   -- result for loadouts whose FG row version 18 had pruned)
    PRIMARY KEY (song_name, team_buff, loadout_hash),
    ...
) STRICT;
```

Gems follow `stats.GEM_KINDS` and stats `gamedata.STATS`. `*_updated` is the unix second of the last write
of that result; `*_seq` numbers results in the order they were stored, across the whole database.
The traces come last so board scans never read them; `store.db.load_traces` loads them on request.

## Boards

- Meta board (`meta_board = 1`): the loadouts with a meta result, by `score DESC, fg_score DESC (NULL last),
  meta_updated DESC, meta_seq`.
- Force Greats board (`fg_board = 1`): the loadouts whose FG result beats their score, by `fg_score DESC,
  score DESC, fg_updated DESC, fg_seq`.
- Each board lists `LOADOUTS_PER_SONG_LIMIT` (51) loadouts per song and tier: the best scores, the earliest
  stored among equal scores. A loadout off both boards is deleted with its results; one on a board keeps both
  results (an FG result off the FG board stays attached, and returns to the board when a place frees up).

Two partial indexes cover the board orders (`loadouts_meta_board`, `loadouts_fg_board`).

## Python API

```python
from gear_optimizer.store import db, schema

conn = schema.connect(path)                       # read-only, version 19
boards = db.load_boards(conn, song, "T5")         # typed Loadout lists in board order
traces = db.load_traces(conn, song, "T5", [x.loadout_hash for x in boards.meta])
for loadout in db.iter_board(conn, "fg", tier="T5"):  # catalog streams, song by song
    ...
```

Writes merge a solve's results into a song's boards in one transaction (`db.store_results`); the pipeline
and the service still hand over version 18 shaped entry dicts through `store.legacy` (`store_entries`,
`promote_entries`, `best_loadouts`) until they build typed candidates themselves.

## Raw SQL

Direct SQL is appropriate for scalar inspection. Do not reimplement row decoding in a separate consumer; use
the store so format changes stay in one place.
