"""
ForceGreatsFinder GPU kernels (Taichi).

This module contains ONLY the FG finder kernels and their helper @ti.func's.
It reuses the shared scoring helpers from `gear_optimizer.solver.taichi_gem.kernels`
(reference lookups + score calculation).

Fields are bound at runtime via `force_greats.fields.bind_fields()`.
"""

import taichi as ti
from taichi.lang import simt

from gear_optimizer.core.parsing import env_flag, env_int

from ..kernels import kernels_helpers
from ..kernels.kernels_scoring import optimize_core_device_exact_bound_preloaded_bits
from .fields import (
    FG_CFG_DEDUPE_SIG_WORDS,
    FG_DOWNLOAD_BATCH_MAX,
    FG_DOWNLOAD_TOPK_MAX,
    FG_EXACT_DP_BATCH_MAX_ROWS,
    FG_EXACT_DP_MAX_NOTES,
    FG_EXACT_DP_PREFIX_HEAD_LEN,
    FG_EXACT_DP_SPARSE_HASH_SIZE,
    FG_EXACT_DP_SPARSE_MAX_STATES,
    FG_MAX_SECTIONS,
    FG_MAX_STAT,
    FG_SIGNATURE_FRONTIER_BATCH_MAX,
    FG_SIGNATURE_FRONTIER_MAX,
    FG_STAGE1_WAVE_SLOTS_MAX,
)

# Reuse the shared kernel block dim to keep launch config consistent with other kernels.
_KERNEL_BLOCK_DIM = kernels_helpers._KERNEL_BLOCK_DIM


# ============================================================================
# FIELD PLACEHOLDERS (bound by force_greats.fields.bind_fields)
# ============================================================================

song_timestamps = None
song_timestamps_great_candidate = None
fg_fever_end_idx_song = None
fg_fever_end_idx_great_candidate = None
fg_forced_counts = None
fg_section_forced_caps = None
fg_pair_caps = None
fg_ft_list = None
fg_ff_list = None
fg_cfg_start_list = None
fg_cfg_len_list = None
fg_cfg_total_len_list = None
fg_cfg_total_len_max = None
fg_cfg_base_list = None
fg_cfg_mode_list = None
fg_cfg_max_fp = None
fg_cfg_dedupe_hash = None
fg_cfg_dedupe_sig = None
fg_cfg_dedupe_rep_cfg_idx = None
fg_cfg_dedupe_rep_count = None
fg_cfg_dedupe_active = None

fg_best_final_score = None
fg_best_base_score = None
fg_best_cfg_idx = None
fg_best_ft = None
fg_best_ff = None
fg_best_g_pp = None
fg_best_g_cm = None
fg_best_g_fm = None
fg_best_g_ov = None
fg_best_score_penalty = None
fg_best_fill_penalty = None
fg_best_cfg_counts = None
fg_best_packed = None

fg_stage1_final_score = None
fg_stage1_base_score = None
fg_stage1_cfg_idx = None
fg_stage1_g_pp = None
fg_stage1_g_cm = None
fg_stage1_g_fm = None
fg_stage1_g_ov = None
fg_stage1_score_penalty = None
fg_stage1_fill_penalty = None

# Flat work items (GPU-friendly parallelization)
fg_flat_work_genome = None
fg_flat_work_ftff = None

# Packed 64-bit field for atomic (score, cfg_idx) updates
fg_stage1_packed = None
# Per-work-item staging for atomic-free Stage-1 reductions (u64 packed keys per wave slot).
fg_stage1_wave_best = None
# Compile-time flags set by force_greats.fields.bind_fields.
FG_STAGE1_HAS_AUX_FIELDS = False
FG_STAGE1_HAS_CFG_IDX_FIELD = False

# Global best fields for GPU-resident accumulation (persist across group calls)
fg_global_best_final_score = None
fg_global_best_base_score = None
fg_global_best_cfg_idx = None
fg_global_best_ft = None
fg_global_best_ff = None
fg_global_best_g_pp = None
fg_global_best_g_cm = None
fg_global_best_g_fm = None
fg_global_best_g_ov = None
fg_global_best_score_penalty = None
fg_global_best_fill_penalty = None
fg_global_best_cfg_counts = None
fg_global_best_packed = None

fg_input_base_score = None
fg_keep_mask = None
fg_selected_count = None
fg_selected_indices = None
fg_selected_packed = None
fg_selected_packed_batch = None
fg_frontier_base_score = None
fg_frontier_proxy_score = None
fg_frontier_priority = None
fg_frontier_force_keep = None
fg_frontier_center_bucket_ft = None
fg_frontier_center_bucket_ff = None
fg_frontier_timing_bucket = None
fg_frontier_selected_count = None
fg_frontier_selected_indices = None
fg_frontier_base_order = None
fg_frontier_fg_order = None
fg_frontier_selected_count_batch = None
fg_frontier_selected_indices_batch = None

# Exact FG DP (reference / research-only)
fg_exact_dp_w_prefix = None
fg_exact_dp_c_prefix = None
fg_exact_dp_dp = None
fg_exact_dp_best_delta = None
fg_exact_dp_counts = None

# Exact FG DP (sparse, full charts)
fg_exact_dp_full_w_prefix = None
fg_exact_dp_full_c_prefix = None
fg_exact_dp_sparse_hash_keys = None
fg_exact_dp_sparse_hash_vals = None
fg_exact_dp_sparse_state_i = None
fg_exact_dp_sparse_state_first = None
fg_exact_dp_sparse_state_carry = None
fg_exact_dp_sparse_dp = None
fg_exact_dp_sparse_policy_p = None
fg_exact_dp_sparse_policy_k = None
fg_exact_dp_sparse_order = None
fg_exact_dp_sparse_state_count = None
fg_exact_dp_sparse_best_delta = None
fg_exact_dp_sparse_counts = None
fg_exact_dp_sparse_states = None
fg_exact_dp_sparse_transitions = None
fg_exact_dp_sparse_overflow = None
fg_exact_dp_batch_raw_fill = None
fg_exact_dp_batch_non_fever_base = None
fg_exact_dp_batch_ft_idx = None
fg_exact_dp_batch_w_head_prefix = None
fg_exact_dp_batch_c_head_prefix = None
fg_exact_dp_batch_w_body = None
fg_exact_dp_batch_c_body = None
fg_exact_dp_batch_hash_keys = None
fg_exact_dp_batch_hash_vals = None
fg_exact_dp_batch_state_i = None
fg_exact_dp_batch_state_first = None
fg_exact_dp_batch_state_carry = None
fg_exact_dp_batch_dp = None
fg_exact_dp_batch_policy_p = None
fg_exact_dp_batch_policy_k = None
fg_exact_dp_batch_order = None
fg_exact_dp_batch_state_count = None
fg_exact_dp_batch_best_delta = None
fg_exact_dp_batch_counts = None
fg_exact_dp_batch_states = None
fg_exact_dp_batch_transitions = None
fg_exact_dp_batch_overflow = None


# ============================================================================
# DEBUG / TEST KERNELS
# ============================================================================
#
# These kernels are intended for test-only parity validation between the CPU
# analytical scorer and the GPU timeline computation semantics (carry_time,
# section-1 offset, binary-search-left end index).
#
# They are not used in production hot paths, but share the same song timestamp
# fields as the FG finder kernels.


@ti.func
def _fg_debug_pack_head_mask_range(m0: ti.u32, m1: ti.u32, m2: ti.u32, m3: ti.u32, start: ti.i32, end: ti.i32):
    """
    Set bits for [start, end) in the first 100 notes, packed as 4x u32.

    Only intended for small head-only loops inside debug kernels (<= 100 bits).
    """
    head_start: ti.i32 = ti.max(0, start)
    head_end: ti.i32 = ti.min(100, end)
    for i in range(head_start, head_end):
        if i < 32:
            m0 |= ti.cast(1, ti.u32) << ti.cast(i, ti.u32)
        elif i < 64:
            m1 |= ti.cast(1, ti.u32) << ti.cast(i - 32, ti.u32)
        elif i < 96:
            m2 |= ti.cast(1, ti.u32) << ti.cast(i - 64, ti.u32)
        else:
            m3 |= ti.cast(1, ti.u32) << ti.cast(i - 96, ti.u32)
    return m0, m1, m2, m3


@ti.kernel
def fg_debug_timeline_forced_counts_kernel(
    total_notes: ti.i32,
    raw_fever_fill: ti.f32,
    fever_duration: ti.f32,
    forced_counts: ti.types.ndarray(dtype=ti.i32, ndim=1),
    n_sections: ti.i32,
    out_mask_u32: ti.types.ndarray(dtype=ti.u32, ndim=1),
    out_counts_i32: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """
    Debug-only: compute the analytical fever head mask + body fever/normal counts from
    forced great counts (not FP targets).

    Output:
      - out_mask_u32[0:4] = (m0, m1, m2, m3)
      - out_counts_i32[0] = body_fever
      - out_counts_i32[1] = body_normal
      - out_counts_i32[2] = fever_activations
    """
    n: ti.i32 = ti.max(0, total_notes)
    base_ceil: ti.i32 = ti.cast(ti.ceil(raw_fever_fill), ti.i32)

    m0 = ti.cast(0, ti.u32)
    m1 = ti.cast(0, ti.u32)
    m2 = ti.cast(0, ti.u32)
    m3 = ti.cast(0, ti.u32)
    body_fever: ti.i32 = 0
    body_normal: ti.i32 = 0
    fever_acts: ti.i32 = 0

    current_idx: ti.i32 = 0
    sec: ti.i32 = 0
    carry_time: ti.f32 = 0.0

    # Matches CPU loop: while idx < total_notes and section < len(forced_counts) + 1
    while current_idx < n and sec < (n_sections + 1):
        forced: ti.i32 = 0
        if sec < n_sections:
            forced = forced_counts[sec]
        if forced < 0:
            forced = 0
        if forced > base_ceil:
            forced = base_ceil

        # notes_needed = ceil(raw_fill + forced*0.5) with section-1 offset.
        notes_needed: ti.i32 = ti.cast(ti.ceil(raw_fever_fill + ti.cast(forced, ti.f32) * 0.5), ti.i32)
        if sec == 0:
            notes_needed -= 1
        if notes_needed < 0:
            notes_needed = 0

        section_start: ti.i32 = current_idx
        current_idx += notes_needed

        if current_idx >= n:
            # Remaining body notes are normal.
            rem_start: ti.i32 = ti.max(100, section_start)
            if rem_start < n:
                body_normal += n - rem_start
            break

        # carry_time update: based on last forced note that contributes to fill.
        if forced > 0:
            forced_start: ti.i32 = section_start if sec == 0 else (section_start + 1)
            if forced_start < 0:
                forced_start = 0
            forced_end: ti.i32 = forced_start + forced - 1
            # End of fill segment is current_idx-1.
            if forced_end > (current_idx - 1):
                forced_end = current_idx - 1
            if forced_end >= forced_start and forced_end < n:
                forced_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                if forced_t > carry_time:
                    carry_time = forced_t

        fever_start_time: ti.f32 = song_timestamps[current_idx]
        if carry_time > fever_start_time:
            fever_start_time = carry_time
        fever_end_time: ti.f32 = fever_start_time + fever_duration
        fever_end_idx: ti.i32 = _binary_search_left_song_timestamps(n, fever_end_time)

        fever_acts += 1

        # Head mask: set bits for fever notes that fall within [0, 100).
        m0, m1, m2, m3 = _fg_debug_pack_head_mask_range(m0, m1, m2, m3, current_idx, ti.min(fever_end_idx, n))

        # Body fever count: notes in [current_idx, fever_end_idx) with idx >= 100.
        bf_start: ti.i32 = ti.max(100, current_idx)
        bf_end: ti.i32 = ti.min(fever_end_idx, n)
        if bf_end > bf_start:
            body_fever += bf_end - bf_start

        # Body normal for this non-fever segment: [section_start, current_idx) with idx >= 100.
        bn_start: ti.i32 = ti.max(100, section_start)
        bn_end: ti.i32 = ti.min(current_idx, n)
        if bn_end > bn_start:
            body_normal += bn_end - bn_start

        current_idx = fever_end_idx
        sec += 1

    # Remaining tail after the loop: normal body.
    tail_start: ti.i32 = ti.max(100, current_idx)
    if tail_start < n:
        body_normal += n - tail_start

    if out_mask_u32.shape[0] >= 4:
        out_mask_u32[0] = m0
        out_mask_u32[1] = m1
        out_mask_u32[2] = m2
        out_mask_u32[3] = m3
    if out_counts_i32.shape[0] >= 3:
        out_counts_i32[0] = body_fever
        out_counts_i32[1] = body_normal
        out_counts_i32[2] = fever_acts


# ============================================================================
# EXACT DP (reference / research-only)
# Superseded by fg_exact_dp_sparse_full_kernel for production use.
# Retained for parity tests and ablation studies on small synthetic charts.
# ============================================================================


@ti.kernel
def fg_exact_dp_reference_kernel(
    total_notes: ti.i32,
    raw_fill: ti.f32,
    non_fever_base: ti.i32,
    ft_idx: ti.i32,
    timing_aware: ti.i32,  # research parameter: 0=count_only, 1=timing_aware carry
):
    """Compute exact FG DP for a fixed stat point on small charts (research / parity reference only).

    SUPERSEDED: Use fg_exact_dp_sparse_full_kernel for production-size charts.
    This kernel uses a dense O(n^2) DP table capped at FG_EXACT_DP_MAX_NOTES (default 128).
    It is retained for GPU parity tests against the CPU reference and ablation studies.

    Inputs:
      - total_notes: number of notes in the uploaded timestamp prefix (<= FG_EXACT_DP_MAX_NOTES)
      - raw_fill / non_fever_base: fill model parameters (match CPU `evaluate_force_greats` semantics)
      - ft_idx: fever-time stat index (0..160)
      - timing_aware: 1 to enable carry-time via great-candidate timestamps, else 0

    Uses (device fields):
      - song_timestamps / song_timestamps_great_candidate
      - fg_fever_end_idx_song / fg_fever_end_idx_great_candidate
      - fg_exact_dp_w_prefix / fg_exact_dp_c_prefix (must be populated for [0..total_notes])

    Writes:
      - fg_exact_dp_best_delta[None]
      - fg_exact_dp_counts[0..FG_MAX_SECTIONS)

    Notes:
      - This kernel is intentionally serialized and intended for small synthetic charts.
      - DP table is stored in fg_exact_dp_dp for optional inspection.
    """
    # Defaults: no-op output.
    fg_exact_dp_best_delta[None] = ti.cast(0, ti.i64)
    for s in range(FG_MAX_SECTIONS):
        fg_exact_dp_counts[s] = ti.cast(-1, ti.i32)

    n: ti.i32 = ti.max(0, total_notes)
    ok = (n > 0) and (n <= FG_EXACT_DP_MAX_NOTES)
    if ok:
        ft: ti.i32 = ft_idx
        if ft < 0:
            ft = 0
        if ft > FG_MAX_STAT:
            ft = FG_MAX_STAT

        m: ti.i32 = non_fever_base
        if m < 0:
            m = 0

        # Max FP plateau index (dense 0..p_max).
        p_max: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(m, ti.f32) * 0.5), ti.i32) - m
        if p_max < 0:
            p_max = 0

        # Bottom-up DP for states with is_first=0. State: (i, carry_state)
        # carry_state=0 => NO_CARRY, else carry_idx=carry_state-1.
        ti.loop_config(serialize=True)
        for i_rev in range(n + 1):
            i: ti.i32 = n - i_rev
            ti.loop_config(serialize=True)
            for carry_state in range(n + 1):
                if i >= n:
                    fg_exact_dp_dp[i, carry_state] = ti.cast(0, ti.i64)
                    continue

                # Canonicalize carry for this state.
                cidx: ti.i32 = -1
                if timing_aware != 0 and carry_state > 0:
                    tmp: ti.i32 = carry_state - 1
                    if tmp >= 0 and tmp < n and song_timestamps_great_candidate[tmp] > song_timestamps[i]:
                        cidx = tmp

                # If even p=0 can't reach an activation note, there's no benefit.
                min_notes_to_fill: ti.i32 = m
                if min_notes_to_fill < 0:
                    min_notes_to_fill = 0
                if i + min_notes_to_fill >= n:
                    fg_exact_dp_dp[i, carry_state] = ti.cast(0, ti.i64)
                    continue

                best_val = ti.cast(0, ti.i64)
                forced_start_base: ti.i32 = i + 1
                if forced_start_base < 0:
                    forced_start_base = 0

                # Scan p in increasing order (matches CPU tie-breaking).
                ti.loop_config(serialize=True)
                for p in range(p_max + 1):
                    notes_to_fill: ti.i32 = m + p
                    if notes_to_fill < 0:
                        notes_to_fill = 0
                    end_normal: ti.i32 = i + notes_to_fill
                    if end_normal >= n:
                        break

                    # Candidate forced counts for this FP plateau: minimal k, plus optional k+1.
                    k0: ti.i32 = _forced_from_fp_target(raw_fill, m, p, m)
                    k1: ti.i32 = k0 + 1
                    has_k1: ti.i32 = 0
                    if k1 <= m:
                        fp1: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(k1, ti.f32) * 0.5), ti.i32) - m
                        if fp1 == p:
                            has_k1 = 1

                    ti.loop_config(serialize=True)
                    for cand in range(2):
                        if cand == 1 and has_k1 == 0:
                            continue
                        forced_val: ti.i32 = ti.select(cand == 0, k0, k1)
                        if forced_val < 0:
                            forced_val = 0
                        if forced_val > m:
                            forced_val = m

                        actual_notes: ti.i32 = end_normal - i
                        if actual_notes < 0:
                            actual_notes = 0
                        forced_applied: ti.i32 = ti.min(forced_val, actual_notes)
                        forced_start: ti.i32 = forced_start_base

                        penalty = ti.cast(0, ti.i64)
                        if forced_applied > 0 and forced_start < n:
                            end_excl: ti.i32 = forced_start + forced_applied
                            if end_excl > n:
                                end_excl = n
                            penalty = fg_exact_dp_c_prefix[end_excl] - fg_exact_dp_c_prefix[forced_start]

                        next_cidx: ti.i32 = cidx
                        if timing_aware != 0 and forced_applied > 0:
                            forced_end: ti.i32 = forced_start + forced_applied - 1
                            if forced_end >= forced_start and forced_end < end_normal and forced_end < n:
                                cand_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                                if next_cidx < 0:
                                    next_cidx = forced_end
                                else:
                                    if cand_t > song_timestamps_great_candidate[next_cidx]:
                                        next_cidx = forced_end

                        # Fever end depends on carry.
                        fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal, ft]
                        if timing_aware != 0 and next_cidx >= 0:
                            if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                                fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                        if fever_end_idx <= end_normal:
                            fever_end_idx = ti.min(n, end_normal + 1)
                        if fever_end_idx > n:
                            fever_end_idx = n

                        # Canonicalize carry for next state.
                        carry_next: ti.i32 = -1
                        if timing_aware != 0 and next_cidx >= 0 and fever_end_idx < n:
                            if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                                carry_next = next_cidx
                        carry_next_state: ti.i32 = carry_next + 1

                        fever_bonus = fg_exact_dp_w_prefix[fever_end_idx] - fg_exact_dp_w_prefix[end_normal]
                        future = fg_exact_dp_dp[fever_end_idx, carry_next_state]
                        total = fever_bonus - penalty + future
                        if total > best_val:
                            best_val = total

                fg_exact_dp_dp[i, carry_state] = best_val

        # Compute initial-state best (is_first=1, carry=NO_CARRY).
        best0 = ti.cast(0, ti.i64)
        min_notes_to_fill0: ti.i32 = m - 1
        if min_notes_to_fill0 < 0:
            min_notes_to_fill0 = 0
        if min_notes_to_fill0 < n:
            ti.loop_config(serialize=True)
            for p in range(p_max + 1):
                notes_to_fill0: ti.i32 = m + p - 1
                if notes_to_fill0 < 0:
                    notes_to_fill0 = 0
                end_normal0: ti.i32 = notes_to_fill0
                if end_normal0 >= n:
                    break

                k0: ti.i32 = _forced_from_fp_target(raw_fill, m, p, m)
                k1: ti.i32 = k0 + 1
                has_k1: ti.i32 = 0
                if k1 <= m:
                    fp1: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(k1, ti.f32) * 0.5), ti.i32) - m
                    if fp1 == p:
                        has_k1 = 1

                ti.loop_config(serialize=True)
                for cand in range(2):
                    if cand == 1 and has_k1 == 0:
                        continue
                    forced_val: ti.i32 = ti.select(cand == 0, k0, k1)
                    if forced_val < 0:
                        forced_val = 0
                    if forced_val > m:
                        forced_val = m

                    actual_notes0: ti.i32 = end_normal0
                    if actual_notes0 < 0:
                        actual_notes0 = 0
                    forced_applied: ti.i32 = ti.min(forced_val, actual_notes0)
                    forced_start: ti.i32 = 0

                    penalty = ti.cast(0, ti.i64)
                    if forced_applied > 0 and forced_start < n:
                        end_excl: ti.i32 = forced_start + forced_applied
                        if end_excl > n:
                            end_excl = n
                        penalty = fg_exact_dp_c_prefix[end_excl] - fg_exact_dp_c_prefix[forced_start]

                    next_cidx: ti.i32 = -1
                    if timing_aware != 0 and forced_applied > 0:
                        forced_end: ti.i32 = forced_start + forced_applied - 1
                        if forced_end >= forced_start and forced_end < end_normal0 and forced_end < n:
                            next_cidx = forced_end

                    fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal0, ft]
                    if timing_aware != 0 and next_cidx >= 0:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal0]:
                            fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                    if fever_end_idx <= end_normal0:
                        fever_end_idx = ti.min(n, end_normal0 + 1)
                    if fever_end_idx > n:
                        fever_end_idx = n

                    carry_next: ti.i32 = -1
                    if timing_aware != 0 and next_cidx >= 0 and fever_end_idx < n:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                            carry_next = next_cidx
                    carry_next_state: ti.i32 = carry_next + 1

                    fever_bonus = fg_exact_dp_w_prefix[fever_end_idx] - fg_exact_dp_w_prefix[end_normal0]
                    future = fg_exact_dp_dp[fever_end_idx, carry_next_state]
                    total = fever_bonus - penalty + future
                    if total > best0:
                        best0 = total

        fg_exact_dp_best_delta[None] = best0

        # Reconstruct a bounded prefix of forced-count decisions.
        i: ti.i32 = 0
        carry_idx: ti.i32 = -1
        is_first: ti.i32 = 1

        ti.loop_config(serialize=True)
        for step in range(FG_MAX_SECTIONS):
            if i >= n:
                break
            if timing_aware != 0 and carry_idx >= 0:
                if song_timestamps_great_candidate[carry_idx] <= song_timestamps[i]:
                    carry_idx = -1

            min_notes: ti.i32 = ti.select(is_first != 0, m - 1, m)
            if min_notes < 0:
                min_notes = 0
            if i + min_notes >= n:
                fg_exact_dp_counts[step] = ti.cast(0, ti.i32)
                break

            best_val = ti.cast(0, ti.i64)
            best_k: ti.i32 = 0
            best_next_i: ti.i32 = n
            best_next_carry: ti.i32 = -1

            forced_start_base: ti.i32 = ti.select(is_first != 0, i, i + 1)
            if forced_start_base < 0:
                forced_start_base = 0

            ti.loop_config(serialize=True)
            for p in range(p_max + 1):
                notes_to_fill: ti.i32 = m + p - ti.select(is_first != 0, 1, 0)
                if notes_to_fill < 0:
                    notes_to_fill = 0
                end_normal: ti.i32 = i + notes_to_fill
                if end_normal >= n:
                    break

                k0: ti.i32 = _forced_from_fp_target(raw_fill, m, p, m)
                k1: ti.i32 = k0 + 1
                has_k1: ti.i32 = 0
                if k1 <= m:
                    fp1: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(k1, ti.f32) * 0.5), ti.i32) - m
                    if fp1 == p:
                        has_k1 = 1

                ti.loop_config(serialize=True)
                for cand in range(2):
                    if cand == 1 and has_k1 == 0:
                        continue
                    forced_val: ti.i32 = ti.select(cand == 0, k0, k1)
                    if forced_val < 0:
                        forced_val = 0
                    if forced_val > m:
                        forced_val = m

                    actual_notes: ti.i32 = end_normal - i
                    if actual_notes < 0:
                        actual_notes = 0
                    forced_applied: ti.i32 = ti.min(forced_val, actual_notes)
                    forced_start: ti.i32 = forced_start_base

                    penalty = ti.cast(0, ti.i64)
                    if forced_applied > 0 and forced_start < n:
                        end_excl: ti.i32 = forced_start + forced_applied
                        if end_excl > n:
                            end_excl = n
                        penalty = fg_exact_dp_c_prefix[end_excl] - fg_exact_dp_c_prefix[forced_start]

                    next_cidx: ti.i32 = carry_idx
                    if timing_aware != 0 and forced_applied > 0:
                        forced_end: ti.i32 = forced_start + forced_applied - 1
                        if forced_end >= forced_start and forced_end < end_normal and forced_end < n:
                            cand_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                            if next_cidx < 0:
                                next_cidx = forced_end
                            else:
                                if cand_t > song_timestamps_great_candidate[next_cidx]:
                                    next_cidx = forced_end

                    fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal, ft]
                    if timing_aware != 0 and next_cidx >= 0:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                            fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                    if fever_end_idx <= end_normal:
                        fever_end_idx = ti.min(n, end_normal + 1)
                    if fever_end_idx > n:
                        fever_end_idx = n

                    carry_next: ti.i32 = -1
                    if timing_aware != 0 and next_cidx >= 0 and fever_end_idx < n:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                            carry_next = next_cidx
                    carry_next_state: ti.i32 = carry_next + 1

                    fever_bonus = fg_exact_dp_w_prefix[fever_end_idx] - fg_exact_dp_w_prefix[end_normal]
                    future = fg_exact_dp_dp[fever_end_idx, carry_next_state]
                    total = fever_bonus - penalty + future
                    if total > best_val:
                        best_val = total
                        best_k = forced_val
                        best_next_i = fever_end_idx
                        best_next_carry = carry_next

            fg_exact_dp_counts[step] = best_k
            i = best_next_i
            carry_idx = best_next_carry
            is_first = 0


