"""
Report "human optionality" metrics for Inventory Meta coverage.

This runs Inventory Meta coverage (default: gpu_full) and prints a compact summary of:
- unique gear IDs vs unique variants (concentration / over-investment)
- wildcard (OV==0) share
- for uncovered songs: how many are "gear-feasible" (blocked by offsets vs missing gear IDs)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _summarize(res: Dict[str, Any]) -> Dict[str, Any]:
    stats = dict(res.get("stats") or {})
    opt = stats.get("optionality") if isinstance(stats.get("optionality"), dict) else {}
    inv = opt.get("inventory") if isinstance(opt.get("inventory"), dict) else {}
    cov = opt.get("coverage") if isinstance(opt.get("coverage"), dict) else {}

    top = inv.get("top_gears_by_variant_count")
    if not isinstance(top, list):
        top = []

    return {
        "songs_total": int(stats.get("songs_total", 0)),
        "songs_covered": int(stats.get("songs_covered", 0)),
        "gear_variants_used": int(stats.get("gear_variants_used", 0)),
        "inventory": {
            "unique_variants": inv.get("unique_variants"),
            "unique_gear_ids": inv.get("unique_gear_ids"),
            "avg_variants_per_gear": inv.get("avg_variants_per_gear"),
            "wildcard_share": inv.get("wildcard_share"),
            "top_gears_by_variant_count": top[:10],
        },
        "uncovered": {
            "songs_uncovered": cov.get("songs_uncovered"),
            "uncovered_gear_feasible_share": cov.get("uncovered_gear_feasible_share"),
            "uncovered_gear_feasible": cov.get("uncovered_gear_feasible"),
            "uncovered_blocked_by_missing_gear": cov.get("uncovered_blocked_by_missing_gear"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory-cap", type=int, default=100)
    ap.add_argument("--restarts", type=int, default=1)
    ap.add_argument("--song-limit", type=int, default=200, help="0 = no limit")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--element", default="", help="Chill/Flow/Rush/Beat/Vibe or empty")
    ap.add_argument("--secondary-element", default="", help="optional second element")

    ap.add_argument("--partitions-per-song", type=int, default=32)
    ap.add_argument("--gpu-repack-passes", type=int, default=3)
    ap.add_argument("--lns-time-sec", type=float, default=0.0)
    ap.add_argument("--lns-attempts", type=int, default=200)
    ap.add_argument("--gpu-lns-destroy", type=int, default=6)

    ap.add_argument("--gpu-full-top-candidates", type=int, default=1)
    ap.add_argument("--gpu-full-wildcard-freq-bonus", type=int, default=0)
    ap.add_argument("--gpu-full-repair-enabled", action="store_true")

    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--output", default="", help="Write full JSON result to this path")
    args = ap.parse_args()

    from inventory_optimizer import run_inventory_meta_coverage

    song_limit = None if int(args.song_limit) == 0 else int(args.song_limit)
    element = str(args.element).strip() or None
    secondary_element = str(args.secondary_element).strip() or None

    t0 = time.perf_counter()
    res = run_inventory_meta_coverage(
        solver="gpu_full",
        inventory_cap=int(args.inventory_cap),
        restarts=int(args.restarts),
        seed=int(args.seed),
        song_limit=song_limit,
        element=element,
        secondary_element=secondary_element,
        partitions_per_song=int(args.partitions_per_song),
        gpu_repack_passes=int(args.gpu_repack_passes),
        lns_time_sec=float(args.lns_time_sec),
        lns_attempts=int(args.lns_attempts),
        gpu_lns_destroy=int(args.gpu_lns_destroy),
        gpu_full_top_candidates=int(args.gpu_full_top_candidates),
        gpu_full_wildcard_freq_bonus=int(args.gpu_full_wildcard_freq_bonus),
        gpu_full_repair_enabled=bool(args.gpu_full_repair_enabled),
        profile=bool(args.profile),
    )
    dt = time.perf_counter() - t0

    print(json.dumps({"time_sec": round(float(dt), 3), "summary": _summarize(res)}, indent=2))

    if args.output:
        Path(args.output).write_text(json.dumps(res, indent=2), encoding="utf-8")
        print(f"Wrote full result JSON to {args.output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

