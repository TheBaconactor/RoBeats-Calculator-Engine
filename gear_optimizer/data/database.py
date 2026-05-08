"""
Database operations for the gear optimizer.
Handles all SQLite interactions for loadout persistence and retrieval.
"""

import re
import json
import os
import sqlite3
import time
import threading
import atexit
import weakref
import warnings
from collections.abc import Iterable
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.parse import quote
import logging

from ..core.constants import LOADOUTS_PER_SONG_LIMIT, PATHS
from ..core.fallback_monitor import warn_fallback
from ..core.gem_defs import GEM_KEYS, STAT_KEYS, fg_score_from_force
from ..core.parsing import env_flag
from ..core.utils import safe_int as _safe_int_for_db
from ..core.team_buff import (
    canonicalize_team_buff,
    normalize_team_buff,
    team_buff_effect,
    team_buff_query_values,
)
from ..core.types import PersistenceEntry
from .migrations import ensure_schema
from .encoding_maps import EncodingMaps
from .loadout_equivalence import (
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    extract_song_colors,
    get_minis_by_name_cached,
    get_gears_by_name_cached,
    canonical_minis_groups_from_names,
    representative_mini_names,
    rotate_mini_groups_for_slot_display,
)

from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)
try:
    import orjson as _orjson
except Exception:  # pragma: no cover - optional dependency
    _orjson = None


def _json_dumps_compact(value: Any) -> str:
    """Serialize JSON using compact separators, with optional orjson acceleration."""
    if _orjson is not None:
        return _orjson.dumps(value).decode("utf-8")
    return json.dumps(value, separators=(",", ":"))


def _json_loads(value: Any) -> Any:
    """Deserialize JSON with optional orjson acceleration."""
    if value is None or value == "":
        return None
    if _orjson is not None:
        return _orjson.loads(value)
    return json.loads(value)


# ---------------------------------------------------------------------------
# Compact piece name encoding (gear/minis)
# ---------------------------------------------------------------------------

_GEAR_NAME_ENCODING_TABLE = "gear_name_encoding"
_MINI_NAME_ENCODING_TABLE = "mini_name_encoding"


def _encode_uvarint(value: int) -> bytes:
    """Encode an unsigned integer as base-128 varint (little-endian groups)."""
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


def _decode_uvarints(blob: bytes) -> list[int]:
    """Decode a sequence of base-128 varints from a bytes blob."""
    if not blob:
        return []
    out: list[int] = []
    x = 0
    shift = 0
    for b in blob:
        x |= (int(b) & 0x7F) << shift
        if int(b) & 0x80:
            shift += 7
            if shift > 63:
                raise ValueError("uvarint too large")
            continue
        out.append(int(x))
        x = 0
        shift = 0
    if shift:
        raise ValueError("truncated uvarint stream")
    return out


def _pack_id_list(ids: Sequence[int]) -> bytes:
    """Pack a list of positive integer IDs into a compact varint blob."""
    if not ids:
        return b""
    buf = bytearray()
    for v in ids:
        iv = int(v)
        if iv <= 0:
            continue
        buf += _encode_uvarint(iv)
    return bytes(buf)


def _unpack_id_list(blob: Any) -> list[int]:
    """Unpack a varint blob produced by `_pack_id_list`."""
    if not blob:
        return []
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    if not isinstance(blob, (bytes, bytearray)):
        return []
    try:
        return [int(v) for v in _decode_uvarints(bytes(blob)) if int(v) > 0]
    except Exception as e:
        logger.debug(f"database:_unpack_id_list: {e}")
        return []


def _pack_id_groups(groups: Sequence[Sequence[int]]) -> bytes:
    """
    Pack list-of-lists IDs using 0 as a group separator.

    IDs are expected to be positive (>=1). Separator is encoded as uvarint(0) i.e. one byte 0.
    """
    if not groups:
        return b""
    buf = bytearray()
    for g0 in groups:
        if not g0:
            continue
        for v in g0:
            iv = int(v)
            if iv <= 0:
                continue
            buf += _encode_uvarint(iv)
        buf += b"\x00"
    return bytes(buf)


def _unpack_id_groups(blob: Any) -> list[list[int]]:
    """Inverse of `_pack_id_groups`."""
    if not blob:
        return []
    if isinstance(blob, memoryview):
        blob = blob.tobytes()
    if not isinstance(blob, (bytes, bytearray)):
        return []
    try:
        values = _decode_uvarints(bytes(blob))
    except Exception as e:
        logger.debug(f"database:_unpack_id_groups: {e}")
        return []
    out: list[list[int]] = []
    cur: list[int] = []
    for v in values:
        iv = int(v)
        if iv == 0:
            if cur:
                out.append(cur)
            cur = []
            continue
        if iv > 0:
            cur.append(iv)
    if cur:
        out.append(cur)
    return out


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
                logger.debug(f"database:_load_piece_name_encoding_maps: {e}")
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
                logger.debug(f"database:_load_piece_name_encoding_maps: {e}")
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
        logger.debug(f"database:_initialize_piece_name_encodings: {e}")
        return

    gear_names = sorted([str(k).strip() for k in (gears_by_name or {}).keys() if str(k).strip()])
    mini_names = sorted([str(k).strip() for k in (minis_by_name or {}).keys() if str(k).strip()])

    if gear_names:
        _insert_missing_piece_names(conn, table=_GEAR_NAME_ENCODING_TABLE, names=gear_names)
    if mini_names:
        _insert_missing_piece_names(conn, table=_MINI_NAME_ENCODING_TABLE, names=mini_names)

    # Refresh cache for this db_path.
    with _PIECE_ENCODING_CACHE_LOCK:
        _PIECE_ENCODING_CACHE.pop(str(db_path), None)


# ---------------------------------------------------------------------------
# Compact details payload helpers (Stats packing, computed fields stripping)
# ---------------------------------------------------------------------------

def _pack_stats_for_storage(details: Any) -> Any:
    """
    Reduce JSON size by storing Stats as a short array under `details["st"]`.

    - Input: details["Stats"] is a dict with verbose keys.
    - Output: details["st"] is a fixed-order int list, and "Stats" is removed.
    """
    if not isinstance(details, dict) or not details:
        return details
    out = dict(details)
    stats = details.get("Stats")
    if isinstance(stats, dict) and stats and out.get("st") is None:
        arr: list[int] = []
        for k in STAT_KEYS:
            try:
                arr.append(int(stats.get(k, 0) or 0))
            except Exception as e:
                logger.debug(f"database:_pack_stats_for_storage: {e}")
                arr.append(0)
        out.pop("Stats", None)
        out["st"] = arr

    gems = details.get("GemCounts")
    if isinstance(gems, dict) and gems and out.get("gc") is None:
        packed_gems: list[int] = []
        gem_key_mask = 0
        for i, k in enumerate(GEM_KEYS):
            if k in gems:
                gem_key_mask |= 1 << i
            try:
                packed_gems.append(int(gems.get(k, 0) or 0))
            except Exception as e:
                logger.debug(f"database:_pack_stats_for_storage: {e}")
                packed_gems.append(0)
        out.pop("GemCounts", None)
        out["gc"] = packed_gems
        if gem_key_mask != (1 << len(GEM_KEYS)) - 1:
            out["gk"] = int(gem_key_mask)

    selected = out.pop("Selected Element", None)
    selected = out.pop("SelectedElement", selected)
    if selected:
        out["se"] = str(selected)

    primary = out.pop("Primary Color", None)
    primary = out.pop("PrimaryColor", primary)
    if primary:
        out["pc"] = str(primary)

    secondary = out.pop("Secondary Color", None)
    secondary = out.pop("SecondaryColor", secondary)
    if secondary:
        out["sc"] = str(secondary)

    if not out.get("ForceGreats"):
        out.pop("ForceGreats", None)
    out.pop("Difficulty", None)
    return out


def _unpack_stats_after_load(details: Any) -> Any:
    """Inverse of `_pack_stats_for_storage` (best-effort)."""
    if not isinstance(details, dict) or not details:
        return details
    out = dict(details)
    stats = details.get("Stats")
    st = details.get("st")
    if not (isinstance(stats, dict) and stats) and isinstance(st, (list, tuple)) and len(st) >= len(STAT_KEYS):
        out_stats: dict[str, int] = {}
        for i, k in enumerate(STAT_KEYS):
            try:
                out_stats[k] = int(st[i] or 0)
            except Exception as e:
                logger.debug(f"database:_unpack_stats_after_load: {e}")
                out_stats[k] = 0
        out["Stats"] = out_stats

    gems = details.get("GemCounts")
    gc = details.get("gc")
    if not (isinstance(gems, dict) and gems) and isinstance(gc, (list, tuple)) and len(gc) >= len(GEM_KEYS):
        try:
            gem_key_mask = int(details.get("gk", (1 << len(GEM_KEYS)) - 1) or 0)
        except Exception as e:
            logger.debug(f"database:_unpack_stats_after_load: {e}")
            gem_key_mask = (1 << len(GEM_KEYS)) - 1
        out_gems: dict[str, int] = {}
        for i, k in enumerate(GEM_KEYS):
            if (gem_key_mask & (1 << i)) == 0:
                continue
            try:
                out_gems[k] = int(gc[i] or 0)
            except Exception as e:
                logger.debug(f"database:_unpack_stats_after_load: {e}")
                out_gems[k] = 0
        out["GemCounts"] = out_gems

    if "SelectedElement" not in out and "Selected Element" not in out and out.get("se"):
        out["SelectedElement"] = str(out.get("se") or "")
    if "PrimaryColor" not in out and "Primary Color" not in out and out.get("pc"):
        out["PrimaryColor"] = str(out.get("pc") or "")
    if "SecondaryColor" not in out and "Secondary Color" not in out and out.get("sc"):
        out["SecondaryColor"] = str(out.get("sc") or "")

    return out


def _strip_computed_details_fields(details: Any) -> Any:
    """Return details without large recomputable payloads."""
    return details


def get_evolution_db_path() -> str:
    """
    Return the configured evolution DB location (env override supported).

    Returns:
        str: Path to evolution database file
    """
    env_path = str(os.getenv("EVOLUTION_DB_PATH", "") or "").strip()
    if env_path:
        return env_path

    # Prefer the external DB (kept out of the repo) when it exists. This keeps the
    # default behavior for typical clones while allowing the monorepo layout:
    #   <parent>/RoBeats-Calculator-Engine
    #   <parent>/ExternalDatabases/evolution.db
    try:
        external_db = os.path.abspath(os.path.join(PATHS.script_dir, os.pardir, "ExternalDatabases", "evolution.db"))
        if os.path.exists(external_db):
            return external_db
    except Exception as e:
        logger.debug(f"database:get_evolution_db_path: {e}")

    return PATHS.evolution_db_default


