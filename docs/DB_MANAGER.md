# Evolution DB Manager (`EvolutionDbManager`)

## Why

The optimizer has a lot of DB touch points (seed reads, persistence writes, overlay mirroring, tooling).
`EvolutionDbManager` is a small wrapper that centralizes:

- DB path resolution (default `evolution.db`, override via `EVOLUTION_DB_PATH`)
- Schema initialization (via existing connection helpers/migrations)
- Common read/write calls used by the optimizer and tools

It does **not** change schema. It is a convenience API on top of `gear_optimizer.data.database`.

## Import

```python
from gear_optimizer.data.db_manager import EvolutionDbManager
```

## Construction

Canonical DB (default):

```python
db = EvolutionDbManager.from_env()
```

Canonical + overlay DB (backend/service mode use case):

```python
db = EvolutionDbManager.from_env(include_overlay=True)
```

## Baseline-Only TeamBuff Persistence (Default)

The default `evolution.db` workflow persists only the **baseline** TeamBuff tier rows (usually `T5`) into:

- `team_buff_loadouts`
- `team_buff_fg_loadouts`

Derived tiers (`NONE/T1/T10/T15`) are recomputed on demand (not persisted).
See: `docs/ON_DEMAND_TEAM_BUFF_TIER_SCORING.md`.

Legacy DB note:
- Pre-compact DBs that still store `gear_json` / `minis_json` are upgraded in place on schema init.
- Current reads use the compact BLOB columns after that repair/backfill step.

## Queueing

The manager exposes a small shared executor for cheap request queueing:

- Default is single-threaded (queued): `DB_MANAGER_MAX_WORKERS=1`

```python
fut = db.submit(db.get_song_catalog, team_buff="T5", max_rank=51)
catalog = fut.result(timeout=30)
```

## Writes

Persist baseline-tier loadouts:

```python
db.init_schema()
db.save_baseline_loadouts(song_key, entries, team_buff="T5")
```

Update per-song counters:

```python
db.update_song_counters(song_key, processed_run=True, record_improved=True)
```

## Reads

Fetch top-N baseline candidates (union of base + FG rows):

```python
rows = db.get_best_loadouts(song_key, limit=51, team_buff="T5")
```

## On-Demand Tier Recomputation

For ad-hoc recompute, use:

```bash
python tools/db/compute_team_buff_tiers_on_demand.py --help
```

For Python integration, call:

- `gear_optimizer.helpers.song_helpers.team_buff_tiers.compute_team_buff_tier_leaderboards(...)`

Or use the manager convenience method (loads config + ref_arrays by default):

```python
from gear_optimizer.data.db_manager import EvolutionDbManager

db = EvolutionDbManager.from_env()

out = db.compute_team_buff_tier_leaderboards_on_demand(
    "Rainshower (Easy) by Silentroom",
    song_file="Data/Normal/Rainshower.txt",
    element="selected",  # or primary/secondary
)
```

## API: Song Catalog (Available Songs + Ranks)

This replaces ad-hoc SQL for basic discovery.

```python
catalog = db.get_song_catalog(max_rank=51)
```

Returns a JSON-friendly dict:

- `team_buff`: the baseline tier queried
  - when omitted, this is resolved from the current config (`AutoSelectBuffAndColor` => `T5`, otherwise the configured
    `TeamContributionBuffConstant.TeamBuff`)
- `songs`: list of:
  - `song_name`
  - `leaderboards`: `["base"]`, `["fg"]`, or `["base","fg"]`
  - `base_ranks`: available base ranks `[1..N]` (clamped to `max_rank`)
  - `fg_ranks`: available fg ranks `[1..N]` (clamped to `max_rank`)

## API: Leaderboard Entry (On-Demand Tier Scoring)

View a single leaderboard entry by `(song, tier, leaderboard, rank)`.

```python
row = db.get_leaderboard_entry(
    "Rainshower (Easy) by Silentroom",
    leaderboard="fg",   # "base" or "fg"
    tier="T10",         # NONE/T1/T5/T10/T15 (computed on demand)
    rank=1,
    element="selected", # selected|primary|secondary
    # team_color="Rush", # optional explicit override (wins over element)
)
```

Notes:
- Tier scoring is computed on demand from the persisted baseline candidates.
- `leaderboard="fg"` filters to rows where `fg_score > score` and ranks by `fg_score DESC`.
- `element` controls which TeamColor is used for scoring:
  - `selected` (default): the run's resolved TeamColor (auto mode follows song Primary Color)
  - `primary`: force TeamColor to the song Primary Color
  - `secondary`: force TeamColor to the song Secondary Color (falls back to Primary)
- The manager attempts to resolve the chart file path automatically from the repo `Data/` layout. If it cannot resolve
  the file for the given `song_name`, it returns `None`.