@ti.func
def _fg_exact_dp_sparse_pack_key(i: ti.i32, is_first: ti.i32, carry_idx: ti.i32) -> ti.i64:
    # carry_idx stored as carry_idx+1 so -1 maps to 0.
    # Pack: [i:32][is_first:1][carry_state:31]
    return (ti.cast(i, ti.i64) << 32) | (ti.cast(is_first & 1, ti.i64) << 31) | ti.cast(carry_idx + 1, ti.i64)


@ti.func
def _fg_exact_dp_sparse_hash_index(key: ti.i64) -> ti.i32:
    # Simple xorshift mix; hash table size is a power of two.
    x = key ^ (key >> 33) ^ (key >> 17)
    return ti.cast(x, ti.i32) & ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE - 1, ti.i32)


@ti.func
def _fg_exact_dp_sparse_hash_lookup(key: ti.i64) -> ti.i32:
    mask: ti.i32 = ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE - 1, ti.i32)
    h: ti.i32 = _fg_exact_dp_sparse_hash_index(key)
    found: ti.i32 = -1
    step: ti.i32 = 0
    done: ti.i32 = 0
    while step < ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE, ti.i32) and done == 0:
        idx: ti.i32 = (h + step) & mask
        k = fg_exact_dp_sparse_hash_keys[idx]
        if k == key:
            found = ti.cast(fg_exact_dp_sparse_hash_vals[idx], ti.i32) - 1
            done = 1
        elif k == 0:
            done = 1
        else:
            step += 1
    return found


@ti.func
def _fg_exact_dp_sparse_hash_insert(key: ti.i64, i: ti.i32, is_first: ti.i32, carry_idx: ti.i32) -> ti.i32:
    mask: ti.i32 = ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE - 1, ti.i32)
    h: ti.i32 = _fg_exact_dp_sparse_hash_index(key)
    out_id: ti.i32 = -1
    step: ti.i32 = 0
    done: ti.i32 = 0
    while step < ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE, ti.i32) and done == 0:
        idx: ti.i32 = (h + step) & mask
        k = fg_exact_dp_sparse_hash_keys[idx]
        if k == key:
            out_id = ti.cast(fg_exact_dp_sparse_hash_vals[idx], ti.i32) - 1
            done = 1
        elif k == 0:
            new_id: ti.i32 = ti.atomic_add(fg_exact_dp_sparse_state_count[None], 1)
            if new_id >= ti.cast(FG_EXACT_DP_SPARSE_MAX_STATES, ti.i32):
                fg_exact_dp_sparse_overflow[None] = 1
                out_id = -1
            else:
                fg_exact_dp_sparse_hash_keys[idx] = key
                fg_exact_dp_sparse_hash_vals[idx] = new_id + 1
                fg_exact_dp_sparse_state_i[new_id] = i
                fg_exact_dp_sparse_state_first[new_id] = is_first
                fg_exact_dp_sparse_state_carry[new_id] = carry_idx
                out_id = new_id
            done = 1
        else:
            step += 1

    if out_id < 0 and fg_exact_dp_sparse_overflow[None] == 0:
        fg_exact_dp_sparse_overflow[None] = 1
    return out_id


@ti.func
def _fg_exact_dp_sparse_canon_carry(i: ti.i32, carry_idx: ti.i32, n: ti.i32, timing_aware: ti.i32) -> ti.i32:
    out: ti.i32 = -1
    if timing_aware != 0 and carry_idx >= 0 and i < n:
        if song_timestamps_great_candidate[carry_idx] > song_timestamps[i]:
            out = carry_idx
    return out


@ti.kernel
def fg_exact_dp_sparse_full_kernel(
    total_notes: ti.i32,
    raw_fill: ti.f32,
    non_fever_base: ti.i32,
    ft_idx: ti.i32,
    timing_aware: ti.i32,  # production default: 1 (carry extends fever window via great-candidate timestamps)
    prune: ti.i32,  # production default: 1 (monotone upper-bound pruning; ~125x transition reduction)
):
    """Compute exact FG DP for a fixed stat point on full charts using sparse state buffers.

    This mirrors the CPU reference recurrence in `gear_optimizer.solver.fg_exact_dp`:
      - state: (section_start_idx, is_first, canonical_carry_idx)
      - actions: choose fp-target p (0..p_max), then choose forced-count k on the plateau
      - transition advances to fever_end_idx (binary-search-left via precomputed tables)
      - reward is prefix-separable: (w_prefix window bonus - c_prefix forced penalty)

    Production call:
      fg_exact_dp_sparse_full_kernel(total_notes, raw_fill, non_fever_base, ft_idx,
                                     timing_aware=1, prune=1)

    Research / ablation:
      - timing_aware=0: disables carry-state dimension (count-only mode, fewer hash states)
      - prune=0: disables the monotone upper-bound pruning rule (full transition space, useful for
                 measuring raw state/transition counts without pruning bias)

    Inputs:
      - total_notes: number of active notes uploaded into `song_timestamps`
      - raw_fill / non_fever_base: fill model parameters (match FG kernels)
      - ft_idx: fever-time stat index (0..160)
      - timing_aware: 1 to enable carry-time via great-candidate timestamps, else 0
      - prune: 1 to enable the same monotone pruning rule as the CPU reference

    Uses (device fields):
      - song_timestamps / song_timestamps_great_candidate
      - fg_fever_end_idx_song / fg_fever_end_idx_great_candidate
      - fg_exact_dp_full_w_prefix / fg_exact_dp_full_c_prefix (must be populated for [0..total_notes])

    Writes:
      - fg_exact_dp_sparse_best_delta[None]
      - fg_exact_dp_sparse_counts[0..FG_MAX_SECTIONS)
      - fg_exact_dp_sparse_states[None]
      - fg_exact_dp_sparse_transitions[None]
      - fg_exact_dp_sparse_overflow[None] (1 if scratch buffers were insufficient)
    """
    fg_exact_dp_sparse_best_delta[None] = ti.cast(0, ti.i64)
    fg_exact_dp_sparse_states[None] = 0
    fg_exact_dp_sparse_transitions[None] = 0
    fg_exact_dp_sparse_overflow[None] = 0
    fg_exact_dp_sparse_state_count[None] = 0
    for s in range(FG_MAX_SECTIONS):
        fg_exact_dp_sparse_counts[s] = ti.cast(-1, ti.i32)

    # Clear hash table.
    for h in range(FG_EXACT_DP_SPARSE_HASH_SIZE):
        fg_exact_dp_sparse_hash_keys[h] = ti.cast(0, ti.i64)
        fg_exact_dp_sparse_hash_vals[h] = ti.cast(0, ti.i32)

    n: ti.i32 = ti.max(0, total_notes)

    ft: ti.i32 = ft_idx
    if ft < 0:
        ft = 0
    if ft > FG_MAX_STAT:
        ft = FG_MAX_STAT

    m: ti.i32 = non_fever_base
    if m < 0:
        m = 0

    # Max FP plateau index (dense 0..p_max).
    p_max: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(m, ti.f32) * 0.5), ti.i32) - m
    if p_max < 0:
        p_max = 0

    # Seed state 0: song start (is_first=1, carry=NO_CARRY).
    _ = _fg_exact_dp_sparse_hash_insert(_fg_exact_dp_sparse_pack_key(0, 1, -1), 0, 1, -1)

    # ------------------------------------------------------------------
    # Build the reachable state set (ignores pruning; bounded by MAX_STATES).
    # ------------------------------------------------------------------
    cur: ti.i32 = 0
    while cur < ti.cast(fg_exact_dp_sparse_state_count[None], ti.i32) and fg_exact_dp_sparse_overflow[None] == 0:
        i: ti.i32 = fg_exact_dp_sparse_state_i[cur]
        is_first: ti.i32 = fg_exact_dp_sparse_state_first[cur]
        carry_idx: ti.i32 = fg_exact_dp_sparse_state_carry[cur]

        carry_idx = _fg_exact_dp_sparse_canon_carry(i, carry_idx, n, timing_aware)
        fg_exact_dp_sparse_state_carry[cur] = carry_idx

        min_notes: ti.i32 = ti.select(is_first != 0, m - 1, m)
        if min_notes < 0:
            min_notes = 0
        if i + min_notes >= n:
            cur += 1
            continue

        forced_start_base: ti.i32 = ti.select(is_first != 0, i, i + 1)
        if forced_start_base < 0:
            forced_start_base = 0

        p: ti.i32 = 0
        done_p: ti.i32 = 0
        while p <= p_max and done_p == 0:
            if fg_exact_dp_sparse_overflow[None] != 0:
                done_p = 1
            else:
                notes_to_fill: ti.i32 = m + p - ti.select(is_first != 0, 1, 0)
                if notes_to_fill < 0:
                    notes_to_fill = 0
                end_normal: ti.i32 = i + notes_to_fill
                if end_normal >= n:
                    done_p = 1
                else:
                    k0: ti.i32 = _forced_from_fp_target(raw_fill, m, p, m)
                    k1: ti.i32 = k0 + 1
                    has_k1: ti.i32 = 0
                    if k1 <= m:
                        fp1: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(k1, ti.f32) * 0.5), ti.i32) - m
                        if fp1 == p:
                            has_k1 = 1

                    # Candidate 0: k0
                    forced_val: ti.i32 = k0
                    if forced_val < 0:
                        forced_val = 0
                    if forced_val > m:
                        forced_val = m

                    actual_notes: ti.i32 = end_normal - i
                    if actual_notes < 0:
                        actual_notes = 0
                    forced_applied: ti.i32 = ti.min(forced_val, actual_notes)

                    next_cidx: ti.i32 = carry_idx
                    if timing_aware != 0 and forced_applied > 0:
                        forced_end: ti.i32 = forced_start_base + forced_applied - 1
                        if forced_end >= forced_start_base and forced_end < end_normal and forced_end < n:
                            cand_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                            if next_cidx < 0:
                                next_cidx = forced_end
                            else:
                                if cand_t > song_timestamps_great_candidate[next_cidx]:
                                    next_cidx = forced_end

                    fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal, ft]
                    if timing_aware != 0 and next_cidx >= 0:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                            fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                    if fever_end_idx <= end_normal:
                        fever_end_idx = ti.min(n, end_normal + 1)
                    if fever_end_idx > n:
                        fever_end_idx = n

                    if fever_end_idx < n:
                        carry_next: ti.i32 = -1
                        if timing_aware != 0 and next_cidx >= 0:
                            if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                                carry_next = next_cidx

                        key_next = _fg_exact_dp_sparse_pack_key(fever_end_idx, 0, carry_next)
                        _ = _fg_exact_dp_sparse_hash_insert(key_next, fever_end_idx, 0, carry_next)

                    # Candidate 1: k1 (when plateau length is 2)
                    if has_k1 != 0 and fg_exact_dp_sparse_overflow[None] == 0:
                        forced_val = k1
                        if forced_val < 0:
                            forced_val = 0
                        if forced_val > m:
                            forced_val = m

                        forced_applied = ti.min(forced_val, actual_notes)

                        next_cidx = carry_idx
                        if timing_aware != 0 and forced_applied > 0:
                            forced_end = forced_start_base + forced_applied - 1
                            if forced_end >= forced_start_base and forced_end < end_normal and forced_end < n:
                                cand_t = song_timestamps_great_candidate[forced_end]
                                if next_cidx < 0:
                                    next_cidx = forced_end
                                else:
                                    if cand_t > song_timestamps_great_candidate[next_cidx]:
                                        next_cidx = forced_end

                        fever_end_idx = fg_fever_end_idx_song[end_normal, ft]
                        if timing_aware != 0 and next_cidx >= 0:
                            if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                                fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                        if fever_end_idx <= end_normal:
                            fever_end_idx = ti.min(n, end_normal + 1)
                        if fever_end_idx > n:
                            fever_end_idx = n

                        if fever_end_idx < n:
                            carry_next = -1
                            if timing_aware != 0 and next_cidx >= 0:
                                if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                                    carry_next = next_cidx

                            key_next = _fg_exact_dp_sparse_pack_key(fever_end_idx, 0, carry_next)
                            _ = _fg_exact_dp_sparse_hash_insert(key_next, fever_end_idx, 0, carry_next)

            p += 1

        cur += 1

    states_total: ti.i32 = ti.cast(fg_exact_dp_sparse_state_count[None], ti.i32)
    fg_exact_dp_sparse_states[None] = states_total

    # If scratch buffers overflowed, skip sort/DP work and leave outputs initialized.
    states_solve: ti.i32 = states_total
    if fg_exact_dp_sparse_overflow[None] != 0:
        states_solve = 0

    # ------------------------------------------------------------------
    # Sort state ids by descending i (topological for dp: transitions always advance i).
    # ------------------------------------------------------------------
    ti.loop_config(serialize=True)
    for s in range(states_solve):
        fg_exact_dp_sparse_order[s] = s

    ti.loop_config(serialize=True)
    for a in range(states_solve):
        best_pos: ti.i32 = a
        best_i: ti.i32 = fg_exact_dp_sparse_state_i[fg_exact_dp_sparse_order[a]]
        for b in range(a + 1, states_solve):
            bid: ti.i32 = fg_exact_dp_sparse_order[b]
            bi: ti.i32 = fg_exact_dp_sparse_state_i[bid]
            if bi > best_i:
                best_i = bi
                best_pos = b
        if best_pos != a:
            tmp: ti.i32 = fg_exact_dp_sparse_order[a]
            fg_exact_dp_sparse_order[a] = fg_exact_dp_sparse_order[best_pos]
            fg_exact_dp_sparse_order[best_pos] = tmp

    # ------------------------------------------------------------------
    # DP solve.
    # ------------------------------------------------------------------
    fg_exact_dp_sparse_transitions[None] = 0
    ti.loop_config(serialize=True)
    for idx in range(states_solve):
        sid: ti.i32 = fg_exact_dp_sparse_order[idx]
        i: ti.i32 = fg_exact_dp_sparse_state_i[sid]
        is_first: ti.i32 = fg_exact_dp_sparse_state_first[sid]
        carry_idx: ti.i32 = fg_exact_dp_sparse_state_carry[sid]

        carry_idx = _fg_exact_dp_sparse_canon_carry(i, carry_idx, n, timing_aware)
        fg_exact_dp_sparse_state_carry[sid] = carry_idx

        if i >= n:
            fg_exact_dp_sparse_dp[sid] = ti.cast(0, ti.i64)
            fg_exact_dp_sparse_policy_p[sid] = 0
            fg_exact_dp_sparse_policy_k[sid] = 0
            continue

        min_notes: ti.i32 = ti.select(is_first != 0, m - 1, m)
        if min_notes < 0:
            min_notes = 0
        if i + min_notes >= n:
            fg_exact_dp_sparse_dp[sid] = ti.cast(0, ti.i64)
            fg_exact_dp_sparse_policy_p[sid] = 0
            fg_exact_dp_sparse_policy_k[sid] = 0
            continue

        forced_start_base: ti.i32 = ti.select(is_first != 0, i, i + 1)
        if forced_start_base < 0:
            forced_start_base = 0

        best_val = ti.cast(0, ti.i64)
        best_p: ti.i32 = 0
        best_k: ti.i32 = 0

        for p in range(p_max + 1):
            notes_to_fill: ti.i32 = m + p - ti.select(is_first != 0, 1, 0)
            if notes_to_fill < 0:
                notes_to_fill = 0
            end_normal: ti.i32 = i + notes_to_fill
            if end_normal >= n:
                break

            k0: ti.i32 = _forced_from_fp_target(raw_fill, m, p, m)
            k1: ti.i32 = k0 + 1
            has_k1: ti.i32 = 0
            if k1 <= m:
                fp1: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(k1, ti.f32) * 0.5), ti.i32) - m
                if fp1 == p:
                    has_k1 = 1

            if prune != 0 and best_val > 0:
                k_min: ti.i32 = k0
                if k_min < 0:
                    k_min = 0
                if k_min > m:
                    k_min = m
                actual_notes: ti.i32 = end_normal - i
                if actual_notes < 0:
                    actual_notes = 0
                forced_applied_min: ti.i32 = ti.min(k_min, actual_notes)
                penalty_min = ti.cast(0, ti.i64)
                if forced_applied_min > 0 and forced_start_base < n:
                    end_excl_min: ti.i32 = forced_start_base + forced_applied_min
                    if end_excl_min > n:
                        end_excl_min = n
                    penalty_min = fg_exact_dp_full_c_prefix[end_excl_min] - fg_exact_dp_full_c_prefix[forced_start_base]

                suffix_bonus: ti.i64 = fg_exact_dp_full_w_prefix[n] - fg_exact_dp_full_w_prefix[end_normal]
                ub: ti.i64 = suffix_bonus - penalty_min
                if ub <= best_val:
                    break

            for cand in range(2):
                if cand == 1 and has_k1 == 0:
                    continue
                fg_exact_dp_sparse_transitions[None] += 1

                forced_val: ti.i32 = ti.select(cand == 0, k0, k1)
                if forced_val < 0:
                    forced_val = 0
                if forced_val > m:
                    forced_val = m

                actual_notes: ti.i32 = end_normal - i
                if actual_notes < 0:
                    actual_notes = 0
                forced_applied: ti.i32 = ti.min(forced_val, actual_notes)

                penalty = ti.cast(0, ti.i64)
                if forced_applied > 0 and forced_start_base < n:
                    end_excl: ti.i32 = forced_start_base + forced_applied
                    if end_excl > n:
                        end_excl = n
                    penalty = fg_exact_dp_full_c_prefix[end_excl] - fg_exact_dp_full_c_prefix[forced_start_base]

                next_cidx: ti.i32 = carry_idx
                if timing_aware != 0 and forced_applied > 0:
                    forced_end: ti.i32 = forced_start_base + forced_applied - 1
                    if forced_end >= forced_start_base and forced_end < end_normal and forced_end < n:
                        cand_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                        if next_cidx < 0:
                            next_cidx = forced_end
                        else:
                            if cand_t > song_timestamps_great_candidate[next_cidx]:
                                next_cidx = forced_end

                fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal, ft]
                if timing_aware != 0 and next_cidx >= 0:
                    if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                        fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                if fever_end_idx <= end_normal:
                    fever_end_idx = ti.min(n, end_normal + 1)
                if fever_end_idx > n:
                    fever_end_idx = n

                carry_next: ti.i32 = -1
                if timing_aware != 0 and next_cidx >= 0 and fever_end_idx < n:
                    if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                        carry_next = next_cidx

                fever_bonus: ti.i64 = fg_exact_dp_full_w_prefix[fever_end_idx] - fg_exact_dp_full_w_prefix[end_normal]

                future = ti.cast(0, ti.i64)
                if fever_end_idx < n:
                    next_id: ti.i32 = _fg_exact_dp_sparse_hash_lookup(
                        _fg_exact_dp_sparse_pack_key(fever_end_idx, 0, carry_next)
                    )
                    if next_id >= 0:
                        future = fg_exact_dp_sparse_dp[next_id]

                total: ti.i64 = fever_bonus - penalty + future
                if total > best_val:
                    best_val = total
                    best_p = p
                    best_k = forced_val

        fg_exact_dp_sparse_dp[sid] = best_val
        fg_exact_dp_sparse_policy_p[sid] = best_p
        fg_exact_dp_sparse_policy_k[sid] = best_k

    # Output best delta from the initial state.
    start_id: ti.i32 = -1
    if states_solve > 0:
        start_id = _fg_exact_dp_sparse_hash_lookup(_fg_exact_dp_sparse_pack_key(0, 1, -1))
        if start_id >= 0:
            fg_exact_dp_sparse_best_delta[None] = fg_exact_dp_sparse_dp[start_id]

    # ------------------------------------------------------------------
    # Reconstruct a bounded prefix of forced-count decisions.
    # ------------------------------------------------------------------
    i: ti.i32 = 0
    is_first: ti.i32 = 1
    carry_idx: ti.i32 = -1
    sid: ti.i32 = start_id

    step: ti.i32 = 0
    done: ti.i32 = 0
    while step < ti.cast(FG_MAX_SECTIONS, ti.i32) and done == 0:
        if sid < 0 or i >= n:
            done = 1
        else:
            carry_idx = _fg_exact_dp_sparse_canon_carry(i, carry_idx, n, timing_aware)

            min_notes: ti.i32 = ti.select(is_first != 0, m - 1, m)
            if min_notes < 0:
                min_notes = 0
            if i + min_notes >= n:
                fg_exact_dp_sparse_counts[step] = ti.cast(0, ti.i32)
                done = 1
            else:
                p: ti.i32 = fg_exact_dp_sparse_policy_p[sid]
                k: ti.i32 = fg_exact_dp_sparse_policy_k[sid]
                fg_exact_dp_sparse_counts[step] = k

                notes_to_fill: ti.i32 = m + p - ti.select(is_first != 0, 1, 0)
                if notes_to_fill < 0:
                    notes_to_fill = 0
                end_normal: ti.i32 = i + notes_to_fill
                if end_normal >= n:
                    done = 1
                else:
                    forced_start_base: ti.i32 = ti.select(is_first != 0, i, i + 1)
                    if forced_start_base < 0:
                        forced_start_base = 0

                    forced_val: ti.i32 = k
                    if forced_val < 0:
                        forced_val = 0
                    if forced_val > m:
                        forced_val = m

                    actual_notes: ti.i32 = end_normal - i
                    if actual_notes < 0:
                        actual_notes = 0
                    forced_applied: ti.i32 = ti.min(forced_val, actual_notes)

                    next_cidx: ti.i32 = carry_idx
                    if timing_aware != 0 and forced_applied > 0:
                        forced_end: ti.i32 = forced_start_base + forced_applied - 1
                        if forced_end >= forced_start_base and forced_end < end_normal and forced_end < n:
                            cand_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                            if next_cidx < 0:
                                next_cidx = forced_end
                            else:
                                if cand_t > song_timestamps_great_candidate[next_cidx]:
                                    next_cidx = forced_end

                    fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal, ft]
                    if timing_aware != 0 and next_cidx >= 0:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                            fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                    if fever_end_idx <= end_normal:
                        fever_end_idx = ti.min(n, end_normal + 1)
                    if fever_end_idx > n:
                        fever_end_idx = n

                    carry_next: ti.i32 = -1
                    if timing_aware != 0 and next_cidx >= 0 and fever_end_idx < n:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                            carry_next = next_cidx

                    i = fever_end_idx
                    carry_idx = carry_next
                    is_first = 0
                    if i >= n:
                        done = 1
                    else:
                        sid = _fg_exact_dp_sparse_hash_lookup(_fg_exact_dp_sparse_pack_key(i, 0, carry_idx))
        step += 1


