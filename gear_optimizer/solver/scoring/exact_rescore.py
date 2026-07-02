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
from ..score_math import lookup_reference_py
from .fg_policy import (
    accumulate_fg_penalties,
    build_fg_result_dict,
    build_penalty_table_and_body,
    compute_great_penalty_base,
    extract_fg_song_inputs,
    extract_song_meta,
    is_single_color_song,
    resolve_stat_factors,
)


_FG_TIMELINE_TLS = threading.local()

# Base timeline-trace memo: the reconstructed trace is a pure function of
# (frontier payload cache_key, FT cell, FF cell, winning pool row) -- stats enter only
# through those. The cache_key is content-addressed (song + ref axes + cache version),
# so entries can never alias across songs or ref tables. Memoized values are kept
# pristine; every hand-out is a fresh copy because callers graft the per-note dicts
# into mutable details payloads.
_TIMELINE_TRACE_MEMO: dict[tuple, dict[str, Any]] = {}
_TIMELINE_TRACE_MEMO_MAX = 4096


def _copy_timeline_trace_meta(meta: dict[str, Any]) -> dict[str, Any]:
    out = dict(meta)
    out["frontier_trace"] = [dict(row) for row in meta["frontier_trace"]]
    out["response_surface"] = list(meta["response_surface"])
    return out


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
    perfect_candidate_timestamps,
    great_candidate_timestamps,
    perfect_floor_timestamps,
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
        perfect_candidate_timestamps,
        great_candidate_timestamps,
        perfect_floor_timestamps,
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

    total_head = 0
    combo_slope = (combo_f - 1.0) / 100.0
    for i, is_fever in enumerate(fever_mask_head):
        scaling = (combo_slope * float(i + 1)) + 1.0
        perfect_value = base_f * scaling
        total_head += floor(perfect_value * fever_f) if bool(is_fever) else floor(perfect_value)

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
) -> int:
    return int(score_stats_exact_batch([stats], calc_song, ref_arrays)[0])


