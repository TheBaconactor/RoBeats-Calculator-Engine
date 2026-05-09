"""Verify exact skyline solver against GA on a real song.

Runs both:
- `solve_coevolution_genetic` (GA)
- `solve_exact_skyline` (exact DP+skyline+GPU scoring)

and asserts `exact_score >= ga_score` under the same inputs.

Usage:
  python tools/verify/verify_exact_skyline_vs_ga.py \
    --song "Data/Hard/00 (Hard) by garlagan.txt" \
    --ga-depth 25 --ga-seed 123
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

# Ensure we can import gear_optimizer when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def _disable_inputs_to_prevent_taint(cfg) -> None:
    if not cfg.has_section("UserInputStatsGems"):
        cfg.add_section("UserInputStatsGems")
    for key in ["perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"]:
        cfg.set("UserInputStatsGems", key, "0")

    if not cfg.has_section("ElementalGems"):
        cfg.add_section("ElementalGems")
    for key in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
        cfg.set("ElementalGems", key, "0")


def _build_ref_arrays(stats_table: list[list[float]]) -> dict[str, np.ndarray]:
    from gear_optimizer.core.constants import TOTAL_ROWS

    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--song",
        default="Data/Hard/00 (Hard) by garlagan.txt",
        help="Path to the song .txt file",
    )
    parser.add_argument("--ga-depth", type=int, default=25, help="GA generation depth")
    parser.add_argument("--ga-seed", type=int, default=123, help="Deterministic GA seed")
    parser.add_argument(
        "--disable-hitsim",
        action="store_true",
        help="Disable HumanHitSim for determinism (recommended)",
    )
    args = parser.parse_args()

    from gear_optimizer.core.config import load_config, load_paths_cache
    from gear_optimizer.core.utils import cfg_to_dict
    from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
    from gear_optimizer.helpers.song_helpers import setup_song_config
    from gear_optimizer.pipeline.song_processor import clone_calc_song, get_base_calc_song
    from gear_optimizer.solver.exact_skyline import solve_exact_skyline
    from gear_optimizer.solver.genetic import solve_coevolution_genetic

    cfg = load_config("config.ini")

    # Force GPU usage (GPU-only policy).
    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")
    cfg.set("IterationEngine", "GPU_Mode", "true")
    cfg.set("IterationEngine", "GPU_Native_GA", "true")

    if args.disable_hitsim:
        if not cfg.has_section("HumanHitSim"):
            cfg.add_section("HumanHitSim")
        cfg.set("HumanHitSim", "Enabled", "false")
        cfg.set("HumanHitSim", "Seed", "1")

    # Mirror app.py auto-mode behavior: prevent DB tainting from manual gems.
    if cfg.getboolean("IterationEngine", "MetaFinder", fallback=False):
        _disable_inputs_to_prevent_taint(cfg)

    paths = load_paths_cache() or {}

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g.get("Name", ""): g for g in all_gears if g.get("Name")}
    minis_by_name = {m.get("Name", ""): m for m in all_minis if m.get("Name")}

    stats_table = read_table(str(paths.get("Stats", "") or ""))
    ref_arrays = _build_ref_arrays(stats_table)

    cfg_dict = cfg_to_dict(cfg)

    fp = str(args.song)
    base_calc = get_base_calc_song(fp, cfg_dict)
    calc_song = clone_calc_song(base_calc)

    song_data = calc_song.get("song_data", {}) or {}
    if "chart_timestamps" not in song_data and song_data.get("timestamps") is not None:
        song_data["chart_timestamps"] = np.asarray(song_data.get("timestamps"), dtype=np.float32)

    auto_buff = cfg.getboolean("IterationEngine", "AutoSelectBuffAndColor", fallback=False)
    (
        ga_settings,
        fixed_stats,
        _current_gear_stats,
        _current_gear_list,
        _current_mini_stats,
        _current_mini_list,
        *_rest,
    ) = setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name)

    def status(msg: str) -> None:
        print(msg)

    t0 = time.perf_counter()
    ga_best_data, *_rest_ga = solve_coevolution_genetic(
        cfg,
        fixed_stats,
        paths,
        calc_song,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        optimize_gear=True,
        optimize_minis=True,
        fixed_gear=None,
        fixed_minis=None,
        ga_depth=int(args.ga_depth),
        db_seed=None,
        ga_settings=ga_settings,
        status_cb=status,
        executor=None,
        known_loadouts=None,
        song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
        ga_seed=int(args.ga_seed),
    )
    ga_s = int((ga_best_data or {}).get("BaseScore") or (ga_best_data or {}).get("Score") or 0)

    exact_best_data, *_rest_exact = solve_exact_skyline(
        cfg,
        fixed_stats,
        paths,
        calc_song,
        ref_arrays,
        all_gears,
        all_minis,
        gears_by_name,
        minis_by_name,
        optimize_gear=True,
        optimize_minis=True,
        fixed_gear=None,
        fixed_minis=None,
        ga_depth=int(args.ga_depth),
        db_seed=None,
        ga_settings=ga_settings,
        status_cb=status,
        executor=None,
        known_loadouts=None,
        song_slot=int(calc_song.get("_gpu_song_slot", 0) or 0),
        ga_seed=int(args.ga_seed),
    )
    exact_s = int((exact_best_data or {}).get("BaseScore") or (exact_best_data or {}).get("Score") or 0)

    dt = time.perf_counter() - t0

    print("\n=== Results ===")
    print(f"GA BaseScore:    {ga_s}")
    print(f"Exact BaseScore: {exact_s}")
    print(f"Wall time:       {dt:.2f}s")

    if ga_best_data:
        print(f"GA Gear:   {ga_best_data.get('GearNames')}")
        print(f"GA Minis:  {ga_best_data.get('MiniNames')}")
    if exact_best_data:
        print(f"Exact Gear:{exact_best_data.get('GearNames')}")
        print(f"Exact Minis:{exact_best_data.get('MiniNames')}")

    out = {
        "song": fp,
        "ga_seed": int(args.ga_seed),
        "ga_depth": int(args.ga_depth),
        "ga_score": int(ga_s),
        "exact_score": int(exact_s),
        "elapsed_s": float(dt),
    }
    try:
        os.makedirs("artifacts", exist_ok=True)
        out_path = Path("artifacts") / "verify_exact_skyline_vs_ga.json"
        out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")
    except Exception:
        pass

    if exact_s < ga_s:
        print("FAIL: exact skyline is worse than GA")
        return 1

    print("OK: exact skyline >= GA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
