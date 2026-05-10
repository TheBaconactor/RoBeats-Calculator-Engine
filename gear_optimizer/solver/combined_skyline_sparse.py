import time

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti

_LAST_COMBINED_SKYLINE_STATS: dict[str, object] = {}


def get_last_combined_skyline_stats() -> dict[str, object]:
    return dict(_LAST_COMBINED_SKYLINE_STATS)


def _add_phase(phase_seconds: dict[str, float], name: str, started: float) -> None:
    phase_seconds[str(name)] = float(phase_seconds.get(str(name), 0.0) + (time.perf_counter() - float(started)))


@ti.kernel
def _pareto_6d(
    pts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    N: ti.i32,
    keep: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for i in range(N):
        dominated = 0
        for j in range(i):
            if dominated == 0:
                ge = 1
                gt = 0
                for d in ti.static(range(6)):
                    if pts[j, d] < pts[i, d]:
                        ge = 0
                    if pts[j, d] > pts[i, d]:
                        gt = 1
                if ge == 1 and gt == 1:
                    dominated = 1
        keep[i] = 1 - dominated


@ti.kernel
def _pareto_current_6d(
    pts: ti.types.ndarray(dtype=ti.i32, ndim=2),
    higher_count: ti.i32,
    current_count: ti.i32,
    keep_current: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for local_i in range(current_count):
        i = higher_count + local_i
        dominated = 0
        for j in range(i):
            if dominated == 0:
                ge = 1
                gt = 0
                for d in ti.static(range(6)):
                    if pts[j, d] < pts[i, d]:
                        ge = 0
                    if pts[j, d] > pts[i, d]:
                        gt = 1
                if ge == 1 and gt == 1:
                    dominated = 1
        keep_current[local_i] = 1 - dominated


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
            "total_seconds": 0.0,
        }
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)

    init_taichi()

    t_phase = time.perf_counter()
    gear = np.ascontiguousarray(gear_points.astype(np.int32))
    mini = np.ascontiguousarray(mini_points.astype(np.int32))
    M = int(mini.shape[0])
    max_pp = int(np.max(gear[:, 0]))
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

    higher = np.zeros((0, 8), dtype=np.int32)
    layer_count_total = 0
    layer_rows_total = 0
    layer_unique_total = 0
    combined_rows_total = 0
    combined_rows_max = 0
    kept_rows_total = 0

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
        layer_desc = np.ascontiguousarray(
            layer_arr[
                np.lexsort(
                    (
                        -layer_arr[:, 5].astype(np.int64),
                        -layer_arr[:, 4].astype(np.int64),
                        -layer_arr[:, 3].astype(np.int64),
                        -layer_arr[:, 2].astype(np.int64),
                        -layer_arr[:, 1].astype(np.int64),
                    )
                )
            ]
        )
        _add_phase(phase_seconds, "host_current_sort", t_phase)

        t_phase = time.perf_counter()
        H = int(higher.shape[0])
        if H > 0:
            combined = np.concatenate([higher, layer_desc], axis=0)
        else:
            combined = layer_desc

        N = int(combined.shape[0])
        current_n = int(layer_desc.shape[0])
        combined_rows_total += int(N)
        combined_rows_max = max(int(combined_rows_max), int(N))
        _add_phase(phase_seconds, "host_combine_sort", t_phase)

        t_phase = time.perf_counter()
        pts_dev = ti.ndarray(dtype=ti.i32, shape=(N, 6))
        keep_dev = ti.ndarray(dtype=ti.i32, shape=(current_n,))
        pts_dev.from_numpy(np.ascontiguousarray(combined[:, :6]))
        _add_phase(phase_seconds, "gpu_alloc_upload", t_phase)

        t_phase = time.perf_counter()
        _pareto_current_6d(pts_dev, int(H), int(current_n), keep_dev)
        _add_phase(phase_seconds, "gpu_pareto_submit", t_phase)

        t_phase = time.perf_counter()
        current_keep = keep_dev.to_numpy().astype(bool)
        _add_phase(phase_seconds, "gpu_sync_download", t_phase)

        t_phase = time.perf_counter()
        if np.any(current_keep):
            current_kept = layer_desc[current_keep]
            kept_g.append(current_kept[:, 6])
            kept_m.append(current_kept[:, 7])
            kept_rows_total += int(current_kept.shape[0])
            higher = np.concatenate([higher, current_kept], axis=0) if H > 0 else current_kept
        elif H <= 0:
            higher = np.zeros((0, 8), dtype=np.int32)
        _add_phase(phase_seconds, "host_collect", t_phase)

    if not kept_g:
        _LAST_COMBINED_SKYLINE_STATS = {
            "phase_seconds": {key: round(float(value), 6) for key, value in phase_seconds.items()},
            "counts": {
                "gear_points": int(gear.shape[0]),
                "mini_points": int(M),
                "layers": int(layer_count_total),
                "layer_rows_total": int(layer_rows_total),
                "layer_unique_total": int(layer_unique_total),
                "combined_rows_total": int(combined_rows_total),
                "combined_rows_max": int(combined_rows_max),
                "kept_rows_total": 0,
                "out_pairs": 0,
            },
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
            "combined_rows_total": int(combined_rows_total),
            "combined_rows_max": int(combined_rows_max),
            "kept_rows_total": int(kept_rows_total),
            "out_pairs": int(out_g.shape[0]),
        },
        "total_seconds": round(float(time.perf_counter() - t_total), 6),
    }
    return out_g, out_m
