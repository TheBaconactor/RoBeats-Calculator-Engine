import json
import pytest

from gear_optimizer.data.database import (
    get_db_connection,
    init_db,
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

    row = db_connection.execute(
        "SELECT score, details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
        (song,),
    ).fetchone()
    assert row["score"] == 1000

    # 2. Attempt Overwrite with Low Score via Batch
    entry_low = {"score": 900, "fg_score": 400, "gear": gear, "minis": minis, "details": {"test": "low"}, "force": None}
    save_loadouts_batch(song, [entry_low])

    row = db_connection.execute(
        "SELECT score, details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
        (song,),
    ).fetchone()
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

    row = db_connection.execute(
        "SELECT score, details_json FROM team_buff_loadouts WHERE song_name=? AND team_buff='T5'",
        (song,),
    ).fetchone()
    assert row["score"] == 1100
    assert json.loads(row["details_json"])["test"] == "higher"
