"""
ForceGreatsFinder GPU kernels (Taichi).

This module contains ONLY the FG finder kernels and their helper @ti.func's.
It reuses the shared scoring helpers from `gear_optimizer.solver.taichi_gem.kernels`
(reference lookups + score calculation).

Fields are bound at runtime via `force_greats.fields.bind_fields()`.
"""

import taichi as ti

from .. import kernels as _core
from .fields import FG_MAX_SECTIONS


# ============================================================================
# FIELD PLACEHOLDERS (bound by force_greats.fields.bind_fields)
# ============================================================================

song_timestamps = None
fg_forced_counts = None
fg_ft_list = None
fg_ff_list = None

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
    Greedy gem allocation optimizer (bitmask head scoring).

    Returns vector:
      [score, pp, cm, fm, p_val, s_val, g_pp, g_cm, g_fm, g_ov]
    """
    GEM_SCALE_NORMAL: ti.i32 = 2
    GEM_SCALE_FEVER: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    MAX_STAT: ti.i32 = 160
    PP_TIE_LOOKAHEAD_MAX: ti.i32 = 8

    gems_pp: ti.i32 = 0
    gems_cm: ti.i32 = 0
    gems_fm: ti.i32 = 0
    gems_ov: ti.i32 = 0
    remaining: ti.i32 = budget

    pp: ti.i32 = cur_pp
    cm: ti.i32 = cur_cm
    fm: ti.i32 = cur_fm
    p_val: ti.i32 = cur_p_val
    s_val: ti.i32 = cur_s_val

    best_final_score: ti.i32 = 0

    while remaining > 0:
        fill_budget: ti.i32 = remaining - 1
        fill_bonus: ti.i32 = fill_budget * ELEMENTAL_GEM_SCALE if fill_budget > 0 else 0

        c_mul_cur: ti.f32 = _core.lookup_ref_cm(cm)
        f_mul_cur: ti.f32 = _core.lookup_ref_fm(fm)

        # OV wins exact ties by default
        t_p: ti.i32 = p_val + (ELEMENTAL_GEM_SCALE * is_p_ov) + (fill_bonus * is_p_ov)
        t_s: ti.i32 = s_val + (ELEMENTAL_GEM_SCALE * is_s_ov) + (fill_bonus * is_s_ov)
        pp_factor: ti.f32 = _core.lookup_ref_pp(pp)
        base: ti.f32 = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
        best_score: ti.i32 = _core.calc_score_with_grid_bits(
            base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
        )
        best_opt: ti.i32 = 3

        pp_score: ti.i32 = -1

        # PP gem
        if pp < MAX_STAT:
            t_pp: ti.i32 = pp + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus * is_s_ov)
            pp_factor = _core.lookup_ref_pp(t_pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            pp_score = _core.calc_score_with_grid_bits(
                base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if pp_score > best_score:
                best_score = pp_score
                best_opt = 0

        # CM gem
        if cm < MAX_STAT:
            t_cm: ti.i32 = cm + GEM_SCALE_NORMAL
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_cm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_cm) + (fill_bonus * is_s_ov)
            pp_factor = _core.lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            c_mul: ti.f32 = _core.lookup_ref_cm(t_cm)
            score: ti.i32 = _core.calc_score_with_grid_bits(
                base, c_mul, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if score > best_score:
                best_score = score
                best_opt = 1

        # FM gem
        if fm < MAX_STAT:
            t_fm: ti.i32 = fm + GEM_SCALE_FEVER
            t_p = p_val + (GEM_STAT_TO_ELEMENT * is_p_fm) + (fill_bonus * is_p_ov)
            t_s = s_val + (GEM_STAT_TO_ELEMENT * is_s_fm) + (fill_bonus * is_s_ov)
            pp_factor = _core.lookup_ref_pp(pp)
            base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
            f_mul: ti.f32 = _core.lookup_ref_fm(t_fm)
            score = _core.calc_score_with_grid_bits(
                base, c_mul_cur, f_mul, m0, m1, m2, m3, head_len, count_fever, count_normal
            )
            if score > best_score:
                best_score = score
                best_opt = 2

        # PP lookahead (optional)
        if best_opt == 3 and pp_score == best_score and remaining > 1:
            max_k: ti.i32 = remaining
            if max_k > PP_TIE_LOOKAHEAD_MAX:
                max_k = PP_TIE_LOOKAHEAD_MAX
            k: ti.i32 = 2
            while k <= max_k:
                fill_bonus_k: ti.i32 = (remaining - k) * ELEMENTAL_GEM_SCALE
                t_pp: ti.i32 = pp + (k * GEM_SCALE_NORMAL)
                t_p = p_val + (k * GEM_STAT_TO_ELEMENT * is_p_pp) + (fill_bonus_k * is_p_ov)
                t_s = s_val + (k * GEM_STAT_TO_ELEMENT * is_s_pp) + (fill_bonus_k * is_s_ov)
                pp_factor = _core.lookup_ref_pp(t_pp)
                base = ti.cast((t_p * 2) + t_s, ti.f32) + pp_factor
                score_k: ti.i32 = _core.calc_score_with_grid_bits(
                    base, c_mul_cur, f_mul_cur, m0, m1, m2, m3, head_len, count_fever, count_normal
                )
                if score_k > best_score:
                    best_opt = 0
                    break
                k += 1

        # Apply best option
        if best_opt == 0:
            pp += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_pp
            s_val += GEM_STAT_TO_ELEMENT * is_s_pp
            gems_pp += 1
        elif best_opt == 1:
            cm += GEM_SCALE_NORMAL
            p_val += GEM_STAT_TO_ELEMENT * is_p_cm
            s_val += GEM_STAT_TO_ELEMENT * is_s_cm
            gems_cm += 1
        elif best_opt == 2:
            fm += GEM_SCALE_FEVER
            p_val += GEM_STAT_TO_ELEMENT * is_p_fm
            s_val += GEM_STAT_TO_ELEMENT * is_s_fm
            gems_fm += 1
        else:
            p_val += ELEMENTAL_GEM_SCALE * is_p_ov
            s_val += ELEMENTAL_GEM_SCALE * is_s_ov
            gems_ov += 1

        remaining -= 1
        best_final_score = best_score

    return ti.Vector(
        [
            best_final_score,
            pp,
            cm,
            fm,
            p_val,
            s_val,
            gems_pp,
            gems_cm,
            gems_fm,
            gems_ov,
        ]
    )


# ============================================================================
# KERNELS
# ============================================================================

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


@ti.kernel
def fg_stage1_init_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """Initialize Stage 1 fields before reduction (supports cfg-chunk accumulation)."""
    for g, f in ti.ndrange(n_genomes, n_ftff):
        fg_stage1_final_score[g, f] = -1
        fg_stage1_base_score[g, f] = 0
        fg_stage1_cfg_idx[g, f] = -1
        fg_stage1_g_pp[g, f] = 0
        fg_stage1_g_cm[g, f] = 0
        fg_stage1_g_fm[g, f] = 0
        fg_stage1_g_ov[g, f] = 0
        fg_stage1_score_penalty[g, f] = 0
        fg_stage1_fill_penalty[g, f] = 0


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
):
    """
    Stage 1: Find best cfg for each (genome, ftff) pair.

    Parallelizes over (genome, ftff), loops cfg sequentially inside.
    NO ATOMICS - each (g, f) pair has its own output slot.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)

    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15

    for g, ftff_idx in ti.ndrange(n_genomes, n_ftff):
        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        if ft_gems + ff_gems > total_budget:
            continue

        # Load genome base stats (hoisted out of cfg loop)
        # Load genome base stats (hoisted out of cfg loop)
        # [pp, cm, fm, p_val, s_val, ft, ff]
        base_stats = _core.genome_base_stats[g]
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
        ft_factor: ti.f32 = _core.lookup_ref_ft(ft_idx)
        ff_factor: ti.f32 = _core.lookup_ref_ff(ff_idx)

        non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_cas * ff_factor), ti.i32)
        non_fever_great_to_fill: ti.i32 = ti.cast(
            ti.ceil(ti.max(1.0, non_fever_cas * ff_factor * 2.0)), ti.i32
        )
        real_fever_time: ti.f32 = fever_time_cas * ft_factor

        # Accumulate across cfg-chunks: seed from existing stage1 result
        best_final: ti.i32 = fg_stage1_final_score[g, ftff_idx]
        best_base: ti.i32 = 0
        best_cfg: ti.i32 = 0
        best_pp: ti.i32 = 0
        best_cm: ti.i32 = 0
        best_fm: ti.i32 = 0
        best_ov: ti.i32 = 0
        best_sp: ti.i32 = 0
        best_fp: ti.i32 = 0
        if best_final >= 0:
            best_base = fg_stage1_base_score[g, ftff_idx]
            best_cfg = fg_stage1_cfg_idx[g, ftff_idx]
            best_pp = fg_stage1_g_pp[g, ftff_idx]
            best_cm = fg_stage1_g_cm[g, ftff_idx]
            best_fm = fg_stage1_g_fm[g, ftff_idx]
            best_ov = fg_stage1_g_ov[g, ftff_idx]
            best_sp = fg_stage1_score_penalty[g, ftff_idx]
            best_fp = fg_stage1_fill_penalty[g, ftff_idx]

        # Sequential loop over configs (no atomics needed!)
        for cfg_idx in range(n_cfg):
            # Timeline simulation -> head mask bits + body fever count
            m0 = ti.cast(0, ti.u32)
            m1 = ti.cast(0, ti.u32)
            m2 = ti.cast(0, ti.u32)
            m3 = ti.cast(0, ti.u32)
            body_fever: ti.i32 = 0

            start_idx = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            forced_applied = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            fill_notes = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
            skip_wasted = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

            current_idx: ti.i32 = 0
            sec: ti.i32 = 0
            while current_idx < total_notes:
                base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
                if base_notes_s < 0:
                    base_notes_s = 0

                forced_val: ti.i32 = 0
                if sec < n_sections:
                    forced_val = fg_forced_counts[cfg_idx, sec]
                    if forced_val < 0:
                        forced_val = 0
                    forced_val = ti.min(forced_val, non_fever_base)

                fp_calc: ti.i32 = 0
                if forced_val > 0:
                    fp_calc = ti.cast(
                        ti.ceil(
                            ti.max(
                                0.0,
                                (ti.cast(non_fever_base * forced_val, ti.f32) / ti.cast(non_fever_great_to_fill, ti.f32)),
                            )
                        ),
                        ti.i32,
                    )

                notes_to_fill: ti.i32 = base_notes_s + fp_calc
                section_start: ti.i32 = current_idx
                end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
                actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
                forced_app: ti.i32 = ti.min(forced_val, actual_notes)

                if sec < n_sections and sec < FG_MAX_SECTIONS:
                    start_idx[sec] = section_start
                    forced_applied[sec] = forced_app
                    fill_notes[sec] = fp_calc
                    skip_wasted[sec] = 1 if sec == 0 else 0

                current_idx = end_normal
                if current_idx >= total_notes:
                    break

                # Fever section
                start_time: ti.f32 = song_timestamps[current_idx]
                end_time: ti.f32 = start_time + real_fever_time
                fever_end_idx: ti.i32 = _core.binary_search_left_from(song_timestamps, total_notes, end_time, current_idx)
                if fever_end_idx <= current_idx:
                    fever_end_idx = ti.min(total_notes, current_idx + 1)

                # Mark head fever notes (bitset)
                if current_idx < head_len:
                    head_end = ti.min(head_len, fever_end_idx)
                    for i in range(current_idx, head_end):
                        word = i >> 5
                        bit = ti.cast(1, ti.u32) << ti.cast(i & 31, ti.u32)
                        if word == 0:
                            m0 |= bit
                        elif word == 1:
                            m1 |= bit
                        elif word == 2:
                            m2 |= bit
                        else:
                            m3 |= bit

                # Count body fever notes
                if fever_end_idx > head_len:
                    body_start = head_len if current_idx < head_len else current_idx
                    if fever_end_idx > body_start:
                        body_fever += (fever_end_idx - body_start)

                current_idx = fever_end_idx
                sec += 1

            body_len = ti.max(total_notes - head_len, 0)
            body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

            budget: ti.i32 = total_budget - ft_gems - ff_gems
            if budget < 0:
                continue

            p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (
                ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff
            )
            s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (
                ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff
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
            final_fm: ti.i32 = opt[3]
            final_p_val: ti.i32 = opt[4]
            final_s_val: ti.i32 = opt[5]
            gems_pp: ti.i32 = opt[6]
            gems_cm: ti.i32 = opt[7]
            gems_fm: ti.i32 = opt[8]
            gems_ov: ti.i32 = opt[9]

            # Penalty math
            pp_factor: ti.f32 = _core.lookup_ref_pp(final_pp)
            combo_mul: ti.f32 = _core.lookup_ref_cm(final_cm)
            combo_span: ti.f32 = combo_mul - 1.0

            base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
            combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

            great_penalty_base: ti.i32 = ti.cast(
                ti.floor((ti.cast((final_p_val * 2) + final_s_val, ti.f32) * (2.0 / 3.0)) + 150.0),
                ti.i32,
            )
            great_combo_value: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * combo_mul), ti.i32)
            body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)

            score_penalty_total: ti.i32 = 0
            fill_penalty_total: ti.i32 = 0

            for s in range(ti.min(n_sections, FG_MAX_SECTIONS)):
                fp_notes: ti.i32 = fill_notes[s]
                fill_penalty_total += fp_notes * combo_value

                forced_n: ti.i32 = forced_applied[s]
                if forced_n > 0:
                    start = start_idx[s] + (1 if skip_wasted[s] != 0 else 0)
                    if start > total_notes:
                        start = total_notes
                    for k in range(forced_n):
                        note_idx = start + k
                        if note_idx < 100:
                            scaling: ti.f32 = 1.0 + combo_span * (ti.cast(note_idx + 1, ti.f32) / 100.0)
                            perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                            great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * scaling), ti.i32)
                            pen: ti.i32 = ti.max(0, perfect_val - great_val)
                            score_penalty_total += pen
                        else:
                            score_penalty_total += body_penalty

            final_score: ti.i32 = base_score - score_penalty_total
            if final_score < 0:
                final_score = 0

            if final_score > best_final:
                best_final = final_score
                best_base = base_score
                best_cfg = cfg_offset + cfg_idx
                best_pp = gems_pp
                best_cm = gems_cm
                best_fm = gems_fm
                best_ov = gems_ov
                best_sp = score_penalty_total
                best_fp = fill_penalty_total

        fg_stage1_final_score[g, ftff_idx] = best_final
        fg_stage1_base_score[g, ftff_idx] = best_base
        fg_stage1_cfg_idx[g, ftff_idx] = best_cfg
        fg_stage1_g_pp[g, ftff_idx] = best_pp
        fg_stage1_g_cm[g, ftff_idx] = best_cm
        fg_stage1_g_fm[g, ftff_idx] = best_fm
        fg_stage1_g_ov[g, ftff_idx] = best_ov
        fg_stage1_score_penalty[g, ftff_idx] = best_sp
        fg_stage1_fill_penalty[g, ftff_idx] = best_fp


