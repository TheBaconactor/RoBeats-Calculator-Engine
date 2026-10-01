import sqlite3

import gear_optimizer.helpers.song_helpers.database_context as database_context
from gear_optimizer.helpers.song_helpers.database_context import SongDbBaseline
from gear_optimizer.pipeline.progress import run_record_info
from gear_optimizer.store import db, schema
from tests.store_support import result


def test_the_baseline_is_invalid_when_the_database_cannot_be_read(monkeypatch):
    def _raise_locked(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(database_context.schema, "connect", _raise_locked)
    assert database_context.load_song_db_baseline("Song A") == SongDbBaseline("Song A", 0, 0, False)


def test_the_baseline_is_the_songs_stored_best_meta_and_fg_scores(tmp_path, monkeypatch):
    path = tmp_path / "results.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(path))
    conn = schema.connect(path, write=True)
    db.store_results(conn, "Song A", "T5", [result("a", 100, 150), result("b", 120), result("c", 90, 160)])
    conn.close()
    assert database_context.load_song_db_baseline(" Song A ") == SongDbBaseline("Song A", 120, 160, True)
    assert database_context.load_song_db_baseline("Song B") == SongDbBaseline("Song B", 0, 0, True)


def test_no_record_is_reported_without_a_readable_baseline():
    info = run_record_info(123456, 130000, 120000, 129000, baseline_valid=False)
    assert (info["record_update"], info["is_better"], info["is_fg_better"]) == (False, False, False)
    assert (info["score"], info["best_fg_score_run"]) == (123456, 130000)


def test_a_record_needs_the_songs_overall_best_to_improve():
    info = run_record_info(1000, 950, 1000, 900, baseline_valid=True)
    assert (info["is_fg_better"], info["record_update"], info["prev_overall_score"]) == (True, False, 1000)
    info = run_record_info(1000, 1100, 1000, 900, baseline_valid=True)
    assert (info["record_update"], info["best_overall_score_run"]) == (True, 1100)


def test_improvements_within_two_points_are_scoring_noise():
    assert run_record_info(1002, 0, 1000, 0, baseline_valid=True)["record_update"] is False
    assert run_record_info(0, 1002, 0, 1000, baseline_valid=True)["is_fg_better"] is False
    info = run_record_info(1003, 0, 1000, 0, baseline_valid=True)
    assert (info["record_update"], info["is_better"]) == (True, True)
