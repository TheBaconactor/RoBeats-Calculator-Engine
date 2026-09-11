"""Research-only regional materialization using the production inner score function.

One GPU row owns one loadout/region, so different timing domains never share a
fitness result. Each row returns an allocation for canonical host comparison.
"""

import numpy as np
import taichi as ti

from gear_optimizer.core.constants import GEM_SCALE_FEVER
from gear_optimizer.solver.scoring.runtime_state import _GPU_LOCK
from gear_optimizer.solver.taichi_gem.api import (
    skyline_aggregate_stats, skyline_upload_base_fixed_stats,
    skyline_upload_item_stats, skyline_upload_population_indices,
)
from gear_optimizer.solver.taichi_gem.kernels.write_results_common import solve_best_combo_uncached


@ti.kernel
def _regional_kernel(n: ti.i32, budget: ti.i32, scale: ti.i32,
                     limits: ti.types.ndarray(dtype=ti.i32, ndim=2),
                     flags: ti.types.ndarray(dtype=ti.i32, ndim=1),
                     result: ti.types.ndarray(dtype=ti.i32, ndim=2)):
    for i in range(n):
        best = ti.Vector([-1, 0, 0, 0, 0, 0, 0])
        for ft in range(limits[i, 0], limits[i, 1] + 1):
            for ff in range(limits[i, 2], ti.min(limits[i, 3], budget - ft) + 1):
                value = solve_best_combo_uncached(i, ft, ff, budget, scale,
                    flags[0], flags[1], flags[2], flags[3], flags[4], flags[5],
                    flags[6], flags[7], flags[8], flags[9], flags[10], flags[11], 0, True, False)
                # Ascending FT then FF; >= preserves the full-table's highest
                # combo index on ties. The production residual solver owns its tie rule.
                if value[0] >= best[0]:
                    best = ti.Vector([value[0], ft, ff, value[1], value[2], value[3], value[4]])
        for j in ti.static(range(7)):
            result[i, j] = best[j]


def solve_regions(chart, arrays, ids, lows, highs):
    """Inputs must be feasible legal count rectangles (validated on the host)."""
    limits = np.ascontiguousarray(np.stack([lows[:, 0], highs[:, 0], lows[:, 1], highs[:, 1]], axis=1),
                                 dtype=np.int32)
    flags = chart.ga_kwargs["color_flags"]
    flag_array = np.array([flags[f"is_{color}_{gem}"]
                          for gem in ("ft", "ff", "pp", "cm", "fm", "ov")
                          for color in ("p", "s")], dtype=np.int32)
    result = np.empty((len(ids), 7), dtype=np.int32)
    with _GPU_LOCK:
        skyline_upload_item_stats(arrays["item_stats"], arrays["slot_start"], arrays["slot_count"])
        skyline_upload_base_fixed_stats(chart.base)
        skyline_upload_population_indices(ids, n_slots=9)
        skyline_aggregate_stats(len(ids), n_slots=9, **flags)
        _regional_kernel(len(ids), chart.domain.budget, GEM_SCALE_FEVER, limits, flag_array, result)
    return result
