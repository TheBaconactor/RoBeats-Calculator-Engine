"""Skyline single-song experiment harness.

Runs exact skyline + GA on one song and produces an authoritative comparison
along with stage-level timing breakdowns.

Usage:
  python tools/experiments/skyline_single_song.py [--song SONG_PATH] [--depth N] [--seed N]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _build_ref_arrays(stats_table: list[list[float]]) -> dict[str, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS
    stat_names = ["Perfect Points", "Combo Multiplier", "Fever Multiplier", "Fever Fill Rate", "Fever Time"]
    ref_arrays: dict[str, np.ndarray] = {}
    for i, name in enumerate(stat_names):
        tmp: list[float] = []
        for v in range(int(TOTAL_ROWS) + 1):
            lookup_index = int(TOTAL_ROWS) - int(v)
            try:
                val = float(stats_table[lookup_index][i]) if stats_table else 0.0
            except Exception:
                val = 0.0
            tmp.append(val)
        ref_arrays[name] = np.asarray(tmp, dtype=np.float32)
    return ref_arrays


def _disable_manual_gems(cfg) -> None:
    if not cfg.has_section("UserInputStatsGems"):
        cfg.add_section("UserInputStatsGems")
    for key in ["perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"]:
        cfg.set("UserInputStatsGems", key, "0")

    if not cfg.has_section("ElementalGems"):
        cfg.add_section("ElementalGems")
    for key in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
        cfg.set("ElementalGems", key, "0")


def _print_stage(name: str, stats: dict[str, int | float]) -> None:
    parts = [f"  {name}:"]
    for k, v in stats.items():
        if isinstance(v, float):
            parts.append(f"{k}={v:.3f}")
        elif isinstance(v, int) and v > 10_000:
            parts.append(f"{k}={v:,}")
        else:
            parts.append(f"{k}={v}")
    print("  ".join(parts))


def main() -> int:
    parser = argparse.ArgumentParser(description="Skyline single-song experiment")
    parser.add_argument("--song", default="Data/Hard/00 (Hard) by garlagan.txt")
    parser.add_argument("--ga-depth", type=int, default=25)
    parser.add_argument("--ga-seed", type=int, default=123)
    parser.add_argument("--fix-minis", action="store_true", default=False, help="Fix minis for faster skyline (debug only)")
    parser.add_argument("--no-fix-minis", dest="fix_minis", action="store_false")
    args = parser.parse_args()

    from gear_optimizer.core.config import load_config, load_paths_cache
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
    from gear_optimizer.helpers.song_helpers import setup_song_config
    from gear_optimizer.helpers.ga_helpers import initialize_pools
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.exact_skyline import solve_exact_skyline
    from gear_optimizer.solver.fg_exact_dp import (
        prepare_force_greats_exact_dp_inputs,
        score_force_greats_exact_dp_bonus_from_prepared,
        solve_force_greats_exact_dp,
    )
    from gear_optimizer.solver.genetic import solve_coevolution_genetic

    cfg = load_config("config.ini")

    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "GPU_Mode", "true")
    cfg.set("IterationEngine", "GPU_Native_GA", "true")

    if not cfg.has_section("HumanHitSim"):
        cfg.add_section("HumanHitSim")
    cfg.set("HumanHitSim", "Enabled", "false")
    cfg.set("HumanHitSim", "Seed", "1")

    _disable_manual_gems(cfg)

    paths = load_paths_cache() or {}

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g.get("Name", ""): g for g in all_gears if g.get("Name")}
    minis_by_name = {m.get("Name", ""): m for m in all_minis if m.get("Name")}

    stats_table = read_table(str(paths.get("Stats", "") or ""))
    ref_arrays = _build_ref_arrays(stats_table)

    cfg_dict = cfg_to_dict(cfg)
    base_calc_song = get_base_calc_song(str(args.song), cfg_dict)
    calc_song = clone_calc_song(base_calc_song)

    song_data = calc_song.get("song_data", {}) or {}
    if "chart_timestamps" not in song_data and song_data.get("timestamps") is not None:
        song_data["chart_timestamps"] = np.asarray(song_data.get("timestamps"), dtype=np.float32)

    auto_buff = cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False)
    ga_settings, fixed_stats, *_ = setup_song_config(
        cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name
    )

    p_color = str((calc_song or {}).get("metadata", {}).get("Primary Color", "Rush") or "Rush")
    s_color = str((calc_song or {}).get("metadata", {}).get("Secondary Color", "") or "")
    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    _gear_pool, mini_pool, *_ = initialize_pools(all_gears, all_minis, p_color, slots, s_color=s_color)

    fixed_minis: list[dict] | None = None
    if args.fix_minis and mini_pool and len(mini_pool) >= 3:
        fixed_minis = sorted(list(mini_pool), key=lambda m: str(m.get("Name", "") or ""))[:3]

    song_slot = int(calc_song.get("_gpu_song_slot", 0) or 0)

    print("=" * 72)
    print(f"Skyline Single-Song Experiment")
    print(f"  Song: {args.song}")
    print(f"  GA Depth: {args.ga_depth}  GA Seed: {args.ga_seed}")
    print(f"  Fix Minis: {args.fix_minis}")
    print(f"  Gear items: {len(all_gears)}  Mini items: {len(all_minis)}")
    print(f"  GPU Song Slot: {song_slot}")
    print("=" * 72)

    def status(msg: str) -> None:
        print(f"  [{time.perf_counter():.1f}] {msg}")

    # --- GA baseline ---
    print("\n--- GA Baseline ---")
    t0 = time.perf_counter()
    ga_best_data, *_ = solve_coevolution_genetic(
        cfg, fixed_stats, paths, calc_song, ref_arrays, all_gears, all_minis,
        gears_by_name, minis_by_name,
        optimize_gear=True,
        optimize_minis=not bool(fixed_minis),
        fixed_gear=None,
        fixed_minis=fixed_minis,
        ga_depth=int(args.ga_depth),
        db_seed=None,
        ga_settings=ga_settings,
        status_cb=lambda _m: None,
        executor=None,
        known_loadouts=None,
        song_slot=song_slot,
        ga_seed=int(args.ga_seed),
    )
    ga_time = time.perf_counter() - t0
    ga_score = int((ga_best_data or {}).get("BaseScore") or (ga_best_data or {}).get("Score") or 0)

    ga_fg_delta = 0
    ga_post_stats = (ga_best_data or {}).get("Stats") or (ga_best_data or {}).get("Details", {}).get("Stats", {}) or {}
    if ga_post_stats:
        try:
            ga_dp = solve_force_greats_exact_dp(
                stats=ga_post_stats, calc_song=calc_song, ref_arrays=ref_arrays, mode="timing_aware", prune=True,
            )
            if ga_dp.best_delta > 0:
                prepared = prepare_force_greats_exact_dp_inputs(
                    stats=ga_post_stats, calc_song=calc_song, ref_arrays=ref_arrays,
                )
                if prepared is not None:
                    baseline_bonus = score_force_greats_exact_dp_bonus_from_prepared(
                        prepared=prepared, section_counts=[],
                    )
                    ga_fg_delta = max(0, int(ga_dp.best_delta) - int(baseline_bonus))
        except Exception:
            ga_fg_delta = 0

    print(f"  GA Score: {ga_score:,}  FG Delta: {ga_fg_delta:,}  Time: {ga_time:.2f}s")

    # --- Exact Skyline ---
    print("\n--- Exact Skyline ---")
    t0 = time.perf_counter()
    exact_best_data, exact_gear, exact_minis, _, _, _, all_evaluated = solve_exact_skyline(
        cfg, fixed_stats, paths, calc_song, ref_arrays, all_gears, all_minis,
        gears_by_name, minis_by_name,
        optimize_gear=True,
        optimize_minis=not bool(fixed_minis),
        fixed_gear=None,
        fixed_minis=fixed_minis,
        ga_depth=int(args.ga_depth),
        db_seed=None,
        ga_settings=ga_settings,
        status_cb=status,
        executor=None,
        known_loadouts=None,
        song_slot=song_slot,
        ga_seed=int(args.ga_seed),
    )
    skyline_time = time.perf_counter() - t0
    exact_score = int((exact_best_data or {}).get("BaseScore") or (exact_best_data or {}).get("Score") or 0)

    print(f"\n  Skyline Base Score: {exact_score:,}  Time: {skyline_time:.2f}s")

    ga_fg_total = ga_score + ga_fg_delta
    ranked_skyline = sorted(
        all_evaluated,
        key=lambda e: int(e.get("BaseScore") or e.get("Score", 0) or 0) + int(e.get("FGDelta", 0) or 0),
        reverse=True,
    )
    best_skyline_entry = ranked_skyline[0] if ranked_skyline else {}
    best_skyline_base = int(best_skyline_entry.get("BaseScore") or best_skyline_entry.get("Score", 0) or 0)
    best_skyline_fg_delta = int(best_skyline_entry.get("FGDelta", 0) or 0)
    best_skyline_fg_total = best_skyline_base + best_skyline_fg_delta

    print("\n" + "=" * 72)
    print("Results")
    print("=" * 72)
    print(f"  GA base:  {ga_score:>10,}  (FG+{ga_fg_delta:,} = {ga_fg_total:,})  {ga_time:.2f}s")
    print(
        f"  Skyline:  {best_skyline_base:>10,}  "
        f"(FG+{best_skyline_fg_delta:,} = {best_skyline_fg_total:,})  {skyline_time:.2f}s"
    )
    if best_skyline_base != exact_score:
        print(f"  Note: base-only skyline winner was {exact_score:,}; best base+FG candidate has base {best_skyline_base:,}.")
    delta = best_skyline_fg_total - ga_fg_total
    print(f"  Delta:    {delta:>+10,}")
    print(f"  Skyline is {'authoritative' if best_skyline_fg_total >= ga_fg_total else 'worse than GA'}")

    if all_evaluated:
        print(f"\n  Top-5 skyline candidates by base+FG:")
        for i, entry in enumerate(ranked_skyline[:5]):
            gear_names = [g.get("Name", "?") for g in entry.get("Gear", [])]
            mini_names = [m.get("Name", "?") for m in entry.get("Minis", [])]
            fgd = int(entry.get("FGDelta", 0) or 0)
            bs = int(entry.get("BaseScore") or entry.get("Score", 0) or 0)
            total = bs + fgd
            if fgd > 0:
                print(f"    #{i+1}: Total={total:,}  Base={bs:,}  FG_delta={fgd:,}  Gear={gear_names}  Minis={mini_names}")
            else:
                print(f"    #{i+1}: Total={total:,}  Base={bs:,}  Gear={gear_names}  Minis={mini_names}")

    out = {
        "song": args.song,
        "ga_depth": int(args.ga_depth),
        "ga_seed": int(args.ga_seed),
        "ga_score": int(ga_score),
        "ga_fg_delta": int(ga_fg_delta),
        "ga_total_score": int(ga_fg_total),
        "ga_time_s": float(ga_time),
        "exact_score": int(exact_score),
        "skyline_best_base_fg_base_score": int(best_skyline_base),
        "skyline_best_fg_delta": int(best_skyline_fg_delta),
        "skyline_best_total_score": int(best_skyline_fg_total),
        "skyline_time_s": float(skyline_time),
        "delta": int(delta),
        "authoritative": bool(best_skyline_fg_total >= ga_fg_total),
    }

    try:
        os.makedirs("artifacts", exist_ok=True)
        out_path = Path("artifacts") / "skyline_single_song_experiment.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nWrote {out_path}")
    except Exception:
        pass

    return 0 if best_skyline_fg_total >= ga_fg_total else 1


if __name__ == "__main__":
    raise SystemExit(main())
