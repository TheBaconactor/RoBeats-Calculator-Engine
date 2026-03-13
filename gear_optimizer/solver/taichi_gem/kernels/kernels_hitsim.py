"""
Taichi Kernels - HumanHitSim Post-GA Refinement.

This module implements GPU-resident evaluation for the "exact boundary regime"
HumanHitSim refinement stage (ApplyTo=ALL). It evaluates deterministic alpha
regimes over grouped hit windows, computes compact fever timeline signatures,
scores a bounded candidate pool, plans regimes by signature change, and selects
the best regime/candidate.
"""

import taichi as ti

from . import kernels_helpers


@ti.func
def _interpolate_group_offset(g_low: ti.i32, g_high: ti.i32, alpha_num: ti.i32, alpha_den: ti.i32) -> ti.i32:
    # Mirrors hit_simulation._interpolate_group_offset (integer rounding, stable cuts).
    out = g_low
    if alpha_den > 0 and alpha_num > 0:
        if alpha_num >= alpha_den:
            out = g_high
        else:
            span = g_high - g_low
            if span > 0:
                out = g_low + ti.cast(
                    (ti.cast(span, ti.i64) * ti.cast(alpha_num, ti.i64) + ti.cast(alpha_den // 2, ti.i64))
                    // ti.cast(alpha_den, ti.i64),
                    ti.i32,
                )
    return out


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
def _or_head_mask_range(
    m0: ti.u32, m1: ti.u32, m2: ti.u32, m3: ti.u32, start: ti.i32, end: ti.i32
) -> ti.types.vector(4, ti.u32):
    # OR a contiguous [start, end) range into 4x u32 head mask words (clipped to [0,100)).
    s = ti.max(0, start)
    e = ti.min(100, end)
    if e > s:
        if s < 32:
            m0 |= _mask_range_u32(s, ti.min(e, 32))
        if e > 32 and s < 64:
            m1 |= _mask_range_u32(ti.max(0, s - 32), ti.min(e, 64) - 32)
        if e > 64 and s < 96:
            m2 |= _mask_range_u32(ti.max(0, s - 64), ti.min(e, 96) - 64)
        if e > 96 and s < 100:
            m3 |= _mask_range_u32(ti.max(0, s - 96), e - 96)
    return ti.Vector([m0, m1, m2, m3], dt=ti.u32)


@ti.func
def _binary_search_left_group_event_from(batch_slot: ti.i32, n: ti.i32, value: ti.i32, lo: ti.i32) -> ti.i32:
    # Leftmost index i in [lo, n) where group_event[i] >= value (or n if none).
    l = ti.max(0, lo)
    r = ti.max(l, n)
    while l < r:
        mid = (l + r) >> 1
        if kernels_helpers.hitsim_batch_group_event_ms[batch_slot, mid] < value:
            l = mid + 1
        else:
            r = mid
    return l


@ti.func
def _compute_row_signature(
    batch_slot: ti.i32,
    group_count: ti.i32,
    note_count: ti.i32,
    non_fever_base: ti.i32,
    fever_time_ms: ti.i32,
) -> tuple[ti.types.vector(3, ti.i32), ti.types.vector(4, ti.u32)]:
    # Compact signature: head_len, body_fever, body_normal, + 4x u32 head mask words.
    head_len = ti.min(note_count, 100)
    m0 = ti.u32(0)
    m1 = ti.u32(0)
    m2 = ti.u32(0)
    m3 = ti.u32(0)

    current_note_idx = ti.i32(0)
    fever_section = ti.i32(0)
    body_fever = ti.i32(0)

    while current_note_idx < note_count:
        fever_section += 1
        notes_to_fill = non_fever_base - 1 if fever_section == 1 else non_fever_base
        if notes_to_fill < 0:
            notes_to_fill = 0
        end_normal_idx = current_note_idx + notes_to_fill
        if end_normal_idx > note_count:
            end_normal_idx = note_count
        current_note_idx = end_normal_idx
        if current_note_idx >= note_count:
            break
        if current_note_idx <= 0:
            break

        fever_start = current_note_idx
        g_start = kernels_helpers.hitsim_note_to_group[fever_start]
        start_event = kernels_helpers.hitsim_batch_group_event_ms[batch_slot, g_start]
        end_ms = start_event + fever_time_ms
        g_end = _binary_search_left_group_event_from(batch_slot, group_count, end_ms, g_start)

        fever_end_idx = note_count
        if g_end < group_count:
            fever_end_idx = kernels_helpers.hitsim_group_starts[g_end]
            if fever_end_idx < fever_start:
                fever_end_idx = fever_start

        if fever_start < head_len:
            vec = _or_head_mask_range(m0, m1, m2, m3, fever_start, ti.min(head_len, fever_end_idx))
            m0 = vec[0]
            m1 = vec[1]
            m2 = vec[2]
            m3 = vec[3]

        if fever_end_idx > 100:
            body_start = ti.max(100, fever_start)
            if fever_end_idx > body_start:
                body_fever += fever_end_idx - body_start

        current_note_idx = fever_end_idx

    body_normal = ti.max(0, note_count - head_len - body_fever)
    counts = ti.Vector([head_len, body_fever, body_normal], dt=ti.i32)
    bits = ti.Vector([m0, m1, m2, m3], dt=ti.u32)
    return counts, bits


@ti.func
def _row_sig_equal(alpha_a: ti.i32, alpha_b: ti.i32, row_idx: ti.i32) -> ti.i32:
    ca = kernels_helpers.hitsim_alpha_row_sig_counts[alpha_a, row_idx]
    cb = kernels_helpers.hitsim_alpha_row_sig_counts[alpha_b, row_idx]
    ba = kernels_helpers.hitsim_alpha_row_sig_bits[alpha_a, row_idx]
    bb = kernels_helpers.hitsim_alpha_row_sig_bits[alpha_b, row_idx]
    eq = ti.i32(1)
    for k in ti.static(range(3)):
        if ca[k] != cb[k]:
            eq = 0
    for k in ti.static(range(4)):
        if ba[k] != bb[k]:
            eq = 0
    return eq


@ti.func
def _gcd_i64(a: ti.i64, b: ti.i64) -> ti.i64:
    x = a
    if x < 0:
        x = -x
    y = b
    if y < 0:
        y = -y
    while y != 0:
        t = x % y
        x = y
        y = t
    return x


@ti.func
def _midpoint_fraction(
    left_num: ti.i32, left_den: ti.i32, right_num: ti.i32, right_den: ti.i32
) -> ti.types.vector(2, ti.i32):
    # Midpoint between two fractions: (L+R)/2, reduced.
    ln = ti.cast(left_num, ti.i64)
    ld = ti.cast(ti.max(1, left_den), ti.i64)
    rn = ti.cast(right_num, ti.i64)
    rd = ti.cast(ti.max(1, right_den), ti.i64)
    num = ln * rd + rn * ld
    den = ti.cast(2, ti.i64) * ld * rd
    g = _gcd_i64(num, den)
    if g > 1:
        num = num // g
        den = den // g
    return ti.Vector([ti.cast(num, ti.i32), ti.cast(den, ti.i32)], dt=ti.i32)


@ti.func
def _frac_less(a_num: ti.i32, a_den: ti.i32, b_num: ti.i32, b_den: ti.i32) -> ti.i32:
    # Compare two non-negative fractions a_num/a_den < b_num/b_den using i64 cross-multiply.
    an = ti.cast(a_num, ti.i64)
    ad = ti.cast(ti.max(1, a_den), ti.i64)
    bn = ti.cast(b_num, ti.i64)
    bd = ti.cast(ti.max(1, b_den), ti.i64)
    return ti.i32(1) if an * bd < bn * ad else ti.i32(0)


@ti.func
def _note_window_perfect(
    note_type: ti.i32,
    perfect_lower_ms: ti.i32,
    perfect_upper_ms: ti.i32,
    held_tail_type: ti.i32,
    held_tail_time_multiplier: ti.i32,
) -> ti.types.vector(3, ti.i32):
    mult = ti.i32(1)
    if note_type == held_tail_type:
        mult = ti.max(1, held_tail_time_multiplier)
    low = perfect_lower_ms * mult
    high = perfect_upper_ms * mult
    return ti.Vector([low, high, mult], dt=ti.i32)


@ti.func
def _note_window_great(
    mult: ti.i32,
    perfect_low_ms: ti.i32,
    perfect_upper_ms: ti.i32,
    great_lower_ms: ti.i32,
    great_extra_upper_ms: ti.i32,
    great_mode_code: ti.i32,
) -> ti.types.vector(2, ti.i32):
    # Mirrors hit_simulation._build_per_note_great_window_ms (int32 path).
    great_upper_abs = (perfect_upper_ms + ti.max(0, great_extra_upper_ms)) * mult
    low = ti.i32(0)
    high = ti.i32(0)
    if great_mode_code == 0:  # late
        low = perfect_upper_ms * mult + 1
        high = great_upper_abs
    elif great_mode_code == 1:  # early
        low = perfect_low_ms + great_lower_ms * mult
        high = perfect_low_ms - 1
    else:  # full
        low = perfect_low_ms + great_lower_ms * mult
        high = great_upper_abs
    return ti.Vector([low, high], dt=ti.i32)


# ============================================================================
# UPLOAD KERNELS
# ============================================================================


@ti.kernel
def hitsim_upload_groups_kernel(
    n_notes: ti.i32,
    n_groups: ti.i32,
    starts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ends: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base_t: ti.types.ndarray(dtype=ti.i32, ndim=1),
    low_p: ti.types.ndarray(dtype=ti.i32, ndim=1),
    high_p: ti.types.ndarray(dtype=ti.i32, ndim=1),
    low_g: ti.types.ndarray(dtype=ti.i32, ndim=1),
    high_g: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    kernels_helpers.hitsim_note_count[0] = n_notes
    kernels_helpers.hitsim_group_count[0] = n_groups
    for g in range(n_groups):
        kernels_helpers.hitsim_group_starts[g] = starts[g]
        kernels_helpers.hitsim_group_ends[g] = ends[g]
        kernels_helpers.hitsim_group_base_t[g] = base_t[g]
        kernels_helpers.hitsim_group_low_perfect[g] = low_p[g]
        kernels_helpers.hitsim_group_high_perfect[g] = high_p[g]
        kernels_helpers.hitsim_group_low_great[g] = low_g[g]
        kernels_helpers.hitsim_group_high_great[g] = high_g[g]


@ti.kernel
def hitsim_build_note_to_group_kernel(n_groups: ti.i32, n_notes: ti.i32):
    for g in range(n_groups):
        s = kernels_helpers.hitsim_group_starts[g]
        e = kernels_helpers.hitsim_group_ends[g]
        if e > n_notes:
            e = n_notes
        for i in range(s, e):
            kernels_helpers.hitsim_note_to_group[i] = g


@ti.kernel
def hitsim_upload_alphas_kernel(
    n_alphas: ti.i32,
    alpha_num: ti.types.ndarray(dtype=ti.i32, ndim=1),
    alpha_den: ti.types.ndarray(dtype=ti.i32, ndim=1),
    left_num: ti.types.ndarray(dtype=ti.i32, ndim=1),
    left_den: ti.types.ndarray(dtype=ti.i32, ndim=1),
    right_num: ti.types.ndarray(dtype=ti.i32, ndim=1),
    right_den: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    kernels_helpers.hitsim_alpha_count[0] = n_alphas
    for i in range(n_alphas):
        kernels_helpers.hitsim_alpha_num[i] = alpha_num[i]
        kernels_helpers.hitsim_alpha_den[i] = alpha_den[i]
        kernels_helpers.hitsim_alpha_left_num[i] = left_num[i]
        kernels_helpers.hitsim_alpha_left_den[i] = left_den[i]
        kernels_helpers.hitsim_alpha_right_num[i] = right_num[i]
        kernels_helpers.hitsim_alpha_right_den[i] = right_den[i]


@ti.kernel
def hitsim_upload_rows_kernel(
    n_rows: ti.i32,
    non_fever_base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    fever_time_ms: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    kernels_helpers.hitsim_row_count[0] = n_rows
    for i in range(n_rows):
        kernels_helpers.hitsim_row_non_fever_base[i] = non_fever_base[i]
        kernels_helpers.hitsim_row_fever_time_ms[i] = fever_time_ms[i]


@ti.kernel
def hitsim_upload_candidates_kernel(
    n_candidates: ti.i32,
    row_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base_value: ti.types.ndarray(dtype=ti.f32, ndim=1),
    combo_mul: ti.types.ndarray(dtype=ti.f32, ndim=1),
    fever_mul: ti.types.ndarray(dtype=ti.f32, ndim=1),
):
    kernels_helpers.hitsim_candidate_count[0] = n_candidates
    for i in range(n_candidates):
        kernels_helpers.hitsim_candidate_row_idx[i] = row_idx[i]
        kernels_helpers.hitsim_candidate_base_value[i] = base_value[i]
        kernels_helpers.hitsim_candidate_combo_mul[i] = combo_mul[i]
        kernels_helpers.hitsim_candidate_fever_mul[i] = fever_mul[i]


@ti.kernel
def hitsim_build_groups_from_notes_kernel(
    n_notes: ti.i32,
    ts_ms: ti.types.ndarray(dtype=ti.i32, ndim=1),
    note_types: ti.types.ndarray(dtype=ti.i16, ndim=1),
    perfect_lower_ms: ti.i32,
    perfect_upper_ms: ti.i32,
    held_tail_type: ti.i32,
    held_tail_time_multiplier: ti.i32,
    great_lower_ms: ti.i32,
    great_extra_upper_ms: ti.i32,
    great_mode_code: ti.i32,
):
    """
    GPU-resident grouped-window prep (replaces CPU _prepare_grouped_hit_windows):
    - chord grouping by identical timestamp_ms runs
    - per-group window aggregation (Perfect + Great) with tail multipliers
    - note->group mapping (needed for fever timeline signature on GPU)

    Inputs:
      ts_ms: int32 ms timestamps (already quantized to match server floor rules)
      note_types: int16 note type codes (held tail uses multiplier)
    """
    kernels_helpers.hitsim_note_count[0] = n_notes
    kernels_helpers.hitsim_group_count[0] = 0

    if n_notes > 0:
        g = ti.i32(-1)
        prev_ts = ti.i32(0)

        cur_start = ti.i32(0)
        cur_base_t = ti.i32(0)
        cur_low_p = ti.i32(0)
        cur_high_p = ti.i32(0)
        cur_low_g = ti.i32(0)
        cur_high_g = ti.i32(0)

        ti.loop_config(serialize=True)
        for i in range(n_notes):
            t = ts_ms[i]
            nt = ti.cast(note_types[i], ti.i32)

            p = _note_window_perfect(
                nt,
                perfect_lower_ms=perfect_lower_ms,
                perfect_upper_ms=perfect_upper_ms,
                held_tail_type=held_tail_type,
                held_tail_time_multiplier=held_tail_time_multiplier,
            )
            p_low = p[0]
            p_high = p[1]
            mult = p[2]

            gg = _note_window_great(
                mult,
                perfect_low_ms=p_low,
                perfect_upper_ms=perfect_upper_ms,
                great_lower_ms=great_lower_ms,
                great_extra_upper_ms=great_extra_upper_ms,
                great_mode_code=great_mode_code,
            )
            g_low = gg[0]
            g_high = gg[1]

            is_new = ti.i32(0)
            if i == 0:
                is_new = 1
            elif t != prev_ts:
                is_new = 1

            if is_new != 0:
                # Close previous group.
                if g >= 0:
                    kernels_helpers.hitsim_group_starts[g] = cur_start
                    kernels_helpers.hitsim_group_ends[g] = i
                    kernels_helpers.hitsim_group_base_t[g] = cur_base_t

                    if cur_low_p > cur_high_p:
                        tmp = cur_low_p
                        cur_low_p = cur_high_p
                        cur_high_p = tmp
                    if cur_low_g > cur_high_g:
                        tmp2 = cur_low_g
                        cur_low_g = cur_high_g
                        cur_high_g = tmp2

                    kernels_helpers.hitsim_group_low_perfect[g] = cur_low_p
                    kernels_helpers.hitsim_group_high_perfect[g] = cur_high_p
                    kernels_helpers.hitsim_group_low_great[g] = cur_low_g
                    kernels_helpers.hitsim_group_high_great[g] = cur_high_g

                # Start new group.
                g = g + 1
                cur_start = i
                cur_base_t = t
                cur_low_p = p_low
                cur_high_p = p_high
                cur_low_g = g_low
                cur_high_g = g_high
            else:
                # Aggregate within group.
                if p_low > cur_low_p:
                    cur_low_p = p_low
                if p_high < cur_high_p:
                    cur_high_p = p_high
                if g_low > cur_low_g:
                    cur_low_g = g_low
                if g_high < cur_high_g:
                    cur_high_g = g_high

            kernels_helpers.hitsim_note_to_group[i] = g
            prev_ts = t

        # Close final group.
        if g >= 0:
            kernels_helpers.hitsim_group_starts[g] = cur_start
            kernels_helpers.hitsim_group_ends[g] = n_notes
            kernels_helpers.hitsim_group_base_t[g] = cur_base_t

            if cur_low_p > cur_high_p:
                tmp = cur_low_p
                cur_low_p = cur_high_p
                cur_high_p = tmp
            if cur_low_g > cur_high_g:
                tmp2 = cur_low_g
                cur_low_g = cur_high_g
                cur_high_g = tmp2

            kernels_helpers.hitsim_group_low_perfect[g] = cur_low_p
            kernels_helpers.hitsim_group_high_perfect[g] = cur_high_p
            kernels_helpers.hitsim_group_low_great[g] = cur_low_g
            kernels_helpers.hitsim_group_high_great[g] = cur_high_g

        kernels_helpers.hitsim_group_count[0] = g + 1


@ti.kernel
def hitsim_build_exact_alpha_regimes_kernel(max_alphas: ti.i32, max_span: ti.i32):
    """
    GPU-resident exact alpha regime enumeration (replaces CPU _build_exact_alpha_regimes).

    Builds the global cut list induced by all positive group spans, sorts+uniques
    it, then emits raw alpha regimes as midpoint fractions between adjacent cuts.
    """
    kernels_helpers.hitsim_alpha_count[0] = 0
    kernels_helpers.hitsim_cut_count[0] = 0

    group_count = kernels_helpers.hitsim_group_count[0]
    if group_count > 0:
        max_span_eff = ti.max(1, max_span)

        # Clear span-used histogram.
        ti.loop_config(serialize=True)
        for s in range(max_span_eff + 1):
            kernels_helpers.hitsim_span_used[s] = 0

        overflow = ti.i32(0)
        have_span = ti.i32(0)

        # Mark unique spans present across groups (Perfect spans only, matches CPU).
        ti.loop_config(serialize=True)
        for g in range(group_count):
            span = kernels_helpers.hitsim_group_high_perfect[g] - kernels_helpers.hitsim_group_low_perfect[g]
            if span <= 0:
                continue
            if span > max_span_eff:
                overflow = 1
                continue
            kernels_helpers.hitsim_span_used[span] = 1
            have_span = 1

        if overflow == 0 and have_span != 0:
            # Build cut list: 0, all boundary points, 1.
            max_cuts = max_alphas + 2
            cut_count = ti.i32(0)
            kernels_helpers.hitsim_cut_num[0] = 0
            kernels_helpers.hitsim_cut_den[0] = 1
            cut_count = 1

            ti.loop_config(serialize=True)
            for span in range(1, max_span_eff + 1):
                if kernels_helpers.hitsim_span_used[span] == 0:
                    continue
                den0 = ti.i32(2) * span
                for step in range(span):
                    if cut_count >= max_cuts - 1:
                        overflow = 1
                        break
                    num0 = ti.i32(2 * step + 1)
                    g0 = _gcd_i64(ti.cast(num0, ti.i64), ti.cast(den0, ti.i64))
                    nn = ti.i32(num0)
                    dd = ti.i32(den0)
                    if g0 > 1:
                        nn = ti.cast(ti.cast(num0, ti.i64) // g0, ti.i32)
                        dd = ti.cast(ti.cast(den0, ti.i64) // g0, ti.i32)
                    kernels_helpers.hitsim_cut_num[cut_count] = nn
                    kernels_helpers.hitsim_cut_den[cut_count] = dd
                    cut_count += 1
                if overflow != 0:
                    break

            if overflow == 0:
                kernels_helpers.hitsim_cut_num[cut_count] = 1
                kernels_helpers.hitsim_cut_den[cut_count] = 1
                cut_count += 1

            if overflow == 0:
                # Insertion sort cuts by rational value.
                ti.loop_config(serialize=True)
                for i in range(1, cut_count):
                    j = i
                    while j > 0:
                        a_num = kernels_helpers.hitsim_cut_num[j]
                        a_den = kernels_helpers.hitsim_cut_den[j]
                        b_num = kernels_helpers.hitsim_cut_num[j - 1]
                        b_den = kernels_helpers.hitsim_cut_den[j - 1]
                        if _frac_less(a_num, a_den, b_num, b_den) != 0:
                            kernels_helpers.hitsim_cut_num[j] = b_num
                            kernels_helpers.hitsim_cut_den[j] = b_den
                            kernels_helpers.hitsim_cut_num[j - 1] = a_num
                            kernels_helpers.hitsim_cut_den[j - 1] = a_den
                            j -= 1
                        else:
                            break

                # Unique adjacent equal fractions in-place.
                unique_count = ti.i32(0)
                ti.loop_config(serialize=True)
                for i in range(cut_count):
                    n = kernels_helpers.hitsim_cut_num[i]
                    d = kernels_helpers.hitsim_cut_den[i]
                    if unique_count == 0:
                        kernels_helpers.hitsim_cut_num[0] = n
                        kernels_helpers.hitsim_cut_den[0] = d
                        unique_count = 1
                    else:
                        pn = kernels_helpers.hitsim_cut_num[unique_count - 1]
                        pd = kernels_helpers.hitsim_cut_den[unique_count - 1]
                        if n != pn or d != pd:
                            kernels_helpers.hitsim_cut_num[unique_count] = n
                            kernels_helpers.hitsim_cut_den[unique_count] = d
                            unique_count += 1

                kernels_helpers.hitsim_cut_count[0] = unique_count

                # Emit regimes between adjacent cuts.
                out_count = ti.i32(0)
                ti.loop_config(serialize=True)
                for i in range(unique_count - 1):
                    if out_count >= max_alphas:
                        overflow = 1
                        break
                    ln = kernels_helpers.hitsim_cut_num[i]
                    ld = kernels_helpers.hitsim_cut_den[i]
                    rn = kernels_helpers.hitsim_cut_num[i + 1]
                    rd = kernels_helpers.hitsim_cut_den[i + 1]
                    if ln == rn and ld == rd:
                        continue
                    mid = _midpoint_fraction(ln, ld, rn, rd)
                    kernels_helpers.hitsim_alpha_num[out_count] = mid[0]
                    kernels_helpers.hitsim_alpha_den[out_count] = mid[1]
                    kernels_helpers.hitsim_alpha_left_num[out_count] = ln
                    kernels_helpers.hitsim_alpha_left_den[out_count] = ld
                    kernels_helpers.hitsim_alpha_right_num[out_count] = rn
                    kernels_helpers.hitsim_alpha_right_den[out_count] = rd
                    out_count += 1

                if overflow == 0:
                    kernels_helpers.hitsim_alpha_count[0] = out_count

        # Fallbacks / error signaling.
        if overflow != 0:
            kernels_helpers.hitsim_alpha_count[0] = -1
        elif have_span == 0:
            # Degenerate: no positive spans => single default regime [0,1] midpoint 1/2.
            kernels_helpers.hitsim_alpha_count[0] = 1
            kernels_helpers.hitsim_alpha_num[0] = 1
            kernels_helpers.hitsim_alpha_den[0] = 2
            kernels_helpers.hitsim_alpha_left_num[0] = 0
            kernels_helpers.hitsim_alpha_left_den[0] = 1
            kernels_helpers.hitsim_alpha_right_num[0] = 1
            kernels_helpers.hitsim_alpha_right_den[0] = 1
            kernels_helpers.hitsim_cut_count[0] = 2
            kernels_helpers.hitsim_cut_num[0] = 0
            kernels_helpers.hitsim_cut_den[0] = 1
            kernels_helpers.hitsim_cut_num[1] = 1
            kernels_helpers.hitsim_cut_den[1] = 1


# ============================================================================
# EVALUATION KERNELS
# ============================================================================


@ti.kernel
def hitsim_compute_group_events_batch_kernel(alpha_start: ti.i32, batch_count: ti.i32, group_count: ti.i32):
    # Write raw (non-prefix-max) event-ms per group for each alpha in this batch.
    for flat in range(batch_count * group_count):
        b = flat // group_count
        g = flat - b * group_count
        alpha_idx = alpha_start + b
        alpha_num = kernels_helpers.hitsim_alpha_num[alpha_idx]
        alpha_den = kernels_helpers.hitsim_alpha_den[alpha_idx]
        base_t = kernels_helpers.hitsim_group_base_t[g]
        g_low = kernels_helpers.hitsim_group_low_perfect[g]
        g_high = kernels_helpers.hitsim_group_high_perfect[g]
        off = _interpolate_group_offset(g_low, g_high, alpha_num, alpha_den)
        kernels_helpers.hitsim_batch_group_event_ms[b, g] = base_t + off


@ti.kernel
def hitsim_prefix_max_batch_kernel(batch_count: ti.i32, group_count: ti.i32):
    # Monotonic clamp: event[g] = max(event[g], event[g-1]) for each alpha in batch.
    for b in range(batch_count):
        prev = ti.i32(-2147483648)
        for g in range(group_count):
            v = kernels_helpers.hitsim_batch_group_event_ms[b, g]
            if v < prev:
                v = prev
            else:
                prev = v
            kernels_helpers.hitsim_batch_group_event_ms[b, g] = v


@ti.kernel
def hitsim_eval_alpha_batch_kernel(
    alpha_start: ti.i32,
    batch_count: ti.i32,
    group_count: ti.i32,
    note_count: ti.i32,
    row_count: ti.i32,
    candidate_count: ti.i32,
):
    # Compute per-row signature rows (compact) and per-alpha best score among candidates.
    for b in range(batch_count):
        alpha_idx = alpha_start + b

        # Compute signatures for all unique param rows.
        for r in range(row_count):
            non_fever_base = kernels_helpers.hitsim_row_non_fever_base[r]
            fever_time_ms = kernels_helpers.hitsim_row_fever_time_ms[r]
            counts, bits = _compute_row_signature(b, group_count, note_count, non_fever_base, fever_time_ms)
            kernels_helpers.hitsim_alpha_row_sig_counts[alpha_idx, r] = counts
            kernels_helpers.hitsim_alpha_row_sig_bits[alpha_idx, r] = bits

        # Score all candidates (mapped to rows) and keep the best.
        best_score = ti.i32(-2147483648)
        best_candidate = ti.i32(0)
        for c in range(candidate_count):
            row_idx = kernels_helpers.hitsim_candidate_row_idx[c]
            counts = kernels_helpers.hitsim_alpha_row_sig_counts[alpha_idx, row_idx]
            bits = kernels_helpers.hitsim_alpha_row_sig_bits[alpha_idx, row_idx]
            score = kernels_helpers.calc_score_with_grid_bits(
                kernels_helpers.hitsim_candidate_base_value[c],
                kernels_helpers.hitsim_candidate_combo_mul[c],
                kernels_helpers.hitsim_candidate_fever_mul[c],
                bits[0],
                bits[1],
                bits[2],
                bits[3],
                counts[0],
                counts[1],
                counts[2],
            )
            if score > best_score:
                best_score = score
                best_candidate = c

        kernels_helpers.hitsim_alpha_best_score[alpha_idx] = best_score
        kernels_helpers.hitsim_alpha_best_candidate_idx[alpha_idx] = best_candidate


# ============================================================================
# REGIME PLANNING + SELECTION
# ============================================================================


@ti.kernel
def hitsim_plan_regimes_kernel(alpha_count: ti.i32, row_count: ti.i32, max_regimes: ti.i32, selection_mode: ti.i32):
    # selection_mode: 0=all, 1=head, 2=even
    kernels_helpers.hitsim_active_row_count[0] = 0
    kernels_helpers.hitsim_regime_count[0] = 0
    kernels_helpers.hitsim_selected_count[0] = 0

    # Active row detection: mark rows that change at least once across alpha list.
    ti.loop_config(serialize=True)
    for r in range(row_count):
        kernels_helpers.hitsim_active_row_mask[r] = 0
        last_alpha = ti.i32(0)
        changed = ti.i32(0)
        for a in range(1, alpha_count):
            if _row_sig_equal(a, last_alpha, r) == 0:
                changed = 1
                break
            last_alpha = a
        if changed != 0:
            kernels_helpers.hitsim_active_row_mask[r] = 1
            kernels_helpers.hitsim_active_row_count[0] = kernels_helpers.hitsim_active_row_count[0] + 1

    # Collapse adjacent raw intervals into regimes when no active row signature changed.
    full_count = ti.i32(0)
    if alpha_count > 0:
        regime_idx = ti.i32(0)
        cur_start = ti.i32(0)
        cur_left_num = kernels_helpers.hitsim_alpha_left_num[0]
        cur_left_den = kernels_helpers.hitsim_alpha_left_den[0]
        cur_right_num = kernels_helpers.hitsim_alpha_right_num[0]
        cur_right_den = kernels_helpers.hitsim_alpha_right_den[0]

        for a in range(1, alpha_count):
            boundary = ti.i32(0)
            for r in range(row_count):
                if kernels_helpers.hitsim_active_row_mask[r] != 0:
                    if _row_sig_equal(a, a - 1, r) == 0:
                        boundary = 1
            if boundary == 0:
                cur_right_num = kernels_helpers.hitsim_alpha_right_num[a]
                cur_right_den = kernels_helpers.hitsim_alpha_right_den[a]
                continue

            mid = _midpoint_fraction(cur_left_num, cur_left_den, cur_right_num, cur_right_den)
            kernels_helpers.hitsim_regime_start_alpha[regime_idx] = cur_start
            kernels_helpers.hitsim_regime_end_alpha[regime_idx] = a
            kernels_helpers.hitsim_regime_left_num[regime_idx] = cur_left_num
            kernels_helpers.hitsim_regime_left_den[regime_idx] = cur_left_den
            kernels_helpers.hitsim_regime_right_num[regime_idx] = cur_right_num
            kernels_helpers.hitsim_regime_right_den[regime_idx] = cur_right_den
            kernels_helpers.hitsim_regime_alpha_num[regime_idx] = mid[0]
            kernels_helpers.hitsim_regime_alpha_den[regime_idx] = mid[1]
            kernels_helpers.hitsim_regime_rep_alpha[regime_idx] = cur_start
            regime_idx += 1

            cur_start = a
            cur_left_num = kernels_helpers.hitsim_alpha_left_num[a]
            cur_left_den = kernels_helpers.hitsim_alpha_left_den[a]
            cur_right_num = kernels_helpers.hitsim_alpha_right_num[a]
            cur_right_den = kernels_helpers.hitsim_alpha_right_den[a]

        mid = _midpoint_fraction(cur_left_num, cur_left_den, cur_right_num, cur_right_den)
        kernels_helpers.hitsim_regime_start_alpha[regime_idx] = cur_start
        kernels_helpers.hitsim_regime_end_alpha[regime_idx] = alpha_count
        kernels_helpers.hitsim_regime_left_num[regime_idx] = cur_left_num
        kernels_helpers.hitsim_regime_left_den[regime_idx] = cur_left_den
        kernels_helpers.hitsim_regime_right_num[regime_idx] = cur_right_num
        kernels_helpers.hitsim_regime_right_den[regime_idx] = cur_right_den
        kernels_helpers.hitsim_regime_alpha_num[regime_idx] = mid[0]
        kernels_helpers.hitsim_regime_alpha_den[regime_idx] = mid[1]
        kernels_helpers.hitsim_regime_rep_alpha[regime_idx] = cur_start
        regime_idx += 1

        full_count = regime_idx
        kernels_helpers.hitsim_regime_count[0] = full_count

    # Selection (optional cap).
    cap = ti.max(0, max_regimes)
    sel_count = full_count
    if cap > 0 and full_count > cap:
        sel_count = cap

    for i in range(full_count):
        kernels_helpers.hitsim_regime_selected_mask[i] = 0
    kernels_helpers.hitsim_selected_count[0] = 0

    if sel_count > 0:
        if cap <= 0 or full_count <= cap:
            for i in range(full_count):
                kernels_helpers.hitsim_regime_selected_mask[i] = 1
                kernels_helpers.hitsim_selected_regime_indices[i] = i
            kernels_helpers.hitsim_selected_count[0] = full_count
        elif selection_mode == 1:
            for i in range(sel_count):
                kernels_helpers.hitsim_regime_selected_mask[i] = 1
                kernels_helpers.hitsim_selected_regime_indices[i] = i
            kernels_helpers.hitsim_selected_count[0] = sel_count
        else:
            # Even spacing (default when capped, including "all" config value).
            if sel_count == 1:
                kernels_helpers.hitsim_regime_selected_mask[0] = 1
            else:
                for slot in range(sel_count):
                    num = slot * (full_count - 1)
                    den = sel_count - 1
                    idx = (num + (den // 2)) // den
                    idx = ti.max(0, ti.min(full_count - 1, idx))
                    kernels_helpers.hitsim_regime_selected_mask[idx] = 1

            picked = ti.i32(0)
            for i in range(full_count):
                if kernels_helpers.hitsim_regime_selected_mask[i] != 0:
                    picked += 1
            if picked < sel_count:
                for i in range(full_count):
                    if kernels_helpers.hitsim_regime_selected_mask[i] == 0:
                        kernels_helpers.hitsim_regime_selected_mask[i] = 1
                        picked += 1
                        if picked >= sel_count:
                            break

            kernels_helpers.hitsim_selected_count[0] = sel_count
            out_i = ti.i32(0)
            for i in range(full_count):
                if kernels_helpers.hitsim_regime_selected_mask[i] != 0:
                    kernels_helpers.hitsim_selected_regime_indices[out_i] = i
                    out_i += 1
                    if out_i >= sel_count:
                        break


@ti.kernel
def hitsim_select_best_regime_kernel(prev_score: ti.i32):
    n_sel = kernels_helpers.hitsim_selected_count[0]
    best_score = prev_score
    best_regime = ti.i32(-1)
    best_candidate = ti.i32(0)
    have_regime = ti.i32(0)

    ti.loop_config(serialize=True)
    for i in range(n_sel):
        r_idx = kernels_helpers.hitsim_selected_regime_indices[i]
        rep_alpha = kernels_helpers.hitsim_regime_rep_alpha[r_idx]
        score = kernels_helpers.hitsim_alpha_best_score[rep_alpha]
        cand = kernels_helpers.hitsim_alpha_best_candidate_idx[rep_alpha]
        if score > best_score or (have_regime == 0 and score >= best_score):
            best_score = score
            best_regime = r_idx
            best_candidate = cand
            have_regime = 1

    kernels_helpers.hitsim_best_score[0] = best_score
    kernels_helpers.hitsim_best_candidate_idx[0] = best_candidate
    kernels_helpers.hitsim_best_regime_idx[0] = best_regime

    if best_regime >= 0:
        kernels_helpers.hitsim_best_alpha_num[0] = kernels_helpers.hitsim_regime_alpha_num[best_regime]
        kernels_helpers.hitsim_best_alpha_den[0] = kernels_helpers.hitsim_regime_alpha_den[best_regime]
        kernels_helpers.hitsim_best_left_num[0] = kernels_helpers.hitsim_regime_left_num[best_regime]
        kernels_helpers.hitsim_best_left_den[0] = kernels_helpers.hitsim_regime_left_den[best_regime]
        kernels_helpers.hitsim_best_right_num[0] = kernels_helpers.hitsim_regime_right_num[best_regime]
        kernels_helpers.hitsim_best_right_den[0] = kernels_helpers.hitsim_regime_right_den[best_regime]
        kernels_helpers.hitsim_best_rep_alpha[0] = kernels_helpers.hitsim_regime_rep_alpha[best_regime]
    else:
        kernels_helpers.hitsim_best_alpha_num[0] = 0
        kernels_helpers.hitsim_best_alpha_den[0] = 1
        kernels_helpers.hitsim_best_left_num[0] = 0
        kernels_helpers.hitsim_best_left_den[0] = 1
        kernels_helpers.hitsim_best_right_num[0] = 1
        kernels_helpers.hitsim_best_right_den[0] = 1
        kernels_helpers.hitsim_best_rep_alpha[0] = 0


@ti.kernel
def hitsim_pack_scalar_outputs_kernel():
    # Packed scalar download to avoid many small GPU->CPU sync points.
    kernels_helpers.hitsim_scalar_out[0] = kernels_helpers.hitsim_best_score[0]
    kernels_helpers.hitsim_scalar_out[1] = kernels_helpers.hitsim_best_candidate_idx[0]
    kernels_helpers.hitsim_scalar_out[2] = kernels_helpers.hitsim_best_regime_idx[0]
    kernels_helpers.hitsim_scalar_out[3] = kernels_helpers.hitsim_best_alpha_num[0]
    kernels_helpers.hitsim_scalar_out[4] = kernels_helpers.hitsim_best_alpha_den[0]
    kernels_helpers.hitsim_scalar_out[5] = kernels_helpers.hitsim_best_left_num[0]
    kernels_helpers.hitsim_scalar_out[6] = kernels_helpers.hitsim_best_left_den[0]
    kernels_helpers.hitsim_scalar_out[7] = kernels_helpers.hitsim_best_right_num[0]
    kernels_helpers.hitsim_scalar_out[8] = kernels_helpers.hitsim_best_right_den[0]
    kernels_helpers.hitsim_scalar_out[9] = kernels_helpers.hitsim_best_rep_alpha[0]
    kernels_helpers.hitsim_scalar_out[10] = kernels_helpers.hitsim_active_row_count[0]
    kernels_helpers.hitsim_scalar_out[11] = kernels_helpers.hitsim_regime_count[0]
    kernels_helpers.hitsim_scalar_out[12] = kernels_helpers.hitsim_selected_count[0]
    kernels_helpers.hitsim_scalar_out[13] = kernels_helpers.hitsim_note_count[0]
    kernels_helpers.hitsim_scalar_out[14] = kernels_helpers.hitsim_group_count[0]
    kernels_helpers.hitsim_scalar_out[15] = kernels_helpers.hitsim_alpha_count[0]
    kernels_helpers.hitsim_scalar_out[16] = kernels_helpers.hitsim_cut_count[0]


@ti.kernel
def hitsim_stage_signature_rows_kernel(alpha_idx: ti.i32, row_count: ti.i32):
    for r in range(row_count):
        counts = kernels_helpers.hitsim_alpha_row_sig_counts[alpha_idx, r]
        bits = kernels_helpers.hitsim_alpha_row_sig_bits[alpha_idx, r]
        kernels_helpers.hitsim_sig_rows_staging[r, 0] = counts[0]
        kernels_helpers.hitsim_sig_rows_staging[r, 1] = counts[1]
        kernels_helpers.hitsim_sig_rows_staging[r, 2] = counts[2]
        kernels_helpers.hitsim_sig_rows_staging[r, 3] = ti.cast(bits[0], ti.i32)
        kernels_helpers.hitsim_sig_rows_staging[r, 4] = ti.cast(bits[1], ti.i32)
        kernels_helpers.hitsim_sig_rows_staging[r, 5] = ti.cast(bits[2], ti.i32)
        kernels_helpers.hitsim_sig_rows_staging[r, 6] = ti.cast(bits[3], ti.i32)


# ============================================================================
# BEST TIMESTAMP MATERIALIZATION
# ============================================================================


@ti.kernel
def hitsim_compute_group_events_tmp_kernel(group_count: ti.i32, alpha_num: ti.i32, alpha_den: ti.i32, use_great: ti.i32):
    for g in range(group_count):
        base_t = kernels_helpers.hitsim_group_base_t[g]
        g_low = kernels_helpers.hitsim_group_low_great[g] if use_great != 0 else kernels_helpers.hitsim_group_low_perfect[g]
        g_high = (
            kernels_helpers.hitsim_group_high_great[g] if use_great != 0 else kernels_helpers.hitsim_group_high_perfect[g]
        )
        off = _interpolate_group_offset(g_low, g_high, alpha_num, alpha_den)
        kernels_helpers.hitsim_group_event_tmp[g] = base_t + off


@ti.kernel
def hitsim_prefix_max_tmp_kernel(group_count: ti.i32):
    prev = ti.i32(-2147483648)
    ti.loop_config(serialize=True)
    for g in range(group_count):
        v = kernels_helpers.hitsim_group_event_tmp[g]
        if v < prev:
            v = prev
        else:
            prev = v
        kernels_helpers.hitsim_group_event_tmp[g] = v


@ti.kernel
def hitsim_broadcast_tmp_to_best_event_ms_kernel(group_count: ti.i32, note_count: ti.i32):
    for g in range(group_count):
        s = kernels_helpers.hitsim_group_starts[g]
        e = kernels_helpers.hitsim_group_ends[g]
        if e > note_count:
            e = note_count
        event = kernels_helpers.hitsim_group_event_tmp[g]
        for i in range(s, e):
            kernels_helpers.hitsim_best_event_ms[i] = event


@ti.kernel
def hitsim_broadcast_tmp_to_best_great_ms_kernel(group_count: ti.i32, note_count: ti.i32):
    for g in range(group_count):
        s = kernels_helpers.hitsim_group_starts[g]
        e = kernels_helpers.hitsim_group_ends[g]
        if e > note_count:
            e = note_count
        event = kernels_helpers.hitsim_group_event_tmp[g]
        for i in range(s, e):
            kernels_helpers.hitsim_best_great_ms[i] = event
