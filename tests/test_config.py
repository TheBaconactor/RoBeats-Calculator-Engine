"""
Unit tests for gear_optimizer.config module.
Tests RunConfig and configuration utilities.
"""
import pytest
import configparser
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.config import RunConfig


class TestRunConfig:
    """Tests for RunConfig dataclass."""

    def test_from_cfg_defaults(self):
        """Empty config should use default values."""
        cfg = configparser.ConfigParser()
        rc = RunConfig.from_cfg(cfg)
        
        assert rc.meta_finder is False
        assert rc.enable_fever is False
        assert rc.use_gpu is False
        assert rc.loop_forever is False
        assert rc.ga_depth == 50

    def test_from_cfg_with_values(self):
        """Config values should be parsed correctly."""
        cfg = configparser.ConfigParser()
        cfg.add_section("IterationEngine")
        cfg.set("IterationEngine", "MetaFinder", "true")
        cfg.set("IterationEngine", "UseGPU", "true")
        cfg.set("IterationEngine", "GA_SearchDepth", "100")
        
        rc = RunConfig.from_cfg(cfg)
        
        assert rc.meta_finder is True
        assert rc.enable_fever is True  # Inherits from meta_finder
        assert rc.enable_mini is True
        assert rc.enable_gear is True
        assert rc.use_gpu is True
        assert rc.ga_depth == 100

    def test_any_finder_active_true(self):
        """any_finder_active should be True when any finder is enabled."""
        rc = RunConfig(enable_fever=True)
        assert rc.any_finder_active is True

    def test_any_finder_active_false(self):
        """any_finder_active should be False when no finder is enabled."""
        rc = RunConfig()
        assert rc.any_finder_active is False

    def test_force_greats_mode(self):
        """ForceGreats mode should be parsed correctly."""
        cfg = configparser.ConfigParser()
        cfg.add_section("IterationEngine")
        cfg.set("IterationEngine", "ForceGreatsMode", "true")
        cfg.set("IterationEngine", "ForceGreatsFinder", "true")
        
        rc = RunConfig.from_cfg(cfg)
        
        assert rc.force_greats_mode is True
        assert rc.force_greats_finder is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
