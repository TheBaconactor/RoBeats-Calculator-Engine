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

    fg_rowids: List[int] = []
    fg_by_rowid: Dict[int, dict] = {}
    for assignment in assignments.values():
        if not isinstance(assignment, dict):
            continue
        if str(assignment.get("source_table") or "") != "fg_loadouts":
            continue
        rowid = assignment.get("candidate_rowid")
        if isinstance(rowid, int) and rowid > 0:
            fg_rowids.append(rowid)
            fg_by_rowid[rowid] = assignment

    if not fg_rowids:
        return

    conn = get_db_connection(db_path)
    try:
        for chunk_start in range(0, len(fg_rowids), 900):
            chunk = fg_rowids[chunk_start : chunk_start + 900]
            placeholders = ",".join("?" for _ in chunk)
            query = f"SELECT rowid AS rowid, force_details_json FROM fg_loadouts WHERE rowid IN ({placeholders})"
            for row in conn.execute(query, chunk):
                rowid = int(row["rowid"] or 0)
                assignment = fg_by_rowid.get(rowid)
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
