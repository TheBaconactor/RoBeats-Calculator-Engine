from __future__ import annotations

import os
import sqlite3
from typing import Dict, List

from gear_optimizer.data.database import get_db_connection, get_evolution_db_path


def get_all_loadouts_from_db() -> List[Dict]:
    """
    Query all loadouts from the database with their scores and gear/mini info.

    Notes:
    - GeneralMeta treats the "peak" per song as the best achievable score for a loadout:
      `max(score, fg_score)` (i.e., either base or ForceGreats).
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return []

    conn = get_db_connection(db_path)
    try:
        results: list[dict] = []

        def _select_all_from(table: str, *, where: str = "", params: tuple = ()) -> None:
            try:
                cursor = conn.execute(
                    f"""
                    SELECT song_name, score, fg_score, gear_json, minis_json, details_json
                    FROM {table}
                    {where}
                    """
                    ,
                    params,
                )
            except sqlite3.Error:
                return
            for row in cursor:
                results.append(
                    {
                        "song_name": row["song_name"],
                        "score": row["score"],
                        "fg_score": row["fg_score"],
                        "gear_json": row["gear_json"],
                        "minis_json": row["minis_json"],
                        "details_json": row["details_json"],
                    }
                )

        has_unified = (
            conn.execute("SELECT 1 FROM sqlite_master WHERE type='view' AND name='loadouts_unified'").fetchone()
            is not None
        )
        if has_unified:
            _select_all_from("loadouts_unified", where="WHERE UPPER(team_buff) = 'T5'")
        else:
            _select_all_from("team_buff_loadouts", where="WHERE UPPER(team_buff) = 'T5'")

        # Use unified view for FG rows so team_buff is always present
        try:
            cursor = conn.execute(
                """
                SELECT song_name, team_buff, score, fg_score, gear_json, minis_json, details_json
                FROM fg_loadouts_unified
                """
            )
            for row in cursor:
                results.append(
                    {
                        "song_name": row["song_name"],
                        "team_buff": row["team_buff"],
                        "score": row["score"],
                        "fg_score": row["fg_score"],
                        "gear_json": row["gear_json"],
                        "minis_json": row["minis_json"],
                        "details_json": row["details_json"],
                    }
                )
        except sqlite3.Error:
            pass
        return results
    finally:
        conn.close()


def get_all_team_buff_loadouts_from_db() -> Dict[str, List[Dict]]:
    """
    Query all TeamBuff-tiered loadouts from the database.

    Returns:
        Dict[str, List[Dict]] mapping `team_buff` -> rows.

    Notes:
    - Rows are sourced from BOTH:
        - team_buff_loadouts
        - team_buff_fg_loadouts
    - Like the non-tiered GeneralMeta path, callers should treat the "peak" as `max(score, fg_score)`.
    - Some DBs may not have these tables; in that case, this returns an empty dict.
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return {}

    conn = get_db_connection(db_path)
    try:
        grouped: dict[str, list[dict]] = {}

        def _select_all_from(table: str) -> None:
            try:
                cursor = conn.execute(
                    f"""
                    SELECT song_name, team_buff, score, fg_score, gear_json, minis_json, details_json
                    FROM {table}
                    """
                )
            except sqlite3.Error:
                return
            for row in cursor:
                team_buff = str(row["team_buff"] or "").strip().upper()
                if not team_buff:
                    continue
                grouped.setdefault(team_buff, []).append(
                    {
                        "song_name": row["song_name"],
                        "team_buff": team_buff,
                        "score": row["score"],
                        "fg_score": row["fg_score"],
                        "gear_json": row["gear_json"],
                        "minis_json": row["minis_json"],
                        "details_json": row["details_json"],
                    }
                )

        _select_all_from("team_buff_loadouts")
        _select_all_from("team_buff_fg_loadouts")
        return grouped
    finally:
        conn.close()


__all__ = ["get_all_loadouts_from_db", "get_all_team_buff_loadouts_from_db"]
