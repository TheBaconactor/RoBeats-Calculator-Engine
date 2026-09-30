from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any

from .stats_scoring import _force_greats_counts_to_dict, build_great_penalty_table

__all__ = [
    "FGSongInputs",
]


GREAT_RESULT_POINTS = 150


@dataclass(frozen=True, slots=True)
class FGSongInputs:
    timestamps: Any
    perfect_candidates: Any
    great_candidates: Any
    perfect_floor: Any
    great_floor: Any
    lanes: Any
    use_forced_great_timing: bool
    total_notes: int
    long_notes: int
    last_note_time: float
    primary_color: str
    secondary_color: str


def fg_song_inputs(song) -> FGSongInputs:
    """The FG solver's view of a TimedSong.

    perfect_window carries the Perfect/Great candidate and floor envelopes (carry-aware FG); zero_ms
    scores every activation and boundary at the hit timeline and has no forced-Great carry.
    """
    chart = song.chart
    hits = song.hit_timestamps
    enveloped = song.mode == "perfect_window"
    return FGSongInputs(
        timestamps=hits,
        perfect_candidates=song.perfect_candidates if enveloped else hits,
        great_candidates=song.great_candidates if enveloped else hits,
        perfect_floor=song.perfect_floor if enveloped else hits,
        great_floor=song.great_floor if enveloped else hits,
        lanes=chart.lanes,
        use_forced_great_timing=enveloped,
        total_notes=chart.total_notes,
        long_notes=chart.long_notes,
        last_note_time=chart.last_note_time,
        primary_color=chart.primary,
        secondary_color=chart.secondary,
    )


def compute_great_penalty_base(primary_val: int, secondary_val: int) -> int:
    primary_i = int(primary_val)
    secondary_i = int(secondary_val)
    return int(
        floor(float(primary_i) * (4.0 / 3.0))
        + floor(float(secondary_i) * (2.0 / 3.0))
        + GREAT_RESULT_POINTS
    )


def build_penalty_table_and_body(
    *,
    base_value: float,
    combo_mul: float,
    primary_val: int,
    secondary_val: int,
    head_limit: int = 100,
) -> tuple[list[int], int, int]:
    combo_value = int(floor(float(base_value) * float(combo_mul)))
    primary_i = int(primary_val)
    secondary_i = int(secondary_val)
    great_penalty_base_head = compute_great_penalty_base(
        primary_i,
        secondary_i,
    )
    great_penalty_base_raw = (
        (float(primary_i) * (4.0 / 3.0))
        + (float(secondary_i) * (2.0 / 3.0))
        + float(GREAT_RESULT_POINTS)
    )
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
