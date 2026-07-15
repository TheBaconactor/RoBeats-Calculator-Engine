import numpy as np
import pytest


pytestmark = pytest.mark.gpu


def _row(
    *,
    pp: int = 0,
    cm: int = 0,
    fm: int = 0,
    ft: int = 0,
    ff: int = 0,
    lane: int = 0,
) -> np.ndarray:
    return np.asarray([pp, cm, fm, ft, ff, lane], dtype=np.int32)


def _upload_i32(ti, array: np.ndarray):
    contiguous = np.ascontiguousarray(array, dtype=np.int32)
    device = ti.ndarray(dtype=ti.i32, shape=contiguous.shape)
    device.from_numpy(contiguous)
    return device


def _upload_f64(ti, array: np.ndarray):
    contiguous = np.ascontiguousarray(array, dtype=np.float64)
    device = ti.ndarray(dtype=ti.f64, shape=contiguous.shape)
    device.from_numpy(contiguous)
    return device


def _require_vulkan():
    from gear_optimizer.solver.taichi_gem.runtime import init_taichi, ti

    init_taichi()
    if ti.cfg.arch != ti.vulkan:
        pytest.skip(f"requires Vulkan, got {ti.cfg.arch}")
    return ti


def test_exact_base_semiring_keeps_strict_dominator_and_witness_chain() -> None:
    from gear_optimizer.solver.taichi_gem.kernels import (
        exact_base_compact_combined_pairs_kernel,
        exact_base_compact_gear_pairs_kernel,
        exact_base_fill_i32_kernel,
        exact_base_fill_u64_kernel,
        exact_base_gather_witness_chains_kernel,
        exact_base_scatter_combined_pairs_kernel,
        exact_base_scatter_gear_pairs_kernel,
        exact_base_suffix_cm_fm_u64,
    )

    ti = _require_vulkan()
    left = _upload_i32(
        ti,
        np.vstack(
            (
                _row(pp=-1, cm=-1, fm=-1, ft=-1, ff=-1, lane=10),
                _row(cm=1, lane=10),
                _row(pp=1, cm=1, lane=100),
            )
        ),
    )
    right = _upload_i32(ti, np.vstack((_row(),)))
    component_ref_pp = np.zeros(161, dtype=np.int32)
    component_ref_pp[1] = -1
    ref_pp = _upload_i32(ti, component_ref_pp)
    gear_grid = ti.ndarray(dtype=ti.u64, shape=(2,))
    count = ti.ndarray(dtype=ti.i32, shape=(1,))
    dummy = ti.ndarray(dtype=ti.i32, shape=(1,))
    exact_base_fill_u64_kernel(gear_grid, 2)
    exact_base_fill_i32_kernel(count, 1, 0)
    exact_base_scatter_gear_pairs_kernel(
        left,
        right,
        ref_pp,
        3,
        1,
        0,
        0,
        0,
        0,
        1,
        1,
        1,
        gear_grid,
    )
    exact_base_suffix_cm_fm_u64(
        gear_grid,
        cm_size=2,
        fm_size=1,
        ft_size=1,
        ff_size=1,
    )
    exact_base_compact_gear_pairs_kernel(
        left,
        right,
        ref_pp,
        3,
        1,
        0,
        0,
        0,
        0,
        2,
        1,
        1,
        1,
        gear_grid,
        dummy,
        dummy,
        dummy,
        count,
        0,
        False,
    )
    assert int(count.to_numpy()[0]) == 1

    gear_key = ti.ndarray(dtype=ti.i32, shape=(1,))
    gear_q = ti.ndarray(dtype=ti.i32, shape=(1,))
    gear_owner = ti.ndarray(dtype=ti.i32, shape=(1,))
    exact_base_fill_i32_kernel(count, 1, 0)
    exact_base_compact_gear_pairs_kernel(
        left,
        right,
        ref_pp,
        3,
        1,
        0,
        0,
        0,
        0,
        2,
        1,
        1,
        1,
        gear_grid,
        gear_key,
        gear_q,
        gear_owner,
        count,
        1,
        True,
    )
    assert int(count.to_numpy()[0]) == 1
    assert int(gear_key.to_numpy()[0]) == 1
    assert int(gear_q.to_numpy()[0]) == 10
    assert int(gear_owner.to_numpy()[0]) == 1

    minis = _upload_i32(ti, np.vstack((_row(), _row(ft=1))))
    programs = _upload_i32(ti, np.zeros(161 * 161, dtype=np.int32))
    final_grid = ti.ndarray(dtype=ti.u64, shape=(2,))
    exact_base_fill_u64_kernel(final_grid, 2)
    exact_base_fill_i32_kernel(count, 1, 0)
    exact_base_scatter_combined_pairs_kernel(
        gear_key,
        gear_q,
        minis,
        programs,
        1,
        2,
        1,
        1,
        1,
        0,
        0,
        0,
        0,
        0,
        1,
        1,
        final_grid,
    )
    exact_base_suffix_cm_fm_u64(
        final_grid,
        cm_size=2,
        fm_size=1,
        ft_size=1,
        ff_size=1,
    )
    exact_base_compact_combined_pairs_kernel(
        gear_key,
        gear_q,
        minis,
        programs,
        1,
        2,
        1,
        1,
        1,
        0,
        0,
        0,
        0,
        0,
        2,
        1,
        1,
        final_grid,
        dummy,
        dummy,
        dummy,
        count,
        0,
        False,
    )
    assert int(count.to_numpy()[0]) == 1

    final_key = ti.ndarray(dtype=ti.i32, shape=(1,))
    final_q = ti.ndarray(dtype=ti.i32, shape=(1,))
    final_owner = ti.ndarray(dtype=ti.i32, shape=(1,))
    exact_base_fill_i32_kernel(count, 1, 0)
    exact_base_compact_combined_pairs_kernel(
        gear_key,
        gear_q,
        minis,
        programs,
        1,
        2,
        1,
        1,
        1,
        0,
        0,
        0,
        0,
        0,
        2,
        1,
        1,
        final_grid,
        final_key,
        final_q,
        final_owner,
        count,
        1,
        True,
    )
    assert int(count.to_numpy()[0]) == 1
    assert int(final_key.to_numpy()[0]) == 1
    assert int(final_q.to_numpy()[0]) == 10
    assert int(final_owner.to_numpy()[0]) == 0

    selected = _upload_i32(ti, np.asarray([0], dtype=np.int32))
    out_gear_pair = ti.ndarray(dtype=ti.i32, shape=(1,))
    out_mini = ti.ndarray(dtype=ti.i32, shape=(1,))
    exact_base_gather_witness_chains_kernel(
        selected,
        final_owner,
        gear_owner,
        2,
        1,
        out_gear_pair,
        out_mini,
    )
    assert int(out_gear_pair.to_numpy()[0]) == 1
    assert int(out_mini.to_numpy()[0]) == 0


