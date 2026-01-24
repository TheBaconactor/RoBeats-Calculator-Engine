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
from inventory_optimizer.macos_gpu_util import MacosGpuUtilSampler


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
    parser.add_argument(
        "--element",
        type=str,
        default="",
        help="Restrict songs to those with peak rows matching this element (e.g. Beat/Flow/Chill).",
    )
    parser.add_argument(
        "--secondary-element",
        type=str,
        default="",
        help="Optional second element filter; songs matching either element are included.",
    )
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
        default=40,
        help="GPU full: add to variant frequency for OV==0 offsets (default: 40).",
    )
    parser.add_argument(
        "--gpu-full-wildcard-palette-size",
        type=int,
        default=0,
        help="GPU full: learn and inject a small OV==0 per-slot wildcard palette into witness generation (0=off; default: 0).",
    )
    parser.add_argument(
        "--gpu-full-wildcard-palette-min-count",
        type=int,
        default=2,
        help="GPU full: wildcard palette learning minimum frequency threshold (default: 2).",
    )
    parser.add_argument(
        "--gpu-full-wildcard-palette-scan",
        type=int,
        default=8,
        help="GPU full: per-slot max palette entries scanned when fitting (default: 8).",
    )
    parser.add_argument(
        "--gpu-full-wildcard-palette-tail-slots",
        type=int,
        default=3,
        help="GPU full: only try palette injection on the tail slots of the rare->common order (0..6, default: 3).",
    )
    parser.add_argument(
        "--gpu-full-synergy-weight",
        type=int,
        default=0,
        help="GPU full: per-pattern wildcard synergy bonus weight (0=off; default: 0).",
    )
    parser.add_argument(
        "--gpu-full-synergy-top-offsets",
        type=int,
        default=128,
        help="GPU full synergy: consider only the top-N wildcard offsets by witness frequency (default: 128).",
    )
    parser.add_argument(
        "--gpu-full-synergy-min-pair-count",
        type=int,
        default=2,
        help="GPU full synergy: minimum co-occurrence count for a pair to contribute (default: 2).",
    )
    parser.add_argument(
        "--gpu-full-synergy-scale",
        type=int,
        default=256,
        help="GPU full synergy: scale factor applied to the PPMI sum (default: 256).",
    )
    parser.add_argument(
        "--gpu-full-synergy-max-bonus",
        type=int,
        default=4095,
        help="GPU full synergy: clamp per-pattern bonus to this max (default: 4095).",
    )
    parser.add_argument(
        "--gpu-full-new-gear-penalty",
        type=int,
        default=0,
        help="GPU full: penalty per newly introduced gear ID when covering a song (0=off; default: 0).",
    )
    parser.add_argument(
        "--gpu-full-witness-anchor-patterns",
        type=int,
        default=128,
        help="GPU full: deterministic witness patterns always included (default: 128).",
    )
    parser.add_argument(
        "--gpu-full-witness-seed-streams",
        type=int,
        default=1,
        help="GPU full: internal RNG streams for witness patterns (default: 1).",
    )
    parser.add_argument(
        "--gpu-full-witness-palettes",
        type=int,
        default=1,
        help="GPU full: number of independent witness palettes (default: 1).",
    )
    parser.add_argument(
        "--gpu-full-repair",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="GPU full: attempt inventory-aware repair for uncovered songs (default: on).",
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
        default=16,
        help="GPU full repair: max inventory variants considered per slot (default: 16).",
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
        default=1,
        help="GPU full: witness pattern profile (0=balanced, 1=reuse-biased, 2=reuse-biased+canonical anchors; default: 1).",
    )
    parser.add_argument(
        "--gpu-full-counter-stripes",
        type=int,
        default=1,
        help="GPU full: number of counter stripes for counts updates (default: 1).",
    )
    parser.add_argument(
        "--gpu-full-human",
        action="store_true",
        help="GPU full: enable optionality-first ('human') mode (allows small score drop for reusable core gear; default: off).",
    )
    parser.add_argument(
        "--gpu-full-human-gear-penalty-step",
        type=int,
        default=0,
        help="GPU full human: penalty added per existing variant for a gear (default: 0).",
    )
    parser.add_argument(
        "--gpu-full-human-gear-free",
        type=int,
        default=2,
        help="GPU full human: number of variants per gear with no concentration penalty (default: 2).",
    )
    parser.add_argument(
        "--gpu-full-human-colored-penalty",
        type=int,
        default=0,
        help="GPU full human: extra penalty per new non-wild (OV>0) variant (default: 0).",
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
        "--gpu-full-lns-random-destroy-prob",
        type=float,
        default=0.0,
        help="GPU full: per-attempt probability of using a pure random destroy step (default: 0.0).",
    )
    parser.add_argument(
        "--gpu-full-lns-restore-after",
        type=int,
        default=12,
        help="GPU full: restore best after this many non-improving LNS attempts (default: 12).",
    )
    parser.add_argument(
        "--gpu-full-lns-restore-drop",
        type=int,
        default=4,
        help="GPU full: restore best if coverage drops this far below best (default: 4).",
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
        default="song_support",
        choices=["occurrence", "song_support"],
        help="GPU full: tie-break weight for variants (default: song_support).",
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
        "--gpu-full-alns",
        action="store_true",
        help="GPU full: enable multi-island ALNS (bandit ruin-and-recreate) instead of single-trajectory LNS (default: off).",
    )
    parser.add_argument(
        "--gpu-full-alns-islands",
        type=int,
        default=1,
        help="GPU full: number of concurrent ALNS islands to run in one solve (default: 1).",
    )
    parser.add_argument(
        "--gpu-full-pt",
        action="store_true",
        help="GPU full: enable parallel tempering across ALNS islands (swaps temperature labels; default: off).",
    )
    parser.add_argument(
        "--gpu-full-pt-t-min",
        type=float,
        default=1.0,
        help="GPU full PT: minimum temperature (default: 1.0).",
    )
    parser.add_argument(
        "--gpu-full-pt-t-max",
        type=float,
        default=10.0,
        help="GPU full PT: maximum temperature (default: 10.0).",
    )
    parser.add_argument(
        "--gpu-full-pt-swap-interval",
        type=int,
        default=8,
        help="GPU full PT: attempt replica exchange every N ALNS iterations (default: 8).",
    )
    parser.add_argument(
        "--gpu-full-pt-destroy-beta",
        type=float,
        default=0.0,
        help="GPU full PT: exponent for destroy degree scaling with temperature (default: 0.0).",
    )
    parser.add_argument(
        "--gpu-full-pt-cap-slack-max",
        type=int,
        default=0,
        help="GPU full PT: max extra inventory capacity for the hottest replicas (barrier crossing; default: 0).",
    )
    parser.add_argument(
        "--cluster-k",
        type=int,
        default=0,
        help="If >0, run clustered GPU_FULL solve: k-means on gem_totals, then bridge solve (default: 0=off).",
    )
    parser.add_argument("--cluster-seed", type=int, default=1, help="Cluster RNG seed (default: 1).")
    parser.add_argument(
        "--cluster-bridge-reserve",
        type=int,
        default=10,
        help="Reserve this many variants for the final bridge solve (default: 10).",
    )
    parser.add_argument(
        "--cluster-report",
        type=str,
        default="",
        help="Optional JSON output path for the gem cluster report.",
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
        gpu_sampler = None
        if sys.platform == "darwin" and (bool(args.profile) or _truthy_env("MACOS_GPU_UTIL_PROFILE")):
            # Best-effort macOS GPU utilization sampling (IOKit/ioreg). Never crash a run.
            # Disabled by default to avoid adding host-side overhead to the optimization loop.
            try:
                gpu_sampler = MacosGpuUtilSampler(interval_sec=0.25)
                gpu_sampler.start()
            except Exception:
                gpu_sampler = None

        init_db()
        if int(args.cluster_k) > 0:
            if str(args.solver) != "gpu_full":
                raise ValueError("--cluster-k requires --solver gpu_full")
            from inventory_optimizer.clustered import run_clustered_gpu_full_coverage, write_cluster_report_json
            from inventory_optimizer.db import fetch_peak_candidates_allow_missing

            candidates_by_song, _missing = fetch_peak_candidates_allow_missing()
            # Apply element filter here (mirrors run_inventory_meta_coverage behavior).
            element = (args.element or "").strip() or None
            secondary = (args.secondary_element or "").strip() or None
            allowed = {e for e in (element, secondary) if e}
            if allowed:
                candidates_by_song = {
                    k: [c for c in v if getattr(c, "selected_element", None) in allowed] for k, v in candidates_by_song.items()
                }
                candidates_by_song = {k: v for k, v in candidates_by_song.items() if v}

            results, report = run_clustered_gpu_full_coverage(
                candidates_by_song=candidates_by_song,
                inventory_cap=int(args.inventory_cap),
                cluster_k=int(args.cluster_k),
                cluster_seed=int(args.cluster_seed),
                bridge_reserve=int(args.cluster_bridge_reserve),
                seed=int(args.seed),
                partitions_per_song=int(args.partitions_per_song),
                adaptive_rounds=int(args.adaptive_rounds),
                adaptive_keep_per_song=int(args.adaptive_keep_per_song),
                gpu_repack_passes=int(args.gpu_repack_passes),
                gpu_lns_destroy=int(args.gpu_lns_destroy),
                lns_time_sec=float(args.lns_time_sec),
                lns_attempts=int(args.lns_attempts),
                gpu_full_witness_palettes=int(args.gpu_full_witness_palettes),
                gpu_full_witness_pattern_profile=int(args.gpu_full_witness_pattern_profile),
                gpu_full_witness_anchor_patterns=int(args.gpu_full_witness_anchor_patterns),
                gpu_full_witness_seed_streams=int(args.gpu_full_witness_seed_streams),
                wildcard_freq_bonus=int(args.gpu_full_wildcard_freq_bonus),
                gpu_full_variant_freq_mode=str(args.gpu_full_variant_freq_mode),
                gpu_full_counter_stripes=int(args.gpu_full_counter_stripes),
                gpu_full_k_scan_select=int(args.gpu_full_k_scan_select),
                gpu_full_k_scan_repack=int(args.gpu_full_k_scan_repack),
                gpu_full_alns_enabled=bool(args.gpu_full_alns),
                gpu_full_alns_islands=int(args.gpu_full_alns_islands),
                gpu_full_pt_enabled=bool(args.gpu_full_pt),
                gpu_full_pt_t_min=float(args.gpu_full_pt_t_min),
                gpu_full_pt_t_max=float(args.gpu_full_pt_t_max),
                gpu_full_pt_swap_interval=int(args.gpu_full_pt_swap_interval),
                gpu_full_pt_destroy_beta=float(args.gpu_full_pt_destroy_beta),
                gpu_full_pt_cap_slack_max=int(args.gpu_full_pt_cap_slack_max),
                profile=bool(args.profile),
            )
            if args.cluster_report:
                write_cluster_report_json(report, args.cluster_report)
        else:
            results = run_inventory_meta_coverage(
                inventory_cap=args.inventory_cap,
                element=(args.element or None),
                secondary_element=(args.secondary_element or None),
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
                gpu_full_wildcard_palette_size=int(args.gpu_full_wildcard_palette_size),
                gpu_full_wildcard_palette_min_count=int(args.gpu_full_wildcard_palette_min_count),
                gpu_full_wildcard_palette_scan=int(args.gpu_full_wildcard_palette_scan),
                gpu_full_wildcard_palette_tail_slots=int(args.gpu_full_wildcard_palette_tail_slots),
                gpu_full_synergy_weight=int(args.gpu_full_synergy_weight),
                gpu_full_synergy_top_offsets=int(args.gpu_full_synergy_top_offsets),
                gpu_full_synergy_min_pair_count=int(args.gpu_full_synergy_min_pair_count),
                gpu_full_synergy_scale=int(args.gpu_full_synergy_scale),
                gpu_full_synergy_max_bonus=int(args.gpu_full_synergy_max_bonus),
                gpu_full_new_gear_penalty=int(args.gpu_full_new_gear_penalty),
                gpu_full_witness_anchor_patterns=args.gpu_full_witness_anchor_patterns,
                gpu_full_witness_seed_streams=args.gpu_full_witness_seed_streams,
                gpu_full_witness_palettes=int(args.gpu_full_witness_palettes),
                gpu_full_repack_rarity_weighted=bool(args.gpu_full_repack_rarity_weighted),
                gpu_full_lns_freq_weighted=bool(args.gpu_full_lns_freq_weighted),
                gpu_full_lns_random_destroy_prob=float(args.gpu_full_lns_random_destroy_prob),
                gpu_full_lns_restore_after=int(args.gpu_full_lns_restore_after),
                gpu_full_lns_restore_drop=int(args.gpu_full_lns_restore_drop),
                gpu_full_v_pad_bin=int(args.gpu_full_v_pad_bin),
                gpu_full_variant_freq_mode=str(args.gpu_full_variant_freq_mode),
                gpu_full_witness_pattern_profile=int(args.gpu_full_witness_pattern_profile),
                gpu_full_counter_stripes=int(args.gpu_full_counter_stripes),
                gpu_full_human_mode=bool(args.gpu_full_human),
                gpu_full_human_gear_free=int(args.gpu_full_human_gear_free),
                gpu_full_human_gear_penalty_step=int(args.gpu_full_human_gear_penalty_step),
                gpu_full_human_colored_penalty=int(args.gpu_full_human_colored_penalty),
                gpu_full_top_candidates=int(args.gpu_full_top_candidates),
                gpu_full_candidate_score_delta=int(args.gpu_full_candidate_score_delta),
                gpu_full_candidate_limit_per_song=int(args.gpu_full_candidate_limit_per_song),
                gpu_full_k_scan_select=int(args.gpu_full_k_scan_select),
                gpu_full_k_scan_repack=int(args.gpu_full_k_scan_repack),
                gpu_full_alns_enabled=bool(args.gpu_full_alns),
                gpu_full_alns_islands=int(args.gpu_full_alns_islands),
                gpu_full_pt_enabled=bool(args.gpu_full_pt),
                gpu_full_pt_t_min=float(args.gpu_full_pt_t_min),
                gpu_full_pt_t_max=float(args.gpu_full_pt_t_max),
                gpu_full_pt_swap_interval=int(args.gpu_full_pt_swap_interval),
                gpu_full_pt_destroy_beta=float(args.gpu_full_pt_destroy_beta),
                gpu_full_pt_cap_slack_max=int(args.gpu_full_pt_cap_slack_max),
                gpu_full_repair_enabled=bool(args.gpu_full_repair),
                gpu_full_repair_attempts=int(args.gpu_full_repair_attempts),
                gpu_full_repair_max_cands_per_slot=int(args.gpu_full_repair_max_cands_per_slot),
                gpu_full_repair_song_limit=int(args.gpu_full_repair_song_limit),
            )
        if gpu_sampler is not None:
            try:
                summary = gpu_sampler.stop()
                results.setdefault("profiling", {})["macos_gpu_util"] = {
                    "samples": int(summary.samples),
                    "wall_sec": round(float(summary.wall_sec), 3),
                    "device_util_avg": None if summary.device_util_avg is None else round(float(summary.device_util_avg), 2),
                    "device_util_max": summary.device_util_max,
                    "renderer_util_avg": None
                    if summary.renderer_util_avg is None
                    else round(float(summary.renderer_util_avg), 2),
                    "renderer_util_max": summary.renderer_util_max,
                    "tiler_util_avg": None if summary.tiler_util_avg is None else round(float(summary.tiler_util_avg), 2),
                    "tiler_util_max": summary.tiler_util_max,
                    "last_submit_pid_top": list(summary.last_submit_pid_top),
                    "proc_pid": summary.proc_pid,
                    "proc_gpu_time_util_est": None
                    if summary.proc_gpu_time_util_est is None
                    else round(float(summary.proc_gpu_time_util_est), 2),
                }
            except Exception:
                pass

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
