import os
import sys
import multiprocessing
import cProfile
import pstats
import io
import time
import numpy as np

# Enable all profiling features
os.environ["PERF_TIMING"] = "1"
os.environ["GPU_PROFILER"] = "1"
os.environ["GPU_SYNC_FOR_TIMING"] = "1"
os.environ["GPU_FORCE_SYNC"] = "1"

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    multiprocessing.freeze_support()

    from gear_optimizer.app import GearOptimizerApp
    from gear_optimizer.solver import genetic

    try:
        print("=" * 70)
        print("GEAR OPTIMIZER - WARM (HOT) PROFILING MODE")
        print("=" * 70)

        # Initialize app
        app = GearOptimizerApp()

        print(">> WARMUP: Pre-compiling Taichi kernels...")
        import taichi as ti
        from gear_optimizer.solver.taichi_gem import api as gem_api
        from gear_optimizer.solver.taichi_gem import fields as gem_fields

        # Ensure Taichi is ready
        ti.init(arch=ti.vulkan)

        # 1. Allocate fields (dummy size for compilation)
        max_genomes = gem_fields.MAX_GENOMES
        n_slots = 9

        # 2. Upload dummy data to fields
        fixed_stats = np.array([10] * 10, dtype=np.int32)
        gem_api.ga_upload_base_fixed_stats(fixed_stats)
        gem_api.ga_init_global_best()
        gem_api.ga_seed_rng(250)

        # 3. Trigger compilation of main kernels
        print("   Compiling kernels (Evaluation, Selection, Crossover)...")
        # Dummy evaluation
        gem_api.ga_evaluate_population(
            n_genomes=250, n_slots=9, total_budget=20, gem_scale_fever=3, song_slot=0, is_p_ft=1, is_s_ff=1, use_hints=0
        )
        # Dummy next generation
        gem_api.ga_next_generation(n_genomes=250, n_slots=9)
        # Dummy storage
        gem_api.ga_store_hints(250)
        gem_api.ga_update_global_best(250, 9)
        gem_api.ga_find_island_elites(250, 5, 2)

        ti.sync()
        print(">> WARMUP COMPLETE. Starting Main Profile...")
        print("-" * 70)

        # Now profile the actual app execution
        profiler = cProfile.Profile()
        profiler.enable()

        app.run()

        profiler.disable()

        print("\n" + "=" * 70)
        print("PROFILING COMPLETE - GENERATING REPORT")
        print("=" * 70)

        # Save results
        output_file = os.path.join(project_root, "tests", "main_profile_hot_results.txt")
        with open(output_file, "w") as f:
            f.write("MAIN.PY HOT PROFILING RESULTS (WARM START)\n")
            f.write("=" * 70 + "\n\n")

            f.write("TOP 50 BY TOTAL (SELF) TIME:\n")
            f.write("-" * 70 + "\n")
            stream2 = io.StringIO()
            stats2 = pstats.Stats(profiler, stream=stream2)
            stats2.strip_dirs()
            stats2.sort_stats("tottime")
            stats2.print_stats(50)
            f.write(stream2.getvalue())

            f.write("\n\nTOP 50 BY CUMULATIVE TIME:\n")
            f.write("-" * 70 + "\n")
            stream1 = io.StringIO()
            stats1 = pstats.Stats(profiler, stream=stream1)
            stats1.strip_dirs()
            stats1.sort_stats("cumulative")
            stats1.print_stats(50)
            f.write(stream1.getvalue())

        print(f"Results saved to: {output_file}")

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
