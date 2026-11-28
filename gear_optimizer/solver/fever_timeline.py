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
    fever_mask_buffer[:] = False
    current_note_idx = 0
    fever_activations = 0
    fever_section = 0
    last_fever_end_idx = 0
    while current_note_idx < total_notes:
        fever_section += 1
        current_note_idx += fill_notes - 1 if fever_section == 1 else fill_notes
        if current_note_idx >= total_notes or current_note_idx <= 0:
            break
        fever_activations += 1
        end_time = song_timestamps[current_note_idx] + fever_duration
        fever_end_idx = np.searchsorted(song_timestamps, np.float32(end_time), side="left")
        fever_mask_buffer[current_note_idx:fever_end_idx] = True
        current_note_idx = fever_end_idx
        last_fever_end_idx = fever_end_idx

    head_limit = min(total_notes, 100)
    count_body_fever = 0
    count_body_normal = 0
    for i in range(100, total_notes):
        if fever_mask_buffer[i]:
            count_body_fever += 1
        else:
            count_body_normal += 1
    return fever_mask_buffer[:head_limit], count_body_fever, count_body_normal, fever_activations, last_fever_end_idx


@jit(nopython=True, cache=True)
def _word_range_mask_u32(start: int, end: int, word_base: int) -> np.uint32:
    lo = max(start, word_base)
    hi = min(end, word_base + 32)
    if hi <= lo:
        return np.uint32(0)
    width = hi - lo
    if width >= 32:
        return np.uint32(0xFFFFFFFF)
    return ((np.uint32(1) << np.uint32(width)) - np.uint32(1)) << np.uint32(lo - word_base)


@jit(nopython=True, cache=True)
def calculate_fever_timeline_surface_grid(song_timestamps, total_notes, fever_durations, fill_notes, out):
    """Batch the canonical fixed-timing surface over every FT/FF axis cell.

    Walks only the fever activations of each distinct (duration, fill) pair in O(A log n) without an O(n) mask
    buffer, accumulating body fever counts and the 4-word head bitmask directly from each disjoint fever interval."""
    body_fever_out, body_normal_out, head_mask_words_out, fever_activations_out, last_fever_end_out = out
    head_limit = min(total_notes, 100)
    total_body = max(0, total_notes - 100)
    n_ft, n_ff = fever_durations.shape[0], fill_notes.shape[0]
    for ft_idx in range(n_ft):
        real_fever_time = fever_durations[ft_idx]
        if ft_idx > 0 and real_fever_time == fever_durations[ft_idx - 1]:
            body_fever_out[ft_idx] = body_fever_out[ft_idx - 1]
            body_normal_out[ft_idx] = body_normal_out[ft_idx - 1]
            fever_activations_out[ft_idx] = fever_activations_out[ft_idx - 1]
            last_fever_end_out[ft_idx] = last_fever_end_out[ft_idx - 1]
            head_mask_words_out[ft_idx] = head_mask_words_out[ft_idx - 1]
            continue
        for ff_idx in range(n_ff):
            non_fever_base = fill_notes[ff_idx]
            if ff_idx > 0 and non_fever_base == fill_notes[ff_idx - 1]:
                body_fever_out[ft_idx, ff_idx] = body_fever_out[ft_idx, ff_idx - 1]
                body_normal_out[ft_idx, ff_idx] = body_normal_out[ft_idx, ff_idx - 1]
                fever_activations_out[ft_idx, ff_idx] = fever_activations_out[ft_idx, ff_idx - 1]
                last_fever_end_out[ft_idx, ff_idx] = last_fever_end_out[ft_idx, ff_idx - 1]
                head_mask_words_out[ft_idx, ff_idx] = head_mask_words_out[ft_idx, ff_idx - 1]
                continue
            current_note_idx = 0
            fever_activations = 0
            fever_section = 0
            last_fever_end_idx = 0
            body_fever = 0
            w0 = w1 = w2 = w3 = np.uint32(0)
            while current_note_idx < total_notes:
                fever_section += 1
                current_note_idx += non_fever_base - 1 if fever_section == 1 else non_fever_base
                if current_note_idx >= total_notes or current_note_idx <= 0:
                    break
                fever_activations += 1
                start_time = song_timestamps[current_note_idx]
                cutoff = np.float32(start_time + real_fever_time)
                lo = current_note_idx + 1 if cutoff > start_time else 0
                hi = total_notes
                while lo < hi:
                    mid = (lo + hi) >> 1
                    if song_timestamps[mid] < cutoff:
                        lo = mid + 1
                    else:
                        hi = mid
                fever_end_idx = lo
                if fever_end_idx > current_note_idx:
                    if fever_end_idx > 100:
                        body_fever += fever_end_idx - max(current_note_idx, 100)
                    if current_note_idx < head_limit:
                        h_hi = min(fever_end_idx, head_limit)
                        w0 |= _word_range_mask_u32(current_note_idx, h_hi, 0)
                        w1 |= _word_range_mask_u32(current_note_idx, h_hi, 32)
                        w2 |= _word_range_mask_u32(current_note_idx, h_hi, 64)
                        w3 |= _word_range_mask_u32(current_note_idx, h_hi, 96)
                current_note_idx = last_fever_end_idx = fever_end_idx
            body_fever_out[ft_idx, ff_idx] = body_fever
            body_normal_out[ft_idx, ff_idx] = total_body - body_fever
            fever_activations_out[ft_idx, ff_idx] = fever_activations
            last_fever_end_out[ft_idx, ff_idx] = last_fever_end_idx
            head_mask_words_out[ft_idx, ff_idx, 0] = w0
            head_mask_words_out[ft_idx, ff_idx, 1] = w1
            head_mask_words_out[ft_idx, ff_idx, 2] = w2
            head_mask_words_out[ft_idx, ff_idx, 3] = w3


