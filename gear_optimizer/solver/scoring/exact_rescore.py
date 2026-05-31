"""
CPU exact score replay helpers.

These helpers are intentionally outside the GPU/JIT hot path. They are used for
canonical replay, persistence, and DB repair where the final visible score should
follow Python/Luau-style double precision instead of the optimizer's f32 GPU
search score.
"""

from __future__ import annotations

from math import floor
import threading
from typing import Any, Mapping

import numpy as np

from ...core.constants import TOTAL_ROWS
from ...helpers.song_helpers.ref_array_builder import resolve_exact_replay_ref_arrays
from ...core.utils import safe_float, safe_int
from ..fever_timeline import calculate_fever_timeline_indices, calculate_force_greats_timeline_indices
from ..scoring_core import lookup_reference_py
from .fg_policy import (
    accumulate_fg_penalties,
    build_fg_result_dict,
    build_penalty_table_and_body,
    extract_fg_song_inputs,
    extract_song_meta,
    is_single_color_song,
    resolve_stat_factors,
)


_FG_TIMELINE_TLS = threading.local()


def _get_fg_timeline_buffers(total_notes: int):
    n = max(0, int(total_notes))
    section_cap = n + 1

    buf = getattr(_FG_TIMELINE_TLS, "buf", None)
    if buf is None:
        buf = {}
        _FG_TIMELINE_TLS.buf = buf

    fever_mask = buf.get("fever_mask")
    if fever_mask is None or int(getattr(fever_mask, "shape", (0,))[0]) != n:
        fever_mask = np.zeros(n, dtype=np.bool_)
        buf["fever_mask"] = fever_mask
    else:
        fever_mask[:] = False

    section_start = buf.get("section_start")
    if section_start is None or int(getattr(section_start, "shape", (0,))[0]) != section_cap:
        section_start = np.zeros(section_cap, dtype=np.int32)
        buf["section_start"] = section_start
    else:
        section_start[:] = 0

    section_forced = buf.get("section_forced")
    if section_forced is None or int(getattr(section_forced, "shape", (0,))[0]) != section_cap:
        section_forced = np.zeros(section_cap, dtype=np.int32)
        buf["section_forced"] = section_forced
    else:
        section_forced[:] = 0

    section_fill_penalty = buf.get("section_fill_penalty")
    if section_fill_penalty is None or int(getattr(section_fill_penalty, "shape", (0,))[0]) != section_cap:
        section_fill_penalty = np.zeros(section_cap, dtype=np.int32)
        buf["section_fill_penalty"] = section_fill_penalty
    else:
        section_fill_penalty[:] = 0

    section_skip_wasted = buf.get("section_skip_wasted")
    if section_skip_wasted is None or int(getattr(section_skip_wasted, "shape", (0,))[0]) != section_cap:
        section_skip_wasted = np.zeros(section_cap, dtype=np.bool_)
        buf["section_skip_wasted"] = section_skip_wasted
    else:
        section_skip_wasted[:] = False

    return fever_mask, section_start, section_forced, section_fill_penalty, section_skip_wasted


def _compute_force_greats_timeline(
    timestamps,
    great_candidate_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes,
    last_note_time,
    force_counts,
    *,
    clamp_base_notes_nonnegative,
    clamp_forced_to_section_notes,
    use_forced_great_timing,
):
    forced_arr = np.asarray(force_counts, dtype=np.int32) if force_counts else np.zeros(0, dtype=np.int32)
    fever_mask_buffer, section_start, section_forced, section_fill_penalty, section_skip_wasted = (
        _get_fg_timeline_buffers(int(total_notes))
    )

    (
        fever_mask_head_view,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_count,
    ) = calculate_force_greats_timeline_indices(
        timestamps,
        great_candidate_timestamps,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
        forced_arr,
        int(forced_arr.shape[0]),
        bool(clamp_base_notes_nonnegative),
        bool(clamp_forced_to_section_notes),
        bool(use_forced_great_timing),
        fever_mask_buffer,
        section_start,
        section_forced,
        section_fill_penalty,
        section_skip_wasted,
    )

    section_details = []
    for i in range(int(section_count)):
        base_notes = int(non_fever_base) - 1 if i == 0 else int(non_fever_base)
        if clamp_base_notes_nonnegative:
            base_notes = max(0, int(base_notes))
        notes_to_fill = int(base_notes) + int(section_fill_penalty[i])

        section_details.append(
            {
                "start_idx": int(section_start[i]),
                "forced": int(section_forced[i]),
                "fill_penalty_notes": int(section_fill_penalty[i]),
                "skip_wasted": bool(section_skip_wasted[i]),
                "notes": int(notes_to_fill),
            }
        )

    return (
        fever_mask_head_view.copy(),
        int(count_body_fever),
        int(count_body_normal),
        int(non_fever_base),
        section_details,
    )


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
    song_meta = extract_song_meta(calc_song)
    primary = song_meta.primary_color
    secondary = song_meta.secondary_color

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


