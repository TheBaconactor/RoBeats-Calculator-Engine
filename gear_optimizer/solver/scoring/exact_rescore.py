"""
CPU exact score replay for callers that still pass the old calc_song dict and ref-array dicts.

The scores are the game's exact visible scores (float64 like the game's Luau numbers), not the
optimizer's float32 GPU search scores. The math lives in the rewrite's core (gear_optimizer.score and
gear_optimizer.timing); this module adapts the old inputs to it until its callers are rewritten.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ... import score as core_score
from ...core.constants import FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE
from ...gamedata import CURVE_STATS, MAX_STAT, STATS, StatCurves
from ...helpers.song_helpers.ref_array_builder import resolve_exact_replay_ref_arrays
from ...timing import fixed_timeline_cell
from .fg_policy import extract_fg_song_inputs

# Base timeline-trace memo: the reconstructed trace is a pure function of
# (frontier payload cache_key, FT cell, FF cell, winning pool row) -- stats enter only
# through those. The cache_key is content-addressed (song + ref axes + cache version),
# so entries can never alias across songs or ref tables. Memoized values are kept
# pristine; every hand-out is a fresh copy because callers graft the per-note dicts
# into mutable details payloads.
# Reuse is intra-song only (the key carries the song cache_key). The cap must exceed one
# pass's distinct keys -- an on-demand tier build inserts at most 7 tiers x 51 rows, and the
# persistence authority pass re-requests the canonicalize pass's keys (<= a few x
# LOADOUTS_PER_SONG_LIMIT entries) -- or FIFO eviction turns every second-pass lookup into a miss.
_TIMELINE_TRACE_MEMO: dict[tuple, dict[str, Any]] = {}
_TIMELINE_TRACE_MEMO_MAX = 1024


def _copy_timeline_trace_meta(meta: dict[str, Any]) -> dict[str, Any]:
    out = dict(meta)
    out["frontier_trace"] = [dict(source) for source in meta["frontier_trace"]]
    out["response_surface"] = list(meta["response_surface"])
    return out


def _frontier_replay_refs(ref_arrays: Mapping[str, Any]) -> dict[str, Any]:
    frontier_refs = dict(resolve_exact_replay_ref_arrays(ref_arrays))
    for axis in ("Fever Time", "Fever Fill Rate"):
        axis_values = np.asarray(frontier_refs.get(axis, ())).reshape(-1)
        if int(axis_values.shape[0]) < MAX_STAT + 1:
            raise ValueError(f"{axis} axis must include stat rows 0..{MAX_STAT}")
        frontier_refs[axis] = axis_values[: MAX_STAT + 1]
    return frontier_refs


def _curves(ref_arrays: Mapping[str, Any]) -> StatCurves:
    return StatCurves(
        values={
            stat: np.asarray(ref_arrays[stat], dtype=np.float64).reshape(-1)[: MAX_STAT + 1] for stat in CURVE_STATS
        }
    )


def _stats_row(stats: Mapping[str, Any]) -> dict[str, int]:
    return {stat: int(stats.get(stat) or 0) for stat in STATS}


def _song_colors(calc_song: Mapping[str, Any]) -> tuple[str, str]:
    metadata = calc_song.get("metadata") or {}
    return str(metadata.get("Primary Color") or ""), str(metadata.get("Secondary Color") or "")


def _chart_timestamps(calc_song: Mapping[str, Any]) -> np.ndarray:
    song_data = calc_song.get("song_data") or {}
    timestamps = song_data.get("chart_timestamps")
    if timestamps is None:
        timestamps = song_data.get("timestamps")
    chart = np.asarray(timestamps if timestamps is not None else (), dtype=np.float32)
    if chart.shape[0] <= 0:
        raise ValueError("exact replay needs a chart with notes")
    return chart


def _best_timeline_score(payload, curves, primary, secondary, stats, total_notes) -> tuple[int, int]:
    """Best score over the stats' timing frontier cell and the winning surface's pool index."""
    f = core_score.factors(stats, curves, primary, secondary)
    cell, offset = core_score.timeline_cell(payload, f.fever_time_row, f.fever_fill_row, MAX_STAT)
    best, index = core_score.best_timeline_score(f, cell, total_notes)
    return best, offset + index


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
    from ..taichi_gem.api.timeline import load_timeline_frontier_payload

    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    total_notes = int(_chart_timestamps(song_dict).shape[0])
    frontier_refs = _frontier_replay_refs(ref_arrays)
    frontier_result = load_timeline_frontier_payload(song_dict, frontier_refs)
    payload = frontier_result.payload
    primary, secondary = _song_colors(song_dict)
    row = _stats_row(stats)
    best_score, pool_idx = _best_timeline_score(
        payload, _curves(frontier_refs), primary, secondary, row, total_notes
    )
    ft_i = max(0, min(row["Fever Time"], MAX_STAT))
    ff_i = max(0, min(row["Fever Fill Rate"], MAX_STAT))
    memo_key = (frontier_result.cache_key, ft_i, ff_i, int(pool_idx))
    frontier_meta = _TIMELINE_TRACE_MEMO.get(memo_key)
    if frontier_meta is None:
        frontier_meta = _timeline_trace_for_payload_surface(
            payload=payload,
            pool_idx=int(pool_idx),
            total_notes=total_notes,
            ft_idx=ft_i,
            ff_idx=ff_i,
            calc_song=song_dict,
            ref_arrays=frontier_refs,
        )
        while len(_TIMELINE_TRACE_MEMO) >= _TIMELINE_TRACE_MEMO_MAX:
            _TIMELINE_TRACE_MEMO.pop(next(iter(_TIMELINE_TRACE_MEMO)))
        _TIMELINE_TRACE_MEMO[memo_key] = frontier_meta
    return {"score": int(best_score), "TimelineFrontier": _copy_timeline_trace_meta(frontier_meta)}


def score_stats_exact_batch(
    stats_rows: Sequence[Mapping[str, Any]],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> list[int]:
    """Exact Perfect-window base scores: the best surface of each row's timing frontier cell."""
    if not stats_rows:
        return []
    from ..taichi_gem.api.timeline import load_timeline_frontier_payload

    song_dict = calc_song if isinstance(calc_song, dict) else dict(calc_song)
    total_notes = int(_chart_timestamps(song_dict).shape[0])
    frontier_refs = _frontier_replay_refs(ref_arrays)
    payload = load_timeline_frontier_payload(song_dict, frontier_refs).payload
    curves = _curves(frontier_refs)
    primary, secondary = _song_colors(song_dict)
    return [
        _best_timeline_score(payload, curves, primary, secondary, _stats_row(stats), total_notes)[0]
        for stats in stats_rows
    ]


