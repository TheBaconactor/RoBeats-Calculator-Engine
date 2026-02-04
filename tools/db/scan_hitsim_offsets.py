import argparse
import json
import sqlite3
from pathlib import Path


def _table_or_view_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE (type='table' OR type='view') AND name = ? LIMIT 1",
        (str(name),),
    ).fetchone()
    return row is not None


def _pick_source_view(conn: sqlite3.Connection) -> str:
    if _table_or_view_exists(conn, "fg_loadouts_unified"):
        return "fg_loadouts_unified"
    raise RuntimeError("No FG source found (expected fg_loadouts_unified).")


def _coerce_int(v: object, default: int = 0) -> int:
    try:
        return int(v or 0)
    except Exception:
        return int(default)


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan DB for max HumanHitSim forced-Great timing offsets.")
    parser.add_argument("--db", default="evolution.db")
    parser.add_argument("--team-buff", default="T5", help="Filter team buff tier (e.g., T5). Use ALL for no filter.")
    parser.add_argument("--top", type=int, default=20, help="Print top-N songs by |offset|.")
    parser.add_argument(
        "--include-non-improving",
        action="store_true",
        help="Include FG records where fg_score <= score (default: skip).",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"DB not found: {db_path}")
        return 2

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        source = _pick_source_view(conn)

        where = ["force_details_json IS NOT NULL", "force_details_json <> ''", "fg_score > 0"]
        params: list[object] = []

        if not args.include_non_improving:
            where.append("fg_score > score")

        team_buff = str(args.team_buff or "").strip()
        if team_buff and team_buff.upper() != "ALL":
            where.append("team_buff = ?")
            params.append(team_buff)

        where_sql = " AND ".join(where)

        rows = conn.execute(
            f"""
            WITH ranked AS (
                SELECT
                    song_name,
                    team_buff,
                    score,
                    fg_score,
                    force_details_json,
                    ROW_NUMBER() OVER (PARTITION BY song_name ORDER BY fg_score DESC) AS rn
                FROM {source}
                WHERE {where_sql}
            )
            SELECT song_name, team_buff, score, fg_score, force_details_json
            FROM ranked
            WHERE rn = 1;
            """,
            params,
        ).fetchall()

        total = len(rows)
        hits: list[dict] = []
        missing_timing = 0
        bad_json = 0

        for r in rows:
            blob = r["force_details_json"]
            try:
                obj = json.loads(blob) if blob else {}
            except Exception:
                bad_json += 1
                continue
            if not isinstance(obj, dict):
                bad_json += 1
                continue

            fg = obj.get("ForceGreats") or {}
            if not isinstance(fg, dict):
                missing_timing += 1
                continue
            signed_ms = _coerce_int(fg.get("hitsim_offset_delta_ms"), 0)
            if signed_ms == 0 and "hitsim_offset_delta_ms" not in fg:
                missing_timing += 1
                continue
            abs_ms = abs(int(signed_ms))

            hits.append(
                {
                    "song": str(r["song_name"]),
                    "team_buff": str(r["team_buff"]),
                    "score": _coerce_int(r["score"], 0),
                    "fg_score": _coerce_int(r["fg_score"], 0),
                    "abs_ms": abs_ms,
                    "signed_ms": signed_ms,
                }
            )

        if not hits:
            print(f"Scanned {total} songs from `{source}`; no rows with ForceGreats.hitsim_offset_delta_ms found.")
            print("Tip: run the optimizer with HumanHitSim enabled and an improving FG result to populate this field.")
            return 0

        hits.sort(key=lambda x: (x["abs_ms"], x["fg_score"]), reverse=True)
        best = hits[0]

        print(
            f"Songs scanned: {total} | with timing: {len(hits)} | missing timing: {missing_timing} | bad json: {bad_json}"
        )
        print(f"MAX |offset|: {best['abs_ms']}ms (signed {best['signed_ms']:+d}ms) | {best['song']}")

        top_n = max(0, int(args.top))
        if top_n:
            print("")
            print(f"Top {min(top_n, len(hits))} by |offset|:")
            for i, e in enumerate(hits[:top_n], start=1):
                print(
                    f"{i:>2}. {e['abs_ms']:>4}ms (signed {e['signed_ms']:+d}ms) | fg={e['fg_score']} base={e['score']} | {e['song']}"
                )

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
