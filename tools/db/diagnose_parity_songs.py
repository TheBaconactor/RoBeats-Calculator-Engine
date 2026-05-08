"""
Diagnose parity regression: dump raw rows for failing songs from both DBs side-by-side.
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import (
    _unpack_stats_after_load,
    _force_payload_base_score,
    _base_details_from_force_payload,
)
from gear_optimizer.data.migrations import _table_exists
from gear_optimizer.helpers.song_helpers.fg_config import extract_fg_config, has_valid_fg_config
from gear_optimizer.helpers.song_helpers.force_greats.entry_resolution import entry_base_score, entry_fg_score


CATEGORY_A_MISSING_FG = [
    "00 (Hard) by garlagan",
    "00 by garlagan",
    "-feeding- (Hard) by naruto2413 (feat. Aya Majiro)",
    "-feeding- by naruto2413 (feat. Aya Majiro)",
    "1xmiss (Hard) by Camellia",
    "1xmiss by Camellia",
]

CATEGORY_B_BASE_REGRESSIONS = [
    "(The) Red * Room (Easy) by Camellia",
    "(The) Red * Room (Hard) by Camellia",
    "9876734123 (Hard) by Silentroom",
    "9876734123 by Silentroom",
    "ANASTASiA (Hard) by BlackY",
    "ANASTASiA by BlackY",
    "Alice in Misanthrope (Hard) by LeaF (7eaF)",
    "All I Want (Hard) by nanobii",
]

CATEGORY_C_FG_DRIFT = [
    "Adopt Me by BSlick",
    "Aether by Geoxor",
    "Meant To Be (Easy) by Slynk",
]


def dump_song(conn, song_name: str, label: str):
    print(f"\n{'='*80}")
    print(f"  {label}: {song_name}")
    print(f"{'='*80}")

    # Base table
    if _table_exists(conn, "team_buff_loadouts"):
        rows = conn.execute(
            """
            SELECT loadout_hash, score, fg_score, details_json, force_details_json
            FROM team_buff_loadouts
            WHERE song_name=? AND team_buff='T5'
            ORDER BY score DESC
            LIMIT 10
            """,
            (song_name,),
        ).fetchall()
        print(f"\n  --- team_buff_loadouts ({len(rows)} rows) ---")
        for r in rows:
            h = str(r[0] or "")
            s = int(r[1] or 0)
            fg = int(r[2] or 0)
            details = json.loads(r[3]) if r[3] else {}
            details = _unpack_stats_after_load(details) if isinstance(details, dict) else {}
            force_raw = json.loads(r[4]) if r[4] else None
            force_cfg = extract_fg_config(force_raw)
            has_fg_cfg = has_valid_fg_config(force_raw)
            force_base = _force_payload_base_score(force_raw) if force_raw else 0
            print(f"    hash={h[:16]}... score={s} fg={fg} force_cfg={bool(force_cfg)} valid_fg={has_fg_cfg} force_base={force_base}")

    # FG table
    if _table_exists(conn, "team_buff_fg_loadouts"):
        rows = conn.execute(
            """
            SELECT loadout_hash, score, fg_score, details_json, force_details_json
            FROM team_buff_fg_loadouts
            WHERE song_name=? AND team_buff='T5'
            ORDER BY fg_score DESC
            LIMIT 10
            """,
            (song_name,),
        ).fetchall()
        print(f"\n  --- team_buff_fg_loadouts ({len(rows)} rows) ---")
        for r in rows:
            h = str(r[0] or "")
            s = int(r[1] or 0)
            fg = int(r[2] or 0)
            details = json.loads(r[3]) if r[3] else {}
            details = _unpack_stats_after_load(details) if isinstance(details, dict) else {}
            force_raw = json.loads(r[4]) if r[4] else None
            force_cfg = extract_fg_config(force_raw)
            fg_valid = has_valid_fg_config(force_raw)
            force_base = _force_payload_base_score(force_raw) if force_raw else 0
            print(f"    hash={h[:16]}... score={s} fg={fg} force_cfg={bool(force_cfg)} valid_fg={fg_valid} force_base={force_base}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current", default=str(PROJECT_ROOT / "evolution.db"))
    p.add_argument("--legacy", default=str(PROJECT_ROOT / "evolutionref5.db"))
    p.add_argument("--category", choices=["A", "B", "C", "all"], default="all")
    args = p.parse_args()

    cur_db = Path(args.current)
    leg_db = Path(args.legacy)

    if not cur_db.exists():
        raise SystemExit(f"Current DB not found: {cur_db}")
    if not leg_db.exists():
        raise SystemExit(f"Legacy DB not found: {leg_db}")

    cur = sqlite3.connect(str(cur_db))
    leg = sqlite3.connect(str(leg_db))

    try:
        songs = []
        if args.category in ("A", "all"):
            songs.extend(CATEGORY_A_MISSING_FG)
        if args.category in ("B", "all"):
            songs.extend(CATEGORY_B_BASE_REGRESSIONS)
        if args.category in ("C", "all"):
            songs.extend(CATEGORY_C_FG_DRIFT)

        for song in songs:
            dump_song(cur, song, "CURRENT")
            dump_song(leg, song, "LEGACY")
    finally:
        cur.close()
        leg.close()


if __name__ == "__main__":
    raise SystemExit(main())
