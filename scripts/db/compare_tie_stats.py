from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import (  # noqa: E402
    _json_loads,
    _unpack_stats_after_load,
    get_db_connection_readonly,
)
from gear_optimizer.core.gem_defs import STAT_KEYS  # noqa: E402
from gear_optimizer.data.migrations import _table_exists  # noqa: E402


@dataclass(frozen=True)
class TopRow:
    song_name: str
    team_buff: str
    loadout_hash: str
    score: int
    fg_score: int
    stats: Optional[dict[str, int]]
    gem_counts: Optional[dict[str, int]]


def _canonical_stats(details: Any) -> Optional[dict[str, int]]:
    if not isinstance(details, dict) or not details:
        return None
    details = _unpack_stats_after_load(details)
    stats = details.get("Stats")
    if not isinstance(stats, dict) or not stats:
        return None
    out: dict[str, int] = {}
    for key in STAT_KEYS:
        try:
            out[str(key)] = int(stats.get(key, 0) or 0)
        except Exception:
            out[str(key)] = 0
    return out


def _canonical_gem_counts(details: Any) -> Optional[dict[str, int]]:
    if not isinstance(details, dict) or not details:
        return None
    details = _unpack_stats_after_load(details)
    raw = details.get("GemCounts")
    if not isinstance(raw, dict) or not raw:
        return None
    out: dict[str, int] = {}
    for k, v in raw.items():
        key = str(k or "").strip()
        if not key:
            continue
        try:
            out[key] = int(v or 0)
        except Exception:
            out[key] = 0
    return out or None


def _load_top_rows(conn, *, table: str, metric: str, team_buff: str) -> dict[str, TopRow]:
    if not _table_exists(conn, table):
        return {}

    metric = str(metric).strip()
    if metric not in {"score", "fg_score"}:
        raise ValueError(f"Unsupported metric: {metric}")

    # NOTE: Deterministic tie-breaker: choose smallest loadout_hash among equal metric values.
    sql = f"""
    SELECT song_name, team_buff, loadout_hash, score, fg_score, details_json
    FROM (
        SELECT song_name, team_buff, loadout_hash, score, fg_score, details_json,
               ROW_NUMBER() OVER (
                   PARTITION BY song_name
                   ORDER BY {metric} DESC, loadout_hash ASC
               ) AS rn
        FROM {table}
        WHERE team_buff = ?
    )
    WHERE rn = 1
    """
    rows = conn.execute(sql, (str(team_buff),)).fetchall()

    out: dict[str, TopRow] = {}
    for row in rows or []:
        song = str(row["song_name"] or "").strip()
        if not song:
            continue
        details = _json_loads(row["details_json"]) if row["details_json"] else None
        if not isinstance(details, dict):
            details = {}
        stats = _canonical_stats(details)
        gems = _canonical_gem_counts(details)
        out[song] = TopRow(
            song_name=song,
            team_buff=str(row["team_buff"] or "").strip(),
            loadout_hash=str(row["loadout_hash"] or "").strip(),
            score=int(row["score"] or 0),
            fg_score=int(row["fg_score"] or 0),
            stats=stats,
            gem_counts=gems,
        )
    return out


def _fetch_by_hash(
    conn,
    *,
    table: str,
    team_buff: str,
    song_name: str,
    loadout_hash: str,
    metric: str,
) -> Optional[TopRow]:
    if not loadout_hash:
        return None
    if not _table_exists(conn, table):
        return None

    metric = str(metric).strip()
    if metric not in {"score", "fg_score"}:
        raise ValueError(f"Unsupported metric: {metric}")

    sql = f"""
    SELECT song_name, team_buff, loadout_hash, score, fg_score, details_json
    FROM {table}
    WHERE song_name = ? AND team_buff = ? AND loadout_hash = ?
    ORDER BY {metric} DESC
    LIMIT 1
    """
    row = conn.execute(sql, (str(song_name), str(team_buff), str(loadout_hash))).fetchone()
    if row is None:
        return None

    details = _json_loads(row["details_json"]) if row["details_json"] else None
    if not isinstance(details, dict):
        details = {}
    stats = _canonical_stats(details)
    gems = _canonical_gem_counts(details)
    return TopRow(
        song_name=str(row["song_name"] or "").strip(),
        team_buff=str(row["team_buff"] or "").strip(),
        loadout_hash=str(row["loadout_hash"] or "").strip(),
        score=int(row["score"] or 0),
        fg_score=int(row["fg_score"] or 0),
        stats=stats,
        gem_counts=gems,
    )


