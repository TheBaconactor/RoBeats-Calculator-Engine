from __future__ import annotations

import sqlite3
from typing import Any, Iterable, Mapping, Optional, Sequence

from gear_optimizer.core.team_buff import normalize_team_buff, team_buff_query_values
from gear_optimizer.data.loadout_equivalence import representative_mini_names

from .encoding_maps import EncodingMaps
from . import database


class EvolutionDbDAL:
    """Unified data access facade for evolution.db."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or database.get_evolution_db_path())
        self._encoding_maps: EncodingMaps | None = None

    def get_connection(self, readonly: bool = False) -> sqlite3.Connection:
        if readonly:
            return database.get_db_connection_readonly(self.db_path)
        return database.get_db_connection(self.db_path)

    @property
    def encoding_maps(self) -> EncodingMaps:
        if self._encoding_maps is not None:
            return self._encoding_maps
        conn = self.get_connection(readonly=True)
        try:
            out = database._load_piece_name_encoding_maps(conn, db_path=self.db_path)
        finally:
            conn.close()
        self._encoding_maps = out
        return out

    # write facade
    def save_loadouts_batch(
        self,
        song_name: str,
        entries: Sequence[Mapping[str, Any]],
        *,
        team_buff: str = "T5",
        preserve_attempt_meta: bool = False,
    ) -> None:
        database.save_loadouts_batch(
            song_name,
            entries,
            db_path=self.db_path,
            team_buff=team_buff,
            preserve_attempt_meta=bool(preserve_attempt_meta),
        )

    def save_team_buff_loadouts_batch(
        self,
        song_name: str,
        team_buff: str,
        entries: Sequence[Mapping[str, Any]],
        *,
        preserve_attempt_meta: bool = False,
    ) -> None:
        database.save_team_buff_loadouts_batch(
            song_name,
            team_buff,
            entries,
            db_path=self.db_path,
            preserve_attempt_meta=bool(preserve_attempt_meta),
        )

    def update_song_counters(self, song_name: str, attempts: int = 1, records: int = 0) -> None:
        database.update_song_counters(song_name, attempts, records, db_path=self.db_path)

    # read facade
    def get_best_loadouts(self, song_name: str, *, team_buff: str = "T5") -> list[dict]:
        return database.get_best_loadouts(song_name, db_path=self.db_path, team_buff=team_buff)

    def get_song_names_present_in_db(self, song_names: Iterable[str]) -> set[str]:
        return database.get_song_names_present_in_db(song_names, db_path=self.db_path)



    def fetch_song_names(self) -> list[str]:
        from inventory_optimizer.db import fetch_song_names

        conn = self.get_connection(readonly=True)
        try:
            return fetch_song_names(conn)
        finally:
            conn.close()

    def get_all_loadouts(self, *, team_buff: str = "T5") -> list[dict]:
        resolved_team_buff = normalize_team_buff(team_buff, default="T5")
        query_team_buffs = team_buff_query_values(resolved_team_buff, default=resolved_team_buff)
        conn = self.get_connection(readonly=True)
        try:
            results: list[dict] = []
            maps = database._load_piece_name_encoding_maps(conn, db_path=self.db_path)

            def _decode_row_names(row: sqlite3.Row) -> tuple[list[str], list[list[str]]]:
                gear_ids = database._unpack_id_list(row["gear_ids_blob"]) if row["gear_ids_blob"] else []
                gear_names = [str(maps.gear_id_to_name.get(int(i), "") or "") for i in gear_ids if int(i) > 0]
                gear_names = [n for n in gear_names if n]

                mini_groups: list[list[str]] = []
                id_groups = database._unpack_id_groups(row["minis_ids_blob"]) if row["minis_ids_blob"] else []
                for g in id_groups or []:
                    if not g:
                        continue
                    names = [str(maps.mini_id_to_name.get(int(i), "") or "") for i in g if int(i) > 0]
                    names = [n for n in names if n]
                    if names:
                        mini_groups.append(names)
                return gear_names, mini_groups

            placeholders = ",".join("?" for _ in query_team_buffs)
            params = tuple(query_team_buffs)
            for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
                try:
                    cursor = conn.execute(
                        f"""
                        SELECT song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json
                        FROM {table}
                        WHERE UPPER(team_buff) IN ({placeholders})
                        """,
                        params,
                    )
                except sqlite3.Error:
                    continue
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
            return results
        finally:
            conn.close()


class ReadOnlyEvolutionDbDAL(EvolutionDbDAL):
    def save_loadouts_batch(
        self,
        song_name: str,
        entries: Sequence[Mapping[str, Any]],
        *,
        team_buff: str = "T5",
        preserve_attempt_meta: bool = False,
    ) -> None:
        raise NotImplementedError("Read-only DAL does not support save_loadouts_batch().")

    def save_team_buff_loadouts_batch(
        self,
        song_name: str,
        team_buff: str,
        entries: Sequence[Mapping[str, Any]],
        *,
        preserve_attempt_meta: bool = False,
    ) -> None:
        raise NotImplementedError("Read-only DAL does not support save_team_buff_loadouts_batch().")

    def update_song_counters(self, song_name: str, attempts: int = 1, records: int = 0) -> None:
        raise NotImplementedError("Read-only DAL does not support update_song_counters().")
