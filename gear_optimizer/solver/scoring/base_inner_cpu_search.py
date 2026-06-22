"""Canonical CPU (numba) EXHAUSTIVE base/meta gem-allocation search.

This is the base/meta twin of the FG CPU search
(`taichi_gem/force_greats/response_inner_cpu_search.resolve_fg_response_groups_native_f64`).

WHY THIS EXISTS
---------------
The base/meta leaderboard's gem allocation is optimized offline by an exhaustive GPU search on
f64-capable hardware (AMD RX 7900 XTX). On the macOS serving host (MoltenVK) the GPU cannot run
that search exactly, and the on-demand GPU re-solve UNDERPERFORMS the inherited (already-feasible)
gems: an exhaustive search can never score below a feasible allocation, so a sub-inherited resolve
is proof the Mac GPU path is not finding the optimum. The CPU production path
(`scoring/fever_solver.solve_best_fever_combination`, `not use_gpu` branch) enumerates every FT/FF
fever timeline exactly, but its INNER PP/CM/FM/OV allocation is the GREEDY 8-step-lookahead
`optimize_core_jit` (`scoring_core.py`), which is not guaranteed optimal.

This module replaces ONLY that inner allocation with an EXHAUSTIVE enumeration: for each FT/FF
timeline (with its remaining gem budget R) it enumerates ALL (g_pp, g_cm, g_fm, g_ov) gem-count
allocations that sum to R, computes the resulting stats EXACTLY as `optimize_core_jit` applies them
per gem (GEM_SCALE_NORMAL/FEVER stat steps, GEM_STAT_TO_ELEMENT_SCALE / ELEMENTAL_GEM_SCALE element
contributions, MAX_STAT_INDEX caps, the `allow_pp` gate), scores each EXACTLY with the same
`fast_calculate_score` formula the greedy and final-scoring paths use (float32, same op order), and
keeps the global argmax over (FT, FF, g_pp, g_cm, g_fm, g_ov). Exhaustive => exact by construction,
so the resolved score is provably >= the greedy score and >= any feasible inherited allocation.

This mirrors the FG precedent (CPU exactness where the Mac GPU cannot be exact); the offline GA keeps
the GPU kernels on f64-capable hardware. This is a parallel reference/parity path, NOT a production
serving fallback: it is wired into the lossless-exact measure harness and validated against the
greedy path; production serving integration is a separate step.

EXACTNESS NOTES
---------------
- Per-gem stat effects replicate `optimize_core_jit` exactly. A stat lane (pp/cm/fm) accepts gems
  only while its current stat index is < MAX_STAT_INDEX; the final gem of a lane may push the stat
  index to/past MAX_STAT_INDEX (the greedy does not clamp the stat, only stops adding), and the
  reference lookup clamps the index. `max_*_gems = ceil((MAX_STAT_INDEX - cur)/scale)` reproduces
  that bound. cm/pp use GEM_SCALE_NORMAL, fm uses GEM_SCALE_FEVER.
- `allow_pp = (is_p_pp>0) or (is_s_pp>0)`: when false, PP gems are never spent (g_pp==0), identical
  to the greedy's PP gate; the leftover goes to overflow.
- The score is `fast_calculate_score(base, c_mul, f_mul, head, body_fever, body_normal)` with
  `base = float32((p*2)+s) + ref_pp[clamp(pp_stat)]`, all float32, head ramp in the same order. This
  is the exact value the greedy compares internally AND the value the final scoring reports, so the
  exhaustive max dominates the greedy choice bit-for-bit.

SOUND PRUNING
-------------
The only reduction applied is bounding the pp/cm/fm loops by their feasible cap (`max_*_gems`) and
letting overflow absorb the remaining budget. This never drops a potentially-optimal allocation:
gems beyond a lane's cap are infeasible (the greedy could not spend them either), and every
remaining-budget split between a capped lane and overflow is still enumerated. No heuristic caps.
"""
import numpy as np

from ...core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_ROWS,
)
from ...core.jit_setup import jit


@jit(nopython=True, cache=True)
def _ref_f32(ref, idx):
    """float32 reference lookup with the same clamp as lookup_reference_py / fast paths."""
    s = idx
    if s < 0:
        s = 0
    if s > TOTAL_ROWS:
        s = TOTAL_ROWS
    return np.float32(ref[s])


