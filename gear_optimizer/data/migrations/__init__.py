"""
SQLite schema versioning for the evolution database.

We use `PRAGMA user_version` as the single source of truth for schema state.
"""

from __future__ import annotations

import sqlite3
from typing import Callable, Dict, Optional

Migration = Callable[[sqlite3.Connection], None]

# NOTE: `evolution.db` in the wild may already have `PRAGMA user_version=8` even though
# the physical schema matches v6 (v6 is a data-level migration only). Keep v7/v8 as
# no-ops so older DBs can advance and newer DBs won't be rejected.
LATEST_SCHEMA_VERSION = 16


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

    conn.execute("DROP TABLE IF EXISTS pending_swing_jobs;")
    return


def _migration_6_effective_loadout_hash_and_mini_variants(conn: sqlite3.Connection) -> None:
    """
    No-op (deprecated loadout tables removed).
    """
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

    These tables are the canonical base/FG leaderboards, partitioned by `team_buff`
    (T1/T5/T10/T15), so retained candidates can be re-scored under each tier without
    rerunning the GPU pipeline.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS team_buff_loadouts (
            song_name TEXT,
            team_buff TEXT,
            loadout_hash TEXT,
            score INTEGER,
            fg_score INTEGER DEFAULT 0,
            gear_json TEXT,
            minis_json TEXT,
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
            gear_json TEXT,
            minis_json TEXT,
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

    # SQLite doesn't support `ADD COLUMN IF NOT EXISTS` on all versions we may encounter,
    # so do best-effort adds and tolerate duplicates.
    for stmt in (
        "ALTER TABLE songs ADD COLUMN attempt_lifetime INTEGER DEFAULT 0;",
        "ALTER TABLE songs ADD COLUMN attempts_first INTEGER DEFAULT 0;",
    ):
        try:
            conn.execute(stmt)
        except sqlite3.Error:
            # Likely: duplicate column name (already migrated).
            pass


def _migration_11_add_team_buff_to_fg_loadouts(conn: sqlite3.Connection) -> None:
    """
    No-op (team_buff tables already include tier metadata).
    """
    return


def _migration_12_add_fg_loadouts_unified_view(conn: sqlite3.Connection) -> None:
    """Create a unified FG view across tiers."""
    # Ensure idempotent updates in case the view definition changes.
    conn.execute("DROP VIEW IF EXISTS fg_loadouts_unified;")
    conn.execute(
        """
        CREATE VIEW fg_loadouts_unified AS
        SELECT
            song_name,
            team_buff,
            loadout_hash,
            score,
            fg_score,
            gear_json,
            minis_json,
            details_json,
            force_details_json,
            timestamp,
            'team_buff_fg_loadouts' AS source_table
        FROM team_buff_fg_loadouts;
        """
    )


def _migration_13_add_frontend_base_top51_view(conn: sqlite3.Connection) -> None:
    """
    Create a frontend-oriented view for "Top 51" base (non-FG) rows per song + team_buff.

    Columns include:
      - song_title / difficulty derived from the "(Easy)/(Normal)/(Hard)" suffix (or default Normal)
      - rank (1..51) within (song_name, team_buff) ordered by score desc

    NOTE: team_buff values are emitted as DB keys (e.g. NONE, T1, T5, T10, T15).
    """
    conn.execute("DROP VIEW IF EXISTS frontend_base_top51_by_song_tier;")
    conn.execute(
        """
        CREATE VIEW frontend_base_top51_by_song_tier AS
        WITH base AS (
            SELECT
                song_name,
                UPPER(team_buff) AS team_buff,
                loadout_hash,
                score,
                gear_json,
                minis_json,
                details_json,
                timestamp
            FROM team_buff_loadouts
            WHERE UPPER(team_buff) != 'NONE'
        ),
        ranked AS (
            SELECT
                song_name,
                CASE
                    WHEN instr(song_name, ' (Easy) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Easy) by ') - 1))
                    WHEN instr(song_name, ' (Hard) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Hard) by ') - 1))
                    WHEN instr(song_name, ' (Normal) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Normal) by ') - 1))
                    WHEN instr(song_name, ' by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' by ') - 1))
                    ELSE song_name
                END AS song_title,
                CASE
                    WHEN instr(song_name, ' (Easy) by ') > 0 THEN 'Easy'
                    WHEN instr(song_name, ' (Hard) by ') > 0 THEN 'Hard'
                    WHEN instr(song_name, ' (Normal) by ') > 0 THEN 'Normal'
                    ELSE 'Normal'
                END AS difficulty,
                team_buff,
                ROW_NUMBER() OVER (PARTITION BY song_name, team_buff ORDER BY score DESC) AS rank,
                loadout_hash,
                score,
                gear_json,
                minis_json,
                details_json,
                timestamp
            FROM base
        )
        SELECT
            song_name,
            song_title,
            difficulty,
            team_buff,
            rank,
            loadout_hash,
            score,
            gear_json,
            minis_json,
            details_json,
            timestamp
        FROM ranked
        WHERE rank <= 51;
        """
    )


def _migration_14_add_frontend_fg_top51_view(conn: sqlite3.Connection) -> None:
    """
    Create a frontend-oriented view for "Top 51" FG rows per song + team_buff.

    Uses `fg_loadouts_unified` as the single FG surface and ranks by fg_score desc.
    """
    conn.execute("DROP VIEW IF EXISTS frontend_fg_top51_by_song_tier;")
    conn.execute(
        """
        CREATE VIEW frontend_fg_top51_by_song_tier AS
        WITH ranked AS (
            SELECT
                song_name,
                CASE
                    WHEN instr(song_name, ' (Easy) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Easy) by ') - 1))
                    WHEN instr(song_name, ' (Hard) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Hard) by ') - 1))
                    WHEN instr(song_name, ' (Normal) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Normal) by ') - 1))
                    WHEN instr(song_name, ' by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' by ') - 1))
                    ELSE song_name
                END AS song_title,
                CASE
                    WHEN instr(song_name, ' (Easy) by ') > 0 THEN 'Easy'
                    WHEN instr(song_name, ' (Hard) by ') > 0 THEN 'Hard'
                    WHEN instr(song_name, ' (Normal) by ') > 0 THEN 'Normal'
                    ELSE 'Normal'
                END AS difficulty,
                UPPER(team_buff) AS team_buff,
                ROW_NUMBER() OVER (PARTITION BY song_name, UPPER(team_buff) ORDER BY fg_score DESC) AS rank,
                loadout_hash,
                score,
                fg_score,
                gear_json,
                minis_json,
                details_json,
                force_details_json,
                timestamp,
                source_table
            FROM fg_loadouts_unified
            WHERE fg_score > 0
        )
        SELECT
            song_name,
            song_title,
            difficulty,
            team_buff,
            rank,
            loadout_hash,
            score,
            fg_score,
            gear_json,
            minis_json,
            details_json,
            force_details_json,
            timestamp,
            source_table
        FROM ranked
        WHERE rank <= 51;
        """
    )


def _migration_15_add_loadouts_unified_and_frontend_best_views(conn: sqlite3.Connection) -> None:
    """
    Add unified base view + frontend convenience views.

    These views are used by frontend/export consumers that want a single query surface and
    deterministic "best row" selection rules.
    """

    # Base unified view (mirrors `fg_loadouts_unified` behavior).
    conn.execute("DROP VIEW IF EXISTS loadouts_unified;")
    conn.execute(
        """
        CREATE VIEW loadouts_unified AS
        SELECT
            song_name,
            UPPER(team_buff) AS team_buff,
            loadout_hash,
            score,
            fg_score,
            gear_json,
            minis_json,
            details_json,
            force_details_json,
            timestamp,
            'team_buff_loadouts' AS source_table
        FROM team_buff_loadouts;
        """
    )

    # Deterministic "best row" surfaces per (song_name, team_buff).
    conn.execute("DROP VIEW IF EXISTS frontend_best_base_loadouts;")
    conn.execute(
        """
        CREATE VIEW frontend_best_base_loadouts AS
        SELECT
            song_name,
            team_buff,
            loadout_hash,
            score,
            fg_score,
            gear_json,
            minis_json,
            details_json,
            force_details_json,
            timestamp,
            source_table
        FROM (
            SELECT
                lu.*,
                ROW_NUMBER() OVER (
                    PARTITION BY lu.song_name, lu.team_buff
                    ORDER BY lu.score DESC, lu.fg_score DESC, lu.timestamp DESC
                ) AS rn
            FROM loadouts_unified lu
        )
        WHERE rn = 1;
        """
    )

    conn.execute("DROP VIEW IF EXISTS frontend_best_fg_loadouts;")
    conn.execute(
        """
        CREATE VIEW frontend_best_fg_loadouts AS
        SELECT
            song_name,
            UPPER(team_buff) AS team_buff,
            loadout_hash,
            score,
            fg_score,
            gear_json,
            minis_json,
            details_json,
            force_details_json,
            timestamp,
            source_table
        FROM (
            SELECT
                fu.*,
                ROW_NUMBER() OVER (
                    PARTITION BY fu.song_name, UPPER(fu.team_buff)
                    ORDER BY fu.fg_score DESC, fu.score DESC, fu.timestamp DESC
                ) AS rn
            FROM fg_loadouts_unified fu
        )
        WHERE rn = 1;
        """
    )

    # Recreate top51 views to use the unified sources and to parse difficulty/title from the standard "(Hard) by" form.
    conn.execute("DROP VIEW IF EXISTS frontend_base_top51_by_song_tier;")
    conn.execute(
        """
        CREATE VIEW frontend_base_top51_by_song_tier AS
        WITH ranked AS (
            SELECT
                lu.*,
                ROW_NUMBER() OVER (
                    PARTITION BY lu.song_name, lu.team_buff
                    ORDER BY lu.score DESC, lu.fg_score DESC, lu.timestamp DESC
                ) AS rank
            FROM loadouts_unified lu
        )
        SELECT
            song_name,
            CASE
                WHEN instr(song_name, ' (Easy) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Easy) by ') - 1))
                WHEN instr(song_name, ' (Hard) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Hard) by ') - 1))
                WHEN instr(song_name, ' (Normal) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Normal) by ') - 1))
                WHEN instr(song_name, ' by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' by ') - 1))
                ELSE song_name
            END AS song_title,
            CASE
                WHEN instr(song_name, ' (Easy) by ') > 0 THEN 'Easy'
                WHEN instr(song_name, ' (Hard) by ') > 0 THEN 'Hard'
                WHEN instr(song_name, ' (Normal) by ') > 0 THEN 'Normal'
                ELSE 'Normal'
            END AS difficulty,
            team_buff,
            rank,
            loadout_hash,
            score,
            fg_score,
            gear_json,
            minis_json,
            details_json,
            force_details_json,
            timestamp,
            source_table
        FROM ranked
        WHERE rank <= 51;
        """
    )

    conn.execute("DROP VIEW IF EXISTS frontend_fg_top51_by_song_tier;")
    conn.execute(
        """
        CREATE VIEW frontend_fg_top51_by_song_tier AS
        WITH ranked AS (
            SELECT
                fu.*,
                ROW_NUMBER() OVER (
                    PARTITION BY fu.song_name, UPPER(fu.team_buff)
                    ORDER BY fu.fg_score DESC, fu.score DESC, fu.timestamp DESC
                ) AS rank
            FROM fg_loadouts_unified fu
            WHERE fg_score > 0
        )
        SELECT
            song_name,
            CASE
                WHEN instr(song_name, ' (Easy) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Easy) by ') - 1))
                WHEN instr(song_name, ' (Hard) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Hard) by ') - 1))
                WHEN instr(song_name, ' (Normal) by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' (Normal) by ') - 1))
                WHEN instr(song_name, ' by ') > 0 THEN trim(substr(song_name, 1, instr(song_name, ' by ') - 1))
                ELSE song_name
            END AS song_title,
            CASE
                WHEN instr(song_name, ' (Easy) by ') > 0 THEN 'Easy'
                WHEN instr(song_name, ' (Hard) by ') > 0 THEN 'Hard'
                WHEN instr(song_name, ' (Normal) by ') > 0 THEN 'Normal'
                ELSE 'Normal'
            END AS difficulty,
            UPPER(team_buff) AS team_buff,
            rank,
            loadout_hash,
            score,
            fg_score,
            gear_json,
            minis_json,
            details_json,
            force_details_json,
            timestamp,
            source_table
        FROM ranked
        WHERE rank <= 51;
        """
    )


def _migration_16_drop_deprecated_tables(conn: sqlite3.Connection) -> None:
    """
    Drop deprecated base/FG tables and refresh unified views.
    """
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

    # Refresh views to ensure they no longer reference deprecated tables.
    _migration_12_add_fg_loadouts_unified_view(conn)
    _migration_15_add_loadouts_unified_and_frontend_best_views(conn)


_MIGRATIONS: Dict[int, Migration] = {
    1: _migration_1_init_schema,
    2: _migration_2_add_pending_fg_jobs,
    3: _migration_3_noop,
    4: _migration_4_noop,
    5: _migration_5_cleanup,
    6: _migration_6_effective_loadout_hash_and_mini_variants,
    7: _migration_7_noop,
    8: _migration_8_noop,
    9: _migration_9_add_team_buff_tier_tables,
    10: _migration_10_add_song_attempt_counters,
    11: _migration_11_add_team_buff_to_fg_loadouts,
    12: _migration_12_add_fg_loadouts_unified_view,
    13: _migration_13_add_frontend_base_top51_view,
    14: _migration_14_add_frontend_fg_top51_view,
    15: _migration_15_add_loadouts_unified_and_frontend_best_views,
    16: _migration_16_drop_deprecated_tables,
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
