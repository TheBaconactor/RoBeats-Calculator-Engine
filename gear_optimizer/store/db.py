"""Reads and writes of the results database (store.tables)."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from collections.abc import Collection, Iterable, Iterator, Sequence
from dataclasses import dataclass

from . import schema
from .boards import FG_ORDER, META_ORDER, Row, merge
from .records import (
    Loadout,
    Traces,
    decode_fg,
    decode_groups,
    decode_meta,
    decode_names,
    decode_trace,
)
from .tables import MODELESS_COLUMNS, MODELESS_ROW_COLUMNS, insert_rows, truncate_wal

_BOARDS = {"meta": ("meta_board", META_ORDER), "fg": ("fg_board", FG_ORDER)}


@dataclass(frozen=True, slots=True)
class Boards:
    meta: list[Loadout]
    fg: list[Loadout]


def load_boards(conn: sqlite3.Connection, mode: str, song: str, tier: str) -> Boards:
    """A song's two boards in board order."""
    return Boards(
        [_loadout(r, mode) for r in _board_rows(conn, "meta", mode, (song,), tier)],
        [_loadout(r, mode) for r in _board_rows(conn, "fg", mode, (song,), tier)],
    )


def iter_board(
    conn: sqlite3.Connection, board: str, *, mode: str, tier: str, songs: Collection[str] | None = None
) -> Iterator[Loadout]:
    """Every loadout on one board ("meta" or "fg"), song by song (by name), each song in board order."""
    for row in _board_rows(conn, board, mode, songs, tier):
        yield _loadout(row, mode)


def load_traces(
    conn: sqlite3.Connection, mode: str, song: str, tier: str, hashes: Iterable[str]
) -> dict[str, Traces]:
    wanted = list(hashes)
    out: dict[str, Traces] = {}
    for chunk in _chunks(wanted):
        rows = conn.execute(
            "SELECT loadout_hash, meta_trace, fg_trace FROM loadouts WHERE timing_mode = ? AND song_name = ?"
            f" AND team_buff = ? AND loadout_hash IN ({_marks(chunk)})",
            (mode, song, tier, *chunk),
        )
        for loadout_hash, meta_trace, fg_trace in rows:
            out[loadout_hash] = Traces(decode_trace(meta_trace), decode_trace(fg_trace))
    return out


def present_songs(conn: sqlite3.Connection, mode: str, names: Iterable[str]) -> set[str]:
    """The given songs the database has processed in `mode` (a songs row: a build, or a run that stored nothing)."""
    out: set[str] = set()
    for chunk in _chunks(sorted(set(names))):
        rows = conn.execute(
            f"SELECT name FROM songs WHERE timing_mode = ? AND name IN ({_marks(chunk)})", (mode, *chunk)
        )
        out.update(row[0] for row in rows)
    return out


def song_names(conn: sqlite3.Connection, mode: str) -> list[str]:
    return [row[0] for row in conn.execute("SELECT name FROM songs WHERE timing_mode = ? ORDER BY rowid", (mode,))]


def latest_update(conn: sqlite3.Connection) -> float | None:
    """When the database last stored a result, in any mode (None when empty)."""
    return conn.execute("SELECT MAX(last_updated) FROM songs").fetchone()[0]


def last_updated(conn: sqlite3.Connection, mode: str, songs: Collection[str] | None = None) -> dict[str, float]:
    if songs is None:
        return dict(conn.execute("SELECT name, last_updated FROM songs WHERE timing_mode = ?", (mode,)))
    out: dict[str, float] = {}
    for chunk in _chunks(list(songs)):
        out.update(
            conn.execute(
                f"SELECT name, last_updated FROM songs WHERE timing_mode = ? AND name IN ({_marks(chunk)})",
                (mode, *chunk),
            )
        )
    return out


def board_sizes(conn: sqlite3.Connection, mode: str) -> dict[tuple[str, str], tuple[int, int]]:
    """(song, tier) -> (meta board size, FG board size) in `mode`: each board counted on its covering index."""
    sizes: dict[tuple[str, str], list[int]] = {}
    for i, (column, _order) in enumerate(_BOARDS.values()):
        rows = conn.execute(
            f"SELECT song_name, team_buff, COUNT(*) FROM loadouts WHERE timing_mode = ? AND {column} = 1"
            " GROUP BY song_name, team_buff",
            (mode,),
        )
        for song, tier, count in rows:
            sizes.setdefault((song, tier), [0, 0])[i] = count
    return {key: (meta, fg) for key, (meta, fg) in sizes.items()}


def song_digest(conn: sqlite3.Connection, mode: str, song: str) -> str:
    """A digest of every stored byte of a song's rows in `mode`: it changes exactly when those rows change."""
    digest = hashlib.sha256()
    rows = conn.execute(
        f"SELECT {MODELESS_ROW_COLUMNS} FROM loadouts WHERE timing_mode = ? AND song_name = ?"
        " ORDER BY team_buff, loadout_hash",
        (mode, song),
    )
    for row in rows:
        for value in row:
            digest.update(repr(value).encode())
    return digest.hexdigest()


