"""Check parity for shared-FG songs in the fresh run DB."""
import sqlite3, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.migrations import _table_exists

team_buff = "T5"

cur = sqlite3.connect(str(PROJECT_ROOT / "evolution.db"))
leg = sqlite3.connect(str(PROJECT_ROOT / "evolutionref5.db"))

cur_fg_songs = set()
for row in cur.execute(
    "SELECT DISTINCT song_name FROM team_buff_fg_loadouts WHERE UPPER(COALESCE(team_buff,''))=?",
    (team_buff,),
):
    cur_fg_songs.add(str(row[0]))

leg_fg_songs = set()
for row in leg.execute(
    "SELECT DISTINCT song_name FROM team_buff_fg_loadouts WHERE UPPER(COALESCE(team_buff,''))=?",
    (team_buff,),
):
    leg_fg_songs.add(str(row[0]))

shared = sorted(cur_fg_songs & leg_fg_songs)
cur_only_fg = sorted(cur_fg_songs - leg_fg_songs)
leg_only_fg = sorted(leg_fg_songs - cur_fg_songs)

print(f"Shared FG songs: {len(shared)}")
print(f"Current-only FG: {len(cur_only_fg)}")
print(f"Legacy-only FG: {len(leg_only_fg)}")

# Best helpers
def _best_base(conn, song, tb):
    if not _table_exists(conn, "team_buff_loadouts"):
        return (0, "")
    row = conn.execute(
        "SELECT score, loadout_hash FROM team_buff_loadouts "
        "WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=? "
        "ORDER BY score DESC LIMIT 1",
        (song, tb),
    ).fetchone()
    if row is None:
        return (0, "")
    return (int(row[0] or 0), str(row[1] or "").strip())

def _best_fg(conn, song, tb):
    if not _table_exists(conn, "team_buff_fg_loadouts"):
        return (0, "")
    row = conn.execute(
        "SELECT fg_score, loadout_hash FROM team_buff_fg_loadouts "
        "WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=? "
        "ORDER BY fg_score DESC LIMIT 1",
        (song, tb),
    ).fetchone()
    if row is None:
        return (0, "")
    return (int(row[0] or 0), str(row[1] or "").strip())

# Compare shared FG songs
wins = ties = losses = 0
base_wins = base_ties = base_losses = 0
details = []

for song in shared:
    c_base_score, c_base_hash = _best_base(cur, song, team_buff)
    c_fg_score, c_fg_hash = _best_fg(cur, song, team_buff)
    l_base_score, l_base_hash = _best_base(leg, song, team_buff)
    l_fg_score, l_fg_hash = _best_fg(leg, song, team_buff)

    c_overall = max(c_base_score, c_fg_score)
    l_overall = max(l_base_score, l_fg_score)
    delta = c_overall - l_overall

    c_src = "fg" if c_fg_score > c_base_score else "base"
    l_src = "fg" if l_fg_score > l_base_score else "base"

    if delta > 0:
        wins += 1
        details.append(f"  WIN  +{delta:>10}  {song}  cur={c_overall} ({c_src})  leg={l_overall} ({l_src})")
    elif delta < 0:
        losses += 1
        details.append(f"  LOSE {delta:>11}  {song}  cur={c_overall} ({c_src})  leg={l_overall} ({l_src})")
    else:
        ties += 1
        details.append(f"  TIE  {delta:>11}  {song}  cur={c_overall} ({c_src})  leg={l_overall} ({l_src})")

    if c_base_score > l_base_score:
        base_wins += 1
    elif c_base_score < l_base_score:
        base_losses += 1
    else:
        base_ties += 1

print(f"\nAmong {len(shared)} shared-FG songs:")
print(f"  Overall: wins={wins} ties={ties} losses={losses}")
print(f"  Base:    wins={base_wins} ties={base_ties} losses={base_losses}")

print("\n--- Per-song ---")
for d in details:
    print(d)

cur.close()
leg.close()
