"""
Benchmark Inventory Meta coverage per element (macOS-safe).

Runs the inventory meta solver once per element (Chill/Flow/Rush/Beat/Vibe) and reports:
- songs_total / songs_covered
- gear_variants_used
- wall-clock time

Notes:
- Uses EVOLUTION_DB_PATH if set; otherwise uses repo default.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List


ELEMENTS = ["Chill", "Flow", "Rush", "Beat", "Vibe"]

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _run_once(*, element: str | None, args: argparse.Namespace, seed: int) -> Dict[str, Any]:
    from inventory_optimizer import run_inventory_meta_coverage

    t0 = time.perf_counter()
    res = run_inventory_meta_coverage(
        inventory_cap=int(args.inventory_cap),
        restarts=int(args.restarts),
        seed=int(seed),
        song_limit=int(args.song_limit) if args.song_limit else None,
        element=element,
        secondary_element=None,
        partitions_per_song=int(args.partitions_per_song),
        adaptive_rounds=int(args.adaptive_rounds),
        adaptive_keep_per_song=int(args.adaptive_keep_per_song),
        gpu_repack_passes=int(args.gpu_repack_passes),
        gpu_lns_destroy=int(args.gpu_lns_destroy),
        lns_time_sec=float(args.lns_time_sec),
        lns_attempts=int(args.lns_attempts),
        profile=bool(args.profile),
    )
    dt = time.perf_counter() - t0

    stats = dict(res.get("stats") or {})
    out: Dict[str, Any] = {
        "element": element or "ALL",
        "mode": res.get("mode"),
        "time_sec": float(dt),
        "songs_total": int(stats.get("songs_total", 0)),
        "songs_covered": int(stats.get("songs_covered", 0)),
        "gear_variants_used": int(stats.get("gear_variants_used", 0)),
        "solver_status": (res.get("solver_stats") or {}).get("status"),
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory-cap", type=int, default=100)
    ap.add_argument("--restarts", type=int, default=1)
    ap.add_argument("--song-limit", type=int, default=0, help="0 = no limit")
    ap.add_argument("--runs", type=int, default=1, help="Runs per element (different seeds)")
    ap.add_argument("--seed", type=int, default=1, help="Base seed")

    ap.add_argument("--partitions-per-song", type=int, default=32)
    ap.add_argument("--adaptive-rounds", type=int, default=0)
    ap.add_argument("--adaptive-keep-per-song", type=int, default=8)

    ap.add_argument("--gpu-repack-passes", type=int, default=3)
    ap.add_argument("--gpu-lns-destroy", type=int, default=6)
    ap.add_argument("--lns-time-sec", type=float, default=0.0)
    ap.add_argument("--lns-attempts", type=int, default=200)
    ap.add_argument("--profile", action="store_true")

    ap.add_argument("--include-all", action="store_true", help="Also run without any element filter")
    ap.add_argument("--output", default="", help="Write JSON results to this path")
    args = ap.parse_args()

    if int(args.runs) <= 0:
        raise SystemExit("--runs must be positive")

    print(
        json.dumps(
            {
                "bench": "inventory_meta_elements",
                "solver": "gpu_full",
                "inventory_cap": int(args.inventory_cap),
                "restarts": int(args.restarts),
                "song_limit": int(args.song_limit),
                "runs_per_element": int(args.runs),
                "db_path": os.environ.get("EVOLUTION_DB_PATH", ""),
            },
            indent=2,
        )
    )

    results: List[Dict[str, Any]] = []
    seeds = [int(args.seed) + i for i in range(int(args.runs))]

    elements_to_run: List[str | None] = []
    if args.include_all:
        elements_to_run.append(None)
    elements_to_run.extend(ELEMENTS)

    for el in elements_to_run:
        for s in seeds:
            row = _run_once(element=el, args=args, seed=s)
            results.append(row)
            print(
                f"{row['element']:>4} seed={s:<4} "
                f"covered={row['songs_covered']}/{row['songs_total']} "
                f"inv={row['gear_variants_used']} "
                f"time={row['time_sec']:.3f}s "
                f"mode={row['mode']} status={row['solver_status']}"
            )

    if args.output:
        out = {"meta": {"elements": ELEMENTS, "args": vars(args)}, "results": results}
        with open(str(args.output), "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"Wrote {len(results)} rows to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
