from __future__ import annotations

import itertools
import math
import time
from dataclasses import dataclass

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.solver.solver_common import BitPack


@dataclass(frozen=True)
class LaneAwareMiniSkylineStats:
    combos_total: int
    unique_keys: int
    points_out: int
    seconds: float


def _item_vec_5(item: dict) -> tuple[int, int, int, int, int]:
    return (
        int(item.get("Perfect Points", 0) or 0),
        int(item.get("Combo Multiplier", 0) or 0),
        int(item.get("Fever Multiplier", 0) or 0),
        int(item.get("Fever Time", 0) or 0),
        int(item.get("Fever Fill Rate", 0) or 0),
    )


def _lane_base_init(item: dict, p_color: str, s_color: str) -> int:
    primary = int(item.get(p_color, 0) or 0) if p_color else 0
    secondary = int(item.get(s_color, 0) or 0) if s_color and s_color != p_color else 0
    return (2 * primary) + secondary


def _suffix_max_4d(src: np.ndarray, out: np.ndarray) -> None:
    out[...] = src
    np.maximum.accumulate(out[::-1, :, :, :], axis=0, out=out[::-1, :, :, :])
    np.maximum.accumulate(out[:, ::-1, :, :], axis=1, out=out[:, ::-1, :, :])
    np.maximum.accumulate(out[:, :, ::-1, :], axis=2, out=out[:, :, ::-1, :])
    np.maximum.accumulate(out[:, :, :, ::-1], axis=3, out=out[:, :, :, ::-1])


def mini_combo_skyline(
    mini_pool: list[dict],
    *,
    p_color: str,
    s_color: str,
    pack: BitPack,
) -> tuple[LaneAwareMiniSkylineStats, np.ndarray, np.ndarray]:
    t0 = time.perf_counter()
    n = len(mini_pool)
    if n < 3:
        return (
            LaneAwareMiniSkylineStats(combos_total=0, unique_keys=0, points_out=0, seconds=float(time.perf_counter() - t0)),
            np.zeros((0, 5), dtype=np.int32),
            np.zeros(0, dtype=np.uint64),
        )

    combos_total = int(math.comb(n, 3))
    states: dict[tuple[int, int, int, int], tuple[int, int]] = {}
    shift0, shift1, shift2 = pack.shifts

    for a_i, b_i, c_i in itertools.combinations(range(n), 3):
        a = mini_pool[a_i]
        b = mini_pool[b_i]
        c = mini_pool[c_i]

        _pp1, cm1, fm1, ft1, ff1 = _item_vec_5(a)
        _pp2, cm2, fm2, ft2, ff2 = _item_vec_5(b)
        _pp3, cm3, fm3, ft3, ff3 = _item_vec_5(c)

        cm = min(MAX_STAT_INDEX, max(0, cm1 + cm2 + cm3))
        fm = min(MAX_STAT_INDEX, max(0, fm1 + fm2 + fm3))
        ft = min(MAX_STAT_INDEX, max(0, ft1 + ft2 + ft3))
        ff = min(MAX_STAT_INDEX, max(0, ff1 + ff2 + ff3))
        base = _lane_base_init(a, p_color, s_color) + _lane_base_init(b, p_color, s_color) + _lane_base_init(c, p_color, s_color)

        key = (int(cm), int(fm), int(ft), int(ff))
        code = (int(a_i) << int(shift0)) | (int(b_i) << int(shift1)) | (int(c_i) << int(shift2))
        prev = states.get(key)
        if prev is None or base > prev[0]:
            states[key] = (int(base), int(code))

    if not states:
        return (
            LaneAwareMiniSkylineStats(
                combos_total=combos_total,
                unique_keys=0,
                points_out=0,
                seconds=float(time.perf_counter() - t0),
            ),
            np.zeros((0, 5), dtype=np.int32),
            np.zeros(0, dtype=np.uint64),
        )

    keys = np.array(list(states.keys()), dtype=np.int32)
    vals = np.array([value[0] for value in states.values()], dtype=np.int16)
    codes = np.array([value[1] for value in states.values()], dtype=np.uint64)

    cm = keys[:, 0]
    fm = keys[:, 1]
    ft = keys[:, 2]
    ff = keys[:, 3]

    max_cm = int(np.max(cm))
    max_fm = int(np.max(fm))
    max_ft = int(np.max(ft))
    max_ff = int(np.max(ff))

    cm_size = max_cm + 1
    fm_size = max_fm + 1
    ft_size = max_ft + 1
    ff_size = max_ff + 1

    flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
    shape = (cm_size, fm_size, ft_size, ff_size)
    grid_elems = int(cm_size) * int(fm_size) * int(ft_size) * int(ff_size)
    if grid_elems > 250_000_000:
        raise MemoryError(f"Mini skyline grid too large: {shape} ({grid_elems:,} elems). Try reducing pools or use GA.")

    layer_grid = np.full(shape, -1, dtype=np.int16)
    layer_suffix = np.empty(shape, dtype=np.int16)

    order = np.lexsort((-vals.astype(np.int32, copy=False), flat.astype(np.int32, copy=False)))
    flat_sorted = flat[order].astype(np.int32, copy=False)
    base_sorted = vals[order]
    code_sorted = codes[order]

    uniq_flat, first_idx = np.unique(flat_sorted, return_index=True)
    base_u = base_sorted[first_idx]
    code_u = code_sorted[first_idx]

    layer_flat = layer_grid.reshape(-1)
    layer_flat.fill(-1)
    layer_flat[uniq_flat] = base_u
    _suffix_max_4d(layer_grid, layer_suffix)

    ff_u = uniq_flat % ff_size
    tmp = uniq_flat // ff_size
    ft_u = tmp % ft_size
    tmp //= ft_size
    fm_u = tmp % fm_size
    cm_u = tmp // fm_size

    strict = np.full_like(base_u, -1)
    m0 = (cm_u + 1) < cm_size
    if np.any(m0):
        strict[m0] = np.maximum(strict[m0], layer_suffix[cm_u[m0] + 1, fm_u[m0], ft_u[m0], ff_u[m0]])
    m1 = (fm_u + 1) < fm_size
    if np.any(m1):
        strict[m1] = np.maximum(strict[m1], layer_suffix[cm_u[m1], fm_u[m1] + 1, ft_u[m1], ff_u[m1]])
    m2 = (ft_u + 1) < ft_size
    if np.any(m2):
        strict[m2] = np.maximum(strict[m2], layer_suffix[cm_u[m2], fm_u[m2], ft_u[m2] + 1, ff_u[m2]])
    m3 = (ff_u + 1) < ff_size
    if np.any(m3):
        strict[m3] = np.maximum(strict[m3], layer_suffix[cm_u[m3], fm_u[m3], ft_u[m3], ff_u[m3] + 1])

    layer_sky = base_u > strict
    if not np.any(layer_sky):
        points = np.zeros((0, 5), dtype=np.int32)
        out_codes = np.zeros(0, dtype=np.uint64)
    else:
        points = np.column_stack(
            (
                cm_u[layer_sky].astype(np.int32),
                fm_u[layer_sky].astype(np.int32),
                ft_u[layer_sky].astype(np.int32),
                ff_u[layer_sky].astype(np.int32),
                base_u[layer_sky].astype(np.int32),
            )
        )
        out_codes = code_u[layer_sky].astype(np.uint64, copy=False)

    stats = LaneAwareMiniSkylineStats(
        combos_total=combos_total,
        unique_keys=int(keys.shape[0]),
        points_out=int(points.shape[0]),
        seconds=float(time.perf_counter() - t0),
    )
    return stats, points, out_codes