def get_evolution_overlay_db_path() -> str:
    """
    Return the configured overlay DB location used for backend/live overlay writes.

    This DB mirrors the canonical schema but remains separate so the website backend
    can compare fresh optimizer output against the canonical DB without rebuilding
    the static site artifacts.
    """
    for env_name in ("EVOLUTION_OVERLAY_DB_PATH", "METAFINDER_EVOLUTION_OVERLAY_DB"):
        env_path = str(os.getenv(env_name, "") or "").strip()
        if env_path:
            return env_path

    try:
        external_db = os.path.abspath(
            os.path.join(PATHS.script_dir, os.pardir, "ExternalDatabases", "evolution_overlay.db")
        )
        if os.path.exists(external_db):
            return external_db
        return external_db
    except Exception as e:
        logger.debug(f"database:get_evolution_overlay_db_path: {e}")
        return os.path.abspath(os.path.join(PATHS.script_dir, "evolution_overlay.db"))


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
    # Ensure parent directory exists for custom paths (e.g. benchmark artifacts).
    try:
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
    except Exception as e:
        logger.debug(f"database:get_db_connection_with_timeout: {e}")
    conn = sqlite3.connect(db_path, timeout=float(timeout))
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    # Match busy_timeout to the connection timeout (cap to avoid surprising waits).
    try:
        busy_ms = int(max(100.0, min(float(timeout) * 1000.0, 30_000.0)))
        conn.execute(f"PRAGMA busy_timeout={busy_ms};")
    except Exception as e:
        logger.debug(f"database:get_db_connection_with_timeout: {e}")
    ensure_schema(conn)
    return conn


def _db_path_to_uri(db_path: str) -> str:
    # SQLite URI filenames expect forward slashes. Percent-encode spaces and other
    # characters while preserving "/" and ":" (Windows drive roots).
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
        logger.debug(f"database:get_db_connection_readonly: {e}")
    return conn


# ---------------------------------------------------------------------------
# Perf: thread-local DB connections for read-heavy paths
# ---------------------------------------------------------------------------
_DB_TLS = threading.local()
_DB_CONN_REGISTRY: "weakref.WeakSet[sqlite3.Connection]" = weakref.WeakSet()
_DB_CONN_REGISTRY_LOCK = threading.Lock()


def _register_db_conn(conn: sqlite3.Connection) -> None:
    try:
        with _DB_CONN_REGISTRY_LOCK:
            _DB_CONN_REGISTRY.add(conn)
    except Exception as e:
        logger.debug(f"database:_register_db_conn: {e}")


def _close_all_registered_db_conns() -> None:
    try:
        with _DB_CONN_REGISTRY_LOCK:
            conns = list(_DB_CONN_REGISTRY)
    except Exception as e:
        logger.debug(f"database:_close_all_registered_db_conns: {e}")
        conns = []
    for c in conns:
        try:
            c.close()
        except Exception as e:
            logger.debug(f"database:_close_all_registered_db_conns: {e}")


atexit.register(_close_all_registered_db_conns)


def get_db_connection_cached(db_path: Optional[str] = None, *, allow_fallback: bool = True) -> sqlite3.Connection:
    """
    Return a per-thread cached SQLite connection.

    This keeps exact query semantics while avoiding per-call reconnect + PRAGMA + migration
    overhead on read-heavy call sites (e.g., per-song DB seed/context reads).
    """
    if db_path is None:
        db_path = get_evolution_db_path()
    try:
        conns = getattr(_DB_TLS, "conns", None)
        if conns is None:
            conns = {}
            setattr(_DB_TLS, "conns", conns)
    except Exception as e:
        logger.debug(f"database:get_db_connection_cached: {e}")
        conns = {}

    db_path = str(db_path)
    conn = conns.get(db_path)
    if conn is not None:
        return conn

    # If we recently failed to open the real DB connection, avoid retrying on every
    # hot-path call (which can spam warnings and waste time during brief lock bursts).
    try:
        now_monotonic = float(time.monotonic())
    except Exception as e:
        logger.debug(f"database:get_db_connection_cached: {e}")
        now_monotonic = 0.0
    try:
        next_retry_ts = float(getattr(_DB_TLS, "ro_next_retry_ts", 0.0) or 0.0)
    except Exception as e:
        logger.debug(f"database:get_db_connection_cached: {e}")
        next_retry_ts = 0.0
    if now_monotonic and (now_monotonic < next_retry_ts):
        fallback = getattr(_DB_TLS, "fallback_conn", None)
        if fallback is not None:
            if not allow_fallback:
                raise sqlite3.OperationalError("read-only DB fallback active during strict read")
            return fallback

    # Default to a small non-zero timeout to allow brief lock contention during
    # write bursts without immediate failure. This prevents spurious fallbacks
    # to the empty in-memory DB when the AsyncDbSaver is actively writing.
    try:
        read_timeout = float(env_get("DB_READ_TIMEOUT_SEC", "0.2") or "0.2")
    except Exception as e:
        logger.debug(f"database:get_db_connection_cached: {e}")
        read_timeout = 0.2

    try:
        conn = get_db_connection_readonly(db_path, timeout=read_timeout)
    except sqlite3.Error as exc:
        # Best-effort: DB might be locked briefly during heavy write bursts, or
        # may not exist yet in some test/tool entrypoints. Never block the GPU
        # feed loop on a read-only seed/context fetch, but also avoid "sticky"
        # permanent fallback: retry opening the real DB after a short cooldown.
        try:
            fail_count = int(getattr(_DB_TLS, "ro_fail_count", 0) or 0) + 1
        except Exception as e:
            logger.debug(f"database:get_db_connection_cached: {e}")
            fail_count = 1
        try:
            setattr(_DB_TLS, "ro_fail_count", int(fail_count))
        except Exception as e:
            logger.debug(f"database:get_db_connection_cached: {e}")
        # Exponential backoff, capped, to avoid thrashing on persistent failures.
        try:
            exp = min(7, max(0, int(fail_count) - 1))
        except Exception as e:
            logger.debug(f"database:get_db_connection_cached: {e}")
            exp = 0
        cooldown_sec = min(5.0, 0.05 * (2**exp))
        try:
            next_retry_ts = float(now_monotonic) + float(cooldown_sec)
            setattr(_DB_TLS, "ro_next_retry_ts", float(next_retry_ts))
        except Exception as e:
            logger.debug(f"database:get_db_connection_cached: {e}")
        site = "db.readonly_connection"
        message = "failed to open read-only DB connection; using thread-local in-memory fallback DB (will retry)"
        if not allow_fallback:
            site = "db.readonly_connection.strict"
            message = "failed to open read-only DB connection for strict baseline read"
        warn_fallback(
            site,
            message,
            context={
                "db_path": db_path,
                "timeout_sec": read_timeout,
                "fail_count": int(fail_count),
                "retry_in_sec": float(cooldown_sec),
            },
            exc=exc,
            fatal=False,
        )
        if not allow_fallback:
            raise
        fallback = getattr(_DB_TLS, "fallback_conn", None)
        if fallback is None:
            try:
                fallback = sqlite3.connect(":memory:")
                fallback.row_factory = sqlite3.Row
                # Keep query semantics stable: fallback DB should look like an empty
                # evolution DB (schema present) rather than raising "no such table".
                try:
                    ensure_schema(fallback)
                except Exception as e:
                    logger.debug(f"database:get_db_connection_cached: {e}")
                try:
                    fallback.execute("PRAGMA query_only=1;")
                except Exception as e:
                    logger.debug(f"database:get_db_connection_cached: {e}")
                setattr(_DB_TLS, "fallback_conn", fallback)
                _register_db_conn(fallback)
            except Exception as e:
                # Last resort: re-raise so callers can handle it.
                logger.debug(f"database:get_db_connection_cached: {e}")
                raise
        return fallback

    conns[db_path] = conn
    try:
        setattr(_DB_TLS, "ro_fail_count", 0)
        setattr(_DB_TLS, "ro_next_retry_ts", 0.0)
    except Exception as e:
        logger.debug(f"database:get_db_connection_cached: {e}")
    _register_db_conn(conn)
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
        # `get_db_connection()` already ensures schema/migrations; keep this function
        # as a stable entry point for callers/tests.
        try:
            _initialize_piece_name_encodings(conn, db_path=str(db_path))
        except Exception as e:
            logger.debug(f"database:init_db: {e}")
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Per-song attempt counters (songs table)
# ---------------------------------------------------------------------------
def get_song_counters(
    song_name: str,
    *,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
    allow_fallback: bool = True,
) -> tuple[int, int, int, int]:
    """
    Fetch per-song attempt counters and best scores from `songs`.

    Returns:
        (attempt_lifetime, attempts_first, best_score, best_fg_score)
    """
    song_name = str(song_name or "").strip()
    if not song_name:
        return (0, 0, 0, 0)

    if conn is None:
        # Intentionally use a per-thread cached read-only connection for the
        # hot-path "DB seed/context read" callers. This connection is owned by
        # the cache and is closed at process exit.
        conn = get_db_connection_cached(db_path or get_evolution_db_path(), allow_fallback=allow_fallback)

    try:
        row = conn.execute(
            """
            SELECT attempt_lifetime, attempts_first, best_score, best_fg_score
            FROM songs
            WHERE name = ?
            """,
            (song_name,),
        ).fetchone()
        if not row:
            return (0, 0, 0, 0)
        try:
            attempt_lifetime = int(row["attempt_lifetime"] or 0)
        except Exception as e:
            logger.debug(f"database:get_song_counters: {e}")
            attempt_lifetime = 0
        try:
            attempts_first = int(row["attempts_first"] or 0)
        except Exception as e:
            logger.debug(f"database:get_song_counters: {e}")
            attempts_first = 0
        try:
            best_score = int(row["best_score"] or 0)
        except Exception as e:
            logger.debug(f"database:get_song_counters: {e}")
            best_score = 0
        try:
            best_fg_score = int(row["best_fg_score"] or 0)
        except Exception as e:
            logger.debug(f"database:get_song_counters: {e}")
            best_fg_score = 0
        return (attempt_lifetime, attempts_first, best_score, best_fg_score)
    except sqlite3.Error:
        # Defensive: if the schema hasn't been migrated yet, treat as missing.
        if not allow_fallback:
            raise
        return (0, 0, 0, 0)


