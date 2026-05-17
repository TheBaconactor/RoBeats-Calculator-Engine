from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import sqlite3

from gear_optimizer.data.database import get_db_connection_readonly
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.core.team_buff import normalize_team_buff, team_buff_query_values
from gear_optimizer.data.database import get_evolution_db_path


def _get_all_loadouts_rows(*, team_buff: str = "T5") -> list[dict[str, Any]]:
    resolved_team_buff = normalize_team_buff(team_buff, default="T5")
    query_team_buffs = team_buff_query_values(resolved_team_buff, default=resolved_team_buff)
    db_path = get_evolution_db_path()
    conn = get_db_connection_readonly(db_path)
    try:
        rows: list[dict[str, Any]] = []
        placeholders = ",".join("?" for _ in query_team_buffs)
        params = tuple(query_team_buffs)

        cursor = conn.execute(
            """
            SELECT song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json
            FROM team_buff_loadouts
            WHERE UPPER(team_buff) IN ({placeholders})
            """.format(placeholders=placeholders),
            params,
        )
        rows.extend(_decode_loadout_rows(cursor, db_path=db_path))

        cursor = conn.execute(
            """
            SELECT song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json
            FROM team_buff_fg_loadouts
            WHERE UPPER(team_buff) IN ({placeholders})
            """.format(placeholders=placeholders),
            params,
        )
        rows.extend(_decode_loadout_rows(cursor, db_path=db_path))
        return rows
    finally:
        conn.close()


def _decode_loadout_rows(cursor: Iterable[sqlite3.Row], *, db_path: str) -> list[dict[str, Any]]:
    from gear_optimizer.data.database import _load_piece_name_encoding_maps, _unpack_id_groups, _unpack_id_list

    conn = getattr(cursor, "connection", None)
    if conn is None:
        raise RuntimeError("SQLite cursor is missing its owning connection")
    maps = _load_piece_name_encoding_maps(conn, db_path=db_path)

    rows: list[dict[str, Any]] = []
    for row in cursor:
        gear_ids = _unpack_id_list(row["gear_ids_blob"]) if row["gear_ids_blob"] else []
        gear_names = [str(maps.gear_id_to_name.get(int(i), "") or "") for i in gear_ids if int(i) > 0]
        gear_names = [name for name in gear_names if name]

        mini_groups: list[list[str]] = []
        for group in _unpack_id_groups(row["minis_ids_blob"]) if row["minis_ids_blob"] else []:
            if not group:
                continue
            names = [str(maps.mini_id_to_name.get(int(i), "") or "") for i in group if int(i) > 0]
            names = [name for name in names if name]
            if names:
                mini_groups.append(names)

        rows.append(
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
    return rows


def get_all_loadouts_from_db(*, team_buff: str = "T5") -> list[dict[str, Any]]:
    return _get_all_loadouts_rows(team_buff=team_buff)


__all__ = ["get_all_loadouts_from_db"]
