"""Analyze combo-ramp and fever-breakpoint signals against persisted FG rows.

This is an offline research helper. It does not alter production behavior and
does not submit GPU work. The goal is to see whether cheap ramp/breakpoint
features are useful for ranking, mutation pressure, or future upper-bound work.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from math import ceil
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.core.config import load_config
from gear_optimizer.core.constants import FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE, TOTAL_ROWS
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.database import _unpack_stats_after_load
from gear_optimizer.pipeline.song_processor import get_base_calc_song
from gear_optimizer.solver.scoring_core import lookup_reference_py


def _infer_difficulty(song_name: str) -> str:
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in str(song_name or ""):
            return diff
    return "Normal"


def _bucket_for_fg_rows(fg_rows: int) -> str:
    if fg_rows <= 0:
        return "zero"
    if fg_rows <= 3:
        return "tiny"
    if fg_rows <= 25:
        return "medium"
    return "rich"


def _load_details(raw: str | None) -> dict[str, Any]:
    try:
        obj = json.loads(raw) if raw else {}
    except Exception:
        obj = {}
    unpacked = _unpack_stats_after_load(obj)
    return unpacked if isinstance(unpacked, dict) else {}


def _timeline_summary(calc_song: dict[str, Any], ref_arrays: dict[str, Any], *, ft_stat: int, ff_stat: int) -> dict:
    metadata = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = np.asarray(song_data.get("fg_timestamps", song_data.get("timestamps", ())), dtype=np.float64)
    total_notes = int(len(timestamps))
    if total_notes <= 0:
        return {"starts": [], "body_fever": 0, "body_normal": 0, "nfb": 0, "signature": ()}

    long_notes = int(metadata.get("Long Notes", 0) or 0)
    last_note_time = float(metadata.get("Last Note Time", timestamps[-1]) or timestamps[-1])
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32)
    ft_factor = float(lookup_reference_py(int(ft_stat), ref_ft, TOTAL_ROWS))
    ff_factor = float(lookup_reference_py(int(ff_stat), ref_ff, TOTAL_ROWS))

    raw_fill = max(0.0, float(total_notes - long_notes) * FEVER_FILL_BASE_RATE * ff_factor)
    non_fever_base = int(ceil(raw_fill))
    fever_duration = ((last_note_time * FEVER_TIME_SCALE) + FEVER_TIME_OFFSET) * ft_factor

    starts: list[int] = []
    is_fever = np.zeros(total_notes, dtype=np.bool_)
    idx = 0
    section = 0
    while idx < total_notes:
        section += 1
        notes_to_fill = non_fever_base - 1 if section == 1 else non_fever_base
        if notes_to_fill < 0:
            notes_to_fill = 0
        idx = min(total_notes, idx + notes_to_fill)
        if idx >= total_notes:
            break
        starts.append(int(idx))
        fever_end = float(timestamps[idx]) + float(fever_duration)
        end_idx = int(np.searchsorted(timestamps, fever_end, side="left"))
        if end_idx <= idx:
            end_idx = min(total_notes, idx + 1)
        is_fever[idx:end_idx] = True
        idx = end_idx

    head_fever = int(is_fever[: min(100, total_notes)].sum())
    body_fever = int(is_fever[100:].sum()) if total_notes > 100 else 0
    body_normal = int(max(0, total_notes - 100 - body_fever))
    head_mask = tuple(int(i) for i in np.flatnonzero(is_fever[: min(100, total_notes)]))
    signature = (tuple(starts[:8]), int(body_fever), int(body_normal), head_mask)
    return {
        "starts": starts,
        "head_fever": head_fever,
        "body_fever": body_fever,
        "total_fever": int(head_fever + body_fever),
        "body_normal": body_normal,
        "nfb": non_fever_base,
        "signature": signature,
    }


def _nearest_timeline_breakpoint(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    ft_stat: int,
    ff_stat: int,
    axis: str,
    max_delta: int,
) -> int | None:
    base = _timeline_summary(calc_song, ref_arrays, ft_stat=ft_stat, ff_stat=ff_stat)["signature"]
    for delta in range(1, max(1, int(max_delta)) + 1):
        if axis == "ft":
            ft_next = min(TOTAL_ROWS, int(ft_stat) + delta)
            ff_next = int(ff_stat)
        else:
            ft_next = int(ft_stat)
            ff_next = min(TOTAL_ROWS, int(ff_stat) + delta)
        sig = _timeline_summary(calc_song, ref_arrays, ft_stat=ft_next, ff_stat=ff_next)["signature"]
        if sig != base:
            return int(delta)
    return None


def _starts_cross_ramp_boundary(base_starts: list[int], next_starts: list[int]) -> bool:
    max_len = max(len(base_starts), len(next_starts))
    for idx in range(max_len):
        base = int(base_starts[idx]) if idx < len(base_starts) else 10**9
        nxt = int(next_starts[idx]) if idx < len(next_starts) else 10**9
        if (base < 100) != (nxt < 100):
            return True
    return False


def _valuable_delta(base: dict[str, Any], nxt: dict[str, Any]) -> bool:
    if int(base["total_fever"]) != int(nxt["total_fever"]):
        return True
    if int(base["head_fever"]) != int(nxt["head_fever"]):
        return True
    if int(base["body_fever"]) != int(nxt["body_fever"]):
        return True
    return _starts_cross_ramp_boundary(list(base["starts"]), list(nxt["starts"]))


def _valuable_score_delta(base: dict[str, Any], nxt: dict[str, Any]) -> int:
    total_delta = abs(int(nxt["total_fever"]) - int(base["total_fever"]))
    head_delta = abs(int(nxt["head_fever"]) - int(base["head_fever"]))
    body_delta = abs(int(nxt["body_fever"]) - int(base["body_fever"]))
    ramp_cross = 1 if _starts_cross_ramp_boundary(list(base["starts"]), list(nxt["starts"])) else 0
    # Head/ramp changes are more informative for combo-ramp identity; body-count
    # changes capture density/timeline-count effects like extended maps.
    return int((head_delta * 4) + (ramp_cross * 3) + (total_delta * 2) + body_delta)


def _nearest_valuable_breakpoint(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    ft_stat: int,
    ff_stat: int,
    axis: str,
    max_delta: int,
) -> tuple[int | None, int]:
    base = _timeline_summary(calc_song, ref_arrays, ft_stat=ft_stat, ff_stat=ff_stat)
    best_score = 0
    for delta in range(1, max(1, int(max_delta)) + 1):
        if axis == "ft":
            ft_next = min(TOTAL_ROWS, int(ft_stat) + delta)
            ff_next = int(ff_stat)
        else:
            ft_next = int(ft_stat)
            ff_next = min(TOTAL_ROWS, int(ff_stat) + delta)
        nxt = _timeline_summary(calc_song, ref_arrays, ft_stat=ft_next, ff_stat=ff_next)
        score = _valuable_score_delta(base, nxt)
        if score > best_score:
            best_score = int(score)
        if _valuable_delta(base, nxt):
            return int(delta), int(score)
    return None, int(best_score)


def _stat_int(stats: dict[str, Any], key: str) -> int:
    try:
        return int(stats.get(key, 0) or 0)
    except Exception:
        return 0


def _selected_colors(details: dict[str, Any], calc_song: dict[str, Any]) -> tuple[str, str]:
    metadata = calc_song.get("metadata", {}) or {}
    primary = (
        details.get("PrimaryColor")
        or details.get("Primary Color")
        or details.get("pc")
        or metadata.get("Primary Color")
        or ""
    )
    secondary = (
        details.get("SecondaryColor")
        or details.get("Secondary Color")
        or details.get("sc")
        or metadata.get("Secondary Color")
        or ""
    )
    return str(primary or ""), str(secondary or "")


def _base_value(stats: dict[str, Any], ref_arrays: dict[str, Any], primary: str, secondary: str, pp_stat: int) -> float:
    ref_pp = np.asarray(ref_arrays["Perfect Points"], dtype=np.float32)
    p_val = _stat_int(stats, primary) if primary else 0
    s_val = _stat_int(stats, secondary) if secondary else 0
    pp_bonus = float(lookup_reference_py(int(pp_stat), ref_pp, TOTAL_ROWS))
    return float((p_val * 2) + s_val) + pp_bonus


def _nearest_score_floor_breakpoint(
    stats: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    primary: str,
    secondary: str,
    axis: str,
    max_delta: int,
) -> tuple[int | None, int]:
    ref_cm = np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32)
    ref_fm = np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32)
    pp0 = _stat_int(stats, "Perfect Points")
    cm0 = _stat_int(stats, "Combo Multiplier")
    fm0 = _stat_int(stats, "Fever Multiplier")
    base0 = _base_value(stats, ref_arrays, primary, secondary, pp0)
    cm_mul0 = float(lookup_reference_py(cm0, ref_cm, TOTAL_ROWS))
    fm_mul0 = float(lookup_reference_py(fm0, ref_fm, TOTAL_ROWS))
    combo0 = int(np.float32(base0) * np.float32(cm_mul0))
    fever0 = int(np.float32(base0) * np.float32(cm_mul0) * np.float32(fm_mul0))

    best_score = 0
    for delta in range(1, max(1, int(max_delta)) + 1):
        pp = pp0
        cm = cm0
        fm = fm0
        if axis == "pp":
            pp = min(TOTAL_ROWS, pp0 + delta)
        elif axis == "cm":
            cm = min(TOTAL_ROWS, cm0 + delta)
        elif axis == "fm":
            fm = min(TOTAL_ROWS, fm0 + delta)
        else:
            return None, 0
        base = _base_value(stats, ref_arrays, primary, secondary, pp)
        cm_mul = float(lookup_reference_py(cm, ref_cm, TOTAL_ROWS))
        fm_mul = float(lookup_reference_py(fm, ref_fm, TOTAL_ROWS))
        combo = int(np.float32(base) * np.float32(cm_mul))
        fever = int(np.float32(base) * np.float32(cm_mul) * np.float32(fm_mul))
        score = abs(combo - combo0) + abs(fever - fever0)
        if score > best_score:
            best_score = int(score)
        if combo != combo0 or fever != fever0:
            return int(delta), int(score)
    return None, int(best_score)


def _score_floor_values(
    stats: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    primary: str,
    secondary: str,
    pp_stat: int | None = None,
    cm_stat: int | None = None,
    fm_stat: int | None = None,
) -> tuple[int, int]:
    ref_cm = np.asarray(ref_arrays["Combo Multiplier"], dtype=np.float32)
    ref_fm = np.asarray(ref_arrays["Fever Multiplier"], dtype=np.float32)
    pp = _stat_int(stats, "Perfect Points") if pp_stat is None else int(pp_stat)
    cm = _stat_int(stats, "Combo Multiplier") if cm_stat is None else int(cm_stat)
    fm = _stat_int(stats, "Fever Multiplier") if fm_stat is None else int(fm_stat)
    base = _base_value(stats, ref_arrays, primary, secondary, pp)
    cm_mul = float(lookup_reference_py(cm, ref_cm, TOTAL_ROWS))
    fm_mul = float(lookup_reference_py(fm, ref_fm, TOTAL_ROWS))
    combo = int(np.float32(base) * np.float32(cm_mul))
    fever = int(np.float32(base) * np.float32(cm_mul) * np.float32(fm_mul))
    return combo, fever


def _best_score_floor_marginal(
    stats: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    primary: str,
    secondary: str,
    timeline: dict[str, Any],
    axis: str,
    max_delta: int,
) -> dict[str, Any]:
    pp0 = _stat_int(stats, "Perfect Points")
    cm0 = _stat_int(stats, "Combo Multiplier")
    fm0 = _stat_int(stats, "Fever Multiplier")
    combo0, fever0 = _score_floor_values(stats, ref_arrays, primary=primary, secondary=secondary)
    fever_notes = int(timeline["total_fever"])
    normal_notes = int(timeline["body_normal"]) + max(0, 100 - int(timeline["head_fever"]))
    best = {"delta": None, "weighted": 0, "efficiency": 0.0}
    for delta in range(1, max(1, int(max_delta)) + 1):
        pp = pp0
        cm = cm0
        fm = fm0
        if axis == "pp":
            pp = min(TOTAL_ROWS, pp0 + delta)
        elif axis == "cm":
            cm = min(TOTAL_ROWS, cm0 + delta)
        elif axis == "fm":
            fm = min(TOTAL_ROWS, fm0 + delta)
        else:
            return best
        combo, fever = _score_floor_values(
            stats,
            ref_arrays,
            primary=primary,
            secondary=secondary,
            pp_stat=pp,
            cm_stat=cm,
            fm_stat=fm,
        )
        weighted = ((combo - combo0) * normal_notes) + ((fever - fever0) * fever_notes)
        efficiency = float(weighted) / float(delta)
        if efficiency > float(best["efficiency"]):
            best = {"delta": int(delta), "weighted": int(weighted), "efficiency": round(efficiency, 3)}
    return best


def _best_timeline_marginal(
    calc_song: dict[str, Any],
    ref_arrays: dict[str, Any],
    *,
    ft_stat: int,
    ff_stat: int,
    stats: dict[str, Any],
    primary: str,
    secondary: str,
    axis: str,
    max_delta: int,
) -> dict[str, Any]:
    base = _timeline_summary(calc_song, ref_arrays, ft_stat=ft_stat, ff_stat=ff_stat)
    combo0, fever0 = _score_floor_values(stats, ref_arrays, primary=primary, secondary=secondary)
    fever_premium = max(0, int(fever0) - int(combo0))
    best = {"delta": None, "weighted": 0, "efficiency": 0.0}
    for delta in range(1, max(1, int(max_delta)) + 1):
        if axis == "ft":
            ft_next = min(TOTAL_ROWS, int(ft_stat) + delta)
            ff_next = int(ff_stat)
        elif axis == "ff":
            ft_next = int(ft_stat)
            ff_next = min(TOTAL_ROWS, int(ff_stat) + delta)
        else:
            return best
        nxt = _timeline_summary(calc_song, ref_arrays, ft_stat=ft_next, ff_stat=ff_next)
        head_delta = int(nxt["head_fever"]) - int(base["head_fever"])
        body_delta = int(nxt["body_fever"]) - int(base["body_fever"])
        ramp_bonus = 0
        if _starts_cross_ramp_boundary(list(base["starts"]), list(nxt["starts"])):
            ramp_bonus = fever_premium * 3
        weighted = ((head_delta * 2) + body_delta) * fever_premium + ramp_bonus
        efficiency = float(weighted) / float(delta)
        if efficiency > float(best["efficiency"]):
            best = {"delta": int(delta), "weighted": int(weighted), "efficiency": round(efficiency, 3)}
    return best


def _best_marginal(row: dict[str, Any]) -> float:
    return max(
        float(row["marginal_ft_eff"]),
        float(row["marginal_ff_eff"]),
        float(row["marginal_pp_eff"]),
        float(row["marginal_cm_eff"]),
        float(row["marginal_fm_eff"]),
    )


def _timeline_marginal(row: dict[str, Any]) -> float:
    return max(float(row["marginal_ft_eff"]), float(row["marginal_ff_eff"]))


def _score_floor_marginal(row: dict[str, Any]) -> float:
    return max(float(row["marginal_pp_eff"]), float(row["marginal_cm_eff"]), float(row["marginal_fm_eff"]))


def _capture_at(records: list[dict[str, Any]], *, fraction: float, scorer: Any = _best_marginal) -> dict[str, Any]:
    if not records:
        return {"rows": 0, "fg_improves": 0, "fg_overall": 0, "avg_fg_lift": 0}
    take = max(1, int(round(len(records) * float(fraction))))
    ranked = sorted(records, key=scorer, reverse=True)[:take]
    return {
        "rows": len(ranked),
        "fg_improves": sum(1 for r in ranked if int(r["fg_lift"]) > 0),
        "fg_overall": sum(1 for r in ranked if bool(r["fg_overall"])),
        "avg_fg_lift": round(mean([r["fg_lift"] for r in ranked]), 3),
        "min_best_efficiency": round(min(scorer(r) for r in ranked), 3),
    }


def _summarize_group(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {"count": 0}
    fg_improves = [r for r in records if r["fg_lift"] > 0]
    fg_overall = [r for r in records if r["fg_overall"]]
    with_head = [r for r in records if r["ramp_starts"] > 0]
    near_bp = [r for r in records if min(r["nearest_ft"] or 999, r["nearest_ff"] or 999) <= 6]
    near_valuable = [r for r in records if min(r["valuable_ft"] or 999, r["valuable_ff"] or 999) <= 6]
    valuable_any = [r for r in records if max(r["valuable_ft_score"], r["valuable_ff_score"]) > 0]
    score_bp_any = [
        r for r in records if min(r["score_bp_pp"] or 999, r["score_bp_cm"] or 999, r["score_bp_fm"] or 999) <= 6
    ]
    marginal_rows = [r for r in records if _best_marginal(r) > 0]
    return {
        "count": len(records),
        "fg_improves": len(fg_improves),
        "fg_overall": len(fg_overall),
        "ramp_start_rows": len(with_head),
        "near_timeline_bp_rows": len(near_bp),
        "near_valuable_bp_rows": len(near_valuable),
        "valuable_any_rows": len(valuable_any),
        "near_score_floor_bp_rows": len(score_bp_any),
        "positive_marginal_rows": len(marginal_rows),
        "avg_fg_lift": round(mean([r["fg_lift"] for r in records]), 3),
        "avg_fg_lift_ramp": round(mean([r["fg_lift"] for r in with_head]), 3) if with_head else 0,
        "avg_fg_lift_near_bp": round(mean([r["fg_lift"] for r in near_bp]), 3) if near_bp else 0,
        "avg_fg_lift_near_valuable": round(mean([r["fg_lift"] for r in near_valuable]), 3) if near_valuable else 0,
        "avg_fg_lift_near_score_floor": round(mean([r["fg_lift"] for r in score_bp_any]), 3) if score_bp_any else 0,
        "top_10pct_marginal": _capture_at(records, fraction=0.10),
        "top_25pct_marginal": _capture_at(records, fraction=0.25),
        "top_10pct_timeline": _capture_at(records, fraction=0.10, scorer=_timeline_marginal),
        "top_25pct_timeline": _capture_at(records, fraction=0.25, scorer=_timeline_marginal),
        "top_10pct_score_floor": _capture_at(records, fraction=0.10, scorer=_score_floor_marginal),
        "top_25pct_score_floor": _capture_at(records, fraction=0.25, scorer=_score_floor_marginal),
    }


class Analyzer:
    def __init__(self, *, db_path: Path, team_buff: str, max_delta: int) -> None:
        self.db_path = db_path
        self.team_buff = str(team_buff or "T5").strip().upper()
        self.max_delta = int(max_delta)
        self.cfg = cfg_to_dict(load_config())
        self.ref_arrays = _get_team_buff_ref_arrays_cached()
        self.calc_cache: dict[str, dict[str, Any] | None] = {}

    def calc_song_for(self, song_name: str) -> dict[str, Any] | None:
        if song_name in self.calc_cache:
            return self.calc_cache[song_name]
        path = PROJECT_ROOT / "Data" / _infer_difficulty(song_name) / f"{song_name}.txt"
        if not path.exists():
            self.calc_cache[song_name] = None
            return None
        self.calc_cache[song_name] = get_base_calc_song(str(path), self.cfg)
        return self.calc_cache[song_name]

    def select_songs(self, conn: sqlite3.Connection, *, songs: list[str], per_bucket: int) -> list[str]:
        if songs:
            return songs
        out: list[str] = []
        bucket_filters = (
            "fg_rows = 0",
            "fg_rows BETWEEN 1 AND 3",
            "fg_rows BETWEEN 4 AND 25",
            "fg_rows >= 26",
        )
        for where_sql in bucket_filters:
            rows = conn.execute(
                f"""
                WITH c AS (
                    SELECT s.name,
                           (
                               SELECT COUNT(*)
                               FROM team_buff_fg_loadouts f
                               WHERE f.song_name = s.name
                                 AND UPPER(COALESCE(f.team_buff, '')) = ?
                           ) AS fg_rows
                    FROM songs s
                    WHERE EXISTS (
                        SELECT 1
                        FROM team_buff_loadouts b
                        WHERE b.song_name = s.name
                          AND UPPER(COALESCE(b.team_buff, '')) = ?
                    )
                )
                SELECT name FROM c WHERE {where_sql} ORDER BY name LIMIT ?
                """,
                (self.team_buff, self.team_buff, int(per_bucket)),
            ).fetchall()
            out.extend(str(r["name"]) for r in rows)
        return out

    def analyze(
        self,
        *,
        songs: list[str],
        per_bucket: int,
        max_rows_per_song: int,
        include_records: bool = False,
    ) -> dict[str, Any]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        start = time.perf_counter()
        records: list[dict[str, Any]] = []
        try:
            selected_songs = self.select_songs(conn, songs=songs, per_bucket=per_bucket)
            for song_name in selected_songs:
                calc_song = self.calc_song_for(song_name)
                if calc_song is None:
                    continue
                song_row = conn.execute(
                    "SELECT best_score, best_fg_score FROM songs WHERE name = ?",
                    (song_name,),
                ).fetchone()
                if song_row is None:
                    continue
                fg_rows = int(
                    conn.execute(
                        """
                        SELECT COUNT(*)
                        FROM team_buff_fg_loadouts
                        WHERE song_name = ?
                          AND UPPER(COALESCE(team_buff, '')) = ?
                        """,
                        (song_name, self.team_buff),
                    ).fetchone()[0]
                    or 0
                )
                rows = conn.execute(
                    """
                    SELECT score, fg_score, details_json
                    FROM team_buff_loadouts
                    WHERE song_name = ?
                      AND UPPER(COALESCE(team_buff, '')) = ?
                    ORDER BY score DESC
                    LIMIT ?
                    """,
                    (song_name, self.team_buff, int(max_rows_per_song)),
                ).fetchall()
                for rank, row in enumerate(rows, 1):
                    details = _load_details(row["details_json"])
                    stats = dict(details.get("Stats") or {})
                    if not stats:
                        continue
                    primary_color, secondary_color = _selected_colors(details, calc_song)
                    ft_stat = int(stats.get("Fever Time", 0) or 0)
                    ff_stat = int(stats.get("Fever Fill Rate", 0) or 0)
                    summary = _timeline_summary(calc_song, self.ref_arrays, ft_stat=ft_stat, ff_stat=ff_stat)
                    starts = list(summary["starts"])
                    nearest_ft = _nearest_timeline_breakpoint(
                        calc_song,
                        self.ref_arrays,
                        ft_stat=ft_stat,
                        ff_stat=ff_stat,
                        axis="ft",
                        max_delta=self.max_delta,
                    )
                    nearest_ff = _nearest_timeline_breakpoint(
                        calc_song,
                        self.ref_arrays,
                        ft_stat=ft_stat,
                        ff_stat=ff_stat,
                        axis="ff",
                        max_delta=self.max_delta,
                    )
                    valuable_ft, valuable_ft_score = _nearest_valuable_breakpoint(
                        calc_song,
                        self.ref_arrays,
                        ft_stat=ft_stat,
                        ff_stat=ff_stat,
                        axis="ft",
                        max_delta=self.max_delta,
                    )
                    valuable_ff, valuable_ff_score = _nearest_valuable_breakpoint(
                        calc_song,
                        self.ref_arrays,
                        ft_stat=ft_stat,
                        ff_stat=ff_stat,
                        axis="ff",
                        max_delta=self.max_delta,
                    )
                    score_bp_pp, score_bp_pp_score = _nearest_score_floor_breakpoint(
                        stats,
                        self.ref_arrays,
                        primary=primary_color,
                        secondary=secondary_color,
                        axis="pp",
                        max_delta=self.max_delta,
                    )
                    score_bp_cm, score_bp_cm_score = _nearest_score_floor_breakpoint(
                        stats,
                        self.ref_arrays,
                        primary=primary_color,
                        secondary=secondary_color,
                        axis="cm",
                        max_delta=self.max_delta,
                    )
                    score_bp_fm, score_bp_fm_score = _nearest_score_floor_breakpoint(
                        stats,
                        self.ref_arrays,
                        primary=primary_color,
                        secondary=secondary_color,
                        axis="fm",
                        max_delta=self.max_delta,
                    )
                    marginal_ft = _best_timeline_marginal(
                        calc_song,
                        self.ref_arrays,
                        ft_stat=ft_stat,
                        ff_stat=ff_stat,
                        stats=stats,
                        primary=primary_color,
                        secondary=secondary_color,
                        axis="ft",
                        max_delta=self.max_delta,
                    )
                    marginal_ff = _best_timeline_marginal(
                        calc_song,
                        self.ref_arrays,
                        ft_stat=ft_stat,
                        ff_stat=ff_stat,
                        stats=stats,
                        primary=primary_color,
                        secondary=secondary_color,
                        axis="ff",
                        max_delta=self.max_delta,
                    )
                    marginal_pp = _best_score_floor_marginal(
                        stats,
                        self.ref_arrays,
                        primary=primary_color,
                        secondary=secondary_color,
                        timeline=summary,
                        axis="pp",
                        max_delta=self.max_delta,
                    )
                    marginal_cm = _best_score_floor_marginal(
                        stats,
                        self.ref_arrays,
                        primary=primary_color,
                        secondary=secondary_color,
                        timeline=summary,
                        axis="cm",
                        max_delta=self.max_delta,
                    )
                    marginal_fm = _best_score_floor_marginal(
                        stats,
                        self.ref_arrays,
                        primary=primary_color,
                        secondary=secondary_color,
                        timeline=summary,
                        axis="fm",
                        max_delta=self.max_delta,
                    )
                    score = int(row["score"] or 0)
                    fg_score = int(row["fg_score"] or 0)
                    records.append(
                        {
                            "song": song_name,
                            "bucket": _bucket_for_fg_rows(fg_rows),
                            "rank": int(rank),
                            "score": score,
                            "fg_score": fg_score,
                            "fg_lift": int(fg_score - score) if fg_score > 0 else 0,
                            "fg_overall": bool(fg_score > int(song_row["best_score"] or 0)),
                            "base_deficit": int(song_row["best_score"] or 0) - score,
                            "fg_rows": fg_rows,
                            "starts": starts[:5],
                            "first_start": int(starts[0]) if starts else None,
                            "ramp_starts": sum(1 for s in starts if int(s) < 100),
                            "nfb": int(summary["nfb"]),
                            "nearest_ft": nearest_ft,
                            "nearest_ff": nearest_ff,
                            "valuable_ft": valuable_ft,
                            "valuable_ff": valuable_ff,
                            "valuable_ft_score": int(valuable_ft_score),
                            "valuable_ff_score": int(valuable_ff_score),
                            "score_bp_pp": score_bp_pp,
                            "score_bp_cm": score_bp_cm,
                            "score_bp_fm": score_bp_fm,
                            "score_bp_pp_score": int(score_bp_pp_score),
                            "score_bp_cm_score": int(score_bp_cm_score),
                            "score_bp_fm_score": int(score_bp_fm_score),
                            "marginal_ft_delta": marginal_ft["delta"],
                            "marginal_ff_delta": marginal_ff["delta"],
                            "marginal_pp_delta": marginal_pp["delta"],
                            "marginal_cm_delta": marginal_cm["delta"],
                            "marginal_fm_delta": marginal_fm["delta"],
                            "marginal_ft_weighted": int(marginal_ft["weighted"]),
                            "marginal_ff_weighted": int(marginal_ff["weighted"]),
                            "marginal_pp_weighted": int(marginal_pp["weighted"]),
                            "marginal_cm_weighted": int(marginal_cm["weighted"]),
                            "marginal_fm_weighted": int(marginal_fm["weighted"]),
                            "marginal_ft_eff": float(marginal_ft["efficiency"]),
                            "marginal_ff_eff": float(marginal_ff["efficiency"]),
                            "marginal_pp_eff": float(marginal_pp["efficiency"]),
                            "marginal_cm_eff": float(marginal_cm["efficiency"]),
                            "marginal_fm_eff": float(marginal_fm["efficiency"]),
                        }
                    )
        finally:
            conn.close()

        by_bucket = {
            bucket: _summarize_group([r for r in records if r["bucket"] == bucket])
            for bucket in ("zero", "tiny", "medium", "rich")
        }
        top_positive = sorted(records, key=lambda r: int(r["fg_lift"]), reverse=True)[:10]
        top_breakpoint = sorted(
            records,
            key=lambda r: (
                min(int(r["nearest_ft"] or 999), int(r["nearest_ff"] or 999)),
                -int(r["fg_lift"]),
            ),
        )[:10]
        top_valuable = sorted(
            records,
            key=lambda r: (
                min(int(r["valuable_ft"] or 999), int(r["valuable_ff"] or 999)),
                -max(int(r["valuable_ft_score"]), int(r["valuable_ff_score"])),
                -int(r["fg_lift"]),
            ),
        )[:10]
        top_score_floor = sorted(
            records,
            key=lambda r: (
                min(int(r["score_bp_pp"] or 999), int(r["score_bp_cm"] or 999), int(r["score_bp_fm"] or 999)),
                -max(int(r["score_bp_pp_score"]), int(r["score_bp_cm_score"]), int(r["score_bp_fm_score"])),
                -int(r["fg_lift"]),
            ),
        )[:10]
        top_marginal = sorted(records, key=_best_marginal, reverse=True)[:10]
        report = {
            "db": str(self.db_path),
            "team_buff": self.team_buff,
            "max_delta": self.max_delta,
            "records": len(records),
            "songs_cached": len([v for v in self.calc_cache.values() if v is not None]),
            "elapsed_sec": round(time.perf_counter() - start, 3),
            "by_bucket": by_bucket,
            "top_positive_lift": top_positive,
            "nearest_breakpoint_examples": top_breakpoint,
            "nearest_valuable_examples": top_valuable,
            "nearest_score_floor_examples": top_score_floor,
            "top_marginal_examples": top_marginal,
        }
        if include_records:
            report["records"] = records
        return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze combo-ramp and timeline-breakpoint FG signals.")
    parser.add_argument("--db", default=str(PROJECT_ROOT / "evolution.db"))
    parser.add_argument("--team-buff", default="T5")
    parser.add_argument("--song", action="append", default=[], help="Specific song name; can be repeated.")
    parser.add_argument("--per-bucket", type=int, default=10)
    parser.add_argument("--max-rows-per-song", type=int, default=20)
    parser.add_argument("--max-delta", type=int, default=30)
    parser.add_argument("--include-records", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    analyzer = Analyzer(db_path=Path(args.db), team_buff=args.team_buff, max_delta=int(args.max_delta))
    report = analyzer.analyze(
        songs=list(args.song or []),
        per_bucket=max(1, int(args.per_bucket)),
        max_rows_per_song=max(1, int(args.max_rows_per_song)),
        include_records=bool(args.include_records),
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    print("=" * 78)
    print("Combo Ramp / Breakpoint Signal Analysis")
    print("=" * 78)
    print(f"DB: {report['db']}  TeamBuff: {report['team_buff']}")
    print(f"Checked {report['records']:,} rows across {report['songs_cached']:,} songs in {report['elapsed_sec']}s")
    print()
    for bucket, stats in report["by_bucket"].items():
        print(
            f"{bucket:<6} count={stats.get('count', 0):<5} "
            f"fg_improves={stats.get('fg_improves', 0):<5} "
            f"fg_overall={stats.get('fg_overall', 0):<5} "
            f"ramp_rows={stats.get('ramp_start_rows', 0):<5} "
            f"near_bp={stats.get('near_timeline_bp_rows', 0):<5} "
            f"near_value={stats.get('near_valuable_bp_rows', 0):<5} "
            f"score_floor={stats.get('near_score_floor_bp_rows', 0):<5} "
            f"marginal={stats.get('positive_marginal_rows', 0):<5} "
            f"avg_lift={stats.get('avg_fg_lift', 0)}"
        )
        top10 = stats.get("top_10pct_marginal", {})
        top25 = stats.get("top_25pct_marginal", {})
        print(
            f"       top10% marginal: rows={top10.get('rows', 0):<4} "
            f"fg+={top10.get('fg_improves', 0):<4} overall={top10.get('fg_overall', 0):<3} "
            f"avg_lift={top10.get('avg_fg_lift', 0):<10} "
            f"top25% fg+={top25.get('fg_improves', 0):<4} overall={top25.get('fg_overall', 0):<3} "
            f"avg_lift={top25.get('avg_fg_lift', 0)}"
        )
        timeline10 = stats.get("top_10pct_timeline", {})
        floor10 = stats.get("top_10pct_score_floor", {})
        print(
            f"       top10% timeline: fg+={timeline10.get('fg_improves', 0):<4} "
            f"overall={timeline10.get('fg_overall', 0):<3} avg_lift={timeline10.get('avg_fg_lift', 0):<10} "
            f"top10% floors: fg+={floor10.get('fg_improves', 0):<4} "
            f"overall={floor10.get('fg_overall', 0):<3} avg_lift={floor10.get('avg_fg_lift', 0)}"
        )
    print("\nTop positive-lift rows:")
    for row in report["top_positive_lift"][:8]:
        print(
            f"  lift={row['fg_lift']:<9} def={row['base_deficit']:<8} "
            f"starts={row['starts']} bp=({row['nearest_ft']},{row['nearest_ff']}) "
            f"vbp=({row['valuable_ft']},{row['valuable_ff']}) {row['song'][:56]}"
        )
    print("\nNearest valuable-breakpoint rows:")
    for row in report["nearest_valuable_examples"][:8]:
        print(
            f"  vbp=({row['valuable_ft']},{row['valuable_ff']}) "
            f"vscore=({row['valuable_ft_score']},{row['valuable_ff_score']}) "
            f"lift={row['fg_lift']:<8} starts={row['starts']} {row['song'][:56]}"
        )
    print("\nNearest score-floor rows:")
    for row in report["nearest_score_floor_examples"][:8]:
        print(
            f"  sbp=({row['score_bp_pp']},{row['score_bp_cm']},{row['score_bp_fm']}) "
            f"sscore=({row['score_bp_pp_score']},{row['score_bp_cm_score']},{row['score_bp_fm_score']}) "
            f"lift={row['fg_lift']:<8} {row['song'][:56]}"
        )
    print("\nTop weighted-marginal rows:")
    for row in report["top_marginal_examples"][:8]:
        best_eff = _best_marginal(row)
        print(
            f"  eff={best_eff:<11} lift={row['fg_lift']:<8} "
            f"t=({row['marginal_ft_eff']},{row['marginal_ff_eff']}) "
            f"s=({row['marginal_pp_eff']},{row['marginal_cm_eff']},{row['marginal_fm_eff']}) "
            f"{row['song'][:56]}"
        )


if __name__ == "__main__":
    main()
