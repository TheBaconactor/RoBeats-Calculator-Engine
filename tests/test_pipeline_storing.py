from types import SimpleNamespace

from gear_optimizer.core.timing_modes import PRECISE
from gear_optimizer.pipeline import storing
from gear_optimizer.store import db, schema
from tests.store_support import result


def _solve(song="Song A"):
    """Stands in for a SongSolve (the canonicalization is replaced)."""
    return SimpleNamespace(song=song, tier="T5", timed=SimpleNamespace(mode=PRECISE))


def test_a_solve_is_stored_the_bests_printed_and_the_boards_best_before_and_after_returned(tmp_path, monkeypatch,
                                                                                        capsys):
    rows = {"Song A": [result("a", 100, 150), result("b", 120)]}
    monkeypatch.setattr(storing, "canonical_rows", lambda solve, gears, minis: rows[solve.song])
    conn = schema.connect(tmp_path / "results.db", write=True)
    assert storing.store_solve(conn, _solve(), {}, {}) == (0, 150)
    boards = db.load_boards(conn, PRECISE, "Song A", "T5")
    assert [x.loadout_hash for x in boards.meta] == ["b", "a"] and [x.loadout_hash for x in boards.fg] == ["a"]
    out = capsys.readouterr().out
    assert "FINAL CONFIGURATION FOR: Song A" in out
    assert "Best Base Score Found: 120" in out and "Best FG Score Found: 150" in out
    assert "NEW RECORD! Previous: 0 | New: 150" in out

    rows["Song A"] = [result("c", 110)]
    assert storing.store_solve(conn, _solve(), {}, {}) == (150, 150)
    assert "No improvement over the stored record (150)" in capsys.readouterr().out
    conn.close()