def score_response_surface_base_exact(
    surface: Any,
    *,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
) -> int:
    head_len = min(max(0, int(total_notes)), 100)
    body_total = max(0, int(total_notes) - 100)
    body_fever = safe_int(getattr(surface, "body_fever", 0), 0)
    if body_fever < 0 or body_fever > body_total:
        raise ValueError("FG response surface body fever count exceeds song body note count")

    base_value = float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor)
    combo_f = float(combo_mul)
    fever_f = float(fever_mul)
    combo_val = floor(base_value * combo_f)
    fever_val = floor(base_value * combo_f * fever_f)
    body_normal = body_total - body_fever
    score = (int(body_fever) * int(fever_val)) + (int(body_normal) * int(combo_val))

    factor = (combo_f - 1.0) * base_value / 100.0
    fever_words = (
        safe_int(getattr(surface, "fever0", 0), 0),
        safe_int(getattr(surface, "fever1", 0), 0),
        safe_int(getattr(surface, "fever2", 0), 0),
        safe_int(getattr(surface, "fever3", 0), 0),
    )
    for i in range(head_len):
        word_idx = i // 32
        bit_idx = i % 32
        ramp_val = base_value + (float(i + 1) * factor)
        is_fever = ((int(fever_words[word_idx]) >> int(bit_idx)) & 1) != 0
        score += floor(ramp_val * fever_f) if is_fever else floor(ramp_val)
    return int(score)


def score_force_greats_surface_base_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    surface: Any,
) -> int | None:
    """
    Exact base-score replay for a solved FG response surface.

    The response surface already owns the exact fever timeline, so this path scores
    that canonical surface directly instead of rebuilding the same timeline from
    forced counts.
    """
    if not stats or not calc_song:
        return None
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    song_inputs = extract_fg_song_inputs(calc_song)
    if song_inputs.total_notes <= 0:
        return None

    primary_val = safe_int(stats.get(song_inputs.primary_color, 0), 0)
    secondary_val = safe_int(stats.get(song_inputs.secondary_color, 0), 0)
    factors = resolve_stat_factors(stats, ref_arrays)
    return int(
        score_response_surface_base_exact(
            surface,
            total_notes=int(song_inputs.total_notes),
            primary_val=int(primary_val),
            secondary_val=int(secondary_val),
            pp_factor=float(factors.pp_factor),
            combo_mul=float(factors.combo_mul),
            fever_mul=float(factors.fever_mul),
        )
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

    song_inputs = extract_fg_song_inputs(calc_song)
    if song_inputs.total_notes <= 0:
        return None

    primary_val = safe_int(stats.get(song_inputs.primary_color, 0), 0)
    secondary_val = safe_int(stats.get(song_inputs.secondary_color, 0), 0)
    factors = resolve_stat_factors(stats, ref_arrays)
    single_color = is_single_color_song(song_inputs.primary_color, song_inputs.secondary_color)
    base_value = float((primary_val * 2) + secondary_val) + float(factors.pp_factor)
    penalty_table, body_penalty, combo_value = build_penalty_table_and_body(
        base_value=float(base_value),
        combo_mul=float(factors.combo_mul),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
        single_color=bool(single_color),
    )

    force_counts = list(forced_counts or [])
    (
        fever_mask_head,
        count_body_fever,
        count_body_normal,
        non_fever_base,
        section_details,
    ) = _compute_force_greats_timeline(
        song_inputs.timestamps,
        song_inputs.great_candidates,
        song_inputs.total_notes,
        factors.fever_fill_rate,
        factors.fever_time_stat,
        song_inputs.long_notes,
        song_inputs.last_note_time,
        force_counts,
        clamp_base_notes_nonnegative=True,
        clamp_forced_to_section_notes=True,
        use_forced_great_timing=song_inputs.use_forced_great_timing,
    )

    base_score = calculate_score_exact(
        base_value,
        float(factors.combo_mul),
        float(factors.fever_mul),
        fever_mask_head,
        int(count_body_fever),
        int(count_body_normal),
    )

    total_score_penalty, total_fill_penalty, penalty_analysis = accumulate_fg_penalties(
        section_details=section_details,
        penalty_table=penalty_table,
        body_penalty=body_penalty,
        combo_value=combo_value,
    )
    return build_fg_result_dict(
        base_score=int(base_score),
        total_score_penalty=int(total_score_penalty),
        total_fill_penalty=int(total_fill_penalty),
        section_details=section_details,
        config_counts=force_counts,
        penalty_analysis=penalty_analysis,
        non_fever_base=int(non_fever_base),
    )
