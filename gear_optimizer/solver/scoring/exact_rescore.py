"""
CPU exact score replay of a timed song.

The scores are the game's exact visible scores (float64 like the game's Luau numbers), not the
optimizer's float32 GPU search scores. The math lives in the rewrite's core (gear_optimizer.score and
gear_optimizer.timing); this module adds the timing frontier lookup and the base trace reconstruction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ... import score as core_score
from gear_optimizer.rules import MAX_STAT
from ...gamedata import STATS, StatCurves
from ...timing import fixed_timeline_cell
from ..timing_envelope import TimedSong, fever_fill_raw, fever_window_times

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


def _stats_row(stats: Mapping[str, Any]) -> dict[str, int]:
    return {stat: int(stats.get(stat) or 0) for stat in STATS}


def _best_timeline_score(payload, curves, primary, secondary, stats, total_notes) -> tuple[int, int]:
    """Best score over the stats' timing frontier cell and the winning surface's pool index."""
    f = core_score.factors(stats, curves, primary, secondary)
    cell, offset = core_score.timeline_cell(payload, f.fever_time_row, f.fever_fill_row, MAX_STAT)
    best, index = core_score.best_timeline_score(f, cell, total_notes)
    return best, offset + index


def score_stats_exact(
    stats: Mapping[str, Any],
    song: TimedSong,
    curves: StatCurves,
) -> int:
    return int(score_stats_exact_batch([stats], song, curves)[0])


def score_stats_exact_with_timeline_trace(
    stats: Mapping[str, Any],
    song: TimedSong,
    curves: StatCurves,
) -> dict[str, Any]:
    from ..taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    total_notes = song.chart.total_notes
    frontier_result = build_or_load_timeline_frontier_payload(song, curves)
    payload = frontier_result.payload
    primary, secondary = song.chart.primary, song.chart.secondary
    row = _stats_row(stats)
    best_score, pool_idx = _best_timeline_score(
        payload, curves, primary, secondary, row, total_notes
    )
    ft_i = max(0, min(row["Fever Time"], MAX_STAT))
    ff_i = max(0, min(row["Fever Fill Rate"], MAX_STAT))
    memo_key = (frontier_result.cache_key, ft_i, ff_i, int(pool_idx))
    frontier_meta = _TIMELINE_TRACE_MEMO.get(memo_key)
    if frontier_meta is None:
        frontier_meta = _timeline_trace_for_payload_surface(
            payload=payload,
            pool_idx=int(pool_idx),
            ft_idx=ft_i,
            ff_idx=ff_i,
            song=song,
            curves=curves,
        )
        while len(_TIMELINE_TRACE_MEMO) >= _TIMELINE_TRACE_MEMO_MAX:
            _TIMELINE_TRACE_MEMO.pop(next(iter(_TIMELINE_TRACE_MEMO)))
        _TIMELINE_TRACE_MEMO[memo_key] = frontier_meta
    return {"score": int(best_score), "TimelineFrontier": _copy_timeline_trace_meta(frontier_meta)}


def score_stats_exact_batch(
    stats_rows: Sequence[Mapping[str, Any]],
    song: TimedSong,
    curves: StatCurves,
) -> list[int]:
    """Exact Perfect-window base scores: the best surface of each row's timing frontier cell."""
    if not stats_rows:
        return []
    from ..taichi_gem.api.timeline import build_or_load_timeline_frontier_payload

    total_notes = song.chart.total_notes
    payload = build_or_load_timeline_frontier_payload(song, curves).payload
    primary, secondary = song.chart.primary, song.chart.secondary
    return [
        _best_timeline_score(payload, curves, primary, secondary, _stats_row(stats), total_notes)[0]
        for stats in stats_rows
    ]


def score_base_exact_batch(
    stats_rows: Sequence[Mapping[str, Any]],
    song: TimedSong,
    curves: StatCurves,
) -> list[int]:
    """Exact base scores at the song's timing: zero_ms on its hit timeline, perfect_window on the Perfect-window
    timing frontier."""
    if song.mode == "zero_ms":
        return score_stats_fixed_timing_exact_batch(stats_rows, song, curves)
    return score_stats_exact_batch(stats_rows, song, curves)


