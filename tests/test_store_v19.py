"""A version 19 results database (one timing mode per file, no mode column) migrates to version 20 as Precise rows."""

from __future__ import annotations

import sqlite3

from gear_optimizer.core.timing_modes import NON_PRECISE, PRECISE
from gear_optimizer.store import db, schema, tables
from tests.store_support import fg_row, meta_row, result

# Version 19 as engine 8e0d89f9 created it (store.tables before the timing mode joined the keys).
V19_DDL = """
CREATE TABLE songs (name TEXT PRIMARY KEY, last_updated REAL NOT NULL) STRICT;
CREATE TABLE loadouts (
    song_name TEXT NOT NULL REFERENCES songs (name), team_buff TEXT NOT NULL, loadout_hash TEXT NOT NULL,
    gear TEXT NOT NULL, minis TEXT NOT NULL, primary_color TEXT NOT NULL, secondary_color TEXT NOT NULL,
    mini_ascension TEXT, score INTEGER NOT NULL, fg_score INTEGER, meta_board INTEGER NOT NULL,
    fg_board INTEGER NOT NULL, meta_updated INTEGER, meta_seq INTEGER, meta_result TEXT, fg_updated INTEGER,
    fg_seq INTEGER, fg_result TEXT, meta_trace BLOB, fg_trace BLOB,
    PRIMARY KEY (song_name, team_buff, loadout_hash)
) STRICT;
CREATE INDEX loadouts_meta_board ON loadouts (song_name, team_buff, score DESC, fg_score DESC, meta_updated DESC, meta_seq)
    WHERE meta_board = 1;
CREATE INDEX loadouts_fg_board ON loadouts (song_name, team_buff, fg_score DESC, score DESC, fg_updated DESC, fg_seq)
    WHERE fg_board = 1;
CREATE INDEX loadouts_meta_seq ON loadouts (meta_seq);
CREATE INDEX loadouts_fg_seq ON loadouts (fg_seq);
PRAGMA user_version = 19;
"""


def _v19_database(path, rows) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(V19_DDL)
    conn.execute("INSERT INTO songs VALUES ('Song A', 1700000000.5)")
    conn.executemany(
        f"INSERT INTO loadouts VALUES ({', '.join(['?'] * 20)})",
        (tables._values(row)[1:] for row in rows),  # every version 20 column but the leading timing mode
    )
    conn.commit()
    conn.close()


def test_a_version_19_database_becomes_precise_rows(tmp_path):
    path = tmp_path / "v19.db"
    rows = [meta_row("a", 120, seq=1), fg_row("b", 100, 150, seq=2), fg_row("c", 90, 140, meta=False, seq=3)]
    _v19_database(path, rows)

    schema.connect(path, write=True).close()

    reader = schema.connect(path)
    try:
        assert tables.user_version(reader) == tables.VERSION
        stored = {r.loadout.loadout_hash: r for r in db.load_rows(reader, PRECISE, "Song A", "T5")}
        assert stored == {r.loadout.loadout_hash: r for r in rows}  # loadouts, entry numbers and traces, byte for byte
        assert db.last_updated(reader, PRECISE) == {"Song A": 1700000000.5}
        assert db.load_rows(reader, NON_PRECISE, "Song A", "T5") == []
        assert db.present_songs(reader, NON_PRECISE, ["Song A"]) == set()
    finally:
        reader.close()


def test_a_migrated_database_takes_the_other_mode_beside_it(tmp_path):
    path = tmp_path / "v19.db"
    _v19_database(path, [meta_row("a", 120, seq=1)])
    conn = schema.connect(path, write=True)
    try:
        db.store_results(conn, NON_PRECISE, "Song A", "T5", [result("a", 300, mode=NON_PRECISE)], now=5)
        assert [x.score for x in db.load_boards(conn, PRECISE, "Song A", "T5").meta] == [120]
        (x,) = db.load_boards(conn, NON_PRECISE, "Song A", "T5").meta
        assert (x.score, x.meta.seq) == (300, 2)  # the database's entry numbers go on across modes
    finally:
        conn.close()


def test_a_version_19_database_from_before_the_entry_number_indexes_migrates_with_every_index(tmp_path):
    path = tmp_path / "v19.db"
    _v19_database(path, [meta_row("a", 120, seq=1)])
    conn = sqlite3.connect(path)
    conn.execute("DROP INDEX loadouts_meta_seq")
    conn.execute("DROP INDEX loadouts_fg_seq")
    conn.close()

    schema.connect(path, write=True).close()

    conn = sqlite3.connect(path)
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
    conn.close()
    assert {"loadouts_meta_board", "loadouts_fg_board", "loadouts_meta_seq", "loadouts_fg_seq"} <= names
