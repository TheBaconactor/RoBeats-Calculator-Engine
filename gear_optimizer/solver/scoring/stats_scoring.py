"""
Stats Scoring - Stats Evaluation Helpers.

This module provides functions for evaluating fixed stats without gem optimization:
- evaluate_stats_score: Calculate score for a fixed stats snapshot
- build_great_penalty_table: Precompute ramp penalties for force greats
- fg_baseline_params: Lightweight baseline computation for ForceGreatsFinder batching
- Helper functions for song caching and config conversion
"""

import os
import numpy as np
from math import floor

from ...core.constants import FEVER_FILL_BASE_RATE, FEVER_TIME_OFFSET, FEVER_TIME_SCALE, TOTAL_ROWS
from ...core.utils import safe_int, safe_float

from ..fever_timeline import (
    calculate_fever_activations_grid,
    calculate_fever_timeline_indices,
    calculate_non_fever_sections,
)

from ..scoring_core import fast_calculate_score, lookup_reference_py


_FG_BASELINE_CACHE: dict[tuple, tuple[int, int]] = {}
_FG_BASELINE_CACHE_MAX = 8192
_FG_BASELINE_GRID_CACHE: dict[tuple, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
_FG_BASELINE_GRID_CACHE_MAX = 64


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
    cached = _FG_BASELINE_GRID_CACHE.get(song_key)
    if cached is not None:
        return cached

    # Normalize timestamps for Numba kernels (keep dtype to preserve parity).
    ts = np.asarray(timestamps)
    if ts.ndim != 1:
        raise ValueError("timestamps must be 1D")
    if not ts.flags["C_CONTIGUOUS"]:
        ts = np.ascontiguousarray(ts)

    grid_size = int(TOTAL_ROWS) + 1
    ref_ft = np.asarray(ref_arrays["Fever Time"], dtype=np.float64)
    ref_ff = np.asarray(ref_arrays["Fever Fill Rate"], dtype=np.float64)
    if int(ref_ft.shape[0]) < grid_size or int(ref_ff.shape[0]) < grid_size:
        raise ValueError("ref_arrays['Fever Time'/'Fever Fill Rate'] must have length >= TOTAL_ROWS+1")
    ft_factors = np.ascontiguousarray(ref_ft[:grid_size], dtype=np.float64)
    ff_factors = np.ascontiguousarray(ref_ff[:grid_size], dtype=np.float64)

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

    if len(_FG_BASELINE_GRID_CACHE) >= _FG_BASELINE_GRID_CACHE_MAX:
        _FG_BASELINE_GRID_CACHE.clear()
    _FG_BASELINE_GRID_CACHE[song_key] = (acts, gap, non_fever_base_by_ff)
    return _FG_BASELINE_GRID_CACHE[song_key]


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

    ft_factor = lookup_reference_py(stats["Fever Time"], ref_arrays["Fever Time"], TOTAL_ROWS)
    ff_factor = lookup_reference_py(stats["Fever Fill Rate"], ref_arrays["Fever Fill Rate"], TOTAL_ROWS)
    fever_mask_head, count_body_fever, count_body_normal, _, _ = calculate_fever_timeline_indices(
        timestamps,
        total_notes,
        ff_factor,
        ft_factor,
        long_count,
        last_time,
        mask_buffer,
    )

    base_pp = lookup_reference_py(stats["Perfect Points"], ref_arrays["Perfect Points"], TOTAL_ROWS)
    combo_mul = lookup_reference_py(stats["Combo Multiplier"], ref_arrays["Combo Multiplier"], TOTAL_ROWS)
    fever_mul = lookup_reference_py(stats["Fever Multiplier"], ref_arrays["Fever Multiplier"], TOTAL_ROWS)

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


def fg_baseline_params(stats, calc_song, ref_arrays):
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
        cached = _FG_BASELINE_CACHE.get(cache_key)
        if cached is not None:
            return cached
    except Exception:
        cache_key = None

    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps"))
    total_notes = len(timestamps)
    if total_notes <= 0:
        return 0, 0

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    # last_note_time is derived from chart length, not simulated hits.
    base_ts = song_data.get("timestamps", timestamps)
    default_last_note = base_ts[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

    # Fast path: use per-song fever_activations/gap grids to avoid per-(FT,FF) timeline stepping.
    use_grid = str(os.environ.get("FG_BASELINE_GRID", "1") or "").strip().lower() in {"1", "true", "yes", "on", ""}
    if use_grid:
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
            if cache_key is not None:
                if len(_FG_BASELINE_CACHE) >= _FG_BASELINE_CACHE_MAX:
                    _FG_BASELINE_CACHE.clear()
                _FG_BASELINE_CACHE[cache_key] = result
            return result
        except Exception:
            # Fall back to the legacy per-point baseline computation.
            pass

    ref_ff = ref_arrays["Fever Fill Rate"]
    ref_ft = ref_arrays["Fever Time"]

    fever_fill_rate = lookup_reference_py(stats.get("Fever Fill Rate", 0), ref_ff, TOTAL_ROWS)
    fever_time_stat = lookup_reference_py(stats.get("Fever Time", 0), ref_ft, TOTAL_ROWS)
    non_fever_section, non_fever_base = calculate_non_fever_sections(
        timestamps,
        total_notes,
        fever_fill_rate,
        fever_time_stat,
        long_notes,
        last_note_time,
    )

    result = (int(non_fever_section), int(non_fever_base))
    if cache_key is not None:
        if len(_FG_BASELINE_CACHE) >= _FG_BASELINE_CACHE_MAX:
            _FG_BASELINE_CACHE.clear()
        _FG_BASELINE_CACHE[cache_key] = result
    return result


def _song_cache_key(calc_song):
    """Generate cache key for song."""
    meta = calc_song.get("metadata", {}) or {}
    song_data = calc_song.get("song_data", {}) or {}
    timestamps = song_data.get("fg_timestamps", song_data.get("timestamps", ()))
    n = int(len(timestamps))
    first_ts = float(timestamps[0]) if n else 0.0
    last_ts = float(timestamps[-1]) if n else 0.0
    sim_seed = int(meta.get("HumanHitSimSeed", 0) or 0)
    return (
        str(meta.get("Song Name", "")),
        n,
        first_ts,
        last_ts,
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
        sim_seed,
    )
