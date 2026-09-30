"""Version 18 shaped views of store records, for callers that still read or write them (temporary).

best_loadouts returns what data.database.get_best_loadouts returned: meta board entries by score, then
FG-only entries by FG score (ties as that reader ordered them), each an entry dict with the unpacked
version 18 details and FG payload; rows_from_entries is its inverse (promotion of a solve's leaderboard, the
website's job databases). store_entries saves the pipeline's result entries. Callers: GA seeding and the POST
/optimize response (removed in stages 4 and 9), the website's tier replays, job databases and readers (stage 8).
"""

from __future__ import annotations

import os
import sqlite3
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from ..data.loadout_equivalence import representative_mini_names
from ..domain.leaderboard import LOADOUTS_PER_SONG_LIMIT
from ..gamedata import MINI_ASCENSION_VERSION, STATS, Gear, Mini
from ..stats import GEM_KINDS
from .boards import Candidate, Row
from .db import load_boards, load_traces, store_results
from .entries import candidates_from_entries
from .records import FgResult, Loadout, MetaResult, encode_trace
from .schema import connect

_GC_KEYS = ("Perfect Points", "Combo Multiplier", "Fever Multiplier", "Element")


def best_loadouts(
    conn: sqlite3.Connection,
    song: str,
    tier: str = "T5",
    *,
    limit: int = LOADOUTS_PER_SONG_LIMIT,
    gears: Mapping[str, Gear] | None = None,
    minis: Mapping[str, Mini] | None = None,
) -> list[dict[str, Any]]:
    boards = load_boards(conn, song, tier)
    # The version 18 reader's orders (its query plans'): meta by score, then FG score, then entry; FG by FG
    # score, then loadout hash.
    meta = sorted(boards.meta, key=lambda x: (-x.score, -(x.fg_score or 0), x.meta.seq))[:limit]
    fg = sorted(boards.fg, key=lambda x: (-x.fg_score, x.loadout_hash))[:limit]
    traces = load_traces(conn, song, tier, {x.loadout_hash for x in meta + fg})
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for x in meta:
        entry = _entry(x, meta_details(x, traces[x.loadout_hash].meta), gears, minis)
        entry["fg_score"] = x.fg_score or 0
        if x.fg is not None and x in fg:
            entry["force"] = fg_payload(x, traces[x.loadout_hash].fg)
            entry["fg_base_score"] = x.score
        seen.add(x.loadout_hash)
        out.append(entry)
    for x in fg:
        if x.loadout_hash in seen:
            continue
        entry = _entry(x, fg_details(x), gears, minis)
        entry["fg_score"] = x.fg_score
        entry["force"] = fg_payload(x, traces[x.loadout_hash].fg)
        out.append(entry)
    return out


def read_best_loadouts(
    path: str | os.PathLike[str],
    song: str,
    tier: str = "T5",
    *,
    limit: int = LOADOUTS_PER_SONG_LIMIT,
    gears: Mapping[str, Gear] | None = None,
    minis: Mapping[str, Mini] | None = None,
) -> list[dict[str, Any]]:
    """best_loadouts of a database file; [] when the file does not exist."""
    if not Path(path).exists():
        return []
    conn = connect(path)
    try:
        return best_loadouts(conn, song, tier, limit=limit, gears=gears, minis=minis)
    finally:
        conn.close()


def store_entries(
    conn: sqlite3.Connection,
    song: str,
    tier: str,
    entries: Sequence[Mapping[str, Any]],
    *,
    gears: Mapping[str, Gear],
    minis: Mapping[str, Mini],
    now: float | None = None,
) -> None:
    """Merge entry dicts into a song's boards (one transaction); an empty batch only marks the song."""
    now = time.time() if now is None else now
    row = conn.execute(
        "SELECT primary_color, secondary_color FROM loadouts WHERE song_name = ? AND team_buff = ? LIMIT 1",
        (song, tier),
    ).fetchone()
    candidates = candidates_from_entries(
        song, tier, entries, gears=gears, minis=minis, stored_colors=tuple(row) if row else None, now=int(now)
    )
    store_results(conn, song, tier, candidates, now=now)


def promote_entries(
    conn: sqlite3.Connection, song: str, tier: str, entries: Sequence[Mapping[str, Any]], *, now: float | None = None
) -> None:
    """Merge a solve's leaderboard (best_loadouts entries of its result database) into this database."""
    rows = rows_from_entries(song, tier, entries)
    store_results(conn, song, tier, [Candidate(row) for row in rows], now=now)


