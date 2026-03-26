"""
SQLite schema versioning for the evolution database.

We use `PRAGMA user_version` as the single source of truth for schema state.

Note: This repo intentionally does NOT provide or maintain legacy view-based schemas.
Consumers should use `gear_optimizer.data.db_manager.EvolutionDbManager` for reads.
"""

from __future__ import annotations

import sqlite3
from typing import Callable, Dict

Migration = Callable[[sqlite3.Connection], None]

# NOTE: `evolution.db` in the wild may already have `PRAGMA user_version=8` even though
# the physical schema matches v6 (v6 is a data-level migration only). Keep v7/v8 as
# no-ops so older DBs can advance and newer DBs won't be rejected.
LATEST_SCHEMA_VERSION = 18


def _migration_1_init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS songs (
            name TEXT PRIMARY KEY,
            best_score INTEGER DEFAULT 0,
            best_fg_score INTEGER DEFAULT 0,
            last_updated REAL
        );
        """
    )


def _migration_2_add_pending_fg_jobs(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS pending_fg_jobs (
            song_name TEXT PRIMARY KEY,
            candidates_json TEXT NOT NULL,
            created_ts REAL,
            updated_ts REAL
        );

        CREATE INDEX IF NOT EXISTS idx_pending_fg_jobs_updated
            ON pending_fg_jobs (updated_ts DESC);
        """
    )


def _migration_3_noop(conn: sqlite3.Connection) -> None:
    """
    No-op migration (schema version continuity).

    Schema version 3 was used by an experimental feature that has since been removed.
    """
    return


def _migration_4_noop(conn: sqlite3.Connection) -> None:
    """
    No-op migration (schema version continuity).

    Schema version 4 was used by an experimental feature that has since been removed.
    """
    return


def _migration_5_cleanup(conn: sqlite3.Connection) -> None:
    """
    Cleanup migration (schema version continuity).

    Drops unused tables from older experimental schemas (best-effort).
    """
    try:
        conn.execute("DROP TABLE IF EXISTS pending_swing_jobs;")
    except sqlite3.Error:
        pass
    return


def _migration_6_noop(conn: sqlite3.Connection) -> None:
    """No-op (deprecated loadout tables removed)."""
    return


def _migration_7_noop(conn: sqlite3.Connection) -> None:
    """
    No-op migration (schema version continuity).

    Schema version 7 did not introduce any physical schema changes in this repo.
    """
    return


def _migration_8_noop(conn: sqlite3.Connection) -> None:
    """
    No-op migration (schema version continuity).

    Schema version 8 did not introduce any physical schema changes in this repo.
    """
    return


def _migration_9_add_team_buff_tier_tables(conn: sqlite3.Connection) -> None:
    """
    Add TeamBuff-tiered leaderboards.

    These tables are the canonical base/FG leaderboards, partitioned by `team_buff`.
    The compact workflow stores gear/minis via encoding-table IDs in BLOB columns.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS team_buff_loadouts (
            song_name TEXT,
            team_buff TEXT,
            loadout_hash TEXT,
            score INTEGER,
            fg_score INTEGER DEFAULT 0,
            gear_ids_blob BLOB,
            minis_ids_blob BLOB,
            details_json TEXT,
            force_details_json TEXT,
            timestamp REAL,
            PRIMARY KEY (song_name, team_buff, loadout_hash),
            FOREIGN KEY (song_name) REFERENCES songs(name)
        );

        CREATE TABLE IF NOT EXISTS team_buff_fg_loadouts (
            song_name TEXT,
            team_buff TEXT,
            loadout_hash TEXT,
            score INTEGER, -- Base score context under this TeamBuff tier
            fg_score INTEGER,
            gear_ids_blob BLOB,
            minis_ids_blob BLOB,
            details_json TEXT,
            force_details_json TEXT,
            timestamp REAL,
            PRIMARY KEY (song_name, team_buff, loadout_hash),
            FOREIGN KEY (song_name) REFERENCES songs(name)
        );

        CREATE INDEX IF NOT EXISTS idx_team_buff_loadouts_score
            ON team_buff_loadouts (song_name, team_buff, score DESC);
        CREATE INDEX IF NOT EXISTS idx_team_buff_loadouts_fg_score
            ON team_buff_loadouts (song_name, team_buff, fg_score DESC);
        CREATE INDEX IF NOT EXISTS idx_team_buff_fg_loadouts_score
            ON team_buff_fg_loadouts (song_name, team_buff, fg_score DESC);
        """
    )


