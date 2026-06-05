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
import warnings
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.parse import quote
import logging
from ..core.constants import LOADOUTS_PER_SONG_LIMIT, PATHS
from ..core.fallback_monitor import warn_fallback
from ..core.gem_defs import fg_score_from_force
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
from .database_codecs import (
    _json_dumps_compact,
    _json_loads,
    _pack_id_groups,
    _pack_id_list,
    _pack_stats_for_storage,
    _strip_computed_details_fields,
    _unpack_id_groups,
    _unpack_id_list,
    _unpack_stats_after_load,
)
from .piece_encoding_store import (
    _GEAR_NAME_ENCODING_TABLE,
    _MINI_NAME_ENCODING_TABLE,
    _initialize_piece_name_encodings,
    _insert_missing_piece_names,
    _load_piece_name_encoding_maps,
)
from .loadout_equivalence import (
    effective_loadout_hash_from_names,
    effective_mini_signature_for_name,
    extract_song_colors,
    get_gears_by_name_cached,
    get_minis_by_name_cached,
    canonical_minis_groups_from_names,
    representative_mini_names,
    rotate_mini_groups_for_slot_display,
)
from gear_optimizer.core.parsing import env_get
logger = logging.getLogger(__name__)
def get_evolution_db_path() -> str:
    """
    Return the configured evolution DB location (env override supported).
    Returns:
        str: Path to evolution database file
    """
    env_path = str(os.getenv("EVOLUTION_DB_PATH", "") or "").strip()
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
def get_db_connection_cached(db_path: Optional[str] = None, *, allow_fallback: bool = True) -> sqlite3.Connection:
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
    try:
        read_timeout = float(env_get("DB_READ_TIMEOUT_SEC", "0.2") or "0.2")
    except Exception as e:
        logger.warning(f"database:get_db_connection_cached: {e}")
        read_timeout = 0.2
    conn = get_db_connection_readonly(db_path, timeout=read_timeout)
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
            logger.warning(f"database:get_song_counters: {e}")
            attempt_lifetime = 0
        try:
            attempts_first = int(row["attempts_first"] or 0)
        except Exception as e:
            logger.warning(f"database:get_song_counters: {e}")
            attempts_first = 0
        try:
            best_score = int(row["best_score"] or 0)
        except Exception as e:
            logger.warning(f"database:get_song_counters: {e}")
            best_score = 0
        try:
            best_fg_score = int(row["best_fg_score"] or 0)
        except Exception as e:
            logger.warning(f"database:get_song_counters: {e}")
            best_fg_score = 0
        return (attempt_lifetime, attempts_first, best_score, best_fg_score)
    except sqlite3.Error:
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
        return
    finally:
        if close_conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"database:update_song_counters: {e}")
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
    if not isinstance(details, dict):
        details = {}
    stats_obj = details.get("Stats")
    if isinstance(stats_obj, dict) and stats_obj:
        return details
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
        logger.warning(f"database:_ensure_stats_in_details: {e}")
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
            logger.warning(f"database:_compact_force_details_for_storage: {e}")
    return out
def _coerce_db_int(v: Any) -> int:
    try:
        return int(v or 0)
    except Exception as e:
        logger.warning(f"database:_coerce_db_int: {e}")
        return 0
def _normalize_force_for_persistence(force_data: Any, *, fg_score: int) -> Any:
    if not isinstance(force_data, dict):
        return force_data
    out = dict(force_data)
    score_v = _coerce_db_int(fg_score)
    if score_v <= 0:
        score_v = _coerce_db_int(out.get("Score", 0))
    if score_v <= 0:
        score_v = _coerce_db_int(out.get("score", 0))
    if score_v > 0:
        out["score"] = int(score_v)
        out["Score"] = int(score_v)
    det = out.get("details")
    if isinstance(det, dict):
        fg = det.get("ForceGreats")
        if isinstance(fg, dict) and int(fg_score or 0) > 0:
            fg_out = dict(fg)
            fg_out["final_score"] = int(fg_score)
            det_out = dict(det)
            det_out["ForceGreats"] = fg_out
            out["details"] = det_out
    fg = out.get("ForceGreats")
    if isinstance(fg, dict) and int(score_v or 0) > 0:
        fg_out = dict(fg)
        fg_out["final_score"] = int(score_v)
        out["ForceGreats"] = fg_out
    return out
