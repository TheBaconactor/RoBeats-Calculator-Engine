"""
CPU exact score replay helpers.

These helpers are intentionally outside the GPU/JIT hot path. They are used for
canonical replay, persistence, and DB repair where the final visible score should
follow Python/Luau-style double precision instead of the optimizer's f32 GPU
search score.
"""

from __future__ import annotations

from math import floor
from typing import Any, Mapping

import numpy as np

from ...core.constants import TOTAL_ROWS
from ...helpers.song_helpers.ref_array_builder import resolve_exact_replay_ref_arrays
from ...core.utils import safe_float, safe_int
from ..fever_timeline import calculate_fever_timeline_indices
from ..force_greats_common import compute_force_greats_timeline
from ..scoring_core import lookup_reference_py
from .stats_scoring import build_great_penalty_table, _force_greats_counts_to_dict


def calculate_score_exact(
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    fever_mask_head,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    """
    Score a fixed timeline using float64 arithmetic and per-note floors.

    This mirrors the existing scoring order, but deliberately avoids f32 casts
    so retained/replayed rows do not inherit GPU boundary drift.
    """
    base_f = float(base_value)
    combo_f = float(combo_mul)
    fever_f = float(fever_mul)

    combo_val_per_note = floor(base_f * combo_f)
    fever_val_per_note = floor(base_f * combo_f * fever_f)
    body_score = (int(count_body_fever) * fever_val_per_note) + (int(count_body_normal) * combo_val_per_note)

    factor = (combo_f - 1.0) * base_f / 100.0
    total_head = 0
    for i, is_fever in enumerate(fever_mask_head):
        ramp_val = base_f + (float(i + 1) * factor)
        total_head += floor(ramp_val * fever_f) if bool(is_fever) else floor(ramp_val)

    return int(body_score + total_head)


def score_fixed_value_exact(
    *,
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    ft_idx: int,
    ff_idx: int,
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    fever_mask_buffer=None,
) -> int:
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("timestamps")
    if timestamps is None:
        timestamps = song_data.get("chart_timestamps", song_data.get("fg_timestamps", ()))
    total_notes = int(len(timestamps))
    if total_notes <= 0:
        return 0

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    mask_buffer = fever_mask_buffer
    if mask_buffer is None or int(getattr(mask_buffer, "shape", (0,))[0]) != total_notes:
        mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    ft_factor = lookup_reference_py(int(ft_idx), ref_arrays["Fever Time"], TOTAL_ROWS)
    ff_factor = lookup_reference_py(int(ff_idx), ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_mask_head, count_body_fever, count_body_normal, _non_fever, _activations = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        ff_factor,
        ft_factor,
        long_notes,
        last_note_time,
        mask_buffer,
    )

    return calculate_score_exact(
        float(base_value),
        float(combo_mul),
        float(fever_mul),
        fever_mask_head,
        int(count_body_fever),
        int(count_body_normal),
    )


def score_stats_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    *,
    fever_mask_buffer=None,
) -> int:
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    metadata = calc_song.get("metadata", {}) or {}
    primary = str(metadata.get("Primary Color", "") or "")
    secondary = str(metadata.get("Secondary Color", "") or "")

    pp_factor = lookup_reference_py(safe_int(stats.get("Perfect Points", 0), 0), ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(
        safe_int(stats.get("Combo Multiplier", 0), 0),
        ref_arrays["Combo Multiplier"],
        TOTAL_ROWS,
    )
    fever_mul = lookup_reference_py(
        safe_int(stats.get("Fever Multiplier", 0), 0),
        ref_arrays["Fever Multiplier"],
        TOTAL_ROWS,
    )
    base_value = (safe_int(stats.get(primary, 0), 0) * 2) + safe_int(stats.get(secondary, 0), 0) + float(pp_factor)

    return score_fixed_value_exact(
        base_value=float(base_value),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        ft_idx=safe_int(stats.get("Fever Time", 0), 0),
        ff_idx=safe_int(stats.get("Fever Fill Rate", 0), 0),
        calc_song=calc_song,
        ref_arrays=ref_arrays,
        fever_mask_buffer=fever_mask_buffer,
    )


def evaluate_force_greats_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    forced_counts=None,
) -> dict[str, Any] | None:
    """
    CPU exact replay for a persisted ForceGreats config.

    This preserves the existing ForceGreats timeline and penalty placement rules,
    but computes the visible score with double precision.
    """
    if not stats or not calc_song:
        return None
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    great_candidates = song_data.get("fg_great_candidate_timestamps", timestamps)
    use_forced_great_timing = bool(song_data.get("fg_great_candidate_timestamps") is not None)
    total_notes = int(len(timestamps)) if timestamps is not None else 0
    if total_notes <= 0:
        return None

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    base_ts = song_data.get("timestamps", timestamps)
    default_last_note = base_ts[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)
    primary_color = str(metadata.get("Primary Color", "") or "")
    secondary_color = str(metadata.get("Secondary Color", "") or "")
    primary_val = safe_int(stats.get(primary_color, 0), 0)
    secondary_val = safe_int(stats.get(secondary_color, 0), 0)

    pp_factor = lookup_reference_py(safe_int(stats.get("Perfect Points", 0), 0), ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(
        safe_int(stats.get("Combo Multiplier", 0), 0),
        ref_arrays["Combo Multiplier"],
        TOTAL_ROWS,
    )
    fever_mul = lookup_reference_py(
        safe_int(stats.get("Fever Multiplier", 0), 0),
        ref_arrays["Fever Multiplier"],
        TOTAL_ROWS,
    )
    fever_fill_rate = lookup_reference_py(
        safe_int(stats.get("Fever Fill Rate", 0), 0),
        ref_arrays["Fever Fill Rate"],
        TOTAL_ROWS,
    )
    fever_time_stat = lookup_reference_py(
        safe_int(stats.get("Fever Time", 0), 0),
        ref_arrays["Fever Time"],
        TOTAL_ROWS,
    )

    base_value = float((primary_val * 2) + secondary_val) + float(pp_factor)
    combo_value = floor(base_value * float(combo_mul))
    great_penalty_base_head = floor((primary_val * 2) * (2.0 / 3.0)) + floor(secondary_val * (2.0 / 3.0)) + 150
    great_penalty_base_raw = ((primary_val * 2) * (2.0 / 3.0)) + (secondary_val * (2.0 / 3.0)) + 150.0
    great_combo_value = floor(great_penalty_base_raw * float(combo_mul))
    body_penalty = max(0, combo_value - great_combo_value)

    penalty_table = build_great_penalty_table(base_value, float(combo_mul), great_penalty_base_head)
    if penalty_table:
        penalty_table[-1] = body_penalty

    force_counts = list(forced_counts or [])
    (
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_details,
    ) = compute_force_greats_timeline(
        timestamps,
        great_candidates,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
        force_counts,
        clamp_base_notes_nonnegative=True,
        clamp_forced_to_section_notes=True,
        use_forced_great_timing=use_forced_great_timing,
    )

    base_score = calculate_score_exact(
        base_value,
        float(combo_mul),
        float(fever_mul),
        fever_mask_head,
        int(count_body_fever),
        int(count_body_normal),
    )

    total_score_penalty = 0
    total_fill_penalty = 0
    penalty_analysis: dict[str, dict[str, int]] = {}
    for idx, detail in enumerate(section_details):
        section_key = f"NonFever{idx + 1}"
        fill_penalty_score = int(detail["fill_penalty_notes"]) * int(combo_value)
        total_fill_penalty += fill_penalty_score
        forced = int(detail["forced"])
        if forced > 0:
            start_idx = int(detail["start_idx"]) + (0 if detail.get("skip_wasted") else 1)
            score_penalty = 0
            note_idx = start_idx
            remaining = forced
            while remaining > 0:
                if note_idx < len(penalty_table):
                    score_penalty += int(penalty_table[note_idx])
                else:
                    score_penalty += int(body_penalty)
                note_idx += 1
                remaining -= 1
        else:
            score_penalty = 0
        total_score_penalty += score_penalty
        penalty_analysis[section_key] = {
            "forced_greats": int(forced),
            "score_penalty": int(score_penalty),
            "fill_penalty": int(fill_penalty_score),
            "total_penalty": int(score_penalty + fill_penalty_score),
        }

    used_counts = force_counts[:]
    if len(used_counts) < len(section_details):
        used_counts.extend([0] * (len(section_details) - len(used_counts)))

    return {
        "base_score": int(base_score),
        "final_score": max(0, int(base_score) - int(total_score_penalty)),
        "score_penalty": int(total_score_penalty),
        "fill_penalty": int(total_fill_penalty),
        "total_penalty": int(total_score_penalty + total_fill_penalty),
        "num_non_fever_sections": len(section_details),
        "config_counts": used_counts[: len(section_details)],
        "config_dict": _force_greats_counts_to_dict(used_counts, len(section_details)),
        "penalty_analysis": penalty_analysis,
        "non_fever_base": int(non_fever_base),
    }
