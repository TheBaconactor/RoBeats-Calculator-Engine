# On-Demand Team Buff Tier Scoring

The default results database retains the optimizer's baseline Team Buff rows,
normally `T5`. Derived views such as `NONE`, `T1`, `T10`, `T20`, `T50`, and
`T51` are recomputed from those retained loadouts rather than materialized by
the normal optimizer run.

`NONE` is the zero-effect view. `T51` represents the `51st+` non-zero cutoff.

## Scoring contract

`gear_optimizer.helpers.song_helpers.team_buff_tiers` owns the recomputation:

- the loadout set comes from persisted baseline candidates;
- gem allocation is solved again for each tier and selected Team Color;
- Base and Force Great surfaces are ranked separately;
- retained scores receive exact CPU reference rescore; and
- malformed or missing Force Great response surfaces fail loudly.

The result is exact for each supplied retained loadout. It does not turn the
outer genetic search into an exhaustive loadout search.

## Python API

```python
from pathlib import Path

from gear_optimizer.chart import load_chart
from gear_optimizer.store.legacy import read_best_loadouts
from gear_optimizer.gamedata import load_stat_curves
from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
    compute_team_buff_tier_leaderboards,
)
from gear_optimizer.settings import paths
from gear_optimizer.solver.timing_envelope import time_song

song_key = "Rainshower (Easy) by Silentroom"
song = time_song(load_chart(Path("Data/Easy/Rainshower.txt")), "perfect_window")

entries = read_best_loadouts(paths().database, song_key, "T5", limit=51)

result = compute_team_buff_tier_leaderboards(
    entries=entries,
    song=song,
    curves=load_stat_curves(paths().stats_txt),
    tiers=("NONE", "T1", "T5", "T10", "T20", "T50", "T51"),
    limit=51,
)
```

The returned payload contains:

- `result["tiers"][tier]["base_top51"]`;
- `result["tiers"][tier]["fg_top51"]`; and
- `result["meta"]`, which describes the resolved tier and Team Color context.

`load_stat_curves` reads the Stats.txt curves (cached until the file changes);
`load_chart` parses the chart (cached the same way) and `time_song` prepares it
for one timing mode.

## Timing modes

The song's timing mode selects the model: `time_song(chart, "perfect_window")`
uses the exact timing-envelope model and is the default; `time_song(chart,
"zero_ms")` evaluates chart-time hits and recomputes both surfaces for that
timing model. The optimizer prebuilds both timing frontiers at
startup; tier views remain derived rankings and must not replace the canonical
persisted leaderboard.

## Persistence

`build_team_buff_tier_db_batches` can construct DB-ready derived batches for
specialized workflows. Normal optimizer persistence intentionally writes only
the baseline tier to control database size and preserve a single canonical
runtime result.
