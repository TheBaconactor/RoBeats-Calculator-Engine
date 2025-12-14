"""
Re-seed the Evolution DB with the known 21,255,624 record loadout for:
  Take Your Time (Hard) by Rutra

This is useful when your current `evolution.db` no longer contains the record
(e.g. DB replaced/merged/cleared), causing GA runs to keep seeding from a lower
plateau instead.

The script:
  - Loads config.ini
  - Mirrors MetaFinder "anti-taint" behavior (forces manual gem inputs to 0)
  - Evaluates the known record loadout (GPU by default)
  - Saves it into the active Evolution DB
  - Prints the best score now stored for that song
"""

from __future__ import annotations

import configparser
import os
import sys
from typing import Any

import numpy as np

# Ensure repo root is on sys.path for direct execution.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.data.csv_parser import (
    get_fixed_stats,
    load_all_gears_list,
    load_all_minis_list,
    read_table,
)
from gear_optimizer.data.database import (
    get_best_loadouts,
    get_evolution_db_path,
    save_loadout_to_db,
)
from gear_optimizer.pipeline.song_processor import read_song_file
from gear_optimizer.solver.scoring import (
    FEVER_TIMELINE_CACHE,
    FG_CACHE,
    GEM_SOLVER_CACHE,
    worker_coevolution_evaluate,
)


def _disable_inputs_to_prevent_taint(cfg: configparser.ConfigParser) -> None:
    # Mirrors gear_optimizer.app.GearOptimizerApp._disable_inputs_to_prevent_taint
    if not cfg.has_section("UserInputStatsGems"):
        cfg.add_section("UserInputStatsGems")
    for key in [
        "perfect_points",
        "combo_multiplier",
        "fever_multiplier",
        "fever_fill",
        "fever_time",
    ]:
        cfg.set("UserInputStatsGems", key, "0")

    if not cfg.has_section("ElementalGems"):
        cfg.add_section("ElementalGems")
    for key in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
        cfg.set("ElementalGems", key, "0")


def _build_details(calc_song: dict[str, Any], eval_data: dict[str, Any]) -> dict[str, Any]:
    meta = calc_song.get("metadata") or {}
    return {
        "FT": eval_data.get("FT", 0),
        "FF": eval_data.get("FF", 0),
        "GemCounts": eval_data.get("GemCounts", {}),
        "Stats": eval_data.get("Stats", {}),
        "SelectedElement": eval_data.get("Selected Element", ""),
        "PrimaryColor": meta.get("Primary Color", ""),
        "SecondaryColor": meta.get("Secondary Color", ""),
        "Difficulty": meta.get("Difficulty", ""),
        "ForceGreats": eval_data.get("ForceGreats", {}) or {},
    }


def main() -> None:
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8-sig")
    paths = load_paths_cache()

    stats_table = read_table(paths.get("Stats", ""))

    # Match MetaFinder runs: ignore manual gem inputs.
    _disable_inputs_to_prevent_taint(cfg)

    # Match AutoSelectBuffAndColor behavior for this specific song (T5 + PrimaryColor)
    song_fp = "Data/Hard/Take Your Time (Hard) by Rutra.txt"
    song_data = read_song_file(song_fp)
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": np.array(song_data["timestamps"], dtype=np.float64)},
    }

    p_col = calc_song["metadata"].get("Primary Color", "Rush")
    if not cfg.has_section("TeamContributionBuffConstant"):
        cfg.add_section("TeamContributionBuffConstant")
    cfg.set("TeamContributionBuffConstant", "TeamColor", p_col)
    cfg.set("TeamContributionBuffConstant", "TeamBuff", "T5")

    fixed_stats = get_fixed_stats(cfg)

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    # Known record loadout
    gear_names = [
        "Autumnal Adept's Bloom",
        "Legendary Vibe Ringleader's Necktie",
        "Legendary Rebel's Mask",
        "Legendary Marshall's Coat",
        "No-Scope Loadout",
        "Legendary Rebel's Trousers",
    ]
    mini_names = ["YooH", "HyuN", "Apocalypse Survivor Starlet"]

    genome = [gears_by_name[n] for n in gear_names] + [minis_by_name[n] for n in mini_names]

    # Evaluate (GPU mode to match your main runs)
    cfg_data = {
        "selected_color": p_col,
        "use_gpu": True,
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    # Build ref arrays exactly like the app
    from gear_optimizer.core.constants import TOTAL_ROWS

    ref_arrays: dict[str, np.ndarray] = {}
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    for i, name in enumerate(stat_names):
        temp_list: list[float] = []
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0
            except Exception:
                val = 0
            temp_list.append(val)
        ref_arrays[name] = np.array(temp_list, dtype=np.float64)

    GEM_SOLVER_CACHE.clear()
    FG_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()

    res = worker_coevolution_evaluate((genome, fixed_stats, cfg_data, calc_song, ref_arrays))
    score = int(res.get("Score", 0))
    eval_data = res.get("Data") or {}
    details = _build_details(calc_song, eval_data)

    song_name = calc_song["metadata"].get("Song Name", "Take Your Time (Hard) by Rutra")
    print(f"[DB] Active DB path: {get_evolution_db_path()}")
    print(f"[Seed] Song: {song_name}")
    print(f"[Seed] Evaluated score: {score:,}")

    save_loadout_to_db(
        song_name=song_name,
        score=score,
        fg_score=0,
        gear=[gears_by_name[n] for n in gear_names],
        minis=[minis_by_name[n] for n in mini_names],
        details=details,
        force_data=None,
    )

    best = get_best_loadouts(song_name, limit=1, gears_by_name=gears_by_name, minis_by_name=minis_by_name)
    if best:
        print(f"[DB] Best now: {best[0].get('score', 0):,}")
    else:
        print("[DB] Best now: (no rows found?)")


if __name__ == "__main__":
    main()







