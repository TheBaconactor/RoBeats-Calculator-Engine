import threading

import pytest

from gear_optimizer.app_async_db import AsyncDbSaver
from gear_optimizer.store import db, schema
from tests.store_support import candidate

STATS = {
    "Perfect Points": 25, "Combo Multiplier": 0, "Fever Multiplier": 0, "Fever Fill Rate": 0, "Fever Time": 0,
    "Chill": 0, "Flow": 0, "Rush": 130, "Beat": 0, "Vibe": 0,
}


def _entry(*, score: int) -> dict:
    """A GA result for items the catalog does not know (its stats are stored as given)."""
    return {
        "score": score,
        "fg_score": 0,
        "gear": ["G1", "G2"],
        "minis": ["M1"],
        "details": {
            "PrimaryColor": "Rush", "SecondaryColor": "Flow", "SelectedElement": "Rush", "FT": 0, "FF": 0,
            "GemCounts": {"Perfect Points": 0, "Combo Multiplier": 0, "Fever Multiplier": 0, "Element": 0},
            "Stats": dict(STATS),
        },
        "force": None,
    }


def _songs(path) -> list[str]:
    conn = schema.connect(path)
    try:
        return db.song_names(conn)
    finally:
        conn.close()


def test_async_saver_reuses_one_writer_connection_per_database(tmp_path, monkeypatch):
    first, second = tmp_path / "first.db", tmp_path / "second.db"
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(first))
    opened: list[str] = []
    real_connect = schema.connect

    def counted(path, *, write=False, timeout=30.0):
        opened.append(str(path))
        return real_connect(path, write=write, timeout=timeout)

    monkeypatch.setattr("gear_optimizer.app_async_db.schema.connect", counted)
    saver = AsyncDbSaver()
    try:
        saver.submit("Song A", [_entry(score=100)], meta={"_processed_run": True})
        saver.submit("Song B", [_entry(score=200)], meta={"_processed_run": True})
        saver.flush(timeout=10.0)
        monkeypatch.setenv("EVOLUTION_DB_PATH", str(second))
        saver.submit("Song C", [_entry(score=300)], meta={"_processed_run": True})
        saver.flush(timeout=10.0)
    finally:
        saver.shutdown(timeout=10.0)
    assert [p.rsplit("/", 1)[-1] for p in opened] == ["first.db", "second.db"]
    assert _songs(first) == ["Song A", "Song B"] and _songs(second) == ["Song C"]


def test_a_processed_run_without_results_marks_the_song(tmp_path, monkeypatch):
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "results.db"))
    saver = AsyncDbSaver()
    try:
        saver.submit("Empty Song", [], meta={"_processed_run": True})
        saver.submit("Ignored Song", [], meta={"_processed_run": False})
        saver.flush(timeout=10.0)
    finally:
        saver.shutdown(timeout=10.0)
    assert _songs(tmp_path / "results.db") == ["Empty Song"]


def test_a_failed_store_leaves_the_database_unchanged(tmp_path, monkeypatch):
    path = tmp_path / "atomic.db"
    conn = schema.connect(path, write=True)

    def fail(*_args, **_kwargs):
        raise RuntimeError("injected insert failure")

    monkeypatch.setattr(db, "insert_rows", fail)

    with pytest.raises(RuntimeError, match="injected insert failure"):
        db.store_results(conn, "Song A", "T5", [candidate("a", 100)])
    assert not conn.in_transaction
    assert conn.execute("SELECT COUNT(*) FROM songs").fetchone()[0] == 0
    conn.close()


@pytest.mark.parametrize("field", ["score", "fg_score", "fg_base_score"])
def test_malformed_score_fields_are_rejected_by_name(tmp_path, field):
    from gear_optimizer.store.legacy import store_entries

    entry = _entry(score=100)
    entry[field] = "not-an-integer"
    conn = schema.connect(tmp_path / "malformed.db", write=True)
    with pytest.raises(ValueError, match=field):
        store_entries(conn, "Malformed Song", "T5", [entry], gears={}, minis={})
    conn.close()


def test_shutdown_timeout_never_restarts_live_writer(tmp_path, monkeypatch):
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "shutdown.db"))
    entered = threading.Event()
    release = threading.Event()

    def _blocked_save(*_args, **_kwargs):
        entered.set()
        assert release.wait(timeout=30.0)

    monkeypatch.setattr("gear_optimizer.app_async_db.store_entries", _blocked_save)
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
