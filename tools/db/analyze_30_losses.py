"""Deep dive into the 30 losing shared-FG songs."""
import sqlite3, json, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import _unpack_stats_after_load, _force_payload_base_score
from gear_optimizer.data.migrations import _table_exists
from gear_optimizer.helpers.song_helpers.fg_config import extract_fg_config, has_valid_fg_config

team_buff = "T5"

cur = sqlite3.connect(str(PROJECT_ROOT / "evolution.db"))
cur.row_factory = sqlite3.Row
leg = sqlite3.connect(str(PROJECT_ROOT / "evolutionref5.db"))
leg.row_factory = sqlite3.Row

LOSING_SONGS = [
    "All You Gotta Do (Is Just Dance) (Easy) by The Just Dance Band [Just Dance]",
    "Alteregoism (Easy) by Laur [LAUR1200]",
    "Armageddon (Easy) by LeaF (7eaF)",
    "Asteroid's Dream (Easy) by brz1128",
    "Attractor Dimension (Easy) by Laur [LAUR1200]",
    "Back Out (Easy) by RiraN",
    "Beautiful Memories (Easy) by HyuN",
    "Blue Zenith (Easy) by xi (xi_com_giko_31)",
    "Calamity Fortune (Easy) by LeaF (7eaF)",
    "Collapsar (Easy) by BlackY",
    "Comfort Zone (Easy) by KepoWorld",
    "DEAD (Easy) by Geoxor & SVRGE",
    "Dad Battle (Easy) by Kawai Sprite",
    "Dark Desire of Ark Six (Easy) by Se-U-Ra",
    "Eternal Ending (Easy) by Kobaryo",
    "Exosphere (Easy) by Creo",
    "FREEDOM DiVE (Easy) by xi (xi_com_giko_31)",
    "Find Myself (Easy) by Tobu, Bonalt & Hadi feat. Tom Martensson",
    "Full Restore (Easy) by Kagi",
    "GoodLove (Easy) by Maliboux",
    "Gravity (Easy) by Jonathan Eiter",
    "Hit That (Easy) by James Landino",
    "I don't care about Christmas though  (Easy) by Camellia feat. Nanahira",
    "Ice Angel (Easy) by Yooh",
    "If We Never (Easy) by Aiobahn & Vin [Monstercat]",
    "In My Heart (Easy) by Silentroom",
    "Inside (Easy) by Slynk",
    "Insight (Easy) by Haywyre",
    "galvanical onEshot (Easy) by seatrus",
]

def _best_base(conn, song, tb):
    if not _table_exists(conn, "team_buff_loadouts"):
        return None
    row = conn.execute(
        "SELECT loadout_hash, score, fg_score, details_json, force_details_json FROM team_buff_loadouts "
        "WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=? ORDER BY score DESC LIMIT 1",
        (song, tb),
    ).fetchone()
    return row

def _best_fg(conn, song, tb):
    if not _table_exists(conn, "team_buff_fg_loadouts"):
        return None
    row = conn.execute(
        "SELECT loadout_hash, score, fg_score, details_json, force_details_json FROM team_buff_fg_loadouts "
        "WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=? ORDER BY fg_score DESC LIMIT 1",
        (song, tb),
    ).fetchone()
    return row

base_regressions = []
fg_drift = []

for song in LOSING_SONGS:
    c_base = _best_base(cur, song, team_buff)
    l_base = _best_base(leg, song, team_buff)
    c_fg = _best_fg(cur, song, team_buff)
    l_fg = _best_fg(leg, song, team_buff)

    c_base_score = int(c_base["score"] or 0) if c_base else 0
    l_base_score = int(l_base["score"] or 0) if l_base else 0
    c_fg_score = int(c_fg["fg_score"] or 0) if c_fg else 0
    l_fg_score = int(l_fg["fg_score"] or 0) if l_fg else 0

    c_overall = max(c_base_score, c_fg_score)
    l_overall = max(l_base_score, l_fg_score)

    base_delta = c_base_score - l_base_score
    fg_delta = c_fg_score - l_fg_score

    label = f"base_d={base_delta:>+8} fg_d={fg_delta:>+8}"
    
    if base_delta < 0 and fg_delta == 0:
        # Pure base regression
        c_hash = str(c_base["loadout_hash"] or "")[:16] if c_base else "?"
        l_hash = str(l_base["loadout_hash"] or "")[:16] if l_base else "?"
        same_gear = c_hash == l_hash
        base_regressions.append((song, base_delta, c_base_score, l_base_score, same_gear, c_hash, l_hash))
        label += f" [BASE REGRESSION] cur_hash={c_hash} leg_hash={l_hash} same={same_gear}"
    elif abs(fg_delta) > 0:
        c_hash = str(c_fg["loadout_hash"] or "")[:16] if c_fg else "?"
        l_hash = str(l_fg["loadout_hash"] or "")[:16] if l_fg else "?"
        same_gear = c_hash == l_hash
        fg_drift.append((song, fg_delta, c_fg_score, l_fg_score, same_gear, c_hash, l_hash, base_delta))
        label += f" [FG DRIFT] cur_hash={c_hash} leg_hash={l_hash} same={same_gear}"
    else:
        label += f" [MIXED]"

    print(label)

print(f"\n--- Summary ---")
print(f"Base regressions (different gear): {len([r for r in base_regressions if not r[4]])}")
print(f"Base regressions (same gear): {len([r for r in base_regressions if r[4]])}")
print(f"FG drift: {len(fg_drift)}")

print("\n--- Base Regressions (different gear) ---")
for s, d, cs, ls, same, ch, lh in base_regressions:
    if not same:
        print(f"  {d:>+8}  {s[:70]}  cur_hash={ch} leg_hash={lh}  cur={cs} leg={ls}")

print("\n--- FG Drift ---")
for s, d, cs, ls, same, ch, lh, bd in fg_drift:
    print(f"  {d:>+8}  {s[:70]}  cur_hash={ch} leg_hash={lh}  same={same}  cur={cs} leg={ls}  base_d={bd}")

cur.close()
leg.close()
