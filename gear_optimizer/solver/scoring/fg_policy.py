from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import floor
from typing import Any, Mapping

from ...core.constants import TOTAL_GEM_BUDGET
from ...core.ref_lookup import StatFactors, resolve_stat_factors
from ...core.utils import safe_float, safe_int
from .stats_scoring import _force_greats_counts_to_dict, build_great_penalty_table

__all__ = [
    "FGSongInputs",
    "StatFactors",
    "resolve_stat_factors",
]


@dataclass(frozen=True, slots=True)
class FGSongInputs:
    timestamps: Any
    great_candidates: Any
    use_forced_great_timing: bool
    total_notes: int
    long_notes: int
    last_note_time: float
    primary_color: str
    secondary_color: str


def extract_fg_song_inputs(calc_song: Mapping[str, Any]) -> FGSongInputs:
    song_data = (calc_song.get("song_data", {}) or {}) if isinstance(calc_song, Mapping) else {}
    metadata = (calc_song.get("metadata", {}) or {}) if isinstance(calc_song, Mapping) else {}

    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    if timestamps is None:
        timestamps = ()
    great_candidates = song_data.get("fg_great_candidate_timestamps", timestamps)
    use_forced_great_timing = bool(song_data.get("fg_great_candidate_timestamps") is not None)

    try:
        total_notes = int(len(timestamps))
    except (ValueError, TypeError):
        total_notes = 0

    long_notes = safe_int(metadata.get("Long Notes"), 0)

    base_ts = song_data.get("timestamps", timestamps)
    if base_ts is None:
        base_ts = timestamps
    default_last_note = base_ts[-1] if total_notes > 0 else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    return FGSongInputs(
        timestamps=timestamps,
        great_candidates=great_candidates,
        use_forced_great_timing=bool(use_forced_great_timing),
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        primary_color=str(metadata.get("Primary Color", "") or ""),
        secondary_color=str(metadata.get("Secondary Color", "") or ""),
    )


def normalize_ft_ff_search_ranges(
    search_ranges: tuple[int, int, int, int] | None,
    *,
    total_budget: int = TOTAL_GEM_BUDGET,
) -> tuple[int, int, int, int]:
    max_budget = int(total_budget)
    if search_ranges:
        start_ft, end_ft, start_ff, end_ff = search_ranges
        start_ft = max(0, int(start_ft))
        end_ft = min(max_budget, int(end_ft))
        start_ff = max(0, int(start_ff))
        end_ff = min(max_budget, int(end_ff))
    else:
        start_ft, end_ft = 0, max_budget
        start_ff, end_ff = 0, max_budget
    return int(start_ft), int(end_ft), int(start_ff), int(end_ff)


def iter_ft_ff_budget_pairs(
    start_ft: int,
    end_ft: int,
    start_ff: int,
    end_ff: int,
    *,
    total_budget: int = TOTAL_GEM_BUDGET,
):
    budget = int(total_budget)
    start_ft_i = int(start_ft)
    end_ft_i = int(end_ft)
    start_ff_i = int(start_ff)
    end_ff_i = int(end_ff)

    for ft_gems in range(start_ft_i, end_ft_i + 1):
        remaining_after_ft = budget - int(ft_gems)
        if remaining_after_ft < 0:
            break
        ff_end = min(end_ff_i, remaining_after_ft)
        for ff_gems in range(start_ff_i, ff_end + 1):
            current_budget = remaining_after_ft - int(ff_gems)
            if current_budget < 0:
                break
            yield int(ft_gems), int(ff_gems), int(current_budget)


def build_force_greats_counts_list(num_sections: int, non_fever_base: int) -> list[tuple[int, ...]]:
    n = int(num_sections)
    if n <= 0:
        return []
    cap_s0 = min(int(non_fever_base or 0), 50)
    cap_s1 = min(int(non_fever_base or 0), 25)
    cap_s2 = min(int(non_fever_base or 0), 15)
    if n == 1:
        return [(s0,) for s0 in range(cap_s0 + 1)]
    if n == 2:
        return [(s0, s1) for s0 in range(cap_s0 + 1) for s1 in range(cap_s1 + 1)]
    if n == 3:
        return [
            (s0, s1, s2)
            for s0 in range(cap_s0 + 1)
            for s1 in range(cap_s1 + 1)
            for s2 in range(cap_s2 + 1)
        ]
    cap = min(int(non_fever_base or 0), 5)
    return [tuple(int(v) for v in counts) for counts in product(range(cap + 1), repeat=n)]


