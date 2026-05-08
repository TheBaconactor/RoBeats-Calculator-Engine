"""
Precise trace: dump full force_details for key hashes from both DBs to find contract breaks.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.migrations import _table_exists

# Key songs where same hash produces different FG scores
TRACE_SONGS = [
    ("Adopt Me by BSlick", "3d515e0586a2922e940fbebf0484d029"),
    ("Aether by Geoxor", "ca8ee8673df0054c5e5ead38ce5ead16"),
    ("Meant To Be (Easy) by Slynk", "082b44da8feab3941bd5604d791dc0f6"),
    ("-feeding- (Hard) by naruto2413 (feat. Aya Majiro)", "5f27d20af8d15745cd847c55303dba9c"),
]

MISSING_FG_SONGS = [
    ("All I Want (Hard) by nanobii", "0f8a8de34bf9c638be2374616782c4bd"),
    ("00 (Hard) by garlagan", "731d290e0ec7e84a0b019324def221fd"),
]


def dump_force(song_name, loadout_hash, conn, label):
    print(f"\n{'='*80}")
    print(f"  {label}: {song_name} / {loadout_hash[:16]}...")
    print(f"{'='*80}")

    # Base row
    if _table_exists(conn, "team_buff_loadouts"):
        row = conn.execute(
            "SELECT score, fg_score, details_json FROM team_buff_loadouts "
            "WHERE song_name=? AND team_buff='T5' AND loadout_hash=?",
            (song_name, loadout_hash),
        ).fetchone()
        if row:
            details = json.loads(row[2]) if row[2] else {}
            stats = details.get("Stats") or details.get("st")
            ft = details.get("FT", "?")
            ff = details.get("FF", "?")
            sel = details.get("SelectedElement") or details.get("Selected Element") or "?"
            print(f"  BASE: score={row[0]} fg_score_cache={row[1]} FT={ft} FF={ff} sel={sel}")
            if isinstance(stats, dict):
                print(f"    Stats: PP={stats.get('Perfect Points')} CM={stats.get('Combo Multiplier')} "
                      f"FM={stats.get('Fever Multiplier')} FF_R={stats.get('Fever Fill Rate')} "
                      f"FT_R={stats.get('Fever Time')}")
        else:
            print(f"  BASE: NOT FOUND")

    # FG row
    if _table_exists(conn, "team_buff_fg_loadouts"):
        row = conn.execute(
            "SELECT score, fg_score, details_json, force_details_json FROM team_buff_fg_loadouts "
            "WHERE song_name=? AND team_buff='T5' AND loadout_hash=?",
            (song_name, loadout_hash),
        ).fetchone()
        if row:
            force = json.loads(row[3]) if row[3] else {}
            details = json.loads(row[2]) if row[2] else {}
            print(f"  FG: score={row[0]} fg_score={row[1]}")
            print(f"    Force: BaseScore={force.get('BaseScore')} Score={force.get('Score')} "
                  f"FT={force.get('FT')} FF={force.get('FF')}")
            gems = force.get("GemCounts", {})
            print(f"    Gems: PP={gems.get('Perfect Points')} CM={gems.get('Combo Multiplier')} "
                  f"FM={gems.get('Fever Multiplier')} Elem={gems.get('Element')}")
            fg_cfg = (force.get("ForceGreats") or {}).get("config") or {}
            print(f"    FG config: {json.dumps(fg_cfg)}")
            forced = force.get("forced_counts") or (force.get("ForceGreats") or {}).get("forced_counts")
            print(f"    Forced counts: {forced}")
            if isinstance(details, dict) and details.get("Stats"):
                stats = details["Stats"]
                print(f"    Details Stats: PP={stats.get('Perfect Points')} CM={stats.get('Combo Multiplier')} "
                      f"FM={stats.get('Fever Multiplier')} FF_R={stats.get('Fever Fill Rate')} "
                      f"FT_R={stats.get('Fever Time')}")
        else:
            print(f"  FG: NOT FOUND")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current", default=str(PROJECT_ROOT / "evolution.db"))
    p.add_argument("--legacy", default=str(PROJECT_ROOT / "evolutionref5.db"))
    args = p.parse_args()

    cur = sqlite3.connect(str(Path(args.current)))
    leg = sqlite3.connect(str(Path(args.legacy)))
    try:
        for song, h in TRACE_SONGS:
            dump_force(song, h, cur, "CURRENT")
            dump_force(song, h, leg, "LEGACY")

        print("\n\n### MISSING FG CATEGORY ###")
        for song, h in MISSING_FG_SONGS:
            dump_force(song, h, cur, "CURRENT")
            dump_force(song, h, leg, "LEGACY")
    finally:
        cur.close()
        leg.close()


if __name__ == "__main__":
    raise SystemExit(main())
