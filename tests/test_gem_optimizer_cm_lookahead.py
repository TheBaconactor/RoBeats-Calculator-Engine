from __future__ import annotations

import numpy as np

from gear_optimizer.solver.scoring.scoring_core import optimize_core_jit


def test_optimize_core_jit_cm_lookahead_breaks_plateau_trap() -> None:
    """
    Regression guard: CM multipliers are lookup-table based, so the first CM gem can be
    "invisible" (no improvement) until we cross a breakpoint. The greedy allocator must
    be able to invest in CM across a short plateau window.
    """
    # Breakpoint: CM multiplier stays at 1.0 until stat >= 6, then jumps to 2.0.
    # With GEM_SCALE_NORMAL=2, this requires 3 CM gems before any improvement is observed.
    ref_pp = np.zeros((161,), dtype=np.float32)
    ref_cm = np.ones((161,), dtype=np.float32)
    ref_cm[:6] = 1.0
    ref_cm[6:] = 2.0
    ref_fm = np.ones((161,), dtype=np.float32)

    fever_mask_head = np.zeros((0,), dtype=np.bool_)
    count_body_fever = 0
    count_body_normal = 250_000

    budget = 10
    cur_pp = 0
    cur_cm = 0
    cur_fm = 0
    cur_p_val = 0
    cur_s_val = 0

    # Only OV contributes to base_value; CM only affects the multiplier (no element delta),
    # so the naive 1-step greedy will never pick CM without lookahead.
    is_p_pp = 0
    is_s_pp = 0
    is_p_cm = 0
    is_s_cm = 0
    is_p_fm = 0
    is_s_fm = 0
    is_p_ov = 1
    is_s_ov = 0

    GEM_SCALE_NORMAL = 2
    GEM_SCALE_FEVER = 3
    GEM_STAT_TO_ELEMENT_SCALE = 3
    ELEMENTAL_GEM_SCALE = 6
    TOTAL_ROWS = 160
    MAX_STAT_INDEX = 160

    (
        _pp,
        _cm,
        _fm,
        _p_val,
        _s_val,
        _g_pp,
        g_cm,
        _g_fm,
        _g_ov,
    ) = optimize_core_jit(
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
        GEM_SCALE_NORMAL,
        GEM_SCALE_FEVER,
        GEM_STAT_TO_ELEMENT_SCALE,
        ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS,
        MAX_STAT_INDEX,
    )

    assert int(g_cm) >= 3, "CM lookahead failed to cross the breakpoint plateau"
