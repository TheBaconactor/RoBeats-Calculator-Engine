"""Results database version 18 (engine <= stage 3A): a strict reader and the migration to version 19.

Version 18 kept two leaderboard tables per song and TeamBuff tier (team_buff_loadouts: meta board;
team_buff_fg_loadouts: Force Greats board), item names as varint id blobs over two name tables, and JSON
details. Every stored key is either carried into the records or listed in DROPPED (nothing reads it:
copies of other values, GA internals, the six GA item keys, and the Mini Ascension song/color keys). A meta
row's ForceGreats copy is its loadout's FG result: dropped when the FG row carries that result, kept as the FG
replay of a loadout whose FG row was pruned (version 18 kept no FG gems for those).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Collection, Iterator
from dataclasses import dataclass, field

from ..gamedata import STATS
from .boards import Row
from .records import SURFACE_SIZE, FgResult, Loadout, MetaResult, encode_trace
from .schema import VERSION, create_tables

# details_json of the meta board.
_META_KEYS = {"FT", "FF", "st", "gc", "se", "pc", "sc", "TimelineFrontier", "ForceGreats"}
_MARKER = "Mini Ascension Materialized"
_MARKER_VERSION = "Mini Ascension Source Version"
_MARKER_COLORS = ("Mini Ascension Materialized Primary Color", "Mini Ascension Materialized Secondary Color")
# details_json of the FG board (a copy of the payload's gems, stats and base score, plus the song colors).
_FG_DETAIL_KEYS = {"FT", "FF", "st", "gc", "se", "pc", "sc", "BaseScore"}
# force_details_json of the FG board.
_FG_KEYS = {
    "Score",
    "BaseScore",
    "FT",
    "FF",
    "GemCounts",
    "SelectedElement",
    "BaseStats",
    "response_surface",
    "ForceGreats",
}

DROPPED = {
    "meta": {"GemCounts", "BaseScore", "Mini Ascension Materialized Song", *_MARKER_COLORS},
    "fg_details": {"GemCounts"},
    "fg": {
        "Selected Element",
        "GenomeIDs",
        "RawGASearchScore",
        "_ga_gpu_run_idx",
        "_ga_gpu_row_idx",
        "_base_stats7",
        "Genome",
        "Gear",
        "Minis",
        "GearNames",
        "MiniNames",
        "Details",
    },
}
# gc = [Perfect Points, Combo Multiplier, Fever Multiplier, Element]; records keep stats.GEM_KINDS order.
_GC_KEYS = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Element")


@dataclass
class Report:
    songs: int = 0
    meta_rows: int = 0
    fg_rows: int = 0
    loadouts: int = 0
    twins: int = 0
    # Twins whose FG row paired a different base score than the meta row (the meta row's score is kept).
    paired_score_conflicts: list[tuple[str, str, int, int]] = field(default_factory=list)
    meta_without_trace: list[tuple[str, str]] = field(default_factory=list)
    fg_replays: int = 0  # FG replays kept without an FG result (their FG row was pruned)


def read_rows(conn: sqlite3.Connection, song: str, report: Report | None = None) -> list[Row]:
    """Every loadout of one song (all tiers) as version 19 rows."""
    report = report if report is not None else Report()
    gear_names = dict(conn.execute("SELECT id, name FROM gear_name_encoding"))
    mini_names = dict(conn.execute("SELECT id, name FROM mini_name_encoding"))
    columns = (
        "team_buff, loadout_hash, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json,"
        " timestamp, rowid"
    )
    meta_rows = conn.execute(f"SELECT {columns} FROM team_buff_loadouts WHERE song_name = ?", (song,)).fetchall()
    fg_rows = conn.execute(f"SELECT {columns} FROM team_buff_fg_loadouts WHERE song_name = ?", (song,)).fetchall()
    report.meta_rows += len(meta_rows)
    report.fg_rows += len(fg_rows)
    fg_by_key = {(r[0], r[1]): r for r in fg_rows}
    if len(fg_by_key) != len(fg_rows):
        raise ValueError(f"{song}: duplicate FG rows")
    rows: list[Row] = []
    seen: set[tuple[str, str]] = set()
    for meta_row in meta_rows:
        key = (meta_row[0], meta_row[1])
        seen.add(key)
        rows.append(_loadout(song, meta_row, fg_by_key.get(key), gear_names, mini_names, report))
    for key, fg_row in fg_by_key.items():
        if key not in seen:
            rows.append(_loadout(song, None, fg_row, gear_names, mini_names, report))
    report.loadouts += len(rows)
    return rows


def song_list(conn: sqlite3.Connection, table: str = "songs") -> list[tuple[str, float]]:
    """(name, last_updated) of every song, in insertion order."""
    out = conn.execute(f"SELECT name, last_updated FROM {table} ORDER BY rowid").fetchall()
    missing = [name for name, updated in out if updated is None]
    if missing:
        raise ValueError(f"songs without last_updated: {missing[:5]}")
    return [(name, float(updated)) for name, updated in out]


def migrate(conn: sqlite3.Connection, *, keep_v18_tables: bool, songs: Collection[str] | None = None) -> Report:
    """Migrate a version 18 database to version 19 in one transaction.

    keep_v18_tables leaves the old leaderboard and name tables in place (frozen) for readers that have not
    switched yet; drop them later with drop_v18_tables.
    """
    report = Report()
    conn.execute("BEGIN IMMEDIATE")
    try:
        song_rows = song_list(conn)
        orphans = conn.execute(
            "SELECT DISTINCT song_name FROM team_buff_loadouts WHERE song_name NOT IN (SELECT name FROM songs)"
            " UNION SELECT DISTINCT song_name FROM team_buff_fg_loadouts WHERE song_name NOT IN (SELECT name FROM songs)"
        ).fetchall()
        if orphans:
            raise ValueError(f"loadouts of songs missing from the songs table: {[r[0] for r in orphans][:5]}")
        # The old songs table moves aside so the new one is created under its own name (same DDL as a fresh DB).
        conn.execute("ALTER TABLE songs RENAME TO songs_v18")
        create_tables(conn)
        from .db import insert_rows, insert_song

        for name, updated in song_rows:
            if songs is not None and name not in songs:
                continue
            insert_song(conn, name, updated)
            insert_rows(conn, read_rows(conn, name, report))
            report.songs += 1
        conn.execute("DROP TABLE songs_v18")
        if not keep_v18_tables:
            drop_v18_tables(conn)
        conn.execute(f"PRAGMA user_version = {VERSION}")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return report


def drop_v18_tables(conn: sqlite3.Connection) -> None:
    for table in ("team_buff_loadouts", "team_buff_fg_loadouts", "gear_name_encoding", "mini_name_encoding"):
        conn.execute(f"DROP TABLE IF EXISTS {table}")


def _loadout(song, meta_row, fg_row, gear_names, mini_names, report: Report) -> Row:
    any_row = meta_row if meta_row is not None else fg_row
    tier, loadout_hash = any_row[0], any_row[1]
    gear = _names(any_row[4], gear_names)
    minis = _groups(any_row[5], mini_names)
    meta = meta_trace = fg = fg_trace = None
    ascension = fg_copy = None
    if meta_row is not None:
        details = json.loads(meta_row[6])
        if meta_row[7] is not None:
            raise ValueError(f"{song} {loadout_hash}: meta row with force_details_json")
        meta, meta_trace_payload, colors, ascension = _meta_part(song, loadout_hash, details, meta_row)
        meta_trace = encode_trace(meta_trace_payload)
        if meta_trace_payload is None:
            report.meta_without_trace.append((song, loadout_hash))
        fg_copy = details.get("ForceGreats")
        if fg_copy is not None and fg_copy.get("final_score") != int(meta_row[3] or 0):
            raise ValueError(f"{song} {loadout_hash}: the meta row's FG copy scores {fg_copy.get('final_score')}, the row {meta_row[3]}")
    if fg_row is not None:
        fg, fg_trace_payload, fg_colors = _fg_part(song, loadout_hash, fg_row)
        fg_trace = encode_trace(fg_trace_payload)
        if meta_row is None:
            colors = fg_colors
        else:
            report.twins += 1
            if (_names(fg_row[4], gear_names), _groups(fg_row[5], mini_names)) != (gear, minis):
                raise ValueError(f"{song} {loadout_hash}: meta and FG rows name different items")
            if fg_colors != colors:
                raise ValueError(f"{song} {loadout_hash}: meta and FG rows have different colors")
            if int(fg_row[3]) != int(meta_row[3]):
                raise ValueError(f"{song} {loadout_hash}: meta row FG score {meta_row[3]} != FG row {fg_row[3]}")
            if int(fg_row[2]) != int(meta_row[2]):
                report.paired_score_conflicts.append((song, loadout_hash, int(meta_row[2]), int(fg_row[2])))
    if fg_row is None and fg_copy is not None and fg_copy.get("frontier_trace"):
        fg_trace = encode_trace({k: v for k, v in fg_copy.items() if k != "final_score"})
        report.fg_replays += 1
    if meta_row is not None:
        score = int(meta_row[2])
        fg_score = int(meta_row[3] or 0) or None
    else:
        score = int(fg_row[2])
        fg_score = int(fg_row[3])
    loadout = Loadout(
        song=song,
        tier=tier,
        loadout_hash=loadout_hash,
        gear=gear,
        minis=minis,
        primary=colors[0],
        secondary=colors[1],
        mini_ascension=ascension,
        score=score,
        fg_score=fg_score,
        meta=meta,
        fg=fg,
        on_meta=meta_row is not None,
        on_fg=fg_row is not None,
    )
    return Row(loadout, meta_trace, fg_trace)


def _meta_part(song: str, loadout_hash: str, details: dict, meta_row):
    marker_keys = {_MARKER, _MARKER_VERSION}
    unexpected = set(details) - _META_KEYS - marker_keys - DROPPED["meta"]
    if unexpected or not {"FT", "FF", "st", "gc", "se", "pc", "sc"} <= set(details):
        raise ValueError(f"{song} {loadout_hash}: meta details keys {sorted(details)}")
    gc = details["gc"]
    if "GemCounts" in details and details["GemCounts"] != dict(zip(_GC_KEYS, gc)):
        raise ValueError(f"{song} {loadout_hash}: GemCounts copy differs from gc")
    colors = (details["pc"], details["sc"])
    ascension = None
    if details.get(_MARKER):
        ascension = details[_MARKER_VERSION]
        marked = tuple(details.get(key) for key in _MARKER_COLORS)
        if marked not in (colors, (None, None)):
            raise ValueError(f"{song} {loadout_hash}: Mini Ascension colors {marked} != row colors {colors}")
    elif _MARKER_VERSION in details:
        raise ValueError(f"{song} {loadout_hash}: Mini Ascension version without the marker")
    meta = MetaResult(
        element=details["se"],
        gems=(gc[0], gc[1], gc[2], int(details["FT"]), int(details["FF"]), gc[3]),
        stats=_stats_list(details["st"]),
        updated=_seconds(meta_row[8]),
        seq=int(meta_row[9]),
    )
    return meta, details.get("TimelineFrontier"), colors, ascension


def _fg_part(song: str, loadout_hash: str, fg_row):
    score, fg_score = int(fg_row[2]), int(fg_row[3])
    details = json.loads(fg_row[6])
    payload = json.loads(fg_row[7])
    unexpected = set(payload) - _FG_KEYS - DROPPED["fg"]
    if unexpected or not _FG_KEYS <= set(payload):
        raise ValueError(f"{song} {loadout_hash}: FG payload keys {sorted(payload)}")
    unexpected = set(details) - _FG_DETAIL_KEYS - DROPPED["fg_details"]
    if unexpected or not _FG_DETAIL_KEYS <= set(details):
        raise ValueError(f"{song} {loadout_hash}: FG details keys {sorted(details)}")
    element = payload["SelectedElement"]
    if payload.get("Selected Element", element) != element:
        raise ValueError(f"{song} {loadout_hash}: two different FG selected elements")
    gem_counts = payload["GemCounts"]
    if set(gem_counts) != set(_GC_KEYS):
        raise ValueError(f"{song} {loadout_hash}: FG GemCounts keys {sorted(gem_counts)}")
    stats = tuple(int(payload["BaseStats"][stat]) for stat in STATS)
    fg = FgResult(
        element=element,
        gems=(
            gem_counts["Perfect Points"],
            gem_counts["Combo Multiplier"],
            gem_counts["Fever Multiplier"],
            int(payload["FT"]),
            int(payload["FF"]),
            gem_counts["Element"],
        ),
        stats=stats,
        surface=tuple(int(v) for v in payload["response_surface"]),
        updated=_seconds(fg_row[8]),
        seq=int(fg_row[9]),
    )
    if len(payload["response_surface"]) != SURFACE_SIZE:
        raise ValueError(f"{song} {loadout_hash}: response surface {payload['response_surface']!r}")
    # The copies must agree with what is carried.
    copies = {
        "Score": (payload["Score"], fg_score),
        "BaseScore": (payload["BaseScore"], score),
        "details BaseScore": (details["BaseScore"], score),
        "details st": (tuple(details["st"]), stats),
        "details gc": (tuple(details["gc"]), tuple(gem_counts[k] for k in _GC_KEYS)),
        "details FT/FF": ((details["FT"], details["FF"]), (payload["FT"], payload["FF"])),
        "details se": (details["se"], element),
    }
    if "GemCounts" in details:
        copies["details GemCounts"] = (details["GemCounts"], gem_counts)
    trace = dict(payload["ForceGreats"])
    copies["final_score"] = (trace.pop("final_score"), fg_score)
    differing = [name for name, (a, b) in copies.items() if a != b]
    if differing:
        raise ValueError(f"{song} {loadout_hash}: FG copies differ: {differing}")
    if not trace.get("frontier_trace"):
        raise ValueError(f"{song} {loadout_hash}: FG payload without a frontier trace")
    return fg, trace, (details["pc"], details["sc"])


def _seconds(timestamp) -> int:
    # Version 18 stamped rows with strftime('%s', 'now'): whole seconds.
    if float(timestamp) != int(float(timestamp)):
        raise ValueError(f"timestamp {timestamp!r} is not whole seconds")
    return int(float(timestamp))


def _stats_list(st) -> tuple[int, ...]:
    if len(st) != len(STATS):
        raise ValueError(f"stats {st!r}")
    return tuple(int(v) for v in st)


def _names(blob, names_by_id) -> tuple[str, ...]:
    return tuple(names_by_id[i] for i in _uvarints(blob) if i)


def _groups(blob, names_by_id) -> tuple[tuple[str, ...], ...]:
    groups: list[tuple[str, ...]] = []
    current: list[str] = []
    for i in _uvarints(blob):
        if i == 0:
            if current:
                groups.append(tuple(current))
            current = []
        else:
            current.append(names_by_id[i])
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def _uvarints(blob) -> Iterator[int]:
    if blob is None:
        return
    value = shift = 0
    for byte in bytes(blob):
        value |= (byte & 0x7F) << shift
        if byte & 0x80:
            shift += 7
            continue
        yield value
        value = shift = 0
    if shift:
        raise ValueError(f"truncated varint blob {bytes(blob)!r}")
