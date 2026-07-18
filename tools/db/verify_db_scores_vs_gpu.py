"""
Verify persisted DB scores against the scorer that owns each table.

This is a practical integrity check for Evolution DB rows:
- `team_buff_loadouts`: decode `details_json` -> Stats, recompute the base score via
  `score_stats_exact`, and compare it to `score`.
- `team_buff_fg_loadouts`: decode `force_details_json` -> visible Stats + response surface,
  recompute the exact FG score, and compare it to `fg_score`. Its `score` column is paired
  source-base context, not the FG score of the re-optimized visible Stats.

Usage:
  python tools/db/verify_db_scores_vs_gpu.py --db evolution.db --team-buff T5 --rows 200
  python tools/db/verify_db_scores_vs_gpu.py --db artifacts/smoke_run/smoke_evolution_v18.db --rows 20
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _infer_difficulty_from_song_name(song_name: str) -> str:
    s = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in s:
            return diff
    if " (Tutorial) " in s:
        return "Easy"
    return "Normal"


def _song_file_from_name(project_root: Path, song_name: str) -> Path | None:
    diff = _infer_difficulty_from_song_name(song_name)
    fp = project_root / "Data" / diff / f"{song_name}.txt"
    if fp.exists():
        return fp
    return _song_path_index(project_root, diff).get(song_name)


@lru_cache(maxsize=6)
def _song_path_index(project_root: Path, difficulty: str) -> dict[str, Path]:
    root = project_root / "Data" / difficulty
    if not root.is_dir():
        return {}

    from gear_optimizer.data.song_io import scan_song_header

    paths: dict[str, Path] = {}
    for path in root.rglob("*.txt"):
        metadata = scan_song_header(str(path))
        name = str((metadata or {}).get("Song Name") or "").strip()
        if name:
            paths.setdefault(name, path)
    return paths


def _replay_fg_score(row: sqlite3.Row, *, calc_song: dict, ref_arrays: dict) -> int | None:
    force_json = row["force_details_json"]
    if not force_json:
        return None
    try:
        force = json.loads(force_json)
    except Exception:
        return None
    if not isinstance(force, dict):
        return None

    from gear_optimizer.helpers.song_helpers.fg_payload import require_response_surface
    from gear_optimizer.helpers.song_helpers.force_greats.result_application import read_visible_stats
    from gear_optimizer.solver.scoring.exact_rescore import score_force_greats_response_surface_exact

    stats = read_visible_stats(force)
    if not stats:
        return None
    try:
        surface = require_response_surface(force)
    except (TypeError, ValueError):
        return None
    score = score_force_greats_response_surface_exact(stats, calc_song, ref_arrays, surface)
    return None if score is None else int(score)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify DB scores against their canonical scorer.")
    parser.add_argument("--db", type=str, default="", help="SQLite DB path (default: ./evolution.db or EVOLUTION_DB_PATH).")
    parser.add_argument("--table", type=str, default="team_buff_loadouts", help="Table to verify (default: team_buff_loadouts).")
    parser.add_argument("--team-buff", type=str, default="T5", help="Team buff tier filter (default: T5).")
    parser.add_argument("--rows", type=int, default=100, help="How many top rows to verify (default: 100).")
    parser.add_argument("--song-contains", type=str, default="", help="Optional substring filter on song_name.")
    parser.add_argument("--show-mismatches", action="store_true", help="Print mismatch details.")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    db_path = Path(args.db) if args.db else (project_root / "evolution.db")
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
    from gear_optimizer.core.config import load_config
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.database import _unpack_stats_after_load
    from gear_optimizer.data.song_io import get_base_calc_song
    from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact

    cfg_dict = cfg_to_dict(load_config())
    ref_arrays = _get_team_buff_ref_arrays_cached()
    if not isinstance(ref_arrays, dict) or not ref_arrays:
        raise SystemExit("ref_arrays unavailable (failed to load Stats lookup tables)")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    calc_song_cache: dict[str, dict] = {}

    team_buff = str(args.team_buff or "").strip().upper() or "T5"
    rows = max(1, int(args.rows))
    song_contains = str(args.song_contains or "").strip().lower()
    table = str(args.table or "team_buff_loadouts").strip()
    if not table.replace("_", "").isalnum():
        raise SystemExit(f"Invalid table name: {table!r}")
    is_fg_table = table == "team_buff_fg_loadouts"

    selected_columns = (
        "song_name, score, fg_score, details_json, force_details_json"
        if is_fg_table
        else "song_name, score, details_json"
    )
    q = f"""
        SELECT {selected_columns}
        FROM {table}
        WHERE UPPER(COALESCE(team_buff,'')) = ?
        ORDER BY {"fg_score" if is_fg_table else "score"} DESC
        LIMIT ?
    """
    db_rows = conn.execute(q, (team_buff, rows)).fetchall()

    checked = 0
    mismatches = 0
    max_abs_delta = 0

    try:
        for r in db_rows:
            song_name = str(r["song_name"] or "").strip()
            if not song_name:
                continue
            if song_contains and song_contains not in song_name.lower():
                continue

            calc_song = calc_song_cache.get(song_name)
            if calc_song is None:
                fp = _song_file_from_name(project_root, song_name)
                if fp is None:
                    continue
                calc_song = get_base_calc_song(str(fp), cfg_dict)
                calc_song_cache[song_name] = calc_song

            if is_fg_table:
                replay_score = _replay_fg_score(r, calc_song=calc_song, ref_arrays=ref_arrays)
                if replay_score is None:
                    continue
                db_score = int(r["fg_score"] or 0)
                replay_label = "fg_score"
            else:
                details_json = r["details_json"]
                if not details_json:
                    continue
                try:
                    details = json.loads(details_json)
                except Exception:
                    continue
                details = _unpack_stats_after_load(details) if isinstance(details, dict) else None
                stats = (details or {}).get("Stats") if isinstance(details, dict) else None
                if not isinstance(stats, dict) or not stats:
                    continue

                replay_score = int(score_stats_exact(stats, calc_song, ref_arrays))
                db_score = int(r["score"] or 0)
                replay_label = "score"
            checked += 1
            delta = int(replay_score) - int(db_score)
            max_abs_delta = max(max_abs_delta, abs(int(delta)))
            if delta != 0:
                mismatches += 1
                if args.show_mismatches:
                    print(
                        f"[MISMATCH] {song_name} {replay_label}={db_score:,} "
                        f"replay={replay_score:,} delta={delta:+,}"
                    )

        print(f"DB: {db_path}")
        print(f"Table: {table} team_buff={team_buff}")
        if is_fg_table:
            print("Verified column: fg_score (score is paired source-base context)")
        print(f"Checked rows: {checked:,}")
        print(f"Mismatches: {mismatches:,}")
        print(f"Max |delta|: {max_abs_delta:,}")
        raise SystemExit(0 if mismatches == 0 else 2)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
