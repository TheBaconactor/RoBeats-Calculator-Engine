"""
Taichi Kernels - Breakpoint Collection.

This module contains kernels for FG breakpoint detection:
- collect_breakpoints_kernel: Parallel breakpoint collection across stat grid

Breakpoints are FG counts where the timeline changes (different fever coverage).
By detecting these on GPU, we eliminate CPU overhead from Python grid scanning.

Reuses timeline simulation logic from kernels_timeline.py.
"""
import taichi as ti

from .kernels_helpers import _KERNEL_BLOCK_DIM
from . import kernels_helpers


# Field placeholders for breakpoint detection
# Bound by fields.bind_fields() at runtime
bp_pair_ft = None      # (MAX_PAIRS,) i32 - FT stat indices to scan
bp_pair_ff = None      # (MAX_PAIRS,) i32 - FF stat indices to scan
bp_result_mask = None  # (16, 64) i32 - breakpoint mask per (section, count)


@ti.func
def _simulate_timeline_signature(
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    forced_section: ti.i32,
    forced_count: ti.i32,
) -> ti.i64:
    """
    Simulate timeline with specific forced count and return a signature.
    
    The signature uniquely identifies the fever coverage pattern.
    Uses body_fever count + fever_activations as a compact hash.
    
    Args:
        total_notes: Total notes in song
        long_notes: Long notes count
        last_note_time: Last note timestamp
        ft_idx: Fever Time stat index
        ff_idx: Fever Fill stat index
        forced_section: Which section to apply forced count (0-based)
        forced_count: Number of forced greats in that section
        
    Returns:
        i64 signature: (body_fever << 32) | (activations << 16) | head_hash
    """
    MAX_HEAD: ti.i32 = 100
    MAX_SECTIONS: ti.i32 = 16
    
    # Lookup multipliers
    ft_factor = kernels_helpers.ref_ft_field[ft_idx]
    ff_factor = kernels_helpers.ref_ff_field[ff_idx]
    
    # Compute fill and time parameters
    non_fever_cas = ti.cast(total_notes - long_notes, ti.f32) * 0.333
    non_fever_base_f = non_fever_cas * ff_factor
    non_fever_base = ti.i32(ti.ceil(non_fever_base_f))
    non_fever_great_to_fill = ti.i32(ti.ceil(ti.max(1.0, non_fever_base_f * 2.0)))
    real_fever_time = (last_note_time * 0.15 + 0.15) * ft_factor
    
    # Initialize fever mask bits
    m0: ti.u32 = 0
    m1: ti.u32 = 0
    
    current_note = 0
    fever_section = 0
    fever_activations = 0
    body_fever = 0
    
    while current_note < total_notes and fever_section < MAX_SECTIONS:
        # Non-fever section
        base_notes = non_fever_base - 1 if fever_section == 0 else non_fever_base
        if base_notes < 0:
            base_notes = 0
        
        # Apply forced greats if this is the target section
        forced_val = 0
        if fever_section == forced_section:
            forced_val = forced_count
            if forced_val > non_fever_base:
                forced_val = non_fever_base
        
        # Calculate fill penalty from forced greats using new formula:
        # For section 1, we apply -1 indexing offset OUTSIDE the ceil.
        raw_penalty: ti.f32 = ti.cast(forced_val, ti.f32) * 0.5
        
        notes_to_fill_total = ti.cast(ti.ceil(non_fever_base_f + raw_penalty), ti.i32)
        if fever_section == 0:
            notes_to_fill_total -= 1
            
        fill_penalty_notes = notes_to_fill_total - base_notes
        
        notes_to_fill = base_notes + fill_penalty_notes
        end_normal_idx = ti.min(current_note + notes_to_fill, total_notes)
        current_note = end_normal_idx
        
        if current_note >= total_notes:
            break
        
        if current_note > 0:
            fever_activations += 1
            start_time = kernels_helpers.song_timestamps[current_note]
            end_time = start_time + real_fever_time
            fever_end_idx = kernels_helpers.binary_search_left(
                kernels_helpers.song_timestamps, total_notes, end_time
            )
            
            # Mark fever notes in bitmask (first 64 only for hash)
            for note_i in range(current_note, fever_end_idx):
                if note_i < 32:
                    m0 |= ti.u32(1) << ti.u32(note_i)
                elif note_i < 64:
                    m1 |= ti.u32(1) << ti.u32(note_i - 32)
                elif note_i >= MAX_HEAD:
                    body_fever += 1
            
            current_note = fever_end_idx
        else:
            break
        
        fever_section += 1
    
    # Create signature from components
    head_hash = ti.cast(m0% 65536, ti.i64)
    signature = (ti.cast(body_fever, ti.i64) << 32) | (ti.cast(fever_activations, ti.i64) << 16) | head_hash
    return signature


@ti.kernel
def collect_breakpoints_kernel(
    n_pairs: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    max_sections: ti.i32,
    max_count: ti.i32,
):
    """
    Collect FG breakpoints by detecting timeline changes on GPU.
    
    Parallelizes over (pair_idx, section, count) triplets.
    Each thread simulates timeline with forced_count and compares to forced_count-1.
    If signatures differ, marks that count as a breakpoint.
    
    Uses atomic_or to aggregate breakpoints across all pairs.
    
    Args:
        n_pairs: Number of (ft, ff) pairs to scan
        total_notes: Total notes in song
        long_notes: Long notes count
        last_note_time: Last note timestamp
        max_sections: Max sections to check (usually 4)
        max_count: Max forced count to check per section (usually 50)
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    
    # Total work items: pairs × sections × counts
    total_work = n_pairs * max_sections * max_count
    
    for work_idx in range(total_work):
        # Decode work item
        pair_idx = work_idx // (max_sections * max_count)
        remainder = work_idx % (max_sections * max_count)
        sec = remainder // max_count
        count = (remainder % max_count) + 1  # counts are 1..max_count
        
        if pair_idx >= n_pairs:
            continue
        
        ft_idx = bp_pair_ft[pair_idx]
        ff_idx = bp_pair_ff[pair_idx]
        
        # Get signature for count and count-1
        sig_curr = _simulate_timeline_signature(
            total_notes, long_notes, last_note_time,
            ft_idx, ff_idx, sec, count
        )
        sig_prev = _simulate_timeline_signature(
            total_notes, long_notes, last_note_time,
            ft_idx, ff_idx, sec, count - 1
        )
        
        # If timeline changed, mark this count as a breakpoint
        if sig_curr != sig_prev:
            ti.atomic_or(bp_result_mask[sec, count], 1)


@ti.kernel
def reset_breakpoint_mask_kernel():
    """Reset breakpoint mask to zeros before collection."""
    for sec, count in ti.ndrange(16, 64):
        bp_result_mask[sec, count] = 0
