"""Precise trace: compare exact replay inputs vs what the optimizer actually scored."""
import json, sqlite3, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import _unpack_stats_after_load
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact
from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.data.db_manager import _build_song_index_for_difficulty
from gear_optimizer.core.team_buff import team_buff_effect
from gear_optimizer.solver.scoring.stats_ops import apply_gems_to_base_stats
from gear_optimizer.core.utils import safe_int

ref = _get_team_buff_ref_arrays_cached()
diff_idx = {d: _build_song_index_for_difficulty(d) for d in ("Easy", "Normal", "Hard")}

def get_fp(name):
    for d in ("Easy", "Normal", "Hard"):
        if f" ({d}) " in name:
            fp = PROJECT_ROOT / "Data" / d / f"{name}.txt"
            if fp.exists():
                return str(fp)
            return str(Path(str(diff_idx[d].get(name) or "")))
    return None

cur = sqlite3.connect(str(PROJECT_ROOT / "evolution.db"))
cur.row_factory = sqlite3.Row

# Find one song with large drift and dump EVERYTHING
rows = cur.execute(
    "SELECT song_name, loadout_hash, score, fg_score, details_json "
    "FROM team_buff_loadouts WHERE team_buff='T5' AND details_json IS NOT NULL "
    "ORDER BY random() LIMIT 50"
).fetchall()

calc_cache = {}
for r in rows:
    details_raw = _unpack_stats_after_load(json.loads(r["details_json"]))
    stats = details_raw.get("Stats")
    if not isinstance(stats, dict):
        continue
    fp = get_fp(r["song_name"])
    if not fp:
        continue
    if r["song_name"] not in calc_cache:
        calc_cache[r["song_name"]] = get_base_calc_song(fp, {})
    calc = calc_cache[r["song_name"]]
    per = int(r["score"])
    rp = int(score_stats_exact(stats, calc, ref))
    delta = per - rp
    if abs(delta) > 500:
        # Dump full comparison
        gems = details_raw.get("GemCounts") or {}
        if isinstance(gems, list):
            from gear_optimizer.core.gem_defs import GEM_KEYS
            gm = {}
            for i, k in enumerate(GEM_KEYS):
                if i < len(gems): gm[k] = int(gems[i] or 0)
            gems = gm
        ft_d = safe_int(details_raw.get("FT", 0), 0)
        ff_d = safe_int(details_raw.get("FF", 0), 0)
        primary = details_raw.get("PrimaryColor") or details_raw.get("Primary Color") or ""
        secondary = details_raw.get("SecondaryColor") or details_raw.get("Secondary Color") or ""
        sel = details_raw.get("SelectedElement") or details_raw.get("Selected Element") or primary

        # What does the replay scorer compute as base_value?
        pp_factor_replay = _lookup_ref_py(int(stats.get("Perfect Points", 0)), ref["Perfect Points"])
        combo_replay = _lookup_ref_py(int(stats.get("Combo Multiplier", 0)), ref["Combo Multiplier"])
        fever_replay = _lookup_ref_py(int(stats.get("Fever Multiplier", 0)), ref["Fever Multiplier"])
        ft_replay = _lookup_ref_py(int(stats.get("Fever Time", 0)), ref["Fever Time"])
        ff_replay = _lookup_ref_py(int(stats.get("Fever Fill Rate", 0)), ref["Fever Fill Rate"])
        prim_val = int(stats.get(primary, 0) or 0)
        sec_val = int(stats.get(secondary, 0) or 0)
        base_val_replay = float((prim_val * 2) + sec_val) + float(pp_factor_replay)

        print(f"\n=== {r['song_name'][:55]} ===")
        print(f"  Persisted: {per}  Replay: {rp}  Delta: {delta}")
        print(f"  Stats: PP={stats.get('Perfect Points')} CM={stats.get('Combo Multiplier')} FM={stats.get('Fever Multiplier')} FT={stats.get('Fever Time')} FF={stats.get('Fever Fill Rate')}")
        print(f"  Primary={primary}={prim_val} Secondary={secondary}={sec_val} Sel={sel}")
        print(f"  Replay factors: PP={pp_factor_replay:.2f} combo={combo_replay:.2f} fever={fever_replay:.2f} ft={ft_replay:.2f} ff={ff_replay:.2f}")
        print(f"  Replay base_value: {base_val_replay:.2f}")
        print(f"  Details: FT_gems={ft_d} FF_gems={ff_d}")
        print(f"  Gems: {gems}")
        print(f"  FG_score cached: {r['fg_score']}")

        # Now let's check: does applying gems to the Stats produce the same Stats?
        # If Stats already include gems, we should NOT re-apply them
        # The exact rescorer reads Stats directly and doesn't apply any gems
        # So if Stats already includes full gem application, the replay should work

        # Check if the Stats already include the FT/FF gem effects
        # by comparing ff in Stats vs what base+buff+gem would be
        buff = team_buff_effect("T5", sel or primary or "")
        print(f"  Buff: {buff}")

        # Only trace one
        break

cur.close()
