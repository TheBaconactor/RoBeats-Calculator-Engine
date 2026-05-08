#!/usr/bin/env python3
"""
InventoryMeta Coverage - Main Entry Point

Goal: maximize the number of songs whose exact peak can be reproduced
using an inventory of <=100 gear variants (GPU heuristic; no proof).
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
from dataclasses import replace
from pathlib import Path
import logging

REPO_ROOT = Path(__file__).resolve().parents[1]

from gear_optimizer.core.parsing import env_flag
from gear_optimizer.data.database import init_db
from inventory_optimizer import export_inventory_meta_json, run_inventory_meta_coverage
from inventory_optimizer.inventory_meta_config import (
    InventoryMetaCoverageSettings,
    default_inventory_meta_config_path,
    load_inventory_meta_coverage_settings,
)
from inventory_optimizer.macos_gpu_util import MacosGpuUtilSampler



logger = logging.getLogger(__name__)
def _maybe_print_taichi_kernel_profile(*, requested: bool) -> None:
    if not requested:
        return
    if not env_flag("TAICHI_KERNEL_PROFILER"):
        return
    try:
        import taichi as ti

        ti.sync()
        ti.profiler.print_kernel_profiler_info()
    except Exception as e:
        logger.warning(f"inventory_cli:_maybe_print_taichi_kernel_profile: {e}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inventory_meta_coverage_main.py",
        description="Inventory Meta coverage solver (GPU-only; standardized on gpu_full).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run coverage solver (gpu_full).")
    run.add_argument("--config", type=str, default="", help="Ini path (default: configs/inventory_meta_coverage.ini).")
    run.add_argument("--quality", type=str, default="", choices=["low", "medium", "high"], help="Quality preset.")
    run.add_argument(
        "--set",
        type=str,
        action="append",
        default=[],
        metavar="Section.Key=Value",
        help="Override config key(s) without editing the ini (repeatable).",
    )
    run.add_argument("--db-path", type=str, default="", help="Override SQLite path (sets EVOLUTION_DB_PATH).")
    run.add_argument("--inventory-cap", type=int, default=0, help="Override inventory cap (default: from config).")
    run.add_argument("--seed", type=int, default=0, help="Override RNG seed (default: from config).")
    run.add_argument("--restarts", type=int, default=0, help="Override restarts (default: from config).")
    run.add_argument("--element", type=str, default="", help="Restrict songs to this element (Beat/Flow/Chill/etc).")
    run.add_argument(
        "--secondary-element",
        type=str,
        default="",
        help="Optional second element; songs matching either element are included.",
    )
    run.add_argument("--song-limit", type=int, default=0, help="Limit number of songs processed (debug).")
    run.add_argument(
        "--output", type=str, default="", help="Output JSON path (default: artifacts/inventory_meta_coverage.json)."
    )
    run.add_argument("--profile", action="store_true", help="Enable best-effort host-side profiling/logs.")
    run.add_argument(
        "--print-effective-config",
        action="store_true",
        help="Print the effective config (after preset + overrides) as JSON and exit.",
    )

    cluster = sub.add_parser("cluster", help="Run clustered gpu_full solve (advanced).")
    cluster.add_argument(
        "--config", type=str, default="", help="Ini path (default: configs/inventory_meta_coverage.ini)."
    )
    cluster.add_argument("--quality", type=str, default="", choices=["low", "medium", "high"], help="Quality preset.")
    cluster.add_argument("--set", type=str, action="append", default=[], metavar="Section.Key=Value")
    cluster.add_argument("--db-path", type=str, default="", help="Override SQLite path (sets EVOLUTION_DB_PATH).")
    cluster.add_argument("--inventory-cap", type=int, default=0, help="Override inventory cap (default: from config).")
    cluster.add_argument("--seed", type=int, default=0, help="Override RNG seed (default: from config).")
    cluster.add_argument("--element", type=str, default="", help="Restrict songs to this element.")
    cluster.add_argument("--secondary-element", type=str, default="", help="Optional second element filter.")
    cluster.add_argument("--song-limit", type=int, default=0, help="Limit number of songs processed (debug).")
    cluster.add_argument(
        "--output", type=str, default="", help="Output JSON path (default: artifacts/inventory_meta_coverage.json)."
    )
    cluster.add_argument("--profile", action="store_true", help="Enable best-effort host-side profiling/logs.")
    cluster.add_argument("--cluster-k", type=int, required=True, help="k-means clusters (k>0).")
    cluster.add_argument("--cluster-seed", type=int, default=1, help="Cluster RNG seed.")
    cluster.add_argument(
        "--cluster-bridge-reserve", type=int, default=10, help="Reserve variants for final bridge solve."
    )
    cluster.add_argument("--cluster-report", type=str, default="", help="Optional JSON output path for cluster report.")

    uni = sub.add_parser("build-universe", help="Build a variant-frequency universe JSON and exit (advanced).")
    uni.add_argument("--db-path", type=str, required=True, help="SQLite snapshot path.")
    uni.add_argument("--out", type=str, required=True, help="Output JSON path.")
    uni.add_argument("--seed", type=int, default=1, help="RNG seed (default: 1).")
    uni.add_argument("--element", type=str, default="", help="Restrict songs to this element.")
    uni.add_argument("--secondary-element", type=str, default="", help="Optional second element filter.")
    uni.add_argument("--song-limit", type=int, default=0, help="Limit number of songs processed (debug).")
    uni.add_argument("--top-candidates", type=int, default=5, help="Max peak candidates per song.")
    uni.add_argument("--patterns-per-candidate", type=int, default=1000, help="Random partitions per candidate.")
    uni.add_argument("--universe-size", type=int, default=5000, help="Keep top-N variants by frequency.")
    uni.add_argument("--batch-instances", type=int, default=1024, help="Candidate-instance batch size.")

    return parser


def _load_settings_from_args(args) -> tuple[InventoryMetaCoverageSettings, dict, list[str]]:
    settings, meta, warnings = load_inventory_meta_coverage_settings(
        config_path=str(getattr(args, "config", "") or ""),
        quality=str(getattr(args, "quality", "") or ""),
        set_overrides=list(getattr(args, "set", []) or []),
    )

    inventory_cap = int(getattr(args, "inventory_cap", 0) or 0)
    seed = int(getattr(args, "seed", 0) or 0)
    restarts = int(getattr(args, "restarts", 0) or 0)
    song_limit = int(getattr(args, "song_limit", 0) or 0)
    element = str(getattr(args, "element", "") or "").strip() or None
    secondary = str(getattr(args, "secondary_element", "") or "").strip() or None
    profile = bool(getattr(args, "profile", False) or False)

    settings = replace(
        settings,
        inventory_cap=inventory_cap if inventory_cap > 0 else settings.inventory_cap,
        seed=seed if seed > 0 else settings.seed,
        restarts=restarts if restarts > 0 else settings.restarts,
        song_limit=song_limit if song_limit > 0 else settings.song_limit,
        element=element if element else settings.element,
        secondary_element=secondary if secondary else settings.secondary_element,
        profile=profile or settings.profile,
    )

    effective_quality = str(((meta.get("meta") or {}).get("quality") or "medium")).strip().lower() or "medium"
    effective_path = str(((meta.get("meta") or {}).get("config_path") or default_inventory_meta_config_path())).strip()
    effective_set = list((meta.get("meta") or {}).get("set_overrides") or [])
    meta = settings.to_effective_config_dict(
        quality=effective_quality, config_path=effective_path, set_overrides=effective_set
    )
    return settings, meta, warnings


def main(argv: list[str] | None = None) -> int:
    multiprocessing.freeze_support()

    parser = _build_parser()
    if argv is None:
        argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["run", *argv]
    args = parser.parse_args(argv)

    if getattr(args, "db_path", ""):
        os.environ["EVOLUTION_DB_PATH"] = args.db_path

    print("=" * 60)
    print("INVENTORY META COVERAGE - GPU Heuristic")
    print("=" * 60)
    print()

    try:
        gpu_sampler = None
        if sys.platform == "darwin" and (bool(getattr(args, "profile", False)) or env_flag("MACOS_GPU_UTIL_PROFILE")):
            # Best-effort macOS GPU utilization sampling (IOKit/ioreg). Never crash a run.
            # Disabled by default to avoid adding host-side overhead to the optimization loop.
            try:
                gpu_sampler = MacosGpuUtilSampler(interval_sec=0.25)
                gpu_sampler.start()
            except Exception as e:
                logger.warning(f"inventory_cli:main: {e}")
                gpu_sampler = None

        init_db()

        if args.cmd == "build-universe":
            from inventory_optimizer.variant_frequency_universe import (
                VariantUniverseBuildConfig,
                build_variant_frequency_universe,
                write_variant_frequency_universe_json,
            )

            cfg = VariantUniverseBuildConfig(
                top_candidates_per_song=int(args.top_candidates),
                patterns_per_candidate=int(args.patterns_per_candidate),
                universe_size=int(args.universe_size),
                seed=int(args.seed),
                element=(args.element or "").strip() or None,
                secondary_element=(args.secondary_element or "").strip() or None,
                song_limit=int(args.song_limit) if int(args.song_limit) > 0 else None,
                batch_instances=int(args.batch_instances),
            )
            payload = build_variant_frequency_universe(config=cfg, db_path=args.db_path or "")
            out_path = write_variant_frequency_universe_json(payload, args.out)
            print(f"[VariantFrequencyUniverse] wrote: {out_path}")
            if gpu_sampler is not None:
                try:
                    gpu_sampler.stop()
                except Exception as e:
                    logger.warning(f"inventory_cli:main: {e}")
            return

        if args.cmd == "cluster":
            from gear_optimizer.data.database import get_db_connection
            from inventory_optimizer.clustered import run_clustered_gpu_full_coverage, write_cluster_report_json
            from inventory_optimizer.db import fetch_peak_candidates_allow_missing

            settings, meta, warnings = _load_settings_from_args(args)

            conn = get_db_connection(args.db_path or None)
            try:
                candidates_by_song, _missing = fetch_peak_candidates_allow_missing(conn)
            finally:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"inventory_cli:main: {e}")

            # Apply element filter here (mirrors run_inventory_meta_coverage behavior).
            element = (args.element or "").strip() or None
            secondary = (args.secondary_element or "").strip() or None
            allowed = {e for e in (element, secondary) if e}
            if allowed:
                candidates_by_song = {
                    k: [c for c in v if getattr(c, "selected_element", None) in allowed]
                    for k, v in candidates_by_song.items()
                }
                candidates_by_song = {k: v for k, v in candidates_by_song.items() if v}

            results, report = run_clustered_gpu_full_coverage(
                candidates_by_song=candidates_by_song,
                inventory_cap=int(settings.inventory_cap),
                cluster_k=int(args.cluster_k),
                cluster_seed=int(args.cluster_seed),
                bridge_reserve=int(args.cluster_bridge_reserve),
                seed=int(settings.seed),
                partitions_per_song=int(settings.partitions_per_song),
                adaptive_rounds=int(settings.adaptive_rounds),
                adaptive_keep_per_song=int(settings.adaptive_keep_per_song),
                gpu_repack_passes=int(settings.gpu_repack_passes),
                gpu_lns_destroy=int(settings.gpu_lns_destroy),
                lns_time_sec=float(settings.lns_time_sec),
                lns_attempts=int(settings.lns_attempts),
                gpu_full_witness_palettes=int(settings.gpu_full_witness_palettes),
                gpu_full_witness_pattern_profile=int(settings.gpu_full_witness_pattern_profile),
                gpu_full_witness_anchor_patterns=int(settings.gpu_full_witness_anchor_patterns),
                gpu_full_witness_seed_streams=int(settings.gpu_full_witness_seed_streams),
                wildcard_freq_bonus=int(settings.gpu_full_wildcard_freq_bonus),
                gpu_full_variant_freq_mode=str(settings.gpu_full_variant_freq_mode),
                gpu_full_counter_stripes=int(settings.gpu_full_counter_stripes),
                gpu_full_k_scan_select=int(settings.gpu_full_k_scan_select),
                gpu_full_k_scan_repack=int(settings.gpu_full_k_scan_repack),
                gpu_full_alns_enabled=bool(settings.gpu_full_alns_enabled),
                gpu_full_alns_islands=int(settings.gpu_full_alns_islands),
                gpu_full_pt_enabled=bool(settings.gpu_full_pt_enabled),
                gpu_full_pt_t_min=float(settings.gpu_full_pt_t_min),
                gpu_full_pt_t_max=float(settings.gpu_full_pt_t_max),
                gpu_full_pt_swap_interval=int(settings.gpu_full_pt_swap_interval),
                gpu_full_pt_destroy_beta=float(settings.gpu_full_pt_destroy_beta),
                gpu_full_pt_cap_slack_max=int(settings.gpu_full_pt_cap_slack_max),
                gpu_full_repair_enabled=bool(settings.gpu_full_repair_enabled),
                gpu_full_repair_attempts=int(settings.gpu_full_repair_attempts),
                gpu_full_repair_max_cands_per_slot=int(settings.gpu_full_repair_max_cands_per_slot),
                gpu_full_repair_song_limit=int(settings.gpu_full_repair_song_limit),
                gpu_full_lns_freq_weighted=bool(settings.gpu_full_lns_freq_weighted),
                profile=bool(settings.profile),
            )
            results["effective_config"] = meta
            if warnings:
                results["effective_config_warnings"] = warnings
            results["cli"] = {"argv": list(sys.argv), "cmd": "cluster"}

            if args.cluster_report:
                write_cluster_report_json(report, args.cluster_report)

            out = getattr(args, "output", "") or str(REPO_ROOT / "artifacts" / "inventory_meta_coverage.json")
            output_path = export_inventory_meta_json(results, out)
            print(f"[Clustered] wrote: {output_path}")
            return

        if args.cmd != "run":
            raise ValueError(f"Unknown command: {args.cmd}")

        settings, meta, warnings = _load_settings_from_args(args)
        if args.print_effective_config:
            payload = {"effective_config": meta, "warnings": warnings}
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            if gpu_sampler is not None:
                try:
                    gpu_sampler.stop()
                except Exception as e:
                    logger.warning(f"inventory_cli:main: {e}")
            return

        results = run_inventory_meta_coverage(
            **{k: v for k, v in settings.to_run_kwargs().items() if v is not None},
        )
        results["effective_config"] = meta
        if warnings:
            results["effective_config_warnings"] = warnings
        results["cli"] = {"argv": list(sys.argv), "cmd": "run"}

        if gpu_sampler is not None:
            try:
                summary = gpu_sampler.stop()
                results.setdefault("profiling", {})["macos_gpu_util"] = {
                    "samples": int(summary.samples),
                    "wall_sec": round(float(summary.wall_sec), 3),
                    "device_util_avg": None
                    if summary.device_util_avg is None
                    else round(float(summary.device_util_avg), 2),
                    "device_util_max": summary.device_util_max,
                    "renderer_util_avg": None
                    if summary.renderer_util_avg is None
                    else round(float(summary.renderer_util_avg), 2),
                    "renderer_util_max": summary.renderer_util_max,
                    "tiler_util_avg": None
                    if summary.tiler_util_avg is None
                    else round(float(summary.tiler_util_avg), 2),
                    "tiler_util_max": summary.tiler_util_max,
                    "last_submit_pid_top": list(summary.last_submit_pid_top),
                    "proc_pid": summary.proc_pid,
                    "proc_gpu_time_util_est": None
                    if summary.proc_gpu_time_util_est is None
                    else round(float(summary.proc_gpu_time_util_est), 2),
                }
            except Exception as e:
                logger.warning(f"inventory_cli:main: {e}")

        out = getattr(args, "output", "") or str(REPO_ROOT / "artifacts" / "inventory_meta_coverage.json")
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
        _maybe_print_taichi_kernel_profile(
            requested=bool(getattr(args, "profile", False) or env_flag("TAICHI_KERNEL_PROFILER_PRINT"))
        )

    except KeyboardInterrupt:
        print("\nCancelled by user.")
        return 0
    except Exception as exc:
        print(f"\nFatal Error: {exc}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
