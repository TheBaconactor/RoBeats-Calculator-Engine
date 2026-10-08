import queue
from types import SimpleNamespace

import pytest

from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.pipeline import post_processor
from gear_optimizer.store import db, schema
from tests.store_support import result


class _Solve:
    """Stands in for a SongSolve (the canonicalization is replaced)."""

    def __init__(self, song="Song A"):
        self.song, self.tier, self.timed = song, "T5", SimpleNamespace(mode=PRECISE)


def _patch(monkeypatch, rows_by_song):
    monkeypatch.setattr(post_processor, "SongSolve", _Solve)
    monkeypatch.setattr(post_processor, "canonical_rows", lambda solve, gears, minis: rows_by_song[solve.song])


def test_a_solve_is_stored_and_the_stored_bests_are_printed(tmp_path, monkeypatch, capsys):
    _patch(monkeypatch, {"Song A": [result("a", 100, 150), result("b", 120)]})
    conn = schema.connect(tmp_path / "results.db", write=True)
    post_processor.store_solve(conn, _Solve(), {}, {})
    boards = db.load_boards(conn, PRECISE, "Song A", "T5")
    assert [x.loadout_hash for x in boards.meta] == ["b", "a"] and [x.loadout_hash for x in boards.fg] == ["a"]
    out = capsys.readouterr().out
    assert "FINAL CONFIGURATION FOR: Song A" in out
    assert "Best Base Score Found: 120" in out and "Best FG Score Found: 150" in out
    assert "NEW RECORD! Previous: 0 | New: 150" in out

    _patch(monkeypatch, {"Song A": [result("c", 110)]})
    post_processor.store_solve(conn, _Solve(), {}, {})
    assert "No improvement over the stored record (150)" in capsys.readouterr().out
    conn.close()


def test_the_loop_stores_solves_counts_failures_and_stops_at_the_sentinel(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EVOLUTION_DB_PATH", str(tmp_path / "results.db"))
    monkeypatch.setenv("METAFINDER_OUTPUT", "1")
    monkeypatch.setattr("gear_optimizer.core.logging_config.configure_default_logging", lambda: None)
    _patch(monkeypatch, {"Song A": [result("a", 100, song="Song A")], "Broken": None})
    items = queue.Queue()
    for item in ({"_error": "boom", "_song_name": "Song X"}, _Solve("Song A"), _Solve("Broken"), None):
        items.put(item)
    with pytest.raises(SystemExit) as exited:
        post_processor.run_post_processor(items, total_tasks=3)
    assert exited.value.code == 1
    conn = schema.connect(tmp_path / "results.db")
    assert [x.loadout_hash for x in db.load_boards(conn, PRECISE, "Song A", "T5").meta] == ["a"]
    conn.close()
    captured = capsys.readouterr()
    assert "[POST] FAILED: Song X - Error: boom" in captured.err
    assert "[POST] FAILED: Broken - TypeError" in captured.err
    assert "[POST][SUMMARY] 2/3 task(s) failed." in captured.out
