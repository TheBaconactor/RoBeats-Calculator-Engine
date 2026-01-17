from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from gear_optimizer.core.constants import TOTAL_GEM_BUDGET
from gear_optimizer.data.loadout_equivalence import decode_minis_json, extract_song_colors

from .keys import ELEMENT_TO_ID
from .models import SongCandidate


def fetch_song_names(conn: sqlite3.Connection) -> List[str]:
    names: set[str] = set()
    for table in ("loadouts", "fg_loadouts"):
        try:
            rows = conn.execute(f"SELECT DISTINCT song_name FROM {table}").fetchall()
        except sqlite3.Error:
            continue
        for row in rows:
            try:
                name = row["song_name"] if isinstance(row, sqlite3.Row) else row[0]
            except Exception:
                continue
            if name:
                names.add(str(name))
    return sorted(names)


def fetch_song_names_limited(conn: sqlite3.Connection, limit: int) -> List[str]:
    limit = int(limit)
    if limit <= 0:
        return []
    try:
        rows = conn.execute(
            """
            SELECT song_name
            FROM (
                SELECT song_name FROM loadouts
                UNION
                SELECT song_name FROM fg_loadouts
            )
            WHERE song_name IS NOT NULL AND song_name != ''
            ORDER BY song_name
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    except sqlite3.Error:
        return []

    names: List[str] = []
    for row in rows:
        try:
            name = row["song_name"] if isinstance(row, sqlite3.Row) else row[0]
        except Exception:
            continue
        if name:
            names.append(str(name))
    return names


def fetch_song_peak(conn: sqlite3.Connection, song_name: str) -> Tuple[int, int, int]:
    try:
        base_peak = conn.execute(
            "SELECT MAX(score) FROM loadouts WHERE song_name = ?",
            (song_name,),
        ).fetchone()[0]
    except sqlite3.Error:
        base_peak = 0
    try:
        fg_peak = conn.execute(
            "SELECT MAX(fg_score) FROM fg_loadouts WHERE song_name = ?",
            (song_name,),
        ).fetchone()[0]
    except sqlite3.Error:
        fg_peak = 0

    base_peak = int(base_peak or 0)
    fg_peak = int(fg_peak or 0)
    return max(base_peak, fg_peak), base_peak, fg_peak


def fetch_candidates_for_peak(
    conn: sqlite3.Connection,
    song_name: str,
    peak: int,
    base_peak: int,
    fg_peak: int,
) -> List[SongCandidate]:
    candidates: List[SongCandidate] = []
    rows: List[Tuple[str, sqlite3.Row]] = []

    if peak == base_peak:
        try:
            rows.extend(
                [
                    ("loadouts", row)
                    for row in conn.execute(
                        """
                        SELECT rowid AS rowid, song_name, score, fg_score, gear_json, minis_json, details_json, force_details_json
                        FROM loadouts
                        WHERE song_name = ? AND score = ?
                        """,
                        (song_name, peak),
                    )
                ]
            )
        except sqlite3.Error:
            pass

    if peak == fg_peak:
        try:
            rows.extend(
                [
                    ("fg_loadouts", row)
                    for row in conn.execute(
                        """
                        SELECT rowid AS rowid, song_name, score, fg_score, gear_json, minis_json, details_json, force_details_json
                        FROM fg_loadouts
                        WHERE song_name = ? AND fg_score = ?
                        """,
                        (song_name, peak),
                    )
                ]
            )
        except sqlite3.Error:
            pass

    for source_table, row in rows:
        candidate = parse_candidate_row(song_name, source_table, row)
        if candidate is not None:
            candidates.append(candidate)

    return candidates


def fetch_peak_candidates_allow_missing(conn: sqlite3.Connection) -> Tuple[Dict[str, List[SongCandidate]], List[str]]:
    candidates_by_song: Dict[str, List[SongCandidate]] = {}

    peak_map: Dict[str, int] = {}
    base_peak: Dict[str, int] = {}
    fg_peak: Dict[str, int] = {}
    for row in conn.execute(
        """
        WITH base AS (
            SELECT song_name, MAX(score) AS base_peak
            FROM loadouts
            GROUP BY song_name
        ),
        fg AS (
            SELECT song_name, MAX(fg_score) AS fg_peak
            FROM fg_loadouts
            GROUP BY song_name
        ),
        songs AS (
            SELECT song_name FROM loadouts
            UNION
            SELECT song_name FROM fg_loadouts
        )
        SELECT
            songs.song_name AS song_name,
            COALESCE(base.base_peak, 0) AS base_peak,
            COALESCE(fg.fg_peak, 0) AS fg_peak
        FROM songs
        LEFT JOIN base ON base.song_name = songs.song_name
        LEFT JOIN fg ON fg.song_name = songs.song_name
        """
    ):
        name = str(row["song_name"] or "")
        bp = int(row["base_peak"] or 0)
        fp = int(row["fg_peak"] or 0)
        base_peak[name] = bp
        fg_peak[name] = fp
        peak_map[name] = max(bp, fp)

    if not peak_map:
        return {}, []

    try:
        for row in conn.execute(
            """
            WITH base AS (
                SELECT song_name, MAX(score) AS base_peak
                FROM loadouts
                GROUP BY song_name
            )
            SELECT l.rowid AS rowid, l.song_name, l.score, l.fg_score, l.gear_json, l.minis_json, l.details_json, l.force_details_json
            FROM loadouts l
            JOIN base ON base.song_name = l.song_name AND base.base_peak = l.score
            """
        ):
            song = str(row["song_name"] or "")
            if peak_map.get(song, 0) != base_peak.get(song, 0):
                continue
            cand = parse_candidate_row(song, "loadouts", row)
            if cand is None:
                continue
            candidates_by_song.setdefault(song, []).append(cand)
    except sqlite3.Error:
        pass

    try:
        for row in conn.execute(
            """
            WITH fg AS (
                SELECT song_name, MAX(fg_score) AS fg_peak
                FROM fg_loadouts
                GROUP BY song_name
            )
            SELECT f.rowid AS rowid, f.song_name, f.score, f.fg_score, f.gear_json, f.minis_json, f.details_json, f.force_details_json
            FROM fg_loadouts f
            JOIN fg ON fg.song_name = f.song_name AND fg.fg_peak = f.fg_score
            """
        ):
            song = str(row["song_name"] or "")
            if peak_map.get(song, 0) != fg_peak.get(song, 0):
                continue
            cand = parse_candidate_row(song, "fg_loadouts", row)
            if cand is None:
                continue
            candidates_by_song.setdefault(song, []).append(cand)
    except sqlite3.Error:
        pass

    missing = [name for name in sorted(peak_map.keys()) if name not in candidates_by_song]

    for song_name, candidates in list(candidates_by_song.items()):
        dedup: Dict[Tuple[Any, ...], SongCandidate] = {}
        ordered = sorted(candidates, key=lambda c: (0 if c.source_table == "loadouts" else 1, c.rowid))
        for cand in ordered:
            key = (cand.gear_names, cand.mini_groups, cand.gem_totals, cand.selected_element)
            if key not in dedup:
                dedup[key] = cand
        candidates_by_song[song_name] = list(dedup.values())

    return candidates_by_song, missing


def parse_candidate_row(song_name: str, source_table: str, row: sqlite3.Row) -> Optional[SongCandidate]:
    try:
        try:
            rowid = int(row["rowid"] or 0)
        except Exception:
            rowid = 0
        if rowid <= 0:
            return None

        gear_names = _parse_gear_json(row["gear_json"])
        mini_groups = _parse_minis_json(row["minis_json"])
        if len(gear_names) != 6 or len(mini_groups) != 3:
            return None

        details = _parse_json(row["details_json"])
        gem_totals = _extract_gem_totals(details)
        if sum(gem_totals) != TOTAL_GEM_BUDGET:
            return None

        _, _, selected = extract_song_colors(details)
        selected = selected.strip()
        if not selected or selected not in ELEMENT_TO_ID:
            return None

        return SongCandidate(
            song_name=song_name,
            source_table=source_table,
            rowid=rowid,
            score=int(row["score"] or 0),
            fg_score=int(row["fg_score"] or 0),
            gear_names=gear_names,
            mini_groups=mini_groups,
            gem_totals=gem_totals,
            selected_element=selected,
        )
    except Exception:
        return None


def _parse_json(payload: Optional[str]) -> Dict[str, Any]:
    if not payload:
        return {}
    try:
        value = json.loads(payload)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _parse_gear_json(payload: Optional[str]) -> Tuple[str, ...]:
    if not payload:
        return tuple()
    try:
        gear = json.loads(payload)
    except Exception:
        return tuple()
    if not isinstance(gear, list):
        return tuple()
    names = [str(item).strip() for item in gear if item]
    if len(names) != 6 or any(not n for n in names):
        return tuple()
    return tuple(names)


def _parse_minis_json(payload: Optional[str]) -> Tuple[Tuple[str, ...], ...]:
    groups = decode_minis_json(payload)
    if len(groups) != 3:
        return tuple()
    normalized: List[Tuple[str, ...]] = []
    for group in groups:
        names = tuple(sorted({str(n).strip() for n in group if n}))
        if not names:
            return tuple()
        normalized.append(names)
    return tuple(normalized)


def _extract_gem_totals(details: Dict[str, Any]) -> Tuple[int, ...]:
    gem_counts = details.get("GemCounts", {}) if isinstance(details, dict) else {}
    if not isinstance(gem_counts, dict):
        gem_counts = {}

    def _get_gc(label: str, *alts: str) -> int:
        for key in (label,) + alts:
            if key in gem_counts:
                try:
                    return int(gem_counts.get(key) or 0)
                except Exception:
                    return 0
        return 0

    pp = _get_gc("Perfect Points", "PP")
    cm = _get_gc("Combo Multiplier", "CM")
    fm = _get_gc("Fever Multiplier", "FM")
    ov = _get_gc("Element", "OV", "Overflow")

    try:
        ft = int(details.get("FT") or gem_counts.get("Fever Time") or gem_counts.get("FT") or 0)
    except Exception:
        ft = 0
    try:
        ff = int(details.get("FF") or gem_counts.get("Fever Fill Rate") or gem_counts.get("FF") or 0)
    except Exception:
        ff = 0

    return (pp, cm, fm, ft, ff, ov)


__all__ = [
    "fetch_candidates_for_peak",
    "fetch_peak_candidates_allow_missing",
    "fetch_song_names",
    "fetch_song_names_limited",
    "fetch_song_peak",
]
