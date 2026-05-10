import time

import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.core.parsing import env_get
from gear_optimizer.solver.skyline_grid_gpu import OWNER_SENTINEL, fill_i32, layer_offsets, suffix_max_cm_fm_gpu
from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti


def _dense_gpu_max_gib() -> float:
    raw = str(env_get("SKYLINE_COMBINED_DENSE_GPU_MAX_GIB", "8.0") or "8.0").strip()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 8.0
    return max(0.0, float(value))


@ti.kernel
def _scatter_combined_layer_base(
    flat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    layer_count: ti.i32,
    layer_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count):
        f = flat[p]
        ti.atomic_max(layer_grid[f], base[p])


@ti.kernel
def _scatter_combined_layer_owner(
    flat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    layer_count: ti.i32,
    layer_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    owner_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count):
        f = flat[p]
        if base[p] == layer_grid[f]:
            ti.atomic_min(owner_grid[f], p)


@ti.kernel
def _filter_combined_layer(
    flat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    gear_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    mini_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    layer_count: ti.i32,
    cm_size: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
    higher_valid: ti.i32,
    layer_suffix: ti.types.ndarray(dtype=ti.i32, ndim=1),
    owner_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    higher_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_gear_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_mini_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count):
        f = flat[p]
        if p == owner_grid[f]:
            b = base[p]

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
                out_gear_idx[out_i] = gear_idx[p]
                out_mini_idx[out_i] = mini_idx[p]


