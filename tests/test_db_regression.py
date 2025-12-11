"""
Database regression tests for loadout details integrity.

These tests verify that the full `details_json` field (including stats, 
multipliers, gem counts, and fever data) survives a round-trip through
the database save/load cycle.

This prevents silent data loss like empty `details_json` in production.
"""

import pytest
import tempfile
import os
import sys
import numpy as np  # Test numpy type serialization

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.database import (
    get_db_connection,
    save_loadout_to_db,
    save_loadouts_batch,
    get_best_loadouts,
    json_dumps,
    json_loads,
    EVOLUTION_DB_PATH,
)


# --- Fixtures ---

@pytest.fixture
def temp_db(monkeypatch):
    """Create a temporary database and patch the path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    # Patch the get_evolution_db_path function to return our temp path
    import gear_optimizer.database as db_module
    monkeypatch.setattr(db_module, "get_evolution_db_path", lambda: db_path)
    
    # Initialize tables
    conn = get_db_connection(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS songs (
            name TEXT PRIMARY KEY,
            best_score INTEGER DEFAULT 0,
            best_fg_score INTEGER DEFAULT 0,
            last_updated REAL
        );
        CREATE TABLE IF NOT EXISTS loadouts (
            song_name TEXT,
            loadout_hash TEXT,
            score INTEGER,
            fg_score INTEGER DEFAULT 0,
            gear_json TEXT,
            minis_json TEXT,
            details_json TEXT,
            force_details_json TEXT,
            timestamp REAL,
            PRIMARY KEY (song_name, loadout_hash),
            FOREIGN KEY (song_name) REFERENCES songs(name)
        );
        CREATE INDEX IF NOT EXISTS idx_loadouts_score ON loadouts (song_name, score DESC);
    """)
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except Exception:
        pass



# --- Test Data: Real-World Loadout Structure ---

def create_real_world_details():
    """
    Create a details dict that mirrors real production data.
    
    This structure is based on the actual output of scoring.py.
    """
    return {
        "Stats": {
            "Chill": 150,
            "Vibe": 120,
            "Beat": 80,
            "Flow": 200,
            "Rush": 50,
            "PerfectPoints": 250,
            "ComboMultiplier": 2.5,
            "FeverMultiplier": 3.5,
            "FeverFillRate": 1.25,
            "FeverTime": 1.1,
        },
        "SelectedElement": "Flow",
        "PrimaryColor": "Flow",
        "GemCounts": {
            "Red": 15,
            "Blue": 20,
            "Green": 10,
            "Yellow": 25,
            "Purple": 20,
            "Element Overflow": 5,
        },
        "PerfectPoints": 250,
        "ComboMultiplier": 2.5,
        "FeverMultiplier": 3.5,
        "FeverFillRate": 1.25,
        "FeverTime": 1.1,
        "FeverTimelines": [
            {"start": 10, "end": 20, "multiplier": 3.5},
            {"start": 50, "end": 65, "multiplier": 3.5},
        ],
        "TotalScore": 31558933,
    }


def create_real_world_gear():
    """Create gear list matching production format."""
    return [
        {"Name": "The Games: Hidden Shine", "type": "Head"},
        {"Name": "Legendary Musketeer's Ruffles", "type": "Neck"},
        {"Name": "Legendary Flow Commander's Visor", "type": "Face"},
        {"Name": "Legendary Flow Commander's Jumpsuit", "type": "Body"},
        {"Name": "No-Scope Loadout", "type": "Back"},
        {"Name": "Legendary Musketeer's Trousers", "type": "Legs"},
    ]


def create_real_world_minis():
    """Create minis list matching production format."""
    return [
        {"Name": "Kagi", "Chill": 10, "Flow": 20},
        {"Name": "Artcore Maid Marie", "Vibe": 15, "Beat": 10},
        {"Name": "Project Skylate", "Rush": 5, "Flow": 25},
    ]


# --- Tests ---

class TestDetailsJsonIntegrity:
    """Tests for details_json round-trip integrity."""

    def test_single_loadout_full_details_preserved(self, temp_db):
        """
        CRITICAL: Verify that a fully-populated details dict survives save/load.
        
        This is the primary regression test for the bug where details were lost.
        """
        song_name = "Test Song (Hard) by TestArtist"
        score = 31558933
        fg_score = 30000000
        gear = create_real_world_gear()
        minis = create_real_world_minis()
        details = create_real_world_details()
        
        # Save
        save_loadout_to_db(song_name, score, fg_score, gear, minis, details)
        
        # Load
        loadouts = get_best_loadouts(song_name, limit=1)
        
        assert len(loadouts) == 1, "Loadout was not saved"
        loaded = loadouts[0]
        
        # Verify score
        assert loaded["score"] == score
        
        # CRITICAL: Verify details were preserved
        loaded_details = loaded["details"]
        assert loaded_details is not None, "details_json was not saved!"
        assert loaded_details != {}, "details_json is empty!"
        
        # Deep equality checks
        assert loaded_details.get("Stats") == details["Stats"], \
            f"Stats mismatch: {loaded_details.get('Stats')} != {details['Stats']}"
        
        assert loaded_details.get("GemCounts") == details["GemCounts"], \
            f"GemCounts mismatch: {loaded_details.get('GemCounts')}"
        
        assert loaded_details.get("FeverMultiplier") == details["FeverMultiplier"]
        assert loaded_details.get("FeverFillRate") == details["FeverFillRate"]
        assert loaded_details.get("PerfectPoints") == details["PerfectPoints"]
        assert loaded_details.get("SelectedElement") == details["SelectedElement"]

    def test_batch_save_preserves_details(self, temp_db):
        """
        Verify that save_loadouts_batch also preserves full details.
        
        This tests the batch code path used by the GA pipeline.
        """
        song_name = "Batch Test Song (Expert)"
        entries = [
            {
                "score": 25000000,
                "fg_score": 24000000,
                "gear": create_real_world_gear(),
                "minis": create_real_world_minis(),
                "details": create_real_world_details(),
                "force": None,
            },
            {
                "score": 26000000,
                "fg_score": 25000000,
                # Use DIFFERENT gear to get a unique loadout hash (avoid deduplication)
                "gear": [
                    {"Name": "Alternative Hat", "type": "Head"},
                    {"Name": "Alternative Shirt", "type": "Body"},
                ],
                "minis": [{"Name": "Alternative Mini"}],
                "details": {
                    "Stats": {"Chill": 100, "Flow": 150},
                    "PerfectPoints": 200,
                    "GemCounts": {"Red": 10},
                },
                "force": None,
            },
        ]

        
        # Save batch
        save_loadouts_batch(song_name, entries)
        
        # Load and verify
        loadouts = get_best_loadouts(song_name, limit=2)
        
        assert len(loadouts) == 2, f"Expected 2 loadouts, got {len(loadouts)}"
        
        # Check both have non-empty details
        for i, loadout in enumerate(loadouts):
            assert loadout["details"] is not None, f"Loadout {i} details is None"
            assert loadout["details"] != {}, f"Loadout {i} details is empty"
            assert "Stats" in loadout["details"], f"Loadout {i} missing Stats"