@ti.func
def _fg_exact_dp_batch_pack_key(i: ti.i32, is_first: ti.i32, carry_idx: ti.i32) -> ti.i64:
    return (ti.cast(i, ti.i64) << 32) | (ti.cast(is_first & 1, ti.i64) << 31) | ti.cast(carry_idx + 1, ti.i64)


@ti.func
def _fg_exact_dp_batch_hash_index(key: ti.i64) -> ti.i32:
    x = key ^ (key >> 33) ^ (key >> 17)
    return ti.cast(x, ti.i32) & ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE - 1, ti.i32)


@ti.func
def _fg_exact_dp_batch_hash_lookup(row: ti.i32, key: ti.i64) -> ti.i32:
    mask: ti.i32 = ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE - 1, ti.i32)
    h: ti.i32 = _fg_exact_dp_batch_hash_index(key)
    found: ti.i32 = -1
    step: ti.i32 = 0
    done: ti.i32 = 0
    while step < ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE, ti.i32) and done == 0:
        idx: ti.i32 = (h + step) & mask
        k = fg_exact_dp_batch_hash_keys[row, idx]
        if k == key:
            found = ti.cast(fg_exact_dp_batch_hash_vals[row, idx], ti.i32) - 1
            done = 1
        elif k == 0:
            done = 1
        else:
            step += 1
    return found


@ti.func
def _fg_exact_dp_batch_hash_insert(row: ti.i32, key: ti.i64, i: ti.i32, is_first: ti.i32, carry_idx: ti.i32) -> ti.i32:
    mask: ti.i32 = ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE - 1, ti.i32)
    h: ti.i32 = _fg_exact_dp_batch_hash_index(key)
    out_id: ti.i32 = -1
    step: ti.i32 = 0
    done: ti.i32 = 0
    while step < ti.cast(FG_EXACT_DP_SPARSE_HASH_SIZE, ti.i32) and done == 0:
        idx: ti.i32 = (h + step) & mask
        k = fg_exact_dp_batch_hash_keys[row, idx]
        if k == key:
            out_id = ti.cast(fg_exact_dp_batch_hash_vals[row, idx], ti.i32) - 1
            done = 1
        elif k == 0:
            new_id: ti.i32 = fg_exact_dp_batch_state_count[row]
            fg_exact_dp_batch_state_count[row] = new_id + 1
            if new_id >= ti.cast(FG_EXACT_DP_SPARSE_MAX_STATES, ti.i32):
                fg_exact_dp_batch_overflow[row] = 1
                out_id = -1
            else:
                fg_exact_dp_batch_hash_keys[row, idx] = key
                fg_exact_dp_batch_hash_vals[row, idx] = new_id + 1
                fg_exact_dp_batch_state_i[row, new_id] = i
                fg_exact_dp_batch_state_first[row, new_id] = is_first
                fg_exact_dp_batch_state_carry[row, new_id] = carry_idx
                out_id = new_id
            done = 1
        else:
            step += 1

    if out_id < 0 and fg_exact_dp_batch_overflow[row] == 0:
        fg_exact_dp_batch_overflow[row] = 1
    return out_id


@ti.func
def _fg_exact_dp_batch_canon_carry(i: ti.i32, carry_idx: ti.i32, n: ti.i32, timing_aware: ti.i32) -> ti.i32:
    out: ti.i32 = -1
    if timing_aware != 0 and carry_idx >= 0 and i < n:
        if song_timestamps_great_candidate[carry_idx] > song_timestamps[i]:
            out = carry_idx
    return out


@ti.func
def _fg_exact_dp_batch_w_prefix(row: ti.i32, idx: ti.i32) -> ti.i64:
    ii: ti.i32 = idx
    if ii < 0:
        ii = 0
    out: ti.i64 = ti.cast(0, ti.i64)
    head_last: ti.i32 = ti.cast(FG_EXACT_DP_PREFIX_HEAD_LEN - 1, ti.i32)
    if ii <= head_last:
        out = fg_exact_dp_batch_w_head_prefix[row, ii]
    else:
        out = fg_exact_dp_batch_w_head_prefix[row, head_last]
        out += fg_exact_dp_batch_w_body[row] * ti.cast(ii - head_last, ti.i64)
    return out


@ti.func
def _fg_exact_dp_batch_c_prefix(row: ti.i32, idx: ti.i32) -> ti.i64:
    ii: ti.i32 = idx
    if ii < 0:
        ii = 0
    out: ti.i64 = ti.cast(0, ti.i64)
    head_last: ti.i32 = ti.cast(FG_EXACT_DP_PREFIX_HEAD_LEN - 1, ti.i32)
    if ii <= head_last:
        out = fg_exact_dp_batch_c_head_prefix[row, ii]
    else:
        out = fg_exact_dp_batch_c_head_prefix[row, head_last]
        out += fg_exact_dp_batch_c_body[row] * ti.cast(ii - head_last, ti.i64)
    return out


@ti.kernel
def fg_exact_dp_sparse_full_batch_kernel(
    batch_n: ti.i32,
    total_notes: ti.i32,
    timing_aware: ti.i32,
    prune: ti.i32,
):
    """Solve multiple independent sparse exact-DP fixed-stat rows in one kernel."""
    n: ti.i32 = ti.max(0, total_notes)
    rows: ti.i32 = batch_n
    if rows < 0:
        rows = 0
    if rows > FG_EXACT_DP_BATCH_MAX_ROWS:
        rows = FG_EXACT_DP_BATCH_MAX_ROWS

    for row in range(rows):
        fg_exact_dp_batch_best_delta[row] = ti.cast(0, ti.i64)
        fg_exact_dp_batch_states[row] = 0
        fg_exact_dp_batch_transitions[row] = 0
        fg_exact_dp_batch_overflow[row] = 0
        fg_exact_dp_batch_state_count[row] = 0

    for row, s in ti.ndrange(rows, FG_MAX_SECTIONS):
        fg_exact_dp_batch_counts[row, s] = ti.cast(-1, ti.i32)

    for row, h in ti.ndrange(rows, FG_EXACT_DP_SPARSE_HASH_SIZE):
        fg_exact_dp_batch_hash_keys[row, h] = ti.cast(0, ti.i64)
        fg_exact_dp_batch_hash_vals[row, h] = ti.cast(0, ti.i32)

    for row in range(rows):
        raw_fill: ti.f32 = fg_exact_dp_batch_raw_fill[row]
        ft: ti.i32 = fg_exact_dp_batch_ft_idx[row]
        if ft < 0:
            ft = 0
        if ft > FG_MAX_STAT:
            ft = FG_MAX_STAT

        m: ti.i32 = fg_exact_dp_batch_non_fever_base[row]
        if m < 0:
            m = 0

        p_max: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(m, ti.f32) * 0.5), ti.i32) - m
        if p_max < 0:
            p_max = 0

        _ = _fg_exact_dp_batch_hash_insert(row, _fg_exact_dp_batch_pack_key(0, 1, -1), 0, 1, -1)

        cur: ti.i32 = 0
        while cur < ti.cast(fg_exact_dp_batch_state_count[row], ti.i32) and fg_exact_dp_batch_overflow[row] == 0:
            i: ti.i32 = fg_exact_dp_batch_state_i[row, cur]
            is_first: ti.i32 = fg_exact_dp_batch_state_first[row, cur]
            carry_idx: ti.i32 = fg_exact_dp_batch_state_carry[row, cur]

            carry_idx = _fg_exact_dp_batch_canon_carry(i, carry_idx, n, timing_aware)
            fg_exact_dp_batch_state_carry[row, cur] = carry_idx

            min_notes: ti.i32 = ti.select(is_first != 0, m - 1, m)
            if min_notes < 0:
                min_notes = 0
            if i + min_notes >= n:
                cur += 1
                continue

            forced_start_base: ti.i32 = ti.select(is_first != 0, i, i + 1)
            if forced_start_base < 0:
                forced_start_base = 0

            p: ti.i32 = 0
            done_p: ti.i32 = 0
            while p <= p_max and done_p == 0:
                if fg_exact_dp_batch_overflow[row] != 0:
                    done_p = 1
                else:
                    notes_to_fill: ti.i32 = m + p - ti.select(is_first != 0, 1, 0)
                    if notes_to_fill < 0:
                        notes_to_fill = 0
                    end_normal: ti.i32 = i + notes_to_fill
                    if end_normal >= n:
                        done_p = 1
                    else:
                        k0: ti.i32 = _forced_from_fp_target(raw_fill, m, p, m)
                        k1: ti.i32 = k0 + 1
                        has_k1: ti.i32 = 0
                        if k1 <= m:
                            fp1: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(k1, ti.f32) * 0.5), ti.i32) - m
                            if fp1 == p:
                                has_k1 = 1

                        forced_val: ti.i32 = k0
                        if forced_val < 0:
                            forced_val = 0
                        if forced_val > m:
                            forced_val = m

                        actual_notes: ti.i32 = end_normal - i
                        if actual_notes < 0:
                            actual_notes = 0
                        forced_applied: ti.i32 = ti.min(forced_val, actual_notes)

                        next_cidx: ti.i32 = carry_idx
                        if timing_aware != 0 and forced_applied > 0:
                            forced_end: ti.i32 = forced_start_base + forced_applied - 1
                            if forced_end >= forced_start_base and forced_end < end_normal and forced_end < n:
                                cand_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                                if next_cidx < 0:
                                    next_cidx = forced_end
                                else:
                                    if cand_t > song_timestamps_great_candidate[next_cidx]:
                                        next_cidx = forced_end

                        fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal, ft]
                        if timing_aware != 0 and next_cidx >= 0:
                            if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                                fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                        if fever_end_idx <= end_normal:
                            fever_end_idx = ti.min(n, end_normal + 1)
                        if fever_end_idx > n:
                            fever_end_idx = n

                        if fever_end_idx < n:
                            carry_next: ti.i32 = -1
                            if timing_aware != 0 and next_cidx >= 0:
                                if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                                    carry_next = next_cidx

                            key_next = _fg_exact_dp_batch_pack_key(fever_end_idx, 0, carry_next)
                            _ = _fg_exact_dp_batch_hash_insert(row, key_next, fever_end_idx, 0, carry_next)

                        if has_k1 != 0 and fg_exact_dp_batch_overflow[row] == 0:
                            forced_val = k1
                            if forced_val < 0:
                                forced_val = 0
                            if forced_val > m:
                                forced_val = m

                            forced_applied = ti.min(forced_val, actual_notes)

                            next_cidx = carry_idx
                            if timing_aware != 0 and forced_applied > 0:
                                forced_end = forced_start_base + forced_applied - 1
                                if forced_end >= forced_start_base and forced_end < end_normal and forced_end < n:
                                    cand_t = song_timestamps_great_candidate[forced_end]
                                    if next_cidx < 0:
                                        next_cidx = forced_end
                                    else:
                                        if cand_t > song_timestamps_great_candidate[next_cidx]:
                                            next_cidx = forced_end

                            fever_end_idx = fg_fever_end_idx_song[end_normal, ft]
                            if timing_aware != 0 and next_cidx >= 0:
                                if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                                    fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                            if fever_end_idx <= end_normal:
                                fever_end_idx = ti.min(n, end_normal + 1)
                            if fever_end_idx > n:
                                fever_end_idx = n

                            if fever_end_idx < n:
                                carry_next = -1
                                if timing_aware != 0 and next_cidx >= 0:
                                    if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                                        carry_next = next_cidx

                                key_next = _fg_exact_dp_batch_pack_key(fever_end_idx, 0, carry_next)
                                _ = _fg_exact_dp_batch_hash_insert(row, key_next, fever_end_idx, 0, carry_next)

                p += 1

            cur += 1

        states_total: ti.i32 = ti.cast(fg_exact_dp_batch_state_count[row], ti.i32)
        fg_exact_dp_batch_states[row] = states_total

        states_solve: ti.i32 = states_total
        if fg_exact_dp_batch_overflow[row] != 0:
            states_solve = 0

        ti.loop_config(serialize=True)
        for s in range(states_solve):
            fg_exact_dp_batch_order[row, s] = s

        ti.loop_config(serialize=True)
        for a in range(states_solve):
            best_pos: ti.i32 = a
            best_i: ti.i32 = fg_exact_dp_batch_state_i[row, fg_exact_dp_batch_order[row, a]]
            for b in range(a + 1, states_solve):
                bid: ti.i32 = fg_exact_dp_batch_order[row, b]
                bi: ti.i32 = fg_exact_dp_batch_state_i[row, bid]
                if bi > best_i:
                    best_i = bi
                    best_pos = b
            if best_pos != a:
                tmp: ti.i32 = fg_exact_dp_batch_order[row, a]
                fg_exact_dp_batch_order[row, a] = fg_exact_dp_batch_order[row, best_pos]
                fg_exact_dp_batch_order[row, best_pos] = tmp

        fg_exact_dp_batch_transitions[row] = 0
        ti.loop_config(serialize=True)
        for idx in range(states_solve):
            sid: ti.i32 = fg_exact_dp_batch_order[row, idx]
            i: ti.i32 = fg_exact_dp_batch_state_i[row, sid]
            is_first: ti.i32 = fg_exact_dp_batch_state_first[row, sid]
            carry_idx: ti.i32 = fg_exact_dp_batch_state_carry[row, sid]

            carry_idx = _fg_exact_dp_batch_canon_carry(i, carry_idx, n, timing_aware)
            fg_exact_dp_batch_state_carry[row, sid] = carry_idx

            if i >= n:
                fg_exact_dp_batch_dp[row, sid] = ti.cast(0, ti.i64)
                fg_exact_dp_batch_policy_p[row, sid] = 0
                fg_exact_dp_batch_policy_k[row, sid] = 0
                continue

            min_notes: ti.i32 = ti.select(is_first != 0, m - 1, m)
            if min_notes < 0:
                min_notes = 0
            if i + min_notes >= n:
                fg_exact_dp_batch_dp[row, sid] = ti.cast(0, ti.i64)
                fg_exact_dp_batch_policy_p[row, sid] = 0
                fg_exact_dp_batch_policy_k[row, sid] = 0
                continue

            forced_start_base: ti.i32 = ti.select(is_first != 0, i, i + 1)
            if forced_start_base < 0:
                forced_start_base = 0

            best_val = ti.cast(0, ti.i64)
            best_p: ti.i32 = 0
            best_k: ti.i32 = 0

            for p in range(p_max + 1):
                notes_to_fill: ti.i32 = m + p - ti.select(is_first != 0, 1, 0)
                if notes_to_fill < 0:
                    notes_to_fill = 0
                end_normal: ti.i32 = i + notes_to_fill
                if end_normal >= n:
                    break

                k0: ti.i32 = _forced_from_fp_target(raw_fill, m, p, m)
                k1: ti.i32 = k0 + 1
                has_k1: ti.i32 = 0
                if k1 <= m:
                    fp1: ti.i32 = ti.cast(ti.ceil(raw_fill + ti.cast(k1, ti.f32) * 0.5), ti.i32) - m
                    if fp1 == p:
                        has_k1 = 1

                if prune != 0 and best_val > 0:
                    k_min: ti.i32 = k0
                    if k_min < 0:
                        k_min = 0
                    if k_min > m:
                        k_min = m
                    actual_notes: ti.i32 = end_normal - i
                    if actual_notes < 0:
                        actual_notes = 0
                    forced_applied_min: ti.i32 = ti.min(k_min, actual_notes)
                    penalty_min = ti.cast(0, ti.i64)
                    if forced_applied_min > 0 and forced_start_base < n:
                        end_excl_min: ti.i32 = forced_start_base + forced_applied_min
                        if end_excl_min > n:
                            end_excl_min = n
                        penalty_min = _fg_exact_dp_batch_c_prefix(row, end_excl_min) - _fg_exact_dp_batch_c_prefix(
                            row, forced_start_base
                        )

                    suffix_bonus: ti.i64 = _fg_exact_dp_batch_w_prefix(row, n) - _fg_exact_dp_batch_w_prefix(
                        row, end_normal
                    )
                    ub: ti.i64 = suffix_bonus - penalty_min
                    if ub <= best_val:
                        break

                for cand in range(2):
                    if cand == 1 and has_k1 == 0:
                        continue
                    fg_exact_dp_batch_transitions[row] += 1

                    forced_val: ti.i32 = ti.select(cand == 0, k0, k1)
                    if forced_val < 0:
                        forced_val = 0
                    if forced_val > m:
                        forced_val = m

                    actual_notes: ti.i32 = end_normal - i
                    if actual_notes < 0:
                        actual_notes = 0
                    forced_applied: ti.i32 = ti.min(forced_val, actual_notes)

                    penalty = ti.cast(0, ti.i64)
                    if forced_applied > 0 and forced_start_base < n:
                        end_excl: ti.i32 = forced_start_base + forced_applied
                        if end_excl > n:
                            end_excl = n
                        penalty = _fg_exact_dp_batch_c_prefix(row, end_excl) - _fg_exact_dp_batch_c_prefix(
                            row, forced_start_base
                        )

                    next_cidx: ti.i32 = carry_idx
                    if timing_aware != 0 and forced_applied > 0:
                        forced_end: ti.i32 = forced_start_base + forced_applied - 1
                        if forced_end >= forced_start_base and forced_end < end_normal and forced_end < n:
                            cand_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                            if next_cidx < 0:
                                next_cidx = forced_end
                            else:
                                if cand_t > song_timestamps_great_candidate[next_cidx]:
                                    next_cidx = forced_end

                    fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal, ft]
                    if timing_aware != 0 and next_cidx >= 0:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                            fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                    if fever_end_idx <= end_normal:
                        fever_end_idx = ti.min(n, end_normal + 1)
                    if fever_end_idx > n:
                        fever_end_idx = n

                    carry_next: ti.i32 = -1
                    if timing_aware != 0 and next_cidx >= 0 and fever_end_idx < n:
                        if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                            carry_next = next_cidx

                    fever_bonus: ti.i64 = _fg_exact_dp_batch_w_prefix(row, fever_end_idx) - _fg_exact_dp_batch_w_prefix(
                        row, end_normal
                    )

                    future = ti.cast(0, ti.i64)
                    if fever_end_idx < n:
                        next_id: ti.i32 = _fg_exact_dp_batch_hash_lookup(
                            row,
                            _fg_exact_dp_batch_pack_key(fever_end_idx, 0, carry_next),
                        )
                        if next_id >= 0:
                            future = fg_exact_dp_batch_dp[row, next_id]

                    total: ti.i64 = fever_bonus - penalty + future
                    if total > best_val:
                        best_val = total
                        best_p = p
                        best_k = forced_val

            fg_exact_dp_batch_dp[row, sid] = best_val
            fg_exact_dp_batch_policy_p[row, sid] = best_p
            fg_exact_dp_batch_policy_k[row, sid] = best_k

        start_id: ti.i32 = -1
        if states_solve > 0:
            start_id = _fg_exact_dp_batch_hash_lookup(row, _fg_exact_dp_batch_pack_key(0, 1, -1))
            if start_id >= 0:
                fg_exact_dp_batch_best_delta[row] = fg_exact_dp_batch_dp[row, start_id]

        i: ti.i32 = 0
        is_first: ti.i32 = 1
        carry_idx: ti.i32 = -1
        sid: ti.i32 = start_id

        step: ti.i32 = 0
        done: ti.i32 = 0
        while step < ti.cast(FG_MAX_SECTIONS, ti.i32) and done == 0:
            if sid < 0 or i >= n:
                done = 1
            else:
                carry_idx = _fg_exact_dp_batch_canon_carry(i, carry_idx, n, timing_aware)

                min_notes: ti.i32 = ti.select(is_first != 0, m - 1, m)
                if min_notes < 0:
                    min_notes = 0
                if i + min_notes >= n:
                    fg_exact_dp_batch_counts[row, step] = ti.cast(0, ti.i32)
                    done = 1
                else:
                    p: ti.i32 = fg_exact_dp_batch_policy_p[row, sid]
                    k: ti.i32 = fg_exact_dp_batch_policy_k[row, sid]
                    fg_exact_dp_batch_counts[row, step] = k

                    notes_to_fill: ti.i32 = m + p - ti.select(is_first != 0, 1, 0)
                    if notes_to_fill < 0:
                        notes_to_fill = 0
                    end_normal: ti.i32 = i + notes_to_fill
                    if end_normal >= n:
                        done = 1
                    else:
                        forced_start_base: ti.i32 = ti.select(is_first != 0, i, i + 1)
                        if forced_start_base < 0:
                            forced_start_base = 0

                        forced_val: ti.i32 = k
                        if forced_val < 0:
                            forced_val = 0
                        if forced_val > m:
                            forced_val = m

                        actual_notes: ti.i32 = end_normal - i
                        if actual_notes < 0:
                            actual_notes = 0
                        forced_applied: ti.i32 = ti.min(forced_val, actual_notes)

                        next_cidx: ti.i32 = carry_idx
                        if timing_aware != 0 and forced_applied > 0:
                            forced_end: ti.i32 = forced_start_base + forced_applied - 1
                            if forced_end >= forced_start_base and forced_end < end_normal and forced_end < n:
                                cand_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                                if next_cidx < 0:
                                    next_cidx = forced_end
                                else:
                                    if cand_t > song_timestamps_great_candidate[next_cidx]:
                                        next_cidx = forced_end

                        fever_end_idx: ti.i32 = fg_fever_end_idx_song[end_normal, ft]
                        if timing_aware != 0 and next_cidx >= 0:
                            if song_timestamps_great_candidate[next_cidx] > song_timestamps[end_normal]:
                                fever_end_idx = fg_fever_end_idx_great_candidate[next_cidx, ft]
                        if fever_end_idx <= end_normal:
                            fever_end_idx = ti.min(n, end_normal + 1)
                        if fever_end_idx > n:
                            fever_end_idx = n

                        carry_next: ti.i32 = -1
                        if timing_aware != 0 and next_cidx >= 0 and fever_end_idx < n:
                            if song_timestamps_great_candidate[next_cidx] > song_timestamps[fever_end_idx]:
                                carry_next = next_cidx

                        i = fever_end_idx
                        carry_idx = carry_next
                        is_first = 0
                        if i >= n:
                            done = 1
                        else:
                            sid = _fg_exact_dp_batch_hash_lookup(row, _fg_exact_dp_batch_pack_key(i, 0, carry_idx))
            step += 1