def rows_from_entries(song: str, tier: str, entries: Sequence[Mapping[str, Any]]) -> list[Row]:
    """The rows best_loadouts read the entries from (entry numbers and write times are not carried: 0)."""
    rows: list[Row] = []
    for entry in entries:
        details = entry["details"]
        force = entry.get("force")
        meta = meta_trace = fg = fg_trace = None
        if "BaseScore" not in details:  # fg_details carries the paired base score; meta_details never does
            meta = MetaResult(
                element=details["se"],
                gems=_gems(details["gc"], details["FT"], details["FF"]),
                stats=tuple(details["st"]),
                updated=0,
                seq=0,
            )
            meta_trace = encode_trace(details.get("TimelineFrontier"))
        if force is not None:
            gem_counts = force["GemCounts"]
            fg = FgResult(
                element=force["SelectedElement"],
                gems=_gems([gem_counts[k] for k in _GC_KEYS], force["FT"], force["FF"]),
                stats=tuple(force["BaseStats"][s] for s in STATS),
                surface=tuple(force["response_surface"]),
                updated=0,
                seq=0,
            )
            fg_trace = encode_trace({k: v for k, v in force["ForceGreats"].items() if k != "final_score"})
        loadout = Loadout(
            song=song,
            tier=tier,
            loadout_hash=entry["loadout_hash"],
            gear=tuple(item.name if isinstance(item, Gear) else item for item in entry["gear"]),
            minis=tuple(tuple(group) for group in entry["mini_groups"]),
            primary=details["pc"],
            secondary=details["sc"],
            mini_ascension=details.get("Mini Ascension Source Version") if details.get("Mini Ascension Materialized") else None,
            score=int(entry["score"]),
            fg_score=int(entry.get("fg_score") or 0) or None,
            meta=meta,
            fg=fg,
        )
        rows.append(Row(loadout, meta_trace, fg_trace))
    return rows


def meta_details(loadout: Loadout, trace: dict[str, Any] | None) -> dict[str, Any]:
    """The meta board's details_json as version 18 unpacked it."""
    details = _result_details(loadout, loadout.meta)
    if trace is not None:
        details["TimelineFrontier"] = trace
    _mark_ascension(details, loadout)
    return details


def fg_details(loadout: Loadout) -> dict[str, Any]:
    """The FG board's details_json (its FG gems and stats, and the paired base score) as version 18 unpacked it,
    plus the Mini Ascension marker of loadouts stored with one (version 18 FG rows never had it)."""
    details = _result_details(loadout, loadout.fg)
    details["BaseScore"] = loadout.score
    _mark_ascension(details, loadout)
    return details


def _mark_ascension(details: dict[str, Any], loadout: Loadout) -> None:
    if loadout.mini_ascension is not None:
        details["Mini Ascension Materialized"] = True
        details["Mini Ascension Source Version"] = loadout.mini_ascension


def _gems(gc: Sequence[int], ft: int, ff: int) -> tuple[int, ...]:
    allocation = dict(zip(_GC_KEYS, gc))
    allocation["Fever Time"] = int(ft)
    allocation["Fever Fill Rate"] = int(ff)
    return tuple(int(allocation[k]) for k in GEM_KINDS)


def fg_payload(loadout: Loadout, trace: dict[str, Any]) -> dict[str, Any]:
    """The FG board's force_details_json (the replay payload) as version 18 stored it."""
    result = loadout.fg
    allocation = dict(zip(GEM_KINDS, result.gems))
    return {
        "Score": loadout.fg_score,
        "FT": allocation["Fever Time"],
        "FF": allocation["Fever Fill Rate"],
        "GemCounts": {key: allocation[key] for key in _GC_KEYS},
        "Selected Element": result.element,
        "BaseScore": loadout.score,
        "BaseStats": dict(zip(STATS, result.stats)),
        "response_surface": list(result.surface),
        "ForceGreats": {"final_score": loadout.fg_score, **trace},
        "SelectedElement": result.element,
    }


def is_current_mini_ascension(loadout: Loadout) -> bool:
    return loadout.mini_ascension == MINI_ASCENSION_VERSION


def _result_details(loadout: Loadout, result: MetaResult | FgResult) -> dict[str, Any]:
    allocation = dict(zip(GEM_KINDS, result.gems))
    gc = [allocation[key] for key in _GC_KEYS]
    st = list(result.stats)
    return {
        "FT": allocation["Fever Time"],
        "FF": allocation["Fever Fill Rate"],
        "st": st,
        "gc": gc,
        "se": result.element,
        "pc": loadout.primary,
        "sc": loadout.secondary,
        "Stats": dict(zip(STATS, st)),
        "GemCounts": dict(zip(_GC_KEYS, gc)),
        "SelectedElement": result.element,
        "PrimaryColor": loadout.primary,
        "SecondaryColor": loadout.secondary,
    }


def _entry(loadout: Loadout, details: dict[str, Any], gears, minis) -> dict[str, Any]:
    groups = [list(group) for group in loadout.minis]
    names = representative_mini_names(groups)
    return {
        "loadout_hash": loadout.loadout_hash,
        "score": loadout.score,
        "gear": [gears.get(n, n) for n in loadout.gear] if gears else list(loadout.gear),
        "minis": [minis.get(n, n) for n in names] if minis else names,
        "mini_groups": groups,
        "details": details,
        "force": None,
    }
