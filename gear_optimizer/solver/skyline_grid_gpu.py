import numpy as np

from gear_optimizer.solver.taichi_gem.runtime import ti


EMPTY_I32 = np.zeros(0, dtype=np.int32)
OWNER_SENTINEL = np.int32(2_147_483_647)


@ti.kernel
def fill_i32(a: ti.types.ndarray(dtype=ti.i32, ndim=1), n: ti.i32, value: ti.i32):
    for i in range(n):
        a[i] = value


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
            v = grid[flat + 1]
            if v > grid[flat]:
                grid[flat] = v


def suffix_max_4d_gpu(grid, *, cm_size: int, fm_size: int, ft_size: int, ff_size: int) -> None:
    _suffix_cm(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))
    _suffix_fm(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))
    _suffix_ft(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))
    _suffix_ff(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))


def suffix_max_cm_fm_gpu(grid, *, cm_size: int, fm_size: int, ft_size: int, ff_size: int) -> None:
    _suffix_cm(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))
    _suffix_fm(grid, int(cm_size), int(fm_size), int(ft_size), int(ff_size))


def layer_offsets(sorted_pp: np.ndarray, max_pp: int) -> np.ndarray:
    counts = np.bincount(sorted_pp, minlength=int(max_pp) + 1).astype(np.int64, copy=False)
    offsets = np.zeros(int(max_pp) + 2, dtype=np.int64)
    offsets[1:] = np.cumsum(counts)
    return offsets
