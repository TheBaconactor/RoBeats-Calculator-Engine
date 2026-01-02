import json

import pytest


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test_swing_detector.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(path))
    from gear_optimizer.data.database import init_db

    init_db()
    return str(path)


def test_swing_json_schema_and_roundtrip(db_path):
    from gear_optimizer.data.database import get_db_connection, save_loadouts_batch

    song = "pytest_swing_song"

    entry = {
        "score": 1000,
        "fg_score": 1500,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"GemCounts": {"Element": 0}, "Stats": {"Perfect Points": 0, "Combo Multiplier": 0}},
        "force": {"details": {"ForceGreats": {"config": {"NonFever1": 1}}}},
        # SwingDetector payloads (zeros should be dropped on persist)
        "swing_score": [0, -3, 5, 0],
        "swing_fg": [0, 7],
    }

    save_loadouts_batch(song, [entry])

    with get_db_connection(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(loadouts);").fetchall()}
        assert "swing_json" in cols
        cols_fg = {row[1] for row in conn.execute("PRAGMA table_info(fg_loadouts);").fetchall()}
        assert "swing_json" in cols_fg

        row = conn.execute(
            "SELECT swing_json FROM loadouts WHERE song_name = ? ORDER BY score DESC LIMIT 1",
            (song,),
        ).fetchone()
        assert row is not None
        assert json.loads(row["swing_json"]) == [-3, 5]

        row_fg = conn.execute(
            "SELECT swing_json FROM fg_loadouts WHERE song_name = ? ORDER BY fg_score DESC LIMIT 1",
            (song,),
        ).fetchone()
        assert row_fg is not None
        assert json.loads(row_fg["swing_json"]) == [7]

