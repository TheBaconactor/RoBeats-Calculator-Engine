
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer.helpers.ga_helpers import create_evaluation_functions
from gear_optimizer.data.database import get_loadout_hash

class TestHeuristicPersistence(unittest.TestCase):
    def test_persistent_cache_respects_heuristic(self):
        # Setup mocks
        p_color = "Rush"
        base_stats_fixed = {}
        cfg_data = {
            "selected_color": "Rush",
            "fg_heuristic": True,  # ENABLED
            "user_ft": 0, "user_ff": 0, "user_pp": 0, "user_cm": 0, "user_fm": 0,
            "static_elem_input": 0
        }
        calc_song = {"metadata": {"Primary Color": "Rush", "Secondary Color": "Beat"}}
        ref_arrays = {}
        
        # Mock genome
        genome = [{"Name": "Gene1"}, {"Name": "Gene2"}] # 2 items? 
        # Genome usually has 6 gear + 3 minis = 9 items
        genome = [{"Name": f"Item{i}"} for i in range(9)]
        
        h = get_loadout_hash(genome[:6], genome[6:])
        
        # Mock known_loadouts with Base Score 1000
        known_loadouts = {
            h: {"score": 1000, "fg_score": 1050, "force_data": {}}
        }
        
        cache_hits_tracker = [0]
        
        # Create evaluation functions
        (
            score_candidate,
            genome_key,
            check_persistent_cache,
            evaluate_genome_local,
            evaluation_cache,
            batch_evaluator,
        ) = create_evaluation_functions(
            p_color,
            base_stats_fixed,
            cfg_data,
            calc_song,
            ref_arrays,
            known_loadouts,
            cache_hits_tracker
        )
        
        # Mock estimate_fg_potential to verify it is called
        with patch('gear_optimizer.helpers.ga_helpers.estimate_fg_potential') as mock_est:
            mock_est.return_value = 2000
            
            # Calling check_persistent_cache should return the entry
            res = check_persistent_cache(genome)
            self.assertIsNotNone(res)
            
            # The ISSUE: Does it return 1000 (Base) or boosted score?
            print(f"DB Score: 1000")
            print(f"Result Score: {res['Score']}")
            
            # Now let's try evaluate_genome_local, which calls check_persistent_cache
            res_local = evaluate_genome_local(genome)
            print(f"Evaluate Local Score: {res_local['Score']}")
            
            if res['Score'] == 2000:
                print("SUCCESS: Heuristic WAS applied (Score=2000).")
            else:
                print(f"FAIL: Heuristic was NOT applied (Score={res['Score']})!")

if __name__ == "__main__":
    unittest.main()
