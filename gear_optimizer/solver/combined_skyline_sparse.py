import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.solver.skyline_grid_gpu import (
    OWNER_SENTINEL,
    fill_i32,
    layer_offsets,
    suffix_max_cm_fm_gpu,
)
from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti


@ti.kernel
def _scatter_combined_layer_base(
    flat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    layer_start: ti.i32,
    layer_count: ti.i32,
    layer_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count):
        src = layer_start + p
        ti.atomic_max(layer_grid[flat[src]], base[src])


@ti.kernel
def _scatter_combined_layer_owner(
    flat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    layer_start: ti.i32,
    layer_count: ti.i32,
    layer_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    owner_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count):
        src = layer_start + p
        f = flat[src]
        if base[src] == layer_grid[f]:
            ti.atomic_min(owner_grid[f], p)


@ti.kernel
def _filter_combined_layer(
    flat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    gi: ti.types.ndarray(dtype=ti.i32, ndim=1),
    mi: ti.types.ndarray(dtype=ti.i32, ndim=1),
    layer_start: ti.i32,
    layer_count: ti.i32,
    cm_size: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
    higher_valid: ti.i32,
    layer_suffix: ti.types.ndarray(dtype=ti.i32, ndim=1),
    owner_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    higher_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_gi: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_mi: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count):
        src = layer_start + p
        f = flat[src]
        if p == owner_grid[f]:
            b = base[src]
            ff = f % ff_size
            tmp0 = f // ff_size
            ft = tmp0 % ft_size
            tmp1 = tmp0 // ft_size
            fm = tmp1 % fm_size
            cm = tmp1 // fm_size
            strict = -1
            if cm + 1 < cm_size:
                v0 = layer_suffix[((((cm + 1) * fm_size) + fm) * ft_size + ft) * ff_size + ff]
                if v0 > strict:
                    strict = v0
            if fm + 1 < fm_size:
                v1 = layer_suffix[(((cm * fm_size) + fm + 1) * ft_size + ft) * ff_size + ff]
                if v1 > strict:
                    strict = v1
            keep = b > strict
            if keep and higher_valid != 0:
                keep = b > higher_grid[f]
            if keep:
                ti.atomic_max(higher_grid[f], b)
                out_i = ti.atomic_add(out_count[0], 1)
                out_gi[out_i] = gi[src]
                out_mi[out_i] = mi[src]


def combined_global_skyline_pairs_6d_sparse(
    gear_points: np.ndarray,
    mini_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if gear_points.size == 0 or mini_points.size == 0:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)

    init_taichi()

    gear = gear_points.astype(np.int32, copy=False)
    mini = mini_points.astype(np.int32, copy=False)
    M = int(mini.shape[0])
    max_pp = int(np.max(gear[:, 0]))

    pp_order = np.argsort(gear[:, 0], kind="stable").astype(np.int32)
    gear_sort = np.ascontiguousarray(gear[pp_order])
    pp_offsets = layer_offsets(gear_sort[:, 0], max_pp)

    max_cm = int(min(MAX_STAT_INDEX, np.max(gear[:, 1]) + np.max(mini[:, 0])))
    max_fm = int(min(MAX_STAT_INDEX, np.max(gear[:, 2]) + np.max(mini[:, 1])))
    max_ft = int(min(MAX_STAT_INDEX, np.max(gear[:, 3]) + np.max(mini[:, 2])))
    max_ff = int(min(MAX_STAT_INDEX, np.max(gear[:, 4]) + np.max(mini[:, 3])))
    cm_size = max_cm + 1
    fm_size = max_fm + 1
    ft_size = max_ft + 1
    ff_size = max_ff + 1

    grid_elems = cm_size * fm_size * ft_size * ff_size
    approx_gb = grid_elems * 4.0 * 3.0 / (1024.0**3)
    if grid_elems > 900_000_000 or approx_gb > 18.0:
        raise MemoryError(
            f"Combined skyline grid too large: "
            f"({cm_size},{fm_size},{ft_size},{ff_size}) = {grid_elems:,} cells, ~{approx_gb:.1f} GiB"
        )

    max_product = 0
    for pp in range(int(max_pp), -1, -1):
        s = int(pp_offsets[pp])
        e = int(pp_offsets[pp + 1])
        if s < e:
            max_product = max(max_product, (e - s) * M)

    layer_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    owner_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    higher_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    fill_i32(higher_grid, grid_elems, -1)

    out_gi = ti.ndarray(dtype=ti.i32, shape=(max_product,))
    out_mi = ti.ndarray(dtype=ti.i32, shape=(max_product,))
    out_count = ti.ndarray(dtype=ti.i32, shape=(1,))

    kept_g: list[np.ndarray] = []
    kept_m: list[np.ndarray] = []
    higher_valid = 0

    for pp in range(int(max_pp), -1, -1):
        s = int(pp_offsets[pp])
        e = int(pp_offsets[pp + 1])
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

        Np = K * M
        flat = (((cm.astype(np.int64) * fm_size + fm.astype(np.int64)) * ft_size + ft.astype(np.int64)) * ff_size + ff.astype(np.int64)).astype(np.int64)
        order = np.lexsort((-base.astype(np.int64), flat))
        flat_s = flat[order].astype(np.int32)
        base_s = base[order]
        gi_s = gi[order]
        mi_s = mi[order]

        flat_dev = ti.ndarray(dtype=ti.i32, shape=(Np,))
        base_dev = ti.ndarray(dtype=ti.i32, shape=(Np,))
        gi_dev = ti.ndarray(dtype=ti.i32, shape=(Np,))
        mi_dev = ti.ndarray(dtype=ti.i32, shape=(Np,))

        flat_dev.from_numpy(np.ascontiguousarray(flat_s))
        base_dev.from_numpy(np.ascontiguousarray(base_s))
        gi_dev.from_numpy(np.ascontiguousarray(gi_s))
        mi_dev.from_numpy(np.ascontiguousarray(mi_s))

        fill_i32(layer_grid, grid_elems, -1)
        fill_i32(owner_grid, grid_elems, int(OWNER_SENTINEL))
        fill_i32(out_count, 1, 0)

        _scatter_combined_layer_base(flat_dev, base_dev, 0, Np, layer_grid)
        _scatter_combined_layer_owner(flat_dev, base_dev, 0, Np, layer_grid, owner_grid)
        suffix_max_cm_fm_gpu(layer_grid, cm_size=cm_size, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size)

        _filter_combined_layer(
            flat_dev, base_dev, gi_dev, mi_dev,
            0, Np,
            cm_size, fm_size, ft_size, ff_size,
            higher_valid,
            layer_grid, owner_grid, higher_grid,
            out_gi, out_mi, out_count,
        )

        suffix_max_cm_fm_gpu(higher_grid, cm_size=cm_size, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size)
        higher_valid = 1

        count = int(out_count.to_numpy()[0])
        if count > 0:
            g_np = out_gi.to_numpy()[:count].astype(np.int32, copy=False)
            m_np = out_mi.to_numpy()[:count].astype(np.int32, copy=False)
            kept_g.append(g_np)
            kept_m.append(m_np)

    if not kept_g:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32)
    return np.concatenate(kept_g), np.concatenate(kept_m)
