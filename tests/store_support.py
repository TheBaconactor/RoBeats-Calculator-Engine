"""Store records for tests, and a version 18 database writer for the migration tests."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable

from gear_optimizer.gamedata import MINI_ASCENSION_VERSION
from gear_optimizer.store.boards import Row
from gear_optimizer.store.records import FgResult, Loadout, MetaResult, encode_trace

STATS10 = (85, 71, 69, 76, 18, 0, 716, 30, 78, 167)
SURFACE = (0, 0, 0, 0, 0, 0, 0, 0, 1702, 2, 2)


def meta_result(*, updated: int = 100, seq: int = 1, element: str = "Flow", gems=(0, 10, 10, 6, 1, 63)) -> MetaResult:
    return MetaResult(element=element, gems=tuple(gems), stats=STATS10, updated=updated, seq=seq)


def fg_result(*, updated: int = 100, seq: int = 1, element: str = "Flow", gems=(0, 10, 10, 6, 1, 63)) -> FgResult:
    return FgResult(element=element, gems=tuple(gems), stats=STATS10, surface=SURFACE, updated=updated, seq=seq)


def loadout(
    loadout_hash: str,
    *,
    score: int,
    fg_score: int | None = None,
    meta: MetaResult | None = None,
    fg: FgResult | None = None,
    song: str = "Song A",
    tier: str = "T5",
    ascension: str | None = MINI_ASCENSION_VERSION,
) -> Loadout:
    """A stored loadout on the boards of its results (merges rank the boards again)."""
    return Loadout(
        song=song,
        tier=tier,
        loadout_hash=loadout_hash,
        gear=(f"{loadout_hash} gear",),
        minis=((f"{loadout_hash} mini", f"{loadout_hash} twin"),),
        primary="Flow",
        secondary="Vibe",
        mini_ascension=ascension,
        score=score,
        fg_score=fg_score,
        meta=meta,
        fg=fg,
        on_meta=meta is not None,
        on_fg=fg is not None and fg_score > score,
    )


def row(value: Loadout) -> Row:
    meta_trace = encode_trace({"frontier_trace": [{"hash": value.loadout_hash}]}) if value.meta else None
    fg_trace = encode_trace({"frontier_trace": [{"fg": value.loadout_hash}]}) if value.fg else None
    return Row(value, meta_trace, fg_trace)


def meta_row(loadout_hash: str, score: int, *, fg_score: int | None = None, updated: int = 100, seq: int = 1) -> Row:
    return row(loadout(loadout_hash, score=score, fg_score=fg_score, meta=meta_result(updated=updated, seq=seq)))


def fg_row(loadout_hash: str, score: int, fg_score: int, *, meta: bool = True, updated: int = 100, seq: int = 1) -> Row:
    return row(
        loadout(
            loadout_hash,
            score=score,
            fg_score=fg_score,
            meta=meta_result(updated=updated, seq=seq) if meta else None,
            fg=fg_result(updated=updated, seq=seq),
        )
    )


def result(loadout_hash: str, score: int, fg_score: int | None = None, *, meta: bool = True, song: str = "Song A") -> Row:
    """A solve's result row: a meta result (unless meta=False) and an FG result when fg_score is given."""
    value = loadout(
        loadout_hash,
        song=song,
        score=score,
        fg_score=fg_score,
        meta=meta_result(updated=0, seq=0) if meta else None,
        fg=fg_result(updated=0, seq=0) if fg_score is not None else None,
    )
    return row(value)


# Version 18, as engine 52f84d17..f9abea47 created it (data/migrations LATEST_SCHEMA_VERSION = 18).
V18_DDL = """
CREATE TABLE songs (name TEXT PRIMARY KEY, best_score INTEGER DEFAULT 0, best_fg_score INTEGER DEFAULT 0,
    last_updated REAL, attempt_lifetime INTEGER DEFAULT 0, attempts_first INTEGER DEFAULT 0);
CREATE TABLE team_buff_loadouts (song_name TEXT, team_buff TEXT, loadout_hash TEXT, score INTEGER,
    fg_score INTEGER DEFAULT 0, gear_ids_blob BLOB, minis_ids_blob BLOB, details_json TEXT, force_details_json TEXT,
    timestamp REAL, PRIMARY KEY (song_name, team_buff, loadout_hash), FOREIGN KEY (song_name) REFERENCES songs(name));
CREATE TABLE team_buff_fg_loadouts (song_name TEXT, team_buff TEXT, loadout_hash TEXT, score INTEGER, fg_score INTEGER,
    gear_ids_blob BLOB, minis_ids_blob BLOB, details_json TEXT, force_details_json TEXT, timestamp REAL,
    PRIMARY KEY (song_name, team_buff, loadout_hash), FOREIGN KEY (song_name) REFERENCES songs(name));
CREATE INDEX idx_team_buff_loadouts_score ON team_buff_loadouts (song_name, team_buff, score DESC);
CREATE INDEX idx_team_buff_loadouts_fg_score ON team_buff_loadouts (song_name, team_buff, fg_score DESC);
CREATE INDEX idx_team_buff_fg_loadouts_score ON team_buff_fg_loadouts (song_name, team_buff, fg_score DESC);
CREATE TABLE gear_name_encoding (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE mini_name_encoding (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
PRAGMA user_version = 18;
"""


class V18Writer:
    """Writes version 18 rows the way the old store stored them (id blobs, packed details)."""

    def __init__(self, path) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.executescript(V18_DDL)

    def song(self, name: str, last_updated: float = 1_700_000_000.5) -> None:
        self.conn.execute("INSERT INTO songs VALUES (?, 1, 1, ?, 3, 4)", (name, last_updated))

    def meta(self, song, loadout_hash, score, fg_score, gear, minis, details, timestamp=1_700_000_000) -> None:
        self.conn.execute(
            "INSERT INTO team_buff_loadouts VALUES (?, 'T5', ?, ?, ?, ?, ?, ?, NULL, ?)",
            (
                song,
                loadout_hash,
                score,
                fg_score,
                self._ids("gear", gear),
                self._groups(minis),
                json.dumps(details),
                timestamp,
            ),
        )

    def fg(self, song, loadout_hash, score, fg_score, gear, minis, details, payload, timestamp=1_700_000_000) -> None:
        self.conn.execute(
            "INSERT INTO team_buff_fg_loadouts VALUES (?, 'T5', ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                song,
                loadout_hash,
                score,
                fg_score,
                self._ids("gear", gear),
                self._groups(minis),
                json.dumps(details),
                json.dumps(payload),
                timestamp,
            ),
        )

    def close(self) -> None:
        self.conn.commit()
        self.conn.close()

    def _id(self, table: str, name: str) -> int:
        self.conn.execute(f"INSERT OR IGNORE INTO {table}_name_encoding (name) VALUES (?)", (name,))
        return self.conn.execute(f"SELECT id FROM {table}_name_encoding WHERE name = ?", (name,)).fetchone()[0]

    def _ids(self, table: str, names: Iterable[str]) -> bytes:
        return b"".join(_uvarint(self._id(table, n)) for n in names)

    def _groups(self, groups: Iterable[Iterable[str]]) -> bytes:
        return b"".join(b"".join(_uvarint(self._id("mini", n)) for n in g) + b"\x00" for g in groups)


def _uvarint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte, value = value & 0x7F, value >> 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)
