"""
Taichi Kernels - Timeline Computation.

This module contains kernels for fever timeline precomputation:
- binary_search_left_from: Binary search with lower bound
- binary_search_left: Binary search for leftmost index
- compute_timeline_grid_kernel: Parallel 161×161 timeline grid computation

The timeline grid kernel precomputes all valid fever timelines for the
full FT/FF stat range (0-160 for each), enabling O(1) lookups during
gem optimization instead of recomputing timelines for each combination.

This is a critical performance optimization that reduces timeline computation
from O(n_combos × song_notes) to O(1) per combo after precomputation.
"""
import taichi as ti

from .kernels_helpers import (
    _KERNEL_BLOCK_DIM,
    ref_ft_field,
    ref_ff_field,
    song_timestamps,
    grid_count_body_fever,
    grid_count_body_normal,
    grid_head_len,
    grid_fever_masks,
    grid_fever_masks_bits,
)


@ti.func
def binary_search_left_from(
    timestamps: ti.template(), n: ti.i32, target: ti.f32, lo: ti.i32
) -> ti.i32:
    """
    Binary search for leftmost index where timestamps[i] >= target, starting at `lo`.

    Equivalent to np.searchsorted(timestamps, target, side='left') with a lower bound.

    Args:
        timestamps: Sorted array of timestamps (Taichi field)
        n: Length of array
        target: Value to search for
        lo: Lower bound starting index

    Returns:
        Leftmost index where timestamps[i] >= target, or n if not found
    """
    hi = n
    while lo < hi:
        mid = (lo + hi) // 2
        if timestamps[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo


@ti.func
def binary_search_left(timestamps: ti.template(), n: ti.i32, target: ti.f32) -> ti.i32:
    """
    Binary search for leftmost index where timestamps[i] >= target.

    Equivalent to np.searchsorted(timestamps, target, side='left').

    Args:
        timestamps: Sorted array of timestamps (Taichi field)
        n: Length of array
        target: Value to search for

    Returns:
        Leftmost index where timestamps[i] >= target, or n if not found
    """
    return binary_search_left_from(timestamps, n, target, 0)


@ti.kernel
def compute_timeline_grid_kernel(
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    song_slot: ti.i32,  # Grid slot to write to (0-7)
):
    """
    Compute all 161×161 fever timeline entries on GPU.

    Parallelizes over (ft_idx, ff_idx) pairs. Each thread computes one timeline
    by simulating fever activation and expiration across the song.

    For each FT/FF stat combination:
    1. Compute fever fill rate (from FF stat) -> notes needed to fill fever gauge
    2. Compute fever duration (from FT stat) -> time fever lasts once activated
    3. Simulate timeline: track which notes are in fever vs non-fever sections
    4. Generate bit-packed fever mask (4×u32 = 128 bits for first 100 notes)
    5. Count body fever/normal notes (notes 100+)

    Writes results to song_slot in grid fields for batch coalescing support.

    Results written to:
    - grid_count_body_fever[song_slot, ft, ff]: Count of fever notes in body
    - grid_count_body_normal[song_slot, ft, ff]: Count of normal notes in body
    - grid_head_len[song_slot, ft, ff]: Number of notes in head (min(total, 100))
    - grid_fever_masks[song_slot, ft, ff, :]: Unpacked fever mask (100 bytes)
    - grid_fever_masks_bits[song_slot, ft, ff, :]: Bit-packed fever mask (4×u32)

    Args:
        total_notes: Total number of notes in song
        long_notes: Number of long notes (sustained notes)
        last_note_time: Timestamp of last note in seconds
        song_slot: Grid slot to write to (0-7 for batch coalescing)
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)

    # Constants
    MAX_HEAD: ti.i32 = 100
    GRID_DIM: ti.i32 = 161

    # Precompute song-invariant values
    # Fever fill formula: non_fever_notes * 0.333 * ff_factor
    non_fever_cas = ti.cast(total_notes - long_notes, ti.f32) * 0.333
    # Fever time formula: song_duration * 0.15 * ft_factor + 0.15
    fever_time_cas = last_note_time * 0.15 + 0.15

    for idx in range(GRID_DIM * GRID_DIM):
        ft_idx = idx // GRID_DIM
        ff_idx = idx % GRID_DIM

        # Lookup multipliers from reference tables
        ft_factor = ref_ft_field[ft_idx]
        ff_factor = ref_ff_field[ff_idx]

        # Compute fill and time parameters
        non_fever_base_f = non_fever_cas * ff_factor
        non_fever_base = ti.i32(ti.ceil(non_fever_base_f))
        real_fever_time = fever_time_cas * ft_factor

        # Initialize fever mask bits (4 × u32 = 128 bits for first 100 notes)
        m0: ti.u32 = 0
        m1: ti.u32 = 0
        m2: ti.u32 = 0
        m3: ti.u32 = 0

        current_note = 0
        fever_section = 0

        # Simulate fever timeline
        while current_note < total_notes:
            fever_section += 1

            # Non-fever section: first section -1, later sections use base
            notes_to_fill = non_fever_base - 1 if fever_section == 1 else non_fever_base

            end_normal_idx = ti.min(current_note + notes_to_fill, total_notes)
            current_note = end_normal_idx

            if current_note >= total_notes:
                break

            if current_note > 0:
                # Fever activates
                start_time = song_timestamps[current_note]
                end_time = start_time + real_fever_time

                # Binary search for first note >= end_time
                fever_end_idx = binary_search_left(song_timestamps, total_notes, end_time)

                # Mark fever notes in bitmask (for first MAX_HEAD notes)
                for note_i in range(current_note, fever_end_idx):
                    if note_i < 32:
                        m0 |= ti.u32(1) << ti.u32(note_i)
                    elif note_i < 64:
                        m1 |= ti.u32(1) << ti.u32(note_i - 32)
                    elif note_i < 96:
                        m2 |= ti.u32(1) << ti.u32(note_i - 64)
                    elif note_i < MAX_HEAD:
                        m3 |= ti.u32(1) << ti.u32(note_i - 96)

                current_note = fever_end_idx
            else:
                break

        # Count body fever/normal (notes 100+)
        count_body_fever = 0
        count_body_normal = 0
        head_len = ti.min(total_notes, MAX_HEAD)

        # Re-simulate to count body notes (notes >= MAX_HEAD)
        # (The bitmask only covers first 100 notes)
        current_note = 0
        fever_section = 0
        body_fever = 0
        body_normal = 0

        while current_note < total_notes:
            fever_section += 1
            notes_to_fill = non_fever_base - 1 if fever_section == 1 else non_fever_base
            end_normal_idx = ti.min(current_note + notes_to_fill, total_notes)

            # Count normal body notes in this section
            for ni in range(current_note, end_normal_idx):
                if ni >= MAX_HEAD:
                    body_normal += 1

            current_note = end_normal_idx
            if current_note >= total_notes:
                break

            if current_note > 0:
                start_time = song_timestamps[current_note]
                end_time = start_time + real_fever_time
                fever_end_idx = binary_search_left(song_timestamps, total_notes, end_time)

                # Count fever body notes
                for ni in range(current_note, fever_end_idx):
                    if ni >= MAX_HEAD:
                        body_fever += 1

                current_note = fever_end_idx
            else:
                break

        # Write outputs to specified song slot
        grid_count_body_fever[song_slot, ft_idx, ff_idx] = body_fever
        grid_count_body_normal[song_slot, ft_idx, ff_idx] = body_normal
        grid_head_len[song_slot, ft_idx, ff_idx] = head_len
        grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0] = m0
        grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1] = m1
        grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2] = m2
        grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3] = m3

        # Also write unpacked mask for compatibility
        for i in range(MAX_HEAD):
            is_fever: ti.i8 = 0
            if i < 32:
                is_fever = ti.cast((m0 >> ti.u32(i)) & 1, ti.i8)
            elif i < 64:
                is_fever = ti.cast((m1 >> ti.u32(i - 32)) & 1, ti.i8)
            elif i < 96:
                is_fever = ti.cast((m2 >> ti.u32(i - 64)) & 1, ti.i8)
            else:
                is_fever = ti.cast((m3 >> ti.u32(i - 96)) & 1, ti.i8)
            grid_fever_masks[song_slot, ft_idx, ff_idx, i] = is_fever
