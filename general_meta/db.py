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
    - Some historical DBs may only have improved ForceGreats rows present in `fg_loadouts`,
      so we include rows from both `loadouts` and `fg_loadouts`.
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return []

    conn = get_db_connection(db_path)
    try:
        results: list[dict] = []

        def _select_all_from(table: str) -> None:
            try:
                cursor = conn.execute(
                    f"""
                    SELECT song_name, score, fg_score, gear_json, minis_json, details_json
                    FROM {table}
                    """
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

        _select_all_from("loadouts")
        _select_all_from("fg_loadouts")
        return results
    finally:
        conn.close()
