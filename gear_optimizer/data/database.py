"""
Database operations for the gear optimizer.
Handles all SQLite interactions for loadout persistence and retrieval.
"""

import hashlib
import json
import os
import sqlite3
import time
import threading
import atexit
import weakref
from collections.abc import Iterable
from typing import Dict, List, Optional, Any
from urllib.parse import quote
from ..core.constants import LOADOUTS_PER_SONG_LIMIT, PATHS
from ..core.types import PersistenceEntry
from .migrations import ensure_schema
from .loadout_equivalence import (
    decode_minis_json,
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    encode_minis_groups,
    extract_song_colors,
    get_minis_by_name_cached,
    canonical_minis_groups_from_names,
    representative_mini_names,
)


def get_evolution_db_path() -> str:
    """
    Return the configured evolution DB location (env override supported).

    Returns:
        str: Path to evolution database file
    """
    env_path = os.getenv("EVOLUTION_DB_PATH", "")
    return env_path if env_path else PATHS.evolution_db_default


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
    except Exception:
        pass
    conn = sqlite3.connect(db_path, timeout=float(timeout))
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
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
    except Exception:
        pass
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
    except Exception:
        pass


def _close_all_registered_db_conns() -> None:
    try:
        with _DB_CONN_REGISTRY_LOCK:
            conns = list(_DB_CONN_REGISTRY)
    except Exception:
        conns = []
    for c in conns:
        try:
            c.close()
        except Exception:
            pass


atexit.register(_close_all_registered_db_conns)


def get_db_connection_cached(db_path: Optional[str] = None) -> sqlite3.Connection:
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
    except Exception:
        conns = {}

    conn = conns.get(db_path)
    if conn is not None:
        return conn

    # Default to a small non-zero timeout to allow brief lock contention during
    # write bursts without immediate failure. This prevents spurious fallbacks
    # to the empty in-memory DB when the AsyncDbSaver is actively writing.
    try:
        read_timeout = float(os.environ.get("DB_READ_TIMEOUT_SEC", "0.2") or "0.2")
    except Exception:
        read_timeout = 0.2

    try:
        conn = get_db_connection_readonly(db_path, timeout=read_timeout)
    except sqlite3.Error:
        # Best-effort: DB might be locked briefly during heavy write bursts.
        # Never block the GPU feed loop on a read-only seed/context fetch.
        fallback = getattr(_DB_TLS, "fallback_conn", None)
        if fallback is None:
            try:
                fallback = sqlite3.connect(":memory:")
                fallback.row_factory = sqlite3.Row
                setattr(_DB_TLS, "fallback_conn", fallback)
                _register_db_conn(fallback)
            except Exception:
                # Last resort: re-raise so callers can handle it.
                raise
        return fallback

    conns[db_path] = conn
    _register_db_conn(conn)
    return conn


def init_db():
    """
    Initialize the SQLite database schema if it doesn't exist.

    Storage optimization: gear_json stores only names (not full stats) as a JSON array of strings.
    minis_json stores mini variant groups as a JSON array of arrays, e.g. [["MiniA","MiniA2"], ["MiniB"], ...].
    Full stats are looked up from Gears.csv/Minis.csv when loading.
    """

    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    try:
        # `get_db_connection()` already ensures schema/migrations; keep this function
        # as a stable entry point for callers/tests.
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
) -> tuple[int, int, int, int]:
    """
    Fetch per-song attempt counters and best scores from `songs`.

    Returns:
        (attempt_lifetime, attempts_first, best_score, best_fg_score)
    """
    song_name = str(song_name or "").strip()
    if not song_name:
        return (0, 0, 0, 0)

    close_conn = False
    if conn is None:
        conn = get_db_connection_cached(get_evolution_db_path())
        close_conn = False

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
        except Exception:
            attempt_lifetime = 0
        try:
            attempts_first = int(row["attempts_first"] or 0)
        except Exception:
            attempts_first = 0
        try:
            best_score = int(row["best_score"] or 0)
        except Exception:
            best_score = 0
        try:
            best_fg_score = int(row["best_fg_score"] or 0)
        except Exception:
            best_fg_score = 0
        return (attempt_lifetime, attempts_first, best_score, best_fg_score)
    except sqlite3.Error:
        # Defensive: if the schema hasn't been migrated yet, treat as missing.
        return (0, 0, 0, 0)
    finally:
        if close_conn:
            try:
                conn.close()
            except Exception:
                pass


