# Data setup

RoBeats Calculator Engine ships chart files, gear tables, and `exported_game_data.json` in the `Data/` tree. Runtime results (`evolution.db`) and frontier credentials stay local and out of git.

## Disclaimer

This is a **community-built analysis tool**. It is not affiliated with, endorsed by, or connected to RoBeats, Roblox, or any game publisher.

## Who uses which data source?

| Persona | Data source |
|---|---|
| **Host operator** | Maintains the canonical `Data/` tree in git and on the authoritative machine; builds frontiers and publishes revisions. |
| **Trusted clients** | Receive Data/frontier bundles from an explicitly configured host (requires `bin/frontier_client_credentials.json`). |
| **Community DIY users** | Use the `Data/` tree from a git clone, or populate their own copy before the first run. Frontier sync is skipped when no credential file is present. |

## Directory layout

```text
Data/
├── Easy/                      # Easy chart .txt files
├── Normal/                    # Normal chart .txt files
├── Hard/                      # Hard chart .txt files
├── Gear/
│   ├── Gears.csv
│   ├── Minis.csv
│   └── Stats.txt
└── exported_game_data.json    # game export; feeds gear CSV regeneration
```

After the first successful path discovery, the optimizer writes `bin/paths_cache.json`. Delete that file if you move or replace `Data/`.

## Gear and Mini tables

Regenerate CSVs from the bundled export when game data changes:

```bash
python -m gear_optimizer.cli sync-data
```

## Results database

Runtime results live in `evolution.db` at the repository root by default. Do not commit this file.

```bash
export EVOLUTION_DB_PATH=/path/to/evolution.db
```

Host operators typically use an external database path via this variable.

## Generated caches (not in git)

| Path | Purpose |
|---|---|
| `evolution.db` | Base and Force Great leaderboards |
| `bin/timeline_frontier_cache/` | Exact fever-timing frontier payloads |
| `bin/fg_response_frontier_cache/` | Exact Force Great response-frontier payloads |
| `bin/paths_cache.json` | Auto-discovered data paths |
| `bin/frontier_publications/` | Host-side published revisions (server only) |

On the host, only the authoritative machine builds timeline and FG frontiers for publication. Trusted clients install prebuilt frontier bundles from the host.

## Host operator notes

| Asset | Action |
|---|---|
| `Data/` tree | Maintained in git and on the host; published via frontier bundles |
| `evolution.db` | External path via `EVOLUTION_DB_PATH` |
| Frontier server | Publication flow, client registry, and `/metafinder/v1` distribution |
| Host application | Authenticate to the documented `/songs` and `/optimize` service endpoints |