def combined_global_skyline_pairs_6d_dense_gpu(
    gear_points: np.ndarray,
    mini_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float]:
    started = time.perf_counter()
    if gear_points.size == 0 or mini_points.size == 0:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), float(time.perf_counter() - started)

    gear = np.ascontiguousarray(np.asarray(gear_points, dtype=np.int32))
    mini = np.ascontiguousarray(np.asarray(mini_points, dtype=np.int32))
    max_pp = int(np.max(gear[:, 0]))
    max_cm = int(min(MAX_STAT_INDEX, int(np.max(gear[:, 1]) + np.max(mini[:, 0]))))
    max_fm = int(min(MAX_STAT_INDEX, int(np.max(gear[:, 2]) + np.max(mini[:, 1]))))
    max_ft = int(min(MAX_STAT_INDEX, int(np.max(gear[:, 3]) + np.max(mini[:, 2]))))
    max_ff = int(min(MAX_STAT_INDEX, int(np.max(gear[:, 4]) + np.max(mini[:, 3]))))

    cm_size = int(max_cm) + 1
    fm_size = int(max_fm) + 1
    ft_size = int(max_ft) + 1
    ff_size = int(max_ff) + 1
    grid_elems = int(cm_size) * int(fm_size) * int(ft_size) * int(ff_size)
    approx_bytes = int(grid_elems) * 4 * 3
    if approx_bytes > int(_dense_gpu_max_gib() * float(1024**3)):
        gib = float(approx_bytes) / float(1024**3)
        raise MemoryError(
            "Combined dense GPU skyline grid too large: "
            f"{(cm_size, fm_size, ft_size, ff_size)} ({grid_elems:,} elems, ~{gib:.2f} GiB)"
        )

    init_taichi()

    pp_order = np.argsort(gear[:, 0], kind="stable").astype(np.int32, copy=False)
    gear_sort = gear[pp_order]
    pp_offsets = layer_offsets(np.ascontiguousarray(gear_sort[:, 0]), int(max_pp))
    max_layer_gears = int(np.max(np.diff(pp_offsets))) if pp_offsets.size > 1 else 0
    max_layer_count = int(max_layer_gears) * int(mini.shape[0])
    if max_layer_count <= 0:
        return np.zeros(0, dtype=np.int32), np.zeros(0, dtype=np.int32), float(time.perf_counter() - started)

    layer_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    owner_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    higher_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    out_gear_idx = ti.ndarray(dtype=ti.i32, shape=(max_layer_count,))
    out_mini_idx = ti.ndarray(dtype=ti.i32, shape=(max_layer_count,))
    out_count = ti.ndarray(dtype=ti.i32, shape=(1,))

    fill_i32(higher_grid, grid_elems, -1)
    higher_valid = 0
    kept_g: list[np.ndarray] = []
    kept_m: list[np.ndarray] = []

    m_cm = mini[:, 0].astype(np.int32, copy=False)
    m_fm = mini[:, 1].astype(np.int32, copy=False)
    m_ft = mini[:, 2].astype(np.int32, copy=False)
    m_ff = mini[:, 3].astype(np.int32, copy=False)
    m_base = mini[:, 4].astype(np.int32, copy=False)
    m_idx = np.arange(int(mini.shape[0]), dtype=np.int32)

    for pp in range(int(max_pp), -1, -1):
        s = int(pp_offsets[pp])
        e = int(pp_offsets[pp + 1])
        if s >= e:
            continue

        g = gear_sort[s:e]
        g_orig = pp_order[s:e].astype(np.int32, copy=False)
        k = int(g.shape[0])
        m = int(mini.shape[0])
        n = int(k) * int(m)
        if n <= 0:
            continue

        cm = np.minimum(int(MAX_STAT_INDEX), g[:, 1:2] + m_cm[None, :]).ravel().astype(np.int32, copy=False)
        fm = np.minimum(int(MAX_STAT_INDEX), g[:, 2:3] + m_fm[None, :]).ravel().astype(np.int32, copy=False)
        ft = np.minimum(int(MAX_STAT_INDEX), g[:, 3:4] + m_ft[None, :]).ravel().astype(np.int32, copy=False)
        ff = np.minimum(int(MAX_STAT_INDEX), g[:, 4:5] + m_ff[None, :]).ravel().astype(np.int32, copy=False)
        base = (g[:, 5:6] + m_base[None, :]).ravel().astype(np.int32, copy=False)
        flat = ((((cm * int(fm_size)) + fm) * int(ft_size) + ft) * int(ff_size) + ff).astype(np.int32, copy=False)
        g_idx = np.broadcast_to(g_orig[:, None], (k, m)).ravel().astype(np.int32, copy=False)
        mini_idx = np.broadcast_to(m_idx[None, :], (k, m)).ravel().astype(np.int32, copy=False)

        flat_dev = ti.ndarray(dtype=ti.i32, shape=(n,))
        base_dev = ti.ndarray(dtype=ti.i32, shape=(n,))
        gear_idx_dev = ti.ndarray(dtype=ti.i32, shape=(n,))
        mini_idx_dev = ti.ndarray(dtype=ti.i32, shape=(n,))
        flat_dev.from_numpy(np.ascontiguousarray(flat))
        base_dev.from_numpy(np.ascontiguousarray(base))
        gear_idx_dev.from_numpy(np.ascontiguousarray(g_idx))
        mini_idx_dev.from_numpy(np.ascontiguousarray(mini_idx))

        fill_i32(layer_grid, grid_elems, -1)
        fill_i32(owner_grid, grid_elems, int(OWNER_SENTINEL))
        fill_i32(out_count, 1, 0)
        _scatter_combined_layer_base(flat_dev, base_dev, int(n), layer_grid)
        _scatter_combined_layer_owner(flat_dev, base_dev, int(n), layer_grid, owner_grid)
        suffix_max_cm_fm_gpu(layer_grid, cm_size=cm_size, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size)
        _filter_combined_layer(
            flat_dev,
            base_dev,
            gear_idx_dev,
            mini_idx_dev,
            int(n),
            int(cm_size),
            int(fm_size),
            int(ft_size),
            int(ff_size),
            int(higher_valid),
            layer_grid,
            owner_grid,
            higher_grid,
            out_gear_idx,
            out_mini_idx,
            out_count,
        )
        suffix_max_cm_fm_gpu(higher_grid, cm_size=cm_size, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size)
        higher_valid = 1

        count = int(out_count.to_numpy()[0])
        if count <= 0:
            continue
        kept_g.append(out_gear_idx.to_numpy()[:count].astype(np.int32, copy=False))
        kept_m.append(out_mini_idx.to_numpy()[:count].astype(np.int32, copy=False))

    out_g = np.concatenate(kept_g, axis=0) if kept_g else np.zeros(0, dtype=np.int32)
    out_m = np.concatenate(kept_m, axis=0) if kept_m else np.zeros(0, dtype=np.int32)
    return out_g, out_m, float(time.perf_counter() - started)
