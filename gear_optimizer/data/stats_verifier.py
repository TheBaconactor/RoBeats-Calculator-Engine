"""
Database Stats integrity verification module.

Checks that all loadout entries have properly populated Stats objects
and warns if any issues are detected.
"""

import json
import sqlite3
from typing import Dict, Tuple, Iterable
import logging

from gear_optimizer.data.database import (
    _base_details_from_force_payload,
    _ensure_stats_in_details,
    _load_piece_name_encoding_maps,
    _pack_stats_for_storage,
    _strip_computed_details_fields,
    _unpack_id_groups,
    _unpack_id_list,
    _unpack_stats_after_load,
    get_db_connection,
    get_evolution_db_path,
)
from gear_optimizer.data.loadout_equivalence import representative_mini_names
from gear_optimizer.data.csv_parser import parse_mini_rows
from gear_optimizer.core.config import load_paths_cache



logger = logging.getLogger(__name__)
def _is_stats_empty(stats) -> bool:
    """Check if Stats is missing or empty."""
    if stats is None:
        return True
    if isinstance(stats, dict) and len(stats) == 0:
        return True
    if isinstance(stats, dict):
        # Check if all values are 0
        if not any(stats.values()):
            return True
    return False


def _decode_names_from_row(row: sqlite3.Row, maps) -> tuple[list[str], list[str]]:
    gear_names: list[str] = []
    try:
        ids = _unpack_id_list(row["gear_ids_blob"])
    except Exception as e:
        logger.warning(f"stats_verifier:_decode_names_from_row: {e}")
        ids = []
    if ids:
        gear_names = [str(maps.gear_id_to_name.get(int(i), "") or "") for i in ids]
        gear_names = [n for n in gear_names if n]

    mini_groups: list[list[str]] = []
    try:
        id_groups = _unpack_id_groups(row["minis_ids_blob"])
    except Exception as e:
        logger.warning(f"stats_verifier:_decode_names_from_row: {e}")
        id_groups = []
    for g in id_groups or []:
        if not g:
            continue
        names = [str(maps.mini_id_to_name.get(int(i), "") or "").strip() for i in g if int(i) > 0]
        names = [n for n in names if n]
        if names:
            mini_groups.append(names)
    mini_names = representative_mini_names(mini_groups)
    return gear_names, list(mini_names)