def update_song_counters(
    song_name: str,
    *,
    processed_run: bool,
    record_improved: bool,
    conn: Optional[sqlite3.Connection] = None,
    db_path: Optional[str] = None,
) -> None:
    """
    Update per-song attempt counters.

    Semantics:
    - If `processed_run=True`: increment `attempt_lifetime` and `attempts_first`
    - If `record_improved=True`: reset `attempts_first = 1`
    - If `processed_run=False`: do not increment (used for deferred FG-only updates)
    """
    song_name = str(song_name or "").strip()
    if not song_name:
        return

    close_conn = False
    if conn is None:
        conn = get_db_connection(db_path or get_evolution_db_path())
        close_conn = True

    pr = 1 if processed_run else 0
    ri = 1 if record_improved else 0

    try:
        with conn:
            # Ensure row exists before updating counters.
            conn.execute(
                """
                INSERT OR IGNORE INTO songs (name, best_score, best_fg_score, last_updated, attempt_lifetime, attempts_first)
                VALUES (?, 0, 0, 0, 0, 0)
                """,
                (song_name,),
            )

            conn.execute(
                """
                UPDATE songs
                SET
                    attempt_lifetime = CASE
                        WHEN ? THEN COALESCE(attempt_lifetime, 0) + 1
                        ELSE COALESCE(attempt_lifetime, 0)
                    END,
                    attempts_first = CASE
                        WHEN ? THEN 1
                        WHEN ? THEN COALESCE(attempts_first, 0) + 1
                        ELSE COALESCE(attempts_first, 0)
                    END,
                    last_updated = strftime('%s', 'now')
                WHERE name = ?
                """,
                (pr, ri, pr, song_name),
            )
    except sqlite3.Error:
        # Best-effort; avoid crashing the optimizer loop on counter updates.
        return
    finally:
        if close_conn:
            try:
                conn.close()
            except Exception as e:
                logger.debug(f"database:update_song_counters: {e}")


def _compact_gear_for_db(gear_list):
    """
    Convert gear list to compact storage format (names only).
    Handles both dicts and strings.

    Args:
        gear_list: List of gear items (dicts or strings)

    Returns:
        list: List of gear names
    """
    if not gear_list:
        return []
    result = []
    for g in gear_list:
        if isinstance(g, dict):
            name = g.get("Name", "")
        else:
            name = str(g) if g else ""
        if name:
            result.append(name)
    return result


def _compact_minis_for_db(mini_list):
    """
    Convert mini list to compact storage format (names only).

    Handles:
    - dicts: {"Name": ...}
    - strings: "Electroman"
    - nested variant groups: [["A","B"], ["C"], ...] (takes a representative per slot)

    Args:
        mini_list: List of mini items (dicts or strings)

    Returns:
        list: List of mini names
    """
    if not mini_list:
        return []

    def _first_name(v: Any) -> str:
        if v is None:
            return ""
        if isinstance(v, dict):
            return str(v.get("Name", "") or "").strip()
        if isinstance(v, (list, tuple)):
            for it in v:
                name = _first_name(it)
                if name:
                    return name
            return ""
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("[") and s.endswith("]"):
                match = re.search(r"[\"']([^\"']+)[\"']", s)
                if match:
                    return match.group(1).strip()
            return s
        return str(v).strip()

    result = []
    for m in mini_list:
        name = _first_name(m)
        if name:
            result.append(name)
    return result


def _expand_gear_from_db(gear_names, gears_by_name):
    """
    Expand gear names back to full stat dictionaries.

    Args:
        gear_names: List of gear names
        gears_by_name: Lookup dict mapping names to full gear dicts

    Returns:
        list: List of full gear dictionaries
    """
    if not gear_names or not gears_by_name:
        return []
    return [gears_by_name.get(name, {"Name": name}) for name in gear_names]


def _expand_minis_from_db(mini_names, minis_by_name):
    """
    Expand mini names back to full stat dictionaries.

    Args:
        mini_names: List of mini names
        minis_by_name: Lookup dict mapping names to full mini dicts

    Returns:
        list: List of full mini dictionaries
    """
    if not mini_names or not minis_by_name:
        return []
    return [minis_by_name.get(name, {"Name": name}) for name in mini_names]


def _loadout_hash_from_names(gear_names: list[str], mini_names: list[str]) -> str:
    from ..helpers.song_helpers.loadout_hashing import loadout_hash_from_names

    return loadout_hash_from_names(gear_names, mini_names)


def get_loadout_hash(gear_list: List[Any], mini_list: List[Any]) -> str:
    """
    Generate a unique hash for a loadout (gear + minis).
    Sorts items by name to ensure consistent hashing regardless of order.
    Handles both dicts (with 'Name' key) and plain strings.

    Args:
        gear_list: List of gear items (dicts or strings)
        mini_list: List of mini items (dicts or strings)

    Returns:
        str: MD5 hash of the loadout
    """
    # Extract names, handling both dict and string inputs
    gear_names = _compact_gear_for_db(gear_list)
    mini_names = _compact_minis_for_db(mini_list)
    return _loadout_hash_from_names(gear_names, mini_names)


def _get_overflow_from_details(details):
    """
    Extract overflow value from details dict.

    Args:
        details: Details dictionary containing GemCounts

    Returns:
        int: Overflow value (Element), or 0 if not found
    """
    if not details:
        return 0
    gem_counts = details.get("GemCounts", {})
    if not gem_counts:
        return 0
    return gem_counts.get("Element", 0)


def _ensure_stats_in_details(
    details: dict,
    gear: list,
    minis: list,
    minis_by_name: dict,
    *,
    team_buff: "Optional[str]" = None,
    team_color: "Optional[str]" = None,
) -> dict:
    """
    Ensure Stats are populated in details dict.

    Defers to the unified stats gateway first; falls back to heavy reconstruction
    from gear/mini names only when the gateway returns without Stats.
    """
    from ..helpers.song_helpers.stats_gateway import ensure_stats

    gateway_result = ensure_stats(details)
    if isinstance(gateway_result, dict) and gateway_result.get("Stats"):
        return gateway_result

    if not isinstance(details, dict):
        details = {}
    warn_fallback(
        "db.ensure_stats",
        "details missing Stats, reconstructing stats for persistence",
        context={"team_buff": team_buff or "", "team_color": team_color or ""},
        fatal=False,
    )

    try:
        from gear_optimizer.core.stats_calculator import compute_full_stats

        gear_names = []
        for g in gear or []:
            if isinstance(g, dict):
                gear_names.append(g.get("Name", ""))
            elif isinstance(g, str):
                gear_names.append(g)

        mini_names = []
        for m in minis or []:
            if isinstance(m, dict):
                mini_names.append(m.get("Name", ""))
            elif isinstance(m, str):
                mini_names.append(m)
            elif isinstance(m, list) and m:
                first = m[0]
                if isinstance(first, dict):
                    mini_names.append(first.get("Name", ""))
                elif isinstance(first, str):
                    mini_names.append(first)

        gears_by_name = get_gears_by_name_cached()

        base_stats = {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 0,
        }

        buff_tier = str(team_buff or "").strip().upper()
        buff_color = str(team_color or "").strip()
        if not buff_color:
            buff_color = str(
                details.get("PrimaryColor")
                or details.get("Primary Color")
                or details.get("SelectedElement")
                or details.get("Selected Element")
                or ""
            ).strip()

        for stat_name, delta in team_buff_effect(buff_tier, buff_color).items():
            base_stats[stat_name] = int(base_stats.get(stat_name, 0) or 0) + int(delta)

        gem_counts = dict(details.get("GemCounts", {}) or {})
        gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
        gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
        selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""

        computed = compute_full_stats(
            gear_names, mini_names, gem_counts, selected_element, gears_by_name, minis_by_name, base_stats
        )

        details["Stats"] = computed

    except Exception as e:
        logger.debug(f"database:_ensure_stats_in_details: {e}")

    return details


def _normalize_details_for_persistence(
    details: Any,
    *,
    score: int,
    fg_score: int,
    force_data: Any,
    preserve_attempt_meta: bool = False,
) -> dict:
    """
    Normalize details payload before persistence.

    Goals:
    - Keep `details["ForceGreats"]["final_score"]` consistent with the persisted `fg_score` when FG ran.
      (Some downstream consumers read this field and will otherwise treat FG as missing/zero.)
    - Strip transient attempt counters from the stored payload unless the caller
      explicitly asks to preserve them for a mirror write.
    """
    if not isinstance(details, dict):
        return {}

    out = dict(details)
    if not preserve_attempt_meta:
        out.pop("attempt_lifetime", None)
        out.pop("attempts_first", None)

    if force_data is None or int(fg_score or 0) <= 0:
        return out

    fg_meta = out.get("ForceGreats")
    if not isinstance(fg_meta, dict):
        return out

    # Update (or create) the final_score field for consistency.
    fg_out = dict(fg_meta)
    fg_out["final_score"] = int(fg_score)

    if out is details:
        out = dict(out)
    out["ForceGreats"] = fg_out
    return out

def _force_payload_base_score(force_data: Any) -> int:
    if not isinstance(force_data, dict):
        return 0
    for key in ("BaseScore", "base_score"):
        score = _safe_int_for_db(force_data.get(key), 0)
        if score > 0:
            return score
    nested = force_data.get("details")
    if isinstance(nested, dict):
        for key in ("BaseScore", "base_score"):
            score = _safe_int_for_db(nested.get(key), 0)
            if score > 0:
                return score
    return 0