@jit(nopython=True, cache=True)
def _score_combo_f32(base_value, combo_mul, fever_mul, fever_mask_head, count_body_fever,
                     count_body_normal):
    """Bit-for-bit transcription of scoring_core.fast_calculate_score (float32, same op order)."""
    base_f = np.float32(base_value)
    combo_mul_f = np.float32(combo_mul)
    fever_mul_f = np.float32(fever_mul)

    combo_val_per_note = int(base_f * combo_mul_f)
    fever_val_per_note = int(base_f * combo_mul_f * fever_mul_f)

    body_score = (count_body_fever * fever_val_per_note) + (count_body_normal * combo_val_per_note)

    factor = (combo_mul_f - np.float32(1.0)) * base_f / np.float32(100.0)
    total_head = 0
    n_head = fever_mask_head.shape[0]
    for i in range(n_head):
        current_ramp_val = base_f + (np.float32(i + 1) * factor)
        if fever_mask_head[i]:
            val = int(current_ramp_val * fever_mul_f)
        else:
            val = int(current_ramp_val)
        total_head += val

    return int(body_score + total_head)


@jit(nopython=True, cache=True)
def _max_gems_for_lane(cur_stat, scale):
    """Feasible gem count for a capped lane: gems are added only while stat < MAX_STAT_INDEX."""
    if cur_stat >= MAX_STAT_INDEX:
        return 0
    rem = MAX_STAT_INDEX - cur_stat
    n = rem // scale
    if rem % scale != 0:
        n += 1
    return n


@jit(nopython=True, cache=True)
def resolve_base_combo_exhaustive(
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
    ref_pp,
    ref_cm,
    ref_fm,
    fever_mask_head,
    count_body_fever,
    count_body_normal,
):
    """Exhaustively search all (g_pp,g_cm,g_fm,g_ov) splits of `budget` for ONE FT/FF timeline.

    Replicates optimize_core_jit's per-gem stat math and fast_calculate_score's scoring exactly,
    then returns the argmax. Tie-break mirrors the greedy's "prefer overflow on ties" intent
    (larger g_ov wins ties), but ties never change the SCORE, which is what the gate checks.

    Returns (best_score, g_pp, g_cm, g_fm, g_ov, final_pp, final_cm, final_fm,
             final_p_val, final_s_val).
    """
    allow_pp = (is_p_pp > 0) or (is_s_pp > 0)

    max_cm_gems = _max_gems_for_lane(cur_cm, GEM_SCALE_NORMAL)
    max_fm_gems = _max_gems_for_lane(cur_fm, GEM_SCALE_FEVER)
    max_pp_gems = 0
    if allow_pp:
        max_pp_gems = _max_gems_for_lane(cur_pp, GEM_SCALE_NORMAL)
    if max_cm_gems > budget:
        max_cm_gems = budget
    if max_fm_gems > budget:
        max_fm_gems = budget
    if max_pp_gems > budget:
        max_pp_gems = budget

    # Per-gem element-lane deltas (match optimize_core_jit's apply step).
    pp_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_pp
    pp_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_pp
    cm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_cm
    cm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_cm
    fm_p_delta = GEM_STAT_TO_ELEMENT_SCALE * is_p_fm
    fm_s_delta = GEM_STAT_TO_ELEMENT_SCALE * is_s_fm
    ov_p_delta = ELEMENTAL_GEM_SCALE * is_p_ov
    ov_s_delta = ELEMENTAL_GEM_SCALE * is_s_ov

    # Default winner: all overflow (matches greedy's OV-wins-ties seed).
    best_g_ov = budget
    best_g_pp = 0
    best_g_cm = 0
    best_g_fm = 0
    best_final_pp = cur_pp
    best_final_cm = cur_cm
    best_final_fm = cur_fm
    best_final_p = cur_p_val + best_g_ov * ov_p_delta
    best_final_s = cur_s_val + best_g_ov * ov_s_delta
    pp_factor0 = _ref_f32(ref_pp, cur_pp)
    cm_mul0 = _ref_f32(ref_cm, cur_cm)
    fm_mul0 = _ref_f32(ref_fm, cur_fm)
    base0 = np.float32(np.float32((best_final_p * 2) + best_final_s) + pp_factor0)
    best_score = _score_combo_f32(base0, cm_mul0, fm_mul0, fever_mask_head,
                                  count_body_fever, count_body_normal)

    g_cm = 0
    while g_cm <= max_cm_gems:
        leftover_after_cm = budget - g_cm
        cm_stat = cur_cm + g_cm * GEM_SCALE_NORMAL
        cm_mul = _ref_f32(ref_cm, cm_stat)
        cm_p = cur_p_val + g_cm * cm_p_delta
        cm_s = cur_s_val + g_cm * cm_s_delta

        g_fm_max = max_fm_gems
        if g_fm_max > leftover_after_cm:
            g_fm_max = leftover_after_cm
        g_fm = 0
        while g_fm <= g_fm_max:
            leftover_after_fm = leftover_after_cm - g_fm
            fm_stat = cur_fm + g_fm * GEM_SCALE_FEVER
            fm_mul = _ref_f32(ref_fm, fm_stat)
            base_p = cm_p + g_fm * fm_p_delta
            base_s = cm_s + g_fm * fm_s_delta

            g_pp_max = max_pp_gems
            if g_pp_max > leftover_after_fm:
                g_pp_max = leftover_after_fm

            g_pp = 0
            while g_pp <= g_pp_max:
                g_ov = leftover_after_fm - g_pp
                pp_stat = cur_pp + g_pp * GEM_SCALE_NORMAL
                pp_factor = _ref_f32(ref_pp, pp_stat)
                p_val = base_p + g_pp * pp_p_delta + g_ov * ov_p_delta
                s_val = base_s + g_pp * pp_s_delta + g_ov * ov_s_delta
                base = np.float32(np.float32((p_val * 2) + s_val) + pp_factor)
                score = _score_combo_f32(base, cm_mul, fm_mul, fever_mask_head,
                                         count_body_fever, count_body_normal)
                # Strict-improve, else tie-break preferring larger overflow (greedy intent).
                if score > best_score or (score == best_score and g_ov > best_g_ov):
                    best_score = score
                    best_g_pp = g_pp
                    best_g_cm = g_cm
                    best_g_fm = g_fm
                    best_g_ov = g_ov
                    best_final_pp = pp_stat
                    best_final_cm = cm_stat
                    best_final_fm = fm_stat
                    best_final_p = p_val
                    best_final_s = s_val
                g_pp += 1
            g_fm += 1
        g_cm += 1

    return (best_score, best_g_pp, best_g_cm, best_g_fm, best_g_ov,
            best_final_pp, best_final_cm, best_final_fm, best_final_p, best_final_s)


