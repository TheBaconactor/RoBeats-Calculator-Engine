import sys
from unittest.mock import MagicMock, patch
import numpy as np

# Mock Taichi and GPU modules BEFORE importing force_greats
sys.modules["gear_optimizer.solver.taichi_gem_solver"] = MagicMock()
sys.modules["gear_optimizer.solver.taichi_gem.force_greats.api"] = MagicMock()

# Now import the target
from gear_optimizer.solver.scoring import force_greats


def test_pruning_integration():
    # Setup mocks
    mock_collect = MagicMock()
    # Simulate breakpoints: s0=[0], s1=[0, 10], s2=[0], s3=[0] (Section 4 pruned)
    mock_collect.return_value = [[0], [0, 10], [0], [0]]

    # Mock the solver facade
    force_greats.collect_analytic_breakpoints = mock_collect

    # Mock taichi_gem_solver import inside the function
    with patch("gear_optimizer.solver.taichi_gem_solver.collect_analytic_breakpoints", mock_collect):
        with patch("gear_optimizer.solver.taichi_gem_solver.solve_force_greats_finder_gpu") as mock_gpu_finder:
            # Mock GPU finder return
            mock_gpu_finder.return_value = [{"cfg_idx": 0, "final_score": 1000}]

            # Test Data
            stats = {"Fever Time": 100, "Fever Fill Rate": 100, "Perfect Points": 100}
            calc_song = {
                "song_data": {"timestamps": np.array([1.0, 2.0])},
                "metadata": {"Long Notes": 0, "Last Note Time": 100.0, "Primary Color": "Rush"},
            }
            ref_arrays = {}

            # Mock evaluate_force_greats to return a baseline with 4 sections
            # This ensures we trigger the path where s3 exists but is pruned
            with patch("gear_optimizer.solver.scoring.force_greats.evaluate_force_greats") as mock_eval:
                mock_eval.return_value = {"num_non_fever_sections": 4, "non_fever_base": 20, "base_score": 100}

                # Run
                result = force_greats.run_force_greats_hill_climb(stats, calc_song, ref_arrays, use_gpu=True)

                # Verify collect was called
                assert mock_collect.called, "collect_analytic_breakpoints should be called"

                # Verify GPU solver was called with pruned list
                # We expect 2 configs: (0, 0, 0, 0) and (0, 10, 0, 0)
                # because s1 has [0, 10]
                args, _ = mock_gpu_finder.call_args
                counts_list = args[4]  # 5th arg is counts_list
                print(f"Generated counts_list: {counts_list}")

                assert len(counts_list) == 2, f"Expected 2 configs, got {len(counts_list)}"
                assert (0, 0, 0, 0) in counts_list
                assert (0, 10, 0, 0) in counts_list
                assert (0, 5, 0, 0) not in counts_list  # 5 was not in breakpoints


if __name__ == "__main__":
    try:
        test_pruning_integration()
        print("Verification SUCCESS: Pruning logic is correctly integrated.")
    except AssertionError as e:
        print(f"Verification FAILED: {e}")
    except Exception as e:
        print(f"Verification ERROR: {e}")
        import traceback

        traceback.print_exc()