# Warm-start hint allocation (bound from fields.py)
fg_genome_hint_allocation = None

# Block-per-owner Stage 1 (Vulkan): threads cooperate per (genome, ftff) owner.
# Must be a multiple of 32 for subgroup slot math.
FG_STAGE1_BLOCK_DIM = env_int("FG_STAGE1_BLOCK_DIM", 64)
FG_STAGE1_BLOCK_DIM = max(32, min(int(FG_STAGE1_BLOCK_DIM), 256))
FG_STAGE1_BLOCK_DIM = (FG_STAGE1_BLOCK_DIM // 32) * 32
if FG_STAGE1_BLOCK_DIM <= 0:
    FG_STAGE1_BLOCK_DIM = 32
# Reduction expects a power-of-two block size. Clamp down to the nearest power-of-two.
_fg_block_pow = 1
while _fg_block_pow * 2 <= FG_STAGE1_BLOCK_DIM:
    _fg_block_pow *= 2
FG_STAGE1_BLOCK_DIM = max(32, min(_fg_block_pow, 256))
# Default OFF: compiling two Stage-1 template variants can hurt cold-start runtime.
FG_STAGE1_SMALL_SECTIONS_FASTPATH = env_flag("FG_STAGE1_SMALL_SECTIONS_FASTPATH")
FG_STAGE1_OWNER_CAP_REDUCTION = env_flag("FG_STAGE1_OWNER_CAP_REDUCTION")
FG_STAGE1_DIRECT_ATOMIC = env_flag("FG_STAGE1_DIRECT_ATOMIC", "1")


@ti.func
def _fg_section_forced_cap(sec: ti.i32) -> ti.i32:
    # Keep this ALU-only in the hot loop; on RDNA3 this outperforms a global field read.
    cap: ti.i32 = 4
    if sec == 0:
        cap = 50
    elif sec == 1:
        cap = 30
    elif sec == 2:
        cap = 15
    elif sec == 3:
        cap = 10
    elif sec == 4:
        cap = 8
    elif sec == 5:
        cap = 6
    elif sec == 6:
        cap = 5
    elif sec < 0 or sec >= FG_MAX_SECTIONS:
        cap = 0
    return cap


# ============================================================================


@ti.func
def _fg_decode_fp_targets_vec(local_cfg_idx: ti.i32, ftff_idx: ti.i32, n_sections: ti.i32):
    """
    Decode a rectangular config index into per-section FP targets (last section fastest).

    Matches `itertools.product` ordering (rightmost / last section is the fastest-changing).
    """
    out = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
    rem: ti.i32 = local_cfg_idx
    for rev in ti.static(range(FG_MAX_SECTIONS)):
        s: ti.i32 = ti.i32(FG_MAX_SECTIONS - 1 - rev)
        if s < n_sections:
            base: ti.i32 = fg_cfg_max_fp[ftff_idx, s] + 1
            if base <= 0:
                base = 1
            out[s] = rem % base
            rem = rem // base
    return out


@ti.func
def _fg_decode_fp_targets_vec4(local_cfg_idx: ti.i32, ftff_idx: ti.i32, n_sections: ti.i32):
    """
    Decode FP targets into a 4-section vector for the common small-section fast path.
    """
    out = ti.Vector.zero(ti.i32, 4)
    rem: ti.i32 = local_cfg_idx
    for rev in ti.static(range(4)):
        s: ti.i32 = ti.i32(3 - rev)
        if s < n_sections:
            base: ti.i32 = fg_cfg_max_fp[ftff_idx, s] + 1
            if base <= 0:
                base = 1
            out[s] = rem % base
            rem = rem // base
    return out


@ti.func
def _fg_decode_fp_targets_with_caps_vec(
    local_cfg_idx: ti.i32, caps: ti.types.vector(FG_MAX_SECTIONS, ti.i32), n_sections: ti.i32
):
    """Decode an owner-effective config index using per-section effective caps."""
    out = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
    rem: ti.i32 = local_cfg_idx
    for rev in ti.static(range(FG_MAX_SECTIONS)):
        s: ti.i32 = ti.i32(FG_MAX_SECTIONS - 1 - rev)
        if s < n_sections:
            base: ti.i32 = caps[s] + 1
            if base <= 0:
                base = 1
            out[s] = rem % base
            rem = rem // base
    return out


@ti.func
def _fg_decode_fp_targets_with_caps_vec4(local_cfg_idx: ti.i32, caps: ti.types.vector(4, ti.i32), n_sections: ti.i32):
    """Decode an owner-effective config index using per-section effective caps."""
    out = ti.Vector.zero(ti.i32, 4)
    rem: ti.i32 = local_cfg_idx
    for rev in ti.static(range(4)):
        s: ti.i32 = ti.i32(3 - rev)
        if s < n_sections:
            base: ti.i32 = caps[s] + 1
            if base <= 0:
                base = 1
            out[s] = rem % base
            rem = rem // base
    return out


@ti.func
def _fg_encode_fp_targets_vec(
    fp_targets: ti.types.vector(FG_MAX_SECTIONS, ti.i32), ftff_idx: ti.i32, n_sections: ti.i32
) -> ti.i32:
    """Encode per-section FP targets into the original global config rectangle order."""
    out: ti.i32 = 0
    stride: ti.i32 = 1
    for rev in ti.static(range(FG_MAX_SECTIONS)):
        s: ti.i32 = ti.i32(FG_MAX_SECTIONS - 1 - rev)
        if s < n_sections:
            val: ti.i32 = fp_targets[s]
            if val < 0:
                val = 0
            out += val * stride
            base: ti.i32 = fg_cfg_max_fp[ftff_idx, s] + 1
            if base <= 0:
                base = 1
            stride *= base
    return out


@ti.func
def _fg_encode_fp_targets_vec4(fp_targets: ti.types.vector(4, ti.i32), ftff_idx: ti.i32, n_sections: ti.i32) -> ti.i32:
    """Encode per-section FP targets into the original global config rectangle order."""
    out: ti.i32 = 0
    stride: ti.i32 = 1
    for rev in ti.static(range(4)):
        s: ti.i32 = ti.i32(3 - rev)
        if s < n_sections:
            val: ti.i32 = fp_targets[s]
            if val < 0:
                val = 0
            out += val * stride
            base: ti.i32 = fg_cfg_max_fp[ftff_idx, s] + 1
            if base <= 0:
                base = 1
            stride *= base
    return out


@ti.func
def _binary_search_left_song_timestamps(n: ti.i32, x: ti.f32) -> ti.i32:
    """
    Leftmost index `i` in `song_timestamps[:n]` such that song_timestamps[i] >= x.

    Assumes `song_timestamps` is sorted ascending (typical chart timestamps).
    """
    lo: ti.i32 = 0
    hi: ti.i32 = n
    while lo < hi:
        mid: ti.i32 = (lo + hi) // 2
        if song_timestamps[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


@ti.func
def _fg_fever_end_idx_from_tables(
    current_idx: ti.i32,
    carry_time: ti.f32,
    carry_idx: ti.i32,
    ft_idx: ti.i32,
    total_notes: ti.i32,
) -> ti.i32:
    """
    Get fever end index using precomputed tables.

    - If `carry_time` extends beyond the next note timestamp, fever starts at the great-candidate time
      from `carry_idx` (exactly mirrors `start_time = max(song_timestamps[current_idx], carry_time)`).
    - Otherwise fever starts at `song_timestamps[current_idx]`.
    """
    start_song: ti.f32 = song_timestamps[current_idx]
    use_carry = carry_time > start_song
    start_idx: ti.i32 = ti.select(use_carry, carry_idx, current_idx)
    end_idx: ti.i32 = ti.select(
        use_carry,
        fg_fever_end_idx_great_candidate[start_idx, ft_idx],
        fg_fever_end_idx_song[start_idx, ft_idx],
    )
    return ti.min(end_idx, total_notes)


@ti.kernel
def fg_precompute_fever_end_idx_tables_kernel(total_notes: ti.i32, last_note_time: ti.f32):
    """
    Precompute fever end indices for fast Stage 1 timeline simulation.

    Writes:
      - fg_fever_end_idx_song[note_idx, ft_idx]
      - fg_fever_end_idx_great_candidate[note_idx, ft_idx]

    Both tables binary-search into `song_timestamps` (the chart timeline). The second table
    uses start times from `song_timestamps_great_candidate` to correctly handle `carry_time`.
    """
    n_stat: ti.i32 = FG_MAX_STAT + 1
    n: ti.i32 = ti.max(total_notes, 0)
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15

    for flat in range(n * n_stat):
        note_idx: ti.i32 = flat // n_stat
        ft_idx: ti.i32 = flat - (note_idx * n_stat)

        ft_factor: ti.f32 = kernels_helpers.lookup_ref_ft(ft_idx)
        fever_time: ti.f32 = fever_time_cas * ft_factor

        start_song: ti.f32 = song_timestamps[note_idx]
        end_song: ti.f32 = start_song + fever_time
        fg_fever_end_idx_song[note_idx, ft_idx] = _binary_search_left_song_timestamps(n, end_song)

        start_gc: ti.f32 = song_timestamps_great_candidate[note_idx]
        end_gc: ti.f32 = start_gc + fever_time
        fg_fever_end_idx_great_candidate[note_idx, ft_idx] = _binary_search_left_song_timestamps(n, end_gc)


# ============================================================================
# HELPERS
# ============================================================================


@ti.func
def _optimize_core_bits(
    budget: ti.i32,
    cur_pp: ti.i32,
    cur_cm: ti.i32,
    cur_fm: ti.i32,
    cur_p_val: ti.i32,
    cur_s_val: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    m0: ti.u32,
    m1: ti.u32,
    m2: ti.u32,
    m3: ti.u32,
    head_len: ti.i32,
    count_fever: ti.i32,
    count_normal: ti.i32,
) -> ti.types.vector(10, ti.i32):
    """
    Shared bitpacked optimizer wrapper.

    Returns vector:
      [score, pp, cm, fm, p_val, s_val, g_pp, g_cm, g_fm, g_ov]
    """
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    res = optimize_core_device_exact_bound_preloaded_bits(
        budget,
        cur_pp,
        cur_cm,
        cur_fm,
        cur_p_val,
        cur_s_val,
        is_p_pp,
        is_s_pp,
        is_p_cm,
        is_s_cm,
        is_p_fm,
        is_s_fm,
        is_p_ov,
        is_s_ov,
        m0,
        m1,
        m2,
        m3,
        head_len,
        count_fever,
        count_normal,
    )

    best_final_score: ti.i32 = res[0]
    gems_pp: ti.i32 = res[1]
    gems_cm: ti.i32 = res[2]
    gems_fm: ti.i32 = res[3]
    gems_ov: ti.i32 = res[4]
    p_val: ti.i32 = res[5]
    s_val: ti.i32 = res[6]

    pp: ti.i32 = ti.min(MAX_STAT, cur_pp + (gems_pp * GEM_SCALE_NORMAL))
    cm: ti.i32 = ti.min(MAX_STAT, cur_cm + (gems_cm * GEM_SCALE_NORMAL))
    fm: ti.i32 = ti.min(MAX_STAT, cur_fm + (gems_fm * GEM_SCALE_FEVER))

    return ti.Vector([best_final_score, pp, cm, fm, p_val, s_val, gems_pp, gems_cm, gems_fm, gems_ov])


@ti.func
def _forced_from_fp_target(
    raw_fill: ti.f32,
    base_ceil: ti.i32,
    fp_target: ti.i32,
    non_fever_base: ti.i32,
) -> ti.i32:
    """
    Convert a fill-penalty target into the minimal forced great count.

    Uses: ceil(raw_fill + 0.5*k) - ceil(raw_fill) >= fp_target
    """
    forced_val: ti.i32 = 0
    if fp_target > 0:
        delta: ti.f32 = (ti.cast(base_ceil, ti.f32) + ti.cast(fp_target, ti.f32) - 1.0) - raw_fill
        if delta >= 0.0:
            forced_val = ti.cast(ti.floor(delta * 2.0), ti.i32) + 1
    if forced_val > non_fever_base:
        forced_val = non_fever_base
    return forced_val


@ti.func
def _mask_range_u32(lo: ti.i32, hi: ti.i32) -> ti.u32:
    """
    Build a u32 mask with bits [lo, hi) set (0 <= lo < hi <= 32).

    Avoids per-bit loops when setting head fever masks.
    """
    full = ti.u32(0xFFFFFFFF)
    left = full << ti.cast(lo, ti.u32)
    right = full if hi == 32 else (full >> ti.cast(32 - hi, ti.u32))
    return left & right


@ti.func
def _or_head_mask_range(m0: ti.u32, m1: ti.u32, m2: ti.u32, m3: ti.u32, start: ti.i32, end: ti.i32) -> ti.types.vector(
    4, ti.u32
):
    """OR-in the [start, end) range into the 4-word head mask bitset."""
    if start < end:
        lo0 = start
        hi0 = ti.min(end, 32)
        if lo0 < hi0:
            m0 |= _mask_range_u32(lo0, hi0)

        lo1 = ti.max(start, 32) - 32
        hi1 = ti.min(end, 64) - 32
        if lo1 < hi1:
            m1 |= _mask_range_u32(lo1, hi1)

        lo2 = ti.max(start, 64) - 64
        hi2 = ti.min(end, 96) - 64
        if lo2 < hi2:
            m2 |= _mask_range_u32(lo2, hi2)

        lo3 = ti.max(start, 96) - 96
        hi3 = ti.min(end, 128) - 96
        if lo3 < hi3:
            m3 |= _mask_range_u32(lo3, hi3)

    return ti.Vector([m0, m1, m2, m3])


@ti.func
def _fg_sig_mix_u32(h: ti.u64, x: ti.i32) -> ti.u64:
    v = ti.cast(x, ti.u64) & ti.u64(0xFFFFFFFF)
    h = h ^ v
    h = h * ti.u64(1099511628211)
    return h


@ti.func
def _fg_signature_hash(sig: ti.types.vector(FG_CFG_DEDUPE_SIG_WORDS, ti.i32)) -> ti.u64:
    h = ti.u64(1469598103934665603)
    for i in ti.static(range(FG_CFG_DEDUPE_SIG_WORDS)):
        h = _fg_sig_mix_u32(h, sig[i])
    if h == ti.u64(0):
        h = ti.u64(1)
    return h


@ti.func
def _fg_config_signature(
    global_cfg_idx: ti.i32,
    cfg_base: ti.i32,
    cfg_mode: ti.i32,
    ftff_idx: ti.i32,
    n_sections: ti.i32,
    total_notes: ti.i32,
    head_len: ti.i32,
    non_fever_base: ti.i32,
    non_fever_base_f: ti.f32,
    ft_idx: ti.i32,
    ff_idx: ti.i32,
    fever_acts: ti.i32,
    song_slot: ti.i32,
    pair_caps_from_timeline: ti.i32,
) -> ti.types.vector(FG_CFG_DEDUPE_SIG_WORDS, ti.i32):
    sig = ti.Vector.zero(ti.i32, FG_CFG_DEDUPE_SIG_WORDS)

    local_cfg_idx: ti.i32 = global_cfg_idx - cfg_base
    if local_cfg_idx < 0:
        local_cfg_idx = 0
    fp_targets_vec = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
    if cfg_mode != 0:
        fp_targets_vec = _fg_decode_fp_targets_vec(local_cfg_idx, ftff_idx, n_sections)

    m0 = ti.cast(0, ti.u32)
    m1 = ti.cast(0, ti.u32)
    m2 = ti.cast(0, ti.u32)
    m3 = ti.cast(0, ti.u32)
    forced_m0 = ti.cast(0, ti.u32)
    forced_m1 = ti.cast(0, ti.u32)
    forced_m2 = ti.cast(0, ti.u32)
    forced_m3 = ti.cast(0, ti.u32)
    body_fever: ti.i32 = 0
    forced_body: ti.i32 = 0

    current_idx: ti.i32 = 0
    sec: ti.i32 = 0
    carry_time: ti.f32 = 0.0
    carry_idx: ti.i32 = 0
    while current_idx < total_notes:
        base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
        if base_notes_s < 0:
            base_notes_s = 0

        fp_target: ti.i32 = 0
        if sec < n_sections:
            if cfg_mode != 0:
                fp_target = fp_targets_vec[sec]
            else:
                fp_target = fg_forced_counts[global_cfg_idx, sec]
            if fp_target < 0:
                fp_target = 0
            if sec < FG_MAX_SECTIONS:
                pair_cap_forced: ti.i32 = 0
                if pair_caps_from_timeline != 0:
                    if sec < fever_acts:
                        pair_cap_forced = _fg_section_forced_cap(sec)
                    else:
                        pair_cap_forced = 0
                else:
                    pair_cap_forced = fg_pair_caps[ft_idx, ff_idx, sec]
                if pair_cap_forced < 0:
                    pair_cap_forced = 0
                notes_with_cap = ti.ceil(non_fever_base_f + ti.cast(pair_cap_forced, ti.f32) * 0.5)
                fp_cap: ti.i32 = ti.cast(notes_with_cap, ti.i32) - non_fever_base
                fp_target = ti.min(fp_target, fp_cap)

        forced_val: ti.i32 = _forced_from_fp_target(non_fever_base_f, non_fever_base, fp_target, non_fever_base)
        notes_to_fill: ti.i32 = base_notes_s + fp_target
        section_start: ti.i32 = current_idx
        end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
        actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
        forced_app: ti.i32 = ti.min(forced_val, actual_notes)

        if forced_app > 0:
            forced_start: ti.i32 = section_start + (1 - ti.cast(sec == 0, ti.i32))
            forced_end: ti.i32 = forced_start + forced_app - 1
            forced_end = ti.min(forced_end, end_normal - 1)
            if forced_end >= forced_start and forced_end < total_notes:
                forced_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                if forced_t > carry_time:
                    carry_time = forced_t
                    carry_idx = forced_end

            head_cap: ti.i32 = 100 - forced_start
            if head_cap < 0:
                head_cap = 0
            head_n: ti.i32 = forced_app
            if head_n > head_cap:
                head_n = head_cap
            forced_body += forced_app - head_n
            if head_n > 0:
                masks_forced = _or_head_mask_range(
                    forced_m0,
                    forced_m1,
                    forced_m2,
                    forced_m3,
                    forced_start,
                    forced_start + head_n,
                )
                forced_m0 = masks_forced[0]
                forced_m1 = masks_forced[1]
                forced_m2 = masks_forced[2]
                forced_m3 = masks_forced[3]

        current_idx = end_normal
        if current_idx >= total_notes:
            break

        fever_end_idx: ti.i32 = _fg_fever_end_idx_from_tables(current_idx, carry_time, carry_idx, ft_idx, total_notes)
        if fever_end_idx <= current_idx:
            fever_end_idx = ti.min(total_notes, current_idx + 1)

        if current_idx < head_len:
            head_end = ti.min(head_len, fever_end_idx)
            masks = _or_head_mask_range(m0, m1, m2, m3, current_idx, head_end)
            m0 = masks[0]
            m1 = masks[1]
            m2 = masks[2]
            m3 = masks[3]

        if fever_end_idx > head_len:
            body_start = head_len if current_idx < head_len else current_idx
            if fever_end_idx > body_start:
                body_fever += fever_end_idx - body_start

        current_idx = fever_end_idx
        sec += 1

    body_len = ti.max(total_notes - head_len, 0)
    body_normal: ti.i32 = ti.max(body_len - body_fever, 0)
    sig[0] = ti.cast(m0, ti.i32)
    sig[1] = ti.cast(m1, ti.i32)
    sig[2] = ti.cast(m2, ti.i32)
    sig[3] = ti.cast(m3, ti.i32)
    sig[4] = body_fever
    sig[5] = body_normal
    sig[6] = ti.cast(forced_m0, ti.i32)
    sig[7] = ti.cast(forced_m1, ti.i32)
    sig[8] = ti.cast(forced_m2, ti.i32)
    sig[9] = ti.cast(forced_m3, ti.i32)
    sig[10] = forced_body
    return sig


# ============================================================================
# KERNELS
# ============================================================================


@ti.kernel
def fg_upload_forced_counts_kernel(n_cfg: ti.i32, cfg_dst_offset: ti.i32, data: ti.types.ndarray(dtype=ti.i32, ndim=2)):
    """
    Upload the per-config forced-count grid from a small external array.

    This avoids `field.from_numpy()` on the huge `(FG_MAX_CONFIGS, FG_MAX_SECTIONS)` field.
    `data` must be shaped `(n_cfg, FG_MAX_SECTIONS)` and contain zeros for unused sections.
    """
    for i, j in ti.ndrange(n_cfg, FG_MAX_SECTIONS):
        fg_forced_counts[cfg_dst_offset + i, j] = data[i, j]


@ti.kernel
def fg_upload_song_timestamps_prefix_kernel(n: ti.i32, timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1)):
    """Upload song timestamps without padding to FG_MAX_SONG_NOTES."""
    for i in range(n):
        song_timestamps[i] = timestamps[i]


@ti.kernel
def fg_upload_great_candidate_timestamps_prefix_kernel(n: ti.i32, timestamps: ti.types.ndarray(dtype=ti.f32, ndim=1)):
    """Upload great-candidate timestamps without padding to FG_MAX_SONG_NOTES."""
    for i in range(n):
        song_timestamps_great_candidate[i] = timestamps[i]


@ti.kernel
def fg_upload_exact_dp_full_w_prefix_kernel(n: ti.i32, prefix: ti.types.ndarray(dtype=ti.i64, ndim=1)):
    """Upload w_prefix[0..n] into `fg_exact_dp_full_w_prefix` (no padding required)."""
    for i in range(n + 1):
        fg_exact_dp_full_w_prefix[i] = prefix[i]


@ti.kernel
def fg_upload_exact_dp_full_c_prefix_kernel(n: ti.i32, prefix: ti.types.ndarray(dtype=ti.i64, ndim=1)):
    """Upload c_prefix[0..n] into `fg_exact_dp_full_c_prefix` (no padding required)."""
    for i in range(n + 1):
        fg_exact_dp_full_c_prefix[i] = prefix[i]


@ti.kernel
def fg_upload_ftff_prefix_kernel(
    n_pairs: ti.i32,
    ft_list: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ff_list: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """Upload only the active FT/FF prefix used by the current packed FG chunk."""
    for i in range(n_pairs):
        fg_ft_list[i] = ft_list[i]
        fg_ff_list[i] = ff_list[i]


@ti.kernel
def fg_upload_cfg_meta_prefix_kernel(
    n_pairs: ti.i32,
    cfg_base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    cfg_mode: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """Upload per-pair config metadata for the active FG chunk."""
    for i in range(n_pairs):
        fg_cfg_base_list[i] = cfg_base[i]
        fg_cfg_mode_list[i] = cfg_mode[i]


@ti.kernel
def fg_upload_cfg_max_fp_prefix_kernel(
    n_pairs: ti.i32,
    n_sections: ti.i32,
    cfg_max_fp_data: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    """Upload only active max-FP rows/sections for packed FG chunks."""
    for i, s in ti.ndrange(n_pairs, n_sections):
        fg_cfg_max_fp[i, s] = cfg_max_fp_data[i, s]


@ti.kernel
def fg_upload_cfg_total_len_prefix_kernel(n_pairs: ti.i32, cfg_total_len: ti.types.ndarray(dtype=ti.i32, ndim=1)):
    """Upload only active per-pair config lengths for packed FG chunks."""
    for i in range(n_pairs):
        fg_cfg_total_len_list[i] = cfg_total_len[i]


@ti.kernel
def fg_cfg_dedupe_clear_kernel(n_work_items: ti.i32, dedupe_slots: ti.i32):
    """Clear GPU config-signature dedupe scratch for the next work-item chunk."""
    for i, j in ti.ndrange(n_work_items, dedupe_slots):
        fg_cfg_dedupe_hash[i, j] = ti.u64(0)
        fg_cfg_dedupe_rep_cfg_idx[i, j] = -1
    for i in range(n_work_items):
        fg_cfg_dedupe_rep_count[i] = 0
        fg_cfg_dedupe_active[i] = 1


@ti.kernel
def fg_cfg_dedupe_build_kernel(
    work_offset: ti.i32,
    n_work_items: ti.i32,
    dedupe_slots: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_sections: ti.i32,
    song_slot: ti.i32,
    pair_caps_from_timeline: ti.i32,
):
    """
    Build per-owner representative cfg indices from exact scoring-relevant signatures.

    This is intentionally GPU-side: configs remain implicit, and Stage 1 later
    reads representative original cfg_idx values from fg_cfg_dedupe_rep_cfg_idx.
    If an owner exhausts the bounded table, it is marked inactive and Stage 1
    falls back to evaluating its full cfg window.
    """
    MAX_STAT: ti.i32 = 160
    head_len: ti.i32 = ti.min(total_notes, 100)
    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))

    for local_work_idx in range(n_work_items):
        work_idx: ti.i32 = work_offset + local_work_idx
        g: ti.i32 = fg_flat_work_genome[work_idx]
        ftff_idx: ti.i32 = fg_flat_work_ftff[work_idx]
        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        total_len: ti.i32 = ti.cast(fg_cfg_total_len_list[ftff_idx], ti.i32)
        cfg_base: ti.i32 = fg_cfg_base_list[ftff_idx]
        cfg_mode: ti.i32 = fg_cfg_mode_list[ftff_idx]

        rep_count: ti.i32 = 0
        active: ti.i32 = 1

        if ft_gems + ff_gems <= total_budget and total_len > 0:
            base_stats = kernels_helpers.genome_base_stats[g]
            base_ft_stat: ti.i32 = base_stats[5]
            base_ff_stat: ti.i32 = base_stats[6]
            ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
            ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
            ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
            ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
            ff_factor: ti.f32 = kernels_helpers.lookup_ref_ff(ff_idx)

            fever_acts: ti.i32 = 0
            if pair_caps_from_timeline != 0:
                fever_acts = ti.cast(kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx], ti.i32)
                if fever_acts < 0:
                    fever_acts = 0

            non_fever_base_f: ti.f32 = non_fever_cas * ff_factor
            non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_base_f), ti.i32)

            dedupe_prefilter_caps = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            dedupe_loop_len: ti.i32 = total_len
            dedupe_owner_cap_prefilter: ti.i32 = 0
            if cfg_mode != 0:
                total_eff: ti.i64 = 1
                for sec_cap in ti.static(range(FG_MAX_SECTIONS)):
                    if sec_cap < n_sections:
                        pair_cap_forced_eff: ti.i32 = 0
                        if pair_caps_from_timeline != 0:
                            if sec_cap < fever_acts:
                                pair_cap_forced_eff = _fg_section_forced_cap(sec_cap)
                            else:
                                pair_cap_forced_eff = 0
                        else:
                            pair_cap_forced_eff = fg_pair_caps[ft_idx, ff_idx, sec_cap]
                        if pair_cap_forced_eff < 0:
                            pair_cap_forced_eff = 0
                        notes_with_cap_eff = ti.ceil(non_fever_base_f + ti.cast(pair_cap_forced_eff, ti.f32) * 0.5)
                        fp_cap_eff: ti.i32 = ti.cast(notes_with_cap_eff, ti.i32) - non_fever_base
                        if fp_cap_eff < 0:
                            fp_cap_eff = 0
                        max_fp_eff: ti.i32 = fg_cfg_max_fp[ftff_idx, sec_cap]
                        if max_fp_eff < 0:
                            max_fp_eff = 0
                        if max_fp_eff > fp_cap_eff:
                            max_fp_eff = fp_cap_eff
                        dedupe_prefilter_caps[sec_cap] = max_fp_eff
                        total_eff *= ti.cast(max_fp_eff + 1, ti.i64)
                if total_eff < 1:
                    total_eff = 1
                if total_eff < ti.cast(total_len, ti.i64):
                    dedupe_owner_cap_prefilter = 1
                    dedupe_loop_len = ti.cast(total_eff, ti.i32)

            cfg_local: ti.i32 = 0
            while cfg_local < dedupe_loop_len and active != 0:
                global_cfg_idx: ti.i32 = cfg_base + cfg_local
                if dedupe_owner_cap_prefilter != 0:
                    prefiltered_targets = _fg_decode_fp_targets_with_caps_vec(
                        cfg_local, dedupe_prefilter_caps, n_sections
                    )
                    global_cfg_idx = cfg_base + _fg_encode_fp_targets_vec(prefiltered_targets, ftff_idx, n_sections)
                sig = _fg_config_signature(
                    global_cfg_idx,
                    cfg_base,
                    cfg_mode,
                    ftff_idx,
                    n_sections,
                    total_notes,
                    head_len,
                    non_fever_base,
                    non_fever_base_f,
                    ft_idx,
                    ff_idx,
                    fever_acts,
                    song_slot,
                    pair_caps_from_timeline,
                )
                h = _fg_signature_hash(sig)
                slot: ti.i32 = ti.cast(h % ti.cast(dedupe_slots, ti.u64), ti.i32)
                probe: ti.i32 = 0
                found: ti.i32 = 0
                inserted: ti.i32 = 0

                while probe < dedupe_slots and found == 0 and inserted == 0:
                    h0 = fg_cfg_dedupe_hash[local_work_idx, slot]
                    if h0 == ti.u64(0):
                        fg_cfg_dedupe_hash[local_work_idx, slot] = h
                        fg_cfg_dedupe_sig[local_work_idx, slot] = sig
                        fg_cfg_dedupe_rep_cfg_idx[local_work_idx, slot] = global_cfg_idx
                        rep_count += 1
                        inserted = 1
                    elif h0 == h:
                        same: ti.i32 = 1
                        old_sig = fg_cfg_dedupe_sig[local_work_idx, slot]
                        for w in ti.static(range(FG_CFG_DEDUPE_SIG_WORDS)):
                            if old_sig[w] != sig[w]:
                                same = 0
                        if same != 0:
                            found = 1
                        else:
                            slot += 1
                            if slot >= dedupe_slots:
                                slot = 0
                            probe += 1
                    else:
                        slot += 1
                        if slot >= dedupe_slots:
                            slot = 0
                        probe += 1

                if found == 0 and inserted == 0:
                    active = 0
                    rep_count = 0
                cfg_local += 1

        fg_cfg_dedupe_rep_count[local_work_idx] = rep_count
        fg_cfg_dedupe_active[local_work_idx] = active


