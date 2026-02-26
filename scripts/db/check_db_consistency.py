import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path

DEFAULT_SONG_NAME = "Ice Angel (Easy) by Yooh"
DEFAULT_REFERENCE_TIER = str(os.environ.get("DB_CONSISTENCY_REFERENCE_TIER", "T5") or "T5").strip().upper() or "T5"


@dataclass
class TierStats:
    team_buff: str
    max_base: int
    max_fg: int
    row_count: int
    fg_table_max: int
    fg_row_count: int


def _safe_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _fmt(value: int) -> str:
    return f"{int(value):,}"


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (str(table_name),)
    ).fetchone()
    return bool(row)


def _fetch_song_record(conn: sqlite3.Connection, song_name: str):
    row = conn.execute("SELECT best_score, best_fg_score FROM songs WHERE name = ?", (song_name,)).fetchone()
    if not row:
        return None
    return (_safe_int(row["best_score"]), _safe_int(row["best_fg_score"]))


def _fetch_tier_stats(conn: sqlite3.Connection, song_name: str) -> list[TierStats]:
    if not _table_exists(conn, "team_buff_loadouts"):
        return []

    base_rows = conn.execute(
        """
        SELECT
            UPPER(COALESCE(team_buff, 'UNKNOWN')) AS team_buff,
            MAX(COALESCE(score, 0)) AS max_base,
            MAX(COALESCE(fg_score, 0)) AS max_fg,
            COUNT(*) AS row_count
        FROM team_buff_loadouts
        WHERE song_name = ?
        GROUP BY UPPER(COALESCE(team_buff, 'UNKNOWN'))
        ORDER BY team_buff
        """,
        (song_name,),
    ).fetchall()

    fg_by_tier: dict[str, tuple[int, int]] = {}
    if _table_exists(conn, "team_buff_fg_loadouts"):
        fg_rows = conn.execute(
            """
            SELECT
                UPPER(COALESCE(team_buff, 'UNKNOWN')) AS team_buff,
                MAX(COALESCE(fg_score, 0)) AS max_fg,
                COUNT(*) AS row_count
            FROM team_buff_fg_loadouts
            WHERE song_name = ?
            GROUP BY UPPER(COALESCE(team_buff, 'UNKNOWN'))
            """,
            (song_name,),
        ).fetchall()
        for row in fg_rows:
            key = str(row["team_buff"] or "UNKNOWN").upper()
            fg_by_tier[key] = (_safe_int(row["max_fg"]), _safe_int(row["row_count"]))

    tiers: list[TierStats] = []
    seen: set[str] = set()

    for row in base_rows:
        key = str(row["team_buff"] or "UNKNOWN").upper()
        fg_max, fg_n = fg_by_tier.get(key, (0, 0))
        tiers.append(
            TierStats(
                team_buff=key,
                max_base=_safe_int(row["max_base"]),
                max_fg=_safe_int(row["max_fg"]),
                row_count=_safe_int(row["row_count"]),
                fg_table_max=int(fg_max),
                fg_row_count=int(fg_n),
            )
        )
        seen.add(key)

    for key, (fg_max, fg_n) in fg_by_tier.items():
        if key in seen:
            continue
        tiers.append(
            TierStats(
                team_buff=key,
                max_base=0,
                max_fg=_safe_int(fg_max),
                row_count=0,
                fg_table_max=_safe_int(fg_max),
                fg_row_count=_safe_int(fg_n),
            )
        )

    tiers.sort(key=lambda t: t.team_buff)
    return tiers


def _fetch_overall_max(conn: sqlite3.Connection, song_name: str) -> tuple[int, int, int]:
    if not _table_exists(conn, "team_buff_loadouts"):
        return (0, 0, 0)
    row = conn.execute(
        """
        SELECT
            MAX(COALESCE(score, 0)) AS max_base,
            MAX(COALESCE(fg_score, 0)) AS max_fg,
            COUNT(*) AS row_count
        FROM team_buff_loadouts
        WHERE song_name = ?
        """,
        (song_name,),
    ).fetchone()
    if not row:
        return (0, 0, 0)
    return (_safe_int(row["max_base"]), _safe_int(row["max_fg"]), _safe_int(row["row_count"]))


