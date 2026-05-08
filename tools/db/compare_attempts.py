"""Compare attempt counts for the 30 losing songs between current and legacy DBs."""
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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

cur = sqlite3.connect(str(PROJECT_ROOT / "evolution.db"))
cur.row_factory = sqlite3.Row
leg = sqlite3.connect(str(PROJECT_ROOT / "evolutionref5.db"))
leg.row_factory = sqlite3.Row

print(f"{'SONG':<70} {'CUR_ATT':>8} {'LEG_ATT':>8} {'CUR_BASE':>10} {'LEG_BASE':>10} {'BASE_D':>8}")
print("-" * 120)

for song in LOSING_SONGS:
    # Current DB
    cr = cur.execute(
        "SELECT attempt_lifetime, best_score, best_fg_score FROM songs WHERE name=?", (song,)
    ).fetchone()
    # Legacy DB
    lr = leg.execute(
        "SELECT attempt_lifetime, best_score, best_fg_score FROM songs WHERE name=?", (song,)
    ).fetchone()

    c_att = int(cr["attempt_lifetime"]) if cr else 0
    l_att = int(lr["attempt_lifetime"]) if lr else 0
    c_base = int(cr["best_score"]) if cr else 0
    l_base = int(lr["best_score"]) if lr else 0
    c_fg = int(cr["best_fg_score"]) if cr else 0
    l_fg = int(lr["best_fg_score"]) if lr else 0

    bdelta = c_base - l_base
    marker = ""
    if c_att < l_att:
        marker = " <-- fewer attempts"

    print(f"{song:<70} {c_att:>8} {l_att:>8} {c_base:>10} {l_base:>10} {bdelta:>+8}{marker}")

# Summary
cur_att_vals = []
leg_att_vals = []
for song in LOSING_SONGS:
    cr = cur.execute("SELECT attempt_lifetime FROM songs WHERE name=?", (song,)).fetchone()
    lr = leg.execute("SELECT attempt_lifetime FROM songs WHERE name=?", (song,)).fetchone()
    if cr: cur_att_vals.append(int(cr["attempt_lifetime"]))
    if lr: leg_att_vals.append(int(lr["attempt_lifetime"]))

print(f"\n--- Summary ---")
print(f"Current mean attempts: {sum(cur_att_vals)/len(cur_att_vals):.1f}")
print(f"Legacy mean attempts:  {sum(leg_att_vals)/len(leg_att_vals):.1f}")
print(f"Current total: {sum(cur_att_vals)}")
print(f"Legacy total:  {sum(leg_att_vals)}")

cur.close()
leg.close()
