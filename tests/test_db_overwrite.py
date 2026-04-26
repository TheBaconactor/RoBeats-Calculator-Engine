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


def test_save_loadouts_batch_deferred_fg_update_preserves_base_details(db_connection):
    """
    Deferred FG-only persistence updates must not overwrite the base row's details payload.

    This guards against persistence-path bugs where an FG variant payload (FT/FF/GemCounts/Stats)
    is accidentally paired with the base score on an equal-score upsert.
    """
    song = "Test Song Deferred FG"
    gear = ["G1", "G2"]
    minis = ["M1"]

    entry_base = {
        "score": 1000,
        "fg_score": 0,
        "gear": gear,
        "minis": minis,
        "details": {"test": "base"},
        "force": None,
    }
    save_loadouts_batch(song, [entry_base])

    entry_deferred_fg = {
        "score": 1000,  # same base score
        "fg_score": 1500,
        "gear": gear,
        "minis": minis,
        "details": {"test": "fg_variant"},
        "force": {"ForceGreats": {"config": {"NonFever1": 1}, "final_score": 1500}},
        "_deferred_fg_update": True,
    }
    save_loadouts_batch(song, [entry_deferred_fg])

    row = db_connection.execute(
        """
        SELECT score, fg_score, details_json, force_details_json
        FROM team_buff_loadouts
        WHERE song_name=? AND team_buff='T5'
        """,
        (song,),
    ).fetchone()
    assert row["score"] == 1000
    assert row["fg_score"] == 1500
    assert json.loads(row["details_json"])["test"] == "base"
    assert row["force_details_json"] is None

    fg_row = db_connection.execute(
        """
        SELECT force_details_json
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND team_buff='T5'
        """,
        (song,),
    ).fetchone()
    assert fg_row is not None
    assert fg_row["force_details_json"] is not None


def test_team_buff_fg_loadouts_upsert_tie_updates_base_score(db_connection):
    """
    `team_buff_fg_loadouts` upserts must keep `score` consistent with the chosen payload.

    On an equal `fg_score` tie for the same (song, team_buff, loadout_hash), prefer the entry with the higher
    base `score` and update the stored payload accordingly.
    """
    song = "Test Song FG Tie"
    gear = ["G1", "G2"]
    minis = ["M1"]

    entry_low_base = {
        "score": 900,
        "fg_score": 2000,
        "gear": gear,
        "minis": minis,
        "details": {"test": "low_base"},
        "force": {"ForceGreats": {"config": {"NonFever1": 1}, "final_score": 2000}},
    }
    save_loadouts_batch(song, [entry_low_base])

    row = db_connection.execute(
        """
        SELECT score, fg_score, details_json
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND team_buff='T5'
        """,
        (song,),
    ).fetchone()
    assert row["score"] == 900
    assert row["fg_score"] == 2000
    assert json.loads(row["details_json"])["test"] == "low_base"

    entry_higher_base = {
        "score": 1000,
        "fg_score": 2000,  # tie on fg_score, higher base score should win
        "gear": gear,
        "minis": minis,
        "details": {"test": "higher_base"},
        "force": {"ForceGreats": {"config": {"NonFever1": 1}, "final_score": 2000}},
    }
    save_loadouts_batch(song, [entry_higher_base])

    row = db_connection.execute(
        """
        SELECT score, fg_score, details_json
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND team_buff='T5'
        """,
        (song,),
    ).fetchone()
    assert row["score"] == 1000
    assert row["fg_score"] == 2000
    assert json.loads(row["details_json"])["test"] == "higher_base"


def test_db_write_integrity_verifier_does_not_fail_when_db_has_better_fg(db_connection, monkeypatch):
    """
    Strict DB write-integrity verification should not fail when the DB already contains a better FG row.

    Scenario:
    - Row A persists with higher `fg_score` but lower base `score`.
    - Row B attempts to persist a higher base `score` but lower `fg_score`.

    The FG table should keep Row A (because FG leaderboard is ordered by `fg_score`), and strict verification should
    not treat the base-score mismatch as an override/race.
    """
    monkeypatch.setenv("DB_VERIFY_WRITE_INTEGRITY", "1")
    monkeypatch.setenv("DB_STRICT_WRITE_INTEGRITY", "1")

    song = "Test Song FG Verifier"
    gear = ["G1", "G2"]
    minis = ["M1"]

    entry_best_fg_lower_base = {
        "score": 900,
        "fg_score": 2000,
        "gear": gear,
        "minis": minis,
        "details": {"test": "best_fg"},
        "force": {"ForceGreats": {"config": {"NonFever1": 1}, "final_score": 2000}},
    }
    save_loadouts_batch(song, [entry_best_fg_lower_base])

    entry_worse_fg_higher_base = {
        "score": 1000,
        "fg_score": 1500,
        "gear": gear,
        "minis": minis,
        "details": {"test": "worse_fg_higher_base"},
        "force": {"ForceGreats": {"config": {"NonFever1": 1}, "final_score": 1500}},
    }
    save_loadouts_batch(song, [entry_worse_fg_higher_base])

    row = db_connection.execute(
        """
        SELECT score, fg_score, details_json
        FROM team_buff_fg_loadouts
        WHERE song_name=? AND team_buff='T5'
        """,
        (song,),
    ).fetchone()
    assert row["fg_score"] == 2000
    assert row["score"] == 900
    assert json.loads(row["details_json"])["test"] == "best_fg"
