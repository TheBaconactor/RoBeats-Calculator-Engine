"""
GPU Batch Profiling Script

Measures where time is actually spent during GPU batch evaluation.
Run this to identify the real bottleneck before optimizing.

Usage:
    python tests/profile_gpu_batch.py
"""

import numpy as np
import sys
import os
import time
import random

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.core.constants import TOTAL_ROWS


def create_mock_song(primary="Beat", secondary="Flow", num_notes=500):
    """Create a mock song with realistic note count."""
    timestamps = np.linspace(0, 120, num_notes).tolist()
    return {
        "metadata": {
            "Song Name": "Profile Test Song",
            "Difficulty": "Hard",
            "Primary Color": primary,
            "Secondary Color": secondary,
            "Long Notes": 10,
            "Last Note Time": 120.0,
            "Total Notes": num_notes,
        },
        "song_data": {"timestamps": timestamps},
    }


def create_mock_ref():
    """Create mock reference arrays."""
    rows = TOTAL_ROWS + 1
    return {
        "Perfect Points": np.linspace(1.0, 2.0, rows),
        "Combo Multiplier": np.linspace(1.0, 3.0, rows),
        "Fever Multiplier": np.linspace(1.0, 5.0, rows),
        "Fever Fill Rate": np.linspace(1.0, 2.0, rows),
        "Fever Time": np.linspace(1.0, 2.5, rows),
    }


def create_random_genome():
    """Create a genome with random stats (simulates different gear loadouts)."""
    return [{
        "Name": f"Mock_{random.randint(0, 10000)}",
        "Perfect Points": random.randint(0, 50),
        "Combo Multiplier": random.randint(0, 50),
        "Fever Multiplier": random.randint(0, 50),
        "Fever Fill Rate": random.randint(0, 50),
        "Fever Time": random.randint(0, 50),
        "Rush": random.randint(0, 100),
        "Flow": random.randint(0, 100),
        "Beat": random.randint(0, 100),
        "Vibe": random.randint(0, 100),
        "Chill": random.randint(0, 100),
    }]


def profile_batch_evaluation(population_size=500, num_iterations=3):
    """Profile the GPU batch evaluation with detailed timing."""
    
    from gear_optimizer.solver.scoring import batch_evaluate_genomes, GEM_SOLVER_CACHE
    from gear_optimizer.solver.fever_timeline import SONG_TIMELINE_GRIDS
    
    print("=" * 60)
    print(f"GPU Batch Profiling: {population_size} genomes, {num_iterations} iterations")
    print("=" * 60)
    
    # Setup
    ref_arrays = create_mock_ref()
    calc_song = create_mock_song()
    
    cfg_data = {
        "selected_color": "Beat",
        "use_gpu": True,
        "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
        "static_elem_input": 0,
    }
    
    base_stats_fixed = {
        "Perfect Points": 50, "Combo Multiplier": 50, "Fever Multiplier": 50,
        "Fever Fill Rate": 50, "Fever Time": 50,
        "Rush": 50, "Flow": 50, "Beat": 50, "Vibe": 50, "Chill": 50,
    }
    
    # Warm up (Taichi JIT compilation)
    print("\n[WARMUP] Compiling Taichi kernels...")
    warmup_pop = [create_random_genome() for _ in range(10)]
    t0 = time.perf_counter()
    batch_evaluate_genomes(warmup_pop, base_stats_fixed, cfg_data, calc_song, ref_arrays)
    warmup_time = time.perf_counter() - t0
    print(f"[WARMUP] First call (includes JIT): {warmup_time:.3f}s")
    
    # Clear caches to simulate fresh generation
    GEM_SOLVER_CACHE.clear()
    SONG_TIMELINE_GRIDS.clear()
    
    # Profile multiple iterations
    times = []
    
    for i in range(num_iterations):
        # Generate fresh population each time (simulate new GA generation)
        population = [create_random_genome() for _ in range(population_size)]
        
        # Clear gem solver cache (but NOT timeline grid - it's song-specific)
        GEM_SOLVER_CACHE.clear()
        
        t0 = time.perf_counter()
        results = batch_evaluate_genomes(population, base_stats_fixed, cfg_data, calc_song, ref_arrays)
        elapsed = time.perf_counter() - t0
        
        times.append(elapsed)
        print(f"[Iteration {i+1}] {elapsed:.3f}s ({len(results)} results)")
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Population size:  {population_size}")
    print(f"Iterations:       {num_iterations}")
    print(f"Avg time/iter:    {avg_time:.3f}s")
    print(f"Min time:         {min_time:.3f}s")
    print(f"Max time:         {max_time:.3f}s")
    print(f"Time per genome:  {avg_time / population_size * 1000:.2f}ms")
    print()
    
    # Now profile with more granularity
    print("=" * 60)
    print("DETAILED BREAKDOWN (instrumented run)")
    print("=" * 60)
    
    profile_detailed_breakdown(population_size, base_stats_fixed, cfg_data, calc_song, ref_arrays)


