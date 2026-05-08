"""Pinpoint the exact cause of persist-vs-replay drift on specified DB."""
import sqlite3, json, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import _unpack_stats_after_load
from gear_optimizer.data.migrations import _table_exists
from gear_optimizer.pipeline.song_processor import get_base_calc_song
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact
from gear_optimizer.data.db_manager import _build_song_index_for_difficulty
from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached

DB_PATH = PROJECT_ROOT / "evolutionref5.db"
TEAM_BUFF = "T5"
TOP_N = 20

difficulty_index = {}
for diff in ("Easy", "Normal", "Hard"):
    difficulty_index[diff] = _build_song_index_for_difficulty(diff)

def infer_diff(song_name):
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in song_name:
            return diff
    return "Normal"

def song_file(song_name):
    diff = infer_diff(song_name)
    fp = PROJECT_ROOT / "Data" / diff / f"{song_name}.txt"
    if fp.exists():
        return str(fp)
    idx = difficulty_index.get(diff, {})
    fp = Path(str(idx.get(song_name) or ""))
    if fp.exists():
        return str(fp)
    return None

calc_song_cache = {}
def get_cs(song_name):
    if song_name in calc_song_cache:
        return calc_song_cache[song_name]
    fp = song_file(song_name)
    if fp is None:
        calc_song_cache[song_name] = None
        return None
    cs = get_base_calc_song(fp, {})
    calc_song_cache[song_name] = cs
    return cs

ref_arrays = _get_team_buff_ref_arrays_cached()

conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

print(f"DB: {DB_PATH}")

rows = conn.execute(
    "SELECT song_name, loadout_hash, score, fg_score, details_json, force_details_json "
    "FROM team_buff_loadouts WHERE team_buff=? ORDER BY song_name, score DESC",
    (TEAM_BUFF,),
).fetchall()

total = len(rows)
print(f"Total T5 rows: {total:,}")

drift_count = 0
no_stats = 0
same_count = 0

drifter_details = []

for r in rows:
    song = str(r["song_name"])
    h = str(r["loadout_hash"] or "")[:32]
    persisted = int(r["score"] or 0)
    fg_score = int(r["fg_score"] or 0)
    details_json = r["details_json"]
    force_json = r["force_details_json"]

    if not details_json:
        no_stats += 1
        continue

    try:
        details = json.loads(details_json)
    except Exception:
        no_stats += 1
        continue

    details = _unpack_stats_after_load(details) if isinstance(details, dict) else {}
    stats = details.get("Stats") if isinstance(details, dict) else None

    if not isinstance(stats, dict) or not stats:
        no_stats += 1
        continue

    cs = get_cs(song)
    if cs is None:
        continue

    try:
        replayed = int(score_stats_exact(stats, cs, ref_arrays))
    except Exception:
        continue

    delta = replayed - persisted
    if abs(delta) <= 0:
        same_count += 1
    else:
        drift_count += 1
        drifter_details.append({
            "song": song,
            "hash": h,
            "persisted": persisted,
            "replayed": replayed,
            "delta": delta,
            "fg_score": fg_score,
            "has_force": bool(force_json),
            "details_keys": sorted(details.keys()) if isinstance(details, dict) else [],
            "stats_keys": sorted(stats.keys()) if isinstance(stats, dict) else [],
        })

print(f"drift: {drift_count}  same: {same_count}  no_stats: {no_stats}")

if drifter_details:
    print(f"\n--- Top {TOP_N} drifters ---")
    for d in drifter_details[:TOP_N]:
        print(f"\n  {d['song']}")
        print(f"    hash: {d['hash']}")
        print(f"    persisted: {d['persisted']:,}  replay: {d['replayed']:,}  delta: {d['delta']:+,}")
        print(f"    fg_score: {d['fg_score']:,}  has_force: {d['has_force']}")
        print(f"    details_keys: {d['details_keys']}")
        print(f"    stats_keys: {d['stats_keys']}")

conn.close()
