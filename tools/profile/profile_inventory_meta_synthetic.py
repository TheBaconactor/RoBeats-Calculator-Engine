#!/usr/bin/env python3
"""
Synthetic workload generator for profiling Inventory Meta GPU solvers.

Creates a temporary SQLite DB with N synthetic songs/loadouts, then runs
`run_inventory_meta_coverage()` with the requested solver settings.

This is intended for GPU utilization/throughput profiling when you don't have a
real `evolution.db` with `loadouts` populated on disk.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
import time
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.data.database import get_db_connection, init_db
from inventory_optimizer import run_inventory_meta_coverage


def _base_details(*, selected_element: str, ov: int = 0) -> dict:
    # Inventory meta candidate parsing requires gem totals to sum to TOTAL_GEM_BUDGET (currently 90).
    budget = 90
    pp = 30
    cm = 30
    ov = int(ov)
    fm = max(0, int(budget - (pp + cm + ov)))
    return {
        "FT": 0,
        "FF": 0,
        "GemCounts": {
            "Perfect Points": int(pp),
            "Combo Multiplier": int(cm),
            "Fever Multiplier": int(fm),
            "Element": int(ov),
        },
        "SelectedElement": selected_element,
        "PrimaryColor": selected_element,
        "SecondaryColor": "Flow",
    }


def _insert_loadout(conn, *, song_name: str, score: int, gear_names: list[str], minis_groups: list[list[str]], details: dict) -> None:
    conn.execute(
        """
        INSERT INTO songs (name, best_score, best_fg_score, last_updated)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            best_score = MAX(best_score, excluded.best_score),
            best_fg_score = MAX(best_fg_score, excluded.best_fg_score),
            last_updated = excluded.last_updated
        """,
        (song_name, score, 0, time.time()),
    )
    conn.execute(
        """
        INSERT INTO loadouts (
            song_name, loadout_hash, score, fg_score, gear_json, minis_json, details_json, force_details_json, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            song_name,
            f"{song_name}-{score}",
            score,
            0,
            json.dumps(gear_names),
            json.dumps(minis_groups),
            json.dumps(details),
            None,
            time.time(),
        ),
    )


def main() -> int:
    ap = argparse.ArgumentParser(prog="profile_inventory_meta_synthetic.py")
    ap.add_argument("--songs", type=int, default=1500, help="Number of synthetic songs to insert (default: 1500).")
    ap.add_argument("--inventory-cap", type=int, default=100, help="Inventory cap V (default: 100).")
    ap.add_argument("--solver", type=str, default="gpu_full", choices=["gpu_dynamic", "gpu_eda", "gpu_full"])
    ap.add_argument("--partitions-per-song", type=int, default=32, help="Witness patterns per song (default: 32).")
    ap.add_argument("--seed", type=int, default=1, help="RNG seed for synthesis + solver (default: 1).")
    ap.add_argument("--adaptive-rounds", type=int, default=3, help="GPU full: witness rounds (default: 3).")
    ap.add_argument("--adaptive-keep-per-song", type=int, default=8, help="GPU full: keep patterns per round (default: 8).")
    ap.add_argument("--lns-time-sec", type=float, default=8.0, help="LNS time budget (default: 8.0).")
    ap.add_argument("--lns-attempts", type=int, default=999999, help="Max LNS attempts (default: 999999).")
    ap.add_argument("--gpu-repack-passes", type=int, default=3, help="GPU repack passes (default: 3).")
    ap.add_argument("--gpu-lns-destroy", type=int, default=6, help="GPU LNS destroy count (default: 6).")
    ap.add_argument("--profile", action="store_true", help="Enable solver profiling/logs (default: off).")
    ap.add_argument("--gpu-full-alns", action="store_true", help="Enable GPU full multi-island ALNS (default: off).")
    ap.add_argument("--gpu-full-alns-islands", type=int, default=1, help="ALNS islands count (default: 1).")
    ap.add_argument("--elements", type=str, default="Chill,Rush,Vibe,Beat,Flow", help="Elements list (default: 5).")
    ap.add_argument(
        "--unique-gear",
        type=int,
        default=8000,
        help="Size of unique gear-name pool (default: 8000). Larger => more rugged/harder and more GPU work.",
    )
    ap.add_argument(
        "--ov",
        type=int,
        default=0,
        help="Element OV in details (0 makes variants wildcard-reusable; >0 makes elements matter).",
    )
    args = ap.parse_args()

    rng = random.Random(int(args.seed))
    elements = [e.strip() for e in str(args.elements).split(",") if e.strip()]
    if not elements:
        elements = ["Chill"]

    with tempfile.TemporaryDirectory(prefix="inventory_meta_synth_") as td:
        db_path = os.path.join(td, "evolution.db")
        os.environ["EVOLUTION_DB_PATH"] = db_path
        init_db()

        conn = get_db_connection(db_path)
        try:
            gear_pool = [f"Gear{idx}" for idx in range(int(args.unique_gear))]
            mini_pool = [f"Mini{idx}" for idx in range(256)]

            for s in range(int(args.songs)):
                song_name = f"SynthSong{s:05d}"
                element = rng.choice(elements)
                gear = [rng.choice(gear_pool) for _ in range(6)]
                minis = [[rng.choice(mini_pool)] for _ in range(3)]
                details = _base_details(selected_element=element, ov=int(args.ov))
                _insert_loadout(conn, song_name=song_name, score=100, gear_names=gear, minis_groups=minis, details=details)
            conn.commit()
        finally:
            conn.close()

        t0 = time.perf_counter()
        results = run_inventory_meta_coverage(
            inventory_cap=int(args.inventory_cap),
            partitions_per_song=int(args.partitions_per_song),
            seed=int(args.seed),
            restarts=1,
            gpu_repack_passes=int(args.gpu_repack_passes),
            gpu_lns_destroy=int(args.gpu_lns_destroy),
            adaptive_rounds=int(args.adaptive_rounds),
            adaptive_keep_per_song=int(args.adaptive_keep_per_song),
            lns_time_sec=float(args.lns_time_sec),
            lns_attempts=int(args.lns_attempts),
            profile=bool(args.profile),
            solver=str(args.solver),
            gpu_full_alns_enabled=bool(args.gpu_full_alns),
            gpu_full_alns_islands=int(args.gpu_full_alns_islands),
        )
        dt = time.perf_counter() - t0
        stats = results.get("stats", {})
        print(
            f"mode={results.get('mode')} time_sec={dt:.3f} songs_total={stats.get('songs_total')} "
            f"songs_covered={stats.get('songs_covered')} variants_used={stats.get('gear_variants_used')}/"
            f"{stats.get('gear_variants_cap')}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