def score_stats_fixed_timing_exact(
    stats: Mapping[str, Any],
    song: TimedSong,
    curves: StatCurves,
) -> int:
    """Exact f64 base replay under fixed 0ms timing (see ``*_batch``)."""
    return int(score_stats_fixed_timing_exact_batch([stats], song, curves)[0])


def score_stats_fixed_timing_exact_batch(
    stats_rows: Sequence[Mapping[str, Any]],
    song: TimedSong,
    curves: StatCurves,
) -> list[int]:
    """
    Exact f64 base replay at the song's hit timeline (fixed timing).

    Scores ``song.hit_timestamps``: the chart itself, or ``chart + T`` for a custom zero_ms offset.
    This is the deterministic hit-time fever timeline -- NOT the Perfect-window frontier used by
    ``score_stats_exact_batch`` -- and independent of any frontier payload.
    """
    return score_stats_timing_exact_batch(stats_rows, song, curves, song.hit_timestamps)


def score_stats_timing_exact_batch(
    stats_rows: Sequence[Mapping[str, Any]],
    song: TimedSong,
    curves: StatCurves,
    hit_timestamps: Any,
) -> list[int]:
    """
    Exact f64 base replay under an EXPLICIT per-note hit-time timeline (chart time + a per-note offset).

    Only the fever-window boundaries depend on the hit times; Long Notes and Last Note Time are the
    chart's. ``hit_timestamps`` must give every note a time, in note order.
    """
    if not stats_rows:
        return []
    chart = song.chart.timestamps
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
    long_notes = song.chart.long_notes
    last_note_time = song.chart.last_note_time
    primary, secondary = song.chart.primary, song.chart.secondary
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
    ft_idx: int,
    ff_idx: int,
    song: TimedSong,
    curves: StatCurves,
) -> dict[str, Any]:
    from ..fg_response_scoring.physical_replay import validate_base_physical_replay
    from ..timeline_exact_frontier import reconstruct_timeline_physical_trace

    pool_idx_i = int(pool_idx)
    if pool_idx_i < 0 or pool_idx_i >= int(payload.frontier_pool_used):
        raise ValueError("Timeline frontier winner points outside the cached surface pool")

    body_fever = int(payload.grid_frontier_body_fever_pool[0, pool_idx_i])
    body_normal = int(payload.grid_frontier_body_normal_pool[0, pool_idx_i])
    words = tuple(int(payload.grid_frontier_masks_bits_pool[0, pool_idx_i, word]) for word in range(4))
    song_inputs = song.fg_inputs
    ref_ft = curves.f32["Fever Time"]
    ref_ff = curves.f32["Fever Fill Rate"]

    total_notes_i = int(song_inputs.total_notes)
    long_notes_i = int(song_inputs.long_notes)
    raw_fever_fill = float(fever_fill_raw(max(0, total_notes_i - long_notes_i), ref_ff, song.mode)[ff_idx])
    fill_count = int(np.ceil(raw_fever_fill))
    fill_count = max(1, int(fill_count))
    real_fever_time = float(fever_window_times(song_inputs.last_note_time, ref_ft[ft_idx : ft_idx + 1], song.mode)[0])

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
        exit_ceiling_timestamps=song_inputs.exit_ceiling,
    )
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
        timestamps=song.chart.timestamps,
        note_types=song.chart.note_types,
        lanes=song.chart.lanes,
        fill_count=int(fill_count),
        fever_duration_ms=float(real_fever_time) * 1000.0,
        timing_mode=song.mode,
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
    song: TimedSong,
    curves: StatCurves,
    surface: Any,
) -> int:
    """
    Exact f64 replay for a solved FG response surface.

    The response surface is the canonical representation for timeline-frontier
    FG because it can encode Fever+Great overlap; forced-count configs cannot.
    """
    if not stats:
        raise ValueError("FG response surface replay needs stats")
    total_notes = song.chart.total_notes
    primary, secondary = song.chart.primary, song.chart.secondary
    f = core_score.factors(_stats_row(stats), curves, primary, secondary)
    return core_score.fg_surface_score(f, surface, total_notes)
