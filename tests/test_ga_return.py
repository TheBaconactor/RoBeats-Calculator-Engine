import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.solver.genetic import solve_coevolution_genetic
from gear_optimizer.data.models import GASettings


class TestGAReturnValues(unittest.TestCase):
    def test_ga_returns_unwrapped_data(self):
        # Mock dependencies
        cfg = MagicMock()
        cfg.getboolean.return_value = False
        cfg.get.return_value = 0

        base_stats_fixed = {"Perfect Points": 100}
        calc_song = {"metadata": {"Primary Color": "Rush"}}
        ref_arrays = {}
        all_gears = [{"Name": "G1", "type": "Hat", "Rush": 10}]
        all_minis = [{"Name": f"M{i}", "Rush": 10} for i in range(1, 4)]
        gears_by_name = {"G1": all_gears[0]}
        minis_by_name = {m["Name"]: m for m in all_minis}

        # Mock result from worker_coevolution_evaluate.
        # The solver returns the inner `Data` dict (not the wrapper).
        genome = [all_gears[0]] * 6 + list(all_minis)
        wrapper_res = {
            "Score": 1000,
            "BaseScore": 1000,
            "Genome": genome,
            "Gear": genome[:6],
            "Minis": genome[6:],
            "MiniNames": [m["Name"] for m in genome[6:]],
            "Data": {"Score": 1000, "Stats": {}},  # Inner Data (no BaseScore yet)
        }

        # Populate all slots to ensure valid genomes
        gear_dict = {
            "Hat": [all_gears[0]],
            "Neck": [all_gears[0]],
            "Face": [all_gears[0]],
            "Shirt": [all_gears[0]],
            "Back": [all_gears[0]],
            "Pants": [all_gears[0]],
        }

        with patch("gear_optimizer.solver.genetic.initialize_pools", return_value=(gear_dict, all_minis, 1, 3)):
            with patch("gear_optimizer.solver.genetic.worker_coevolution_evaluate", return_value=wrapper_res):
                # Mock evaluate_population_parallel to return list of wrappers
                with patch("gear_optimizer.solver.genetic.evaluate_population_parallel", return_value=[wrapper_res]):
                    with patch("gear_optimizer.solver.genetic.create_evaluation_functions") as mock_create:
                        # Setup mocks for helper returns
                        mock_create.return_value = (
                            lambda x: 0,  # score_candidate
                            lambda x: "key",  # genome_key
                            lambda x: None,  # check_persistent
                            lambda x: wrapper_res,  # evaluate_local
                            {},  # cache
                            lambda x: [wrapper_res],  # batch_eval
                        )

                        # Use minimal depth to finish fast
                        best_data, best_gear, best_minis, _, _, _, _ = solve_coevolution_genetic(
                            cfg,
                            base_stats_fixed,
                            {},
                            calc_song,
                            ref_arrays,
                            all_gears,
                            all_minis,
                            gears_by_name,
                            minis_by_name,
                            ga_depth=1,
                            ga_settings=None,  # Use defaults from mocked cfg
                        )

                        assert isinstance(best_data, dict)
                        # Returned payload is the inner "Data" dict, not the wrapper.
                        assert "Genome" not in best_data
                        assert best_data.get("Score") == 1000
                        # Solver injects BaseScore into the inner data dict for DB storage.
                        assert best_data.get("BaseScore") == 1000


if __name__ == "__main__":
    unittest.main()
