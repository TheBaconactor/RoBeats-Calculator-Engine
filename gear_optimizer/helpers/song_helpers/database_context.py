"""Song Helpers - Database Context - Progress baseline loading."""

import logging
import os
import sqlite3
import threading
import time
from typing import Any, Mapping

from ...core.env_config import env_flag
from ...data.database import (
    get_db_connection_cached,
    get_best_loadouts,
    get_evolution_db_path,
    get_song_counters,
)
from ...data.models import WarnOnce

# Global warn-once instance
from gear_optimizer.core.parsing import env_get

logger = logging.getLogger(__name__)
WARN_ONCE = WarnOnce()

_WAL_MAINT_LOCK = threading.Lock()
_LAST_WAL_MAINT_TS = 0.0


def _db_context_verbose() -> bool:
    return env_flag("DB_CONTEXT_VERBOSE", "0")


def build_db_key(found_song_name: str, calc_song: dict | None = None) -> str:
    """
    Build a stable DB lookup key for a song.

    Timing-envelope analysis does not affect the DB namespace; all scores accumulate
    under the same song key.
    """
    # Keep signature for call sites that pass calc_song.
    _ = calc_song
    return str(found_song_name or "").strip()


def resolve_database_baseline_team_buff(
    cfg: Any | None = None,
    *,
    cfg_dict: Mapping[str, Any] | None = None,
    default: str = "T5",
) -> str:
    """
    Resolve the TeamBuff tier used for progress/context reads.

    Native optimizer DB context reads the persisted baseline slice. Runtime auto
    mode stores baseline rows under T5, so this path stays pinned to T5 even when
    display-only DB best views use the selected config tier.
    """
    default_tier = str(default or "T5")
    try:
        return default_tier
    except Exception as e:
        logger.debug(f"database_context:resolve_database_baseline_team_buff: {e}")
        return default_tier


def _maybe_wal_maintenance(conn) -> None:
    """
    Opportunistic WAL maintenance for long-running sessions.

    This MUST NOT run on every per-song DB read: TRUNCATE checkpoints can take locks
    and stall concurrent writers, which can indirectly starve the GPU pipeline.
    """
    try:
        interval_sec = float(env_get("DB_WAL_MAINT_INTERVAL_SEC", "30") or "30")
    except Exception as e:
        logger.debug(f"database_context:_maybe_wal_maintenance: {e}")
        interval_sec = 30.0

    if interval_sec <= 0:
        return

    global _LAST_WAL_MAINT_TS
    now = time.monotonic()
    with _WAL_MAINT_LOCK:
        if (now - _LAST_WAL_MAINT_TS) < interval_sec:
            return
        _LAST_WAL_MAINT_TS = now

    try:
        # PASSIVE is non-blocking; it won't force truncation, but it helps keep WAL
        # growth in check without taking disruptive locks.
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
    except Exception as e:
        logger.debug(f"database_context:_maybe_wal_maintenance: {e}")
        logging.debug("[DB] WAL checkpoint(PASSIVE) failed", exc_info=True)

    optimize_enabled = env_flag("DB_OPTIMIZE", "0")
    if not optimize_enabled:
        return

    try:
        conn.execute("PRAGMA optimize")
    except Exception as e:
        logger.debug(f"database_context:_maybe_wal_maintenance: {e}")
        logging.debug("[DB] PRAGMA optimize failed", exc_info=True)


def load_database_context(
    found_song_name,
    gears_by_name,
    minis_by_name,
    *,
    allow_fallback: bool = True,
    team_buff: str = "T5",
):
    """
    Load the previous best DB record used for progress and result display.

    Args:
        found_song_name: Name of the song
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name

    Returns:
        previous record or None
    """
    prev_record = None

    pid = None
    try:
        pid = os.getpid()
    except Exception as e:
        logger.debug(f"database_context:load_database_context: {e}")
        pid = None

    if _db_context_verbose():
        # Always print DB path + exact lookup key to make seeding issues obvious.
        # (repr shows hidden whitespace / mismatched suffixes that would otherwise be invisible.)
        try:
            if pid is not None:
                print(f"[DB pid={pid}] Using DB: {get_evolution_db_path()} | lookup key: {found_song_name!r}")
            else:
                print(f"[DB] Using DB: {get_evolution_db_path()} | lookup key: {found_song_name!r}")
        except Exception as e:
            logger.debug(f"database_context:load_database_context: {e}")
            if pid is not None:
                print(f"[DB pid={pid}] Using DB: (unknown) | lookup key: {found_song_name!r}")
            else:
                print(f"[DB] Using DB: (unknown) | lookup key: {found_song_name!r}")

    best_loadouts = get_best_loadouts(
        found_song_name,
        limit=1,
        gears_by_name=gears_by_name,
        minis_by_name=minis_by_name,
        team_buff=str(team_buff or "T5"),
        allow_fallback=allow_fallback,
    )
    if best_loadouts:
        prev_record = best_loadouts[0]

    if prev_record:
        try:
            prev_base = int(prev_record.get("score", 0) or 0)
        except Exception as e:
            logger.debug(f"database_context:load_database_context: {e}")
            prev_base = 0
        prev_best_fg = 0
        try:
            prev_best_fg = max(int(r.get("fg_score", 0) or 0) for r in (best_loadouts or []) if isinstance(r, dict))
        except Exception as e:
            logger.debug(f"database_context:load_database_context: {e}")
            prev_best_fg = 0

        if _db_context_verbose():
            tag = f"[DB pid={pid}]" if pid is not None else "[DB]"
            print(f"{tag} Found previous best (Base: {prev_base}, FG: {prev_best_fg})")
    try:
        conn = get_db_connection_cached(allow_fallback=allow_fallback)
        _maybe_wal_maintenance(conn)
    except Exception as e:
        logger.debug(f"database_context:load_database_context: {e}")

    return prev_record


