import shutil
from pathlib import Path

from gear_optimizer.data.database import init_db, save_loadouts_batch
from gear_optimizer.data.persistence_audit import audit_persistence_db, inject_synthetic_persistence_bug


def _make_valid_db(path: Path, monkeypatch) -> None:
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(path))
    init_db()

    save_loadouts_batch(
        "pytest_persistence_audit_song",
        [
            {
                "score": 100,
                "fg_score": 200,
                "gear": ["G1"],
                "minis": ["M1"],
                "details": {"tag": "base"},
                "force": {"score": 200, "ForceGreats": {"config": {"NonFever1": 1}}},
            }
        ],
    )


def test_audit_reports_clean_for_valid_db(tmp_path, monkeypatch):
    db_path = tmp_path / "valid.db"
    _make_valid_db(db_path, monkeypatch)

    report = audit_persistence_db(db_path, expected_min_songs=1)
    assert report["exists"] is True
    assert report["issues"] == []
    assert report["metrics"]["songs_count"] >= 1


def test_mutation_injection_is_detected(tmp_path, monkeypatch):
    base_db = tmp_path / "base.db"
    _make_valid_db(base_db, monkeypatch)

    mutated_db = tmp_path / "mutated.db"
    shutil.copy2(base_db, mutated_db)

    mutation = inject_synthetic_persistence_bug(mutated_db)
    assert mutation["applied"] is True

    report = audit_persistence_db(mutated_db, expected_min_songs=1)
    assert report["issues"]
    assert any(i["code"] in {"fg_non_improving_rows", "pending_fg_jobs_nonzero", "songs_negative_best_score"} for i in report["issues"])


def test_audit_flags_pending_fg_jobs(tmp_path, monkeypatch):
    db_path = tmp_path / "pending_jobs.db"
    _make_valid_db(db_path, monkeypatch)

    import sqlite3

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO pending_fg_jobs(song_name, candidates_json, created_ts, updated_ts) VALUES(?, ?, ?, ?)",
            ("pytest_pending_fg", "[]", 0, 0),
        )
        conn.commit()
    finally:
        conn.close()

    report = audit_persistence_db(db_path, expected_min_songs=1)
    assert any(i["code"] == "pending_fg_jobs_nonzero" for i in report["issues"])

