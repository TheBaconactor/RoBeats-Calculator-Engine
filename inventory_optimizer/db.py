from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from gear_optimizer.core.constants import TOTAL_GEM_BUDGET
from gear_optimizer.data.database import _unpack_id_groups, _unpack_id_list, _unpack_stats_after_load
from gear_optimizer.data.loadout_equivalence import extract_song_colors

from .keys import ELEMENT_TO_ID
from .models import SongCandidate

TEAM_BUFF_DEFAULT: str = "T5"
_BASELINE_TEAM_BUFF_BY_DB_PATH: Dict[str, str] = {}


def _conn_db_path(conn: sqlite3.Connection) -> str:
    """
    Best-effort: resolve the on-disk file path for this connection's main database.

    This is used only for lightweight process-local caching of the resolved baseline TeamBuff tier.
    """
    try:
        rows = conn.execute("PRAGMA database_list").fetchall()
    except sqlite3.Error:
        return ""

    for row in rows or []:
        try:
            name = row["name"] if isinstance(row, sqlite3.Row) else row[1]
            file = row["file"] if isinstance(row, sqlite3.Row) else row[2]
        except Exception:
            continue
        if str(name) == "main":
            return str(file or "")

    # Fall back to the first row's file if present.
    if rows:
        try:
            file = rows[0]["file"] if isinstance(rows[0], sqlite3.Row) else rows[0][2]
            return str(file or "")
        except Exception:
            return ""
    return ""


