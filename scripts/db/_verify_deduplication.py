import sqlite3

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

db_path = get_evolution_db_path()
conn = get_db_connection(db_path)
conn.row_factory = sqlite3.Row

# Count entries per tier in the canonical FG leaderboard table.
rows = conn.execute(
    "SELECT UPPER(COALESCE(team_buff, 'UNKNOWN')) AS team_buff, COUNT(*) AS c "
    "FROM team_buff_fg_loadouts "
    "GROUP BY UPPER(COALESCE(team_buff, 'UNKNOWN')) "
    "ORDER BY team_buff"
).fetchall()

print("FG tier counts (team_buff_fg_loadouts):")
total = 0
for r in rows:
    tier = str(r["team_buff"] or "UNKNOWN")
    c = int(r["c"] or 0)
    total += c
    print(f"  {tier:7s}: {c:,} entries")

print(f"\nTotal: {total:,} entries")

conn.close()