def load_rows(conn: sqlite3.Connection, mode: str, song: str, tier: str) -> list[Row]:
    rows = conn.execute(
        f"SELECT {MODELESS_ROW_COLUMNS} FROM loadouts WHERE timing_mode = ? AND song_name = ? AND team_buff = ?",
        (mode, song, tier),
    )
    return [Row(_loadout(r, mode), r["meta_trace"], r["fg_trace"]) for r in rows]


def store_results(
    conn: sqlite3.Connection, mode: str, song: str, tier: str, results: Sequence[Row], *, now: float | None = None
) -> None:
    """Merge one solve's results into a song's boards and mark the song processed (one transaction)."""
    strays = {(r.loadout.mode, r.loadout.song, r.loadout.tier) for r in results} - {(mode, song, tier)}
    if strays:
        raise ValueError(f"results for {sorted(strays)} cannot be stored under {mode} {song!r} {tier}")
    now = time.time() if now is None else now
    conn.execute("BEGIN IMMEDIATE")
    try:
        _touch_song(conn, mode, song, now)
        if results:
            # One MAX per query: SQLite reads a lone MIN/MAX from the index; two in one query scan the table.
            last_meta = conn.execute("SELECT MAX(meta_seq) FROM loadouts").fetchone()[0]
            last_fg = conn.execute("SELECT MAX(fg_seq) FROM loadouts").fetchone()[0]
            next_seq = ((last_meta or 0) + 1, (last_fg or 0) + 1)
            merged = merge(load_rows(conn, mode, song, tier), results, now=int(now), next_seq=next_seq)
            conn.execute(
                "DELETE FROM loadouts WHERE timing_mode = ? AND song_name = ? AND team_buff = ?", (mode, song, tier)
            )
            insert_rows(conn, merged)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    truncate_wal(conn)


def promote(
    source: str | os.PathLike[str], target: str | os.PathLike[str], mode: str, song: str, tier: str
) -> None:
    """Merge a song's results stored in another database (an isolated solve's) into `target`, every attached
    result included: the source's meta board first in board order (new loadouts are numbered in it), then its FG
    board, then any other loadout."""
    conn = schema.connect(source)
    try:
        rows = {row.loadout.loadout_hash: row for row in load_rows(conn, mode, song, tier)}
        boards = load_boards(conn, mode, song, tier)
    finally:
        conn.close()
    order = dict.fromkeys([x.loadout_hash for x in boards.meta + boards.fg] + sorted(rows))
    conn = schema.connect(target, write=True)
    try:
        store_results(conn, mode, song, tier, [rows[h] for h in order])
    finally:
        conn.close()


def _touch_song(conn: sqlite3.Connection, mode: str, song: str, now: float) -> None:
    conn.execute(
        "INSERT INTO songs (timing_mode, name, last_updated) VALUES (?, ?, ?)"
        " ON CONFLICT (timing_mode, name) DO UPDATE SET last_updated = excluded.last_updated",
        (mode, song, now),
    )


def _board_rows(
    conn: sqlite3.Connection, board: str, mode: str, songs: Collection[str] | None, tier: str
) -> Iterator[sqlite3.Row]:
    column, order = _BOARDS[board]
    base = f"SELECT {MODELESS_COLUMNS} FROM loadouts WHERE timing_mode = ? AND team_buff = ? AND {column} = 1"
    if songs is None:
        yield from conn.execute(f"{base} ORDER BY song_name, {order}", (mode, tier))
        return
    for chunk in _chunks(sorted(set(songs))):
        yield from conn.execute(
            f"{base} AND song_name IN ({_marks(chunk)}) ORDER BY song_name, {order}", (mode, tier, *chunk)
        )


def _loadout(row: sqlite3.Row, mode: str) -> Loadout:
    return Loadout(
        mode=mode,
        song=row["song_name"],
        tier=row["team_buff"],
        loadout_hash=row["loadout_hash"],
        gear=decode_names(row["gear"]),
        minis=decode_groups(row["minis"]),
        primary=row["primary_color"],
        secondary=row["secondary_color"],
        mini_ascension=row["mini_ascension"],
        score=row["score"],
        fg_score=row["fg_score"],
        meta=None
        if row["meta_result"] is None
        else decode_meta(row["meta_result"], row["meta_updated"], row["meta_seq"]),
        fg=None if row["fg_result"] is None else decode_fg(row["fg_result"], row["fg_updated"], row["fg_seq"]),
        on_meta=bool(row["meta_board"]),
        on_fg=bool(row["fg_board"]),
    )


def _chunks(values: list, size: int = 500) -> Iterator[list]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _marks(values: Iterable) -> str:
    return ",".join("?" for _ in values)