def _normalize_force_base_score_for_persistence(force_data: Any, *, fg_base_score: int) -> Any:
    if not isinstance(force_data, dict):
        return force_data
    base_i = _coerce_db_int(fg_base_score)
    if base_i <= 0:
        return force_data
    out = dict(force_data)
    out["BaseScore"] = int(base_i)
    det = out.get("details")
    if isinstance(det, dict):
        det_out = dict(det)
        det_out["BaseScore"] = int(base_i)
        out["details"] = det_out
    return out
def _assert_force_score_pairing(force_data: Any, *, fg_base_score: int, fg_score: int) -> None:
    if not isinstance(force_data, dict) or int(fg_score or 0) <= 0:
        return
    force_base = _force_payload_base_score(force_data)
    if int(force_base or 0) != int(fg_base_score or 0):
        raise AssertionError(
            "FG persistence payload BaseScore must match the paired FG base score "
            f"(force={force_base}, row={fg_base_score})."
        )
    force_score = _coerce_db_int(force_data.get("Score", force_data.get("score", 0)))
    if int(force_score or 0) != int(fg_score or 0):
        raise AssertionError(
            "FG persistence payload Score must match the row FG score "
            f"(force={force_score}, row={fg_score})."
        )
    fg_meta = force_data.get("ForceGreats")
    if isinstance(fg_meta, dict) and "final_score" in fg_meta:
        meta_score = _coerce_db_int(fg_meta.get("final_score"))
        if int(meta_score or 0) != int(fg_score or 0):
            raise AssertionError(
                "FG persistence ForceGreats.final_score must match the row FG score "
                f"(force={meta_score}, row={fg_score})."
            )
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
    best_score_max = None
    best_fg_max = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        score = _coerce_db_int(entry.get("score", 0))
        fg_score = _coerce_db_int(entry.get("fg_score", 0))
        fg_base_score = score
        try:
            raw_fg_base = entry.get("fg_base_score")
        except Exception as e:
            logger.warning(f"database:_coerce_db_int: {e}")
            raw_fg_base = None
        if raw_fg_base is not None:
            fg_base_score = _coerce_db_int(raw_fg_base)
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
        logger.warning(f"database:save_team_buff_loadouts_batch: {e}")
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
                    logger.warning(f"database:_extract_entry_colors: {e}")
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
    entry_names_cache: Dict[int, tuple[list[str], list[str]]] = {}
    def _compact_entry_names(entry: Mapping[str, Any]) -> tuple[list[str], list[str]]:
        entry_id = int(id(entry))
        cached = entry_names_cache.get(entry_id)
        if cached is not None:
            return cached
        out = (_compact_gear_for_db(entry.get("gear", [])), _compact_minis_for_db(entry.get("minis", [])))
        entry_names_cache[entry_id] = out
        return out
    def _effective_hash_for_entry(
        entry: Mapping[str, Any],
    ) -> Optional[tuple[str, list[tuple[Any, ...]], str, str, str]]:
        gear_names_local, mini_names_local = _compact_entry_names(entry)
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
            gear_names_local, mini_names_local = _compact_entry_names(entry)
            h = _loadout_hash_from_names(gear_names_local, mini_names_local)
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
            logger.warning(f"database:_effective_hash_for_entry: {e}")
            deduplicated_entries.append(group[0])
    _log_timing("dedup_entries", time.perf_counter() - _t_dedup0)
    def _can_recompute_stats_for_persistence(gear_names_local: list[str], mini_names_local: list[str]) -> bool:
        gear_ok = (not gear_names_local) or (
            isinstance(gears_by_name, dict)
            and bool(gears_by_name)
            and all((not n or n in gears_by_name) for n in gear_names_local)
        )
        mini_ok = (not mini_names_local) or (
            isinstance(minis_by_name, dict)
            and bool(minis_by_name)
            and all((not n or n in minis_by_name) for n in mini_names_local)
        )
        return bool(gear_ok and mini_ok)
    def _details_with_representative_stats(
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
            logger.warning(f"database:_recompute_stats_in_details_for_persistence: {e}")
            return details_obj
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
    def _canonical_persistence_minis(
        gear_names_local: list[str],
        mini_names_local: list[str],
        eff: Optional[tuple[str, list[tuple[Any, ...]], str, str, str]],
    ) -> tuple[str, list[list[str]], list[str]]:
        if eff is None:
            warn_fallback(
                "db.minis_groups.singletons",
                "effective mini grouping unavailable; persisting singleton mini groups",
                context={"song_name": song_name, "team_buff": team_buff},
                fatal=False,
            )
            return _loadout_hash_from_names(gear_names_local, mini_names_local), [[n] for n in mini_names_local], [
                *mini_names_local
            ]
        loadout_hash, mini_sigs, p_color, s_color, sel_color = eff
        groups = canonical_minis_groups_from_names(
            mini_names_local,
            minis_by_name,
            p_color,
            s_color,
            sel_color,
            mini_sigs=mini_sigs,
        )
        groups = rotate_mini_groups_for_slot_display(groups)
        return loadout_hash, groups, [g[0] for g in groups if g]
    def _canonicalize_persistence_details(
        details_obj: Any,
        *,
        gear_names_local: list[str],
        representative_mini_names_local: list[str],
        original_gear: Any,
        original_minis: Any,
        eff: Optional[tuple[str, list[tuple[Any, ...]], str, str, str]],
    ) -> dict:
        details_unpacked = _unpack_stats_after_load(details_obj) if isinstance(details_obj, dict) else details_obj
        if not isinstance(details_unpacked, dict):
            details_unpacked = {}
        team_color_for_stats = str(
            details_unpacked.get("PrimaryColor") or details_unpacked.get("Primary Color") or ""
        ).strip()
        if (eff is not None) and _can_recompute_stats_for_persistence(
            gear_names_local, representative_mini_names_local
        ):
            return _details_with_representative_stats(
                details_unpacked,
                gear_names_local=gear_names_local,
                mini_names_local=representative_mini_names_local,
                team_color=team_color_for_stats,
            )
        current_stats = details_unpacked.get("Stats")
        if isinstance(current_stats, dict) and current_stats:
            return details_unpacked
        return _ensure_stats_in_details(
            details_unpacked,
            original_gear,
            original_minis,
            minis_by_name,
            team_buff=team_buff,
            team_color=team_color_for_stats,
        )
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
            logger.warning(f"database:_recompute_stats_in_details_for_persistence: {e}")
        _t_params0 = time.perf_counter()
        loadouts_params = []
        deferred_fg_loadouts_params = []
        fg_loadouts_params = []
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
        for entry in deduplicated_entries:
            score = _coerce_db_int(entry.get("score", 0))
            fg_score = _coerce_db_int(entry.get("fg_score", 0))
            fg_base_score = score
            has_explicit_fg_base = False
            try:
                raw_fg_base = entry.get("fg_base_score")
            except Exception as e:
                logger.warning(f"database:_encode_mini_groups_to_blob: {e}")
                raw_fg_base = None
            if raw_fg_base is not None:
                has_explicit_fg_base = True
                fg_base_score = _coerce_db_int(raw_fg_base)
                if fg_base_score <= 0:
                    fg_base_score = score
            gear = entry.get("gear", [])
            minis = entry.get("minis", [])
            details = entry.get("details", {})
            force_data = entry.get("force")
            entry_id = int(id(entry))
            eff = effective_cache_by_entry_id.get(entry_id)
            if entry_id not in effective_cache_by_entry_id:
                eff = _effective_hash_for_entry(entry)
                effective_cache_by_entry_id[entry_id] = eff
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
            if has_explicit_fg_base and fg_base_score > 0:
                force_data = _normalize_force_base_score_for_persistence(force_data, fg_base_score=fg_base_score)
            elif force_base_score > 0:
                fg_base_score = force_base_score
            elif fg_base_score > 0:
                force_data = _normalize_force_base_score_for_persistence(force_data, fg_base_score=fg_base_score)
            if force_data is not None and fg_score > fg_base_score:
                _assert_force_score_pairing(force_data, fg_base_score=fg_base_score, fg_score=fg_score)
            details = _normalize_details_for_persistence(
                details,
                score=score,
                fg_score=fg_score,
                force_data=force_data,
                preserve_attempt_meta=bool(preserve_attempt_meta),
            )
            gear_names, mini_names = _compact_entry_names(entry)
            loadout_hash, groups, mini_names = _canonical_persistence_minis(gear_names, mini_names, eff)
            details = _canonicalize_persistence_details(
                details,
                gear_names_local=gear_names,
                representative_mini_names_local=mini_names,
                original_gear=gear,
                original_minis=minis,
                eff=eff,
            )
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
                    gear_ids_blob = CASE WHEN excluded.score > score THEN excluded.gear_ids_blob ELSE gear_ids_blob END,
                    minis_ids_blob = CASE WHEN excluded.score > score THEN excluded.minis_ids_blob ELSE minis_ids_blob END,
                    details_json = CASE WHEN excluded.score > score THEN excluded.details_json ELSE details_json END,
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
                        WHEN excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL THEN excluded.score
                        ELSE score
                    END,
                    gear_ids_blob = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL)
                            THEN excluded.gear_ids_blob
                        ELSE gear_ids_blob
                    END,
                    minis_ids_blob = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL)
                            THEN excluded.minis_ids_blob
                        ELSE minis_ids_blob
                    END,
                    details_json = CASE
                        WHEN excluded.fg_score > fg_score OR (excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL)
                            THEN excluded.details_json
                        ELSE details_json
                    END,
                    force_details_json = CASE
                        WHEN excluded.fg_score > fg_score THEN excluded.force_details_json
                        WHEN excluded.fg_score = fg_score AND excluded.force_details_json IS NOT NULL
                            THEN excluded.force_details_json
                        ELSE force_details_json
                    END,
                    timestamp = strftime('%s', 'now')
                """,
                fg_loadouts_params,
            )
            _log_timing("insert_team_buff_fg_loadouts", time.perf_counter() - _t_insfg0)
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
                    logger.warning(f"database:_verify_table_row: {e}")
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
                logger.warning(f"database:_materialize_common: {e}")
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
                logger.warning(f"database:_materialize_common: {e}")
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
            details = _strip_computed_details_fields(details)
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
                    logger.warning(f"database:_materialize_common: {e}")
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
            if gears_by_name:
                gear_data = _expand_gear_from_db(gear_names, gears_by_name)
            else:
                gear_data = gear_names  # Return as names for hash lookups
            if minis_by_name:
                minis_data = _expand_minis_from_db(mini_names, minis_by_name)
            else:
                minis_data = mini_names
            return gear_data, minis_data
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
            try:
                existing_fg = int(entry.get("fg_score", 0) or 0)
            except Exception as e:
                logger.warning(f"database:_expand_items: {e}")
                existing_fg = 0
            try:
                fg_i = int(fg_score or 0)
            except Exception as e:
                logger.warning(f"database:_expand_items: {e}")
                fg_i = 0
            if fg_i > existing_fg:
                entry["fg_score"] = fg_score
                entry["force"] = force_obj
                entry["fg_base_score"] = fg_base_score
            elif fg_i == existing_fg:
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
        pass
from . import pending_fg_jobs as _pending_fg_jobs
get_song_names_present_in_db = _pending_fg_jobs.get_song_names_present_in_db
upsert_pending_fg_job = _pending_fg_jobs.upsert_pending_fg_job
delete_pending_fg_job = _pending_fg_jobs.delete_pending_fg_job
list_pending_fg_jobs = _pending_fg_jobs.list_pending_fg_jobs
