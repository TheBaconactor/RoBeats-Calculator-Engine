import time

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX

_LAST_COMBINED_SKYLINE_STATS: dict[str, object] = {}


def get_last_combined_skyline_stats() -> dict[str, object]:
    return dict(_LAST_COMBINED_SKYLINE_STATS)


def _add_phase(phase_seconds: dict[str, float], name: str, started: float) -> None:
    phase_seconds[str(name)] = float(phase_seconds.get(str(name), 0.0) + (time.perf_counter() - float(started)))


def _suffix_max_2d_inplace(grid: np.ndarray) -> None:
    np.maximum.accumulate(grid[::-1, :], axis=0, out=grid[::-1, :])
    np.maximum.accumulate(grid[:, ::-1], axis=1, out=grid[:, ::-1])


def combined_global_skyline_pairs_6d_sparse(
    gear_points: np.ndarray,
    mini_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    global _LAST_COMBINED_SKYLINE_STATS
    t_total = time.perf_counter()
    phase_seconds: dict[str, float] = {}
    if gear_points.size == 0 or mini_points.size == 0:
        _LAST_COMBINED_SKYLINE_STATS = {
            "phase_seconds": {},
            "counts": {"gear_points": 0, "mini_points": 0, "layers": 0},
            "dominance": "fixed_final_ft_ff",
            "total_seconds": 0.0,
        }
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)

    t_phase = time.perf_counter()
    gear = np.ascontiguousarray(gear_points.astype(np.int32))
    mini = np.ascontiguousarray(mini_points.astype(np.int32))
    M = int(mini.shape[0])
    max_pp = int(np.max(gear[:, 0]))
    max_cm = int(min(MAX_STAT_INDEX, int(np.max(gear[:, 1]) + np.max(mini[:, 0]))))
    max_fm = int(min(MAX_STAT_INDEX, int(np.max(gear[:, 2]) + np.max(mini[:, 1]))))
    max_ff = int(min(MAX_STAT_INDEX, int(np.max(gear[:, 4]) + np.max(mini[:, 3]))))
    base_max = int(np.max(gear[:, 5]) + np.max(mini[:, 4]))
    base_dtype = np.int16 if base_max <= int(np.iinfo(np.int16).max) else np.int32
    cm_size = int(max_cm) + 1
    fm_size = int(max_fm) + 1
    ff_size = int(max_ff) + 1
    _add_phase(phase_seconds, "host_input_cast", t_phase)

    t_phase = time.perf_counter()
    pp_order = np.argsort(gear[:, 0], kind="stable").astype(np.int32)
    gear_sort = gear[pp_order]

    counts = np.bincount(gear_sort[:, 0], minlength=max_pp + 1).astype(np.int64)
    offsets = np.zeros(max_pp + 2, dtype=np.int64)
    offsets[1:] = np.cumsum(counts)
    _add_phase(phase_seconds, "host_pp_sort", t_phase)

    kept_g: list[np.ndarray] = []
    kept_m: list[np.ndarray] = []

    higher_by_cell: dict[int, np.ndarray] = {}
    layer_grid = np.empty((cm_size, fm_size), dtype=base_dtype)
    layer_count_total = 0
    layer_rows_total = 0
    layer_unique_total = 0
    kept_rows_total = 0
    timing_cell_visits = 0

    for pp in range(int(max_pp), -1, -1):
        s = int(offsets[pp])
        e = int(offsets[pp + 1])
        if s >= e:
            continue

        K = e - s
        lg = gear_sort[s:e]
        lo = pp_order[s:e]
        layer_count_total += 1
        layer_rows_total += int(K) * int(M)

        t_phase = time.perf_counter()
        cm = np.minimum(lg[:, 1:2] + mini[None, :, 0], MAX_STAT_INDEX).ravel().astype(np.int32)
        fm = np.minimum(lg[:, 2:3] + mini[None, :, 1], MAX_STAT_INDEX).ravel().astype(np.int32)
        ft = np.minimum(lg[:, 3:4] + mini[None, :, 2], MAX_STAT_INDEX).ravel().astype(np.int32)
        ff = np.minimum(lg[:, 4:5] + mini[None, :, 3], MAX_STAT_INDEX).ravel().astype(np.int32)
        base = (lg[:, 5:6] + mini[None, :, 4]).ravel().astype(np.int32)
        gi = np.broadcast_to(lo[:, None], (K, M)).ravel().astype(np.int32)
        mi = np.broadcast_to(np.arange(M, dtype=np.int32)[None, :], (K, M)).ravel().astype(np.int32)
        _add_phase(phase_seconds, "host_layer_build", t_phase)

        t_phase = time.perf_counter()
        sidx = np.lexsort(
            (
                -base.astype(np.int64),
                ff.astype(np.int64),
                ft.astype(np.int64),
                fm.astype(np.int64),
                cm.astype(np.int64),
            )
        )
        cm_s = cm[sidx]
        fm_s = fm[sidx]
        ft_s = ft[sidx]
        ff_s = ff[sidx]
        base_s = base[sidx]
        gi_s = gi[sidx]
        mi_s = mi[sidx]

        Np = K * M
        if Np > 1:
            eq = (
                (cm_s[1:] == cm_s[:-1])
                & (fm_s[1:] == fm_s[:-1])
                & (ft_s[1:] == ft_s[:-1])
                & (ff_s[1:] == ff_s[:-1])
            )
            first = np.concatenate([[True], ~eq])
        else:
            first = np.ones(Np, dtype=bool)

        layer_arr = np.column_stack(
            [
                np.full(np.sum(first), pp, dtype=np.int32),
                cm_s[first],
                fm_s[first],
                ft_s[first],
                ff_s[first],
                base_s[first],
                gi_s[first],
                mi_s[first],
            ]
        )
        layer_unique_total += int(layer_arr.shape[0])
        _add_phase(phase_seconds, "host_layer_sort_dedupe", t_phase)

        t_phase = time.perf_counter()
        if layer_arr.size == 0:
            _add_phase(phase_seconds, "host_timing_cell_frontier", t_phase)
            continue

        cell_keys = (layer_arr[:, 3].astype(np.int64) * int(ff_size) + layer_arr[:, 4].astype(np.int64)).astype(
            np.int32,
            copy=False,
        )
        cell_order = np.argsort(cell_keys, kind="stable")
        sorted_cells = cell_keys[cell_order]
        starts = np.concatenate(
            (
                np.asarray([0], dtype=np.int64),
                np.flatnonzero(sorted_cells[1:] != sorted_cells[:-1]).astype(np.int64) + 1,
            )
        )
        ends = np.empty_like(starts)
        if starts.size > 0:
            ends[:-1] = starts[1:]
            ends[-1] = int(cell_order.shape[0])

        for start, end in zip(starts.tolist(), ends.tolist(), strict=True):
            loc = cell_order[int(start) : int(end)]
            timing_cell_visits += 1

            cm_c = layer_arr[loc, 1].astype(np.int32, copy=False)
            fm_c = layer_arr[loc, 2].astype(np.int32, copy=False)
            base_c = layer_arr[loc, 5].astype(np.int32, copy=False)

            layer_grid.fill(-1)
            layer_grid[cm_c, fm_c] = base_c.astype(base_dtype, copy=False)
            _suffix_max_2d_inplace(layer_grid)

            strict = np.full(int(loc.shape[0]), -1, dtype=np.int32)
            m0 = (cm_c + 1) < int(cm_size)
            if np.any(m0):
                strict[m0] = np.maximum(strict[m0], layer_grid[cm_c[m0] + 1, fm_c[m0]].astype(np.int32, copy=False))
            m1 = (fm_c + 1) < int(fm_size)
            if np.any(m1):
                strict[m1] = np.maximum(strict[m1], layer_grid[cm_c[m1], fm_c[m1] + 1].astype(np.int32, copy=False))

            keep = base_c > strict
            cell_key = int(sorted_cells[int(start)])
            higher_grid = higher_by_cell.get(cell_key)
            if higher_grid is not None:
                keep &= base_c > higher_grid[cm_c, fm_c].astype(np.int32, copy=False)

            if not np.any(keep):
                continue

            kept_rows = layer_arr[loc[keep]]
            kept_g.append(kept_rows[:, 6].astype(np.int32, copy=False))
            kept_m.append(kept_rows[:, 7].astype(np.int32, copy=False))
            kept_rows_total += int(kept_rows.shape[0])

            if higher_grid is None:
                higher_grid = np.full((cm_size, fm_size), -1, dtype=base_dtype)
                higher_by_cell[cell_key] = higher_grid
            cm_k = kept_rows[:, 1].astype(np.int32, copy=False)
            fm_k = kept_rows[:, 2].astype(np.int32, copy=False)
            base_k = kept_rows[:, 5].astype(base_dtype, copy=False)
            np.maximum.at(higher_grid, (cm_k, fm_k), base_k)
            _suffix_max_2d_inplace(higher_grid)

        _add_phase(phase_seconds, "host_timing_cell_frontier", t_phase)

    if not kept_g:
        _LAST_COMBINED_SKYLINE_STATS = {
            "phase_seconds": {key: round(float(value), 6) for key, value in phase_seconds.items()},
            "counts": {
                "gear_points": int(gear.shape[0]),
                "mini_points": int(M),
                "layers": int(layer_count_total),
                "layer_rows_total": int(layer_rows_total),
                "layer_unique_total": int(layer_unique_total),
                "timing_cell_visits": int(timing_cell_visits),
                "active_timing_cells": int(len(higher_by_cell)),
                "kept_rows_total": 0,
                "out_pairs": 0,
            },
            "dominance": "fixed_final_ft_ff",
            "total_seconds": round(float(time.perf_counter() - t_total), 6),
        }
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)
    out_g = np.concatenate(kept_g)
    out_m = np.concatenate(kept_m)
    _LAST_COMBINED_SKYLINE_STATS = {
        "phase_seconds": {key: round(float(value), 6) for key, value in phase_seconds.items()},
        "counts": {
            "gear_points": int(gear.shape[0]),
            "mini_points": int(M),
            "layers": int(layer_count_total),
            "layer_rows_total": int(layer_rows_total),
            "layer_unique_total": int(layer_unique_total),
            "timing_cell_visits": int(timing_cell_visits),
            "active_timing_cells": int(len(higher_by_cell)),
            "kept_rows_total": int(kept_rows_total),
            "out_pairs": int(out_g.shape[0]),
        },
        "dominance": "fixed_final_ft_ff",
        "total_seconds": round(float(time.perf_counter() - t_total), 6),
    }
    return out_g, out_m
