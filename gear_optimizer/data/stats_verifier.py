"""
Database Stats integrity verification module.

Checks that all loadout entries have properly populated Stats objects
and warns if any issues are detected.
"""

import json
import sqlite3
from typing import Dict, List, Tuple

from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.database import _ensure_stats_in_details, get_evolution_db_path
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows
from gear_optimizer.core.config import load_paths_cache


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
                       "fg_total": N, "fg_empty": E, "fg_repaired": R,
                       "tb_fg_total": N, "tb_fg_empty": E, "tb_fg_repaired": R}
    """
    if verbose:
        print("[StatsVerifier] Loading gear and mini data...")

    paths = load_paths_cache()
    gears_path = paths.get("Gears", "")
    minis_path = paths.get("Minis", "")

    gears_list = parse_gear_rows(gears_path)
    minis_list = parse_mini_rows(minis_path)
    gears_by_name = {g["Name"]: g for g in gears_list}
    minis_by_name = {m["Name"]: m for m in minis_list}

    if verbose:
        print(f"[StatsVerifier] Loaded {len(gears_by_name)} gears, {len(minis_by_name)} minis")

    # Empty base stats - DB Stats represent ONLY loadout contribution (gear+minis+gems)
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

    db_path = get_evolution_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # ============================================================
    # PART 1: Verify and repair base table (team_buff_loadouts preferred)
    # ============================================================
    base_table = "team_buff_loadouts"
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (base_table,)
    ).fetchone()
    if not table_exists:
        base_table = "loadouts"

    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({base_table})").fetchall()}
    has_team_buff = "team_buff" in cols
    select_cols = ["rowid", "song_name", "gear_json", "minis_json", "details_json"]
    if has_team_buff:
        select_cols.append("team_buff")

    query = f"SELECT {', '.join(select_cols)} FROM {base_table}"
    if sample_size > 0:
        query += f" LIMIT {int(sample_size)}"

    cur = conn.execute(query)
    rows = cur.fetchall()

    total = len(rows)
    missing = 0
    empty = 0
    repaired = 0
    issues: List[Tuple[int, str, str]] = []  # (rowid, song_name, issue_type)

    if verbose and total > 0:
        print(f"[StatsVerifier] Checking {total} {base_table} entries...")

    for i, row in enumerate(rows):
        if verbose and total > 1000 and i > 0 and i % 10000 == 0:
            print(f"[StatsVerifier] loadouts progress: {i}/{total}...")

        details = json.loads(row["details_json"]) if row["details_json"] else {}
        stats = details.get("Stats")

        # Check for missing or empty Stats
        issue_type = None
        if stats is None:
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
            issues.append((row["rowid"], row["song_name"], issue_type))

            if not dry_run:
                gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
                mini_names_raw = json.loads(row["minis_json"]) if row["minis_json"] else []

                mini_names = []
                for item in mini_names_raw:
                    if isinstance(item, list) and item:
                        mini_names.append(item[0])
                    elif isinstance(item, str):
                        mini_names.append(item)

                if has_team_buff:
                    details = _ensure_stats_in_details(
                        details,
                        gear_names,
                        mini_names,
                        minis_by_name,
                        team_buff=row["team_buff"] if isinstance(row, sqlite3.Row) else None,
                        team_color=str(details.get("PrimaryColor") or details.get("Primary Color") or "").strip(),
                    )
                else:
                    gem_counts = dict(details.get("GemCounts", {}) or {})
                    gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
                    gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
                    selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""

                    computed_stats = compute_full_stats(
                        gear_names,
                        mini_names,
                        gem_counts,
                        selected_element,
                        gears_by_name,
                        minis_by_name,
                        base_stats,
                    )
                    details["Stats"] = computed_stats

                conn.execute(
                    f"UPDATE {base_table} SET details_json = ? WHERE rowid = ?",
                    (json.dumps(details), row["rowid"]),
                )
                repaired += 1

    if not dry_run and repaired > 0:
        conn.commit()
        if verbose:
            print(f"[StatsVerifier] Committed {repaired} repairs to {base_table} table")

    # ============================================================
    # PART 2: Verify and repair `fg_loadouts` table
    # ============================================================
    fg_total, fg_empty, fg_repaired = _verify_fg_table(
        conn, "fg_loadouts", gears_by_name, minis_by_name, base_stats, dry_run, verbose, sample_size
    )

    # ============================================================
    # PART 3: Verify and repair `team_buff_fg_loadouts` table
    # ============================================================
    tb_fg_total, tb_fg_empty, tb_fg_repaired = _verify_fg_table(
        conn, "team_buff_fg_loadouts", gears_by_name, minis_by_name, base_stats, dry_run, verbose, sample_size
    )

    conn.close()

    all_valid = missing == 0 and empty == 0 and fg_empty == 0 and tb_fg_empty == 0
    stats_dict = {
        "total": total,
        "missing": missing,
        "empty": empty,
        "repaired": repaired,
        "fg_total": fg_total,
        "fg_empty": fg_empty,
        "fg_repaired": fg_repaired,
        "tb_fg_total": tb_fg_total,
        "tb_fg_empty": tb_fg_empty,
        "tb_fg_repaired": tb_fg_repaired,
    }

    return all_valid, stats_dict


def _verify_fg_table(
    conn: sqlite3.Connection,
    table_name: str,
    gears_by_name: Dict,
    minis_by_name: Dict,
    base_stats: Dict,
    dry_run: bool,
    verbose: bool,
    sample_size: int,
) -> Tuple[int, int, int]:
    """
    Verify and repair an FG table (fg_loadouts or team_buff_fg_loadouts).

    For FG tables, we can get Stats from BaseStats in force_details_json.
    If not available, we recompute from gear/minis/gems.

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

    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    has_team_buff = "team_buff" in cols
    select_cols = ["rowid", "song_name", "gear_json", "minis_json", "details_json", "force_details_json"]
    if has_team_buff:
        select_cols.append("team_buff")

    query = f"SELECT {', '.join(select_cols)} FROM {table_name}"
    if sample_size > 0:
        query += f" LIMIT {int(sample_size)}"

    rows = conn.execute(query).fetchall()
    total = len(rows)
    empty_count = 0
    repaired_count = 0

    if verbose and total > 0:
        print(f"[StatsVerifier] Checking {total} {table_name} entries...")

    for i, row in enumerate(rows):
        if verbose and total > 1000 and i > 0 and i % 10000 == 0:
            print(f"[StatsVerifier] {table_name} progress: {i}/{total}...")

        details = json.loads(row["details_json"]) if row["details_json"] else {}
        stats = details.get("Stats")

        if _is_stats_empty(stats):
            empty_count += 1

            if not dry_run:
                # Try to get Stats from force_details_json BaseStats
                force_details = json.loads(row["force_details_json"]) if row["force_details_json"] else {}
                base_stats_from_force = force_details.get("BaseStats")

                if base_stats_from_force and isinstance(base_stats_from_force, dict) and base_stats_from_force:
                    # Use BaseStats from force_details_json
                    details["Stats"] = base_stats_from_force
                else:
                    # Recompute from gear/minis/gems
                    gear_names = json.loads(row["gear_json"]) if row["gear_json"] else []
                    mini_names_raw = json.loads(row["minis_json"]) if row["minis_json"] else []

                    mini_names = []
                    for item in mini_names_raw:
                        if isinstance(item, list) and item:
                            mini_names.append(item[0])
                        elif isinstance(item, str):
                            mini_names.append(item)

                    if has_team_buff:
                        details = _ensure_stats_in_details(
                            details,
                            gear_names,
                            mini_names,
                            minis_by_name,
                            team_buff=row["team_buff"] if isinstance(row, sqlite3.Row) else None,
                            team_color=str(details.get("PrimaryColor") or details.get("Primary Color") or "").strip(),
                        )
                    else:
                        gem_counts = dict(details.get("GemCounts", {}) or {})
                        gem_counts["Fever Time"] = int(details.get("FT", 0) or 0)
                        gem_counts["Fever Fill Rate"] = int(details.get("FF", 0) or 0)
                        selected_element = details.get("SelectedElement") or details.get("Selected Element") or ""

                        computed_stats = compute_full_stats(
                            gear_names,
                            mini_names,
                            gem_counts,
                            selected_element,
                            gears_by_name,
                            minis_by_name,
                            base_stats,
                        )
                        details["Stats"] = computed_stats

                conn.execute(
                    f"UPDATE {table_name} SET details_json = ? WHERE rowid = ?", (json.dumps(details), row["rowid"])
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
    total = stats_dict.get("total", 0)
    fg_empty = stats_dict.get("fg_empty", 0)
    fg_total = stats_dict.get("fg_total", 0)
    tb_fg_empty = stats_dict.get("tb_fg_empty", 0)
    tb_fg_total = stats_dict.get("tb_fg_total", 0)

    total_issues = missing + empty + fg_empty + tb_fg_empty

    if total_issues > 0:
        print("\n" + "=" * 80)
        print("+" + "=" * 78 + "+")
        print("|" + " " * 78 + "|")
        print("|" + "   WARNING: DATABASE STATS INTEGRITY ISSUE".center(78) + "|")
        print("|" + " " * 78 + "|")
        print("+" + "=" * 78 + "+")
        print(f"  Found {total_issues:,} entries with invalid Stats:")
        if missing > 0:
            print(f"    - loadouts: {missing:,} entries have MISSING Stats (None)")
        if empty > 0:
            print(f"    - loadouts: {empty:,} entries have EMPTY Stats ({{}})")
        if fg_empty > 0:
            print(f"    - fg_loadouts: {fg_empty:,} / {fg_total:,} entries have EMPTY Stats")
        if tb_fg_empty > 0:
            print(f"    - team_buff_fg_loadouts: {tb_fg_empty:,} / {tb_fg_total:,} entries have EMPTY Stats")
        print()
        print("  This means elemental stats (Chill/Flow/Rush/Beat/Vibe) will show as 0")
        print("  in the frontend/extractor, causing incorrect score calculations!")
        print()
        print("  SOLUTION: Run tools/db/backfill_stats.py to repair the database:")
        print("    python tools/db/backfill_stats.py")
        print("=" * 80 + "\n")