def verify_and_repair_stats(
    *, dry_run: bool = False, verbose: bool = False, sample_size: int = 0
) -> Tuple[bool, Dict[str, int]]:
    """
    Verify database Stats integrity and optionally repair issues.

    Args:
        dry_run: If True, only check without repairing
        verbose: If True, print progress details
        sample_size: If > 0, only check first N entries (for quick validation)

    Returns:
        (all_valid, stats_dict) where:
        - all_valid: True if all entries have valid Stats
        - stats_dict: {"total": N, "missing": M, "empty": E, "repaired": R,
                       "fg_total": N, "fg_empty": E, "fg_repaired": R}
    """
    if verbose:
        print("[StatsVerifier] Loading mini data...")

    paths = load_paths_cache()
    minis_path = paths.get("Minis", "")

    minis_list = parse_mini_rows(minis_path)
    minis_by_name = {m["Name"]: m for m in minis_list}

    if verbose:
        print(f"[StatsVerifier] Loaded {len(minis_by_name)} minis")

    db_path = get_evolution_db_path()
    conn = get_db_connection(str(db_path))

    def _sqlite_json_available(c: sqlite3.Connection) -> bool:
        # SQLite JSON functions are built-in on modern builds (sqlite >= 3.38).
        # Keep a defensive fallback for older environments.
        try:
            c.execute("SELECT json_extract('{\"a\":1}', '$.a')").fetchone()
            return True
        except sqlite3.Error:
            return False

    json_ok = _sqlite_json_available(conn)

    def _iter_base_rows_to_verify(c: sqlite3.Connection, *, table: str, limit: int) -> Iterable[sqlite3.Row]:
        cols = "rowid, song_name, gear_ids_blob, minis_ids_blob, details_json, team_buff"
        q = f"SELECT {cols} FROM {table}"
        if limit > 0:
            q += f" LIMIT {int(limit)}"
        return c.execute(q)

    def _iter_problem_base_rows_sql(c: sqlite3.Connection, *, table: str, limit: int) -> Iterable[sqlite3.Row]:
        # Fast path: only stream rows that look invalid, using SQLite JSON functions.
        #
        # We treat as invalid when:
        # - Stats is missing (NULL json_type)
        # - Stats is an empty object ({})
        # - Stats object exists but all values are 0 (placeholder dict)
        cols = (
            "rowid, song_name, gear_ids_blob, minis_ids_blob, details_json, team_buff, "
            "CASE WHEN json_type(details_json, '$.Stats') IS NULL AND json_type(details_json, '$.st') IS NULL THEN 1 ELSE 0 END AS is_missing"
        )
        q = f"""
            SELECT {cols}
            FROM {table}
            WHERE
                (json_type(details_json, '$.Stats') IS NULL AND json_type(details_json, '$.st') IS NULL)
                OR (
                    json_type(details_json, '$.Stats') = 'object'
                    AND (
                        json_extract(details_json, '$.Stats') = '{{}}'
                        OR NOT EXISTS (
                            SELECT 1 FROM json_each(details_json, '$.Stats')
                            WHERE CAST(value AS REAL) != 0
                        )
                    )
                )
                OR (
                    json_type(details_json, '$.st') = 'array'
                    AND NOT EXISTS (
                        SELECT 1 FROM json_each(details_json, '$.st')
                        WHERE CAST(value AS REAL) != 0
                    )
                )
        """
        if limit > 0:
            q += f" LIMIT {int(limit)}"
        return c.execute(q)

    # ============================================================
    # PART 1: Verify and repair base table (team_buff_loadouts)
    # ============================================================
    base_table = "team_buff_loadouts"
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (base_table,)
    ).fetchone()
    if not table_exists:
        if verbose:
            print("[StatsVerifier] team_buff_loadouts table not found; nothing to verify.")
        conn.close()
        return True, {
            "total": 0,
            "missing": 0,
            "empty": 0,
            "repaired": 0,
            "fg_total": 0,
            "fg_empty": 0,
            "fg_repaired": 0,
        }

    # Total rows is fast via SQLite's count(*) optimization.
    total = int(conn.execute(f"SELECT COUNT(*) FROM {base_table}").fetchone()[0] or 0)
    missing = 0
    empty = 0
    repaired = 0

    if verbose and total > 0:
        print(f"[StatsVerifier] Checking {total} {base_table} entries...")

    # sample_size>0: validate the first N rows (quick check).
    # sample_size==0: validate full table. Use SQLite JSON functions to avoid Python-level scan.
    verify_limit = int(sample_size) if int(sample_size) > 0 else 0
    if json_ok and verify_limit <= 0:
        row_iter = _iter_problem_base_rows_sql(conn, table=base_table, limit=0)
    else:
        row_iter = _iter_base_rows_to_verify(conn, table=base_table, limit=verify_limit)

    for i, row in enumerate(row_iter):
        # In sample mode we still iterate through N rows; keep lightweight progress logs.
        if verbose and verify_limit > 0 and verify_limit > 1000 and i > 0 and i % 10000 == 0:
            print(f"[StatsVerifier] {base_table} sample progress: {i}/{verify_limit}...")

        details = json.loads(row["details_json"]) if row["details_json"] else {}
        details = _unpack_stats_after_load(details) or {}
        stats = details.get("Stats") if isinstance(details, dict) else None

        # Check for missing or empty Stats
        issue_type = None
        # Fast-path categorization for SQL-selected rows.
        if json_ok and verify_limit <= 0 and ("is_missing" in row.keys()):
            is_missing = bool(row["is_missing"])
            if is_missing:
                issue_type = "missing"
                missing += 1
            else:
                issue_type = "empty"
                empty += 1
        elif stats is None:
            issue_type = "missing"
            missing += 1
        elif isinstance(stats, dict) and len(stats) == 0:
            issue_type = "empty"
            empty += 1
        elif isinstance(stats, dict):
            # Verify Stats has at least some elemental values
            elemental_keys = ["Chill", "Flow", "Rush", "Beat", "Vibe"]
            has_any_elemental = any(stats.get(k, 0) != 0 for k in elemental_keys)
            if not has_any_elemental and not any(stats.values()):
                issue_type = "empty"
                empty += 1

        if issue_type:
            if not dry_run:
                maps = _load_piece_name_encoding_maps(conn, db_path=str(db_path))
                gear_names, mini_names = _decode_names_from_row(row, maps)

                details = _ensure_stats_in_details(
                    details,
                    gear_names,
                    mini_names,
                    minis_by_name,
                    team_buff=row["team_buff"] if isinstance(row, sqlite3.Row) else None,
                    team_color=str(details.get("PrimaryColor") or details.get("Primary Color") or "").strip(),
                )
                details = _pack_stats_for_storage(_strip_computed_details_fields(details)) if details else details

                conn.execute(
                    f"UPDATE {base_table} SET details_json = ? WHERE rowid = ?",
                    (json.dumps(details, separators=(",", ":")), row["rowid"]),
                )
                repaired += 1

    if not dry_run and repaired > 0:
        conn.commit()
        if verbose:
            print(f"[StatsVerifier] Committed {repaired} repairs to {base_table} table")

    # ============================================================
    # PART 2: Verify and repair team_buff_fg_loadouts table
    # ============================================================
    fg_total, fg_empty, fg_repaired = _verify_fg_table(
        conn,
        "team_buff_fg_loadouts",
        minis_by_name,
        dry_run=dry_run,
        verbose=verbose,
        sample_size=sample_size,
        json_ok=json_ok,
    )

    conn.close()

    all_valid = missing == 0 and empty == 0 and fg_empty == 0
    stats_dict = {
        "total": total,
        "missing": missing,
        "empty": empty,
        "repaired": repaired,
        "fg_total": fg_total,
        "fg_empty": fg_empty,
        "fg_repaired": fg_repaired,
    }

    return all_valid, stats_dict


