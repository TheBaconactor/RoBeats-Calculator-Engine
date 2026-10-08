"""Connections to the results database: a writer creates its tables (store.tables) or migrates version 19 (one
timing mode per file: store.v19); a reader requires the current version.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from . import v19
from .tables import TABLES, VERSION, create_tables, user_version

JOURNAL_SIZE_LIMIT = 64 * 1024 * 1024


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
        # A large transaction leaves a WAL that never shrinks on its own, and every reader pays for it on open.
        conn.execute(f"PRAGMA journal_size_limit = {JOURNAL_SIZE_LIMIT}")
        ensure_schema(conn)
        return conn
    conn = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=timeout)
    conn.row_factory = sqlite3.Row
    found = user_version(conn)
    if found != VERSION:
        conn.close()
        raise StoreVersionError(f"{path} is results database version {found}; this engine reads version {VERSION}")
    return conn


def ensure(path: str | os.PathLike[str]) -> None:
    """Create the database, or migrate it to this version, if needed."""
    connect(path, write=True).close()


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
    if found == 19:
        v19.migrate(conn)
        return
    raise StoreVersionError(f"results database version {found} is not supported (this engine uses {VERSION})")


def _tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")
    return {row[0] for row in rows}
