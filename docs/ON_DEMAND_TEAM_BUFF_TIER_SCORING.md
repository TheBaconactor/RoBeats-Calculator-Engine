# On-Demand TeamBuff Tier Scoring (`evolution.db`)

## Summary

The default DB (`evolution.db`) is optimized for size: it persists only the **baseline** TeamBuff tier rows (usually `T5`)
and does **not** materialize `NONE/T1/T10/T15` rows.

When you need tiered leaderboards, compute them **on demand** from the persisted baseline candidates.

On-demand recompute is **GPU-backed**:

- Base score: `taichi_gem.api.fixed_scoring.score_fixed_stats_gpu(...)`
- FG score: `taichi_gem.force_greats.api.solve_force_greats_finder_gpu(...)` (fixed-stats evaluation)

## What Is Stored (Default DB)

Compact DB writes:

- `songs` (best base/FG scalar scores)
- `team_buff_loadouts` (base leaderboard) for the baseline tier only
- `team_buff_fg_loadouts` (FG leaderboard) for the baseline tier only

Derived tier rows (`NONE/T1/T10/T15`) are never persisted. They are recomputed on demand.

## How To Recompute Tier Leaderboards

### CLI (recommended)

This utility loads the persisted baseline candidates for a song, recomputes tiered base/FG scores, and prints Top1
results per tier.

```bash
python tools/db/compute_team_buff_tiers_on_demand.py `
  --song "Rainshower (Easy) by Silentroom" `
  --file "Data/Normal/Rainshower.txt" `
  --tiers "NONE,T1,T5,T10,T15" `
  --limit 51 `
  --element selected
```

Element / TeamColor overrides:

- `--element selected` (default): use the run's resolved TeamColor (auto mode follows the song's Primary Color).
- `--element primary`: score as if TeamColor were the song's Primary Color.
- `--element secondary`: score as if TeamColor were the song's Secondary Color (falls back to Primary if missing).
- `--team-color Rush`: force a specific TeamColor (overrides `--element`).

DB selection:

- Default: uses `evolution.db`.
- Override: pass `--db path/to/dbfile.db` (sets `EVOLUTION_DB_PATH` for the process).

Config selection (affects HumanHitSim semantics and tier baseline resolution):

- Default: uses repo `config.ini` resolution.
- Override: pass `--config path/to/config.ini` (sets `METAFINDER_CONFIG_PATH` for the process).

### Python API

If you want to integrate this into an exporter/backend:

```python
from gear_optimizer.core.config import load_config
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.database import get_best_loadouts
from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song

cfg = load_config()
cfg_dict = cfg_to_dict(cfg)

song_key = "Rainshower (Easy) by Silentroom"
song_file = "Data/Normal/Rainshower.txt"

# Baseline tier rows are stored under the baseline TeamBuff (typically T5).
baseline_team_buff = "T5"
entries = get_best_loadouts(song_key, limit=51, team_buff=baseline_team_buff)

base_calc_song = get_base_calc_song(song_file, cfg_dict)
calc_song = clone_calc_song(base_calc_song)

# ref_arrays is the Stats lookup table bundle (Perfect Points, CM, FM, FT, FF).
from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
ref_arrays = _get_team_buff_ref_arrays_cached()

payload = compute_team_buff_tier_leaderboards(
    entries=entries,
    calc_song=calc_song,
    ref_arrays=ref_arrays,
    cfg_dict=cfg_dict,
    tiers=("NONE", "T1", "T5", "T10", "T15"),
    target_team_color_override=None,  # or "Rush" / "Flow" / etc
)
```

The result shape is:

- `payload["tiers"][tier]["base_top51"]`: list of rows ranked by base `score`
- `payload["tiers"][tier]["fg_top51"]`: list of rows ranked by `fg_score`
- `payload["meta"]`: resolved TeamBuff/TeamColor context

## Note

This repo intentionally avoids persisting derived tiers to keep DB size and per-song CPU cost low.

## HumanHitSim Recompute (Seeded)

When HumanHitSim is enabled with `HumanHitSim.Seed=0`, the optimizer chooses a different random seed per run. To make
on-demand recomputation deterministic, persisted rows include a compact timing context:

- `details_json.hs = [seed, apply_to_code, dist_code, great_mode_code]`

This allows tier recompute to re-apply HumanHitSim per persisted row before scoring (without changing DB keys).
