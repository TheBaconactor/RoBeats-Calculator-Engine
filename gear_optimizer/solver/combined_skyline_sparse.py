import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti


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


def combined_global_skyline_pairs_6d_sparse(
    gear_points: np.ndarray,
    mini_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if gear_points.size == 0 or mini_points.size == 0:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)

    init_taichi()

    gear = np.ascontiguousarray(gear_points.astype(np.int32))
    mini = np.ascontiguousarray(mini_points.astype(np.int32))
    M = int(mini.shape[0])
    max_pp = int(np.max(gear[:, 0]))

    pp_order = np.argsort(gear[:, 0], kind="stable").astype(np.int32)
    gear_sort = gear[pp_order]

    counts = np.bincount(gear_sort[:, 0], minlength=max_pp + 1).astype(np.int64)
    offsets = np.zeros(max_pp + 2, dtype=np.int64)
    offsets[1:] = np.cumsum(counts)

    kept_g: list[np.ndarray] = []
    kept_m: list[np.ndarray] = []

    higher = np.zeros((0, 8), dtype=np.int32)

    for pp in range(int(max_pp), -1, -1):
        s = int(offsets[pp])
        e = int(offsets[pp + 1])
        if s >= e:
            continue

        K = e - s
        lg = gear_sort[s:e]
        lo = pp_order[s:e]

        cm = np.minimum(lg[:, 1:2] + mini[None, :, 0], MAX_STAT_INDEX).ravel().astype(np.int32)
        fm = np.minimum(lg[:, 2:3] + mini[None, :, 1], MAX_STAT_INDEX).ravel().astype(np.int32)
        ft = np.minimum(lg[:, 3:4] + mini[None, :, 2], MAX_STAT_INDEX).ravel().astype(np.int32)
        ff = np.minimum(lg[:, 4:5] + mini[None, :, 3], MAX_STAT_INDEX).ravel().astype(np.int32)
        base = (lg[:, 5:6] + mini[None, :, 4]).ravel().astype(np.int32)
        gi = np.broadcast_to(lo[:, None], (K, M)).ravel().astype(np.int32)
        mi = np.broadcast_to(np.arange(M, dtype=np.int32)[None, :], (K, M)).ravel().astype(np.int32)

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

        H = int(higher.shape[0])
        if H > 0:
            combined = np.concatenate([higher, layer_arr], axis=0)
        else:
            combined = layer_arr

        N = int(combined.shape[0])

        sidx2 = np.lexsort(
            (
                -combined[:, 5].astype(np.int64),
                -combined[:, 4].astype(np.int64),
                -combined[:, 3].astype(np.int64),
                -combined[:, 2].astype(np.int64),
                -combined[:, 1].astype(np.int64),
                -combined[:, 0].astype(np.int64),
            )
        )
        cs = np.ascontiguousarray(combined[sidx2])

        pts_dev = ti.ndarray(dtype=ti.i32, shape=(N, 6))
        keep_dev = ti.ndarray(dtype=ti.i32, shape=(N,))
        pts_dev.from_numpy(np.ascontiguousarray(cs[:, :6]))

        _pareto_6d(pts_dev, N, keep_dev)

        k = keep_dev.to_numpy().astype(bool)

        orig_idx = sidx2[k]
        is_cur = orig_idx >= H
        if np.any(is_cur):
            kept_g.append(cs[k][is_cur, 6])
            kept_m.append(cs[k][is_cur, 7])

        higher = cs[k]

    if not kept_g:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)
    return np.concatenate(kept_g), np.concatenate(kept_m)
