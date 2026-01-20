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
LATEST_SCHEMA_VERSION = 9


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
    v6 migration: make loadout identity song-context aware for minis and persist mini variants.

    Changes (data-level; column layout unchanged):
    - `minis_json` becomes a JSON array of arrays (variant groups), rather than a JSON array of strings.
    - `loadout_hash` becomes an "effective" hash computed from gear names + minis' effective signatures for the song.
      Minis that differ only in stats irrelevant to the song context collapse to the same row, and their names are
      unioned inside `minis_json` groups.

    Notes:
    - Best-effort: if we cannot resolve song colors or minis stats, we keep the existing hash and only normalize
      minis_json to list[list[str]].
    """

    import json

    from ..loadout_equivalence import (
        decode_minis_json,
        effective_loadout_hash_from_names,
        effective_mini_signature_for_name,
        encode_minis_groups,
        extract_song_colors,
        get_minis_by_name_cached,
        merge_minis_groups_for_entry,
        representative_mini_names,
    )

    minis_by_name = get_minis_by_name_cached()

    def _safe_json_load(blob: Optional[str]) -> dict:
        if not blob:
            return {}
        try:
            obj = json.loads(blob)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def _safe_json_list(blob: Optional[str]) -> list:
        if not blob:
            return []
        try:
            obj = json.loads(blob)
            return obj if isinstance(obj, list) else []
        except Exception:
            return []

    def _migrate_table(table_name: str) -> None:
        # Create a new table and then swap it in (primary key depends on loadout_hash).
        new_name = f"{table_name}__v6"

        conn.execute(f"DROP TABLE IF EXISTS {new_name};")
        conn.execute(
            f"""
            CREATE TABLE {new_name} (
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
            """
        )

        rows = conn.execute(
            f"""
            SELECT song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp
            FROM {table_name}
            """
        ).fetchall()

        aggregated: dict[tuple[str, str], dict] = {}

        for row in rows or []:
            try:
                song = str(row["song_name"] or "")
            except Exception:
                song = ""
            if not song:
                continue

            old_hash = str(row["loadout_hash"] or "")
            score = int(row["score"] or 0)
            fg_score = int(row["fg_score"] or 0)
            gear_names = [str(x) for x in _safe_json_list(row["gear_json"]) if str(x)]

            details = _safe_json_load(row["details_json"])
            p_color, s_color, sel_color = extract_song_colors(details)

            # Normalize minis_json to canonical groups, then build a representative list for hashing.
            groups_in = decode_minis_json(row["minis_json"])
            mini_names_rep = representative_mini_names(groups_in)

            # Decide whether we can compute the effective hash.
            new_hash = old_hash
            if minis_by_name and (p_color or s_color) and mini_names_rep:
                mini_sigs = [
                    effective_mini_signature_for_name(n, minis_by_name, p_color, s_color, sel_color)
                    for n in mini_names_rep
                ]
                try:
                    new_hash = effective_loadout_hash_from_names(gear_names, mini_sigs)
                except Exception:
                    new_hash = old_hash

            key = (song, new_hash)
            prev = aggregated.get(key)
            if prev is None:
                aggregated[key] = {
                    "song_name": song,
                    "loadout_hash": new_hash,
                    "score": score,
                    "fg_score": fg_score,
                    "gear_json": json.dumps(gear_names, separators=(",", ":")),
                    "minis_groups": groups_in,
                    "details_json": row["details_json"],
                    "force_details_json": row["force_details_json"],
                    "timestamp": row["timestamp"],
                    "p_color": p_color,
                    "s_color": s_color,
                    "sel_color": sel_color,
                }
                continue

            # Merge: keep the best base score; union mini variants; keep best FG + latest timestamp.
            if score > int(prev.get("score", 0) or 0):
                prev["score"] = score
                prev["gear_json"] = json.dumps(gear_names, separators=(",", ":"))
                prev["details_json"] = row["details_json"]

            if fg_score > int(prev.get("fg_score", 0) or 0):
                prev["fg_score"] = fg_score
                prev["force_details_json"] = row["force_details_json"]

            # Union minis variants when we have enough context; otherwise, name-only union.
            if minis_by_name and (p_color or s_color):
                prev_groups = prev.get("minis_groups") or []
                merged = merge_minis_groups_for_entry(
                    prev_groups,
                    mini_names_rep,
                    minis_by_name,
                    p_color,
                    s_color,
                    sel_color,
                )
                prev["minis_groups"] = merged
            else:
                # Conservative: flatten and unique (loses multiplicity but preserves names).
                flat = []
                for g in (prev.get("minis_groups") or []) + groups_in:
                    flat.extend(g or [])
                prev["minis_groups"] = [[n] for n in sorted(set([n for n in flat if n]))]

            # Timestamp: keep max.
            try:
                prev_ts = float(prev.get("timestamp") or 0.0)
            except Exception:
                prev_ts = 0.0
            try:
                cur_ts = float(row["timestamp"] or 0.0)
            except Exception:
                cur_ts = 0.0
            prev["timestamp"] = max(prev_ts, cur_ts)

        # Ensure songs exist for any migrated loadouts (older DBs may have inconsistencies).
        for song_name, _h in aggregated.keys():
            conn.execute(
                "INSERT OR IGNORE INTO songs (name, best_score, best_fg_score, last_updated) VALUES (?, 0, 0, 0)",
                (song_name,),
            )

        # Insert into new table.
        for rec in aggregated.values():
            minis_json = encode_minis_groups(rec.get("minis_groups") or [])
            conn.execute(
                f"""
                INSERT INTO {new_name} (
                    song_name, loadout_hash, score, fg_score,
                    gear_json, minis_json, details_json, force_details_json, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec.get("song_name"),
                    rec.get("loadout_hash"),
                    int(rec.get("score") or 0),
                    int(rec.get("fg_score") or 0),
                    rec.get("gear_json"),
                    minis_json,
                    rec.get("details_json"),
                    rec.get("force_details_json"),
                    rec.get("timestamp"),
                ),
            )

        # Swap tables.
        conn.execute(f"DROP TABLE IF EXISTS {table_name};")
        conn.execute(f"ALTER TABLE {new_name} RENAME TO {table_name};")

    # Foreign keys can trip during swap; do best-effort with FK off.
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
    except Exception:
        pass

    _migrate_table("loadouts")
    _migrate_table("fg_loadouts")

    # Recreate indexes (idempotent).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_loadouts_score ON loadouts (song_name, score DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_loadouts_fg_score ON loadouts (song_name, fg_score DESC);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fg_loadouts_score ON fg_loadouts (song_name, fg_score DESC);")

    try:
        conn.execute("PRAGMA foreign_keys = ON;")
    except Exception:
        pass


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

    These tables mirror `loadouts` / `fg_loadouts` but are partitioned by `team_buff`
    (T1/T5/T10/T15) so the same retained candidates can be re-scored under each tier
    without rerunning the GPU pipeline.
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
