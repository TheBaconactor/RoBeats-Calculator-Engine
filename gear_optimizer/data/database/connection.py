"""
SQLite connection management for the gear optimizer database package.

Owns evolution DB path resolution, connection factories (read/write, read-only,
per-thread cached), the thread-local connection cache, and schema init.
"""
import os
import sqlite3
import threading
import logging
from typing import Optional
from urllib.parse import quote
from ...core.constants import PATHS
from ..migrations import ensure_schema
from ..piece_encoding_store import _initialize_piece_name_encodings
from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)


def get_evolution_db_path() -> str:
    """
    Return the configured evolution DB location (env override supported).
    Returns:
        str: Path to evolution database file
    """
    env_path = str(env_get("EVOLUTION_DB_PATH", "") or "").strip()
    if env_path:
        return env_path
    try:
        external_db = os.path.abspath(os.path.join(PATHS.script_dir, os.pardir, "ExternalDatabases", "evolution.db"))
        if os.path.exists(external_db):
            return external_db
    except Exception as e:
        logger.warning(f"database:get_evolution_db_path: {e}")
    return PATHS.evolution_db_default


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Create a SQLite connection with optimized settings.
    Args:
        db_path: Optional database path (defaults to evolution DB)
    Returns:
        sqlite3.Connection: Database connection with WAL mode enabled
    """
    return get_db_connection_with_timeout(db_path=db_path)


def get_db_connection_with_timeout(db_path: Optional[str] = None, *, timeout: float = 30.0) -> sqlite3.Connection:
    """
    Create a SQLite connection with optimized settings.
    `timeout` is the maximum time SQLite will wait for a lock before raising.
    """
    if db_path is None:
        db_path = get_evolution_db_path()
    try:
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
    except Exception as e:
        logger.warning(f"database:get_db_connection_with_timeout: {e}")
    conn = sqlite3.connect(db_path, timeout=float(timeout))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    try:
        busy_ms = int(max(100.0, min(float(timeout) * 1000.0, 30_000.0)))
        conn.execute(f"PRAGMA busy_timeout={busy_ms};")
    except Exception as e:
        logger.warning(f"database:get_db_connection_with_timeout: {e}")
    ensure_schema(conn)
    return conn


def _db_path_to_uri(db_path: str) -> str:
    path = os.path.abspath(str(db_path))
    path = path.replace("\\", "/")
    return f"file:{quote(path, safe='/:')}?mode=ro"


def get_db_connection_readonly(db_path: Optional[str] = None, *, timeout: float = 0.0) -> sqlite3.Connection:
    """
    Create a read-only SQLite connection (no PRAGMAs/migrations).
    This is used for read-heavy seed/context fetches where we must never block the GPU feed loop.
    """
    if db_path is None:
        db_path = get_evolution_db_path()
    db_path = str(db_path)
    if not db_path:
        raise sqlite3.OperationalError("Empty db path")
    if not os.path.exists(db_path):
        raise sqlite3.OperationalError("DB not found")
    uri = _db_path_to_uri(db_path)
    conn = sqlite3.connect(uri, timeout=float(timeout), uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=1;")
    except Exception as e:
        logger.warning(f"database:get_db_connection_readonly: {e}")
    return conn


_DB_TLS = threading.local()


def get_db_connection_cached(db_path: Optional[str] = None) -> sqlite3.Connection:
    """
    Return a per-thread cached SQLite connection.
    This keeps exact query semantics while avoiding per-call reconnect + PRAGMA + migration
    overhead on read-heavy call sites (e.g., per-song progress/context reads).
    """
    if db_path is None:
        db_path = get_evolution_db_path()
    try:
        conns = getattr(_DB_TLS, "conns", None)
        if conns is None:
            conns = {}
            setattr(_DB_TLS, "conns", conns)
    except Exception as e:
        logger.warning(f"database:get_db_connection_cached: {e}")
        conns = {}
    db_path = str(db_path)
    conn = conns.get(db_path)
    if conn is not None:
        return conn
    read_timeout = 0.2
    # Resolve `get_db_connection_readonly` through the package facade at call time
    # so a monkeypatch of `gear_optimizer.data.database.get_db_connection_readonly`
    # is honored here, exactly as in the pre-split monolith where this was a
    # module-level name.
    from gear_optimizer.data import database as _db
    conn = _db.get_db_connection_readonly(db_path, timeout=read_timeout)
    conns[db_path] = conn
    return conn


def init_db():
    """
    Initialize the SQLite database schema if it doesn't exist.
    Storage optimization (compact/default `evolution.db`):
    - Gear + minis are persisted as compact integer IDs via:
      - encoding tables: `gear_name_encoding`, `mini_name_encoding`
      - BLOB columns: `gear_ids_blob`, `minis_ids_blob`
    - `details_json` stores packed Stats as `st` (fixed-order int list) instead of verbose `Stats` keys.
    """
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        try:
            _initialize_piece_name_encodings(conn, db_path=str(db_path))
        except Exception as e:
            logger.warning(f"database:init_db: {e}")
        conn.commit()
    finally:
        conn.close()
