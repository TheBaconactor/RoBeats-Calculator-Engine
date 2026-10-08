"""The results database's tables (version 20): their DDL, and how a row (store.records) is written into them.

One `loadouts` row per loadout of a song, timing mode and TeamBuff tier holds its results and its board membership
(see records.py); an FG replay can be stored without an FG result (version 18 kept only the replay of some). Both
timing modes live side by side: every key starts with the mode.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from .boards import Row
from .records import encode_fg, encode_groups, encode_meta, encode_names

VERSION = 20

SONGS_DDL = """
CREATE TABLE songs (
    timing_mode TEXT NOT NULL,
    name TEXT NOT NULL,
    last_updated REAL NOT NULL,
    PRIMARY KEY (timing_mode, name)
) STRICT
"""

LOADOUTS_DDL = """
CREATE TABLE loadouts (
    timing_mode TEXT NOT NULL,
    song_name TEXT NOT NULL,
    team_buff TEXT NOT NULL,
    loadout_hash TEXT NOT NULL,
    gear TEXT NOT NULL,
    minis TEXT NOT NULL,
    primary_color TEXT NOT NULL,
    secondary_color TEXT NOT NULL,
    mini_ascension TEXT,
    score INTEGER NOT NULL,
    fg_score INTEGER,
    meta_board INTEGER NOT NULL,
    fg_board INTEGER NOT NULL,
    meta_updated INTEGER,
    meta_seq INTEGER,
    meta_result TEXT,
    fg_updated INTEGER,
    fg_seq INTEGER,
    fg_result TEXT,
    meta_trace BLOB,
    fg_trace BLOB,
    PRIMARY KEY (timing_mode, song_name, team_buff, loadout_hash),
    FOREIGN KEY (timing_mode, song_name) REFERENCES songs (timing_mode, name),
    CHECK (meta_board IN (0, 1) AND fg_board IN (0, 1) AND meta_board + fg_board > 0),
    CHECK ((meta_result IS NULL) = (meta_updated IS NULL) AND (meta_result IS NULL) = (meta_seq IS NULL)),
    CHECK (meta_board = 0 OR meta_result IS NOT NULL),
    CHECK (meta_trace IS NULL OR meta_result IS NOT NULL),
    CHECK ((fg_result IS NULL) = (fg_updated IS NULL) AND (fg_result IS NULL) = (fg_seq IS NULL)),
    CHECK (fg_board = 0 OR (fg_result IS NOT NULL AND fg_score > score)),
    CHECK (fg_result IS NULL OR fg_trace IS NOT NULL),
    CHECK (fg_trace IS NULL OR fg_score IS NOT NULL)
) STRICT
"""

# Covering the board orders (store.boards), so a board read walks one index; and the entry numbers, so a write
# finds the next one without scanning the table.
INDEXES_DDL = (
    """
    CREATE INDEX loadouts_meta_board ON loadouts
        (timing_mode, song_name, team_buff, score DESC, fg_score DESC, meta_updated DESC, meta_seq)
        WHERE meta_board = 1
    """,
    """
    CREATE INDEX loadouts_fg_board ON loadouts
        (timing_mode, song_name, team_buff, fg_score DESC, score DESC, fg_updated DESC, fg_seq)
        WHERE fg_board = 1
    """,
    "CREATE INDEX loadouts_meta_seq ON loadouts (meta_seq)",
    "CREATE INDEX loadouts_fg_seq ON loadouts (fg_seq)",
)

TABLES = ("songs", "loadouts")

# A read-only connection cannot rebuild the WAL index, so every open rescans a leftover WAL (4 ms at 16 MiB, 15 ms
# at 64 MiB, 90 ms at 388 MiB; measured 09-30): a write session truncates it, waiting this long at most for readers.
TRUNCATE_WAIT_MS = 1000

# A row's columns after its timing mode (what a query that fixes the mode reads; a version 19 row's), with its traces,
# and with the mode.
MODELESS_COLUMNS = (
    "song_name, team_buff, loadout_hash, gear, minis, primary_color, secondary_color, mini_ascension, score, fg_score,"
    " meta_board, fg_board, meta_updated, meta_seq, meta_result, fg_updated, fg_seq, fg_result"
)
MODELESS_ROW_COLUMNS = MODELESS_COLUMNS + ", meta_trace, fg_trace"
ROW_COLUMNS = "timing_mode, " + MODELESS_ROW_COLUMNS


def user_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def create_tables(conn: sqlite3.Connection) -> None:
    conn.execute(SONGS_DDL)
    conn.execute(LOADOUTS_DDL)
    for ddl in INDEXES_DDL:
        conn.execute(ddl)


def truncate_wal(conn: sqlite3.Connection) -> None:
    """End a write session: checkpoint the write-ahead log and truncate it to zero bytes. A reader still on the log
    makes it give up after TRUNCATE_WAIT_MS (the committed write stands; the next write session truncates)."""
    timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    conn.execute(f"PRAGMA busy_timeout = {TRUNCATE_WAIT_MS}")
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    finally:
        conn.execute(f"PRAGMA busy_timeout = {timeout}")


def insert_rows(conn: sqlite3.Connection, rows: Iterable[Row]) -> None:
    conn.executemany(
        f"INSERT INTO loadouts ({ROW_COLUMNS}) VALUES ({', '.join(['?'] * 21)})", (_values(row) for row in rows)
    )


def insert_song(conn: sqlite3.Connection, mode: str, song: str, last_updated_at: float) -> None:
    conn.execute("INSERT INTO songs (timing_mode, name, last_updated) VALUES (?, ?, ?)", (mode, song, last_updated_at))


def _values(row: Row) -> tuple:
    x = row.loadout
    return (
        x.mode,
        x.song,
        x.tier,
        x.loadout_hash,
        encode_names(x.gear),
        encode_groups(x.minis),
        x.primary,
        x.secondary,
        x.mini_ascension,
        x.score,
        x.fg_score,
        int(x.on_meta),
        int(x.on_fg),
        None if x.meta is None else x.meta.updated,
        None if x.meta is None else x.meta.seq,
        None if x.meta is None else encode_meta(x.meta),
        None if x.fg is None else x.fg.updated,
        None if x.fg is None else x.fg.seq,
        None if x.fg is None else encode_fg(x.fg),
        row.meta_trace,
        row.fg_trace,
    )
