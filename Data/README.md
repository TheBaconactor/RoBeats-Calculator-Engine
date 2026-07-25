# User-supplied data

This directory is **not** shipped with the public repository. You must provide your own chart and gear files before running the optimizer.

See [DATA.md](../DATA.md) for the required layout, gear CSV format, and setup steps.

## Expected layout

```text
Data/
├── Easy/          # Easy chart .txt files
├── Normal/        # Normal chart .txt files
├── Hard/          # Hard chart .txt files
├── Gear/
│   ├── Gears.csv
│   ├── Minis.csv
│   └── Stats.txt
└── exported_game_data.json   # optional; used by `python -m gear_optimizer.cli sync-data`
```

Chart files use the RoBeats note-chart text format (tab-separated rows). Gear tables can be maintained manually or regenerated from `exported_game_data.json`.
