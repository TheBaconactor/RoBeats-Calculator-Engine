"""
Deterministic fever timeline kernels (numba) for the fingerprinted frontier code and the website.

gear_optimizer.timing is the rewrite's implementation of the same walk.
"""

import numpy as np
from math import ceil

from ..core.jit_setup import jit


@jit(nopython=True, cache=True)
def calculate_fever_timeline_indices(
    song_timestamps,
    total_notes,
    fever_fill_rate,
    fever_time_stat,
    long_notes_count,
    last_note_time,
    fever_mask_buffer,
):
    """
    Calculate fever timeline using corrected server-matching logic.

    Key fixes:
    1. First non-fever section: non_fever_base - 1 notes
       Later sections: non_fever_base notes (1 "wasted" note where fever ends)
    2. Binary search uses side="left" (>=) instead of side="right" (>)

    Args:
        song_timestamps: NumPy array of note timestamps
        total_notes: Total number of notes in song
        fever_fill_rate: Fever fill rate multiplier
        fever_time_stat: Fever time multiplier
        long_notes_count: Number of long notes
        last_note_time: Timestamp of last note
        fever_mask_buffer: Preallocated boolean array for fever mask

    Returns:
        tuple: (fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx)
               last_fever_end_idx = where the last fever window ends (for gap calculation)
    """
    # Game formula constants (see rules.FEVER_FILL_PER_NOTE, FEVER_TIME_PER_SECOND, FEVER_TIME_OFFSET)
    non_fever_cas = (total_notes - long_notes_count) * 0.333  # FEVER_FILL_PER_NOTE
    non_fever_base = ceil(non_fever_cas * fever_fill_rate)
    # Keep these literals in this cached kernel's own bytecode. Numba's disk-cache key does not
    # include values imported from another module, so using FEVER_TIME_SCALE/OFFSET here can revive
    # machine code compiled with older constants after rules.py changes.
    fever_time_cas = last_note_time * 0.15 + 0.15
    real_fever_time = fever_time_cas * fever_time_stat

    is_fever = fever_mask_buffer
    is_fever[:] = False
    current_note_idx = 0
    fever_activations = 0
    fever_section = 0
    last_fever_end_idx = 0  # Track where last fever ends

    while current_note_idx < total_notes:
        # Non-fever section
        fever_section += 1
        # First section: -1, Later sections: use base (wasted note effect)
        if fever_section == 1:
            notes_to_fill = non_fever_base - 1
        else:
            notes_to_fill = non_fever_base

        end_normal_idx = min(current_note_idx + notes_to_fill, total_notes)
        current_note_idx = end_normal_idx
        if current_note_idx >= total_notes:
            break

        if current_note_idx > 0:
            fever_activations += 1
            start_time = song_timestamps[current_note_idx]
            end_time = start_time + real_fever_time
            # Use side="left" to find first note where time >= end_time (not >)
            fever_end_idx = np.searchsorted(song_timestamps, np.float32(end_time), side="left")
            is_fever[current_note_idx:fever_end_idx] = True
            current_note_idx = fever_end_idx
            last_fever_end_idx = fever_end_idx  # Update last fever end
        else:
            break

    head_limit = min(total_notes, 100)
    fever_mask_head = is_fever[:head_limit]
    count_body_fever = 0
    count_body_normal = 0
    if total_notes > 100:
        for i in range(100, total_notes):
            if is_fever[i]:
                count_body_fever += 1
            else:
                count_body_normal += 1
    return fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx


@jit(nopython=True, cache=True)
def calculate_fever_timeline_surface_grid(
    song_timestamps,
    total_notes,
    ft_factors,
    ff_factors,
    long_notes_count,
    last_note_time,
    body_fever_out,
    body_normal_out,
    head_mask_words_out,
    fever_activations_out,
    last_fever_end_out,
):
    """Batch the canonical fixed-timing surface over every FT/FF axis cell."""
    mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    for ft_idx in range(ft_factors.shape[0]):
        for ff_idx in range(ff_factors.shape[0]):
            head_mask, body_fever, body_normal, activations, last_end = calculate_fever_timeline_indices(
                song_timestamps,
                total_notes,
                ff_factors[ff_idx],
                ft_factors[ft_idx],
                long_notes_count,
                last_note_time,
                mask_buffer,
            )
            body_fever_out[ft_idx, ff_idx] = body_fever
            body_normal_out[ft_idx, ff_idx] = body_normal
            fever_activations_out[ft_idx, ff_idx] = activations
            last_fever_end_out[ft_idx, ff_idx] = last_end
            for word_idx in range(head_mask_words_out.shape[2]):
                head_mask_words_out[ft_idx, ff_idx, word_idx] = np.uint32(0)
            for note_idx in range(head_mask.shape[0]):
                if head_mask[note_idx]:
                    word_idx = note_idx // 32
                    bit_idx = note_idx % 32
                    head_mask_words_out[ft_idx, ff_idx, word_idx] |= np.uint32(1) << np.uint32(bit_idx)