def _dict_diff_keys(a: Optional[dict[str, int]], b: Optional[dict[str, int]]) -> list[str]:
    if a is None and b is None:
        return []
    if a is None or b is None:
        return ["<missing>"]
    keys = set(a.keys()) | set(b.keys())
    changed = []
    for k in sorted(keys):
        if int(a.get(k, 0) or 0) != int(b.get(k, 0) or 0):
            changed.append(k)
    return changed


def _compare_tie_stats(
    *,
    label: str,
    current_rows: dict[str, TopRow],
    legacy_rows: dict[str, TopRow],
    metric: str,
    eps: int,
    current_conn,
    legacy_conn,
    table: str,
    team_buff: str,
    cross_hash: bool,
    example_limit: int,
) -> dict[str, Any]:
    songs = sorted(set(current_rows.keys()) & set(legacy_rows.keys()))

    total = len(songs)
    tie_songs: list[str] = []

    same_hash = 0
    diff_hash = 0
    stats_match = 0
    stats_mismatch = 0
    gems_match = 0
    gems_mismatch = 0
    missing_stats = 0

    cross_compared = 0
    cross_stats_mismatch = 0
    cross_missing_stats = 0

    mismatches: list[dict[str, Any]] = []

    for song in songs:
        c = current_rows.get(song)
        l = legacy_rows.get(song)
        if c is None or l is None:
            continue

        cm = int(getattr(c, metric) or 0)
        lm = int(getattr(l, metric) or 0)
        if abs(cm - lm) > int(eps):
            continue

        tie_songs.append(song)
        if c.loadout_hash and c.loadout_hash == l.loadout_hash:
            same_hash += 1
            diff_stats = _dict_diff_keys(c.stats, l.stats)
            diff_gems = _dict_diff_keys(c.gem_counts, l.gem_counts)

            if c.stats is None or l.stats is None:
                missing_stats += 1
            if not diff_stats:
                stats_match += 1
            else:
                stats_mismatch += 1
                if len(mismatches) < int(example_limit):
                    mismatches.append(
                        {
                            "song_name": song,
                            "metric": metric,
                            "current": {
                                "value": cm,
                                "loadout_hash": c.loadout_hash,
                                "stats": c.stats,
                                "gem_counts": c.gem_counts,
                            },
                            "legacy": {
                                "value": lm,
                                "loadout_hash": l.loadout_hash,
                                "stats": l.stats,
                                "gem_counts": l.gem_counts,
                            },
                            "diff_stats_keys": diff_stats,
                            "diff_gem_keys": diff_gems,
                        }
                    )

            if not diff_gems:
                gems_match += 1
            else:
                gems_mismatch += 1
            continue

        diff_hash += 1

        if not cross_hash:
            continue

        # Cross-hash compare: for tie songs where top loadout differs, check whether
        # the other DB has the opposite hash and whether stats/gems match for that
        # shared hash. This helps detect "stats wrong but score right" even when the
        # top tie-breaker chose different hashes.
        if c.loadout_hash:
            l_for_c = _fetch_by_hash(
                legacy_conn,
                table=table,
                team_buff=team_buff,
                song_name=song,
                loadout_hash=c.loadout_hash,
                metric=metric,
            )
            if l_for_c is not None:
                cross_compared += 1
                diff_stats = _dict_diff_keys(c.stats, l_for_c.stats)
                if c.stats is None or l_for_c.stats is None:
                    cross_missing_stats += 1
                if diff_stats:
                    cross_stats_mismatch += 1

        if l.loadout_hash:
            c_for_l = _fetch_by_hash(
                current_conn,
                table=table,
                team_buff=team_buff,
                song_name=song,
                loadout_hash=l.loadout_hash,
                metric=metric,
            )
            if c_for_l is not None:
                cross_compared += 1
                diff_stats = _dict_diff_keys(c_for_l.stats, l.stats)
                if c_for_l.stats is None or l.stats is None:
                    cross_missing_stats += 1
                if diff_stats:
                    cross_stats_mismatch += 1

    result = {
        "label": label,
        "metric": metric,
        "team_buff": team_buff,
        "eps": int(eps),
        "total_songs_compared": total,
        "tie_song_count": len(tie_songs),
        "tie_same_hash_count": same_hash,
        "tie_diff_hash_count": diff_hash,
        "tie_same_hash": {
            "stats_match": stats_match,
            "stats_mismatch": stats_mismatch,
            "missing_stats": missing_stats,
            "gem_counts_match": gems_match,
            "gem_counts_mismatch": gems_mismatch,
        },
        "cross_hash": {
            "enabled": bool(cross_hash),
            "comparisons": cross_compared,
            "stats_mismatch": cross_stats_mismatch,
            "missing_stats": cross_missing_stats,
        },
        "examples": mismatches,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare Stats payloads for tie songs between current and legacy DBs.")
    parser.add_argument("--current", type=str, default=str(PROJECT_ROOT / "evolution.db"))
    parser.add_argument("--legacy", type=str, default=str(PROJECT_ROOT / "evolution_legacy.db"))
    parser.add_argument("--team-buff", type=str, default="T5")
    parser.add_argument("--eps", type=int, default=2, help="Treat scores within +/- eps as ties.")
    parser.add_argument("--no-cross-hash", action="store_true", help="Disable cross-hash comparison for diff-hash ties.")
    parser.add_argument("--examples", type=int, default=10, help="Max mismatch examples to print/store.")
    parser.add_argument("--artifacts-dir", type=str, default=str(PROJECT_ROOT / "artifacts"))
    args = parser.parse_args()

    team_buff = str(args.team_buff or "").strip().upper() or "T5"
    eps = int(args.eps)
    example_limit = max(0, int(args.examples))
    cross_hash = not bool(args.no_cross_hash)

    current_path = str(args.current)
    legacy_path = str(args.legacy)

    current_conn = get_db_connection_readonly(current_path, timeout=5.0)
    legacy_conn = get_db_connection_readonly(legacy_path, timeout=5.0)

    try:
        current_base = _load_top_rows(current_conn, table="team_buff_loadouts", metric="score", team_buff=team_buff)
        legacy_base = _load_top_rows(legacy_conn, table="team_buff_loadouts", metric="score", team_buff=team_buff)

        current_fg = _load_top_rows(current_conn, table="team_buff_fg_loadouts", metric="fg_score", team_buff=team_buff)
        legacy_fg = _load_top_rows(legacy_conn, table="team_buff_fg_loadouts", metric="fg_score", team_buff=team_buff)

        base_report = _compare_tie_stats(
            label="base_best_score",
            current_rows=current_base,
            legacy_rows=legacy_base,
            metric="score",
            eps=eps,
            current_conn=current_conn,
            legacy_conn=legacy_conn,
            table="team_buff_loadouts",
            team_buff=team_buff,
            cross_hash=cross_hash,
            example_limit=example_limit,
        )
        fg_report = _compare_tie_stats(
            label="fg_best_fg_score",
            current_rows=current_fg,
            legacy_rows=legacy_fg,
            metric="fg_score",
            eps=eps,
            current_conn=current_conn,
            legacy_conn=legacy_conn,
            table="team_buff_fg_loadouts",
            team_buff=team_buff,
            cross_hash=cross_hash,
            example_limit=example_limit,
        )

        combined = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "current_db": current_path,
            "legacy_db": legacy_path,
            "reports": [base_report, fg_report],
        }

        # Print concise summary
        for report in combined["reports"]:
            print("=" * 80)
            print(f"{report['label']} (team_buff={report['team_buff']}, eps=+/-{report['eps']})")
            print("=" * 80)
            print(f"Songs compared: {report['total_songs_compared']}")
            print(f"Ties: {report['tie_song_count']}")
            print(f"  tie_same_hash: {report['tie_same_hash_count']}")
            print(f"  tie_diff_hash: {report['tie_diff_hash_count']}")
            same = report["tie_same_hash"]
            print("Same-hash ties:")
            print(f"  stats_match: {same['stats_match']}")
            print(f"  stats_mismatch: {same['stats_mismatch']}")
            print(f"  missing_stats: {same['missing_stats']}")
            print(f"  gem_counts_match: {same['gem_counts_match']}")
            print(f"  gem_counts_mismatch: {same['gem_counts_mismatch']}")
            cross = report["cross_hash"]
            if cross.get("enabled"):
                print("Cross-hash checks (diff-hash ties):")
                print(f"  comparisons: {cross['comparisons']}")
                print(f"  stats_mismatch: {cross['stats_mismatch']}")
                print(f"  missing_stats: {cross['missing_stats']}")
            if report.get("examples"):
                print("\nExample mismatches (same-hash ties):")
                for ex in report["examples"]:
                    song = ex.get("song_name", "")
                    keys = ex.get("diff_stats_keys", [])
                    gem_keys = ex.get("diff_gem_keys", [])
                    print(f"- {song}: diff_stats={keys} diff_gems={gem_keys}")

        artifacts_dir = Path(str(args.artifacts_dir))
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = artifacts_dir / f"db_tie_stats_check_{stamp}.json"
        out_path.write_text(json.dumps(combined, indent=2), encoding="utf-8")
        print("\nWrote report:", str(out_path))
        return 0
    finally:
        try:
            current_conn.close()
        except Exception:
            pass
        try:
            legacy_conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
