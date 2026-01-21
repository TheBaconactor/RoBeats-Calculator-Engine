#!/usr/bin/env python3
"""
Inventory Meta Coverage - Benchmark Worker (subprocess-safe).

Reads a JSON object from stdin:
  {
    "db_path": "/path/to/evolution.db",
    "kwargs": { ... run_inventory_meta_coverage kwargs ... },
    "label": "optional label"
  }

Writes a single JSON object to stdout. Other logs may appear before it.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Dict


def _extract_json_object_from_stdout(stdout: str) -> Dict[str, Any] | None:
    raw = (stdout or "").strip()
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass
    for idx in range(len(raw) - 1, -1, -1):
        if raw[idx] != "{":
            continue
        try:
            parsed = json.loads(raw[idx:])
        except Exception:
            continue
        if isinstance(parsed, dict) and ("ok" in parsed):
            return parsed
    return None


def _main() -> int:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw else {}
        if not isinstance(payload, dict):
            raise ValueError("Expected JSON object payload on stdin.")

        db_path = str(payload.get("db_path") or "").strip()
        if db_path:
            os.environ["EVOLUTION_DB_PATH"] = db_path

        repo_root = Path(__file__).resolve().parents[2]
        repo_str = str(repo_root)
        if repo_str not in sys.path:
            sys.path.insert(0, repo_str)

        from inventory_optimizer import run_inventory_meta_coverage

        kwargs = payload.get("kwargs") or {}
        if not isinstance(kwargs, dict):
            raise ValueError("payload.kwargs must be an object")

        t0 = time.perf_counter()
        result = run_inventory_meta_coverage(**kwargs)
        elapsed = time.perf_counter() - t0

        stats = result.get("stats", {}) if isinstance(result, dict) else {}
        inventory = result.get("inventory", {}) if isinstance(result, dict) else {}
        variants = inventory.get("gear_variants", []) if isinstance(inventory, dict) else []
        unique_gears = (
            len({str(v.get("gear_name") or "") for v in variants if isinstance(v, dict) and v.get("gear_name")})
            if isinstance(variants, list)
            else 0
        )

        out = {
            "ok": True,
            "label": str(payload.get("label") or ""),
            "time_sec": float(round(elapsed, 6)),
            "seed": int(kwargs.get("seed") or 0),
            "solver": str(kwargs.get("solver") or ""),
            "stats": {
                "songs_total": int(stats.get("songs_total") or 0) if isinstance(stats, dict) else 0,
                "songs_covered": int(stats.get("songs_covered") or 0) if isinstance(stats, dict) else 0,
                "gear_variants_used": int(stats.get("gear_variants_used") or 0) if isinstance(stats, dict) else 0,
                "gear_variants_cap": int(stats.get("gear_variants_cap") or 0) if isinstance(stats, dict) else 0,
                "unique_gears_used": int(unique_gears),
            },
        }
        sys.stdout.write(json.dumps(out))
        return 0
    except BaseException as exc:
        sys.stdout.write(
            json.dumps(
                {
                    "ok": False,
                    "error": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(_main())
