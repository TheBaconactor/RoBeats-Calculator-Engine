"""
Song Helpers - Database Context - Database seeds and known loadouts loading.

This module provides database operations:
- load_database_context: Load database seeds and known loadouts
"""

import json
import logging
import os
import threading
import time

from ...data.database import (
    get_db_connection,
    get_best_loadouts,
    get_evolution_db_path,
    LOADOUTS_PER_SONG_LIMIT,
)
from ...data.models import WarnOnce

# Global warn-once instance
WARN_ONCE = WarnOnce()

_WAL_MAINT_LOCK = threading.Lock()
_LAST_WAL_MAINT_TS = 0.0


def build_db_key(found_song_name: str, calc_song: dict | None = None) -> str:
    """
    Build a DB lookup key that includes scoring-relevant context when needed.

    Today the big source of "regression-looking" behavior is HumanHitSim:
    if the HumanHitSim seed/mode changes between runs but the DB key stays the
    same, we mix incompatible score contexts (bad seeding + misleading records).
    """
    if not isinstance(found_song_name, str) or not found_song_name:
        found_song_name = str(found_song_name)

    if not isinstance(calc_song, dict):
        return found_song_name
    meta = calc_song.get("metadata", {}) or {}

    if not meta.get("HumanHitSimApplied"):
        return found_song_name

    seed = meta.get("HumanHitSimSeed")
    apply_to = meta.get("HumanHitSimApplyTo")
    dist = meta.get("HumanHitSimDistribution")
    great_mode = meta.get("HumanHitSimGreatMode")
    if seed is None and apply_to is None and dist is None and great_mode is None:
        return found_song_name

    try:
        seed_s = "?" if seed is None else str(int(seed))
    except Exception:
        seed_s = "?"
    apply_s = str(apply_to or "?").strip()
    dist_s = str(dist or "?").strip()
    gm_s = str(great_mode or "?").strip()
    return f"{found_song_name} | HumanHitSim(apply={apply_s},dist={dist_s},mode={gm_s},seed={seed_s})"


def _maybe_wal_maintenance(conn) -> None:
    """
    Opportunistic WAL maintenance for long-running sessions.

    This MUST NOT run on every per-song DB read: TRUNCATE checkpoints can take locks
    and stall concurrent writers, which can indirectly starve the GPU pipeline.
    """
    try:
        interval_sec = float(os.environ.get("DB_WAL_MAINT_INTERVAL_SEC", "30") or "30")
    except Exception:
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
    except Exception:
        logging.debug("[DB] WAL checkpoint(PASSIVE) failed", exc_info=True)

    try:
        conn.execute("PRAGMA optimize")
    except Exception:
        logging.debug("[DB] PRAGMA optimize failed", exc_info=True)


def load_database_context(found_song_name, use_evo_db, gears_by_name, minis_by_name):
    """
    Load database seeds and known loadouts.

    Args:
        found_song_name: Name of the song
        use_evo_db: Whether to use evolution database
        gears_by_name: Dictionary of gears by name
        minis_by_name: Dictionary of minis by name

    Returns:
        tuple: (prev_record, known_loadouts)
    """
    prev_record = None
    known_loadouts = {}

    if use_evo_db:
        # Always print DB path + exact lookup key to make seeding issues obvious.
        # (repr shows hidden whitespace / mismatched suffixes that would otherwise be invisible.)
        try:
            print(f"[DB] Using DB: {get_evolution_db_path()} | lookup key: {found_song_name!r}")
        except Exception:
            print(f"[DB] Using DB: (unknown) | lookup key: {found_song_name!r}")

        # Load previous best for seeding
        best_loadouts = get_best_loadouts(
            found_song_name, limit=1, gears_by_name=gears_by_name, minis_by_name=minis_by_name
        )
        if best_loadouts:
            prev_record = best_loadouts[0]

        if prev_record:
            print(f"[DB] Found previous best: {prev_record.get('score', 0)}")
        else:
            # If we expected a DB seed but didn't find one, show nearby candidates.
            # This catches cases where the song key differs by suffix/spacing.
            try:
                conn = get_db_connection()
                rows = conn.execute(
                    "SELECT DISTINCT song_name FROM loadouts WHERE song_name LIKE ? LIMIT 8",
                    (f"%{found_song_name.split('(')[0].strip()}%",),
                ).fetchall()
                conn.close()
                if rows:
                    print("[DB] No exact seed found. Similar keys in DB:")
                    for r in rows:
                        # sqlite3.Row supports index access in this connection setup
                        print(f"  - {str(r[0])!r}")
            except Exception:
                pass

        # Fetch known loadouts for persistent caching
        try:
            conn = get_db_connection()
            cursor = conn.execute(
                """SELECT loadout_hash, score, fg_score, force_details_json, details_json
                   FROM loadouts
                   WHERE song_name = ?
                   ORDER BY score DESC
                   LIMIT ?""",
                (found_song_name, LOADOUTS_PER_SONG_LIMIT),
            )
            for row in cursor:
                force_blob = row["force_details_json"]
                force_data = None
                if force_blob:
                    try:
                        force_data = json.loads(force_blob)
                    except Exception as exc:
                        WARN_ONCE.warn(
                            "force-loadout-json",
                            f"Invalid force JSON for {row.get('loadout_hash')}: {exc}",
                        )
                        force_data = None

                details_blob = row["details_json"]
                details_data = None
                if details_blob:
                    try:
                        details_data = json.loads(details_blob)
                    except Exception as exc:
                        WARN_ONCE.warn(
                            "details-loadout-json",
                            f"Invalid details JSON for {row.get('loadout_hash')}: {exc}",
                        )
                        details_data = None

                known_loadouts[row["loadout_hash"]] = (
                    row["score"],
                    row["fg_score"],
                    force_data,
                    details_data,
                )

            _maybe_wal_maintenance(conn)
            conn.close()
        except Exception as e:
            print(f"[DB] Error fetching known loadouts: {e}")

    return prev_record, known_loadouts
