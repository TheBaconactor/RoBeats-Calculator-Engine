"""
Force Greats timeline and manual evaluation helpers.

Production FG optimization uses the response-frontier GPU path (`process_force_greats`).
This module retains CPU timeline/penalty evaluation for tooling and rescoring.
"""

import logging
import threading

import numpy as np

from ...core.utils import safe_int
from ..fever_timeline import calculate_force_greats_timeline_indices
from ..scoring_core import fast_calculate_score
from .fg_policy import (
    accumulate_fg_penalties,
    build_fg_result_dict,
    build_penalty_table_and_body,
    extract_fg_song_inputs,
    is_single_color_song,
    resolve_stat_factors,
)
from .runtime_state import FORCE_GREATS_ALGO_VERSION  # noqa: F401 -- re-exported for FG helpers


logger = logging.getLogger(__name__)

# Thread-local scratch buffers for Force Greats timeline computation.
# This avoids per-call NumPy allocations in hot loops without introducing
# cross-thread aliasing issues.
_FG_TIMELINE_TLS = threading.local()


def _get_fg_timeline_buffers(total_notes: int):
    """
    Get (or allocate) reusable scratch buffers sized for `total_notes`.

    Returns:
        tuple: (fever_mask_buffer, section_start, section_forced, section_fill_penalty, section_skip_wasted)
    """
    n = int(total_notes)
    if n < 0:
        n = 0
    # Worst-case: section count is bounded by note count (+1 for safety).
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
    """
    Compute fever timeline with force greats applied.

    Args:
        timestamps: Song timestamps array
        total_notes: Total number of notes
        fever_fill_rate: Fever fill rate factor
        fever_time_stat: Fever time factor
        long_notes: Number of long notes
        last_note_time: Last note timestamp
        force_counts: List of forced great counts per section
        clamp_base_notes_nonnegative: Whether to clamp base notes to non-negative
        clamp_forced_to_section_notes: Whether to clamp forced counts to section notes

    Returns:
        tuple: (fever_mask_head, count_body_fever, count_body_normal, non_fever_base, section_details)
    """
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
        base_notes = non_fever_base - 1 if (i == 0) else non_fever_base
        if clamp_base_notes_nonnegative:
            base_notes = max(0, int(base_notes))
        notes_to_fill = int(base_notes) + int(section_fill_penalty[i])

        section_details.append(
            {
                "start_idx": int(section_start[i]),
                "forced": int(section_forced[i]),
                "fill_penalty_notes": int(section_fill_penalty[i]),
                "skip_wasted": bool(section_skip_wasted[i]),
                "notes": notes_to_fill,
            }
        )

    return (
        fever_mask_head_view.copy(),
        int(count_body_fever),
        int(count_body_normal),
        int(non_fever_base),
        section_details,
    )


def evaluate_force_greats(stats, calc_song, ref_arrays, forced_counts=None):
    """
    Recompute fever timeline and penalties when greats are forced in non-fever sections.
    Returns None when prerequisites are missing.
    """
    if not stats or not calc_song:
        return None

    song_inputs = extract_fg_song_inputs(calc_song)
    if int(song_inputs.total_notes) <= 0:
        return None

    primary_val = safe_int(stats.get(song_inputs.primary_color, 0), 0)
    secondary_val = safe_int(stats.get(song_inputs.secondary_color, 0), 0)
    factors = resolve_stat_factors(stats, ref_arrays)
    single_color = is_single_color_song(song_inputs.primary_color, song_inputs.secondary_color)
    base_value = (primary_val * 2) + secondary_val + float(factors.pp_factor)
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

    base_score = fast_calculate_score(
        base_value,
        factors.combo_mul,
        factors.fever_mul,
        fever_mask_head,
        count_body_fever,
        count_body_normal,
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