@jit(nopython=True, cache=True)
def resolve_base_loadout_exhaustive(
    timeline_budgets,
    timeline_pvals,
    timeline_svals,
    timeline_head_offsets,
    timeline_head_lengths,
    timeline_body_fever,
    timeline_body_normal,
    head_mask_flat,
    cur_pp,
    cur_cm,
    cur_fm,
    is_p_pp,
    is_s_pp,
    is_p_cm,
    is_s_cm,
    is_p_fm,
    is_s_fm,
    is_p_ov,
    is_s_ov,
    ref_pp,
    ref_cm,
    ref_fm,
):
    """Exhaustive base gem search over ALL FT/FF timelines for one loadout; global argmax.

    Inputs are the flattened precomputed-timeline arrays (one row per FT/FF combo). `cur_pp/cm/fm`
    are the base (pre-PP/CM/FM-gem) stat indices, shared across timelines (FT/FF gems do not touch
    them). `timeline_pvals/svals` are the primary/secondary element values AFTER FT/FF gem
    contributions for that combo (exactly the `cur_p_val/cur_s_val` the CPU path feeds into
    optimize_core_jit). Head masks are concatenated into `head_mask_flat` (bool) and sliced by
    offset/length.

    Returns out[10] (int64): [best_score, best_ti, g_pp, g_cm, g_fm, g_ov,
                              final_pp, final_cm, final_fm, dummy]. (final p/s recomputed by caller
    via apply_gems for parity with the production result builder.)
    """
    n_tl = timeline_budgets.shape[0]
    out = np.zeros(10, dtype=np.int64)
    best_score = -1
    best_ti = 0
    best_g_pp = 0
    best_g_cm = 0
    best_g_fm = 0
    best_g_ov = 0
    best_final_pp = cur_pp
    best_final_cm = cur_cm
    best_final_fm = cur_fm

    for ti in range(n_tl):
        budget = int(timeline_budgets[ti])
        cur_p_val = int(timeline_pvals[ti])
        cur_s_val = int(timeline_svals[ti])
        h_off = int(timeline_head_offsets[ti])
        h_len = int(timeline_head_lengths[ti])
        head = head_mask_flat[h_off:h_off + h_len]
        body_fever = int(timeline_body_fever[ti])
        body_normal = int(timeline_body_normal[ti])

        (score, g_pp, g_cm, g_fm, g_ov,
         final_pp, final_cm, final_fm, _fp, _fs) = resolve_base_combo_exhaustive(
            budget, cur_pp, cur_cm, cur_fm, cur_p_val, cur_s_val,
            is_p_pp, is_s_pp, is_p_cm, is_s_cm, is_p_fm, is_s_fm, is_p_ov, is_s_ov,
            ref_pp, ref_cm, ref_fm, head, body_fever, body_normal)

        if score > best_score:
            best_score = score
            best_ti = ti
            best_g_pp = g_pp
            best_g_cm = g_cm
            best_g_fm = g_fm
            best_g_ov = g_ov
            best_final_pp = final_pp
            best_final_cm = final_cm
            best_final_fm = final_fm

    out[0] = best_score
    out[1] = best_ti
    out[2] = best_g_pp
    out[3] = best_g_cm
    out[4] = best_g_fm
    out[5] = best_g_ov
    out[6] = best_final_pp
    out[7] = best_final_cm
    out[8] = best_final_fm
    return out
