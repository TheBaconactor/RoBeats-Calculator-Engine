import numpy as np

from gear_optimizer.core.constants import (
    ELEMENTAL_GEM_SCALE,
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    MAX_STAT_INDEX,
    TOTAL_ROWS,
)
from gear_optimizer.solver.scoring_core import (
    fast_calculate_score,
    lookup_reference_py,
    optimize_core_exact_bounded_jit,
    optimize_core_jit,
    semi_exact_upper_bound_jit,
)


def _cm_cap(cur_cm: int, is_p_cm: int, is_s_cm: int, budget: int) -> int:
    allow_cm_color = int(is_p_cm) != 0 or int(is_s_cm) != 0
    if int(cur_cm) >= int(MAX_STAT_INDEX):
        out = 0
    elif allow_cm_color:
        rem = int(MAX_STAT_INDEX) - int(cur_cm)
        out = (rem + int(GEM_SCALE_NORMAL) - 1) // int(GEM_SCALE_NORMAL)
    elif int(cur_cm) > 50:
        out = 0
    else:
        out = ((50 - int(cur_cm)) // int(GEM_SCALE_NORMAL)) + 1
    return max(0, min(int(budget), int(out)))


def _pp_cap(cur_pp: int, is_p_pp: int, is_s_pp: int, budget: int) -> int:
    allow_pp = int(is_p_pp) != 0 or int(is_s_pp) != 0
    if not allow_pp or int(cur_pp) >= int(MAX_STAT_INDEX):
        return 0
    rem = int(MAX_STAT_INDEX) - int(cur_pp)
    out = (rem + int(GEM_SCALE_NORMAL) - 1) // int(GEM_SCALE_NORMAL)
    return max(0, min(int(budget), int(out)))


def _fm_cap(cur_fm: int, budget: int) -> int:
    if int(cur_fm) >= int(MAX_STAT_INDEX):
        return 0
    rem = int(MAX_STAT_INDEX) - int(cur_fm)
    out = (rem + int(GEM_SCALE_FEVER) - 1) // int(GEM_SCALE_FEVER)
    return max(0, min(int(budget), int(out)))


def _score_from_alloc(
    *,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    g_pp: int,
    g_cm: int,
    g_fm: int,
    g_ov: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_pp: np.ndarray,
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
) -> int:
    pp_stat = int(cur_pp) + int(g_pp) * int(GEM_SCALE_NORMAL)
    cm_stat = int(cur_cm) + int(g_cm) * int(GEM_SCALE_NORMAL)
    fm_stat = int(cur_fm) + int(g_fm) * int(GEM_SCALE_FEVER)
    p_val = (
        int(cur_p_val)
        + int(g_pp) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_p_pp)
        + int(g_cm) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_p_cm)
        + int(g_fm) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_p_fm)
        + int(g_ov) * int(ELEMENTAL_GEM_SCALE) * int(is_p_ov)
    )
    s_val = (
        int(cur_s_val)
        + int(g_pp) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_s_pp)
        + int(g_cm) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_s_cm)
        + int(g_fm) * int(GEM_STAT_TO_ELEMENT_SCALE) * int(is_s_fm)
        + int(g_ov) * int(ELEMENTAL_GEM_SCALE) * int(is_s_ov)
    )
    base = np.float32((p_val * 2) + s_val) + np.float32(lookup_reference_py(pp_stat, ref_pp, TOTAL_ROWS))
    c_mul = np.float32(lookup_reference_py(cm_stat, ref_cm, TOTAL_ROWS))
    f_mul = np.float32(lookup_reference_py(fm_stat, ref_fm, TOTAL_ROWS))
    return int(
        fast_calculate_score(
            base,
            c_mul,
            f_mul,
            fever_mask_head,
            int(count_body_fever),
            int(count_body_normal),
        )
    )


