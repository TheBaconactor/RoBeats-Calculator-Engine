"""
Unit tests for gear_optimizer.models module.
Tests the new SongContext and SolverParams dataclasses.
"""
import pytest
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.models import SongContext, SolverParams, GASettings


class TestSongContext:
    """Tests for SongContext dataclass."""

    def test_from_calc_song_basic(self):
        """Create SongContext from a calc_song dictionary."""
        calc_song = {
            "metadata": {
                "Song Name": "Test Song (Hard)",
                "Difficulty": "10",
                "Primary Color": "Chill",
                "Secondary Color": "Flow",
                "Long Notes": 50,
                "Last Note Time": 180.5,
            },
            "song_data": {
                "timestamps": np.array([0.5, 1.0, 1.5, 2.0]),
            },
        }
        ctx = SongContext.from_calc_song(calc_song)
        
        assert ctx.name == "Test Song (Hard)"
        assert ctx.difficulty == "10"
        assert ctx.primary_color == "Chill"
        assert ctx.secondary_color == "Flow"
        assert ctx.total_notes == 4
        assert ctx.long_notes == 50
        assert ctx.last_note_time == pytest.approx(180.5)
        assert len(ctx.timestamps) == 4

    def test_from_calc_song_empty(self):
        """Handle missing metadata gracefully."""
        calc_song = {}
        ctx = SongContext.from_calc_song(calc_song)
        
        assert ctx.name == ""
        assert ctx.primary_color == ""
        assert ctx.total_notes == 0

    def test_to_calc_song_round_trip(self):
        """Round-trip: from_calc_song -> to_calc_song preserves data."""
        original = {
            "metadata": {
                "Song Name": "Round Trip Test",
                "Difficulty": "Hard",
                "Primary Color": "Rush",
                "Secondary Color": "Vibe",
                "Long Notes": 25,
                "Last Note Time": 90.0,
            },
            "song_data": {
                "timestamps": np.array([1.0, 2.0, 3.0]),
            },
        }
        ctx = SongContext.from_calc_song(original)
        result = ctx.to_calc_song()
        
        assert result["metadata"]["Song Name"] == "Round Trip Test"
        assert result["metadata"]["Primary Color"] == "Rush"
        assert len(result["song_data"]["timestamps"]) == 3


class TestSolverParams:
    """Tests for SolverParams dataclass."""

    def test_from_cfg_data_basic(self):
        """Create SolverParams from cfg_data dictionary."""
        cfg_data = {
            "selected_color": "Chill",
            "user_ft": 5,
            "user_ff": 10,
            "user_pp": 15,
            "user_cm": 20,
            "user_fm": 3,
            "static_elem_input": 2,
            "use_gpu": True,
        }
        params = SolverParams.from_cfg_data(cfg_data, gem_budget=90)
        
        assert params.gem_budget == 90
        assert params.selected_color == "Chill"
        assert params.user_ft == 5
        assert params.user_ff == 10
        assert params.user_pp == 15
        assert params.user_cm == 20
        assert params.user_fm == 3
        assert params.use_gpu is True

    def test_from_cfg_data_defaults(self):
        """Missing keys use default values."""
        cfg_data = {"selected_color": "Rush"}
        params = SolverParams.from_cfg_data(cfg_data)
        
        assert params.selected_color == "Rush"
        assert params.user_ft == 0
        assert params.use_gpu is False

    def test_to_cfg_data_round_trip(self):
        """Round-trip: from_cfg_data -> to_cfg_data preserves data."""
        original = {
            "selected_color": "Beat",
            "user_ft": 7,
            "user_ff": 8,
            "user_pp": 9,
            "user_cm": 10,
            "user_fm": 11,
            "static_elem_input": 5,
            "use_gpu": False,
        }
        params = SolverParams.from_cfg_data(original)
        result = params.to_cfg_data()
        
        assert result["selected_color"] == "Beat"
        assert result["user_ft"] == 7
        assert result["use_gpu"] is False

    def test_direct_construction(self):
        """Direct construction with required args works."""
        params = SolverParams(gem_budget=60, selected_color="Vibe")
        
        assert params.gem_budget == 60
        assert params.selected_color == "Vibe"
        assert params.user_ft == 0  # Default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
