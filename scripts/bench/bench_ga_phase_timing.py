#!/usr/bin/env python
"""
Benchmark: GPU-Native GA Phase Timing

Runs a real GA optimization on one song and reports per-phase timing breakdown.
"""

import os
import sys
import time

# Enable phase timing before imports
os.environ["GPU_NATIVE_GA_PHASE_TIMING"] = "1"
os.environ["PERF_TIMING"] = "1"

# Disable HitSim for deterministic timing
os.environ["HITSIM_ENABLED"] = "0"

from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def main():
    from gear_optimizer.core.config import find_and_cache_paths, load_config
    from gear_optimizer.pipeline.song_processor import prepare_song_data
    from gear_optimizer.solver.taichi_gem.api import (
        ensure_ready,
        load_ref_arrays,
        precompute_timeline_gpu,
        ga_upload_item_stats,
        ga_upload_base_fixed_stats,
    )
    from gear_optimizer.solver.taichi_gem import fields as gpu_fields
    from gear_optimizer.solver import genetic

    print("=" * 70)
    print("GPU-Native GA Phase Timing Benchmark")
    print("=" * 70)
    print()

    # Load config
    config_path = project_root / "config.ini"
    if not config_path.exists():
        print(f"ERROR: Config not found at {config_path}")
        return

    config = load_config(str(config_path))
    paths = find_and_cache_paths()

    # Find a song
    hard_folder = paths.get("hard_folder")
    if not hard_folder or not Path(hard_folder).exists():
        print(f"ERROR: Hard folder not found")
        return

    song_files = list(Path(hard_folder).glob("*.txt"))
    if not song_files:
        print("ERROR: No songs found")
        return

    song_file = song_files[0]
    print(f"Song: {song_file.name}")
    print()

    # Prepare song data
    song_data = prepare_song_data(str(song_file), config, paths)
    if not song_data:
        print("ERROR: Failed to prepare song data")
        return

    calc_song = song_data["calc_song"]
    ref_arrays = song_data["ref_arrays"]
    cfg_data = song_data["cfg_data"]

    # Initialize GPU
    print("Initializing GPU...")
    ensure_ready(ref_arrays)
    load_ref_arrays(ref_arrays)

    # Precompute timeline
    print("Precomputing timeline...")
    precompute_timeline_gpu(calc_song, ref_arrays, song_slot=0)

    # Build item registry arrays
    from gear_optimizer.solver.genetic import _build_item_registry_arrays

    item_stats, slot_start, slot_count = _build_item_registry_arrays(
        song_data["candidate_gear"],
        song_data["candidate_minis"],
    )

    # Upload item stats
    ga_upload_item_stats(item_stats, slot_start, slot_count)

    # Build base fixed stats
    from gear_optimizer.solver.genetic import _build_base_fixed_stats_array

    base_fixed = _build_base_fixed_stats_array(cfg_data)
    ga_upload_base_fixed_stats(base_fixed)

    # Build color flags
    from gear_optimizer.solver.scoring.genome_evaluation import build_color_flags

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    sel_color = "Rush"  # default
    color_flags = build_color_flags(p_color, s_color, sel_color)

    # Run timed GA
    print()
    print("Running GPU-Native GA (1 run, 100 generations, 256 genomes)...")
    print("-" * 70)

    n_genomes = 256
    n_generations = 100
    num_runs = 1

    t_start = time.perf_counter()

    from gear_optimizer.solver.genetic import run_gpu_native_ga_runs_payload_prebuilt

    result = run_gpu_native_ga_runs_payload_prebuilt(
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        song_slot=0,
        item_stats=item_stats,
        slot_start=slot_start,
        slot_count=slot_count,
        base_fixed_stats_arr=base_fixed,
        n_generations=n_generations,
        num_runs=num_runs,
        n_genomes=n_genomes,
        color_flags=color_flags,
        cfg_data=cfg_data,
        ga_seed=42,
    )

    t_total = time.perf_counter() - t_start

    print("-" * 70)
    print(f"Total time: {t_total * 1000:.1f} ms")
    print(f"Per generation: {t_total * 1000 / n_generations:.2f} ms")
    print(f"Per genome-generation: {t_total * 1e6 / (n_generations * n_genomes):.2f} µs")
    print()

    # Report best score
    if result is not None and result.shape[0] > 0:
        # Result format: (runs, genomes, cols)
        best_score = int(result[0, :, 0].max())
        print(f"Best score found: {best_score:,}")


if __name__ == "__main__":
    main()