def _iter_top_loadouts_for_tier(conn: sqlite3.Connection, song_name: str, team_buff: str, per_tier_limit: int):
    if per_tier_limit <= 0:
        return []
    rows = conn.execute(
        """
        SELECT score, fg_score, gear_json, details_json
        FROM team_buff_loadouts
        WHERE song_name = ? AND UPPER(COALESCE(team_buff, 'UNKNOWN')) = ?
        ORDER BY score DESC, fg_score DESC
        LIMIT ?
        """,
        (song_name, str(team_buff).upper(), int(per_tier_limit)),
    ).fetchall()
    return rows


def _print_tier_table(song_record, tier_stats: list[TierStats]) -> None:
    print("\nTIER SUMMARY (team_buff_loadouts + team_buff_fg_loadouts):")
    if not tier_stats:
        print("  (no tier rows found)")
        return

    song_best = _safe_int(song_record[0]) if song_record else None
    song_best_fg = _safe_int(song_record[1]) if song_record else None

    for tier in tier_stats:
        base_match = song_best is not None and int(tier.max_base) == int(song_best)
        fg_match = song_best_fg is not None and int(tier.max_fg) == int(song_best_fg)
        fg_sync_ok = (tier.fg_row_count <= 0 and int(tier.fg_table_max) <= 0) or (
            tier.fg_row_count > 0 and int(tier.max_fg) == int(tier.fg_table_max)
        )
        print(
            f"  {tier.team_buff}: rows={tier.row_count}, fg_rows={tier.fg_row_count}, "
            f"max_base={_fmt(tier.max_base)}, max_fg={_fmt(tier.max_fg)}, "
            f"fg_table_max={_fmt(tier.fg_table_max)}, "
            f"songs_match(base={'yes' if base_match else 'no'}, fg={'yes' if fg_match else 'no'}), "
            f"fg_table_sync={'yes' if fg_sync_ok else 'no'}"
        )


def _print_top_loadouts(
    conn: sqlite3.Connection, song_name: str, tier_stats: list[TierStats], per_tier_limit: int
) -> None:
    if per_tier_limit <= 0 or not tier_stats:
        return
    print("\nTOP LOADOUTS PER TIER:")
    for tier in tier_stats:
        print(f"  [{tier.team_buff}]")
        rows = _iter_top_loadouts_for_tier(conn, song_name, tier.team_buff, per_tier_limit=per_tier_limit)
        if not rows:
            print("    (none)")
            continue
        for i, row in enumerate(rows, 1):
            gear = json.loads(row["gear_json"]) if row["gear_json"] else []
            details = json.loads(row["details_json"]) if row["details_json"] else {}
            ft = details.get("FT", "?")
            ff = details.get("FF", "?")
            print(
                f"    #{i}: Base={_fmt(_safe_int(row['score']))}, FG={_fmt(_safe_int(row['fg_score']))}, FT={ft}, FF={ff}"
            )
            if gear:
                print(f"        Gear: {', '.join(gear[:3])}{'...' if len(gear) > 3 else ''}")