@ti.kernel
def fg_generate_fp_targets_cartesian_kernel(
    n_cfg: ti.i32,
    cfg_dst_offset: ti.i32,
    cfg_src_offset: ti.i32,
    n_sections: ti.i32,
    max_fp_by_section: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    """
    Generate rectangular FP-target configs directly on GPU.

    This replaces CPU `itertools.product(*ranges)` materialization for the common
    breakpoint-mode case where each section is simply `range(0, max_fp+1)`.

    Ordering matches Python's `itertools.product`:
      - last dimension (section n-1) varies fastest
      - first dimension (section 0) varies slowest
    """
    for i in range(n_cfg):
        idx = ti.i32(cfg_src_offset + i)
        # Decode idx in mixed radix bases=(max_fp+1) from last section to first.
        # We store per-section FP targets into `fg_forced_counts`.
        # Unused sections are zeroed for safety.
        for sec in range(FG_MAX_SECTIONS):
            if sec < n_sections:
                fg_forced_counts[cfg_dst_offset + i, sec] = 0
            else:
                fg_forced_counts[cfg_dst_offset + i, sec] = 0

        for k in range(n_sections):
            sec = (n_sections - 1) - k
            base = ti.i32(0)
            if sec < FG_MAX_SECTIONS:
                base = ti.max(1, ti.i32(max_fp_by_section[sec]) + 1)
                val = idx % base
                idx = idx // base
                fg_forced_counts[cfg_dst_offset + i, sec] = val


@ti.kernel
def fg_read_forced_counts_kernel(
    n_cfg: ti.i32,
    cfg_src_offset: ti.i32,
    n_sections: ti.i32,
    out: ti.types.ndarray(dtype=ti.i32, ndim=2),
):
    """Read back forced-count/FP-target rows into a small host array for tests/bench."""
    for i, s in ti.ndrange(n_cfg, n_sections):
        if s < FG_MAX_SECTIONS:
            out[i, s] = ti.cast(fg_forced_counts[cfg_src_offset + i, s], ti.i32)
        else:
            out[i, s] = 0


@ti.kernel
def fg_upload_cfg_ranges_kernel(
    n_ftff: ti.i32,
    cfg_start: ti.types.ndarray(dtype=ti.i32, ndim=1),
    cfg_len: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for i in range(n_ftff):
        fg_cfg_start_list[i] = cfg_start[i]
        fg_cfg_len_list[i] = cfg_len[i]


@ti.kernel
def fg_compute_max_fp_for_ftff_kernel(
    n_pairs: ti.i32,
    n_base_pairs: ti.i32,
    n_sections: ti.i32,
    song_slot: ti.i32,
    gem_scale_fever: ti.i32,
    base_ft_stat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base_ff_stat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    non_fever_base_by_ff: ti.types.ndarray(dtype=ti.i16, ndim=1),
    fp_cap_table: ti.types.ndarray(dtype=ti.i16, ndim=2),
):
    """
    Compute per-(ftff_pair, section) max-FP caps directly into fg_cfg_max_fp.

    Uses GPU-resident ft/ff lists and per-song timeline grids; avoids downloading
    the full max-FP matrix to CPU.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)

    for pair_idx, sec in ti.ndrange(n_pairs, n_sections):
        max_fp: ti.i32 = 0

        ft_g = fg_ft_list[pair_idx]
        ff_g = fg_ff_list[pair_idx]

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

        fg_cfg_max_fp[pair_idx, sec] = max_fp


@ti.kernel
def fg_compute_cfg_total_len_kernel(n_pairs: ti.i32, n_sections: ti.i32):
    """
    Compute per-ftff config length from fg_cfg_max_fp and store in fg_cfg_total_len_list.
    """
    for i in range(n_pairs):
        total: ti.i64 = 1
        for s in range(n_sections):
            total = total * (ti.cast(fg_cfg_max_fp[i, s], ti.i64) + 1)
        if total < 1:
            total = 1
        if total > 2147483647:
            total = 2147483647
        fg_cfg_total_len_list[i] = ti.cast(total, ti.i32)


@ti.kernel
def fg_zero_dominated_surface_pairs_kernel(
    n_pairs: ti.i32,
    n_sections: ti.i32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    is_p_ft: ti.i32,
    is_s_ft: ti.i32,
    is_p_ff: ti.i32,
    is_s_ff: ti.i32,
):
    """
    Losslessly remove FT/FF pairs that expose an identical FG surface.

    For equal per-section max-FP rows, the exact-inner solver sees the same
    forced-Great config universe. A pair is dominated when another equal-surface
    pair leaves at least as much remaining gem budget and at least as much
    primary/secondary elemental value. We keep one deterministic representative
    for exact ties.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)

    for i in range(n_pairs):
        ft_i: ti.i32 = fg_ft_list[i]
        ff_i: ti.i32 = fg_ff_list[i]
        budget_i: ti.i32 = total_budget - ft_i - ff_i

        dominated: ti.i32 = 0
        if budget_i < 0:
            dominated = 1

        p_i: ti.i32 = (ft_i * is_p_ft + ff_i * is_p_ff) * gem_scale_fever
        s_i: ti.i32 = (ft_i * is_s_ft + ff_i * is_s_ff) * gem_scale_fever

        for j in range(n_pairs):
            if dominated == 0 and j != i:
                same_surface: ti.i32 = 1
                for sec in range(n_sections):
                    if fg_cfg_max_fp[i, sec] != fg_cfg_max_fp[j, sec]:
                        same_surface = 0

                if same_surface == 1:
                    ft_j: ti.i32 = fg_ft_list[j]
                    ff_j: ti.i32 = fg_ff_list[j]
                    budget_j: ti.i32 = total_budget - ft_j - ff_j
                    p_j: ti.i32 = (ft_j * is_p_ft + ff_j * is_p_ff) * gem_scale_fever
                    s_j: ti.i32 = (ft_j * is_s_ft + ff_j * is_s_ff) * gem_scale_fever

                    if budget_j >= budget_i and p_j >= p_i and s_j >= s_i:
                        strict_better: ti.i32 = 0
                        if budget_j > budget_i or p_j > p_i or s_j > s_i:
                            strict_better = 1

                        deterministic_tie: ti.i32 = 0
                        if strict_better == 0:
                            if ft_j < ft_i:
                                deterministic_tie = 1
                            elif ft_j == ft_i and ff_j < ff_i:
                                deterministic_tie = 1
                            elif ft_j == ft_i and ff_j == ff_i and j < i:
                                deterministic_tie = 1

                        if strict_better == 1 or deterministic_tie == 1:
                            dominated = 1

        if dominated == 1:
            fg_cfg_total_len_list[i] = 0


@ti.kernel
def fg_reduce_cfg_total_len_max_kernel(n_pairs: ti.i32):
    """Compute max(fg_cfg_total_len_list[:n_pairs]) into fg_cfg_total_len_max[None]."""
    fg_cfg_total_len_max[None] = 0
    # Atomic-free reduction: single-thread scan (n_pairs <= FG_MAX_FTFF).
    for _ in range(1):
        best: ti.i32 = 0
        for i in range(n_pairs):
            v: ti.i32 = fg_cfg_total_len_list[i]
            if v > best:
                best = v
        fg_cfg_total_len_max[None] = best


@ti.kernel
def fg_build_flat_work_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """
    Build the flat work-item arrays on GPU.

    Each work item is (genome_id, ftff_id). This avoids uploading two 4M-element
    arrays from CPU on every FG call.
    """
    for g, f in ti.ndrange(n_genomes, n_ftff):
        idx: ti.i32 = g * n_ftff + f
        fg_flat_work_genome[idx] = g
        fg_flat_work_ftff[idx] = f


@ti.kernel
def fg_reset_best_kernel(n_genomes: ti.i32):
    for i in range(n_genomes):
        fg_best_final_score[i] = -1
        fg_best_base_score[i] = 0
        fg_best_cfg_idx[i] = -1
        fg_best_ft[i] = 0
        fg_best_ff[i] = 0
        fg_best_g_pp[i] = 0
        fg_best_g_cm[i] = 0
        fg_best_g_fm[i] = 0
        fg_best_g_ov[i] = 0
        fg_best_score_penalty[i] = 0
        fg_best_fill_penalty[i] = 0
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_best_cfg_counts[i, s] = 0


@ti.kernel
def fg_stage1_init_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """Initialize Stage 1 fields before reduction (supports cfg-chunk accumulation)."""
    for g, f in ti.ndrange(n_genomes, n_ftff):
        if ti.static(FG_STAGE1_HAS_AUX_FIELDS):
            fg_stage1_final_score[g, f] = -1
            fg_stage1_base_score[g, f] = 0
            fg_stage1_g_pp[g, f] = 0
            fg_stage1_g_cm[g, f] = 0
            fg_stage1_g_fm[g, f] = 0
            fg_stage1_g_ov[g, f] = 0
            fg_stage1_score_penalty[g, f] = 0
            fg_stage1_fill_penalty[g, f] = 0
        if ti.static(FG_STAGE1_HAS_CFG_IDX_FIELD):
            fg_stage1_cfg_idx[g, f] = -1
        # Initialize packed field to sentinel value (very negative score, cfg=-1)
        # Use -2^62 in upper bits for sentinel (so any real score wins)
        fg_stage1_packed[g, f] = ti.cast(-1, ti.i64) << 32


@ti.kernel
def fg_stage1_init_packed_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """
    Minimal Stage 1 init for the flattened Vulkan kernels.

    Only the packed reduction key must be reset for correctness; per-result fields
    are overwritten only when an entry wins the atomic update.
    """
    for g, f in ti.ndrange(n_genomes, n_ftff):
        fg_stage1_packed[g, f] = ti.cast(-1, ti.i64) << 32


@ti.kernel
def fg_stage1_clear_wave_best_kernel(n_work_items: ti.i32):
    """Clear per-work-item wave staging buffer before Stage-1 wave writes."""
    for w, s in ti.ndrange(n_work_items, ti.static(FG_STAGE1_WAVE_SLOTS_MAX)):
        fg_stage1_wave_best[w, s] = ti.u64(0)


@ti.kernel
def fg_stage1_waves_kernel(
    use_small_sections: ti.template(),
    work_offset: ti.i32,
    use_cfg_dedupe: ti.i32,
    cfg_dedupe_slots: ti.i32,
    n_work_items: ti.i32,
    n_cfg: ti.i32,
    cfg_offset: ti.i32,
    cfg_read_offset: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_sections: ti.i32,
    is_p_ft: ti.i32,
    is_s_ft: ti.i32,
    is_p_ff: ti.i32,
    is_s_ff: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    song_slot: ti.i32,
    pair_caps_from_timeline: ti.i32,
):
    """
    Stage 1 (Vulkan): block-per-owner, wave-staged (no shared memory).

    One workgroup per (genome, ftff) owner. Threads stride across cfg indices and compute a local best.
    Within each subgroup (wave32/wave64), reduce_max selects the best packed key, and subgroup leaders
    write that key into a global wave-staging buffer (`fg_stage1_wave_best`).

    A separate reduction kernel merges wave slots + previous chunk's packed best into `fg_stage1_packed`.
    """
    ti.loop_config(block_dim=FG_STAGE1_BLOCK_DIM)
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)
    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))

    total_threads = n_work_items * FG_STAGE1_BLOCK_DIM
    for tid in range(total_threads):
        local_work_idx = tid // FG_STAGE1_BLOCK_DIM
        work_idx = work_offset + local_work_idx
        lane = tid - (local_work_idx * FG_STAGE1_BLOCK_DIM)

        g: ti.i32 = fg_flat_work_genome[work_idx]
        ftff_idx: ti.i32 = fg_flat_work_ftff[work_idx]

        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        local_best_packed: ti.u64 = ti.u64(0)

        if ft_gems + ff_gems <= total_budget:
            # Packed-tasks mode: when cfg_offset is negative, each FT/FF pair can reference a different
            # config window in the global cfg table. Two sub-modes:
            # - sentinel: cfg_offset<0 and cfg_read_offset<0 -> read fg_cfg_start_list/fg_cfg_len_list
            # - fused:  cfg_offset<0 and cfg_read_offset>=0 -> compute ranges on-the-fly using (cfg_base,total_len,band_start)
            cfg_global_base: ti.i32 = cfg_offset
            cfg_read_base: ti.i32 = cfg_read_offset
            cfg_len: ti.i32 = n_cfg
            cfg_mode: ti.i32 = 0
            cfg_base: ti.i32 = 0
            dedupe_active: ti.i32 = 0
            if use_cfg_dedupe != 0:
                dedupe_active = fg_cfg_dedupe_active[local_work_idx]
            if cfg_offset < 0:
                cfg_mode = fg_cfg_mode_list[ftff_idx]
                cfg_base = fg_cfg_base_list[ftff_idx]
                if cfg_read_offset < 0:
                    cfg_global_base = fg_cfg_start_list[ftff_idx]
                    cfg_read_base = cfg_global_base
                    cfg_len = fg_cfg_len_list[ftff_idx]
                else:
                    band_start: ti.i32 = cfg_read_offset
                    total_len: ti.i32 = ti.cast(fg_cfg_total_len_list[ftff_idx], ti.i32)
                    if dedupe_active != 0:
                        total_len = cfg_dedupe_slots
                    remaining: ti.i32 = total_len - band_start
                    if remaining <= 0:
                        cfg_len = 0
                    else:
                        cfg_len = ti.min(remaining, n_cfg)
                    cfg_global_base = cfg_base + band_start
                    cfg_read_base = cfg_global_base

            # Load genome base stats (hoisted out of cfg loop)
            # [pp, cm, fm, p_val, s_val, ft, ff]
            base_stats = kernels_helpers.genome_base_stats[g]
            base_pp: ti.i32 = base_stats[0]
            base_cm: ti.i32 = base_stats[1]
            base_fm: ti.i32 = base_stats[2]
            base_p_val: ti.i32 = base_stats[3]
            base_s_val: ti.i32 = base_stats[4]
            base_ft_stat: ti.i32 = base_stats[5]
            base_ff_stat: ti.i32 = base_stats[6]

            ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
            ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
            ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
            ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
            ff_factor: ti.f32 = kernels_helpers.lookup_ref_ff(ff_idx)

            fever_acts: ti.i32 = 0
            if pair_caps_from_timeline != 0:
                fever_acts = ti.cast(kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx], ti.i32)
                if fever_acts < 0:
                    fever_acts = 0

            non_fever_base_f: ti.f32 = non_fever_cas * ff_factor
            non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_base_f), ti.i32)

            owner_cap_reduce: ti.i32 = 0
            owner_cap_total_len: ti.i32 = cfg_len
            owner_max_fp16 = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            owner_max_fp4 = ti.Vector.zero(ti.i32, 4)
            if ti.static(FG_STAGE1_OWNER_CAP_REDUCTION):
                if cfg_mode != 0 and dedupe_active == 0 and cfg_read_offset >= 0:
                    total_eff: ti.i64 = 1
                    for sec_cap in ti.static(range(FG_MAX_SECTIONS)):
                        if sec_cap < n_sections:
                            pair_cap_forced_eff: ti.i32 = 0
                            if pair_caps_from_timeline != 0:
                                if sec_cap < fever_acts:
                                    pair_cap_forced_eff = _fg_section_forced_cap(sec_cap)
                                else:
                                    pair_cap_forced_eff = 0
                            else:
                                pair_cap_forced_eff = fg_pair_caps[ft_idx, ff_idx, sec_cap]
                            if pair_cap_forced_eff < 0:
                                pair_cap_forced_eff = 0
                            notes_with_cap_eff = ti.ceil(non_fever_base_f + ti.cast(pair_cap_forced_eff, ti.f32) * 0.5)
                            fp_cap_eff: ti.i32 = ti.cast(notes_with_cap_eff, ti.i32) - non_fever_base
                            if fp_cap_eff < 0:
                                fp_cap_eff = 0
                            max_fp_eff: ti.i32 = fg_cfg_max_fp[ftff_idx, sec_cap]
                            if max_fp_eff < 0:
                                max_fp_eff = 0
                            if max_fp_eff > fp_cap_eff:
                                max_fp_eff = fp_cap_eff
                            owner_max_fp16[sec_cap] = max_fp_eff
                            if sec_cap < 4:
                                owner_max_fp4[sec_cap] = max_fp_eff
                            total_eff *= ti.cast(max_fp_eff + 1, ti.i64)
                    if total_eff < 1:
                        total_eff = 1
                    if total_eff < ti.cast(cfg_len, ti.i64):
                        owner_cap_reduce = 1
                        owner_cap_total_len = ti.cast(total_eff, ti.i32)
                        remaining_eff: ti.i32 = owner_cap_total_len - cfg_read_offset
                        if remaining_eff <= 0:
                            cfg_len = 0
                        else:
                            cfg_len = ti.min(remaining_eff, n_cfg)

            # Parallel loop over configs (block-strided)
            cfg_idx: ti.i32 = lane
            while cfg_idx < n_cfg:
                if cfg_idx >= cfg_len:
                    cfg_idx += FG_STAGE1_BLOCK_DIM
                    continue
                global_cfg_idx: ti.i32 = cfg_global_base + cfg_idx
                if dedupe_active != 0:
                    rep_slot: ti.i32 = cfg_read_offset + cfg_idx
                    if rep_slot >= cfg_dedupe_slots:
                        cfg_idx += FG_STAGE1_BLOCK_DIM
                        continue
                    global_cfg_idx = fg_cfg_dedupe_rep_cfg_idx[local_work_idx, rep_slot]
                    if global_cfg_idx < 0:
                        cfg_idx += FG_STAGE1_BLOCK_DIM
                        continue
                fp_targets_vec4 = ti.Vector.zero(ti.i32, 4)
                fp_targets_vec16 = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
                if cfg_mode != 0:
                    local_cfg_idx: ti.i32 = global_cfg_idx - cfg_base
                    if owner_cap_reduce != 0:
                        local_cfg_idx = cfg_read_offset + cfg_idx
                    if local_cfg_idx < 0:
                        local_cfg_idx = 0
                    if ti.static(use_small_sections):
                        if owner_cap_reduce != 0:
                            fp_targets_vec4 = _fg_decode_fp_targets_with_caps_vec4(
                                local_cfg_idx, owner_max_fp4, n_sections
                            )
                            global_cfg_idx = cfg_base + _fg_encode_fp_targets_vec4(
                                fp_targets_vec4, ftff_idx, n_sections
                            )
                        else:
                            fp_targets_vec4 = _fg_decode_fp_targets_vec4(local_cfg_idx, ftff_idx, n_sections)
                    else:
                        if owner_cap_reduce != 0:
                            fp_targets_vec16 = _fg_decode_fp_targets_with_caps_vec(
                                local_cfg_idx, owner_max_fp16, n_sections
                            )
                            global_cfg_idx = cfg_base + _fg_encode_fp_targets_vec(
                                fp_targets_vec16, ftff_idx, n_sections
                            )
                        else:
                            fp_targets_vec16 = _fg_decode_fp_targets_vec(local_cfg_idx, ftff_idx, n_sections)

                m0 = ti.cast(0, ti.u32)
                m1 = ti.cast(0, ti.u32)
                m2 = ti.cast(0, ti.u32)
                m3 = ti.cast(0, ti.u32)
                body_fever: ti.i32 = 0

                start_idx4 = ti.Vector.zero(ti.i32, 4)
                forced_applied4 = ti.Vector.zero(ti.i32, 4)
                start_idx16 = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
                forced_applied16 = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

                current_idx: ti.i32 = 0
                sec: ti.i32 = 0
                carry_time: ti.f32 = 0.0
                carry_idx: ti.i32 = 0
                while current_idx < total_notes:
                    base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
                    if base_notes_s < 0:
                        base_notes_s = 0

                    fp_target: ti.i32 = 0
                    if sec < n_sections:
                        if cfg_mode != 0:
                            if ti.static(use_small_sections):
                                if sec < 4:
                                    fp_target = fp_targets_vec4[sec]
                            else:
                                fp_target = fp_targets_vec16[sec]
                        else:
                            read_cfg_idx: ti.i32 = cfg_read_base + cfg_idx
                            if dedupe_active != 0:
                                read_cfg_idx = global_cfg_idx
                            fp_target = fg_forced_counts[read_cfg_idx, sec]
                        if fp_target < 0:
                            fp_target = 0
                        if sec < FG_MAX_SECTIONS:
                            pair_cap_forced: ti.i32 = 0
                            if pair_caps_from_timeline != 0:
                                if sec < fever_acts:
                                    pair_cap_forced = _fg_section_forced_cap(sec)
                                else:
                                    pair_cap_forced = 0
                            else:
                                pair_cap_forced = fg_pair_caps[ft_idx, ff_idx, sec]
                            if pair_cap_forced < 0:
                                pair_cap_forced = 0
                            notes_with_cap = ti.ceil(non_fever_base_f + ti.cast(pair_cap_forced, ti.f32) * 0.5)
                            fp_cap: ti.i32 = ti.cast(notes_with_cap, ti.i32) - non_fever_base
                            fp_target = ti.min(fp_target, fp_cap)

                    forced_val: ti.i32 = _forced_from_fp_target(
                        non_fever_base_f, non_fever_base, fp_target, non_fever_base
                    )

                    fp_calc: ti.i32 = fp_target

                    notes_to_fill: ti.i32 = base_notes_s + fp_calc
                    section_start: ti.i32 = current_idx
                    end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
                    actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
                    forced_app: ti.i32 = ti.min(forced_val, actual_notes)

                    if forced_app > 0:
                        forced_start: ti.i32 = section_start + (1 - ti.cast(sec == 0, ti.i32))
                        forced_end: ti.i32 = forced_start + forced_app - 1
                        forced_end = ti.min(forced_end, end_normal - 1)
                        if forced_end >= forced_start and forced_end < total_notes:
                            forced_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                            if forced_t > carry_time:
                                carry_time = forced_t
                                carry_idx = forced_end

                    if ti.static(use_small_sections):
                        if sec < n_sections and sec < 4:
                            start_idx4[sec] = section_start
                            forced_applied4[sec] = forced_app
                    else:
                        if sec < n_sections and sec < FG_MAX_SECTIONS:
                            start_idx16[sec] = section_start
                            forced_applied16[sec] = forced_app

                    current_idx = end_normal
                    if current_idx >= total_notes:
                        break

                    fever_end_idx: ti.i32 = _fg_fever_end_idx_from_tables(
                        current_idx, carry_time, carry_idx, ft_idx, total_notes
                    )
                    if fever_end_idx <= current_idx:
                        fever_end_idx = ti.min(total_notes, current_idx + 1)

                    if current_idx < head_len:
                        head_end = ti.min(head_len, fever_end_idx)
                        masks = _or_head_mask_range(m0, m1, m2, m3, current_idx, head_end)
                        m0 = masks[0]
                        m1 = masks[1]
                        m2 = masks[2]
                        m3 = masks[3]

                    if fever_end_idx > head_len:
                        body_start = head_len if current_idx < head_len else current_idx
                        if fever_end_idx > body_start:
                            body_fever += fever_end_idx - body_start

                    current_idx = fever_end_idx
                    sec += 1

                # Compute base score and forced-great penalty for this cfg.
                body_len = ti.max(total_notes - head_len, 0)
                body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

                budget: ti.i32 = total_budget - ft_gems - ff_gems
                if budget < 0:
                    cfg_idx += FG_STAGE1_BLOCK_DIM
                    continue

                p_val: ti.i32 = (
                    base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
                )
                s_val: ti.i32 = (
                    base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)
                )

                opt = _optimize_core_bits(
                    budget,
                    base_pp,
                    base_cm,
                    base_fm,
                    p_val,
                    s_val,
                    is_p_pp,
                    is_s_pp,
                    is_p_cm,
                    is_s_cm,
                    is_p_fm,
                    is_s_fm,
                    is_p_ov,
                    is_s_ov,
                    m0,
                    m1,
                    m2,
                    m3,
                    head_len,
                    body_fever,
                    body_normal,
                )

                base_score: ti.i32 = opt[0]
                final_pp: ti.i32 = opt[1]
                final_cm: ti.i32 = opt[2]
                final_p_val: ti.i32 = opt[4]
                final_s_val: ti.i32 = opt[5]

                # Penalty math
                pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(final_pp)
                combo_mul: ti.f32 = kernels_helpers.lookup_ref_cm(final_cm)
                combo_span: ti.f32 = combo_mul - 1.0
                combo_span_scaled: ti.f32 = combo_span * 0.01

                base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
                combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

                great_penalty_base_head: ti.i32 = (
                    ti.cast(ti.floor(ti.cast(final_p_val * 2, ti.f32) * (2.0 / 3.0)), ti.i32)
                    + ti.cast(ti.floor(ti.cast(final_s_val, ti.f32) * (2.0 / 3.0)), ti.i32)
                    + 150
                )
                great_penalty_base_raw: ti.f32 = (
                    (ti.cast(final_p_val * 2, ti.f32) * (2.0 / 3.0))
                    + (ti.cast(final_s_val, ti.f32) * (2.0 / 3.0))
                    + 150.0
                )
                great_combo_value: ti.i32 = ti.cast(ti.floor(great_penalty_base_raw * combo_mul), ti.i32)
                body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)
                great_penalty_base_f: ti.f32 = ti.cast(great_penalty_base_head, ti.f32)

                score_penalty_total: ti.i32 = 0
                if ti.static(use_small_sections):
                    for s in ti.static(range(4)):
                        if s < n_sections:
                            forced_n: ti.i32 = forced_applied4[s]
                            if forced_n > 0:
                                start = start_idx4[s] + ti.cast(s > 0, ti.i32)
                                head_cap: ti.i32 = 100 - start
                                if head_cap < 0:
                                    head_cap = 0
                                head_n: ti.i32 = forced_n
                                if head_n > head_cap:
                                    head_n = head_cap
                                body_n: ti.i32 = forced_n - head_n

                                score_penalty_total += body_n * body_penalty
                                for k in range(head_n):
                                    note_idx = start + k
                                    if note_idx == 99:
                                        score_penalty_total += body_penalty
                                    else:
                                        scaling: ti.f32 = 1.0 + combo_span_scaled * ti.cast(note_idx + 1, ti.f32)
                                        perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                                        great_val: ti.i32 = ti.cast(ti.floor(great_penalty_base_f * scaling), ti.i32)
                                        pen: ti.i32 = ti.max(0, perfect_val - great_val)
                                        score_penalty_total += pen
                else:
                    for s in range(ti.min(n_sections, FG_MAX_SECTIONS)):
                        forced_n: ti.i32 = forced_applied16[s]
                        if forced_n > 0:
                            start = start_idx16[s] + ti.cast(s > 0, ti.i32)
                            head_cap: ti.i32 = 100 - start
                            if head_cap < 0:
                                head_cap = 0
                            head_n: ti.i32 = forced_n
                            if head_n > head_cap:
                                head_n = head_cap
                            body_n: ti.i32 = forced_n - head_n

                            score_penalty_total += body_n * body_penalty
                            for k in range(head_n):
                                note_idx = start + k
                                if note_idx == 99:
                                    score_penalty_total += body_penalty
                                else:
                                    scaling: ti.f32 = 1.0 + combo_span_scaled * ti.cast(note_idx + 1, ti.f32)
                                    perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                                    great_val: ti.i32 = ti.cast(ti.floor(great_penalty_base_f * scaling), ti.i32)
                                    pen: ti.i32 = ti.max(0, perfect_val - great_val)
                                    score_penalty_total += pen

                final_score: ti.i32 = base_score - score_penalty_total
                if final_score < 0:
                    final_score = 0

                inverted_idx: ti.u64 = ti.u64(0x7FFFFFFF) - ti.cast(global_cfg_idx, ti.u64)
                packed_val: ti.u64 = (ti.cast(final_score, ti.u64) << 32) | inverted_idx
                if packed_val > local_best_packed:
                    local_best_packed = packed_val

                cfg_idx += FG_STAGE1_BLOCK_DIM

        best_wave = simt.subgroup.reduce_max(local_best_packed)
        if simt.subgroup.elect() and best_wave > ti.u64(0):
            if ti.static(FG_STAGE1_DIRECT_ATOMIC):
                ti.atomic_max(fg_stage1_packed[g, ftff_idx], ti.cast(best_wave, ti.i64))
            else:
                # lane//32, valid for wave32 and wave64 (wave64 uses even slots)
                wave_slot = lane >> 5
                if wave_slot < ti.static(FG_STAGE1_WAVE_SLOTS_MAX):
                    fg_stage1_wave_best[local_work_idx, wave_slot] = best_wave