@jit(nopython=True, cache=True)
def intern_fixed_timing_surfaces(body_fever, masks, activations, last_fever_end, max_pool: int):
    """Intern the (G, G) fixed-timing cells in FT-major first-cell order in O(G^2) using an open-addressing table.

    Equality of (body_fever, mask[0..3], activations, last_fever_end) is identical to equality of all 8 cell fields
    since body_normal = total_body - body_fever and gap = total_notes - last_fever_end.
    Returns (offsets_2d, pool_bf, pool_masks, pool_used)."""
    rows, cols = body_fever.shape[0], body_fever.shape[1]
    n_cells = rows * cols
    cap = 16
    while cap < 2 * n_cells:
        cap <<= 1
    mask_cap = cap - 1
    slots = np.full(cap, -1, dtype=np.int32)
    offsets = np.empty((rows, cols), dtype=np.int32)
    pool_bf = np.empty(n_cells, dtype=np.int32)
    pool_masks = np.empty((n_cells, 4), dtype=np.uint32)
    pool_act = np.empty(n_cells, dtype=np.int32)
    pool_lfe = np.empty(n_cells, dtype=np.int32)
    used = 0
    for r in range(rows):
        for c in range(cols):
            bf, act, lfe = body_fever[r, c], activations[r, c], last_fever_end[r, c]
            m0, m1, m2, m3 = masks[r, c, 0], masks[r, c, 1], masks[r, c, 2], masks[r, c, 3]
            h = np.uint64(np.int64(bf)) * np.uint64(0x9E3779B97F4A7C15)
            h = (h ^ (h >> np.uint64(29)) ^ np.uint64(m0)) * np.uint64(0xBF58476D1CE4E5B9)
            h = (h ^ (h >> np.uint64(31)) ^ np.uint64(m1)) * np.uint64(0x94D049BB133111EB)
            h = (h ^ (h >> np.uint64(29)) ^ np.uint64(m2)) * np.uint64(0x9E3779B97F4A7C15)
            h = (h ^ (h >> np.uint64(31)) ^ np.uint64(m3)) * np.uint64(0xBF58476D1CE4E5B9)
            h = (h ^ (h >> np.uint64(29)) ^ np.uint64(np.int64(act))) * np.uint64(0x94D049BB133111EB)
            h = (h ^ (h >> np.uint64(31)) ^ np.uint64(np.int64(lfe))) * np.uint64(0x9E3779B97F4A7C15)
            slot = np.int64((h ^ (h >> np.uint64(32))) & np.uint64(mask_cap))
            while True:
                pid = slots[slot]
                if pid < 0:
                    if used >= max_pool:
                        raise RuntimeError("non-precise timeline surface pool overflow")
                    slots[slot] = used
                    pool_bf[used], pool_act[used], pool_lfe[used] = bf, act, lfe
                    pool_masks[used, 0], pool_masks[used, 1], pool_masks[used, 2], pool_masks[used, 3] = m0, m1, m2, m3
                    offsets[r, c] = used
                    used += 1
                    break
                if (
                    pool_bf[pid] == bf and pool_act[pid] == act and pool_lfe[pid] == lfe
                    and pool_masks[pid, 0] == m0 and pool_masks[pid, 1] == m1
                    and pool_masks[pid, 2] == m2 and pool_masks[pid, 3] == m3
                ):
                    offsets[r, c] = pid
                    break
                slot = (slot + 1) & mask_cap
    return offsets, pool_bf[:used], pool_masks[:used], used


def fixed_timeline_cell(hit_times: np.ndarray, *, fill_notes: int, fever_duration: float) -> TimelineCell:
    """The single timing surface of play at `hit_times` (float32, non-decreasing), as a TimelineCell."""
    total = int(hit_times.shape[0])
    head, body_fever, body_normal, _activations, _end = calculate_fever_timeline_indices(
        np.asarray(hit_times, dtype=np.float32), total, int(fill_notes), float(fever_duration), np.zeros(total, np.bool_)
    )
    return single_surface_cell(head, int(body_fever), int(body_normal))
