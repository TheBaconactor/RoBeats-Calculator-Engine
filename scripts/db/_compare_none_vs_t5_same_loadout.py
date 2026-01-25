"""Compare SAME loadout saved under NONE vs T5 team buff.

This answers: should PP(T5) = PP(NONE) + 25 ?
Only valid if the rows share the same (song_name, loadout_hash).
"""

import json
import sqlite3

conn = sqlite3.connect("evolution.db")
conn.row_factory = sqlite3.Row

row = conn.execute(
    """
    WITH both AS (
      SELECT song_name, loadout_hash
      FROM team_buff_loadouts
      WHERE team_buff IN ('NONE', 'T5')
      GROUP BY song_name, loadout_hash
      HAVING COUNT(DISTINCT team_buff) = 2
    )
    SELECT song_name, loadout_hash
    FROM both
    LIMIT 1;
    """
).fetchone()

if not row:
    print("NO_SHARED_LOADOUT_HASH_FOUND")
    raise SystemExit(0)

song = row["song_name"]
loadout_hash = row["loadout_hash"]
print("Song:", song)
print("LoadoutHash:", loadout_hash)

rows = conn.execute(
    """
    SELECT team_buff, score, details_json
    FROM team_buff_loadouts
    WHERE song_name = ? AND loadout_hash = ? AND team_buff IN ('NONE', 'T5')
    ORDER BY team_buff;
    """,
    (song, loadout_hash),
).fetchall()

by = {}
for r in rows:
    details = json.loads(r["details_json"]) if r["details_json"] else {}
    stats = details.get("Stats") or {}
    by[r["team_buff"]] = {
        "score": int(r["score"] or 0),
        "pp": int(stats.get("Perfect Points") or 0),
        "chill": int(stats.get("Chill") or 0),
        "flow": int(stats.get("Flow") or 0),
        "rush": int(stats.get("Rush") or 0),
        "beat": int(stats.get("Beat") or 0),
        "vibe": int(stats.get("Vibe") or 0),
    }

print("NONE:", by.get("NONE"))
print("T5  :", by.get("T5"))

if "NONE" in by and "T5" in by:
    print("ΔPP:", by["T5"]["pp"] - by["NONE"]["pp"])
    deltas = {k: by["T5"][k] - by["NONE"][k] for k in ["chill", "flow", "rush", "beat", "vibe"]}
    print("ΔElements:", deltas)

conn.close()
