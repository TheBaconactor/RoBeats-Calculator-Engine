# Data setup

RoBeats Song Optimizer ships chart files, gear tables, and `exported_game_data.json` in the `Data/` tree. Runtime results (`evolution.db`) and frontier credentials stay local and out of git.

See the root README [Deployment models](README.md#deployment-models) for how each persona uses this data.

## Disclaimer

This is a **community-built analysis tool**. It is not affiliated with, endorsed by, or connected to RoBeats, Roblox, or any game publisher.

## Who uses which data source?

| Persona | Data source |
|---|---|
| **Host operator** | Maintains the canonical `Data/` tree in git and on the authoritative machine; builds frontiers and publishes revisions. |
| **Trusted clients** | Receive the host's published Data/frontier bundles via `https://api.robeatsmeta.net/metafinder/v1` (requires `bin/frontier_client_credentials.json`). |
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
export METAFINDER_EVOLUTION_DB=/path/to/evolution.db
```

The host operator and [RoBeatsMeta](https://robeatsmeta.net) website pipeline typically use an external database path via this variable.

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
| `evolution.db` | External path via `METAFINDER_EVOLUTION_DB` |
| Frontier server | Publication flow, client registry, and `/metafinder/v1` distribution |
| Website bridge | `ROBEATSMETA_OPTIMIZER_REPO_ROOT`, service token, `/songs`, `/optimize` |
| Website game-data sync | RoBeatsMeta can sync `Data/exported_game_data.json` from this repo on GitHub, or copy from a local sibling checkout |
