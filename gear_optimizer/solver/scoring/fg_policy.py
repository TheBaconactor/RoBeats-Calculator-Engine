from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any, Mapping

from ...core.ref_lookup import StatFactors, resolve_stat_factors
from ...core.utils import safe_float, safe_int
from .stats_scoring import _force_greats_counts_to_dict, build_great_penalty_table

__all__ = [
    "FGSongInputs",
    "SongMeta",
    "StatFactors",
    "extract_song_meta",
    "resolve_stat_factors",
]


GREAT_RESULT_POINTS = 150


@dataclass(frozen=True, slots=True)
class SongMeta:
    primary_color: str
    secondary_color: str


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


def extract_song_meta(
    calc_song: Mapping[str, Any],
    *,
    default_primary: str = "",
    default_secondary: str = "",
) -> SongMeta:
    metadata = (calc_song.get("metadata", {}) or {}) if isinstance(calc_song, Mapping) else {}
    return SongMeta(
        primary_color=str(metadata.get("Primary Color", default_primary) or default_primary),
        secondary_color=str(metadata.get("Secondary Color", default_secondary) or default_secondary),
    )


def extract_fg_song_inputs(calc_song: Mapping[str, Any]) -> FGSongInputs:
    song_data = (calc_song.get("song_data", {}) or {}) if isinstance(calc_song, Mapping) else {}
    metadata = (calc_song.get("metadata", {}) or {}) if isinstance(calc_song, Mapping) else {}
    song_meta = extract_song_meta(calc_song)

    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    if timestamps is None:
        timestamps = ()
    has_perfect_candidates = "fg_perfect_candidate_timestamps" in song_data
    has_great_candidates = "fg_great_candidate_timestamps" in song_data
    perfect_candidates = song_data.get("fg_perfect_candidate_timestamps", timestamps)
    great_candidates = song_data.get("fg_great_candidate_timestamps", timestamps)
    # Earliest-Perfect floor envelope: the carry-aware fever-boundary search basis (issue
    # #42). If an FG timing envelope is present, the floor is REQUIRED; silently searching chart
    # would under-count endpoint-early fever and produce a plausible but wrong best_fg_score.
    if "fg_perfect_floor_timestamps" in song_data:
        perfect_floor = song_data["fg_perfect_floor_timestamps"]
    elif has_perfect_candidates or has_great_candidates:
        raise ValueError(
            "fg_perfect_floor_timestamps is required when FG timing candidate timestamps are present"
        )
    else:
        # Explicit degenerate baseline: no timing envelope applied, so chart is the floor.
        perfect_floor = timestamps
    # Earliest-Great floor (issue #44 greats-side endpoint-early fever). REQUIRED whenever an FG
    # timing envelope is present, same fail-loud rule as perfect_floor: silently searching chart
    # (or the Perfect floor) would miss the early-Great boundary surfaces -> a wrong best_fg_score.
    if "fg_great_floor_timestamps" in song_data:
        great_floor = song_data["fg_great_floor_timestamps"]
    elif has_perfect_candidates or has_great_candidates:
        raise ValueError(
            "fg_great_floor_timestamps is required when FG timing candidate timestamps are present"
        )
    else:
        # Degenerate baseline (no envelope): chart is the floor, so the Great boundary collapses
        # onto the Perfect one and no early-Great surface is reachable.
        great_floor = timestamps
    use_forced_great_timing = bool(has_great_candidates)

    try:
        total_notes = int(len(timestamps))
    except (ValueError, TypeError):
        total_notes = 0

    lanes = song_data.get("lanes")
    if lanes is None or len(lanes) != total_notes:
        # Missing lanes are an external chart-ingest boundary. Use all-distinct lanes so reachability
        # imposes no fabricated same-lane constraint; production call sites that require real lanes
        # can still fail loudly when overlap makes lane identity load-bearing.
        lanes = tuple(range(total_notes))

    long_notes = safe_int(metadata.get("Long Notes"), 0)

    base_ts = song_data.get("timestamps", timestamps)
    if base_ts is None:
        base_ts = timestamps
    default_last_note = base_ts[-1] if total_notes > 0 else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    return FGSongInputs(
        timestamps=timestamps,
        perfect_candidates=perfect_candidates,
        great_candidates=great_candidates,
        perfect_floor=perfect_floor,
        great_floor=great_floor,
        lanes=lanes,
        use_forced_great_timing=bool(use_forced_great_timing),
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        primary_color=song_meta.primary_color,
        secondary_color=song_meta.secondary_color,
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
