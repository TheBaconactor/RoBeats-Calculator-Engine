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
bp_pair_ft = None  # (MAX_PAIRS,) i32 - FT stat indices to scan
bp_pair_ff = None  # (MAX_PAIRS,) i32 - FF stat indices to scan
bp_result_mask = None  # (16, 64) i32 - breakpoint mask per (section, count)

# ForceGreats section forced-count caps (must match `gear_optimizer.helpers.fg_utils.MAX_SECTION_CAPS`
# and `gear_optimizer.solver.taichi_gem.force_greats.kernels._FG_SECTION_FORCED_CAPS`).
_FG_SECTION_FORCED_CAPS = (50, 30, 15, 10, 8, 6, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4)


@ti.func
def _fg_section_forced_cap(sec: ti.i32) -> ti.i32:
    cap: ti.i32 = 4
    for i in ti.static(range(len(_FG_SECTION_FORCED_CAPS))):
        if sec == ti.i32(i):
            cap = ti.i32(_FG_SECTION_FORCED_CAPS[i])
    return cap


@ti.kernel
def fg_compute_max_fp_by_pair_kernel(
    n_pairs: ti.i32,
    n_base_pairs: ti.i32,
    n_sections: ti.i32,
    song_slot: ti.i32,
    gem_scale_fever: ti.i32,
    pair_ft_gems: ti.types.ndarray(dtype=ti.i32, ndim=1),
    pair_ff_gems: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base_ft_stat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base_ff_stat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    non_fever_base_by_ff: ti.types.ndarray(dtype=ti.i16, ndim=1),  # (161,)
    fp_cap_table: ti.types.ndarray(dtype=ti.i16, ndim=2),  # (161, 51)
    out_max_fp: ti.types.ndarray(dtype=ti.i16, ndim=2),  # (n_pairs, n_sections)
):
    """
    GPU-accelerated breakpoint "range" computation for native FG solver batching.

    Computes the per-(ftff_pair, section) maximum fill-penalty cap (FP cap) across
    all provided base (FT stat, FF stat) pairs.

    This matches the behavior of `helpers.fg_utils.iter_analytical_breakpoint_groups`
    where per-section breakpoints are simply `range(0, max_fp + 1)`.

    Notes:
    - Uses `grid_gap` and `grid_fever_activations` (baseline timeline grid).
    - Uses integer math for section scaling to avoid float drift:
        sec0: base_cap
        sec1: floor(base_cap * 0.6) == (3*base_cap)//5
        sec>=2: floor(base_cap * 0.3) == (3*base_cap)//10
    - `fp_cap_table[ff_idx, forced_cap]` must be computed on CPU with the exact ceil rules.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)

    for pair_idx, sec in ti.ndrange(n_pairs, n_sections):
        max_fp: ti.i32 = 0

        ft_g = pair_ft_gems[pair_idx]
        ff_g = pair_ff_gems[pair_idx]

        for b in range(n_base_pairs):
            ft_idx = base_ft_stat[b] + ft_g * gem_scale_fever
            ff_idx = base_ff_stat[b] + ff_g * gem_scale_fever
            if ft_idx < 0:
                ft_idx = 0
            if ft_idx > 160:
                ft_idx = 160
            if ff_idx < 0:
                ff_idx = 0
            if ff_idx > 160:
                ff_idx = 160

            fever_acts = ti.cast(kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx], ti.i32)
            if sec >= fever_acts:
                continue

            gap = ti.cast(kernels_helpers.grid_gap[song_slot, ft_idx, ff_idx], ti.i32)
            if gap < 0:
                gap = 0

            base_notes = ti.cast(non_fever_base_by_ff[ff_idx], ti.i32)
            # NOTE: Do not cap by `gap` here.
            #
            # Using `gap = total_notes - last_fever_end_idx` as a hard cap is overly strict when
            # fever overflows to song end (gap=0) and can incorrectly collapse breakpoint ranges
            # to [0] for most/all FT/FF pairs. The breakpoint "cap" is used to bound search, not
            # to enforce correctness; correctness is handled by the full FG evaluation.
            base_cap = base_notes

            cap = base_cap
            if sec == 1:
                cap = (cap * 3) // 5
            elif sec >= 2:
                cap = (cap * 3) // 10

            hard_cap = _fg_section_forced_cap(sec)
            if cap > hard_cap:
                cap = hard_cap
            if cap < 0:
                cap = 0
            if cap > 50:
                cap = 50

            fp = ti.cast(fp_cap_table[ff_idx, cap], ti.i32)
            if fp > max_fp:
                max_fp = fp

        out_max_fp[pair_idx, sec] = ti.cast(max_fp, ti.i16)


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
    ff_factor = kernels_helpers.ref_ff_field[ff_idx]

    # Compute fill and time parameters (game formula constants from constants.py)
    non_fever_cas = ti.cast(total_notes - long_notes, ti.f32) * 0.333  # FEVER_FILL_BASE_RATE
    non_fever_base_f = non_fever_cas * ff_factor
    non_fever_base = ti.i32(ti.ceil(non_fever_base_f))

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
            # NOTE: Requires precompute_fever_end_idx_kernel() to have populated
            # kernels_helpers.fever_end_idx_song for the current song/last_note_time.
            fever_end_idx = ti.min(kernels_helpers.fever_end_idx_song[current_note, ft_idx], total_notes)

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
    head_hash = ti.cast(m0 % 65536, ti.i64)
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
        sig_curr = _simulate_timeline_signature(total_notes, long_notes, last_note_time, ft_idx, ff_idx, sec, count)
        sig_prev = _simulate_timeline_signature(total_notes, long_notes, last_note_time, ft_idx, ff_idx, sec, count - 1)

        # If timeline changed, mark this count as a breakpoint
        if sig_curr != sig_prev:
            ti.atomic_or(bp_result_mask[sec, count], 1)


@ti.kernel
def reset_breakpoint_mask_kernel():
    """Reset breakpoint mask to zeros before collection."""
    for sec, count in ti.ndrange(16, 64):
        bp_result_mask[sec, count] = 0
