import sqlite3

import pytest

import gear_optimizer.data.database as db
import gear_optimizer.helpers.song_helpers.database_context as database_context
from gear_optimizer.helpers.song_helpers.persistence import evaluate_progress_record_update


def _clear_db_tls() -> None:
    try:
        db._DB_TLS.__dict__.clear()
    except Exception:
        pass


def test_get_db_connection_cached_strict_does_not_create_fallback(tmp_path, monkeypatch):
    db_path = tmp_path / "strict.db"
    db_path.write_text("", encoding="utf-8")
    _clear_db_tls()

    def _raise_locked(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "get_db_connection_readonly", _raise_locked)

    with pytest.raises(sqlite3.OperationalError, match="locked"):
        db.get_db_connection_cached(str(db_path), allow_fallback=False)

    assert getattr(db._DB_TLS, "fallback_conn", None) is None


def test_load_database_progress_baseline_marks_invalid_when_strict_read_fails(monkeypatch):
    monkeypatch.setattr(database_context, "load_database_context", lambda *args, **kwargs: (None, {}))

    def _raise_locked(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(database_context, "get_song_counters", _raise_locked)

    result = database_context.load_database_progress_baseline(
        "Song A",
        True,
        {},
        {},
        load_known_loadouts=False,
        allow_fallback=False,
    )

    assert result == (None, {}, 0, 0, 0, 0, False)


def test_evaluate_progress_record_update_suppresses_new_when_baseline_invalid():
    info = evaluate_progress_record_update(
        {"BaseScore": 123456},
        {"score": 120000},
        [{"base_score": 123456, "fg_score": 130000, "data": {"ForceGreats": {"config": {"a": 1}}}}],
        db_best_fg_score=129000,
        baseline_valid=False,
        fg_only=True,
    )

    assert isinstance(info, dict)
    assert info["record_update"] is False
    assert info["baseline_unavailable"] is True
    assert info["is_better"] is False
    assert info["is_fg_better"] is False
    assert info["best_fg_score_run"] == 130000


def test_evaluate_progress_record_update_requires_overall_song_improvement():
    info = evaluate_progress_record_update(
        {"BaseScore": 1000},
        {"score": 1000},
        [{"base_score": 900, "fg_score": 950, "data": {"ForceGreats": {"config": {"a": 1}}}}],
        db_best_fg_score=900,
        baseline_valid=True,
        fg_only=True,
    )

    assert isinstance(info, dict)
    assert info["is_fg_better"] is True
    assert info["is_overall_better"] is False
    assert info["record_update"] is False
    assert info["prev_overall_score"] == 1000
    assert info["best_overall_score_run"] == 1000


def test_evaluate_progress_record_update_counts_fg_when_it_beats_overall_song_best():
    info = evaluate_progress_record_update(
        {"BaseScore": 1000},
        {"score": 1000},
        [{"base_score": 900, "fg_score": 1050, "data": {"ForceGreats": {"config": {"a": 1}}}}],
        db_best_fg_score=900,
        baseline_valid=True,
        fg_only=True,
    )

    assert isinstance(info, dict)
    assert info["is_fg_better"] is True
    assert info["is_overall_better"] is True
    assert info["record_update"] is True
    assert info["prev_overall_score"] == 1000
    assert info["best_overall_score_run"] == 1050
