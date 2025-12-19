#!/usr/bin/env python3
"""
Profile main.py ignoring cold start by running 2 songs.
First song warms up all kernels, second song is profiled.
"""
import os
import sys
import multiprocessing
import cProfile
import pstats
import io

# Enable all profiling features
os.environ["PERF_TIMING"] = "1"
os.environ["GPU_PROFILER"] = "1"
os.environ["GPU_SYNC_FOR_TIMING"] = "1"
os.environ["GPU_FORCE_SYNC"] = "1"

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    from gear_optimizer.app import GearOptimizerApp
    
    try:
        print("=" * 70)
        print("GEAR OPTIMIZER - WARM-ONLY PROFILING (ignoring cold start)")
        print("=" * 70)
        
        # Run 1: Warmup (not profiled)
        print("\n>> WARMUP RUN: Processing first song to compile all kernels...")
        app = GearOptimizerApp()
        app._run_single_iteration()  # Run once to warm up
        
        print("\n" + "-" * 70)
        print(">> WARMUP COMPLETE. Starting PROFILED run...")
        print("-" * 70 + "\n")
        
        # Run 2: Profiled (hot)
        profiler = cProfile.Profile()
        profiler.enable()
        
        app._run_single_iteration()  # This is the profiled run
        
        profiler.disable()
        
        print("\n" + "=" * 70)
        print("PROFILING COMPLETE - GENERATING REPORT")
        print("=" * 70)
        
        # Save results
        output_file = os.path.join(project_root, "tests", "main_profile_warm_results.txt")
        with open(output_file, "w") as f:
            f.write("MAIN.PY WARM-ONLY PROFILING (Cold Start Excluded)\n")
            f.write("=" * 70 + "\n\n")
            
            f.write("TOP 50 BY TOTAL (SELF) TIME:\n")
            f.write("-" * 70 + "\n")
            stream2 = io.StringIO()
            stats2 = pstats.Stats(profiler, stream=stream2)
            stats2.strip_dirs()
            stats2.sort_stats('tottime')
            stats2.print_stats(50)
            f.write(stream2.getvalue())
            
            f.write("\n\nTOP 50 BY CUMULATIVE TIME:\n")
            f.write("-" * 70 + "\n")
            stream1 = io.StringIO()
            stats1 = pstats.Stats(profiler, stream=stream1)
            stats1.strip_dirs()
            stats1.sort_stats('cumulative')
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