def _evaluate(song_record, tier_stats: list[TierStats], reference_tier: str) -> dict:
    out = {
        "ok": True,
        "reference_tier_found": False,
        "reference_base_match": False,
        "reference_fg_match": False,
        "base_match_tiers": [],
        "fg_match_tiers": [],
        "fg_sync_issues": [],
    }

    if song_record is None:
        out["ok"] = False
        return out

    song_best, song_best_fg = int(song_record[0]), int(song_record[1])
    tier_map = {t.team_buff: t for t in tier_stats}
    out["base_match_tiers"] = [t.team_buff for t in tier_stats if int(t.max_base) == song_best]
    out["fg_match_tiers"] = [t.team_buff for t in tier_stats if int(t.max_fg) == song_best_fg]

    ref_key = str(reference_tier or "").strip().upper() or "T5"
    ref = tier_map.get(ref_key)
    if ref is not None:
        out["reference_tier_found"] = True
        out["reference_base_match"] = int(ref.max_base) == song_best
        out["reference_fg_match"] = int(ref.max_fg) == song_best_fg
        if not (out["reference_base_match"] and out["reference_fg_match"]):
            out["ok"] = False
    else:
        out["ok"] = False

    fg_sync_issues = []
    for t in tier_stats:
        fg_sync_ok = (t.fg_row_count <= 0 and int(t.fg_table_max) <= 0) or (
            t.fg_row_count > 0 and int(t.max_fg) == int(t.fg_table_max)
        )
        if not fg_sync_ok:
            fg_sync_issues.append(t.team_buff)
    out["fg_sync_issues"] = fg_sync_issues
    if fg_sync_issues:
        out["ok"] = False

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Check songs-table consistency against TeamBuff tier leaderboards.")
    parser.add_argument("--song", default=DEFAULT_SONG_NAME, help="Exact song name key in DB.")
    parser.add_argument("--db-path", default="", help="Optional explicit DB path (overrides default lookup).")
    parser.add_argument(
        "--reference-tier",
        default=DEFAULT_REFERENCE_TIER,
        help="Tier that songs.best_score/songs.best_fg_score should match (default: T5).",
    )
    parser.add_argument(
        "--show-loadouts",
        action="store_true",
        help="Print top loadouts for each tier.",
    )
    parser.add_argument(
        "--max-loadouts-per-tier",
        type=int,
        default=3,
        help="When --show-loadouts is enabled, print at most this many loadouts per tier.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero if reference-tier match or tier FG table sync checks fail.",
    )
    args = parser.parse_args()

    song_name = str(args.song or "").strip()
    if not song_name:
        print("ERROR: --song must be non-empty")
        return 2

    db_path = str(args.db_path or "").strip() or get_evolution_db_path()
    reference_tier = str(args.reference_tier or "").strip().upper() or "T5"

    conn = get_db_connection(db_path)
    try:
        song_record = _fetch_song_record(conn, song_name)
        tier_stats = _fetch_tier_stats(conn, song_name)
        overall_max_base, overall_max_fg, overall_rows = _fetch_overall_max(conn, song_name)
        eval_result = _evaluate(song_record, tier_stats, reference_tier)

        print("=" * 96)
        print(f"DATABASE CONSISTENCY CHECK: {song_name}")
        print("=" * 96)
        print(f"DB Path: {db_path}")
        print(f"Reference Tier: {reference_tier}")

        if song_record is None:
            print("\nSONGS TABLE:")
            print("  (no row found for this song)")
        else:
            print("\nSONGS TABLE:")
            print(f"  Best Score: {_fmt(song_record[0])}")
            print(f"  Best FG Score: {_fmt(song_record[1])}")

        print("\nALL-TIER OVERALL MAX (team_buff_loadouts):")
        print(f"  Highest Base Score: {_fmt(overall_max_base)}")
        print(f"  Highest FG Score: {_fmt(overall_max_fg)}")
        print(f"  Total Rows: {overall_rows}")

        _print_tier_table(song_record, tier_stats)

        if args.show_loadouts:
            _print_top_loadouts(
                conn,
                song_name,
                tier_stats,
                per_tier_limit=max(0, int(args.max_loadouts_per_tier)),
            )

        print("\nREFERENCE CHECK:")
        if not eval_result["reference_tier_found"]:
            print(f"  FAIL: reference tier '{reference_tier}' was not found for this song.")
        else:
            print(
                f"  Reference tier ({reference_tier}): "
                f"base_match={'YES' if eval_result['reference_base_match'] else 'NO'}, "
                f"fg_match={'YES' if eval_result['reference_fg_match'] else 'NO'}"
            )

        print("\nALL-TIER MATCH SCAN:")
        base_tiers = eval_result["base_match_tiers"] or []
        fg_tiers = eval_result["fg_match_tiers"] or []
        print(f"  Songs best_score matches tiers: {', '.join(base_tiers) if base_tiers else '(none)'}")
        print(f"  Songs best_fg_score matches tiers: {', '.join(fg_tiers) if fg_tiers else '(none)'}")

        print("\nFG TABLE SYNC CHECK:")
        fg_sync_issues = eval_result["fg_sync_issues"] or []
        if fg_sync_issues:
            print(f"  FAIL: team_buff_loadouts vs team_buff_fg_loadouts mismatch in tiers: {', '.join(fg_sync_issues)}")
        else:
            print("  OK: per-tier FG maxima are synchronized across both tables.")

        if eval_result["ok"]:
            print("\nRESULT: PASS")
            return 0

        print("\nRESULT: FAIL")
        return 1 if args.strict else 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
