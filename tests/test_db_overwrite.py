import json
import pytest

from gear_optimizer.data.database import (
    get_db_connection,
    init_db,
    save_loadout_to_db,
    save_loadouts_batch,
)


@pytest.fixture
def db_connection(tmp_path, monkeypatch):
    db_path = tmp_path / "test_overwrite.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    conn = get_db_connection(str(db_path))
    try:
        yield conn
    finally:
        conn.close()


def test_save_loadout_singular_overwrite(db_connection):
    """Test that singular save_loadout_to_db protects high scores."""
    song = "Test Song"
    gear = ["G1", "G2"]
    minis = ["M1"]

    # 1. Save High Score
    save_loadout_to_db(song, 1000, 500, gear, minis, {"test": "high"})

    # Verify insert
    row = db_connection.execute("SELECT score, details_json FROM loadouts").fetchone()
    assert row["score"] == 1000
    assert json.loads(row["details_json"])["test"] == "high"

    # 2. Attempt Overwrite with Low Score (The Bug)
    save_loadout_to_db(song, 900, 400, gear, minis, {"test": "low"})

    # Verify protection (Should still be 1000/high)
    row = db_connection.execute("SELECT score, details_json FROM loadouts").fetchone()
    assert row["score"] == 1000, "High score was overwritten by low score!"
    assert json.loads(row["details_json"])["test"] == "high", "High score details were overwritten!"

    # 3. Overwrite with Even Higher Score (Desired behavior)
    save_loadout_to_db(song, 1100, 600, gear, minis, {"test": "higher"})

    # Verify update
    row = db_connection.execute("SELECT score, details_json FROM loadouts").fetchone()
    assert row["score"] == 1100
    assert json.loads(row["details_json"])["test"] == "higher"


def test_save_loadouts_batch_overwrite(db_connection):
    """Test that batch save_loadouts_batch protects high scores."""
    song = "Test Song Batch"
    gear = ["G1", "G2"]
    minis = ["M1"]

    # 1. Save High Score via Batch
    entry_high = {
        "score": 1000,
        "fg_score": 500,
        "gear": gear,
        "minis": minis,
        "details": {"test": "high"},
        "force": None,
    }
    save_loadouts_batch(song, [entry_high])

    row = db_connection.execute("SELECT score, details_json FROM loadouts WHERE song_name=?", (song,)).fetchone()
    assert row["score"] == 1000

    # 2. Attempt Overwrite with Low Score via Batch
    entry_low = {"score": 900, "fg_score": 400, "gear": gear, "minis": minis, "details": {"test": "low"}, "force": None}
    save_loadouts_batch(song, [entry_low])

    row = db_connection.execute("SELECT score, details_json FROM loadouts WHERE song_name=?", (song,)).fetchone()
    assert row["score"] == 1000, "High score was overwritten by low score in batch!"
    assert json.loads(row["details_json"])["test"] == "high"

    # 3. Overwrite with Higher Score
    entry_higher = {
        "score": 1100,
        "fg_score": 600,
        "gear": gear,
        "minis": minis,
        "details": {"test": "higher"},
        "force": None,
    }
    save_loadouts_batch(song, [entry_higher])

    row = db_connection.execute("SELECT score, details_json FROM loadouts WHERE song_name=?", (song,)).fetchone()
    assert row["score"] == 1100
    assert json.loads(row["details_json"])["test"] == "higher"
