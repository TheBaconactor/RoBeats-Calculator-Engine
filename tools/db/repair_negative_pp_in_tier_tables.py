"""
Repair negative Perfect Points in tier tables (team_buff_loadouts/team_buff_fg_loadouts).

Why this exists:
- Tier recomputation is expressed as a delta vs the runtime "base" TeamBuff (auto mode => T5).
- Some historical DB repairs/backfills populated details_json["Stats"] as *loadout-only* (no TeamBuff).
- When those rows were later tier-postprocessed, the delta could make PP go negative (e.g. NONE: -25).

This script fixes the *display-breaking* symptom by adding the missing base TeamBuff effect (T5)
back into the stored Stats/BaseStats payloads for rows where PP is negative.

Notes:
- This does NOT recompute scores; it only repairs JSON payloads so the frontend doesn't show
  negative PP and so Stats more closely match the intended tier context.
- For full correctness across all rows (even those that didn't go negative), re-run tier recomputation
  via backfill / postprocess.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gear_optimizer.core.utils import safe_int as _safe_int

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.data.database import get_evolution_db_path


BASE_PP_ADD = 25  # base TeamBuff=T5
BASE_ELEM_ADD = 30  # base TeamBuff=T5
ELEMENT_KEYS = {"Chill", "Flow", "Rush", "Beat", "Vibe"}


def _loads_json(s: Any, default: Any) -> Any:
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

def _apply_base_effect_to_stats(stats: dict, *, primary_color: str) -> dict:
    if not isinstance(stats, dict) or not stats:
        return stats if isinstance(stats, dict) else {}
    out = dict(stats)
    out["Perfect Points"] = _safe_int(out.get("Perfect Points"), 0) + int(BASE_PP_ADD)
    pc = str(primary_color or "").strip()
    if pc in ELEMENT_KEYS:
        out[pc] = _safe_int(out.get(pc), 0) + int(BASE_ELEM_ADD)
    return out


@dataclass
class FixCounts:
    scanned: int = 0
    fixed_details_stats: int = 0
    fixed_force_basestats: int = 0
    fixed_force_details_stats: int = 0


def repair_negative_pp(*, db_path: Path, dry_run: bool) -> FixCounts:
    # Ensure any helpers that rely on EVOLUTION_DB_PATH use this DB.
    os.environ["EVOLUTION_DB_PATH"] = str(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    counts = FixCounts()

    for table in ("team_buff_loadouts", "team_buff_fg_loadouts"):
        exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
        if not exists:
            continue

        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if not {"details_json", "force_details_json"}.issubset(cols):
            continue

        cur = conn.execute(f"SELECT rowid, details_json, force_details_json FROM {table}")
        for r in cur:
            counts.scanned += 1

            details = _loads_json(r["details_json"], {})
            if not isinstance(details, dict):
                continue

            primary = details.get("PrimaryColor") or details.get("Primary Color") or ""
            stats = details.get("Stats")
            if not isinstance(stats, dict) or not stats:
                continue

            pp = _safe_int(stats.get("Perfect Points"), 0)
            if pp >= 0:
                continue

            details_out = dict(details)
            details_out["Stats"] = _apply_base_effect_to_stats(stats, primary_color=str(primary))
            counts.fixed_details_stats += 1

            force = _loads_json(r["force_details_json"], {})
            force_out = force
            if isinstance(force, dict) and force:
                force_out = dict(force)
                bs = force_out.get("BaseStats")
                if isinstance(bs, dict) and bs:
                    if _safe_int(bs.get("Perfect Points"), 0) < 0:
                        force_out["BaseStats"] = _apply_base_effect_to_stats(bs, primary_color=str(primary))
                        counts.fixed_force_basestats += 1
                det = force_out.get("details")
                if isinstance(det, dict):
                    st2 = det.get("Stats")
                    if isinstance(st2, dict) and st2:
                        if _safe_int(st2.get("Perfect Points"), 0) < 0:
                            det_out = dict(det)
                            det_out["Stats"] = _apply_base_effect_to_stats(st2, primary_color=str(primary))
                            force_out["details"] = det_out
                            counts.fixed_force_details_stats += 1

            if not dry_run:
                conn.execute(
                    f"UPDATE {table} SET details_json = ?, force_details_json = ? WHERE rowid = ?",
                    (
                        json.dumps(details_out),
                        json.dumps(force_out) if isinstance(force_out, dict) else r["force_details_json"],
                        r["rowid"],
                    ),
                )

    if not dry_run:
        conn.commit()
    conn.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Repair negative PP in tier tables (frontend display fix).")
    parser.add_argument("--db", type=str, default="", help="DB path (defaults to EVOLUTION_DB_PATH / ./evolution.db).")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report only; do not write changes.")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser() if args.db else Path(get_evolution_db_path())
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    counts = repair_negative_pp(db_path=db_path, dry_run=bool(args.dry_run))
    print("\n" + "=" * 60)
    print("NEGATIVE PP REPAIR" + (" (DRY RUN)" if args.dry_run else ""))
    print("=" * 60)
    print(f"DB: {db_path}")
    print(f"scanned: {counts.scanned:,}")
    print(f"fixed_details_stats: {counts.fixed_details_stats:,}")
    print(f"fixed_force_basestats: {counts.fixed_force_basestats:,}")
    print(f"fixed_force_details_stats: {counts.fixed_force_details_stats:,}")


if __name__ == "__main__":
    main()
