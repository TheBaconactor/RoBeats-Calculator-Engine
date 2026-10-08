"""Results database version 19 (one timing mode per file, no mode column): the migration to version 20.

Every version 19 database holds Precise results: released engines solved charts without a Timing Mode header in
Precise, no catalog chart has one, and the website's optimizer jobs request Precise.
"""

from __future__ import annotations

import sqlite3

from ..core.timing_modes import PRECISE
from .tables import MODELESS_ROW_COLUMNS, VERSION, create_tables


def migrate(conn: sqlite3.Connection) -> None:
    """Move a version 19 database's rows into version 20 tables as Precise rows, in one transaction."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        for name in ("loadouts_meta_board", "loadouts_fg_board", "loadouts_meta_seq", "loadouts_fg_seq"):
            conn.execute(f"DROP INDEX IF EXISTS {name}")
        conn.execute("ALTER TABLE songs RENAME TO songs_v19")
        conn.execute("ALTER TABLE loadouts RENAME TO loadouts_v19")
        create_tables(conn)
        conn.execute("INSERT INTO songs SELECT ?, name, last_updated FROM songs_v19", (PRECISE,))
        conn.execute(
            f"INSERT INTO loadouts (timing_mode, {MODELESS_ROW_COLUMNS}) SELECT ?, {MODELESS_ROW_COLUMNS}"
            " FROM loadouts_v19",
            (PRECISE,),
        )
        conn.execute("DROP TABLE loadouts_v19")
        conn.execute("DROP TABLE songs_v19")
        conn.execute(f"PRAGMA user_version = {VERSION}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    # The migration rewrote every row; truncate the write-ahead log it grew (readers pay for its size on open).
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")  # no wait bound: nothing else writes during a migration
