from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.data.database import get_db_connection
from inventory_optimizer.db import fetch_peak_candidates_allow_missing


def _normalize_key(name: str, offset: int) -> Tuple[str, int]:
    return (str(name or "").strip().lower(), int(offset))


def _song_best_elements(db_path: Path) -> Dict[str, str]:
    os.environ["EVOLUTION_DB_PATH"] = str(db_path)
    conn = get_db_connection(str(db_path))
    try:
        cands_by_song, _ = fetch_peak_candidates_allow_missing(conn)
    finally:
        conn.close()

    out: Dict[str, str] = {}
    for song, cands in cands_by_song.items():
        best = None
        best_key = None
        for c in cands:
            key = (max(int(c.score), int(c.fg_score)), int(c.fg_score), int(c.score), int(c.rowid))
            if best_key is None or key > best_key:
                best_key = key
                best = c
        if best is not None:
            out[str(song)] = str(best.selected_element)
    return out


def _load_universe(path: Path) -> Dict[Tuple[str, int], Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    variants = payload.get("variants") if isinstance(payload, dict) else None
    if not isinstance(variants, list):
        raise SystemExit(f"Invalid universe JSON: {path}")
    out: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for v in variants:
        if not isinstance(v, dict):
            continue
        name = v.get("gear_name")
        off = v.get("offset")
        if name is None or off is None:
            continue
        try:
            out[_normalize_key(str(name), int(off))] = v
        except Exception:
            continue
    return out


def _seed_distribution(seed_path: Path, universe: Dict[Tuple[str, int], Dict[str, Any]]) -> Dict[str, Any]:
    payload = json.loads(seed_path.read_text(encoding="utf-8"))
    items = payload.get("variants") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        raise SystemExit(f"Invalid seed JSON: {seed_path}")

    by_bucket = Counter()
    missing = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("gear_name")
        off = item.get("offset")
        if name is None or off is None:
            continue
        key = _normalize_key(str(name), int(off))
        info = universe.get(key)
        if not info:
            missing += 1
            continue
        gems = info.get("gems") if isinstance(info, dict) else None
        gems = gems if isinstance(gems, dict) else {}
        ov = int(gems.get("OV") or 0)
        bucket = str(info.get("ov_color_name")) if ov > 0 and info.get("ov_color_name") else "ANY"
        by_bucket[bucket] += 1

    return {
        "seed_path": str(seed_path),
        "seed_variants": int(len(items)),
        "missing_in_universe": int(missing),
        "bucket_counts": dict(sorted(by_bucket.items(), key=lambda kv: (-kv[1], kv[0]))),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Analyze an inventory_meta_coverage_main.py result JSON.")
    ap.add_argument("--result", type=str, required=True, help="Result JSON path.")
    ap.add_argument("--db-path", type=str, default="", help="Optional DB snapshot path for best-peak element stats.")
    ap.add_argument("--universe", type=str, default="", help="Optional universe JSON for seed distribution.")
    ap.add_argument(
        "--seed",
        type=str,
        default="",
        help="Optional seed variants JSON (gear_name+offset). Defaults to stats.seed_inventory_variants.source_path when present.",
    )
    ap.add_argument("--out", type=str, default="", help="Optional output JSON path.")
    args = ap.parse_args()

    result_path = Path(args.result)
    data = json.loads(result_path.read_text(encoding="utf-8"))
    assignments = data.get("assignments") if isinstance(data, dict) else None
    assignments = assignments if isinstance(assignments, dict) else {}
    uncovered = data.get("uncovered_songs") if isinstance(data, dict) else None
    uncovered = uncovered if isinstance(uncovered, list) else []

    covered_by_selected = Counter()
    for a in assignments.values():
        if not isinstance(a, dict):
            continue
        covered_by_selected[str(a.get("selected_element") or "")] += 1

    out: Dict[str, Any] = {
        "result_path": str(result_path),
        "stats": data.get("stats") if isinstance(data, dict) else {},
        "covered_count": int(len(assignments)),
        "uncovered_count": int(len(uncovered)),
        "covered_by_selected_element": dict(sorted(covered_by_selected.items(), key=lambda kv: (-kv[1], kv[0]))),
    }

    if str(args.db_path or "").strip():
        best_el = _song_best_elements(Path(args.db_path))
        cov_best = Counter()
        unc_best = Counter()
        for song in assignments.keys():
            cov_best[str(best_el.get(str(song)) or "")] += 1
        for song in uncovered:
            unc_best[str(best_el.get(str(song)) or "")] += 1
        out["covered_by_best_peak_element"] = dict(sorted(cov_best.items(), key=lambda kv: (-kv[1], kv[0])))
        out["uncovered_by_best_peak_element"] = dict(sorted(unc_best.items(), key=lambda kv: (-kv[1], kv[0])))

    seed_path = str(args.seed or "").strip()
    if not seed_path and isinstance(out.get("stats"), dict):
        seed_info = out["stats"].get("seed_inventory_variants") if isinstance(out["stats"], dict) else None
        if isinstance(seed_info, dict) and seed_info.get("source_path"):
            seed_path = str(seed_info["source_path"])
    if seed_path and str(args.universe or "").strip():
        universe = _load_universe(Path(args.universe))
        out["seed_distribution"] = _seed_distribution(Path(seed_path), universe)

    out_json = json.dumps(out, indent=2, sort_keys=True)
    if str(args.out or "").strip():
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out_json, encoding="utf-8")
        print(f"Wrote analysis: {out_path}")
    else:
        print(out_json)


if __name__ == "__main__":
    main()

