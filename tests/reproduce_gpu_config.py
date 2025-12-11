
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import configparser
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gear_optimizer import scoring

class TestGPUConfig(unittest.TestCase):
    def setUp(self):
        # Mock ref arrays
        self.ref_arrays = {
            "Perfect Points": np.zeros(101),
            "Combo Multiplier": np.zeros(101),
            "Fever Multiplier": np.zeros(101),
            "Fever Fill Rate": np.zeros(101),
            "Fever Time": np.zeros(101),
        }
        
        # Mock song data
        self.calc_song = {
            "metadata": {
                "Song Name": "Test Song",
                "Long Notes": 0,
                "Last Note Time": 10.0,
                "Primary Color": "Rush",
                "Secondary Color": "Flow"
            },
            "song_data": {
                "timestamps": np.array([1.0, 2.0, 3.0])
            }
        }
        
        # Initial stats
        self.stats = {
            "Perfect Points": 0,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Beat": 0,
            "Vibe": 0,
            "Rush": 0,
            "Flow": 0,
            "Chill": 0
        }

    @patch('gear_optimizer.scoring.HAS_TAICHI', True)
    @patch('gear_optimizer.scoring.taichi_accelerator')
    def test_gpu_config_ignored(self, mock_taichi):
        """Test that UseGPU in config is currently ignored in solve_best_fever_combination"""
        
        # Setup mock return for GPU solver
        mock_taichi.solve_ftff_grid_taichi.return_value = (1000, 10, 10, 1, 1, 1, 0)
        
        # Create config with UseGPU=True
        cfg = configparser.ConfigParser()
        cfg.add_section("IterationEngine")
        cfg.set("IterationEngine", "UseGPU", "True")
        
        # Run solver
        # We expect this to NOT call taichi because usage depends on override_cfg currently
        with patch('gear_optimizer.scoring.solve_ftff_grid_jit') as mock_cpu:
            mock_cpu.return_value = (900, 5, 5, 0, 0, 0, 0)
            
            scoring.solve_best_fever_combination(
                cfg,
                self.stats,
                self.calc_song,
                self.ref_arrays,
                silent=True
            )
            
            # This assertion confirms the BUG:
            # We EXPECT taichi NOT to be called despite config saying True
            # because the code only checks override_cfg
            mock_taichi.solve_ftff_grid_taichi.assert_not_called()
            mock_cpu.assert_called()
            print("\n[CONFIRMED] GPU path was skipped despite UseGPU=True in config")

if __name__ == '__main__':
    unittest.main()
