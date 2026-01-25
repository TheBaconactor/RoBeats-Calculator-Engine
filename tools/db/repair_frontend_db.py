"""
Repair common DB integrity issues that break frontend/export consumers.

This tool is intended to be safe to run on large, messy datasets where:
  - Tier tables already exist (team_buff_*), but have corrupted minis_json shapes.
  - details_json["Stats"] is missing/empty, causing frontend to show 0 stats.
  - FG tables contain rows where fg_score <= score (should never happen).

It is conservative:
  - It repairs known-corruption patterns and missing Stats.
  - It does not attempt to recompute scores.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.core.stats_calculator import compute_full_stats
from gear_optimizer.data.database import get_evolution_db_path
from gear_optimizer.data.csv_parser import parse_gear_rows, parse_mini_rows
from gear_optimizer.core.config import load_paths_cache


EXPECTED_TEAM_BUFFS = {"NONE", "T1", "T5", "T10", "T15"}
ELEMENT_KEYS = ("Chill", "Flow", "Rush", "Beat", "Vibe")


def _json_loads(s: Any, default: Any) -> Any:
    if s is None:
        return default
    if isinstance(s, (dict, list)):
        return s
    text = str(s).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def _stats_missing_or_empty(stats: Any) -> bool:
    if stats is None:
        return True
    if isinstance(stats, dict) and not stats:
        return True
    if isinstance(stats, dict):
        # Treat "all zeros" as empty.
        if not any(float(v or 0) != 0.0 for v in stats.values() if isinstance(v, (int, float))):
            # If there are non-numeric values this could be a false positive; handle that below.
            any_nonzero = False
            for v in stats.values():
                try:
                    if float(v or 0) != 0.0:
                        any_nonzero = True
                        break
                except Exception:
                    continue
            return not any_nonzero
    return False


def _repair_minis_node(node: Any) -> tuple[Any, int]:
    """
    Repair minis_json corruption where a string contains a python-list literal like:
      \"['Electroman']\"
    Returns: (new_node, repair_count)
    """
    if isinstance(node, str):
        text = node.strip()
        if text.startswith("[") and text.endswith("]") and "['" in text:
            try:
                val = ast.literal_eval(text)
            except Exception:
                return node, 0
            if isinstance(val, list) and all(isinstance(x, str) for x in val):
                return val, 1
        return node, 0

    if isinstance(node, list):
        repaired = 0
        out: list[Any] = []
        for item in node:
            new_item, r = _repair_minis_node(item)
            repaired += r
            out.append(new_item)
        return out, repaired

    return node, 0


def _representative_mini_names(minis_json_obj: Any) -> list[str]:
    """
    Normalize minis_json into a list[str] for Stats recompute.
    - Supports legacy flat list[str]
    - Supports grouped list[list[str]] (variant groups)
    """
    minis: list[str] = []
    if isinstance(minis_json_obj, list):
        for item in minis_json_obj:
            if isinstance(item, list) and item:
                if isinstance(item[0], str):
                    minis.append(item[0])
            elif isinstance(item, str):
                minis.append(item)
    return minis


def _extract_base_stats_from_force(force: Any) -> dict[str, Any] | None:
    if not isinstance(force, dict) or not force:
        return None
    if isinstance(force.get("BaseStats"), dict) and force["BaseStats"]:
        return force["BaseStats"]
    if (
        isinstance(force.get("details"), dict)
        and isinstance(force["details"].get("BaseStats"), dict)
        and force["details"]["BaseStats"]
    ):
        return force["details"]["BaseStats"]
    # Some legacy shapes embed under ForceGreats.
    if isinstance(force.get("ForceGreats"), dict) and isinstance(force["ForceGreats"].get("BaseStats"), dict):
        if force["ForceGreats"]["BaseStats"]:
            return force["ForceGreats"]["BaseStats"]
    return None


@dataclass
class RepairStats:
    scanned_rows: int = 0
    minis_fixed: int = 0
    stats_fixed: int = 0
    fg_invariant_deleted: int = 0
    team_buff_fixed_case: int = 0
    team_buff_unexpected: int = 0


def repair_frontend_db(
    *,
    db_path: Path,
    dry_run: bool,
    verbose: bool,
) -> RepairStats:
    # Allow downstream helpers that read get_evolution_db_path() to use this DB.
    os.environ["EVOLUTION_DB_PATH"] = str(db_path)

    paths = load_paths_cache()
    gears_list = parse_gear_rows(paths.get("Gears", ""))
    minis_list = parse_mini_rows(paths.get("Minis", ""))
    gears_by_name = {g["Name"]: g for g in gears_list}
    minis_by_name = {m["Name"]: m for m in minis_list}

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

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    stats = RepairStats()

    def table_exists(name: str) -> bool:
        return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None

    # 1) Normalize team_buff casing for tables that have it.
    for tbl in ("fg_loadouts", "team_buff_loadouts", "team_buff_fg_loadouts"):
        if not table_exists(tbl):
            continue
        # Skip if column missing.
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
        if "team_buff" not in cols:
            continue

        before = conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE team_buff != UPPER(TRIM(team_buff))").fetchone()[0]
        if before:
            stats.team_buff_fixed_case += int(before)
            if not dry_run:
                conn.execute(f"UPDATE {tbl} SET team_buff = UPPER(TRIM(team_buff))")

        # Map common bad values to NONE.
        if not dry_run:
            conn.execute(
                f"""
                UPDATE {tbl}
                SET team_buff = 'NONE'
                WHERE team_buff IN ('0', 'NO_BUFF', 'NO BUFF', 'NONEBUFF', 'NONE BUFF')
                """
            )

        unexpected = conn.execute(
            f"""
            SELECT COUNT(*) FROM {tbl}
            WHERE team_buff IS NOT NULL
              AND team_buff != ''
              AND UPPER(team_buff) NOT IN ('NONE','T1','T5','T10','T15')
            """
        ).fetchone()[0]
        stats.team_buff_unexpected += int(unexpected)

    # 2) Enforce FG invariant (delete rows where fg_score <= score).
    for tbl in ("fg_loadouts", "team_buff_fg_loadouts"):
        if not table_exists(tbl):
            continue
        deleted = conn.execute(f"SELECT COUNT(*) FROM {tbl} WHERE fg_score <= score").fetchone()[0]
        stats.fg_invariant_deleted += int(deleted)
        if deleted and not dry_run:
            conn.execute(f"DELETE FROM {tbl} WHERE fg_score <= score")

    # 3) Repair minis_json corruption + missing Stats.
    tables = ("loadouts", "fg_loadouts", "team_buff_loadouts", "team_buff_fg_loadouts")
    for tbl in tables:
        if not table_exists(tbl):
            continue

        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({tbl})").fetchall()}
        if not {"gear_json", "minis_json", "details_json"}.issubset(cols):
            continue
        has_force = "force_details_json" in cols

        if verbose:
            print(f"[Repair] Scanning table: {tbl}")

        cur = conn.execute(
            f"SELECT rowid, gear_json, minis_json, details_json{', force_details_json' if has_force else ''} FROM {tbl}"
        )
        for row in cur:
            stats.scanned_rows += 1

            minis_obj = _json_loads(row["minis_json"], [])
            minis_fixed_obj, minis_repairs = _repair_minis_node(minis_obj)
            if minis_repairs:
                stats.minis_fixed += minis_repairs

            details = _json_loads(row["details_json"], {})
            if not isinstance(details, dict):
                details = {}

            force = _json_loads(row["force_details_json"], {}) if has_force else {}

            stats_needs_repair = _stats_missing_or_empty(details.get("Stats"))
            if stats_needs_repair:
                base_stats_from_force = _extract_base_stats_from_force(force)
                if base_stats_from_force is not None:
                    details["Stats"] = base_stats_from_force
                    stats.stats_fixed += 1
                else:
                    gear_names = _json_loads(row["gear_json"], [])
                    mini_names = _representative_mini_names(minis_fixed_obj)

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
                    stats.stats_fixed += 1

            if minis_repairs or stats_needs_repair:
                if not dry_run:
                    conn.execute(
                        f"UPDATE {tbl} SET minis_json = ?, details_json = ? WHERE rowid = ?",
                        (json.dumps(minis_fixed_obj), json.dumps(details), row["rowid"]),
                    )

    if not dry_run:
        conn.commit()
    conn.close()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair common frontend-breaking DB integrity issues.")
    parser.add_argument(
        "--db",
        type=str,
        default="",
        help="DB path (defaults to EVOLUTION_DB_PATH / ./evolution.db).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Scan and report, but do not write changes.")
    parser.add_argument("--verbose", action="store_true", help="Print per-table progress.")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser() if args.db else Path(get_evolution_db_path())
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    result = repair_frontend_db(db_path=db_path, dry_run=bool(args.dry_run), verbose=bool(args.verbose))
    print("\n" + "=" * 60)
    print("REPAIR SUMMARY" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 60)
    print(f"DB: {db_path}")
    print(f"scanned_rows: {result.scanned_rows:,}")
    print(f"minis_fixed: {result.minis_fixed:,}")
    print(f"stats_fixed: {result.stats_fixed:,}")
    print(f"fg_invariant_rows_deleted: {result.fg_invariant_deleted:,}")
    print(f"team_buff_case_fixed_rows: {result.team_buff_fixed_case:,}")
    if result.team_buff_unexpected:
        print(f"WARNING: unexpected team_buff rows remain: {result.team_buff_unexpected:,}")
        print(f"expected: {sorted(EXPECTED_TEAM_BUFFS)}")


if __name__ == "__main__":
    main()
