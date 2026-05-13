"""
Investigate fresh-DB replay drifters for retained secondary rows.

This is a read-only diagnostic focused on songs where persisted base score does
not replay from the row's own saved Stats.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.data.database import _unpack_stats_after_load
from gear_optimizer.data.db_manager import _build_song_index_for_difficulty
from gear_optimizer.data.song_io import get_base_calc_song
from gear_optimizer.solver.scoring.exact_rescore import score_stats_exact


DEFAULT_SONGS = [
    "Endgame (Easy) by Bossfight",
    "Hue Shift (Hard) by coda",
    "Inner by fusq feat. MYLK",
    "Internet Pajamas Party by you",
    "Monday Night Monsters (Hard) by FinnMK",
    "No Time by fusq (feat. kinoine)",
    "ouroVoros (Easy) by Team Grimoire",
]


def _infer_difficulty(song_name: str) -> str:
    s = str(song_name or "")
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in s:
            return diff
    return "Normal"


def _song_file(song_name: str, difficulty_index: dict[str, dict[str, str]]) -> str | None:
    diff = _infer_difficulty(song_name)
    fp = PROJECT_ROOT / "Data" / diff / f"{song_name}.txt"
    if fp.exists():
        return str(fp)
    idx = difficulty_index.get(diff, {})
    fp = Path(str(idx.get(song_name) or ""))
    if fp.exists():
        return str(fp)
    return None


def _load_calc_song(song_name: str, difficulty_index: dict[str, dict[str, str]]) -> tuple[dict | None, str]:
    fp = _song_file(song_name, difficulty_index)
    if not fp:
        return None, "song_file_missing"
    try:
        calc_song = get_base_calc_song(fp, {})
    except Exception:
        return None, "calc_song_load_error"
    if not isinstance(calc_song, dict) or not calc_song:
        return None, "calc_song_load_error"
    return calc_song, "ok"


def _inferred_origin(
    *,
    row_hash: str,
    top_base_hash: str,
    top_fg_hash: str,
    exists_in_fg_table: bool,
) -> str:
    if row_hash and row_hash == top_base_hash:
        return "priority_top_base"
    if row_hash and row_hash == top_fg_hash:
        return "priority_top_fg_hash"
    if exists_in_fg_table:
        return "retained_or_fg_companion_secondary"
    return "retained_secondary_inferred"


def main() -> int:
    ap = argparse.ArgumentParser(description="Investigate fresh replay drifters for specific songs.")
    ap.add_argument("--db", type=str, default="evolution.db")
    ap.add_argument("--team-buff", type=str, default="T5")
    ap.add_argument("--songs", nargs="*", default=DEFAULT_SONGS)
    args = ap.parse_args()

    db_path = str(Path(args.db))
    team_buff = str(args.team_buff or "T5").strip().upper()
    target_songs = [str(s) for s in (args.songs or DEFAULT_SONGS) if str(s).strip()]

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    ref_arrays = _get_team_buff_ref_arrays_cached()
    difficulty_index = {d: _build_song_index_for_difficulty(d) for d in ("Easy", "Normal", "Hard")}
    try:
        print("=" * 88)
        print(f"fresh_secondary_drifter_investigation db={db_path} team_buff={team_buff}")
        print("=" * 88)
        for song in target_songs:
            rows = conn.execute(
                """
                SELECT loadout_hash, score, fg_score, details_json, force_details_json, timestamp
                FROM team_buff_loadouts
                WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=UPPER(?)
                ORDER BY score DESC, loadout_hash ASC
                """,
                (song, team_buff),
            ).fetchall()
            if not rows:
                print(json.dumps({"song": song, "status": "missing_song_rows"}))
                continue

            calc_song, calc_reason = _load_calc_song(song, difficulty_index)
            if not isinstance(ref_arrays, dict) or not ref_arrays:
                calc_song = None
                calc_reason = "ref_arrays_missing"

            top_base_hash = str(rows[0]["loadout_hash"] or "")
            top_fg_row = conn.execute(
                """
                SELECT loadout_hash, fg_score
                FROM team_buff_fg_loadouts
                WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=UPPER(?)
                ORDER BY fg_score DESC, loadout_hash ASC
                LIMIT 1
                """,
                (song, team_buff),
            ).fetchone()
            top_fg_hash = str(top_fg_row["loadout_hash"] or "") if top_fg_row is not None else ""

            worst_row = None
            worst_abs_delta = 0
            worst_replay = 0
            worst_has_stats = False
            worst_reason = "ok"

            for row in rows:
                row_hash = str(row["loadout_hash"] or "")
                details_blob = row["details_json"]
                details = {}
                if details_blob:
                    try:
                        details = _unpack_stats_after_load(json.loads(details_blob)) or {}
                    except Exception:
                        details = {}
                stats = details.get("Stats") if isinstance(details, dict) else None
                has_stats = isinstance(stats, dict) and bool(stats)
                if not has_stats:
                    replay_score = 0
                    reason = "stats_missing"
                elif not isinstance(calc_song, dict):
                    replay_score = 0
                    reason = calc_reason
                else:
                    try:
                        replay_score = int(score_stats_exact(stats, calc_song, ref_arrays))
                        reason = "ok" if replay_score > 0 else "replay_zero"
                    except Exception:
                        replay_score = 0
                        reason = "replay_error"

                persisted = int(row["score"] or 0)
                delta = persisted - replay_score
                if abs(delta) > worst_abs_delta:
                    worst_abs_delta = abs(delta)
                    worst_row = row
                    worst_replay = int(replay_score)
                    worst_has_stats = bool(has_stats)
                    worst_reason = str(reason)

            if worst_row is None:
                print(json.dumps({"song": song, "status": "no_replayable_rows"}))
                continue

            row_hash = str(worst_row["loadout_hash"] or "")
            exists_in_fg_table = (
                conn.execute(
                    """
                    SELECT 1
                    FROM team_buff_fg_loadouts
                    WHERE song_name=? AND UPPER(COALESCE(team_buff,''))=UPPER(?) AND loadout_hash=?
                    LIMIT 1
                    """,
                    (song, team_buff, row_hash),
                ).fetchone()
                is not None
            )

            persisted_score = int(worst_row["score"] or 0)
            delta = int(persisted_score - worst_replay)
            origin = _inferred_origin(
                row_hash=row_hash,
                top_base_hash=top_base_hash,
                top_fg_hash=top_fg_hash,
                exists_in_fg_table=exists_in_fg_table,
            )

            details_blob = worst_row["details_json"]
            details_obj = {}
            if details_blob:
                try:
                    details_obj = _unpack_stats_after_load(json.loads(details_blob)) or {}
                except Exception:
                    details_obj = {}

            payload = {
                "song": song,
                "loadout_hash": row_hash,
                "persisted_score": persisted_score,
                "replay_score": int(worst_replay),
                "delta_persisted_minus_replay": int(delta),
                "is_positive_drift": bool(delta > 0),
                "row_fg_score": int(worst_row["fg_score"] or 0),
                "has_force_payload_in_base_row": bool(worst_row["force_details_json"]),
                "has_stats_now": bool(worst_has_stats),
                "replay_reason": worst_reason,
                "calc_song_status": calc_reason,
                "top_base_hash": top_base_hash,
                "top_fg_hash": top_fg_hash,
                "is_top_base_row": bool(row_hash == top_base_hash),
                "is_top_fg_hash_row": bool(row_hash == top_fg_hash),
                "exists_in_fg_table": bool(exists_in_fg_table),
                "inferred_origin": origin,
                "details_keys": sorted(list(details_obj.keys())) if isinstance(details_obj, dict) else [],
            }
            print(json.dumps(payload, ensure_ascii=False))
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