def _verify_fg_table(
    conn: sqlite3.Connection,
    table_name: str,
    minis_by_name: Dict,
    *,
    dry_run: bool,
    verbose: bool,
    sample_size: int,
    json_ok: bool,
) -> Tuple[int, int, int]:
    """
    Verify and repair team_buff_fg_loadouts.

    FG table `details_json` must explain/replay the paired base `score`.
    `force_details_json` explains/replays `fg_score`; when the force payload has
    BaseStats+gems, repair derives the base details from that same allocation.

    Returns: (total, empty, repaired)
    """
    # Check if table exists
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    ).fetchone()
    if not table_exists:
        if verbose:
            print(f"[StatsVerifier] Table {table_name} does not exist, skipping...")
        return 0, 0, 0

    select_cols = [
        "rowid",
        "song_name",
        "team_buff",
        "loadout_hash",
        "gear_ids_blob",
        "minis_ids_blob",
        "details_json",
        "force_details_json",
    ]
    total = int(conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0] or 0)
    empty_count = 0
    repaired_count = 0

    if verbose and total > 0:
        print(f"[StatsVerifier] Checking {total} {table_name} entries...")

    verify_limit = int(sample_size) if int(sample_size) > 0 else 0

    def _iter_fg_rows_to_verify(c: sqlite3.Connection, *, limit: int) -> Iterable[sqlite3.Row]:
        q = f"SELECT {', '.join(select_cols)} FROM {table_name}"
        if limit > 0:
            q += f" LIMIT {int(limit)}"
        return c.execute(q)

    def _iter_problem_fg_rows_sql(c: sqlite3.Connection, *, limit: int) -> Iterable[sqlite3.Row]:
        # See base table for invalid definitions; apply the same rules here.
        q = f"""
            SELECT
                {", ".join(select_cols)},
                CASE WHEN json_type(details_json, '$.Stats') IS NULL AND json_type(details_json, '$.st') IS NULL THEN 1 ELSE 0 END AS is_missing
            FROM {table_name}
            WHERE
                (json_type(details_json, '$.Stats') IS NULL AND json_type(details_json, '$.st') IS NULL)
                OR (
                    json_type(details_json, '$.Stats') = 'object'
                    AND (
                        json_extract(details_json, '$.Stats') = '{{}}'
                        OR NOT EXISTS (
                            SELECT 1 FROM json_each(details_json, '$.Stats')
                            WHERE CAST(value AS REAL) != 0
                        )
                    )
                )
                OR (
                    json_type(details_json, '$.st') = 'array'
                    AND NOT EXISTS (
                        SELECT 1 FROM json_each(details_json, '$.st')
                        WHERE CAST(value AS REAL) != 0
                    )
                )
        """
        if limit > 0:
            q += f" LIMIT {int(limit)}"
        return c.execute(q)

    if json_ok and verify_limit <= 0:
        row_iter = _iter_problem_fg_rows_sql(conn, limit=0)
    else:
        row_iter = _iter_fg_rows_to_verify(conn, limit=verify_limit)

    for i, row in enumerate(row_iter):
        if verbose and verify_limit > 0 and verify_limit > 1000 and i > 0 and i % 10000 == 0:
            print(f"[StatsVerifier] {table_name} sample progress: {i}/{verify_limit}...")

        details = json.loads(row["details_json"]) if row["details_json"] else {}
        details = _unpack_stats_after_load(details) or {}
        stats = details.get("Stats") if isinstance(details, dict) else None

        is_empty = _is_stats_empty(stats)
        if json_ok and verify_limit <= 0 and ("is_missing" in row.keys()):
            # SQL-selected rows are always invalid; treat them as empty to preserve old counters.
            is_empty = True

        if is_empty:
            empty_count += 1

            if not dry_run:
                base_row = conn.execute(
                    """
                    SELECT details_json
                    FROM team_buff_loadouts
                    WHERE song_name = ? AND team_buff = ? AND loadout_hash = ?
                    LIMIT 1
                    """,
                    (row["song_name"], row["team_buff"], row["loadout_hash"]),
                ).fetchone()
                base_details = None
                if base_row is not None and base_row["details_json"]:
                    try:
                        base_details = _unpack_stats_after_load(json.loads(base_row["details_json"])) or {}
                    except Exception as e:
                        logger.warning(f"stats_verifier:_iter_problem_fg_rows_sql: {e}")
                        base_details = None

                force_payload = {}
                if row["force_details_json"]:
                    try:
                        force_payload = json.loads(row["force_details_json"]) or {}
                    except Exception as e:
                        logger.warning(f"stats_verifier:_iter_problem_fg_rows_sql: {e}")
                        force_payload = {}

                fg_base_details = _base_details_from_force_payload(base_details or details, force_payload)
                if isinstance(fg_base_details, dict) and not _is_stats_empty(fg_base_details.get("Stats")):
                    details = fg_base_details
                elif isinstance(base_details, dict) and not _is_stats_empty(base_details.get("Stats")):
                    details = dict(base_details)
                elif isinstance(details, dict):
                    # Recompute from gear/minis/gems
                    maps = _load_piece_name_encoding_maps(conn, db_path=str(get_evolution_db_path()))
                    gear_names, mini_names = _decode_names_from_row(row, maps)

                    details = _ensure_stats_in_details(
                        details,
                        gear_names,
                        mini_names,
                        minis_by_name,
                        team_buff=row["team_buff"] if isinstance(row, sqlite3.Row) else None,
                        team_color=str(details.get("PrimaryColor") or details.get("Primary Color") or "").strip(),
                    )
                else:
                    continue

                details = _pack_stats_for_storage(_strip_computed_details_fields(details)) if details else details

                conn.execute(
                    f"UPDATE {table_name} SET details_json = ? WHERE rowid = ?",
                    (json.dumps(details, separators=(",", ":")), row["rowid"]),
                )
                repaired_count += 1

    if not dry_run and repaired_count > 0:
        conn.commit()
        if verbose:
            print(f"[StatsVerifier] Committed {repaired_count} repairs to {table_name}")

    return total, empty_count, repaired_count


