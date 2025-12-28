import sqlite3

import pytest

from gear_optimizer.data.database import (
    delete_pending_fg_job,
    get_db_connection,
    init_db,
    list_pending_fg_jobs,
    upsert_pending_fg_job,
)


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test_pending_fg_jobs.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(path))
    init_db()
    return str(path)


def test_pending_fg_jobs_table_exists_and_schema_migrates(db_path):
    conn = get_db_connection(db_path)
    try:
        ver = conn.execute("PRAGMA user_version;").fetchone()[0]
        assert int(ver) >= 2
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='pending_fg_jobs'"
            ).fetchall()
        }
        assert "pending_fg_jobs" in tables
    finally:
        conn.close()


def test_upsert_list_delete_pending_fg_jobs_roundtrip(db_path):
    song = "Pending FG Song"
    candidates = [
        {
            "Score": 123,
            "BaseScore": 123,
            "Gear": ["G1"],
            "Minis": ["M1"],
            "Data": {"Score": 123, "FT": 1, "FF": 2, "GemCounts": {"Perfect Points": 0}},
            "_fg_priority": 0,
        }
    ]

    upsert_pending_fg_job(song, candidates)
    jobs = list_pending_fg_jobs()
    got = next((j for j in jobs if j.get("song_name") == song), None)
    assert got is not None
    assert got.get("candidates") == candidates

    delete_pending_fg_job(song)
    jobs2 = list_pending_fg_jobs()
    assert next((j for j in jobs2 if j.get("song_name") == song), None) is None


def test_upsert_pending_fg_job_empty_deletes(db_path):
    song = "Pending FG Song Empty Delete"
    upsert_pending_fg_job(song, [{"Score": 1, "Gear": ["G1"], "Minis": ["M1"]}])
    assert next((j for j in list_pending_fg_jobs() if j.get("song_name") == song), None) is not None

    upsert_pending_fg_job(song, [])
    assert next((j for j in list_pending_fg_jobs() if j.get("song_name") == song), None) is None