@ti.kernel
def fg_stage2_kernel(n_genomes: ti.i32, n_ftff: ti.i32):
    """
    Stage 2: Reduce across ftff to find best per genome.

    Each thread handles one genome, loops over ftff sequentially.
    """
    for g in range(n_genomes):
        best_final: ti.i32 = -1
        best_ftff: ti.i32 = 0

        for f in range(n_ftff):
            score = fg_stage1_final_score[g, f]
            if score > best_final:
                best_final = score
                best_ftff = f

        if best_final >= 0:
            fg_best_final_score[g] = best_final
            fg_best_base_score[g] = fg_stage1_base_score[g, best_ftff]
            fg_best_cfg_idx[g] = fg_stage1_cfg_idx[g, best_ftff]
            fg_best_ft[g] = fg_ft_list[best_ftff]
            fg_best_ff[g] = fg_ff_list[best_ftff]
            fg_best_g_pp[g] = fg_stage1_g_pp[g, best_ftff]
            fg_best_g_cm[g] = fg_stage1_g_cm[g, best_ftff]
            fg_best_g_fm[g] = fg_stage1_g_fm[g, best_ftff]
            fg_best_g_ov[g] = fg_stage1_g_ov[g, best_ftff]
            fg_best_score_penalty[g] = fg_stage1_score_penalty[g, best_ftff]
            fg_best_fill_penalty[g] = fg_stage1_fill_penalty[g, best_ftff]


