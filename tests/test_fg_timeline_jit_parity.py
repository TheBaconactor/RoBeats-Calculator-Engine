import os
import sys
from math import ceil

import numpy as np

# Ensure we can import gear_optimizer
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gear_optimizer.solver.fever_timeline import (  # noqa: E402
    calculate_force_greats_timeline_indices,
    calculate_non_fever_sections,
)


def _py_baseline_sections(
    timestamps: np.ndarray,
    fever_fill_rate: float,
    fever_time_stat: float,
    long_notes: int,
    last_note_time: float,
):
    total_notes = int(len(timestamps))
    non_fever_cas = max(0.0, (total_notes - int(long_notes)) * 0.333)
    non_fever_base = ceil(non_fever_cas * float(fever_fill_rate))
    fever_time_cas = float(last_note_time) * 0.15 + 0.15
    real_fever_time = fever_time_cas * float(fever_time_stat)

    current_idx = 0
    non_fever_section = 0
    while current_idx < total_notes:
        non_fever_section += 1
        base_notes = non_fever_base - 1 if non_fever_section == 1 else non_fever_base
        base_notes = max(0, base_notes)
        current_idx = min(current_idx + base_notes, total_notes)
        if current_idx >= total_notes:
            break
        start_time = timestamps[current_idx]
        end_time = start_time + real_fever_time
        fever_end_idx = int(np.searchsorted(timestamps, end_time, side="left"))
        if fever_end_idx <= current_idx:
            fever_end_idx = min(total_notes, current_idx + 1)
        current_idx = fever_end_idx

    return int(non_fever_section), int(non_fever_base)


def _py_force_greats_timeline(
    timestamps: np.ndarray,
    fever_fill_rate: float,
    fever_time_stat: float,
    long_notes: int,
    last_note_time: float,
    forced_counts: list[int],
    *,
    clamp_base_notes_nonnegative: bool,
    clamp_forced_to_section_notes: bool,
):
    total_notes = int(len(timestamps))
    non_fever_cas = max(0.0, (total_notes - int(long_notes)) * 0.333)
    non_fever_base = ceil(non_fever_cas * float(fever_fill_rate))
    non_fever_great_to_fill = ceil(max(1.0, (non_fever_cas * float(fever_fill_rate)) * 2.0))
    fever_time_cas = float(last_note_time) * 0.15 + 0.15
    real_fever_time = fever_time_cas * float(fever_time_stat)

    fever_mask = np.zeros(total_notes, dtype=np.bool_)
    current_idx = 0
    non_fever_section = 0
    section_details = []

    while current_idx < total_notes:
        non_fever_section += 1
        base_notes = non_fever_base - 1 if non_fever_section == 1 else non_fever_base
        if clamp_base_notes_nonnegative:
            base_notes = max(0, base_notes)

        forced_val = forced_counts[non_fever_section - 1] if (non_fever_section - 1) < len(forced_counts) else 0
        forced_val = min(int(forced_val), non_fever_base)
        # Use raw values and ceiling AFTER adding: ceil(raw_base + raw_penalty)
        raw_penalty = max(0.0, forced_val * 0.5)
        raw_fever_fill = non_fever_cas * float(fever_fill_rate)
        
        notes_to_fill = ceil(raw_fever_fill + raw_penalty)
        if non_fever_section == 1:
            notes_to_fill -= 1
        fill_penalty_notes = notes_to_fill - base_notes

        section_start = current_idx
        end_normal = min(section_start + notes_to_fill, total_notes)
        actual_notes = max(0, end_normal - section_start)
        forced_applied = min(forced_val, actual_notes) if clamp_forced_to_section_notes else forced_val

        section_details.append(
            {
                "start_idx": int(section_start),
                "forced": int(forced_applied),
                "fill_penalty_notes": int(fill_penalty_notes),
                "skip_wasted": bool(non_fever_section == 1),
            }
        )

        current_idx = end_normal
        if current_idx >= total_notes:
            break

        start_time = timestamps[current_idx]
        end_time = start_time + real_fever_time
        fever_end_idx = int(np.searchsorted(timestamps, end_time, side="left"))
        if fever_end_idx <= current_idx:
            fever_end_idx = min(total_notes, current_idx + 1)
        fever_mask[current_idx:fever_end_idx] = True
        current_idx = fever_end_idx

    head_limit = min(total_notes, 100)
    fever_mask_head = fever_mask[:head_limit].copy()
    if total_notes > 100:
        body_slice = fever_mask[100:]
        count_body_fever = int(np.count_nonzero(body_slice))
        count_body_normal = int(max(len(body_slice) - count_body_fever, 0))
    else:
        count_body_fever = 0
        count_body_normal = 0

    return fever_mask_head, count_body_fever, count_body_normal, int(non_fever_base), section_details