def test_exact_base_frontier_bound_flags_empty_program_atomically() -> None:
    from gear_optimizer.solver.taichi_gem.kernels import (
        exact_base_fill_i32_kernel,
        exact_base_score_frontier_bounds_kernel,
    )

    ti = _require_vulkan()
    state_key = _upload_i32(ti, np.asarray([0, 1], dtype=np.int32))
    state_q = _upload_i32(ti, np.asarray([10, 10], dtype=np.int32))
    program_offsets = _upload_i32(ti, np.asarray([0, 1, 1], dtype=np.int32))
    program_budget = _upload_i32(ti, np.asarray([0], dtype=np.int32))
    program_direct = _upload_i32(ti, np.asarray([0], dtype=np.int32))
    program_body_fever = _upload_i32(ti, np.asarray([0], dtype=np.int32))
    program_body_normal = _upload_i32(ti, np.asarray([1], dtype=np.int32))
    program_head_normal = _upload_i32(ti, np.asarray([0], dtype=np.int32))
    program_head_fever = _upload_i32(ti, np.asarray([0], dtype=np.int32))
    program_sigma_normal = _upload_i32(ti, np.asarray([0], dtype=np.int32))
    program_sigma_fever = _upload_i32(ti, np.asarray([0], dtype=np.int32))
    one_f64 = _upload_f64(ti, np.asarray([1.0], dtype=np.float64))
    zero_f64 = _upload_f64(ti, np.asarray([0.0], dtype=np.float64))
    response_bound = _upload_i32(ti, np.zeros(91 * 10, dtype=np.int32))
    bounds = ti.ndarray(dtype=ti.i32, shape=(2,))
    invalid = ti.ndarray(dtype=ti.i32, shape=(1,))
    exact_base_fill_i32_kernel(invalid, 1, 0)
    exact_base_score_frontier_bounds_kernel(
        state_key,
        state_q,
        2,
        1,
        2,
        program_offsets,
        program_budget,
        program_direct,
        program_body_fever,
        program_body_normal,
        program_head_normal,
        program_head_fever,
        program_sigma_normal,
        program_sigma_fever,
        one_f64,
        one_f64,
        one_f64,
        zero_f64,
        response_bound,
        bounds,
        invalid,
    )

    assert bounds.to_numpy().tolist() == [12, -1]
    assert int(invalid.to_numpy()[0]) == 1
