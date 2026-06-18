"""
Stats Scoring - Stats Evaluation Helpers.

This module provides functions for evaluating fixed stats without gem optimization:
- evaluate_stats_score: Calculate score for a fixed stats snapshot
- build_great_penalty_table: Precompute ramp penalties for force greats
- fg_baseline_params: Lightweight baseline computation for ForceGreatsFinder batching
- Helper functions for song caching and config conversion
"""

import threading
import numpy as np
from math import ceil, floor
import logging

from gear_optimizer.core.array_signature import array_sig16

from ...core.constants import FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE, TOTAL_ROWS
from ...core.utils import timing_envelope_full_context, timing_envelope_timing_context, safe_int, safe_float

from ..fever_timeline import (
    calculate_fever_activations_grid,
    calculate_fever_timeline_indices,
    calculate_non_fever_sections,
)
from ...core.ref_lookup import resolve_stat_factors

from ..scoring_core import fast_calculate_score, lookup_reference_py

logger = logging.getLogger(__name__)
_FG_BASELINE_CACHE: dict[tuple, tuple[int, int]] = {}
_FG_BASELINE_CACHE_MAX = 8192
_FG_BASELINE_GRID_CACHE: dict[tuple, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
_FG_BASELINE_GRID_CACHE_MAX = 64
_FG_BASELINE_GRID_INFLIGHT: dict[tuple, threading.Event] = {}
_FG_BASELINE_POINT_MISS_COUNT: dict[tuple, int] = {}
_FG_BASELINE_CACHE_LOCK = threading.Lock()


def _fg_baseline_grid_auto_threshold() -> int:
    return 16


def _fg_baseline_cache_get(cache_key: tuple | None) -> tuple[int, int] | None:
    if cache_key is None:
        return None
    with _FG_BASELINE_CACHE_LOCK:
        return _FG_BASELINE_CACHE.get(cache_key)


def _fg_baseline_cache_put(cache_key: tuple | None, result: tuple[int, int]) -> None:
    if cache_key is None:
        return
    with _FG_BASELINE_CACHE_LOCK:
        if len(_FG_BASELINE_CACHE) >= _FG_BASELINE_CACHE_MAX:
            _FG_BASELINE_CACHE.clear()
        _FG_BASELINE_CACHE[cache_key] = result


def _get_fg_baseline_grids(
    *,
    song_key: tuple,
    timestamps: np.ndarray,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    ref_arrays: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build or fetch per-song baseline grids for fast ForceGreatsFinder batching.

    Returns:
        (fever_activations_grid, gap_grid, non_fever_base_by_ff)
    """
    build_event: threading.Event | None = None
    is_builder = False
    with _FG_BASELINE_CACHE_LOCK:
        cached = _FG_BASELINE_GRID_CACHE.get(song_key)
        if cached is not None:
            return cached
        build_event = _FG_BASELINE_GRID_INFLIGHT.get(song_key)
        if build_event is None:
            build_event = threading.Event()
            _FG_BASELINE_GRID_INFLIGHT[song_key] = build_event
            is_builder = True
    if not is_builder and build_event is not None:
        build_event.wait()
        with _FG_BASELINE_CACHE_LOCK:
            cached = _FG_BASELINE_GRID_CACHE.get(song_key)
            if cached is not None:
                return cached

    # Normalize timestamps for Numba kernels (float32-first for CPU/GPU parity).
    ts = np.asarray(timestamps)
    if ts.ndim != 1:
        raise ValueError("timestamps must be 1D")
    if not ts.flags["C_CONTIGUOUS"]:
        ts = np.ascontiguousarray(ts)

    grid_size = int(TOTAL_ROWS) + 1
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float32)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float32)
    if int(ref_ft.shape[0]) < grid_size or int(ref_ff.shape[0]) < grid_size:
        raise ValueError("ref_arrays['Fever Time'/'Fever Fill Rate'] must have length >= TOTAL_ROWS+1")
    ft_factors = np.ascontiguousarray(ref_ft[:grid_size], dtype=np.float32)
    ff_factors = np.ascontiguousarray(ref_ff[:grid_size], dtype=np.float32)

    non_fever_cas = float(int(total_notes) - int(long_notes)) * float(FEVER_FILL_BASE_RATE)
    if non_fever_cas < 0.0:
        non_fever_cas = 0.0
    fever_time_cas = float(last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)

    acts = np.zeros((grid_size, grid_size), dtype=np.int32)
    last_end = np.zeros((grid_size, grid_size), dtype=np.int32)
    calculate_fever_activations_grid(
        ts,
        int(total_notes),
        float(fever_time_cas),
        float(non_fever_cas),
        ft_factors,
        ff_factors,
        acts,
        last_end,
    )

    gap = np.empty((grid_size, grid_size), dtype=np.int32)
    gap[:, :] = int(total_notes) - last_end

    non_fever_base_by_ff = np.ceil(float(non_fever_cas) * ff_factors).astype(np.int32)

    try:
        with _FG_BASELINE_CACHE_LOCK:
            if len(_FG_BASELINE_GRID_CACHE) >= _FG_BASELINE_GRID_CACHE_MAX:
                _FG_BASELINE_GRID_CACHE.clear()
            _FG_BASELINE_GRID_CACHE[song_key] = (acts, gap, non_fever_base_by_ff)
            _FG_BASELINE_POINT_MISS_COUNT.pop(song_key, None)
            cached = _FG_BASELINE_GRID_CACHE[song_key]
    finally:
        with _FG_BASELINE_CACHE_LOCK:
            event = _FG_BASELINE_GRID_INFLIGHT.pop(song_key, None)
        if event is not None:
            event.set()
    return cached


def evaluate_stats_score(
    stats,
    calc_song,
    ref_arrays,
    song_timestamps=None,
    long_notes=None,
    last_note=None,
    fever_mask_buffer=None,
):
    """
    Return total score for a fixed stats snapshot without gem reallocations.

    This is used when you just want to evaluate a loadout without optimizing gems.

    Args:
        stats: Stats dictionary
        calc_song: Song calculation context
        ref_arrays: Reference lookup arrays
        song_timestamps: Optional precomputed timestamps
        long_notes: Optional long notes count
        last_note: Optional last note time
        fever_mask_buffer: Optional preallocated fever mask buffer

    Returns:
        int: Total score
    """
    timestamps = song_timestamps if song_timestamps is not None else calc_song["song_data"]["timestamps"]
    total_notes = len(timestamps)
    long_count = long_notes if long_notes is not None else safe_int(calc_song["metadata"].get("Long Notes"), 0)
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_time = (
        last_note
        if last_note is not None
        else safe_float(calc_song["metadata"].get("Last Note Time"), default_last_note)
    )
    mask_buffer = fever_mask_buffer
    if mask_buffer is None or mask_buffer.shape[0] != total_notes:
        mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    factors = resolve_stat_factors(stats, ref_arrays)
    ft_factor = float(factors.fever_time_stat)
    ff_factor = float(factors.fever_fill_rate)
    fever_mask_head, count_body_fever, count_body_normal, _, _ = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        ff_factor,
        ft_factor,
        long_count,
        last_time,
        mask_buffer,
    )

    base_pp = float(factors.pp_factor)
    combo_mul = float(factors.combo_mul)
    fever_mul = float(factors.fever_mul)

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    primary_val = stats.get(p_color, 0)
    secondary_val = stats.get(s_color, 0)
    total_base = (primary_val * 2) + secondary_val + base_pp

    return fast_calculate_score(
        total_base,
        combo_mul,
        fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
    )


def evaluate_stats_score_nojit(
    stats,
    calc_song,
    ref_arrays,
    song_timestamps=None,
    long_notes=None,
    last_note=None,
    fever_mask_buffer=None,
):
    timestamps = song_timestamps if song_timestamps is not None else calc_song["song_data"]["timestamps"]
    total_notes = len(timestamps)
    long_count = long_notes if long_notes is not None else safe_int(calc_song["metadata"].get("Long Notes"), 0)
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_time = (
        last_note
        if last_note is not None
        else safe_float(calc_song["metadata"].get("Last Note Time"), default_last_note)
    )
    mask_buffer = fever_mask_buffer
    if mask_buffer is None or mask_buffer.shape[0] != total_notes:
        mask_buffer = np.zeros(total_notes, dtype=np.bool_)

    factors = resolve_stat_factors(stats, ref_arrays)
    fever_mask_head, count_body_fever, count_body_normal, _, _ = _calculate_fever_timeline_indices_python(
        timestamps,
        total_notes,
        float(factors.fever_fill_rate),
        float(factors.fever_time_stat),
        long_count,
        last_time,
        mask_buffer,
    )

    p_color = calc_song["metadata"].get("Primary Color", "")
    s_color = calc_song["metadata"].get("Secondary Color", "")
    total_base = (stats.get(p_color, 0) * 2) + stats.get(s_color, 0) + float(factors.pp_factor)
    base_f = np.float32(total_base)
    combo_f = np.float32(float(factors.combo_mul))
    fever_f = np.float32(float(factors.fever_mul))
    combo_val = int(base_f * combo_f)
    fever_val = int(base_f * combo_f * fever_f)
    score = (int(count_body_fever) * fever_val) + (int(count_body_normal) * combo_val)
    factor = (combo_f - np.float32(1.0)) * base_f / np.float32(100.0)
    for idx, in_fever in enumerate(fever_mask_head):
        ramp = base_f + (np.float32(idx + 1) * factor)
        score += int(ramp * fever_f) if bool(in_fever) else int(ramp)
    return int(score)


def _calculate_fever_timeline_indices_python(
    song_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes_count,
    last_note_time,
    fever_mask_buffer,
):
    non_fever_cas = (int(total_notes) - int(long_notes_count)) * float(FEVER_FILL_BASE_RATE)
    non_fever_base = ceil(non_fever_cas * float(fever_fill_rate))
    fever_time_cas = float(last_note_time) * float(FEVER_TIME_SCALE) + float(FEVER_TIME_OFFSET)
    real_fever_time = fever_time_cas * float(fever_time_stat)

    is_fever = fever_mask_buffer
    is_fever[:] = False
    current_note_idx = 0
    fever_activations = 0
    fever_section = 0
    last_fever_end_idx = 0

    while current_note_idx < int(total_notes):
        fever_section += 1
        notes_to_fill = int(non_fever_base) - 1 if int(fever_section) == 1 else int(non_fever_base)
        end_normal_idx = min(int(current_note_idx) + int(notes_to_fill), int(total_notes))
        current_note_idx = int(end_normal_idx)
        if current_note_idx >= int(total_notes):
            break

        if current_note_idx > 0:
            fever_activations += 1
            start_time = float(song_timestamps[current_note_idx])
            end_time = start_time + float(real_fever_time)
            fever_end_idx = int(np.searchsorted(song_timestamps, np.float32(end_time), side="left"))
            is_fever[current_note_idx:fever_end_idx] = True
            current_note_idx = int(fever_end_idx)
            last_fever_end_idx = int(fever_end_idx)
        else:
            break

    head_limit = min(int(total_notes), 100)
    fever_mask_head = is_fever[:head_limit]
    count_body_fever = 0
    count_body_normal = 0
    if int(total_notes) > 100:
        count_body_fever = int(np.count_nonzero(is_fever[100:int(total_notes)]))
        count_body_normal = int(total_notes) - 100 - int(count_body_fever)
    return fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx


def _force_greats_counts_to_dict(counts, sections):
    """Convert force counts to config dict."""
    config = {}
    for idx in range(sections):
        val = counts[idx] if idx < len(counts) else 0
        config[f"NonFever{idx + 1}"] = max(0, int(val))
    return config


def build_great_penalty_table(base_value, combo_mul, great_penalty_base, head_limit=100):
    """
    Precompute ramp penalties for the first `head_limit` notes.
    Avoids recalculating scaling when evaluating force-great permutations.
    """
    penalties = [0] * head_limit
    combo_span = combo_mul - 1.0
    for idx in range(head_limit):
        scaling = 1.0 + combo_span * (idx + 1) / 100.0
        perfect_val = floor(base_value * scaling)
        great_val = floor(great_penalty_base * scaling)
        penalties[idx] = max(0, perfect_val - great_val)
    return penalties


def _fg_baseline_params_point(
    *,
    stats,
    timestamps,
    total_notes: int,
    long_notes: int,
    last_note_time: float,
    ref_arrays: dict,
) -> tuple[int, int]:
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
    non_fever_section, non_fever_base = calculate_non_fever_sections(
        timestamps,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
    )
    return int(non_fever_section), int(non_fever_base)


def fg_baseline_params(stats, calc_song, ref_arrays, *, prefer_grid: bool | None = None):
    """
    Lightweight baseline computation for ForceGreatsFinder batching.

    Returns:
        (num_non_fever_sections, non_fever_base)
    """
    if not stats or not calc_song:
        return 0, 0

    # Cache by song + FT/FF stats. This is called many times during FG candidate
    # collection; caching avoids repeated baseline work.
    song_key = None
    ft_stat_raw = 0
    ff_stat_raw = 0
    try:
        song_key = _song_cache_key(calc_song)
        ft_stat_raw = int(safe_int(stats.get("Fever Time", 0), 0))
        ff_stat_raw = int(safe_int(stats.get("Fever Fill Rate", 0), 0))
        cache_key = (song_key, ft_stat_raw, ff_stat_raw)
        cached = _fg_baseline_cache_get(cache_key)
        if cached is not None:
            return cached
    except Exception as e:
        logger.debug(f"stats_scoring:fg_baseline_params: {e}")
        cache_key = None

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps", song_data.get("timestamps", song_data.get("fg_timestamps")))
    total_notes = len(timestamps)
    if total_notes <= 0:
        return 0, 0

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    # last_note_time is derived from chart length, not simulated hits.
    base_ts = song_data.get("chart_timestamps", song_data.get("timestamps", timestamps))
    default_last_note = base_ts[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    # Fast path: use per-song fever_activations/gap grids to avoid per-(FT,FF) timeline stepping.
    use_grid = True  # grid baseline is output-identical and faster than the per-point path (always on)
    if prefer_grid is None:
        prefer_grid = False
        if use_grid:
            threshold = _fg_baseline_grid_auto_threshold()
            with _FG_BASELINE_CACHE_LOCK:
                prefer_grid = song_key in _FG_BASELINE_GRID_CACHE
                if not prefer_grid and threshold <= 0:
                    prefer_grid = True
                if not prefer_grid:
                    point_miss_count = int(_FG_BASELINE_POINT_MISS_COUNT.get(song_key, 0))
                    prefer_grid = point_miss_count >= int(threshold)
    else:
        prefer_grid = bool(prefer_grid)

    if use_grid and prefer_grid:
        try:
            if song_key is None:
                song_key = _song_cache_key(calc_song)
            if not isinstance(timestamps, np.ndarray):
                timestamps = np.asarray(timestamps)
            acts_grid, gap_grid, non_fever_base_by_ff = _get_fg_baseline_grids(
                song_key=song_key,
                timestamps=timestamps,
                total_notes=int(total_notes),
                long_notes=int(long_notes),
                last_note_time=float(last_note_time),
                ref_arrays=ref_arrays,
            )
            ft_idx = max(0, min(TOTAL_ROWS, int(ft_stat_raw)))
            ff_idx = max(0, min(TOTAL_ROWS, int(ff_stat_raw)))
            fever_acts = int(acts_grid[ft_idx, ff_idx])
            gap0 = int(gap_grid[ft_idx, ff_idx])
            if gap0 < 0:
                gap0 = 0
            non_fever_base = int(non_fever_base_by_ff[ff_idx]) if non_fever_base_by_ff is not None else 0
            non_fever_section = int(fever_acts) + (1 if gap0 > 0 else 0)
            result = (int(non_fever_section), int(non_fever_base))
            _fg_baseline_cache_put(cache_key, result)
            return result
        except Exception as e:
            # Fall back to the per-point baseline computation.
            logger.debug(f"stats_scoring:fg_baseline_params: {e}")

    result = _fg_baseline_params_point(
        stats=stats,
        timestamps=timestamps,
        total_notes=int(total_notes),
        long_notes=int(long_notes),
        last_note_time=float(last_note_time),
        ref_arrays=ref_arrays,
    )
    _fg_baseline_cache_put(cache_key, result)
    if use_grid and song_key is not None:
        with _FG_BASELINE_CACHE_LOCK:
            if song_key not in _FG_BASELINE_GRID_CACHE:
                _FG_BASELINE_POINT_MISS_COUNT[song_key] = int(_FG_BASELINE_POINT_MISS_COUNT.get(song_key, 0)) + 1
    return result


def _song_cache_key(calc_song):
    """Generate cache key for song."""
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("chart_timestamps", song_data.get("timestamps", song_data.get("fg_timestamps", ())))
    n = int(len(timestamps))
    first_ts = float(timestamps[0]) if n else 0.0
    last_ts = float(timestamps[-1]) if n else 0.0
    return (
        str(meta.get("Song Name", "")),
        n,
        first_ts,
        last_ts,
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        "TIMING_ENVELOPE",
        0,
    ) + timing_envelope_timing_context(calc_song)


def _song_cache_key_for_fg_timeline(calc_song):
    """
    Generate cache key for ForceGreats timeline evaluation.

    This key MUST vary when fg_timestamps / fg_perfect_candidate_timestamps /
    fg_great_candidate_timestamps vary,
    otherwise FG timeline caches can cross-contaminate between different simulated runs.
    """
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}

    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps", ()))
    try:
        n = int(len(timestamps))
    except Exception as e:
        logger.debug(f"stats_scoring:_song_cache_key_for_fg_timeline: {e}")
        n = 0

    first_ms = 0
    last_ms = 0
    try:
        if n:
            first_ms = int(float(timestamps[0]) * 1000.0)
            last_ms = int(float(timestamps[n - 1]) * 1000.0)
    except Exception as e:
        logger.debug(f"stats_scoring:_song_cache_key_for_fg_timeline: {e}")
        first_ms = 0
        last_ms = 0

    perfect_candidates = song_data.get("fg_perfect_candidate_timestamps")
    great_candidates = song_data.get("fg_great_candidate_timestamps")
    perfect_sig = b""
    great_sig = b""
    has_perfect_candidates = 0
    has_great_candidates = 0
    try:
        has_perfect_candidates = 1 if perfect_candidates is not None and int(len(perfect_candidates)) == int(n) else 0
        if has_perfect_candidates:
            perfect_sig = bytes(array_sig16(np.asarray(perfect_candidates, dtype=np.float32).reshape(-1)))
        has_great_candidates = 1 if great_candidates is not None and int(len(great_candidates)) == int(n) else 0
        if has_great_candidates:
            great_sig = bytes(array_sig16(np.asarray(great_candidates, dtype=np.float32).reshape(-1)))
    except Exception as e:
        logger.debug(f"stats_scoring:_song_cache_key_for_fg_timeline: {e}")
        has_perfect_candidates = 0
        has_great_candidates = 0
        perfect_sig = b""
        great_sig = b""

    return (
        str(meta.get("Song Name", "")),
        str(meta.get("Difficulty", "")),
        n,
        safe_int(first_ms, 0),
        safe_int(last_ms, 0),
        safe_float(meta.get("Last Note Time", 0) or 0, 0.0),
        safe_int(meta.get("Long Notes", 0) or 0, 0),
        int(has_perfect_candidates),
        perfect_sig,
        int(has_great_candidates),
        great_sig,
    ) + timing_envelope_full_context(calc_song)