def print_verification_warning(stats_dict: Dict[str, int]) -> None:
    """Print a prominent warning if Stats issues were detected."""
    missing = stats_dict.get("missing", 0)
    empty = stats_dict.get("empty", 0)
    fg_empty = stats_dict.get("fg_empty", 0)
    fg_total = stats_dict.get("fg_total", 0)

    total_issues = missing + empty + fg_empty

    if total_issues > 0:
        print("\n" + "=" * 80)
        print("+" + "=" * 78 + "+")
        print("|" + " " * 78 + "|")
        print("|" + "   WARNING: DATABASE STATS INTEGRITY ISSUE".center(78) + "|")
        print("|" + " " * 78 + "|")
        print("+" + "=" * 78 + "+")
        print(f"  Found {total_issues:,} entries with invalid Stats:")
        if missing > 0:
            print(f"    - team_buff_loadouts: {missing:,} entries have MISSING Stats (None)")
        if empty > 0:
            print(f"    - team_buff_loadouts: {empty:,} entries have EMPTY Stats ({{}})")
        if fg_empty > 0:
            print(f"    - team_buff_fg_loadouts: {fg_empty:,} / {fg_total:,} entries have EMPTY Stats")
        print()
        print("  This means elemental stats (Chill/Flow/Rush/Beat/Vibe) will show as 0")
        print("  in the frontend/extractor, causing incorrect score calculations!")
        print()
        print("  SOLUTION: Run tools/db/backfill_stats.py to repair the database:")
        print("    python tools/db/backfill_stats.py")
        print("=" * 80 + "\n")
