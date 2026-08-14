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
from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.core.config import load_config
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.database import get_best_loadouts
from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song
from gear_optimizer.helpers.song_helpers.team_buff_tiers import (
    compute_team_buff_tier_leaderboards,
)

config = cfg_to_dict(load_config())
song_key = "Rainshower (Easy) by Silentroom"
chart_path = "Data/Easy/Rainshower.txt"

entries = get_best_loadouts(
    song_key,
    team_buff="T5",
    limit=51,
)
base_song = get_base_calc_song(chart_path, config)

result = compute_team_buff_tier_leaderboards(
    entries=entries,
    calc_song=clone_calc_song(base_song),
    ref_arrays=_get_team_buff_ref_arrays_cached(),
    cfg_dict=config,
    tiers=("NONE", "T1", "T5", "T10", "T20", "T50", "T51"),
    limit=51,
)
```

The returned payload contains:

- `result["tiers"][tier]["base_top51"]`;
- `result["tiers"][tier]["fg_top51"]`; and
- `result["meta"]`, which describes the resolved tier and Team Color context.

The reference-array loader shown above is an application integration helper,
not a stable external SDK. In a separate application, provide the same Stats
lookup arrays explicitly.

## Timing modes

`timing_mode="perfect_window"` uses the exact timing-envelope model and is the
default. `timing_mode="zero_ms"` evaluates chart-time hits and recomputes both
surfaces for that timing model. The optimizer prebuilds both timing frontiers at
startup; tier views remain derived rankings and must not replace the canonical
persisted leaderboard.

## Persistence

`build_team_buff_tier_db_batches` can construct DB-ready derived batches for
specialized workflows. Normal optimizer persistence intentionally writes only
the baseline tier to control database size and preserve a single canonical
runtime result.