def _bruteforce_best(
    *,
    budget: int,
    cur_pp: int,
    cur_cm: int,
    cur_fm: int,
    cur_p_val: int,
    cur_s_val: int,
    is_p_pp: int,
    is_s_pp: int,
    is_p_cm: int,
    is_s_cm: int,
    is_p_fm: int,
    is_s_fm: int,
    is_p_ov: int,
    is_s_ov: int,
    ref_pp: np.ndarray,
    ref_cm: np.ndarray,
    ref_fm: np.ndarray,
    fever_mask_head: np.ndarray,
    count_body_fever: int,
    count_body_normal: int,
) -> tuple[int, tuple[int, int, int, int]]:
    max_pp = _pp_cap(cur_pp, is_p_pp, is_s_pp, budget)
    max_cm = _cm_cap(cur_cm, is_p_cm, is_s_cm, budget)
    max_fm = _fm_cap(cur_fm, budget)
    best_score = -1
    best_alloc = (0, 0, 0, int(budget))
    for g_cm in range(max_cm + 1):
        for g_fm in range(min(max_fm, budget - g_cm) + 1):
            rem = int(budget) - int(g_cm) - int(g_fm)
            if rem < 0:
                continue
            for g_pp in range(min(max_pp, rem) + 1):
                g_ov = int(rem) - int(g_pp)
                score = _score_from_alloc(
                    cur_pp=cur_pp,
                    cur_cm=cur_cm,
                    cur_fm=cur_fm,
                    cur_p_val=cur_p_val,
                    cur_s_val=cur_s_val,
                    g_pp=g_pp,
                    g_cm=g_cm,
                    g_fm=g_fm,
                    g_ov=g_ov,
                    is_p_pp=is_p_pp,
                    is_s_pp=is_s_pp,
                    is_p_cm=is_p_cm,
                    is_s_cm=is_s_cm,
                    is_p_fm=is_p_fm,
                    is_s_fm=is_s_fm,
                    is_p_ov=is_p_ov,
                    is_s_ov=is_s_ov,
                    ref_pp=ref_pp,
                    ref_cm=ref_cm,
                    ref_fm=ref_fm,
                    fever_mask_head=fever_mask_head,
                    count_body_fever=count_body_fever,
                    count_body_normal=count_body_normal,
                )
                if score > best_score:
                    best_score = int(score)
                    best_alloc = (int(g_pp), int(g_cm), int(g_fm), int(g_ov))
    return best_score, best_alloc


