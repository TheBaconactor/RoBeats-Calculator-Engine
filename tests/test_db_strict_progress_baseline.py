import sqlite3

import gear_optimizer.helpers.song_helpers.database_context as database_context
from gear_optimizer.helpers.song_helpers.persistence_records import evaluate_progress_record_update
from gear_optimizer.store import db, schema
from tests.store_support import candidate


def test_load_database_progress_baseline_marks_invalid_when_the_read_fails(monkeypatch):
    def _raise_locked(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(database_context.schema, "connect", _raise_locked)
    assert database_context.load_database_progress_baseline("Song A") == (None, 0, 0, False)


def test_load_database_progress_baseline_reads_the_top_meta_entry_and_best_scores(tmp_path, monkeypatch):
    path = tmp_path / "results.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(path))
    conn = schema.connect(path, write=True)
    db.store_results(conn, "Song A", "T5", [candidate("a", 100, 150), candidate("b", 120), candidate("c", 90, 160)])
    conn.close()
    prev_record, best, best_fg, valid = database_context.load_database_progress_baseline("Song A")
    assert (prev_record["loadout_hash"], best, best_fg, valid) == ("b", 120, 160, True)
    assert database_context.load_database_progress_baseline("Song B") == (None, 0, 0, True)


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


def test_evaluate_progress_record_update_ignores_two_point_base_drift():
    info = evaluate_progress_record_update(
        {"BaseScore": 1002},
        {"score": 1000},
        [],
        db_best_fg_score=0,
        baseline_valid=True,
    )

    assert isinstance(info, dict)
    assert info["is_better"] is False
    assert info["is_overall_better"] is False
    assert info["record_update"] is False


def test_evaluate_progress_record_update_ignores_two_point_fg_drift():
    info = evaluate_progress_record_update(
        {"BaseScore": 1000},
        {"score": 1000},
        [{"base_score": 1000, "fg_score": 1002, "data": {"ForceGreats": {"config": {"a": 1}}}}],
        db_best_fg_score=1000,
        baseline_valid=True,
        fg_only=True,
    )

    assert isinstance(info, dict)
    assert info["is_fg_better"] is False
    assert info["is_overall_better"] is False
    assert info["record_update"] is False


def test_evaluate_progress_record_update_counts_three_point_improvement():
    info = evaluate_progress_record_update(
        {"BaseScore": 1003},
        {"score": 1000},
        [],
        db_best_fg_score=0,
        baseline_valid=True,
    )

    assert isinstance(info, dict)
    assert info["is_better"] is True
    assert info["is_overall_better"] is True
    assert info["record_update"] is True
