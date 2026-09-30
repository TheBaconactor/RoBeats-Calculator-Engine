import sqlite3

import pytest

from gear_optimizer.store import db, schema
from gear_optimizer.store.boards import boards
from tests.store_support import fg_row, meta_row, result


@pytest.fixture
def conn(tmp_path):
    connection = schema.connect(tmp_path / "results.db", write=True)
    yield connection
    connection.close()


def test_a_writer_creates_the_current_schema_and_a_reader_requires_it(tmp_path):
    path = tmp_path / "results.db"
    schema.connect(path, write=True).close()
    reader = schema.connect(path)
    assert schema.user_version(reader) == schema.VERSION
    reader.close()
    other = tmp_path / "other.db"
    sqlite3.connect(other).execute("PRAGMA user_version = 7").connection.close()
    with pytest.raises(schema.StoreVersionError):
        schema.connect(other)
    with pytest.raises(schema.StoreVersionError):
        schema.connect(other, write=True)


def test_stored_results_read_back_in_board_order_with_their_traces(conn):
    db.store_results(
        conn, "Song A", "T5", [result("a", 100, 150), result("b", 120), result("c", 100)], now=1000.5
    )
    got = db.load_boards(conn, "Song A", "T5")
    assert [x.loadout_hash for x in got.meta] == ["b", "a", "c"]
    assert [x.loadout_hash for x in got.fg] == ["a"]
    rows = db.load_rows(conn, "Song A", "T5")
    assert (got.meta, got.fg) == boards(rows)
    traces = db.load_traces(conn, "Song A", "T5", ["a", "b"])
    assert traces["a"].meta == {"frontier_trace": [{"hash": "a"}]}
    assert traces["a"].fg == {"frontier_trace": [{"fg": "a"}]}
    assert traces["b"].fg is None
    assert db.last_updated(conn) == {"Song A": 1000.5}
    assert db.board_sizes(conn) == {("Song A", "T5"): (3, 1)}


def test_catalog_streams_walk_songs_by_name_in_board_order(conn):
    db.store_results(conn, "B song", "T5", [result("x", 5, song="B song")], now=1)
    db.store_results(
        conn, "A song", "T5", [result("y", 7, song="A song"), result("z", 9, 12, song="A song")], now=2
    )
    assert [(x.song, x.loadout_hash) for x in db.iter_board(conn, "meta", tier="T5")] == [
        ("A song", "z"),
        ("A song", "y"),
        ("B song", "x"),
    ]
    assert [x.loadout_hash for x in db.iter_board(conn, "fg", tier="T5", songs=["A song"])] == ["z"]
    assert db.song_names(conn) == ["B song", "A song"]


def test_sql_board_order_matches_the_python_order_on_ties(conn):
    rows = [
        meta_row("no-fg", 100, updated=9, seq=1),
        meta_row("fg", 100, fg_score=100, updated=1, seq=2),
        meta_row("newer", 100, updated=10, seq=3),
        meta_row("later-entry", 100, updated=10, seq=4),
        fg_row("f1", 90, 200, updated=5, seq=6),
        fg_row("f2", 95, 200, updated=5, seq=5),
    ]
    conn.execute("INSERT INTO songs VALUES ('Song A', 1)")
    db.insert_rows(conn, rows)
    conn.commit()
    got = db.load_boards(conn, "Song A", "T5")
    assert (got.meta, got.fg) == boards(rows)
    assert [x.loadout_hash for x in got.fg] == ["f2", "f1"]


def test_a_song_digest_changes_exactly_when_its_rows_change(conn):
    db.store_results(conn, "Song A", "T5", [result("a", 100)], now=10)
    db.store_results(conn, "Song B", "T5", [result("b", 100, song="Song B")], now=10)
    first = db.song_digest(conn, "Song A")
    db.store_results(conn, "Song B", "T5", [result("c", 200, song="Song B")], now=11)
    assert db.song_digest(conn, "Song A") == first
    db.store_results(conn, "Song A", "T5", [result("a", 90)], now=12)
    assert db.song_digest(conn, "Song A") != first


def test_a_processed_run_without_results_only_marks_the_song(conn):
    db.store_results(conn, "Song A", "T5", [], now=42.0)
    assert db.song_names(conn) == ["Song A"] and db.board_sizes(conn) == {}


def test_results_of_another_song_are_refused(conn):
    with pytest.raises(ValueError, match="cannot be stored"):
        db.store_results(conn, "Song B", "T5", [result("a", 1)], now=1)
    assert db.song_names(conn) == []


def test_entry_numbers_count_across_songs_like_insertion_order(conn):
    db.store_results(conn, "Song A", "T5", [result("a1", 10, 20, song="Song A"), result("a2", 5, song="Song A")], now=1)
    db.store_results(conn, "Song B", "T5", [result("b1", 7, 9, song="Song B")], now=2)
    db.store_results(conn, "Song A", "T5", [result("a3", 1, song="Song A")], now=3)
    seqs = {x.loadout_hash: x.meta.seq for song in ("Song A", "Song B") for x in db.load_boards(conn, song, "T5").meta}
    assert seqs == {"a1": 1, "a2": 2, "b1": 3, "a3": 4}
    assert [x.fg.seq for x in db.load_boards(conn, "Song B", "T5").fg] == [2]
