# Data setup

RoBeats Song Optimizer does **not** ship chart files, gear tables, or a prebuilt `evolution.db` in the public repository. How you obtain data depends on your deployment model — see the root README [Deployment models](README.md#deployment-models).

## Disclaimer

This is a **community-built analysis tool**. It is not affiliated with, endorsed by, or connected to RoBeats, Roblox, or any game publisher. Chart data must come from your own lawful sources. Do not commit proprietary chart dumps or credentials to a public fork.

## Who supplies data?

| Persona | Data source |
|---|---|
| **Host operator** | Local `Data/` tree on the authoritative machine (untracked). Host builds frontiers and publishes a canonical revision. |
| **Trusted clients** | Synced from the host via `https://api.robeatsmeta.net/metafinder/v1` (requires `bin/frontier_client_credentials.json`). Clients do not rebuild the published catalog locally. |
| **Community DIY users** | You populate `Data/` yourself before the first run. Frontier sync is skipped when no credential file is present. |

## Directory layout

Create this structure under the repository root (DIY users and host operators; see also `Data/README.md`):

```text
Data/
├── Easy/                      # Easy chart .txt files
├── Normal/                    # Normal chart .txt files
├── Hard/                      # Hard chart .txt files
├── Gear/
│   ├── Gears.csv
│   ├── Minis.csv
│   └── Stats.txt
└── exported_game_data.json    # optional; feeds gear CSV regeneration
```

After the first successful path discovery, the optimizer writes `bin/paths_cache.json`. Delete that file if you move or replace `Data/`.

## Chart files

Each chart is a tab-separated text file named like the in-game chart identity, for example:

```text
Data/Hard/Example Song (Hard) by Artist.txt
```

The optimizer discovers charts by scanning `Data/Easy`, `Data/Normal`, and `Data/Hard`.

- **DIY users:** obtain and maintain these files yourself.
- **Host operator:** keeps the canonical catalog locally; publishes it in frontier bundles.
- **Trusted clients:** receive charts through hosted sync, not from git.

## Gear and Mini tables

`Data/Gear/Gears.csv`, `Data/Gear/Minis.csv`, and `Data/Gear/Stats.txt` describe the gear and Mini stat surface the search uses.

If you have `Data/exported_game_data.json` (a structured game export), regenerate the CSVs:

```bash
python -m gear_optimizer.cli sync-data
```

## Results database

Runtime results are stored in `evolution.db` at the repository root by default. This file is generated locally and should not be committed.

Override the location with:

```bash
export METAFINDER_EVOLUTION_DB=/path/to/evolution.db
```

The host operator and [RoBeatsMeta](https://robeatsmeta.net) website pipeline use an external database path via this variable.

## Generated caches

These paths are created during normal operation and stay out of git:

| Path | Purpose |
|---|---|
| `evolution.db` | Base and Force Great leaderboards |
| `bin/timeline_frontier_cache/` | Exact fever-timing frontier payloads |
| `bin/fg_response_frontier_cache/` | Exact Force Great response-frontier payloads |
| `bin/paths_cache.json` | Auto-discovered data paths |
| `bin/frontier_publications/` | Host-side published revisions (server only) |
| `bin/` (other) | Logs, profiles, frontier download state |

On the host, only the authoritative machine builds timeline and FG frontiers for publication. Trusted clients install prebuilt frontier bundles from the host. DIY users build frontiers locally on their own GPU.

## Configuration

Copy the template and set your target chart:

```bash
cp config.ini.example config.ini
```

Edit `[CalculateSong]` — see the root README for field meanings. Override the config path with `METAFINDER_CONFIG_PATH` if needed.

## Host operator migration (post-OSS)

If you already run the optimizer as the RoBeatsMeta host:

| Asset | Action |
|---|---|
| `Data/` tree | Keep your existing local copy; it stays untracked |
| `evolution.db` | Keep using `METAFINDER_EVOLUTION_DB` pointing at your external database |
| Frontier server | No change — publication flow, client registry, and `/metafinder/v1` distribution stay required for trusted clients |
| Website bridge | `ROBEATSMETA_OPTIMIZER_REPO_ROOT`, service token, `/songs`, `/optimize`, and evolution.db pipeline are unchanged |
| Git source | Point `ROBEATSMETA_FRONTIER_GIT_REMOTE` / `ROBEATSMETA_FRONTIER_GIT_BRANCH` at public GitHub `main` |
| Website game-data sync | RoBeatsMeta prefers `ROBEATSMETA_GAME_DATA_LOCAL_PATH` or sibling `../RoBeats-Calculator-Engine/Data/exported_game_data.json`; GitHub fetch via `ROBEATSMETA_GAME_DATA_REPO` / `ROBEATSMETA_GAME_DATA_PATH` is the fallback |

Nothing in the OSS split removes the host's role as the sole frontier builder and publisher. Trusted clients still require credentials. Only community DIY users treat frontier auth as optional.