def profile_detailed_breakdown(population_size, base_stats_fixed, cfg_data, calc_song, ref_arrays):
    """Profile individual phases of batch_evaluate_genomes."""
    
    from gear_optimizer.solver.scoring import GEM_SOLVER_CACHE
    from gear_optimizer.solver.fever_timeline import get_song_timeline_grid, SONG_TIMELINE_GRIDS
    from gear_optimizer.core.utils import stats_signature, SKIP_ITEM_KEYS
    from gear_optimizer.core.constants import (
        TOTAL_GEM_BUDGET, MAX_STAT_INDEX, GEM_SCALE_NORMAL, GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE,
    )
    from gear_optimizer.solver.scoring import precompute_fever_timelines
    from gear_optimizer.solver.taichi_gem_solver import mega_batch_solve_population
    from math import floor
    
    population = [create_random_genome() for _ in range(population_size)]
    GEM_SOLVER_CACHE.clear()
    SONG_TIMELINE_GRIDS.clear()
    
    sel_color = cfg_data["selected_color"]
    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    
    user_ft = cfg_data["user_ft"]
    user_ff = cfg_data["user_ff"]
    user_pp = cfg_data["user_pp"]
    user_cm = cfg_data["user_cm"]
    user_fm = cfg_data["user_fm"]
    static_elem_input = cfg_data["static_elem_input"]
    
    # Phase 1: Aggregate stats
    t0 = time.perf_counter()
    all_stats = []
    for genome in population:
        current_stats = base_stats_fixed.copy()
        for item in genome:
            for k, v in item.items():
                if k not in SKIP_ITEM_KEYS:
                    current_stats[k] = current_stats.get(k, 0) + v
        all_stats.append(current_stats)
    phase1_time = time.perf_counter() - t0
    print(f"Phase 1 (Stat aggregation):     {phase1_time:.4f}s")
    
    # Phase 2: Deduplication
    t0 = time.perf_counter()
    unique_stats = []
    for stats in all_stats:
        sig = stats_signature(stats, calc_song, sel_color)
        # Simplified: just collect unique stats without full caching logic
        unique_stats.append((sig, stats))
    phase2_time = time.perf_counter() - t0
    print(f"Phase 2 (Signature dedup):      {phase2_time:.4f}s")
    
    # Phase 3: Timeline grid + precompute_fever_timelines
    t0 = time.perf_counter()
    grid = get_song_timeline_grid(calc_song, ref_arrays)
    phase3a_time = time.perf_counter() - t0
    print(f"Phase 3a (Timeline grid init):  {phase3a_time:.4f}s")
    
    t0 = time.perf_counter()
    total_work_items = 0
    genome_stats = {}
    work_items = []
    genome_ids = []
    
    for unique_idx, (sig, stats) in enumerate(unique_stats[:50]):  # Sample first 50 for speed
        base_stats = stats.copy()
        
        # Deduct user-specified gems from base stats
        base_stats["Fever Time"] -= user_ft * GEM_SCALE_FEVER
        base_stats["Beat"] -= user_ft * GEM_STAT_TO_ELEMENT_SCALE
        base_stats["Fever Fill Rate"] -= user_ff * GEM_SCALE_FEVER
        base_stats["Vibe"] -= user_ff * GEM_STAT_TO_ELEMENT_SCALE
        base_stats["Fever Multiplier"] -= user_fm * GEM_SCALE_FEVER
        base_stats["Rush"] -= user_fm * GEM_STAT_TO_ELEMENT_SCALE
        base_stats["Combo Multiplier"] -= user_cm * GEM_SCALE_NORMAL
        base_stats["Flow"] -= user_cm * GEM_STAT_TO_ELEMENT_SCALE
        base_stats["Perfect Points"] -= user_pp * GEM_SCALE_NORMAL
        base_stats["Chill"] -= user_pp * GEM_STAT_TO_ELEMENT_SCALE
        base_stats[sel_color] -= static_elem_input * ELEMENTAL_GEM_SCALE
        
        remaining_ft_stat = MAX_STAT_INDEX - base_stats["Fever Time"]
        remaining_ff_stat = MAX_STAT_INDEX - base_stats["Fever Fill Rate"]
        max_ft_gems = floor(remaining_ft_stat / GEM_SCALE_FEVER) if remaining_ft_stat > 0 else 0
        max_ff_gems = floor(remaining_ff_stat / GEM_SCALE_FEVER) if remaining_ff_stat > 0 else 0
        
        timelines = precompute_fever_timelines(
            base_stats, calc_song, ref_arrays,
            TOTAL_GEM_BUDGET, max_ft_gems, max_ff_gems, None
        )
        
        for t_data in timelines:
            work_items.append({
                "budget": t_data["remaining_budget"],
                "fever_mask_head": t_data["timeline"][0],
                "count_body_fever": t_data["timeline"][1],
                "count_body_normal": t_data["timeline"][2],
                "ft_gems": t_data["ft_gems"],
                "ff_gems": t_data["ff_gems"],
            })
            genome_ids.append(unique_idx)
        
        total_work_items += len(timelines)
        
        # Build genome stats
        base_pp = stats.get("Perfect Points", 0) - user_pp * GEM_SCALE_NORMAL
        base_cm = stats.get("Combo Multiplier", 0) - user_cm * GEM_SCALE_NORMAL
        base_fm = stats.get("Fever Multiplier", 0) - user_fm * GEM_SCALE_FEVER
        
        base_beat = stats.get("Beat", 0) - user_ft * GEM_STAT_TO_ELEMENT_SCALE
        base_vibe = stats.get("Vibe", 0) - user_ff * GEM_STAT_TO_ELEMENT_SCALE
        base_rush = stats.get("Rush", 0) - user_fm * GEM_STAT_TO_ELEMENT_SCALE
        base_flow = stats.get("Flow", 0) - user_cm * GEM_STAT_TO_ELEMENT_SCALE
        base_chill = stats.get("Chill", 0) - user_pp * GEM_STAT_TO_ELEMENT_SCALE
        
        if sel_color == "Beat": base_beat -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Vibe": base_vibe -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Rush": base_rush -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Flow": base_flow -= static_elem_input * ELEMENTAL_GEM_SCALE
        elif sel_color == "Chill": base_chill -= static_elem_input * ELEMENTAL_GEM_SCALE

        color_vals = {"Beat": base_beat, "Vibe": base_vibe, "Rush": base_rush, "Flow": base_flow, "Chill": base_chill}
        base_p_val = color_vals.get(p_color, 0)
        base_s_val = color_vals.get(s_color, 0)
        
        genome_stats[unique_idx] = (int(base_pp), int(base_cm), int(base_fm), int(base_p_val), int(base_s_val))
    
    phase3b_time = time.perf_counter() - t0
    print(f"Phase 3b (Fever timeline gen):  {phase3b_time:.4f}s  ({total_work_items} work items for 50 genomes)")
    print(f"         Extrapolated for {population_size}: ~{phase3b_time * population_size / 50:.3f}s")
    
    # Phase 4: GPU Kernel
    if work_items:
        # Color flags
        is_p_pp = 1 if "Chill" == p_color else 0
        is_s_pp = 1 if "Chill" == s_color else 0
        is_p_cm = 1 if "Flow" == p_color else 0
        is_s_cm = 1 if "Flow" == s_color else 0
        is_p_fm = 1 if "Rush" == p_color else 0
        is_s_fm = 1 if "Rush" == s_color else 0
        is_p_ov = 1 if sel_color == p_color else 0
        is_s_ov = 1 if sel_color == s_color else 0
        is_p_ft = 1 if "Beat" == p_color else 0
        is_s_ft = 1 if "Beat" == s_color else 0
        is_p_ff = 1 if "Vibe" == p_color else 0
        is_s_ff = 1 if "Vibe" == s_color else 0
        
        t0 = time.perf_counter()
        results = mega_batch_solve_population(
            work_items,
            np.array(genome_ids, dtype=np.int32),
            genome_stats,
            is_p_ft, is_s_ft, is_p_ff, is_s_ff,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm,
            is_p_fm, is_s_fm, is_p_ov, is_s_ov,
            ref_arrays,
        )
        phase4_time = time.perf_counter() - t0
        print(f"Phase 4 (GPU kernel):           {phase4_time:.4f}s  ({len(work_items)} work items)")
        print(f"         Extrapolated for {population_size}: ~{phase4_time * population_size / 50:.3f}s")
    
    print()
    print("CONCLUSION:")
    print("-" * 40)
    estimated_total = phase1_time + phase2_time + phase3a_time + (phase3b_time * population_size / 50) + (phase4_time * population_size / 50)
    print(f"Estimated total for {population_size} genomes: {estimated_total:.3f}s")
    
    if phase3b_time * population_size / 50 > phase4_time * population_size / 50:
        print("BOTTLENECK: CPU-side fever timeline generation (Phase 3b)")
    else:
        print("BOTTLENECK: GPU kernel (Phase 4)")


if __name__ == "__main__":
    profile_batch_evaluation(population_size=500, num_iterations=3)