@ti.kernel
def fg_stage1_reduce_waves_kernel(work_offset: ti.i32, n_work_items: ti.i32, is_first_chunk: ti.i32):
    """Reduce wave-staged Stage-1 winners into `fg_stage1_packed` (accumulates across cfg chunks)."""
    sentinel_i64: ti.i64 = ti.cast(-1, ti.i64) << 32
    for local_work_idx in range(n_work_items):
        work_idx: ti.i32 = work_offset + local_work_idx
        g: ti.i32 = fg_flat_work_genome[work_idx]
        ftff_idx: ti.i32 = fg_flat_work_ftff[work_idx]

        best: ti.u64 = ti.u64(0)
        if is_first_chunk == 0:
            prev: ti.i64 = fg_stage1_packed[g, ftff_idx]
            if prev >= 0:
                best = ti.cast(prev, ti.u64)

        for i in ti.static(range(FG_STAGE1_WAVE_SLOTS_MAX)):
            v = fg_stage1_wave_best[local_work_idx, i]
            if v > best:
                best = v

        if best > ti.u64(0):
            fg_stage1_packed[g, ftff_idx] = ti.cast(best, ti.i64)
        else:
            fg_stage1_packed[g, ftff_idx] = sentinel_i64


@ti.kernel
def fg_stage1_kernel(
    n_genomes: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_cfg: ti.i32,
    n_sections: ti.i32,
    n_ftff: ti.i32,
    cfg_offset: ti.i32,
    cfg_read_offset: ti.i32,
    is_p_ft: ti.i32,
    is_s_ft: ti.i32,
    is_p_ff: ti.i32,
    is_s_ff: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    song_slot: ti.i32,
    pair_caps_from_timeline: ti.i32,
    is_first_chunk: ti.i32,
):
    """
    Stage 1: Find best cfg for each (genome, ftff) pair.

    Parallelizes over (genome, ftff), loops cfg sequentially inside.
    NO ATOMICS - each (g, f) pair has its own output slot.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)

    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))

    for g, ftff_idx in ti.ndrange(n_genomes, n_ftff):
        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        if ft_gems + ff_gems > total_budget:
            continue

        # Packed-tasks mode: when cfg_offset is negative, each FT/FF pair can reference a different
        # config window in the global cfg table. Two sub-modes:
        # - sentinel: cfg_offset<0 and cfg_read_offset<0 -> read fg_cfg_start_list/fg_cfg_len_list (precomputed ranges)
        # - fused:  cfg_offset<0 and cfg_read_offset>=0 -> compute ranges on-the-fly using (cfg_base,total_len,band_start)
        cfg_global_base: ti.i32 = cfg_offset
        cfg_read_base: ti.i32 = cfg_read_offset
        cfg_len: ti.i32 = n_cfg
        cfg_mode: ti.i32 = 0
        cfg_base: ti.i32 = 0
        if cfg_offset < 0:
            cfg_mode = fg_cfg_mode_list[ftff_idx]
            cfg_base = fg_cfg_base_list[ftff_idx]
            if cfg_read_offset < 0:
                cfg_global_base = fg_cfg_start_list[ftff_idx]
                cfg_read_base = cfg_global_base
                cfg_len = fg_cfg_len_list[ftff_idx]
            else:
                band_start: ti.i32 = cfg_read_offset
                total_len: ti.i32 = ti.cast(fg_cfg_total_len_list[ftff_idx], ti.i32)
                remaining: ti.i32 = total_len - band_start
                if remaining <= 0:
                    cfg_len = 0
                else:
                    cfg_len = ti.min(remaining, n_cfg)
                cfg_global_base = cfg_base + band_start
                cfg_read_base = cfg_global_base

        # Load genome base stats (hoisted out of cfg loop)
        # Load genome base stats (hoisted out of cfg loop)
        # [pp, cm, fm, p_val, s_val, ft, ff]
        base_stats = kernels_helpers.genome_base_stats[g]
        base_pp: ti.i32 = base_stats[0]
        base_cm: ti.i32 = base_stats[1]
        base_fm: ti.i32 = base_stats[2]
        base_p_val: ti.i32 = base_stats[3]
        base_s_val: ti.i32 = base_stats[4]
        base_ft_stat: ti.i32 = base_stats[5]
        base_ff_stat: ti.i32 = base_stats[6]

        # Fever multipliers for this FT/FF (hoisted)
        ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        ff_factor: ti.f32 = kernels_helpers.lookup_ref_ff(ff_idx)

        fever_acts: ti.i32 = 0
        if pair_caps_from_timeline != 0 and song_slot >= 0:
            fever_acts = ti.cast(kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx], ti.i32)
            if fever_acts < 0:
                fever_acts = 0

        non_fever_base_f: ti.f32 = non_fever_cas * ff_factor
        non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_base_f), ti.i32)

        # Accumulate across cfg-chunks. On the first chunk, outputs are already initialized,
        # so we can avoid a global read of the Stage-1 fields.
        best_final: ti.i32 = -1
        best_base: ti.i32 = 0
        best_cfg: ti.i32 = -1
        best_pp: ti.i32 = 0
        best_cm: ti.i32 = 0
        best_fm: ti.i32 = 0
        best_ov: ti.i32 = 0
        best_sp: ti.i32 = 0
        best_fp: ti.i32 = 0
        if is_first_chunk == 0:
            if ti.static(FG_STAGE1_HAS_AUX_FIELDS):
                best_final = fg_stage1_final_score[g, ftff_idx]
                if best_final >= 0:
                    best_base = fg_stage1_base_score[g, ftff_idx]
                    best_cfg = fg_stage1_cfg_idx[g, ftff_idx]
                    best_pp = fg_stage1_g_pp[g, ftff_idx]
                    best_cm = fg_stage1_g_cm[g, ftff_idx]
                    best_fm = fg_stage1_g_fm[g, ftff_idx]
                    best_ov = fg_stage1_g_ov[g, ftff_idx]
                    best_sp = fg_stage1_score_penalty[g, ftff_idx]
                    best_fp = fg_stage1_fill_penalty[g, ftff_idx]
            else:
                prev_packed: ti.i64 = fg_stage1_packed[g, ftff_idx]
                if prev_packed >= 0:
                    best_final = ti.cast(prev_packed >> 32, ti.i32)
                    inverted_idx: ti.i32 = ti.cast(prev_packed & ti.i64(0x7FFFFFFF), ti.i32)
                    best_cfg = 0x7FFFFFFF - inverted_idx

        # Sequential loop over configs (no atomics needed!)
        for cfg_idx in range(n_cfg):
            if cfg_idx >= cfg_len:
                continue
            global_cfg_idx: ti.i32 = cfg_global_base + cfg_idx
            fp_targets_vec = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            if cfg_mode != 0:
                local_cfg_idx: ti.i32 = global_cfg_idx - cfg_base
                if local_cfg_idx < 0:
                    local_cfg_idx = 0
                fp_targets_vec = _fg_decode_fp_targets_vec(local_cfg_idx, ftff_idx, n_sections)
            # Timeline simulation -> head mask bits + body fever count
            m0 = ti.cast(0, ti.u32)
            m1 = ti.cast(0, ti.u32)
            m2 = ti.cast(0, ti.u32)
            m3 = ti.cast(0, ti.u32)
            body_fever: ti.i32 = 0

            start_idx = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            forced_applied = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            fill_notes = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

            current_idx: ti.i32 = 0
            sec: ti.i32 = 0
            carry_time: ti.f32 = 0.0
            carry_idx: ti.i32 = 0
            while current_idx < total_notes:
                base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
                if base_notes_s < 0:
                    base_notes_s = 0

                fp_target: ti.i32 = 0
                if sec < n_sections:
                    if cfg_mode != 0:
                        fp_target = fp_targets_vec[sec]
                    else:
                        fp_target = fg_forced_counts[cfg_read_base + cfg_idx, sec]
                    if fp_target < 0:
                        fp_target = 0
                    if sec < FG_MAX_SECTIONS:
                        pair_cap_forced: ti.i32 = 0
                        if pair_caps_from_timeline != 0:
                            if sec < fever_acts:
                                pair_cap_forced = _fg_section_forced_cap(sec)
                            else:
                                pair_cap_forced = 0
                        else:
                            pair_cap_forced = fg_pair_caps[ft_idx, ff_idx, sec]
                        if pair_cap_forced < 0:
                            pair_cap_forced = 0
                        # Convert forced-count cap to an FP-target cap:
                        # fp_cap = ceil(raw_fill + 0.5*cap) - ceil(raw_fill)
                        notes_with_cap = ti.ceil(non_fever_base_f + ti.cast(pair_cap_forced, ti.f32) * 0.5)
                        fp_cap: ti.i32 = ti.cast(notes_with_cap, ti.i32) - non_fever_base
                        fp_target = ti.min(fp_target, fp_cap)

                # Derive forced_val from fp_target using raw_fill-based inverse.
                forced_val: ti.i32 = _forced_from_fp_target(non_fever_base_f, non_fever_base, fp_target, non_fever_base)

                fp_calc: ti.i32 = fp_target

                notes_to_fill: ti.i32 = base_notes_s + fp_calc
                section_start: ti.i32 = current_idx
                end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
                actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
                forced_app: ti.i32 = ti.min(forced_val, actual_notes)

                if forced_app > 0:
                    forced_start: ti.i32 = section_start + (1 - ti.cast(sec == 0, ti.i32))
                    forced_end: ti.i32 = forced_start + forced_app - 1
                    forced_end = ti.min(forced_end, end_normal - 1)
                    if forced_end >= forced_start and forced_end < total_notes:
                        forced_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                        if forced_t > carry_time:
                            carry_time = forced_t
                            carry_idx = forced_end

                if sec < n_sections and sec < FG_MAX_SECTIONS:
                    start_idx[sec] = section_start
                    forced_applied[sec] = forced_app
                    fill_notes[sec] = fp_calc

                current_idx = end_normal
                if current_idx >= total_notes:
                    break

                # Fever section
                fever_end_idx: ti.i32 = _fg_fever_end_idx_from_tables(
                    current_idx, carry_time, carry_idx, ft_idx, total_notes
                )
                if fever_end_idx <= current_idx:
                    fever_end_idx = ti.min(total_notes, current_idx + 1)

                # Mark head fever notes (bitset)
                if current_idx < head_len:
                    head_end = ti.min(head_len, fever_end_idx)
                    masks = _or_head_mask_range(m0, m1, m2, m3, current_idx, head_end)
                    m0 = masks[0]
                    m1 = masks[1]
                    m2 = masks[2]
                    m3 = masks[3]

                # Count body fever notes
                if fever_end_idx > head_len:
                    body_start = head_len if current_idx < head_len else current_idx
                    if fever_end_idx > body_start:
                        body_fever += fever_end_idx - body_start

                current_idx = fever_end_idx
                sec += 1

            body_len = ti.max(total_notes - head_len, 0)
            body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

            budget: ti.i32 = total_budget - ft_gems - ff_gems
            if budget < 0:
                continue

            p_val: ti.i32 = (
                base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
            )
            s_val: ti.i32 = (
                base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)
            )

            opt = _optimize_core_bits(
                budget,
                base_pp,
                base_cm,
                base_fm,
                p_val,
                s_val,
                is_p_pp,
                is_s_pp,
                is_p_cm,
                is_s_cm,
                is_p_fm,
                is_s_fm,
                is_p_ov,
                is_s_ov,
                m0,
                m1,
                m2,
                m3,
                head_len,
                body_fever,
                body_normal,
            )

            base_score: ti.i32 = opt[0]
            final_pp: ti.i32 = opt[1]
            final_cm: ti.i32 = opt[2]
            final_p_val: ti.i32 = opt[4]
            final_s_val: ti.i32 = opt[5]
            gems_pp: ti.i32 = opt[6]
            gems_cm: ti.i32 = opt[7]
            gems_fm: ti.i32 = opt[8]
            gems_ov: ti.i32 = opt[9]

            # Penalty math
            pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(final_pp)
            combo_mul: ti.f32 = kernels_helpers.lookup_ref_cm(final_cm)
            combo_span: ti.f32 = combo_mul - 1.0
            combo_span_scaled: ti.f32 = combo_span * 0.01

            base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
            combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

            # Great scoring:
            # - For ramped notes (<100), we use an integer base derived from per-term floors.
            # - For full-combo (>=100), we compute the floor *after* applying the combo multiplier to the
            #   underlying float expression to match in-game flooring behavior at max combo.
            great_penalty_base_head: ti.i32 = (
                ti.cast(
                    ti.floor(ti.cast(final_p_val * 2, ti.f32) * (2.0 / 3.0)),
                    ti.i32,
                )
                + ti.cast(
                    ti.floor(ti.cast(final_s_val, ti.f32) * (2.0 / 3.0)),
                    ti.i32,
                )
                + 150
            )
            great_penalty_base_raw: ti.f32 = (
                (ti.cast(final_p_val * 2, ti.f32) * (2.0 / 3.0)) + (ti.cast(final_s_val, ti.f32) * (2.0 / 3.0)) + 150.0
            )
            great_combo_value: ti.i32 = ti.cast(ti.floor(great_penalty_base_raw * combo_mul), ti.i32)
            body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)
            great_penalty_base_f: ti.f32 = ti.cast(great_penalty_base_head, ti.f32)

            score_penalty_total: ti.i32 = 0
            fill_penalty_total: ti.i32 = 0

            for s in range(ti.min(n_sections, FG_MAX_SECTIONS)):
                fp_notes: ti.i32 = fill_notes[s]
                fill_penalty_total += fp_notes * combo_value

                forced_n: ti.i32 = forced_applied[s]
                if forced_n > 0:
                    # For sections 2+, the first non-fever note is the transition note (no fill).
                    # Forced Greats should apply to fill-contributing notes, so offset by +1.
                    start = start_idx[s] + ti.cast(s > 0, ti.i32)
                    head_cap: ti.i32 = 100 - start
                    if head_cap < 0:
                        head_cap = 0
                    head_n: ti.i32 = forced_n
                    if head_n > head_cap:
                        head_n = head_cap
                    body_n: ti.i32 = forced_n - head_n

                    # All forced notes at indices >= 100 have the same body penalty.
                    score_penalty_total += body_n * body_penalty

                    for k in range(head_n):
                        note_idx = start + k  # guaranteed < 100
                        if note_idx == 99:
                            score_penalty_total += body_penalty
                        else:
                            scaling: ti.f32 = 1.0 + combo_span_scaled * ti.cast(note_idx + 1, ti.f32)
                            perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                            great_val: ti.i32 = ti.cast(ti.floor(great_penalty_base_f * scaling), ti.i32)
                            pen: ti.i32 = ti.max(0, perfect_val - great_val)
                            score_penalty_total += pen

            final_score: ti.i32 = base_score - score_penalty_total
            if final_score < 0:
                final_score = 0

            # Stable tie-break: prefer the lower global cfg idx when final_score ties.
            if (final_score > best_final) or (final_score == best_final and global_cfg_idx < best_cfg):
                best_final = final_score
                best_base = base_score
                best_cfg = global_cfg_idx
                best_pp = gems_pp
                best_cm = gems_cm
                best_fm = gems_fm
                best_ov = gems_ov
                best_sp = score_penalty_total
                best_fp = fill_penalty_total

        if ti.static(FG_STAGE1_HAS_AUX_FIELDS):
            fg_stage1_final_score[g, ftff_idx] = best_final
            fg_stage1_base_score[g, ftff_idx] = best_base
            fg_stage1_g_pp[g, ftff_idx] = best_pp
            fg_stage1_g_cm[g, ftff_idx] = best_cm
            fg_stage1_g_fm[g, ftff_idx] = best_fm
            fg_stage1_g_ov[g, ftff_idx] = best_ov
            fg_stage1_score_penalty[g, ftff_idx] = best_sp
            fg_stage1_fill_penalty[g, ftff_idx] = best_fp

        if ti.static(FG_STAGE1_HAS_CFG_IDX_FIELD):
            fg_stage1_cfg_idx[g, ftff_idx] = best_cfg
        # Keep packed field consistent for Stage 2 reduction (Metal path has no 64-bit atomics).
        if best_final >= 0:
            inverted_idx: ti.i32 = 0x7FFFFFFF - best_cfg
            fg_stage1_packed[g, ftff_idx] = (ti.cast(best_final, ti.i64) << 32) | ti.cast(inverted_idx, ti.i64)
        else:
            fg_stage1_packed[g, ftff_idx] = ti.cast(-1, ti.i64) << 32


def fg_stage2_recompute_kernel(
    n_genomes: ti.i32,
    n_ftff: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_sections: ti.i32,
    is_p_ft: ti.i32,
    is_s_ft: ti.i32,
    is_p_ff: ti.i32,
    is_s_ff: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    song_slot: ti.i32,
    pair_caps_from_timeline: ti.i32,
):
    """
    Stage 2 recompute (no global-best update).

    Delegates to the fused stage-2 kernel with an invalid song_slot sentinel so
    global-best accumulation is skipped while keeping one recompute implementation.
    """
    fg_stage2_recompute_and_update_global_best_kernel(
        n_genomes,
        n_ftff,
        total_notes,
        long_notes,
        last_note_time,
        total_budget,
        gem_scale_fever,
        n_sections,
        is_p_ft,
        is_s_ft,
        is_p_ff,
        is_s_ff,
        is_p_pp,
        is_s_pp,
        is_p_cm,
        is_s_cm,
        is_p_fm,
        is_s_fm,
        is_p_ov,
        is_s_ov,
        -1,
        pair_caps_from_timeline,
    )


@ti.kernel
def fg_stage2_recompute_and_update_global_best_kernel(
    n_genomes: ti.i32,
    n_ftff: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_sections: ti.i32,
    is_p_ft: ti.i32,
    is_s_ft: ti.i32,
    is_p_ff: ti.i32,
    is_s_ff: ti.i32,
    is_p_pp: ti.i32,
    is_s_pp: ti.i32,
    is_p_cm: ti.i32,
    is_s_cm: ti.i32,
    is_p_fm: ti.i32,
    is_s_fm: ti.i32,
    is_p_ov: ti.i32,
    is_s_ov: ti.i32,
    song_slot: ti.i32,
    pair_caps_from_timeline: ti.i32,
):
    """
    Packed-task Stage 2: select best (ftff, cfg) from fg_stage1_packed, then recompute auxiliary
    outputs (base score, gems, penalties) for that selection.

    This avoids a race where multiple Stage-1 cfg tiles can update `fg_stage1_packed` and then
    write auxiliary fields non-atomically, causing penalties/fill data to become inconsistent with
    the final packed winner.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)
    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))

    for gid in range(n_genomes):
        best_packed: ti.i64 = ti.cast(-1, ti.i64) << 32
        best_ftff: ti.i32 = 0

        for f in range(n_ftff):
            packed = fg_stage1_packed[gid, f]
            if packed > best_packed:
                best_packed = packed
                best_ftff = f

        best_final: ti.i32 = ti.cast(best_packed >> 32, ti.i32)
        if best_final < 0:
            continue

        inverted_cfg: ti.i32 = ti.cast(best_packed & 0x7FFFFFFF, ti.i32)
        best_cfg: ti.i32 = 0x7FFFFFFF - inverted_cfg

        ft_gems: ti.i32 = fg_ft_list[best_ftff]
        ff_gems: ti.i32 = fg_ff_list[best_ftff]
        if ft_gems + ff_gems > total_budget:
            continue

        # Load genome base stats: [pp, cm, fm, p_val, s_val, ft, ff]
        base_stats = kernels_helpers.genome_base_stats[gid]
        base_pp: ti.i32 = base_stats[0]
        base_cm: ti.i32 = base_stats[1]
        base_fm: ti.i32 = base_stats[2]
        base_p_val: ti.i32 = base_stats[3]
        base_s_val: ti.i32 = base_stats[4]
        base_ft_stat: ti.i32 = base_stats[5]
        base_ff_stat: ti.i32 = base_stats[6]

        ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        ff_factor: ti.f32 = kernels_helpers.lookup_ref_ff(ff_idx)

        fever_acts: ti.i32 = 0
        if pair_caps_from_timeline != 0:
            fever_acts = ti.cast(kernels_helpers.grid_fever_activations[song_slot, ft_idx, ff_idx], ti.i32)
            if fever_acts < 0:
                fever_acts = 0

        non_fever_base_f: ti.f32 = non_fever_cas * ff_factor
        non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_base_f), ti.i32)

        cfg_mode: ti.i32 = fg_cfg_mode_list[best_ftff]
        cfg_base: ti.i32 = fg_cfg_base_list[best_ftff]
        fp_targets_vec = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        cfg_counts_vec = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        if cfg_mode != 0:
            local_cfg_idx: ti.i32 = best_cfg - cfg_base
            if local_cfg_idx < 0:
                local_cfg_idx = 0
            fp_targets_vec = _fg_decode_fp_targets_vec(local_cfg_idx, best_ftff, n_sections)
        if cfg_mode != 0:
            cfg_counts_vec = fp_targets_vec
        else:
            if best_cfg >= 0:
                for s in ti.static(range(FG_MAX_SECTIONS)):
                    if s < n_sections:
                        cfg_counts_vec[s] = fg_forced_counts[best_cfg, s]

        m0 = ti.cast(0, ti.u32)
        m1 = ti.cast(0, ti.u32)
        m2 = ti.cast(0, ti.u32)
        m3 = ti.cast(0, ti.u32)
        body_fever: ti.i32 = 0

        start_idx_vec = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        forced_applied = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        fill_notes = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

        budget: ti.i32 = total_budget - ft_gems - ff_gems
        if budget < 0:
            continue

        p_val: ti.i32 = (
            base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff)
        )
        s_val: ti.i32 = (
            base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff)
        )

        current_idx: ti.i32 = 0
        sec: ti.i32 = 0
        carry_time: ti.f32 = 0.0
        carry_idx: ti.i32 = 0
        while current_idx < total_notes:
            base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
            if base_notes_s < 0:
                base_notes_s = 0

            fp_target: ti.i32 = 0
            if sec < n_sections:
                if cfg_mode != 0:
                    fp_target = fp_targets_vec[sec]
                else:
                    fp_target = fg_forced_counts[best_cfg, sec]
                if fp_target < 0:
                    fp_target = 0

                # Clamp by per-pair dynamic cap (stored as forced-count caps)
                if sec < FG_MAX_SECTIONS:
                    pair_cap_forced: ti.i32 = 0
                    if pair_caps_from_timeline != 0:
                        if sec < fever_acts:
                            pair_cap_forced = _fg_section_forced_cap(sec)
                        else:
                            pair_cap_forced = 0
                    else:
                        pair_cap_forced = fg_pair_caps[ft_idx, ff_idx, sec]
                    if pair_cap_forced < 0:
                        pair_cap_forced = 0
                    notes_with_cap = ti.ceil(non_fever_base_f + ti.cast(pair_cap_forced, ti.f32) * 0.5)
                    fp_cap: ti.i32 = ti.cast(notes_with_cap, ti.i32) - non_fever_base
                    fp_target = ti.min(fp_target, fp_cap)

            forced_val: ti.i32 = _forced_from_fp_target(non_fever_base_f, non_fever_base, fp_target, non_fever_base)
            fp_calc: ti.i32 = fp_target

            notes_to_fill: ti.i32 = base_notes_s + fp_calc
            section_start: ti.i32 = current_idx
            end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
            actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
            forced_app: ti.i32 = ti.min(forced_val, actual_notes)

            if forced_app > 0:
                forced_start: ti.i32 = section_start + (1 - ti.cast(sec == 0, ti.i32))
                forced_end: ti.i32 = forced_start + forced_app - 1
                forced_end = ti.min(forced_end, end_normal - 1)
                if forced_end >= forced_start and forced_end < total_notes:
                    forced_t: ti.f32 = song_timestamps_great_candidate[forced_end]
                    if forced_t > carry_time:
                        carry_time = forced_t
                        carry_idx = forced_end

            if sec < n_sections and sec < FG_MAX_SECTIONS:
                start_idx_vec[sec] = section_start
                forced_applied[sec] = forced_app
                fill_notes[sec] = fp_calc

            current_idx = end_normal
            if current_idx >= total_notes:
                break

            fever_end_idx: ti.i32 = _fg_fever_end_idx_from_tables(
                current_idx, carry_time, carry_idx, ft_idx, total_notes
            )
            if fever_end_idx <= current_idx:
                fever_end_idx = ti.min(total_notes, current_idx + 1)

            if current_idx < head_len:
                head_end = ti.min(head_len, fever_end_idx)
                masks = _or_head_mask_range(m0, m1, m2, m3, current_idx, head_end)
                m0 = masks[0]
                m1 = masks[1]
                m2 = masks[2]
                m3 = masks[3]

            if fever_end_idx > head_len:
                body_start = head_len if current_idx < head_len else current_idx
                if fever_end_idx > body_start:
                    body_fever += fever_end_idx - body_start

            current_idx = fever_end_idx
            sec += 1

        body_len = ti.max(total_notes - head_len, 0)
        body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

        opt = _optimize_core_bits(
            budget,
            base_pp,
            base_cm,
            base_fm,
            p_val,
            s_val,
            is_p_pp,
            is_s_pp,
            is_p_cm,
            is_s_cm,
            is_p_fm,
            is_s_fm,
            is_p_ov,
            is_s_ov,
            m0,
            m1,
            m2,
            m3,
            head_len,
            body_fever,
            body_normal,
        )

        base_score: ti.i32 = opt[0]
        final_pp: ti.i32 = opt[1]
        final_cm: ti.i32 = opt[2]
        final_p_val: ti.i32 = opt[4]
        final_s_val: ti.i32 = opt[5]
        gems_pp: ti.i32 = opt[6]
        gems_cm: ti.i32 = opt[7]
        gems_fm: ti.i32 = opt[8]
        gems_ov: ti.i32 = opt[9]

        pp_factor: ti.f32 = kernels_helpers.lookup_ref_pp(final_pp)
        combo_mul: ti.f32 = kernels_helpers.lookup_ref_cm(final_cm)
        combo_span_scaled: ti.f32 = (combo_mul - 1.0) * 0.01

        base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
        combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

        great_penalty_base_head: ti.i32 = (
            ti.cast(ti.floor(ti.cast(final_p_val * 2, ti.f32) * (2.0 / 3.0)), ti.i32)
            + ti.cast(ti.floor(ti.cast(final_s_val, ti.f32) * (2.0 / 3.0)), ti.i32)
            + 150
        )
        great_penalty_base_raw: ti.f32 = (
            (ti.cast(final_p_val * 2, ti.f32) * (2.0 / 3.0)) + (ti.cast(final_s_val, ti.f32) * (2.0 / 3.0)) + 150.0
        )
        great_combo_value: ti.i32 = ti.cast(ti.floor(great_penalty_base_raw * combo_mul), ti.i32)
        body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)
        great_penalty_base_f: ti.f32 = ti.cast(great_penalty_base_head, ti.f32)

        score_penalty_total: ti.i32 = 0
        fill_penalty_total: ti.i32 = 0

        for s in ti.static(range(FG_MAX_SECTIONS)):
            if s < n_sections:
                fp_notes: ti.i32 = fill_notes[s]
                fill_penalty_total += fp_notes * combo_value

                forced_n: ti.i32 = forced_applied[s]
                if forced_n > 0:
                    start = start_idx_vec[s] + (1 if s > 0 else 0)
                    head_cap: ti.i32 = 100 - start
                    if head_cap < 0:
                        head_cap = 0
                    head_n: ti.i32 = forced_n
                    if head_n > head_cap:
                        head_n = head_cap
                    body_n: ti.i32 = forced_n - head_n

                    score_penalty_total += body_n * body_penalty

                    for k in range(head_n):
                        note_idx = start + k
                        if note_idx == 99:
                            score_penalty_total += body_penalty
                        else:
                            scaling: ti.f32 = 1.0 + combo_span_scaled * ti.cast(note_idx + 1, ti.f32)
                            perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                            great_val: ti.i32 = ti.cast(ti.floor(great_penalty_base_f * scaling), ti.i32)
                            score_penalty_total += ti.max(0, perfect_val - great_val)

        # Write per-call best (consistent with best_packed)
        fg_best_final_score[gid] = best_final
        fg_best_base_score[gid] = base_score
        fg_best_cfg_idx[gid] = best_cfg
        fg_best_ft[gid] = ft_gems
        fg_best_ff[gid] = ff_gems
        fg_best_g_pp[gid] = gems_pp
        fg_best_g_cm[gid] = gems_cm
        fg_best_g_fm[gid] = gems_fm
        fg_best_g_ov[gid] = gems_ov
        fg_best_score_penalty[gid] = score_penalty_total
        fg_best_fill_penalty[gid] = fill_penalty_total

        # Update global best only when accumulation is enabled (song_slot >= 0).
        if song_slot >= 0:
            old_score = fg_global_best_final_score[song_slot, gid]
            old_cfg = fg_global_best_cfg_idx[song_slot, gid]
            old_ft = fg_global_best_ft[song_slot, gid]
            old_ff = fg_global_best_ff[song_slot, gid]

            better = False
            if best_final > old_score:
                better = True
            elif best_final == old_score:
                if old_cfg < 0 and best_cfg >= 0:
                    better = True
                elif best_cfg >= 0 and best_cfg < old_cfg:
                    better = True
                elif best_cfg == old_cfg:
                    if ft_gems < old_ft:
                        better = True
                    elif ft_gems == old_ft and ff_gems < old_ff:
                        better = True

            if better:
                fg_global_best_final_score[song_slot, gid] = best_final
                fg_global_best_base_score[song_slot, gid] = base_score
                fg_global_best_cfg_idx[song_slot, gid] = best_cfg
                fg_global_best_ft[song_slot, gid] = ft_gems
                fg_global_best_ff[song_slot, gid] = ff_gems
                fg_global_best_g_pp[song_slot, gid] = gems_pp
                fg_global_best_g_cm[song_slot, gid] = gems_cm
                fg_global_best_g_fm[song_slot, gid] = gems_fm
                fg_global_best_g_ov[song_slot, gid] = gems_ov
                fg_global_best_score_penalty[song_slot, gid] = score_penalty_total
                fg_global_best_fill_penalty[song_slot, gid] = fill_penalty_total
                for s in ti.static(range(FG_MAX_SECTIONS)):
                    fg_global_best_cfg_counts[song_slot, gid, s] = cfg_counts_vec[s]


