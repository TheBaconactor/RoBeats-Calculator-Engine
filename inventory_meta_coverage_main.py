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


def _truthy_env(name: str) -> bool:
    return str(os.environ.get(name, "0") or "").strip().lower() in {"1", "true", "yes", "on"}


def _maybe_print_taichi_kernel_profile(*, requested: bool) -> None:
    if not requested:
        return
    if not _truthy_env("TAICHI_KERNEL_PROFILER"):
        return
    try:
        import taichi as ti

        ti.sync()
        ti.profiler.print_kernel_profiler_info()
    except Exception:
        pass


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
        "--partitions-per-song",
        type=int,
        default=32,
        help="GPU full: base witness patterns per song (K base). Legacy for other solvers (default: 32).",
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
        "--adaptive-rounds",
        type=int,
        default=3,
        help="GPU full: contributes to witness pool size (K_total). Legacy for other solvers (default: 3).",
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
        help="GPU full: contributes to witness pool size (K_total). Legacy for other solvers (default: 8).",
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
        help="Large-neighborhood search total time budget in seconds (split across restarts; default: 0=off).",
    )
    parser.add_argument(
        "--lns-attempts",
        type=int,
        default=200,
        help="Max LNS attempts total (split across restarts; default: 200).",
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
        "--gpu-full-wildcard-freq-bonus",
        type=int,
        default=0,
        help="GPU full: add to variant frequency for OV==0 offsets (default: 0).",
    )
    parser.add_argument(
        "--gpu-full-witness-anchor-patterns",
        type=int,
        default=24,
        help="GPU full: deterministic witness patterns always included (default: 24).",
    )
    parser.add_argument(
        "--gpu-full-witness-seed-streams",
        type=int,
        default=4,
        help="GPU full: internal RNG streams for witness patterns (default: 4).",
    )
    parser.add_argument(
        "--gpu-full-witness-palettes",
        type=int,
        default=1,
        help="GPU full: number of independent witness palettes (default: 1).",
    )
    parser.add_argument(
        "--gpu-full-repair",
        action="store_true",
        help="GPU full: attempt inventory-aware repair for uncovered songs (default: off).",
    )
    parser.add_argument(
        "--gpu-full-repair-attempts",
        type=int,
        default=128,
        help="GPU full repair: attempts per song (default: 128).",
    )
    parser.add_argument(
        "--gpu-full-repair-max-cands-per-slot",
        type=int,
        default=8,
        help="GPU full repair: max inventory variants considered per slot (default: 8).",
    )
    parser.add_argument(
        "--gpu-full-repair-song-limit",
        type=int,
        default=512,
        help="GPU full repair: max uncovered songs to attempt (0=all; default: 512).",
    )
    parser.add_argument(
        "--gpu-full-witness-pattern-profile",
        type=int,
        default=0,
        help="GPU full: witness pattern profile (0=balanced, 1=reuse-biased; default: 0).",
    )
    parser.add_argument(
        "--gpu-full-counter-stripes",
        type=int,
        default=1,
        help="GPU full: number of counter stripes for counts updates (default: 1).",
    )
    parser.add_argument(
        "--gpu-full-top-candidates",
        type=int,
        default=1,
        help="GPU full: top candidates per song to consider (default: 1).",
    )
    parser.add_argument(
        "--gpu-full-candidate-score-delta",
        type=int,
        default=0,
        help="GPU full: widen candidate pool to rows within this delta of peak (default: 0; exact peak only).",
    )
    parser.add_argument(
        "--gpu-full-candidate-limit-per-song",
        type=int,
        default=0,
        help="GPU full: max DB candidates per song when widening pool (0=auto; default: 0).",
    )
    parser.add_argument(
        "--gpu-full-repack-rarity-weighted",
        action="store_true",
        help="GPU full: make repack prefer swapping out rare variants (default: off).",
    )
    parser.add_argument(
        "--gpu-full-lns-freq-weighted",
        action="store_true",
        help="GPU full: weight LNS destroy/evict by witness frequency (default: off).",
    )
    parser.add_argument(
        "--gpu-full-v-pad-bin",
        type=int,
        default=4096,
        help="GPU full: pad V to a multiple of this bin size (kernel cache stability; default: 4096).",
    )
    parser.add_argument(
        "--gpu-full-variant-freq-mode",
        type=str,
        default="occurrence",
        choices=["occurrence", "song_support"],
        help="GPU full: tie-break weight for variants (default: occurrence).",
    )
    parser.add_argument(
        "--gpu-full-k-scan-select",
        type=int,
        default=0,
        help="GPU full: scan only this many patterns per song in selection (0=all; default: 0).",
    )
    parser.add_argument(
        "--gpu-full-k-scan-repack",
        type=int,
        default=0,
        help="GPU full: scan only this many patterns per song in repack (0=all; default: 0).",
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
            gpu_full_wildcard_freq_bonus=args.gpu_full_wildcard_freq_bonus,
            gpu_full_witness_anchor_patterns=args.gpu_full_witness_anchor_patterns,
            gpu_full_witness_seed_streams=args.gpu_full_witness_seed_streams,
            gpu_full_witness_palettes=int(args.gpu_full_witness_palettes),
            gpu_full_repack_rarity_weighted=bool(args.gpu_full_repack_rarity_weighted),
            gpu_full_lns_freq_weighted=bool(args.gpu_full_lns_freq_weighted),
            gpu_full_v_pad_bin=int(args.gpu_full_v_pad_bin),
            gpu_full_variant_freq_mode=str(args.gpu_full_variant_freq_mode),
            gpu_full_witness_pattern_profile=int(args.gpu_full_witness_pattern_profile),
            gpu_full_counter_stripes=int(args.gpu_full_counter_stripes),
            gpu_full_top_candidates=int(args.gpu_full_top_candidates),
            gpu_full_candidate_score_delta=int(args.gpu_full_candidate_score_delta),
            gpu_full_candidate_limit_per_song=int(args.gpu_full_candidate_limit_per_song),
            gpu_full_k_scan_select=int(args.gpu_full_k_scan_select),
            gpu_full_k_scan_repack=int(args.gpu_full_k_scan_repack),
            gpu_full_repair_enabled=bool(args.gpu_full_repair),
            gpu_full_repair_attempts=int(args.gpu_full_repair_attempts),
            gpu_full_repair_max_cands_per_slot=int(args.gpu_full_repair_max_cands_per_slot),
            gpu_full_repair_song_limit=int(args.gpu_full_repair_song_limit),
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
        _maybe_print_taichi_kernel_profile(requested=bool(args.profile or _truthy_env("TAICHI_KERNEL_PROFILER_PRINT")))

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
