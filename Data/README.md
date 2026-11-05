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
├── Gear/
│   ├── Gears.csv
│   └── Minis.csv
└── exported_game_data.json    # game export; feeds gear CSV regeneration
```

The optimizer reads this fixed layout under `Data/` (or under `ROBEATSMETA_OPTIMIZER_DATA_DIR`). Chart files use the
RoBeats note-chart text format (tab-separated rows).

## Who uses which data source?

| Persona | Data source |
|---|---|
| **Host operator** | Maintains the canonical `Data/` tree in git and on the authoritative machine; builds frontiers and publishes revisions. |
| **Trusted clients** | Receive Data/frontier bundles from an explicitly configured host (requires `bin/frontier_client_credentials.json`). |
| **Community DIY users** | Use the `Data/` tree from a git clone, or populate their own copy before the first run. Frontier sync is skipped when no credential file is present. |

## Gear and Mini tables

Regenerate the CSVs from the bundled export when game data changes:

```bash
python -m gear_optimizer.cli sync-data
```

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
| `bin/frontier_publications/` | Host-side published revisions (server only) |

Only the authoritative machine builds timeline and FG frontiers for publication. Trusted clients install prebuilt
frontier bundles from the host; see the
[maintenance playbook](../docs/MAINTENANCE_PLAYBOOK.md#managed-frontier-distribution).
