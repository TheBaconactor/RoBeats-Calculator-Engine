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
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": {"GemCounts": {"Element": 0}, "Stats": {"Perfect Points": 0, "Combo Multiplier": 0}},
        # Swing payloads (zeros should be dropped on persist)
        "swing_score": [0, 5, 0],
    }

    save_loadouts_batch(song, [entry])

    with get_db_connection(db_path) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(loadouts);").fetchall()}
        assert "swing_json" in cols

        row = conn.execute(
            "SELECT swing_json FROM loadouts WHERE song_name = ? ORDER BY score DESC LIMIT 1",
            (song,),
        ).fetchone()
        assert row is not None
        assert json.loads(row["swing_json"]) == [5]


def test_details_json_updates_when_swing_first_added_without_score_improvement(db_path):
    from gear_optimizer.data.database import get_db_connection, save_loadouts_batch

    song = "pytest_swing_details_song"

    base_details = {"GemCounts": {"Element": 0}, "Stats": {"Perfect Points": 0, "Combo Multiplier": 0}}
    entry1 = {
        "score": 1000,
        "fg_score": 0,
        "gear": ["G1", "G2", "G3", "G4", "G5", "G6"],
        "minis": ["M1", "M2", "M3"],
        "details": dict(base_details),
    }
    save_loadouts_batch(song, [entry1])

    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT details_json, swing_json FROM loadouts WHERE song_name = ? ORDER BY score DESC LIMIT 1",
            (song,),
        ).fetchone()
        assert row is not None
        assert row["swing_json"] is None
        details = json.loads(row["details_json"])
        assert "MockSwing" not in details

    entry2 = {
        **entry1,
        "details": {
            **base_details,
            "MockSwing": {
                "best_mode": "HITSIM",
                "best_seed": 123,
                "best_delta_vs_off": 5,
                "ff_stat": 60,
                "ft_stat": 43,
            },
        },
        "swing_score": [5],
    }
    save_loadouts_batch(song, [entry2])

    with get_db_connection(db_path) as conn:
        row = conn.execute(
            "SELECT details_json, swing_json FROM loadouts WHERE song_name = ? ORDER BY score DESC LIMIT 1",
            (song,),
        ).fetchone()
        assert row is not None
        assert json.loads(row["swing_json"]) == [5]
        details = json.loads(row["details_json"])
        assert details.get("MockSwing", {}).get("best_seed") == 123
