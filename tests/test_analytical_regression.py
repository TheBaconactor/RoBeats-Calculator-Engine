"""
Step 3: Regression Testing - Compare Analytical FG Scorer performance

This test:
1. Loads a real song
2. Runs current GPU FG solver
3. Runs analytical pre-computation + scoring
4. Compares results and timing
"""

import sys
import time
import numpy as np

sys.path.insert(0, ".")


def run_regression_test():
    """Run full regression test on a real song."""
    print("=" * 70)
    print("REGRESSION TEST: Analytical FG vs GPU Kernel")
    print("=" * 70)

    try:
        from gear_optimizer.solver.fever_timeline import SongTimelineGrid
        from gear_optimizer.solver.analytical_fg import AnalyticalFGScorer, create_scorer_from_calc_song

        # Create a synthetic song for testing
        print("\n1. Setting up test data...")
        n_notes = 500
        timestamps = np.linspace(0, 60.0, n_notes).tolist()

        calc_song = {
            "song_data": {
                "timestamps": timestamps,
                "total_notes": n_notes,
            },
            "metadata": {
                "Long Notes": 0,
                "Last Note Time": 60.0,
            },
        }

        # Mock reference arrays
        ref_arrays = {
            "Fever Time": np.linspace(0.5, 1.5, 161),
            "Fever Fill Rate": np.linspace(0.5, 2.0, 161),
            "Perfect Points": np.linspace(100, 450, 161),
            "Combo Multiplier": np.linspace(1.0, 2.0, 161),
            "Fever Multiplier": np.linspace(1.0, 2.0, 161),
        }

        # Create analytical scorer using factory
        scorer = create_scorer_from_calc_song(calc_song, ref_arrays)
        print(f"   Scorer created: {scorer.total_notes} notes, head_len={scorer.head_len}")

        # Create SongTimelineGrid for ground truth
        grid = SongTimelineGrid(calc_song, ref_arrays)
        print(f"   Grid created: {grid.total_notes} notes")

        # Test FG configs
        ft_stat, ff_stat = 80, 80
        configs = [
            [0, 0],
            [5, 0],
            [10, 0],
            [0, 5],
            [10, 5],
            [20, 10],
        ]

        print(f"\n2. Testing {len(configs)} FG configs at FT={ft_stat}, FF={ff_stat}...")
        print("-" * 70)

        # Benchmark analytical scorer
        n_iterations = 100
        t0 = time.perf_counter()
        for _ in range(n_iterations):
            results = scorer.precompute_all_configs(ft_stat, ff_stat, configs)
        t_analytical = (time.perf_counter() - t0) / n_iterations * 1000

        print(f"   Analytical: {t_analytical:.3f} ms per {len(configs)} configs")

        # Benchmark SongTimelineGrid (ground truth)
        t0 = time.perf_counter()
        for _ in range(n_iterations):
            gt_results = []
            for cfg in configs:
                mask, bf, bn = grid.get_timeline_with_forced(ft_stat, ff_stat, cfg)
                gt_results.append((mask, bf, bn))
        t_grid = (time.perf_counter() - t0) / n_iterations * 1000

        print(f"   Grid:       {t_grid:.3f} ms per {len(configs)} configs")
        print(f"   Speedup:    {t_grid / t_analytical:.1f}x")

        # Compare results
        print("\n3. Comparing results...")
        print("-" * 70)

        all_match = True
        for i, cfg in enumerate(configs):
            an_m0, an_m1, an_m2, an_m3, an_bf, an_bn = results[i]
            gt_mask, gt_bf, gt_bn = gt_results[i]

            match = (an_bf == gt_bf) and (an_bn == gt_bn)
            status = "✓" if match else "✗"

            if not match:
                all_match = False

            print(
                f"   Config {str(cfg):10s}: AN(bf={an_bf:3d}, bn={an_bn:3d}) vs GT(bf={gt_bf:3d}, bn={gt_bn:3d}) {status}"
            )

        print("-" * 70)

        if all_match:
            print("\n✓ ALL RESULTS MATCH!")
        else:
            print("\n✗ SOME RESULTS DO NOT MATCH")

        # Larger benchmark
        print("\n4. Large-scale benchmark...")
        print("-" * 70)

        # Generate many configs
        large_configs = []
        for s0 in range(0, 51, 5):
            for s1 in range(0, 31, 5):
                large_configs.append([s0, s1])

        n_large_configs = len(large_configs)
        print(f"   Testing {n_large_configs} configs...")

        # Analytical
        t0 = time.perf_counter()
        an_results = scorer.precompute_all_configs(ft_stat, ff_stat, large_configs)
        t_an_large = (time.perf_counter() - t0) * 1000

        # Grid
        t0 = time.perf_counter()
        gt_results = []
        for cfg in large_configs:
            mask, bf, bn = grid.get_timeline_with_forced(ft_stat, ff_stat, cfg)
            gt_results.append((bf, bn))
        t_gt_large = (time.perf_counter() - t0) * 1000

        print(f"   Analytical: {t_an_large:.3f} ms for {n_large_configs} configs")
        print(f"   Grid:       {t_gt_large:.3f} ms for {n_large_configs} configs")
        print(f"   Speedup:    {t_gt_large / t_an_large:.1f}x")

        # Verify all match
        n_match = 0
        for i, (an, gt) in enumerate(zip(an_results, gt_results)):
            an_bf, an_bn = an[4], an[5]
            gt_bf, gt_bn = gt
            if an_bf == gt_bf and an_bn == gt_bn:
                n_match += 1

        print(f"   Match rate: {n_match}/{n_large_configs} ({100 * n_match / n_large_configs:.0f}%)")

        print("\n" + "=" * 70)
        print("REGRESSION TEST COMPLETE")
        print("=" * 70)

        return all_match and n_match == n_large_configs

    except Exception as e:
        import traceback

        print(f"\nERROR: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_regression_test()
    sys.exit(0 if success else 1)
