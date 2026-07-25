# Chart and gear data

This directory ships with the repository. The host operator maintains the canonical catalog here, publishes it through frontier bundles to trusted clients, and keeps it in sync with git.

See [DATA.md](../DATA.md) for layout, gear CSV format, and deployment-specific notes.

## Layout

```text
Data/
├── Easy/          # Easy chart .txt files
├── Normal/        # Normal chart .txt files
├── Hard/          # Hard chart .txt files
├── Gear/
│   ├── Gears.csv
│   ├── Minis.csv
│   └── Stats.txt
└── exported_game_data.json   # structured game export; feeds `python -m gear_optimizer.cli sync-data`
```

Chart files use the RoBeats note-chart text format (tab-separated rows). Gear tables can be maintained manually or regenerated from `exported_game_data.json`.
