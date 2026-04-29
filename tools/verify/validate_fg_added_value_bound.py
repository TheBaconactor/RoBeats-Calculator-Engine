"""Validate cheap added-fever upper bounds against persisted FG outcomes.

This is an offline/shadow verifier. It does not change production behavior and
does not submit GPU work.

The tested production-safe shape is:

    base_score(loadout) + conservative_added_fever_bound(loadout) <= song_best_base

If true, FG would be skipped for that retained loadout. A persisted FG-overall
row skipped by a bound is a known miss for that bound.
"""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import sys
import time
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.core.config import load_config
from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    FEVER_FILL_BASE_RATE,
    FEVER_TIME_OFFSET,
    FEVER_TIME_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    TOTAL_GEM_BUDGET,
    TOTAL_ROWS,
)
from gear_optimizer.core.utils import cfg_to_dict
from gear_optimizer.data.database import _unpack_stats_after_load
from gear_optimizer.pipeline.song_processor import get_base_calc_song
from gear_optimizer.solver.fg_exact_dp import _build_fp_actions
from gear_optimizer.solver.scoring.force_greats import _extract_base_stats
from gear_optimizer.solver.scoring_core import lookup_reference_py


def _infer_difficulty(song_name: str) -> str:
    for diff in ("Easy", "Normal", "Hard"):
        if f" ({diff}) " in str(song_name or ""):
            return diff
    return "Normal"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _load_details(raw: str | None) -> dict[str, Any]:
    try:
        obj = json.loads(raw) if raw else {}
    except Exception:
        obj = {}
    unpacked = _unpack_stats_after_load(obj)
    return unpacked if isinstance(unpacked, dict) else {}


def _selected_colors(details: dict[str, Any], calc_song: dict[str, Any]) -> tuple[str, str, str]:
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
    selected = details.get("SelectedElement") or details.get("Selected Element") or details.get("se") or primary
    return str(primary or ""), str(secondary or ""), str(selected or "")