def load_database_progress_baseline(
    found_song_name,
    gears_by_name,
    minis_by_name,
    *,
    allow_fallback: bool = True,
    team_buff: str = "T5",
):
    """
    Load the canonical progress baseline.

    Returns:
        tuple:
            (
                prev_record,
                db_best_score,
                db_best_fg_score,
                attempt_lifetime,
                prev_attempts_first,
                baseline_valid,
            )
    """
    prev_record = None
    db_best_score = 0
    db_best_fg_score = 0
    attempt_lifetime_prev = 0
    prev_attempts_first = 0
    baseline_valid = False

    def _invalid_baseline_result():
        if isinstance(prev_record, tuple) and len(prev_record) == 2:
            return prev_record[0], prev_record[1], 0, 0, 0, 0, False
        return None, {}, 0, 0, 0, 0, False

    try:
        prev_record = load_database_context(
            found_song_name,
            gears_by_name,
            minis_by_name,
            allow_fallback=allow_fallback,
            team_buff=str(team_buff or "T5"),
        )
    except sqlite3.Error:
        if not allow_fallback:
            return _invalid_baseline_result()
        raise

    try:
        (
            attempt_lifetime_prev,
            prev_attempts_first,
            db_best_score,
            db_best_fg_score,
        ) = get_song_counters(str(found_song_name or "").strip(), allow_fallback=allow_fallback)
        baseline_valid = True
        if not db_best_fg_score:
            conn = get_db_connection_cached(allow_fallback=allow_fallback)
            row = conn.execute(
                """
                SELECT MAX(fg_score)
                FROM team_buff_fg_loadouts
                WHERE song_name = ? AND team_buff = ?
                """,
                (str(found_song_name or "").strip(), str(team_buff or "T5")),
            ).fetchone()
            if row is not None:
                try:
                    db_best_fg_score = int(row[0] or 0)
                except Exception as e:
                    logger.debug(f"database_context:load_database_progress_baseline: {e}")
                    db_best_fg_score = 0
    except sqlite3.Error:
        if not allow_fallback:
            return _invalid_baseline_result()
        baseline_valid = True

    if not db_best_score and isinstance(prev_record, dict):
        try:
            db_best_score = int(prev_record.get("score", 0) or 0)
        except Exception as e:
            logger.debug(f"database_context:load_database_progress_baseline: {e}")
            db_best_score = 0

    if not db_best_fg_score and isinstance(prev_record, dict):
        try:
            db_best_fg_score = int(prev_record.get("fg_score", 0) or 0)
        except Exception as e:
            logger.debug(f"database_context:load_database_progress_baseline: {e}")
            db_best_fg_score = 0

    if isinstance(prev_record, dict) and "details" in prev_record:
        try:
            if int(attempt_lifetime_prev or 0) <= 0:
                attempt_lifetime_prev = int(prev_record["details"].get("attempt_lifetime", 0) or 0)
        except Exception as e:
            logger.debug(f"database_context:load_database_progress_baseline: {e}")
            attempt_lifetime_prev = int(attempt_lifetime_prev or 0)
        try:
            if int(prev_attempts_first or 0) <= 0:
                prev_attempts_first = int(prev_record["details"].get("attempts_first", 0) or 0)
        except Exception as e:
            logger.debug(f"database_context:load_database_progress_baseline: {e}")
            prev_attempts_first = int(prev_attempts_first or 0)

    attempt_lifetime = int(attempt_lifetime_prev) + 1
    return (
        prev_record,
        int(db_best_score or 0),
        int(db_best_fg_score or 0),
        int(attempt_lifetime or 0),
        int(prev_attempts_first or 0),
        bool(baseline_valid),
    )
