from __future__ import annotations

from math import floor

import numpy as np


def _score_exact(
    *,
    base_value: float,
    combo_mul: float,
    fever_mul: float,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    combo_val = floor(float(base_value) * float(combo_mul))
    fever_val = floor(float(base_value) * float(combo_mul) * float(fever_mul))
    body = (int(count_body_fever) * fever_val) + (int(count_body_normal) * combo_val)
    factor = (float(combo_mul) - 1.0) * float(base_value) / 100.0
    head = 0
    for idx, is_fever in enumerate(np.asarray(fever_mask_head, dtype=np.bool_).tolist(), start=1):
        ramp = float(base_value) + (float(idx) * factor)
        head += floor(ramp * float(fever_mul)) if bool(is_fever) else floor(ramp)
    return int(body + head)


def _relaxed_response_ub(
    *,
    budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    flags: dict[str, int],
    ref_pp: np.ndarray,
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    head_len: int,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    w_pp = 6 * int(flags["is_p_pp"]) + 3 * int(flags["is_s_pp"])
    w_cm = 6 * int(flags["is_p_cm"]) + 3 * int(flags["is_s_cm"])
    w_fm = 6 * int(flags["is_p_fm"]) + 3 * int(flags["is_s_fm"])
    w_ov = 12 * int(flags["is_p_ov"]) + 6 * int(flags["is_s_ov"])
    w_max = max(w_pp, w_cm, w_fm, w_ov)

    pp_stat = min(160, max(0, int(cur_pp) + (2 * int(budget))))
    cm_stat = min(160, max(0, int(cur_cm) + (2 * int(budget))))
    fm_stat = min(160, max(0, int(cur_fm) + (3 * int(budget))))
    base_lane = (int(cur_p_val) * 2) + int(cur_s_val) + (int(budget) * int(w_max))
    head_all_fever = np.ones(int(head_len), dtype=np.bool_)
    return _score_exact(
        base_value=float(base_lane) + float(ref_pp[pp_stat]),
        combo_mul=float(ref_cm[cm_stat]),
        fever_mul=float(ref_fm[fm_stat]),
        fever_mask_head=head_all_fever,
        count_body_fever=int(count_body_fever) + int(count_body_normal),
        count_body_normal=0,
    )


def _pp_ov_prefix_best(*, cur_pp: int, max_pp_gems: int, delta_pp_vs_ov: int, ref_pp: np.ndarray) -> float:
    best = float(ref_pp[min(160, max(0, cur_pp))])
    for g_pp in range(1, max(0, int(max_pp_gems)) + 1):
        pp_stat = min(160, max(0, int(cur_pp) + (2 * g_pp)))
        best = max(best, float(g_pp * int(delta_pp_vs_ov)) + float(ref_pp[pp_stat]))
    return best


def _cmfm_rectangle_score_ub(
    *,
    budget: int,
    cm0: int,
    cm1: int,
    fm0: int,
    fm1: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    flags: dict[str, int],
    ref_pp: np.ndarray,
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    w_pp = 6 * int(flags["is_p_pp"]) + 3 * int(flags["is_s_pp"])
    w_cm = 6 * int(flags["is_p_cm"]) + 3 * int(flags["is_s_cm"])
    w_fm = 6 * int(flags["is_p_fm"]) + 3 * int(flags["is_s_fm"])
    w_ov = 12 * int(flags["is_p_ov"]) + 6 * int(flags["is_s_ov"])
    base_init = (int(cur_p_val) * 2) + int(cur_s_val)

    max_leftover = int(budget) - int(cm0) - int(fm0)
    max_pp_gems = min(int(budget), max(0, (160 - int(cur_pp) + 1) // 2), max_leftover)
    pp_extra = _pp_ov_prefix_best(
        cur_pp=cur_pp,
        max_pp_gems=max_pp_gems,
        delta_pp_vs_ov=w_pp - w_ov,
        ref_pp=ref_pp,
    )

    cm_base_gems = int(cm1) if w_cm >= w_ov else int(cm0)
    fm_base_gems = int(fm1) if w_fm >= w_ov else int(fm0)
    base_linear = base_init + (int(budget) * w_ov) + (cm_base_gems * (w_cm - w_ov)) + (
        fm_base_gems * (w_fm - w_ov)
    )

    return _score_exact(
        base_value=float(base_linear) + float(pp_extra),
        combo_mul=float(ref_cm[min(160, int(cur_cm) + (2 * int(cm1)))]),
        fever_mul=float(ref_fm[min(160, int(cur_fm) + (3 * int(fm1)))]),
        fever_mask_head=fever_mask_head,
        count_body_fever=count_body_fever,
        count_body_normal=count_body_normal,
    )


def test_relaxed_response_upper_bound_covers_all_non_timing_allocations():
    ref_pp = np.linspace(0.0, 2500.0, 161, dtype=np.float64)
    ref_cm = np.linspace(1.0, 3.25, 161, dtype=np.float64)
    ref_fm = np.linspace(1.0, 4.5, 161, dtype=np.float64)
    flags = {
        "is_p_pp": 0,
        "is_s_pp": 1,
        "is_p_cm": 0,
        "is_s_cm": 0,
        "is_p_fm": 1,
        "is_s_fm": 0,
        "is_p_ov": 1,
        "is_s_ov": 0,
    }
    fever_mask_head = np.asarray([False, True, False, True, True, False, False, True], dtype=np.bool_)
    budget = 12
    cur_pp = 109
    cur_cm = 96
    cur_fm = 101
    cur_p_val = 345
    cur_s_val = 191
    count_body_fever = 73
    count_body_normal = 41

    ub = _relaxed_response_ub(
        budget=budget,
        cur_pp=cur_pp,
        cur_cm=cur_cm,
        cur_fm=cur_fm,
        cur_p_val=cur_p_val,
        cur_s_val=cur_s_val,
        flags=flags,
        ref_pp=ref_pp,
        ref_cm=ref_cm,
        ref_fm=ref_fm,
        head_len=int(fever_mask_head.shape[0]),
        count_body_fever=count_body_fever,
        count_body_normal=count_body_normal,
    )

    best = -1
    for g_pp in range(budget + 1):
        for g_cm in range(budget - g_pp + 1):
            for g_fm in range(budget - g_pp - g_cm + 1):
                g_ov = budget - g_pp - g_cm - g_fm
                pp_stat = min(160, cur_pp + (2 * g_pp))
                cm_stat = min(160, cur_cm + (2 * g_cm))
                fm_stat = min(160, cur_fm + (3 * g_fm))
                p_val = cur_p_val + (3 * g_fm * flags["is_p_fm"]) + (6 * g_ov * flags["is_p_ov"])
                s_val = cur_s_val + (3 * g_pp * flags["is_s_pp"])
                base_value = float((p_val * 2) + s_val) + float(ref_pp[pp_stat])
                score = _score_exact(
                    base_value=base_value,
                    combo_mul=float(ref_cm[cm_stat]),
                    fever_mul=float(ref_fm[fm_stat]),
                    fever_mask_head=fever_mask_head,
                    count_body_fever=count_body_fever,
                    count_body_normal=count_body_normal,
                )
                best = max(best, score)

    assert best <= ub


def test_cmfm_rectangle_upper_bound_covers_all_cells_in_block():
    ref_pp = np.linspace(0.0, 1800.0, 161, dtype=np.float64)
    ref_cm = np.linspace(1.0, 4.0, 161, dtype=np.float64)
    ref_fm = np.linspace(1.0, 5.0, 161, dtype=np.float64)
    fever_mask_head = np.asarray([False, True, True, False, True, False, False, True, True], dtype=np.bool_)
    common = {
        "budget": 17,
        "cur_pp": 91,
        "cur_cm": 88,
        "cur_fm": 84,
        "cur_p_val": 317,
        "cur_s_val": 205,
        "ref_pp": ref_pp,
        "ref_cm": ref_cm,
        "ref_fm": ref_fm,
        "fever_mask_head": fever_mask_head,
        "count_body_fever": 61,
        "count_body_normal": 47,
    }
    cases = [
        (
            {"is_p_pp": 0, "is_s_pp": 1, "is_p_cm": 1, "is_s_cm": 0, "is_p_fm": 0, "is_s_fm": 0, "is_p_ov": 0, "is_s_ov": 1},
            (3, 6, 4, 11),
        ),
        (
            {"is_p_pp": 1, "is_s_pp": 0, "is_p_cm": 0, "is_s_cm": 0, "is_p_fm": 0, "is_s_fm": 1, "is_p_ov": 1, "is_s_ov": 0},
            (4, 7, 2, 9),
        ),
    ]

    for flags, block in cases:
        cm0, cm1, fm0, fm1 = block
        ub = _cmfm_rectangle_score_ub(flags=flags, cm0=cm0, cm1=cm1, fm0=fm0, fm1=fm1, **common)
        best = -1
        w_pp = 6 * flags["is_p_pp"] + 3 * flags["is_s_pp"]
        w_cm = 6 * flags["is_p_cm"] + 3 * flags["is_s_cm"]
        w_fm = 6 * flags["is_p_fm"] + 3 * flags["is_s_fm"]
        w_ov = 12 * flags["is_p_ov"] + 6 * flags["is_s_ov"]
        base_init = (common["cur_p_val"] * 2) + common["cur_s_val"]

        for g_cm in range(cm0, cm1 + 1):
            for g_fm in range(fm0, fm1 + 1):
                leftover = common["budget"] - g_cm - g_fm
                if leftover < 0:
                    continue
                for g_pp in range(leftover + 1):
                    g_ov = leftover - g_pp
                    pp_stat = min(160, common["cur_pp"] + (2 * g_pp))
                    cm_stat = min(160, common["cur_cm"] + (2 * g_cm))
                    fm_stat = min(160, common["cur_fm"] + (3 * g_fm))
                    base_value = (
                        base_init
                        + (g_cm * w_cm)
                        + (g_fm * w_fm)
                        + (g_pp * w_pp)
                        + (g_ov * w_ov)
                        + float(ref_pp[pp_stat])
                    )
                    score = _score_exact(
                        base_value=base_value,
                        combo_mul=float(ref_cm[cm_stat]),
                        fever_mul=float(ref_fm[fm_stat]),
                        fever_mask_head=fever_mask_head,
                        count_body_fever=common["count_body_fever"],
                        count_body_normal=common["count_body_normal"],
                    )
                    best = max(best, score)

        assert best <= ub