def update_song_counters(
    song_name: str,
    *,
    processed_run: bool,
    record_improved: bool,
    conn: Optional[sqlite3.Connection] = None,
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
        conn = get_db_connection(get_evolution_db_path())
        close_conn = True

    pr = 1 if processed_run else 0
    ri = 1 if record_improved else 0

    try:
        with conn:
            # Ensure row exists (older DBs can have loadouts without a songs row).
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
            except Exception:
                pass


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
    Handles both dicts and strings.

    Args:
        mini_list: List of mini items (dicts or strings)

    Returns:
        list: List of mini names
    """
    if not mini_list:
        return []
    result = []
    for m in mini_list:
        if isinstance(m, dict):
            name = m.get("Name", "")
        else:
            name = str(m) if m else ""
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
    """
    Generate a stable loadout hash from pre-extracted item names.

    Notes:
    - Hashing is order-invariant: names are sorted before hashing.
    - Inputs should already be filtered to non-empty strings.
    """
    g = sorted([n for n in (gear_names or []) if n])
    m = sorted([n for n in (mini_names or []) if n])
    payload = f"GEAR:{'|'.join(g)}::MINIS:{'|'.join(m)}"
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


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


def _deduplicate_db_loadouts(conn, song_name, table_name="loadouts"):
    """
    Remove duplicate loadouts from database for a specific song and table.

    Identifies and removes tie-breakers:
    - Same score with exact same loadout hash (shouldn't happen but just in case)
    - Same score with different loadouts (keep one with highest overflow)

    Args:
        conn: SQLite connection
        song_name: Name of the song to deduplicate
        table_name: Table to target ("loadouts" or "fg_loadouts")

    Returns:
        int: Number of duplicates removed
    """
    try:
        # Sort criteria depends on table. For fg_loadouts, fg_score is primary.
        # But here we are deduplicating BY SCORE (base score collisions).
        # Actually for fg_loadouts we might want to deduplicate by FG score?
        # For now, stick to standard deduplication logic (Score + Hash) to prevent spam.

        cursor = conn.execute(
            f"""
            SELECT loadout_hash, score, details_json, fg_score
            FROM {table_name}
            WHERE song_name = ?
            ORDER BY score DESC, fg_score DESC
        """,
            (song_name,),
        )

        rows = cursor.fetchall()
        if not rows:
            return 0

        # Group by score
        score_groups = {}
        for row in rows:
            score = row["score"]
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(
                {
                    "loadout_hash": row["loadout_hash"],
                    "score": score,
                    "details_json": row["details_json"],
                    "fg_score": row["fg_score"],
                }
            )

        hashes_to_delete = set()

        for score, group in score_groups.items():
            if len(group) <= 1:
                continue  # No duplicates at this score level

            # Multiple loadouts with same score - keep best one(s) based on overflow and fg_score
            loadouts_with_overflow = []
            for loadout in group:
                details = {}
                if loadout["details_json"]:
                    try:
                        details = json.loads(loadout["details_json"])
                    except json.JSONDecodeError:
                        # Corrupted JSON, skip this loadout's details
                        pass
                overflow = _get_overflow_from_details(details)
                loadouts_with_overflow.append(
                    {
                        **loadout,
                        "overflow": overflow,
                    }
                )

            # Sort by overflow (descending), then fg_score (descending)
            loadouts_with_overflow.sort(key=lambda x: (x["overflow"], x["fg_score"]), reverse=True)

            # Keep the best one, mark rest for deletion
            for loadout in loadouts_with_overflow[1:]:
                hashes_to_delete.add(loadout["loadout_hash"])

        # Delete duplicates
        if hashes_to_delete:
            placeholders = ",".join("?" * len(hashes_to_delete))
            conn.execute(
                f"""
                DELETE FROM {table_name}
                WHERE song_name = ? AND loadout_hash IN ({placeholders})
            """,
                (song_name, *hashes_to_delete),
            )
            return len(hashes_to_delete)

        return 0
    except (sqlite3.Error, json.JSONDecodeError) as e:
        print(f"[DB] Error deduplicating loadouts in {table_name}: {e}")
        return 0


def save_loadout_to_db(song_name, score, fg_score, gear, minis, details, force_data=None):
    """
    Save a single loadout (Legacy wrapper, directs to batch).
    """
    entry = {
        "score": score,
        "fg_score": fg_score,
        "gear": gear,
        "minis": minis,
        "details": details,
        "force": force_data,
    }
    save_loadouts_batch(song_name, [entry])


def save_loadouts_batch(song_name: str, entries: List[PersistenceEntry]) -> None:
    """
    Batch insert/update loadouts for a song in a single transaction.
    Splits data into 'loadouts' (All) and 'fg_loadouts' (Valid FG Only).

    Args:
        song_name: Name of the song
        entries: List of persistence dicts with keys: score, fg_score, gear, minis, details, force
    """
    if not entries:
        return

    timing = str(os.environ.get("DB_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    timing_threshold_ms = 50.0
    try:
        timing_threshold_ms = float(os.environ.get("DB_TIMING_THRESHOLD_MS", str(timing_threshold_ms)))
    except Exception:
        timing_threshold_ms = 50.0

    def _log_timing(label: str, dt_sec: float) -> None:
        if not timing:
            return
        ms = float(dt_sec) * 1000.0
        if ms < timing_threshold_ms:
            return
        print(f"[DB][TIMING] {song_name} {label}={ms:.1f}ms")

    _t0 = time.perf_counter()

    minis_by_name = get_minis_by_name_cached()

    def _effective_hash_for_entry(entry: Dict[str, Any]) -> Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]:
        gear_names_local = _compact_gear_for_db(entry.get("gear", []))
        mini_names_local = _compact_minis_for_db(entry.get("minis", []))
        details_local = entry.get("details", {})
        p_color, s_color, sel_color = extract_song_colors(details_local)
        if not p_color and not s_color:
            return None
        mini_sigs_local = [
            effective_mini_signature_for_name(n, minis_by_name, p_color, s_color, sel_color) for n in mini_names_local
        ]
        return (
            effective_loadout_hash_from_names(gear_names_local, mini_sigs_local),
            mini_sigs_local,
            p_color,
            s_color,
            sel_color,
        )

    # Deduplicate entries before DB insertion (use effective hash when we have song colors).
    _t_dedup0 = time.perf_counter()
    dedup_groups: Dict[tuple[int, str], list[Dict[str, Any]]] = {}
    entry_effective: Dict[int, Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]] = {}

    for idx, entry in enumerate(entries):
        eff = _effective_hash_for_entry(entry)
        entry_effective[idx] = eff
        if eff is None:
            # Legacy key: score + name-hash
            h = _loadout_hash_from_names(
                _compact_gear_for_db(entry.get("gear", [])), _compact_minis_for_db(entry.get("minis", []))
            )
        else:
            h = eff[0]
        key = (int(entry.get("score", 0) or 0), str(h))
        dedup_groups.setdefault(key, []).append(entry)

    deduplicated_entries: list[Dict[str, Any]] = []
    for (_score, _h), group in dedup_groups.items():
        if len(group) == 1:
            deduplicated_entries.append(group[0])
            continue
        try:
            best_entry = max(
                group, key=lambda e: (_get_overflow_from_details(e.get("details", {})), e.get("fg_score", 0))
            )
            deduplicated_entries.append(best_entry)
        except Exception:
            deduplicated_entries.append(group[0])

    _log_timing("dedup_entries", time.perf_counter() - _t_dedup0)

    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)
    best_score_max = None
    best_fg_max = None

    try:
        # Relax sync during batch for throughput
        try:
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass

        # Pre-build parameter lists for executemany (faster than per-entry execute)
        _t_params0 = time.perf_counter()
        loadouts_params = []
        fg_loadouts_params = []

        entry_to_effective: Dict[int, Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]] = {}
        for i, entry in enumerate(deduplicated_entries):
            eff = _effective_hash_for_entry(entry)
            entry_to_effective[i] = eff

        for i, entry in enumerate(deduplicated_entries):
            score = entry.get("score", 0)
            fg_score = entry.get("fg_score", 0)
            gear = entry.get("gear", [])
            minis = entry.get("minis", [])
            details = entry.get("details", {})
            
            # ForceGreats details are persisted as a lean, flat payload in `entry['force']`.
            # Historical DBs may contain older nested formats; we preserve best-effort compatibility
            # by unwrapping `{..., 'details': {...}}` into the details dict.
            force_data = entry.get("force")
            if isinstance(force_data, dict) and ("ForceGreats" not in force_data) and isinstance(force_data.get("details"), dict):
                force_data = force_data.get("details")

            gear_names = _compact_gear_for_db(gear)
            mini_names = _compact_minis_for_db(minis)

            eff = entry_to_effective.get(i)
            if eff is not None:
                (loadout_hash, _mini_sigs, p_color, s_color, sel_color) = eff
                # Deterministically expand mini variant groups from Minis.csv equivalence.
                # This avoids relying on the GA to have explored both names and removes
                # the need for cross-row union/merging.
                groups = canonical_minis_groups_from_names(
                    mini_names,
                    minis_by_name,
                    p_color,
                    s_color,
                    sel_color,
                )
                minis_json = encode_minis_groups(groups)
                # Store representatives in-memory for any downstream name-based utilities.
                mini_names = representative_mini_names(groups)
            else:
                loadout_hash = _loadout_hash_from_names(gear_names, mini_names)
                minis_json = json.dumps([[n] for n in mini_names], separators=(",", ":"))

            gear_json = json.dumps(gear_names, separators=(",", ":"))
            details_json = json.dumps(details, separators=(",", ":")) if details else None
            force_json = json.dumps(force_data, separators=(",", ":")) if force_data else None

            # All entries go to loadouts table
            loadouts_params.append(
                (
                    song_name,
                    loadout_hash,
                    score,
                    fg_score,
                    gear_json,
                    minis_json,
                    details_json,
                    force_json,
                )
            )

            # Only FG-improving entries go to fg_loadouts table (FG leaderboard):
            # We require fg_score strictly better than base score to avoid storing
            # "FG results" that are worse than the base outcome.
            if force_data is not None and fg_score > score:
                fg_loadouts_params.append(
                    (
                        song_name,
                        loadout_hash,
                        score,
                        fg_score,
                        gear_json,
                        minis_json,
                        details_json,
                        force_json,
                    )
                )

            # Track best scores
            if best_score_max is None or score > best_score_max:
                best_score_max = score
            if force_data is not None and fg_score > score and (best_fg_max is None or fg_score > best_fg_max):
                best_fg_max = fg_score
        _log_timing("build_params_json", time.perf_counter() - _t_params0)

        # Batch insert into loadouts table
        if loadouts_params:
            _t_ins0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, loadout_hash) DO UPDATE SET
                    score = CASE WHEN excluded.score > score THEN excluded.score ELSE score END,
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_json = excluded.gear_json,
                    minis_json = excluded.minis_json,
                    -- Update details on ties so attempt counters (and other run metadata) can advance
                    -- without requiring a new best score.
                    details_json = CASE WHEN excluded.score >= score THEN excluded.details_json ELSE details_json END,
                    force_details_json = CASE
                        WHEN excluded.fg_score > fg_score THEN excluded.force_details_json
                        ELSE force_details_json
                    END,
                    timestamp = strftime('%s', 'now')
            """,
                loadouts_params,
            )
            _log_timing("insert_loadouts", time.perf_counter() - _t_ins0)

        # Batch insert into fg_loadouts table
        if fg_loadouts_params:
            _t_insfg0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO fg_loadouts (song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, loadout_hash) DO UPDATE SET
                    score = CASE WHEN excluded.fg_score > fg_score THEN excluded.score ELSE score END,
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_json = excluded.gear_json,
                    minis_json = excluded.minis_json,
                    -- Same reasoning as `loadouts`: allow metadata (e.g., attempt counters) to advance on ties.
                    details_json = CASE WHEN excluded.fg_score >= fg_score THEN excluded.details_json ELSE details_json END,
                    force_details_json = CASE WHEN excluded.fg_score > fg_score THEN excluded.force_details_json ELSE force_details_json END,
                    timestamp = strftime('%s', 'now')
            """,
                fg_loadouts_params,
            )
            _log_timing("insert_fg_loadouts", time.perf_counter() - _t_insfg0)

        # Update Song Stats
        if best_score_max is not None:
            _t_song0 = time.perf_counter()
            conn.execute(
                """
                INSERT INTO songs (name, best_score) VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET best_score = MAX(best_score, excluded.best_score), last_updated = strftime('%s', 'now')
            """,
                (song_name, best_score_max),
            )
            _log_timing("upsert_song_best_score", time.perf_counter() - _t_song0)

        if best_fg_max:
            _t_songfg0 = time.perf_counter()
            conn.execute(
                """
                INSERT INTO songs (name, best_fg_score) VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET best_fg_score = MAX(best_fg_score, excluded.best_fg_score), last_updated = strftime('%s', 'now')
            """,
                (song_name, best_fg_max),
            )
            _log_timing("upsert_song_best_fg_score", time.perf_counter() - _t_songfg0)

        # Enforce FG leaderboard invariant (in case older DB rows exist):
        # fg_loadouts should only contain entries where FG strictly beats base.
        _t_inv0 = time.perf_counter()
        conn.execute(
            """
            DELETE FROM fg_loadouts
            WHERE song_name = ?
            AND fg_score <= score
            """,
            (song_name,),
        )
        _log_timing("delete_fg_invariant", time.perf_counter() - _t_inv0)

        # Deduplicate and Prune BOTH tables
        for table in ["loadouts", "fg_loadouts"]:
            # Deduplicate
            _t_dd0 = time.perf_counter()
            _deduplicate_db_loadouts(conn, song_name, table)
            _log_timing(f"dedup_db_{table}", time.perf_counter() - _t_dd0)

            # Prune (Limit size)
            _t_cnt0 = time.perf_counter()
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE song_name = ?", (song_name,))
            count = cursor.fetchone()[0]
            _log_timing(f"count_{table}", time.perf_counter() - _t_cnt0)
            if count <= LOADOUTS_PER_SONG_LIMIT:
                continue

            if table == "loadouts":
                # Base leaderboard retention: keep top-N by base score only.
                _t_pr0 = time.perf_counter()
                conn.execute(
                    """
                    DELETE FROM loadouts
                    WHERE song_name = ?
                    AND loadout_hash NOT IN (
                        SELECT loadout_hash FROM loadouts
                        WHERE song_name = ?
                        ORDER BY score DESC
                        LIMIT ?
                    )
                    """,
                    (song_name, song_name, LOADOUTS_PER_SONG_LIMIT),
                )
                _log_timing("prune_loadouts", time.perf_counter() - _t_pr0)
            else:
                # For fg_loadouts we prioritize FG_SCORE only.
                _t_prfg0 = time.perf_counter()
                conn.execute(
                    """
                    DELETE FROM fg_loadouts
                    WHERE song_name = ?
                    AND loadout_hash NOT IN (
                        SELECT loadout_hash FROM fg_loadouts
                        WHERE song_name = ?
                        ORDER BY fg_score DESC
                        LIMIT ?
                    )
                    """,
                    (song_name, song_name, LOADOUTS_PER_SONG_LIMIT),
                )
                _log_timing("prune_fg_loadouts", time.perf_counter() - _t_prfg0)

        _t_commit0 = time.perf_counter()
        conn.commit()
        _log_timing("commit", time.perf_counter() - _t_commit0)
    except sqlite3.Error as e:
        print(f"[DB] Error saving batch loadouts: {e}")
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
    finally:
        try:
            conn.execute("PRAGMA synchronous=FULL;")
        except sqlite3.Error:
            pass
        conn.close()
        _log_timing("total", time.perf_counter() - _t0)


def save_team_buff_loadouts_batch(song_name: str, team_buff: str, entries: List[Dict[str, Any]]) -> None:
    """
    Batch insert/update tiered leaderboards for a song in a single transaction.

    Mirrors `save_loadouts_batch`, but partitions by `team_buff` (T1/T5/T10/T15) into:
    - team_buff_loadouts (base leaderboard for that tier)
    - team_buff_fg_loadouts (FG leaderboard for that tier; FG strictly beats base)
    """
    song_name = str(song_name or "").strip()
    team_buff = str(team_buff or "").strip().upper()
    if not song_name or not team_buff or not entries:
        return

    timing = str(os.environ.get("DB_TIMING", "0") or "").strip().lower() in {"1", "true", "yes", "on"}
    timing_threshold_ms = 50.0
    try:
        timing_threshold_ms = float(os.environ.get("DB_TIMING_THRESHOLD_MS", str(timing_threshold_ms)))
    except Exception:
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

    def _effective_hash_for_entry(entry: Dict[str, Any]) -> Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]:
        gear_names_local = _compact_gear_for_db(entry.get("gear", []))
        mini_names_local = _compact_minis_for_db(entry.get("minis", []))
        details_local = entry.get("details", {})
        p_color, s_color, sel_color = extract_song_colors(details_local)
        if not p_color and not s_color:
            return None
        mini_sigs_local = [
            effective_mini_signature_for_name(n, minis_by_name, p_color, s_color, sel_color) for n in mini_names_local
        ]
        return (
            effective_loadout_hash_from_names(gear_names_local, mini_sigs_local),
            mini_sigs_local,
            p_color,
            s_color,
            sel_color,
        )

    # Deduplicate (score + hash) within this batch.
    _t_dedup0 = time.perf_counter()
    dedup_groups: Dict[tuple[int, str], list[Dict[str, Any]]] = {}
    for entry in entries:
        eff = _effective_hash_for_entry(entry)
        if eff is None:
            h = _loadout_hash_from_names(
                _compact_gear_for_db(entry.get("gear", [])), _compact_minis_for_db(entry.get("minis", []))
            )
        else:
            h = eff[0]
        key = (int(entry.get("score", 0) or 0), str(h))
        dedup_groups.setdefault(key, []).append(entry)

    deduplicated_entries: list[Dict[str, Any]] = []
    for (_score, _h), group in dedup_groups.items():
        if len(group) == 1:
            deduplicated_entries.append(group[0])
            continue
        try:
            best_entry = max(
                group, key=lambda e: (_get_overflow_from_details(e.get("details", {})), e.get("fg_score", 0))
            )
            deduplicated_entries.append(best_entry)
        except Exception:
            deduplicated_entries.append(group[0])

    _log_timing("dedup_entries", time.perf_counter() - _t_dedup0)

    db_path = get_evolution_db_path()
    conn = get_db_connection(db_path)

    try:
        try:
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass

        _t_params0 = time.perf_counter()
        loadouts_params = []
        fg_loadouts_params = []

        entry_to_effective: Dict[int, Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]] = {}
        for i, entry in enumerate(deduplicated_entries):
            entry_to_effective[i] = _effective_hash_for_entry(entry)

        for i, entry in enumerate(deduplicated_entries):
            score = int(entry.get("score", 0) or 0)
            fg_score = int(entry.get("fg_score", 0) or 0)
            gear = entry.get("gear", [])
            minis = entry.get("minis", [])
            details = entry.get("details", {})
            force_data = entry.get("force")

            gear_names = _compact_gear_for_db(gear)
            mini_names = _compact_minis_for_db(minis)

            eff = entry_to_effective.get(i)
            if eff is not None:
                (loadout_hash, _mini_sigs, p_color, s_color, sel_color) = eff
                groups = canonical_minis_groups_from_names(
                    mini_names,
                    minis_by_name,
                    p_color,
                    s_color,
                    sel_color,
                )
                minis_json = encode_minis_groups(groups)
                mini_names = representative_mini_names(groups)
            else:
                loadout_hash = _loadout_hash_from_names(gear_names, mini_names)
                minis_json = json.dumps([[n] for n in mini_names], separators=(",", ":"))

            gear_json = json.dumps(gear_names, separators=(",", ":"))
            details_json = json.dumps(details, separators=(",", ":")) if details else None
            force_json = json.dumps(force_data, separators=(",", ":")) if force_data else None

            loadouts_params.append(
                (
                    song_name,
                    team_buff,
                    loadout_hash,
                    score,
                    fg_score,
                    gear_json,
                    minis_json,
                    details_json,
                    force_json,
                )
            )

            if force_data is not None and fg_score > score:
                fg_loadouts_params.append(
                    (
                        song_name,
                        team_buff,
                        loadout_hash,
                        score,
                        fg_score,
                        gear_json,
                        minis_json,
                        details_json,
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
                    gear_json, minis_json, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, team_buff, loadout_hash) DO UPDATE SET
                    score = CASE WHEN excluded.score > score THEN excluded.score ELSE score END,
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_json = excluded.gear_json,
                    minis_json = excluded.minis_json,
                    details_json = CASE WHEN excluded.score >= score THEN excluded.details_json ELSE details_json END,
                    force_details_json = CASE
                        WHEN excluded.fg_score > fg_score THEN excluded.force_details_json
                        ELSE force_details_json
                    END,
                    timestamp = strftime('%s', 'now')
            """,
                loadouts_params,
            )
            _log_timing("insert_team_buff_loadouts", time.perf_counter() - _t_ins0)

        if fg_loadouts_params:
            _t_insfg0 = time.perf_counter()
            conn.executemany(
                """
                INSERT INTO team_buff_fg_loadouts (
                    song_name, team_buff, loadout_hash, score, fg_score,
                    gear_json, minis_json, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
                ON CONFLICT(song_name, team_buff, loadout_hash) DO UPDATE SET
                    score = CASE WHEN excluded.fg_score > fg_score THEN excluded.score ELSE score END,
                    fg_score = MAX(fg_score, excluded.fg_score),
                    gear_json = excluded.gear_json,
                    minis_json = excluded.minis_json,
                    details_json = CASE WHEN excluded.fg_score >= fg_score THEN excluded.details_json ELSE details_json END,
                    force_details_json = CASE
                        WHEN excluded.fg_score > fg_score THEN excluded.force_details_json
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
        _log_timing("delete_team_buff_fg_invariant", time.perf_counter() - _t_inv0)

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

        _t_commit0 = time.perf_counter()
        conn.commit()
        _log_timing("commit", time.perf_counter() - _t_commit0)
    except sqlite3.Error as e:
        print(f"[DB] Error saving TeamBuff batch loadouts: {e}")
        try:
            conn.rollback()
        except sqlite3.Error:
            pass
    finally:
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
) -> List[Dict[str, Any]]:
    """
    Retrieve the top N loadouts for a song to seed the GA.

    Storage format:
    - gear_json: JSON array of name strings
    - minis_json: JSON array of name strings (legacy) OR JSON array of arrays (variant groups)
    If gears_by_name/minis_by_name are provided, expands representative names to full stat dicts.

    Args:
        song_name: Name of the song
        limit: Maximum number of loadouts to retrieve
        gears_by_name: Optional dict mapping gear names to full dicts
        minis_by_name: Optional dict mapping mini names to full dicts

    Returns:
        list: List of loadout dictionaries
    """
    db_path = get_evolution_db_path()
    if not os.path.exists(db_path):
        return []

    song_name = str(song_name or "").strip()

    # PERF: use a cached per-thread connection for read-heavy call sites.
    conn = get_db_connection_cached(db_path)
    try:
        # 1. Fetch Top Base Score Loadouts
        cursor = conn.execute(
            """
            SELECT loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json
            FROM loadouts
            WHERE song_name = ?
            ORDER BY score DESC
            LIMIT ?
        """,
            (song_name, limit),
        )

        results = []
        seen_hashes = set()

        def process_row(row):
            if row["loadout_hash"] in seen_hashes:
                return

            gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
            mini_groups = decode_minis_json(row["minis_json"])
            mini_names = representative_mini_names(mini_groups)
            force_block = json.loads(row["force_details_json"]) if row["force_details_json"] else None

            # Expand names to full dicts if lookup provided
            if gears_by_name:
                gear_data = _expand_gear_from_db(gear_names, gears_by_name)
            else:
                gear_data = gear_names  # Return as names for hash lookups

            if minis_by_name:
                minis_data = _expand_minis_from_db(mini_names, minis_by_name)
            else:
                minis_data = mini_names

            results.append(
                {
                    "score": row["score"],
                    "fg_score": row["fg_score"],
                    "gear": gear_data,
                    "minis": minis_data,
                    "mini_groups": mini_groups,
                    "details": json.loads(row["details_json"]) if row["details_json"] else {},
                    "force": force_block if isinstance(force_block, dict) else None,
                }
            )
            seen_hashes.add(row["loadout_hash"])

        for row in cursor:
            process_row(row)

        # 2. Fetch Top Force Greats Loadouts
        cursor = conn.execute(
            """
            SELECT loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json
            FROM fg_loadouts
            WHERE song_name = ?
            ORDER BY fg_score DESC
            LIMIT ?
        """,
            (song_name, limit),
        )

        for row in cursor:
            process_row(row)

        return results
    except (sqlite3.Error, json.JSONDecodeError) as e:
        print(f"[DB] Error retrieving loadouts: {e}")
        return []
    finally:
        # Thread-local connection is intentionally not closed here.
        pass


def get_song_names_present_in_db(song_names: Iterable[str], db_path: Optional[str] = None) -> set[str]:
    """
    Return the subset of song names that are already present in the DB.

    Presence is defined as having a row in `songs` OR any row in `loadouts`/`fg_loadouts`.
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

        for table in ("loadouts", "fg_loadouts"):
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
    rerunning GA (e.g. when FG is deferred/interleaved for throughput).
    """
    song_name = str(song_name or "").strip()
    if not song_name:
        return
    if not candidates:
        delete_pending_fg_job(song_name)
        return

    payload = json.dumps(candidates, separators=(",", ":"))
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
            except Exception:
                continue

            try:
                candidates = json.loads(cand_json) if cand_json else []
            except Exception:
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
