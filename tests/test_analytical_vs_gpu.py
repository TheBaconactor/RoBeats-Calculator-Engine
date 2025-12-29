"""
Real Song Validation: Compare Analytical FG Scorer vs Existing Timeline

This test uses SongTimelineGrid directly to validate the analytical scorer.
"""

import sys
import numpy as np
from math import floor, ceil

sys.path.insert(0, "..")

from test_analytical_fg_scorer import AnalyticalFGScorer


def create_mock_ref_arrays():
    """
    Create mock reference arrays using known bezier interpolation points.
    These are approximations of the actual game values.
    """
    # Simple linear interpolation for testing
    # Real values use bezier curves, but linear is good enough for validation
    return {
        "Fever Time": np.linspace(0.5, 1.5, 161),  # 0.5x at 0, 1.5x at 160
        "Fever Fill Rate": np.linspace(0.5, 2.0, 161),  # 0.5x at 0, 2.0x at 160
        "Perfect Points": np.linspace(100, 450, 161),  # 100 at 0, 450 at 160
        "Combo Multiplier": np.linspace(1.0, 2.0, 161),  # 1.0x at 0, 2.0x at 160
        "Fever Multiplier": np.linspace(1.0, 2.0, 161),  # 1.0x at 0, 2.0x at 160
    }


def run_standalone_validation():
    """Run validation using SongTimelineGrid directly."""
    print("=" * 70)
    print("STANDALONE VALIDATION: Analytical vs SongTimelineGrid")
    print("=" * 70)

    try:
        from gear_optimizer.solver.fever_timeline import SongTimelineGrid

        # Create a synthetic song
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

        ref_arrays = create_mock_ref_arrays()

        print("\n1. Creating SongTimelineGrid...")
        grid = SongTimelineGrid(calc_song, ref_arrays)
        print(f"   Grid created: {grid.total_notes} notes")

        print("\n2. Creating Analytical Scorer...")
        scorer = AnalyticalFGScorer(
            timestamps=np.array(timestamps),
            total_notes=n_notes,
            long_notes=0,
            last_note_time=60.0,
            ref_ft=ref_arrays["Fever Time"],
            ref_ff=ref_arrays["Fever Fill Rate"],
            ref_pp=ref_arrays["Perfect Points"],
            ref_cm=ref_arrays["Combo Multiplier"],
            ref_fm=ref_arrays["Fever Multiplier"],
        )
        print(f"   Scorer created: head_len={scorer.head_len}")

        print("\n3. Comparing Baseline Timelines (0 forced greats)...")
        print("-" * 70)

        test_points = [
            (0, 0),
            (0, 80),
            (0, 160),
            (80, 0),
            (80, 80),
            (80, 160),
            (160, 0),
            (160, 80),
            (160, 160),
        ]

        all_match = True
        mismatches = []

        for ft_stat, ff_stat in test_points:
            # Ground truth from SongTimelineGrid
            tl = grid.get_timeline(ft_stat, ff_stat)
            gt_mask = tl[0]  # numpy array of first 100 notes
            gt_bf = tl[1]
            gt_bn = tl[2]
            gt_acts = tl[3]

            # Analytical (0 forced greats for all sections)
            forced_counts = [0] * max(1, gt_acts)
            an_mask, an_bf, an_bn = scorer.compute_timeline_with_forced(ft_stat, ff_stat, forced_counts)

            # Compare body counts
            match = (gt_bf == an_bf) and (gt_bn == an_bn)
            status = "✓" if match else "✗"

            if not match:
                all_match = False
                mismatches.append(
                    {
                        "ft": ft_stat,
                        "ff": ff_stat,
                        "gt_bf": gt_bf,
                        "gt_bn": gt_bn,
                        "an_bf": an_bf,
                        "an_bn": an_bn,
                    }
                )

            print(
                f"   FT={ft_stat:3d}, FF={ff_stat:3d}: acts={gt_acts} | "
                f"GT(bf={gt_bf:4d}, bn={gt_bn:4d}) vs "
                f"AN(bf={an_bf:4d}, bn={an_bn:4d}) {status}"
            )

        print("-" * 70)

        if all_match:
            print("\n✓ ALL BASELINE COMPARISONS MATCH!")
        else:
            print(f"\n✗ {len(mismatches)} MISMATCHES found:")
            for m in mismatches[:3]:
                print(f"   FT={m['ft']}, FF={m['ff']}: GT({m['gt_bf']},{m['gt_bn']}) != AN({m['an_bf']},{m['an_bn']})")

        # Test with forced greats
        print("\n4. Comparing Forced Greats Timelines...")
        print("-" * 70)

        ft_stat, ff_stat = 80, 80
        tl = grid.get_timeline(ft_stat, ff_stat)
        acts = tl[3]

        fg_match = True

        if acts >= 1:
            for forced_counts in [[0], [5], [10], [20]]:
                forced_counts_padded = forced_counts + [0] * (acts - len(forced_counts))

                gt_mask, gt_bf, gt_bn = grid.get_timeline_with_forced(ft_stat, ff_stat, forced_counts_padded)
                an_mask, an_bf, an_bn = scorer.compute_timeline_with_forced(ft_stat, ff_stat, forced_counts_padded)

                match = (gt_bf == an_bf) and (gt_bn == an_bn)
                status = "✓" if match else "✗"

                if not match:
                    fg_match = False

                print(
                    f"   Config {str(forced_counts_padded):15s}: "
                    f"GT(bf={gt_bf:4d}, bn={gt_bn:4d}) vs "
                    f"AN(bf={an_bf:4d}, bn={an_bn:4d}) {status}"
                )

        print("-" * 70)

        if fg_match:
            print("\n✓ ALL FORCED GREATS COMPARISONS MATCH!")
        else:
            print("\n✗ FORCED GREATS MISMATCHES found - investigation needed")

        print("\n" + "=" * 70)
        print("VALIDATION COMPLETE")
        print("=" * 70)

        return all_match and fg_match

    except Exception as e:
        import traceback

        print(f"\nERROR: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_standalone_validation()
    sys.exit(0 if success else 1)
