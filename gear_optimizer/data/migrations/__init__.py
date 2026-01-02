"""
SQLite schema versioning for the evolution database.

We use `PRAGMA user_version` as the single source of truth for schema state.
"""

from __future__ import annotations

import sqlite3
from typing import Callable, Dict

Migration = Callable[[sqlite3.Connection], None]

LATEST_SCHEMA_VERSION = 3


def _migration_1_init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS songs (
            name TEXT PRIMARY KEY,
            best_score INTEGER DEFAULT 0,
            best_fg_score INTEGER DEFAULT 0,
            last_updated REAL
        );
        CREATE TABLE IF NOT EXISTS loadouts (
            song_name TEXT,
            loadout_hash TEXT,
            score INTEGER,
            fg_score INTEGER DEFAULT 0,
            gear_json TEXT,
            minis_json TEXT,
            details_json TEXT,
            force_details_json TEXT,
            timestamp REAL,
            PRIMARY KEY (song_name, loadout_hash),
            FOREIGN KEY (song_name) REFERENCES songs(name)
        );

        -- Separate table for Force Greats loadouts to prevent leaderboard pollution
        CREATE TABLE IF NOT EXISTS fg_loadouts (
            song_name TEXT,
            loadout_hash TEXT,
            score INTEGER, -- Base score context
            fg_score INTEGER,
            gear_json TEXT,
            minis_json TEXT,
            details_json TEXT,
            force_details_json TEXT,
            timestamp REAL,
            PRIMARY KEY (song_name, loadout_hash),
            FOREIGN KEY (song_name) REFERENCES songs(name)
        );

        CREATE INDEX IF NOT EXISTS idx_loadouts_score ON loadouts (song_name, score DESC);
        CREATE INDEX IF NOT EXISTS idx_loadouts_fg_score ON loadouts (song_name, fg_score DESC); -- Legacy index, keep for now
        CREATE INDEX IF NOT EXISTS idx_fg_loadouts_score ON fg_loadouts (song_name, fg_score DESC);
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


def _migration_3_add_swing_json(conn: sqlite3.Connection) -> None:
    """
    Add SwingDetector storage columns.

    `swing_json` is a compact JSON array of signed deltas (non-zero) that represent
    score variance under HumanHitSim seeds.
    """

    def _has_column(table: str, column: str) -> bool:
        try:
            rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
            return any(r[1] == column for r in rows)
        except Exception:
            return False

    for table in ("loadouts", "fg_loadouts"):
        if not _has_column(table, "swing_json"):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN swing_json TEXT;")


_MIGRATIONS: Dict[int, Migration] = {
    1: _migration_1_init_schema,
    2: _migration_2_add_pending_fg_jobs,
    3: _migration_3_add_swing_json,
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
