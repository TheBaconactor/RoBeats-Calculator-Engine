"""
Stats Scoring - Stats Evaluation Helpers.

This module provides functions for evaluating fixed stats without gem optimization:
- evaluate_stats_score: Calculate score for a fixed stats snapshot
- build_great_penalty_table: Precompute ramp penalties for force greats
- Helper for Force Greats config conversion
"""

import numpy as np
from math import floor

from ...core.utils import safe_int, safe_float

from ..fever_timeline import calculate_fever_timeline_indices
from ...core.ref_lookup import resolve_stat_factors

from ..score_math import fast_calculate_score


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


