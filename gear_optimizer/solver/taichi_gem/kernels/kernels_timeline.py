"""
Taichi Kernels - Timeline Computation.

This module contains kernels for fever timeline precomputation:
- precompute_fever_end_idx_kernel: Precompute fever end indices per (note, FT)
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
)

# Import kernels_helpers to access fields at runtime (they're bound by fields.bind_fields())
from . import kernels_helpers


@ti.kernel
def precompute_fever_end_idx_kernel(total_notes: ti.i32, last_note_time: ti.f32):
    """
    Precompute fever end indices for each (note_idx, ft_idx) using song timestamps.

    This replaces per-section binary searches in timeline simulation with O(1)
    table lookups (reduces divergent branches on GPU).
    """
    n_stat: ti.i32 = 161
    n: ti.i32 = ti.max(total_notes, 0)
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15  # FEVER_TIME_SCALE + FEVER_TIME_OFFSET

    for flat in range(n * n_stat):
        note_idx: ti.i32 = flat // n_stat
        ft_idx: ti.i32 = flat - (note_idx * n_stat)

        ft_factor: ti.f32 = kernels_helpers.ref_ft_field[ft_idx]
        fever_time: ti.f32 = fever_time_cas * ft_factor

        start_time: ti.f32 = kernels_helpers.song_timestamps[note_idx]
        end_time: ti.f32 = start_time + fever_time
        kernels_helpers.fever_end_idx_song[note_idx, ft_idx] = kernels_helpers.binary_search_left(
            kernels_helpers.song_timestamps, n, end_time
        )


@ti.func
def _mix_u64(x: ti.u64) -> ti.u64:
    """
    64-bit mix function for building robust timeline signatures.

    We use a strong integer mixer (MurmurHash3 finalizer) to reduce collision risk
    when bucketing "same timeline outcome" regions.
    """
    x ^= x >> ti.u64(33)
    x *= ti.u64(0xFF51AFD7ED558CCD)
    x ^= x >> ti.u64(33)
    x *= ti.u64(0xC4CEB9FE1A85EC53)
    x ^= x >> ti.u64(33)
    return x


@ti.func
def _pack_mask_sig(m0: ti.u32, m1: ti.u32, m2: ti.u32, m3: ti.u32) -> ti.u64:
    lo = ti.cast(m0, ti.u64) | (ti.cast(m1, ti.u64) << ti.u64(32))
    hi = ti.cast(m2, ti.u64) | (ti.cast(m3, ti.u64) << ti.u64(32))
    return _mix_u64(lo) ^ _mix_u64(hi + ti.u64(0x9E3779B97F4A7C15))


@ti.func
def _pack_counts_sig(
    body_fever: ti.i32,
    body_normal: ti.i32,
    head_len: ti.i32,
    fever_activations: ti.i32,
    gap: ti.i32,
) -> ti.u64:
    bf = ti.cast(body_fever & 0xFFFF, ti.u64)
    bn = ti.cast(body_normal & 0xFFFF, ti.u64) << ti.u64(16)
    hl = ti.cast(head_len & 0xFF, ti.u64) << ti.u64(32)
    fa = ti.cast(fever_activations & 0xFF, ti.u64) << ti.u64(40)
    gp = ti.cast(gap & 0xFFFF, ti.u64) << ti.u64(48)
    return bf | bn | hl | fa | gp


@ti.func
def _mask_range_u32(lo: ti.i32, hi: ti.i32) -> ti.u32:
    lo_c = ti.max(0, ti.min(32, lo))
    hi_c = ti.max(0, ti.min(32, hi))
    span = hi_c - lo_c
    out = ti.u32(0)
    if span > 0:
        if span >= 32:
            out = ti.u32(0xFFFFFFFF)
        else:
            out = (ti.u32(1) << ti.u32(span)) - ti.u32(1)
        out = out << ti.u32(lo_c)
    return out


@ti.func
def _or_head_mask_range(m0: ti.u32, m1: ti.u32, m2: ti.u32, m3: ti.u32, start: ti.i32, end: ti.i32) -> ti.types.vector(
    4, ti.u32
):
    s = ti.max(0, start)
    e = ti.min(100, end)
    if e > s:
        if s < 32:
            lo0 = s
            hi0 = ti.min(e, 32)
            m0 |= _mask_range_u32(lo0, hi0)
        if e > 32 and s < 64:
            lo1 = ti.max(0, s - 32)
            hi1 = ti.min(32, e - 32)
            m1 |= _mask_range_u32(lo1, hi1)
        if e > 64 and s < 96:
            lo2 = ti.max(0, s - 64)
            hi2 = ti.min(32, e - 64)
            m2 |= _mask_range_u32(lo2, hi2)
        if e > 96:
            lo3 = ti.max(0, s - 96)
            hi3 = ti.min(32, e - 96)
            m3 |= _mask_range_u32(lo3, hi3)
    return ti.Vector([m0, m1, m2, m3])


@ti.func
def _head_mask_coefficients(
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
) -> ti.types.vector(4, ti.i32):
    n_hn: ti.i32 = 0
    n_hf: ti.i32 = 0
    sigma_hn: ti.i32 = 0
    sigma_hf: ti.i32 = 0
    i = ti.i32(0)
    while i < head_len:
        pos = i + 1
        bit = ti.i32(0)
        if i < 32:
            bit = ti.cast((m0 >> ti.cast(i, ti.u32)) & ti.u32(1), ti.i32)
        elif i < 64:
            bit = ti.cast((m1 >> ti.cast(i - 32, ti.u32)) & ti.u32(1), ti.i32)
        elif i < 96:
            bit = ti.cast((m2 >> ti.cast(i - 64, ti.u32)) & ti.u32(1), ti.i32)
        else:
            bit = ti.cast((m3 >> ti.cast(i - 96, ti.u32)) & ti.u32(1), ti.i32)
        if bit != 0:
            n_hf += 1
            sigma_hf += pos
        else:
            n_hn += 1
            sigma_hn += pos
        i += 1
    return ti.Vector([n_hn, n_hf, sigma_hn, sigma_hf])


@ti.func
def _write_timeline_frontier_variant(
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    variant_idx: ti.i32,
    head_len: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    body_fever: ti.i32,
    body_normal: ti.i32,
) -> None:
    coeffs = _head_mask_coefficients(m0, m1, m2, m3, head_len)
    kernels_helpers.grid_frontier_body_fever[song_slot, ft_idx, ff_idx, variant_idx] = ti.cast(body_fever, ti.i16)
    kernels_helpers.grid_frontier_body_normal[song_slot, ft_idx, ff_idx, variant_idx] = ti.cast(body_normal, ti.i16)
    kernels_helpers.grid_frontier_N_hn[song_slot, ft_idx, ff_idx, variant_idx] = ti.cast(coeffs[0], ti.i16)
    kernels_helpers.grid_frontier_N_hf[song_slot, ft_idx, ff_idx, variant_idx] = ti.cast(coeffs[1], ti.i16)
    kernels_helpers.grid_frontier_Sigma_hn[song_slot, ft_idx, ff_idx, variant_idx] = ti.cast(coeffs[2], ti.i16)
    kernels_helpers.grid_frontier_Sigma_hf[song_slot, ft_idx, ff_idx, variant_idx] = ti.cast(coeffs[3], ti.i16)
    kernels_helpers.grid_frontier_masks_bits[song_slot, ft_idx, ff_idx, variant_idx, 0] = m0
    kernels_helpers.grid_frontier_masks_bits[song_slot, ft_idx, ff_idx, variant_idx, 1] = m1
    kernels_helpers.grid_frontier_masks_bits[song_slot, ft_idx, ff_idx, variant_idx, 2] = m2
    kernels_helpers.grid_frontier_masks_bits[song_slot, ft_idx, ff_idx, variant_idx, 3] = m3


@ti.func
def _timeline_surface_equal(a: ti.template(), b: ti.template()) -> ti.i32:
    same: ti.i32 = 0
    if (
        a.m0 == b.m0
        and a.m1 == b.m1
        and a.m2 == b.m2
        and a.m3 == b.m3
        and a.body_fever == b.body_fever
        and a.body_normal == b.body_normal
    ):
        same = 1
    return same


@ti.func
def _timeline_surface_dominates(a: ti.template(), b: ti.template()) -> ti.i32:
    dominates: ti.i32 = 0
    a_contains_b_head = (
        ((a.m0 | b.m0) == a.m0)
        and ((a.m1 | b.m1) == a.m1)
        and ((a.m2 | b.m2) == a.m2)
        and ((a.m3 | b.m3) == a.m3)
    )
    if a_contains_b_head and a.body_fever >= b.body_fever and a.body_normal <= b.body_normal:
        dominates = 1
    return dominates


@ti.func
def _timeline_surface_drop_candidate(
    cand: ti.template(),
    cand_idx: ti.i32,
    other: ti.template(),
    other_idx: ti.i32,
) -> ti.i32:
    drop: ti.i32 = 0
    if _timeline_surface_equal(other, cand) != 0:
        if other_idx < cand_idx:
            drop = 1
    elif _timeline_surface_dominates(other, cand) != 0:
        drop = 1
    return drop


@ti.func
def _write_exact_timeline_frontier4(
    song_slot: ti.i32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    head_len: ti.i32,
    v0: ti.template(),
    v1: ti.template(),
    v2: ti.template(),
    v3: ti.template(),
) -> None:
    drop0 = (
        _timeline_surface_drop_candidate(v0, ti.i32(0), v1, ti.i32(1))
        | _timeline_surface_drop_candidate(v0, ti.i32(0), v2, ti.i32(2))
        | _timeline_surface_drop_candidate(v0, ti.i32(0), v3, ti.i32(3))
    )
    drop1 = (
        _timeline_surface_drop_candidate(v1, ti.i32(1), v0, ti.i32(0))
        | _timeline_surface_drop_candidate(v1, ti.i32(1), v2, ti.i32(2))
        | _timeline_surface_drop_candidate(v1, ti.i32(1), v3, ti.i32(3))
    )
    drop2 = (
        _timeline_surface_drop_candidate(v2, ti.i32(2), v0, ti.i32(0))
        | _timeline_surface_drop_candidate(v2, ti.i32(2), v1, ti.i32(1))
        | _timeline_surface_drop_candidate(v2, ti.i32(2), v3, ti.i32(3))
    )
    drop3 = (
        _timeline_surface_drop_candidate(v3, ti.i32(3), v0, ti.i32(0))
        | _timeline_surface_drop_candidate(v3, ti.i32(3), v1, ti.i32(1))
        | _timeline_surface_drop_candidate(v3, ti.i32(3), v2, ti.i32(2))
    )

    out_idx: ti.i32 = 0
    if drop0 == 0:
        _write_timeline_frontier_variant(
            song_slot, ft_idx, ff_idx, out_idx, head_len, v0.m0, v0.m1, v0.m2, v0.m3, v0.body_fever, v0.body_normal
        )
        out_idx += 1
    if drop1 == 0:
        _write_timeline_frontier_variant(
            song_slot, ft_idx, ff_idx, out_idx, head_len, v1.m0, v1.m1, v1.m2, v1.m3, v1.body_fever, v1.body_normal
        )
        out_idx += 1
    if drop2 == 0:
        _write_timeline_frontier_variant(
            song_slot, ft_idx, ff_idx, out_idx, head_len, v2.m0, v2.m1, v2.m2, v2.m3, v2.body_fever, v2.body_normal
        )
        out_idx += 1
    if drop3 == 0:
        _write_timeline_frontier_variant(
            song_slot, ft_idx, ff_idx, out_idx, head_len, v3.m0, v3.m1, v3.m2, v3.m3, v3.body_fever, v3.body_normal
        )
        out_idx += 1

    kernels_helpers.grid_frontier_count[song_slot, ft_idx, ff_idx] = ti.cast(out_idx, ti.i8)


@ti.kernel
def compute_timeline_grid_kernel(
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    song_slot: ti.i32,  # Grid slot to write to (0-7)
    write_unpacked_masks: ti.i32,
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
        write_unpacked_masks: 1=write grid_fever_masks (compat), 0=skip unpacked mask writes
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)

    # Constants
    MAX_HEAD: ti.i32 = 100
    GRID_DIM: ti.i32 = 161

    # Precompute song-invariant values (game formula constants from constants.py)
    # Fever fill formula: non_fever_notes * FEVER_FILL_BASE_RATE * ff_factor
    non_fever_cas = ti.cast(total_notes - long_notes, ti.f32) * 0.333  # constants.FEVER_FILL_BASE_RATE
    # `last_note_time` is kept in the kernel signature for API stability.

    for idx in range(GRID_DIM * GRID_DIM):
        ft_idx = idx // GRID_DIM
        ff_idx = idx % GRID_DIM

        # Lookup multipliers from reference tables
        ff_factor = kernels_helpers.ref_ff_field[ff_idx]

        # Compute fill parameter
        non_fever_base_f = non_fever_cas * ff_factor
        non_fever_base = ti.i32(ti.ceil(non_fever_base_f))

        # Initialize fever mask bits (4 × u32 = 128 bits for first 100 notes)
        m0: ti.u32 = 0
        m1: ti.u32 = 0
        m2: ti.u32 = 0
        m3: ti.u32 = 0

        current_note = 0
        fever_section = 0
        fever_activations: ti.i32 = 0
        last_fever_end_idx: ti.i32 = 0
        body_fever: ti.i32 = 0
        body_normal: ti.i32 = 0
        head_len: ti.i32 = ti.min(total_notes, MAX_HEAD)

        # Single-pass simulation: build mask bits and body note counts together.
        while current_note < total_notes:
            fever_section += 1

            # Non-fever section: first section -1, later sections use base
            notes_to_fill = non_fever_base - 1 if fever_section == 1 else non_fever_base
            end_normal_idx = ti.min(current_note + notes_to_fill, total_notes)

            # Count normal body notes (notes >= MAX_HEAD) without per-note looping.
            body_normal_start = ti.max(current_note, MAX_HEAD)
            if end_normal_idx > body_normal_start:
                body_normal += end_normal_idx - body_normal_start

            current_note = end_normal_idx
            if current_note >= total_notes:
                break

            if current_note > 0:
                # Fever activates
                fever_activations += 1
                fever_end_idx = ti.min(kernels_helpers.fever_end_idx_song[current_note, ft_idx], total_notes)

                # Mark fever notes in bitmask (only first MAX_HEAD notes are represented).
                head_fever_end = ti.min(fever_end_idx, MAX_HEAD)
                masks = _or_head_mask_range(m0, m1, m2, m3, current_note, head_fever_end)
                m0 = masks[0]
                m1 = masks[1]
                m2 = masks[2]
                m3 = masks[3]

                # Count fever body notes (notes >= MAX_HEAD) without per-note looping.
                body_fever_start = ti.max(current_note, MAX_HEAD)
                if fever_end_idx > body_fever_start:
                    body_fever += fever_end_idx - body_fever_start

                last_fever_end_idx = fever_end_idx
                current_note = fever_end_idx
            else:
                break

        # Write outputs to specified song slot
        coeffs = _head_mask_coefficients(m0, m1, m2, m3, head_len)
        kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx] = ti.cast(body_fever, ti.i16)
        kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx] = ti.cast(body_normal, ti.i16)
        kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx] = ti.cast(head_len, ti.i8)
        kernels_helpers.grid_N_hn[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[0], ti.i16)
        kernels_helpers.grid_N_hf[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[1], ti.i16)
        kernels_helpers.grid_Sigma_hn[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[2], ti.i16)
        kernels_helpers.grid_Sigma_hf[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[3], ti.i16)
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0] = m0
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1] = m1
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2] = m2
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3] = m3
        kernels_helpers.grid_frontier_count[song_slot, ft_idx, ff_idx] = ti.cast(1, ti.i8)
        _write_timeline_frontier_variant(
            song_slot,
            ft_idx,
            ff_idx,
            ti.i32(0),
            head_len,
            m0,
            m1,
            m2,
            m3,
            body_fever,
            body_normal,
        )
        gap = ti.cast(total_notes - last_fever_end_idx, ti.i32)
        kernels_helpers.grid_gap[song_slot, ft_idx, ff_idx] = ti.cast(gap, ti.i16)
        kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx] = ti.cast(fever_activations, ti.i8)

        # Store compact signatures used for GA plateau bucketing / pruning.
        kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx] = _pack_mask_sig(m0, m1, m2, m3)
        kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx] = _pack_counts_sig(
            body_fever,
            body_normal,
            head_len,
            fever_activations,
            gap,
        )

        # Unpacked grid_fever_masks writes are intentionally skipped in production.
        # Bitpacked `grid_fever_masks_bits` is the canonical timeline representation.


@ti.func
def _binary_search_left_i32(arr, n: ti.i32, x: ti.i32) -> ti.i32:
    """Lower-bound search on a monotone non-decreasing i32 array."""
    lo = ti.i32(0)
    hi = n
    while lo < hi:
        mid = (lo + hi) >> 1
        if arr[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


@ti.func
def _propagate_carry_interval(lo: ti.i32, hi: ti.i32, g: ti.i32) -> ti.types.vector(2, ti.i32):
    """
    Carry propagation over chord groups using the interval propagation lemma:

      T_g([p,q]) = [max(l_g, p - Δ_g), max(u_g, q - Δ_g)]

    where Δ_g = c_g - c_{g-1}.
    """
    l_g = ti.cast(kernels_helpers.song_group_low_ms[g], ti.i32)
    u_g = ti.cast(kernels_helpers.song_group_high_ms[g], ti.i32)
    c_g = ti.cast(kernels_helpers.song_group_base_t_ms[g], ti.i32)
    c_prev = ti.cast(kernels_helpers.song_group_base_t_ms[g - 1], ti.i32)
    delta = c_g - c_prev
    if delta < 1:
        delta = 1
    out_lo = ti.max(l_g, lo - delta)
    out_hi = ti.max(u_g, hi - delta)
    return ti.Vector([out_lo, out_hi])


@ti.func
def _ceiling_anchor_ms(g: ti.i32, pick_high: ti.i32) -> ti.i32:
    lo = ti.cast(kernels_helpers.song_group_low_ms[g], ti.i32)
    hi = ti.cast(kernels_helpers.song_group_high_ms[g], ti.i32)
    return ti.select(pick_high != 0, hi, lo)


@ti.func
def _ceiling_head_bit(m0: ti.u32, m1: ti.u32, m2: ti.u32, m3: ti.u32, i: ti.i32) -> ti.i32:
    w = i >> 5
    b = i & 31
    bit = ti.u32(0)
    if w == 0:
        bit = (m0 >> ti.u32(b)) & ti.u32(1)
    elif w == 1:
        bit = (m1 >> ti.u32(b)) & ti.u32(1)
    elif w == 2:
        bit = (m2 >> ti.u32(b)) & ti.u32(1)
    else:
        bit = (m3 >> ti.u32(b)) & ti.u32(1)
    return ti.cast(bit, ti.i32)


@ti.func
def _ceiling_compare_score(
    head_len: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    body_fever: ti.i32,
    body_normal: ti.i32,
) -> ti.i32:
    base_f = ti.f32(10000.0)
    combo_mul_f = ti.f32(2.6)
    fever_mul_f = ti.f32(5.25)

    combo_val_per_note = ti.cast(base_f * combo_mul_f, ti.i32)
    fever_val_per_note = ti.cast(base_f * combo_mul_f * fever_mul_f, ti.i32)
    body_score = (body_fever * fever_val_per_note) + (body_normal * combo_val_per_note)

    factor = (combo_mul_f - ti.f32(1.0)) * base_f / ti.f32(100.0)
    total_head = ti.i32(0)
    i = ti.i32(0)
    while i < head_len:
        current_ramp_val = base_f + (ti.cast(i + 1, ti.f32) * factor)
        if _ceiling_head_bit(m0, m1, m2, m3, i) != 0:
            total_head += ti.cast(current_ramp_val * fever_mul_f, ti.i32)
        else:
            total_head += ti.cast(current_ramp_val, ti.i32)
        i += 1

    return body_score + total_head


@ti.func
def _ceiling_variant_is_better(
    cand: ti.template(),
    cand_score: ti.i32,
    best: ti.template(),
    best_score: ti.i32,
) -> ti.i32:
    better = ti.i32(0)
    if cand_score > best_score:
        better = 1
    elif cand_score == best_score:
        if cand.body_fever > best.body_fever:
            better = 1
        elif cand.body_fever == best.body_fever:
            if cand.m3 > best.m3:
                better = 1
            elif cand.m3 == best.m3:
                if cand.m2 > best.m2:
                    better = 1
                elif cand.m2 == best.m2:
                    if cand.m1 > best.m1:
                        better = 1
                    elif cand.m1 == best.m1 and cand.m0 > best.m0:
                        better = 1
    return better


_CeilingCellResult = ti.types.struct(
    m0=ti.u32,
    m1=ti.u32,
    m2=ti.u32,
    m3=ti.u32,
    body_fever=ti.i32,
    body_normal=ti.i32,
    fever_activations=ti.i32,
    gap=ti.i32,
)


@ti.func
def _simulate_ceiling_cell(
    n: ti.i32,
    gcount: ti.i32,
    fill_count: ti.i32,
    d_ms: ti.i32,
    pick_high: ti.i32,
    end_mode: ti.i32,
) -> _CeilingCellResult:
    MAX_HEAD: ti.i32 = 100

    m0 = ti.u32(0)
    m1 = ti.u32(0)
    m2 = ti.u32(0)
    m3 = ti.u32(0)
    body_fever = ti.i32(0)
    body_normal = ti.i32(0)
    fever_activations = ti.i32(0)
    last_fever_end_idx = ti.i32(0)

    current_note = ti.i32(0)
    fever_section = ti.i32(0)

    prev_group = ti.i32(-1)
    prev_carry = ti.i32(0)

    while current_note < n:
        fever_section += 1
        notes_to_fill = fill_count - 1 if fever_section == 1 else fill_count
        if notes_to_fill < 0:
            notes_to_fill = 0

        start_normal_idx = current_note
        end_normal_idx = ti.min(current_note + notes_to_fill, n)

        body_normal_start = ti.max(start_normal_idx, MAX_HEAD)
        if end_normal_idx > body_normal_start:
            body_normal += end_normal_idx - body_normal_start

        walk_note = start_normal_idx
        while walk_note < end_normal_idx:
            g = ti.cast(kernels_helpers.song_note_group_idx[walk_note], ti.i32)
            if g < 0:
                g = 0
            if g >= gcount:
                break

            if g != prev_group:
                anchor = _ceiling_anchor_ms(g, pick_high)
                if prev_group < 0:
                    prev_carry = anchor
                else:
                    c_g = ti.cast(kernels_helpers.song_group_base_t_ms[g], ti.i32)
                    c_prev = ti.cast(kernels_helpers.song_group_base_t_ms[prev_group], ti.i32)
                    delta = c_g - c_prev
                    if delta < 1:
                        delta = 1
                    prev_carry = ti.max(anchor, prev_carry - delta)
                prev_group = g

            group_end = n
            if (g + 1) < gcount:
                group_end = ti.cast(kernels_helpers.song_group_starts[g + 1], ti.i32)
            walk_note = ti.min(group_end, end_normal_idx)

        current_note = end_normal_idx
        if current_note >= n:
            break

        if current_note <= 0:
            break

        fever_activations += 1
        activation_note = current_note
        if activation_note >= n:
            break

        s = ti.cast(kernels_helpers.song_note_group_idx[activation_note], ti.i32)
        if s < 0:
            s = 0
        if s >= gcount:
            break

        if s != prev_group:
            anchor = _ceiling_anchor_ms(s, pick_high)
            if prev_group < 0:
                prev_carry = anchor
            else:
                c_s = ti.cast(kernels_helpers.song_group_base_t_ms[s], ti.i32)
                c_prev = ti.cast(kernels_helpers.song_group_base_t_ms[prev_group], ti.i32)
                delta = c_s - c_prev
                if delta < 1:
                    delta = 1
                prev_carry = ti.max(anchor, prev_carry - delta)
            prev_group = s

        r_act = prev_carry
        c_s = ti.cast(kernels_helpers.song_group_base_t_ms[s], ti.i32)
        Q = c_s + r_act + d_ms

        b_minus = _binary_search_left_i32(kernels_helpers.song_group_base_t_ms, gcount, Q - 80)
        b_plus = _binary_search_left_i32(kernels_helpers.song_group_base_t_ms, gcount, Q + 40)

        start_g = s + 1
        if b_minus < start_g:
            b_minus = start_g
        if b_plus < start_g:
            b_plus = start_g
        if b_minus > gcount:
            b_minus = gcount
        if b_plus > gcount:
            b_plus = gcount

        if end_mode != 0:
            # Variant: end fever as early as possible (first reachable out-group in the swing band).
            #
            # This intentionally sacrifices swing groups to shift subsequent activation indices earlier
            # (cascade), which can improve score vs the greedy "keep fever as long as feasible" variant.
            lo = r_act
            hi = r_act

            # Propagate through groups that are always in-fever under the global max offset bound (+80ms).
            g = start_g
            while g < b_minus:
                out = _propagate_carry_interval(lo, hi, g)
                lo = out[0]
                hi = out[1]
                g += 1

            out_group = ti.i32(-1)
            out_carry = ti.i32(0)

            g = b_minus
            while g < b_plus and g < gcount:
                out = _propagate_carry_interval(lo, hi, g)
                lo = out[0]
                hi = out[1]

                c_g = ti.cast(kernels_helpers.song_group_base_t_ms[g], ti.i32)
                out_threshold = Q - c_g

                if hi >= out_threshold:
                    out_group = g
                    # Choose the smallest carry that still forces this group out of fever.
                    out_carry = ti.max(lo, out_threshold)
                    break

                remain_hi = out_threshold - 1
                lo = ti.max(lo, ti.i32(-40))
                hi = ti.min(hi, remain_hi)
                g += 1

            fever_end_idx = n
            if out_group >= 0:
                fever_end_idx = ti.cast(kernels_helpers.song_group_starts[out_group], ti.i32)
            else:
                if b_plus < gcount:
                    out_group = b_plus
                    out = _propagate_carry_interval(lo, hi, out_group)
                    out_carry = out[0]
                    fever_end_idx = ti.cast(kernels_helpers.song_group_starts[out_group], ti.i32)
                else:
                    fever_end_idx = n

            if fever_end_idx < activation_note:
                fever_end_idx = activation_note
            if fever_end_idx > n:
                fever_end_idx = n

            masks = _or_head_mask_range(m0, m1, m2, m3, activation_note, fever_end_idx)
            m0 = masks[0]
            m1 = masks[1]
            m2 = masks[2]
            m3 = masks[3]

            body_fever_start = ti.max(activation_note, MAX_HEAD)
            if fever_end_idx > body_fever_start:
                body_fever += fever_end_idx - body_fever_start

            # Carry state after fever: we must instantiate an explicit carry for the out-group
            # (otherwise the early-end signature may be infeasible).
            if out_group >= 0 and out_group < gcount:
                prev_group = out_group
                prev_carry = out_carry
            else:
                prev_group = s
                prev_carry = r_act

            last_fever_end_idx = fever_end_idx
            current_note = fever_end_idx
            continue

        lo = r_act
        hi = r_act
        last_fever_group = s
        last_fever_hi = r_act
        g = start_g
        while g < b_minus:
            out = _propagate_carry_interval(lo, hi, g)
            lo = out[0]
            hi = out[1]
            last_fever_group = g
            last_fever_hi = hi
            g += 1

        exit_group = ti.i32(-1)
        g = b_minus
        while g < b_plus and g < gcount:
            prev_lo = lo
            prev_hi = hi
            out = _propagate_carry_interval(lo, hi, g)
            lo = out[0]
            hi = out[1]

            c_g = ti.cast(kernels_helpers.song_group_base_t_ms[g], ti.i32)
            remain_hi = Q - c_g - 1

            keep_lo = ti.max(lo, ti.i32(-40))
            keep_hi = ti.min(hi, remain_hi)

            if keep_lo <= keep_hi:
                lo = keep_lo
                hi = keep_hi
                last_fever_group = g
                last_fever_hi = hi
                g += 1
                continue

            exit_group = g
            lo = prev_lo
            hi = prev_hi
            break

        fever_end_idx = n
        if exit_group >= 0:
            fever_end_idx = ti.cast(kernels_helpers.song_group_starts[exit_group], ti.i32)
        else:
            if b_plus < gcount:
                g = b_plus
                _ = _propagate_carry_interval(lo, hi, g)
                fever_end_idx = ti.cast(kernels_helpers.song_group_starts[g], ti.i32)
            else:
                fever_end_idx = n

        if fever_end_idx < activation_note:
            fever_end_idx = activation_note
        if fever_end_idx > n:
            fever_end_idx = n

        masks = _or_head_mask_range(m0, m1, m2, m3, activation_note, fever_end_idx)
        m0 = masks[0]
        m1 = masks[1]
        m2 = masks[2]
        m3 = masks[3]

        body_fever_start = ti.max(activation_note, MAX_HEAD)
        if fever_end_idx > body_fever_start:
            body_fever += fever_end_idx - body_fever_start

        prev_group = last_fever_group
        prev_carry = last_fever_hi
        last_fever_end_idx = fever_end_idx
        current_note = fever_end_idx

    body_normal_start = ti.max(current_note, MAX_HEAD)
    if n > body_normal_start:
        body_normal += n - body_normal_start

    gap = n - last_fever_end_idx
    return _CeilingCellResult(
        m0=m0,
        m1=m1,
        m2=m2,
        m3=m3,
        body_fever=body_fever,
        body_normal=body_normal,
        fever_activations=fever_activations,
        gap=gap,
    )


@ti.kernel
def compute_timeline_grid_ceiling_envelope_kernel(
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    group_count: ti.i32,
    song_slot: ti.i32,
    write_unpacked_masks: ti.i32,
):
    """
    Compute all 161×161 fever timeline entries using analytical timing-envelope ceiling mode.

    This models per-chord Perfect-window offsets (with held-tail multiplier) and enforces
    non-decreasing event times.

    For each (FT, FF) cell we evaluate fast, fully-feasible variants that differ in:
      (a) how they choose a concrete carry during non-fever ("fill") segments, and
      (b) whether they greedily extend fever as long as feasible ("max") or end fever as early as possible ("min").

    Variants:
      - normal-hi: choose the latest nominal carry (group_high)
      - normal-lo: choose the earliest nominal carry (group_low)
      - fever-max: keep swing groups in fever whenever feasible
      - fever-min: end fever at the earliest reachable out-group in the swing band

    We emit the better variant via
    `_ceiling_compare_score()` (deterministic selection).

    Output format matches compute_timeline_grid_kernel: bitpacked head-fever masks + body counts + signatures.
    """
    # `write_unpacked_masks` is intentionally ignored: unpacked masks are derived from bits via
    # unpack_timeline_grid_masks_kernel() (debug/tests only).

    n_stat: ti.i32 = 161
    n: ti.i32 = ti.max(total_notes, 0)
    gcount: ti.i32 = ti.max(group_count, 0)
    MAX_HEAD: ti.i32 = 100
    head_len: ti.i32 = ti.min(n, MAX_HEAD)

    non_fever_cas: ti.f32 = ti.cast(ti.max(0, total_notes - long_notes), ti.f32) * ti.f32(0.333)
    fever_time_cas: ti.f32 = last_note_time * ti.f32(0.15) + ti.f32(0.15)

    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for ft_idx, ff_idx in ti.ndrange(n_stat, n_stat):
        # (1) Parameters for this (FT, FF) cell.
        ft_factor: ti.f32 = kernels_helpers.ref_ft_field[ft_idx]
        ff_factor: ti.f32 = kernels_helpers.ref_ff_field[ff_idx]

        raw_fill: ti.f32 = non_fever_cas * ff_factor
        fill_count: ti.i32 = ti.cast(ti.ceil(raw_fill), ti.i32)
        if fill_count < 1:
            fill_count = 1

        fever_time_sec: ti.f32 = fever_time_cas * ft_factor
        d_ms: ti.i32 = ti.cast(ti.ceil(fever_time_sec * ti.f32(1000.0)), ti.i32)
        if d_ms < 0:
            d_ms = 0

        # (2) Timeline simulation (4 variants) + deterministic selection.
        hi_max = _simulate_ceiling_cell(n, gcount, fill_count, d_ms, ti.i32(1), ti.i32(0))
        hi_min = _simulate_ceiling_cell(n, gcount, fill_count, d_ms, ti.i32(1), ti.i32(1))
        lo_max = _simulate_ceiling_cell(n, gcount, fill_count, d_ms, ti.i32(0), ti.i32(0))
        lo_min = _simulate_ceiling_cell(n, gcount, fill_count, d_ms, ti.i32(0), ti.i32(1))
        _write_exact_timeline_frontier4(song_slot, ft_idx, ff_idx, head_len, hi_max, hi_min, lo_max, lo_min)

        best = hi_max
        best_score = _ceiling_compare_score(
            head_len, best.m0, best.m1, best.m2, best.m3, best.body_fever, best.body_normal
        )

        cand = hi_min
        cand_score = _ceiling_compare_score(
            head_len, cand.m0, cand.m1, cand.m2, cand.m3, cand.body_fever, cand.body_normal
        )
        if _ceiling_variant_is_better(cand, cand_score, best, best_score) != 0:
            best = cand
            best_score = cand_score

        cand = lo_max
        cand_score = _ceiling_compare_score(
            head_len, cand.m0, cand.m1, cand.m2, cand.m3, cand.body_fever, cand.body_normal
        )
        if _ceiling_variant_is_better(cand, cand_score, best, best_score) != 0:
            best = cand
            best_score = cand_score

        cand = lo_min
        cand_score = _ceiling_compare_score(
            head_len, cand.m0, cand.m1, cand.m2, cand.m3, cand.body_fever, cand.body_normal
        )
        if _ceiling_variant_is_better(cand, cand_score, best, best_score) != 0:
            best = cand
            best_score = cand_score

        m0 = best.m0
        m1 = best.m1
        m2 = best.m2
        m3 = best.m3
        body_fever = best.body_fever
        body_normal = best.body_normal
        fever_activations = best.fever_activations
        gap = best.gap

        # Write outputs to specified song slot.
        coeffs = _head_mask_coefficients(m0, m1, m2, m3, head_len)
        kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx] = ti.cast(body_fever, ti.i16)
        kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx] = ti.cast(body_normal, ti.i16)
        kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx] = ti.cast(head_len, ti.i8)
        kernels_helpers.grid_N_hn[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[0], ti.i16)
        kernels_helpers.grid_N_hf[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[1], ti.i16)
        kernels_helpers.grid_Sigma_hn[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[2], ti.i16)
        kernels_helpers.grid_Sigma_hf[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[3], ti.i16)
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0] = m0
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1] = m1
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2] = m2
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3] = m3

        kernels_helpers.grid_gap[song_slot, ft_idx, ff_idx] = ti.cast(gap, ti.i16)
        kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx] = ti.cast(fever_activations, ti.i8)

        # Store compact signatures used for GA plateau bucketing / pruning.
        kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx] = _pack_mask_sig(m0, m1, m2, m3)
        kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx] = _pack_counts_sig(
            body_fever,
            body_normal,
            head_len,
            fever_activations,
            gap,
        )


@ti.kernel
def compute_timeline_grid_ceiling_envelope_reps_kernel(
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    group_count: ti.i32,
    song_slot: ti.i32,
    write_unpacked_masks: ti.i32,
    rep_ft_values: ti.types.ndarray(dtype=ti.i16, ndim=1),
    rep_ff_values: ti.types.ndarray(dtype=ti.i16, ndim=1),
    rep_ft_n: ti.i32,
    rep_ff_n: ti.i32,
):
    """
    Ceiling timeline precompute with exact cell deduplication by (fill_count, d_ms).

    For a fixed song, the ceiling kernel's output for a cell depends only on:
      - `fill_count` (a function of FF index), and
      - `d_ms` (a function of FT index).

    The caller supplies per-cell representative indices (rep_ft, rep_ff) such that
    all cells mapping to the same (fill_count, d_ms) pair share one representative
    cell, and only the representative cells satisfy:
      rep_ft[ft, ff] == ft and rep_ff[ft, ff] == ff.

    This kernel computes ONLY those representative cells. A follow-up scatter kernel
    must copy representative outputs into the rest of the grid.

    Correctness: exact, by construction, because the simulated signature is a pure
    function of (fill_count, d_ms) for a fixed song.
    """
    # `write_unpacked_masks` is intentionally ignored: unpacked masks are derived from bits via
    # unpack_timeline_grid_masks_kernel() (debug/tests only).

    n_stat: ti.i32 = 161
    n: ti.i32 = ti.max(total_notes, 0)
    gcount: ti.i32 = ti.max(group_count, 0)
    MAX_HEAD: ti.i32 = 100
    head_len: ti.i32 = ti.min(n, MAX_HEAD)

    non_fever_cas: ti.f32 = ti.cast(ti.max(0, total_notes - long_notes), ti.f32) * ti.f32(0.333)
    fever_time_cas: ti.f32 = last_note_time * ti.f32(0.15) + ti.f32(0.15)

    rep_ft_n_i: ti.i32 = ti.max(rep_ft_n, 0)
    rep_ff_n_i: ti.i32 = ti.max(rep_ff_n, 0)

    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for rep_i, rep_j in ti.ndrange(rep_ft_n_i, rep_ff_n_i):
        ft_idx = ti.cast(rep_ft_values[rep_i], ti.i32)
        ff_idx = ti.cast(rep_ff_values[rep_j], ti.i32)
        if ft_idx < 0 or ft_idx >= n_stat or ff_idx < 0 or ff_idx >= n_stat:
            continue

        # (1) Parameters for this (FT, FF) cell.
        ft_factor: ti.f32 = kernels_helpers.ref_ft_field[ft_idx]
        ff_factor: ti.f32 = kernels_helpers.ref_ff_field[ff_idx]

        raw_fill: ti.f32 = non_fever_cas * ff_factor
        fill_count: ti.i32 = ti.cast(ti.ceil(raw_fill), ti.i32)
        if fill_count < 1:
            fill_count = 1

        fever_time_sec: ti.f32 = fever_time_cas * ft_factor
        d_ms: ti.i32 = ti.cast(ti.ceil(fever_time_sec * ti.f32(1000.0)), ti.i32)
        if d_ms < 0:
            d_ms = 0

        # (2) Timeline simulation (4 variants) + deterministic selection.
        hi_max = _simulate_ceiling_cell(n, gcount, fill_count, d_ms, ti.i32(1), ti.i32(0))
        hi_min = _simulate_ceiling_cell(n, gcount, fill_count, d_ms, ti.i32(1), ti.i32(1))
        lo_max = _simulate_ceiling_cell(n, gcount, fill_count, d_ms, ti.i32(0), ti.i32(0))
        lo_min = _simulate_ceiling_cell(n, gcount, fill_count, d_ms, ti.i32(0), ti.i32(1))
        _write_exact_timeline_frontier4(song_slot, ft_idx, ff_idx, head_len, hi_max, hi_min, lo_max, lo_min)

        best = hi_max
        best_score = _ceiling_compare_score(
            head_len, best.m0, best.m1, best.m2, best.m3, best.body_fever, best.body_normal
        )

        cand = hi_min
        cand_score = _ceiling_compare_score(
            head_len, cand.m0, cand.m1, cand.m2, cand.m3, cand.body_fever, cand.body_normal
        )
        if _ceiling_variant_is_better(cand, cand_score, best, best_score) != 0:
            best = cand
            best_score = cand_score

        cand = lo_max
        cand_score = _ceiling_compare_score(
            head_len, cand.m0, cand.m1, cand.m2, cand.m3, cand.body_fever, cand.body_normal
        )
        if _ceiling_variant_is_better(cand, cand_score, best, best_score) != 0:
            best = cand
            best_score = cand_score

        cand = lo_min
        cand_score = _ceiling_compare_score(
            head_len, cand.m0, cand.m1, cand.m2, cand.m3, cand.body_fever, cand.body_normal
        )
        if _ceiling_variant_is_better(cand, cand_score, best, best_score) != 0:
            best = cand
            best_score = cand_score

        m0 = best.m0
        m1 = best.m1
        m2 = best.m2
        m3 = best.m3
        body_fever = best.body_fever
        body_normal = best.body_normal
        fever_activations = best.fever_activations
        gap = best.gap

        # Write outputs to specified song slot (representatives only).
        coeffs = _head_mask_coefficients(m0, m1, m2, m3, head_len)
        kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx] = ti.cast(body_fever, ti.i16)
        kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx] = ti.cast(body_normal, ti.i16)
        kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx] = ti.cast(head_len, ti.i8)
        kernels_helpers.grid_N_hn[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[0], ti.i16)
        kernels_helpers.grid_N_hf[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[1], ti.i16)
        kernels_helpers.grid_Sigma_hn[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[2], ti.i16)
        kernels_helpers.grid_Sigma_hf[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[3], ti.i16)
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0] = m0
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1] = m1
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2] = m2
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3] = m3

        kernels_helpers.grid_gap[song_slot, ft_idx, ff_idx] = ti.cast(gap, ti.i16)
        kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx] = ti.cast(fever_activations, ti.i8)

        # Store compact signatures used for GA plateau bucketing / pruning.
        kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx] = _pack_mask_sig(m0, m1, m2, m3)
        kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx] = _pack_counts_sig(
            body_fever,
            body_normal,
            head_len,
            fever_activations,
            gap,
        )


@ti.kernel
def scatter_timeline_grid_ceiling_envelope_from_reps_kernel(
    song_slot: ti.i32,
    rep_ft_by_ft: ti.types.ndarray(dtype=ti.i16, ndim=1),
    rep_ff_by_ff: ti.types.ndarray(dtype=ti.i16, ndim=1),
):
    """
    Fill the full 161×161 grid by copying representative-cell outputs.

    Must be called after compute_timeline_grid_ceiling_envelope_reps_kernel().
    """
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for ft_idx, ff_idx in ti.ndrange(161, 161):
        rft = ti.cast(rep_ft_by_ft[ft_idx], ti.i32)
        rff = ti.cast(rep_ff_by_ff[ff_idx], ti.i32)

        kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_count_body_fever[
            song_slot, rft, rff
        ]
        kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_count_body_normal[
            song_slot, rft, rff
        ]
        kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_head_len[song_slot, rft, rff]
        kernels_helpers.grid_N_hn[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_N_hn[song_slot, rft, rff]
        kernels_helpers.grid_N_hf[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_N_hf[song_slot, rft, rff]
        kernels_helpers.grid_Sigma_hn[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_Sigma_hn[song_slot, rft, rff]
        kernels_helpers.grid_Sigma_hf[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_Sigma_hf[song_slot, rft, rff]

        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0] = kernels_helpers.grid_fever_masks_bits[
            song_slot, rft, rff, 0
        ]
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1] = kernels_helpers.grid_fever_masks_bits[
            song_slot, rft, rff, 1
        ]
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2] = kernels_helpers.grid_fever_masks_bits[
            song_slot, rft, rff, 2
        ]
        kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3] = kernels_helpers.grid_fever_masks_bits[
            song_slot, rft, rff, 3
        ]
        kernels_helpers.grid_frontier_count[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_frontier_count[
            song_slot, rft, rff
        ]
        for variant_idx, word_idx in ti.ndrange(4, 4):
            kernels_helpers.grid_frontier_masks_bits[song_slot, ft_idx, ff_idx, variant_idx, word_idx] = (
                kernels_helpers.grid_frontier_masks_bits[song_slot, rft, rff, variant_idx, word_idx]
            )
        for variant_idx in range(4):
            kernels_helpers.grid_frontier_body_fever[song_slot, ft_idx, ff_idx, variant_idx] = (
                kernels_helpers.grid_frontier_body_fever[song_slot, rft, rff, variant_idx]
            )
            kernels_helpers.grid_frontier_body_normal[song_slot, ft_idx, ff_idx, variant_idx] = (
                kernels_helpers.grid_frontier_body_normal[song_slot, rft, rff, variant_idx]
            )
            kernels_helpers.grid_frontier_N_hn[song_slot, ft_idx, ff_idx, variant_idx] = (
                kernels_helpers.grid_frontier_N_hn[song_slot, rft, rff, variant_idx]
            )
            kernels_helpers.grid_frontier_N_hf[song_slot, ft_idx, ff_idx, variant_idx] = (
                kernels_helpers.grid_frontier_N_hf[song_slot, rft, rff, variant_idx]
            )
            kernels_helpers.grid_frontier_Sigma_hn[song_slot, ft_idx, ff_idx, variant_idx] = (
                kernels_helpers.grid_frontier_Sigma_hn[song_slot, rft, rff, variant_idx]
            )
            kernels_helpers.grid_frontier_Sigma_hf[song_slot, ft_idx, ff_idx, variant_idx] = (
                kernels_helpers.grid_frontier_Sigma_hf[song_slot, rft, rff, variant_idx]
            )

        kernels_helpers.grid_gap[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_gap[song_slot, rft, rff]
        kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_fever_activations[
            song_slot, rft, rff
        ]

        kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_sig0[song_slot, rft, rff]
        kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx] = kernels_helpers.grid_sig1[song_slot, rft, rff]


@ti.kernel
def compute_timeline_grid_signatures_kernel(song_slot: ti.i32):
    """
    Compute grid signature fields from existing grid outputs.

    Used after CPU upload paths that populate grid_* fields without running
    compute_timeline_grid_kernel(). Keeps signature generation GPU-only.
    """
    # Prefer 2D ndrange over div/mod on Metal (avoids backend edge cases).
    ti.loop_config(block_dim=kernels_helpers._KERNEL_BLOCK_DIM)
    for ft_idx, ff_idx in ti.ndrange(161, 161):
        m0 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 0]
        m1 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 1]
        m2 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 2]
        m3 = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, 3]

        bf = ti.cast(kernels_helpers.grid_count_body_fever[song_slot, ft_idx, ff_idx], ti.i32)
        bn = ti.cast(kernels_helpers.grid_count_body_normal[song_slot, ft_idx, ff_idx], ti.i32)
        hl = ti.cast(kernels_helpers.grid_head_len[song_slot, ft_idx, ff_idx], ti.i32)
        fa = ti.cast(kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx], ti.i32)
        gap = ti.cast(kernels_helpers.grid_gap[song_slot, ft_idx, ff_idx], ti.i32)
        coeffs = _head_mask_coefficients(m0, m1, m2, m3, hl)
        kernels_helpers.grid_N_hn[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[0], ti.i16)
        kernels_helpers.grid_N_hf[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[1], ti.i16)
        kernels_helpers.grid_Sigma_hn[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[2], ti.i16)
        kernels_helpers.grid_Sigma_hf[song_slot, ft_idx, ff_idx] = ti.cast(coeffs[3], ti.i16)

        kernels_helpers.grid_sig0[song_slot, ft_idx, ff_idx] = _pack_mask_sig(m0, m1, m2, m3)
        kernels_helpers.grid_sig1[song_slot, ft_idx, ff_idx] = _pack_counts_sig(bf, bn, hl, fa, gap)


@ti.kernel
def unpack_timeline_grid_masks_kernel(song_slot: ti.i32):
    """
    Unpack bitpacked head-fever masks (4×u32) into the legacy i8 mask grid.

    Production kernels use `grid_fever_masks_bits` as the canonical representation.
    This kernel exists for debug/tests that still compare against the unpacked
    `grid_fever_masks` representation.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    for ft_idx, ff_idx, k in ti.ndrange(161, 161, 100):
        # Unpacked masks are stored only for slot 0 to keep VRAM usage low.
        dst_slot = ti.i32(0)
        word = kernels_helpers.grid_fever_masks_bits[song_slot, ft_idx, ff_idx, k >> 5]
        bit = (word >> ti.u32(k & 31)) & ti.u32(1)
        kernels_helpers.grid_fever_masks[dst_slot, ft_idx, ff_idx, k] = ti.cast(bit, ti.i8)
