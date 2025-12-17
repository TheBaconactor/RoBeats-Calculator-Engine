"""
Profile main.py with PERF_TIMING enabled.

This runs the gear optimizer with detailed timing for:
- ForceGreats GPU processing (collect, cfg_build, gpu_calls)
- Song processing phases
- GPU batch operations
"""

import os
import sys

# Enable all profiling features
os.environ["PERF_TIMING"] = "1"
os.environ["GPU_PROFILER"] = "1"
os.environ["GPU_SYNC_FOR_TIMING"] = "1"  # Accurate GPU timing
os.environ["GPU_FORCE_SYNC"] = "1"  # Force sync after kernels

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

if __name__ == "__main__":
    import cProfile
    import pstats

    from gear_optimizer.app import GearOptimizerApp
    
    try:
        print("=" * 70)
        print("GEAR OPTIMIZER - PROFILING MODE")
        print("=" * 70)
        print("  PERF_TIMING=1 (FG timing breakdown)")
        print("  GPU_PROFILER=1 (GPU operation timing)")
        print("  GPU_SYNC_FOR_TIMING=1 (Accurate kernel timing)")
        print("=" * 70)
        print()
        
        # Instantiate App (Cold Start / Init costs are here)
        app = GearOptimizerApp()
        
        # Start Profiling ONLY for the run loop
        print("[Profiler] Starting cProfile...")
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            app.run()
        except SystemExit:
            pass # Expected exit
            
        profiler.disable()
        print("[Profiler] Stopped cProfile.")
        
        # Save Stats
        stats_file = "profile_main.prof"
        profiler.dump_stats(stats_file)
        print(f"[Profiler] Stats saved to {stats_file}")
        
        # Print Summary
        print("=" * 70)
        print("TOP 20 CALLS BY CUMULATIVE TIME")
        print("=" * 70)
        stats = pstats.Stats(profiler)
        stats.sort_stats("cumtime").print_stats(20)
        
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
