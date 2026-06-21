"""Parity / soundness gate for the EXHAUSTIVE base/meta CPU gem-search
(`scoring/base_inner_cpu_search.resolve_base_combo_exhaustive`).

The exhaustive search replaces the greedy inner allocation (`scoring_core.optimize_core_jit`) used by
the CPU base path (`scoring/fever_solver.solve_best_fever_combination`, `not use_gpu` branch). Because
it enumerates every feasible (pp,cm,fm,ov) split and scores each with the SAME `fast_calculate_score`,
its result must satisfy, for every input:

  exhaustive_score >= greedy_score        (exhaustive dominates: it can always replay greedy's split)

and the exhaustive score must EQUAL the score of its own returned gem split when re-scored through the
production scoring path (`fast_calculate_score`). Money-critical: a violation means a served score could
fall below the achievable optimum, so this is release-blocking. CPU-only (no GPU)."""
import numpy as np

from gear_optimizer.app_async_db import _get_team_buff_ref_arrays_cached
from gear_optimizer.core.constants import (
    GEM_SCALE_FEVER,
    GEM_SCALE_NORMAL,
    GEM_STAT_TO_ELEMENT_SCALE,
    ELEMENTAL_GEM_SCALE,
    TOTAL_ROWS,
    MAX_STAT_INDEX,
)
from gear_optimizer.solver.scoring.base_inner_cpu_search import resolve_base_combo_exhaustive
from gear_optimizer.solver.scoring_core import (
    fast_calculate_score,
    lookup_reference_py,
    optimize_core_jit,
)


# Color-flag configs: (is_p_pp,is_s_pp,is_p_cm,is_s_cm,is_p_fm,is_s_fm,is_p_ov,is_s_ov).
# Each gem type's element contribution lands on primary/secondary per the active song colors; these
# cover single-color, dual-color, pp-allowed and pp-blocked lanes.
_FLAG_CONFIGS = (
    (1, 0, 1, 0, 0, 1, 0, 1),  # mixed, pp allowed
    (0, 0, 1, 0, 0, 1, 1, 0),  # pp blocked (no chill in p/s)
    (0, 1, 0, 1, 0, 1, 0, 1),  # all on secondary, pp allowed
    (1, 1, 0, 0, 0, 0, 0, 0),  # only pp lanes
    (0, 0, 0, 0, 0, 0, 1, 1),  # only overflow lanes (pp blocked)
)


def _greedy(budget, cur_pp, cur_cm, cur_fm, cur_p, cur_s, flags, ref_pp, ref_cm, ref_fm, head, bf, bn):
    (f_pp, f_cm, f_fm, f_p, f_s, g_pp, g_cm, g_fm, g_ov) = optimize_core_jit(
        budget, cur_pp, cur_cm, cur_fm, cur_p, cur_s,
        flags[0], flags[1], flags[2], flags[3], flags[4], flags[5], flags[6], flags[7],
        ref_pp, ref_cm, ref_fm, head, bf, bn,
        GEM_SCALE_NORMAL, GEM_SCALE_FEVER, GEM_STAT_TO_ELEMENT_SCALE, ELEMENTAL_GEM_SCALE,
        TOTAL_ROWS, MAX_STAT_INDEX,
    )
    base = (f_p * 2) + f_s + lookup_reference_py(f_pp, ref_pp, TOTAL_ROWS)
    c_mul = lookup_reference_py(f_cm, ref_cm, TOTAL_ROWS)
    f_mul = lookup_reference_py(f_fm, ref_fm, TOTAL_ROWS)
    score = fast_calculate_score(base, c_mul, f_mul, head, bf, bn)
    return int(score), (int(g_pp), int(g_cm), int(g_fm), int(g_ov))


def _rescore_exhaustive(out, ref_pp, ref_cm, ref_fm, head, bf, bn):
    """Re-score the exhaustive search's returned split through the production scoring path.

    resolve_base_combo_exhaustive returns
    (score, g_pp, g_cm, g_fm, g_ov, final_pp, final_cm, final_fm, final_p, final_s).
    """
    _score, _g_pp, _g_cm, _g_fm, _g_ov, f_pp, f_cm, f_fm, f_p, f_s = out
    base = (f_p * 2) + f_s + lookup_reference_py(f_pp, ref_pp, TOTAL_ROWS)
    c_mul = lookup_reference_py(f_cm, ref_cm, TOTAL_ROWS)
    f_mul = lookup_reference_py(f_fm, ref_fm, TOTAL_ROWS)
    return int(fast_calculate_score(base, c_mul, f_mul, head, bf, bn))


def test_exhaustive_dominates_greedy_and_is_self_consistent():
    ra = _get_team_buff_ref_arrays_cached()
    ref_pp = np.ascontiguousarray(np.asarray(ra["Perfect Points"], np.float32))
    ref_cm = np.ascontiguousarray(np.asarray(ra["Combo Multiplier"], np.float32))
    ref_fm = np.ascontiguousarray(np.asarray(ra["Fever Multiplier"], np.float32))

    rng = np.random.default_rng(20260621)
    n_cases = 0
    n_strictly_better = 0
    for flags in _FLAG_CONFIGS:
        for _ in range(120):
            budget = int(rng.integers(0, 91))
            cur_pp = int(rng.integers(0, 170))
            cur_cm = int(rng.integers(0, 170))
            cur_fm = int(rng.integers(0, 170))
            cur_p = int(rng.integers(0, 400))
            cur_s = int(rng.integers(0, 400))
            head_len = int(rng.integers(0, 101))
            head = (rng.integers(0, 2, size=head_len) > 0).astype(np.bool_)
            bf = int(rng.integers(0, 400))
            bn = int(rng.integers(0, 400))

            g_score, _g_split = _greedy(budget, cur_pp, cur_cm, cur_fm, cur_p, cur_s, flags,
                                        ref_pp, ref_cm, ref_fm, head, bf, bn)
            out = resolve_base_combo_exhaustive(
                budget, cur_pp, cur_cm, cur_fm, cur_p, cur_s,
                flags[0], flags[1], flags[2], flags[3], flags[4], flags[5], flags[6], flags[7],
                ref_pp, ref_cm, ref_fm, head, bf, bn,
            )
            e_score = int(out[0])

            # 1. Exhaustive must never score below greedy.
            assert e_score >= g_score, (
                f"exhaustive {e_score} < greedy {g_score} flags={flags} "
                f"budget={budget} pp={cur_pp} cm={cur_cm} fm={cur_fm} p={cur_p} s={cur_s}"
            )
            # 2. The reported score must match re-scoring its own returned gem split.
            assert e_score == _rescore_exhaustive(out, ref_pp, ref_cm, ref_fm, head, bf, bn), (
                f"exhaustive score {e_score} != re-score of returned split flags={flags}"
            )
            # 3. Returned gem counts (out[1:5] = g_pp,g_cm,g_fm,g_ov) must sum to the budget.
            assert int(out[1]) + int(out[2]) + int(out[3]) + int(out[4]) == budget
            n_cases += 1
            if e_score > g_score:
                n_strictly_better += 1

    assert n_cases > 0
    # Informational: prove the search actually finds cases the greedy misses (else the test is vacuous
    # against the motivating bug). Greedy is good but not optimal on the random distribution.
    print(f"base cpu search parity: {n_cases} cases, exhaustive strictly beat greedy in "
          f"{n_strictly_better}")
