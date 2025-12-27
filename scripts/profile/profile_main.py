"""
Profile main.py with PERF_TIMING enabled.

This runs the gear optimizer with detailed timing for:
- ForceGreats GPU processing (collect, cfg_build, gpu_calls)
- Song processing phases
- GPU batch operations
"""

import os
import sys
import tempfile
import configparser
from pathlib import Path

# Enable all profiling features
os.environ["PERF_TIMING"] = "1"
os.environ["GPU_PROFILER"] = "1"
os.environ["GPU_SYNC_FOR_TIMING"] = "1"  # Accurate GPU timing
os.environ["GPU_FORCE_SYNC"] = "1"  # Force sync after kernels
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("FG_VULKAN_RETRIES", "1")

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

def _write_profile_config(project_root_dir: str) -> str:
    """
    Create a bounded profiling config so `app.run()` finishes in reasonable time.

    Keeps GPU + ForceGreats enabled, but reduces GA depth/multi-start.
    """
    src = Path(project_root_dir) / "config.ini"
    cfg = configparser.ConfigParser()
    cfg.read(src, encoding="utf-8-sig")

    if not cfg.has_section("IterationEngine"):
        cfg.add_section("IterationEngine")

    # Bound runtime: user config can be extremely heavy (e.g., depth=500, multistart=75).
    cfg.set("IterationEngine", "GA_SearchDepth", "50")
    cfg.set("IterationEngine", "GA_MultiStart", "5")
    cfg.set("IterationEngine", "MaxParallelSongs", cfg.get("IterationEngine", "MaxParallelSongs", fallback="1"))
    cfg.set("IterationEngine", "LoopForever", "false")
    cfg.set("IterationEngine", "GPU_Mode", "true")
    cfg.set("IterationEngine", "GPU_Native_GA", cfg.get("IterationEngine", "GPU_Native_GA", fallback="true"))

    # Force-greats path is what was crashing; keep it enabled for profiling.
    cfg.set("IterationEngine", "ForceGreatsMode", cfg.get("IterationEngine", "ForceGreatsMode", fallback="true"))
    cfg.set("IterationEngine", "ForceGreatsFinder", cfg.get("IterationEngine", "ForceGreatsFinder", fallback="true"))
    cfg.set("IterationEngine", "ForceGreatsDebug", "true")

    tmp_dir = Path(project_root_dir) / "bin"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out = tmp_dir / "config.profile.ini"
    with out.open("w", encoding="utf-8") as f:
        cfg.write(f)
    return str(out)

if __name__ == "__main__":
    import cProfile
    import pstats

    from gear_optimizer.app import GearOptimizerApp
    
    try:
        profile_cfg = _write_profile_config(project_root)
        os.environ["METAFINDER_CONFIG_PATH"] = profile_cfg

        print("=" * 70)
        print("GEAR OPTIMIZER - PROFILING MODE")
        print("=" * 70)
        print("  PERF_TIMING=1 (FG timing breakdown)")
        print("  GPU_PROFILER=1 (GPU operation timing)")
        print("  GPU_SYNC_FOR_TIMING=1 (Accurate kernel timing)")
        print(f"  METAFINDER_CONFIG_PATH={profile_cfg}")
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
