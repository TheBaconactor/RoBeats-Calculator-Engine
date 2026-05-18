from __future__ import annotations

import logging
import sqlite3
import threading
from typing import Sequence

from .encoding_maps import EncodingMaps
from .loadout_equivalence import get_gears_by_name_cached, get_minis_by_name_cached

logger = logging.getLogger(__name__)

_GEAR_NAME_ENCODING_TABLE = "gear_name_encoding"
_MINI_NAME_ENCODING_TABLE = "mini_name_encoding"
_PIECE_ENCODING_CACHE_LOCK = threading.Lock()
_PIECE_ENCODING_CACHE: dict[str, EncodingMaps] = {}


def _encoding_table_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0] or 0) if row else 0
    except sqlite3.Error:
        return 0


def _load_piece_name_encoding_maps(conn: sqlite3.Connection, *, db_path: str) -> EncodingMaps:
    """
    Load (and cache) piece name <-> id maps for a DB path.

    Cache is refreshed when the encoding tables' row counts change.
    """
    db_path = str(db_path)
    gear_count = _encoding_table_count(conn, _GEAR_NAME_ENCODING_TABLE)
    mini_count = _encoding_table_count(conn, _MINI_NAME_ENCODING_TABLE)

    with _PIECE_ENCODING_CACHE_LOCK:
        cached = _PIECE_ENCODING_CACHE.get(db_path)
        if (
            cached is not None
            and int(cached.gear_count) == int(gear_count)
            and int(cached.mini_count) == int(mini_count)
        ):
            return cached

    gear_name_to_id: dict[str, int] = {}
    gear_id_to_name: dict[int, str] = {}
    mini_name_to_id: dict[str, int] = {}
    mini_id_to_name: dict[int, str] = {}

    try:
        rows = conn.execute(f"SELECT id, name FROM {_GEAR_NAME_ENCODING_TABLE}").fetchall()
        for r in rows:
            try:
                i = int(r[0] or 0)
                n = str(r[1] or "")
            except Exception as e:
                logger.warning(f"database:_load_piece_name_encoding_maps: {e}")
                continue
            if i > 0 and n:
                gear_name_to_id[n] = i
                gear_id_to_name[i] = n
    except sqlite3.Error:
        pass

    try:
        rows = conn.execute(f"SELECT id, name FROM {_MINI_NAME_ENCODING_TABLE}").fetchall()
        for r in rows:
            try:
                i = int(r[0] or 0)
                n = str(r[1] or "")
            except Exception as e:
                logger.warning(f"database:_load_piece_name_encoding_maps: {e}")
                continue
            if i > 0 and n:
                mini_name_to_id[n] = i
                mini_id_to_name[i] = n
    except sqlite3.Error:
        pass

    maps = EncodingMaps(
        gear_name_to_id=gear_name_to_id,
        gear_id_to_name=gear_id_to_name,
        mini_name_to_id=mini_name_to_id,
        mini_id_to_name=mini_id_to_name,
        gear_count=int(gear_count),
        mini_count=int(mini_count),
    )
    with _PIECE_ENCODING_CACHE_LOCK:
        _PIECE_ENCODING_CACHE[db_path] = maps
    return maps


def _insert_missing_piece_names(
    conn: sqlite3.Connection,
    *,
    table: str,
    names: Sequence[str],
) -> None:
    if not names:
        return
    cleaned = sorted({str(n).strip() for n in (names or []) if str(n).strip()})
    if not cleaned:
        return

    try:
        existing = {str(r[0]) for r in conn.execute(f"SELECT name FROM {table}").fetchall() if r and r[0]}
    except sqlite3.Error:
        existing = set()
    missing = [n for n in cleaned if n not in existing]
    if not missing:
        return

    try:
        row = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table}").fetchone()
        max_id = int(row[0] or 0) if row else 0
    except sqlite3.Error:
        max_id = 0

    params = [(max_id + idx + 1, n) for idx, n in enumerate(missing)]
    try:
        conn.executemany(
            f"INSERT INTO {table} (id, name) VALUES (?, ?) ON CONFLICT(name) DO NOTHING",
            params,
        )
    except sqlite3.Error:
        # Fallback for older SQLite builds lacking ON CONFLICT DO NOTHING syntax.
        try:
            conn.executemany(f"INSERT OR IGNORE INTO {table} (id, name) VALUES (?, ?)", params)
        except sqlite3.Error:
            return


def _initialize_piece_name_encodings(conn: sqlite3.Connection, *, db_path: str) -> None:
    """
    Populate encoding tables deterministically (sorted) from the known dataset.

    This is best-effort: failures must not block optimizer startup.
    """
    try:
        gears_by_name = get_gears_by_name_cached()
        minis_by_name = get_minis_by_name_cached()
    except Exception as e:
        logger.warning(f"database:_initialize_piece_name_encodings: {e}")
        return

    gear_names = sorted([str(k).strip() for k in (gears_by_name or {}).keys() if str(k).strip()])
    mini_names = sorted([str(k).strip() for k in (minis_by_name or {}).keys() if str(k).strip()])

    if gear_names:
        _insert_missing_piece_names(conn, table=_GEAR_NAME_ENCODING_TABLE, names=gear_names)
    if mini_names:
        _insert_missing_piece_names(conn, table=_MINI_NAME_ENCODING_TABLE, names=mini_names)

    with _PIECE_ENCODING_CACHE_LOCK:
        _PIECE_ENCODING_CACHE.pop(str(db_path), None)