def test_non_fever_sections_jit_matches_python():
    timestamps = (np.arange(0, 250, dtype=np.float64) * 0.5).astype(np.float64)
    total_notes = int(len(timestamps))
    long_notes = 0
    last_note_time = float(timestamps[-1]) if total_notes else 0.0

    fever_fill_rate = 0.5
    fever_time_stat = 1.0

    py_sections, py_base = _py_baseline_sections(
        timestamps, fever_fill_rate, fever_time_stat, long_notes, last_note_time
    )
    jit_sections, jit_base = calculate_non_fever_sections(
        timestamps, total_notes, fever_fill_rate, fever_time_stat, long_notes, last_note_time
    )

    assert int(jit_sections) == int(py_sections)
    assert int(jit_base) == int(py_base)


def test_force_greats_timeline_jit_matches_python_for_both_semantics():
    timestamps = (np.arange(0, 260, dtype=np.float64) * 0.5).astype(np.float64)
    total_notes = int(len(timestamps))
    long_notes = 0
    last_note_time = float(timestamps[-1]) if total_notes else 0.0

    fever_fill_rate = 0.5
    fever_time_stat = 1.0
    forced_counts = [5, 0, 10, 2]

    for clamp_base_notes_nonnegative, clamp_forced_to_section_notes in (
        (True, True),   # evaluate_force_greats
        (False, False), # evaluate_fg_with_gem_iteration
    ):
        py = _py_force_greats_timeline(
            timestamps,
            fever_fill_rate,
            fever_time_stat,
            long_notes,
            last_note_time,
            forced_counts,
            clamp_base_notes_nonnegative=clamp_base_notes_nonnegative,
            clamp_forced_to_section_notes=clamp_forced_to_section_notes,
        )
        py_mask, py_cbf, py_cbn, py_nf_base, py_sections = py

        fever_mask_buffer = np.zeros(total_notes, dtype=np.bool_)
        forced_arr = np.asarray(forced_counts, dtype=np.int32)
        section_cap = total_notes + 1
        section_start = np.zeros(section_cap, dtype=np.int32)
        section_forced = np.zeros(section_cap, dtype=np.int32)
        section_fill_penalty = np.zeros(section_cap, dtype=np.int32)
        section_skip_wasted = np.zeros(section_cap, dtype=np.bool_)

        (
            jit_mask_view,
            jit_cbf,
            jit_cbn,
            jit_nf_base,
            jit_section_count,
        ) = calculate_force_greats_timeline_indices(
            timestamps,
            timestamps,  # great_candidate_timestamps (disabled in this parity test)
            total_notes,
            fever_fill_rate,
            fever_time_stat,
            long_notes,
            last_note_time,
            forced_arr,
            int(forced_arr.shape[0]),
            bool(clamp_base_notes_nonnegative),
            bool(clamp_forced_to_section_notes),
            False,  # use_forced_great_timing
            fever_mask_buffer,
            section_start,
            section_forced,
            section_fill_penalty,
            section_skip_wasted,
        )

        jit_mask = jit_mask_view.copy()
        assert np.array_equal(jit_mask, py_mask)
        assert int(jit_cbf) == int(py_cbf)
        assert int(jit_cbn) == int(py_cbn)
        assert int(jit_nf_base) == int(py_nf_base)

        jit_sections = []
        for i in range(int(jit_section_count)):
            jit_sections.append(
                {
                    "start_idx": int(section_start[i]),
                    "forced": int(section_forced[i]),
                    "fill_penalty_notes": int(section_fill_penalty[i]),
                    "skip_wasted": bool(section_skip_wasted[i]),
                }
            )

        assert jit_sections == py_sections

