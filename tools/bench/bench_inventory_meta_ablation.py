#!/usr/bin/env python3
"""
Benchmark/ablation runner for Inventory Meta coverage (GPU-only).

Measures per-pass song coverage under a fixed inventory cap, with optional feature toggles to
quantify which changes actually help.

Example:
  python tools/bench/bench_inventory_meta_ablation.py --trials 1 --lns-time-sec 10 --partitions-per-song 256
"""

from __future__ import annotations

import argparse
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from gear_optimizer.data.database import init_db
from inventory_optimizer import run_inventory_meta_coverage


@dataclass(frozen=True)
class TrialResult:
    covered: int
    variants_used: int
    witness_time_sec: float
    gpu_time_sec: float
    attempts: int
    improvements: int

    @property
    def total_solver_sec(self) -> float:
        return float(self.witness_time_sec + self.gpu_time_sec)


def _extract_trial(res: dict) -> TrialResult:
    stats = res["stats"]
    solver = res["solver_stats"]["solver"]
    wp = solver.get("witness_pool", {}) or {}
    gpu = solver.get("gpu_full", {}) or {}
    return TrialResult(
        covered=int(stats.get("songs_covered", 0)),
        variants_used=int(stats.get("gear_variants_used", 0)),
        witness_time_sec=float(wp.get("time_sec", 0.0)),
        gpu_time_sec=float(gpu.get("time_sec", 0.0)),
        attempts=int(gpu.get("attempts", 0)),
        improvements=int(gpu.get("improvements", 0)),
    )


