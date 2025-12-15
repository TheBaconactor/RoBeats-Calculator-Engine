"""
Stats Scoring - Stats Evaluation Helpers.

This module provides functions for evaluating fixed stats without gem optimization:
- evaluate_stats_score: Calculate score for a fixed stats snapshot
- build_great_penalty_table: Precompute ramp penalties for force greats
- fg_baseline_params: Lightweight baseline computation for ForceGreatsFinder batching
- Helper functions for song caching and config conversion
"""
import numpy as np
from math import floor

from ...core.constants import TOTAL_ROWS
from ...core.utils import safe_int, safe_float

from ..fever_timeline import (
    calculate_fever_timeline_indices,
    calculate_non_fever_sections,
    lookup_reference_py,
)

from ..scoring_core import fast_calculate_score


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
    timestamps = (
        song_timestamps if song_timestamps is not None else calc_song["song_data"]["timestamps"]
    )
    total_notes = len(timestamps)
    long_count = (
        long_notes
        if long_notes is not None
        else safe_int(calc_song["metadata"].get("Long Notes"), 0)
    )
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
    fever_mask_head, count_body_fever, count_body_normal, _ = calculate_fever_timeline_indices(
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

    timestamps = calc_song["song_data"]["timestamps"]
    total_notes = len(timestamps)
    if total_notes <= 0:
        return 0, 0

    metadata = calc_song.get("metadata", {}) or {}
    long_notes = safe_int(metadata.get("Long Notes"), 0)
    default_last_note = timestamps[-1] if total_notes else 0.0
    last_note_time = safe_float(metadata.get("Last Note Time"), default_last_note)

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

    return int(non_fever_section), int(non_fever_base)


def _song_cache_key(calc_song):
    """Generate cache key for song."""
    meta = calc_song.get("metadata", {}) or {}
    timestamps = calc_song.get("song_data", {}).get("timestamps", ())
    return (
        str(meta.get("Song Name", "")),
        int(len(timestamps)),
        float(meta.get("Last Note Time", 0) or 0),
        int(meta.get("Long Notes", 0) or 0),
    )