@ti.kernel
def fg_pack_results_kernel(n_genomes: ti.i32):
    """
    Pack best result fields + cfg_counts into a single contiguous array for efficient CPU download.

    This eliminates 11 separate to_numpy() calls (11 CPU waits) into 1 single download.
    MASSIVE speedup on weak CPUs that bottleneck on GPU synchronization.

    Column order: [final_score, base_score, cfg_idx, ft, ff, g_pp, g_cm, g_fm, g_ov, score_penalty, fill_penalty, cfg_counts...]
    """
    for g in range(n_genomes):
        fg_best_packed[g, 0] = fg_best_final_score[g]
        fg_best_packed[g, 1] = fg_best_base_score[g]
        fg_best_packed[g, 2] = fg_best_cfg_idx[g]
        fg_best_packed[g, 3] = fg_best_ft[g]
        fg_best_packed[g, 4] = fg_best_ff[g]
        fg_best_packed[g, 5] = fg_best_g_pp[g]
        fg_best_packed[g, 6] = fg_best_g_cm[g]
        fg_best_packed[g, 7] = fg_best_g_fm[g]
        fg_best_packed[g, 8] = fg_best_g_ov[g]
        fg_best_packed[g, 9] = fg_best_score_penalty[g]
        fg_best_packed[g, 10] = fg_best_fill_penalty[g]
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_best_packed[g, 11 + s] = fg_best_cfg_counts[g, s]


