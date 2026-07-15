import json
import os
import sqlite3
import threading

import pytest

from gear_optimizer.app_async_db import AsyncDbSaver
from gear_optimizer.data import database as db
from gear_optimizer.data.database import persistence


def _entry(*, score: int, fg_score: int = 0, force: dict | None = None) -> dict:
    return {
        "score": score,
        "fg_score": fg_score,
        "gear": ["G1", "G2"],
        "minis": ["M1"],
        "details": {"test": "base" if force is None else "fg_variant"},
        "force": force,
    }


def _force_payload(fg_score: int, *, base_score: int) -> dict:
    return {
        "Score": fg_score,
        "BaseScore": base_score,
        "FT": 0,
        "FF": 0,
        "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
        "BaseStats": {
            "Perfect Points": 25,
            "Combo Multiplier": 0,
            "Fever Multiplier": 0,
            "Fever Fill Rate": 0,
            "Fever Time": 0,
            "Chill": 0,
            "Flow": 0,
            "Rush": 100,
            "Beat": 0,
            "Vibe": 0,
        },
        "Selected Element": "Rush",
        "ForceGreats": {"config": {"NonFever1": 1}, "final_score": fg_score},
    }


def test_async_saver_reuses_one_writer_connection_for_multiple_saves(tmp_path, monkeypatch):
    db_path = tmp_path / "persistent.db"
    second_db_path = tmp_path / "second.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(db_path))
    real_get_connection = db.get_db_connection
    opened_paths: list[str] = []

    def _counted_get_connection(path):
        opened_paths.append(str(path))
        return real_get_connection(path)

    monkeypatch.setattr("gear_optimizer.app_async_db.get_db_connection", _counted_get_connection)
    saver = AsyncDbSaver()
    try:
        saver.submit("Song A", [_entry(score=100)], meta={"_processed_run": True})
        saver.submit("Song B", [_entry(score=200)], meta={"_processed_run": True})
        saver.flush(timeout=10.0)
        monkeypatch.setenv("EVOLUTION_DB_PATH", str(second_db_path))
        saver.submit("Song C", [_entry(score=300)], meta={"_processed_run": True})
        saver.flush(timeout=10.0)
    finally:
        saver.shutdown(timeout=10.0)

    assert opened_paths == [
        os.path.normcase(os.path.realpath(os.path.abspath(str(db_path)))),
        os.path.normcase(os.path.realpath(os.path.abspath(str(second_db_path)))),
    ]
    with real_get_connection(str(db_path)) as conn:
        rows = conn.execute("SELECT name, attempt_lifetime FROM songs ORDER BY name").fetchall()
    assert [(row["name"], row["attempt_lifetime"]) for row in rows] == [("Song A", 1), ("Song B", 1)]
    with real_get_connection(str(second_db_path)) as conn:
        row = conn.execute("SELECT name, attempt_lifetime FROM songs").fetchone()
    assert (row["name"], row["attempt_lifetime"]) == ("Song C", 1)


def test_optimizer_result_rollback_removes_loadouts_and_counters(tmp_path, monkeypatch):
    db_path = tmp_path / "atomic.db"
    conn = db.get_db_connection(str(db_path))
    db.configure_persistent_writer_connection(conn)

    def _fail_counter_update(*_args, **_kwargs):
        raise RuntimeError("injected counter failure")

    monkeypatch.setattr(persistence, "_update_song_counters_in_transaction", _fail_counter_update)
    with pytest.raises(RuntimeError, match="injected counter failure"):
        db.save_optimizer_song_result(
            "Atomic Song",
            [_entry(score=100)],
            processed_run=True,
            conn=conn,
            db_path=str(db_path),
        )

    assert not conn.in_transaction
    assert conn.execute("SELECT COUNT(*) FROM team_buff_loadouts").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0] == 0
    conn.close()


@pytest.mark.parametrize("field", ["score", "fg_score", "fg_base_score"])
def test_optimizer_result_rejects_malformed_internal_score_fields(field):
    entry = _entry(score=100)
    entry[field] = "not-an-integer"
    with pytest.raises(ValueError, match=field):
        db.save_optimizer_song_result("Malformed Song", [entry], processed_run=True)


def test_optimizer_result_rejects_connection_path_mismatch_and_derives_when_omitted(tmp_path):
    db_path = tmp_path / "connection.db"
    other_path = tmp_path / "other.db"
    conn = db.get_db_connection(str(db_path))
    db.configure_persistent_writer_connection(conn)

    with pytest.raises(ValueError, match="does not match"):
        db.save_optimizer_song_result(
            "Wrong Path",
            [_entry(score=100)],
            processed_run=True,
            conn=conn,
            db_path=str(other_path),
        )
    db.save_optimizer_song_result(
        "Derived Path",
        [_entry(score=100)],
        processed_run=True,
        conn=conn,
    )

    assert conn.execute("SELECT COUNT(*) FROM songs WHERE name = 'Wrong Path'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM songs WHERE name = 'Derived Path'").fetchone()[0] == 1
    conn.close()


