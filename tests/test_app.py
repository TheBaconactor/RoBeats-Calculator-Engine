"""
Unit tests for gear_optimizer.app module.
"""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.app import GearOptimizerApp


class TestGearOptimizerApp:
    """Tests for GearOptimizerApp class."""

    @patch("gear_optimizer.app.init_db")
    @patch("gear_optimizer.app.auto_merge_secondary_databases")
    @patch("gear_optimizer.app.load_all_gears_list")
    @patch("gear_optimizer.app.load_all_minis_list")
    @patch("gear_optimizer.app.read_table")
    @patch("gear_optimizer.app.RunConfig.from_cfg")
    def test_setup(
        self, 
        mock_from_cfg,
        mock_read_table, 
        mock_load_minis, 
        mock_load_gears, 
        mock_merge, 
        mock_init_db
    ):
        """Test application setup."""
        # Setup mocks
        mock_read_table.return_value = []
        mock_load_gears.return_value = []
        mock_load_minis.return_value = []
        mock_merge.return_value = (True, "Merged")
        
        # Mock config
        mock_cfg_obj = MagicMock()
        mock_from_cfg.return_value = mock_cfg_obj
        
        # Instantiate
        # We need a dummy config file or mock open
        with patch("configparser.ConfigParser.read") as mock_read:
            app = GearOptimizerApp("dummy_config.ini")
            # We mock load_paths_cache inside setup
            with patch("gear_optimizer.config.load_paths_cache", return_value={}):
                app.setup()
            
            # Assertions
            mock_read.assert_called()
            mock_init_db.assert_called()
            mock_merge.assert_called()
            mock_load_gears.assert_called()
            mock_load_minis.assert_called()
            assert app.run_config == mock_cfg_obj

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
