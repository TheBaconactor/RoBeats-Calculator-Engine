from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from gear_optimizer.core.constants import PATHS
from gear_optimizer.data.database import get_db_connection


def export_inventory_meta_json(results: dict, output_path: Optional[str] = None) -> str:
    if output_path is None:
        output_path = os.path.join(PATHS.script_dir, "artifacts", "inventory_meta_coverage.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return output_path


def hydrate_force_details(solution: dict, *, db_path: str) -> None:
    assignments = solution.get("assignments")
    if not isinstance(assignments, dict):
        return

    fg_rowids_by_table: Dict[str, List[int]] = {}
    fg_by_key: Dict[tuple[str, int], dict] = {}
    for assignment in assignments.values():
        if not isinstance(assignment, dict):
            continue
        table = str(assignment.get("source_table") or "")
        if table not in {"fg_loadouts", "team_buff_fg_loadouts"}:
            continue
        rowid = assignment.get("candidate_rowid")
        if isinstance(rowid, int) and rowid > 0:
            fg_rowids_by_table.setdefault(table, []).append(rowid)
            fg_by_key[(table, rowid)] = assignment

    if not fg_rowids_by_table:
        return

    conn = get_db_connection(db_path)
    try:
        for table, rowids in fg_rowids_by_table.items():
            for chunk_start in range(0, len(rowids), 900):
                chunk = rowids[chunk_start : chunk_start + 900]
                placeholders = ",".join("?" for _ in chunk)
                query = f"SELECT rowid AS rowid, force_details_json FROM {table} WHERE rowid IN ({placeholders})"
                for row in conn.execute(query, chunk):
                    rowid = int(row["rowid"] or 0)
                    assignment = fg_by_key.get((table, rowid))
                    if not assignment:
                        continue
                    force_json = row["force_details_json"]
                    if not force_json:
                        assignment["force_details"] = None
                        continue
                    try:
                        parsed = json.loads(force_json)
                    except Exception:
                        parsed = None
                    assignment["force_details"] = parsed if isinstance(parsed, dict) else None
    finally:
        conn.close()


__all__ = ["export_inventory_meta_json", "hydrate_force_details"]
