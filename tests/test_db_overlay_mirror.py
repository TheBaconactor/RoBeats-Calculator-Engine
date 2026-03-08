import json

from gear_optimizer.app_async_db import AsyncDbSaver
from gear_optimizer.data.database import get_db_connection, init_db, save_loadouts_batch


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


def test_save_loadouts_batch_respects_explicit_db_path(tmp_path, monkeypatch):
    canonical_db = tmp_path / "canonical.db"
    overlay_db = tmp_path / "overlay.db"
    song_name = "Overlay Path Song"

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    init_db()

    save_loadouts_batch(song_name, [_entry(score=1234)], db_path=str(overlay_db))

    with get_db_connection(str(canonical_db)) as conn:
        assert (
            conn.execute("SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name = ?", (song_name,)).fetchone()[0] == 0
        )

    with get_db_connection(str(overlay_db)) as conn:
        row = conn.execute(
            "SELECT score FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5'",
            (song_name,),
        ).fetchone()
        assert row is not None
        assert int(row["score"]) == 1234


def test_async_db_saver_mirrors_overlay_db_in_backend_mode(tmp_path, monkeypatch):
    canonical_db = tmp_path / "canonical.db"
    overlay_db = tmp_path / "overlay.db"
    song_meta_path = tmp_path / "song_meta_index.json"
    song_name = "Backend Overlay Song"

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    monkeypatch.setenv("EVOLUTION_OVERLAY_DB_PATH", str(overlay_db))
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.setenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", "1")
    monkeypatch.setenv("POST_TEAM_BUFF_TIERS", "0")
    song_meta_path.write_text("[]", encoding="utf-8")

    init_db()

    saver = AsyncDbSaver()
    try:
        saver.submit(song_name, [_entry(score=2222)], meta={"db_key": song_name, "_processed_run": True})
        saver.flush(timeout=10.0)
    finally:
        saver.shutdown(timeout=10.0)

    with get_db_connection(str(canonical_db)) as conn:
        base_count = conn.execute(
            "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5'",
            (song_name,),
        ).fetchone()[0]
        song_row = conn.execute(
            "SELECT attempt_lifetime, attempts_first, best_score FROM songs WHERE name = ?",
            (song_name,),
        ).fetchone()
        assert int(base_count) == 0
        assert song_row is not None
        assert int(song_row["attempt_lifetime"]) == 1
        assert int(song_row["attempts_first"]) == 1
        assert int(song_row["best_score"]) == 0

    with get_db_connection(str(overlay_db)) as conn:
        overlay_row = conn.execute(
            "SELECT score, details_json FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5'",
            (song_name,),
        ).fetchone()
        overlay_song = conn.execute("SELECT best_score FROM songs WHERE name = ?", (song_name,)).fetchone()
        assert overlay_row is not None
        assert int(overlay_row["score"]) == 2222
        assert overlay_song is not None
        assert int(overlay_song["best_score"]) == 2222
        details = json.loads(str(overlay_row["details_json"] or "{}"))
        assert int(details.get("attempt_lifetime") or 0) == 1
        assert int(details.get("attempts_first") or 0) == 1


def test_async_db_saver_keeps_canonical_db_for_local_runs(tmp_path, monkeypatch):
    canonical_db = tmp_path / "canonical.db"
    overlay_db = tmp_path / "overlay.db"
    song_meta_path = tmp_path / "song_meta_index.json"
    song_name = "Local Canonical Song"

    monkeypatch.setenv("EVOLUTION_DB_PATH", str(canonical_db))
    monkeypatch.setenv("EVOLUTION_OVERLAY_DB_PATH", str(overlay_db))
    monkeypatch.setenv("ROBEATSMETA_SONG_META_INDEX_PATH", str(song_meta_path))
    monkeypatch.delenv("ROBEATSMETA_OPTIMIZER_SERVICE_MODE", raising=False)
    monkeypatch.setenv("POST_TEAM_BUFF_TIERS", "0")
    song_meta_path.write_text("[]", encoding="utf-8")

    init_db()

    saver = AsyncDbSaver()
    try:
        saver.submit(song_name, [_entry(score=3333)], meta={"db_key": song_name, "_processed_run": True})
        saver.flush(timeout=10.0)
    finally:
        saver.shutdown(timeout=10.0)

    with get_db_connection(str(canonical_db)) as conn:
        row = conn.execute(
            "SELECT score FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5'",
            (song_name,),
        ).fetchone()
        assert row is not None
        assert int(row["score"]) == 3333

    with get_db_connection(str(overlay_db)) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5'",
            (song_name,),
        ).fetchone()[0]
        assert int(count) == 0
