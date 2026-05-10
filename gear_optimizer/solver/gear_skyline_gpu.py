import time

import numpy as np

from gear_optimizer.solver.skyline_grid_gpu import OWNER_SENTINEL, fill_i32, layer_offsets, suffix_max_cm_fm_gpu
from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti


@ti.kernel
def _scatter_gear_layer_base(
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
def _scatter_gear_layer_owner(
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
def _filter_gear_layer(
    flat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    code: ti.types.ndarray(dtype=ti.u64, ndim=1),
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
    out_flat: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_base: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_code: ti.types.ndarray(dtype=ti.u64, ndim=1),
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
                out_flat[out_i] = f
                out_base[out_i] = b
                out_code[out_i] = code[src]


def _flatten_states(
    states: dict[tuple[int, int, int, int], list[tuple[int, int, int]]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, int, int, int, int]:
    keys = list(states.keys())
    max_pp = max(k[0] for k in keys)
    max_cm = max(k[1] for k in keys)
    max_fm = max(k[2] for k in keys)
    max_ft = max(k[3] for k in keys)

    counts = np.zeros(int(max_pp) + 1, dtype=np.int64)
    total_points = 0
    max_ff = 0
    for (pp, _cm, _fm, _ft), frontier in states.items():
        n = len(frontier)
        counts[int(pp)] += n
        total_points += n
        for ff, _base, _code in frontier:
            if ff > max_ff:
                max_ff = int(ff)

    cm_size = int(max_cm) + 1
    fm_size = int(max_fm) + 1
    ft_size = int(max_ft) + 1
    ff_size = int(max_ff) + 1

    offsets = np.zeros(int(max_pp) + 2, dtype=np.int64)
    offsets[1:] = np.cumsum(counts)

    flat = np.empty(total_points, dtype=np.int32)
    base = np.empty(total_points, dtype=np.int32)
    code = np.empty(total_points, dtype=np.uint64)
    pp_values = np.empty(total_points, dtype=np.int32)
    curs = offsets[:-1].copy()

    for (pp, cm, fm, ft), frontier in states.items():
        pp_i = int(pp)
        cur = int(curs[pp_i])
        prefix = ((int(cm) * fm_size + int(fm)) * ft_size + int(ft)) * ff_size
        for ff, b, c in frontier:
            flat[cur] = prefix + int(ff)
            base[cur] = int(b)
            code[cur] = np.uint64(int(c))
            pp_values[cur] = pp_i
            cur += 1
        curs[pp_i] = cur

    return flat, base, code, pp_values, int(max_pp), cm_size, fm_size, ft_size, ff_size


def _points_from_flat(pp: int, flat: np.ndarray, base: np.ndarray, *, fm_size: int, ft_size: int, ff_size: int) -> np.ndarray:
    ff = flat % int(ff_size)
    tmp = flat // int(ff_size)
    ft = tmp % int(ft_size)
    tmp //= int(ft_size)
    fm = tmp % int(fm_size)
    cm = tmp // int(fm_size)
    return np.column_stack(
        (
            np.full(flat.shape, int(pp), dtype=np.int32),
            cm.astype(np.int32, copy=False),
            fm.astype(np.int32, copy=False),
            ft.astype(np.int32, copy=False),
            ff.astype(np.int32, copy=False),
            base.astype(np.int32, copy=False),
        )
    )


def global_gear_skyline_points_6d_gpu(
    states: dict[tuple[int, int, int, int], list[tuple[int, int, int]]],
) -> tuple[int, np.ndarray, np.ndarray, float]:
    t0 = time.perf_counter()
    if not states:
        return 0, np.zeros((0, 6), dtype=np.int32), np.zeros(0, dtype=np.uint64), float(time.perf_counter() - t0)

    flat, base, code, pp_values, max_pp, cm_size, fm_size, ft_size, ff_size = _flatten_states(states)
    total_points = int(flat.shape[0])
    if total_points <= 0:
        return 0, np.zeros((0, 6), dtype=np.int32), np.zeros(0, dtype=np.uint64), float(time.perf_counter() - t0)

    grid_elems = int(cm_size) * int(fm_size) * int(ft_size) * int(ff_size)
    shape = (int(cm_size), int(fm_size), int(ft_size), int(ff_size))
    if grid_elems > 250_000_000:
        raise MemoryError(f"Gear skyline GPU grid too large: {shape} ({grid_elems:,} elems). Try reducing pools or use GA.")

    approx_bytes = int(grid_elems) * 4 * 3
    if approx_bytes > 8 * 1024**3:
        gib = float(approx_bytes) / float(1024**3)
        raise MemoryError(f"Gear skyline GPU grid too large: {shape} ({grid_elems:,} elems, ~{gib:.2f} GiB)")

    init_taichi()

    order = np.argsort(pp_values, kind="stable").astype(np.int32, copy=False)
    flat_sorted = np.ascontiguousarray(flat[order])
    base_sorted = np.ascontiguousarray(base[order])
    code_sorted = np.ascontiguousarray(code[order])
    pp_sorted = np.ascontiguousarray(pp_values[order])
    pp_offsets = layer_offsets(pp_sorted, int(max_pp))
    max_layer_count = int(np.max(np.diff(pp_offsets))) if pp_offsets.size > 1 else 0
    if max_layer_count <= 0:
        return total_points, np.zeros((0, 6), dtype=np.int32), np.zeros(0, dtype=np.uint64), float(time.perf_counter() - t0)

    flat_dev = ti.ndarray(dtype=ti.i32, shape=flat_sorted.shape)
    base_dev = ti.ndarray(dtype=ti.i32, shape=base_sorted.shape)
    code_dev = ti.ndarray(dtype=ti.u64, shape=code_sorted.shape)
    flat_dev.from_numpy(flat_sorted)
    base_dev.from_numpy(base_sorted)
    code_dev.from_numpy(code_sorted)

    layer_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    owner_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))
    higher_grid = ti.ndarray(dtype=ti.i32, shape=(grid_elems,))

    out_flat = ti.ndarray(dtype=ti.i32, shape=(max_layer_count,))
    out_base = ti.ndarray(dtype=ti.i32, shape=(max_layer_count,))
    out_code = ti.ndarray(dtype=ti.u64, shape=(max_layer_count,))
    out_count = ti.ndarray(dtype=ti.i32, shape=(1,))

    fill_i32(higher_grid, grid_elems, -1)

    kept_points: list[np.ndarray] = []
    kept_codes: list[np.ndarray] = []
    higher_valid = 0

    for pp in range(int(max_pp), -1, -1):
        layer_start = int(pp_offsets[pp])
        layer_end = int(pp_offsets[pp + 1])
        layer_count = int(layer_end - layer_start)
        if layer_count <= 0:
            continue

        fill_i32(layer_grid, grid_elems, -1)
        fill_i32(owner_grid, grid_elems, int(OWNER_SENTINEL))
        fill_i32(out_count, 1, 0)

        _scatter_gear_layer_base(flat_dev, base_dev, layer_start, layer_count, layer_grid)
        _scatter_gear_layer_owner(flat_dev, base_dev, layer_start, layer_count, layer_grid, owner_grid)
        suffix_max_cm_fm_gpu(layer_grid, cm_size=cm_size, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size)
        _filter_gear_layer(
            flat_dev,
            base_dev,
            code_dev,
            layer_start,
            layer_count,
            cm_size,
            fm_size,
            ft_size,
            ff_size,
            higher_valid,
            layer_grid,
            owner_grid,
            higher_grid,
            out_flat,
            out_base,
            out_code,
            out_count,
        )
        suffix_max_cm_fm_gpu(higher_grid, cm_size=cm_size, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size)
        higher_valid = 1

        count = int(out_count.to_numpy()[0])
        if count <= 0:
            continue

        flat_np = out_flat.to_numpy()[:count].astype(np.int32, copy=False)
        base_np = out_base.to_numpy()[:count].astype(np.int32, copy=False)
        code_np = out_code.to_numpy()[:count].astype(np.uint64, copy=False)
        sort_order = np.argsort(flat_np, kind="stable")
        flat_np = flat_np[sort_order]
        base_np = base_np[sort_order]
        code_np = code_np[sort_order]
        kept_points.append(_points_from_flat(pp, flat_np, base_np, fm_size=fm_size, ft_size=ft_size, ff_size=ff_size))
        kept_codes.append(code_np)

    points = np.concatenate(kept_points, axis=0) if kept_points else np.zeros((0, 6), dtype=np.int32)
    codes = np.concatenate(kept_codes, axis=0) if kept_codes else np.zeros(0, dtype=np.uint64)
    return total_points, points, codes, float(time.perf_counter() - t0)
