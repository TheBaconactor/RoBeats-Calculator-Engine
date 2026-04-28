"""Check if recent FG rows have details.Stats matching force_details.BaseStats + GemCounts."""
import sqlite3, json, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import _unpack_stats_after_load

conn = sqlite3.connect(str(PROJECT_ROOT / "evolution.db"))
conn.row_factory = sqlite3.Row

rows = conn.execute(
    "SELECT song_name, details_json, force_details_json, timestamp "
    "FROM team_buff_fg_loadouts ORDER BY timestamp DESC LIMIT 20"
).fetchall()

ok = 0
bad = 0
for r in rows:
    details = json.loads(r["details_json"]) if r["details_json"] else None
    fd = json.loads(r["force_details_json"]) if r["force_details_json"] else None
    if not details or not fd:
        continue
    details = _unpack_stats_after_load(details) if isinstance(details, dict) else details
    stats = (details or {}).get("Stats", {}) or {}
    base = (fd or {}).get("BaseStats", {}) or {}
    gems = (fd or {}).get("GemCounts", {}) or {}
    ft_g = int(fd.get("FT", 0) or 0)
    ff_g = int(fd.get("FF", 0) or 0)

    pp_ok = int(base.get("Perfect Points",0) or 0) + int(gems.get("Perfect Points",0) or 0) == int(stats.get("Perfect Points",0) or 0)
    cm_ok = int(base.get("Combo Multiplier",0) or 0) + int(gems.get("Combo Multiplier",0) or 0) == int(stats.get("Combo Multiplier",0) or 0)
    fm_ok = int(base.get("Fever Multiplier",0) or 0) + int(gems.get("Fever Multiplier",0) or 0) == int(stats.get("Fever Multiplier",0) or 0)
    ft_ok = int(base.get("Fever Time",0) or 0) + int(ft_g) == int(stats.get("Fever Time",0) or 0)
    ff_ok = int(base.get("Fever Fill Rate",0) or 0) + int(ff_g) == int(stats.get("Fever Fill Rate",0) or 0)

    if pp_ok and cm_ok and fm_ok and ft_ok and ff_ok:
        ok += 1
    else:
        bad += 1

print(f"Clean (all 5 gem stats match): {ok}")
print(f"Stale (at least one mismatch):  {bad}")
print(f"Total: {ok + bad}")
conn.close()
