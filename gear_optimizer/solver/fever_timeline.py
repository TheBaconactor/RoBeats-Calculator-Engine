"""The fever timeline of play at fixed hit times (Non-Precise, or chart + a custom offset): numba kernels for the
frontier payload and the website, and the scorer's timing cell.

The fever bar fills after `fill_notes` scored notes (timing_envelope.fever_axes: the game's fill threshold, rounded
up to whole Perfects). The note that fills it is the first fever note, and the first section needs one note less
because the fill is applied before the note is scored. Fever lasts `fever_duration` seconds (the game's float64
duration); the note where it ends is scored outside fever without adding fill.
"""

import numpy as np

from ..core.jit_setup import jit
from ..score import TimelineCell, single_surface_cell


@jit(nopython=True, cache=True)
def calculate_fever_timeline_indices(song_timestamps, total_notes, fill_notes, fever_duration, fever_mask_buffer):
    """The fever mask of play at `song_timestamps` (float32 seconds, non-decreasing) into `fever_mask_buffer`.

    Returns (fever_mask_head, count_body_fever, count_body_normal, fever_activations, last_fever_end_idx); the last
    is where the last fever window ends (for the gap after it).
    """
    non_fever_base = fill_notes
    real_fever_time = fever_duration

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
    fever_durations,
    fill_notes,
    body_fever_out,
    body_normal_out,
    head_mask_words_out,
    fever_activations_out,
    last_fever_end_out,
):
    """Batch the canonical fixed-timing surface over every FT/FF axis cell."""
    mask_buffer = np.zeros(total_notes, dtype=np.bool_)
    for ft_idx in range(fever_durations.shape[0]):
        for ff_idx in range(fill_notes.shape[0]):
            head_mask, body_fever, body_normal, activations, last_end = calculate_fever_timeline_indices(
                song_timestamps, total_notes, fill_notes[ff_idx], fever_durations[ft_idx], mask_buffer
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


def fixed_timeline_cell(hit_times: np.ndarray, *, fill_notes: int, fever_duration: float) -> TimelineCell:
    """The single timing surface of play at `hit_times` (float32, non-decreasing), as a TimelineCell."""
    total = int(hit_times.shape[0])
    head, body_fever, body_normal, _activations, _end = calculate_fever_timeline_indices(
        np.asarray(hit_times, dtype=np.float32), total, int(fill_notes), float(fever_duration), np.zeros(total, np.bool_)
    )
    return single_surface_cell(head, int(body_fever), int(body_normal))
