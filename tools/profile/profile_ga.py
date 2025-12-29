"""
Profile the Genetic Algorithm to identify bottlenecks.

Usage: python tools/profile_ga.py
"""

import cProfile
import pstats
import io
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def run_ga():
    """Run a minimal GA to profile."""
    from gear_optimizer.solver.genetic import solve_coevolution_genetic
    from gear_optimizer.solver.scoring import solve_best_fever_combination
    from gear_optimizer.data.models import GASettings
    from gear_optimizer.data.gears import load_gears
    from gear_optimizer.data.minis import load_minis
    from gear_optimizer.data.songs import load_song_data
    from gear_optimizer.core.references import load_stat_references

    # Load data
    gears = load_gears()
    minis = load_minis()
    ref_arrays = load_stat_references()

    # Load a test song
    song_data = load_song_data()
    test_song = None
    for song in song_data:
        if "ATENA" in song.get("Title", ""):
            test_song = song
            break

    if not test_song:
        test_song = song_data[0] if song_data else None

    if not test_song:
        print("No song found!")
        return

    print(f"Profiling with song: {test_song.get('Title', 'Unknown')}")

    # Build calc_song
    calc_song = {
        "metadata": test_song,
        "song_data": {
            "timestamps": test_song.get("timestamps", [0.0] * 100),
        },
    }

    # Config
    cfg_data = {
        "selected_color": "Beat",
        "user_ft": 0,
        "user_ff": 0,
        "user_pp": 0,
        "user_cm": 0,
        "user_fm": 0,
        "static_elem_input": 0,
        "use_gpu": True,
    }

    base_stats = {
        "Beat": 50,
        "Vibe": 30,
        "Rush": 20,
        "Flow": 25,
        "Chill": 15,
        "Perfect Points": 40,
        "Combo Multiplier": 35,
        "Fever Multiplier": 30,
        "Fever Time": 25,
        "Fever Fill Rate": 20,
    }

    # GA Settings - reduced for profiling
    ga_settings = GASettings()
    ga_settings.multi_start = 1  # Single run

    # Run GA
    result = solve_coevolution_genetic(
        cfg=None,
        base_stats_fixed=base_stats,
        cfg_data=cfg_data,
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        all_gears=gears,
        all_minis=minis,
        fixed_gear=None,
        fixed_minis=None,
        optimize_gear=True,
        optimize_minis=True,
        ga_depth=10,  # Reduced for profiling
        db_seed=None,
        known_loadouts={},
        status_cb=None,
        ga_settings=ga_settings,
    )

    print(f"Best score: {result.get('Score', 0):,}")


if __name__ == "__main__":
    print("=" * 60)
    print("GA Profiler")
    print("=" * 60)

    # Profile
    pr = cProfile.Profile()
    pr.enable()

    run_ga()

    pr.disable()

    # Print stats
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(30)  # Top 30 functions
    print("\n" + "=" * 60)
    print("TOP 30 BY CUMULATIVE TIME")
    print("=" * 60)
    print(s.getvalue())

    # Also print by tottime
    s2 = io.StringIO()
    ps2 = pstats.Stats(pr, stream=s2).sort_stats("tottime")
    ps2.print_stats(20)  # Top 20 functions
    print("\n" + "=" * 60)
    print("TOP 20 BY TOTAL TIME (self)")
    print("=" * 60)
    print(s2.getvalue())
