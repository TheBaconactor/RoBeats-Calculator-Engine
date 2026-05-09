import numpy as np

from gear_optimizer.core.constants import MAX_STAT_INDEX
from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti


_EMPTY_I32 = np.zeros(0, dtype=np.int32)
_OWNER_SENTINEL = np.int32(2_147_483_647)


@ti.kernel
def _fill_i32(a: ti.types.ndarray(dtype=ti.i32, ndim=1), n: ti.i32, value: ti.i32):
    for i in range(n):
        a[i] = value


@ti.kernel
def _scatter_layer_base(
    gear: ti.types.ndarray(dtype=ti.i32, ndim=2),
    mini: ti.types.ndarray(dtype=ti.i32, ndim=2),
    layer_start: ti.i32,
    layer_count: ti.i32,
    mini_count: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
    max_cm: ti.i32,
    max_fm: ti.i32,
    max_ft: ti.i32,
    max_ff: ti.i32,
    layer_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count * mini_count):
        g_local = p // mini_count
        m = p - g_local * mini_count
        g = layer_start + g_local

        cm = gear[g, 1] + mini[m, 0]
        fm = gear[g, 2] + mini[m, 1]
        ft = gear[g, 3] + mini[m, 2]
        ff = gear[g, 4] + mini[m, 3]
        if cm > max_cm:
            cm = max_cm
        if fm > max_fm:
            fm = max_fm
        if ft > max_ft:
            ft = max_ft
        if ff > max_ff:
            ff = max_ff

        flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
        base = gear[g, 5] + mini[m, 4]
        ti.atomic_max(layer_grid[flat], base)


@ti.kernel
def _scatter_layer_owner(
    gear: ti.types.ndarray(dtype=ti.i32, ndim=2),
    mini: ti.types.ndarray(dtype=ti.i32, ndim=2),
    layer_start: ti.i32,
    layer_count: ti.i32,
    mini_count: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
    max_cm: ti.i32,
    max_fm: ti.i32,
    max_ft: ti.i32,
    max_ff: ti.i32,
    layer_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    owner_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count * mini_count):
        g_local = p // mini_count
        m = p - g_local * mini_count
        g = layer_start + g_local

        cm = gear[g, 1] + mini[m, 0]
        fm = gear[g, 2] + mini[m, 1]
        ft = gear[g, 3] + mini[m, 2]
        ff = gear[g, 4] + mini[m, 3]
        if cm > max_cm:
            cm = max_cm
        if fm > max_fm:
            fm = max_fm
        if ft > max_ft:
            ft = max_ft
        if ff > max_ff:
            ff = max_ff

        flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
        base = gear[g, 5] + mini[m, 4]
        if base == layer_grid[flat]:
            ti.atomic_min(owner_grid[flat], p)


@ti.kernel
def _suffix_cm(
    grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    cm_size: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
):
    for fm, ft, ff in ti.ndrange(fm_size, ft_size, ff_size):
        for cm_rev in range(cm_size - 1):
            cm = cm_size - 2 - cm_rev
            flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
            next_flat = ((((cm + 1) * fm_size) + fm) * ft_size + ft) * ff_size + ff
            v = grid[next_flat]
            if v > grid[flat]:
                grid[flat] = v


@ti.kernel
def _suffix_fm(
    grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    cm_size: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
):
    for cm, ft, ff in ti.ndrange(cm_size, ft_size, ff_size):
        for fm_rev in range(fm_size - 1):
            fm = fm_size - 2 - fm_rev
            flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
            next_flat = (((cm * fm_size) + fm + 1) * ft_size + ft) * ff_size + ff
            v = grid[next_flat]
            if v > grid[flat]:
                grid[flat] = v


@ti.kernel
def _suffix_ft(
    grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    cm_size: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
):
    for cm, fm, ff in ti.ndrange(cm_size, fm_size, ff_size):
        for ft_rev in range(ft_size - 1):
            ft = ft_size - 2 - ft_rev
            flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
            next_flat = (((cm * fm_size) + fm) * ft_size + ft + 1) * ff_size + ff
            v = grid[next_flat]
            if v > grid[flat]:
                grid[flat] = v


