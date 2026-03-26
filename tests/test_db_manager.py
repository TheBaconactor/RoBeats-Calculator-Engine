from pathlib import Path


def _entry(*, score: int, fg_score: int = 0) -> dict:
    return {
        "score": int(score),
        "fg_score": int(fg_score),
        "gear": ["Test Hat"],
        "minis": ["Test Mini"],
        "details": {
            "Stats": {
                "Perfect Points": 100,
                "Combo Multiplier": 100,
                "Fever Multiplier": 100,
                "Fever Fill Rate": 100,
                "Fever Time": 100,
                "Chill": 10,
                "Vibe": 10,
                "Beat": 10,
                "Flow": 10,
                "Rush": 10,
            },
            "GemCounts": {},
            "PrimaryColor": "Rush",
            "SecondaryColor": "Flow",
            "SelectedElement": "Rush",
        },
        "force": None,
    }


def test_evolution_db_manager_from_env_uses_evolution_db_path(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.delenv("EVOLUTION_OVERLAY_DB_PATH", raising=False)
    monkeypatch.delenv("METAFINDER_EVOLUTION_OVERLAY_DB", raising=False)

    db = EvolutionDbManager.from_env()
    assert db.db_path == str(db_path)
    assert db.overlay_db_path is None


def test_evolution_db_manager_from_env_include_overlay_wires_overlay_path(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.db_manager import EvolutionDbManager

    db_path = tmp_path / "evolution.db"
    overlay = tmp_path / "overlay.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    monkeypatch.setenv("EVOLUTION_OVERLAY_DB_PATH", str(overlay))

    db = EvolutionDbManager.from_env(include_overlay=True)
    assert db.db_path == str(db_path)
    assert db.overlay_db_path == str(overlay)


def test_save_loadouts_batch_persists_under_explicit_baseline_team_buff(tmp_path: Path, monkeypatch):
    from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch

    db_path = tmp_path / "evolution.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    init_db()

    song = "pytest_baseline_team_buff"
    save_loadouts_batch(song, [_entry(score=1234)], team_buff="T10")

    conn = get_db_connection(str(db_path))
    try:
        row = conn.execute(
            "SELECT team_buff, score FROM team_buff_loadouts WHERE song_name = ? LIMIT 1",
            (song,),
        ).fetchone()
        assert row is not None
        assert str(row["team_buff"]) == "T10"
        assert int(row["score"]) == 1234
    finally:
        conn.close()

