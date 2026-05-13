"""
Validation utility: compare GPU-native GA evaluation vs the proven solve_genomes_with_ftff() path.

Goal:
  Catch scoring mismatches (score inflation/deflation) caused by:
  - wrong p_val/s_val aggregation
  - wrong color flag mapping
  - bugs in solve_genomes_with_ftff_kernel (GPU-native evaluator)

Usage:
  python tools/validate_gpu_native_eval.py --song "Data/Hard/Feeling Alright (Hard) by Rutra.txt" --n 32
"""

from __future__ import annotations

import argparse
import configparser
import random
from pathlib import Path

import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gear_optimizer.core.config import load_paths_cache
from gear_optimizer.core.constants import (
    TOTAL_GEM_BUDGET,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_ROWS,
)
from gear_optimizer.core.utils import safe_int
from gear_optimizer.data.csv_parser import load_all_gears_list, load_all_minis_list, read_table
from gear_optimizer.helpers.song_helpers import setup_song_config
from gear_optimizer.pipeline.song_processor import read_song_file
from gear_optimizer.helpers.ga_helpers import initialize_pools
from gear_optimizer.solver.item_registry import ItemRegistry
from gear_optimizer.solver.taichi_gem import api as gpu_api
from gear_optimizer.solver.taichi_gem import fields as gpu_fields
from gear_optimizer.solver.scoring import solve_best_fever_combination


def _disable_inputs_to_prevent_taint(cfg: configparser.ConfigParser) -> None:
    if not cfg.has_section("UserInputStatsGems"):
        cfg.add_section("UserInputStatsGems")
    for key in ["perfect_points", "combo_multiplier", "fever_multiplier", "fever_fill", "fever_time"]:
        cfg.set("UserInputStatsGems", key, "0")

    if not cfg.has_section("ElementalGems"):
        cfg.add_section("ElementalGems")
    for key in ["Chill", "Flow", "Rush", "Beat", "Vibe"]:
        cfg.set("ElementalGems", key, "0")


def _build_ref_arrays(stats_table: list[list[float]]) -> dict[str, np.ndarray]:
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
        for v in range(TOTAL_ROWS + 1):
            lookup_index = TOTAL_ROWS - v
            try:
                val = stats_table[lookup_index][i] if stats_table else 0.0
            except Exception:
                val = 0.0
            tmp.append(val)
        ref_arrays[name] = np.array(tmp, dtype=np.float64)
    return ref_arrays


def _flags_for_song(calc_song: dict, selected_color: str) -> dict[str, int]:
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    return {
        "is_p_ft": 1 if p_color == "Beat" else 0,
        "is_s_ft": 1 if s_color == "Beat" else 0,
        "is_p_ff": 1 if p_color == "Vibe" else 0,
        "is_s_ff": 1 if s_color == "Vibe" else 0,
        "is_p_pp": 1 if p_color == "Chill" else 0,
        "is_s_pp": 1 if s_color == "Chill" else 0,
        "is_p_cm": 1 if p_color == "Flow" else 0,
        "is_s_cm": 1 if s_color == "Flow" else 0,
        "is_p_fm": 1 if p_color == "Rush" else 0,
        "is_s_fm": 1 if s_color == "Rush" else 0,
        "is_p_ov": 1 if selected_color == p_color else 0,
        "is_s_ov": 1 if selected_color == s_color else 0,
    }


