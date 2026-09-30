"""The results database schema (version 19) and its connections.

One `loadouts` row per loadout of a song and TeamBuff tier holds both boards' results (see records.py).
Version 18 (two leaderboard tables + name-id tables) is migrated by store.v18.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

VERSION = 19

SONGS_DDL = """
CREATE TABLE songs (
    name TEXT PRIMARY KEY,
    last_updated REAL NOT NULL
) STRICT
"""

LOADOUTS_DDL = """
CREATE TABLE loadouts (
    song_name TEXT NOT NULL REFERENCES songs (name),
    team_buff TEXT NOT NULL,
    loadout_hash TEXT NOT NULL,
    gear TEXT NOT NULL,
    minis TEXT NOT NULL,
    primary_color TEXT NOT NULL,
    secondary_color TEXT NOT NULL,
    mini_ascension TEXT,
    score INTEGER NOT NULL,
    fg_score INTEGER,
    meta_updated INTEGER,
    meta_seq INTEGER,
    meta_result TEXT,
    fg_updated INTEGER,
    fg_seq INTEGER,
    fg_result TEXT,
    meta_trace BLOB,
    fg_trace BLOB,
    PRIMARY KEY (song_name, team_buff, loadout_hash),
    CHECK ((meta_result IS NULL) = (meta_updated IS NULL) AND (meta_result IS NULL) = (meta_seq IS NULL)),
    CHECK (meta_trace IS NULL OR meta_result IS NOT NULL),
    CHECK ((fg_result IS NULL) = (fg_updated IS NULL) AND (fg_result IS NULL) = (fg_seq IS NULL)),
    CHECK ((fg_result IS NULL) = (fg_trace IS NULL)),
    CHECK (fg_result IS NULL OR fg_score IS NOT NULL),
    CHECK (meta_result IS NOT NULL OR fg_result IS NOT NULL)
) STRICT
"""

# Covering the board orders (store.boards), so a board read walks one index.
INDEXES_DDL = (
    """
    CREATE INDEX loadouts_meta_board ON loadouts
        (song_name, team_buff, score DESC, fg_score DESC, meta_updated DESC, meta_seq)
        WHERE meta_result IS NOT NULL
    """,
    """
    CREATE INDEX loadouts_fg_board ON loadouts
        (song_name, team_buff, fg_score DESC, score DESC, fg_updated DESC, fg_seq)
        WHERE fg_result IS NOT NULL
    """,
)

TABLES = ("songs", "loadouts")


class StoreVersionError(RuntimeError):
    pass


def connect(path: str | os.PathLike[str], *, write: bool = False, timeout: float = 30.0) -> sqlite3.Connection:
    """Open the results database. A writer creates or migrates it; a reader requires the current version."""
    if write:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(os.fspath(path), timeout=timeout)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        ensure_schema(conn)
        return conn
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=timeout)
    conn.row_factory = sqlite3.Row
    found = user_version(conn)
    if found != VERSION:
        conn.close()
        raise StoreVersionError(f"{path} is results database version {found}; this engine reads version {VERSION}")
    return conn


def user_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def create_tables(conn: sqlite3.Connection) -> None:
    conn.execute(SONGS_DDL)
    conn.execute(LOADOUTS_DDL)
    for ddl in INDEXES_DDL:
        conn.execute(ddl)


def ensure_schema(conn: sqlite3.Connection) -> None:
    found = user_version(conn)
    if found == VERSION:
        missing = set(TABLES) - _tables(conn)
        if missing:
            raise StoreVersionError(f"results database version {VERSION} is missing tables {sorted(missing)}")
        return
    if found == 0 and not _tables(conn):
        conn.execute("BEGIN IMMEDIATE")
        create_tables(conn)
        conn.execute(f"PRAGMA user_version = {VERSION}")
        conn.commit()
        return
    if found == 18:
        from .v18 import migrate

        migrate(conn, keep_v18_tables=False)
        return
    raise StoreVersionError(f"results database version {found} is not supported (this engine uses {VERSION})")


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
    return {row[0] for row in rows}