def _base_details_from_force_payload(base_details: Any, force_data: Any) -> dict:
    """
    Build the FG table details payload that explains the FG row's paired `score`.

    `force_details_json` owns the FG replay surface (`fg_score` plus ForceGreats config).
    The FG row's `details_json` owns the paired base replay surface for the same FG
    allocation, so it must be derived from the force payload's BaseStats+gems instead
    of from the loadout's separate best-base winner.
    """
    if not isinstance(force_data, dict):
        return {}

    from gear_optimizer.helpers.song_helpers.force_greats.result_application import materialize_stats_from_payload

    payload = force_data.get("details") if isinstance(force_data.get("details"), dict) else force_data
    if not isinstance(payload, dict):
        return {}

    selected = (
        payload.get("SelectedElement")
        or payload.get("Selected Element")
        or (base_details.get("SelectedElement") if isinstance(base_details, dict) else None)
        or (base_details.get("Selected Element") if isinstance(base_details, dict) else None)
        or ""
    )
    stats = materialize_stats_from_payload(payload, selected_element=selected)
    if not isinstance(stats, dict) or not stats:
        return {}

    out: dict[str, Any] = {}
    if isinstance(base_details, dict):
        for key in ("PrimaryColor", "Primary Color", "SecondaryColor", "Secondary Color"):
            if base_details.get(key) not in (None, ""):
                out[key] = base_details.get(key)

    out["Stats"] = dict(stats)
    out["FT"] = _safe_int_for_db(payload.get("FT", (payload.get("GemCounts") or {}).get("Fever Time", 0)), 0)
    out["FF"] = _safe_int_for_db(
        payload.get("FF", (payload.get("GemCounts") or {}).get("Fever Fill Rate", 0)),
        0,
    )
    gem_counts = payload.get("GemCounts")
    if isinstance(gem_counts, dict):
        out["GemCounts"] = dict(gem_counts)
    if selected:
        out["SelectedElement"] = str(selected)
    base_score = _force_payload_base_score(force_data)
    if base_score > 0:
        out["BaseScore"] = int(base_score)
    return out


def _compact_force_details_for_storage(force_data: Any) -> Any:
    """
    Return the raw FG payload without fields already persisted in FG details.

    `force_details_json` must keep the replay surface: BaseStats, GemCounts,
    FT/FF, selected element, ForceGreats config, and score. A materialized final
    `Stats` copy is redundant when BaseStats + gems are present, because FG
    replay reconstructs it from `force_details_json`. The FG table `details_json`
    remains the paired base-score detail surface.
    """
    if not isinstance(force_data, dict) or not force_data:
        return force_data

    out = dict(force_data)
    if (
        isinstance(out.get("Stats"), dict)
        and isinstance(out.get("BaseStats"), dict)
        and isinstance(out.get("GemCounts"), dict)
    ):
        out.pop("Stats", None)

    if "Score" in out and "score" in out:
        try:
            if int(out.get("Score") or 0) == int(out.get("score") or 0):
                out.pop("score", None)
        except Exception as e:
            logger.debug(f"database:_compact_force_details_for_storage: {e}")

    return out


def save_loadouts_batch(
    song_name: str,
    entries: List[PersistenceEntry],
    *,
    db_path: Optional[str] = None,
    team_buff: str = "T5",
    preserve_attempt_meta: bool = False,
) -> None:
    """
    Batch insert/update loadouts for a song in a single transaction.
    Persists base results into TeamBuff tier tables for the provided baseline tier.

    Args:
        song_name: Name of the song
        entries: List of persistence dicts with keys: score, fg_score, gear, minis, details, force
        team_buff: Baseline TeamBuff tier for this run (default: T5)
    """
    if not entries:
        return
    song_name = str(song_name or "").strip()
    if not song_name:
        return
    team_buff = normalize_team_buff(team_buff, default="T5")

    def _coerce_int(v: Any) -> int:
        try:
            return int(v or 0)
        except Exception as e:
            logger.debug(f"database:_coerce_int: {e}")
            return 0

    best_score_max = None
    best_fg_max = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        score = _coerce_int(entry.get("score", 0))
        fg_score = _coerce_int(entry.get("fg_score", 0))
        fg_base_score = score
        try:
            raw_fg_base = entry.get("fg_base_score")
        except Exception as e:
            logger.debug(f"database:_coerce_int: {e}")
            raw_fg_base = None
        if raw_fg_base is not None:
            fg_base_score = _coerce_int(raw_fg_base)
            if fg_base_score <= 0:
                fg_base_score = score
        force_data = entry.get("force")
        if fg_score <= 0 and force_data is not None:
            fg_score = fg_score_from_force(force_data)
        if force_data is not None:
            force_base_score = _force_payload_base_score(force_data)
            if force_base_score > 0:
                fg_base_score = force_base_score

        if best_score_max is None or score > best_score_max:
            best_score_max = score
        if (
            force_data is not None
            and fg_score > fg_base_score
            and _base_details_from_force_payload(entry.get("details", {}), force_data)
            and (best_fg_max is None or fg_score > best_fg_max)
        ):
            best_fg_max = fg_score

    resolved_db_path = str(db_path or get_evolution_db_path())
    conn = get_db_connection(resolved_db_path)
    try:

        def _is_lock_error(err: sqlite3.Error) -> bool:
            msg = str(err or "").lower()
            return ("database is locked" in msg) or ("database is busy" in msg) or ("database table is locked" in msg)

        max_attempts = 6
        base_sleep_sec = 0.05
        for attempt in range(max_attempts):
            try:
                # Persist the base run under the baseline TeamBuff tier in the same transaction.
                save_team_buff_loadouts_batch(
                    song_name,
                    team_buff,
                    entries,
                    conn=conn,
                    commit=False,
                    db_path=resolved_db_path,
                    preserve_attempt_meta=bool(preserve_attempt_meta),
                )

                if best_score_max is not None:
                    conn.execute(
                        """
                        INSERT INTO songs (name, best_score) VALUES (?, ?)
                        ON CONFLICT(name) DO UPDATE SET
                            best_score = MAX(best_score, excluded.best_score),
                            last_updated = strftime('%s', 'now')
                        """,
                        (song_name, best_score_max),
                    )

                if best_fg_max:
                    conn.execute(
                        """
                        INSERT INTO songs (name, best_fg_score) VALUES (?, ?)
                        ON CONFLICT(name) DO UPDATE SET
                            best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
                            last_updated = strftime('%s', 'now')
                        """,
                        (song_name, best_fg_max),
                    )

                conn.commit()
                return
            except sqlite3.OperationalError as e:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                if _is_lock_error(e) and attempt < (max_attempts - 1):
                    sleep_sec = min(2.0, float(base_sleep_sec) * (2**attempt))
                    time.sleep(max(0.0, sleep_sec))
                    continue
                raise
            except sqlite3.Error:
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
                raise
    finally:
        conn.close()