class TestNumpyTypeSerialization:
    """
    Test that numpy types (common in Taichi/GPU calculations) serialize correctly.
    
    This is a suspected cause of silent serialization failures.
    """

    def test_numpy_int_in_details(self, temp_db):
        """Numpy integers should be converted and saved correctly."""
        song_name = "Numpy Int Test"
        details = {
            "Stats": {
                "Chill": np.int64(150),  # Numpy type
                "Flow": np.int32(200),
            },
            "PerfectPoints": np.int64(250),
        }
        
        save_loadout_to_db(
            song_name, 1000000, 900000,
            [{"Name": "Test Gear"}], [{"Name": "Test Mini"}],
            details
        )
        
        loadouts = get_best_loadouts(song_name, limit=1)
        assert len(loadouts) == 1
        loaded = loadouts[0]["details"]
        
        # Values should be preserved (as Python ints)
        assert loaded["Stats"]["Chill"] == 150
        assert loaded["Stats"]["Flow"] == 200
        assert loaded["PerfectPoints"] == 250

    def test_numpy_float_in_details(self, temp_db):
        """Numpy floats should be converted and saved correctly."""
        song_name = "Numpy Float Test"
        details = {
            "FeverMultiplier": np.float64(3.5),
            "FeverFillRate": np.float32(1.25),
        }
        
        save_loadout_to_db(
            song_name, 1000000, 900000,
            [{"Name": "Test Gear"}], [{"Name": "Test Mini"}],
            details
        )
        
        loadouts = get_best_loadouts(song_name, limit=1)
        loaded = loadouts[0]["details"]
        
        assert abs(loaded["FeverMultiplier"] - 3.5) < 0.001
        assert abs(loaded["FeverFillRate"] - 1.25) < 0.001


class TestEmptyAndNullCases:
    """Test edge cases that might cause silent failures."""

    def test_empty_details_saved_as_empty(self, temp_db):
        """Explicitly empty details should be saved as empty, not None."""
        song_name = "Empty Details Test"
        
        save_loadout_to_db(
            song_name, 500000, 400000,
            [{"Name": "Gear"}], [{"Name": "Mini"}],
            {}  # Explicitly empty
        )
        
        loadouts = get_best_loadouts(song_name, limit=1)
        # Empty dict should remain empty dict, not become None
        assert loadouts[0]["details"] == {}

    def test_none_details_handled(self, temp_db):
        """None details should not crash and should return empty dict on load."""
        song_name = "None Details Test"
        
        save_loadout_to_db(
            song_name, 500000, 400000,
            [{"Name": "Gear"}], [{"Name": "Mini"}],
            None  # None instead of dict
        )
        
        loadouts = get_best_loadouts(song_name, limit=1)
        # None becomes empty dict on load (per get_best_loadouts logic)
        assert loadouts[0]["details"] == {}


class TestJsonSerializationEdgeCases:
    """Test JSON serialization edge cases."""

    def test_nested_structures_preserved(self, temp_db):
        """Deeply nested structures should be preserved."""
        song_name = "Nested Test"
        details = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": 42,
                        "list": [1, 2, 3],
                    }
                }
            }
        }
        
        save_loadout_to_db(
            song_name, 100, 90,
            [{"Name": "G"}], [{"Name": "M"}],
            details
        )
        
        loadouts = get_best_loadouts(song_name, limit=1)
        assert loadouts[0]["details"]["level1"]["level2"]["level3"]["value"] == 42
        assert loadouts[0]["details"]["level1"]["level2"]["level3"]["list"] == [1, 2, 3]

    def test_special_characters_in_values(self, temp_db):
        """Special characters should not break serialization."""
        song_name = "Special Chars Test"
        details = {
            "note": "Test with 'quotes' and \"double quotes\"",
            "unicode": "日本語テスト",
            "emoji": "🎮🎵",
        }
        
        save_loadout_to_db(
            song_name, 100, 90,
            [{"Name": "G"}], [{"Name": "M"}],
            details
        )
        
        loadouts = get_best_loadouts(song_name, limit=1)
        assert loadouts[0]["details"]["unicode"] == "日本語テスト"
        assert loadouts[0]["details"]["emoji"] == "🎮🎵"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