@ti.kernel
def fg_stage1_flat_kernel(
    n_work_items: ti.i32,
    n_cfg: ti.i32,
    cfg_offset: ti.i32,
    total_notes: ti.i32,
    long_notes: ti.i32,
    last_note_time: ti.f32,
    total_budget: ti.i32,
    gem_scale_fever: ti.i32,
    n_sections: ti.i32,
    is_p_ft: ti.i32, is_s_ft: ti.i32,
    is_p_ff: ti.i32, is_s_ff: ti.i32,
    is_p_pp: ti.i32, is_s_pp: ti.i32,
    is_p_cm: ti.i32, is_s_cm: ti.i32,
    is_p_fm: ti.i32, is_s_fm: ti.i32,
    is_p_ov: ti.i32, is_s_ov: ti.i32,
):
    """
    GPU-friendly Stage 1: One thread per (work_item, cfg) pair.
    
    Parallelizes over (work_item * n_cfg), where work_item is (genome, ftff).
    Uses atomic_max for reduction within each (genome, ftff) slot.
    """
    GEM_STAT_TO_ELEMENT: ti.i32 = 3
    ELEMENTAL_GEM_SCALE: ti.i32 = 6
    MAX_STAT: ti.i32 = 160

    head_len: ti.i32 = ti.min(total_notes, 100)
    non_fever_cas: ti.f32 = ti.max(0.0, (ti.cast(total_notes - long_notes, ti.f32) * 0.333))
    fever_time_cas: ti.f32 = last_note_time * 0.15 + 0.15

    # Flatten: each thread handles one (work_item, cfg) pair
    for flat_idx in range(n_work_items * n_cfg):
        work_idx: ti.i32 = flat_idx // n_cfg
        cfg_idx: ti.i32 = flat_idx % n_cfg

        # Decode work item -> (genome, ftff)
        g: ti.i32 = fg_flat_work_genome[work_idx]
        ftff_idx: ti.i32 = fg_flat_work_ftff[work_idx]

        ft_gems: ti.i32 = fg_ft_list[ftff_idx]
        ff_gems: ti.i32 = fg_ff_list[ftff_idx]
        if ft_gems + ff_gems > total_budget:
            continue

        # Load genome base stats
        base_stats = _core.genome_base_stats[g]
        base_pp: ti.i32 = base_stats[0]
        base_cm: ti.i32 = base_stats[1]
        base_fm: ti.i32 = base_stats[2]
        base_p_val: ti.i32 = base_stats[3]
        base_s_val: ti.i32 = base_stats[4]
        base_ft_stat: ti.i32 = base_stats[5]
        base_ff_stat: ti.i32 = base_stats[6]

        # Fever multipliers
        ft_stat_val: ti.i32 = base_ft_stat + (ft_gems * gem_scale_fever)
        ff_stat_val: ti.i32 = base_ff_stat + (ff_gems * gem_scale_fever)
        ft_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ft_stat_val))
        ff_idx: ti.i32 = ti.min(MAX_STAT, ti.max(0, ff_stat_val))
        ft_factor: ti.f32 = _core.lookup_ref_ft(ft_idx)
        ff_factor: ti.f32 = _core.lookup_ref_ff(ff_idx)

        non_fever_base: ti.i32 = ti.cast(ti.ceil(non_fever_cas * ff_factor), ti.i32)
        non_fever_great_to_fill: ti.i32 = ti.cast(
            ti.ceil(ti.max(1.0, non_fever_cas * ff_factor * 2.0)), ti.i32
        )
        real_fever_time: ti.f32 = fever_time_cas * ft_factor

        # Timeline simulation for this ONE config
        m0 = ti.cast(0, ti.u32)
        m1 = ti.cast(0, ti.u32)
        m2 = ti.cast(0, ti.u32)
        m3 = ti.cast(0, ti.u32)
        body_fever: ti.i32 = 0

        start_idx_vec = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        forced_applied = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        fill_notes = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)
        skip_wasted = ti.Vector.zero(ti.i32, FG_MAX_SECTIONS)

        current_idx: ti.i32 = 0
        sec: ti.i32 = 0
        while current_idx < total_notes:
            base_notes_s: ti.i32 = non_fever_base - 1 if sec == 0 else non_fever_base
            if base_notes_s < 0:
                base_notes_s = 0

            forced_val: ti.i32 = 0
            if sec < n_sections:
                forced_val = fg_forced_counts[cfg_idx, sec]
                if forced_val < 0:
                    forced_val = 0
                forced_val = ti.min(forced_val, non_fever_base)

            fp_calc: ti.i32 = 0
            if forced_val > 0:
                fp_calc = ti.cast(
                    ti.ceil(
                        ti.max(
                            0.0,
                            (ti.cast(non_fever_base * forced_val, ti.f32) / ti.cast(non_fever_great_to_fill, ti.f32)),
                        )
                    ),
                    ti.i32,
                )

            notes_to_fill: ti.i32 = base_notes_s + fp_calc
            section_start: ti.i32 = current_idx
            end_normal: ti.i32 = ti.min(total_notes, section_start + notes_to_fill)
            actual_notes: ti.i32 = ti.max(0, end_normal - section_start)
            forced_app: ti.i32 = ti.min(forced_val, actual_notes)

            if sec < n_sections and sec < FG_MAX_SECTIONS:
                start_idx_vec[sec] = section_start
                forced_applied[sec] = forced_app
                fill_notes[sec] = fp_calc
                skip_wasted[sec] = 1 if sec == 0 else 0

            current_idx = end_normal
            if current_idx >= total_notes:
                break

            # Fever section
            start_time: ti.f32 = song_timestamps[current_idx]
            end_time: ti.f32 = start_time + real_fever_time
            fever_end_idx: ti.i32 = _core.binary_search_left_from(song_timestamps, total_notes, end_time, current_idx)
            if fever_end_idx <= current_idx:
                fever_end_idx = ti.min(total_notes, current_idx + 1)

            # Mark head fever notes (bitset)
            if current_idx < head_len:
                head_end = ti.min(head_len, fever_end_idx)
                for i in range(current_idx, head_end):
                    word = i >> 5
                    bit = ti.cast(1, ti.u32) << ti.cast(i & 31, ti.u32)
                    if word == 0:
                        m0 |= bit
                    elif word == 1:
                        m1 |= bit
                    elif word == 2:
                        m2 |= bit
                    else:
                        m3 |= bit

            # Count body fever notes
            if fever_end_idx > head_len:
                body_start = head_len if current_idx < head_len else current_idx
                if fever_end_idx > body_start:
                    body_fever += (fever_end_idx - body_start)

            current_idx = fever_end_idx
            sec += 1

        body_len = ti.max(total_notes - head_len, 0)
        body_normal: ti.i32 = ti.max(body_len - body_fever, 0)

        budget: ti.i32 = total_budget - ft_gems - ff_gems
        if budget < 0:
            continue

        p_val: ti.i32 = base_p_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_p_ft) + (
            ff_gems * GEM_STAT_TO_ELEMENT * is_p_ff
        )
        s_val: ti.i32 = base_s_val + (ft_gems * GEM_STAT_TO_ELEMENT * is_s_ft) + (
            ff_gems * GEM_STAT_TO_ELEMENT * is_s_ff
        )

        opt = _optimize_core_bits(
            budget,
            base_pp, base_cm, base_fm,
            p_val, s_val,
            is_p_pp, is_s_pp,
            is_p_cm, is_s_cm,
            is_p_fm, is_s_fm,
            is_p_ov, is_s_ov,
            m0, m1, m2, m3,
            head_len,
            body_fever, body_normal,
        )

        base_score: ti.i32 = opt[0]
        final_pp: ti.i32 = opt[1]
        final_cm: ti.i32 = opt[2]
        final_fm: ti.i32 = opt[3]
        final_p_val: ti.i32 = opt[4]
        final_s_val: ti.i32 = opt[5]
        gems_pp: ti.i32 = opt[6]
        gems_cm: ti.i32 = opt[7]
        gems_fm: ti.i32 = opt[8]
        gems_ov: ti.i32 = opt[9]

        # Penalty calculation
        pp_factor: ti.f32 = _core.lookup_ref_pp(final_pp)
        combo_mul: ti.f32 = _core.lookup_ref_cm(final_cm)
        combo_span: ti.f32 = combo_mul - 1.0

        base_value: ti.f32 = ti.cast((final_p_val * 2) + final_s_val, ti.f32) + pp_factor
        combo_value: ti.i32 = ti.cast(ti.floor(base_value * combo_mul), ti.i32)

        great_penalty_base: ti.i32 = ti.cast(
            ti.floor((ti.cast((final_p_val * 2) + final_s_val, ti.f32) * (2.0 / 3.0)) + 150.0),
            ti.i32,
        )
        great_combo_value: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * combo_mul), ti.i32)
        body_penalty: ti.i32 = ti.max(0, combo_value - great_combo_value)

        score_penalty_total: ti.i32 = 0
        fill_penalty_total: ti.i32 = 0

        for s in range(ti.min(n_sections, FG_MAX_SECTIONS)):
            fp_notes: ti.i32 = fill_notes[s]
            fill_penalty_total += fp_notes * combo_value

            forced_n: ti.i32 = forced_applied[s]
            if forced_n > 0:
                start = start_idx_vec[s] + (1 if skip_wasted[s] != 0 else 0)
                if start > total_notes:
                    start = total_notes
                for k in range(forced_n):
                    note_idx = start + k
                    if note_idx < 100:
                        scaling: ti.f32 = 1.0 + combo_span * (ti.cast(note_idx + 1, ti.f32) / 100.0)
                        perfect_val: ti.i32 = ti.cast(ti.floor(base_value * scaling), ti.i32)
                        great_val: ti.i32 = ti.cast(ti.floor(ti.cast(great_penalty_base, ti.f32) * scaling), ti.i32)
                        pen: ti.i32 = ti.max(0, perfect_val - great_val)
                        score_penalty_total += pen
                    else:
                        score_penalty_total += body_penalty

        final_score: ti.i32 = base_score - score_penalty_total
        if final_score < 0:
            final_score = 0

        # Atomic max: update (genome, ftff) slot if this config is better
        old_score = ti.atomic_max(fg_stage1_final_score[g, ftff_idx], final_score)
        if final_score > old_score:
            # We won the race - update other fields
            # Note: This is a benign race - all threads writing the same winning config
            # will write the same values, giving correct final result
            fg_stage1_base_score[g, ftff_idx] = base_score
            fg_stage1_cfg_idx[g, ftff_idx] = cfg_offset + cfg_idx
            fg_stage1_g_pp[g, ftff_idx] = gems_pp
            fg_stage1_g_cm[g, ftff_idx] = gems_cm
            fg_stage1_g_fm[g, ftff_idx] = gems_fm
            fg_stage1_g_ov[g, ftff_idx] = gems_ov
            fg_stage1_score_penalty[g, ftff_idx] = score_penalty_total
            fg_stage1_fill_penalty[g, ftff_idx] = fill_penalty_total