def compute_great_penalty_base(primary_val: int, secondary_val: int) -> int:
    return int(floor((int(primary_val) * 2) * (2.0 / 3.0)) + floor(int(secondary_val) * (2.0 / 3.0)) + 150)


def build_penalty_table_and_body(
    *,
    base_value: float,
    combo_mul: float,
    primary_val: int,
    secondary_val: int,
    head_limit: int = 100,
) -> tuple[list[int], int, int]:
    combo_value = int(floor(float(base_value) * float(combo_mul)))
    great_penalty_base_head = compute_great_penalty_base(int(primary_val), int(secondary_val))
    great_penalty_base_raw = ((int(primary_val) * 2) * (2.0 / 3.0)) + (int(secondary_val) * (2.0 / 3.0)) + 150.0
    great_combo_value = int(floor(float(great_penalty_base_raw) * float(combo_mul)))
    body_penalty = max(0, int(combo_value - great_combo_value))

    penalty_table = build_great_penalty_table(
        float(base_value),
        float(combo_mul),
        int(great_penalty_base_head),
        head_limit=int(head_limit),
    )
    if penalty_table:
        penalty_table[-1] = int(body_penalty)
    return penalty_table, int(body_penalty), int(combo_value)


def accumulate_forced_score_penalty(
    *,
    forced: int,
    start_idx: int,
    skip_wasted: bool,
    penalty_table: list[int],
    body_penalty: int,
) -> int:
    forced_i = int(forced)
    if forced_i <= 0:
        return 0
    note_idx = int(start_idx) + (0 if bool(skip_wasted) else 1)
    score_penalty = 0
    remaining = int(forced_i)
    while remaining > 0:
        if note_idx < len(penalty_table):
            score_penalty += int(penalty_table[note_idx])
        else:
            score_penalty += int(body_penalty)
        note_idx += 1
        remaining -= 1
    return int(score_penalty)


def accumulate_fg_penalties(
    *,
    section_details: list[dict[str, Any]],
    penalty_table: list[int],
    body_penalty: int,
    combo_value: int,
) -> tuple[int, int, dict[str, dict[str, int]]]:
    total_score_penalty = 0
    total_fill_penalty = 0
    penalty_analysis: dict[str, dict[str, int]] = {}
    for idx, detail in enumerate(section_details):
        forced = int(detail.get("forced", 0))
        fill_penalty_score = int(detail.get("fill_penalty_notes", 0)) * int(combo_value)
        score_penalty = accumulate_forced_score_penalty(
            forced=int(forced),
            start_idx=int(detail.get("start_idx", 0)),
            skip_wasted=bool(detail.get("skip_wasted")),
            penalty_table=penalty_table,
            body_penalty=int(body_penalty),
        )
        total_score_penalty += int(score_penalty)
        total_fill_penalty += int(fill_penalty_score)
        section_key = f"NonFever{idx + 1}"
        penalty_analysis[section_key] = {
            "forced_greats": int(forced),
            "score_penalty": int(score_penalty),
            "fill_penalty": int(fill_penalty_score),
            "total_penalty": int(score_penalty + fill_penalty_score),
        }
    return int(total_score_penalty), int(total_fill_penalty), penalty_analysis


def build_fg_result_dict(
    *,
    base_score: int,
    total_score_penalty: int,
    total_fill_penalty: int,
    section_details: list[dict[str, Any]],
    config_counts: list[int],
    penalty_analysis: dict[str, dict[str, int]],
    non_fever_base: int,
) -> dict[str, Any]:
    used_counts = list(config_counts or [])
    if len(used_counts) < len(section_details):
        used_counts.extend([0] * (len(section_details) - len(used_counts)))
    used_counts = used_counts[: len(section_details)]

    return {
        "base_score": int(base_score),
        "final_score": max(0, int(base_score) - int(total_score_penalty)),
        "score_penalty": int(total_score_penalty),
        "fill_penalty": int(total_fill_penalty),
        "total_penalty": int(total_score_penalty + total_fill_penalty),
        "num_non_fever_sections": len(section_details),
        "config_counts": list(used_counts),
        "config_dict": _force_greats_counts_to_dict(list(used_counts), len(section_details)),
        "penalty_analysis": penalty_analysis,
        "non_fever_base": int(non_fever_base),
    }