def test_optimize_core_exact_bounded_matches_bruteforce_randomized():
    ref_pp = np.linspace(1.0, 2.2, TOTAL_ROWS + 1, dtype=np.float32)
    ref_cm = np.linspace(1.0, 3.1, TOTAL_ROWS + 1, dtype=np.float32)
    ref_fm = np.linspace(1.0, 4.6, TOTAL_ROWS + 1, dtype=np.float32)

    for seed in range(6):
        rng = np.random.default_rng(20260408 + seed)
        budget = int(rng.integers(6, 13))
        cur_pp = int(rng.integers(0, 151))
        cur_cm = int(rng.integers(0, 151))
        cur_fm = int(rng.integers(0, 151))
        cur_p_val = int(rng.integers(40, 260))
        cur_s_val = int(rng.integers(20, 180))
        flags = [int(v) for v in rng.integers(0, 2, size=8)]
        fever_mask_head = np.asarray(rng.integers(0, 2, size=40), dtype=np.bool_)
        count_body_fever = int(rng.integers(0, 80))
        count_body_normal = int(rng.integers(0, 80))

        exact = optimize_core_exact_bounded_jit(
            budget,
            cur_pp,
            cur_cm,
            cur_fm,
            cur_p_val,
            cur_s_val,
            flags[0],
            flags[1],
            flags[2],
            flags[3],
            flags[4],
            flags[5],
            flags[6],
            flags[7],
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
        exact_score = _score_from_alloc(
            cur_pp=cur_pp,
            cur_cm=cur_cm,
            cur_fm=cur_fm,
            cur_p_val=cur_p_val,
            cur_s_val=cur_s_val,
            g_pp=int(exact[5]),
            g_cm=int(exact[6]),
            g_fm=int(exact[7]),
            g_ov=int(exact[8]),
            is_p_pp=flags[0],
            is_s_pp=flags[1],
            is_p_cm=flags[2],
            is_s_cm=flags[3],
            is_p_fm=flags[4],
            is_s_fm=flags[5],
            is_p_ov=flags[6],
            is_s_ov=flags[7],
            ref_pp=ref_pp,
            ref_cm=ref_cm,
            ref_fm=ref_fm,
            fever_mask_head=fever_mask_head,
            count_body_fever=count_body_fever,
            count_body_normal=count_body_normal,
        )
        brute_score, _ = _bruteforce_best(
            budget=budget,
            cur_pp=cur_pp,
            cur_cm=cur_cm,
            cur_fm=cur_fm,
            cur_p_val=cur_p_val,
            cur_s_val=cur_s_val,
            is_p_pp=flags[0],
            is_s_pp=flags[1],
            is_p_cm=flags[2],
            is_s_cm=flags[3],
            is_p_fm=flags[4],
            is_s_fm=flags[5],
            is_p_ov=flags[6],
            is_s_ov=flags[7],
            ref_pp=ref_pp,
            ref_cm=ref_cm,
            ref_fm=ref_fm,
            fever_mask_head=fever_mask_head,
            count_body_fever=count_body_fever,
            count_body_normal=count_body_normal,
        )
        assert exact_score == brute_score


def test_optimize_core_exact_bounded_never_worse_than_greedy():
    ref_pp = np.linspace(1.0, 2.0, TOTAL_ROWS + 1, dtype=np.float32)
    ref_cm = np.linspace(1.0, 3.0, TOTAL_ROWS + 1, dtype=np.float32)
    ref_fm = np.linspace(1.0, 5.0, TOTAL_ROWS + 1, dtype=np.float32)
    rng = np.random.default_rng(20260408)

    for _ in range(10):
        budget = int(rng.integers(8, 16))
        cur_pp = int(rng.integers(0, 151))
        cur_cm = int(rng.integers(0, 151))
        cur_fm = int(rng.integers(0, 151))
        cur_p_val = int(rng.integers(60, 300))
        cur_s_val = int(rng.integers(30, 220))
        flags = [int(v) for v in rng.integers(0, 2, size=8)]
        fever_mask_head = np.asarray(rng.integers(0, 2, size=50), dtype=np.bool_)
        count_body_fever = int(rng.integers(0, 120))
        count_body_normal = int(rng.integers(0, 120))

        greedy = optimize_core_jit(
            budget,
            cur_pp,
            cur_cm,
            cur_fm,
            cur_p_val,
            cur_s_val,
            flags[0],
            flags[1],
            flags[2],
            flags[3],
            flags[4],
            flags[5],
            flags[6],
            flags[7],
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
        greedy_score = _score_from_alloc(
            cur_pp=cur_pp,
            cur_cm=cur_cm,
            cur_fm=cur_fm,
            cur_p_val=cur_p_val,
            cur_s_val=cur_s_val,
            g_pp=int(greedy[5]),
            g_cm=int(greedy[6]),
            g_fm=int(greedy[7]),
            g_ov=int(greedy[8]),
            is_p_pp=flags[0],
            is_s_pp=flags[1],
            is_p_cm=flags[2],
            is_s_cm=flags[3],
            is_p_fm=flags[4],
            is_s_fm=flags[5],
            is_p_ov=flags[6],
            is_s_ov=flags[7],
            ref_pp=ref_pp,
            ref_cm=ref_cm,
            ref_fm=ref_fm,
            fever_mask_head=fever_mask_head,
            count_body_fever=count_body_fever,
            count_body_normal=count_body_normal,
        )

        exact = optimize_core_exact_bounded_jit(
            budget,
            cur_pp,
            cur_cm,
            cur_fm,
            cur_p_val,
            cur_s_val,
            flags[0],
            flags[1],
            flags[2],
            flags[3],
            flags[4],
            flags[5],
            flags[6],
            flags[7],
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
        exact_score = _score_from_alloc(
            cur_pp=cur_pp,
            cur_cm=cur_cm,
            cur_fm=cur_fm,
            cur_p_val=cur_p_val,
            cur_s_val=cur_s_val,
            g_pp=int(exact[5]),
            g_cm=int(exact[6]),
            g_fm=int(exact[7]),
            g_ov=int(exact[8]),
            is_p_pp=flags[0],
            is_s_pp=flags[1],
            is_p_cm=flags[2],
            is_s_cm=flags[3],
            is_p_fm=flags[4],
            is_s_fm=flags[5],
            is_p_ov=flags[6],
            is_s_ov=flags[7],
            ref_pp=ref_pp,
            ref_cm=ref_cm,
            ref_fm=ref_fm,
            fever_mask_head=fever_mask_head,
            count_body_fever=count_body_fever,
            count_body_normal=count_body_normal,
        )
        assert exact_score >= greedy_score


def test_semi_exact_upper_bound_dominates_exact_score():
    ref_pp = np.linspace(1.0, 2.1, TOTAL_ROWS + 1, dtype=np.float32)
    ref_cm = np.linspace(1.0, 2.9, TOTAL_ROWS + 1, dtype=np.float32)
    ref_fm = np.linspace(1.0, 4.8, TOTAL_ROWS + 1, dtype=np.float32)
    fever_mask_head = np.asarray([0, 1, 0, 1, 1, 0, 0, 1] * 5, dtype=np.bool_)
    count_body_fever = 31
    count_body_normal = 47
    base_value = np.float32(812.5)
    combo_mul = np.float32(ref_cm[73])
    fever_mul = np.float32(ref_fm[64])
    n_hn = int((~fever_mask_head).sum())
    n_hf = int(fever_mask_head.sum())
    sigma_hn = int(sum(i + 1 for i, v in enumerate(fever_mask_head) if not v))
    sigma_hf = int(sum(i + 1 for i, v in enumerate(fever_mask_head) if v))

    exact = int(
        fast_calculate_score(
            base_value,
            combo_mul,
            fever_mul,
            fever_mask_head,
            count_body_fever,
            count_body_normal,
        )
    )
    ub = float(
        semi_exact_upper_bound_jit(
            base_value,
            combo_mul,
            fever_mul,
            count_body_fever,
            count_body_normal,
            n_hn,
            n_hf,
            sigma_hn,
            sigma_hf,
        )
    )
    assert ub >= float(exact)
