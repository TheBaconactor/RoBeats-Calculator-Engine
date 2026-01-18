#!/usr/bin/env python3
"""
InventoryMeta Coverage - Main Entry Point

Goal: maximize the number of songs whose exact peak can be reproduced
using an inventory of <=100 gear variants (GPU heuristic; no proof).
"""

import argparse
import multiprocessing
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.data.database import init_db
from inventory_optimizer import export_inventory_meta_json, run_inventory_meta_coverage


def main() -> None:
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(
        prog="inventory_meta_coverage_main.py", description="Inventory Meta coverage solver."
    )
    parser.add_argument("--db-path", type=str, default="", help="Override SQLite path (sets EVOLUTION_DB_PATH).")
    parser.add_argument("--inventory-cap", type=int, default=100, help="Max number of gear variants (default: 100).")
    parser.add_argument(
        "--solver",
        type=str,
        default="gpu_dynamic",
        choices=["gpu_dynamic", "gpu_eda", "gpu_full"],
        help="Coverage solver backend (default: gpu_dynamic).",
    )
    parser.add_argument(
        "--partitions-per-song", type=int, default=32, help="Legacy (ignored): patterns per song (default: 32)."
    )
    parser.add_argument("--seed", type=int, default=1, help="RNG seed (default: 1).")
    parser.add_argument("--restarts", type=int, default=1, help="Run multiple seeds and keep best (default: 1).")
    parser.add_argument(
        "--gpu-repack-passes", type=int, default=3, help="GPU repack passes per stabilize step (default: 3)."
    )
    parser.add_argument(
        "--gpu-lns-destroy", type=int, default=6, help="GPU LNS destroy count per attempt (default: 6)."
    )
    parser.add_argument(
        "--adaptive-rounds", type=int, default=3, help="Legacy (ignored): adaptive rounds (default: 3)."
    )
    parser.add_argument(
        "--adaptive-patterns-per-round",
        type=int,
        default=64,
        help="Legacy (ignored): new patterns per adaptive round (default: 64).",
    )
    parser.add_argument(
        "--adaptive-keep-per-song",
        type=int,
        default=8,
        help="Legacy (ignored): partitions to keep per song per round (default: 8).",
    )
    parser.add_argument(
        "--adaptive-repack-songs",
        type=int,
        default=256,
        help="Legacy (ignored): repack songs count (default: 256).",
    )
    parser.add_argument(
        "--lns-time-sec",
        type=float,
        default=0.0,
        help="Large-neighborhood search time budget in seconds (default: 0=off).",
    )
    parser.add_argument(
        "--lns-attempts",
        type=int,
        default=200,
        help="Max LNS attempts (default: 200).",
    )
    parser.add_argument("--song-limit", type=int, default=0, help="Limit number of songs processed (debug only).")
    parser.add_argument("--profile", action="store_true", help="Print memory logs during phases.")
    parser.add_argument("--eda-witnesses-per-song", type=int, default=16, help="EDA: witnesses per song (default: 16).")
    parser.add_argument("--eda-population", type=int, default=64, help="EDA: population size (default: 64).")
    parser.add_argument("--eda-iterations", type=int, default=20, help="EDA: iterations (default: 20).")
    parser.add_argument("--eda-elites", type=int, default=8, help="EDA: elite count (default: 8).")
    parser.add_argument("--eda-alpha", type=float, default=0.25, help="EDA: update rate alpha (default: 0.25).")
    parser.add_argument(
        "--eda-wildcard-bonus",
        type=float,
        default=0.03,
        help="EDA: per-update bonus for OV==0 offsets (default: 0.03).",
    )
    parser.add_argument(
        "--output", type=str, default="", help="Output JSON path (default: artifacts/inventory_meta_coverage.json)."
    )
    args = parser.parse_args()

    if args.db_path:
        os.environ["EVOLUTION_DB_PATH"] = args.db_path

    print("=" * 60)
    print("INVENTORY META COVERAGE - GPU Heuristic")
    print("=" * 60)
    print()

    try:
        init_db()
        results = run_inventory_meta_coverage(
            inventory_cap=args.inventory_cap,
            partitions_per_song=args.partitions_per_song,
            seed=args.seed,
            restarts=args.restarts,
            gpu_repack_passes=args.gpu_repack_passes,
            gpu_lns_destroy=args.gpu_lns_destroy,
            adaptive_rounds=args.adaptive_rounds,
            adaptive_patterns_per_round=args.adaptive_patterns_per_round,
            adaptive_keep_per_song=args.adaptive_keep_per_song,
            adaptive_repack_songs=args.adaptive_repack_songs,
            lns_time_sec=args.lns_time_sec,
            lns_attempts=args.lns_attempts,
            song_limit=args.song_limit or None,
            profile=args.profile,
            solver=args.solver,
            eda_witnesses_per_song=args.eda_witnesses_per_song,
            eda_population=args.eda_population,
            eda_iterations=args.eda_iterations,
            eda_elites=args.eda_elites,
            eda_alpha=args.eda_alpha,
            eda_wildcard_bonus=args.eda_wildcard_bonus,
        )
        out = args.output or str(REPO_ROOT / "artifacts" / "inventory_meta_coverage.json")
        output_path = export_inventory_meta_json(results, out)

        print("\n" + "=" * 60)
        print("INVENTORY META COVERAGE COMPLETE")
        print("=" * 60)
        print(f"\nResults exported to: {output_path}")
        stats = results.get("stats", {})
        print(f"Songs total: {stats.get('songs_total', 0)}")
        print(f"Songs covered: {stats.get('songs_covered', 0)}")
        print(f"Gear variants used: {stats.get('gear_variants_used', 0)} / {stats.get('gear_variants_cap', 0)}")
        print(f"Minis used: {len(results.get('inventory', {}).get('minis', []))}")

    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(0)
    except Exception as exc:
        print(f"\nFatal Error: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
