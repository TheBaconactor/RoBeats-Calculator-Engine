from __future__ import annotations

import numpy as np

from gear_optimizer.solver.exact_base_search import _build_response_cm_fm_bound


def test_response_cm_fm_bound_covers_every_allocation_in_its_bin() -> None:
    response_delta = np.asarray(
        [(budget * budget) + (3 * budget) for budget in range(91)],
        dtype=np.int32,
    )
    stat_weight = 9

    bound = _build_response_cm_fm_bound(
        response_delta,
        stat_elemental_weight_max=stat_weight,
    ).reshape(91, 10)

    for budget in range(91):
        for stat_gems in range(budget + 1):
            bin_index = stat_gems // 10
            exact_base_response = (
                stat_gems * stat_weight
                + int(response_delta[budget - stat_gems])
            )
            assert int(bound[budget, bin_index]) >= exact_base_response