@ti.kernel
def _suffix_ff(
    grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    cm_size: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
):
    for cm, fm, ft in ti.ndrange(cm_size, fm_size, ft_size):
        for ff_rev in range(ff_size - 1):
            ff = ff_size - 2 - ff_rev
            flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
            next_flat = flat + 1
            v = grid[next_flat]
            if v > grid[flat]:
                grid[flat] = v


def _suffix_max_4d_gpu(grid, *, cm_size: int, fm_size: int, ft_size: int, ff_size: int) -> None:
    _suffix_cm(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))
    _suffix_fm(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))
    _suffix_ft(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))
    _suffix_ff(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))


@ti.kernel
def _filter_layer(
    gear: ti.types.ndarray(dtype=ti.i32, ndim=2),
    mini: ti.types.ndarray(dtype=ti.i32, ndim=2),
    orig_idx: ti.types.ndarray(dtype=ti.i32, ndim=1),
    layer_start: ti.i32,
    layer_count: ti.i32,
    mini_count: ti.i32,
    cm_size: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
    max_cm: ti.i32,
    max_fm: ti.i32,
    max_ft: ti.i32,
    max_ff: ti.i32,
    higher_valid: ti.i32,
    layer_suffix: ti.types.ndarray(dtype=ti.i32, ndim=1),
    owner_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    higher_grid: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_g: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_m: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for p in range(layer_count * mini_count):
        g_local = p // mini_count
        m = p - g_local * mini_count
        g = layer_start + g_local

        cm = gear[g, 1] + mini[m, 0]
        fm = gear[g, 2] + mini[m, 1]
        ft = gear[g, 3] + mini[m, 2]
        ff = gear[g, 4] + mini[m, 3]
        if cm > max_cm:
            cm = max_cm
        if fm > max_fm:
            fm = max_fm
        if ft > max_ft:
            ft = max_ft
        if ff > max_ff:
            ff = max_ff

        flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
        if p == owner_grid[flat]:
            base = gear[g, 5] + mini[m, 4]
            strict = -1
            if cm + 1 < cm_size:
                v0 = layer_suffix[((((cm + 1) * fm_size) + fm) * ft_size + ft) * ff_size + ff]
                if v0 > strict:
                    strict = v0
            if fm + 1 < fm_size:
                v1 = layer_suffix[(((cm * fm_size) + fm + 1) * ft_size + ft) * ff_size + ff]
                if v1 > strict:
                    strict = v1
            if ft + 1 < ft_size:
                v2 = layer_suffix[(((cm * fm_size) + fm) * ft_size + ft + 1) * ff_size + ff]
                if v2 > strict:
                    strict = v2
            if ff + 1 < ff_size:
                v3 = layer_suffix[flat + 1]
                if v3 > strict:
                    strict = v3

            keep = base > strict
            if keep and higher_valid != 0:
                keep = base > higher_grid[flat]

            if keep:
                ti.atomic_max(higher_grid[flat], base)
                out_i = ti.atomic_add(out_count[0], 1)
                out_g[out_i] = orig_idx[g]
                out_m[out_i] = m


def _layer_offsets(sorted_pp: np.ndarray, max_pp: int) -> np.ndarray:
    counts = np.bincount(sorted_pp, minlength=max_pp + 1).astype(np.int64, copy=False)
    offsets = np.zeros(max_pp + 2, dtype=np.int64)
    offsets[1:] = np.cumsum(counts)
    return offsets


def combined_global_skyline_pairs_6d_gpu(
    gear_points: np.ndarray,
    mini_points: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    if gear_points.size == 0 or mini_points.size == 0:
        return _EMPTY_I32.copy(), _EMPTY_I32.copy()

    init_taichi()

    gear_points = np.ascontiguousarray(gear_points.astype(np.int32, copy=False))
    mini_points = np.ascontiguousarray(mini_points.astype(np.int32, copy=False))

    max_pp = int(np.max(gear_points[:, 0]))
    max_cm = int(min(MAX_STAT_INDEX, int(np.max(gear_points[:, 1]) + np.max(mini_points[:, 0]))))
    max_fm = int(min(MAX_STAT_INDEX, int(np.max(gear_points[:, 2]) + np.max(mini_points[:, 1]))))
    max_ft = int(min(MAX_STAT_INDEX, int(np.max(gear_points[:, 3]) + np.max(mini_points[:, 2]))))
    max_ff = int(min(MAX_STAT_INDEX, int(np.max(gear_points[:, 4]) + np.max(mini_points[:, 3]))))

    cm_size = max_cm + 1
    fm_size = max_fm + 1
    ft_size = max_ft + 1
    ff_size = max_ff + 1
    grid_elems = int(cm_size) * int(fm_size) * int(ft_size) * int(ff_size)

    if grid_elems > 250_000_000:
        shape = (cm_size, fm_size, ft_size, ff_size)
        raise MemoryError(f"Combined skyline GPU grid too large: {shape} ({grid_elems:,} elems)")

    approx_bytes = int(grid_elems) * 4 * 3
    if approx_bytes > 8 * 1024**3:
        shape = (cm_size, fm_size, ft_size, ff_size)
        gib = float(approx_bytes) / float(1024**3)
        raise MemoryError(f"Combined skyline GPU grid too large: {shape} ({grid_elems:,} elems, ~{gib:.2f} GiB)")

    pp_order = np.argsort(gear_points[:, 0], kind="stable").astype(np.int32, copy=False)
    g_sorted = np.ascontiguousarray(gear_points[pp_order])
    sorted_orig = np.ascontiguousarray(pp_order.astype(np.int32, copy=False))
    pp_offsets = _layer_offsets(g_sorted[:, 0], max_pp)

    mini_count = int(mini_points.shape[0])
    max_layer_count = int(np.max(np.diff(pp_offsets))) if pp_offsets.size > 1 else 0
    max_layer_products = int(max_layer_count) * int(mini_count)
    if max_layer_products <= 0:
        return _EMPTY_I32.copy(), _EMPTY_I32.copy()

    gear_dev = ti.ndarray(dtype=ti.i32, shape=g_sorted.shape)
    mini_dev = ti.ndarray(dtype=ti.i32, shape=mini_points.shape)
    orig_dev = ti.ndarray(dtype=ti.i32, shape=sorted_orig.shape)
    gear_dev.from_numpy(g_sorted)
    mini_dev.from_numpy(mini_points)
    orig_dev.from_numpy(sorted_orig)

    layer_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    owner_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    higher_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))

    out_g = ti.ndarray(dtype=ti.i32, shape=(max_layer_products,))
    out_m = ti.ndarray(dtype=ti.i32, shape=(max_layer_products,))
    out_count = ti.ndarray(dtype=ti.i32, shape=(1,))

    _fill_i32(higher_grid, grid_elems, -1)

    kept_g: list[np.ndarray] = []
    kept_m: list[np.ndarray] = []
    higher_valid = 0

    for pp in range(int(max_pp), -1, -1):
        layer_start = int(pp_offsets[pp])
        layer_end = int(pp_offsets[pp + 1])
        layer_count = int(layer_end - layer_start)
        if layer_count <= 0:
            continue

        _fill_i32(layer_grid, grid_elems, -1)
        _fill_i32(owner_grid, grid_elems, int(_OWNER_SENTINEL))
        _fill_i32(out_count, 1, 0)

        _scatter_layer_base(
            gear_dev, mini_dev,
            layer_start, layer_count, mini_count,
            fm_size, ft_size, ff_size,
            max_cm, max_fm, max_ft, max_ff,
            layer_grid,
        )
        _scatter_layer_owner(
            gear_dev, mini_dev,
            layer_start, layer_count, mini_count,
            fm_size, ft_size, ff_size,
            max_cm, max_fm, max_ft, max_ff,
            layer_grid, owner_grid,
        )
        _suffix_max_4d_gpu(layer_grid, cm_size=cm_size, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size)
        _filter_layer(
            gear_dev, mini_dev, orig_dev,
            layer_start, layer_count, mini_count,
            cm_size, fm_size, ft_size, ff_size,
            max_cm, max_fm, max_ft, max_ff,
            higher_valid,
            layer_grid, owner_grid, higher_grid,
            out_g, out_m, out_count,
        )
        _suffix_max_4d_gpu(higher_grid, cm_size=cm_size, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size)
        higher_valid = 1

        count = int(out_count.to_numpy()[0])
        if count <= 0:
            continue

        kept_g.append(out_g.to_numpy()[:count].astype(np.int32, copy=False))
        kept_m.append(out_m.to_numpy()[:count].astype(np.int32, copy=False))

    if not kept_g:
        return _EMPTY_I32.copy(), _EMPTY_I32.copy()

    return np.concatenate(kept_g, axis=0), np.concatenate(kept_m, axis=0)