def test_write_transaction_retries_lock_before_committing(monkeypatch):
    class _LockOnceConnection:
        def __init__(self):
            self.begin_calls = 0
            self.rollback_calls = 0
            self.commit_calls = 0

        def execute(self, sql):
            assert sql == "BEGIN IMMEDIATE"
            self.begin_calls += 1
            if self.begin_calls == 1:
                raise sqlite3.OperationalError("database is locked")

        def rollback(self):
            self.rollback_calls += 1

        def commit(self):
            self.commit_calls += 1

    conn = _LockOnceConnection()
    operation_calls = 0

    def _operation():
        nonlocal operation_calls
        operation_calls += 1

    monkeypatch.setattr(persistence.time, "sleep", lambda _seconds: None)
    persistence._run_write_transaction(conn, _operation)

    assert conn.begin_calls == 2
    assert conn.rollback_calls == 1
    assert conn.commit_calls == 1
    assert operation_calls == 1


def test_update_song_counters_propagates_sqlite_errors(tmp_path):
    conn = db.get_db_connection(str(tmp_path / "closed.db"))
    conn.close()
    with pytest.raises(sqlite3.Error):
        db.update_song_counters(
            "Required Counter",
            processed_run=True,
            record_improved=True,
            conn=conn,
        )


def test_optimizer_result_preserves_meta_only_and_full_base_fg_semantics(tmp_path):
    db_path = tmp_path / "semantics.db"
    conn = db.get_db_connection(str(db_path))
    db.configure_persistent_writer_connection(conn)

    db.save_optimizer_song_result(
        "Meta Only",
        [],
        processed_run=True,
        conn=conn,
        db_path=str(db_path),
    )
    assert db.get_song_counters("Meta Only", conn=conn) == (1, 1, 0, 0)

    base_entry = _entry(score=100)
    db.save_optimizer_song_result(
        "Full Result Song",
        [base_entry],
        processed_run=True,
        conn=conn,
        db_path=str(db_path),
    )
    assert base_entry["details"]["attempt_lifetime"] == 1
    assert base_entry["details"]["attempts_first"] == 1

    second_entry = _entry(score=100)
    db.save_optimizer_song_result(
        "Full Result Song",
        [second_entry],
        processed_run=True,
        conn=conn,
        db_path=str(db_path),
    )
    assert second_entry["details"]["attempt_lifetime"] == 2
    assert second_entry["details"]["attempts_first"] == 2

    fg_entry = _entry(
        score=100,
        fg_score=150,
        force=_force_payload(150, base_score=100),
    )
    db.save_optimizer_song_result(
        "Full Result Song",
        [fg_entry],
        processed_run=True,
        conn=conn,
        db_path=str(db_path),
    )
    assert db.get_song_counters("Full Result Song", conn=conn) == (3, 1, 100, 150)

    base_row = conn.execute(
        "SELECT score, details_json FROM team_buff_loadouts WHERE song_name = ? AND team_buff = 'T5'",
        ("Full Result Song",),
    ).fetchone()
    fg_row = conn.execute(
        "SELECT score, fg_score FROM team_buff_fg_loadouts WHERE song_name = ? AND team_buff = 'T5'",
        ("Full Result Song",),
    ).fetchone()
    assert base_row["score"] == 100
    assert json.loads(base_row["details_json"])["test"] == "base"
    assert (fg_row["score"], fg_row["fg_score"]) == (100, 150)
    conn.close()


def test_record_improvement_uses_persisted_fg_pairing_not_entry_score(tmp_path):
    db_path = tmp_path / "fg_pairing.db"
    conn = db.get_db_connection(str(db_path))
    db.configure_persistent_writer_connection(conn)

    db.save_optimizer_song_result(
        "FG Pairing",
        [_entry(score=100)],
        processed_run=True,
        conn=conn,
        db_path=str(db_path),
    )
    db.save_optimizer_song_result(
        "FG Pairing",
        [_entry(score=100)],
        processed_run=True,
        conn=conn,
        db_path=str(db_path),
    )
    assert db.get_song_counters("FG Pairing", conn=conn) == (2, 2, 100, 0)

    fg_entry = _entry(
        score=100,
        fg_score=95,
        force=_force_payload(95, base_score=90),
    )
    fg_entry["fg_base_score"] = 90
    db.save_optimizer_song_result(
        "FG Pairing",
        [fg_entry],
        processed_run=True,
        conn=conn,
        db_path=str(db_path),
    )

    assert db.get_song_counters("FG Pairing", conn=conn) == (3, 1, 100, 95)
    conn.close()


def test_shutdown_timeout_never_restarts_live_writer(tmp_path, monkeypatch):
    monkeypatch.setenv("GPU_STRICT", "1")
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "shutdown.db"))
    entered = threading.Event()
    release = threading.Event()

    def _blocked_save(*_args, **_kwargs):
        entered.set()
        assert release.wait(timeout=30.0)

    monkeypatch.setattr("gear_optimizer.app_async_db.save_optimizer_song_result", _blocked_save)
    saver = AsyncDbSaver()
    saver.submit("Blocked Song", [_entry(score=100)], meta={"_processed_run": True})
    assert entered.wait(timeout=5.0)
    writer_thread = saver._thread

    try:
        with pytest.raises(RuntimeError, match="timed out"):
            saver.shutdown(timeout=0.01)
        assert writer_thread is not None and writer_thread.is_alive()
        with pytest.raises(RuntimeError, match="not accepting"):
            saver.submit("Second Song", [_entry(score=200)], meta={"_processed_run": True})
        with pytest.raises(RuntimeError, match="cannot start"):
            saver.start()
    finally:
        release.set()
        assert saver._terminated_event.wait(timeout=5.0)

    assert not writer_thread.is_alive()
    assert saver._writer_connection is None
    with pytest.raises(RuntimeError, match="cannot start"):
        saver.start()
