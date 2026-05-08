"""Check replay fidelity: only rows written AFTER the recompute fix."""
import json, sqlite3, sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import _unpack_stats_after_load
from gear_optimizer.pipeline.song_processor import get_base_calc_song
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact
from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.data.db_manager import _build_song_index_for_difficulty

ref = _get_team_buff_ref_arrays_cached()
diff_idx = {d: _build_song_index_for_difficulty(d) for d in ("Easy", "Normal", "Hard")}
calc_cache = {}

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

# Fix landed at ~21:50 UTC-5. Use timestamp cutoff.
# The fix commit was pushed at ~21:45. Rows with timestamp after 21:45 should be clean.
CUTOFF = int(datetime(2026, 5, 7, 21, 50, 0).timestamp())

new_rows = cur.execute(
    "SELECT song_name, loadout_hash, score, details_json, timestamp "
    "FROM team_buff_loadouts WHERE team_buff='T5' AND details_json IS NOT NULL "
    "AND CAST(timestamp AS INTEGER) > ? ORDER BY timestamp DESC", (CUTOFF,)
).fetchall()

print(f"Rows written after fix: {len(new_rows)}")

match = 0
drift = 0
for r in new_rows:
    try:
        details = _unpack_stats_after_load(json.loads(r["details_json"]))
    except Exception:
        continue
    stats = details.get("Stats")
    if not stats:
        continue
    fp = get_fp(r["song_name"])
    if not fp:
        continue
    if r["song_name"] not in calc_cache:
        try:
            calc_cache[r["song_name"]] = get_base_calc_song(fp, {})
        except Exception:
            continue
    calc = calc_cache[r["song_name"]]
    per = int(r["score"])
    rp = int(score_stats_exact(stats, calc, ref))
    delta = per - rp
    if abs(delta) < 2:
        match += 1
    else:
        drift += 1
        if drift <= 5:
            print(f"DRIFT {delta:+6}  {r['song_name'][:55]}  per={per} rp={rp}")

# Also check some rows from BEFORE the fix for comparison
old_rows = cur.execute(
    "SELECT song_name, loadout_hash, score, details_json, timestamp "
    "FROM team_buff_loadouts WHERE team_buff='T5' AND details_json IS NOT NULL "
    "AND CAST(timestamp AS INTEGER) <= ? ORDER BY timestamp ASC LIMIT 50", (CUTOFF,)
).fetchall()

old_match = 0
old_drift = 0
for r in old_rows:
    try:
        details = _unpack_stats_after_load(json.loads(r["details_json"]))
    except Exception:
        continue
    stats = details.get("Stats")
    if not stats:
        continue
    fp = get_fp(r["song_name"])
    if not fp:
        continue
    if r["song_name"] not in calc_cache:
        try:
            calc_cache[r["song_name"]] = get_base_calc_song(fp, {})
        except Exception:
            continue
    calc = calc_cache[r["song_name"]]
    per = int(r["score"])
    rp = int(score_stats_exact(stats, calc, ref))
    delta = per - rp
    if abs(delta) < 2:
        old_match += 1
    else:
        old_drift += 1

print(f"\nAfter fix:  match={match}  drift={drift}  ({match+drift} total)")
print(f"Before fix: match={old_match}  drift={old_drift}  ({old_match+old_drift} total)")

cur.close()
