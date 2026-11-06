# Chart and gear data

The repository ships its inputs here: chart files, gear tables, and the game export the tables are generated from.
Runtime results (`evolution.db`) and frontier credentials stay local and out of git.

This is a community-built analysis tool. It is not affiliated with, endorsed by, or connected to RoBeats, Roblox, or
any game publisher.

## Layout

```text
Data/
├── Easy/                      # Easy chart .txt files
├── Normal/                    # Normal chart .txt files
├── Hard/                      # Hard chart .txt files
└── exported_game_data.json    # game export: gears, minis, songs
```

The optimizer reads this fixed layout under `Data/` (or under `ROBEATSMETA_OPTIMIZER_DATA_DIR`). Chart files use the
RoBeats note-chart text format (tab-separated rows).

## Gears and Minis

The optimizer reads them straight from `exported_game_data.json`, so a new export needs no regeneration step. A gear's
export stats are final; a mini's are its level-1 stats, which the reader raises to max level.

## Auto sync

A new export takes effect by itself. Every run and every service solve reads the file as it is now, and the HTTP service
follows `origin/main`: within five minutes of a push, or at once after `POST /frontiers/refresh`, it moves to the new
`Data/` without a restart, builds the frontiers of new charts, and solves the official charts the database lacks.

## Results database

Runtime results live in `evolution.db` at the repository root by default. Do not commit this file. Host operators
typically keep it on an external path:

```bash
export EVOLUTION_DB_PATH=/path/to/evolution.db
```

## Generated caches (not in git)

| Path | Purpose |
|---|---|
| `evolution.db` | Base and Force Great leaderboards |
| `bin/timeline_frontier_cache/` | Exact fever-timing frontier payloads |
| `bin/fg_response_frontier_cache/` | Exact Force Great response-frontier payloads |

A run builds the frontiers its charts lack, and later runs reuse them.