@ti.kernel
def fg_copy_best_packed_to_download_staging_kernel(out_packed: ti.template(), n_genomes: ti.i32):
    """
    Copy the populated prefix of `fg_best_packed` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_GENOMES buffer can add avoidable sync/transfer overhead when only a small
    number of genomes are active (e.g., a compact GA run).
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    total_cols = 11 + FG_MAX_SECTIONS
    for g, c in ti.ndrange(n_genomes, total_cols):
        out_packed[g, c] = fg_best_packed[g, c]


@ti.kernel
def fg_copy_global_best_packed_to_download_staging_kernel(out_packed: ti.template(), n_genomes: ti.i32):
    """
    Copy the populated prefix of `fg_global_best_packed` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    MAX_GENOMES buffer can add avoidable sync/transfer overhead when only a small
    number of genomes are active (e.g., a compact GA run).
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    total_cols = 11 + FG_MAX_SECTIONS
    for g, c in ti.ndrange(n_genomes, total_cols):
        out_packed[g, c] = fg_global_best_packed[g, c]


@ti.kernel
def fg_pack_global_best_kernel(session_slot: ti.i32, n_genomes: ti.i32):
    """
    Pack all global-best fields + cfg_counts into a single contiguous array for efficient CPU download.

    Mirrors `fg_pack_results_kernel`, but for the GPU-resident global best buffers used by
    multi-group accumulation.
    """
    for g in range(n_genomes):
        fg_global_best_packed[g, 0] = fg_global_best_final_score[session_slot, g]
        fg_global_best_packed[g, 1] = fg_global_best_base_score[session_slot, g]
        fg_global_best_packed[g, 2] = fg_global_best_cfg_idx[session_slot, g]
        fg_global_best_packed[g, 3] = fg_global_best_ft[session_slot, g]
        fg_global_best_packed[g, 4] = fg_global_best_ff[session_slot, g]
        fg_global_best_packed[g, 5] = fg_global_best_g_pp[session_slot, g]
        fg_global_best_packed[g, 6] = fg_global_best_g_cm[session_slot, g]
        fg_global_best_packed[g, 7] = fg_global_best_g_fm[session_slot, g]
        fg_global_best_packed[g, 8] = fg_global_best_g_ov[session_slot, g]
        fg_global_best_packed[g, 9] = fg_global_best_score_penalty[session_slot, g]
        fg_global_best_packed[g, 10] = fg_global_best_fill_penalty[session_slot, g]
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_global_best_packed[g, 11 + s] = fg_global_best_cfg_counts[session_slot, g, s]


@ti.kernel
def fg_select_global_best_topk_kernel(session_slot: ti.i32, n_genomes: ti.i32, topk: ti.i32):
    """
    Build a compact list of genome indices worth downloading from global_best.

    Output order:
    - keep items first (in ascending genome index)
    - then top-k candidates by final_score (descending), tie-breaking by lower genome index (stable)

    Eligibility filter for candidates:
    - final_score > fg_input_base_score
    - fg_global_best_fill_penalty > 0 (implies at least one forced section; matches CPU "valid config" intent)
    """
    k: ti.i32 = topk
    if k < 0:
        k = 0
    if k > ti.i32(FG_DOWNLOAD_TOPK_MAX):
        k = ti.i32(FG_DOWNLOAD_TOPK_MAX)

    # Clear output
    fg_selected_count[None] = 0
    ti.loop_config(serialize=True)
    for j in range(FG_DOWNLOAD_TOPK_MAX):
        fg_selected_indices[j] = -1

    # Keep set: include these indices unconditionally
    keep_count: ti.i32 = 0
    ti.loop_config(serialize=True)
    for i in range(n_genomes):
        if fg_keep_mask[i] != 0:
            if keep_count < ti.i32(FG_DOWNLOAD_TOPK_MAX):
                fg_selected_indices[keep_count] = i
                keep_count += 1

    start: ti.i32 = keep_count
    max_k: ti.i32 = k
    if start + max_k > ti.i32(FG_DOWNLOAD_TOPK_MAX):
        max_k = ti.i32(FG_DOWNLOAD_TOPK_MAX) - start
    if max_k < 0:
        max_k = 0

    # Initialize candidate slots
    ti.loop_config(serialize=True)
    for j in range(max_k):
        fg_selected_indices[start + j] = -1

    # Insert-sort top-k candidates by packed key
    ti.loop_config(serialize=True)
    for i in range(n_genomes):
        if fg_keep_mask[i] != 0:
            continue
        score: ti.i32 = fg_global_best_final_score[session_slot, i]
        if score <= fg_input_base_score[i]:
            continue
        if fg_global_best_fill_penalty[session_slot, i] <= 0:
            continue

        key: ti.i64 = (ti.cast(score, ti.i64) << 32) | ti.cast(0x7FFFFFFF - i, ti.i64)
        pos: ti.i32 = max_k

        # Find insertion point
        for j in range(max_k):
            idx_j: ti.i32 = fg_selected_indices[start + j]
            if idx_j < 0:
                pos = j
                break
            score_j: ti.i32 = fg_global_best_final_score[session_slot, idx_j]
            key_j: ti.i64 = (ti.cast(score_j, ti.i64) << 32) | ti.cast(0x7FFFFFFF - idx_j, ti.i64)
            if key > key_j:
                pos = j
                break

        if pos < max_k:
            # Shift down to make room
            for off in range(max_k - 1):
                s: ti.i32 = (max_k - 1) - off
                if s > pos:
                    fg_selected_indices[start + s] = fg_selected_indices[start + s - 1]
            fg_selected_indices[start + pos] = i

    # Compute final count (keep + filled candidates)
    count: ti.i32 = keep_count
    ti.loop_config(serialize=True)
    for j in range(max_k):
        if fg_selected_indices[start + j] >= 0:
            count += 1
        else:
            break
    fg_selected_count[None] = count


@ti.func
def _fg_frontier_cmp_base(lhs: ti.i32, rhs: ti.i32) -> ti.i32:
    out = 0
    base_l = fg_frontier_base_score[lhs]
    base_r = fg_frontier_base_score[rhs]
    if base_l != base_r:
        out = 1 if base_l > base_r else 0
    else:
        proxy_l = fg_frontier_proxy_score[lhs]
        proxy_r = fg_frontier_proxy_score[rhs]
        if proxy_l != proxy_r:
            out = 1 if proxy_l > proxy_r else 0
        else:
            prio_l = fg_frontier_priority[lhs]
            prio_r = fg_frontier_priority[rhs]
            if prio_l != prio_r:
                out = 1 if prio_l > prio_r else 0
            else:
                out = 1 if lhs < rhs else 0
    return out


@ti.func
def _fg_frontier_cmp_fg(lhs: ti.i32, rhs: ti.i32) -> ti.i32:
    out = 0
    keep_l = fg_frontier_force_keep[lhs]
    keep_r = fg_frontier_force_keep[rhs]
    if keep_l != keep_r:
        out = 1 if keep_l > keep_r else 0
    else:
        prio_l = fg_frontier_priority[lhs]
        prio_r = fg_frontier_priority[rhs]
        if prio_l != prio_r:
            out = 1 if prio_l > prio_r else 0
        else:
            proxy_l = fg_frontier_proxy_score[lhs]
            proxy_r = fg_frontier_proxy_score[rhs]
            if proxy_l != proxy_r:
                out = 1 if proxy_l > proxy_r else 0
            else:
                base_l = fg_frontier_base_score[lhs]
                base_r = fg_frontier_base_score[rhs]
                if base_l != base_r:
                    out = 1 if base_l > base_r else 0
                else:
                    out = 1 if lhs < rhs else 0
    return out


@ti.func
def _fg_frontier_selected_has_idx(idx: ti.i32, count: ti.i32) -> ti.i32:
    found = 0
    ti.loop_config(serialize=True)
    for j in range(FG_SIGNATURE_FRONTIER_MAX):
        if j < count and fg_frontier_selected_indices[j] == idx:
            found = 1
    return found


@ti.func
def _fg_frontier_selected_has_center(idx: ti.i32, count: ti.i32) -> ti.i32:
    ft_bucket = fg_frontier_center_bucket_ft[idx]
    ff_bucket = fg_frontier_center_bucket_ff[idx]
    found = 0
    ti.loop_config(serialize=True)
    for j in range(FG_SIGNATURE_FRONTIER_MAX):
        if j < count:
            sel = fg_frontier_selected_indices[j]
            if (
                sel >= 0
                and fg_frontier_center_bucket_ft[sel] == ft_bucket
                and fg_frontier_center_bucket_ff[sel] == ff_bucket
            ):
                found = 1
    return found


@ti.func
def _fg_frontier_selected_has_timing(idx: ti.i32, count: ti.i32) -> ti.i32:
    timing_bucket = fg_frontier_timing_bucket[idx]
    found = 0
    if timing_bucket <= 0:
        found = 1
    else:
        ti.loop_config(serialize=True)
        for j in range(FG_SIGNATURE_FRONTIER_MAX):
            if j < count:
                sel = fg_frontier_selected_indices[j]
                if sel >= 0 and fg_frontier_timing_bucket[sel] == timing_bucket:
                    found = 1
    return found


@ti.func
def _fg_frontier_try_add(idx: ti.i32, count: ti.i32, limit: ti.i32) -> ti.i32:
    out = count
    if count >= limit:
        out = count
    elif _fg_frontier_selected_has_idx(idx, count) != 0:
        out = count
    else:
        fg_frontier_selected_indices[count] = idx
        out = count + 1
    return out


@ti.kernel
def fg_select_signature_frontier_kernel(n_signatures: ti.i32, limit: ti.i32, top_base_keep: ti.i32):
    n = n_signatures
    if n < 0:
        n = 0
    if n > ti.i32(FG_SIGNATURE_FRONTIER_MAX):
        n = ti.i32(FG_SIGNATURE_FRONTIER_MAX)

    lim = limit
    if lim < 0:
        lim = 0
    if lim > n:
        lim = n

    base_keep = top_base_keep
    if base_keep < 0:
        base_keep = 0
    if base_keep > lim:
        base_keep = lim

    fg_frontier_selected_count[None] = 0
    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        fg_frontier_selected_indices[i] = -1
        fg_frontier_base_order[i] = -1
        fg_frontier_fg_order[i] = -1
        if i < n:
            fg_frontier_base_order[i] = i
            fg_frontier_fg_order[i] = i

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n:
            continue
        cur = fg_frontier_base_order[i]
        j = i
        while j > 0 and _fg_frontier_cmp_base(cur, fg_frontier_base_order[j - 1]) != 0:
            fg_frontier_base_order[j] = fg_frontier_base_order[j - 1]
            j -= 1
        fg_frontier_base_order[j] = cur

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n:
            continue
        cur = fg_frontier_fg_order[i]
        j = i
        while j > 0 and _fg_frontier_cmp_fg(cur, fg_frontier_fg_order[j - 1]) != 0:
            fg_frontier_fg_order[j] = fg_frontier_fg_order[j - 1]
            j -= 1
        fg_frontier_fg_order[j] = cur

    extra_budget = lim - base_keep
    if extra_budget < 0:
        extra_budget = 0
    keep_budget = 0
    if extra_budget > 0:
        keep_budget = extra_budget // 2
        if keep_budget < 2:
            keep_budget = 2
        if keep_budget > extra_budget:
            keep_budget = extra_budget
    keep_budget_end = base_keep + keep_budget
    if keep_budget_end > lim:
        keep_budget_end = lim

    priority_budget = 0
    if extra_budget > 0:
        priority_budget = extra_budget
        if priority_budget > 5:
            priority_budget = 5
        if priority_budget < 2:
            priority_budget = 2
        rem = lim - keep_budget_end
        if rem < 0:
            rem = 0
        if priority_budget > rem:
            priority_budget = rem
    priority_budget_end = keep_budget_end + priority_budget
    if priority_budget_end > lim:
        priority_budget_end = lim

    fg_budget_end = priority_budget_end
    if extra_budget > 0:
        fg_budget_end = base_keep + priority_budget
        scaled_extra = (extra_budget * 85) // 100
        if scaled_extra > fg_budget_end - base_keep:
            fg_budget_end = base_keep + scaled_extra
        if fg_budget_end < priority_budget_end:
            fg_budget_end = priority_budget_end
        if fg_budget_end > lim:
            fg_budget_end = lim

    selected = 0
    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= base_keep:
            continue
        idx = fg_frontier_base_order[i]
        if idx >= 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= keep_budget_end:
            continue
        idx = fg_frontier_base_order[i]
        if idx >= 0 and fg_frontier_force_keep[idx] != 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= priority_budget_end:
            continue
        idx = fg_frontier_fg_order[i]
        if idx >= 0 and fg_frontier_priority[idx] != 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= fg_budget_end:
            continue
        idx = fg_frontier_fg_order[i]
        if idx >= 0 and _fg_frontier_selected_has_timing(idx, selected) == 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= fg_budget_end:
            continue
        idx = fg_frontier_fg_order[i]
        if idx >= 0 and _fg_frontier_selected_has_center(idx, selected) == 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= fg_budget_end:
            continue
        idx = fg_frontier_fg_order[i]
        if idx >= 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    ti.loop_config(serialize=True)
    for i in range(FG_SIGNATURE_FRONTIER_MAX):
        if i >= n or selected >= lim:
            continue
        idx = fg_frontier_base_order[i]
        if idx >= 0:
            selected = _fg_frontier_try_add(idx, selected, lim)

    fg_frontier_selected_count[None] = selected


@ti.kernel
def fg_copy_signature_frontier_selected_to_batch_kernel(batch_idx: ti.i32):
    if batch_idx >= 0 and batch_idx < ti.i32(FG_SIGNATURE_FRONTIER_BATCH_MAX):
        fg_frontier_selected_count_batch[batch_idx] = fg_frontier_selected_count[None]
        for j in range(FG_SIGNATURE_FRONTIER_MAX):
            fg_frontier_selected_indices_batch[batch_idx, j] = fg_frontier_selected_indices[j]


@ti.kernel
def fg_pack_selected_global_best_kernel(session_slot: ti.i32, n_selected: ti.i32):
    """Pack selected rows from global_best into fg_selected_packed for fast CPU download.

    Column order (12 + FG_MAX_SECTIONS):
      [genome_idx, final_score, base_score, cfg_idx, ft, ff, g_pp, g_cm, g_fm, g_ov, score_penalty, fill_penalty, cfg_counts...]
    """
    total_cols = 12 + FG_MAX_SECTIONS
    for j in range(n_selected):
        idx: ti.i32 = fg_selected_indices[j]
        fg_selected_packed[j, 0] = idx
        if idx < 0:
            for c in range(1, total_cols):
                fg_selected_packed[j, c] = 0
            continue
        fg_selected_packed[j, 1] = fg_global_best_final_score[session_slot, idx]
        fg_selected_packed[j, 2] = fg_global_best_base_score[session_slot, idx]
        fg_selected_packed[j, 3] = fg_global_best_cfg_idx[session_slot, idx]
        fg_selected_packed[j, 4] = fg_global_best_ft[session_slot, idx]
        fg_selected_packed[j, 5] = fg_global_best_ff[session_slot, idx]
        fg_selected_packed[j, 6] = fg_global_best_g_pp[session_slot, idx]
        fg_selected_packed[j, 7] = fg_global_best_g_cm[session_slot, idx]
        fg_selected_packed[j, 8] = fg_global_best_g_fm[session_slot, idx]
        fg_selected_packed[j, 9] = fg_global_best_g_ov[session_slot, idx]
        fg_selected_packed[j, 10] = fg_global_best_score_penalty[session_slot, idx]
        fg_selected_packed[j, 11] = fg_global_best_fill_penalty[session_slot, idx]
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_selected_packed[j, 12 + s] = fg_global_best_cfg_counts[session_slot, idx, s]


@ti.kernel
def fg_pack_selected_global_best_batch_kernel(session_slot: ti.i32, n_selected: ti.i32, batch_idx: ti.i32):
    """Pack selected rows from global_best into `fg_selected_packed_batch[batch_idx]`.

    This is used by executor-side batching so multiple payloads can be downloaded via a single `to_numpy()`.
    """
    if batch_idx >= 0 and batch_idx < ti.i32(FG_DOWNLOAD_BATCH_MAX):
        total_cols = 12 + FG_MAX_SECTIONS
        for j in range(n_selected):
            idx: ti.i32 = fg_selected_indices[j]
            fg_selected_packed_batch[batch_idx, j, 0] = idx
            if idx < 0:
                for c in range(1, total_cols):
                    fg_selected_packed_batch[batch_idx, j, c] = 0
                continue
            fg_selected_packed_batch[batch_idx, j, 1] = fg_global_best_final_score[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 2] = fg_global_best_base_score[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 3] = fg_global_best_cfg_idx[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 4] = fg_global_best_ft[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 5] = fg_global_best_ff[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 6] = fg_global_best_g_pp[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 7] = fg_global_best_g_cm[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 8] = fg_global_best_g_fm[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 9] = fg_global_best_g_ov[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 10] = fg_global_best_score_penalty[session_slot, idx]
            fg_selected_packed_batch[batch_idx, j, 11] = fg_global_best_fill_penalty[session_slot, idx]
            for s in ti.static(range(FG_MAX_SECTIONS)):
                fg_selected_packed_batch[batch_idx, j, 12 + s] = fg_global_best_cfg_counts[session_slot, idx, s]


@ti.kernel
def fg_copy_selected_packed_batch_to_download_staging_kernel(out_packed: ti.template(), n_payloads: ti.i32):
    """
    Copy the populated prefix of `fg_selected_packed_batch` into a smaller staging field.

    On Vulkan, `to_numpy()` transfers the full field shape, so downloading the padded
    FG_DOWNLOAD_BATCH_MAX buffer can dominate throughput when only a small number of
    payloads are active in a fused executor bundle.
    """
    ti.loop_config(block_dim=_KERNEL_BLOCK_DIM)
    total_cols = 12 + FG_MAX_SECTIONS
    for batch_idx, j in ti.ndrange(n_payloads, FG_DOWNLOAD_TOPK_MAX):
        for c in range(total_cols):
            out_packed[batch_idx, j, c] = fg_selected_packed_batch[batch_idx, j, c]


@ti.kernel
def fg_reset_global_best_kernel(session_slot: ti.i32, n_genomes: ti.i32):
    """
    Reset global best fields to sentinel values before multi-group processing.

    Call this once at the start of a batch of FG groups, before the loop.
    """
    for i in range(n_genomes):
        fg_global_best_final_score[session_slot, i] = -1
        fg_global_best_base_score[session_slot, i] = 0
        fg_global_best_cfg_idx[session_slot, i] = -1
        fg_global_best_ft[session_slot, i] = 0
        fg_global_best_ff[session_slot, i] = 0
        fg_global_best_g_pp[session_slot, i] = 0
        fg_global_best_g_cm[session_slot, i] = 0
        fg_global_best_g_fm[session_slot, i] = 0
        fg_global_best_g_ov[session_slot, i] = 0
        fg_global_best_score_penalty[session_slot, i] = 0
        fg_global_best_fill_penalty[session_slot, i] = 0
        for s in ti.static(range(FG_MAX_SECTIONS)):
            fg_global_best_cfg_counts[session_slot, i, s] = 0


@ti.kernel
def fg_update_global_best_kernel(session_slot: ti.i32, n_genomes: ti.i32):
    """
    Compare current fg_best_* results with fg_global_best_*, update if better.

    Call this after each solve_force_greats_finder_gpu() call to accumulate
    the best results across all groups without downloading to CPU.
    """
    for gid in range(n_genomes):
        new_score = fg_best_final_score[gid]
        old_score = fg_global_best_final_score[session_slot, gid]
        new_cfg = fg_best_cfg_idx[gid]
        old_cfg = fg_global_best_cfg_idx[session_slot, gid]
        new_ft = fg_best_ft[gid]
        old_ft = fg_global_best_ft[session_slot, gid]
        new_ff = fg_best_ff[gid]
        old_ff = fg_global_best_ff[session_slot, gid]

        # Deterministic tie-breaking:
        # 1) Higher final score wins.
        # 2) If scores tie, prefer lower cfg_idx (matches stage1 packed tie-break).
        # 3) If still tied, prefer lower (ft, ff) lexicographically for stability.
        better = False
        if new_score > old_score:
            better = True
        elif new_score == old_score:
            if old_cfg < 0 and new_cfg >= 0:
                better = True
            elif new_cfg >= 0 and new_cfg < old_cfg:
                better = True
            elif new_cfg == old_cfg:
                if new_ft < old_ft:
                    better = True
                elif new_ft == old_ft and new_ff < old_ff:
                    better = True

        if better:
            fg_global_best_final_score[session_slot, gid] = new_score
            fg_global_best_base_score[session_slot, gid] = fg_best_base_score[gid]
            fg_global_best_cfg_idx[session_slot, gid] = new_cfg
            fg_global_best_ft[session_slot, gid] = new_ft
            fg_global_best_ff[session_slot, gid] = new_ff
            fg_global_best_g_pp[session_slot, gid] = fg_best_g_pp[gid]
            fg_global_best_g_cm[session_slot, gid] = fg_best_g_cm[gid]
            fg_global_best_g_fm[session_slot, gid] = fg_best_g_fm[gid]
            fg_global_best_g_ov[session_slot, gid] = fg_best_g_ov[gid]
            fg_global_best_score_penalty[session_slot, gid] = fg_best_score_penalty[gid]
            fg_global_best_fill_penalty[session_slot, gid] = fg_best_fill_penalty[gid]