class AddedValueBoundValidator:
    def __init__(self, *, db_path: Path, team_buff: str) -> None:
        self.db_path = db_path
        self.team_buff = str(team_buff or "T5").strip().upper()
        self.cfg = cfg_to_dict(load_config())
        self.ref_arrays = _get_team_buff_ref_arrays_cached()
        self.calc_song_cache: dict[str, dict[str, Any] | None] = {}
        self._max_window_cache: dict[tuple[int, int], int] = {}
        self._normal_timeline_cache: dict[tuple[int, int, int], tuple[int, int, int]] = {}
        self._k_by_budget_cache: dict[tuple[int, int, int, str], list[int]] = {}
        self._base_mask_cache: dict[tuple[int, int, int], np.ndarray] = {}

    def calc_song_for(self, song_name: str) -> dict[str, Any] | None:
        if song_name in self.calc_song_cache:
            return self.calc_song_cache[song_name]
        path = PROJECT_ROOT / "Data" / _infer_difficulty(song_name) / f"{song_name}.txt"
        if not path.exists():
            self.calc_song_cache[song_name] = None
            return None
        self.calc_song_cache[song_name] = get_base_calc_song(str(path), self.cfg)
        return self.calc_song_cache[song_name]

    def _song_arrays(self, calc_song: dict[str, Any]) -> tuple[np.ndarray, np.ndarray | None, int, float]:
        song_data = calc_song.get("song_data", {}) or {}
        metadata = calc_song.get("metadata", {}) or {}
        timestamps = np.asarray(song_data.get("fg_timestamps", song_data.get("timestamps", ())), dtype=np.float64)
        great_raw = song_data.get("fg_great_candidate_timestamps")
        great_candidates = np.asarray(great_raw, dtype=np.float64) if great_raw is not None else None
        long_notes = _safe_int(metadata.get("Long Notes"), 0)
        default_last = float(timestamps[-1]) if len(timestamps) else 0.0
        last_note_time = float(metadata.get("Last Note Time", default_last) or default_last)
        return timestamps, great_candidates, int(long_notes), float(last_note_time)

    def _timeline_params(
        self,
        calc_song: dict[str, Any],
        *,
        ft_stat: int,
        ff_stat: int,
    ) -> tuple[np.ndarray, np.ndarray | None, int, float, int, float]:
        timestamps, great_candidates, long_notes, last_note_time = self._song_arrays(calc_song)
        total_notes = int(len(timestamps))
        ff_factor = float(lookup_reference_py(int(ff_stat), self.ref_arrays["Fever Fill Rate"], TOTAL_ROWS))
        ft_factor = float(lookup_reference_py(int(ft_stat), self.ref_arrays["Fever Time"], TOTAL_ROWS))
        raw_fill = max(0.0, float(total_notes - long_notes) * float(FEVER_FILL_BASE_RATE)) * ff_factor
        non_fever_base = int(math.ceil(raw_fill))
        fever_duration = ((last_note_time * float(FEVER_TIME_SCALE)) + float(FEVER_TIME_OFFSET)) * ft_factor
        return timestamps, great_candidates, total_notes, float(raw_fill), int(non_fever_base), float(fever_duration)

    def _max_window_notes(self, calc_song: dict[str, Any], ft_stat: int) -> int:
        key = (id(calc_song), int(ft_stat))
        cached = self._max_window_cache.get(key)
        if cached is not None:
            return int(cached)
        timestamps, _great, total_notes, _raw, _nfb, fever_duration = self._timeline_params(
            calc_song,
            ft_stat=int(ft_stat),
            ff_stat=0,
        )
        if total_notes <= 0:
            self._max_window_cache[key] = 0
            return 0
        ends = np.searchsorted(timestamps, timestamps + float(fever_duration), side="left")
        widths = ends - np.arange(total_notes)
        max_width = int(widths.max()) if int(widths.size) else 0
        if max_width <= 0:
            max_width = 1
        self._max_window_cache[key] = int(max_width)
        return int(max_width)

    def _normal_timeline_counts(self, calc_song: dict[str, Any], ft_stat: int, ff_stat: int) -> tuple[int, int, int]:
        key = (id(calc_song), int(ft_stat), int(ff_stat))
        cached = self._normal_timeline_cache.get(key)
        if cached is not None:
            return cached
        timestamps, _great, total_notes, _raw, non_fever_base, fever_duration = self._timeline_params(
            calc_song,
            ft_stat=int(ft_stat),
            ff_stat=int(ff_stat),
        )
        idx = 0
        is_first = True
        fever_notes = 0
        windows = 0
        while idx < total_notes:
            notes_to_fill = int(non_fever_base - 1 if is_first else non_fever_base)
            if notes_to_fill < 0:
                notes_to_fill = 0
            end_normal = int(idx + notes_to_fill)
            if end_normal >= total_notes:
                break
            fever_end = int(np.searchsorted(timestamps, timestamps[end_normal] + float(fever_duration), side="left"))
            if fever_end <= end_normal:
                fever_end = min(total_notes, end_normal + 1)
            fever_notes += max(0, int(fever_end - end_normal))
            windows += 1
            idx = int(fever_end)
            is_first = False
        out = (int(windows), int(fever_notes), int(non_fever_base))
        self._normal_timeline_cache[key] = out
        return out

    def _base_fever_mask(self, calc_song: dict[str, Any], ft_stat: int, ff_stat: int) -> np.ndarray:
        key = (id(calc_song), int(ft_stat), int(ff_stat))
        cached = self._base_mask_cache.get(key)
        if cached is not None:
            return cached
        timestamps, _great, total_notes, _raw, non_fever_base, fever_duration = self._timeline_params(
            calc_song,
            ft_stat=int(ft_stat),
            ff_stat=int(ff_stat),
        )
        mask = np.zeros(total_notes, dtype=np.bool_)
        idx = 0
        is_first = True
        while idx < total_notes:
            notes_to_fill = int(non_fever_base - 1 if is_first else non_fever_base)
            if notes_to_fill < 0:
                notes_to_fill = 0
            end_normal = int(idx + notes_to_fill)
            if end_normal >= total_notes:
                break
            fever_end = int(np.searchsorted(timestamps, timestamps[end_normal] + float(fever_duration), side="left"))
            if fever_end <= end_normal:
                fever_end = min(total_notes, end_normal + 1)
            mask[end_normal:fever_end] = True
            idx = int(fever_end)
            is_first = False
        self._base_mask_cache[key] = mask
        return mask

    def _k_by_budget(
        self,
        calc_song: dict[str, Any],
        *,
        base_ft_stat: int,
        base_ff_stat: int,
        mode: str,
    ) -> list[int]:
        key = (id(calc_song), int(base_ft_stat), int(base_ff_stat), str(mode))
        cached = self._k_by_budget_cache.get(key)
        if cached is not None:
            return cached

        timestamps, _great, _long, _last = self._song_arrays(calc_song)
        total_notes = int(len(timestamps))
        max_k_by_budget = [0 for _ in range(TOTAL_GEM_BUDGET + 1)]

        for ft_gems in range(TOTAL_GEM_BUDGET + 1):
            ft_stat = max(0, min(TOTAL_ROWS, int(base_ft_stat) + (int(ft_gems) * GEM_SCALE_FEVER)))
            for ff_gems in range(TOTAL_GEM_BUDGET - int(ft_gems) + 1):
                remaining = int(TOTAL_GEM_BUDGET - int(ft_gems) - int(ff_gems))
                ff_stat = max(0, min(TOTAL_ROWS, int(base_ff_stat) + (int(ff_gems) * GEM_SCALE_FEVER)))
                windows, base_fever_notes, _nfb = self._normal_timeline_counts(calc_song, ft_stat, ff_stat)
                total_fever_upper = min(total_notes, int(windows) * self._max_window_notes(calc_song, ft_stat))
                if mode == "topk_minus_base_diagnostic":
                    # Diagnostic only: this assumes base-window overlap that has not been proven.
                    k = max(0, int(total_fever_upper) - int(base_fever_notes))
                else:
                    k = max(0, int(total_fever_upper))
                if k > int(max_k_by_budget[remaining]):
                    max_k_by_budget[remaining] = int(k)

        self._k_by_budget_cache[key] = max_k_by_budget
        return max_k_by_budget

    def _value_weights(
        self,
        *,
        base_stats: dict[str, Any],
        primary: str,
        secondary: str,
        selected: str,
        total_notes: int,
        remaining_budget: int,
        timing_budget_spent: int = 0,
    ) -> np.ndarray:
        budget = max(0, int(remaining_budget))
        timing_spent = max(0, int(timing_budget_spent))

        primary_val = _safe_int(base_stats.get(primary), 0) if primary else 0
        secondary_val = _safe_int(base_stats.get(secondary), 0) if secondary else 0

        # Conservative independent ceilings: each scoring lane may receive the full
        # remaining budget. This intentionally overbounds legal gem coupling.
        pp_stat = min(TOTAL_ROWS, _safe_int(base_stats.get("Perfect Points"), 0) + (budget * GEM_SCALE_NORMAL))
        cm_stat = min(TOTAL_ROWS, _safe_int(base_stats.get("Combo Multiplier"), 0) + (budget * GEM_SCALE_NORMAL))
        fm_stat = min(TOTAL_ROWS, _safe_int(base_stats.get("Fever Multiplier"), 0) + (budget * GEM_SCALE_FEVER))

        for gem_color, scale, cap_budget in (
            ("Chill", GEM_STAT_TO_ELEMENT_SCALE, budget),
            ("Flow", GEM_STAT_TO_ELEMENT_SCALE, budget),
            ("Rush", GEM_STAT_TO_ELEMENT_SCALE, budget),
            (selected, ELEMENTAL_GEM_SCALE, budget),
            ("Beat", GEM_STAT_TO_ELEMENT_SCALE, timing_spent),
            ("Vibe", GEM_STAT_TO_ELEMENT_SCALE, timing_spent),
        ):
            if primary and gem_color == primary:
                primary_val += int(cap_budget) * int(scale)
            if secondary and gem_color == secondary:
                secondary_val += int(cap_budget) * int(scale)

        base_value = np.float32((primary_val * 2) + secondary_val) + np.float32(
            lookup_reference_py(pp_stat, self.ref_arrays["Perfect Points"], TOTAL_ROWS)
        )
        combo_mul = np.float32(lookup_reference_py(cm_stat, self.ref_arrays["Combo Multiplier"], TOTAL_ROWS))
        fever_mul = np.float32(lookup_reference_py(fm_stat, self.ref_arrays["Fever Multiplier"], TOTAL_ROWS))
        body_bonus = int(np.float32(base_value * combo_mul * fever_mul)) - int(np.float32(base_value * combo_mul))
        factor = np.float32((combo_mul - np.float32(1.0)) * base_value / np.float32(100.0))

        weights = np.empty(int(total_notes), dtype=np.int64)
        for idx in range(int(total_notes)):
            if idx < 100:
                ramp_value = np.float32(base_value + (np.float32(idx + 1) * factor))
                weights[idx] = max(0, int(np.float32(ramp_value * fever_mul)) - int(ramp_value))
            else:
                weights[idx] = max(0, int(body_bonus))
        return weights

    @staticmethod
    def _top_k_sum(weights: np.ndarray, k: int) -> int:
        if int(k) <= 0 or int(weights.size) <= 0:
            return 0
        k = min(int(k), int(weights.size))
        if k >= int(weights.size):
            return int(np.sum(weights, dtype=np.int64))
        # Partition is cheaper than sorting every note for long songs.
        top = np.partition(weights, int(weights.size) - k)[int(weights.size) - k :]
        return int(np.sum(top, dtype=np.int64))

    def _topk_total_bound(
        self,
        *,
        calc_song: dict[str, Any],
        base_stats: dict[str, Any],
        primary: str,
        secondary: str,
        selected: str,
        mode: str,
    ) -> int:
        timestamps, _great, _long, _last = self._song_arrays(calc_song)
        total_notes = int(len(timestamps))
        k_by_budget = self._k_by_budget(
            calc_song,
            base_ft_stat=_safe_int(base_stats.get("Fever Time"), 0),
            base_ff_stat=_safe_int(base_stats.get("Fever Fill Rate"), 0),
            mode=mode,
        )
        best = 0
        for remaining_budget, k in enumerate(k_by_budget):
            if int(k) <= 0:
                continue
            timing_budget_spent = int(TOTAL_GEM_BUDGET - int(remaining_budget))
            weights = self._value_weights(
                base_stats=base_stats,
                primary=primary,
                secondary=secondary,
                selected=selected,
                total_notes=total_notes,
                remaining_budget=int(remaining_budget),
                timing_budget_spent=timing_budget_spent,
            )
            value = self._top_k_sum(weights, int(k))
            if value > best:
                best = int(value)
        return int(best)

    def _added_dp_bound(
        self,
        *,
        calc_song: dict[str, Any],
        ft_stat: int,
        ff_stat: int,
        weights: np.ndarray,
    ) -> int:
        timestamps, great_candidates, total_notes, raw_fill, non_fever_base, fever_duration = self._timeline_params(
            calc_song,
            ft_stat=int(ft_stat),
            ff_stat=int(ff_stat),
        )
        if total_notes <= 0:
            return 0

        base_mask = self._base_fever_mask(calc_song, int(ft_stat), int(ff_stat))
        added_weights = np.where(base_mask, 0, weights.astype(np.int64, copy=False))
        w_prefix = np.zeros(total_notes + 1, dtype=np.int64)
        w_prefix[1:] = np.cumsum(added_weights, dtype=np.int64)

        fever_end_song = np.searchsorted(timestamps, timestamps + float(fever_duration), side="left").astype(np.int32)
        use_timing_carry = great_candidates is not None
        if use_timing_carry:
            assert great_candidates is not None
            fever_end_gc = np.searchsorted(timestamps, great_candidates + float(fever_duration), side="left").astype(
                np.int32
            )
        else:
            fever_end_gc = None

        p_to_ks = _build_fp_actions(float(raw_fill), int(non_fever_base))
        p_max = int(len(p_to_ks) - 1)

        def _canon_carry(i: int, carry_idx: int) -> int:
            if (not use_timing_carry) or int(carry_idx) < 0:
                return -1
            if int(i) >= int(total_notes):
                return -1
            assert great_candidates is not None
            cidx = int(carry_idx)
            return -1 if float(great_candidates[cidx]) <= float(timestamps[int(i)]) else cidx

        @lru_cache(maxsize=None)
        def _solve(i: int, is_first: int, carry_idx_canon: int) -> int:
            i = int(i)
            if i >= total_notes:
                return 0

            first = bool(int(is_first) != 0)
            cidx = _canon_carry(i, int(carry_idx_canon))
            min_notes_to_fill = int(non_fever_base - 1 if first else non_fever_base)
            if min_notes_to_fill < 0:
                min_notes_to_fill = 0
            if i + min_notes_to_fill >= total_notes:
                return 0

            best_val = 0
            forced_start_base = i if first else (i + 1)
            if forced_start_base < 0:
                forced_start_base = 0

            for p in range(p_max + 1):
                notes_to_fill = int(non_fever_base + p)
                if first:
                    notes_to_fill -= 1
                if notes_to_fill < 0:
                    notes_to_fill = 0
                end_normal = int(i + notes_to_fill)
                if end_normal >= total_notes:
                    break

                for k in p_to_ks[p] if p < len(p_to_ks) else (0,):
                    forced_val = max(0, min(int(k), int(non_fever_base)))
                    actual_notes = max(0, int(end_normal - i))
                    forced_applied = min(int(forced_val), int(actual_notes))
                    next_cidx = int(cidx)

                    if use_timing_carry and forced_applied > 0:
                        assert great_candidates is not None
                        forced_end = int(forced_start_base + forced_applied - 1)
                        if forced_end >= forced_start_base and forced_end < end_normal and forced_end < total_notes:
                            if next_cidx < 0 or float(great_candidates[forced_end]) > float(
                                great_candidates[next_cidx]
                            ):
                                next_cidx = int(forced_end)

                    fever_end_idx = int(fever_end_song[end_normal])
                    if use_timing_carry and next_cidx >= 0:
                        assert great_candidates is not None and fever_end_gc is not None
                        if float(great_candidates[next_cidx]) > float(timestamps[end_normal]):
                            fever_end_idx = int(fever_end_gc[next_cidx])
                    if fever_end_idx <= end_normal:
                        fever_end_idx = min(total_notes, end_normal + 1)

                    carry_next = _canon_carry(int(fever_end_idx), int(next_cidx))
                    fever_bonus = int(w_prefix[fever_end_idx] - w_prefix[end_normal])
                    value = int(fever_bonus) + _solve(int(fever_end_idx), 0, int(carry_next))
                    if value > best_val:
                        best_val = int(value)

            return int(best_val)

        return int(_solve(0, 1, -1))

    def _current_stat_weights(
        self,
        *,
        stats: dict[str, Any],
        primary: str,
        secondary: str,
        total_notes: int,
    ) -> np.ndarray:
        primary_val = _safe_int(stats.get(primary), 0) if primary else 0
        secondary_val = _safe_int(stats.get(secondary), 0) if secondary else 0
        base_stats = {
            "Perfect Points": _safe_int(stats.get("Perfect Points"), 0),
            "Combo Multiplier": _safe_int(stats.get("Combo Multiplier"), 0),
            "Fever Multiplier": _safe_int(stats.get("Fever Multiplier"), 0),
            primary: primary_val,
            secondary: secondary_val,
        }
        return self._value_weights(
            base_stats=base_stats,
            primary=primary,
            secondary=secondary,
            selected="",
            total_notes=total_notes,
            remaining_budget=0,
            timing_budget_spent=0,
        )

    def _bounds_for_row(
        self,
        *,
        calc_song: dict[str, Any],
        details: dict[str, Any],
        requested_bounds: set[str],
    ) -> dict[str, int]:
        stats = dict(details.get("Stats") or {})
        gem_counts = dict(details.get("GemCounts") or {})
        primary, secondary, selected = _selected_colors(details, calc_song)
        row_ft_gems = _safe_int(details.get("FT"), 0)
        row_ff_gems = _safe_int(details.get("FF"), 0)
        base_stats = _extract_base_stats(stats, gem_counts, selected, row_ft_gems, row_ff_gems)
        timestamps, _great, _long, _last = self._song_arrays(calc_song)
        total_notes = int(len(timestamps))

        out: dict[str, int] = {}

        if "topk_total" in requested_bounds:
            out["topk_total"] = self._topk_total_bound(
                calc_song=calc_song,
                base_stats=base_stats,
                primary=primary,
                secondary=secondary,
                selected=selected,
                mode="topk_total",
            )

        if "topk_minus_base_diagnostic" in requested_bounds:
            out["topk_minus_base_diagnostic"] = self._topk_total_bound(
                calc_song=calc_song,
                base_stats=base_stats,
                primary=primary,
                secondary=secondary,
                selected=selected,
                mode="topk_minus_base_diagnostic",
            )

        if "added_dp_base_current" in requested_bounds:
            weights = self._current_stat_weights(
                stats=stats,
                primary=primary,
                secondary=secondary,
                total_notes=total_notes,
            )
            out["added_dp_base_current"] = self._added_dp_bound(
                calc_song=calc_song,
                ft_stat=_safe_int(stats.get("Fever Time"), 0),
                ff_stat=_safe_int(stats.get("Fever Fill Rate"), 0),
                weights=weights,
            )

        if "added_dp_base_ceiling" in requested_bounds:
            timing_stats = dict(base_stats)
            timing_stats["Fever Time"] = _safe_int(timing_stats.get("Fever Time"), 0) + (row_ft_gems * GEM_SCALE_FEVER)
            timing_stats["Fever Fill Rate"] = _safe_int(timing_stats.get("Fever Fill Rate"), 0) + (
                row_ff_gems * GEM_SCALE_FEVER
            )
            timing_stats["Beat"] = _safe_int(timing_stats.get("Beat"), 0) + (row_ft_gems * GEM_STAT_TO_ELEMENT_SCALE)
            timing_stats["Vibe"] = _safe_int(timing_stats.get("Vibe"), 0) + (row_ff_gems * GEM_STAT_TO_ELEMENT_SCALE)
            remaining_budget = max(0, int(TOTAL_GEM_BUDGET - row_ft_gems - row_ff_gems))
            weights = self._value_weights(
                base_stats=timing_stats,
                primary=primary,
                secondary=secondary,
                selected=selected,
                total_notes=total_notes,
                remaining_budget=remaining_budget,
                timing_budget_spent=0,
            )
            out["added_dp_base_ceiling"] = self._added_dp_bound(
                calc_song=calc_song,
                ft_stat=max(0, min(TOTAL_ROWS, _safe_int(timing_stats.get("Fever Time"), 0))),
                ff_stat=max(0, min(TOTAL_ROWS, _safe_int(timing_stats.get("Fever Fill Rate"), 0))),
                weights=weights,
            )

        return out

    def select_songs(self, conn: sqlite3.Connection, *, songs: list[str], per_bucket: int) -> list[sqlite3.Row]:
        if songs:
            selected: list[sqlite3.Row] = []
            for song in songs:
                row = conn.execute(
                    """
                    SELECT s.name, s.best_score, s.best_fg_score,
                           (
                               SELECT COUNT(*)
                               FROM team_buff_fg_loadouts f
                               WHERE f.song_name = s.name
                                 AND UPPER(COALESCE(f.team_buff, '')) = ?
                           ) AS fg_rows,
                           'selected' AS bucket
                    FROM songs s
                    WHERE s.name = ?
                    """,
                    (self.team_buff, str(song)),
                ).fetchone()
                if row is not None:
                    selected.append(row)
            return selected

        selected = []
        bucket_filters = {
            "zero": "fg_rows = 0",
            "tiny": "fg_rows BETWEEN 1 AND 3",
            "medium": "fg_rows BETWEEN 4 AND 25",
            "rich": "fg_rows >= 26",
        }
        for bucket, where_sql in bucket_filters.items():
            selected.extend(
                conn.execute(
                    f"""
                    WITH c AS (
                        SELECT
                            s.name,
                            s.best_score,
                            s.best_fg_score,
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
                    SELECT *, ? AS bucket
                    FROM c
                    WHERE {where_sql}
                    ORDER BY name
                    LIMIT ?
                    """,
                    (self.team_buff, self.team_buff, bucket, int(per_bucket)),
                ).fetchall()
            )
        return selected

    def validate(
        self,
        *,
        songs: list[str],
        per_bucket: int,
        max_rows_per_song: int,
        bounds: list[str],
    ) -> dict[str, Any]:
        requested_bounds = set(bounds)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        start = time.perf_counter()
        records: list[dict[str, Any]] = []
        missing_song_charts = 0

        try:
            selected_songs = self.select_songs(conn, songs=songs, per_bucket=per_bucket)
            for song in selected_songs:
                song_name = str(song["name"])
                calc_song = self.calc_song_for(song_name)
                if calc_song is None:
                    missing_song_charts += 1
                    continue
                rows = conn.execute(
                    """
                    SELECT loadout_hash, score, fg_score, details_json
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
                    if not isinstance(details.get("Stats"), dict):
                        continue
                    try:
                        bound_values = self._bounds_for_row(
                            calc_song=calc_song,
                            details=details,
                            requested_bounds=requested_bounds,
                        )
                    except Exception as exc:
                        bound_values = {"error": str(type(exc).__name__)}
                    score = int(row["score"] or 0)
                    fg_score = int(row["fg_score"] or 0)
                    best_score = int(song["best_score"] or 0)
                    records.append(
                        {
                            "song": song_name,
                            "bucket": str(song["bucket"]),
                            "fg_rows": int(song["fg_rows"] or 0),
                            "rank": int(rank),
                            "score": score,
                            "fg_score": fg_score,
                            "fg_lift": int(fg_score - score) if fg_score > 0 else 0,
                            "base_deficit": int(best_score - score),
                            "fg_overall": bool(fg_score > best_score),
                            "bounds": bound_values,
                        }
                    )
        finally:
            conn.close()

        return {
            "db": str(self.db_path),
            "team_buff": self.team_buff,
            "bounds": bounds,
            "bounds_contract": {
                "topk_total": "production-safe but intentionally loose",
                "topk_minus_base_diagnostic": "unsafe diagnostic; subtracts base fever count without a proven overlap guarantee",
                "added_dp_base_current": "diagnostic only; fixed current stats/base FTFF, no full production reoptimization",
                "added_dp_base_ceiling": "diagnostic only; base FTFF with conservative score ceiling, not full FTFF surface",
            },
            "records": len(records),
            "songs": len({str(row.get("song") or "") for row in records}),
            "songs_missing_chart": int(missing_song_charts),
            "elapsed_sec": round(time.perf_counter() - start, 3),
            "summaries": self._summaries(records, bounds),
        }

    @staticmethod
    def _summaries(records: list[dict[str, Any]], bounds: list[str]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        deficits = [int(row["base_deficit"]) for row in records]
        for bound_name in bounds:
            checked = 0
            would_skip = 0
            false_skips = 0
            total_overall = 0
            values: list[int] = []
            examples: list[dict[str, Any]] = []
            by_bucket: dict[str, dict[str, int]] = defaultdict(
                lambda: {"checked": 0, "would_skip": 0, "false_skips": 0, "fg_overall": 0}
            )
            for row in records:
                bounds_map = row.get("bounds") if isinstance(row.get("bounds"), dict) else {}
                if bound_name not in bounds_map:
                    continue
                value = bounds_map.get(bound_name)
                if not isinstance(value, int):
                    continue
                checked += 1
                values.append(int(value))
                deficit = int(row["base_deficit"])
                skip = int(value) <= int(deficit)
                overall = bool(row["fg_overall"])
                would_skip += int(skip)
                false_skips += int(skip and overall)
                total_overall += int(overall)
                bucket = str(row.get("bucket") or "unknown")
                by_bucket[bucket]["checked"] += 1
                by_bucket[bucket]["would_skip"] += int(skip)
                by_bucket[bucket]["false_skips"] += int(skip and overall)
                by_bucket[bucket]["fg_overall"] += int(overall)
                if skip and overall and len(examples) < 10:
                    examples.append(
                        {
                            "song": row["song"],
                            "bucket": bucket,
                            "rank": row["rank"],
                            "score": row["score"],
                            "fg_score": row["fg_score"],
                            "fg_lift": row["fg_lift"],
                            "base_deficit": deficit,
                            "bound": int(value),
                        }
                    )

            pct = {}
            if values:
                pct = {
                    "p10": int(np.percentile(values, 10)),
                    "p50": int(np.percentile(values, 50)),
                    "p90": int(np.percentile(values, 90)),
                    "p99": int(np.percentile(values, 99)),
                }
            out[bound_name] = {
                "checked": checked,
                "would_skip": would_skip,
                "skip_rate": round(float(would_skip) / float(checked), 4) if checked else 0.0,
                "fg_overall_rows": total_overall,
                "false_skips": false_skips,
                "false_skip_rate_overall": round(float(false_skips) / float(total_overall), 4)
                if total_overall
                else 0.0,
                "bound_percentiles": pct,
                "deficit_percentiles": {
                    "p10": int(np.percentile(deficits, 10)) if deficits else 0,
                    "p50": int(np.percentile(deficits, 50)) if deficits else 0,
                    "p90": int(np.percentile(deficits, 90)) if deficits else 0,
                    "p99": int(np.percentile(deficits, 99)) if deficits else 0,
                },
                "by_bucket": dict(sorted(by_bucket.items())),
                "false_examples": examples,
            }
        return out


def _parse_bounds(raw: str) -> list[str]:
    valid = {
        "topk_total",
        "topk_minus_base_diagnostic",
        "added_dp_base_current",
        "added_dp_base_ceiling",
    }
    out: list[str] = []
    for part in str(raw or "").split(","):
        name = part.strip()
        if not name:
            continue
        if name not in valid:
            raise ValueError(f"unknown bound '{name}'; valid: {', '.join(sorted(valid))}")
        out.append(name)
    return out or ["topk_total"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate FG added-fever upper-bound candidates.")
    parser.add_argument("--db", default=str(PROJECT_ROOT / "evolution.db"))
    parser.add_argument("--team-buff", default="T5")
    parser.add_argument("--song", action="append", default=[], help="Specific song name; can be repeated.")
    parser.add_argument("--per-bucket", type=int, default=8)
    parser.add_argument("--max-rows-per-song", type=int, default=51)
    parser.add_argument(
        "--bounds",
        default="topk_total,topk_minus_base_diagnostic,added_dp_base_current,added_dp_base_ceiling",
        help="Comma-separated: topk_total, topk_minus_base_diagnostic, added_dp_base_current, added_dp_base_ceiling",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    validator = AddedValueBoundValidator(db_path=Path(args.db), team_buff=str(args.team_buff or "T5"))
    report = validator.validate(
        songs=list(args.song or []),
        per_bucket=max(1, int(args.per_bucket)),
        max_rows_per_song=max(1, int(args.max_rows_per_song)),
        bounds=_parse_bounds(str(args.bounds or "")),
    )

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    print("=" * 78)
    print("FG Added-Value Bound Validation")
    print("=" * 78)
    print(f"DB: {report['db']}  TeamBuff: {report['team_buff']}")
    print(f"Checked {report['records']:,} rows across {report['songs']:,} songs in {report['elapsed_sec']}s.")
    print()
    for name, summary in report["summaries"].items():
        pct = summary["bound_percentiles"]
        print(
            f"{name:<30} skip={summary['would_skip']:<6}/{summary['checked']:<6} "
            f"rate={summary['skip_rate']:<6} overall={summary['fg_overall_rows']:<4} "
            f"false={summary['false_skips']:<4} "
            f"bound_p50={pct.get('p50', 0):,} bound_p90={pct.get('p90', 0):,}"
        )
        if summary["false_examples"]:
            for ex in summary["false_examples"][:3]:
                print(
                    f"  false {str(ex['song'])[:58]} | def={ex['base_deficit']:,} "
                    f"lift={ex['fg_lift']:,} bound={ex['bound']:,}"
                )
    print()
    print("Only topk_total is production-safe here, and it is deliberately loose.")
    print("The other bounds are diagnostics for whether tighter math might be worth pursuing.")


if __name__ == "__main__":
    main()