def _probe_first_team_buff(conn: sqlite3.Connection, table: str) -> Optional[str]:
    """
    Return a TeamBuff value present in `table`, or None if table is missing/empty.

    Compact DB mode persists baseline candidates under exactly one TeamBuff tier per DB in practice,
    so a single-row probe is sufficient and avoids scanning large tables.
    """
    try:
        row = conn.execute(
            f"SELECT team_buff FROM {table} WHERE team_buff IS NOT NULL AND team_buff != '' LIMIT 1"
        ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    try:
        v = row["team_buff"] if isinstance(row, sqlite3.Row) else row[0]
    except Exception:
        return None
    s = str(v or "").strip().upper()
    return s or None


def _resolve_baseline_team_buff(conn: sqlite3.Connection) -> str:
    """
    Resolve which baseline TeamBuff tier this DB is using for persisted candidates.

    This intentionally resolves from the DB contents (not config) so tools keep working when a DB
    created under a different baseline tier is inspected with a different local config.
    """
    db_path = _conn_db_path(conn)
    cached = _BASELINE_TEAM_BUFF_BY_DB_PATH.get(db_path) if db_path else None
    if cached:
        return cached

    # Prefer base table; then FG table.
    tb_base = _probe_first_team_buff(conn, "team_buff_loadouts")
    tb_fg = _probe_first_team_buff(conn, "team_buff_fg_loadouts")
    baseline = tb_base or tb_fg or TEAM_BUFF_DEFAULT

    # Only cache when we successfully observed a tier in the DB; if the DB is empty,
    # caching would make later inserts under a different baseline invisible.
    if db_path and (tb_base or tb_fg):
        _BASELINE_TEAM_BUFF_BY_DB_PATH[db_path] = str(baseline)
    return str(baseline)


class _EncodingMaps:
    __slots__ = ("gear_id_to_name", "mini_id_to_name")

    def __init__(self, *, gear_id_to_name: Dict[int, str], mini_id_to_name: Dict[int, str]):
        self.gear_id_to_name = gear_id_to_name
        self.mini_id_to_name = mini_id_to_name


def _load_encoding_maps(conn: sqlite3.Connection) -> _EncodingMaps:
    gear_id_to_name: Dict[int, str] = {}
    mini_id_to_name: Dict[int, str] = {}

    try:
        rows = conn.execute("SELECT id, name FROM gear_name_encoding").fetchall()
        for r in rows or []:
            try:
                i = int(r[0] or 0)
                n = str(r[1] or "").strip()
            except Exception:
                continue
            if i > 0 and n:
                gear_id_to_name[i] = n
    except sqlite3.Error:
        pass

    try:
        rows = conn.execute("SELECT id, name FROM mini_name_encoding").fetchall()
        for r in rows or []:
            try:
                i = int(r[0] or 0)
                n = str(r[1] or "").strip()
            except Exception:
                continue
            if i > 0 and n:
                mini_id_to_name[i] = n
    except sqlite3.Error:
        pass

    return _EncodingMaps(gear_id_to_name=gear_id_to_name, mini_id_to_name=mini_id_to_name)


def _decode_gear_names_blob(payload: object, maps: _EncodingMaps) -> Tuple[str, ...]:
    ids = _unpack_id_list(payload)
    names = [str(maps.gear_id_to_name.get(int(i), "") or "").strip() for i in ids if int(i) > 0]
    names = [n for n in names if n]
    return tuple(names)


def _decode_mini_groups_blob(payload: object, maps: _EncodingMaps) -> Tuple[Tuple[str, ...], ...]:
    id_groups = _unpack_id_groups(payload)
    out: List[Tuple[str, ...]] = []
    for g in id_groups or []:
        if not g:
            continue
        names = [str(maps.mini_id_to_name.get(int(i), "") or "").strip() for i in g if int(i) > 0]
        names = sorted({n for n in names if n})
        if names:
            out.append(tuple(names))
    return tuple(out)


def _resolve_tables(conn: sqlite3.Connection) -> Tuple[str, str, str]:
    """
    Choose which DB tables to treat as the base/FG leaderboards.

    Uses `team_buff_*` (filtered to the DB's baseline TeamBuff tier).
    """
    return "team_buff_loadouts", "team_buff_fg_loadouts", _resolve_baseline_team_buff(conn)


def _is_fg_table(name: str) -> bool:
    return str(name or "") == "team_buff_fg_loadouts"


def _is_base_table(name: str) -> bool:
    return str(name or "") == "team_buff_loadouts"


def fetch_song_names(conn: sqlite3.Connection) -> List[str]:
    names: set[str] = set()
    base_table, fg_table, team_buff = _resolve_tables(conn)
    for table in (base_table, fg_table):
        where = "WHERE team_buff = ?"
        params: Tuple[Any, ...] = (team_buff,)
        try:
            rows = conn.execute(f"SELECT DISTINCT song_name FROM {table} {where}", params).fetchall()
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
    base_table, fg_table, team_buff = _resolve_tables(conn)
    tb_filter_base = "WHERE team_buff = ?"
    tb_filter_fg = "WHERE team_buff = ?"
    params: List[Any] = [team_buff, team_buff]

    query = f"""
            SELECT song_name
            FROM (
                SELECT song_name FROM {base_table} {tb_filter_base}
                UNION
                SELECT song_name FROM {fg_table} {tb_filter_fg}
            )
            WHERE song_name IS NOT NULL AND song_name != ''
            ORDER BY song_name
            LIMIT ?
            """
    try:
        rows = conn.execute(query, tuple(params + [limit])).fetchall()
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
    base_table, fg_table, team_buff = _resolve_tables(conn)
    try:
        base_peak = conn.execute(
            f"SELECT MAX(score) FROM {base_table} WHERE song_name = ? AND team_buff = ?",
            (song_name, team_buff),
        ).fetchone()[0]
    except sqlite3.Error:
        base_peak = 0
    try:
        fg_peak = conn.execute(
            f"SELECT MAX(fg_score) FROM {fg_table} WHERE song_name = ? AND team_buff = ?",
            (song_name, team_buff),
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
    base_table, fg_table, team_buff = _resolve_tables(conn)
    candidates: List[SongCandidate] = []
    rows: List[Tuple[str, sqlite3.Row]] = []
    maps = _load_encoding_maps(conn)

    if peak == base_peak:
        try:
            cursor = conn.execute(
                f"""
                    SELECT rowid AS rowid, song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
                    FROM {base_table}
                    WHERE song_name = ? AND team_buff = ? AND score = ?
                    """,
                (song_name, team_buff, peak),
            )
            rows.extend([(base_table, row) for row in cursor])
        except sqlite3.Error:
            pass

    if peak == fg_peak:
        try:
            cursor = conn.execute(
                f"""
                    SELECT rowid AS rowid, song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
                    FROM {fg_table}
                    WHERE song_name = ? AND team_buff = ? AND fg_score = ?
                    """,
                (song_name, team_buff, peak),
            )
            rows.extend([(fg_table, row) for row in cursor])
        except sqlite3.Error:
            pass

    for source_table, row in rows:
        candidate = parse_candidate_row(song_name, source_table, row, maps)
        if candidate is not None:
            candidates.append(candidate)

    return candidates


def fetch_peak_candidates_allow_missing(conn: sqlite3.Connection) -> Tuple[Dict[str, List[SongCandidate]], List[str]]:
    candidates_by_song: Dict[str, List[SongCandidate]] = {}
    maps = _load_encoding_maps(conn)

    base_table, fg_table, team_buff = _resolve_tables(conn)
    peak_map: Dict[str, int] = {}
    base_peak: Dict[str, int] = {}
    fg_peak: Dict[str, int] = {}

    base_filter = "WHERE team_buff = ?"
    fg_filter = "WHERE team_buff = ?"
    params = [team_buff, team_buff, team_buff, team_buff]

    for row in conn.execute(
        f"""
        WITH base AS (
            SELECT song_name, MAX(score) AS base_peak
            FROM {base_table}
            {base_filter}
            GROUP BY song_name
        ),
        fg AS (
            SELECT song_name, MAX(fg_score) AS fg_peak
            FROM {fg_table}
            {fg_filter}
            GROUP BY song_name
        ),
        songs AS (
            SELECT song_name FROM {base_table}
            {base_filter}
            UNION
            SELECT song_name FROM {fg_table}
            {fg_filter}
        )
        SELECT
            songs.song_name AS song_name,
            COALESCE(base.base_peak, 0) AS base_peak,
            COALESCE(fg.fg_peak, 0) AS fg_peak
        FROM songs
        LEFT JOIN base ON base.song_name = songs.song_name
        LEFT JOIN fg ON fg.song_name = songs.song_name
        """,
        tuple(params),
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
            f"""
            WITH base AS (
                SELECT song_name, MAX(score) AS base_peak
                FROM {base_table}
                {base_filter}
                GROUP BY song_name
            )
            SELECT l.rowid AS rowid, l.song_name, l.score, l.fg_score, l.gear_ids_blob, l.minis_ids_blob, l.details_json, l.force_details_json
            FROM {base_table} l
            JOIN base ON base.song_name = l.song_name AND base.base_peak = l.score
            WHERE l.team_buff = ?
            """,
            (team_buff, team_buff),
        ):
            song = str(row["song_name"] or "")
            if peak_map.get(song, 0) != base_peak.get(song, 0):
                continue
            cand = parse_candidate_row(song, base_table, row, maps)
            if cand is None:
                continue
            candidates_by_song.setdefault(song, []).append(cand)
    except sqlite3.Error:
        pass

    try:
        for row in conn.execute(
            f"""
            WITH fg AS (
                SELECT song_name, MAX(fg_score) AS fg_peak
                FROM {fg_table}
                {fg_filter}
                GROUP BY song_name
            )
            SELECT f.rowid AS rowid, f.song_name, f.score, f.fg_score, f.gear_ids_blob, f.minis_ids_blob, f.details_json, f.force_details_json
            FROM {fg_table} f
            JOIN fg ON fg.song_name = f.song_name AND fg.fg_peak = f.fg_score
            WHERE f.team_buff = ?
            """,
            (team_buff, team_buff),
        ):
            song = str(row["song_name"] or "")
            if peak_map.get(song, 0) != fg_peak.get(song, 0):
                continue
            cand = parse_candidate_row(song, fg_table, row, maps)
            if cand is None:
                continue
            candidates_by_song.setdefault(song, []).append(cand)
    except sqlite3.Error:
        pass

    missing = [name for name in sorted(peak_map.keys()) if name not in candidates_by_song]

    for song_name, candidates in list(candidates_by_song.items()):
        dedup: Dict[Tuple[Any, ...], SongCandidate] = {}
        ordered = sorted(candidates, key=lambda c: (0 if _is_base_table(c.source_table) else 1, c.rowid))
        for cand in ordered:
            key = (cand.gear_names, cand.mini_groups, cand.gem_totals, cand.selected_element)
            if key not in dedup:
                dedup[key] = cand
        candidates_by_song[song_name] = list(dedup.values())

    return candidates_by_song, missing


def fetch_candidates_within_delta_allow_missing(
    conn: sqlite3.Connection,
    *,
    score_delta: int,
    limit_per_song: int,
) -> Tuple[Dict[str, List[SongCandidate]], List[str]]:
    """
    Fetch up to N candidates per song within `score_delta` of the *max(base_peak, fg_peak)*.

    Note: this relaxes "exact peak only" and is intended for approximate multi-candidate coverage experiments.
    """
    score_delta = int(score_delta)
    if score_delta < 0:
        raise ValueError("score_delta must be >= 0.")
    limit_per_song = int(limit_per_song)
    if limit_per_song <= 0:
        raise ValueError("limit_per_song must be positive.")

    base_table, fg_table, team_buff = _resolve_tables(conn)
    candidates_by_song: Dict[str, List[SongCandidate]] = {}
    maps = _load_encoding_maps(conn)

    peak_map: Dict[str, int] = {}
    base_peak: Dict[str, int] = {}
    fg_peak: Dict[str, int] = {}

    base_filter = "WHERE team_buff = ?"
    fg_filter = "WHERE team_buff = ?"
    params = [team_buff, team_buff, team_buff, team_buff]

    for row in conn.execute(
        f"""
        WITH base AS (
            SELECT song_name, MAX(score) AS base_peak
            FROM {base_table}
            {base_filter}
            GROUP BY song_name
        ),
        fg AS (
            SELECT song_name, MAX(fg_score) AS fg_peak
            FROM {fg_table}
            {fg_filter}
            GROUP BY song_name
        ),
        songs AS (
            SELECT song_name FROM {base_table}
            {base_filter}
            UNION
            SELECT song_name FROM {fg_table}
            {fg_filter}
        )
        SELECT
            songs.song_name AS song_name,
            COALESCE(base.base_peak, 0) AS base_peak,
            COALESCE(fg.fg_peak, 0) AS fg_peak
        FROM songs
        LEFT JOIN base ON base.song_name = songs.song_name
        LEFT JOIN fg ON fg.song_name = songs.song_name
        """,
        tuple(params),
    ):
        name = str(row["song_name"] or "")
        bp = int(row["base_peak"] or 0)
        fp = int(row["fg_peak"] or 0)
        base_peak[name] = bp
        fg_peak[name] = fp
        peak_map[name] = max(bp, fp)

    if not peak_map:
        return {}, []

    delta = int(score_delta)
    n = int(limit_per_song)

    try:
        peaks_params: List[Any] = [team_buff, team_buff, team_buff, team_buff, team_buff, delta, n]
        query = f"""
            WITH peaks AS (
                WITH base AS (
                    SELECT song_name, MAX(score) AS base_peak
                    FROM {base_table}
                    {base_filter}
                    GROUP BY song_name
                ),
                fg AS (
                    SELECT song_name, MAX(fg_score) AS fg_peak
                    FROM {fg_table}
                    {fg_filter}
                    GROUP BY song_name
                ),
                songs AS (
                    SELECT song_name FROM {base_table}
                    {base_filter}
                    UNION
                    SELECT song_name FROM {fg_table}
                    {fg_filter}
                )
                SELECT
                    songs.song_name AS song_name,
                    CASE
                        WHEN COALESCE(base.base_peak, 0) > COALESCE(fg.fg_peak, 0) THEN COALESCE(base.base_peak, 0)
                        ELSE COALESCE(fg.fg_peak, 0)
                    END AS peak
                FROM songs
                LEFT JOIN base ON base.song_name = songs.song_name
                LEFT JOIN fg ON fg.song_name = songs.song_name
            ),
            ranked AS (
                SELECT
                    l.rowid AS rowid,
                    l.song_name AS song_name,
                    l.score AS score,
                    l.fg_score AS fg_score,
                    l.gear_ids_blob AS gear_ids_blob,
                    l.minis_ids_blob AS minis_ids_blob,
                    l.details_json AS details_json,
                    l.force_details_json AS force_details_json,
                    ROW_NUMBER() OVER (PARTITION BY l.song_name ORDER BY l.score DESC, l.rowid ASC) AS rn
                FROM {base_table} l
                JOIN peaks p ON p.song_name = l.song_name
                WHERE l.team_buff = ? AND l.score >= (p.peak - ?)
            )
            SELECT rowid, song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
            FROM ranked
            WHERE rn <= ?
            """
        for row in conn.execute(query, tuple(peaks_params)):
            song = str(row["song_name"] or "")
            cand = parse_candidate_row(song, base_table, row, maps)
            if cand is None:
                continue
            candidates_by_song.setdefault(song, []).append(cand)
    except sqlite3.Error:
        pass

    try:
        peaks_params = [team_buff, team_buff, team_buff, team_buff, team_buff, delta, n]
        query = f"""
            WITH peaks AS (
                WITH base AS (
                    SELECT song_name, MAX(score) AS base_peak
                    FROM {base_table}
                    {base_filter}
                    GROUP BY song_name
                ),
                fg AS (
                    SELECT song_name, MAX(fg_score) AS fg_peak
                    FROM {fg_table}
                    {fg_filter}
                    GROUP BY song_name
                ),
                songs AS (
                    SELECT song_name FROM {base_table}
                    {base_filter}
                    UNION
                    SELECT song_name FROM {fg_table}
                    {fg_filter}
                )
                SELECT
                    songs.song_name AS song_name,
                    CASE
                        WHEN COALESCE(base.base_peak, 0) > COALESCE(fg.fg_peak, 0) THEN COALESCE(base.base_peak, 0)
                        ELSE COALESCE(fg.fg_peak, 0)
                    END AS peak
                FROM songs
                LEFT JOIN base ON base.song_name = songs.song_name
                LEFT JOIN fg ON fg.song_name = songs.song_name
            ),
            ranked AS (
                SELECT
                    f.rowid AS rowid,
                    f.song_name AS song_name,
                    f.score AS score,
                    f.fg_score AS fg_score,
                    f.gear_ids_blob AS gear_ids_blob,
                    f.minis_ids_blob AS minis_ids_blob,
                    f.details_json AS details_json,
                    f.force_details_json AS force_details_json,
                    ROW_NUMBER() OVER (PARTITION BY f.song_name ORDER BY f.fg_score DESC, f.rowid ASC) AS rn
                FROM {fg_table} f
                JOIN peaks p ON p.song_name = f.song_name
                WHERE f.team_buff = ? AND f.fg_score >= (p.peak - ?)
            )
            SELECT rowid, song_name, score, fg_score, gear_ids_blob, minis_ids_blob, details_json, force_details_json
            FROM ranked
            WHERE rn <= ?
            """
        for row in conn.execute(query, tuple(peaks_params)):
            song = str(row["song_name"] or "")
            cand = parse_candidate_row(song, fg_table, row, maps)
            if cand is None:
                continue
            candidates_by_song.setdefault(song, []).append(cand)
    except sqlite3.Error:
        pass

    missing = [name for name in sorted(peak_map.keys()) if name not in candidates_by_song]

    for song_name, candidates in list(candidates_by_song.items()):
        dedup: Dict[Tuple[Any, ...], SongCandidate] = {}

        # Highest score first for selection diversity; stable within table by rowid.
        def _metric(c: SongCandidate) -> int:
            return int(c.fg_score) if _is_fg_table(c.source_table) else int(c.score)

        ordered = sorted(candidates, key=lambda c: (-_metric(c), 0 if _is_base_table(c.source_table) else 1, c.rowid))
        for cand in ordered:
            key = (
                cand.gear_names,
                cand.mini_groups,
                cand.gem_totals,
                cand.selected_element,
                cand.source_table,
                _metric(cand),
            )
            if key not in dedup:
                dedup[key] = cand
        candidates_by_song[song_name] = list(dedup.values())

    return candidates_by_song, missing


def parse_candidate_row(
    song_name: str, source_table: str, row: sqlite3.Row, maps: _EncodingMaps
) -> Optional[SongCandidate]:
    try:
        try:
            rowid = int(row["rowid"] or 0)
        except Exception:
            rowid = 0
        if rowid <= 0:
            return None

        gear_names = _decode_gear_names_blob(row["gear_ids_blob"], maps)
        mini_groups = _decode_mini_groups_blob(row["minis_ids_blob"], maps)
        if len(gear_names) != 6 or len(mini_groups) != 3:
            return None

        details = _unpack_stats_after_load(_parse_json(row["details_json"]))
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
    "fetch_candidates_within_delta_allow_missing",
    "fetch_peak_candidates_allow_missing",
    "fetch_song_names",
    "fetch_song_names_limited",
    "fetch_song_peak",
]