def _aggregate_genome_stats_for_solve_with_ftff(
    genome: list[dict],
    *,
    base_stats_fixed: dict,
    cfg_data: dict,
    calc_song: dict,
) -> dict:
    from gear_optimizer.core.utils import SKIP_ITEM_KEYS

    stats = base_stats_fixed.copy()
    for item in genome:
        for k, v in item.items():
            if k not in SKIP_ITEM_KEYS:
                stats[k] = stats.get(k, 0) + v

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    sel_color = cfg_data["selected_color"]

    user_ft = cfg_data["user_ft"]
    user_ff = cfg_data["user_ff"]
    user_pp = cfg_data["user_pp"]
    user_cm = cfg_data["user_cm"]
    user_fm = cfg_data["user_fm"]
    static_elem_input = cfg_data["static_elem_input"]

    base_pp = stats.get("Perfect Points", 0) - user_pp * GEM_SCALE_NORMAL
    base_cm = stats.get("Combo Multiplier", 0) - user_cm * GEM_SCALE_NORMAL
    base_fm = stats.get("Fever Multiplier", 0) - user_fm * GEM_SCALE_FEVER
    base_ft_stat = stats.get("Fever Time", 0) - user_ft * GEM_SCALE_FEVER
    base_ff_stat = stats.get("Fever Fill Rate", 0) - user_ff * GEM_SCALE_FEVER

    base_beat = stats.get("Beat", 0) - user_ft * GEM_STAT_TO_ELEMENT_SCALE
    base_vibe = stats.get("Vibe", 0) - user_ff * GEM_STAT_TO_ELEMENT_SCALE
    base_rush = stats.get("Rush", 0) - user_fm * GEM_STAT_TO_ELEMENT_SCALE
    base_flow = stats.get("Flow", 0) - user_cm * GEM_STAT_TO_ELEMENT_SCALE
    base_chill = stats.get("Chill", 0) - user_pp * GEM_STAT_TO_ELEMENT_SCALE

    if static_elem_input:
        if sel_color == "Beat":
            base_beat -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Vibe":
            base_vibe -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Rush":
            base_rush -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Flow":
            base_flow -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Chill":
            base_chill -= static_elem_input * ELEMENTAL_GEM_SCALE

    color_vals = {
        "Beat": base_beat,
        "Vibe": base_vibe,
        "Rush": base_rush,
        "Flow": base_flow,
        "Chill": base_chill,
    }
    base_p_val = color_vals.get(p_color, 0)
    base_s_val = color_vals.get(s_color, 0)

    return {
        "base_pp": int(base_pp),
        "base_cm": int(base_cm),
        "base_fm": int(base_fm),
        "base_p_val": int(base_p_val),
        "base_s_val": int(base_s_val),
        "base_ft_stat": int(base_ft_stat),
        "base_ff_stat": int(base_ff_stat),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--song", required=True, help="Path to the song .txt file")
    parser.add_argument("--n", type=int, default=32, help="Population size")
    parser.add_argument("--seed", type=int, default=123, help="RNG seed")
    args = parser.parse_args()

    rng = random.Random(args.seed)

    cfg = configparser.ConfigParser()
    cfg.read("config.ini", encoding="utf-8")

    # Mirror app.py behavior: prevent DB tainting from manual gems.
    _disable_inputs_to_prevent_taint(cfg)

    # Load paths + data tables
    paths = load_paths_cache()
    all_gears = load_all_gears_list(paths)
    all_minis = load_all_minis_list(paths)
    gears_by_name = {g.get("Name", ""): g for g in all_gears if g.get("Name")}
    minis_by_name = {m.get("Name", ""): m for m in all_minis if m.get("Name")}

    stats_table = read_table(paths.get("Stats", ""))
    ref_arrays = _build_ref_arrays(stats_table)

    # Load song file
    fp = Path(args.song)
    song_data = read_song_file(str(fp))
    calc_song = {
        "metadata": song_data["song_details"],
        "song_data": {"timestamps": np.array(song_data["timestamps"], dtype=np.float64)},
    }

    auto_buff = True
    (
        _ga_settings,
        fixed_stats,
        _current_gear_stats,
        _current_gear_list,
        _current_mini_stats,
        _current_mini_list,
        *_rest,
    ) = setup_song_config(cfg, calc_song, auto_buff, paths, gears_by_name, minis_by_name)

    slots = ["Hat", "Neck", "Face", "Shirt", "Back", "Pants"]
    p_color = calc_song["metadata"].get("Primary Color", "Rush")
    selected_color = p_color

    gear_pool, mini_pool, *_ = initialize_pools(all_gears, all_minis, p_color, slots)
    if gear_pool is None or not mini_pool:
        raise RuntimeError("Failed to build item pools")

    # Build population (ensure minis unique per genome)
    population: list[list[dict]] = []
    for _ in range(int(args.n)):
        genome = [rng.choice(gear_pool[s]) for s in slots]
        minis = rng.sample(mini_pool, 3) if len(mini_pool) >= 3 else [rng.choice(mini_pool) for _ in range(3)]
        genome.extend(minis)
        population.append(genome)

    cfg_data = {
        "selected_color": selected_color,
        "use_gpu": True,  # reference path uses solve_genomes_with_ftff
        "user_ft": safe_int(cfg.get("UserInputStatsGems", "fever_time", fallback=0)),
        "user_ff": safe_int(cfg.get("UserInputStatsGems", "fever_fill", fallback=0)),
        "user_pp": safe_int(cfg.get("UserInputStatsGems", "perfect_points", fallback=0)),
        "user_cm": safe_int(cfg.get("UserInputStatsGems", "combo_multiplier", fallback=0)),
        "user_fm": safe_int(cfg.get("UserInputStatsGems", "fever_multiplier", fallback=0)),
        "static_elem_input": safe_int(cfg.get("ElementalGems", selected_color, fallback=0)),
    }

    flags = _flags_for_song(calc_song, selected_color)

    # Reference: solve_genomes_with_ftff (known-good kernel path)
    gpu_api.load_ref_arrays(ref_arrays)
    genome_stats_list = [
        _aggregate_genome_stats_for_solve_with_ftff(
            g, base_stats_fixed=fixed_stats, cfg_data=cfg_data, calc_song=calc_song
        )
        for g in population
    ]
    ref_results = gpu_api.solve_genomes_with_ftff(
        genome_stats_list,
        calc_song,
        flags["is_p_ft"],
        flags["is_s_ft"],
        flags["is_p_ff"],
        flags["is_s_ff"],
        flags["is_p_pp"],
        flags["is_s_pp"],
        flags["is_p_cm"],
        flags["is_s_cm"],
        flags["is_p_fm"],
        flags["is_s_fm"],
        flags["is_p_ov"],
        flags["is_s_ov"],
        ref_arrays,
        total_budget=TOTAL_GEM_BUDGET,
        gem_scale_fever=GEM_SCALE_FEVER,
        song_slot=0,
    )

    # GPU-native: aggregate + solve_genomes_with_ftff_kernel
    registry = ItemRegistry(gear_pool, mini_pool, slots)
    gpu_data = registry.to_gpu_arrays()
    gpu_api.ga_upload_item_stats(gpu_data["item_stats"], gpu_data["slot_start"], gpu_data["slot_count"])

    base_stats_arr = np.array(
        [
            fixed_stats.get("Perfect Points", 0),
            fixed_stats.get("Combo Multiplier", 0),
            fixed_stats.get("Fever Multiplier", 0),
            fixed_stats.get("Fever Time", 0),
            fixed_stats.get("Fever Fill Rate", 0),
            fixed_stats.get("Beat", 0),
            fixed_stats.get("Vibe", 0),
            fixed_stats.get("Rush", 0),
            fixed_stats.get("Flow", 0),
            fixed_stats.get("Chill", 0),
        ],
        dtype=np.int32,
    )

    # Same deductions as scoring.solve_best_fever_combination()
    user_pp = int(cfg_data["user_pp"])
    user_cm = int(cfg_data["user_cm"])
    user_fm = int(cfg_data["user_fm"])
    user_ft = int(cfg_data["user_ft"])
    user_ff = int(cfg_data["user_ff"])
    static_elem_input = int(cfg_data["static_elem_input"])

    base_stats_arr[0] -= user_pp * GEM_SCALE_NORMAL
    base_stats_arr[1] -= user_cm * GEM_SCALE_NORMAL
    base_stats_arr[2] -= user_fm * GEM_SCALE_FEVER
    base_stats_arr[3] -= user_ft * GEM_SCALE_FEVER
    base_stats_arr[4] -= user_ff * GEM_SCALE_FEVER

    base_stats_arr[9] -= user_pp * GEM_STAT_TO_ELEMENT_SCALE
    base_stats_arr[8] -= user_cm * GEM_STAT_TO_ELEMENT_SCALE
    base_stats_arr[7] -= user_fm * GEM_STAT_TO_ELEMENT_SCALE
    base_stats_arr[5] -= user_ft * GEM_STAT_TO_ELEMENT_SCALE
    base_stats_arr[6] -= user_ff * GEM_STAT_TO_ELEMENT_SCALE

    if static_elem_input:
        color_to_idx = {"Beat": 5, "Vibe": 6, "Rush": 7, "Flow": 8, "Chill": 9}
        idx = color_to_idx.get(selected_color)
        if idx is not None:
            base_stats_arr[idx] -= static_elem_input * ELEMENTAL_GEM_SCALE

    gpu_api.ga_upload_base_fixed_stats(base_stats_arr)
    pop_ids = registry.encode_population(population)
    gpu_api.ga_upload_population_indices(pop_ids, n_slots=9)

    # Ensure timeline grid is present (song_slot=0)
    gpu_api.precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)
    gpu_api.ga_evaluate_population(
        n_genomes=len(population),
        n_slots=9,
        total_budget=TOTAL_GEM_BUDGET,
        gem_scale_fever=GEM_SCALE_FEVER,
        song_slot=0,
        **flags,
    )
    native_results = gpu_api.ga_download_results(len(population))

    # Sanity-check: compare genome_base_stats used by GPU-native evaluation vs expected base stats.
    expected_base = np.zeros((len(population), 7), dtype=np.int32)
    for i, st in enumerate(genome_stats_list):
        expected_base[i, 0] = int(st["base_pp"])
        expected_base[i, 1] = int(st["base_cm"])
        expected_base[i, 2] = int(st["base_fm"])
        expected_base[i, 3] = int(st["base_p_val"])
        expected_base[i, 4] = int(st["base_s_val"])
        expected_base[i, 5] = int(st["base_ft_stat"])
        expected_base[i, 6] = int(st["base_ff_stat"])

    native_base = gpu_fields.genome_base_stats.to_numpy()[: len(population)]
    base_mism = np.nonzero((native_base != expected_base).any(axis=1))[0]
    if base_mism.size:
        print(f"[BASE_MISMATCH] {base_mism.size}/{len(population)} genome_base_stats rows differ (showing up to 5)")
        for idx in base_mism[:5]:
            print(
                f" idx={int(idx)} expected={tuple(map(int, expected_base[idx]))} native={tuple(map(int, native_base[idx]))}"
            )

    # Compare
    mismatches = 0
    worst_delta = 0
    mismatch_indices: list[int] = []
    for i, (ref_row, nat_row) in enumerate(zip(ref_results, native_results)):
        ref_score = int(ref_row[0])
        nat_score = int(nat_row[0])
        delta = nat_score - ref_score
        if delta != 0:
            mismatches += 1
            worst_delta = max(worst_delta, abs(delta))
            mismatch_indices.append(int(i))
            if mismatches <= 10:
                print(f"[MISMATCH #{mismatches}] idx={i} ref={ref_row} native={tuple(map(int, nat_row))} delta={delta}")

    if mismatches:
        # Spot-check against CPU solver for the first mismatch to identify which path is wrong.
        from gear_optimizer.core.utils import SKIP_ITEM_KEYS

        cfg_cpu = dict(cfg_data)
        cfg_cpu["use_gpu"] = False

        for idx in mismatch_indices[:3]:
            genome = population[idx]
            full_stats = fixed_stats.copy()
            for item in genome:
                for k, v in item.items():
                    if k not in SKIP_ITEM_KEYS:
                        full_stats[k] = full_stats.get(k, 0) + v

            cpu_res = solve_best_fever_combination(
                None,
                full_stats,
                calc_song,
                ref_arrays,
                silent=True,
                override_cfg=cfg_cpu,
            )
            cpu_score = int(cpu_res.get("Score", -1))
            ref_score = int(ref_results[idx][0])
            nat_score = int(native_results[idx][0])
            print(f"[CPU CHECK] idx={idx} cpu={cpu_score} ref_parallel={ref_score} native={nat_score}")

        print(f"FAIL: {mismatches}/{len(population)} mismatches (worst abs delta={worst_delta})")
        return 1

    print(f"OK: {len(population)}/{len(population)} match (solve_genomes_with_ftff == GPU-native)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