def _migration_10_add_song_attempt_counters(conn: sqlite3.Connection) -> None:
    """
    Add per-song attempt counters.

    - `attempt_lifetime`: increments once per processed run, monotonically.
    - `attempts_first`: increments once per processed run but resets to 1 on any
      new base OR FG record (per-song).
    """
    for stmt in (
        "ALTER TABLE songs ADD COLUMN attempt_lifetime INTEGER DEFAULT 0;",
        "ALTER TABLE songs ADD COLUMN attempts_first INTEGER DEFAULT 0;",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.Error:
            # Likely: duplicate column name (already migrated).
            pass


def _migration_11_noop(conn: sqlite3.Connection) -> None:
    """No-op (team_buff tables already include tier metadata)."""
    return


def _migration_12_noop(conn: sqlite3.Connection) -> None:
    """Removed: legacy SQL views."""
    return


def _migration_13_noop(conn: sqlite3.Connection) -> None:
    """Removed: legacy frontend SQL views."""
    return


def _migration_14_noop(conn: sqlite3.Connection) -> None:
    """Removed: legacy frontend SQL views."""
    return


def _migration_15_noop(conn: sqlite3.Connection) -> None:
    """Removed: legacy unified/frontend SQL views."""
    return


def _migration_16_drop_deprecated_tables(conn: sqlite3.Connection) -> None:
    """Drop deprecated base/FG tables (best-effort)."""
    for stmt in (
        "DROP INDEX IF EXISTS idx_loadouts_score;",
        "DROP INDEX IF EXISTS idx_loadouts_fg_score;",
        "DROP INDEX IF EXISTS idx_fg_loadouts_score;",
        "DROP INDEX IF EXISTS idx_fg_loadouts_team_buff;",
        "DROP TABLE IF EXISTS loadouts;",
        "DROP TABLE IF EXISTS fg_loadouts;",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.Error:
            pass
    return


def _migration_17_noop(conn: sqlite3.Connection) -> None:
    """Removed: legacy color-aware frontend SQL views."""
    return


def _migration_18_add_piece_name_encoding_tables(conn: sqlite3.Connection) -> None:
    """
    Add compact name encodings for gear/minis.

    These tables de-duplicate repeated piece names across rows.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gear_name_encoding (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS mini_name_encoding (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        """
    )


_MIGRATIONS: Dict[int, Migration] = {
    1: _migration_1_init_schema,
    2: _migration_2_add_pending_fg_jobs,
    3: _migration_3_noop,
    4: _migration_4_noop,
    5: _migration_5_cleanup,
    6: _migration_6_noop,
    7: _migration_7_noop,
    8: _migration_8_noop,
    9: _migration_9_add_team_buff_tier_tables,
    10: _migration_10_add_song_attempt_counters,
    11: _migration_11_noop,
    12: _migration_12_noop,
    13: _migration_13_noop,
    14: _migration_14_noop,
    15: _migration_15_noop,
    16: _migration_16_drop_deprecated_tables,
    17: _migration_17_noop,
    18: _migration_18_add_piece_name_encoding_tables,
}


def get_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version;").fetchone()
    if not row:
        return 0
    return int(row[0] or 0)


def set_schema_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {int(version)};")


def ensure_schema(conn: sqlite3.Connection) -> None:
    current = get_schema_version(conn)
    if current > LATEST_SCHEMA_VERSION:
        raise RuntimeError(f"DB schema version {current} is newer than this app supports ({LATEST_SCHEMA_VERSION}).")
    if current == LATEST_SCHEMA_VERSION:
        return

    with conn:
        for version in range(current + 1, LATEST_SCHEMA_VERSION + 1):
            migration = _MIGRATIONS.get(version)
            if migration is None:
                raise RuntimeError(f"Missing migration for schema version {version}.")
            migration(conn)
            set_schema_version(conn, version)
