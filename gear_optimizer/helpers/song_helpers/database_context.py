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

from ...core.env_config import env_flag
from ...data.database import (
    get_db_connection,
    get_db_connection_cached,
    get_best_loadouts,
    get_evolution_db_path,
    LOADOUTS_PER_SONG_LIMIT,
)
from ...data.models import WarnOnce

# Global warn-once instance
WARN_ONCE = WarnOnce()

_WAL_MAINT_LOCK = threading.Lock()
_LAST_WAL_MAINT_TS = 0.0


class _LazyJsonDict(dict):
    """
    Lazy JSON decoder that still satisfies isinstance(x, dict).

    Used to avoid eager json.loads() for every known_loadouts row when most code paths
    only care about (score, fg_score) and never touch details/force payloads.
    """

    __slots__ = ("_blob", "_loaded", "_warn_key", "_warn_msg")

    def __init__(self, blob: str, *, warn_key: str, warn_msg: str):
        super().__init__()
        self._blob = str(blob or "")
        self._loaded = False
        self._warn_key = str(warn_key or "lazy-json")
        self._warn_msg = str(warn_msg or "Invalid JSON")

    def _ensure(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            data = json.loads(self._blob) if self._blob else None
            if isinstance(data, dict):
                self.update(data)
        except Exception as exc:
            try:
                WARN_ONCE.warn(self._warn_key, f"{self._warn_msg}: {exc}")
            except Exception:
                pass

    def __getitem__(self, key):
        self._ensure()
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._ensure()
        return super().get(key, default)

    def items(self):
        self._ensure()
        return super().items()

    def keys(self):
        self._ensure()
        return super().keys()

    def values(self):
        self._ensure()
        return super().values()

    def __iter__(self):
        self._ensure()
        return super().__iter__()

    def __len__(self):
        self._ensure()
        return super().__len__()

    def __contains__(self, item):
        self._ensure()
        return super().__contains__(item)


def build_db_key(found_song_name: str, calc_song: dict | None = None) -> str:
    """
    Build a stable DB lookup key for a song.

    HumanHitSim parameters MUST NOT affect the DB namespace: HitSim is intended to
    explore/visualize timelines while accumulating scores under the same song key.
    """
    # Keep signature for call sites that pass calc_song, but ignore HitSim context by design.
    _ = calc_song
    return str(found_song_name or "").strip()


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

    optimize_enabled = env_flag("DB_OPTIMIZE", "0")
    if not optimize_enabled:
        return

    try:
        conn.execute("PRAGMA optimize")
    except Exception:
        logging.debug("[DB] PRAGMA optimize failed", exc_info=True)


def load_database_context(
    found_song_name, use_evo_db, gears_by_name, minis_by_name, *, load_known_loadouts: bool = True
):
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
        pid = None
        try:
            pid = os.getpid()
        except Exception:
            pid = None

        # Always print DB path + exact lookup key to make seeding issues obvious.
        # (repr shows hidden whitespace / mismatched suffixes that would otherwise be invisible.)
        try:
            if pid is not None:
                print(f"[DB pid={pid}] Using DB: {get_evolution_db_path()} | lookup key: {found_song_name!r}")
            else:
                print(f"[DB] Using DB: {get_evolution_db_path()} | lookup key: {found_song_name!r}")
        except Exception:
            if pid is not None:
                print(f"[DB pid={pid}] Using DB: (unknown) | lookup key: {found_song_name!r}")
            else:
                print(f"[DB] Using DB: (unknown) | lookup key: {found_song_name!r}")

        # Load previous best for seeding
        best_loadouts = get_best_loadouts(
            found_song_name, limit=1, gears_by_name=gears_by_name, minis_by_name=minis_by_name
        )
        if best_loadouts:
            prev_record = best_loadouts[0]

        if prev_record:
            try:
                prev_base = int(prev_record.get("score", 0) or 0)
            except Exception:
                prev_base = 0
            # `get_best_loadouts(..., limit=1)` may include both:
            # - top base loadout from `loadouts`
            # - top FG loadout from `fg_loadouts`
            # so we can cheaply surface an approximate best-FG alongside base.
            prev_best_fg = 0
            try:
                prev_best_fg = max(int(r.get("fg_score", 0) or 0) for r in (best_loadouts or []) if isinstance(r, dict))
            except Exception:
                prev_best_fg = 0

            tag = f"[DB pid={pid}]" if pid is not None else "[DB]"
            print(f"{tag} Found previous best (Base: {prev_base}, FG: {prev_best_fg})")
        else:
            # If we expected a DB seed but didn't find one, show nearby candidates.
            # This catches cases where the song key differs by suffix/spacing.
            suggest_enabled = env_flag("DB_SEED_SUGGEST", "0")
            if suggest_enabled:
                try:
                    conn = get_db_connection_cached()
                    def _table_exists(name: str) -> bool:
                        try:
                            return conn.execute(
                                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                                (name,),
                            ).fetchone() is not None
                        except Exception:
                            return False

                    lookup_table = "team_buff_loadouts" if _table_exists("team_buff_loadouts") else "loadouts"
                    base_key = str(found_song_name or "").strip()
                    if "|" in base_key:
                        base_key = base_key.split("|", 1)[0].strip()
                    base_key = base_key.split("(", 1)[0].strip()
                    if not base_key:
                        base_key = str(found_song_name or "").strip()
                    rows = conn.execute(
                        f"SELECT DISTINCT song_name FROM {lookup_table} WHERE song_name LIKE ? LIMIT 8",
                        (f"%{base_key}%",),
                    ).fetchall()
                    if rows:
                        print("[DB] No exact seed found. Similar keys in DB:")
                        for r in rows:
                            # sqlite3.Row supports index access in this connection setup
                            print(f"  - {str(r[0])!r}")
                except Exception:
                    pass

        if load_known_loadouts:
            # Fetch known loadouts for persistent caching
            try:
                conn = get_db_connection_cached()
                def _table_exists(name: str) -> bool:
                    try:
                        return conn.execute(
                            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                            (name,),
                        ).fetchone() is not None
                    except Exception:
                        return False

                song_key = str(found_song_name or "").strip()
                if _table_exists("team_buff_loadouts"):
                    cursor = conn.execute(
                        """SELECT loadout_hash, score, fg_score, force_details_json, details_json
                           FROM team_buff_loadouts
                           WHERE song_name = ? AND team_buff = 'T5'
                           ORDER BY score DESC
                           LIMIT ?""",
                        (song_key, LOADOUTS_PER_SONG_LIMIT),
                    )
                else:
                    cursor = conn.execute(
                        """SELECT loadout_hash, score, fg_score, force_details_json, details_json
                           FROM loadouts
                           WHERE song_name = ?
                           ORDER BY score DESC
                           LIMIT ?""",
                        (song_key, LOADOUTS_PER_SONG_LIMIT),
                    )
                for row in cursor:
                    force_blob = row["force_details_json"]
                    force_data = None
                    if force_blob:
                        force_data = _LazyJsonDict(
                            str(force_blob),
                            warn_key="force-loadout-json",
                            warn_msg=f"Invalid force JSON for {row['loadout_hash']}",
                        )

                    details_blob = row["details_json"]
                    details_data = None
                    if details_blob:
                        details_data = _LazyJsonDict(
                            str(details_blob),
                            warn_key="details-loadout-json",
                            warn_msg=f"Invalid details JSON for {row['loadout_hash']}",
                        )

                    known_loadouts[row["loadout_hash"]] = (
                        row["score"],
                        row["fg_score"],
                        force_data,
                        details_data,
                    )

                _maybe_wal_maintenance(conn)
            except Exception as e:
                print(f"[DB] Error fetching known loadouts: {e}")

    return prev_record, known_loadouts