def _summarize(label: str, trials: list[TrialResult]) -> None:
    covered = [t.covered for t in trials]
    total = [t.total_solver_sec for t in trials]
    attempts = [t.attempts for t in trials]
    improvements = [t.improvements for t in trials]
    best_cov = max(covered) if covered else 0
    med_cov = int(statistics.median(covered)) if covered else 0
    best_t = min(total) if total else 0.0
    med_t = float(statistics.median(total)) if total else 0.0
    med_attempts = int(statistics.median(attempts)) if attempts else 0
    med_impr = int(statistics.median(improvements)) if improvements else 0
    print(
        f"{label:34s}  covered(best/med)={best_cov:4d}/{med_cov:4d}  "
        f"time_sec(best/med)={best_t:5.2f}/{med_t:5.2f}  attempts~{med_attempts:4d} impr~{med_impr:3d}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(prog="bench_inventory_meta_ablation.py")
    ap.add_argument("--db-path", type=str, default="", help="Override SQLite path (sets EVOLUTION_DB_PATH).")
    ap.add_argument("--trials", type=int, default=1, help="Trials per configuration (default: 1).")
    ap.add_argument("--seed", type=int, default=0, help="Seed (0=random per run; default: 0).")
    ap.add_argument("--inventory-cap", type=int, default=100, help="Max gear variants (default: 100).")
    ap.add_argument("--partitions-per-song", type=int, default=256, help="GPU full K base (default: 256).")
    ap.add_argument("--adaptive-rounds", type=int, default=0, help="GPU full adaptive rounds (default: 0).")
    ap.add_argument("--adaptive-keep-per-song", type=int, default=8, help="GPU full keep per round (default: 8).")
    ap.add_argument("--gpu-full-wildcard-freq-bonus", type=int, default=40, help="GPU full wildcard freq bonus.")
    ap.add_argument("--gpu-repack-passes", type=int, default=3, help="GPU repack passes (default: 3).")
    ap.add_argument("--gpu-full-witness-palettes", type=int, default=1, help="Witness palettes (default: 1).")
    ap.add_argument("--gpu-full-repair", action="store_true", help="Enable inventory-aware repair (default: off).")
    ap.add_argument("--gpu-full-repair-attempts", type=int, default=128, help="Repair attempts per song (default: 128).")
    ap.add_argument("--gpu-full-repair-song-limit", type=int, default=512, help="Max songs for repair (default: 512).")
    ap.add_argument(
        "--gpu-full-variant-freq-mode",
        type=str,
        default="occurrence",
        choices=["occurrence", "song_support"],
        help="GPU full: tie-break weight for variants (default: occurrence).",
    )
    ap.add_argument(
        "--gpu-full-witness-pattern-profile",
        type=int,
        default=0,
        help="Witness profile (0=balanced, 1=reuse-biased; default: 0).",
    )
    ap.add_argument(
        "--gpu-full-counter-stripes",
        type=int,
        default=1,
        help="Counter stripes for counts updates (default: 1).",
    )
    ap.add_argument(
        "--gpu-full-top-candidates",
        type=int,
        default=1,
        help="Top candidates per song (default: 1).",
    )
    ap.add_argument(
        "--gpu-full-candidate-score-delta",
        type=int,
        default=0,
        help="Widen candidate pool to rows within this delta of peak (default: 0).",
    )
    ap.add_argument(
        "--gpu-full-k-scan-select",
        type=int,
        default=0,
        help="Scan only this many patterns per song in selection (0=all; default: 0).",
    )
    ap.add_argument(
        "--gpu-full-k-scan-repack",
        type=int,
        default=0,
        help="Scan only this many patterns per song in repack (0=all; default: 0).",
    )
    ap.add_argument(
        "--gpu-full-v-pad-bin",
        type=int,
        default=4096,
        help="Pad V to a multiple of this bin size (default: 4096).",
    )
    ap.add_argument("--lns-time-sec", type=float, default=10.0, help="LNS time budget (default: 10).")
    ap.add_argument("--lns-attempts", type=int, default=1000, help="Max LNS attempts (default: 1000).")
    ap.add_argument("--gpu-lns-destroy", type=int, default=12, help="LNS destroy count (default: 12).")
    ap.add_argument("--warmup", action="store_true", help="Run one warmup solve (not counted).")
    args = ap.parse_args()

    if args.db_path:
        os.environ["EVOLUTION_DB_PATH"] = args.db_path

    init_db()

    base_kwargs = dict(
        solver="gpu_full",
        restarts=1,
        inventory_cap=int(args.inventory_cap),
        partitions_per_song=int(args.partitions_per_song),
        adaptive_rounds=int(args.adaptive_rounds),
        adaptive_keep_per_song=int(args.adaptive_keep_per_song),
        gpu_repack_passes=int(args.gpu_repack_passes),
        gpu_lns_destroy=int(args.gpu_lns_destroy),
        lns_time_sec=float(args.lns_time_sec),
        lns_attempts=int(args.lns_attempts),
        gpu_full_wildcard_freq_bonus=int(args.gpu_full_wildcard_freq_bonus),
        gpu_full_variant_freq_mode=str(args.gpu_full_variant_freq_mode),
        gpu_full_v_pad_bin=int(args.gpu_full_v_pad_bin),
        gpu_full_counter_stripes=int(args.gpu_full_counter_stripes),
        gpu_full_top_candidates=int(args.gpu_full_top_candidates),
        gpu_full_candidate_score_delta=int(args.gpu_full_candidate_score_delta),
        gpu_full_k_scan_select=int(args.gpu_full_k_scan_select),
        gpu_full_k_scan_repack=int(args.gpu_full_k_scan_repack),
        gpu_full_witness_palettes=int(args.gpu_full_witness_palettes),
        gpu_full_repair_enabled=bool(args.gpu_full_repair),
        gpu_full_repair_attempts=int(args.gpu_full_repair_attempts),
        gpu_full_repair_song_limit=int(args.gpu_full_repair_song_limit),
    )

    configs = [
        (
            "baseline",
            dict(
                gpu_full_witness_anchor_patterns=24,
                gpu_full_witness_seed_streams=4,
                gpu_full_lns_freq_weighted=False,
                gpu_full_repack_rarity_weighted=False,
                gpu_full_witness_pattern_profile=int(args.gpu_full_witness_pattern_profile),
            ),
        ),
        (
            "witness_profile_1",
            dict(
                gpu_full_witness_anchor_patterns=24,
                gpu_full_witness_seed_streams=4,
                gpu_full_lns_freq_weighted=False,
                gpu_full_repack_rarity_weighted=False,
                gpu_full_witness_pattern_profile=1,
            ),
        ),
        (
            "no_anchors",
            dict(
                gpu_full_witness_anchor_patterns=0,
                gpu_full_witness_seed_streams=4,
                gpu_full_lns_freq_weighted=False,
                gpu_full_repack_rarity_weighted=False,
                gpu_full_witness_pattern_profile=int(args.gpu_full_witness_pattern_profile),
            ),
        ),
        (
            "freq_weighted_lns",
            dict(
                gpu_full_witness_anchor_patterns=24,
                gpu_full_witness_seed_streams=4,
                gpu_full_lns_freq_weighted=True,
                gpu_full_repack_rarity_weighted=False,
                gpu_full_witness_pattern_profile=int(args.gpu_full_witness_pattern_profile),
            ),
        ),
        (
            "repack_rarity",
            dict(
                gpu_full_witness_anchor_patterns=24,
                gpu_full_witness_seed_streams=4,
                gpu_full_lns_freq_weighted=False,
                gpu_full_repack_rarity_weighted=True,
                gpu_full_witness_pattern_profile=int(args.gpu_full_witness_pattern_profile),
            ),
        ),
        (
            "no_anchors+freq_weighted",
            dict(
                gpu_full_witness_anchor_patterns=0,
                gpu_full_witness_seed_streams=4,
                gpu_full_lns_freq_weighted=True,
                gpu_full_repack_rarity_weighted=False,
                gpu_full_witness_pattern_profile=int(args.gpu_full_witness_pattern_profile),
            ),
        ),
    ]

    print("Inventory Meta Ablation (GPU-only)")
    print(
        f"trials={int(args.trials)} seed={int(args.seed)} cap={int(args.inventory_cap)} "
        f"K={int(args.partitions_per_song)} lns={float(args.lns_time_sec)}s"
    )
    print()

    trial_seeds = None
    if int(args.seed) == 0:
        trial_seeds = [random.randrange(1, 2**31 - 1) for _ in range(int(args.trials))]
        print(f"random_seeds={trial_seeds}")
        print()

    for label, overrides in configs:
        if args.warmup:
            run_inventory_meta_coverage(**base_kwargs, **overrides)
        trials: list[TrialResult] = []
        for i in range(int(args.trials)):
            # Ensure seed=0 runs vary even in a tight loop.
            if int(args.seed) == 0:
                time.sleep(0.002)
                seed_val = int(trial_seeds[i])
            else:
                seed_val = int(args.seed)
            res = run_inventory_meta_coverage(**base_kwargs, seed=seed_val, **overrides)
            trials.append(_extract_trial(res))
        _summarize(label, trials)


if __name__ == "__main__":
    main()
