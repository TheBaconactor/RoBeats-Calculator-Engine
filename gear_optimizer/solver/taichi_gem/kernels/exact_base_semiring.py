"""GPU primitives for the exact Base semiring frontier."""

from typing import Any

import taichi as ti

from gear_optimizer.core.constants import MAX_STAT_INDEX, TOTAL_GEM_BUDGET


_MAX_STAT_INDEX = int(MAX_STAT_INDEX)
_GRID_SIZE = _MAX_STAT_INDEX + 1
_BUDGET_SIZE = int(TOTAL_GEM_BUDGET) + 1
_BOUND_BIN_WIDTH = 10
_BOUND_BIN_COUNT = (int(TOTAL_GEM_BUDGET) // _BOUND_BIN_WIDTH) + 1


@ti.kernel
def exact_base_fill_u64_kernel(
    dst: ti.types.ndarray(dtype=ti.u64, ndim=1),
    n: ti.i32,
):
    for idx in range(n):
        dst[idx] = ti.u64(0)


@ti.kernel
def exact_base_fill_i32_kernel(
    dst: ti.types.ndarray(dtype=ti.i32, ndim=1),
    n: ti.i32,
    value: ti.i32,
):
    for idx in range(n):
        dst[idx] = value


@ti.kernel
def exact_base_suffix_cm_u64_kernel(
    grid: ti.types.ndarray(dtype=ti.u64, ndim=1),
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
            value = grid[next_flat]
            if value > grid[flat]:
                grid[flat] = value


@ti.kernel
def exact_base_suffix_fm_u64_kernel(
    grid: ti.types.ndarray(dtype=ti.u64, ndim=1),
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
            value = grid[next_flat]
            if value > grid[flat]:
                grid[flat] = value


def exact_base_suffix_cm_fm_u64(
    grid: Any,
    *,
    cm_size: int,
    fm_size: int,
    ft_size: int,
    ff_size: int,
) -> None:
    exact_base_suffix_cm_u64_kernel(
        grid,
        int(cm_size),
        int(fm_size),
        int(ft_size),
        int(ff_size),
    )
    exact_base_suffix_fm_u64_kernel(
        grid,
        int(cm_size),
        int(fm_size),
        int(ft_size),
        int(ff_size),
    )


@ti.kernel
def exact_base_score_frontier_bounds_kernel(
    state_key: ti.types.ndarray(dtype=ti.i32, ndim=1),
    state_q: ti.types.ndarray(dtype=ti.i32, ndim=1),
    state_count: ti.i32,
    final_fm_size: ti.i32,
    program_count: ti.i32,
    program_offsets: ti.types.ndarray(dtype=ti.i32, ndim=1),
    program_budget: ti.types.ndarray(dtype=ti.i32, ndim=1),
    program_direct: ti.types.ndarray(dtype=ti.i32, ndim=1),
    program_body_fever: ti.types.ndarray(dtype=ti.i32, ndim=1),
    program_body_normal: ti.types.ndarray(dtype=ti.i32, ndim=1),
    program_head_normal: ti.types.ndarray(dtype=ti.i32, ndim=1),
    program_head_fever: ti.types.ndarray(dtype=ti.i32, ndim=1),
    program_sigma_normal: ti.types.ndarray(dtype=ti.i32, ndim=1),
    program_sigma_fever: ti.types.ndarray(dtype=ti.i32, ndim=1),
    ref_cm: ti.types.ndarray(dtype=ti.f64, ndim=1),
    ref_fm: ti.types.ndarray(dtype=ti.f64, ndim=1),
    joint_cm_fm: ti.types.ndarray(dtype=ti.f64, ndim=1),
    joint_cm_span_fm: ti.types.ndarray(dtype=ti.f64, ndim=1),
    response_cm_fm_bound: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_bounds: ti.types.ndarray(dtype=ti.i32, ndim=1),
    invalid: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    normal_rounding = ti.cast(1.0 / ((1.0 - (2.0**-24)) ** 5), ti.f64)
    fever_rounding = ti.cast(1.0 / ((1.0 - (2.0**-24)) ** 6), ti.f64)
    for row in range(state_count):
        key = state_key[row]
        program = key % program_count
        key = key // program_count
        fm = key % final_fm_size
        cm = key // final_fm_size
        start = program_offsets[program]
        end = program_offsets[program + 1]
        best_upper = ti.i64(-1)
        for entry in range(start, end):
            budget = program_budget[entry]
            base_anchor = state_q[row] + program_direct[entry]
            for bin_index in ti.static(range(_BOUND_BIN_COUNT)):
                bin_lo = bin_index * _BOUND_BIN_WIDTH
                if bin_lo <= budget:
                    bin_hi = ti.min(budget, bin_lo + _BOUND_BIN_WIDTH - 1)
                    response_idx = budget * _BOUND_BIN_COUNT + bin_index
                    base_upper = base_anchor + response_cm_fm_bound[response_idx]
                    cm_idx = ti.min(_MAX_STAT_INDEX, cm + 2 * bin_hi)
                    fm_idx = ti.min(_MAX_STAT_INDEX, fm + 3 * bin_hi)
                    joint_idx = (cm * _GRID_SIZE + fm) * _BUDGET_SIZE + bin_hi
                    cm_max = ref_cm[cm_idx]
                    fm_max = ref_fm[fm_idx]
                    cm_fm_max = joint_cm_fm[joint_idx]
                    cm_span_fm_max = joint_cm_span_fm[joint_idx]
                    base_f64 = ti.cast(base_upper, ti.f64)
                    body_normal_unit = ti.cast(
                        ti.ceil(base_f64 * cm_max * normal_rounding), ti.i64
                    ) + 1
                    body_fever_unit = ti.cast(
                        ti.ceil(base_f64 * cm_fm_max * fever_rounding), ti.i64
                    ) + 1
                    head_normal = program_head_normal[entry]
                    head_fever = program_head_fever[entry]
                    head_normal_ideal = base_f64 * (
                        ti.cast(head_normal, ti.f64)
                        + (
                            (cm_max - 1.0)
                            * ti.cast(program_sigma_normal[entry], ti.f64)
                            / 100.0
                        )
                    )
                    head_fever_ideal = base_f64 * (
                        fm_max * ti.cast(head_fever, ti.f64)
                        + (
                            cm_span_fm_max
                            * ti.cast(program_sigma_fever[entry], ti.f64)
                            / 100.0
                        )
                    )
                    upper = (
                        ti.cast(program_body_normal[entry], ti.i64) * body_normal_unit
                        + ti.cast(program_body_fever[entry], ti.i64) * body_fever_unit
                        + ti.cast(ti.ceil(head_normal_ideal * normal_rounding), ti.i64)
                        + ti.cast(head_normal, ti.i64)
                        + ti.cast(ti.ceil(head_fever_ideal * fever_rounding), ti.i64)
                        + ti.cast(head_fever, ti.i64)
                    )
                    if upper > best_upper:
                        best_upper = upper
        if best_upper < 0 or best_upper > 2_147_483_647:
            ti.atomic_max(invalid[0], 1)
            out_bounds[row] = -1
        else:
            out_bounds[row] = ti.cast(best_upper, ti.i32)


@ti.kernel
def exact_base_scatter_gear_pairs_kernel(
    left: ti.types.ndarray(dtype=ti.i32, ndim=2),
    right: ti.types.ndarray(dtype=ti.i32, ndim=2),
    ref_pp: ti.types.ndarray(dtype=ti.i32, ndim=1),
    left_count: ti.i32,
    right_count: ti.i32,
    fixed_pp: ti.i32,
    mini_pp_total: ti.i32,
    fixed_lane: ti.i32,
    same_color: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
    grid: ti.types.ndarray(dtype=ti.u64, ndim=1),
):
    for pair_idx in range(left_count * right_count):
        left_idx = pair_idx // right_count
        right_idx = pair_idx - left_idx * right_count
        pp = left[left_idx, 0] + right[right_idx, 0] + fixed_pp + mini_pp_total
        if pp < 0:
            pp = 0
        if pp > _MAX_STAT_INDEX:
            pp = _MAX_STAT_INDEX
        cm = left[left_idx, 1] + right[right_idx, 1]
        fm = left[left_idx, 2] + right[right_idx, 2]
        ft = left[left_idx, 3] + right[right_idx, 3]
        ff = left[left_idx, 4] + right[right_idx, 4]
        if cm < 0:
            cm = 0
        if cm > _MAX_STAT_INDEX:
            cm = _MAX_STAT_INDEX
        if fm < 0:
            fm = 0
        if fm > _MAX_STAT_INDEX:
            fm = _MAX_STAT_INDEX
        if ft < 0:
            ft = 0
        if ft > _MAX_STAT_INDEX:
            ft = _MAX_STAT_INDEX
        if ff < 0:
            ff = 0
        if ff > _MAX_STAT_INDEX:
            ff = _MAX_STAT_INDEX
        lane = left[left_idx, 5] + right[right_idx, 5]
        if same_color != 0:
            lane = (3 * lane) // 2
        q = lane + fixed_lane + ref_pp[pp]
        flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
        inverse_owner = ti.u64(0xFFFF_FFFF) - ti.cast(pair_idx, ti.u64)
        packed = (ti.cast(q + 1, ti.u64) << 32) | inverse_owner
        if ref_pp[pp] >= 0:
            ti.atomic_max(grid[flat], packed)


@ti.kernel
def exact_base_compact_gear_pairs_kernel(
    left: ti.types.ndarray(dtype=ti.i32, ndim=2),
    right: ti.types.ndarray(dtype=ti.i32, ndim=2),
    ref_pp: ti.types.ndarray(dtype=ti.i32, ndim=1),
    left_count: ti.i32,
    right_count: ti.i32,
    fixed_pp: ti.i32,
    mini_pp_total: ti.i32,
    fixed_lane: ti.i32,
    same_color: ti.i32,
    cm_size: ti.i32,
    fm_size: ti.i32,
    ft_size: ti.i32,
    ff_size: ti.i32,
    grid: ti.types.ndarray(dtype=ti.u64, ndim=1),
    out_key: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_q: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_owner: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_capacity: ti.i32,
    write_output: ti.template(),
):
    for pair_idx in range(left_count * right_count):
        left_idx = pair_idx // right_count
        right_idx = pair_idx - left_idx * right_count
        pp = left[left_idx, 0] + right[right_idx, 0] + fixed_pp + mini_pp_total
        if pp < 0:
            pp = 0
        if pp > _MAX_STAT_INDEX:
            pp = _MAX_STAT_INDEX
        cm = left[left_idx, 1] + right[right_idx, 1]
        fm = left[left_idx, 2] + right[right_idx, 2]
        ft = left[left_idx, 3] + right[right_idx, 3]
        ff = left[left_idx, 4] + right[right_idx, 4]
        if cm < 0:
            cm = 0
        if cm > _MAX_STAT_INDEX:
            cm = _MAX_STAT_INDEX
        if fm < 0:
            fm = 0
        if fm > _MAX_STAT_INDEX:
            fm = _MAX_STAT_INDEX
        if ft < 0:
            ft = 0
        if ft > _MAX_STAT_INDEX:
            ft = _MAX_STAT_INDEX
        if ff < 0:
            ff = 0
        if ff > _MAX_STAT_INDEX:
            ff = _MAX_STAT_INDEX
        lane = left[left_idx, 5] + right[right_idx, 5]
        if same_color != 0:
            lane = (3 * lane) // 2
        q = lane + fixed_lane + ref_pp[pp]
        flat = (((cm * fm_size) + fm) * ft_size + ft) * ff_size + ff
        inverse_owner = ti.u64(0xFFFF_FFFF) - ti.cast(pair_idx, ti.u64)
        packed = (ti.cast(q + 1, ti.u64) << 32) | inverse_owner
        if ref_pp[pp] >= 0 and packed == grid[flat]:
            strict_q = -1
            if cm + 1 < cm_size:
                neighbor = grid[
                    ((((cm + 1) * fm_size) + fm) * ft_size + ft) * ff_size + ff
                ]
                neighbor_q = ti.cast(neighbor >> 32, ti.i32) - 1
                if neighbor_q > strict_q:
                    strict_q = neighbor_q
            if fm + 1 < fm_size:
                neighbor = grid[
                    (((cm * fm_size) + fm + 1) * ft_size + ft) * ff_size + ff
                ]
                neighbor_q = ti.cast(neighbor >> 32, ti.i32) - 1
                if neighbor_q > strict_q:
                    strict_q = neighbor_q
            if q > strict_q:
                out_idx = ti.atomic_add(out_count[0], 1)
                if ti.static(write_output):
                    if out_idx < out_capacity:
                        out_key[out_idx] = flat
                        out_q[out_idx] = q
                        out_owner[out_idx] = pair_idx


@ti.kernel
def exact_base_scatter_combined_pairs_kernel(
    gear_key: ti.types.ndarray(dtype=ti.i32, ndim=1),
    gear_q: ti.types.ndarray(dtype=ti.i32, ndim=1),
    minis: ti.types.ndarray(dtype=ti.i32, ndim=2),
    program_by_cell: ti.types.ndarray(dtype=ti.i32, ndim=1),
    gear_count: ti.i32,
    mini_count: ti.i32,
    gear_fm_size: ti.i32,
    gear_ft_size: ti.i32,
    gear_ff_size: ti.i32,
    fixed_cm: ti.i32,
    fixed_fm: ti.i32,
    fixed_ft: ti.i32,
    fixed_ff: ti.i32,
    same_color: ti.i32,
    final_fm_size: ti.i32,
    program_count: ti.i32,
    grid: ti.types.ndarray(dtype=ti.u64, ndim=1),
):
    for pair_idx in range(gear_count * mini_count):
        gear_idx = pair_idx // mini_count
        mini_idx = pair_idx - gear_idx * mini_count
        key = gear_key[gear_idx]
        gear_ff = key % gear_ff_size
        key = key // gear_ff_size
        gear_ft = key % gear_ft_size
        key = key // gear_ft_size
        gear_fm = key % gear_fm_size
        gear_cm = key // gear_fm_size
        cm = gear_cm + minis[mini_idx, 1] + fixed_cm
        fm = gear_fm + minis[mini_idx, 2] + fixed_fm
        ft = gear_ft + minis[mini_idx, 3] + fixed_ft
        ff = gear_ff + minis[mini_idx, 4] + fixed_ff
        if cm < 0:
            cm = 0
        if cm > _MAX_STAT_INDEX:
            cm = _MAX_STAT_INDEX
        if fm < 0:
            fm = 0
        if fm > _MAX_STAT_INDEX:
            fm = _MAX_STAT_INDEX
        if ft < 0:
            ft = 0
        if ft > _MAX_STAT_INDEX:
            ft = _MAX_STAT_INDEX
        if ff < 0:
            ff = 0
        if ff > _MAX_STAT_INDEX:
            ff = _MAX_STAT_INDEX
        lane = minis[mini_idx, 5]
        if same_color != 0:
            lane = (3 * lane) // 2
        q = gear_q[gear_idx] + lane
        program = program_by_cell[ft * _GRID_SIZE + ff]
        flat = (cm * final_fm_size + fm) * program_count + program
        inverse_owner = ti.u64(0xFFFF_FFFF) - ti.cast(pair_idx, ti.u64)
        packed = (ti.cast(q + 1, ti.u64) << 32) | inverse_owner
        ti.atomic_max(grid[flat], packed)


@ti.kernel
def exact_base_compact_combined_pairs_kernel(
    gear_key: ti.types.ndarray(dtype=ti.i32, ndim=1),
    gear_q: ti.types.ndarray(dtype=ti.i32, ndim=1),
    minis: ti.types.ndarray(dtype=ti.i32, ndim=2),
    program_by_cell: ti.types.ndarray(dtype=ti.i32, ndim=1),
    gear_count: ti.i32,
    mini_count: ti.i32,
    gear_fm_size: ti.i32,
    gear_ft_size: ti.i32,
    gear_ff_size: ti.i32,
    fixed_cm: ti.i32,
    fixed_fm: ti.i32,
    fixed_ft: ti.i32,
    fixed_ff: ti.i32,
    same_color: ti.i32,
    final_cm_size: ti.i32,
    final_fm_size: ti.i32,
    program_count: ti.i32,
    grid: ti.types.ndarray(dtype=ti.u64, ndim=1),
    out_key: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_q: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_owner: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_count: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_capacity: ti.i32,
    write_output: ti.template(),
):
    for pair_idx in range(gear_count * mini_count):
        gear_idx = pair_idx // mini_count
        mini_idx = pair_idx - gear_idx * mini_count
        key = gear_key[gear_idx]
        gear_ff = key % gear_ff_size
        key = key // gear_ff_size
        gear_ft = key % gear_ft_size
        key = key // gear_ft_size
        gear_fm = key % gear_fm_size
        gear_cm = key // gear_fm_size
        cm = gear_cm + minis[mini_idx, 1] + fixed_cm
        fm = gear_fm + minis[mini_idx, 2] + fixed_fm
        ft = gear_ft + minis[mini_idx, 3] + fixed_ft
        ff = gear_ff + minis[mini_idx, 4] + fixed_ff
        if cm < 0:
            cm = 0
        if cm > _MAX_STAT_INDEX:
            cm = _MAX_STAT_INDEX
        if fm < 0:
            fm = 0
        if fm > _MAX_STAT_INDEX:
            fm = _MAX_STAT_INDEX
        if ft < 0:
            ft = 0
        if ft > _MAX_STAT_INDEX:
            ft = _MAX_STAT_INDEX
        if ff < 0:
            ff = 0
        if ff > _MAX_STAT_INDEX:
            ff = _MAX_STAT_INDEX
        lane = minis[mini_idx, 5]
        if same_color != 0:
            lane = (3 * lane) // 2
        q = gear_q[gear_idx] + lane
        program = program_by_cell[ft * _GRID_SIZE + ff]
        flat = (cm * final_fm_size + fm) * program_count + program
        inverse_owner = ti.u64(0xFFFF_FFFF) - ti.cast(pair_idx, ti.u64)
        packed = (ti.cast(q + 1, ti.u64) << 32) | inverse_owner
        if packed == grid[flat]:
            strict_q = -1
            if cm + 1 < final_cm_size:
                neighbor = grid[
                    ((cm + 1) * final_fm_size + fm) * program_count + program
                ]
                neighbor_q = ti.cast(neighbor >> 32, ti.i32) - 1
                if neighbor_q > strict_q:
                    strict_q = neighbor_q
            if fm + 1 < final_fm_size:
                neighbor = grid[
                    (cm * final_fm_size + fm + 1) * program_count + program
                ]
                neighbor_q = ti.cast(neighbor >> 32, ti.i32) - 1
                if neighbor_q > strict_q:
                    strict_q = neighbor_q
            if q > strict_q:
                out_idx = ti.atomic_add(out_count[0], 1)
                if ti.static(write_output):
                    if out_idx < out_capacity:
                        out_key[out_idx] = flat
                        out_q[out_idx] = q
                        out_owner[out_idx] = pair_idx


@ti.kernel
def exact_base_gather_witness_chains_kernel(
    selected: ti.types.ndarray(dtype=ti.i32, ndim=1),
    final_owner: ti.types.ndarray(dtype=ti.i32, ndim=1),
    gear_owner: ti.types.ndarray(dtype=ti.i32, ndim=1),
    mini_count: ti.i32,
    selected_count: ti.i32,
    out_gear_pair: ti.types.ndarray(dtype=ti.i32, ndim=1),
    out_mini: ti.types.ndarray(dtype=ti.i32, ndim=1),
):
    for row in range(selected_count):
        pair_owner = final_owner[selected[row]]
        gear_idx = pair_owner // mini_count
        out_gear_pair[row] = gear_owner[gear_idx]
        out_mini[row] = pair_owner - gear_idx * mini_count


__all__ = [
    "exact_base_compact_combined_pairs_kernel",
    "exact_base_compact_gear_pairs_kernel",
    "exact_base_fill_i32_kernel",
    "exact_base_fill_u64_kernel",
    "exact_base_gather_witness_chains_kernel",
    "exact_base_scatter_combined_pairs_kernel",
    "exact_base_scatter_gear_pairs_kernel",
    "exact_base_score_frontier_bounds_kernel",
    "exact_base_suffix_cm_fm_u64",
    "exact_base_suffix_cm_u64_kernel",
    "exact_base_suffix_fm_u64_kernel",
]