def save_team_buff_loadouts_batch(
    song_name: str,
    team_buff: str,
    entries: Sequence[Mapping[str, Any]],
    *,
    conn: Optional[sqlite3.Connection] = None,
    commit: bool = True,
    db_path: Optional[str] = None,
    preserve_attempt_meta: bool = False,
) -> None:
    """
    Batch insert/update tiered leaderboards for a song in a single transaction.

    Mirrors `save_loadouts_batch`, but partitions by `team_buff` (`NONE/T1/T5/T10/T20/T50/T51`) into:
    - team_buff_loadouts (base leaderboard for that tier)
    - team_buff_fg_loadouts (FG leaderboard for that tier; FG strictly beats base)
    """
    song_name = str(song_name or "").strip()
    team_buff = canonicalize_team_buff(team_buff)
    if not song_name or not team_buff or not entries:
        return

    timing = env_flag("DB_TIMING")
    timing_threshold_ms = 50.0
    try:
        timing_threshold_ms = float(env_get("DB_TIMING_THRESHOLD_MS", str(timing_threshold_ms)))
    except Exception as e:
        logger.debug(f"database:save_team_buff_loadouts_batch: {e}")
        timing_threshold_ms = 50.0

    def _log_timing(label: str, dt_sec: float) -> None:
        if not timing:
            return
        ms = float(dt_sec) * 1000.0
        if ms < timing_threshold_ms:
            return
        print(f"[DB][TIMING] {song_name} {team_buff} {label}={ms:.1f}ms")

    _t0 = time.perf_counter()

    minis_by_name = get_minis_by_name_cached()
    gears_by_name = get_gears_by_name_cached()

    def _coerce_int(v: Any) -> int:
        try:
            return int(v or 0)
        except Exception as e:
            logger.debug(f"database:_coerce_int: {e}")
            return 0

    def _normalize_force_for_persistence(force_data: Any, *, fg_score: int) -> Any:
        if not isinstance(force_data, dict):
            return force_data

        out = dict(force_data)

        score_v = _coerce_int(out.get("score", 0))
        if score_v <= 0:
            score_v = _coerce_int(out.get("Score", 0))
        if score_v <= 0 and int(fg_score or 0) > 0:
            score_v = int(fg_score)
        if score_v > 0:
            out["score"] = int(score_v)

        det = out.get("details")
        if isinstance(det, dict):
            fg = det.get("ForceGreats")
            if isinstance(fg, dict) and int(fg_score or 0) > 0:
                fg_out = dict(fg)
                fg_out["final_score"] = int(fg_score)
                det_out = dict(det)
                det_out["ForceGreats"] = fg_out
                out["details"] = det_out
        return out

    entry_color_cache: Dict[int, tuple[str, str, str]] = {}

    def _extract_entry_colors(entry: Mapping[str, Any]) -> tuple[str, str, str]:
        entry_id = int(id(entry))
        cached = entry_color_cache.get(entry_id)
        if cached is not None:
            return cached

        p_color, s_color, sel_color = extract_song_colors(entry.get("details", {}))
        if p_color or s_color:
            out = (p_color, s_color, sel_color)
            entry_color_cache[entry_id] = out
            return out

        force_data = entry.get("force")
        if isinstance(force_data, dict):
            nested = force_data.get("details")
            if isinstance(nested, dict):
                p2, s2, sel2 = extract_song_colors(nested)
                if p2 or s2:
                    out = (p2, s2, sel2 or sel_color)
                    entry_color_cache[entry_id] = out
                    return out

            p2, s2, sel2 = extract_song_colors(force_data)
            if p2 or s2:
                out = (p2, s2, sel2 or sel_color)
                entry_color_cache[entry_id] = out
                return out

        out = (p_color, s_color, sel_color)
        entry_color_cache[entry_id] = out
        return out

    # Keep effective mini hashing active even when some incoming entries omit colors
    # Some payloads omit colors. Song colors are stable per song, so borrowing
    # from another entry or an existing DB row is safe and prevents duplicate rows.
    song_color_fallback: Optional[tuple[str, str, str]] = None
    for entry in entries:
        p_color, s_color, sel_color = _extract_entry_colors(entry)
        if p_color or s_color:
            song_color_fallback = (p_color, s_color, sel_color)
            break

    if song_color_fallback is None:
        db_path_lookup = str(db_path or get_evolution_db_path())
        try:
            lookup_conn = get_db_connection_cached(db_path_lookup)
            rows = lookup_conn.execute(
                """
                SELECT details_json
                FROM team_buff_loadouts
                WHERE song_name = ? AND team_buff = ? AND details_json IS NOT NULL
                ORDER BY score DESC, timestamp DESC
                LIMIT 25
                """,
                (song_name, team_buff),
            ).fetchall()
            for row in rows:
                try:
                    details_row = _json_loads(row["details_json"]) if row["details_json"] else {}
                    details_row = _unpack_stats_after_load(details_row)
                except Exception as e:
                    logger.debug(f"database:_extract_entry_colors: {e}")
                    continue
                p_color, s_color, sel_color = extract_song_colors(details_row)
                if p_color or s_color:
                    song_color_fallback = (p_color, s_color, sel_color)
                    warn_fallback(
                        "db.song_color_fallback",
                        "using existing DB details colors as fallback for effective mini hashing",
                        context={
                            "song_name": song_name,
                            "team_buff": team_buff,
                            "primary": p_color,
                            "secondary": s_color,
                        },
                        fatal=False,
                    )
                    break
        except sqlite3.Error:
            pass

    mini_sig_cache: Dict[tuple[str, str, str, str], tuple[Any, ...]] = {}

    def _mini_signature_cached(name: str, p_color: str, s_color: str, sel_color: str) -> tuple[Any, ...]:
        key = (str(name or ""), str(p_color or ""), str(s_color or ""), str(sel_color or ""))
        sig = mini_sig_cache.get(key)
        if sig is not None:
            return sig
        sig = effective_mini_signature_for_name(name, minis_by_name, p_color, s_color, sel_color)
        mini_sig_cache[key] = sig
        return sig

    def _effective_hash_for_entry(
        entry: Mapping[str, Any],
    ) -> Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]:
        gear_names_local = _compact_gear_for_db(entry.get("gear", []))
        mini_names_local = _compact_minis_for_db(entry.get("minis", []))
        p_color, s_color, sel_color = _extract_entry_colors(entry)
        if (not p_color and not s_color) and song_color_fallback is not None:
            p_color, s_color, fallback_sel = song_color_fallback
            if not sel_color:
                sel_color = fallback_sel or p_color or s_color
        if not p_color and not s_color:
            return None
        if not sel_color:
            sel_color = p_color or s_color
        mini_sigs_local = [_mini_signature_cached(n, p_color, s_color, sel_color) for n in mini_names_local]
        return (
            effective_loadout_hash_from_names(gear_names_local, mini_sigs_local),
            mini_sigs_local,
            p_color,
            s_color,
            sel_color,
        )

    # Deduplicate (score + hash) within this batch.
    _t_dedup0 = time.perf_counter()
    dedup_groups: Dict[tuple[int, str], list[Mapping[str, Any]]] = {}
    effective_cache_by_entry_id: Dict[int, Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]] = {}
    for entry in entries:
        entry_id = int(id(entry))
        eff = effective_cache_by_entry_id.get(entry_id)
        if entry_id not in effective_cache_by_entry_id:
            eff = _effective_hash_for_entry(entry)
            effective_cache_by_entry_id[entry_id] = eff
        if eff is None:
            warn_fallback(
                "db.hash.raw_names",
                "missing song color metadata; using raw name hash fallback",
                context={"song_name": song_name, "team_buff": team_buff},
                fatal=False,
            )
            h = _loadout_hash_from_names(
                _compact_gear_for_db(entry.get("gear", [])), _compact_minis_for_db(entry.get("minis", []))
            )
        else:
            h = eff[0]
        key = (int(entry.get("score", 0) or 0), str(h))
        dedup_groups.setdefault(key, []).append(entry)

    deduplicated_entries: list[Mapping[str, Any]] = []
    for (_score, _h), group in dedup_groups.items():
        if len(group) == 1:
            deduplicated_entries.append(group[0])
            continue
        try:
            best_entry = max(
                group, key=lambda e: (_get_overflow_from_details(e.get("details", {})), e.get("fg_score", 0))
            )
            deduplicated_entries.append(best_entry)
        except Exception as e:
            logger.debug(f"database:_effective_hash_for_entry: {e}")
            deduplicated_entries.append(group[0])

    _log_timing("dedup_entries", time.perf_counter() - _t_dedup0)

    def _can_recompute_stats_for_persistence(gear_names_local: list[str], mini_names_local: list[str]) -> bool:
        if gear_names_local:
            if not isinstance(gears_by_name, dict) or not gears_by_name:
                return False
            if any((n and n not in gears_by_name) for n in gear_names_local):
                return False
        if mini_names_local:
            if not isinstance(minis_by_name, dict) or not minis_by_name:
                return False
            if any((n and n not in minis_by_name) for n in mini_names_local):
                return False
        return True

    def _recompute_stats_in_details_for_persistence(
        details_obj: Any,
        *,
        gear_names_local: list[str],
        mini_names_local: list[str],
        team_color: str,
    ) -> dict:
        """
        Recompute `details["Stats"]` deterministically from:
        - canonical representative gear + mini names
        - persisted gem counts (GemCounts + FT/FF)
        - TeamBuff tier effect for correct frontend display

        This prevents persisting:
        - mini-variant off-element drift (equivalence-group representatives),
        - config-tainted Stats snapshots that don't match legacy DB semantics.
        """
        if not isinstance(details_obj, dict):
            details_obj = {}

        try:
            from gear_optimizer.core.stats_calculator import compute_full_stats
        except Exception as e:
            logger.debug(f"database:_recompute_stats_in_details_for_persistence: {e}")
            return details_obj

        # Base stats for persistence: TeamBuff only (no user-config gems).
        base_stats = {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Chill": 0,
            "Flow": 0,
            "Rush": 0,
            "Beat": 0,
            "Vibe": 0,
        }

        buff_tier = str(team_buff or "").strip().upper()
        buff_color = str(team_color or "").strip()
        if not buff_color:
            buff_color = str(
                details_obj.get("PrimaryColor")
                or details_obj.get("Primary Color")
                or details_obj.get("SelectedElement")
                or details_obj.get("Selected Element")
                or ""
            ).strip()

        for stat_name, delta in team_buff_effect(buff_tier, buff_color).items():
            base_stats[stat_name] = int(base_stats.get(stat_name, 0) or 0) + int(delta)

        gem_counts = details_obj.get("GemCounts")
        if isinstance(gem_counts, dict):
            gem_counts = dict(gem_counts)
        else:
            gem_counts = {}
        gem_counts["Fever Time"] = int(details_obj.get("FT", 0) or 0)
        gem_counts["Fever Fill Rate"] = int(details_obj.get("FF", 0) or 0)

        selected_element = details_obj.get("SelectedElement") or details_obj.get("Selected Element") or ""
        selected_element = str(selected_element or "").strip()

        computed = compute_full_stats(
            gear_names_local,
            mini_names_local,
            gem_counts,
            selected_element,
            gears_by_name if isinstance(gears_by_name, dict) else {},
            minis_by_name if isinstance(minis_by_name, dict) else {},
            base_stats,
        )
        if not isinstance(computed, dict) or not computed:
            return details_obj

        out = dict(details_obj)
        out.pop("st", None)  # Always repack from Stats at persistence time.
        out["Stats"] = computed
        return out

    own_conn = conn is None
    if conn is None:
        resolved_db_path = str(db_path or get_evolution_db_path())
        conn = get_db_connection(resolved_db_path)
    else:
        resolved_db_path = str(db_path or get_evolution_db_path())

    try:
        try:
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            logger.debug(f"database:_recompute_stats_in_details_for_persistence: {e}")

        _t_params0 = time.perf_counter()
        loadouts_params = []
        deferred_fg_loadouts_params = []
        fg_loadouts_params = []

        # Compact name encoding maps (gear/minis). These tables are populated at init_db()
        # and extended lazily for previously unseen names.
        encoding_maps = _load_piece_name_encoding_maps(conn, db_path=resolved_db_path)

        def _encode_gear_names_to_blob(gear_names: list[str]) -> bytes:
            nonlocal encoding_maps
            missing = [n for n in (gear_names or []) if n and n not in encoding_maps.gear_name_to_id]
            if missing:
                _insert_missing_piece_names(conn, table=_GEAR_NAME_ENCODING_TABLE, names=missing)
                encoding_maps = _load_piece_name_encoding_maps(conn, db_path=resolved_db_path)
            ids: list[int] = []
            for n in gear_names or []:
                if not n:
                    continue
                i = int(encoding_maps.gear_name_to_id.get(n, 0) or 0)
                if i > 0:
                    ids.append(i)
            return bytes(_pack_id_list(ids))

        def _encode_mini_groups_to_blob(groups: list[list[str]]) -> bytes:
            nonlocal encoding_maps
            flat: list[str] = []
            for g in groups or []:
                if not g:
                    continue
                for n in g:
                    if n:
                        flat.append(str(n))
            missing = [n for n in sorted(set(flat)) if n and n not in encoding_maps.mini_name_to_id]
            if missing:
                _insert_missing_piece_names(conn, table=_MINI_NAME_ENCODING_TABLE, names=missing)
                encoding_maps = _load_piece_name_encoding_maps(conn, db_path=resolved_db_path)
            id_groups: list[list[int]] = []
            for g in groups or []:
                if not g:
                    continue
                ids: list[int] = []
                for n in g:
                    if not n:
                        continue
                    i = int(encoding_maps.mini_name_to_id.get(str(n), 0) or 0)
                    if i > 0:
                        ids.append(i)
                if ids:
                    id_groups.append(ids)
            return bytes(_pack_id_groups(id_groups))

        entry_to_effective: Dict[int, Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]] = {}
        for i, entry in enumerate(deduplicated_entries):
            entry_id = int(id(entry))
            eff = effective_cache_by_entry_id.get(entry_id)
            if entry_id not in effective_cache_by_entry_id:
                eff = _effective_hash_for_entry(entry)
                effective_cache_by_entry_id[entry_id] = eff
            entry_to_effective[i] = eff

        for i, entry in enumerate(deduplicated_entries):
            score = _coerce_int(entry.get("score", 0))
            fg_score = _coerce_int(entry.get("fg_score", 0))
            fg_base_score = score
            try:
                raw_fg_base = entry.get("fg_base_score")
            except Exception as e:
                logger.debug(f"database:_encode_mini_groups_to_blob: {e}")
                raw_fg_base = None
            if raw_fg_base is not None:
                fg_base_score = _coerce_int(raw_fg_base)
                if fg_base_score <= 0:
                    fg_base_score = score
            gear = entry.get("gear", [])
            minis = entry.get("minis", [])
            details = entry.get("details", {})
            force_data = entry.get("force")

            eff = entry_to_effective.get(i)
            if eff is not None and isinstance(details, dict):
                (_loadout_hash_eff, _mini_sigs_eff, p_color_eff, s_color_eff, sel_color_eff) = eff
                if (
                    (p_color_eff or s_color_eff)
                    and not (details.get("PrimaryColor") or details.get("Primary Color"))
                    and not (details.get("SecondaryColor") or details.get("Secondary Color"))
                ):
                    details_out = dict(details)
                    if p_color_eff:
                        details_out["PrimaryColor"] = p_color_eff
                    if s_color_eff:
                        details_out["SecondaryColor"] = s_color_eff
                    if sel_color_eff and not (
                        details_out.get("SelectedElement") or details_out.get("Selected Element")
                    ):
                        details_out["SelectedElement"] = sel_color_eff
                    details = details_out

            if fg_score <= 0 and force_data is not None:
                fg_score = fg_score_from_force(force_data)

            force_data = _normalize_force_for_persistence(force_data, fg_score=fg_score)
            force_base_score = _force_payload_base_score(force_data)
            if force_base_score > 0:
                fg_base_score = force_base_score
            details = _normalize_details_for_persistence(
                details,
                score=score,
                fg_score=fg_score,
                force_data=force_data,
                preserve_attempt_meta=bool(preserve_attempt_meta),
            )

            gear_names = _compact_gear_for_db(gear)
            mini_names = _compact_minis_for_db(minis)

            if eff is not None:
                (loadout_hash, _mini_sigs, p_color, s_color, sel_color) = eff
                groups = canonical_minis_groups_from_names(
                    mini_names,
                    minis_by_name,
                    p_color,
                    s_color,
                    sel_color,
                )
                # Legacy mini-group representation contract:
                # - choose distinct representatives across duplicate groups when possible, and
                # - rotate each group so the representative becomes the first element (consumers often read `g[0]`).
                groups = rotate_mini_groups_for_slot_display(groups)
                mini_names = [g[0] for g in groups if g]
            else:
                warn_fallback(
                    "db.minis_groups.singletons",
                    "effective mini grouping unavailable; persisting singleton mini groups",
                    context={"song_name": song_name, "team_buff": team_buff},
                    fatal=False,
                )
                loadout_hash = _loadout_hash_from_names(gear_names, mini_names)
                groups = [[n] for n in mini_names]

            # Canonicalize persisted Stats:
            # - Use representative mini names for equivalence groups (legacy DB behavior)
            # - Avoid persisting config-tainted Stats snapshots (ElementalGems/UserInputStatsGems)
            # - Preserve unknown-gear/minis cases (tests/tools may use synthetic names)
            details_unpacked = _unpack_stats_after_load(details) if isinstance(details, dict) else details
            current_stats = details_unpacked.get("Stats") if isinstance(details_unpacked, dict) else None
            has_stats = isinstance(current_stats, dict) and len(current_stats) > 0
            can_recompute = (eff is not None) and _can_recompute_stats_for_persistence(gear_names, mini_names)
            if not has_stats:
                # Defensive: never persist empty Stats.
                if can_recompute:
                    details = _recompute_stats_in_details_for_persistence(
                        details_unpacked,
                        gear_names_local=gear_names,
                        mini_names_local=mini_names,
                        team_color=str(
                            details_unpacked.get("PrimaryColor") or details_unpacked.get("Primary Color") or ""
                        ).strip(),
                    )
                else:
                    details = _ensure_stats_in_details(
                        details_unpacked,
                        gear,
                        minis,
                        minis_by_name,
                        team_buff=team_buff,
                        team_color=str(
                            details_unpacked.get("PrimaryColor") or details_unpacked.get("Primary Color") or ""
                        ).strip(),
                    )
            else:
                details = details_unpacked

            if (
                isinstance(details, dict)
                and isinstance(details.get("Stats"), dict)
                and details.get("Stats")
                and details.get("st") is not None
            ):
                details = dict(details)
                details.pop("st", None)

            gear_ids_blob = _encode_gear_names_to_blob(gear_names) or None
            minis_ids_blob = _encode_mini_groups_to_blob(groups) or None

            # Compact storage: names are persisted via encoding tables + BLOB IDs.
            details_storage = _pack_stats_for_storage(_strip_computed_details_fields(details)) if details else None
            details_json = _json_dumps_compact(details_storage) if details_storage else None
            force_storage = _compact_force_details_for_storage(force_data)
            force_json = _json_dumps_compact(force_storage) if force_storage else None

            loadouts_params.append(
                (
                    song_name,
                    team_buff,
                    loadout_hash,
                    score,
                    fg_score,
                    gear_ids_blob,
                    minis_ids_blob,
                    details_json,
                    None,
                )
            )
            if bool(entry.get("_deferred_fg_update")):
                deferred_fg_loadouts_params.append(loadouts_params.pop())

            if force_data is not None and fg_score > fg_base_score:
                fg_details = _base_details_from_force_payload(details, force_data)
                if not fg_details:
                    continue
                fg_details_storage = _pack_stats_for_storage(_strip_computed_details_fields(fg_details))
                fg_details_json = _json_dumps_compact(fg_details_storage) if fg_details_storage else None
                fg_loadouts_params.append(
                    (
                        song_name,
                        team_buff,
                        loadout_hash,
                        fg_base_score,
                        fg_score,
                        gear_ids_blob,
                        minis_ids_blob,
                        fg_details_json,
                        force_json,
                    )
                )

        _log_timing("build_params_json", time.perf_counter() - _t_params0)

        if loadouts_params:
            _t_ins0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO team_buff_loadouts (
                    song_name, team_buff, loadout_hash, score, fg_score,
                    gear_ids_blob, minis_ids_blob, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, team_buff, loadout_hash) DO UPDATE SET
                    score = CASE WHEN excluded.score > score THEN excluded.score ELSE score END,
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_ids_blob = CASE WHEN excluded.score >= score THEN excluded.gear_ids_blob ELSE gear_ids_blob END,
                    minis_ids_blob = CASE WHEN excluded.score >= score THEN excluded.minis_ids_blob ELSE minis_ids_blob END,
                    details_json = CASE WHEN excluded.score >= score THEN excluded.details_json ELSE details_json END,
                    force_details_json = NULL,
                    timestamp = strftime('%s', 'now')
            """,
                loadouts_params,
            )
            _log_timing("insert_team_buff_loadouts", time.perf_counter() - _t_ins0)

        if deferred_fg_loadouts_params:
            _t_ins0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO team_buff_loadouts (
                    song_name, team_buff, loadout_hash, score, fg_score,
                    gear_ids_blob, minis_ids_blob, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, team_buff, loadout_hash) DO UPDATE SET
                    -- Deferred FG-only update: preserve base leaderboard payload (score/details/gear/minis)
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_ids_blob = CASE WHEN gear_ids_blob IS NULL THEN excluded.gear_ids_blob ELSE gear_ids_blob END,
                    minis_ids_blob = CASE WHEN minis_ids_blob IS NULL THEN excluded.minis_ids_blob ELSE minis_ids_blob END,
                    details_json = CASE WHEN details_json IS NULL THEN excluded.details_json ELSE details_json END,
                    force_details_json = NULL,
                    timestamp = strftime('%s', 'now')
            """,
                deferred_fg_loadouts_params,
            )
            _log_timing("insert_team_buff_loadouts_deferred_fg", time.perf_counter() - _t_ins0)

        if fg_loadouts_params:
            _t_insfg0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO team_buff_fg_loadouts (
                    song_name, team_buff, loadout_hash, score, fg_score,
                    gear_ids_blob, minis_ids_blob, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, team_buff, loadout_hash) DO UPDATE SET
                    fg_score = MAX(fg_score, excluded.fg_score),
                    score = CASE
                        WHEN excluded.fg_score > fg_score THEN excluded.score
                        WHEN excluded.fg_score = fg_score AND excluded.score > score THEN excluded.score
                        ELSE score
                    END,
                    gear_ids_blob = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.score > score)
                            THEN excluded.gear_ids_blob
                        ELSE gear_ids_blob
                    END,
                    minis_ids_blob = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.score > score)
                            THEN excluded.minis_ids_blob
                        ELSE minis_ids_blob
                    END,
                    details_json = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.score > score)
                            THEN excluded.details_json
                        ELSE details_json
                    END,
                    force_details_json = CASE
                        WHEN excluded.fg_score > fg_score THEN excluded.force_details_json
                        WHEN excluded.fg_score = fg_score AND excluded.score > score AND excluded.force_details_json IS NOT NULL
                            THEN excluded.force_details_json
                        WHEN excluded.fg_score = fg_score AND excluded.score = score AND excluded.force_details_json IS NOT NULL
                            THEN excluded.force_details_json
                        ELSE force_details_json
                    END,
                    timestamp = strftime('%s', 'now')
                """,
                fg_loadouts_params,
            )
            _log_timing("insert_team_buff_fg_loadouts", time.perf_counter() - _t_insfg0)

        # Enforce FG leaderboard invariant.
        _t_inv0 = time.perf_counter()
        conn.execute(
            """
            DELETE FROM team_buff_fg_loadouts
            WHERE song_name = ?
            AND team_buff = ?
            AND fg_score <= score
            """,
            (song_name, team_buff),
        )

        conn.execute(
            """
            UPDATE team_buff_loadouts
            SET fg_score = score
            WHERE song_name = ?
            AND team_buff = ?
            AND fg_score > score
            AND NOT EXISTS (
                SELECT 1
                FROM team_buff_fg_loadouts fg
                WHERE fg.song_name = team_buff_loadouts.song_name
                AND fg.team_buff = team_buff_loadouts.team_buff
                AND fg.loadout_hash = team_buff_loadouts.loadout_hash
            )
            """,
            (song_name, team_buff),
        )
        _log_timing("delete_team_buff_fg_invariant", time.perf_counter() - _t_inv0)

        # Base coverage rows own score/loadout identity only. The replayable FG
        # payload belongs in team_buff_fg_loadouts; duplicating it across every
        # retained base row makes the repaired 51-row frontier scale like a
        # queue dump instead of a compact seed frontier.
        _t_clear0 = time.perf_counter()
        conn.execute(
            """
            UPDATE team_buff_loadouts
            SET force_details_json = NULL
            WHERE song_name = ?
            AND team_buff = ?
            AND force_details_json IS NOT NULL
            """,
            (song_name, team_buff),
        )
        _log_timing("clear_base_force_details", time.perf_counter() - _t_clear0)

        # Prune BOTH tables to `LOADOUTS_PER_SONG_LIMIT` for this (song, team_buff).
        for table in ["team_buff_loadouts", "team_buff_fg_loadouts"]:
            _t_cnt0 = time.perf_counter()
            cursor = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE song_name = ? AND team_buff = ?",
                (song_name, team_buff),
            )
            count = cursor.fetchone()[0]
            _log_timing(f"count_{table}", time.perf_counter() - _t_cnt0)
            if count <= LOADOUTS_PER_SONG_LIMIT:
                continue

            if table == "team_buff_loadouts":
                _t_pr0 = time.perf_counter()
                conn.execute(
                    """
                    DELETE FROM team_buff_loadouts
                    WHERE song_name = ?
                    AND team_buff = ?
                    AND loadout_hash NOT IN (
                        SELECT loadout_hash FROM team_buff_loadouts
                        WHERE song_name = ?
                        AND team_buff = ?
                        ORDER BY score DESC
                        LIMIT ?
                    )
                    """,
                    (song_name, team_buff, song_name, team_buff, LOADOUTS_PER_SONG_LIMIT),
                )
                _log_timing("prune_team_buff_loadouts", time.perf_counter() - _t_pr0)
            else:
                _t_prfg0 = time.perf_counter()
                conn.execute(
                    """
                    DELETE FROM team_buff_fg_loadouts
                    WHERE song_name = ?
                    AND team_buff = ?
                    AND loadout_hash NOT IN (
                        SELECT loadout_hash FROM team_buff_fg_loadouts
                        WHERE song_name = ?
                        AND team_buff = ?
                        ORDER BY fg_score DESC
                        LIMIT ?
                    )
                    """,
                    (song_name, team_buff, song_name, team_buff, LOADOUTS_PER_SONG_LIMIT),
                )
                _log_timing("prune_team_buff_fg_loadouts", time.perf_counter() - _t_prfg0)

        verify_integrity = env_flag("DB_VERIFY_WRITE_INTEGRITY", "0")
        if verify_integrity:
            strict = env_flag("DB_STRICT_WRITE_INTEGRITY", "0")

            def _warn_or_raise(msg: str) -> None:
                if strict:
                    raise RuntimeError(msg)
                warnings.warn(msg, RuntimeWarning, stacklevel=2)

            def _verify_table_row(
                *, table: str, loadout_hash: str, expected_score: int, expected_fg_score: int
            ) -> None:
                row = conn.execute(
                    f"SELECT score, fg_score, gear_ids_blob, minis_ids_blob, details_json FROM {table} "
                    "WHERE song_name = ? AND team_buff = ? AND loadout_hash = ?",
                    (song_name, team_buff, loadout_hash),
                ).fetchone()
                if row is None:
                    _warn_or_raise(
                        f"[DB] Missing expected row after persistence: table={table} song={song_name!r} "
                        f"team_buff={team_buff!r} hash={loadout_hash}"
                    )
                    return

                got_score = int(row["score"] or 0)
                got_fg_score = int(row["fg_score"] or 0)
                if table != "team_buff_fg_loadouts" or got_fg_score <= int(expected_fg_score):
                    if got_score < int(expected_score):
                        _warn_or_raise(
                            f"[DB] Score regressed after persistence (possible override/race): table={table} "
                            f"song={song_name!r} team_buff={team_buff!r} hash={loadout_hash} "
                            f"expected>={int(expected_score)} got={got_score}"
                        )
                if got_fg_score < int(expected_fg_score):
                    _warn_or_raise(
                        f"[DB] FG score regressed after persistence (possible override/race): table={table} "
                        f"song={song_name!r} team_buff={team_buff!r} hash={loadout_hash} "
                        f"expected>={int(expected_fg_score)} got={got_fg_score}"
                    )

                # Hash consistency check: ensure persisted (gear/minis/details) re-hash back to the stored hash.
                try:
                    gear_ids_blob_row = row["gear_ids_blob"]
                    minis_ids_blob_row = row["minis_ids_blob"]

                    gear_names_row: list[str] = []
                    ids = _unpack_id_list(gear_ids_blob_row)
                    if ids:
                        gear_names_row = [
                            str(encoding_maps.gear_id_to_name.get(int(i), "") or "") for i in ids if int(i) > 0
                        ]
                        gear_names_row = [n for n in gear_names_row if n]

                    mini_groups_row: list[list[str]] = []
                    id_groups = _unpack_id_groups(minis_ids_blob_row)
                    if id_groups:
                        for g in id_groups:
                            if not g:
                                continue
                            names = [str(encoding_maps.mini_id_to_name.get(int(i), "") or "") for i in g if int(i) > 0]
                            names = [n for n in names if n]
                            if names:
                                mini_groups_row.append(names)
                    mini_names_row = representative_mini_names(mini_groups_row)
                    details_row = _json_loads(row["details_json"]) if row["details_json"] else {}
                    p_color, s_color, sel_color = extract_song_colors(details_row)
                    if p_color or s_color:
                        mini_sigs_row = [
                            effective_mini_signature_for_name(n, minis_by_name, p_color, s_color, sel_color)
                            for n in mini_names_row
                        ]
                        expected_hash = effective_loadout_hash_from_names(gear_names_row, mini_sigs_row)
                    else:
                        expected_hash = _loadout_hash_from_names(gear_names_row, mini_names_row)
                    if expected_hash and str(expected_hash) != str(loadout_hash):
                        _warn_or_raise(
                            f"[DB] Loadout hash mismatch after persistence (possible override/race): table={table} "
                            f"song={song_name!r} team_buff={team_buff!r} stored={loadout_hash} expected={expected_hash}"
                        )
                except Exception as e:
                    logger.debug(f"database:_verify_table_row: {e}")

            try:
                if loadouts_params:
                    best = max(loadouts_params, key=lambda t: int(t[3] or 0))
                    _verify_table_row(
                        table="team_buff_loadouts",
                        loadout_hash=str(best[2]),
                        expected_score=int(best[3] or 0),
                        expected_fg_score=int(best[4] or 0),
                    )
                if fg_loadouts_params:
                    best_fg = max(fg_loadouts_params, key=lambda t: int(t[4] or 0))
                    _verify_table_row(
                        table="team_buff_fg_loadouts",
                        loadout_hash=str(best_fg[2]),
                        expected_score=int(best_fg[3] or 0),
                        expected_fg_score=int(best_fg[4] or 0),
                    )
            except Exception as exc:
                _warn_or_raise(
                    f"[DB] Write integrity verification failed: song={song_name!r} team_buff={team_buff!r} "
                    f"error={type(exc).__name__}: {exc}"
                )

        if commit:
            _t_commit0 = time.perf_counter()
            conn.commit()
            _log_timing("commit", time.perf_counter() - _t_commit0)
    except sqlite3.Error as e:
        print(f"[DB] Error saving TeamBuff batch loadouts: {e}")
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        if own_conn:
            try:
                conn.execute("PRAGMA synchronous=FULL;")
            except sqlite3.Error:
                pass
            conn.close()
        _log_timing("total", time.perf_counter() - _t0)


def get_best_loadouts(
    song_name: str,
    limit: int = LOADOUTS_PER_SONG_LIMIT,
    gears_by_name: Optional[Dict[str, Any]] = None,
    minis_by_name: Optional[Dict[str, Any]] = None,
    team_buff: str = "T5",
    *,
    allow_fallback: bool = True,
    db_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve the top N loadouts for a song to seed the GA.

    Storage format:
    - gear_ids_blob: varint-packed list of encoding-table IDs (decoded via `gear_name_encoding`)
    - minis_ids_blob: varint-packed groups of IDs with 0 separators (decoded via `mini_name_encoding`)
    If gears_by_name/minis_by_name are provided, expands representative names to full stat dicts.

    Args:
        song_name: Name of the song
        limit: Maximum number of loadouts to retrieve
        gears_by_name: Optional dict mapping gear names to full dicts
        minis_by_name: Optional dict mapping mini names to full dicts
        team_buff: TeamBuff tier to seed from (defaults to T5)

    Returns:
        list: List of loadout dictionaries
    """
    resolved_db_path = str(db_path or get_evolution_db_path() or "").strip()
    if not resolved_db_path or not os.path.exists(resolved_db_path):
        return []

    song_name = str(song_name or "").strip()

    team_buff = normalize_team_buff(team_buff, default="T5")
    query_team_buffs = team_buff_query_values(team_buff, default=team_buff)
    strict_seed_hash = str(env_get("DB_STRICT_SEED_HASH", "0") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    # PERF: use a cached per-thread connection for read-heavy call sites.
    conn = get_db_connection_cached(resolved_db_path, allow_fallback=allow_fallback)
    try:
        results: list[dict[str, Any]] = []
        by_hash: dict[str, dict[str, Any]] = {}

        encoding_maps = _load_piece_name_encoding_maps(conn, db_path=resolved_db_path)

        def _materialize_common(row) -> tuple[str, list[str], list[list[str]], list[str], dict[str, Any], dict | None]:
            loadout_hash = str(row["loadout_hash"])
            gear_names: list[str] = []
            try:
                gear_ids_blob = row["gear_ids_blob"]
            except Exception as e:
                logger.debug(f"database:_materialize_common: {e}")
                gear_ids_blob = None
            if gear_ids_blob:
                ids = _unpack_id_list(gear_ids_blob)
                if ids:
                    gear_names = [str(encoding_maps.gear_id_to_name.get(int(i), "") or "") for i in ids]
                    gear_names = [n for n in gear_names if n]

            mini_groups: list[list[str]] = []
            try:
                minis_ids_blob = row["minis_ids_blob"]
            except Exception as e:
                logger.debug(f"database:_materialize_common: {e}")
                minis_ids_blob = None
            if minis_ids_blob:
                id_groups = _unpack_id_groups(minis_ids_blob)
                if id_groups:
                    for g in id_groups:
                        names = [str(encoding_maps.mini_id_to_name.get(int(i), "") or "") for i in g]
                        names = [n for n in names if n]
                        if names:
                            mini_groups.append(names)
            mini_names = representative_mini_names(mini_groups)
            details = _json_loads(row["details_json"]) if row["details_json"] else {}
            details = _unpack_stats_after_load(details)
            # DB seeding doesn't need large derived fields; keep the in-memory payload lightweight.
            details = _strip_computed_details_fields(details)

            # Optional strict verifier: detect corrupted/mismatched hashes before seeding.
            if strict_seed_hash:
                try:
                    p_color, s_color, sel_color = extract_song_colors(details)
                    if p_color or s_color:
                        lookup = minis_by_name or get_minis_by_name_cached()
                        mini_sigs = [
                            effective_mini_signature_for_name(n, lookup, p_color, s_color, sel_color)
                            for n in mini_names
                        ]
                        expected = effective_loadout_hash_from_names(gear_names, mini_sigs)
                    else:
                        expected = _loadout_hash_from_names(gear_names, mini_names)
                    if expected and str(expected) != str(loadout_hash):
                        warnings.warn(
                            f"[DB] Loadout hash mismatch (seed): song={song_name!r} team_buff={team_buff!r} "
                            f"stored={loadout_hash} expected={expected}",
                            RuntimeWarning,
                            stacklevel=2,
                        )
                except Exception as e:
                    # Best-effort only; never break seeding on verifier errors.
                    logger.debug(f"database:_materialize_common: {e}")

            force_block = _json_loads(row["force_details_json"]) if row["force_details_json"] else None
            force_obj = force_block if isinstance(force_block, dict) else None
            if isinstance(force_obj, dict):
                force_obj = _strip_computed_details_fields(force_obj)
                nested = force_obj.get("details")
                if isinstance(nested, dict):
                    nested_out = _strip_computed_details_fields(nested)
                    if nested_out is not nested:
                        force_obj = dict(force_obj)
                        force_obj["details"] = nested_out
            return loadout_hash, gear_names, mini_groups, mini_names, details, force_obj

        def _expand_items(gear_names: list[str], mini_names: list[str]):
            # Expand names to full dicts if lookup provided
            if gears_by_name:
                gear_data = _expand_gear_from_db(gear_names, gears_by_name)
            else:
                gear_data = gear_names  # Return as names for hash lookups

            if minis_by_name:
                minis_data = _expand_minis_from_db(mini_names, minis_by_name)
            else:
                minis_data = mini_names
            return gear_data, minis_data

        # 1. Fetch Top Base Score Loadouts (canonical base seed rows)
        query_placeholders = ",".join("?" for _ in query_team_buffs)
        cursor = conn.execute(
            f"""
            SELECT loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
            FROM team_buff_loadouts
            WHERE song_name = ? AND UPPER(team_buff) IN ({query_placeholders})
            ORDER BY score DESC
            LIMIT ?
            """,
            (song_name, *query_team_buffs, limit),
        )
        for row in cursor:
            loadout_hash, gear_names, mini_groups, mini_names, details, force_obj = _materialize_common(row)
            if loadout_hash in by_hash:
                continue
            gear_data, minis_data = _expand_items(gear_names, mini_names)
            entry = {
                "loadout_hash": loadout_hash,
                "score": row["score"],
                "fg_score": row["fg_score"],
                "gear": gear_data,
                "minis": minis_data,
                "mini_groups": mini_groups,
                "details": details,
                "force": force_obj,
            }
            by_hash[loadout_hash] = entry
            results.append(entry)

        # 2. Fetch Top ForceGreats Loadouts (paired base+fg scores)
        cursor = conn.execute(
            f"""
            SELECT loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
            FROM team_buff_fg_loadouts
            WHERE song_name = ? AND UPPER(team_buff) IN ({query_placeholders})
            ORDER BY fg_score DESC
            LIMIT ?
            """,
            (song_name, *query_team_buffs, limit),
        )
        for row in cursor:
            loadout_hash, gear_names, mini_groups, mini_names, details, force_obj = _materialize_common(row)
            gear_data, minis_data = _expand_items(gear_names, mini_names)
            fg_score = row["fg_score"]
            fg_base_score = row["score"]

            entry = by_hash.get(loadout_hash)
            if entry is None:
                entry = {
                    "loadout_hash": loadout_hash,
                    "score": row["score"],
                    "fg_score": fg_score,
                    "gear": gear_data,
                    "minis": minis_data,
                    "mini_groups": mini_groups,
                    "details": details,
                    "force": force_obj,
                }
                by_hash[loadout_hash] = entry
                results.append(entry)
                continue

            # Preserve best base score for this hash, but also preserve the paired base score for the
            # best-FG payload so downstream FG comparisons use the correct base context.
            try:
                existing_fg = int(entry.get("fg_score", 0) or 0)
            except Exception as e:
                logger.debug(f"database:_expand_items: {e}")
                existing_fg = 0
            try:
                fg_i = int(fg_score or 0)
            except Exception as e:
                logger.debug(f"database:_expand_items: {e}")
                fg_i = 0

            if fg_i > existing_fg:
                entry["fg_score"] = fg_score
                entry["force"] = force_obj
                entry["fg_base_score"] = fg_base_score
            elif fg_i == existing_fg:
                # Fill missing paired base score / force payload when we already had the same FG score.
                if "fg_base_score" not in entry:
                    entry["fg_base_score"] = fg_base_score
                if entry.get("force") is None and force_obj is not None:
                    entry["force"] = force_obj

        return results
    except (sqlite3.Error, json.JSONDecodeError) as e:
        if not allow_fallback and isinstance(e, sqlite3.Error):
            raise
        print(f"[DB] Error retrieving loadouts: {e}")
        return []
    finally:
        # Thread-local connection is intentionally not closed here.
        pass


def get_song_names_present_in_db(song_names: Iterable[str], db_path: Optional[str] = None) -> set[str]:
    """
    Return the subset of song names that are already present in the DB.

    Presence is defined as having a row in `songs` OR any row in the loadout tables.
    """
    names = [name for name in (song_names or []) if name]
    if not names:
        return set()

    if db_path is None:
        db_path = get_evolution_db_path()
    db_path = str(db_path)
    if not db_path or not os.path.exists(db_path):
        return set()

    conn = get_db_connection_cached(db_path)
    present: set[str] = set()
    batch_size = 900  # sqlite default parameter cap is commonly 999
    for offset in range(0, len(names), batch_size):
        batch = names[offset : offset + batch_size]
        placeholders = ",".join("?" for _ in batch)

        try:
            rows = conn.execute(
                f"SELECT name FROM songs WHERE name IN ({placeholders})",
                batch,
            ).fetchall()
            present.update(row[0] for row in rows if row and row[0])
        except sqlite3.Error:
            pass

        for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
            try:
                rows = conn.execute(
                    f"SELECT DISTINCT song_name FROM {table} WHERE song_name IN ({placeholders})",
                    batch,
                ).fetchall()
                present.update(row[0] for row in rows if row and row[0])
            except sqlite3.Error:
                continue

    return present


def prioritize_song_queue_missing_db(
    song_queue: list[tuple[str, str, str]],
    db_path: Optional[str] = None,
) -> list[tuple[str, str, str]]:
    """
    Reorder a discovered song queue so songs not in the DB run first.

    Stable partition: preserves relative order within each group.
    """
    if not song_queue:
        return []

    present = get_song_names_present_in_db((item[1] for item in song_queue), db_path=db_path)
    if not present:
        return song_queue

    missing: list[tuple[str, str, str]] = []
    existing: list[tuple[str, str, str]] = []
    for item in song_queue:
        (existing if item[1] in present else missing).append(item)
    return missing + existing


def upsert_pending_fg_job(song_name: str, candidates: List[Dict[str, Any]]) -> None:
    """
    Persist a crash-safe pending ForceGreats job for a song.

    This stores a compact candidate list so FG can be computed later without
    rerunning GA (e.g. when FG is deferred/batched for throughput).
    """
    song_name = str(song_name or "").strip()
    if not song_name:
        return
    if not candidates:
        delete_pending_fg_job(song_name)
        return

    payload = _json_dumps_compact(candidates)
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO pending_fg_jobs (song_name, candidates_json, created_ts, updated_ts)
            VALUES (?, ?, strftime('%s','now'), strftime('%s','now'))
            ON CONFLICT(song_name) DO UPDATE SET
                candidates_json = excluded.candidates_json,
                updated_ts = strftime('%s','now')
            """,
            (song_name, payload),
        )
        conn.commit()
    except sqlite3.Error:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
    finally:
        conn.close()


def delete_pending_fg_job(song_name: str) -> None:
    song_name = str(song_name or "").strip()
    if not song_name:
        return
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        conn.execute("DELETE FROM pending_fg_jobs WHERE song_name = ?", (song_name,))
        conn.commit()
    except sqlite3.Error:
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
    finally:
        conn.close()


def list_pending_fg_jobs(limit: int = 0) -> List[Dict[str, Any]]:
    """
    List pending FG jobs, newest-first.

    Returns dicts with keys: song_name, candidates, created_ts, updated_ts.
    """
    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        lim = int(limit or 0)
        if lim > 0:
            rows = conn.execute(
                """
                SELECT song_name, candidates_json, created_ts, updated_ts
                FROM pending_fg_jobs
                ORDER BY COALESCE(updated_ts, created_ts) DESC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT song_name, candidates_json, created_ts, updated_ts
                FROM pending_fg_jobs
                ORDER BY COALESCE(updated_ts, created_ts) DESC
                """,
            ).fetchall()

        out: List[Dict[str, Any]] = []
        for r in rows or []:
            try:
                song = r["song_name"] if isinstance(r, sqlite3.Row) else r[0]
                cand_json = r["candidates_json"] if isinstance(r, sqlite3.Row) else r[1]
                created_ts = r["created_ts"] if isinstance(r, sqlite3.Row) else r[2]
                updated_ts = r["updated_ts"] if isinstance(r, sqlite3.Row) else r[3]
            except Exception as e:
                logger.debug(f"database:list_pending_fg_jobs: {e}")
                continue

            try:
                candidates = _json_loads(cand_json) if cand_json else []
            except Exception as e:
                logger.debug(f"database:list_pending_fg_jobs: {e}")
                candidates = []

            out.append(
                {
                    "song_name": song,
                    "candidates": candidates,
                    "created_ts": created_ts,
                    "updated_ts": updated_ts,
                }
            )
        return out
    except sqlite3.Error:
        return []
    finally:
        conn.close()
