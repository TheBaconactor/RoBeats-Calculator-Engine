"""
Live leaderboard vs DB audit.
Compares robeats_top1_song_leaderboards.json against evolution.db to find
scores that beat our optimised database, flagging regressions where even
the strongest team-buff tier (T1) cannot explain the gap.

Usage:
    python -m tools run scripts:regression/lb_audit
    python -m tools run scripts:regression/lb_audit -- --csv
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("EVOLUTION_DB_PATH", REPO_ROOT / "evolution.db"))
LB_PATH = REPO_ROOT / "robeats_top1_song_leaderboards.json"

# T1 is the only tier stronger than our T5 baseline (+5 Elem).
# On element-matched charts this yields ~0.5-1.5 % extra score.
# Gaps beyond 2 % cannot credibly be explained by a tier bump alone.
PLAUSIBLE_PCT = 2.0
REGRESSIVE_PCT = 4.0


def load_lb() -> list[dict]:
    with open(LB_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["rows"]


def load_db_songs(db) -> dict[str, dict]:
    c = db.execute("SELECT name, best_score, best_fg_score FROM songs")
    return {r[0]: {"best_score": r[1], "best_fg_score": r[2] or 0} for r in c.fetchall()}


def build_db_key(row: dict) -> str:
    title = row["title"]
    artist = row["artist"]
    return f"{title} by {artist}"


def audit(db_rows: dict[str, dict], lb_rows: list[dict]) -> list[dict]:
    results = []
    matched = 0
    not_found = 0

    for row in lb_rows:
        key = build_db_key(row)
        db_entry = db_rows.get(key)

        if db_entry is None:
            not_found += 1
            results.append({
                "song_name": key,
                "player": row["playerName"],
                "live_score": row["bestScore"],
                "db_score": None,
                "db_fg_score": None,
                "naked_score": row.get("nakedScore", 0),
                "gear_power": row.get("gearPower", 0),
                "gap": None,
                "gap_pct": None,
                "status": "NO_DB_MATCH",
            })
            continue

        matched += 1
        live = row["bestScore"]
        db_score = db_entry["best_score"]
        db_fg_score = db_entry["best_fg_score"]
        db_best = max(db_score, db_fg_score)

        gap = live - db_best
        gap_pct = (gap / db_best * 100) if db_best > 0 else 0.0

        if live <= db_best:
            status = "OK"
        elif gap_pct < PLAUSIBLE_PCT:
            status = "PLAUSIBLE_T1"
        elif gap_pct < REGRESSIVE_PCT:
            status = "SUSPICIOUS"
        else:
            status = "REGRESSIVE"

        results.append({
            "song_name": key,
            "player": row["playerName"],
            "live_score": live,
            "db_score": db_score,
            "db_fg_score": db_fg_score,
            "naked_score": row.get("nakedScore", 0),
            "gear_power": row.get("gearPower", 0),
            "gap": gap,
            "gap_pct": round(gap_pct, 2),
            "status": status,
        })

    return results, matched, not_found


def print_report(results, matched, not_found):
    regressive = [r for r in results if r["status"] == "REGRESSIVE"]
    suspicious = [r for r in results if r["status"] == "SUSPICIOUS"]
    plausible = [r for r in results if r["status"] == "PLAUSIBLE_T1"]

    print("=" * 70)
    print("  LIVE LB vs DB AUDIT REPORT")
    print("=" * 70)
    print(f"  LB entries:       {len(results)}")
    print(f"  DB matches:       {matched}")
    print(f"  No DB match:      {not_found}")
    print(f"  DB ahead (OK):    {len([r for r in results if r['status'] == 'OK'])}")
    print(f"  Plausible T1:     {len(plausible)}  (gap < {PLAUSIBLE_PCT}%)")
    print(f"  Suspicious:       {len(suspicious)}  (gap {PLAUSIBLE_PCT}-{REGRESSIVE_PCT}%)")
    print(f"  REGRESSIVE:       {len(regressive)}  (gap > {REGRESSIVE_PCT}%)")
    print()

    if regressive:
        print("-" * 70)
        print("  REGRESSIVE -- even T1 cannot bridge the gap")
        print("-" * 70)
        regressive.sort(key=lambda r: -r["gap_pct"])
        for r in regressive:
            gp = r["gear_power"]
            ns = r["naked_score"]
            print(f"  {r['gap_pct']:>6.1f}%  {r['player']:<20s}  {r['song_name'][:60]}")
            print(f"          live={r['live_score']:>9}  db={r['db_score']:>9}  fg={r['db_fg_score']:>9}  gap={r['gap']:>+9}")
            print(f"          naked={ns:>9}  gearPwr={gp:>5}")
        print()

    if suspicious:
        print("-" * 70)
        print("  SUSPICIOUS -- gap exceeds plausible tier benefit")
        print("-" * 70)
        for r in suspicious:
            print(f"  {r['gap_pct']:>6.1f}%  {r['player']:<20s}  {r['song_name'][:60]}")

    if not_found:
        print()
        print("-" * 70)
        print(f"  NO_DB_MATCH ({not_found} entries -- songs not in our chart folder)")
        print("-" * 70)
        for r in results:
            if r["status"] == "NO_DB_MATCH":
                print(f"  {r['player']:<20s}  {r['song_name'][:70]}")


def export_csv(results, path: Path):
    import csv
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=[
            "status", "song_name", "player", "live_score",
            "db_score", "db_fg_score", "naked_score", "gear_power",
            "gap", "gap_pct",
        ])
        w.writeheader()
        w.writerows(results)
    print(f"  CSV exported: {path}")


def main():
    print("  Loading live leaderboard...")
    lb_rows = load_lb()

    print("  Loading DB songs...")
    db = sqlite3.connect(str(DB_PATH))
    db_rows = load_db_songs(db)
    db.close()

    print("  Comparing...")
    results, matched, not_found = audit(db_rows, lb_rows)

    print_report(results, matched, not_found)

    if "--csv" in sys.argv:
        export_csv(results, REPO_ROOT / "artifacts" / "lb_audit_report.csv")


if __name__ == "__main__":
    main()
