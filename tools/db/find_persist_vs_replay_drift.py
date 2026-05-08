"""Find songs where persisted score != replayed score for the SAME loadout."""
import sqlite3, json, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import _unpack_stats_after_load
from gear_optimizer.data.migrations import _table_exists
from gear_optimizer.pipeline.song_processor import get_base_calc_song
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

team_buff = "T5"
eps = 0

cur = sqlite3.connect(str(PROJECT_ROOT / "evolution.db"))
cur.row_factory = sqlite3.Row

# Build calc_song cache
difficulty_index = {}
from gear_optimizer.data.db_manager import _build_song_index_for_difficulty
for diff in ("Easy", "Normal", "Hard"):
    difficulty_index[diff] = _build_song_index_for_difficulty(diff)

def _infer_difficulty(song_name):
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in song_name:
            return diff
    return "Normal"

def _song_file(song_name):
    diff = _infer_difficulty(song_name)
    fp = PROJECT_ROOT / "Data" / diff / f"{song_name}.txt"
    if fp.exists():
        return str(fp)
    idx = difficulty_index.get(diff, {})
    fp = Path(str(idx.get(song_name) or ""))
    if fp.exists():
        return str(fp)
    return None

calc_song_cache = {}
def _get_calc_song(song_name):
    if song_name in calc_song_cache:
        return calc_song_cache[song_name]
    fp = _song_file(song_name)
    if fp is None:
        calc_song_cache[song_name] = None
        return None
    calc_song = get_base_calc_song(fp, {})
    calc_song_cache[song_name] = calc_song
    return calc_song

# Get ref_arrays
from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
ref_arrays = _get_team_buff_ref_arrays_cached()

drift_count = 0
no_stats = 0
no_calc_song = 0
same_delta = 0

print(f"{'SONG':<65} {'PERSIST':>10} {'REPLAY':>10} {'DELTA':>8}  HASH")
print("-" * 120)

if not _table_exists(cur, "team_buff_loadouts"):
    raise SystemExit("No team_buff_loadouts table")

rows = cur.execute(
    "SELECT song_name, loadout_hash, score, details_json FROM team_buff_loadouts "
    "WHERE team_buff=? ORDER BY song_name, score DESC",
    (team_buff,),
).fetchall()

for r in rows:
    song = str(r["song_name"])
    h = str(r["loadout_hash"] or "")[:16]
    persisted = int(r["score"] or 0)
    details_json = r["details_json"]

    if not details_json:
        no_stats += 1
        continue

    try:
        details = json.loads(details_json)
    except Exception:
        no_stats += 1
        continue

    details = _unpack_stats_after_load(details)
    stats = details.get("Stats") if isinstance(details, dict) else None
    if not isinstance(stats, dict) or not stats:
        no_stats += 1
        continue

    calc_song = _get_calc_song(song)
    if calc_song is None:
        no_calc_song += 1
        continue

    try:
        replayed = int(score_stats_exact(stats, calc_song, ref_arrays))
    except Exception:
        continue

    delta = replayed - persisted
    if abs(delta) <= eps:
        same_delta += 1
    else:
        drift_count += 1
        print(f"{song:<65} {persisted:>10} {replayed:>10} {delta:>+8}  {h}")

print(f"\ndrift: {drift_count}  same: {same_delta}  no_stats: {no_stats}  no_calc_song: {no_calc_song}")
cur.close()
