"""
SQLite schema versioning for the evolution database.

We use `PRAGMA user_version` as the single source of truth for schema state.

Note: This repo intentionally does NOT provide or maintain historical view-based schemas.
Consumers should use `gear_optimizer.data.db_manager.EvolutionDbManager` for reads.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Callable, Dict
import logging


logger = logging.getLogger(__name__)
Migration = Callable[[sqlite3.Connection], None]

# NOTE: `evolution.db` in the wild may already have `PRAGMA user_version=8` even though
# the physical schema matches v6 (v6 is a data-level migration only). Keep v7/v8 as
# no-ops so older DBs can advance and newer DBs won't be rejected.
LATEST_SCHEMA_VERSION = 18

_GEAR_NAME_ENCODING_TABLE = "gear_name_encoding"
_MINI_NAME_ENCODING_TABLE = "mini_name_encoding"


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (str(table),),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except sqlite3.Error:
        return set()
    out: set[str] = set()
    for row in rows or []:
        try:
            name = str(row[1] or "").strip()
        except Exception as e:
            logger.debug(f"__init__:_table_columns: {e}")
            name = ""
        if name:
            out.add(name)
    return out


def _add_column_if_missing(conn: sqlite3.Connection, *, table: str, column: str, column_sql: str) -> None:
    if column in _table_columns(conn, table):
        return
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column_sql}")
    except sqlite3.Error:
        pass


def _load_json(payload: object, *, default: object) -> object:
    if payload is None:
        return default
    if isinstance(payload, (list, dict)):
        return payload
    text = str(payload or "").strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception as e:
        logger.debug(f"__init__:_load_json: {e}")
        return default


def _decode_historical_gear_names(payload: object) -> list[str]:
    raw = _load_json(payload, default=[])
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        name = str(item or "").strip()
        if name:
            out.append(name)
    return out


def _decode_historical_mini_groups(payload: object) -> list[list[str]]:
    raw = _load_json(payload, default=[])
    if not isinstance(raw, list):
        return []
    out: list[list[str]] = []
    for item in raw:
        if isinstance(item, list):
            names = [str(name or "").strip() for name in item]
            names = [name for name in names if name]
            if names:
                out.append(names)
            continue
        name = str(item or "").strip()
        if name:
            out.append([name])
    return out


def _encode_uvarint(value: int) -> bytes:
    x = int(value)
    if x < 0:
        raise ValueError("uvarint cannot encode negative values")
    out = bytearray()
    while True:
        b = x & 0x7F
        x >>= 7
        if x:
            out.append(int(b | 0x80))
        else:
            out.append(int(b))
            break
    return bytes(out)


def _pack_id_list(ids: list[int]) -> bytes:
    if not ids:
        return b""
    buf = bytearray()
    for value in ids:
        iv = int(value)
        if iv <= 0:
            continue
        buf += _encode_uvarint(iv)
    return bytes(buf)


def _pack_id_groups(groups: list[list[int]]) -> bytes:
    if not groups:
        return b""
    buf = bytearray()
    for group in groups:
        if not group:
            continue
        for value in group:
            iv = int(value)
            if iv <= 0:
                continue
            buf += _encode_uvarint(iv)
        buf += b"\x00"
    return bytes(buf)


def _insert_missing_encoding_names(conn: sqlite3.Connection, *, table: str, names: set[str]) -> None:
    cleaned = sorted({str(name).strip() for name in (names or set()) if str(name).strip()})
    if not cleaned:
        return

    existing_rows = conn.execute(f"SELECT id, name FROM {table}").fetchall()
    existing_names = {str(row[1] or "").strip() for row in existing_rows or [] if row and row[1]}
    if all(name in existing_names for name in cleaned):
        return

    try:
        row = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}").fetchone()
        next_id = int(row[0] or 0) + 1 if row else 1
    except sqlite3.Error:
        next_id = 1

    params: list[tuple[int, str]] = []
    for name in cleaned:
        if name in existing_names:
            continue
        params.append((int(next_id), name))
        existing_names.add(name)
        next_id += 1

    if not params:
        return

    try:
        conn.executemany(
            f"INSERT INTO {table} (id, name) VALUES (?, ?) ON CONFLICT(name) DO NOTHING",
            params,
        )
    except sqlite3.Error:
        conn.executemany(f"INSERT OR IGNORE INTO {table} (id, name) VALUES (?, ?)", params)


def _encoding_name_to_id(conn: sqlite3.Connection, table: str) -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        rows = conn.execute(f"SELECT id, name FROM {table}").fetchall()
    except sqlite3.Error:
        return out
    for row in rows or []:
        try:
            idx = int(row[0] or 0)
            name = str(row[1] or "").strip()
        except Exception as e:
            logger.debug(f"__init__:_encoding_name_to_id: {e}")
            continue
        if idx > 0 and name:
            out[name] = idx
    return out


def _backfill_historical_piece_blobs(conn: sqlite3.Connection, *, table: str) -> None:
    if not _table_exists(conn, table):
        return

    _add_column_if_missing(conn, table=table, column="gear_ids_blob", column_sql="gear_ids_blob BLOB")
    _add_column_if_missing(conn, table=table, column="minis_ids_blob", column_sql="minis_ids_blob BLOB")

    columns = _table_columns(conn, table)
    if "gear_json" not in columns or "minis_json" not in columns:
        return

    try:
        rows = conn.execute(
            f"""
            SELECT rowid, gear_json, minis_json, gear_ids_blob, minis_ids_blob
            FROM {table}
            WHERE COALESCE(length(gear_ids_blob), 0) = 0
               OR COALESCE(length(minis_ids_blob), 0) = 0
            """
        ).fetchall()
    except sqlite3.Error:
        return
    if not rows:
        return

    gear_names: set[str] = set()
    mini_names: set[str] = set()
    decoded_rows: list[tuple[int, list[str], list[list[str]], object, object]] = []
    for row in rows:
        try:
            rowid = int(row[0] or 0)
        except Exception as e:
            logger.debug(f"__init__:_backfill_historical_piece_blobs: {e}")
            rowid = 0
        if rowid <= 0:
            continue
        gears = _decode_historical_gear_names(row[1])
        minis = _decode_historical_mini_groups(row[2])
        gear_names.update(gears)
        for group in minis:
            mini_names.update(group)
        decoded_rows.append((rowid, gears, minis, row[3], row[4]))

    _insert_missing_encoding_names(conn, table=_GEAR_NAME_ENCODING_TABLE, names=gear_names)
    _insert_missing_encoding_names(conn, table=_MINI_NAME_ENCODING_TABLE, names=mini_names)

    gear_name_to_id = _encoding_name_to_id(conn, _GEAR_NAME_ENCODING_TABLE)
    mini_name_to_id = _encoding_name_to_id(conn, _MINI_NAME_ENCODING_TABLE)

    updates: list[tuple[bytes | None, bytes | None, int]] = []
    for rowid, gears, minis, gear_blob, mini_blob in decoded_rows:
        new_gear_blob = gear_blob
        if not new_gear_blob:
            ids = [int(gear_name_to_id.get(name, 0) or 0) for name in gears]
            ids = [idx for idx in ids if idx > 0]
            new_gear_blob = _pack_id_list(ids) or None

        new_mini_blob = mini_blob
        if not new_mini_blob:
            id_groups: list[list[int]] = []
            for group in minis:
                ids = [int(mini_name_to_id.get(name, 0) or 0) for name in group]
                ids = [idx for idx in ids if idx > 0]
                if ids:
                    id_groups.append(ids)
            new_mini_blob = _pack_id_groups(id_groups) or None

        updates.append((new_gear_blob, new_mini_blob, int(rowid)))

    if not updates:
        return

    conn.executemany(
        f"UPDATE {table} SET gear_ids_blob = ?, minis_ids_blob = ? WHERE rowid = ?",
        updates,
    )


def _ensure_compact_piece_storage_postconditions(conn: sqlite3.Connection) -> None:
    conn.executescript(
        f"""
        CREATE TABLE IF NOT EXISTS {_GEAR_NAME_ENCODING_TABLE} (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS {_MINI_NAME_ENCODING_TABLE} (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        """
    )
    _backfill_historical_piece_blobs(conn, table="team_buff_loadouts")
    _backfill_historical_piece_blobs(conn, table="team_buff_fg_loadouts")


def _migration_1_init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS songs (
            name TEXT PRIMARY KEY,
            best_score INTEGER DEFAULT 0,
            best_fg_score INTEGER DEFAULT 0,
            last_updated REAL
        );
        """
    )


def _migration_2_add_pending_fg_jobs(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS pending_fg_jobs (
            song_name TEXT PRIMARY KEY,
            candidates_json TEXT NOT NULL,
            created_ts REAL,
            updated_ts REAL
        );

        CREATE INDEX IF NOT EXISTS idx_pending_fg_jobs_updated
            ON pending_fg_jobs (updated_ts DESC);
        """
    )


def _migration_3_noop(conn: sqlite3.Connection) -> None:
    """
    No-op migration (schema version continuity).

    Schema version 3 was used by an experimental feature that has since been removed.
    """
    return


def _migration_4_noop(conn: sqlite3.Connection) -> None:
    """
    No-op migration (schema version continuity).

    Schema version 4 was used by an experimental feature that has since been removed.
    """
    return


def _migration_5_cleanup(conn: sqlite3.Connection) -> None:
    """
    Cleanup migration (schema version continuity).

    Drops unused tables from older experimental schemas (best-effort).
    """
    try:
        conn.execute("DROP TABLE IF EXISTS pending_swing_jobs;")
    except sqlite3.Error:
        pass
    return


def _migration_6_noop(conn: sqlite3.Connection) -> None:
    """No-op (deprecated loadout tables removed)."""
    return


def _migration_7_noop(conn: sqlite3.Connection) -> None:
    """
    No-op migration (schema version continuity).

    Schema version 7 did not introduce any physical schema changes in this repo.
    """
    return


def _migration_8_noop(conn: sqlite3.Connection) -> None:
    """
    No-op migration (schema version continuity).

    Schema version 8 did not introduce any physical schema changes in this repo.
    """
    return


def _migration_9_add_team_buff_tier_tables(conn: sqlite3.Connection) -> None:
    """
    Add TeamBuff-tiered leaderboards.

    These tables are the canonical base/FG leaderboards, partitioned by `team_buff`.
    The compact workflow stores gear/minis via encoding-table IDs in BLOB columns.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS team_buff_loadouts (
            song_name TEXT,
            team_buff TEXT,
            loadout_hash TEXT,
            score INTEGER,
            fg_score INTEGER DEFAULT 0,
            gear_ids_blob BLOB,
            minis_ids_blob BLOB,
            details_json TEXT,
            force_details_json TEXT,
            timestamp REAL,
            PRIMARY KEY (song_name, team_buff, loadout_hash),
            FOREIGN KEY (song_name) REFERENCES songs(name)
        );

        CREATE TABLE IF NOT EXISTS team_buff_fg_loadouts (
            song_name TEXT,
            team_buff TEXT,
            loadout_hash TEXT,
            score INTEGER, -- Base score context under this TeamBuff tier
            fg_score INTEGER,
            gear_ids_blob BLOB,
            minis_ids_blob BLOB,
            details_json TEXT,
            force_details_json TEXT,
            timestamp REAL,
            PRIMARY KEY (song_name, team_buff, loadout_hash),
            FOREIGN KEY (song_name) REFERENCES songs(name)
        );

        CREATE INDEX IF NOT EXISTS idx_team_buff_loadouts_score
            ON team_buff_loadouts (song_name, team_buff, score DESC);
        CREATE INDEX IF NOT EXISTS idx_team_buff_loadouts_fg_score
            ON team_buff_loadouts (song_name, team_buff, fg_score DESC);
        CREATE INDEX IF NOT EXISTS idx_team_buff_fg_loadouts_score
            ON team_buff_fg_loadouts (song_name, team_buff, fg_score DESC);
        """
    )


def _migration_10_add_song_attempt_counters(conn: sqlite3.Connection) -> None:
    """
    Add per-song attempt counters.

    - `attempt_lifetime`: increments once per processed run, monotonically.
    - `attempts_first`: increments once per processed run but resets to 1 on any
      new base OR FG record (per-song).
    """
    for stmt in (
        "ALTER TABLE songs ADD COLUMN attempt_lifetime INTEGER DEFAULT 0;",
        "ALTER TABLE songs ADD COLUMN attempts_first INTEGER DEFAULT 0;",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.Error:
            # Likely: duplicate column name (already migrated).
            pass


def _migration_11_noop(conn: sqlite3.Connection) -> None:
    """No-op (team_buff tables already include tier metadata)."""
    return


def _migration_12_noop(conn: sqlite3.Connection) -> None:
    """Removed: historical SQL views."""
    return


def _migration_13_noop(conn: sqlite3.Connection) -> None:
    """Removed: historical frontend SQL views."""
    return


def _migration_14_noop(conn: sqlite3.Connection) -> None:
    """Removed: historical frontend SQL views."""
    return


def _migration_15_noop(conn: sqlite3.Connection) -> None:
    """Removed: historical unified/frontend SQL views."""
    return


def _migration_16_drop_deprecated_tables(conn: sqlite3.Connection) -> None:
    """Drop deprecated base/FG tables (best-effort)."""
    for stmt in (
        "DROP INDEX IF EXISTS idx_loadouts_score;",
        "DROP INDEX IF EXISTS idx_loadouts_fg_score;",
        "DROP INDEX IF EXISTS idx_fg_loadouts_score;",
        "DROP INDEX IF EXISTS idx_fg_loadouts_team_buff;",
        "DROP TABLE IF EXISTS loadouts;",
        "DROP TABLE IF EXISTS fg_loadouts;",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.Error:
            pass
    return


def _migration_17_noop(conn: sqlite3.Connection) -> None:
    """Removed: historical color-aware frontend SQL views."""
    return


def _migration_18_add_piece_name_encoding_tables(conn: sqlite3.Connection) -> None:
    """
    Add compact name encodings for gear/minis.

    These tables de-duplicate repeated piece names across rows.
    """
    _ensure_compact_piece_storage_postconditions(conn)


_MIGRATIONS: Dict[int, Migration] = {
    1: _migration_1_init_schema,
    2: _migration_2_add_pending_fg_jobs,
    3: _migration_3_noop,
    4: _migration_4_noop,
    5: _migration_5_cleanup,
    6: _migration_6_noop,
    7: _migration_7_noop,
    8: _migration_8_noop,
    9: _migration_9_add_team_buff_tier_tables,
    10: _migration_10_add_song_attempt_counters,
    11: _migration_11_noop,
    12: _migration_12_noop,
    13: _migration_13_noop,
    14: _migration_14_noop,
    15: _migration_15_noop,
    16: _migration_16_drop_deprecated_tables,
    17: _migration_17_noop,
    18: _migration_18_add_piece_name_encoding_tables,
}


def get_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version;").fetchone()
    if not row:
        return 0
    return int(row[0] or 0)


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {int(version)};")


def ensure_schema(conn: sqlite3.Connection) -> None:
    current = get_schema_version(conn)
    if current > LATEST_SCHEMA_VERSION:
        raise RuntimeError(f"DB schema version {current} is newer than this app supports ({LATEST_SCHEMA_VERSION}).")

    with conn:
        if current < LATEST_SCHEMA_VERSION:
            for version in range(current + 1, LATEST_SCHEMA_VERSION + 1):
                migration = _MIGRATIONS.get(version)
                if migration is None:
                    raise RuntimeError(f"Missing migration for schema version {version}.")
                migration(conn)
                set_schema_version(conn, version)

        # Repair malformed/partially-upgraded DBs where user_version reached 18 before
        # compact blob columns were actually added/backfilled.
        _ensure_compact_piece_storage_postconditions(conn)
