# On-Demand TeamBuff Tier Scoring (`evolution.db`)

## Summary

The default DB (`evolution.db`) is optimized for size: it persists only the **baseline** TeamBuff tier rows (usually `T5`)
and does **not** materialize `NONE/T1/T10/T20/T50/T51` rows.

Tier note:

- `NONE` is the true zero-effect view
- `T51` models the `51st+` non-zero cutoff (`+10 chosen-color stat`, `+5 Perfect Points`)

When you need tiered leaderboards, compute them **on demand** from the persisted baseline candidates.

On-demand recompute is owned by `gear_optimizer/helpers/song_helpers/team_buff_tiers.py`:

- Base: re-solve the retained loadout's gems with the canonical GPU loadout evaluator, then exact-rescore the resolved
  Stats with `solver.scoring.exact_rescore.score_stats_exact_batch(...)` (or the fixed-timing equivalent for zero-ms).
- FG score: `solver.scoring.exact_rescore.score_force_greats_response_surface_exact(...)` over the
  persisted `response_surface` (the canonical exact FG representation). FG rows without a persisted
  surface fail loudly. Tier deltas never shift FT/FF, so the fever/great timeline is tier-invariant
  and the baseline-tier replay is bit-exact to the persisted `fg_score`. See
  `docs/Implementation Records/FG_TIER_REPLAY_RESPONSE_SURFACE_AUTHORITY.md`.

Production FG optimization itself remains GPU-first; tier recompute uses the persisted exact response surface.

## What Is Stored (Default DB)

Compact DB writes:

- `songs` (best base/FG scalar scores)
- `team_buff_loadouts` (base leaderboard) for the baseline tier only
- `team_buff_fg_loadouts` (FG leaderboard) for the baseline tier only

Derived tier rows (`NONE/T1/T10/T20/T50/T51`) are never persisted. They are recomputed on demand.

## How To Recompute Tier Leaderboards

The maintained interface is the Python API:

If you want to integrate this into an exporter/backend:

```python
from gear_optimizer.core.config import load_config
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.database import get_best_loadouts
from gear_optimizer.helpers.song_helpers.team_buff_tiers import compute_team_buff_tier_leaderboards
from gear_optimizer.data.song_io import clone_calc_song, get_base_calc_song

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
    tiers=("NONE", "T1", "T5", "T10", "T20", "T50", "T51"),
    target_team_color_override=None,  # or "Rush" / "Flow" / etc
)
```

The result shape is:

- `payload["tiers"][tier]["base_top51"]`: list of rows ranked by base `score`
- `payload["tiers"][tier]["fg_top51"]`: list of rows ranked by `fg_score`
- `payload["meta"]`: resolved TeamBuff/TeamColor context

## Note

This repo intentionally avoids persisting derived tiers to keep DB size and per-song CPU cost low.
There is no separate tier-recompute CLI; operators and website code use the same Python owner shown above.

## Timing Replay

On-demand recomputation uses the same chart timing and timing-envelope/frontier
semantics as the optimizer. Persisted DB rows are not a source of sampled timing
state.
