# Manual Exported Game Data Sync

## Date

2026-05-13

## Decision

`Data/Gear/Gears.csv` and `Data/Gear/Minis.csv` are regenerated from
`Data/exported_game_data.json` only when the maintainer explicitly runs:

```powershell
python -m gear_optimizer.cli sync-data
```

Normal optimizer startup does not regenerate these files.

## Invariant

The checked-in optimizer gear and mini CSVs must exactly match the exported game
data source after the manual sync command is run.

## Enforcement

`tests/test_general_meta_main_data_sync.py` regenerates both CSVs to a temporary
directory and compares them byte-for-byte with the checked-in `Data/Gear` files.
This makes stale CSVs fail loudly during targeted tests and quality checks.
