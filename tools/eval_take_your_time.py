"""
Quick repro utility for investigating score plateaus.

Evaluates two known loadouts for:
  - Data/Hard/Take Your Time (Hard) by Rutra.txt

Prints CPU vs GPU scores and gem allocations so we can confirm:
  - Whether 21,255,624 is still achievable with current data/scoring
  - Whether the GPU evaluator matches CPU (parity)
"""

from __future__ import annotations

import configparser
import os
import sys

import numpy as np

# Ensure repo root is on sys.path so `import gear_optimizer` works when running
# this file directly (python tools/eval_take_your_time.py).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.core.constants import TOTAL_ROWS
from gear_optimizer.data.csv_parser import (
    get_fixed_stats,
    load_all_gears_list,
    load_all_minis_list,
    read_table,
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


def _preload_ref_arrays(stats_table: list[list[float]]) -> dict[str, np.ndarray]:
    stat_names = [
        "Perfect Points",
        "Combo Multiplier",
        "Fever Multiplier",
        "Fever Fill Rate",
        "Fever Time",
    ]
    ref_arrays: dict[str, np.ndarray] = {}
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
    return ref_arrays


def _eval_loadout(
    *,
    gears_by_name: dict,
    minis_by_name: dict,
    fixed_stats: dict,
    calc_song: dict,
    ref_arrays: dict,
    selected_color: str,
    gear_names: list[str],
    mini_names: list[str],
    use_gpu: bool,
) -> dict:
    cfg_data = {
        "selected_color": selected_color,
        "use_gpu": use_gpu,
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
    }

    genome = [gears_by_name[n] for n in gear_names] + [minis_by_name[n] for n in mini_names]

    GEM_SOLVER_CACHE.clear()
    FG_CACHE.clear()
    FEVER_TIMELINE_CACHE.clear()

    return worker_coevolution_evaluate((genome, fixed_stats, cfg_data, calc_song, ref_arrays))


def _print_result(tag: str, res: dict) -> None:
    data = res.get("Data") or {}
    gems = data.get("GemCounts") or data.get("gem_counts") or {}
    print(f"\n[{tag}]")
    print(f"Score: {res.get('Score'):,}")
    print(
        "Gems:",
        f"FT={data.get('FT', data.get('FT_gems', '?'))},",
        f"FF={data.get('FF', data.get('FF_gems', '?'))},",
        f"PP={gems.get('Perfect Points', '?')},",
        f"CM={gems.get('Combo Multiplier', '?')},",
        f"FM={gems.get('Fever Multiplier', '?')},",
        f"OV={gems.get('Element', gems.get('Overflow', '?'))}",
    )


def main() -> None:
    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8-sig")

    paths = load_paths_cache()
    stats_table = read_table(paths.get("Stats", ""))

    # Keep behavior consistent with MetaFinder runs: ignore manual gem inputs.
    _disable_inputs_to_prevent_taint(cfg)

    # Load song
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

    ref_arrays = _preload_ref_arrays(stats_table)
    fixed_stats = get_fixed_stats(cfg)

    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g["Name"]: g for g in all_gears}
    minis_by_name = {m["Name"]: m for m in all_minis}

    # Loadouts to compare
    loadouts = [
        (
            "DB_record_21255624",
            [
                "Autumnal Adept's Bloom",
                "Legendary Vibe Ringleader's Necktie",
                "Legendary Rebel's Mask",
                "Legendary Marshall's Coat",
                "No-Scope Loadout",
                "Legendary Rebel's Trousers",
            ],
            ["YooH", "HyuN", "Apocalypse Survivor Starlet"],
        ),
        (
            "Plateau_21201424",
            [
                "Autumnal Adept's Bloom",
                "Legendary Rebel's Scarf",
                "Legendary Marshall's Mask",
                "Legendary Marshall's Coat",
                "Legendary Rebel's Sash",
                "Legendary Rebel's Trousers",
            ],
            ["DJ Hiku: Party Mode", "YooH", "Apocalypse Survivor Starlet"],
        ),
    ]

    print(f"Song: {calc_song['metadata'].get('Song Name')} ({calc_song['metadata'].get('Difficulty')})")
    print(f"Primary Color: {p_col}")

    for tag, gear_names, mini_names in loadouts:
        cpu = _eval_loadout(
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            fixed_stats=fixed_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            selected_color=p_col,
            gear_names=gear_names,
            mini_names=mini_names,
            use_gpu=False,
        )
        _print_result(f"{tag} CPU", cpu)

        gpu = _eval_loadout(
            gears_by_name=gears_by_name,
            minis_by_name=minis_by_name,
            fixed_stats=fixed_stats,
            calc_song=calc_song,
            ref_arrays=ref_arrays,
            selected_color=p_col,
            gear_names=gear_names,
            mini_names=mini_names,
            use_gpu=True,
        )
        _print_result(f"{tag} GPU", gpu)


if __name__ == "__main__":
    main()


