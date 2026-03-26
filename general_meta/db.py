from __future__ import annotations

import os
import sqlite3
from typing import List

from gear_optimizer.data.database import (
    _load_piece_name_encoding_maps,
    _unpack_id_groups,
    _unpack_id_list,
    get_db_connection,
    get_evolution_db_path,
)
from gear_optimizer.data.loadout_equivalence import representative_mini_names


def get_all_loadouts_from_db() -> List[dict]:
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
        maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))

        def _decode_row_names(row: sqlite3.Row) -> tuple[list[str], list[list[str]]]:
            gear_ids = _unpack_id_list(row["gear_ids_blob"]) if row["gear_ids_blob"] else []
            gear_names = [str(maps.gear_id_to_name.get(int(i), "") or "") for i in gear_ids if int(i) > 0]
            gear_names = [n for n in gear_names if n]

            mini_groups: list[list[str]] = []
            id_groups = _unpack_id_groups(row["minis_ids_blob"]) if row["minis_ids_blob"] else []
            for g in id_groups or []:
                if not g:
                    continue
                names = [str(maps.mini_id_to_name.get(int(i), "") or "") for i in g if int(i) > 0]
                names = [n for n in names if n]
                if names:
                    mini_groups.append(names)
            return gear_names, mini_groups

        def _select_all_from(table: str, *, where: str = "", params: tuple = ()) -> None:
            try:
                cursor = conn.execute(
                    f"""
                    SELECT song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json
                    FROM {table}
                    {where}
                    """,
                    params,
                )
            except sqlite3.Error:
                return
            for row in cursor:
                gear_names, mini_groups = _decode_row_names(row)
                results.append(
                    {
                        "song_name": row["song_name"],
                        "score": row["score"],
                        "fg_score": row["fg_score"],
                        "gear": gear_names,
                        "mini_groups": mini_groups,
                        "minis": representative_mini_names(mini_groups),
                        "details_json": row["details_json"],
                    }
                )

        # Baseline-only workflow: GeneralMeta reads the canonical baseline tier (T5 by default).
        _select_all_from("team_buff_loadouts", where="WHERE UPPER(team_buff) = 'T5'")
        _select_all_from("team_buff_fg_loadouts", where="WHERE UPPER(team_buff) = 'T5'")
        return results
    finally:
        conn.close()


__all__ = ["get_all_loadouts_from_db"]
