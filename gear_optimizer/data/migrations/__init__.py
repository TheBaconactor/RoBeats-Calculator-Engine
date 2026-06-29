from __future__ import annotations

import sqlite3

LATEST_SCHEMA_VERSION = 18


_CURRENT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS songs (
    name TEXT PRIMARY KEY,
    best_score INTEGER DEFAULT 0,
    best_fg_score INTEGER DEFAULT 0,
    last_updated REAL,
    attempt_lifetime INTEGER DEFAULT 0,
    attempts_first INTEGER DEFAULT 0
);

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
    score INTEGER,
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

CREATE TABLE IF NOT EXISTS gear_name_encoding (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS mini_name_encoding (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
"""

_REQUIRED_COLUMNS: dict[str, set[str]] = {
    "songs": {"name", "best_score", "best_fg_score", "last_updated", "attempt_lifetime", "attempts_first"},
    "team_buff_loadouts": {
        "song_name",
        "team_buff",
        "loadout_hash",
        "score",
        "fg_score",
        "gear_ids_blob",
        "minis_ids_blob",
        "details_json",
        "force_details_json",
        "timestamp",
    },
    "team_buff_fg_loadouts": {
        "song_name",
        "team_buff",
        "loadout_hash",
        "score",
        "fg_score",
        "gear_ids_blob",
        "minis_ids_blob",
        "details_json",
        "force_details_json",
        "timestamp",
    },
    "gear_name_encoding": {"id", "name"},
    "mini_name_encoding": {"id", "name"},
}


def get_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version;").fetchone()
    if not row:
        return 0
    return int(row[0] or 0)


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {int(version)};")


def _user_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()
    return {str(row[0] or "") for row in rows or [] if row and row[0]}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return str(table) in _user_tables(conn)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {str(row[1] or "") for row in rows or [] if row and row[1]}


def _create_current_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_CURRENT_SCHEMA_SQL)


def _validate_current_schema(conn: sqlite3.Connection) -> None:
    existing_tables = _user_tables(conn)
    missing_tables = sorted(set(_REQUIRED_COLUMNS) - existing_tables)
    if missing_tables:
        raise RuntimeError(f"DB schema is missing required current tables: {', '.join(missing_tables)}")

    missing_columns: list[str] = []
    for table, required in sorted(_REQUIRED_COLUMNS.items()):
        missing = sorted(required - _table_columns(conn, table))
        if missing:
            missing_columns.append(f"{table}({', '.join(missing)})")
    if missing_columns:
        raise RuntimeError(f"DB schema is missing required current columns: {'; '.join(missing_columns)}")


def ensure_schema(conn: sqlite3.Connection) -> None:
    current = get_schema_version(conn)
    if current > LATEST_SCHEMA_VERSION:
        raise RuntimeError(f"DB schema version {current} is newer than this app supports ({LATEST_SCHEMA_VERSION}).")

    with conn:
        if current == 0:
            if _user_tables(conn):
                raise RuntimeError("Unversioned existing DB schema is not supported; rebuild or migrate it explicitly.")
            _create_current_schema(conn)
            set_schema_version(conn, LATEST_SCHEMA_VERSION)
            return

        if current != LATEST_SCHEMA_VERSION:
            raise RuntimeError(
                f"Legacy DB schema version {current} is not supported; rebuild or migrate to {LATEST_SCHEMA_VERSION}."
            )

        _validate_current_schema(conn)