def score_stats_fixed_timing_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> int:
    """Exact f64 base replay under fixed 0ms timing (see ``*_batch``)."""
    return int(score_stats_fixed_timing_exact_batch([stats], calc_song, ref_arrays)[0])


def score_stats_fixed_timing_exact_batch(
    stats_rows: Sequence[Mapping[str, Any]],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
) -> list[int]:
    """
    Exact f64 base replay for the PREPARED fixed/explicit-timing calc_song.

    Scores the played hit timeline materialized as ``song_data["fg_timestamps"]`` by
    ``apply_timing_envelope(mode="zero_ms", baseline_offset=T)`` (= ``chart + T``). The ``zero_ms``
    / ``T == 0`` preset leaves it == chart, so this is the deterministic chart-time fever timeline
    -- NOT the Perfect-window frontier used by ``score_stats_exact_batch``, and independent of any
    frontier payload. A calc_song without ``fg_timestamps`` scores the chart times.
    """
    song_data = calc_song.get("song_data") or {}
    hit_timestamps = song_data.get("fg_timestamps")
    if hit_timestamps is None:
        hit_timestamps = _chart_timestamps(calc_song)
    return score_stats_timing_exact_batch(stats_rows, calc_song, ref_arrays, hit_timestamps)


def score_stats_timing_exact_batch(
    stats_rows: Sequence[Mapping[str, Any]],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    hit_timestamps: Any,
) -> list[int]:
    """
    Exact f64 base replay under an EXPLICIT per-note hit-time timeline (chart time + a per-note offset).

    Only the fever-window boundaries depend on the hit times; Long Notes and Last Note Time are the
    chart's. ``hit_timestamps`` must give every note a time, in note order.
    """
    if not stats_rows:
        return []
    chart = _chart_timestamps(calc_song)
    hits = np.asarray(hit_timestamps, dtype=np.float32)
    if hits.shape != chart.shape:
        raise ValueError(
            f"score_stats_timing_exact_batch: hit_timestamps length {hits.shape[0]} != song note count {chart.shape[0]}"
        )
    if hits.shape[0] > 1 and bool(np.any(np.diff(hits) < 0)):
        raise ValueError(
            "score_stats_timing_exact_batch: hit_timestamps must be non-decreasing "
            "(a per-note timing offset may not reorder notes)"
        )
    metadata = calc_song.get("metadata") or {}
    long_notes = int(metadata["Long Notes"])
    last_note_time = float(metadata["Last Note Time"])
    curves = _curves(resolve_exact_replay_ref_arrays(ref_arrays))
    primary, secondary = _song_colors(calc_song)
    cells: dict[tuple[int, int], core_score.TimelineCell] = {}
    scores: list[int] = []
    for stats in stats_rows:
        f = core_score.factors(_stats_row(stats), curves, primary, secondary)
        key = (f.fever_time_row, f.fever_fill_row)
        cell = cells.get(key)
        if cell is None:
            cell = cells[key] = fixed_timeline_cell(
                hits,
                long_notes=long_notes,
                last_note_time=last_note_time,
                fill_factor=curves.factor("Fever Fill Rate", f.fever_fill_row),
                time_factor=curves.factor("Fever Time", f.fever_time_row),
            )
        scores.append(core_score.best_timeline_score(f, cell, int(chart.shape[0]))[0])
    return scores


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
    from ..fg_response_scoring.physical_replay import validate_base_physical_replay
    from ..timeline_exact_frontier import reconstruct_timeline_physical_trace

    pool_idx_i = int(pool_idx)
    if pool_idx_i < 0 or pool_idx_i >= int(payload.frontier_pool_used):
        raise ValueError("Timeline frontier winner points outside the cached surface pool")

    body_fever = int(payload.grid_frontier_body_fever_pool[0, pool_idx_i])
    body_normal = int(payload.grid_frontier_body_normal_pool[0, pool_idx_i])
    words = tuple(int(payload.grid_frontier_masks_bits_pool[0, pool_idx_i, word]) for word in range(4))
    song_inputs = extract_fg_song_inputs(calc_song)
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32).reshape(-1)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32).reshape(-1)

    total_notes_i = int(song_inputs.total_notes)
    long_notes_i = int(song_inputs.long_notes)
    non_fever_cas = float(max(0, total_notes_i - long_notes_i)) * float(FEVER_FILL_BASE_RATE)
    fever_time_cas = float(song_inputs.last_note_time) * FEVER_TIME_SCALE + FEVER_TIME_OFFSET
    raw_fever_fill = float(non_fever_cas) * float(ref_ff[ff_idx])
    fill_count = int(np.ceil(raw_fever_fill))
    fill_count = max(1, int(fill_count))
    real_fever_time = max(0.0, float(fever_time_cas) * float(ref_ft[ft_idx]))

    trace = reconstruct_timeline_physical_trace(
        head_bits=(int(words[0]), int(words[1]), int(words[2]), int(words[3])),
        body_fever=int(body_fever),
        timestamps=song_inputs.timestamps,
        perfect_candidate_timestamps=song_inputs.perfect_candidates,
        great_candidate_timestamps=song_inputs.great_candidates,
        perfect_floor_timestamps=song_inputs.perfect_floor,
        great_floor_timestamps=song_inputs.great_floor,
        lanes=song_inputs.lanes,
        raw_fever_fill=float(raw_fever_fill),
        real_fever_time=float(real_fever_time),
    )
    song_data = calc_song.get("song_data")
    if not isinstance(song_data, Mapping):
        raise ValueError("Timeline frontier trace requires complete chart geometry")
    response_surface = [
        int(words[0]),
        int(words[1]),
        int(words[2]),
        int(words[3]),
        int(body_fever),
        int(body_normal),
    ]
    validate_base_physical_replay(
        frontier_trace=trace,
        response_surface=response_surface,
        timestamps=song_data.get("timestamps", ()),
        note_types=song_data.get("note_types", ()),
        lanes=song_data.get("lanes", ()),
        fill_count=int(fill_count),
        fever_duration_ms=float(real_fever_time) * 1000.0,
    )
    return {
        "frontier_trace": [dict(section) for section in trace],
        "response_surface": response_surface,
        "frontier_pool_index": int(pool_idx_i),
        "frontier_first_surfaces": int(payload.grid_frontier_count[0, ft_idx, ff_idx]),
        "activation_judgment": "perfect",
        "fill_count": int(fill_count),
        "fever_duration_ms": float(real_fever_time) * 1000.0,
    }


def score_force_greats_response_surface_exact(
    stats: Mapping[str, Any],
    calc_song: Mapping[str, Any],
    ref_arrays: Mapping[str, Any],
    surface: Any,
) -> int:
    """
    Exact f64 replay for a solved FG response surface.

    The response surface is the canonical representation for timeline-frontier
    FG because it can encode Fever+Great overlap; forced-count configs cannot.
    """
    if not stats:
        raise ValueError("FG response surface replay needs stats")
    total_notes = int(_chart_timestamps(calc_song).shape[0])
    primary, secondary = _song_colors(calc_song)
    curves = _curves(resolve_exact_replay_ref_arrays(ref_arrays))
    f = core_score.factors(_stats_row(stats), curves, primary, secondary)
    return core_score.fg_surface_score(f, surface, total_notes)