def score_stats_exact_with_timeline_trace(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(stats, Mapping) or not stats:
        return {"score": 0, "TimelineFrontier": {"frontier_trace": []}}

    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps")
    if timestamps is None:
        timestamps = song_data.get("timestamps", ())
    total_notes = int(len(timestamps))
    if total_notes <= 0:
        return {"score": 0, "TimelineFrontier": {"frontier_trace": []}}

    from ..taichi_gem.api.timeline import load_timeline_frontier_payload

    frontier_refs = _frontier_replay_refs(ref_arrays)
    frontier_result = load_timeline_frontier_payload(song_dict, frontier_refs)
    payload = frontier_result.payload
    song_meta = extract_song_meta(song_dict)
    (
        primary_val,
        secondary_val,
        pp_factor,
        combo_mul,
        fever_mul,
        ft_idx,
        ff_idx,
    ) = _score_stat_inputs(stats, frontier_refs, song_meta.primary_color, song_meta.secondary_color)
    score, pool_idx = _score_timeline_frontier_payload_vectorized_result(
        payload=payload,
        total_notes=int(total_notes),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
        pp_factor=float(pp_factor),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        ft_idx=int(ft_idx),
        ff_idx=int(ff_idx),
    )
    ft_i = max(0, min(int(ft_idx), TOTAL_ROWS))
    ff_i = max(0, min(int(ff_idx), TOTAL_ROWS))
    memo_key = (frontier_result.cache_key, ft_i, ff_i, int(pool_idx))
    frontier_meta = _TIMELINE_TRACE_MEMO.get(memo_key)
    if frontier_meta is None:
        frontier_meta = _timeline_trace_for_payload_surface(
            payload=payload,
            pool_idx=int(pool_idx),
            total_notes=int(total_notes),
            ft_idx=int(ft_idx),
            ff_idx=int(ff_idx),
            calc_song=song_dict,
            ref_arrays=frontier_refs,
        )
        while len(_TIMELINE_TRACE_MEMO) >= _TIMELINE_TRACE_MEMO_MAX:
            _TIMELINE_TRACE_MEMO.pop(next(iter(_TIMELINE_TRACE_MEMO)))
        _TIMELINE_TRACE_MEMO[memo_key] = frontier_meta
    return {"score": int(score), "TimelineFrontier": _copy_timeline_trace_meta(frontier_meta)}


def score_stats_exact_batch(
    stats_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> list[int]:
    if not stats_rows:
        return []

    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps")
    if timestamps is None:
        timestamps = song_data.get("timestamps", ())
    total_notes = int(len(timestamps))
    if total_notes <= 0:
        return [0 for _stats in stats_rows]

    from ..taichi_gem.api.timeline import load_timeline_frontier_payload

    frontier_refs = _frontier_replay_refs(ref_arrays)

    payload = load_timeline_frontier_payload(song_dict, frontier_refs).payload
    song_meta = extract_song_meta(song_dict)
    scores: list[int] = []
    for stats in stats_rows:
        (
            primary_val,
            secondary_val,
            pp_factor,
            combo_mul,
            fever_mul,
            ft_idx,
            ff_idx,
        ) = _score_stat_inputs(stats, frontier_refs, song_meta.primary_color, song_meta.secondary_color)
        scores.append(
            _score_timeline_frontier_payload_vectorized(
                payload=payload,
                total_notes=int(total_notes),
                primary_val=int(primary_val),
                secondary_val=int(secondary_val),
                pp_factor=float(pp_factor),
                combo_mul=float(combo_mul),
                fever_mul=float(fever_mul),
                ft_idx=int(ft_idx),
                ff_idx=int(ff_idx),
            )
        )
    return scores


def score_stats_fixed_timing_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> int:
    """Exact f64 base replay under fixed 0ms timing (see ``*_batch``)."""
    return int(score_stats_fixed_timing_exact_batch([stats], calc_song, ref_arrays)[0])


def score_stats_fixed_timing_exact_batch(
    stats_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> list[int]:
    """
    Exact f64 base replay for the PREPARED fixed/explicit-timing calc_song.

    Scores the played hit timeline materialized as ``song_data["fg_timestamps"]`` by
    ``apply_timing_envelope(mode="zero_ms", baseline_offset=T)`` (= ``chart + T``). The ``zero_ms``
    / ``T == 0`` preset leaves it == chart, so this is the deterministic chart-time fever timeline
    -- NOT the Perfect-window frontier used by ``score_stats_exact_batch``, and independent of any
    frontier payload. A raw (un-prepared) calc_song falls back to the chart.

    Thin adapter over ``score_stats_timing_exact_batch`` (the canonical explicit-timeline scorer).
    """
    if not stats_rows:
        return []
    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    hit_timestamps = song_data.get("fg_timestamps")
    if hit_timestamps is None:
        hit_timestamps = song_data.get("chart_timestamps", song_data.get("timestamps", ()))
    return score_stats_timing_exact_batch(stats_rows, song_dict, ref_arrays, hit_timestamps)


def score_stats_timing_exact_batch(
    stats_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    hit_timestamps: Any,
) -> list[int]:
    """
    Exact f64 base replay under an EXPLICIT per-note hit-time timeline.

    Generalizes the fixed-0ms (``zero_ms``) base replay: the deterministic fever timeline is
    computed from the supplied ``hit_timestamps`` (chart time + a per-note offset ``T``), not
    from chart. ``hit_timestamps == chart_timestamps`` reproduces
    ``score_stats_fixed_timing_exact_batch`` bit-for-bit -- ``zero_ms`` is the ``T == 0`` preset.

    Only the fever-window BOUNDARIES depend on the per-note offset; the fill count is
    offset-independent (see ``fg_response_scoring/fixed_timing.py``) and base scoring carries no
    greats. Song-intrinsic quantities (``total_notes``, ``Long Notes``, ``Last Note Time``) come
    from the chart, not from ``hit_timestamps`` -- ``T`` shifts the played timeline, not the song.

    ``hit_timestamps`` MUST be non-decreasing: ``calculate_fever_timeline_indices`` searches it,
    so a timing vector that reorders notes is an invalid external input and fails loud.
    """
    if not stats_rows:
        return []

    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    song_data = song_dict.get("song_data", {}) or {}
    chart = song_data.get("chart_timestamps")
    if chart is None:
        chart = song_data.get("timestamps", song_data.get("fg_timestamps", ()))
    chart = np.asarray(chart, dtype=np.float32)
    total_notes = int(chart.shape[0])
    if total_notes <= 0:
        return [0 for _stats in stats_rows]

    hits = np.asarray(hit_timestamps, dtype=np.float32)
    if int(hits.shape[0]) != total_notes:
        raise ValueError(
            "score_stats_timing_exact_batch: hit_timestamps length "
            f"{int(hits.shape[0])} != song note count {total_notes}"
        )
    if total_notes > 1 and bool(np.any(np.diff(hits) < np.float32(0.0))):
        raise ValueError(
            "score_stats_timing_exact_batch: hit_timestamps must be non-decreasing "
            "(a per-note timing offset may not reorder notes)"
        )

    metadata = song_dict.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = float(chart[-1]) if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    ft_axis = ref_arrays["Fever Time"]
    ff_axis = ref_arrays["Fever Fill Rate"]
    mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    song_meta = extract_song_meta(song_dict)
    # (FT, FF) -> deterministic fever timeline: a pure function of the cell within one
    # batch (hits/notes/long/last are batch-constant). The njit walk returns a VIEW of
    # the shared mask buffer, so the memo stores a copy.
    timeline_by_cell: dict[tuple[int, int], tuple[np.ndarray, int, int]] = {}

    scores: list[int] = []
    for stats in stats_rows:
        (
            primary_val,
            secondary_val,
            pp_factor,
            combo_mul,
            fever_mul,
            ft_idx,
            ff_idx,
        ) = _score_stat_inputs(stats, ref_arrays, song_meta.primary_color, song_meta.secondary_color)
        base_value = float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor)
        cell = (int(ft_idx), int(ff_idx))
        cached_timeline = timeline_by_cell.get(cell)
        if cached_timeline is None:
            ft_factor = lookup_reference_py(int(ft_idx), ft_axis, TOTAL_ROWS)
            ff_factor = lookup_reference_py(int(ff_idx), ff_axis, TOTAL_ROWS)
            fever_mask_head, count_body_fever, count_body_normal, _activations, _last_end = (
                calculate_fever_timeline_indices(
                    hits,
                    total_notes,
                    ff_factor,
                    ft_factor,
                    long_notes,
                    last_note_time,
                    mask_buffer,
                )
            )
            cached_timeline = (fever_mask_head.copy(), int(count_body_fever), int(count_body_normal))
            timeline_by_cell[cell] = cached_timeline
        fever_mask_head, count_body_fever, count_body_normal = cached_timeline
        scores.append(
            calculate_score_exact(
                base_value,
                float(combo_mul),
                float(fever_mul),
                fever_mask_head,
                int(count_body_fever),
                int(count_body_normal),
            )
        )
    return scores


def _frontier_replay_refs(ref_arrays: Mapping[str, Any]) -> dict[str, Any]:
    frontier_refs = dict(resolve_exact_replay_ref_arrays(ref_arrays))
    for axis in ("Fever Time", "Fever Fill Rate"):
        axis_values = np.asarray(frontier_refs.get(axis, ())).reshape(-1)
        if int(axis_values.shape[0]) < TOTAL_ROWS + 1:
            raise ValueError(f"{axis} axis must include stat rows 0..{TOTAL_ROWS}")
        frontier_refs[axis] = axis_values[: TOTAL_ROWS + 1]
    return frontier_refs


def _score_stat_inputs(
    stats: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    primary: str,
    secondary: str,
) -> tuple[int, int, float, float, float, int, int]:
    """Per-row scoring inputs.

    ``ref_arrays`` must already be resolved and ``primary``/``secondary`` extracted once
    per song -- both are row-invariant, so callers hoist them out of their row loops.
    """
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
    primary_val = safe_int(stats.get(primary, 0), 0)
    secondary_val = safe_int(stats.get(secondary, 0), 0)

    return (
        int(primary_val),
        int(secondary_val),
        float(pp_factor),
        float(combo_mul),
        float(fever_mul),
        safe_int(stats.get("Fever Time", 0), 0),
        safe_int(stats.get("Fever Fill Rate", 0), 0),
    )


def _score_surface_counts_exact(
    *,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    body_fever: int,
    body_normal: int,
    fever_words,
) -> int:
    head_len = min(max(0, int(total_notes)), 100)
    body_total = max(0, int(total_notes) - 100)
    body_fever = safe_int(body_fever, 0)
    body_normal = safe_int(body_normal, 0)
    if body_fever < 0 or body_normal < 0 or int(body_fever + body_normal) != int(body_total):
        raise ValueError("Timing surface body counts do not match song body note count")

    words = tuple(safe_int(value, 0) for value in tuple(fever_words)[:4])
    if len(words) < 4:
        words = words + (0,) * (4 - len(words))

    base_value = float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor)
    combo_f = float(combo_mul)
    fever_f = float(fever_mul)
    combo_val = floor(base_value * combo_f)
    fever_val = floor(base_value * combo_f * fever_f)
    score = (int(body_fever) * int(fever_val)) + (int(body_normal) * int(combo_val))

    combo_slope = (combo_f - 1.0) / 100.0
    for i in range(head_len):
        word_idx = i // 32
        bit_idx = i % 32
        scaling = (combo_slope * float(i + 1)) + 1.0
        perfect_value = base_value * scaling
        is_fever = ((int(words[word_idx]) >> int(bit_idx)) & 1) != 0
        score += floor(perfect_value * fever_f) if is_fever else floor(perfect_value)
    return int(score)


def _score_timeline_frontier_payload_vectorized(
    *,
    payload: Any,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    ft_idx: int,
    ff_idx: int,
) -> int:
    score, _pool_idx = _score_timeline_frontier_payload_vectorized_result(
        payload=payload,
        total_notes=int(total_notes),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
        pp_factor=float(pp_factor),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        ft_idx=int(ft_idx),
        ff_idx=int(ff_idx),
    )
    return int(score)


def _score_timeline_frontier_payload_vectorized_result(
    *,
    payload: Any,
    total_notes: int,
    primary_val: int,
    secondary_val: int,
    pp_factor: float,
    combo_mul: float,
    fever_mul: float,
    ft_idx: int,
    ff_idx: int,
) -> tuple[int, int]:
    ft_i = max(0, min(int(ft_idx), TOTAL_ROWS))
    ff_i = max(0, min(int(ff_idx), TOTAL_ROWS))
    frontier_count = int(payload.grid_frontier_count[0, ft_i, ff_i])
    if frontier_count <= 0:
        raise ValueError("Timing frontier payload has no replayable surface for the requested FT/FF cell")
    frontier_offset = int(payload.grid_frontier_offset[0, ft_i, ff_i])
    frontier_limit = int(frontier_offset + frontier_count)
    if frontier_offset < 0 or frontier_limit > int(payload.frontier_pool_used):
        raise ValueError("Timing frontier payload contains an invalid surface range")

    body_total = max(0, int(total_notes) - 100)
    body_fever = np.asarray(
        payload.grid_frontier_body_fever_pool[0, frontier_offset:frontier_limit],
        dtype=np.int64,
    )
    body_normal = np.asarray(
        payload.grid_frontier_body_normal_pool[0, frontier_offset:frontier_limit],
        dtype=np.int64,
    )
    if bool(np.any(body_fever < 0)) or bool(np.any(body_normal < 0)) or bool(
        np.any((body_fever + body_normal) != int(body_total))
    ):
        raise ValueError("Timing surface body counts do not match song body note count")

    base_value = np.float64(float((int(primary_val) * 2) + int(secondary_val)) + float(pp_factor))
    combo_f = np.float64(float(combo_mul))
    fever_f = np.float64(float(fever_mul))
    combo_val = np.int64(np.floor(base_value * combo_f))
    fever_val = np.int64(np.floor(base_value * combo_f * fever_f))
    scores = (body_fever * combo_val) + (body_normal * combo_val)
    if int(fever_val) != int(combo_val):
        scores = scores + (body_fever * (fever_val - combo_val))

    head_len = min(max(0, int(total_notes)), 100)
    combo_slope = np.float64((float(combo_f) - 1.0) / 100.0)
    if head_len > 0:
        # Vectorized head replay: the per-position f64 expressions (multiply, add,
        # floor -- same op order per lane) are elementwise-identical to the scalar
        # per-note loop this replaces, and only exact int64 additions are regrouped,
        # so every pool lane's score is bit-identical (same argmax winner).
        positions = np.arange(1, head_len + 1, dtype=np.float64)
        perfect_values = base_value * ((combo_slope * positions) + np.float64(1.0))
        normal_scores = np.floor(perfect_values).astype(np.int64)
        fever_scores = np.floor(perfect_values * fever_f).astype(np.int64)
        scores = scores + np.int64(normal_scores.sum())
        fever_delta = fever_scores - normal_scores
        if bool(np.any(fever_delta != 0)):
            words = np.asarray(
                payload.grid_frontier_masks_bits_pool[0, frontier_offset:frontier_limit, :4], dtype=np.uint64
            )
            note_idx = np.arange(head_len)
            head_bits = ((words[:, note_idx // 32] >> (note_idx % 32).astype(np.uint64)) & np.uint64(1)).astype(
                np.int64
            )
            scores = scores + (head_bits @ fever_delta)

    if int(scores.shape[0]) <= 0:
        raise ValueError("Timing frontier replay did not produce a score")
    winner_local_idx = int(np.argmax(scores))
    return int(scores[winner_local_idx]), int(frontier_offset + winner_local_idx)


def _timeline_trace_for_payload_surface(
    *,
    payload: Any,
    pool_idx: int,
    total_notes: int,
    ft_idx: int,
    ff_idx: int,
    calc_song: dict[str, Any],
    ref_arrays: Mapping[str, Any],
) -> dict[str, Any]:
    from ..taichi_gem.api.timeline import _timeline_payload_context
    from ..timeline_exact_frontier import TimelineExactSignature, reconstruct_timeline_frontier_trace

    pool_idx_i = int(pool_idx)
    if pool_idx_i < 0 or pool_idx_i >= int(payload.frontier_pool_used):
        raise ValueError("Timeline frontier winner points outside the cached surface pool")

    head_len = min(max(0, int(total_notes)), 100)
    body_fever = int(payload.grid_frontier_body_fever_pool[0, pool_idx_i])
    body_normal = int(payload.grid_frontier_body_normal_pool[0, pool_idx_i])
    words = tuple(int(payload.grid_frontier_masks_bits_pool[0, pool_idx_i, word]) for word in range(4))
    surface = TimelineExactSignature(
        head_len=int(head_len),
        head_bits=(int(words[0]), int(words[1]), int(words[2]), int(words[3])),
        body_fever=int(body_fever),
        body_normal=int(body_normal),
        fever_activations=0,
        gap=0,
    )

    ctx = _timeline_payload_context(calc_song, dict(ref_arrays), require_cached_group_payload=True)
    group_payload = ctx["group_payload"]
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32).reshape(-1)
    ft_i = max(0, min(int(ft_idx), TOTAL_ROWS))
    ff_i = max(0, min(int(ff_idx), TOTAL_ROWS))

    total_notes_i = int(ctx["total_notes"])
    long_notes_i = int(ctx["long_notes"])
    non_fever_cas = float(max(0, total_notes_i - long_notes_i)) * 0.333
    fever_time_cas = float(ctx["last_note_time"]) * 0.15 + 0.15
    fill_count = int(np.ceil(np.float32(non_fever_cas) * np.float32(ref_ff[ff_i])))
    fill_count = max(1, int(fill_count))
    d_ms = int(np.ceil(np.float32(fever_time_cas) * np.float32(ref_ft[ft_i]) * np.float32(1000.0)))
    d_ms = max(0, int(d_ms))

    trace = reconstruct_timeline_frontier_trace(
        total_notes=int(total_notes_i),
        group_starts=np.asarray(group_payload["group_starts"], dtype=np.int32),
        group_ends=np.asarray(group_payload["group_ends"], dtype=np.int32),
        group_base_t_ms=np.asarray(group_payload["group_base_t_ms"], dtype=np.int32),
        group_low_ms=np.asarray(group_payload["group_low_ms"], dtype=np.int32),
        group_high_ms=np.asarray(group_payload["group_high_ms"], dtype=np.int32),
        note_group_idx=np.asarray(group_payload["note_group_idx"], dtype=np.int32),
        fill_count=int(fill_count),
        d_ms=int(d_ms),
        target_surface=surface,
    )
    return {
        "frontier_trace": list(trace),
        "response_surface": [int(words[0]), int(words[1]), int(words[2]), int(words[3]), body_fever, body_normal],
        "frontier_pool_index": int(pool_idx_i),
        "frontier_first_surfaces": int(payload.grid_frontier_count[0, ft_i, ff_i]),
        "activation_judgment": "perfect",
        "fill_count": int(fill_count),
        "fever_duration_ms": int(d_ms),
    }


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
    body_total = max(0, int(total_notes) - 100)
    body_fever = safe_int(getattr(surface, "body_fever", 0), 0)
    if body_fever < 0 or body_fever > body_total:
        raise ValueError("FG response surface body fever count exceeds song body note count")

    return _score_surface_counts_exact(
        total_notes=int(total_notes),
        primary_val=int(primary_val),
        secondary_val=int(secondary_val),
        pp_factor=float(pp_factor),
        combo_mul=float(combo_mul),
        fever_mul=float(fever_mul),
        body_fever=int(body_fever),
        body_normal=int(body_total - body_fever),
        fever_words=(
            safe_int(getattr(surface, "fever0", 0), 0),
            safe_int(getattr(surface, "fever1", 0), 0),
            safe_int(getattr(surface, "fever2", 0), 0),
            safe_int(getattr(surface, "fever3", 0), 0),
        ),
    )


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


def score_force_greats_response_surface_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    surface: Any,
) -> int | None:
    """
    Exact f64 replay for a solved FG response surface.

    The response surface is the canonical representation for timeline-frontier
    FG because it can encode Fever+Great overlap; forced-count configs cannot.
    """
    if not stats or not calc_song:
        return None
    ref_arrays = resolve_exact_replay_ref_arrays(ref_arrays)
    song_inputs = extract_fg_song_inputs(calc_song)
    total_notes = int(song_inputs.total_notes)
    if total_notes <= 0:
        return None

    head_len = min(total_notes, 100)
    body_total = max(0, total_notes - 100)
    body_fever = safe_int(getattr(surface, "body_fever", 0), 0)
    body_great = safe_int(getattr(surface, "body_great", 0), 0)
    body_fever_great = safe_int(getattr(surface, "body_fever_great", 0), 0)
    if (
        body_fever < 0
        or body_great < 0
        or body_fever_great < 0
        or body_fever > body_total
        or body_great > body_total
        or body_fever_great > body_fever
        or body_fever_great > body_great
        or body_fever + body_great - body_fever_great > body_total
    ):
        raise ValueError("FG response surface body categories do not match song body note count")

    primary_val = safe_int(stats.get(song_inputs.primary_color, 0), 0)
    secondary_val = safe_int(stats.get(song_inputs.secondary_color, 0), 0)
    factors = resolve_stat_factors(stats, ref_arrays)
    single_color = is_single_color_song(song_inputs.primary_color, song_inputs.secondary_color)
    base_value = float((primary_val * 2) + secondary_val) + float(factors.pp_factor)
    combo_f = float(factors.combo_mul)
    fever_f = float(factors.fever_mul)
    combo_val = floor(base_value * combo_f)
    fever_val = floor(base_value * combo_f * fever_f)

    great_head_base = compute_great_penalty_base(primary_val, secondary_val, single_color=bool(single_color))

    body_normal_great = int(body_great - body_fever_great)
    body_normal = int(body_total - body_fever)
    if body_normal - body_normal_great < 0:
        raise ValueError("FG response surface body normal category is negative")

    score = 0
    score += int(body_fever) * int(fever_val)
    score += int(body_normal) * int(combo_val)
    great_base = float(great_head_base)
    body_normal_penalty = max(0, int(combo_val) - int(floor(great_base * combo_f)))
    body_fever_penalty = max(0, int(fever_val) - int(floor(great_base * combo_f * fever_f)))
    score -= int(body_normal_great) * int(body_normal_penalty)
    score -= int(body_fever_great) * int(body_fever_penalty)

    fever_words = (
        safe_int(getattr(surface, "fever0", 0), 0),
        safe_int(getattr(surface, "fever1", 0), 0),
        safe_int(getattr(surface, "fever2", 0), 0),
        safe_int(getattr(surface, "fever3", 0), 0),
    )
    great_words = (
        safe_int(getattr(surface, "great0", 0), 0),
        safe_int(getattr(surface, "great1", 0), 0),
        safe_int(getattr(surface, "great2", 0), 0),
        safe_int(getattr(surface, "great3", 0), 0),
    )
    combo_slope = (combo_f - 1.0) / 100.0
    for i in range(head_len):
        word_idx = i // 32
        bit_idx = i % 32
        is_fever = ((int(fever_words[word_idx]) >> int(bit_idx)) & 1) != 0
        is_great = ((int(great_words[word_idx]) >> int(bit_idx)) & 1) != 0
        scaling = (combo_slope * float(i + 1)) + 1.0
        perfect_value = base_value * scaling
        perfect_score = floor(perfect_value * fever_f) if is_fever else floor(perfect_value)
        if is_great:
            great_score = float(great_head_base) * scaling
            great_score = floor(great_score * fever_f) if is_fever else floor(great_score)
            perfect_score -= max(0, int(perfect_score) - int(great_score))
        score += int(perfect_score)
    return int(score)


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
        song_inputs.perfect_candidates,
        song_inputs.great_candidates,
        song_inputs.perfect_floor,
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
